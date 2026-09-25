import json
import unittest

from dsa_analysis.policy_browser import script_json, shared_national_rows


class PolicyBrowserTests(unittest.TestCase):
    def test_national_reuse_resolves_existing_evidence_without_counting_it_again(self):
        cases = [{
            "race_id": key, "election_date": "2020-03-03", "office": "US President",
            "endorsed_candidates": "Bernie Sanders", "other_candidates": "Joseph R. Biden",
        } for key in ("original", "other")]
        comparison = {
            "comparison_id": "source", "race_id": "original", "election_date": "2020-03-03",
            "timing_status": "pre_primary_verified", "representation_kind": "policy_position",
            "candidate_excerpt_id": "left", "opponent_excerpt_id": "right",
            "candidate_name": "Bernie Sanders", "opponent_name": "Joe Biden",
            "analysis": "Current reviewed interpretation.",
        }
        applicability = [{
            "race_id": key, "election_date": "2020-03-03", "source_comparison_id": "source",
            "source_review_race_id": "original", "new_independent_evidence": "false",
            "evidence_scope": "same_cycle_national_platforms_not_state_specific_campaigning",
            "candidate_name": "Bernie Sanders", "opponent_name": "Joseph R. Biden",
            "analysis": "Stale copied interpretation.",
        } for key in ("original", "other")]
        result = shared_national_rows(cases, [comparison], applicability)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["race_id"], "other")
        self.assertEqual(result[0]["candidate_excerpt_id"], "left")
        self.assertEqual(result[0]["representation_kind"], "policy_position")
        self.assertEqual(result[0]["analysis"], "Current reviewed interpretation.")
        self.assertEqual(comparison["race_id"], "original")
        with self.assertRaisesRegex(ValueError, "scope or temporal"):
            shared_national_rows(cases, [comparison], [{**applicability[1], "new_independent_evidence": "true"}])
        with self.assertRaisesRegex(ValueError, "missing source"):
            shared_national_rows(cases, [], applicability)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            shared_national_rows(cases, [comparison], [applicability[1], applicability[1]])
        with self.assertRaisesRegex(ValueError, "scope or temporal"):
            shared_national_rows(
                [{**row, "office": "City Council"} for row in cases], [comparison], applicability,
            )
        with self.assertRaisesRegex(ValueError, "scope or temporal"):
            shared_national_rows(cases, [comparison], [{**applicability[1], "opponent_name": "Someone Else"}])

    def test_source_text_cannot_close_the_embedded_json_element(self):
        value = {"quote": "</script><script>alert('source text')</script>&\u2028"}
        encoded = script_json(value)
        self.assertNotIn("<", encoded)
        self.assertNotIn("&", encoded)
        self.assertEqual(json.loads(encoded), value)

    def test_nonfinite_values_are_not_published_as_valid_json(self):
        with self.assertRaises(ValueError):
            script_json({"score": float("nan")})


if __name__ == "__main__":
    unittest.main()
