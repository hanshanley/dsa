import csv
import hashlib
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

from .chapter_crawler import is_endorsement_page, parse_html
from .io import read_csv, write_csv
from .paths import PROCESSED_DIR

USER_AGENT = "dsa-analysis/0.1 (+public archived endorsement research)"


def fetch_archived_pages(limit: int = 500, workers: int = 4) -> tuple[int, int, int]:
    source = read_csv(PROCESSED_DIR / "wayback_endorsement_urls.csv")
    pages_path = PROCESSED_DIR / "archived_endorsement_pages.csv"
    status_path = PROCESSED_DIR / "archive_page_status.csv"
    pages = read_csv(pages_path) if pages_path.exists() else []
    statuses = read_csv(status_path) if status_path.exists() else []
    for row in statuses:
        row["attempt_count"] = row.get("attempt_count", "") or "1"
        if row["fetch_status"] == "source_unavailable" and _is_transient_error(row["error"]):
            row["fetch_status"] = "fetch_error"
    statuses_by_id = {row["archive_id"]: row for row in statuses}
    completed = {
        row["archive_id"]
        for row in statuses
        if row["fetch_status"] != "fetch_error"
        or int(row["attempt_count"]) >= 3
    }
    targets = sorted(
        (row for row in source if row["archive_id"] not in completed),
        key=lambda row: (
            int(statuses_by_id.get(row["archive_id"], {}).get("attempt_count", "0")),
            statuses_by_id.get(row["archive_id"], {}).get("retrieved_at", ""),
            row["archive_id"],
        ),
    )[:limit]
    new_pages = []
    new_statuses = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_fetch_one, row): row for row in targets}
        for future in as_completed(futures):
            page, status = future.result()
            status["attempt_count"] = str(
                int(statuses_by_id.get(status["archive_id"], {}).get("attempt_count", "0"))
                + 1
            )
            new_statuses.append(status)
            if page:
                new_pages.append(page)
    pages_by_id = {row["archive_id"]: row for row in pages}
    pages_by_id.update({row["archive_id"]: row for row in new_pages})
    write_csv(
        pages_path,
        sorted(pages_by_id.values(), key=lambda row: row["archive_id"]),
        [
            "page_id",
            "archive_id",
            "chapter_record_id",
            "chapter",
            "state",
            "website",
            "page_url",
            "original_url",
            "title",
            "published_date",
            "capture_year",
            "discovery_method",
            "retrieved_at",
            "sha256",
            "verification_status",
            "text_excerpt",
        ],
    )
    statuses_by_id.update({row["archive_id"]: row for row in new_statuses})
    write_csv(
        status_path,
        sorted(statuses_by_id.values(), key=lambda row: row["archive_id"]),
        [
            "archive_id",
            "chapter_record_id",
            "chapter",
            "state",
            "archive_url",
            "fetch_status",
            "attempt_count",
            "retrieved_at",
            "error",
        ],
    )
    return len(targets), len(new_pages), len(source) - len(completed) - len(targets)


def _fetch_one(
    row: dict[str, str],
) -> tuple[dict[str, str] | None, dict[str, str]]:
    retrieved_at = datetime.now(UTC).isoformat()
    request = urllib.request.Request(
        row["archive_url"],
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.5"},
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=45,
            context=ssl.create_default_context(),
        ) as response:
            body = response.read(2_000_000)
            content_type = response.headers.get_content_type()
            if not content_type.startswith("text/html"):
                return None, _status(
                    row,
                    "source_unavailable",
                    retrieved_at,
                    f"unsupported content type: {content_type}",
                )
            html = body.decode(response.headers.get_content_charset() or "utf-8", "replace")
            parser = parse_html(html)
            text = " ".join(parser.text)
            title = " ".join(parser.title)
            if not is_endorsement_page(title, text):
                return None, _status(row, "searched_not_found", retrieved_at, "")
            page_url = response.geturl()
            page = {
                "page_id": hashlib.sha256(page_url.encode()).hexdigest()[:20],
                "archive_id": row["archive_id"],
                "chapter_record_id": row["chapter_record_id"],
                "chapter": row["chapter"],
                "state": row["state"],
                "website": "",
                "page_url": page_url,
                "original_url": row["url"],
                "title": title,
                "published_date": parser.published_date[:10],
                "capture_year": row["year"],
                "discovery_method": "wayback",
                "retrieved_at": retrieved_at,
                "sha256": hashlib.sha256(body).hexdigest(),
                "verification_status": "found_unverified",
                "text_excerpt": text[:10000],
            }
            return page, _status(row, "found_unverified", retrieved_at, "")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        return None, _status(
            row,
            "fetch_error" if _is_transient_error(str(error)) else "source_unavailable",
            retrieved_at,
            f"{type(error).__name__}: {error}",
        )


def _is_transient_error(error: str) -> bool:
    lowered = error.casefold()
    return any(
        marker in lowered
        for marker in (
            "connection refused",
            "connection reset",
            "remote end closed",
            "temporarily unavailable",
            "timed out",
            "timeout",
            "http error 429",
            "http error 500",
            "http error 502",
            "http error 503",
            "http error 504",
        )
    )


def _status(
    row: dict[str, str],
    fetch_status: str,
    retrieved_at: str,
    error: str,
) -> dict[str, str]:
    return {
        "archive_id": row["archive_id"],
        "chapter_record_id": row["chapter_record_id"],
        "chapter": row["chapter"],
        "state": row["state"],
        "archive_url": row["archive_url"],
        "fetch_status": fetch_status,
        "retrieved_at": retrieved_at,
        "error": error,
    }
