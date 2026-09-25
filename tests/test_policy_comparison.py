import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from dsa_analysis.document_corpus import CandidateDocumentBatchPaths
from dsa_analysis.io import read_csv, write_csv
from dsa_analysis.policy_comparison import (
    attributed_quote_locators, ingest_reviewed_documents, platform_pair_date_issues,
    source_evidence_date, validate_comparison, validated_supplemental_review,
    eligible_identity_rows,
)
from dsa_analysis.paths import ANALYSIS_DATA_DIR, MANUAL_DIR, PROCESSED_DIR


class PolicyComparisonTests(unittest.TestCase):
    def test_shared_ballot_keeps_focal_party_but_excludes_republican_comparators(self):
        race = {
            "office": "US House", "jurisdiction": "District 24", "state_code": "CA",
            "election_date": "2026-06-02", "endorsed_candidate": "Focal Candidate",
        }
        rows = [{
            "candidate_name": name, "state_code": "CA", "election_date": "2026-06-02",
            "chamber": "House", "district": "24", "write_in": "false",
            "primary_party": "", "party": party, "election_system": "nonpartisan_top_two",
        } for name, party in [
            ("Focal Candidate", "Peace and Freedom"), ("Democrat", "Democratic"), ("Republican", "Republican"),
        ]]
        self.assertEqual(
            [row["candidate_name"] for row in eligible_identity_rows(
                rows, race, "nonpartisan_ballot_endorsed_vs_democrats",
            )],
            ["Focal Candidate", "Democrat"],
        )
        self.assertEqual(rows[0]["party"], "Peace and Freedom")

    def test_undated_guide_answer_is_retained_without_backdating_the_comparison(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory).resolve()
            sources = []
            excerpts = []
            ballots = []
            for key, speaker, role, status in [
                ("left", "Jane Example", "endorsed_candidate", "used"),
                ("right", "Other Democrat", "opponent_candidate", "timing_unverified"),
            ]:
                quote = "I support public housing."
                body = f"<p>{speaker}: {quote}</p>".encode()
                (root / f"{key}.html").write_bytes(body)
                sources.append({
                    "document_id": key, "url": f"https://example.gov/{key}",
                    "final_url": (
                        f"https://example.gov/{key}" if status == "used" else
                        f"https://web.archive.org/web/20260624120000id_/https://example.gov/{key}"
                    ),
                    "publication_date": "2026-05-18" if status == "used" else None,
                    "retrieved_at": "2026-09-22T12:00:00Z", "raw_path": f"{key}.html",
                    "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "status": status,
                })
                excerpts.append({
                    "excerpt_id": key, "document_id": key, "speaker": speaker, "role": role,
                    "race_id": "race", "election_date": "2026-06-23", "topic": "housing",
                    "subtopic": "public_housing", "stance": "support", "short_exact_quote": quote,
                    "locator": "candidate answer", "notes": "Fixture reviewed candidate answer.",
                })
                ballots.append({
                    "candidate_name": speaker, "state_code": "NY", "election_date": "2026-06-23",
                    "district": "01", "chamber": "House", "primary_party": "Democratic", "write_in": "false",
                })
            review = {
                "review_method": "assistant_source_review_not_independent_human_gold",
                "sources": sources, "excerpts": excerpts, "unsuccessful_sources": [],
                "source_attempts": [{
                    "candidate": "Other Democrat", "url": "https://example.gov/old",
                    "raw_path": "right.html", "outcome": "prior_lookup",
                }],
                "comparisons": [{
                    "comparison_id": "pair", "race_id": "race", "excerpt_ids": ["left", "right"],
                    "relationship": "shared_position", "interpretation": "Both support public housing.",
                }],
            }
            path = root / "review.json"
            path.write_text(json.dumps(review))
            races = {"race": {
                "scope_kind": "tracked_dsa_endorsed_democratic_primary", "state_code": "NY",
                "office": "US House",
                "jurisdiction": "District 1", "election_date": "2026-06-23",
                "endorsed_candidates": "", "endorsed_candidate": "Jane Example",
                "opponent_candidates": "Other Democrat",
            }}
            with patch("dsa_analysis.policy_comparison.ROOT", root):
                result = validated_supplemental_review(path, races, ballots, "2026-09-22")
            self.assertEqual(result["rows"], [])
            self.assertEqual(len(result["timing_unverified_rows"]), 1)
            self.assertEqual(len(result["statements"]), 1)
            self.assertEqual(result["timing_unverified_statements"][0]["quote"], "I support public housing.")
            self.assertEqual(result["timing_unverified_statements"][0]["publication_date"], "")
            self.assertEqual(result["timing_unverified_statements"][0]["capture_date"], "2026-06-24")
            self.assertEqual(result["timing_unverified_statements"][0]["temporal_evidence_date"], "")
            self.assertEqual(result["gaps"][0]["outcome"], "pre_primary_timing_unverified")
            self.assertEqual(result["attempts"][0]["race_id"], "race")
            self.assertEqual(result["attempts"][0]["attempted_url"], "https://example.gov/old")
            self.assertEqual(result["attempts"][0]["raw_path"], "right.html")

    def test_archive_capture_date_is_not_fabricated_publication_date(self):
        source = {
            "publication_date": None,
            "final_url": "https://web.archive.org/web/20260613064424id_/https://example.org/issues",
        }
        self.assertEqual(source_evidence_date(source, "2026-06-23", "2026-09-22"), (
            "2026-06-13", "2026-06-13",
        ))
        self.assertIsNone(source["publication_date"])
        with self.assertRaisesRegex(ValueError, "undated current source"):
            source_evidence_date(
                {**source, "final_url": "https://example.org/issues"}, "2026-06-23", "2026-09-22",
            )
        with self.assertRaisesRegex(ValueError, "postdates the research cutoff"):
            source_evidence_date(
                {**source, "publication_date": "2026-09-23"}, "2026-11-03", "2026-09-22",
            )

    def test_current_campaign_replay_keeps_the_older_original_publication_date(self):
        source = {
            "publication_date": "2018-01-22", "source_updated_date": "2020-01-20",
            "source_type": "official_campaign_platform",
            "version_timing_basis": "pre_primary_archived_campaign_platform",
            "final_url": "https://web.archive.org/web/20200204082527id_/https://example.org/issues",
        }
        self.assertEqual(source_evidence_date(source, "2020-02-11", "2026-09-22"), (
            "2020-02-04", "2020-02-04",
        ))
        self.assertEqual(source["publication_date"], "2018-01-22")
        for changes in (
            {"source_type": "candidate_interview"},
            {"final_url": "https://example.org/issues"},
            {"source_updated_date": "2020-03-01"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                source_evidence_date({**source, **changes}, "2020-02-11", "2026-09-22")

    def test_known_revision_is_not_backdated_to_original_publication(self):
        source = {
            "publication_date": "2019-04-16", "source_updated_date": "2020-01-20",
            "final_url": "https://example.org/issues",
        }
        self.assertEqual(source_evidence_date(source, "2020-02-11", "2026-09-22")[0], "2020-01-20")
        with self.assertRaisesRegex(ValueError, "campaign window"):
            source_evidence_date(source, "2020-01-10", "2026-09-22")

    def test_new_york_reviews_match_retained_quotes_and_actual_democratic_ballots(self):
        races = {row["race_id"]: row for row in read_csv(PROCESSED_DIR / "race_registry.csv")}
        ballots = read_csv(ANALYSIS_DATA_DIR / "congressional" / "state_primary_results.csv")
        bundle = validated_supplemental_review(
            MANUAL_DIR / "policy_ny_2026_review.json", races, ballots, "2026-09-22",
        )
        by_id = {row["comparison_id"]: row for row in bundle["rows"]}
        self.assertGreaterEqual(len(bundle["statements"]), 7)
        self.assertEqual(by_id["cmp-ny7-labor"]["relationship"], "shared_position")
        self.assertEqual(by_id["cmp-ny13-immigration"]["relationship"], "shared_position")
        self.assertEqual(by_id["cmp-ny14-immigration"]["relationship"], "different_emphasis")
        recovered = {(row["race_id"], row["speaker"]) for row in bundle["statements"]}
        self.assertTrue(all((row["race_id"], row["candidate"]) not in recovered for row in bundle["gaps"]))
        with self.assertRaisesRegex(ValueError, "ballot identity"):
            validated_supplemental_review(
                MANUAL_DIR / "policy_ny_2026_review.json", races, [], "2026-09-22",
            )

    def test_pennsylvania_aliases_are_explicit_and_illinois_comparators_are_complete(self):
        races = {row["race_id"]: row for row in read_csv(PROCESSED_DIR / "race_registry.csv")}
        ballots = read_csv(ANALYSIS_DATA_DIR / "congressional" / "state_primary_results.csv")
        path = MANUAL_DIR / "policy_pa_il_2026_review.json"
        bundle = validated_supplemental_review(path, races, ballots, "2026-09-22")
        statements = {row["speaker"]: row for row in bundle["statements"]}
        self.assertEqual(statements["Chris Rabb"]["identity_resolution"], "accepted_direct_official_alias")
        self.assertEqual(statements["Sharif Street"]["identity_resolution"], "accepted_contextual_official_alias")
        self.assertIn("cmp-il08-healthcare-right", {
            row["comparison_id"] for row in bundle["timing_unverified_rows"]
        })
        self.assertEqual(races["race-46743736b1d8a06d6eff"]["unopposed_candidates"], "")
        self.assertEqual(races["race-46743736b1d8a06d6eff"]["opponent_candidates"], "Sean Casten")
        self.assertEqual(int(races["race-b1a420450d32f5e0bd93"]["candidate_count"]), 8)
        review = json.loads(path.read_text())
        del review["identity_aliases"][0]["review_status"]
        with tempfile.TemporaryDirectory(dir=".") as directory:
            invalid = Path(directory) / "review.json"
            invalid.write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError, "explicit source review"):
                validated_supplemental_review(invalid, races, ballots, "2026-09-22")

    def test_followup_recovers_the_entire_illinois_8_field_without_backdating(self):
        races = {row["race_id"]: row for row in read_csv(PROCESSED_DIR / "race_registry.csv")}
        ballots = read_csv(ANALYSIS_DATA_DIR / "congressional" / "state_primary_results.csv")
        bundle = validated_supplemental_review(
            MANUAL_DIR / "policy_pa_il_2026_review.json", races, ballots, "2026-09-22",
        )
        recovered = bundle["statements"] + bundle["timing_unverified_statements"]
        names = {
            row["speaker"] for row in recovered if row["race_id"] == "race-b1a420450d32f5e0bd93"
        }
        self.assertEqual(names, set(races["race-b1a420450d32f5e0bd93"]["all_candidates"].split(" | ")))
        khot = next(row for row in bundle["statements"] if row["excerpt_id"] == "ex-il08-khot-aca-subsidies")
        self.assertEqual(khot["capture_date"], "2026-03-17")
        self.assertEqual(khot["publication_date"], "")
        ryan = next(row for row in bundle["timing_unverified_statements"] if row["speaker"] == "Ryan Vetticad")
        self.assertEqual(ryan["capture_date"], "2026-03-19")
        self.assertEqual(ryan["temporal_evidence_date"], "")

    def test_offline_ingestion_uses_jsonl_manifest_and_only_scoped_speaker_text(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory).resolve()
            manual = root / "manual"
            output = root / "analysis" / "policy_evidence"
            raw = root / "raw"
            raw.mkdir()
            body = b"<p>Interviewer: Tell us your policy.</p><p>Example: I support public housing.</p>"
            (raw / "interview.html").write_bytes(body)
            source = {
                "source_url": "https://example.org/interview", "final_url": "https://example.org/interview",
                "raw_path": "raw/interview.html", "sha256": hashlib.sha256(body).hexdigest(),
                "retrieved_at": "2026-05-20T12:00:00+00:00", "content_type": "text/html",
                "encoding": "utf-8",
            }
            write_csv(output / "source_manifest.csv", [source], list(source))
            document = {
                "candidate_document_id": "doc", "race_id": "race",
                "candidate_name": "Jane Example", "role": "endorsed", "election_date": "2026-06-16",
                "publication_date": "2026-05-18", "source_type": "candidate_interview",
                "source_url": source["source_url"], "analysis_scope": "candidate_excerpt",
                "locator": "paragraph 2",
            }
            write_csv(manual / "candidate_documents.csv", [document], list(document))
            paths = CandidateDocumentBatchPaths(
                queue_path=root / "queue.csv", raw_dir=raw, raw_manifest_path=root / "raw.jsonl",
                metadata_path=root / "metadata.csv", full_text_path=root / "full.jsonl",
                paragraph_path=root / "paragraphs.csv", sentence_path=root / "sentences.csv",
                analysis_segment_path=root / "segments.csv",
            )
            with (
                patch("dsa_analysis.policy_comparison.ROOT", root),
                patch("dsa_analysis.policy_comparison.MANUAL_DIR", manual),
                patch("dsa_analysis.policy_comparison.RAW_DIR", raw),
                patch("dsa_analysis.policy_comparison.ANALYSIS_DATA_DIR", root / "analysis"),
                patch("dsa_analysis.policy_comparison.export_policy_comparisons"),
                patch("dsa_analysis.policy_comparison.CandidateDocumentBatchPaths.default", return_value=paths),
            ):
                ingest_reviewed_documents()
                ingest_reviewed_documents()
            entries = [json.loads(line) for line in (output / "corpus_raw_manifest.jsonl").read_text().splitlines()]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["sha256"], source["sha256"])
            self.assertEqual([row["text"] for row in read_csv(paths.analysis_segment_path)], [
                "Example: I support public housing.",
            ])

    def test_current_undated_platform_cannot_be_projected_into_a_historical_cycle(self):
        comparison = {"cycle": "2020", "dsa_excerpt_id": "a", "democratic_excerpt_id": "b"}
        excerpts = {"a": {"document_id": "a"}, "b": {"document_id": "b"}}
        documents = {"a": {"publication_date": ""}, "b": {"publication_date": "2020-08-18"}}
        self.assertEqual(platform_pair_date_issues(comparison, excerpts, documents), ["dsa_source_date_unknown"])
        documents["a"]["publication_date"] = "2026-01-01"
        self.assertEqual(platform_pair_date_issues(comparison, excerpts, documents), ["dsa_source_postdates_comparison_cycle"])

    def test_reporter_or_interviewer_words_are_not_candidate_quotes(self):
        paragraphs = [
            SimpleNamespace(locator="paragraph 1", text="Warner: Do you support single payer?"),
            SimpleNamespace(locator="paragraph 2", text="The candidate discussed single payer."),
            SimpleNamespace(locator="paragraph 3", text="Example: I support single payer."),
        ]
        self.assertEqual(attributed_quote_locators(paragraphs, "Jane Example", "single payer"), ["paragraph 3"])
        self.assertEqual(attributed_quote_locators(paragraphs, "Jane Example", "Do you support"), [])

    def test_shared_position_requires_matching_policy_not_assumed_party_platform(self):
        race = {
            "scope_kind": "tracked_dsa_endorsed_democratic_primary",
            "endorsed_candidate": "Jane Example", "endorsed_candidates": "",
            "opponent_candidates": "Other Democrat",
        }
        left = {"speaker": "Jane Example", "topic": "healthcare", "subtopic": "single_payer",
                "stance": "support", "reviewed": "true"}
        right = {**left, "speaker": "Other Democrat"}
        validate_comparison({"relationship": "shared_position"}, left, right, race)
        with self.assertRaisesRegex(ValueError, "mechanism and stance"):
            validate_comparison(
                {"relationship": "shared_position"}, left,
                {**right, "subtopic": "public_option"}, race,
            )
        with self.assertRaisesRegex(ValueError, "same proposition"):
            validate_comparison(
                {"relationship": "explicit_disagreement"}, left,
                {**right, "subtopic": "public_option", "stance": "oppose"}, race,
            )
        with self.assertRaisesRegex(ValueError, "registry roles"):
            validate_comparison({"relationship": "shared_position"}, left, left, race)


if __name__ == "__main__":
    unittest.main()
