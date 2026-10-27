import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.national_claims import (
    LocalGemma,
    prepare,
    run,
    select_blocks,
    validate_response,
)
from dsa_analysis.national_platforms import GROUPS, digest, read_rows, write_rows


def sources():
    rows = []
    for group in GROUPS:
        for year in (2000, 2024):
            paragraph = (
                "We support universal care. We do not support premiums. "
                "If funding is approved, the proposal would expand services for "
                "residents next year, rather than immediately, and would retain "
                "existing options while the new services are introduced to the public."
            )
            text = f"HEALTH CARE\n\n{paragraph}\n\n{paragraph} Additional context."
            rows.append(
                {
                    "document_id": f"{group}-{year}",
                    "group": group,
                    "document_type": "platform",
                    "publication_date": str(year),
                    "title": f"{group} platform",
                    "source_url": "https://example.test",
                    "sha256": digest(f"capture-{group}-{year}"),
                    "scoped_text": text,
                    "complete_text": text,
                    "text_sha256": digest(text),
                    "complete_text_sha256": digest(text),
                    "duplicate_of": "",
                    "bundle_id": "",
                }
            )
    return rows


def coverage(rows):
    return [
        {"document_id": row["document_id"], "status": "eligible", "text_sha256": row["text_sha256"]}
        for row in rows
    ]


def response(block):
    return json.dumps(
        {
            "claims": [
                {
                    "claim_text": "The document supports universal care.",
                    "claim_types": ["policy_position"],
                    "evidence": "We support universal care.",
                }
            ],
            "unresolved_references": [],
        }
    )


class ClaimPilotTests(unittest.TestCase):
    def test_balanced_deterministic_sampling_and_source_offsets(self):
        rows = sources()
        selected = select_blocks(rows, coverage(rows), 2)
        self.assertEqual(selected, select_blocks(list(reversed(rows)), coverage(rows), 2))
        self.assertEqual([row["group"] for row in selected], list(GROUPS) * 2)
        by_id = {row["document_id"]: row for row in rows}
        for block in selected:
            text = by_id[block["document_id"]]["scoped_text"]
            self.assertEqual(text[block["source_start"] : block["source_end"]], block["text"])
            self.assertEqual(
                text[block["context_start"] : block["context_end"]], block["context_before"]
            )
        self.assertEqual({row["publication_date"] for row in selected}, {"2000", "2024"})
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            select_blocks(rows, coverage(rows), 100)

    def test_exclusion_and_source_hash_validation(self):
        rows = sources()
        screened = coverage(rows)
        screened[0]["status"] = "reused_document"
        blocks = select_blocks(rows, screened, 1)
        self.assertNotIn(rows[0]["document_id"], {row["document_id"] for row in blocks})
        rows[1]["scoped_text"] += "tampered"
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            select_blocks(rows, screened, 1)
        rows = sources()
        rows[0]["document_id"] = "../outside"
        with self.assertRaisesRegex(ValueError, "Unsafe source"):
            select_blocks(rows, coverage(rows), 1)

    def test_short_claims_are_retained_with_exact_source_offsets(self):
        block = select_blocks(sources(), coverage(sources()), 1)[0]
        accepted, errors, unresolved = validate_response(response(block), block)
        self.assertEqual(errors, [])
        self.assertEqual(unresolved, [])
        self.assertEqual(len(accepted), 1)
        self.assertLess(len(accepted[0]["claim_text"].split()), 8)
        self.assertFalse(accepted[0]["analysis_eligible"])
        fenced = f"```json\n{response(block)}\n```"
        self.assertEqual(validate_response(fenced, block)[0], accepted)
        offset = accepted[0]["source_start"] - block["source_start"]
        self.assertEqual(
            block["text"][offset : offset + len(accepted[0]["evidence"])], accepted[0]["evidence"]
        )

    def test_malformed_and_unsupported_claims_are_not_silently_accepted(self):
        block = select_blocks(sources(), coverage(sources()), 1)[0]
        for text in ("not JSON", "[]", '{"claims":[]}', '{"claims":null}'):
            self.assertTrue(validate_response(text, block)[1])
        payload = json.loads(response(block))
        payload["claims"][0]["evidence"] = "Invented quotation"
        self.assertEqual(validate_response(json.dumps(payload), block)[0], [])
        payload = json.loads(response(block))
        payload["claims"][0]["claim_types"] = ["ideology"]
        self.assertTrue(validate_response(json.dumps(payload), block)[1])
        payload = json.loads(response(block))
        payload["claims"] *= 2
        self.assertEqual(len(validate_response(json.dumps(payload), block)[0]), 1)
        self.assertIn("duplicate_claim", validate_response(json.dumps(payload), block)[1][0])

    def test_cache_resume_full_download_and_configuration_invalidation(self):
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary) / "corpus"
            corpus.mkdir()
            output = Path(temporary) / "pilot"
            rows = sources()
            write_rows(corpus / "complete_sources.csv", rows)
            write_rows(corpus / "coverage.csv", coverage(rows))
            baseline = {path.name: path.read_bytes() for path in corpus.iterdir()}
            blocks, _ = prepare(corpus, output, 1, 2048)
            calls = []

            def extract(prompt, max_tokens):
                block = next(block for block in blocks if block["text"] in prompt)
                calls.append(prompt)
                return {
                    "text": response(block),
                    "seconds": 1.0,
                    "generation_tokens": 40,
                    "peak_memory": 2.0,
                }

            first = run(
                corpus=corpus, output=output, per_group=1, max_tokens=2048, extractor=extract
            )
            archive_before = (output / "pilot_documents.zip").read_bytes()
            self.assertEqual(len(calls), 3)
            with patch.object(LocalGemma, "__init__", side_effect=AssertionError("not offline")):
                second = run(corpus=corpus, output=output, per_group=1, max_tokens=2048)
            self.assertEqual(first, second)
            self.assertEqual(archive_before, (output / "pilot_documents.zip").read_bytes())
            self.assertEqual(first["claims"], 3)
            self.assertEqual(baseline, {path.name: path.read_bytes() for path in corpus.iterdir()})
            with zipfile.ZipFile(output / "pilot_documents.zip") as archive:
                self.assertIn("complete_sources.csv", archive.namelist())
                self.assertIn(
                    "We support universal care.", archive.read("complete_sources.csv").decode()
                )
            self.assertEqual(len(read_rows(output / "claims.csv")), 3)
            write_rows(
                output / "semantic_review.csv",
                [
                    {
                        "block_id": blocks[0]["block_id"],
                        "review_status": "issues_found",
                        "flagged_claim_numbers": "1",
                        "notes": "Example fidelity issue, not a truth judgment",
                    },
                    {
                        "block_id": blocks[1]["block_id"],
                        "review_status": "no_issue_observed",
                        "flagged_claim_numbers": "",
                        "notes": "No fidelity issue observed",
                    },
                ],
            )
            reviewed = run(corpus=corpus, output=output, per_group=1, max_tokens=2048)
            self.assertEqual(reviewed["blocks_semantically_reviewed"], 2)
            self.assertEqual(reviewed["candidate_claims_flagged_in_review"], 1)
            self.assertEqual(
                reviewed["blocks_by_status"],
                {
                    "reviewed_issues_found": 1,
                    "reviewed_no_issue_observed": 1,
                    "pending_semantic_review": 1,
                },
            )
            self.assertTrue(
                all(row["analysis_eligible"] == "False" for row in read_rows(output / "claims.csv"))
            )
            with self.assertRaisesRegex(ValueError, "configuration"):
                prepare(corpus, output, 1, 1024)
            with self.assertRaisesRegex(ValueError, "separate"):
                prepare(corpus, corpus, 1, 2048)
            path = next((output / "responses").glob("*.json"))
            record = json.loads(path.read_text())
            record["prompt_sha256"] = "stale"
            path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "Stale response"):
                run(corpus=corpus, output=output, per_group=1, max_tokens=2048)

    def test_token_limit_is_reported_even_when_json_is_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            corpus, output = Path(temporary) / "corpus", Path(temporary) / "pilot"
            corpus.mkdir()
            rows = sources()
            write_rows(corpus / "complete_sources.csv", rows)
            write_rows(corpus / "coverage.csv", coverage(rows))
            blocks, _ = prepare(corpus, output, 1, 10)

            def extract(prompt, max_tokens):
                return {
                    "text": response(blocks[0]),
                    "seconds": 1.0,
                    "generation_tokens": 10,
                    "peak_memory": 2.0,
                }

            summary = run(
                corpus=corpus, output=output, per_group=1, max_tokens=10, extractor=extract
            )
            self.assertEqual(summary["blocks_by_status"], {"validation_failed": 3})


if __name__ == "__main__":
    unittest.main()
