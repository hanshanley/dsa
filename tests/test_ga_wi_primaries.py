import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from dsa_analysis.ga_wi_primaries import (
    _contest_rows,
    parse_georgia,
    parse_wisconsin,
)


class GeorgiaWisconsinPrimaryTests(unittest.TestCase):
    def test_georgia_uses_ballot_category_and_blanks_write_in_party(self):
        source = {
            "source_id": "ga-test",
            "date": "2026-05-19",
            "stage": "primary",
            "slug": "test",
            "expected_contests": {("House", "01", "Democratic")},
        }
        metadata = {
            "electionDate": "2026-05-19",
            "isOfficialResults": True,
            "asOf": "2026-06-05T00:00:00Z",
        }
        results = {
            "data": [
                {
                    "id": "contest-1",
                    "name": [{"languageId": "en", "text": (
                        "US House of Representatives - District 1 - Dem"
                    )}],
                    "reportingStatus": {"reportingUnits": 2, "totalUnits": 2},
                    "voteTotal": 5,
                    "summaryResults": {
                        "ballotOptions": [
                            {
                                "id": "candidate-1",
                                "name": [{"languageId": "en", "text": "Candidate One"}],
                                "voteCount": 5,
                                "party": {"abbreviation": "DEM"},
                                "groupResults": [
                                    {"voteCount": 0},
                                    {"voteCount": 5},
                                ],
                                "isWriteIn": False,
                                "isQualifiedWriteIn": False,
                            },
                            {
                                "id": "write-in-1",
                                "name": [{"languageId": "en", "text": "Named Write-In"}],
                                "voteCount": 0,
                                "party": {"abbreviation": "DEM"},
                                "groupResults": [
                                    {"voteCount": 0},
                                    {"voteCount": 0},
                                ],
                                "isWriteIn": True,
                                "isQualifiedWriteIn": True,
                            },
                        ],
                    },
                },
            ],
            "totalRecordCount": 1,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results_path = root / "results.json"
            metadata_path = root / "metadata.json"
            results_path.write_text(json.dumps(results))
            metadata_path.write_text(json.dumps(metadata))
            rows = parse_georgia(results_path, metadata_path, source)
        self.assertEqual([row["votes"] for row in rows], [5, 0])
        self.assertEqual({row["primary_party"] for row in rows}, {"Democratic"})
        self.assertEqual(rows[0]["party"], "Democratic")
        self.assertEqual(rows[1]["party"], "")
        self.assertTrue(rows[1]["write_in"])
        self.assertEqual(rows[0]["reporting_units"], 2)

    def test_georgia_rejects_candidate_party_different_from_contest(self):
        source = {
            "source_id": "ga-test",
            "date": "2024-05-21",
            "stage": "primary",
            "slug": "test",
            "expected_contests": {("House", "02", "Republican")},
        }
        metadata = {
            "electionDate": "2024-05-21",
            "isOfficialResults": True,
        }
        results = {
            "data": [
                {
                    "id": "contest-2",
                    "name": [{"languageId": "en", "text": (
                        "US House of Representatives - District 2 - Rep"
                    )}],
                    "reportingStatus": {"reportingUnits": 1, "totalUnits": 1},
                    "voteTotal": 1,
                    "summaryResults": {
                        "ballotOptions": [
                            {
                                "id": "candidate-2",
                                "name": [{"languageId": "en", "text": "Candidate Two"}],
                                "voteCount": 1,
                                "party": {"abbreviation": "DEM"},
                                "groupResults": [{"voteCount": 1}],
                                "isWriteIn": False,
                            },
                        ],
                    },
                },
            ],
            "totalRecordCount": 1,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results_path = root / "results.json"
            metadata_path = root / "metadata.json"
            results_path.write_text(json.dumps(results))
            metadata_path.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, "party differs"):
                parse_georgia(results_path, metadata_path, source)

    def test_wisconsin_preserves_scattering_zero_and_pdf_hash(self):
        source = {
            "date": "2026-08-11",
            "stage": "primary",
            "expected_contests": {("House", "01", "Wisconsin Green")},
        }
        fields = [
            "source_pdf", "page", "chamber", "district", "primary_party",
            "candidate_name", "candidate_source_id", "declared_party",
            "write_in", "votes", "contest_total",
        ]
        rows = [
            {
                "source_pdf": "wi-2026-partisan-primary-summary.pdf",
                "page": "5",
                "chamber": "House",
                "district": "01",
                "primary_party": "Wisconsin Green",
                "candidate_name": "Printed Candidate",
                "candidate_source_id": "candidate-1",
                "declared_party": "Wisconsin Green",
                "write_in": "False",
                "votes": "12",
                "contest_total": "12",
            },
            {
                "source_pdf": "wi-2026-partisan-primary-summary.pdf",
                "page": "5",
                "chamber": "House",
                "district": "01",
                "primary_party": "Wisconsin Green",
                "candidate_name": "SCATTERING",
                "candidate_source_id": "scattering-1",
                "declared_party": "",
                "write_in": "True",
                "votes": "0",
                "contest_total": "12",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            raw_root = Path(directory)
            pdf_dir = raw_root / "wi" / "2026"
            pdf_dir.mkdir(parents=True)
            pdf_path = pdf_dir / "wi-2026-partisan-primary-summary.pdf"
            pdf_path.write_bytes(b"certified pdf")
            extraction = pdf_dir / "extraction.csv"
            with extraction.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            parsed = parse_wisconsin(extraction, raw_root, source)
        self.assertEqual([row["votes"] for row in parsed], [12, 0])
        self.assertEqual(parsed[1]["party"], "")
        self.assertTrue(parsed[1]["write_in"])
        self.assertEqual(
            parsed[0]["source_sha256"],
            hashlib.sha256(b"certified pdf").hexdigest(),
        )

    def test_contest_flags_ignore_scattering_for_unopposed_status(self):
        rows = [
            {
                "contest_id": "wi-test",
                "state_code": "WI",
                "cycle": "2026",
                "election_date": "2026-08-11",
                "stage": "primary",
                "chamber": "House",
                "district": "01",
                "primary_party": "Republican",
                "write_in": False,
                "votes": 10,
                "source_id": "source",
            },
            {
                "contest_id": "wi-test",
                "state_code": "WI",
                "cycle": "2026",
                "election_date": "2026-08-11",
                "stage": "primary",
                "chamber": "House",
                "district": "01",
                "primary_party": "Republican",
                "write_in": True,
                "votes": 1,
                "source_id": "source",
            },
        ]
        contest = _contest_rows(rows)[0]
        self.assertTrue(contest["unopposed"])
        self.assertFalse(contest["write_in_only"])
        self.assertTrue(contest["has_write_in_option"])


if __name__ == "__main__":
    unittest.main()
