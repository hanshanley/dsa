import unittest

from dsa_analysis.policy_findings import summarize_findings
from dsa_analysis.policy_inventory import inventory_rows
from dsa_analysis.policy_comparison import comparison_representation_kind, apply_representation_reviews
import hashlib


class PolicyFindingsTests(unittest.TestCase):
    def test_kind_review_is_bound_to_exact_source_and_quote(self):
        statements = {"id": {"quote": "Support public housing.", "source_sha256": "source"}}
        decision = {
            "excerpt_id": "id", "source_sha256": "source",
            "quote_sha256": hashlib.sha256(b"Support public housing.").hexdigest(),
            "representation_kind": "policy_position", "rationale": "An explicit policy commitment.",
        }
        review = {"review_method": "assistant_source_review_not_independent_human_gold", "reviews": [decision]}
        apply_representation_reviews(statements, review)
        self.assertEqual(statements["id"]["representation_kind"], "policy_position")
        with self.assertRaisesRegex(ValueError, "no longer matches"):
            apply_representation_reviews({"id": {**statements["id"], "quote": "Different claim."}}, review)
        with self.assertRaisesRegex(ValueError, "no longer matches"):
            apply_representation_reviews({"id": {**statements["id"], "source_sha256": "new"}}, review)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            apply_representation_reviews(statements, {**review, "reviews": [decision, decision]})
        with self.assertRaisesRegex(ValueError, "conflicts"):
            apply_representation_reviews({"id": {**statements["id"], "representation_kind": "campaign_frame"}}, review)

    def race(self, race_id):
        return {
            "race_id": race_id, "scope_kind": "tracked_dsa_endorsed_democratic_primary",
            "election_year": "2020", "election_date": "2020-03-03", "state_code": "AA",
            "office": "State House", "jurisdiction": "District 1", "source_race_ids": race_id,
            "endorsed_candidate": "Endorsed", "endorsed_candidates": "",
            "opponent_candidates": "Other", "all_candidates": "Endorsed | Other",
            "official_election_source_status": "resolution_verified",
            "certified_opponents_status": "corpus_candidate_set",
        }

    def test_all_registry_cases_remain_visible_when_no_policy_source_is_reviewed(self):
        races = {key: self.race(key) for key in ("one", "two")}
        cases, candidates, sources = inventory_rows(races, [], [], [])
        self.assertEqual(len(cases), 2)
        self.assertEqual(len(candidates), 4)
        self.assertEqual(sources, [])
        self.assertTrue(all(row["coverage_status"] == "no_reviewed_excerpt" for row in candidates))
        self.assertTrue(all(row["full_platform_completeness"] == "not_established" for row in cases))

    def test_reused_national_sources_do_not_inflate_distinct_policy_evidence(self):
        races = {key: self.race(key) for key in ("one", "two", "unreviewed")}
        common = {
            "candidate_name": "Endorsed", "opponent_name": "Other", "topic": "housing",
            "candidate_quote": "Build public housing", "opponent_quote": "Build more homes",
            "candidate_source_sha256": "same-left", "opponent_source_sha256": "same-right",
            "relationship": "different_emphasis", "analysis": "Different emphasis, not opposition.",
            "timing_status": "pre_primary_verified",
        }
        comparisons = [{**common, "race_id": key, "comparison_id": key} for key in ("one", "two")]
        _, topics, cases = summarize_findings([], comparisons, races)
        self.assertEqual(topics[0]["distinct_source_quote_pairs"], 1)
        self.assertEqual(topics[0]["election_cases"], 2)
        self.assertEqual(next(row for row in cases if row["race_id"] == "unreviewed")["study_status"], "not_source_reviewed")

    def test_shared_ballot_matrix_does_not_turn_republicans_into_missing_democrats(self):
        race = {
            **self.race("shared"), "scope_kind": "other_corpus_race",
            "all_candidates": "Endorsed | Other | Republican",
            "opponent_candidates": "Other | Republican",
        }
        _, _, cases = summarize_findings([], [], {"shared": race}, {"shared": ["Endorsed", "Other"]})
        self.assertEqual(cases[0]["other_candidates"], "Other")
        self.assertNotIn("Republican", cases[0]["unreviewed_candidates"])

    def test_campaign_framing_does_not_inflate_policy_position_coverage(self):
        races = {key: self.race(key) for key in ("framing", "policy", "legacy")}
        statements = [
            {"excerpt_id": key + suffix, "race_id": key, "speaker": name, "topic": "housing",
             "representation_kind": kind, "source_url": "https://example.org/" + key + suffix}
            for key, kind in (("framing", "campaign_frame"), ("policy", "policy_position"))
            for suffix, name in (("-a", "Endorsed"), ("-b", "Other"))
        ]
        comparisons = [{
            "comparison_id": key, "race_id": key, "candidate_name": "Endorsed", "opponent_name": "Other",
            "topic": "housing", "relationship": "different_emphasis", "analysis": "Source-backed emphasis.",
            **({"candidate_excerpt_id": key + "-a", "opponent_excerpt_id": key + "-b"} if key != "legacy" else {}),
        } for key in races]
        _, _, cases = summarize_findings(statements, comparisons, races)
        by_id = {r["race_id"]: r for r in cases}
        self.assertEqual(by_id["framing"]["policy_comparison_count"], 0)
        self.assertEqual(by_id["framing"]["campaign_frame_comparison_count"], 1)
        self.assertEqual(by_id["policy"]["policy_comparison_count"], 1)
        self.assertEqual(by_id["legacy"]["unspecified_comparison_count"], 1)
        self.assertEqual(by_id["legacy"]["policy_comparison_count"], 0)
        with self.assertRaisesRegex(ValueError, "missing statement"):
            comparison_representation_kind({"candidate_excerpt_id": "missing"}, {})
        with self.assertRaisesRegex(ValueError, "different statement kinds"):
            comparison_representation_kind(
                {"candidate_excerpt_id": "a", "opponent_excerpt_id": "b"},
                {"a": {"representation_kind": "policy_position"}, "b": {"representation_kind": "campaign_frame"}},
            )


if __name__ == "__main__":
    unittest.main()
