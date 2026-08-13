import unittest

from dsa_analysis.statement_batches import _expand_to_active_queues


class StatementBatchTests(unittest.TestCase):
    def test_reuses_evidence_for_active_queue_in_same_race(self):
        evidence = [
            {
                "statement_key": "old-key",
                "queue_id": "old-queue",
                "race_id": "old-race",
                "primary_type": "top_two",
                "election_date": "2018-06-05",
                "candidate_name": "Gayle McLaughlin",
                "party": "No Party Preference",
                "role": "endorsed",
                "official_election_source": "old-source",
                "evidence_status": "verified",
                "source_url": "https://example.com/statement",
                "source_type": "candidate_statement",
                "published_date": "2018-05-01",
                "quote": "Candidate words.",
                "locator": "Candidate statement",
                "topic": "labor",
                "subtopic": "wages",
                "stance": "support",
                "direct_opponent_name": "",
                "notes": "",
            }
        ]
        roster = [
            {
                "queue_id": "old-queue",
                "resolution_status": "verified",
                "race_id": "canonical-race",
                "primary_type": "top_two",
                "election_date": "2018-06-05",
                "candidate_name": "Gayle McLaughlin",
                "party": "No Party Preference",
                "role": "endorsed",
                "official_election_source": "official-source",
            },
            {
                "queue_id": "active-queue",
                "resolution_status": "verified",
                "race_id": "canonical-race",
                "primary_type": "top_two",
                "election_date": "2018-06-05",
                "candidate_name": "Gayle McLaughlin",
                "party": "No Party Preference",
                "role": "endorsed",
                "official_election_source": "official-source",
            },
        ]

        expanded = _expand_to_active_queues(evidence, roster, {"active-queue"})

        self.assertEqual(len(expanded), 1)
        self.assertEqual(expanded[0]["queue_id"], "active-queue")
        self.assertEqual(expanded[0]["race_id"], "canonical-race")
        self.assertEqual(expanded[0]["quote"], "Candidate words.")

    def test_reuses_evidence_when_duplicate_rosters_have_different_race_ids(self):
        evidence = [
            {
                "statement_key": "old-key",
                "queue_id": "old-queue",
                "race_id": "old-race",
                "primary_type": "democratic",
                "election_date": "2022-06-07",
                "candidate_name": "Eunisses Hernandez",
                "party": "Nonpartisan",
                "role": "endorsed",
                "official_election_source": "old-source",
                "evidence_status": "verified",
                "source_url": "https://example.com/statement",
                "source_type": "candidate_statement",
                "published_date": "2022-05-01",
                "quote": "Candidate words.",
                "locator": "Candidate statement",
                "topic": "housing",
                "subtopic": "rent_control",
                "stance": "support",
                "direct_opponent_name": "",
                "notes": "",
            }
        ]
        roster = [
            {
                "queue_id": "old-queue",
                "resolution_status": "verified",
                "race_id": "canonical-old",
                "primary_type": "top_two",
                "election_date": "2022-06-07",
                "candidate_name": "Eunisses Hernandez",
                "party": "Nonpartisan",
                "role": "endorsed",
                "official_election_source": "official-source",
            },
            {
                "queue_id": "active-queue",
                "resolution_status": "verified",
                "race_id": "canonical-active",
                "primary_type": "top_two",
                "election_date": "2022-06-07",
                "candidate_name": "Eunisses Hernandez",
                "party": "Nonpartisan",
                "role": "endorsed",
                "official_election_source": "official-source",
            },
        ]

        expanded = _expand_to_active_queues(evidence, roster, {"active-queue"})

        self.assertEqual(len(expanded), 1)
        self.assertEqual(expanded[0]["queue_id"], "active-queue")
        self.assertEqual(expanded[0]["race_id"], "canonical-active")

    def test_reuses_evidence_across_two_active_duplicate_queues(self):
        evidence = [
            {
                "statement_key": "old-key",
                "queue_id": "national-queue",
                "race_id": "old-race",
                "primary_type": "democratic",
                "election_date": "2024-06-25",
                "candidate_name": "Jonathan Soto",
                "party": "Democratic",
                "role": "endorsed",
                "official_election_source": "old-source",
                "evidence_status": "source_unavailable",
                "source_url": "",
                "source_type": "",
                "published_date": "",
                "quote": "",
                "locator": "",
                "topic": "",
                "subtopic": "",
                "stance": "",
                "direct_opponent_name": "",
                "notes": "Documented search.",
            }
        ]
        roster = [
            {
                "queue_id": "national-queue",
                "resolution_status": "verified",
                "race_id": "canonical-national",
                "primary_type": "democratic",
                "election_date": "2024-06-25",
                "candidate_name": "Jonathan Soto",
                "party": "Democratic",
                "role": "endorsed",
                "official_election_source": "official-source",
            },
            {
                "queue_id": "local-queue",
                "resolution_status": "verified",
                "race_id": "canonical-local",
                "primary_type": "democratic",
                "election_date": "2024-06-25",
                "candidate_name": "Jonathan Soto",
                "party": "Democratic",
                "role": "endorsed",
                "official_election_source": "official-source",
            },
        ]

        expanded = _expand_to_active_queues(
            evidence, roster, {"national-queue", "local-queue"}
        )

        self.assertEqual(
            {row["queue_id"] for row in expanded},
            {"national-queue", "local-queue"},
        )


if __name__ == "__main__":
    unittest.main()
