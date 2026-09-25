"""Resolve official no-primary, no-candidate, and unopposed nomination units."""

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode

from .paths import ANALYSIS_DATA_DIR, RAW_DIR, ROOT

DATA_CUTOFF = "2026-09-22"
RAW_SUBDIR = "nomination_followup"
ANALYSIS_SUBDIR = "congressional/nomination_followup"

ACCOUNTING_FIELDS = [
    "cycle",
    "election_date",
    "state_code",
    "chamber",
    "district",
    "term",
    "stage",
    "primary_party",
    "status",
    "candidate_names",
    "source_urls",
    "locators",
    "notes",
]

ATTEMPT_FIELDS = [
    "state_code",
    "cycle",
    "attempted_on",
    "source_url",
    "method",
    "outcome",
    "raw_evidence",
    "notes",
]

MANIFEST_FIELDS = [
    "source_id",
    "state_code",
    "cycle",
    "authority",
    "source_url",
    "path",
    "sha256",
    "bytes",
    "artifact_type",
    "locators",
    "coverage",
]

RAW_ARTIFACT_FIELDS = ["provider", "path", "sha256", "bytes", "artifact_type"]

COVERAGE_FIELDS = [
    "state_code",
    "cycle",
    "target_units",
    "resolved_units",
    "unresolved_units",
    "status_counts",
    "notes",
]

AR_NOTICE_URL = (
    "https://votepulaskiar.gov/wp-content/uploads/"
    "03052024_Notice-of-Election_AMENDED-1.pdf"
)
AR_CALENDAR_URL = (
    "https://www.sos.arkansas.gov/uploads/elections/"
    "2026_Election_Calendar_Rev._6-2025_.pdf"
)
AR_LAW_URL = (
    "https://www.sos.arkansas.gov/uploads/elections/"
    "Arkansas_Election_Laws_and_Constitution_2025_Edition.pdf"
)
AR_CANDIDATE_PUBLICATION_URL = "https://candidates.arkansas.gov/"
AR_WASHINGTON_RESULT_URL = (
    "https://www.washingtoncountyar.gov/home/showpublisheddocument/"
    "30266/638464358286800000"
)
KY_2024_CANDIDATE_URL = (
    "https://web.sos.ky.gov/CandidateFilings/default.aspx?elecid=82&id=4"
)
KY_2026_CANDIDATE_URL = (
    "https://web.sos.ky.gov/CandidateFilings/default.aspx?elecid=86&id=4"
)
KY_KRS_118_185_URL = (
    "https://apps.legislature.ky.gov/law/statutes/statute.aspx?id=27594"
)
KY_KRS_118_212_URL = (
    "https://apps.legislature.ky.gov/law/statutes/statute.aspx?id=57013"
)
SD_2024_CANDIDATE_URL = (
    "https://sdsos.gov/elections-voting/election-resources/election-history/"
    "2024/2024PrimaryCandidateList.csv"
)
SD_2024_HISTORY_URL = (
    "https://sdsos.gov/elections-voting/election-resources/election-history/"
    "2024_Election_History.aspx"
)
SD_2026_CANDIDATE_URL = "https://vip.sdsos.gov/candidatelist.aspx?eid=773"
SD_2026_INFO_URL = (
    "https://sdsos.gov/elections-voting/upcoming-elections/"
    "general-information/2026%20Election%20Information/default.aspx"
)
SD_LAW_URL = "https://sdlegislature.gov/api/Statutes/Statute/12-6-9"


def _arkansas_candidate_api_url() -> str:
    params = [("rand", "1732"), ("draw", "3")]
    columns = [
        "FilerID",
        "CanBallotName",
        "Descript",
        "PartyAffiliation",
        "FilingDate",
    ]
    for index, column in enumerate(columns):
        params.extend(
            [
                (f"columns[{index}][data]", column),
                (f"columns[{index}][name]", ""),
                (f"columns[{index}][searchable]", "true"),
                (f"columns[{index}][orderable]", "false" if index == 0 else "true"),
                (f"columns[{index}][search][value]", ""),
                (f"columns[{index}][search][regex]", "false"),
            ]
        )
    params.extend(
        [
            ("order[0][column]", "1"),
            ("order[0][dir]", "asc"),
            ("start", "0"),
            ("length", "1000"),
            ("search[value]", ""),
            ("search[regex]", "false"),
            ("postID", "2941"),
            ("CanBallotName", ""),
            ("Descript", ""),
        ]
    )
    return (
        "https://candidates.arkansas.gov/wp-json/metl/v1/all?"
        + urlencode(params)
    )


AR_CANDIDATE_API_URL = _arkansas_candidate_api_url()

TargetKey = tuple[str, str, str, str, str]

TARGET_KEYS: set[TargetKey] = {
    ("2024", "AR", "House", "01", "Democratic"),
    ("2024", "AR", "House", "01", "Republican"),
    ("2024", "AR", "House", "02", "Democratic"),
    ("2024", "AR", "House", "02", "Republican"),
    ("2024", "AR", "House", "03", "Democratic"),
    ("2024", "AR", "House", "04", "Democratic"),
    ("2024", "AR", "House", "04", "Republican"),
    ("2026", "AR", "House", "01", "Democratic"),
    ("2026", "AR", "House", "01", "Republican"),
    ("2026", "AR", "House", "03", "Democratic"),
    ("2026", "AR", "House", "03", "Republican"),
    ("2026", "AR", "House", "04", "Republican"),
    ("2024", "KY", "House", "01", "Democratic"),
    ("2024", "KY", "House", "01", "Republican"),
    ("2024", "KY", "House", "02", "Republican"),
    ("2024", "KY", "House", "04", "Democratic"),
    ("2024", "KY", "House", "05", "Democratic"),
    ("2024", "KY", "House", "06", "Republican"),
    ("2026", "KY", "House", "01", "Democratic"),
    ("2026", "KY", "House", "03", "Democratic"),
    ("2026", "KY", "House", "05", "Democratic"),
    ("2024", "SD", "House", "00", "Democratic"),
    ("2024", "SD", "House", "00", "Republican"),
    ("2026", "SD", "House", "00", "Democratic"),
    ("2026", "SD", "Senate", "S", "Democratic"),
}

ARTIFACTS = [
    {
        "source_id": "ar-2024-pulaski-primary-notice",
        "state_code": "AR",
        "cycle": "2024",
        "authority": "Pulaski County Election Commission",
        "source_url": AR_NOTICE_URL,
        "path": "ar/2024/pulaski-2024-primary-amended-notice.pdf",
        "artifact_type": "official_pdf",
        "locators": (
            "PDF page 3 (printed Page 4 of 5), Republican Unopposed Candidates "
            "and Democratic Unopposed Candidates"
        ),
        "coverage": "AR 2024 House districts 01, 02, and 04 Democratic/Republican",
    },
    {
        "source_id": "ar-2024-pulaski-primary-notice-text",
        "state_code": "AR",
        "cycle": "2024",
        "authority": "Pulaski County Election Commission",
        "source_url": AR_NOTICE_URL,
        "path": "ar/2024/pulaski-2024-primary-amended-notice.txt",
        "artifact_type": "extracted_text",
        "locators": "lines 569-582",
        "coverage": "Parser input for the six explicitly labeled unopposed units",
    },
    {
        "source_id": "ar-election-law-2025",
        "state_code": "AR",
        "cycle": "2024;2026",
        "authority": "Arkansas Secretary of State",
        "source_url": AR_LAW_URL,
        "path": "ar/arkansas-election-laws-2025.pdf",
        "artifact_type": "official_pdf",
        "locators": "PDF page 252, Ark. Code section 7-7-102(a)",
        "coverage": "Certification of party nominees as unopposed candidates",
    },
    {
        "source_id": "ar-code-7-7-102-extract",
        "state_code": "AR",
        "cycle": "2024;2026",
        "authority": "Arkansas Secretary of State",
        "source_url": AR_LAW_URL,
        "path": "ar/arkansas-code-7-7-102-extract.txt",
        "artifact_type": "extracted_text",
        "locators": "PDF page 252, Ark. Code section 7-7-102(a)",
        "coverage": "Parser assertion for automatic unopposed certification",
    },
    {
        "source_id": "ar-2026-candidate-roster",
        "state_code": "AR",
        "cycle": "2026",
        "authority": "Arkansas Secretary of State",
        "source_url": AR_CANDIDATE_API_URL,
        "path": "ar/2026/ar-2026-candidate-roster.json",
        "artifact_type": "official_json",
        "locators": (
            "recordsTotal=199; data rows for U.S. Congress District 01, 03, "
            "and 04"
        ),
        "coverage": "Exhaustive 2026 filing roster",
    },
    {
        "source_id": "ar-2026-election-calendar",
        "state_code": "AR",
        "cycle": "2026",
        "authority": "Arkansas Secretary of State",
        "source_url": AR_CALENDAR_URL,
        "path": "ar/2026/ar-2026-election-calendar.pdf",
        "artifact_type": "official_pdf",
        "locators": (
            "PDF printed page 13, March 3 primary; printed page 17, "
            "March 18 unopposed certification deadline"
        ),
        "coverage": "Election date and explicit unopposed certification procedure",
    },
    {
        "source_id": "ar-2026-election-calendar-text",
        "state_code": "AR",
        "cycle": "2026",
        "authority": "Arkansas Secretary of State",
        "source_url": AR_CALENDAR_URL,
        "path": "ar/2026/ar-2026-election-calendar.txt",
        "artifact_type": "extracted_text",
        "locators": "lines 611-614 and 824-829",
        "coverage": "Parser assertions for date and certification procedure",
    },
    {
        "source_id": "ky-2024-house-candidate-filings",
        "state_code": "KY",
        "cycle": "2024",
        "authority": "Kentucky Secretary of State",
        "source_url": KY_2024_CANDIDATE_URL,
        "path": "ky/2024/ky-2024-us-house-candidate-filings.html",
        "artifact_type": "official_html",
        "locators": "Candidates for US Representative; active table, 23 filings",
        "coverage": "Exhaustive 2024 U.S. House filing roster",
    },
    {
        "source_id": "ky-2026-house-candidate-filings",
        "state_code": "KY",
        "cycle": "2026",
        "authority": "Kentucky Secretary of State",
        "source_url": KY_2026_CANDIDATE_URL,
        "path": "ky/2026/ky-2026-us-house-candidate-filings.html",
        "artifact_type": "official_html",
        "locators": (
            "Candidates for US Representative; active table, 48 filings; "
            "Withdrawn / Deceased / Disqualified section"
        ),
        "coverage": "Exhaustive 2026 U.S. House filing roster and withdrawals",
    },
    {
        "source_id": "ky-krs-118-185",
        "state_code": "KY",
        "cycle": "2024;2026",
        "authority": "Kentucky Legislative Research Commission",
        "source_url": KY_KRS_118_185_URL,
        "path": "ky/krs-118-185.pdf",
        "artifact_type": "official_pdf",
        "locators": "KRS 118.185, Certification of unopposed candidate",
        "coverage": "Automatic certificate of nomination for a sole filer",
    },
    {
        "source_id": "ky-krs-118-185-text",
        "state_code": "KY",
        "cycle": "2024;2026",
        "authority": "Kentucky Legislative Research Commission",
        "source_url": KY_KRS_118_185_URL,
        "path": "ky/krs-118-185.txt",
        "artifact_type": "extracted_text",
        "locators": "lines 1-8",
        "coverage": "Parser assertion for a sole filer's certificate of nomination",
    },
    {
        "source_id": "ky-krs-118-212",
        "state_code": "KY",
        "cycle": "2026",
        "authority": "Kentucky Legislative Research Commission",
        "source_url": KY_KRS_118_212_URL,
        "path": "ky/krs-118-212.pdf",
        "artifact_type": "official_pdf",
        "locators": "KRS 118.212(4), effective April 14, 2026",
        "coverage": "Certificate of nomination for sole remaining primary candidate",
    },
    {
        "source_id": "ky-krs-118-212-text",
        "state_code": "KY",
        "cycle": "2026",
        "authority": "Kentucky Legislative Research Commission",
        "source_url": KY_KRS_118_212_URL,
        "path": "ky/krs-118-212.txt",
        "artifact_type": "extracted_text",
        "locators": "lines 24-36 and 49-56",
        "coverage": "Parser assertion for nomination after withdrawal",
    },
    {
        "source_id": "sd-2024-primary-candidates",
        "state_code": "SD",
        "cycle": "2024",
        "authority": "South Dakota Secretary of State",
        "source_url": SD_2024_CANDIDATE_URL,
        "path": "sd/2024/sd-2024-primary-candidates.csv",
        "artifact_type": "official_csv",
        "locators": "rows 8-9, United States Representative",
        "coverage": "Exhaustive 2024 primary candidate list",
    },
    {
        "source_id": "sd-2024-election-history",
        "state_code": "SD",
        "cycle": "2024",
        "authority": "South Dakota Secretary of State",
        "source_url": SD_2024_HISTORY_URL,
        "path": "sd/2024/sd-2024-election-history.html",
        "artifact_type": "official_html",
        "locators": "2024 Primary Election - June 4, 2024",
        "coverage": "Official primary date and candidate-list publication context",
    },
    {
        "source_id": "sd-2026-primary-candidates",
        "state_code": "SD",
        "cycle": "2026",
        "authority": "South Dakota Secretary of State",
        "source_url": SD_2026_CANDIDATE_URL,
        "path": "sd/2026/sd-2026-primary-candidates.html",
        "artifact_type": "official_html",
        "locators": (
            "page note: unopposed candidates are not on the primary ballot; "
            "United States Senator and United States Representative rows"
        ),
        "coverage": "Exhaustive 2026 primary candidate list",
    },
    {
        "source_id": "sd-2026-election-information",
        "state_code": "SD",
        "cycle": "2026",
        "authority": "South Dakota Secretary of State",
        "source_url": SD_2026_INFO_URL,
        "path": "sd/2026/sd-2026-election-information.html",
        "artifact_type": "official_html",
        "locators": "Primary Election Date: June 2, 2026",
        "coverage": "Official primary date",
    },
    {
        "source_id": "sdcl-12-6-9",
        "state_code": "SD",
        "cycle": "2024;2026",
        "authority": "South Dakota Legislative Research Council",
        "source_url": SD_LAW_URL,
        "path": "sd/sdcl-12-6-9.json",
        "artifact_type": "official_json",
        "locators": (
            "SDCL 12-6-9, Unopposed candidate automatically nominated--"
            "Primary not held if no contest"
        ),
        "coverage": "Automatic nomination rule for unopposed party candidates",
    },
]


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def _html_rows(text: str) -> list[list[str]]:
    parser = _TableParser()
    parser.feed(text)
    return parser.rows


def parse_arkansas_2024_notice(path: Path) -> dict[tuple[str, str], str]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    parsed: dict[tuple[str, str], str] = {}
    party = ""
    for index, line in enumerate(lines):
        if line == "Republican Unopposed Candidates:":
            party = "Republican"
        elif line == "Democratic Unopposed Candidates:":
            party = "Democratic"
        elif party and (match := re.fullmatch(r"U\.S\. Congress District (\d)", line)):
            following = next(
                candidate
                for candidate in lines[index + 1 :]
                if candidate
            )
            parsed[(f"{int(match.group(1)):02}", party)] = following
    return parsed


def parse_arkansas_2026_roster(path: Path) -> dict[tuple[str, str], list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["recordsTotal"] != len(payload["data"]):
        raise ValueError("Arkansas roster response is not exhaustive")
    parsed: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in payload["data"]:
        match = re.fullmatch(r"U\.S\. Congress District (\d{2})", row["Descript"])
        if match:
            parsed[(match.group(1), row["PartyAffiliation"])].append(
                row["CanBallotName"]
            )
    return dict(parsed)


def parse_kentucky_house_filings(path: Path) -> dict[str, list[dict[str, str]]]:
    text = path.read_text(encoding="utf-8")
    marker = 'id="ctl00_MainContent_pnlOfficeWddResults"'
    active_text, separator, withdrawn_text = text.partition(marker)
    groups = {"active": active_text, "withdrawn": withdrawn_text if separator else ""}
    parsed: dict[str, list[dict[str, str]]] = {"active": [], "withdrawn": []}
    for status, group in groups.items():
        for cells in _html_rows(group):
            if len(cells) < 6 or cells[2] != "US Representative":
                continue
            district_match = re.fullmatch(r"(\d+)(?:st|nd|rd|th)", cells[3])
            if not district_match:
                continue
            parsed[status].append(
                {
                    "name": cells[0],
                    "district": f"{int(district_match.group(1)):02}",
                    "party": cells[4].removesuffix(" Party"),
                    "filed": cells[5],
                }
            )
    return parsed


def parse_south_dakota_2024(path: Path) -> dict[tuple[str, str], list[str]]:
    parsed: dict[tuple[str, str], list[str]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row["Contest"] != "United States Representative":
                continue
            party = {"DEM": "Democratic", "REP": "Republican"}.get(row["Party"])
            if party:
                parsed[("00", party)].append(row["Name"])
    return dict(parsed)


def parse_south_dakota_2026(path: Path) -> dict[tuple[str, str], list[str]]:
    text = path.read_text(encoding="utf-8")
    if "If a candidate is unopposed, that candidate will not be on the Primary" not in text:
        raise ValueError("South Dakota unopposed-candidate notice is missing")
    parsed: dict[tuple[str, str], list[str]] = defaultdict(list)
    for cells in _html_rows(text):
        if len(cells) < 16 or cells[13] != "Active" or cells[14] != "Primary":
            continue
        party = {"DEM": "Democratic", "REP": "Republican"}.get(cells[2])
        if not party:
            continue
        if cells[0] == "United States Senator":
            parsed[("S", party)].append(cells[1])
        elif cells[0] == "United States Representative":
            parsed[("00", party)].append(cells[1])
    return dict(parsed)


def _key(row: dict[str, str]) -> TargetKey:
    return (
        row["cycle"],
        row["state_code"],
        row["chamber"],
        row["district"],
        row["primary_party"],
    )


def _ordinal(district: str) -> str:
    number = int(district)
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _read_accounting(path: Path) -> dict[TargetKey, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = {_key(row): row for row in csv.DictReader(handle) if _key(row) in TARGET_KEYS}
    missing = TARGET_KEYS - rows.keys()
    if missing:
        raise ValueError(f"Missing target accounting units: {sorted(missing)}")
    return rows


def _resolved_row(
    base: dict[str, str],
    *,
    election_date: str,
    status: str,
    candidate_names: list[str],
    source_urls: list[str],
    locators: list[str],
    notes: str,
) -> dict[str, str]:
    row = {field: base.get(field, "") for field in ACCOUNTING_FIELDS}
    row.update(
        {
            "election_date": election_date,
            "status": status,
            "candidate_names": "; ".join(candidate_names),
            "source_urls": "; ".join(source_urls),
            "locators": "; ".join(locators),
            "notes": notes,
        }
    )
    return row


def build_accounting_updates(
    raw_root: Path,
    accounting_path: Path,
) -> list[dict[str, str]]:
    base = _read_accounting(accounting_path)
    raw = raw_root / RAW_SUBDIR
    ar_2024 = parse_arkansas_2024_notice(
        raw / "ar/2024/pulaski-2024-primary-amended-notice.txt"
    )
    ar_2026 = parse_arkansas_2026_roster(
        raw / "ar/2026/ar-2026-candidate-roster.json"
    )
    ky_2024 = parse_kentucky_house_filings(
        raw / "ky/2024/ky-2024-us-house-candidate-filings.html"
    )
    ky_2026 = parse_kentucky_house_filings(
        raw / "ky/2026/ky-2026-us-house-candidate-filings.html"
    )
    sd_2024 = parse_south_dakota_2024(
        raw / "sd/2024/sd-2024-primary-candidates.csv"
    )
    sd_2026 = parse_south_dakota_2026(
        raw / "sd/2026/sd-2026-primary-candidates.html"
    )

    ar_law = (raw / "ar/arkansas-code-7-7-102-extract.txt").read_text(
        encoding="utf-8"
    )
    if "as an unopposed candidate" not in ar_law:
        raise ValueError("Arkansas unopposed-candidate certification law is missing")
    ar_calendar = (raw / "ar/2026/ar-2026-election-calendar.txt").read_text(
        encoding="utf-8"
    )
    if "March 3, 2026" not in ar_calendar or "unopposed candidates" not in ar_calendar:
        raise ValueError("Arkansas 2026 calendar evidence is incomplete")
    ky_185 = (raw / "ky/krs-118-185.txt").read_text(encoding="utf-8")
    if "certificate of nomination" not in ky_185:
        raise ValueError("KRS 118.185 evidence is incomplete")
    ky_212 = (raw / "ky/krs-118-212.txt").read_text(encoding="utf-8")
    if "only one (1) remaining candidate" not in ky_212:
        raise ValueError("KRS 118.212 withdrawal evidence is incomplete")
    sd_law = json.loads(
        (raw / "sd/sdcl-12-6-9.json").read_text(encoding="utf-8")
    )
    if (
        sd_law.get("Statute") != "12-6-9"
        or "Unopposed candidate automatically nominated"
        not in sd_law.get("CatchLine", "")
        or "shall automatically become the nominee"
        not in sd_law.get("Html", "")
    ):
        raise ValueError("South Dakota automatic-nomination law is missing")

    updates: list[dict[str, str]] = []
    for district in ("01", "02", "04"):
        for party in ("Democratic", "Republican"):
            key = ("2024", "AR", "House", district, party)
            if key not in TARGET_KEYS:
                continue
            candidate = ar_2024[(district, party)]
            updates.append(
                _resolved_row(
                    base[key],
                    election_date="2024-03-05",
                    status="unopposed_nomination_verified",
                    candidate_names=[candidate],
                    source_urls=[AR_NOTICE_URL, AR_LAW_URL],
                    locators=[
                        (
                            "Pulaski amended notice PDF page 3 (printed Page 4 of 5), "
                            f"{party} Unopposed Candidates, U.S. Congress District "
                            f"{int(district)}"
                        ),
                        (
                            "Arkansas Election Laws 2025 PDF page 252, "
                            "Ark. Code section 7-7-102(a); history shows no amendment "
                            "after 2011"
                        ),
                    ],
                    notes=(
                        "The official primary notice explicitly labels this candidate "
                        "unopposed, and Ark. Code section 7-7-102(a) provides certification "
                        "as an unopposed party nominee."
                    ),
                )
            )

    unresolved_key = ("2024", "AR", "House", "03", "Democratic")
    updates.append(
        _resolved_row(
            base[unresolved_key],
            election_date="2024-03-05",
            status="unresolved",
            candidate_names=[],
            source_urls=[AR_WASHINGTON_RESULT_URL],
            locators=[
                "2024 Primary Certification Report, DEM U.S. CONGRESS DISTRICT 03"
            ],
            notes=(
                "Not an automatic-nomination unit: the indexed official Washington "
                "County certification reports a one-candidate Democratic numeric primary. "
                "Direct capture returned HTTP 403 and numeric-result integration was "
                "explicitly outside this follow-up scope, so this remains unresolved."
            ),
        )
    )

    ar_2026_targets = [
        ("01", "Democratic"),
        ("01", "Republican"),
        ("03", "Democratic"),
        ("03", "Republican"),
        ("04", "Republican"),
    ]
    for district, party in ar_2026_targets:
        candidates = ar_2026[(district, party)]
        if len(candidates) != 1:
            raise ValueError(f"Expected one AR 2026 candidate for {district} {party}")
        key = ("2026", "AR", "House", district, party)
        updates.append(
            _resolved_row(
                base[key],
                election_date="2026-03-03",
                status="unopposed_nomination_verified",
                candidate_names=candidates,
                source_urls=[AR_CANDIDATE_API_URL, AR_CALENDAR_URL, AR_LAW_URL],
                locators=[
                    (
                        "candidate API data row where Descript='U.S. Congress District "
                        f"{district}' and PartyAffiliation='{party}'"
                    ),
                    (
                        "2026 Election Calendar printed page 13, March 3 primary, and "
                        "printed page 17, March 18 deadline to declare and certify "
                        "unopposed candidates"
                    ),
                    "Arkansas Election Laws 2025 PDF page 252, Ark. Code section 7-7-102(a)",
                ],
                notes=(
                    "The exhaustive official filing API has exactly one candidate in "
                    "this party unit; the official calendar and statute require separate "
                    "declaration and certification of unopposed candidates."
                ),
            )
        )

    def kentucky_active(
        filings: dict[str, list[dict[str, str]]],
        district: str,
        party: str,
    ) -> list[str]:
        return [
            row["name"]
            for row in filings["active"]
            if row["district"] == district and row["party"] == party
        ]

    ky_2024_targets = [
        ("01", "Democratic"),
        ("01", "Republican"),
        ("02", "Republican"),
        ("04", "Democratic"),
        ("05", "Democratic"),
        ("06", "Republican"),
    ]
    for district, party in ky_2024_targets:
        candidates = kentucky_active(ky_2024, district, party)
        key = ("2024", "KY", "House", district, party)
        if len(candidates) == 1:
            status = "unopposed_nomination_verified"
            urls = [KY_2024_CANDIDATE_URL, KY_KRS_118_185_URL]
            locators = [
                (
                    "Candidates for US Representative active table, "
                    f"{_ordinal(district)} district {party} row"
                ),
                "KRS 118.185, Certification of unopposed candidate",
            ]
            notes = (
                "The exhaustive official filing table has one active party filer, "
                "and KRS 118.185 requires an immediate certificate of nomination."
            )
        elif not candidates:
            status = "no_candidate_verified"
            urls = [KY_2024_CANDIDATE_URL]
            locators = [
                (
                    "Candidates for US Representative active table (23 filings); "
                    f"no {party} row for the {_ordinal(district)} district"
                )
            ]
            notes = (
                "The exhaustive official U.S. House filing table contains no active "
                "candidate in this district-party unit."
            )
        else:
            raise ValueError(f"Unexpected KY 2024 filings for {district} {party}")
        updates.append(
            _resolved_row(
                base[key],
                election_date="2024-05-21",
                status=status,
                candidate_names=candidates,
                source_urls=urls,
                locators=locators,
                notes=notes,
            )
        )

    ky_2026_targets = [
        ("01", "Democratic"),
        ("03", "Democratic"),
        ("05", "Democratic"),
    ]
    for district, party in ky_2026_targets:
        candidates = kentucky_active(ky_2026, district, party)
        if len(candidates) != 1:
            raise ValueError(f"Expected one KY 2026 active candidate for {district} {party}")
        key = ("2026", "KY", "House", district, party)
        urls = [KY_2026_CANDIDATE_URL, KY_KRS_118_185_URL]
        locators = [
            (
                "Candidates for US Representative active table, "
                f"{_ordinal(district)} district {party} row"
            ),
            "KRS 118.185, Certification of unopposed candidate",
        ]
        notes = (
            "The exhaustive official filing table has one active party filer, "
            "and KRS 118.185 requires an immediate certificate of nomination."
        )
        if district == "03":
            withdrawn = [
                row["name"]
                for row in ky_2026["withdrawn"]
                if row["district"] == district and row["party"] == party
            ]
            if withdrawn != ["Jared Randall"]:
                raise ValueError("Expected Jared Randall in the withdrawn section")
            urls.append(KY_KRS_118_212_URL)
            locators.extend(
                [
                    (
                        "Withdrawn / Deceased / Disqualified section, Jared Randall, "
                        "3rd district Democratic"
                    ),
                    "KRS 118.212(4), sole remaining primary candidate",
                ]
            )
            notes = (
                "Morgan McGarvey is the sole active Democratic filer; Jared Randall "
                "is listed in the official withdrawn section. KRS 118.212(4) requires "
                "a certificate of nomination for the sole remaining primary candidate."
            )
        updates.append(
            _resolved_row(
                base[key],
                election_date="2026-05-19",
                status="unopposed_nomination_verified",
                candidate_names=candidates,
                source_urls=urls,
                locators=locators,
                notes=notes,
            )
        )

    sd_targets = [
        ("2024", "2024-06-04", "House", "00", "Democratic", sd_2024),
        ("2024", "2024-06-04", "House", "00", "Republican", sd_2024),
        ("2026", "2026-06-02", "House", "00", "Democratic", sd_2026),
        ("2026", "2026-06-02", "Senate", "S", "Democratic", sd_2026),
    ]
    for cycle, election_date, chamber, district, party, filings in sd_targets:
        candidates = filings[(district, party)]
        if len(candidates) != 1:
            raise ValueError(
                f"Expected one SD {cycle} candidate for {chamber} {district} {party}"
            )
        key = (cycle, "SD", chamber, district, party)
        candidate_url = SD_2024_CANDIDATE_URL if cycle == "2024" else SD_2026_CANDIDATE_URL
        date_url = SD_2024_HISTORY_URL if cycle == "2024" else SD_2026_INFO_URL
        locator = (
            "United States Representative rows 8-9"
            if cycle == "2024"
            else (
                "page note that unopposed candidates are omitted from the primary "
                f"ballot; {chamber} {party} candidate row"
            )
        )
        notes = (
            "The exhaustive official candidate list has exactly one party candidate, "
            "and SDCL 12-6-9 makes an unopposed candidate the automatic party nominee."
        )
        if cycle == "2026" and chamber == "Senate":
            notes += (
                " A later general-cycle withdrawal does not alter the verified June "
                "primary nomination status."
            )
        updates.append(
            _resolved_row(
                base[key],
                election_date=election_date,
                status="unopposed_nomination_verified",
                candidate_names=candidates,
                source_urls=[candidate_url, date_url, SD_LAW_URL],
                locators=[
                    locator,
                    f"official election information, primary date {election_date}",
                    (
                        "SDCL 12-6-9, Unopposed candidate automatically nominated--"
                        "Primary not held if no contest"
                    ),
                ],
                notes=notes,
            )
        )

    if {_key(row) for row in updates} != TARGET_KEYS:
        raise ValueError("Generated accounting updates do not match the 25 target units")
    for row in updates:
        if row["status"] != "unresolved" and (
            not row["source_urls"] or not row["locators"]
        ):
            raise ValueError(f"Resolved row lacks provenance: {_key(row)}")
    return sorted(
        updates,
        key=lambda row: (
            row["cycle"],
            row["state_code"],
            row["chamber"],
            row["district"],
            row["primary_party"],
        ),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _artifact_rows(raw_root: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    manifest: list[dict[str, object]] = []
    raw_artifacts: list[dict[str, object]] = []
    for artifact in ARTIFACTS:
        path = raw_root / RAW_SUBDIR / artifact["path"]
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(path)
        relative = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        digest = _sha256(path)
        manifest.append(
            {
                **artifact,
                "path": str(relative),
                "sha256": digest,
                "bytes": path.stat().st_size,
            }
        )
        raw_artifacts.append(
            {
                "provider": "nomination_followup",
                "path": str(relative),
                "sha256": digest,
                "bytes": path.stat().st_size,
                "artifact_type": artifact["artifact_type"],
            }
        )
    return manifest, raw_artifacts


def _attempt_rows() -> list[dict[str, str]]:
    return [
        {
            "state_code": "AR",
            "cycle": "2024",
            "attempted_on": DATA_CUTOFF,
            "source_url": AR_NOTICE_URL,
            "method": "official county amended primary notice PDF",
            "outcome": "resolved_6_of_7",
            "raw_evidence": (
                "data/raw/nomination_followup/ar/2024/"
                "pulaski-2024-primary-amended-notice.pdf"
            ),
            "notes": (
                "The notice explicitly labels House 01, 02, and 04 Democratic and "
                "Republican candidates unopposed."
            ),
        },
        {
            "state_code": "AR",
            "cycle": "2024",
            "attempted_on": DATA_CUTOFF,
            "source_url": AR_WASHINGTON_RESULT_URL,
            "method": "official county primary certification PDF",
            "outcome": "blocked_http_403_unit_remains_unresolved",
            "raw_evidence": "",
            "notes": (
                "The indexed official certification identifies House 03 Democratic "
                "as a one-candidate numeric primary, not an automatic nomination. "
                "The direct source returned HTTP 403 and was excluded from raw artifacts."
            ),
        },
        {
            "state_code": "AR",
            "cycle": "2026",
            "attempted_on": DATA_CUTOFF,
            "source_url": AR_CANDIDATE_API_URL,
            "method": "official public DataTables JSON API plus election calendar",
            "outcome": "resolved_5_of_5",
            "raw_evidence": (
                "data/raw/nomination_followup/ar/2026/ar-2026-candidate-roster.json"
            ),
            "notes": "The exhaustive response contains 199 filings and one filer per target unit.",
        },
        {
            "state_code": "KY",
            "cycle": "2024",
            "attempted_on": DATA_CUTOFF,
            "source_url": KY_2024_CANDIDATE_URL,
            "method": "official Secretary of State candidate filing table plus KRS 118.185",
            "outcome": "resolved_6_of_6",
            "raw_evidence": (
                "data/raw/nomination_followup/ky/2024/"
                "ky-2024-us-house-candidate-filings.html"
            ),
            "notes": "Four sole filers and two explicit roster absences were verified.",
        },
        {
            "state_code": "KY",
            "cycle": "2026",
            "attempted_on": DATA_CUTOFF,
            "source_url": KY_2026_CANDIDATE_URL,
            "method": (
                "official Secretary of State active/withdrawn filing tables plus "
                "KRS 118.185 and 118.212"
            ),
            "outcome": "resolved_3_of_3",
            "raw_evidence": (
                "data/raw/nomination_followup/ky/2026/"
                "ky-2026-us-house-candidate-filings.html"
            ),
            "notes": "The House 03 resolution preserves Jared Randall's withdrawn status.",
        },
        {
            "state_code": "SD",
            "cycle": "2024",
            "attempted_on": DATA_CUTOFF,
            "source_url": SD_2024_CANDIDATE_URL,
            "method": "official exhaustive primary candidate CSV plus SDCL 12-6-9",
            "outcome": "resolved_2_of_2",
            "raw_evidence": (
                "data/raw/nomination_followup/sd/2024/"
                "sd-2024-primary-candidates.csv"
            ),
            "notes": "One Democratic and one Republican at-large House filer were verified.",
        },
        {
            "state_code": "SD",
            "cycle": "2026",
            "attempted_on": DATA_CUTOFF,
            "source_url": SD_2026_CANDIDATE_URL,
            "method": "official exhaustive primary candidate page plus SDCL 12-6-9",
            "outcome": "resolved_2_of_2",
            "raw_evidence": (
                "data/raw/nomination_followup/sd/2026/"
                "sd-2026-primary-candidates.html"
            ),
            "notes": (
                "The page states unopposed candidates are omitted from the primary "
                "ballot; later general-cycle withdrawal is retained only as a note."
            ),
        },
    ]


def _coverage_rows(updates: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in updates:
        grouped[(row["state_code"], row["cycle"])].append(row)
    rows: list[dict[str, object]] = []
    for (state_code, cycle), units in sorted(grouped.items()):
        counts = Counter(row["status"] for row in units)
        unresolved = counts.get("unresolved", 0)
        notes = ""
        if state_code == "AR" and cycle == "2024":
            notes = (
                "House 03 Democratic remains unresolved because official evidence "
                "indicates a numeric primary requiring the separate results pipeline."
            )
        rows.append(
            {
                "state_code": state_code,
                "cycle": cycle,
                "target_units": len(units),
                "resolved_units": len(units) - unresolved,
                "unresolved_units": unresolved,
                "status_counts": "; ".join(
                    f"{status}={count}" for status, count in sorted(counts.items())
                ),
                "notes": notes,
            }
        )
    return rows


def generate(
    raw_root: Path = RAW_DIR,
    analysis_root: Path = ANALYSIS_DATA_DIR,
    accounting_path: Path | None = None,
) -> list[dict[str, str]]:
    accounting_path = accounting_path or (
        analysis_root / "congressional/party_contest_accounting.csv"
    )
    updates = build_accounting_updates(raw_root, accounting_path)
    output = analysis_root / ANALYSIS_SUBDIR
    manifest, raw_artifacts = _artifact_rows(raw_root)
    _write_csv(
        output / "party_contest_accounting_updates.csv",
        ACCOUNTING_FIELDS,
        updates,
    )
    _write_csv(output / "source_attempts.csv", ATTEMPT_FIELDS, _attempt_rows())
    _write_csv(output / "source_manifest.csv", MANIFEST_FIELDS, manifest)
    _write_csv(
        output / "raw_artifacts.csv",
        RAW_ARTIFACT_FIELDS,
        raw_artifacts,
    )
    _write_csv(
        output / "coverage_summary.csv",
        COVERAGE_FIELDS,
        _coverage_rows(updates),
    )
    return updates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, default=RAW_DIR)
    parser.add_argument("--analysis-root", type=Path, default=ANALYSIS_DATA_DIR)
    parser.add_argument("--accounting", type=Path)
    args = parser.parse_args()
    generate(args.raw_root, args.analysis_root, args.accounting)


if __name__ == "__main__":
    main()
