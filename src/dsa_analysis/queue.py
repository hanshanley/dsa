from .io import read_csv, read_json, write_csv
from .paths import CONFIG_DIR, PROCESSED_DIR


def build_research_queue() -> tuple[int, int]:
    endorsements = read_csv(PROCESSED_DIR / "national_endorsement_archive.csv")
    chapters = read_csv(PROCESSED_DIR / "chapter_directory.csv")
    config = read_json(CONFIG_DIR / "sources.json")
    first_year = int(config["study_start"][:4])
    final_year = int(config["research_cutoff"][:4])

    candidate_rows = []
    for row in endorsements:
        office_types = row["office_types"].split(" | ")
        if office_types and all(value == "Ballot Initiative" for value in office_types):
            continue
        candidate_rows.append(
            {
                "record_id": row["record_id"],
                "candidate": row["campaign"],
                "office": row["office"],
                "office_types": row["office_types"],
                "election_date": row["election_date"],
                "endorsing_chapters": row["endorsing_chapters"],
                "national_endorsement": row["national_endorsement"],
                "primary_result": row["primary_result"],
                "democratic_primary_status": "needs_verification",
                "candidate_sources_status": "not_searched",
                "opponent_sources_status": "not_searched",
                "notes": "",
            }
        )
    write_csv(
        PROCESSED_DIR / "primary_research_queue.csv",
        candidate_rows,
        [
            "record_id",
            "candidate",
            "office",
            "office_types",
            "election_date",
            "endorsing_chapters",
            "national_endorsement",
            "primary_result",
            "democratic_primary_status",
            "candidate_sources_status",
            "opponent_sources_status",
            "notes",
        ],
    )

    coverage_rows = []
    for chapter in chapters:
        name = chapter.get("Name", "").strip()
        state = chapter.get("State", "").strip()
        if not name:
            continue
        for year in range(first_year, final_year + 1):
            coverage_rows.append(
                {
                    "coverage_id": f'{chapter["record_id"]}-{year}',
                    "chapter": name,
                    "state": state,
                    "election_year": year,
                    "website": chapter.get("Website", ""),
                    "status": "not_searched",
                    "searched_on": "",
                    "notes": "Seeded from current directory; historical chapter status needs review",
                }
            )
    write_csv(
        PROCESSED_DIR / "coverage_template.csv",
        coverage_rows,
        [
            "coverage_id",
            "chapter",
            "state",
            "election_year",
            "website",
            "status",
            "searched_on",
            "notes",
        ],
    )
    return len(candidate_rows), len(coverage_rows)
