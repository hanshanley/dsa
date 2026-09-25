"""Reconcile the DSA research registry to source-first congressional returns."""

import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from .io import read_csv, write_csv
from .paths import PROCESSED_DIR
from .state_results import PRIMARY_RESULT_STAGES


def _name(value: str) -> str:
    value = re.sub(r"\s+for congress$", "", value, flags=re.I)
    value = unicodedata.normalize("NFKD", value)
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", value.encode("ascii", "ignore").decode().lower()).split())


def reconcile_dsa_congressional(output_dir: Path) -> dict[str, int]:
    registry = PROCESSED_DIR / "race_registry.csv"
    if not registry.exists():
        return {"dsa_congressional_rows_reconciled": 0}
    results = read_csv(output_dir / "state_primary_results.csv")
    index = defaultdict(list)
    for row in results:
        if row["stage"] in PRIMARY_RESULT_STAGES and str(row["write_in"]).lower() != "true":
            index[(row["cycle"], row["state_code"], row["chamber"], _name(row["candidate_name"]))].append(row)
    output = []
    for row in read_csv(registry):
        office = re.search(
            r"\b(?:U\.?S\.?|United States)\s+(House|Congress|Senat)",
            row["office"], re.I,
        )
        if not office:
            continue
        if row["election_year"] not in {"2024", "2026"}:
            continue
        candidates = [name for name in row["endorsed_candidates"].split(" | ") if name] or [
            row["endorsed_candidate"]
        ]
        chamber = "Senate" if office[1].lower() == "senat" else "House"
        matches = []
        unmatched = []
        for candidate in candidates:
            candidate_matches = index.get(
                (row["election_year"], row["state_code"], chamber, _name(candidate)), []
            )
            matches.extend(candidate_matches)
            if not candidate_matches:
                unmatched.append(candidate)
        matches = list({(match["source_id"], match["contest_id"], match["candidate_source_id"]): match for match in matches}.values())
        issues = []
        if not matches:
            issues.append("no_exact_name_match_in_recovered_returns")
        else:
            if unmatched:
                issues.append("some_endorsed_candidates_not_matched")
            dates = {match["election_date"] for match in matches}
            if row["election_date"] not in dates:
                issues.append("registry_election_date_differs")
            districts = {match["district"] for match in matches}
            district_match = re.search(
                r"\b(?:District\s+(\d+)|(\d+)(?:st|nd|rd|th)\s+Congressional)",
                row["jurisdiction"], re.I,
            )
            expected_district = (
                next(value for value in district_match.groups() if value).zfill(2)
                if district_match else ""
            )
            if expected_district and expected_district not in districts:
                issues.append("registry_district_differs")
            if len(districts) > 1:
                issues.append("multiple_source_districts_require_review")
        status = "matched_recovered_result" if matches and not issues else "review_required"
        output.append({
            "registry_race_id": row["race_id"],
            "cycle": row["election_year"], "state_code": row["state_code"],
            "registry_candidate": row["endorsed_candidate"],
            "registry_election_date": row["election_date"], "registry_office": row["office"],
            "registry_jurisdiction": row["jurisdiction"], "status": status,
            "unmatched_registry_candidates": " | ".join(unmatched),
            "matched_source_candidates": " | ".join(sorted({match["candidate_name"] for match in matches})),
            "matched_election_dates": " | ".join(sorted({match["election_date"] for match in matches})),
            "matched_districts": " | ".join(sorted({match["district"] for match in matches})),
            "matched_contest_ids": " | ".join(sorted({match["contest_id"] for match in matches})),
            "source_urls": " | ".join(sorted({match["source_url"] for match in matches})),
            "issues": " | ".join(issues),
            "notes": (
                "Exact normalized-name matching only. Missing match is not proof of no candidacy; "
                "aliases, incomplete sources, conventions and future contests require review. "
                "No registry or endorsement role is changed automatically."
            ),
        })
    fields = [
        "registry_race_id", "cycle", "state_code", "registry_candidate",
        "registry_election_date", "registry_office", "registry_jurisdiction", "status",
        "unmatched_registry_candidates",
        "matched_source_candidates", "matched_election_dates", "matched_districts",
        "matched_contest_ids", "source_urls", "issues", "notes",
    ]
    write_csv(output_dir / "dsa_registry_reconciliation.csv", output, fields)
    return {
        "dsa_congressional_rows_reconciled": len(output),
        "dsa_congressional_review_required": sum(row["status"] == "review_required" for row in output),
    }
