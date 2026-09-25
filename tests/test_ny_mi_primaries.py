import csv
import tempfile
import unittest
from pathlib import Path

from dsa_analysis.ny_mi_primaries import (
    parse_michigan_results,
    parse_ny_enr_partial,
    parse_nyc_results,
    parse_new_york_results,
    parse_new_york_roster,
    parse_suffolk_results,
)


class NewYorkMichiganPrimaryTests(unittest.TestCase):
    def test_michigan_aggregates_counties_and_preserves_write_in_ids(self):
        header = [
            "ElectionDate", "OfficeCode(text)", "DistrictCode(Text)", "StatusCode",
            "CountyCode", "CountyName", "OfficeDescription", "PartyOrder",
            "PartyDescription", "CandidateID", "CandidateLastName",
            "CandidateFirstName", "CandidateMiddleName", "CandidateFormerName",
            "CandidateVotes", "WriteIn(W)/Uncommitted(Z)", "Recount(*)",
            "Nomindated(N)/Elected(E)",
        ]
        senate_rows = [
            [
                "2024-08-06", "7", "0", "0", county, name,
                "UNITED STATES SENATOR 6 YEAR TERM (1) POSITION", "1",
                "DEMOCRATIC", "1", "ALPHA", "ANN", "", "", votes, "", "", "",
            ]
            for county, name, votes in (("1", "ONE", "10"), ("2", "TWO", "20"))
        ]
        text = "TOTAL VOTER TURNOUT: 100\n"
        text += "\t".join(header) + "\n"
        text += "\n".join("\t".join(row) for row in senate_rows) + "\n"
        house_rows = []
        for district in range(1, 14):
            suffix = "TH"
            if district == 1:
                suffix = "ST"
            elif district == 2:
                suffix = "ND"
            elif district == 3:
                suffix = "RD"
            house_rows.append(
                f"2024-08-06\t8\t{district:02}\t0\t1\tONE\t"
                f"{district}{suffix} DISTRICT REPRESENTATIVE IN CONGRESS "
                "2 YEAR TERM (1) POSITION\t1\tREPUBLICAN\t"
                f"{100 + district}\tWRITE-IN\t\t\t\t{district}\tY\t\t"
            )
        text += "\n".join(house_rows) + "\n"
        source = {
            "source_id": "mi-test",
            "date": "2024-08-06",
            "url": "https://example.test/mi",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mi.tsv"
            path.write_text(text)
            rows = parse_michigan_results(path, source)
        senate = [row for row in rows if row["chamber"] == "Senate"]
        self.assertEqual(senate[0]["candidate_name"], "ANN ALPHA")
        self.assertEqual(senate[0]["votes"], 30)
        self.assertEqual(senate[0]["reporting_units"], 2)
        write_ins = [row for row in rows if row["write_in"]]
        self.assertEqual(len(write_ins), 13)
        self.assertEqual({row["candidate_source_id"] for row in write_ins},
                         {str(number) for number in range(101, 114)})

    def test_new_york_keeps_scattering_but_drops_ballot_accounting_rows(self):
        fields = [
            "contest_id", "election_id", "election_date", "election_type",
            "primary_party", "question_text", "question_type", "office_id",
            "office_name", "office_modifier", "district_id", "district_type",
            "district_name", "candidate_id", "candidate_name",
            "retention_candidate_id", "retention_candidate_name", "division_id",
            "division_type", "division_name", "vote_channel", "is_winner",
            "number_seats", "candidate_party_id", "candidate_party_name", "votes",
        ]
        rows = []
        for contest, district in zip(("5566", "5567", "5568", "5580"),
                                     ("17", "22", "24", "16"), strict=True):
            for division, votes in (("1", "3"), ("2", "4")):
                row = dict.fromkeys(fields, "")
                row.update({
                    "contest_id": contest,
                    "election_date": "2024-06-25T00:00:00Z",
                    "election_type": "Primary",
                    "primary_party": "Democratic",
                    "office_name": "Representative in Congress",
                    "district_name": district,
                    "candidate_id": "100",
                    "candidate_name": "Candidate One",
                    "division_id": division,
                    "candidate_party_name": "Democratic",
                    "votes": votes,
                })
                rows.append(row)
            for candidate_id, name, votes in (
                ("6", "Scattering", "1"),
                ("10", "Blank", "2"),
                ("9", "Void", "3"),
                ("1", "Total Votes", "10"),
            ):
                row = dict.fromkeys(fields, "")
                row.update({
                    "contest_id": contest,
                    "election_date": "2024-06-25T00:00:00Z",
                    "election_type": "Primary",
                    "primary_party": "Democratic",
                    "office_name": "Representative in Congress",
                    "district_name": district,
                    "candidate_id": candidate_id,
                    "candidate_name": name,
                    "division_id": "1",
                    "votes": votes,
                })
                rows.append(row)
        source = {
            "source_id": "ny-test",
            "date": "2024-06-25",
            "url": "https://example.test/ny",
            "expected_contests": {"5566", "5567", "5568", "5580"},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ny.csv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            parsed = parse_new_york_results(path, source)
        self.assertEqual(len(parsed), 8)
        candidates = [row for row in parsed if row["candidate_name"] == "Candidate One"]
        self.assertTrue(all(row["votes"] == 7 for row in candidates))
        scattering = [row for row in parsed if row["candidate_name"] == "Scattering"]
        self.assertTrue(all(row["write_in"] for row in scattering))
        self.assertFalse({"Blank", "Void", "Total Votes"} & {
            row["candidate_name"] for row in parsed
        })

    def test_new_york_roster_has_blank_results_and_pdf_locator(self):
        source = {
            "source_id": "ny-roster",
            "date": "2024-06-25",
            "url": "https://example.test/certification",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            extraction = root / "roster.csv"
            extraction.write_text(
                "page,office,district,party,ballot_order,candidate_name\n"
                "3,U.S. Senator,Statewide,Democratic,Uncontested,Example Senator\n"
                "6,Representative in Congress,16,Democratic,1,Example House\n"
            )
            source_pdf = root / "certification.pdf"
            source_pdf.write_bytes(b"official source bytes")
            rows = parse_new_york_roster(extraction, source_pdf, source)
        self.assertEqual([row["votes"] for row in rows], ["", ""])
        self.assertEqual(rows[0]["district"], "S")
        self.assertEqual(rows[1]["district"], "16")
        self.assertEqual(rows[1]["stage"], "primary_roster")
        self.assertEqual(rows[1]["source_locators"], "certification.pdf:page-6")

    def test_nyc_certified_recap_uses_only_total_rows(self):
        row = [""] * 23
        row[3] = (
            "Total for Democratic Representative in Congress "
            "(10th Congressional District)"
        )
        row[4] = "Example Candidate"
        row[5] = "1,234"
        write_in = row.copy()
        write_in[4] = "OTHER PERSON (Write-In)"
        write_in[5] = "2"
        county = row.copy()
        county[3] = "New York County"
        source = {
            "source_id": "nyc-test",
            "date": "2024-06-25",
            "year": 2024,
            "district": "10",
            "party": "Democratic",
            "reporting_units": 2,
            "filename": "nyc-2024-test.csv",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / source["filename"]
            with path.open("w", newline="") as handle:
                csv.writer(handle).writerows([county, row, write_in])
            parsed = parse_nyc_results(path, source)
        self.assertEqual([candidate["votes"] for candidate in parsed], [1234, 2])
        self.assertEqual(parsed[1]["candidate_name"], "OTHER PERSON")
        self.assertTrue(parsed[1]["write_in"])
        self.assertEqual(parsed[1]["party"], "")
        self.assertEqual(parsed[1]["primary_party"], "Democratic")

    def test_suffolk_final_result_table_parses_candidate_names(self):
        html = """
        <table><tr><td><h2>Representative in Congress, 1st Congressional District
        (Democratic Party) (Elect 1)</h2></td></tr></table>
        <table>
          <tr><th>Candidate</th><th>Party</th><th>Votes</th><th>Share</th></tr>
          <tr><td>Avlon, John P</td><td>Democratic</td><td>19,383</td><td>70%</td></tr>
          <tr><td>Goroff, Nancy S</td><td>Democratic</td><td>8,253</td><td>30%</td></tr>
        </table>
        """
        source = {
            "source_id": "suffolk-test",
            "date": "2024-06-25",
            "district": "01",
            "party": "Democratic",
            "url": "https://example.test/results",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "suffolk.html"
            path.write_text(html)
            parsed = parse_suffolk_results(path, source)
        self.assertEqual(parsed[0]["candidate_name"], "John P Avlon")
        self.assertEqual(parsed[0]["votes"], 19383)

    def test_enr_partial_preserves_reporting_status_without_blank_votes(self):
        sections = []
        for party, district in (
            ("DEM", "3"), ("REP", "3"), ("REP", "4"), ("REP", "19"),
            ("DEM", "21"), ("REP", "21"), ("DEM", "23"), ("DEM", "24"),
            ("DEM", "25"),
        ):
            ordinal = (
                "3rd" if district == "3"
                else "4th" if district == "4"
                else f"{district}th"
            )
            header = (
                f" {party} Primary > {ordinal} Congressional District > All Counties "
                "(Active Enrolled Voters: 1) Election Districts Reporting: 673 of 673"
            )
            sections.append(f"""
{header}
Candidate Party Graph Percent Votes
Robin Wilt\tDEM\t\t29.77 %\t11,516
Joseph D. Morelle\tDEM\t\t62.27 %\t24,085
Blank\t\t\t1.48 %\t573
Void\t\t\t0.20 %\t79
Write-in\t\t\t0.39 %\t151
Total Votes\t38,677
""")
        text = "\n".join(sections)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "enr.txt"
            path.write_text(text)
            rows = parse_ny_enr_partial(path)
        rows = [row for row in rows if row["district"] == "25"]
        self.assertEqual(
            [row["candidate_name"] for row in rows],
            ["Robin Wilt", "Joseph D. Morelle", "Write-in"],
        )
        self.assertEqual(rows[0]["reporting_units"], 673)
        self.assertEqual(rows[0]["_expected_reporting_units"], 673)
        self.assertEqual(rows[2]["party"], "")


if __name__ == "__main__":
    unittest.main()
