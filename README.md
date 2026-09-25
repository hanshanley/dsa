<div align="center">
  <h1>DSA and Democratic Primary Discourse</h1>
  <p><strong>A source-first national comparison of campaigns, platforms, and policy language since 2016.</strong></p>
  <p>
    <a href="#source-backed-policy-comparisons">Policy evidence</a> ·
    <a href="#what-the-campaigns-emphasize">Findings</a> ·
    <a href="#semantic-map">Semantic map</a> ·
    <a href="#data-and-coverage">Data</a> ·
    <a href="#methods">Methods</a> ·
    <a href="#reproduce-the-analysis">Reproduce</a>
  </p>
</div>

---

## What this project asks

How do DSA-endorsed candidates describe politics differently from other Democrats in the same
primaries—and where do they speak in similar terms?

This repository builds an auditable national dataset of DSA endorsements, reconstructs the
corresponding Democratic-primary fields, collects exact campaign and organizational text, and
compares the resulting language. Sources include campaign platforms, policy pages,
questionnaires, debates, interviews, speeches, press releases, archived websites, and official
DSA and Democratic Party platforms.

The analysis measures **emphasis and language**, not ideology by assumption. Missing evidence is
recorded as missing; it is never interpreted as a candidate holding no position.

## Source-backed policy comparisons

The central deliverable is what candidates actually said, compared with other Democrats'
statements on the same policies. Research now spans the **full 2016–2026 registry of 420
tracked Democratic-primary records**, with sourced exclusions maintained as research improves.
This includes federal, state, and local campaigns—not just
the initial 2026 congressional subset. The current selected evidence contains **1,186 attributed
statements and 478 reviewed comparisons across 126 directly paired records**. Of these,
**375 pairs in 115 records compare policy positions**; the other **103 pairs compare campaign
framing**. These are not 126 complete campaign-platform collections, and unresolved duplicate
registry contexts remain explicitly flagged.

The current counts are generated in
[`summary.json`](data/analysis/policy_evidence/summary.json) and
[`historical_inventory_summary.json`](data/analysis/policy_evidence/historical_inventory_summary.json).
The full
[`race_policy_comparison_matrix.csv`](data/analysis/policy_evidence/race_policy_comparison_matrix.csv)
keeps unreviewed candidates and races visible instead of silently dropping them.
[`documented_campaign_positions.csv`](data/analysis/policy_evidence/documented_campaign_positions.csv)
retains the actual short quotations, topics, campaign frames, sources, and timing qualifications
for each reviewed candidate/race record.

Open [`report/platform_comparison.html`](report/platform_comparison.html) for the offline,
searchable comparison browser. It shows actual claims and short quotations side by side,
with source links, date qualifications, agreements, disagreements, and missing-candidate
warnings. Filter by election year or search for a candidate, office, or policy.
The content filter separates policy-position pairs, campaign framing, agenda items, and
uncategorized legacy pairs. A framing-only case is not presented as a complete platform
comparison, and missing representation labels are not silently treated as policy positions.
The default view also exposes applicable same-cycle presidential platforms in additional
primary records. Those cards are explicitly labeled reused national evidence, retain the
original comparison IDs, and add no independent observations. The evidence filter can show
only directly reviewed pairs or only shared national evidence. Reuse does not establish
state-specific campaigning or a candidate's active status after withdrawal.
The browser also links the
[`publication-date correction audit`](data/analysis/policy_evidence/source_date_correction_audit.csv)
and [`source-replacement audit`](data/analysis/policy_evidence/first_party_source_replacements.csv).
Unsupported dates are qualified rather than treated as pre-primary evidence, and later
publisher revisions are displayed explicitly.
Verified archive links take precedence over expired live campaign addresses. The
[`historical-replay recovery audit`](data/analysis/policy_evidence/archive_recovery_audit.csv)
and [`complete recovered platform texts`](data/analysis/policy_evidence/recovered_platform_texts.csv)
document the restoration of original campaign pages without substituting later campaign content.
The prose counterpart is
[`platform_comparison_briefs.md`](data/analysis/policy_evidence/platform_comparison_briefs.md).
For the substantive answer to what differed and how candidates presented their campaigns,
start with [`policy_comparison_findings.md`](report/policy_comparison_findings.md).

For a complete common-question comparison, open
[`report/mayor_same_question_comparison.html`](report/mayor_same_question_comparison.html).
It preserves **18 questions × 9 Democratic candidates** from THE CITY and Gothamist's
published 2025 mayoral survey at a pre-primary source commit. Every option, original
explanation and missing code is retained. Publisher-coded choices are distinguished from
literal candidate quotations; conflicting option fit and multi-approach answers are flagged.
These 162 response records and 144 matched-question rows do **not** inflate independently
reviewed statement or comparison counts. Source attribution and the publisher's license
are retained with the complete data download.

[`report/complete_questionnaire_comparison.html`](report/complete_questionnaire_comparison.html)
adds complete, candidate-authored answers rather than selected quote anchors. The initial
Hawaii 2018 collection contains **12 questions across six candidates**, with all 72 answers
and 60 focal-versus-other-Democrat question pairs downloadable in full. Original prompts,
source hashes, paragraph boundaries, and source ambiguities are retained. Missing respondents
remain visible. These are matched questions, not 60 newly classified policy comparisons.
Only answer paragraphs enter the full-text corpus; quote-only records remain separate.
Questionnaire word counts are not estimates of whole-campaign issue salience.
The same interface also includes all four Illinois District 7 Democrats' complete 2020
three-question responses. Those sources explicitly identify the historical primary, but their
original publication/version dates remain unresolved, so their full answers are not promoted
to timing-supported model inputs. Complete-answer exports and reviewed policy labels remain
separate deliverables.
It also includes both 2024 Travis County district-attorney candidates' three responses, with
the DSA-endorsed candidate and other Democrat explicitly labeled. These dated answers are
included in the answer-only corpus, without treating a three-question, word-limited survey
as an exhaustive campaign platform.
Minnesota Senate District 65's 2022 priority responses are retained in full, with the
publisher's missing respondent identified separately from her recovered campaign platform.
The complete-answer view also covers the2019 Braddock District housing/transportation
questionnaire, both2020 Larimer County District3 candidates, and the timing-qualified2020
Louisville District10 responses. Candidate biographies remain downloadable but are excluded
from policy-model inputs where identified as nonpolicy questions.
Complete common-question fields now also cover Pittsburgh City Council District 7 and
Allegheny County Council District 11 in 2023, Wisconsin Assembly District 76 in 2026, and
the 2016 Somerville state-house contest. Interleaved surveys retain each named speaker's
answers separately. Nonpolicy questions and explicitly flagged attribution concerns remain
downloadable but do not enter policy-model inputs.

The 2017 Bay Ridge recovery also retains
[40 complete published interview response blocks](data/analysis/policy_evidence/complete_interview_answers/policy_new_york_2017/complete_responses.csv)
from four of the five Democratic candidates, with exact source bytes and locators. These are
the publisher's edited quotations, not unedited transcripts. Reporter narration, headings and
unrelated newsletter items are excluded from the candidate-only model input.
This adds **30 attributed statements and 15 reviewed comparisons**, not a complete field or
four complete platforms. Vincent Chirico remains without reviewed candidate words.

The Wisconsin governor comparison now includes all six tracked Democrats' **36 published
response blocks** on housing, data centers, school funding, vouchers, first priorities and
bipartisan governing. Its **30 edited-topic pairs** are labeled separately from identical-question
questionnaire pairs: the broadcast edits do not establish identical original interview questions.
The original transcripts and named-speaker boundaries remain available in the complete-response
download. Early interviews do not establish continued campaign activity after withdrawal.

The presidential follow-up retains
[11 complete archived campaign sources](data/analysis/policy_evidence/complete_campaign_platforms/policy_presidential_2020_followup/complete_sources.csv)
and [separately scoped campaign text](data/analysis/policy_evidence/complete_campaign_platforms/policy_presidential_2020_followup/scoped_blocks.csv).
Yang's and Williamson's healthcare pages illustrate why a Medicare-for-All title does not by
itself establish an identical insurance design. Their actual qualifications are compared with
Sanders' plan; Williamson's conflicting basic-income age language is preserved explicitly.
Complete source downloads include navigation and historical quotations for audit, but only
separately eligible passages enter models. Existing source inputs are reused, not duplicated.

The Arizona 2018 recovery adds
[six complete original congressional campaign sources](data/analysis/policy_evidence/complete_campaign_platforms/policy_arizona_2018_followup/complete_sources.csv)
for Westbrook and Tipirneni, including a directly documented disagreement about retaining private
health insurers and shared support for existing ACA coverage. A later state-house platform
reached through an archive redirect was excluded; the
[source-version audit](data/manual/policy_arizona_2018_source_dispositions.json) preserves the
failed routes and qualifications. Westbrook's article uses inconsistent Medicaid/Medicare
terminology, which is retained rather than silently corrected.

The Maryland District 39 follow-up adds **25 complete answers and 20 timing-qualified
comparisons** for five candidates. The publisher identifies the responses as unedited Vote411
answers, but their exact pre-primary version is unverified. They remain available in the
comparison browser and complete-response download without entering the dated model corpus.
Amar Mukunda is absent from the guide; no nonresponse or withdrawal is inferred.

[`national_platform_applicability.csv`](data/analysis/policy_evidence/national_platform_applicability.csv)
links already-reviewed presidential platforms to other same-cycle primary fields where the
candidates appear. These links add **no new independent evidence** and make no claim about
state-specific campaigning or continued campaign activity after withdrawal.

Agreements, differences in policy scope, and differences in emphasis or strategy are kept
distinct. Source counts are not complete platforms, and selected evidence is not a measured
ranking of what a whole campaign emphasized. Shared national presidential sources are
identified as reused evidence rather than multiplied across states to inflate independent
comparisons.

California's shared ballots are identified separately: the focal DSA-endorsed candidate need
not be a Democrat, but comparison candidates must have a verified Democratic party preference.
Louisiana's November election is still future relative to the research cutoff. Jewett's
standalone positions are retained; the qualified field has no other named Democrat, so no
Democratic opponent is invented.

Exact short quotations, locators, dates and source hashes are in
[`reviewed_candidate_comparisons.csv`](data/analysis/policy_evidence/reviewed_candidate_comparisons.csv)
and [`reviewed_candidate_statements.csv`](data/analysis/policy_evidence/reviewed_candidate_statements.csv).
The complete candidate-by-case accounting is in
[`candidate_coverage.csv`](data/analysis/policy_evidence/candidate_coverage.csv).
Answers with timing uncertainty remain available in the corresponding
[`timing_unverified_candidate_comparisons.csv`](data/analysis/policy_evidence/timing_unverified_candidate_comparisons.csv)
and [`statement export`](data/analysis/policy_evidence/timing_unverified_candidate_statements.csv).
Archive dates are not substituted for unknown publication dates.

These are assistant source reviews, not independent human gold labels or a complete national
census. Full original sources are retained. A different emphasis or an unmentioned policy does
not establish disagreement, and party platforms are not attributed to individual candidates.

The source library also retains complete published candidate-questionnaire bodies from the
public JOLDC archive, with original publisher records and publication/revision timestamps.
Those are **unreviewed discovery inputs**, not automatically accepted candidate positions.
See [`questionnaire_library/`](data/analysis/policy_evidence/questionnaire_library/).
The recovered Stonewall 2020 and 2024 compilations also have a
[`complete section download`](data/analysis/policy_evidence/stonewall_library/complete_candidate_sections.csv).
It retains full text and provenance, including publisher questions, repeated responses, and
printed name/office inconsistencies. It is an **unscoped discovery library**, not additional
reviewed claims or model-ready candidate speech. Only separately source-reviewed sections
enter the comparison exports.

## Coverage update — September 22, 2026

**This is not yet a complete census.** Discovery now includes sources from **January 1, 2015**
for the 2016 election cycle. Publication dates do not change a document's election-cycle
assignment. A verified endorsement no longer counts as proof that every endorsement in that
chapter-year has been found.

The new **nationwide congressional inventory is independent of DSA endorsement** and retains
all parties, U.S. House and Senate seats, nonvoting delegates, and separately identified special
elections. It is not silently substituted for the narrower DSA discourse comparison below.

| Nationwide congressional artifact | Recovered coverage |
| --- | ---: |
| Official FEC congressional result source rows, 2016/2018/2020/2022 workbooks | **13,581** |
| Regular seat-cycle checklist, 2016–2026 | **2,843** |
| Official 2024 general-ballot source rows, kept separate from primary rosters | **1,259** |
| Special-election calendar entries from 2015 onward | **73** |

Source rows are **not** counts of unique candidates or races: fusion ballot lines, aggregate
write-ins, and overlapping special-election appendices remain explicit. The regular-seat
checklist retains explicit missing result entries, principally for 2024 and 2026. General-ballot
nominees cannot stand in for primary losers. The retrieved special-election calendar was updated
March 12, 2026, so it cannot establish complete September 2026 coverage.

Full source rows, raw vote flags, workbook/sheet/row provenance, acquisition failures, and
per-seat gaps are in [`data/analysis/congressional/`](data/analysis/congressional/).
The complete longitudinal download is
[`all_primary_records.csv`](data/analysis/congressional/all_primary_records.csv);
it includes the actual source observations, not only coverage metadata.
[`state_cycle_coverage.csv`](data/analysis/congressional/state_cycle_coverage.csv) lists every
expected, recovered, and missing congressional district separately for each state and cycle.
[`district_primary_accounting.csv`](data/analysis/congressional/district_primary_accounting.csv)
separately checks party-contest and official no-primary evidence; one party's recovered returns
do not certify a complete district.
Official state primary returns are being recovered separately from the older FEC workbooks;
[`summary.json`](data/analysis/congressional/summary.json) contains the current counts.
The broader endorsement audit is in [`census_summary.json`](data/analysis/census_summary.json),
[`census_by_year.csv`](data/analysis/census_by_year.csv), and
[`census_gaps.csv`](data/analysis/census_gaps.csv). The refreshed national archive contains
369 campaign records; the chapter discovery grid contains 2,988 chapter-years, none yet certified
as exhaustive under the strengthened standard. These are open research obligations, not evidence
that no endorsements or positions exist.
The refreshed national endorsement archive and current/historical chapter directory are retained
as versionable snapshots under `data/processed/`; later refreshes do not erase historical entries.

The figures below describe the screened, recoverable campaign corpus, **not all congressional
primaries** and not a completed post-primary national census.

The 2026 calendar also cannot be treated as entirely past: the FEC's published calendar
records Louisiana's House election on **November 3, 2026**, with a possible **December 12, 2026**
runoff. Those dates are after this repository's September 22 cutoff. Louisiana's Senate primary
and runoff are distinct events. Calendar information is retained at
`data/raw/fec/2026pdates.pdf`; no future results are inferred.

## Semantic map

**The candidate analysis has been rerun after the source-integrity repairs.** The pinned local
topic model processed **2,866 passages**, assigned topics to **2,557**, and left **309 unclassified**.
The separate GTE embedding/KDE run retained **2,825 passages from 104 candidate-cycle units** and selected
**five dimensions**. Candidate-cycle versus group-cycle deduplication explains the different
input counts. Identified archive toolbars, HTML navigation, forms, footers and page controls
were removed before segmentation; unscoped speech, statement and press-release sources are withheld.
Substantive shared wording is no longer discarded merely because it repeats across documents.
The cleanup also checks false positives: whole-page theme classes containing the word "menu"
do not qualify as navigation. Verified policy text from those pages remains in the accepted run.

The previous unscreened map is superseded, not reinterpreted as valid evidence.
The current [map and region report](report/provisional_kde_analysis.md) remain exploratory:
names, geography, office, year, and source format can affect the geometry. A cluster is not a
policy stance or an estimate of nationwide agreement. Classification does not verify attribution.
The [execution audit](report/analysis_execution.md) records completed stages, exact input
fingerprints, coverage by year, and the prepared-only status of Jev.

## What the campaigns emphasize

<p align="center">
  <img src="outputs/figures/text_analysis/policy_language_difference.svg" width="1100" alt="Comparison of policy-language prevalence in DSA-endorsed and other Democratic campaign documents">
</p>

These exploratory document-level mention rates use the screened source subset. They are not
a national estimate or evidence of disagreement: a topic mention does not establish a stance,
and automatic screening is not semantic verification of every passage.

## Where the agendas overlap

<p align="center">
  <img src="outputs/figures/text_analysis/policy_language_overlap.svg" width="1050" alt="Issues discussed by both DSA-endorsed candidates and other Democrats">
</p>

Shared attention does not establish agreement: candidates may diagnose the same problem while
proposing different mechanisms. Conversely, sharing a concrete policy should be recorded as
agreement even when a candidate's endorsement or party label differs.

The automated review aid below counts primaries where both sides use the same policy phrase
after a local-negation screen. Matching phrases can conceal different policy designs.

<p align="center">
  <img src="outputs/figures/text_analysis/shared_affirmative_policy_mechanisms.svg" width="980" alt="Shared named-policy language within Democratic primaries, not verified agreement">
</p>

Negated or explicitly oppositional mentions are excluded; exact paired passages remain available
for review. The chart is a phrase-based review aid, not a substitute for comparing both speakers'
positions in context.

## Official platforms

Candidate rhetoric is analyzed separately from organizational platforms. The official corpus
contains DSA national and state/local programs alongside DNC and state Democratic Party
platforms. The lexical corpus contains **6 DSA documents** and **38 Democratic documents**.
The semantic analysis additionally requires at least 10 quality-screened passages per platform,
leaving **6 DSA documents (327 passages)** and **35 Democratic documents (4,983 passages)**.
Document prevalence gives each platform one observation per feature. The semantic fingerprint
fits UMAP and KDE to equal-size, round-robin document-stratified samples and gives every eligible
platform equal aggregate KDE weight.

The KDE-eligible set contains 3 DSA national documents, 3 DSA state/local documents, 3 DNC
national platforms, and 32 state Democratic Party platforms. That level mismatch is material:
the result is a comparison of the recoverable corpus, not a balanced census of national and local
organizations. The coverage ledger retains 154 explicit platform gaps; these remain missing data
rather than evidence of organizational silence.

<p align="center">
  <img src="figures/official_platform_gte_kde.png" width="1100" alt="Document-stratified, equal-platform-weighted semantic density map of official DSA and Democratic platforms">
</p>

The map draws an equal-size sample of 327 passages per group, avoiding the false visual impression
that the much larger collected Democratic corpus is itself a substantive result. The full run
retains 15 exploratory regions; the six strongest are displayed. Across 24 prespecified HDBSCAN
configurations, the retained-region count ranges from 6 to 17, so these regions are evidence
summaries rather than a stable topic taxonomy. The document-prevalence result separately
shows the strongest DSA-side differences for social housing, working-class, tenant, Green New
Deal, and Medicare for All language. These are relative emphasis patterns in the recoverable
corpus, not evidence that every organization or candidate holds the same position.

The complete accounting is in
[`analysis_flow.csv`](data/analysis/official_platform_gte_kde/analysis_flow.csv),
[`platform_coverage.csv`](data/analysis/official_platform_gte_kde/platform_coverage.csv),
[`density_regions.csv`](data/analysis/official_platform_gte_kde/density_regions.csv), and
[`clustering_sensitivity.csv`](data/analysis/official_platform_gte_kde/clustering_sensitivity.csv).

<p align="center">
  <img src="outputs/figures/text_analysis/official_platform_document_prevalence.svg" width="1050" alt="Document-level policy language prevalence in official DSA and Democratic platforms">
</p>

| DSA / DSA-endorsed emphasis | Democratic platform / other-Democrat emphasis |
| --- | --- |
| Housing as a right; tenants; rent control; social and public housing | Housing supply, development, and administrative delivery |
| Single payer and Medicare for All | Public-option and incremental coverage mechanisms |
| Living wages, unions, workers, and collective power | Training, pathways, small business, and labor-market opportunity |
| Movement-building and working-class political power | Governing competence, coalition breadth, and institutional implementation |
| Collective or public ownership and decommodification | Regulated, competitive capitalism |

<p align="center">
  <img src="outputs/figures/text_analysis/official_policy_contrasts.svg" width="1050" alt="Reviewed contrasts between official DSA and Democratic Party policy language">
</p>

## Data and coverage

| Corpus component | Current coverage |
| --- | ---: |
| Strict in-scope Democratic or Minnesota DFL primaries | **420** |
| Individual candidate/race records with source-reviewed words | **470 / 1,876** |
| Endorsed ballot-campaign records, kept separate from people | **7** |
| Other non-person ballot choices, not individual platform gaps | **30** |
| Directly paired records, including separately labeled shared ballots | **126** |
| Records with explicit policy-position comparisons | **115** |
| Races with screened substantive model text on both sides | **88** |
| Source-document associations contributing to the model corpus | **522** |
| Deduplicated candidate analysis documents | **209** |
| Deduplicated candidate analysis passages | **2,866** |
| Complete published responses / matched-question pairs / edited-topic pairs | **287 / 178 / 30** |
| Separately exported complete published interview response blocks | **40** |
| Organizational documents successfully extracted | **93 / 93** |
| Full organizational platforms in lexical analysis | **44** (**6 DSA; 38 Democratic**) |

The retained materials cover portions of 2016–2026; see the year-level audit for missing years.
They are **not complete nationwide text coverage**: **1,406 individual candidate/race records**
and **seven endorsed ballot campaigns** still lack source-reviewed evidence. Reviewed records
can themselves have only partial platforms. The legacy 1,913-record denominator includes
30 non-person ballot choices, such as Scattered and No Preference; these are preserved election
observations, not 30 people whose platforms need finding. Exact same-cycle presidential research
grouping yields **833 open acquisition work units**, not independent observations or proof of
source applicability in each state. Suspected duplicate registry contexts remain explicitly
flagged rather than fuzzily merged.
The separate full-text audit retains **898 retryable candidate-source gaps**. Its extraction
and eligibility counts are not counts of semantically reviewed positions. The older manual
ledger also retains 26 unverified other-Democrat records; it is not the current policy-coverage
denominator. See [`docs/completeness.md`](docs/completeness.md) for the completion criteria and
[`data/processed/full_text_audit_summary.json`](data/processed/full_text_audit_summary.json) for
the machine-readable audit.

## Evidence standard

Substantive findings must trace to exact text from official organizations, campaigns, debates,
interviews, or attributable candidate responses. Journalism and search results may locate
sources but do not substitute for primary evidence.

Every analyzed passage retains its candidate, race, document, URL, source type, date, and
locator. `source_unavailable`, `searched_not_found`, and unresolved records remain explicit
unknowns.
The exclusion ledger is
[`candidate_document_eligibility.csv`](data/analysis/candidate_document_eligibility.csv).
Sources outside the primary campaign window, undated historical sources without an in-window
capture, unrelated campaign-homepage seeds, rolling press indexes without article-specific
scope, and out-of-scope races are excluded from candidate
comparisons while their raw evidence is preserved.
The former count of 38,207 passages was not a count of verified candidate positions. The lower
screened count reflects evidence exclusions, not candidates abandoning policies.
An offline repair decoded 20 retained gzip captures covering 49 candidate-document associations,
without refetching or changing raw hashes. Empty or unscoped results remain excluded; the repair
ledger is in `data/analysis/policy_evidence/legacy_gzip_repairs.csv`.
Three year-only source dates were also corrected: a year does not establish January 1 or prove
that a questionnaire was available before the primary. Exact source bytes remain retained.

Reproduce the source-reviewed comparison and ingest only registered speaker-answer paragraphs:

```bash
uv run python -m dsa_analysis.policy_comparison --ingest
uv run dsa-analysis analyze
uv run dsa-analysis rebuild-analysis-segments
uv run dsa-analysis analyze-text
uv run dsa-analysis provisional-kde
uv run dsa-analysis audit-full-text
uv run dsa-analysis analyze
```

The first `analyze` replays registered complete questionnaire and interview answers before modeling; the last publishes the
new results. The full-text audit still exits nonzero for insufficient coverage, not a model-run
failure. `--download` refreshes the three registered
Colorado interview captures; supplemental reviews replay their separately retained full sources.
Quote matching, reviewed attribution, dates, hashes, and recovered Democratic ballot identities
must validate. Supplemental reviewed statements are in the comparison export; the full captured
pages are not automatically promoted to speaker-verified classifier input.
The existing 1,251-row automated contrast snapshot has not been revalidated against the cleaned
sources and is not the new source-reviewed comparison table.

## Methods

### Document-level language

Policy phrases are normalized before counting. Each feature is measured as the share of
candidate-election documents containing that phrase, preventing a campaign that repeats one
term many times from dominating the comparison.

### Semantic density

Eligible passages are embedded with the pinned multilingual GTE model and L2-normalized.
Dimensionality is selected by a trustworthiness sweep; the current candidate KDE uses
**five dimensions** and Scott's bandwidth rule. Fitting uses deterministic candidate round-robin
sampling up to a per-group cap. That cap is not reached in this run, so it does **not** make
candidates equally weighted. Density is estimated in the selected representation; the separate
two-dimensional UMAP projection is only a display.

Official platforms use a separate five-dimensional sweep result. Both the UMAP manifold and KDE
use **327 passages per group** after the separate semantic quality and platform-coverage gates.
UMAP fitting uses a deterministic round-robin document-stratified sample; inverse
within-document passage-frequency weights give each of the **6 DSA and 35 Democratic**
KDE-eligible platforms equal aggregate density weight. This prevents the larger Democratic
passage inventory from mechanically determining the geometry or density estimates, but it cannot
replace missing DSA state/local platforms or erase the 6-versus-35 semantic-coverage limitation.

### Agreement and disagreement

- **Overlap** identifies issues discussed by both groups.
- **Shared named-policy language** identifies matching phrases without local negation.
  It is an automated review aid, not proof of agreement on a concrete mechanism.
- **Explicit conflicts** are direct, source-supported candidate contrasts; analyst-coded
  divergences are kept separate.

Full details are in [`docs/methodology.md`](docs/methodology.md), with field definitions in
[`docs/data_dictionary.md`](docs/data_dictionary.md).

## Key outputs

- [`data/analysis/candidate_text_corpus.csv`](data/analysis/candidate_text_corpus.csv) — exact
  deduplicated candidate passages with full provenance
- [`data/analysis/provisional_gte_kde/density_regions.csv`](data/analysis/provisional_gte_kde/density_regions.csv)
  — all substantive semantic regions (up to six per category), terms, counts, representative
  evidence, and an indicator for the two per category displayed on the map
- [`outputs/tables/text_analysis/candidate_feature_prevalence.csv`](outputs/tables/text_analysis/candidate_feature_prevalence.csv)
  — document-level phrase prevalence by candidate group
- [`outputs/tables/text_analysis/official_platform_document_prevalence.csv`](outputs/tables/text_analysis/official_platform_document_prevalence.csv)
  — document-balanced policy-feature prevalence across official DSA and Democratic platforms
- [`data/analysis/official_platform_gte_kde/density_regions.csv`](data/analysis/official_platform_gte_kde/density_regions.csv)
  — HDBSCAN regions underlying the balanced official-platform KDE map
- [`report/official_platform_kde_analysis.md`](report/official_platform_kde_analysis.md)
  — official-platform KDE dimensions, balancing, region table, and limitations
- [`outputs/tables/text_analysis/shared_affirmative_policy_mechanisms.csv`](outputs/tables/text_analysis/shared_affirmative_policy_mechanisms.csv)
  — exact paired passages for reviewing shared phrases, not independently verified stance labels
- [`report/text_analysis.md`](report/text_analysis.md) — lexical, overlap, and agreement analysis
- [`report/provisional_kde_analysis.md`](report/provisional_kde_analysis.md) — region-by-region
  semantic interpretation
- [`report/draft.md`](report/draft.md) — generated canonical research report
- [`report/analysis_execution.md`](report/analysis_execution.md) and
  [`execution_audit.json`](data/analysis/execution_audit.json) — actual stage completion,
  input freshness, selected policy relationships, and explicit remaining coverage gaps

## Reproduce the analysis

The project requires Python 3.12 and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/hanshanley/dsa.git
cd dsa
uv sync
uv run dsa-analysis validate
uv run dsa-analysis analyze
uv run dsa-analysis rebuild-analysis-segments
uv run dsa-analysis analyze-text
uv run dsa-analysis provisional-kde
uv run dsa-analysis analyze
```

`analyze-text` also executes the local topic classifier; it is not a preparation-only command.
The final `analyze` publishes an execution receipt and checks input hashes. If metadata,
source segments, or the registry changed, regenerate affected models before using their results.

To refresh official source inventories and expose every known coverage gap:

```bash
uv run dsa-analysis collect-endorsements
uv run dsa-analysis collect-chapters
uv run dsa-analysis build-queue
uv run dsa-analysis build-coverage-ledger
uv run dsa-analysis build-opponent-queue
uv run dsa-analysis build-race-registry
uv run --with 'xlrd>=2,<3' dsa-analysis collect-state-primaries
uv run dsa-analysis collect-congressional --download
uv run dsa-analysis audit-census
uv run dsa-analysis validate --strict
```

Strict validation currently **fails**, intentionally, because national coverage is incomplete.
`collect-state-primaries` rebuilds the complete consolidated primary table from retained official
sources and provider outputs. Add `--download` to refresh the registered sources. Alabama's
legacy BIFF workbooks require the optional `xlrd` reader. If the package-index download is
unavailable, the official pinned source can be used without replacing any project dependency:
`uv run --with 'xlrd @ git+https://github.com/python-excel/xlrd.git@3a19d22014d7b3f3041b7188d21a653c18c709bf' dsa-analysis collect-state-primaries`.
The separate Arkansas/Kentucky/South Dakota nomination evidence can be rebuilt with
`uv run python -m dsa_analysis.nomination_followup` before `collect-congressional`.
It uses retained official qualifying rosters and nomination rules, not missing numeric returns
as proof that a candidate was unopposed.
PDF calendar extraction uses the existing `pypdf` reader or macOS PDFKit/Swift fallback.
On systems without either, run the congressional command with
`uv run --with 'pypdf>=5,<7' dsa-analysis collect-congressional --download`.
Historical archive discovery uses `source_start` and `research_cutoff` from `config/sources.json`;
`crawl-wayback` retains prior discoveries and exposes truncated searches instead of treating
them as complete. Bounded retries, for example
`uv run dsa-analysis crawl-wayback --workers 4 --limit 4 --timeout 10`, prioritize
least-recently-attempted chapters and preserve discoveries and statuses outside the batch.

### Jev comparison (opt-in)

The current **220-passage pilot** is in `data/analysis/jev_policy_preserving_pilot/`, using the same
CAP taxonomy and exact source passages as the structurally screened local baseline. Older pilot
directories remain retained but are **stale for the current corpus**; the execution receipt
checks every pilot against both corpus and baseline hashes.
The current pilot contains complete sampled text and provenance, request bodies, and a blinded
annotation CSV. **No live Jev predictions or accuracy improvement have been measured**:
`TYPESAFE_API_KEY` was unavailable and no independent reference labels exist. The canonical
classifier remains local.

```bash
uv run dsa-analysis benchmark-jev --limit 220 --output-dir data/analysis/jev_policy_preserving_pilot
# Set TYPESAFE_API_KEY securely in the environment before opting into hosted inference.
uv run dsa-analysis benchmark-jev --limit 220 --output-dir data/analysis/jev_policy_preserving_pilot --execute --allow-hosted
# After independent review of review.csv:
uv run dsa-analysis benchmark-jev --limit 220 --output-dir data/analysis/jev_policy_preserving_pilot --gold data/analysis/jev_policy_preserving_pilot/review.csv
```

Hosted execution sends only passage text and the topic rubric to TypeSafe, may incur charges,
and requires explicit consent. The versioned `jev-1.13.0` model, full probabilities, usage,
latency, hashes, and cached responses are retained. Agreement with the existing classifier is
not accuracy; gold-label metrics remain null until reviewed labels exist. Use a separate
`--output-dir` for a different sample to protect annotations.

Run the full test suite with:

```bash
uv run python -m unittest discover -s tests
```

## Repository guide

- `src/dsa_analysis/` — collection, extraction, audit, and analysis code
- `data/manual/` — reviewed source registrations and adjudications
- `data/processed/` — generated corpora, coverage queues, and audit outputs
- `data/analysis/` — analysis-ready snapshots and model outputs
- `outputs/` — reproducible tables and SVG figures
- `figures/` — semantic-density visualization
- `docs/` — methodology, codebook, completeness criteria, and data dictionary
- `tests/` — regression and validation tests
