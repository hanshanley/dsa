import csv
import gzip
import tempfile
import unittest
from pathlib import Path

from dsa_analysis.northeast_primaries import (
    parse_connecticut,
    parse_maryland,
    parse_massachusetts,
)


class NortheastPrimaryTests(unittest.TestCase):
    def test_massachusetts_parses_named_and_aggregate_write_ins(self):
        html = """
        <tr class="election_item" id="election-id-1">
        <td>2024</td><td>U.S. House</td><td>1st Congressional</td>
        <td>Democratic Primary</td><td class="candidates_container_cell">
        <table class="candidates"><tbody>
        <tr><td class="candidate"><div class="name"><a href="/candidates/view/A">
        Example Candidate</a></div></td><td class="number">100</td></tr>
        <tr class="non_candidate n_all_other_votes"><td class="candidate">
        All Others</td><td class="number">3</td></tr>
        </tbody></table></td></tr>
        """
        source = {"source_id": "ma-test", "date": "2024-09-03", "url": "x"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ma.html"
            path.write_text(html)
            with self.assertRaises(ValueError):
                parse_massachusetts(path, source)

    def test_connecticut_uses_city_town_not_polling_place_rows(self):
        fields = [
            "contest_id", "election_date", "election_type", "primary_party",
            "office_name", "district_name", "candidate_id", "candidate_name",
            "division_id", "division_type", "vote_channel", "candidate_party_name",
            "votes",
        ]
        rows = []
        for division_type, division_id, votes in (
            ("City/Town", "town", "10"), ("Polling Place", "poll", "10"),
        ):
            rows.append(dict(zip(fields, [
                "1", "2024-08-13T00:00:00Z", "Primary", "Republican",
                "Representative in Congress", "4", "a", "Candidate A",
                division_id, division_type, "Election Day", "Republican", votes,
            ], strict=True)))
        source = {"source_id": "ct-test", "date": "2024-08-13", "url": "x"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ct.csv.gz"
            with gzip.open(path, "wt", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            parsed = parse_connecticut(path, source)
        self.assertEqual(parsed[0]["votes"], 10)
        self.assertEqual(parsed[0]["reporting_units"], 1)

    def test_maryland_sums_senate_district_columns_once(self):
        header = [
            "County", "County Name", "Office Name", "Office District",
            "Candidate Name", "Party", "Winner",
            *[f"Congressional District {value}" for value in range(1, 9)],
        ]
        source = {
            "source_id": "md-test", "date": "2024-05-14",
            "party": "Democratic", "url": "x",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "md.csv"
            with path.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(header)
                writer.writerow([
                    "00", "State", "U.S. Senator", "", "Candidate", "DEM", "Y",
                    *range(1, 9),
                ])
            parsed = parse_maryland(path, source)
        self.assertEqual(parsed[0]["votes"], 36)


if __name__ == "__main__":
    unittest.main()
