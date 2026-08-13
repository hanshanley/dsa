import csv
import hashlib
import heapq
import json
import re
import unicodedata
from pathlib import Path

from .io import read_csv, read_json, write_csv
from .paths import CONFIG_DIR, PROCESSED_DIR

SESSION_BATCH_DIR = Path(
    "/Users/hanshanley/.copilot/session-state/"
    "0ed4a415-a2be-4bcc-9083-2ca717c4ece8/files/statement_batches"
)
OPPONENT_BATCH_DIR = Path(
    "/Users/hanshanley/.copilot/session-state/"
    "0ed4a415-a2be-4bcc-9083-2ca717c4ece8/files/opponent_batches"
)
EVIDENCE_FIELDS = [
    "statement_key",
    "evidence_status",
    "source_url",
    "source_type",
    "published_date",
    "quote",
    "locator",
    "topic",
    "subtopic",
    "stance",
    "direct_opponent_name",
    "notes",
]


def prepare_statement_batches(count: int = 16) -> tuple[int, int]:
    roster_path = PROCESSED_DIR / "race_rosters_discovered.csv"
    if not roster_path.exists():
        raise FileNotFoundError("Run merge-opponent-reviews first")
    with roster_path.open(newline="", encoding="utf-8") as handle:
        roster = list(csv.DictReader(handle))
    rows = list(_records(roster).values())
    written = _write_missing_batches(rows, count)
    return len(rows), written


def prepare_partial_statement_batches(count: int = 4) -> tuple[int, int]:
    roster = []
    for path in sorted(OPPONENT_BATCH_DIR.glob("opponent_review_*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            roster.extend(csv.DictReader(handle))
    rows = list(_records(roster).values())
    written = _write_missing_batches(rows, count)
    return len(rows), written


def _records(roster: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    records = {}
    for row in roster:
        if row["resolution_status"] != "verified" or row["role"] not in {
            "endorsed",
            "opponent",
            "unopposed",
        }:
            continue
        key = hashlib.sha256(
            f'{row["race_id"]}\n{row["candidate_name"]}\n{row["party"]}'.encode()
        ).hexdigest()[:24]
        records[key] = {
            "statement_key": key,
            "queue_id": row["queue_id"],
            "race_id": row["race_id"],
            "primary_type": row["primary_type"],
            "election_date": row["election_date"],
            "candidate_name": row["candidate_name"],
            "party": row["party"],
            "role": row["role"],
            "official_election_source": row["official_election_source"],
        }
    return records


def _write_missing_batches(rows: list[dict[str, str]], count: int) -> int:
    SESSION_BATCH_DIR.mkdir(parents=True, exist_ok=True)
    existing_keys = set()
    existing_indices = []
    for path in sorted(SESSION_BATCH_DIR.glob("statement_batch_*.jsonl")):
        existing_indices.append(int(path.stem.rsplit("_", 1)[1]))
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                existing_keys.add(json.loads(line)["statement_key"])
    rows = [row for row in rows if row["statement_key"] not in existing_keys]
    if not rows:
        return 0
    batches: list[list[dict[str, str]]] = [[] for _ in range(count)]
    heap = [(0, index) for index in range(count)]
    for row in sorted(rows, key=lambda item: len(item["candidate_name"]), reverse=True):
        size, index = heapq.heappop(heap)
        batches[index].append(row)
        heapq.heappush(heap, (size + len(row["candidate_name"]) + 120, index))
    start_index = max(existing_indices, default=-1) + 1
    written = 0
    for offset, batch in enumerate(batches):
        if not batch:
            continue
        index = start_index + offset
        path = SESSION_BATCH_DIR / f"statement_batch_{index:02d}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for row in batch:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        written += 1
    return written


def merge_statement_reviews(
    batch_dir: Path = SESSION_BATCH_DIR,
    require_complete: bool = True,
) -> tuple[int, int, int]:
    expected, metadata = _expected(batch_dir)
    taxonomy = read_json(CONFIG_DIR / "taxonomy.json")
    topics = set(taxonomy["topics"])
    evidence = []
    covered = set()
    for path in sorted(batch_dir.glob("statement_review_*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = set(EVIDENCE_FIELDS) - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
            for row in reader:
                key = row["statement_key"]
                if key not in expected:
                    raise ValueError(f"{path.name}: unknown statement_key")
                if row["evidence_status"] not in {"verified", "source_unavailable"}:
                    raise ValueError(f"{path.name}: invalid evidence_status")
                if row["evidence_status"] == "verified" and (
                    not row["source_url"].strip() or not row["quote"].strip()
                ):
                    raise ValueError(f"{path.name}: verified evidence lacks source or quote")
                if row["evidence_status"] == "verified" and (
                    row["topic"] not in topics
                    or row["subtopic"] not in taxonomy["topics"].get(row["topic"], [])
                ):
                    raise ValueError(f"{path.name}: invalid topic code")
                if row["evidence_status"] == "verified" and row["stance"] not in {
                    "support",
                    "oppose",
                    "mixed",
                    "unclear",
                }:
                    raise ValueError(f"{path.name}: invalid stance")
                covered.add(key)
                evidence.append({**metadata[key], **row})
    uncovered = expected - covered
    if uncovered and require_complete:
        raise ValueError(f"{len(uncovered)} primary candidates lack evidence review")
    queue_path = PROCESSED_DIR / "opponent_research_queue.csv"
    valid_queue_ids = {
        row["queue_id"] for row in read_csv(queue_path)
    } if queue_path.exists() else set()
    roster_path = PROCESSED_DIR / "race_rosters_discovered.csv"
    roster = read_csv(roster_path) if roster_path.exists() else []
    evidence = _expand_to_active_queues(evidence, roster, valid_queue_ids)
    write_csv(
        PROCESSED_DIR / "candidate_statement_evidence.csv",
        evidence,
        [
            "statement_key",
            "queue_id",
            "race_id",
            "primary_type",
            "election_date",
            "candidate_name",
            "party",
            "role",
            "official_election_source",
            "evidence_status",
            "source_url",
            "source_type",
            "published_date",
            "quote",
            "locator",
            "topic",
            "subtopic",
            "stance",
            "direct_opponent_name",
            "notes",
        ],
    )
    _update_opponent_queue(evidence)
    verified = sum(row["evidence_status"] == "verified" for row in evidence)
    unavailable = sum(row["evidence_status"] == "source_unavailable" for row in evidence)
    return len(covered), verified, unavailable


def _expand_to_active_queues(
    evidence: list[dict[str, str]],
    roster: list[dict[str, str]],
    valid_queue_ids: set[str],
) -> list[dict[str, str]]:
    canonical_by_queue = {
        row["queue_id"]: row["race_id"]
        for row in roster
        if row["resolution_status"] == "verified"
    }
    for row in evidence:
        canonical = canonical_by_queue.get(row["queue_id"])
        if canonical:
            row["race_id"] = canonical
    if not valid_queue_ids:
        return evidence

    targets_by_race: dict[tuple[str, str], list[dict[str, str]]] = {}
    targets_by_date: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in roster:
        if (
            row["resolution_status"] != "verified"
            or row["queue_id"] not in valid_queue_ids
        ):
            continue
        identity = _identity_name(row["candidate_name"])
        targets_by_race.setdefault((row["race_id"], identity), []).append(row)
        targets_by_date.setdefault((row["election_date"], identity), []).append(row)

    expanded = []
    seen = set()
    for row in evidence:
        identity = _identity_name(row["candidate_name"])
        targets = [
            *targets_by_race.get((row["race_id"], identity), []),
            *targets_by_date.get((row["election_date"], identity), []),
        ]
        for target in targets:
            clone = {
                **row,
                "queue_id": target["queue_id"],
                "race_id": target["race_id"],
                "primary_type": target["primary_type"],
                "election_date": target["election_date"],
                "candidate_name": target["candidate_name"],
                "party": target["party"],
                "role": target["role"],
                "official_election_source": target["official_election_source"],
            }
            dedupe_key = (
                clone["queue_id"],
                clone["race_id"],
                _identity_name(clone["candidate_name"]),
                clone["evidence_status"],
                clone["source_url"],
                clone["quote"],
                clone["locator"],
            )
            if dedupe_key not in seen:
                seen.add(dedupe_key)
                expanded.append(clone)
    return expanded


def _identity_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = (
        value.replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("–", "-")
        .replace("—", "-")
    )
    return re.sub(r"\s+", " ", value).strip().casefold()


def _expected(
    batch_dir: Path,
) -> tuple[set[str], dict[str, dict[str, str]]]:
    ids = set()
    metadata = {}
    for path in sorted(batch_dir.glob("statement_batch_*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                ids.add(row["statement_key"])
                metadata[row["statement_key"]] = row
    if not ids:
        raise ValueError("No statement batch inputs were found")
    return ids, metadata


def _update_opponent_queue(evidence: list[dict[str, str]]) -> None:
    queue_path = PROCESSED_DIR / "opponent_research_queue.csv"
    with queue_path.open(newline="", encoding="utf-8") as handle:
        queue_rows = list(csv.DictReader(handle))
    by_queue: dict[str, list[dict[str, str]]] = {}
    for row in evidence:
        by_queue.setdefault(row["queue_id"], []).append(row)
    for row in queue_rows:
        if row["race_resolution_status"] == "not_a_primary":
            row["candidate_statement_status"] = "not_applicable"
            row["opponent_statement_status"] = "not_applicable"
            continue
        if row["race_resolution_status"] == "source_unavailable":
            row["candidate_statement_status"] = "source_unavailable"
            row["opponent_statement_status"] = "source_unavailable"
            continue
        row["candidate_statement_status"] = "not_searched"
        row["opponent_statement_status"] = "not_searched"
        reviews = by_queue.get(row["queue_id"], [])
        if not reviews:
            continue
        endorsed = [review for review in reviews if review["role"] in {"endorsed", "unopposed"}]
        opponents = [review for review in reviews if review["role"] == "opponent"]
        if endorsed:
            row["candidate_statement_status"] = _group_status(endorsed)
        row["opponent_statement_status"] = (
            "not_applicable" if not opponents else _group_status(opponents)
        )
    write_csv(
        queue_path,
        queue_rows,
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


def _group_status(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "source_unavailable"
    statuses = {row["evidence_status"] for row in rows}
    return "verified" if "verified" in statuses else "source_unavailable"
