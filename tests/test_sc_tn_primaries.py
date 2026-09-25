import csv
import json
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from dsa_analysis.sc_tn_primaries import (
    _coverage_rows,
    parse_south_carolina_civera,
    parse_south_carolina_enr,
    parse_tennessee,
)


class SouthCarolinaTennesseePrimaryTests(unittest.TestCase):
    def test_south_carolina_civera_excludes_accounting_and_preserves_zero(self):
        rows = [
            [
                "", "", "Candidate One", "Write-In", "Total Votes Cast",
                "Overvotes/Undervotes", "Total Ballots Cast",
            ],
            ["", "", "Democratic", "Democratic", "", "", ""],
            ["Congressional District", "1", "5", "0", "5", "10", "15"],
            ["County", "Example", "5", "0", "5", "10", "15"],
            ["Precinct", "One", "0", "0", "0", "2", "2"],
            ["Precinct", "Two", "5", "0", "5", "8", "13"],
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sc-contest-1.csv"
            with path.open("w", newline="") as handle:
                csv.writer(handle).writerows(rows)
            parsed = parse_south_carolina_civera(path)
        self.assertEqual([row["votes"] for row in parsed], [5, 0])
        self.assertEqual(parsed[1]["party"], "")
        self.assertTrue(parsed[1]["write_in"])

    def test_south_carolina_enr_preserves_special_primary_stage(self):
        source = {
            "source_id": "sc-test",
            "election_id": "1",
            "version": "2",
            "date": "2026-08-11",
            "stage": "special_primary",
            "term": "special",
        }
        summary = [
            {
                "C": "U.S.  Senate  - REP",
                "K": "26001",
                "CH": ["Candidate One", "Candidate Two"],
                "P": ["REP", "REP"],
                "V": [0, 5],
                "TP": 46,
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary_path = root / "summary.json"
            config_path = root / "config.json"
            summary_path.write_text(json.dumps(summary))
            config_path.write_text(json.dumps({"isPublished": True}))
            rows = parse_south_carolina_enr(
                summary_path,
                config_path,
                source,
            )
        self.assertEqual([row["votes"] for row in rows], [0, 5])
        self.assertEqual({row["stage"] for row in rows}, {"special_primary"})
        self.assertEqual({row["term"] for row in rows}, {"special"})
        self.assertEqual(rows[0]["reporting_units"], 46)

    def test_tennessee_aggregates_precincts_and_blanks_write_in_party(self):
        header = [
            "COUNTY", "PRCTSEQ", "PRECINCT", "BALSEQID", "JURISID",
            "SECJURISID", "CANDGROUP", "OFFICENAME", "ELECTDATE", "ELECTTYPE",
        ]
        for number in range(1, 11):
            header.extend([
                f"COL{number}HDG",
                f"RNAME{number}",
                f"PARTY{number}",
                f"PVTALLY{number}",
            ])
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "SOFFICEL"
        sheet.append(header)
        for precinct, candidate_votes, write_in_votes in (
            ("One", 5, 0),
            ("Two", 7, 0),
        ):
            row = [
                "Example", precinct, precinct, "1", "0", "0", "0",
                "United States Senate", "2026-08-06", "Republican Primary",
            ]
            row.extend(["1", "Printed Candidate", "Republican", candidate_votes])
            row.extend(["2", "Write-In - Private Person", "Republican", write_in_votes])
            row.extend([None, None, None, None] * 8)
            sheet.append(row)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.xlsx"
            workbook.save(path)
            parsed = parse_tennessee(
                path,
                {
                    "date": "2026-08-06",
                    "source_id": "tn-test",
                    "url": "https://example.test/results",
                    "expected_units": {("Senate", "S", "Republican")},
                },
            )
        self.assertEqual([row["votes"] for row in parsed], [12, 0])
        self.assertEqual(parsed[1]["party"], "")
        self.assertTrue(parsed[1]["write_in"])
        self.assertEqual(parsed[0]["reporting_units"], 2)

    def test_coverage_keeps_missing_primary_unit_explicit(self):
        rows = [
            {
                "state_code": "SC",
                "election_date": "2024-06-11",
                "stage": "primary",
                "chamber": "House",
                "district": "01",
                "primary_party": "Democratic",
                "source_id": "source",
            },
        ]
        coverage = _coverage_rows(rows)
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
                ("SC", "2024-06-11", "primary", "House", "01", "Democratic")
            ]["coverage_status"],
            "actual_results",
        )
        self.assertEqual(
            by_key[
                ("SC", "2024-06-11", "primary", "House", "05", "Republican")
            ]["coverage_status"],
            "no_published_primary_result",
        )


if __name__ == "__main__":
    unittest.main()
