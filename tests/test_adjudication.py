import unittest

from dsa_analysis.adjudication import _deduplicate_accepts


class AdjudicationTests(unittest.TestCase):
    def test_duplicate_accepts_are_merged(self) -> None:
        rows = [
            {
                "decision": "accept",
                "chapter": "Example DSA",
                "state": "EX",
                "candidate_name": "Jane Doe",
                "office_text": "City Council District 1",
                "election_year": "2024",
                "election_stage": "primary",
                "source_url": "https://example.org/endorsement",
                "mention_id": "one",
                "confidence": "high",
                "notes": "",
            },
            {
                "decision": "accept",
                "chapter": "Example DSA",
                "state": "EX",
                "candidate_name": "Jane Doe",
                "office_text": "City Council District 1",
                "election_year": "2024",
                "election_stage": "primary",
                "source_url": "https://example.org/endorsement",
                "mention_id": "two",
                "confidence": "medium",
                "notes": "",
            },
        ]
        result = _deduplicate_accepts(rows)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["confidence"], "high")


if __name__ == "__main__":
    unittest.main()
