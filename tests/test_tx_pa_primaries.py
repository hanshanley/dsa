import base64
import csv
import json
import tempfile
import unittest
from pathlib import Path

from dsa_analysis.tx_pa_primaries import (
    parse_pennsylvania,
    parse_texas_api,
    parse_texas_canvass,
)


class TexasPennsylvaniaPrimaryTests(unittest.TestCase):
    def test_texas_primary_canvass_maps_truncated_name_and_page_spanning_race(self):
        source = {
            "source_id": "tx-test-primary",
            "date": "2024-03-05",
            "stage": "primary",
            "party": "Democratic",
            "party_code": "DEM",
            "election_id": "1",
            "report_name": "OfficialCanvassReport.pdf",
        }
        federal = {
            "OffType": "FEDERAL OFFICES",
            "OffTypeID": 1,
            "Races": [
                {
                    "id": 37,
                    "N": "U. S. REPRESENTATIVE DISTRICT 37",
                    "Candidates": [
                        {
                            "ID": 10,
                            "N": 'CHRISTOPHER "CHRIS" MCNERNEY',
                            "P": "DEM",
                            "V": 0,
                        },
                        {
                            "ID": 11,
                            "N": 'EDUARDO "LALITO" ROMERO',
                            "P": "DEM",
                            "V": 0,
                        },
                    ],
                },
            ],
        }
        text = """
\fPAGE 1
U. S. REPRESENTATIVE DISTRICT 37 1,000 10 %
CHRISTOPHER "CHRIS" DEM 5,279 56.62 %
\fPAGE 2
EDUARDO "LALITO" ROMERO DEM 4,048 43.38 %
9,327Total Votes
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text_path = root / "canvass.txt"
            pdf_path = root / "canvass.pdf"
            json_path = root / "Federal.json"
            text_path.write_text(text)
            pdf_path.write_bytes(b"official pdf bytes")
            json_path.write_text(json.dumps(federal))
            rows = parse_texas_canvass(text_path, pdf_path, json_path, source)
        self.assertEqual(
            [row["candidate_name"] for row in rows],
            ['CHRISTOPHER "CHRIS" MCNERNEY', 'EDUARDO "LALITO" ROMERO'],
        )
        self.assertEqual([row["votes"] for row in rows], [5279, 4048])
        self.assertTrue(rows[1]["source_locators"].startswith("canvass.pdf:page-2"))

    def test_texas_runoff_uses_pdf_totals_when_companion_json_is_zero(self):
        source = {
            "source_id": "tx-test-runoff",
            "date": "2024-05-28",
            "stage": "primary_runoff",
            "party": "Democratic",
            "party_code": "DEM",
            "election_id": "2",
            "report_name": "CountybyCountyCanvassReport.pdf",
        }
        federal = {
            "OffType": "FEDERAL OFFICES",
            "OffTypeID": 1,
            "Races": [
                {
                    "id": 31,
                    "N": "U. S. REPRESENTATIVE DISTRICT 31",
                    "Candidates": [
                        {"ID": 20, "N": "BRIAN WALBRIDGE", "P": "DEM", "V": 0},
                        {"ID": 21, "N": "STUART WHITLOW", "P": "DEM", "V": 0},
                    ],
                },
            ],
        }
        text = """
\fPAGE 1
U. S. REPRESENTATIVE DISTRICT 31
County
BRIAN
WALBRIDGE
[DEM]
STUART
WHITLOW
[DEM] Total Votes
BELL 279 490 769
TOTAL VOTES 1,614 3,512 5,126
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text_path = root / "runoff.txt"
            pdf_path = root / "runoff.pdf"
            json_path = root / "Federal.json"
            text_path.write_text(text)
            pdf_path.write_bytes(b"official runoff pdf")
            json_path.write_text(json.dumps(federal))
            rows = parse_texas_canvass(text_path, pdf_path, json_path, source)
        self.assertEqual([row["votes"] for row in rows], [1614, 3512])
        self.assertEqual({row["stage"] for row in rows}, {"primary_runoff"})

    def test_texas_api_preserves_actual_zero(self):
        source = {
            "source_id": "tx-test-api",
            "date": "2026-03-03",
            "stage": "primary",
            "party": "Republican",
            "party_code": "REP",
            "election_id": "3",
            "expected_house_districts": {1},
            "expected_senate": False,
        }
        home = {
            "ElecDate": "03032026",
            "CountiesReporting": {"CR": 254, "CT": 254},
            "LastUpdatedTime": "Apr 14, 2026 20:48:17",
        }
        federal = {
            "Races": [
                {
                    "id": 1,
                    "N": "U. S. REPRESENTATIVE DISTRICT 1",
                    "Candidates": [
                        {"ID": 30, "N": "ZERO CANDIDATE", "P": "REP", "V": 0},
                        {"ID": 31, "N": "ONE CANDIDATE", "P": "REP", "V": 1},
                    ],
                    "T": 1,
                },
            ],
        }
        payload = {
            "Home": base64.b64encode(json.dumps(home).encode()).decode(),
            "Federal": base64.b64encode(json.dumps(federal).encode()).decode(),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "election.json"
            path.write_text(json.dumps(payload))
            rows = parse_texas_api(path, source)
        self.assertEqual([row["votes"] for row in rows], [0, 1])
        self.assertTrue(rows[0]["source_locators"].endswith("Candidates[0]"))

    def test_pennsylvania_repairs_unquoted_municipality_and_preserves_zero(self):
        source = {
            "source_id": "pa-test",
            "date": "2024-04-23",
            "stage": "primary",
            "url": "https://example.test/pa",
            "expected_house_districts": {1},
            "expected_senate": False,
        }
        rows = []
        for precinct, votes in (("10.0", "0.0"), ("20.0", "5.0")):
            row = [
                "2024.0", "P", "36.0", precinct, "8.0", "1.0", "1.0", "1.0",
                "USC", "DEM", "2024C0001", "EXAMPLE", "ALICE", "B", "JR",
                votes, "0.0", "0.0", "1.0", "1.0", "1.0", "4.0",
                "MANOR X MANOR", "NEW", "X", "", "", "", "0.0", "175.0",
                "71.0", "1402.0", "", "", "0.0", "1.0", "1.0", "1.0",
            ]
            rows.append(row)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pa.txt"
            with path.open("w", newline="") as handle:
                csv.writer(handle).writerows(rows)
            parsed = parse_pennsylvania(path, source)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["candidate_name"], "ALICE B EXAMPLE JR")
        self.assertEqual(parsed[0]["votes"], 5)
        self.assertEqual(parsed[0]["reporting_units"], 2)
        self.assertEqual(parsed[0]["source_locators"], "pa.txt:1-2")


if __name__ == "__main__":
    unittest.main()
