"""Recover official Georgia and Wisconsin congressional primary returns."""

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .io import write_csv
from .paths import ANALYSIS_DATA_DIR, RAW_DIR
from .state_results import FIELDS

RAW_SUBDIR = "ga_wi_primaries"
RESULT_FILENAME = "ga_wi_primary_results.csv"
MANIFEST_SUBDIR = "ga_wi"

PARTY_CODES = {"DEM": "Democratic", "REP": "Republican"}
WISCONSIN_BALLOT_CATEGORIES = {
    "Democratic",
    "Republican",
    "Constitution",
    "Libertarian",
    "Wisconsin Green",
}

SOURCE_MANIFEST_FIELDS = [
    "source_id",
    "state_code",
    "election_date",
    "stage",
    "artifact_kind",
    "authority",
    "publication_url",
    "source_url",
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
    "ballot_candidate_count",
    "printed_candidate_count",
    "unopposed",
    "write_in_only",
    "has_write_in_option",
    "actual_zero_rows",
    "nonnumeric_result",
    "result_status",
    "certification_status",
    "primary_party_semantics",
    "party_field_semantics",
    "source_id",
]

GA_RESULTS_BASE = "https://results.sos.ga.gov"
GA_PUBLICATION = "https://sos.ga.gov/page/georgia-election-results"
WI_PUBLICATION = "https://elections.wi.gov/elections/election-results"

GA_SOURCES = (
    {
        "source_id": "ga-2024-general-primary-results",
        "date": "2024-05-21",
        "stage": "primary",
        "slug": "2024MayGenPri",
        "filename": "ga/2024/2024MayGenPri-ballot-items.json",
        "metadata": "ga/2024/2024MayGenPri-metadata.json",
        "expected_contests": {
            ("House", f"{district:02}", party)
            for district in range(1, 15)
            for party in ("Democratic", "Republican")
        },
    },
    {
        "source_id": "ga-2024-general-primary-runoff-results",
        "date": "2024-06-18",
        "stage": "primary_runoff",
        "slug": "2024JunPriRunoff",
        "filename": "ga/2024/2024JunPriRunoff-ballot-items.json",
        "metadata": "ga/2024/2024JunPriRunoff-metadata.json",
        "expected_contests": {
            ("House", "02", "Republican"),
            ("House", "03", "Republican"),
            ("House", "14", "Democratic"),
        },
    },
    {
        "source_id": "ga-2026-general-primary-results",
        "date": "2026-05-19",
        "stage": "primary",
        "slug": "GeneralPrimary51926",
        "filename": "ga/2026/GeneralPrimary51926-ballot-items.json",
        "metadata": "ga/2026/GeneralPrimary51926-metadata.json",
        "expected_contests": {
            *{
                ("House", f"{district:02}", party)
                for district in range(1, 15)
                for party in ("Democratic", "Republican")
            },
            ("Senate", "S", "Democratic"),
            ("Senate", "S", "Republican"),
        },
    },
    {
        "source_id": "ga-2026-general-primary-runoff-results",
        "date": "2026-06-16",
        "stage": "primary_runoff",
        "slug": "06162026GeneralPrimaryRunoff",
        "filename": "ga/2026/06162026GeneralPrimaryRunoff-ballot-items.json",
        "metadata": "ga/2026/06162026GeneralPrimaryRunoff-metadata.json",
        "expected_contests": {
            ("Senate", "S", "Republican"),
            ("House", "01", "Democratic"),
            ("House", "07", "Democratic"),
            ("House", "11", "Republican"),
            ("House", "12", "Democratic"),
        },
    },
)

WI_PDF_SOURCES = {
    "wi-2024-partisan-primary-us-house-county-canvass.pdf": {
        "source_id": "wi-2024-partisan-primary-house-canvass",
        "date": "2024-08-13",
        "stage": "primary",
        "url": (
            "https://elections.wi.gov/sites/default/files/documents/"
            "County%20by%20County%20Report_US%20Congress.pdf"
        ),
        "source_date": "2024-08-26",
    },
    "wi-2024-partisan-primary-us-senate-county-canvass.pdf": {
        "source_id": "wi-2024-partisan-primary-senate-canvass",
        "date": "2024-08-13",
        "stage": "primary",
        "url": (
            "https://elections.wi.gov/sites/default/files/documents/"
            "County%20by%20County%20Report%20-%20US%20Senate.pdf"
        ),
        "source_date": "2024-08-26",
    },
    "wi-2026-partisan-primary-summary.pdf": {
        "source_id": "wi-2026-partisan-primary-congressional-canvass",
        "date": "2026-08-11",
        "stage": "primary",
        "url": (
            "https://elections.wi.gov/sites/default/files/documents/"
            "August%202026%20Partisan%20Primary_Summary%20Results.pdf"
        ),
        "source_date": "2026-08-27",
    },
}

WI_EXTRACTIONS = (
    {
        "date": "2024-08-13",
        "stage": "primary",
        "filename": "wi/2024/wi-2024-partisan-primary-congressional-extraction.csv",
        "expected_contests": {
            *{
                ("House", f"{district:02}", party)
                for district in range(1, 9)
                for party in WISCONSIN_BALLOT_CATEGORIES
            },
            *{
                ("Senate", "S", party)
                for party in WISCONSIN_BALLOT_CATEGORIES
            },
        },
    },
    {
        "date": "2026-08-11",
        "stage": "primary",
        "filename": "wi/2026/wi-2026-partisan-primary-congressional-extraction.csv",
        "expected_contests": {
            ("House", f"{district:02}", party)
            for district in range(1, 9)
            for party in WISCONSIN_BALLOT_CATEGORIES
        },
    },
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _integer(value: object) -> int:
    text = str(value).strip().replace(",", "")
    if re.fullmatch(r"\d+", text) is None:
        raise ValueError(f"Invalid vote total: {value!r}")
    return int(text)


def _boolean(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().casefold()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise ValueError(f"Invalid boolean: {value!r}")


def _english(values: list[dict]) -> str:
    for value in values:
        if value.get("languageId") == "en":
            return " ".join(str(value.get("text", "")).split())
    raise ValueError("English source label is missing")


def _candidate_name(value: str) -> str:
    text = value.replace('""', '"')
    return re.sub(r"\s+\(I\)$", "", " ".join(text.split())).strip()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _contest_id(
    state: str,
    date: str,
    chamber: str,
    district: str,
    primary_party: str,
) -> str:
    return "-".join((
        state.casefold(),
        date,
        chamber.casefold(),
        district.casefold(),
        "regular",
        _slug(primary_party),
    ))


def _georgia_contest(name: str) -> tuple[str, str, str] | None:
    senate = re.fullmatch(r"US Senate - (Rep|Dem)", name)
    if senate:
        return "Senate", "S", PARTY_CODES[senate[1].upper()]
    house = re.fullmatch(
        r"US House of Representatives - District\s*(\d+)\s*-\s*(Rep|Dem)",
        name,
    )
    if house:
        return "House", house[1].zfill(2), PARTY_CODES[house[2].upper()]
    return None


def parse_georgia(
    results_path: Path,
    metadata_path: Path,
    source: dict,
) -> list[dict]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    if not metadata.get("isOfficialResults"):
        raise ValueError(f'{source["source_id"]}: Georgia results are not official')
    if metadata.get("electionDate") != source["date"]:
        raise ValueError("Georgia metadata contains a different election date")
    payload = json.loads(results_path.read_text(encoding="utf-8-sig"))
    required = {"data", "totalRecordCount"}
    if not required <= set(payload) or len(payload["data"]) != payload["totalRecordCount"]:
        raise ValueError("Georgia ballot-item API schema changed")
    source_hash = _sha256(results_path)
    rows = []
    contests = set()
    for contest_index, contest in enumerate(payload["data"]):
        contest_name = _english(contest["name"])
        parsed = _georgia_contest(contest_name)
        if parsed is None:
            continue
        chamber, district, primary_party = parsed
        contests.add(parsed)
        options = contest["summaryResults"]["ballotOptions"]
        if not options:
            raise ValueError(f"Georgia contest lacks ballot options: {contest_name}")
        if sum(_integer(option["voteCount"]) for option in options) != _integer(
            contest["voteTotal"]
        ):
            raise ValueError(f"Georgia contest total differs: {contest_name}")
        status = contest["reportingStatus"]
        if status["reportingUnits"] != status["totalUnits"]:
            raise ValueError(f"Georgia contest is not fully reported: {contest_name}")
        for option_index, option in enumerate(options):
            write_in = bool(option.get("isWriteIn") or option.get("isQualifiedWriteIn"))
            name = _candidate_name(_english(option["name"]))
            group_results = option.get("groupResults") or []
            votes = _integer(option["voteCount"])
            if group_results and sum(
                _integer(group["voteCount"]) for group in group_results
            ) != votes:
                raise ValueError(f"Georgia vote methods differ: {contest_name}/{name}")
            party_code = (option.get("party") or {}).get("abbreviation", "")
            if not write_in and PARTY_CODES.get(party_code) != primary_party:
                raise ValueError(
                    f"Georgia candidate party differs from ballot category: {name}"
                )
            rows.append({
                "contest_id": _contest_id(
                    "GA", source["date"], chamber, district, primary_party
                ),
                "cycle": source["date"][:4],
                "election_date": source["date"],
                "stage": source["stage"],
                "state_code": "GA",
                "chamber": chamber,
                "district": district,
                "term": "regular",
                "election_system": "partisan_primary",
                "primary_party": primary_party,
                "candidate_name": name,
                "candidate_source_id": f'{contest["id"]}:{option["id"]}',
                "party": "" if write_in else primary_party,
                "write_in": write_in,
                "votes": votes,
                "source_id": source["source_id"],
                "source_url": (
                    f"{GA_RESULTS_BASE}/results/public/api/elections/Georgia/"
                    f"{source['slug']}/ballot-items"
                ),
                "source_sha256": source_hash,
                "source_locators": (
                    f"{results_path.name}:$.data[{contest_index}]"
                    f".summaryResults.ballotOptions[{option_index}]"
                ),
                "reporting_units": len(group_results) or 1,
            })
    if contests != source["expected_contests"]:
        raise ValueError(
            f'{source["source_id"]}: Georgia contest coverage differs: '
            f"{contests ^ source['expected_contests']}"
        )
    return rows


def parse_wisconsin(
    extraction_path: Path,
    raw_root: Path,
    source: dict,
) -> list[dict]:
    with extraction_path.open(newline="", encoding="utf-8") as handle:
        extracted = list(csv.DictReader(handle))
    required = {
        "source_pdf",
        "page",
        "chamber",
        "district",
        "primary_party",
        "candidate_name",
        "candidate_source_id",
        "declared_party",
        "write_in",
        "votes",
        "contest_total",
    }
    if not extracted or not required <= set(extracted[0]):
        raise ValueError("Wisconsin normalized extraction schema changed")
    rows = []
    contests = defaultdict(list)
    seen = set()
    for line_number, row in enumerate(extracted, 2):
        pdf_source = WI_PDF_SOURCES.get(row["source_pdf"])
        if pdf_source is None or pdf_source["date"] != source["date"]:
            raise ValueError(f"Unknown Wisconsin source PDF: {row['source_pdf']}")
        chamber = row["chamber"]
        district = row["district"]
        primary_party = row["primary_party"]
        if primary_party not in WISCONSIN_BALLOT_CATEGORIES:
            raise ValueError(f"Unknown Wisconsin ballot category: {primary_party}")
        write_in = _boolean(row["write_in"])
        declared_party = row["declared_party"].strip()
        if write_in and declared_party:
            raise ValueError("Wisconsin write-in/scattering row asserts a party")
        key = (chamber, district, primary_party, row["candidate_source_id"])
        if key in seen:
            raise ValueError(f"Duplicate Wisconsin candidate: {key}")
        seen.add(key)
        votes = _integer(row["votes"])
        contest_total = _integer(row["contest_total"])
        contests[(chamber, district, primary_party)].append((votes, contest_total))
        pdf_path = raw_root / "wi" / source["date"][:4] / row["source_pdf"]
        rows.append({
            "contest_id": _contest_id(
                "WI", source["date"], chamber, district, primary_party
            ),
            "cycle": source["date"][:4],
            "election_date": source["date"],
            "stage": source["stage"],
            "state_code": "WI",
            "chamber": chamber,
            "district": district,
            "term": "regular",
            "election_system": "partisan_primary",
            "primary_party": primary_party,
            "candidate_name": row["candidate_name"].strip(),
            "candidate_source_id": row["candidate_source_id"],
            "party": declared_party,
            "write_in": write_in,
            "votes": votes,
            "source_id": pdf_source["source_id"],
            "source_url": pdf_source["url"],
            "source_sha256": _sha256(pdf_path),
            "source_locators": (
                f"{row['source_pdf']}:page-{_integer(row['page'])} | "
                f"{extraction_path.name}:line-{line_number}"
            ),
            "reporting_units": 1,
        })
    if set(contests) != source["expected_contests"]:
        raise ValueError(
            f"Wisconsin contest coverage differs: "
            f"{set(contests) ^ source['expected_contests']}"
        )
    for contest, values in contests.items():
        totals = {total for _, total in values}
        if len(totals) != 1 or sum(votes for votes, _ in values) != next(iter(totals)):
            raise ValueError(f"Wisconsin contest total differs: {contest}")
    return rows


def _source_counts(rows: list[dict], source_id: str) -> tuple[int, int]:
    source_rows = [row for row in rows if row["source_id"] == source_id]
    return len(source_rows), len({row["contest_id"] for row in source_rows})


def _manifest_row(
    raw_root: Path,
    path: Path,
    *,
    source_id: str,
    state_code: str,
    election_date: str,
    stage: str,
    artifact_kind: str,
    authority: str,
    publication_url: str,
    source_url: str,
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
        "raw_filename": path.relative_to(raw_root).as_posix(),
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
    manifest = []
    for source in GA_SOURCES:
        results_path = raw_root / source["filename"]
        metadata_path = raw_root / source["metadata"]
        metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        candidate_rows, contests = _source_counts(rows, source["source_id"])
        results_url = (
            f"{GA_RESULTS_BASE}/results/public/api/elections/Georgia/"
            f"{source['slug']}/ballot-items"
        )
        manifest.append(_manifest_row(
            raw_root,
            results_path,
            source_id=source["source_id"],
            state_code="GA",
            election_date=source["date"],
            stage=source["stage"],
            artifact_kind="official_public_ballot_item_api",
            authority="Georgia Secretary of State linked Enhanced Voting service",
            publication_url=(
                f"{GA_RESULTS_BASE}/results/public/Georgia/elections/{source['slug']}"
            ),
            source_url=results_url,
            source_date=metadata["asOf"][:10],
            verification_status="verified_official",
            certification_status="official",
            provisional_status="final_all_reporting_units",
            candidate_rows=candidate_rows,
            contests=contests,
            coverage="all federal ballot items in this election event",
            source_locators="JSON pointers recorded per output row",
            notes=(
                "primary_party is the Rep/Dem ballot contest category. party is "
                "the option party supplied by the API and is blank for write-ins."
            ),
        ))
        manifest.append(_manifest_row(
            raw_root,
            metadata_path,
            source_id=f"{source['source_id']}-metadata",
            state_code="GA",
            election_date=source["date"],
            stage=source["stage"],
            artifact_kind="official_election_metadata",
            authority="Georgia Secretary of State linked Enhanced Voting service",
            publication_url=GA_PUBLICATION,
            source_url=(
                f"{GA_RESULTS_BASE}/results/public/api/elections/Georgia/"
                f"{source['slug']}"
            ),
            source_date=metadata["asOf"][:10],
            verification_status="verified_official",
            certification_status=(
                "official" if metadata["isOfficialResults"] else "not_official"
            ),
            provisional_status="metadata_only",
            candidate_rows=0,
            contests=0,
            coverage="election date, official flag, publication timestamp",
            source_locators="$.electionDate, $.isOfficialResults, $.asOf",
            notes="The parser requires isOfficialResults=true.",
        ))
    for filename, source in WI_PDF_SOURCES.items():
        year = source["date"][:4]
        path = raw_root / "wi" / year / filename
        candidate_rows, contests = _source_counts(rows, source["source_id"])
        manifest.append(_manifest_row(
            raw_root,
            path,
            source_id=source["source_id"],
            state_code="WI",
            election_date=source["date"],
            stage=source["stage"],
            artifact_kind="certified_canvass_pdf",
            authority="Wisconsin Elections Commission",
            publication_url=WI_PUBLICATION,
            source_url=source["url"],
            source_date=source["source_date"],
            verification_status="verified_official",
            certification_status="certified_canvass",
            provisional_status="final_canvassed_totals",
            candidate_rows=candidate_rows,
            contests=contests,
            coverage="congressional ballot categories contained in this PDF",
            source_locators="PDF page numbers recorded per output row",
            notes=(
                "primary_party is the partisan ballot category. party is the "
                "printed candidate affiliation; it is blank for scattering and "
                "named write-ins because ballot category does not prove affiliation."
            ),
        ))
        text_path = path.with_suffix(".txt")
        manifest.append(_manifest_row(
            raw_root,
            text_path,
            source_id=f"{source['source_id']}-text",
            state_code="WI",
            election_date=source["date"],
            stage=source["stage"],
            artifact_kind="derived_pdf_text",
            authority="Derived locally from Wisconsin Elections Commission PDF",
            publication_url=WI_PUBLICATION,
            source_url=source["url"],
            source_date=source["source_date"],
            verification_status="derived_parser_audit",
            certification_status="inherits_pdf",
            provisional_status="inherits_pdf",
            candidate_rows=candidate_rows,
            contests=contests,
            coverage="all PDF pages with form-feed PAGE markers",
            source_locators="PAGE markers preserve physical PDF page numbers",
            notes="Extracted with pypdf 6.16.0; result rows hash the source PDF.",
        ))
    for extraction in WI_EXTRACTIONS:
        path = raw_root / extraction["filename"]
        year = extraction["date"][:4]
        extraction_rows = [
            row for row in rows
            if row["state_code"] == "WI" and row["cycle"] == year
        ]
        manifest.append(_manifest_row(
            raw_root,
            path,
            source_id=f"wi-{year}-congressional-normalized-extraction",
            state_code="WI",
            election_date=extraction["date"],
            stage="primary",
            artifact_kind="derived_structured_extraction",
            authority="Derived locally from certified WEC canvass PDFs",
            publication_url=WI_PUBLICATION,
            source_url=WI_PUBLICATION,
            source_date="2026-09-22",
            verification_status="verified_against_pdf_contest_totals",
            certification_status="inherits_pdf",
            provisional_status="inherits_pdf",
            candidate_rows=len(extraction_rows),
            contests=len({row["contest_id"] for row in extraction_rows}),
            coverage="every congressional PDF contest, candidate, and scattering row",
            source_locators="source_pdf and page columns; CSV line in each result row",
            notes=(
                "Generated with pdfplumber 0.11.8 and pypdf 6.16.0. "
                "candidate_source_id is a deterministic derived locator, not a WEC ID."
            ),
        ))
    return manifest


def _attempt_rows() -> list[dict]:
    attempted_on = "2026-09-22"
    return [
        {
            "attempt_id": "ga-01-historical-inventory",
            "attempted_on": attempted_on,
            "state_code": "GA",
            "cycle": "2024",
            "source_url": "https://sos.ga.gov/page/historical-elections-results",
            "method": "inspect official statewide archive inventory",
            "outcome": "success_event_identification",
            "raw_evidence": "",
            "notes": "Confirmed May 21 primary and June 18 runoff events.",
        },
        {
            "attempt_id": "ga-02-historical-zips",
            "attempted_on": attempted_on,
            "state_code": "GA",
            "cycle": "2024",
            "source_url": (
                "https://sos.ga.gov/sites/default/files/2024-07/"
                "statewide_2024_may_21.zip"
            ),
            "method": "request official historical statewide ZIP",
            "outcome": "blocked_cloudflare_403",
            "raw_evidence": "",
            "notes": "No loop after the documented block; public results API used instead.",
        },
        {
            "attempt_id": "ga-03-election-metadata-api",
            "attempted_on": attempted_on,
            "state_code": "GA",
            "cycle": "2024-2026",
            "source_url": (
                f"{GA_RESULTS_BASE}/results/public/api/elections/Georgia/"
                "GeneralPrimary51926"
            ),
            "method": "call public election metadata endpoints",
            "outcome": "success_official_flags",
            "raw_evidence": "ga/2026/GeneralPrimary51926-metadata.json",
            "notes": "All four events report isOfficialResults=true.",
        },
        {
            "attempt_id": "ga-04-ballot-item-api-2024-primary",
            "attempted_on": attempted_on,
            "state_code": "GA",
            "cycle": "2024",
            "source_url": (
                f"{GA_RESULTS_BASE}/results/public/api/elections/Georgia/"
                "2024MayGenPri/ballot-items"
            ),
            "method": "download official public ballot-item JSON",
            "outcome": "success_complete_primary",
            "raw_evidence": "ga/2024/2024MayGenPri-ballot-items.json",
            "notes": "All 14 House districts and both party ballot categories.",
        },
        {
            "attempt_id": "ga-05-ballot-item-api-2024-runoff",
            "attempted_on": attempted_on,
            "state_code": "GA",
            "cycle": "2024",
            "source_url": (
                f"{GA_RESULTS_BASE}/results/public/api/elections/Georgia/"
                "2024JunPriRunoff/ballot-items"
            ),
            "method": "download official public ballot-item JSON",
            "outcome": "success_complete_runoff",
            "raw_evidence": "ga/2024/2024JunPriRunoff-ballot-items.json",
            "notes": "Three congressional runoff contests recovered.",
        },
        {
            "attempt_id": "ga-06-ballot-item-api-2026",
            "attempted_on": attempted_on,
            "state_code": "GA",
            "cycle": "2026",
            "source_url": (
                f"{GA_RESULTS_BASE}/results/public/api/elections/Georgia/"
                "GeneralPrimary51926/ballot-items"
            ),
            "method": "download primary and runoff public ballot-item JSON",
            "outcome": "success_complete_primary_and_runoff",
            "raw_evidence": "ga/2026/GeneralPrimary51926-ballot-items.json",
            "notes": "All 14 House districts, Senate, and five federal runoffs.",
        },
        {
            "attempt_id": "wi-01-results-page",
            "attempted_on": attempted_on,
            "state_code": "WI",
            "cycle": "2024-2026",
            "source_url": WI_PUBLICATION,
            "method": "request official election-results index",
            "outcome": "blocked_cloudflare_403",
            "raw_evidence": "",
            "notes": "Direct certified document URLs remained publicly accessible.",
        },
        {
            "attempt_id": "wi-02-2024-house-canvass",
            "attempted_on": attempted_on,
            "state_code": "WI",
            "cycle": "2024",
            "source_url": WI_PDF_SOURCES[
                "wi-2024-partisan-primary-us-house-county-canvass.pdf"
            ]["url"],
            "method": "download certified county-by-county House canvass PDF",
            "outcome": "success_complete_house_primary",
            "raw_evidence": (
                "wi/2024/wi-2024-partisan-primary-us-house-county-canvass.pdf"
            ),
            "notes": "All eight districts and five partisan ballot categories.",
        },
        {
            "attempt_id": "wi-03-2024-senate-canvass",
            "attempted_on": attempted_on,
            "state_code": "WI",
            "cycle": "2024",
            "source_url": WI_PDF_SOURCES[
                "wi-2024-partisan-primary-us-senate-county-canvass.pdf"
            ]["url"],
            "method": "download certified county-by-county Senate canvass PDF",
            "outcome": "success_complete_senate_primary",
            "raw_evidence": (
                "wi/2024/wi-2024-partisan-primary-us-senate-county-canvass.pdf"
            ),
            "notes": "All five partisan ballot categories, including scattering.",
        },
        {
            "attempt_id": "wi-04-ballot-candidate-download",
            "attempted_on": attempted_on,
            "state_code": "WI",
            "cycle": "2024",
            "source_url": "https://elections.wi.gov/media/26866/download",
            "method": "request official ballot-candidate download",
            "outcome": "blocked_cloudflare_403",
            "raw_evidence": "",
            "notes": "Not used to infer participation; certified canvass is sufficient.",
        },
        {
            "attempt_id": "wi-05-2026-summary-canvass",
            "attempted_on": attempted_on,
            "state_code": "WI",
            "cycle": "2026",
            "source_url": WI_PDF_SOURCES[
                "wi-2026-partisan-primary-summary.pdf"
            ]["url"],
            "method": "download certified statewide summary canvass PDF",
            "outcome": "success_complete_house_primary",
            "raw_evidence": "wi/2026/wi-2026-partisan-primary-summary.pdf",
            "notes": "All eight districts and five partisan ballot categories.",
        },
        {
            "attempt_id": "wi-06-structured-pdf-extraction",
            "attempted_on": attempted_on,
            "state_code": "WI",
            "cycle": "2024-2026",
            "source_url": WI_PUBLICATION,
            "method": "extract rotated/multi-column canvass tables with coordinates",
            "outcome": "success_verified_against_office_totals",
            "raw_evidence": "wi/2026/wi-2026-partisan-primary-congressional-extraction.csv",
            "notes": "Every normalized contest sum is checked against its PDF total.",
        },
    ]


def _gap_rows(rows: list[dict]) -> list[dict]:
    output = []
    source_urls = {
        ("GA", "2024"): (
            f"{GA_RESULTS_BASE}/results/public/Georgia/elections/2024MayGenPri"
        ),
        ("GA", "2026"): (
            f"{GA_RESULTS_BASE}/results/public/Georgia/elections/GeneralPrimary51926"
        ),
        ("WI", "2024"): WI_PUBLICATION,
        ("WI", "2026"): WI_PUBLICATION,
    }
    for state in ("GA", "WI"):
        for cycle in ("2024", "2026"):
            state_rows = [
                row for row in rows
                if row["state_code"] == state and row["cycle"] == cycle
            ]
            for stage in ("primary", "primary_runoff"):
                stage_rows = [row for row in state_rows if row["stage"] == stage]
                applicable = state == "GA" or stage == "primary"
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
                        if applicable else "Wisconsin has no primary runoff stage"
                    ),
                    "missing_scope": "",
                    "blocker": "",
                    "next_authoritative_step": "none",
                    "source_urls": source_urls[(state, cycle)],
                })
            output.append({
                "gap_id": f"{state.casefold()}-{cycle}-special-primary",
                "state_code": state,
                "cycle": cycle,
                "stage": "special_primary",
                "chamber": "House/Senate",
                "coverage_status": "not_applicable",
                "recovered_scope": (
                    "No congressional special primary in the recovered state inventory"
                ),
                "missing_scope": "",
                "blocker": "",
                "next_authoritative_step": "none",
                "source_urls": source_urls[(state, cycle)],
            })
    return output


def _contest_rows(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["contest_id"]].append(row)
    output = []
    for contest_id, candidates in sorted(groups.items()):
        first = candidates[0]
        printed = [candidate for candidate in candidates if not candidate["write_in"]]
        output.append({
            "contest_id": contest_id,
            "state_code": first["state_code"],
            "cycle": first["cycle"],
            "election_date": first["election_date"],
            "stage": first["stage"],
            "chamber": first["chamber"],
            "district": first["district"],
            "primary_party": first["primary_party"],
            "ballot_candidate_count": len(candidates),
            "printed_candidate_count": len(printed),
            "unopposed": len(printed) == 1,
            "write_in_only": len(printed) == 0,
            "has_write_in_option": any(
                candidate["write_in"] for candidate in candidates
            ),
            "actual_zero_rows": sum(candidate["votes"] == 0 for candidate in candidates),
            "nonnumeric_result": False,
            "result_status": "actual_numeric",
            "certification_status": (
                "official" if first["state_code"] == "GA" else "certified_canvass"
            ),
            "primary_party_semantics": "ballot_or_contest_category",
            "party_field_semantics": (
                "official printed candidate affiliation; blank for "
                "write-in/scattering options"
            ),
            "source_id": first["source_id"],
        })
    return output


def _validate_output(rows: list[dict]) -> None:
    if not rows:
        raise ValueError("No Georgia/Wisconsin primary results generated")
    seen = set()
    for row in rows:
        if set(row) != set(FIELDS):
            raise ValueError(f"Output schema differs: {row.get('candidate_name')}")
        key = (row["contest_id"], row["candidate_source_id"])
        if key in seen:
            raise ValueError(f"Duplicate candidate result: {key}")
        seen.add(key)
        if not isinstance(row["votes"], int) or row["votes"] < 0:
            raise ValueError(f"Invalid candidate total: {row}")
        if row["write_in"] and row["party"]:
            raise ValueError(f"Write-in row asserts candidate affiliation: {row}")
        if len(row["source_sha256"]) != 64 or not row["source_locators"]:
            raise ValueError(f"Incomplete source provenance: {row}")
    expected = {
        ("GA", "2024", "primary"),
        ("GA", "2024", "primary_runoff"),
        ("GA", "2026", "primary"),
        ("GA", "2026", "primary_runoff"),
        ("WI", "2024", "primary"),
        ("WI", "2026", "primary"),
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
    rows = []
    for source in GA_SOURCES:
        rows.extend(parse_georgia(
            raw_root / source["filename"],
            raw_root / source["metadata"],
            source,
        ))
    for source in WI_EXTRACTIONS:
        rows.extend(parse_wisconsin(raw_root / source["filename"], raw_root, source))
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
        description="Generate official Georgia/Wisconsin congressional primary results"
    )
    parser.parse_args()
    rows = generate()
    print(
        f"Wrote {len(rows)} candidate results to "
        f"{ANALYSIS_DATA_DIR / 'congressional' / RESULT_FILENAME}"
    )


if __name__ == "__main__":
    main()
