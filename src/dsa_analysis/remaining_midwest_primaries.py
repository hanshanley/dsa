"""Parse recovered Indiana and Minnesota results and account for blocked sources."""

import argparse
import csv
import hashlib
from collections import defaultdict
from pathlib import Path

from .io import write_csv
from .paths import ANALYSIS_DATA_DIR, RAW_DIR
from .state_results import FIELDS

RAW_SUBDIR = "remaining_midwest_primaries"
RESULT_FILENAME = "remaining_midwest_primary_results.csv"

ACCOUNTING_FIELDS = [
    "cycle", "state_code", "chamber", "district", "term", "primary_party",
    "status", "candidate_rows", "source_ids", "notes",
]

PARTY_CONTEST_FIELDS = [
    "cycle", "election_date", "state_code", "chamber", "district", "term",
    "stage", "primary_party", "status", "candidate_names", "source_urls",
    "locators", "notes",
]

RAW_ARTIFACT_FIELDS = [
    "provider", "path", "sha256", "bytes", "artifact_type",
]

ELECTION_DATES = {
    ("CT", "2024"): "2024-08-13",
    ("CT", "2026"): "2026-08-11",
    ("IL", "2024"): "2024-03-19",
    ("IL", "2026"): "2026-03-17",
    ("IN", "2024"): "2024-05-07",
    ("IN", "2026"): "2026-05-05",
    ("MA", "2024"): "2024-09-03",
    ("MA", "2026"): "2026-09-01",
    ("MD", "2024"): "2024-05-14",
    ("MD", "2026"): "2026-06-23",
    ("MI", "2024"): "2024-08-06",
    ("MI", "2026"): "2026-08-04",
    ("MN", "2024"): "2024-08-13",
    ("MN", "2026"): "2026-08-11",
    ("MO", "2026"): "2026-08-04",
    ("NY", "2024"): "2024-06-25",
    ("NY", "2026"): "2026-06-23",
    ("OH", "2024"): "2024-03-19",
    ("OH", "2026"): "2026-05-05",
}

STATUS_MAP = {
    "complete_certified_results": "results_complete",
    "complete_official_results": "results_complete",
    "complete_unopposed_result": "results_complete",
    "partial_official_uncertified": "results_partial",
    "official_100pct_uncertified_not_emitted": "results_partial",
    "official_uncontested_roster": "unopposed_nomination_verified",
    "official_no_candidates": "no_candidate_verified",
    "no_reported_contest_not_inferred": "unresolved",
    "blocked_certified_workbook_unretrieved": "unresolved",
    "blocked_certified_canvass_unrecovered": "unresolved",
    "blocked_certified_source_unrecovered": "unresolved",
    "not_scheduled_this_cycle": "not_scheduled",
}

STATUS_PRIORITY = {
    "results_complete": 7,
    "results_partial": 6,
    "unopposed_nomination_verified": 5,
    "no_primary_verified": 4,
    "no_candidate_verified": 3,
    "unresolved": 2,
    "not_scheduled": 1,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _votes(value: object) -> int:
    text = str(value or "").strip().replace(",", "")
    if not text or not text.isdigit():
        raise ValueError(f"Invalid vote total: {value!r}")
    return int(text)


def parse_indiana_2024(path: Path) -> list[dict]:
    output = []
    source_hash = _sha256(path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for number, row in enumerate(csv.DictReader(handle), 2):
            if row["Office"] not in {"US Representative", "US Senator"}:
                continue
            chamber = "Senate" if row["Office"] == "US Senator" else "House"
            district = "S" if chamber == "Senate" else row["District"].zfill(2)
            party = row["Party"].strip()
            name = row["Candidate"].strip()
            write_in = "write-in" in name.casefold()
            output.append({
                "contest_id": (
                    f"in-2024-05-07-{chamber.lower()}-{district.lower()}-regular-"
                    f"{party.lower()}"
                ),
                "cycle": "2024",
                "election_date": "2024-05-07",
                "stage": "primary",
                "state_code": "IN",
                "chamber": chamber,
                "district": district,
                "term": "regular",
                "election_system": "partisan_primary",
                "primary_party": party,
                "candidate_name": name,
                "candidate_source_id": f"in-2024-{number}",
                "party": "" if write_in else party,
                "write_in": write_in,
                "votes": _votes(row["Votes"]),
                "source_id": "in-2024-primary",
                "source_url": (
                    "https://indianavoters.in.gov/ENRHistorical/"
                    "ExportElectionsToCSV?year=2024&electionType=PRIMARY"
                ),
                "source_sha256": source_hash,
                "source_locators": f"{path.name}:{number}",
                "reporting_units": 1,
            })
    if {row["district"] for row in output if row["chamber"] == "House"} != {
        f"{value:02}" for value in range(1, 10)
    }:
        raise ValueError("Indiana 2024 House district coverage is incomplete")
    if not any(row["chamber"] == "Senate" for row in output):
        raise ValueError("Indiana 2024 Senate primary is missing")
    return output


def parse_minnesota_senate(path: Path) -> list[dict]:
    output = []
    source_hash = _sha256(path)
    with path.open(newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), 2):
            write_in = "write-in" in row["candidate_name"].casefold()
            party = row["primary_party"]
            output.append({
                "contest_id": (
                    f"mn-{row['election_date']}-senate-s-regular-"
                    f"{party.lower().replace(' ', '-')}"
                ),
                "cycle": row["cycle"],
                "election_date": row["election_date"],
                "stage": "primary",
                "state_code": "MN",
                "chamber": "Senate",
                "district": "S",
                "term": "regular",
                "election_system": "partisan_primary",
                "primary_party": party,
                "candidate_name": row["candidate_name"],
                "candidate_source_id": f"mn-{row['cycle']}-senate-{number}",
                "party": "" if write_in else party,
                "write_in": write_in,
                "votes": _votes(row["votes"]),
                "source_id": f"mn-{row['cycle']}-primary-senate-summary",
                "source_url": row["source_url"],
                "source_sha256": source_hash,
                "source_locators": row["source_locator"],
                "reporting_units": 1,
            })
    return output


def _canonical_status(status: str) -> str:
    try:
        return STATUS_MAP[status]
    except KeyError as error:
        raise ValueError(f"Unknown provider accounting status: {status}") from error


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _source_urls(analysis_dir: Path) -> dict[str, str]:
    output = {}
    manifests = (
        analysis_dir / "ny_mi" / "source_manifest.csv",
        analysis_dir / "il_oh" / "source_manifest.csv",
        analysis_dir / "northeast" / "source_manifest.csv",
        analysis_dir / "remaining_midwest" / "source_manifest.csv",
    )
    for path in manifests:
        for row in _read_rows(path):
            source_id = row.get("source_id", "")
            source_url = row.get("source_url", "")
            if source_id and source_url:
                output[source_id] = source_url
    return output


def _fallback_source_url(state: str, cycle: str) -> str:
    return {
        ("CT", "2024"): "https://ct.elstats.civera.com/api/download_search.csv",
        ("CT", "2026"): "https://ct.elstats.civera.com/api/download_search.csv",
        ("IL", "2024"): (
            "https://www.elections.il.gov/electionoperations/ElectionVoteTotals.aspx"
        ),
        ("IL", "2026"): (
            "https://www.elections.il.gov/electionoperations/ElectionVoteTotals.aspx"
        ),
        ("IN", "2024"): (
            "https://indianavoters.in.gov/ENRHistorical/ExportElectionsToCSV"
        ),
        ("IN", "2026"): "https://indianavoters.in.gov/ENRHistorical/ElectionResults",
        ("MA", "2024"): (
            "https://electionstats.state.ma.us/elections/search/date:2024-09-03"
        ),
        ("MA", "2026"): (
            "https://electionstats.state.ma.us/elections/search/date:2026-09-01"
        ),
        ("MD", "2024"): (
            "https://elections.maryland.gov/elections/archive/2024/election_data/"
        ),
        ("MD", "2026"): (
            "https://elections.maryland.gov/elections/2026/election_data/"
        ),
        ("MI", "2024"): "https://mvic.sos.state.mi.us/votehistory/",
        ("MI", "2026"): "https://mvic.sos.state.mi.us/votehistory/",
        ("MN", "2024"): "https://electionresults.sos.mn.gov/20240813",
        ("MN", "2026"): "https://electionresults.sos.mn.gov/20260811",
        ("MO", "2026"): "https://www.sos.mo.gov/elections/s_default.asp?id=results",
        ("NY", "2024"): "https://results.elections.ny.gov/",
        ("NY", "2026"): "https://nyenr.elections.ny.gov/HomeNoJS.aspx",
        ("OH", "2024"): "https://data.ohiosos.gov/portal/past-election-results",
        ("OH", "2026"): "https://data.ohiosos.gov/portal/past-election-results",
    }.get((state, cycle), "")


def _contest_key(row: dict[str, str]) -> tuple[str, ...]:
    district = row["district"]
    if row["chamber"] == "House":
        district = district.zfill(2)
    elif row["chamber"] == "Senate":
        district = "S"
    return (
        row["cycle"],
        row["election_date"],
        row["state_code"],
        row["chamber"],
        district,
        row["term"],
        row["stage"],
        row["primary_party"],
    )


def export_party_contest_accounting(
    analysis_dir: Path,
    output_path: Path,
) -> list[dict]:
    canonical: dict[tuple[str, ...], dict[str, str]] = {}
    result_files = (
        analysis_dir / "ny_mi_primary_results.csv",
        analysis_dir / "il_oh_primary_results.csv",
        analysis_dir / "northeast_primary_results.csv",
        analysis_dir / "remaining_midwest_primary_results.csv",
    )
    for path in result_files:
        groups = defaultdict(list)
        for row in _read_rows(path):
            groups[_contest_key(row)].append(row)
        for key, rows in groups.items():
            candidate_names = " | ".join(
                sorted({row["candidate_name"] for row in rows})
            )
            source_urls = " | ".join(
                sorted({row["source_url"] for row in rows if row["source_url"]})
            )
            locators = " | ".join(
                f"{row['candidate_name']} [{row['source_locators']}]"
                for row in rows
            )
            canonical[key] = dict(zip(PARTY_CONTEST_FIELDS[:8], key, strict=True)) | {
                "status": "results_complete",
                "candidate_names": candidate_names,
                "source_urls": source_urls,
                "locators": locators,
                "notes": (
                    "Official reported primary vote totals. A single numeric candidate "
                    "row remains results_complete and is not treated as proof of an "
                    "unopposed nomination."
                ),
            }

    partial_path = analysis_dir / "ny_mi" / "ny_mi_primary_partial_results.csv"
    partial_groups = defaultdict(list)
    for row in _read_rows(partial_path):
        partial_groups[_contest_key(row)].append(row)
    for key, rows in partial_groups.items():
        if key in canonical:
            continue
        canonical[key] = dict(zip(PARTY_CONTEST_FIELDS[:8], key, strict=True)) | {
            "status": "results_partial",
            "candidate_names": " | ".join(
                sorted({row["candidate_name"] for row in rows})
            ),
            "source_urls": " | ".join(
                sorted({row["source_url"] for row in rows if row["source_url"]})
            ),
            "locators": " | ".join(
                f"{row['candidate_name']} [{row['source_locators']}]"
                for row in rows
            ),
            "notes": "Official-hosted partial or uncertified reporting; not merged into results.",
        }

    roster_names = defaultdict(set)
    roster_urls = defaultdict(set)
    roster_locators = defaultdict(set)
    for row in _read_rows(analysis_dir / "ny_mi_primary_rosters.csv"):
        key = (
            row["cycle"], row["state_code"], row["chamber"],
            "S" if row["chamber"] == "Senate" else row["district"].zfill(2),
            row["primary_party"],
        )
        roster_names[key].add(row["candidate_name"])
        if row["source_url"]:
            roster_urls[key].add(row["source_url"])
        if row["source_locators"]:
            roster_locators[key].add(row["source_locators"])

    source_map = _source_urls(analysis_dir)
    accounting_files = (
        analysis_dir / "ny_mi" / "contest_accounting.csv",
        analysis_dir / "il_oh" / "contest_accounting.csv",
        analysis_dir / "northeast" / "contest_accounting.csv",
        analysis_dir / "remaining_midwest" / "contest_accounting.csv",
    )
    for path in accounting_files:
        for row in _read_rows(path):
            status = _canonical_status(row["status"])
            cycle = row["cycle"]
            state = row["state_code"]
            chamber = row["chamber"]
            district = row["district"]
            if chamber == "House":
                district = district.zfill(2)
            elif chamber == "Senate":
                district = "S"
            primary_party = row["primary_party"]
            if (
                state == "MN"
                and cycle == "2024"
                and chamber == "House"
                and district == "03"
                and status == "results_partial"
            ):
                status = "unresolved"
            key = (
                cycle,
                ELECTION_DATES[(state, cycle)],
                state,
                chamber,
                district,
                row.get("term", "regular") or "regular",
                "primary",
                primary_party,
            )
            if key in canonical and STATUS_PRIORITY[canonical[key]["status"]] >= (
                STATUS_PRIORITY[status]
            ):
                continue
            source_ids = [
                value.strip()
                for value in row.get("source_ids", "").split("|")
                if value.strip()
            ]
            urls = [source_map[value] for value in source_ids if value in source_map]
            names = ""
            explicit_key = (cycle, state, chamber, district, primary_party)
            if status == "unopposed_nomination_verified":
                names = " | ".join(sorted(roster_names.get(explicit_key, set())))
                urls.extend(roster_urls.get(explicit_key, set()))
            canonical[key] = dict(zip(PARTY_CONTEST_FIELDS[:8], key, strict=True)) | {
                "status": status,
                "candidate_names": names,
                "source_urls": " | ".join(sorted(set(urls))) or (
                    _fallback_source_url(state, cycle)
                ),
                "locators": (
                    " | ".join(sorted(roster_locators.get(explicit_key, set())))
                    if status == "unopposed_nomination_verified"
                    else (
                        "Official result row explicitly labeled No Candidates"
                        if status == "no_candidate_verified"
                        else ""
                    )
                ),
                "notes": (
                    "No federal primary contest appears for this district-party on the "
                    "official all-district page; absence is not interpreted as no primary."
                    if (
                        state == "MN"
                        and cycle == "2024"
                        and chamber == "House"
                        and district == "03"
                    )
                    else row.get("notes", "")
                ),
            }

    rows = sorted(canonical.values(), key=lambda row: (
        row["cycle"], row["state_code"], row["chamber"], row["district"],
        row["term"], row["primary_party"], row["status"],
    ))
    write_csv(output_path, rows, PARTY_CONTEST_FIELDS)
    return rows


def export_provider_raw_artifacts(
    raw_root: Path,
    analysis_dir: Path,
    output_path: Path,
) -> list[dict]:
    manifest_sources = (
        ("ny_mi_primaries", analysis_dir / "ny_mi" / "source_manifest.csv"),
        ("il_oh_primaries", analysis_dir / "il_oh" / "source_manifest.csv"),
        ("northeast_primaries", analysis_dir / "northeast" / "source_manifest.csv"),
        (
            "remaining_midwest_primaries",
            analysis_dir / "remaining_midwest" / "source_manifest.csv",
        ),
        ("nh_ct_nominations", analysis_dir / "nh_ct" / "source_manifest.csv"),
        ("wv_primaries", analysis_dir / "wv" / "source_manifest.csv"),
    )
    excluded_name_tokens = (
        "blocked", "captcha", "headers", "cookies",
    )
    blocked_markers = (
        b"<title>radware captcha page</title>",
        b"<title>just a moment...</title>",
        b"<title>access denied</title>",
        b"ohio secretary of state's office website maintenance",
        b"please solve this captcha",
    )
    candidates: set[tuple[str, Path]] = set()
    for provider, manifest_path in manifest_sources:
        for row in _read_rows(manifest_path):
            raw_filename = row.get("raw_filename", "").strip()
            if not raw_filename or "{" in raw_filename or " | " in raw_filename:
                continue
            path = raw_root / provider / raw_filename
            if path.is_file():
                candidates.add((provider, path))
    for path in (raw_root / "il_oh_primaries" / "illinois" / "candidate_details").glob(
        "*.html"
    ):
        candidates.add(("il_oh_primaries", path))
    for name in (
        "ny-2024-primary-certification-congressional.csv",
        "ny-2026-primary-certification-congressional.csv",
        "counties/dutchess-2026-cd17-certified.csv",
    ):
        path = raw_root / "ny_mi_primaries" / name
        if path.is_file():
            candidates.add(("ny_mi_primaries", path))
    for county in ("putnam", "rockland", "westchester"):
        for kind in ("metadata", "data"):
            path = (
                raw_root / "ny_mi_primaries" / "counties" / "enhanced"
                / f"{county}-county-ny-PE26-{kind}.json"
            )
            if path.is_file():
                candidates.add(("ny_mi_primaries", path))
    for path in (raw_root / "nh_ct_nominations" / "connecticut").glob("*.pdf"):
        candidates.add(("nh_ct_nominations", path))

    rows = []
    for provider, path in sorted(candidates, key=lambda item: str(item[1])):
            lower_name = path.name.casefold()
            if (
                any(token in lower_name for token in excluded_name_tokens)
                or path.suffix.casefold() == ".js"
            ):
                continue
            if path.suffix.casefold() in {".html", ".htm", ".txt", ".xml"}:
                prefix = path.read_bytes()[:131072].lower()
                if any(marker in prefix for marker in blocked_markers):
                    continue
            rows.append({
                "provider": provider,
                "path": str(path.relative_to(raw_root.parent.parent)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
                "artifact_type": path.suffix.casefold().lstrip(".") or "binary",
            })
    write_csv(output_path, rows, RAW_ARTIFACT_FIELDS)
    return rows


def _accounting(results: list[dict]) -> list[dict]:
    rows = []
    groups = defaultdict(list)
    for row in results:
        groups[row["contest_id"]].append(row)
    for group in groups.values():
        first = group[0]
        rows.append({
            "cycle": first["cycle"], "state_code": first["state_code"],
            "chamber": first["chamber"], "district": first["district"],
            "term": first["term"], "primary_party": first["primary_party"],
            "status": (
                "complete_unopposed_result" if len(group) == 1
                else "complete_official_results"
            ),
            "candidate_rows": len(group), "source_ids": first["source_id"],
            "notes": "",
        })
    observed = {
        (row["cycle"], row["state_code"], row["chamber"], row["district"], row["primary_party"])
        for row in rows
    }
    for district in range(1, 10):
        for party in ("Democratic", "Republican"):
            key = ("2024", "IN", "House", f"{district:02}", party)
            if key not in observed:
                rows.append({
                    "cycle": "2024", "state_code": "IN", "chamber": "House",
                    "district": f"{district:02}", "term": "regular",
                    "primary_party": party,
                    "status": "no_reported_contest_not_inferred",
                    "candidate_rows": 0, "source_ids": "in-2024-primary",
                    "notes": "No row in the complete statewide primary export.",
                })
    for district in range(1, 9):
        for cycle in ("2024", "2026"):
            for party in ("Democratic-Farmer-Labor", "Republican"):
                rows.append({
                    "cycle": cycle, "state_code": "MN", "chamber": "House",
                    "district": f"{district:02}", "term": "regular",
                    "primary_party": party,
                    "status": "official_100pct_uncertified_not_emitted",
                    "candidate_rows": "",
                    "source_ids": f"mn-{cycle}-electionresults",
                    "notes": (
                        "Authority-hosted page reported 100%, but labels results unofficial. "
                        "Certified canvass report data was not recoverable without CAPTCHA."
                    ),
                })
    for district in range(1, 10):
        for party in ("Democratic", "Republican"):
            rows.append({
                "cycle": "2026", "state_code": "IN", "chamber": "House",
                "district": f"{district:02}", "term": "regular",
                "primary_party": party,
                "status": "blocked_certified_canvass_unrecovered",
                "candidate_rows": "", "source_ids": "in-2026-primary",
                "notes": "Current results are not yet exposed by the historical export API.",
            })
    for state, districts, parties in (
        ("MO", 8, ("Democratic", "Republican")),
        ("OH", 15, ("Democratic", "Libertarian", "Republican")),
    ):
        for district in range(1, districts + 1):
            for party in parties:
                rows.append({
                    "cycle": "2026", "state_code": state, "chamber": "House",
                    "district": f"{district:02}", "term": "regular",
                    "primary_party": party,
                    "status": "blocked_certified_source_unrecovered",
                    "candidate_rows": 0,
                    "source_ids": f"{state.lower()}-2026-official-index",
                    "notes": "No absence or no-primary status is inferred.",
                })
    for party in ("Democratic", "Libertarian", "Republican"):
        rows.append({
            "cycle": "2026", "state_code": "OH", "chamber": "Senate",
            "district": "S", "term": "special", "primary_party": party,
            "status": "blocked_certified_source_unrecovered",
            "candidate_rows": 0, "source_ids": "oh-2026-official-index",
            "notes": "Special U.S. Senate term ending January 3, 2029.",
        })
    for state in ("IN", "MO"):
        rows.append({
            "cycle": "2026", "state_code": state, "chamber": "Senate",
            "district": "S", "term": "regular", "primary_party": "",
            "status": "not_scheduled_this_cycle", "candidate_rows": 0,
            "source_ids": f"{state.lower()}-2026-election-calendar",
            "notes": "No U.S. Senate seat was scheduled for election in this state in 2026.",
        })
    return sorted(rows, key=lambda row: (
        row["cycle"], row["state_code"], row["chamber"], row["district"],
        row["primary_party"], row["status"],
    ))


def collect_remaining_midwest(
    raw_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict:
    raw_dir = raw_dir or RAW_DIR / RAW_SUBDIR
    output_dir = output_dir or ANALYSIS_DATA_DIR / "congressional"
    ledger = output_dir / "remaining_midwest"
    ledger.mkdir(parents=True, exist_ok=True)
    results = parse_indiana_2024(raw_dir / "indiana/in-2024-primary.csv")
    results.extend(
        parse_minnesota_senate(
            raw_dir / "minnesota/mn-senate-certified-summary.csv",
        )
    )
    results.sort(key=lambda row: (
        row["cycle"], row["state_code"], row["chamber"], row["district"],
        row["primary_party"], row["candidate_name"],
    ))
    write_csv(output_dir / RESULT_FILENAME, results, FIELDS)
    accounting = _accounting(results)
    write_csv(ledger / "contest_accounting.csv", accounting, ACCOUNTING_FIELDS)
    sources = [
        {
            "source_id": "in-2024-primary", "state_code": "IN",
            "election_date": "2024-05-07",
            "source_url": (
                "https://indianavoters.in.gov/ENRHistorical/ExportElectionsToCSV"
            ),
            "raw_filename": "indiana/in-2024-primary.csv",
            "sha256": _sha256(raw_dir / "indiana/in-2024-primary.csv"),
            "candidate_rows": sum(row["state_code"] == "IN" for row in results),
            "contests": len({row["contest_id"] for row in results if row["state_code"] == "IN"}),
            "coverage": "all_9_House_districts_and_US_Senate",
            "status": "complete_official_statewide_export",
        },
        {
            "source_id": "mn-senate-certified-summaries", "state_code": "MN",
            "election_date": "2024-08-13 | 2026-08-11",
            "source_url": "https://www.sos.mn.gov/elections-voting/election-results/",
            "raw_filename": "minnesota/mn-senate-certified-summary.csv",
            "sha256": _sha256(raw_dir / "minnesota/mn-senate-certified-summary.csv"),
            "candidate_rows": sum(row["state_code"] == "MN" for row in results),
            "contests": len({row["contest_id"] for row in results if row["state_code"] == "MN"}),
            "coverage": "scheduled_US_Senate_primaries_only",
            "status": "official_summary_recovered",
        },
        {
            "source_id": "mn-house-blocker", "state_code": "MN",
            "election_date": "2024-08-13 | 2026-08-11",
            "source_url": "https://electionresults.sos.mn.gov/",
            "raw_filename": "",
            "sha256": "",
            "candidate_rows": 0, "contests": 0,
            "coverage": "House_results_not_emitted",
            "status": "radware_captcha_or_uncertified_only",
        },
        {
            "source_id": "oh-2026-official-index", "state_code": "OH",
            "election_date": "2026-05-05",
            "source_url": "https://publicfiles.ohiosos.gov/election-results/files-index.json",
            "raw_filename": "ohio/ohio-files-index.json",
            "sha256": _sha256(raw_dir / "ohio/ohio-files-index.json"),
            "candidate_rows": 0, "contests": 0,
            "coverage": "certified_routes_verified_results_blocked",
            "status": "blocked",
        },
        {
            "source_id": "mo-2026-official-index", "state_code": "MO",
            "election_date": "2026-08-04",
            "source_url": "https://www.sos.mo.gov/elections/s_default.asp?id=results",
            "raw_filename": "missouri/mo-results-index.html",
            "sha256": _sha256(raw_dir / "missouri/mo-results-index.html"),
            "candidate_rows": 0, "contests": 0,
            "coverage": "live_ENR_unofficial_certified_archive_missing",
            "status": "blocked",
        },
    ]
    write_csv(ledger / "source_manifest.csv", sources, list(sources[0]))
    party_rows = export_party_contest_accounting(
        output_dir,
        ledger / "party_contest_accounting.csv",
    )
    raw_artifacts = export_provider_raw_artifacts(
        RAW_DIR,
        output_dir,
        ledger / "provider_raw_artifacts.csv",
    )
    return {
        "result_rows": len(results),
        "contests": len({row["contest_id"] for row in results}),
        "accounting_rows": len(accounting),
        "sources": len(sources),
        "party_contests": len(party_rows),
        "raw_artifacts": len(raw_artifacts),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    summary = collect_remaining_midwest(args.raw_dir, args.output_dir)
    print(" ".join(f"{key}={value}" for key, value in summary.items()))


if __name__ == "__main__":
    main()
