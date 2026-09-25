import unittest

from dsa_analysis.national_platform_applicability import applicable_rows, is_presidential_office


class NationalPlatformApplicabilityTests(unittest.TestCase):
    def test_local_presidents_are_not_us_presidential_contests(self):
        for office in ("President of the Board of Aldermen", "County Council President", "School Board President"):
            self.assertFalse(is_presidential_office(office))
        for office in ("President", "US President", "U.S. President", "Democratic Presidential Primary"):
            self.assertTrue(is_presidential_office(office))

    def test_reuse_requires_same_cycle_candidate_field_and_in_window_sources(self):
        def race(key, election_date, opponents):
            return {
                "race_id": key, "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                "office": "President", "election_date": election_date, "election_year": election_date[:4],
                "state_code": "AA", "jurisdiction": key,
                "endorsed_candidates": "Bernie Sanders", "endorsed_candidate": "Bernie Sanders",
                "opponent_candidates": opponents,
            }
        races = {
            "source": race("source", "2020-02-11", "Joseph R. Biden"),
            "later": race("later", "2020-03-03", "Joe Biden"),
            "too-early": race("too-early", "2020-01-01", "Joseph R. Biden"),
            "wrong-cycle": race("wrong-cycle", "2024-03-03", "Joseph R. Biden"),
            "absent": race("absent", "2020-03-03", "Other Candidate"),
        }
        statements = [{
            "excerpt_id": key, "source_type": "official_campaign_platform",
            "publication_date": "", "capture_date": "2020-02-01",
        } for key in ("left", "right")]
        comparisons = [{
            "comparison_id": "one-reviewed-pair", "race_id": "source", "election_date": "2020-02-11",
            "timing_status": "pre_primary_verified", "candidate_name": "Bernie Sanders",
            "opponent_name": "Joseph R. Biden", "candidate_excerpt_id": "left", "opponent_excerpt_id": "right",
            "candidate_source_url": "https://example.org/left", "opponent_source_url": "https://example.org/right",
            "topic": "healthcare", "relationship": "different_strategy", "analysis": "Different stated models.",
        }]
        rows = applicable_rows(races, statements, comparisons)
        self.assertEqual({row["race_id"] for row in rows}, {"source", "later"})
        self.assertTrue(all(row["new_independent_evidence"] == "false" for row in rows))
        self.assertTrue(all("not_state_specific" in row["evidence_scope"] for row in rows))
        later_edition = [{
            **row, "publication_date": "2019-01-01", "temporal_evidence_date": "2020-02-20",
        } for row in statements]
        self.assertEqual(
            {row["race_id"] for row in applicable_rows(races, later_edition, comparisons)},
            {"later"},
        )


if __name__ == "__main__":
    unittest.main()
