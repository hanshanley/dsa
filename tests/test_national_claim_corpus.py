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
    load_source_repairs,
    make_prompt,
    prepare,
    repair_request,
    source_repair_basis,
    standardize_stance,
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
    def test_libertarian_blocks_and_stance_do_not_require_other_parties(self):
        original = sources()[:1]
        libertarian = [
            {
                **original[0],
                "document_id": "libertarian-2022",
                "group": "libertarian",
            }
        ]
        blocks = build_blocks(libertarian, coverage(libertarian))
        self.assertTrue(blocks)
        self.assertEqual({block["group"] for block in blocks}, {"libertarian"})
        self.assertEqual(
            standardize_stance(
                "The Libertarian Party supports voluntary association.",
                "libertarian",
                ["policy_position"],
            ),
            "Support for voluntary association.",
        )
        baseline = sources()
        combined = [*baseline, *libertarian]
        self.assertEqual(
            [
                block
                for block in build_blocks(combined, coverage(combined))
                if block["group"] != "libertarian"
            ],
            build_blocks(baseline, coverage(baseline)),
        )

    def write_source_repair(self, output, block, manifest, claims):
        record = {
            "block_id": block["block_id"],
            "basis_sha256": source_repair_basis(
                block,
                (output / "responses" / f"{block['block_id']}.json").read_bytes(),
                manifest["fingerprint"],
            ),
            "reviewer": "assistant_source_fidelity",
            "notes": "Correct the candidate against the complete target and preceding context.",
            "claims": claims,
            "unresolved_references": [],
        }
        directory = output / "source_repairs"
        directory.mkdir(exist_ok=True)
        path = directory / f"{block['block_id']}.json"
        path.write_text(json.dumps(record))
        return path, record

    def test_source_repairs_preserve_originals_and_cannot_leave_superseded_duplicate_anchors(self):
        with tempfile.TemporaryDirectory() as temporary:
            corpus, output = Path(temporary) / "baseline", Path(temporary) / "claims"
            corpus.mkdir()
            rows = sources()[:1]
            text = "\n\n".join(["We support universal care."] * 100)
            rows[0].update(
                scoped_text=text,
                complete_text=text,
                text_sha256=digest(text),
                complete_text_sha256=digest(text),
            )
            write_rows(corpus / "complete_sources.csv", rows)
            write_rows(corpus / "coverage.csv", coverage(rows))

            def extractor(*_):
                return {
                    "text": response(claim_text="Support for universal care."),
                    "seconds": 0.1,
                    "generation_tokens": 25,
                    "peak_memory": 1,
                }

            extract_corpus(output=output, corpus=corpus, extractor=extractor)
            blocks, manifest = prepare(output, corpus)
            self.assertGreater(len(blocks), 2)
            raw = {p.name: p.read_bytes() for p in (output / "responses").glob("*.json")}
            original = read_rows(output / "claims.csv")[0]
            self.write_source_repair(
                output,
                blocks[0],
                manifest,
                [claim(claim_text="Support for care for all residents.")],
            )
            summary = extract_corpus(output=output, corpus=corpus, prepare_only=True)
            exported = read_rows(output / "claims.csv")
            historical = next(r for r in exported if r["claim_id"] == original["claim_id"])
            repaired = next(
                r for r in exported if r["normalization_origin"] == "assistant_source_repair"
            )
            self.assertEqual(historical["model_claim_text"], original["model_claim_text"])
            self.assertEqual(historical["claim_text"], original["claim_text"])
            self.assertEqual(historical["analysis_eligible"], "False")
            self.assertEqual(historical["superseded_by_repair"], repaired["repair_id"])
            self.assertEqual(repaired["model_claim_text"], "")
            self.assertEqual(repaired["analysis_eligible"], "True")
            self.assertEqual(summary["analysis_claims"], 2)
            self.assertEqual(summary["assistant_source_repaired_blocks"], 1)
            self.assertEqual(summary["model_blocks_by_status"], {"normalized": len(blocks)})
            self.assertTrue(all(r["duplicate_of"] != original["claim_id"] for r in exported))
            self.assertEqual(
                raw, {p.name: p.read_bytes() for p in (output / "responses").glob("*.json")}
            )
            replay = (output / "claims.csv").read_bytes()
            extract_corpus(output=output, corpus=corpus, prepare_only=True)
            self.assertEqual(replay, (output / "claims.csv").read_bytes())

    def test_failed_model_source_repair_is_separate_and_rejects_stale_or_invalid_corrections(self):
        with tempfile.TemporaryDirectory() as temporary:
            corpus, output = Path(temporary) / "baseline", Path(temporary) / "claims"
            corpus.mkdir()
            rows = sources()
            write_rows(corpus / "complete_sources.csv", rows)
            write_rows(corpus / "coverage.csv", coverage(rows))

            def extractor(*_):
                return {
                    "text": "invalid",
                    "seconds": 0.1,
                    "generation_tokens": 25,
                    "peak_memory": 1,
                }

            extract_corpus(output=output, corpus=corpus, extractor=extractor)
            blocks, manifest = prepare(output, corpus)
            raw = {p.name: p.read_bytes() for p in (output / "responses").glob("*.json")}
            path, record = self.write_source_repair(
                output, blocks[0], manifest, [claim(claim_text="Support for universal care.")]
            )
            with patch(
                "dsa_analysis.national_claim_corpus.LocalGemma",
                side_effect=AssertionError("source corrections must not regenerate model replies"),
            ):
                summary = extract_corpus(output=output, corpus=corpus)
            status = read_rows(output / "block_status.csv")[0]
            self.assertEqual(status["status"], "source_repaired")
            self.assertEqual(status["model_status"], "validation_failed")
            self.assertIn("invalid_json", status["errors"])
            self.assertEqual(summary["model_blocks_by_status"], {"validation_failed": len(blocks)})
            self.assertEqual(summary["analysis_claims"], 1)
            with zipfile.ZipFile(output / "claim_documents.zip") as archive:
                self.assertEqual(archive.read(f"source_repairs/{path.name}"), path.read_bytes())
                self.assertEqual(
                    archive.read(f"responses/{blocks[0]['block_id']}.json"),
                    raw[f"{blocks[0]['block_id']}.json"],
                )
            path.write_text(json.dumps({**record, "replaces_claim_numbers": [1]}))
            with self.assertRaisesRegex(ValueError, "Invalid partial source repair"):
                load_source_repairs(blocks, output, manifest)
            path.write_text(json.dumps(record))
            changed = [{**blocks[0], "context_before": "Changed source context."}, *blocks[1:]]
            with self.assertRaisesRegex(ValueError, "Stale source repair"):
                load_source_repairs(changed, output, manifest)
            response_path = output / "responses" / f"{blocks[0]['block_id']}.json"
            response_path.write_bytes(response_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "Stale source repair"):
                load_source_repairs(blocks, output, manifest)
            response_path.write_bytes(raw[response_path.name])
            path.write_text(json.dumps({**record, "claims": [claim(evidence_ids=[99])]}))
            with self.assertRaisesRegex(ValueError, "Invalid source repair claims"):
                load_source_repairs(blocks, output, manifest)
            path.write_text(json.dumps({**record, "block_id": "unknown"}))
            with self.assertRaisesRegex(ValueError, "Invalid source repair"):
                load_source_repairs(blocks, output, manifest)

    def test_source_repair_can_discard_nonassertive_material_without_inventing_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            corpus, output = Path(temporary) / "baseline", Path(temporary) / "claims"
            corpus.mkdir()
            rows = sources()[:1]
            text = "Acknowledgements.\n\nStaff and contributors."
            rows[0].update(
                scoped_text=text,
                complete_text=text,
                text_sha256=digest(text),
                complete_text_sha256=digest(text),
            )
            write_rows(corpus / "complete_sources.csv", rows)
            write_rows(corpus / "coverage.csv", coverage(rows))

            def extractor(*_):
                return {
                    "text": response(),
                    "seconds": 0.1,
                    "generation_tokens": 25,
                    "peak_memory": 1,
                }

            extract_corpus(output=output, corpus=corpus, extractor=extractor)
            blocks, manifest = prepare(output, corpus)
            self.write_source_repair(output, blocks[0], manifest, [])
            summary = extract_corpus(output=output, corpus=corpus, prepare_only=True)
            self.assertEqual(summary["analysis_claims"], 0)
            self.assertEqual(summary["assistant_source_repaired_claims"], 0)
            self.assertEqual(summary["superseded_model_claims"], 1)
            self.assertEqual(read_rows(output / "claims.csv")[0]["analysis_eligible"], "False")

    def test_partial_source_repair_keeps_unaffected_model_claims_and_original_review_numbers(self):
        with tempfile.TemporaryDirectory() as temporary:
            corpus, output = Path(temporary) / "baseline", Path(temporary) / "claims"
            corpus.mkdir()
            rows = sources()[:1]
            write_rows(corpus / "complete_sources.csv", rows)
            write_rows(corpus / "coverage.csv", coverage(rows))

            def extractor(*_):
                return {
                    "text": json.dumps(
                        {
                            "claims": [
                                claim(claim_text="Support for universal care."),
                                claim(claim_text="Support for services."),
                            ],
                            "unresolved_references": [],
                        }
                    ),
                    "seconds": 0.1,
                    "generation_tokens": 25,
                    "peak_memory": 1,
                }

            extract_corpus(output=output, corpus=corpus, extractor=extractor)
            blocks, manifest = prepare(output, corpus)
            original = read_rows(output / "claims.csv")
            write_rows(
                output / "semantic_review.csv",
                [
                    {
                        "block_id": blocks[0]["block_id"],
                        "review_status": "issues_found",
                        "flagged_claim_numbers": "2",
                    }
                ],
            )
            path, record = self.write_source_repair(
                output,
                blocks[0],
                manifest,
                [claim(claim_text="Support for care for all residents.")],
            )
            path.write_text(json.dumps({**record, "replaces_claim_numbers": [2]}))
            summary = extract_corpus(output=output, corpus=corpus, prepare_only=True)
            exported = read_rows(output / "claims.csv")
            self.assertEqual(exported[0]["claim_id"], original[0]["claim_id"])
            self.assertEqual(exported[0]["claim_text"], original[0]["claim_text"])
            self.assertEqual(exported[0]["model_claim_text"], original[0]["model_claim_text"])
            self.assertEqual(exported[0]["analysis_eligible"], "True")
            self.assertEqual(exported[0]["superseded_by_repair"], "")
            self.assertEqual(
                exported[1]["quality_status"], "assistant_flagged_source_fidelity_issue"
            )
            self.assertEqual(exported[1]["analysis_eligible"], "False")
            self.assertEqual(summary["assistant_flagged_claims"], 1)
            self.assertEqual(summary["unrepaired_flagged_model_claims"], 0)
            self.assertEqual(summary["superseded_model_claims"], 1)
            self.assertEqual(summary["analysis_claims"], 2)
            self.assertEqual(read_rows(output / "block_status.csv")[0]["claims"], "2")
            for invalid in ([], [0], [3], [2, 2], [True]):
                path.write_text(json.dumps({**record, "replaces_claim_numbers": invalid}))
                with self.assertRaisesRegex(ValueError, "Invalid partial source repair"):
                    load_source_repairs(blocks, output, manifest)

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
            response(claim_text='"We will expand services."'),
            response(claim_text='"No, we cannot", we say.'),
            response(claim_types=["ideology"]),
            response(extra_field="none"),
        ]
        for text in invalid:
            with self.subTest(text=text):
                self.assertTrue(validate_response(text, block)[1])
        errors = validate_response(response(evidence_ids=[99]), block)[1]
        allowed = json.dumps(sorted(unit["id"] for unit in block["units"]), separators=(",", ":"))
        self.assertIn(f"allowed_source_unit_ids={allowed}", errors[0])
        self.assertIn("received_evidence_ids=[99]", errors[0])
        self.assertIn("not numbered list items", errors[0])
        errors = validate_response(response(claim_text="These investments reduce costs."), block)[1]
        self.assertIn("Forbidden opening='These'", errors[0])
        self.assertIn("claim_text=", errors[0])
        errors = validate_response(
            response(claim_text="Republicans will secure our Borders."), block
        )[1]
        self.assertIn('Forbidden narrator tokens=["our"]', errors[0])
        self.assertIn("possessives and objects", errors[0])
        payload = json.loads(response())
        payload["claims"] *= 2
        self.assertTrue(validate_response(json.dumps(payload), block)[1])

    def test_source_stance_prefixes_preserve_qualifiers_and_original_wording(self):
        block = build_blocks(sources(), coverage(sources()))[0]
        cases = [
            (
                "democratic",
                "The Democratic Party will seek funding next year only if Congress agrees.",
                ["policy_position"],
                "Commitment to seek funding next year only if Congress agrees.",
            ),
            (
                "republican",
                "Republicans will not only support clinics but also fund hospitals.",
                ["policy_position"],
                "Commitment to not only support clinics but also fund hospitals.",
            ),
            (
                "dsa",
                "DSA opposes cuts to Medicare.",
                ["policy_position"],
                "Opposition to cuts to Medicare.",
            ),
            (
                "democratic",
                "Democrats support Medicare.",
                ["policy_position"],
                "Support for Medicare.",
            ),
            (
                "dsa",
                "The Democratic Socialists of America is committed to seeking reform.",
                ["policy_position"],
                "Commitment to seeking reform.",
            ),
        ]
        unchanged = [
            ("democratic", "Republicans will cut funding.", ["policy_position"]),
            ("democratic", "Democrats supported the agreement.", ["policy_position"]),
            ("democratic", "Democrats will receive more votes.", ["prediction"]),
            (
                "democratic",
                "Democrats will receive more votes.",
                ["prediction", "policy_position"],
            ),
            ("democratic", "Democrats may seek funding.", ["policy_position"]),
            ("democratic", 'Judith Smith says "Democrats will help".', ["factual_assertion"]),
        ]
        cases.extend((group, text, types, text) for group, text, types in unchanged)
        for group, original, types, expected in cases:
            with self.subTest(original=original):
                accepted, errors, _ = validate_response(
                    response(claim_text=original, claim_types=types), {**block, "group": group}
                )
                self.assertEqual(errors, [])
                self.assertEqual(accepted[0]["claim_text"], expected)
                self.assertEqual(accepted[0]["model_claim_text"], original)

    def test_relative_time_and_quoted_slogans_are_not_narrator_pronouns(self):
        block = build_blocks(sources(), coverage(sources()))[0]
        for text in (
            "This winter, American families will spend more on heat.",
            "This year, employment may grow.",
            'The slogan "No, we cannot" is not a viable energy policy.',
            "The slogan \u201cNo, we cannot\u201d is not a viable energy policy.",
        ):
            with self.subTest(text=text):
                accepted, errors, _ = validate_response(response(claim_text=text), block)
                self.assertEqual(errors, [])
                self.assertEqual(accepted[0]["claim_text"], text)

    def test_repair_uses_source_request_without_copying_failed_answer(self):
        block = build_blocks(sources(), coverage(sources()))[0]
        previous = response(evidence_ids=[6])
        errors = validate_response(previous, block)[1]
        base = "AUTHORITATIVE SOURCE [1]: " + block["text"]
        request = repair_request(base, previous, errors)
        self.assertIn(base, request)
        self.assertIn(digest(previous), request)
        self.assertNotIn(previous, request)
        self.assertIn("received_evidence_ids=[6]", request)
        self.assertLess(request.index(digest(previous)), request.index(base))
        accepted, errors, _ = validate_response(
            response(claim_text='Support for the "Protect Our Workers" Act.'), block
        )
        self.assertEqual(errors, [])
        self.assertEqual(accepted[0]["claim_text"], 'Support for the "Protect Our Workers" Act.')
        self.assertTrue(
            validate_response(response(claim_text="Support for our workers."), block)[1]
        )

    def test_repair_separates_unit_ids_from_internal_list_numbers_without_changing_text(self):
        units = [{"id": 1, "text": '6. Support bargaining for "Our Union".\n7. Workplace rights.'}]
        block = {
            "title": "Collective bargaining fixture",
            "group": "dsa",
            "publication_date": "2011-01-01",
            "context_before": "Reference-only context.",
            "units": units,
        }
        draft = "\nPROPOSED CLAIMS:\n" + response()
        previous = response(claim_text="Failed candidate.", evidence_ids=[6])
        errors = ["claim_1: invalid_schema_or_evidence_ids; received_evidence_ids=[6]"]
        first = repair_request(make_prompt(block) + draft, previous, errors, units=units)
        nested = repair_request(first, previous, errors, units=units)
        for request in (first, nested):
            with self.subTest(nested=request == nested):
                encoded = request.split("\nSOURCE UNITS:\n", 1)[1].splitlines()[0]
                self.assertEqual(json.loads(encoded), {"[1]": units[0]["text"]})
                self.assertEqual(request.count("\nSOURCE UNITS:\n"), 1)
                self.assertIn(block["context_before"], request)
                self.assertIn(draft, request)
                self.assertIn(digest(previous), request)
                self.assertNotIn(previous, request)

    def test_targeted_retry_does_not_regenerate_other_or_successful_blocks(self):
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary) / "baseline"
            corpus.mkdir()
            output = Path(temporary) / "claims"
            rows = sources()
            write_rows(corpus / "complete_sources.csv", rows)
            write_rows(corpus / "coverage.csv", coverage(rows))

            def result(text):
                return {"text": text, "seconds": 0.1, "generation_tokens": 25, "peak_memory": 1}

            extract_corpus(output=output, corpus=corpus, extractor=lambda *_: result("invalid"))
            original = {path.name: path.read_bytes() for path in (output / "responses").glob("*")}
            target = build_blocks(rows, coverage(rows))[-1]["block_id"]
            calls = []

            def extractor(prompt, max_tokens):
                calls.append(prompt)
                return result(response())

            summary = extract_corpus(
                output=output,
                corpus=corpus,
                retry_failed=True,
                block_ids={target},
                max_new_blocks=1,
                extractor=extractor,
            )
            self.assertEqual(summary["blocks_by_status"]["normalized"], 1)
            self.assertEqual(len(calls), 2)
            self.assertIn('"[1]"', calls[0])
            for name, contents in original.items():
                if name != f"{target}.json":
                    self.assertEqual((output / "responses" / name).read_bytes(), contents)
            self.assertTrue(
                (
                    output
                    / "response_history"
                    / f"{target}-{digest(original[f'{target}.json'])[:12]}.json"
                ).exists()
            )
            with patch(
                "dsa_analysis.national_claim_corpus.LocalGemma",
                side_effect=AssertionError("selection must not initialize a model"),
            ):
                for selection in (set(), {target}):
                    extract_corpus(
                        output=output, corpus=corpus, retry_failed=True, block_ids=selection
                    )
                with self.assertRaisesRegex(ValueError, "Unknown claim block IDs"):
                    extract_corpus(output=output, corpus=corpus, block_ids={"unknown"})

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
            self.assertIn("FAILED CHECKS", calls[1])
            self.assertIn(digest("invalid"), calls[1])
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

    def test_flagged_claims_cannot_anchor_within_document_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary) / "baseline"
            corpus.mkdir()
            output = Path(temporary) / "claims"
            rows = sources()[:1]
            text = "\n\n".join([claim()["claim_text"]] * 40)
            rows[0].update(
                scoped_text=text,
                complete_text=text,
                text_sha256=digest(text),
                complete_text_sha256=digest(text),
            )
            write_rows(corpus / "complete_sources.csv", rows)
            write_rows(corpus / "coverage.csv", coverage(rows))

            def extractor(prompt, max_tokens):
                return {
                    "text": response(),
                    "seconds": 0.1,
                    "generation_tokens": 25,
                    "peak_memory": 1,
                }

            extract_corpus(output=output, corpus=corpus, extractor=extractor)
            original = read_rows(output / "claims.csv")
            self.assertGreaterEqual(len(original), 3)
            for flagged_indices in ((0,), (0, 1), tuple(range(len(original)))):
                with self.subTest(flagged_indices=flagged_indices):
                    write_rows(
                        output / "semantic_review.csv",
                        [
                            {
                                "block_id": original[index]["block_id"],
                                "review_status": "issues_found",
                                "flagged_claim_numbers": "1",
                            }
                            for index in flagged_indices
                        ],
                    )
                    summary = extract_corpus(output=output, corpus=corpus, prepare_only=True)
                    exported = read_rows(output / "claims.csv")
                    flagged_ids = {original[index]["claim_id"] for index in flagged_indices}
                    self.assertEqual(
                        summary["analysis_claims"], int(len(flagged_ids) < len(original))
                    )
                    self.assertEqual(summary["assistant_flagged_claims"], len(flagged_ids))
                    self.assertTrue(all(row["duplicate_of"] not in flagged_ids for row in exported))
                    eligible = [row for row in exported if row["analysis_eligible"] == "True"]
                    if eligible:
                        self.assertNotIn(eligible[0]["claim_id"], flagged_ids)
                        self.assertTrue(
                            all(
                                not row["duplicate_of"]
                                or row["duplicate_of"] == eligible[0]["claim_id"]
                                for row in exported
                            )
                        )

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
            previous = {p.name: p.read_bytes() for p in (output / "responses").glob("*.json")}
            with patch(
                "dsa_analysis.national_claim_corpus.LocalGemma",
                side_effect=AssertionError("failed records are not retried implicitly"),
            ):
                extract_corpus(output=output, corpus=corpus)

            def repaired(prompt, max_tokens):
                return {
                    "text": response(),
                    "generation_tokens": 25,
                    "seconds": 0.1,
                    "peak_memory": 1,
                }

            recovered = extract_corpus(
                output=output, corpus=corpus, extractor=repaired, retry_failed=True
            )
            self.assertEqual(recovered["status"], "complete")
            self.assertEqual(recovered["analysis_claims"], recovered["blocks"])
            history = list((output / "response_history").glob("*.json"))
            self.assertEqual(len(history), len(previous))
            self.assertEqual({p.read_bytes() for p in history}, set(previous.values()))
            with zipfile.ZipFile(output / "claim_documents.zip") as archive:
                self.assertEqual(
                    len(
                        [
                            name
                            for name in archive.namelist()
                            if name.startswith("response_history/")
                        ]
                    ),
                    len(previous),
                )


if __name__ == "__main__":
    unittest.main()
