import csv
import gzip
import hashlib
import io
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from openpyxl import Workbook

from dsa_analysis.io import write_csv
from dsa_analysis.state_results import (
    FIELDS,
    _aggregate,
    _compress_locators,
    _votes,
    collect_state_primaries,
    parse_alabama,
    parse_california,
    parse_civera,
    parse_florida,
    parse_iowa_text,
    parse_missouri,
    parse_virginia,
)


class StatePrimaryTests(unittest.TestCase):
    def source(self, state="CA", **kwargs):
        return {
            "source_id": "fixture", "state": state, "date": "2026-06-02",
            "url": "https://example.gov/results", "election_system": "partisan_primary",
            **kwargs,
        }

    def test_vote_counts_do_not_convert_missing_to_zero(self):
        self.assertEqual(_votes("0"), 0)
        for value in (None, "", True, -1, 1.5):
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                _votes(value)

    def test_future_provider_results_cannot_replace_the_current_download(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "congressional"
            output.mkdir()
            canonical = output / "state_primary_results.csv"
            canonical.write_text("previous complete download\n")
            previous = canonical.read_bytes()
            future = dict.fromkeys(FIELDS, "")
            future.update({
                "source_id": "future-source", "election_date": "2026-11-03",
                "stage": "primary", "votes": "1",
            })
            write_csv(output / "future.csv", [future], FIELDS)
            (output / "future_manifest.csv").write_text("source_id\n")
            config = {
                "sources": [],
                "supplemental_outputs": [{
                    "provider": "future", "results": "future.csv",
                    "source_manifest": "future_manifest.csv",
                }],
            }
            with (
                patch("dsa_analysis.state_results.ANALYSIS_DATA_DIR", root),
                patch("dsa_analysis.state_results.RAW_DIR", root / "raw"),
                patch("dsa_analysis.state_results.read_json", side_effect=[
                    config, {"research_cutoff": "2026-09-22"},
                ]),
                self.assertRaisesRegex(ValueError, "postdate research cutoff"),
            ):
                collect_state_primaries()
            self.assertEqual(canonical.read_bytes(), previous)

    def test_exact_row_locators_are_compacted_without_losing_rows(self):
        self.assertEqual(
            _compress_locators(["a.csv:3", "a.csv:1", "a.csv:2", "a.csv:6", "b.csv:9"]),
            "a.csv:1-3,6 | b.csv:9",
        )

    def test_california_aggregates_counties_and_preserves_zero_vote_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ca.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "SOV Candidates Export"
            sheet.append(["Election Date", "County Id", "Contest ID", "Contest Name",
                          "Candidate ID", "Candidate Name", "Write-in Flag", "Party Name",
                          "Vote Total"])
            for county, votes in ((1, 3), (2, 7)):
                sheet.append(["06/02/2026", county, "congress-1",
                              "United States Representative District 1",
                              10, "Candidate One", "N", "Democratic", votes])
                sheet.append(["06/02/2026", county, "congress-1",
                              "United States Representative District 1",
                              20, "Candidate Two", "Y", "Republican", 0])
            workbook.save(path)
            source = self.source(expected_house_districts=1, expected_senate_contests=0,
                                 expected_counties=2, election_system="nonpartisan_top_two")
            rows = parse_california(path, source)
            self.assertEqual([row["votes"] for row in rows], [10, 0])
            self.assertTrue(rows[1]["write_in"])
            self.assertEqual(rows[0]["primary_party"], "")
            self.assertEqual(rows[0]["reporting_units"], 2)
            with self.assertRaises(ValueError):
                parse_california(path, {**source, "expected_house_districts": 2})

    def test_florida_recount_replaces_not_adds_and_excludes_noncandidate_tallies(self):
        def row(name, candidate, votes, precinct="01"):
            return ["ALA", "Alachua", "1", "06/02/2026", "Primary", precinct, "Precinct",
                    "100", "50", "0", "0", "Representative in Congress", " District 3",
                    "r", name, "DEM", "v", candidate, str(votes)]

        def text(rows):
            handle = io.StringIO()
            csv.writer(handle, delimiter="\t").writerows(rows)
            return handle.getvalue()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fl.zip"
            with ZipFile(path, "w") as archive:
                archive.writestr("ALA.txt", text([
                    row("Candidate One", "1", 9), row("Candidate Two", "2", 11),
                    row("OverVotes", "901", 1), row("UnderVotes", "902", 2),
                ]))
                archive.writestr("ALA_Recount.txt", text([
                    row("Candidate One", "1", 10), row("Candidate Two", "2", 10),
                ]))
            rows = parse_florida(path, self.source("FL", expected_counties=1))
            self.assertEqual(len(rows), 2)
            self.assertEqual([row["votes"] for row in rows], [10, 10])
            self.assertIn("Recount", rows[0]["source_locators"])

    def test_virginia_refuses_general_election_rows(self):
        row = {
            "CandidateId": "1", "CandidateName": "Candidate", "TOTAL_VOTES": "1",
            "Party": "Democratic", "WriteInVote": "0", "LocalityCode": "001",
            "PrecinctId": "01", "DistrictName": "2", "DistrictType": "congressional",
            "OfficeTitle": "Member, House of Representatives (2nd District)",
            "ElectionDate": "2026-06-02", "ElectionType": "General",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "va.csv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)
            with self.assertRaises(ValueError):
                parse_virginia(path, self.source("VA"))

    def test_duplicate_reporting_units_fail_loudly(self):
        row = {"contest": "c", "candidate_id": "1", "unit": "u"}
        with self.assertRaises(ValueError):
            _aggregate(self.source(), [row, row], Path("not-read"))

    def test_superseded_primary_does_not_become_current_nomination_evidence(self):
        row = {
            "contest": "one", "candidate_id": "one", "unit": "one", "name": "Write-in name",
            "party": "", "primary_party": "REP", "chamber": "House", "district": "01",
            "term": "regular", "write_in": True, "votes": 0, "locator": "source:1",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.csv"
            path.write_text("source")
            output = _aggregate(
                self.source("AL", superseded_house_districts=["01"]), [row], path,
            )
        self.assertEqual(output[0]["stage"], "superseded_primary")
        self.assertEqual(output[0]["primary_party"], "REP")
        self.assertEqual(output[0]["party"], "")
        self.assertEqual(output[0]["votes"], 0)

    def test_alabama_nonapplicable_cells_are_not_missing_candidate_votes(self):
        header = ["Contest Title", "Party", "Candidate", "Precinct 1", "Precinct 2"]
        rows = [
            header,
            ["UNITED STATES REPRESENTATIVE, 1ST CONGRESSIONAL DISTRICT", "REP", "One", 0, ""],
            ["UNITED STATES REPRESENTATIVE, 1ST CONGRESSIONAL DISTRICT", "REP", "Two", 3, ""],
        ]
        sheet = types.SimpleNamespace(
            nrows=len(rows), ncols=len(header), row_values=lambda index: rows[index],
        )
        reader = types.SimpleNamespace(open_workbook=lambda **_: types.SimpleNamespace(
            sheet_by_index=lambda _: sheet,
        ))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "al.zip"
            with ZipFile(path, "w") as archive:
                archive.writestr("County.xls", b"fixture read through the mocked BIFF reader")
            with patch.dict("sys.modules", {"xlrd": reader}):
                output = parse_alabama(path, self.source("AL", expected_counties=1))
                self.assertEqual([row["votes"] for row in output], [0, 3])
                rows[2][-1] = 1
                with self.assertRaisesRegex(ValueError, "partially missing"):
                    parse_alabama(path, self.source("AL", expected_counties=1))

    def test_civera_uses_county_totals_not_precincts_or_same_day_general_contests(self):
        base = {
            "contest_id": "one", "election_date": "2026-06-02T00:00:00Z",
            "election_type": "Primary", "primary_party": "Democratic",
            "office_name": "United States Congressperson", "office_modifier": "",
            "district_name": "1", "candidate_id": "a", "candidate_name": "Candidate",
            "division_id": "county1", "division_type": "County", "vote_channel": "",
            "candidate_party_name": "Democratic", "votes": "3",
        }
        rows = [
            base, {**base, "division_id": "county2", "votes": "4"},
            {**base, "division_id": "precinct", "division_type": "Precinct", "votes": "100"},
            {**base, "office_modifier": "Congressional Vacancy Election", "votes": "200"},
            {**base, "candidate_id": "total", "candidate_name": "Total Votes Cast", "votes": "300"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "co.csv.gz"
            with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(base))
                writer.writeheader()
                writer.writerows(rows)
            output = parse_civera(path, self.source(
                "CO", chamber="House", office_name="United States Congressperson",
                expected_contests=1, filename="co.csv.gz",
            ))
            self.assertEqual(output[0]["votes"], 7)
            self.assertEqual(output[0]["reporting_units"], 2)
            self.assertEqual(output[0]["source_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_iowa_uses_final_statewide_total_and_retains_write_in_only_contests(self):
        text = """[PDF page 2]
IOWA SECRETARY OF STATE
2026 Primary Election CANVASS SUMMARY
United States Representative District 1 - Dem.
Candidate One,
DEM Write-in Under Votes Over Votes Total
Election Day 2 0 0 0 2
Absentee 1 0 0 0 1
Total 3 0 0 0 3
[PDF page 3]
TOTAL Candidate One,
DEM Write-in Under Votes Over Votes Total
Election Day 20 2 1 0 23
Absentee 10 1 0 0 11
Total 30 3 1 0 34
[PDF page 4]
IOWA SECRETARY OF STATE
2026 Primary Election CANVASS SUMMARY
United States Representative District 1 - Lib.
Write-in Under Votes Over Votes Total
TOTAL Election Day 0 1 0 1
Absentee 0 0 0 0
Total 0 1 0 1
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "iowa.pdf"
            path.write_bytes(b"fixture source")
            rows = parse_iowa_text(text, path, self.source("IA", expected_contests=2))
            self.assertEqual([row["votes"] for row in rows], [30, 3, 0])
            self.assertTrue(rows[-1]["write_in"])
            self.assertEqual(rows[-1]["primary_party"], "Libertarian")
            self.assertEqual(rows[-1]["party"], "")
            self.assertEqual(rows[0]["source_locators"], "PDF pages 2-3; statewide TOTAL")
            with self.assertRaisesRegex(ValueError, "do not reconcile"):
                parse_iowa_text(
                    text.replace("Total 30 3 1 0 34", "Total 31 3 1 0 35"),
                    path, self.source("IA", expected_contests=2),
                )

    def test_pdf_page_marker_is_provenance_not_part_of_a_candidate_name(self):
        text = """[PDF page 1] Official Election Returns
U.S. Representative - District 1 (2 of 2 Precincts Reported)
Candidate One Republican 1 100.0%
Party Total 1
[PDF page 2] Cori Bush Democratic 3 100.0%
Party Total 3
Total Votes 4
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mo.pdf"
            path.write_bytes(b"source")
            with patch("dsa_analysis.state_results._extract_pdf_text", return_value=("", text)):
                rows = parse_missouri(path, self.source("MO", expected_house_districts=1))
        names = {row["candidate_name"] for row in rows}
        self.assertEqual(names, {"Candidate One", "Cori Bush"})
        bush = next(row for row in rows if row["candidate_name"] == "Cori Bush")
        self.assertEqual(bush["source_locators"], "PDF page 2")


if __name__ == "__main__":
    unittest.main()
