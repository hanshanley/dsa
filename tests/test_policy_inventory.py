import unittest

from dsa_analysis.policy_inventory import inventory_rows, participant_kind


class PolicyInventoryTests(unittest.TestCase):
    def test_ballot_options_are_not_people_but_endorsed_campaigns_still_need_evidence(self):
        self.assertEqual(participant_kind("President", "Scattered", {"Bernie Sanders"}), "non_person_ballot_option")
        self.assertEqual(participant_kind("President", '"Uncommitted"', {"Bernie Sanders"}), "non_person_ballot_option")
        self.assertEqual(participant_kind("President", "Uncommitted", {"Uncommitted"}), "endorsed_ballot_campaign")
        self.assertEqual(participant_kind("President", "John Wolfe", {"Bernie Sanders"}), "individual_candidate")
        self.assertEqual(participant_kind("County Council President", "No Preference", set()), "individual_candidate")

    def test_inventory_preserves_ballot_rows_without_fabricating_platform_gaps(self):
        race = {
            "race_id": "r", "election_year": "2020", "election_date": "2020-03-03",
            "state_code": "AA", "office": "President", "jurisdiction": "Example",
            "endorsed_candidates": "Bernie Sanders", "endorsed_candidate": "Bernie Sanders",
            "all_candidates": "Bernie Sanders | Joe Biden | Scattered | No Preference",
            "official_election_source_status": "verified", "certified_opponents_status": "verified",
        }
        cases, candidates, sources = inventory_rows({"r": race}, [], [], [])
        self.assertEqual(len(candidates), 4)
        self.assertEqual(cases[0]["individual_candidate_count"], 2)
        self.assertEqual(cases[0]["non_person_ballot_option_count"], 2)
        self.assertEqual(sum(r["policy_evidence_required"] for r in candidates), 2)
        self.assertEqual(candidates[-1]["coverage_status"], "not_an_individual_platform_gap")
        self.assertEqual(sources, [])
        with self.assertRaisesRegex(ValueError, "resolve its campaign identity"):
            inventory_rows({"r": race}, [], [], [{
                "race_id": "r", "speaker": "Scattered", "representation_kind": "policy_position",
            }])
