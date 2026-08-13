import csv
import hashlib
import re
import unicodedata
import heapq
import json
from pathlib import Path

from .io import write_csv
from .paths import PROCESSED_DIR

SESSION_BATCH_DIR = Path(
    "/Users/hanshanley/.copilot/session-state/"
    "0ed4a415-a2be-4bcc-9083-2ca717c4ece8/files/opponent_batches"
)
ROSTER_FIELDS = [
    "queue_id",
    "resolution_status",
    "race_id",
    "primary_type",
    "election_date",
    "candidate_name",
    "party",
    "role",
    "outcome",
    "official_election_source",
    "notes",
]


def prepare_opponent_batches(count: int = 8) -> tuple[int, int]:
    queue_path = PROCESSED_DIR / "opponent_research_queue.csv"
    if not queue_path.exists():
        raise FileNotFoundError("Run build-opponent-queue first")
    with queue_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    SESSION_BATCH_DIR.mkdir(parents=True, exist_ok=True)
    existing_ids = set()
    existing_indices = []
    for path in sorted(SESSION_BATCH_DIR.glob("opponent_batch_*.jsonl")):
        existing_indices.append(int(path.stem.rsplit("_", 1)[1]))
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                existing_ids.add(json.loads(line)["queue_id"])
    rows = [row for row in rows if row["queue_id"] not in existing_ids]
    if not rows:
        return 0, 0
    batches: list[list[dict[str, str]]] = [[] for _ in range(count)]
    heap = [(0, index) for index in range(count)]
    for row in sorted(
        rows,
        key=lambda item: len(item["candidate_name"]) + len(item["office_text"]),
        reverse=True,
    ):
        size, index = heapq.heappop(heap)
        batches[index].append(row)
        heapq.heappush(
            heap,
            (size + len(row["candidate_name"]) + len(row["office_text"]) + 80, index),
        )
    start_index = max(existing_indices, default=-1) + 1
    written = 0
    for offset, batch in enumerate(batches):
        if not batch:
            continue
        index = start_index + offset
        path = SESSION_BATCH_DIR / f"opponent_batch_{index:02d}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for row in batch:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        written += 1
    return len(rows), written


def merge_opponent_reviews(
    batch_dir: Path = SESSION_BATCH_DIR,
    require_complete: bool = True,
) -> tuple[int, int, int]:
    expected = _expected_queue_ids(batch_dir)
    roster_rows = []
    covered: set[str] = set()
    for path in sorted(batch_dir.glob("opponent_review_*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = set(ROSTER_FIELDS) - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
            for row in reader:
                if row["queue_id"] not in expected:
                    raise ValueError(f"{path.name}: unknown queue_id")
                if row["resolution_status"] not in {
                    "verified",
                    "not_a_primary",
                    "source_unavailable",
                }:
                    raise ValueError(f"{path.name}: invalid resolution_status")
                if row["role"] not in {"endorsed", "opponent", "unopposed", ""}:
                    raise ValueError(f"{path.name}: invalid role")
                covered.add(row["queue_id"])
                roster_rows.append(row)
    uncovered = expected - covered
    if uncovered and require_complete:
        raise ValueError(f"{len(uncovered)} opponent queue rows remain unreviewed")

    queue_path = PROCESSED_DIR / "opponent_research_queue.csv"
    with queue_path.open(newline="", encoding="utf-8") as handle:
        queue_rows = list(csv.DictReader(handle))
    valid_queue_ids = {row["queue_id"] for row in queue_rows}
    roster_rows = _canonicalize_races(
        [row for row in roster_rows if row["queue_id"] in valid_queue_ids]
    )
    by_queue: dict[str, list[dict[str, str]]] = {}
    for row in roster_rows:
        by_queue.setdefault(row["queue_id"], []).append(row)
    updated = []
    resolved = 0
    unavailable = 0
    for row in queue_rows:
        reviews = by_queue.get(row["queue_id"])
        if not reviews:
            updated.append(row)
            continue
        statuses = {review["resolution_status"] for review in reviews}
        if statuses == {"verified"}:
            status = "verified"
        elif statuses == {"not_a_primary"}:
            status = "not_a_primary"
        else:
            status = "source_unavailable"
        sources = sorted(
            {
                review["official_election_source"]
                for review in reviews
                if review["official_election_source"]
            }
        )
        row["race_resolution_status"] = status
        row["opponent_roster_status"] = (
            "not_applicable" if status == "not_a_primary" else status
        )
        if status == "not_a_primary":
            row["candidate_statement_status"] = "not_applicable"
            row["opponent_statement_status"] = "not_applicable"
        row["official_election_source"] = " | ".join(sources)
        row["notes"] = " | ".join(
            sorted(
                {
                    value
                    for value in (
                        row["notes"],
                        *(review["notes"] for review in reviews),
                    )
                    if value
                }
            )
        )
        resolved += status in {"verified", "not_a_primary"}
        unavailable += status == "source_unavailable"
        updated.append(row)
    write_csv(
        queue_path,
        updated,
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
    write_csv(
        PROCESSED_DIR / "race_rosters_discovered.csv",
        roster_rows,
        ROSTER_FIELDS,
    )
    return len(covered), resolved, unavailable


def _canonicalize_races(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    by_queue: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_queue.setdefault(row["queue_id"], []).append(row)
    fingerprint_ids: dict[tuple, str] = {}
    for queue_rows in by_queue.values():
        verified = [
            row for row in queue_rows if row["resolution_status"] == "verified"
        ]
        if not verified:
            continue
        fingerprint = (
            verified[0]["election_date"],
            verified[0]["primary_type"],
            tuple(
                sorted(
                    (
                        _fingerprint_name(row["candidate_name"]),
                        row["party"].strip().casefold(),
                    )
                    for row in verified
                )
            ),
        )
        race_id = fingerprint_ids.setdefault(
            fingerprint,
            "race-" + hashlib.sha256(repr(fingerprint).encode()).hexdigest()[:20],
        )
        for row in queue_rows:
            if row["resolution_status"] == "verified":
                row["race_id"] = race_id
    return rows


def _fingerprint_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = (
        value.replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("–", "-")
        .replace("—", "-")
    )
    return re.sub(r"\s+", " ", value).strip().casefold()


def _expected_queue_ids(batch_dir: Path) -> set[str]:
    ids = set()
    for path in sorted(batch_dir.glob("opponent_batch_*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                ids.add(json.loads(line)["queue_id"])
    if not ids:
        raise ValueError("No opponent batch inputs were found")
    return ids
