"""Reproduce reviewed policy comparisons from exact, speaker-attributed evidence."""

import argparse
import calendar
import hashlib
import json
import mimetypes
import re
from dataclasses import replace
from datetime import date
from urllib.parse import urlparse

from .congressional_accounting import canonical_party
from .document_corpus import (
    RawDocumentCapture,
    CandidateDocumentBatchPaths,
    canonical_source_url,
    campaign_window_for_election,
    archived_campaign_version_date,
    extract_document_text,
    fetch_raw_document,
    persist_raw_document,
    run_candidate_document_extraction_batch,
    _raw_manifest_row,
    _write_jsonl,
)
from .io import read_csv, read_json, write_csv
from .paths import ANALYSIS_DATA_DIR, CONFIG_DIR, MANUAL_DIR, PROCESSED_DIR, RAW_DIR, ROOT

COMPARISON_SCOPES = {
    "democratic_primary",
    "nonpartisan_ballot_democratic_candidates",
    "nonpartisan_ballot_endorsed_vs_democrats",
    "upcoming_nonpartisan_ballot_democratic_candidates",
}

def normalize(value: str) -> str:
    return " ".join(value.split())


def platform_pair_date_issues(comparison: dict, excerpts: dict, documents: dict) -> list[str]:
    issues = []
    cycle = int(comparison["cycle"])
    for side in ("dsa", "democratic"):
        document = documents[excerpts[comparison[f"{side}_excerpt_id"]]["document_id"]]
        published = document.get("publication_date", "")
        if not published:
            issues.append(f"{side}_source_date_unknown")
        elif date.fromisoformat(published).year > cycle:
            issues.append(f"{side}_source_postdates_comparison_cycle")
    return issues


def attributed_quote_locators(paragraphs, speaker: str, quote: str) -> list[str]:
    names = (speaker, speaker.rsplit(" ", 1)[-1])
    prefix = re.compile(r"^(?:" + "|".join(re.escape(name) for name in names) + r"):\s*", re.I)
    return [
        paragraph.locator for paragraph in paragraphs
        if prefix.match(paragraph.text) and normalize(quote) in normalize(paragraph.text)
    ]


def comparison_representation_kind(comparison: dict, statements: dict) -> str:
    refs = [comparison.get(f"{side}_excerpt_id", "") for side in ("candidate", "opponent")]
    if any(ref and ref not in statements for ref in refs):
        raise ValueError("Comparison representation refers to a missing statement")
    kinds = [statements.get(ref, {}).get("representation_kind") for ref in refs]
    if not all(kinds):
        return "unspecified"
    if kinds[0] != kinds[1]:
        raise ValueError("Comparison representation mixes different statement kinds")
    if kinds[0] not in {"policy_position", "campaign_frame", "agenda_item"}:
        raise ValueError("Unknown comparison representation kind")
    return kinds[0]


def apply_representation_reviews(statements: dict, review: dict) -> None:
    if review.get("review_method") != "assistant_source_review_not_independent_human_gold":
        raise ValueError("Representation review must identify its actual review method")
    seen = set()
    for decision in review["reviews"]:
        key = decision["excerpt_id"]
        if key in seen or key not in statements:
            raise ValueError("Representation review has a duplicate or missing statement")
        seen.add(key)
        statement = statements[key]
        quote = statement.get("quote") or statement.get("short_exact_quote", "")
        if (
            statement["source_sha256"] != decision["source_sha256"]
            or hashlib.sha256(quote.encode()).hexdigest() != decision["quote_sha256"]
        ):
            raise ValueError("Representation review no longer matches its source and quotation")
        kind = decision["representation_kind"]
        if kind not in {"policy_position", "campaign_frame", "agenda_item"} or not decision.get("rationale"):
            raise ValueError("Representation review lacks a supported kind or reason")
        if statement.get("representation_kind") and statement["representation_kind"] != kind:
            raise ValueError("Representation review conflicts with the canonical statement kind")
        statement["representation_kind"] = kind
        statement["representation_review_notes"] = decision["rationale"]


def validate_comparison(
    review: dict, left: dict, right: dict, race: dict, *,
    comparison_scope: str = "democratic_primary",
) -> None:
    if comparison_scope not in COMPARISON_SCOPES:
        raise ValueError("Unknown policy comparison scope")
    if comparison_scope == "democratic_primary" and race["scope_kind"] != "tracked_dsa_endorsed_democratic_primary":
        raise ValueError("Policy comparison requires an in-scope Democratic primary")
    endorsed = set((race["endorsed_candidates"] or race["endorsed_candidate"]).split(" | "))
    opponents = set(race["opponent_candidates"].split(" | "))
    left_name = left.get("canonical_speaker", left["speaker"])
    right_name = right.get("canonical_speaker", right["speaker"])
    if left_name not in endorsed or right_name not in opponents or right_name in endorsed:
        raise ValueError("Comparison speakers do not match the endorsed/opponent registry roles")
    if left["topic"] != right["topic"]:
        raise ValueError("Paired policy evidence must address the same topic")
    if not all(
        excerpt["reviewed"] == "true"
        or excerpt.get("review_notes", "").startswith("Assistant source review;")
        for excerpt in (left, right)
    ):
        raise ValueError("Both excerpts require source review")
    if left.get("representation_kind", "policy_position") != right.get("representation_kind", "policy_position"):
        raise ValueError("Policy positions and campaign frames require separate comparison categories")
    relationship = review["relationship"]
    if relationship == "shared_position":
        if left["stance"] in {"", "position", "unclear", "unknown", "unmentioned", "not_stated"}:
            raise ValueError("A shared position requires a substantive stance, not an unknown/default label")
        if left["subtopic"] != right["subtopic"] or left["stance"] != right["stance"]:
            raise ValueError("Shared-position evidence must agree on mechanism and stance")
    elif relationship == "explicit_disagreement":
        if left["subtopic"] != right["subtopic"] or {left["stance"], right["stance"]} != {"support", "oppose"}:
            raise ValueError("Disagreement requires opposite stances on the same proposition")
    elif relationship not in {"different_scope", "different_strategy", "different_mechanism", "different_emphasis"}:
        raise ValueError(f"Unknown comparison relationship: {relationship}")


def archive_capture_date(source: dict) -> str:
    archive_match = (
        re.search(r"/web/(\d{4})(\d{2})(\d{2})\d*", source["final_url"])
        if urlparse(source["final_url"]).hostname == "web.archive.org" else None
    )
    return "-".join(archive_match.groups()) if archive_match else ""


def source_evidence_date(
    source: dict, election_date: str, cutoff: str, *, verified_available_by: str = "",
) -> tuple[str, str]:
    published = source.get("publication_date")
    capture_date = archive_capture_date(source)
    revised = source.get("source_updated_date") or ""
    if revised and revised > election_date:
        raise ValueError("Policy source revision is outside the primary campaign window")
    if revised and revised > cutoff:
        raise ValueError("Policy source revision postdates the research cutoff")
    if not published and source.get("publication_month"):
        year, month = map(int, source["publication_month"].split("-"))
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        window = campaign_window_for_election(election_date)
        if not window.contains(start) or not window.contains(end) or end.isoformat() > cutoff:
            raise ValueError("Publication-month interval does not prove pre-primary, in-window timing")
        if not source.get("publication_period_evidence", {}).get("exact_quote"):
            raise ValueError("Publication-month interval requires retained edition evidence")
        return max(end.isoformat(), revised), capture_date
    if source.get("available_by_date") and verified_available_by != source["available_by_date"]:
        raise ValueError("Publisher availability bounds require validated linked publication evidence")
    published_version = max(
        (value for value in (published, revised) if value),
        default="",
    )
    evidence_date = published_version or capture_date or verified_available_by
    if source.get("version_timing_basis") == "pre_primary_archived_campaign_platform":
        version_date = archived_campaign_version_date(source, election_date)
        if not version_date:
            raise ValueError("Campaign-version timing requires an older original date and an in-window retained platform replay")
        evidence_date = version_date
    if not evidence_date:
        raise ValueError("An undated current source cannot establish a pre-primary policy")
    if not campaign_window_for_election(election_date).contains(date.fromisoformat(evidence_date)):
        raise ValueError("Policy source is outside the primary campaign window")
    if evidence_date > cutoff:
        raise ValueError("Policy evidence postdates the research cutoff")
    return evidence_date, capture_date


def federal_seat(race: dict) -> tuple[str, str]:
    office = race.get("office", "")
    if re.search(r"\b(?:U\.?S\.?|United States)\s+Senat", office, re.I):
        return "Senate", "S"
    if not re.search(r"\b(?:U\.?S\.?|United States)\s+(?:House|Congress)", office, re.I):
        raise ValueError("Congressional policy review requires an identified federal office")
    match = re.search(r"\b(?:District\s+(\d+)|(\d+)(?:st|nd|rd|th)\s+Congressional)", race["jurisdiction"], re.I)
    if match:
        return "House", next(value for value in match.groups() if value).zfill(2)
    if re.search(r"\bat[- ]large\b", race["jurisdiction"], re.I):
        return "House", "00"
    raise ValueError("Congressional policy review requires an identified district")


def eligible_identity_rows(
    rows: list[dict], race: dict, scope: str, *, focal_ballot_names: set[str] | None = None,
) -> list[dict]:
    chamber, district = federal_seat(race)
    focal = focal_ballot_names or set(
        (race.get("endorsed_candidates") or race.get("endorsed_candidate", "")).split(" | ")
    )
    focal = {name.casefold() for name in focal if name}
    output = []
    for row in rows:
        if (
            row["state_code"] != race["state_code"] or row["election_date"] != race["election_date"]
            or row["chamber"] != chamber or row["district"] != district
            or str(row["write_in"]).casefold() == "true"
        ):
            continue
        if scope == "democratic_primary":
            democratic = canonical_party(row["primary_party"]) == "Democratic"
        else:
            democratic = (
                row.get("election_system", "").startswith("nonpartisan_")
                and (
                    canonical_party(row.get("party", "")) == "Democratic"
                    or (
                        scope == "nonpartisan_ballot_endorsed_vs_democrats"
                        and row["candidate_name"].casefold() in focal
                    )
                )
            )
        if democratic:
            output.append(row)
    return output


def reviewed_alias(race_id: str, name: str, aliases: dict) -> dict | None:
    alias = aliases.get((race_id, name))
    if alias is not None:
        return alias
    matches = [
        value for (candidate_race, _), value in aliases.items()
        if candidate_race == race_id and value["ballot_name"].casefold() == name.casefold()
    ]
    if len(matches) > 1:
        raise ValueError("Source speaker has multiple reviewed canonical identities")
    return matches[0] if matches else None


def validated_supplemental_review(path, races: dict, ballots: list[dict], cutoff: str) -> dict:
    bundle = read_json(path)
    scope = bundle.get("comparison_scope", "democratic_primary")
    if scope not in COMPARISON_SCOPES:
        raise ValueError("Unknown supplemental comparison scope")
    if bundle["review_method"] != "assistant_source_review_not_independent_human_gold":
        raise ValueError("Supplemental review must state its actual non-human-gold review method")
    sources = {}
    parsed = {}
    for source in bundle["sources"]:
        source_id = source["document_id"]
        if source_id in sources:
            raise ValueError(f"Duplicate supplemental source ID: {source_id}")
        raw_path = (ROOT / source["raw_path"]).resolve()
        if not raw_path.is_relative_to(ROOT.resolve()):
            raise ValueError("Supplemental source path leaves the repository")
        body = raw_path.read_bytes()
        if hashlib.sha256(body).hexdigest() != source["sha256"] or len(body) != int(source["bytes"]):
            raise ValueError(f"Supplemental raw source integrity failed: {source_id}")
        sources[source_id] = source
        if source["status"] in {"used", "timing_unverified"}:
            capture = RawDocumentCapture(
                document_id=source_id, source_url=source["url"], final_url=source["final_url"],
                retrieved_at=source["retrieved_at"],
                content_type=source.get("content_type") or mimetypes.guess_type(str(raw_path))[0] or "application/octet-stream",
                encoding=source.get("encoding", "utf-8"),
                content_bytes=body, byte_count=len(body), sha256=source["sha256"],
            )
            parsed[source_id] = extract_document_text(capture)
    identity_rows = list(ballots)
    roster = bundle.get("qualifying_roster")
    if roster:
        roster_path = (ROOT / roster["path"]).resolve()
        if not roster_path.is_relative_to(ROOT.resolve()) or hashlib.sha256(roster_path.read_bytes()).hexdigest() != roster["sha256"]:
            raise ValueError("Qualifying-roster identity snapshot failed integrity verification")
        authority_ids = roster.get("source_document_ids") or [roster["source_document_id"]]
        if any(sources[source_id]["status"] != "identity_only" for source_id in authority_ids):
            raise ValueError("Qualifying roster must point to separately retained identity-only evidence")
        for row in read_csv(roster_path):
            matches = [
                source_id for source_id in authority_ids
                if row["source_sha256"] == sources[source_id]["sha256"]
                and canonical_source_url(row["source_url"]) in {
                    canonical_source_url(sources[source_id]["url"]),
                    canonical_source_url(sources[source_id]["final_url"]),
                }
            ]
            if len(matches) != 1 or row.get("votes"):
                raise ValueError("Qualifying roster must match its retained authority and cannot invent votes")
            identity_rows.append({
                **row, "party": row["candidate_party"], "write_in": "false",
                "source_id": matches[0],
                "candidate_source_id": row.get("candidate_source_id") or row["source_locator"],
            })
    aliases = {}
    for alias in bundle.get("identity_aliases", []):
        key = alias["race_id"], alias["speaker"]
        if key in aliases or alias.get("review_status") not in {
            "accepted_direct_official_alias", "accepted_contextual_official_alias",
        }:
            raise ValueError("Ballot aliases require a unique explicit source review, not fuzzy matching")
        if not alias["notes"] or not alias["identity_document_ids"] or any(
            source_id not in sources for source_id in alias["identity_document_ids"]
        ):
            raise ValueError("Reviewed ballot alias lacks retained identity evidence")
        aliases[key] = alias
    statements = {}
    for excerpt in bundle["excerpts"]:
        source = sources[excerpt["document_id"]]
        if source["status"] not in {"used", "timing_unverified"}:
            raise ValueError("Excluded source cannot support a policy comparison")
        race = races[excerpt["race_id"]]
        alias = reviewed_alias(excerpt["race_id"], excerpt["speaker"], aliases)
        canonical_speaker = alias["speaker"] if alias else excerpt["speaker"]
        endorsed = set((race["endorsed_candidates"] or race["endorsed_candidate"]).split(" | "))
        opponents = set(race["opponent_candidates"].split(" | "))
        if (
            excerpt["role"] == "endorsed_candidate" and canonical_speaker not in endorsed
            or excerpt["role"] == "opponent_candidate" and (
                canonical_speaker not in opponents or canonical_speaker in endorsed
            )
            or excerpt["role"] not in {"endorsed_candidate", "opponent_candidate"}
        ):
            raise ValueError("Statement speaker/role differs from the canonical endorsement registry")
        if excerpt["election_date"] != race["election_date"]:
            raise ValueError("Reviewed excerpt election date differs from the registry")
        if source["status"] == "timing_unverified":
            if source.get("publication_date"):
                raise ValueError("A known publication date must be checked, not hidden as unverified timing")
            evidence_date, capture_date = "", archive_capture_date(source)
        else:
            evidence_date, capture_date = source_evidence_date(source, race["election_date"], cutoff)
        quote = excerpt["short_exact_quote"]
        matches = [
            p.locator for p in parsed[excerpt["document_id"]].paragraphs
            if normalize(quote) in normalize(p.text)
        ]
        if not quote.strip() or not matches or not excerpt["locator"] or not excerpt["notes"]:
            raise ValueError(f"Supplemental quotation lacks exact retained evidence: {excerpt['excerpt_id']}")
        ballot_name = alias["ballot_name"] if alias else excerpt["speaker"]
        focal_names = {
            aliases.get((excerpt["race_id"], name), {}).get("ballot_name", name) for name in endorsed
        }
        participants = eligible_identity_rows(identity_rows, race, scope, focal_ballot_names=focal_names)
        ballot_matches = [
            row for row in participants
            if row["candidate_name"].casefold() == ballot_name.casefold()
            and (
                alias is None or (
                    row["source_id"] == alias["ballot_source_id"]
                    and row["candidate_source_id"] == alias["ballot_candidate_source_id"]
                )
            )
        ]
        if not ballot_matches:
            raise ValueError(f"Reviewed speaker lacks the matching official ballot identity for this scope: {excerpt['speaker']}")
        if scope != "democratic_primary" and excerpt["role"] == "opponent_candidate" and any(
            canonical_party(row.get("party", "")) != "Democratic" for row in ballot_matches
        ):
            raise ValueError("Nonpartisan-ballot comparison candidate is not a declared Democrat")
        if excerpt["excerpt_id"] in statements:
            raise ValueError("Duplicate supplemental excerpt ID")
        statements[excerpt["excerpt_id"]] = {
            **excerpt, "quote": quote, "reviewed": "false",
            "canonical_speaker": canonical_speaker,
            "review_notes": "Assistant source review; " + excerpt["notes"],
            "source_url": source["url"], "publication_date": source["publication_date"] or "",
            "archive_url": source["final_url"] if capture_date else "",
            "capture_date": capture_date, "temporal_evidence_date": evidence_date,
            "quote_match_locators": " | ".join(matches), "source_sha256": source["sha256"],
            "ballot_name": ballot_name,
            "ballot_party": " | ".join(sorted({
                row.get("party") or row.get("primary_party", "") for row in ballot_matches
            })),
            "identity_resolution": alias["review_status"] if alias else "exact_case_insensitive_match",
            "identity_evidence_ids": " | ".join(alias["identity_document_ids"]) if alias else "",
            "identity_review_notes": alias["notes"] if alias else "",
            "identity_source_ids": " | ".join(sorted({row.get("source_id", "") for row in ballot_matches})),
            "identity_evidence_type": (
                "official_qualifying_roster"
                if roster and all(row.get("source_id") in authority_ids for row in ballot_matches)
                else "official_returns"
            ),
            "comparison_scope": scope,
            "election_timing": "future_scheduled" if race["election_date"] > cutoff else "past_scheduled_date",
            "timing_status": (
                "pre_primary_time_unverified" if source["status"] == "timing_unverified"
                else "verified_publication_date" if source.get("publication_date")
                else "verified_archive_capture"
            ),
        }
    rows = []
    timing_unverified_rows = []
    for comparison in bundle["comparisons"]:
        cited = [statements[key] for key in comparison["excerpt_ids"]]
        if len(cited) != 2 or {row["role"] for row in cited} != {"endorsed_candidate", "opponent_candidate"}:
            raise ValueError("Each supplemental comparison requires exactly two opposing candidate roles")
        left = next(row for row in cited if row["role"] == "endorsed_candidate")
        right = next(row for row in cited if row["role"] == "opponent_candidate")
        if any(row["race_id"] != comparison["race_id"] for row in cited):
            raise ValueError("Comparison evidence crosses races")
        race = races[comparison["race_id"]]
        validate_comparison(comparison, left, right, race, comparison_scope=scope)
        row = {
            "comparison_id": comparison["comparison_id"], "race_id": comparison["race_id"],
            "election_date": race["election_date"], "topic": left["topic"],
            "relationship": comparison["relationship"], "analysis": comparison["interpretation"],
            "review_method": bundle["review_method"],
            "comparison_scope": scope,
            "election_timing": "future_scheduled" if race["election_date"] > cutoff else "past_scheduled_date",
        }
        for side, excerpt in (("candidate", left), ("opponent", right)):
            row.update({
                f"{side}_name": excerpt["canonical_speaker"],
                f"{side}_source_speaker_name": excerpt["speaker"],
                f"{side}_excerpt_id": excerpt["excerpt_id"],
                f"{side}_quote": excerpt["quote"], f"{side}_source_url": excerpt["source_url"],
                f"{side}_publication_date": excerpt["publication_date"],
                f"{side}_archive_url": excerpt["archive_url"], f"{side}_capture_date": excerpt["capture_date"],
                f"{side}_locators": excerpt["quote_match_locators"],
                f"{side}_reviewed_locator": excerpt["locator"],
                f"{side}_source_sha256": excerpt["source_sha256"],
                f"{side}_timing_status": excerpt["timing_status"],
                f"{side}_ballot_name": excerpt["ballot_name"],
                f"{side}_ballot_party": excerpt["ballot_party"],
                f"{side}_identity_resolution": excerpt["identity_resolution"],
                f"{side}_identity_evidence_ids": excerpt["identity_evidence_ids"],
                f"{side}_identity_review_notes": excerpt["identity_review_notes"],
            })
        if any(excerpt["timing_status"] == "pre_primary_time_unverified" for excerpt in cited):
            row["timing_status"] = "pre_primary_time_unverified"
            row["timing_caveat"] = (
                "At least one authentic campaign statement or election-guide answer was retrieved after the primary "
                "without a verified publication date or pre-primary capture. This comparison "
                "does not establish the exact text available to voters before the election."
            )
            timing_unverified_rows.append(row)
        else:
            row["timing_status"] = "pre_primary_verified"
            rows.append(row)
    verified_statements = [
        row for row in statements.values() if row["timing_status"] != "pre_primary_time_unverified"
    ]
    timing_unverified_statements = [
        row for row in statements.values() if row["timing_status"] == "pre_primary_time_unverified"
    ]
    recovered_candidates = {(row["race_id"], row["canonical_speaker"]) for row in verified_statements}
    candidate_races = {}
    for statement in statements.values():
        for name in {statement["speaker"], statement["canonical_speaker"]}:
            candidate_races.setdefault(name, set()).add(statement["race_id"])
    for gap in bundle["unsuccessful_sources"]:
        candidate_races.setdefault(gap["candidate"], set()).add(gap["race_id"])
    attempts = []
    for attempt in [*bundle["unsuccessful_sources"], *bundle.get("source_attempts", [])]:
        race_id = attempt.get("race_id", "")
        if not race_id:
            matches = candidate_races.get(attempt["candidate"], set())
            if len(matches) != 1:
                raise ValueError("Source attempt lacks an unambiguous candidate/race identity")
            race_id = next(iter(matches))
        attempts.append({
            **attempt, "race_id": race_id,
            "source_candidate_name": attempt.get("source_candidate_name", attempt["candidate"]),
            "candidate": (reviewed_alias(race_id, attempt["candidate"], aliases) or {}).get("speaker", attempt["candidate"]),
            "attempted_url": attempt.get("attempted_url") or attempt.get("url") or "",
            "notes": attempt.get("notes", ""),
        })
    gaps = []
    for row in bundle["unsuccessful_sources"]:
        alias = reviewed_alias(row["race_id"], row["candidate"], aliases)
        name = alias["speaker"] if alias else row["candidate"]
        if (row["race_id"], name) not in recovered_candidates:
            gaps.append({
                **row, "candidate": name, "source_candidate_name": row["candidate"],
            })
    unverified_by_candidate = {
        (row["race_id"], row["canonical_speaker"]): row for row in timing_unverified_statements
    }
    gaps = [
        {
            **row,
            "attempted_url": unverified_by_candidate[(row["race_id"], row["candidate"])]["source_url"],
            "outcome": "pre_primary_timing_unverified",
            "notes": "Candidate statement recovered; pre-primary timing/version remains unverified. Prior failures remain in the attempt history.",
        }
        if (row["race_id"], row["candidate"]) in unverified_by_candidate else row
        for row in gaps
    ]
    existing_gaps = {(row["race_id"], row["candidate"]) for row in gaps}
    for statement in timing_unverified_statements:
        key = statement["race_id"], statement["canonical_speaker"]
        if key not in recovered_candidates and key not in existing_gaps:
            gaps.append({
                "race_id": key[0], "candidate": key[1], "attempted_url": statement["source_url"],
                "outcome": "pre_primary_timing_unverified",
                "notes": "Candidate answer recovered; publication date and pre-primary version remain unverified.",
            })
            existing_gaps.add(key)
    expected_candidates = {}
    for race_id in {row["race_id"] for row in statements.values()}:
        race = races[race_id]
        focal_names = {
            aliases.get((race_id, name), {}).get("ballot_name", name)
            for name in (race["endorsed_candidates"] or race["endorsed_candidate"]).split(" | ")
        }
        participants = eligible_identity_rows(identity_rows, race, scope, focal_ballot_names=focal_names)
        expected_candidates[race_id] = []
        canonical_names = set(race["all_candidates"].split(" | ")) if race.get("all_candidates") else {
            row["canonical_speaker"] for row in statements.values() if row["race_id"] == race_id
        }
        for participant in participants:
            matches = [
                name for name in canonical_names
                if (aliases.get((race_id, name), {}).get("ballot_name") or name).casefold()
                == participant["candidate_name"].casefold()
            ]
            if len(matches) > 1:
                raise ValueError("Multiple canonical names map to one ballot identity")
            expected_candidates[race_id].append(matches[0] if matches else participant["candidate_name"])
    return {
        "rows": rows, "statements": verified_statements,
        "timing_unverified_rows": timing_unverified_rows,
        "timing_unverified_statements": timing_unverified_statements,
        "sources": list(sources.values()),
        "gaps": gaps,
        "attempts": attempts,
        "expected_candidates": expected_candidates,
        "comparison_scope": scope,
        "review_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def export_policy_comparisons(*, download: bool = False) -> dict:
    config = read_json(CONFIG_DIR / "policy_comparison_reviews.json")
    cutoff = read_json(CONFIG_DIR / "sources.json")["research_cutoff"]
    reviews = config["comparisons"]
    if not reviews or len({row["comparison_id"] for row in reviews}) != len(reviews):
        raise ValueError("Policy reviews require a nonempty set of unique comparison IDs")
    documents = {row["document_id"]: row for row in read_csv(MANUAL_DIR / "documents.csv")}
    excerpts = {row["excerpt_id"]: row for row in read_csv(MANUAL_DIR / "excerpts.csv")}
    races = {row["race_id"]: row for row in read_csv(PROCESSED_DIR / "race_registry.csv")}
    output = ANALYSIS_DATA_DIR / "policy_evidence"
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "source_manifest.csv"
    previous = {
        row["document_id"]: row for row in read_csv(manifest_path)
    } if manifest_path.exists() else {}
    source_ids = {
        excerpts[review[field]]["document_id"]
        for review in reviews for field in ("candidate_excerpt_id", "opponent_excerpt_id")
    }
    manifest = {}
    extracted = {}
    for document_id in sorted(source_ids):
        document = documents[document_id]
        if download:
            capture = fetch_raw_document(document_id, document["url"])
            raw_path = persist_raw_document(capture, RAW_DIR / "policy_evidence")
            entry = {
                "document_id": document_id, "source_url": capture.source_url,
                "final_url": capture.final_url, "retrieved_at": capture.retrieved_at,
                "publication_date": document["publication_date"], "content_type": capture.content_type,
                "encoding": capture.encoding, "sha256": capture.sha256,
                "bytes": capture.byte_count, "raw_path": str(raw_path.relative_to(ROOT)),
            }
        else:
            if document_id not in previous:
                raise ValueError(f"Missing retained source for {document_id}; run with --download")
            entry = previous[document_id]
            body = (ROOT / entry["raw_path"]).read_bytes()
            if hashlib.sha256(body).hexdigest() != entry["sha256"] or len(body) != int(entry["bytes"]):
                raise ValueError(f"Retained source integrity failed: {document_id}")
            if entry["source_url"] != document["url"] or entry["publication_date"] != document["publication_date"]:
                raise ValueError(f"Source metadata changed and requires review: {document_id}")
            capture = RawDocumentCapture(
                document_id=document_id, source_url=entry["source_url"], final_url=entry["final_url"],
                retrieved_at=entry["retrieved_at"], content_type=entry["content_type"],
                encoding=entry["encoding"], content_bytes=body, byte_count=len(body), sha256=entry["sha256"],
            )
        extracted[document_id] = extract_document_text(capture)
        manifest[document_id] = entry
    rows = []
    for review in reviews:
        left = excerpts[review["candidate_excerpt_id"]]
        right = excerpts[review["opponent_excerpt_id"]]
        race = races[review["race_id"]]
        validate_comparison(review, left, right, race)
        row = {
            "comparison_id": review["comparison_id"], "race_id": review["race_id"],
            "election_date": race["election_date"], "topic": left["topic"],
            "relationship": review["relationship"], "analysis": review["analysis"],
            "review_method": "assistant_source_review_not_independent_human_gold",
            "timing_status": "pre_primary_verified",
        }
        for side, excerpt in (("candidate", left), ("opponent", right)):
            document = documents[excerpt["document_id"]]
            source_evidence_date(
                {**manifest[excerpt["document_id"]], "publication_date": document["publication_date"]},
                race["election_date"], cutoff,
            )
            locators = attributed_quote_locators(
                extracted[excerpt["document_id"]].paragraphs, excerpt["speaker"], excerpt["quote"],
            )
            if not locators:
                raise ValueError(f"Quote not found in the named speaker's answer: {excerpt['excerpt_id']}")
            row.update({
                f"{side}_name": excerpt["speaker"], f"{side}_excerpt_id": excerpt["excerpt_id"],
                f"{side}_quote": excerpt["quote"], f"{side}_source_url": document["url"],
                f"{side}_publication_date": document["publication_date"],
                f"{side}_locators": " | ".join(locators),
                f"{side}_source_sha256": manifest[excerpt["document_id"]]["sha256"],
                f"{side}_timing_status": "verified_publication_date",
            })
        rows.append(row)
    statements = {}
    for row in rows:
        for side in ("candidate", "opponent"):
            key = row[f"{side}_excerpt_id"]
            statements[key] = {
                "excerpt_id": key, "speaker": row[f"{side}_name"], "race_id": row["race_id"],
                "election_date": row["election_date"], "topic": row["topic"],
                "quote": row[f"{side}_quote"], "source_url": row[f"{side}_source_url"],
                "publication_date": row[f"{side}_publication_date"],
                "quote_match_locators": row[f"{side}_locators"],
                "source_sha256": row[f"{side}_source_sha256"],
                "reviewed": "false", "review_method": row["review_method"],
            }
    supplemental_sources = []
    timing_unverified_rows = []
    timing_unverified_statements = []
    excluded_statements = []
    gaps = []
    attempts = []
    review_hashes = {}
    expected_candidates = {}
    race_scopes = {}
    supplemental_paths = config.get("supplemental_review_files", [])
    historical_paths = config.get("historical_review_files", [])
    ballots = read_csv(ANALYSIS_DATA_DIR / "congressional" / "state_primary_results.csv") if supplemental_paths else []
    for filename in [*supplemental_paths, *historical_paths]:
        if filename in historical_paths:
            from .historical_policy import validate_historical_review

            prior = {
                **statements,
                **{row["excerpt_id"]: row for row in timing_unverified_statements},
            }
            bundle = validate_historical_review(MANUAL_DIR / filename, races, cutoff, prior)
        else:
            bundle = validated_supplemental_review(MANUAL_DIR / filename, races, ballots, cutoff)
        rows.extend(bundle["rows"])
        excluded_statements.extend(bundle.get("excluded_statements", []))
        timing_unverified_rows.extend(bundle["timing_unverified_rows"])
        timing_unverified_statements.extend({
            **statement, "review_method": "assistant_source_review_not_independent_human_gold",
        } for statement in bundle["timing_unverified_statements"])
        for statement in bundle["statements"]:
            if statement["excerpt_id"] in statements:
                raise ValueError("Excerpt IDs must be unique across reviews")
            statements[statement["excerpt_id"]] = {
                **statement, "review_method": "assistant_source_review_not_independent_human_gold",
            }
        supplemental_sources.extend(bundle["sources"])
        gaps.extend(bundle["gaps"])
        attempts.extend(bundle["attempts"])
        review_hashes[filename] = bundle["review_file_sha256"]
        for race_id, names in bundle["expected_candidates"].items():
            if race_id in expected_candidates and set(expected_candidates[race_id]) != set(names):
                raise ValueError("Source reviews disagree about the candidate comparison universe")
            expected_candidates[race_id] = names
            race_scopes[race_id] = bundle["comparison_scope"]
    recovered = {
        (row["race_id"], row.get("canonical_speaker", row["speaker"])) for row in statements.values()
    }
    qualified = {
        (row["race_id"], row.get("canonical_speaker", row["speaker"])) for row in timing_unverified_statements
    }
    unresolved = {}
    for gap in gaps:
        key = gap["race_id"], gap["candidate"]
        if key in recovered:
            attempts.append({**gap, "resolution": "subsequent_timing_verified_statement_recovered"})
            continue
        if key in qualified:
            gap = {**gap, "outcome": "pre_primary_timing_unverified",
                   "notes": "Candidate words recovered; timing remains qualified. Prior attempts are preserved."}
        unresolved[(key, gap["outcome"])] = gap
    gaps = list(unresolved.values())
    all_comparisons = [*rows, *timing_unverified_rows]
    statement_index = {**statements, **{row["excerpt_id"]: row for row in timing_unverified_statements}}
    representation_path = MANUAL_DIR / "policy_representation_reviews.json"
    if representation_path.exists():
        apply_representation_reviews(
            {**statement_index, **{row["excerpt_id"]: row for row in excluded_statements}},
            read_json(representation_path),
        )
    for row in all_comparisons:
        row["representation_kind"] = comparison_representation_kind(row, statement_index)
    if len({row["comparison_id"] for row in all_comparisons}) != len(all_comparisons):
        raise ValueError("Comparison IDs must be unique across reviews")
    write_csv(
        output / "reviewed_candidate_comparisons.csv", rows,
        list(dict.fromkeys(key for row in rows for key in row)),
    )
    statement_rows = list(statements.values())
    write_csv(
        output / "excluded_candidate_statements.csv", excluded_statements,
        list(dict.fromkeys([
            "excerpt_id", "speaker", "race_id", "election_date", "quote",
            "scope_exclusion_reason", "scope_exclusion_source_url",
            *(key for row in excluded_statements for key in row),
        ])),
    )
    write_csv(
        output / "reviewed_candidate_statements.csv", statement_rows,
        list(dict.fromkeys(key for row in statement_rows for key in row)),
    )
    write_csv(
        output / "timing_unverified_candidate_statements.csv", timing_unverified_statements,
        list(dict.fromkeys(key for row in [*statement_rows, *timing_unverified_statements] for key in row)),
    )
    write_csv(
        output / "timing_unverified_candidate_comparisons.csv", timing_unverified_rows,
        list(dict.fromkeys(key for row in all_comparisons for key in row)),
    )
    campaign_frames = [
        row for row in [*statement_rows, *timing_unverified_statements]
        if row.get("representation_kind") == "campaign_frame"
    ]
    write_csv(
        output / "reviewed_campaign_frames.csv", campaign_frames,
        list(dict.fromkeys(key for row in [*statement_rows, *timing_unverified_statements] for key in row)),
    )
    write_csv(
        output / "supplemental_source_manifest.csv", supplemental_sources,
        list(dict.fromkeys([
            "document_id", "url", "final_url", "publication_date", "retrieved_at",
            "retrieved_at_precision", "raw_path", "sha256", "bytes", "status", "notes",
            *(key for source in supplemental_sources for key in source),
        ])),
    )
    write_csv(
        output / "source_recovery_gaps.csv", gaps,
        list(dict.fromkeys([
            "race_id", "candidate", "attempted_url", "outcome", "notes",
            *(key for gap in gaps for key in gap),
        ])),
    )
    write_csv(
        output / "source_recovery_attempts.csv", attempts,
        list(dict.fromkeys([
            "race_id", "candidate", "attempted_url", "outcome", "notes",
            *(key for attempt in attempts for key in attempt),
        ])),
    )
    all_statements = [*statement_rows, *timing_unverified_statements]
    coverage = []
    for race_id in sorted({row["race_id"] for row in all_statements}):
        race = races[race_id]
        endorsed = set((race["endorsed_candidates"] or race["endorsed_candidate"]).split(" | "))
        names = expected_candidates.get(race_id, race["all_candidates"].split(" | "))
        for candidate in sorted(set(names)):
            verified = [
                row for row in statement_rows
                if row["race_id"] == race_id and row.get("canonical_speaker", row["speaker"]) == candidate
            ]
            qualified = [
                row for row in timing_unverified_statements
                if row["race_id"] == race_id and row.get("canonical_speaker", row["speaker"]) == candidate
            ]
            coverage.append({
                "race_id": race_id, "state_code": race["state_code"],
                "jurisdiction": race["jurisdiction"], "election_date": race["election_date"],
                "candidate_name": candidate, "role": "endorsed" if candidate in endorsed else "opponent",
                "democratic_comparator_count_for_endorsed_group": len(set(names) - endorsed),
                "comparison_scope": race_scopes.get(race_id, "democratic_primary"),
                "election_timing": "future_scheduled" if race["election_date"] > cutoff else "past_scheduled_date",
                "timing_verified_statements": len(verified),
                "timing_unverified_statements": len(qualified),
                "statement_coverage": (
                    "has_timing_verified_statement" if verified else
                    "has_timing_unverified_statement_only" if qualified else "no_reviewed_statement"
                ),
                "full_platform_review": "not_established_by_excerpt_recovery",
                "source_urls": " | ".join(sorted({row["source_url"] for row in verified + qualified})),
                "excerpt_ids": " | ".join(row["excerpt_id"] for row in verified + qualified),
            })
    write_csv(output / "candidate_coverage.csv", coverage, list(coverage[0]))
    write_csv(manifest_path, list(manifest.values()), list(next(iter(manifest.values()))))
    summary = {
        "comparisons": len(rows), "races": len({row["race_id"] for row in rows}),
        "sources": len(manifest) + sum(row["status"] == "used" for row in supplemental_sources),
        "captured_sources": len(manifest) + len(supplemental_sources),
        "statements": len(statements),
        "timing_unverified_statements": len(timing_unverified_statements),
        "timing_unverified_comparisons": len(timing_unverified_rows),
        "timing_unverified_sources": sum(row["status"] == "timing_unverified" for row in supplemental_sources),
        "unresolved_candidate_source_gaps": len({(row["race_id"], row["candidate"]) for row in gaps}),
        "unresolved_discovery_candidates": len({
            (row["race_id"], row["candidate"]) for row in gaps
            if row["outcome"] != "pre_primary_timing_unverified"
        }),
        "candidates_with_timing_unverified_answers": len({
            (row["race_id"], row.get("canonical_speaker", row["speaker"])) for row in timing_unverified_statements
        }),
        "total_recovered_statements": len(statements) + len(timing_unverified_statements),
        "policy_position_comparisons": sum(row["representation_kind"] == "policy_position" for row in all_comparisons),
        "campaign_frame_comparisons": sum(row["representation_kind"] == "campaign_frame" for row in all_comparisons),
        "agenda_item_comparisons": sum(row["representation_kind"] == "agenda_item" for row in all_comparisons),
        "unspecified_kind_comparisons": sum(row["representation_kind"] == "unspecified" for row in all_comparisons),
        "scope_excluded_historical_statements": len(excluded_statements),
        "explicit_campaign_frame_statements": len(campaign_frames),
        "studied_primaries": len({row["race_id"] for row in coverage}),
        "studied_election_cases": len({row["race_id"] for row in coverage}),
        "future_election_cases": len({
            row["race_id"] for row in coverage if row["election_timing"] == "future_scheduled"
        }),
        "expected_candidates_in_studied_primaries": len(coverage),
        "expected_candidates_in_comparison_set": len(coverage),
        "candidates_with_at_least_one_statement": sum(
            row["statement_coverage"] != "no_reviewed_statement" for row in coverage
        ),
        "supplemental_review_hashes": review_hashes,
        "unique_candidate_pairs": len({
            tuple(sorted((row["candidate_name"], row["opponent_name"]))) for row in all_comparisons
        }),
        "unique_evidence_pairs": len({
            (
                row["candidate_name"], row["opponent_name"], row["topic"],
                row["candidate_quote"], row["opponent_quote"],
                row["candidate_source_sha256"], row["opponent_source_sha256"],
            ) for row in all_comparisons
        }),
        "complete_census": False, "review_method": "assistant_source_review_not_independent_human_gold",
        "limitations": [
            "These are candidates' attributed statements, not independent verification of their factual claims.",
            "An interview is not an adopted party platform, and party platforms are not imputed to individual candidates.",
            "A shared policy goal does not establish identical implementation details.",
            "The reviewed comparisons are a small source-backed subset, not a representative national estimate.",
            "Campaign material and guide answers without verified pre-primary timing are exported separately, not discarded or backdated.",
        ],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def ingest_reviewed_documents() -> None:
    export_policy_comparisons()
    output = ANALYSIS_DATA_DIR / "policy_evidence"
    sources = {row["source_url"]: row for row in read_csv(output / "source_manifest.csv")}
    queue = [{
        **row, "document_id": row["candidate_document_id"], "legacy_locators": row["locator"],
    } for row in read_csv(MANUAL_DIR / "candidate_documents.csv")
        if row["source_url"] in sources and row["analysis_scope"] == "candidate_excerpt"]
    if not queue:
        raise ValueError("No scoped manual candidate documents match the reviewed sources")

    def retained_capture(document_id, source_url):
        row = sources[source_url]
        body = (ROOT / row["raw_path"]).read_bytes()
        if hashlib.sha256(body).hexdigest() != row["sha256"]:
            raise ValueError("Reviewed raw source changed before corpus ingestion")
        return RawDocumentCapture(
            document_id=document_id, source_url=source_url, final_url=row["final_url"],
            retrieved_at=row["retrieved_at"], content_type=row["content_type"], encoding=row["encoding"],
            content_bytes=body, byte_count=len(body), sha256=row["sha256"],
        )

    raw_manifest = []
    for row in queue:
        capture = retained_capture(row["document_id"], row["source_url"])
        path = persist_raw_document(capture, RAW_DIR / "policy_evidence")
        raw_manifest.append(_raw_manifest_row(capture, path))
    _write_jsonl(output / "corpus_raw_manifest.jsonl", raw_manifest)
    run_candidate_document_extraction_batch(
        queue, replace(
            CandidateDocumentBatchPaths.default(),
            raw_dir=RAW_DIR / "policy_evidence",
            raw_manifest_path=output / "corpus_raw_manifest.jsonl",
        ),
        fetcher=retained_capture,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--ingest", action="store_true", help="Add only registered speaker excerpts to the candidate corpus")
    args = parser.parse_args()
    summary = export_policy_comparisons(download=args.download)
    if args.ingest:
        ingest_reviewed_documents()
    print(json.dumps(summary, indent=2))
