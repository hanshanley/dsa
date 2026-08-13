import csv
import hashlib
import json
from pathlib import Path

from .io import read_csv, write_csv
from .paths import PROCESSED_DIR

SESSION_BATCH_DIR = Path(
    "/Users/hanshanley/.copilot/session-state/"
    "0ed4a415-a2be-4bcc-9083-2ca717c4ece8/files/endorsement_batches"
)
REVIEW_FIELDS = [
    "mention_id",
    "decision",
    "candidate_name",
    "office_text",
    "election_year",
    "election_stage",
    "chapter",
    "state",
    "source_url",
    "confidence",
    "notes",
]
REQUIRED_REVIEW_FIELDS = set(REVIEW_FIELDS)


def merge_reviews(batch_dir: Path = SESSION_BATCH_DIR) -> tuple[int, int, int]:
    input_ids = _input_ids(batch_dir)
    rows = []
    reviewed_ids: set[str] = set()
    for path in sorted(batch_dir.glob("review_*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = REQUIRED_REVIEW_FIELDS - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
            for row in reader:
                mention_id = row["mention_id"].strip()
                if mention_id not in input_ids:
                    raise ValueError(f"{path.name}: unknown mention_id {mention_id}")
                if row["decision"] not in {"accept", "reject"}:
                    raise ValueError(f"{path.name}: invalid decision")
                if row["decision"] == "accept" and not row["candidate_name"].strip():
                    raise ValueError(f"{path.name}: accepted row lacks candidate")
                reviewed_ids.add(mention_id)
                rows.append(row)

    uncovered = input_ids - reviewed_ids
    if uncovered:
        raise ValueError(f"{len(uncovered)} input mentions were not adjudicated")

    write_csv(
        PROCESSED_DIR / "local_endorsement_adjudication.csv",
        rows,
        REVIEW_FIELDS,
    )
    accepted = _deduplicate_accepts(rows)
    accepted = _merge_structured_voter_guides(accepted)
    write_csv(
        PROCESSED_DIR / "local_endorsement_candidates.csv",
        accepted,
        [
            "endorsement_key",
            "chapter",
            "state",
            "candidate_name",
            "office_text",
            "election_year",
            "election_stage",
            "source_url",
            "confidence",
            "review_status",
            "mention_ids",
            "notes",
        ],
    )
    rejects = sum(row["decision"] == "reject" for row in rows)
    return len(input_ids), len(accepted), rejects


def build_opponent_queue() -> int:
    verified_path = PROCESSED_DIR / "local_endorsements_verified.csv"
    path = (
        verified_path
        if verified_path.exists()
        else PROCESSED_DIR / "local_endorsement_candidates.csv"
    )
    if not path.exists():
        raise FileNotFoundError("Run merge-endorsement-reviews first")
    with path.open(newline="", encoding="utf-8") as handle:
        candidates = list(csv.DictReader(handle))
    queue_path = PROCESSED_DIR / "opponent_research_queue.csv"
    existing_by_id = {
        row["queue_id"]: row
        for row in read_csv(queue_path)
    } if queue_path.exists() else {}
    rows_by_key = {}
    for candidate in candidates:
        queue_id = hashlib.sha256(
            (
                f'{candidate["chapter"]}\n{candidate["candidate_name"]}\n'
                f'{candidate["office_text"]}\n{candidate["election_year"]}'
            ).encode()
        ).hexdigest()[:24]
        new_row = _queue_row(
            queue_id=queue_id,
            chapter=candidate["chapter"],
            state=candidate["state"],
            candidate_name=candidate["candidate_name"],
            office_text=candidate["office_text"],
            election_year=candidate["election_year"],
            election_stage=candidate["election_stage"],
            endorsement_source_url=candidate["source_url"],
            notes="Local chapter endorsement",
        )
        rows_by_key[_queue_key(candidate)] = _preserve_queue_status(
            new_row,
            existing_by_id.get(queue_id),
        )

    national_path = PROCESSED_DIR / "national_endorsement_archive.csv"
    if national_path.exists():
        with national_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                office_types = set(row["office_types"].split(" | "))
                if office_types and office_types <= {"Ballot Initiative"}:
                    continue
                year = row["election_date"][:4]
                candidate = {
                    "candidate_name": row["campaign"],
                    "office_text": row["office"],
                    "election_year": year,
                    "state": "",
                }
                key = _queue_key(candidate)
                if key in rows_by_key:
                    rows_by_key[key]["chapter"] = (
                        rows_by_key[key]["chapter"] + " | DSA National"
                    )
                    continue
                new_row = _queue_row(
                    queue_id=f'national-{row["record_id"]}',
                    chapter="DSA National",
                    state="",
                    candidate_name=row["campaign"],
                    office_text=row["office"],
                    election_year=year,
                    election_stage="unknown",
                    endorsement_source_url=row["source_view_url"],
                    notes="Official DSA National endorsement archive",
                )
                rows_by_key[key] = _preserve_queue_status(
                    new_row,
                    existing_by_id.get(new_row["queue_id"]),
                )
    rows = sorted(
        rows_by_key.values(),
        key=lambda row: (
            row["election_year"],
            row["state"],
            row["candidate_name"],
            row["office_text"],
        ),
    )
    write_csv(
        queue_path,
        rows,
        [
            "queue_id",
            "chapter",
            "state",
            "candidate_name",
            "office_text",
            "election_year",
            "election_stage",
            "endorsement_source_url",
            "race_resolution_status",
            "official_election_source",
            "opponent_roster_status",
            "candidate_statement_status",
            "opponent_statement_status",
            "notes",
        ],
    )
    return len(rows)


def _preserve_queue_status(
    new_row: dict[str, str],
    existing: dict[str, str] | None,
) -> dict[str, str]:
    if not existing:
        return new_row
    for field in (
        "race_resolution_status",
        "official_election_source",
        "opponent_roster_status",
        "candidate_statement_status",
        "opponent_statement_status",
    ):
        new_row[field] = existing[field]
    if existing["notes"]:
        new_row["notes"] = " | ".join(
            dict.fromkeys((new_row["notes"], existing["notes"]))
        )
    return new_row


def _queue_key(candidate: dict[str, str]) -> tuple[str, ...]:
    return (
        candidate.get("candidate_name", "").strip().casefold(),
        candidate.get("office_text", "").strip().casefold(),
        candidate.get("election_year", "").strip(),
        candidate.get("state", "").strip().casefold(),
    )


def _queue_row(
    *,
    queue_id: str,
    chapter: str,
    state: str,
    candidate_name: str,
    office_text: str,
    election_year: str,
    election_stage: str,
    endorsement_source_url: str,
    notes: str,
) -> dict[str, str]:
    return {
        "queue_id": queue_id,
        "chapter": chapter,
        "state": state,
        "candidate_name": candidate_name,
        "office_text": office_text,
        "election_year": election_year,
        "election_stage": election_stage,
        "endorsement_source_url": endorsement_source_url,
        "race_resolution_status": "not_searched",
        "official_election_source": "",
        "opponent_roster_status": "not_searched",
        "candidate_statement_status": "not_searched",
        "opponent_statement_status": "not_searched",
        "notes": notes,
    }


def finalize_verification(
    batch_dir: Path = SESSION_BATCH_DIR,
) -> tuple[int, int, int]:
    candidates_path = PROCESSED_DIR / "local_endorsement_candidates.csv"
    if not candidates_path.exists():
        raise FileNotFoundError("Run merge-endorsement-reviews first")
    with candidates_path.open(newline="", encoding="utf-8") as handle:
        candidates = {
            row["endorsement_key"]: row
            for row in csv.DictReader(handle)
        }
    reviews = {}
    for path in sorted(batch_dir.glob("verify_review_*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            required = {
                "endorsement_key",
                "decision",
                "candidate_name",
                "office_text",
                "election_year",
                "election_stage",
                "confidence",
                "notes",
            }
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
            for row in reader:
                key = row["endorsement_key"]
                if key not in candidates:
                    raise ValueError(f"{path.name}: unknown endorsement_key {key}")
                if key in reviews:
                    raise ValueError(f"duplicate verification for {key}")
                if row["decision"] not in {"verified", "reject"}:
                    raise ValueError(f"{path.name}: invalid verification decision")
                reviews[key] = row
    uncovered = set(candidates) - set(reviews)
    if uncovered:
        raise ValueError(f"{len(uncovered)} candidate endorsements were not verified")

    verified = []
    rejected = []
    for key, candidate in candidates.items():
        review = reviews[key]
        if candidate["review_status"] == "verified":
            decision = "verified"
        else:
            decision = review["decision"]
        row = {
            **candidate,
            "candidate_name": review["candidate_name"].strip()
            or candidate["candidate_name"],
            "office_text": review["office_text"].strip()
            or candidate["office_text"],
            "election_year": review["election_year"].strip()
            or candidate["election_year"],
            "election_stage": review["election_stage"].strip()
            or candidate["election_stage"],
            "confidence": review["confidence"].strip()
            or candidate["confidence"],
            "review_status": decision,
            "notes": " | ".join(
                value
                for value in (candidate["notes"], review["notes"].strip())
                if value
            ),
        }
        (verified if decision == "verified" else rejected).append(row)

    fieldnames = [
        "endorsement_key",
        "chapter",
        "state",
        "candidate_name",
        "office_text",
        "election_year",
        "election_stage",
        "source_url",
        "confidence",
        "review_status",
        "mention_ids",
        "notes",
    ]
    write_csv(
        PROCESSED_DIR / "local_endorsements_verified.csv",
        verified,
        fieldnames,
    )
    write_csv(
        PROCESSED_DIR / "local_endorsements_rejected.csv",
        rejected,
        fieldnames,
    )
    return len(candidates), len(verified), len(rejected)


def import_chapter_history(
    path: Path,
    chapter: str,
    state: str,
    replace_chapter: bool = False,
) -> tuple[int, int]:
    required = {
        "election_year",
        "candidate_name",
        "office_text",
        "election_stage",
        "source_url",
        "archive_url",
        "verification_status",
        "notes",
    }
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"chapter history missing columns {sorted(missing)}")
        rows = list(reader)
    verified_path = PROCESSED_DIR / "local_endorsements_verified.csv"
    existing = []
    if verified_path.exists():
        with verified_path.open(newline="", encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))
    if replace_chapter:
        existing = [row for row in existing if row["chapter"] != chapter]
    combined = {
        (
            row["chapter"],
            row["candidate_name"],
            row["office_text"],
            row["election_year"],
        ): row
        for row in existing
    }
    gaps = []
    imported = 0
    for row in rows:
        if row["verification_status"] != "verified":
            gaps.append({"chapter": chapter, "state": state, **row})
            continue
        key = (
            chapter,
            row["candidate_name"].strip(),
            row["office_text"].strip(),
            row["election_year"].strip(),
        )
        source = " | ".join(
            value
            for value in (row["source_url"].strip(), row["archive_url"].strip())
            if value
        )
        combined[key] = {
            "endorsement_key": hashlib.sha256("\n".join(key).encode()).hexdigest()[:24],
            "chapter": chapter,
            "state": state,
            "candidate_name": key[1],
            "office_text": key[2],
            "election_year": key[3],
            "election_stage": row["election_stage"].strip() or "unknown",
            "source_url": source,
            "confidence": "high",
            "review_status": "verified",
            "mention_ids": "",
            "notes": row["notes"].strip(),
        }
        imported += 1
    fieldnames = [
        "endorsement_key",
        "chapter",
        "state",
        "candidate_name",
        "office_text",
        "election_year",
        "election_stage",
        "source_url",
        "confidence",
        "review_status",
        "mention_ids",
        "notes",
    ]
    write_csv(
        verified_path,
        sorted(
            combined.values(),
            key=lambda row: (
                row["election_year"],
                row["state"],
                row["chapter"],
                row["candidate_name"],
            ),
        ),
        fieldnames,
    )
    if gaps:
        gap_path = PROCESSED_DIR / "chapter_history_gaps.csv"
        prior = []
        if gap_path.exists():
            with gap_path.open(newline="", encoding="utf-8") as handle:
                prior = list(csv.DictReader(handle))
        if replace_chapter:
            prior = [row for row in prior if row["chapter"] != chapter]
        write_csv(
            gap_path,
            prior + gaps,
            [
                "chapter",
                "state",
                "election_year",
                "candidate_name",
                "office_text",
                "election_stage",
                "source_url",
                "archive_url",
                "verification_status",
                "notes",
            ],
        )
    return imported, len(gaps)


def enrich_verified_endorsement_years() -> tuple[int, int]:
    verified_path = PROCESSED_DIR / "local_endorsements_verified.csv"
    mentions_path = PROCESSED_DIR / "local_endorsement_mentions.csv"
    mentions = {
        row["mention_id"]: {
            year
            for year in row["inferred_years"].split(" | ")
            if year
        }
        for row in read_csv(mentions_path)
    }
    rows = read_csv(verified_path)
    enriched = 0
    unresolved = 0
    for row in rows:
        if len(row["election_year"]) == 4 and row["election_year"].isdigit():
            continue
        years = set()
        for mention_id in row["mention_ids"].split(" | "):
            years.update(mentions.get(mention_id, set()))
        if len(years) == 1:
            row["election_year"] = years.pop()
            enriched += 1
        else:
            unresolved += 1
    write_csv(
        verified_path,
        rows,
        [
            "endorsement_key",
            "chapter",
            "state",
            "candidate_name",
            "office_text",
            "election_year",
            "election_stage",
            "source_url",
            "confidence",
            "review_status",
            "mention_ids",
            "notes",
        ],
    )
    return enriched, unresolved


def _input_ids(batch_dir: Path) -> set[str]:
    input_ids = set()
    for path in sorted(batch_dir.glob("batch_*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                input_ids.add(json.loads(line)["mention_id"])
    if not input_ids:
        raise ValueError("No adjudication batch inputs were found")
    return input_ids


def _deduplicate_accepts(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = {}
    for row in rows:
        if row["decision"] != "accept":
            continue
        key = (
            row["chapter"].strip(),
            row["state"].strip(),
            row["candidate_name"].strip(),
            row["office_text"].strip(),
            row["election_year"].strip(),
        )
        grouped.setdefault(key, []).append(row)
    output = []
    for key, matches in grouped.items():
        chapter, state, candidate_name, office_text, year = key
        source_urls = sorted({row["source_url"].strip() for row in matches})
        mention_ids = sorted({row["mention_id"].strip() for row in matches})
        confidence = _max_confidence(row["confidence"] for row in matches)
        endorsement_key = hashlib.sha256("\n".join(key).encode()).hexdigest()[:24]
        output.append(
            {
                "endorsement_key": endorsement_key,
                "chapter": chapter,
                "state": state,
                "candidate_name": candidate_name,
                "office_text": office_text,
                "election_year": year,
                "election_stage": _stage(matches),
                "source_url": " | ".join(source_urls),
                "confidence": confidence,
                "review_status": "agent_reviewed",
                "mention_ids": " | ".join(mention_ids),
                "notes": " | ".join(
                    sorted({row["notes"].strip() for row in matches if row["notes"].strip()})
                ),
            }
        )
    return sorted(
        output,
        key=lambda row: (
            row["election_year"],
            row["state"],
            row["chapter"],
            row["candidate_name"],
        ),
    )


def _merge_structured_voter_guides(
    accepted: list[dict[str, str]],
) -> list[dict[str, str]]:
    path = PROCESSED_DIR / "structured_voter_guide_candidates.csv"
    if not path.exists():
        return accepted
    combined = {
        (
            row["chapter"],
            row["state"],
            row["candidate_name"],
            row["office_text"],
            row["election_year"],
        ): row
        for row in accepted
    }
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["role"] != "endorsed":
                continue
            key = (
                row["chapter"],
                row["state"],
                row["candidate_name"],
                row["office_text"],
                row["election_year"],
            )
            combined[key] = {
                "endorsement_key": hashlib.sha256("\n".join(key).encode()).hexdigest()[:24],
                "chapter": row["chapter"],
                "state": row["state"],
                "candidate_name": row["candidate_name"],
                "office_text": row["office_text"],
                "election_year": row["election_year"],
                "election_stage": row["election_stage"],
                "source_url": row["source_url"],
                "confidence": "high",
                "review_status": "verified",
                "mention_ids": "",
                "notes": row["notes"],
            }
    return sorted(
        combined.values(),
        key=lambda row: (
            row["election_year"],
            row["state"],
            row["chapter"],
            row["candidate_name"],
        ),
    )


def _max_confidence(values) -> str:
    rank = {"low": 0, "medium": 1, "high": 2}
    return max(values, key=lambda value: rank.get(value, -1))


def _stage(rows: list[dict[str, str]]) -> str:
    known = {
        row["election_stage"]
        for row in rows
        if row["election_stage"] not in {"", "unknown"}
    }
    return known.pop() if len(known) == 1 else "unknown"
