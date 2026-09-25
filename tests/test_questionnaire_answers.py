import hashlib
import json
import tempfile
import unittest
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.document_corpus import CandidateDocumentBatchPaths, TextSegment
from dsa_analysis.historical_policy import REVIEW_METHOD
from dsa_analysis.io import read_csv, write_csv
from dsa_analysis.questionnaire_answers import (
    _candidate_heading_name, build_questionnaire_answers, match_answers,
    render_questionnaires, split_answers,
)


class CompleteQuestionnaireTests(unittest.TestCase):
    def test_publisher_democratic_party_suffix_is_not_a_different_person(self):
        self.assertEqual(_candidate_heading_name("Lesley Lopez (D)"), "Lesley Lopez")
        self.assertEqual(_candidate_heading_name("Francesca Hong:"), "Francesca Hong")
        self.assertEqual(_candidate_heading_name("Another Person (D)"), "Another Person")
        self.assertEqual(_candidate_heading_name("Unreviewed (R)"), "Unreviewed (R)")

    def setUp(self):
        texts = [
            "Publisher navigation", "1. What is your priority?", "Housing.", "And transit.",
            "2) What about health?", "Universal coverage.", "Subscribe now", "Publisher biography",
        ]
        self.paragraphs = tuple(
            TextSegment(str(i), "source", "paragraph", i, f"paragraph {i}", text, "")
            for i, text in enumerate(texts, 1)
        )
        self.document = {"question_paragraphs": [2, 5], "end_paragraph": 7, "end_marker": "Subscribe now"}
        self.questions = [
            {"id": "q1", "topic": "priorities", "prompt": "What is your priority?"},
            {"id": "q2", "topic": "health", "prompt": "What about health?"},
        ]

    def test_complete_answers_exclude_prompts_and_footer(self):
        rows = split_answers(self.paragraphs, self.document, self.questions)
        self.assertEqual([r["complete_answer"] for r in rows], ["Housing.\n\nAnd transit.", "Universal coverage."])
        self.assertEqual(rows[0]["answer_locator"], "paragraphs 3-4")
        self.assertEqual(rows[-1]["original_question"], "2) What about health?")

    def test_changed_or_partial_boundaries_fail(self):
        for changes in (
            {"question_paragraphs": [2]},
            {"question_paragraphs": [5, 2]},
            {"question_paragraphs": [2, 2]},
            {"end_paragraph": 8},
            {"end_marker": "Missing footer"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                split_answers(self.paragraphs, {**self.document, **changes}, self.questions)
        with self.assertRaisesRegex(ValueError, "missing paragraph"):
            split_answers(tuple(p for p in self.paragraphs if p.index != 4), self.document, self.questions)

    def test_changed_question_and_empty_response_fail(self):
        questions = deepcopy(self.questions)
        questions[1]["prompt"] = "A different question?"
        with self.assertRaisesRegex(ValueError, "prompt differs"):
            split_answers(self.paragraphs, self.document, questions)
        with self.assertRaisesRegex(ValueError, "empty"):
            split_answers(self.paragraphs, {**self.document, "end_paragraph": 6, "end_marker": "Universal coverage."}, self.questions)

    def test_explicit_prompt_variant_and_caveat_preserved(self):
        questions = deepcopy(self.questions)
        questions[1]["prompt"] = "Different canonical phrasing?"
        questions[1]["variants"] = ["What about health?"]
        document = {**self.document, "answer_caveats": {"q2": "Source ambiguity retained."}}
        rows = split_answers(self.paragraphs, document, questions)
        self.assertEqual(rows[1]["review_caveat"], "Source ambiguity retained.")
        self.assertEqual(rows[1]["original_question"], "2) What about health?")

    def test_unnumbered_questions_require_exact_reviewed_prompt(self):
        questions = [{**q, "numbered": False} for q in self.questions]
        paragraphs = tuple(
            TextSegment(p.segment_id, p.document_id, p.segment_kind, p.index, p.locator,
                        p.text.removeprefix("1. ").removeprefix("2) "), p.sha256)
            for p in self.paragraphs
        )
        rows = split_answers(paragraphs, self.document, questions)
        self.assertEqual(rows[0]["original_question"], "What is your priority?")
        self.assertEqual(rows[1]["complete_answer"], "Universal coverage.")

    def test_interleaved_answers_cannot_capture_another_speaker(self):
        from dataclasses import replace
        paragraphs = tuple(replace(p, text="Other: " + p.text) if p.index == 3 else
                           replace(p, text="Focal: " + p.text) if p.index in {4, 6} else p
                           for p in self.paragraphs)
        document = {**self.document, "answer_paragraphs": [4, 6], "speaker_prefixes": ["Focal:"]}
        rows = split_answers(paragraphs, document, self.questions)
        self.assertEqual(rows[0]["complete_answer"], "Focal: And transit.")
        self.assertEqual(rows[0]["answer_locator"], "paragraph 4")
        with self.assertRaisesRegex(ValueError, "reviewed speaker"):
            split_answers(paragraphs, {**document, "answer_paragraphs": [3, 6]}, self.questions)
        with self.assertRaisesRegex(ValueError, "question boundaries"):
            split_answers(paragraphs, {**document, "answer_paragraphs": [6, 4]}, self.questions)
        with self.assertRaisesRegex(ValueError, "speaker prefixes"):
            split_answers(paragraphs, {**document, "speaker_prefixes": [""]}, self.questions)

    def test_nonpolicy_and_ambiguous_answers_remain_in_complete_exports(self):
        questions = deepcopy(self.questions)
        questions[1]["include_in_policy_corpus"] = False
        document = {**self.document, "analysis_excluded_questions": {"q1": "attribution_requires_review"}}
        rows = split_answers(self.paragraphs, document, questions)
        self.assertEqual(rows[0]["corpus_exclusion_reason"], "attribution_requires_review")
        self.assertEqual(rows[1]["corpus_exclusion_reason"], "nonpolicy_question")
        self.assertEqual(rows[1]["complete_answer"], "Universal coverage.")
        self.assertEqual(rows[1]["question_scope"], "nonpolicy_context")
        with self.assertRaisesRegex(ValueError, "nonempty reasons"):
            split_answers(self.paragraphs, {**self.document, "analysis_excluded_questions": {"q1": ""}}, self.questions)

    def test_shared_question_ranges_are_bound_to_the_named_candidate_section(self):
        texts = ["What are your priorities?", "Focal", "Housing.", "Public schools.", "Other", "Transport.", "End"]
        paragraphs = tuple(
            TextSegment(str(i), "source", "paragraph", i, f"paragraph {i}", text, "")
            for i, text in enumerate(texts, 1)
        )
        questions = [{"id": "q1", "topic": "priorities", "prompt": texts[0], "numbered": False}]
        document = {
            "question_paragraphs": [1], "answer_ranges": [[3, 4]],
            "candidate_heading": {"paragraph": 2, "text": "Focal"},
            "end_paragraph": 5, "end_marker": "Other",
        }
        rows = split_answers(paragraphs, document, questions)
        self.assertEqual(rows[0]["complete_answer"], "Housing.\n\nPublic schools.")
        self.assertEqual(rows[0]["answer_locator"], "paragraphs 3-4")
        with self.assertRaisesRegex(ValueError, "candidate heading"):
            split_answers(paragraphs, {**document, "candidate_heading": {"paragraph": 5, "text": "Focal"}}, questions)
        with self.assertRaisesRegex(ValueError, "question boundaries"):
            split_answers(paragraphs, {**document, "answer_ranges": [[3, 6]]}, questions)
        with self.assertRaisesRegex(ValueError, "complete ranges"):
            split_answers(paragraphs, {**document, "answer_ranges": [[4, 3]]}, questions)

    def test_each_transcript_round_binds_its_own_speaker_heading(self):
        texts = [
            "Housing?", "Focal:", "Build homes.", "Other:", "Fund shelters.",
            "Schools?", "Focal:", "Fund schools.", "Other:", "Close schools.", "End",
        ]
        paragraphs = tuple(
            TextSegment(str(i), "source", "paragraph", i, f"paragraph {i}", text, "")
            for i, text in enumerate(texts, 1)
        )
        questions = [
            {"id": "housing", "topic": "housing", "prompt": "Housing?", "numbered": False},
            {"id": "schools", "topic": "education", "prompt": "Schools?", "numbered": False},
        ]
        document = {
            "question_paragraphs": [1, 6], "answer_ranges": [[3, 3], [8, 8]],
            "candidate_heading": {"paragraph": 2, "text": "Focal:"},
            "answer_headings": [{"paragraph": 2, "text": "Focal:"}, {"paragraph": 7, "text": "Focal:"}],
            "end_paragraph": 11, "end_marker": "End",
        }
        self.assertEqual(
            [r["complete_answer"] for r in split_answers(paragraphs, document, questions)],
            ["Build homes.", "Fund schools."],
        )
        with self.assertRaisesRegex(ValueError, "immediately follow"):
            split_answers(paragraphs, {**document, "answer_ranges": [[3, 3], [10, 10]]}, questions)
        with self.assertRaisesRegex(ValueError, "complete named answer ranges"):
            split_answers(paragraphs, {**document, "answer_headings": []}, questions)

    def test_interleaved_multi_paragraph_answers_cannot_include_another_candidate(self):
        texts = ["What are your priorities?", "Focal: Housing.", "And schools.", "Other: Transit.", "End"]
        paragraphs = tuple(
            TextSegment(str(i), "source", "paragraph", i, f"paragraph {i}", text, "")
            for i, text in enumerate(texts, 1)
        )
        questions = [{"id": "q1", "topic": "priorities", "prompt": texts[0], "numbered": False}]
        document = {
            "question_paragraphs": [1], "answer_ranges": [[2, 3]],
            "speaker_prefixes": ["Focal:"], "all_speaker_prefixes": ["Focal:", "Other:"],
            "end_paragraph": 5, "end_marker": "End",
        }
        self.assertEqual(
            split_answers(paragraphs, document, questions)[0]["complete_answer"],
            "Focal: Housing.\n\nAnd schools.",
        )
        with self.assertRaisesRegex(ValueError, "another candidate"):
            split_answers(paragraphs, {**document, "answer_ranges": [[2, 4]]}, questions)
        with self.assertRaisesRegex(ValueError, "reviewed speaker"):
            split_answers(paragraphs, {**document, "answer_ranges": [[4, 4]]}, questions)

    def test_exact_publisher_ad_is_removed_without_losing_answer_text(self):
        texts = ["What would you do?", "Fund schools.", "Subscribe now.", "Build housing.", "End"]
        paragraphs = tuple(
            TextSegment(str(i), "source", "paragraph", i, f"paragraph {i}", text, "")
            for i, text in enumerate(texts, 1)
        )
        document = {
            "question_paragraphs": [1], "end_paragraph": 5, "end_marker": "End",
            "noncandidate_paragraphs": [{"paragraph": 3, "exact_text": "Subscribe now.", "reason": "Publisher advertisement."}],
        }
        questions = [{"id": "q1", "topic": "priorities", "prompt": texts[0], "numbered": False}]
        answer = split_answers(paragraphs, document, questions)[0]
        self.assertEqual(answer["complete_answer"], "Fund schools.\n\nBuild housing.")
        self.assertEqual(answer["answer_locator"], "paragraph 2 | paragraph 4")
        self.assertIn("paragraph 3", answer["excluded_publisher_paragraphs"])
        with self.assertRaisesRegex(ValueError, "exact reviewed"):
            split_answers(paragraphs, {**document, "noncandidate_paragraphs": [
                {"paragraph": 3, "exact_text": "A different ad.", "reason": "Publisher advertisement."},
            ]}, questions)
        with self.assertRaisesRegex(ValueError, "exact reviewed"):
            split_answers(paragraphs, {**document, "noncandidate_paragraphs": [
                {"paragraph": 1, "exact_text": texts[0], "reason": "Not actually an ad."},
            ]}, questions)

    def _rows(self):
        answer = split_answers(self.paragraphs, self.document, self.questions)[0]
        return [{
            **answer, "bundle_id": "b", "race_id": "r", "candidate_name": name, "role": role,
            "source_url": "https://example.org/source", "timing_status": "pre_primary_supported",
        } for name, role in [("Focal", "endorsed"), ("Other", "opponent")]]

    def test_matching_question_does_not_infer_agreement(self):
        pairs = match_answers(self._rows())
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["relationship"], "same_question_not_stance_classified")
        self.assertEqual(pairs[0]["other_complete_answer"], "Housing.\n\nAnd transit.")
        self.assertIn("other_answer_sha256", pairs[0])
        with self.assertRaisesRegex(ValueError, "Repeated"):
            match_answers(self._rows() + self._rows())

    def test_edited_topic_round_is_not_mislabeled_as_an_identical_question(self):
        rows = self._rows()
        for row in rows:
            row["pairing_basis"] = "shared_published_topic_round"
        [pair] = match_answers(rows)
        self.assertEqual(pair["relationship"], "shared_topic_not_stance_classified")
        self.assertIn("not proof of identical", pair["interpretation_limit"])
        rows[1]["pairing_basis"] = "same_published_question"
        with self.assertRaisesRegex(ValueError, "pairing basis"):
            match_answers(rows)

    def test_pairs_cannot_cross_races_or_bundles(self):
        for field in ("bundle_id", "race_id", "question_id"):
            rows = self._rows()
            rows[1][field] = "different"
            self.assertEqual(match_answers(rows), [])

    def test_browser_escapes_answers_and_preserves_missing_candidates(self):
        rows = self._rows()
        rows[0]["complete_answer"] = "<script>alert(1)</script>"
        coverage = [{"bundle_id": "b", "title": "Race", "coverage_note": "Incomplete field.",
                     "missing_registry_candidates": ["Missing"]}]
        page = render_questionnaires(rows, coverage)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn("<script>alert(1)", page)
        self.assertIn("Missing", page)
        self.assertIn("DSA-endorsed", page)
        self.assertIn("Other Democrat", page)
        rows[0]["source_url"] = "javascript:alert(1)"
        with self.assertRaisesRegex(ValueError, "HTTP"):
            render_questionnaires(rows, coverage)

    def test_browser_does_not_silently_relabel_unknown_roles(self):
        rows = self._rows()
        rows[0]["role"] = "unknown"
        coverage = [{"bundle_id": "b", "title": "Race", "coverage_note": "Incomplete field.",
                     "missing_registry_candidates": []}]
        with self.assertRaisesRegex(ValueError, "comparison roles"):
            render_questionnaires(rows, coverage)

    def _fixture(self, root, *, timing_supported=True):
        body = b"<p>1. Priorities?</p><p>Public housing and affordable transport.</p><p>Subscribe</p>"
        (root / "source.html").write_bytes(body)
        (root / "report").mkdir()
        race = {
            "race_id": "r", "scope_kind": "tracked_dsa_endorsed_democratic_primary",
            "election_date": "2020-06-01", "endorsed_candidate": "Focal", "endorsed_candidates": "Focal",
            "all_candidates": "Focal | Other",
        }
        write_csv(root / "race_registry.csv", [race], list(race))
        write_csv(root / "candidate_document_metadata.csv",
                  [{"document_id": "quote-only", "analysis_scope": "reviewed_quote"}],
                  ["document_id", "analysis_scope"])
        source = {
            "document_id": "source", "url": "https://example.org/qa", "final_url": "https://example.org/qa",
            "publication_date": "2020-05-01" if timing_supported else None,
            "retrieved_at": "2026-09-23", "raw_path": "source.html",
            "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "content_type": "text/html",
            "status": "used" if timing_supported else "timing_unverified",
            "notes": "Publication date unknown." if not timing_supported else "Reviewed original source.",
        }
        review = {
            "review_method": REVIEW_METHOD, "sources": [source],
            "excerpts": [{"document_id": "source", "speaker": "Focal", "race_id": "r",
                          "election_date": "2020-06-01", "role": "endorsed_candidate"}],
        }
        config = {"review_method": REVIEW_METHOD, "bundles": [{
            "id": "b", "title": "Race", "race_id": "r", "review_path": "review.json", "coverage_note": "One candidate.",
            "questions": [{"id": "q1", "topic": "priorities", "prompt": "Priorities?"}],
            "documents": [{"source_id": "source", "candidate_name": "Focal", "question_paragraphs": [1],
                           "end_paragraph": 3, "end_marker": "Subscribe"}],
        }]}
        (root / "review.json").write_text(json.dumps(review))
        (root / "sources.json").write_text(json.dumps({"research_cutoff": "2026-09-22"}))
        (root / "policy_complete_questionnaires.json").write_text(json.dumps(config))
        return CandidateDocumentBatchPaths(
            root / "queue.csv", root / "raw", root / "manifest.jsonl", root / "candidate_document_metadata.csv",
            root / "full_text.jsonl", root / "paragraphs.csv", root / "sentences.csv", root / "segments.csv",
        )

    def _patched_paths(self, root, paths):
        stack = ExitStack()
        for name in ("ROOT", "MANUAL_DIR", "PROCESSED_DIR", "CONFIG_DIR", "ANALYSIS_DATA_DIR"):
            stack.enter_context(patch("dsa_analysis.questionnaire_answers." + name, root))
        stack.enter_context(patch("dsa_analysis.document_corpus.ROOT", root))
        stack.enter_context(patch("dsa_analysis.questionnaire_answers.CandidateDocumentBatchPaths.default", return_value=paths))
        return stack

    def test_enrollment_replays_bytes_and_preserves_quote_only_records(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = self._fixture(root)
            with self._patched_paths(root, paths):
                first = build_questionnaire_answers()
                second = build_questionnaire_answers()
            self.assertEqual(first, second)
            self.assertEqual(first["enrolled_timing_supported_documents"], 1)
            metadata = {r["document_id"]: r for r in read_csv(paths.metadata_path)}
            self.assertEqual(len(metadata), 2)
            self.assertEqual(metadata["quote-only"]["analysis_scope"], "reviewed_quote")
            self.assertEqual([p["text"] for p in read_csv(paths.paragraph_path)], ["Public housing and affordable transport."])

    def test_timing_qualified_full_answers_are_downloadable_but_not_enrolled(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = self._fixture(root, timing_supported=False)
            with self._patched_paths(root, paths):
                summary = build_questionnaire_answers()
            self.assertEqual(summary["enrolled_timing_supported_documents"], 0)
            self.assertEqual(summary["timing_qualified_documents_not_enrolled"], 1)
            rows = read_csv(root / "policy_evidence/complete_questionnaires/complete_candidate_answers.csv")
            self.assertEqual(rows[0]["complete_answer"], "Public housing and affordable transport.")
            self.assertEqual(rows[0]["metadata_document_id"], "")
            self.assertEqual(read_csv(paths.analysis_segment_path), [])

    def test_publisher_exclusion_survives_actual_corpus_enrollment(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = self._fixture(root)
            body = (
                b"<p>1. Priorities?</p><p>Public housing and affordable transport.</p>"
                b"<p>Subscribe to our newsletter.</p><p>Fund schools and health clinics.</p><p>Subscribe</p>"
            )
            (root / "source.html").write_bytes(body)
            review = json.loads((root / "review.json").read_text())
            review["sources"][0].update(sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))
            (root / "review.json").write_text(json.dumps(review))
            config = json.loads((root / "policy_complete_questionnaires.json").read_text())
            config["bundles"][0]["documents"][0].update(
                end_paragraph=5,
                noncandidate_paragraphs=[{
                    "paragraph": 3, "exact_text": "Subscribe to our newsletter.", "reason": "Publisher insertion.",
                }],
            )
            (root / "policy_complete_questionnaires.json").write_text(json.dumps(config))
            with self._patched_paths(root, paths):
                result = build_questionnaire_answers()
            self.assertEqual(result["enrolled_timing_supported_documents"], 1)
            self.assertEqual(
                [row["text"] for row in read_csv(paths.paragraph_path)],
                ["Public housing and affordable transport.", "Fund schools and health clinics."],
            )
            answers = read_csv(root / "policy_evidence/complete_questionnaires/complete_candidate_answers.csv")
            self.assertEqual(answers[0]["answer_locator"], "paragraph 2 | paragraph 4")
            self.assertNotIn("newsletter", answers[0]["complete_answer"])

    def test_source_tampering_fails_before_enrollment(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = self._fixture(root)
            (root / "source.html").write_text("<p>A silently replaced page.</p>")
            with self._patched_paths(root, paths), self.assertRaisesRegex(ValueError, "byte/hash"):
                build_questionnaire_answers()
            self.assertEqual(len(read_csv(paths.metadata_path)), 1)

    def test_nonpolicy_response_is_not_enrolled_even_with_verified_timing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = self._fixture(root)
            config_path = root / "policy_complete_questionnaires.json"
            config = json.loads(config_path.read_text())
            config["bundles"][0]["questions"][0]["include_in_policy_corpus"] = False
            config_path.write_text(json.dumps(config))
            with self._patched_paths(root, paths):
                summary = build_questionnaire_answers()
            self.assertEqual(summary["complete_answer_rows"], 1)
            self.assertEqual(summary["nonpolicy_answer_rows"], 1)
            self.assertEqual(summary["enrolled_timing_supported_documents"], 0)
            self.assertEqual(summary["timing_qualified_documents_not_enrolled"], 0)
            self.assertEqual(read_csv(paths.analysis_segment_path), [])

    def test_removed_enrollment_cannot_silently_leave_old_model_text(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = self._fixture(root)
            with self._patched_paths(root, paths):
                build_questionnaire_answers()
                manifest_path = root / "policy_evidence/complete_questionnaires/raw_manifest.jsonl"
                before = manifest_path.read_bytes()
                manifest_path.write_bytes(before + b'{"document_id":"previously-enrolled"}\n')
                with self.assertRaisesRegex(ValueError, "removed or rekeyed"):
                    build_questionnaire_answers()
                self.assertEqual(manifest_path.read_bytes(), before + b'{"document_id":"previously-enrolled"}\n')


if __name__ == "__main__":
    unittest.main()
