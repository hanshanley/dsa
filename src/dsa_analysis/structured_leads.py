import hashlib
import re

from .io import read_csv, write_csv
from .paths import PROCESSED_DIR

NAME = r"[A-Z][A-Za-zÀ-ÖØ-öø-ÿ.'’\-]+(?:\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ.'’\-]+){1,5}"
DIRECT_PATTERN = re.compile(
    rf"\b(?i:endorse(?:s|d)?)\s+"
    rf"(?:the\s+campaign\s+of\s+)?"
    rf"(?P<name>{NAME})"
    rf"(?:'s|’s)?(?:\s+campaign)?\s+for\s+"
    rf"(?P<office>.+?)"
    rf"(?=(?:,\s+(?:advancing|who|while|but)\b)|(?:\s+and\s+{NAME}\s+for\s+)|[.;]|$)",
)
PAIR_PATTERN = re.compile(
    rf"(?P<name>{NAME})\s+for\s+"
    rf"(?P<office>.+?)"
    rf"(?=(?:\s+and\s+{NAME}\s+for\s+)|[.;]|$)"
)
INVALID_NAMES = {
    "Current Endorsements",
    "Past Endorsements",
    "Democratic Socialists",
    "Electoral Endorsements",
    "General Election",
    "Primary Election",
}


def extract_structured_leads() -> int:
    mentions = read_csv(PROCESSED_DIR / "local_endorsement_mentions.csv")
    output = {}
    for mention in mentions:
        text = mention["mention_text"]
        matches = list(DIRECT_PATTERN.finditer(text))
        if not matches and re.search(r"endorsed\s+(?:two|three|four|five|\d+)\s+candidates", text, re.I):
            matches = list(PAIR_PATTERN.finditer(text))
        for match in matches:
            name = _clean(match.group("name"))
            office = _clean(match.group("office"))
            if not _valid(name, office):
                continue
            lead_id = hashlib.sha256(
                f'{mention["chapter"]}\n{name}\n{office}\n{mention["page_url"]}'.encode()
            ).hexdigest()[:24]
            output[lead_id] = {
                "lead_id": lead_id,
                "chapter": mention["chapter"],
                "state": mention["state"],
                "inferred_years": mention["inferred_years"],
                "candidate_name": name,
                "office_text": office,
                "source_url": mention["page_url"],
                "source_title": mention["page_title"],
                "mention_id": mention["mention_id"],
                "verification_status": "found_unverified",
                "mention_text": text,
            }
    rows = sorted(
        output.values(),
        key=lambda row: (
            row["state"],
            row["chapter"],
            row["inferred_years"],
            row["candidate_name"],
        ),
    )
    write_csv(
        PROCESSED_DIR / "local_endorsement_leads.csv",
        rows,
        [
            "lead_id",
            "chapter",
            "state",
            "inferred_years",
            "candidate_name",
            "office_text",
            "source_url",
            "source_title",
            "mention_id",
            "verification_status",
            "mention_text",
        ],
    )
    return len(rows)


def parse_leads(text: str) -> list[tuple[str, str]]:
    matches = list(DIRECT_PATTERN.finditer(text))
    if not matches and re.search(r"endorsed\s+(?:two|three|four|five|\d+)\s+candidates", text, re.I):
        matches = list(PAIR_PATTERN.finditer(text))
    return [
        (_clean(match.group("name")), _clean(match.group("office")))
        for match in matches
        if _valid(_clean(match.group("name")), _clean(match.group("office")))
    ]


def _clean(value: str) -> str:
    cleaned = " ".join(value.strip(" ,:-–—").split())
    return re.sub(r"(?:'s|’s)$", "", cleaned)


def _valid(name: str, office: str) -> bool:
    if name in INVALID_NAMES:
        return False
    if len(name) < 5 or len(name) > 80 or len(office) < 3 or len(office) > 180:
        return False
    lowered_office = office.lower()
    return any(
        term in lowered_office
        for term in (
            "council",
            "assembly",
            "house",
            "senate",
            "mayor",
            "governor",
            "board",
            "congress",
            "district",
            "attorney",
            "judge",
            "supervisor",
            "commission",
            "representative",
            "school",
            "clerk",
            "sheriff",
            "comptroller",
        )
    )
