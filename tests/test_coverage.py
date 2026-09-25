import unittest

from dsa_analysis.coverage import build_coverage_ledger, coverage_chapters
from dsa_analysis.io import read_csv, read_json
from dsa_analysis.paths import CONFIG_DIR, PROCESSED_DIR
from dsa_analysis.queue import build_research_queue


class CoverageTests(unittest.TestCase):
    def test_coverage_has_every_chapter_year(self) -> None:
        build_research_queue()
        rows, unresolved = build_coverage_ledger()
        chapters = coverage_chapters()
        ledger = read_csv(PROCESSED_DIR / "coverage_ledger.csv")
        config = read_json(CONFIG_DIR / "sources.json")
        expected_years = {
            str(year) for year in range(
                int(config["source_start"][:4]), int(config["research_cutoff"][:4]) + 1
            )
        }
        self.assertIn("2015", expected_years)
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
