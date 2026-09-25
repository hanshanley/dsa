"""Replay reviewed response or platform blocks, separately from short quote anchors."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from .document_corpus import (
    CandidateDocumentBatchPaths, RawDocumentCapture, _raw_manifest_row,
    _resolve_locator_paragraphs, _write_jsonl, candidate_document_id,
    candidate_document_analysis_issues, extract_document_text, run_candidate_document_extraction_batch,
)
from .historical_policy import validate_historical_review
from .io import read_csv, read_json, write_csv
from .paths import ANALYSIS_DATA_DIR, CONFIG_DIR, MANUAL_DIR, PROCESSED_DIR, ROOT


def export_reviewed_interview_answers(name: str = "policy_new_york_2017") -> dict:
    return _export_reviewed_text(name, source_type="candidate_interview")


def export_reviewed_platform_text(name: str) -> dict:
    return _export_reviewed_text(name, source_type="official_campaign_platform")


def _export_reviewed_text(name: str, *, source_type: str) -> dict:
    if not name.startswith("policy_") or Path(name).name != name:
        raise ValueError("Expected a policy review bundle name, not a path")
    spec = read_json(MANUAL_DIR / f"{name}_specs.json")
    platform = source_type == "official_campaign_platform"
    text_field = "scoped_campaign_text" if platform else "complete_published_response"
    count_field = "scoped_campaign_text_blocks" if platform else "complete_published_response_blocks"
    review_path = MANUAL_DIR / f"{name}_review.json"
    review = read_json(review_path)
    races = {r["race_id"]: r for r in read_csv(PROCESSED_DIR / "race_registry.csv")}
    own_ids = {e["excerpt_id"] for e in review["excerpts"]}
    prior = {}
    for filename in ("reviewed_candidate_statements.csv", "timing_unverified_candidate_statements.csv"):
        path = ANALYSIS_DATA_DIR / "policy_evidence" / filename
        if path.exists():
            prior.update({
                row["excerpt_id"]: row for row in read_csv(path) if row["excerpt_id"] not in own_ids
            })
    validate_historical_review(
        review_path, races, read_json(CONFIG_DIR / "sources.json")["research_cutoff"], prior,
    )
    sources = {s["document_id"]: s for s in review["sources"]}
    output = ANALYSIS_DATA_DIR / "policy_evidence" / (
        "complete_campaign_platforms" if platform else "complete_interview_answers"
    ) / name
    output.mkdir(parents=True, exist_ok=True)
    existing = {r["document_id"]: r for r in read_csv(PROCESSED_DIR / "candidate_document_metadata.csv")}
    jobs, manifest, rows, full_sources = [], [], [], []
    for definition in spec["sources"]:
        if definition.get("source_type", spec["source_defaults"]["source_type"]) != source_type:
            raise ValueError("Reviewed text export cannot silently change a source's genre")
        capture_path = (ROOT / spec["raw_folder"] / definition["capture"]).resolve()
        if not capture_path.is_relative_to(ROOT):
            raise ValueError("Interview capture path leaves the repository")
        source = sources[read_json(capture_path)["document_id"]]
        if source["status"] != "used":
            raise ValueError("Full interview enrollment requires timing-supported reviewed sources")
        name_on_ballot = definition["speaker"]
        race_id = definition["race_id"]
        associated = [e for e in review["excerpts"] if e["document_id"] == source["document_id"]]
        if not associated or any(
            e["speaker"] != name_on_ballot or e["race_id"] != race_id for e in associated
        ):
            raise ValueError("Full interview scope requires a reviewed single-candidate source association")
        locators = definition["complete_text_locators" if platform else "complete_answer_locators"]
        scope_hash = hashlib.sha256(locators.encode()).hexdigest()[:12]
        reused_document_id = definition.get("existing_analysis_document_id")
        document_id = reused_document_id or (
            candidate_document_id(name_on_ballot, race_id, source["url"], source_type)
            + "-answers-" + source["sha256"][:12] + "-" + scope_hash
        )
        if reused_document_id:
            prior = existing[reused_document_id]
            if (
                prior["raw_sha256"] != source["sha256"] or prior["race_id"] != race_id
                or prior["candidate_name"] != name_on_ballot
                or prior["extraction_status"] != "extracted"
                or candidate_document_analysis_issues(prior)
            ):
                raise ValueError("An existing platform input is not the declared eligible source/candidate/race")
        raw = (ROOT / source["raw_path"]).resolve()
        if not raw.is_relative_to(ROOT):
            raise ValueError("Interview source path leaves the repository")
        body = raw.read_bytes()
        if len(body) != source["bytes"] or hashlib.sha256(body).hexdigest() != source["sha256"]:
            raise ValueError("Full interview source failed integrity checks")
        capture = RawDocumentCapture(
            document_id, source["url"], source["final_url"], source["retrieved_at"],
            source["content_type"], source.get("encoding", "utf-8"), body, len(body), source["sha256"],
        )
        parsed = extract_document_text(capture)
        selected = set()
        for locator in locators.split(" | "):
            indices = _resolve_locator_paragraphs(locator, parsed.paragraphs)
            if not indices:
                raise ValueError("A reviewed interview locator did not resolve")
            selected.update(indices)
        if not selected:
            raise ValueError("No reviewed complete interview answer blocks")
        if platform:
            full_sources.append({
                "candidate_name": name_on_ballot, "race_id": race_id,
                "source_id": source["document_id"], "source_url": source["url"],
                "final_url": source["final_url"], "source_sha256": source["sha256"],
                "source_raw_path": source["raw_path"],
                "publication_date": source.get("publication_date") or "",
                "source_updated_date": source.get("source_updated_date") or "",
                "analysis_locators": locators,
                "full_retained_source_text": parsed.text,
                "limit": "Complete extracted source, including navigation, citations and embedded historical quotations. Only the separately scoped text is eligible model input; not a complete campaign census.",
            })
        for paragraph in parsed.paragraphs:
            if paragraph.index in selected:
                rows.append({
                    "candidate_name": name_on_ballot, "race_id": race_id,
                    "source_id": source["document_id"], "metadata_document_id": document_id,
                    "source_url": source["url"], "publication_date": source.get("publication_date") or "",
                    "source_sha256": source["sha256"], "source_raw_path": source["raw_path"],
                    "locator": paragraph.locator, text_field: paragraph.text,
                    "text_sha256": paragraph.sha256, "review_method": review["review_method"],
                    "limit": (
                        "Complete selected campaign-source paragraph, not a new stance classification or complete campaign census."
                        if platform else
                        "Complete published response block; edited by the publisher, not an unedited transcript or complete campaign platform."
                    ),
                })
        if reused_document_id:
            continue
        jobs.append({
            "document_id": document_id, "candidate_name": name_on_ballot, "race_id": race_id,
            "role": associated[0]["role"].removesuffix("_candidate"),
            "election_date": races[race_id]["election_date"],
            "source_type": source_type, "source_url": source["url"],
            "archive_url": source["final_url"] if "web.archive.org/web/" in source["final_url"] else "",
            "publication_date": source.get("publication_date") or "",
            "analysis_scope": "candidate_excerpt", "legacy_locators": locators,
            "notes": "Reviewed complete source blocks explicitly scoped in " + f"{name}_specs.json; navigation, other speakers and unselected historical excerpts are not enrolled.",
        })
        manifest.append(_raw_manifest_row(capture, raw, archive_url=jobs[-1]["archive_url"]))
    if not rows:
        raise ValueError("No complete interview responses")
    manifest_path = output / "raw_manifest.jsonl"
    if manifest_path.exists():
        old_ids = {
            json.loads(line)["document_id"] for line in manifest_path.read_text().splitlines() if line
        }
        if old_ids - {job["document_id"] for job in jobs}:
            raise ValueError("Interview scopes changed; explicitly retire previous enrollment first")
    _write_jsonl(manifest_path, manifest)

    def no_network(*args):
        raise AssertionError("Interview replay must use retained source bytes")

    result = run_candidate_document_extraction_batch(
        jobs, replace(CandidateDocumentBatchPaths.default(), raw_manifest_path=manifest_path),
        fetcher=no_network,
    )
    if result.fetch_errors or result.metadata_errors or result.extraction_errors:
        raise ValueError("Full interview enrollment failed; inspect extraction metadata")
    write_csv(output / ("scoped_blocks.csv" if platform else "complete_responses.csv"), rows, list(rows[0]))
    if full_sources:
        write_csv(output / "complete_sources.csv", full_sources, list(full_sources[0]))
    summary = {
        "source_documents": len(spec["sources"]),
        "scoped_documents_replayed": len(jobs),
        "external_existing_documents_reused": len(spec["sources"]) - len(jobs),
        "candidate_race_records": len({(r["race_id"], r["candidate_name"]) for r in rows}),
        count_field: len(rows),
        "review_sha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
        "spec_sha256": hashlib.sha256((MANUAL_DIR / f"{name}_specs.json").read_bytes()).hexdigest(),
        "new_independent_stance_classifications": 0,
        "complete_campaign_platforms": False,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    print(export_reviewed_interview_answers())
