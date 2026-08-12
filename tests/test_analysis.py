import unittest

from dsa_analysis.analysis import analyze
from dsa_analysis.paths import REPORT_DIR


class AnalysisTests(unittest.TestCase):
    def test_analysis_generates_caveated_report(self) -> None:
        stats = analyze()
        report = (REPORT_DIR / "draft.md").read_text(encoding="utf-8")
        self.assertEqual(stats["endorsements"], 4)
        self.assertEqual(stats["tracked_races"], 3)
        self.assertEqual(stats["opponent_candidates"], 20)
        self.assertIn("What cannot yet be concluded", report)
        self.assertIn("direct textual observations", report)
        self.assertIn("mo01-dem-primary-2026", report)


if __name__ == "__main__":
    unittest.main()
