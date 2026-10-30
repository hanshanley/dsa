import contextlib
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.national_claim_analysis import analysis_rows, run_analysis, topic_shares
from dsa_analysis.national_claim_corpus import (
    FULL_OUTPUT,
    export_results,
    extract_corpus,
    prepare,
    source_repair_basis,
)
from dsa_analysis.national_four_party import merge_components
from dsa_analysis.national_platforms import (
    ROOT,
    SUPPORTED_GROUPS,
    digest,
    read_rows,
    write_json,
    write_rows,
)
from tests.test_national_claims import coverage, sources


class FourPartyTests(unittest.TestCase):
    def prepare_components(self, root):
        baseline = sources()
        libertarian = [
            {
                **baseline[0],
                "document_id": "libertarian-2022",
                "group": "libertarian",
                "publication_date": "2022",
            }
        ]
        for name, documents in (("base", baseline), ("libertarian", libertarian)):
            corpus = root / f"{name}-sources"
            corpus.mkdir()
            write_rows(corpus / "complete_sources.csv", documents)
            write_rows(corpus / "coverage.csv", coverage(documents))

            def extractor(*_):
                return {
                    "text": json.dumps(
                        {
                            "claims": [
                                {
                                    "claim_text": "Support for universal care.",
                                    "claim_types": ["policy_position"],
                                    "evidence_ids": [2],
                                }
                            ],
                            "unresolved_references": [],
                        }
                    ),
                    "seconds": 0.1,
                    "generation_tokens": 25,
                    "peak_memory": 1,
                }

            with contextlib.redirect_stdout(io.StringIO()):
                extract_corpus(output=root / name, corpus=corpus, extractor=extractor)
            if name == "base":
                output = root / name
                blocks, manifest = prepare(output, corpus)
                block = blocks[0]
                response = output / "responses" / f"{block['block_id']}.json"
                repairs = output / "source_repairs"
                repairs.mkdir()
                write_json(
                    repairs / response.name,
                    {
                        "block_id": block["block_id"],
                        "basis_sha256": source_repair_basis(
                            block, response.read_bytes(), manifest["fingerprint"]
                        ),
                        "reviewer": "assistant_source_fidelity",
                        "notes": (
                            "Fixture source correction preserves a superseded original candidate."
                        ),
                        "claims": [
                            {
                                "claim_text": "Support for universal care.",
                                "claim_types": ["policy_position"],
                                "evidence_ids": [2],
                            }
                        ],
                        "unresolved_references": [],
                    },
                )
                history = output / "response_history"
                history.mkdir()
                shutil.copyfile(response, history / f"{response.stem}-fixture.json")
                export_results(blocks, output, manifest)
        return root / "base", root / "libertarian"

    def test_merge_retains_component_fingerprints_and_original_bytes_and_replays(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base, libertarian = self.prepare_components(root)
            originals = {
                path: digest(path.read_bytes())
                for directory in (base, libertarian)
                for path in directory.rglob("*")
                if path.is_file()
            }
            output = root / "four-party"
            summary = merge_components(base=base, libertarian=libertarian, output=output)
            claims = read_rows(output / "claims.csv")
            documents = read_rows(output / "complete_sources.csv")
            self.assertEqual(len(analysis_rows(claims, documents)), summary["analysis_claims"])
            self.assertEqual({row["group"] for row in claims}, set(SUPPORTED_GROUPS))
            self.assertNotIn("fingerprint", summary)
            self.assertNotEqual(
                summary["components"]["three_party"]["fingerprint"],
                summary["components"]["libertarian"]["fingerprint"],
            )
            for component, source in (("three_party", base), ("libertarian", libertarian)):
                restored = [
                    {key: value for key, value in row.items() if key != "normalization_component"}
                    for row in claims
                    if row["normalization_component"] == component
                ]
                self.assertEqual(restored, read_rows(source / "claims.csv"))
            before = {path.name: path.read_bytes() for path in output.glob("*") if path.is_file()}
            merge_components(base=base, libertarian=libertarian, output=output)
            self.assertEqual(
                before,
                {path.name: path.read_bytes() for path in output.glob("*") if path.is_file()},
            )
            self.assertTrue(
                all(digest(path.read_bytes()) == value for path, value in originals.items())
            )
            with zipfile.ZipFile(output / "claim_documents.zip") as archive:
                for path in output.rglob("*"):
                    if path.is_file() and path.suffix in {".csv", ".json", ".jsonl"}:
                        self.assertEqual(
                            archive.read(path.relative_to(output).as_posix()), path.read_bytes()
                        )
            replay = root / "replay"
            shutil.copytree(output / "components/three_party", replay)
            blocks = read_rows(replay / "blocks.csv")
            for block in blocks:
                for field in ("words", "source_start", "source_end"):
                    block[field] = int(block[field])
                block["units"] = json.loads(block["units"])
            export_results(
                blocks, replay, json.loads((replay / "normalization_manifest.json").read_text())
            )
            self.assertEqual(
                (replay / "claims.csv").read_bytes(), (base / "claims.csv").read_bytes()
            )

    def test_merge_rejects_running_or_provenance_corrupted_components_and_baseline_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base, libertarian = self.prepare_components(root)
            with self.assertRaisesRegex(ValueError, "must not overwrite"):
                merge_components(base=base, libertarian=libertarian, output=base / "four")
            path = libertarian / "extraction_summary.json"
            original = path.read_text()
            summary = json.loads(original)
            summary["status"] = "running"
            path.write_text(json.dumps(summary))
            with self.assertRaisesRegex(ValueError, "completed standalone"):
                merge_components(base=base, libertarian=libertarian, output=root / "four")
            path.write_text(original)
            claims = read_rows(libertarian / "claims.csv")
            claims[0]["evidence"] = "Altered source evidence."
            write_rows(libertarian / "claims.csv", claims)
            with self.assertRaisesRegex(ValueError, "provenance mismatch"):
                merge_components(base=base, libertarian=libertarian, output=root / "four")

    def test_merge_requires_complete_chunk_and_response_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base, libertarian = self.prepare_components(root)
            blocks = libertarian / "blocks.csv"
            original = blocks.read_bytes()
            blocks.unlink()
            with self.assertRaisesRegex(ValueError, "evidence is incomplete"):
                merge_components(base=base, libertarian=libertarian, output=root / "four")
            blocks.write_bytes(original)
            next((libertarian / "responses").glob("*.json")).unlink()
            with self.assertRaisesRegex(ValueError, "provenance"):
                merge_components(base=base, libertarian=libertarian, output=root / "four")

    def test_merge_detects_input_change_after_reading_claims(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base, libertarian = self.prepare_components(root)
            copy = shutil.copyfile
            claims = base / "claims.csv"
            changed = False

            def racing_copy(source, destination):
                nonlocal changed
                result = copy(source, destination)
                if not changed:
                    claims.write_bytes(claims.read_bytes() + b"\r\n")
                    changed = True
                return result

            with patch("dsa_analysis.national_four_party.shutil.copyfile", side_effect=racing_copy):
                with self.assertRaisesRegex(ValueError, "claims changed during merge"):
                    merge_components(base=base, libertarian=libertarian, output=root / "four")

    def test_four_party_topic_shares_keep_each_organization_bundle_balanced(self):
        predictions = [
            {"group": group, "bundle_id": f"{group}-a", "topic_code": "1"}
            for group in SUPPORTED_GROUPS
        ]
        predictions += [
            {"group": "libertarian", "bundle_id": "libertarian-b", "topic_code": ""}
        ] * 4
        shares = topic_shares(
            predictions,
            {"topics": [{"code": 1, "name": "Economics"}]},
            "expanded",
            groups=SUPPORTED_GROUPS,
        )
        libertarian = [row for row in shares if row["group"] == "libertarian"]
        self.assertEqual([row["share"] for row in libertarian], [0.5, 0.5])
        for group in SUPPORTED_GROUPS:
            self.assertAlmostEqual(sum(row["share"] for row in shares if row["group"] == group), 1)

    def test_four_party_analysis_rejects_baseline_output_and_report_before_loading_models(self):
        separate_report = ROOT / "report/national_claim_analysis_four_party.md"
        separate_output = FULL_OUTPUT.parent / "four_party"
        for output, report in (
            (FULL_OUTPUT, separate_report),
            (FULL_OUTPUT / "four_party", separate_report),
            (separate_output, None),
            (separate_output, ROOT / "report/national_claim_analysis.md"),
        ):
            with self.subTest(output=output, report=report):
                with self.assertRaisesRegex(ValueError, "separate"):
                    run_analysis(output, groups=SUPPORTED_GROUPS, report=report)
