import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.io import write_csv
from dsa_analysis.jev_topics import (
    JEV_MODEL,
    benchmark_jev,
    comparison_metrics,
    select_sample,
    topic_question,
    validate_answer,
)


class JevTests(unittest.TestCase):
    def setUp(self):
        self.config = {"topics": [
            {"code": 3, "name": "Health", "description": "Health care."},
            {"code": 14, "name": "Housing", "description": "Tenant protections."},
        ]}
        self.criteria = topic_question(self.config)["criteria"]
        self.response = {
            "model": JEV_MODEL,
            "answers": {"topic": {
                "type": "choice", "choice": "3", "confidence": 0.7,
                "probabilities": {"3": 0.8, "14": 0.1, "unclassified": 0.1},
            }},
            "usage": {"input_tokens": 100, "output_tokens": 20},
        }

    def test_all_topic_options_and_explicit_abstention(self):
        self.assertEqual(set(self.criteria), {"3", "14", "unclassified"})

    def test_sample_is_order_independent_and_balanced(self):
        rows = [
            {"corpus_segment_id": f"{group}-{year}-{i}", "group": group, "cycle": year,
             "text": "Exact policy passage"}
            for group in ("endorsed", "opponent") for year in ("2016", "2026")
            for i in range(3)
        ]
        sample = select_sample(rows, 4)
        self.assertEqual(sample, select_sample(list(reversed(rows)), 4))
        self.assertEqual(len({(r["group"], r["cycle"]) for r in sample}), 4)
        with self.assertRaises(ValueError):
            select_sample(rows, 0)

    def test_validate_rejects_bad_distribution_and_model(self):
        self.assertEqual(validate_answer(self.response, self.criteria, JEV_MODEL)["choice"], "3")
        for field, value in (
            ("confidence", float("nan")),
            ("confidence", True),
            ("choice", "14"),
            ("probabilities", {"3": 1.0}),
            ("probabilities", {"3": 0.8, "14": 0.8, "unclassified": 0.1}),
        ):
            with self.subTest(field=field, value=value):
                response = copy.deepcopy(self.response)
                response["answers"]["topic"][field] = value
                with self.assertRaises(ValueError):
                    validate_answer(response, self.criteria, JEV_MODEL)
        with self.assertRaises(ValueError):
            validate_answer({**self.response, "model": "jev-latest"}, self.criteria, JEV_MODEL)

    def test_agreement_without_gold_is_not_accuracy(self):
        rows = [{
            "corpus_segment_id": "x", "local_topic_code": "3", "jev_topic_code": "3",
            "probabilities": {"3": 0.8, "14": 0.1, "unclassified": 0.1},
        }]
        metrics = comparison_metrics(rows, {}, self.criteria)
        self.assertEqual(metrics["agreement_with_local"], 1.0)
        self.assertIsNone(metrics["jev_accuracy"])
        self.assertFalse(metrics["improvement_established"])
        metrics = comparison_metrics(rows, {"x": "14"}, self.criteria)
        self.assertEqual(metrics["jev_accuracy"], 0)
        self.assertEqual(metrics["local_accuracy"], 0)
        self.assertGreater(metrics["jev_log_loss"], 0)

    def test_end_to_end_prepare_execute_resume_and_protect_review(self):
        sample = [{
            "corpus_segment_id": "x", "group": "endorsed", "cycle": "2016",
            "text": "We support universal health care.", "text_sha256": "same-hash",
            "source_urls": "https://example.org/policy", "locators": "paragraph 1",
        }]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_dir = root / "config"
            config_dir.mkdir()
            (config_dir / "cap_topics.json").write_text(json.dumps(self.config))
            write_csv(root / "candidate_text_corpus.csv", sample, list(sample[0]))
            baseline = [{**sample[0], "topic_code": "3"}]
            write_csv(root / "model_topic_classifications.csv", baseline, list(baseline[0]))
            output = root / "pilot"
            with (
                patch("dsa_analysis.jev_topics.ANALYSIS_DATA_DIR", root),
                patch("dsa_analysis.jev_topics.CONFIG_DIR", config_dir),
                patch("dsa_analysis.jev_topics._request", return_value=self.response) as request,
                patch.dict("os.environ", {"TYPESAFE_API_KEY": "test-only"}),
            ):
                result = benchmark_jev(limit=1, output_dir=output)
                self.assertEqual(result["status"], "prepared")
                request.assert_not_called()
                with self.assertRaises(ValueError):
                    benchmark_jev(limit=1, execute=True, output_dir=output)
                result = benchmark_jev(limit=1, execute=True, allow_hosted=True, output_dir=output)
                self.assertEqual(result["prediction_rows"], 1)
                self.assertEqual(result["input_tokens_this_run"], 100)
                self.assertEqual(request.call_count, 1)
                payload = request.call_args.args[0]
                self.assertEqual(payload["state"], sample[0]["text"])
                self.assertNotIn("group", payload)
                result = benchmark_jev(limit=1, output_dir=output)
                self.assertEqual(result["status"], "complete")
                self.assertEqual(result["live_requests"], 0)
                self.assertEqual(request.call_count, 1)
                self.assertEqual(sample[0]["text"], baseline[0]["text"])

    def test_empty_corpus_fails_instead_of_reporting_success(self):
        with self.assertRaises(ValueError):
            select_sample([], 10)


if __name__ == "__main__":
    unittest.main()
