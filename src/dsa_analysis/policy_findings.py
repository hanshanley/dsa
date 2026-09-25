"""Summarize reviewed race-level policy evidence without estimating unobserved campaign salience."""

import json
import hashlib
from collections import Counter, defaultdict

from .io import read_csv, read_json, write_csv
from .paths import ANALYSIS_DATA_DIR, MANUAL_DIR, PROCESSED_DIR, ROOT
from .policy_comparison import comparison_representation_kind
from .policy_inventory import participant_kind

TOPIC_GROUPS = {
    "tax_policy": "tax_budget", "taxation": "tax_budget",
    "climate": "climate_environment", "climate_energy": "climate_environment",
    "environment": "climate_environment",
    "criminal_justice": "justice_and_public_safety", "public_safety": "justice_and_public_safety",
    "campaign_frame": "campaign_strategy_and_framing", "political_strategy": "campaign_strategy_and_framing",
    "campaign_approach": "campaign_strategy_and_framing",
}


def topic_group(topic: str) -> str:
    return TOPIC_GROUPS.get(topic, topic)


def evidence_pair_key(row: dict) -> tuple:
    return tuple(row.get(key, "") for key in (
        "candidate_name", "opponent_name", "topic", "candidate_quote", "opponent_quote",
        "candidate_source_sha256", "opponent_source_sha256",
    ))


def summarize_findings(
    statements: list[dict], comparisons: list[dict], races: dict,
    expected_candidates: dict | None = None,
) -> tuple[list, list, list]:
    expected_candidates = expected_candidates or {}
    statement_index = {row["excerpt_id"]: row for row in statements}
    by_candidate = defaultdict(list)
    for row in statements:
        by_candidate[(row["race_id"], row.get("canonical_speaker") or row["speaker"])].append(row)
    candidate_rows = []
    for (race_id, candidate), rows in sorted(by_candidate.items()):
        race = races[race_id]
        topics = sorted({topic_group(row["topic"]) for row in rows})
        candidate_rows.append({
            "race_id": race_id, "election_date": race["election_date"], "office": race["office"],
            "jurisdiction": race["jurisdiction"], "candidate_name": candidate,
            "role": "endorsed" if candidate in (race["endorsed_candidates"] or race["endorsed_candidate"]).split(" | ") else "opponent",
            "documented_topics": " | ".join(topics),
            "policy_statements": sum(row.get("representation_kind") == "policy_position" for row in rows),
            "campaign_frames": sum(row.get("representation_kind") == "campaign_frame" for row in rows),
            "other_or_unspecified_statements": sum(not row.get("representation_kind") for row in rows),
            "evidence": json.dumps([{
                "excerpt_id": row["excerpt_id"], "topic": row["topic"],
                "kind": row.get("representation_kind", "unspecified"),
                "claim_summary": row.get("claim_summary") or row.get("notes", ""),
                "quote": row.get("quote") or row.get("short_exact_quote", ""),
                "source_url": row["source_url"], "locator": row.get("quote_match_locators", ""),
                "source_type": row.get("source_type", "unspecified"),
                "timing": row.get("timing_status", "see_statement_export"),
            } for row in rows], ensure_ascii=False),
            "interpretation_limit": "Documented in selected reviewed evidence; not a complete platform or a measured campaign-priority ranking. Unobserved topics remain unknown.",
        })
    by_topic = defaultdict(dict)
    by_race = defaultdict(list)
    for row in comparisons:
        row = {**row, "representation_kind": comparison_representation_kind(row, statement_index)}
        by_topic[topic_group(row["topic"])][evidence_pair_key(row)] = row
        by_race[row["race_id"]].append(row)
    topic_rows = []
    for topic, unique in sorted(by_topic.items()):
        rows = list(unique.values())
        counts = Counter(row["relationship"] for row in rows)
        topic_rows.append({
            "topic_group": topic, "distinct_source_quote_pairs": len(rows),
            "election_cases": len({row["race_id"] for row in comparisons if topic_group(row["topic"]) == topic}),
            "shared_position": counts["shared_position"],
            "explicit_disagreement": counts["explicit_disagreement"],
            "different_mechanism": counts["different_mechanism"],
            "different_scope": counts["different_scope"],
            "different_strategy": counts["different_strategy"],
            "different_emphasis": counts["different_emphasis"],
            "timing_unverified_pairs": sum(row.get("timing_status") == "pre_primary_time_unverified" for row in rows),
            "comparison_ids": " | ".join(row["comparison_id"] for row in rows),
            "interpretation_limit": "Counts of selected reviewed evidence, not prevalence among all candidates or whole campaigns. Reused national source pairs are deduplicated.",
        })
    case_rows = []
    for race_id, race in sorted(races.items()):
        if (
            race["scope_kind"] != "tracked_dsa_endorsed_democratic_primary"
            and race_id not in by_race and race_id not in expected_candidates
        ):
            continue
        rows = by_race[race_id]
        kinds = Counter(row["representation_kind"] for row in rows)
        participants = expected_candidates.get(
            race_id, list(dict.fromkeys(race["all_candidates"].split(" | "))),
        )
        endorsed = set((race["endorsed_candidates"] or race["endorsed_candidate"]).split(" | "))
        ballot_options = [
            name for name in participants
            if participant_kind(race["office"], name, endorsed) == "non_person_ballot_option"
        ]
        participants = [name for name in participants if name not in ballot_options]
        covered = [name for name in participants if by_candidate.get((race_id, name))]
        missing = [name for name in participants if not by_candidate.get((race_id, name))]
        case_rows.append({
            "race_id": race_id, "election_date": race["election_date"], "state_code": race["state_code"],
            "office": race["office"], "jurisdiction": race["jurisdiction"],
            "endorsed_candidates": race["endorsed_candidates"] or race["endorsed_candidate"],
            "non_person_ballot_options": " | ".join(ballot_options),
            "other_candidates": " | ".join(name for name in participants if name not in endorsed),
            "source_reviewed_candidates": " | ".join(covered), "unreviewed_candidates": " | ".join(missing),
            "comparison_count": len(rows), "documented_topics": " | ".join(sorted({topic_group(row["topic"]) for row in rows})),
            "policy_comparison_count": kinds["policy_position"],
            "campaign_frame_comparison_count": kinds["campaign_frame"],
            "agenda_comparison_count": kinds["agenda_item"],
            "unspecified_comparison_count": kinds["unspecified"],
            "paired_evidence_types": " | ".join(sorted(kinds)) if rows else "none",
            "agreements": json.dumps([{
                "pair": f'{row["candidate_name"]} / {row["opponent_name"]}',
                "analysis": row["analysis"], "comparison_id": row["comparison_id"],
            } for row in rows if row["relationship"] == "shared_position"], ensure_ascii=False),
            "differences_and_emphases": json.dumps([{
                "pair": f'{row["candidate_name"]} / {row["opponent_name"]}',
                "relationship": row["relationship"], "analysis": row["analysis"],
                "comparison_id": row["comparison_id"],
            } for row in rows if row["relationship"] != "shared_position"], ensure_ascii=False),
            "study_status": "paired_reviewed_evidence" if rows else "standalone_reviewed_evidence" if covered else "not_source_reviewed",
            "completeness": "not_a_complete_platform_census",
        })
    return candidate_rows, topic_rows, case_rows


def build_policy_findings() -> dict:
    output = ANALYSIS_DATA_DIR / "policy_evidence"
    statements = []
    comparisons = []
    for filename in ("reviewed_candidate_statements.csv", "timing_unverified_candidate_statements.csv"):
        statements.extend(read_csv(output / filename))
    for filename in ("reviewed_candidate_comparisons.csv", "timing_unverified_candidate_comparisons.csv"):
        comparisons.extend(read_csv(output / filename))
    races = {row["race_id"]: row for row in read_csv(PROCESSED_DIR / "race_registry.csv")}
    expected = defaultdict(list)
    for row in read_csv(output / "candidate_coverage.csv"):
        expected[row["race_id"]].append(row["candidate_name"])
    candidates, topics, cases = summarize_findings(statements, comparisons, races, expected)
    alert_path = MANUAL_DIR / "policy_race_identity_alerts.json"
    alerts = {}
    if alert_path.exists():
        for alert in read_json(alert_path)["alerts"]:
            if alert["race_id"] not in races or alert["race_id"] in alerts:
                raise ValueError("Race identity alert has an unknown or repeated race")
            if not alert.get("notes") or not alert.get("evidence"):
                raise ValueError("Race identity alert requires retained evidence and review notes")
            for evidence in alert["evidence"]:
                path = (ROOT / evidence["raw_path"]).resolve()
                if not path.is_relative_to(ROOT.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != evidence["sha256"]:
                    raise ValueError("Race identity alert source integrity failed")
            alerts[alert["race_id"]] = alert
    for case in cases:
        alert = alerts.get(case["race_id"], {})
        case["identity_review_alert"] = alert.get("status", "")
        case["identity_review_notes"] = alert.get("notes", "")
    write_csv(output / "documented_campaign_positions.csv", candidates, list(candidates[0]))
    write_csv(output / "cross_race_policy_findings.csv", topics, list(topics[0]))
    write_csv(output / "race_policy_comparison_matrix.csv", cases, list(cases[0]))
    comparison_index = {row["comparison_id"]: row for row in comparisons}
    findings = []
    for finding in read_json(MANUAL_DIR / "policy_supported_findings.json")["findings"]:
        evidence = [comparison_index[key] for key in finding["comparison_ids"]]
        findings.append({
            "finding_id": finding["finding_id"], "title": finding["title"],
            "finding": finding["finding"], "limit": finding["limit"],
            "comparison_ids": " | ".join(finding["comparison_ids"]),
            "source_case_count": len({row["race_id"] for row in evidence}),
            "source_urls": " | ".join(sorted({
                row[key] for row in evidence for key in ("candidate_source_url", "opponent_source_url")
            })),
        })
    write_csv(output / "supported_cross_race_findings.csv", findings, list(findings[0]))
    statement_index = {row["excerpt_id"]: row for row in statements}
    grouped_comparisons = defaultdict(list)
    for comparison in comparisons:
        grouped_comparisons[comparison["race_id"]].append(comparison)
    lines = [
        "# Source-backed platform and campaign comparisons", "",
        "These briefs compare actual attributed commitments and campaign framing. "
        "They distinguish explicit disagreement from shared goals and complementary tools. "
        "Unreviewed subjects are unknown, not evidence of opposition or no platform.", "",
        "## Cross-race findings", "",
    ]
    for finding in findings:
        lines.extend([
            f"### {finding['title']}", "", finding["finding"], "",
            f"**Limit:** {finding['limit']}", "",
            f"Evidence IDs: `{finding['comparison_ids']}`", "",
        ])
    lines.extend(["## Election-level comparisons", ""])
    for race_id in sorted(grouped_comparisons, key=lambda key: (races[key]["election_date"], key)):
        race = races[race_id]
        lines.extend([
            f"### {race['election_date']} — {race['state_code']} {race['office']}, {race['jurisdiction']}",
            "", f"Registry ID: `{race_id}`", "",
        ])
        for comparison in grouped_comparisons[race_id]:
            lines.extend([
                f"**{comparison['candidate_name']} / {comparison['opponent_name']} — "
                f"{comparison['topic']} ({comparison['relationship']})**",
                "", comparison["analysis"], "",
            ])
            for side in ("candidate", "opponent"):
                evidence = statement_index[comparison[f"{side}_excerpt_id"]]
                claim = evidence.get("claim_summary") or evidence.get("notes") or evidence.get("quote")
                lines.append(
                    f"- **{comparison[f'{side}_name']}:** {claim} "
                    f"[Source]({comparison[f'{side}_source_url']}); "
                    f"`{comparison[f'{side}_excerpt_id']}`."
                )
            lines.extend([
                "", f"Timing: `{comparison.get('timing_status', 'see statement record')}`. "
                f"Identity basis: `{comparison.get('identity_resolution') or 'see statement-level provenance'}`.", "",
            ])
    (output / "platform_comparison_briefs.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    overview = [
        "# What the documented platforms and campaigns show", "",
        "This is a source-backed, case-comparative analysis—not a claim that every candidate "
        "in the national registry has a recovered complete platform. It studies attributed "
        "positions and candidate-authored campaign framing, not private beliefs or voter preferences.", "",
    ]
    for finding in findings:
        overview.extend([
            f"## {finding['title']}", "", finding["finding"], "",
            f"**Evidence:** `{finding['comparison_ids']}`", "", f"**Limit:** {finding['limit']}", "",
        ])
    overview.extend([
        "## What this does not establish", "",
        "- That every DSA-endorsed candidate supports every DSA organizational policy.",
        "- That other Democrats uniformly oppose single-payer, public housing, union rights or climate action.",
        "- That an omitted topic is opposed, or that a short answer is a complete platform.",
        "- That source counts measure spending, campaign attention, voter salience or electoral effectiveness.",
        "- That repeated national-platform material is independent state-specific campaigning.",
        "- That a publisher's forced-choice survey code captures every qualification in a candidate's answer.", "",
        "## Use the comparisons", "",
        "- `platform_comparison.html`: searchable, source-reviewed claims and pairs with dates and provenance.",
        "- `mayor_same_question_comparison.html`: all 18 questions and nine covered Democratic candidates from "
        "THE CITY/Gothamist's pre-primary survey, with original qualifications and uncoded answers preserved.",
        "- `complete_questionnaire_comparison.html`: complete candidate-authored answers from the reviewed multi-state "
        "questionnaires, with original prompts, answer boundaries, timing limits and full-answer downloads.",
        "- `../data/analysis/policy_evidence/race_policy_comparison_matrix.csv`: every registry case, including gaps.",
        "- `../data/analysis/policy_evidence/documented_campaign_positions.csv`: actual candidate claims and quotation anchors.", "",
        "- `../data/analysis/policy_evidence/excluded_candidate_statements.csv`: preserved historical statements excluded "
        "from active-endorsement comparisons, including a documented pre-primary revocation.", "",
        "Missing source material remains an explicit research gap. The dated and timing-qualified "
        "exports must not be silently pooled into a claim of complete pre-primary coverage.", "",
    ])
    (ROOT / "report" / "policy_comparison_findings.md").write_text("\n".join(overview), encoding="utf-8")
    summary = {
        "registry_cases_accounted_for": len(cases),
        "cases_with_comparisons": sum(row["comparison_count"] > 0 for row in cases),
        "candidate_race_profiles": len(candidates), "topic_groups_with_comparisons": len(topics),
        "unique_source_quote_pairs": sum(row["distinct_source_quote_pairs"] for row in topics),
        "complete": False,
        "meaning": "Observed policy commitments and campaign frames from reviewed sources; not population prevalence, full campaign salience, or an inference from missing topics.",
    }
    (output / "cross_race_findings_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(build_policy_findings(), indent=2))
