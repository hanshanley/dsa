import unittest

from dsa_analysis.text_analysis import (
    FIGURE_DIR,
    TABLE_DIR,
    analyze_text,
    cosine_similarity,
    mpif_rows,
    tokenize,
)


class TextAnalysisTests(unittest.TestCase):
    def test_tokenize_removes_stopwords_and_normalizes_possessives(self):
        self.assertEqual(
            tokenize("The workers’ movement supports public ownership."),
            ["workers", "movement", "supports", "public", "ownership"],
        )

    def test_cosine_similarity_bounds(self):
        self.assertAlmostEqual(cosine_similarity("public housing", "public housing"), 1.0)
        self.assertEqual(cosine_similarity("housing", "healthcare"), 0.0)

    def test_mpif_direction(self):
        rows = mpif_rows(
            [
                {"group": "endorsed", "text": "workers workers union"},
                {"group": "opponent", "text": "business business market"},
            ],
            "endorsed",
            "opponent",
            minimum_total=1,
        )
        by_feature = {row["feature"]: row for row in rows}
        self.assertEqual(by_feature["workers"]["favored_group"], "endorsed")
        self.assertEqual(by_feature["business"]["favored_group"], "opponent")

    def test_analysis_generates_figures_and_manifest(self):
        stats = analyze_text()
        self.assertGreater(stats["candidate_documents"], 0)
        self.assertGreater(stats["sticking_points"], 0)
        self.assertTrue((FIGURE_DIR / "candidate_mpif_terms.svg").exists())
        self.assertTrue((TABLE_DIR / "analysis_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
