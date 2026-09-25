import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from dsa_analysis.nj_fl_primaries import (
    _coverage_rows,
    parse_florida_roster,
    parse_florida_summary,
    parse_new_jersey,
)


class NewJerseyFloridaPrimaryTests(unittest.TestCase):
    def test_florida_summary_parses_special_senate_and_recount_house(self):
        source = {
            "source_id": "fl-test",
            "date": "2026-08-18",
            "stage": "primary",
            "party": "Republican",
            "party_code": "REP",
        }
        html = """
        <html><body>
        <p>August 18, 2026 Primary Election</p>
        <p>Official Results</p>
        <table>
          <tr><td>United States Senator</td></tr>
          <tr><td></td><td>Candidate One</td><td>Candidate Two</td></tr>
          <tr><td>Total</td><td>0</td><td>5</td></tr>
        </table>
        <table>
          <tr><td>District: 11</td></tr>
          <tr><td></td><td>House One</td><td>House Two</td></tr>
          <tr><td>Total</td><td>3</td><td>4</td></tr>
          <tr><td>Machine Recount Completed</td></tr>
        </table>
        </body></html>
        """
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.html"
            path.write_text(html)
            rows = parse_florida_summary(path, source)
        self.assertEqual([row["votes"] for row in rows], [0, 5, 3, 4])
        self.assertEqual(rows[0]["chamber"], "Senate")
        self.assertEqual(rows[0]["term"], "special")
        self.assertEqual(rows[2]["district"], "11")
        self.assertEqual(rows[2]["term"], "regular")

    def test_florida_roster_separates_unopposed_from_no_candidate(self):
        fields = [
            "AcctNum", "OfficeCode", "Juris1num", "StatusCode", "StatusDesc",
            "PartyCode", "NameLast", "NameFirst", "NameMiddle",
        ]
        records = [
            {
                "AcctNum": "1",
                "OfficeCode": "USR",
                "Juris1num": "001",
                "StatusCode": "UNO",
                "StatusDesc": "Unopposed",
                "PartyCode": "DEM",
                "NameLast": "Example",
                "NameFirst": "Alice",
                "NameMiddle": "",
            },
            {
                "AcctNum": "2",
                "OfficeCode": "USR",
                "Juris1num": "002",
                "StatusCode": "QUA",
                "StatusDesc": "Qualified",
                "PartyCode": "REP",
                "NameLast": "Candidate",
                "NameFirst": "Bob",
                "NameMiddle": "Q",
            },
            {
                "AcctNum": "3",
                "OfficeCode": "USR",
                "Juris1num": "003",
                "StatusCode": "DNQ",
                "StatusDesc": "Did Not Qualify",
                "PartyCode": "DEM",
                "NameLast": "Missing",
                "NameFirst": "Carol",
                "NameMiddle": "",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidates.tsv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=fields,
                    delimiter="\t",
                )
                writer.writeheader()
                writer.writerows(records)
            roster, missing = parse_florida_roster(path, set())
        roster_by_unit = {
            (row["district"], row["primary_party"]): row for row in roster
        }
        self.assertEqual(
            roster_by_unit[("01", "Democratic")]["verification_status"],
            "official_database_unopposed_status",
        )
        self.assertEqual(
            roster_by_unit[("02", "Republican")]["candidate_name"],
            "Bob Q Candidate",
        )
        self.assertEqual(
            missing[("House", "03", "Democratic")],
            "no_qualified_party_candidate",
        )

    def test_new_jersey_special_primary_hashes_pdf_and_preserves_stage(self):
        fields = [
            "source_pdf", "page", "total_page", "chamber", "district",
            "primary_party", "candidate_name", "candidate_source_id",
            "write_in", "votes",
        ]
        record = {
            "source_pdf": (
                "2026-official-special-primary-results-us-house-11cd.pdf"
            ),
            "page": "1",
            "total_page": "2",
            "chamber": "House",
            "district": "11",
            "primary_party": "Democratic",
            "candidate_name": "EXAMPLE CANDIDATE",
            "candidate_source_id": "candidate-1",
            "write_in": "False",
            "votes": "10",
        }
        with tempfile.TemporaryDirectory() as directory:
            raw_root = Path(directory)
            pdf_dir = raw_root / "nj" / "2026"
            pdf_dir.mkdir(parents=True)
            pdf_path = pdf_dir / record["source_pdf"]
            pdf_path.write_bytes(b"official pdf")
            extraction = pdf_dir / "extraction.csv"
            with extraction.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(record)
            rows = parse_new_jersey(extraction, raw_root)
        self.assertEqual(rows[0]["stage"], "special_primary")
        self.assertEqual(rows[0]["term"], "special")
        self.assertFalse(rows[0]["write_in"])
        self.assertEqual(
            rows[0]["source_sha256"],
            hashlib.sha256(b"official pdf").hexdigest(),
        )

    def test_coverage_marks_result_roster_and_absent_units_separately(self):
        results = [
            {
                "state_code": "NJ",
                "election_date": "2026-06-02",
                "stage": "primary",
                "chamber": "House",
                "district": "01",
                "primary_party": "Democratic",
                "source_id": "result",
            },
        ]
        rosters = [
            {
                "state_code": "NJ",
                "election_date": "2026-06-02",
                "stage": "primary",
                "chamber": "House",
                "district": "12",
                "primary_party": "Republican",
                "source_id": "roster",
            },
        ]
        coverage = _coverage_rows(
            results,
            rosters,
            {("House", "10", "Republican"): "no_qualified_party_candidate"},
        )
        by_key = {
            (
                row["state_code"],
                row["election_date"],
                row["chamber"],
                row["district"],
                row["primary_party"],
            ): row
            for row in coverage
        }
        self.assertEqual(
            by_key[("NJ", "2026-06-02", "House", "01", "Democratic")][
                "coverage_status"
            ],
            "actual_results",
        )
        self.assertEqual(
            by_key[("NJ", "2026-06-02", "House", "12", "Republican")][
                "coverage_status"
            ],
            "unopposed_roster_only",
        )
        self.assertEqual(
            by_key[("FL", "2026-08-18", "House", "10", "Republican")][
                "coverage_status"
            ],
            "no_qualified_party_candidate",
        )


if __name__ == "__main__":
    unittest.main()
