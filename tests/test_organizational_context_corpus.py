import csv
import hashlib
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.document_corpus import AnalysisSegmentConfig, ExtractionError
from dsa_analysis.organizational_context_corpus import (
    OrganizationalContextCorpusError,
    OrganizationalContextCorpusPaths,
    run_organizational_context_extraction_batch,
)

SCRATCH_ROOT = Path(__file__).resolve().parent / "_scratch_organizational_context_corpus"


class OrganizationalContextCorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree(SCRATCH_ROOT, ignore_errors=True)
        SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(SCRATCH_ROOT, ignore_errors=True))

    def test_run_organizational_context_extraction_batch_writes_outputs_and_summary(self) -> None:
        root = self._scenario_root("extract")
        paths = self._paths(root)
        self._write_csv(
            paths.inventory_path,
            [
                self._inventory_row(
                    "context-state-party-ca-2020",
                    state="California",
                    state_code="CA",
                    cycle_year="2020",
                    context_category="state_democratic_party",
                    organization_level="state",
                    organization="California Democratic Party",
                    title="California Democratic Party Platform",
                    platform_type="state_party_platform",
                    source_url="https://example.org/ca-platform",
                ),
                self._inventory_row(
                    "context-state-party-ca-2022",
                    state="California",
                    state_code="CA",
                    cycle_year="2022",
                    context_category="state_democratic_party",
                    organization_level="state",
                    organization="California Democratic Party",
                    title="California Democratic Party Platform",
                    platform_type="state_party_platform",
                    source_url="https://example.org/ca-platform",
                ),
                self._inventory_row(
                    "context-east-bay-dsa-ca-2022",
                    state="California",
                    state_code="CA",
                    cycle_year="2022",
                    context_category="dsa_state_local",
                    organization_level="local",
                    organization="East Bay DSA",
                    endorsing_body="East Bay DSA",
                    title="East Bay DSA Platform",
                    platform_type="chapter_platform",
                    source_url="https://example.org/east-bay-platform.txt",
                ),
                self._inventory_row(
                    "context-dsa-national-2022",
                    state="California",
                    state_code="CA",
                    cycle_year="2022",
                    context_category="dsa_national",
                    organization_level="national",
                    organization="Democratic Socialists of America",
                    title="DSA Platform Draft",
                    platform_type="dsa_national_platform_draft",
                    source_url="https://example.org/platform-draft.pdf",
                ),
                self._inventory_row(
                    "context-process-2026",
                    state="Missouri",
                    state_code="MO",
                    cycle_year="2026",
                    context_category="dsa_state_local",
                    organization_level="local",
                    organization="Example DSA",
                    endorsing_body="Example DSA",
                    title="Process Doc",
                    platform_type="chapter_endorsement_process",
                    source_url="https://example.org/process.bin",
                ),
            ],
        )
        self._write_fetched_document(
            paths,
            fetch_id="fetch-ca",
            fetch_url="https://example.org/ca-platform",
            context_entry_ids="context-state-party-ca-2020 | context-state-party-ca-2022",
            content_type="text/html",
            suffix=".html",
            body=(
                b"<html><head><title>California Platform</title></head><body>"
                b"<p>We support public housing, labor rights, climate jobs, mass transit, union power, "
                b"reproductive freedom, education funding, community healthcare, and voting rights for every resident.</p>"
                b"</body></html>"
            ),
        )
        self._write_fetched_document(
            paths,
            fetch_id="fetch-east-bay",
            fetch_url="https://example.org/east-bay-platform.txt",
            context_entry_ids="context-east-bay-dsa-ca-2022",
            content_type="text/plain",
            suffix=".txt",
            body=(
                b"East Bay DSA supports rent control, universal childcare, free transit, clean energy jobs, "
                b"strong unions, language justice, disability access, tenant organizing, and democratic schools."
            ),
        )
        self._write_fetched_document(
            paths,
            fetch_id="fetch-dsa-draft",
            fetch_url="https://example.org/platform-draft.pdf",
            context_entry_ids="context-dsa-national-2022",
            content_type="application/pdf",
            suffix=".pdf",
            body=b"%PDF-1.7",
        )
        self._write_fetched_document(
            paths,
            fetch_id="fetch-process",
            fetch_url="https://example.org/process.bin",
            context_entry_ids="context-process-2026",
            content_type="application/octet-stream",
            suffix=".bin",
            body=b"\x00\x01\x02\x03",
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
            side_effect=[
                subprocess.CompletedProcess(
                    ["/usr/bin/swift"],
                    0,
                    stdout=(
                        b'{"title":"DSA Draft Platform","pages":'
                        b'[{"page":"1","text":"A democratic socialist platform demands public housing, union power, mass transit, '
                        b'climate jobs, reproductive freedom, healthcare, education, labor rights, voting access, and tenant power."}]}'
                    ),
                    stderr=b"",
                )
            ],
        ):
            result = run_organizational_context_extraction_batch(paths)

        self.assertEqual(result.fetched_documents, 4)
        self.assertEqual(result.successful_documents, 3)
        self.assertEqual(result.extraction_errors, 1)

        metadata_rows = {row["fetch_id"]: row for row in self._read_csv(paths.metadata_path)}
        self.assertEqual(
            metadata_rows["fetch-ca"]["context_entry_ids"],
            "context-state-party-ca-2020 | context-state-party-ca-2022",
        )
        self.assertEqual(metadata_rows["fetch-ca"]["cycle_years"], "2020 | 2022")
        self.assertEqual(metadata_rows["fetch-ca"]["extractor"], "html")
        self.assertEqual(metadata_rows["fetch-dsa-draft"]["extractor"], "pdf")
        self.assertEqual(metadata_rows["fetch-process"]["extraction_status"], "extraction_error")

        full_text_rows = {row["fetch_id"]: row for row in self._read_jsonl(paths.full_text_path)}
        self.assertIn("California Platform", full_text_rows["fetch-ca"]["extracted_title"])
        self.assertIn("public housing", full_text_rows["fetch-ca"]["text"])
        self.assertIn("East Bay DSA supports rent control", full_text_rows["fetch-east-bay"]["text"])
        self.assertIn("[PDF page 1]", full_text_rows["fetch-dsa-draft"]["text"])

        analysis_rows = self._read_csv(paths.analysis_segment_path)
        self.assertTrue(any(row["fetch_id"] == "fetch-ca" for row in analysis_rows))
        self.assertTrue(any(row["fetch_id"] == "fetch-east-bay" for row in analysis_rows))

        summary = json.loads(paths.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["clean_full_platform_documents_by_category"]["state_democratic_party"], 1)
        self.assertEqual(summary["clean_full_platform_documents_by_category"]["dsa_state_local"], 1)
        self.assertEqual(summary["clean_full_platform_documents_by_category"]["dsa_national"], 1)
        self.assertGreater(summary["clean_full_platform_analysis_segments_by_category"]["state_democratic_party"], 0)
        self.assertGreater(summary["clean_full_platform_analysis_segments_by_category"]["dsa_national"], 0)
        self.assertEqual(len(summary["extraction_failures"]), 1)

    def test_run_organizational_context_extraction_batch_uses_pdfkit_fallback(self) -> None:
        root = self._scenario_root("pdf")
        paths = self._paths(root)
        self._write_csv(
            paths.inventory_path,
            [
                self._inventory_row(
                    "context-dnc-2024",
                    state="Colorado",
                    state_code="CO",
                    cycle_year="2024",
                    context_category="dnc_national",
                    organization_level="national",
                    organization="Democratic National Committee",
                    title="2024 Democratic Party Platform",
                    platform_type="national_party_platform",
                    source_url="https://example.org/dnc-2024.pdf",
                )
            ],
        )
        self._write_fetched_document(
            paths,
            fetch_id="fetch-dnc-pdf",
            fetch_url="https://example.org/dnc-2024.pdf",
            context_entry_ids="context-dnc-2024",
            content_type="application/pdf",
            suffix=".pdf",
            body=b"%PDF-1.7",
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
                    b'{"title":"DNC Platform","pages":'
                    b'[{"page":"1","text":"We support labor rights, climate action, public housing, mass transit, '
                    b'civil rights, reproductive freedom, voting access, strong schools, healthcare, and unions."}]}'
                ),
                stderr=b"",
            ),
        ):
            run_organizational_context_extraction_batch(paths)

        metadata_row = self._read_csv(paths.metadata_path)[0]
        self.assertEqual(metadata_row["extractor"], "pdf")
        full_text_row = self._read_jsonl(paths.full_text_path)[0]
        self.assertIn("[PDF page 1]", full_text_row["text"])
        summary = json.loads(paths.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["clean_full_platform_documents_by_category"]["dnc_national"], 1)
        self.assertGreater(summary["clean_full_platform_analysis_segments_by_category"]["dnc_national"], 0)

    def test_run_organizational_context_extraction_batch_surfaces_unknown_context_entries(self) -> None:
        root = self._scenario_root("invalid")
        paths = self._paths(root)
        self._write_csv(
            paths.inventory_path,
            [
                self._inventory_row(
                    "context-known",
                    state="Texas",
                    state_code="TX",
                    cycle_year="2022",
                    context_category="state_democratic_party",
                    organization_level="state",
                    organization="Texas Democratic Party",
                    title="Texas Platform",
                    platform_type="state_party_platform",
                    source_url="https://example.org/tx-platform",
                )
            ],
        )
        paths.fetch_status_path.parent.mkdir(parents=True, exist_ok=True)
        with paths.fetch_status_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "fetch_id",
                    "fetch_url",
                    "archive_url",
                    "context_entry_ids",
                    "status",
                    "http_status",
                    "content_type",
                    "retrieved_at",
                    "final_url",
                    "raw_path",
                    "sha256",
                    "error",
                ],
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerow(
                {
                    "fetch_id": "fetch-invalid",
                    "fetch_url": "https://example.org/unknown-platform",
                    "archive_url": "",
                    "context_entry_ids": "context-known | context-missing",
                    "status": "fetched",
                    "http_status": "200",
                    "content_type": "text/html",
                    "retrieved_at": "2026-08-20T00:00:00+00:00",
                    "final_url": "https://example.org/unknown-platform",
                    "raw_path": "raw/organizational_context/fetch-invalid.html",
                    "sha256": "",
                    "error": "",
                }
            )
        paths.raw_manifest_path.write_text("", encoding="utf-8")

        with self.assertRaisesRegex(OrganizationalContextCorpusError, "unknown context_entry_ids"):
            run_organizational_context_extraction_batch(paths)

    def test_run_organizational_context_extraction_batch_remaps_superseded_context_id_by_url(self) -> None:
        root = self._scenario_root("superseded_context")
        paths = self._paths(root)
        source_url = "https://example.org/current-platform"
        self._write_csv(
            paths.inventory_path,
            [
                self._inventory_row(
                    "context-current",
                    state="Wisconsin",
                    state_code="WI",
                    cycle_year="2026",
                    context_category="dsa_state_local",
                    organization_level="local",
                    organization="Madison Area DSA",
                    title="Current platform",
                    platform_type="chapter_endorsement_process",
                    source_url=source_url,
                )
            ],
        )
        self._write_csv(paths.fetch_status_path, [], [
            "fetch_id",
            "fetch_url",
            "archive_url",
            "context_entry_ids",
            "status",
            "http_status",
            "content_type",
            "retrieved_at",
            "final_url",
            "raw_path",
            "sha256",
            "error",
        ])
        self._write_jsonl(paths.raw_manifest_path, [])
        self._write_fetched_document(
            paths,
            fetch_id="fetch-current-platform",
            fetch_url=source_url,
            context_entry_ids="context-superseded",
            content_type="text/html",
            suffix=".html",
            body=b"<main><p>Workers deserve housing, healthcare, transit, education, and democratic power.</p></main>",
        )

        run_organizational_context_extraction_batch(paths)

        metadata_rows = self._read_csv(paths.metadata_path)
        self.assertEqual(metadata_rows[0]["context_entry_ids"], "context-current")

    def _scenario_root(self, name: str) -> Path:
        root = SCRATCH_ROOT / name
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _paths(self, root: Path) -> OrganizationalContextCorpusPaths:
        return OrganizationalContextCorpusPaths(
            inventory_path=root / "data" / "processed" / "organizational_context_inventory.csv",
            fetch_status_path=root / "data" / "processed" / "organizational_context_fetch_status.csv",
            raw_manifest_path=root / "data" / "processed" / "organizational_context_raw_manifest.jsonl",
            metadata_path=root / "data" / "processed" / "organizational_context_document_metadata.csv",
            full_text_path=root / "data" / "processed" / "organizational_context_full_text.jsonl",
            paragraph_path=root / "data" / "processed" / "organizational_context_paragraphs.csv",
            sentence_path=root / "data" / "processed" / "organizational_context_sentences.csv",
            analysis_segment_path=root / "data" / "processed" / "organizational_context_analysis_segments.csv",
            summary_path=root / "data" / "processed" / "organizational_context_extraction_summary.json",
        )

    def _inventory_row(
        self,
        context_entry_id: str,
        *,
        state: str,
        state_code: str,
        cycle_year: str,
        context_category: str,
        organization_level: str,
        organization: str,
        title: str,
        platform_type: str,
        source_url: str,
        endorsing_body: str = "",
    ) -> dict[str, str]:
        return {
            "corpus_scope": "organizational_context",
            "context_entry_id": context_entry_id,
            "state": state,
            "state_code": state_code,
            "cycle_year": cycle_year,
            "organization_level": organization_level,
            "context_category": context_category,
            "organization": organization,
            "endorsing_body": endorsing_body,
            "title": title,
            "platform_type": platform_type,
            "adoption_date": "",
            "effective_date": "",
            "source_url": source_url,
            "archive_url": "",
            "verification_status": "verified",
            "notes": "",
            "synthetic": "false",
        }

    def _write_fetched_document(
        self,
        paths: OrganizationalContextCorpusPaths,
        *,
        fetch_id: str,
        fetch_url: str,
        context_entry_ids: str,
        content_type: str,
        suffix: str,
        body: bytes,
    ) -> None:
        raw_path = paths.metadata_path.parents[1] / "raw" / "organizational_context" / f"{fetch_id}{suffix}"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(body)
        sha256 = hashlib.sha256(body).hexdigest()
        status_row = {
            "fetch_id": fetch_id,
            "fetch_url": fetch_url,
            "archive_url": "",
            "context_entry_ids": context_entry_ids,
            "status": "fetched",
            "http_status": "200",
            "content_type": content_type,
            "retrieved_at": "2026-08-20T00:00:00+00:00",
            "final_url": fetch_url,
            "raw_path": str(raw_path),
            "sha256": sha256,
            "error": "",
        }
        manifest_row = {
            "fetch_id": fetch_id,
            "fetch_url": fetch_url,
            "archive_url": "",
            "final_url": fetch_url,
            "retrieved_at": "2026-08-20T00:00:00+00:00",
            "content_type": content_type,
            "byte_count": str(len(body)),
            "sha256": sha256,
            "raw_path": str(raw_path),
        }
        status_rows = self._read_csv(paths.fetch_status_path)
        status_rows.append(status_row)
        self._write_csv(
            paths.fetch_status_path,
            status_rows,
            [
                "fetch_id",
                "fetch_url",
                "archive_url",
                "context_entry_ids",
                "status",
                "http_status",
                "content_type",
                "retrieved_at",
                "final_url",
                "raw_path",
                "sha256",
                "error",
            ],
        )
        manifest_rows = self._read_jsonl(paths.raw_manifest_path)
        manifest_rows.append(manifest_row)
        self._write_jsonl(paths.raw_manifest_path, manifest_rows)

    def _write_csv(self, path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if fieldnames is None:
            fieldnames = list(rows[0]) if rows else []
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def _write_jsonl(self, path: Path, rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def _read_jsonl(self, path: Path) -> list[dict[str, str]]:
        if not path.exists():
            return []
        rows = []
        with path.open(encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows


if __name__ == "__main__":
    unittest.main()
