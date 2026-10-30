"""Standalone national-document collection, with no race-registry dependency."""

from __future__ import annotations

import calendar
import csv
import hashlib
import json
import re
import subprocess
import zipfile
from collections import Counter
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path

from .document_corpus import RawDocumentCapture, extract_document_text

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "data/manual/national_platform_sources.csv"
OUTPUT = ROOT / "data/analysis/national_platforms"
RAW = ROOT / "data/raw/national_platforms"
GROUPS = ("democratic", "republican", "dsa")
SUPPORTED_GROUPS = (*GROUPS, "libertarian")
STRICT_TYPES = {"platform", "program"}
FALLBACK_TYPES = {"resolution", "statement"}
DEFAULT_CUTOFF = "2026-10-26"
MIN_PASSAGES = 10
MAX_LENGTH = 256


def read_rows(path: Path) -> list[dict]:
    csv.field_size_limit(100_000_000)
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest(value: str | bytes) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def export_document_archive(output: Path = OUTPUT, raw: Path = RAW) -> Path:
    """Bundle complete document texts and deduplicated original PDFs, not website chrome."""
    target = output / "source_documents.zip"
    previous = zipfile.ZipFile(target) if target.exists() else None
    members: dict[str, bytes] = {}
    manifest = []
    collections = [
        ("complete_sources", "document_id"),
        ("historical_resolution_inventory", "capture_id"),
        ("historical_statement_inventory", "statement_id"),
        ("historical_strategy_inventory", "strategy_id"),
        ("historical_convention_inventory", "record_id"),
    ]
    captures = {}
    for collection, key in collections[:2]:
        path = output / f"{collection}.csv"
        if path.exists():
            captures.update({row[key]: row for row in read_rows(path)})
    temporary = target.with_suffix(".zip.tmp")
    try:
        for collection, key in collections:
            path = output / f"{collection}.csv"
            if not path.exists():
                continue
            for row in read_rows(path):
                identifier = row[key]
                if not re.fullmatch(r"[a-zA-Z0-9_-]+", identifier):
                    raise ValueError(f"Unsafe archive document ID: {identifier}")
                text = row["complete_text"].encode("utf-8")
                text_hash = digest(text)
                if text_hash != row["complete_text_sha256"]:
                    raise ValueError(f"Document text hash mismatch: {identifier}")
                text_path = f"texts/{collection}/{identifier}.txt"
                members[text_path] = text
                metadata = {
                    name: value
                    for name, value in row.items()
                    if name not in {"complete_text", "scoped_text"}
                }
                metadata.update(collection=collection, text_path=text_path)
                if row.get("scoped_text"):
                    scoped = row["scoped_text"].encode("utf-8")
                    expected = row.get("scoped_text_sha256") or row.get("text_sha256")
                    if digest(scoped) != expected:
                        raise ValueError(f"Scoped document hash mismatch: {identifier}")
                    scoped_path = f"scoped/{collection}/{identifier}.txt"
                    members[scoped_path] = scoped
                    metadata["scoped_text_path"] = scoped_path
                capture_id = row.get("capture_id") or row.get("document_id") or ""
                meta_path = raw / f"{capture_id}.json"
                capture_meta = (
                    json.loads(meta_path.read_text())
                    if meta_path.exists()
                    else captures.get(capture_id, row)
                )
                document_format = row.get("document_format") or captures.get(capture_id, {}).get(
                    "document_format"
                )
                if (
                    "application/pdf" in capture_meta.get("content_type", "")
                    or document_format == "pdf"
                ):
                    pdf_hash = capture_meta["sha256"]
                    expected = row.get("sha256") or row.get("source_sha256")
                    if expected and expected != pdf_hash:
                        raise ValueError(f"Original PDF provenance mismatch: {capture_id}")
                    pdf_path = f"pdfs/{pdf_hash}.pdf"
                    capture_path = raw / f"{capture_id}.source"
                    if pdf_path not in members:
                        if capture_path.exists():
                            data = capture_path.read_bytes()
                        elif previous is not None and pdf_path in previous.namelist():
                            data = previous.read(pdf_path)
                        else:
                            data = None
                        if data is not None and (
                            not data.startswith(b"%PDF-") or digest(data) != pdf_hash
                        ):
                            raise ValueError(f"Original PDF hash or format mismatch: {capture_id}")
                        if data is not None:
                            members[pdf_path] = data
                    if pdf_path in members:
                        metadata["pdf_path"] = pdf_path
                        metadata["pdf_status"] = "original_capture_included"
                    else:
                        metadata["pdf_status"] = "capture_unavailable_complete_text_included"
                    metadata["pdf_sha256"] = pdf_hash
                    metadata["pdf_source_url"] = capture_meta["source_url"]
                    metadata["pdf_retrieved_at"] = capture_meta["retrieved_at"]
                manifest.append(metadata)
        members["manifest.json"] = (
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        disposition = output / "historical_document_link_disposition.csv"
        if disposition.exists():
            members[disposition.name] = disposition.read_bytes()
        members["README.txt"] = (
            b"Complete document texts and original PDF captures; see manifest.json for "
            b"source URLs, hashes, attribution, and screening status.\n"
            b"PDFs are deduplicated by SHA-256. Non-PDF documents are supplied as complete "
            b"article text, not surrounding website scripts, forms, or navigation.\n"
            b"Proposal packets and evidence-only records are not adopted platforms. "
            b"Check each record's screening status; unamended proposal text must not be "
            b"substituted for a resolution adopted with amendments.\n"
            b"Original authors and publishers retain their rights.\n"
        )
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(members.items()):
                info = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
    finally:
        if previous is not None:
            previous.close()
    temporary.replace(target)
    return target


def date_bounds(value: str) -> tuple[date, date]:
    if re.fullmatch(r"\d{4}", value):
        return date(int(value), 1, 1), date(int(value), 12, 31)
    if re.fullmatch(r"\d{4}-\d{2}", value):
        year, month = map(int, value.split("-"))
        return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    parsed = date.fromisoformat(value)
    return parsed, parsed


def load_ledger(path: Path = LEDGER) -> list[dict]:
    rows = read_rows(path)
    seen = set()
    for row in rows:
        row.update({key: value or "" for key, value in row.items()})
        identifier = row["document_id"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", identifier) or identifier in seen:
            raise ValueError(f"Invalid or repeated document ID: {identifier}")
        seen.add(identifier)
        if row["group"] not in SUPPORTED_GROUPS or row["organization_level"] != "national":
            raise ValueError(f"Not a national organization document: {identifier}")
        if row["document_type"] not in STRICT_TYPES | FALLBACK_TYPES | {"gap"}:
            raise ValueError(f"Unsupported document type: {identifier}")
        if row["document_type"] in FALLBACK_TYPES and row["group"] != "dsa":
            raise ValueError(f"Fallback evidence is restricted to national DSA: {identifier}")
        if row["publication_date"]:
            date_bounds(row["publication_date"])
        for key in ("adoption_date", "version_date"):
            if row.get(key):
                date_bounds(row[key])
    by_id = {row["document_id"]: row for row in rows}
    for row in rows:
        reused = row.get("reuse_of", "")
        if reused and (
            reused not in by_id
            or by_id[reused]["group"] != row["group"]
            or by_id[reused].get("reuse_of")
            or reused == row["document_id"]
        ):
            raise ValueError(f"Invalid reuse relationship: {row['document_id']}")
    return rows


class ContentParser(HTMLParser):
    def __init__(self, css_class: str):
        super().__init__(convert_charrefs=True)
        self.css_class = css_class
        self.depth = 0
        self.skipped = 0
        self.parts: list[str] = []
        self.matches = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if not self.depth and self.css_class in attrs.get("class", "").split():
            self.depth = 1
            self.matches += 1
        elif self.depth and tag not in {"img", "br", "hr", "input", "meta", "link", "source"}:
            self.depth += 1
        if self.depth:
            if tag in {"script", "style", "nav", "footer", "form"}:
                self.skipped += 1
            if tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "br"}:
                self.parts.append("\n\n")

    def handle_endtag(self, tag):
        if self.depth:
            if tag in {"script", "style", "nav", "footer", "form"}:
                self.skipped = max(0, self.skipped - 1)
            if tag in {"p", "div", "li", "h1", "h2", "h3", "h4"}:
                self.parts.append("\n\n")
            if tag not in {"img", "br", "hr", "input", "meta", "link", "source"}:
                self.depth -= 1

    def handle_data(self, data):
        if self.depth and not self.skipped:
            self.parts.append(data)

    def text(self) -> str:
        if self.matches != 1:
            raise ValueError(f"Expected one {self.css_class!r} content block; got {self.matches}")
        return "\n\n".join(
            re.sub(r"\s+", " ", block).strip()
            for block in re.split(r"\n\s*\n", "".join(self.parts))
            if block.strip()
        )


def scope_text(text: str, row: dict) -> str:
    start, end = row.get("scope_start", ""), row.get("scope_end", "")
    if " || " in start:
        starts, ends = start.split(" || "), end.split(" || ")
        if len(starts) != len(ends):
            raise ValueError("Scope range count mismatch")
        return "\n\n".join(
            scope_text(text, {**row, "scope_start": first, "scope_end": last})
            for first, last in zip(starts, ends, strict=True)
        )
    if start:
        if text.count(start) != 1:
            raise ValueError(f"Ambiguous or absent start marker: {row['document_id']}")
        text = text[text.index(start) :]
    if end:
        if text.count(end) != 1:
            raise ValueError(f"Ambiguous or absent end marker: {row['document_id']}")
        text = text[: text.index(end)]
    return text.strip()


def fetch_sources(rows: list[dict], raw: Path = RAW) -> list[dict]:
    raw.mkdir(parents=True, exist_ok=True)
    attempts = []
    for row in rows:
        if not row["source_url"] or row["reuse_of"] or row["document_type"] == "gap":
            continue
        identifier = row["document_id"]
        target = raw / f"{identifier}.source"
        meta_path = raw / f"{identifier}.json"
        if target.exists() and meta_path.exists():
            metadata = json.loads(meta_path.read_text())
            if metadata["sha256"] == digest(target.read_bytes()) and metadata["source_url"] in {
                row["source_url"],
                row.get("alternate_url"),
            }:
                continue
        for url in filter(None, [row["source_url"], row.get("alternate_url")]):
            temporary = raw / f"{identifier}.download"
            result = subprocess.run(
                [
                    "curl",
                    "--location",
                    "--compressed",
                    "--fail",
                    "--silent",
                    "--show-error",
                    "--retry",
                    "2",
                    "--max-time",
                    "90",
                    "--user-agent",
                    "Mozilla/5.0",
                    "--output",
                    str(temporary),
                    "--write-out",
                    "%{url_effective}\n%{content_type}",
                    url,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            attempts.append(
                {
                    "document_id": identifier,
                    "url": url,
                    "status": "fetched" if result.returncode == 0 else "fetch_error",
                    "error": result.stderr.strip(),
                }
            )
            if result.returncode == 0:
                final_url, _, content_type = result.stdout.partition("\n")
                data = temporary.read_bytes()
                temporary.replace(target)
                write_json(
                    meta_path,
                    {
                        "source_url": url,
                        "final_url": final_url,
                        "content_type": content_type,
                        "retrieved_at": datetime.now(UTC).isoformat(),
                        "sha256": digest(data),
                    },
                )
                break
            temporary.unlink(missing_ok=True)
    audit = raw / "fetch_attempts.jsonl"
    with audit.open("a", encoding="utf-8") as handle:
        for attempt in attempts:
            handle.write(json.dumps(attempt) + "\n")
    return attempts


def split_passages(text: str, tokenizer, max_length: int = MAX_LENGTH) -> list[dict]:
    limit = max_length - tokenizer.num_special_tokens_to_add(pair=False)
    if limit < 20:
        raise ValueError("Encoder token limit is too small")
    passages = []
    for paragraph_number, paragraph in enumerate(text.split("\n\n"), 1):
        paragraph = re.sub(r"\[PDF page \d+\]\s*", "", paragraph)
        paragraph = re.sub(
            r"(?:\d+\s+)?WORKERS DESERVE MORE!(?:\s+\d+)?",
            "",
            paragraph,
            flags=re.IGNORECASE,
        )
        paragraph = re.sub(r"^\s*\d+\s+", "", paragraph).strip()
        paragraph = re.sub(
            r"(?:page \d+ [•·] Democratic Left [•·] "
            r"(?:Spring(?:-Summer)?|Summer|Fall(?:-Winter)?|Winter) \d{4}"
            r"|Democratic Left [•·] (?:Spring(?:-Summer)?|Summer|Fall(?:-Winter)?|Winter) "
            r"\d{4} [•·] Page \d+)",
            "",
            paragraph,
            flags=re.IGNORECASE,
        )
        if len(paragraph.split()) < 8:
            continue
        encoded = tokenizer(paragraph, add_special_tokens=False, return_offsets_mapping=True)
        offsets = encoded["offset_mapping"]
        start, chunk = 0, 0
        while start < len(offsets):
            chunk += 1
            end = min(start + limit, len(offsets))
            part = paragraph[offsets[start][0] : offsets[end - 1][1]].strip()
            count = len(tokenizer(part, add_special_tokens=True)["input_ids"])
            while count > max_length and end > start + 1:
                end -= 1
                part = paragraph[offsets[start][0] : offsets[end - 1][1]].strip()
                count = len(tokenizer(part, add_special_tokens=True)["input_ids"])
            if count > max_length:
                raise ValueError("A source span cannot fit the encoder token limit")
            if len(part.split()) >= 8:
                passages.append(
                    {
                        "locator": f"scoped paragraph {paragraph_number}, chunk {chunk}",
                        "text": part,
                        "token_count": count,
                    }
                )
            start = end
    return passages


def ledger_status(row: dict, cutoff: str) -> str:
    if row["document_type"] == "gap":
        return row["verification_status"]
    if not row["publication_date"]:
        return "date_unverified"
    lower, upper = date_bounds(row["publication_date"])
    if lower < date(2000, 1, 1) or upper > date.fromisoformat(cutoff):
        return "outside_cutoff_or_uncertain_boundary"
    if row.get("version_date") and date_bounds(row["version_date"])[1] > date.fromisoformat(cutoff):
        return "version_after_cutoff"
    if row["reuse_of"]:
        return "reused_document"
    if row["verification_status"] != "verified":
        return row["verification_status"]
    if row["adoption_status"] not in {"adopted", "official_statement"}:
        return "adoption_unverified"
    if row["document_type"] in STRICT_TYPES and row["adoption_status"] != "adopted":
        return "adoption_unverified"
    return "eligible"


def prepare_corpus(
    rows: list[dict],
    tokenizer,
    *,
    raw: Path = RAW,
    output: Path = OUTPUT,
    cutoff: str = DEFAULT_CUTOFF,
) -> tuple[list[dict], list[dict]]:
    output.mkdir(parents=True, exist_ok=True)
    snapshot_path = output / "complete_sources.csv"
    snapshots = (
        {row["document_id"]: row for row in read_rows(snapshot_path)}
        if snapshot_path.exists()
        else {}
    )
    coverage, sources, passages = [], [], []
    hashes: dict[tuple[str, str], str] = {}
    for entry in rows:
        row = dict(entry)
        row.update(status=ledger_status(row, cutoff), passage_count=0, duplicate_of="")
        if row["status"] != "eligible":
            coverage.append(row)
            continue
        identifier = row["document_id"]
        try:
            capture_path, meta_path = raw / f"{identifier}.source", raw / f"{identifier}.json"
            if not capture_path.exists() and not meta_path.exists() and identifier in snapshots:
                saved = snapshots[identifier]
                for key in (
                    "scope_start",
                    "scope_end",
                    "html_class",
                    "publication_date",
                    "version_date",
                ):
                    if (saved.get(key) or "") != (row.get(key) or ""):
                        raise ValueError(
                            "Saved extraction no longer matches source ledger; refetch"
                        )
                complete, selected = saved["complete_text"], saved["scoped_text"]
                if digest(selected) != saved["text_sha256"] or digest(complete) != saved.get(
                    "complete_text_sha256"
                ):
                    raise ValueError("Saved extraction hash mismatch")
                meta = {
                    key: saved[key]
                    for key in (
                        "source_url",
                        "final_url",
                        "retrieved_at",
                        "content_type",
                        "sha256",
                    )
                }
                if saved.get("requested_url"):
                    meta["requested_url"] = saved["requested_url"]
            else:
                data = capture_path.read_bytes()
                meta = json.loads(meta_path.read_text())
                if digest(data) != meta["sha256"]:
                    raise ValueError("Raw capture hash mismatch")
                capture = RawDocumentCapture(
                    identifier,
                    meta["source_url"],
                    meta["final_url"],
                    meta["retrieved_at"],
                    meta["content_type"],
                    "utf-8",
                    data,
                    len(data),
                    meta["sha256"],
                )
                if "application/json" in meta["content_type"]:
                    payload = json.loads(data)
                    if row.get("version_date") and (
                        payload.get("modified", "")[:10] != row["version_date"]
                    ):
                        raise ValueError(
                            "Official API version changed; verify and update the ledger"
                        )
                    rendered = payload["content"]["rendered"]
                    parser = ContentParser("national-api-content")
                    parser.feed(f'<article class="national-api-content">{rendered}</article>')
                    complete = parser.text()
                    selected = complete
                elif row["html_class"]:
                    parser = ContentParser(row["html_class"])
                    parser.feed(data.decode("utf-8"))
                    complete = parser.text()
                    selected = complete
                else:
                    complete = extract_document_text(capture).text
                    selected = complete
                selected = scope_text(selected, row)
            if meta["source_url"] not in {row["source_url"], row.get("alternate_url")}:
                raise ValueError("Capture URL no longer matches the source ledger; refetch")
            meta = {key: meta[key] for key in sorted(meta)}
            text_hash = digest(selected)
            duplicate = hashes.get((row["group"], text_hash), "")
            chunks = split_passages(selected, tokenizer)
            source = {
                **entry,
                **meta,
                "complete_text": complete,
                "scoped_text": selected,
                "text_sha256": text_hash,
                "complete_text_sha256": digest(complete),
                "duplicate_of": duplicate,
            }
            sources.append(source)
            row.update(sha256=meta["sha256"], text_sha256=text_hash, duplicate_of=duplicate)
            if duplicate:
                row["status"] = "duplicate_document"
            else:
                hashes[(row["group"], text_hash)] = identifier
                seen = set()
                for chunk in chunks:
                    chunk_hash = digest(chunk["text"])
                    if chunk_hash in seen:
                        continue
                    seen.add(chunk_hash)
                    passages.append(
                        {
                            "segment_id": f"{identifier}-{len(seen):04d}",
                            "document_id": identifier,
                            "group": row["group"],
                            "bundle_id": row["bundle_id"] or identifier,
                            "document_type": row["document_type"],
                            "strict": row["document_type"] in STRICT_TYPES,
                            "publication_date": row["publication_date"],
                            "adoption_date": row.get("adoption_date", ""),
                            "version_date": row.get("version_date", ""),
                            "title": row["title"],
                            "source_url": row["source_url"],
                            "final_url": meta["final_url"],
                            "source_sha256": meta["sha256"],
                            "text_sha256": chunk_hash,
                            **chunk,
                        }
                    )
                row["passage_count"] = len(seen)
        except (OSError, ValueError, RuntimeError, KeyError) as error:
            row.update(status="extraction_or_capture_error", error=str(error))
        coverage.append(row)
    counts = Counter(p["bundle_id"] for p in passages)
    for row in coverage:
        if row["status"] == "eligible":
            bundle = row["bundle_id"] or row["document_id"]
            if counts[bundle] < MIN_PASSAGES:
                row["status"] = "sparse_bundle"
    eligible_ids = {r["document_id"] for r in coverage if r["status"] == "eligible"}
    for passage in passages:
        passage["eligible"] = passage["document_id"] in eligible_ids
    write_rows(output / "coverage.csv", coverage)
    write_rows(output / "passages.csv", passages)
    write_rows(output / "complete_sources.csv", sources)
    with (output / "complete_sources.jsonl").open("w", encoding="utf-8") as handle:
        for source in sources:
            handle.write(json.dumps(source, ensure_ascii=False) + "\n")
    years = []
    groups = tuple(group for group in SUPPORTED_GROUPS if any(r["group"] == group for r in rows))
    for year in range(2000, date.fromisoformat(cutoff).year + 1):
        for group in groups:
            observed = [
                r
                for r in coverage
                if r["group"] == group and r["publication_date"].startswith(str(year))
            ]
            years.append(
                {
                    "year": year,
                    "group": group,
                    "document_ids": " | ".join(r["document_id"] for r in observed),
                    "statuses": " | ".join(sorted({r["status"] for r in observed})),
                    "coverage": "document_recorded" if observed else "no_recovered_publication",
                    "qualification": "Publication chronology, not annual platform applicability",
                }
            )
    write_rows(output / "year_coverage.csv", years)
    export_document_archive(output, raw)
    return passages, coverage
