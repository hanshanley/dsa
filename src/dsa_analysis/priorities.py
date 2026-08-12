from collections import Counter

from .io import read_csv, write_csv
from .paths import PROCESSED_DIR


def build_priority_queues() -> tuple[int, int]:
    coverage = read_csv(PROCESSED_DIR / "coverage_ledger.csv")
    endorsements = read_csv(PROCESSED_DIR / "local_endorsements_verified.csv")
    unresolved = [
        row
        for row in coverage
        if row["status"] in {"not_searched", "found_unverified"}
    ]
    unresolved_by_chapter = Counter(row["chapter"] for row in unresolved)
    known_by_chapter = Counter(row["chapter"] for row in endorsements)
    state_by_chapter = {
        row["chapter"]: row["state"]
        for row in coverage
    }
    chapter_rows = [
        {
            "chapter": chapter,
            "state": state_by_chapter.get(chapter, ""),
            "unresolved_chapter_years": unresolved_count,
            "known_verified_endorsements": known_by_chapter.get(chapter, 0),
            "priority_score": unresolved_count * (known_by_chapter.get(chapter, 0) + 1),
        }
        for chapter, unresolved_count in unresolved_by_chapter.items()
    ]
    chapter_rows.sort(
        key=lambda row: (
            -int(row["priority_score"]),
            -int(row["known_verified_endorsements"]),
            row["chapter"],
        )
    )
    write_csv(
        PROCESSED_DIR / "chapter_history_priority.csv",
        chapter_rows,
        [
            "chapter",
            "state",
            "unresolved_chapter_years",
            "known_verified_endorsements",
            "priority_score",
        ],
    )

    opponent_queue = read_csv(PROCESSED_DIR / "opponent_research_queue.csv")
    candidacy_rows = [
        row
        for row in opponent_queue
        if any(
            row[field]
            not in {
                "verified",
                "source_unavailable",
                "not_a_primary",
                "not_applicable",
            }
            for field in (
                "race_resolution_status",
                "opponent_roster_status",
                "candidate_statement_status",
                "opponent_statement_status",
            )
        )
    ]
    candidacy_rows.sort(
        key=lambda row: (
            row["election_year"] == "",
            row["election_year"],
            row["state"],
            row["candidate_name"],
        )
    )
    write_csv(
        PROCESSED_DIR / "remaining_candidacy_priority.csv",
        candidacy_rows,
        list(candidacy_rows[0]) if candidacy_rows else [
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
    return len(chapter_rows), len(candidacy_rows)
