import csv
import json
import shutil
import unittest
from pathlib import Path

from dsa_analysis.organizational_context import (
    FetchCapture,
    OrganizationalContextFetchError,
    OrganizationalContextPaths,
    build_organizational_context_inventory,
    run_organizational_context_fetch_pass,
)

SCRATCH_ROOT = Path(__file__).resolve().parent / "_scratch_organizational_context"


class OrganizationalContextTests(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree(SCRATCH_ROOT, ignore_errors=True)
        SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(SCRATCH_ROOT, ignore_errors=True))

    def test_inventory_derives_denominator_from_race_registry_and_generates_gap_rows(self) -> None:
        root = self._scenario_root("derived")
        self._write_csv(
            root / "data" / "processed" / "race_registry.csv",
            [
                {
                    "race_id": "race-ma",
                    "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                    "election_date": "2016-09-08",
                    "election_year": "2016",
                    "primary_party": "Democratic",
                    "endorsed_candidate": "Mike Connolly",
                    "endorsed_candidates": "Mike Connolly",
                    "unopposed_candidates": "",
                    "opponent_candidates": "Timothy J. Toomey, Jr.",
                    "all_candidates": "Mike Connolly | Timothy J. Toomey, Jr.",
                    "candidate_count": "2",
                    "role_set": "endorsed | opponent",
                    "party_set": "Democratic",
                    "evidence_statuses": "source_unavailable",
                    "office": "State Representative",
                    "office_status": "manual_verified",
                    "jurisdiction": "Massachusetts 26th Middlesex District",
                    "jurisdiction_status": "manual_verified",
                    "state": "Massachusetts",
                    "state_code": "MA",
                    "state_status": "manual_verified",
                    "official_election_source": "https://example.org/ma-results",
                    "official_election_source_status": "manual_verified",
                    "certified_opponents": "Timothy J. Toomey, Jr.",
                    "certified_opponents_status": "manual_verified",
                    "endorsing_bodies": "Boston DSA",
                    "metadata_source": "manual_verified",
                    "source_reference": "ma-race",
                    "unresolved_fields": "",
                },
                {
                    "race_id": "race-me",
                    "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                    "election_date": "2016-06-14",
                    "election_year": "2016",
                    "primary_party": "Democratic",
                    "endorsed_candidate": "Mike Sylvester",
                    "endorsed_candidates": "Mike Sylvester",
                    "unopposed_candidates": "",
                    "opponent_candidates": "Andrew Edwards",
                    "all_candidates": "Mike Sylvester | Andrew Edwards",
                    "candidate_count": "2",
                    "role_set": "endorsed | opponent",
                    "party_set": "Democratic",
                    "evidence_statuses": "verified | source_unavailable",
                    "office": "State Representative",
                    "office_status": "hint_parsed",
                    "jurisdiction": "District 39",
                    "jurisdiction_status": "hint_parsed",
                    "state": "Maine",
                    "state_code": "ME",
                    "state_status": "hint_parsed",
                    "official_election_source": "",
                    "official_election_source_status": "unresolved",
                    "certified_opponents": "Andrew Edwards",
                    "certified_opponents_status": "corpus_candidate_set",
                    "endorsing_bodies": "DSA National",
                    "metadata_source": "hint_parsed",
                    "source_reference": "2016-ME-HOUSE-39-DEM",
                    "unresolved_fields": "official_election_source",
                },
                {
                    "race_id": "race-unresolved",
                    "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                    "election_date": "2024-06-04",
                    "election_year": "2024",
                    "primary_party": "Democratic",
                    "endorsed_candidate": "Alex Example",
                    "endorsed_candidates": "Alex Example",
                    "unopposed_candidates": "",
                    "opponent_candidates": "",
                    "all_candidates": "Alex Example",
                    "candidate_count": "1",
                    "role_set": "endorsed",
                    "party_set": "Democratic",
                    "evidence_statuses": "verified",
                    "office": "",
                    "office_status": "unresolved",
                    "jurisdiction": "",
                    "jurisdiction_status": "unresolved",
                    "state": "",
                    "state_code": "",
                    "state_status": "unresolved",
                    "official_election_source": "",
                    "official_election_source_status": "unresolved",
                    "certified_opponents": "",
                    "certified_opponents_status": "unresolved",
                    "endorsing_bodies": "",
                    "metadata_source": "corpus_only",
                    "source_reference": "",
                    "unresolved_fields": "office | jurisdiction | state | official_election_source | certified_opponents",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "organizational_context_sources.csv",
            [
                {
                    "context_entry_id": "dnc-ma-2016",
                    "state": "Massachusetts",
                    "state_code": "MA",
                    "cycle_year": "2016",
                    "organization_level": "national",
                    "context_category": "dnc_national",
                    "organization": "Democratic National Committee",
                    "endorsing_body": "",
                    "title": "2016 DNC Platform",
                    "platform_type": "national_party_platform",
                    "adoption_date": "2016-07-25",
                    "effective_date": "2016-07-25",
                    "source_url": "https://example.org/dnc-2016.pdf",
                    "archive_url": "",
                    "verification_status": "verified",
                    "notes": "Verified",
                },
                {
                    "context_entry_id": "ma-state-2016",
                    "state": "Massachusetts",
                    "state_code": "MA",
                    "cycle_year": "2016",
                    "organization_level": "state",
                    "context_category": "state_democratic_party",
                    "organization": "Massachusetts Democratic Party",
                    "endorsing_body": "",
                    "title": "MA platform",
                    "platform_type": "state_party_platform_archive",
                    "adoption_date": "",
                    "effective_date": "",
                    "source_url": "https://example.org/ma-platform",
                    "archive_url": "",
                    "verification_status": "searched_not_found",
                    "notes": "Need archival recovery",
                },
            ],
        )

        result = build_organizational_context_inventory(self._paths(root))

        self.assertEqual(result.represented_state_cycle_rows, 2)
        self.assertTrue(result.all_represented_state_cycles_have_status)
        self.assertGreater(result.platform_gap_rows, 0)

        coverage_rows = self._read_csv(result.coverage_path)
        by_key = {(row["state_code"], row["cycle_year"]): row for row in coverage_rows}
        self.assertEqual(by_key[("MA", "2016")]["dsa_state_local_status"], "not_searched")
        self.assertEqual(by_key[("ME", "2016")]["dsa_state_local_status"], "not_applicable")
        self.assertEqual(by_key[("ME", "2016")]["dnc_national_status"], "verified")

        collection_rows = self._read_csv(result.collection_queue_path)
        self.assertTrue(any(row["queue_reason"] == "add_registry_seed" for row in collection_rows))

        fetch_rows = self._read_csv(result.fetch_queue_path)
        self.assertEqual(len(fetch_rows), 1)

        summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["represented_state_cycles"], 2)
        self.assertEqual(summary["coverage"]["platform_gap_rows"], result.platform_gap_rows)

    def test_national_platforms_carry_forward_by_effective_period(self) -> None:
        root = self._scenario_root("carry_forward")
        self._write_csv(
            root / "data" / "processed" / "race_registry.csv",
            [
                {
                    "race_id": "race-ca-2024",
                    "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                    "election_date": "2024-03-05",
                    "election_year": "2024",
                    "primary_party": "Democratic",
                    "endorsed_candidate": "Ana Example",
                    "endorsed_candidates": "Ana Example",
                    "unopposed_candidates": "",
                    "opponent_candidates": "Bo Example",
                    "all_candidates": "Ana Example | Bo Example",
                    "candidate_count": "2",
                    "role_set": "endorsed | opponent",
                    "party_set": "Democratic",
                    "evidence_statuses": "verified",
                    "office": "Assembly",
                    "office_status": "manual_verified",
                    "jurisdiction": "District 1",
                    "jurisdiction_status": "manual_verified",
                    "state": "California",
                    "state_code": "CA",
                    "state_status": "manual_verified",
                    "official_election_source": "https://example.org/ca-results",
                    "official_election_source_status": "manual_verified",
                    "certified_opponents": "Bo Example",
                    "certified_opponents_status": "manual_verified",
                    "endorsing_bodies": "DSA National",
                    "metadata_source": "manual_verified",
                    "source_reference": "ca-race",
                    "unresolved_fields": "",
                },
                {
                    "race_id": "race-wa-2026",
                    "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                    "election_date": "2026-08-04",
                    "election_year": "2026",
                    "primary_party": "Democratic",
                    "endorsed_candidate": "Cy Example",
                    "endorsed_candidates": "Cy Example",
                    "unopposed_candidates": "",
                    "opponent_candidates": "Dee Example",
                    "all_candidates": "Cy Example | Dee Example",
                    "candidate_count": "2",
                    "role_set": "endorsed | opponent",
                    "party_set": "Democratic",
                    "evidence_statuses": "verified",
                    "office": "County Council",
                    "office_status": "manual_verified",
                    "jurisdiction": "King County",
                    "jurisdiction_status": "manual_verified",
                    "state": "Washington",
                    "state_code": "WA",
                    "state_status": "manual_verified",
                    "official_election_source": "https://example.org/wa-results",
                    "official_election_source_status": "manual_verified",
                    "certified_opponents": "Dee Example",
                    "certified_opponents_status": "manual_verified",
                    "endorsing_bodies": "DSA National",
                    "metadata_source": "manual_verified",
                    "source_reference": "wa-race",
                    "unresolved_fields": "",
                },
                {
                    "race_id": "race-pa-2023",
                    "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                    "election_date": "2023-05-16",
                    "election_year": "2023",
                    "primary_party": "Democratic",
                    "endorsed_candidate": "Eli Example",
                    "endorsed_candidates": "Eli Example",
                    "unopposed_candidates": "",
                    "opponent_candidates": "Fran Example",
                    "all_candidates": "Eli Example | Fran Example",
                    "candidate_count": "2",
                    "role_set": "endorsed | opponent",
                    "party_set": "Democratic",
                    "evidence_statuses": "verified",
                    "office": "City Council",
                    "office_status": "manual_verified",
                    "jurisdiction": "Philadelphia At Large",
                    "jurisdiction_status": "manual_verified",
                    "state": "Pennsylvania",
                    "state_code": "PA",
                    "state_status": "manual_verified",
                    "official_election_source": "https://example.org/pa-results",
                    "official_election_source_status": "manual_verified",
                    "certified_opponents": "Fran Example",
                    "certified_opponents_status": "manual_verified",
                    "endorsing_bodies": "DSA National",
                    "metadata_source": "manual_verified",
                    "source_reference": "pa-race",
                    "unresolved_fields": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "organizational_context_sources.csv",
            [
                {
                    "context_entry_id": "dnc-2025-seed",
                    "state": "New York",
                    "state_code": "NY",
                    "cycle_year": "2025",
                    "organization_level": "national",
                    "context_category": "dnc_national",
                    "organization": "Democratic National Committee",
                    "endorsing_body": "",
                    "title": "2024 Democratic Party Platform",
                    "platform_type": "national_party_platform",
                    "adoption_date": "2024-08-19",
                    "effective_date": "2024-08-19",
                    "source_url": "https://example.org/dnc-2024.pdf",
                    "archive_url": "",
                    "verification_status": "verified",
                    "notes": "Verified 2024 national platform.",
                },
                {
                    "context_entry_id": "dsa-2022-seed",
                    "state": "California",
                    "state_code": "CA",
                    "cycle_year": "2022",
                    "organization_level": "national",
                    "context_category": "dsa_national",
                    "organization": "Democratic Socialists of America",
                    "endorsing_body": "",
                    "title": "2021 DSA National Platform second draft",
                    "platform_type": "dsa_national_platform_draft",
                    "adoption_date": "2021",
                    "effective_date": "2021",
                    "source_url": "https://example.org/dsa-platform-draft.pdf",
                    "archive_url": "",
                    "verification_status": "verified",
                    "notes": "Official draft platform carried into 2022-2023.",
                },
                {
                    "context_entry_id": "dsa-2026-seed",
                    "state": "Missouri",
                    "state_code": "MO",
                    "cycle_year": "2026",
                    "organization_level": "national",
                    "context_category": "dsa_national",
                    "organization": "Democratic Socialists of America",
                    "endorsing_body": "",
                    "title": "DSA National Program",
                    "platform_type": "dsa_national_program",
                    "adoption_date": "2026-07-01",
                    "effective_date": "2026-07-01",
                    "source_url": "https://example.org/dsa-program",
                    "archive_url": "",
                    "verification_status": "verified",
                    "notes": "Verified 2026 national program.",
                },
            ],
        )

        result = build_organizational_context_inventory(self._paths(root))

        inventory_rows = self._read_csv(result.inventory_path)
        rows_by_key = {
            (row["state_code"], row["cycle_year"], row["context_category"]): row
            for row in inventory_rows
        }
        self.assertEqual(rows_by_key[("CA", "2024", "dnc_national")]["verification_status"], "verified")
        self.assertEqual(rows_by_key[("CA", "2024", "dnc_national")]["synthetic"], "true")
        self.assertIn(
            "Carried forward from verified national entry dnc-2025-seed",
            rows_by_key[("CA", "2024", "dnc_national")]["notes"],
        )
        self.assertEqual(rows_by_key[("WA", "2026", "dsa_national")]["verification_status"], "verified")
        self.assertIn(
            "Carried forward from verified national entry dsa-2026-seed",
            rows_by_key[("WA", "2026", "dsa_national")]["notes"],
        )
        self.assertEqual(rows_by_key[("PA", "2023", "dsa_national")]["verification_status"], "verified")
        self.assertIn(
            "Carried forward from verified national entry dsa-2022-seed",
            rows_by_key[("PA", "2023", "dsa_national")]["notes"],
        )

        coverage_rows = self._read_csv(result.coverage_path)
        by_key = {(row["state_code"], row["cycle_year"]): row for row in coverage_rows}
        self.assertEqual(by_key[("CA", "2024")]["dnc_national_status"], "verified")
        self.assertEqual(by_key[("WA", "2026")]["dsa_national_status"], "verified")
        self.assertEqual(by_key[("PA", "2023")]["dsa_national_status"], "verified")

    def test_local_seed_entries_are_used_even_without_local_endorsing_bodies(self) -> None:
        root = self._scenario_root("local_seed_without_body")
        self._write_csv(
            root / "data" / "processed" / "race_registry.csv",
            [
                {
                    "race_id": "race-dc",
                    "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                    "election_date": "2022-06-21",
                    "election_year": "2022",
                    "primary_party": "Democratic",
                    "endorsed_candidate": "Zachary Parker",
                    "endorsed_candidates": "Zachary Parker",
                    "unopposed_candidates": "",
                    "opponent_candidates": "Vincent Orange",
                    "all_candidates": "Vincent Orange | Zachary Parker",
                    "candidate_count": "2",
                    "role_set": "endorsed | opponent",
                    "party_set": "Democratic",
                    "evidence_statuses": "verified",
                    "office": "City Council",
                    "office_status": "metadata_inferred",
                    "office_source": "title_url:doc-zp",
                    "office_confidence": "high",
                    "jurisdiction": "Ward 5",
                    "jurisdiction_status": "metadata_inferred",
                    "jurisdiction_source": "title_url:doc-zp",
                    "jurisdiction_confidence": "high",
                    "state": "District of Columbia",
                    "state_code": "DC",
                    "state_status": "metadata_inferred",
                    "state_source": "official_host:doc-zp",
                    "state_confidence": "high",
                    "official_election_source": "",
                    "official_election_source_status": "unresolved",
                    "official_election_source_source": "",
                    "official_election_source_confidence": "",
                    "certified_opponents": "Vincent Orange",
                    "certified_opponents_status": "corpus_candidate_set",
                    "endorsing_bodies": "",
                    "metadata_source": "metadata_inferred",
                    "source_reference": "title_url:doc-zp",
                    "unresolved_fields": "official_election_source",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "organizational_context_sources.csv",
            [
                {
                    "context_entry_id": "context-dc-dsa-2022",
                    "state": "District of Columbia",
                    "state_code": "DC",
                    "cycle_year": "2022",
                    "organization_level": "local",
                    "context_category": "dsa_state_local",
                    "organization": "Metro DC Democratic Socialists of America",
                    "endorsing_body": "Metro DC DSA",
                    "title": "Political Endorsement Questionnaire",
                    "platform_type": "chapter_questionnaire_process",
                    "adoption_date": "",
                    "effective_date": "",
                    "source_url": "https://web.archive.org/web/20220521131811/https://washingtondc.dsacommittees.org/political-endorsement-questionnaire/",
                    "archive_url": "https://web.archive.org/web/20220521131811/https://washingtondc.dsacommittees.org/political-endorsement-questionnaire/",
                    "verification_status": "verified",
                    "notes": "Official chapter questionnaire archive; not a full platform.",
                },
            ],
        )

        result = build_organizational_context_inventory(self._paths(root))
        inventory_rows = self._read_csv(result.inventory_path)
        dc_local = next(
            row
            for row in inventory_rows
            if row["state_code"] == "DC" and row["cycle_year"] == "2022" and row["context_category"] == "dsa_state_local"
        )
        self.assertEqual(dc_local["verification_status"], "verified")
        self.assertEqual(dc_local["synthetic"], "false")

        coverage_rows = self._read_csv(result.coverage_path)
        dc_coverage = next(row for row in coverage_rows if row["state_code"] == "DC" and row["cycle_year"] == "2022")
        self.assertEqual(dc_coverage["dsa_state_local_status"], "verified")

    def test_multiple_local_seed_entries_are_retained_without_local_endorsing_bodies(self) -> None:
        root = self._scenario_root("multiple_local_seed_without_body")
        self._write_csv(
            root / "data" / "processed" / "race_registry.csv",
            [
                {
                    "race_id": "race-nv",
                    "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                    "election_date": "2026-06-09",
                    "election_year": "2026",
                    "primary_party": "Democratic",
                    "endorsed_candidate": "Val Example",
                    "endorsed_candidates": "Val Example",
                    "unopposed_candidates": "",
                    "opponent_candidates": "Sam Example",
                    "all_candidates": "Sam Example | Val Example",
                    "candidate_count": "2",
                    "role_set": "endorsed | opponent",
                    "party_set": "Democratic",
                    "evidence_statuses": "verified",
                    "office": "Assembly",
                    "office_status": "manual_verified",
                    "jurisdiction": "District 1",
                    "jurisdiction_status": "manual_verified",
                    "state": "Nevada",
                    "state_code": "NV",
                    "state_status": "manual_verified",
                    "official_election_source": "https://example.org/nv-results",
                    "official_election_source_status": "manual_verified",
                    "certified_opponents": "Sam Example",
                    "certified_opponents_status": "manual_verified",
                    "endorsing_bodies": "Las Vegas",
                    "metadata_source": "manual_verified",
                    "source_reference": "nv-race",
                    "unresolved_fields": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "organizational_context_sources.csv",
            [
                {
                    "context_entry_id": "context-lvdsa-process",
                    "state": "Nevada",
                    "state_code": "NV",
                    "cycle_year": "2026",
                    "organization_level": "local",
                    "context_category": "dsa_state_local",
                    "organization": "Las Vegas Democratic Socialists of America",
                    "endorsing_body": "Las Vegas DSA",
                    "title": "LVDSA Endorsements",
                    "platform_type": "chapter_endorsement_process",
                    "adoption_date": "",
                    "effective_date": "",
                    "source_url": "https://example.org/endorsements",
                    "archive_url": "",
                    "verification_status": "verified",
                    "notes": "Process page.",
                },
                {
                    "context_entry_id": "context-lvdsa-guide",
                    "state": "Nevada",
                    "state_code": "NV",
                    "cycle_year": "2026",
                    "organization_level": "local",
                    "context_category": "dsa_state_local",
                    "organization": "Las Vegas Democratic Socialists of America",
                    "endorsing_body": "Las Vegas DSA",
                    "title": "LVDSA Voter Guide",
                    "platform_type": "chapter_voter_guide",
                    "adoption_date": "",
                    "effective_date": "",
                    "source_url": "https://example.org/voter-guide",
                    "archive_url": "",
                    "verification_status": "verified",
                    "notes": "Guide page.",
                },
            ],
        )

        result = build_organizational_context_inventory(self._paths(root))
        inventory_rows = [
            row
            for row in self._read_csv(result.inventory_path)
            if row["state_code"] == "NV" and row["cycle_year"] == "2026" and row["context_category"] == "dsa_state_local"
        ]
        self.assertEqual(len(inventory_rows), 2)
        self.assertEqual(
            {row["platform_type"] for row in inventory_rows},
            {"chapter_endorsement_process", "chapter_voter_guide"},
        )

    def test_verified_analog_plus_full_platform_gap_aggregates_to_searched_not_found(self) -> None:
        root = self._scenario_root("verified_analog_with_gap")
        self._write_csv(
            root / "data" / "processed" / "race_registry.csv",
            [
                {
                    "race_id": "race-ny",
                    "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                    "election_date": "2025-06-24",
                    "election_year": "2025",
                    "primary_party": "Democratic",
                    "endorsed_candidate": "Example",
                    "endorsed_candidates": "Example",
                    "unopposed_candidates": "",
                    "opponent_candidates": "Opponent",
                    "all_candidates": "Example | Opponent",
                    "candidate_count": "2",
                    "role_set": "endorsed | opponent",
                    "party_set": "Democratic",
                    "evidence_statuses": "verified",
                    "office": "Mayor",
                    "office_status": "manual_verified",
                    "jurisdiction": "New York City",
                    "jurisdiction_status": "manual_verified",
                    "state": "New York",
                    "state_code": "NY",
                    "state_status": "manual_verified",
                    "official_election_source": "https://example.org/results",
                    "official_election_source_status": "manual_verified",
                    "certified_opponents": "Opponent",
                    "certified_opponents_status": "manual_verified",
                    "endorsing_bodies": "",
                    "metadata_source": "manual_verified",
                    "source_reference": "ny-race",
                    "unresolved_fields": "",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "organizational_context_sources.csv",
            [
                {
                    "context_entry_id": "ny-analog",
                    "state": "New York",
                    "state_code": "NY",
                    "cycle_year": "2025",
                    "organization_level": "state",
                    "context_category": "state_democratic_party",
                    "organization": "New York State Democratic Party",
                    "endorsing_body": "",
                    "title": "About and archive pages",
                    "platform_type": "state_party_about_resolutions_archive",
                    "adoption_date": "",
                    "effective_date": "",
                    "source_url": "https://example.org/about",
                    "archive_url": "",
                    "verification_status": "verified",
                    "notes": "Not a full platform.",
                },
                {
                    "context_entry_id": "ny-gap",
                    "state": "New York",
                    "state_code": "NY",
                    "cycle_year": "2025",
                    "organization_level": "state",
                    "context_category": "state_democratic_party",
                    "organization": "New York State Democratic Party",
                    "endorsing_body": "",
                    "title": "Full platform search seed",
                    "platform_type": "state_party_platform_search_seed",
                    "adoption_date": "",
                    "effective_date": "",
                    "source_url": "https://example.org",
                    "archive_url": "",
                    "verification_status": "searched_not_found",
                    "notes": "No full platform recovered.",
                },
            ],
        )

        result = build_organizational_context_inventory(self._paths(root))
        inventory_rows = self._read_csv(result.inventory_path)
        matching_rows = [
            row
            for row in inventory_rows
            if row["state_code"] == "NY" and row["cycle_year"] == "2025" and row["context_category"] == "state_democratic_party"
        ]
        self.assertEqual(len(matching_rows), 2)
        self.assertEqual(
            {row["verification_status"] for row in matching_rows},
            {"verified", "searched_not_found"},
        )
        coverage_row = self._read_csv(result.coverage_path)[0]
        self.assertEqual(coverage_row["state_democratic_party_status"], "searched_not_found")

    def test_found_unverified_platform_is_fetched_but_kept_as_gap(self) -> None:
        root = self._scenario_root("found_unverified_fetch")
        self._write_csv(
            root / "data" / "processed" / "race_registry.csv",
            [
                {
                    "race_id": "race-nv",
                    "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                    "election_date": "2024-06-11",
                    "election_year": "2024",
                    "primary_party": "Democratic",
                    "endorsed_candidate": "Valerie Thomason",
                    "endorsed_candidates": "Valerie Thomason",
                    "unopposed_candidates": "",
                    "opponent_candidates": "Venise L. Karris",
                    "all_candidates": "Valerie Thomason | Venise L. Karris",
                    "candidate_count": "2",
                    "role_set": "endorsed | opponent",
                    "party_set": "Democratic",
                    "evidence_statuses": "verified",
                    "office": "State Assembly",
                    "office_status": "manual_verified",
                    "jurisdiction": "District 10",
                    "jurisdiction_status": "manual_verified",
                    "state": "Nevada",
                    "state_code": "NV",
                    "state_status": "manual_verified",
                    "official_election_source": "https://example.org/nv-results",
                    "official_election_source_status": "manual_verified",
                    "certified_opponents": "Venise L. Karris",
                    "certified_opponents_status": "manual_verified",
                    "endorsing_bodies": "",
                    "metadata_source": "manual_verified",
                    "source_reference": "nv-race",
                    "unresolved_fields": "",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "organizational_context_sources.csv",
            [
                {
                    "context_entry_id": "context-state-party-nv-2024-draft",
                    "state": "Nevada",
                    "state_code": "NV",
                    "cycle_year": "2024",
                    "organization_level": "state",
                    "context_category": "state_democratic_party",
                    "organization": "Nevada State Democratic Party",
                    "endorsing_body": "",
                    "title": "2024 Nevada Democratic Party State Convention Platform (draft)",
                    "platform_type": "state_party_platform_draft",
                    "adoption_date": "2024-06",
                    "effective_date": "2024-06",
                    "source_url": "https://nvdems.com/wp-content/uploads/2024/06/FINAL-NV-Dems-State-Convention-Platform-2024.pdf",
                    "archive_url": "",
                    "verification_status": "found_unverified",
                    "notes": "Official draft platform PDF located, but not treated as a verified final full platform.",
                }
            ],
        )

        result = build_organizational_context_inventory(self._paths(root))
        coverage_row = self._read_csv(result.coverage_path)[0]
        self.assertEqual(coverage_row["state_democratic_party_status"], "found_unverified")

        fetch_rows = self._read_csv(result.fetch_queue_path)
        self.assertEqual(len(fetch_rows), 1)
        self.assertEqual(
            fetch_rows[0]["fetch_url"],
            "https://nvdems.com/wp-content/uploads/2024/06/FINAL-NV-Dems-State-Convention-Platform-2024.pdf",
        )

    def test_fetch_pass_writes_status_and_manifest(self) -> None:
        root = self._scenario_root("fetch")
        self._write_csv(
            root / "data" / "processed" / "race_registry.csv",
            [
                {
                    "race_id": "race-ny",
                    "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                    "election_date": "2025-06-24",
                    "election_year": "2025",
                    "primary_party": "Democratic",
                    "endorsed_candidate": "Zohran Mamdani",
                    "endorsed_candidates": "Zohran Mamdani",
                    "unopposed_candidates": "",
                    "opponent_candidates": "Andrew Cuomo",
                    "all_candidates": "Zohran Mamdani | Andrew Cuomo",
                    "candidate_count": "2",
                    "role_set": "endorsed | opponent",
                    "party_set": "Democratic",
                    "evidence_statuses": "verified",
                    "office": "Mayor",
                    "office_status": "manual_verified",
                    "jurisdiction": "New York City",
                    "jurisdiction_status": "manual_verified",
                    "state": "New York",
                    "state_code": "NY",
                    "state_status": "manual_verified",
                    "official_election_source": "https://example.org/ny-results",
                    "official_election_source_status": "manual_verified",
                    "certified_opponents": "Andrew Cuomo",
                    "certified_opponents_status": "manual_verified",
                    "endorsing_bodies": "NYC-DSA",
                    "metadata_source": "manual_verified",
                    "source_reference": "ny-race",
                    "unresolved_fields": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "organizational_context_sources.csv",
            [
                {
                    "context_entry_id": "ny-state-2025",
                    "state": "New York",
                    "state_code": "NY",
                    "cycle_year": "2025",
                    "organization_level": "state",
                    "context_category": "state_democratic_party",
                    "organization": "New York State Democratic Party",
                    "endorsing_body": "",
                    "title": "Our Party",
                    "platform_type": "state_party_priorities_page",
                    "adoption_date": "",
                    "effective_date": "",
                    "source_url": "https://example.org/ny-party",
                    "archive_url": "",
                    "verification_status": "verified",
                    "notes": "Verified",
                },
            ],
        )
        result = build_organizational_context_inventory(self._paths(root))
        fetch_result = run_organizational_context_fetch_pass(
            self._read_csv(result.fetch_queue_path),
            self._paths(root),
            fetcher=lambda url: FetchCapture(
                fetch_url=url,
                final_url=url,
                retrieved_at="2026-08-20T00:00:00+00:00",
                content_type="text/html",
                content_bytes=b"<html>ok</html>",
                status_code=200,
            ),
            limit=1,
        )
        self.assertEqual(fetch_result.queued_urls, 1)
        status_rows = self._read_csv(fetch_result.status_path)
        self.assertEqual(status_rows[0]["status"], "fetched")

    def test_fetch_pass_preserves_records_from_prior_targeted_runs(self) -> None:
        root = self._scenario_root("fetch_resume")
        paths = self._paths(root)
        first_queue = [
            {
                "fetch_id": "fetch-a",
                "fetch_url": "https://example.org/a",
                "archive_url": "",
                "context_entry_ids": "context-a",
            }
        ]
        second_queue = [
            {
                "fetch_id": "fetch-b",
                "fetch_url": "https://example.org/b",
                "archive_url": "",
                "context_entry_ids": "context-b",
            }
        ]

        def fetcher(url: str) -> FetchCapture:
            return FetchCapture(
                fetch_url=url,
                final_url=url,
                retrieved_at="2026-08-20T00:00:00+00:00",
                content_type="text/html",
                content_bytes=url.encode(),
                status_code=200,
            )

        run_organizational_context_fetch_pass(first_queue, paths, fetcher=fetcher)
        fetch_result = run_organizational_context_fetch_pass(second_queue, paths, fetcher=fetcher)

        status_rows = self._read_csv(fetch_result.status_path)
        self.assertEqual([row["fetch_id"] for row in status_rows], ["fetch-a", "fetch-b"])
        manifest_rows = [
            json.loads(line)
            for line in fetch_result.raw_manifest_path.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual([row["fetch_id"] for row in manifest_rows], ["fetch-a", "fetch-b"])

    def test_fetch_pass_uses_archive_after_live_failure(self) -> None:
        root = self._scenario_root("fetch_archive_fallback")
        paths = self._paths(root)
        queue = [
            {
                "fetch_id": "fetch-a",
                "fetch_url": "https://example.org/live",
                "archive_url": "https://web.archive.org/example",
                "context_entry_ids": "context-a",
            }
        ]
        attempted_urls: list[str] = []

        def fetcher(url: str) -> FetchCapture:
            attempted_urls.append(url)
            if url.endswith("/live"):
                raise OrganizationalContextFetchError("live source unavailable")
            return FetchCapture(
                fetch_url=url,
                final_url=url,
                retrieved_at="2026-08-20T00:00:00+00:00",
                content_type="text/html",
                content_bytes=b"<html>archived platform</html>",
                status_code=200,
            )

        result = run_organizational_context_fetch_pass(queue, paths, fetcher=fetcher)

        self.assertEqual(
            attempted_urls,
            ["https://example.org/live", "https://web.archive.org/example"],
        )
        self.assertEqual(result.fetched_urls, 1)
        self.assertEqual(result.failed_urls, 0)
        status = self._read_csv(result.status_path)[0]
        self.assertEqual(status["status"], "fetched")
        self.assertEqual(status["final_url"], "https://web.archive.org/example")

    def test_fetch_pass_uses_archive_after_live_access_challenge(self) -> None:
        root = self._scenario_root("fetch_access_challenge")
        paths = self._paths(root)
        queue = [
            {
                "fetch_id": "fetch-a",
                "fetch_url": "https://example.org/live.pdf",
                "archive_url": "https://web.archive.org/example.pdf",
                "context_entry_ids": "context-a",
            }
        ]
        attempted_urls: list[str] = []

        def fetcher(url: str) -> FetchCapture:
            attempted_urls.append(url)
            if url == "https://example.org/live.pdf":
                return FetchCapture(
                    fetch_url=url,
                    final_url=url,
                    retrieved_at="2026-08-20T00:00:00+00:00",
                    content_type="text/html",
                    content_bytes=b'<meta http-equiv="refresh" content="0;/.well-known/sgcaptcha/">',
                    status_code=202,
                )
            return FetchCapture(
                fetch_url=url,
                final_url=url,
                retrieved_at="2026-08-20T00:00:00+00:00",
                content_type="application/pdf",
                content_bytes=b"%PDF-1.7 archived platform",
                status_code=200,
            )

        result = run_organizational_context_fetch_pass(queue, paths, fetcher=fetcher)

        self.assertEqual(
            attempted_urls,
            ["https://example.org/live.pdf", "https://web.archive.org/example.pdf"],
        )
        self.assertEqual(result.fetched_urls, 1)
        self.assertEqual(result.failed_urls, 0)
        status = self._read_csv(result.status_path)[0]
        self.assertEqual(status["content_type"], "application/pdf")

    def _scenario_root(self, name: str) -> Path:
        root = SCRATCH_ROOT / name
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _paths(self, root: Path) -> OrganizationalContextPaths:
        return OrganizationalContextPaths(
            registry_seed_path=root / "data" / "manual" / "organizational_context_sources.csv",
            race_registry_path=root / "data" / "processed" / "race_registry.csv",
            output_dir=root / "data" / "processed",
            raw_dir=root / "data" / "raw" / "organizational_context",
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
