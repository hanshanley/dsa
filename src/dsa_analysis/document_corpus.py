import base64
import hashlib
import http.client
import importlib
import json
import mimetypes
import platform
import re
import subprocess
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import urlparse, urlunparse

from .io import read_csv, write_csv
from .paths import PROCESSED_DIR, RAW_DIR, ROOT

USER_AGENT = "dsa-analysis/0.1 (+candidate document corpus)"
COVERAGE_STATUSES = {
    "not_searched",
    "searched_not_found",
    "source_unavailable",
    "found_unverified",
    "verified",
    "media_no_transcript",
    "shared_document_unscoped",
}
BLOCK_TAGS = {
    "article",
    "blockquote",
    "dd",
    "div",
    "dl",
    "dt",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}
IGNORED_TAGS = {"script", "style", "noscript", "svg"}
COMMON_ABBREVIATIONS = {
    "dr.",
    "e.g.",
    "i.e.",
    "jr.",
    "mr.",
    "mrs.",
    "ms.",
    "no.",
    "prof.",
    "sr.",
    "st.",
    "u.k.",
    "u.s.",
    "vs.",
}
MEDIA_SUFFIXES = {
    ".aac",
    ".avi",
    ".m4a",
    ".mov",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".oga",
    ".ogg",
    ".ogv",
    ".wav",
    ".webm",
}
PDF_TYPES = {"application/pdf", "application/x-pdf"}
TEXT_TYPES = {"text/plain"}
SRT_TYPES = {"application/x-subrip", "text/srt"}
HTML_TYPES = {"text/html", "application/xhtml+xml"}
OPENING_SENTENCE_CHARS = {'"', "'", "“", "‘", "(", "["}
TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "ref_url",
    "utm_campaign",
    "utm_content",
    "utm_id",
    "utm_medium",
    "utm_name",
    "utm_source",
    "utm_term",
    "share",
}
SOCIAL_HOSTS = {
    "bsky.app",
    "facebook.com",
    "instagram.com",
    "linktr.ee",
    "threads.net",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "youtu.be",
}
NON_CAMPAIGN_HOSTS = {
    "archive.org",
    "docs.google.com",
    "drive.google.com",
    "vimeo.com",
    "web.archive.org",
    *SOCIAL_HOSTS,
}
VIDEO_HOSTS = {"vimeo.com", "youtube.com", "youtu.be"}
CAMPAIGN_DOMAIN_SOURCE_TERMS = (
    "official_campaign",
    "campaign_announcement",
    "campaign_issue",
    "campaign_page",
    "campaign_platform",
    "campaign_policy",
    "campaign_press_release",
    "campaign_release",
    "campaign_site",
    "campaign_speech",
    "campaign_statement",
    "campaign_website",
)
NON_GENUINE_CAMPAIGN_DOMAIN_TERMS = (
    "ballot",
    "election",
    "guide",
    "questionnaire",
    "survey",
    "vote",
    "voter",
)
SOURCE_TYPE_CLASS_PRIORITY = {
    "campaign_page": 0,
    "policy_page": 0,
    "press_release": 1,
    "statement": 1,
    "campaign_material": 2,
    "social_post": 3,
    "video": 4,
    "questionnaire": 5,
    "voter_guide": 6,
    "interview": 7,
    "debate": 7,
    "forum": 7,
    "speech": 7,
    "filing": 8,
    "profile_or_op_ed": 9,
    "other": 10,
    "search_log": 11,
}
QUEUE_SEED_PRIORITY = {
    "campaign_domain": 1,
    "known_document": 2,
    "official_election_source": 3,
    "campaign_live_discovery": 4,
    "campaign_archive_discovery": 4,
}
FETCH_STATUSES = {"fetched", "reused_raw", "fetch_error", "metadata_error"}
EXTRACTION_STATUSES = {
    "extracted",
    "media_no_transcript",
    "shared_document_unscoped",
    "extraction_error",
    "metadata_error",
    "not_attempted",
}
REGATHER_PRIORITY_SOURCE_TYPE_CLASSES = (
    "campaign_page",
    "policy_page",
    "speech",
    "press_release",
    "questionnaire",
    "interview",
    "debate",
)
BOILERPLATE_PHRASES = {
    "all rights reserved",
    "cookie policy",
    "paid for by",
    "privacy policy",
    "terms of service",
    "unsubscribe",
}
ANALYSIS_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "this",
    "to",
    "we",
    "with",
    "you",
    "your",
}
DISCOVERY_PATH_HINTS = (
    "agenda",
    "announcement",
    "issue",
    "issues",
    "news",
    "platform",
    "policies",
    "policy",
    "press",
    "priorities",
    "qa",
    "questionnaire",
    "questionnaires",
    "release",
    "releases",
    "remarks",
    "speech",
    "speeches",
    "statement",
    "statements",
)
DISCOVERY_HTML_KEYWORDS = (
    "issues",
    "platform",
    "policy",
    "policies",
    "agenda",
    "priorities",
    "news",
    "press",
    "release",
    "statement",
    "speech",
    "questionnaire",
    "questionnaires",
    "qa",
    "q&a",
)
DISCOVERY_SITEMAP_PATHS = (
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/wp-sitemap.xml",
)
DISCOVERY_FEED_PATHS = ("/feed", "/rss.xml", "/atom.xml")
DISCOVERY_COMPLETED_STATUSES = {"complete", "skipped_non_campaign_domain"}
DISCOVERY_CANDIDATE_SOURCE_TYPES = {
    "campaign_page",
    "policy_page",
    "press_release",
    "statement",
    "speech",
    "questionnaire",
}


class DocumentCorpusError(ValueError):
    """Raised when candidate-document corpus inputs are invalid."""


class RawFetchError(DocumentCorpusError):
    """Raised when raw content cannot be retrieved."""


class ExtractionError(DocumentCorpusError):
    """Raised when fetched content cannot be converted into reviewable text."""


@dataclass(frozen=True)
class CampaignWindow:
    start: date
    end: date

    def contains(self, value: date) -> bool:
        return self.start <= value <= self.end


@dataclass(frozen=True)
class RawDocumentCapture:
    document_id: str
    source_url: str
    final_url: str
    retrieved_at: str
    content_type: str
    encoding: str
    content_bytes: bytes
    byte_count: int
    sha256: str

    @property
    def suffix(self) -> str:
        return _suffix(self.final_url or self.source_url, self.content_type)


@dataclass(frozen=True)
class TextSegment:
    segment_id: str
    document_id: str
    segment_kind: str
    index: int
    locator: str
    text: str
    sha256: str

    def as_row(self) -> dict[str, str]:
        return {
            "segment_id": self.segment_id,
            "document_id": self.document_id,
            "segment_kind": self.segment_kind,
            "index": str(self.index),
            "locator": self.locator,
            "text": self.text,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class ExtractedDocument:
    document_id: str
    source_url: str
    final_url: str
    retrieved_at: str
    content_type: str
    title: str
    text: str
    text_sha256: str
    coverage_status: str
    extractor: str
    paragraphs: tuple[TextSegment, ...]
    sentences: tuple[TextSegment, ...]


@dataclass(frozen=True)
class AnalysisSegmentConfig:
    min_tokens: int = 20
    max_tokens: int = 80
    near_duplicate_min_tokens: int = 6
    review_sample_size: int = 24

    def __post_init__(self) -> None:
        if self.min_tokens < 1:
            raise DocumentCorpusError("analysis min_tokens must be positive")
        if self.max_tokens < self.min_tokens:
            raise DocumentCorpusError("analysis max_tokens must be >= min_tokens")
        if self.near_duplicate_min_tokens < 1:
            raise DocumentCorpusError("near_duplicate_min_tokens must be positive")
        if self.review_sample_size < 1:
            raise DocumentCorpusError("review_sample_size must be positive")


@dataclass(frozen=True)
class AnalysisSegment:
    analysis_segment_id: str
    document_id: str
    candidate_slug: str
    candidate_name: str
    race_id: str
    role: str
    source_type: str
    segment_index: int
    analysis_kind: str
    locator: str
    source_locator_start: str
    source_locator_end: str
    paragraph_start: int
    paragraph_end: int
    sentence_start: int
    sentence_end: int
    text: str
    token_count: int
    sha256: str
    exact_duplicate_hash: str
    exact_duplicate_count: int
    exact_duplicate_flag: bool
    near_duplicate_hash: str
    near_duplicate_count: int
    near_duplicate_flag: bool
    boilerplate_flag: bool
    boilerplate_reasons: str

    def as_row(self) -> dict[str, str]:
        return {
            "analysis_segment_id": self.analysis_segment_id,
            "document_id": self.document_id,
            "candidate_slug": self.candidate_slug,
            "candidate_name": self.candidate_name,
            "race_id": self.race_id,
            "role": self.role,
            "source_type": self.source_type,
            "segment_index": str(self.segment_index),
            "analysis_kind": self.analysis_kind,
            "locator": self.locator,
            "source_locator_start": self.source_locator_start,
            "source_locator_end": self.source_locator_end,
            "paragraph_start": str(self.paragraph_start),
            "paragraph_end": str(self.paragraph_end),
            "sentence_start": str(self.sentence_start),
            "sentence_end": str(self.sentence_end),
            "text": self.text,
            "token_count": str(self.token_count),
            "sha256": self.sha256,
            "exact_duplicate_hash": self.exact_duplicate_hash,
            "exact_duplicate_count": str(self.exact_duplicate_count),
            "exact_duplicate_flag": str(self.exact_duplicate_flag).lower(),
            "near_duplicate_hash": self.near_duplicate_hash,
            "near_duplicate_count": str(self.near_duplicate_count),
            "near_duplicate_flag": str(self.near_duplicate_flag).lower(),
            "boilerplate_flag": str(self.boilerplate_flag).lower(),
            "boilerplate_reasons": self.boilerplate_reasons,
        }


@dataclass(frozen=True)
class CandidateDocumentMetadata:
    document_id: str
    candidate_slug: str
    candidate_name: str
    race_id: str
    election_date: str
    publication_date: str
    campaign_window_start: str
    campaign_window_end: str
    campaign_window_status: str
    source_type: str
    source_url: str
    archive_url: str
    final_url: str
    retrieved_at: str
    content_type: str
    title: str
    coverage_status: str
    raw_sha256: str
    text_sha256: str
    provenance_hash: str
    paragraph_count: int
    sentence_count: int
    raw_path: str

    def as_row(self) -> dict[str, str]:
        return {
            "document_id": self.document_id,
            "candidate_slug": self.candidate_slug,
            "candidate_name": self.candidate_name,
            "race_id": self.race_id,
            "election_date": self.election_date,
            "publication_date": self.publication_date,
            "campaign_window_start": self.campaign_window_start,
            "campaign_window_end": self.campaign_window_end,
            "campaign_window_status": self.campaign_window_status,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "archive_url": self.archive_url,
            "final_url": self.final_url,
            "retrieved_at": self.retrieved_at,
            "content_type": self.content_type,
            "title": self.title,
            "coverage_status": self.coverage_status,
            "raw_sha256": self.raw_sha256,
            "text_sha256": self.text_sha256,
            "provenance_hash": self.provenance_hash,
            "paragraph_count": str(self.paragraph_count),
            "sentence_count": str(self.sentence_count),
            "raw_path": self.raw_path,
        }


@dataclass(frozen=True)
class CandidateDocumentJob:
    document_id: str
    queue_id: str
    race_id: str
    candidate_name: str
    role: str
    election_date: str
    publication_date: str
    source_type: str
    source_url: str
    archive_url: str
    notes: str
    seed_kind: str
    source_record_id: str
    legacy_locators: str
    analysis_scope: str
    transcript_text: str
    transcript_title: str


@dataclass(frozen=True)
class CandidateDocumentBatchPaths:
    queue_path: Path
    raw_dir: Path
    raw_manifest_path: Path
    metadata_path: Path
    full_text_path: Path
    paragraph_path: Path
    sentence_path: Path
    analysis_segment_path: Path

    @classmethod
    def default(cls) -> "CandidateDocumentBatchPaths":
        return cls(
            queue_path=PROCESSED_DIR / "candidate_document_queue.csv",
            raw_dir=RAW_DIR / "candidate_documents",
            raw_manifest_path=PROCESSED_DIR / "candidate_document_raw_manifest.jsonl",
            metadata_path=PROCESSED_DIR / "candidate_document_metadata.csv",
            full_text_path=PROCESSED_DIR / "candidate_document_full_text.jsonl",
            paragraph_path=PROCESSED_DIR / "candidate_document_paragraphs.csv",
            sentence_path=PROCESSED_DIR / "candidate_document_sentences.csv",
            analysis_segment_path=PROCESSED_DIR / "candidate_document_analysis_segments.csv",
        )


@dataclass(frozen=True)
class CandidateDocumentBatchResult:
    queued_documents: int
    processed_documents: int
    successful_documents: int
    fetched_documents: int
    reused_raw_documents: int
    metadata_errors: int
    fetch_errors: int
    extraction_errors: int
    media_without_transcript: int
    raw_manifest_path: Path
    metadata_path: Path
    full_text_path: Path
    paragraph_path: Path
    sentence_path: Path
    analysis_segment_path: Path


@dataclass(frozen=True)
class CandidateDocumentRegatherPlan:
    queue_rows: tuple[dict[str, str], ...]
    selected_unique_urls: int
    pending_documents: int
    pending_unique_urls: int
    skipped_completed_documents: int
    skipped_transcriptless_video_documents: int


@dataclass(frozen=True)
class CandidateDocumentRegatherResult:
    limit: int | None
    output_queue_path: Path | None
    plan: CandidateDocumentRegatherPlan
    batch_result: CandidateDocumentBatchResult


@dataclass(frozen=True)
class CampaignDomainDiscoveryPaths:
    queue_path: Path
    status_path: Path
    discovered_url_path: Path

    @classmethod
    def default(cls) -> "CampaignDomainDiscoveryPaths":
        return cls(
            queue_path=PROCESSED_DIR / "candidate_document_queue.csv",
            status_path=PROCESSED_DIR / "candidate_campaign_domain_discovery_status.csv",
            discovered_url_path=PROCESSED_DIR
            / "candidate_campaign_domain_discovered_urls.csv",
        )


@dataclass(frozen=True)
class CampaignDomainDiscoveryResult:
    queued_domains: int
    searched_domains: int
    appended_queue_rows: int
    discovered_urls: int
    remaining_domains: int
    status_path: Path
    discovered_url_path: Path
    queue_path: Path


@dataclass
class _RawManifestIndex:
    by_document_id: dict[str, dict[str, str]]
    by_canonical_url: dict[str, dict[str, str]]


def stable_hash(*parts: str, length: int = 24) -> str:
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest[:length]


def candidate_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    lowered = normalized.casefold()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered)
    return collapsed.strip("-")


def normalize_source_url(value: str) -> str:
    value = value.strip()
    if not value:
        raise DocumentCorpusError("source_url is required")
    if re.search(r"[\x00-\x20|]", value):
        raise DocumentCorpusError(f"invalid source_url: {value}")
    if re.match(r"^https?:/(?!/)", value, flags=re.IGNORECASE):
        raise DocumentCorpusError(f"invalid source_url: {value}")
    if not re.match(r"^https?://", value, flags=re.IGNORECASE):
        value = f"https://{value}"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise DocumentCorpusError(f"invalid source_url: {value}")
    path = parsed.path or "/"
    if parsed.netloc.casefold() != "web.archive.org":
        path = re.sub(r"/{2,}", "/", path)
    return urlunparse(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            path,
            "",
            parsed.query,
            "",
        )
    )


def candidate_document_id(
    candidate_name: str,
    race_id: str,
    source_url: str,
    source_type: str,
) -> str:
    return stable_hash(
        candidate_slug(candidate_name),
        race_id.strip(),
        canonical_source_url(source_url),
        source_type.strip().casefold(),
    )


def campaign_window_for_election(value: date | str) -> CampaignWindow:
    election_date = _coerce_date(value)
    return CampaignWindow(
        start=date(election_date.year - 1, 1, 1),
        end=election_date,
    )


def classify_campaign_window(
    election_date: date | str,
    publication_date: date | str | None,
) -> str:
    if publication_date in {None, ""}:
        return "undated"
    window = campaign_window_for_election(election_date)
    published = _coerce_date(publication_date)
    return "in_window" if window.contains(published) else "out_of_window"


def fetch_raw_document(
    document_id: str,
    source_url: str,
    *,
    user_agent: str = USER_AGENT,
    timeout: int = 45,
) -> RawDocumentCapture:
    if not document_id.strip():
        raise DocumentCorpusError("document_id is required")
    normalized_url = normalize_source_url(source_url)
    retrieved_at = datetime.now(UTC).isoformat()
    request = urllib.request.Request(
        normalized_url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,text/plain,application/pdf;q=0.9,*/*;q=0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content = response.read()
            final_url = normalize_source_url(response.geturl())
            content_type = response.headers.get_content_type()
            encoding = response.headers.get_content_charset() or "utf-8"
    except (
        urllib.error.URLError,
        http.client.InvalidURL,
        TimeoutError,
        OSError,
        ValueError,
    ) as error:
        raise RawFetchError(
            f"failed to fetch {normalized_url}: {type(error).__name__}: {error}"
        ) from error
    return RawDocumentCapture(
        document_id=document_id,
        source_url=normalized_url,
        final_url=final_url,
        retrieved_at=retrieved_at,
        content_type=content_type,
        encoding=encoding,
        content_bytes=content,
        byte_count=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )


def persist_raw_document(
    capture: RawDocumentCapture,
    raw_dir: Path = RAW_DIR / "candidate_documents",
) -> Path:
    document_dir = raw_dir / capture.document_id
    document_dir.mkdir(parents=True, exist_ok=True)
    path = document_dir / f"{capture.sha256}{capture.suffix}"
    if not path.exists():
        path.write_bytes(capture.content_bytes)
    return path


def extract_document_text(capture: RawDocumentCapture) -> ExtractedDocument:
    extractor = _extractor_name(capture)
    if extractor == "media_no_transcript":
        return ExtractedDocument(
            document_id=capture.document_id,
            source_url=capture.source_url,
            final_url=capture.final_url,
            retrieved_at=capture.retrieved_at,
            content_type=capture.content_type,
            title="",
            text="",
            text_sha256=_sha256_text(""),
            coverage_status="media_no_transcript",
            extractor=extractor,
            paragraphs=(),
            sentences=(),
        )
    if extractor == "pdf":
        title, text = _extract_pdf_text(capture.content_bytes)
        paragraph_segments, sentence_segments = segment_document(capture.document_id, text)
        normalized_text = "\n\n".join(segment.text for segment in paragraph_segments)
    elif extractor == "srt":
        title, normalized_text, paragraph_segments, sentence_segments = _extract_srt_text(capture)
    elif extractor == "html":
        title, text = _extract_html_text(capture)
        paragraph_segments, sentence_segments = segment_document(capture.document_id, text)
        normalized_text = "\n\n".join(segment.text for segment in paragraph_segments)
    elif extractor == "plain_text":
        title, text = "", _decode_text(capture.content_bytes, capture.encoding)
        paragraph_segments, sentence_segments = segment_document(capture.document_id, text)
        normalized_text = "\n\n".join(segment.text for segment in paragraph_segments)
    else:
        raise ExtractionError(
            f"{capture.document_id}: unsupported content type {capture.content_type}"
        )
    title = _sanitize_extracted_text(title).strip()
    if not paragraph_segments:
        raise ExtractionError(f"{capture.document_id}: extracted text is empty")
    return ExtractedDocument(
        document_id=capture.document_id,
        source_url=capture.source_url,
        final_url=capture.final_url,
        retrieved_at=capture.retrieved_at,
        content_type=capture.content_type,
        title=title,
        text=normalized_text,
        text_sha256=_sha256_text(normalized_text),
        coverage_status="found_unverified",
        extractor=extractor,
        paragraphs=paragraph_segments,
        sentences=sentence_segments,
    )


def segment_paragraphs(text: str) -> tuple[str, ...]:
    normalized = _sanitize_extracted_text(text).replace("\r\n", "\n").replace("\r", "\n")
    parts = re.split(r"\n\s*\n+", normalized)
    paragraphs = [
        re.sub(r"\s+", " ", part).strip()
        for part in parts
        if re.sub(r"\s+", " ", part).strip()
    ]
    return tuple(paragraphs)


def segment_sentences(text: str) -> tuple[str, ...]:
    sentences: list[str] = []
    for paragraph in segment_paragraphs(text):
        sentences.extend(_split_sentences(paragraph))
    return tuple(sentences)


def segment_document(
    document_id: str,
    text: str,
) -> tuple[tuple[TextSegment, ...], tuple[TextSegment, ...]]:
    paragraph_text = segment_paragraphs(text)
    paragraph_segments = tuple(
        _segment(document_id, "paragraph", index, f"paragraph {index}", value)
        for index, value in enumerate(paragraph_text, start=1)
    )
    sentence_segments: list[TextSegment] = []
    sentence_index = 1
    for paragraph_index, paragraph in enumerate(paragraph_text, start=1):
        for local_index, sentence in enumerate(_split_sentences(paragraph), start=1):
            sentence_segments.append(
                _segment(
                    document_id,
                    "sentence",
                    sentence_index,
                    f"paragraph {paragraph_index} sentence {local_index}",
                    sentence,
                )
            )
            sentence_index += 1
    return paragraph_segments, tuple(sentence_segments)


def build_candidate_document_metadata(
    *,
    candidate_name: str,
    race_id: str,
    election_date: date | str,
    publication_date: date | str | None,
    source_type: str,
    capture: RawDocumentCapture,
    extracted: ExtractedDocument,
    archive_url: str = "",
    raw_path: Path | None = None,
) -> CandidateDocumentMetadata:
    if not candidate_name.strip():
        raise DocumentCorpusError("candidate_name is required")
    if not race_id.strip():
        raise DocumentCorpusError("race_id is required")
    if not source_type.strip():
        raise DocumentCorpusError("source_type is required")
    if capture.document_id != extracted.document_id:
        raise DocumentCorpusError("capture and extracted document_ids do not match")
    election_day = _coerce_date(election_date)
    publication_day = _coerce_optional_date(publication_date)
    campaign_window = campaign_window_for_election(election_day)
    normalized_archive_url = _archive_provenance_url(archive_url, capture.final_url)
    row_path = ""
    if raw_path is not None:
        try:
            row_path = str(raw_path.relative_to(ROOT))
        except ValueError:
            row_path = str(raw_path)
    publication_value = publication_day.isoformat() if publication_day else ""
    provenance_hash = stable_hash(
        capture.document_id,
        capture.sha256,
        extracted.text_sha256,
        capture.final_url,
        publication_value,
        extracted.coverage_status,
        source_type.strip().casefold(),
    )
    return CandidateDocumentMetadata(
        document_id=capture.document_id,
        candidate_slug=candidate_slug(candidate_name),
        candidate_name=candidate_name.strip(),
        race_id=race_id.strip(),
        election_date=election_day.isoformat(),
        publication_date=publication_value,
        campaign_window_start=campaign_window.start.isoformat(),
        campaign_window_end=campaign_window.end.isoformat(),
        campaign_window_status=classify_campaign_window(election_day, publication_day),
        source_type=source_type.strip(),
        source_url=capture.source_url,
        archive_url=normalized_archive_url,
        final_url=capture.final_url,
        retrieved_at=capture.retrieved_at,
        content_type=capture.content_type,
        title=extracted.title,
        coverage_status=extracted.coverage_status,
        raw_sha256=capture.sha256,
        text_sha256=extracted.text_sha256,
        provenance_hash=provenance_hash,
        paragraph_count=len(extracted.paragraphs),
        sentence_count=len(extracted.sentences),
        raw_path=row_path,
    )


def build_candidate_document_regather_plan(
    queue_rows: list[dict[str, str]] | None = None,
    paths: CandidateDocumentBatchPaths | None = None,
    *,
    limit: int | None = None,
    preferred_source_classes: Sequence[str] = REGATHER_PRIORITY_SOURCE_TYPE_CLASSES,
    skip_transcriptless_video: bool = True,
) -> CandidateDocumentRegatherPlan:
    if limit is not None and limit <= 0:
        raise DocumentCorpusError("limit must be positive when provided")
    paths = paths or CandidateDocumentBatchPaths.default()
    if queue_rows is None:
        queue_rows = _load_candidate_document_queue(paths.queue_path)
    metadata_by_document = _load_existing_csv_by_key(paths.metadata_path, "document_id")
    full_text_by_document = _load_existing_jsonl_by_key(paths.full_text_path, "document_id")
    paragraph_counts = Counter(
        row.get("document_id", "")
        for row in (read_csv(paths.paragraph_path) if paths.paragraph_path.exists() else [])
        if row.get("document_id", "")
    )
    sentence_counts = Counter(
        row.get("document_id", "")
        for row in (read_csv(paths.sentence_path) if paths.sentence_path.exists() else [])
        if row.get("document_id", "")
    )
    preferred_classes = {value.strip() for value in preferred_source_classes if value.strip()}
    race_group_support = _regather_race_group_support(queue_rows)

    pending_rows: list[dict[str, str]] = []
    skipped_completed_documents = 0
    skipped_transcriptless_video_documents = 0

    for row in queue_rows:
        normalized_row = _normalized_regather_queue_row(row)
        metadata_row = metadata_by_document.get(normalized_row["document_id"])
        if _is_completed_document_metadata(
            metadata_row,
            full_text_by_document.get(normalized_row["document_id"]),
            paragraph_counts.get(normalized_row["document_id"], 0),
            sentence_counts.get(normalized_row["document_id"], 0),
        ) or (
            metadata_row is None and _is_completed_queue_row(normalized_row)
        ):
            skipped_completed_documents += 1
            continue
        if (
            skip_transcriptless_video
            and _is_transcriptless_video_queue_row(normalized_row)
        ):
            skipped_transcriptless_video_documents += 1
            continue
        pending_rows.append(normalized_row)

    pending_unique_urls = len(
        {
            _regather_group_key(row)
            for row in pending_rows
        }
    )
    grouped_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in pending_rows:
        grouped_rows[_regather_group_key(row)].append(row)

    prioritized_groups = sorted(
        grouped_rows.values(),
        key=lambda rows: _regather_group_sort_key(
            rows,
            preferred_classes=preferred_classes,
            race_group_support=race_group_support,
        ),
    )
    if limit is not None:
        prioritized_groups = prioritized_groups[:limit]
    selected_rows = [
        row
        for rows in prioritized_groups
        for row in sorted(rows, key=_regather_row_sort_key)
    ]
    return CandidateDocumentRegatherPlan(
        queue_rows=tuple(selected_rows),
        selected_unique_urls=len(prioritized_groups),
        pending_documents=len(pending_rows),
        pending_unique_urls=pending_unique_urls,
        skipped_completed_documents=skipped_completed_documents,
        skipped_transcriptless_video_documents=skipped_transcriptless_video_documents,
    )


def run_candidate_document_regather_batch(
    queue_rows: list[dict[str, str]] | None = None,
    paths: CandidateDocumentBatchPaths | None = None,
    *,
    limit: int | None = None,
    fetcher: Callable[[str, str], RawDocumentCapture] | None = None,
    fetch_timeout: int = 20,
    analysis_config: AnalysisSegmentConfig | None = None,
    output_queue_path: Path | None = None,
    preferred_source_classes: Sequence[str] = REGATHER_PRIORITY_SOURCE_TYPE_CLASSES,
    skip_transcriptless_video: bool = True,
) -> CandidateDocumentRegatherResult:
    paths = paths or CandidateDocumentBatchPaths.default()
    plan = build_candidate_document_regather_plan(
        queue_rows=queue_rows,
        paths=paths,
        limit=limit,
        preferred_source_classes=preferred_source_classes,
        skip_transcriptless_video=skip_transcriptless_video,
    )
    if output_queue_path is not None:
        _write_candidate_document_queue(output_queue_path, plan.queue_rows)
    effective_fetcher = fetcher or (
        lambda document_id, source_url: fetch_raw_document(
            document_id,
            source_url,
            timeout=fetch_timeout,
        )
    )
    batch_result = run_candidate_document_extraction_batch(
        list(plan.queue_rows),
        paths,
        fetcher=effective_fetcher,
        analysis_config=analysis_config,
    )
    return CandidateDocumentRegatherResult(
        limit=limit,
        output_queue_path=output_queue_path,
        plan=plan,
        batch_result=batch_result,
    )


def run_candidate_document_extraction_batch(
    queue_rows: list[dict[str, str]] | None = None,
    paths: CandidateDocumentBatchPaths | None = None,
    *,
    fetcher: Callable[[str, str], RawDocumentCapture] = fetch_raw_document,
    analysis_config: AnalysisSegmentConfig | None = None,
) -> CandidateDocumentBatchResult:
    paths = paths or CandidateDocumentBatchPaths.default()
    if queue_rows is None:
        queue_rows = _load_candidate_document_queue(paths.queue_path)
    analysis_config = analysis_config or AnalysisSegmentConfig()
    shared_source_candidates = _shared_source_candidates(queue_rows)

    manifest_index = _load_raw_manifest_index(paths.raw_manifest_path)
    metadata_by_document = _load_existing_csv_by_key(paths.metadata_path, "document_id")
    full_text_by_document = _load_existing_jsonl_by_key(paths.full_text_path, "document_id")
    paragraph_rows = read_csv(paths.paragraph_path) if paths.paragraph_path.exists() else []
    sentence_rows = read_csv(paths.sentence_path) if paths.sentence_path.exists() else []

    current_metadata_rows: dict[str, dict[str, str]] = {}
    current_text_rows: dict[str, dict[str, str]] = {}
    current_paragraph_rows: dict[str, list[dict[str, str]]] = {}
    current_sentence_rows: dict[str, list[dict[str, str]]] = {}
    replaced_document_ids: set[str] = set()

    processed_documents = 0
    successful_documents = 0
    fetched_documents = 0
    reused_raw_documents = 0
    metadata_errors = 0
    fetch_errors = 0
    extraction_errors = 0
    media_without_transcript = 0

    for row in queue_rows:
        job: CandidateDocumentJob | None = None
        try:
            job = _normalize_candidate_document_job(row)
        except DocumentCorpusError as error:
            metadata_errors += 1
            processed_documents += 1
            fallback_id = row.get("document_id", "").strip() or stable_hash(
                json.dumps(row, sort_keys=True)
            )
            current_metadata_rows[fallback_id] = _error_metadata_row(
                document_id=fallback_id,
                candidate_name=row.get("candidate_name", "").strip(),
                race_id=row.get("race_id", "").strip(),
                role=row.get("role", "").strip(),
                election_date=row.get("election_date", "").strip(),
                publication_date=(
                    row.get("publication_date", "").strip()
                    or row.get("published_date", "").strip()
                ),
                source_type=row.get("source_type", "").strip(),
                source_url=(
                    row.get("source_url", "").strip()
                    or row.get("seed_url", "").strip()
                    or row.get("reference_url", "").strip()
                ),
                archive_url=row.get("archive_url", "").strip(),
                queue_id=row.get("queue_id", "").strip(),
                seed_kind=row.get("seed_kind", "").strip(),
                source_record_id=row.get("source_record_id", "").strip(),
                analysis_scope=row.get("analysis_scope", "").strip() or "analysis",
                notes=row.get("notes", "").strip(),
                fetch_status="metadata_error",
                extraction_status="metadata_error",
                error=str(error),
            )
            continue

        replaced_document_ids.add(job.document_id)
        try:
            capture, fetch_status, raw_path = _resolve_raw_capture(job, manifest_index, fetcher)
        except (DocumentCorpusError, RawFetchError) as error:
            processed_documents += 1
            if isinstance(error, RawFetchError):
                fetch_errors += 1
                fetch_status = "fetch_error"
            else:
                metadata_errors += 1
                fetch_status = "metadata_error"
            current_metadata_rows[job.document_id] = _error_metadata_row(
                document_id=job.document_id,
                candidate_name=job.candidate_name,
                race_id=job.race_id,
                role=job.role,
                election_date=job.election_date,
                publication_date=job.publication_date,
                source_type=job.source_type,
                source_url=job.source_url,
                archive_url=job.archive_url,
                queue_id=job.queue_id,
                seed_kind=job.seed_kind,
                source_record_id=job.source_record_id,
                analysis_scope=job.analysis_scope,
                notes=job.notes,
                fetch_status=fetch_status,
                extraction_status="not_attempted",
                error=str(error),
                coverage_status="found_unverified" if fetch_status == "fetch_error" else "",
            )
            current_paragraph_rows[job.document_id] = []
            current_sentence_rows[job.document_id] = []
            continue

        processed_documents += 1
        if fetch_status == "fetched":
            fetched_documents += 1
            raw_path = persist_raw_document(capture, paths.raw_dir)
            manifest_row = _raw_manifest_row(capture, raw_path, archive_url=job.archive_url)
            _append_raw_manifest(paths.raw_manifest_path, manifest_row)
            _index_raw_manifest_row(manifest_index, manifest_row)
        else:
            reused_raw_documents += 1

        try:
            extracted = (
                extract_transcript_text(
                    capture,
                    job.transcript_text,
                    title=job.transcript_title,
                )
                if job.transcript_text
                else extract_document_text(capture)
            )
        except ExtractionError as error:
            extraction_errors += 1
            current_metadata_rows[job.document_id] = _error_metadata_row(
                document_id=job.document_id,
                candidate_name=job.candidate_name,
                race_id=job.race_id,
                role=job.role,
                election_date=job.election_date,
                publication_date=job.publication_date,
                source_type=job.source_type,
                source_url=job.source_url,
                archive_url=job.archive_url,
                queue_id=job.queue_id,
                seed_kind=job.seed_kind,
                source_record_id=job.source_record_id,
                analysis_scope=job.analysis_scope,
                notes=job.notes,
                fetch_status=fetch_status,
                extraction_status="extraction_error",
                error=str(error),
                capture=capture,
                raw_path=raw_path,
            )
            current_paragraph_rows[job.document_id] = []
            current_sentence_rows[job.document_id] = []
            continue

        shared_scope_status = ""
        if (
            len(shared_source_candidates.get(canonical_source_url(job.source_url), set())) > 1
            and not job.transcript_text
        ):
            extracted, shared_scope_status = _scope_shared_document_for_candidate(
                job,
                extracted,
            )

        extraction_status = (
            "media_no_transcript"
            if extracted.coverage_status == "media_no_transcript"
            else shared_scope_status or "extracted"
        )
        if extraction_status == "media_no_transcript":
            media_without_transcript += 1
        successful_documents += 1

        metadata = build_candidate_document_metadata(
            candidate_name=job.candidate_name,
            race_id=job.race_id,
            election_date=job.election_date,
            publication_date=job.publication_date,
            source_type=job.source_type,
            capture=capture,
            extracted=extracted,
            archive_url=job.archive_url,
            raw_path=raw_path,
        )
        current_metadata_rows[job.document_id] = _success_metadata_row(
            metadata,
            job=job,
            fetch_status=fetch_status,
            extraction_status=extraction_status,
            extractor=extracted.extractor,
        )
        current_text_rows[job.document_id] = _full_text_row(metadata, extracted, job, raw_path)
        current_paragraph_rows[job.document_id] = [
            segment.as_row() for segment in extracted.paragraphs
        ]
        current_sentence_rows[job.document_id] = [
            segment.as_row() for segment in extracted.sentences
        ]

    for document_id in replaced_document_ids:
        full_text_by_document.pop(document_id, None)
        metadata_by_document.pop(document_id, None)
    metadata_by_document.update(current_metadata_rows)
    full_text_by_document.update(
        {
            document_id: row
            for document_id, row in current_text_rows.items()
            if row.get("text", "")
            or row.get("coverage_status") in {
                "media_no_transcript",
                "shared_document_unscoped",
            }
        }
    )

    paragraph_rows = [
        row for row in paragraph_rows if row.get("document_id", "") not in replaced_document_ids
    ]
    sentence_rows = [
        row for row in sentence_rows if row.get("document_id", "") not in replaced_document_ids
    ]
    for rows in current_paragraph_rows.values():
        paragraph_rows.extend(rows)
    for rows in current_sentence_rows.values():
        sentence_rows.extend(rows)

    write_csv(
        paths.metadata_path,
        sorted(metadata_by_document.values(), key=_metadata_sort_key),
        _metadata_fieldnames(),
    )
    _write_jsonl(
        paths.full_text_path,
        sorted(full_text_by_document.values(), key=_metadata_sort_key),
    )
    write_csv(
        paths.paragraph_path,
        sorted(paragraph_rows, key=_segment_sort_key),
        ["segment_id", "document_id", "segment_kind", "index", "locator", "text", "sha256"],
    )
    write_csv(
        paths.sentence_path,
        sorted(sentence_rows, key=_segment_sort_key),
        ["segment_id", "document_id", "segment_kind", "index", "locator", "text", "sha256"],
    )
    analysis_segments = _build_analysis_segment_corpus(
        metadata_by_document.values(),
        paragraph_rows,
        sentence_rows,
        analysis_config,
    )
    write_csv(
        paths.analysis_segment_path,
        [segment.as_row() for segment in analysis_segments],
        _analysis_segment_fieldnames(),
    )

    return CandidateDocumentBatchResult(
        queued_documents=len(queue_rows),
        processed_documents=processed_documents,
        successful_documents=successful_documents,
        fetched_documents=fetched_documents,
        reused_raw_documents=reused_raw_documents,
        metadata_errors=metadata_errors,
        fetch_errors=fetch_errors,
        extraction_errors=extraction_errors,
        media_without_transcript=media_without_transcript,
        raw_manifest_path=paths.raw_manifest_path,
        metadata_path=paths.metadata_path,
        full_text_path=paths.full_text_path,
        paragraph_path=paths.paragraph_path,
        sentence_path=paths.sentence_path,
        analysis_segment_path=paths.analysis_segment_path,
    )


def build_analysis_segments(
    *,
    candidate_name: str,
    race_id: str,
    role: str,
    document_id: str,
    paragraphs: Sequence[TextSegment],
    sentences: Sequence[TextSegment],
    candidate_slug_value: str = "",
    source_type: str = "",
    config: AnalysisSegmentConfig | None = None,
) -> tuple[AnalysisSegment, ...]:
    analysis_config = config or AnalysisSegmentConfig()
    segments = _analysis_segments_for_document(
        candidate_name=candidate_name,
        race_id=race_id,
        role=role,
        document_id=document_id,
        paragraphs=paragraphs,
        sentences=sentences,
        candidate_slug_value=candidate_slug_value,
        source_type=source_type,
        config=analysis_config,
    )
    return _annotate_analysis_segments(segments, analysis_config)


def build_analysis_segment_review_sample(
    segments: Sequence[AnalysisSegment],
    *,
    sample_size: int | None = None,
) -> list[dict[str, str]]:
    if not segments:
        return []
    ordered = sorted(segments, key=_analysis_segment_sort_key)
    size = sample_size or min(len(ordered), AnalysisSegmentConfig().review_sample_size)
    buckets = {
        "boilerplate": [
            segment for segment in ordered if segment.boilerplate_flag
        ],
        "exact_duplicate": [
            segment
            for segment in ordered
            if segment.exact_duplicate_flag and not segment.boilerplate_flag
        ],
        "near_duplicate": [
            segment
            for segment in ordered
            if segment.near_duplicate_flag and not segment.boilerplate_flag
        ],
        "merged_fragment": [
            segment
            for segment in ordered
            if segment.analysis_kind == "merged"
            and not segment.exact_duplicate_flag
            and not segment.near_duplicate_flag
        ],
        "split_paragraph": [
            segment
            for segment in ordered
            if segment.analysis_kind == "sentence_window"
            and not segment.exact_duplicate_flag
            and not segment.near_duplicate_flag
        ],
        "standard": ordered[:],
    }
    chosen: list[dict[str, str]] = []
    seen: set[str] = set()
    while len(chosen) < size and any(buckets.values()):
        progressed = False
        for bucket_name in (
            "boilerplate",
            "exact_duplicate",
            "near_duplicate",
            "merged_fragment",
            "split_paragraph",
            "standard",
        ):
            bucket = buckets[bucket_name]
            while bucket and bucket[0].analysis_segment_id in seen:
                bucket.pop(0)
            if not bucket or len(chosen) >= size:
                continue
            segment = bucket.pop(0)
            row = segment.as_row()
            row["review_bucket"] = bucket_name
            chosen.append(row)
            seen.add(segment.analysis_segment_id)
            progressed = True
        if not progressed:
            break
    return chosen


def extract_transcript_text(
    capture: RawDocumentCapture,
    transcript_text: str,
    *,
    title: str = "",
) -> ExtractedDocument:
    sanitized_text = _sanitize_extracted_text(transcript_text)
    paragraph_segments, sentence_segments = segment_document(
        capture.document_id,
        sanitized_text,
    )
    if not paragraph_segments:
        raise ExtractionError(f"{capture.document_id}: extracted text is empty")
    normalized_text = "\n\n".join(segment.text for segment in paragraph_segments)
    return ExtractedDocument(
        document_id=capture.document_id,
        source_url=capture.source_url,
        final_url=capture.final_url,
        retrieved_at=capture.retrieved_at,
        content_type=capture.content_type,
        title=_sanitize_extracted_text(title).strip(),
        text=normalized_text,
        text_sha256=_sha256_text(normalized_text),
        coverage_status="found_unverified",
        extractor="transcript",
        paragraphs=paragraph_segments,
        sentences=sentence_segments,
    )


def canonical_source_url(value: str) -> str:
    normalized = normalize_source_url(value)
    archive_url, live_url = split_archive_url(normalized)
    base_url = live_url or archive_url
    parsed = urlparse(base_url)
    query_parts = []
    for part in filter(None, parsed.query.split("&")):
        key, separator, remainder = part.partition("=")
        if key.casefold() in TRACKING_QUERY_PARAMS:
            continue
        query_parts.append((key, remainder if separator else ""))
    query = "&".join(
        f"{key}={value}" if value else key
        for key, value in sorted(query_parts)
    )
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, path, "", query, ""))


def split_archive_url(value: str) -> tuple[str, str]:
    normalized = normalize_source_url(value)
    parsed = urlparse(normalized)
    if parsed.netloc != "web.archive.org":
        return "", normalized
    match = re.match(r"^/web/\d+(?:[a-z_]+)?/(https?://.+)$", parsed.path, re.IGNORECASE)
    if not match:
        match = re.match(r"^/web/\d+(?:[a-z_]+)?/(https?:/.+)$", parsed.path, re.IGNORECASE)
    if not match:
        return normalized, ""
    live_url = match.group(1)
    if live_url.startswith("http:/") and not live_url.startswith("http://"):
        live_url = live_url.replace("http:/", "http://", 1)
    if live_url.startswith("https:/") and not live_url.startswith("https://"):
        live_url = live_url.replace("https:/", "https://", 1)
    return normalized, normalize_source_url(live_url)


def source_domain(value: str) -> str:
    if not value:
        return ""
    _, live_url = split_archive_url(value)
    parsed = urlparse(live_url or value)
    return (parsed.hostname or "").removeprefix("www.")


def classify_source_type(source_type: str, source_url: str = "") -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", source_type.casefold()).strip("_")
    if not normalized:
        if not source_url:
            return "search_log"
        host = source_domain(source_url)
        path = urlparse(canonical_source_url(source_url)).path.casefold()
        if host in SOCIAL_HOSTS:
            return "social_post"
        if "questionnaire" in path:
            return "questionnaire"
        if any(token in path for token in ("issues", "platform", "policies", "policy")):
            return "policy_page"
        return "other"
    if "social" in normalized:
        return "social_post"
    if "questionnaire" in normalized or "written_response" in normalized:
        return "questionnaire"
    if "voter_guide" in normalized:
        return "voter_guide"
    if "debate" in normalized:
        return "debate"
    if "forum" in normalized:
        return "forum"
    if "interview" in normalized:
        return "interview"
    if "speech" in normalized:
        return "speech"
    if "video" in normalized:
        return "video"
    if "op_ed" in normalized or "profile" in normalized:
        return "profile_or_op_ed"
    if "filing" in normalized:
        return "filing"
    if any(token in normalized for token in ("release", "announcement", "press")):
        return "press_release"
    if "statement" in normalized:
        return "statement"
    if any(token in normalized for token in ("issue", "policy", "platform")):
        return "policy_page"
    if any(token in normalized for token in ("literature", "mailer", "ad")):
        return "campaign_material"
    if any(
        token in normalized
        for token in ("campaign_page", "campaign_site", "campaign_website", "website", "campaign")
    ):
        return "campaign_page"
    return "other"


def _candidate_source_rows(
    evidence_rows: Sequence[dict[str, str]],
    candidate_document_rows: Sequence[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    rows = [dict(row) for row in evidence_rows]
    for row in candidate_document_rows or ():
        normalized = _normalize_candidate_document_row(row)
        if normalized:
            rows.append(normalized)
    return rows


def _coerce_source_types(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(" | ") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        result: list[str] = []
        for item in value:
            result.extend(_coerce_source_types(item))
        return result
    return [str(value).strip()]


def _normalize_source_type_tag(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _supports_campaign_domain_derivation(
    *,
    domain: str,
    candidate_slug_value: str,
    source_types: Sequence[str],
    explicit_registration: bool,
) -> bool:
    if not _is_candidate_specific_campaign_domain(
        domain,
        candidate_slug_value,
        explicit_registration=explicit_registration,
    ):
        return False
    if explicit_registration:
        return True
    normalized_types = [_normalize_source_type_tag(value) for value in source_types if value]
    if not normalized_types:
        return False
    return any(
        any(term in source_type for term in CAMPAIGN_DOMAIN_SOURCE_TERMS)
        for source_type in normalized_types
    )


def _normalize_candidate_document_row(row: dict[str, str]) -> dict[str, str]:
    source_url = (
        row.get("source_url", "")
        or row.get("live_url", "")
        or row.get("url", "")
    ).strip()
    candidate_name = row.get("candidate_name", "").strip()
    if not source_url or not candidate_name:
        return {}
    return {
        "statement_key": (
            row.get("statement_key", "")
            or row.get("source_record_id", "")
            or row.get("document_id", "")
        ).strip(),
        "race_id": row.get("race_id", "").strip(),
        "candidate_name": candidate_name,
        "election_date": row.get("election_date", "").strip(),
        "role": row.get("role", "").strip(),
        "evidence_status": (
            row.get("evidence_status", "")
            or row.get("verification_status", "")
            or row.get("coverage_status", "")
            or row.get("status", "")
            or "verified"
        ).strip(),
        "source_url": source_url,
        "source_type": (
            row.get("source_type", "")
            or row.get("source_type_class", "")
            or row.get("document_type", "")
        ).strip(),
        "publication_date": row.get("publication_date", "").strip(),
        "effective_date": row.get("effective_date", "").strip(),
        "source_tier": row.get("source_tier", "").strip(),
        "archive_url": row.get("archive_url", "").strip(),
        "live_url": row.get("live_url", "").strip(),
        "locator": (
            row.get("locator", "")
            or row.get("legacy_locator", "")
            or row.get("legacy_locators", "")
        ).strip(),
        "analysis_scope": (row.get("analysis_scope", "").strip() or "analysis"),
        "notes": row.get("notes", "").strip(),
        "_fetch_url": source_url,
        "_registry_source": "candidate_document_registry",
    }


def build_candidate_source_inventory(
    evidence_rows: list[dict[str, str]],
    roster_rows: list[dict[str, str]],
    candidate_document_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    roster_by_race, roster_by_date = _index_roster_rows(roster_rows)
    grouped: dict[tuple[str, str, str], dict[str, object]] = {}
    for row in _candidate_source_rows(evidence_rows, candidate_document_rows):
        source_url = row.get("source_url", "").strip()
        if not source_url:
            continue
        normalized_url = normalize_source_url(source_url)
        archive_url, live_url = split_archive_url(normalized_url)
        canonical_url = canonical_source_url(source_url)
        race_id = row.get("race_id", "").strip()
        candidate_name = row.get("candidate_name", "").strip()
        election_date = row.get("election_date", "").strip()
        role = row.get("role", "").strip()
        identity = _identity_name(candidate_name)
        roster = _match_roster_row(
            race_id, election_date, identity, roster_by_race, roster_by_date
        )
        source_type_class = classify_source_type(row.get("source_type", ""), source_url)
        group_key = (race_id, identity, canonical_url)
        group = grouped.setdefault(
            group_key,
            {
                "race_id": race_id,
                "candidate_name": candidate_name,
                "candidate_slug": candidate_slug(candidate_name),
                "role": role or roster.get("role", ""),
                "election_date": election_date or roster.get("election_date", ""),
                "queue_id": roster.get("queue_id", ""),
                "official_election_source": roster.get("official_election_source", ""),
                "canonical_url": canonical_url,
                "fetch_url": row.get("_fetch_url", "").strip() or normalized_url,
                "archive_url": row.get("archive_url", "").strip() or archive_url,
                "live_url": row.get("live_url", "").strip() or live_url or canonical_url,
                "source_domain": source_domain(canonical_url),
                "source_type_class": source_type_class,
                "source_types": set(),
                "statement_keys": set(),
                "legacy_locators": set(),
                "evidence_statuses": set(),
                "publication_dates": set(),
                "effective_dates": set(),
                "source_tiers": set(),
                "analysis_scopes": set(),
                "notes": set(),
                "campaign_domain_registered": False,
                "campaign_domain_signal": False,
            },
        )
        group["role"] = group["role"] or role or roster.get("role", "")
        group["queue_id"] = group["queue_id"] or roster.get("queue_id", "")
        group["official_election_source"] = group["official_election_source"] or roster.get(
            "official_election_source", ""
        )
        if row.get("_fetch_url", "").strip() and not str(group["fetch_url"]).strip():
            group["fetch_url"] = row.get("_fetch_url", "").strip()
        if row.get("archive_url", "").strip() and not str(group["archive_url"]).strip():
            group["archive_url"] = row.get("archive_url", "").strip()
        if row.get("live_url", "").strip() and not str(group["live_url"]).strip():
            group["live_url"] = row.get("live_url", "").strip()
        group["source_types"].add(row.get("source_type", "").strip())
        statement_key = row.get("statement_key", "").strip()
        if statement_key:
            group["statement_keys"].add(statement_key)
        locator = row.get("locator", "").strip()
        if locator:
            group["legacy_locators"].add(locator)
        evidence_status = row.get("evidence_status", "").strip()
        if evidence_status:
            group["evidence_statuses"].add(evidence_status)
        publication_date = row.get("publication_date", "").strip()
        if publication_date:
            group["publication_dates"].add(publication_date)
        effective_date = row.get("effective_date", "").strip()
        if effective_date:
            group["effective_dates"].add(effective_date)
        source_tier = row.get("source_tier", "").strip()
        if source_tier:
            group["source_tiers"].add(source_tier)
        analysis_scope = row.get("analysis_scope", "").strip()
        if analysis_scope:
            group["analysis_scopes"].add(analysis_scope)
        note = row.get("notes", "").strip()
        if note:
            group["notes"].add(note)
        if row.get("_registry_source") == "candidate_document_registry":
            group["campaign_domain_registered"] = True
        if _supports_campaign_domain_derivation(
            domain=str(group["source_domain"]),
            candidate_slug_value=str(group["candidate_slug"]),
            source_types=[row.get("source_type", "").strip()],
            explicit_registration=bool(group["campaign_domain_registered"]),
        ):
            group["campaign_domain_signal"] = True
        current_priority = SOURCE_TYPE_CLASS_PRIORITY[group["source_type_class"]]
        new_priority = SOURCE_TYPE_CLASS_PRIORITY[source_type_class]
        if (new_priority, source_type_class) < (
            current_priority,
            str(group["source_type_class"]),
        ):
            group["source_type_class"] = source_type_class

    campaign_domains = derive_campaign_domains(grouped.values())
    inventory_rows = []
    for group in grouped.values():
        statement_keys = sorted(group["statement_keys"])
        legacy_locators = sorted(group["legacy_locators"])
        publication_dates = sorted(group["publication_dates"])
        effective_dates = sorted(group["effective_dates"])
        source_tiers = sorted(group["source_tiers"], key=lambda value: int(value) if value.isdigit() else 99)
        analysis_scopes = set(group["analysis_scopes"])
        notes = sorted(group["notes"])
        evidence_statuses = set(group["evidence_statuses"])
        evidence_status = "verified" if "verified" in evidence_statuses else (
            sorted(evidence_statuses)[0] if evidence_statuses else ""
        )
        source_types = sorted(value for value in group["source_types"] if value)
        key = (
            group["race_id"],
            group["candidate_slug"],
            group["election_date"],
            group["role"],
        )
        inventory_rows.append(
            {
                "source_record_id": stable_hash(
                    group["race_id"],
                    group["candidate_name"],
                    group["canonical_url"],
                ),
                "queue_id": str(group["queue_id"]),
                "race_id": str(group["race_id"]),
                "candidate_slug": str(group["candidate_slug"]),
                "candidate_name": str(group["candidate_name"]),
                "role": str(group["role"]),
                "election_date": str(group["election_date"]),
                "official_election_source": str(group["official_election_source"]),
                "fetch_url": str(group["fetch_url"]),
                "source_url": str(group["canonical_url"]),
                "archive_url": str(group["archive_url"]),
                "live_url": str(group["live_url"]),
                "source_domain": str(group["source_domain"]),
                "campaign_domain": campaign_domains.get(key, ""),
                "source_type": " | ".join(source_types),
                "source_type_class": str(group["source_type_class"]),
                "publication_date": publication_dates[0] if publication_dates else "",
                "effective_date": effective_dates[0] if effective_dates else "",
                "source_tier": source_tiers[0] if source_tiers else "",
                "analysis_scope": (
                    "context_only" if "context_only" in analysis_scopes else "analysis"
                ),
                "evidence_status": evidence_status,
                "statement_count": str(len(statement_keys)),
                "statement_keys": " | ".join(statement_keys),
                "legacy_locators": " | ".join(legacy_locators),
                "notes": " | ".join(notes),
            }
        )
    return sorted(
        inventory_rows,
        key=lambda row: (
            row["election_date"],
            row["candidate_name"].casefold(),
            row["role"],
            row["source_url"],
        ),
    )


def derive_campaign_domains(
    source_rows: list[dict[str, object]],
) -> dict[tuple[str, str, str, str], str]:
    candidates: dict[tuple[str, str, str, str], Counter[str]] = defaultdict(Counter)
    priorities: dict[tuple[str, str, str, str], dict[str, int]] = defaultdict(dict)
    for row in source_rows:
        domain = str(row.get("source_domain", ""))
        if not domain:
            continue
        candidate_slug_value = str(row.get("candidate_slug", ""))
        explicit_registration = bool(row.get("campaign_domain_registered"))
        if not _supports_campaign_domain_derivation(
            domain=domain,
            candidate_slug_value=candidate_slug_value,
            source_types=_coerce_source_types(
                row.get("source_types", row.get("source_type"))
            ),
            explicit_registration=explicit_registration,
        ):
            continue
        if not bool(row.get("campaign_domain_signal")) and not explicit_registration:
            continue
        source_type_class = str(row.get("source_type_class", "other"))
        key = (
            str(row.get("race_id", "")),
            candidate_slug_value,
            str(row.get("election_date", "")),
            str(row.get("role", "")),
        )
        candidates[key][domain] += 1
        priority = SOURCE_TYPE_CLASS_PRIORITY[source_type_class]
        best_priority = priorities[key].get(domain, priority)
        priorities[key][domain] = min(best_priority, priority)
    results = {}
    for key, domain_counts in candidates.items():
        best_domain = min(
            domain_counts,
            key=lambda domain: (
                priorities[key][domain],
                -domain_counts[domain],
                domain,
            ),
        )
        results[key] = best_domain
    return results


def build_candidate_document_discovery_queue(
    evidence_rows: list[dict[str, str]],
    roster_rows: list[dict[str, str]],
    candidate_document_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    source_rows = _candidate_source_rows(evidence_rows, candidate_document_rows)
    inventory_rows = build_candidate_source_inventory(
        evidence_rows,
        roster_rows,
        candidate_document_rows,
    )
    candidate_records = _candidate_records(source_rows, roster_rows)
    inventory_by_candidate: dict[tuple[str, str, str, str], list[dict[str, str]]] = (
        defaultdict(list)
    )
    for row in inventory_rows:
        inventory_by_candidate[
            (row["race_id"], row["candidate_slug"], row["election_date"], row["role"])
        ].append(row)
    queue_rows = []
    seen = set()
    for candidate in candidate_records:
        key = (
            candidate["race_id"],
            candidate["candidate_slug"],
            candidate["election_date"],
            candidate["role"],
        )
        sources = inventory_by_candidate.get(key, [])
        campaign_domain = sources[0]["campaign_domain"] if sources else ""
        if campaign_domain:
            seed_url = f"https://{campaign_domain}/"
            seen_key = (*key, "campaign_domain", seed_url)
            if seen_key not in seen:
                seen.add(seen_key)
                queue_rows.append(
                    _discovery_seed_row(
                        candidate,
                        seed_url=seed_url,
                        seed_kind="campaign_domain",
                        source_record_id="",
                        source_type_class="campaign_page",
                        campaign_domain=campaign_domain,
                        known_source_count=len(sources),
                        legacy_locators="",
                        note="Derived from existing candidate-owned source URLs",
                    )
                )
        for source in sources:
            seed_url = source.get("fetch_url", "").strip() or source["live_url"]
            seen_key = (*key, "known_document", seed_url)
            if seen_key in seen:
                continue
            seen.add(seen_key)
            queue_rows.append(
                _discovery_seed_row(
                    candidate,
                    seed_url=seed_url,
                    seed_kind="known_document",
                    source_record_id=source["source_record_id"],
                    source_type_class=source["source_type_class"],
                    campaign_domain=source["campaign_domain"],
                    known_source_count=len(sources),
                    legacy_locators=source.get("legacy_locators", ""),
                    note="Seeded from existing candidate corpus URL",
                    source_tier=source.get("source_tier", ""),
                    publication_date=source.get("publication_date", ""),
                    effective_date=source.get("effective_date", ""),
                    archive_url=source.get("archive_url", ""),
                    live_url=source.get("live_url", ""),
                    analysis_scope=source.get("analysis_scope", "") or "analysis",
                )
            )
        official_election_source = candidate["official_election_source"]
        if official_election_source:
            for source_url in _split_source_urls(official_election_source):
                seed_url = canonical_source_url(source_url)
                seen_key = (*key, "official_election_source", seed_url)
                if seen_key not in seen:
                    seen.add(seen_key)
                    queue_rows.append(
                        _discovery_seed_row(
                            candidate,
                            seed_url=seed_url,
                            seed_kind="official_election_source",
                            source_record_id="",
                            source_type_class="filing",
                            campaign_domain=campaign_domain,
                            known_source_count=len(sources),
                            legacy_locators="",
                            note="Election metadata context from roster discovery",
                        )
                    )
    return sorted(
        queue_rows,
        key=lambda row: (
            row["election_date"],
            row["candidate_name"].casefold(),
            row["role"],
            int(row["seed_priority"]),
            row["seed_url"],
        ),
    )


def run_campaign_domain_discovery_pass(
    paths: CampaignDomainDiscoveryPaths | None = None,
    *,
    max_domains: int = 10,
    max_live_pages: int = 6,
    max_urls_per_stage: int = 40,
    wayback_limit: int = 200,
    fetcher: Callable[[str], dict[str, str]] | None = None,
    cdx_fetcher: Callable[[str, date, date, int], list[dict[str, str]]] | None = None,
    now: datetime | None = None,
) -> CampaignDomainDiscoveryResult:
    discovery_paths = paths or CampaignDomainDiscoveryPaths.default()
    timestamp = (now or datetime.now(UTC)).isoformat()
    queue_rows = _load_candidate_document_queue(discovery_paths.queue_path)
    seeds = _campaign_domain_seeds_from_queue(queue_rows)
    status_rows = read_csv(discovery_paths.status_path) if discovery_paths.status_path.exists() else []
    status_by_seed = {row.get("discovery_seed_id", ""): dict(row) for row in status_rows}
    discovered_rows = (
        read_csv(discovery_paths.discovered_url_path)
        if discovery_paths.discovered_url_path.exists()
        else []
    )
    discovered_index = {
        _discovered_url_key(row): dict(row)
        for row in discovered_rows
        if row.get("discovery_seed_id") and row.get("source_url")
    }
    fetch = fetcher or _fetch_discovery_document
    cdx = cdx_fetcher or _query_wayback_cdx
    pending = [seed for seed in seeds if not _campaign_domain_seed_complete(seed, status_by_seed)]
    attempted_domains = _attempted_campaign_domains(seeds, status_by_seed)
    fresh_pending = [
        seed
        for seed in pending
        if seed["campaign_domain"] not in attempted_domains
    ]
    incomplete_pending = [
        seed
        for seed in pending
        if seed["campaign_domain"] in attempted_domains
        and _seed_has_unattempted_stage(seed, status_by_seed)
    ]
    retry_pending = [
        seed
        for seed in pending
        if _seed_has_retryable_stage(seed, status_by_seed)
    ]
    selected = _select_campaign_domain_batch(fresh_pending, max_domains)
    if len(selected) < max_domains:
        selected.extend(
            _select_campaign_domain_batch(
                incomplete_pending,
                max_domains - len(selected),
                excluded_domains={seed["campaign_domain"] for seed in selected},
            )
        )
    if len(selected) < max_domains:
        selected.extend(
            _select_campaign_domain_batch(
                retry_pending,
                max_domains - len(selected),
                excluded_domains={seed["campaign_domain"] for seed in selected},
            )
        )
    searched_domains = 0
    appended_queue_rows = 0
    new_discovery_keys: set[tuple[str, str, str]] = set()
    for seed in selected:
        status_row = status_by_seed.get(seed["discovery_seed_id"], _new_campaign_domain_status(seed))
        searched_domains += 1
        if not _is_candidate_specific_campaign_domain(seed["campaign_domain"], seed["candidate_slug"]):
            status_row.update(
                {
                    "live_search_status": "skipped_non_campaign_domain",
                    "live_searched_at": timestamp,
                    "live_error": "",
                    "archive_search_status": "skipped_non_campaign_domain",
                    "archive_searched_at": timestamp,
                    "archive_error": "",
                }
            )
            status_by_seed[seed["discovery_seed_id"]] = status_row
            continue
        live_retrying_existing_error = _should_retry_existing_stage(status_row, "live")
        if _should_attempt_stage(status_row, "live"):
            live_rows, live_status, live_error = _discover_live_campaign_domain_urls(
                seed,
                fetcher=fetch,
                max_live_pages=max_live_pages,
                max_urls=max_urls_per_stage,
            )
            live_retry_used = False
            if (
                live_status == "error"
                and not live_retrying_existing_error
                and _is_transient_discovery_error(live_error)
            ):
                live_rows, live_status, live_error = _discover_live_campaign_domain_urls(
                    seed,
                    fetcher=fetch,
                    max_live_pages=max_live_pages,
                    max_urls=max_urls_per_stage,
                )
                live_retry_used = True
            status_row.update(
                {
                    "live_search_status": live_status,
                    "live_searched_at": timestamp,
                    "live_error": live_error,
                }
            )
            if live_retrying_existing_error or live_retry_used:
                status_row["live_retry_count"] = str(
                    max(1, _safe_int(status_row.get("live_retry_count", "0")) + 1)
                )
            for row in live_rows:
                discovered_index[_discovered_url_key(row)] = row
                new_discovery_keys.add(_discovered_url_key(row))
        archive_retrying_existing_error = _should_retry_existing_stage(status_row, "archive")
        if _should_attempt_stage(status_row, "archive"):
            archive_rows, archive_status, archive_error = _discover_archive_campaign_domain_urls(
                seed,
                cdx_fetcher=cdx,
                max_urls=max_urls_per_stage,
                limit=wayback_limit,
            )
            archive_retry_used = False
            if (
                archive_status == "error"
                and not archive_retrying_existing_error
                and _is_transient_discovery_error(archive_error)
            ):
                archive_rows, archive_status, archive_error = _discover_archive_campaign_domain_urls(
                    seed,
                    cdx_fetcher=cdx,
                    max_urls=max_urls_per_stage,
                    limit=wayback_limit,
                )
                archive_retry_used = True
            status_row.update(
                {
                    "archive_search_status": archive_status,
                    "archive_searched_at": timestamp,
                    "archive_error": archive_error,
                }
            )
            if archive_retrying_existing_error or archive_retry_used:
                status_row["archive_retry_count"] = str(
                    max(1, _safe_int(status_row.get("archive_retry_count", "0")) + 1)
                )
            for row in archive_rows:
                discovered_index[_discovered_url_key(row)] = row
                new_discovery_keys.add(_discovered_url_key(row))
        status_by_seed[seed["discovery_seed_id"]] = status_row
    updated_queue_rows, appended_queue_rows = _append_campaign_discovery_queue_rows(
        queue_rows,
        [discovered_index[key] for key in sorted(new_discovery_keys)],
    )
    _write_candidate_document_queue(discovery_paths.queue_path, updated_queue_rows)
    _write_campaign_domain_status_rows(
        discovery_paths.status_path,
        list(status_by_seed.values()),
    )
    _write_campaign_domain_discovered_rows(
        discovery_paths.discovered_url_path,
        list(discovered_index.values()),
    )
    remaining_domains = len(
        {
            seed["campaign_domain"]
            for seed in seeds
            if not _campaign_domain_seed_complete(seed, status_by_seed)
        }
    )
    return CampaignDomainDiscoveryResult(
        queued_domains=len(selected),
        searched_domains=searched_domains,
        appended_queue_rows=appended_queue_rows,
        discovered_urls=len(new_discovery_keys),
        remaining_domains=remaining_domains,
        status_path=discovery_paths.status_path,
        discovered_url_path=discovery_paths.discovered_url_path,
        queue_path=discovery_paths.queue_path,
    )


def _campaign_domain_seeds_from_queue(queue_rows: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
    for row in queue_rows:
        campaign_domain = row.get("campaign_domain", "").strip().casefold()
        if not campaign_domain:
            continue
        key = (
            row.get("race_id", "").strip(),
            row.get("candidate_slug", "").strip() or candidate_slug(row.get("candidate_name", "")),
            row.get("candidate_name", "").strip(),
            row.get("role", "").strip(),
            campaign_domain,
        )
        seed = grouped.setdefault(
            key,
            {
                "discovery_seed_id": stable_hash(
                    row.get("race_id", "").strip(),
                    row.get("candidate_name", "").strip(),
                    row.get("role", "").strip(),
                    "campaign_domain",
                    f"https://{campaign_domain}/",
                ),
                "queue_id": row.get("queue_id", "").strip(),
                "race_id": row.get("race_id", "").strip(),
                "candidate_slug": key[1],
                "candidate_name": row.get("candidate_name", "").strip(),
                "role": row.get("role", "").strip(),
                "election_date": row.get("election_date", "").strip(),
                "campaign_domain": campaign_domain,
                "official_election_source": row.get("official_election_source", "").strip(),
                "known_source_count": row.get("known_source_count", "0").strip() or "0",
                "legacy_statement_count": row.get("legacy_statement_count", "0").strip() or "0",
                "campaign_domain_registered": row.get("campaign_domain_registered", "").strip(),
                "campaign_domain_signal": "",
            },
        )
        seed["queue_id"] = seed["queue_id"] or row.get("queue_id", "").strip()
        if row.get("official_election_source", "").strip():
            seed["official_election_source"] = row.get("official_election_source", "").strip()
        if row.get("election_date", "").strip():
            seed["election_date"] = row.get("election_date", "").strip()
        known_source_count = max(
            _safe_int(seed.get("known_source_count", "0")),
            _safe_int(row.get("known_source_count", "0")),
        )
        legacy_statement_count = max(
            _safe_int(seed.get("legacy_statement_count", "0")),
            _safe_int(row.get("legacy_statement_count", "0")),
        )
        seed["known_source_count"] = str(known_source_count)
        seed["legacy_statement_count"] = str(legacy_statement_count)
        explicit_registration = seed.get("campaign_domain_registered", "").strip() in {
            "1",
            "true",
            "yes",
        }
        if _supports_campaign_domain_derivation(
            domain=campaign_domain,
            candidate_slug_value=seed["candidate_slug"],
            source_types=[
                row.get("source_type", "").strip(),
                row.get("source_type_class", "").strip(),
            ],
            explicit_registration=explicit_registration,
        ):
            seed["campaign_domain_signal"] = "1"
    return sorted(
        [
            row
            for row in grouped.values()
            if row.get("campaign_domain_signal") == "1"
            or row.get("campaign_domain_registered", "").strip() in {"1", "true", "yes"}
        ],
        key=lambda row: (
            -_safe_int(row.get("legacy_statement_count", "0")),
            row.get("election_date", ""),
            -_safe_int(row.get("known_source_count", "0")),
            row.get("candidate_name", "").casefold(),
            row.get("campaign_domain", ""),
        ),
    )


def _campaign_domain_seed_complete(
    seed: dict[str, str],
    status_by_seed: dict[str, dict[str, str]],
) -> bool:
    status = status_by_seed.get(seed["discovery_seed_id"])
    if status is None:
        return False
    return (
        status.get("live_search_status", "") in DISCOVERY_COMPLETED_STATUSES
        and status.get("archive_search_status", "") in DISCOVERY_COMPLETED_STATUSES
    )


def _seed_has_unattempted_stage(
    seed: dict[str, str],
    status_by_seed: dict[str, dict[str, str]],
) -> bool:
    status = status_by_seed.get(seed["discovery_seed_id"])
    if status is None:
        return True
    return any(
        status.get(field, "") in {"", "not_searched"}
        for field in ("live_search_status", "archive_search_status")
    )


def _seed_has_retryable_stage(
    seed: dict[str, str],
    status_by_seed: dict[str, dict[str, str]],
) -> bool:
    status = status_by_seed.get(seed["discovery_seed_id"])
    if status is None:
        return False
    return _should_retry_existing_stage(status, "live") or _should_retry_existing_stage(
        status, "archive"
    )


def _should_attempt_stage(status_row: dict[str, str], stage: str) -> bool:
    stage_status = status_row.get(_stage_status_field(stage), "")
    if stage_status in DISCOVERY_COMPLETED_STATUSES:
        return False
    if stage_status in {"", "not_searched"}:
        return True
    return _should_retry_existing_stage(status_row, stage)


def _should_retry_existing_stage(status_row: dict[str, str], stage: str) -> bool:
    stage_status = status_row.get(_stage_status_field(stage), "")
    if stage_status != "error":
        return False
    if _safe_int(status_row.get(_stage_retry_field(stage), "0")) >= 1:
        return False
    return _is_transient_discovery_error(status_row.get(_stage_error_field(stage), ""))


def _stage_status_field(stage: str) -> str:
    return f"{stage}_search_status"


def _stage_error_field(stage: str) -> str:
    return f"{stage}_error"


def _stage_retry_field(stage: str) -> str:
    return f"{stage}_retry_count"


def _attempted_campaign_domains(
    seeds: Sequence[dict[str, str]],
    status_by_seed: dict[str, dict[str, str]],
) -> set[str]:
    return {
        seed["campaign_domain"]
        for seed in seeds
        if seed["discovery_seed_id"] in status_by_seed
    }


def _select_campaign_domain_batch(
    pending_seeds: Sequence[dict[str, str]],
    max_domains: int,
    *,
    excluded_domains: set[str] | None = None,
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    seen_domains: set[str] = set(excluded_domains or ())
    for seed in pending_seeds:
        domain = seed["campaign_domain"]
        if domain in seen_domains:
            continue
        selected.append(seed)
        seen_domains.add(domain)
        if len(selected) >= max_domains:
            break
    return selected


def _is_transient_discovery_error(error_text: str) -> bool:
    lowered = error_text.casefold()
    if not lowered:
        return False
    return any(
        token in lowered
        for token in (
            "429",
            "500",
            "502",
            "503",
            "504",
            "connection reset",
            "connection refused",
            "temporarily unavailable",
            "temporary failure",
            "timed out",
            "timeout",
        )
    )


def _new_campaign_domain_status(seed: dict[str, str]) -> dict[str, str]:
    return {
        "discovery_seed_id": seed["discovery_seed_id"],
        "queue_id": seed.get("queue_id", ""),
        "race_id": seed.get("race_id", ""),
        "candidate_slug": seed.get("candidate_slug", ""),
        "candidate_name": seed.get("candidate_name", ""),
        "role": seed.get("role", ""),
        "election_date": seed.get("election_date", ""),
        "campaign_domain": seed.get("campaign_domain", ""),
        "known_source_count": seed.get("known_source_count", "0"),
        "legacy_statement_count": seed.get("legacy_statement_count", "0"),
        "live_search_status": "not_searched",
        "live_searched_at": "",
        "live_error": "",
        "live_retry_count": "0",
        "archive_search_status": "not_searched",
        "archive_searched_at": "",
        "archive_error": "",
        "archive_retry_count": "0",
    }


def _discover_live_campaign_domain_urls(
    seed: dict[str, str],
    *,
    fetcher: Callable[[str], dict[str, str]],
    max_live_pages: int,
    max_urls: int,
) -> tuple[list[dict[str, str]], str, str]:
    root_url = f"https://{seed['campaign_domain']}/"
    discovered: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    fetched_pages: set[str] = set()
    homepage = fetcher(root_url)
    homepage_html = ""
    if homepage.get("ok") == "true":
        homepage_html = homepage.get("text", "")
        _collect_html_discovery_urls(
            discovered,
            homepage_html,
            base_url=homepage.get("final_url", root_url) or root_url,
            seed=seed,
            discovery_method="homepage_link",
            provenance_url=homepage.get("final_url", root_url) or root_url,
            provenance_date=homepage.get("retrieved_at", ""),
            max_urls=max_urls,
        )
    else:
        errors.append(f"homepage: {homepage.get('error', 'unknown error')}")
    for sitemap_url in _candidate_sitemap_urls(root_url):
        response = fetcher(sitemap_url)
        if response.get("ok") != "true":
            errors.append(f"{sitemap_url}: {response.get('error', 'unknown error')}")
            continue
        for entry in _parse_sitemap_entries(response.get("text", "")):
            if len(discovered) >= max_urls:
                break
            loc = _same_domain_absolute_url(root_url, entry.get("loc", ""))
            if not loc:
                continue
            if loc.casefold().endswith(".xml"):
                nested = fetcher(loc)
                if nested.get("ok") != "true":
                    errors.append(f"{loc}: {nested.get('error', 'unknown error')}")
                    continue
                for nested_entry in _parse_sitemap_entries(nested.get("text", "")):
                    if len(discovered) >= max_urls:
                        break
                    nested_loc = _same_domain_absolute_url(root_url, nested_entry.get("loc", ""))
                    if not nested_loc:
                        continue
                    _maybe_add_discovered_url(
                        discovered,
                        seed=seed,
                        url=nested_loc,
                        discovery_stage="live",
                        discovery_method="sitemap",
                        provenance_url=loc,
                        provenance_date=nested_entry.get("lastmod", "") or entry.get("lastmod", ""),
                    )
                continue
            _maybe_add_discovered_url(
                discovered,
                seed=seed,
                url=loc,
                discovery_stage="live",
                discovery_method="sitemap",
                provenance_url=sitemap_url,
                provenance_date=entry.get("lastmod", ""),
            )
    for feed_url in _candidate_feed_urls(root_url):
        response = fetcher(feed_url)
        if response.get("ok") != "true":
            continue
        for entry in _parse_feed_entries(response.get("text", "")):
            if len(discovered) >= max_urls:
                break
            link = _same_domain_absolute_url(root_url, entry.get("url", ""))
            if not link:
                continue
            _maybe_add_discovered_url(
                discovered,
                seed=seed,
                url=link,
                discovery_stage="live",
                discovery_method="feed",
                provenance_url=feed_url,
                provenance_date=entry.get("published_at", ""),
            )
    relevant_pages = sorted(
        {
            row["source_url"]
            for row in discovered.values()
            if not row["source_url"].casefold().endswith(".pdf")
        }
    )
    for page_url in relevant_pages:
        if len(fetched_pages) >= max_live_pages or len(discovered) >= max_urls:
            break
        if page_url in fetched_pages:
            continue
        fetched_pages.add(page_url)
        response = fetcher(page_url)
        if response.get("ok") != "true":
            errors.append(f"{page_url}: {response.get('error', 'unknown error')}")
            continue
        _collect_html_discovery_urls(
            discovered,
            response.get("text", ""),
            base_url=response.get("final_url", page_url) or page_url,
            seed=seed,
            discovery_method="same_domain_link",
            provenance_url=page_url,
            provenance_date=response.get("retrieved_at", ""),
            max_urls=max_urls,
        )
    if homepage_html and len(discovered) < max_urls:
        _collect_html_discovery_urls(
            discovered,
            homepage_html,
            base_url=homepage.get("final_url", root_url) or root_url,
            seed=seed,
            discovery_method="same_domain_link",
            provenance_url=homepage.get("final_url", root_url) or root_url,
            provenance_date=homepage.get("retrieved_at", ""),
            max_urls=max_urls,
        )
    status = "complete" if discovered or len(errors) < 3 else "error"
    return list(discovered.values()), status, " | ".join(errors[:12])


def _discover_archive_campaign_domain_urls(
    seed: dict[str, str],
    *,
    cdx_fetcher: Callable[[str, date, date, int], list[dict[str, str]]],
    max_urls: int,
    limit: int,
) -> tuple[list[dict[str, str]], str, str]:
    window = campaign_window_for_election(seed["election_date"])
    try:
        entries = cdx_fetcher(seed["campaign_domain"], window.start, window.end, limit)
    except (DocumentCorpusError, OSError, TimeoutError, ValueError, urllib.error.URLError) as error:
        return [], "error", f"wayback: {type(error).__name__}: {error}"
    discovered: dict[str, dict[str, str]] = {}
    for entry in entries:
        if len(discovered) >= max_urls:
            break
        original_url = entry.get("original", "")
        timestamp = entry.get("timestamp", "")
        if not original_url or not timestamp:
            continue
        _maybe_add_discovered_url(
            discovered,
            seed=seed,
            url=original_url,
            archive_timestamp=timestamp,
            discovery_stage="archive",
            discovery_method="wayback_cdx",
            provenance_url=f"https://web.archive.org/cdx/search/cdx?url={seed['campaign_domain']}/*",
            provenance_date=timestamp,
        )
    return list(discovered.values()), "complete", ""


def _append_campaign_discovery_queue_rows(
    queue_rows: Sequence[dict[str, str]],
    discovery_rows: Sequence[dict[str, str]],
) -> tuple[list[dict[str, str]], int]:
    updated_rows = [dict(row) for row in queue_rows]
    row_by_key = {
        _queue_candidate_source_key(row): row
        for row in updated_rows
        if row.get("source_url")
    }
    appended = 0
    for discovery in discovery_rows:
        key = (
            discovery.get("race_id", ""),
            discovery.get("candidate_slug", ""),
            discovery.get("role", ""),
            canonical_source_url(discovery.get("source_url", "")),
        )
        existing = row_by_key.get(key)
        seed_kind = (
            "campaign_archive_discovery"
            if discovery.get("discovery_stage") == "archive"
            else "campaign_live_discovery"
        )
        if existing is not None:
            existing["seed_kinds"] = _merge_pipe_lists(existing.get("seed_kinds", ""), seed_kind)
            existing["seed_priority"] = str(
                min(
                    _safe_int(existing.get("seed_priority", str(QUEUE_SEED_PRIORITY[seed_kind]))),
                    QUEUE_SEED_PRIORITY[seed_kind],
                )
            )
            if discovery.get("archive_url") and not existing.get("archive_url"):
                existing["archive_url"] = discovery["archive_url"]
            if discovery.get("campaign_domain") and not existing.get("campaign_domain"):
                existing["campaign_domain"] = discovery["campaign_domain"]
            if discovery.get("discovery_method"):
                existing["discovery_method"] = _merge_pipe_lists(
                    existing.get("discovery_method", ""),
                    discovery["discovery_method"],
                )
            if discovery.get("discovery_provenance_url"):
                existing["discovery_provenance_url"] = _merge_pipe_lists(
                    existing.get("discovery_provenance_url", ""),
                    discovery["discovery_provenance_url"],
                )
            if discovery.get("archive_timestamp") and not existing.get("archive_timestamp"):
                existing["archive_timestamp"] = discovery["archive_timestamp"]
            continue
        source_type_class = discovery.get("source_type_class", "other") or "other"
        note = (
            f"Discovered via {discovery.get('discovery_method', '')} "
            f"from {discovery.get('discovery_provenance_url', '')}"
        ).strip()
        if discovery.get("archive_timestamp"):
            note = f"{note} ({discovery['archive_timestamp']})".strip()
        new_row = {
            "document_id": candidate_document_id(
                discovery.get("candidate_name", ""),
                discovery.get("race_id", ""),
                discovery.get("source_url", ""),
                source_type_class,
            ),
            "queue_id": discovery.get("queue_id", ""),
            "race_id": discovery.get("race_id", ""),
            "candidate_slug": discovery.get("candidate_slug", ""),
            "candidate_name": discovery.get("candidate_name", ""),
            "role": discovery.get("role", ""),
            "election_date": discovery.get("election_date", ""),
            "publication_date": _truncate_date(discovery.get("discovery_provenance_date", "")),
            "source_type": source_type_class,
            "source_type_class": source_type_class,
            "source_url": discovery.get("source_url", ""),
            "archive_url": discovery.get("archive_url", ""),
            "campaign_domain": discovery.get("campaign_domain", ""),
            "official_election_source": "",
            "seed_kinds": seed_kind,
            "seed_priority": str(QUEUE_SEED_PRIORITY[seed_kind]),
            "source_record_ids": "",
            "legacy_locators": "",
            "known_source_count": discovery.get("known_source_count", "0"),
            "legacy_statement_count": discovery.get("legacy_statement_count", "0"),
            "collection_status": "not_collected",
            "metadata_status": "not_searched",
            "analysis_segment_count": "0",
            "substantive_segment_count": "0",
            "notes": note,
            "discovery_seed_id": discovery.get("discovery_seed_id", ""),
            "discovery_stage": discovery.get("discovery_stage", ""),
            "discovery_method": discovery.get("discovery_method", ""),
            "discovery_provenance_url": discovery.get("discovery_provenance_url", ""),
            "discovery_provenance_date": discovery.get("discovery_provenance_date", ""),
            "archive_timestamp": discovery.get("archive_timestamp", ""),
        }
        updated_rows.append(new_row)
        row_by_key[key] = new_row
        appended += 1
    updated_rows.sort(
        key=lambda row: (
            row.get("election_date", ""),
            row.get("candidate_name", "").casefold(),
            row.get("role", ""),
            _safe_int(row.get("seed_priority", "999")),
            row.get("source_url", ""),
        )
    )
    return updated_rows, appended


def _queue_candidate_source_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        row.get("race_id", "").strip(),
        row.get("candidate_slug", "").strip() or candidate_slug(row.get("candidate_name", "")),
        row.get("role", "").strip(),
        canonical_source_url(row.get("source_url", "")),
    )


def _maybe_add_discovered_url(
    discovered: dict[str, dict[str, str]],
    *,
    seed: dict[str, str],
    url: str,
    discovery_stage: str,
    discovery_method: str,
    provenance_url: str,
    provenance_date: str,
    archive_timestamp: str = "",
) -> None:
    canonical_url = canonical_source_url(url)
    if not _is_candidate_document_discovery_url(canonical_url):
        return
    source_type_class = _classify_discovered_source_type(canonical_url)
    if source_type_class not in DISCOVERY_CANDIDATE_SOURCE_TYPES:
        return
    archive_url = ""
    if archive_timestamp:
        archive_url = f"https://web.archive.org/web/{archive_timestamp}/{canonical_url}"
    key = (
        seed["discovery_seed_id"],
        discovery_stage,
        canonical_url,
    )
    existing = discovered.get(key)
    row = {
        "discovery_result_id": stable_hash(
            seed["discovery_seed_id"],
            discovery_stage,
            canonical_url,
        ),
        "discovery_seed_id": seed["discovery_seed_id"],
        "queue_id": seed.get("queue_id", ""),
        "race_id": seed.get("race_id", ""),
        "candidate_slug": seed.get("candidate_slug", ""),
        "candidate_name": seed.get("candidate_name", ""),
        "role": seed.get("role", ""),
        "election_date": seed.get("election_date", ""),
        "campaign_domain": seed.get("campaign_domain", ""),
        "known_source_count": seed.get("known_source_count", "0"),
        "legacy_statement_count": seed.get("legacy_statement_count", "0"),
        "source_url": canonical_url,
        "archive_url": archive_url,
        "archive_timestamp": archive_timestamp,
        "source_type_class": source_type_class,
        "discovery_stage": discovery_stage,
        "discovery_method": discovery_method,
        "discovery_provenance_url": provenance_url,
        "discovery_provenance_date": provenance_date,
    }
    if existing is None:
        discovered[key] = row
        return
    if archive_url and not existing.get("archive_url"):
        existing["archive_url"] = archive_url
    if archive_timestamp and not existing.get("archive_timestamp"):
        existing["archive_timestamp"] = archive_timestamp
    if provenance_date and not existing.get("discovery_provenance_date"):
        existing["discovery_provenance_date"] = provenance_date
    existing["discovery_method"] = _merge_pipe_lists(
        existing.get("discovery_method", ""),
        discovery_method,
    )
    existing["discovery_provenance_url"] = _merge_pipe_lists(
        existing.get("discovery_provenance_url", ""),
        provenance_url,
    )


def _collect_html_discovery_urls(
    discovered: dict[tuple[str, str, str], dict[str, str]],
    html: str,
    *,
    base_url: str,
    seed: dict[str, str],
    discovery_method: str,
    provenance_url: str,
    provenance_date: str,
    max_urls: int,
) -> None:
    parser = _DiscoveryLinkParser()
    parser.feed(html)
    for href in parser.links:
        if len(discovered) >= max_urls:
            return
        absolute_url = _same_domain_absolute_url(base_url, href)
        if not absolute_url:
            continue
        _maybe_add_discovered_url(
            discovered,
            seed=seed,
            url=absolute_url,
            discovery_stage="live",
            discovery_method=discovery_method,
            provenance_url=provenance_url,
            provenance_date=provenance_date,
        )


def _same_domain_absolute_url(base_url: str, candidate_url: str) -> str:
    if not candidate_url:
        return ""
    absolute_url = urllib.parse.urljoin(base_url, candidate_url)
    parsed_base = urlparse(base_url)
    parsed_url = urlparse(absolute_url)
    if parsed_url.scheme not in {"http", "https"}:
        return ""
    if (parsed_base.hostname or "").removeprefix("www.").casefold() != (
        parsed_url.hostname or ""
    ).removeprefix("www.").casefold():
        return ""
    return canonical_source_url(absolute_url)


def _candidate_sitemap_urls(root_url: str) -> tuple[str, ...]:
    return tuple(urllib.parse.urljoin(root_url, path) for path in DISCOVERY_SITEMAP_PATHS)


def _candidate_feed_urls(root_url: str) -> tuple[str, ...]:
    return tuple(urllib.parse.urljoin(root_url, path) for path in DISCOVERY_FEED_PATHS)


def _parse_sitemap_entries(value: str) -> list[dict[str, str]]:
    entries = []
    for block in re.findall(
        r"<(?:url|sitemap)\b[^>]*>.*?</(?:url|sitemap)>",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        loc_match = re.search(r"<loc>\s*(.*?)\s*</loc>", block, flags=re.IGNORECASE | re.DOTALL)
        if not loc_match:
            continue
        lastmod_match = re.search(
            r"<lastmod>\s*(.*?)\s*</lastmod>",
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )
        entries.append(
            {
                "loc": urllib.parse.unquote(loc_match.group(1).strip()),
                "lastmod": lastmod_match.group(1).strip() if lastmod_match else "",
            }
        )
    return entries


def _parse_feed_entries(value: str) -> list[dict[str, str]]:
    entries = []
    for block in re.findall(
        r"<(?:item|entry)\b[^>]*>.*?</(?:item|entry)>",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        link_match = re.search(
            r"<link>\s*(.*?)\s*</link>",
            block,
            flags=re.IGNORECASE | re.DOTALL,
        ) or re.search(
            r"<link[^>]*href=['\"](.*?)['\"]",
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not link_match:
            continue
        date_match = re.search(
            r"<(?:pubDate|updated|published)>\s*(.*?)\s*</(?:pubDate|updated|published)>",
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )
        entries.append(
            {
                "url": urllib.parse.unquote(link_match.group(1).strip()),
                "published_at": date_match.group(1).strip() if date_match else "",
            }
        )
    return entries


def _is_candidate_document_discovery_url(value: str) -> bool:
    parsed = urlparse(value)
    path = urllib.parse.unquote(parsed.path).casefold()
    if not path or path == "/":
        return False
    if path.endswith(
        (".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".xml", ".css", ".js")
    ):
        return False
    if path in {"/feed", "/comments/feed"} or path.startswith("/comments/feed/"):
        return False
    if path.startswith(("/wp-content/", "/wp-includes/")):
        return False
    if any(
        term in path
        for term in (
            "privacy-policy",
            "privacy_policy",
            "terms-of-service",
            "terms_of_service",
            "cookie-policy",
            "cookie_policy",
        )
    ):
        return False
    if any(hint in path for hint in DISCOVERY_PATH_HINTS):
        return True
    filename = path.rsplit("/", 1)[-1]
    return filename.endswith(".pdf") and any(hint in filename for hint in DISCOVERY_PATH_HINTS)


def _classify_discovered_source_type(value: str) -> str:
    path = urllib.parse.unquote(urlparse(value).path).casefold()
    if "questionnaire" in path or re.search(r"/qa(?:/|$|-)|q-and-a|q&a", path):
        return "questionnaire"
    if any(term in path for term in ("issues", "issue", "platform", "policy", "policies", "agenda", "priorities")):
        return "policy_page"
    if any(term in path for term in ("press", "release", "releases", "news", "announcement")):
        return "press_release"
    if any(term in path for term in ("speech", "speeches", "remarks")):
        return "speech"
    if any(term in path for term in ("statement", "statements")):
        return "statement"
    return "campaign_page"


def _is_candidate_specific_campaign_domain(
    domain: str,
    candidate_slug_value: str,
    *,
    explicit_registration: bool = False,
) -> bool:
    lowered = domain.casefold()
    if not explicit_registration and lowered in NON_CAMPAIGN_HOSTS:
        return False
    if not explicit_registration and (
        lowered.endswith(".gov")
        or any(term in lowered for term in NON_GENUINE_CAMPAIGN_DOMAIN_TERMS)
    ):
        return False
    if explicit_registration:
        return True
    tokens = [token for token in candidate_slug_value.split("-") if len(token) >= 4]
    return bool(tokens) and any(token in lowered for token in tokens)


def _fetch_discovery_document(url: str) -> dict[str, str]:
    retrieved_at = datetime.now(UTC).isoformat()
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xml,text/xml,application/rss+xml,application/atom+xml,text/plain;q=0.8,*/*;q=0.2",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(2_000_000)
            content_type = response.headers.get_content_type()
            charset = response.headers.get_content_charset() or "utf-8"
            text = body.decode(charset, "replace")
            return {
                "ok": "true",
                "text": text,
                "content_type": content_type,
                "final_url": response.geturl(),
                "retrieved_at": retrieved_at,
                "error": "",
            }
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        return {
            "ok": "false",
            "text": "",
            "content_type": "",
            "final_url": "",
            "retrieved_at": retrieved_at,
            "error": f"{type(error).__name__}: {error}",
        }


def _query_wayback_cdx(
    domain: str,
    start_date: date,
    end_date: date,
    limit: int,
) -> list[dict[str, str]]:
    query = urllib.parse.urlencode(
        {
            "url": f"{domain}/*",
            "from": start_date.strftime("%Y%m%d"),
            "to": end_date.strftime("%Y%m%d"),
            "output": "json",
            "fl": "timestamp,original,statuscode,mimetype",
            "filter": "statuscode:200",
            "collapse": "original",
            "limit": str(limit),
        }
    )
    request = urllib.request.Request(
        f"https://web.archive.org/cdx/search/cdx?{query}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/plain;q=0.8,*/*;q=0.2"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8", "replace"))
    if not isinstance(payload, list) or not payload:
        return []
    if isinstance(payload[0], list):
        header = [str(value) for value in payload[0]]
        return [
            {
                header[index]: str(value)
                for index, value in enumerate(row)
                if index < len(header)
            }
            for row in payload[1:]
            if isinstance(row, list)
        ]
    results = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        results.append({str(key): str(value) for key, value in row.items()})
    return results


def _discovered_url_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        row.get("discovery_seed_id", ""),
        row.get("discovery_stage", ""),
        canonical_source_url(row.get("source_url", "")),
    )


def _write_campaign_domain_status_rows(path: Path, rows: Sequence[dict[str, str]]) -> None:
    write_csv(
        path,
        sorted(
            rows,
            key=lambda row: (
                row.get("election_date", ""),
                row.get("candidate_name", "").casefold(),
                row.get("role", ""),
                row.get("campaign_domain", ""),
            ),
        ),
        [
            "discovery_seed_id",
            "queue_id",
            "race_id",
            "candidate_slug",
            "candidate_name",
            "role",
            "election_date",
            "campaign_domain",
            "known_source_count",
            "legacy_statement_count",
            "live_search_status",
            "live_searched_at",
            "live_error",
            "live_retry_count",
            "archive_search_status",
            "archive_searched_at",
            "archive_error",
            "archive_retry_count",
        ],
    )


def _write_campaign_domain_discovered_rows(path: Path, rows: Sequence[dict[str, str]]) -> None:
    write_csv(
        path,
        sorted(
            rows,
            key=lambda row: (
                row.get("election_date", ""),
                row.get("candidate_name", "").casefold(),
                row.get("role", ""),
                row.get("source_url", ""),
            ),
        ),
        [
            "discovery_result_id",
            "discovery_seed_id",
            "queue_id",
            "race_id",
            "candidate_slug",
            "candidate_name",
            "role",
            "election_date",
            "campaign_domain",
            "known_source_count",
            "legacy_statement_count",
            "source_url",
            "archive_url",
            "archive_timestamp",
            "source_type_class",
            "discovery_stage",
            "discovery_method",
            "discovery_provenance_url",
            "discovery_provenance_date",
        ],
    )


def _merge_pipe_lists(*values: str) -> str:
    items: list[str] = []
    seen = set()
    for value in values:
        for item in (part.strip() for part in value.split(" | ")):
            if not item or item in seen:
                continue
            seen.add(item)
            items.append(item)
    return " | ".join(items)


def _safe_int(value: str) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def _truncate_date(value: str) -> str:
    return value[:10] if len(value) >= 10 else value


@dataclass(frozen=True)
class _AnalysisSourceUnit:
    source_kind: str
    paragraph_start: int
    paragraph_end: int
    sentence_start: int
    sentence_end: int
    source_locator_start: str
    source_locator_end: str
    text: str
    token_count: int


def _load_candidate_document_queue(path: Path) -> list[dict[str, str]]:
    return read_csv(path)


def _write_candidate_document_queue(
    path: Path,
    rows: Sequence[dict[str, str]],
) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    if not fieldnames:
        fieldnames = [
            "document_id",
            "queue_id",
            "race_id",
            "candidate_slug",
            "candidate_name",
            "role",
            "election_date",
            "publication_date",
            "source_type",
            "source_type_class",
            "source_url",
            "archive_url",
            "campaign_domain",
            "official_election_source",
            "seed_kinds",
            "seed_priority",
            "source_record_ids",
            "legacy_locators",
            "known_source_count",
            "legacy_statement_count",
            "collection_status",
            "metadata_status",
            "analysis_segment_count",
            "substantive_segment_count",
            "notes",
            "discovery_seed_id",
            "discovery_stage",
            "discovery_method",
            "discovery_provenance_url",
            "discovery_provenance_date",
            "archive_timestamp",
        ]
    write_csv(path, list(rows), fieldnames)


def _load_existing_csv_by_key(path: Path, key: str) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    return {row.get(key, ""): row for row in read_csv(path) if row.get(key, "")}


def _load_existing_jsonl_by_key(path: Path, key: str) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    rows: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            row = json.loads(line)
            row_key = str(row.get(key, ""))
            if row_key:
                rows[row_key] = {str(name): str(value) for name, value in row.items()}
    return rows


def _write_jsonl(path: Path, rows: Sequence[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _load_raw_manifest_index(path: Path) -> _RawManifestIndex:
    index = _RawManifestIndex(by_document_id={}, by_canonical_url={})
    if not path.exists():
        return index
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            row = json.loads(line)
            normalized_row = {str(name): str(value) for name, value in row.items()}
            _index_raw_manifest_row(index, normalized_row)
    return index


def _index_raw_manifest_row(index: _RawManifestIndex, row: dict[str, str]) -> None:
    document_id = row.get("document_id", "").strip()
    if document_id:
        index.by_document_id[document_id] = row
    for key in _manifest_canonical_keys(row):
        index.by_canonical_url[key] = row


def _manifest_canonical_keys(row: dict[str, str]) -> tuple[str, ...]:
    keys: list[str] = []
    for raw_value in (
        row.get("canonical_source_url", ""),
        row.get("archive_url", ""),
        row.get("canonical_final_url", ""),
        row.get("source_url", ""),
        row.get("final_url", ""),
    ):
        value = raw_value.strip()
        if not value:
            continue
        try:
            canonical_value = canonical_source_url(value)
        except DocumentCorpusError:
            continue
        if canonical_value not in keys:
            keys.append(canonical_value)
    return tuple(keys)


def _resolve_raw_capture(
    job: CandidateDocumentJob,
    manifest_index: _RawManifestIndex,
    fetcher: Callable[[str, str], RawDocumentCapture],
) -> tuple[RawDocumentCapture, str, Path | None]:
    seen_rows: set[int] = set()
    manifest_rows: list[dict[str, str]] = []
    for candidate_row in (
        manifest_index.by_document_id.get(job.document_id),
        *(manifest_index.by_canonical_url.get(key) for key in _job_manifest_lookup_keys(job)),
    ):
        if candidate_row is None:
            continue
        identity = id(candidate_row)
        if identity in seen_rows:
            continue
        seen_rows.add(identity)
        manifest_rows.append(candidate_row)
    for manifest_row in manifest_rows:
        raw_path = _path_from_row(manifest_row.get("raw_path", ""))
        if raw_path and raw_path.exists():
            content = raw_path.read_bytes()
            sha256 = hashlib.sha256(content).hexdigest()
            expected_sha = manifest_row.get("sha256", "").strip()
            if not expected_sha or sha256 == expected_sha:
                manifest_source_url = manifest_row.get("source_url", "").strip() or job.source_url
                manifest_final_url = manifest_row.get("final_url", "").strip() or manifest_source_url
                return (
                    RawDocumentCapture(
                        document_id=job.document_id,
                        source_url=manifest_source_url,
                        final_url=manifest_final_url,
                        retrieved_at=manifest_row.get("retrieved_at", ""),
                        content_type=manifest_row.get("content_type", "application/octet-stream"),
                        encoding=manifest_row.get("encoding", "utf-8") or "utf-8",
                        content_bytes=content,
                        byte_count=len(content),
                        sha256=sha256,
                    ),
                    "reused_raw",
                    raw_path,
                )
    try:
        return fetcher(job.document_id, job.source_url), "fetched", None
    except RawFetchError:
        if not job.archive_url:
            raise
        archive_capture = fetcher(job.document_id, job.archive_url)
        return (
            RawDocumentCapture(
                document_id=archive_capture.document_id,
                source_url=job.source_url,
                final_url=archive_capture.final_url,
                retrieved_at=archive_capture.retrieved_at,
                content_type=archive_capture.content_type,
                encoding=archive_capture.encoding,
                content_bytes=archive_capture.content_bytes,
                byte_count=archive_capture.byte_count,
                sha256=archive_capture.sha256,
            ),
            "fetched",
            None,
        )


def _job_manifest_lookup_keys(job: CandidateDocumentJob) -> tuple[str, ...]:
    keys = [canonical_source_url(job.source_url)]
    if job.archive_url:
        keys.append(canonical_source_url(job.archive_url))
    deduped: list[str] = []
    for key in keys:
        if key not in deduped:
            deduped.append(key)
    return tuple(deduped)


def _shared_source_candidates(
    queue_rows: Sequence[dict[str, str]],
) -> dict[str, set[tuple[str, str, str]]]:
    grouped: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    for row in queue_rows:
        source_url = (
            row.get("source_url", "").strip()
            or row.get("seed_url", "").strip()
            or row.get("reference_url", "").strip()
        )
        candidate_name = row.get("candidate_name", "").strip()
        race_id = row.get("race_id", "").strip()
        role = row.get("role", "").strip()
        if not source_url or not candidate_name or not race_id or not role:
            continue
        try:
            grouped[canonical_source_url(source_url)].add(
                (race_id, _identity_name(candidate_name), role)
            )
        except DocumentCorpusError:
            continue
    return grouped


def _scope_shared_document_for_candidate(
    job: CandidateDocumentJob,
    extracted: ExtractedDocument,
) -> tuple[ExtractedDocument, str]:
    locators = [value.strip() for value in job.legacy_locators.split(" | ") if value.strip()]
    if not locators:
        return _shared_document_unscoped(extracted), "shared_document_unscoped"
    paragraph_indices: set[int] = set()
    for locator in locators:
        resolved = _resolve_locator_paragraphs(locator, extracted.paragraphs)
        if not resolved:
            return _shared_document_unscoped(extracted), "shared_document_unscoped"
        paragraph_indices.update(resolved)
    scoped_paragraphs = tuple(
        paragraph
        for paragraph in extracted.paragraphs
        if paragraph.index in paragraph_indices
    )
    if not scoped_paragraphs:
        return _shared_document_unscoped(extracted), "shared_document_unscoped"
    scoped_sentences = tuple(
        sentence
        for sentence in extracted.sentences
        if _sentence_paragraph_index(sentence) in paragraph_indices
    )
    scoped_text = "\n\n".join(paragraph.text for paragraph in scoped_paragraphs)
    return (
        ExtractedDocument(
            document_id=extracted.document_id,
            source_url=extracted.source_url,
            final_url=extracted.final_url,
            retrieved_at=extracted.retrieved_at,
            content_type=extracted.content_type,
            title=extracted.title,
            text=scoped_text,
            text_sha256=_sha256_text(scoped_text),
            coverage_status="found_unverified",
            extractor=extracted.extractor,
            paragraphs=scoped_paragraphs,
            sentences=scoped_sentences,
        ),
        "extracted",
    )


def _shared_document_unscoped(extracted: ExtractedDocument) -> ExtractedDocument:
    return ExtractedDocument(
        document_id=extracted.document_id,
        source_url=extracted.source_url,
        final_url=extracted.final_url,
        retrieved_at=extracted.retrieved_at,
        content_type=extracted.content_type,
        title=extracted.title,
        text="",
        text_sha256=_sha256_text(""),
        coverage_status="shared_document_unscoped",
        extractor=extracted.extractor,
        paragraphs=(),
        sentences=(),
    )


def _resolve_locator_paragraphs(
    locator: str,
    paragraphs: Sequence[TextSegment],
) -> tuple[int, ...]:
    normalized_locator = locator.strip()
    if not normalized_locator:
        return ()
    time_match = re.fullmatch(
        r"time\s+([0-9:,]+)\s*(?:-|-->|to)\s*([0-9:,]+)",
        normalized_locator,
        re.IGNORECASE,
    )
    if time_match:
        start = _locator_time_value(time_match.group(1))
        end = _locator_time_value(time_match.group(2))
        matches = []
        for paragraph in paragraphs:
            paragraph_range = _paragraph_time_range(paragraph.locator)
            if paragraph_range is None:
                continue
            paragraph_start, paragraph_end = paragraph_range
            if paragraph_end >= start and paragraph_start <= end:
                matches.append(paragraph.index)
        return tuple(matches)
    range_match = re.fullmatch(
        r"range:\s*(.+?)\s*=>\s*(.+)",
        normalized_locator,
        re.IGNORECASE,
    )
    if range_match:
        start_indexes = [
            paragraph.index
            for paragraph in paragraphs
            if range_match.group(1).casefold() in paragraph.text.casefold()
        ]
        end_indexes = [
            paragraph.index
            for paragraph in paragraphs
            if range_match.group(2).casefold() in paragraph.text.casefold()
        ]
        if len(start_indexes) == 1 and len(end_indexes) == 1 and start_indexes[0] < end_indexes[0]:
            return tuple(range(start_indexes[0], end_indexes[0]))
        return ()
    from_match = re.fullmatch(r"from:\s*(.+)", normalized_locator, re.IGNORECASE)
    if from_match:
        start_indexes = [
            paragraph.index
            for paragraph in paragraphs
            if from_match.group(1).casefold() in paragraph.text.casefold()
        ]
        if len(start_indexes) == 1:
            return tuple(range(start_indexes[0], len(paragraphs) + 1))
        return ()
    paragraph_match = re.search(r"\bparagraph\s+(\d+)\b", normalized_locator, re.IGNORECASE)
    if paragraph_match:
        return (int(paragraph_match.group(1)),)
    page_match = re.search(
        r"\b(?:pdf\s+)?page(?:s)?\s+(\d+)(?:\s*-\s*(\d+))?\b",
        normalized_locator,
        re.IGNORECASE,
    )
    if page_match:
        start = int(page_match.group(1))
        end = int(page_match.group(2) or start)
        matches = []
        for paragraph in paragraphs:
            lowered = paragraph.text.casefold()
            for page_number in range(start, end + 1):
                if f"[pdf page {page_number}]".casefold() in lowered:
                    matches.append(paragraph.index)
                    break
        return tuple(matches)
    lowered_locator = normalized_locator.casefold()
    matches = [
        paragraph.index
        for paragraph in paragraphs
        if lowered_locator in paragraph.text.casefold()
    ]
    if len(matches) == 1:
        return (matches[0],)
    return ()


def _locator_time_value(value: str) -> int:
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})(?:,(\d{1,3}))?", value.strip())
    if not match:
        raise DocumentCorpusError(f"invalid time locator: {value}")
    hours, minutes, seconds, millis = match.groups()
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(seconds) * 1_000
        + int((millis or "0").ljust(3, "0"))
    )


def _paragraph_time_range(locator: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"time\s+([0-9:,]+)-([0-9:,]+)", locator.strip(), re.IGNORECASE)
    if not match:
        return None
    return _locator_time_value(match.group(1)), _locator_time_value(match.group(2))


def _sentence_paragraph_index(sentence: TextSegment) -> int:
    match = re.fullmatch(r"paragraph (\d+) sentence (\d+)", sentence.locator)
    return int(match.group(1)) if match else 0


def _normalize_candidate_document_job(row: dict[str, str]) -> CandidateDocumentJob:
    candidate_name = row.get("candidate_name", "").strip()
    race_id = row.get("race_id", "").strip()
    role = row.get("role", "").strip()
    election_date = row.get("election_date", "").strip()
    source_url = (
        row.get("source_url", "").strip()
        or row.get("seed_url", "").strip()
        or row.get("reference_url", "").strip()
    )
    if not candidate_name:
        raise DocumentCorpusError("candidate_name is required")
    if not race_id:
        raise DocumentCorpusError("race_id is required")
    if not role:
        raise DocumentCorpusError("role is required")
    if not election_date:
        raise DocumentCorpusError("election_date is required")
    _coerce_date(election_date)
    source_urls = _split_source_urls(source_url)
    normalized_source_url = (
        source_urls[0] if source_urls else normalize_source_url(source_url)
    )
    source_type = (
        row.get("source_type", "").strip()
        or row.get("source_type_class", "").strip()
        or classify_source_type("", normalized_source_url)
    )
    archive_url = row.get("archive_url", "").strip()
    if archive_url:
        archive_url = normalize_source_url(archive_url)
    publication_date = row.get("publication_date", "").strip() or row.get(
        "published_date", ""
    ).strip() or row.get(
        "effective_date", ""
    ).strip()
    if publication_date:
        _coerce_date(publication_date)
    document_id = row.get("document_id", "").strip() or candidate_document_id(
        candidate_name,
        race_id,
        normalized_source_url,
        source_type,
    )
    return CandidateDocumentJob(
        document_id=document_id,
        queue_id=row.get("queue_id", "").strip(),
        race_id=race_id,
        candidate_name=candidate_name,
        role=role,
        election_date=election_date,
        publication_date=publication_date,
        source_type=source_type,
        source_url=normalized_source_url,
        archive_url=archive_url,
        notes=row.get("notes", "").strip(),
        seed_kind=row.get("seed_kind", "").strip(),
        source_record_id=row.get("source_record_id", "").strip(),
        legacy_locators=row.get("legacy_locators", "").strip(),
        analysis_scope=row.get("analysis_scope", "").strip() or "analysis",
        transcript_text=row.get("transcript_text", "").strip(),
        transcript_title=row.get("transcript_title", "").strip(),
    )


def _split_source_urls(value: str) -> tuple[str, ...]:
    urls: list[str] = []
    for part in re.split(r"\s+\|\s+", value.strip()):
        if not part:
            continue
        try:
            normalized = normalize_source_url(part)
        except DocumentCorpusError:
            continue
        if normalized not in urls:
            urls.append(normalized)
    return tuple(urls)


def _normalized_regather_queue_row(row: dict[str, str]) -> dict[str, str]:
    try:
        job = _normalize_candidate_document_job(row)
    except DocumentCorpusError:
        return dict(row)
    normalized = dict(row)
    normalized["document_id"] = job.document_id
    normalized["source_url"] = job.source_url
    normalized["archive_url"] = job.archive_url
    normalized["source_type"] = job.source_type
    normalized["candidate_name"] = job.candidate_name
    normalized["race_id"] = job.race_id
    normalized["role"] = job.role
    normalized["election_date"] = job.election_date
    normalized["publication_date"] = job.publication_date
    normalized["analysis_scope"] = job.analysis_scope
    normalized["source_type_class"] = (
        row.get("source_type_class", "").strip()
        or classify_source_type(job.source_type, job.source_url)
    )
    return normalized


def _is_completed_document_metadata(
    metadata_row: dict[str, str] | None,
    full_text_row: dict[str, str] | None,
    paragraph_count: int,
    sentence_count: int,
) -> bool:
    if not metadata_row:
        return False
    fetch_status = metadata_row.get("fetch_status", "").strip()
    extraction_status = metadata_row.get("extraction_status", "").strip()
    if fetch_status not in {"fetched", "reused_raw"}:
        return False
    if extraction_status == "media_no_transcript":
        return bool(full_text_row) and (
            full_text_row.get("coverage_status", "").strip() == "media_no_transcript"
        )
    if extraction_status != "extracted" or not full_text_row:
        return False
    if not full_text_row.get("text", "").strip():
        return False
    expected_paragraphs = int(metadata_row.get("paragraph_count", "0") or 0)
    expected_sentences = int(metadata_row.get("sentence_count", "0") or 0)
    if expected_paragraphs <= 0 or expected_sentences <= 0:
        return False
    return paragraph_count == expected_paragraphs and sentence_count == expected_sentences


def _is_completed_queue_row(row: dict[str, str]) -> bool:
    if int(row.get("analysis_segment_count", "0") or 0) > 0:
        return True
    return (
        row.get("collection_status", "").strip() == "media_no_transcript"
        and "media_no_transcript" in row.get("metadata_status", "")
    )


def _is_transcriptless_video_queue_row(row: dict[str, str]) -> bool:
    if row.get("transcript_text", "").strip():
        return False
    source_type_class = row.get("source_type_class", "").strip()
    source_url = (
        row.get("source_url", "").strip()
        or row.get("seed_url", "").strip()
        or row.get("reference_url", "").strip()
    )
    if source_type_class == "video":
        return True
    if not source_url:
        return False
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").removeprefix("www.").casefold()
    if host in VIDEO_HOSTS:
        return True
    return any(parsed.path.casefold().endswith(suffix) for suffix in MEDIA_SUFFIXES)


def _regather_group_key(row: dict[str, str]) -> str:
    source_url = (
        row.get("source_url", "").strip()
        or row.get("seed_url", "").strip()
        or row.get("reference_url", "").strip()
    )
    if not source_url:
        return row.get("document_id", "").strip()
    try:
        return canonical_source_url(source_url)
    except DocumentCorpusError:
        return source_url


def _regather_group_support_key(role: str) -> str:
    return "endorsed" if role.strip() in {"endorsed", "unopposed"} else "opponent"


def _regather_race_group_support(
    queue_rows: Sequence[dict[str, str]],
) -> dict[str, dict[str, bool]]:
    support: dict[str, dict[str, bool]] = defaultdict(
        lambda: {"endorsed": False, "opponent": False}
    )
    for row in queue_rows:
        race_id = row.get("race_id", "").strip()
        if not race_id:
            continue
        substantive_segments = int(row.get("substantive_segment_count", "0") or 0)
        if substantive_segments <= 0:
            continue
        support[race_id][_regather_group_support_key(row.get("role", ""))] = True
    return support


def _regather_row_priority(
    row: dict[str, str],
    *,
    preferred_classes: set[str],
    race_group_support: dict[str, dict[str, bool]],
) -> tuple[int, tuple[str, ...]]:
    score = 0
    reasons: list[str] = []
    election_year = row.get("election_date", "")[:4]
    if election_year == "2016":
        score += 200
        reasons.append("2016_cycle")
    if "known_document" in {
        value.strip() for value in row.get("seed_kinds", "").split(" | ") if value.strip()
    }:
        score += 140
        reasons.append("known_document")
    legacy_statement_count = int(row.get("legacy_statement_count", "0") or 0)
    if legacy_statement_count > 0:
        score += min(legacy_statement_count * 8, 60)
        reasons.append("legacy_quote_support")
    role = row.get("role", "").strip()
    if role == "opponent":
        score += 160
        reasons.append("opponent_side")
    elif role in {"endorsed", "unopposed"}:
        score += 40
        reasons.append("non_opponent_side")
    source_type_class = row.get("source_type_class", "").strip()
    if source_type_class in preferred_classes:
        score += 70
        reasons.append(f"preferred_source_class:{source_type_class}")
    race_id = row.get("race_id", "").strip()
    if race_id:
        support = race_group_support.get(race_id, {"endorsed": False, "opponent": False})
        own_group = _regather_group_support_key(row.get("role", ""))
        other_group = "opponent" if own_group == "endorsed" else "endorsed"
        if support.get(other_group) and not support.get(own_group):
            score += 220
            reasons.append("one_sided_race")
    known_source_count = int(row.get("known_source_count", "0") or 0)
    if known_source_count > 1:
        score += min((known_source_count - 1) * 3, 18)
        reasons.append("multiple_known_sources")
    return score, tuple(reasons)


def _regather_row_sort_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        row.get("election_date", ""),
        row.get("candidate_name", "").casefold(),
        row.get("role", ""),
        row.get("document_id", ""),
    )


def _regather_group_sort_key(
    rows: Sequence[dict[str, str]],
    *,
    preferred_classes: set[str],
    race_group_support: dict[str, dict[str, bool]],
) -> tuple[int, int, int, str, str, str]:
    scored_rows = [
        _regather_row_priority(
            row,
            preferred_classes=preferred_classes,
            race_group_support=race_group_support,
        )
        for row in rows
    ]
    top_score = max(score for score, _ in scored_rows)
    duplicate_bonus = min(len(rows) - 1, 24)
    first_row = min(rows, key=_regather_row_sort_key)
    top_seed_priority = min(int(row.get("seed_priority", "999") or 999) for row in rows)
    return (
        -(top_score + duplicate_bonus),
        top_seed_priority,
        first_row.get("election_date", ""),
        first_row.get("candidate_name", "").casefold(),
        first_row.get("document_id", ""),
    )


def _error_metadata_row(
    *,
    document_id: str,
    candidate_name: str,
    race_id: str,
    role: str,
    election_date: str,
    publication_date: str,
    source_type: str,
    source_url: str,
    archive_url: str,
    queue_id: str,
    seed_kind: str,
    source_record_id: str,
    analysis_scope: str,
    notes: str,
    fetch_status: str,
    extraction_status: str,
    error: str,
    coverage_status: str = "",
    capture: RawDocumentCapture | None = None,
    raw_path: Path | None = None,
) -> dict[str, str]:
    row = {
        "document_id": document_id,
        "queue_id": queue_id,
        "candidate_slug": candidate_slug(candidate_name) if candidate_name else "",
        "candidate_name": candidate_name,
        "race_id": race_id,
        "role": role,
        "election_date": election_date,
        "publication_date": publication_date,
        "campaign_window_start": "",
        "campaign_window_end": "",
        "campaign_window_status": "",
        "source_type": source_type,
        "source_url": source_url,
        "archive_url": archive_url,
        "final_url": capture.final_url if capture else "",
        "retrieved_at": capture.retrieved_at if capture else "",
        "content_type": capture.content_type if capture else "",
        "title": "",
        "coverage_status": coverage_status,
        "fetch_status": fetch_status,
        "extraction_status": extraction_status,
        "extractor": "",
        "raw_sha256": capture.sha256 if capture else "",
        "text_sha256": "",
        "provenance_hash": "",
        "paragraph_count": "0",
        "sentence_count": "0",
        "raw_path": _relative_path(raw_path),
        "seed_kind": seed_kind,
        "source_record_id": source_record_id,
        "analysis_scope": analysis_scope,
        "notes": notes,
        "error": error,
    }
    if election_date:
        try:
            window = campaign_window_for_election(election_date)
            row["campaign_window_start"] = window.start.isoformat()
            row["campaign_window_end"] = window.end.isoformat()
            row["campaign_window_status"] = classify_campaign_window(
                election_date,
                publication_date,
            )
        except DocumentCorpusError:
            row["campaign_window_status"] = ""
    return row


def _success_metadata_row(
    metadata: CandidateDocumentMetadata,
    *,
    job: CandidateDocumentJob,
    fetch_status: str,
    extraction_status: str,
    extractor: str,
) -> dict[str, str]:
    row = metadata.as_row()
    row.update(
        {
            "queue_id": job.queue_id,
            "role": job.role,
            "fetch_status": fetch_status,
            "extraction_status": extraction_status,
            "extractor": extractor,
            "seed_kind": job.seed_kind,
            "source_record_id": job.source_record_id,
            "analysis_scope": job.analysis_scope,
            "notes": job.notes,
            "error": "",
        }
    )
    return row


def _full_text_row(
    metadata: CandidateDocumentMetadata,
    extracted: ExtractedDocument,
    job: CandidateDocumentJob,
    raw_path: Path,
) -> dict[str, str]:
    return {
        "document_id": metadata.document_id,
        "queue_id": job.queue_id,
        "candidate_slug": metadata.candidate_slug,
        "candidate_name": metadata.candidate_name,
        "race_id": metadata.race_id,
        "role": job.role,
        "source_type": metadata.source_type,
        "source_url": metadata.source_url,
        "archive_url": metadata.archive_url,
        "final_url": metadata.final_url,
        "retrieved_at": metadata.retrieved_at,
        "content_type": metadata.content_type,
        "title": metadata.title,
        "coverage_status": metadata.coverage_status,
        "extractor": extracted.extractor,
        "publication_date": metadata.publication_date,
        "raw_path": _relative_path(raw_path),
        "raw_sha256": metadata.raw_sha256,
        "text_sha256": metadata.text_sha256,
        "provenance_hash": metadata.provenance_hash,
        "paragraph_count": str(metadata.paragraph_count),
        "sentence_count": str(metadata.sentence_count),
        "analysis_scope": job.analysis_scope,
        "text": extracted.text,
    }


def _raw_manifest_fieldnames() -> list[str]:
    return [
        "document_id",
        "source_url",
        "canonical_source_url",
        "archive_url",
        "final_url",
        "canonical_final_url",
        "retrieved_at",
        "content_type",
        "encoding",
        "byte_count",
        "sha256",
        "raw_path",
    ]


def _raw_manifest_row(
    capture: RawDocumentCapture,
    raw_path: Path,
    *,
    archive_url: str = "",
) -> dict[str, str]:
    return {
        "document_id": capture.document_id,
        "source_url": capture.source_url,
        "canonical_source_url": canonical_source_url(capture.source_url),
        "archive_url": _archive_provenance_url(archive_url, capture.final_url),
        "final_url": capture.final_url,
        "canonical_final_url": canonical_source_url(capture.final_url),
        "retrieved_at": capture.retrieved_at,
        "content_type": capture.content_type,
        "encoding": capture.encoding,
        "byte_count": str(capture.byte_count),
        "sha256": capture.sha256,
        "raw_path": _relative_path(raw_path),
    }


def _append_raw_manifest(path: Path, row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _metadata_fieldnames() -> list[str]:
    return [
        "document_id",
        "queue_id",
        "candidate_slug",
        "candidate_name",
        "race_id",
        "role",
        "election_date",
        "publication_date",
        "campaign_window_start",
        "campaign_window_end",
        "campaign_window_status",
        "source_type",
        "source_url",
        "archive_url",
        "final_url",
        "retrieved_at",
        "content_type",
        "title",
        "coverage_status",
        "fetch_status",
        "extraction_status",
        "extractor",
        "raw_sha256",
        "text_sha256",
        "provenance_hash",
        "paragraph_count",
        "sentence_count",
        "raw_path",
        "seed_kind",
        "source_record_id",
        "analysis_scope",
        "notes",
        "error",
    ]


def _metadata_sort_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        row.get("election_date", ""),
        row.get("candidate_name", "").casefold(),
        row.get("role", ""),
        row.get("document_id", ""),
    )


def _segment_sort_key(row: dict[str, str]) -> tuple[str, int, str]:
    return (
        row.get("document_id", ""),
        int(row.get("index", "0") or 0),
        row.get("segment_id", ""),
    )


def _analysis_segment_fieldnames() -> list[str]:
    return [
        "analysis_segment_id",
        "document_id",
        "candidate_slug",
        "candidate_name",
        "race_id",
        "role",
        "source_type",
        "segment_index",
        "analysis_kind",
        "locator",
        "source_locator_start",
        "source_locator_end",
        "paragraph_start",
        "paragraph_end",
        "sentence_start",
        "sentence_end",
        "text",
        "token_count",
        "sha256",
        "exact_duplicate_hash",
        "exact_duplicate_count",
        "exact_duplicate_flag",
        "near_duplicate_hash",
        "near_duplicate_count",
        "near_duplicate_flag",
        "boilerplate_flag",
        "boilerplate_reasons",
    ]


def _analysis_segment_sort_key(segment: AnalysisSegment) -> tuple[str, int, str]:
    return (segment.document_id, segment.segment_index, segment.analysis_segment_id)


def _build_analysis_segment_corpus(
    metadata_rows: Sequence[dict[str, str]],
    paragraph_rows: Sequence[dict[str, str]],
    sentence_rows: Sequence[dict[str, str]],
    config: AnalysisSegmentConfig,
) -> tuple[AnalysisSegment, ...]:
    paragraph_segments = defaultdict(list)
    sentence_segments = defaultdict(list)
    for row in paragraph_rows:
        segment = _segment_from_row(row)
        paragraph_segments[segment.document_id].append(segment)
    for row in sentence_rows:
        segment = _segment_from_row(row)
        sentence_segments[segment.document_id].append(segment)

    all_segments: list[AnalysisSegment] = []
    for metadata_row in sorted(metadata_rows, key=_metadata_sort_key):
        if not _metadata_supports_analysis(metadata_row):
            continue
        document_id = metadata_row.get("document_id", "")
        paragraphs = tuple(sorted(paragraph_segments.get(document_id, []), key=lambda value: value.index))
        if not paragraphs:
            continue
        sentences = tuple(sorted(sentence_segments.get(document_id, []), key=lambda value: value.index))
        all_segments.extend(
            _analysis_segments_for_document(
                candidate_name=metadata_row.get("candidate_name", ""),
                race_id=metadata_row.get("race_id", ""),
                role=metadata_row.get("role", ""),
                document_id=document_id,
                paragraphs=paragraphs,
                sentences=sentences,
                candidate_slug_value=metadata_row.get("candidate_slug", ""),
                source_type=metadata_row.get("source_type", ""),
                config=config,
            )
        )
    return _annotate_analysis_segments(all_segments, config)


def _metadata_supports_analysis(metadata_row: dict[str, str]) -> bool:
    if metadata_row.get("analysis_scope", "").strip() == "context_only":
        return False
    return metadata_row.get("coverage_status", "").strip() != "shared_document_unscoped" and (
        metadata_row.get("extraction_status", "").strip() != "shared_document_unscoped"
    )


def _segment_from_row(row: dict[str, str]) -> TextSegment:
    return TextSegment(
        segment_id=row.get("segment_id", ""),
        document_id=row.get("document_id", ""),
        segment_kind=row.get("segment_kind", ""),
        index=int(row.get("index", "0") or 0),
        locator=row.get("locator", ""),
        text=row.get("text", ""),
        sha256=row.get("sha256", ""),
    )


def _analysis_segments_for_document(
    *,
    candidate_name: str,
    race_id: str,
    role: str,
    document_id: str,
    paragraphs: Sequence[TextSegment],
    sentences: Sequence[TextSegment],
    candidate_slug_value: str,
    source_type: str,
    config: AnalysisSegmentConfig,
) -> list[AnalysisSegment]:
    sentence_meta = [_sentence_meta(segment) for segment in sentences]
    sentences_by_paragraph: dict[int, list[dict[str, object]]] = defaultdict(list)
    for meta in sentence_meta:
        sentences_by_paragraph[int(meta["paragraph_index"])].append(meta)
    units: list[_AnalysisSourceUnit] = []
    for paragraph in sorted(paragraphs, key=lambda value: value.index):
        paragraph_sentences = sentences_by_paragraph.get(paragraph.index, [])
        token_count = _token_count(paragraph.text)
        if token_count > config.max_tokens and len(paragraph_sentences) > 1:
            units.extend(_split_long_paragraph(paragraph, paragraph_sentences, config))
            continue
        first_sentence = paragraph_sentences[0]["global_index"] if paragraph_sentences else 0
        last_sentence = paragraph_sentences[-1]["global_index"] if paragraph_sentences else 0
        units.append(
            _AnalysisSourceUnit(
                source_kind="paragraph",
                paragraph_start=paragraph.index,
                paragraph_end=paragraph.index,
                sentence_start=int(first_sentence),
                sentence_end=int(last_sentence),
                source_locator_start=paragraph.locator,
                source_locator_end=paragraph.locator,
                text=paragraph.text,
                token_count=token_count,
            )
        )
    merged_units = _merge_analysis_units(units, config)
    slug = candidate_slug_value or candidate_slug(candidate_name)
    segments = []
    for segment_index, group in enumerate(merged_units, start=1):
        text = " ".join(unit.text for unit in group).strip()
        start = group[0]
        end = group[-1]
        locator = _format_analysis_locator(start.source_locator_start, end.source_locator_end)
        analysis_kind = group[0].source_kind if len(group) == 1 else "merged"
        segments.append(
            AnalysisSegment(
                analysis_segment_id=stable_hash(document_id, str(segment_index), locator, text),
                document_id=document_id,
                candidate_slug=slug,
                candidate_name=candidate_name.strip(),
                race_id=race_id.strip(),
                role=role.strip(),
                source_type=source_type.strip(),
                segment_index=segment_index,
                analysis_kind=analysis_kind,
                locator=locator,
                source_locator_start=start.source_locator_start,
                source_locator_end=end.source_locator_end,
                paragraph_start=start.paragraph_start,
                paragraph_end=end.paragraph_end,
                sentence_start=start.sentence_start,
                sentence_end=end.sentence_end,
                text=text,
                token_count=_token_count(text),
                sha256=_sha256_text(text),
                exact_duplicate_hash="",
                exact_duplicate_count=0,
                exact_duplicate_flag=False,
                near_duplicate_hash="",
                near_duplicate_count=0,
                near_duplicate_flag=False,
                boilerplate_flag=False,
                boilerplate_reasons="",
            )
        )
    return segments


def _split_long_paragraph(
    paragraph: TextSegment,
    paragraph_sentences: Sequence[dict[str, object]],
    config: AnalysisSegmentConfig,
) -> list[_AnalysisSourceUnit]:
    groups: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    current_tokens = 0
    for sentence in paragraph_sentences:
        sentence_tokens = _token_count(str(sentence["text"]))
        if current and current_tokens + sentence_tokens > config.max_tokens and (
            current_tokens >= config.min_tokens or len(current) > 1
        ):
            groups.append(current)
            current = []
            current_tokens = 0
        current.append(sentence)
        current_tokens += sentence_tokens
    if current:
        groups.append(current)
    if len(groups) > 1 and _group_token_count(groups[-1]) < config.min_tokens:
        groups[-2].extend(groups[-1])
        groups.pop()
    units = []
    for group in groups:
        first = group[0]
        last = group[-1]
        local_start = int(first["local_index"])
        local_end = int(last["local_index"])
        locator = (
            f"paragraph {paragraph.index} sentence {local_start}"
            if local_start == local_end
            else f"paragraph {paragraph.index} sentences {local_start}-{local_end}"
        )
        units.append(
            _AnalysisSourceUnit(
                source_kind="sentence_window",
                paragraph_start=paragraph.index,
                paragraph_end=paragraph.index,
                sentence_start=int(first["global_index"]),
                sentence_end=int(last["global_index"]),
                source_locator_start=locator,
                source_locator_end=locator,
                text=" ".join(str(item["text"]) for item in group).strip(),
                token_count=_group_token_count(group),
            )
        )
    return units


def _merge_analysis_units(
    units: Sequence[_AnalysisSourceUnit],
    config: AnalysisSegmentConfig,
) -> list[list[_AnalysisSourceUnit]]:
    if not units:
        return []
    merged: list[list[_AnalysisSourceUnit]] = []
    pending: list[_AnalysisSourceUnit] = []
    pending_tokens = 0
    soft_max_tokens = config.max_tokens + max(5, config.min_tokens // 2)

    def flush() -> None:
        nonlocal pending, pending_tokens
        if pending:
            merged.append(pending)
        pending = []
        pending_tokens = 0

    for unit in units:
        unit_tokens = unit.token_count
        if not pending:
            pending = [unit]
            pending_tokens = unit_tokens
            continue
        if pending_tokens < config.min_tokens and pending_tokens + unit_tokens <= soft_max_tokens:
            pending.append(unit)
            pending_tokens += unit_tokens
            continue
        flush()
        pending = [unit]
        pending_tokens = unit_tokens
    if pending:
        if merged and pending_tokens < config.min_tokens:
            previous_tokens = sum(unit.token_count for unit in merged[-1])
            if previous_tokens + pending_tokens <= soft_max_tokens:
                merged[-1].extend(pending)
            else:
                merged.append(pending)
        else:
            merged.append(pending)
    return merged


def _annotate_analysis_segments(
    segments: Sequence[AnalysisSegment],
    config: AnalysisSegmentConfig,
) -> tuple[AnalysisSegment, ...]:
    exact_hashes = [_exact_duplicate_hash(segment.text) for segment in segments]
    near_hashes = [_near_duplicate_hash(segment.text, config) for segment in segments]
    exact_counts = Counter(exact_hash for exact_hash in exact_hashes if exact_hash)
    near_counts = Counter(near_hash for near_hash in near_hashes if near_hash)
    exact_documents: dict[str, set[str]] = defaultdict(set)
    near_documents: dict[str, set[str]] = defaultdict(set)
    for segment, exact_hash, near_hash in zip(segments, exact_hashes, near_hashes, strict=False):
        if exact_hash:
            exact_documents[exact_hash].add(segment.document_id)
        if near_hash:
            near_documents[near_hash].add(segment.document_id)
    annotated = []
    for segment, exact_hash, near_hash in zip(segments, exact_hashes, near_hashes, strict=False):
        exact_count = exact_counts.get(exact_hash, 0)
        near_count = near_counts.get(near_hash, 0) if near_hash else 0
        exact_flag = exact_count > 1
        near_flag = bool(near_hash) and near_count > 1 and not exact_flag
        boilerplate_reasons = _boilerplate_reasons(
            segment.text,
            segment.token_count,
            exact_hash,
            near_hash,
            exact_documents,
            near_documents,
            config,
        )
        annotated.append(
            AnalysisSegment(
                analysis_segment_id=segment.analysis_segment_id,
                document_id=segment.document_id,
                candidate_slug=segment.candidate_slug,
                candidate_name=segment.candidate_name,
                race_id=segment.race_id,
                role=segment.role,
                source_type=segment.source_type,
                segment_index=segment.segment_index,
                analysis_kind=segment.analysis_kind,
                locator=segment.locator,
                source_locator_start=segment.source_locator_start,
                source_locator_end=segment.source_locator_end,
                paragraph_start=segment.paragraph_start,
                paragraph_end=segment.paragraph_end,
                sentence_start=segment.sentence_start,
                sentence_end=segment.sentence_end,
                text=segment.text,
                token_count=segment.token_count,
                sha256=segment.sha256,
                exact_duplicate_hash=exact_hash,
                exact_duplicate_count=exact_count,
                exact_duplicate_flag=exact_flag,
                near_duplicate_hash=near_hash,
                near_duplicate_count=near_count,
                near_duplicate_flag=near_flag,
                boilerplate_flag=bool(boilerplate_reasons),
                boilerplate_reasons=" | ".join(boilerplate_reasons),
            )
        )
    return tuple(annotated)


def _boilerplate_reasons(
    text: str,
    token_count: int,
    exact_hash: str,
    near_hash: str,
    exact_documents: dict[str, set[str]],
    near_documents: dict[str, set[str]],
    config: AnalysisSegmentConfig,
) -> list[str]:
    reasons = []
    normalized = _normalize_analysis_text(text)
    for phrase in sorted(BOILERPLATE_PHRASES):
        if phrase in normalized:
            reasons.append(f"phrase:{phrase}")
    if exact_hash and len(exact_documents.get(exact_hash, set())) > 1 and token_count <= config.max_tokens:
        reasons.append("repeated_cross_document_exact")
    elif near_hash and len(near_documents.get(near_hash, set())) > 1 and token_count <= config.max_tokens:
        reasons.append("repeated_cross_document_near")
    return reasons


def _exact_duplicate_hash(text: str) -> str:
    return _sha256_text(_normalize_analysis_text(text))


def _near_duplicate_hash(text: str, config: AnalysisSegmentConfig) -> str:
    tokens = _informative_analysis_tokens(text)
    if len(tokens) < config.near_duplicate_min_tokens:
        return ""
    signature = " ".join(sorted(set(tokens)))
    return _sha256_text(signature)


def _informative_analysis_tokens(text: str) -> list[str]:
    return [
        _simple_stem(token)
        for token in _analysis_tokens(text)
        if len(token) > 2 and token not in ANALYSIS_STOPWORDS
    ]


def _analysis_tokens(text: str) -> list[str]:
    return [
        token.strip("'")
        for token in re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", text.casefold())
        if token.strip("'")
    ]


def _simple_stem(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("sses"):
        return token[:-2]
    if token.endswith("s") and len(token) > 4 and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def _normalize_analysis_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    normalized = normalized.replace("“", '"').replace("”", '"').replace("’", "'")
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def _token_count(text: str) -> int:
    return len(_analysis_tokens(text))


def _sentence_meta(segment: TextSegment) -> dict[str, object]:
    match = re.fullmatch(r"paragraph (\d+) sentence (\d+)", segment.locator)
    if not match:
        raise DocumentCorpusError(f"invalid sentence locator: {segment.locator}")
    return {
        "paragraph_index": int(match.group(1)),
        "local_index": int(match.group(2)),
        "global_index": segment.index,
        "text": segment.text,
    }


def _group_token_count(group: Sequence[dict[str, object]]) -> int:
    return sum(_token_count(str(item["text"])) for item in group)


def _format_analysis_locator(start: str, end: str) -> str:
    return start if start == end else f"{start} -> {end}"


def _relative_path(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _path_from_row(value: str) -> Path | None:
    normalized = value.strip()
    if not normalized:
        return None
    path = Path(normalized)
    return path if path.is_absolute() else ROOT / path


def _archive_provenance_url(archive_url: str, final_url: str) -> str:
    if archive_url.strip():
        return normalize_source_url(archive_url)
    try:
        normalized_final_url = normalize_source_url(final_url)
    except DocumentCorpusError:
        return ""
    if urlparse(normalized_final_url).netloc == "web.archive.org":
        return normalized_final_url
    return ""


def _candidate_records(
    evidence_rows: list[dict[str, str]],
    roster_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    records = {}
    for row in roster_rows:
        candidate_name = row.get("candidate_name", "").strip()
        if not candidate_name:
            continue
        role = row.get("role", "").strip()
        race_id = row.get("race_id", "").strip()
        election_date = row.get("election_date", "").strip()
        key = (race_id, candidate_slug(candidate_name), election_date, role)
        records[key] = {
            "queue_id": row.get("queue_id", "").strip(),
            "race_id": race_id,
            "candidate_slug": candidate_slug(candidate_name),
            "candidate_name": candidate_name,
            "role": role,
            "election_date": election_date,
            "official_election_source": row.get("official_election_source", "").strip(),
        }
    for row in evidence_rows:
        candidate_name = row.get("candidate_name", "").strip()
        if not candidate_name:
            continue
        role = row.get("role", "").strip()
        race_id = row.get("race_id", "").strip()
        election_date = row.get("election_date", "").strip()
        key = (race_id, candidate_slug(candidate_name), election_date, role)
        records.setdefault(
            key,
            {
                "queue_id": "",
                "race_id": race_id,
                "candidate_slug": candidate_slug(candidate_name),
                "candidate_name": candidate_name,
                "role": role,
                "election_date": election_date,
                "official_election_source": "",
            },
        )
    return sorted(
        records.values(),
        key=lambda row: (
            row["election_date"],
            row["candidate_name"].casefold(),
            row["role"],
            row["race_id"],
        ),
    )


def _discovery_seed_row(
    candidate: dict[str, str],
    *,
    seed_url: str,
    seed_kind: str,
    source_record_id: str,
    source_type_class: str,
    campaign_domain: str,
    known_source_count: int,
    legacy_locators: str,
    note: str,
    source_tier: str = "",
    publication_date: str = "",
    effective_date: str = "",
    archive_url: str = "",
    live_url: str = "",
    analysis_scope: str = "analysis",
) -> dict[str, str]:
    return {
        "discovery_seed_id": stable_hash(
            candidate["race_id"],
            candidate["candidate_name"],
            candidate["role"],
            seed_kind,
            seed_url,
        ),
        "queue_id": candidate["queue_id"],
        "race_id": candidate["race_id"],
        "candidate_slug": candidate["candidate_slug"],
        "candidate_name": candidate["candidate_name"],
        "role": candidate["role"],
        "election_date": candidate["election_date"],
        "campaign_domain": campaign_domain,
        "official_election_source": candidate["official_election_source"],
        "seed_url": seed_url,
        "seed_kind": seed_kind,
        "seed_priority": str(QUEUE_SEED_PRIORITY[seed_kind]),
        "source_record_id": source_record_id,
        "source_type_class": source_type_class,
        "source_tier": source_tier,
        "publication_date": publication_date,
        "effective_date": effective_date,
        "archive_url": archive_url,
        "live_url": live_url,
        "analysis_scope": analysis_scope,
        "known_source_count": str(known_source_count),
        "legacy_locators": legacy_locators,
        "current_status": "not_searched",
        "notes": note,
    }


def _index_roster_rows(
    roster_rows: list[dict[str, str]],
) -> tuple[
    dict[tuple[str, str], dict[str, str]],
    dict[tuple[str, str], dict[str, str]],
]:
    by_race = {}
    by_date = {}
    for row in roster_rows:
        candidate_name = row.get("candidate_name", "").strip()
        identity = _identity_name(candidate_name)
        if not identity:
            continue
        race_id = row.get("race_id", "").strip()
        election_date = row.get("election_date", "").strip()
        if race_id:
            by_race[(race_id, identity)] = row
        if election_date:
            by_date[(election_date, identity)] = row
    return by_race, by_date


def _match_roster_row(
    race_id: str,
    election_date: str,
    identity: str,
    roster_by_race: dict[tuple[str, str], dict[str, str]],
    roster_by_date: dict[tuple[str, str], dict[str, str]],
) -> dict[str, str]:
    return roster_by_race.get(
        (race_id, identity),
        roster_by_date.get((election_date, identity), {}),
    )


def _identity_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = (
        normalized.replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("–", "-")
        .replace("—", "-")
    )
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def _coerce_date(value: date | str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError as error:
        raise DocumentCorpusError(f"invalid ISO date: {value}") from error


def _coerce_optional_date(value: date | str | None) -> date | None:
    if value in {None, ""}:
        return None
    return _coerce_date(value)


def _suffix(url: str, content_type: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix:
        return suffix
    return mimetypes.guess_extension(content_type) or ".bin"


def _extractor_name(capture: RawDocumentCapture) -> str:
    suffix = capture.suffix
    if capture.content_type.startswith(("audio/", "video/")) or suffix in MEDIA_SUFFIXES:
        return "media_no_transcript"
    if capture.content_type in PDF_TYPES or suffix == ".pdf":
        return "pdf"
    if capture.content_type in SRT_TYPES or suffix == ".srt":
        return "srt"
    if capture.content_type in HTML_TYPES or suffix in {".htm", ".html", ".xhtml"}:
        return "html"
    if capture.content_type in TEXT_TYPES or capture.content_type.startswith("text/"):
        return "plain_text"
    return ""


def _decode_text(value: bytes, encoding: str) -> str:
    return _sanitize_extracted_text(value.decode(encoding or "utf-8", "replace"))


def _extract_srt_text(
    capture: RawDocumentCapture,
) -> tuple[str, str, tuple[TextSegment, ...], tuple[TextSegment, ...]]:
    text = _decode_text(capture.content_bytes, capture.encoding)
    blocks = re.split(r"\n\s*\n+", text.replace("\r\n", "\n").replace("\r", "\n"))
    paragraph_segments: list[TextSegment] = []
    sentence_segments: list[TextSegment] = []
    sentence_index = 1
    for paragraph_index, block in enumerate(blocks, start=1):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        if re.fullmatch(r"\d+", lines[0]):
            lines = lines[1:]
        if not lines:
            continue
        timecode = lines[0]
        if "-->" not in timecode:
            continue
        text_lines = [_sanitize_extracted_text(line) for line in lines[1:]]
        paragraph_text = re.sub(r"\s+", " ", " ".join(line for line in text_lines if line).strip())
        if not paragraph_text:
            continue
        locator = f"time {timecode.replace(' --> ', '-').replace(' -->', '-').replace('--> ', '-').replace('-->', '-')}"
        paragraph_segments.append(
            _segment(capture.document_id, "paragraph", paragraph_index, locator, paragraph_text)
        )
        for local_index, sentence in enumerate(_split_sentences(paragraph_text), start=1):
            sentence_segments.append(
                _segment(
                    capture.document_id,
                    "sentence",
                    sentence_index,
                    f"paragraph {paragraph_index} sentence {local_index}",
                    sentence,
                )
            )
            sentence_index += 1
    if not paragraph_segments:
        raise ExtractionError(f"{capture.document_id}: extracted SRT text is empty")
    normalized_text = "\n\n".join(segment.text for segment in paragraph_segments)
    return "", normalized_text, tuple(paragraph_segments), tuple(sentence_segments)


def _extract_html_text(capture: RawDocumentCapture) -> tuple[str, str]:
    parser = _StructuredHTMLParser()
    parser.feed(_decode_text(capture.content_bytes, capture.encoding))
    parser.close()
    title = " ".join(parser.title).strip()
    text = "\n\n".join(parser.paragraphs())
    return title, text


def _extract_pdf_text(value: bytes) -> tuple[str, str]:
    try:
        reader_class = _pdf_reader_class()
    except ExtractionError as error:
        return _extract_pdf_text_with_swift(value, dependency_error=error)
    try:
        reader = reader_class(BytesIO(value))
    except Exception as error:
        raise ExtractionError(f"PDF extraction failed: {type(error).__name__}: {error}") from error
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[PDF page {page_number}] {text.strip()}")
    title = ""
    metadata = getattr(reader, "metadata", None)
    if metadata:
        title = str(getattr(metadata, "title", "") or metadata.get("/Title", "") or "").strip()
    return title, "\n\n".join(pages)


def _extract_pdf_text_with_swift(
    value: bytes,
    *,
    dependency_error: ExtractionError,
) -> tuple[str, str]:
    if platform.system() != "Darwin":
        raise ExtractionError(
            "PDF extraction requires the optional dependency 'pypdf'; "
            "the PDFKit fallback is only available on macOS"
        ) from dependency_error
    swift_path = _swift_executable()
    if swift_path is None:
        raise ExtractionError(
            "PDF extraction requires the optional dependency 'pypdf'; "
            "the macOS PDFKit fallback also requires /usr/bin/swift"
        ) from dependency_error
    script = """
import Foundation
import PDFKit

let input = FileHandle.standardInput.readDataToEndOfFile()
guard let pdfData = Data(base64Encoded: input) else {
    fputs("invalid-base64", stderr)
    exit(2)
}
guard let document = PDFDocument(data: pdfData) else {
    fputs("pdfkit-open-failed", stderr)
    exit(3)
}
var pages: [[String: String]] = []
for index in 0..<document.pageCount {
    guard let page = document.page(at: index) else { continue }
    let text = page.string?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    if !text.isEmpty {
        pages.append(["page": String(index + 1), "text": text])
    }
}
let title = (document.documentAttributes?[PDFDocumentAttribute.titleAttribute] as? String) ?? ""
let payload: [String: Any] = ["title": title, "pages": pages]
do {
    let output = try JSONSerialization.data(withJSONObject: payload, options: [])
    FileHandle.standardOutput.write(output)
} catch {
    fputs("json-encode-failed: \\(error)", stderr)
    exit(4)
}
"""
    try:
        completed = subprocess.run(
            [str(swift_path), "-e", script],
            input=base64.b64encode(value),
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, OSError) as error:
        raise ExtractionError(
            f"macOS PDFKit extraction via /usr/bin/swift failed to start: {error}"
        ) from error
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", "replace").strip()
        raise ExtractionError(
            "macOS PDFKit extraction via /usr/bin/swift failed "
            f"with exit code {completed.returncode}: {stderr or 'unknown error'}"
        )
    try:
        payload = json.loads(completed.stdout.decode("utf-8", "replace") or "{}")
    except json.JSONDecodeError as error:
        raise ExtractionError(
            f"Swift PDF extraction returned invalid JSON: {error}"
        ) from error
    title = str(payload.get("title", "") or "").strip()
    page_blocks = []
    for page in payload.get("pages", []):
        page_number = str(page.get("page", "") or "").strip()
        page_text = str(page.get("text", "") or "").strip()
        if page_number and page_text:
            page_blocks.append(f"[PDF page {page_number}] {page_text}")
    return title, "\n\n".join(page_blocks)


def _pdf_reader_class():
    try:
        module = importlib.import_module("pypdf")
    except ImportError as error:
        raise ExtractionError(
            "PDF extraction requires the optional dependency 'pypdf'"
        ) from error
    return module.PdfReader


def _swift_executable() -> Path | None:
    path = Path("/usr/bin/swift")
    return path if path.exists() else None


def _sanitize_extracted_text(value: str) -> str:
    sanitized: list[str] = []
    for character in value.replace("\r\n", "\n").replace("\r", "\n"):
        if character in {"\n", "\t"}:
            sanitized.append(character)
            continue
        if unicodedata.category(character).startswith("C"):
            sanitized.append(" ")
            continue
        sanitized.append(character)
    return "".join(sanitized)


def _segment(
    document_id: str,
    segment_kind: str,
    index: int,
    locator: str,
    text: str,
) -> TextSegment:
    return TextSegment(
        segment_id=stable_hash(document_id, segment_kind, locator, text),
        document_id=document_id,
        segment_kind=segment_kind,
        index=index,
        locator=locator,
        text=text,
        sha256=_sha256_text(text),
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _split_sentences(paragraph: str) -> list[str]:
    sentences: list[str] = []
    start = 0
    index = 0
    while index < len(paragraph):
        character = paragraph[index]
        if character not in ".?!":
            index += 1
            continue
        end = index + 1
        while end < len(paragraph) and paragraph[end] in '"\')]}”’':
            end += 1
        next_index = end
        while next_index < len(paragraph) and paragraph[next_index].isspace():
            next_index += 1
        next_char = paragraph[next_index] if next_index < len(paragraph) else ""
        if _is_sentence_boundary(paragraph, index, next_char):
            sentence = paragraph[start:end].strip()
            if sentence:
                sentences.append(sentence)
            start = next_index
            index = next_index
            continue
        index = end
    tail = paragraph[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def _is_sentence_boundary(paragraph: str, index: int, next_char: str) -> bool:
    punctuation = paragraph[index]
    if punctuation == ".":
        token = paragraph[: index + 1].rstrip().split()[-1].casefold()
        if token in COMMON_ABBREVIATIONS:
            return False
        if re.fullmatch(r"(?:[a-z]\.){2,}", token, flags=re.IGNORECASE):
            return False
        if re.fullmatch(r"[a-z]\.", token, flags=re.IGNORECASE):
            return False
        if index > 0 and paragraph[index - 1].isdigit() and next_char.isdigit():
            return False
    if not next_char:
        return True
    return next_char.isupper() or next_char.isdigit() or next_char in OPENING_SENTENCE_CHARS


class _StructuredHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title: list[str] = []
        self._paragraphs: list[str] = []
        self._current: list[str] = []
        self._ignored_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if tag == "title":
            self._in_title = True
            return
        if tag == "br":
            self._flush_paragraph()
            return
        if tag in BLOCK_TAGS:
            self._flush_paragraph()

    def handle_endtag(self, tag: str) -> None:
        if tag in IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if tag == "title":
            self._in_title = False
            return
        if tag in BLOCK_TAGS:
            self._flush_paragraph()

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        normalized = " ".join(data.split())
        if not normalized:
            return
        if self._in_title:
            self.title.append(normalized)
            return
        self._current.append(normalized)

    def paragraphs(self) -> tuple[str, ...]:
        self._flush_paragraph()
        return tuple(self._paragraphs)

    def _flush_paragraph(self) -> None:
        if not self._current:
            return
        paragraph = " ".join(self._current).strip()
        if paragraph:
            self._paragraphs.append(paragraph)
        self._current.clear()


class _DiscoveryLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for key, value in attrs:
            if key == "href" and value:
                self.links.append(value.strip())
                return
