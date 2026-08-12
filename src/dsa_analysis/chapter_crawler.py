import hashlib
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any

from .io import read_csv, write_csv
from .paths import PROCESSED_DIR

USER_AGENT = "dsa-analysis/0.1 (+public-source endorsement research)"
DISCOVERY_TERMS = ("endor", "elect", "candidate", "voter-guide", "slate")
MATCH_TERMS = (
    "endorse",
    "endorsement",
    "endorsed",
    "electoral slate",
    "candidate slate",
    "voter guide",
)


@dataclass(frozen=True)
class CrawlResult:
    status: dict[str, Any]
    pages: tuple[dict[str, Any], ...]


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.text: list[str] = []
        self.title: list[str] = []
        self.published_date = ""
        self._ignored_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])
        if tag == "meta":
            property_name = attributes.get("property") or attributes.get("name")
            if property_name in {
                "article:published_time",
                "date",
                "datePublished",
                "publish_date",
            }:
                self.published_date = attributes.get("content", "")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        normalized = " ".join(data.split())
        if not normalized or self._ignored_depth:
            return
        self.text.append(normalized)
        if self._in_title:
            self.title.append(normalized)


def crawl_all_chapters(workers: int = 12, pages_per_site: int = 40) -> tuple[int, int]:
    chapters = read_csv(PROCESSED_DIR / "chapter_directory.csv")
    results: list[CrawlResult] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_crawl_chapter, chapter, pages_per_site): chapter
            for chapter in chapters
        }
        for future in as_completed(futures):
            chapter = futures[future]
            try:
                results.append(future.result())
            except Exception as error:
                results.append(
                    CrawlResult(
                        status=_status_row(
                            chapter,
                            "error",
                            error=f"{type(error).__name__}: {error}",
                        ),
                        pages=(),
                    )
                )

    statuses = sorted(
        (result.status for result in results),
        key=lambda row: (row["state"], row["chapter"]),
    )
    pages = sorted(
        (page for result in results for page in result.pages),
        key=lambda row: (row["state"], row["chapter"], row["page_url"]),
    )
    write_csv(
        PROCESSED_DIR / "chapter_crawl_status.csv",
        statuses,
        [
            "chapter_record_id",
            "chapter",
            "state",
            "chapter_status",
            "website",
            "crawl_status",
            "urls_discovered",
            "pages_checked",
            "endorsement_pages_found",
            "crawled_at",
            "error",
        ],
    )
    write_csv(
        PROCESSED_DIR / "local_endorsement_pages.csv",
        pages,
        [
            "page_id",
            "chapter_record_id",
            "chapter",
            "state",
            "chapter_status",
            "website",
            "page_url",
            "title",
            "published_date",
            "discovery_method",
            "retrieved_at",
            "sha256",
            "verification_status",
            "text_excerpt",
        ],
    )
    return len(statuses), len(pages)


def _crawl_chapter(chapter: dict[str, str], pages_per_site: int) -> CrawlResult:
    source_value = (
        chapter.get("Website", "").strip()
        or chapter.get("Blog", "").strip()
        or chapter.get("Linktree", "").strip()
    )
    website = normalize_url(source_value)
    if not website:
        return CrawlResult(
            status=_status_row(chapter, "source_unavailable"),
            pages=(),
        )

    discovered: dict[str, str] = {}
    homepage_page: dict[str, Any] | None = None
    checked = 0
    errors: list[str] = []
    homepage = _fetch(website)
    checked += 1
    if homepage["ok"] and homepage["text"]:
        parser = parse_html(homepage["text"])
        homepage_text = " ".join(parser.text)
        homepage_title = " ".join(parser.title)
        if is_endorsement_page(homepage_title, homepage_text):
            homepage_page = _page_row(
                chapter,
                website,
                homepage["final_url"] or website,
                homepage_title,
                parser.published_date,
                "homepage",
                homepage["retrieved_at"],
                homepage["body"],
                homepage_text,
            )
        for link in parser.links:
            normalized = _same_site_url(website, link)
            if normalized and has_discovery_term(normalized):
                discovered.setdefault(normalized, "homepage")
    elif homepage["error"]:
        errors.append(homepage["error"])

    for path, method in (
        ("/wp-json/wp/v2/search?search=endorsement&per_page=100", "wordpress"),
        ("/wp-json/wp/v2/search?search=endorsed&per_page=100", "wordpress"),
        ("/wp-json/wp/v2/search?search=election&per_page=100", "wordpress"),
        ("/wp-sitemap.xml", "sitemap"),
        ("/sitemap.xml", "sitemap"),
        ("/post-sitemap.xml", "sitemap"),
        ("/page-sitemap.xml", "sitemap"),
    ):
        result = _fetch(urllib.parse.urljoin(website, path))
        checked += 1
        if not result["ok"]:
            continue
        if method == "wordpress":
            for url in parse_wordpress_search(result["text"]):
                discovered.setdefault(url, method)
        else:
            for url in parse_sitemap(result["text"]):
                if has_discovery_term(url):
                    discovered.setdefault(url, method)

    pages: list[dict[str, Any]] = [homepage_page] if homepage_page else []
    for url, method in list(discovered.items())[:pages_per_site]:
        result = _fetch(url)
        checked += 1
        if not result["ok"] or not result["text"]:
            continue
        parser = parse_html(result["text"])
        text = " ".join(parser.text)
        title = " ".join(parser.title)
        if not is_endorsement_page(title, text):
            continue
        page_url = result["final_url"] or url
        pages.append(
            _page_row(
                chapter,
                website,
                page_url,
                title,
                parser.published_date,
                method,
                result["retrieved_at"],
                result["body"],
                text,
            )
        )

    pages = list({page["page_id"]: page for page in pages}.values())
    crawl_status = "searched_not_found" if not pages else "found_unverified"
    if not homepage["ok"] and not discovered:
        crawl_status = "source_unavailable"
    return CrawlResult(
        status=_status_row(
            chapter,
            crawl_status,
            website=website,
            urls_discovered=len(discovered),
            pages_checked=checked,
            endorsement_pages_found=len(pages),
            error=" | ".join(errors),
        ),
        pages=tuple(pages),
    )


def normalize_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if not re.match(r"^https?://", value, flags=re.IGNORECASE):
        value = f"https://{value}"
    parsed = urllib.parse.urlparse(value)
    if not parsed.hostname:
        return ""
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path or "/", "", "", "")
    )


def has_discovery_term(value: str) -> bool:
    lowered = value.lower()
    return any(term in lowered for term in DISCOVERY_TERMS)


def is_endorsement_page(title: str, text: str) -> bool:
    sample = f"{title} {text[:6000]}".lower()
    return any(term in sample for term in MATCH_TERMS)


def parse_html(value: str) -> PageParser:
    parser = PageParser()
    parser.feed(value)
    return parser


def parse_wordpress_search(value: str) -> list[str]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [
        item["url"]
        for item in payload
        if isinstance(item, dict) and isinstance(item.get("url"), str)
    ]


def parse_sitemap(value: str) -> list[str]:
    return [
        urllib.parse.unquote(match)
        for match in re.findall(r"<loc>\s*(.*?)\s*</loc>", value, flags=re.IGNORECASE)
    ]


def _same_site_url(base: str, link: str) -> str:
    url = urllib.parse.urljoin(base, link)
    base_host = (urllib.parse.urlparse(base).hostname or "").removeprefix("www.")
    url_host = (urllib.parse.urlparse(url).hostname or "").removeprefix("www.")
    if not url_host or url_host != base_host:
        return ""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, "")
    )


def _fetch(url: str) -> dict[str, Any]:
    retrieved_at = datetime.now(UTC).isoformat()
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json,application/xml,text/xml;q=0.9,*/*;q=0.1",
        },
    )
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=15, context=context) as response:
            body = response.read(2_000_000)
            content_type = response.headers.get_content_type()
            text = ""
            if content_type.startswith("text/") or content_type in {
                "application/json",
                "application/xml",
            }:
                text = body.decode(response.headers.get_content_charset() or "utf-8", "replace")
            return {
                "ok": True,
                "body": body,
                "text": text,
                "final_url": response.geturl(),
                "retrieved_at": retrieved_at,
                "error": "",
            }
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        return {
            "ok": False,
            "body": b"",
            "text": "",
            "final_url": "",
            "retrieved_at": retrieved_at,
            "error": f"{type(error).__name__}: {error}",
        }


def _status_row(
    chapter: dict[str, str],
    crawl_status: str,
    *,
    website: str = "",
    urls_discovered: int = 0,
    pages_checked: int = 0,
    endorsement_pages_found: int = 0,
    error: str = "",
) -> dict[str, Any]:
    return {
        "chapter_record_id": chapter["record_id"],
        "chapter": chapter.get("Name", ""),
        "state": chapter.get("State", ""),
        "chapter_status": chapter.get("Status", ""),
        "website": website or chapter.get("Website", ""),
        "crawl_status": crawl_status,
        "urls_discovered": urls_discovered,
        "pages_checked": pages_checked,
        "endorsement_pages_found": endorsement_pages_found,
        "crawled_at": datetime.now(UTC).isoformat(),
        "error": error,
    }


def _page_row(
    chapter: dict[str, str],
    website: str,
    page_url: str,
    title: str,
    published_date: str,
    discovery_method: str,
    retrieved_at: str,
    body: bytes,
    text: str,
) -> dict[str, Any]:
    return {
        "page_id": hashlib.sha256(page_url.encode()).hexdigest()[:20],
        "chapter_record_id": chapter["record_id"],
        "chapter": chapter.get("Name", ""),
        "state": chapter.get("State", ""),
        "chapter_status": chapter.get("Status", ""),
        "website": website,
        "page_url": page_url,
        "title": title,
        "published_date": published_date[:10],
        "discovery_method": discovery_method,
        "retrieved_at": retrieved_at,
        "sha256": hashlib.sha256(body).hexdigest(),
        "verification_status": "found_unverified",
        "text_excerpt": text[:8000],
    }
