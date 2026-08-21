import csv
import json
import shutil
import unittest
from dataclasses import replace
from pathlib import Path

from dsa_analysis.document_corpus import candidate_document_id
from dsa_analysis.full_text_audit import (
    FullTextAuditPaths,
    _load_corpus_rows,
    _load_registry_queue,
    build_full_text_sufficiency_audit,
)

SCRATCH_ROOT = Path(__file__).resolve().parent / "_scratch_full_text_audit"


class FullTextAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree(SCRATCH_ROOT, ignore_errors=True)
        SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(SCRATCH_ROOT, ignore_errors=True))

    def test_registry_queue_reuses_unique_candidate_documents_across_canonical_race_ids(self) -> None:
        root = self._scenario_root("registry_alias")
        paths = replace(
            self._paths(root),
            race_registry_path=root / "data" / "processed" / "race_registry.csv",
            candidate_search_resolutions_path=root
            / "data"
            / "manual"
            / "candidate_document_search_resolutions.csv",
        )
        self._write_csv(
            paths.race_registry_path,
            [
                {
                    "race_id": "canonical-race",
                    "source_race_ids": "canonical-race",
                    "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                    "election_date": "2016-09-08",
                    "endorsed_candidates": "Casey Example",
                    "unopposed_candidates": "",
                    "opponent_candidates": "Robin Example | Taylor Example",
                    "office": "State Representative",
                    "official_election_source": "https://example.org/results",
                }
            ],
        )
        self._write_csv(
            paths.candidate_document_metadata_path,
            [
                {
                    "document_id": "doc-casey-unavailable",
                    "candidate_name": "Casey Example",
                    "race_id": "canonical-race",
                    "role": "endorsed",
                    "election_date": "2016-09-08",
                    "source_type": "campaign_page",
                    "source_url": "https://example.org/missing-casey",
                    "coverage_status": "source_unavailable",
                    "fetch_status": "fetch_error",
                    "extraction_status": "source_unavailable",
                    "analysis_scope": "analysis",
                },
                {
                    "document_id": "doc-casey",
                    "candidate_name": "Casey Example",
                    "race_id": "legacy-race",
                    "role": "endorsed",
                    "election_date": "2016-09-08",
                    "source_type": "campaign_page",
                    "source_url": "https://example.org/casey",
                    "coverage_status": "found_unverified",
                    "fetch_status": "reused_raw",
                    "extraction_status": "extracted",
                    "analysis_scope": "analysis",
                },
                {
                    "document_id": "doc-robin",
                    "candidate_name": "Robin Example",
                    "race_id": "canonical-race",
                    "role": "opponent",
                    "election_date": "2016-09-08",
                    "source_type": "campaign_page",
                    "source_url": "https://example.org/robin",
                    "coverage_status": "found_unverified",
                    "fetch_status": "fetch_error",
                    "extraction_status": "not_attempted",
                    "analysis_scope": "analysis",
                },
            ],
        )
        self._write_csv(
            paths.candidate_search_resolutions_path,
            [
                {
                    "race_id": "canonical-race",
                    "candidate_name": "Taylor Example",
                    "role": "opponent",
                    "research_status": "searched_not_found",
                }
            ],
        )

        queue = _load_registry_queue(paths, [2016])
        by_candidate = {row["candidate_name"]: row for row in queue}

        self.assertEqual(by_candidate["Casey Example"]["current_status"], "verified")
        self.assertEqual(by_candidate["Robin Example"]["current_status"], "found_unverified")
        self.assertEqual(by_candidate["Taylor Example"]["current_status"], "searched_not_found")

    def test_registry_seed_without_legacy_quote_columns_is_supported(self) -> None:
        root = self._scenario_root("registry_seed")
        self._write_json(
            root / "config" / "sources.json",
            {
                "study_start": "2016-01-01",
                "research_cutoff": "2016-12-31",
            },
        )
        paths = self._paths(root)
        self._write_csv(
            paths.candidate_corpus_path,
            [
                {
                    "race_id": "race-1",
                    "candidate_name": "Casey Example",
                    "election_date": "2016-05-10",
                    "role": "endorsed",
                    "evidence_status": "verified",
                }
            ],
        )

        rows = _load_corpus_rows(paths.candidate_corpus_path, [2016])

        self.assertEqual(len(rows), 1)

    def test_legacy_quotes_seed_actionable_queues_but_do_not_count_as_full_documents(self) -> None:
        root = self._scenario_root("manual")
        self._write_json(
            root / "config" / "sources.json",
            {
                "study_start": "2016-01-01",
                "research_cutoff": "2018-12-31",
            },
        )
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "c16-e",
                    "race_id": "corpus-2016",
                    "candidate_name": "Casey Example",
                    "election_date": "2016-05-10",
                    "role": "endorsed",
                    "evidence_status": "source_unavailable",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "notes": "No retrievable statement",
                },
                {
                    "statement_key": "c16-o",
                    "race_id": "corpus-2016",
                    "candidate_name": "Taylor Example",
                    "election_date": "2016-05-10",
                    "role": "opponent",
                    "evidence_status": "source_unavailable",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "notes": "No retrievable statement",
                },
                {
                    "statement_key": "c17-e",
                    "race_id": "manual-race-2017",
                    "candidate_name": "Alex One",
                    "election_date": "2017-06-01",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "quote": "We need public housing and stronger labor rights.",
                    "source_url": "https://example.com/alex-platform",
                    "source_type": "official_campaign_page",
                    "published_date": "2017-05-01",
                    "locator": "Issues",
                    "notes": "Legacy quote row",
                },
                {
                    "statement_key": "c18-e",
                    "race_id": "manual-race-2018",
                    "candidate_name": "Jordan Two",
                    "election_date": "2018-08-01",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "quote": "A living wage is overdue.",
                    "source_url": "https://example.com/jordan-platform",
                    "source_type": "candidate_questionnaire",
                    "published_date": "2018-07-15",
                    "locator": "Q1",
                    "notes": "Legacy quote row",
                },
                {
                    "statement_key": "c18-o",
                    "race_id": "manual-race-2018",
                    "candidate_name": "Robin Two",
                    "election_date": "2018-08-01",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "quote": "I support public schools and transit funding.",
                    "source_url": "https://example.com/robin-qa",
                    "source_type": "candidate_questionnaire",
                    "published_date": "2018-07-16",
                    "locator": "Q2",
                    "notes": "Legacy quote row",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "documents.csv",
            [
                {
                    "document_id": "doc-2017",
                    "url": "https://example.com/endorsement-2017",
                },
                {
                    "document_id": "doc-2018",
                    "url": "https://example.com/endorsement-2018",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "endorsements.csv",
            [
                {
                    "race_id": "manual-race-2017",
                    "election_date": "2017-06-01",
                    "endorsement_source_document_id": "doc-2017",
                },
                {
                    "race_id": "manual-race-2018",
                    "election_date": "2018-08-01",
                    "endorsement_source_document_id": "doc-2018",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_candidates.csv",
            [
                {
                    "race_id": "manual-race-2017",
                    "candidate_name": "Alex One",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "source_url": "https://example.com/alex-platform",
                    "notes": "Verified platform",
                },
                {
                    "race_id": "manual-race-2017",
                    "candidate_name": "Taylor One",
                    "role": "opponent",
                    "evidence_status": "found_unverified",
                    "source_url": "https://example.com/taylor-search",
                    "notes": "Questionnaire needs regather",
                },
                {
                    "race_id": "manual-race-2018",
                    "candidate_name": "Jordan Two",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "source_url": "https://example.com/jordan-platform",
                    "notes": "Verified questionnaire",
                },
                {
                    "race_id": "manual-race-2018",
                    "candidate_name": "Robin Two",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "source_url": "https://example.com/robin-qa",
                    "notes": "Verified questionnaire",
                },
            ],
        )

        result = build_full_text_sufficiency_audit(self._paths(root))

        self.assertEqual(result.queue_source, "manual")
        self.assertEqual(result.eligible_races, 0)
        self.assertEqual(result.retryable_gaps, 2)
        self.assertFalse(result.sufficient)
        self.assertIn("paired_race_two_sided_substantive_text", result.failed_gates)

        summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["sufficiency"]["decision"], "insufficient")
        self.assertEqual(summary["queue"]["missing_years"], ["2016"])
        self.assertEqual(summary["paired_races"]["eligible_count"], 0)
        self.assertEqual(summary["document_corpus"]["status"], "absent")
        self.assertIn(
            "legacy quotation rows are discovery evidence only",
            summary["document_corpus"]["status_note"],
        )
        self.assertEqual(summary["discovery"]["source_inventory_rows"], 3)
        self.assertEqual(summary["discovery"]["queued_candidates_without_any_document_seed"], 0)

        document_queue = self._read_csv(result.document_queue_path)
        taylor_rows = [row for row in document_queue if row["candidate_name"] == "Taylor One"]
        self.assertEqual(len(taylor_rows), 2)
        self.assertEqual(taylor_rows[0]["collection_status"], "not_collected")
        self.assertIn("queue_reference", taylor_rows[0]["seed_kinds"])

        support_rows = self._read_csv(result.group_year_support_path)
        support_by_key = {
            (row["group"], row["election_year"]): row for row in support_rows
        }
        self.assertEqual(
            support_by_key[("opponent", "2018")]["substantive_candidate_count"],
            "0",
        )
        self.assertEqual(
            support_by_key[("opponent", "2018")]["missing_support"],
            "true",
        )

        imbalance_rows = self._read_csv(result.imbalance_diagnostics_path)
        self.assertEqual(imbalance_rows[0]["dimension"], "overall")
        self.assertEqual(imbalance_rows[0]["flag_reason"], "no_substantive_document_support")

    def test_processed_queue_and_full_document_corpus_can_pass_all_hard_gates(self) -> None:
        root = self._scenario_root("processed")
        doc_a = self._doc_id("Alex Processed", "race-2016", "https://alex.example/issues", "campaign_page")
        doc_b = self._doc_id(
            "Blair Processed",
            "race-2016",
            "https://blair.example/questionnaire",
            "questionnaire",
        )
        doc_c = self._doc_id("Casey Processed", "race-2017", "https://casey.example/issues", "campaign_page")
        doc_d = self._doc_id(
            "Drew Processed",
            "race-2017",
            "https://drew.example/questionnaire",
            "questionnaire",
        )
        self._write_json(
            root / "config" / "sources.json",
            {
                "study_start": "2016-01-01",
                "research_cutoff": "2017-12-31",
            },
        )
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "r1e",
                    "race_id": "race-2016",
                    "candidate_name": "Alex Processed",
                    "election_date": "2016-09-01",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "quote": "Public transit needs durable funding and public housing now.",
                    "source_url": "https://alex.example/issues",
                    "source_type": "official_campaign_page",
                    "published_date": "2016-08-15",
                    "locator": "Platform",
                    "notes": "Legacy quote row",
                },
                {
                    "statement_key": "r1o",
                    "race_id": "race-2016",
                    "candidate_name": "Blair Processed",
                    "election_date": "2016-09-01",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "quote": "Fully fund schools and adopt housing-first policy statewide.",
                    "source_url": "https://blair.example/questionnaire",
                    "source_type": "candidate_questionnaire",
                    "published_date": "2016-08-16",
                    "locator": "Questionnaire",
                    "notes": "Legacy quote row",
                },
                {
                    "statement_key": "r2e",
                    "race_id": "race-2017",
                    "candidate_name": "Casey Processed",
                    "election_date": "2017-10-10",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "quote": "Municipal broadband, free buses, and social housing belong in every ward.",
                    "source_url": "https://casey.example/issues",
                    "source_type": "official_campaign_page",
                    "published_date": "2017-09-20",
                    "locator": "Platform",
                    "notes": "Legacy quote row",
                },
                {
                    "statement_key": "r2o",
                    "race_id": "race-2017",
                    "candidate_name": "Drew Processed",
                    "election_date": "2017-10-10",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "quote": "Raise wages, expand transit, and protect union schools.",
                    "source_url": "https://drew.example/questionnaire",
                    "source_type": "candidate_questionnaire",
                    "published_date": "2017-09-21",
                    "locator": "Questionnaire",
                    "notes": "Legacy quote row",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "documents.csv",
            [{"document_id": "doc", "url": "https://example.com/doc"}],
        )
        self._write_csv(
            root / "data" / "manual" / "endorsements.csv",
            [
                {
                    "race_id": "manual-race",
                    "election_date": "2017-10-10",
                    "endorsement_source_document_id": "doc",
                }
            ],
        )
        (root / "data" / "manual" / "documents.csv").parent.mkdir(parents=True, exist_ok=True)
        (root / "data" / "manual" / "documents.csv").write_text("document_id,url\n", encoding="utf-8")
        (root / "data" / "manual" / "endorsements.csv").write_text(
            "race_id,election_date,endorsement_source_document_id\nrace-2020,2020-03-03,\n",
            encoding="utf-8",
        )
        self._write_csv(
            root / "data" / "manual" / "race_candidates.csv",
            [
                {
                    "race_id": "manual-race",
                    "candidate_name": "Manual Only",
                    "role": "endorsed",
                    "evidence_status": "not_searched",
                    "source_url": "https://example.com/manual-only",
                    "notes": "Manual fallback should not be used",
                },
                {
                    "race_id": "manual-race",
                    "candidate_name": "Manual Opponent",
                    "role": "opponent",
                    "evidence_status": "not_searched",
                    "source_url": "https://example.com/manual-opponent",
                    "notes": "Manual fallback should not be used",
                },
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "opponent_research_queue.csv",
            [
                {
                    "queue_id": "q1",
                    "candidate_statement_status": "verified",
                    "opponent_statement_status": "verified",
                    "endorsement_source_url": "https://example.com/endorsement-q1",
                    "notes": "Processed queue 2016",
                },
                {
                    "queue_id": "q2",
                    "candidate_statement_status": "verified",
                    "opponent_statement_status": "verified",
                    "endorsement_source_url": "https://example.com/endorsement-q2",
                    "notes": "Processed queue 2017",
                },
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "race_rosters_discovered.csv",
            [
                {
                    "queue_id": "q1",
                    "resolution_status": "verified",
                    "race_id": "race-2016",
                    "election_date": "2016-09-01",
                    "candidate_name": "Alex Processed",
                    "role": "endorsed",
                    "official_election_source": "https://county.example/2016-ballot",
                    "notes": "Processed roster 2016",
                },
                {
                    "queue_id": "q1",
                    "resolution_status": "verified",
                    "race_id": "race-2016",
                    "election_date": "2016-09-01",
                    "candidate_name": "Blair Processed",
                    "role": "opponent",
                    "official_election_source": "https://county.example/2016-ballot",
                    "notes": "Processed roster 2016",
                },
                {
                    "queue_id": "q2",
                    "resolution_status": "verified",
                    "race_id": "race-2017",
                    "election_date": "2017-10-10",
                    "candidate_name": "Casey Processed",
                    "role": "endorsed",
                    "official_election_source": "https://county.example/2017-ballot",
                    "notes": "Processed roster 2017",
                },
                {
                    "queue_id": "q2",
                    "resolution_status": "verified",
                    "race_id": "race-2017",
                    "election_date": "2017-10-10",
                    "candidate_name": "Drew Processed",
                    "role": "opponent",
                    "official_election_source": "https://county.example/2017-ballot",
                    "notes": "Processed roster 2017",
                },
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "candidate_statement_evidence.csv",
            [
                {"queue_id": "q1", "candidate_name": "Alex Processed", "role": "endorsed", "evidence_status": "verified"},
                {"queue_id": "q1", "candidate_name": "Blair Processed", "role": "opponent", "evidence_status": "verified"},
                {"queue_id": "q2", "candidate_name": "Casey Processed", "role": "endorsed", "evidence_status": "verified"},
                {"queue_id": "q2", "candidate_name": "Drew Processed", "role": "opponent", "evidence_status": "verified"},
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "candidate_document_metadata.csv",
            [
                {
                    "document_id": doc_a,
                    "queue_id": "q1",
                    "candidate_slug": "alex-processed",
                    "candidate_name": "Alex Processed",
                    "race_id": "race-2016",
                    "role": "endorsed",
                    "election_date": "2016-09-01",
                    "publication_date": "2016-08-15",
                    "campaign_window_start": "2015-01-01",
                    "campaign_window_end": "2016-09-01",
                    "campaign_window_status": "in_window",
                    "source_type": "campaign_page",
                    "source_url": "https://alex.example/issues",
                    "archive_url": "",
                    "final_url": "https://alex.example/issues",
                    "retrieved_at": "2026-08-19T17:00:00+00:00",
                    "content_type": "text/html",
                    "title": "Alex Issues",
                    "coverage_status": "found_unverified",
                    "fetch_status": "reused_raw",
                    "extraction_status": "extracted",
                    "extractor": "html",
                    "raw_sha256": "a",
                    "text_sha256": "a",
                    "provenance_hash": "a",
                    "paragraph_count": "1",
                    "sentence_count": "1",
                    "raw_path": "",
                    "seed_kind": "known_document",
                    "source_record_id": "inv-a",
                    "notes": "",
                    "error": "",
                },
                {
                    "document_id": doc_b,
                    "queue_id": "q1",
                    "candidate_slug": "blair-processed",
                    "candidate_name": "Blair Processed",
                    "race_id": "race-2016",
                    "role": "opponent",
                    "election_date": "2016-09-01",
                    "publication_date": "2016-08-16",
                    "campaign_window_start": "2015-01-01",
                    "campaign_window_end": "2016-09-01",
                    "campaign_window_status": "in_window",
                    "source_type": "questionnaire",
                    "source_url": "https://blair.example/questionnaire",
                    "archive_url": "",
                    "final_url": "https://blair.example/questionnaire",
                    "retrieved_at": "2026-08-19T17:00:00+00:00",
                    "content_type": "text/html",
                    "title": "Blair Questionnaire",
                    "coverage_status": "found_unverified",
                    "fetch_status": "reused_raw",
                    "extraction_status": "extracted",
                    "extractor": "html",
                    "raw_sha256": "b",
                    "text_sha256": "b",
                    "provenance_hash": "b",
                    "paragraph_count": "1",
                    "sentence_count": "1",
                    "raw_path": "",
                    "seed_kind": "known_document",
                    "source_record_id": "inv-b",
                    "notes": "",
                    "error": "",
                },
                {
                    "document_id": doc_c,
                    "queue_id": "q2",
                    "candidate_slug": "casey-processed",
                    "candidate_name": "Casey Processed",
                    "race_id": "race-2017",
                    "role": "endorsed",
                    "election_date": "2017-10-10",
                    "publication_date": "2017-09-20",
                    "campaign_window_start": "2016-01-01",
                    "campaign_window_end": "2017-10-10",
                    "campaign_window_status": "in_window",
                    "source_type": "campaign_page",
                    "source_url": "https://casey.example/issues",
                    "archive_url": "",
                    "final_url": "https://casey.example/issues",
                    "retrieved_at": "2026-08-19T17:00:00+00:00",
                    "content_type": "text/html",
                    "title": "Casey Issues",
                    "coverage_status": "found_unverified",
                    "fetch_status": "reused_raw",
                    "extraction_status": "extracted",
                    "extractor": "html",
                    "raw_sha256": "c",
                    "text_sha256": "c",
                    "provenance_hash": "c",
                    "paragraph_count": "1",
                    "sentence_count": "1",
                    "raw_path": "",
                    "seed_kind": "known_document",
                    "source_record_id": "inv-c",
                    "notes": "",
                    "error": "",
                },
                {
                    "document_id": doc_d,
                    "queue_id": "q2",
                    "candidate_slug": "drew-processed",
                    "candidate_name": "Drew Processed",
                    "race_id": "race-2017",
                    "role": "opponent",
                    "election_date": "2017-10-10",
                    "publication_date": "2017-09-21",
                    "campaign_window_start": "2016-01-01",
                    "campaign_window_end": "2017-10-10",
                    "campaign_window_status": "in_window",
                    "source_type": "questionnaire",
                    "source_url": "https://drew.example/questionnaire",
                    "archive_url": "",
                    "final_url": "https://drew.example/questionnaire",
                    "retrieved_at": "2026-08-19T17:00:00+00:00",
                    "content_type": "text/html",
                    "title": "Drew Questionnaire",
                    "coverage_status": "found_unverified",
                    "fetch_status": "reused_raw",
                    "extraction_status": "extracted",
                    "extractor": "html",
                    "raw_sha256": "d",
                    "text_sha256": "d",
                    "provenance_hash": "d",
                    "paragraph_count": "1",
                    "sentence_count": "1",
                    "raw_path": "",
                    "seed_kind": "known_document",
                    "source_record_id": "inv-d",
                    "notes": "",
                    "error": "",
                },
            ],
        )
        self._write_jsonl(
            root / "data" / "processed" / "candidate_document_full_text.jsonl",
            [
                {"document_id": doc_a, "text": "Public transit needs durable funding and public housing now."},
                {"document_id": doc_b, "text": "Fully fund schools and adopt housing-first policy statewide."},
                {"document_id": doc_c, "text": "Municipal broadband, free buses, and social housing belong in every ward."},
                {"document_id": doc_d, "text": "Raise wages, expand transit, and protect union schools."},
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "candidate_document_analysis_segments.csv",
            [
                self._segment_row("seg-a", doc_a, "Alex Processed", "alex-processed", "race-2016", "endorsed", "campaign_page", 24, "Public transit needs durable funding and public housing now."),
                self._segment_row("seg-b", doc_b, "Blair Processed", "blair-processed", "race-2016", "opponent", "questionnaire", 23, "Fully fund schools and adopt housing-first policy statewide."),
                self._segment_row("seg-c", doc_c, "Casey Processed", "casey-processed", "race-2017", "endorsed", "campaign_page", 25, "Municipal broadband, free buses, and social housing belong in every ward."),
                self._segment_row("seg-d", doc_d, "Drew Processed", "drew-processed", "race-2017", "opponent", "questionnaire", 21, "Raise wages, expand transit, and protect union schools."),
            ],
        )

        result = build_full_text_sufficiency_audit(self._paths(root))

        self.assertEqual(result.queue_source, "processed")
        self.assertTrue(result.sufficient)
        self.assertEqual(result.failed_gates, ())
        self.assertEqual(result.eligible_races, 2)

        summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["sufficiency"]["decision"], "sufficient")
        self.assertEqual(summary["document_corpus"]["status"], "present")
        self.assertEqual(summary["document_corpus"]["substantive_candidate_count"], 4)
        self.assertEqual(summary["paired_races"]["years_with_eligible_races"], ["2016", "2017"])
        self.assertEqual(summary["support"]["missing_group_year_support"], [])
        self.assertEqual(summary["support"]["missing_source_classes"], [])

        document_queue = self._read_csv(result.document_queue_path)
        collected_rows = [row for row in document_queue if row["collection_status"] == "found_unverified"]
        self.assertEqual(len(collected_rows), 4)
        self.assertEqual(collected_rows[0]["substantive_segment_count"], "1")

    def test_metadata_and_segments_are_consumed_without_full_text_jsonl(self) -> None:
        root = self._scenario_root("partial")
        doc_casey = self._doc_id(
            "Casey Example",
            "race-2016",
            "https://example.com/casey-platform",
            "campaign_page",
        )
        doc_taylor = self._doc_id(
            "Taylor Example",
            "race-2016",
            "https://example.com/taylor-qa",
            "questionnaire",
        )
        self._write_json(
            root / "config" / "sources.json",
            {
                "study_start": "2016-01-01",
                "research_cutoff": "2016-12-31",
            },
        )
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "p1",
                    "race_id": "race-2016",
                    "candidate_name": "Casey Example",
                    "election_date": "2016-05-10",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "quote": "Build social housing at scale and fund schools.",
                    "source_url": "https://example.com/casey-platform",
                    "source_type": "official_campaign_page",
                    "published_date": "2016-04-01",
                    "locator": "Platform",
                    "notes": "Legacy row",
                },
                {
                    "statement_key": "p2",
                    "race_id": "race-2016",
                    "candidate_name": "Taylor Example",
                    "election_date": "2016-05-10",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "quote": "Expand public transit and protect tenants everywhere.",
                    "source_url": "https://example.com/taylor-qa",
                    "source_type": "candidate_questionnaire",
                    "published_date": "2016-04-02",
                    "locator": "Questionnaire",
                    "notes": "Legacy row",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "documents.csv",
            [{"document_id": "doc-2016", "url": "https://example.com/endorsement-2016"}],
        )
        self._write_csv(
            root / "data" / "manual" / "endorsements.csv",
            [
                {
                    "race_id": "race-2016",
                    "election_date": "2016-05-10",
                    "endorsement_source_document_id": "doc-2016",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_candidates.csv",
            [
                {
                    "race_id": "race-2016",
                    "candidate_name": "Casey Example",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "source_url": "https://example.com/casey-platform",
                    "notes": "",
                },
                {
                    "race_id": "race-2016",
                    "candidate_name": "Taylor Example",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "source_url": "https://example.com/taylor-qa",
                    "notes": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "candidate_document_metadata.csv",
            [
                {
                    "document_id": doc_casey,
                    "queue_id": "",
                    "candidate_slug": "casey-example",
                    "candidate_name": "Casey Example",
                    "race_id": "race-2016",
                    "role": "endorsed",
                    "election_date": "2016-05-10",
                    "publication_date": "2016-04-01",
                    "campaign_window_start": "2015-01-01",
                    "campaign_window_end": "2016-05-10",
                    "campaign_window_status": "in_window",
                    "source_type": "campaign_page",
                    "source_url": "https://example.com/casey-platform",
                    "archive_url": "",
                    "final_url": "https://example.com/casey-platform",
                    "retrieved_at": "2026-08-19T17:00:00+00:00",
                    "content_type": "text/html",
                    "title": "Casey Platform",
                    "coverage_status": "found_unverified",
                    "fetch_status": "reused_raw",
                    "extraction_status": "extracted",
                    "extractor": "html",
                    "raw_sha256": "1",
                    "text_sha256": "1",
                    "provenance_hash": "1",
                    "paragraph_count": "1",
                    "sentence_count": "1",
                    "raw_path": "",
                    "seed_kind": "known_document",
                    "source_record_id": "inv-1",
                    "notes": "",
                    "error": "",
                },
                {
                    "document_id": doc_taylor,
                    "queue_id": "",
                    "candidate_slug": "taylor-example",
                    "candidate_name": "Taylor Example",
                    "race_id": "race-2016",
                    "role": "opponent",
                    "election_date": "2016-05-10",
                    "publication_date": "2016-04-02",
                    "campaign_window_start": "2015-01-01",
                    "campaign_window_end": "2016-05-10",
                    "campaign_window_status": "in_window",
                    "source_type": "questionnaire",
                    "source_url": "https://example.com/taylor-qa",
                    "archive_url": "",
                    "final_url": "https://example.com/taylor-qa",
                    "retrieved_at": "2026-08-19T17:00:00+00:00",
                    "content_type": "text/html",
                    "title": "Taylor QA",
                    "coverage_status": "found_unverified",
                    "fetch_status": "reused_raw",
                    "extraction_status": "extracted",
                    "extractor": "html",
                    "raw_sha256": "2",
                    "text_sha256": "2",
                    "provenance_hash": "2",
                    "paragraph_count": "1",
                    "sentence_count": "1",
                    "raw_path": "",
                    "seed_kind": "known_document",
                    "source_record_id": "inv-2",
                    "notes": "",
                    "error": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "candidate_document_analysis_segments.csv",
            [
                self._segment_row("seg-casey", doc_casey, "Casey Example", "casey-example", "race-2016", "endorsed", "campaign_page", 22, "Build social housing at scale and fund schools for every neighborhood."),
                self._segment_row("seg-taylor", doc_taylor, "Taylor Example", "taylor-example", "race-2016", "opponent", "questionnaire", 21, "Expand public transit, protect tenants, and raise wages across the city."),
            ],
        )

        result = build_full_text_sufficiency_audit(self._paths(root))

        self.assertTrue(result.sufficient)
        summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["document_corpus"]["status"], "partial")
        self.assertEqual(summary["document_corpus"]["full_text_rows"], 0)
        self.assertEqual(summary["paired_races"]["eligible_count"], 1)
        self.assertEqual(summary["sufficiency"]["hard_gates"]["paired_race_two_sided_substantive_text"]["pass"], True)

    def test_paired_race_coverage_derives_from_clean_document_metadata_not_manual_queue(self) -> None:
        root = self._scenario_root("paired_from_clean_documents")
        doc_casey = self._doc_id(
            "Casey Example",
            "race-2016",
            "https://example.com/casey-platform",
            "campaign_page",
        )
        doc_taylor = self._doc_id(
            "Taylor Example",
            "race-2016",
            "https://example.com/taylor-qa",
            "questionnaire",
        )
        doc_jordan = self._doc_id(
            "Jordan Example",
            "race-2017",
            "https://example.com/jordan-platform",
            "campaign_page",
        )
        doc_robin = self._doc_id(
            "Robin Example",
            "race-2017",
            "https://example.com/robin-qa",
            "questionnaire",
        )
        self._write_json(
            root / "config" / "sources.json",
            {
                "study_start": "2016-01-01",
                "research_cutoff": "2017-12-31",
            },
        )
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "2016-endorsed",
                    "race_id": "race-2016",
                    "candidate_name": "Casey Example",
                    "election_date": "2016-05-10",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "quote": "Build social housing and expand transit access citywide.",
                    "source_url": "https://example.com/casey-platform",
                    "source_type": "official_campaign_page",
                    "published_date": "2016-04-01",
                    "locator": "Issues",
                    "notes": "",
                },
                {
                    "statement_key": "2016-opponent",
                    "race_id": "race-2016",
                    "candidate_name": "Taylor Example",
                    "election_date": "2016-05-10",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "quote": "Protect tenants and fully fund schools across the district.",
                    "source_url": "https://example.com/taylor-qa",
                    "source_type": "candidate_questionnaire",
                    "published_date": "2016-04-02",
                    "locator": "Q1",
                    "notes": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "documents.csv",
            [{"document_id": "doc-2016", "url": "https://example.com/endorsement-2016"}],
        )
        self._write_csv(
            root / "data" / "manual" / "endorsements.csv",
            [
                {
                    "race_id": "race-2016",
                    "election_date": "2016-05-10",
                    "endorsement_source_document_id": "doc-2016",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_candidates.csv",
            [
                {
                    "race_id": "race-2016",
                    "candidate_name": "Casey Example",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "source_url": "https://example.com/casey-platform",
                    "notes": "",
                },
                {
                    "race_id": "race-2016",
                    "candidate_name": "Taylor Example",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "source_url": "https://example.com/taylor-qa",
                    "notes": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "candidate_document_metadata.csv",
            [
                {
                    "document_id": doc_casey,
                    "queue_id": "",
                    "candidate_slug": "casey-example",
                    "candidate_name": "Casey Example",
                    "race_id": "race-2016",
                    "role": "endorsed",
                    "election_date": "2016-05-10",
                    "publication_date": "2016-04-01",
                    "campaign_window_start": "2015-01-01",
                    "campaign_window_end": "2016-05-10",
                    "campaign_window_status": "in_window",
                    "source_type": "campaign_page",
                    "source_url": "https://example.com/casey-platform",
                    "archive_url": "",
                    "final_url": "https://example.com/casey-platform",
                    "retrieved_at": "2026-08-19T17:00:00+00:00",
                    "content_type": "text/html",
                    "title": "Casey Platform",
                    "coverage_status": "found_unverified",
                    "fetch_status": "reused_raw",
                    "extraction_status": "extracted",
                    "extractor": "html",
                    "raw_sha256": "1",
                    "text_sha256": "1",
                    "provenance_hash": "1",
                    "paragraph_count": "1",
                    "sentence_count": "1",
                    "raw_path": "",
                    "seed_kind": "known_document",
                    "source_record_id": "inv-1",
                    "analysis_scope": "analysis",
                    "notes": "",
                    "error": "",
                },
                {
                    "document_id": doc_taylor,
                    "queue_id": "",
                    "candidate_slug": "taylor-example",
                    "candidate_name": "Taylor Example",
                    "race_id": "race-2016",
                    "role": "opponent",
                    "election_date": "2016-05-10",
                    "publication_date": "2016-04-02",
                    "campaign_window_start": "2015-01-01",
                    "campaign_window_end": "2016-05-10",
                    "campaign_window_status": "in_window",
                    "source_type": "questionnaire",
                    "source_url": "https://example.com/taylor-qa",
                    "archive_url": "",
                    "final_url": "https://example.com/taylor-qa",
                    "retrieved_at": "2026-08-19T17:00:00+00:00",
                    "content_type": "text/html",
                    "title": "Taylor QA",
                    "coverage_status": "found_unverified",
                    "fetch_status": "reused_raw",
                    "extraction_status": "extracted",
                    "extractor": "html",
                    "raw_sha256": "2",
                    "text_sha256": "2",
                    "provenance_hash": "2",
                    "paragraph_count": "1",
                    "sentence_count": "1",
                    "raw_path": "",
                    "seed_kind": "known_document",
                    "source_record_id": "inv-2",
                    "analysis_scope": "analysis",
                    "notes": "",
                    "error": "",
                },
                {
                    "document_id": doc_jordan,
                    "queue_id": "",
                    "candidate_slug": "jordan-example",
                    "candidate_name": "Jordan Example",
                    "race_id": "race-2017",
                    "role": "endorsed",
                    "election_date": "2017-06-06",
                    "publication_date": "2017-05-01",
                    "campaign_window_start": "2016-01-01",
                    "campaign_window_end": "2017-06-06",
                    "campaign_window_status": "in_window",
                    "source_type": "campaign_page",
                    "source_url": "https://example.com/jordan-platform",
                    "archive_url": "",
                    "final_url": "https://example.com/jordan-platform",
                    "retrieved_at": "2026-08-19T17:00:00+00:00",
                    "content_type": "text/html",
                    "title": "Jordan Platform",
                    "coverage_status": "found_unverified",
                    "fetch_status": "reused_raw",
                    "extraction_status": "extracted",
                    "extractor": "html",
                    "raw_sha256": "3",
                    "text_sha256": "3",
                    "provenance_hash": "3",
                    "paragraph_count": "1",
                    "sentence_count": "1",
                    "raw_path": "",
                    "seed_kind": "known_document",
                    "source_record_id": "inv-3",
                    "analysis_scope": "analysis",
                    "notes": "",
                    "error": "",
                },
                {
                    "document_id": doc_robin,
                    "queue_id": "",
                    "candidate_slug": "robin-example",
                    "candidate_name": "Robin Example",
                    "race_id": "race-2017",
                    "role": "opponent",
                    "election_date": "2017-06-06",
                    "publication_date": "2017-05-02",
                    "campaign_window_start": "2016-01-01",
                    "campaign_window_end": "2017-06-06",
                    "campaign_window_status": "in_window",
                    "source_type": "questionnaire",
                    "source_url": "https://example.com/robin-qa",
                    "archive_url": "",
                    "final_url": "https://example.com/robin-qa",
                    "retrieved_at": "2026-08-19T17:00:00+00:00",
                    "content_type": "text/html",
                    "title": "Robin QA",
                    "coverage_status": "found_unverified",
                    "fetch_status": "reused_raw",
                    "extraction_status": "extracted",
                    "extractor": "html",
                    "raw_sha256": "4",
                    "text_sha256": "4",
                    "provenance_hash": "4",
                    "paragraph_count": "1",
                    "sentence_count": "1",
                    "raw_path": "",
                    "seed_kind": "known_document",
                    "source_record_id": "inv-4",
                    "analysis_scope": "analysis",
                    "notes": "",
                    "error": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "candidate_document_analysis_segments.csv",
            [
                self._segment_row("seg-casey", doc_casey, "Casey Example", "casey-example", "race-2016", "endorsed", "campaign_page", 22, "Build social housing at scale and fund schools for every neighborhood."),
                self._segment_row("seg-taylor", doc_taylor, "Taylor Example", "taylor-example", "race-2016", "opponent", "questionnaire", 21, "Expand public transit, protect tenants, and raise wages across the city."),
                self._segment_row("seg-jordan", doc_jordan, "Jordan Example", "jordan-example", "race-2017", "endorsed", "campaign_page", 22, "Create fare-free buses, tenant protections, and a public bank."),
                self._segment_row("seg-robin", doc_robin, "Robin Example", "robin-example", "race-2017", "opponent", "questionnaire", 21, "Increase school funding, expand clinics, and strengthen labor protections."),
            ],
        )

        result = build_full_text_sufficiency_audit(self._paths(root))

        self.assertEqual(result.queue_source, "manual")
        self.assertEqual(result.eligible_races, 2)

        summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(
            summary["paired_races"]["basis"],
            "clean_candidate_document_metadata_and_analysis_segments",
        )
        self.assertEqual(summary["paired_races"]["eligible_count"], 2)
        self.assertEqual(summary["paired_races"]["years_with_eligible_races"], ["2016", "2017"])
        self.assertEqual(summary["queue"]["years_present"], ["2016"])

        paired_rows = self._read_csv(result.paired_race_path)
        self.assertEqual({row["race_id"] for row in paired_rows}, {"race-2016", "race-2017"})
        self.assertEqual(
            {row["paired_race_eligible"] for row in paired_rows},
            {"true"},
        )

    def test_duplicate_candidate_url_seeds_merge_into_one_document_queue_row(self) -> None:
        root = self._scenario_root("dedup_document_queue")
        self._write_json(
            root / "config" / "sources.json",
            {
                "study_start": "2016-01-01",
                "research_cutoff": "2016-12-31",
            },
        )
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "dup-1",
                    "race_id": "race-2016",
                    "candidate_name": "Casey Example",
                    "election_date": "2016-05-10",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "quote": "Build social housing for everyone in the city.",
                    "source_url": "https://casey.example/platform?utm_source=email",
                    "source_type": "official_campaign_page",
                    "published_date": "2016-04-01",
                    "locator": "Platform",
                    "notes": "",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "documents.csv",
            [{"document_id": "doc-2016", "url": ""}],
        )
        self._write_csv(
            root / "data" / "manual" / "endorsements.csv",
            [
                {
                    "race_id": "race-2016",
                    "election_date": "2016-05-10",
                    "endorsement_source_document_id": "doc-2016",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_candidates.csv",
            [
                {
                    "race_id": "race-2016",
                    "candidate_name": "Casey Example",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "source_url": "https://casey.example/platform",
                    "notes": "",
                }
            ],
        )

        result = build_full_text_sufficiency_audit(self._paths(root))

        document_queue = self._read_csv(result.document_queue_path)
        self.assertEqual(len(document_queue), 2)
        platform_row = next(
            row
            for row in document_queue
            if row["candidate_name"] == "Casey Example" and "platform" in row["source_url"]
        )
        self.assertEqual(
            platform_row["seed_kinds"],
            "known_document | official_election_source | queue_reference",
        )
        self.assertEqual(platform_row["legacy_locators"], "Platform")
        summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["discovery"]["document_queue_rows"], 2)

    def test_manual_roster_source_urls_seed_official_election_discovery_rows(self) -> None:
        root = self._scenario_root("manual_official_seed")
        self._write_json(
            root / "config" / "sources.json",
            {
                "study_start": "2016-01-01",
                "research_cutoff": "2016-12-31",
            },
        )
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "seed-1",
                    "race_id": "race-2016",
                    "candidate_name": "Casey Example",
                    "election_date": "2016-05-10",
                    "role": "endorsed",
                    "evidence_status": "source_unavailable",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "Search log",
                    "notes": "No first-party quote yet",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "documents.csv",
            [{"document_id": "doc-2016", "url": "https://example.com/endorsement-2016"}],
        )
        self._write_csv(
            root / "data" / "manual" / "endorsements.csv",
            [
                {
                    "race_id": "race-2016",
                    "election_date": "2016-05-10",
                    "endorsement_source_document_id": "doc-2016",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_candidates.csv",
            [
                {
                    "race_id": "race-2016",
                    "candidate_name": "Casey Example",
                    "role": "endorsed",
                    "evidence_status": "not_searched",
                    "source_url": "https://state.example/ballot-2016",
                    "notes": "",
                },
                {
                    "race_id": "race-2016",
                    "candidate_name": "Taylor Example",
                    "role": "opponent",
                    "evidence_status": "not_searched",
                    "source_url": "https://state.example/ballot-2016",
                    "notes": "",
                },
            ],
        )

        result = build_full_text_sufficiency_audit(self._paths(root))

        discovery_rows = self._read_csv(result.discovery_queue_path)
        official_seed_rows = [
            row for row in discovery_rows if row["seed_kind"] == "official_election_source"
        ]
        self.assertEqual(len(official_seed_rows), 2)
        self.assertEqual(
            {row["seed_url"] for row in official_seed_rows},
            {"https://state.example/ballot-2016"},
        )

    def test_transcriptless_only_full_text_is_not_marked_present(self) -> None:
        root = self._scenario_root("transcriptless_only")
        document_id = self._doc_id(
            "Media Example",
            "race-2016",
            "https://example.com/watch",
            "video",
        )
        self._write_json(
            root / "config" / "sources.json",
            {
                "study_start": "2016-01-01",
                "research_cutoff": "2016-12-31",
            },
        )
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "media-1",
                    "race_id": "race-2016",
                    "candidate_name": "Media Example",
                    "election_date": "2016-05-10",
                    "role": "endorsed",
                    "evidence_status": "source_unavailable",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "notes": "",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "documents.csv",
            [{"document_id": "doc-2016", "url": ""}],
        )
        self._write_csv(
            root / "data" / "manual" / "endorsements.csv",
            [
                {
                    "race_id": "race-2016",
                    "election_date": "2016-05-10",
                    "endorsement_source_document_id": "doc-2016",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_candidates.csv",
            [
                {
                    "race_id": "race-2016",
                    "candidate_name": "Media Example",
                    "role": "endorsed",
                    "evidence_status": "found_unverified",
                    "source_url": "https://example.com/watch",
                    "notes": "",
                }
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "candidate_document_metadata.csv",
            [
                {
                    "document_id": document_id,
                    "queue_id": "",
                    "candidate_slug": "media-example",
                    "candidate_name": "Media Example",
                    "race_id": "race-2016",
                    "role": "endorsed",
                    "election_date": "2016-05-10",
                    "publication_date": "",
                    "campaign_window_start": "2015-01-01",
                    "campaign_window_end": "2016-05-10",
                    "campaign_window_status": "undated",
                    "source_type": "video",
                    "source_url": "https://example.com/watch",
                    "coverage_status": "media_no_transcript",
                    "fetch_status": "reused_raw",
                    "extraction_status": "media_no_transcript",
                    "extractor": "media_no_transcript",
                }
            ],
        )
        self._write_jsonl(
            root / "data" / "processed" / "candidate_document_full_text.jsonl",
            [
                {
                    "document_id": document_id,
                    "candidate_name": "Media Example",
                    "race_id": "race-2016",
                    "role": "endorsed",
                    "source_type": "video",
                    "source_url": "https://example.com/watch",
                    "coverage_status": "media_no_transcript",
                    "text": "",
                }
            ],
        )

        result = build_full_text_sufficiency_audit(self._paths(root))

        summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["document_corpus"]["status"], "partial")
        self.assertIn("transcriptless media placeholders", summary["document_corpus"]["status_note"])
        self.assertEqual(summary["document_corpus"]["full_text_rows"], 1)

    def test_manual_candidate_document_registry_feeds_discovery_outputs(self) -> None:
        root = self._scenario_root("manual_candidate_documents")
        self._write_json(
            root / "config" / "sources.json",
            {
                "study_start": "2016-01-01",
                "research_cutoff": "2016-12-31",
            },
        )
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "c16-e",
                    "race_id": "race-2016",
                    "candidate_name": "Alex Example",
                    "election_date": "2016-06-14",
                    "role": "endorsed",
                    "evidence_status": "source_unavailable",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "notes": "",
                },
                {
                    "statement_key": "c16-o",
                    "race_id": "race-2016",
                    "candidate_name": "Blair Example",
                    "election_date": "2016-06-14",
                    "role": "opponent",
                    "evidence_status": "source_unavailable",
                    "quote": "",
                    "source_url": "",
                    "source_type": "",
                    "published_date": "",
                    "locator": "",
                    "notes": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "documents.csv",
            [{"document_id": "doc-2016", "url": "https://example.org/endorsement"}],
        )
        self._write_csv(
            root / "data" / "manual" / "endorsements.csv",
            [
                {
                    "endorsement_id": "endorse-2016",
                    "race_id": "race-2016",
                    "candidate_name": "Alex Example",
                    "election_date": "2016-06-14",
                    "endorsement_source_document_id": "doc-2016",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_candidates.csv",
            [
                {
                    "race_id": "race-2016",
                    "candidate_name": "Alex Example",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "source_url": "https://state.example/results",
                    "notes": "",
                },
                {
                    "race_id": "race-2016",
                    "candidate_name": "Blair Example",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "source_url": "https://state.example/results",
                    "notes": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "candidate_documents.csv",
            [
                {
                    "candidate_document_id": "candidate-doc-alex-platform",
                    "race_id": "race-2016",
                    "candidate_id": "alex-example",
                    "candidate_name": "Alex Example",
                    "role": "endorsed",
                    "election_date": "2016-06-14",
                    "title": "Alex Platform",
                    "source_type": "campaign_platform",
                    "source_tier": "1",
                    "publication_date": "2016-05-10",
                    "effective_date": "2016-05-10",
                    "source_url": "http://web.archive.org/web/20160510000000/https://alex.example/platform",
                    "live_url": "https://alex.example/platform",
                    "archive_url": "http://web.archive.org/web/20160510000000/https://alex.example/platform",
                    "locator": "",
                    "analysis_scope": "analysis",
                    "verification_status": "verified",
                    "notes": "Archive fetch target",
                },
                {
                    "candidate_document_id": "candidate-doc-blair-context",
                    "race_id": "race-2016",
                    "candidate_id": "blair-example",
                    "candidate_name": "Blair Example",
                    "role": "opponent",
                    "election_date": "2016-06-14",
                    "title": "Blair Bio",
                    "source_type": "candidate_profile",
                    "source_tier": "3",
                    "publication_date": "",
                    "effective_date": "",
                    "source_url": "https://ballotpedia.org/Blair_Example",
                    "live_url": "https://ballotpedia.org/Blair_Example",
                    "archive_url": "",
                    "locator": "",
                    "analysis_scope": "context_only",
                    "verification_status": "verified",
                    "notes": "Context only",
                },
            ],
        )

        result = build_full_text_sufficiency_audit(self._paths(root))

        inventory_rows = self._read_csv(result.source_inventory_path)
        alex_inventory = next(row for row in inventory_rows if row["candidate_name"] == "Alex Example")
        self.assertEqual(
            alex_inventory["fetch_url"],
            "http://web.archive.org/web/20160510000000/https://alex.example/platform",
        )
        self.assertEqual(alex_inventory["source_url"], "https://alex.example/platform")
        self.assertEqual(alex_inventory["source_tier"], "1")
        self.assertEqual(alex_inventory["publication_date"], "2016-05-10")
        self.assertEqual(alex_inventory["analysis_scope"], "analysis")

        document_queue = self._read_csv(result.document_queue_path)
        alex_queue = next(row for row in document_queue if row["candidate_name"] == "Alex Example")
        blair_queue = next(row for row in document_queue if row["candidate_name"] == "Blair Example")
        self.assertEqual(
            alex_queue["source_url"],
            "http://web.archive.org/web/20160510000000/https://alex.example/platform",
        )
        self.assertEqual(alex_queue["live_url"], "https://alex.example/platform")
        self.assertEqual(blair_queue["analysis_scope"], "context_only")

    def test_shared_document_unscoped_rows_do_not_inflate_support_counts(self) -> None:
        root = self._scenario_root("shared_unscoped_support")
        shared_url = "https://example.com/shared-guide.pdf"
        doc_a = self._doc_id("Alex Example", "race-2016", shared_url, "voter_guide")
        doc_b = self._doc_id("Blair Example", "race-2016", shared_url, "voter_guide")
        self._write_json(
            root / "config" / "sources.json",
            {
                "study_start": "2016-01-01",
                "research_cutoff": "2016-12-31",
            },
        )
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "shared-a",
                    "race_id": "race-2016",
                    "candidate_name": "Alex Example",
                    "election_date": "2016-05-10",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "quote": "Legacy quote.",
                    "source_url": shared_url,
                    "source_type": "official_voter_guide",
                    "published_date": "2016-04-01",
                    "locator": "PDF page 1",
                    "notes": "",
                },
                {
                    "statement_key": "shared-b",
                    "race_id": "race-2016",
                    "candidate_name": "Blair Example",
                    "election_date": "2016-05-10",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "quote": "Legacy quote.",
                    "source_url": shared_url,
                    "source_type": "official_voter_guide",
                    "published_date": "2016-04-01",
                    "locator": "PDF page 2",
                    "notes": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "documents.csv",
            [{"document_id": "doc-2016", "url": ""}],
        )
        self._write_csv(
            root / "data" / "manual" / "endorsements.csv",
            [
                {
                    "race_id": "race-2016",
                    "election_date": "2016-05-10",
                    "endorsement_source_document_id": "doc-2016",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_candidates.csv",
            [
                {
                    "race_id": "race-2016",
                    "candidate_name": "Alex Example",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "source_url": shared_url,
                    "notes": "",
                },
                {
                    "race_id": "race-2016",
                    "candidate_name": "Blair Example",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "source_url": shared_url,
                    "notes": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "candidate_document_metadata.csv",
            [
                {
                    "document_id": doc_a,
                    "queue_id": "",
                    "candidate_slug": "alex-example",
                    "candidate_name": "Alex Example",
                    "race_id": "race-2016",
                    "role": "endorsed",
                    "election_date": "2016-05-10",
                    "publication_date": "2016-04-01",
                    "campaign_window_start": "2015-01-01",
                    "campaign_window_end": "2016-05-10",
                    "campaign_window_status": "in_window",
                    "source_type": "voter_guide",
                    "source_url": shared_url,
                    "coverage_status": "shared_document_unscoped",
                    "fetch_status": "reused_raw",
                    "extraction_status": "shared_document_unscoped",
                    "extractor": "pdf",
                },
                {
                    "document_id": doc_b,
                    "queue_id": "",
                    "candidate_slug": "blair-example",
                    "candidate_name": "Blair Example",
                    "race_id": "race-2016",
                    "role": "opponent",
                    "election_date": "2016-05-10",
                    "publication_date": "2016-04-01",
                    "campaign_window_start": "2015-01-01",
                    "campaign_window_end": "2016-05-10",
                    "campaign_window_status": "in_window",
                    "source_type": "voter_guide",
                    "source_url": shared_url,
                    "coverage_status": "shared_document_unscoped",
                    "fetch_status": "reused_raw",
                    "extraction_status": "shared_document_unscoped",
                    "extractor": "pdf",
                },
            ],
        )
        self._write_jsonl(
            root / "data" / "processed" / "candidate_document_full_text.jsonl",
            [
                {
                    "document_id": doc_a,
                    "candidate_name": "Alex Example",
                    "race_id": "race-2016",
                    "role": "endorsed",
                    "source_type": "voter_guide",
                    "source_url": shared_url,
                    "coverage_status": "shared_document_unscoped",
                    "text": "",
                },
                {
                    "document_id": doc_b,
                    "candidate_name": "Blair Example",
                    "race_id": "race-2016",
                    "role": "opponent",
                    "source_type": "voter_guide",
                    "source_url": shared_url,
                    "coverage_status": "shared_document_unscoped",
                    "text": "",
                },
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "candidate_document_analysis_segments.csv",
            [
                self._segment_row(
                    "seg-shared-a",
                    doc_a,
                    "Alex Example",
                    "alex-example",
                    "race-2016",
                    "endorsed",
                    "voter_guide",
                    24,
                    "Contaminated shared text that should not count.",
                ),
                self._segment_row(
                    "seg-shared-b",
                    doc_b,
                    "Blair Example",
                    "blair-example",
                    "race-2016",
                    "opponent",
                    "voter_guide",
                    25,
                    "More contaminated shared text that should not count.",
                ),
            ],
        )

        result = build_full_text_sufficiency_audit(self._paths(root))

        summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["document_corpus"]["raw_extracted_document_count"], 2)
        self.assertEqual(summary["document_corpus"]["eligible_text_document_count"], 0)
        self.assertEqual(summary["document_corpus"]["shared_document_unscoped_count"], 2)
        self.assertEqual(summary["document_corpus"]["eligible_analysis_segment_rows"], 0)
        self.assertEqual(summary["document_corpus"]["substantive_candidate_count"], 0)
        self.assertEqual(summary["document_corpus"]["substantive_document_count"], 0)
        self.assertIn("excluded from analysis eligibility", summary["document_corpus"]["status_note"])
        support_rows = self._read_csv(result.group_year_support_path)
        by_group = {row["group"]: row for row in support_rows}
        self.assertEqual(by_group["endorsed"]["substantive_segment_count"], "0")
        self.assertEqual(by_group["opponent"]["substantive_segment_count"], "0")

    def test_queue_status_falls_back_to_document_id_when_seed_url_changes(self) -> None:
        root = self._scenario_root("queue_document_id_fallback")
        queue_url = "https://berniesanders.com/"
        metadata_url = "https://berniesanders.com/issues/medicare-for-all"
        document_id = self._doc_id(
            "Bernie Example",
            "race-2020",
            queue_url,
            "campaign_page",
        )
        self._write_json(
            root / "config" / "sources.json",
            {
                "study_start": "2020-01-01",
                "research_cutoff": "2020-12-31",
            },
        )
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "bern-1",
                    "race_id": "race-2020",
                    "candidate_name": "Bernie Example",
                    "election_date": "2020-03-03",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "quote": "Medicare for all is a human right.",
                    "source_url": metadata_url,
                    "source_type": "official_campaign_page",
                    "published_date": "2020-02-01",
                    "locator": "Issues",
                    "notes": "",
                }
            ],
        )
        manual_dir = root / "data" / "manual"
        manual_dir.mkdir(parents=True, exist_ok=True)
        (manual_dir / "documents.csv").write_text("document_id,url\n", encoding="utf-8")
        (manual_dir / "endorsements.csv").write_text(
            "race_id,election_date,endorsement_source_document_id\nrace-2020,2020-03-03,\n",
            encoding="utf-8",
        )
        self._write_csv(
            root / "data" / "manual" / "race_candidates.csv",
            [
                {
                    "race_id": "race-2020",
                    "candidate_name": "Bernie Example",
                    "role": "endorsed",
                    "evidence_status": "found_unverified",
                    "source_url": queue_url,
                    "notes": "Homepage seed replaces older issue URL.",
                }
            ],
        )
        self._write_csv(
            root / "data" / "processed" / "candidate_document_metadata.csv",
            [
                {
                    "document_id": document_id,
                    "queue_id": "",
                    "candidate_slug": "bernie-example",
                    "candidate_name": "Bernie Example",
                    "race_id": "race-2020",
                    "role": "endorsed",
                    "election_date": "2020-03-03",
                    "publication_date": "2020-02-01",
                    "campaign_window_start": "2019-01-01",
                    "campaign_window_end": "2020-03-03",
                    "campaign_window_status": "in_window",
                    "source_type": "campaign_page",
                    "source_url": metadata_url,
                    "coverage_status": "shared_document_unscoped",
                    "fetch_status": "reused_raw",
                    "extraction_status": "shared_document_unscoped",
                    "extractor": "html",
                }
            ],
        )
        self._write_jsonl(
            root / "data" / "processed" / "candidate_document_full_text.jsonl",
            [
                {
                    "document_id": document_id,
                    "candidate_name": "Bernie Example",
                    "race_id": "race-2020",
                    "role": "endorsed",
                    "source_type": "campaign_page",
                    "source_url": metadata_url,
                    "coverage_status": "shared_document_unscoped",
                    "text": "",
                }
            ],
        )

        result = build_full_text_sufficiency_audit(self._paths(root))

        queue_rows = self._read_csv(result.document_queue_path)
        bernie_rows = [row for row in queue_rows if row["candidate_name"] == "Bernie Example"]
        self.assertGreaterEqual(len(bernie_rows), 1)
        self.assertEqual({row["document_id"] for row in bernie_rows}, {document_id})
        self.assertEqual(
            {row["collection_status"] for row in bernie_rows},
            {"shared_document_unscoped"},
        )
        self.assertEqual(
            {row["metadata_status"] for row in bernie_rows},
            {"reused_raw/shared_document_unscoped"},
        )

    def test_invalid_manual_status_raises_value_error(self) -> None:
        root = self._scenario_root("invalid")
        self._write_json(
            root / "config" / "sources.json",
            {
                "study_start": "2016-01-01",
                "research_cutoff": "2016-12-31",
            },
        )
        self._write_csv(
            root / "data" / "analysis" / "candidate_text_corpus.csv",
            [
                {
                    "statement_key": "bad",
                    "race_id": "corpus-2016",
                    "candidate_name": "Casey Example",
                    "election_date": "2016-05-10",
                    "role": "endorsed",
                    "evidence_status": "verified",
                    "quote": "Exact quote.",
                    "source_url": "https://example.com/casey",
                    "source_type": "official_campaign_page",
                    "published_date": "2016-04-01",
                    "locator": "Platform",
                    "notes": "",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "documents.csv",
            [{"document_id": "doc-2016", "url": "https://example.com/endorsement-2016"}],
        )
        self._write_csv(
            root / "data" / "manual" / "endorsements.csv",
            [
                {
                    "race_id": "manual-race-2016",
                    "election_date": "2016-05-10",
                    "endorsement_source_document_id": "doc-2016",
                }
            ],
        )
        self._write_csv(
            root / "data" / "manual" / "race_candidates.csv",
            [
                {
                    "race_id": "manual-race-2016",
                    "candidate_name": "Casey Example",
                    "role": "endorsed",
                    "evidence_status": "pending_review",
                    "source_url": "https://example.com/casey",
                    "notes": "Bad status",
                },
                {
                    "race_id": "manual-race-2016",
                    "candidate_name": "Taylor Example",
                    "role": "opponent",
                    "evidence_status": "verified",
                    "source_url": "https://example.com/taylor",
                    "notes": "Valid row",
                },
            ],
        )

        with self.assertRaisesRegex(ValueError, "invalid evidence_status"):
            build_full_text_sufficiency_audit(self._paths(root))

    def _scenario_root(self, name: str) -> Path:
        root = SCRATCH_ROOT / name
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _paths(self, root: Path) -> FullTextAuditPaths:
        return FullTextAuditPaths(
            candidate_corpus_path=root / "data" / "analysis" / "candidate_text_corpus.csv",
            config_path=root / "config" / "sources.json",
            manual_documents_path=root / "data" / "manual" / "documents.csv",
            manual_candidate_documents_path=root / "data" / "manual" / "candidate_documents.csv",
            manual_endorsements_path=root / "data" / "manual" / "endorsements.csv",
            manual_race_candidates_path=root / "data" / "manual" / "race_candidates.csv",
            processed_opponent_queue_path=root / "data" / "processed" / "opponent_research_queue.csv",
            processed_race_rosters_path=root / "data" / "processed" / "race_rosters_discovered.csv",
            processed_candidate_evidence_path=root / "data" / "processed" / "candidate_statement_evidence.csv",
            candidate_document_metadata_path=root / "data" / "processed" / "candidate_document_metadata.csv",
            candidate_document_full_text_path=root / "data" / "processed" / "candidate_document_full_text.jsonl",
            candidate_document_analysis_segments_path=root / "data" / "processed" / "candidate_document_analysis_segments.csv",
            output_dir=root / "data" / "processed",
        )

    def _segment_row(
        self,
        segment_id: str,
        document_id: str,
        candidate_name: str,
        candidate_slug: str,
        race_id: str,
        role: str,
        source_type: str,
        token_count: int,
        text: str,
    ) -> dict[str, str]:
        return {
            "analysis_segment_id": segment_id,
            "document_id": document_id,
            "candidate_slug": candidate_slug,
            "candidate_name": candidate_name,
            "race_id": race_id,
            "role": role,
            "source_type": source_type,
            "segment_index": "1",
            "analysis_kind": "paragraph",
            "locator": "paragraph 1",
            "source_locator_start": "paragraph 1",
            "source_locator_end": "paragraph 1",
            "paragraph_start": "1",
            "paragraph_end": "1",
            "sentence_start": "1",
            "sentence_end": "1",
            "text": text,
            "token_count": str(token_count),
            "sha256": segment_id,
            "exact_duplicate_hash": segment_id,
            "exact_duplicate_count": "1",
            "exact_duplicate_flag": "false",
            "near_duplicate_hash": segment_id,
            "near_duplicate_count": "1",
            "near_duplicate_flag": "false",
            "boilerplate_flag": "false",
            "boilerplate_reasons": "",
        }

    def _doc_id(self, candidate_name: str, race_id: str, source_url: str, source_type: str) -> str:
        return candidate_document_id(candidate_name, race_id, source_url, source_type)

    def _write_csv(self, path: Path, rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _write_jsonl(self, path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
