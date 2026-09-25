import unittest

from dsa_analysis.congressional_accounting import (
    canonical_party,
    reconcile_party_contests,
)


class PartyAccountingTests(unittest.TestCase):
    def seat(self, state="CT", district="01"):
        return {"cycle": 2026, "state_code": state, "chamber": "House",
                "district": district, "source_rows": 0}

    def result(self, party="Democratic", state="CT"):
        return {
            "cycle": "2026", "election_date": "2026-08-11", "state_code": state,
            "chamber": "House", "district": "01", "term": "regular", "stage": "primary",
            "primary_party": party, "candidate_name": "Candidate",
            "source_id": "official", "source_url": "https://example.gov/results",
            "source_locators": "page 1",
        }

    def review(self, status, party="Republican"):
        return {
            "cycle": "2026", "election_date": "2026-08-11", "state_code": "CT",
            "chamber": "House", "district": "01", "term": "regular", "stage": "primary",
            "primary_party": party, "status": status, "candidate_names": "Nominee",
            "source_urls": "https://example.gov/certification", "locators": "page 2",
            "notes": "Explicit official nomination record",
        }

    def test_single_party_result_does_not_complete_the_district(self):
        rows, seats = reconcile_party_contests(
            [self.seat()], [self.result()], [], cutoff="2026-09-22",
        )
        self.assertEqual(seats[0]["regular_primary_status"], "unresolved")
        self.assertEqual(seats[0]["unresolved_ballot_categories"], "Republican")
        self.assertEqual({row["status"] for row in rows}, {"results_complete", "unresolved"})

    def test_explicit_no_primary_nomination_closes_only_that_ballot_category(self):
        rows, seats = reconcile_party_contests(
            [self.seat()], [self.result()],
            [self.review("unopposed_nomination_verified")], cutoff="2026-09-22",
        )
        self.assertEqual(seats[0]["regular_primary_status"], "tracked_party_contests_resolved")
        self.assertNotIn("votes", rows[1])
        self.assertEqual(seats[0]["minor_party_universe_status"], "requires_state_election_specific_review")

    def test_noncandidate_classification_requires_source_evidence(self):
        review = self.review("no_candidate_verified")
        review["source_urls"] = ""
        with self.assertRaisesRegex(ValueError, "requires source"):
            reconcile_party_contests([self.seat()], [], [review], cutoff="2026-09-22")

    def test_nonpartisan_primary_is_one_ballot_not_two_parties(self):
        _, seats = reconcile_party_contests(
            [self.seat("WA")], [self.result("", "WA")], [], cutoff="2026-09-22",
        )
        self.assertEqual(seats[0]["regular_primary_status"], "tracked_party_contests_resolved")

    def test_puerto_rico_does_not_default_to_us_democratic_republican_primaries(self):
        seat = {**self.seat("PR", "00"), "cycle": 2024}
        rows, seats = reconcile_party_contests([seat], [], [], cutoff="2026-09-22")
        self.assertEqual({row["primary_party"] for row in rows}, {""})
        self.assertEqual(seats[0]["regular_primary_status"], "unresolved")
        self.assertEqual(seats[0]["unresolved_ballot_categories"], "unspecified-party")

    def test_unknown_territorial_ballot_category_is_not_called_all_party(self):
        review = {
            **self.review("results_partial", ""), "state_code": "VI", "district": "00",
        }
        _, seats = reconcile_party_contests(
            [self.seat("VI", "00")], [], [review], cutoff="2026-09-22",
        )
        self.assertEqual(seats[0]["regular_primary_status"], "unresolved")
        self.assertIn("unspecified-party", seats[0]["unresolved_ballot_categories"])
        self.assertNotIn("all-party", seats[0]["unresolved_ballot_categories"])

    def test_conflicting_evidence_is_not_silently_resolved(self):
        rows, seats = reconcile_party_contests(
            [self.seat()], [self.result()],
            [self.review("no_primary_verified", "Democratic")], cutoff="2026-09-22",
        )
        self.assertIn("conflicting_evidence", {row["status"] for row in rows})
        self.assertEqual(seats[0]["regular_primary_status"], "unresolved")

    def test_party_aliases_preserve_minor_parties(self):
        self.assertEqual(canonical_party("Democratic-Farmer-Labor"), "Democratic")
        self.assertEqual(canonical_party("REP"), "Republican")
        self.assertEqual(canonical_party("Working Families"), "Working Families")

    def test_senate_no_election_claim_must_match_the_independent_class_schedule(self):
        seat = {**self.seat("WV", "S"), "chamber": "Senate"}
        review = {
            **self.review("not_scheduled"), "state_code": "WV",
            "chamber": "Senate", "district": "S",
        }
        with self.assertRaisesRegex(ValueError, "class inventory"):
            reconcile_party_contests([seat], [], [review], cutoff="2026-09-22")

    def test_explicit_partial_evidence_is_not_overruled_by_numeric_row_presence(self):
        rows, seats = reconcile_party_contests(
            [self.seat()], [self.result()],
            [self.review("results_partial", "Democratic")], cutoff="2026-09-22",
        )
        self.assertEqual(
            next(row["status"] for row in rows if row["primary_party"] == "Democratic"),
            "results_partial",
        )
        self.assertEqual(seats[0]["regular_primary_status"], "unresolved")


if __name__ == "__main__":
    unittest.main()
