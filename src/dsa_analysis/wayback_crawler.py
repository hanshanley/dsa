import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

from .chapter_crawler import normalize_url
from .io import read_csv, write_csv
from .paths import PROCESSED_DIR

USER_AGENT = "dsa-analysis/0.1 (+public historical endorsement research)"
STRONG_HISTORICAL_TERMS = (
    "endorse",
    "endorsement",
    "endorsed",
    "voter-guide",
    "voterguide",
    "slate",
)
EXCLUDED_PATH_PARTS = (
    "/wp-content/",
    "/wp-includes/",
    "/plugins/",
    "/themes/",
    "/assets/",
    "/static/",
    "/calendar/category/",
    "/events/category/",
)
EXCLUDED_SUFFIXES = (
    ".js",
    ".css",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".woff",
    ".woff2",
    ".ttf",
    ".ico",
    ".ics",
    ".map",
)


def discover_wayback_urls(workers: int = 8) -> tuple[int, int]:
    chapters = read_csv(PROCESSED_DIR / "chapter_directory.csv")
    rows = []
    status_rows = []
    targets = [chapter for chapter in chapters if chapter.get("Website", "").strip()]
    if workers == 1:
        for chapter in targets:
            chapter_rows, status = _discover_chapter(chapter)
            rows.extend(chapter_rows)
            status_rows.append(status)
            time.sleep(1.25)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_discover_chapter, chapter): chapter
                for chapter in targets
            }
            for future in as_completed(futures):
                chapter = futures[future]
                try:
                    chapter_rows, status = future.result()
                except Exception as error:
                    chapter_rows = []
                    status = _status(
                        chapter,
                        "error",
                        error=f"{type(error).__name__}: {error}",
                    )
                rows.extend(chapter_rows)
                status_rows.append(status)

    rows.sort(key=lambda row: (row["state"], row["chapter"], row["timestamp"], row["url"]))
    status_rows.sort(key=lambda row: (row["state"], row["chapter"]))
    write_csv(
        PROCESSED_DIR / "wayback_endorsement_urls.csv",
        rows,
        [
            "archive_id",
            "chapter_record_id",
            "chapter",
            "state",
            "timestamp",
            "year",
            "url",
            "digest",
            "archive_url",
            "review_status",
        ],
    )
    write_csv(
        PROCESSED_DIR / "wayback_crawl_status.csv",
        status_rows,
        [
            "chapter_record_id",
            "chapter",
            "state",
            "website",
            "crawl_status",
            "matching_urls",
            "crawled_at",
            "error",
        ],
    )
    return len(status_rows), len(rows)


def _discover_chapter(
    chapter: dict[str, str],
) -> tuple[list[dict[str, str]], dict[str, str | int]]:
    website = normalize_url(chapter["Website"])
    host = urllib.parse.urlparse(website).hostname or ""
    query = urllib.parse.urlencode(
        {
            "url": f"{host}/*",
            "output": "json",
            "fl": "timestamp,original,statuscode,digest",
            "filter": "statuscode:200",
            "from": "2016",
            "to": "2026",
            "collapse": "urlkey",
            "limit": "10000",
        }
    )
    url = f"https://web.archive.org/cdx/search/cdx?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    error: Exception | None = None
    payload = None
    for delay in (0, 3, 10):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.load(response)
            break
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as caught:
            error = caught
    if payload is None:
        return [], _status(
            chapter,
            "source_unavailable",
            website=website,
            error=f"{type(error).__name__}: {error}",
        )

    output = []
    for item in payload[1:] if payload else []:
        timestamp, original, _status_code, digest = item
        if not is_historical_candidate_url(original):
            continue
        original = canonical_original_url(original)
        archive_url = f"https://web.archive.org/web/{timestamp}id_/{original}"
        output.append(
            {
                "archive_id": hashlib.sha256(
                    f"{timestamp}\n{original}".encode()
                ).hexdigest()[:24],
                "chapter_record_id": chapter["record_id"],
                "chapter": chapter.get("Name", ""),
                "state": chapter.get("State", ""),
                "timestamp": timestamp,
                "year": infer_election_year(original, timestamp[:4]),
                "url": original,
                "digest": digest,
                "archive_url": archive_url,
                "review_status": "not_searched",
            }
        )
    return output, _status(
        chapter,
        "found_unverified" if output else "searched_not_found",
        website=website,
        matching_urls=len(output),
    )


def filter_existing_wayback_urls() -> tuple[int, int]:
    urls_path = PROCESSED_DIR / "wayback_endorsement_urls.csv"
    status_path = PROCESSED_DIR / "wayback_crawl_status.csv"
    rows = read_csv(urls_path)
    deduplicated: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        if not is_historical_candidate_url(row["url"]):
            continue
        row["url"] = canonical_original_url(row["url"])
        row["year"] = infer_election_year(row["url"], row["timestamp"][:4])
        row["archive_url"] = (
            f'https://web.archive.org/web/{row["timestamp"]}id_/{row["url"]}'
        )
        key = (row["chapter_record_id"], row["url"], row["year"])
        prior = deduplicated.get(key)
        if prior is None or row["timestamp"] > prior["timestamp"]:
            deduplicated[key] = row
    kept = list(deduplicated.values())
    counts: dict[str, int] = {}
    for row in kept:
        counts[row["chapter_record_id"]] = counts.get(row["chapter_record_id"], 0) + 1
    statuses = read_csv(status_path)
    for row in statuses:
        if row["crawl_status"] == "source_unavailable":
            continue
        count = counts.get(row["chapter_record_id"], 0)
        row["matching_urls"] = str(count)
        row["crawl_status"] = "found_unverified" if count else "searched_not_found"
    write_csv(
        urls_path,
        kept,
        [
            "archive_id",
            "chapter_record_id",
            "chapter",
            "state",
            "timestamp",
            "year",
            "url",
            "digest",
            "archive_url",
            "review_status",
        ],
    )
    write_csv(
        status_path,
        statuses,
        [
            "chapter_record_id",
            "chapter",
            "state",
            "website",
            "crawl_status",
            "matching_urls",
            "crawled_at",
            "error",
        ],
    )
    return len(rows), len(kept)


def is_historical_candidate_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path).lower()
    if any(part in path for part in EXCLUDED_PATH_PARTS):
        return False
    if path.endswith(EXCLUDED_SUFFIXES):
        return False
    if "tribe-bar-date=" in parsed.query.lower():
        return False
    if any(prefix in path for prefix in ("/event/", "/events/")) and any(
        term in path
        for term in (
            "endorsement-forum",
            "endorsement-qa",
            "endorsement-process",
            "endorsement-meeting",
            "candidate-forum",
        )
    ):
        return False
    if any(term in path for term in STRONG_HISTORICAL_TERMS):
        return True
    if "candidate" in path:
        return not any(
            value in path
            for value in (
                "call-for-candidates",
                "candidate-forum",
                "internal-election",
                "delegates",
            )
        )
    if any(term in path for term in ("electoral", "election")):
        return not any(
            value in path
            for value in (
                "/event/",
                "/events/",
                "/series/",
                "/calendar/",
                "/feed",
                "/embed",
                "working-group",
                "committee-meeting",
            )
        )
    return False


def canonical_original_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    path = re.sub(r"/(?:amp|embed)/?$", "/", parsed.path, flags=re.IGNORECASE)
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, path, "", "", "")
    )


def infer_election_year(url: str, capture_year: str) -> str:
    path = urllib.parse.urlparse(url).path
    matches = re.findall(r"/(201[6-9]|202[0-6])(?:/|[-_])", path)
    return matches[0] if matches else capture_year


def _status(
    chapter: dict[str, str],
    crawl_status: str,
    *,
    website: str = "",
    matching_urls: int = 0,
    error: str = "",
) -> dict[str, str | int]:
    return {
        "chapter_record_id": chapter["record_id"],
        "chapter": chapter.get("Name", ""),
        "state": chapter.get("State", ""),
        "website": website or chapter.get("Website", ""),
        "crawl_status": crawl_status,
        "matching_urls": matching_urls,
        "crawled_at": datetime.now(UTC).isoformat(),
        "error": error,
    }
