import io
import unittest
from datetime import datetime

from openpyxl import Workbook

from dsa_analysis.fec_presidential import (
    parse_2016_presidential_primaries,
    parse_2020_presidential_primaries,
)


class FECPresidentialTests(unittest.TestCase):
    def test_parses_only_democratic_contests_with_sanders(self) -> None:
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "2016 Pres Primary Results"
        worksheet.append(
            [
                "row",
                "FEC ID",
                "STATE",
                "STATE ABBREVIATION",
                "PRIMARY DATE",
                "FIRST NAME",
                "LAST NAME",
                "LAST NAME, FIRST",
                "TOTAL VOTES",
                "PARTY",
                "PRIMARY RESULTS",
                "PRIMARY %",
                "FOOTNOTES",
            ]
        )
        worksheet.append(
            [1, "a", "Test State", "TS", datetime(2016, 3, 1), "Bernie", "Sanders",
             "Sanders, Bernie", None, "D", 60, 0.6, None]
        )
        worksheet.append(
            [2, "b", "Test State", "TS", datetime(2016, 3, 1), "Hillary", "Clinton",
             "Clinton, Hillary", None, "D", 40, 0.4, None]
        )
        output = io.BytesIO()
        workbook.save(output)

        endorsements, candidates = parse_2016_presidential_primaries(output.getvalue())

        self.assertEqual(len(endorsements), 1)
        self.assertEqual(endorsements[0]["race_id"], "us-president-dem-primary-2016-ts")
        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            {row["role"] for row in candidates},
            {"endorsed", "opponent"},
        )

    def test_parses_2020_sheet_and_ids(self) -> None:
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "10. 2020 Pres Primary Results"
        worksheet.append(["row", "FEC ID", "STATE", "STATE ABBREVIATION",
                          "PRIMARY DATE", "FIRST NAME", "LAST NAME",
                          "LAST NAME, FIRST", "TOTAL VOTES", "PARTY",
                          "PRIMARY RESULTS", "PRIMARY %", "RCV"])
        worksheet.append(
            [1, "a", "Test State", "TS", datetime(2020, 3, 3), "Bernie", "Sanders",
             "Sanders, Bernie", None, "D", 40, 0.4, None]
        )
        worksheet.append(
            [2, "b", "Test State", "TS", datetime(2020, 3, 3), "Joseph R.", "Biden",
             "Biden, Joseph R.", None, "D", 60, 0.6, None]
        )
        output = io.BytesIO()
        workbook.save(output)

        endorsements, candidates = parse_2020_presidential_primaries(output.getvalue())

        self.assertEqual(endorsements[0]["race_id"], "us-president-dem-primary-2020-ts")
        self.assertEqual(len(candidates), 2)
