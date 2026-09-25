import csv
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from dsa_analysis.nh_ct_nominations import (
    _accounting,
    parse_new_hampshire,
)


class NewHampshireConnecticutTests(unittest.TestCase):
    def test_new_hampshire_uses_totals_and_party_suffixes(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Con1"
        sheet.append(["Title"])
        sheet.append(["Congressional District 1"])
        sheet.append(["Date", "Candidate D, d", "Candidate R, r", "Write-Ins"])
        sheet.append(["Town", 10, 20, 1])
        sheet.append(["Totals", 10, 20, 1])
        source = {
            "source_id": "nh-test", "district": "01",
            "archive_url": "https://example.test/archive",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nh.xlsx"
            workbook.save(path)
            rows = parse_new_hampshire(path, source)
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["primary_party"] for row in rows}, {
            "Democratic", "Republican",
        })

    def test_ct_nomination_does_not_override_numeric_result(self):
        nominations = [{
            "cycle": "2024", "election_date": "2024-08-13",
            "chamber": "House", "district": "04", "primary_party": "Republican",
            "candidate_name": "Nominee", "source_url": "https://example.test/guide",
            "source_locator": "page-4",
        }]
        result = {
            "cycle": "2024", "state_code": "CT", "chamber": "House",
            "district": "04", "primary_party": "Republican",
            "election_date": "2024-08-13", "term": "regular",
            "stage": "primary", "candidate_name": "Candidate",
            "source_url": "https://example.test/results",
            "source_locators": "results:1",
        }
        rows = _accounting([], nominations, [result])
        row = next(item for item in rows if item["state_code"] == "CT"
                   and item["cycle"] == "2024")
        self.assertEqual(row["status"], "results_complete")


if __name__ == "__main__":
    unittest.main()
