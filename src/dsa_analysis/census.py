"""Source-first accounting of known coverage gaps, not a claim to an exhaustive census."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from .coverage import coverage_chapters
from .io import read_csv, read_json, write_csv
from .paths import ANALYSIS_DATA_DIR, CONFIG_DIR, MANUAL_DIR, PROCESSED_DIR
from .race_registry import IN_SCOPE_KIND, _national_endorsement_reconciliation_rows

GAP_FIELDS = [
    "kind", "record_id", "year", "candidate", "race_ids", "issue", "source_url", "detail",
]


def census_gaps() -> tuple[list[dict[str, str]], dict]:
    config = read_json(CONFIG_DIR / "sources.json")
    source_year = int(config.get("source_start", config["study_start"])[:4])
    first_year = int(config["study_start"][:4])
    final_year = int(config["research_cutoff"][:4])
    gaps = []
    inputs = {}

    def load(filename: str) -> list[dict[str, str]]:
        path = PROCESSED_DIR / filename
        if not path.exists():
            add("artifact", filename, "", "missing_artifact")
            return []
        inputs[str(path.relative_to(PROCESSED_DIR))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        return read_csv(path)

    def add(kind, key, year, issue, candidate="", races="", url="", detail=""):
        gaps.append(dict(zip(GAP_FIELDS, (
            kind, key, year, candidate, races, issue, url, detail,
        ), strict=True)))

    registry = load("race_registry.csv")
    coverage = load("coverage_ledger.csv")
    expected = {
        f'{chapter["record_id"]}-{year}'
        for chapter in coverage_chapters()
        for year in range(source_year, final_year + 1)
    }
    present = Counter(row["coverage_id"] for row in coverage)
    for key in sorted(expected - present.keys()):
        add("chapter_year", key, key.rsplit("-", 1)[-1], "missing_chapter_year")
    for key, count in present.items():
        if count != 1:
            add("chapter_year", key, key.rsplit("-", 1)[-1], "duplicate_chapter_year")
    for row in coverage:
        if row["status"] not in {"verified", "searched_not_found", "source_unavailable"}:
            add("chapter_year", row["coverage_id"], row["election_year"],
                row["status"], url=row["evidence_urls"],
                detail=f'{row["chapter"]}: {row["search_method"]}')
        elif not row.get("searched_on") or not row.get("evidence_urls"):
            add("chapter_year", row["coverage_id"], row["election_year"],
                "undocumented_search_resolution", detail=row["chapter"])

    archive = load("national_endorsement_archive.csv")
    national = _national_endorsement_reconciliation_rows(
        PROCESSED_DIR / "national_endorsement_archive.csv",
        registry,
        tuple(sorted(MANUAL_DIR.glob("national_census_resolutions_*.csv"))),
    )
    national_ids = {row["record_id"] for row in national}
    for row in archive:
        if "Ballot Initiative" in row["office_types"].split(" | "):
            continue
        if row["record_id"] not in national_ids and not row["election_date"]:
            add("national_endorsement", row["record_id"], "", "unresolved_election_year",
                row["campaign"], url=row["source_view_url"])
    for row in national:
        if row["election_year"] > str(final_year):
            continue
        if row["review_status"] != "resolved":
            add("national_endorsement", row["record_id"], row["election_year"],
                row["review_status"], row["campaign"], row["matched_race_ids"],
                detail=row["notes"])
        if row["census_verification_status"] != "verified":
            add("national_endorsement", row["record_id"], row["election_year"],
                "election_scope_not_verified", row["campaign"], row["matched_race_ids"],
                detail=row["census_classification"])

    accepted = load("local_endorsements_verified.csv")
    rejected = load("local_endorsements_rejected.csv")
    adjudicated = {row["endorsement_key"] for row in accepted + rejected}
    for row in load("local_endorsement_candidates.csv"):
        year = row["election_year"]
        if year and (year < str(first_year) or year > str(final_year)):
            continue
        if row["endorsement_key"] not in adjudicated:
            add("local_endorsement", row["endorsement_key"], year,
                "missing_second_pass_review", row["candidate_name"], url=row["source_url"])
    for row in accepted:
        if not row["election_year"]:
            add("local_endorsement", row["endorsement_key"], "",
                "unresolved_election_year", row["candidate_name"], url=row["source_url"])

    queue = load("opponent_research_queue.csv")
    resolved = {"verified", "source_unavailable", "not_a_primary", "not_applicable"}
    for row in queue:
        year = row["election_year"]
        if year and not first_year <= int(year) <= final_year:
            continue
        missing = [
            field for field in (
                "race_resolution_status", "opponent_roster_status",
                "candidate_statement_status", "opponent_statement_status",
            ) if row[field] not in resolved
        ]
        if missing:
            add("candidacy", row["queue_id"], year, "incomplete_race_evidence",
                row["candidate_name"], url=row["endorsement_source_url"],
                detail=" | ".join(missing))

    race_text = {row["race_id"]: row for row in load("full_text_race_summary.csv")}
    for row in registry:
        year = row["election_year"]
        if not first_year <= int(year) <= final_year:
            continue
        if row["unresolved_fields"]:
            add("race", row["race_id"], year, "unresolved_registry_fields",
                row["endorsed_candidate"], row["race_id"],
                row["official_election_source"], row["unresolved_fields"])
        if row["scope_kind"] != IN_SCOPE_KIND:
            continue
        text = race_text.get(row["race_id"], {})
        if text.get("paired_race_eligible") != "true":
            add("race", row["race_id"], year, "missing_paired_campaign_text",
                row["endorsed_candidate"], row["race_id"],
                detail=text.get("paired_race_gap_reason", "No full-text audit row"))
        if row["election_date"] > config["research_cutoff"]:
            add("race", row["race_id"], year, "election_after_cutoff",
                row["endorsed_candidate"], row["race_id"])

    gaps.sort(key=lambda row: (row["year"], row["kind"], row["record_id"], row["issue"]))
    summary = {
        "as_of": config["research_cutoff"],
        "study_start": config["study_start"],
        "source_start": config.get("source_start", config["study_start"]),
        "complete": not gaps,
        "national_archive_rows": len(archive),
        "national_candidate_endorsements": len(national),
        "registry_races": len(registry),
        "strict_primary_races": sum(row["scope_kind"] == IN_SCOPE_KIND for row in registry),
        "expected_chapter_years": len(expected),
        "gaps": len(gaps),
        "gaps_by_kind": dict(sorted(Counter(row["kind"] for row in gaps).items())),
        "input_sha256": inputs,
        "limitations": [
            "This is an audit of discovered sources, not proof that all historical chapters "
            "or races have been discovered.",
            "Endorsement source dates, primary dates, and general election dates are distinct.",
            "One verified endorsement does not establish an exhaustive chapter-year search.",
            "National DSA primary outcomes are organization-reported, not certified results.",
        ],
    }
    return gaps, summary


def audit_census(output_dir: Path = ANALYSIS_DATA_DIR) -> dict:
    gaps, summary = census_gaps()
    write_csv(output_dir / "census_gaps.csv", gaps, GAP_FIELDS)
    years = range(int(summary["source_start"][:4]), int(summary["as_of"][:4]) + 1)
    registry = read_csv(PROCESSED_DIR / "race_registry.csv")
    yearly = [
        {
            "year": year,
            "discovery_only": str(year < int(summary["study_start"][:4])).lower(),
            "registry_races": sum(row["election_year"] == str(year) for row in registry),
            "strict_primary_races": sum(
                row["election_year"] == str(year) and row["scope_kind"] == IN_SCOPE_KIND
                for row in registry
            ),
            "gap_records": sum(row["year"] == str(year) for row in gaps),
        }
        for year in years
    ]
    write_csv(output_dir / "census_by_year.csv", yearly, list(yearly[0]))
    (output_dir / "census_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary
