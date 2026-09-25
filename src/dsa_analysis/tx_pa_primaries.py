"""Recover official Texas and Pennsylvania congressional primary returns."""

import argparse
import base64
import csv
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .io import write_csv
from .paths import ANALYSIS_DATA_DIR, RAW_DIR
from .state_results import FIELDS

RAW_SUBDIR = "tx_pa_primaries"
RESULT_FILENAME = "tx_pa_primary_results.csv"
MANIFEST_SUBDIR = "tx_pa"

SOURCE_MANIFEST_FIELDS = [
    "source_id",
    "state_code",
    "election_date",
    "stage",
    "artifact_kind",
    "authority",
    "publication_url",
    "source_url",
    "acquisition_url",
    "raw_filename",
    "source_date",
    "sha256",
    "acquisition_status",
    "verification_status",
    "certification_status",
    "provisional_status",
    "candidate_rows",
    "contests",
    "coverage",
    "source_locators",
    "notes",
]

ATTEMPT_FIELDS = [
    "attempt_id",
    "attempted_on",
    "state_code",
    "cycle",
    "source_url",
    "method",
    "outcome",
    "raw_evidence",
    "notes",
]

GAP_FIELDS = [
    "gap_id",
    "state_code",
    "cycle",
    "stage",
    "chamber",
    "coverage_status",
    "recovered_scope",
    "missing_scope",
    "blocker",
    "next_authoritative_step",
    "source_urls",
]

CONTEST_FIELDS = [
    "contest_id",
    "state_code",
    "cycle",
    "election_date",
    "stage",
    "chamber",
    "district",
    "primary_party",
    "candidate_count",
    "uncontested",
    "nonnumeric_result",
    "result_status",
    "certification_status",
    "source_id",
]

TX_PUBLICATION = (
    "https://www.sos.texas.gov/elections/historical/elections-results-archive.shtml"
)
TX_2024_REPORT_BASE = "https://results.texas-election.com/static/data/Reports"
TX_2024_JSON_BASE = "https://results.texas-election.com/static/data/election"
TX_2026_API_BASE = (
    "https://goelect.txelections.civixapps.com/api-ivis-system/api/s3/enr"
)
PA_PUBLICATION = (
    "https://www.pa.gov/agencies/dos/resources/voting-and-elections-resources/"
    "voting-and-election-statistics/election-data"
)
PA_2024_DATA_URL = (
    "https://www.pa.gov/content/dam/copapwp-pagov/en/dos/resources/"
    "voting-and-elections/bulk-data/electionreturns_2024_primary_precinctreturns.txt"
)
PA_2026_DATA_URL = (
    "https://www.pa.gov/content/dam/copapwp-pagov/en/dos/resources/"
    "voting-and-elections/bulk-data/2026-general-primary/er/"
    "electionreturns_2026_primary_precinctreturns.txt"
)

TX_2024_SOURCES = (
    {
        "source_id": "tx-2024-dem-primary-official-canvass",
        "date": "2024-03-05",
        "stage": "primary",
        "party": "Democratic",
        "party_code": "DEM",
        "election_id": "49665",
        "version": "659",
        "pdf": "tx/2024/tx-2024-dem-primary-official-canvass.pdf",
        "text": "tx/2024/tx-2024-dem-primary-official-canvass.txt",
        "json": "tx/2024/election-49665-Federal.json",
        "report_name": "OfficialCanvassReport.pdf",
        "archive_timestamp": "20241002024848",
        "source_date": "2024-06-25",
        "report_kind": "official_canvass",
    },
    {
        "source_id": "tx-2024-rep-primary-official-canvass",
        "date": "2024-03-05",
        "stage": "primary",
        "party": "Republican",
        "party_code": "REP",
        "election_id": "49666",
        "version": "782",
        "pdf": "tx/2024/tx-2024-rep-primary-official-canvass.pdf",
        "text": "tx/2024/tx-2024-rep-primary-official-canvass.txt",
        "json": "tx/2024/election-49666-Federal.json",
        "report_name": "OfficialCanvassReport.pdf",
        "archive_timestamp": "20240530022252",
        "source_date": "2024-05-15",
        "report_kind": "official_canvass",
    },
    {
        "source_id": "tx-2024-dem-primary-runoff-county-canvass",
        "date": "2024-05-28",
        "stage": "primary_runoff",
        "party": "Democratic",
        "party_code": "DEM",
        "election_id": "50026",
        "version": "784",
        "pdf": "tx/2024/tx-2024-dem-runoff-county-canvass.pdf",
        "text": "tx/2024/tx-2024-dem-runoff-county-canvass.txt",
        "json": "tx/2024/election-50026-Federal.json",
        "report_name": "CountybyCountyCanvassReport.pdf",
        "archive_timestamp": "20240724024241",
        "source_date": "2024-06-17",
        "report_kind": "county_canvass",
    },
    {
        "source_id": "tx-2024-rep-primary-runoff-county-canvass",
        "date": "2024-05-28",
        "stage": "primary_runoff",
        "party": "Republican",
        "party_code": "REP",
        "election_id": "50027",
        "version": "852",
        "pdf": "tx/2024/tx-2024-rep-runoff-county-canvass.pdf",
        "text": "tx/2024/tx-2024-rep-runoff-county-canvass.txt",
        "json": "tx/2024/election-50027-Federal.json",
        "report_name": "CountybyCountyCanvassReport.pdf",
        "archive_timestamp": "20260205173121",
        "source_date": "2024-06-17",
        "report_kind": "county_canvass",
    },
)

TX_2026_SOURCES = (
    {
        "source_id": "tx-2026-rep-primary-results",
        "date": "2026-03-03",
        "stage": "primary",
        "party": "Republican",
        "party_code": "REP",
        "election_id": "53813",
        "filename": "tx/2026/election-53813.json",
        "expected_house_districts": set(range(1, 39)),
        "expected_senate": True,
    },
    {
        "source_id": "tx-2026-dem-primary-results",
        "date": "2026-03-03",
        "stage": "primary",
        "party": "Democratic",
        "party_code": "DEM",
        "election_id": "53814",
        "filename": "tx/2026/election-53814.json",
        "expected_house_districts": set(range(1, 39)),
        "expected_senate": True,
    },
    {
        "source_id": "tx-2026-rep-primary-runoff-results",
        "date": "2026-05-26",
        "stage": "primary_runoff",
        "party": "Republican",
        "party_code": "REP",
        "election_id": "58315",
        "filename": "tx/2026/election-58315.json",
        "expected_house_districts": {7, 9, 16, 19, 30, 33, 35, 37, 38},
        "expected_senate": True,
    },
    {
        "source_id": "tx-2026-dem-primary-runoff-results",
        "date": "2026-05-26",
        "stage": "primary_runoff",
        "party": "Democratic",
        "party_code": "DEM",
        "election_id": "58314",
        "filename": "tx/2026/election-58314.json",
        "expected_house_districts": {1, 5, 14, 17, 18, 24, 33, 35},
        "expected_senate": False,
    },
)

PA_SOURCES = (
    {
        "source_id": "pa-2024-primary-precinct-returns",
        "date": "2024-04-23",
        "stage": "primary",
        "filename": "pa/2024/electionreturns_2024_primary_precinctreturns.txt",
        "readme": "pa/2024/electionreturns_2024_primary_readme.txt",
        "certification": "pa/2024/pa-2024-primary-certification.html",
        "url": PA_2024_DATA_URL,
        "readme_url": (
            "https://www.pa.gov/content/dam/copapwp-pagov/en/dos/resources/"
            "voting-and-elections/bulk-data/electionreturns_2024_primary_readme.txt"
        ),
        "certification_url": (
            "https://www.pa.gov/agencies/dos/newsroom/"
            "secretary-of-the-commonwealth-certifies-2024-primary-election-re"
        ),
        "source_date": "2024-07-23",
        "expected_house_districts": set(range(1, 18)),
        "expected_senate": True,
    },
    {
        "source_id": "pa-2026-primary-precinct-returns",
        "date": "2026-05-19",
        "stage": "primary",
        "filename": "pa/2026/electionreturns_2026_primary_precinctreturns.txt",
        "readme": "pa/2026/electionreturns_2026_primary_readmefile.txt",
        "certification": "pa/2026/pa-2026-primary-certification.html",
        "url": PA_2026_DATA_URL,
        "readme_url": (
            "https://www.pa.gov/content/dam/copapwp-pagov/en/dos/resources/"
            "voting-and-elections/bulk-data/2026-general-primary/er/"
            "electionreturns_2026_primary_readmefile.txt"
        ),
        "certification_url": (
            "https://www.pa.gov/agencies/dos/newsroom/"
            "secretary-of-the-commonwealth-certifies-2026-primary-election-re"
        ),
        "source_date": "2026-07-21",
        "expected_house_districts": set(range(1, 18)),
        "expected_senate": False,
    },
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _integer(value: object) -> int:
    text = str(value).strip().replace(",", "")
    if re.fullmatch(r"\d+(?:\.0)?", text) is None:
        raise ValueError(f"Invalid integer value: {value!r}")
    return int(float(text))


def _party_name(code: str) -> str:
    parties = {"DEM": "Democratic", "REP": "Republican"}
    try:
        return parties[code.strip().upper()]
    except KeyError as error:
        raise ValueError(f"Unknown primary party code: {code!r}") from error


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _candidate_name(value: str) -> str:
    return re.sub(r"\s+\(I\)$", "", " ".join(value.split())).strip()


def _match_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    text = re.sub(r"\s+\(I\)$", "", text.upper())
    return re.sub(r"[^A-Z0-9]+", " ", text).strip()


def _contest_id(source: dict, chamber: str, district: str) -> str:
    return "-".join((
        "tx" if source.get("state", "TX") == "TX" else "pa",
        source["date"],
        chamber.casefold(),
        district.casefold(),
        "regular",
        _slug(source["party"]),
    ))


def _locator_ranges(filename: str, numbers: list[int]) -> str:
    ranges = []
    start = end = None
    for number in sorted(set(numbers)):
        if start is None:
            start = end = number
        elif number == end + 1:
            end = number
        else:
            ranges.append(str(start) if start == end else f"{start}-{end}")
            start = end = number
    if start is not None:
        ranges.append(str(start) if start == end else f"{start}-{end}")
    return f"{filename}:{','.join(ranges)}"


def _texas_races(path: Path) -> tuple[dict[str, tuple[int, dict]], dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    races = {}
    for race_index, race in enumerate(data.get("Races", [])):
        office = " ".join(str(race.get("N", "")).split())
        if office == "U. S. SENATOR":
            district = "S"
        else:
            match = re.fullmatch(r"U\. S\. REPRESENTATIVE DISTRICT (\d+)", office)
            if match is None:
                continue
            district = match[1].zfill(2)
        if district in races:
            raise ValueError(f"Duplicate Texas congressional race: {district}")
        races[district] = (race_index, race)
    if not races:
        raise ValueError(f"No Texas congressional races in {path}")
    return races, data


def _texas_constants(path: Path, encoded: bool) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if encoded:
        data = json.loads(base64.b64decode(data["upload"]))
    try:
        return data["electionInfo"]
    except KeyError as error:
        raise ValueError("Texas election-constants schema changed") from error


def _validate_texas_constants(raw_root: Path) -> None:
    sources = (
        (
            _texas_constants(
                raw_root / "tx/2024/ElectionConstants_382.json", encoded=False
            ),
            TX_2024_SOURCES,
        ),
        (
            _texas_constants(
                raw_root / "tx/2026/electionConstants.json", encoded=True
            ),
            TX_2026_SOURCES,
        ),
    )
    for election_info, source_group in sources:
        for source in source_group:
            year = source["date"][:4]
            matches = [
                election
                for stage in election_info.get(year, {}).values()
                for election_id, election in stage.items()
                if election_id == source["election_id"]
            ]
            if len(matches) != 1:
                raise ValueError(
                    f'Cannot locate Texas election ID {source["election_id"]}'
                )
            if matches[0].get("O") != "Y":
                raise ValueError(
                    f'Texas election is not official: {source["election_id"]}'
                )


def _validate_texas_coverage(rows: list[dict], source: dict) -> None:
    house = {int(row["district"]) for row in rows if row["chamber"] == "House"}
    senate = any(row["chamber"] == "Senate" for row in rows)
    expected_house = source.get("expected_house_districts")
    if expected_house is not None and house != set(expected_house):
        raise ValueError(
            f'{source["source_id"]}: Texas House coverage differs: {house}'
        )
    expected_senate = source.get("expected_senate")
    if expected_senate is not None and senate != expected_senate:
        raise ValueError(f'{source["source_id"]}: Texas Senate coverage differs')


def parse_texas_api(path: Path, source: dict) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {"Home", "Federal"}
    if not required <= set(payload):
        raise ValueError("Texas Civix election payload schema changed")
    home = json.loads(base64.b64decode(payload["Home"]))
    federal = json.loads(base64.b64decode(payload["Federal"]))
    election_date = datetime.strptime(home["ElecDate"], "%m%d%Y").date().isoformat()
    if election_date != source["date"]:
        raise ValueError("Texas Civix payload contains a different election date")
    rows = []
    source_hash = _sha256(path)
    for race_index, race in enumerate(federal.get("Races", [])):
        office = " ".join(str(race.get("N", "")).split())
        if office == "U. S. SENATOR":
            chamber, district = "Senate", "S"
        else:
            match = re.fullmatch(r"U\. S\. REPRESENTATIVE DISTRICT (\d+)", office)
            if match is None:
                continue
            chamber, district = "House", match[1].zfill(2)
        candidates = race.get("Candidates", [])
        if not candidates:
            raise ValueError(f"Texas race lacks candidates: {office}")
        if sum(_integer(candidate["V"]) for candidate in candidates) != _integer(race["T"]):
            raise ValueError(f"Texas candidate totals differ from race total: {office}")
        for candidate_index, candidate in enumerate(candidates):
            if candidate["P"] != source["party_code"]:
                raise ValueError(f"Unexpected Texas party in {office}")
            rows.append({
                "contest_id": _contest_id(source, chamber, district),
                "cycle": source["date"][:4],
                "election_date": source["date"],
                "stage": source["stage"],
                "state_code": "TX",
                "chamber": chamber,
                "district": district,
                "term": "regular",
                "election_system": "partisan_primary",
                "primary_party": source["party"],
                "candidate_name": _candidate_name(candidate["N"]),
                "candidate_source_id": str(candidate["ID"]),
                "party": source["party"],
                "write_in": "WRITE-IN" in candidate["N"].upper(),
                "votes": _integer(candidate["V"]),
                "source_id": source["source_id"],
                "source_url": (
                    f"{TX_2026_API_BASE}/election/{source['election_id']}"
                ),
                "source_sha256": source_hash,
                "source_locators": (
                    f"{path.name}:$.Federal(base64).Races[{race_index}]"
                    f".Candidates[{candidate_index}]"
                ),
                "reporting_units": 1,
            })
    _validate_texas_coverage(rows, source)
    return rows


def _map_texas_candidate(pdf_name: str, candidates: list[dict]) -> dict:
    target = _match_name(pdf_name)
    matches = [
        candidate for candidate in candidates
        if (
            _match_name(candidate["N"]) == target
            or _match_name(candidate["N"]).startswith(target)
            or target.startswith(_match_name(candidate["N"]))
        )
    ]
    if len(matches) != 1:
        raise ValueError(f"Cannot uniquely map Texas candidate {pdf_name!r}")
    return matches[0]


def _parse_texas_primary_text(
    text_path: Path,
    races: dict[str, tuple[int, dict]],
    source: dict,
) -> dict[str, list[tuple[dict, int, int]]]:
    parsed: dict[str, list[tuple[dict, int, int]]] = defaultdict(list)
    totals = {}
    page = 0
    district = None
    office_pattern = re.compile(
        r"U\. S\. (SENATOR|REPRESENTATIVE DISTRICT (\d+)) "
        r"[\d,]+ [\d.]+ %$"
    )
    candidate_pattern = re.compile(
        rf"(.+?) {source['party_code']} ([\d,]+) [\d.]+ %$"
    )
    for line in text_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        page_match = re.fullmatch(r"PAGE (\d+)", line)
        if page_match:
            page = int(page_match[1])
            continue
        office_match = office_pattern.fullmatch(line)
        if office_match:
            district = (
                "S" if office_match[1] == "SENATOR"
                else office_match[2].zfill(2)
            )
            continue
        if line.startswith((
            "PRESIDENT",
            "STATE ",
            "RAILROAD ",
            "JUSTICE",
            "PRESIDING ",
            "MEMBER,",
            "DISTRICT ",
        )):
            district = None
        candidate_match = candidate_pattern.fullmatch(line)
        if candidate_match and district is not None:
            _, race = races[district]
            candidate = _map_texas_candidate(
                candidate_match[1], race.get("Candidates", [])
            )
            parsed[district].append((
                candidate,
                _integer(candidate_match[2]),
                page,
            ))
        total_match = re.fullmatch(r"([\d,]+)Total Votes", line)
        if total_match and district is not None:
            totals[district] = _integer(total_match[1])
    if set(parsed) != set(races):
        raise ValueError(
            f'Texas canvass contest coverage differs: {set(parsed)} != {set(races)}'
        )
    for district_name, candidate_rows in parsed.items():
        if len(candidate_rows) != len(races[district_name][1]["Candidates"]):
            raise ValueError(f"Texas canvass candidate coverage differs: {district_name}")
        if sum(row[1] for row in candidate_rows) != totals.get(district_name):
            raise ValueError(f"Texas canvass totals do not add: {district_name}")
    return parsed


def _parse_texas_runoff_text(
    text_path: Path,
    races: dict[str, tuple[int, dict]],
) -> dict[str, list[tuple[dict, int, int]]]:
    lines = []
    page = 0
    for raw_line in text_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        page_match = re.fullmatch(r"PAGE (\d+)", line)
        if page_match:
            page = int(page_match[1])
        lines.append((line, page))
    parsed = {}
    for district, (_, race) in races.items():
        heading = (
            "U. S. SENATOR" if district == "S"
            else f"U. S. REPRESENTATIVE DISTRICT {int(district)}"
        )
        starts = [index for index, (line, _) in enumerate(lines) if line == heading]
        if len(starts) != 1:
            raise ValueError(f"Cannot locate Texas runoff contest: {heading}")
        total_match = None
        total_page = None
        for line, line_page in lines[starts[0] + 1:]:
            match = re.fullmatch(r"TOTAL VOTES ((?:[\d,]+ ?)+)", line)
            if match:
                total_match = match
                total_page = line_page
                break
        if total_match is None:
            raise ValueError(f"Cannot locate Texas runoff totals: {heading}")
        numbers = [_integer(value) for value in total_match[1].split()]
        candidates = race.get("Candidates", [])
        if len(numbers) != len(candidates) + 1:
            raise ValueError(f"Texas runoff total column count changed: {heading}")
        if sum(numbers[:-1]) != numbers[-1]:
            raise ValueError(f"Texas runoff totals do not add: {heading}")
        json_votes = [_integer(candidate["V"]) for candidate in candidates]
        if any(json_votes) and json_votes != numbers[:-1]:
            raise ValueError(f"Texas runoff PDF and JSON totals differ: {heading}")
        parsed[district] = [
            (candidate, votes, total_page)
            for candidate, votes in zip(candidates, numbers[:-1], strict=True)
        ]
    return parsed


def parse_texas_canvass(
    text_path: Path,
    pdf_path: Path,
    json_path: Path,
    source: dict,
) -> list[dict]:
    races, _ = _texas_races(json_path)
    if source["stage"] == "primary":
        parsed = _parse_texas_primary_text(text_path, races, source)
    else:
        parsed = _parse_texas_runoff_text(text_path, races)
    rows = []
    source_hash = _sha256(pdf_path)
    for district, candidate_rows in parsed.items():
        race_index, race = races[district]
        chamber = "Senate" if district == "S" else "House"
        for candidate, votes, page in candidate_rows:
            candidate_index = race["Candidates"].index(candidate)
            if candidate["P"] != source["party_code"]:
                raise ValueError(f"Unexpected Texas canvass party: {candidate['P']}")
            rows.append({
                "contest_id": _contest_id(source, chamber, district),
                "cycle": source["date"][:4],
                "election_date": source["date"],
                "stage": source["stage"],
                "state_code": "TX",
                "chamber": chamber,
                "district": district,
                "term": "regular",
                "election_system": "partisan_primary",
                "primary_party": source["party"],
                "candidate_name": _candidate_name(candidate["N"]),
                "candidate_source_id": str(candidate["ID"]),
                "party": source["party"],
                "write_in": "WRITE-IN" in candidate["N"].upper(),
                "votes": votes,
                "source_id": source["source_id"],
                "source_url": (
                    f"{TX_2024_REPORT_BASE}/{source['election_id']}/"
                    f"{source['report_name']}"
                ),
                "source_sha256": source_hash,
                "source_locators": (
                    f"{pdf_path.name}:page-{page} | "
                    f"{json_path.name}:$.Races[{race_index}]"
                    f".Candidates[{candidate_index}]"
                ),
                "reporting_units": 1,
            })
    source_with_expectations = {
        **source,
        "expected_house_districts": {
            int(district) for district in races if district != "S"
        },
        "expected_senate": "S" in races,
    }
    _validate_texas_coverage(rows, source_with_expectations)
    return rows


def _repair_pennsylvania_row(row: list[str]) -> list[str]:
    if len(row) == 38:
        row = row[:22] + [f"{row[22]}, {row[23]}"] + row[24:]
    if len(row) != 37:
        raise ValueError(f"Pennsylvania precinct row has {len(row)} fields")
    return row


def _pennsylvania_name(row: list[str]) -> str:
    last, first, middle, suffix = (row[index].strip() for index in (11, 12, 13, 14))
    return " ".join(part for part in (first, middle, last, suffix) if part)


def parse_pennsylvania(path: Path, source: dict) -> list[dict]:
    groups: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    seen = set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for line_number, raw_row in enumerate(csv.reader(handle), 1):
            row = _repair_pennsylvania_row(raw_row)
            office = row[8].strip()
            if office not in {"USS", "USC"}:
                continue
            if _integer(row[0]) != int(source["date"][:4]) or row[1].strip() != "P":
                raise ValueError("Pennsylvania return contains a different election")
            party = _party_name(row[9])
            chamber = "Senate" if office == "USS" else "House"
            district = "S" if office == "USS" else str(_integer(row[5])).zfill(2)
            candidate_id = row[10].strip()
            unit = f"{_integer(row[2]):02}:{_integer(row[3])}"
            duplicate = (office, district, row[9].strip(), candidate_id, unit)
            if duplicate in seen:
                raise ValueError(f"Duplicate Pennsylvania precinct result: {duplicate}")
            seen.add(duplicate)
            groups[(office, district, row[9].strip(), candidate_id)].append({
                "name": _pennsylvania_name(row),
                "party": party,
                "chamber": chamber,
                "district": district,
                "unit": unit,
                "votes": _integer(row[15]),
                "line": line_number,
            })
    source_hash = _sha256(path)
    rows = []
    for (_, district, _, candidate_id), records in sorted(groups.items()):
        identities = {
            (record["name"], record["party"], record["chamber"])
            for record in records
        }
        if len(identities) != 1:
            raise ValueError(f"Inconsistent Pennsylvania candidate: {candidate_id}")
        name, party, chamber = next(iter(identities))
        row_source = {**source, "party": party, "state": "PA"}
        rows.append({
            "contest_id": _contest_id(row_source, chamber, district),
            "cycle": source["date"][:4],
            "election_date": source["date"],
            "stage": source["stage"],
            "state_code": "PA",
            "chamber": chamber,
            "district": district,
            "term": "regular",
            "election_system": "partisan_primary",
            "primary_party": party,
            "candidate_name": name,
            "candidate_source_id": candidate_id,
            "party": party,
            "write_in": "WRITE" in name.upper() or "WRITE" in candidate_id.upper(),
            "votes": sum(record["votes"] for record in records),
            "source_id": source["source_id"],
            "source_url": source["url"],
            "source_sha256": source_hash,
            "source_locators": _locator_ranges(
                path.name, [record["line"] for record in records]
            ),
            "reporting_units": len(records),
        })
    house = {int(row["district"]) for row in rows if row["chamber"] == "House"}
    senate = any(row["chamber"] == "Senate" for row in rows)
    if house != source["expected_house_districts"]:
        raise ValueError(f'{source["source_id"]}: Pennsylvania House coverage differs')
    if senate != source["expected_senate"]:
        raise ValueError(f'{source["source_id"]}: Pennsylvania Senate coverage differs')
    return rows


def _source_counts(rows: list[dict], source_id: str) -> tuple[int, int]:
    source_rows = [row for row in rows if row["source_id"] == source_id]
    return len(source_rows), len({row["contest_id"] for row in source_rows})


def _manifest_row(
    *,
    source_id: str,
    state_code: str,
    election_date: str,
    stage: str,
    artifact_kind: str,
    authority: str,
    publication_url: str,
    source_url: str,
    acquisition_url: str,
    path: Path,
    source_date: str,
    verification_status: str,
    certification_status: str,
    provisional_status: str,
    candidate_rows: int,
    contests: int,
    coverage: str,
    source_locators: str,
    notes: str,
) -> dict:
    return {
        "source_id": source_id,
        "state_code": state_code,
        "election_date": election_date,
        "stage": stage,
        "artifact_kind": artifact_kind,
        "authority": authority,
        "publication_url": publication_url,
        "source_url": source_url,
        "acquisition_url": acquisition_url,
        "raw_filename": path.relative_to(RAW_DIR / RAW_SUBDIR).as_posix(),
        "source_date": source_date,
        "sha256": _sha256(path),
        "acquisition_status": "captured",
        "verification_status": verification_status,
        "certification_status": certification_status,
        "provisional_status": provisional_status,
        "candidate_rows": candidate_rows,
        "contests": contests,
        "coverage": coverage,
        "source_locators": source_locators,
        "notes": notes,
    }


def _source_manifest(raw_root: Path, rows: list[dict]) -> list[dict]:
    manifest = [
        _manifest_row(
            source_id="tx-2024-election-constants",
            state_code="TX",
            election_date="",
            stage="inventory",
            artifact_kind="official_vendor_election_inventory",
            authority="Texas Secretary of State linked results vendor",
            publication_url=TX_PUBLICATION,
            source_url=(
                "https://results.texas-election.com/static/data/"
                "ElectionConstants_382.json"
            ),
            acquisition_url=(
                "https://web.archive.org/web/20240730193019id_/"
                "https://results.texas-election.com/static/data/"
                "ElectionConstants_382.json"
            ),
            path=raw_root / "tx/2024/ElectionConstants_382.json",
            source_date="2024-07-30",
            verification_status="verified_official",
            certification_status="official_flags_verified",
            provisional_status="inventory_only",
            candidate_rows=0,
            contests=4,
            coverage="2024 Democratic/Republican primary and runoff election IDs",
            source_locators="$.electionInfo.2024",
            notes="All four recovered elections have the official flag O=Y.",
        ),
        _manifest_row(
            source_id="tx-2026-election-constants",
            state_code="TX",
            election_date="",
            stage="inventory",
            artifact_kind="official_public_api_election_inventory",
            authority="Texas Secretary of State linked Civix results service",
            publication_url=TX_PUBLICATION,
            source_url=f"{TX_2026_API_BASE}/electionConstants",
            acquisition_url=f"{TX_2026_API_BASE}/electionConstants",
            path=raw_root / "tx/2026/electionConstants.json",
            source_date="2026-09-22",
            verification_status="verified_official",
            certification_status="official_flags_verified",
            provisional_status="inventory_only",
            candidate_rows=0,
            contests=4,
            coverage="2026 Democratic/Republican primary and runoff election IDs",
            source_locators="$.upload(base64).electionInfo.2026",
            notes="All four recovered elections have the official flag O=Y.",
        ),
    ]
    for source in TX_2024_SOURCES:
        pdf_path = raw_root / source["pdf"]
        json_path = raw_root / source["json"]
        text_path = raw_root / source["text"]
        candidate_rows, contests = _source_counts(rows, source["source_id"])
        source_url = (
            f"{TX_2024_REPORT_BASE}/{source['election_id']}/{source['report_name']}"
        )
        archive_url = (
            f"https://web.archive.org/web/{source['archive_timestamp']}id_/"
            f"{source_url}"
        )
        manifest.append(_manifest_row(
            source_id=source["source_id"],
            state_code="TX",
            election_date=source["date"],
            stage=source["stage"],
            artifact_kind="official_canvass_pdf",
            authority="Texas Secretary of State",
            publication_url=TX_PUBLICATION,
            source_url=source_url,
            acquisition_url=archive_url,
            path=pdf_path,
            source_date=source["source_date"],
            verification_status="verified_official",
            certification_status="official_canvass",
            provisional_status="final_canvassed_totals",
            candidate_rows=candidate_rows,
            contests=contests,
            coverage="all congressional contests reported in this party/stage",
            source_locators="page numbers recorded per output row",
            notes=(
                "Archived capture of the exact state-linked vendor report; "
                "the original URL is preserved as source_url."
            ),
        ))
        manifest.append(_manifest_row(
            source_id=f"{source['source_id']}-candidate-ids",
            state_code="TX",
            election_date=source["date"],
            stage=source["stage"],
            artifact_kind="official_vendor_json_companion",
            authority="Texas Secretary of State linked results vendor",
            publication_url=TX_PUBLICATION,
            source_url=(
                f"{TX_2024_JSON_BASE}/{source['election_id']}/"
                f"{source['version']}/Federal.json"
            ),
            acquisition_url=(
                "https://web.archive.org/web/"
                f"{source['archive_timestamp']}id_/{TX_2024_JSON_BASE}/"
                f"{source['election_id']}/{source['version']}/Federal.json"
            ),
            path=json_path,
            source_date=source["source_date"],
            verification_status="verified_identity_companion",
            certification_status="official",
            provisional_status="not_used_for_vote_totals",
            candidate_rows=candidate_rows,
            contests=contests,
            coverage="candidate IDs and source spellings for the canvass report",
            source_locators="JSON pointers recorded per output row",
            notes=(
                "Used only for candidate IDs and full source names. PDF canvass "
                "totals supersede broken zero totals in the live 2024 Democratic JSON."
            ),
        ))
        manifest.append(_manifest_row(
            source_id=f"{source['source_id']}-text-extraction",
            state_code="TX",
            election_date=source["date"],
            stage=source["stage"],
            artifact_kind="derived_pdf_text",
            authority="Derived locally from official PDF",
            publication_url=TX_PUBLICATION,
            source_url=source_url,
            acquisition_url=archive_url,
            path=text_path,
            source_date=source["source_date"],
            verification_status="derived_parser_input",
            certification_status="inherits_pdf",
            provisional_status="inherits_pdf",
            candidate_rows=candidate_rows,
            contests=contests,
            coverage="text extraction for every PDF page",
            source_locators="form-feed PAGE markers preserve PDF page numbers",
            notes="Created with pypdf 6.16.0; output rows hash the PDF, not this text.",
        ))
    for source in TX_2026_SOURCES:
        path = raw_root / source["filename"]
        candidate_rows, contests = _source_counts(rows, source["source_id"])
        payload = json.loads(path.read_text(encoding="utf-8"))
        home = json.loads(base64.b64decode(payload["Home"]))
        manifest.append(_manifest_row(
            source_id=source["source_id"],
            state_code="TX",
            election_date=source["date"],
            stage=source["stage"],
            artifact_kind="official_public_api_json",
            authority="Texas Secretary of State linked Civix results service",
            publication_url=TX_PUBLICATION,
            source_url=f"{TX_2026_API_BASE}/election/{source['election_id']}",
            acquisition_url=f"{TX_2026_API_BASE}/election/{source['election_id']}",
            path=path,
            source_date=datetime.strptime(
                home["LastUpdatedTime"], "%b %d, %Y %H:%M:%S"
            ).date().isoformat(),
            verification_status="verified_official",
            certification_status="official",
            provisional_status="final_all_counties_reporting",
            candidate_rows=candidate_rows,
            contests=contests,
            coverage="all congressional contests reported in this party/stage",
            source_locators="base64-decoded JSON pointers recorded per output row",
            notes=(
                f"{home['CountiesReporting']['CR']} of "
                f"{home['CountiesReporting']['CT']} counties reporting."
            ),
        ))
    for source in PA_SOURCES:
        path = raw_root / source["filename"]
        readme_path = raw_root / source["readme"]
        certification_path = raw_root / source["certification"]
        candidate_rows, contests = _source_counts(rows, source["source_id"])
        manifest.append(_manifest_row(
            source_id=source["source_id"],
            state_code="PA",
            election_date=source["date"],
            stage=source["stage"],
            artifact_kind="official_precinct_returns",
            authority="Pennsylvania Department of State",
            publication_url=PA_PUBLICATION,
            source_url=source["url"],
            acquisition_url=source["url"],
            path=path,
            source_date=source["source_date"],
            verification_status="verified_official",
            certification_status="certified",
            provisional_status="certified_returns_include_eligible_provisional_ballots",
            candidate_rows=candidate_rows,
            contests=contests,
            coverage="all 67 counties; every congressional candidate record",
            source_locators="source line ranges recorded per output row",
            notes="Actual zero precinct totals are retained before aggregation.",
        ))
        manifest.append(_manifest_row(
            source_id=f"{source['source_id']}-schema",
            state_code="PA",
            election_date=source["date"],
            stage=source["stage"],
            artifact_kind="official_data_dictionary",
            authority="Pennsylvania Department of State",
            publication_url=PA_PUBLICATION,
            source_url=source["readme_url"],
            acquisition_url=source["readme_url"],
            path=readme_path,
            source_date=source["source_date"],
            verification_status="verified_official",
            certification_status="supports_certified_extract",
            provisional_status="schema_only",
            candidate_rows=0,
            contests=0,
            coverage="37-field precinct return schema and code tables",
            source_locators="field definitions and office/party code tables",
            notes="Documents extract date, record count, and field meanings.",
        ))
        manifest.append(_manifest_row(
            source_id=f"{source['source_id']}-certification",
            state_code="PA",
            election_date=source["date"],
            stage=source["stage"],
            artifact_kind="official_certification_notice",
            authority="Pennsylvania Department of State",
            publication_url=source["certification_url"],
            source_url=source["certification_url"],
            acquisition_url=source["certification_url"],
            path=certification_path,
            source_date="2024-06-03" if source["date"].startswith("2024") else "2026-06-17",
            verification_status="verified_official",
            certification_status="certified",
            provisional_status="post_audit_certification",
            candidate_rows=0,
            contests=0,
            coverage="state certification after receipt of all 67 county returns",
            source_locators="page title, dateline, and certification body text",
            notes="Confirms post-election audit and statewide certification status.",
        ))
    return manifest


def _attempt_rows() -> list[dict]:
    attempted_on = "2026-09-22"
    return [
        {
            "attempt_id": "tx24-01-state-archive",
            "attempted_on": attempted_on,
            "state_code": "TX",
            "cycle": "2024",
            "source_url": TX_PUBLICATION,
            "method": "follow official archive link to results application",
            "outcome": "success_publication_link",
            "raw_evidence": "discovery/tx-election-results-archive.html",
            "notes": "Established results.texas-election.com as the state-linked source.",
        },
        {
            "attempt_id": "tx24-02-legacy-portal",
            "attempted_on": attempted_on,
            "state_code": "TX",
            "cycle": "2024",
            "source_url": "https://elections.sos.state.tx.us/index.htm",
            "method": "inspect public historical election ID list",
            "outcome": "blocked_no_2024_records",
            "raw_evidence": "discovery/tx-legacy-election-index.html",
            "notes": "Public list ends at 2019 and cannot supply 2024 election IDs.",
        },
        {
            "attempt_id": "tx24-03-live-vendor-json",
            "attempted_on": attempted_on,
            "state_code": "TX",
            "cycle": "2024",
            "source_url": "https://results.texas-election.com/races",
            "method": "request public application and known static JSON",
            "outcome": "blocked_403_and_broken_democratic_totals",
            "raw_evidence": "tx/2024/election-49665-Federal.json",
            "notes": "Cloudflare blocks scripted page access; live Democratic JSON is all zero.",
        },
        {
            "attempt_id": "tx24-04-archived-canvass-reports",
            "attempted_on": attempted_on,
            "state_code": "TX",
            "cycle": "2024",
            "source_url": f"{TX_2024_REPORT_BASE}/49665/OfficialCanvassReport.pdf",
            "method": "recover archived official vendor canvass PDFs and JSON IDs",
            "outcome": "success_complete_primary_and_runoff",
            "raw_evidence": "tx/2024/tx-2024-dem-primary-official-canvass.pdf",
            "notes": "Recovered both parties' primary and runoff official reports.",
        },
        {
            "attempt_id": "tx26-01-state-archive",
            "attempted_on": attempted_on,
            "state_code": "TX",
            "cycle": "2026",
            "source_url": TX_PUBLICATION,
            "method": "follow official archive link to current Civix application",
            "outcome": "success_publication_link",
            "raw_evidence": "discovery/tx-election-results-archive.html",
            "notes": "Established goelection Civix service as the current linked source.",
        },
        {
            "attempt_id": "tx26-02-public-constants-api",
            "attempted_on": attempted_on,
            "state_code": "TX",
            "cycle": "2026",
            "source_url": f"{TX_2026_API_BASE}/electionConstants",
            "method": "call public application constants endpoint",
            "outcome": "success_election_ids_and_official_flags",
            "raw_evidence": "tx/2026/electionConstants.json",
            "notes": "Recovered party-specific primary and runoff IDs with O=Y.",
        },
        {
            "attempt_id": "tx26-03-public-election-api",
            "attempted_on": attempted_on,
            "state_code": "TX",
            "cycle": "2026",
            "source_url": f"{TX_2026_API_BASE}/election/53813",
            "method": "call four public election payload endpoints",
            "outcome": "success_complete_primary_and_runoff",
            "raw_evidence": "tx/2026/election-53813.json",
            "notes": "All 254 counties reported; federal summaries include candidate IDs.",
        },
        {
            "attempt_id": "pa24-01-public-returns-app",
            "attempted_on": attempted_on,
            "state_code": "PA",
            "cycle": "2024",
            "source_url": "https://www.electionreturns.pa.gov/",
            "method": "inspect public election returns application",
            "outcome": "blocked_incapsula",
            "raw_evidence": "",
            "notes": "No administrative or authenticated endpoint was attempted.",
        },
        {
            "attempt_id": "pa24-02-bulk-data",
            "attempted_on": attempted_on,
            "state_code": "PA",
            "cycle": "2024",
            "source_url": PA_2024_DATA_URL,
            "method": "download official precinct return extract and schema",
            "outcome": "success_complete_primary",
            "raw_evidence": "pa/2024/electionreturns_2024_primary_precinctreturns.txt",
            "notes": "All 67 counties and all 17 House districts plus Senate recovered.",
        },
        {
            "attempt_id": "pa24-03-certification",
            "attempted_on": attempted_on,
            "state_code": "PA",
            "cycle": "2024",
            "source_url": PA_SOURCES[0]["certification_url"],
            "method": "capture official post-audit certification notice",
            "outcome": "success_certified",
            "raw_evidence": "pa/2024/pa-2024-primary-certification.html",
            "notes": "Congressional races are not the cited state-house litigation exception.",
        },
        {
            "attempt_id": "pa26-01-bulk-data",
            "attempted_on": attempted_on,
            "state_code": "PA",
            "cycle": "2026",
            "source_url": PA_2026_DATA_URL,
            "method": "download official precinct return extract and schema",
            "outcome": "success_complete_primary",
            "raw_evidence": "pa/2026/electionreturns_2026_primary_precinctreturns.txt",
            "notes": "All 67 counties and all 17 House districts recovered; no Senate race.",
        },
        {
            "attempt_id": "pa26-02-certification",
            "attempted_on": attempted_on,
            "state_code": "PA",
            "cycle": "2026",
            "source_url": PA_SOURCES[1]["certification_url"],
            "method": "capture official post-audit certification notice",
            "outcome": "success_certified",
            "raw_evidence": "pa/2026/pa-2026-primary-certification.html",
            "notes": "Secretary certified results on June 17, 2026.",
        },
    ]


def _gap_rows(rows: list[dict]) -> list[dict]:
    output = []
    urls_by_state_year = {
        ("TX", "2024"): TX_PUBLICATION,
        ("TX", "2026"): TX_PUBLICATION,
        ("PA", "2024"): PA_2024_DATA_URL,
        ("PA", "2026"): PA_2026_DATA_URL,
    }
    for state in ("TX", "PA"):
        for cycle in ("2024", "2026"):
            state_rows = [
                row for row in rows
                if row["state_code"] == state and row["cycle"] == cycle
            ]
            for stage in ("primary", "primary_runoff"):
                stage_rows = [row for row in state_rows if row["stage"] == stage]
                applicable = state == "TX" or stage == "primary"
                output.append({
                    "gap_id": f"{state.casefold()}-{cycle}-{stage}",
                    "state_code": state,
                    "cycle": cycle,
                    "stage": stage,
                    "chamber": "House/Senate",
                    "coverage_status": "complete" if applicable else "not_applicable",
                    "recovered_scope": (
                        f"{len(stage_rows)} candidate rows across "
                        f"{len({row['contest_id'] for row in stage_rows})} contests"
                        if applicable else "Pennsylvania does not hold primary runoffs"
                    ),
                    "missing_scope": "",
                    "blocker": "",
                    "next_authoritative_step": "none",
                    "source_urls": urls_by_state_year[(state, cycle)],
                })
            output.append({
                "gap_id": f"{state.casefold()}-{cycle}-special-primary",
                "state_code": state,
                "cycle": cycle,
                "stage": "special_primary",
                "chamber": "House/Senate",
                "coverage_status": "not_applicable",
                "recovered_scope": (
                    "No congressional special primary in the official election inventory"
                ),
                "missing_scope": "",
                "blocker": "",
                "next_authoritative_step": "none",
                "source_urls": urls_by_state_year[(state, cycle)],
            })
    return output


def _contest_rows(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["contest_id"]].append(row)
    output = []
    for contest_id, candidates in sorted(groups.items()):
        first = candidates[0]
        output.append({
            "contest_id": contest_id,
            "state_code": first["state_code"],
            "cycle": first["cycle"],
            "election_date": first["election_date"],
            "stage": first["stage"],
            "chamber": first["chamber"],
            "district": first["district"],
            "primary_party": first["primary_party"],
            "candidate_count": len(candidates),
            "uncontested": len(candidates) == 1,
            "nonnumeric_result": False,
            "result_status": "actual_numeric",
            "certification_status": (
                "official_canvass" if first["state_code"] == "TX" else "certified"
            ),
            "source_id": first["source_id"],
        })
    return output


def _validate_output(rows: list[dict]) -> None:
    if not rows:
        raise ValueError("No Texas/Pennsylvania primary results generated")
    seen = set()
    for row in rows:
        if set(row) != set(FIELDS):
            raise ValueError(f"Output schema differs for {row.get('candidate_name')}")
        key = (row["contest_id"], row["candidate_source_id"])
        if key in seen:
            raise ValueError(f"Duplicate candidate result: {key}")
        seen.add(key)
        if not isinstance(row["votes"], int) or row["votes"] < 0:
            raise ValueError(f"Invalid candidate total: {row}")
        if len(row["source_sha256"]) != 64 or not row["source_locators"]:
            raise ValueError(f"Incomplete provenance: {row}")
    expected = {
        ("TX", "2024", "primary"),
        ("TX", "2024", "primary_runoff"),
        ("TX", "2026", "primary"),
        ("TX", "2026", "primary_runoff"),
        ("PA", "2024", "primary"),
        ("PA", "2026", "primary"),
    }
    actual = {(row["state_code"], row["cycle"], row["stage"]) for row in rows}
    if actual != expected:
        raise ValueError(f"State/year/stage coverage differs: {actual}")


def generate(
    raw_root: Path | None = None,
    analysis_root: Path | None = None,
) -> list[dict]:
    raw_root = raw_root or RAW_DIR / RAW_SUBDIR
    analysis_root = analysis_root or ANALYSIS_DATA_DIR / "congressional"
    _validate_texas_constants(raw_root)
    rows = []
    for source in TX_2024_SOURCES:
        rows.extend(parse_texas_canvass(
            raw_root / source["text"],
            raw_root / source["pdf"],
            raw_root / source["json"],
            source,
        ))
    for source in TX_2026_SOURCES:
        rows.extend(parse_texas_api(raw_root / source["filename"], source))
    for source in PA_SOURCES:
        rows.extend(parse_pennsylvania(raw_root / source["filename"], source))
    rows.sort(key=lambda row: (
        row["state_code"],
        row["election_date"],
        row["stage"],
        row["chamber"],
        row["district"],
        row["primary_party"],
        row["candidate_name"],
    ))
    _validate_output(rows)
    write_csv(analysis_root / RESULT_FILENAME, rows, FIELDS)
    manifest_dir = analysis_root / MANIFEST_SUBDIR
    write_csv(
        manifest_dir / "source_manifest.csv",
        _source_manifest(raw_root, rows),
        SOURCE_MANIFEST_FIELDS,
    )
    write_csv(manifest_dir / "attempt_ledger.csv", _attempt_rows(), ATTEMPT_FIELDS)
    write_csv(manifest_dir / "unresolved_gaps.csv", _gap_rows(rows), GAP_FIELDS)
    write_csv(
        manifest_dir / "contest_manifest.csv",
        _contest_rows(rows),
        CONTEST_FIELDS,
    )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate official Texas/Pennsylvania congressional primary results"
    )
    parser.parse_args()
    rows = generate()
    print(
        f"Wrote {len(rows)} candidate results to "
        f"{ANALYSIS_DATA_DIR / 'congressional' / RESULT_FILENAME}"
    )


if __name__ == "__main__":
    main()
