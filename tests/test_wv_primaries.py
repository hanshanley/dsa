import unittest

from dsa_analysis.wv_primaries import (
    SENATE_SCHEDULE,
    _accounting,
    validate_clarity_payload,
)


class WestVirginiaPrimaryTests(unittest.TestCase):
    def test_empty_clarity_response_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_clarity_payload(b"")

    def test_every_federal_slot_remains_visible(self):
        rows = _accounting()
        self.assertEqual(len(rows), 12)
        self.assertEqual({row["status"] for row in rows}, {"unresolved"})

    def test_wv_2026_senate_schedule_is_independent_of_result_rows(self):
        self.assertIn(("WV", "2026"), SENATE_SCHEDULE)
        senate = [
            row for row in _accounting()
            if row["cycle"] == "2026" and row["chamber"] == "Senate"
        ]
        self.assertEqual(
            {(row["primary_party"], row["status"]) for row in senate},
            {("Democratic", "unresolved"), ("Republican", "unresolved")},
        )


if __name__ == "__main__":
    unittest.main()
