from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .document_corpus import (
    AnalysisSegmentConfig,
    ExtractionError,
    RawDocumentCapture,
    _analysis_segments_for_document,
    _annotate_analysis_segments,
    _path_from_row,
    extract_document_text,
)
from .io import read_csv, write_csv
from .organizational_context import CONTEXT_CATEGORIES
from .paths import PROCESSED_DIR

FULL_PLATFORM_TYPES = {
    "chapter_platform",
    "dsa_national_platform_draft",
    "dsa_national_program",
    "national_party_platform",
    "state_party_platform",
    "state_party_platform_archive",
    "state_party_platform_google_doc",
}
SUBSTANTIVE_MIN_TOKENS = 20


@dataclass(frozen=True)
class OrganizationalContextCorpusPaths:
    inventory_path: Path
    fetch_status_path: Path
    raw_manifest_path: Path
    metadata_path: Path
    full_text_path: Path
    paragraph_path: Path
    sentence_path: Path
    analysis_segment_path: Path
    summary_path: Path

    @classmethod
    def default(cls) -> "OrganizationalContextCorpusPaths":
        return cls(
            inventory_path=PROCESSED_DIR / "organizational_context_inventory.csv",
            fetch_status_path=PROCESSED_DIR / "organizational_context_fetch_status.csv",
            raw_manifest_path=PROCESSED_DIR / "organizational_context_raw_manifest.jsonl",
            metadata_path=PROCESSED_DIR / "organizational_context_document_metadata.csv",
            full_text_path=PROCESSED_DIR / "organizational_context_full_text.jsonl",
            paragraph_path=PROCESSED_DIR / "organizational_context_paragraphs.csv",
            sentence_path=PROCESSED_DIR / "organizational_context_sentences.csv",
            analysis_segment_path=PROCESSED_DIR / "organizational_context_analysis_segments.csv",
            summary_path=PROCESSED_DIR / "organizational_context_extraction_summary.json",
        )


@dataclass(frozen=True)
class OrganizationalContextCorpusResult:
    fetched_documents: int
    processed_documents: int
    successful_documents: int
    extraction_errors: int
    metadata_path: Path
    full_text_path: Path
    paragraph_path: Path
    sentence_path: Path
    analysis_segment_path: Path
    summary_path: Path


class OrganizationalContextCorpusError(ValueError):
    pass


@dataclass(frozen=True)
class _FetchedContextDocument:
    context_document_id: str
    fetch_row: dict[str, str]
    manifest_row: dict[str, str]
    entry_rows: tuple[dict[str, str], ...]


def run_organizational_context_extraction_batch(
    paths: OrganizationalContextCorpusPaths | None = None,
    *,
    analysis_config: AnalysisSegmentConfig | None = None,
) -> OrganizationalContextCorpusResult:
    paths = paths or OrganizationalContextCorpusPaths.default()
    analysis_config = analysis_config or AnalysisSegmentConfig()

    inventory_rows = _load_inventory_rows(paths.inventory_path)
    fetched_documents = _load_fetched_documents(
        inventory_rows,
        paths.fetch_status_path,
        paths.raw_manifest_path,
    )

    metadata_rows: list[dict[str, str]] = []
    full_text_rows: list[dict[str, str]] = []
    paragraph_rows: list[dict[str, str]] = []
    sentence_rows: list[dict[str, str]] = []
    extraction_failures: list[dict[str, str]] = []
    extracted_documents: list[tuple[dict[str, str], object]] = []

    for document in fetched_documents:
        raw_capture = _load_raw_capture(document)
        provenance = _document_provenance(document, raw_capture)
        try:
            extracted = extract_document_text(raw_capture)
        except ExtractionError as error:
            metadata_rows.append(
                {
                    **provenance,
                    "extractor": "",
                    "extraction_status": "extraction_error",
                    "text_sha256": "",
                    "paragraph_count": "0",
                    "sentence_count": "0",
                    "extracted_title": "",
                    "error": str(error),
                }
            )
            extraction_failures.append(
                {
                    "context_document_id": provenance["context_document_id"],
                    "fetch_id": provenance["fetch_id"],
                    "fetch_url": provenance["fetch_url"],
                    "context_entry_ids": provenance["context_entry_ids"],
                    "error": str(error),
                }
            )
            continue

        extraction_status = (
            "media_no_transcript"
            if extracted.coverage_status == "media_no_transcript"
            else "extracted"
        )
        metadata_row = {
            **provenance,
            "extractor": extracted.extractor,
            "extraction_status": extraction_status,
            "text_sha256": extracted.text_sha256,
            "paragraph_count": str(len(extracted.paragraphs)),
            "sentence_count": str(len(extracted.sentences)),
            "extracted_title": extracted.title,
            "error": "",
        }
        metadata_rows.append(metadata_row)
        full_text_rows.append(
            {
                **metadata_row,
                "text": extracted.text,
            }
        )
        paragraph_rows.extend(
            _segment_rows(
                metadata_row,
                extracted.paragraphs,
            )
        )
        sentence_rows.extend(
            _segment_rows(
                metadata_row,
                extracted.sentences,
            )
        )
        if extraction_status == "extracted":
            extracted_documents.append((metadata_row, extracted))

    analysis_rows = _analysis_rows(extracted_documents, analysis_config)
    _write_outputs(
        paths,
        metadata_rows,
        full_text_rows,
        paragraph_rows,
        sentence_rows,
        analysis_rows,
        extraction_failures,
    )

    return OrganizationalContextCorpusResult(
        fetched_documents=len(fetched_documents),
        processed_documents=len(fetched_documents),
        successful_documents=sum(
            row["extraction_status"] in {"extracted", "media_no_transcript"}
            for row in metadata_rows
        ),
        extraction_errors=sum(row["extraction_status"] == "extraction_error" for row in metadata_rows),
        metadata_path=paths.metadata_path,
        full_text_path=paths.full_text_path,
        paragraph_path=paths.paragraph_path,
        sentence_path=paths.sentence_path,
        analysis_segment_path=paths.analysis_segment_path,
        summary_path=paths.summary_path,
    )


def _load_inventory_rows(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        raise OrganizationalContextCorpusError(
            f"organizational context inventory is missing: {path}"
        )
    rows = read_csv(path)
    by_entry_id: dict[str, dict[str, str]] = {}
    for number, row in enumerate(rows, start=2):
        context_entry_id = row.get("context_entry_id", "").strip()
        if not context_entry_id:
            raise OrganizationalContextCorpusError(
                f"{path.name}:{number}: missing context_entry_id"
            )
        if context_entry_id in by_entry_id:
            raise OrganizationalContextCorpusError(
                f"{path.name}:{number}: duplicate context_entry_id {context_entry_id}"
            )
        by_entry_id[context_entry_id] = row
    return by_entry_id


def _load_fetched_documents(
    inventory_rows: dict[str, dict[str, str]],
    fetch_status_path: Path,
    raw_manifest_path: Path,
) -> list[_FetchedContextDocument]:
    if not fetch_status_path.exists():
        raise OrganizationalContextCorpusError(
            f"organizational context fetch status is missing: {fetch_status_path}"
        )
    manifest_by_fetch_id = _load_jsonl_index(raw_manifest_path, "fetch_id")
    documents: list[_FetchedContextDocument] = []
    seen_fetch_ids: set[str] = set()
    for number, row in enumerate(read_csv(fetch_status_path), start=2):
        if row.get("status", "").strip() != "fetched":
            continue
        fetch_id = row.get("fetch_id", "").strip()
        if not fetch_id:
            raise OrganizationalContextCorpusError(
                f"{fetch_status_path.name}:{number}: missing fetch_id"
            )
        if fetch_id in seen_fetch_ids:
            raise OrganizationalContextCorpusError(
                f"{fetch_status_path.name}:{number}: duplicate fetch_id {fetch_id}"
            )
        seen_fetch_ids.add(fetch_id)
        entry_ids = _split_pipe(row.get("context_entry_ids", ""))
        if not entry_ids:
            raise OrganizationalContextCorpusError(
                f"{fetch_status_path.name}:{number}: fetched row is missing context_entry_ids"
            )
        fetch_urls = {
            row.get("fetch_url", "").strip(),
            row.get("final_url", "").strip(),
            row.get("archive_url", "").strip(),
        } - {""}
        current_entry_ids = {
            entry_id
            for entry_id, entry_row in inventory_rows.items()
            if fetch_urls
            & {
                entry_row.get("source_url", "").strip(),
                entry_row.get("archive_url", "").strip(),
            }
            - {""}
        }
        missing_entry_ids = [entry_id for entry_id in entry_ids if entry_id not in inventory_rows]
        if current_entry_ids:
            entry_ids = sorted(current_entry_ids)
        elif missing_entry_ids and len(missing_entry_ids) < len(entry_ids) - len(missing_entry_ids):
            continue
        elif missing_entry_ids and len(missing_entry_ids) != len(entry_ids):
            raise OrganizationalContextCorpusError(
                f"{fetch_status_path.name}:{number}: unknown context_entry_ids {missing_entry_ids}"
            )
        else:
            continue
        manifest_row = manifest_by_fetch_id.get(fetch_id, {})
        documents.append(
            _FetchedContextDocument(
                context_document_id=f"context-doc-{fetch_id}",
                fetch_row=row,
                manifest_row=manifest_row,
                entry_rows=tuple(
                    inventory_rows[entry_id]
                    for entry_id in sorted(entry_ids)
                ),
            )
        )
    return sorted(documents, key=lambda item: item.fetch_row["fetch_id"])


def _load_jsonl_index(path: Path, key: str) -> dict[str, dict[str, str]]:
    if not path.exists():
        raise OrganizationalContextCorpusError(
            f"organizational context raw manifest is missing: {path}"
        )
    rows: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8") as handle:
        for number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            row = json.loads(line)
            normalized = {str(name): str(value) for name, value in row.items()}
            row_key = normalized.get(key, "").strip()
            if not row_key:
                raise OrganizationalContextCorpusError(
                    f"{path.name}:{number}: missing {key}"
                )
            if row_key in rows:
                raise OrganizationalContextCorpusError(
                    f"{path.name}:{number}: duplicate {key} {row_key}"
                )
            rows[row_key] = normalized
    return rows


def _load_raw_capture(document: _FetchedContextDocument) -> RawDocumentCapture:
    row = document.manifest_row or document.fetch_row
    raw_path = _resolve_raw_path(
        row.get("raw_path", "") or document.fetch_row.get("raw_path", "")
    )
    if raw_path is None:
        raise OrganizationalContextCorpusError(
            f"{document.fetch_row['fetch_id']}: missing raw_path"
        )
    if not raw_path.exists():
        raise OrganizationalContextCorpusError(
            f"{document.fetch_row['fetch_id']}: raw_path does not exist: {raw_path}"
        )
    content_bytes = raw_path.read_bytes()
    actual_sha = hashlib.sha256(content_bytes).hexdigest()
    expected_sha = (row.get("sha256", "") or document.fetch_row.get("sha256", "")).strip()
    if expected_sha and expected_sha != actual_sha:
        raise OrganizationalContextCorpusError(
            f"{document.fetch_row['fetch_id']}: raw sha256 mismatch for {raw_path}"
        )
    return RawDocumentCapture(
        document_id=document.context_document_id,
        source_url=(row.get("fetch_url", "") or document.fetch_row.get("fetch_url", "")).strip(),
        final_url=(row.get("final_url", "") or document.fetch_row.get("final_url", "")).strip(),
        retrieved_at=(row.get("retrieved_at", "") or document.fetch_row.get("retrieved_at", "")).strip(),
        content_type=(row.get("content_type", "") or document.fetch_row.get("content_type", "")).strip(),
        encoding="utf-8",
        content_bytes=content_bytes,
        byte_count=len(content_bytes),
        sha256=actual_sha,
    )


def _document_provenance(
    document: _FetchedContextDocument,
    raw_capture: RawDocumentCapture,
) -> dict[str, str]:
    entry_rows = document.entry_rows
    return {
        "context_document_id": document.context_document_id,
        "fetch_id": document.fetch_row.get("fetch_id", "").strip(),
        "context_entry_ids": _join_unique(entry["context_entry_id"] for entry in entry_rows),
        "context_entry_count": str(len(entry_rows)),
        "states": _join_unique(entry["state"] for entry in entry_rows),
        "state_codes": _join_unique(entry["state_code"] for entry in entry_rows),
        "cycle_years": _join_unique(entry["cycle_year"] for entry in entry_rows),
        "context_categories": _join_unique(entry["context_category"] for entry in entry_rows),
        "full_platform_categories": _join_unique(
            entry["context_category"]
            for entry in entry_rows
            if _is_full_platform_type(entry.get("platform_type", ""))
        ),
        "organization_levels": _join_unique(entry["organization_level"] for entry in entry_rows),
        "organizations": _join_unique(entry["organization"] for entry in entry_rows),
        "endorsing_bodies": _join_unique(entry["endorsing_body"] for entry in entry_rows),
        "titles": _join_unique(entry["title"] for entry in entry_rows),
        "platform_types": _join_unique(entry["platform_type"] for entry in entry_rows),
        "adoption_dates": _join_unique(entry["adoption_date"] for entry in entry_rows),
        "effective_dates": _join_unique(entry["effective_date"] for entry in entry_rows),
        "verification_statuses": _join_unique(entry["verification_status"] for entry in entry_rows),
        "fetch_url": document.fetch_row.get("fetch_url", "").strip(),
        "source_urls": _join_unique(entry["source_url"] for entry in entry_rows),
        "archive_urls": _join_unique(
            value
            for entry in entry_rows
            for value in (entry.get("archive_url", ""), document.fetch_row.get("archive_url", ""))
        ),
        "final_url": raw_capture.final_url,
        "retrieved_at": raw_capture.retrieved_at,
        "content_type": raw_capture.content_type,
        "raw_sha256": raw_capture.sha256,
        "raw_path": (document.manifest_row.get("raw_path", "") or document.fetch_row.get("raw_path", "")).strip(),
    }


def _segment_rows(
    metadata_row: dict[str, str],
    segments: Sequence[object],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for segment in segments:
        rows.append(
            {
                "segment_id": segment.segment_id,
                "context_document_id": metadata_row["context_document_id"],
                "fetch_id": metadata_row["fetch_id"],
                "context_entry_ids": metadata_row["context_entry_ids"],
                "states": metadata_row["states"],
                "state_codes": metadata_row["state_codes"],
                "cycle_years": metadata_row["cycle_years"],
                "context_categories": metadata_row["context_categories"],
                "full_platform_categories": metadata_row["full_platform_categories"],
                "organization_levels": metadata_row["organization_levels"],
                "organizations": metadata_row["organizations"],
                "endorsing_bodies": metadata_row["endorsing_bodies"],
                "titles": metadata_row["titles"],
                "platform_types": metadata_row["platform_types"],
                "segment_kind": segment.segment_kind,
                "index": str(segment.index),
                "locator": segment.locator,
                "text": segment.text,
                "sha256": segment.sha256,
            }
        )
    return rows


def _analysis_rows(
    extracted_documents: Sequence[tuple[dict[str, str], object]],
    analysis_config: AnalysisSegmentConfig,
) -> list[dict[str, str]]:
    base_segments = []
    metadata_by_document: dict[str, dict[str, str]] = {}
    for metadata_row, extracted in extracted_documents:
        metadata_by_document[metadata_row["context_document_id"]] = metadata_row
        base_segments.extend(
            _analysis_segments_for_document(
                candidate_name=metadata_row["organizations"] or metadata_row["titles"],
                race_id="",
                role="",
                document_id=metadata_row["context_document_id"],
                paragraphs=extracted.paragraphs,
                sentences=extracted.sentences,
                candidate_slug_value=metadata_row["context_document_id"],
                source_type=metadata_row["context_categories"],
                config=analysis_config,
            )
        )
    annotated_segments = _annotate_analysis_segments(base_segments, analysis_config)
    rows = []
    for segment in annotated_segments:
        metadata_row = metadata_by_document[segment.document_id]
        rows.append(
            {
                "analysis_segment_id": segment.analysis_segment_id,
                "context_document_id": metadata_row["context_document_id"],
                "fetch_id": metadata_row["fetch_id"],
                "context_entry_ids": metadata_row["context_entry_ids"],
                "states": metadata_row["states"],
                "state_codes": metadata_row["state_codes"],
                "cycle_years": metadata_row["cycle_years"],
                "context_categories": metadata_row["context_categories"],
                "full_platform_categories": metadata_row["full_platform_categories"],
                "organization_levels": metadata_row["organization_levels"],
                "organizations": metadata_row["organizations"],
                "endorsing_bodies": metadata_row["endorsing_bodies"],
                "titles": metadata_row["titles"],
                "platform_types": metadata_row["platform_types"],
                "segment_index": str(segment.segment_index),
                "analysis_kind": segment.analysis_kind,
                "locator": segment.locator,
                "source_locator_start": segment.source_locator_start,
                "source_locator_end": segment.source_locator_end,
                "paragraph_start": str(segment.paragraph_start),
                "paragraph_end": str(segment.paragraph_end),
                "sentence_start": str(segment.sentence_start),
                "sentence_end": str(segment.sentence_end),
                "text": segment.text,
                "token_count": str(segment.token_count),
                "sha256": segment.sha256,
                "exact_duplicate_hash": segment.exact_duplicate_hash,
                "exact_duplicate_count": str(segment.exact_duplicate_count),
                "exact_duplicate_flag": str(segment.exact_duplicate_flag).lower(),
                "near_duplicate_hash": segment.near_duplicate_hash,
                "near_duplicate_count": str(segment.near_duplicate_count),
                "near_duplicate_flag": str(segment.near_duplicate_flag).lower(),
                "boilerplate_flag": str(segment.boilerplate_flag).lower(),
                "boilerplate_reasons": segment.boilerplate_reasons,
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            row["context_document_id"],
            int(row["segment_index"]),
            row["analysis_segment_id"],
        ),
    )


def _write_outputs(
    paths: OrganizationalContextCorpusPaths,
    metadata_rows: list[dict[str, str]],
    full_text_rows: list[dict[str, str]],
    paragraph_rows: list[dict[str, str]],
    sentence_rows: list[dict[str, str]],
    analysis_rows: list[dict[str, str]],
    extraction_failures: list[dict[str, str]],
) -> None:
    write_csv(
        paths.metadata_path,
        sorted(metadata_rows, key=lambda row: row["context_document_id"]),
        [
            "context_document_id",
            "fetch_id",
            "context_entry_ids",
            "context_entry_count",
            "states",
            "state_codes",
            "cycle_years",
            "context_categories",
            "full_platform_categories",
            "organization_levels",
            "organizations",
            "endorsing_bodies",
            "titles",
            "platform_types",
            "adoption_dates",
            "effective_dates",
            "verification_statuses",
            "fetch_url",
            "source_urls",
            "archive_urls",
            "final_url",
            "retrieved_at",
            "content_type",
            "extractor",
            "extraction_status",
            "raw_sha256",
            "text_sha256",
            "paragraph_count",
            "sentence_count",
            "extracted_title",
            "raw_path",
            "error",
        ],
    )
    _write_jsonl(
        paths.full_text_path,
        sorted(full_text_rows, key=lambda row: row["context_document_id"]),
    )
    write_csv(
        paths.paragraph_path,
        sorted(paragraph_rows, key=_segment_sort_key),
        [
            "segment_id",
            "context_document_id",
            "fetch_id",
            "context_entry_ids",
            "states",
            "state_codes",
            "cycle_years",
            "context_categories",
            "full_platform_categories",
            "organization_levels",
            "organizations",
            "endorsing_bodies",
            "titles",
            "platform_types",
            "segment_kind",
            "index",
            "locator",
            "text",
            "sha256",
        ],
    )
    write_csv(
        paths.sentence_path,
        sorted(sentence_rows, key=_segment_sort_key),
        [
            "segment_id",
            "context_document_id",
            "fetch_id",
            "context_entry_ids",
            "states",
            "state_codes",
            "cycle_years",
            "context_categories",
            "full_platform_categories",
            "organization_levels",
            "organizations",
            "endorsing_bodies",
            "titles",
            "platform_types",
            "segment_kind",
            "index",
            "locator",
            "text",
            "sha256",
        ],
    )
    write_csv(
        paths.analysis_segment_path,
        analysis_rows,
        [
            "analysis_segment_id",
            "context_document_id",
            "fetch_id",
            "context_entry_ids",
            "states",
            "state_codes",
            "cycle_years",
            "context_categories",
            "full_platform_categories",
            "organization_levels",
            "organizations",
            "endorsing_bodies",
            "titles",
            "platform_types",
            "segment_index",
            "analysis_kind",
            "locator",
            "source_locator_start",
            "source_locator_end",
            "paragraph_start",
            "paragraph_end",
            "sentence_start",
            "sentence_end",
            "text",
            "token_count",
            "sha256",
            "exact_duplicate_hash",
            "exact_duplicate_count",
            "exact_duplicate_flag",
            "near_duplicate_hash",
            "near_duplicate_count",
            "near_duplicate_flag",
            "boilerplate_flag",
            "boilerplate_reasons",
        ],
    )
    summary = _summary(metadata_rows, analysis_rows, extraction_failures)
    paths.summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _summary(
    metadata_rows: Sequence[dict[str, str]],
    analysis_rows: Sequence[dict[str, str]],
    extraction_failures: Sequence[dict[str, str]],
) -> dict[str, object]:
    clean_full_platform_documents = Counter({category: 0 for category in CONTEXT_CATEGORIES})
    clean_full_platform_segments = Counter({category: 0 for category in CONTEXT_CATEGORIES})
    clean_document_ids = {
        row["context_document_id"]
        for row in metadata_rows
        if row.get("extraction_status") == "extracted"
        and row.get("full_platform_categories", "").strip()
    }
    for row in metadata_rows:
        if row["context_document_id"] not in clean_document_ids:
            continue
        for category in _split_pipe(row.get("full_platform_categories", "")):
            clean_full_platform_documents[category] += 1
    for row in analysis_rows:
        if row["context_document_id"] not in clean_document_ids:
            continue
        if not _is_substantive_segment(row):
            continue
        for category in _split_pipe(row.get("full_platform_categories", "")):
            clean_full_platform_segments[category] += 1
    return {
        "corpus_scope": "organizational_context",
        "fetched_documents": len(metadata_rows),
        "successful_documents": sum(
            row.get("extraction_status", "") in {"extracted", "media_no_transcript"}
            for row in metadata_rows
        ),
        "extraction_errors": len(extraction_failures),
        "by_extraction_status": dict(
            sorted(Counter(row.get("extraction_status", "") for row in metadata_rows).items())
        ),
        "clean_full_platform_documents_by_category": {
            category: clean_full_platform_documents.get(category, 0)
            for category in CONTEXT_CATEGORIES
        },
        "clean_full_platform_analysis_segments_by_category": {
            category: clean_full_platform_segments.get(category, 0)
            for category in CONTEXT_CATEGORIES
        },
        "extraction_failures": list(extraction_failures),
    }


def _write_jsonl(path: Path, rows: Sequence[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _segment_sort_key(row: dict[str, str]) -> tuple[str, int, str]:
    return (
        row.get("context_document_id", ""),
        int(row.get("index", "0") or 0),
        row.get("segment_id", ""),
    )


def _resolve_raw_path(value: str) -> Path | None:
    raw_path = _path_from_row(value)
    if raw_path is not None and raw_path.exists():
        return raw_path
    normalized = value.strip()
    if not normalized:
        return raw_path
    relative = Path(normalized)
    if relative.is_absolute():
        return relative
    candidate = PROCESSED_DIR.parent / relative
    if candidate.exists():
        return candidate
    return raw_path


def _join_unique(values: Sequence[str]) -> str:
    ordered: list[str] = []
    seen = set()
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return " | ".join(ordered)


def _split_pipe(value: str) -> list[str]:
    return [part.strip() for part in value.split(" | ") if part.strip()]


def _is_full_platform_type(value: str) -> bool:
    return value.strip() in FULL_PLATFORM_TYPES


def _is_substantive_segment(row: dict[str, str]) -> bool:
    if not row.get("text", "").strip():
        return False
    if row.get("boilerplate_flag", "false").strip().casefold() == "true":
        return False
    return int(row.get("token_count", "0") or 0) >= SUBSTANTIVE_MIN_TOKENS
