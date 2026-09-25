import csv
import json
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from dsa_analysis.gulf_primaries import (
    _assert_future_scheduled_coverage,
    _coverage_rows,
    _update_party_accounting_future_status,
    parse_louisiana,
    parse_mississippi,
    parse_oklahoma,
)


class GulfPrimaryTests(unittest.TestCase):
    def test_louisiana_2024_is_nonpartisan_open_primary(self):
        source = {
            "source_id": "la-test",
            "date": "2024-11-05",
            "stage": "nonpartisan_primary",
            "system": "nonpartisan_open_primary",
            "url": "https://example.test/la",
        }
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Multi-Parish(Parish)"
        sheet.append([None, "Louisiana Secretary of State"])
        sheet.append([None, "Election Results"])
        sheet.append([None, "Election Date: 2024-11-05"])
        sheet.append([])
        sheet.append([])
        sheet.append(["U. S. Representative -- 1st Congressional District"])
        sheet.append([
            None,
            "Candidate One Democratic (DEM)",
            "Candidate Two No Party (NOPTY)",
        ])
        sheet.append(["Total Votes", 0, 5])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "la.xlsx"
            workbook.save(path)
            rows = parse_louisiana(path, source)
        self.assertEqual([row["votes"] for row in rows], [0, 5])
        self.assertEqual({row["stage"] for row in rows}, {"nonpartisan_primary"})
        self.assertEqual(
            {row["election_system"] for row in rows},
            {"nonpartisan_open_primary"},
        )
        self.assertEqual({row["primary_party"] for row in rows}, {""})
        self.assertEqual([row["party"] for row in rows], ["Democratic", "No Party"])

    def test_mississippi_parser_does_not_bleed_presidential_candidates(self):
        source = {
            "source_id": "ms-test",
            "date": "2024-03-12",
            "stage": "primary",
            "party": "Republican",
        }
        text = """
\fPAGE 1
US House Of Rep 03-3rd Congressional
District
Michael Guest Republican 5 10
United States-President
Donald J. Trump Republican 100 200
US House Of Rep 04-4th Congressional
District
Mike Ezell Republican 3 7
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf_path = root / "results.pdf"
            pdf_path.write_bytes(b"official pdf")
            pdf_path.with_suffix(".txt").write_text(text)
            rows = parse_mississippi(pdf_path, source)
        self.assertEqual(
            [(row["district"], row["candidate_name"], row["votes"]) for row in rows],
            [("03", "Michael Guest", 10), ("04", "Mike Ezell", 7)],
        )

    def test_oklahoma_preserves_zero_and_official_status(self):
        source = {
            "source_id": "ok-test",
            "date": "2026-06-16",
            "stage": "primary",
        }
        payload = {
            "electionDate": "2026-06-16T00:00:00",
            "isOfficial": True,
            "races": [
                {
                    "raceID": 1,
                    "raceTitle": "FOR UNITED STATES SENATOR",
                    "raceTitle2": "Libertarian",
                    "raceCandidates": [
                        {"candName": "Candidate One"},
                        {"candName": "WRITE-IN - Private Person"},
                    ],
                },
            ],
            "results": [
                {
                    "raceID": 1,
                    "totalPrecincts": 10,
                    "reportingPrecincts": 10,
                    "candResults": [
                        {"totalVotes": 5},
                        {"totalVotes": 0},
                    ],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ok.json"
            path.write_text(json.dumps(payload))
            rows = parse_oklahoma(path, source)
        self.assertEqual([row["votes"] for row in rows], [5, 0])
        self.assertEqual(rows[1]["party"], "")
        self.assertTrue(rows[1]["write_in"])
        self.assertEqual(rows[0]["primary_party"], "Libertarian")

    def test_coverage_distinguishes_future_cancelled_and_roster_units(self):
        results = []
        rosters = [
            {
                "state_code": "OK",
                "election_date": "2026-06-16",
                "stage": "primary",
                "chamber": "Senate",
                "district": "S",
                "primary_party": "Libertarian",
                "source_id": "roster",
            },
        ]
        coverage = _coverage_rows(results, rosters, {})
        by_key = {
            (
                row["state_code"],
                row["election_date"],
                row["stage"],
                row["chamber"],
                row["district"],
                row["primary_party"],
            ): row
            for row in coverage
        }
        self.assertEqual(
            by_key[
                ("LA", "2026-11-03", "nonpartisan_primary", "House", "01", "")
            ]["coverage_status"],
            "future_scheduled",
        )
        self.assertEqual(
            by_key[
                (
                    "OK", "2026-08-25", "primary_runoff",
                    "House", "01", "Republican",
                )
            ]["coverage_status"],
            "runoff_cancelled_after_withdrawal",
        )
        self.assertEqual(
            by_key[
                ("OK", "2026-06-16", "primary", "Senate", "S", "Libertarian")
            ]["coverage_status"],
            "unopposed_roster_only",
        )

    def test_future_accounting_requires_future_date_and_no_votes(self):
        coverage = _coverage_rows([], [], {})
        _assert_future_scheduled_coverage(coverage, [])
        fields = [
            "cycle", "election_date", "state_code", "chamber", "district",
            "term", "stage", "primary_party", "status", "candidate_names",
            "source_urls", "locators", "notes",
        ]
        rows = [
            {
                "cycle": "2026",
                "election_date": "2026-11-03",
                "state_code": "LA",
                "chamber": "House",
                "district": f"{district:02}",
                "term": "regular",
                "stage": "nonpartisan_primary",
                "primary_party": "",
                "status": "not_scheduled",
                "candidate_names": "",
                "source_urls": "https://example.test/authority",
                "locators": "page-1",
                "notes": "status enum represented as not_scheduled. future_scheduled",
            }
            for district in range(1, 7)
        ]
        with tempfile.TemporaryDirectory() as directory:
            analysis_root = Path(directory)
            manifest_dir = analysis_root / "gulf"
            manifest_dir.mkdir()
            path = manifest_dir / "party_contest_accounting.csv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            _update_party_accounting_future_status(analysis_root, [])
            with path.open(newline="") as handle:
                updated = list(csv.DictReader(handle))
        self.assertTrue(all(row["status"] == "future_scheduled" for row in updated))
        self.assertTrue(all("not_scheduled" not in row["notes"] for row in updated))


if __name__ == "__main__":
    unittest.main()
