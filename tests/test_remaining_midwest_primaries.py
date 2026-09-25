import csv
import tempfile
import unittest
from pathlib import Path

from dsa_analysis.remaining_midwest_primaries import (
    ACCOUNTING_FIELDS,
    PARTY_CONTEST_FIELDS,
    export_party_contest_accounting,
    parse_indiana_2024,
    parse_minnesota_senate,
)
from dsa_analysis.state_results import FIELDS


class RemainingMidwestTests(unittest.TestCase):
    def test_indiana_filters_state_legislative_rows(self):
        rows = [
            ["County", "Office", "Candidate", "Party", "District", "Votes"],
            ["", "US Representative", "House Candidate", "Democratic", "01", "100"],
            ["", "US Senator", "Senate Candidate", "Republican", "1, 2", "200"],
            ["", "State Senator", "State Candidate", "Republican", "01", "300"],
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "in.csv"
            with path.open("w", newline="") as handle:
                csv.writer(handle).writerows(rows)
            with self.assertRaises(ValueError):
                parse_indiana_2024(path)

    def test_minnesota_senate_keeps_ballot_party_category(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mn.csv"
            path.write_text(
                "cycle,election_date,primary_party,candidate_name,votes,"
                "source_url,source_locator\n"
                "2026,2026-08-11,Republican,Example,10,https://example.test,line-1\n"
            )
            rows = parse_minnesota_senate(path)
        self.assertEqual(rows[0]["primary_party"], "Republican")
        self.assertEqual(rows[0]["votes"], 10)

    def test_canonical_accounting_does_not_infer_unopposed_from_one_result(self):
        with tempfile.TemporaryDirectory() as directory:
            analysis = Path(directory)
            (analysis / "remaining_midwest").mkdir()
            result = dict.fromkeys(FIELDS, "")
            result.update({
                "contest_id": "in-test", "cycle": "2024",
                "election_date": "2024-05-07", "stage": "primary",
                "state_code": "IN", "chamber": "House", "district": "01",
                "term": "regular", "election_system": "partisan_primary",
                "primary_party": "Democratic", "candidate_name": "Only Candidate",
                "candidate_source_id": "one", "party": "Democratic",
                "write_in": "False", "votes": "100", "source_id": "in-test",
                "source_url": "https://example.test/results",
                "source_sha256": "abc", "source_locators": "results.csv:2",
                "reporting_units": "1",
            })
            with (analysis / "remaining_midwest_primary_results.csv").open(
                "w", newline="",
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerow(result)
            accounting = [
                {
                    "cycle": "2024", "state_code": "IN", "chamber": "House",
                    "district": "01", "term": "regular",
                    "primary_party": "Democratic",
                    "status": "complete_unopposed_result", "candidate_rows": "1",
                    "source_ids": "in-test", "notes": "",
                },
                {
                    "cycle": "2024", "state_code": "MA", "chamber": "House",
                    "district": "01", "term": "regular",
                    "primary_party": "Republican",
                    "status": "official_no_candidates", "candidate_rows": "0",
                    "source_ids": "ma-2024-primary",
                    "notes": "Explicit No Candidates label.",
                },
            ]
            with (analysis / "remaining_midwest" / "contest_accounting.csv").open(
                "w", newline="",
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=ACCOUNTING_FIELDS)
                writer.writeheader()
                writer.writerows(accounting)
            output = analysis / "remaining_midwest" / "party_contest_accounting.csv"
            rows = export_party_contest_accounting(analysis, output)
        self.assertEqual(set(rows[0]), set(PARTY_CONTEST_FIELDS))
        statuses = {
            (row["state_code"], row["primary_party"]): row["status"]
            for row in rows
        }
        self.assertEqual(statuses[("IN", "Democratic")], "results_complete")
        self.assertEqual(statuses[("MA", "Republican")], "no_candidate_verified")


if __name__ == "__main__":
    unittest.main()
