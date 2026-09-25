"""Parse recovered New York and Michigan congressional primary records."""

import argparse
import csv
import hashlib
import html
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

from .io import write_csv
from .paths import ANALYSIS_DATA_DIR, RAW_DIR
from .state_results import FIELDS

RAW_SUBDIR = "ny_mi_primaries"
RESULT_FILENAME = "ny_mi_primary_results.csv"
ROSTER_FILENAME = "ny_mi_primary_rosters.csv"
PARTIAL_RESULT_FILENAME = "ny_mi_primary_partial_results.csv"

ACCOUNTING_FIELDS = [
    "cycle",
    "state_code",
    "chamber",
    "district",
    "primary_party",
    "status",
    "candidate_rows",
    "reporting_units",
    "source_ids",
    "notes",
]

COUNTY_ACCOUNTING_FIELDS = [
    "district",
    "primary_party",
    "county",
    "contest_status",
    "county_source_status",
    "source_url",
    "raw_filename",
    "notes",
]

MI_RESULT_SOURCES = (
    {
        "source_id": "mi-2024-primary-results",
        "state": "MI",
        "date": "2024-08-06",
        "filename": "mi-2024-primary-results.tsv",
        "url": (
            "https://mvic.sos.state.mi.us/VoteHistory/"
            "GetElectionResultFile?electionId=698"
        ),
        "publication": (
            "https://mvic.sos.state.mi.us/votehistory/"
            "Index?type=C&electionDate=8-6-2024"
        ),
    },
    {
        "source_id": "mi-2026-primary-results",
        "state": "MI",
        "date": "2026-08-04",
        "filename": "mi-2026-primary-results.tsv",
        "url": (
            "https://mvic.sos.state.mi.us/VoteHistory/"
            "GetElectionResultFile?electionId=706"
        ),
        "publication": (
            "https://mvic.sos.state.mi.us/votehistory/"
            "Index?type=C&electionDate=8-4-2026"
        ),
    },
)

NY_2024_RESULT_SOURCE = {
    "source_id": "ny-2024-election-database-search",
    "state": "NY",
    "date": "2024-06-25",
    "filename": "ny-2024-election-database-search.csv",
    "url": (
        "https://ny.elstats.civera.com/api/download_search.csv?"
        "search=%7B%22global%22%3A%7B%22years%22%3A%7B%22from%22%3A2024%2C"
        "%22to%22%3A2024%7D%7D%2C%22ballotQuestions%22%3A%7B%22text%22%3A"
        "%22%22%2C%22types%22%3A%5B%5D%2C%22number%22%3A%22%22%2C"
        "%22divisions%22%3A%5B%5D%7D%2C%22contests%22%3A%7B%22candidates"
        "%22%3A%5B%5D%2C%22offices%22%3A%5B%5D%2C%22divisions%22%3A%5B"
        "%5D%7D%2C%22voterStats%22%3Afalse%2C%22stages%22%3A%5B%5D%2C"
        "%22specialElectionsOnly%22%3Afalse%7D"
    ),
    "publication": "https://results.elections.ny.gov/search?df=2024&dt=2024&p=1",
    "expected_contests": {"5566", "5567", "5568", "5580"},
}

NY_2024_ROSTER_SOURCE = {
    "source_id": "ny-2024-primary-certification",
    "state": "NY",
    "date": "2024-06-25",
    "filename": "ny-2024-primary-certification-congressional.csv",
    "source_pdf": "ny-2024-primary-certification.pdf",
    "url": "https://elections.ny.gov/certification-june-25-2024-primary-election",
    "publication": "https://elections.ny.gov/node/306",
}

NY_2026_ROSTER_SOURCE = {
    "source_id": "ny-2026-primary-certification",
    "state": "NY",
    "date": "2026-06-23",
    "filename": "ny-2026-primary-certification-congressional.csv",
    "source_pdf": "ny-2026-primary-certification.pdf",
    "url": (
        "https://elections.ny.gov/system/files/documents/2026/05/"
        "accessible-june-23-2026-primary-certification-amended-5.13.26_0.pdf"
    ),
    "publication": "https://elections.ny.gov/certification-june-23-2026-primary-election",
}

NYC_RESULT_SOURCES = (
    {
        "source_id": "nyc-2024-cd10-dem",
        "date": "2024-06-25",
        "year": 2024,
        "district": "10",
        "party": "Democratic",
        "reporting_units": 2,
        "filename": (
            "nyc/nyc-2024-01001900010Crossover_Democratic_Representative_in_"
            "Congress_10th_Congressional_District_Recap.csv"
        ),
    },
    {
        "source_id": "nyc-2024-cd14-dem",
        "date": "2024-06-25",
        "year": 2024,
        "district": "14",
        "party": "Democratic",
        "reporting_units": 2,
        "filename": (
            "nyc/nyc-2024-01001900014Crossover_Democratic_Representative_in_"
            "Congress_14th_Congressional_District_Recap.csv"
        ),
    },
    *(
        {
            "source_id": f"nyc-2026-cd{district}-dem",
            "date": "2026-06-23",
            "year": 2026,
            "district": district,
            "party": "Democratic",
            "reporting_units": units,
            "filename": filename,
        }
        for district, units, filename in (
            (
                "07", 2, "nyc/nyc-2026-01001600007Crossover_Democratic_"
                "Representative_in_Congress_7th_Congressional_District_Recap.csv",
            ),
            (
                "10", 2, "nyc/nyc-2026-01001600010Crossover_Democratic_"
                "Representative_in_Congress_10th_Congressional_District_Recap.csv",
            ),
            (
                "11", 2, "nyc/nyc-2026-01001600011Crossover_Democratic_"
                "Representative_in_Congress_11th_Congressional_District_Recap.csv",
            ),
            (
                "13", 2, "nyc/nyc-2026-01001600013Crossover_Democratic_"
                "Representative_in_Congress_13th_Congressional_District_Recap.csv",
            ),
            (
                "14", 2, "nyc/nyc-2026-01001600014Crossover_Democratic_"
                "Representative_in_Congress_14th_Congressional_District_Recap.csv",
            ),
            (
                "12", 1, "nyc/nyc-2026-01101600012New_York_Democratic_"
                "Representative_in_Congress_12th_Congressional_District_Recap.csv",
            ),
            (
                "15", 1, "nyc/nyc-2026-01201600015Bronx_Democratic_"
                "Representative_in_Congress_15th_Congressional_District_Recap.csv",
            ),
            (
                "09", 1, "nyc/nyc-2026-01301600009Kings_Democratic_"
                "Representative_in_Congress_9th_Congressional_District_Recap.csv",
            ),
            (
                "06", 1, "nyc/nyc-2026-01401600006Queens_Democratic_"
                "Representative_in_Congress_6th_Congressional_District_Recap.csv",
            ),
        )
    ),
)

SUFFOLK_RESULT_SOURCES = (
    {
        "source_id": "suffolk-2024-cd01-dem",
        "date": "2024-06-25",
        "district": "01",
        "party": "Democratic",
        "filename": "suffolk/suffolk-2024-primary-democratic.html",
        "url": "https://apps2.suffolkcountyny.gov/boe/eleres/24pe/DEMs.htm",
    },
    {
        "source_id": "suffolk-2026-cd01-dem",
        "date": "2026-06-23",
        "district": "01",
        "party": "Democratic",
        "filename": "suffolk/suffolk-2026-primary-DEMs.html",
        "url": "https://apps2.suffolkcountyny.gov/boe/eleres/26pe/DEMs.htm",
    },
)

NY_2026_CD17_SOURCE = {
    "source_id": "ny-2026-cd17-certified-county-canvass",
    "date": "2026-06-23",
    "district": "17",
    "party": "Democratic",
    "json_counties": ("putnam", "rockland", "westchester"),
    "dutchess_filename": "counties/dutchess-2026-cd17-certified.csv",
    "dutchess_pdf": "counties/dutchess-2026-primary-detailed.pdf",
}

MANIFEST_FIELDS = [
    "source_id",
    "state_code",
    "election_date",
    "artifact_kind",
    "authority",
    "publication_url",
    "source_url",
    "raw_filename",
    "sha256",
    "acquisition_status",
    "verification_status",
    "candidate_rows",
    "contests",
    "coverage",
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
    "chamber",
    "requested_artifact",
    "coverage_status",
    "recovered_scope",
    "missing_scope",
    "blocker",
    "next_authoritative_step",
    "source_urls",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _votes(value: str) -> int:
    text = value.strip().replace(",", "")
    if not text or not text.isdigit():
        raise ValueError(f"Invalid vote total: {value!r}")
    return int(text)


def _candidate_name(first: str, middle: str, last: str) -> str:
    return " ".join(part.strip() for part in (first, middle, last) if part.strip())


def _locator_ranges(locators: list[str]) -> str:
    files: dict[str, set[int]] = defaultdict(set)
    for locator in locators:
        filename, number = locator.rsplit(":", 1)
        files[filename].add(int(number))
    output = []
    for filename, numbers in sorted(files.items()):
        ranges = []
        start = end = None
        for number in sorted(numbers):
            if start is None:
                start = end = number
            elif number == end + 1:
                end = number
            else:
                ranges.append(str(start) if start == end else f"{start}-{end}")
                start = end = number
        ranges.append(str(start) if start == end else f"{start}-{end}")
        output.append(f"{filename}:{','.join(ranges)}")
    return " | ".join(output)


def parse_michigan_results(path: Path, source: dict) -> list[dict]:
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    seen = set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        turnout = next(handle, "").strip()
        if not turnout.startswith("TOTAL VOTER TURNOUT:"):
            raise ValueError("Michigan export is missing the turnout preamble")
        reader = csv.DictReader(handle, delimiter="\t")
        required = {
            "ElectionDate",
            "DistrictCode(Text)",
            "CountyCode",
            "OfficeDescription",
            "PartyDescription",
            "CandidateID",
            "CandidateLastName",
            "CandidateFirstName",
            "CandidateMiddleName",
            "CandidateVotes",
            "WriteIn(W)/Uncommitted(Z)",
        }
        if not required <= set(reader.fieldnames or []):
            raise ValueError("Michigan election-result schema changed")
        for line_number, row in enumerate(reader, 3):
            office = (row["OfficeDescription"] or "").strip()
            senate = office.startswith("UNITED STATES SENATOR")
            house = re.fullmatch(
                r"(\d+)(?:ST|ND|RD|TH) DISTRICT REPRESENTATIVE IN CONGRESS "
                r"2 YEAR TERM \(1\) POSITION",
                office,
                re.I,
            )
            if not senate and house is None:
                continue
            if row["ElectionDate"] != source["date"]:
                raise ValueError("Michigan export contains a different election date")
            chamber = "Senate" if senate else "House"
            district = "S" if senate else house[1].zfill(2)
            candidate_id = (row["CandidateID"] or "").strip()
            if not candidate_id:
                raise ValueError(f"Michigan candidate lacks an ID at line {line_number}")
            party = (row["PartyDescription"] or "").strip().title()
            write_in = (row["WriteIn(W)/Uncommitted(Z)"] or "").strip() == "Y"
            name = _candidate_name(
                row["CandidateFirstName"] or "",
                row["CandidateMiddleName"] or "",
                row["CandidateLastName"] or "",
            )
            if write_in and not name:
                name = "Write-In"
            if not name:
                raise ValueError(f"Michigan candidate lacks a name at line {line_number}")
            key = (office, party, candidate_id)
            unit = (row["CountyCode"] or "").strip()
            duplicate = (*key, unit)
            if duplicate in seen:
                raise ValueError(f"Duplicate Michigan county result: {duplicate}")
            seen.add(duplicate)
            groups[key].append({
                "name": name,
                "party": party,
                "candidate_id": candidate_id,
                "chamber": chamber,
                "district": district,
                "write_in": write_in,
                "votes": _votes(row["CandidateVotes"] or ""),
                "unit": unit,
                "locator": f"{path.name}:{line_number}",
            })
    source_hash = _sha256(path)
    output = []
    for (office, party, candidate_id), rows in sorted(groups.items()):
        identities = {
            (row["name"], row["chamber"], row["district"], row["write_in"])
            for row in rows
        }
        if len(identities) != 1:
            raise ValueError(f"Inconsistent Michigan candidate identity: {candidate_id}")
        name, chamber, district, write_in = next(iter(identities))
        contest_id = "-".join((
            "mi",
            source["date"],
            chamber.lower(),
            district.lower(),
            "regular",
            party.lower().replace(" ", "-"),
        ))
        output.append({
            "contest_id": contest_id,
            "cycle": source["date"][:4],
            "election_date": source["date"],
            "stage": "primary",
            "state_code": "MI",
            "chamber": chamber,
            "district": district,
            "term": "regular",
            "election_system": "partisan_primary",
            "primary_party": party,
            "candidate_name": name,
            "candidate_source_id": candidate_id,
            "party": "" if write_in else party,
            "write_in": write_in,
            "votes": sum(row["votes"] for row in rows),
            "source_id": source["source_id"],
            "source_url": source["url"],
            "source_sha256": source_hash,
            "source_locators": _locator_ranges([row["locator"] for row in rows]),
            "reporting_units": len(rows),
        })
    house_districts = {row["district"] for row in output if row["chamber"] == "House"}
    if house_districts != {f"{number:02}" for number in range(1, 14)}:
        raise ValueError("Michigan export does not cover all 13 House districts")
    if not any(row["chamber"] == "Senate" for row in output):
        raise ValueError("Michigan export is missing the U.S. Senate primary")
    return output


def parse_new_york_results(path: Path, source: dict) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    seen = set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {
            "contest_id",
            "election_date",
            "election_type",
            "primary_party",
            "office_name",
            "district_name",
            "candidate_id",
            "candidate_name",
            "division_id",
            "division_name",
            "candidate_party_name",
            "votes",
        }
        if not required <= set(reader.fieldnames or []):
            raise ValueError("New York election-database schema changed")
        for line_number, row in enumerate(reader, 2):
            if not row["election_date"].startswith(source["date"]):
                continue
            if row["election_type"] != "Primary":
                continue
            if row["office_name"] not in {"Representative in Congress", "United States Senator"}:
                continue
            if row["candidate_name"] in {"Total Votes", "Blank", "Void"}:
                continue
            contest_id = row["contest_id"]
            candidate_id = row["candidate_id"]
            unit = row["division_id"]
            duplicate = (contest_id, candidate_id, unit)
            if duplicate in seen:
                raise ValueError(f"Duplicate New York division result: {duplicate}")
            seen.add(duplicate)
            chamber = "Senate" if row["office_name"] == "United States Senator" else "House"
            district = "S" if chamber == "Senate" else row["district_name"].zfill(2)
            write_in = row["candidate_name"] == "Scattering"
            party = row["candidate_party_name"] or row["primary_party"]
            groups[(contest_id, candidate_id)].append({
                "name": row["candidate_name"],
                "party": party,
                "primary_party": row["primary_party"],
                "chamber": chamber,
                "district": district,
                "write_in": write_in,
                "votes": _votes(row["votes"]),
                "unit": unit,
                "locator": f"{path.name}:{line_number}",
            })
    contests = {contest for contest, _candidate in groups}
    if contests != source["expected_contests"]:
        raise ValueError(
            f"New York certified-result contest coverage changed: {sorted(contests)}"
        )
    source_hash = _sha256(path)
    output = []
    for (official_contest_id, candidate_id), rows in sorted(groups.items()):
        identities = {
            (
                row["name"],
                row["party"],
                row["primary_party"],
                row["chamber"],
                row["district"],
                row["write_in"],
            )
            for row in rows
        }
        if len(identities) != 1:
            raise ValueError(f"Inconsistent New York candidate identity: {candidate_id}")
        name, party, primary_party, chamber, district, write_in = next(iter(identities))
        contest_id = "-".join((
            "ny",
            source["date"],
            chamber.lower(),
            district.lower(),
            "regular",
            primary_party.lower().replace(" ", "-"),
        ))
        output.append({
            "contest_id": contest_id,
            "cycle": source["date"][:4],
            "election_date": source["date"],
            "stage": "primary",
            "state_code": "NY",
            "chamber": chamber,
            "district": district,
            "term": "regular",
            "election_system": "partisan_primary",
            "primary_party": primary_party,
            "candidate_name": name,
            "candidate_source_id": candidate_id,
            "party": party,
            "write_in": write_in,
            "votes": sum(row["votes"] for row in rows),
            "source_id": source["source_id"],
            "source_url": source["url"],
            "source_sha256": source_hash,
            "source_locators": _locator_ranges([row["locator"] for row in rows]),
            "reporting_units": len(rows),
        })
    return output


def parse_new_york_roster(path: Path, source_pdf: Path, source: dict) -> list[dict]:
    rows = []
    source_hash = _sha256(source_pdf)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"page", "office", "district", "party", "ballot_order", "candidate_name"}
        if not required <= set(reader.fieldnames or []):
            raise ValueError("New York certification extraction schema changed")
        for row_number, row in enumerate(reader, 2):
            chamber = "Senate" if row["office"] == "U.S. Senator" else "House"
            if chamber == "House" and row["office"] != "Representative in Congress":
                continue
            district = "S" if chamber == "Senate" else row["district"].zfill(2)
            party = row["party"].strip()
            name = row["candidate_name"].strip()
            contest_id = "-".join((
                "ny",
                source["date"],
                chamber.lower(),
                district.lower(),
                "regular",
                party.lower().replace(" ", "-"),
            ))
            source_candidate_id = "-".join((
                "cert",
                row["page"],
                party.lower().replace(" ", "-"),
                row["ballot_order"].lower().replace(" ", "-"),
                re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
            ))
            rows.append({
                "contest_id": contest_id,
                "cycle": source["date"][:4],
                "election_date": source["date"],
                "stage": "primary_roster",
                "state_code": "NY",
                "chamber": chamber,
                "district": district,
                "term": "regular",
                "election_system": "partisan_primary",
                "primary_party": party,
                "candidate_name": name,
                "candidate_source_id": source_candidate_id,
                "party": party,
                "write_in": False,
                "votes": "",
                "source_id": source["source_id"],
                "source_url": source["url"],
                "source_sha256": source_hash,
                "source_locators": f"{source_pdf.name}:page-{row['page']}",
                "reporting_units": "",
            })
    if not rows:
        raise ValueError("New York certification extraction contains no congressional rows")
    return rows


def _nyc_source_url(source: dict) -> str:
    basename = Path(source["filename"]).name.removeprefix(f"nyc-{source['year']}-")
    basename = basename.replace("_", " ")
    election = source["date"].replace("-", "")
    return (
        "https://www.vote.nyc/sites/default/files/pdf/election_results/"
        f"{source['year']}/{election}Primary%20Election/{quote(basename)}"
    )


def parse_nyc_results(path: Path, source: dict) -> list[dict]:
    contest_label = (
        f"Total for Democratic Representative in Congress "
        f"({int(source['district'])}th Congressional District)"
    )
    candidates = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for line_number, row in enumerate(csv.reader(handle), 1):
            if len(row) < 6 or not row[3].startswith("Total for "):
                continue
            if "Representative in Congress" not in row[3]:
                continue
            if not row[3].startswith(contest_label):
                raise ValueError(f"Unexpected NYC contest label at {path.name}:{line_number}")
            name = row[4].strip()
            if not name or name in {
                "Public Counter",
                "Manually Counted Emergency",
                "Absentee / Military",
                "Federal",
                "Affidavit",
            }:
                continue
            write_in = name.endswith(" (Write-In)")
            if write_in:
                name = name.removesuffix(" (Write-In)").strip()
            candidates.append({
                "name": name,
                "votes": _votes(row[5]),
                "write_in": write_in,
                "locator": f"{path.name}:{line_number}",
            })
    if len(candidates) < 2:
        raise ValueError(f"NYC certified recap lacks candidates: {path.name}")
    names = [row["name"] for row in candidates]
    if len(names) != len(set(names)):
        raise ValueError(f"NYC certified recap has duplicate candidate names: {path.name}")
    source_hash = _sha256(path)
    party = source["party"]
    district = source["district"].zfill(2)
    contest_id = (
        f"ny-{source['date']}-house-{district}-regular-"
        f"{party.lower().replace(' ', '-')}"
    )
    source_url = _nyc_source_url(source)
    return [
        {
            "contest_id": contest_id,
            "cycle": source["date"][:4],
            "election_date": source["date"],
            "stage": "primary",
            "state_code": "NY",
            "chamber": "House",
            "district": district,
            "term": "regular",
            "election_system": "partisan_primary",
            "primary_party": party,
            "candidate_name": row["name"],
            "candidate_source_id": (
                f"nyc-{source['date']}-{district}-{party.lower()}-"
                f"{row['locator'].rsplit(':', 1)[1]}-"
                f"{re.sub(r'[^a-z0-9]+', '-', row['name'].lower()).strip('-')}"
            ),
            "party": "" if row["write_in"] else party,
            "write_in": row["write_in"],
            "votes": row["votes"],
            "source_id": source["source_id"],
            "source_url": source_url,
            "source_sha256": source_hash,
            "source_locators": row["locator"],
            "reporting_units": source["reporting_units"],
        }
        for row in candidates
    ]


def parse_suffolk_results(path: Path, source: dict) -> list[dict]:
    text = path.read_text(errors="replace")
    district_number = int(source["district"])
    pattern = re.compile(
        rf"<h2[^>]*>.*?Representative in Congress,\s*{district_number}"
        rf"(?:st|nd|rd|th) Congressional District.*?"
        rf"\({re.escape(source['party'])} Party\).*?</h2>",
        re.I | re.S,
    )
    heading = pattern.search(text)
    if heading is None:
        raise ValueError(f"Suffolk congressional contest not found: {path.name}")
    first_table_end = text.find("</table>", heading.end())
    table_match = re.search(
        r"<table[^>]*>(.*?)</table>",
        text[first_table_end + len("</table>"):],
        re.I | re.S,
    )
    if table_match is None:
        raise ValueError(f"Suffolk candidate table not found: {path.name}")
    candidates = []
    for row_number, tr in enumerate(
        re.findall(r"<tr[^>]*>(.*?)</tr>", table_match[1], re.I | re.S)[1:],
        1,
    ):
        cells = [
            re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cell))).strip()
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.I | re.S)
        ]
        if len(cells) < 3:
            continue
        source_name, party, votes = cells[:3]
        write_in = source_name.upper().startswith("WRITE-IN")
        if "," in source_name and not write_in:
            last, rest = source_name.split(",", 1)
            name = f"{rest.strip()} {last.strip()}"
        else:
            name = source_name.title() if write_in else source_name
        candidates.append({
            "name": name,
            "party": party,
            "votes": _votes(votes),
            "write_in": write_in,
            "locator": f"{path.name}:candidate-row-{row_number}",
        })
    if len(candidates) < 2:
        raise ValueError(f"Suffolk result table lacks candidates: {path.name}")
    source_hash = _sha256(path)
    district = source["district"].zfill(2)
    party = source["party"]
    contest_id = (
        f"ny-{source['date']}-house-{district}-regular-"
        f"{party.lower().replace(' ', '-')}"
    )
    return [
        {
            "contest_id": contest_id,
            "cycle": source["date"][:4],
            "election_date": source["date"],
            "stage": "primary",
            "state_code": "NY",
            "chamber": "House",
            "district": district,
            "term": "regular",
            "election_system": "partisan_primary",
            "primary_party": party,
            "candidate_name": row["name"],
            "candidate_source_id": (
                f"suffolk-{source['date']}-{district}-"
                f"{re.sub(r'[^a-z0-9]+', '-', row['name'].lower()).strip('-')}"
            ),
            "party": row["party"] or party,
            "write_in": row["write_in"],
            "votes": row["votes"],
            "source_id": source["source_id"],
            "source_url": source["url"],
            "source_sha256": source_hash,
            "source_locators": row["locator"],
            "reporting_units": 1,
        }
        for row in candidates
    ]


def parse_ny_cd17_county_canvass(raw_dir: Path, source: dict) -> list[dict]:
    expected = {
        "Effie Guadalupe Phillips-Staley",
        "Cait Conley",
        "Beth Davidson",
        "John Cappello",
        "Michael Sacks",
        "Write-in",
    }
    totals = defaultdict(int)
    locators = defaultdict(list)
    paths = []
    source_urls = []
    for county in source["json_counties"]:
        metadata_path = (
            raw_dir / "counties" / "enhanced" / f"{county}-county-ny-PE26-metadata.json"
        )
        data_path = (
            raw_dir / "counties" / "enhanced" / f"{county}-county-ny-PE26-data.json"
        )
        metadata = json.loads(metadata_path.read_text())
        data = json.loads(data_path.read_text())
        if metadata.get("isOfficialResults") is not True:
            raise ValueError(f"{county} results are not marked official")
        if metadata.get("electionDate") != source["date"]:
            raise ValueError(f"{county} result date changed")
        contest = next(
            item for item in data["ballotItems"]
            if "Congress" in item["name"][0]["text"] and "17" in item["name"][0]["text"]
        )
        for option in contest["summaryResults"]["ballotOptions"]:
            name = option["name"][0]["text"].strip()
            if option["isWriteIn"]:
                name = "Write-in"
            elif name.startswith("Effie Guadalupe Phillips-"):
                name = "Effie Guadalupe Phillips-Staley"
            if name not in expected:
                raise ValueError(f"Unexpected CD17 candidate from {county}: {name}")
            totals[name] += int(option["voteCount"])
            locators[name].append(f"{data_path.name}:ballot-option-{option['id']}")
        paths.extend((metadata_path, data_path))
        source_urls.append(
            "https://app.enhancedvoting.com/results/public/api/elections/"
            f"{county}-county-ny/PE26/data"
        )
    dutchess_path = raw_dir / source["dutchess_filename"]
    dutchess_pdf = raw_dir / source["dutchess_pdf"]
    with dutchess_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["candidate_name"] not in expected:
                raise ValueError(f"Unexpected Dutchess CD17 candidate: {row['candidate_name']}")
            totals[row["candidate_name"]] += _votes(row["votes"])
            locators[row["candidate_name"]].append(row["source_locator"])
    paths.extend((dutchess_path, dutchess_pdf))
    source_urls.append(
        "https://elections.dutchessny.gov/wp-content/uploads/2026/07/"
        "Detailed-Results-by-Contest-Table-7-10.pdf"
    )
    if set(totals) != expected:
        raise ValueError(f"CD17 county canvass coverage changed: {sorted(totals)}")
    if sum(totals.values()) != 46_955:
        raise ValueError("CD17 all-county candidate total changed")
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.read_bytes())
    district = source["district"]
    party = source["party"]
    contest_id = f"ny-{source['date']}-house-{district}-regular-democratic"
    return [
        {
            "contest_id": contest_id,
            "cycle": "2026",
            "election_date": source["date"],
            "stage": "primary",
            "state_code": "NY",
            "chamber": "House",
            "district": district,
            "term": "regular",
            "election_system": "partisan_primary",
            "primary_party": party,
            "candidate_name": name,
            "candidate_source_id": (
                f"ny-cd17-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}"
            ),
            "party": "" if name == "Write-in" else party,
            "write_in": name == "Write-in",
            "votes": totals[name],
            "source_id": source["source_id"],
            "source_url": " | ".join(source_urls),
            "source_sha256": digest.hexdigest(),
            "source_locators": " | ".join(locators[name]),
            "reporting_units": 4,
        }
        for name in sorted(totals)
    ]


def parse_ny_enr_partial(path: Path) -> list[dict]:
    target = {
        ("DEM", "3"),
        ("REP", "3"),
        ("REP", "4"),
        ("REP", "19"),
        ("DEM", "21"),
        ("REP", "21"),
        ("DEM", "23"),
        ("DEM", "24"),
        ("DEM", "25"),
    }
    party_names = {"DEM": "Democratic", "REP": "Republican"}
    lines = path.read_text(encoding="utf-8").splitlines()
    source_hash = _sha256(path)
    output = []
    for index, line in enumerate(lines):
        match = re.search(
            r"(DEM|REP) Primary > (\d+)(?:st|nd|rd|th) Congressional District"
            r".*Reporting: ([\d,]+) of ([\d,]+)",
            line,
        )
        if match is None or (match[1], match[2]) not in target:
            continue
        party = party_names[match[1]]
        district = match[2].zfill(2)
        reported = _votes(match[3])
        expected = _votes(match[4])
        contest_id = (
            f"ny-2026-06-23-house-{district}-regular-"
            f"{party.lower().replace(' ', '-')}"
        )
        for row_number in range(index + 1, len(lines)):
            candidate_line = lines[row_number].strip()
            if candidate_line.startswith("Total Votes"):
                break
            if not candidate_line or candidate_line.startswith("Candidate"):
                continue
            cells = candidate_line.split("\t")
            name = cells[0].strip()
            if name in {"Blank", "Void"}:
                continue
            votes = _votes(cells[-1])
            write_in = name == "Write-in"
            output.append({
                "contest_id": contest_id,
                "cycle": "2026",
                "election_date": "2026-06-23",
                "stage": "primary",
                "state_code": "NY",
                "chamber": "House",
                "district": district,
                "term": "regular",
                "election_system": "partisan_primary",
                "primary_party": party,
                "candidate_name": name,
                "candidate_source_id": (
                    f"ny-enr-{district}-{match[1].lower()}-{row_number + 1}-"
                    f"{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}"
                ),
                "party": "" if write_in else party,
                "write_in": write_in,
                "votes": votes,
                "source_id": "ny-2026-enr-uncertified",
                "source_url": "https://nyenr.elections.ny.gov/HomeNoJS.aspx",
                "source_sha256": source_hash,
                "source_locators": f"{path.name}:{row_number + 1}",
                "reporting_units": reported,
                "_expected_reporting_units": expected,
            })
    if {row["contest_id"] for row in output} != {
        f"ny-2026-06-23-house-{district.zfill(2)}-regular-"
        f"{party_names[party].lower()}"
        for party, district in target
    }:
        raise ValueError("New York ENR partial contest inventory changed")
    return output


def _contest_accounting(
    results: list[dict],
    partial: list[dict],
    raw_dir: Path,
) -> list[dict]:
    rows = []
    for status, records in (
        ("complete_certified_results", results),
        ("partial_official_uncertified", partial),
    ):
        groups = defaultdict(list)
        for row in records:
            groups[row["contest_id"]].append(row)
        for contest_id, group in groups.items():
            first = group[0]
            expected = max(
                (int(row.get("_expected_reporting_units", 0)) for row in group),
                default=0,
            )
            reported = max(int(row["reporting_units"] or 0) for row in group)
            notes = ""
            if status == "partial_official_uncertified":
                notes = (
                    f"Authority-hosted election-night total; ED reporting "
                    f"{reported} of {expected}; excluded from successful results."
                )
            rows.append({
                "cycle": first["cycle"],
                "state_code": first["state_code"],
                "chamber": first["chamber"],
                "district": first["district"],
                "primary_party": first["primary_party"],
                "status": status,
                "candidate_rows": len(group),
                "reporting_units": (
                    f"{reported}/{expected}" if expected else str(reported)
                ),
                "source_ids": " | ".join(sorted({row["source_id"] for row in group})),
                "notes": notes,
            })
    known = {
        (row["cycle"], row["district"], row["primary_party"])
        for row in rows
        if row["state_code"] == "NY"
    }
    for source in (NY_2024_ROSTER_SOURCE, NY_2026_ROSTER_SOURCE):
        path = raw_dir / source["filename"]
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row["ballot_order"] != "Uncontested":
                    continue
                chamber = "Senate" if row["office"] == "U.S. Senator" else "House"
                district = "S" if chamber == "Senate" else row["district"].zfill(2)
                key = (source["date"][:4], district, row["party"])
                if key in known:
                    continue
                known.add(key)
                rows.append({
                    "cycle": source["date"][:4],
                    "state_code": "NY",
                    "chamber": chamber,
                    "district": district,
                    "primary_party": row["party"],
                    "status": "official_uncontested_roster",
                    "candidate_rows": 1,
                    "reporting_units": "",
                    "source_ids": source["source_id"],
                    "notes": (
                        "Explicitly marked Uncontested in the official pre-election "
                        "certification; no vote result is inferred."
                    ),
                })
    return sorted(rows, key=lambda row: (
        row["cycle"],
        row["state_code"],
        row["chamber"],
        row["district"],
        row["primary_party"],
        row["status"],
    ))


def _county_canvass_accounting() -> list[dict]:
    contests = {
        ("03", "Democratic"): ("Nassau", "Queens", "Suffolk"),
        ("03", "Republican"): ("Nassau", "Queens", "Suffolk"),
        ("04", "Republican"): ("Nassau",),
        ("17", "Democratic"): ("Putnam", "Rockland", "Dutchess", "Westchester"),
        ("19", "Republican"): (
            "Broome", "Chenango", "Columbia", "Delaware", "Greene", "Otsego",
            "Sullivan", "Tompkins", "Cortland", "Rensselaer", "Ulster",
        ),
        ("21", "Democratic"): (
            "Clinton", "Essex", "Franklin", "Fulton", "Hamilton", "Herkimer",
            "Lewis", "St. Lawrence", "Schoharie", "Warren", "Washington",
            "Jefferson", "Montgomery", "Oneida", "Saratoga",
        ),
        ("21", "Republican"): (
            "Clinton", "Essex", "Franklin", "Fulton", "Hamilton", "Herkimer",
            "Lewis", "St. Lawrence", "Schoharie", "Warren", "Washington",
            "Jefferson", "Montgomery", "Oneida", "Saratoga",
        ),
        ("23", "Democratic"): (
            "Allegany", "Cattaraugus", "Chautauqua", "Chemung", "Tioga",
            "Erie", "Niagara", "Schuyler", "Steuben",
        ),
        ("24", "Democratic"): (
            "Genesee", "Livingston", "Orleans", "Oswego", "Seneca", "Wayne",
            "Wyoming", "Yates", "Cayuga", "Jefferson", "Niagara", "Ontario",
            "Schuyler", "Steuben",
        ),
        ("25", "Democratic"): ("Monroe", "Ontario"),
    }
    captured = {
        ("03", "Democratic", "Nassau"): (
            "official_hosted_uncertified",
            "https://app.nassaucountyny.gov/BOE/results/election2.html",
            "nassau/nassau-2026-primary-unofficial.html",
        ),
        ("03", "Republican", "Nassau"): (
            "official_hosted_uncertified",
            "https://app.nassaucountyny.gov/BOE/results/election2.html",
            "nassau/nassau-2026-primary-unofficial.html",
        ),
        ("04", "Republican", "Nassau"): (
            "official_hosted_uncertified",
            "https://app.nassaucountyny.gov/BOE/results/election2.html",
            "nassau/nassau-2026-primary-unofficial.html",
        ),
        ("03", "Democratic", "Queens"): (
            "certified_county_canvass",
            "https://www.vote.nyc/page/election-results-summary",
            (
                "nyc/nyc-2026-01401600003Queens_Democratic_Representative_in_"
                "Congress_3rd_Congressional_District_Recap.csv"
            ),
        ),
        ("03", "Republican", "Queens"): (
            "certified_county_canvass",
            "https://www.vote.nyc/page/election-results-summary",
            (
                "nyc/nyc-2026-02401600003Queens_Republican_Representative_in_"
                "Congress_3rd_Congressional_District_Recap.csv"
            ),
        ),
        ("03", "Democratic", "Suffolk"): (
            "final_county_return",
            "https://apps2.suffolkcountyny.gov/boe/eleres/26pe/DEMs.htm",
            "suffolk/suffolk-2026-primary-DEMs.html",
        ),
        ("03", "Republican", "Suffolk"): (
            "final_county_return",
            "https://apps2.suffolkcountyny.gov/boe/eleres/26pe/REPs.htm",
            "suffolk/suffolk-2026-primary-REPs.html",
        ),
        ("17", "Democratic", "Dutchess"): (
            "certified_county_canvass",
            (
                "https://elections.dutchessny.gov/wp-content/uploads/2026/07/"
                "Detailed-Results-by-Contest-Table-7-10.pdf"
            ),
            "counties/dutchess-2026-primary-detailed.pdf",
        ),
        ("19", "Republican", "Tompkins"): (
            "certified_county_canvass",
            "https://electionhistory.tompkinscountyny.gov/contest/647",
            "counties/tompkins-2026-cd19-certified.csv",
        ),
        ("25", "Democratic", "Monroe"): (
            "certified_county_canvass",
            (
                "https://www.monroecounty.gov/files/boe/Election%20Results/"
                "Election%20Canvass%20Books/PE26%20Official%20Results%20Excel%20Reports.zip"
            ),
            "counties/monroe-2026-primary-official.zip",
        ),
    }
    enhanced_official = {
        ("17", "Democratic", county)
        for county in ("Putnam", "Rockland", "Westchester")
    } | {
        ("19", "Republican", county)
        for county in ("Columbia", "Sullivan", "Rensselaer")
    } | {
        ("23", "Democratic", county)
        for county in ("Cattaraugus", "Chemung")
    } | {("24", "Democratic", "Livingston")}
    enhanced_unofficial = {
        ("19", "Republican", "Broome"),
        ("21", "Democratic", "Jefferson"),
        ("21", "Republican", "Jefferson"),
        ("23", "Democratic", "Steuben"),
        ("24", "Democratic", "Jefferson"),
        ("24", "Democratic", "Ontario"),
        ("24", "Democratic", "Steuben"),
        ("25", "Democratic", "Ontario"),
    }
    rows = []
    for (district, party), counties in contests.items():
        contest_status = "complete" if district == "17" else "partial"
        for county in counties:
            key = (district, party, county)
            if key in captured:
                status, source_url, raw_filename = captured[key]
            elif key in enhanced_official:
                slug = county.lower().replace(" ", "-").replace(".", "")
                status = "certified_county_canvass"
                source_url = (
                    "https://app.enhancedvoting.com/results/public/api/elections/"
                    f"{slug}-county-ny/PE26/data"
                )
                raw_filename = (
                    f"counties/enhanced/{slug}-county-ny-PE26-data.json"
                )
            elif key in enhanced_unofficial:
                slug = county.lower().replace(" ", "-").replace(".", "")
                status = "official_hosted_uncertified"
                source_url = (
                    "https://app.enhancedvoting.com/results/public/api/elections/"
                    f"{slug}-county-ny/PE26/data"
                )
                raw_filename = (
                    f"counties/enhanced/{slug}-county-ny-PE26-data.json"
                )
            else:
                status = "not_recovered"
                source_url = ""
                raw_filename = ""
            rows.append({
                "district": district,
                "primary_party": party,
                "county": county,
                "contest_status": contest_status,
                "county_source_status": status,
                "source_url": source_url,
                "raw_filename": raw_filename,
                "notes": (
                    "Certified/final all-county set complete."
                    if contest_status == "complete"
                    else "District remains excluded until every county canvass is certified."
                ),
            })
    return rows


def _manifest(
    raw_dir: Path,
    results: list[dict],
    roster: list[dict],
    partial: list[dict],
) -> list[dict]:
    result_counts = defaultdict(list)
    for row in results:
        result_counts[row["source_id"]].append(row)
    roster_counts = defaultdict(list)
    for row in roster:
        roster_counts[row["source_id"]].append(row)

    entries = []
    for source in MI_RESULT_SOURCES:
        path = raw_dir / source["filename"]
        rows = result_counts[source["source_id"]]
        entries.append({
            "source_id": source["source_id"],
            "state_code": "MI",
            "election_date": source["date"],
            "artifact_kind": "certified_results",
            "authority": "Michigan Department of State",
            "publication_url": source["publication"],
            "source_url": source["url"],
            "raw_filename": source["filename"],
            "sha256": _sha256(path),
            "acquisition_status": "recovered",
            "verification_status": "complete_official_statewide_export",
            "candidate_rows": len(rows),
            "contests": len({row["contest_id"] for row in rows}),
            "coverage": "US_Senate_and_all_13_US_House_districts_all_reported_candidates",
            "notes": (
                "Authority index links the MVIC result page; browser session exposed export ID."
            ),
        })
    ny_result_path = raw_dir / NY_2024_RESULT_SOURCE["filename"]
    ny_rows = result_counts[NY_2024_RESULT_SOURCE["source_id"]]
    entries.append({
        "source_id": NY_2024_RESULT_SOURCE["source_id"],
        "state_code": "NY",
        "election_date": NY_2024_RESULT_SOURCE["date"],
        "artifact_kind": "certified_results",
        "authority": "New York State Board of Elections / Civera hosted database",
        "publication_url": NY_2024_RESULT_SOURCE["publication"],
        "source_url": NY_2024_RESULT_SOURCE["url"],
        "raw_filename": NY_2024_RESULT_SOURCE["filename"],
        "sha256": _sha256(ny_result_path),
        "acquisition_status": "recovered",
        "verification_status": "partial_state_board_canvass_only",
        "candidate_rows": len(ny_rows),
        "contests": len({row["contest_id"] for row in ny_rows}),
        "coverage": "four_state_board_certified_contested_US_House_primaries",
        "notes": "County-contained congressional primaries are not present in this state export.",
    })
    ny_roster_path = raw_dir / NY_2024_ROSTER_SOURCE["source_pdf"]
    ny_roster_rows = roster_counts[NY_2024_ROSTER_SOURCE["source_id"]]
    entries.append({
        "source_id": NY_2024_ROSTER_SOURCE["source_id"],
        "state_code": "NY",
        "election_date": NY_2024_ROSTER_SOURCE["date"],
        "artifact_kind": "ballot_roster",
        "authority": "New York State Board of Elections",
        "publication_url": NY_2024_ROSTER_SOURCE["publication"],
        "source_url": NY_2024_ROSTER_SOURCE["url"],
        "raw_filename": NY_2024_ROSTER_SOURCE["source_pdf"],
        "sha256": _sha256(ny_roster_path),
        "acquisition_status": "recovered",
        "verification_status": "partial_state_filed_offices_only",
        "candidate_rows": len(ny_roster_rows),
        "contests": len({row["contest_id"] for row in ny_roster_rows}),
        "coverage": "US_Senate_and_state_board_filed_US_House_districts_02_03_16_to_26",
        "notes": "Districts filed solely with county boards are outside this certification.",
    })
    ny_2026_roster_path = raw_dir / NY_2026_ROSTER_SOURCE["source_pdf"]
    ny_2026_roster_rows = roster_counts[NY_2026_ROSTER_SOURCE["source_id"]]
    entries.append({
        "source_id": NY_2026_ROSTER_SOURCE["source_id"],
        "state_code": "NY",
        "election_date": NY_2026_ROSTER_SOURCE["date"],
        "artifact_kind": "ballot_roster",
        "authority": "New York State Board of Elections",
        "publication_url": NY_2026_ROSTER_SOURCE["publication"],
        "source_url": NY_2026_ROSTER_SOURCE["url"],
        "raw_filename": NY_2026_ROSTER_SOURCE["source_pdf"],
        "sha256": _sha256(ny_2026_roster_path),
        "acquisition_status": "recovered",
        "verification_status": "partial_state_filed_offices_only",
        "candidate_rows": len(ny_2026_roster_rows),
        "contests": len({row["contest_id"] for row in ny_2026_roster_rows}),
        "coverage": "state_board_filed_US_House_districts_02_03_16_to_26",
        "notes": "Pre-election roster only; county-filed districts remain outside this source.",
    })
    supporting_sources = [
        {
            "source_id": "mi-election-results-index",
            "state_code": "MI",
            "election_date": "",
            "artifact_kind": "authority_index",
            "authority": "Michigan Department of State",
            "publication_url": (
                "https://www.michigan.gov/sos/elections/election-results-and-data"
            ),
            "source_url": (
                "https://www.michigan.gov/sos/elections/election-results-and-data"
            ),
            "raw_filename": "mi-election-results-index.html",
            "verification_status": "authority_links_verified",
            "coverage": "links_2024_and_2026_August_primary_results_and_candidate_listings",
            "notes": "",
        },
        {
            "source_id": "mi-2024-primary-result-page",
            "state_code": "MI",
            "election_date": "2024-08-06",
            "artifact_kind": "result_page",
            "authority": "Michigan Department of State",
            "publication_url": MI_RESULT_SOURCES[0]["publication"],
            "source_url": MI_RESULT_SOURCES[0]["publication"],
            "raw_filename": "mi-2024-primary-results.html",
            "verification_status": "official_rendered_result_page",
            "coverage": "statewide_primary_results_page",
            "notes": "Contains export link with electionId=698.",
        },
        {
            "source_id": "mi-2024-primary-candidate-listing",
            "state_code": "MI",
            "election_date": "2024-08-06",
            "artifact_kind": "candidate_listing",
            "authority": "Michigan Department of State",
            "publication_url": (
                "https://www.michigan.gov/sos/elections/election-results-and-data"
            ),
            "source_url": (
                "https://mi-boe.entellitrak.com/candlist/2024PRI_CANDLIST.html"
            ),
            "raw_filename": "mi-2024-primary-candidates.html",
            "verification_status": "official_candidate_listing",
            "coverage": "all_state_and_judicial_offices_including_statuses",
            "notes": "Result export, not this filing list, defines emitted ballot candidates.",
        },
        {
            "source_id": "mi-2026-primary-result-page",
            "state_code": "MI",
            "election_date": "2026-08-04",
            "artifact_kind": "result_page",
            "authority": "Michigan Department of State",
            "publication_url": MI_RESULT_SOURCES[1]["publication"],
            "source_url": MI_RESULT_SOURCES[1]["publication"],
            "raw_filename": "mi-2026-primary-results.html",
            "verification_status": "official_rendered_result_page",
            "coverage": "statewide_primary_results_page",
            "notes": "Contains export link with electionId=706.",
        },
        {
            "source_id": "mi-2026-primary-candidate-listing",
            "state_code": "MI",
            "election_date": "2026-08-04",
            "artifact_kind": "candidate_listing",
            "authority": "Michigan Department of State",
            "publication_url": (
                "https://www.michigan.gov/sos/elections/election-results-and-data"
            ),
            "source_url": (
                "https://mi-boe.entellitrak.com/etk-mi-boe-prod/page.request.do?"
                "electionType=PRI&electionYear=2026&page=page.miboePublicReport"
            ),
            "raw_filename": "mi-2026-primary-candidates.html",
            "verification_status": "official_candidate_listing",
            "coverage": "all_state_and_judicial_offices_including_statuses",
            "notes": "Result export, not this filing list, defines emitted ballot candidates.",
        },
        {
            "source_id": "ny-2024-primary-certified-results-pdf",
            "state_code": "NY",
            "election_date": "2024-06-25",
            "artifact_kind": "certified_results_pdf",
            "authority": "New York State Board of Elections / Civera hosted database",
            "publication_url": "https://results.elections.ny.gov/document/472?page=1",
            "source_url": "https://ny.staging.elstats2.civera.com/eng/files/serve/472",
            "raw_filename": "ny-2024-primary-certified-results.pdf",
            "verification_status": "official_partial_state_board_canvass",
            "coverage": "same_four_congressional_contests_as_search_export",
            "notes": "Used as an independent official cross-check of the CSV.",
        },
    ]
    contest_sources = (
        ("5580", "ny-2024-cd16-dem.csv", "CD16_Democratic"),
        ("5566", "ny-2024-cd17-wfp.csv", "CD17_Working_Families"),
        ("5567", "ny-2024-cd22-dem.csv", "CD22_Democratic"),
        ("5568", "ny-2024-cd24-rep.csv", "CD24_Republican"),
    )
    for contest_id, filename, coverage in contest_sources:
        supporting_sources.append({
            "source_id": f"ny-2024-contest-{contest_id}",
            "state_code": "NY",
            "election_date": "2024-06-25",
            "artifact_kind": "contest_results_csv",
            "authority": "New York State Board of Elections / Civera hosted database",
            "publication_url": f"https://results.elections.ny.gov/contest/{contest_id}",
            "source_url": (
                "https://ny.elstats3.civera.com/api/"
                f"download_contest/{contest_id}_table.csv?split_party=false"
            ),
            "raw_filename": filename,
            "verification_status": "official_contest_cross_check",
            "coverage": coverage,
            "notes": "",
        })
    for support in supporting_sources:
        path = raw_dir / support["raw_filename"]
        entries.append({
            **support,
            "sha256": _sha256(path),
            "acquisition_status": "recovered",
            "candidate_rows": "",
            "contests": "",
        })
    for source in (*NYC_RESULT_SOURCES, *SUFFOLK_RESULT_SOURCES):
        path = raw_dir / source["filename"]
        rows = result_counts[source["source_id"]]
        is_nyc = source["source_id"].startswith("nyc-")
        entries.append({
            "source_id": source["source_id"],
            "state_code": "NY",
            "election_date": source["date"],
            "artifact_kind": "certified_county_primary_results",
            "authority": (
                "Board of Elections in the City of New York"
                if is_nyc
                else "Suffolk County Board of Elections"
            ),
            "publication_url": (
                "https://www.vote.nyc/page/election-results-summary"
                if is_nyc and source["date"].startswith("2026")
                else (
                    "https://vote.nyc/page/election-results-summary-2024"
                    if is_nyc
                    else source["url"].rsplit("/", 1)[0] + "/default.htm"
                )
            ),
            "source_url": _nyc_source_url(source) if is_nyc else source["url"],
            "raw_filename": source["filename"],
            "sha256": _sha256(path),
            "acquisition_status": "recovered",
            "verification_status": "certified_or_final_county_return",
            "candidate_rows": len(rows),
            "contests": len({row["contest_id"] for row in rows}),
            "coverage": f"Congressional_District_{source['district']}_{source['party']}",
            "notes": (
                "Named write-ins are reported ballot options, not proof of willing or "
                "qualified candidacy or political affiliation. primary_party is the ballot "
                "category; party is blank for write-ins."
            ),
        })
    cd17_rows = result_counts[NY_2026_CD17_SOURCE["source_id"]]
    entries.append({
        "source_id": NY_2026_CD17_SOURCE["source_id"],
        "state_code": "NY",
        "election_date": NY_2026_CD17_SOURCE["date"],
        "artifact_kind": "certified_multi_county_primary_results",
        "authority": (
            "Dutchess, Putnam, Rockland, and Westchester County Boards of Elections"
        ),
        "publication_url": "multiple_official_county_canvasses",
        "source_url": cd17_rows[0]["source_url"],
        "raw_filename": (
            "counties/dutchess-2026-primary-detailed.pdf | "
            "counties/enhanced/{putnam,rockland,westchester}-county-ny-PE26-data.json"
        ),
        "sha256": cd17_rows[0]["source_sha256"],
        "acquisition_status": "recovered",
        "verification_status": "complete_certified_all_county_aggregate",
        "candidate_rows": len(cd17_rows),
        "contests": 1,
        "coverage": "CD17_Democratic_all_four_county_units",
        "notes": (
            "County candidate totals sum to 46,955 including 44 reported write-in/"
            "irregular votes; no party affiliation is inferred for write-ins."
        ),
    })
    partial_path = raw_dir / "ny-2026-enr.txt"
    entries.append({
        "source_id": "ny-2026-enr-uncertified",
        "state_code": "NY",
        "election_date": "2026-06-23",
        "artifact_kind": "partial_election_night_results",
        "authority": "New York State Board of Elections",
        "publication_url": "https://nyenr.elections.ny.gov/",
        "source_url": "https://nyenr.elections.ny.gov/HomeNoJS.aspx",
        "raw_filename": partial_path.name,
        "sha256": _sha256(partial_path),
        "acquisition_status": "recovered",
        "verification_status": "official_hosted_uncertified_excluded_from_results",
        "candidate_rows": len(partial),
        "contests": len({row["contest_id"] for row in partial}),
        "coverage": "nine_unresolved_2026_congressional_primary_contests",
        "notes": (
            "Preserved separately. Complete ED reporting is not equivalent to a certified "
            "canvass; absent or incomplete reporting is not interpreted as no primary."
        ),
    })
    for county_row in _county_canvass_accounting():
        if not county_row["raw_filename"]:
            continue
        path = raw_dir / county_row["raw_filename"]
        if not path.exists():
            continue
        party_slug = county_row["primary_party"].lower().replace(" ", "-")
        county_slug = county_row["county"].lower().replace(" ", "-").replace(".", "")
        note = "Supporting county unit; district status is recorded in county accounting."
        if county_row["county"] == "Queens":
            note = (
                "Named write-ins are reported ballot options, not proof of willing or "
                "qualified candidacy or political affiliation. primary_party is the ballot "
                "category; party remains blank for write-ins."
            )
        entries.append({
            "source_id": (
                f"ny-2026-county-{county_slug}-cd{county_row['district']}-{party_slug}"
            ),
            "state_code": "NY",
            "election_date": "2026-06-23",
            "artifact_kind": "county_canvass_supporting_source",
            "authority": f"{county_row['county']} County Board of Elections",
            "publication_url": county_row["source_url"],
            "source_url": county_row["source_url"],
            "raw_filename": county_row["raw_filename"],
            "sha256": _sha256(path),
            "acquisition_status": "recovered",
            "verification_status": county_row["county_source_status"],
            "candidate_rows": "",
            "contests": 1,
            "coverage": (
                f"CD{county_row['district']}_{county_row['primary_party']}_"
                f"{county_row['county']}_county_unit"
            ),
            "notes": note,
        })
    return entries


def _attempts() -> list[dict]:
    return [
        {
            "attempt_id": "ny-01",
            "attempted_on": "2026-09-22",
            "state_code": "NY",
            "cycle": "2024",
            "source_url": "https://elections.ny.gov/2024-election-results",
            "method": "urllib_and_curl",
            "outcome": "blocked_http_403",
            "raw_evidence": "",
            "notes": "Authority landing page rejected direct scripted retrieval.",
        },
        {
            "attempt_id": "ny-02",
            "attempted_on": "2026-09-22",
            "state_code": "NY",
            "cycle": "2024",
            "source_url": "https://results.elections.ny.gov/search?df=2024&dt=2024&p=1",
            "method": "headless_firefox",
            "outcome": "success",
            "raw_evidence": "ny-2024-election-database-search.csv",
            "notes": "Official replacement database loaded and exposed its search CSV URL.",
        },
        {
            "attempt_id": "ny-03",
            "attempted_on": "2026-09-22",
            "state_code": "NY",
            "cycle": "2024",
            "source_url": "https://ny.elstats.civera.com/api/download_search.csv",
            "method": "authority_linked_vendor_download",
            "outcome": "success_partial",
            "raw_evidence": "ny-2024-election-database-search.csv",
            "notes": (
                "Contains four State Board congressional primary contests, "
                "not county-only races."
            ),
        },
        {
            "attempt_id": "ny-04",
            "attempted_on": "2026-09-22",
            "state_code": "NY",
            "cycle": "2024",
            "source_url": "https://ny.staging.elstats2.civera.com/eng/files/serve/472",
            "method": "authority_linked_vendor_download",
            "outcome": "success_partial",
            "raw_evidence": "ny-2024-primary-certified-results.pdf",
            "notes": "Certified statement confirms the same four congressional contests.",
        },
        {
            "attempt_id": "ny-05",
            "attempted_on": "2026-09-22",
            "state_code": "NY",
            "cycle": "2024",
            "source_url": "https://elections.ny.gov/certification-june-25-2024-primary-election",
            "method": "headless_firefox",
            "outcome": "success_partial",
            "raw_evidence": "ny-2024-primary-certification.pdf",
            "notes": "Pre-election roster covers state-filed offices, not county-filed districts.",
        },
        {
            "attempt_id": "ny-06",
            "attempted_on": "2026-09-22",
            "state_code": "NY",
            "cycle": "2026",
            "source_url": (
                "https://elections.ny.gov/system/files/documents/2026/05/"
                "accessible-june-23-2026-primary-certification-amended-4.30.26-.pdf"
            ),
            "method": "curl_and_headless_firefox",
            "outcome": "blocked_http_403_or_authority_404",
            "raw_evidence": "ny-2026-primary-certification-blocked-403.html",
            "notes": "Pre-election certification was not treated as post-primary results.",
        },
        {
            "attempt_id": "ny-07",
            "attempted_on": "2026-09-22",
            "state_code": "NY",
            "cycle": "2026",
            "source_url": (
                "https://elections.ny.gov/certification-june-23-2026-primary-election"
            ),
            "method": "headless_firefox",
            "outcome": "success_partial_roster",
            "raw_evidence": "ny-2026-primary-certification.pdf",
            "notes": (
                "Current authority alias resolved the amended May 13 PDF; "
                "state-filed districts only."
            ),
        },
        {
            "attempt_id": "ny-08",
            "attempted_on": "2026-09-22",
            "state_code": "NY",
            "cycle": "2026",
            "source_url": "https://nyenr.elections.ny.gov/HomeNoJS.aspx",
            "method": "web_index_and_direct_probe",
            "outcome": "rejected_unofficial_incomplete",
            "raw_evidence": "",
            "notes": (
                "June 26 snapshot labels itself unofficial and has incomplete "
                "district reporting."
            ),
        },
        {
            "attempt_id": "mi-01",
            "attempted_on": "2026-09-22",
            "state_code": "MI",
            "cycle": "2024",
            "source_url": "https://mielections.us/election/results/2024PRI_CENR.html",
            "method": "curl",
            "outcome": "timeout",
            "raw_evidence": "",
            "notes": "Legacy authority host did not respond within 45 seconds.",
        },
        {
            "attempt_id": "mi-02",
            "attempted_on": "2026-09-22",
            "state_code": "MI",
            "cycle": "2026",
            "source_url": "https://mielections.us/election/results/2026PRI_CENR.html",
            "method": "curl",
            "outcome": "timeout",
            "raw_evidence": "",
            "notes": "Legacy authority host did not respond within 45 seconds.",
        },
        {
            "attempt_id": "mi-03",
            "attempted_on": "2026-09-22",
            "state_code": "MI",
            "cycle": "2024-2026",
            "source_url": "https://mvic.sos.state.mi.us/votehistory/",
            "method": "curl_and_web_fetch",
            "outcome": "blocked_http_403",
            "raw_evidence": "",
            "notes": "Cloudflare rejected non-browser requests to result pages and exports.",
        },
        {
            "attempt_id": "mi-04",
            "attempted_on": "2026-09-22",
            "state_code": "MI",
            "cycle": "2024-2026",
            "source_url": "https://mvic.sos.state.mi.us/votehistory/",
            "method": "headless_firefox_webdriver_bidi",
            "outcome": "success",
            "raw_evidence": "mi-2024-primary-results.tsv | mi-2026-primary-results.tsv",
            "notes": (
                "Authority pages exposed election IDs 698 and 706; "
                "same-origin export fetch succeeded."
            ),
        },
    ]


def _gaps() -> list[dict]:
    return [
        {
            "gap_id": "ny-2024-congressional-roster",
            "state_code": "NY",
            "cycle": "2024",
            "chamber": "House and Senate",
            "requested_artifact": "complete_primary_ballot_roster",
            "coverage_status": "partial",
            "recovered_scope": "US Senate and House districts 02, 03, 16-26 filed with NYSBOE",
            "missing_scope": "House districts 01 and 04-15 filed solely with county boards",
            "blocker": "State certification is jurisdictionally incomplete by design.",
            "next_authoritative_step": (
                "Acquire county ballot certifications for omitted districts."
            ),
            "source_urls": "https://elections.ny.gov/certification-june-25-2024-primary-election",
        },
        {
            "gap_id": "ny-2026-house-results",
            "state_code": "NY",
            "cycle": "2026",
            "chamber": "House",
            "requested_artifact": "certified_primary_results",
            "coverage_status": "partial",
            "recovered_scope": (
                "CD01 DEM; CD06 DEM; CD07 DEM; CD09 DEM; CD10 DEM; CD11 DEM; "
                "CD12 DEM; CD13 DEM; CD14 DEM; CD15 DEM; CD17 DEM"
            ),
            "missing_scope": (
                "CD03 DEM/REP; CD04 REP; CD19 REP; CD21 DEM/REP; "
                "CD23 DEM; CD24 DEM; CD25 DEM"
            ),
            "blocker": (
                "Remaining contests require certified Nassau and multi-county canvass statements; "
                "the state election-night page is incomplete for those districts."
            ),
            "next_authoritative_step": (
                "Acquire certified county statements and aggregate each remaining district."
            ),
            "source_urls": (
                "https://www.vote.nyc/page/election-results-summary | "
                "https://apps2.suffolkcountyny.gov/boe/eleres/26pe/DEMs.htm | "
                "https://nyenr.elections.ny.gov/HomeNoJS.aspx"
            ),
        },
        {
            "gap_id": "ny-2026-congressional-roster",
            "state_code": "NY",
            "cycle": "2026",
            "chamber": "House",
            "requested_artifact": "complete_primary_ballot_roster",
            "coverage_status": "partial",
            "recovered_scope": "House districts 02, 03, and 16-26 filed with NYSBOE",
            "missing_scope": "House districts 01 and 04-15 filed solely with county boards",
            "blocker": (
                "The recovered state certification is jurisdictionally incomplete by design."
            ),
            "next_authoritative_step": (
                "Acquire county ballot certifications for the omitted districts."
            ),
            "source_urls": NY_2026_ROSTER_SOURCE["url"],
        },
    ]


def collect_ny_mi_primaries(
    raw_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict:
    raw_dir = raw_dir or RAW_DIR / RAW_SUBDIR
    output_dir = output_dir or ANALYSIS_DATA_DIR / "congressional"
    ledger_dir = output_dir / "ny_mi"
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for source in MI_RESULT_SOURCES:
        results.extend(parse_michigan_results(raw_dir / source["filename"], source))
    results.extend(
        parse_new_york_results(
            raw_dir / NY_2024_RESULT_SOURCE["filename"],
            NY_2024_RESULT_SOURCE,
        )
    )
    for source in NYC_RESULT_SOURCES:
        results.extend(parse_nyc_results(raw_dir / source["filename"], source))
    for source in SUFFOLK_RESULT_SOURCES:
        results.extend(parse_suffolk_results(raw_dir / source["filename"], source))
    results.extend(parse_ny_cd17_county_canvass(raw_dir, NY_2026_CD17_SOURCE))
    results.sort(key=lambda row: (
        row["cycle"],
        row["state_code"],
        row["chamber"],
        row["district"],
        row["primary_party"],
        row["candidate_name"],
        row["candidate_source_id"],
    ))

    roster = parse_new_york_roster(
        raw_dir / NY_2024_ROSTER_SOURCE["filename"],
        raw_dir / NY_2024_ROSTER_SOURCE["source_pdf"],
        NY_2024_ROSTER_SOURCE,
    )
    roster.extend(
        parse_new_york_roster(
            raw_dir / NY_2026_ROSTER_SOURCE["filename"],
            raw_dir / NY_2026_ROSTER_SOURCE["source_pdf"],
            NY_2026_ROSTER_SOURCE,
        )
    )
    roster.sort(key=lambda row: (
        row["cycle"],
        row["chamber"],
        row["district"],
        row["primary_party"],
        row["candidate_name"],
    ))

    partial = parse_ny_enr_partial(raw_dir / "ny-2026-enr.txt")
    write_csv(output_dir / RESULT_FILENAME, results, FIELDS)
    write_csv(output_dir / ROSTER_FILENAME, roster, FIELDS)
    write_csv(
        ledger_dir / PARTIAL_RESULT_FILENAME,
        [{field: row.get(field, "") for field in FIELDS} for row in partial],
        FIELDS,
    )
    accounting = _contest_accounting(results, partial, raw_dir)
    write_csv(ledger_dir / "contest_accounting.csv", accounting, ACCOUNTING_FIELDS)
    county_accounting = _county_canvass_accounting()
    write_csv(
        ledger_dir / "county_canvass_accounting.csv",
        county_accounting,
        COUNTY_ACCOUNTING_FIELDS,
    )
    manifest = _manifest(raw_dir, results, roster, partial)
    write_csv(ledger_dir / "source_manifest.csv", manifest, MANIFEST_FIELDS)
    write_csv(ledger_dir / "attempt_ledger.csv", _attempts(), ATTEMPT_FIELDS)
    write_csv(ledger_dir / "unresolved_gaps.csv", _gaps(), GAP_FIELDS)
    return {
        "result_rows": len(results),
        "result_contests": len({row["contest_id"] for row in results}),
        "roster_rows": len(roster),
        "partial_result_rows": len(partial),
        "accounting_rows": len(accounting),
        "county_accounting_rows": len(county_accounting),
        "manifest_sources": len(manifest),
        "unresolved_gaps": len(_gaps()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    summary = collect_ny_mi_primaries(args.raw_dir, args.output_dir)
    print(" ".join(f"{key}={value}" for key, value in summary.items()))


if __name__ == "__main__":
    main()
