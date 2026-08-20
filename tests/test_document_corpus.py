import csv
import hashlib
import json
import subprocess
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.document_corpus import (
    AnalysisSegmentConfig,
    CampaignDomainDiscoveryPaths,
    CandidateDocumentBatchPaths,
    COVERAGE_STATUSES,
    ExtractionError,
    RawFetchError,
    RawDocumentCapture,
    build_analysis_segment_review_sample,
    build_analysis_segments,
    build_candidate_document_discovery_queue,
    build_candidate_source_inventory,
    build_candidate_document_metadata,
    build_candidate_document_regather_plan,
    canonical_source_url,
    campaign_window_for_election,
    candidate_document_id,
    classify_source_type,
    extract_document_text,
    fetch_raw_document,
    normalize_source_url,
    persist_raw_document,
    run_candidate_document_regather_batch,
    run_campaign_domain_discovery_pass,
    run_candidate_document_extraction_batch,
    segment_document,
    segment_paragraphs,
    segment_sentences,
    stable_hash,
)
from dsa_analysis.schema import VERIFICATION_STATUSES

SCRATCH_ROOT = Path(__file__).resolve().parent / "_scratch_document_corpus"


class _Headers:
    def __init__(self, content_type: str, charset: str = "utf-8") -> None:
        self._content_type = content_type
        self._charset = charset

    def get_content_type(self) -> str:
        return self._content_type

    def get_content_charset(self) -> str:
        return self._charset


class _Response:
    def __init__(
        self,
        body: bytes,
        *,
        final_url: str,
        content_type: str,
        charset: str = "utf-8",
    ) -> None:
        self._body = body
        self._final_url = final_url
        self.headers = _Headers(content_type, charset)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self._body

    def geturl(self) -> str:
        return self._final_url


class DocumentCorpusTests(unittest.TestCase):
    def test_fetch_raw_document_preserves_provenance(self) -> None:
        with patch(
            "dsa_analysis.document_corpus.urllib.request.urlopen",
            return_value=_Response(
                b"Policy text.",
                final_url="https://example.org/platform.txt",
                content_type="text/plain",
            ),
        ):
            capture = fetch_raw_document("doc-1", "https://example.org/platform.txt")

        self.assertEqual(capture.source_url, "https://example.org/platform.txt")
        self.assertEqual(capture.final_url, "https://example.org/platform.txt")
        self.assertEqual(capture.content_type, "text/plain")
        self.assertEqual(capture.byte_count, 12)
        self.assertEqual(capture.sha256, hashlib.sha256(b"Policy text.").hexdigest())

    def test_html_extraction_builds_deterministic_metadata(self) -> None:
        document_id = candidate_document_id(
            "Zohran Mamdani",
            "nyc-mayor-primary-2025",
            "https://Example.org/issues#housing",
            "campaign_issues",
        )
        capture = RawDocumentCapture(
            document_id=document_id,
            source_url=normalize_source_url("https://Example.org/issues#housing"),
            final_url=normalize_source_url("https://example.org/issues"),
            retrieved_at="2026-08-19T17:00:00+00:00",
            content_type="text/html",
            encoding="utf-8",
            content_bytes=(
                b"<html><head><title>Housing Platform</title></head>"
                b"<body><p>Build social housing. Freeze the rent.</p>"
                b"<p>Dr. Rivera backs public power. Tax the rich.</p>"
                b"<script>ignore me</script></body></html>"
            ),
            byte_count=157,
            sha256="a" * 64,
        )

        extracted = extract_document_text(capture)
        metadata = build_candidate_document_metadata(
            candidate_name="Zohran Mamdani",
            race_id="nyc-mayor-primary-2025",
            election_date="2025-06-24",
            publication_date="2025-03-01",
            source_type="campaign_issues",
            capture=capture,
            extracted=extracted,
        )

        self.assertEqual(extracted.title, "Housing Platform")
        self.assertEqual([row.text for row in extracted.paragraphs], [
            "Build social housing. Freeze the rent.",
            "Dr. Rivera backs public power. Tax the rich.",
        ])
        self.assertEqual(
            [row.text for row in extracted.sentences],
            [
                "Build social housing.",
                "Freeze the rent.",
                "Dr. Rivera backs public power.",
                "Tax the rich.",
            ],
        )
        self.assertEqual(extracted.sentences[2].locator, "paragraph 2 sentence 1")
        self.assertEqual(metadata.campaign_window_start, "2024-01-01")
        self.assertEqual(metadata.campaign_window_end, "2025-06-24")
        self.assertEqual(metadata.campaign_window_status, "in_window")
        self.assertEqual(metadata.coverage_status, "found_unverified")
        self.assertEqual(metadata.paragraph_count, 2)
        self.assertEqual(metadata.sentence_count, 4)
        self.assertEqual(metadata.document_id, document_id)
        self.assertEqual(metadata.as_row()["paragraph_count"], "2")

    def test_plain_text_segmentation_is_deterministic(self) -> None:
        text = (
            "Workers deserve a raise.\nStill the same paragraph.\n\n"
            "Dr. Jones supports rent control! Public power now?"
        )
        self.assertEqual(
            segment_paragraphs(text),
            (
                "Workers deserve a raise. Still the same paragraph.",
                "Dr. Jones supports rent control! Public power now?",
            ),
        )
        self.assertEqual(
            segment_sentences(text),
            (
                "Workers deserve a raise.",
                "Still the same paragraph.",
                "Dr. Jones supports rent control!",
                "Public power now?",
            ),
        )

    def test_media_content_uses_media_no_transcript_status(self) -> None:
        capture = RawDocumentCapture(
            document_id="media-doc",
            source_url="https://example.org/video",
            final_url="https://example.org/video",
            retrieved_at="2026-08-19T17:00:00+00:00",
            content_type="video/mp4",
            encoding="utf-8",
            content_bytes=b"",
            byte_count=0,
            sha256=hashlib.sha256(b"").hexdigest(),
        )

        extracted = extract_document_text(capture)

        self.assertEqual(extracted.coverage_status, "media_no_transcript")
        self.assertEqual(extracted.paragraphs, ())
        self.assertIn("media_no_transcript", COVERAGE_STATUSES)

    def test_pdf_prefers_swift_pdfkit_output_and_sanitizes_controls(self) -> None:
        capture = RawDocumentCapture(
            document_id="pdf-doc",
            source_url="https://example.org/platform.pdf",
            final_url="https://example.org/platform.pdf",
            retrieved_at="2026-08-19T17:00:00+00:00",
            content_type="application/pdf",
            encoding="utf-8",
            content_bytes=b"%PDF-1.7",
            byte_count=8,
            sha256="b" * 64,
        )

        with patch(
            "dsa_analysis.document_corpus._pdf_reader_class",
            side_effect=ExtractionError("PDF extraction requires the optional dependency 'pypdf'"),
        ), patch(
            "dsa_analysis.document_corpus.platform.system",
            return_value="Darwin",
        ), patch(
            "dsa_analysis.document_corpus._swift_executable",
            return_value=Path("/usr/bin/swift"),
        ), patch(
            "dsa_analysis.document_corpus.subprocess.run",
            return_value=subprocess.CompletedProcess(
                ["/usr/bin/swift"],
                0,
                stdout=(
                    b'{"title":"Platform\\u0000 PDF","pages":'
                    b'[{"page":"1","text":"Housing\\u0000 for all"},'
                    b'{"page":"2","text":"Labor\\u000b rights now"}]}'
                ),
                stderr=b"",
            ),
        ):
            extracted = extract_document_text(capture)

        self.assertEqual(extracted.title, "Platform  PDF")
        self.assertEqual(
            extracted.text,
            "[PDF page 1] Housing for all\n\n[PDF page 2] Labor rights now",
        )
        self.assertTrue(extracted.paragraphs)
        self.assertEqual(extracted.paragraphs[0].locator, "paragraph 1")

    def test_pdf_errors_clearly_without_macos_pdfkit_fallback(self) -> None:
        capture = RawDocumentCapture(
            document_id="pdf-doc",
            source_url="https://example.org/platform.pdf",
            final_url="https://example.org/platform.pdf",
            retrieved_at="2026-08-19T17:00:00+00:00",
            content_type="application/pdf",
            encoding="utf-8",
            content_bytes=b"%PDF-1.7",
            byte_count=8,
            sha256="b" * 64,
        )

        with patch(
            "dsa_analysis.document_corpus._pdf_reader_class",
            side_effect=ExtractionError("PDF extraction requires the optional dependency 'pypdf'"),
        ), patch(
            "dsa_analysis.document_corpus.platform.system",
            return_value="Linux",
        ):
            with self.assertRaisesRegex(ExtractionError, "only available on macOS"):
                extract_document_text(capture)

        with patch(
            "dsa_analysis.document_corpus._pdf_reader_class",
            side_effect=ExtractionError("PDF extraction requires the optional dependency 'pypdf'"),
        ), patch(
            "dsa_analysis.document_corpus.platform.system",
            return_value="Darwin",
        ), patch(
            "dsa_analysis.document_corpus._swift_executable",
            return_value=None,
        ):
            with self.assertRaisesRegex(ExtractionError, "/usr/bin/swift"):
                extract_document_text(capture)

    def test_plain_text_sanitizes_control_characters(self) -> None:
        capture = RawDocumentCapture(
            document_id="text-doc",
            source_url="https://example.org/platform.txt",
            final_url="https://example.org/platform.txt",
            retrieved_at="2026-08-19T17:00:00+00:00",
            content_type="text/plain",
            encoding="utf-8",
            content_bytes=b"Housing\x00 for all.\n\nLabor\x0b rights now.",
            byte_count=37,
            sha256="c" * 64,
        )

        extracted = extract_document_text(capture)

        self.assertEqual(extracted.text, "Housing for all.\n\nLabor rights now.")

    def test_campaign_window_and_document_id_are_stable(self) -> None:
        document_id = candidate_document_id(
            "Zohran Mamdani",
            "nyc-mayor-primary-2025",
            "https://Example.org/issues#top",
            "campaign_issues",
        )

        self.assertEqual(
            document_id,
            candidate_document_id(
                "Zohran Mamdani",
                "nyc-mayor-primary-2025",
                "https://example.org/issues",
                "campaign_issues",
            ),
        )
        self.assertEqual(
            campaign_window_for_election("2025-06-24").start.isoformat(),
            "2024-01-01",
        )
        self.assertEqual(
            campaign_window_for_election("2025-06-24").end.isoformat(),
            "2025-06-24",
        )

    def test_canonical_inventory_dedupes_archive_and_tracking_urls(self) -> None:
        evidence_rows = [
            {
                "statement_key": "s1",
                "race_id": "race-1",
                "candidate_name": "Janeese Lewis George",
                "election_date": "2026-06-16",
                "role": "endorsed",
                "evidence_status": "verified",
                "source_url": (
                    "https://web.archive.org/web/20260301010101/"
                    "https://janeesefordc.com/platform/homes-for-all/?utm_source=email"
                ),
                "source_type": "archived_campaign_page",
                "locator": "Homes for All",
            },
            {
                "statement_key": "s2",
                "race_id": "race-1",
                "candidate_name": "Janeese Lewis George",
                "election_date": "2026-06-16",
                "role": "endorsed",
                "evidence_status": "verified",
                "source_url": "https://janeesefordc.com/platform/homes-for-all/#top",
                "source_type": "official_campaign_page",
                "locator": "Homes for All",
            },
            {
                "statement_key": "s3",
                "race_id": "race-1",
                "candidate_name": "Janeese Lewis George",
                "election_date": "2026-06-16",
                "role": "endorsed",
                "evidence_status": "verified",
                "source_url": "https://www.civilbeat.org/qa/janeese",
                "source_type": "candidate_questionnaire",
                "locator": "Question 5",
            },
        ]
        roster_rows = [
            {
                "queue_id": "q1",
                "race_id": "race-1",
                "candidate_name": "Janeese Lewis George",
                "role": "endorsed",
                "election_date": "2026-06-16",
                "official_election_source": "https://dc.gov/ballot?utm_medium=email",
            }
        ]

        inventory = build_candidate_source_inventory(evidence_rows, roster_rows)
        by_domain = {row["source_domain"]: row for row in inventory}

        self.assertEqual(len(inventory), 2)
        self.assertEqual(
            by_domain["civilbeat.org"]["source_url"],
            "https://www.civilbeat.org/qa/janeese",
        )
        self.assertEqual(
            by_domain["janeesefordc.com"]["source_url"],
            "https://janeesefordc.com/platform/homes-for-all",
        )
        self.assertEqual(
            canonical_source_url(evidence_rows[0]["source_url"]),
            "https://janeesefordc.com/platform/homes-for-all",
        )
        self.assertEqual(
            canonical_source_url("https://janeesefordc.com/news/post?share=twitter#top"),
            "https://janeesefordc.com/news/post",
        )
        self.assertEqual(
            by_domain["janeesefordc.com"]["archive_url"],
            normalize_source_url(evidence_rows[0]["source_url"]),
        )
        self.assertEqual(by_domain["janeesefordc.com"]["statement_count"], "2")
        self.assertEqual(by_domain["janeesefordc.com"]["campaign_domain"], "janeesefordc.com")
        self.assertEqual(by_domain["janeesefordc.com"]["source_type_class"], "campaign_page")
        self.assertEqual(by_domain["janeesefordc.com"]["legacy_locators"], "Homes for All")
        self.assertEqual(by_domain["civilbeat.org"]["legacy_locators"], "Question 5")

    def test_discovery_queue_seeds_campaign_domain_known_docs_and_roster_context(self) -> None:
        evidence_rows = [
            {
                "statement_key": "s1",
                "race_id": "race-1",
                "candidate_name": "Janeese Lewis George",
                "election_date": "2026-06-16",
                "role": "endorsed",
                "evidence_status": "verified",
                "source_url": "https://janeesefordc.com/platform/homes-for-all/",
                "source_type": "official_campaign_page",
                "locator": "Homes for All",
            }
        ]
        roster_rows = [
            {
                "queue_id": "q1",
                "race_id": "race-1",
                "candidate_name": "Janeese Lewis George",
                "role": "endorsed",
                "election_date": "2026-06-16",
                "official_election_source": "https://dc.gov/ballot?utm_medium=email",
            },
            {
                "queue_id": "q2",
                "race_id": "race-2",
                "candidate_name": "Taylor Example",
                "role": "opponent",
                "election_date": "2026-06-16",
                "official_election_source": "https://county.example/contest#top",
            },
        ]

        queue = build_candidate_document_discovery_queue(evidence_rows, roster_rows)
        janeese_rows = [row for row in queue if row["candidate_name"] == "Janeese Lewis George"]
        taylor_rows = [row for row in queue if row["candidate_name"] == "Taylor Example"]

        self.assertEqual(
            [row["seed_kind"] for row in janeese_rows],
            ["campaign_domain", "known_document", "official_election_source"],
        )
        self.assertEqual(janeese_rows[0]["seed_url"], "https://janeesefordc.com/")
        self.assertEqual(
            janeese_rows[1]["seed_url"],
            "https://janeesefordc.com/platform/homes-for-all/",
        )
        self.assertEqual(janeese_rows[1]["legacy_locators"], "Homes for All")
        self.assertEqual(
            janeese_rows[2]["seed_url"],
            "https://dc.gov/ballot",
        )
        self.assertEqual(taylor_rows[0]["seed_kind"], "official_election_source")
        self.assertEqual(taylor_rows[0]["seed_url"], "https://county.example/contest")

    def test_candidate_document_registry_rows_feed_inventory_and_discovery_queue(self) -> None:
        roster_rows = [
            {
                "queue_id": "q2016",
                "race_id": "race-2016",
                "candidate_name": "Jane Example",
                "role": "endorsed",
                "election_date": "2016-06-07",
                "official_election_source": "https://county.example/ballot",
            }
        ]
        candidate_document_rows = [
            {
                "source_record_id": "manual-1",
                "race_id": "race-2016",
                "candidate_name": "Jane Example",
                "role": "endorsed",
                "election_date": "2016-06-07",
                "verification_status": "verified",
                "publication_date": "2016-05-15",
                "effective_date": "2016-05-15",
                "source_tier": "1",
                "source_url": (
                    "https://web.archive.org/web/20160515000000/"
                    "https://janeexample.com/issues?share=twitter"
                ),
                "live_url": "https://janeexample.com/issues",
                "document_type": "campaign_page",
                "legacy_locator": "Issues",
                "analysis_scope": "analysis",
                "notes": "Archived platform page",
            }
        ]

        inventory = build_candidate_source_inventory(
            [],
            roster_rows,
            candidate_document_rows=candidate_document_rows,
        )
        queue = build_candidate_document_discovery_queue(
            [],
            roster_rows,
            candidate_document_rows=candidate_document_rows,
        )

        self.assertEqual(len(inventory), 1)
        self.assertEqual(
            inventory[0]["fetch_url"],
            candidate_document_rows[0]["source_url"],
        )
        self.assertEqual(inventory[0]["source_url"], "https://janeexample.com/issues")
        self.assertEqual(inventory[0]["archive_url"], candidate_document_rows[0]["source_url"])
        self.assertEqual(inventory[0]["live_url"], "https://janeexample.com/issues")
        self.assertEqual(inventory[0]["campaign_domain"], "janeexample.com")
        self.assertEqual(inventory[0]["publication_date"], "2016-05-15")
        self.assertEqual(inventory[0]["effective_date"], "2016-05-15")
        self.assertEqual(inventory[0]["source_tier"], "1")
        self.assertEqual(inventory[0]["analysis_scope"], "analysis")
        self.assertEqual(inventory[0]["legacy_locators"], "Issues")
        jane_rows = [row for row in queue if row["candidate_name"] == "Jane Example"]
        self.assertEqual(
            [row["seed_kind"] for row in jane_rows],
            ["campaign_domain", "known_document", "official_election_source"],
        )
        self.assertEqual(jane_rows[1]["seed_url"], candidate_document_rows[0]["source_url"])
        self.assertEqual(jane_rows[1]["legacy_locators"], "Issues")

    def test_campaign_domain_derivation_rejects_publisher_government_and_questionnaire_hosts(self) -> None:
        evidence_rows = [
            {
                "statement_key": "pub-1",
                "race_id": "race-pub",
                "candidate_name": "Alex Example",
                "election_date": "2024-06-04",
                "role": "endorsed",
                "evidence_status": "verified",
                "source_url": "https://blockclubchicago.org/2024/02/10/alex-example-questions",
                "source_type": "candidate_statement",
            },
            {
                "statement_key": "gov-1",
                "race_id": "race-gov",
                "candidate_name": "Casey Example",
                "election_date": "2024-06-04",
                "role": "endorsed",
                "evidence_status": "verified",
                "source_url": "https://cityofsacramento.gov/candidates/casey-example",
                "source_type": "official_candidate_statement",
            },
            {
                "statement_key": "q-1",
                "race_id": "race-q",
                "candidate_name": "Jordan Example",
                "election_date": "2024-06-04",
                "role": "opponent",
                "evidence_status": "verified",
                "source_url": "https://ballotready.org/jordan-example",
                "source_type": "campaign_platform | candidate_profile",
            },
            {
                "statement_key": "real-1",
                "race_id": "race-real",
                "candidate_name": "Taylor Example",
                "election_date": "2024-06-04",
                "role": "endorsed",
                "evidence_status": "verified",
                "source_url": "https://taylorexample.com/issues",
                "source_type": "official_campaign_issue_page",
            },
        ]
        roster_rows = [
            {
                "queue_id": "q-pub",
                "race_id": "race-pub",
                "candidate_name": "Alex Example",
                "role": "endorsed",
                "election_date": "2024-06-04",
            },
            {
                "queue_id": "q-gov",
                "race_id": "race-gov",
                "candidate_name": "Casey Example",
                "role": "endorsed",
                "election_date": "2024-06-04",
            },
            {
                "queue_id": "q-q",
                "race_id": "race-q",
                "candidate_name": "Jordan Example",
                "role": "opponent",
                "election_date": "2024-06-04",
            },
            {
                "queue_id": "q-real",
                "race_id": "race-real",
                "candidate_name": "Taylor Example",
                "role": "endorsed",
                "election_date": "2024-06-04",
            },
        ]
        candidate_document_rows = [
            {
                "source_record_id": "manual-party-1",
                "race_id": "race-manual",
                "candidate_name": "Robin Example",
                "role": "endorsed",
                "election_date": "2024-06-04",
                "verification_status": "verified",
                "source_url": "https://peoplesplatform.org/robin-example",
                "document_type": "campaign_page",
            }
        ]

        inventory = build_candidate_source_inventory(
            evidence_rows,
            roster_rows
            + [
                {
                    "queue_id": "q-manual",
                    "race_id": "race-manual",
                    "candidate_name": "Robin Example",
                    "role": "endorsed",
                    "election_date": "2024-06-04",
                }
            ],
            candidate_document_rows=candidate_document_rows,
        )
        by_candidate = {row["candidate_name"]: row for row in inventory}
        queue = build_candidate_document_discovery_queue(
            evidence_rows,
            roster_rows
            + [
                {
                    "queue_id": "q-manual",
                    "race_id": "race-manual",
                    "candidate_name": "Robin Example",
                    "role": "endorsed",
                    "election_date": "2024-06-04",
                }
            ],
            candidate_document_rows=candidate_document_rows,
        )

        self.assertEqual(by_candidate["Alex Example"]["campaign_domain"], "")
        self.assertEqual(by_candidate["Casey Example"]["campaign_domain"], "")
        self.assertEqual(by_candidate["Jordan Example"]["campaign_domain"], "")
        self.assertEqual(by_candidate["Taylor Example"]["campaign_domain"], "taylorexample.com")
        self.assertEqual(by_candidate["Robin Example"]["campaign_domain"], "peoplesplatform.org")
        queue_domains = {
            row["candidate_name"]: [entry["seed_kind"] for entry in queue if entry["candidate_name"] == row["candidate_name"]]
            for row in inventory
        }
        self.assertNotIn("campaign_domain", queue_domains["Alex Example"])
        self.assertNotIn("campaign_domain", queue_domains["Casey Example"])
        self.assertNotIn("campaign_domain", queue_domains["Jordan Example"])
        self.assertIn("campaign_domain", queue_domains["Taylor Example"])
        self.assertIn("campaign_domain", queue_domains["Robin Example"])

    def test_source_type_classification_is_deterministic(self) -> None:
        self.assertEqual(
            classify_source_type("candidate_questionnaire"),
            "questionnaire",
        )
        self.assertEqual(
            classify_source_type("", "https://example.org/issues/housing"),
            "policy_page",
        )
        self.assertEqual(
            classify_source_type("", "https://x.com/candidate/status/1"),
            "social_post",
        )
        self.assertNotIn("media_no_transcript", VERIFICATION_STATUSES)


class CampaignDomainDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree(SCRATCH_ROOT, ignore_errors=True)
        SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(SCRATCH_ROOT, ignore_errors=True))

    def test_run_campaign_domain_discovery_pass_discovers_live_and_archive_urls(self) -> None:
        root = SCRATCH_ROOT / "campaign_discovery"
        root.mkdir(parents=True, exist_ok=True)
        paths = CampaignDomainDiscoveryPaths(
            queue_path=root / "candidate_document_queue.csv",
            status_path=root / "candidate_campaign_domain_discovery_status.csv",
            discovered_url_path=root / "candidate_campaign_domain_discovered_urls.csv",
        )
        self._write_csv(
            paths.queue_path,
            [
                {
                    "document_id": "seed-1",
                    "queue_id": "q-1",
                    "race_id": "race-1",
                    "candidate_slug": "casey-example",
                    "candidate_name": "Casey Example",
                    "role": "endorsed",
                    "election_date": "2022-06-07",
                    "source_type": "campaign_page",
                    "source_type_class": "campaign_page",
                    "source_url": "https://caseyexample.com/",
                    "campaign_domain": "caseyexample.com",
                    "seed_kinds": "campaign_domain",
                    "seed_priority": "1",
                    "known_source_count": "1",
                    "legacy_statement_count": "3",
                },
                {
                    "document_id": "known-issues",
                    "queue_id": "q-1",
                    "race_id": "race-1",
                    "candidate_slug": "casey-example",
                    "candidate_name": "Casey Example",
                    "role": "endorsed",
                    "election_date": "2022-06-07",
                    "source_type": "policy_page",
                    "source_type_class": "policy_page",
                    "source_url": "https://caseyexample.com/issues",
                    "campaign_domain": "caseyexample.com",
                    "seed_kinds": "known_document",
                    "seed_priority": "2",
                    "known_source_count": "1",
                    "legacy_statement_count": "3",
                },
            ],
        )

        def fetcher(url: str) -> dict[str, str]:
            responses = {
                "https://caseyexample.com/": {
                    "ok": "true",
                    "text": (
                        '<html><body><a href="/issues">Issues</a>'
                        '<a href="/news/release-1">Release</a>'
                        '<a href="/privacy-policy">Privacy</a></body></html>'
                    ),
                    "final_url": "https://caseyexample.com/",
                    "retrieved_at": "2024-01-01T00:00:00+00:00",
                    "error": "",
                },
                "https://caseyexample.com/sitemap.xml": {
                    "ok": "true",
                    "text": (
                        "<urlset>"
                        "<url><loc>https://caseyexample.com/questionnaire</loc>"
                        "<lastmod>2022-03-02</lastmod></url>"
                        "<url><loc>https://caseyexample.com/news-sitemap.xml</loc></url>"
                        "</urlset>"
                    ),
                    "final_url": "https://caseyexample.com/sitemap.xml",
                    "retrieved_at": "2024-01-01T00:00:00+00:00",
                    "error": "",
                },
                "https://caseyexample.com/news-sitemap.xml": {
                    "ok": "true",
                    "text": (
                        "<urlset>"
                        "<url><loc>https://caseyexample.com/speeches/remarks.pdf</loc>"
                        "<lastmod>2022-02-01</lastmod></url>"
                        "</urlset>"
                    ),
                    "final_url": "https://caseyexample.com/news-sitemap.xml",
                    "retrieved_at": "2024-01-01T00:00:00+00:00",
                    "error": "",
                },
                "https://caseyexample.com/sitemap_index.xml": {
                    "ok": "false",
                    "text": "",
                    "final_url": "",
                    "retrieved_at": "2024-01-01T00:00:00+00:00",
                    "error": "404",
                },
                "https://caseyexample.com/wp-sitemap.xml": {
                    "ok": "false",
                    "text": "",
                    "final_url": "",
                    "retrieved_at": "2024-01-01T00:00:00+00:00",
                    "error": "404",
                },
                "https://caseyexample.com/feed": {
                    "ok": "true",
                    "text": (
                        "<rss><channel><item><link>https://caseyexample.com/statements/update</link>"
                        "<pubDate>2022-02-12</pubDate></item></channel></rss>"
                    ),
                    "final_url": "https://caseyexample.com/feed",
                    "retrieved_at": "2024-01-01T00:00:00+00:00",
                    "error": "",
                },
                "https://caseyexample.com/rss.xml": {
                    "ok": "false",
                    "text": "",
                    "final_url": "",
                    "retrieved_at": "2024-01-01T00:00:00+00:00",
                    "error": "404",
                },
                "https://caseyexample.com/atom.xml": {
                    "ok": "false",
                    "text": "",
                    "final_url": "",
                    "retrieved_at": "2024-01-01T00:00:00+00:00",
                    "error": "404",
                },
                "https://caseyexample.com/news/release-1": {
                    "ok": "true",
                    "text": (
                        '<html><body><a href="/policy/clean-energy">Policy</a></body></html>'
                    ),
                    "final_url": "https://caseyexample.com/news/release-1",
                    "retrieved_at": "2024-01-01T00:00:00+00:00",
                    "error": "",
                },
                "https://caseyexample.com/issues": {
                    "ok": "true",
                    "text": "<html><body>Issues</body></html>",
                    "final_url": "https://caseyexample.com/issues",
                    "retrieved_at": "2024-01-01T00:00:00+00:00",
                    "error": "",
                },
                "https://caseyexample.com/questionnaire": {
                    "ok": "true",
                    "text": "<html><body>Questionnaire</body></html>",
                    "final_url": "https://caseyexample.com/questionnaire",
                    "retrieved_at": "2024-01-01T00:00:00+00:00",
                    "error": "",
                },
                "https://caseyexample.com/statements/update": {
                    "ok": "true",
                    "text": "<html><body>Statement</body></html>",
                    "final_url": "https://caseyexample.com/statements/update",
                    "retrieved_at": "2024-01-01T00:00:00+00:00",
                    "error": "",
                },
            }
            return responses[url]

        def cdx_fetcher(domain, start_date, end_date, limit):
            self.assertEqual(domain, "caseyexample.com")
            self.assertEqual(start_date.isoformat(), "2021-01-01")
            self.assertEqual(end_date.isoformat(), "2022-06-07")
            self.assertEqual(limit, 25)
            return [
                {
                    "timestamp": "20220315010101",
                    "original": "https://caseyexample.com/issues",
                },
                {
                    "timestamp": "20220404040404",
                    "original": "https://caseyexample.com/news/archive-release",
                },
            ]

        result = run_campaign_domain_discovery_pass(
            paths,
            max_domains=1,
            max_live_pages=3,
            max_urls_per_stage=10,
            wayback_limit=25,
            fetcher=fetcher,
            cdx_fetcher=cdx_fetcher,
        )

        self.assertEqual(result.queued_domains, 1)
        self.assertEqual(result.searched_domains, 1)
        self.assertEqual(result.appended_queue_rows, 6)
        self.assertEqual(result.discovered_urls, 8)
        queue_rows = self._read_csv(paths.queue_path)
        issues_row = next(row for row in queue_rows if row["source_url"] == "https://caseyexample.com/issues")
        self.assertEqual(
            issues_row["seed_kinds"],
            "known_document | campaign_archive_discovery | campaign_live_discovery",
        )
        self.assertEqual(
            issues_row["archive_url"],
            "https://web.archive.org/web/20220315010101/https://caseyexample.com/issues",
        )
        self.assertIn(
            "https://caseyexample.com/news/archive-release",
            {row["source_url"] for row in queue_rows},
        )
        self.assertNotIn(
            "https://caseyexample.com/privacy-policy",
            {row["source_url"] for row in queue_rows},
        )
        discovered_rows = self._read_csv(paths.discovered_url_path)
        self.assertEqual(len(discovered_rows), 8)
        self.assertIn(
            "https://caseyexample.com/sitemap.xml",
            {row["discovery_provenance_url"] for row in discovered_rows},
        )
        status_rows = self._read_csv(paths.status_path)
        self.assertEqual(status_rows[0]["live_search_status"], "complete")
        self.assertEqual(status_rows[0]["archive_search_status"], "complete")

    def test_run_campaign_domain_discovery_pass_skips_non_candidate_domains(self) -> None:
        root = SCRATCH_ROOT / "campaign_discovery_skip"
        root.mkdir(parents=True, exist_ok=True)
        paths = CampaignDomainDiscoveryPaths(
            queue_path=root / "candidate_document_queue.csv",
            status_path=root / "candidate_campaign_domain_discovery_status.csv",
            discovered_url_path=root / "candidate_campaign_domain_discovered_urls.csv",
        )
        self._write_csv(
            paths.queue_path,
            [
                {
                    "document_id": "seed-1",
                    "queue_id": "q-1",
                    "race_id": "race-1",
                    "candidate_slug": "casey-example",
                    "candidate_name": "Casey Example",
                    "role": "endorsed",
                    "election_date": "2022-06-07",
                    "source_url": "https://regionalpaper.com/",
                    "campaign_domain": "regionalpaper.com",
                    "seed_kinds": "campaign_domain",
                }
            ],
        )

        result = run_campaign_domain_discovery_pass(
            paths,
            fetcher=lambda url: (_ for _ in ()).throw(AssertionError("should not fetch")),
            cdx_fetcher=lambda domain, start_date, end_date, limit: (_ for _ in ()).throw(
                AssertionError("should not query wayback")
            ),
        )

        self.assertEqual(result.queued_domains, 0)
        self.assertEqual(result.searched_domains, 0)
        self.assertEqual(result.appended_queue_rows, 0)
        self.assertEqual(result.remaining_domains, 0)
        self.assertEqual(self._read_csv(paths.status_path), [])

    def test_run_campaign_domain_discovery_pass_is_resumable(self) -> None:
        root = SCRATCH_ROOT / "campaign_discovery_resume"
        root.mkdir(parents=True, exist_ok=True)
        paths = CampaignDomainDiscoveryPaths(
            queue_path=root / "candidate_document_queue.csv",
            status_path=root / "candidate_campaign_domain_discovery_status.csv",
            discovered_url_path=root / "candidate_campaign_domain_discovered_urls.csv",
        )
        self._write_csv(
            paths.queue_path,
            [
                {
                    "document_id": "seed-1",
                    "queue_id": "q-1",
                    "race_id": "race-1",
                    "candidate_slug": "casey-example",
                    "candidate_name": "Casey Example",
                    "role": "endorsed",
                    "election_date": "2022-06-07",
                    "source_type": "campaign_page",
                    "source_type_class": "campaign_page",
                    "source_url": "https://caseyexample.com/",
                    "campaign_domain": "caseyexample.com",
                    "seed_kinds": "campaign_domain",
                }
            ],
        )
        calls = {"fetch": 0, "cdx": 0}

        def fetcher(url: str) -> dict[str, str]:
            calls["fetch"] += 1
            return {
                "ok": "true",
                "text": "<html><body><a href='/issues'>Issues</a></body></html>",
                "final_url": url,
                "retrieved_at": "2024-01-01T00:00:00+00:00",
                "error": "",
            }

        def cdx_fetcher(domain, start_date, end_date, limit):
            calls["cdx"] += 1
            return []

        run_campaign_domain_discovery_pass(
            paths,
            max_domains=1,
            fetcher=fetcher,
            cdx_fetcher=cdx_fetcher,
        )
        rerun = run_campaign_domain_discovery_pass(
            paths,
            max_domains=1,
            fetcher=lambda url: (_ for _ in ()).throw(AssertionError("already complete")),
            cdx_fetcher=lambda domain, start_date, end_date, limit: (_ for _ in ()).throw(
                AssertionError("already complete")
            ),
        )

        self.assertEqual(calls["fetch"], 8)
        self.assertEqual(calls["cdx"], 1)
        self.assertEqual(rerun.searched_domains, 0)
        self.assertEqual(rerun.remaining_domains, 0)

    def test_run_campaign_domain_discovery_pass_retries_transient_live_failure_once(self) -> None:
        root = SCRATCH_ROOT / "campaign_discovery_transient"
        root.mkdir(parents=True, exist_ok=True)
        paths = CampaignDomainDiscoveryPaths(
            queue_path=root / "candidate_document_queue.csv",
            status_path=root / "candidate_campaign_domain_discovery_status.csv",
            discovered_url_path=root / "candidate_campaign_domain_discovered_urls.csv",
        )
        self._write_csv(
            paths.queue_path,
            [
                {
                    "document_id": "seed-1",
                    "queue_id": "q-1",
                    "race_id": "race-1",
                    "candidate_slug": "casey-example",
                    "candidate_name": "Casey Example",
                    "role": "endorsed",
                    "election_date": "2022-06-07",
                    "source_type": "campaign_page",
                    "source_type_class": "campaign_page",
                    "source_url": "https://caseyexample.com/",
                    "campaign_domain": "caseyexample.com",
                    "seed_kinds": "campaign_domain",
                }
            ],
        )
        calls = {"homepage": 0}

        def fetcher(url: str) -> dict[str, str]:
            if url == "https://caseyexample.com/":
                calls["homepage"] += 1
                if calls["homepage"] == 1:
                    return {
                        "ok": "false",
                        "text": "",
                        "final_url": "",
                        "retrieved_at": "2024-01-01T00:00:00+00:00",
                        "error": "URLError: timed out",
                    }
            elif calls["homepage"] <= 1:
                return {
                    "ok": "false",
                    "text": "",
                    "final_url": "",
                    "retrieved_at": "2024-01-01T00:00:00+00:00",
                    "error": "URLError: timed out",
                }
            return {
                "ok": "true",
                "text": "<html><body><a href='/issues'>Issues</a></body></html>",
                "final_url": url,
                "retrieved_at": "2024-01-01T00:00:00+00:00",
                "error": "",
            }

        result = run_campaign_domain_discovery_pass(
            paths,
            max_domains=1,
            fetcher=fetcher,
            cdx_fetcher=lambda domain, start_date, end_date, limit: [],
        )

        self.assertEqual(calls["homepage"], 2)
        self.assertEqual(result.remaining_domains, 0)
        status_row = self._read_csv(paths.status_path)[0]
        self.assertEqual(status_row["live_search_status"], "complete")
        self.assertEqual(status_row["live_retry_count"], "1")

    def test_run_campaign_domain_discovery_pass_retries_existing_transient_error_once(self) -> None:
        root = SCRATCH_ROOT / "campaign_discovery_retry_existing"
        root.mkdir(parents=True, exist_ok=True)
        paths = CampaignDomainDiscoveryPaths(
            queue_path=root / "candidate_document_queue.csv",
            status_path=root / "candidate_campaign_domain_discovery_status.csv",
            discovered_url_path=root / "candidate_campaign_domain_discovered_urls.csv",
        )
        self._write_csv(
            paths.queue_path,
            [
                {
                    "document_id": "seed-1",
                    "queue_id": "q-1",
                    "race_id": "race-1",
                    "candidate_slug": "casey-example",
                    "candidate_name": "Casey Example",
                    "role": "endorsed",
                    "election_date": "2022-06-07",
                    "source_type": "campaign_page",
                    "source_type_class": "campaign_page",
                    "source_url": "https://caseyexample.com/",
                    "campaign_domain": "caseyexample.com",
                    "seed_kinds": "campaign_domain",
                }
            ],
        )
        self._write_csv(
            paths.status_path,
            [
                {
                    "discovery_seed_id": stable_hash(
                        "race-1",
                        "Casey Example",
                        "endorsed",
                        "campaign_domain",
                        "https://caseyexample.com/",
                    ),
                    "queue_id": "q-1",
                    "race_id": "race-1",
                    "candidate_slug": "casey-example",
                    "candidate_name": "Casey Example",
                    "role": "endorsed",
                    "election_date": "2022-06-07",
                    "campaign_domain": "caseyexample.com",
                    "known_source_count": "0",
                    "legacy_statement_count": "0",
                    "live_search_status": "error",
                    "live_searched_at": "2024-01-01T00:00:00+00:00",
                    "live_error": "URLError: timed out",
                    "live_retry_count": "0",
                    "archive_search_status": "complete",
                    "archive_searched_at": "2024-01-01T00:00:00+00:00",
                    "archive_error": "",
                    "archive_retry_count": "0",
                }
            ],
        )
        calls = {"homepage": 0}

        def fetcher(url: str) -> dict[str, str]:
            calls["homepage"] += 1
            return {
                "ok": "false",
                "text": "",
                "final_url": "",
                "retrieved_at": "2024-01-01T00:00:00+00:00",
                "error": "URLError: timed out",
            }

        first = run_campaign_domain_discovery_pass(
            paths,
            max_domains=1,
            fetcher=fetcher,
            cdx_fetcher=lambda domain, start_date, end_date, limit: [],
        )
        second = run_campaign_domain_discovery_pass(
            paths,
            max_domains=1,
            fetcher=lambda url: (_ for _ in ()).throw(AssertionError("retry already used")),
            cdx_fetcher=lambda domain, start_date, end_date, limit: [],
        )

        self.assertGreater(calls["homepage"], 0)
        self.assertEqual(first.searched_domains, 1)
        self.assertEqual(second.searched_domains, 0)
        status_row = self._read_csv(paths.status_path)[0]
        self.assertEqual(status_row["live_search_status"], "error")
        self.assertEqual(status_row["live_retry_count"], "1")

    def test_run_campaign_domain_discovery_pass_prefers_unsearched_domains_over_duplicate_domains(self) -> None:
        root = SCRATCH_ROOT / "campaign_discovery_breadth"
        root.mkdir(parents=True, exist_ok=True)
        paths = CampaignDomainDiscoveryPaths(
            queue_path=root / "candidate_document_queue.csv",
            status_path=root / "candidate_campaign_domain_discovery_status.csv",
            discovered_url_path=root / "candidate_campaign_domain_discovered_urls.csv",
        )
        self._write_csv(
            paths.queue_path,
            [
                {
                    "document_id": "seed-1",
                    "queue_id": "q-1",
                    "race_id": "race-1",
                    "candidate_slug": "casey-example",
                    "candidate_name": "Casey Example",
                    "role": "endorsed",
                    "election_date": "2022-06-07",
                    "source_type": "campaign_page",
                    "source_type_class": "campaign_page",
                    "source_url": "https://caseyexample.com/",
                    "campaign_domain": "caseyexample.com",
                    "seed_kinds": "campaign_domain",
                },
                {
                    "document_id": "seed-1b",
                    "queue_id": "q-1b",
                    "race_id": "race-1b",
                    "candidate_slug": "casey-example-jr",
                    "candidate_name": "Casey Example Jr.",
                    "role": "opponent",
                    "election_date": "2024-06-04",
                    "source_type": "campaign_page",
                    "source_type_class": "campaign_page",
                    "source_url": "https://caseyexample.com/platform",
                    "campaign_domain": "caseyexample.com",
                    "seed_kinds": "campaign_domain",
                },
                {
                    "document_id": "seed-2",
                    "queue_id": "q-2",
                    "race_id": "race-2",
                    "candidate_slug": "taylor-example",
                    "candidate_name": "Taylor Example",
                    "role": "endorsed",
                    "election_date": "2022-06-07",
                    "source_type": "campaign_page",
                    "source_type_class": "campaign_page",
                    "source_url": "https://taylorexample.com/",
                    "campaign_domain": "taylorexample.com",
                    "seed_kinds": "campaign_domain",
                },
            ],
        )
        fetched = []

        def fetcher(url: str) -> dict[str, str]:
            fetched.append(url)
            return {
                "ok": "true",
                "text": "<html><body><a href='/issues'>Issues</a></body></html>",
                "final_url": url,
                "retrieved_at": "2024-01-01T00:00:00+00:00",
                "error": "",
            }

        run_campaign_domain_discovery_pass(
            paths,
            max_domains=1,
            fetcher=fetcher,
            cdx_fetcher=lambda domain, start_date, end_date, limit: [],
        )
        run_campaign_domain_discovery_pass(
            paths,
            max_domains=1,
            fetcher=fetcher,
            cdx_fetcher=lambda domain, start_date, end_date, limit: [],
        )

        self.assertTrue(any(url.startswith("https://caseyexample.com/") for url in fetched))
        self.assertTrue(any(url.startswith("https://taylorexample.com/") for url in fetched))
        self.assertEqual(self._read_csv(paths.status_path)[0]["campaign_domain"], "caseyexample.com")
        self.assertEqual(self._read_csv(paths.status_path)[1]["campaign_domain"], "taylorexample.com")

    def _write_csv(self, path: Path, rows: list[dict[str, str]]) -> None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))


class DocumentCorpusBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree(SCRATCH_ROOT, ignore_errors=True)
        SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(SCRATCH_ROOT, ignore_errors=True))

    def test_analysis_segments_merge_fragments_split_long_paragraphs_and_flag_duplicates(self) -> None:
        document_id = "analysis-doc"
        text = (
            "Jobs now.\n\n"
            "We will build social housing at scale for working families across every ward. "
            "We will fund public transit, school modernization, and resilient public power. "
            "We will protect tenants through rent stabilization and right-to-counsel.\n\n"
            "Paid for by Example for City Council.\n\n"
            "Paid for by Example for City Council."
        )
        paragraphs, sentences = self._segments(document_id, text)

        segments = build_analysis_segments(
            candidate_name="Casey Example",
            race_id="race-1",
            role="endorsed",
            document_id=document_id,
            paragraphs=paragraphs,
            sentences=sentences,
            source_type="campaign_page",
            config=AnalysisSegmentConfig(min_tokens=5, max_tokens=14, near_duplicate_min_tokens=3),
        )

        self.assertEqual(segments[0].analysis_kind, "merged")
        self.assertEqual(segments[0].locator, "paragraph 1 -> paragraph 2 sentence 1")
        self.assertEqual(segments[0].candidate_name, "Casey Example")
        self.assertEqual(segments[0].role, "endorsed")
        self.assertEqual(segments[1].analysis_kind, "sentence_window")
        self.assertEqual(segments[3].exact_duplicate_flag, True)
        self.assertEqual(segments[4].exact_duplicate_count, 2)
        self.assertEqual(segments[3].boilerplate_flag, True)
        self.assertIn("phrase:paid for by", segments[3].boilerplate_reasons)
        self.assertEqual(segments[3].text, "Paid for by Example for City Council.")

    def test_segment_review_sample_is_deterministic(self) -> None:
        paragraphs, sentences = self._segments(
            "review-a",
            (
                "Public schools first and public housing now.\n\n"
                "Public housing now and public schools first.\n\n"
                "Paid for by Example Committee."
            ),
        )
        config = AnalysisSegmentConfig(min_tokens=2, max_tokens=6, near_duplicate_min_tokens=2)
        segments = build_analysis_segments(
            candidate_name="Casey Example",
            race_id="race-1",
            role="endorsed",
            document_id="review-a",
            paragraphs=paragraphs,
            sentences=sentences,
            source_type="campaign_page",
            config=config,
        )

        sample = build_analysis_segment_review_sample(segments, sample_size=4)

        self.assertEqual(len(sample), 3)
        self.assertEqual(sample[0]["review_bucket"], "boilerplate")
        self.assertEqual(sample[1]["review_bucket"], "near_duplicate")
        self.assertEqual(sample[0]["document_id"], "review-a")
        self.assertEqual(sample[1]["locator"], "paragraph 1")

    def test_run_candidate_document_extraction_batch_fetches_and_writes_outputs(self) -> None:
        root = self._scenario_root("fetch_success")
        paths = self._paths(root)
        capture = self._capture(
            document_id="ignored",
            source_url="https://example.org/platform",
            content_type="text/html",
            body=(
                b"<html><head><title>Platform</title></head><body>"
                b"<p>Public housing now.</p><p>Public schools forever.</p>"
                b"</body></html>"
            ),
        )
        queue_rows = [
            {
                "queue_id": "q1",
                "race_id": "race-1",
                "candidate_name": "Casey Example",
                "role": "endorsed",
                "election_date": "2026-06-16",
                "publication_date": "2026-02-01",
                "source_type": "campaign_page",
                "source_url": "https://example.org/platform",
                "notes": "platform",
            }
        ]

        def fetcher(document_id: str, source_url: str) -> RawDocumentCapture:
            self.assertEqual(source_url, "https://example.org/platform")
            return RawDocumentCapture(
                document_id=document_id,
                source_url=capture.source_url,
                final_url=capture.final_url,
                retrieved_at=capture.retrieved_at,
                content_type=capture.content_type,
                encoding=capture.encoding,
                content_bytes=capture.content_bytes,
                byte_count=capture.byte_count,
                sha256=capture.sha256,
            )

        result = run_candidate_document_extraction_batch(
            queue_rows,
            paths,
            fetcher=fetcher,
            analysis_config=AnalysisSegmentConfig(min_tokens=2, max_tokens=6),
        )

        self.assertEqual(result.processed_documents, 1)
        self.assertEqual(result.fetched_documents, 1)
        self.assertEqual(result.reused_raw_documents, 0)
        metadata_rows = self._read_csv(paths.metadata_path)
        self.assertEqual(metadata_rows[0]["fetch_status"], "fetched")
        self.assertEqual(metadata_rows[0]["extractor"], "html")
        full_text_rows = self._read_jsonl(paths.full_text_path)
        self.assertEqual(full_text_rows[0]["text"], "Public housing now.\n\nPublic schools forever.")
        manifest_rows = self._read_jsonl(paths.raw_manifest_path)
        self.assertEqual(manifest_rows[0]["sha256"], capture.sha256)
        analysis_rows = self._read_csv(paths.analysis_segment_path)
        self.assertEqual(analysis_rows[0]["candidate_name"], "Casey Example")
        self.assertEqual(analysis_rows[0]["locator"], "paragraph 1")
        self.assertTrue((Path(__file__).resolve().parents[1] / manifest_rows[0]["raw_path"]).exists())

    def test_run_candidate_document_extraction_batch_reuses_persisted_raw(self) -> None:
        root = self._scenario_root("resume_raw")
        paths = self._paths(root)
        queue_rows = [
            {
                "queue_id": "q2",
                "race_id": "race-2",
                "candidate_name": "Taylor Example",
                "role": "opponent",
                "election_date": "2026-06-16",
                "source_type": "campaign_page",
                "source_url": "https://example.org/reuse",
            }
        ]
        document_id = candidate_document_id(
            "Taylor Example",
            "race-2",
            "https://example.org/reuse",
            "campaign_page",
        )
        capture = self._capture(
            document_id=document_id,
            source_url="https://example.org/reuse",
            content_type="text/plain",
            body=b"Persisted raw text.",
        )
        raw_path = persist_raw_document(capture, paths.raw_dir)
        paths.raw_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        paths.raw_manifest_path.write_text(
            json.dumps(
                {
                    "document_id": document_id,
                    "source_url": capture.source_url,
                    "final_url": capture.final_url,
                    "retrieved_at": capture.retrieved_at,
                    "content_type": capture.content_type,
                    "encoding": capture.encoding,
                    "byte_count": str(capture.byte_count),
                    "sha256": capture.sha256,
                    "raw_path": str(raw_path.relative_to(Path(__file__).resolve().parents[1])),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        called = False

        def fetcher(document_id: str, source_url: str) -> RawDocumentCapture:
            nonlocal called
            called = True
            raise AssertionError("fetcher should not be called when raw is already persisted")

        result = run_candidate_document_extraction_batch(queue_rows, paths, fetcher=fetcher)

        self.assertFalse(called)
        self.assertEqual(result.reused_raw_documents, 1)
        self.assertEqual(result.fetched_documents, 0)
        self.assertEqual(len(self._read_jsonl(paths.raw_manifest_path)), 1)
        self.assertEqual(self._read_csv(paths.metadata_path)[0]["fetch_status"], "reused_raw")

    def test_run_candidate_document_extraction_batch_reuses_raw_across_document_ids(self) -> None:
        root = self._scenario_root("shared_url_raw")
        paths = self._paths(root)
        shared_url = (
            "https://cdn.example.org/voter-guide.pdf?utm_source=email"
        )
        queue_rows = [
            {
                "queue_id": "q-shared-1",
                "race_id": "race-1",
                "candidate_name": "Alex Example",
                "role": "endorsed",
                "election_date": "2017-11-07",
                "source_type": "voter_guide",
                "source_url": shared_url,
            },
            {
                "queue_id": "q-shared-2",
                "race_id": "race-1",
                "candidate_name": "Blair Example",
                "role": "opponent",
                "election_date": "2017-11-07",
                "source_type": "voter_guide",
                "source_url": "https://cdn.example.org/voter-guide.pdf",
            },
        ]
        fetch_calls: list[tuple[str, str]] = []

        def fetcher(document_id: str, source_url: str) -> RawDocumentCapture:
            fetch_calls.append((document_id, source_url))
            return self._capture(
                document_id=document_id,
                source_url=source_url,
                content_type="text/plain",
                body=b"Shared voter guide text.",
            )

        result = run_candidate_document_extraction_batch(queue_rows, paths, fetcher=fetcher)

        self.assertEqual(result.fetched_documents, 1)
        self.assertEqual(result.reused_raw_documents, 1)
        self.assertEqual(len(fetch_calls), 1)
        metadata_rows = {row["candidate_name"]: row for row in self._read_csv(paths.metadata_path)}
        self.assertEqual(metadata_rows["Alex Example"]["fetch_status"], "fetched")
        self.assertEqual(metadata_rows["Blair Example"]["fetch_status"], "reused_raw")
        self.assertEqual(metadata_rows["Alex Example"]["raw_path"], metadata_rows["Blair Example"]["raw_path"])
        self.assertEqual(len(self._read_jsonl(paths.raw_manifest_path)), 1)

    def test_archive_source_does_not_reuse_live_interstitial_raw(self) -> None:
        root = self._scenario_root("archive_replaces_live")
        paths = self._paths(root)
        live_url = "https://example.org/platform"
        archive_url = (
            "https://web.archive.org/web/20200101000000id_/"
            "https://example.org/platform"
        )
        fetch_calls: list[str] = []

        def fetcher(document_id: str, source_url: str) -> RawDocumentCapture:
            fetch_calls.append(source_url)
            body = (
                b"<html><body><p>Archived substantive platform text.</p></body></html>"
                if source_url == archive_url
                else b"<html><head><meta http-equiv='refresh' content='0'></head></html>"
            )
            return self._capture(
                document_id=document_id,
                source_url=source_url,
                content_type="text/html",
                body=body,
            )

        run_candidate_document_extraction_batch(
            [
                {
                    "queue_id": "q-live",
                    "race_id": "race-1",
                    "candidate_name": "Alex Example",
                    "role": "endorsed",
                    "election_date": "2020-06-16",
                    "source_type": "campaign_page",
                    "source_url": live_url,
                }
            ],
            paths,
            fetcher=fetcher,
        )
        result = run_candidate_document_extraction_batch(
            [
                {
                    "queue_id": "q-archive",
                    "race_id": "race-1",
                    "candidate_name": "Alex Example",
                    "role": "endorsed",
                    "election_date": "2020-06-16",
                    "source_type": "campaign_page",
                    "source_url": archive_url,
                }
            ],
            paths,
            fetcher=fetcher,
        )

        self.assertEqual(fetch_calls, [live_url, archive_url])
        self.assertEqual(result.fetched_documents, 1)
        self.assertEqual(result.reused_raw_documents, 0)

    def test_reused_raw_preserves_archive_provenance(self) -> None:
        root = self._scenario_root("reuse_archive_provenance")
        paths = self._paths(root)
        queue_rows = [
            {
                "queue_id": "q-archive",
                "race_id": "race-archive",
                "candidate_name": "Archive Example",
                "role": "endorsed",
                "election_date": "2018-08-07",
                "source_type": "campaign_page",
                "source_url": "https://archive-example.org/platform",
                "archive_url": (
                    "https://web.archive.org/web/20180801000000/"
                    "https://archive-example.org/platform"
                ),
            }
        ]

        def archive_fetcher(document_id: str, source_url: str) -> RawDocumentCapture:
            if source_url == "https://archive-example.org/platform":
                raise RawFetchError("gone")
            return self._capture(
                document_id=document_id,
                source_url=source_url,
                content_type="text/html",
                body=b"<html><body><p>Archived platform text.</p></body></html>",
            )

        run_candidate_document_extraction_batch(queue_rows, paths, fetcher=archive_fetcher)
        run_candidate_document_extraction_batch(
            [
                {
                    **queue_rows[0],
                    "archive_url": "",
                }
            ],
            paths,
            fetcher=lambda document_id, source_url: (_ for _ in ()).throw(
                AssertionError("raw bytes should be reused")
            ),
        )

        metadata_row = self._read_csv(paths.metadata_path)[0]
        manifest_row = self._read_jsonl(paths.raw_manifest_path)[0]
        archive_url = (
            "https://web.archive.org/web/20180801000000/"
            "https://archive-example.org/platform"
        )
        self.assertEqual(metadata_row["fetch_status"], "reused_raw")
        self.assertEqual(metadata_row["source_url"], "https://archive-example.org/platform")
        self.assertEqual(metadata_row["archive_url"], archive_url)
        self.assertEqual(metadata_row["final_url"], archive_url)
        self.assertEqual(manifest_row["archive_url"], archive_url)

    def test_run_candidate_document_extraction_batch_falls_back_to_archive_url(self) -> None:
        root = self._scenario_root("archive_fallback")
        paths = self._paths(root)
        queue_rows = [
            {
                "queue_id": "q-archive",
                "race_id": "race-archive",
                "candidate_name": "Archive Example",
                "role": "endorsed",
                "election_date": "2018-08-07",
                "source_type": "campaign_page",
                "source_url": "https://archive-example.org/platform",
                "archive_url": (
                    "https://web.archive.org/web/20180801000000/"
                    "https://archive-example.org/platform"
                ),
            }
        ]
        calls: list[str] = []

        def fetcher(document_id: str, source_url: str) -> RawDocumentCapture:
            calls.append(source_url)
            if source_url == "https://archive-example.org/platform":
                raise RawFetchError("gone")
            return self._capture(
                document_id=document_id,
                source_url=source_url,
                content_type="text/html",
                body=b"<html><body><p>Archived platform text.</p></body></html>",
            )

        result = run_candidate_document_extraction_batch(queue_rows, paths, fetcher=fetcher)

        self.assertEqual(result.successful_documents, 1)
        self.assertEqual(
            calls,
            [
                "https://archive-example.org/platform",
                "https://web.archive.org/web/20180801000000/https://archive-example.org/platform",
            ],
        )
        metadata_row = self._read_csv(paths.metadata_path)[0]
        self.assertEqual(metadata_row["source_url"], "https://archive-example.org/platform")
        self.assertEqual(
            metadata_row["final_url"],
            "https://web.archive.org/web/20180801000000/https://archive-example.org/platform",
        )

    def test_build_candidate_document_regather_plan_keeps_metadata_only_rows_pending(self) -> None:
        root = self._scenario_root("regather_plan")
        paths = self._paths(root)
        queue_rows = [
            {
                "document_id": "doc-a",
                "race_id": "race-2018",
                "candidate_name": "Alex Example",
                "role": "endorsed",
                "election_date": "2018-08-07",
                "source_type": "voter_guide",
                "source_type_class": "voter_guide",
                "source_url": "https://cdn.example.org/guide.pdf?utm_source=email",
                "seed_kinds": "known_document",
                "seed_priority": "1",
                "legacy_statement_count": "2",
                "known_source_count": "1",
                "substantive_segment_count": "0",
            },
            {
                "document_id": "doc-b",
                "race_id": "race-2018",
                "candidate_name": "Blair Example",
                "role": "opponent",
                "election_date": "2018-08-07",
                "source_type": "voter_guide",
                "source_type_class": "voter_guide",
                "source_url": "https://cdn.example.org/guide.pdf",
                "seed_kinds": "known_document",
                "seed_priority": "1",
                "legacy_statement_count": "1",
                "known_source_count": "1",
                "substantive_segment_count": "0",
            },
            {
                "document_id": "doc-video",
                "race_id": "race-2018",
                "candidate_name": "Video Example",
                "role": "endorsed",
                "election_date": "2018-08-07",
                "source_type": "video",
                "source_type_class": "video",
                "source_url": "https://example.org/watch",
                "seed_kinds": "known_document",
                "seed_priority": "1",
                "legacy_statement_count": "1",
                "known_source_count": "1",
                "substantive_segment_count": "0",
                "transcript_text": "",
            },
            {
                "document_id": "doc-2016",
                "race_id": "race-2016",
                "candidate_name": "Casey Example",
                "role": "endorsed",
                "election_date": "2016-05-10",
                "source_type": "campaign_page",
                "source_type_class": "campaign_page",
                "source_url": "https://casey.example/platform",
                "seed_kinds": "campaign_domain",
                "seed_priority": "3",
                "legacy_statement_count": "0",
                "known_source_count": "0",
                "substantive_segment_count": "0",
            },
        ]
        self._write_csv(
            paths.metadata_path,
            [
                {
                    "document_id": "doc-2016",
                    "queue_id": "",
                    "candidate_slug": "casey-example",
                    "candidate_name": "Casey Example",
                    "race_id": "race-2016",
                    "role": "endorsed",
                    "election_date": "2016-05-10",
                    "publication_date": "",
                    "campaign_window_start": "",
                    "campaign_window_end": "",
                    "campaign_window_status": "",
                    "source_type": "campaign_page",
                    "source_url": "https://casey.example/platform",
                    "archive_url": "",
                    "final_url": "https://casey.example/platform",
                    "retrieved_at": "",
                    "content_type": "text/html",
                    "title": "",
                    "coverage_status": "found_unverified",
                    "fetch_status": "fetched",
                    "extraction_status": "extracted",
                    "extractor": "html",
                    "raw_sha256": "x",
                    "text_sha256": "x",
                    "provenance_hash": "x",
                    "paragraph_count": "1",
                    "sentence_count": "1",
                    "raw_path": "",
                    "seed_kind": "",
                    "source_record_id": "",
                    "notes": "",
                    "error": "",
                }
            ],
        )

        plan = build_candidate_document_regather_plan(queue_rows, paths, limit=1)

        self.assertEqual(plan.selected_unique_urls, 1)
        self.assertEqual(plan.pending_documents, 3)
        self.assertEqual(plan.skipped_completed_documents, 0)
        self.assertEqual(plan.skipped_transcriptless_video_documents, 1)
        self.assertEqual([row["document_id"] for row in plan.queue_rows], ["doc-2016"])

    def test_regather_plan_requires_full_text_artifacts_not_metadata_alone(self) -> None:
        root = self._scenario_root("regather_metadata_only")
        paths = self._paths(root)
        queue_rows = [
            {
                "document_id": "doc-1",
                "race_id": "race-1",
                "candidate_name": "Alex Example",
                "role": "endorsed",
                "election_date": "2017-11-07",
                "source_type": "campaign_page",
                "source_type_class": "campaign_page",
                "source_url": "https://alex.example/platform",
                "seed_kinds": "known_document",
                "seed_priority": "1",
                "legacy_statement_count": "1",
                "known_source_count": "1",
                "substantive_segment_count": "0",
            }
        ]
        self._write_csv(
            paths.metadata_path,
            [
                {
                    "document_id": "doc-1",
                    "queue_id": "",
                    "candidate_slug": "alex-example",
                    "candidate_name": "Alex Example",
                    "race_id": "race-1",
                    "role": "endorsed",
                    "election_date": "2017-11-07",
                    "publication_date": "",
                    "campaign_window_start": "2016-01-01",
                    "campaign_window_end": "2017-11-07",
                    "campaign_window_status": "undated",
                    "source_type": "campaign_page",
                    "source_url": "https://alex.example/platform",
                    "archive_url": "",
                    "final_url": "https://alex.example/platform",
                    "retrieved_at": "",
                    "content_type": "text/html",
                    "title": "",
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
                }
            ],
        )

        plan = build_candidate_document_regather_plan(queue_rows, paths, limit=1)

        self.assertEqual(plan.skipped_completed_documents, 0)
        self.assertEqual(plan.pending_documents, 1)
        self.assertEqual([row["document_id"] for row in plan.queue_rows], ["doc-1"])

    def test_build_candidate_document_regather_plan_prioritizes_one_sided_race_gaps(self) -> None:
        root = self._scenario_root("regather_one_sided")
        paths = self._paths(root)
        queue_rows = [
            {
                "document_id": "doc-endorsed-collected",
                "race_id": "race-one-sided",
                "candidate_name": "Alex Example",
                "role": "endorsed",
                "election_date": "2022-08-02",
                "source_type": "campaign_page",
                "source_type_class": "campaign_page",
                "source_url": "https://alex.example/platform",
                "seed_kinds": "known_document",
                "seed_priority": "1",
                "legacy_statement_count": "1",
                "known_source_count": "1",
                "substantive_segment_count": "4",
            },
            {
                "document_id": "doc-opponent-gap",
                "race_id": "race-one-sided",
                "candidate_name": "Blair Example",
                "role": "opponent",
                "election_date": "2022-08-02",
                "source_type": "questionnaire",
                "source_type_class": "questionnaire",
                "source_url": "https://blair.example/questionnaire",
                "seed_kinds": "known_document",
                "seed_priority": "1",
                "legacy_statement_count": "1",
                "known_source_count": "1",
                "substantive_segment_count": "0",
            },
            {
                "document_id": "doc-other",
                "race_id": "race-other",
                "candidate_name": "Casey Example",
                "role": "endorsed",
                "election_date": "2022-08-02",
                "source_type": "campaign_page",
                "source_type_class": "campaign_page",
                "source_url": "https://casey.example/platform",
                "seed_kinds": "known_document",
                "seed_priority": "1",
                "legacy_statement_count": "1",
                "known_source_count": "1",
                "substantive_segment_count": "0",
            },
        ]

        plan = build_candidate_document_regather_plan(queue_rows, paths, limit=1)

        self.assertEqual(plan.selected_unique_urls, 1)
        self.assertEqual([row["document_id"] for row in plan.queue_rows], ["doc-opponent-gap"])

    def test_build_candidate_document_regather_plan_prioritizes_opponents_over_endorsed(self) -> None:
        root = self._scenario_root("regather_opponents_first")
        paths = self._paths(root)
        queue_rows = [
            {
                "document_id": "doc-endorsed-gap",
                "race_id": "race-1",
                "candidate_name": "Alex Example",
                "role": "endorsed",
                "election_date": "2024-08-06",
                "source_type": "campaign_page",
                "source_type_class": "campaign_page",
                "source_url": "https://alex.example/platform",
                "seed_kinds": "known_document",
                "seed_priority": "1",
                "legacy_statement_count": "1",
                "known_source_count": "1",
                "substantive_segment_count": "0",
            },
            {
                "document_id": "doc-opponent-gap",
                "race_id": "race-2",
                "candidate_name": "Blair Example",
                "role": "opponent",
                "election_date": "2024-08-06",
                "source_type": "campaign_page",
                "source_type_class": "campaign_page",
                "source_url": "https://blair.example/platform",
                "seed_kinds": "known_document",
                "seed_priority": "1",
                "legacy_statement_count": "1",
                "known_source_count": "1",
                "substantive_segment_count": "0",
            },
        ]

        plan = build_candidate_document_regather_plan(queue_rows, paths, limit=1)

        self.assertEqual(plan.selected_unique_urls, 1)
        self.assertEqual([row["document_id"] for row in plan.queue_rows], ["doc-opponent-gap"])

    def test_build_candidate_document_regather_plan_skips_youtube_without_transcript(self) -> None:
        root = self._scenario_root("regather_skip_youtube")
        paths = self._paths(root)
        queue_rows = [
            {
                "document_id": "doc-youtube",
                "race_id": "race-video",
                "candidate_name": "Video Example",
                "role": "opponent",
                "election_date": "2024-06-25",
                "source_type": "debate",
                "source_type_class": "debate",
                "source_url": "https://www.youtube.com/watch?v=abc123",
                "seed_kinds": "known_document",
                "seed_priority": "1",
                "legacy_statement_count": "1",
                "known_source_count": "1",
                "substantive_segment_count": "0",
            },
            {
                "document_id": "doc-text",
                "race_id": "race-text",
                "candidate_name": "Text Example",
                "role": "endorsed",
                "election_date": "2024-06-25",
                "source_type": "questionnaire",
                "source_type_class": "questionnaire",
                "source_url": "https://example.org/questionnaire",
                "seed_kinds": "known_document",
                "seed_priority": "1",
                "legacy_statement_count": "1",
                "known_source_count": "1",
                "substantive_segment_count": "0",
            },
        ]

        plan = build_candidate_document_regather_plan(queue_rows, paths, limit=10)

        self.assertEqual(plan.skipped_transcriptless_video_documents, 1)
        self.assertEqual([row["document_id"] for row in plan.queue_rows], ["doc-text"])

    def test_run_candidate_document_regather_batch_writes_bounded_queue(self) -> None:
        root = self._scenario_root("regather_batch")
        paths = self._paths(root)
        output_queue_path = root / "data" / "processed" / "candidate_document_regather_queue.csv"
        queue_rows = [
            {
                "document_id": "doc-1",
                "queue_id": "q1",
                "race_id": "race-1",
                "candidate_name": "Alex Example",
                "role": "endorsed",
                "election_date": "2017-11-07",
                "source_type": "campaign_page",
                "source_type_class": "campaign_page",
                "source_url": "https://alex.example/platform",
                "seed_kinds": "known_document",
                "seed_priority": "1",
                "legacy_statement_count": "1",
                "known_source_count": "1",
                "substantive_segment_count": "0",
            },
            {
                "document_id": "doc-2",
                "queue_id": "q2",
                "race_id": "race-1",
                "candidate_name": "Blair Example",
                "role": "opponent",
                "election_date": "2017-11-07",
                "source_type": "interview",
                "source_type_class": "interview",
                "source_url": "https://blair.example/interview",
                "seed_kinds": "known_document",
                "seed_priority": "1",
                "legacy_statement_count": "1",
                "known_source_count": "1",
                "substantive_segment_count": "0",
            },
        ]

        result = run_candidate_document_regather_batch(
            queue_rows,
            paths,
            limit=1,
            output_queue_path=output_queue_path,
            fetcher=lambda document_id, source_url: self._capture(
                document_id=document_id,
                source_url=source_url,
                content_type="text/plain",
                body=b"Bounded queue text.",
            ),
        )

        self.assertEqual(result.plan.selected_unique_urls, 1)
        self.assertEqual(result.batch_result.processed_documents, 1)
        self.assertTrue(output_queue_path.exists())
        written_rows = self._read_csv(output_queue_path)
        self.assertEqual(len(written_rows), 1)
        self.assertEqual(written_rows[0]["document_id"], result.plan.queue_rows[0]["document_id"])

    def test_persist_raw_document_uses_content_addressed_immutable_storage(self) -> None:
        root = self._scenario_root("content_addressed")
        raw_dir = root / "data" / "raw" / "candidate_documents"
        first = self._capture(
            document_id="content-doc",
            source_url="https://example.org/one",
            content_type="text/plain",
            body=b"First version",
        )
        second = self._capture(
            document_id="content-doc",
            source_url="https://example.org/one",
            content_type="text/plain",
            body=b"Second version",
        )

        first_path = persist_raw_document(first, raw_dir)
        second_path = persist_raw_document(second, raw_dir)

        self.assertNotEqual(first_path, second_path)
        self.assertEqual(first_path.read_bytes(), b"First version")
        self.assertEqual(second_path.read_bytes(), b"Second version")

    def test_run_candidate_document_extraction_batch_records_fetch_and_extraction_errors(self) -> None:
        root = self._scenario_root("batch_errors")
        paths = self._paths(root)
        queue_rows = [
            {
                "queue_id": "q3",
                "race_id": "race-3",
                "candidate_name": "Fetch Failure",
                "role": "endorsed",
                "election_date": "2026-06-16",
                "source_type": "campaign_page",
                "source_url": "https://example.org/fetch-error",
            },
            {
                "queue_id": "q4",
                "race_id": "race-4",
                "candidate_name": "Extraction Failure",
                "role": "opponent",
                "election_date": "2026-06-16",
                "source_type": "campaign_page",
                "source_url": "https://example.org/extraction-error",
            },
            {
                "queue_id": "q5",
                "race_id": "race-5",
                "candidate_name": "Malformed URL",
                "role": "opponent",
                "election_date": "2026-06-16",
                "source_type": "campaign_page",
                "source_url": "/document/132 | https:/example.org/platform.pdf",
            },
            {
                "queue_id": "q6",
                "race_id": "race-6",
                "candidate_name": "Year Only Date",
                "role": "endorsed",
                "election_date": "2020-06-16",
                "publication_date": "2020",
                "source_type": "campaign_page",
                "source_url": "https://example.org/year-only",
            },
        ]

        def fetcher(document_id: str, source_url: str) -> RawDocumentCapture:
            if source_url.endswith("fetch-error"):
                raise RawFetchError("boom")
            return self._capture(
                document_id=document_id,
                source_url=source_url,
                content_type="text/plain",
                body=(
                    b"A substantive campaign platform about housing and healthcare."
                    if source_url.endswith("year-only")
                    else b"   \n\n  "
                ),
            )

        result = run_candidate_document_extraction_batch(
            queue_rows,
            paths,
            fetcher=fetcher,
        )

        self.assertEqual(result.fetch_errors, 1)
        self.assertEqual(result.extraction_errors, 1)
        self.assertEqual(result.metadata_errors, 1)
        metadata_rows = {row["candidate_name"]: row for row in self._read_csv(paths.metadata_path)}
        self.assertEqual(metadata_rows["Fetch Failure"]["fetch_status"], "fetch_error")
        self.assertEqual(metadata_rows["Fetch Failure"]["coverage_status"], "found_unverified")
        self.assertEqual(metadata_rows["Extraction Failure"]["extraction_status"], "extraction_error")
        self.assertEqual(metadata_rows["Malformed URL"]["fetch_status"], "metadata_error")
        self.assertEqual(metadata_rows["Year Only Date"]["publication_date"], "2020-01-01")
        analysis_rows = self._read_csv(paths.analysis_segment_path)
        self.assertEqual(len(analysis_rows), 1)
        self.assertEqual(analysis_rows[0]["candidate_name"], "Year Only Date")

    def test_run_candidate_document_extraction_batch_prefers_transcript_text(self) -> None:
        root = self._scenario_root("transcript")
        paths = self._paths(root)
        queue_rows = [
            {
                "queue_id": "q5",
                "race_id": "race-5",
                "candidate_name": "Transcript Example",
                "role": "endorsed",
                "election_date": "2026-06-16",
                "source_type": "video",
                "source_url": "https://example.org/watch",
                "transcript_title": "Town Hall",
                "transcript_text": "Public broadband now. Climate jobs guarantee.",
            }
        ]

        result = run_candidate_document_extraction_batch(
            queue_rows,
            paths,
            fetcher=lambda document_id, source_url: self._capture(
                document_id=document_id,
                source_url=source_url,
                content_type="video/mp4",
                body=b"video",
            ),
        )

        self.assertEqual(result.successful_documents, 1)
        metadata_row = self._read_csv(paths.metadata_path)[0]
        self.assertEqual(metadata_row["extractor"], "transcript")
        full_text_row = self._read_jsonl(paths.full_text_path)[0]
        self.assertEqual(full_text_row["text"], "Public broadband now. Climate jobs guarantee.")
        self.assertEqual(self._read_csv(paths.analysis_segment_path)[0]["source_type"], "video")

    def test_batch_outputs_strip_nul_and_unsafe_controls(self) -> None:
        root = self._scenario_root("sanitized_outputs")
        paths = self._paths(root)
        queue_rows = [
            {
                "queue_id": "q-clean-1",
                "race_id": "race-clean",
                "candidate_name": "Plain Example",
                "role": "endorsed",
                "election_date": "2026-06-16",
                "source_type": "campaign_page",
                "source_url": "https://example.org/plain.txt",
            },
            {
                "queue_id": "q-clean-2",
                "race_id": "race-clean",
                "candidate_name": "Transcript Example",
                "role": "opponent",
                "election_date": "2026-06-16",
                "source_type": "candidate_video",
                "source_url": "https://example.org/watch",
                "transcript_text": "Public transit\x00 now.\n\nJobs\x0b and housing\tfor all.",
            },
        ]

        run_candidate_document_extraction_batch(
            queue_rows,
            paths,
            fetcher=lambda document_id, source_url: self._capture(
                document_id=document_id,
                source_url=source_url,
                content_type="video/mp4" if source_url.endswith("/watch") else "text/plain",
                body=b"Housing\x00 now.\n\nLabor\x0b rights\tfor all.",
            ),
            analysis_config=AnalysisSegmentConfig(min_tokens=1, max_tokens=20),
        )

        for path in (
            paths.metadata_path,
            paths.full_text_path,
            paths.paragraph_path,
            paths.sentence_path,
            paths.analysis_segment_path,
        ):
            data = path.read_bytes()
            self.assertEqual(data.count(b"\x00"), 0)
        with paths.analysis_segment_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertTrue(rows)
        self.assertTrue(all("\x00" not in row["text"] for row in rows))
        full_text_rows = {row["candidate_name"]: row for row in self._read_jsonl(paths.full_text_path)}
        self.assertIn("Housing now.", full_text_rows["Plain Example"]["text"])
        self.assertIn("Jobs and housing for all.", full_text_rows["Transcript Example"]["text"])

    def test_run_candidate_document_extraction_batch_records_media_without_transcript(self) -> None:
        root = self._scenario_root("media_no_transcript")
        paths = self._paths(root)
        queue_rows = [
            {
                "queue_id": "q6",
                "race_id": "race-6",
                "candidate_name": "Media Example",
                "role": "opponent",
                "election_date": "2026-06-16",
                "source_type": "video",
                "source_url": "https://example.org/media",
            }
        ]

        result = run_candidate_document_extraction_batch(
            queue_rows,
            paths,
            fetcher=lambda document_id, source_url: self._capture(
                document_id=document_id,
                source_url=source_url,
                content_type="video/mp4",
                body=b"",
            ),
        )

        self.assertEqual(result.media_without_transcript, 1)
        self.assertEqual(self._read_csv(paths.metadata_path)[0]["coverage_status"], "media_no_transcript")
        self.assertEqual(self._read_jsonl(paths.full_text_path)[0]["coverage_status"], "media_no_transcript")
        self.assertEqual(self._read_csv(paths.analysis_segment_path), [])

    def test_shared_document_without_locator_is_marked_unscoped(self) -> None:
        root = self._scenario_root("shared_unscoped")
        paths = self._paths(root)
        shared_url = "https://example.org/guide.txt"
        queue_rows = [
            {
                "queue_id": "q7",
                "race_id": "race-7",
                "candidate_name": "Alex Example",
                "role": "endorsed",
                "election_date": "2026-06-16",
                "source_type": "voter_guide",
                "source_url": shared_url,
            },
            {
                "queue_id": "q8",
                "race_id": "race-7",
                "candidate_name": "Blair Example",
                "role": "opponent",
                "election_date": "2026-06-16",
                "source_type": "voter_guide",
                "source_url": shared_url,
            },
        ]

        run_candidate_document_extraction_batch(
            queue_rows,
            paths,
            fetcher=lambda document_id, source_url: self._capture(
                document_id=document_id,
                source_url=source_url,
                content_type="text/plain",
                body=(
                    b"This is a shared voter guide with complete text for multiple candidates. "
                    b"It should not be assigned wholesale to either candidate."
                ),
            ),
            analysis_config=AnalysisSegmentConfig(min_tokens=2, max_tokens=30),
        )

        metadata_rows = self._read_csv(paths.metadata_path)
        self.assertEqual(
            {row["coverage_status"] for row in metadata_rows},
            {"shared_document_unscoped"},
        )
        self.assertEqual(
            {row["extraction_status"] for row in metadata_rows},
            {"shared_document_unscoped"},
        )
        self.assertEqual(self._read_csv(paths.analysis_segment_path), [])
        full_text_rows = self._read_jsonl(paths.full_text_path)
        self.assertEqual(
            {row["coverage_status"] for row in full_text_rows},
            {"shared_document_unscoped"},
        )
        self.assertEqual({row["text"] for row in full_text_rows}, {""})

    def test_shared_document_with_locator_scopes_candidate_specific_section(self) -> None:
        root = self._scenario_root("shared_scoped")
        paths = self._paths(root)
        shared_url = "https://example.org/questions.txt"
        queue_rows = [
            {
                "queue_id": "q9",
                "race_id": "race-9",
                "candidate_name": "Alex Example",
                "role": "endorsed",
                "election_date": "2026-06-16",
                "source_type": "questionnaire",
                "source_url": shared_url,
                "legacy_locators": "Question 1",
            },
            {
                "queue_id": "q10",
                "race_id": "race-9",
                "candidate_name": "Blair Example",
                "role": "opponent",
                "election_date": "2026-06-16",
                "source_type": "questionnaire",
                "source_url": shared_url,
                "legacy_locators": "Question 2",
            },
        ]

        run_candidate_document_extraction_batch(
            queue_rows,
            paths,
            fetcher=lambda document_id, source_url: self._capture(
                document_id=document_id,
                source_url=source_url,
                content_type="text/plain",
                body=(
                    b"Question 1 Candidate supports public housing and public power for working families.\n\n"
                    b"Question 2 Candidate supports fully funding public schools and tenant protections."
                ),
            ),
            analysis_config=AnalysisSegmentConfig(min_tokens=3, max_tokens=40),
        )

        full_text_rows = {
            row["candidate_name"]: row for row in self._read_jsonl(paths.full_text_path)
        }
        self.assertIn("Question 1", full_text_rows["Alex Example"]["text"])
        self.assertNotIn("Question 2", full_text_rows["Alex Example"]["text"])
        self.assertIn("Question 2", full_text_rows["Blair Example"]["text"])
        self.assertNotIn("Question 1", full_text_rows["Blair Example"]["text"])
        analysis_rows = self._read_csv(paths.analysis_segment_path)
        self.assertEqual(len(analysis_rows), 2)
        self.assertEqual(
            {row["candidate_name"] for row in analysis_rows},
            {"Alex Example", "Blair Example"},
        )

    def test_range_and_from_locators_scope_shared_candidate_sections(self) -> None:
        root = self._scenario_root("shared_range_from")
        paths = self._paths(root)
        shared_url = "https://example.org/qa.txt"
        queue_rows = [
            {
                "queue_id": "q13",
                "race_id": "race-13",
                "candidate_name": "Mike Connolly",
                "role": "endorsed",
                "election_date": "2016-09-08",
                "source_type": "candidate_questionnaire",
                "source_url": shared_url,
                "legacy_locators": "range: Mike Connolly => Tim Toomey",
            },
            {
                "queue_id": "q14",
                "race_id": "race-13",
                "candidate_name": "Tim Toomey",
                "role": "opponent",
                "election_date": "2016-09-08",
                "source_type": "candidate_questionnaire",
                "source_url": shared_url,
                "legacy_locators": "from: Tim Toomey",
            },
        ]

        run_candidate_document_extraction_batch(
            queue_rows,
            paths,
            fetcher=lambda document_id, source_url: self._capture(
                document_id=document_id,
                source_url=source_url,
                content_type="text/plain",
                body=(
                    b"Mike Connolly\n\n"
                    b"Expand affordable housing and fund transit.\n\n"
                    b"Tim Toomey\n\n"
                    b"Protect neighborhood schools and city services."
                ),
            ),
            analysis_config=AnalysisSegmentConfig(min_tokens=2, max_tokens=40),
        )

        full_text_rows = {
            row["candidate_name"]: row for row in self._read_jsonl(paths.full_text_path)
        }
        self.assertIn("Expand affordable housing", full_text_rows["Mike Connolly"]["text"])
        self.assertNotIn("Protect neighborhood schools", full_text_rows["Mike Connolly"]["text"])
        self.assertIn("Protect neighborhood schools", full_text_rows["Tim Toomey"]["text"])
        self.assertNotIn("Expand affordable housing", full_text_rows["Tim Toomey"]["text"])

    def test_srt_time_locators_scope_candidate_specific_captions(self) -> None:
        root = self._scenario_root("srt_locators")
        paths = self._paths(root)
        shared_url = "https://archive.example/interview.asr.srt"
        queue_rows = [
            {
                "queue_id": "q15",
                "race_id": "race-15",
                "candidate_name": "Mike Connolly",
                "role": "endorsed",
                "election_date": "2016-09-08",
                "source_type": "candidate_interview_transcript",
                "source_url": shared_url,
                "legacy_locators": "time 00:00:01,000-00:00:04,000 | time 00:00:09,000-00:00:12,000",
            },
            {
                "queue_id": "q16",
                "race_id": "race-15",
                "candidate_name": "Tim Toomey",
                "role": "opponent",
                "election_date": "2016-09-08",
                "source_type": "candidate_interview_transcript",
                "source_url": shared_url,
                "legacy_locators": "time 00:00:05,000-00:00:08,000",
            },
        ]

        run_candidate_document_extraction_batch(
            queue_rows,
            paths,
            fetcher=lambda document_id, source_url: self._capture(
                document_id=document_id,
                source_url=source_url,
                content_type="application/x-subrip",
                body=(
                    b"1\n00:00:01,000 --> 00:00:04,000\n"
                    b"Connolly opening on housing and transit.\n\n"
                    b"2\n00:00:05,000 --> 00:00:08,000\n"
                    b"Toomey opening on schools and city services.\n\n"
                    b"3\n00:00:09,000 --> 00:00:12,000\n"
                    b"Connolly closing on labor rights.\n"
                ),
            ),
            analysis_config=AnalysisSegmentConfig(min_tokens=2, max_tokens=40),
        )

        full_text_rows = {
            row["candidate_name"]: row for row in self._read_jsonl(paths.full_text_path)
        }
        self.assertIn("Connolly opening", full_text_rows["Mike Connolly"]["text"])
        self.assertIn("Connolly closing", full_text_rows["Mike Connolly"]["text"])
        self.assertNotIn("Toomey opening", full_text_rows["Mike Connolly"]["text"])
        self.assertIn("Toomey opening", full_text_rows["Tim Toomey"]["text"])
        paragraphs = self._read_csv(paths.paragraph_path)
        self.assertEqual(paragraphs[0]["locator"], "time 00:00:01,000-00:00:04,000")

    def test_context_only_documents_are_excluded_from_analysis_segments(self) -> None:
        root = self._scenario_root("context_only")
        paths = self._paths(root)
        queue_rows = [
            {
                "queue_id": "q17",
                "race_id": "race-17",
                "candidate_name": "Andrew Edwards",
                "role": "opponent",
                "election_date": "2016-06-14",
                "source_type": "candidate_profile",
                "source_url": "https://ballotpedia.org/Andrew_Edwards",
                "analysis_scope": "context_only",
            }
        ]

        run_candidate_document_extraction_batch(
            queue_rows,
            paths,
            fetcher=lambda document_id, source_url: self._capture(
                document_id=document_id,
                source_url=source_url,
                content_type="text/plain",
                body=b"Biography and election history for Andrew Edwards.",
            ),
            analysis_config=AnalysisSegmentConfig(min_tokens=2, max_tokens=30),
        )

        metadata_rows = self._read_csv(paths.metadata_path)
        self.assertEqual(metadata_rows[0]["analysis_scope"], "context_only")
        self.assertEqual(metadata_rows[0]["extraction_status"], "extracted")
        self.assertEqual(self._read_csv(paths.analysis_segment_path), [])

    def test_shared_pdf_page_locators_scope_candidates_without_overlap(self) -> None:
        root = self._scenario_root("shared_pdf_scoped")
        paths = self._paths(root)
        shared_url = "https://example.org/questions.pdf"
        queue_rows = [
            {
                "queue_id": "q11",
                "race_id": "race-11",
                "candidate_name": "Alex Example",
                "role": "endorsed",
                "election_date": "2026-06-16",
                "source_type": "questionnaire",
                "source_url": shared_url,
                "legacy_locators": "PDF page 1",
            },
            {
                "queue_id": "q12",
                "race_id": "race-11",
                "candidate_name": "Blair Example",
                "role": "opponent",
                "election_date": "2026-06-16",
                "source_type": "questionnaire",
                "source_url": shared_url,
                "legacy_locators": "PDF page 2",
            },
        ]

        with patch(
            "dsa_analysis.document_corpus._pdf_reader_class",
            side_effect=ExtractionError("PDF extraction requires the optional dependency 'pypdf'"),
        ), patch(
            "dsa_analysis.document_corpus.platform.system",
            return_value="Darwin",
        ), patch(
            "dsa_analysis.document_corpus._swift_executable",
            return_value=Path("/usr/bin/swift"),
        ), patch(
            "dsa_analysis.document_corpus.subprocess.run",
            return_value=subprocess.CompletedProcess(
                ["/usr/bin/swift"],
                0,
                stdout=(
                    b'{"title":"Guide","pages":'
                    b'[{"page":"1","text":"Alex supports public housing for all."},'
                    b'{"page":"2","text":"Blair supports union schools and transit."}]}'
                ),
                stderr=b"",
            ),
        ):
            run_candidate_document_extraction_batch(
                queue_rows,
                paths,
                fetcher=lambda document_id, source_url: self._capture(
                    document_id=document_id,
                    source_url=source_url,
                    content_type="application/pdf",
                    body=b"%PDF-1.7",
                ),
                analysis_config=AnalysisSegmentConfig(min_tokens=1, max_tokens=20),
            )

        full_text_rows = {
            row["candidate_name"]: row for row in self._read_jsonl(paths.full_text_path)
        }
        self.assertIn("[PDF page 1]", full_text_rows["Alex Example"]["text"])
        self.assertNotIn("[PDF page 2]", full_text_rows["Alex Example"]["text"])
        self.assertIn("[PDF page 2]", full_text_rows["Blair Example"]["text"])
        self.assertNotIn("[PDF page 1]", full_text_rows["Blair Example"]["text"])
        analysis_rows = self._read_csv(paths.analysis_segment_path)
        self.assertEqual(len(analysis_rows), 2)

    def _scenario_root(self, name: str) -> Path:
        root = SCRATCH_ROOT / name
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _paths(self, root: Path) -> CandidateDocumentBatchPaths:
        return CandidateDocumentBatchPaths(
            queue_path=root / "data" / "processed" / "candidate_document_queue.csv",
            raw_dir=root / "data" / "raw" / "candidate_documents",
            raw_manifest_path=root / "data" / "processed" / "candidate_document_raw_manifest.jsonl",
            metadata_path=root / "data" / "processed" / "candidate_document_metadata.csv",
            full_text_path=root / "data" / "processed" / "candidate_document_full_text.jsonl",
            paragraph_path=root / "data" / "processed" / "candidate_document_paragraphs.csv",
            sentence_path=root / "data" / "processed" / "candidate_document_sentences.csv",
            analysis_segment_path=root / "data" / "processed" / "candidate_document_analysis_segments.csv",
        )

    def _capture(
        self,
        *,
        document_id: str,
        source_url: str,
        content_type: str,
        body: bytes,
    ) -> RawDocumentCapture:
        return RawDocumentCapture(
            document_id=document_id,
            source_url=normalize_source_url(source_url),
            final_url=normalize_source_url(source_url),
            retrieved_at="2026-08-19T17:00:00+00:00",
            content_type=content_type,
            encoding="utf-8",
            content_bytes=body,
            byte_count=len(body),
            sha256=hashlib.sha256(body).hexdigest(),
        )

    def _segments(
        self,
        document_id: str,
        text: str,
    ):
        return segment_document(document_id, text)

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def _write_csv(self, path: Path, rows: list[dict[str, str]]) -> None:
        if not rows:
            raise AssertionError("rows are required")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def _read_jsonl(self, path: Path) -> list[dict[str, str]]:
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]


if __name__ == "__main__":
    unittest.main()
