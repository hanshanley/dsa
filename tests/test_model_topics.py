import unittest

from dsa_analysis.model_topics import (
    Topic,
    _keyword_patterns,
    _keyword_predict,
    _topic_emphasis,
    _validation_summary,
)


class ModelTopicTests(unittest.TestCase):
    def test_no_reviewed_labels_do_not_mean_zero_accuracy(self):
        summary = _validation_summary([])
        self.assertEqual(summary["crosswalk_rows"], 0)
        self.assertIsNone(summary["crosswalk_agreement"])
        self.assertIsNone(summary["model_keyword_agreement"])

    def test_keyword_baseline_uses_configured_seeds(self):
        topics = [
            Topic(3, "Health", "Health care and insurance.", ("healthcare", "medicare")),
            Topic(14, "Housing", "Rent and tenant policy.", ("rent", "tenant")),
        ]
        code, score = _keyword_predict(
            "We support tenant protections and rent stabilization.",
            topics,
            _keyword_patterns(topics),
        )
        self.assertEqual(code, 14)
        self.assertGreater(score, 0)

    def test_topic_emphasis_uses_classified_rows(self):
        rows = [
            {
                "topic_code": "5",
                "topic_name": "Labor and employment",
                "group": "endorsed",
                "similarity": "0.6",
                "margin": "0.2",
            },
            {
                "topic_code": "5",
                "topic_name": "Labor and employment",
                "group": "opponent",
                "similarity": "0.5",
                "margin": "0.1",
            },
            {
                "topic_code": "14",
                "topic_name": "Housing and community development",
                "group": "endorsed",
                "similarity": "0.7",
                "margin": "0.3",
            },
        ]
        emphasis = {row["topic_code"]: row for row in _topic_emphasis(rows)}
        self.assertGreater(float(emphasis["14"]["difference"]), 0)


if __name__ == "__main__":
    unittest.main()
