"""Recover official New Jersey and Florida congressional primary returns."""

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

from .io import write_csv
from .paths import ANALYSIS_DATA_DIR, RAW_DIR
from .state_results import FIELDS

RAW_SUBDIR = "nj_fl_primaries"
RESULT_FILENAME = "nj_fl_primary_results.csv"
MANIFEST_SUBDIR = "nj_fl"

PARTIES = ("Democratic", "Republican")
FL_PARTY_CODES = {"DEM": "Democratic", "REP": "Republican"}

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
    "district",
    "primary_party",
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
    "term",
    "primary_party",
    "candidate_count",
    "unopposed",
    "actual_zero_rows",
    "recount_status",
    "result_status",
    "certification_status",
    "source_id",
]

ROSTER_FIELDS = [
    "state_code",
    "cycle",
    "election_date",
    "stage",
    "chamber",
    "district",
    "term",
    "primary_party",
    "candidate_name",
    "candidate_source_id",
    "source_id",
    "source_url",
    "source_sha256",
    "source_locators",
    "verification_status",
    "notes",
]

COVERAGE_FIELDS = [
    "state_code",
    "cycle",
    "election_date",
    "stage",
    "chamber",
    "district",
    "term",
    "primary_party",
    "coverage_status",
    "result_rows",
    "roster_rows",
    "missing_reason",
    "source_ids",
]

NJ_PUBLICATION = "https://www.nj.gov/state/elections/election-information-{year}.shtml"
NJ_RESULT_BASE = (
    "https://www.nj.gov/state/elections/assets/pdf/election-results"
)
FL_RESULTS_BASE = "https://results.elections.myflorida.com"
FL_CANDIDATE_BASE = "https://dos.elections.myflorida.com/candidates"
FL_PUBLICATION = (
    "https://dos.fl.gov/elections/data-statistics/elections-data/"
    "election-results-archive/"
)

NJ_PDF_SOURCES = {
    "2024-official-primary-results-us-senate.pdf": {
        "source_id": "nj-2024-primary-senate-official-results",
        "date": "2024-06-04",
        "stage": "primary",
        "term": "regular",
        "source_date": "2024-07-02",
    },
    "2024-official-primary-results-us-house.pdf": {
        "source_id": "nj-2024-primary-house-official-results",
        "date": "2024-06-04",
        "stage": "primary",
        "term": "regular",
        "source_date": "2024-07-02",
    },
    "2024-official-special-primary-results-us-house-10cd.pdf": {
        "source_id": "nj-2024-special-primary-house-10-official-results",
        "date": "2024-07-16",
        "stage": "special_primary",
        "term": "special",
        "source_date": "2024-07-31",
    },
    "2026-official-primary-results-us-senate.pdf": {
        "source_id": "nj-2026-primary-senate-official-results",
        "date": "2026-06-02",
        "stage": "primary",
        "term": "regular",
        "source_date": "2026-07-27",
    },
    "2026-official-primary-results-us-house.pdf": {
        "source_id": "nj-2026-primary-house-official-results",
        "date": "2026-06-02",
        "stage": "primary",
        "term": "regular",
        "source_date": "2026-07-27",
    },
    "2026-official-special-primary-results-us-house-11cd.pdf": {
        "source_id": "nj-2026-special-primary-house-11-official-results",
        "date": "2026-02-05",
        "stage": "special_primary",
        "term": "special",
        "source_date": "2026-02-23",
    },
}

NJ_EXTRACTIONS = (
    {
        "date": "2024",
        "filename": "nj/2024/nj-2024-congressional-primary-extraction.csv",
    },
    {
        "date": "2026",
        "filename": "nj/2026/nj-2026-congressional-primary-extraction.csv",
    },
)

FL_SUMMARY_SOURCES = (
    {
        "source_id": "fl-2026-primary-republican-federal-official-results",
        "date": "2026-08-18",
        "stage": "primary",
        "party": "Republican",
        "party_code": "REP",
        "filename": "fl/2026/fl-2026-federal-REP.html",
    },
    {
        "source_id": "fl-2026-primary-democratic-federal-official-results",
        "date": "2026-08-18",
        "stage": "primary",
        "party": "Democratic",
        "party_code": "DEM",
        "filename": "fl/2026/fl-2026-federal-DEM.html",
    },
)

FL_EXPECTED_RESULT_UNITS = {
    ("Senate", "S", "Republican"),
    ("Senate", "S", "Democratic"),
    *{
        ("House", f"{district:02}", "Republican")
        for district in (1, 2, 5, 6, 7, 9, 11, 14, 16, 19, 20, 22, 23, 25, 27)
    },
    *{
        ("House", f"{district:02}", "Democratic")
        for district in (
            2, 3, 4, 5, 6, 7, 11, 12, 13, 15,
            16, 17, 19, 20, 21, 22, 23, 24, 25, 27,
        )
    },
}

FL_RECOUNT_UNITS = {("House", "11", "Republican")}


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


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _contest_id(
    state: str,
    date: str,
    chamber: str,
    district: str,
    term: str,
    primary_party: str,
) -> str:
    return "-".join((
        state.casefold(),
        date,
        chamber.casefold(),
        district.casefold(),
        term,
        _slug(primary_party),
    ))


def parse_new_jersey(
    extraction_path: Path,
    raw_root: Path,
) -> list[dict]:
    with extraction_path.open(newline="", encoding="utf-8") as handle:
        extracted = list(csv.DictReader(handle))
    required = {
        "source_pdf",
        "page",
        "total_page",
        "chamber",
        "district",
        "primary_party",
        "candidate_name",
        "candidate_source_id",
        "write_in",
        "votes",
    }
    if not extracted or not required <= set(extracted[0]):
        raise ValueError("New Jersey normalized extraction schema changed")
    rows = []
    seen = set()
    for line_number, row in enumerate(extracted, 2):
        source = NJ_PDF_SOURCES.get(row["source_pdf"])
        if source is None:
            raise ValueError(f"Unknown New Jersey result PDF: {row['source_pdf']}")
        key = (source["date"], row["candidate_source_id"])
        if key in seen:
            raise ValueError(f"Duplicate New Jersey candidate: {key}")
        seen.add(key)
        party = row["primary_party"]
        if party not in PARTIES:
            raise ValueError(f"Unknown New Jersey primary party: {party}")
        write_in = _boolean(row["write_in"])
        pdf_path = raw_root / "nj" / source["date"][:4] / row["source_pdf"]
        rows.append({
            "contest_id": _contest_id(
                "NJ",
                source["date"],
                row["chamber"],
                row["district"],
                source["term"],
                party,
            ),
            "cycle": source["date"][:4],
            "election_date": source["date"],
            "stage": source["stage"],
            "state_code": "NJ",
            "chamber": row["chamber"],
            "district": row["district"],
            "term": source["term"],
            "election_system": "partisan_primary",
            "primary_party": party,
            "candidate_name": row["candidate_name"].strip(),
            "candidate_source_id": row["candidate_source_id"],
            "party": "" if write_in else party,
            "write_in": write_in,
            "votes": _integer(row["votes"]),
            "source_id": source["source_id"],
            "source_url": (
                f"{NJ_RESULT_BASE}/{source['date'][:4]}/{row['source_pdf']}"
            ),
            "source_sha256": _sha256(pdf_path),
            "source_locators": (
                f"{row['source_pdf']}:page-{_integer(row['page'])}"
                f"-{_integer(row['total_page'])} | "
                f"{extraction_path.name}:line-{line_number}"
            ),
            "reporting_units": 1,
        })
    return rows


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row:
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def _florida_table_contest(title: str) -> tuple[str, str] | None:
    if title == "United States Senator":
        return "Senate", "S"
    match = re.fullmatch(r"District:\s*(\d+)", title)
    if match:
        return "House", match[1].zfill(2)
    return None


def parse_florida_summary(path: Path, source: dict) -> list[dict]:
    text = path.read_text(encoding="latin-1")
    if "Official Results" not in text or "August 18, 2026 Primary Election" not in text:
        raise ValueError("Florida official summary heading is missing")
    parser = _TableParser()
    parser.feed(text)
    rows = []
    source_hash = _sha256(path)
    contests = set()
    for table_index, table in enumerate(parser.tables):
        if not table or not table[0]:
            continue
        parsed = _florida_table_contest(table[0][0])
        if parsed is None:
            continue
        chamber, district = parsed
        header = next(
            (row for row in table[1:] if row and row[0] == "" and len(row) > 1),
            None,
        )
        total = next(
            (row for row in table[1:] if row and row[0] == "Total"),
            None,
        )
        if header is None or total is None or len(header) != len(total):
            raise ValueError(f"Florida federal table schema changed: {table[0][0]}")
        candidates = header[1:]
        votes = [_integer(value) for value in total[1:]]
        if not candidates:
            raise ValueError(f"Florida contest lacks candidates: {table[0][0]}")
        contests.add((chamber, district, source["party"]))
        for candidate_index, (candidate, vote_total) in enumerate(
            zip(candidates, votes, strict=True),
            1,
        ):
            write_in = "WRITE-IN" in candidate.upper() or candidate.upper() == "WRITE-IN"
            rows.append({
                "contest_id": _contest_id(
                    "FL",
                    source["date"],
                    chamber,
                    district,
                    "special" if chamber == "Senate" else "regular",
                    source["party"],
                ),
                "cycle": "2026",
                "election_date": source["date"],
                "stage": source["stage"],
                "state_code": "FL",
                "chamber": chamber,
                "district": district,
                "term": "special" if chamber == "Senate" else "regular",
                "election_system": "partisan_primary",
                "primary_party": source["party"],
                "candidate_name": candidate,
                "candidate_source_id": (
                    f"fl-2026-{chamber.casefold()}-{district.casefold()}-"
                    f"{source['party_code'].casefold()}-{candidate_index}"
                ),
                "party": "" if write_in else source["party"],
                "write_in": write_in,
                "votes": vote_total,
                "source_id": source["source_id"],
                "source_url": (
                    f"{FL_RESULTS_BASE}/SummaryRpt.asp?ElectionDate=8/18/2026"
                    f"&Race=FED&Party={source['party_code']}&DATAMODE="
                ),
                "source_sha256": source_hash,
                "source_locators": (
                    f"{path.name}:table-{table_index + 1}:"
                    f"candidate-{candidate_index}/total"
                ),
                "reporting_units": 1,
            })
    if not contests:
        raise ValueError(f'{source["source_id"]}: no Florida federal contests parsed')
    return rows


def _florida_candidate_name(row: dict) -> str:
    return " ".join(
        value.strip()
        for value in (row["NameFirst"], row["NameMiddle"], row["NameLast"])
        if value.strip()
    )


def parse_florida_roster(
    path: Path,
    actual_units: set[tuple[str, str, str]],
) -> tuple[list[dict], dict[tuple[str, str, str], str]]:
    candidates = defaultdict(list)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {
            "AcctNum",
            "OfficeCode",
            "Juris1num",
            "StatusCode",
            "StatusDesc",
            "PartyCode",
            "NameLast",
            "NameFirst",
            "NameMiddle",
        }
        if not required <= set(reader.fieldnames or []):
            raise ValueError("Florida candidate extract schema changed")
        for line_number, row in enumerate(reader, 2):
            if row["OfficeCode"] not in {"USS", "USR"}:
                continue
            party = FL_PARTY_CODES.get(row["PartyCode"])
            if party is None:
                continue
            chamber = "Senate" if row["OfficeCode"] == "USS" else "House"
            district = (
                "S" if chamber == "Senate"
                else f'{_integer(row["Juris1num"]):02}'
            )
            candidates[(chamber, district, party)].append({
                **row,
                "line": line_number,
            })
    source_hash = _sha256(path)
    source_url = f"{FL_CANDIDATE_BASE}/extractCanList.asp"
    roster = []
    missing_reasons = {}
    expected_units = {
        *{("Senate", "S", party) for party in PARTIES},
        *{
            ("House", f"{district:02}", party)
            for district in range(1, 29)
            for party in PARTIES
        },
    }
    for unit in sorted(expected_units):
        if unit in actual_units:
            continue
        rows = candidates.get(unit, [])
        unopposed = [
            row for row in rows
            if row["StatusCode"] in {"UNO", "QUA", "ELE"}
        ]
        defeated = [row for row in rows if row["StatusCode"] == "DEF"]
        if len(unopposed) == 1 and not defeated:
            row = unopposed[0]
            verification = (
                "official_database_unopposed_status"
                if row["StatusCode"] == "UNO"
                else "single_qualified_candidate_no_official_result"
            )
            roster.append({
                "state_code": "FL",
                "cycle": "2026",
                "election_date": "2026-08-18",
                "stage": "primary",
                "chamber": unit[0],
                "district": unit[1],
                "term": "special" if unit[0] == "Senate" else "regular",
                "primary_party": unit[2],
                "candidate_name": _florida_candidate_name(row),
                "candidate_source_id": row["AcctNum"],
                "source_id": "fl-2026-federal-candidate-extract",
                "source_url": source_url,
                "source_sha256": source_hash,
                "source_locators": f"{path.name}:line-{row['line']}",
                "verification_status": verification,
                "notes": (
                    f'{row["StatusCode"]}: {row["StatusDesc"]}. '
                    "No official vote-result table exists for this party unit; "
                    "the candidate database describes itself as an unofficial reference."
                ),
            })
            missing_reasons[unit] = "unopposed_roster_only"
        elif not unopposed and not defeated:
            missing_reasons[unit] = "no_qualified_party_candidate"
        else:
            missing_reasons[unit] = "candidate_status_requires_review"
    return roster, missing_reasons


def parse_new_jersey_roster(path: Path, raw_root: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "source_pdf",
        "page",
        "chamber",
        "district",
        "primary_party",
        "candidate_name",
        "candidate_source_id",
        "verification_status",
        "notes",
    }
    if not rows or not required <= set(rows[0]):
        raise ValueError("New Jersey unopposed roster schema changed")
    source_pdf = raw_root / "nj" / "2026" / rows[0]["source_pdf"]
    source_url = (
        f"{NJ_RESULT_BASE}/2026/{rows[0]['source_pdf']}"
    )
    return [
        {
            "state_code": "NJ",
            "cycle": "2026",
            "election_date": "2026-06-02",
            "stage": "primary",
            "chamber": row["chamber"],
            "district": row["district"],
            "term": "regular",
            "primary_party": row["primary_party"],
            "candidate_name": row["candidate_name"],
            "candidate_source_id": row["candidate_source_id"],
            "source_id": "nj-2026-official-primary-house-candidate-roster",
            "source_url": source_url,
            "source_sha256": _sha256(source_pdf),
            "source_locators": (
                f"{row['source_pdf']}:page-{_integer(row['page'])}"
            ),
            "verification_status": row["verification_status"],
            "notes": row["notes"],
        }
        for row in rows
    ]


def _result_unit(row: dict) -> tuple[str, str, str, str, str, str]:
    return (
        row["state_code"],
        row["election_date"],
        row["stage"],
        row["chamber"],
        row["district"],
        row["primary_party"],
    )


def _coverage_rows(
    results: list[dict],
    rosters: list[dict],
    florida_missing: dict[tuple[str, str, str], str],
) -> list[dict]:
    result_groups = defaultdict(list)
    roster_groups = defaultdict(list)
    for row in results:
        result_groups[_result_unit(row)].append(row)
    for row in rosters:
        roster_groups[_result_unit(row)].append(row)
    expected = []
    for year, regular_date, special_date, special_district in (
        ("2024", "2024-06-04", "2024-07-16", "10"),
        ("2026", "2026-06-02", "2026-02-05", "11"),
    ):
        expected.extend(
            ("NJ", regular_date, "primary", "Senate", "S", party, "regular")
            for party in PARTIES
        )
        expected.extend(
            (
                "NJ", regular_date, "primary", "House",
                f"{district:02}", party, "regular",
            )
            for district in range(1, 13)
            for party in PARTIES
        )
        expected.extend(
            (
                "NJ", special_date, "special_primary", "House",
                special_district, party, "special",
            )
            for party in PARTIES
        )
    expected.extend(
        ("FL", "2026-08-18", "primary", "Senate", "S", party, "special")
        for party in PARTIES
    )
    expected.extend(
        (
            "FL", "2026-08-18", "primary", "House",
            f"{district:02}", party, "regular",
        )
        for district in range(1, 29)
        for party in PARTIES
    )
    output = []
    for state, date, stage, chamber, district, party, term in expected:
        key = (state, date, stage, chamber, district, party)
        result_rows = result_groups.get(key, [])
        roster_rows = roster_groups.get(key, [])
        if result_rows:
            status = "actual_results"
            reason = ""
        elif roster_rows:
            status = "unopposed_roster_only"
            reason = "official vote totals are not published for this unit"
        elif state == "FL":
            status = florida_missing.get(
                (chamber, district, party),
                "candidate_status_requires_review",
            )
            reason = status.replace("_", " ")
        else:
            status = "no_reported_candidate"
            reason = "official primary result and candidate PDFs report no candidate"
        output.append({
            "state_code": state,
            "cycle": date[:4],
            "election_date": date,
            "stage": stage,
            "chamber": chamber,
            "district": district,
            "term": term,
            "primary_party": party,
            "coverage_status": status,
            "result_rows": len(result_rows),
            "roster_rows": len(roster_rows),
            "missing_reason": reason,
            "source_ids": " | ".join(sorted({
                row["source_id"] for row in result_rows + roster_rows
            })),
        })
    return output


def _contest_rows(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["contest_id"]].append(row)
    output = []
    for contest_id, candidates in sorted(groups.items()):
        first = candidates[0]
        unit = (first["chamber"], first["district"], first["primary_party"])
        output.append({
            "contest_id": contest_id,
            "state_code": first["state_code"],
            "cycle": first["cycle"],
            "election_date": first["election_date"],
            "stage": first["stage"],
            "chamber": first["chamber"],
            "district": first["district"],
            "term": first["term"],
            "primary_party": first["primary_party"],
            "candidate_count": len(candidates),
            "unopposed": len(candidates) == 1,
            "actual_zero_rows": sum(candidate["votes"] == 0 for candidate in candidates),
            "recount_status": (
                "machine_recount_completed"
                if first["state_code"] == "FL" and unit in FL_RECOUNT_UNITS
                else ""
            ),
            "result_status": "actual_numeric",
            "certification_status": "official",
            "source_id": first["source_id"],
        })
    return output


def _gap_rows(coverage: list[dict]) -> list[dict]:
    output = []
    for row in coverage:
        if row["coverage_status"] == "actual_results":
            continue
        output.append({
            "gap_id": "-".join((
                row["state_code"].casefold(),
                row["election_date"],
                row["stage"],
                row["chamber"].casefold(),
                row["district"].casefold(),
                _slug(row["primary_party"]),
            )),
            "state_code": row["state_code"],
            "cycle": row["cycle"],
            "stage": row["stage"],
            "chamber": row["chamber"],
            "district": row["district"],
            "primary_party": row["primary_party"],
            "coverage_status": row["coverage_status"],
            "recovered_scope": (
                f'{row["roster_rows"]} roster row(s)' if row["roster_rows"] else ""
            ),
            "missing_scope": "numeric primary vote totals",
            "blocker": row["missing_reason"],
            "next_authoritative_step": (
                "none expected for an unopposed/no-candidate primary unit"
            ),
            "source_urls": (
                NJ_PUBLICATION.format(year=row["cycle"])
                if row["state_code"] == "NJ"
                else FL_PUBLICATION
            ),
        })
    return output


def _source_counts(rows: list[dict], source_id: str) -> tuple[int, int]:
    selected = [row for row in rows if row["source_id"] == source_id]
    return len(selected), len({row["contest_id"] for row in selected})


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


def _source_manifest(
    raw_root: Path,
    results: list[dict],
    rosters: list[dict],
) -> list[dict]:
    manifest = []
    for filename, source in NJ_PDF_SOURCES.items():
        year = source["date"][:4]
        path = raw_root / "nj" / year / filename
        candidate_rows, contests = _source_counts(results, source["source_id"])
        source_url = f"{NJ_RESULT_BASE}/{year}/{filename}"
        manifest.append(_manifest_row(
            raw_root,
            path,
            source_id=source["source_id"],
            state_code="NJ",
            election_date=source["date"],
            stage=source["stage"],
            artifact_kind="official_primary_results_pdf",
            authority="New Jersey Division of Elections",
            publication_url=NJ_PUBLICATION.format(year=year),
            source_url=source_url,
            source_date=source["source_date"],
            verification_status="verified_official",
            certification_status="official",
            provisional_status="final_official_totals",
            candidate_rows=candidate_rows,
            contests=contests,
            coverage="candidate totals contained in this official result PDF",
            source_locators="PDF page ranges recorded per output row",
            notes="The PDF's (w) marker means winner, not write-in.",
        ))
        text_path = path.with_suffix(".txt")
        manifest.append(_manifest_row(
            raw_root,
            text_path,
            source_id=f"{source['source_id']}-text",
            state_code="NJ",
            election_date=source["date"],
            stage=source["stage"],
            artifact_kind="derived_pdf_text",
            authority="Derived from New Jersey Division of Elections PDF",
            publication_url=NJ_PUBLICATION.format(year=year),
            source_url=source_url,
            source_date=source["source_date"],
            verification_status="derived_parser_audit",
            certification_status="inherits_pdf",
            provisional_status="inherits_pdf",
            candidate_rows=candidate_rows,
            contests=contests,
            coverage="all physical PDF pages",
            source_locators="form-feed PAGE markers preserve physical page numbers",
            notes="Extracted with pypdf 6.16.0; result rows hash the PDF.",
        ))
    for extraction in NJ_EXTRACTIONS:
        path = raw_root / extraction["filename"]
        year_rows = [
            row for row in results
            if row["state_code"] == "NJ" and row["cycle"] == extraction["date"]
        ]
        manifest.append(_manifest_row(
            raw_root,
            path,
            source_id=f"nj-{extraction['date']}-normalized-extraction",
            state_code="NJ",
            election_date="",
            stage="multiple",
            artifact_kind="derived_structured_extraction",
            authority="Derived from official New Jersey result PDFs",
            publication_url=NJ_PUBLICATION.format(year=extraction["date"]),
            source_url=NJ_PUBLICATION.format(year=extraction["date"]),
            source_date="2026-09-22",
            verification_status="verified_against_pdf_candidate_totals",
            certification_status="inherits_pdfs",
            provisional_status="inherits_pdfs",
            candidate_rows=len(year_rows),
            contests=len({row["contest_id"] for row in year_rows}),
            coverage="regular and special congressional primary PDF rows",
            source_locators="source_pdf, candidate page, and total page columns",
            notes="Generated with pdfplumber 0.11.8 and pypdf 6.16.0.",
        ))
    candidate_pdf = raw_root / "nj/2026/2026-official-primary-candidates-us-house.pdf"
    manifest.append(_manifest_row(
        raw_root,
        candidate_pdf,
        source_id="nj-2026-official-primary-house-candidate-roster",
        state_code="NJ",
        election_date="2026-06-02",
        stage="primary",
        artifact_kind="official_primary_candidate_pdf",
        authority="New Jersey Division of Elections",
        publication_url=NJ_PUBLICATION.format(year="2026"),
        source_url=f"{NJ_RESULT_BASE}/2026/{candidate_pdf.name}",
        source_date="2026-04-02",
        verification_status="verified_official_roster",
        certification_status="candidate_list_not_vote_result",
        provisional_status="roster_only",
        candidate_rows=sum(
            row["source_id"] == "nj-2026-official-primary-house-candidate-roster"
            for row in rosters
        ),
        contests=1,
        coverage="House district 12 Republican roster-only unit",
        source_locators="page 16",
        notes="Gregg Mele is listed, but no official primary vote total is published.",
    ))
    roster_path = raw_root / "nj/2026/nj-2026-unopposed-roster.csv"
    manifest.append(_manifest_row(
        raw_root,
        roster_path,
        source_id="nj-2026-unopposed-roster-extraction",
        state_code="NJ",
        election_date="2026-06-02",
        stage="primary",
        artifact_kind="derived_roster_extraction",
        authority="Derived from official New Jersey candidate PDF",
        publication_url=NJ_PUBLICATION.format(year="2026"),
        source_url=f"{NJ_RESULT_BASE}/2026/{candidate_pdf.name}",
        source_date="2026-09-22",
        verification_status="roster_only_no_votes",
        certification_status="inherits_candidate_pdf",
        provisional_status="not_a_result",
        candidate_rows=1,
        contests=1,
        coverage="House district 12 Republican missing result unit",
        source_locators="source_pdf and page columns",
        notes="Retained outside the actual-results table.",
    ))
    for source in FL_SUMMARY_SOURCES:
        path = raw_root / source["filename"]
        candidate_rows, contests = _source_counts(results, source["source_id"])
        source_url = (
            f"{FL_RESULTS_BASE}/SummaryRpt.asp?ElectionDate=8/18/2026"
            f"&Race=FED&Party={source['party_code']}&DATAMODE="
        )
        manifest.append(_manifest_row(
            raw_root,
            path,
            source_id=source["source_id"],
            state_code="FL",
            election_date=source["date"],
            stage=source["stage"],
            artifact_kind="official_statewide_summary_html",
            authority="Florida Department of State, Division of Elections",
            publication_url=FL_PUBLICATION,
            source_url=source_url,
            source_date="2026-09-22",
            verification_status="verified_official",
            certification_status="official",
            provisional_status="final_official_totals",
            candidate_rows=candidate_rows,
            contests=contests,
            coverage="all contested federal offices in this party primary",
            source_locators="HTML table and candidate column locators",
            notes=(
                "The U.S. Senate contest fills the 2025 vacancy and is marked "
                "term=special even though its primary used the regular August 18 date."
            ),
        ))
    for filename, artifact, notes in (
        (
            "fl/2026/fl-2026-election-races.html",
            "official_election_inventory_html",
            "Frameset navigation proves FED summaries exist for both parties.",
        ),
        (
            "fl/2026/fl-2026-title-page.html",
            "official_election_title_html",
            "Confirms August 18, 2026 Primary Election.",
        ),
        (
            "fl/2026/fl-2026-federal-candidate-extract.tsv",
            "official_candidate_database_extract",
            (
                "The database labels itself an unofficial reference. Used only "
                "for separate unopposed/no-candidate coverage, never as vote results."
            ),
        ),
    ):
        path = raw_root / filename
        roster_rows = (
            sum(row["state_code"] == "FL" for row in rosters)
            if filename.endswith(".tsv") else 0
        )
        manifest.append(_manifest_row(
            raw_root,
            path,
            source_id=_slug(Path(filename).stem),
            state_code="FL",
            election_date="2026-08-18",
            stage="primary",
            artifact_kind=artifact,
            authority="Florida Department of State, Division of Elections",
            publication_url=FL_PUBLICATION,
            source_url=(
                f"{FL_CANDIDATE_BASE}/extractCanList.asp"
                if filename.endswith(".tsv")
                else f"{FL_RESULTS_BASE}/"
            ),
            source_date="2026-09-22",
            verification_status=(
                "official_database_unofficial_reference"
                if filename.endswith(".tsv") else "verified_official"
            ),
            certification_status="supporting_artifact",
            provisional_status="not_vote_results",
            candidate_rows=roster_rows,
            contests=roster_rows,
            coverage="calendar, inventory, or roster support",
            source_locators="document fields and source lines",
            notes=notes,
        ))
    return manifest


def _attempt_rows() -> list[dict]:
    date = "2026-09-22"
    return [
        {
            "attempt_id": "nj-01-2024-election-page",
            "attempted_on": date,
            "state_code": "NJ",
            "cycle": "2024",
            "source_url": NJ_PUBLICATION.format(year="2024"),
            "method": "follow official Senate, House, and special-primary result links",
            "outcome": "success_official_pdf_inventory",
            "raw_evidence": "nj/2024/2024-official-primary-results-us-house.pdf",
            "notes": "Regular and CD10 special primary sources identified.",
        },
        {
            "attempt_id": "nj-02-2024-results-pdfs",
            "attempted_on": date,
            "state_code": "NJ",
            "cycle": "2024",
            "source_url": f"{NJ_RESULT_BASE}/2024/",
            "method": "download and extract three official result PDFs",
            "outcome": "success_complete_regular_and_special",
            "raw_evidence": "nj/2024/nj-2024-congressional-primary-extraction.csv",
            "notes": "All 12 districts, both parties, Senate, and CD10 special.",
        },
        {
            "attempt_id": "nj-03-2026-election-page",
            "attempted_on": date,
            "state_code": "NJ",
            "cycle": "2026",
            "source_url": NJ_PUBLICATION.format(year="2026"),
            "method": "follow official Senate, House, and special-primary result links",
            "outcome": "success_official_pdf_inventory",
            "raw_evidence": "nj/2026/2026-official-primary-results-us-house.pdf",
            "notes": "Regular and CD11 special primary sources identified.",
        },
        {
            "attempt_id": "nj-04-2026-results-pdfs",
            "attempted_on": date,
            "state_code": "NJ",
            "cycle": "2026",
            "source_url": f"{NJ_RESULT_BASE}/2026/",
            "method": "download and extract three official result PDFs",
            "outcome": "success_partial_regular_complete_special",
            "raw_evidence": "nj/2026/nj-2026-congressional-primary-extraction.csv",
            "notes": "Two regular House party units lack numeric result rows.",
        },
        {
            "attempt_id": "nj-05-2026-candidate-pdf",
            "attempted_on": date,
            "state_code": "NJ",
            "cycle": "2026",
            "source_url": (
                f"{NJ_RESULT_BASE}/2026/"
                "2026-official-primary-candidates-us-house.pdf"
            ),
            "method": "check official primary candidates for missing result units",
            "outcome": "success_one_roster_one_no_candidate",
            "raw_evidence": "nj/2026/nj-2026-unopposed-roster.csv",
            "notes": "District 12 Republican roster-only; District 8 Republican absent.",
        },
        {
            "attempt_id": "fl-01-legacy-index",
            "attempted_on": date,
            "state_code": "FL",
            "cycle": "2026",
            "source_url": (
                f"{FL_RESULTS_BASE}/Index.asp?"
                "ElectionDate=8/18/2026&DATAMODE="
            ),
            "method": "inspect frameset instead of treating frame shell as empty",
            "outcome": "success_frames_discovered",
            "raw_evidence": "fl/2026/fl-2026-title-page.html",
            "notes": "ElectionRaces.asp and SummaryRpt.asp are the data-bearing frames.",
        },
        {
            "attempt_id": "fl-02-election-races",
            "attempted_on": date,
            "state_code": "FL",
            "cycle": "2026",
            "source_url": (
                f"{FL_RESULTS_BASE}/ElectionRaces.asp?"
                "ElectionDate=8/18/2026&DATAMODE="
            ),
            "method": "inspect official party and federal-office selectors",
            "outcome": "success_federal_routes",
            "raw_evidence": "fl/2026/fl-2026-election-races.html",
            "notes": "Both Democratic and Republican FED summaries are published.",
        },
        {
            "attempt_id": "fl-03-republican-summary",
            "attempted_on": date,
            "state_code": "FL",
            "cycle": "2026",
            "source_url": (
                f"{FL_RESULTS_BASE}/SummaryRpt.asp?"
                "ElectionDate=8/18/2026&Race=FED&Party=REP&DATAMODE="
            ),
            "method": "download official Republican federal summary",
            "outcome": "success_official_results",
            "raw_evidence": "fl/2026/fl-2026-federal-REP.html",
            "notes": "Includes special U.S. Senate and 15 contested House units.",
        },
        {
            "attempt_id": "fl-04-democratic-summary",
            "attempted_on": date,
            "state_code": "FL",
            "cycle": "2026",
            "source_url": (
                f"{FL_RESULTS_BASE}/SummaryRpt.asp?"
                "ElectionDate=8/18/2026&Race=FED&Party=DEM&DATAMODE="
            ),
            "method": "download official Democratic federal summary",
            "outcome": "success_official_results",
            "raw_evidence": "fl/2026/fl-2026-federal-DEM.html",
            "notes": "Includes special U.S. Senate and 20 contested House units.",
        },
        {
            "attempt_id": "fl-05-download-results",
            "attempted_on": date,
            "state_code": "FL",
            "cycle": "2026",
            "source_url": (
                f"{FL_RESULTS_BASE}/downloadresults.asp?"
                "ElectionDate=8/18/2026&DATAMODE="
            ),
            "method": "inspect official download page",
            "outcome": "no_2026_statewide_precinct_download",
            "raw_evidence": "",
            "notes": "Summary pages remain the available statewide first-party source.",
        },
        {
            "attempt_id": "fl-06-precinct-index",
            "attempted_on": date,
            "state_code": "FL",
            "cycle": "2026",
            "source_url": (
                "https://dos.fl.gov/elections/data-statistics/elections-data/"
                "precinct-level-election-results"
            ),
            "method": "inspect official precinct-result ZIP inventory",
            "outcome": "no_2026_statewide_zip",
            "raw_evidence": "",
            "notes": "The fetched inventory stops at 2026 state-legislative specials.",
        },
        {
            "attempt_id": "fl-07-candidate-extract",
            "attempted_on": date,
            "state_code": "FL",
            "cycle": "2026",
            "source_url": f"{FL_CANDIDATE_BASE}/extractCanList.asp",
            "method": "POST official federal candidate-list extract",
            "outcome": "success_unopposed_gap_classification",
            "raw_evidence": "fl/2026/fl-2026-federal-candidate-extract.tsv",
            "notes": "Kept separate because the database calls itself unofficial reference.",
        },
    ]


def _validate_output(rows: list[dict]) -> None:
    if not rows:
        raise ValueError("No New Jersey/Florida results generated")
    seen = set()
    for row in rows:
        if set(row) != set(FIELDS):
            raise ValueError(f"Output schema differs: {row.get('candidate_name')}")
        key = (row["contest_id"], row["candidate_source_id"])
        if key in seen:
            raise ValueError(f"Duplicate candidate result: {key}")
        seen.add(key)
        if not isinstance(row["votes"], int) or row["votes"] < 0:
            raise ValueError(f"Invalid vote total: {row}")
        if len(row["source_sha256"]) != 64 or not row["source_locators"]:
            raise ValueError(f"Incomplete provenance: {row}")
    florida_units = {
        (row["chamber"], row["district"], row["primary_party"])
        for row in rows if row["state_code"] == "FL"
    }
    if florida_units != FL_EXPECTED_RESULT_UNITS:
        raise ValueError(
            f"Florida official result coverage differs: "
            f"{florida_units ^ FL_EXPECTED_RESULT_UNITS}"
        )


def generate(
    raw_root: Path | None = None,
    analysis_root: Path | None = None,
) -> list[dict]:
    raw_root = raw_root or RAW_DIR / RAW_SUBDIR
    analysis_root = analysis_root or ANALYSIS_DATA_DIR / "congressional"
    results = []
    for extraction in NJ_EXTRACTIONS:
        results.extend(parse_new_jersey(raw_root / extraction["filename"], raw_root))
    for source in FL_SUMMARY_SOURCES:
        results.extend(parse_florida_summary(raw_root / source["filename"], source))
    results.sort(key=lambda row: (
        row["state_code"],
        row["election_date"],
        row["stage"],
        row["chamber"],
        row["district"],
        row["primary_party"],
        row["candidate_name"],
    ))
    _validate_output(results)
    actual_fl_units = {
        (row["chamber"], row["district"], row["primary_party"])
        for row in results if row["state_code"] == "FL"
    }
    florida_roster, florida_missing = parse_florida_roster(
        raw_root / "fl/2026/fl-2026-federal-candidate-extract.tsv",
        actual_fl_units,
    )
    new_jersey_roster = parse_new_jersey_roster(
        raw_root / "nj/2026/nj-2026-unopposed-roster.csv",
        raw_root,
    )
    rosters = sorted(
        new_jersey_roster + florida_roster,
        key=lambda row: (
            row["state_code"],
            row["district"],
            row["primary_party"],
            row["candidate_name"],
        ),
    )
    coverage = _coverage_rows(results, rosters, florida_missing)
    write_csv(analysis_root / RESULT_FILENAME, results, FIELDS)
    manifest_dir = analysis_root / MANIFEST_SUBDIR
    write_csv(
        manifest_dir / "source_manifest.csv",
        _source_manifest(raw_root, results, rosters),
        SOURCE_MANIFEST_FIELDS,
    )
    write_csv(manifest_dir / "attempt_ledger.csv", _attempt_rows(), ATTEMPT_FIELDS)
    write_csv(manifest_dir / "unresolved_gaps.csv", _gap_rows(coverage), GAP_FIELDS)
    write_csv(
        manifest_dir / "contest_manifest.csv",
        _contest_rows(results),
        CONTEST_FIELDS,
    )
    write_csv(
        manifest_dir / "unopposed_roster.csv",
        rosters,
        ROSTER_FIELDS,
    )
    write_csv(
        manifest_dir / "coverage_units.csv",
        coverage,
        COVERAGE_FIELDS,
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate official New Jersey/Florida congressional primary results"
    )
    parser.parse_args()
    rows = generate()
    print(
        f"Wrote {len(rows)} candidate results to "
        f"{ANALYSIS_DATA_DIR / 'congressional' / RESULT_FILENAME}"
    )


if __name__ == "__main__":
    main()
