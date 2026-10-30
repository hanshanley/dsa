import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from dsa_analysis.national_claim_analysis import (
    analysis_rows,
    audit_claim_lengths,
    classify_topics,
    run_analysis,
    topic_predictions,
    topic_shares,
    write_report,
)
from dsa_analysis.national_claim_corpus import build_blocks, validate_response
from dsa_analysis.national_platforms import read_rows, write_json, write_rows
from tests.test_national_claim_corpus import response
from tests.test_national_claims import coverage, sources

CONFIG = {
    "minimum_similarity": 0.2,
    "topics": [{"code": 3, "name": "Health"}, {"code": 5, "name": "Labor"}],
}


class ClaimAnalysisTests(unittest.TestCase):
    def test_adapter_embeds_claims_not_evidence_and_checks_exact_provenance(self):
        source_rows = sources()
        block = build_blocks(source_rows, coverage(source_rows))[0]
        claims, _, _ = validate_response(response(), block)
        adapted = analysis_rows(claims, source_rows)
        self.assertEqual(adapted[0]["text"], claims[0]["claim_text"])
        self.assertNotEqual(adapted[0]["text"], claims[0]["evidence"])
        self.assertEqual(adapted[0]["segment_id"], claims[0]["claim_id"])
        self.assertIn("scoped characters", adapted[0]["locator"])
        self.assertTrue(adapted[0]["strict"])
        claims[0]["analysis_eligible"] = False
        self.assertEqual(analysis_rows(claims, source_rows), [])
        claims[0]["analysis_eligible"] = True
        claims[0]["evidence"] = "Not in the original document"
        with self.assertRaisesRegex(ValueError, "provenance"):
            analysis_rows(claims, source_rows)

    def test_duplicate_and_excluded_claims_do_not_enter_analysis(self):
        source_rows = sources()
        block = build_blocks(source_rows, coverage(source_rows))[0]
        claims, _, _ = validate_response(response(), block)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            analysis_rows(claims * 2, source_rows)
        claims[0]["duplicate_of"] = "earlier"
        self.assertEqual(analysis_rows(claims, source_rows), [])

    def test_topics_preserve_unclassified_and_document_bundle_mass(self):
        rows = [
            {"group": "dsa", "bundle_id": "many"},
            {"group": "dsa", "bundle_id": "many"},
            {"group": "dsa", "bundle_id": "one"},
            {"group": "democratic", "bundle_id": "d"},
        ]
        predictions = topic_predictions(
            rows, np.array([[0.7, 0.1], [0.8, 0.3], [0.1, 0.6], [0.1, 0.1]]), CONFIG
        )
        self.assertEqual(predictions[-1]["topic_name"], "Unclassified")
        shares = topic_shares(predictions, CONFIG, "expanded")
        dsa = {row["topic_code"]: row["share"] for row in shares if row["group"] == "dsa"}
        self.assertEqual(dsa["3"], 0.5)
        self.assertEqual(dsa["5"], 0.5)
        self.assertEqual(sum(dsa.values()), 1)
        democratic = [row for row in shares if row["group"] == "democratic"]
        self.assertEqual(next(row["share"] for row in democratic if not row["topic_code"]), 1)
        self.assertTrue(all(row["share"] == 0 for row in shares if row["group"] == "republican"))
        with self.assertRaises(ValueError):
            topic_predictions(rows, np.zeros((1, 2)), CONFIG)

    def test_topic_cache_is_offline_and_text_changes_invalidate_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            rows = [{"text": "Support: universal health care.", "claim_id": "one"}]
            config = json.loads(
                (Path(__file__).resolve().parents[1] / "config/cap_topics.json").read_text()
            )
            vectors = np.zeros((1, len(config["topics"])))
            vectors[0, 2] = 0.8

            class Model:
                calls = []

                def __init__(self, *args, **kwargs):
                    self.calls.append(kwargs)

                def encode(self, texts, **kwargs):
                    if len(texts) == 1:
                        return np.array([[1.0, 0.0]])
                    return np.column_stack([vectors[0], np.zeros(len(texts))])

            with patch("sentence_transformers.SentenceTransformer", Model):
                first, manifest = classify_topics(rows, output)
            self.assertFalse(manifest["cache_reused"])
            self.assertTrue(Model.calls[0]["local_files_only"])
            with patch(
                "sentence_transformers.SentenceTransformer",
                side_effect=AssertionError("cache must not load a model"),
            ):
                second, manifest = classify_topics(rows, output)
                self.assertEqual(first, second)
                self.assertTrue(manifest["cache_reused"])
                with self.assertRaisesRegex(AssertionError, "must not"):
                    classify_topics([{**rows[0], "text": "Changed."}], output)
            self.assertEqual(
                read_rows(output / "topic_assignments.csv")[0]["text"], rows[0]["text"]
            )

    def test_incomplete_full_extraction_cannot_be_presented_as_complete(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            write_json(output / "extraction_summary.json", {"status": "running"})
            write_rows(output / "claims.csv", [])
            with self.assertRaisesRegex(ValueError, "still running"):
                run_analysis(output)

    def test_long_claim_qualifiers_are_not_silently_truncated(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            rows = [{"claim_id": "long", "text": "Claim with a necessary final condition."}]
            with patch("transformers.AutoTokenizer.from_pretrained") as loader:
                loader.return_value.return_value = {"input_ids": [list(range(300))]}
                with self.assertRaisesRegex(ValueError, "refusing silent truncation"):
                    audit_claim_lengths(rows, output)
            self.assertTrue((output / "claim_token_lengths.csv").exists())
            with patch(
                "transformers.AutoTokenizer.from_pretrained",
                side_effect=AssertionError("cached length checks must not reload tokenizers"),
            ):
                with self.assertRaisesRegex(ValueError, "refusing silent truncation"):
                    audit_claim_lengths(rows, output)

    def test_report_does_not_mix_expanded_and_strict_topic_rankings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "report").mkdir()
            groups = {"democratic": 1, "republican": 1, "dsa": 1}
            summary = {
                "corpus": {"status": "reviewed_sample_not_full_corpus"},
                "claims_by_group": groups,
                "documents_by_group": groups,
                "bundles_by_group": groups,
                "views": {
                    view: {"status": "insufficient_evidence", "reason": "fixture"}
                    for view in ("expanded", "strict")
                },
            }
            shares = [
                {"group": group, "view": view, "topic_name": "Health", "share": 1}
                for group in groups
                for view in ("expanded", "strict")
            ]
            with patch("dsa_analysis.national_claim_analysis.ROOT", root):
                report = write_report(root / "data/sample", summary, shares, root / "figures")
            self.assertEqual(report.read_text().count("Health 100.0%"), 3)

    def test_orchestrator_passes_claim_text_to_both_semantic_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output, baseline = root / "claims", root / "baseline"
            output.mkdir()
            baseline.mkdir()
            source_rows = sources()
            claims = [
                validate_response(response(), block)[0][0]
                for block in build_blocks(source_rows, coverage(source_rows))
            ]
            write_rows(output / "claims.csv", claims)
            write_rows(output / "complete_sources.csv", source_rows)
            write_json(output / "extraction_summary.json", {"status": "complete"})
            write_rows(baseline / "coverage.csv", coverage(source_rows))
            observed = {}

            def encoder(rows, *args, **kwargs):
                observed["embedding_texts"] = [row["text"] for row in rows]
                return np.zeros((len(rows), 768)), True

            def classifier(rows, *args, **kwargs):
                observed["topic_texts"] = [row["text"] for row in rows]
                return [{**row, "topic_code": "3", "topic_name": "Health"} for row in rows], {
                    "cache_reused": True
                }

            module = "dsa_analysis.national_claim_analysis"
            with (
                patch(f"{module}.ROOT", root),
                patch(f"{module}.OUTPUT", baseline),
                patch(f"{module}.encode", side_effect=encoder),
                patch(f"{module}.audit_claim_lengths", return_value={"truncated_claims": 0}),
                patch(f"{module}.classify_topics", side_effect=classifier),
                patch(
                    f"{module}.analyze_view",
                    return_value={
                        "status": "insufficient_evidence",
                        "reason": "fixture",
                    },
                ) as kde,
                patch(f"{module}.plot_outputs"),
                patch(f"{module}.plot_topics"),
                patch(f"{module}.write_report", return_value=root / "report.md"),
            ):
                summary = run_analysis(output)
            self.assertEqual(observed["embedding_texts"], [row["claim_text"] for row in claims])
            self.assertEqual(observed["topic_texts"], observed["embedding_texts"])
            self.assertEqual(kde.call_count, 2)
            self.assertEqual(summary["claims"], len(claims))
            self.assertFalse(summary["baseline_modified"])

    def test_completed_report_explains_dsa_source_mix_sensitivity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "report").mkdir()
            groups = {"democratic": 7, "republican": 6, "dsa": 122}
            summary = {
                "corpus": {
                    "status": "complete",
                    "blocks_by_status": {"normalized": 2462, "source_repaired": 161},
                    "model_blocks_by_status": {"normalized": 2596, "validation_failed": 27},
                    "assistant_source_repaired_blocks": 161,
                    "assistant_source_repaired_claims": 1200,
                    "superseded_model_claims": 1100,
                    "assistant_flagged_claims": 1054,
                    "unrepaired_flagged_model_claims": 0,
                },
                "claims_by_group": groups,
                "documents_by_group": groups,
                "bundles_by_group": groups,
                "views": {
                    view: {
                        "status": "complete",
                        "dimensions": 10,
                        "group_documents": {**groups, "dsa": count},
                        "group_passages": {**groups, "dsa": count * 10},
                    }
                    for view, count in (("expanded", 122), ("strict", 3))
                },
            }
            shares = [
                {
                    "group": group,
                    "view": view,
                    "topic_code": code,
                    "topic_name": name,
                    "share": share,
                }
                for group in groups
                for view, code, name, share in (
                    ("expanded", "3", "Health", 0.3),
                    ("strict", "5", "Labor", 0.6),
                    ("expanded", "", "Unclassified", 0.7),
                    ("strict", "", "Unclassified", 0.4),
                )
            ]
            with patch("dsa_analysis.national_claim_analysis.ROOT", root):
                report = write_report(root / "data/full", summary, shares, root / "figures")
            text = report.read_text()
            self.assertIn("3 documents and 30 claims", text)
            self.assertIn("122 documents and 1,220 claims", text)
            self.assertIn("Health (30.0%)", text)
            self.assertIn("Labor (60.0%)", text)
            self.assertIn("not a measured change in positions over time", text)
            self.assertIn('"validation_failed": 27', text)
            self.assertIn("Original Gemma chunk outcomes", text)
            self.assertIn("**161 chunks**", text)
            self.assertIn("**1,200 replacement claims**", text)
            self.assertIn("normalization_origin=assistant_source_repair", text)
            self.assertIn("not independent human gold", text)
            self.assertIn("still lacking a superseding correction: **0**", text)


if __name__ == "__main__":
    unittest.main()
