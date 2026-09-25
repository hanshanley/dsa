"""Recover official Idaho, Oregon, and New Mexico congressional primaries."""

import argparse
import csv
import gzip
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from .io import write_csv
from .paths import ANALYSIS_DATA_DIR, RAW_DIR
from .state_results import FIELDS

RAW_SUBDIR = "northwest_primaries"
RESULT_FILENAME = "northwest_primary_results.csv"
MANIFEST_SUBDIR = "northwest"

SOURCE_FIELDS = [
    "source_id", "state_code", "election_date", "artifact_kind", "authority",
    "publication_url", "source_url", "raw_filename", "sha256", "verification_status",
    "certification_status", "candidate_rows", "contests", "coverage", "notes",
]
COVERAGE_FIELDS = [
    "state_code", "cycle", "election_date", "chamber", "district", "primary_party",
    "coverage_status", "candidate_rows", "source_ids", "notes",
]
GAP_FIELDS = [
    "gap_id", "state_code", "cycle", "chamber", "coverage_status", "recovered_scope",
    "missing_scope", "blocker", "next_authoritative_step", "source_urls",
]
ATTEMPT_FIELDS = [
    "attempt_id", "attempted_on", "state_code", "cycle", "source_url", "method",
    "outcome", "raw_evidence", "notes",
]
PARTY_ACCOUNTING_FIELDS = [
    "cycle", "election_date", "state_code", "chamber", "district", "term",
    "stage", "primary_party", "status", "candidate_names", "source_urls",
    "locators", "notes",
]
PARTY_ACCOUNTING_STATUSES = {
    "results_complete", "results_partial", "unopposed_nomination_verified",
    "no_primary_verified", "no_candidate_verified", "unresolved", "not_scheduled",
}
PROVIDER_RAW_FIELDS = ["provider", "path", "sha256", "bytes", "artifact_type"]

UTAH_NOMINATIONS = (
    ("2024", "2024-06-25", "Senate", "S", "Democratic", "CAROLINE GLEICH"),
    ("2024", "2024-06-25", "Senate", "S", "Independent American", "CARLTON E. BOWEN"),
    ("2024", "2024-06-25", "House", "01", "Democratic", "BILL CAMPBELL"),
    ("2024", "2024-06-25", "House", "01", "Libertarian", "DANIEL R. COTTAM"),
    ("2024", "2024-06-25", "House", "02", "Constitution", "CASSIE EASLEY"),
    ("2024", "2024-06-25", "House", "02", "Democratic", "NATHANIEL E WOODWARD"),
    ("2024", "2024-06-25", "House", "03", "Democratic", "GLENN J. WRIGHT"),
    ("2024", "2024-06-25", "House", "04", "Democratic", "KATRINA FALLICK-WANG"),
    ("2024", "2024-06-25", "House", "04", "Republican", "BURGESS OWENS"),
    ("2024", "2024-06-25", "House", "04", "United Utah", "VAUGHN R COOK"),
    ("2026", "2026-06-23", "House", "01", "Libertarian", "JESSE WEST"),
    ("2026", "2026-06-23", "House", "01", "Republican", "RILEY OWEN"),
    ("2026", "2026-06-23", "House", "02", "Democratic", "PETER CROSBY"),
    ("2026", "2026-06-23", "House", "02", "Independent American", "CARLTON E. BOWEN"),
    ("2026", "2026-06-23", "House", "02", "Libertarian", "DANIEL COTTAM"),
    ("2026", "2026-06-23", "House", "03", "Constitution", "CASSIE EASLEY"),
    ("2026", "2026-06-23", "House", "03", "Democratic", "KENT S. UDELL"),
    ("2026", "2026-06-23", "House", "03", "Libertarian", "MICHAEL R. STODDARD"),
    ("2026", "2026-06-23", "House", "04", "Democratic", "JONNY LARSEN"),
    ("2026", "2026-06-23", "House", "04", "Libertarian", "TAYLOR WRIGHT"),
    ("2026", "2026-06-23", "House", "04", "Republican", "MIKE KENNEDY"),
)

NEVADA_NOMINATIONS = (
    (
        "2024", "2024-06-11", "House", "01", "Democratic", "Dina Titus",
        "https://www.clarkcountynv.gov/government/departments/elections/24p-info",
        "contests-not-on-ballot-24p.pdf:page-1; contests-candidates PDF:District 1",
        "Official no-primary notice says the contest had only one or no Democratic "
        "candidate; the official roster identifies Dina Titus as the sole nominee.",
    ),
    (
        "2026", "2026-06-09", "House", "04", "Democratic", "Steven A. Horsford",
        "https://www.nvsos.gov/home/showpublisheddocument/18368/639135026079800000",
        "official roster:Representative In Congress, District 4; Primary=N",
        "Official statewide roster marks Horsford as not appearing in the primary.",
    ),
)

ID_2024_CONTESTS = (
    ("20318", "01", "Republican"), ("20316", "01", "Democratic"),
    ("20317", "01", "Libertarian"), ("20315", "01", "Constitution"),
    ("20322", "02", "Republican"), ("20320", "02", "Democratic"),
    ("20321", "02", "Libertarian"), ("20319", "02", "Constitution"),
)

ID_2026_RESULTS = {
    ("Senate", "S", "Democratic"): [
        ("Brad Moore", 14863), ("David Roth", 29534), ("Nickolas 007 Bonds", 3344),
    ],
    ("Senate", "S", "Libertarian"): [("Matt Loesby", 855)],
    ("Senate", "S", "Republican"): [
        ("Denny LaVe", 10182), ("Jim Risch", 156140),
        ("Joe Evans", 32636), ("Josh Roy", 33188),
    ],
    ("House", "01", "Democratic"): [
        ("Kaylee Peterson", 18907), ("Kenneth Brungardt", 2803),
    ],
    ("House", "01", "Republican"): [
        ("Andy Briner", 14438), ("Joseph P Morrison", 13407),
        ("Russ Fulcher", 100104),
    ],
    ("House", "02", "Democratic"): [
        ("Ellie Gilbreath", 19523), ("Julie Wiley", 7411),
    ],
    ("House", "02", "Republican"): [
        ("Brian Keene", 20975), ("Mike Simpson", 63448),
        ("Perry Shumway", 15802),
    ],
    ("House", "02", "Libertarian"): [("Will Johanson", 336)],
}

NM_2024_CONTESTS = (
    ("14427", "Senate", "S", "Democratic"),
    ("14428", "Senate", "S", "Republican"),
    ("14431", "House", "01", "Republican"),
    ("14432", "House", "01", "Democratic"),
    ("14433", "House", "02", "Democratic"),
    ("14434", "House", "02", "Republican"),
)

NM_2026_FILES = (
    ("senate-DEM.json", "Senate", "S", "Democratic"),
    ("senate-REP.json", "Senate", "S", "Republican"),
    ("cd01-DEM.json", "House", "01", "Democratic"),
    ("cd01-REP.json", "House", "01", "Republican"),
    ("cd02-DEM.json", "House", "02", "Democratic"),
    ("cd02-REP.json", "House", "02", "Republican"),
    ("cd03-DEM.json", "House", "03", "Democratic"),
    ("cd03-REP.json", "House", "03", "Republican"),
)

NM_2026_STATE_TOTALS = {
    "18908": 182360, "18933": 34289, "19598": 31220,
    "18928": 79823, "18909": 31809,
    "18913": 47123, "18906": 26836, "18929": 4910,
    "18912": 68768, "18905": 32901,
}

OR_2024_RESULTS = {
    ("01", "Democratic"): [
        ("Suzanne Bonamici", 75577, False), ("Jamil O. Ahmad", 5007, False),
        ("Courtney E. Casgraux (Moore)", 2500, False),
        ("Miscellaneous Write-In", 383, True),
    ],
    ("01", "Republican"): [
        ("Bob Todd", 23993, False), ("Miscellaneous Write-In", 579, True),
    ],
    ("02", "Democratic"): [
        ("Steve William Laible", 5325, False), ("Dan Ruby", 33585, False),
        ("Miscellaneous Write-In", 620, True),
    ],
    ("02", "Republican"): [
        ("Jason Beebe", 16403, False), ("Cliff Bentz", 73031, False),
        ("Miscellaneous Write-In", 360, True),
    ],
    ("03", "Democratic"): [
        ("Maxine E. Dexter", 47254, False), ("Eddy Morales", 649, False),
        ("Ricardo Barajas", 2138, False), ("Nolan Bylenga", 856, False),
        ("Rachel Lydia Rand", 2359, False), ("Susheela Jayapal", 32793, False),
        ("Michael Jonas", 13391, False), ("Miscellaneous Write-In", 430, True),
    ],
    ("03", "Republican"): [
        ("Gary L. Dye", 6869, False), ("Teresa Orwig", 4303, False),
        ("Joanna Harbour", 13948, False), ("Miscellaneous Write-In", 258, True),
    ],
    ("04", "Democratic"): [
        ("Val Hoyle", 73444, False), ("Miscellaneous Write-In", 1212, True),
    ],
    ("04", "Republican"): [
        ("Monique DeSpain", 31436, False), ("Amy L Ryan Courser", 22418, False),
        ("Miscellaneous Write-In", 498, True),
    ],
    ("05", "Democratic"): [
        ("Janelle S. Bynum", 55473, False), ("Jamie McLeod-Skinner", 23905, False),
        ("Miscellaneous Write-In", 510, True),
    ],
    ("05", "Republican"): [
        ("Lori Chavez-DeRemer", 54458, False),
        ("Miscellaneous Write-In", 1009, True),
    ],
    ("06", "Democratic"): [
        ("Cody Reynolds", 7463, False), ("Andrea Salinas", 52509, False),
        ("Miscellaneous Write-In", 330, True),
    ],
    ("06", "Republican"): [
        ("Mike Erickson", 37497, False), ("David A Burch", 1447, False),
        ("David Russ", 10908, False), ("Conrad J Herold", 628, False),
        ("Miscellaneous Write-In", 381, True),
    ],
}

OR_2026_RESULTS = {
    ("Senate", "S", "Democratic"): [
        ("Jeff Merkley", 457006, False), ("Paul Damian Wells", 30544, False),
        ("Miscellaneous Write-In", 2907, True),
    ],
    ("Senate", "S", "Republican"): [
        ("Brent Barker", 85229, False), ("Deborah C Brown", 14021, False),
        ("David A Burch", 8704, False), ("Russell McAlmond", 42136, False),
        ("Jo Rae Perkins", 99278, False), ("Timothy Skelton", 5626, False),
        ("David Brock Smith", 107953, False), ("Miscellaneous Write-In", 3254, True),
    ],
    ("House", "01", "Democratic"): [
        ("Jamil O Ahmad", 11458, False), ("Suzanne Bonamici", 77306, False),
        ("Miscellaneous Write-In", 497, True),
    ],
    ("House", "01", "Republican"): [
        ("Barbara J Kahl", 26877, False), ("John Verbeek", 10285, False),
        ("Miscellaneous Write-In", 437, True),
    ],
    ("House", "02", "Democratic"): [
        ("Chris Beck", 15951, False), ("Mary Doyle", 9101, False),
        ("Rebecca Mueller", 8357, False), ("Patty Snow", 4224, False),
        ("Dawn Rasmussen", 6880, False), ("Peter Quince", 1258, False),
        ("Miscellaneous Write-In", 610, True),
    ],
    ("House", "02", "Republican"): [
        ("Cliff Bentz", 79543, False), ("Andrea Carr", 5353, False),
        ("Peter J Larson", 14565, False), ("Miscellaneous Write-In", 474, True),
    ],
    ("House", "03", "Democratic"): [
        ("Andrew Castilleja", 2082, False), ("Maxine E Dexter", 81643, False),
        ("Jessica Salas", 7513, False), ("Miscellaneous Write-In", 352, True),
    ],
    ("House", "03", "Republican"): [
        ("Loran Ayles", 14420, False), ("Miscellaneous Write-In", 557, True),
    ],
    ("House", "04", "Democratic"): [
        ("Daniel B Bahlen", 2259, False), ("Melissa Bird", 19850, False),
        ("Val Hoyle", 68900, False), ("Miscellaneous Write-In", 676, True),
    ],
    ("House", "04", "Republican"): [
        ("Monique DeSpain", 59232, False), ("Stefan G Strek", 8507, False),
        ("Miscellaneous Write-In", 696, True),
    ],
    ("House", "05", "Democratic"): [
        ("Janelle S Bynum", 70294, False), ("Zeva Rosenbaum", 14951, False),
        ("Miscellaneous Write-In", 468, True),
    ],
    ("House", "05", "Republican"): [
        ("Patti Adair", 43524, False), ("Jonathan Lockwood", 28984, False),
        ("Miscellaneous Write-In", 504, True),
    ],
    ("House", "06", "Democratic"): [
        ("Andrea Salinas", 62532, False), ("Miscellaneous Write-In", 797, True),
    ],
    ("House", "06", "Republican"): [
        ("David Russ", 44027, False), ("Miscellaneous Write-In", 731, True),
    ],
}

OREGON_COUNTIES = {
    "Baker", "Benton", "Clackamas", "Clatsop", "Columbia", "Coos", "Crook",
    "Curry", "Deschutes", "Douglas", "Gilliam", "Grant", "Harney", "Hood River",
    "Jackson", "Jefferson", "Josephine", "Klamath", "Lake", "Lane", "Lincoln",
    "Linn", "Malheur", "Marion", "Morrow", "Multnomah", "Polk", "Sherman",
    "Tillamook", "Umatilla", "Union", "Wallowa", "Wasco", "Washington",
    "Wheeler", "Yamhill",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_oregon_2026_split_archive(raw_root: Path) -> dict:
    manifest_path = (
        raw_root / "or/2026/or-2026-primary-county-results.zip.gz.parts.json"
    )
    metadata = json.loads(manifest_path.read_text())
    compressed_hash = hashlib.sha256()
    compressed_bytes = 0
    descriptor, temporary_name = tempfile.mkstemp(suffix=".zip.gz")
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with temporary.open("wb") as output:
            for part in metadata["parts"]:
                path = manifest_path.parent / part["filename"]
                if path.stat().st_size != part["bytes"] or _sha256(path) != part["sha256"]:
                    raise ValueError(f"Oregon archive part differs: {path.name}")
                with path.open("rb") as handle:
                    while chunk := handle.read(1024 * 1024):
                        output.write(chunk)
                        compressed_hash.update(chunk)
                        compressed_bytes += len(chunk)
        if (
            compressed_bytes != metadata["gzip_bytes"]
            or compressed_hash.hexdigest() != metadata["gzip_sha256"]
        ):
            raise ValueError("Reassembled Oregon gzip differs from manifest")
        original_hash = hashlib.sha256()
        original_bytes = 0
        with gzip.open(temporary, "rb") as handle:
            while chunk := handle.read(1024 * 1024):
                original_hash.update(chunk)
                original_bytes += len(chunk)
        if (
            original_bytes != metadata["original_bytes"]
            or original_hash.hexdigest() != metadata["original_sha256"]
        ):
            raise ValueError("Oregon decompressed ZIP differs from downloaded source")
    finally:
        temporary.unlink(missing_ok=True)
    return metadata


def _write_csv_atomic(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp",
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        write_csv(temporary, rows, fieldnames)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _row(
    source_id: str,
    source_url: str,
    source_path: Path,
    date: str,
    state: str,
    chamber: str,
    district: str,
    party: str,
    name: str,
    candidate_id: str,
    votes: int,
    locator: str,
    *,
    write_in: bool = False,
    reporting_units: int = 1,
    candidate_party: str | None = None,
) -> dict:
    return {
        "contest_id": "-".join((
            state.casefold(), date, chamber.casefold(), district.casefold(),
            "regular", _slug(party),
        )),
        "cycle": date[:4], "election_date": date, "stage": "primary",
        "state_code": state, "chamber": chamber, "district": district,
        "term": "regular", "election_system": "partisan_primary",
        "primary_party": party, "candidate_name": name,
        "candidate_source_id": candidate_id,
        "party": candidate_party if candidate_party is not None else party,
        "write_in": write_in, "votes": votes, "source_id": source_id,
        "source_url": source_url, "source_sha256": _sha256(source_path),
        "source_locators": locator, "reporting_units": reporting_units,
    }


def parse_idaho_2024(raw_root: Path) -> list[dict]:
    output = []
    for contest_id, district, party in ID_2024_CONTESTS:
        path = raw_root / "id" / "2024" / f"contest-{contest_id}.csv"
        with path.open(encoding="utf-8-sig") as handle:
            rows = list(csv.reader(handle))
        if len(rows) < 2 or rows[0][0] != "County" or rows[1][0] != "Totals":
            raise ValueError(f"Idaho contest schema changed: {contest_id}")
        candidates = []
        for index, header in enumerate(rows[0][1:], 1):
            if header == "Total Votes Cast":
                break
            parts = header.rsplit("\n", 1)
            if len(parts) != 2:
                raise ValueError(f"Idaho candidate lacks party: {header!r}")
            name, source_party = parts
            candidates.append((index, name, source_party))
        for index, name, source_party in candidates:
            votes = int(rows[1][index].replace(",", ""))
            output.append(_row(
                f"id-2024-primary-{contest_id}",
                (
                    "https://canvass.sos.idaho.gov/eng/contests/view/"
                    f"{contest_id}"
                ),
                path, "2024-05-21", "ID", "House", district, party,
                name, f"{contest_id}:{index}", votes, f"{path.name}:Totals",
                reporting_units=len(rows) - 2, candidate_party=source_party,
            ))
    if len(output) != 11 or len({row["contest_id"] for row in output}) != 8:
        raise ValueError("Idaho 2024 congressional coverage is incomplete")
    return output


def parse_idaho_2026(raw_root: Path) -> list[dict]:
    path = raw_root / "id/2026/id-2026-primary-canvass.pdf"
    text = (raw_root / "id/2026/id-2026-primary-canvass.txt").read_text()
    expected_totals = {
        "Contest Total 14,863 29,534 3,344": "Senate Democratic",
        "Contest Total 855": "Senate Libertarian",
        "Contest Total 10,182 156,140": "Senate Republican first columns",
        "32,636 33,188 112 16,344": "Senate Republican remaining columns",
        "Contest Total 18,907": "House 1 Democratic first candidate",
        "2,803 7 1,040": "House 1 Democratic second candidate",
        "Contest Total 14,438": "House 1 Republican first candidate",
        "13,407 100,104 15 12,035": "House 1 Republican remaining candidates",
        "Contest Total 19,523": "House 2 Democratic first candidate",
        "7,411 12 2,150": "House 2 Democratic second candidate",
        "Contest Total 20,975": "House 2 Republican first candidate",
        "63,448 15,802 71 8,299": "House 2 Republican remaining candidates",
        "Contest Total 336": "House 2 Libertarian",
    }
    for needle, label in expected_totals.items():
        if needle not in text:
            raise ValueError(f"Idaho 2026 canvass differs for {label}")
    output = []
    page_map = {
        ("Senate", "Democratic"): 4, ("Senate", "Libertarian"): 7,
        ("Senate", "Republican"): 10, ("House-01", "Democratic"): 11,
        ("House-01", "Republican"): 12, ("House-02", "Democratic"): 14,
        ("House-02", "Republican"): 16, ("House-02", "Libertarian"): 18,
    }
    for (chamber, district, party), candidates in ID_2026_RESULTS.items():
        page_key = (chamber if chamber == "Senate" else f"House-{district}", party)
        for index, (name, votes) in enumerate(candidates):
            output.append(_row(
                "id-2026-primary-canvass",
                (
                    "https://archive.voteidaho.gov/results/2026/primary/"
                    "canvass_report_2026_primary.pdf"
                ),
                path, "2026-05-19", "ID", chamber, district, party,
                name, f"{district}:{_slug(party)}:{index}", votes,
                f"{path.name}:page-{page_map[page_key]}",
                reporting_units=44, candidate_party=party,
            ))
    if len(output) != 19 or len({row["contest_id"] for row in output}) != 8:
        raise ValueError("Idaho 2026 federal coverage is incomplete")
    return output


def parse_nm_2024(raw_root: Path) -> list[dict]:
    output = []
    for contest_id, chamber, district, party in NM_2024_CONTESTS:
        path = raw_root / "nm" / "2024" / f"contest-{contest_id}.csv"
        with path.open(encoding="utf-8-sig") as handle:
            rows = list(csv.reader(handle))
        if len(rows) < 3 or rows[2][0] not in {"State", "Congressional District"}:
            raise ValueError(f"New Mexico contest schema changed: {contest_id}")
        for index, name in enumerate(rows[0][2:], 2):
            if name in {"Total Votes Cast", "Total Ballots Cast"}:
                break
            source_party = rows[1][index]
            output.append(_row(
                f"nm-2024-primary-{contest_id}",
                f"https://electionstats.sos.nm.gov/contest/{contest_id}",
                path, "2024-06-04", "NM", chamber, district, party,
                name, f"{contest_id}:{index}", int(rows[2][index].replace(",", "")),
                f"{path.name}:row-3", reporting_units=sum(1 for row in rows if row[0] == "County"),
                candidate_party=source_party,
            ))
    reviewed_path = raw_root / "nm" / "2024" / "nm-2024-cd3-reviewed.csv"
    with reviewed_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            output.append(_row(
                "nm-2024-primary-cd3-official-page", row["source_url"], reviewed_path,
                row["election_date"], "NM", row["chamber"], row["district"],
                row["primary_party"], row["candidate_name"], row["candidate_source_id"],
                int(row["votes"]), row["source_locator"],
                write_in=row["write_in"] == "true", candidate_party=row["party"],
            ))
    if len(output) != 9 or len({row["contest_id"] for row in output}) != 8:
        raise ValueError("New Mexico 2024 federal coverage is incomplete")
    return output


def parse_nm_2026(raw_root: Path) -> list[dict]:
    output = []
    for filename, chamber, district, party in NM_2026_FILES:
        path = raw_root / "nm" / "2026" / filename
        data = json.loads(path.read_text())
        groups = {}
        for index, item in enumerate(data):
            candidate_id = item["CandidateID"]
            group = groups.setdefault(candidate_id, {
                "name": item["calcCandidate"], "party": item["PartyCode"],
                "votes": 0, "units": 0, "locators": [],
            })
            value = item["calcCandidateVotes"]
            if str(value).isdigit():
                group["votes"] += int(value)
            elif value != "*":
                raise ValueError(f"Invalid New Mexico 2026 total: {value!r}")
            group["units"] += 1
            group["locators"].append(index)
        for candidate_id, group in groups.items():
            name = group["name"]
            statewide_total = NM_2026_STATE_TOTALS[candidate_id]
            if group["votes"] > statewide_total or statewide_total - group["votes"] > 1:
                raise ValueError(
                    f"New Mexico county totals do not reconcile for {candidate_id}"
                )
            output.append(_row(
                f"nm-2026-{filename.removesuffix('.json')}",
                (
                    "https://electionresults-api.sos.nm.gov/NMResultsAjax.svc/"
                    "GetMapData?type=FED&category=CTY"
                ),
                path, "2026-06-02", "NM", chamber, district, party,
                re.sub(r"\s*\(write in\)$", "", name, flags=re.I),
                candidate_id, statewide_total,
                f"{filename}:items-{min(group['locators'])}-{max(group['locators'])}",
                write_in="write in" in name.casefold(),
                reporting_units=group["units"], candidate_party=party,
            ))
    if len(output) != 10 or len({row["contest_id"] for row in output}) != 8:
        raise ValueError("New Mexico 2026 federal coverage is incomplete")
    return output


def parse_oregon_2024(raw_root: Path) -> list[dict]:
    path = raw_root / "or" / "2024" / "or-2024-primary-abstract.pdf"
    output = []
    page_by_district = {"01": 3, "02": 4, "03": 6, "04": 7, "05": 8, "06": 9}
    for (district, party), candidates in OR_2024_RESULTS.items():
        for index, (name, votes, write_in) in enumerate(candidates):
            output.append(_row(
                "or-2024-primary-abstract",
                (
                    "https://sos.oregon.gov/elections/Documents/results/"
                    "may-primary-2024-results.pdf"
                ),
                path, "2024-05-21", "OR", "House", district, party,
                name, f"{district}:{_slug(party)}:{index}", votes,
                f"{path.name}:page-{page_by_district[district]}",
                write_in=write_in, candidate_party="" if write_in else party,
            ))
    if len(output) != 42 or len({row["contest_id"] for row in output}) != 12:
        raise ValueError("Oregon 2024 federal coverage is incomplete")
    return output


def parse_oregon_2026(raw_root: Path) -> list[dict]:
    path = raw_root / "or" / "2026" / "or-2026-primary-official-results.pdf"
    text_path = raw_root / "or" / "2026" / "or-2026-primary-official-results.txt"
    text = text_path.read_text()
    page1 = text.split("\fPAGE 1", 1)[1].split("\fPAGE 2", 1)[0]
    county_lines = [
        line for line in page1.splitlines()
        if any(line.startswith(f"{county} ") for county in OREGON_COUNTIES)
    ]
    found_counties = {
        county for county in OREGON_COUNTIES
        if sum(line.startswith(f"{county} ") for line in county_lines) == 1
    }
    if found_counties != OREGON_COUNTIES or len(county_lines) != 36:
        raise ValueError("Oregon statewide abstract does not contain 36 unique counties")
    if "Lincoln 7,455 438 39" not in page1:
        raise ValueError("Oregon Lincoln Democratic Senate row differs from county final")
    page2 = text.split("\fPAGE 2", 1)[1].split("\fPAGE 3", 1)[0]
    if "Lincoln 1,006 209 122 595 1,300 81 1,191 46" not in page2:
        raise ValueError("Oregon Lincoln Republican Senate row differs from county final")
    page7 = text.split("\fPAGE 7", 1)[1].split("\fPAGE 8", 1)[0]
    if (
        "Lincoln 145 1,543 5,956 48" not in page7
        or "Lincoln 3,604 756 39" not in page7
    ):
        raise ValueError("Oregon Lincoln District 4 rows differ from county final")
    output = []
    for (chamber, district, party), candidates in OR_2026_RESULTS.items():
        page = {"S": 1, "01": 3, "02": 4, "03": 6, "04": 7, "05": 8, "06": 9}[district]
        for index, (name, votes, write_in) in enumerate(candidates):
            output.append(_row(
                "or-2026-primary-official-results",
                "https://records.sos.state.or.us/ORSOSCMSearch/",
                path, "2026-05-19", "OR", chamber, district, party,
                name, f"{district}:{_slug(party)}:{index}", votes,
                f"{path.name}:page-{page}",
                write_in=write_in, candidate_party="" if write_in else party,
                reporting_units=36 if chamber == "Senate" else 1,
            ))
    if len(output) != 51 or len({row["contest_id"] for row in output}) != 14:
        raise ValueError("Oregon 2026 federal coverage is incomplete")
    return output


def export_party_contest_accounting(output_root: Path) -> list[dict]:
    result_paths = (
        (output_root / "western_primary_results.csv", "results_complete"),
        (output_root / "western" / "partial_primary_results.csv", "results_partial"),
        (output_root / RESULT_FILENAME, "results_complete"),
    )
    accounting = {}
    source_urls_by_id = {}
    for manifest_path in (
        output_root / "western" / "source_manifest.csv",
        output_root / MANIFEST_SUBDIR / "source_manifest.csv",
    ):
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                source_url = row["source_url"]
                if not source_url.startswith(("http://", "https://")):
                    source_url = row["publication_url"]
                source_urls_by_id[row["source_id"]] = source_url
    for path, result_status in result_paths:
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                key = (
                    row["cycle"], row["election_date"], row["state_code"],
                    row["chamber"], row["district"], row["term"], row["stage"],
                    row["primary_party"],
                )
                item = accounting.setdefault(key, {
                    "cycle": row["cycle"], "election_date": row["election_date"],
                    "state_code": row["state_code"], "chamber": row["chamber"],
                    "district": row["district"], "term": row["term"],
                    "stage": row["stage"], "primary_party": row["primary_party"],
                    "status": result_status, "candidate_names": [],
                    "source_urls": [], "locators": [], "notes": "",
                })
                item["candidate_names"].append(row["candidate_name"])
                item["source_urls"].append(row["source_url"])
                item["locators"].append(row["source_locators"])

    coverage_paths = (
        output_root / "western" / "contest_coverage.csv",
        output_root / MANIFEST_SUBDIR / "contest_coverage.csv",
    )
    for path in coverage_paths:
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                key = (
                    row["cycle"], row["election_date"], row["state_code"],
                    row["chamber"], row["district"], "regular", "primary",
                    row["primary_party"],
                )
                coverage_status = row["coverage_status"]
                if (
                    key in accounting
                    and coverage_status
                    == "official_results_partial_missing_aggregate_write_in"
                ):
                    accounting[key]["status"] = "results_partial"
                    accounting[key]["notes"] = row["notes"]
                    accounting[key]["locators"].append(row["source_ids"])
                    continue
                if key in accounting:
                    continue
                if coverage_status == "not_regularly_scheduled":
                    status = "not_scheduled"
                elif coverage_status in {
                    "open_official_results_unrecovered",
                    "official_results_unrecovered",
                    "official_roster_only_results_unrecovered",
                }:
                    status = "unresolved"
                elif coverage_status == "official_no_primary_contest":
                    # These are replaced below only when explicit candidate/no-primary
                    # evidence is available. Otherwise absence is unresolved.
                    status = "unresolved"
                else:
                    continue
                accounting[key] = {
                    "cycle": row["cycle"], "election_date": row["election_date"],
                    "state_code": row["state_code"], "chamber": row["chamber"],
                    "district": row["district"], "term": "regular", "stage": "primary",
                    "primary_party": row["primary_party"], "status": status,
                    "candidate_names": [],
                    "source_urls": [
                        source_urls_by_id[source_id]
                        for source_id in row["source_ids"].split("|")
                        if source_id in source_urls_by_id
                    ],
                    "locators": [row["source_ids"]] if row["source_ids"] else [],
                    "notes": row["notes"],
                }

    fallback_urls = {
        ("ID", "2026"): [
            "https://voteidaho.gov/",
            "https://sos.idaho.gov/election-information/",
        ],
        ("OR", "2026"): ["https://records.sos.state.or.us/"],
        ("NV", "2024"): [
            "https://silverstateelection.nv.gov/",
            "https://www.clarkcountynv.gov/government/departments/elections/24p-info",
        ],
        ("NV", "2026"): [
            "https://silverstateelection.nv.gov/",
            "https://www.nvsos.gov/home/showpublisheddocument/18368/639135026079800000",
        ],
    }
    for item in accounting.values():
        if not item["source_urls"] and (item["state_code"], item["cycle"]) in fallback_urls:
            item["source_urls"] = fallback_urls[(item["state_code"], item["cycle"])]
    nv_cd2_key = (
        "2024", "2024-06-11", "NV", "House", "02", "regular", "primary",
        "Democratic",
    )
    if nv_cd2_key in accounting:
        accounting[nv_cd2_key].update({
            "status": "unresolved",
            "candidate_names": [],
            "source_urls": [
                "https://www.humboldtcountynv.gov/DocumentCenter/View/7426",
                "https://silverstateelection.nv.gov/",
            ],
            "locators": ["Humboldt final summary:District 2 Republican only"],
            "notes": (
                "No explicit statewide official no-primary or sole-nominee evidence was "
                "recovered for the Democratic unit; absence is not promoted to no-primary."
            ),
        })

    for cycle, date, chamber, district, party, name in UTAH_NOMINATIONS:
        key = (cycle, date, "UT", chamber, district, "regular", "primary", party)
        if key in accounting:
            continue
        accounting[key] = {
            "cycle": cycle, "election_date": date, "state_code": "UT",
            "chamber": chamber, "district": district, "term": "regular",
            "stage": "primary", "primary_party": party,
            "status": "unopposed_nomination_verified", "candidate_names": [name],
            "source_urls": [
                f"https://vote.utah.gov/{cycle}-candidate-filings/"
            ],
            "locators": [f"Federal Offices:{chamber} {district}:{party}:{name}"],
            "notes": (
                "Official filing status shows the candidate advanced from the party "
                "process without a numeric primary result."
            ),
        }

    for cycle, date, chamber, district, party, name, url, locator, notes in (
        NEVADA_NOMINATIONS
    ):
        key = (cycle, date, "NV", chamber, district, "regular", "primary", party)
        accounting[key] = {
            "cycle": cycle, "election_date": date, "state_code": "NV",
            "chamber": chamber, "district": district, "term": "regular",
            "stage": "primary", "primary_party": party,
            "status": "unopposed_nomination_verified", "candidate_names": [name],
            "source_urls": [url], "locators": [locator], "notes": notes,
        }

    rows = []
    for item in accounting.values():
        row = dict(item)
        row["candidate_names"] = "|".join(dict.fromkeys(row["candidate_names"]))
        row["source_urls"] = "|".join(dict.fromkeys(row["source_urls"]))
        row["locators"] = "|".join(dict.fromkeys(row["locators"]))
        if row["status"] not in PARTY_ACCOUNTING_STATUSES:
            raise ValueError(f"Unknown party accounting status: {row['status']}")
        rows.append(row)
    rows.sort(key=lambda row: (
        row["cycle"], row["election_date"], row["state_code"], row["chamber"],
        row["district"], row["primary_party"],
    ))
    _write_csv_atomic(
        output_root / MANIFEST_SUBDIR / "party_contest_accounting.csv",
        rows, PARTY_ACCOUNTING_FIELDS,
    )
    return rows


def export_provider_raw_artifacts(output_root: Path) -> list[dict]:
    repo_root = RAW_DIR.parent.parent
    rows = {}
    providers = (
        (
            "western_primaries",
            output_root / "western" / "source_manifest.csv",
            RAW_DIR / "western_primaries",
        ),
        (
            "northwest_primaries",
            output_root / MANIFEST_SUBDIR / "source_manifest.csv",
            RAW_DIR / RAW_SUBDIR,
        ),
    )
    for provider, manifest_path, raw_root in providers:
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            for source in csv.DictReader(handle):
                path = raw_root / source["raw_filename"]
                if not path.is_file() or path.stat().st_size == 0:
                    continue
                relative = str(path.relative_to(repo_root))
                rows[(provider, relative)] = {
                    "provider": provider, "path": relative,
                    "sha256": _sha256(path), "bytes": path.stat().st_size,
                    "artifact_type": source["artifact_kind"],
                }
    extras = (
        (
            "western_primaries",
            RAW_DIR / (
                "western_primaries/ut/2024/"
                "ut-2024-primary-candidate-certification.pdf"
            ),
            "official_candidate_certification_pdf",
        ),
        (
            "western_primaries",
            RAW_DIR / "western_primaries/ut/2026/ut-2026-candidate-filings.xlsx",
            "official_candidate_filing_workbook",
        ),
        (
            "northwest_primaries",
            RAW_DIR / "northwest_primaries/or/2026/or-2026-certified-ballot.pdf",
            "official_candidate_certification_pdf",
        ),
    )
    for provider, path, artifact_type in extras:
        if not path.is_file() or path.stat().st_size == 0:
            continue
        relative = str(path.relative_to(repo_root))
        rows[(provider, relative)] = {
            "provider": provider, "path": relative, "sha256": _sha256(path),
            "bytes": path.stat().st_size, "artifact_type": artifact_type,
        }
    split_manifest = (
        RAW_DIR / RAW_SUBDIR / "or/2026/"
        "or-2026-primary-county-results.zip.gz.parts.json"
    )
    split_metadata = json.loads(split_manifest.read_text())
    for part in split_metadata["parts"]:
        path = split_manifest.parent / part["filename"]
        relative = str(path.relative_to(repo_root))
        rows[("northwest_primaries", relative)] = {
            "provider": "northwest_primaries",
            "path": relative,
            "sha256": part["sha256"],
            "bytes": part["bytes"],
            "artifact_type": "official_records_archive_zip_gzip_part",
        }
    output = sorted(rows.values(), key=lambda row: (row["provider"], row["path"]))
    _write_csv_atomic(
        output_root / MANIFEST_SUBDIR / "provider_raw_artifacts.csv",
        output, PROVIDER_RAW_FIELDS,
    )
    return output


def collect_northwest_primaries() -> dict:
    raw_root = RAW_DIR / RAW_SUBDIR
    output_root = ANALYSIS_DATA_DIR / "congressional"
    manifest_root = output_root / MANIFEST_SUBDIR
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)
    results = (
        parse_idaho_2024(raw_root)
        + parse_idaho_2026(raw_root)
        + parse_oregon_2024(raw_root)
        + parse_oregon_2026(raw_root)
        + parse_nm_2024(raw_root)
        + parse_nm_2026(raw_root)
    )
    results.sort(key=lambda row: (
        row["state_code"], row["cycle"], row["chamber"], row["district"],
        row["primary_party"], row["candidate_name"],
    ))
    if any(set(row) != set(FIELDS) for row in results):
        raise ValueError("Northwest result schema differs from canonical fields")
    keys = [(row["contest_id"], row["candidate_source_id"]) for row in results]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate northwest candidate identity")

    manifest = []
    source_groups = {}
    for row in results:
        source_groups.setdefault(row["source_id"], []).append(row)
    paths = {
        "or-2024-primary-abstract": raw_root / "or/2024/or-2024-primary-abstract.pdf",
        "or-2026-primary-official-results": (
            raw_root / "or/2026/or-2026-primary-official-results.pdf"
        ),
        "nm-2024-primary-cd3-official-page": (
            raw_root / "nm/2024/nm-2024-cd3-reviewed.csv"
        ),
    }
    for contest_id, _, _ in ID_2024_CONTESTS:
        paths[f"id-2024-primary-{contest_id}"] = raw_root / f"id/2024/contest-{contest_id}.csv"
    paths["id-2026-primary-canvass"] = raw_root / "id/2026/id-2026-primary-canvass.pdf"
    for contest_id, *_ in NM_2024_CONTESTS:
        paths[f"nm-2024-primary-{contest_id}"] = raw_root / f"nm/2024/contest-{contest_id}.csv"
    for filename, *_ in NM_2026_FILES:
        paths[f"nm-2026-{filename.removesuffix('.json')}"] = raw_root / f"nm/2026/{filename}"
    for source_id, rows in sorted(source_groups.items()):
        path = paths[source_id]
        state = rows[0]["state_code"]
        manifest.append({
            "source_id": source_id, "state_code": state,
            "election_date": rows[0]["election_date"],
            "artifact_kind": (
                "official_statewide_abstract_pdf" if source_id.startswith("or-")
                else "official_statewide_canvass_pdf"
                if source_id == "id-2026-primary-canvass"
                else "reviewed_official_page_extraction"
                if source_id.endswith("official-page")
                else "official_public_api_json"
                if source_id.startswith("nm-2026") else "official_contest_csv"
            ),
            "authority": {
                "ID": "Idaho Secretary of State",
                "OR": "Oregon Secretary of State",
                "NM": "New Mexico Secretary of State",
            }[state],
            "publication_url": rows[0]["source_url"], "source_url": rows[0]["source_url"],
            "raw_filename": str(path.relative_to(raw_root)), "sha256": _sha256(path),
            "verification_status": "verified_official",
            "certification_status": "certified",
            "candidate_rows": len(rows),
            "contests": len({row["contest_id"] for row in rows}),
            "coverage": "all candidates and ballot options in the registered contest/source",
            "notes": "",
        })
    or26_metadata = validate_oregon_2026_split_archive(raw_root)
    or26 = (
        raw_root / "or/2026/"
        "or-2026-primary-county-results.zip.gz.parts.json"
    )
    manifest.append({
        "source_id": "or-2026-primary-county-results", "state_code": "OR",
        "election_date": "2026-05-19",         "artifact_kind": "official_records_archive_zip_gzip_parts",
        "authority": "Oregon Secretary of State",
        "publication_url": "https://records.sos.state.or.us/",
        "source_url": "Oregon State Archives record EPD/26/113",
        "raw_filename": str(or26.relative_to(raw_root)), "sha256": _sha256(or26),
        "verification_status": "verified_supporting_county_set",
        "certification_status": "county_certified_returns",
        "candidate_rows": 0, "contests": 0,
        "coverage": "35 county PDFs plus separately captured Lincoln County final report",
        "notes": (
            "Deterministic gzip split into sub-100MiB parts. Decompression verifies original "
            f"ZIP sha256={or26_metadata['original_sha256']} bytes="
            f"{or26_metadata['original_bytes']}."
        ),
    })
    lincoln = raw_root / "or/2026/counties/Lincoln.pdf"
    manifest.append({
        "source_id": "or-2026-lincoln-final-results", "state_code": "OR",
        "election_date": "2026-05-19", "artifact_kind": "official_county_final_pdf",
        "authority": "Lincoln County Clerk",
        "publication_url": "https://www.co.lincoln.or.us/1296/May-19-2026-Primary-Election",
        "source_url": (
            "https://www.co.lincoln.or.us/DocumentCenter/View/8425/"
            "Election-Results-for-May-19-2026-Primary?bidId="
        ),
        "raw_filename": str(lincoln.relative_to(raw_root)), "sha256": _sha256(lincoln),
        "verification_status": "verified_official",
        "certification_status": "final_official",
        "candidate_rows": 0, "contests": 4,
        "coverage": "Lincoln County Senate and U.S. House District 4 final totals",
        "notes": "Rows reconcile exactly to the statewide abstract county table.",
    })

    coverage = []
    for contest_id in sorted({row["contest_id"] for row in results}):
        rows = [row for row in results if row["contest_id"] == contest_id]
        first = rows[0]
        coverage.append({
            "state_code": first["state_code"], "cycle": first["cycle"],
            "election_date": first["election_date"], "chamber": first["chamber"],
            "district": first["district"], "primary_party": first["primary_party"],
            "coverage_status": "complete_certified_results",
            "candidate_rows": len(rows), "source_ids": "|".join(
                sorted({row["source_id"] for row in rows})
            ), "notes": "",
        })
    for state, cycle, date, chamber, district, party in [
        ("ID", "2026", "2026-05-19", "Senate", "S", "Constitution"),
        ("ID", "2026", "2026-05-19", "House", "01", "Constitution"),
        ("ID", "2026", "2026-05-19", "House", "01", "Libertarian"),
        ("ID", "2026", "2026-05-19", "House", "02", "Constitution"),
    ]:
        coverage.append({
            "state_code": state, "cycle": cycle, "election_date": date,
            "chamber": chamber, "district": district, "primary_party": party,
            "coverage_status": "open_official_results_unrecovered",
            "candidate_rows": 0,             "source_ids": "",
            "notes": "Possible recognized-party unit pending the official canvass.",
        })
    coverage.extend([
        {
            "state_code": "ID", "cycle": "2024", "election_date": "2024-05-21",
            "chamber": "Senate", "district": "S", "primary_party": "",
            "coverage_status": "not_regularly_scheduled", "candidate_rows": 0,
            "source_ids": "", "notes": "No U.S. Senate seat scheduled in 2024.",
        },
        {
            "state_code": "OR", "cycle": "2024", "election_date": "2024-05-21",
            "chamber": "Senate", "district": "S", "primary_party": "",
            "coverage_status": "not_regularly_scheduled", "candidate_rows": 0,
            "source_ids": "or-2024-primary-abstract",
            "notes": "No U.S. Senate contest appears in the certified abstract.",
        },
    ])

    gaps = [
        {
            "gap_id": "id-2026-federal-primary", "state_code": "ID", "cycle": "2026",
            "chamber": "House|Senate",
            "coverage_status": "official_nomination_evidence_unrecovered",
            "recovered_scope": "all 8 numeric federal primary contests and 19 candidates",
            "missing_scope": (
                "explicit candidate/no-primary evidence for Constitution Senate/House 01/"
                "House 02 and Libertarian House 01"
            ),
            "blocker": "certified canvass absence alone cannot establish no candidate/no primary",
            "next_authoritative_step": "recover the certified 2026 federal candidate list",
            "source_urls": (
                "https://archive.voteidaho.gov/results/2026/primary/"
                "canvass_report_2026_primary.pdf"
            ),
        },
    ]
    attempts = [
        {
            "attempt_id": "id-2026-canvass-routes", "attempted_on": "2026-09-22",
            "state_code": "ID", "cycle": "2026",
            "source_url": "https://sos.idaho.gov/elections/data/results/2026/",
            "method": "official_site_and_historical_database",
            "outcome": "current_voteidaho_canvass_recovered",
            "raw_evidence": "id/2026/id-2026-primary-canvass.pdf",
            "notes": "Used current VoteIdaho certification, not the historical database.",
        },
        {
            "attempt_id": "or-2026-records-archive", "attempted_on": "2026-09-22",
            "state_code": "OR", "cycle": "2026",
            "source_url": "Oregon State Archives EPD/26/3 and EPD/26/113",
            "method": "official_records_postback_download_and_county_reconciliation",
            "outcome": "complete_statewide_abstract_reconciled_to_36_counties",
            "raw_evidence": (
                "or/2026/or-2026-primary-official-results.pdf|"
                "or/2026/or-2026-primary-county-results.zip.gz.parts.json|"
                "or/2026/counties/Lincoln.pdf"
            ),
            "notes": "State abstract county rows are unique; Lincoln matches its clerk final.",
        },
    ]
    _write_csv_atomic(output_root / RESULT_FILENAME, results, FIELDS)
    _write_csv_atomic(manifest_root / "source_manifest.csv", manifest, SOURCE_FIELDS)
    _write_csv_atomic(manifest_root / "contest_coverage.csv", coverage, COVERAGE_FIELDS)
    _write_csv_atomic(manifest_root / "unresolved_gaps.csv", gaps, GAP_FIELDS)
    _write_csv_atomic(manifest_root / "attempt_ledger.csv", attempts, ATTEMPT_FIELDS)
    party_accounting = export_party_contest_accounting(output_root)
    raw_artifacts = export_provider_raw_artifacts(output_root)
    return {
        "candidate_rows": len(results),
        "contests": len({row["contest_id"] for row in results}),
        "sources": len(manifest),
        "remaining_gaps": len(gaps),
        "party_accounting_rows": len(party_accounting),
        "raw_artifact_rows": len(raw_artifacts),
    }


def main() -> None:
    argparse.ArgumentParser().parse_args()
    print(collect_northwest_primaries())


if __name__ == "__main__":
    main()
