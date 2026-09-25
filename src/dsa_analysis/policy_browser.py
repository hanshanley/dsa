"""Build an offline browser for the actual candidate claims and paired comparisons."""

import json
from pathlib import Path

from .io import read_csv, read_json
from .paths import ANALYSIS_DATA_DIR, ROOT
from .national_platform_applicability import is_presidential_office, name_key


def script_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def shared_national_rows(cases: list[dict], comparisons: list[dict], applicability: list[dict]) -> list[dict]:
    case_index = {row["race_id"]: row for row in cases}
    comparison_index = {row["comparison_id"]: row for row in comparisons}
    seen = set()
    result = []
    for item in applicability:
        key = item["race_id"], item["source_comparison_id"]
        if key in seen:
            raise ValueError("Duplicate national comparison applicability")
        seen.add(key)
        if item["race_id"] not in case_index or item["source_comparison_id"] not in comparison_index:
            raise ValueError("National applicability refers to missing source evidence or race")
        source = comparison_index[item["source_comparison_id"]]
        target = case_index[item["race_id"]]
        if (
            item.get("new_independent_evidence") != "false"
            or item.get("evidence_scope") != "same_cycle_national_platforms_not_state_specific_campaigning"
            or source["race_id"] != item["source_review_race_id"]
            or source["election_date"][:4] != item["election_date"][:4]
            or target["election_date"] != item["election_date"]
            or source.get("timing_status") != "pre_primary_verified"
            or not is_presidential_office(target.get("office", ""))
            or name_key(item["candidate_name"]) != name_key(source["candidate_name"])
            or name_key(item["opponent_name"]) != name_key(source["opponent_name"])
            or item["candidate_name"] not in target["endorsed_candidates"].split(" | ")
            or item["opponent_name"] not in target["other_candidates"].split(" | ")
        ):
            raise ValueError("National applicability scope or temporal provenance is inconsistent")
        if source["race_id"] == item["race_id"]:
            continue
        result.append({
            **item, **source,
            "race_id": item["race_id"], "election_date": item["election_date"],
            "candidate_name": item["candidate_name"], "opponent_name": item["opponent_name"],
            "representation_kind": source.get("representation_kind", "unspecified"),
        })
    return result


def build_policy_browser() -> dict:
    directory = ANALYSIS_DATA_DIR / "policy_evidence"
    statements = [
        *read_csv(directory / "reviewed_candidate_statements.csv"),
        *read_csv(directory / "timing_unverified_candidate_statements.csv"),
    ]
    comparisons = [
        *read_csv(directory / "reviewed_candidate_comparisons.csv"),
        *read_csv(directory / "timing_unverified_candidate_comparisons.csv"),
    ]
    cases = read_csv(directory / "race_policy_comparison_matrix.csv")
    applicability_path = directory / "national_platform_applicability.csv"
    shared = shared_national_rows(
        cases, comparisons, read_csv(applicability_path) if applicability_path.exists() else [],
    )
    payload = {
        "statements": statements, "comparisons": comparisons,
        "cases": cases, "shared_national": shared,
        "findings": read_csv(directory / "supported_cross_race_findings.csv"),
        "summary": read_json(directory / "summary.json"),
    }
    html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Candidate platforms and campaign comparisons</title>
<style>
:root{font-family:system-ui,-apple-system,sans-serif;color:#20252b;background:#f5f6f7;line-height:1.5}
*{box-sizing:border-box}body{margin:0}main{max-width:1320px;margin:auto;padding:28px}
h1{font-size:1.9rem;line-height:1.2;margin:0 0 14px}h2{font-size:1.3rem}h3{font-size:1.05rem}
.muted{color:#58616b}.intro{max-width:1000px}.stats{font-variant-numeric:tabular-nums;padding:12px 0;font-weight:600}
.controls{display:flex;gap:12px;flex-wrap:wrap;margin:22px 0}label{display:flex;flex-direction:column;font-size:.85rem;gap:4px}
input,select{font:inherit;background:white;border:1px solid #b8bec4;border-radius:4px;padding:8px}input{min-width:260px}
.layout{display:grid;grid-template-columns:310px 1fr;gap:24px}.cases{max-height:75vh;overflow:auto;background:white;border:1px solid #d8dde1}
.case-button{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid #e4e7ea;background:white;padding:12px;cursor:pointer}
.case-button:hover,.case-button.active{background:#eaf0f5}.case-button small{display:block;color:#58616b}
.card{background:white;border:1px solid #d8dde1;border-radius:5px;padding:18px;margin:16px 0}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}.quote{border-left:3px solid #8ca2b4;padding-left:12px;color:#303d49}
.badge{display:inline-block;border:1px solid #c5ced5;padding:2px 7px;border-radius:3px;font-size:.78rem;margin:0 6px 5px 0}
.qualified{background:#fff6df;border-color:#d8c796}.source{font-size:.8rem;overflow-wrap:anywhere}a{color:#185f91}
details{margin:12px 0}summary{cursor:pointer}.empty{padding:22px;background:#fff;border:1px dashed #b9c0c6}
@media(max-width:800px){main{padding:16px}.layout,.pair{grid-template-columns:1fr}.cases{max-height:250px}}
</style></head><body><main>
<h1>What candidates proposed — and how they campaigned</h1>
<p class="intro muted">Compare attributed policy commitments, stated campaign priorities and campaign framing. Agreement, different tools and explicit disagreement are separate categories. Missing evidence is unknown—not opposition. These are selected source reviews, not complete platform inventories or a representative population estimate.</p>
<div class="stats" id="stats"></div>
<p class="muted" id="representation-stats"></p>
<p class="muted" id="national-stats"></p>
<details><summary>Source-supported cross-race findings</summary><div id="findings"></div></details>
<p class="source">Downloads:
<a href="../data/analysis/policy_evidence/reviewed_candidate_comparisons.csv" download>dated comparisons</a> ·
<a href="../data/analysis/policy_evidence/timing_unverified_candidate_comparisons.csv" download>timing-qualified comparisons</a> ·
<a href="../data/analysis/policy_evidence/documented_campaign_positions.csv" download>candidate claims and quotations</a> ·
<a href="../data/analysis/policy_evidence/race_policy_comparison_matrix.csv" download>whole-registry comparison matrix</a></p>
<p class="source"><a href="../data/analysis/policy_evidence/national_platform_applicability.csv" download>National-platform applicability</a>:
same-cycle presidential platforms may apply to several primary fields. Reuse adds no independent evidence
and does not establish state-specific campaigning or that a candidate was still actively campaigning.</p>
<p class="source">Cohort qualifications:
<a href="../data/manual/race_scope_resolutions.csv" download>documented exclusions</a> ·
<a href="../data/manual/policy_race_identity_corrections.json" download>official-source race corrections</a> ·
<a href="../data/manual/policy_race_identity_alerts.json" download>unresolved identity alerts</a> ·
<a href="../data/analysis/policy_evidence/excluded_candidate_statements.csv" download>preserved out-of-scope candidate words</a>.
A revoked endorsement is not counted as active at the primary; its historical evidence is retained separately.</p>
<p class="source">Source audits:
<a href="../data/analysis/policy_evidence/source_date_correction_audit.csv" download>corrected publication dates</a> ·
<a href="../data/analysis/policy_evidence/first_party_source_replacements.csv" download>original-source replacements</a> ·
<a href="../data/analysis/policy_evidence/archive_recovery_audit.csv" download>historical-replay recovery audit</a> ·
<a href="../data/analysis/policy_evidence/recovered_platform_texts.csv" download>complete recovered platform text</a>.
Election-context dates are not publication dates, and an old publication date does not erase a later revision.</p>
<p class="source"><a href="../data/processed/candidate_analysis_paragraph_exclusions.csv" download>Model page-control exclusions</a> ·
<a href="../data/analysis/policy_evidence/non_individual_ballot_records.csv" download>Non-individual ballot records</a> ·
<a href="../data/analysis/policy_evidence/policy_research_worklist.csv" download>Remaining policy-research worklist</a>:
excluded text and ballot choices remain auditable; neither exclusion nor missing evidence means policy opposition.</p>
<p class="source"><a href="mayor_same_question_comparison.html">Complete 18-question mayoral comparison</a>:
the separate THE CITY/Gothamist publisher-coded survey includes all nine covered Democratic candidates,
original explanations, uncoded responses and editorial caveats. Its rows are not added to the reviewed-claim counts here.</p>
<p class="source"><a href="complete_questionnaire_comparison.html">Complete candidate questionnaire answers</a>:
read the full responses alongside the same questions, with original source locators and missing participants visible.
These matched answers are not automatically labeled agreements or disagreements.</p>
<p class="source"><a href="../data/analysis/policy_evidence/complete_campaign_platforms/policy_presidential_2020_followup/complete_sources.csv" download>Complete retained presidential campaign-source text</a> ·
<a href="../data/analysis/policy_evidence/complete_campaign_platforms/policy_presidential_2020_followup/scoped_blocks.csv" download>Separately scoped platform blocks</a>:
full sources preserve navigation, citations and historical quotations for audit; these are not automatically current candidate positions or model inputs.</p>
<p class="source"><a href="../data/analysis/policy_evidence/complete_campaign_platforms/policy_arizona_2018_followup/complete_sources.csv" download>Complete recovered Arizona 2018 campaign sources</a> ·
<a href="../data/manual/policy_arizona_2018_source_dispositions.json" download>Arizona source-version and failed-route audit</a>:
original congressional platforms and candidate-authored articles; later state-house redirects are not substituted.</p>
<p class="source"><a href="../data/analysis/policy_evidence/complete_interview_answers/policy_new_york_2017/complete_responses.csv" download>Complete published Bay Ridge 2017 interview response blocks</a>:
four of five Democratic candidates, with reporter narration excluded. Published editing is preserved;
these are not unedited transcripts or complete campaign platforms.</p>
<p class="source"><a href="analysis_execution.md">Actual analysis execution and coverage audit</a>:
completed model stages, input fingerprints, selected policy relationships and remaining source gaps.
Preparing Jev requests is not live inference or evidence of higher accuracy.</p>
<p class="source"><a href="../data/analysis/policy_evidence/oregon_complete_submitted_statements.csv" download>Complete Oregon 2020 congressional statements</a>:
all five candidates' campaign-supplied programs from the original official primary pamphlet.
Endorsement quotations and attacks remain attributed campaign material, not independent facts.</p>
<div class="controls">
<label>Find a candidate, race or policy<input id="search" type="search" placeholder="Name, office, housing, healthcare…"></label>
<label>Election year<select id="year"><option value="">All years</option></select></label>
<label>Evidence<select id="mode"><option value="available">Available comparisons, including shared national evidence</option><option value="paired">Race-linked reviewed comparisons only</option><option value="national">Shared national-platform evidence</option><option value="words">Records with directly reviewed candidate words</option><option value="all">All registry cases, including gaps</option></select></label>
<label>Timing<select id="timing"><option value="all">Include explicit timing qualifications</option><option value="verified">Dated/pre-primary-supported only</option></select></label>
<label>Comparison content<select id="representation"><option value="all">Policy positions and campaign framing</option><option value="policy_position">Policy-position pairs only</option><option value="campaign_frame">Campaign-framing pairs only</option><option value="agenda_item">Agenda items only</option><option value="unspecified">Not yet categorized</option></select></label>
</div>
<div class="layout"><nav class="cases" id="cases" aria-label="Election cases"></nav><section id="detail" aria-live="polite"></section></div>
<script id="evidence-data" type="application/json">__DATA__</script>
<script>
"use strict";
const data=JSON.parse(document.getElementById("evidence-data").textContent);
const statements=new Map(data.statements.map(x=>[x.excerpt_id,x]));
let active=null;
const byRace=new Map(),wordsByRace=new Map(),nationalByRace=new Map();
for(const x of data.comparisons){if(!byRace.has(x.race_id))byRace.set(x.race_id,[]);byRace.get(x.race_id).push(x)}
for(const x of data.statements){if(!wordsByRace.has(x.race_id))wordsByRace.set(x.race_id,[]);wordsByRace.get(x.race_id).push(x)}
for(const x of data.shared_national){if(!nationalByRace.has(x.race_id))nationalByRace.set(x.race_id,[]);nationalByRace.get(x.race_id).push(x)}
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n};
const isQualified=x=>x.timing_status==="pre_primary_time_unverified";
const permitted=x=>(document.getElementById("timing").value!=="verified"||!isQualified(x))&&(document.getElementById("representation").value==="all"||(x.representation_kind||"unspecified")===document.getElementById("representation").value);
function link(url){try{const parsed=new URL(url);if(!["http:","https:"].includes(parsed.protocol))return el("span",url);const a=el("a","Original source");a.href=parsed.href;a.target="_blank";a.rel="noopener noreferrer";return a}catch{return el("span","Source URL unavailable")}}
function evidenceCard(s,name){
 const box=el("div");box.append(el("h3",name||s.canonical_speaker||s.speaker));
 const kind=s.representation_kind||"attributed statement";box.append(el("span",kind.replaceAll("_"," "),"badge"));
 if(isQualified(s))box.append(el("span","Pre-primary version/timing unresolved","badge qualified"));
 box.append(el("p",s.claim_summary||s.notes||s.quote||s.short_exact_quote));
 box.append(el("p","“"+(s.quote||s.short_exact_quote||"")+"”","quote"));
 const meta=el("div",undefined,"source");meta.append(link(s.archive_url||s.source_url));
 const date=s.publication_date?` Published ${s.publication_date}.`:s.publication_month?` Publication month ${s.publication_month}; exact day not asserted.`:s.capture_date?` Archived ${s.capture_date}.`:s.available_by_date?` Available by publisher release ${s.available_by_date}.`:" Exact publication date unknown.";
 const revision=s.source_updated_date?` Revised ${s.source_updated_date}.`:"";
 const archive=s.capture_date&&s.publication_date?` Archived ${s.capture_date}.`:"";
 meta.append(document.createTextNode(date+revision+archive+" "+(s.quote_match_locators||s.locator||"")));
 box.append(meta);
 const d=el("details");d.append(el("summary","Provenance and limitations"));
 if(s.answer_context)d.append(el("p","Publisher question and answer context (not all candidate-authored): "+s.answer_context,"source"));
 if(s.archive_url)d.append(el("p","Original source address: "+s.source_url,"source"));
 d.append(el("p","Evidence ID: "+s.excerpt_id,"source"));
 d.append(el("p","Source SHA-256: "+s.source_sha256,"source"));
 if(s.temporal_evidence_date)d.append(el("p","Version/availability date used for temporal eligibility: "+s.temporal_evidence_date+" ("+(s.timing_status||"").replaceAll("_"," ")+"). Original publication and capture dates remain separate.","source"));
 d.append(el("p",s.identity_caveat||"See the source and registry identity review; endorsement does not imply adoption of an entire party platform.","source"));
 if(s.version_timing_qualification)d.append(el("p",s.version_timing_qualification.replaceAll("_"," "),"source"));
 box.append(d);return box;
}
function comparisonCard(pair,shared,used){
 const card=el("article",undefined,"card");
 card.append(el("h3",pair.topic.replaceAll("_"," ")+" · "+pair.relationship.replaceAll("_"," ")));
 card.append(el("span",(pair.representation_kind||"unspecified").replaceAll("_"," "),"badge"));
 if(shared)card.append(el("span","Reused national evidence — not a new observation","badge"));
 if(isQualified(pair))card.append(el("span","Timing-qualified comparison","badge qualified"));
 card.append(el("p",pair.analysis));
 const grid=el("div",undefined,"pair");
 for(const side of ["candidate","opponent"]){const id=pair[side+"_excerpt_id"];used.add(id);const s=statements.get(id);if(s)grid.append(evidenceCard(s,pair[side+"_name"]))}
 card.append(grid);
 card.append(el("p",shared?`Original comparison: ${pair.source_comparison_id}. Original reviewed record: ${pair.source_review_race_id}. Same-cycle national platforms, not state-specific campaigning.`:pair.comparison_scope||"See registry scope","source"));
 return card;
}
function renderDetail(race){
 const target=document.getElementById("detail");target.replaceChildren();
 target.append(el("h2",`${race.election_date} · ${race.state_code} · ${race.office} · ${race.jurisdiction}`));
 target.append(el("p","Tracked endorsed group: "+race.endorsed_candidates));
 target.append(el("p","Other candidates in this comparison set: "+(race.other_candidates||"No comparator listed")));
 if(race.non_person_ballot_options)target.append(el("p","Other ballot choices, not individual platform gaps: "+race.non_person_ballot_options,"muted"));
 if(race.unreviewed_candidates)target.append(el("p","No directly race-linked source review yet: "+race.unreviewed_candidates,"muted"));
 target.append(el("p","Registry record: "+race.race_id,"source"));
 if(race.identity_review_alert)target.append(el("p","Identity review required: "+race.identity_review_notes,"empty"));
 target.append(el("p",`Directly reviewed for this record: ${race.policy_comparison_count} policy-position pairs; ${race.campaign_frame_comparison_count} campaign-framing pairs; ${race.agenda_comparison_count} agenda pairs; ${race.unspecified_comparison_count} not yet categorized. Shared national evidence is separate.`,"source"));
 const mode=document.getElementById("mode").value;
 const pairs=mode==="national"?[]:(byRace.get(race.race_id)||[]).filter(permitted),national=mode==="paired"?[]:(nationalByRace.get(race.race_id)||[]).filter(permitted),used=new Set();
 if(!pairs.length&&!national.length)target.append(el("p","No defensible paired comparison under the current filter. Standalone words, where available, remain below.","empty"));
 for(const pair of pairs)target.append(comparisonCard(pair,false,used));
 if(national.length){
  target.append(el("h2","Applicable national-platform comparisons"));
  target.append(el("p","These candidates were in this recorded primary field, and their reviewed national platforms were available within its campaign window. These are reused source pairs—not newly recovered local statements. Candidate withdrawal or active-campaign status is not inferred.","muted"));
  for(const pair of national)target.append(comparisonCard(pair,true,used));
 }
 const standalone=mode==="national"?[]:(wordsByRace.get(race.race_id)||[]).filter(x=>!used.has(x.excerpt_id)&&permitted(x));
 if(standalone.length){target.append(el("h2","Additional documented positions and campaign framing"));
 for(const s of standalone){const card=el("article",undefined,"card");card.append(evidenceCard(s));target.append(card)}}
}
function render(){
 const search=document.getElementById("search").value.toLowerCase(),year=document.getElementById("year").value,mode=document.getElementById("mode").value;
 const filtered=data.cases.filter(r=>{
  if(year&&!r.election_date.startsWith(year))return false;
  if(mode==="available"&&!(byRace.get(r.race_id)||[]).some(permitted)&&!(nationalByRace.get(r.race_id)||[]).some(permitted))return false;
  if(mode==="paired"&&!(byRace.get(r.race_id)||[]).some(permitted))return false;
  if(mode==="national"&&!(nationalByRace.get(r.race_id)||[]).some(permitted))return false;
  if(mode==="words"&&!(wordsByRace.get(r.race_id)||[]).some(permitted))return false;
  const text=[r.endorsed_candidates,r.other_candidates,r.office,r.jurisdiction,r.state_code,
   ...(byRace.get(r.race_id)||[]).map(x=>x.topic+" "+x.analysis),
   ...(nationalByRace.get(r.race_id)||[]).map(x=>x.topic+" "+x.analysis),
   ...(wordsByRace.get(r.race_id)||[]).map(x=>x.topic+" "+(x.claim_summary||""))].join(" ").toLowerCase();
  return !search||text.includes(search);
 }).sort((a,b)=>a.election_date.localeCompare(b.election_date)||a.race_id.localeCompare(b.race_id));
 const nav=document.getElementById("cases");nav.replaceChildren();
 if(!filtered.some(r=>r.race_id===active))active=filtered[0]?.race_id||null;
 for(const r of filtered){const button=el("button",undefined,"case-button"+(r.race_id===active?" active":""));button.append(el("strong",r.endorsed_candidates));button.append(el("small",`${r.election_date} · ${r.state_code} ${r.jurisdiction}`));button.append(el("small",`${(byRace.get(r.race_id)||[]).filter(permitted).length} reviewed pairs · ${(wordsByRace.get(r.race_id)||[]).filter(permitted).length} statements`));const shared=(nationalByRace.get(r.race_id)||[]).filter(permitted).length;if(shared)button.append(el("small",`${shared} shared national comparisons (reused)`));button.onclick=()=>{active=r.race_id;render()};nav.append(button)}
 const selected=filtered.find(r=>r.race_id===active);if(selected)renderDetail(selected);else document.getElementById("detail").replaceChildren(el("p","No matching cases.","empty"));
}
for(const year of [...new Set(data.cases.map(x=>x.election_date.slice(0,4)))].sort()){const o=el("option",year);o.value=year;document.getElementById("year").append(o)}
for(const id of ["search","year","mode","timing","representation"])document.getElementById(id).addEventListener(id==="search"?"input":"change",render);
document.getElementById("stats").textContent=`${data.summary.total_recovered_statements} attributed statements · ${data.summary.unique_candidate_pairs} distinct reviewed candidate pairs · ${data.cases.length} registry records accounted for. Not a complete platform census.`;
document.getElementById("representation-stats").textContent=`${data.summary.policy_position_comparisons} policy-position pairs · ${data.summary.campaign_frame_comparisons} campaign-framing pairs · ${data.summary.agenda_item_comparisons} agenda pairs · ${data.summary.unspecified_kind_comparisons} not yet categorized. A framing-only comparison is not a full platform comparison.`;
document.getElementById("national-stats").textContent=`Shared national-platform evidence is additionally accessible in ${nationalByRace.size} primary records, reusing ${new Set(data.shared_national.map(x=>x.source_comparison_id)).size} underlying comparisons. It adds zero independent observations to the counts above.`;
const findings=document.getElementById("findings");for(const f of data.findings){const box=el("div",undefined,"card");box.append(el("h3",f.title),el("p",f.finding),el("p",f.limit,"muted"));findings.append(box)}
render();
</script></main></body></html>"""
    destination = ROOT / "report" / "platform_comparison.html"
    destination.write_text(html.replace("__DATA__", script_json(payload)), encoding="utf-8")
    return {
        "path": str(destination.relative_to(ROOT)), "candidate_statements": len(statements),
        "comparison_rows": len(comparisons), "shared_national_rows": len(shared),
        "shared_national_primary_records": len({row["race_id"] for row in shared}),
        "new_independent_evidence_from_reuse": 0,
    }


if __name__ == "__main__":
    print(json.dumps(build_policy_browser(), indent=2))
