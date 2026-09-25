import json
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from dsa_analysis.congressional import (
    _district,
    parse_congressional_workbook,
    parse_senate_class,
    parse_special_elections,
    source_identity_issues,
    export_longitudinal_primary_records,
)
from dsa_analysis.io import read_csv


class CongressionalTests(unittest.TestCase):
    def test_every_party_zero_votes_and_raw_flags_survive_import(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "US House Results by State"
        sheet.append([
            "STATE ABBREVIATION", "STATE", "DISTRICT", "FEC ID#", "CANDIDATE NAME",
            "PARTY", "PRIMARY VOTES", "RUNOFF VOTES", "GENERAL VOTES ",
            "GE RUNOFF ELECTION VOTES (LA)", "FOOTNOTES",
        ])
        sheet.append(["AL", "Alabama", "01", "one", "Example, A", "D", 0, 2, None, None, ""])
        sheet.append(["AL", "Alabama", "01", "two", "Example, B", "R",
                      "Unopposed", None, 100, None, ""])
        sheet.append(["AL", "Alabama", "01", "three", "Example, C", "LIB",
                      "*", None, 10, None, "Nominated by convention"])
        sheet.append(["AL", "Alabama", "01", "", "Scattered", "W", None, None, 3, None, ""])
        sheet.append(["AL", "Alabama", "01", "", None, "D", 999, None, None, None, "Total"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.xlsx"
            workbook.save(path)
            rows = parse_congressional_workbook(path, 2016, "https://www.fec.gov/test.xlsx")
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["primary_votes"], "0")
        self.assertEqual(rows[0]["general_votes"], "")
        self.assertEqual(rows[1]["primary_votes"], "")
        self.assertEqual(rows[1]["primary_votes_raw"], "Unopposed")
        self.assertEqual(rows[2]["primary_votes_raw"], "*")
        self.assertEqual(rows[3]["row_kind"], "aggregate")
        self.assertEqual(json.loads(rows[0]["raw_cells_json"])[6], "0")
        self.assertEqual(rows[0]["source_row"], 2)
        self.assertEqual(len({row["source_record_id"] for row in rows}), 4)

    def test_special_and_full_terms_are_not_collapsed(self):
        self.assertEqual(_district("01 - FULL TERM"), "01")
        self.assertEqual(_district("1 - UNEXPIRED TERM"), "01")
        self.assertEqual(_district("S-Unexpired Term"), "S")
        self.assertEqual(_district(" "), "")

    def test_special_calendar_preserves_date_type_and_source_freshness(self):
        text = """[PDF page 8] SPECIAL ELECTIONS
Updated by: Example, 3/12/2026
2015
NY/11 5/05 Previous member (R) New member (R)
2020
AZ/S 11/03 Previous senator (R) New senator (D)
2026
TX/18** 1/31 Previous member (D) New member (D)
CA/1 6/2 Previous member (R)
FL/01 11/03 Future contest
NOTES:
TX/18 11/4/26
"""
        rows = parse_special_elections(text, 2015, "2026-09-22")
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["reported_election_date"], "2015-05-05")
        self.assertEqual(rows[1]["chamber"], "Senate")
        self.assertEqual(rows[2]["date_type"], "special_general_runoff")
        self.assertEqual(rows[3]["district"], "01")
        self.assertEqual(rows[3]["source_updated_on"], "2026-03-12")
        self.assertEqual(rows[3]["primary_date"], "")

    def test_senate_class_cannot_silently_accept_truncated_source(self):
        with self.assertRaises(ValueError):
            parse_senate_class("<td>A Senator (D-NJ)</td>", 2)

    def test_non_congressional_workbook_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.xlsx"
            Workbook().save(path)
            with self.assertRaises(ValueError):
                parse_congressional_workbook(path, 2024, "https://www.fec.gov/test.xlsx")

    def test_conflicting_source_ids_are_flagged_not_silently_merged(self):
        rows = [
            {
                "fec_candidate_id": "S4NY00404", "candidate_name": name,
                "source_url": "https://www.fec.gov/example.xlsx",
                "source_sheet": "New York", "source_row": number,
            }
            for number, name in enumerate(("Candidate One", "Candidate Two"), 2)
        ]
        issues = source_identity_issues(rows)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["names"], "Candidate One | Candidate Two")
        self.assertEqual(rows[0]["candidate_name"], "Candidate One")

    def test_longitudinal_download_keeps_zero_and_nomination_flags_distinct(self):
        common = {
            "workbook_cycle": 2016, "state_code": "AL", "chamber": "House",
            "district": "01", "term": "regular", "party_raw": "D",
            "candidate_name": "Candidate", "fec_candidate_id": "one", "row_kind": "candidate",
            "primary_runoff_votes_raw": "", "primary_runoff_votes": "",
            "source_url": "https://www.fec.gov/test.xlsx", "source_sha256": "hash",
            "source_sheet": "House", "source_row": 3, "footnotes": "",
        }
        rows = [
            {**common, "source_record_id": "zero", "primary_votes": "0", "primary_votes_raw": "0"},
            {**common, "source_record_id": "flag", "primary_votes": "", "primary_votes_raw": "Unopposed"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            self.assertEqual(export_longitudinal_primary_records(output, rows, []), 2)
            result = read_csv(output / "all_primary_records.csv")
        self.assertEqual(result[0]["votes"], "0")
        self.assertEqual(result[1]["votes"], "")
        self.assertEqual(result[1]["votes_raw"], "Unopposed")
        self.assertEqual(result[1]["observation_status"], "source_nomination_flag")
        self.assertEqual(result[0]["election_date"], "")


if __name__ == "__main__":
    unittest.main()
