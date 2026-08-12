import hashlib
import re

from .io import read_csv, write_csv
from .paths import PROCESSED_DIR

ENDORSEMENT_PATTERN = re.compile(r"\b(?:endorse(?:d|ment|ments|s|ing)?|re-endorse\w*)\b", re.I)
YEAR_PATTERN = re.compile(r"\b(201[6-9]|202[0-6])\b")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|(?=\b(?:20\d{2}|Current|Past) Endorsements\b)")
LOW_VALUE_PATTERNS = (
    "endorsement process",
    "endorsement questionnaire",
    "seeking endorsement",
    "apply for endorsement",
    "endorsement criteria",
    "endorsement policy",
    "cannot endorse",
    "not endorse",
    "no endorsement",
)


def extract_mentions() -> tuple[int, int]:
    pages = read_csv(PROCESSED_DIR / "local_endorsement_pages.csv")
    archive_path = PROCESSED_DIR / "archived_endorsement_pages.csv"
    if archive_path.exists():
        pages.extend(read_csv(archive_path))
    mentions = []
    pages_with_mentions: set[str] = set()
    for page in pages:
        text = page["text_excerpt"]
        page_year = page["published_date"][:4] or page.get("capture_year", "")
        for sentence in SENTENCE_SPLIT.split(text):
            sentence = " ".join(sentence.split()).strip()
            if not ENDORSEMENT_PATTERN.search(sentence):
                continue
            lowered = sentence.lower()
            if any(pattern in lowered for pattern in LOW_VALUE_PATTERNS):
                continue
            if len(sentence) < 25 or len(sentence) > 1200:
                continue
            years = sorted(set(YEAR_PATTERN.findall(sentence)))
            mention_id = hashlib.sha256(
                f'{page["page_id"]}\n{sentence}'.encode()
            ).hexdigest()[:24]
            mentions.append(
                {
                    "mention_id": mention_id,
                    "page_id": page["page_id"],
                    "chapter": page["chapter"],
                    "state": page["state"],
                    "page_url": page["page_url"],
                    "page_title": page["title"],
                    "page_published_date": page["published_date"],
                    "inferred_years": " | ".join(years or ([page_year] if page_year else [])),
                    "review_status": "not_searched",
                    "mention_text": sentence,
                }
            )
            pages_with_mentions.add(page["page_id"])
    mentions.sort(
        key=lambda row: (
            row["state"],
            row["chapter"],
            row["page_published_date"],
            row["mention_id"],
        )
    )
    write_csv(
        PROCESSED_DIR / "local_endorsement_mentions.csv",
        mentions,
        [
            "mention_id",
            "page_id",
            "chapter",
            "state",
            "page_url",
            "page_title",
            "page_published_date",
            "inferred_years",
            "review_status",
            "mention_text",
        ],
    )
    return len(mentions), len(pages_with_mentions)
