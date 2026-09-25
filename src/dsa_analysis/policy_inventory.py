"""Account for policy evidence across the whole historical primary registry."""

import json
import hashlib
import re
from collections import defaultdict
from datetime import date

from .document_corpus import candidate_document_analysis_issues, candidate_slug, campaign_window_for_election
from .historical_policy import REVIEW_METHOD, race_aliases
from .io import read_csv, read_json, write_csv
from .paths import ANALYSIS_DATA_DIR, MANUAL_DIR, PROCESSED_DIR, ROOT
from .policy_comparison import archive_capture_date
from .national_platform_applicability import is_presidential_office, name_key


PRESIDENTIAL_BALLOT_OPTIONS = {
    "no preference", "scattered", "uncommitted", '"uncommitted"',
    "uninstructed delegation", "miscellaneous", "uncommitted delegate",
    "uncommitted delegates", "undeclared", "uninstructed delegate",
    "noncommitted delegate", "uncommitted nj", "uninstructed campaign",
}


def participant_kind(office: str, name: str, endorsed: set[str]) -> str:
    if is_presidential_office(office) and name.casefold() in PRESIDENTIAL_BALLOT_OPTIONS:
        return "endorsed_ballot_campaign" if name in endorsed else "non_person_ballot_option"
    return "individual_candidate"


def inventory_rows(races: dict, metadata: list[dict], endorsements: list[dict], statements: list[dict]) -> tuple[list, list, list]:
    aliases = race_aliases(races, endorsements)
    lookup = defaultdict(set)
    for race_id, values in aliases.items():
        for value in values:
            lookup[value].add(race_id)
    source_rows = []
    by_candidate = defaultdict(list)
    for document in metadata:
        matches = lookup.get(document["race_id"], set())
        if len(matches) != 1:
            continue
        race_id = next(iter(matches))
        race = races[race_id]
        names = [
            name for name in race["all_candidates"].split(" | ")
            if candidate_slug(name) == candidate_slug(document["candidate_name"])
        ]
        if len(names) != 1:
            continue
        issues = candidate_document_analysis_issues(document)
        non_temporal = set(issues) - {"undated_source_without_in_window_capture", "outside_primary_campaign_window"}
        observed = archive_capture_date(document) or document.get("retrieved_at", "")[:10]
        if not issues and document["extraction_status"] == "extracted":
            status = "screened_source_needs_semantic_review"
        elif (
            not non_temporal and document["extraction_status"] == "extracted"
            and not document.get("publication_date") and observed
            and date.fromisoformat(observed).year == int(race["election_year"])
            and date.fromisoformat(observed) >= campaign_window_for_election(race["election_date"]).start
        ):
            status = "same_cycle_source_timing_unverified"
        else:
            status = "source_requires_recovery_or_scope_review"
        row = {
            "race_id": race_id, "candidate_name": names[0], "document_id": document["document_id"],
            "source_race_id": document["race_id"], "source_url": document.get("source_url", ""),
            "final_url": document.get("final_url", ""), "source_type": document.get("source_type", ""),
            "publication_date": document.get("publication_date", ""), "retrieved_at": document.get("retrieved_at", ""),
            "raw_path": document.get("raw_path", ""), "raw_sha256": document.get("raw_sha256", ""),
            "source_review_status": status, "source_issues": " | ".join(issues),
        }
        source_rows.append(row)
        by_candidate[(race_id, names[0])].append(row)
    evidence = defaultdict(list)
    for statement in statements:
        name = statement.get("canonical_speaker") or statement["speaker"]
        evidence[(statement["race_id"], name)].append(statement)
    candidate_rows = []
    case_rows = []
    for race_id, race in sorted(races.items()):
        endorsed = set((race["endorsed_candidates"] or race["endorsed_candidate"]).split(" | "))
        current = []
        for name in dict.fromkeys(race["all_candidates"].split(" | ")):
            sources = by_candidate[(race_id, name)]
            reviewed = evidence[(race_id, name)]
            entity_kind = participant_kind(race["office"], name, endorsed)
            if entity_kind == "non_person_ballot_option" and reviewed:
                raise ValueError("A ballot option has reviewed speech; explicitly resolve its campaign identity")
            row = {
                "race_id": race_id, "election_year": race["election_year"], "election_date": race["election_date"],
                "state_code": race["state_code"], "office": race["office"], "jurisdiction": race["jurisdiction"],
                "candidate_name": name, "role": "endorsed" if name in endorsed else "opponent",
                "entity_kind": entity_kind,
                "policy_evidence_required": entity_kind != "non_person_ballot_option",
                "reviewed_statements": len(reviewed),
                "reviewed_policy_positions": sum(s.get("representation_kind") == "policy_position" for s in reviewed),
                "reviewed_campaign_frames": sum(s.get("representation_kind") == "campaign_frame" for s in reviewed),
                "screened_sources": len({
                    s["raw_sha256"] for s in sources if s["source_review_status"] == "screened_source_needs_semantic_review"
                }),
                "timing_qualified_sources": len({
                    s["raw_sha256"] for s in sources if s["source_review_status"] == "same_cycle_source_timing_unverified"
                }),
                "sources_needing_recovery_or_scope_review": sum(
                    s["source_review_status"] == "source_requires_recovery_or_scope_review" for s in sources
                ),
                "coverage_status": (
                    "not_an_individual_platform_gap" if entity_kind == "non_person_ballot_option"
                    else "source_reviewed_excerpt_available" if reviewed else "no_reviewed_excerpt"
                ),
                "full_platform_completeness": "not_established",
                "source_urls": " | ".join(dict.fromkeys(s["source_url"] for s in sources)),
            }
            current.append(row)
            candidate_rows.append(row)
        grouped = {
            role: [row for row in current if row["role"] == role and row["policy_evidence_required"]]
            for role in ("endorsed", "opponent")
        }
        required = [row for row in current if row["policy_evidence_required"]]
        case_rows.append({
            "race_id": race_id, "election_year": race["election_year"], "election_date": race["election_date"],
            "state_code": race["state_code"], "office": race["office"], "jurisdiction": race["jurisdiction"],
            "candidate_count": len(current),
            "individual_candidate_count": sum(r["entity_kind"] == "individual_candidate" for r in current),
            "endorsed_ballot_campaign_count": sum(r["entity_kind"] == "endorsed_ballot_campaign" for r in current),
            "non_person_ballot_option_count": sum(r["entity_kind"] == "non_person_ballot_option" for r in current),
            "candidates_with_reviewed_statements": sum(row["reviewed_statements"] > 0 for row in current),
            "all_candidates_have_reviewed_statement": bool(required) and all(row["reviewed_statements"] > 0 for row in required),
            "both_groups_have_reviewed_statements": all(
                any(row["reviewed_statements"] > 0 for row in grouped[role]) for role in grouped
            ),
            "both_groups_have_sources_including_qualified": all(
                any(row["screened_sources"] or row["timing_qualified_sources"] for row in grouped[role]) for role in grouped
            ),
            "source_associations": sum(
                len(by_candidate[(race_id, row["candidate_name"])]) for row in current
            ),
            "presidential_case": is_presidential_office(race["office"]),
            "official_election_source_status": race["official_election_source_status"],
            "certified_opponents_status": race["certified_opponents_status"],
            "full_platform_completeness": "not_established",
        })
    return case_rows, candidate_rows, source_rows


def build_policy_inventory() -> dict:
    output = ANALYSIS_DATA_DIR / "policy_evidence"
    races = {
        row["race_id"]: row for row in read_csv(PROCESSED_DIR / "race_registry.csv")
        if row["scope_kind"] == "tracked_dsa_endorsed_democratic_primary"
    }
    statements = []
    for filename in ("reviewed_candidate_statements.csv", "timing_unverified_candidate_statements.csv"):
        path = output / filename
        if path.exists():
            statements.extend(read_csv(path))
    cases, candidates, sources = inventory_rows(
        races, read_csv(PROCESSED_DIR / "candidate_document_metadata.csv"),
        read_csv(MANUAL_DIR / "endorsements.csv"), statements,
    )
    classification = read_json(MANUAL_DIR / "policy_ballot_option_review.json")
    if (
        classification["review_method"] != REVIEW_METHOD
        or {name.casefold() for name in classification["reviewed_labels"]} != PRESIDENTIAL_BALLOT_OPTIONS
    ):
        raise ValueError("Ballot-option classification differs from its explicit source review")
    for evidence in classification["evidence"]:
        path = (ROOT / evidence["raw_path"]).resolve()
        if (
            not path.is_relative_to(ROOT.resolve())
            or hashlib.sha256(path.read_bytes()).hexdigest() != evidence["sha256"]
        ):
            raise ValueError("Ballot-option review source integrity failed")
    write_csv(output / "historical_race_inventory.csv", cases, list(cases[0]))
    write_csv(output / "historical_candidate_inventory.csv", candidates, list(candidates[0]))
    write_csv(output / "historical_source_inventory.csv", sources, list(sources[0]))
    options = [row for row in candidates if row["entity_kind"] != "individual_candidate"]
    write_csv(output / "non_individual_ballot_records.csv", options, list(candidates[0]))
    research_groups = defaultdict(list)
    for row in candidates:
        if not row["policy_evidence_required"]:
            continue
        key = (
            (row["election_year"], name_key(row["candidate_name"]))
            if is_presidential_office(row["office"])
            else (row["race_id"], row["candidate_name"])
        )
        research_groups[key].append(row)
    worklist = []
    for key, members in sorted(research_groups.items()):
        missing = [r for r in members if not r["reviewed_statements"]]
        if not missing:
            continue
        worklist.append({
            "research_group": " | ".join(key),
            "election_year": members[0]["election_year"],
            "candidate_names": " | ".join(sorted({r["candidate_name"] for r in members})),
            "entity_kind": members[0]["entity_kind"],
            "grouping_scope": (
                "same_cycle_national_campaign_research_only"
                if is_presidential_office(members[0]["office"]) else "one_registry_record"
            ),
            "records_without_direct_review": len(missing),
            "records_with_direct_review": len(members) - len(missing),
            "race_ids": " | ".join(sorted(r["race_id"] for r in members)),
            "meaning": "Acquisition work unit, not an independent observation or proof that a source applies to every listed primary.",
        })
    write_csv(output / "policy_research_worklist.csv", worklist, [
        "research_group", "election_year", "candidate_names", "entity_kind", "grouping_scope",
        "records_without_direct_review", "records_with_direct_review", "race_ids", "meaning",
    ])
    summary = {
        "in_scope_races": len(cases), "candidate_race_records": len(candidates),
        "cases_with_reviewed_statements": sum(row["candidates_with_reviewed_statements"] > 0 for row in cases),
        "cases_with_both_groups_reviewed": sum(row["both_groups_have_reviewed_statements"] for row in cases),
        "candidates_with_reviewed_statements": sum(row["reviewed_statements"] > 0 for row in candidates),
        "individual_candidate_race_records": sum(r["entity_kind"] == "individual_candidate" for r in candidates),
        "individual_candidate_records_with_reviewed_statements": sum(
            r["entity_kind"] == "individual_candidate" and r["reviewed_statements"] > 0 for r in candidates
        ),
        "endorsed_ballot_campaign_records": sum(r["entity_kind"] == "endorsed_ballot_campaign" for r in candidates),
        "non_person_ballot_option_records": sum(r["entity_kind"] == "non_person_ballot_option" for r in candidates),
        "policy_evidence_records_without_reviewed_statements": sum(
            r["policy_evidence_required"] and not r["reviewed_statements"] for r in candidates
        ),
        "acquisition_work_units_with_missing_direct_review": len(worklist),
        "cases_with_paired_cached_sources": sum(row["both_groups_have_sources_including_qualified"] for row in cases),
        "source_associations": len(sources),
        "unique_retained_raw_sources": len({row["raw_sha256"] for row in sources if row["raw_sha256"]}),
        "strict_congressional_registry_records": sum(bool(re.search(
            r"\b(?:U\.?S\.?|United States)\s+(?:House|Congress|Representative|Senat)",
            row["office"], re.I,
        )) for row in cases),
        "strict_congressional_records_with_reviewed_statements": sum(
            bool(re.search(r"\b(?:U\.?S\.?|United States)\s+(?:House|Congress|Representative|Senat)", row["office"], re.I))
            and row["candidates_with_reviewed_statements"] > 0 for row in cases
        ),
        "complete": False,
        "limitations": [
            "Cached source availability is not semantic review or complete platform coverage.",
            "Candidate/race records are not necessarily distinct people or distinct national campaigns.",
            "Shared presidential sources do not constitute independent state-specific policy observations.",
            "Missing reviewed statements do not establish that candidates lacked a policy.",
            "The legacy candidate_race_records count includes non-person ballot options and endorsed ballot campaigns; entity-specific denominators are separate.",
            "Generic Uncommitted/No Preference/Scattered results are not individual platform gaps. Endorsed ballot campaigns still require campaign evidence.",
            "Research work units group same-cycle presidential names using only the explicit reviewed alias map; they do not merge election records or create reviewed evidence.",
        ],
    }
    (output / "historical_inventory_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(build_policy_inventory(), indent=2))
