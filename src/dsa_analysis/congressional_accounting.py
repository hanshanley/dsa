"""Keep every expected district visible without inventing missing primary results."""

from collections import defaultdict
from datetime import date
from pathlib import Path

from .io import read_csv, read_json, write_csv
from .paths import CONFIG_DIR, MANUAL_DIR
from .state_results import PRIMARY_RESULT_STAGES

FIELDS = [
    "cycle", "election_date", "state_code", "chamber", "district", "term", "stage",
    "primary_party", "status", "candidate_names", "source_urls", "locators", "notes",
]
KEY_FIELDS = FIELDS[:8]
RESOLVED_STATUSES = {
    "results_complete", "unopposed_nomination_verified", "no_primary_verified",
    "no_candidate_verified",
}
STATUSES = RESOLVED_STATUSES | {
    "results_partial", "unresolved", "not_scheduled", "future_scheduled",
    "source_records_present", "conflicting_evidence", "superseded",
}


def canonical_party(value: str) -> str:
    raw = value.strip()
    normalized = raw.casefold().replace(" ", "").replace("-", "")
    if normalized in {
        "d", "dem", "democratic", "democrat", "democraticparty", "democraticfarmerlabor",
        "dfl", "democraticnpl", "democraticfarmerlaborparty",
    }:
        return "Democratic"
    if normalized in {"r", "rep", "republican", "republicanparty", "gop"}:
        return "Republican"
    if normalized in {"l", "lib", "libertarian", "libertarianparty"}:
        return "Libertarian"
    return raw


def _normalize(row: dict) -> dict[str, str]:
    output = {field: str(row.get(field, "")).strip() for field in FIELDS}
    output["primary_party"] = canonical_party(output["primary_party"])
    if output["chamber"] == "Senate":
        output["district"] = "S"
    elif output["district"].isdigit():
        output["district"] = output["district"].zfill(2)
    output["term"] = output["term"] or "regular"
    output["stage"] = output["stage"] or "primary"
    if output["status"] not in STATUSES:
        raise ValueError(f"Unknown congressional accounting status: {output['status']!r}")
    if output["status"] in RESOLVED_STATUSES and (
        not output["source_urls"] or not output["locators"]
    ):
        raise ValueError("Resolved nomination/primary accounting requires source and locator")
    if output["status"] == "unopposed_nomination_verified" and not output["candidate_names"]:
        raise ValueError("Verified unopposed nomination requires the nominee's name")
    if output["election_date"]:
        date.fromisoformat(output["election_date"])
    return output


def reconcile_party_contests(
    inventory: list[dict], results: list[dict], reviews: list[dict], *, cutoff: str,
) -> tuple[list[dict], list[dict]]:
    groups = defaultdict(list)
    row_numbers = {id(row): index for index, row in enumerate(results, 2)}
    for row in results:
        if row["stage"] not in PRIMARY_RESULT_STAGES:
            continue
        date.fromisoformat(row["election_date"])
        if row["election_date"] > cutoff:
            raise ValueError("Future primary results cannot enter the as-of dataset")
        key = (
            str(row["cycle"]), row["election_date"], row["state_code"], row["chamber"],
            row["district"], row["term"], row["stage"], canonical_party(row["primary_party"]),
        )
        groups[key].append(row)
    accounting = {}
    for key, rows in groups.items():
        accounting[key] = {
            **dict(zip(KEY_FIELDS, key, strict=True)),
            "status": "results_complete",
            "candidate_names": " | ".join(sorted({row["candidate_name"] for row in rows})),
            "source_urls": " | ".join(sorted({row["source_url"] for row in rows})),
            "locators": "state_primary_results.csv rows "
            + ",".join(str(row_numbers[id(row)]) for row in rows),
            "notes": "Complete reported ballot options in the source; this does not certify "
                     "the existence of every nomination method or every minor party.",
        }
    evidence = defaultdict(list)
    scheduled_senate = {
        (str(row["cycle"]), row["state_code"])
        for row in inventory if row["chamber"] == "Senate"
    }
    for row in reviews:
        normalized = _normalize(row)
        if (
            normalized["status"] == "not_scheduled" and normalized["chamber"] == "Senate"
            and (normalized["cycle"], normalized["state_code"]) in scheduled_senate
        ):
            raise ValueError("Not-scheduled Senate claim contradicts the independent class inventory")
        if normalized["election_date"] > cutoff and normalized["status"] == "results_complete":
            raise ValueError("Completed election results cannot postdate the cutoff")
        evidence[tuple(normalized[field] for field in KEY_FIELDS)].append(normalized)
    for key, rows in evidence.items():
        prior = accounting.get(key)
        resolved = [row for row in rows if row["status"] in RESOLVED_STATUSES]
        statuses = {row["status"] for row in resolved}
        if prior:
            statuses.add(prior["status"])
        if len(statuses) > 1:
            all_rows = ([prior] if prior else []) + rows
            accounting[key] = {
                **rows[0], "status": "conflicting_evidence",
                "source_urls": " | ".join(sorted({row["source_urls"] for row in all_rows})),
                "notes": "Conflicting source resolutions: " + " | ".join(sorted(statuses)),
            }
        elif resolved:
            chosen = resolved[-1]
            accounting[key] = prior or chosen
        elif any(row["status"] == "results_partial" for row in rows):
            accounting[key] = next(row for row in reversed(rows) if row["status"] == "results_partial")
        elif prior is None:
            accounting[key] = rows[-1]

    by_seat = defaultdict(list)
    for row in accounting.values():
        if row["term"] == "regular" and row["status"] != "not_scheduled":
            by_seat[(row["cycle"], row["state_code"], row["chamber"], row["district"])].append(row)

    seat_status = []
    for seat in inventory:
        cycle = str(seat["cycle"])
        seat_key = (cycle, seat["state_code"], seat["chamber"], seat["district"])
        rows = by_seat.get(seat_key, [])
        nonpartisan = seat["state_code"] in {"CA", "WA", "AS", "MP"} or (
            seat["state_code"] == "AK" and int(cycle) >= 2022
        ) or (
            seat["state_code"] == "LA" and (seat["chamber"] == "House" or int(cycle) < 2026)
        )
        unknown_party_universe = seat["state_code"] == "PR"
        expected = {""} if nonpartisan or unknown_party_universe else {"Democratic", "Republican"}
        blank_category = "all-party" if nonpartisan else "unspecified-party"
        present = {row["primary_party"] for row in rows}
        for party in sorted(expected - present):
            status = "source_records_present" if int(cycle) <= 2022 and seat["source_rows"] else "unresolved"
            missing = {
                "cycle": cycle, "election_date": "", "state_code": seat["state_code"],
                "chamber": seat["chamber"], "district": seat["district"], "term": "regular",
                "stage": "primary", "primary_party": party, "status": status,
                "candidate_names": "", "source_urls": "", "locators": "",
                "notes": (
                    "Puerto Rico's local-party primary universe requires official reconciliation; "
                    "U.S. Democratic/Republican ballot categories are not assumed."
                    if unknown_party_universe else
                    "FEC result rows are preserved, but election-specific date/party-roster "
                    "reconciliation is not yet certified."
                    if status == "source_records_present" else
                    "No complete primary or explicit official no-primary/nomination resolution "
                    "has been recovered. Absence is not evidence that no contest occurred."
                ),
            }
            accounting[tuple(missing[field] for field in KEY_FIELDS)] = missing
            rows.append(missing)
        unknown = []
        scheduled = []
        for party in sorted(expected | present):
            party_rows = [row for row in rows if row["primary_party"] == party]
            if any(row["status"] == "conflicting_evidence" for row in party_rows):
                unknown.append(party or blank_category)
            elif any(row["status"] in RESOLVED_STATUSES for row in party_rows):
                continue
            elif any(
                row["status"] == "future_scheduled" and row["election_date"] > cutoff
                for row in party_rows
            ):
                scheduled.append(party or blank_category)
            else:
                unknown.append(party or blank_category)
        seat_status.append({
            "cycle": cycle, "state_code": seat["state_code"], "chamber": seat["chamber"],
            "district": seat["district"],
            "regular_primary_status": (
                "unresolved" if unknown else "future_scheduled" if scheduled else
                "tracked_party_contests_resolved"
            ),
            "unresolved_ballot_categories": " | ".join(unknown),
            "future_ballot_categories": " | ".join(scheduled),
            "minor_party_universe_status": "requires_state_election_specific_review",
            "special_election_status": "tracked_separately_not_implied_by_regular_seat",
        })
    return sorted(accounting.values(), key=lambda row: tuple(row[key] for key in KEY_FIELDS)), seat_status


def export_party_accounting(output_dir: Path, inventory: list[dict], results: list[dict]) -> dict:
    config = read_json(CONFIG_DIR / "congressional_state_sources.json")
    cutoff = read_json(CONFIG_DIR / "sources.json")["research_cutoff"]
    reviews = []
    for filename in config.get("party_accounting_files", []):
        reviews.extend(read_csv(output_dir / filename))
    manual = MANUAL_DIR / "congressional_nomination_resolutions.csv"
    if manual.exists():
        reviews.extend(read_csv(manual))
    rows, seats = reconcile_party_contests(inventory, results, reviews, cutoff=cutoff)
    write_csv(output_dir / "party_contest_accounting.csv", rows, FIELDS)
    write_csv(output_dir / "district_primary_accounting.csv", seats, [
        "cycle", "state_code", "chamber", "district", "regular_primary_status",
        "unresolved_ballot_categories", "future_ballot_categories",
        "minor_party_universe_status", "special_election_status",
    ])
    return {
        "party_accounting_rows": len(rows),
        "tracked_party_resolved_seat_cycles": sum(
            row["regular_primary_status"] == "tracked_party_contests_resolved" for row in seats
        ),
        "unresolved_primary_seat_cycles": sum(
            row["regular_primary_status"] == "unresolved" for row in seats
        ),
        "future_primary_seat_cycles": sum(row["regular_primary_status"] == "future_scheduled" for row in seats),
    }
