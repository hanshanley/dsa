"""Replay reviewed complete answer boundaries without inferring stance from question matching."""

import hashlib
import html
import json
import re
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlparse

from .document_corpus import (
    CandidateDocumentBatchPaths, RawDocumentCapture, candidate_document_id,
    extract_document_text, run_candidate_document_extraction_batch,
    _raw_manifest_row, _write_jsonl,
)
from .historical_policy import REVIEW_METHOD, linked_publication_bound, validate_publisher_dates, validate_publisher_record
from .io import read_csv, read_json, write_csv
from .paths import ANALYSIS_DATA_DIR, CONFIG_DIR, MANUAL_DIR, PROCESSED_DIR, ROOT
from .policy_comparison import archive_capture_date, normalize, source_evidence_date


def split_answers(paragraphs, document: dict, questions: list[dict]) -> list[dict]:
    """Require every reviewed heading, complete intervening answer, and the explicit stop marker."""
    starts = document["question_paragraphs"]
    end = document["end_paragraph"]
    if not questions or len(starts) != len(questions) or starts != sorted(set(starts)) or end <= starts[-1]:
        raise ValueError("Questionnaire boundaries are incomplete, repeated, or out of order")
    if len({q["id"] for q in questions}) != len(questions):
        raise ValueError("Question IDs must be unique")
    selected = document.get("answer_paragraphs")
    ranges = document.get("answer_ranges")
    answer_headings = document.get("answer_headings")
    if answer_headings is not None and (
        ranges is None or not isinstance(answer_headings, list)
        or len(answer_headings) != len(questions)
        or any(
            not isinstance(h, dict) or type(h.get("paragraph")) is not int
            or not isinstance(h.get("text"), str) or not h["text"].strip()
            for h in answer_headings
        )
    ):
        raise ValueError("Per-answer speaker headings require complete named answer ranges")
    section = document.get("candidate_heading")
    valid_section = (
        isinstance(section, dict) and isinstance(section.get("text"), str) and bool(section["text"].strip())
        and isinstance(section.get("paragraph"), int) and not isinstance(section["paragraph"], bool)
    )
    if section is not None and not valid_section:
        raise ValueError("Shared-question ranges require a valid candidate heading")
    prefixes = document.get("speaker_prefixes", [])
    if not isinstance(prefixes, list) or any(
        not isinstance(prefix, str) or not prefix.strip() or not prefix.rstrip().endswith(":")
        for prefix in prefixes
    ):
        raise ValueError("Interleaved answers require explicit speaker prefixes")
    if ranges is not None:
        if (
            selected is not None or len(ranges) != len(questions)
            or not (prefixes or valid_section)
            or any(
                not isinstance(value, list) or len(value) != 2
                or any(not isinstance(n, int) or isinstance(n, bool) for n in value)
                or value[0] > value[1] for value in ranges
            )
        ):
            raise ValueError("Shared-question ranges require an explicit candidate heading and complete ranges")
    if selected is not None and (
        len(selected) != len(questions) or not prefixes
        or any(not isinstance(number, int) or isinstance(number, bool) for number in selected)
    ):
        raise ValueError("Interleaved answers require one paragraph per question and explicit speaker prefixes")
    excluded_questions = document.get("analysis_excluded_questions", {})
    if not isinstance(excluded_questions, dict) or any(
        not isinstance(reason, str) or not reason.strip() for reason in excluded_questions.values()
    ):
        raise ValueError("Policy-corpus exclusions require explicit nonempty reasons")
    if set(excluded_questions) - {q["id"] for q in questions}:
        raise ValueError("Policy-corpus exclusion refers to an unknown question")
    by_index = {p.index: p for p in paragraphs}
    omitted = {}
    for exclusion in document.get("noncandidate_paragraphs", []):
        number = exclusion.get("paragraph")
        if (
            type(number) is not int or number in omitted or number in starts
            or not starts[0] < number < end or number not in by_index
            or not exclusion.get("reason") or not exclusion.get("exact_text")
            or by_index[number].text != exclusion["exact_text"]
        ):
            raise ValueError("Publisher-paragraph exclusion must identify exact reviewed noncandidate text")
        omitted[number] = exclusion
    if ranges is not None and section is not None and (
        section["paragraph"] not in by_index
        or normalize(by_index[section["paragraph"]].text) != normalize(section["text"])
        or any(section["paragraph"] >= start for start, _ in ranges)
    ):
        raise ValueError("Shared-question candidate heading does not match the retained source")
    if end not in by_index or normalize(by_index[end].text) != normalize(document["end_marker"]):
        raise ValueError("Questionnaire end marker changed or is missing")
    if set(document.get("answer_caveats", {})) - {q["id"] for q in questions}:
        raise ValueError("Questionnaire caveat refers to an unknown question")
    rows = []
    for index, question in enumerate(questions):
        start, stop = starts[index], starts[index + 1] if index + 1 < len(starts) else end
        if any(number not in by_index for number in range(start, stop)):
            raise ValueError("Questionnaire answer contains a missing paragraph")
        heading = by_index[start].text
        if question.get("numbered", True):
            match = re.fullmatch(r"(\d+)[.)]\s+(.+)", heading, re.S)
            if not match or int(match[1]) != index + 1:
                raise ValueError("Questionnaire heading numbering differs from the reviewed boundaries")
            prompt = match[2]
        else:
            prompt = heading
        accepted = {normalize(value) for value in [question["prompt"], *question.get("variants", [])]}
        if normalize(prompt) not in accepted:
            raise ValueError("Questionnaire prompt differs from the reviewed common question")
        if ranges is not None:
            first, last = ranges[index]
            if not start < first <= last < stop:
                raise ValueError("Selected answer range is outside its reviewed question boundaries")
            if answer_headings is not None:
                speaker = answer_headings[index]
                number = speaker["paragraph"]
                if (
                    number not in by_index or number + 1 != first or number <= start
                    or normalize(by_index[number].text) != normalize(speaker["text"])
                ):
                    raise ValueError("Selected answer does not immediately follow its reviewed speaker heading")
            answer = [by_index[number].text for number in range(first, last + 1)]
            answer_numbers = list(range(first, last + 1))
            locator = f"paragraphs {first}-{last}"
        elif selected is not None:
            number = selected[index]
            if not start < number < stop:
                raise ValueError("Selected answer is outside its reviewed question boundaries")
            text = by_index[number].text
            answer = [text]
            answer_numbers = [number]
            locator = f"paragraph {number}"
        else:
            answer = [by_index[number].text for number in range(start + 1, stop)]
            answer_numbers = list(range(start + 1, stop))
            locator = f"paragraphs {start + 1}-{stop - 1}"
        excluded = [number for number in answer_numbers if number in omitted]
        if excluded:
            answer_numbers = [number for number in answer_numbers if number not in omitted]
            answer = [by_index[number].text for number in answer_numbers]
            locator = " | ".join(f"paragraph {number}" for number in answer_numbers)
        if not answer or not all(text.strip() for text in answer):
            raise ValueError("Questionnaire answer is empty; do not invent a response")
        if prefixes:
            if not any(normalize(answer[0]).startswith(normalize(prefix)) for prefix in prefixes):
                raise ValueError("Selected answer does not belong to the reviewed speaker")
            others = set(document.get("all_speaker_prefixes", prefixes)) - set(prefixes)
            if any(normalize(text).startswith(normalize(prefix)) for text in answer for prefix in others):
                raise ValueError("Selected answer range includes another candidate's response")
        if any(re.match(r"^\d+[.)]\s", text) and "?" in text for text in answer):
            raise ValueError("An unscoped question appears inside a candidate answer")
        text = "\n\n".join(answer)
        exclusion_reason = (
            "nonpolicy_question" if not question.get("include_in_policy_corpus", True)
            else excluded_questions.get(question["id"], "")
        )
        rows.append({
            "question_id": question["id"], "topic": question["topic"],
            "question": question["prompt"], "original_question": heading,
            "complete_answer": text, "answer_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "question_locator": f"paragraph {start}",
            "answer_locator": locator,
            "answer_paragraph_count": len(answer),
            "question_scope": "nonpolicy_context" if not question.get("include_in_policy_corpus", True) else "policy_or_campaign",
            "pairing_basis": (
                "shared_published_topic_round"
                if document.get("response_format") == "published_topic_round"
                else "same_published_question"
            ),
            "corpus_exclusion_reason": exclusion_reason,
            "review_caveat": document.get("answer_caveats", {}).get(question["id"], ""),
            "excluded_publisher_paragraphs": " | ".join(
                f"paragraph {number}: {omitted[number]['reason']}" for number in excluded
            ),
        })
    return rows


def match_answers(rows: list[dict]) -> list[dict]:
    pairs = []
    if any(r.get("pairing_basis") not in {
        "same_published_question", "shared_published_topic_round",
    } for r in rows):
        raise ValueError("Answer matching requires an explicit question or topic-round basis")
    keys = [(r["bundle_id"], r["candidate_name"], r["question_id"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Repeated candidate/question answer")
    for left in rows:
        if left["role"] != "endorsed":
            continue
        for right in rows:
            if (
                right["role"] != "opponent" or right["bundle_id"] != left["bundle_id"]
                or right["race_id"] != left["race_id"] or right["question_id"] != left["question_id"]
            ):
                continue
            if left["pairing_basis"] != right["pairing_basis"]:
                raise ValueError("Matched answers disagree on their question/topic pairing basis")
            pairs.append({
                "bundle_id": left["bundle_id"], "race_id": left["race_id"],
                "question_id": left["question_id"], "topic": left["topic"], "question": left["question"],
                "question_scope": left["question_scope"],
                "pairing_basis": left["pairing_basis"],
                "endorsed_candidate": left["candidate_name"], "other_democrat": right["candidate_name"],
                "endorsed_complete_answer": left["complete_answer"],
                "other_complete_answer": right["complete_answer"],
                "endorsed_source_url": left["source_url"], "other_source_url": right["source_url"],
                "endorsed_answer_locator": left["answer_locator"], "other_answer_locator": right["answer_locator"],
                "endorsed_answer_sha256": left["answer_sha256"], "other_answer_sha256": right["answer_sha256"],
                "endorsed_timing_status": left["timing_status"], "other_timing_status": right["timing_status"],
                "review_caveats": " | ".join(filter(None, [left["review_caveat"], right["review_caveat"]])),
                "answer_scope_exclusions": " | ".join(dict.fromkeys(filter(None, [
                    left["corpus_exclusion_reason"], right["corpus_exclusion_reason"],
                ]))),
                "relationship": (
                    "shared_topic_not_stance_classified"
                    if left["pairing_basis"] == "shared_published_topic_round"
                    else "same_question_not_stance_classified"
                ),
                "interpretation_limit": (
                    "Shared edited topic round, not proof of identical unedited interview questions or policy agreement."
                    if left["pairing_basis"] == "shared_published_topic_round" else
                    "Same question does not establish agreement or disagreement; compound answers require proposition-level review."
                ),
            })
    return pairs


def _repository_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("Questionnaire source path leaves the repository")
    return path


def _candidate_heading_name(text: str) -> str:
    return re.sub(r"\s+\(D\)$", "", text.removesuffix(":").strip())


def build_questionnaire_answers() -> dict:
    config = read_json(MANUAL_DIR / "policy_complete_questionnaires.json")
    if config["review_method"] != REVIEW_METHOD:
        raise ValueError("Complete answer boundaries must identify their actual review method")
    races = {r["race_id"]: r for r in read_csv(PROCESSED_DIR / "race_registry.csv")}
    cutoff = read_json(CONFIG_DIR / "sources.json")["research_cutoff"]
    rows, jobs, manifest, coverage = [], [], [], []
    if len({b["id"] for b in config["bundles"]}) != len(config["bundles"]):
        raise ValueError("Questionnaire bundle IDs must be unique")
    for bundle in config["bundles"]:
        response_format = bundle.get("response_format", "questionnaire")
        if response_format not in {"questionnaire", "published_topic_round"}:
            raise ValueError("Unknown published response format")
        source_type = "candidate_interview" if response_format == "published_topic_round" else "candidate_questionnaire"
        race = races[bundle["race_id"]]
        if race["scope_kind"] != "tracked_dsa_endorsed_democratic_primary":
            raise ValueError("Questionnaire bundle is outside the tracked Democratic-primary scope")
        endorsed = set((race["endorsed_candidates"] or race["endorsed_candidate"]).split(" | "))
        names = set(race["all_candidates"].split(" | "))
        review = read_json(_repository_path(bundle["review_path"]))
        if review["review_method"] != REVIEW_METHOD:
            raise ValueError("Questionnaire source association lacks a source review")
        sources = {s["document_id"]: s for s in review["sources"]}
        covered = set()
        speaker_prefixes = sorted({
            prefix for document in bundle["documents"] for prefix in document.get("speaker_prefixes", [])
        })
        for document in bundle["documents"]:
            document = {**document, "all_speaker_prefixes": speaker_prefixes, "response_format": response_format}
            name = document["candidate_name"]
            source = sources[document["source_id"]]
            if name not in names or name in covered:
                raise ValueError("Questionnaire candidate is absent from the race or repeated")
            covered.add(name)
            role = "endorsed" if name in endorsed else "opponent"
            associated = [
                e for e in review["excerpts"]
                if e["document_id"] == source["document_id"] and e["speaker"] == name
                and e["race_id"] == race["race_id"] and e["election_date"] == race["election_date"]
                and e["role"] == ("endorsed_candidate" if role == "endorsed" else "opponent_candidate")
            ]
            if not associated:
                raise ValueError("Full answers need an existing reviewed source/candidate/race association")
            if document.get("speaker_prefixes"):
                names_on_source = {name, *(e.get("source_speaker") or name for e in associated)}
                if any(
                    prefix.rstrip().removesuffix(":").strip() not in names_on_source
                    for prefix in document.get("speaker_prefixes", [])
                ):
                    raise ValueError("Interleaved speaker prefix conflicts with the reviewed candidate identity")
            if "answer_ranges" in document and not document.get("speaker_prefixes"):
                names_on_source = {name, *(e.get("source_speaker") or name for e in associated)}
                heading_name = _candidate_heading_name(document.get("candidate_heading", {}).get("text", ""))
                if heading_name not in names_on_source:
                    raise ValueError("Shared-question heading conflicts with the reviewed candidate identity")
                if any(
                    _candidate_heading_name(h.get("text", "")) not in names_on_source
                    for h in document.get("answer_headings", [])
                ):
                    raise ValueError("Per-answer heading conflicts with the reviewed candidate identity")
            if source["status"] not in {"used", "timing_unverified"}:
                raise ValueError("An excluded or identity-only source cannot supply complete answers")
            raw_path = _repository_path(source["raw_path"])
            body = raw_path.read_bytes()
            if len(body) != int(source["bytes"]) or hashlib.sha256(body).hexdigest() != source["sha256"]:
                raise ValueError("Complete questionnaire source failed byte/hash validation")
            validate_publisher_record(source)
            validate_publisher_dates(source, body)
            if source["status"] == "used":
                source_evidence_date(source, race["election_date"], cutoff,
                                     verified_available_by=linked_publication_bound(source, sources))
                if (source.get("source_updated_date") or "") > race["election_date"]:
                    raise ValueError("A revised questionnaire needs an explicit timing qualification")
            elif not source.get("notes"):
                raise ValueError("Timing-unverified questionnaire needs an explicit qualification")
            scope = [document["question_paragraphs"], document["end_paragraph"]]
            if "answer_paragraphs" in document:
                scope.append(document["answer_paragraphs"])
            if "answer_ranges" in document:
                scope.append(document["answer_ranges"])
            if document.get("noncandidate_paragraphs"):
                scope.append(document["noncandidate_paragraphs"])
            scope_hash = hashlib.sha256(json.dumps(scope, separators=(",", ":")).encode()).hexdigest()[:12]
            # Preserve answer-corpus IDs when the source's genre is refined.
            document_id = (
                candidate_document_id(name, race["race_id"], source["url"], "candidate_questionnaire")
                + "-answers-" + source["sha256"][:12] + "-" + scope_hash
            )
            capture = RawDocumentCapture(
                document_id, source["url"], source["final_url"], source["retrieved_at"],
                source["content_type"], source.get("encoding", "utf-8"), body, len(body), source["sha256"],
            )
            answers = split_answers(extract_document_text(capture).paragraphs, document, bundle["questions"])
            policy_answers = [a for a in answers if not a["corpus_exclusion_reason"]]
            timing = "pre_primary_supported" if source["status"] == "used" else "pre_primary_time_unverified"
            for answer in answers:
                rows.append({
                    "bundle_id": bundle["id"], "race_id": race["race_id"], "election_date": race["election_date"],
                    "candidate_name": name, "role": role, **answer,
                    "source_id": source["document_id"],
                    "metadata_document_id": (
                        document_id if source["status"] == "used" and not answer["corpus_exclusion_reason"] else ""
                    ),
                    "source_url": source["url"], "final_url": source["final_url"],
                    "source_raw_path": source["raw_path"], "source_sha256": source["sha256"],
                    "publication_date": source.get("publication_date") or "",
                    "publication_month": source.get("publication_month") or "",
                    "source_updated_date": source.get("source_updated_date") or "",
                    "available_by_date": source.get("available_by_date") or "",
                    "archive_capture_date": archive_capture_date(source),
                    "timing_status": timing, "source_notes": source.get("notes", ""),
                    "review_method": REVIEW_METHOD,
                    "record_type": (
                        "complete_published_response_block_not_independent_stance_gold"
                        if response_format == "published_topic_round" else
                        "complete_candidate_answer_not_independent_stance_gold"
                    ),
                })
            if source["status"] != "used" or not policy_answers:
                existing = read_csv(PROCESSED_DIR / "candidate_document_metadata.csv")
                if any(r["document_id"] == document_id for r in existing):
                    raise ValueError("Previously enrolled questionnaire lost timing or answer eligibility; review its corpus enrollment")
                continue
            archive = source["final_url"] if urlparse(source["final_url"]).hostname == "web.archive.org" else ""
            jobs.append({
                "document_id": document_id, "candidate_name": name, "race_id": race["race_id"],
                "role": role, "election_date": race["election_date"],
                "source_type": source_type, "source_url": source["url"],
                "archive_url": archive, "publication_date": source.get("publication_date") or "",
                "analysis_scope": "candidate_excerpt",
                "legacy_locators": " | ".join(a["answer_locator"] for a in policy_answers),
                "notes": "Complete reviewed answer blocks; prompts excluded. Not a full campaign-platform census or independent stance gold.",
            })
            manifest.append(_raw_manifest_row(capture, raw_path, archive_url=archive))
        coverage.append({
            "bundle_id": bundle["id"], "title": bundle["title"], "race_id": race["race_id"],
            "response_format": response_format,
            "question_count": len(bundle["questions"]), "covered_candidates": sorted(covered),
            "missing_registry_candidates": sorted(names - covered), "coverage_note": bundle["coverage_note"],
        })
    pairs = match_answers(rows)
    if not rows:
        raise ValueError("No complete questionnaire answers were configured")
    output = ANALYSIS_DATA_DIR / "policy_evidence" / "complete_questionnaires"
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "raw_manifest.jsonl"
    if manifest_path.exists():
        previous_ids = {
            json.loads(line)["document_id"]
            for line in manifest_path.read_text().splitlines() if line.strip()
        }
        missing = previous_ids - {job["document_id"] for job in jobs}
        if missing:
            raise ValueError(
                "Previously enrolled questionnaire documents were removed or rekeyed; "
                "retire their corpus scopes explicitly before replacing the enrollment manifest: "
                + ", ".join(sorted(missing))
            )
    _write_jsonl(manifest_path, manifest)

    def no_network(*args):
        raise AssertionError("Full-answer enrollment must use exact retained captures")

    paths = replace(CandidateDocumentBatchPaths.default(), raw_manifest_path=manifest_path)
    result = run_candidate_document_extraction_batch(jobs, paths, fetcher=no_network)
    if result.fetch_errors or result.metadata_errors or result.extraction_errors:
        raise ValueError("Complete questionnaire enrollment failed; inspect extraction metadata")
    metadata = {r["document_id"]: r for r in read_csv(paths.metadata_path)}
    paragraphs = {}
    for paragraph in read_csv(paths.paragraph_path):
        paragraphs.setdefault(paragraph["document_id"], []).append(paragraph)
    for job in jobs:
        retained = metadata[job["document_id"]]
        actual = "\n\n".join(p["text"] for p in paragraphs.get(job["document_id"], []))
        expected = "\n\n".join(r["complete_answer"] for r in rows if r["metadata_document_id"] == job["document_id"])
        if retained["extraction_status"] != "extracted" or actual != expected:
            raise ValueError("Enrolled full text differs from the reviewed complete answers")
    write_csv(output / "complete_candidate_answers.csv", rows, list(rows[0]))
    write_csv(output / "same_question_pairs.csv", pairs, list(pairs[0]) if pairs else ["bundle_id", "relationship"])
    summary = {
        "questionnaire_documents": len({(r["bundle_id"], r["candidate_name"]) for r in rows}),
        "enrolled_timing_supported_documents": len(jobs),
        "timing_qualified_documents_not_enrolled": len({
            (r["bundle_id"], r["candidate_name"]) for r in rows if r["timing_status"] == "pre_primary_time_unverified"
        }),
        "nonpolicy_answer_rows": sum(r["question_scope"] == "nonpolicy_context" for r in rows),
        "answer_rows_with_explicit_corpus_exclusion": sum(bool(r["corpus_exclusion_reason"]) for r in rows),
        "complete_answer_rows": len(rows),
        "matched_published_response_pairs": len(pairs),
        "matched_question_pairs": sum(r["pairing_basis"] == "same_published_question" for r in pairs),
        "shared_topic_round_pairs": sum(r["pairing_basis"] == "shared_published_topic_round" for r in pairs),
        "matched_nonpolicy_question_pairs": sum(r["question_scope"] == "nonpolicy_context" for r in pairs),
        "answer_words": sum(len(r["complete_answer"].split()) for r in rows),
        "source_reviewed_statement_or_comparison_count_added": 0,
        "hosted_model_inference_performed": False,
        "stance_classification_performed_by_this_export": False,
        "scope_limit": "Complete within the reviewed questionnaire boundaries, not the entire campaign or national census.",
        "coverage": coverage,
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "report" / "complete_questionnaire_comparison.html").write_text(
        render_questionnaires(rows, coverage), encoding="utf-8",
    )
    return summary


def render_questionnaires(rows: list[dict], coverage: list[dict]) -> str:
    esc = html.escape
    sections = []
    for bundle in coverage:
        answers = [r for r in rows if r["bundle_id"] == bundle["bundle_id"]]
        names = list(dict.fromkeys(r["candidate_name"] for r in answers))
        questions = {r["question_id"]: r["question"] for r in answers}
        lookup = {(r["candidate_name"], r["question_id"]): r for r in answers}
        headers = []
        for name in names:
            roles = {r["role"] for r in answers if r["candidate_name"] == name}
            if len(roles) != 1 or not roles <= {"endorsed", "opponent"}:
                raise ValueError("Questionnaire candidate has inconsistent or unknown comparison roles")
            label = "DSA-endorsed" if "endorsed" in roles else "Other Democrat"
            headers.append("<th scope='col'>" + esc(name) + "<br><small>" + label + "</small></th>")
        body = []
        for question_id, question in questions.items():
            cells = []
            for name in names:
                row = lookup[name, question_id]
                url = row["source_url"]
                if urlparse(url).scheme not in {"https", "http"}:
                    raise ValueError("Questionnaire source link must be HTTP(S)")
                cells.append(
                    "<td><div class='answer'>" + esc(row["complete_answer"]) + "</div><p class='caveat'>"
                    + esc(" | ".join(filter(None, [
                        row["review_caveat"], row["corpus_exclusion_reason"], row.get("excluded_publisher_paragraphs", ""),
                    ])))
                    + "</p><small>" + esc(row["answer_locator"]) + " | "
                    + esc(row["timing_status"]) + "</small><p><a href='" + esc(url, quote=True)
                    + "' rel='noopener noreferrer'>Original source</a></p></td>"
                )
            body.append("<tr><th scope='row'>" + esc(question) + "</th>" + "".join(cells) + "</tr>")
        sections.append(
            "<section><h2>" + esc(bundle["title"]) + "</h2><p>" + esc(bundle["coverage_note"])
            + "</p><p>Registry candidates without this questionnaire: "
            + esc(", ".join(bundle["missing_registry_candidates"]) or "None")
            + "</p><div class='table'><table><thead><tr><th>"
            + ("Published topic prompt" if bundle.get("response_format") == "published_topic_round" else "Question")
            + "</th>"
            + "".join(headers)
            + "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div></section>"
        )
    return """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Complete candidate questionnaire comparisons</title><style>
body{font:15px/1.5 system-ui,sans-serif;margin:24px;color:#20252b}p{max-width:1100px}
.table{overflow:auto;max-height:78vh;border:1px solid #ccd1d6}table{border-collapse:separate;border-spacing:0}
th,td{border-right:1px solid #dde1e5;border-bottom:1px solid #dde1e5;padding:14px;min-width:310px;vertical-align:top;background:white}
thead th{position:sticky;top:0;background:#eaf0f5;z-index:2}tbody th{position:sticky;left:0;max-width:310px;background:#f5f6f7;z-index:1}
.answer{white-space:pre-wrap}small{color:#56616d}.caveat{color:#79560b}a{color:#185f91}section{margin:32px 0}
</style><h1>Complete candidate answers, side by side</h1>
<p>Candidate answers are reproduced from retained source captures using reviewed paragraph boundaries.
Publisher prompts remain separate. Questionnaires preserve complete published answers; edited interview rounds preserve complete published response blocks, not necessarily the full unedited answers or identical original interview questions.
Matching a question or topic does not classify agreement or disagreement. These are not every campaign statement. Factual assertions and embedded quotations remain the speaker's statements, not independently verified facts.</p>
<p>Nonpolicy questions and answers with unresolved attribution concerns remain in the complete download, but are excluded from policy-model inputs.</p>
<p><a href="../data/analysis/policy_evidence/complete_questionnaires/complete_candidate_answers.csv" download>Download every complete answer</a> |
<a href="../data/analysis/policy_evidence/complete_questionnaires/same_question_pairs.csv" download>Download all full-answer pairs</a> |
<a href="platform_comparison.html">Source-reviewed policy comparisons</a></p>""" + "".join(sections) + "</html>\n"
