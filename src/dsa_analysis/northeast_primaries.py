"""Parse official Maryland, Massachusetts, and Connecticut primary results."""

import argparse
import csv
import gzip
import hashlib
import html
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

from .io import write_csv
from .paths import ANALYSIS_DATA_DIR, RAW_DIR
from .state_results import FIELDS

RAW_SUBDIR = "northeast_primaries"
RESULT_FILENAME = "northeast_primary_results.csv"

MA_SOURCES = (
    {
        "source_id": "ma-2024-primary",
        "date": "2024-09-03",
        "filename": "massachusetts/ma-2024-primary.html",
        "url": "https://electionstats.state.ma.us/elections/search/date:2024-09-03",
    },
    {
        "source_id": "ma-2026-primary",
        "date": "2026-09-01",
        "filename": "massachusetts/ma-2026-primary.html",
        "url": "https://electionstats.state.ma.us/elections/search/date:2026-09-01",
    },
)

CT_SOURCES = (
    {
        "source_id": "ct-2024-primary",
        "date": "2024-08-13",
        "filename": "connecticut/ct-2024-all.csv.gz",
        "url": (
            "https://ct.elstats.civera.com/api/download_search.csv?search="
            "%7B%22global%22%3A%7B%22years%22%3A%7B%22from%22%3A2024%2C"
            "%22to%22%3A2024%7D%7D%2C%22contests%22%3A%7B%22candidates%22%3A"
            "%5B%5D%2C%22offices%22%3A%5B%5D%2C%22divisions%22%3A%5B%5D"
            "%7D%2C%22voterStats%22%3Afalse%2C%22stages%22%3A%5B%5D%2C"
            "%22specialElectionsOnly%22%3Afalse%7D"
        ),
    },
    {
        "source_id": "ct-2026-primary",
        "date": "2026-08-11",
        "filename": "connecticut/ct-2026-all.csv.gz",
        "url": (
            "https://ct.elstats.civera.com/api/download_search.csv?search="
            "%7B%22global%22%3A%7B%22years%22%3A%7B%22from%22%3A2026%2C"
            "%22to%22%3A2026%7D%7D%2C%22contests%22%3A%7B%22candidates%22%3A"
            "%5B%5D%2C%22offices%22%3A%5B%5D%2C%22divisions%22%3A%5B%5D"
            "%7D%2C%22voterStats%22%3Afalse%2C%22stages%22%3A%5B%5D%2C"
            "%22specialElectionsOnly%22%3Afalse%7D"
        ),
    },
)

MD_SOURCES = tuple(
    {
        "source_id": f"md-{year}-primary-{party.lower()}",
        "date": date,
        "party": party,
        "filename": f"maryland/md-{year}-{filename_party}.csv",
        "url": (
            f"https://elections.maryland.gov/elections/{prefix}{year}/election_data/"
            f"{code}_CongressionalBreakDown{filename_party}.csv"
        ),
    }
    for year, date, prefix, code in (
        (2024, "2024-05-14", "archive/", "PP24"),
        (2026, "2026-06-23", "", "GP26"),
    )
    for party, filename_party in (
        ("Democratic", "Democratic"),
        ("Republican", "Republican"),
    )
)

MANIFEST_FIELDS = [
    "source_id", "state_code", "election_date", "artifact_kind", "authority",
    "publication_url", "source_url", "raw_filename", "sha256", "acquisition_status",
    "verification_status", "candidate_rows", "contests", "coverage", "notes",
]

ACCOUNTING_FIELDS = [
    "cycle", "state_code", "chamber", "district", "term", "primary_party",
    "status", "candidate_rows", "source_ids", "notes",
]

ATTEMPT_FIELDS = [
    "attempt_id", "attempted_on", "state_code", "cycle", "source_url", "method",
    "outcome", "raw_evidence", "notes",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _votes(value: object) -> int:
    text = str(value or "").strip().replace(",", "")
    if not text or not text.isdigit():
        raise ValueError(f"Invalid vote total: {value!r}")
    return int(text)


def _strip_tags(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def _massachusetts_inventory(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    chunks = re.split(r'(?=<tr[^>]*class="election_item)', text)
    output = []
    for chunk in chunks:
        opening = re.match(r"<tr[^>]*>", chunk)
        identity = (
            re.search(r'id="election-id-(\d+)"', opening[0])
            if opening else None
        )
        if identity is None or '<td class="candidates_container_cell"' not in chunk:
            continue
        prefix, candidate_cell = chunk.split(
            '<td class="candidates_container_cell"', 1,
        )
        cells = re.findall(r"<td[^>]*>(.*?)</td>", prefix, re.S)
        if len(cells) < 4:
            continue
        year, office, district, stage = (_strip_tags(cell) for cell in cells[:4])
        if office not in {"U.S. House", "U.S. Senate"}:
            continue
        candidates = []
        body_match = re.search(r"<tbody>(.*?)</tbody>", candidate_cell, re.S)
        if body_match:
            for row_number, match in enumerate(
                re.finditer(r"<tr([^>]*)>(.*?)</tr>", body_match[1], re.S),
                1,
            ):
                attrs, body = match.groups()
                if "more_info" in attrs:
                    continue
                vote_match = re.search(
                    r'<td class="number">\s*([\d,]+)\s*</td>',
                    body,
                    re.S,
                )
                if vote_match is None:
                    continue
                name_match = re.search(
                    r'<div class="name">\s*(?:<a[^>]*>)?'
                    r"(.*?)(?:</a>)?\s*</div>",
                    body,
                    re.S,
                )
                if name_match:
                    name = _strip_tags(name_match[1])
                    href_match = re.search(r'<a href="([^"]+)"', name_match[0])
                    source_id = (
                        href_match[1].rsplit("/", 1)[-1]
                        if href_match else re.sub(r"\W+", "-", name.lower())
                    )
                    write_in = "(Write-In)" in _strip_tags(body)
                elif "n_all_other_votes" in attrs:
                    name = "All Others"
                    source_id = "all-others"
                    write_in = True
                else:
                    continue
                candidates.append({
                    "name": name,
                    "source_id": source_id,
                    "write_in": write_in,
                    "votes": _votes(vote_match[1]),
                    "row_number": row_number,
                })
        output.append({
            "election_id": identity[1],
            "year": year,
            "office": office,
            "district": district,
            "stage": stage,
            "candidates": candidates,
            "no_candidates": "class=\"no_candidates\"" in candidate_cell,
        })
    return output


def parse_massachusetts(path: Path, source: dict) -> list[dict]:
    source_hash = _sha256(path)
    output = []
    for contest in _massachusetts_inventory(path):
        chamber = "Senate" if contest["office"] == "U.S. Senate" else "House"
        district = (
            "S" if chamber == "Senate"
            else re.match(r"(\d+)", contest["district"])[1].zfill(2)
        )
        party = contest["stage"].removesuffix(" Primary")
        contest_id = (
            f"ma-{source['date']}-{chamber.lower()}-{district.lower()}-regular-"
            f"{party.lower()}"
        )
        for candidate in contest["candidates"]:
            output.append({
                "contest_id": contest_id,
                "cycle": source["date"][:4],
                "election_date": source["date"],
                "stage": "primary",
                "state_code": "MA",
                "chamber": chamber,
                "district": district,
                "term": "regular",
                "election_system": "partisan_primary",
                "primary_party": party,
                "candidate_name": candidate["name"],
                "candidate_source_id": (
                    f"{contest['election_id']}-{candidate['source_id']}"
                ),
                "party": "" if candidate["write_in"] else party,
                "write_in": candidate["write_in"],
                "votes": candidate["votes"],
                "source_id": source["source_id"],
                "source_url": source["url"],
                "source_sha256": source_hash,
                "source_locators": (
                    f"{path.name}:election-{contest['election_id']}:"
                    f"candidate-{candidate['row_number']}"
                ),
                "reporting_units": 1,
            })
    house = {row["district"] for row in output if row["chamber"] == "House"}
    if house != {f"{district:02}" for district in range(1, 10)}:
        raise ValueError("Massachusetts House coverage is incomplete")
    if not any(row["chamber"] == "Senate" for row in output):
        raise ValueError("Massachusetts Senate coverage is incomplete")
    return output


def parse_connecticut(path: Path, source: dict) -> list[dict]:
    groups = defaultdict(list)
    seen = set()
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for number, row in enumerate(reader, 2):
            if (
                row["election_date"][:10] != source["date"]
                or row["election_type"] != "Primary"
                or row["office_name"] not in {
                    "Representative in Congress", "United States Senator",
                }
                or row["division_type"] != "City/Town"
            ):
                continue
            if row["candidate_name"].casefold() in {
                "total votes cast", "total ballots cast", "blank votes",
                "overvotes", "undervotes",
            }:
                continue
            key = (
                row["contest_id"], row["candidate_id"], row["division_id"],
                row["vote_channel"],
            )
            if key in seen:
                raise ValueError(f"Duplicate Connecticut town/channel row: {key}")
            seen.add(key)
            groups[(row["contest_id"], row["candidate_id"])].append({
                "name": row["candidate_name"],
                "party": row["candidate_party_name"],
                "primary_party": row["primary_party"],
                "office": row["office_name"],
                "district": row["district_name"],
                "unit": row["division_id"],
                "votes": _votes(row["votes"]),
                "locator": f"{path.name}:{number}",
            })
    source_hash = _sha256(path)
    output = []
    for (official_contest, candidate_id), rows in sorted(groups.items()):
        first = rows[0]
        chamber = "Senate" if first["office"] == "United States Senator" else "House"
        district = "S" if chamber == "Senate" else str(int(first["district"])).zfill(2)
        party = first["primary_party"]
        write_in = first["name"].casefold() in {"write-in", "scattering"}
        output.append({
            "contest_id": (
                f"ct-{source['date']}-{chamber.lower()}-{district.lower()}-"
                f"regular-{party.lower()}"
            ),
            "cycle": source["date"][:4],
            "election_date": source["date"],
            "stage": "primary",
            "state_code": "CT",
            "chamber": chamber,
            "district": district,
            "term": "regular",
            "election_system": "partisan_primary",
            "primary_party": party,
            "candidate_name": first["name"],
            "candidate_source_id": candidate_id,
            "party": "" if write_in else first["party"],
            "write_in": write_in,
            "votes": sum(row["votes"] for row in rows),
            "source_id": source["source_id"],
            "source_url": source["url"],
            "source_sha256": source_hash,
            "source_locators": (
                f"{path.name}:contest-{official_contest}:candidate-{candidate_id}"
            ),
            "reporting_units": len({row["unit"] for row in rows}),
        })
    return output


def parse_maryland(path: Path, source: dict) -> list[dict]:
    output = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = [value.strip() for value in next(reader)]
        for number, values in enumerate(reader, 2):
            row = dict(zip(header, values))
            if row["Office Name"] not in {"U.S. Congress", "U.S. Senator"}:
                continue
            chamber = "Senate" if row["Office Name"] == "U.S. Senator" else "House"
            district = "S" if chamber == "Senate" else row["Office District"].zfill(2)
            if chamber == "Senate":
                votes = sum(
                    _votes(row[f"Congressional District {value}"])
                    for value in range(1, 9)
                )
            else:
                votes = _votes(row[f"Congressional District {int(district)}"])
            write_in = "write-in" in row["Candidate Name"].casefold()
            party = source["party"]
            output.append({
                "contest_id": (
                    f"md-{source['date']}-{chamber.lower()}-{district.lower()}-"
                    f"regular-{party.lower()}"
                ),
                "cycle": source["date"][:4],
                "election_date": source["date"],
                "stage": "primary",
                "state_code": "MD",
                "chamber": chamber,
                "district": district,
                "term": "regular",
                "election_system": "partisan_primary",
                "primary_party": party,
                "candidate_name": row["Candidate Name"],
                "candidate_source_id": f"{source['source_id']}-{number}",
                "party": "" if write_in else party,
                "write_in": write_in,
                "votes": votes,
                "source_id": source["source_id"],
                "source_url": source["url"],
                "source_sha256": _sha256(path),
                "source_locators": f"{path.name}:{number}",
                "reporting_units": 1,
            })
    return output


def _accounting(results: list[dict], raw_dir: Path) -> list[dict]:
    rows = []
    groups = defaultdict(list)
    for row in results:
        groups[row["contest_id"]].append(row)
    for group in groups.values():
        first = group[0]
        named = [row for row in group if not row["write_in"]]
        rows.append({
            "cycle": first["cycle"], "state_code": first["state_code"],
            "chamber": first["chamber"], "district": first["district"],
            "term": first["term"], "primary_party": first["primary_party"],
            "status": (
                "complete_unopposed_result" if len(named) == 1
                else "complete_official_results"
            ),
            "candidate_rows": len(group),
            "source_ids": first["source_id"],
            "notes": "",
        })
    ma_seen = {
        (row["cycle"], row["chamber"], row["district"], row["primary_party"])
        for row in rows if row["state_code"] == "MA"
    }
    for source in MA_SOURCES:
        for item in _massachusetts_inventory(raw_dir / source["filename"]):
            chamber = "Senate" if item["office"] == "U.S. Senate" else "House"
            district = (
                "S" if chamber == "Senate"
                else re.match(r"(\d+)", item["district"])[1].zfill(2)
            )
            party = item["stage"].removesuffix(" Primary")
            key = (source["date"][:4], chamber, district, party)
            if key in ma_seen:
                continue
            rows.append({
                "cycle": source["date"][:4], "state_code": "MA",
                "chamber": chamber, "district": district, "term": "regular",
                "primary_party": party,
                "status": (
                    "official_no_candidates"
                    if item["no_candidates"]
                    else "no_reported_contest_not_inferred"
                ),
                "candidate_rows": 0, "source_ids": source["source_id"],
                "notes": "Explicit No Candidates label." if item["no_candidates"] else "",
            })
    observed = {
        (row["cycle"], row["state_code"], row["chamber"], row["district"], row["primary_party"])
        for row in rows
    }
    for cycle in ("2024", "2026"):
        for district in range(1, 6):
            for party in ("Democratic", "Republican"):
                key = (cycle, "CT", "House", f"{district:02}", party)
                if key not in observed:
                    rows.append({
                        "cycle": cycle, "state_code": "CT", "chamber": "House",
                        "district": f"{district:02}", "term": "regular",
                        "primary_party": party,
                        "status": "no_reported_contest_not_inferred",
                        "candidate_rows": 0,
                        "source_ids": f"ct-{cycle}-primary",
                        "notes": "No federal contest row in the complete year export.",
                    })
    for party in ("Democratic", "Republican"):
        key = ("2024", "CT", "Senate", "S", party)
        if key not in observed:
            rows.append({
                "cycle": "2024", "state_code": "CT", "chamber": "Senate",
                "district": "S", "term": "regular", "primary_party": party,
                "status": "no_reported_contest_not_inferred", "candidate_rows": 0,
                "source_ids": "ct-2024-primary",
                "notes": "No Senate contest row in the complete year export.",
            })
    for state in ("CT", "MD"):
        rows.append({
            "cycle": "2026",
            "state_code": state,
            "chamber": "Senate",
            "district": "S",
            "term": "regular",
            "primary_party": "",
            "status": "not_scheduled_this_cycle",
            "candidate_rows": 0,
            "source_ids": (
                "ct-2026-primary"
                if state == "CT"
                else "md-2026-primary-election-calendar"
            ),
            "notes": "No U.S. Senate seat was scheduled for election in this state in 2026.",
        })
    return sorted(rows, key=lambda row: (
        row["cycle"], row["state_code"], row["chamber"], row["district"],
        row["primary_party"], row["status"],
    ))


def collect_northeast_primaries(
    raw_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict:
    raw_dir = raw_dir or RAW_DIR / RAW_SUBDIR
    output_dir = output_dir or ANALYSIS_DATA_DIR / "congressional"
    ledger = output_dir / "northeast"
    ledger.mkdir(parents=True, exist_ok=True)
    results = []
    for source in MA_SOURCES:
        results.extend(parse_massachusetts(raw_dir / source["filename"], source))
    for source in CT_SOURCES:
        results.extend(parse_connecticut(raw_dir / source["filename"], source))
    for source in MD_SOURCES:
        results.extend(parse_maryland(raw_dir / source["filename"], source))
    results.sort(key=lambda row: (
        row["cycle"], row["state_code"], row["chamber"], row["district"],
        row["primary_party"], row["candidate_name"],
    ))
    write_csv(output_dir / RESULT_FILENAME, results, FIELDS)
    accounting = _accounting(results, raw_dir)
    write_csv(ledger / "contest_accounting.csv", accounting, ACCOUNTING_FIELDS)
    manifest = []
    for source in (*MA_SOURCES, *CT_SOURCES, *MD_SOURCES):
        path = raw_dir / source["filename"]
        subset = [row for row in results if row["source_id"] == source["source_id"]]
        manifest.append({
            "source_id": source["source_id"],
            "state_code": source["source_id"][:2].upper(),
            "election_date": source["date"],
            "source_url": source["url"],
            "raw_filename": source["filename"],
            "sha256": _sha256(path),
            "candidate_rows": len(subset),
            "contests": len({row["contest_id"] for row in subset}),
            "coverage": (
                "complete_year_export; City/Town hierarchy only"
                if source["source_id"].startswith("ct-")
                else "official_statewide_certified_results"
            ),
            "notes": (
                "Named write-ins have blank party; primary_party is the ballot category."
            ),
        })
    write_csv(
        ledger / "source_manifest.csv",
        manifest,
        list(manifest[0]),
    )
    attempts = [
        {
            "attempt_id": "ma-certified-pages", "attempted_on": "2026-09-22",
            "state_code": "MA", "cycle": "2024-2026",
            "source_url": "https://electionstats.state.ma.us/elections/search/",
            "method": "direct_certified_html", "outcome": "success",
            "raw_evidence": "massachusetts/", "notes": "",
        },
        {
            "attempt_id": "ct-civera", "attempted_on": "2026-09-22",
            "state_code": "CT", "cycle": "2024-2026",
            "source_url": "https://ct.elstats.civera.com/api/download_search.csv",
            "method": "public_csv_export_gzip", "outcome": "success",
            "raw_evidence": "connecticut/", "notes": "Polling Place rows excluded.",
        },
        {
            "attempt_id": "md-statewide-csv", "attempted_on": "2026-09-22",
            "state_code": "MD", "cycle": "2024-2026",
            "source_url": "https://elections.maryland.gov/elections/",
            "method": "state_congressional_breakdown_csv", "outcome": "success",
            "raw_evidence": "maryland/", "notes": "",
        },
    ]
    write_csv(ledger / "attempt_ledger.csv", attempts, ATTEMPT_FIELDS)
    return {
        "result_rows": len(results),
        "contests": len({row["contest_id"] for row in results}),
        "accounting_rows": len(accounting),
        "sources": len(manifest),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    summary = collect_northeast_primaries(args.raw_dir, args.output_dir)
    print(" ".join(f"{key}={value}" for key, value in summary.items()))


if __name__ == "__main__":
    main()
