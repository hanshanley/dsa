import csv
import tempfile
import unittest
from pathlib import Path

from dsa_analysis.territorial_primaries import (
    _accounting,
    parse_guam_2024,
    parse_vi_2026,
)


class TerritorialPrimaryTests(unittest.TestCase):
    def test_guam_write_in_has_no_inferred_party(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gu.csv"
            (Path(directory) / "gu-2024-primary-official-results.html").write_text(
                "Official certified delegate results"
            )
            path.write_text(
                "primary_party,candidate_name,votes,write_in,source_locator\n"
                "Democratic,Write-In Totals,5,true,row-1\n"
                "Republican,Candidate,10,false,row-2\n"
            )
            rows = parse_guam_2024(path)
        write_in = next(row for row in rows if row["write_in"])
        self.assertEqual(write_in["party"], "")

    def test_pr_2026_is_verified_unscheduled(self):
        rows = _accounting([
            {
                "state_code": "GU",
                "primary_party": "Democratic", "candidate_name": "D",
                "source_url": "x", "source_locators": "d",
            },
            {
                "state_code": "GU",
                "primary_party": "Republican", "candidate_name": "R",
                "source_url": "x", "source_locators": "r",
            },
            {
                "state_code": "VI", "primary_party": "", "candidate_name": "V",
                "source_url": "v", "source_locators": "v",
            },
        ])
        pr = next(row for row in rows if row["state_code"] == "PR"
                  and row["cycle"] == "2026")
        self.assertEqual(pr["status"], "not_scheduled")

    def test_vi_primary_has_blank_party_without_source_party_label(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vi.csv"
            path.write_text(
                "candidate_name,votes,write_in,source_locator\n"
                "Candidate,10,false,row-1\n"
            )
            rows = parse_vi_2026(path)
        self.assertEqual(rows[0]["primary_party"], "")
        self.assertEqual(rows[0]["party"], "")


if __name__ == "__main__":
    unittest.main()
