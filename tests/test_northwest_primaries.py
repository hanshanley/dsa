import unittest
import csv

from dsa_analysis.paths import ANALYSIS_DATA_DIR
from dsa_analysis.northwest_primaries import (
    OR_2024_RESULTS,
    collect_northwest_primaries,
    export_party_contest_accounting,
    export_provider_raw_artifacts,
    parse_idaho_2024,
    parse_idaho_2026,
    parse_nm_2026,
    parse_oregon_2026,
    validate_oregon_2026_split_archive,
)
from dsa_analysis.paths import RAW_DIR
from dsa_analysis.state_results import FIELDS


class NorthwestPrimaryTests(unittest.TestCase):
    def test_idaho_2024_preserves_all_four_party_primaries(self):
        rows = parse_idaho_2024(RAW_DIR / "northwest_primaries")
        self.assertEqual(len(rows), 11)
        self.assertEqual(
            {row["primary_party"] for row in rows},
            {"Constitution", "Democratic", "Libertarian", "Republican"},
        )
        self.assertEqual({row["district"] for row in rows}, {"01", "02"})

    def test_new_mexico_2026_preserves_write_in_and_all_federal_contests(self):
        rows = parse_nm_2026(RAW_DIR / "northwest_primaries")
        self.assertEqual(len(rows), 10)
        self.assertEqual(len({row["contest_id"] for row in rows}), 8)
        write_ins = [row for row in rows if row["write_in"]]
        self.assertEqual(
            [(row["candidate_name"], row["votes"]) for row in write_ins],
            [("LARRY E MARKER", 31220)],
        )

    def test_idaho_2026_uses_current_certified_canvass(self):
        rows = parse_idaho_2026(RAW_DIR / "northwest_primaries")
        self.assertEqual(len(rows), 19)
        self.assertEqual(len({row["contest_id"] for row in rows}), 8)
        self.assertEqual(
            sum(row["votes"] for row in rows if row["candidate_name"] == "Jim Risch"),
            156140,
        )

    def test_oregon_2024_preserves_miscellaneous_write_in_options(self):
        self.assertEqual(len(OR_2024_RESULTS), 12)
        self.assertEqual(
            sum(
                write_in
                for candidates in OR_2024_RESULTS.values()
                for _, _, write_in in candidates
            ),
            12,
        )

    def test_collection_matches_canonical_schema(self):
        summary = collect_northwest_primaries()
        self.assertEqual(summary["candidate_rows"], 142)
        self.assertEqual(summary["contests"], 58)
        self.assertEqual(summary["remaining_gaps"], 1)
        self.assertEqual(len(FIELDS), 20)
        path = ANALYSIS_DATA_DIR / "congressional" / "northwest_primary_results.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            persisted = list(csv.DictReader(handle))
        self.assertEqual(len(persisted), 142)
        self.assertEqual(len({row["contest_id"] for row in persisted}), 58)
        self.assertFalse(list(path.parent.glob(f".{path.name}.*.tmp")))

    def test_oregon_2026_reconciles_all_counties_and_lincoln(self):
        rows = parse_oregon_2026(RAW_DIR / "northwest_primaries")
        self.assertEqual(len(rows), 51)
        self.assertEqual(len({row["contest_id"] for row in rows}), 14)
        self.assertEqual(
            sum(row["votes"] for row in rows if row["contest_id"].endswith("senate-s-regular-democratic")),
            490457,
        )

    def test_party_accounting_distinguishes_results_nominations_and_gaps(self):
        rows = export_party_contest_accounting(
            RAW_DIR.parent / "analysis" / "congressional"
        )
        by_key = {
            (
                row["cycle"], row["state_code"], row["chamber"],
                row["district"], row["primary_party"],
            ): row
            for row in rows
        }
        self.assertEqual(
            by_key[("2026", "UT", "House", "04", "Republican")]["status"],
            "unopposed_nomination_verified",
        )
        self.assertEqual(
            by_key[("2024", "NV", "House", "01", "Democratic")]["candidate_names"],
            "Dina Titus",
        )
        self.assertEqual(
            by_key[("2024", "NV", "House", "02", "Democratic")]["status"],
            "unresolved",
        )
        self.assertEqual(
            by_key[("2024", "AK", "House", "00", "")]["status"],
            "results_complete",
        )
        self.assertEqual(
            by_key[("2026", "NV", "House", "01", "Democratic")]["status"],
            "results_partial",
        )

    def test_provider_raw_artifacts_are_existing_nonempty_verified_inputs(self):
        rows = export_provider_raw_artifacts(
            RAW_DIR.parent / "analysis" / "congressional"
        )
        self.assertTrue(rows)
        for row in rows:
            path = RAW_DIR.parent.parent / row["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(path.stat().st_size, int(row["bytes"]))
            self.assertGreater(int(row["bytes"]), 0)
            self.assertEqual(len(row["sha256"]), 64)
        paths = {row["path"] for row in rows}
        self.assertNotIn(
            "data/raw/northwest_primaries/or/2026/"
            "or-2026-primary-county-results.zip",
            paths,
        )
        self.assertNotIn(
            "data/raw/northwest_primaries/or/2026/"
            "or-2026-primary-county-results.zip.gz",
            paths,
        )
        part_rows = [
            row for row in rows
            if row["artifact_type"] == "official_records_archive_zip_gzip_part"
        ]
        self.assertEqual(len(part_rows), 2)
        self.assertTrue(all(int(row["bytes"]) < 100 * 1024 * 1024 for row in part_rows))

    def test_oregon_split_archive_reconstructs_original_download(self):
        raw_root = RAW_DIR / "northwest_primaries"
        metadata = validate_oregon_2026_split_archive(raw_root)
        self.assertEqual(metadata["gzip_mtime"], 0)
        self.assertEqual(
            metadata["original_sha256"],
            "bf6b2a450e1667f6d479bbb8c68a8ff7ea7358491861227e6409d85b00f83ca9",
        )
        self.assertEqual(metadata["original_bytes"], 178804397)
        first_part = (
            raw_root / "or/2026" / metadata["parts"][0]["filename"]
        ).read_bytes()[:10]
        self.assertEqual(first_part[:2], b"\x1f\x8b")
        self.assertEqual(int.from_bytes(first_part[4:8], "little"), 0)


if __name__ == "__main__":
    unittest.main()
