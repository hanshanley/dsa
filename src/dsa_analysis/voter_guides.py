import hashlib
import re
import urllib.parse
import urllib.request

from .chapter_crawler import parse_html
from .io import write_csv
from .paths import PROCESSED_DIR

USER_AGENT = "dsa-analysis/0.1 (+official DSA voter guide research)"
NYC_HOME = "https://ballot.socialists.nyc/"
LA_GUIDE = "https://dsavoterguide.com/la/simple-guide.html"
PERSON_TOKEN = (
    r"[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+"
    r"(?:[-'’][A-Za-zÀ-ÖØ-öø-ÿ]+)*"
)
PERSON_PATTERN = rf"{PERSON_TOKEN}(?:\s+{PERSON_TOKEN}){{1,5}}"


def collect_voter_guides() -> tuple[int, int]:
    nyc_rows = _collect_nyc()
    la_rows = _collect_la()
    rows = nyc_rows + la_rows
    write_csv(
        PROCESSED_DIR / "structured_voter_guide_candidates.csv",
        rows,
        [
            "guide_record_id",
            "chapter",
            "state",
            "election_year",
            "election_stage",
            "candidate_name",
            "role",
            "office_text",
            "district",
            "campaign_url",
            "priorities",
            "source_url",
            "evidence_status",
            "notes",
        ],
    )
    return len(nyc_rows), len(la_rows)


def _collect_nyc() -> list[dict[str, str]]:
    homepage = _fetch(NYC_HOME)
    script_paths = re.findall(r'src="([^"]+LookupPage[^"]+\.js)"', homepage)
    if not script_paths:
        raise ValueError("NYC voter guide application script was not found")
    app_script_url = urllib.parse.urljoin(NYC_HOME, script_paths[0])
    app_script = _fetch(app_script_url)
    module_match = re.search(r'\./(candidates\.[A-Za-z0-9_-]+\.js)', app_script)
    if not module_match:
        raise ValueError("NYC voter guide candidate module was not found")
    module_url = urllib.parse.urljoin(app_script_url, module_match.group(1))
    source = _fetch(module_url)
    pattern = re.compile(
        r'\{name:"(?P<name>[^"]+)",office:"(?P<office>[^"]+)",'
        r'district:"(?P<district>[^"]+)".*?endorsed:!0.*?'
        r'website:(?:"(?P<website>[^"]*)"|null).*?'
        r'priorities:\[(?P<priorities>.*?)\],endorsers:',
        re.DOTALL,
    )
    rows = []
    for match in pattern.finditer(source):
        name = match.group("name")
        rows.append(
            _row(
                chapter="New York City",
                state="NY",
                year="2026",
                stage="primary",
                name=name,
                role="endorsed",
                office=match.group("office"),
                district=match.group("district"),
                campaign_url=match.group("website") or "",
                priorities=" | ".join(
                    re.findall(r'"([^"]+)"', match.group("priorities"))
                ),
                source_url=module_url,
                notes="Official NYC-DSA ballot application candidate module",
            )
        )
    return rows


def _collect_la() -> list[dict[str, str]]:
    html = _fetch(LA_GUIDE)
    text = " ".join(parse_html(html).text)
    sections = re.split(r"(?=TL;DR:)", text)
    rows = []
    for section in sections:
        if not section.startswith("TL;DR:"):
            continue
        endorsed_match = re.search(
            rf"(?P<name>{PERSON_PATTERN})\s+Endorsed DSA\b",
            section,
        )
        if not endorsed_match:
            continue
        endorsed_name = endorsed_match.group("name")
        district = _district_near(section, endorsed_match.end())
        summary = section[: section.find(".") + 1] if "." in section else section[:300]
        rows.append(
            _row(
                chapter="Los Angeles",
                state="CA",
                year="2026",
                stage="top_two",
                name=endorsed_name,
                role="endorsed",
                office=_office_hint(section, district),
                district=district,
                campaign_url="",
                priorities="",
                source_url=LA_GUIDE,
                notes=summary,
            )
        )
        for opponent_match in re.finditer(
            rf"(?P<name>{PERSON_PATTERN})\s+Opposed\b",
            section,
        ):
            opponent_name = opponent_match.group("name")
            rows.append(
                _row(
                    chapter="Los Angeles",
                    state="CA",
                    year="2026",
                    stage="top_two",
                    name=opponent_name,
                    role="opponent",
                    office=_office_hint(section, district),
                    district=_district_near(section, opponent_match.end()) or district,
                    campaign_url="",
                    priorities="",
                    source_url=LA_GUIDE,
                    notes=f"Opponent listed in official DSA-LA guide section for {endorsed_name}",
                )
            )
    return rows


def _row(
    *,
    chapter: str,
    state: str,
    year: str,
    stage: str,
    name: str,
    role: str,
    office: str,
    district: str,
    campaign_url: str,
    priorities: str,
    source_url: str,
    notes: str,
) -> dict[str, str]:
    record_id = hashlib.sha256(
        f"{chapter}\n{year}\n{name}\n{role}\n{office}\n{district}".encode()
    ).hexdigest()[:24]
    return {
        "guide_record_id": record_id,
        "chapter": chapter,
        "state": state,
        "election_year": year,
        "election_stage": stage,
        "candidate_name": name,
        "role": role,
        "office_text": office,
        "district": district,
        "campaign_url": campaign_url,
        "priorities": priorities,
        "source_url": source_url,
        "evidence_status": "verified",
        "notes": notes,
    }


def _district_near(section: str, start: int) -> str:
    match = re.search(
        r"\b(?:District|AD|SD|NY|CD)\s*-?\s*\d+[A-Za-z]?\b",
        section[start : start + 150],
        re.IGNORECASE,
    )
    return match.group(0) if match else ""


def _office_hint(section: str, district: str) -> str:
    for office in (
        "City Attorney",
        "LAUSD School Board",
        "School Board",
        "Board of Supervisors",
        "State Assembly",
        "State Senate",
        "U.S. Congress",
        "City Council",
        "Mayor",
    ):
        if office.lower() in section.lower():
            normalized = "School Board" if office == "LAUSD School Board" else office
            return f"{normalized} {district}".strip()
    return district


def _fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", "replace")
