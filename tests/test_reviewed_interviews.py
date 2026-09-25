import unittest

from dsa_analysis.io import read_csv
from dsa_analysis.paths import ANALYSIS_DATA_DIR
from dsa_analysis.reviewed_interviews import export_reviewed_interview_answers, export_reviewed_platform_text


class ReviewedInterviewTests(unittest.TestCase):
    def test_arizona_platform_preserves_program_name_ambiguity_and_excludes_later_campaign(self):
        summary = export_reviewed_platform_text("policy_arizona_2018_followup")
        self.assertEqual(summary["source_documents"], 6)
        output = ANALYSIS_DATA_DIR / "policy_evidence/complete_campaign_platforms/policy_arizona_2018_followup"
        sources = read_csv(output / "complete_sources.csv")
        self.assertFalse(any("westbrookforarizona.com" in r["final_url"] for r in sources))
        article = next(r for r in sources if r["source_id"] == "az18-westbrook-single-payer")
        self.assertIn("expansion of Medicaid", article["full_retained_source_text"])
        self.assertIn("Medicare for All", article["full_retained_source_text"])
        self.assertEqual(article["publication_date"], "")
        self.assertIn("/20171216170154", article["final_url"])
        blocks = read_csv(output / "scoped_blocks.csv")
        self.assertFalse(any(
            r["scoped_campaign_text"] == "Facebook Twitter Linkedin Tumblr Google+ Pinterest"
            for r in blocks
        ))

    def test_platform_export_preserves_complete_sources_but_scopes_model_input(self):
        summary = export_reviewed_platform_text("policy_presidential_2020_followup")
        self.assertEqual(summary["source_documents"], 11)
        self.assertEqual(summary["scoped_documents_replayed"], 6)
        self.assertEqual(summary["external_existing_documents_reused"], 5)
        self.assertEqual(summary["new_independent_stance_classifications"], 0)
        output = ANALYSIS_DATA_DIR / "policy_evidence/complete_campaign_platforms/policy_presidential_2020_followup"
        sources = read_csv(output / "complete_sources.csv")
        blocks = read_csv(output / "scoped_blocks.csv")
        self.assertEqual(len(sources), 11)
        dividend = next(r for r in sources if r["source_id"] == "hp20-yang-dividend")
        self.assertEqual(dividend["publication_date"], "2018-01-22")
        self.assertIn("Thomas Paine", dividend["full_retained_source_text"])
        model_dividend = "\n".join(
            r["scoped_campaign_text"] for r in blocks if r["source_id"] == "hp20-yang-dividend"
        )
        self.assertIn("$1,000/month", model_dividend)
        self.assertNotIn("Thomas Paine", model_dividend)
        self.assertNotIn("Bernie Sanders, May 2014", model_dividend)
        economy = "\n".join(
            r["scoped_campaign_text"] for r in blocks if r["source_id"] == "hp20-williamson-economy"
        )
        self.assertIn("age 18 to 65", economy)
        self.assertNotIn("Q9.", economy)
        self.assertNotIn("Universal, single-payer health insurance.", economy)

    def test_complete_response_replay_excludes_reporter_narration(self):
        summary = export_reviewed_interview_answers()
        self.assertEqual(summary["complete_published_response_blocks"], 40)
        self.assertEqual(summary["candidate_race_records"], 4)
        self.assertFalse(summary["complete_campaign_platforms"])
        rows = read_csv(
            ANALYSIS_DATA_DIR / "policy_evidence/complete_interview_answers"
            / "policy_new_york_2017/complete_responses.csv"
        )
        self.assertEqual(len(rows), 40)
        self.assertTrue(all(
            r["complete_published_response"].startswith(("“", "Khader El-Yateem:", "KEY:"))
            for r in rows
        ))
        self.assertFalse(any(
            "Starting in January 2022" in r["complete_published_response"] for r in rows
        ))
        self.assertTrue(any(
            r["candidate_name"] == "Justin Brannan" and "form of activism" in r["complete_published_response"]
            for r in rows
        ))

    def test_bundle_path_is_not_an_arbitrary_filesystem_path(self):
        with self.assertRaises(ValueError):
            export_reviewed_interview_answers("../policy_test")
