from collections import defaultdict
from pathlib import Path

from .io import read_csv, read_json, write_csv
from .paths import CONFIG_DIR, PROCESSED_DIR

SOCIAL_FIELDS = ("Facebook", "Instagram", "Twitter", "Bluesky", "Linktree", "Blog")


def build_coverage_ledger() -> tuple[int, int]:
    template = read_csv(PROCESSED_DIR / "coverage_template.csv")
    chapters = {
        row["record_id"]: row
        for row in read_csv(PROCESSED_DIR / "chapter_directory.csv")
    }
    crawl_status = _by_id("chapter_crawl_status.csv", "chapter_record_id")
    wayback_status = _by_id("wayback_crawl_status.csv", "chapter_record_id")
    evidence_years: dict[str, set[str]] = defaultdict(set)
    undated_evidence: set[str] = set()
    verified_years: dict[str, set[str]] = defaultdict(set)
    evidence_urls: dict[tuple[str, str], set[str]] = defaultdict(set)

    _add_page_evidence(evidence_years, evidence_urls, undated_evidence)
    _add_wayback_evidence(evidence_years, evidence_urls)
    _add_verified_endorsements(chapters, verified_years, evidence_urls)

    rows = []
    unresolved = 0
    current_year = read_json(CONFIG_DIR / "sources.json")["research_cutoff"][:4]
    for template_row in template:
        chapter_id, year = template_row["coverage_id"].rsplit("-", 1)
        chapter = chapters[chapter_id]
        current = crawl_status.get(chapter_id, {})
        historical = wayback_status.get(chapter_id, {})
        urls = sorted(evidence_urls[(chapter_id, year)])
        if year in verified_years[chapter_id]:
            status = "verified"
            method = "verified_first_party_endorsement"
        elif year in evidence_years[chapter_id]:
            status = "found_unverified"
            method = "chapter_site_or_wayback"
        elif _has_unsearched_social_source(chapter):
            status = "not_searched"
            method = "official_social_account_pending"
        elif (
            current.get("crawl_status") in {"searched_not_found", "found_unverified"}
            and historical.get("crawl_status") in {
                "searched_not_found",
                "found_unverified",
            }
            and not (year == current_year and chapter_id in undated_evidence)
        ):
            status = "searched_not_found"
            method = "current_site_and_wayback_url_index"
        elif (
            current.get("crawl_status") == "source_unavailable"
            and historical.get("crawl_status") in {"", "source_unavailable"}
        ):
            status = "source_unavailable"
            method = "no_public_website_or_archive"
        else:
            status = "not_searched"
            method = "additional_archive_review_needed"
        if status in {"not_searched", "found_unverified"}:
            unresolved += 1
        rows.append(
            {
                **template_row,
                "status": status,
                "search_method": method,
                "evidence_urls": " | ".join(urls),
                "notes": _notes(current, historical),
            }
        )
    write_csv(
        PROCESSED_DIR / "coverage_ledger.csv",
        rows,
        [
            "coverage_id",
            "chapter",
            "state",
            "election_year",
            "website",
            "status",
            "searched_on",
            "search_method",
            "evidence_urls",
            "notes",
        ],
    )
    return len(rows), unresolved


def _add_page_evidence(
    evidence_years: dict[str, set[str]],
    evidence_urls: dict[tuple[str, str], set[str]],
    undated_evidence: set[str],
) -> None:
    mentions_path = PROCESSED_DIR / "local_endorsement_mentions.csv"
    if not mentions_path.exists():
        return
    page_to_chapter = {
        row["page_id"]: row["chapter_record_id"]
        for row in read_csv(PROCESSED_DIR / "local_endorsement_pages.csv")
    }
    archive_path = PROCESSED_DIR / "archived_endorsement_pages.csv"
    if archive_path.exists():
        page_to_chapter.update(
            {
                row["page_id"]: row["chapter_record_id"]
                for row in read_csv(archive_path)
            }
        )
    for row in read_csv(mentions_path):
        chapter_id = page_to_chapter.get(row["page_id"], "")
        years = [year for year in row["inferred_years"].split(" | ") if year]
        if chapter_id and not years:
            undated_evidence.add(chapter_id)
        for year in years:
            if not chapter_id or not year:
                continue
            evidence_years[chapter_id].add(year)
            evidence_urls[(chapter_id, year)].add(row["page_url"])


def _add_wayback_evidence(
    evidence_years: dict[str, set[str]],
    evidence_urls: dict[tuple[str, str], set[str]],
) -> None:
    path = PROCESSED_DIR / "wayback_endorsement_urls.csv"
    if not path.exists():
        return
    for row in read_csv(path):
        chapter_id = row["chapter_record_id"]
        year = row["year"]
        evidence_years[chapter_id].add(year)
        evidence_urls[(chapter_id, year)].add(row["archive_url"])


def _add_verified_endorsements(
    chapters: dict[str, dict[str, str]],
    verified_years: dict[str, set[str]],
    evidence_urls: dict[tuple[str, str], set[str]],
) -> None:
    path = PROCESSED_DIR / "local_endorsements_verified.csv"
    if not path.exists():
        return
    chapter_ids = {
        row.get("Name", "").strip().lower(): chapter_id
        for chapter_id, row in chapters.items()
    }
    for row in read_csv(path):
        year = row["election_year"].strip()
        chapter_id = chapter_ids.get(row["chapter"].strip().lower(), "")
        if not chapter_id or len(year) != 4 or not year.isdigit():
            continue
        verified_years[chapter_id].add(year)
        for url in row["source_url"].split(" | "):
            if url:
                evidence_urls[(chapter_id, year)].add(url)


def _by_id(filename: str, key: str) -> dict[str, dict[str, str]]:
    path = PROCESSED_DIR / filename
    if not path.exists():
        return {}
    return {row[key]: row for row in read_csv(path)}


def _has_unsearched_social_source(chapter: dict[str, str]) -> bool:
    return not chapter.get("Website", "").strip() and any(
        chapter.get(field, "").strip() for field in SOCIAL_FIELDS
    )


def _notes(
    current: dict[str, str],
    historical: dict[str, str],
) -> str:
    values = []
    if current.get("error"):
        values.append(f'current: {current["error"]}')
    if historical.get("error"):
        values.append(f'wayback: {historical["error"]}')
    return " | ".join(values)
