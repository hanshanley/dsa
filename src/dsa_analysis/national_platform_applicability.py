"""Link reviewed national platforms to relevant primary fields without inventing state-specific evidence."""

import json
import re
from datetime import date

from .document_corpus import campaign_window_for_election, candidate_slug
from .io import read_csv, write_csv
from .paths import ANALYSIS_DATA_DIR, PROCESSED_DIR

NAME_ALIASES = {
    "joe-biden": "joseph-r-biden",
    "joseph-r-biden-jr": "joseph-r-biden",
    "joseph-biden": "joseph-r-biden",
    "hillary-r-clinton": "hillary-clinton",
    "hillary-rodham-clinton": "hillary-clinton",
    "martin-omalley": "martin-j-omalley",
    "john-delaney": "john-k-delaney",
    "elizabeth-ann-warren": "elizabeth-warren",
    "elizabeth-a-warren": "elizabeth-warren",
}


def name_key(name: str) -> str:
    key = candidate_slug(name)
    return NAME_ALIASES.get(key, key)


def is_presidential_office(office: str) -> bool:
    return re.sub(r"[^a-z]", "", office.casefold()) in {
        "president", "uspresident", "unitedstatespresident",
        "presidentoftheunitedstates", "democraticpresidentialprimary",
    }


def applicable_rows(races: dict, statements: list[dict], comparisons: list[dict]) -> list[dict]:
    source_statements = {row["excerpt_id"]: row for row in statements}
    national = [
        row for row in comparisons
        if row.get("timing_status") == "pre_primary_verified"
        and is_presidential_office(races[row["race_id"]]["office"])
        and all(
            source_statements.get(row[f"{side}_excerpt_id"], {}).get("source_type")
            == "official_campaign_platform" for side in ("candidate", "opponent")
        )
    ]
    output = []
    for race in races.values():
        if not is_presidential_office(race["office"]) or race["scope_kind"] != "tracked_dsa_endorsed_democratic_primary":
            continue
        endorsed = {
            name_key(name): name for name in (race["endorsed_candidates"] or race["endorsed_candidate"]).split(" | ")
        }
        opponents = {name_key(name): name for name in race["opponent_candidates"].split(" | ") if name}
        for comparison in national:
            if comparison["election_date"][:4] != race["election_year"]:
                continue
            left, right = name_key(comparison["candidate_name"]), name_key(comparison["opponent_name"])
            if left not in endorsed or right not in opponents or right in endorsed:
                continue
            evidence = [
                source_statements[comparison[f"{side}_excerpt_id"]] for side in ("candidate", "opponent")
            ]
            dates = [
                row.get("temporal_evidence_date") or row.get("publication_date")
                or row.get("capture_date") or row.get("available_by_date")
                for row in evidence
            ]
            window = campaign_window_for_election(race["election_date"])
            if not all(value and window.contains(date.fromisoformat(value)) for value in dates):
                continue
            output.append({
                "race_id": race["race_id"], "election_date": race["election_date"],
                "state_code": race["state_code"], "jurisdiction": race["jurisdiction"],
                "candidate_name": endorsed[left], "opponent_name": opponents[right],
                "source_comparison_id": comparison["comparison_id"],
                "source_review_race_id": comparison["race_id"], "topic": comparison["topic"],
                "relationship": comparison["relationship"], "analysis": comparison["analysis"],
                "candidate_source_url": comparison["candidate_source_url"],
                "opponent_source_url": comparison["opponent_source_url"],
                "evidence_scope": "same_cycle_national_platforms_not_state_specific_campaigning",
                "new_independent_evidence": "false",
                "candidate_activity_at_primary": "withdrawal_or_active_campaign_status_not_inferred",
            })
    return output


def export_national_platform_applicability() -> dict:
    output = ANALYSIS_DATA_DIR / "policy_evidence"
    races = {r["race_id"]: r for r in read_csv(PROCESSED_DIR / "race_registry.csv")}
    statements = read_csv(output / "reviewed_candidate_statements.csv")
    comparisons = read_csv(output / "reviewed_candidate_comparisons.csv")
    rows = applicable_rows(races, statements, comparisons)
    write_csv(
        output / "national_platform_applicability.csv", rows,
        list(rows[0]) if rows else ["race_id", "source_comparison_id", "evidence_scope"],
    )
    summary = {
        "primary_records_with_applicable_national_comparisons": len({r["race_id"] for r in rows}),
        "applicability_rows": len(rows),
        "distinct_underlying_comparisons": len({r["source_comparison_id"] for r in rows}),
        "new_independent_policy_evidence": 0,
        "not_added_to_reviewed_case_or_comparison_counts": True,
    }
    (output / "national_platform_applicability_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    print(json.dumps(export_national_platform_applicability(), indent=2))
