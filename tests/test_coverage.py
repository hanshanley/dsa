import unittest

from dsa_analysis.coverage import build_coverage_ledger
from dsa_analysis.io import read_csv
from dsa_analysis.paths import PROCESSED_DIR


class CoverageTests(unittest.TestCase):
    def test_coverage_has_every_chapter_year(self) -> None:
        rows, unresolved = build_coverage_ledger()
        chapters = read_csv(PROCESSED_DIR / "chapter_directory.csv")
        ledger = read_csv(PROCESSED_DIR / "coverage_ledger.csv")
        expected_years = {str(year) for year in range(2016, 2027)}
        self.assertEqual(rows, len(chapters) * len(expected_years))
        self.assertEqual(len({row["coverage_id"] for row in ledger}), rows)
        self.assertEqual({row["election_year"] for row in ledger}, expected_years)
        self.assertEqual(
            unresolved,
            sum(
                row["status"] in {"not_searched", "found_unverified"}
                for row in ledger
            ),
        )


if __name__ == "__main__":
    unittest.main()
