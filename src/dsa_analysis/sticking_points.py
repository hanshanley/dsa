import csv
import hashlib
import re
import unicodedata
from itertools import combinations

from .io import write_csv
from .paths import PROCESSED_DIR


def analyze_sticking_points() -> tuple[int, int]:
    evidence_path = PROCESSED_DIR / "candidate_statement_evidence.csv"
    if not evidence_path.exists():
        raise FileNotFoundError("Run merge-statement-reviews first")
    with evidence_path.open(newline="", encoding="utf-8") as handle:
        evidence = [
            row
            for row in csv.DictReader(handle)
            if row["evidence_status"] == "verified" and row["quote"].strip()
        ]
    rows = []
    explicit = 0
    roles_by_race: dict[str, dict[str, str]] = {}
    display_names: dict[tuple[str, str], str] = {}
    for row in evidence:
        identity = _identity_name(row["candidate_name"])
        roles_by_race.setdefault(row["race_id"], {})[identity] = row["role"]
        display_names.setdefault((row["race_id"], identity), row["candidate_name"])
    for row in evidence:
        if not row["direct_opponent_name"].strip():
            continue
        roles = roles_by_race.get(row["race_id"], {})
        candidate_identity = _identity_name(row["candidate_name"])
        opponent_identity = _identity_name(row["direct_opponent_name"])
        if (
            row["role"] not in {"endorsed", "unopposed"}
            and roles.get(opponent_identity) not in {"endorsed", "unopposed"}
        ):
            continue
        rows.append(
            _row(
                row,
                display_names.get((row["race_id"], candidate_identity), row["candidate_name"]),
                display_names.get(
                    (row["race_id"], opponent_identity),
                    row["direct_opponent_name"],
                ),
                "explicit_conflict",
                "explicit_disagreement",
                row["quote"],
                "",
                row["source_url"],
                "",
            )
        )
        explicit += 1

    by_race_topic: dict[tuple[str, str], dict[str, list[dict[str, str]]]] = {}
    for row in evidence:
        if not row["topic"].strip():
            continue
        candidate_identity = _identity_name(row["candidate_name"])
        by_race_topic.setdefault(
            (row["race_id"], row["topic"]), {}
        ).setdefault(candidate_identity, []).append(row)
    coded = 0
    for (_race_id, _topic), candidates in by_race_topic.items():
        for candidate_a, candidate_b in combinations(sorted(candidates), 2):
            roles = roles_by_race.get(_race_id, {})
            if not (
                roles.get(candidate_a) in {"endorsed", "unopposed"}
                or roles.get(candidate_b) in {"endorsed", "unopposed"}
            ):
                continue
            relation, left, right = _relationship(
                candidates[candidate_a],
                candidates[candidate_b],
            )
            if not relation:
                continue
            rows.append(
                _row(
                    left,
                    display_names.get((_race_id, candidate_a), candidate_a),
                    display_names.get((_race_id, candidate_b), candidate_b),
                    "coded_divergence",
                    relation,
                    left["quote"],
                    right["quote"],
                    left["source_url"],
                    right["source_url"],
                )
            )
            coded += 1
    write_csv(
        PROCESSED_DIR / "primary_sticking_points.csv",
        rows,
        [
            "sticking_point_id",
            "race_id",
            "topic",
            "subtopic",
            "candidate_a",
            "candidate_b",
            "contrast_type",
            "relationship_code",
            "candidate_a_quote",
            "candidate_b_quote",
            "candidate_a_source",
            "candidate_b_source",
        ],
    )
    return explicit, coded


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


def _relationship(
    left_rows: list[dict[str, str]],
    right_rows: list[dict[str, str]],
) -> tuple[str, dict[str, str], dict[str, str]]:
    for left in left_rows:
        for right in right_rows:
            if {left["stance"], right["stance"]} == {"support", "oppose"}:
                return "explicit_disagreement", left, right
    for left in left_rows:
        for right in right_rows:
            if (
                left["subtopic"]
                and right["subtopic"]
                and left["subtopic"] != right["subtopic"]
            ):
                return "different_mechanism", left, right
    return "", {}, {}


def _row(
    evidence: dict[str, str],
    candidate_a: str,
    candidate_b: str,
    contrast_type: str,
    relationship_code: str,
    quote_a: str,
    quote_b: str,
    source_a: str,
    source_b: str,
) -> dict[str, str]:
    value = (
        f'{evidence["race_id"]}\n{evidence["topic"]}\n{candidate_a}\n'
        f"{candidate_b}\n{contrast_type}\n{quote_a}\n{quote_b}"
    )
    return {
        "sticking_point_id": hashlib.sha256(value.encode()).hexdigest()[:24],
        "race_id": evidence["race_id"],
        "topic": evidence["topic"],
        "subtopic": evidence["subtopic"],
        "candidate_a": candidate_a,
        "candidate_b": candidate_b,
        "contrast_type": contrast_type,
        "relationship_code": relationship_code,
        "candidate_a_quote": quote_a,
        "candidate_b_quote": quote_b,
        "candidate_a_source": source_a,
        "candidate_b_source": source_b,
    }
