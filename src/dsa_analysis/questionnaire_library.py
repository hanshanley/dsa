"""Collect complete public candidate-answer records, retaining discovery and timing provenance."""

import argparse
import gzip
import hashlib
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode, urljoin
from zoneinfo import ZoneInfo

from .document_corpus import candidate_slug, fetch_raw_document
from .io import read_csv, write_csv
from .paths import ANALYSIS_DATA_DIR, PROCESSED_DIR, RAW_DIR, ROOT

BASE_URL = "https://jimowles.org"


def candidate_title_matches(title: str, name: str) -> bool:
    title_tokens = set(candidate_slug(title).split("-"))
    name_tokens = [token for token in candidate_slug(name).split("-") if len(token) > 1]
    return len(name_tokens) >= 2 and name_tokens[0] in title_tokens and name_tokens[-1] in title_tokens


def collect_questionnaires(*, since_year: int = 2015, max_pages: int = 100, pause_seconds: float = 1.0) -> dict:
    if max_pages < 1 or not 1 <= since_year <= 9999 or pause_seconds < 0:
        raise ValueError("Invalid questionnaire collection bounds")
    raw_dir = RAW_DIR / "questionnaire_library" / "joldc"
    output = ANALYSIS_DATA_DIR / "policy_evidence" / "questionnaire_library"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    records = {}
    pages = []
    matches = []
    registry = [
        row for row in read_csv(PROCESSED_DIR / "race_registry.csv")
        if row["scope_kind"] == "tracked_dsa_endorsed_democratic_primary"
    ]
    offset = None
    seen_offsets = set()
    complete = False
    for page_number in range(max_pages):
        query = {"category": "questionnaire", "format": "json"}
        if offset is not None:
            query["offset"] = str(offset)
        url = BASE_URL + "/news?" + urlencode(query)
        capture = fetch_raw_document(f"joldc-index-{page_number}", url)
        payload = json.loads(capture.content_bytes)
        items = payload.get("items")
        if not isinstance(items, list):
            raise ValueError("Public questionnaire index no longer exposes its expected item list")
        timezone = payload.get("website", {}).get("timeZone")
        if not timezone:
            raise ValueError("Publisher timezone is required for publication-date interpretation")
        zone = ZoneInfo(timezone)
        parent_path = raw_dir / f"index-{capture.sha256}.json.gz"
        if not parent_path.exists():
            parent_path.write_bytes(gzip.compress(capture.content_bytes, mtime=0))
        pages.append({
            "page_number": page_number, "source_url": url, "retrieved_at": capture.retrieved_at,
            "uncompressed_sha256": capture.sha256,
            "raw_path": str(parent_path.relative_to(ROOT)),
            "stored_sha256": hashlib.sha256(parent_path.read_bytes()).hexdigest(),
        })
        oldest_year = None
        for position, item in enumerate(items):
            published_ms = item.get("publishOn")
            if not isinstance(published_ms, (float, int)) or published_ms <= 0:
                raise ValueError("Questionnaire post lacks a usable published timestamp")
            published = datetime.fromtimestamp(published_ms / 1000, UTC)
            oldest_year = min(oldest_year or published.year, published.year)
            if published.year < since_year:
                continue
            if not isinstance(item.get("body"), str) or not item["body"].strip():
                continue
            if not re.fullmatch(r"[A-Za-z0-9_-]+", str(item.get("id", ""))):
                raise ValueError("Unsafe or missing publisher item identifier")
            item_bytes = json.dumps(item, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
            digest = hashlib.sha256(item_bytes).hexdigest()
            item_path = raw_dir / f"post-{item['id']}-{digest}.json"
            if not item_path.exists():
                item_path.write_bytes(item_bytes)
            body_bytes = item["body"].encode()
            body_path = raw_dir / f"post-{item['id']}-{digest}.html"
            if not body_path.exists():
                body_path.write_bytes(body_bytes)
            updated_ms = item.get("updatedOn")
            updated = datetime.fromtimestamp(updated_ms / 1000, UTC) if updated_ms else None
            record = {
                "item_id": item["id"], "title": item["title"],
                "source_url": urljoin(BASE_URL, item["fullUrl"]), "api_source_url": url,
                "publication_timestamp": published.isoformat(),
                "publication_date": published.astimezone(zone).date().isoformat(),
                "updated_timestamp": updated.isoformat() if updated else "",
                "updated_date": updated.astimezone(zone).date().isoformat() if updated else "",
                "publisher_timezone": timezone, "retrieved_at": capture.retrieved_at,
                "raw_record_path": str(item_path.relative_to(ROOT)), "raw_record_sha256": digest,
                "complete_body_path": str(body_path.relative_to(ROOT)),
                "complete_body_sha256": hashlib.sha256(body_bytes).hexdigest(),
                "parent_response_path": str(parent_path.relative_to(ROOT)),
                "parent_response_sha256": capture.sha256, "parent_item_index": position,
                "status": "captured_full_post_not_semantically_reviewed",
                "candidate_answer_title": "candidate answers" in item["title"].casefold(),
            }
            records[item["id"]] = record
        next_offset = payload.get("pagination", {}).get("nextPageOffset")
        if records:
            write_csv(output / "source_catalog.progress.csv", list(records.values()), list(next(iter(records.values()))))
        write_csv(output / "index_pages.progress.csv", pages, list(pages[0]))
        if not payload.get("pagination", {}).get("nextPage") or oldest_year is None or oldest_year < since_year:
            complete = True
            break
        if next_offset is None or next_offset in seen_offsets:
            raise ValueError("Questionnaire pagination did not advance")
        seen_offsets.add(next_offset)
        offset = next_offset
        time.sleep(pause_seconds)
    if not complete:
        raise RuntimeError("Questionnaire pagination limit reached; partial progress retained without replacing the published catalog")
    if not records:
        raise ValueError("No full questionnaire posts recovered; published catalog was not replaced")
    write_csv(output / "source_catalog.csv", list(records.values()), list(next(iter(records.values()))))
    write_csv(output / "index_pages.csv", pages, list(pages[0]))
    for record in records.values():
        year = int(record["publication_date"][:4])
        for race in registry:
            if not int(race["election_year"]) - 1 <= year <= int(race["election_year"]):
                continue
            for candidate in race["all_candidates"].split(" | "):
                if not candidate_title_matches(record["title"], candidate):
                    continue
                matches.append({
                    "race_id": race["race_id"], "election_date": race["election_date"],
                    "candidate_name": candidate, "office": race["office"], "jurisdiction": race["jurisdiction"],
                    "item_id": record["item_id"], "title": record["title"],
                    "source_url": record["source_url"], "publication_date": record["publication_date"],
                    "updated_date": record["updated_date"], "complete_body_path": record["complete_body_path"],
                    "status": "discovery_lead_name_and_time_window_not_identity_or_policy_verification",
                    "first_published_by_election": record["publication_date"] <= race["election_date"],
                    "updated_after_election": bool(record["updated_date"] and record["updated_date"] > race["election_date"]),
                })
    write_csv(
        output / "registry_source_leads.csv", matches,
        list(matches[0]) if matches else ["race_id", "candidate_name", "item_id", "status"],
    )
    summary = {
        "publisher": BASE_URL, "since_year": since_year, "pages": len(pages),
        "complete_public_index_pass": complete, "full_questionnaire_category_posts": len(records),
        "candidate_race_discovery_leads": len(matches), "semantic_review_complete": False,
        "limitations": "Publication dates and name matches are discovery evidence, not source attribution or proof of pre-primary text versions.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-pages", type=int, default=100)
    print(json.dumps(collect_questionnaires(max_pages=parser.parse_args().max_pages), indent=2))
