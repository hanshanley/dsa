# Data dictionary

## Current execution and coverage audits

For sanitized public snapshots, `source_sha256`/`raw_sha256` describe the published representation.
`publication_redactions.json` provides `original_sha256`, `public_sha256`, original/public byte
counts and redaction categories. It contains no credential values. An original filename may remain
stable while its public content is redacted; use the recorded public hash, not a digest inferred
from the filename.

`data/analysis/execution_audit.json` separates model execution from source completeness.
Stage `completed_at` values are recorded run times; `audited_at` is only observation time.
`current` means the recorded input/output fingerprints and screening version match, not that
every passage has independent semantic certification. Missing gold accuracy stays null.

`historical_candidate_inventory.csv` now includes `entity_kind` and `policy_evidence_required`.
`individual_candidate`, `endorsed_ballot_campaign`, and `non_person_ballot_option` are separate.
The legacy `candidate_race_records` total includes all three; the newer individual-candidate
denominator excludes ballot labels. `non_individual_ballot_records.csv` preserves all such
records, while `policy_research_worklist.csv` groups acquisition work without claiming new evidence.

Candidate statements retain `publication_date`, `source_updated_date`, `capture_date`, and
`temporal_evidence_date` separately. An in-window archived campaign edition can have an older
original publication date. The edition used for eligibility must not be available only after
the target primary.

Complete-response exports include `pairing_basis`: `same_published_question` versus
`shared_published_topic_round`. The latter is an edited interview grouping, not proof of
identical original questions. `matched_question_pairs` excludes edited-topic pairs;
`matched_published_response_pairs` includes both and `shared_topic_round_pairs` counts the latter.

`complete_campaign_platforms/*/complete_sources.csv` preserves complete extracted source text,
including navigation and embedded historical quotations. `scoped_blocks.csv` identifies the
separately reviewed candidate-text boundaries. Neither export creates independent stance labels.
`candidate_analysis_paragraph_exclusions.csv` retains excluded control text, original locators,
source hashes and exclusion reasons without changing the original extraction.

## `documents.csv`

One row per source document or media item. `source_tier` is `1`, `2`, `3`, or `4` under the
methodology hierarchy. `verification_status` records whether a reviewer checked the content.

## `endorsements.csv`

One row per endorsing body, candidate, and race. Multiple DSA bodies may endorse the same
candidacy. `endorsement_source_document_id` must reference `documents.csv`.

## `race_candidates.csv`

One row for every candidate on a tracked Democratic-primary ballot. The endorsed candidate and
all other Democrats are retained, including withdrawn candidates who remained on the certified ballot.
`evidence_status` tracks whether first-party policy material has been reviewed for that person.

## `excerpts.csv`

One row per exact quotation. `locator` is a page, heading/paragraph, or timestamp. `reviewed`
must be `true` before the excerpt can support final analysis.

## `contrasts.csv`

One row per endorsed-candidate/other-Democrat/topic comparison. `contrast_type` is `explicit_conflict` or
`coded_divergence`; both sides require excerpt IDs unless the relationship is
`insufficient_evidence`.

## `platform_comparisons.csv`

One row per time-aligned DSA/Democratic Party comparison. Both excerpt IDs must reference reviewed
first-party text before the row may appear in the report.

## `coverage.csv`

One row per chapter and election year searched. It records where researchers looked and why a
chapter-year may remain unresolved.
## Analysis snapshots

### `data/analysis/candidate_text_corpus.csv`

Generated row-level input for the reproducible text and topic graphs. It is exported from
`data/processed/candidate_document_analysis_segments.csv` and joined to
`candidate_document_metadata.csv` for source provenance.

Key fields:

- `corpus_segment_id` and contributing `source_analysis_segment_ids`
- aggregated `document_ids`, `candidate_names`, `race_ids`, `roles`, and election dates
- `group` and `cycle`
- source types, source/archive/final URLs, publication dates, and locators
- exact `text`, token count, text hash, duplicate hash, and provenance-row count

Only nonempty segments with at least 20 tokens and `boilerplate_flag=false` are eligible. Exact
text is deduplicated within endorsed/other-Democrat group and election cycle, so a shared national
platform is not multiplied across state races; all contributing provenance is retained.

### `data/analysis/organizational_context_text_corpus.csv`

Generated exact-text segment snapshot for official DSA-versus-Democratic analysis. Eligibility
requires a full-platform category, at least 20 tokens, and no boilerplate flag. DSA National and
state/local DSA categories form the DSA group; DNC National and state Democratic Party categories
form the Democratic group. At analysis time, at least one contributing context entry must still
have `verification_status=verified` in the current organizational inventory; stale extraction
artifacts from unavailable or invalidated sources are excluded.

### `outputs/tables/text_analysis/official_platform_document_prevalence.csv`

One row per canonical policy feature. Counts and shares record how many analyzed DSA and
Democratic platform documents mention the feature; `difference` is DSA share minus Democratic
share. Each platform contributes at most once per feature.

### `data/analysis/official_platform_gte_kde/`

Document-stratified, equal-platform-weighted semantic-density outputs for official platforms.
This pipeline applies an additional quality and minimum-platform-coverage gate beyond the
44-document lexical corpus:

- `segment_density_scores.csv`: exact passages, provenance, selected-space density values,
  two-dimensional visualization coordinates, zone, HDBSCAN label, and membership probability;
- `analysis_flow.csv`: complete passage accounting from loaded and excluded rows through
  highlighted, noise, retained-region, and displayed-region subsets;
- `platform_coverage.csv`: every contributing platform, national/subnational level, passage
  coverage, eligibility status, and exclusion reason;
- `density_regions.csv`: retained DSA-overrepresented, Democratic-overrepresented, and shared
  HDBSCAN regions with terms and representative exact passages;
- `clustering_sensitivity.csv`: region counts and assigned-passage counts across the prespecified
  HDBSCAN method, minimum-cluster-size, and minimum-samples grid;
- `umap_dimension_sweep.csv`: trustworthiness for 2, 5, 10, 20, and 30 dimensions;
- `hot_cold_terms.csv`: deterministic hot/cold-zone lexical characterization;
- `summary.json`: model identity, corpus hash, balance rules, bandwidths, thresholds, dimensions,
  group/document counts, eligibility gates, passage-flow counts, clustering configuration, and
  sensitivity ranges.

`embeddings.npy` is a local cache and is not versioned.

### `data/analysis/model_topic_classifications.csv`

Local sentence-transformer output for every eligible candidate segment. It preserves exact text
and aggregated candidate/race/document/source provenance and adds:

- configured model name and local device;
- predicted CAP topic code/name;
- cosine similarity;
- runner-up topic and similarity;
- top-two margin;
- keyword-baseline topic/score and agreement flag.

### `data/analysis/candidate_document_eligibility.csv`

One row per candidate document, retaining identity, source URL, capture/publication dates,
`analysis_status`, and all `exclusion_reasons`. `screened_not_semantically_verified` means only
that automatic source/date/scope gates passed; it is not a human verification label.
The original raw and metadata records are retained even when excluded from policy comparisons.
`policy_evidence/legacy_gzip_repairs.csv` records old/new extraction hashes and preserved raw
copies for the compressed-source repair. `legacy_date_precision_repairs.csv` records the removal
of fabricated January 1 publication dates while keeping the originally supplied year.

### `data/analysis/policy_evidence/`

`reviewed_candidate_comparisons.csv` contains paired short quotations, speaker names, election and
publication dates, exact paragraph locators, source URLs/hashes, relationship type, and a
source-supported interpretation. `review_method` explicitly distinguishes assistant source
review from independent human gold. `reviewed_candidate_statements.csv` retains all individually
checked short statements, including evidence not used by a paired comparison.
`source_manifest.csv` records the retained Colorado interview
captures; `corpus_raw_manifest.jsonl` records the same sources used for scoped corpus extraction.
`supplemental_source_manifest.csv` records used and excluded full New York captures.
Unknown publication dates stay blank; `capture_date` and `archive_url` separately establish when
an archived campaign text existed. `source_recovery_gaps.csv` preserves missing comparators and
concrete failed attempts, with unresolved discovery gaps distinguished from exhaustive searches.
`source_recovery_attempts.csv` retains failed-attempt history even after a usable candidate
statement has been recovered; recovering one statement does not establish a complete platform.
`timing_unverified_candidate_statements.csv` and `timing_unverified_candidate_comparisons.csv`
retain authentic election-guide answers whose exact pre-primary publication time/version remains
unknown. They are not silently backdated or included in the timing-verified comparison table.
The comparison includes both sources and an explicit timing caveat, rather than treating a
missing timestamp as a missing position.
`ballot_name`, `identity_resolution`, `identity_evidence_ids`, and `identity_review_notes`
retain explicit reviewed aliases without changing canonical speaker names. Contextual official
corroboration is not mislabeled exact formal-name proof. Original PDFs are the authoritative
source artifacts even when a derived text extraction is also retained.
`summary.json` keeps the limited reviewed coverage and `complete_census=false` explicit.

The expanded comparison layer includes:
- `race_policy_comparison_matrix.csv`: every tracked race, with actual paired findings,
  standalone evidence and unresolved candidates distinguished.
- `documented_campaign_positions.csv`: source-backed candidate claims, short quotation
  anchors, campaign frames and source references; not an inferred complete platform.
- `cross_race_policy_findings.csv`: descriptive counts of reviewed findings by topic,
  not population prevalence or campaign-message frequency.
- `supported_cross_race_findings.csv`: substantive conclusions linked to their exact
  supporting comparison IDs.
- `platform_comparison_briefs.md` and `report/platform_comparison.html`: readable
  election-by-election comparisons; the HTML browser runs offline.
- `national_platform_applicability.csv`: transparent reuse of national campaign
  evidence for other applicable primary fields, without adding independent observations.

`available_by_date` is a publisher-release bound, not an invented first-publication
date for a linked PDF. Its source release, actual link, date marker and retained hash
are validated. `reviewed_quote` extraction stores only the exact source-located
quotation and is excluded from the broader full-text salience classifier.
`candidate_coverage.csv` lists each focal candidate and eligible comparator, the election-system
scope, verified/qualified statement counts, and source references. At least one recovered
statement does not establish complete platform coverage. For shared ballots it excludes
non-Democratic comparators while preserving the focal candidate's actual party preference;
future election cases remain explicit.
`config/policy_comparison_reviews.json` supplies reviewed relationships rather than deriving
ideological disagreement from topic frequency or endorsement labels.

`data/analysis/platform_comparison_eligibility.csv` separately flags historical organizational
comparisons whose source dates are missing or postdate the comparison cycle.

### `data/analysis/model_topic_validation.json`

Run-level counts and diagnostics: classified/unclassified rows, threshold, low-margin rows,
keyword agreement, input hash, source-document count, and corpus lineage. The legacy
quotation-level reviewed-code crosswalk is marked inapplicable to full-document segments.

### `data/analysis/primary_sticking_points.csv`

Retained, deduplicated legacy contrast snapshot. If its original statement-evidence inputs are
unavailable, it is marked `legacy_snapshot_not_revalidated` and excluded from current conflict
charts. It is not the separately source-reviewed `policy_evidence` comparison table.

### Source and election windows

`config/sources.json` distinguishes `source_start` (January 1, 2015), `study_start`
(January 1, 2016), and `research_cutoff`. A source dated 2015 can belong to a 2016 candidacy.
Chapter-year discovery coverage is not an election-results table.

### `data/analysis/congressional/`

- `all_primary_records.csv`: the complete longitudinal primary-source download, combining
  FEC primary/runoff observations with dated state-authority returns. Each row retains exact
  source locators, hashes, raw vote flags, and an observation ID. `cycle_basis` distinguishes
  FEC publication cycles from verified election dates; missing historical dates are not
  manufactured. Overlapping publications remain separate observations.
- `candidate_results.csv`: all candidate-bearing FEC result rows, including aggregate
  write-ins marked by `row_kind`. `workbook_cycle` identifies the publication, not necessarily
  the year of a special election in an appendix. Numeric and raw vote fields are separate;
  missing votes are empty, while an actual zero remains `0`. `raw_cells_json` preserves the
  source columns, including ranked-choice rounds and footnotes.
- `regular_seat_inventory.csv`: all-party seat-cycle checklist, source-row counts,
  primary-system distinctions, and explicit missing results. `seat_basis_cycle` can identify
  a prior-cycle map or an independent Senate class; neither constitutes a current ballot roster.
- `state_primary_results.csv`: all reported candidate/ballot-option returns recovered from
  state election authorities, including losing candidates, declared and aggregate write-ins,
  and actual zero votes. `primary_party` is a ballot category, not evidence of a private
  write-in person's affiliation. Source rows marked `superseded_primary` cannot fill current
  nomination gaps. Ranked-choice first preferences are not final-round winner determinations.
- `state_primary_sources.csv` and `state_primary_providers.csv`: direct source registrations
  and supplemental-provider file/manifest hashes. Every provider retains its own complete
  provenance and unresolved-unit ledger.
- `party_contest_accounting.csv`: official results, explicit nomination/no-primary evidence,
  and unresolved party-contest units. Single-candidate numeric returns are not automatically
  called unopposed nominations. Contrary sources produce `conflicting_evidence`, not an
  arbitrary preferred answer.
- `district_primary_accounting.csv`: every expected regular district/seat, with remaining
  ballot categories and separately identified future contests. Resolving tracked party
  contests does not establish an exhaustive minor-party or special-election census.
  An unidentified territorial ballot is `unspecified-party`, not automatically all-party
  or nonpartisan. Puerto Rico's local-party universe is not replaced with U.S.
  Democratic/Republican primary categories.
- `state_cycle_coverage.csv`: every state's expected, observed, and missing congressional
  districts by cycle. Presence of a return is a weaker condition than full party-roster
  reconciliation; use `district_primary_accounting.csv` for the latter.
- `special_election_inventory.csv`: dated entries from the FEC special-election calendar,
  including its own update date, raw text, and page locator. A special general or runoff date
  is not a primary date.
- `general_ballot_2024.csv`: official general-ballot source rows, never used as a complete
  primary roster.
- `source_manifest.csv`: workbook URLs, SHA-256 hashes, retrieval status, and explicit errors.
- `source_attempts.csv`: additional state-authority access attempts and failures; an attempted
  URL is not treated as a verified roster or evidence that an election did not occur.
- `source_identity_review.csv`: FEC IDs assigned to different name spellings in the same
  publication. These are review leads (possible aliases or source errors), not automatic merges.
- `dsa_registry_reconciliation.csv`: exact normalized-name and chamber comparisons between
  2024/2026 DSA registry entries and recovered primary returns. Flags unmatched candidates,
  date/district differences, and ambiguous districts without changing endorsements or identities.
  Missing exact matches are review leads, not evidence that a candidate did not run.
- `source_quality_notes.csv`: substantive source limitations, including superseded Alabama
  primaries, nonnumeric source cells, corrected Maine ranked-choice totals, and misleading
  annotation/reporting-counter semantics.
- `ranked_choice_rounds.csv`: source-verified rounds and exhausted ballots kept separately
  from first preferences. The importer checks round totals, ballot-option continuity and
  final majority; it does not label the first-round plurality leader the winner.
- `coverage_gaps.csv` and `summary.json`: unresolved coverage obligations and honest
  completeness status. Counts of gap records are not counts of unique missing races.

Raw workbooks, the special-election calendar, and Senate class pages are in `data/raw/fec/`.
FEC source IDs and spellings are preserved even when the source appears internally inconsistent;
they must not be treated as independently validated candidate identities.

### `data/analysis/census_*`

`census_gaps.csv` reconciles known chapter-years, national and local endorsements, candidacies,
and registry/text gaps. `census_by_year.csv` separates the 2015 discovery lookback from study
cycles. `census_summary.json` records input hashes and completeness; it is not proof that every
historical chapter or race has been discovered.

### `data/analysis/jev_pilot/`

`sample.csv` contains complete selected source passages and provenance; `requests.jsonl`
contains the exact hosted request bodies. `review.csv` is a blinded annotation template.
After opt-in execution, `responses.jsonl` retains complete responses keyed by request hash,
and `predictions.csv` retains local and Jev labels, the full probability distribution, latency,
and source provenance. `summary.json` distinguishes prepared, partial cached, complete, and
failed runs. Here `complete` means all sampled predictions were produced, not that the dataset
is complete or that accuracy improved. Gold-dependent metrics are null until labels exist.
