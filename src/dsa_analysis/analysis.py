from collections import Counter
from datetime import date

from .audit import validate
from .io import read_csv, read_json, write_csv
from .paths import CONFIG_DIR, MANUAL_DIR, OUTPUT_DIR, PROCESSED_DIR, REPORT_DIR


def analyze() -> dict[str, int]:
    audit = validate()
    if not audit.ok:
        raise ValueError("Validation failed:\n" + "\n".join(audit.errors))

    documents = read_csv(MANUAL_DIR / "documents.csv")
    endorsements = read_csv(MANUAL_DIR / "endorsements.csv")
    race_candidates = read_csv(MANUAL_DIR / "race_candidates.csv")
    excerpts = read_csv(MANUAL_DIR / "excerpts.csv")
    contrasts = read_csv(MANUAL_DIR / "contrasts.csv")
    platform_comparisons = read_csv(MANUAL_DIR / "platform_comparisons.csv")
    coverage = read_csv(MANUAL_DIR / "coverage.csv")
    reviewed = [row for row in excerpts if row["reviewed"].lower() == "true"]
    national_archive = _optional_csv("national_endorsement_archive.csv")
    candidate_queue = _optional_csv("primary_research_queue.csv")
    coverage_template = _optional_csv("coverage_template.csv")
    chapter_crawl = _optional_csv("chapter_crawl_status.csv")
    local_pages = _optional_csv("local_endorsement_pages.csv")
    local_mentions = _optional_csv("local_endorsement_mentions.csv")
    local_leads = _optional_csv("local_endorsement_leads.csv")
    census_coverage = _optional_csv("coverage_ledger.csv")
    local_verified = _optional_csv("local_endorsements_verified.csv")
    local_rejected = _optional_csv("local_endorsements_rejected.csv")
    opponent_queue = _optional_csv("opponent_research_queue.csv")
    race_rosters = _optional_csv("race_rosters_discovered.csv")
    statement_evidence = _optional_csv("candidate_statement_evidence.csv")
    sticking_points = _optional_csv("primary_sticking_points.csv")

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

    stats = {
        "documents": len(documents),
        "verified_documents": sum(
            row["verification_status"] == "verified" for row in documents
        ),
        "endorsements": len(endorsements),
        "tracked_races": len({row["race_id"] for row in race_candidates}),
        "race_candidates": len(race_candidates),
        "opponent_candidates": sum(
            row["role"] == "opponent" for row in race_candidates
        ),
        "opponents_with_verified_evidence": sum(
            row["role"] == "opponent" and row["evidence_status"] == "verified"
            for row in race_candidates
        ),
        "reviewed_excerpts": len(reviewed),
        "platform_comparisons": sum(
            row["reviewed"].lower() == "true" for row in platform_comparisons
        ),
        "contrasts": len(contrasts),
        "coverage_rows": len(coverage),
        "national_archive_records": len(national_archive),
        "candidate_queue_rows": len(candidate_queue),
        "coverage_search_units": len(coverage_template),
        "chapters_crawled": len(chapter_crawl),
        "local_endorsement_pages": len(local_pages),
        "local_endorsement_mentions": len(local_mentions),
        "local_endorsement_leads": len(local_leads),
        "census_coverage_rows": len(census_coverage),
        "census_unresolved_rows": sum(
            row["status"] in {"not_searched", "found_unverified"}
            for row in census_coverage
        ),
        "local_verified_endorsements": len(local_verified),
        "local_rejected_leads": len(local_rejected),
        "all_endorsed_candidacies": len(opponent_queue),
        "race_roster_rows": len(race_rosters),
        "race_reviews_resolved": sum(
            row["race_resolution_status"]
            in {"verified", "not_a_primary", "source_unavailable"}
            for row in opponent_queue
        ),
        "candidacy_unresolved_rows": sum(
            any(
                row[field]
                not in {
                    "verified",
                    "not_a_primary",
                    "not_applicable",
                    "source_unavailable",
                }
                for field in (
                    "race_resolution_status",
                    "opponent_roster_status",
                    "candidate_statement_status",
                    "opponent_statement_status",
                )
            )
            for row in opponent_queue
        ),
        "candidate_evidence_rows": len(statement_evidence),
        "sticking_point_rows": len(sticking_points),
    }
    _write_report(
        stats,
        documents,
        reviewed,
        platform_comparisons,
        contrasts,
        sticking_points,
        year_rows,
        audit.warnings,
    )
    return stats


def _write_report(
    stats: dict[str, int],
    documents: list[dict[str, str]],
    excerpts: list[dict[str, str]],
    platform_comparisons: list[dict[str, str]],
    contrasts: list[dict[str, str]],
    sticking_points: list[dict[str, str]],
    year_rows: list[dict[str, object]],
    warnings: tuple[str, ...],
) -> None:
    census_complete = (
        stats["census_unresolved_rows"] == 0
        and stats["candidacy_unresolved_rows"] == 0
    )
    local_census_note = (
        "Together, the national archive and verified local layer form the completed "
        "nationwide endorsement census under the methodology's source-availability rules."
        if census_complete
        else "The verified local layer is still incomplete and must not be treated as a "
        "nationwide local-endorsement census."
    )
    completion_note = (
        "Strict validation passes: every chapter-year is resolved and every endorsed "
        "candidacy has a resolved race, roster, and candidate/opponent evidence status."
        if census_complete
        else "The analysis is not complete until `uv run dsa-analysis validate --strict` "
        "passes."
    )
    sticking_note = (
        "These are nationwide counts of recorded, source-supported contrasts in the "
        "completed census. They measure expressed and recoverable campaign differences, "
        "not unspoken positions or voter priorities."
        if census_complete
        else "These counts come only from currently verified candidate evidence and are "
        "not yet nationwide frequency estimates."
    )
    limitations = (
        "The census is complete under the stated protocol, but source-unavailable records "
        "remain explicit unknowns. A missing quotation does not imply that a candidate held "
        "no position. Topic counts measure recoverable statements and coded contrasts, not "
        "the prevalence or intensity of beliefs among all candidates or voters. The platform "
        "matrix is limited to the reviewed official documents and election cycles."
        if census_complete
        else "The national and local endorsement census, full platform coding, candidate/"
        "opponent evidence, and primary-level contrasts are not complete. Frequency claims "
        "are therefore premature."
    )
    config = read_json(CONFIG_DIR / "sources.json")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    quote_lines = []
    documents_by_id = {row["document_id"]: row for row in documents}
    for row in excerpts:
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
    sticking_topic_counts = Counter(row["topic"] for row in sticking_points)
    sticking_lines = [
        f"- {topic.replace('_', ' ').title()}: {count}"
        for topic, count in sticking_topic_counts.most_common()
    ]
    text = f"""# DSA and Democratic primary positions

**Research window:** {config["study_start"]} through {config["research_cutoff"]}

## Current dataset status

- Registered documents: {stats["documents"]}
- Verified documents: {stats["verified_documents"]}
- Verified DSA endorsements: {stats["endorsements"]}
- Tracked Democratic primaries: {stats["tracked_races"]}
- Candidates on tracked primary ballots: {stats["race_candidates"]}
- Opponents requiring comparison: {stats["opponent_candidates"]}
- Opponents with verified first-party evidence: {stats["opponents_with_verified_evidence"]}
- Reviewed exact excerpts: {stats["reviewed_excerpts"]}
- Reviewed party-platform comparisons: {stats["platform_comparisons"]}
- Candidate/opponent contrasts: {stats["contrasts"]}
- Chapter-year coverage records: {stats["coverage_rows"]}

## Official national endorsement census

The official DSA National archive currently yields **{stats["national_archive_records"]} unique
campaign records**. Removing rows categorized only as ballot initiatives leaves
**{stats["candidate_queue_rows"]} candidate or office records** requiring verification of party,
primary type, opponents, and campaign sources. The current chapter directory creates
**{stats["coverage_search_units"]} chapter-year search units** for 2016–2026.

{chr(10).join(year_lines) or "- Run the official Airtable collection commands to populate this section."}

These counts cover national endorsements. The manually verified layer separately includes local
endorsements such as Zohran Mamdani by NYC-DSA and Francesca Hong by Madison Area DSA and
Milwaukee DSA. {local_census_note}

## Nationwide local-chapter census status

- Current chapters and organizing committees crawled: {stats["chapters_crawled"]}
- Endorsement-like first-party pages discovered: {stats["local_endorsement_pages"]}
- Reviewable endorsement mentions extracted: {stats["local_endorsement_mentions"]}
- High-confidence candidate/office leads extracted: {stats["local_endorsement_leads"]}
- Independently verified local candidate endorsements: {stats["local_verified_endorsements"]}
- Rejected candidate-level false positives: {stats["local_rejected_leads"]}
- Chapter-year coverage units: {stats["census_coverage_rows"]}
- Unresolved chapter-year units: {stats["census_unresolved_rows"]}
- National and local endorsed candidacies queued: {stats["all_endorsed_candidacies"]}
- Endorsed candidacies with resolved roster research: {stats["race_reviews_resolved"]}
- Candidate rows in verified primary rosters: {stats["race_roster_rows"]}
- Exact candidate evidence rows: {stats["candidate_evidence_rows"]}
- Derived primary sticking-point rows: {stats["sticking_point_rows"]}

{completion_note}

## Findings from reviewed first-party text

The reviewed DSA material explicitly describes democratic socialism in terms of replacing
capitalism, expanding democratic control into workplaces and the economy, and collective or
public ownership of key economic systems. It also describes electoral work as movement-building
rather than simple alignment with the Democratic Party. These are direct textual observations,
not claims about every endorsed candidate.

{chr(10).join(quote_lines) or "- No reviewed excerpts are available."}

## Reviewed DSA-Democratic platform contrasts

{chr(10).join(comparison_lines) or "- No reviewed comparisons are available."}

## Reviewed primary sticking-point example

{chr(10).join(contrast_lines) or "- No reviewed candidate contrasts are available."}

## Primary sticking-point counts

{sticking_note}

{chr(10).join(sticking_lines) or "- No derived sticking points are available."}

## Reproducible text-analysis figures

The full TF-IDF, MPIF, topic-share, similarity, and cycle analysis is generated with
`uv run dsa-analysis analyze-text`.

![Distinctive candidate MPIF terms](../outputs/figures/text_analysis/candidate_mpif_terms.svg)

![Official DSA and Democratic Party MPIF terms](../outputs/figures/text_analysis/official_dsa_democratic_mpif.svg)

![Candidate topic shares](../outputs/figures/text_analysis/candidate_topic_shares.svg)

![Primary sticking points by topic](../outputs/figures/text_analysis/sticking_points_by_topic.svg)

![Primary sticking points by cycle](../outputs/figures/text_analysis/sticking_points_by_cycle.svg)

## Limitations

{limitations}

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
