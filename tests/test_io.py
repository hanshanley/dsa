import unittest
import tempfile
from pathlib import Path

from dsa_analysis.io import merge_notes, read_csv, write_csv


class IoTests(unittest.TestCase):
    def test_csv_failure_preserves_previous_complete_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "output.csv"
            write_csv(path, [{"id": "prior"}], ["id"])
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                write_csv(path, [{"id": "new"}, {"id": "bad", "unexpected": "field"}], ["id"])
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(read_csv(path), [{"id": "prior"}])
            self.assertEqual([item.name for item in path.parent.iterdir()], ["output.csv"])

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
