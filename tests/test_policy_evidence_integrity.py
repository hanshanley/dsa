import hashlib
import gzip
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.document_corpus import (
    TextSegment,
    build_analysis_segments,
    candidate_document_analysis_issues,
    tracked_primary_race_ids,
    build_candidate_source_inventory,
    build_candidate_document_discovery_queue,
    RawDocumentCapture,
    ExtractionError,
    extract_document_text,
    canonical_source_url,
    _apply_source_date_corrections,
    _apply_source_association_corrections,
    _apply_source_exclusions,
    _append_campaign_discovery_queue_rows,
    _parse_feed_entries,
    _normalize_candidate_document_job,
    DocumentCorpusError,
)
from dsa_analysis.sticking_points import _relationship
from dsa_analysis.full_text_audit import _load_corpus_rows, _load_document_metadata_rows
from dsa_analysis.io import write_csv
from dsa_analysis.race_registry import _scope_resolutions


class PolicyEvidenceIntegrityTests(unittest.TestCase):
    def test_wrong_content_exclusion_is_hash_and_race_specific(self):
        from dataclasses import replace
        body = b"Not the old campaign"
        job = _normalize_candidate_document_job({
            "candidate_name": "Example", "race_id": "race-2024", "role": "endorsed",
            "election_date": "2024-06-25", "source_type": "campaign_platform",
            "source_url": "https://candidate.example/issues",
        })
        capture = RawDocumentCapture(
            job.document_id, job.source_url, "https://different.example/", "2026-09-24",
            "text/plain", "utf-8", body, len(body), hashlib.sha256(body).hexdigest(),
        )
        exclusion = {
            "candidate_name": "Example", "race_id": "race-2024", "source_sha256": capture.sha256,
            "reason": "Wrong office and cycle.",
        }
        corrected = _apply_source_exclusions(job, capture, [exclusion])
        self.assertEqual(corrected.analysis_scope, "context_only")
        self.assertEqual(_apply_source_exclusions(corrected, capture, [exclusion]), corrected)
        other_race = replace(job, race_id="race-2026")
        self.assertEqual(_apply_source_exclusions(other_race, capture, [exclusion]), other_race)
        self.assertEqual(_apply_source_exclusions(job, replace(capture, sha256="other"), [exclusion]), job)

    def test_requested_archive_and_campaign_redirect_are_not_identity_proof(self):
        row = self.metadata(
            source_type="campaign_platform", source_url="https://candidate.example/issues",
            final_url="https://different.example/", analysis_scope="analysis",
            archive_url="https://web.archive.org/web/20200501/https://candidate.example/issues",
        )
        issues = candidate_document_analysis_issues(row)
        self.assertIn("requested_archive_capture_not_retained", issues)
        self.assertIn("campaign_redirect_requires_identity_and_cycle_review", issues)
        archived = {**row, "final_url": row["archive_url"]}
        self.assertNotIn("requested_archive_capture_not_retained", candidate_document_analysis_issues(archived))
        self.assertNotIn("campaign_redirect_requires_identity_and_cycle_review", candidate_document_analysis_issues(archived))
        direct_request = {**row, "source_url": row["archive_url"], "archive_url": ""}
        self.assertIn("requested_archive_capture_not_retained", candidate_document_analysis_issues(direct_request))

    def test_discovery_timestamps_do_not_become_publication_dates(self):
        source = {
            "candidate_name": "Example", "candidate_slug": "example", "race_id": "race", "role": "endorsed",
            "election_date": "2026-06-23", "source_url": "https://candidate.example/issues",
            "source_type_class": "policy_page", "discovery_stage": "archive",
            "discovery_method": "wayback_cdx", "archive_timestamp": "20260501120000",
            "archive_url": "https://web.archive.org/web/20260501120000/https://candidate.example/issues",
            "discovery_provenance_date": "2026-05-01",
        }
        rows, added = _append_campaign_discovery_queue_rows([], [source])
        self.assertEqual(added, 1)
        self.assertEqual(rows[0]["publication_date"], "")
        self.assertEqual(rows[0]["archive_url"], source["archive_url"])
        legacy = _normalize_candidate_document_job({**rows[0], "publication_date": "2026-05-01"})
        self.assertEqual(legacy.publication_date, "")
        self.assertIn("Discovery provenance date is not document publication", legacy.notes)
        feed = "<feed><entry><link href='https://example.org/post'/><updated>2026-05-01</updated></entry></feed>"
        self.assertEqual(_parse_feed_entries(feed)[0]["published_at"], "")

    def test_source_race_correction_is_exact_and_cannot_cross_elections(self):
        from dataclasses import replace
        body = b"<p>Candidate for District2.</p>"
        job = _normalize_candidate_document_job({
            "document_id": "legacy", "candidate_name": "Example", "role": "opponent",
            "race_id": "wrong-race", "election_date": "2020-08-04",
            "source_type": "candidate_profile", "source_url": "https://example.org/candidate",
        })
        capture = RawDocumentCapture(
            job.document_id, job.source_url, job.source_url, "2026-09-24", "text/html", "utf-8",
            body, len(body), hashlib.sha256(body).hexdigest(),
        )
        correction = {
            "candidate_name": "Example", "source_url": job.source_url, "source_sha256": capture.sha256,
            "previous_race_id": "wrong-race", "corrected_race_id": "right-race",
            "election_date": "2020-08-04", "role": "opponent", "reason": "Official roster correction.",
        }
        corrected = _apply_source_association_corrections(job, capture, [correction])
        self.assertEqual(corrected.race_id, "right-race")
        self.assertEqual(corrected.document_id, job.document_id)
        self.assertEqual(_apply_source_association_corrections(corrected, capture, [correction]), corrected)
        other = replace(job, candidate_name="Another Candidate")
        self.assertEqual(_apply_source_association_corrections(other, capture, [correction]), other)
        with self.assertRaisesRegex(DocumentCorpusError, "reviewed source version"):
            _apply_source_association_corrections(job, replace(capture, sha256="different"), [correction])
        with self.assertRaisesRegex(DocumentCorpusError, "election date"):
            _apply_source_association_corrections(replace(job, election_date="2024-08-06"), capture, [correction])

    def test_rejected_primary_date_cannot_reenter_through_a_legacy_queue(self):
        from dataclasses import replace
        body = b"<p>Candidate platform without a publication date.</p>"
        job = _normalize_candidate_document_job({
            "document_id": "legacy-id", "candidate_name": "Example", "race_id": "race",
            "role": "opponent",
            "election_date": "2026-06-23", "publication_date": "2026-06-23",
            "source_type": "campaign_platform", "source_url": "https://example.org/platform",
        })
        capture = RawDocumentCapture(
            job.document_id, job.source_url, job.source_url, "2026-08-20", "text/html", "utf-8",
            body, len(body), hashlib.sha256(body).hexdigest(),
        )
        corrections = [{
            "source_url": job.source_url, "source_sha256": capture.sha256,
            "rejected_publication_date": job.publication_date,
            "reason": "The primary day is not present in the retained source.",
        }]
        corrected = _apply_source_date_corrections(job, capture, corrections)
        self.assertEqual(corrected.publication_date, "")
        self.assertIn("Rejected unsupported publication date", corrected.notes)
        self.assertEqual(_apply_source_date_corrections(corrected, capture, corrections), corrected)
        self.assertEqual(
            _apply_source_date_corrections(replace(job, document_id="alias-id"), capture, corrections).publication_date,
            "",
        )
        self.assertEqual(
            _apply_source_date_corrections(replace(job, publication_date="2026-05-01"), capture, corrections).publication_date,
            "2026-05-01",
        )
        replacement = [{**corrections[0], "replacement_publication_date": "2026-05-01"}]
        self.assertEqual(_apply_source_date_corrections(job, capture, replacement).publication_date, "2026-05-01")
        self.assertEqual(
            _apply_source_date_corrections(replace(job, publication_date=""), capture, replacement).publication_date,
            "2026-05-01",
        )
        self.assertEqual(
            _apply_source_date_corrections(
                replace(job, publication_date=""), replace(capture, sha256="different"), replacement,
            ).publication_date,
            "",
        )
        with self.assertRaisesRegex(DocumentCorpusError, "different source version"):
            _apply_source_date_corrections(job, replace(capture, sha256="different"), corrections)

    def test_effective_date_does_not_become_a_publication_date(self):
        row = {
            "document_id": "doc", "candidate_name": "Example", "role": "opponent", "race_id": "race",
            "election_date": "2026-06-23", "effective_date": "2026-06-23",
            "source_type": "campaign_platform", "source_url": "https://example.org/platform",
        }
        job = _normalize_candidate_document_job(row)
        self.assertEqual(job.publication_date, "")
        self.assertIn("not inferred as publication", job.notes)
        self.assertEqual(
            _normalize_candidate_document_job({**row, "publication_date": "2026-05-01"}).publication_date,
            "2026-05-01",
        )
        self.assertEqual(
            _normalize_candidate_document_job({**row, "published_date": "2026-05-02"}).publication_date,
            "2026-05-02",
        )

    def test_interview_and_questionnaire_text_need_explicit_candidate_scoping(self):
        for source_type in ("candidate_interview", "candidate_questionnaire", "candidate_debate", "voter_guide", "candidate_profile"):
            with self.subTest(source_type=source_type):
                row = self.metadata(
                    source_type=source_type, source_url="https://publisher.example/candidate",
                    analysis_scope="analysis", campaign_window_status="in_window",
                )
                self.assertIn("mixed_speaker_source_requires_candidate_scope", candidate_document_analysis_issues(row))
                self.assertEqual(candidate_document_analysis_issues({**row, "analysis_scope": "candidate_excerpt"}), [])
                self.assertEqual(
                    candidate_document_analysis_issues({**row, "analysis_scope": "reviewed_quote"}),
                    ["reviewed_quote_not_full_text_input"],
                )

    def test_generic_binary_pdf_uses_its_signature_without_rewriting_transport_metadata(self):
        body = b"%PDF-1.3\nretained test bytes"
        capture = RawDocumentCapture(
            document_id="binary-pdf", source_url="https://example.org/download?id=123",
            final_url="https://example.org/download?id=123", retrieved_at="2026-09-24",
            content_type="application/octet-stream", encoding="utf-8", content_bytes=body,
            byte_count=len(body), sha256=hashlib.sha256(body).hexdigest(),
        )
        with patch("dsa_analysis.document_corpus._extract_pdf_text", return_value=("", "Candidate answer.")) as parser:
            result = extract_document_text(capture)
        parser.assert_called_once_with(body)
        self.assertEqual(result.extractor, "pdf")
        self.assertEqual(result.content_type, "application/octet-stream")
        self.assertEqual(capture.content_bytes, body)
        from dataclasses import replace
        with self.assertRaisesRegex(ExtractionError, "unsupported content type"):
            extract_document_text(replace(capture, content_bytes=b"Not a PDF"))

    def test_revoked_endorsement_stays_out_of_scope_even_with_a_legacy_endorsement(self):
        resolution = {
            "race_id": "race", "scope_kind": "other_corpus_race",
            "classification": "endorsement_revoked_before_primary",
            "source_url": "https://chapter.example/revocation", "notes": "Revoked before the primary.",
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "scope.csv"
            write_csv(path, [resolution], list(resolution))
            self.assertEqual(_scope_resolutions(path, {"race": []}), {"race": "other_corpus_race"})
        registry = [{
            "race_id": "race", "scope_kind": "other_corpus_race",
            "election_date": "2022-07-19", "endorsed_candidate": "Example",
        }]
        endorsements = [{
            "race_id": "legacy", "election_date": "2022-07-19",
            "candidate_name": "Example", "verification_status": "verified",
        }]
        self.assertEqual(tracked_primary_race_ids(registry, endorsements), set())

    def test_archived_candidate_queries_remain_distinct_and_match_their_live_sources(self):
        live = "https://example.gov/candidates?OfficeCode=1&ElectionCode=2026"
        archived = "https://web.archive.org/web/20260606074525id_/" + live
        other = archived.replace("OfficeCode=1", "OfficeCode=4")
        self.assertEqual(canonical_source_url(archived), canonical_source_url(live))
        self.assertNotEqual(canonical_source_url(archived), canonical_source_url(other))
    def test_gzip_archive_is_decoded_without_changing_retained_source_identity(self):
        body = gzip.compress(b"<html><title>Policy</title><p>Healthcare is a human right.</p></html>", mtime=0)
        capture = RawDocumentCapture(
            document_id="archive", source_url="https://example.org/policy",
            final_url="https://example.org/policy", retrieved_at="2026-09-23",
            content_type="text/html", encoding="utf-8", content_bytes=body,
            byte_count=len(body), sha256=hashlib.sha256(body).hexdigest(),
        )
        document = extract_document_text(capture)
        self.assertEqual(document.title, "Policy")
        self.assertEqual(document.text, "Healthcare is a human right.")
        self.assertEqual(capture.content_bytes, body)
        self.assertEqual(capture.sha256, hashlib.sha256(body).hexdigest())
        self.assertEqual(capture.suffix, ".html.gz")
        with patch("dsa_analysis.document_corpus.MAX_DECOMPRESSED_DOCUMENT_BYTES", 10):
            with self.assertRaisesRegex(ExtractionError, "size limit"):
                extract_document_text(capture)

    def test_roster_seeds_allow_honest_unsearched_and_unverified_policy_statuses(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "seed.csv"
            rows = [{
                "race_id": "race", "candidate_name": status, "role": "opponent",
                "election_date": "2026-03-17", "evidence_status": status,
            } for status in ("not_searched", "found_unverified")]
            write_csv(path, rows, list(rows[0]))
            self.assertEqual(len(_load_corpus_rows(path, [2026])), 2)
            rows[0].update({"quote": "", "source_url": "", "evidence_status": "verified"})
            write_csv(path, rows[:1], list(rows[0]))
            with self.assertRaisesRegex(ValueError, "verified row requires"):
                _load_corpus_rows(path, [2026])
    def test_excerpt_scope_survives_discovery_and_inventory_rebuilds(self):
        source = {
            "race_id": "race", "candidate_name": "Jane Example", "role": "endorsed",
            "election_date": "2026-06-16", "source_url": "https://example.org/interview",
            "source_type": "candidate_interview", "analysis_scope": "candidate_excerpt",
            "locator": "paragraph 4", "publication_date": "2026-05-01",
        }
        inventory = build_candidate_source_inventory([], [], [source])
        self.assertEqual(inventory[0]["analysis_scope"], "candidate_excerpt")
        queue = build_candidate_document_discovery_queue([], [], [source])
        known = next(row for row in queue if row["seed_kind"] == "known_document")
        self.assertEqual(known["analysis_scope"], "candidate_excerpt")

    def test_quote_only_scope_is_not_promoted_to_full_text_by_inventory_rebuild(self):
        source = {
            "race_id": "race", "candidate_name": "Jane Example", "role": "endorsed",
            "election_date": "2026-06-16", "source_url": "https://example.org/interview",
            "source_type": "candidate_interview", "analysis_scope": "reviewed_quote",
            "locator": "paragraph 4 quote: I support public housing.", "publication_date": "2026-05-01",
        }
        inventory = build_candidate_source_inventory([], [], [source])
        self.assertEqual(inventory[0]["analysis_scope"], "reviewed_quote")
        queue = build_candidate_document_discovery_queue([], [], [source])
        known = next(row for row in queue if row["seed_kind"] == "known_document")
        self.assertEqual(known["analysis_scope"], "reviewed_quote")
        full_source = {**source, "source_type": "official_campaign_platform", "analysis_scope": "analysis"}
        quote_source = {**full_source, "analysis_scope": "reviewed_quote"}
        combined = build_candidate_source_inventory([], [], [full_source, quote_source])
        self.assertEqual(combined[0]["analysis_scope"], "analysis")

    def test_verified_legacy_endorsement_race_id_survives_canonicalization(self):
        registry = [{
            "race_id": "canonical", "scope_kind": "tracked_dsa_endorsed_democratic_primary",
            "election_date": "2016-09-08", "endorsed_candidate": "Mike Connolly",
        }]
        endorsements = [{
            "race_id": "legacy", "election_date": "2016-09-08",
            "candidate_name": "Mike Connolly", "verification_status": "verified",
        }]
        self.assertEqual(tracked_primary_race_ids(registry, endorsements), {"canonical", "legacy"})
        endorsements[0]["election_date"] = "2026-09-08"
        self.assertEqual(tracked_primary_race_ids(registry, endorsements), {"canonical"})

    def metadata(self, **overrides):
        return {
            "candidate_name": "Jane Example",
            "candidate_slug": "jane-example",
            "source_url": "https://janeexample.com/issues",
            "source_type": "policy_page",
            "title": "Jane Example's priorities",
            "extraction_status": "extracted",
            "coverage_status": "found_unverified",
            "election_date": "2026-08-04",
            "campaign_window_status": "undated",
            "retrieved_at": "2026-06-01T12:00:00+00:00",
            **overrides,
        }

    def test_newspaper_homepage_is_not_a_historical_candidate_platform(self):
        issues = candidate_document_analysis_issues(self.metadata(
            candidate_name="Mike Sylvester", candidate_slug="mike-sylvester",
            source_url="https://pressherald.com/", source_type="campaign_page",
            title="Portland Press Herald - Maine Sunday Telegram",
            election_date="2016-06-14", retrieved_at="2026-08-20T04:33:44+00:00",
        ))
        self.assertEqual(set(issues), {
            "unattributed_campaign_homepage", "undated_source_without_in_window_capture",
        })

    def test_dated_or_in_window_archived_evidence_remains_eligible(self):
        self.assertEqual(candidate_document_analysis_issues(self.metadata()), [])
        self.assertEqual(candidate_document_analysis_issues(self.metadata(
            election_date="2016-06-14",
            archive_url="https://web.archive.org/web/20160607163830/https://janeexample.com/issues",
        )), [])

    def test_requested_archive_date_cannot_override_a_later_actual_replay(self):
        row = self.metadata(
            election_date="2026-03-17",
            archive_url="https://web.archive.org/web/20260316000000/https://janeexample.com/issues",
            final_url="https://web.archive.org/web/20260319000000/https://janeexample.com/issues",
        )
        self.assertIn("undated_source_without_in_window_capture", candidate_document_analysis_issues(row))

    def test_post_primary_and_unscoped_documents_are_excluded(self):
        self.assertIn("outside_primary_campaign_window", candidate_document_analysis_issues(
            self.metadata(campaign_window_status="out_of_window")
        ))

    def test_dated_rolling_press_index_is_not_a_single_dated_policy_document(self):
        row = self.metadata(source_url="https://janeexample.com/category/press/")
        self.assertIn("rolling_index_requires_article_or_excerpt_scope", candidate_document_analysis_issues(row))
        self.assertEqual(candidate_document_analysis_issues({**row, "analysis_scope": "candidate_excerpt"}), [])

    def test_ballot_metadata_is_not_policy_text_without_a_reviewed_candidate_section(self):
        row = self.metadata(source_type="filing", source_url="https://example.gov/results")
        self.assertIn("filing_context_is_not_candidate_policy", candidate_document_analysis_issues(row))
        self.assertEqual(candidate_document_analysis_issues({**row, "analysis_scope": "candidate_excerpt"}), [])

    def test_audit_loader_keeps_temporal_and_attribution_checks(self):
        row = self.metadata(
            document_id="source", race_id="race", role="endorsed",
            campaign_window_status="out_of_window",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata.csv"
            write_csv(path, [row], list(row))
            loaded = _load_document_metadata_rows(path)[0]
        self.assertEqual(loaded["campaign_window_status"], "out_of_window")
        self.assertEqual(loaded["retrieved_at"], row["retrieved_at"])
        self.assertIn("outside_primary_campaign_window", candidate_document_analysis_issues(loaded))
        self.assertIn("not_extracted_or_unscoped", candidate_document_analysis_issues(
            self.metadata(extraction_status="shared_document_unscoped")
        ))

    def test_news_tip_instructions_are_boilerplate_not_a_policy_position(self):
        text = "SEND US YOUR CONFIDENTIAL NEWS TIP Add your confidential information here."
        paragraph = TextSegment(
            segment_id="paragraph", document_id="document", segment_kind="paragraph",
            index=1, locator="paragraph 1", text=text,
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )
        segments = build_analysis_segments(
            candidate_name="Jane Example", race_id="race", role="endorsed",
            document_id="document", paragraphs=[paragraph], sentences=[],
        )
        self.assertTrue(segments[0].boilerplate_flag)

    def test_opposite_stances_on_different_policies_are_not_disagreement(self):
        left = [{"subtopic": "single_payer", "stance": "support"}]
        right = [{"subtopic": "public_option", "stance": "oppose"}]
        self.assertEqual(_relationship(left, right), ("", {}, {}))

    def test_disagreement_requires_the_same_policy_and_mechanisms_require_support(self):
        support = [{"subtopic": "single_payer", "stance": "support"}]
        oppose = [{"subtopic": "single_payer", "stance": "oppose"}]
        alternative = [{"subtopic": "public_option", "stance": "support"}]
        self.assertEqual(_relationship(support, oppose)[0], "explicit_disagreement")
        self.assertEqual(_relationship(support, alternative)[0], "different_mechanism")


if __name__ == "__main__":
    unittest.main()
