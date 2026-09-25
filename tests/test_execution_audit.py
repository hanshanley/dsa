import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from dsa_analysis.execution_audit import input_check, write_execution_audit
from dsa_analysis.document_corpus import CANDIDATE_SCREENING_VERSION
from dsa_analysis.io import write_csv


class ExecutionAuditTests(unittest.TestCase):
    def test_unrecorded_missing_and_changed_inputs_are_not_current(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input"
            source.write_text("original")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(input_check(root, {"input": digest})["status"], "current")
            self.assertEqual(input_check(root, {})["status"], "stale_or_missing")
            self.assertEqual(input_check(root, {"input": None})["status"], "stale_or_missing")
            source.write_text("changed")
            self.assertEqual(input_check(root, {"input": digest})["status"], "stale_or_missing")
            self.assertEqual(input_check(root, {"missing": digest})["status"], "stale_or_missing")

    def test_receipt_separates_execution_coverage_and_stale_pilots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            analysis = root / "data/analysis"
            policy = analysis / "policy_evidence"
            (root / "report").mkdir()

            def csv(name, rows):
                write_csv(root / name, rows, list(rows[0]))

            def save(name, value):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))

            def digest(name):
                return hashlib.sha256((root / name).read_bytes()).hexdigest()

            corpus = "data/analysis/candidate_text_corpus.csv"
            segments = "data/processed/candidate_document_analysis_segments.csv"
            metadata = "data/processed/candidate_document_metadata.csv"
            registry = "data/processed/race_registry.csv"
            endorsements = "data/manual/endorsements.csv"
            output = "data/analysis/model_topic_classifications.csv"
            csv(corpus, [{"corpus_segment_id": "a", "text_sha256": "abc", "text": "policy"}])
            csv(output, [{
                "corpus_segment_id": "a", "text_sha256": "abc", "text": "policy", "topic_code": "3",
            }])
            for name in (segments, metadata, registry, endorsements):
                csv(name, [{"id": "one"}])
            save("config/cap_topics.json", {})
            save("config/sources.json", {"research_cutoff": "2026-09-22"})
            save("outputs/tables/text_analysis/analysis_manifest.json", {
                "screening_version": CANDIDATE_SCREENING_VERSION,
                "candidate_documents": 1,
                "input_hashes": {
                    name: digest(name) for name in (corpus, segments, metadata, registry, endorsements)
                },
            })
            save("data/analysis/model_topic_validation.json", {
                "input_sha256": digest(corpus), "config_sha256": digest("config/cap_topics.json"),
                "output_sha256": digest(output), "total_rows": 1, "classified_rows": 1,
                "unclassified_rows": 0, "model_name": "test-model",
            })
            csv("data/analysis/provisional_gte_kde/segment_density_scores.csv", [{"id": "a"}])
            save("data/analysis/provisional_gte_kde/summary.json", {
                "screening_version": CANDIDATE_SCREENING_VERSION,
                "candidate_corpus_sha256": digest(corpus), "input_sha256": digest(segments),
                "metadata_sha256": digest(metadata), "registry_sha256": digest(registry),
                "retained_segments": 1, "model_name": "test-model", "model_revision": "revision",
                "group_counts": {"endorsed": 1, "opponent": 0},
                "candidate_counts": {"endorsed": 1, "opponent": 0}, "selected_dimensions": 5,
            })
            save("data/analysis/policy_evidence/historical_inventory_summary.json", {
                "complete": False, "in_scope_races": 1, "candidate_race_records": 2,
                "candidates_with_reviewed_statements": 1,
                "individual_candidate_race_records": 2,
                "individual_candidate_records_with_reviewed_statements": 1,
                "endorsed_ballot_campaign_records": 0, "non_person_ballot_option_records": 0,
                "acquisition_work_units_with_missing_direct_review": 1,
            })
            save("data/analysis/policy_evidence/summary.json", {
                "unique_evidence_pairs": 2, "total_recovered_statements": 4,
                "review_method": "assistant_source_review_not_independent_human_gold",
            })
            save("data/analysis/policy_evidence/complete_questionnaires/summary.json", {
                "complete_answer_rows": 4, "matched_question_pairs": 2, "shared_topic_round_pairs": 0,
            })
            for filename, identifier, kind in (
                ("reviewed_candidate_comparisons.csv", "a", "policy_position"),
                ("timing_unverified_candidate_comparisons.csv", "b", "campaign_frame"),
            ):
                csv(str((policy / filename).relative_to(root)), [{
                    "comparison_id": identifier, "representation_kind": kind,
                    "relationship": "shared_position",
                }])
            csv("data/analysis/policy_evidence/race_policy_comparison_matrix.csv", [{
                "comparison_count": 2, "policy_comparison_count": 1,
            }])
            csv("data/analysis/policy_evidence/historical_candidate_inventory.csv", [
                {"election_year": "2020", "reviewed_statements": 4, "entity_kind": "individual_candidate"},
                {"election_year": "2020", "reviewed_statements": 0, "entity_kind": "individual_candidate"},
            ])
            save("data/analysis/jev_old/summary.json", {
                "corpus_sha256": "old", "baseline_sha256": "old", "status": "prepared",
                "sample_rows": 1, "live_requests": 0,
            })
            receipt = write_execution_audit(root)
            self.assertFalse(receipt["complete_national_source_collection"])
            self.assertTrue(all(s["status"] == "current" for s in receipt["stages"].values()))
            self.assertIsNone(receipt["stages"]["local_classifier"]["accuracy"])
            self.assertIsNone(receipt["stages"]["local_classifier"]["completed_at"])
            self.assertEqual(receipt["source_review"]["policy_relationships_by_timing"], {
                "timing_supported": {"shared_position": 1}, "timing_qualified": {},
            })
            self.assertEqual(receipt["coverage_by_year"]["2020"]["without_reviewed_statements"], 1)
            self.assertEqual(receipt["jev_pilots"][0]["input_status"], "stale_or_missing")
            self.assertTrue((analysis / "execution_audit.json").is_file())
            self.assertIn("No prepared pilot matches", (root / "report/analysis_execution.md").read_text())

            csv(metadata, [{"id": "changed"}])
            receipt = write_execution_audit(root)
            self.assertEqual(receipt["stages"]["local_classifier"]["status"], "stale_upstream")
            self.assertEqual(receipt["stages"]["candidate_kde"]["status"], "stale_or_missing")
