import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.national_claim_corpus import (
    MAX_CHUNK_WORDS,
    bounded_units,
    build_blocks,
    extract_corpus,
    prepare,
    validate_response,
)
from dsa_analysis.national_platforms import digest, read_rows, write_rows
from tests.test_national_claims import coverage, sources


def claim(**updates):
    return {
        "claim_text": (
            "Commitment to expand services for residents next year, rather than immediately, "
            "if funding is approved."
        ),
        "claim_types": ["policy_position"],
        "evidence_ids": [1],
        **updates,
    }


def response(**updates):
    return json.dumps({"claims": [claim(**updates)], "unresolved_references": []})


class ClaimCorpusTests(unittest.TestCase):
    def test_complete_source_is_chunked_with_hard_limit_and_exact_offsets(self):
        rows = sources()
        text = (
            "Yes.\n\n"
            + " ".join(f"Sentence {i} has several words." for i in range(250))
            + "\n\nNo."
        )
        for row in rows:
            row.update(
                scoped_text=text,
                complete_text=text,
                text_sha256=digest(text),
                complete_text_sha256=digest(text),
            )
        blocks = build_blocks(rows, coverage(rows))
        for source in rows:
            selected = [block for block in blocks if block["document_id"] == source["document_id"]]
            self.assertGreater(len(selected), 1)
            self.assertEqual(
                [word for block in selected for word in block["text"].split()], text.split()
            )
            covered_positions = []
            for block in selected:
                self.assertLessEqual(len(block["text"].split()), MAX_CHUNK_WORDS)
                self.assertLessEqual(len(block["context_before"]), 1200)
                self.assertEqual(text[block["source_start"] : block["source_end"]], block["text"])
                for unit in block["units"]:
                    self.assertEqual(text[unit["start"] : unit["end"]], unit["text"])
                    covered_positions.extend(
                        unit["start"] + match.start() for match in re.finditer(r"\S", unit["text"])
                    )
            self.assertEqual(
                covered_positions, [match.start() for match in re.finditer(r"\S", text)]
            )
        self.assertEqual(build_blocks(list(reversed(rows)), coverage(rows)), blocks)

    def test_long_sentence_word_boundary_fallback_and_short_assertions(self):
        text = "Yes.\n\n" + " ".join(f"word{i}" for i in range(971)) + "\n\nNo."
        units = bounded_units(text)
        self.assertEqual([word for unit in units for word in unit["text"].split()], text.split())
        self.assertTrue(all(len(unit["text"].split()) <= MAX_CHUNK_WORDS for unit in units))
        self.assertEqual(units[0]["text"], "Yes.")
        self.assertEqual(units[-1]["text"], "No.")
        with self.assertRaises(ValueError):
            bounded_units(text, 0)
        with self.assertRaises(ValueError):
            build_blocks(sources(), coverage(sources()), max_words=100)
        with self.assertRaisesRegex(ValueError, "sources missing"):
            build_blocks(sources()[1:], coverage(sources()))

    def test_qualifications_and_attribution_are_part_of_embedding_text(self):
        block = build_blocks(sources(), coverage(sources()))[0]
        accepted, errors, _ = validate_response(response(), block)
        self.assertEqual(errors, [])
        self.assertEqual(len(accepted), 1)
        row = accepted[0]
        self.assertIn("if funding is approved", row["claim_text"])
        self.assertIn("next year, rather than immediately", row["claim_text"])
        testimony, errors, _ = validate_response(
            response(
                claim_text="Judith Smith says the Affordable Care Act saved Judith Smith's life."
            ),
            block,
        )
        self.assertEqual(errors, [])
        self.assertIn("Judith Smith says", testimony[0]["claim_text"])
        start = row["source_start"] - block["source_start"]
        self.assertEqual(block["text"][start : start + len(row["evidence"])], row["evidence"])
        self.assertNotEqual(row["claim_text"], row["evidence"])

    def test_schema_reference_and_actor_failures_are_explicit(self):
        block = build_blocks(sources(), coverage(sources()))[0]
        invalid = [
            "not JSON",
            "[]",
            response(evidence_ids=[99]),
            response(evidence_ids=[True]),
            response(claim_text="We will expand services"),
            response(claim_text="The document will expand services"),
            response(claim_text="These will expand services"),
            response(claim_types=["ideology"]),
            response(extra_field="none"),
        ]
        for text in invalid:
            with self.subTest(text=text):
                self.assertTrue(validate_response(text, block)[1])
        payload = json.loads(response())
        payload["claims"] *= 2
        self.assertTrue(validate_response(json.dumps(payload), block)[1])

    def test_resume_retries_complete_download_and_baseline_isolation(self):
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary) / "baseline"
            corpus.mkdir()
            output = Path(temporary) / "claims"
            rows = sources()
            write_rows(corpus / "complete_sources.csv", rows)
            write_rows(corpus / "coverage.csv", coverage(rows))
            baseline = {path.name: path.read_bytes() for path in corpus.iterdir()}
            calls = []

            def extractor(prompt, max_tokens):
                calls.append(prompt)
                return {
                    "text": "invalid" if len(calls) == 1 else response(),
                    "seconds": 0.1,
                    "generation_tokens": 25,
                    "peak_memory": 1,
                }

            summary = extract_corpus(output=output, corpus=corpus, extractor=extractor)
            self.assertEqual(summary["status"], "complete")
            self.assertEqual(len(calls), 2 * summary["blocks"] + 1)
            self.assertEqual(baseline, {path.name: path.read_bytes() for path in corpus.iterdir()})
            with zipfile.ZipFile(output / "claim_documents.zip") as archive:
                self.assertIn("complete_sources.csv", archive.namelist())
                self.assertIn("claims.csv", archive.namelist())
                recovered = archive.read("complete_sources.csv").decode()
                self.assertIn("We support universal care.", recovered)
            before = (output / "claim_documents.zip").read_bytes()
            with patch(
                "dsa_analysis.national_claim_corpus.LocalGemma",
                side_effect=AssertionError("cached replay must not initialize a model"),
            ):
                extract_corpus(output=output, corpus=corpus)
            self.assertEqual(before, (output / "claim_documents.zip").read_bytes())
            identifier = read_rows(output / "claims.csv")[0]["block_id"]
            write_rows(
                output / "semantic_review.csv",
                [
                    {
                        "block_id": identifier,
                        "review_status": "issues_found",
                        "flagged_claim_numbers": "1",
                    }
                ],
            )
            with patch(
                "dsa_analysis.national_claim_corpus.LocalGemma",
                side_effect=AssertionError("review updates must reuse raw inference"),
            ):
                reviewed = extract_corpus(output=output, corpus=corpus)
            self.assertEqual(reviewed["assistant_flagged_claims"], 1)
            self.assertEqual(reviewed["analysis_claims"], summary["analysis_claims"] - 1)
            cached = next((output / "responses").glob("*.json"))
            record = json.loads(cached.read_text())
            record["fingerprint"] = "stale"
            cached.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "Stale"):
                extract_corpus(output=output, corpus=corpus)
            with self.assertRaisesRegex(ValueError, "separate"):
                prepare(corpus, corpus)

    def test_failed_and_token_capped_blocks_are_not_analysis_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary) / "baseline"
            corpus.mkdir()
            output = Path(temporary) / "claims"
            rows = sources()
            write_rows(corpus / "complete_sources.csv", rows)
            write_rows(corpus / "coverage.csv", coverage(rows))

            def extractor(prompt, max_tokens):
                return {
                    "text": response(),
                    "generation_tokens": max_tokens,
                    "seconds": 0.1,
                    "peak_memory": 1,
                }

            summary = extract_corpus(output=output, corpus=corpus, extractor=extractor)
            self.assertEqual(summary["status"], "complete_with_exclusions")
            self.assertEqual(summary["claims"], 0)
            self.assertEqual(read_rows(output / "claims.csv"), [])
            self.assertTrue(
                all(
                    row["status"] == "validation_failed"
                    for row in read_rows(output / "block_status.csv")
                )
            )


if __name__ == "__main__":
    unittest.main()
