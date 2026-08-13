import unittest

from dsa_analysis.io import merge_notes


class IoTests(unittest.TestCase):
    def test_merge_notes_deduplicates_nested_segments(self):
        self.assertEqual(
            merge_notes(
                "Local chapter endorsement",
                "Local chapter endorsement | Official primary roster",
            ),
            "Local chapter endorsement | Official primary roster",
        )


if __name__ == "__main__":
    unittest.main()
