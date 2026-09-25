import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.airtable import _endorsement_row, collect_national_endorsements, decode_value
from dsa_analysis.io import read_csv, write_csv


class AirtableTests(unittest.TestCase):
    def test_select_values_are_decoded(self) -> None:
        column = {
            "type": "select",
            "typeOptions": {
                "choices": {"sel1": {"id": "sel1", "name": "Endorsed 2020"}}
            },
        }
        self.assertEqual(decode_value(column, "sel1"), "Endorsed 2020")

    def test_foreign_keys_use_display_names(self) -> None:
        column = {"type": "foreignKey"}
        value = [{"foreignRowId": "rec1", "foreignRowDisplayName": "New York City"}]
        self.assertEqual(decode_value(column, value), ["New York City"])

    def test_refresh_retains_records_removed_from_live_views(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "national_endorsement_archive.csv"
            old = _endorsement_row({
                "record_id": "old", "Campaign": "Former candidate",
                "Election Date": "2016-06-01",
            }, "https://example.org/old")
            write_csv(archive, [old], list(old))
            with (
                patch("dsa_analysis.airtable.PROCESSED_DIR", root),
                patch("dsa_analysis.airtable.RAW_DIR", root),
                patch("dsa_analysis.airtable.fetch_shared_view", return_value={}),
                patch("dsa_analysis.airtable.normalize_table", side_effect=[
                    [{"record_id": "new", "Campaign": "Current candidate",
                      "Election Date": "2026-06-01"}], [],
                ]),
            ):
                self.assertEqual(collect_national_endorsements(), 2)
            rows = {row["record_id"]: row for row in read_csv(archive)}
            self.assertEqual(rows["old"]["source_presence"], "historical_capture_only")
            self.assertEqual(rows["new"]["source_presence"], "latest_official_views")

    def test_failed_refresh_does_not_overwrite_prior_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prior = root / "national-endorsements-past.json"
            prior.write_text('{"prior": true}')
            with (
                patch("dsa_analysis.airtable.PROCESSED_DIR", root),
                patch("dsa_analysis.airtable.RAW_DIR", root),
                patch("dsa_analysis.airtable.fetch_shared_view",
                      side_effect=[{}, ValueError("upstream failure")]),
                patch("dsa_analysis.airtable.normalize_table", return_value=[]),
            ):
                with self.assertRaises(ValueError):
                    collect_national_endorsements()
            self.assertEqual(prior.read_text(), '{"prior": true}')


if __name__ == "__main__":
    unittest.main()
