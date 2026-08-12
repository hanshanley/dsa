import unittest

from dsa_analysis.audit import validate


class AuditTests(unittest.TestCase):
    def test_seed_data_has_no_errors(self) -> None:
        result = validate()
        self.assertEqual(result.errors, ())

    def test_generated_coverage_removes_missing_ledger_warning(self) -> None:
        result = validate()
        self.assertNotIn(
            "chapter-year coverage ledger has not yet been populated",
            result.warnings,
        )


if __name__ == "__main__":
    unittest.main()
