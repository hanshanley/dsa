import csv
import tempfile
import unittest
from pathlib import Path

from dsa_analysis.nomination_followup import (
    TARGET_KEYS,
    build_accounting_updates,
    generate,
    parse_arkansas_2024_notice,
    parse_arkansas_2026_roster,
    parse_kentucky_house_filings,
    parse_south_dakota_2024,
    parse_south_dakota_2026,
)
from dsa_analysis.paths import ANALYSIS_DATA_DIR, RAW_DIR


class NominationFollowupTests(unittest.TestCase):
    def test_arkansas_official_sources_preserve_unresolved_numeric_unit(self):
        raw = RAW_DIR / "nomination_followup"
        notice = parse_arkansas_2024_notice(
            raw / "ar/2024/pulaski-2024-primary-amended-notice.txt"
        )
        self.assertEqual(notice[("01", "Democratic")], "Rodney Govens")
        self.assertEqual(notice[("04", "Republican")], "Congressman Bruce Westerman")
        roster = parse_arkansas_2026_roster(
            raw / "ar/2026/ar-2026-candidate-roster.json"
        )
        self.assertEqual(roster[("03", "Democratic")], ["Robb Ryerse"])
        self.assertEqual(roster[("03", "Republican")], ["Congressman Steve Womack"])

        updates = build_accounting_updates(
            RAW_DIR,
            ANALYSIS_DATA_DIR / "congressional/party_contest_accounting.csv",
        )
        by_key = {
            (
                row["cycle"],
                row["state_code"],
                row["chamber"],
                row["district"],
                row["primary_party"],
            ): row
            for row in updates
        }
        unresolved = by_key[("2024", "AR", "House", "03", "Democratic")]
        self.assertEqual(unresolved["status"], "unresolved")
        self.assertIn("numeric primary", unresolved["notes"])

    def test_kentucky_active_withdrawn_and_no_candidate_units(self):
        raw = RAW_DIR / "nomination_followup"
        rows_2024 = parse_kentucky_house_filings(
            raw / "ky/2024/ky-2024-us-house-candidate-filings.html"
        )
        rows_2026 = parse_kentucky_house_filings(
            raw / "ky/2026/ky-2026-us-house-candidate-filings.html"
        )
        self.assertFalse(
            [
                row
                for row in rows_2024["active"]
                if row["district"] == "04" and row["party"] == "Democratic"
            ]
        )
        self.assertEqual(
            [
                row["name"]
                for row in rows_2026["active"]
                if row["district"] == "03" and row["party"] == "Democratic"
            ],
            ["Morgan McGarvey"],
        )
        self.assertEqual(
            [
                row["name"]
                for row in rows_2026["withdrawn"]
                if row["district"] == "03" and row["party"] == "Democratic"
            ],
            ["Jared Randall"],
        )

    def test_south_dakota_exhaustive_lists(self):
        raw = RAW_DIR / "nomination_followup"
        rows_2024 = parse_south_dakota_2024(
            raw / "sd/2024/sd-2024-primary-candidates.csv"
        )
        rows_2026 = parse_south_dakota_2026(
            raw / "sd/2026/sd-2026-primary-candidates.html"
        )
        self.assertEqual(rows_2024[("00", "Democratic")], ["Sheryl Johnson"])
        self.assertEqual(rows_2024[("00", "Republican")], ["Dusty Johnson"])
        self.assertEqual(
            rows_2026[("00", "Democratic")],
            ['Nicole "Nikki" Gronli'],
        )
        self.assertEqual(rows_2026[("S", "Democratic")], ["Julian Beaudion"])

    def test_generated_ledger_has_exact_keys_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            analysis_root = Path(directory)
            updates = generate(
                RAW_DIR,
                analysis_root,
                ANALYSIS_DATA_DIR / "congressional/party_contest_accounting.csv",
            )
            keys = {
                (
                    row["cycle"],
                    row["state_code"],
                    row["chamber"],
                    row["district"],
                    row["primary_party"],
                )
                for row in updates
            }
            self.assertEqual(keys, TARGET_KEYS)
            self.assertEqual(len(updates), 25)
            self.assertEqual(
                sum(row["status"] == "unresolved" for row in updates),
                1,
            )
            self.assertTrue(
                all(
                    row["status"] == "unresolved"
                    or (row["source_urls"] and row["locators"])
                    for row in updates
                )
            )

            output = (
                analysis_root
                / "congressional/nomination_followup"
                / "raw_artifacts.csv"
            )
            with output.open(newline="", encoding="utf-8") as handle:
                artifacts = list(csv.DictReader(handle))
            self.assertTrue(artifacts)
            self.assertTrue(all(row["sha256"] and int(row["bytes"]) > 0 for row in artifacts))
            self.assertFalse(any("blocked" in row["path"].lower() for row in artifacts))


if __name__ == "__main__":
    unittest.main()
