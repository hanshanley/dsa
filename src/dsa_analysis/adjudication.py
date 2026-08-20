import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from .io import merge_notes, read_csv, read_json, write_csv
from .paths import CONFIG_DIR, MANUAL_DIR, PROCESSED_DIR

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
    source_config = read_json(CONFIG_DIR / "sources.json")
    final_year = int(source_config["research_cutoff"][:4])
    allowed_years = {str(year) for year in range(2016, final_year + 1)}
    rows_by_key = {}
    unresolved_local = []
    for candidate in candidates:
        unresolved_reasons = []
        if candidate["election_year"] not in allowed_years:
            unresolved_reasons.append(
                "missing_or_out_of_window_election_year"
            )
        if not candidate["office_text"].strip():
            unresolved_reasons.append("missing_office")
        if unresolved_reasons:
            unresolved_local.append(
                {
                    **candidate,
                    "resolution_reason": " | ".join(unresolved_reasons),
                }
            )
            continue
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

    national_resolutions = {
        row["record_id"]: row
        for path in sorted(MANUAL_DIR.glob("national_census_resolutions_*.csv"))
        for row in read_csv(path)
    }
    reconciliation_path = (
        PROCESSED_DIR / "race_registry_national_endorsement_reconciliation.csv"
    )
    reconciliation = {
        row["record_id"]: row
        for row in read_csv(reconciliation_path)
    } if reconciliation_path.exists() else {}
    registry_path = PROCESSED_DIR / "race_registry.csv"
    registry_by_id = {
        row["race_id"]: row
        for row in read_csv(registry_path)
    } if registry_path.exists() else {}
    national_path = PROCESSED_DIR / "national_endorsement_archive.csv"
    if national_path.exists():
        with national_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                office_types = set(row["office_types"].split(" | "))
                if "Ballot Initiative" in office_types:
                    continue
                resolution = national_resolutions.get(row["record_id"], {})
                year = (
                    resolution.get("primary_date", "")[:4]
                    or row["election_date"][:4]
                )
                candidate = {
                    "candidate_name": row["campaign"],
                    "office_text": resolution.get("office", "") or row["office"],
                    "election_year": year,
                    "state": resolution.get("state", ""),
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
                    election_stage=(
                        "primary"
                        if resolution.get("classification", "")
                        == "democratic_primary"
                        else "unknown"
                    ),
                    endorsement_source_url=row["source_view_url"],
                    notes="Official DSA National endorsement archive",
                )
                new_row = _preserve_queue_status(
                    new_row,
                    existing_by_id.get(new_row["queue_id"]),
                )
                classification = resolution.get("classification", "")
                if classification == "democratic_primary":
                    new_row["race_resolution_status"] = "verified"
                    new_row["official_election_source"] = resolution.get(
                        "official_election_source", ""
                    ).split(" ; ")[0]
                    new_row["opponent_roster_status"] = (
                        "verified"
                        if _resolved_opponent_names(
                            resolution.get("opponents", "")
                        )
                        else "not_searched"
                    )
                elif classification == "source_unavailable":
                    new_row["race_resolution_status"] = "source_unavailable"
                    new_row["opponent_roster_status"] = "source_unavailable"
                    new_row["candidate_statement_status"] = "source_unavailable"
                    new_row["opponent_statement_status"] = "source_unavailable"
                elif classification:
                    new_row["race_resolution_status"] = "not_a_primary"
                    new_row["opponent_roster_status"] = "not_applicable"
                    new_row["candidate_statement_status"] = "not_applicable"
                    new_row["opponent_statement_status"] = "not_applicable"
                elif (
                    reconciliation.get(row["record_id"], {}).get(
                        "registry_status", ""
                    )
                    == "matched_in_scope"
                ):
                    matched_race_ids = reconciliation[row["record_id"]].get(
                        "matched_race_ids", ""
                    ).split(" | ")
                    matched_registry = next(
                        (
                            registry_by_id[race_id]
                            for race_id in matched_race_ids
                            if race_id in registry_by_id
                        ),
                        {},
                    )
                    new_row["race_resolution_status"] = "verified"
                    new_row["official_election_source"] = matched_registry.get(
                        "official_election_source", ""
                    )
                    new_row["opponent_roster_status"] = (
                        "verified"
                        if matched_registry.get("certified_opponents", "")
                        else "not_searched"
                    )
                rows_by_key[key] = new_row
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
    write_csv(
        PROCESSED_DIR / "local_endorsement_resolution_queue.csv",
        unresolved_local,
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
            "resolution_reason",
        ],
    )
    return len(rows)


def _resolved_opponent_names(value: str) -> list[str]:
    placeholders = {
        "april general field",
        "democratic primary field",
        "district democratic field",
        "none listed",
    }
    return [
        name.strip()
        for name in re.split(r"\s*[;|]\s*", value)
        if name.strip() and name.strip().casefold() not in placeholders
    ]


def _identity(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    return " ".join(
        re.sub(r"[^a-z0-9]+", " ", normalized.casefold()).split()
    )


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
        new_row["notes"] = merge_notes(new_row["notes"], existing["notes"])
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
    covered_years = {
        row["election_year"].strip()
        for row in rows
        if len(row["election_year"].strip()) == 4
    }
    verified_path = PROCESSED_DIR / "local_endorsements_verified.csv"
    existing = []
    if verified_path.exists():
        with verified_path.open(newline="", encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))
    if replace_chapter:
        existing = [
            row
            for row in existing
            if row["chapter"] != chapter
            or row["election_year"] not in covered_years
        ]
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
            prior = [
                row
                for row in prior
                if row["chapter"] != chapter
                or row["election_year"] not in covered_years
            ]
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


def enrich_verified_endorsements_from_registry() -> tuple[int, int, int]:
    verified_path = PROCESSED_DIR / "local_endorsements_verified.csv"
    registry_path = PROCESSED_DIR / "race_registry.csv"
    if not verified_path.exists() or not registry_path.exists():
        return 0, 0, 0
    registry_by_candidate: dict[str, list[dict[str, str]]] = {}
    for registry_row in read_csv(registry_path):
        for candidate_name in registry_row.get("all_candidates", "").split(" | "):
            key = _identity(candidate_name)
            if key:
                registry_by_candidate.setdefault(key, []).append(registry_row)

    rows = read_csv(verified_path)
    years_enriched = 0
    offices_enriched = 0
    unresolved = 0
    final_year = int(
        read_json(CONFIG_DIR / "sources.json")["research_cutoff"][:4]
    )
    for row in rows:
        matches = [
            match
            for match in registry_by_candidate.get(
                _identity(row["candidate_name"]), []
            )
            if not row["state"]
            or not match.get("state_code", "")
            or row["state"] == match["state_code"]
        ]
        unique_matches = {
            (
                match.get("election_year", ""),
                match.get("office", ""),
                match.get("state_code", ""),
            ): match
            for match in matches
        }
        if len(unique_matches) != 1:
            if not row["election_year"] or not row["office_text"]:
                unresolved += 1
            continue
        match = next(iter(unique_matches.values()))
        match_year = match.get("election_year", "")
        if (
            not row["election_year"]
            and match_year.isdigit()
            and 2016 <= int(match_year) <= final_year
        ):
            row["election_year"] = match_year
            years_enriched += 1
        if not row["office_text"] and match.get("office", ""):
            row["office_text"] = match["office"]
            offices_enriched += 1
        if not row["election_year"] or not row["office_text"]:
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
    return years_enriched, offices_enriched, unresolved


def merge_local_metadata_reviews(batch_dir: Path) -> tuple[int, int, int]:
    expected: set[str] = set()
    for path in sorted(batch_dir.glob("metadata_batch_*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                expected.add(json.loads(line)["endorsement_key"])
    if not expected:
        raise ValueError("No local metadata batch inputs were found")

    required = {
        "endorsement_key",
        "decision",
        "office_text",
        "election_year",
        "election_stage",
        "official_source",
        "notes",
    }
    reviews: dict[str, dict[str, str]] = {}
    for path in sorted(batch_dir.glob("metadata_review_*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
            for row in reader:
                key = row["endorsement_key"].strip()
                if key not in expected:
                    raise ValueError(f"{path.name}: unknown endorsement_key {key}")
                if key in reviews:
                    raise ValueError(f"{path.name}: duplicate endorsement_key {key}")
                if row["decision"] not in {
                    "resolved",
                    "out_of_window",
                    "source_unavailable",
                }:
                    raise ValueError(f"{path.name}: invalid decision")
                if row["decision"] == "resolved" and (
                    not row["office_text"].strip()
                    or not re.fullmatch(r"20\d{2}", row["election_year"].strip())
                ):
                    raise ValueError(
                        f"{path.name}: resolved row lacks office or four-digit year"
                    )
                reviews[key] = row
    uncovered = expected - set(reviews)
    if uncovered:
        raise ValueError(f"{len(uncovered)} local metadata rows remain unreviewed")

    verified_path = PROCESSED_DIR / "local_endorsements_verified.csv"
    verified = []
    out_of_window = []
    unavailable = 0
    for candidate in read_csv(verified_path):
        review = reviews.get(candidate["endorsement_key"])
        if not review:
            verified.append(candidate)
            continue
        decision = review["decision"]
        candidate["notes"] = merge_notes(
            candidate["notes"],
            review["notes"].strip(),
            (
                f"Metadata source: {review['official_source'].strip()}"
                if review["official_source"].strip()
                else ""
            ),
        )
        if decision == "out_of_window":
            candidate["office_text"] = (
                review["office_text"].strip() or candidate["office_text"]
            )
            candidate["election_year"] = review["election_year"].strip()
            candidate["election_stage"] = (
                review["election_stage"].strip() or candidate["election_stage"]
            )
            out_of_window.append(candidate)
            continue
        if decision == "source_unavailable":
            unavailable += 1
            verified.append(candidate)
            continue
        candidate["office_text"] = review["office_text"].strip()
        candidate["election_year"] = review["election_year"].strip()
        candidate["election_stage"] = (
            review["election_stage"].strip() or "unknown"
        )
        verified.append(candidate)

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
    write_csv(verified_path, verified, fieldnames)
    write_csv(
        PROCESSED_DIR / "local_endorsements_out_of_window.csv",
        out_of_window,
        fieldnames,
    )
    return len(reviews), len(out_of_window), unavailable


def _input_ids(batch_dir: Path) -> set[str]:
    input_ids = set()
    for path in sorted(batch_dir.glob("batch_*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                input_ids.add(json.loads(line)["mention_id"])
    for path in sorted(batch_dir.glob("input_*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                mention_id = row.get("mention_id", "").strip()
                if mention_id:
                    input_ids.add(mention_id)
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
