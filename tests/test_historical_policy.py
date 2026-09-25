import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.document_corpus import CandidateDocumentBatchPaths
from dsa_analysis.historical_policy import (
    IDENTITY_BASIS, REVIEW_METHOD, linked_publication_bound,
    register_review_captures, validate_historical_review, validate_publisher_dates, answer_context_matches,
)
from dsa_analysis.io import read_csv, write_csv
from dsa_analysis.paths import ANALYSIS_DATA_DIR, MANUAL_DIR, PROCESSED_DIR


class HistoricalPolicyTests(unittest.TestCase):
    def test_campaign_edition_date_survives_the_real_statement_export_path(self):
        path = MANUAL_DIR / "policy_presidential_2020_followup_review.json"
        own = {e["excerpt_id"] for e in json.loads(path.read_text())["excerpts"]}
        prior = {
            r["excerpt_id"]: r
            for filename in ("reviewed_candidate_statements.csv", "timing_unverified_candidate_statements.csv")
            for r in read_csv(ANALYSIS_DATA_DIR / "policy_evidence" / filename)
            if r["excerpt_id"] not in own
        }
        races = {r["race_id"]: r for r in read_csv(PROCESSED_DIR / "race_registry.csv")}
        result = validate_historical_review(path, races, "2026-09-22", prior)
        statements = {r["excerpt_id"]: r for r in result["statements"]}
        dividend = statements["hpf20-yang-income"]
        self.assertEqual(dividend["publication_date"], "2018-01-22")
        self.assertEqual(dividend["temporal_evidence_date"], "2020-02-04")
        self.assertEqual(dividend["timing_status"], "verified_archived_campaign_version")
        self.assertEqual(statements["hpf20-yang-health"]["temporal_evidence_date"], "2020-01-20")

    def test_html_publication_metadata_is_bound_to_the_page_and_keeps_unknown_revision(self):
        source = {
            "url": "https://example.org/vision/", "content_type": "text/html",
            "publication_date": "2019-11-12",
            "publisher_date_metadata": {"format": "html_meta"},
        }
        body = (
            '<meta property="og:url" content="https://example.org/vision/">'
            '<meta property="article:published_time" content="2019-11-12T02:29:36">'
        ).encode()
        self.assertTrue(validate_publisher_dates(source, body))
        self.assertNotIn("source_updated_date", source)
        for changes in (
            {"url": "https://example.org/other"},
            {"publication_date": "2019-12-06"},
            {"source_updated_date": "2019-11-12"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_publisher_dates({**source, **changes}, body)
        with self.assertRaises(ValueError):
            validate_publisher_dates(source, body + body)

    def test_article_date_node_without_id_requires_unique_type_and_page_url(self):
        node = {
            "@type": "NewsArticle", "mainEntityOfPage": {"@id": "https://example.org/article"},
            "datePublished": "2020-06-17T16:03:06Z", "dateModified": "2024-03-05T21:02:11Z",
        }
        source = {
            "url": "https://example.org/article", "content_type": "text/html",
            "publication_date": "2020-06-17", "source_updated_date": "2024-03-05",
            "publisher_date_metadata": {
                "format": "json_ld", "node_url": "https://example.org/article", "node_type": "NewsArticle",
            },
        }
        body = ('<script type="application/ld+json">' + json.dumps(node) + '</script>').encode()
        self.assertTrue(validate_publisher_dates(source, body))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            validate_publisher_dates(source, body + body)
        with self.assertRaisesRegex(ValueError, "different source"):
            validate_publisher_dates({**source, "url": "https://example.org/other"}, body)
        with self.assertRaisesRegex(ValueError, "exactly one explicit"):
            validate_publisher_dates({
                **source, "publisher_date_metadata": {**source["publisher_date_metadata"], "node_id": "also-set"},
            }, body)

    def test_visible_datelines_preserve_known_post_primary_revisions(self):
        source = {
            "content_type": "text/html", "publication_date": "2025-03-02", "source_updated_date": "2026-01-22",
            "publisher_date_metadata": {
                "format": "html_dateline", "class_name": "dateline",
                "publication_text": "Mar 2, 2025 7:00 pm",
                "revision_text": "· Updated Jan 22, 2026 3:52 pm",
            },
        }
        body = (
            '<span class="dateline text-smaller">Mar 2, 2025 7:00 pm</span>'
            '<span class="dateline text-smaller">&middot; Updated Jan 22, 2026 3:52 pm</span>'
        ).encode()
        self.assertTrue(validate_publisher_dates(source, body))
        with self.assertRaisesRegex(ValueError, "differs"):
            validate_publisher_dates({**source, "source_updated_date": "2025-03-02"}, body)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            validate_publisher_dates(source, body + body)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            validate_publisher_dates(source, body.replace(b'dateline text-smaller', b'candidate-quote'))

    def test_checkbox_quote_is_bound_to_its_own_question_context(self):
        paragraph = "Support proposal A? YES [X] NO [ ] Support proposal B? YES [ ] NO [X]"
        excerpt = {"short_exact_quote": "NO [X]", "answer_context": "Support proposal B? YES [ ] NO [X]"}
        self.assertTrue(answer_context_matches(excerpt, paragraph))
        self.assertFalse(answer_context_matches({**excerpt, "answer_context": "Support proposal A? YES [ ] NO [X]"}, paragraph))
        self.assertFalse(answer_context_matches(excerpt, paragraph + " " + paragraph))
        with self.assertRaisesRegex(ValueError, "exactly one occurrence"):
            answer_context_matches({**excerpt, "answer_context": "NO [X] NO [X]"}, paragraph)
        with self.assertRaisesRegex(ValueError, "nonempty"):
            answer_context_matches({**excerpt, "answer_context": ""}, paragraph)

    def test_publisher_date_proof_must_match_page_identity_and_both_dates(self):
        source = {
            "url": "https://example.org/candidate", "content_type": "text/html",
            "publication_date": "2020-04-22", "source_updated_date": "2024-01-16",
            "publisher_date_metadata": {"format": "json_ld", "node_id": "https://example.org/candidate"},
        }
        node = {
            "@type": "WebPage", "@id": source["url"], "url": source["url"],
            "datePublished": "2020-04-22T02:03:08+00:00", "dateModified": "2024-01-16T18:49:23+00:00",
        }
        body = ('<script type="application/ld+json">' + json.dumps({"@graph": [node]}) + "</script>").encode()
        self.assertTrue(validate_publisher_dates(source, body))
        upgraded = body.replace(b"https://example.org/candidate", b"http://example.org/candidate")
        self.assertTrue(validate_publisher_dates({
            **source, "publisher_date_metadata": {"format": "json_ld", "node_id": "http://example.org/candidate"},
        }, upgraded))
        with self.assertRaisesRegex(ValueError, "different source"):
            validate_publisher_dates({**source, "url": "https://other.example/candidate"}, body)
        with self.assertRaisesRegex(ValueError, "differs"):
            validate_publisher_dates({**source, "publication_date": "2020-04-21"}, body)
        with self.assertRaisesRegex(ValueError, "different source"):
            validate_publisher_dates({**source, "url": "https://example.org/other"}, body)
        wrong_type = body.replace(b"WebPage", b"ImageObject")
        with self.assertRaisesRegex(ValueError, "unrelated metadata type"):
            validate_publisher_dates(source, wrong_type)
        self.assertFalse(validate_publisher_dates({}, body))

    def test_linked_release_requires_exact_retained_link_and_publication_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            body = b'<script>{"datePublished":"2021-02-18"}</script><a href="/answers.pdf">Candidate answers</a>'
            (root / "release.html").write_bytes(body)
            parent = {
                "url": "https://publisher.example/article", "raw_path": "release.html",
                "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
                "publication_date": "2021-02-18", "source_updated_date": "2021-02-18",
            }
            source = {
                "url": "https://publisher.example/answers.pdf", "available_by_date": "2021-02-18",
                "availability_evidence": {
                    "document_id": "release", "publication_date_marker": '"datePublished":"2021-02-18"',
                    "source_locator": "candidate-answer link",
                },
            }
            with patch("dsa_analysis.historical_policy.ROOT", root):
                self.assertEqual(linked_publication_bound(source, {"release": parent}), "2021-02-18")
                with self.assertRaisesRegex(ValueError, "does not link"):
                    linked_publication_bound({**source, "url": "https://publisher.example/other.pdf"}, {"release": parent})
                with self.assertRaisesRegex(ValueError, "Later revisions"):
                    linked_publication_bound(source, {"release": {**parent, "source_updated_date": "2022-01-01"}})
                updated_body = body + b'<meta property="article:modified_time" content="2021-02-20"/>'
                (root / "release.html").write_bytes(updated_body)
                parent.update(sha256=hashlib.sha256(updated_body).hexdigest(), bytes=len(updated_body),
                              source_updated_date="2021-02-20")
                revised_source = {
                    **source, "available_by_date": "2021-02-20",
                    "availability_evidence": {
                        "document_id": "release", "source_locator": "candidate-answer link",
                        "date_field": "source_updated_date",
                        "availability_date_marker": 'content="2021-02-20"',
                    },
                }
                self.assertEqual(linked_publication_bound(revised_source, {"release": parent}), "2021-02-20")
                with self.assertRaisesRegex(ValueError, "cannot precede"):
                    linked_publication_bound(revised_source, {"release": {**parent, "publication_date": "2021-02-21"}})

    def test_new_intake_uses_reviewed_locator_and_never_turns_questions_into_answers(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory).resolve()
            body = b"<p>Question: Do you support public housing?</p><p>Jane: I support public housing.</p><p>Jane: I support worker organizing.</p>"
            (root / "source.html").write_bytes(body)
            race = {
                "race_id": "race", "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                "election_date": "2020-08-01", "endorsed_candidate": "Jane Example",
                "endorsed_candidates": "", "opponent_candidates": "", "all_candidates": "Jane Example",
            }
            write_csv(root / "race_registry.csv", [race], list(race))
            source = {
                "document_id": "source", "url": "https://example.org/qa", "final_url": "https://example.org/qa",
                "publication_date": "2020-05-01", "retrieved_at": "2020-05-02",
                "raw_path": "source.html", "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body), "content_type": "text/html", "status": "used",
            }
            review = {
                "review_method": REVIEW_METHOD, "sources": [source],
                "excerpts": [{
                    "excerpt_id": "quote", "document_id": "source", "metadata_document_id": None,
                    "speaker": "Jane Example", "race_id": "race", "short_exact_quote": "public housing",
                    "role": "endorsed_candidate",
                    "candidate_document_registration": {
                        "race_id": "race", "candidate_name": "Jane Example", "role": "endorsed",
                        "election_date": "2020-08-01", "source_type": "candidate_questionnaire",
                        "publication_date": "2020-05-01", "locator": "paragraph 2",
                    },
                }],
            }
            source_path = root / "input.json"
            source_path.write_text(json.dumps(review))
            paths = CandidateDocumentBatchPaths(
                queue_path=root / "queue.csv", raw_dir=root / "raw", raw_manifest_path=root / "raw.jsonl",
                metadata_path=root / "candidate_document_metadata.csv", full_text_path=root / "text.jsonl",
                paragraph_path=root / "candidate_document_paragraphs.csv",
                sentence_path=root / "sentences.csv", analysis_segment_path=root / "segments.csv",
            )
            with (
                patch("dsa_analysis.historical_policy.ROOT", root),
                patch("dsa_analysis.historical_policy.PROCESSED_DIR", root),
                patch("dsa_analysis.historical_policy.ANALYSIS_DATA_DIR", root / "analysis"),
                patch("dsa_analysis.historical_policy.CandidateDocumentBatchPaths.default", return_value=paths),
            ):
                register_review_captures(source_path, root / "review.json")
                second = json.loads(json.dumps(review))
                second["excerpts"][0]["excerpt_id"] = "second-quote"
                second["excerpts"][0]["short_exact_quote"] = "worker organizing"
                second["excerpts"][0]["candidate_document_registration"]["locator"] = "paragraph 3"
                second_path = root / "second-input.json"
                second_path.write_text(json.dumps(second))
                register_review_captures(second_path, root / "second-review.json")
            from dsa_analysis.io import read_csv
            self.assertEqual([r["text"] for r in read_csv(paths.paragraph_path)], ["public housing", "worker organizing"])
            self.assertEqual(read_csv(paths.analysis_segment_path), [])
            bound = json.loads((root / "review.json").read_text())["excerpts"][0]["metadata_document_id"]
            self.assertTrue(bound)

    def test_state_house_sources_keep_identity_basis_and_timing_qualification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources, excerpts, metadata, paragraphs = [], [], [], []
            for key, speaker, role, status in [
                ("left", "Jane Example", "endorsed_candidate", "used"),
                ("right", "Other Democrat", "opponent_candidate", "timing_unverified"),
            ]:
                quote = "I support public housing."
                body = f"<p>{speaker}: {quote}</p>".encode()
                (root / f"{key}.html").write_bytes(body)
                digest = hashlib.sha256(body).hexdigest()
                final = f"https://example.org/{key}"
                sources.append({
                    "document_id": key, "url": final, "final_url": final,
                    "publication_date": "2020-05-01" if status == "used" else None,
                    "retrieved_at": "2020-09-01", "raw_path": f"{key}.html",
                    "sha256": digest, "bytes": len(body), "content_type": "text/html", "status": status,
                })
                metadata.append({
                    "document_id": key, "candidate_name": speaker, "race_id": "legacy-race",
                    "election_date": "2020-08-01", "raw_sha256": digest,
                    "source_url": final, "final_url": final, "extraction_status": "extracted",
                    "analysis_scope": "candidate_excerpt",
                    "publication_date": "2020-05-01" if status == "used" else "",
                })
                paragraphs.append({"document_id": key, "locator": "paragraph 1", "text": f"{speaker}: {quote}"})
                excerpts.append({
                    "excerpt_id": key, "document_id": key, "metadata_document_id": key,
                    "speaker": speaker, "role": role, "race_id": "race", "election_date": "2020-08-01",
                    "topic": "housing", "subtopic": "public_housing", "stance": "support",
                    "short_exact_quote": quote, "locator": "candidate answer", "notes": "Source-reviewed answer.",
                })
            write_csv(root / "candidate_document_metadata.csv", metadata, list(metadata[0]))
            write_csv(root / "candidate_document_paragraphs.csv", paragraphs, list(paragraphs[0]))
            write_csv(root / "endorsements.csv", [], ["race_id", "candidate_name", "election_date", "verification_status"])
            race = {
                "race_id": "race", "election_date": "2020-08-01", "election_year": "2020",
                "scope_kind": "tracked_dsa_endorsed_democratic_primary", "office": "State House",
                "endorsed_candidate": "Jane Example", "endorsed_candidates": "",
                "opponent_candidates": "Other Democrat", "all_candidates": "Jane Example | Other Democrat",
                "source_race_ids": "legacy-race", "official_election_source": "https://example.gov/results",
                "official_election_source_status": "resolution_verified",
                "certified_opponents_status": "corpus_candidate_set",
            }
            review = {
                "identity_basis": IDENTITY_BASIS, "review_method": REVIEW_METHOD,
                "sources": sources, "excerpts": excerpts, "unsuccessful_sources": [],
                "comparisons": [{
                    "comparison_id": "pair", "race_id": "race", "excerpt_ids": ["left", "right"],
                    "relationship": "shared_position", "interpretation": "Both support public housing.",
                }],
            }
            path = root / "review.json"
            path.write_text(json.dumps(review))
            with (
                patch("dsa_analysis.historical_policy.ROOT", root),
                patch("dsa_analysis.historical_policy.PROCESSED_DIR", root),
                patch("dsa_analysis.historical_policy.MANUAL_DIR", root),
            ):
                result = validate_historical_review(path, {"race": race}, "2026-09-22")
                self.assertEqual(result["rows"], [])
                self.assertEqual(len(result["timing_unverified_rows"]), 1)
                self.assertEqual(result["statements"][0]["identity_resolution"], IDENTITY_BASIS)
                self.assertEqual(result["gaps"][0]["outcome"], "pre_primary_timing_unverified")
                right = review["sources"][1]
                right["publication_date"] = "2020-05-01"
                right["source_updated_date"] = "2024-01-01"
                right["publisher_date_metadata"] = {"format": "json_ld", "node_id": right["url"]}
                date_node = {
                    "@type": "WebPage", "@id": right["url"], "url": right["url"],
                    "datePublished": "2020-05-01T00:00:00Z", "dateModified": "2024-01-01T00:00:00Z",
                }
                body = (root / "right.html").read_bytes() + (
                    '<script type="application/ld+json">' + json.dumps(date_node) + "</script>"
                ).encode()
                (root / "right.html").write_bytes(body)
                right.update(sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))
                metadata[1].update(raw_sha256=right["sha256"], publication_date=right["publication_date"])
                write_csv(root / "candidate_document_metadata.csv", metadata, list(metadata[0]))
                path.write_text(json.dumps(review))
                revised = validate_historical_review(path, {"race": race}, "2026-09-22")
                self.assertEqual(len(revised["timing_unverified_rows"]), 1)
                proof = right.pop("publisher_date_metadata")
                path.write_text(json.dumps(review))
                with self.assertRaisesRegex(ValueError, "cannot be hidden"):
                    validate_historical_review(path, {"race": race}, "2026-09-22")
                right["publisher_date_metadata"] = proof
                notice = "Update: A candidate response was added after this article first ran."
                notice_body = b"<p>Other Democrat: I support public housing.</p><p>" + notice.encode() + b"</p>"
                right["source_updated_date"] = ""
                right.pop("publisher_date_metadata")
                right["unbounded_revision_notice"] = {"source_locator": "paragraph 2", "exact_quote": notice}
                right.update(sha256=hashlib.sha256(notice_body).hexdigest(), bytes=len(notice_body))
                (root / "right.html").write_bytes(notice_body)
                metadata[1]["raw_sha256"] = right["sha256"]
                write_csv(root / "candidate_document_metadata.csv", metadata, list(metadata[0]))
                path.write_text(json.dumps(review))
                unknown_revision = validate_historical_review(path, {"race": race}, "2026-09-22")
                self.assertEqual(
                    unknown_revision["timing_unverified_statements"][0]["version_timing_qualification"],
                    "publisher_revision_day_unknown",
                )
                right["unbounded_revision_notice"]["source_locator"] = "paragraph 1"
                path.write_text(json.dumps(review))
                with self.assertRaisesRegex(ValueError, "revision notice is absent"):
                    validate_historical_review(path, {"race": race}, "2026-09-22")
                right["unbounded_revision_notice"]["source_locator"] = "paragraph 2"
                review["excerpts"][0]["locator"] = "paragraph 2"
                path.write_text(json.dumps(review))
                with self.assertRaisesRegex(ValueError, "candidate-scoped evidence"):
                    validate_historical_review(path, {"race": race}, "2026-09-22")
                review["excerpts"][0]["locator"] = "candidate answer"
                review["sources"][1]["final_url"] = "https://web.archive.org/web/20200701/https://example.org/right"
                path.write_text(json.dumps(review))
                with self.assertRaisesRegex(ValueError, "actual retained final URL"):
                    validate_historical_review(path, {"race": race}, "2026-09-22")
                right["final_url"] = right["url"]
                race["scope_kind"] = "other_corpus_race"
                resolution = {
                    "race_id": "race", "scope_kind": "other_corpus_race",
                    "classification": "endorsement_revoked_before_primary",
                    "source_url": "https://chapter.example/revocation", "notes": "Revoked before primary.",
                }
                write_csv(root / "race_scope_resolutions.csv", [resolution], list(resolution))
                path.write_text(json.dumps(review))
                with self.assertRaisesRegex(ValueError, "scope-excluded"):
                    validate_historical_review(path, {"race": race}, "2026-09-22")
                review["comparisons"] = []
                path.write_text(json.dumps(review))
                excluded = validate_historical_review(path, {"race": race}, "2026-09-22")
                self.assertEqual(excluded["statements"], [])
                self.assertEqual(excluded["timing_unverified_statements"], [])
                self.assertEqual(excluded["expected_candidates"], {})
                self.assertEqual(len(excluded["excluded_statements"]), 2)
                self.assertEqual(excluded["excluded_statements"][0]["quote"], "I support public housing.")


if __name__ == "__main__":
    unittest.main()
