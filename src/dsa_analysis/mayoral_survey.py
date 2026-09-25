"""Expose the publisher's common-question 2025 mayoral dataset without inventing candidate quotations."""

import hashlib
import html
import json
from html.parser import HTMLParser

from .io import read_csv, read_json, write_csv
from .paths import ANALYSIS_DATA_DIR, PROCESSED_DIR, RAW_DIR, ROOT

COMMIT = "a420a293a42513df19e96423642a6ffd7fa1266a"
RACE_ID = "race-d0d830cb7a9e40e91152"
CANDIDATES = {
    "candidateZohran": "Zohran Kwame Mamdani",
    "candidateAdrienne": "Adrienne E. Adams",
    "candidateMichael": "Michael Blake",
    "candidateAndrew": "Andrew M. Cuomo",
    "candidateBrad": "Brad Lander",
    "candidateZellnor": "Zellnor Myrie",
    "candidateJessica": "Jessica Ramos",
    "candidateScott": "Scott M. Stringer",
    "candidateWhitney": "Whitney R. Tilson",
}
CAVEATS = {
    ("candidateAndrew", "question7"): (
        "campaign_disputes_option_fit",
        "Publisher explicitly says the campaign considers none of the offered options an accurate fit; preserve its mixed public/private and resident-partnership explanation.",
    ),
    ("candidateBrad", "question6"): (
        "supports_multiple_offered_approaches",
        "The campaign says all of the above; the publisher's single code is not an exclusive preference.",
    ),
    ("candidateJessica", "question6"): (
        "supports_multiple_offered_approaches",
        "The campaign says it wants all offered approaches; a single code cannot establish rejection of the others.",
    ),
    ("candidateZellnor", "question5a"): (
        "citation_date_conflict",
        "The cited podcast date says December2025 despite the June2025 data commit. Preserve the publisher record, but do not independently certify that reference's chronology.",
    ),
}


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain(value: str) -> str:
    parser = PlainText()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split())


def parse_response(value: str, question: dict) -> tuple[str, str, str, str]:
    parts = value.split("|", 2)
    code = parts[0].strip()
    if code not in {"0", "1", "2", "3", "4"}:
        raise ValueError(f"Unknown publisher response code: {code}")
    option = question.get("option" + code, "") if code != "0" else ""
    if code != "0" and not option:
        raise ValueError("Publisher response refers to an undefined option")
    return code, option, plain(parts[1]) if len(parts) > 1 else "", plain(parts[2]) if len(parts) > 2 else ""


def build_mayoral_survey() -> dict:
    folder = RAW_DIR / "policy_mayor_survey_2025" / "publisher_version"
    original = read_json(folder / "manifest.json")
    if any(row["commit_sha"] != COMMIT for row in original):
        raise ValueError("Survey inputs mix publisher versions")
    for record in read_json(folder / "parsed_manifest.json"):
        for path_key, hash_key in (("parsed_path", "parsed_sha256"), ("original_path", "original_sha256")):
            path = (ROOT / record[path_key]).resolve()
            if not path.is_relative_to(ROOT.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != record[hash_key]:
                raise ValueError("Survey source transformation failed integrity validation")
    commit = read_json(folder / "commit.json")
    if commit["sha"] != COMMIT or commit["commit"]["committer"]["date"][:10] != "2025-06-03":
        raise ValueError("Expected pre-primary publisher version metadata is missing")
    candidates = read_json(folder / "candidateContent.json")
    questions = read_json(folder / "questionContent.json")
    race = next(row for row in read_csv(PROCESSED_DIR / "race_registry.csv") if row["race_id"] == RACE_ID)
    registry_names = set(race["all_candidates"].split(" | "))
    if not set(CANDIDATES.values()).issubset(registry_names):
        raise ValueError("Publisher candidate-to-registry mapping needs review")
    rows = []
    for key, name in CANDIDATES.items():
        candidate = candidates[key]
        if candidate["party"] != "democrat":
            raise ValueError("Non-Democratic general-election candidate entered the primary comparison")
        for question_id, question in questions.items():
            field = "quizResponse" + question_id.removeprefix("question")
            if field not in candidate:
                raise ValueError("Publisher response record is incomplete; absence is not code zero")
            raw_response = candidate[field]
            code, label, explanation, reference = parse_response(raw_response, question)
            caveat, note = CAVEATS.get((key, question_id), ("", ""))
            rows.append({
                "race_id": RACE_ID, "election_date": race["election_date"], "candidate_name": name,
                "publisher_candidate_name": candidate["name"], "publisher_candidate_key": key,
                "role": "endorsed" if key == "candidateZohran" else "opponent",
                "question_id": question_id, "topic": question["subject"], "question": question["title"],
                "publisher_option_code": code, "publisher_option_text": label,
                "publisher_explanation": explanation, "publisher_reference": reference,
                "complete_original_response": raw_response,
                "response_status": "no_coded_option_not_no_position" if code == "0" else "publisher_coded_option",
                "supporting_explanation_present": bool(explanation),
                "review_caveat": caveat, "review_note": note,
                "record_type": "publisher_coded_survey_not_literal_candidate_quote_or_independent_stance_review",
                "publisher_commit": COMMIT, "publisher_version_date": "2025-06-03",
                "source_url": f"https://github.com/thecityny/2025-meet-your-mayor/blob/{COMMIT}/src/candidate-content.js",
                "attribution": "THE CITY and Gothamist, Meet Your Mayor2025. Original publisher license retained with source package.",
            })
    lookup = {(row["publisher_candidate_key"], row["question_id"]): row for row in rows}
    pairs = []
    for question_id in questions:
        left = lookup["candidateZohran", question_id]
        for key in CANDIDATES:
            if key == "candidateZohran":
                continue
            right = lookup[key, question_id]
            status = (
                "no_coded_option" if "0" in {left["publisher_option_code"], right["publisher_option_code"]} else
                "same_publisher_option" if left["publisher_option_code"] == right["publisher_option_code"] else
                "different_publisher_option"
            )
            pairs.append({
                "race_id": RACE_ID, "question_id": question_id, "question": left["question"], "topic": left["topic"],
                "endorsed_candidate": left["candidate_name"], "other_democrat": right["candidate_name"],
                "endorsed_option": left["publisher_option_text"], "other_option": right["publisher_option_text"],
                "code_relationship": status, "endorsed_explanation": left["publisher_explanation"],
                "other_explanation": right["publisher_explanation"],
                "caveats": " | ".join(filter(None, (left["review_note"], right["review_note"]))),
                "interpretation_limit": "Different codes are not automatically opposing platforms; read conditions and publisher explanations. These rows are not added to independently source-reviewed comparison counts.",
            })
    output = ANALYSIS_DATA_DIR / "policy_evidence" / "mayor_survey_2025"
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "complete_candidate_responses.csv", rows, list(rows[0]))
    write_csv(output / "same_question_comparisons.csv", pairs, list(pairs[0]))
    write_csv(output / "question_options.csv", [{
        "question_id": key, "topic": question["subject"], "question": question["title"],
        **{f"option{i}": question.get(f"option{i}", "") for i in range(1, 5)},
    } for key, question in questions.items()], ["question_id", "topic", "question", "option1", "option2", "option3", "option4"])
    summary = {
        "publisher_version": COMMIT, "publisher_version_date": "2025-06-03",
        "primary_candidates": len(CANDIDATES), "questions": len(questions),
        "complete_response_rows": len(rows), "matched_question_pairs": len(pairs),
        "no_coded_option_rows": sum(row["publisher_option_code"] == "0" for row in rows),
        "manually_noted_caveats": len(CAVEATS),
        "not_added_to_source_reviewed_statement_or_comparison_counts": True,
        "scope_limit": "Complete within the publisher's nine-candidate survey, not the entire eleven-candidate primary or every platform topic.",
        "missing_registry_candidates": sorted(registry_names - set(CANDIDATES.values())),
        "attribution": "THE CITY and Gothamist",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    headers = "".join(f"<th>{html.escape(name)}</th>" for name in CANDIDATES.values())
    table_rows = []
    for question_id, question in questions.items():
        cells = []
        for key in CANDIDATES:
            row = lookup[key, question_id]
            cells.append("<td><strong>" + html.escape(row["publisher_option_text"] or "No coded option") +
                         "</strong><p>" + html.escape(row["publisher_explanation"]) +
                         "</p><small>" + html.escape(row["publisher_reference"]) +
                         "</small><p class='caveat'>" + html.escape(row["review_note"]) + "</p></td>")
        table_rows.append("<tr><th>" + html.escape(question["title"]) + "</th>" + "".join(cells) + "</tr>")
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>2025 mayoral candidates: common-question comparison</title><style>
body{font:15px/1.5 system-ui,sans-serif;margin:24px;color:#20252b}p{max-width:1000px}
.table{overflow:auto;max-height:78vh;border:1px solid #ccd1d6}table{border-collapse:separate;border-spacing:0}
th,td{border-right:1px solid #dde1e5;border-bottom:1px solid #dde1e5;padding:14px;min-width:270px;vertical-align:top;background:white}
thead th{position:sticky;top:0;background:#eaf0f5;z-index:2}tbody th{position:sticky;left:0;max-width:300px;background:#f5f6f7;z-index:1}
small{color:#56616d}.caveat{color:#79560b}a{color:#185f91}</style><h1>2025 NYC mayoral platforms: the same questions, side by side</h1>
<p>Complete publisher-coded responses from <a href="https://projects.thecity.nyc/meet-your-mayor-2025-election-quiz-candidates/">THE CITY and Gothamist's Meet Your Mayor</a>, pinned to the June3 pre-primary source version.
These are the publisher's option assignments, not literal candidate quotations or new independent stance judgments. Conditions, disputed option fit, and uncoded answers are preserved. Missing a code does not mean having no position.</p>
<p><a href="../data/analysis/policy_evidence/mayor_survey_2025/complete_candidate_responses.csv" download>Download all complete responses</a> ·
<a href="../data/analysis/policy_evidence/mayor_survey_2025/same_question_comparisons.csv" download>Download same-question pairs</a> ·
<a href="platform_comparison.html">Source-reviewed race browser</a></p>
<div class="table"><table><thead><tr><th>Question</th>__HEADERS__</tr></thead><tbody>__ROWS__</tbody></table></div>
<p>Data and option wording: THE CITY and Gothamist. <a href="https://github.com/thecityny/2025-meet-your-mayor">Original source and license</a>.
No voter preferences are collected, inferred, or scored here.</p></html>"""
    (ROOT / "report" / "mayor_same_question_comparison.html").write_text(
        page.replace("__HEADERS__", headers).replace("__ROWS__", "".join(table_rows)), encoding="utf-8",
    )
    return summary


if __name__ == "__main__":
    print(json.dumps(build_mayoral_survey(), indent=2))
