import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.congressional_reconciliation import reconcile_dsa_congressional
from dsa_analysis.io import read_csv, write_csv


class CongressionalReconciliationTests(unittest.TestCase):
    def test_verified_return_flags_stale_district_without_mutating_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = [{
                "race_id": "old", "office": "US House", "election_year": "2026",
                "state_code": "CO", "endorsed_candidates": "", "endorsed_candidate": "Jane Example",
                "election_date": "2026-06-30", "jurisdiction": "District 2",
            }]
            results = [{
                "cycle": "2026", "state_code": "CO", "chamber": "House", "candidate_name": "Jane Example",
                "stage": "primary", "write_in": "false", "source_id": "official",
                "contest_id": "district-1", "candidate_source_id": "jane",
                "election_date": "2026-06-30", "district": "01",
                "source_url": "https://example.gov/results",
            }]
            write_csv(root / "race_registry.csv", registry, list(registry[0]))
            write_csv(root / "state_primary_results.csv", results, list(results[0]))
            before = (root / "race_registry.csv").read_bytes()
            with patch("dsa_analysis.congressional_reconciliation.PROCESSED_DIR", root):
                summary = reconcile_dsa_congressional(root)
            self.assertEqual(summary["dsa_congressional_review_required"], 1)
            row = read_csv(root / "dsa_registry_reconciliation.csv")[0]
            self.assertEqual(row["issues"], "registry_district_differs")
            self.assertEqual(row["matched_districts"], "01")
            self.assertEqual((root / "race_registry.csv").read_bytes(), before)

    def test_matching_requires_chamber_and_every_endorsed_candidate(self):
        for chamber, candidates, issue in [
            ("Senate", "", "no_exact_name_match_in_recovered_returns"),
            ("House", "Jane Example | Other Candidate", "some_endorsed_candidates_not_matched"),
        ]:
            with self.subTest(chamber=chamber), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                registry = [{
                    "race_id": "race", "office": "US House", "election_year": "2026",
                    "state_code": "CO", "endorsed_candidates": candidates,
                    "endorsed_candidate": "Jane Example", "election_date": "2026-06-30",
                    "jurisdiction": "District 1",
                }]
                results = [{
                    "cycle": "2026", "state_code": "CO", "chamber": chamber,
                    "candidate_name": "Jane Example", "stage": "primary", "write_in": "false",
                    "source_id": "official", "contest_id": "contest", "candidate_source_id": "jane",
                    "election_date": "2026-06-30", "district": "01",
                    "source_url": "https://example.gov/results",
                }]
                write_csv(root / "race_registry.csv", registry, list(registry[0]))
                write_csv(root / "state_primary_results.csv", results, list(results[0]))
                with patch("dsa_analysis.congressional_reconciliation.PROCESSED_DIR", root):
                    summary = reconcile_dsa_congressional(root)
                self.assertEqual(summary["dsa_congressional_review_required"], 1)
                row = read_csv(root / "dsa_registry_reconciliation.csv")[0]
                self.assertEqual(row["issues"], issue)
                self.assertTrue(row["unmatched_registry_candidates"])


if __name__ == "__main__":
    unittest.main()
