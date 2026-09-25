"""Report observed analysis artifacts without equating execution with source completeness."""

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .io import read_csv, read_json
from .document_corpus import CANDIDATE_SCREENING_VERSION
from .paths import ROOT


def input_check(root: Path, expected: dict[str, str | None]) -> dict:
    checks = {}
    for name, digest in expected.items():
        path = root / name
        current = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        checks[name] = {
            "recorded_sha256": digest,
            "current_sha256": current,
            "matches": bool(digest and current == digest),
        }
    return {
        "status": "current" if checks and all(r["matches"] for r in checks.values()) else "stale_or_missing",
        "files": checks,
    }


def write_execution_audit(root: Path = ROOT) -> dict:
    analysis = root / "data/analysis"
    policy = analysis / "policy_evidence"
    lexical = read_json(root / "outputs/tables/text_analysis/analysis_manifest.json")
    model = read_json(analysis / "model_topic_validation.json")
    kde = read_json(analysis / "provisional_gte_kde/summary.json")
    coverage = read_json(policy / "historical_inventory_summary.json")
    sources = read_json(policy / "summary.json")
    questionnaires = read_json(policy / "complete_questionnaires/summary.json")
    interviews = [
        {"manifest": str(path.relative_to(root)), **read_json(path)}
        for path in sorted((policy / "complete_interview_answers").glob("*/summary.json"))
    ]
    platforms = [
        {"manifest": str(path.relative_to(root)), **read_json(path)}
        for path in sorted((policy / "complete_campaign_platforms").glob("*/summary.json"))
    ]
    corpus_name = "data/analysis/candidate_text_corpus.csv"
    corpus = read_csv(root / corpus_name)
    predictions = read_csv(analysis / "model_topic_classifications.csv")
    scores = read_csv(analysis / "provisional_gte_kde/segment_density_scores.csv")
    corpus_keys = [(r["corpus_segment_id"], r["text_sha256"], r["text"]) for r in corpus]
    prediction_keys = [
        (r["corpus_segment_id"], r["text_sha256"], r["text"]) for r in predictions
    ]

    lexical_inputs = dict(lexical.get("input_hashes", {}))
    for name in (
        corpus_name,
        "data/processed/candidate_document_analysis_segments.csv",
        "data/processed/candidate_document_metadata.csv",
        "data/processed/race_registry.csv",
        "data/manual/endorsements.csv",
    ):
        lexical_inputs.setdefault(name, None)
    lexical_stage = input_check(root, lexical_inputs)
    if lexical.get("screening_version") != CANDIDATE_SCREENING_VERSION:
        lexical_stage["status"] = "stale_screening_version"
    model_stage = input_check(root, {
        corpus_name: model.get("input_sha256"),
        "config/cap_topics.json": model.get("config_sha256"),
        "data/analysis/model_topic_classifications.csv": model.get("output_sha256"),
    })
    model_rows_match = (
        corpus_keys == prediction_keys
        and len(predictions) == model["total_rows"]
        and sum(bool(r["topic_code"]) for r in predictions) == model["classified_rows"]
        and sum(not r["topic_code"] for r in predictions) == model["unclassified_rows"]
    )
    if not model_rows_match:
        model_stage["status"] = "output_mismatch"
    kde_stage = input_check(root, {
        corpus_name: kde.get("candidate_corpus_sha256"),
        "data/processed/candidate_document_analysis_segments.csv": kde.get("input_sha256"),
        "data/processed/candidate_document_metadata.csv": kde.get("metadata_sha256"),
        "data/processed/race_registry.csv": kde.get("registry_sha256"),
    })
    if len(scores) != kde["retained_segments"]:
        kde_stage["status"] = "output_mismatch"
    if kde.get("screening_version") != CANDIDATE_SCREENING_VERSION:
        kde_stage["status"] = "stale_screening_version"
    if lexical_stage["status"] != "current":
        for stage in (model_stage, kde_stage):
            if stage["status"] == "current":
                stage["status"] = "stale_upstream"
    lexical_stage.update({
        "completed_at": lexical.get("completed_at"),
        "passages": len(corpus),
        "deduplicated_documents": lexical["candidate_documents"],
    })
    model_stage.update({
        "completed_at": model.get("completed_at"),
        "model": model["model_name"],
        "resolved_revision": model.get("resolved_model_revision"),
        "classified": model["classified_rows"],
        "unclassified": model["unclassified_rows"],
        "exact_input_output_rows_match": model_rows_match,
        "accuracy": None,
        "accuracy_reason": "No independent reviewed reference labels.",
    })
    kde_stage.update({
        "completed_at": kde.get("completed_at"),
        "model": kde["model_name"],
        "revision": kde["model_revision"],
        "passages": len(scores),
        "group_counts": kde["group_counts"],
        "candidate_cycle_units": kde["candidate_counts"],
        "dimensions": kde["selected_dimensions"],
        "interpretation": "Exploratory language density, not policy agreement or population inference.",
    })

    comparison_sets = {
        "timing_supported": read_csv(policy / "reviewed_candidate_comparisons.csv"),
        "timing_qualified": read_csv(policy / "timing_unverified_candidate_comparisons.csv"),
    }
    comparisons = [row for rows in comparison_sets.values() for row in rows]
    if len({r["comparison_id"] for r in comparisons}) != len(comparisons):
        raise ValueError("Execution audit found duplicate comparison IDs")
    if len(comparisons) != sources["unique_evidence_pairs"]:
        raise ValueError("Comparison exports disagree with the evidence summary")
    matrix = read_csv(policy / "race_policy_comparison_matrix.csv")
    inventory = read_csv(policy / "historical_candidate_inventory.csv")
    years = {}
    for year in sorted({r["election_year"] for r in inventory}):
        rows = [r for r in inventory if r["election_year"] == year]
        reviewed = sum(int(r["reviewed_statements"]) > 0 for r in rows)
        years[year] = {
            "candidate_race_records": len(rows),
            "with_reviewed_statements": reviewed,
            "without_reviewed_statements": len(rows) - reviewed,
            "individual_candidates": sum(r["entity_kind"] == "individual_candidate" for r in rows),
            "endorsed_ballot_campaigns": sum(r["entity_kind"] == "endorsed_ballot_campaign" for r in rows),
            "other_ballot_options": sum(r["entity_kind"] == "non_person_ballot_option" for r in rows),
            "policy_evidence_gaps": sum(
                r["entity_kind"] != "non_person_ballot_option" and not int(r["reviewed_statements"])
                for r in rows
            ),
        }
    relationships = {
        timing: dict(sorted(Counter(
            r["relationship"] for r in rows if r["representation_kind"] == "policy_position"
        ).items()))
        for timing, rows in comparison_sets.items()
    }
    jev = []
    for path in sorted(analysis.glob("jev*/summary.json")):
        summary = read_json(path)
        checks = input_check(root, {
            corpus_name: summary.get("corpus_sha256"),
            "data/analysis/model_topic_classifications.csv": summary.get("baseline_sha256"),
        })
        jev.append({
            "manifest": str(path.relative_to(root)),
            "input_status": checks["status"],
            "execution_status": summary["status"],
            "sample_rows": summary["sample_rows"],
            "live_requests_in_recorded_run": summary["live_requests"],
            "accuracy_improvement": summary.get("accuracy_difference"),
        })
    receipt = {
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "timestamp_meaning": "Audit observation time; only stage completed_at fields record execution.",
        "research_cutoff": read_json(root / "config/sources.json")["research_cutoff"],
        "complete_national_source_collection": coverage["complete"],
        "stages": {"lexical": lexical_stage, "local_classifier": model_stage, "candidate_kde": kde_stage},
        "source_review": {
            "statements": sources["total_recovered_statements"],
            "comparisons": len(comparisons),
            "direct_paired_cases": sum(int(r["comparison_count"]) > 0 for r in matrix),
            "policy_paired_cases": sum(int(r["policy_comparison_count"]) > 0 for r in matrix),
            "comparison_kinds": dict(Counter(r["representation_kind"] for r in comparisons)),
            "policy_relationships_by_timing": relationships,
            "review_method": sources["review_method"],
            "national_reuse_adds_independent_observations": False,
        },
        "complete_questionnaires": {
            key: questionnaires[key] for key in (
                "complete_answer_rows", "matched_question_pairs", "shared_topic_round_pairs",
            )
        },
        "complete_interview_exports": interviews,
        "complete_platform_exports": platforms,
        "strict_registry_coverage": coverage,
        "coverage_by_year": years,
        "jev_pilots": jev,
    }
    output = analysis / "execution_audit.json"
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    relation_lines = []
    for relationship in sorted(set().union(*(set(r) for r in relationships.values()))):
        supported = relationships["timing_supported"].get(relationship, 0)
        qualified = relationships["timing_qualified"].get(relationship, 0)
        relation_lines.append(
            f"| {relationship} | {supported} | {qualified} | {supported + qualified} |"
        )
    stage_lines = [
        f'| {name} | {stage["status"]} | {stage.get("completed_at") or "Not recorded"} |'
        for name, stage in receipt["stages"].items()
    ]
    year_lines = [
        f'| {year} | {row["individual_candidates"]} | {row["endorsed_ballot_campaigns"]} '
        f'| {row["other_ballot_options"]} | {row["with_reviewed_statements"]} '
        f'| {row["policy_evidence_gaps"]} |' for year, row in years.items()
    ]
    current_jev = [row for row in jev if row["input_status"] == "current"]
    jev_lines = [
        f'- `{row["manifest"]}`: {row["execution_status"]}; {row["sample_rows"]} passages; '
        f'{row["live_requests_in_recorded_run"]} live requests in the recorded run.'
        for row in current_jev
    ]
    (root / "report/analysis_execution.md").write_text(
        f"""# Analysis execution and source coverage

Audit observed at **{receipt["audited_at"]}**. Research cutoff: **{receipt["research_cutoff"]}**.
The machine-readable receipt is `data/analysis/execution_audit.json`, including input hashes.
An audit timestamp is not a claimed model execution time.

## Actual analysis artifacts

| Stage | Input/output status | Recorded completion time (UTC) |
| --- | --- | --- |
{chr(10).join(stage_lines)}

The lexical corpus contains **{len(corpus):,} passages** in
**{lexical["candidate_documents"]} deduplicated analysis documents**.
The local topic model assigned **{model["classified_rows"]:,}** passages and left
**{model["unclassified_rows"]:,}** unclassified. Topic assignment is not stance classification;
agreement with keyword rules is not measured accuracy. No independent reference labels exist.

The candidate KDE retains **{len(scores):,} passages**:
**{kde["group_counts"]["endorsed"]:,} endorsed / {kde["group_counts"]["opponent"]:,} other-Democrat**,
from **{sum(kde["candidate_counts"].values())} candidate-cycle units**.
It selected **{kde["selected_dimensions"]} dimensions**. Its candidate-cycle deduplication differs
from the classifier's group-cycle deduplication. It is exploratory and source-imbalanced:
names, geography, year, office, and document format can affect the result.
No retained region for a group is not evidence that its candidates have no distinctive policy.

## What the source-reviewed comparison actually measures

**{sources["total_recovered_statements"]:,} attributed statements** support
**{len(comparisons)} comparisons across {receipt["source_review"]["direct_paired_cases"]} directly
paired cases**; **{receipt["source_review"]["policy_paired_cases"]}** have policy-position pairs.
The remaining comparison kinds are kept separate from policy positions. Reused national
presidential material adds zero independent observations.

| Policy relationship | Timing-supported | Timing-qualified | Total selected pairs |
| --- | ---: | ---: | ---: |
{chr(10).join(relation_lines)}

These are assistant source reviews, not independent human gold. The categories count selected
evidence, not population prevalence, whole-platform similarity, or whole-campaign salience.
Different strategies or mechanisms can coexist; omissions never count as opposition.
Timing-qualified versions are not claimed to have been available before the primary.
Read the actual quotations and reviewed interpretations in `platform_comparison.html` and
`policy_comparison_findings.md`.

The complete-response export contains **{questionnaires["complete_answer_rows"]} published responses**,
**{questionnaires["matched_question_pairs"]} same-question pairs**, and
**{questionnaires["shared_topic_round_pairs"]} separately identified shared-topic interview pairs**.
Edited topic rounds do not prove identical unedited questions or complete original answers.
Complete published responses do not imply complete campaign platforms, and these pairings add no stance labels.
Separate complete-interview exports retain
**{sum(row["complete_published_response_blocks"] for row in interviews)} published response blocks**.
Those are the publisher's edited quotations, not verbatim unedited transcripts or additional
independent stance labels; full text and provenance are in `data/analysis/policy_evidence/complete_interview_answers/`.
The platform-text export retains **{sum(row["source_documents"] for row in platforms)} complete captured sources**
and **{sum(row["scoped_campaign_text_blocks"] for row in platforms)} separately scoped campaign-text blocks**.
Complete extracted sources retain navigation and embedded quotations for audit; they are not
automatically treated as current candidate positions. Existing model documents are reused rather
than duplicated. See `data/analysis/policy_evidence/complete_campaign_platforms/`.

## What is still missing

Nationwide source completeness: **{coverage["complete"]}**.
The strict registry contains **{coverage["in_scope_races"]} primary records** and
**{coverage["candidate_race_records"]:,} participant/ballot-option records**:
**{coverage["individual_candidate_race_records"]:,} individual candidate/race records**,
**{coverage["endorsed_ballot_campaign_records"]} endorsed ballot campaigns**, and
**{coverage["non_person_ballot_option_records"]} other non-person ballot choices**.
**{coverage["individual_candidate_records_with_reviewed_statements"]} individual candidate records**
have reviewed words. Ballot choices such as Scattered or No Preference are not people with
missing personal platforms; endorsed ballot campaigns still require campaign evidence.
The denominator excludes separately labeled shared-ballot contexts and does not count unique people.
Suspected duplicate registry contexts remain explicitly flagged pending source-preserving resolution.
Even a record with reviewed words may have only a partial platform.

| Cycle | Individual candidates | Endorsed ballot campaigns | Other ballot choices | With reviewed words | Policy evidence gaps |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(year_lines)}

Candidate-level gaps remain in `data/analysis/policy_evidence/historical_candidate_inventory.csv`;
paired and unpaired cases remain in `race_policy_comparison_matrix.csv`.
Missing sources are unknowns, not evidence of policy silence.
The acquisition worklist `policy_research_worklist.csv` groups repeated same-cycle presidential
records for research efficiency only. Its **{coverage["acquisition_work_units_with_missing_direct_review"]}**
open work units are not independent observations and do not establish source applicability.

## Jev

{chr(10).join(jev_lines) or "No prepared pilot matches both current corpus and baseline hashes."}

All older pilots remain separately accounted for in the JSON receipt. Preparation is not
inference. No accuracy-improvement claim is supported without executed predictions and
independently reviewed reference labels.
""",
        encoding="utf-8",
    )
    return receipt
