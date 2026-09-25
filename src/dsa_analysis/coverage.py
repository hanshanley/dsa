import hashlib
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from .io import read_csv, read_json, write_csv
from .paths import CONFIG_DIR, MANUAL_DIR, PROCESSED_DIR

SOCIAL_FIELDS = ("Facebook", "Instagram", "Twitter", "Bluesky", "Linktree", "Blog")


def _chapter_key(name: str) -> str:
    return re.sub(r"\s+dsa$", "", " ".join(name.lower().split()))


def _chapter_identity(name: str, state: str) -> tuple[str, str]:
    return _chapter_key(name), state.strip().upper()


def coverage_chapters() -> list[dict[str, str]]:
    """Keep historical chapter identities even when absent from today's directory."""
    chapters = read_csv(PROCESSED_DIR / "chapter_directory.csv")
    known = {
        _chapter_identity(row.get("Name", ""), row.get("State", "")) for row in chapters
    }
    for filename in (
        "local_endorsements_verified.csv",
        "local_endorsement_candidates.csv",
        "chapter_history_gaps.csv",
    ):
        path = PROCESSED_DIR / filename
        if not path.exists():
            continue
        for row in read_csv(path):
            name = row.get("chapter", "").strip()
            key = _chapter_identity(name, row.get("state", ""))
            if not key[0] or key in known:
                continue
            known.add(key)
            chapters.append({
                "record_id": "historical-" + hashlib.sha256(
                    "\n".join(key).encode()
                ).hexdigest()[:16],
                "Name": name,
                "State": row.get("state", ""),
                "Website": "",
            })
    return chapters


def build_coverage_ledger() -> tuple[int, int]:
    template = read_csv(PROCESSED_DIR / "coverage_template.csv")
    chapters = {
        row["record_id"]: row
        for row in coverage_chapters()
    }
    crawl_status = _by_id("chapter_crawl_status.csv", "chapter_record_id")
    wayback_status = _by_id("wayback_crawl_status.csv", "chapter_record_id")
    evidence_years: dict[str, set[str]] = defaultdict(set)
    undated_evidence: set[str] = set()
    verified_years: dict[str, set[str]] = defaultdict(set)
    history_gaps: dict[str, set[str]] = defaultdict(set)
    evidence_urls: dict[tuple[str, str], set[str]] = defaultdict(set)

    _add_page_evidence(evidence_years, evidence_urls, undated_evidence)
    _add_wayback_evidence(evidence_years, evidence_urls)
    _add_verified_endorsements(chapters, verified_years, evidence_urls)
    _add_history_gaps(chapters, history_gaps, evidence_urls)
    resolutions = _coverage_resolutions()

    rows = []
    unresolved = 0
    cutoff = read_json(CONFIG_DIR / "sources.json")["research_cutoff"]
    current_year = cutoff[:4]
    for template_row in template:
        chapter_id, year = template_row["coverage_id"].rsplit("-", 1)
        chapter = chapters[chapter_id]
        current = crawl_status.get(chapter_id, {})
        historical = wayback_status.get(chapter_id, {})
        urls = sorted(evidence_urls[(chapter_id, year)])
        resolution = resolutions.get(template_row["coverage_id"])
        if resolution:
            status = resolution["status"]
            method = "reviewed_chapter_year_search"
            urls = sorted(set(urls + resolution["evidence_urls"].split(" | ")))
            if year == current_year and resolution["searched_on"] < cutoff:
                status = "found_unverified"
                method = "current_year_review_predates_cutoff"
        elif year in verified_years[chapter_id]:
            status = "found_unverified"
            method = "verified_endorsement_not_exhaustive_census"
        elif year in history_gaps[chapter_id]:
            status = "source_unavailable"
            method = "documented_chapter_history_gap"
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
            status = "not_searched"
            method = "url_index_searched_content_review_pending"
        elif (
            current.get("crawl_status") == "source_unavailable"
            and historical.get("crawl_status") in {"", "source_unavailable"}
        ):
            status = "not_searched"
            method = "website_or_archive_retry_needed"
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
                "searched_on": resolution["searched_on"] if resolution else "",
                "notes": resolution["notes"] if resolution else _notes(current, historical),
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


def _coverage_resolutions() -> dict[str, dict[str, str]]:
    path = MANUAL_DIR / "chapter_year_resolutions.csv"
    if not path.exists():
        return {}
    resolutions = {}
    for row in read_csv(path):
        key = row.get("coverage_id", "")
        if not key or key in resolutions:
            raise ValueError(f"{path.name}: missing or duplicate coverage_id {key!r}")
        if row.get("status") not in {"verified", "searched_not_found", "source_unavailable"}:
            raise ValueError(f"{key}: invalid chapter-year resolution status")
        if not row.get("notes", "").strip() or not row.get("evidence_urls", "").strip():
            raise ValueError(f"{key}: resolution requires search notes and evidence URLs")
        date.fromisoformat(row["searched_on"])
        resolutions[key] = row
    return resolutions


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
        _chapter_identity(row.get("Name", ""), row.get("State", "")): chapter_id
        for chapter_id, row in chapters.items()
    }
    for row in read_csv(path):
        year = row["election_year"].strip()
        chapter_id = chapter_ids.get(_chapter_identity(row["chapter"], row.get("state", "")), "")
        if not chapter_id or len(year) != 4 or not year.isdigit():
            continue
        verified_years[chapter_id].add(year)
        for url in row["source_url"].split(" | "):
            if url:
                evidence_urls[(chapter_id, year)].add(url)


def _add_history_gaps(
    chapters: dict[str, dict[str, str]],
    history_gaps: dict[str, set[str]],
    evidence_urls: dict[tuple[str, str], set[str]],
) -> None:
    path = PROCESSED_DIR / "chapter_history_gaps.csv"
    if not path.exists():
        return
    chapter_ids = {
        _chapter_identity(row.get("Name", ""), row.get("State", "")): chapter_id
        for chapter_id, row in chapters.items()
    }
    for row in read_csv(path):
        year = row["election_year"].strip()
        chapter_id = chapter_ids.get(_chapter_identity(row["chapter"], row.get("state", "")), "")
        if not chapter_id or len(year) != 4 or not year.isdigit():
            continue
        history_gaps[chapter_id].add(year)
        for url in (row["source_url"], row["archive_url"]):
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
