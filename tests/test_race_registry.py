import csv
import json
import shutil
import unittest
from pathlib import Path

from dsa_analysis.race_registry import RaceRegistryPaths, build_race_registry

SCRATCH_ROOT = Path(__file__).resolve().parent / "_scratch_race_registry"


class RaceRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree(SCRATCH_ROOT, ignore_errors=True)
        SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(SCRATCH_ROOT, ignore_errors=True))

    def test_dfl_primary_is_in_scope(self) -> None:
        root = self._scenario_root("dfl")
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "dfl-1",
                    "race_id": "race-dfl",
                    "candidate_name": "Endorsed Candidate",
                    "election_date": "2022-08-09",
                    "party": "Democratic-Farmer-Labor",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "notes": "",
                },
                {
                    "statement_key": "dfl-2",
                    "race_id": "race-dfl",
                    "candidate_name": "Primary Opponent",
                    "election_date": "2022-08-09",
                    "party": "Democratic-Farmer-Labor",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "notes": "",
                },
                {
                    "statement_key": "dfl-mayor",
                    "race_id": "race-dfl-mayor",
                    "candidate_name": "Mayoral Candidate",
                    "election_date": "2025-11-04",
                    "party": "Democratic-Farmer-Labor",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "notes": "2025-MN-MINNEAPOLIS-MAYOR",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_registry_resolutions_dfl.csv",
            [
                {
                    "race_id": "race-dfl-mayor",
                    "election_date": "2025-11-04",
                    "office": "Mayor",
                    "jurisdiction": "Minneapolis",
                    "state": "Minnesota",
                    "state_code": "MN",
                    "official_election_source": "https://example.org/results",
                    "verification_status": "verified",
                    "notes": "Minnesota municipal contest.",
                }
            ],
        )

        result = build_race_registry(self._paths(root))
        registry_rows = {
            row["race_id"]: row for row in self._read_csv(result.registry_path)
        }
        registry_row = registry_rows["race-dfl"]

        self.assertEqual(
            registry_row["scope_kind"],
            "tracked_dsa_endorsed_democratic_primary",
        )
        self.assertEqual(registry_row["primary_party"], "Democratic-Farmer-Labor")
        self.assertEqual(
            registry_rows["race-dfl-mayor"]["scope_kind"],
            "other_corpus_race",
        )

    def test_builds_registry_with_manual_hint_and_unresolved_rows(self) -> None:
        root = self._scenario_root("registry")
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "a1",
                    "race_id": "race-manual",
                    "candidate_name": "Mike Connolly",
                    "election_date": "2016-09-08",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "Search log",
                },
                {
                    "statement_key": "a2",
                    "race_id": "race-manual",
                    "candidate_name": "Timothy J. Toomey, Jr.",
                    "election_date": "2016-09-08",
                    "party": "Democratic",
                    "role": "opponent",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "Mike Connolly",
                    "notes": "Search log",
                },
                {
                    "statement_key": "b1",
                    "race_id": "race-hint",
                    "candidate_name": "Cori Bush",
                    "election_date": "2020-08-04",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "Searched exact-name and 2020-MO-US-HOUSE-D1-DEM web results; no accessible exact first-party quote was recovered.",
                },
                {
                    "statement_key": "b2",
                    "race_id": "race-hint",
                    "candidate_name": "William Lacy Clay",
                    "election_date": "2020-08-04",
                    "party": "Democratic",
                    "role": "opponent",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "Cori Bush",
                    "notes": "Searched exact-name and 2020-MO-US-HOUSE-D1-DEM web results; no accessible exact first-party quote was recovered.",
                },
                {
                    "statement_key": "c1",
                    "race_id": "race-unresolved",
                    "candidate_name": "Alex Example",
                    "election_date": "2024-06-04",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "topic": "housing",
                    "subtopic": "rent_control",
                    "stance": "support",
                    "quote": "Rent control now.",
                    "source_url": "https://example.org/alex",
                    "source_type": "campaign_page",
                    "published_date": "2024-05-01",
                    "locator": "Platform",
                    "direct_opponent_name": "",
                    "notes": "verified text without roster metadata",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "endorsements.csv",
            [
                {
                    "endorsement_id": "endorse-connolly",
                    "race_id": "ma-house-26th-middlesex-dem-primary-2016",
                    "candidate_id": "mike-connolly",
                    "candidate_name": "Mike Connolly",
                    "office": "State Representative 26th Middlesex District",
                    "jurisdiction": "Massachusetts 26th Middlesex District",
                    "election_date": "2016-09-08",
                    "primary_party": "Democratic",
                    "endorsing_body": "Boston DSA",
                    "endorsement_date": "",
                    "endorsement_source_document_id": "doc-a",
                    "outcome": "Win",
                    "verification_status": "verified",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_candidates.csv",
            [
                {
                    "race_candidate_id": "connolly",
                    "race_id": "ma-house-26th-middlesex-dem-primary-2016",
                    "candidate_id": "mike-connolly",
                    "candidate_name": "Mike Connolly",
                    "party": "Democratic",
                    "role": "endorsed",
                    "ballot_status": "certified",
                    "outcome": "Win",
                    "evidence_status": "verified",
                    "source_url": "https://electionstats.state.ma.us/elections/view/129704",
                    "notes": "",
                },
                {
                    "race_candidate_id": "toomey",
                    "race_id": "ma-house-26th-middlesex-dem-primary-2016",
                    "candidate_id": "timothy-j-toomey-jr",
                    "candidate_name": "Timothy J. Toomey, Jr.",
                    "party": "Democratic",
                    "role": "opponent",
                    "ballot_status": "certified",
                    "outcome": "Loss",
                    "evidence_status": "verified",
                    "source_url": "https://electionstats.state.ma.us/elections/view/129704",
                    "notes": "",
                },
            ],
        )

        result = build_race_registry(self._paths(root))

        self.assertEqual(result.race_rows, 3)
        self.assertEqual(result.in_scope_race_rows, 3)
        self.assertEqual(result.resolved_state_race_rows, 2)
        self.assertEqual(result.unresolved_race_rows, 2)

        registry_rows = self._read_csv(result.registry_path)
        by_id = {row["race_id"]: row for row in registry_rows}
        self.assertEqual(by_id["race-manual"]["state_code"], "MA")
        self.assertEqual(by_id["race-manual"]["office_status"], "manual_verified")
        self.assertEqual(by_id["race-manual"]["certified_opponents"], "Timothy J. Toomey, Jr.")
        self.assertEqual(by_id["race-hint"]["state_code"], "MO")
        self.assertEqual(by_id["race-hint"]["office"], "US House")
        self.assertEqual(by_id["race-hint"]["jurisdiction"], "District 1")
        self.assertEqual(by_id["race-unresolved"]["state_status"], "unresolved")
        self.assertIn("state", by_id["race-unresolved"]["unresolved_fields"])

        represented_rows = self._read_csv(result.represented_state_cycles_path)
        self.assertEqual(len(represented_rows), 2)
        self.assertEqual({row["state_code"] for row in represented_rows}, {"MA", "MO"})

        summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["represented_state_cycles"], 2)
        self.assertEqual(summary["in_scope_unresolved_races"], 2)

    def test_national_census_seeds_primary_absent_from_quotation_corpus(self) -> None:
        root = self._scenario_root("national_source_first")
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "race_id": "existing-race",
                    "candidate_name": "Existing Candidate",
                    "election_date": "2024-06-25",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "notes": "",
                }
            ],
        )
        self._write_csv(
            root
            / "data"
            / "manual"
            / "national_census_resolutions_2024.csv",
            [
                {
                    "record_id": "rec-source-first",
                    "campaign": "New Candidate",
                    "endorsement_election_date": "2024-11-05",
                    "office": "State Assembly",
                    "classification": "democratic_primary",
                    "primary_date": "2024-06-25",
                    "primary_party": "Democratic",
                    "state": "New York",
                    "state_code": "NY",
                    "jurisdiction": "District 1",
                    "official_election_source": "https://elections.ny.gov/",
                    "opponents": "Primary Opponent",
                    "verification_status": "official",
                    "notes": "Certified primary record.",
                }
            ],
        )

        result = build_race_registry(self._paths(root))
        rows = self._read_csv(result.registry_path)
        seeded = next(row for row in rows if row["endorsed_candidate"] == "New Candidate")

        self.assertEqual(result.race_rows, 2)
        self.assertEqual(result.in_scope_race_rows, 2)
        self.assertEqual(seeded["opponent_candidates"], "Primary Opponent")
        self.assertEqual(seeded["metadata_source"], "resolution_verified")
        summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["national_democratic_primary_seeded_races"], 1)

    def test_metadata_inference_resolves_unambiguous_race_and_skips_ambiguous_conflicts(self) -> None:
        root = self._scenario_root("metadata_inference")
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "m1",
                    "race_id": "race-meta",
                    "candidate_name": "Alex Example",
                    "election_date": "2024-06-25",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "topic": "",
                    "subtopic": "",
                    "stance": "support",
                    "quote": "Build housing.",
                    "source_url": "https://alexforassembly.example/issues",
                    "source_type": "campaign_page",
                    "published_date": "2024-05-01",
                    "locator": "Issues",
                    "direct_opponent_name": "",
                    "notes": "",
                },
                {
                    "statement_key": "m2",
                    "race_id": "race-meta",
                    "candidate_name": "Blair Example",
                    "election_date": "2024-06-25",
                    "party": "Democratic",
                    "role": "opponent",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "Alex Example",
                    "notes": "",
                },
                {
                    "statement_key": "a1",
                    "race_id": "race-ambiguous",
                    "candidate_name": "Casey Example",
                    "election_date": "2024-06-25",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "topic": "",
                    "subtopic": "",
                    "stance": "support",
                    "quote": "Transit now.",
                    "source_url": "https://casey.example/issues",
                    "source_type": "campaign_page",
                    "published_date": "2024-05-01",
                    "locator": "Issues",
                    "direct_opponent_name": "",
                    "notes": "",
                },
                {
                    "statement_key": "a2",
                    "race_id": "race-ambiguous",
                    "candidate_name": "Devon Example",
                    "election_date": "2024-06-25",
                    "party": "Democratic",
                    "role": "opponent",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "Casey Example",
                    "notes": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "candidate_document_metadata.csv",
            [
                {
                    "document_id": "doc-meta-endorsed",
                    "candidate_name": "Alex Example",
                    "role": "endorsed",
                    "race_id": "race-meta",
                    "election_date": "2024-06-25",
                    "publication_date": "2024-05-20",
                    "campaign_window_status": "in_window",
                    "source_type": "official_voter_guide",
                    "source_url": "https://www.nycvotes.org/whats-on-the-ballot/2024-state-and-federal-primary-election/member-of-the-assembly/profile?geoAreaAbbr=51",
                    "title": "Alex Example | NYC Votes",
                    "coverage_status": "found_unverified",
                    "extraction_status": "extracted",
                    "analysis_scope": "analysis",
                },
                {
                    "document_id": "doc-meta-opponent",
                    "candidate_name": "Blair Example",
                    "role": "opponent",
                    "race_id": "race-meta",
                    "election_date": "2024-06-25",
                    "publication_date": "2024-05-22",
                    "campaign_window_status": "in_window",
                    "source_type": "candidate_questionnaire",
                    "source_url": "https://jimowles.org/news/blair-example-for-city-council",
                    "title": "Candidate Answers: Blair Example for State Assembly District 51 — Jim Owles",
                    "coverage_status": "found_unverified",
                    "extraction_status": "extracted",
                    "analysis_scope": "analysis",
                },
                {
                    "document_id": "doc-ambiguous-1",
                    "candidate_name": "Casey Example",
                    "role": "endorsed",
                    "race_id": "race-ambiguous",
                    "election_date": "2024-06-25",
                    "publication_date": "2024-05-20",
                    "campaign_window_status": "in_window",
                    "source_type": "candidate_questionnaire",
                    "source_url": "https://example.org/casey-profile",
                    "title": "Candidate answers: Casey Example for City Council District 1",
                    "coverage_status": "found_unverified",
                    "extraction_status": "extracted",
                    "analysis_scope": "analysis",
                },
                {
                    "document_id": "doc-ambiguous-2",
                    "candidate_name": "Devon Example",
                    "role": "opponent",
                    "race_id": "race-ambiguous",
                    "election_date": "2024-06-25",
                    "publication_date": "2024-05-21",
                    "campaign_window_status": "in_window",
                    "source_type": "candidate_questionnaire",
                    "source_url": "https://example.org/devon-profile",
                    "title": "Candidate answers: Devon Example for Mayor",
                    "coverage_status": "found_unverified",
                    "extraction_status": "extracted",
                    "analysis_scope": "analysis",
                },
            ],
        )

        result = build_race_registry(self._paths(root))
        rows = {row["race_id"]: row for row in self._read_csv(result.registry_path)}

        resolved = rows["race-meta"]
        self.assertEqual(resolved["state_code"], "NY")
        self.assertEqual(resolved["office"], "State Assembly")
        self.assertEqual(resolved["jurisdiction"], "District 51")
        self.assertEqual(resolved["official_election_source_status"], "metadata_inferred")
        self.assertEqual(resolved["state_confidence"], "high")
        self.assertIn("official_host", resolved["state_source"])
        self.assertEqual(resolved["unresolved_fields"], "")

        ambiguous = rows["race-ambiguous"]
        self.assertEqual(ambiguous["office_status"], "unresolved")
        self.assertEqual(ambiguous["jurisdiction_status"], "unresolved")
        self.assertIn("office", ambiguous["unresolved_fields"])
        self.assertIn("jurisdiction", ambiguous["unresolved_fields"])

    def test_resolution_rows_override_hints_and_validate_conflicts(self) -> None:
        root = self._scenario_root("resolution_override")
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "r1",
                    "race_id": "race-resolution",
                    "candidate_name": "Cori Bush",
                    "election_date": "2020-08-04",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "Searched exact-name and 2020-MO-US-HOUSE-D1-DEM web results; no accessible exact first-party quote was recovered.",
                },
                {
                    "statement_key": "r2",
                    "race_id": "race-resolution",
                    "candidate_name": "William Lacy Clay",
                    "election_date": "2020-08-04",
                    "party": "Democratic",
                    "role": "opponent",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "Cori Bush",
                    "notes": "Searched exact-name and 2020-MO-US-HOUSE-D1-DEM web results; no accessible exact first-party quote was recovered.",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_registry_resolutions_2020.csv",
            [
                {
                    "race_id": "race-resolution",
                    "election_date": "2020-08-04",
                    "office": "",
                    "jurisdiction": "",
                    "state": "",
                    "state_code": "",
                    "official_election_source": "",
                    "verification_status": "source_unavailable",
                    "notes": "Curated source-unavailable resolution should suppress weaker hint inference.",
                }
            ],
        )

        result = build_race_registry(self._paths(root))
        row = self._read_csv(result.registry_path)[0]
        self.assertEqual(row["metadata_source"], "resolution_source_unavailable")
        self.assertEqual(row["official_election_source_status"], "source_unavailable")
        self.assertEqual(row["official_election_source_confidence"], "")
        self.assertEqual(row["state_status"], "unresolved")
        self.assertEqual(row["office_status"], "unresolved")
        self.assertIn("state", row["unresolved_fields"])

    def test_reclassifies_non_authority_resolution_sources_and_excludes_generic_gov_metadata(self) -> None:
        root = self._scenario_root("source_classification")
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "t1",
                    "race_id": "race-tlaib",
                    "candidate_name": "Rashida Tlaib",
                    "election_date": "2026-08-04",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "topic": "",
                    "subtopic": "",
                    "stance": "support",
                    "quote": "Workers first.",
                    "source_url": "https://rashidaforcongress.com/",
                    "source_type": "campaign_statement",
                    "published_date": "2026-01-28",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "",
                },
                {
                    "statement_key": "t2",
                    "race_id": "race-tlaib",
                    "candidate_name": "Byron Nolen",
                    "election_date": "2026-08-04",
                    "party": "Democratic",
                    "role": "opponent",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "Rashida Tlaib",
                    "notes": "",
                },
                {
                    "statement_key": "v1",
                    "race_id": "race-votekarris",
                    "candidate_name": "Valerie Thomason",
                    "election_date": "2026-06-09",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "topic": "",
                    "subtopic": "",
                    "stance": "support",
                    "quote": "Housing now.",
                    "source_url": "https://valerie.example/",
                    "source_type": "campaign_page",
                    "published_date": "2026-04-01",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "",
                },
                {
                    "statement_key": "v2",
                    "race_id": "race-votekarris",
                    "candidate_name": "Venise L. Karris",
                    "election_date": "2026-06-09",
                    "party": "Democratic",
                    "role": "opponent",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "Valerie Thomason",
                    "notes": "",
                },
                {
                    "statement_key": "m1",
                    "race_id": "race-mcadams",
                    "candidate_name": "Ben McAdams",
                    "election_date": "2026-03-17",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "",
                },
                {
                    "statement_key": "g1",
                    "race_id": "race-generic-gov",
                    "candidate_name": "Alex Example",
                    "election_date": "2024-06-25",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "topic": "",
                    "subtopic": "",
                    "stance": "support",
                    "quote": "Transit now.",
                    "source_url": "https://alex.example/issues",
                    "source_type": "campaign_page",
                    "published_date": "2024-05-01",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "",
                },
                {
                    "statement_key": "g2",
                    "race_id": "race-generic-gov",
                    "candidate_name": "Blair Example",
                    "election_date": "2024-06-25",
                    "party": "Democratic",
                    "role": "opponent",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "Alex Example",
                    "notes": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_registry_resolutions_2026.csv",
            [
                {
                    "race_id": "race-tlaib",
                    "election_date": "2026-08-04",
                    "office": "US House",
                    "jurisdiction": "District 12",
                    "state": "Michigan",
                    "state_code": "MI",
                    "official_election_source": "https://tlaib.house.gov/",
                    "verification_status": "verified",
                    "notes": "Incumbent House site should not count as an official election source.",
                },
                {
                    "race_id": "race-votekarris",
                    "election_date": "2026-06-09",
                    "office": "State Assembly",
                    "jurisdiction": "District 10",
                    "state": "Nevada",
                    "state_code": "NV",
                    "official_election_source": "https://votekarris.com/",
                    "verification_status": "verified",
                    "notes": "Candidate campaign site should move to supporting_source.",
                },
                {
                    "race_id": "race-mcadams",
                    "election_date": "2026-03-17",
                    "office": "State Senate",
                    "jurisdiction": "District 24",
                    "state": "Illinois",
                    "state_code": "IL",
                    "official_election_source": "https://mcadamsforil.com/",
                    "verification_status": "verified",
                    "notes": "Campaign site should move to supporting_source.",
                },
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "candidate_document_metadata.csv",
            [
                {
                    "document_id": "doc-generic",
                    "candidate_name": "Alex Example",
                    "role": "endorsed",
                    "race_id": "race-generic-gov",
                    "election_date": "2024-06-25",
                    "publication_date": "2024-05-10",
                    "campaign_window_status": "in_window",
                    "source_type": "candidate_questionnaire",
                    "source_url": "https://city.example.gov/mayor/alex-example",
                    "title": "Alex Example | Office of the Mayor",
                    "coverage_status": "found_unverified",
                    "extraction_status": "extracted",
                    "analysis_scope": "analysis",
                },
            ],
        )

        result = build_race_registry(self._paths(root))
        rows = {row["race_id"]: row for row in self._read_csv(result.registry_path)}

        self.assertEqual(rows["race-tlaib"]["official_election_source"], "")
        self.assertEqual(rows["race-tlaib"]["official_election_source_status"], "unresolved")
        self.assertEqual(rows["race-tlaib"]["supporting_source"], "https://tlaib.house.gov/")
        self.assertEqual(rows["race-tlaib"]["supporting_source_type"], "incumbent_office")

        self.assertEqual(rows["race-votekarris"]["official_election_source"], "")
        self.assertEqual(rows["race-votekarris"]["supporting_source"], "https://votekarris.com/")
        self.assertEqual(rows["race-votekarris"]["supporting_source_type"], "candidate_controlled")

        self.assertEqual(rows["race-mcadams"]["official_election_source"], "")
        self.assertEqual(rows["race-mcadams"]["supporting_source"], "https://mcadamsforil.com/")
        self.assertEqual(rows["race-mcadams"]["supporting_source_type"], "candidate_controlled")

        self.assertEqual(rows["race-generic-gov"]["official_election_source"], "")
        self.assertEqual(rows["race-generic-gov"]["official_election_source_status"], "unresolved")

    def test_duplicate_contests_merge_to_canonical_rows_and_alias_mapping(self) -> None:
        root = self._scenario_root("duplicate_merge")
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "mi1",
                    "race_id": "race-mi12-a",
                    "candidate_name": "Rashida Tlaib",
                    "election_date": "2026-08-04",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "topic": "",
                    "subtopic": "",
                    "stance": "support",
                    "quote": "Justice now.",
                    "source_url": "https://rashida.example/",
                    "source_type": "campaign_statement",
                    "published_date": "2026-01-28",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "",
                },
                {
                    "statement_key": "mi2",
                    "race_id": "race-mi12-a",
                    "candidate_name": "Byron H. Nolen",
                    "election_date": "2026-08-04",
                    "party": "Democratic",
                    "role": "opponent",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "Rashida Tlaib",
                    "notes": "",
                },
                {
                    "statement_key": "mi3",
                    "race_id": "race-mi12-b",
                    "candidate_name": "Rashida Tlaib",
                    "election_date": "2026-08-04",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "topic": "",
                    "subtopic": "",
                    "stance": "support",
                    "quote": "Justice now.",
                    "source_url": "https://rashida.example/",
                    "source_type": "campaign_statement",
                    "published_date": "2026-01-28",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "",
                },
                {
                    "statement_key": "mi4",
                    "race_id": "race-mi12-b",
                    "candidate_name": "Byron Nolen",
                    "election_date": "2026-08-04",
                    "party": "Democratic",
                    "role": "opponent",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "Rashida Tlaib",
                    "notes": "",
                },
                {
                    "statement_key": "nv1",
                    "race_id": "race-nv34-a",
                    "candidate_name": "Shaun R. Navarro",
                    "election_date": "2026-06-09",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "topic": "",
                    "subtopic": "",
                    "stance": "support",
                    "quote": "Workers first.",
                    "source_url": "https://navarro.example/",
                    "source_type": "campaign_page",
                    "published_date": "2026-02-01",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "",
                },
                {
                    "statement_key": "nv2",
                    "race_id": "race-nv34-a",
                    "candidate_name": "Hanadi Nadeem",
                    "election_date": "2026-06-09",
                    "party": "Democratic",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "topic": "",
                    "subtopic": "",
                    "stance": "support",
                    "quote": "Higher wages.",
                    "source_url": "https://hanadi.example/",
                    "source_type": "campaign_page",
                    "published_date": "2026-03-01",
                    "locator": "",
                    "direct_opponent_name": "Shaun R. Navarro",
                    "notes": "",
                },
                {
                    "statement_key": "nv3",
                    "race_id": "race-nv34-b",
                    "candidate_name": "Shaun Navarro",
                    "election_date": "2026-06-09",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "topic": "",
                    "subtopic": "",
                    "stance": "support",
                    "quote": "Workers first.",
                    "source_url": "https://navarro.example/",
                    "source_type": "campaign_page",
                    "published_date": "2026-02-01",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "",
                },
                {
                    "statement_key": "nv4",
                    "race_id": "race-nv34-b",
                    "candidate_name": "Hanadi Nadeem",
                    "election_date": "2026-06-09",
                    "party": "Democratic",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "topic": "",
                    "subtopic": "",
                    "stance": "support",
                    "quote": "Higher wages.",
                    "source_url": "https://hanadi.example/",
                    "source_type": "campaign_page",
                    "published_date": "2026-03-01",
                    "locator": "",
                    "direct_opponent_name": "Shaun Navarro",
                    "notes": "",
                },
                {
                    "statement_key": "il1",
                    "race_id": "race-il24-a",
                    "candidate_name": "Ben McAdams",
                    "election_date": "2026-03-17",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "",
                },
                {
                    "statement_key": "il2",
                    "race_id": "race-il24-b",
                    "candidate_name": "Benjamin \"Ben\" McAdams",
                    "election_date": "2026-03-17",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_registry_resolutions_2026.csv",
            [
                {
                    "race_id": "race-mi12-a",
                    "election_date": "2026-08-04",
                    "office": "US House",
                    "jurisdiction": "District 12",
                    "state": "Michigan",
                    "state_code": "MI",
                    "official_election_source": "https://tlaib.house.gov/",
                    "verification_status": "verified",
                    "notes": "Duplicate contest A.",
                },
                {
                    "race_id": "race-mi12-b",
                    "election_date": "2026-08-04",
                    "office": "US House",
                    "jurisdiction": "District 12",
                    "state": "Michigan",
                    "state_code": "MI",
                    "official_election_source": "https://tlaib.house.gov/",
                    "verification_status": "verified",
                    "notes": "Duplicate contest B.",
                },
                {
                    "race_id": "race-nv34-a",
                    "election_date": "2026-06-09",
                    "office": "State Assembly",
                    "jurisdiction": "District 34",
                    "state": "Nevada",
                    "state_code": "NV",
                    "official_election_source": "https://navarrofornevada.com/",
                    "verification_status": "verified",
                    "notes": "Duplicate contest A.",
                },
                {
                    "race_id": "race-nv34-b",
                    "election_date": "2026-06-09",
                    "office": "State Assembly",
                    "jurisdiction": "District 34",
                    "state": "Nevada",
                    "state_code": "NV",
                    "official_election_source": "https://navarrofornevada.com/",
                    "verification_status": "verified",
                    "notes": "Duplicate contest B.",
                },
                {
                    "race_id": "race-il24-a",
                    "election_date": "2026-03-17",
                    "office": "State Senate",
                    "jurisdiction": "District 24",
                    "state": "Illinois",
                    "state_code": "IL",
                    "official_election_source": "https://mcadamsforil.com/",
                    "verification_status": "verified",
                    "notes": "Duplicate contest A.",
                },
                {
                    "race_id": "race-il24-b",
                    "election_date": "2026-03-17",
                    "office": "State Senate",
                    "jurisdiction": "District 24",
                    "state": "Illinois",
                    "state_code": "IL",
                    "official_election_source": "https://mcadamsforil.com/",
                    "verification_status": "verified",
                    "notes": "Duplicate contest B.",
                },
            ],
        )

        result = build_race_registry(self._paths(root))
        self.assertEqual(result.race_rows, 3)

        summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["merged_alias_count"], 3)
        self.assertEqual(summary["in_scope_races"], 3)

        registry_rows = {row["race_id"]: row for row in self._read_csv(result.registry_path)}
        self.assertIn("race-mi12-a", registry_rows)
        self.assertEqual(
            registry_rows["race-mi12-a"]["scope_kind"],
            "tracked_dsa_endorsed_democratic_primary",
        )
        self.assertEqual(registry_rows["race-mi12-a"]["merged_race_id_count"], "2")
        self.assertEqual(
            registry_rows["race-mi12-a"]["all_candidates"],
            "Byron H. Nolen | Rashida Tlaib",
        )
        self.assertEqual(
            registry_rows["race-nv34-a"]["all_candidates"],
            "Hanadi Nadeem | Shaun R. Navarro",
        )
        self.assertEqual(
            registry_rows["race-il24-a"]["all_candidates"],
            "Benjamin \"Ben\" McAdams",
        )

        alias_rows = self._read_csv(result.alias_mapping_path)
        self.assertEqual(len(alias_rows), 6)
        self.assertEqual(
            {row["canonical_race_id"] for row in alias_rows if row["merge_group_size"] == "2"},
            {"race-mi12-a", "race-nv34-a", "race-il24-a"},
        )

    def test_source_unavailable_valid_official_source_uses_high_confidence(self) -> None:
        root = self._scenario_root("source_unavailable_confidence")
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "s1",
                    "race_id": "race-source-unavailable",
                    "candidate_name": "Pamela Stevenson",
                    "election_date": "2022-05-17",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_registry_resolutions_2022.csv",
            [
                {
                    "race_id": "race-source-unavailable",
                    "election_date": "2022-05-17",
                    "office": "State House",
                    "jurisdiction": "District 43",
                    "state": "Kentucky",
                    "state_code": "KY",
                    "official_election_source": "https://elect.ky.gov/results/2020-2029/Pages/2022.aspx",
                    "verification_status": "source_unavailable",
                    "notes": "Official authority URL exists, but candidate verification remained unavailable.",
                }
            ],
        )

        row = self._read_csv(build_race_registry(self._paths(root)).registry_path)[0]
        self.assertEqual(row["official_election_source_status"], "source_unavailable")
        self.assertEqual(row["official_election_source_confidence"], "high")
        self.assertNotEqual(row["official_election_source_confidence"], "verified")

    def test_official_government_campaign_finance_filing_is_election_source(self) -> None:
        root = self._scenario_root("official_campaign_finance_filing")
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "s1",
                    "race_id": "race-tucson-filing",
                    "candidate_name": "Sadie Shaw",
                    "election_date": "2025-08-05",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "",
                }
            ],
        )
        filing_url = (
            "https://www.tucsonaz.gov/files/sharedassets/public/v/1/clerks/documents/"
            "campaign-finance/campaign-finance-reports/2025/shaw-report.pdf"
        )
        self._write_csv(
            root / "data" / "manual" / "race_registry_resolutions_2025.csv",
            [
                {
                    "race_id": "race-tucson-filing",
                    "election_date": "2025-08-05",
                    "office": "City Council",
                    "jurisdiction": "Ward 3 (Tucson)",
                    "state": "Arizona",
                    "state_code": "AZ",
                    "official_election_source": filing_url,
                    "verification_status": "verified",
                    "notes": "Official city campaign-finance filing.",
                }
            ],
        )

        row = self._read_csv(build_race_registry(self._paths(root)).registry_path)[0]
        self.assertEqual(row["official_election_source"], filing_url)
        self.assertEqual(row["official_election_source_status"], "resolution_verified")
        self.assertEqual(row["official_election_source_confidence"], "verified")
        self.assertEqual(row["supporting_source"], "")

    def test_resolution_validation_rejects_duplicate_and_manual_conflict(self) -> None:
        root = self._scenario_root("resolution_conflict")
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "m1",
                    "race_id": "race-manual",
                    "candidate_name": "Mike Connolly",
                    "election_date": "2016-09-08",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "",
                },
                {
                    "statement_key": "m2",
                    "race_id": "race-manual",
                    "candidate_name": "Timothy J. Toomey, Jr.",
                    "election_date": "2016-09-08",
                    "party": "Democratic",
                    "role": "opponent",
                    "evidence_status": "source_unavailable",
                    "topic": "",
                    "subtopic": "",
                    "stance": "unclear",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "Mike Connolly",
                    "notes": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "endorsements.csv",
            [
                {
                    "endorsement_id": "endorse-connolly",
                    "race_id": "ma-house-26th-middlesex-dem-primary-2016",
                    "candidate_id": "mike-connolly",
                    "candidate_name": "Mike Connolly",
                    "office": "State Representative",
                    "jurisdiction": "Massachusetts 26th Middlesex District",
                    "election_date": "2016-09-08",
                    "primary_party": "Democratic",
                    "endorsing_body": "Boston DSA",
                    "endorsement_date": "",
                    "endorsement_source_document_id": "doc-a",
                    "outcome": "Win",
                    "verification_status": "verified",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_candidates.csv",
            [
                {
                    "race_candidate_id": "connolly",
                    "race_id": "ma-house-26th-middlesex-dem-primary-2016",
                    "candidate_id": "mike-connolly",
                    "candidate_name": "Mike Connolly",
                    "party": "Democratic",
                    "role": "endorsed",
                    "ballot_status": "certified",
                    "outcome": "Win",
                    "evidence_status": "verified",
                    "source_url": "https://electionstats.state.ma.us/elections/view/129704",
                    "notes": "",
                },
                {
                    "race_candidate_id": "toomey",
                    "race_id": "ma-house-26th-middlesex-dem-primary-2016",
                    "candidate_id": "timothy-j-toomey-jr",
                    "candidate_name": "Timothy J. Toomey, Jr.",
                    "party": "Democratic",
                    "role": "opponent",
                    "ballot_status": "certified",
                    "outcome": "Loss",
                    "evidence_status": "verified",
                    "source_url": "https://electionstats.state.ma.us/elections/view/129704",
                    "notes": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_registry_resolutions_2016.csv",
            [
                {
                    "race_id": "race-manual",
                    "election_date": "2016-09-08",
                    "office": "US House",
                    "jurisdiction": "District 1",
                    "state": "Massachusetts",
                    "state_code": "MA",
                    "official_election_source": "https://example.org/conflict",
                    "verification_status": "verified",
                    "notes": "Intentional conflict with verified manual roster.",
                }
            ],
        )

        with self.assertRaisesRegex(Exception, "conflicts with verified manual race"):
            build_race_registry(self._paths(root))

    def test_resolution_schema_validation_rejects_invalid_verified_row(self) -> None:
        root = self._scenario_root("resolution_schema")
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "x1",
                    "race_id": "race-x",
                    "candidate_name": "Alex Example",
                    "election_date": "2024-06-04",
                    "party": "Democratic",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "topic": "",
                    "subtopic": "",
                    "stance": "support",
                    "quote": "Housing now.",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "direct_opponent_name": "",
                    "notes": "",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_registry_resolutions_2024.csv",
            [
                {
                    "race_id": "race-x",
                    "election_date": "2024-06-04",
                    "office": "State House",
                    "jurisdiction": "District 1",
                    "state": "Exampleland",
                    "state_code": "EX",
                    "official_election_source": "",
                    "verification_status": "verified",
                    "notes": "Invalid verified row.",
                }
            ],
        )

        with self.assertRaisesRegex(Exception, "unknown state_code|verified row missing official_election_source"):
            build_race_registry(self._paths(root))

    def _scenario_root(self, name: str) -> Path:
        root = SCRATCH_ROOT / name
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _paths(self, root: Path) -> RaceRegistryPaths:
        return RaceRegistryPaths(
            candidate_corpus_path=root / "data" / "analysis" / "candidate_text_corpus.csv",
            manual_endorsements_path=root / "data" / "manual" / "endorsements.csv",
            manual_race_candidates_path=root / "data" / "manual" / "race_candidates.csv",
            manual_resolution_paths=tuple(
                sorted((root / "data" / "manual").glob("race_registry_resolutions_*.csv"))
            ),
            processed_race_rosters_path=root / "data" / "processed" / "race_rosters_discovered.csv",
            output_dir=root / "data" / "processed",
            candidate_document_metadata_path=root / "data" / "processed" / "candidate_document_metadata.csv",
            candidate_document_full_text_path=root / "data" / "processed" / "candidate_document_full_text.jsonl",
            national_census_resolution_paths=tuple(
                sorted(
                    (root / "data" / "manual").glob(
                        "national_census_resolutions_*.csv"
                    )
                )
            ),
        )

    def _write_csv(self, path: Path, rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
