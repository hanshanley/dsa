"""Validate historical source reviews without pretending they are federal return imports."""

import hashlib
import gzip
import json
import re
from collections import defaultdict
from dataclasses import replace
from datetime import date
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from .document_corpus import (
    CandidateDocumentBatchPaths, RawDocumentCapture, candidate_document_id, candidate_slug,
    canonical_source_url, extract_document_text, normalize_source_url,
    run_candidate_document_extraction_batch, _raw_manifest_row, _write_jsonl,
    _resolve_locator_paragraphs,
)
from .io import read_csv, read_json
from .paths import ANALYSIS_DATA_DIR, MANUAL_DIR, PROCESSED_DIR, ROOT

IDENTITY_BASIS = "canonical_registry_and_cached_source_association"
REVIEW_METHOD = "assistant_source_review_not_independent_human_gold"


def validate_publisher_dates(source: dict, body: bytes) -> bool:
    proof = source.get("publisher_date_metadata")
    if proof is None:
        return False
    if not isinstance(proof, dict) or proof.get("format") not in {"json_ld", "html_dateline", "html_meta"}:
        raise ValueError("Publisher date metadata requires a supported explicit source format")
    if source["content_type"] not in {"text/html", "application/xhtml+xml"}:
        raise ValueError("Publisher date proof requires an HTML source")
    if proof["format"] == "html_meta":
        class Properties(HTMLParser):
            def __init__(self):
                super().__init__()
                self.values = defaultdict(list)

            def handle_starttag(self, tag, attrs):
                values = dict(attrs)
                if tag == "meta" and values.get("property") and values.get("content"):
                    self.values[values["property"]].append(values["content"])

        metadata = Properties()
        metadata.feed(body.decode(source.get("encoding", "utf-8")))
        urls = metadata.values["og:url"]
        if len(urls) != 1 or (
            urlparse(canonical_source_url(urls[0]))._replace(scheme="https")
            != urlparse(canonical_source_url(source["url"]))._replace(scheme="https")
        ):
            raise ValueError("Publisher HTML date metadata identifies a different or ambiguous page")
        for property_name, field in (
            ("article:published_time", "publication_date"),
            ("article:modified_time", "source_updated_date"),
        ):
            values = metadata.values[property_name]
            if field == "source_updated_date" and not values and not source.get(field):
                continue
            if len(values) != 1 or datetime.fromisoformat(values[0]).date().isoformat() != source.get(field):
                raise ValueError("Publisher date differs from retained HTML metadata")
        return True
    if proof["format"] == "html_dateline":
        if not all(isinstance(proof.get(key), str) and proof[key].strip() for key in (
            "class_name", "publication_text", "revision_text",
        )):
            raise ValueError("HTML dateline proof needs a class and both complete timestamp strings")

        class Datelines(HTMLParser):
            def __init__(self):
                super().__init__()
                self.depth = 0
                self.parts = []
                self.values = []

            def handle_starttag(self, tag, attrs):
                if tag != "span":
                    return
                if self.depth:
                    self.depth += 1
                elif proof["class_name"] in dict(attrs).get("class", "").split():
                    self.depth = 1
                    self.parts = []

            def handle_data(self, data):
                if self.depth:
                    self.parts.append(data)

            def handle_endtag(self, tag):
                if tag == "span" and self.depth:
                    self.depth -= 1
                    if self.depth == 0:
                        self.values.append(" ".join("".join(self.parts).split()))

        datelines = Datelines()
        datelines.feed(body.decode(source.get("encoding", "utf-8")))
        for key, field in (("publication_text", "publication_date"), ("revision_text", "source_updated_date")):
            text = " ".join(proof[key].split())
            if datelines.values.count(text) != 1:
                raise ValueError("HTML dateline does not match exactly one retained timestamp")
            timestamp = re.sub(r"^(?:·\s*)?Updated\s+", "", text) if key == "revision_text" else text
            if key == "revision_text" and timestamp == text:
                raise ValueError("Revision dateline is not marked Updated")
            recorded = datetime.strptime(timestamp, "%b %d, %Y %I:%M %p").date().isoformat()
            if source.get(field) != recorded:
                raise ValueError("Publisher publication or revision date differs from the retained dateline")
        return True
    if bool(proof.get("node_id")) == bool(proof.get("node_url")):
        raise ValueError("Publisher date metadata requires exactly one explicit JSON-LD node selector")
    if proof.get("node_url") and proof.get("node_type") not in {"WebPage", "Article", "NewsArticle"}:
        raise ValueError("URL-selected date metadata requires a specific article or webpage type")

    def node_url(node):
        page = node.get("mainEntityOfPage")
        main_url = page.get("@id", "") if isinstance(page, dict) else page if isinstance(page, str) else ""
        return node.get("url") or node.get("@id") or main_url

    class Metadata(HTMLParser):
        def __init__(self):
            super().__init__()
            self.active = False
            self.parts = []
            self.records = []

        def handle_starttag(self, tag, attrs):
            if tag == "script":
                self.active = dict(attrs).get("type") == "application/ld+json"
                self.parts = []

        def handle_data(self, data):
            if self.active:
                self.parts.append(data)

        def handle_endtag(self, tag):
            if tag == "script" and self.active:
                self.records.append(json.loads("".join(self.parts)))
                self.active = False

    parser = Metadata()
    parser.feed(body.decode(source.get("encoding", "utf-8")))
    matches = []
    for record in parser.records:
        nodes = record if isinstance(record, list) else record.get("@graph", [record])
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if proof.get("node_id") and node.get("@id") == proof["node_id"]:
                matches.append(node)
            elif (
                proof.get("node_url") and node.get("@type") == proof["node_type"]
                and node_url(node) == proof["node_url"]
            ):
                matches.append(node)
    if len(matches) != 1:
        raise ValueError("Publisher date proof must identify exactly one retained metadata node")
    node = matches[0]
    kinds = node.get("@type", [])
    kinds = [kinds] if isinstance(kinds, str) else kinds
    if not set(kinds) & {"WebPage", "Article", "NewsArticle"}:
        raise ValueError("Publisher date proof identifies an unrelated metadata type")
    selected_url = urlparse(canonical_source_url(node_url(node)))
    source_url = urlparse(canonical_source_url(source["url"]))
    if (
        selected_url.scheme not in {"http", "https"} or source_url.scheme not in {"http", "https"}
        or selected_url._replace(scheme="https") != source_url._replace(scheme="https")
    ):
        raise ValueError("Publisher date proof identifies a different source URL")
    for property_name, field in (("datePublished", "publication_date"), ("dateModified", "source_updated_date")):
        timestamp = node.get(property_name)
        if not isinstance(timestamp, str):
            raise ValueError("Publisher date proof lacks a publication or revision timestamp")
        recorded = datetime.fromisoformat(timestamp).date().isoformat()
        if source.get(field) != recorded:
            raise ValueError("Publisher publication or revision date differs from retained JSON-LD")
    return True


def linked_publication_bound(source: dict, sources: dict) -> str:
    evidence = source.get("availability_evidence")
    if not source.get("available_by_date"):
        return ""
    marker = (evidence or {}).get("availability_date_marker") or (evidence or {}).get("publication_date_marker")
    if not evidence or not evidence.get("source_locator") or not marker:
        raise ValueError("Linked source availability lacks a retained publication/date locator")
    parent = sources[evidence["document_id"]]
    date_field = evidence.get("date_field", "publication_date")
    if date_field not in {"publication_date", "source_updated_date"}:
        raise ValueError("Linked availability requires a publisher publication or revision date")
    if parent.get(date_field) != source["available_by_date"]:
        raise ValueError("Availability bound differs from the publisher's dated release")
    if date_field == "source_updated_date" and (
        not parent.get("publication_date") or parent["publication_date"] > source["available_by_date"]
    ):
        raise ValueError("Publisher revision cannot precede or replace a missing original publication date")
    path = (ROOT / parent["raw_path"]).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("Linked publication path leaves the repository")
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != parent["sha256"] or len(body) != int(parent["bytes"]):
        raise ValueError("Linked publication integrity check failed")
    if body.startswith(b"\x1f\x8b"):
        raise ValueError("Linked publication date verification requires an explicitly decoded retained representation")
    text = body.decode(parent.get("encoding", "utf-8"))
    if marker not in text or source["available_by_date"] not in marker:
        raise ValueError("Publisher's asserted date is absent from the retained release")

    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urls = set()

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if tag == "a" and values.get("href"):
                self.urls.add(canonical_source_url(urljoin(parent["url"], values["href"])))

    links = Links()
    links.feed(text)
    if canonical_source_url(source["url"]) not in links.urls:
        raise ValueError("The dated release does not link to the claimed candidate document")
    if parent.get("source_updated_date", "") > source["available_by_date"]:
        raise ValueError("Later revisions prevent treating this release as an unqualified availability bound")
    return source["available_by_date"]


def answer_context_matches(excerpt: dict, paragraph_text: str) -> bool:
    context = excerpt.get("answer_context")
    if context is None:
        return True
    if not isinstance(context, str) or not context.strip():
        raise ValueError("Answer context must be a nonempty exact source span")
    normalized = " ".join(context.split())
    quote = " ".join(excerpt["short_exact_quote"].split())
    if not quote or normalized.count(quote) != 1:
        raise ValueError("Answer context must bind exactly one occurrence of the quoted response")
    return " ".join(paragraph_text.split()).count(normalized) == 1


def validate_publisher_record(source: dict) -> None:
    if not source.get("publisher_record_path"):
        return
    record_path = (ROOT / source["publisher_record_path"]).resolve()
    parent_path = (ROOT / source["publisher_parent_path"]).resolve()
    if not record_path.is_relative_to(ROOT.resolve()) or not parent_path.is_relative_to(ROOT.resolve()):
        raise ValueError("Publisher provenance leaves the repository")
    record_bytes = record_path.read_bytes()
    if hashlib.sha256(record_bytes).hexdigest() != source["publisher_record_sha256"]:
        raise ValueError("Publisher item record hash differs")
    record = json.loads(record_bytes)
    with gzip.open(parent_path, "rb") as handle:
        parent_bytes = handle.read(64 * 1024 * 1024 + 1)
    if len(parent_bytes) > 64 * 1024 * 1024 or hashlib.sha256(parent_bytes).hexdigest() != source["publisher_parent_sha256"]:
        raise ValueError("Publisher index response integrity failed")
    parent = json.loads(parent_bytes)
    if parent["items"][int(source["publisher_parent_item_index"])] != record:
        raise ValueError("Publisher body does not match the retained index item")
    if hashlib.sha256(record["body"].encode()).hexdigest() != source["sha256"]:
        raise ValueError("Publisher post body differs from the captured source")
    if canonical_source_url(urljoin(source["url"], record["fullUrl"])) != canonical_source_url(source["url"]):
        raise ValueError("Publisher record identifies a different article")
    zone = ZoneInfo(parent["website"]["timeZone"])
    published = datetime.fromtimestamp(record["publishOn"] / 1000, UTC).astimezone(zone).date().isoformat()
    updated = (
        datetime.fromtimestamp(record["updatedOn"] / 1000, UTC).astimezone(zone).date().isoformat()
        if record.get("updatedOn") else ""
    )
    if source.get("publication_date") != published or source.get("source_updated_date") != updated:
        raise ValueError("Publisher publication or revision date differs from the retained record")


def register_review_captures(input_path, output_path) -> dict:
    """Bind newly recovered, explicitly scoped sources through the real extraction pipeline."""
    from .policy_comparison import source_evidence_date

    review = read_json(input_path)
    if review["review_method"] != REVIEW_METHOD:
        raise ValueError("New capture intake must identify its actual source-review method")
    review["identity_basis"] = IDENTITY_BASIS
    sources = {row["document_id"]: row for row in review["sources"]}
    races = {row["race_id"]: row for row in read_csv(PROCESSED_DIR / "race_registry.csv")}
    jobs = {}
    captures = {}
    parsed_documents = {}
    manifest = {}
    existing_metadata_path = PROCESSED_DIR / "candidate_document_metadata.csv"
    existing_paragraph_path = PROCESSED_DIR / "candidate_document_paragraphs.csv"
    existing_metadata = {
        row["document_id"]: row for row in read_csv(existing_metadata_path)
    } if existing_metadata_path.exists() else {}
    existing_quotes = defaultdict(list)
    if existing_paragraph_path.exists():
        for paragraph in read_csv(existing_paragraph_path):
            if existing_metadata.get(paragraph["document_id"], {}).get("analysis_scope") == "reviewed_quote":
                existing_quotes[paragraph["document_id"]].append(paragraph)
    for excerpt in review["excerpts"]:
        excerpt["notes"] = " | ".join(dict.fromkeys(filter(None, [
            excerpt.get("notes", ""), excerpt.get("attribution_notes", ""),
        ])))
        if excerpt.get("metadata_document_id"):
            continue
        source = sources[excerpt["document_id"]]
        registration = excerpt.get("candidate_document_registration") or source.get("candidate_document_registration")
        if registration is None:
            matches = [
                row for row in review.get("candidate_document_registration", [])
                if row["document_id"] == source["document_id"]
                and (row.get("candidate_name") or row.get("exact_candidate_name")) == excerpt["speaker"]
            ]
            if len(matches) != 1:
                raise ValueError("New source needs an unambiguous candidate-document registration")
            registration = matches[0]
        race = races[excerpt["race_id"]]
        if race["scope_kind"] != "tracked_dsa_endorsed_democratic_primary":
            raise ValueError("New historical capture is outside the tracked Democratic-primary scope")
        endorsed = set((race["endorsed_candidates"] or race["endorsed_candidate"]).split(" | "))
        expected_role = "endorsed" if excerpt["speaker"] in endorsed else "opponent"
        expected_excerpt_role = "endorsed_candidate" if expected_role == "endorsed" else "opponent_candidate"
        if excerpt.get("role") != expected_excerpt_role:
            raise ValueError("Recovered excerpt reverses the canonical endorsed/opponent role")
        if excerpt["speaker"] not in race["all_candidates"].split(" | "):
            raise ValueError("New historical source speaker is not in the canonical race")
        if (
            (registration.get("race_id") or registration.get("canonical_race_id")) != race["race_id"]
            or (registration.get("candidate_name") or registration.get("exact_candidate_name")) != excerpt["speaker"]
            or registration["role"] != expected_role
            or registration["election_date"] != race["election_date"]
        ):
            raise ValueError("New capture registration conflicts with candidate, role, or election identity")
        declared_aliases = [
            alias for alias in review.get("identity_aliases", [])
            if alias.get("race_id") == race["race_id"]
            and alias.get("canonical_candidate_name") == excerpt["speaker"]
            and (
                alias.get("identity_document_id") == source["document_id"]
                or source["document_id"].startswith(alias.get("identity_document_id", "") + "-lead")
            )
        ]
        if len(declared_aliases) > 1:
            raise ValueError("Multiple source-name aliases match one recovered excerpt")
        if declared_aliases:
            alias = declared_aliases[0]
            if alias.get("review_status") != "accepted_body_name_variant" or not alias.get("notes"):
                raise ValueError("Publisher source-name variant lacks explicit review")
            excerpt["source_speaker"] = alias["speaker"]
            excerpt["identity_review"] = {
                "status": "accepted_reviewed_source_alias",
                "evidence_document_ids": [source["document_id"]],
                "notes": alias["notes"] + " This is a reviewed source-name association, not legal-name certification.",
            }
        source_speaker = excerpt.get("source_speaker") or registration.get("source_speaker_name") or excerpt["speaker"]
        if candidate_slug(source_speaker) != candidate_slug(excerpt["speaker"]):
            identity_review = excerpt.get("identity_review") or registration.get("identity_review") or {}
            if (
                identity_review.get("status") not in {
                    "accepted_direct_official_alias", "accepted_contextual_official_alias", "accepted_reviewed_source_alias",
                }
                or not identity_review.get("notes") or not identity_review.get("evidence_document_ids")
                or any(key not in sources for key in identity_review["evidence_document_ids"])
            ):
                raise ValueError("Source/canonical candidate-name differences require explicit retained alias evidence")
            excerpt["identity_review"] = identity_review
        if registration.get("analysis_scope", "reviewed_quote") not in {"candidate_excerpt", "reviewed_quote"}:
            raise ValueError("New source intake requires explicit candidate-only paragraph scope")
        locator = (
            registration.get("locator") or registration.get("legacy_locators")
            or registration.get("original_candidate_only_locators")
            or registration.get("candidate_only_locators")
            or registration.get("candidate_only_locator")
        )
        if not locator:
            raise ValueError("New source intake requires reviewed candidate-only locators")
        if (registration.get("publication_date") or "") != (source.get("publication_date") or ""):
            raise ValueError("New capture publication date differs from the reviewed source")
        raw = (ROOT / source["raw_path"]).resolve()
        if not raw.is_relative_to(ROOT.resolve()):
            raise ValueError("New source capture path leaves the repository")
        body = raw.read_bytes()
        if hashlib.sha256(body).hexdigest() != source["sha256"] or len(body) != int(source["bytes"]):
            raise ValueError("New source capture failed integrity validation")
        validate_publisher_dates(source, body)
        if source["status"] == "used":
            from .paths import CONFIG_DIR
            source_evidence_date(
                source, race["election_date"], read_json(CONFIG_DIR / "sources.json")["research_cutoff"],
                verified_available_by=linked_publication_bound(source, sources),
            )
        elif source["status"] != "timing_unverified":
            raise ValueError("Only reviewed source captures can be registered")
        source_type = registration["source_type"]
        url = source["url"]
        document_id = candidate_document_id(excerpt["speaker"], race["race_id"], url, source_type) + "-" + source["sha256"][:12]
        excerpt["metadata_document_id"] = document_id
        job = {
            "document_id": document_id, "candidate_name": excerpt["speaker"],
            "race_id": race["race_id"], "role": expected_role, "election_date": race["election_date"],
            "source_type": source_type, "source_url": url,
            "archive_url": source["final_url"] if "web.archive.org/web/" in source["final_url"] else "",
            "publication_date": source.get("publication_date") or "",
            "analysis_scope": "candidate_excerpt", "legacy_locators": locator,
            "notes": "Scoped source intake from " + input_path.name + "; not independent human gold.",
        }
        captures[document_id] = RawDocumentCapture(
            document_id=document_id, source_url=url, final_url=source["final_url"],
            retrieved_at=source["retrieved_at"], content_type=source["content_type"],
            encoding=source.get("encoding", "utf-8"), content_bytes=body,
            byte_count=len(body), sha256=source["sha256"],
        )
        if document_id not in parsed_documents:
            parsed_documents[document_id] = extract_document_text(captures[document_id])
        parsed = parsed_documents[document_id]
        matches = [
            p for p in parsed.paragraphs
            if " ".join(excerpt["short_exact_quote"].split()) in " ".join(p.text.split())
            and answer_context_matches(excerpt, p.text)
        ]
        numeric_locator = re.match(r"^(paragraphs?\s+\d+(?:\s*[-–]\s*\d+)?)", locator, re.I)
        if numeric_locator or len(matches) != 1:
            exact_locator = numeric_locator[1] if numeric_locator else locator
            indices = _resolve_locator_paragraphs(exact_locator, parsed.paragraphs)
            matches = [p for p in matches if p.index in indices]
        if len(matches) != 1:
            raise ValueError(f"New reviewed quotation needs an unambiguous retained paragraph: {excerpt['excerpt_id']}")
        quote_locator = f"paragraph {matches[0].index} quote: {excerpt['short_exact_quote']}"
        if document_id in jobs and jobs[document_id].get("analysis_scope") == "reviewed_quote":
            quote_locator = " | ".join(dict.fromkeys([
                *jobs[document_id]["legacy_locators"].split(" | "), quote_locator,
            ]))
        elif document_id in existing_quotes:
            quote_locator = " | ".join(dict.fromkeys([
                *(f"paragraph {p['index']} quote: {p['text']}" for p in existing_quotes[document_id]),
                quote_locator,
            ]))
        job["analysis_scope"] = "reviewed_quote"
        job["legacy_locators"] = quote_locator
        jobs[document_id] = job
        source.setdefault("metadata_document_ids", [])
        if document_id not in source["metadata_document_ids"]:
            source["metadata_document_ids"].append(document_id)
        source["metadata_document_id"] = document_id if len(source["metadata_document_ids"]) == 1 else None
        manifest[document_id] = _raw_manifest_row(captures[document_id], raw, archive_url=job["archive_url"])
    intake_dir = ANALYSIS_DATA_DIR / "policy_evidence" / "source_intake"
    manifest_path = intake_dir / f"{output_path.stem}.jsonl"
    _write_jsonl(manifest_path, list(manifest.values()))

    def no_network(*args):
        raise AssertionError("Reviewed-source registration must replay exact retained captures")

    result = run_candidate_document_extraction_batch(
        list(jobs.values()),
        replace(CandidateDocumentBatchPaths.default(), raw_manifest_path=manifest_path),
        fetcher=no_network,
    )
    if result.fetch_errors or result.metadata_errors or result.extraction_errors:
        raise ValueError("Reviewed source registration failed; inspect the explicit extraction metadata")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"registered_documents": len(jobs), "review_path": str(output_path)}


def race_aliases(races: dict, endorsements: list[dict]) -> dict[str, set[str]]:
    aliases = {}
    for race_id, race in races.items():
        names = {
            candidate_slug(name)
            for name in (race["endorsed_candidates"] or race["endorsed_candidate"]).split(" | ")
            if name
        }
        aliases[race_id] = {race_id, *filter(None, race.get("source_race_ids", "").split(" | "))}
        aliases[race_id].update(
            row["race_id"] for row in endorsements
            if row["verification_status"] == "verified"
            and row["election_date"] == race["election_date"]
            and candidate_slug(row["candidate_name"]) in names
        )
    return aliases


def validate_historical_review(path, races: dict, cutoff: str, prior_statements: dict | None = None) -> dict:
    from .policy_comparison import archive_capture_date, normalize, source_evidence_date, validate_comparison

    review = read_json(path)
    prior_statements = prior_statements or {}
    if review.get("identity_basis") != IDENTITY_BASIS or review.get("review_method") != REVIEW_METHOD:
        raise ValueError("Historical reviews must identify their actual source/registry evidence basis")
    metadata = {
        row["document_id"]: row for row in read_csv(PROCESSED_DIR / "candidate_document_metadata.csv")
    }
    aliases = race_aliases(races, read_csv(MANUAL_DIR / "endorsements.csv"))
    cached_paragraphs = defaultdict(list)
    for paragraph in read_csv(PROCESSED_DIR / "candidate_document_paragraphs.csv"):
        cached_paragraphs[paragraph["document_id"]].append(paragraph)
    sources = {}
    parsed = {}
    verified_date_metadata = set()
    for supplied_source in review["sources"]:
        source = dict(supplied_source)
        capture_date = archive_capture_date(source)
        if (
            capture_date and source.get("publication_date") == capture_date
            and not source.get("publisher_date_metadata")
            and not source.get("publisher_record_path")
        ):
            source["metadata_publication_date"] = source["publication_date"]
            source["publication_date"] = None
            source["publication_date_basis"] = "archive_capture_only"
        source_id = source["document_id"]
        if source_id in sources:
            raise ValueError("Historical source IDs must be unique")
        if source["status"] not in {"used", "timing_unverified", "excluded", "identity_only"}:
            raise ValueError("Unsupported historical source review status")
        raw = (ROOT / source["raw_path"]).resolve()
        if not raw.is_relative_to(ROOT.resolve()):
            raise ValueError("Historical source path leaves repository")
        body = raw.read_bytes()
        if len(body) != int(source["bytes"]) or hashlib.sha256(body).hexdigest() != source["sha256"]:
            raise ValueError(f"Historical source integrity failed: {source_id}")
        sources[source_id] = source
        validate_publisher_record(source)
        if validate_publisher_dates(source, body):
            verified_date_metadata.add(source_id)
        if source["status"] in {"used", "timing_unverified"}:
            parsed[source_id] = extract_document_text(RawDocumentCapture(
                document_id=source_id, source_url=source["url"], final_url=source["final_url"],
                retrieved_at=source["retrieved_at"], content_type=source["content_type"],
                encoding=source.get("encoding", "utf-8"), content_bytes=body,
                byte_count=len(body), sha256=source["sha256"],
            ))
    statements = {}
    expected = {}
    excluded = {}
    scope_path = MANUAL_DIR / "race_scope_resolutions.csv"
    exclusions = {
        row["race_id"]: row for row in read_csv(scope_path)
        if row["scope_kind"] == "other_corpus_race"
        and row["classification"] == "endorsement_revoked_before_primary"
    } if scope_path.exists() else {}
    for excerpt in review["excerpts"]:
        source = sources[excerpt["document_id"]]
        document = metadata[excerpt["metadata_document_id"]]
        race = races[excerpt["race_id"]]
        if source["status"] not in {"used", "timing_unverified"}:
            raise ValueError("Excluded historical source cannot support an excerpt")
        out_of_scope = race["scope_kind"] != "tracked_dsa_endorsed_democratic_primary"
        if out_of_scope and race["race_id"] not in exclusions:
            raise ValueError("Historical review is outside the tracked Democratic-primary scope")
        if document["race_id"] not in aliases[race["race_id"]] or document["election_date"] != race["election_date"]:
            raise ValueError("Historical source association does not match the canonical race/date")
        if excerpt["election_date"] != race["election_date"]:
            raise ValueError("Historical excerpt election date differs from canonical race")
        if document["raw_sha256"] != source["sha256"]:
            raise ValueError("Historical quote must use the retained source version, not a silently replaced page")
        if normalize_source_url(source["final_url"]) != normalize_source_url(document["final_url"]):
            raise ValueError("Historical source must preserve the actual retained final URL and archive timestamp")
        recorded_date = source.get("metadata_publication_date", source.get("publication_date") or "")
        if recorded_date != document.get("publication_date", ""):
            raise ValueError("Historical source publication date differs from the retained metadata; review the discrepancy explicitly")
        if canonical_source_url(source["url"]) not in {
            canonical_source_url(document["source_url"]), canonical_source_url(document["final_url"]),
        }:
            raise ValueError("Historical review source URL differs from the retained source association")
        if candidate_slug(document["candidate_name"]) != candidate_slug(excerpt["speaker"]):
            raise ValueError("Historical source is attached to a different candidate")
        endorsed = set((race["endorsed_candidates"] or race["endorsed_candidate"]).split(" | "))
        opponents = set(race["opponent_candidates"].split(" | ")) - endorsed
        role = excerpt["role"]
        if not (
            role == "endorsed_candidate" and excerpt["speaker"] in endorsed
            or role == "opponent_candidate" and excerpt["speaker"] in opponents
        ):
            raise ValueError("Historical excerpt does not match the canonical endorsement role")
        if document["extraction_status"] != "extracted" or document["analysis_scope"] == "context_only":
            raise ValueError("Historical source is unscoped, failed, or context-only")
        quote = excerpt["short_exact_quote"]
        if source.get("artifact_kind") == "publisher_api_post_body" and not excerpt.get("claim_summary", "").strip():
            raise ValueError("Questionnaire review requires the actual candidate claim, not only a question label")
        paragraphs = parsed[excerpt["document_id"]].paragraphs
        numeric_locator = re.match(
            r"^(paragraphs?\s+\d+(?:\s*[-–]\s*\d+)?)", excerpt["locator"], re.I,
        )
        indices = (
            set(_resolve_locator_paragraphs(numeric_locator[1], paragraphs))
            if numeric_locator else None
        )
        matches = [
            p.locator for p in paragraphs
            if normalize(quote) in normalize(p.text) and (indices is None or p.index in indices)
            and answer_context_matches(excerpt, p.text)
        ]
        associated = []
        for paragraph in cached_paragraphs[excerpt["metadata_document_id"]]:
            locator_match = re.match(r"paragraph (\d+)", paragraph["locator"])
            if (
                normalize(quote) in normalize(paragraph["text"])
                and (indices is None or locator_match and int(locator_match[1]) in indices)
            ):
                associated.append(paragraph["locator"])
        if not quote.strip() or not matches or not associated or not excerpt["locator"] or not excerpt["notes"]:
            raise ValueError("Historical quotation lacks exact retained and candidate-scoped evidence")
        if source.get("publication_month"):
            period = source.get("publication_period_evidence", {})
            if (
                not period.get("source_locator") or not period.get("exact_quote")
                or normalize(period["exact_quote"]) not in normalize(parsed[excerpt["document_id"]].text)
            ):
                raise ValueError("Historical publication month lacks exact retained edition evidence")
            if source["publication_month"] + "-01" > race["election_date"]:
                raise ValueError("Known post-primary publication period cannot be treated as uncertain pre-primary evidence")
        revision_notice = source.get("unbounded_revision_notice")
        if revision_notice:
            if (
                not isinstance(revision_notice, dict) or not source.get("publication_date")
                or source.get("source_updated_date") or source["status"] != "timing_unverified"
            ):
                raise ValueError("Unbounded revision requires a retained original date and an explicitly qualified source")
            indices = _resolve_locator_paragraphs(revision_notice.get("source_locator", ""), paragraphs)
            notice_quote = normalize(revision_notice.get("exact_quote", ""))
            if not notice_quote or not any(
                p.index in indices and notice_quote in normalize(p.text) for p in paragraphs
            ):
                raise ValueError("Publisher revision notice is absent from its retained source locator")
            source_evidence_date(source, race["election_date"], cutoff)
        evidence_date = ""
        if source["status"] == "timing_unverified":
            late_revision = (
                (source.get("publisher_record_path") or source["document_id"] in verified_date_metadata)
                and source.get("publication_date", "") <= race["election_date"]
                and (source.get("source_updated_date") or "") > race["election_date"]
            )
            if source.get("publication_date") and not (late_revision or revision_notice):
                raise ValueError("Known historical publication dates cannot be hidden as timing uncertainty")
            capture_date = archive_capture_date(source)
            observed = capture_date or source.get("retrieved_at", "")[:10]
            if not (late_revision or revision_notice) and (not observed or date.fromisoformat(observed).year != int(race["election_year"])):
                cycle_evidence = source.get("historical_cycle_evidence", {})
                if (
                    str(cycle_evidence.get("election_year")) != race["election_year"]
                    or (
                        cycle_evidence.get("election_date")
                        and cycle_evidence["election_date"] != race["election_date"]
                    )
                    or not cycle_evidence.get("source_locator")
                    or not cycle_evidence.get("exact_quote")
                    or normalize(cycle_evidence["exact_quote"]) not in normalize(parsed[excerpt["document_id"]].text)
                ):
                    raise ValueError("Undated historical source needs explicit retained election-cycle evidence")
            timing = "pre_primary_time_unverified"
        else:
            if (source.get("source_updated_date") or "") > race["election_date"]:
                raise ValueError("Source revised after the primary requires explicit version-timing qualification")
            evidence_date, capture_date = source_evidence_date(
                source, race["election_date"], cutoff,
                verified_available_by=linked_publication_bound(source, sources),
            )
            timing = (
                "verified_archived_campaign_version"
                if source.get("version_timing_basis") == "pre_primary_archived_campaign_platform" else
                "verified_publisher_revision_date"
                if source.get("source_updated_date") and evidence_date == source["source_updated_date"]
                and evidence_date != source.get("publication_date") else
                "verified_publication_date" if source.get("publication_date") else
                "verified_publisher_release_bound" if source.get("available_by_date") else
                "verified_publication_month_bound" if source.get("publication_month") else "verified_archive_capture"
            )
        if excerpt["excerpt_id"] in statements:
            raise ValueError("Historical excerpt IDs must be unique")
        statements[excerpt["excerpt_id"]] = {
            **excerpt, "quote": quote, "canonical_speaker": excerpt["speaker"],
            "reviewed": "false", "review_notes": "Assistant source review; " + excerpt["notes"],
            "source_type": document.get("source_type", "unspecified"),
            "source_url": source["url"], "publication_date": source.get("publication_date") or "",
            "temporal_evidence_date": evidence_date,
            "metadata_publication_date": source.get("metadata_publication_date", ""),
            "publication_month": source.get("publication_month", ""),
            "available_by_date": source.get("available_by_date", ""),
            "source_updated_date": source.get("source_updated_date", ""),
            "version_timing_qualification": (
                "publisher_revision_day_unknown" if revision_notice else "publisher_post_revised_after_primary"
                if source.get("source_updated_date", "") > race["election_date"] else ""
            ),
            "archive_url": source["final_url"] if capture_date else "", "capture_date": capture_date,
            "source_sha256": source["sha256"], "quote_match_locators": " | ".join(matches),
            "candidate_scoped_locators": " | ".join(associated), "timing_status": timing,
            "identity_resolution": IDENTITY_BASIS,
            "identity_caveat": "Canonical registry role and retained candidate-source association; not a new independent ballot certification.",
            "official_election_source": race["official_election_source"],
            "official_election_source_status": race["official_election_source_status"],
            "certified_opponents_status": race["certified_opponents_status"],
            "comparison_scope": "democratic_primary",
            "election_timing": "future_scheduled" if race["election_date"] > cutoff else "past_scheduled_date",
            "review_method": REVIEW_METHOD,
        }
        if out_of_scope:
            resolution = exclusions[race["race_id"]]
            excluded[excerpt["excerpt_id"]] = {
                **statements[excerpt["excerpt_id"]],
                "comparison_scope": resolution["classification"],
                "scope_exclusion_reason": resolution["notes"],
                "scope_exclusion_source_url": resolution["source_url"],
                "historical_role": role,
                "role": "formerly_endorsed_candidate" if role == "endorsed_candidate" else role,
            }
        else:
            expected[race["race_id"]] = list(dict.fromkeys(race["all_candidates"].split(" | ")))
    rows = []
    qualified_rows = []
    for comparison in review["comparisons"]:
        if any(key in excluded for key in comparison["excerpt_ids"]):
            raise ValueError("A scope-excluded endorsement cannot support an active primary comparison")
        selected = [
            statements[key] if key in statements else prior_statements[key]
            for key in comparison["excerpt_ids"]
        ]
        if len(selected) != 2 or {row["role"] for row in selected} != {"endorsed_candidate", "opponent_candidate"}:
            raise ValueError("Historical comparisons require one endorsed and one other Democratic candidate")
        if any(row["race_id"] != comparison["race_id"] for row in selected):
            raise ValueError("Historical comparison mixes distinct elections")
        left = next(row for row in selected if row["role"] == "endorsed_candidate")
        right = next(row for row in selected if row["role"] == "opponent_candidate")
        race = races[comparison["race_id"]]
        validate_comparison(comparison, left, right, race)
        row = {
            "comparison_id": comparison["comparison_id"], "race_id": race["race_id"],
            "election_date": race["election_date"], "topic": left["topic"],
            "relationship": comparison["relationship"], "analysis": comparison["interpretation"],
            "review_method": REVIEW_METHOD, "comparison_scope": "democratic_primary",
            "identity_resolution": IDENTITY_BASIS,
            "identity_caveat": left.get("identity_caveat", "Retained source review; see statement-level identity basis."),
            "election_timing": left["election_timing"],
        }
        for side, statement in (("candidate", left), ("opponent", right)):
            for output, source_key in {
                "name": "speaker", "excerpt_id": "excerpt_id", "quote": "quote",
                "source_url": "source_url", "publication_date": "publication_date",
                "publication_month": "publication_month",
                "archive_url": "archive_url", "capture_date": "capture_date",
                "locators": "quote_match_locators", "source_sha256": "source_sha256",
                "timing_status": "timing_status",
                "source_type": "source_type",
            }.items():
                row[f"{side}_{output}"] = statement[source_key]
        if any(s["timing_status"] == "pre_primary_time_unverified" for s in selected):
            row["timing_status"] = "pre_primary_time_unverified"
            row["timing_caveat"] = "At least one authentic source has an unverified pre-primary publication/version."
            qualified_rows.append(row)
        else:
            row["timing_status"] = "pre_primary_verified"
            rows.append(row)
    active = [row for key, row in statements.items() if key not in excluded]
    verified = [row for row in active if row["timing_status"] != "pre_primary_time_unverified"]
    qualified = [row for row in active if row["timing_status"] == "pre_primary_time_unverified"]
    recovered = {(row["race_id"], row["speaker"]) for row in verified}
    available = {(row["race_id"], row["speaker"]): row for row in qualified}
    gaps = []
    for attempt in review.get("unsuccessful_sources", []):
        if attempt["race_id"] in exclusions:
            continue
        key = attempt["race_id"], attempt["candidate"]
        if key in recovered:
            continue
        gaps.append({
            **attempt,
            "outcome": "pre_primary_timing_unverified" if key in available else attempt["outcome"],
        })
    already = {(row["race_id"], row["candidate"]) for row in gaps}
    for key, statement in available.items():
        if key not in recovered and key not in already:
            gaps.append({
                "race_id": key[0], "candidate": key[1], "attempted_url": statement["source_url"],
                "outcome": "pre_primary_timing_unverified", "notes": "Actual words recovered; historical timing remains unverified.",
            })
    attempts = [*review.get("unsuccessful_sources", []), *review.get("source_attempts", [])]
    return {
        "rows": rows, "statements": verified, "timing_unverified_rows": qualified_rows,
        "timing_unverified_statements": qualified, "sources": list(sources.values()),
        "excluded_statements": list(excluded.values()),
        "gaps": gaps, "attempts": attempts, "expected_candidates": expected,
        "comparison_scope": "democratic_primary",
        "review_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
