import csv
import json
import tempfile
import unittest
from pathlib import Path

from dsa_analysis.analysis import _load_canonical_metrics, analyze
from dsa_analysis.paths import PROCESSED_DIR, REPORT_DIR


class AnalysisTests(unittest.TestCase):
    def test_analysis_generates_caveated_report(self) -> None:
        race_summary = json.loads(
            (PROCESSED_DIR / "race_registry_summary.json").read_text(encoding="utf-8")
        )
        full_text_summary = json.loads(
            (PROCESSED_DIR / "full_text_audit_summary.json").read_text(
                encoding="utf-8"
            )
        )
        stats = analyze()
        report = (REPORT_DIR / "draft.md").read_text(encoding="utf-8")
        self.assertEqual(stats["canonical_races"], race_summary["canonical_races"])
        self.assertEqual(stats["in_scope_races"], race_summary["in_scope_races"])
        self.assertEqual(
            stats["candidate_queue_records"],
            full_text_summary["queue"]["candidate_rows"],
        )
        self.assertIn(
            f'- Canonical races: {race_summary["canonical_races"]}',
            report,
        )
        self.assertIn("## 1. Denominator completeness", report)
        self.assertIn("## 3. Candidate-document coverage", report)
        self.assertIn("## 6. Provisional KDE", report)
        self.assertNotIn("Tracked Democratic primaries: 84", report)
        self.assertIn("mo01-dem-primary-2026", report)

    def test_canonical_summary_ingestion(self) -> None:
        with tempfile.TemporaryDirectory(dir=".") as temp_dir:
            root = Path(temp_dir)
            processed = root / "processed"
            analysis = root / "analysis"
            output = root / "outputs"
            (output / "tables" / "text_analysis").mkdir(parents=True)
            (analysis / "provisional_gte_kde").mkdir(parents=True)
            (analysis / "official_platform_gte_kde").mkdir(parents=True)
            processed.mkdir()

            fixtures = {
                processed / "race_registry_summary.json": {
                    "canonical_races": 10,
                    "in_scope_races": 7,
                    "in_scope_unresolved_races": 2,
                    "valid_official_election_source_rows": 6,
                    "national_candidate_endorsements": 8,
                    "national_endorsements_matched_in_scope": 5,
                    "national_endorsements_absent_from_registry": 1,
                },
                processed / "full_text_audit_summary.json": {
                    "queue": {
                        "candidate_rows": 20,
                        "status_counts": {"verified": 12},
                    },
                    "retryable_gaps": {"candidate_gap_count": 6},
                    "document_corpus": {
                        "substantive_candidate_count": 11,
                        "substantive_document_count": 15,
                        "substantive_segment_rows": 100,
                    },
                    "paired_races": {
                        "clean_document_backed_races": 5,
                        "eligible_count": 3,
                    },
                    "sufficiency": {"decision": "insufficient"},
                },
                processed / "organizational_context_summary.json": {
                    "represented_state_cycles": 4,
                    "inventory": {
                        "row_count": 16,
                        "by_verification_status": {"verified": 9},
                    },
                    "coverage": {"platform_gap_rows": 3},
                },
                processed / "organizational_context_extraction_summary.json": {
                    "fetched_documents": 8,
                    "successful_documents": 7,
                    "extraction_errors": 1,
                },
                output / "tables" / "text_analysis" / "analysis_manifest.json": {
                    "official_documents": 4,
                    "official_documents_by_group": {"dsa": 1, "democratic": 3},
                    "official_source_segments": 40,
                    "official_segments": 38,
                    "candidate_source_documents": 15,
                    "candidate_source_segments": 100,
                    "candidate_segments": 90,
                    "candidate_documents": 13,
                    "sticking_points": 2,
                },
                analysis / "model_topic_validation.json": {
                    "classified_rows": 70,
                    "unclassified_rows": 20,
                },
                analysis / "provisional_gte_kde" / "summary.json": {
                    "status": "provisional",
                    "retained_segments": 88,
                    "candidate_counts": {"endorsed": 4, "opponent": 7},
                    "selected_dimensions": 3,
                    "kde": {"fit_counts": {"endorsed": 40, "opponent": 40}},
                },
                analysis / "official_platform_gte_kde" / "summary.json": {
                    "selected_dimensions": 5,
                    "kde": {"fit_counts": {"dsa": 10, "democratic": 10}},
                },
            }
            for path, payload in fixtures.items():
                path.write_text(json.dumps(payload), encoding="utf-8")

            self._write_csv(
                processed / "race_registry.csv",
                ["scope_kind", "candidate_count"],
                [
                    ["tracked_dsa_endorsed_democratic_primary", "3"],
                    ["tracked_dsa_endorsed_democratic_primary", "2"],
                    ["other_corpus_race", "9"],
                ],
            )
            self._write_csv(
                processed / "local_endorsements_verified.csv",
                ["endorsement_key"],
                [["a"], ["b"]],
            )
            self._write_csv(
                processed / "coverage_ledger.csv",
                ["status"],
                [["verified"], ["not_searched"], ["found_unverified"]],
            )

            result = _load_canonical_metrics(processed, analysis, output)
            self.assertEqual(result["stats"]["in_scope_candidate_records"], 5)
            self.assertEqual(result["stats"]["local_verified_endorsements"], 2)
            self.assertEqual(result["stats"]["local_unresolved_rows"], 2)
            self.assertEqual(result["stats"]["candidate_analysis_segments"], 90)
            self.assertEqual(result["stats"]["kde_status"], "provisional")

    @staticmethod
    def _write_csv(path: Path, fieldnames: list[str], rows: list[list[str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(fieldnames)
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
