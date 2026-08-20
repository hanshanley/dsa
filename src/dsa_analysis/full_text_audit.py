from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .document_corpus import (
    build_candidate_document_discovery_queue,
    build_candidate_source_inventory,
    canonical_source_url,
    candidate_document_id,
    candidate_slug,
    classify_source_type,
    normalize_source_url,
)
from .io import merge_notes, read_csv, read_json, write_csv
from .paths import ANALYSIS_DATA_DIR, CONFIG_DIR, MANUAL_DIR, PROCESSED_DIR

CORPUS_STATUSES = {"verified", "source_unavailable"}
QUEUE_STATUSES = {
    "verified",
    "source_unavailable",
    "not_searched",
    "found_unverified",
    "searched_not_found",
    "not_applicable",
}
QUEUE_ROLES = {"endorsed", "opponent", "unopposed"}
RETRYABLE_STATUSES = {"not_searched", "found_unverified", "searched_not_found"}
SUBSTANTIVE_MIN_TOKENS = 20
DOCUMENT_QUEUE_SEED_PRIORITY = {
    "known_document": 1,
    "queue_reference": 2,
    "campaign_domain": 3,
    "official_election_source": 4,
    "endorsement_source": 5,
}


@dataclass(frozen=True)
class FullTextAuditPaths:
    candidate_corpus_path: Path
    config_path: Path
    manual_documents_path: Path
    manual_candidate_documents_path: Path
    manual_endorsements_path: Path
    manual_race_candidates_path: Path
    processed_opponent_queue_path: Path
    processed_race_rosters_path: Path
    processed_candidate_evidence_path: Path
    candidate_document_metadata_path: Path
    candidate_document_full_text_path: Path
    candidate_document_analysis_segments_path: Path
    output_dir: Path
    race_registry_path: Path | None = None

    @classmethod
    def default(cls) -> "FullTextAuditPaths":
        return cls(
            candidate_corpus_path=ANALYSIS_DATA_DIR / "candidate_text_corpus.csv",
            config_path=CONFIG_DIR / "sources.json",
            manual_documents_path=MANUAL_DIR / "documents.csv",
            manual_candidate_documents_path=MANUAL_DIR / "candidate_documents.csv",
            manual_endorsements_path=MANUAL_DIR / "endorsements.csv",
            manual_race_candidates_path=MANUAL_DIR / "race_candidates.csv",
            processed_opponent_queue_path=PROCESSED_DIR / "opponent_research_queue.csv",
            processed_race_rosters_path=PROCESSED_DIR / "race_rosters_discovered.csv",
            processed_candidate_evidence_path=PROCESSED_DIR
            / "candidate_statement_evidence.csv",
            candidate_document_metadata_path=PROCESSED_DIR
            / "candidate_document_metadata.csv",
            candidate_document_full_text_path=PROCESSED_DIR
            / "candidate_document_full_text.jsonl",
            candidate_document_analysis_segments_path=PROCESSED_DIR
            / "candidate_document_analysis_segments.csv",
            output_dir=PROCESSED_DIR,
            race_registry_path=PROCESSED_DIR / "race_registry.csv",
        )


@dataclass(frozen=True)
class FullTextAuditResult:
    queue_source: str
    corpus_rows: int
    queue_candidate_rows: int
    eligible_races: int
    retryable_gaps: int
    sufficient: bool
    failed_gates: tuple[str, ...]
    summary_path: Path
    corpus_summary_path: Path
    queue_summary_path: Path
    race_summary_path: Path
    paired_race_path: Path
    retryable_gaps_path: Path
    document_queue_path: Path
    source_inventory_path: Path
    discovery_queue_path: Path
    group_year_support_path: Path
    source_class_support_path: Path
    imbalance_diagnostics_path: Path


def build_full_text_sufficiency_audit(
    paths: FullTextAuditPaths | None = None,
) -> FullTextAuditResult:
    paths = paths or FullTextAuditPaths.default()
    study_start_year, final_year = _study_window(paths.config_path)
    expected_years = list(range(study_start_year, final_year + 1))

    corpus_rows = _load_corpus_rows(paths.candidate_corpus_path, expected_years)
    queue_source, queue_candidates = _load_queue_candidates(paths, expected_years)
    roster_rows = _load_roster_rows(paths, expected_years)
    manual_candidate_document_rows = _load_manual_candidate_document_rows(
        paths.manual_candidate_documents_path,
        expected_years,
    )

    source_inventory_rows = build_candidate_source_inventory(
        corpus_rows,
        roster_rows,
        manual_candidate_document_rows,
    )
    discovery_queue_rows = build_candidate_document_discovery_queue(
        corpus_rows,
        roster_rows,
        manual_candidate_document_rows,
    )

    metadata_rows = _load_document_metadata_rows(paths.candidate_document_metadata_path)
    full_text_rows = _load_jsonl_rows(paths.candidate_document_full_text_path)
    analysis_segment_rows = _load_analysis_segment_rows(
        paths.candidate_document_analysis_segments_path
    )
    document_support = _document_support_snapshot(metadata_rows, analysis_segment_rows)
    paired_race_rows = _paired_race_rows_from_clean_documents(
        metadata_rows,
        analysis_segment_rows,
        document_support["candidate_index"],
    )

    race_summary_rows = _race_summary_rows(queue_candidates, document_support["candidate_index"])
    race_index = {row["race_id"]: row for row in race_summary_rows}
    coverage_gap_rows = _coverage_gap_rows(queue_candidates, queue_source, expected_years)
    retryable_gap_rows = _retryable_gap_rows(
        queue_candidates,
        race_index,
        coverage_gap_rows,
    )
    priority_rows = _priority_rows(
        retryable_gap_rows,
        study_start_year,
        final_year,
    )
    document_queue_rows = _build_candidate_document_queue_rows(
        source_inventory_rows=source_inventory_rows,
        discovery_queue_rows=discovery_queue_rows,
        queue_candidates=queue_candidates,
        metadata_rows=metadata_rows,
        analysis_segment_rows=analysis_segment_rows,
    )
    group_year_support_rows = _group_year_support_rows(
        queue_candidates,
        document_support["candidate_index"],
        expected_years,
    )
    source_class_support_rows = _source_class_support_rows(
        source_inventory_rows,
        document_support["candidate_index"],
    )
    imbalance_rows = _imbalance_diagnostic_rows(
        document_support["candidate_index"],
        group_year_support_rows,
        source_class_support_rows,
    )

    hard_gates = _hard_gate_summary(
        expected_years=expected_years,
        queue_candidates=queue_candidates,
        race_summary_rows=race_summary_rows,
        source_inventory_rows=source_inventory_rows,
        group_year_support_rows=group_year_support_rows,
        source_class_support_rows=source_class_support_rows,
        imbalance_rows=imbalance_rows,
        paired_race_rows=paired_race_rows,
    )
    summary = _summary(
        queue_source=queue_source,
        corpus_rows=corpus_rows,
        queue_candidates=queue_candidates,
        race_summary_rows=race_summary_rows,
        paired_race_rows=paired_race_rows,
        retryable_gap_rows=retryable_gap_rows,
        expected_years=expected_years,
        study_start_year=study_start_year,
        source_inventory_rows=source_inventory_rows,
        discovery_queue_rows=discovery_queue_rows,
        document_queue_rows=document_queue_rows,
        metadata_rows=metadata_rows,
        full_text_rows=full_text_rows,
        analysis_segment_rows=analysis_segment_rows,
        document_support=document_support,
        group_year_support_rows=group_year_support_rows,
        source_class_support_rows=source_class_support_rows,
        imbalance_rows=imbalance_rows,
        hard_gates=hard_gates,
    )

    paths.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = paths.output_dir / "full_text_audit_summary.json"
    corpus_summary_path = paths.output_dir / "full_text_corpus_summary.csv"
    queue_summary_path = paths.output_dir / "full_text_queue_summary.csv"
    race_summary_path = paths.output_dir / "full_text_race_summary.csv"
    paired_race_path = paths.output_dir / "paired_race_eligibility.csv"
    retryable_gaps_path = paths.output_dir / "full_text_retryable_gaps.csv"
    document_queue_path = paths.output_dir / "candidate_document_queue.csv"
    source_inventory_path = paths.output_dir / "candidate_source_inventory.csv"
    discovery_queue_path = paths.output_dir / "candidate_document_discovery_queue.csv"
    group_year_support_path = paths.output_dir / "full_text_group_year_support.csv"
    source_class_support_path = paths.output_dir / "full_text_source_class_support.csv"
    imbalance_diagnostics_path = paths.output_dir / "full_text_imbalance_diagnostics.csv"
    priority_queue_path = paths.output_dir / "document_regather_priority.csv"

    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(
        corpus_summary_path,
        _corpus_summary_rows(corpus_rows),
        [
            "corpus_kind",
            "group",
            "election_year",
            "source_type_class",
            "source_type",
            "evidence_status",
            "row_count",
            "unique_candidates",
            "unique_races",
        ],
    )
    write_csv(
        queue_summary_path,
        _queue_summary_rows(queue_candidates, queue_source),
        [
            "queue_source",
            "group",
            "election_year",
            "current_status",
            "candidate_count",
            "race_count",
        ],
    )
    write_csv(
        race_summary_path,
        race_summary_rows,
        [
            "queue_source",
            "race_id",
            "election_year",
            "endorsed_candidates",
            "opponent_candidates",
            "verified_candidates",
            "source_unavailable_candidates",
            "retryable_gap_candidates",
            "endorsed_verified_candidates",
            "opponent_verified_candidates",
            "endorsed_retryable_candidates",
            "opponent_retryable_candidates",
            "endorsed_substantive_candidates",
            "opponent_substantive_candidates",
            "substantive_document_count",
            "substantive_segment_count",
            "substantive_source_classes",
            "paired_race_eligible",
            "paired_race_retryable",
            "pair_completion_gap_count",
            "paired_race_gap_reason",
        ],
    )
    write_csv(
        paired_race_path,
        [
            _select_fields(
                row,
                [
                    "race_id",
                    "election_year",
                    "paired_race_eligible",
                    "endorsed_clean_candidates",
                    "opponent_clean_candidates",
                    "clean_document_count",
                    "clean_analysis_segment_count",
                    "clean_source_classes",
                    "endorsed_substantive_candidates",
                    "opponent_substantive_candidates",
                    "substantive_document_count",
                    "substantive_segment_count",
                    "substantive_source_classes",
                    "paired_race_gap_reason",
                ],
            )
            for row in paired_race_rows
        ],
        [
            "race_id",
            "election_year",
            "paired_race_eligible",
            "endorsed_clean_candidates",
            "opponent_clean_candidates",
            "clean_document_count",
            "clean_analysis_segment_count",
            "clean_source_classes",
            "endorsed_substantive_candidates",
            "opponent_substantive_candidates",
            "substantive_document_count",
            "substantive_segment_count",
            "substantive_source_classes",
            "paired_race_gap_reason",
        ],
    )
    write_csv(
        retryable_gaps_path,
        retryable_gap_rows,
        [
            "gap_type",
            "queue_source",
            "election_year",
            "race_id",
            "candidate_name",
            "group",
            "role",
            "current_status",
            "paired_race_eligible",
            "would_unlock_paired_race",
            "pair_completion_gap_count",
            "reference_url",
            "endorsement_source_url",
            "gap_reason",
            "notes",
        ],
    )
    write_csv(
        priority_queue_path,
        priority_rows,
        [
            "priority_rank",
            "priority_score",
            "priority_reasons",
            "gap_type",
            "queue_source",
            "election_year",
            "race_id",
            "candidate_name",
            "group",
            "role",
            "current_status",
            "paired_race_eligible",
            "would_unlock_paired_race",
            "pair_completion_gap_count",
            "reference_url",
            "endorsement_source_url",
            "gap_reason",
            "notes",
        ],
    )
    write_csv(
        source_inventory_path,
        source_inventory_rows,
        [
            "source_record_id",
            "queue_id",
            "race_id",
            "candidate_slug",
            "candidate_name",
            "role",
            "election_date",
            "official_election_source",
            "source_url",
            "fetch_url",
            "archive_url",
            "live_url",
            "source_domain",
            "campaign_domain",
            "source_type",
            "source_type_class",
            "source_tier",
            "publication_date",
            "effective_date",
            "analysis_scope",
            "evidence_status",
            "statement_count",
            "statement_keys",
            "legacy_locators",
            "notes",
        ],
    )
    write_csv(
        discovery_queue_path,
        discovery_queue_rows,
        [
            "discovery_seed_id",
            "queue_id",
            "race_id",
            "candidate_slug",
            "candidate_name",
            "role",
            "election_date",
            "campaign_domain",
            "official_election_source",
            "seed_url",
            "seed_kind",
            "seed_priority",
            "source_record_id",
            "source_type_class",
            "source_tier",
            "publication_date",
            "effective_date",
            "archive_url",
            "live_url",
            "analysis_scope",
            "known_source_count",
            "legacy_locators",
            "current_status",
            "notes",
        ],
    )
    write_csv(
        document_queue_path,
        document_queue_rows,
        [
            "document_id",
            "queue_id",
            "race_id",
            "candidate_slug",
            "candidate_name",
            "role",
            "election_date",
            "publication_date",
            "effective_date",
            "source_type",
            "source_type_class",
            "source_url",
            "archive_url",
            "live_url",
            "source_tier",
            "analysis_scope",
            "campaign_domain",
            "official_election_source",
            "seed_kinds",
            "seed_priority",
            "source_record_ids",
            "legacy_locators",
            "known_source_count",
            "legacy_statement_count",
            "collection_status",
            "metadata_status",
            "analysis_segment_count",
            "substantive_segment_count",
            "notes",
        ],
    )
    write_csv(
        group_year_support_path,
        group_year_support_rows,
        [
            "group",
            "election_year",
            "queue_candidate_count",
            "queue_race_count",
            "substantive_candidate_count",
            "substantive_race_count",
            "substantive_document_count",
            "substantive_segment_count",
            "source_class_count",
            "coverage_ratio",
            "missing_support",
        ],
    )
    write_csv(
        source_class_support_path,
        source_class_support_rows,
        [
            "source_type_class",
            "group",
            "inventory_candidate_count",
            "inventory_race_count",
            "inventory_source_count",
            "substantive_candidate_count",
            "substantive_race_count",
            "substantive_document_count",
            "substantive_segment_count",
            "coverage_ratio",
            "missing_support",
        ],
    )
    write_csv(
        imbalance_diagnostics_path,
        imbalance_rows,
        [
            "dimension",
            "bucket",
            "endorsed_candidate_count",
            "opponent_candidate_count",
            "endorsed_document_count",
            "opponent_document_count",
            "endorsed_segment_count",
            "opponent_segment_count",
            "imbalance_ratio",
            "flag_reason",
            "hard_gate_pass",
        ],
    )

    return FullTextAuditResult(
        queue_source=queue_source,
        corpus_rows=len(corpus_rows),
        queue_candidate_rows=len(queue_candidates),
        eligible_races=sum(row["paired_race_eligible"] == "true" for row in paired_race_rows),
        retryable_gaps=len(retryable_gap_rows),
        sufficient=hard_gates["passes"],
        failed_gates=tuple(hard_gates["failed_gates"]),
        summary_path=summary_path,
        corpus_summary_path=corpus_summary_path,
        queue_summary_path=queue_summary_path,
        race_summary_path=race_summary_path,
        paired_race_path=paired_race_path,
        retryable_gaps_path=retryable_gaps_path,
        document_queue_path=document_queue_path,
        source_inventory_path=source_inventory_path,
        discovery_queue_path=discovery_queue_path,
        group_year_support_path=group_year_support_path,
        source_class_support_path=source_class_support_path,
        imbalance_diagnostics_path=imbalance_diagnostics_path,
    )


def _study_window(config_path: Path) -> tuple[int, int]:
    config = read_json(config_path)
    start_year = _year_from_value(config.get("study_start", ""), config_path.name, "study_start")
    final_year = _year_from_value(
        config.get("research_cutoff", ""),
        config_path.name,
        "research_cutoff",
    )
    if start_year > final_year:
        raise ValueError(f"{config_path.name}: study_start exceeds research_cutoff")
    return start_year, final_year


def _load_corpus_rows(path: Path, expected_years: list[int]) -> list[dict[str, str]]:
    rows = read_csv(path)
    required = {
        "race_id",
        "candidate_name",
        "election_date",
        "role",
        "evidence_status",
        "quote",
        "source_url",
        "source_type",
    }
    missing = required - set(rows[0]) if rows else set()
    if missing:
        raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
    allowed_years = {str(year) for year in expected_years}
    output = []
    for number, row in enumerate(rows, start=2):
        role = row.get("role", "").strip()
        if role not in QUEUE_ROLES:
            raise ValueError(f"{path.name}:{number}: invalid role")
        status = row.get("evidence_status", "").strip()
        if status not in CORPUS_STATUSES:
            raise ValueError(f"{path.name}:{number}: invalid evidence_status")
        election_date = row.get("election_date", "").strip()
        year = _year_from_value(election_date, path.name, f"row {number} election_date")
        if str(year) not in allowed_years:
            raise ValueError(f"{path.name}:{number}: election year outside study window")
        if status == "verified" and (
            not row.get("quote", "").strip() or not row.get("source_url", "").strip()
        ):
            raise ValueError(
                f"{path.name}:{number}: verified row requires quote and source_url"
            )
        source_type = row.get("source_type", "").strip() or "unspecified"
        source_url = row.get("source_url", "").strip()
        output.append(
            {
                "statement_key": row.get("statement_key", "").strip(),
                "race_id": row["race_id"].strip(),
                "candidate_name": row["candidate_name"].strip(),
                "candidate_slug": candidate_slug(row["candidate_name"].strip()),
                "group": "endorsed" if role in {"endorsed", "unopposed"} else "opponent",
                "role": role,
                "election_date": election_date,
                "election_year": str(year),
                "evidence_status": status,
                "quote": row.get("quote", "").strip(),
                "source_url": source_url,
                "source_type": source_type,
                "source_type_class": classify_source_type(source_type, source_url),
                "published_date": row.get("published_date", "").strip(),
                "locator": row.get("locator", "").strip(),
                "notes": row.get("notes", "").strip(),
            }
        )
    return output


def _load_manual_candidate_document_rows(
    path: Path,
    expected_years: list[int],
) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows = read_csv(path)
    allowed_years = {str(year) for year in expected_years}
    output: list[dict[str, str]] = []
    for number, row in enumerate(rows, start=2):
        election_date = row.get("election_date", "").strip()
        year = _year_from_value(election_date, path.name, f"row {number} election_date")
        if str(year) not in allowed_years:
            raise ValueError(f"{path.name}:{number}: election year outside study window")
        output.append(row)
    return output


def _load_queue_candidates(
    paths: FullTextAuditPaths,
    expected_years: list[int],
) -> tuple[str, list[dict[str, str]]]:
    if paths.race_registry_path and paths.race_registry_path.exists():
        return "registry", _load_registry_queue(paths, expected_years)
    if paths.processed_race_rosters_path.exists():
        return "processed", _load_processed_queue(paths, expected_years)
    return "manual", _load_manual_queue(paths, expected_years)


def _load_registry_queue(
    paths: FullTextAuditPaths,
    expected_years: list[int],
) -> list[dict[str, str]]:
    registry_rows = read_csv(paths.race_registry_path)  # type: ignore[arg-type]
    metadata_rows = _load_document_metadata_rows(
        paths.candidate_document_metadata_path
    )
    allowed_years = {str(year) for year in expected_years}
    candidate_occurrences: Counter[tuple[str, str]] = Counter()
    for row in registry_rows:
        if (
            row.get("scope_kind", "").strip()
            != "tracked_dsa_endorsed_democratic_primary"
        ):
            continue
        year = row.get("election_date", "").strip()[:4]
        row_candidates: set[tuple[str, str]] = set()
        for field in (
            "endorsed_candidates",
            "unopposed_candidates",
            "opponent_candidates",
        ):
            row_candidates.update(
                (_identity(name), year) for name in _pipe_values(row.get(field, ""))
            )
        candidate_occurrences.update(row_candidates)
    output: list[dict[str, str]] = []
    for number, row in enumerate(registry_rows, start=2):
        if (
            row.get("scope_kind", "").strip()
            != "tracked_dsa_endorsed_democratic_primary"
        ):
            continue
        election_date = row.get("election_date", "").strip()
        year = str(
            _year_from_value(
                election_date,
                paths.race_registry_path.name,  # type: ignore[union-attr]
                f"row {number} election_date",
            )
        )
        if year not in allowed_years:
            continue
        source_race_ids = set(
            _pipe_values(row.get("source_race_ids", ""))
            or [row.get("race_id", "").strip()]
        )
        candidate_roles: list[tuple[str, str]] = []
        candidate_roles.extend(
            (name, "endorsed")
            for name in _pipe_values(row.get("endorsed_candidates", ""))
        )
        candidate_roles.extend(
            (name, "unopposed")
            for name in _pipe_values(row.get("unopposed_candidates", ""))
        )
        candidate_roles.extend(
            (name, "opponent")
            for name in _pipe_values(row.get("opponent_candidates", ""))
        )
        seen_candidates: set[tuple[str, str]] = set()
        for candidate_name, role in candidate_roles:
            group = "endorsed" if role in {"endorsed", "unopposed"} else "opponent"
            candidate_key = (group, _identity(candidate_name))
            if candidate_key in seen_candidates:
                continue
            seen_candidates.add(candidate_key)
            matching_metadata = [
                metadata
                for metadata in metadata_rows
                if metadata.get("race_id", "").strip() in source_race_ids
                and _identity(metadata.get("candidate_name", "")) == candidate_key[1]
            ]
            if (
                candidate_occurrences[(candidate_key[1], year)] == 1
                or "president" in _identity(row.get("office", ""))
            ):
                fallback_metadata = [
                    metadata
                    for metadata in metadata_rows
                    if metadata.get("election_year", "") == year
                    and _identity(metadata.get("candidate_name", "")) == candidate_key[1]
                ]
                matching_document_ids = {
                    metadata.get("document_id", "") for metadata in matching_metadata
                }
                matching_metadata.extend(
                    metadata
                    for metadata in fallback_metadata
                    if metadata.get("document_id", "") not in matching_document_ids
                )
            if any(
                metadata.get("extraction_status", "").strip() == "extracted"
                and metadata.get("analysis_scope", "analysis").strip() == "analysis"
                for metadata in matching_metadata
            ):
                status = "verified"
            elif matching_metadata and all(
                metadata.get("coverage_status", "").strip() == "source_unavailable"
                for metadata in matching_metadata
            ):
                status = "source_unavailable"
            elif matching_metadata:
                status = "found_unverified"
            else:
                status = "not_searched"
            output.append(
                {
                    "queue_source": "registry",
                    "race_id": row.get("race_id", "").strip(),
                    "candidate_name": candidate_name,
                    "candidate_slug": candidate_slug(candidate_name),
                    "group": group,
                    "role": role,
                    "election_date": election_date,
                    "election_year": year,
                    "current_status": status,
                    "reference_url": row.get(
                        "official_election_source", ""
                    ).strip(),
                    "endorsement_source_url": "",
                    "notes": (
                        "Seeded from the endorsement-first canonical race registry."
                    ),
                }
            )
    return output


def _load_manual_queue(
    paths: FullTextAuditPaths,
    expected_years: list[int],
) -> list[dict[str, str]]:
    endorsements = read_csv(paths.manual_endorsements_path)
    race_candidates = read_csv(paths.manual_race_candidates_path)
    documents = {row["document_id"]: row for row in read_csv(paths.manual_documents_path)}
    allowed_years = {str(year) for year in expected_years}
    election_date_by_race: dict[str, str] = {}
    endorsement_urls_by_race: dict[str, set[str]] = defaultdict(set)
    for number, row in enumerate(endorsements, start=2):
        race_id = row.get("race_id", "").strip()
        election_date = row.get("election_date", "").strip()
        year = _year_from_value(
            election_date,
            paths.manual_endorsements_path.name,
            f"row {number} election_date",
        )
        if str(year) not in allowed_years:
            raise ValueError(
                f"{paths.manual_endorsements_path.name}:{number}: election year outside study window"
            )
        previous = election_date_by_race.setdefault(race_id, election_date)
        if previous != election_date:
            raise ValueError(
                f"{paths.manual_endorsements_path.name}:{number}: conflicting election_date for {race_id}"
            )
        document_id = row.get("endorsement_source_document_id", "").strip()
        if document_id:
            if document_id not in documents:
                raise ValueError(
                    f"{paths.manual_endorsements_path.name}:{number}: unknown endorsement_source_document_id"
                )
            url = documents[document_id].get("url", "").strip()
            if url:
                endorsement_urls_by_race[race_id].add(url)

    output = []
    for number, row in enumerate(race_candidates, start=2):
        role = row.get("role", "").strip()
        if role not in QUEUE_ROLES:
            raise ValueError(f"{paths.manual_race_candidates_path.name}:{number}: invalid role")
        status = row.get("evidence_status", "").strip()
        if status not in QUEUE_STATUSES - {"not_applicable"}:
            raise ValueError(
                f"{paths.manual_race_candidates_path.name}:{number}: invalid evidence_status"
            )
        race_id = row.get("race_id", "").strip()
        election_date = election_date_by_race.get(race_id, "")
        if not election_date:
            raise ValueError(
                f"{paths.manual_race_candidates_path.name}:{number}: missing endorsement election_date for {race_id}"
            )
        year = str(
            _year_from_value(
                election_date,
                paths.manual_race_candidates_path.name,
                f"row {number} election_date",
            )
        )
        candidate_name = row.get("candidate_name", "").strip()
        output.append(
            {
                "queue_source": "manual",
                "race_id": race_id,
                "candidate_name": candidate_name,
                "candidate_slug": candidate_slug(candidate_name),
                "group": "endorsed" if role in {"endorsed", "unopposed"} else "opponent",
                "role": role,
                "election_date": election_date,
                "election_year": year,
                "current_status": status,
                "reference_url": row.get("source_url", "").strip(),
                "endorsement_source_url": " | ".join(sorted(endorsement_urls_by_race[race_id])),
                "notes": row.get("notes", "").strip(),
            }
        )
    return output


def _load_processed_queue(
    paths: FullTextAuditPaths,
    expected_years: list[int],
) -> list[dict[str, str]]:
    rosters = read_csv(paths.processed_race_rosters_path)
    queue_rows = (
        read_csv(paths.processed_opponent_queue_path)
        if paths.processed_opponent_queue_path.exists()
        else []
    )
    queue_by_id = {row.get("queue_id", "").strip(): row for row in queue_rows}
    evidence_by_candidate = _processed_candidate_status(paths.processed_candidate_evidence_path)
    allowed_years = {str(year) for year in expected_years}
    output = []
    for number, row in enumerate(rosters, start=2):
        role = row.get("role", "").strip()
        if role not in QUEUE_ROLES:
            raise ValueError(f"{paths.processed_race_rosters_path.name}:{number}: invalid role")
        resolution = row.get("resolution_status", "").strip()
        if resolution not in {"verified", "not_a_primary", "source_unavailable"}:
            raise ValueError(
                f"{paths.processed_race_rosters_path.name}:{number}: invalid resolution_status"
            )
        election_date = row.get("election_date", "").strip()
        year = str(
            _year_from_value(
                election_date,
                paths.processed_race_rosters_path.name,
                f"row {number} election_date",
            )
        )
        if year not in allowed_years:
            raise ValueError(
                f"{paths.processed_race_rosters_path.name}:{number}: election year outside study window"
            )
        queue_id = row.get("queue_id", "").strip()
        queue_row = queue_by_id.get(queue_id, {})
        group = "endorsed" if role in {"endorsed", "unopposed"} else "opponent"
        if resolution == "not_a_primary":
            status = "not_applicable"
        elif resolution == "source_unavailable":
            status = "source_unavailable"
        else:
            status = evidence_by_candidate.get(
                (queue_id, _identity(row.get("candidate_name", "")), group)
            )
            if not status:
                status = (
                    queue_row.get("candidate_statement_status", "not_searched")
                    if group == "endorsed"
                    else queue_row.get("opponent_statement_status", "not_searched")
                ).strip() or "not_searched"
            if status not in QUEUE_STATUSES:
                raise ValueError(
                    f"{paths.processed_race_rosters_path.name}:{number}: invalid derived status"
                )
        candidate_name = row.get("candidate_name", "").strip()
        output.append(
            {
                "queue_source": "processed",
                "race_id": row.get("race_id", "").strip(),
                "candidate_name": candidate_name,
                "candidate_slug": candidate_slug(candidate_name),
                "group": group,
                "role": role,
                "election_date": election_date,
                "election_year": year,
                "current_status": status,
                "reference_url": row.get("official_election_source", "").strip(),
                "endorsement_source_url": queue_row.get("endorsement_source_url", "").strip(),
                "notes": row.get("notes", "").strip() or queue_row.get("notes", "").strip(),
            }
        )
    return output


def _load_roster_rows(
    paths: FullTextAuditPaths,
    expected_years: list[int],
) -> list[dict[str, str]]:
    allowed_years = {str(year) for year in expected_years}
    if paths.race_registry_path and paths.race_registry_path.exists():
        output = []
        for number, row in enumerate(
            read_csv(paths.race_registry_path),
            start=2,
        ):
            if (
                row.get("scope_kind", "").strip()
                != "tracked_dsa_endorsed_democratic_primary"
            ):
                continue
            election_date = row.get("election_date", "").strip()
            year = str(
                _year_from_value(
                    election_date,
                    paths.race_registry_path.name,
                    f"row {number} election_date",
                )
            )
            if year not in allowed_years:
                continue
            roles = (
                ("endorsed_candidates", "endorsed"),
                ("unopposed_candidates", "unopposed"),
                ("opponent_candidates", "opponent"),
            )
            seen: set[tuple[str, str]] = set()
            for field, role in roles:
                for candidate_name in _pipe_values(row.get(field, "")):
                    key = (role, _identity(candidate_name))
                    if key in seen:
                        continue
                    seen.add(key)
                    output.append(
                        {
                            "queue_id": "",
                            "race_id": row.get("race_id", "").strip(),
                            "candidate_name": candidate_name,
                            "role": role,
                            "election_date": election_date,
                            "official_election_source": row.get(
                                "official_election_source", ""
                            ).strip(),
                        }
                    )
        return output
    if paths.processed_race_rosters_path.exists():
        rows = read_csv(paths.processed_race_rosters_path)
        output = []
        for number, row in enumerate(rows, start=2):
            role = row.get("role", "").strip()
            if role not in QUEUE_ROLES:
                raise ValueError(f"{paths.processed_race_rosters_path.name}:{number}: invalid role")
            election_date = row.get("election_date", "").strip()
            year = str(
                _year_from_value(
                    election_date,
                    paths.processed_race_rosters_path.name,
                    f"row {number} election_date",
                )
            )
            if year not in allowed_years:
                raise ValueError(
                    f"{paths.processed_race_rosters_path.name}:{number}: election year outside study window"
                )
            output.append(
                {
                    "queue_id": row.get("queue_id", "").strip(),
                    "race_id": row.get("race_id", "").strip(),
                    "candidate_name": row.get("candidate_name", "").strip(),
                    "role": role,
                    "election_date": election_date,
                    "official_election_source": row.get("official_election_source", "").strip(),
                }
            )
        return output

    endorsements = read_csv(paths.manual_endorsements_path)
    race_candidates = read_csv(paths.manual_race_candidates_path)
    election_date_by_race: dict[str, str] = {}
    for number, row in enumerate(endorsements, start=2):
        race_id = row.get("race_id", "").strip()
        election_date = row.get("election_date", "").strip()
        year = str(
            _year_from_value(
                election_date,
                paths.manual_endorsements_path.name,
                f"row {number} election_date",
            )
        )
        if year not in allowed_years:
            raise ValueError(
                f"{paths.manual_endorsements_path.name}:{number}: election year outside study window"
            )
        election_date_by_race[race_id] = election_date

    output = []
    for number, row in enumerate(race_candidates, start=2):
        role = row.get("role", "").strip()
        if role not in QUEUE_ROLES:
            raise ValueError(f"{paths.manual_race_candidates_path.name}:{number}: invalid role")
        race_id = row.get("race_id", "").strip()
        election_date = election_date_by_race.get(race_id, "")
        if not election_date:
            raise ValueError(
                f"{paths.manual_race_candidates_path.name}:{number}: missing endorsement election_date for {race_id}"
            )
        output.append(
            {
                "queue_id": "",
                "race_id": race_id,
                "candidate_name": row.get("candidate_name", "").strip(),
                "role": role,
                "election_date": election_date,
                "official_election_source": row.get("source_url", "").strip(),
            }
        )
    return output


def _pipe_values(value: str) -> list[str]:
    return [part.strip() for part in value.split(" | ") if part.strip()]


def _processed_candidate_status(path: Path) -> dict[tuple[str, str, str], str]:
    if not path.exists():
        return {}
    rows = read_csv(path)
    statuses: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for number, row in enumerate(rows, start=2):
        status = row.get("evidence_status", "").strip()
        if status not in CORPUS_STATUSES:
            raise ValueError(f"{path.name}:{number}: invalid evidence_status")
        role = row.get("role", "").strip()
        if role not in QUEUE_ROLES:
            raise ValueError(f"{path.name}:{number}: invalid role")
        group = "endorsed" if role in {"endorsed", "unopposed"} else "opponent"
        queue_id = row.get("queue_id", "").strip()
        statuses[(queue_id, _identity(row.get("candidate_name", "")), group)].add(status)
    return {
        key: ("verified" if "verified" in values else "source_unavailable")
        for key, values in statuses.items()
    }


def _load_document_metadata_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows = read_csv(path)
    required = {
        "document_id",
        "candidate_name",
        "race_id",
        "role",
        "election_date",
        "source_type",
        "source_url",
        "coverage_status",
    }
    missing = required - set(rows[0]) if rows else set()
    if missing:
        raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
    output = []
    for number, row in enumerate(rows, start=2):
        role = row.get("role", "").strip()
        if role and role not in QUEUE_ROLES:
            raise ValueError(f"{path.name}:{number}: invalid role")
        candidate_name = row.get("candidate_name", "").strip()
        source_type = row.get("source_type", "").strip()
        source_url = row.get("source_url", "").strip()
        election_date = row.get("election_date", "").strip()
        if election_date:
            year = str(_year_from_value(election_date, path.name, f"row {number} election_date"))
        else:
            year = ""
        output.append(
            {
                "document_id": row.get("document_id", "").strip(),
                "queue_id": row.get("queue_id", "").strip(),
                "candidate_name": candidate_name,
                "candidate_slug": row.get("candidate_slug", "").strip() or candidate_slug(candidate_name),
                "race_id": row.get("race_id", "").strip(),
                "role": role,
                "group": "endorsed" if role in {"endorsed", "unopposed"} else "opponent",
                "election_date": election_date,
                "election_year": year,
                "publication_date": row.get("publication_date", "").strip(),
                "source_type": source_type,
                "source_type_class": classify_source_type(source_type, source_url),
                "source_url": source_url,
                "coverage_status": row.get("coverage_status", "").strip(),
                "fetch_status": row.get("fetch_status", "").strip(),
                "extraction_status": row.get("extraction_status", "").strip(),
                "analysis_scope": row.get("analysis_scope", "").strip() or "analysis",
            }
        )
    return output


def _load_analysis_segment_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows = read_csv(path)
    required = {
        "analysis_segment_id",
        "document_id",
        "candidate_name",
        "race_id",
        "role",
        "source_type",
        "token_count",
        "text",
    }
    missing = required - set(rows[0]) if rows else set()
    if missing:
        raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
    output = []
    for number, row in enumerate(rows, start=2):
        role = row.get("role", "").strip()
        if role not in QUEUE_ROLES:
            raise ValueError(f"{path.name}:{number}: invalid role")
        token_count = row.get("token_count", "").strip()
        if token_count and not token_count.isdigit():
            raise ValueError(f"{path.name}:{number}: invalid token_count")
        source_type = row.get("source_type", "").strip()
        candidate_name = row.get("candidate_name", "").strip()
        output.append(
            {
                "analysis_segment_id": row.get("analysis_segment_id", "").strip(),
                "document_id": row.get("document_id", "").strip(),
                "candidate_name": candidate_name,
                "candidate_slug": row.get("candidate_slug", "").strip() or candidate_slug(candidate_name),
                "race_id": row.get("race_id", "").strip(),
                "role": role,
                "group": "endorsed" if role in {"endorsed", "unopposed"} else "opponent",
                "source_type": source_type,
                "source_type_class": classify_source_type(source_type),
                "token_count": token_count or "0",
                "text": row.get("text", "").strip(),
                "boilerplate_flag": row.get("boilerplate_flag", "false").strip() or "false",
                "exact_duplicate_flag": row.get("exact_duplicate_flag", "false").strip() or "false",
                "near_duplicate_flag": row.get("near_duplicate_flag", "false").strip() or "false",
            }
        )
    return output


def _load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    output: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            output.append(json.loads(line))
    return output


def _document_support_snapshot(
    metadata_rows: list[dict[str, str]],
    analysis_segment_rows: list[dict[str, str]],
) -> dict[str, Any]:
    metadata_by_document = {row["document_id"]: row for row in metadata_rows if row.get("document_id")}
    candidate_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    document_index: dict[str, dict[str, Any]] = {}
    eligible_analysis_segments = []
    substantive_segments = []

    for segment in analysis_segment_rows:
        metadata = metadata_by_document.get(segment["document_id"], {})
        if metadata and not _metadata_supports_analysis(metadata):
            continue
        eligible_analysis_segments.append(segment)
        if not _is_substantive_segment(segment):
            continue
        candidate_name = metadata.get("candidate_name", "") or segment["candidate_name"]
        role = metadata.get("role", "") or segment["role"]
        group = "endorsed" if role in {"endorsed", "unopposed"} else "opponent"
        election_date = metadata.get("election_date", "")
        election_year = election_date[:4] if election_date else ""
        source_type = metadata.get("source_type", "") or segment["source_type"]
        source_url = metadata.get("source_url", "")
        source_type_class = metadata.get("source_type_class", "") or segment["source_type_class"]
        logical_document_key = _candidate_source_key(
            race_id=metadata.get("race_id", "") or segment["race_id"],
            candidate_name=candidate_name,
            role=role,
            source_url=source_url,
            fallback=segment["document_id"],
        )
        candidate_key = (
            metadata.get("race_id", "") or segment["race_id"],
            _identity(candidate_name),
            group,
        )
        candidate_support = candidate_index.setdefault(
            candidate_key,
            {
                "race_id": metadata.get("race_id", "") or segment["race_id"],
                "candidate_name": candidate_name,
                "group": group,
                "role": role,
                "election_year": election_year,
                "document_ids": set(),
                "segment_ids": set(),
                "source_classes": set(),
            },
        )
        candidate_support["document_ids"].add(logical_document_key)
        candidate_support["segment_ids"].add(segment["analysis_segment_id"])
        if source_type_class:
            candidate_support["source_classes"].add(source_type_class)

        document_support = document_index.setdefault(
            logical_document_key,
            {
                "document_id": segment["document_id"],
                "race_id": candidate_support["race_id"],
                "candidate_name": candidate_name,
                "group": group,
                "role": role,
                "election_year": election_year,
                "source_type": source_type,
                "source_type_class": source_type_class,
                "source_url": source_url,
                "raw_document_ids": set(),
                "segment_ids": set(),
            },
        )
        document_support["raw_document_ids"].add(segment["document_id"])
        document_support["segment_ids"].add(segment["analysis_segment_id"])
        substantive_segments.append(
            {
                "analysis_segment_id": segment["analysis_segment_id"],
                "document_id": segment["document_id"],
                "race_id": candidate_support["race_id"],
                "candidate_name": candidate_name,
                "group": group,
                "role": role,
                "election_year": election_year,
                "source_type": source_type,
                "source_type_class": source_type_class,
            }
        )

    return {
        "metadata_by_document": metadata_by_document,
        "candidate_index": candidate_index,
        "document_index": document_index,
        "eligible_analysis_segments": eligible_analysis_segments,
        "substantive_segments": substantive_segments,
    }


def _is_substantive_segment(row: dict[str, str]) -> bool:
    if not row.get("text", "").strip():
        return False
    if _as_bool(row.get("boilerplate_flag", "false")):
        return False
    return int(row.get("token_count", "0") or "0") >= SUBSTANTIVE_MIN_TOKENS


def _metadata_supports_analysis(row: dict[str, str]) -> bool:
    if row.get("analysis_scope", "").strip() == "context_only":
        return False
    return row.get("coverage_status", "").strip() != "shared_document_unscoped" and (
        row.get("extraction_status", "").strip() != "shared_document_unscoped"
    )


def _metadata_supports_clean_pairing(row: dict[str, str]) -> bool:
    return _metadata_supports_analysis(row) and row.get("extraction_status", "").strip() == "extracted"


def _paired_race_rows_from_clean_documents(
    metadata_rows: list[dict[str, str]],
    analysis_segment_rows: list[dict[str, str]],
    substantive_candidate_index: dict[tuple[str, str, str], dict[str, Any]],
) -> list[dict[str, str]]:
    segment_ids_by_document: dict[str, set[str]] = defaultdict(set)
    for row in analysis_segment_rows:
        document_id = row.get("document_id", "").strip()
        if document_id:
            segment_ids_by_document[document_id].add(row.get("analysis_segment_id", "").strip())

    candidate_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in metadata_rows:
        if not _metadata_supports_clean_pairing(row):
            continue
        race_id = row.get("race_id", "").strip()
        candidate_name = row.get("candidate_name", "").strip()
        group = row.get("group", "").strip() or (
            "endorsed" if row.get("role", "").strip() in {"endorsed", "unopposed"} else "opponent"
        )
        document_id = row.get("document_id", "").strip()
        candidate_key = (race_id, _identity(candidate_name), group)
        support = candidate_index.setdefault(
            candidate_key,
            {
                "race_id": race_id,
                "candidate_name": candidate_name,
                "group": group,
                "election_year": row.get("election_year", "").strip(),
                "document_ids": set(),
                "segment_ids": set(),
                "source_classes": set(),
            },
        )
        if document_id:
            support["document_ids"].add(document_id)
            support["segment_ids"].update(
                segment_id
                for segment_id in segment_ids_by_document.get(document_id, set())
                if segment_id
            )
        source_type_class = row.get("source_type_class", "").strip()
        if source_type_class:
            support["source_classes"].add(source_type_class)

    by_race: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for support in candidate_index.values():
        by_race[support["race_id"]].append(support)

    output = []
    for race_id in sorted(by_race):
        rows = by_race[race_id]
        years = {row["election_year"] for row in rows if row["election_year"]}
        if len(years) != 1:
            raise ValueError(f"{race_id}: inconsistent election years in clean document metadata")
        election_year = years.pop() if years else ""
        endorsed = [row for row in rows if row["group"] == "endorsed"]
        opponents = [row for row in rows if row["group"] == "opponent"]
        clean_document_ids = {
            document_id
            for row in rows
            for document_id in row["document_ids"]
        }
        clean_segment_ids = {
            segment_id
            for row in rows
            for segment_id in row["segment_ids"]
        }
        clean_source_classes = sorted(
            {
                source_class
                for row in rows
                for source_class in row["source_classes"]
            }
        )
        substantive_endorsed = sum(
            (race_id, _identity(row["candidate_name"]), "endorsed") in substantive_candidate_index
            for row in endorsed
        )
        substantive_opponents = sum(
            (race_id, _identity(row["candidate_name"]), "opponent") in substantive_candidate_index
            for row in opponents
        )
        substantive_document_ids = {
            document_id
            for key, support in substantive_candidate_index.items()
            if key[0] == race_id
            for document_id in support["document_ids"]
        }
        substantive_segment_count = sum(
            len(support["segment_ids"])
            for key, support in substantive_candidate_index.items()
            if key[0] == race_id
        )
        substantive_source_classes = sorted(
            {
                source_class
                for key, support in substantive_candidate_index.items()
                if key[0] == race_id
                for source_class in support["source_classes"]
            }
        )
        blockers = []
        if not endorsed:
            blockers.append("endorsed_clean_document_missing")
        if not opponents:
            blockers.append("opponent_clean_document_missing")
        output.append(
            {
                "race_id": race_id,
                "election_year": election_year,
                "paired_race_eligible": "true" if endorsed and opponents else "false",
                "endorsed_clean_candidates": str(len(endorsed)),
                "opponent_clean_candidates": str(len(opponents)),
                "clean_document_count": str(len(clean_document_ids)),
                "clean_analysis_segment_count": str(len(clean_segment_ids)),
                "clean_source_classes": " | ".join(clean_source_classes),
                "endorsed_substantive_candidates": str(substantive_endorsed),
                "opponent_substantive_candidates": str(substantive_opponents),
                "substantive_document_count": str(len(substantive_document_ids)),
                "substantive_segment_count": str(substantive_segment_count),
                "substantive_source_classes": " | ".join(substantive_source_classes),
                "paired_race_gap_reason": " | ".join(blockers),
            }
        )
    return output


def _corpus_summary_rows(corpus_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    counts = Counter()
    candidates: dict[tuple[str, str, str, str, str], set[tuple[str, str, str]]] = defaultdict(set)
    races: dict[tuple[str, str, str, str, str], set[str]] = defaultdict(set)
    for row in corpus_rows:
        key = (
            row["group"],
            row["election_year"],
            row["source_type_class"],
            row["source_type"],
            row["evidence_status"],
        )
        counts[key] += 1
        candidates[key].add((row["candidate_name"], row["election_year"], row["group"]))
        races[key].add(row["race_id"])
    output = []
    for key in sorted(counts, key=lambda item: (item[1], item[0], item[4], item[2], item[3])):
        group, year, source_type_class, source_type, status = key
        output.append(
            {
                "corpus_kind": "legacy_statement_rows",
                "group": group,
                "election_year": year,
                "source_type_class": source_type_class,
                "source_type": source_type,
                "evidence_status": status,
                "row_count": str(counts[key]),
                "unique_candidates": str(len(candidates[key])),
                "unique_races": str(len(races[key])),
            }
        )
    return output


def _queue_summary_rows(
    queue_candidates: list[dict[str, str]],
    queue_source: str,
) -> list[dict[str, str]]:
    counts = Counter()
    races: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in queue_candidates:
        key = (row["group"], row["election_year"], row["current_status"])
        counts[key] += 1
        races[key].add(row["race_id"])
    output = []
    for key in sorted(counts, key=lambda item: (item[1], item[0], item[2])):
        group, year, status = key
        output.append(
            {
                "queue_source": queue_source,
                "group": group,
                "election_year": year,
                "current_status": status,
                "candidate_count": str(counts[key]),
                "race_count": str(len(races[key])),
            }
        )
    return output


def _race_summary_rows(
    queue_candidates: list[dict[str, str]],
    candidate_index: dict[tuple[str, str, str], dict[str, Any]],
) -> list[dict[str, str]]:
    by_race: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in queue_candidates:
        by_race[row["race_id"]].append(row)
    output = []
    for race_id in sorted(by_race):
        rows = by_race[race_id]
        years = {row["election_year"] for row in rows}
        if len(years) != 1:
            raise ValueError(f"{race_id}: inconsistent election years in queue")
        year = years.pop()
        endorsed = [row for row in rows if row["group"] == "endorsed"]
        opponents = [row for row in rows if row["group"] == "opponent"]
        endorsed_verified = sum(row["current_status"] == "verified" for row in endorsed)
        opponent_verified = sum(row["current_status"] == "verified" for row in opponents)
        endorsed_retryable = sum(row["current_status"] in RETRYABLE_STATUSES for row in endorsed)
        opponent_retryable = sum(row["current_status"] in RETRYABLE_STATUSES for row in opponents)

        endorsed_support = [_candidate_support(candidate_index, row) for row in endorsed]
        opponent_support = [_candidate_support(candidate_index, row) for row in opponents]
        endorsed_substantive = sum(value is not None for value in endorsed_support)
        opponent_substantive = sum(value is not None for value in opponent_support)
        document_ids = {
            document_id
            for support in endorsed_support + opponent_support
            if support is not None
            for document_id in support["document_ids"]
        }
        substantive_segment_count = sum(
            len(support["segment_ids"])
            for support in endorsed_support + opponent_support
            if support is not None
        )
        source_classes = sorted(
            {
                source_class
                for support in endorsed_support + opponent_support
                if support is not None
                for source_class in support["source_classes"]
            }
        )
        eligible = endorsed_substantive > 0 and opponent_substantive > 0
        blockers = []
        if not endorsed:
            blockers.append("missing_endorsed_candidate")
        if not opponents:
            blockers.append("missing_opponent_candidate")
        if endorsed_substantive == 0:
            blockers.append("endorsed_substantive_text_missing")
            if endorsed_retryable:
                blockers.append("endorsed_search_retryable")
        if opponent_substantive == 0:
            blockers.append("opponent_substantive_text_missing")
            if opponent_retryable:
                blockers.append("opponent_search_retryable")
        if all(row["current_status"] == "not_applicable" for row in rows):
            blockers.append("not_primary")
        pair_completion_gap_count = int(endorsed_substantive == 0) + int(opponent_substantive == 0)
        paired_retryable = (not eligible) and (
            (endorsed_substantive == 0 and endorsed_retryable > 0)
            or (opponent_substantive == 0 and opponent_retryable > 0)
        )
        output.append(
            {
                "queue_source": rows[0]["queue_source"],
                "race_id": race_id,
                "election_year": year,
                "endorsed_candidates": str(len(endorsed)),
                "opponent_candidates": str(len(opponents)),
                "verified_candidates": str(
                    sum(row["current_status"] == "verified" for row in rows)
                ),
                "source_unavailable_candidates": str(
                    sum(row["current_status"] == "source_unavailable" for row in rows)
                ),
                "retryable_gap_candidates": str(
                    sum(row["current_status"] in RETRYABLE_STATUSES for row in rows)
                ),
                "endorsed_verified_candidates": str(endorsed_verified),
                "opponent_verified_candidates": str(opponent_verified),
                "endorsed_retryable_candidates": str(endorsed_retryable),
                "opponent_retryable_candidates": str(opponent_retryable),
                "endorsed_substantive_candidates": str(endorsed_substantive),
                "opponent_substantive_candidates": str(opponent_substantive),
                "substantive_document_count": str(len(document_ids)),
                "substantive_segment_count": str(substantive_segment_count),
                "substantive_source_classes": " | ".join(source_classes),
                "paired_race_eligible": "true" if eligible else "false",
                "paired_race_retryable": "true" if paired_retryable else "false",
                "pair_completion_gap_count": str(pair_completion_gap_count),
                "paired_race_gap_reason": " | ".join(blockers),
            }
        )
    return output


def _candidate_support(
    candidate_index: dict[tuple[str, str, str], dict[str, Any]],
    row: dict[str, str],
) -> dict[str, Any] | None:
    return candidate_index.get((row["race_id"], _identity(row["candidate_name"]), row["group"]))


def _coverage_gap_rows(
    queue_candidates: list[dict[str, str]],
    queue_source: str,
    expected_years: list[int],
) -> list[dict[str, str]]:
    present_years = {int(row["election_year"]) for row in queue_candidates}
    output = []
    for year in expected_years:
        if year in present_years:
            continue
        output.append(
            {
                "gap_type": "coverage_gap",
                "queue_source": queue_source,
                "election_year": str(year),
                "race_id": "",
                "candidate_name": "",
                "group": "",
                "role": "",
                "current_status": "not_searched",
                "paired_race_eligible": "false",
                "would_unlock_paired_race": "false",
                "pair_completion_gap_count": "",
                "reference_url": "",
                "endorsement_source_url": "",
                "gap_reason": "queue_missing_year_coverage",
                "notes": f"Current {queue_source} queue has no tracked candidacy rows for this year.",
            }
        )
    return output


def _retryable_gap_rows(
    queue_candidates: list[dict[str, str]],
    race_index: dict[str, dict[str, str]],
    coverage_gap_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    output = list(coverage_gap_rows)
    for row in queue_candidates:
        if row["current_status"] not in RETRYABLE_STATUSES:
            continue
        race = race_index[row["race_id"]]
        if row["group"] == "endorsed":
            own_substantive = int(race["endorsed_substantive_candidates"])
            other_substantive = int(race["opponent_substantive_candidates"])
        else:
            own_substantive = int(race["opponent_substantive_candidates"])
            other_substantive = int(race["endorsed_substantive_candidates"])
        would_unlock = own_substantive == 0 and other_substantive > 0
        output.append(
            {
                "gap_type": "candidate_gap",
                "queue_source": row["queue_source"],
                "election_year": row["election_year"],
                "race_id": row["race_id"],
                "candidate_name": row["candidate_name"],
                "group": row["group"],
                "role": row["role"],
                "current_status": row["current_status"],
                "paired_race_eligible": race["paired_race_eligible"],
                "would_unlock_paired_race": "true" if would_unlock else "false",
                "pair_completion_gap_count": race["pair_completion_gap_count"],
                "reference_url": row["reference_url"],
                "endorsement_source_url": row["endorsement_source_url"],
                "gap_reason": race["paired_race_gap_reason"] or "retryable_candidate_gap",
                "notes": row["notes"],
            }
        )
    return sorted(
        output,
        key=lambda row: (
            row["election_year"],
            row["race_id"],
            row["candidate_name"],
            row["gap_type"],
        ),
    )


def _priority_rows(
    retryable_gap_rows: list[dict[str, str]],
    study_start_year: int,
    final_year: int,
) -> list[dict[str, str]]:
    prioritized = []
    for row in retryable_gap_rows:
        score = 0
        reasons = []
        year = int(row["election_year"])
        if row["gap_type"] == "coverage_gap":
            score += 140
            reasons.append("missing_queue_year")
        status_weight = {
            "found_unverified": 40,
            "not_searched": 30,
            "searched_not_found": 20,
        }
        score += status_weight.get(row["current_status"], 0)
        if year == study_start_year:
            score += 100
            reasons.append("study_start_year_gap")
        else:
            score += max(final_year - year, 0)
        if row["would_unlock_paired_race"] == "true":
            score += 80
            reasons.append("would_unlock_paired_race")
        elif row["gap_type"] == "candidate_gap" and row["pair_completion_gap_count"] == "2":
            score += 35
            reasons.append("paired_race_two_step_gap")
        if row["group"] == "endorsed":
            score += 15
            reasons.append("endorsed_candidate")
        if row["reference_url"] or row["endorsement_source_url"]:
            score += 10
            reasons.append("has_seed_url")
        prioritized.append(
            {
                **row,
                "priority_score": str(score),
                "priority_reasons": " | ".join(reasons),
            }
        )
    prioritized.sort(
        key=lambda row: (
            -int(row["priority_score"]),
            row["election_year"],
            row["gap_type"],
            row["candidate_name"],
            row["race_id"],
        )
    )
    for number, row in enumerate(prioritized, start=1):
        row["priority_rank"] = str(number)
    return prioritized


def _build_candidate_document_queue_rows(
    *,
    source_inventory_rows: list[dict[str, str]],
    discovery_queue_rows: list[dict[str, str]],
    queue_candidates: list[dict[str, str]],
    metadata_rows: list[dict[str, str]],
    analysis_segment_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    metadata_by_document = {row["document_id"]: row for row in metadata_rows if row.get("document_id")}
    analysis_segment_counts = Counter(row["document_id"] for row in analysis_segment_rows)
    substantive_segment_counts = Counter(
        row["document_id"] for row in analysis_segment_rows if _is_substantive_segment(row)
    )
    metadata_by_key: dict[tuple[str, str, str, str], dict[str, str]] = {}
    analysis_counts_by_key: dict[tuple[str, str, str, str], int] = defaultdict(int)
    substantive_counts_by_key: dict[tuple[str, str, str, str], int] = defaultdict(int)
    for metadata in metadata_rows:
        document_id = metadata.get("document_id", "").strip()
        key = _candidate_source_key(
            race_id=metadata.get("race_id", "").strip(),
            candidate_name=metadata.get("candidate_name", "").strip(),
            role=metadata.get("role", "").strip(),
            source_url=metadata.get("source_url", "").strip(),
            fallback=document_id,
        )
        analysis_counts_by_key[key] = max(
            analysis_counts_by_key[key],
            analysis_segment_counts.get(document_id, 0),
        )
        substantive_counts_by_key[key] = max(
            substantive_counts_by_key[key],
            substantive_segment_counts.get(document_id, 0),
        )
        existing = metadata_by_key.get(key)
        if existing is None or _metadata_completion_rank(metadata) > _metadata_completion_rank(
            existing
        ):
            metadata_by_key[key] = metadata
    rows_by_document: dict[tuple[str, str, str, str], dict[str, str]] = {}

    def upsert(row: dict[str, str]) -> None:
        row_key = _candidate_source_key(
            race_id=row.get("race_id", "").strip(),
            candidate_name=row.get("candidate_name", "").strip(),
            role=row.get("role", "").strip(),
            source_url=row.get("source_url", "").strip(),
            fallback=row.get("document_id", "").strip(),
        )
        existing = rows_by_document.get(row_key)
        if existing is None:
            rows_by_document[row_key] = row
            return
        existing["seed_kinds"] = merge_notes(existing["seed_kinds"], row["seed_kinds"])
        existing["source_record_ids"] = merge_notes(
            existing["source_record_ids"], row["source_record_ids"]
        )
        existing["legacy_locators"] = merge_notes(
            existing["legacy_locators"], row["legacy_locators"]
        )
        existing["notes"] = merge_notes(existing["notes"], row["notes"])
        existing["seed_priority"] = str(
            min(int(existing["seed_priority"] or "999"), int(row["seed_priority"] or "999"))
        )
        existing["known_source_count"] = str(
            max(int(existing["known_source_count"] or "0"), int(row["known_source_count"] or "0"))
        )
        existing["legacy_statement_count"] = str(
            max(
                int(existing["legacy_statement_count"] or "0"),
                int(row["legacy_statement_count"] or "0"),
            )
        )
        for field in (
            "queue_id",
            "archive_url",
            "live_url",
            "campaign_domain",
            "official_election_source",
            "publication_date",
            "effective_date",
            "source_tier",
            "analysis_scope",
            "legacy_locators",
        ):
            if not existing[field] and row[field]:
                existing[field] = row[field]
        if (
            existing.get("analysis_scope", "").strip() == "analysis"
            and row.get("analysis_scope", "").strip() == "context_only"
        ):
            existing["analysis_scope"] = "context_only"

    def collection_fields(row: dict[str, str]) -> tuple[str, str, str, str, str]:
        document_id = row.get("document_id", "").strip()
        row_key = _candidate_source_key(
            race_id=row.get("race_id", "").strip(),
            candidate_name=row.get("candidate_name", "").strip(),
            role=row.get("role", "").strip(),
            source_url=row.get("source_url", "").strip(),
            fallback=document_id,
        )
        metadata = metadata_by_key.get(row_key) or metadata_by_document.get(document_id)
        analysis_count = analysis_counts_by_key.get(row_key, analysis_segment_counts.get(document_id, 0))
        substantive_count = substantive_counts_by_key.get(
            row_key,
            substantive_segment_counts.get(document_id, 0),
        )
        if not metadata:
            return (
                document_id,
                "not_collected",
                "",
                str(analysis_count),
                str(substantive_count),
            )
        metadata_status = "/".join(
            value
            for value in (
                metadata.get("fetch_status", ""),
                metadata.get("extraction_status", ""),
            )
            if value
        )
        if not _metadata_supports_analysis(metadata):
            analysis_count = 0
            substantive_count = 0
        return (
            metadata.get("document_id", "").strip() or row.get("document_id", "").strip(),
            metadata.get("coverage_status", "") or "collected",
            metadata_status,
            str(analysis_count),
            str(substantive_count),
        )

    for row in source_inventory_rows:
        source_url = row.get("live_url", "").strip() or row.get("source_url", "").strip()
        if not source_url:
            continue
        document_id = candidate_document_id(
            row["candidate_name"],
            row["race_id"],
            source_url,
            row.get("source_type_class", "") or row.get("source_type", "other"),
        )
        base_row = {
            "document_id": document_id,
            "queue_id": row.get("queue_id", "").strip(),
            "race_id": row.get("race_id", "").strip(),
            "candidate_slug": row.get("candidate_slug", "").strip(),
            "candidate_name": row.get("candidate_name", "").strip(),
            "role": row.get("role", "").strip(),
            "election_date": row.get("election_date", "").strip(),
            "publication_date": row.get("publication_date", "").strip(),
            "effective_date": row.get("effective_date", "").strip(),
            "source_type": row.get("source_type", "").strip()
            or row.get("source_type_class", "other"),
            "source_type_class": row.get("source_type_class", "").strip() or "other",
            "source_url": row.get("fetch_url", "").strip() or source_url,
            "archive_url": row.get("archive_url", "").strip(),
            "live_url": row.get("live_url", "").strip(),
            "source_tier": row.get("source_tier", "").strip(),
            "analysis_scope": row.get("analysis_scope", "").strip() or "analysis",
            "campaign_domain": row.get("campaign_domain", "").strip(),
            "official_election_source": row.get("official_election_source", "").strip(),
            "seed_kinds": "known_document",
            "seed_priority": str(DOCUMENT_QUEUE_SEED_PRIORITY["known_document"]),
            "source_record_ids": row.get("source_record_id", "").strip(),
            "known_source_count": "1",
            "legacy_statement_count": row.get("statement_count", "0").strip() or "0",
            "legacy_locators": row.get("legacy_locators", "").strip(),
            "notes": "Seeded from legacy quotation-source inventory; collect full document text for audit coverage.",
        }
        (
            base_row["document_id"],
            collection_status,
            metadata_status,
            analysis_count,
            substantive_count,
        ) = collection_fields(
            base_row
        )
        upsert(
            {
                **base_row,
                "collection_status": collection_status,
                "metadata_status": metadata_status,
                "analysis_segment_count": analysis_count,
                "substantive_segment_count": substantive_count,
            }
        )

    for row in discovery_queue_rows:
        seed_url = row.get("seed_url", "").strip()
        if not seed_url:
            continue
        document_id = candidate_document_id(
            row["candidate_name"],
            row["race_id"],
            seed_url,
            row.get("source_type_class", "other") or "other",
        )
        base_row = {
            "document_id": document_id,
            "queue_id": row.get("queue_id", "").strip(),
            "race_id": row.get("race_id", "").strip(),
            "candidate_slug": row.get("candidate_slug", "").strip(),
            "candidate_name": row.get("candidate_name", "").strip(),
            "role": row.get("role", "").strip(),
            "election_date": row.get("election_date", "").strip(),
            "publication_date": row.get("publication_date", "").strip(),
            "effective_date": row.get("effective_date", "").strip(),
            "source_type": row.get("source_type_class", "other").strip() or "other",
            "source_type_class": row.get("source_type_class", "other").strip() or "other",
            "source_url": seed_url,
            "archive_url": row.get("archive_url", "").strip(),
            "live_url": row.get("live_url", "").strip(),
            "source_tier": row.get("source_tier", "").strip(),
            "analysis_scope": row.get("analysis_scope", "").strip() or "analysis",
            "campaign_domain": row.get("campaign_domain", "").strip(),
            "official_election_source": row.get("official_election_source", "").strip(),
            "seed_kinds": row.get("seed_kind", "").strip(),
            "seed_priority": str(
                DOCUMENT_QUEUE_SEED_PRIORITY.get(row.get("seed_kind", "").strip(), 9)
            ),
            "source_record_ids": row.get("source_record_id", "").strip(),
            "known_source_count": row.get("known_source_count", "0").strip() or "0",
            "legacy_statement_count": "0",
            "legacy_locators": row.get("legacy_locators", "").strip(),
            "notes": row.get("notes", "").strip(),
        }
        (
            base_row["document_id"],
            collection_status,
            metadata_status,
            analysis_count,
            substantive_count,
        ) = collection_fields(
            base_row
        )
        upsert(
            {
                **base_row,
                "collection_status": collection_status,
                "metadata_status": metadata_status,
                "analysis_segment_count": analysis_count,
                "substantive_segment_count": substantive_count,
            }
        )

    for row in queue_candidates:
        for url_field, seed_kind, note in (
            (
                "reference_url",
                "queue_reference",
                "Seeded from current candidacy queue reference URL.",
            ),
            (
                "endorsement_source_url",
                "endorsement_source",
                "Seeded from endorsement source context for candidate-document discovery.",
            ),
        ):
            raw_urls = row.get(url_field, "").strip()
            if not raw_urls:
                continue
            for raw_url in raw_urls.split(" | "):
                source_url = raw_url.strip()
                if not source_url:
                    continue
                try:
                    normalized_url = normalize_source_url(source_url)
                except ValueError:
                    normalized_url = source_url
                source_type_class = classify_source_type("", normalized_url)
                document_id = candidate_document_id(
                    row["candidate_name"],
                    row["race_id"],
                    normalized_url,
                    source_type_class,
                )
                base_row = {
                    "document_id": document_id,
                    "queue_id": row.get("queue_id", "").strip(),
                    "race_id": row["race_id"],
                    "candidate_slug": row.get("candidate_slug", "").strip()
                    or candidate_slug(row["candidate_name"]),
                    "candidate_name": row["candidate_name"],
                    "role": row["role"],
                    "election_date": row.get("election_date", "").strip(),
                    "publication_date": "",
                    "effective_date": "",
                    "source_type": source_type_class,
                    "source_type_class": source_type_class,
                    "source_url": normalized_url,
                    "archive_url": "",
                    "live_url": "",
                    "source_tier": "",
                    "analysis_scope": _default_analysis_scope_for_url(normalized_url),
                    "campaign_domain": "",
                    "official_election_source": "",
                    "seed_kinds": seed_kind,
                    "seed_priority": str(DOCUMENT_QUEUE_SEED_PRIORITY[seed_kind]),
                    "source_record_ids": "",
                    "known_source_count": "0",
                    "legacy_statement_count": "0",
                    "legacy_locators": "",
                    "notes": merge_notes(note, row.get("notes", "").strip()),
                }
                (
                    base_row["document_id"],
                    collection_status,
                    metadata_status,
                    analysis_count,
                    substantive_count,
                ) = collection_fields(
                    base_row
                )
                upsert(
                    {
                        **base_row,
                        "collection_status": collection_status,
                        "metadata_status": metadata_status,
                        "analysis_segment_count": analysis_count,
                        "substantive_segment_count": substantive_count,
                    }
                )

    return sorted(
        rows_by_document.values(),
        key=lambda row: (
            row["election_date"],
            row["candidate_name"].casefold(),
            row["role"],
            int(row["seed_priority"] or "999"),
            row["source_url"],
        ),
    )


def _group_year_support_rows(
    queue_candidates: list[dict[str, str]],
    candidate_index: dict[tuple[str, str, str], dict[str, Any]],
    expected_years: list[int],
) -> list[dict[str, str]]:
    queue_candidates_by_group_year: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    queue_races_by_group_year: dict[tuple[str, str], set[str]] = defaultdict(set)
    substantive_candidates_by_group_year: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    substantive_races_by_group_year: dict[tuple[str, str], set[str]] = defaultdict(set)
    substantive_documents_by_group_year: dict[tuple[str, str], set[str]] = defaultdict(set)
    substantive_segments_by_group_year: Counter[tuple[str, str]] = Counter()
    source_classes_by_group_year: dict[tuple[str, str], set[str]] = defaultdict(set)

    for row in queue_candidates:
        key = (row["group"], row["election_year"])
        queue_candidates_by_group_year[key].add((row["race_id"], row["candidate_slug"]))
        queue_races_by_group_year[key].add(row["race_id"])

    for support in candidate_index.values():
        key = (support["group"], support["election_year"])
        substantive_candidates_by_group_year[key].add(
            (support["race_id"], _identity(support["candidate_name"]))
        )
        substantive_races_by_group_year[key].add(support["race_id"])
        substantive_documents_by_group_year[key].update(support["document_ids"])
        substantive_segments_by_group_year[key] += len(support["segment_ids"])
        source_classes_by_group_year[key].update(support["source_classes"])

    output = []
    for year in expected_years:
        year_text = str(year)
        for group in ("endorsed", "opponent"):
            key = (group, year_text)
            queue_count = len(queue_candidates_by_group_year[key])
            substantive_count = len(substantive_candidates_by_group_year[key])
            output.append(
                {
                    "group": group,
                    "election_year": year_text,
                    "queue_candidate_count": str(queue_count),
                    "queue_race_count": str(len(queue_races_by_group_year[key])),
                    "substantive_candidate_count": str(substantive_count),
                    "substantive_race_count": str(len(substantive_races_by_group_year[key])),
                    "substantive_document_count": str(len(substantive_documents_by_group_year[key])),
                    "substantive_segment_count": str(substantive_segments_by_group_year[key]),
                    "source_class_count": str(len(source_classes_by_group_year[key])),
                    "coverage_ratio": (
                        f"{substantive_count / queue_count:.3f}" if queue_count else ""
                    ),
                    "missing_support": "true"
                    if queue_count > 0 and substantive_count == 0
                    else "false",
                }
            )
    return output


def _source_class_support_rows(
    source_inventory_rows: list[dict[str, str]],
    candidate_index: dict[tuple[str, str, str], dict[str, Any]],
) -> list[dict[str, str]]:
    inventory_candidates: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    inventory_races: dict[tuple[str, str], set[str]] = defaultdict(set)
    inventory_sources: Counter[tuple[str, str]] = Counter()
    substantive_candidates: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    substantive_races: dict[tuple[str, str], set[str]] = defaultdict(set)
    substantive_documents: dict[tuple[str, str], set[str]] = defaultdict(set)
    substantive_segments: Counter[tuple[str, str]] = Counter()

    for row in source_inventory_rows:
        key = (row["source_type_class"], "endorsed" if row["role"] in {"endorsed", "unopposed"} else "opponent")
        inventory_candidates[key].add((row["race_id"], row["candidate_slug"]))
        inventory_races[key].add(row["race_id"])
        inventory_sources[key] += 1

    for support in candidate_index.values():
        for source_class in support["source_classes"]:
            key = (source_class, support["group"])
            substantive_candidates[key].add((support["race_id"], _identity(support["candidate_name"])))
            substantive_races[key].add(support["race_id"])
            substantive_documents[key].update(support["document_ids"])
            substantive_segments[key] += len(support["segment_ids"])

    source_classes = sorted(
        {
            key[0] for key in inventory_candidates
        }
        | {key[0] for key in substantive_candidates}
    )
    output = []
    for source_class in source_classes:
        for group in ("endorsed", "opponent"):
            key = (source_class, group)
            inventory_count = len(inventory_candidates[key])
            substantive_count = len(substantive_candidates[key])
            output.append(
                {
                    "source_type_class": source_class,
                    "group": group,
                    "inventory_candidate_count": str(inventory_count),
                    "inventory_race_count": str(len(inventory_races[key])),
                    "inventory_source_count": str(inventory_sources[key]),
                    "substantive_candidate_count": str(substantive_count),
                    "substantive_race_count": str(len(substantive_races[key])),
                    "substantive_document_count": str(len(substantive_documents[key])),
                    "substantive_segment_count": str(substantive_segments[key]),
                    "coverage_ratio": (
                        f"{substantive_count / inventory_count:.3f}" if inventory_count else ""
                    ),
                    "missing_support": "true"
                    if inventory_count > 0 and substantive_count == 0
                    else "false",
                }
            )
    return output


def _imbalance_diagnostic_rows(
    candidate_index: dict[tuple[str, str, str], dict[str, Any]],
    group_year_support_rows: list[dict[str, str]],
    source_class_support_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows = []

    overall = {
        "endorsed_candidate_count": 0,
        "opponent_candidate_count": 0,
        "endorsed_document_count": 0,
        "opponent_document_count": 0,
        "endorsed_segment_count": 0,
        "opponent_segment_count": 0,
    }
    for support in candidate_index.values():
        prefix = support["group"]
        overall[f"{prefix}_candidate_count"] += 1
        overall[f"{prefix}_document_count"] += len(support["document_ids"])
        overall[f"{prefix}_segment_count"] += len(support["segment_ids"])
    overall_expected = {
        "endorsed": sum(row["group"] == "endorsed" for row in group_year_support_rows),
        "opponent": sum(row["group"] == "opponent" for row in group_year_support_rows),
    }
    rows.append(_imbalance_row("overall", "all", overall, overall_expected))

    by_year: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "endorsed_candidate_count": 0,
            "opponent_candidate_count": 0,
            "endorsed_document_count": 0,
            "opponent_document_count": 0,
            "endorsed_segment_count": 0,
            "opponent_segment_count": 0,
        }
    )
    year_expected: dict[str, dict[str, int]] = defaultdict(
        lambda: {"endorsed": 0, "opponent": 0}
    )
    for row in group_year_support_rows:
        prefix = row["group"]
        bucket = row["election_year"]
        by_year[bucket][f"{prefix}_candidate_count"] = int(row["substantive_candidate_count"])
        by_year[bucket][f"{prefix}_document_count"] = int(row["substantive_document_count"])
        by_year[bucket][f"{prefix}_segment_count"] = int(row["substantive_segment_count"])
        year_expected[bucket][prefix] = int(row["queue_candidate_count"])
    for bucket in sorted(by_year):
        rows.append(_imbalance_row("election_year", bucket, by_year[bucket], year_expected[bucket]))

    by_source_class: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "endorsed_candidate_count": 0,
            "opponent_candidate_count": 0,
            "endorsed_document_count": 0,
            "opponent_document_count": 0,
            "endorsed_segment_count": 0,
            "opponent_segment_count": 0,
        }
    )
    source_class_expected: dict[str, dict[str, int]] = defaultdict(
        lambda: {"endorsed": 0, "opponent": 0}
    )
    for row in source_class_support_rows:
        prefix = row["group"]
        bucket = row["source_type_class"]
        by_source_class[bucket][f"{prefix}_candidate_count"] = int(
            row["substantive_candidate_count"]
        )
        by_source_class[bucket][f"{prefix}_document_count"] = int(
            row["substantive_document_count"]
        )
        by_source_class[bucket][f"{prefix}_segment_count"] = int(
            row["substantive_segment_count"]
        )
        source_class_expected[bucket][prefix] = int(row["inventory_candidate_count"])
    for bucket in sorted(by_source_class):
        rows.append(
            _imbalance_row(
                "source_type_class",
                bucket,
                by_source_class[bucket],
                source_class_expected[bucket],
            )
        )

    return rows


def _imbalance_row(
    dimension: str,
    bucket: str,
    counts: dict[str, int],
    expected: dict[str, int],
) -> dict[str, str]:
    endorsed = counts["endorsed_candidate_count"]
    opponent = counts["opponent_candidate_count"]
    endorsed_expected = expected.get("endorsed", 0)
    opponent_expected = expected.get("opponent", 0)
    if endorsed == 0 and opponent == 0:
        ratio = ""
        reason = "no_substantive_document_support"
        passed = "false" if endorsed_expected > 0 or opponent_expected > 0 else "true"
    elif endorsed == 0 or opponent == 0:
        ratio = ""
        if endorsed_expected > 0 and opponent_expected > 0:
            reason = "one_sided_support"
            passed = "false"
        else:
            reason = ""
            passed = "true"
    else:
        numeric_ratio = max(endorsed, opponent) / min(endorsed, opponent)
        ratio = f"{numeric_ratio:.3f}"
        if numeric_ratio > 3.0:
            reason = "candidate_ratio_gt_3"
            passed = "false"
        else:
            reason = ""
            passed = "true"
    return {
        "dimension": dimension,
        "bucket": bucket,
        "endorsed_candidate_count": str(endorsed),
        "opponent_candidate_count": str(opponent),
        "endorsed_document_count": str(counts["endorsed_document_count"]),
        "opponent_document_count": str(counts["opponent_document_count"]),
        "endorsed_segment_count": str(counts["endorsed_segment_count"]),
        "opponent_segment_count": str(counts["opponent_segment_count"]),
        "imbalance_ratio": ratio,
        "flag_reason": reason,
        "hard_gate_pass": passed,
    }


def _hard_gate_summary(
    *,
    expected_years: list[int],
    queue_candidates: list[dict[str, str]],
    race_summary_rows: list[dict[str, str]],
    source_inventory_rows: list[dict[str, str]],
    group_year_support_rows: list[dict[str, str]],
    source_class_support_rows: list[dict[str, str]],
    imbalance_rows: list[dict[str, str]],
    paired_race_rows: list[dict[str, str]],
) -> dict[str, Any]:
    expected_year_strings = [str(year) for year in expected_years]
    queue_years = sorted({row["election_year"] for row in queue_candidates})
    retryable_candidate_rows = sum(
        row["current_status"] in RETRYABLE_STATUSES for row in queue_candidates
    )
    eligible_years = sorted(
        {row["election_year"] for row in paired_race_rows if row["paired_race_eligible"] == "true"}
    )
    missing_group_year_support = [
        f"{row['group']}:{row['election_year']}"
        for row in group_year_support_rows
        if row["missing_support"] == "true"
    ]
    groups_with_substantive_text = sorted(
        {
            row["group"]
            for row in group_year_support_rows
            if int(row["substantive_candidate_count"]) > 0
        }
    )
    years_with_substantive_text = sorted(
        {
            row["election_year"]
            for row in group_year_support_rows
            if int(row["substantive_candidate_count"]) > 0
        }
    )
    inventory_source_classes = sorted({row["source_type_class"] for row in source_inventory_rows})
    substantive_source_classes = sorted(
        {
            row["source_type_class"]
            for row in source_class_support_rows
            if int(row["substantive_candidate_count"]) > 0
        }
    )
    missing_source_classes = [
        source_class
        for source_class in inventory_source_classes
        if source_class not in substantive_source_classes
    ]
    imbalance_failures = [
        f"{row['dimension']}:{row['bucket']}:{row['flag_reason']}"
        for row in imbalance_rows
        if row["hard_gate_pass"] == "false"
    ]

    gates = {
        "census_2016_present": {
            "pass": queue_years == expected_year_strings,
            "years_present": queue_years,
            "missing_years": [
                year for year in expected_year_strings if year not in queue_years
            ],
        },
        "no_retryable_candidate_searches": {
            "pass": retryable_candidate_rows == 0,
            "retryable_candidate_rows": retryable_candidate_rows,
        },
        "paired_race_two_sided_substantive_text": {
            "pass": eligible_years == expected_year_strings and bool(eligible_years),
            "eligible_races": sum(
                row["paired_race_eligible"] == "true" for row in paired_race_rows
            ),
            "eligible_years": eligible_years,
            "missing_years": [
                year for year in expected_year_strings if year not in eligible_years
            ],
        },
        "group_year_source_class_support": {
            "pass": (
                groups_with_substantive_text == ["endorsed", "opponent"]
                and years_with_substantive_text == expected_year_strings
                and not missing_group_year_support
                and bool(substantive_source_classes)
                and not missing_source_classes
            ),
            "groups_with_substantive_text": groups_with_substantive_text,
            "years_with_substantive_text": years_with_substantive_text,
            "missing_group_year_support": missing_group_year_support,
            "source_classes_with_substantive_text": substantive_source_classes,
            "missing_source_classes": missing_source_classes,
        },
        "imbalance_diagnostics": {
            "pass": not imbalance_failures,
            "flagged_rows": imbalance_failures,
        },
    }
    failed_gates = [name for name, payload in gates.items() if not payload["pass"]]
    return {
        "passes": not failed_gates,
        "failed_gates": failed_gates,
        "gates": gates,
    }


def _summary(
    *,
    queue_source: str,
    corpus_rows: list[dict[str, str]],
    queue_candidates: list[dict[str, str]],
    race_summary_rows: list[dict[str, str]],
    paired_race_rows: list[dict[str, str]],
    retryable_gap_rows: list[dict[str, str]],
    expected_years: list[int],
    study_start_year: int,
    source_inventory_rows: list[dict[str, str]],
    discovery_queue_rows: list[dict[str, str]],
    document_queue_rows: list[dict[str, str]],
    metadata_rows: list[dict[str, str]],
    full_text_rows: list[dict[str, Any]],
    analysis_segment_rows: list[dict[str, str]],
    document_support: dict[str, Any],
    group_year_support_rows: list[dict[str, str]],
    source_class_support_rows: list[dict[str, str]],
    imbalance_rows: list[dict[str, str]],
    hard_gates: dict[str, Any],
) -> dict[str, object]:
    expected_year_strings = [str(year) for year in expected_years]
    corpus_years = sorted({row["election_year"] for row in corpus_rows})
    corpus_verified_years = sorted(
        {row["election_year"] for row in corpus_rows if row["evidence_status"] == "verified"}
    )
    queue_years = sorted({row["election_year"] for row in queue_candidates})
    eligible_years = sorted(
        {row["election_year"] for row in paired_race_rows if row["paired_race_eligible"] == "true"}
    )
    queue_status_counts = Counter(row["current_status"] for row in queue_candidates)
    queue_group_counts = Counter(row["group"] for row in queue_candidates)
    retryable_status_counts = Counter(
        row["current_status"]
        for row in retryable_gap_rows
        if row["gap_type"] == "candidate_gap"
    )
    raw_extracted_document_count = sum(
        row.get("extraction_status", "").strip()
        in {"extracted", "shared_document_unscoped", "media_no_transcript"}
        for row in metadata_rows
    )
    shared_unscoped_document_count = sum(
        row.get("coverage_status", "").strip() == "shared_document_unscoped"
        or row.get("extraction_status", "").strip() == "shared_document_unscoped"
        for row in metadata_rows
    )
    eligible_text_document_count = sum(
        row.get("extraction_status", "").strip() == "extracted"
        and _metadata_supports_analysis(row)
        for row in metadata_rows
    )
    eligible_analysis_segments = document_support["eligible_analysis_segments"]
    substantive_segments = document_support["substantive_segments"]
    substantive_groups = sorted({row["group"] for row in substantive_segments})
    substantive_years = sorted({row["election_year"] for row in substantive_segments if row["election_year"]})
    substantive_source_classes = sorted(
        {row["source_type_class"] for row in substantive_segments if row["source_type_class"]}
    )
    queue_seeded_candidates = {
        (row["race_id"], row["candidate_slug"], row["role"])
        for row in document_queue_rows
    }
    unseeded_queue_candidates = [
        row
        for row in queue_candidates
        if (row["race_id"], row["candidate_slug"], row["role"]) not in queue_seeded_candidates
    ]
    textual_full_text_rows = [
        row for row in full_text_rows if str(row.get("text", "")).strip()
    ]
    transcriptless_only = bool(full_text_rows) and not textual_full_text_rows and all(
        str(row.get("coverage_status", "")).strip() == "media_no_transcript"
        for row in full_text_rows
    )
    if textual_full_text_rows:
        corpus_status = "present"
        corpus_note = "Collected candidate-document full text is available and counted separately from legacy quotation rows."
    elif transcriptless_only:
        corpus_status = "partial"
        corpus_note = (
            "Only transcriptless media placeholders are present; no collected full-text corpus "
            "is available for substantive audit coverage."
        )
    elif metadata_rows or analysis_segment_rows:
        corpus_status = "partial"
        corpus_note = "Document metadata or analysis segments exist, but candidate_document_full_text.jsonl is absent or empty."
    else:
        corpus_status = "absent"
        corpus_note = "No collected candidate-document corpus is present; legacy quotation rows are discovery evidence only."
    if shared_unscoped_document_count:
        corpus_note = (
            f"{corpus_note} {shared_unscoped_document_count} shared multi-candidate document"
            f"{'' if shared_unscoped_document_count == 1 else 's'} lack usable locators and are"
            " retained as provenance only, excluded from analysis eligibility."
        )

    return {
        "study_window": {
            "start_year": study_start_year,
            "final_year": expected_years[-1],
            "expected_years": expected_year_strings,
        },
        "sufficiency": {
            "decision": "sufficient" if hard_gates["passes"] else "insufficient",
            "passes": hard_gates["passes"],
            "failed_gates": hard_gates["failed_gates"],
            "hard_gates": hard_gates["gates"],
        },
        "queue": {
            "source_mode": queue_source,
            "candidate_rows": len(queue_candidates),
            "race_count": len(race_summary_rows),
            "years_present": queue_years,
            "missing_years": [year for year in expected_year_strings if year not in queue_years],
            "has_2016_coverage": str(study_start_year) in queue_years,
            "status_counts": dict(sorted(queue_status_counts.items())),
            "group_counts": dict(sorted(queue_group_counts.items())),
        },
        "corpus": {
            "corpus_kind": "legacy_statement_rows",
            "treat_as_full_documents": False,
            "rows": len(corpus_rows),
            "verified_rows": sum(row["evidence_status"] == "verified" for row in corpus_rows),
            "source_unavailable_rows": sum(
                row["evidence_status"] == "source_unavailable" for row in corpus_rows
            ),
            "years_present": corpus_years,
            "missing_years": [year for year in expected_year_strings if year not in corpus_years],
            "years_with_verified_text": corpus_verified_years,
            "missing_verified_text_years": [
                year for year in expected_year_strings if year not in corpus_verified_years
            ],
            "has_2016_verified_text": str(study_start_year) in corpus_verified_years,
            "source_class_counts": dict(
                sorted(Counter(row["source_type_class"] for row in corpus_rows).items())
            ),
        },
        "document_corpus": {
            "status": corpus_status,
            "status_note": corpus_note,
            "metadata_rows": len(metadata_rows),
            "raw_extracted_document_count": raw_extracted_document_count,
            "full_text_rows": len(full_text_rows),
            "eligible_text_document_count": eligible_text_document_count,
            "shared_document_unscoped_count": shared_unscoped_document_count,
            "analysis_segment_rows": len(analysis_segment_rows),
            "eligible_analysis_segment_rows": len(eligible_analysis_segments),
            "substantive_segment_rows": len(substantive_segments),
            "substantive_candidate_count": len(document_support["candidate_index"]),
            "substantive_document_count": len(document_support["document_index"]),
            "groups_with_substantive_text": substantive_groups,
            "years_with_substantive_text": substantive_years,
            "missing_years": [year for year in expected_year_strings if year not in substantive_years],
            "source_classes_with_substantive_text": substantive_source_classes,
        },
        "paired_races": {
            "basis": "clean_candidate_document_metadata_and_analysis_segments",
            "race_count": len(paired_race_rows),
            "eligible_count": sum(row["paired_race_eligible"] == "true" for row in paired_race_rows),
            "clean_document_backed_races": sum(row["clean_document_count"] != "0" for row in paired_race_rows),
            "years_with_eligible_races": eligible_years,
            "missing_years": [year for year in expected_year_strings if year not in eligible_years],
            "has_2016_eligible_race": str(study_start_year) in eligible_years,
        },
        "support": {
            "group_year_rows": len(group_year_support_rows),
            "source_class_rows": len(source_class_support_rows),
            "missing_group_year_support": [
                f"{row['group']}:{row['election_year']}"
                for row in group_year_support_rows
                if row["missing_support"] == "true"
            ],
            "missing_source_classes": [
                row["source_type_class"]
                for row in source_class_support_rows
                if row["missing_support"] == "true"
            ],
        },
        "imbalance_diagnostics": {
            "rows": len(imbalance_rows),
            "flagged_rows": [
                {
                    "dimension": row["dimension"],
                    "bucket": row["bucket"],
                    "flag_reason": row["flag_reason"],
                }
                for row in imbalance_rows
                if row["hard_gate_pass"] == "false"
            ],
        },
        "discovery": {
            "source_inventory_rows": len(source_inventory_rows),
            "discovery_queue_rows": len(discovery_queue_rows),
            "document_queue_rows": len(document_queue_rows),
            "queued_candidates_without_any_document_seed": len(unseeded_queue_candidates),
            "top_unseeded_candidates": [
                {
                    "race_id": row["race_id"],
                    "candidate_name": row["candidate_name"],
                    "role": row["role"],
                    "election_year": row["election_year"],
                }
                for row in unseeded_queue_candidates[:10]
            ],
        },
        "retryable_gaps": {
            "count": len(retryable_gap_rows),
            "candidate_gap_count": sum(
                row["gap_type"] == "candidate_gap" for row in retryable_gap_rows
            ),
            "coverage_gap_years": [
                row["election_year"]
                for row in retryable_gap_rows
                if row["gap_type"] == "coverage_gap"
            ],
            "by_status": dict(sorted(retryable_status_counts.items())),
            "top_priority": [
                {
                    "gap_type": row["gap_type"],
                    "election_year": row["election_year"],
                    "candidate_name": row["candidate_name"],
                    "race_id": row["race_id"],
                }
                for row in _priority_rows(
                    retryable_gap_rows,
                    study_start_year,
                    expected_years[-1],
                )[:5]
            ],
        },
    }


def _year_from_value(value: str, filename: str, field: str) -> int:
    value = value.strip()
    if not re.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", value):
        raise ValueError(f"{filename}: invalid {field}")
    return int(value[:4])


def _identity(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = (
        value.replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("–", "-")
        .replace("—", "-")
    )
    return re.sub(r"\s+", " ", value).strip().casefold()


def _select_fields(row: dict[str, str], fieldnames: list[str]) -> dict[str, str]:
    return {field: row.get(field, "") for field in fieldnames}


def _as_bool(value: str) -> bool:
    return value.strip().casefold() == "true"


def _default_analysis_scope_for_url(source_url: str) -> str:
    normalized = source_url.strip().casefold()
    if "ballotpedia.org" in normalized:
        return "context_only"
    return "analysis"


def _candidate_source_key(
    *,
    race_id: str,
    candidate_name: str,
    role: str,
    source_url: str,
    fallback: str,
) -> tuple[str, str, str, str]:
    normalized_url = source_url.strip()
    if normalized_url:
        try:
            normalized_url = canonical_source_url(normalized_url)
        except ValueError:
            pass
    else:
        normalized_url = fallback.strip()
    return (
        race_id.strip(),
        _identity(candidate_name),
        role.strip(),
        normalized_url,
    )


def _metadata_completion_rank(metadata: dict[str, str]) -> tuple[int, int, int]:
    extraction_status = metadata.get("extraction_status", "").strip()
    return (
        extraction_status == "extracted",
        extraction_status == "media_no_transcript",
        metadata.get("fetch_status", "").strip() in {"fetched", "reused_raw"},
    )
