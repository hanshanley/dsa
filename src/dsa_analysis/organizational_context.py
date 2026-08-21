from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import re
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from .io import read_csv, write_csv
from .paths import MANUAL_DIR, PROCESSED_DIR, RAW_DIR
from .race_registry import RaceRegistryPaths, build_race_registry
from .schema import ORGANIZATIONAL_CONTEXT_STATUSES

CORPUS_SCOPE = "organizational_context"
CONTEXT_CATEGORIES = (
    "dnc_national",
    "state_democratic_party",
    "dsa_national",
    "dsa_state_local",
)
CATEGORY_DEFAULTS = {
    "dnc_national": ("national", "Democratic National Committee", "national_party_platform"),
    "state_democratic_party": ("state", "State Democratic Party", "state_party_platform"),
    "dsa_national": ("national", "Democratic Socialists of America", "dsa_national_program_or_equivalent"),
    "dsa_state_local": ("local", "Local DSA chapter", "chapter_electoral_platform_or_questionnaire"),
}
RESOLVED_STATUSES = {"verified", "searched_not_found", "source_unavailable", "not_applicable"}
GAP_STATUSES = {"not_searched", "found_unverified", "searched_not_found", "source_unavailable"}
NATIONAL_CARRY_FORWARD_CATEGORIES = {"dnc_national", "dsa_national"}
USER_AGENT = "Mozilla/5.0 (compatible; dsa-analysis/0.1; +source-first academic research)"
STATE_NAME_BY_CODE = {
    row["state_code"]: row["state"]
    for row in read_csv(PROCESSED_DIR / "organizational_context_represented_state_cycles.csv")
} if (PROCESSED_DIR / "organizational_context_represented_state_cycles.csv").exists() else {}


@dataclass(frozen=True)
class OrganizationalContextPaths:
    registry_seed_path: Path
    race_registry_path: Path
    output_dir: Path
    raw_dir: Path

    @classmethod
    def default(cls) -> "OrganizationalContextPaths":
        return cls(
            registry_seed_path=MANUAL_DIR / "organizational_context_sources.csv",
            race_registry_path=PROCESSED_DIR / "race_registry.csv",
            output_dir=PROCESSED_DIR,
            raw_dir=RAW_DIR / "organizational_context",
        )


@dataclass(frozen=True)
class OrganizationalContextResult:
    inventory_rows: int
    represented_state_cycle_rows: int
    coverage_rows: int
    collection_queue_rows: int
    fetch_queue_rows: int
    platform_gap_rows: int
    all_represented_state_cycles_have_status: bool
    summary_path: Path
    inventory_path: Path
    represented_state_cycles_path: Path
    coverage_path: Path
    collection_queue_path: Path
    fetch_queue_path: Path


@dataclass(frozen=True)
class OrganizationalContextFetchResult:
    queued_urls: int
    fetched_urls: int
    failed_urls: int
    status_path: Path
    raw_manifest_path: Path


@dataclass(frozen=True)
class RepresentedStateCycle:
    state: str
    state_code: str
    cycle_year: str
    race_count: str
    race_ids: str
    endorsed_candidates: str
    endorsing_bodies: str
    local_endorsing_bodies: str


@dataclass(frozen=True)
class ContextEntry:
    context_entry_id: str
    state: str
    state_code: str
    cycle_year: str
    organization_level: str
    context_category: str
    organization: str
    endorsing_body: str
    title: str
    platform_type: str
    adoption_date: str
    effective_date: str
    source_url: str
    archive_url: str
    verification_status: str
    notes: str
    synthetic: bool

    def as_row(self) -> dict[str, str]:
        return {
            "corpus_scope": CORPUS_SCOPE,
            "context_entry_id": self.context_entry_id,
            "state": self.state,
            "state_code": self.state_code,
            "cycle_year": self.cycle_year,
            "organization_level": self.organization_level,
            "context_category": self.context_category,
            "organization": self.organization,
            "endorsing_body": self.endorsing_body,
            "title": self.title,
            "platform_type": self.platform_type,
            "adoption_date": self.adoption_date,
            "effective_date": self.effective_date,
            "source_url": self.source_url,
            "archive_url": self.archive_url,
            "verification_status": self.verification_status,
            "notes": self.notes,
            "synthetic": str(self.synthetic).lower(),
        }


@dataclass(frozen=True)
class FetchCapture:
    fetch_url: str
    final_url: str
    retrieved_at: str
    content_type: str
    content_bytes: bytes
    status_code: int


class OrganizationalContextError(ValueError):
    pass


class OrganizationalContextFetchError(RuntimeError):
    pass


def build_organizational_context_inventory(
    paths: OrganizationalContextPaths | None = None,
) -> OrganizationalContextResult:
    paths = paths or OrganizationalContextPaths.default()
    if not paths.race_registry_path.exists():
        build_race_registry(RaceRegistryPaths.default())
    represented = _load_represented_state_cycles(paths.race_registry_path)
    seed_entries = _load_seed_entries(paths.registry_seed_path)
    inventory_entries = _inventory_entries(represented, seed_entries)
    inventory_rows = [entry.as_row() for entry in inventory_entries]
    represented_rows = [entry.__dict__ for entry in represented]
    coverage_rows = _coverage_rows(represented, inventory_entries)
    collection_rows = _collection_queue_rows(inventory_entries)
    fetch_queue_rows = _fetch_queue_rows(inventory_entries)
    platform_gap_rows = sum(
        row["verification_status"] in GAP_STATUSES and row["verification_status"] != "not_applicable"
        for row in inventory_rows
    )
    summary = _summary(represented, inventory_entries, coverage_rows, collection_rows, fetch_queue_rows, platform_gap_rows)

    paths.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = paths.output_dir / "organizational_context_summary.json"
    inventory_path = paths.output_dir / "organizational_context_inventory.csv"
    represented_path = paths.output_dir / "organizational_context_represented_state_cycles.csv"
    coverage_path = paths.output_dir / "organizational_context_coverage.csv"
    collection_path = paths.output_dir / "organizational_context_collection_queue.csv"
    fetch_queue_path = paths.output_dir / "organizational_context_fetch_queue.csv"

    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(
        inventory_path,
        inventory_rows,
        [
            "corpus_scope",
            "context_entry_id",
            "state",
            "state_code",
            "cycle_year",
            "organization_level",
            "context_category",
            "organization",
            "endorsing_body",
            "title",
            "platform_type",
            "adoption_date",
            "effective_date",
            "source_url",
            "archive_url",
            "verification_status",
            "notes",
            "synthetic",
        ],
    )
    write_csv(
        represented_path,
        represented_rows,
        [
            "state",
            "state_code",
            "cycle_year",
            "race_count",
            "race_ids",
            "endorsed_candidates",
            "endorsing_bodies",
            "local_endorsing_bodies",
        ],
    )
    write_csv(
        coverage_path,
        coverage_rows,
        [
            "corpus_scope",
            "state",
            "state_code",
            "cycle_year",
            "race_count",
            "race_ids",
            "endorsed_candidates",
            "endorsing_bodies",
            "local_endorsing_bodies",
            "dnc_national_status",
            "dnc_national_entry_ids",
            "state_democratic_party_status",
            "state_democratic_party_entry_ids",
            "dsa_national_status",
            "dsa_national_entry_ids",
            "dsa_state_local_status",
            "dsa_state_local_entry_ids",
            "all_categories_have_status",
        ],
    )
    write_csv(
        collection_path,
        collection_rows,
        [
            "priority_rank",
            "priority_score",
            "state",
            "state_code",
            "cycle_year",
            "context_category",
            "organization_level",
            "organization",
            "endorsing_body",
            "verification_status",
            "context_entry_id",
            "title",
            "platform_type",
            "source_url",
            "archive_url",
            "queue_reason",
            "notes",
            "synthetic",
        ],
    )
    write_csv(
        fetch_queue_path,
        fetch_queue_rows,
        [
            "fetch_id",
            "fetch_url",
            "archive_url",
            "context_entry_ids",
            "states",
            "cycles",
            "context_categories",
            "organizations",
            "source_count",
        ],
    )

    return OrganizationalContextResult(
        inventory_rows=len(inventory_rows),
        represented_state_cycle_rows=len(represented_rows),
        coverage_rows=len(coverage_rows),
        collection_queue_rows=len(collection_rows),
        fetch_queue_rows=len(fetch_queue_rows),
        platform_gap_rows=platform_gap_rows,
        all_represented_state_cycles_have_status=all(row["all_categories_have_status"] == "true" for row in coverage_rows),
        summary_path=summary_path,
        inventory_path=inventory_path,
        represented_state_cycles_path=represented_path,
        coverage_path=coverage_path,
        collection_queue_path=collection_path,
        fetch_queue_path=fetch_queue_path,
    )


def merge_organizational_context_reviews(
    batch_dir: Path,
    paths: OrganizationalContextPaths | None = None,
) -> tuple[int, int, int]:
    paths = paths or OrganizationalContextPaths.default()
    expected: set[str] = set()
    for path in sorted(batch_dir.glob("platform_batch_*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                expected.add(json.loads(line)["context_entry_id"])
    if not expected:
        raise OrganizationalContextError("No platform research batches were found")

    fields = [
        "context_entry_id",
        "state",
        "state_code",
        "cycle_year",
        "organization_level",
        "context_category",
        "organization",
        "endorsing_body",
        "title",
        "platform_type",
        "adoption_date",
        "effective_date",
        "source_url",
        "archive_url",
        "verification_status",
        "notes",
    ]
    reviews: dict[str, dict[str, str]] = {}
    for path in sorted(batch_dir.glob("platform_review_*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != fields:
                raise OrganizationalContextError(
                    f"{path.name}: expected header {fields}, found {reader.fieldnames}"
                )
            for row in reader:
                context_id = row["context_entry_id"].strip()
                if context_id not in expected:
                    raise OrganizationalContextError(
                        f"{path.name}: unknown context_entry_id {context_id}"
                    )
                if context_id in reviews:
                    raise OrganizationalContextError(
                        f"{path.name}: duplicate context_entry_id {context_id}"
                    )
                status = row["verification_status"].strip()
                if status not in RESOLVED_STATUSES | GAP_STATUSES:
                    raise OrganizationalContextError(
                        f"{path.name}: invalid verification_status {status}"
                    )
                if status == "verified" and not (
                    row["source_url"].strip() or row["archive_url"].strip()
                ):
                    raise OrganizationalContextError(
                        f"{path.name}: verified row requires a source URL"
                    )
                reviews[context_id] = {
                    field: row.get(field, "").strip()
                    for field in fields
                }
    uncovered = expected - set(reviews)
    if uncovered:
        raise OrganizationalContextError(
            f"{len(uncovered)} platform research rows remain unreviewed"
        )

    existing = {
        row["context_entry_id"]: {
            field: (row.get(field) or "").strip()
            for field in fields
        }
        for row in read_csv(paths.registry_seed_path)
    }
    existing.update(reviews)
    rows = sorted(
        existing.values(),
        key=lambda row: (
            row["cycle_year"],
            row["state_code"],
            row["context_category"],
            row["context_entry_id"],
        ),
    )
    write_csv(paths.registry_seed_path, rows, fields)
    return (
        len(reviews),
        sum(row["verification_status"] == "verified" for row in reviews.values()),
        sum(row["verification_status"] != "verified" for row in reviews.values()),
    )


def run_organizational_context_fetch_pass(
    queue_rows: list[dict[str, str]] | None = None,
    paths: OrganizationalContextPaths | None = None,
    *,
    limit: int | None = None,
    fetcher: Callable[[str], FetchCapture] | None = None,
    timeout: int = 45,
) -> OrganizationalContextFetchResult:
    paths = paths or OrganizationalContextPaths.default()
    if queue_rows is None:
        queue_path = paths.output_dir / "organizational_context_fetch_queue.csv"
        if not queue_path.exists():
            build_organizational_context_inventory(paths)
        queue_rows = read_csv(queue_path)
    if limit is not None and limit <= 0:
        raise OrganizationalContextError("limit must be positive when provided")
    selected = queue_rows[:limit] if limit is not None else queue_rows
    fetcher = fetcher or (lambda url: _fetch_url(url, timeout=timeout))
    status_rows: list[dict[str, str]] = []
    manifest_rows: list[dict[str, str]] = []
    paths.raw_dir.mkdir(parents=True, exist_ok=True)
    fetched = 0
    failed = 0
    for row in selected:
        fetch_id = row["fetch_id"]
        fetch_url = row["fetch_url"]
        archive_url = row.get("archive_url", "").strip()
        try:
            capture = fetcher(fetch_url)
            _raise_for_access_block(capture)
        except OrganizationalContextFetchError as live_error:
            if not archive_url or archive_url == fetch_url:
                error = str(live_error)
                capture = None
            else:
                try:
                    capture = fetcher(archive_url)
                    _raise_for_access_block(capture)
                except OrganizationalContextFetchError as archive_error:
                    error = f"{live_error}; archive fallback failed: {archive_error}"
                    capture = None
            if capture is None:
                failed += 1
                status_rows.append(
                    {
                        "fetch_id": fetch_id,
                        "fetch_url": fetch_url,
                        "archive_url": archive_url,
                        "context_entry_ids": row.get("context_entry_ids", ""),
                        "status": "fetch_error",
                        "http_status": "",
                        "content_type": "",
                        "retrieved_at": datetime.now(UTC).isoformat(),
                        "final_url": "",
                        "raw_path": "",
                        "sha256": "",
                        "error": error,
                    }
                )
                continue
        fetched += 1
        output_path = _persist_fetch_capture(paths.raw_dir, fetch_id, capture)
        sha256 = hashlib.sha256(capture.content_bytes).hexdigest()
        status_rows.append(
            {
                "fetch_id": fetch_id,
                "fetch_url": fetch_url,
                "archive_url": archive_url,
                "context_entry_ids": row.get("context_entry_ids", ""),
                "status": "fetched",
                "http_status": str(capture.status_code),
                "content_type": capture.content_type,
                "retrieved_at": capture.retrieved_at,
                "final_url": capture.final_url,
                "raw_path": str(output_path.relative_to(paths.raw_dir.parent.parent)),
                "sha256": sha256,
                "error": "",
            }
        )
        manifest_rows.append(
            {
                "fetch_id": fetch_id,
                "fetch_url": fetch_url,
                "archive_url": archive_url,
                "final_url": capture.final_url,
                "retrieved_at": capture.retrieved_at,
                "content_type": capture.content_type,
                "byte_count": str(len(capture.content_bytes)),
                "sha256": sha256,
                "raw_path": str(output_path.relative_to(paths.raw_dir.parent.parent)),
            }
        )
    status_path = paths.output_dir / "organizational_context_fetch_status.csv"
    manifest_path = paths.output_dir / "organizational_context_raw_manifest.jsonl"
    existing_statuses = {
        row["fetch_id"]: row
        for row in read_csv(status_path)
    } if status_path.exists() else {}
    existing_statuses.update(
        {row["fetch_id"]: row for row in status_rows}
    )
    write_csv(
        status_path,
        sorted(existing_statuses.values(), key=lambda row: row["fetch_id"]),
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
    existing_manifest: dict[str, dict[str, str]] = {}
    if manifest_path.exists():
        with manifest_path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                existing_manifest[row["fetch_id"]] = row
    existing_manifest.update(
        {row["fetch_id"]: row for row in manifest_rows}
    )
    with manifest_path.open("w", encoding="utf-8") as handle:
        for row in sorted(
            existing_manifest.values(),
            key=lambda row: row["fetch_id"],
        ):
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return OrganizationalContextFetchResult(
        queued_urls=len(selected),
        fetched_urls=fetched,
        failed_urls=failed,
        status_path=status_path,
        raw_manifest_path=manifest_path,
    )


def _load_represented_state_cycles(path: Path) -> list[RepresentedStateCycle]:
    rows = read_csv(path)
    represented = []
    for row in rows:
        if row.get("scope_kind", "") != "tracked_dsa_endorsed_democratic_primary":
            continue
        state_code = row.get("state_code", "").strip()
        cycle_year = row.get("election_year", "").strip()
        if not state_code or not cycle_year:
            continue
        key = (state_code, cycle_year)
        represented.append(key)
    grouped: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in rows:
        if row.get("scope_kind", "") != "tracked_dsa_endorsed_democratic_primary":
            continue
        state_code = row.get("state_code", "").strip()
        cycle_year = row.get("election_year", "").strip()
        if not state_code or not cycle_year:
            continue
        key = (state_code, cycle_year)
        grouped[key]["race_ids"].add(row["race_id"])
        if row.get("endorsed_candidate", "").strip():
            grouped[key]["endorsed_candidates"].update(
                part.strip() for part in row["endorsed_candidate"].split(" | ") if part.strip()
            )
        if row.get("endorsing_bodies", "").strip():
            bodies = [part.strip() for part in row["endorsing_bodies"].split(" | ") if part.strip()]
            grouped[key]["endorsing_bodies"].update(bodies)
            grouped[key]["local_endorsing_bodies"].update(
                body for body in bodies if _identity(body) != _identity("DSA National")
            )
    result = []
    for (state_code, cycle_year), values in sorted(grouped.items()):
        result.append(
            RepresentedStateCycle(
                state=_state_name(state_code),
                state_code=state_code,
                cycle_year=cycle_year,
                race_count=str(len(values["race_ids"])),
                race_ids=" | ".join(sorted(values["race_ids"])),
                endorsed_candidates=" | ".join(sorted(values["endorsed_candidates"])),
                endorsing_bodies=" | ".join(sorted(values["endorsing_bodies"])),
                local_endorsing_bodies=" | ".join(sorted(values["local_endorsing_bodies"])),
            )
        )
    return result


def _load_seed_entries(path: Path) -> list[ContextEntry]:
    if not path.exists():
        return []
    rows = read_csv(path)
    entries = []
    for number, row in enumerate(rows, start=2):
        status = row.get("verification_status", "").strip()
        if status not in ORGANIZATIONAL_CONTEXT_STATUSES:
            raise OrganizationalContextError(f"{path.name}:{number}: invalid verification_status")
        category = row.get("context_category", "").strip()
        if category not in CONTEXT_CATEGORIES:
            raise OrganizationalContextError(f"{path.name}:{number}: invalid context_category")
        entries.append(
            ContextEntry(
                context_entry_id=row.get("context_entry_id", "").strip(),
                state=row.get("state", "").strip(),
                state_code=row.get("state_code", "").strip(),
                cycle_year=row.get("cycle_year", "").strip(),
                organization_level=row.get("organization_level", "").strip(),
                context_category=category,
                organization=row.get("organization", "").strip(),
                endorsing_body=row.get("endorsing_body", "").strip(),
                title=row.get("title", "").strip(),
                platform_type=row.get("platform_type", "").strip(),
                adoption_date=row.get("adoption_date", "").strip(),
                effective_date=row.get("effective_date", "").strip(),
                source_url=row.get("source_url", "").strip(),
                archive_url=row.get("archive_url", "").strip(),
                verification_status=status,
                notes=row.get("notes", "").strip(),
                synthetic=False,
            )
        )
    return entries


def _inventory_entries(
    represented: list[RepresentedStateCycle],
    seed_entries: list[ContextEntry],
) -> list[ContextEntry]:
    seed_entries_by_key: dict[tuple[str, str, str, str], list[ContextEntry]] = defaultdict(list)
    seed_entries_by_cycle_category: dict[tuple[str, str, str], list[ContextEntry]] = defaultdict(list)
    for entry in seed_entries:
        seed_entries_by_key[
            (
                entry.state_code,
                entry.cycle_year,
                entry.context_category,
                _local_body_identity(entry.endorsing_body),
            )
        ].append(entry)
        seed_entries_by_cycle_category[(entry.state_code, entry.cycle_year, entry.context_category)].append(entry)
    local_seed_entries_by_cycle = defaultdict(list)
    for entry in seed_entries:
        if entry.context_category == "dsa_state_local":
            local_seed_entries_by_cycle[(entry.state_code, entry.cycle_year)].append(entry)
    national_carry_forward = _national_carry_forward_index(seed_entries)
    inventory: list[ContextEntry] = []
    for item in represented:
        for category in CONTEXT_CATEGORIES:
            if category == "dsa_state_local":
                local_bodies = [part.strip() for part in item.local_endorsing_bodies.split(" | ") if part.strip()]
                local_seed_entries = local_seed_entries_by_cycle.get((item.state_code, item.cycle_year), [])
                if not local_bodies and local_seed_entries:
                    inventory.extend(sorted(local_seed_entries, key=lambda entry: (entry.endorsing_body, entry.context_entry_id)))
                    continue
                if not local_bodies:
                    inventory.append(
                        _synthetic_entry(
                            item,
                            category=category,
                            organization="Not applicable",
                            endorsing_body="",
                            verification_status="not_applicable",
                            notes="No local/state chapter endorsement is recorded for this represented state/cycle.",
                        )
                    )
                    continue
                covered_bodies = set()
                for body in local_bodies:
                    matching_entries = seed_entries_by_key.get(
                        (
                            item.state_code,
                            item.cycle_year,
                            category,
                            _local_body_identity(body),
                        ),
                        [],
                    )
                    covered_bodies.add(_local_body_identity(body))
                    if matching_entries:
                        inventory.extend(
                            sorted(
                                matching_entries,
                                key=lambda entry: (entry.endorsing_body, entry.platform_type, entry.context_entry_id),
                            )
                        )
                    else:
                        inventory.append(
                            _synthetic_entry(
                                item,
                                category=category,
                                organization=body,
                                endorsing_body=body,
                                verification_status="not_searched",
                                notes="No local DSA platform/questionnaire seed is cataloged yet.",
                            )
                        )
                for seed in sorted(local_seed_entries, key=lambda entry: (entry.endorsing_body, entry.context_entry_id)):
                    if _local_body_identity(seed.endorsing_body) not in covered_bodies:
                        inventory.append(seed)
                continue
            matching_entries = seed_entries_by_cycle_category.get(
                (item.state_code, item.cycle_year, category),
                [],
            )
            if matching_entries:
                inventory.extend(
                    sorted(
                        matching_entries,
                        key=lambda entry: (entry.platform_type, entry.title, entry.context_entry_id),
                    )
                )
                continue
            carried = _carried_forward_national_entry(item, category, national_carry_forward)
            if carried is not None:
                inventory.append(carried)
                continue
            level, organization, platform_type = CATEGORY_DEFAULTS[category]
            if category == "state_democratic_party":
                organization = f"{item.state} Democratic Party"
            inventory.append(
                ContextEntry(
                    context_entry_id=_synthetic_id(item, category, ""),
                    state=item.state,
                    state_code=item.state_code,
                    cycle_year=item.cycle_year,
                    organization_level=level,
                    context_category=category,
                    organization=organization,
                    endorsing_body="",
                    title=_default_title(item, category, ""),
                    platform_type=platform_type,
                    adoption_date="",
                    effective_date="",
                    source_url="",
                    archive_url="",
                    verification_status="not_searched",
                    notes="No seed entry is cataloged yet for this represented state/cycle.",
                    synthetic=True,
                )
            )
    return sorted(inventory, key=lambda entry: (entry.state_code, entry.cycle_year, entry.context_category, entry.endorsing_body, entry.context_entry_id))


def _national_carry_forward_index(
    seed_entries: list[ContextEntry],
) -> dict[str, list[tuple[int, ContextEntry]]]:
    grouped: dict[str, dict[tuple[int, str, str], ContextEntry]] = defaultdict(dict)
    for entry in seed_entries:
        if (
            entry.context_category not in NATIONAL_CARRY_FORWARD_CATEGORIES
            or entry.organization_level != "national"
            or entry.verification_status != "verified"
        ):
            continue
        start_year = _effective_start_year(entry)
        key = (
            start_year,
            entry.source_url or entry.archive_url,
            entry.platform_type,
        )
        grouped[entry.context_category].setdefault(key, entry)
    return {
        category: sorted(
            [(start_year, entry) for (start_year, _, _), entry in entries.items()],
            key=lambda item: (item[0], item[1].cycle_year, item[1].context_entry_id),
        )
        for category, entries in grouped.items()
    }


def _effective_start_year(entry: ContextEntry) -> int:
    date_value = entry.effective_date or entry.adoption_date
    if date_value:
        match = re.match(r"^(\d{4})", date_value)
        if match:
            return int(match.group(1))
    return int(entry.cycle_year)


def _carried_forward_national_entry(
    item: RepresentedStateCycle,
    category: str,
    national_carry_forward: dict[str, list[tuple[int, ContextEntry]]],
) -> ContextEntry | None:
    if category not in NATIONAL_CARRY_FORWARD_CATEGORIES:
        return None
    try:
        target_year = int(item.cycle_year)
    except ValueError:
        return None
    applicable = [
        (start_year, entry)
        for start_year, entry in national_carry_forward.get(category, [])
        if start_year <= target_year
    ]
    if not applicable:
        return None
    _, seed = applicable[-1]
    return ContextEntry(
        context_entry_id=_carried_forward_id(item, seed),
        state=item.state,
        state_code=item.state_code,
        cycle_year=item.cycle_year,
        organization_level=seed.organization_level,
        context_category=seed.context_category,
        organization=seed.organization,
        endorsing_body="",
        title=_carried_forward_title(seed, item.cycle_year),
        platform_type=seed.platform_type,
        adoption_date=seed.adoption_date,
        effective_date=seed.effective_date,
        source_url=seed.source_url,
        archive_url=seed.archive_url,
        verification_status=seed.verification_status,
        notes=_carried_forward_notes(seed, item.cycle_year),
        synthetic=True,
    )


def _carried_forward_id(item: RepresentedStateCycle, seed: ContextEntry) -> str:
    digest = hashlib.sha256(
        f"{item.state_code}|{item.cycle_year}|{seed.context_entry_id}|carry_forward".encode("utf-8")
    ).hexdigest()[:16]
    return f"carry-{item.state_code.lower()}-{item.cycle_year}-{seed.context_category}-{digest}"


def _carried_forward_title(seed: ContextEntry, target_cycle_year: str) -> str:
    if seed.cycle_year == target_cycle_year:
        return seed.title
    return f"{seed.title} carried into the {target_cycle_year} cycle"


def _carried_forward_notes(seed: ContextEntry, target_cycle_year: str) -> str:
    note = (
        f"Carried forward from verified national entry {seed.context_entry_id} "
        f"with effective start {seed.effective_date or seed.adoption_date or seed.cycle_year}."
    )
    if seed.notes:
        note = f"{note} {seed.notes}"
    if seed.cycle_year == target_cycle_year:
        return note
    return f"{note} Applied to the {target_cycle_year} represented cycle until superseded by a later verified national entry."


def _synthetic_entry(item: RepresentedStateCycle, *, category: str, organization: str, endorsing_body: str, verification_status: str, notes: str) -> ContextEntry:
    level, _, platform_type = CATEGORY_DEFAULTS[category]
    return ContextEntry(
        context_entry_id=_synthetic_id(item, category, endorsing_body),
        state=item.state,
        state_code=item.state_code,
        cycle_year=item.cycle_year,
        organization_level=level,
        context_category=category,
        organization=organization,
        endorsing_body=endorsing_body,
        title=_default_title(item, category, endorsing_body),
        platform_type=platform_type,
        adoption_date="",
        effective_date="",
        source_url="",
        archive_url="",
        verification_status=verification_status,
        notes=notes,
        synthetic=True,
    )


def _synthetic_id(item: RepresentedStateCycle, category: str, endorsing_body: str) -> str:
    digest = hashlib.sha256(f"{item.state_code}|{item.cycle_year}|{category}|{endorsing_body}".encode("utf-8")).hexdigest()[:16]
    return f"synthetic-{item.state_code.lower()}-{item.cycle_year}-{category}-{digest}"


def _default_title(item: RepresentedStateCycle, category: str, endorsing_body: str) -> str:
    if category == "dnc_national":
        return f"DNC platform status for {item.cycle_year}"
    if category == "state_democratic_party":
        return f"{item.state} Democratic Party platform status for {item.cycle_year}"
    if category == "dsa_national":
        return f"DSA national program status for {item.cycle_year}"
    if endorsing_body:
        return f"{endorsing_body} electoral platform/questionnaire status for {item.cycle_year}"
    return f"Local DSA platform/questionnaire status for {item.cycle_year}"


def _coverage_rows(represented: list[RepresentedStateCycle], inventory_entries: list[ContextEntry]) -> list[dict[str, str]]:
    by_key: dict[tuple[str, str, str], list[ContextEntry]] = defaultdict(list)
    for entry in inventory_entries:
        by_key[(entry.state_code, entry.cycle_year, entry.context_category)].append(entry)
    rows = []
    for item in represented:
        row = {
            "corpus_scope": CORPUS_SCOPE,
            "state": item.state,
            "state_code": item.state_code,
            "cycle_year": item.cycle_year,
            "race_count": item.race_count,
            "race_ids": item.race_ids,
            "endorsed_candidates": item.endorsed_candidates,
            "endorsing_bodies": item.endorsing_bodies,
            "local_endorsing_bodies": item.local_endorsing_bodies,
        }
        all_categories_have_status = True
        for category in CONTEXT_CATEGORIES:
            entries = by_key.get((item.state_code, item.cycle_year, category), [])
            statuses = [entry.verification_status for entry in entries]
            row[f"{category}_status"] = _aggregate_status(statuses)
            row[f"{category}_entry_ids"] = " | ".join(entry.context_entry_id for entry in entries)
            if not statuses:
                all_categories_have_status = False
        row["all_categories_have_status"] = str(all_categories_have_status).lower()
        rows.append(row)
    return rows


def _aggregate_status(statuses: list[str]) -> str:
    if not statuses:
        return ""
    if all(status == "not_applicable" for status in statuses):
        return "not_applicable"
    if "not_searched" in statuses:
        return "not_searched"
    if "found_unverified" in statuses:
        return "found_unverified"
    if "searched_not_found" in statuses:
        return "searched_not_found"
    if "source_unavailable" in statuses:
        return "source_unavailable"
    if all(status == "verified" for status in statuses):
        return "verified"
    return statuses[0]


def _collection_queue_rows(entries: list[ContextEntry]) -> list[dict[str, str]]:
    rows = []
    for entry in entries:
        if entry.verification_status in {"verified", "not_applicable"}:
            continue
        rows.append(
            {
                "priority_rank": "",
                "priority_score": str(_priority_score(entry)),
                "state": entry.state,
                "state_code": entry.state_code,
                "cycle_year": entry.cycle_year,
                "context_category": entry.context_category,
                "organization_level": entry.organization_level,
                "organization": entry.organization,
                "endorsing_body": entry.endorsing_body,
                "verification_status": entry.verification_status,
                "context_entry_id": entry.context_entry_id,
                "title": entry.title,
                "platform_type": entry.platform_type,
                "source_url": entry.source_url,
                "archive_url": entry.archive_url,
                "queue_reason": _queue_reason(entry.verification_status, entry.synthetic),
                "notes": entry.notes,
                "synthetic": str(entry.synthetic).lower(),
            }
        )
    rows.sort(key=lambda row: (-int(row["priority_score"]), row["state_code"], row["cycle_year"], row["context_category"], row["organization"]))
    for number, row in enumerate(rows, start=1):
        row["priority_rank"] = str(number)
    return rows


def _priority_score(entry: ContextEntry) -> int:
    category_weight = {
        "state_democratic_party": 90,
        "dnc_national": 80,
        "dsa_national": 70,
        "dsa_state_local": 60,
    }[entry.context_category]
    status_weight = {
        "not_searched": 50,
        "found_unverified": 40,
        "searched_not_found": 35,
        "source_unavailable": 20,
        "verified": 0,
        "not_applicable": 0,
    }[entry.verification_status]
    year_weight = max(2050 - int(entry.cycle_year), 1)
    synthetic_penalty = 5 if entry.synthetic else 0
    return category_weight + status_weight + year_weight + synthetic_penalty


def _queue_reason(status: str, synthetic: bool) -> str:
    if synthetic:
        return "add_registry_seed"
    return {
        "not_searched": "search_for_official_source",
        "found_unverified": "verify_located_source",
        "searched_not_found": "retry_historical_source_search",
        "source_unavailable": "seek_archive_or_contact_organization",
        "verified": "",
        "not_applicable": "",
    }[status]


def _fetch_queue_rows(entries: list[ContextEntry]) -> list[dict[str, str]]:
    grouped: dict[str, dict[str, set[str] | str]] = {}
    for entry in entries:
        if entry.verification_status not in {"verified", "found_unverified"}:
            continue
        fetch_url = entry.source_url or entry.archive_url
        if not fetch_url:
            continue
        group = grouped.setdefault(
            fetch_url,
            {
                "archive_url": entry.archive_url,
                "context_entry_ids": set(),
                "states": set(),
                "cycles": set(),
                "context_categories": set(),
                "organizations": set(),
            },
        )
        group["context_entry_ids"].add(entry.context_entry_id)
        group["states"].add(entry.state_code)
        group["cycles"].add(entry.cycle_year)
        group["context_categories"].add(entry.context_category)
        group["organizations"].add(entry.organization)
        if not str(group["archive_url"]):
            group["archive_url"] = entry.archive_url
    rows = []
    for fetch_url, group in grouped.items():
        rows.append(
            {
                "fetch_id": hashlib.sha256(fetch_url.encode("utf-8")).hexdigest()[:24],
                "fetch_url": fetch_url,
                "archive_url": str(group["archive_url"]),
                "context_entry_ids": " | ".join(sorted(group["context_entry_ids"])),
                "states": " | ".join(sorted(group["states"])),
                "cycles": " | ".join(sorted(group["cycles"])),
                "context_categories": " | ".join(sorted(group["context_categories"])),
                "organizations": " | ".join(sorted(group["organizations"])),
                "source_count": str(len(group["context_entry_ids"])),
            }
        )
    return sorted(rows, key=lambda row: (row["states"], row["cycles"], row["fetch_url"]))


def _summary(
    represented: list[RepresentedStateCycle],
    entries: list[ContextEntry],
    coverage_rows: list[dict[str, str]],
    collection_rows: list[dict[str, str]],
    fetch_queue_rows: list[dict[str, str]],
    platform_gap_rows: int,
) -> dict[str, object]:
    return {
        "corpus_scope": CORPUS_SCOPE,
        "represented_states": sorted({item.state_code for item in represented}),
        "represented_state_cycles": len(represented),
        "inventory": {
            "row_count": len(entries),
            "by_context_category": dict(sorted(Counter(entry.context_category for entry in entries).items())),
            "by_verification_status": dict(sorted(Counter(entry.verification_status for entry in entries).items())),
        },
        "coverage": {
            "row_count": len(coverage_rows),
            "all_represented_state_cycles_have_status": all(row["all_categories_have_status"] == "true" for row in coverage_rows),
            "platform_gap_rows": platform_gap_rows,
            "gap_state_cycles": [
                {
                    "state_code": row["state_code"],
                    "cycle_year": row["cycle_year"],
                    "dnc_national_status": row["dnc_national_status"],
                    "state_democratic_party_status": row["state_democratic_party_status"],
                    "dsa_national_status": row["dsa_national_status"],
                    "dsa_state_local_status": row["dsa_state_local_status"],
                }
                for row in coverage_rows
                if any(row[f"{category}_status"] in GAP_STATUSES for category in CONTEXT_CATEGORIES)
            ],
        },
        "collection_queue": {
            "row_count": len(collection_rows),
            "top_priority": collection_rows[:5],
        },
        "fetch_queue": {
            "row_count": len(fetch_queue_rows),
            "verified_url_count": len(fetch_queue_rows),
        },
    }


def _fetch_url(url: str, *, timeout: int) -> FetchCapture:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    retrieved_at = datetime.now(UTC).isoformat()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return FetchCapture(
                fetch_url=url,
                final_url=response.geturl(),
                retrieved_at=retrieved_at,
                content_type=response.headers.get_content_type(),
                content_bytes=response.read(),
                status_code=response.status,
            )
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise OrganizationalContextFetchError(f"failed to fetch {url}: {type(error).__name__}: {error}") from error


def _raise_for_access_block(capture: FetchCapture) -> None:
    if capture.content_type not in {"text/html", "application/xhtml+xml"}:
        return
    sample = capture.content_bytes[:16_384].lower()
    markers = (
        b"/.well-known/sgcaptcha/",
        b"cf-chl-",
        b"cloudflare ray id",
        b"<title>just a moment",
    )
    if any(marker in sample for marker in markers):
        raise OrganizationalContextFetchError(
            f"failed to fetch {capture.fetch_url}: access challenge page returned"
        )


def _persist_fetch_capture(raw_dir: Path, fetch_id: str, capture: FetchCapture) -> Path:
    suffix = _suffix(capture.final_url or capture.fetch_url, capture.content_type)
    output_path = raw_dir / f"{fetch_id}{suffix}"
    output_path.write_bytes(capture.content_bytes)
    return output_path


def _suffix(url: str, content_type: str) -> str:
    path_suffix = Path(urlparse(url).path).suffix
    if path_suffix:
        return path_suffix
    return mimetypes.guess_extension(content_type) or ".bin"


def _state_name(state_code: str) -> str:
    if state_code in STATE_NAME_BY_CODE:
        return STATE_NAME_BY_CODE[state_code]
    if (PROCESSED_DIR / "race_registry_represented_state_cycles.csv").exists():
        with (PROCESSED_DIR / "race_registry_represented_state_cycles.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("state_code") == state_code:
                    return row.get("state", "")
    return state_code


def _identity(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _local_body_identity(value: str) -> str:
    identity = _identity(value)
    identity = re.sub(r"\bdemocratic socialists of america\b", " ", identity)
    identity = re.sub(r"\bdsa\b", " ", identity)
    identity = re.sub(r"\bchapter\b", " ", identity)
    return re.sub(r"[^a-z0-9]+", " ", identity).strip()
