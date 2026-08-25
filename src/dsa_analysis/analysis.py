from collections import Counter
from datetime import date
from pathlib import Path

from .audit import validate
from .io import read_csv, read_json, write_csv
from .paths import (
    ANALYSIS_DATA_DIR,
    CONFIG_DIR,
    MANUAL_DIR,
    OUTPUT_DIR,
    PROCESSED_DIR,
    REPORT_DIR,
)


def analyze() -> dict[str, object]:
    audit = validate()
    audit_messages = tuple(f"Validation error: {error}" for error in audit.errors)
    audit_messages += audit.warnings

    documents = read_csv(MANUAL_DIR / "documents.csv")
    excerpts = read_csv(MANUAL_DIR / "excerpts.csv")
    contrasts = read_csv(MANUAL_DIR / "contrasts.csv")
    platform_comparisons = read_csv(MANUAL_DIR / "platform_comparisons.csv")
    reviewed = [row for row in excerpts if row["reviewed"].lower() == "true"]
    national_archive = _optional_csv("national_endorsement_archive.csv")
    local_verified = _optional_csv("local_endorsements_verified.csv")
    sticking_points = _optional_csv("primary_sticking_points.csv")
    canonical = _load_canonical_metrics()

    topic_counts = Counter(row["topic"] for row in reviewed)
    topic_rows = [
        {"topic": topic, "reviewed_excerpt_count": count}
        for topic, count in sorted(topic_counts.items())
    ]
    write_csv(
        OUTPUT_DIR / "tables" / "reviewed_excerpt_topics.csv",
        topic_rows,
        ["topic", "reviewed_excerpt_count"],
    )
    year_counts = Counter(row["national_endorsement"] for row in national_archive)
    year_rows = [
        {"endorsement_cycle": cycle, "campaign_count": count}
        for cycle, count in sorted(year_counts.items())
    ]
    write_csv(
        OUTPUT_DIR / "tables" / "national_endorsements_by_cycle.csv",
        year_rows,
        ["endorsement_cycle", "campaign_count"],
    )
    local_cycle_counts = Counter(
        (row["election_year"] or "unknown", row["chapter"])
        for row in local_verified
    )
    write_csv(
        OUTPUT_DIR / "tables" / "local_endorsements_by_cycle_chapter.csv",
        [
            {
                "election_year": year,
                "chapter": chapter,
                "verified_endorsement_count": count,
            }
            for (year, chapter), count in sorted(local_cycle_counts.items())
        ],
        ["election_year", "chapter", "verified_endorsement_count"],
    )
    sticking_counts = Counter(
        (row["topic"], row["contrast_type"], row["relationship_code"])
        for row in sticking_points
    )
    write_csv(
        OUTPUT_DIR / "tables" / "primary_sticking_points_summary.csv",
        [
            {
                "topic": topic,
                "contrast_type": contrast_type,
                "relationship_code": relationship,
                "count": count,
            }
            for (topic, contrast_type, relationship), count in sorted(
                sticking_counts.items()
            )
        ],
        ["topic", "contrast_type", "relationship_code", "count"],
    )
    write_csv(
        OUTPUT_DIR / "tables" / "canonical_analysis_overview.csv",
        [
            {"section": section, "metric": metric, "value": value}
            for section, metrics in canonical["overview"].items()
            for metric, value in metrics.items()
        ],
        ["section", "metric", "value"],
    )

    stats = {
        **canonical["stats"],
        "national_archive_records": len(national_archive),
    }
    _write_report(
        stats,
        documents,
        reviewed,
        platform_comparisons,
        contrasts,
        year_rows,
        audit_messages,
    )
    return stats


def _write_report(
    stats: dict[str, object],
    documents: list[dict[str, str]],
    excerpts: list[dict[str, str]],
    platform_comparisons: list[dict[str, str]],
    contrasts: list[dict[str, str]],
    year_rows: list[dict[str, object]],
    warnings: tuple[str, ...],
) -> None:
    config = read_json(CONFIG_DIR / "sources.json")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    quote_lines = []
    documents_by_id = {row["document_id"]: row for row in documents}
    for row in excerpts[:3]:
        document = documents_by_id[row["document_id"]]
        quote_lines.append(
            f'- **{row["topic"]}/{row["subtopic"]}:** "{row["quote"]}" '
            f'— {row["speaker"]}, [{document["title"]}]({document["url"]}), '
            f'{row["locator"]}'
        )
    warning_lines = [f"- {warning}" for warning in warnings]
    excerpts_by_id = {row["excerpt_id"]: row for row in excerpts}
    comparison_lines = []
    for row in platform_comparisons:
        dsa = excerpts_by_id[row["dsa_excerpt_id"]]
        democratic = excerpts_by_id[row["democratic_excerpt_id"]]
        comparison_lines.append(
            f'### {row["topic"].replace("_", " ").title()} ({row["cycle"]})\n\n'
            f'- **DSA:** "{dsa["quote"]}"\n'
            f'- **Democratic platform:** "{democratic["quote"]}"\n'
            f'- **Coded relationship:** `{row["relationship_code"]}` — {row["notes"]}'
        )
    contrast_lines = []
    for row in contrasts:
        candidate = excerpts_by_id[row["candidate_excerpt_id"]]
        opponent = excerpts_by_id[row["opponent_excerpt_id"]]
        document = documents_by_id[candidate["document_id"]]
        contrast_lines.append(
            f'### {row["race_id"]}: {row["topic"].replace("_", " ").title()}\n\n'
            f'- **{candidate["speaker"]}:** "{candidate["quote"]}"\n'
            f'- **{opponent["speaker"]}:** "{opponent["quote"]}"\n'
            f'- **Coded relationship:** `{row["relationship_code"]}` — {row["notes"]}\n'
            f'- **Shared source:** [{document["title"]}]({document["url"]})'
        )
    year_lines = [
        f'- {row["endorsement_cycle"]}: {row["campaign_count"]}'
        for row in year_rows
    ]
    text = f"""# DSA and Democratic primary positions

**Research window:** {config["study_start"]} through {config["research_cutoff"]}

## Scope and canonical outputs

This report is generated from the current race registry, full-text audit, organizational-context
inventory/extraction summaries, endorsement-census outputs, and full-corpus analysis manifests.
The small reviewed quotations below are qualitative examples only; their counts are not corpus
totals and are not used as the denominator for the quantitative sections.

## 1. Denominator completeness

- Canonical races: {stats["canonical_races"]}
- In-scope DSA-endorsed Democratic primaries: {stats["in_scope_races"]}
- In-scope races with unresolved denominator metadata: {stats["in_scope_unresolved_races"]}
- In-scope candidate/race records represented in the registry: {stats["in_scope_candidate_records"]}
- Valid official-election-source rows: {stats["valid_official_election_source_rows"]}
- National candidate endorsements: {stats["national_candidate_endorsements"]}
- National endorsements matched to in-scope races: {stats["national_endorsements_matched_in_scope"]}
- National endorsements absent from the registry:
  {stats["national_endorsements_absent_from_registry"]}

These are denominator and reconciliation counts, not claims that every candidate has usable text.
The race denominator remains incomplete while unresolved in-scope races or unmatched national
endorsements remain.

## 2. National and local endorsement census

The official national archive contains **{stats["national_archive_records"]} campaign records**.
Its cycle distribution is:

{chr(10).join(year_lines) or "- No official national archive cycle rows are available."}

- Verified local candidate endorsements: {stats["local_verified_endorsements"]}
- Local chapter-year search units: {stats["local_coverage_rows"]}
- Local chapter-year units still `not_searched` or `found_unverified`:
  {stats["local_unresolved_rows"]}

The local verified file is a census output, but unresolved chapter-year search units remain
explicit coverage gaps. Verified endorsement counts must not be substituted for a complete
nationwide local denominator.

## 3. Candidate-document coverage

- Registry candidate/race records in the document queue: {stats["candidate_queue_records"]}
- Records with verified extraction status: {stats["verified_candidate_records"]}
- Retryable candidate-document gaps: {stats["retryable_candidate_gaps"]}
- Candidates with substantive extracted text: {stats["substantive_candidate_count"]}
- Substantive source documents: {stats["substantive_document_count"]}
- Eligible analysis segments before analysis-specific deduplication:
  {stats["substantive_segment_rows"]}
- Clean document-backed races: {stats["document_backed_races"]}
- Two-sided paired races eligible for comparison: {stats["paired_race_eligible"]}

Candidate-document coverage is incomplete. Shared multi-candidate documents without usable
locators remain provenance-only and are excluded from analysis eligibility.

## 4. Official-platform coverage

- Represented state-cycle rows: {stats["organizational_state_cycles"]}
- Inventory rows across DNC, DSA, state-party, and local-DSA categories:
  {stats["organizational_inventory_rows"]}
- Verified organizational-context inventory rows: {stats["organizational_verified_rows"]}
- Platform-gap rows: {stats["organizational_platform_gap_rows"]}
- Fetched organizational documents: {stats["organizational_fetched_documents"]}
- Successfully extracted organizational documents: {stats["organizational_successful_documents"]}
- Extraction errors: {stats["organizational_extraction_errors"]}
- Eligible full-platform documents in lexical analysis: {stats["official_analysis_documents"]}
- Eligible full-platform source segments: {stats["official_source_segments"]}

Every represented state-cycle has an explicit status for each context category, but explicit
`searched_not_found`, `source_unavailable`, and `not_applicable` statuses are not extracted
platform text. Official-platform lexical results therefore describe the recoverable full-platform
subset.

## 5. Full-corpus lexical and topic outputs

- Candidate source documents used by lexical analysis: {stats["candidate_source_documents"]}
- Candidate source segments before shared-text deduplication: {stats["candidate_source_segments"]}
- Candidate segments after deduplication: {stats["candidate_analysis_segments"]}
- Candidate analysis documents after deduplication: {stats["candidate_analysis_documents"]}
- Unique source-supported primary contrasts: {stats["analysis_sticking_points"]}
- Local-model classified segments: {stats["model_classified_rows"]}
- Local-model unclassified segments below threshold: {stats["model_unclassified_rows"]}

TF-IDF, MPIF, document prevalence, source mix, cycle volume, explicit-conflict, and local-model
topic outputs are generated from the full eligible segment snapshots, not from the legacy manual
excerpt table.

![Difference in policy language](../outputs/figures/text_analysis/policy_language_difference.svg)

![Shared policy emphasis](../outputs/figures/text_analysis/policy_language_overlap.svg)

![Shared affirmative policy mechanisms](../outputs/figures/text_analysis/shared_affirmative_policy_mechanisms.svg)

![Official contrast](../outputs/figures/text_analysis/official_policy_contrasts.svg)

![Modeled topics](../outputs/figures/text_analysis/model_topic_emphasis_difference.svg)

## 6. Provisional KDE

- Status: **{stats["kde_status"]}**
- Retained segments: {stats["kde_retained_segments"]}
- Candidates represented: {stats["kde_endorsed_candidates"]} endorsed and
  {stats["kde_opponent_candidates"]} opponents
- Selected UMAP dimensions: {stats["kde_selected_dimensions"]}
- Density-fit sample: {stats["kde_endorsed_fit_count"]} endorsed and
  {stats["kde_opponent_fit_count"]} opponent segments

The KDE remains provisional because the full-text sufficiency audit fails. It describes the
currently recoverable segmented corpus and is not a complete-census estimate. The labeled
regions are derived from the underlying segments in each locally overrepresented or shared
high-density area; each label reports distinctive terms, an extractive representative passage,
and candidate support.

![Provisional GTE KDE](../figures/provisional_gte_kde.png)

## 7. Small reviewed qualitative examples

These quotations and hand-coded contrasts are intentionally a small, nonrepresentative
qualitative layer. They illustrate what exact source-level evidence looks like; they are not
frequency estimates and their row counts are not corpus totals.

{chr(10).join(quote_lines) or "- No reviewed excerpts are available."}

### Reviewed DSA-Democratic platform examples

{chr(10).join(comparison_lines) or "- No reviewed comparisons are available."}

### Reviewed primary sticking-point example

{chr(10).join(contrast_lines) or "- No reviewed candidate contrasts are available."}

## Remaining gaps

- The race registry has {stats["in_scope_unresolved_races"]} unresolved in-scope races and
  {stats["national_endorsements_absent_from_registry"]} national endorsements absent from the
  registry.
- Candidate-document recovery has {stats["retryable_candidate_gaps"]} retryable candidate gaps;
  the full-text sufficiency decision is **{stats["full_text_sufficiency"]}**.
- Local census coverage has {stats["local_unresolved_rows"]} unresolved chapter-year units.
- Organizational context has {stats["organizational_platform_gap_rows"]} platform-gap rows and
  {stats["organizational_extraction_errors"]} extraction error.
- Source-class and group/year imbalance diagnostics still prevent population-level frequency
  claims.

## Audit warnings

{chr(10).join(warning_lines) or "- None."}

Generated {date.today().isoformat()}. See `docs/methodology.md` for evidence rules.
"""
    (REPORT_DIR / "draft.md").write_text(text, encoding="utf-8")


def _optional_csv(name: str) -> list[dict[str, str]]:
    path = PROCESSED_DIR / name
    return (
        read_csv(path)
        if path.exists() or path.with_suffix(path.suffix + ".gz").exists()
        else []
    )


def _load_canonical_metrics(
    processed_dir: Path = PROCESSED_DIR,
    analysis_data_dir: Path = ANALYSIS_DATA_DIR,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, dict[str, object]]:
    race = read_json(processed_dir / "race_registry_summary.json")
    full_text = read_json(processed_dir / "full_text_audit_summary.json")
    organization = read_json(processed_dir / "organizational_context_summary.json")
    extraction = read_json(
        processed_dir / "organizational_context_extraction_summary.json"
    )
    lexical = read_json(output_dir / "tables" / "text_analysis" / "analysis_manifest.json")
    model = read_json(analysis_data_dir / "model_topic_validation.json")
    kde = read_json(analysis_data_dir / "provisional_gte_kde" / "summary.json")

    registry_rows = read_csv(processed_dir / "race_registry.csv")
    local_rows = read_csv(processed_dir / "local_endorsements_verified.csv")
    local_coverage = read_csv(processed_dir / "coverage_ledger.csv")
    in_scope_candidate_records = sum(
        int(row["candidate_count"])
        for row in registry_rows
        if row["scope_kind"] == "tracked_dsa_endorsed_democratic_primary"
    )
    local_unresolved_rows = sum(
        row["status"] in {"not_searched", "found_unverified"}
        for row in local_coverage
    )
    stats = {
        "canonical_races": race["canonical_races"],
        "in_scope_races": race["in_scope_races"],
        "in_scope_unresolved_races": race["in_scope_unresolved_races"],
        "in_scope_candidate_records": in_scope_candidate_records,
        "valid_official_election_source_rows": race[
            "valid_official_election_source_rows"
        ],
        "national_candidate_endorsements": race["national_candidate_endorsements"],
        "national_endorsements_matched_in_scope": race[
            "national_endorsements_matched_in_scope"
        ],
        "national_endorsements_absent_from_registry": race[
            "national_endorsements_absent_from_registry"
        ],
        "local_verified_endorsements": len(local_rows),
        "local_coverage_rows": len(local_coverage),
        "local_unresolved_rows": local_unresolved_rows,
        "candidate_queue_records": full_text["queue"]["candidate_rows"],
        "verified_candidate_records": full_text["queue"]["status_counts"]["verified"],
        "retryable_candidate_gaps": full_text["retryable_gaps"]["candidate_gap_count"],
        "substantive_candidate_count": full_text["document_corpus"][
            "substantive_candidate_count"
        ],
        "substantive_document_count": full_text["document_corpus"][
            "substantive_document_count"
        ],
        "substantive_segment_rows": full_text["document_corpus"][
            "substantive_segment_rows"
        ],
        "document_backed_races": full_text["paired_races"][
            "clean_document_backed_races"
        ],
        "paired_race_eligible": full_text["paired_races"]["eligible_count"],
        "full_text_sufficiency": full_text["sufficiency"]["decision"],
        "organizational_state_cycles": organization["represented_state_cycles"],
        "organizational_inventory_rows": organization["inventory"]["row_count"],
        "organizational_verified_rows": organization["inventory"][
            "by_verification_status"
        ]["verified"],
        "organizational_platform_gap_rows": organization["coverage"][
            "platform_gap_rows"
        ],
        "organizational_fetched_documents": extraction["fetched_documents"],
        "organizational_successful_documents": extraction["successful_documents"],
        "organizational_extraction_errors": extraction["extraction_errors"],
        "official_analysis_documents": lexical["official_documents"],
        "official_source_segments": lexical["official_source_segments"],
        "candidate_source_documents": lexical["candidate_source_documents"],
        "candidate_source_segments": lexical["candidate_source_segments"],
        "candidate_analysis_segments": lexical["candidate_segments"],
        "candidate_analysis_documents": lexical["candidate_documents"],
        "analysis_sticking_points": lexical["sticking_points"],
        "model_classified_rows": model["classified_rows"],
        "model_unclassified_rows": model["unclassified_rows"],
        "kde_status": kde["status"],
        "kde_retained_segments": kde["retained_segments"],
        "kde_endorsed_candidates": kde["candidate_counts"]["endorsed"],
        "kde_opponent_candidates": kde["candidate_counts"]["opponent"],
        "kde_selected_dimensions": kde["selected_dimensions"],
        "kde_endorsed_fit_count": kde["kde"]["fit_counts"]["endorsed"],
        "kde_opponent_fit_count": kde["kde"]["fit_counts"]["opponent"],
    }
    overview = {
        "denominator_completeness": {
            key: stats[key]
            for key in (
                "canonical_races",
                "in_scope_races",
                "in_scope_unresolved_races",
                "in_scope_candidate_records",
                "valid_official_election_source_rows",
                "national_endorsements_absent_from_registry",
            )
        },
        "candidate_document_coverage": {
            key: stats[key]
            for key in (
                "candidate_queue_records",
                "verified_candidate_records",
                "retryable_candidate_gaps",
                "substantive_candidate_count",
                "substantive_document_count",
                "paired_race_eligible",
            )
        },
        "official_platform_coverage": {
            key: stats[key]
            for key in (
                "organizational_state_cycles",
                "organizational_inventory_rows",
                "organizational_platform_gap_rows",
                "organizational_successful_documents",
                "official_analysis_documents",
                "official_source_segments",
            )
        },
        "full_corpus_analysis": {
            key: stats[key]
            for key in (
                "candidate_source_documents",
                "candidate_source_segments",
                "candidate_analysis_segments",
                "model_classified_rows",
                "analysis_sticking_points",
            )
        },
        "provisional_kde": {
            key: stats[key]
            for key in (
                "kde_status",
                "kde_retained_segments",
                "kde_endorsed_candidates",
                "kde_opponent_candidates",
                "kde_selected_dimensions",
            )
        },
    }
    return {"stats": stats, "overview": overview}
