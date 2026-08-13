import unittest

from dsa_analysis.coverage import build_coverage_ledger


class CoverageTests(unittest.TestCase):
    def test_coverage_has_every_chapter_year(self) -> None:
        rows, unresolved = build_coverage_ledger()
        self.assertEqual(rows, 2640)
        self.assertEqual(unresolved, 0)


if __name__ == "__main__":
    unittest.main()
