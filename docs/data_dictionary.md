# Data dictionary

## `documents.csv`

One row per source document or media item. `source_tier` is `1`, `2`, `3`, or `4` under the
methodology hierarchy. `verification_status` records whether a reviewer checked the content.

## `endorsements.csv`

One row per endorsing body, candidate, and race. Multiple DSA bodies may endorse the same
candidacy. `endorsement_source_document_id` must reference `documents.csv`.

## `race_candidates.csv`

One row for every candidate on a tracked Democratic-primary ballot. The endorsed candidate and
all opponents are retained, including withdrawn candidates who remained on the certified ballot.
`evidence_status` tracks whether first-party policy material has been reviewed for that person.

## `excerpts.csv`

One row per exact quotation. `locator` is a page, heading/paragraph, or timestamp. `reviewed`
must be `true` before the excerpt can support final analysis.

## `contrasts.csv`

One row per candidate/opponent/topic comparison. `contrast_type` is `explicit_conflict` or
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
text is deduplicated within endorsed/opponent group and election cycle, so a shared national
platform is not multiplied across state races; all contributing provenance is retained.

### `data/analysis/organizational_context_text_corpus.csv`

Generated exact-text segment snapshot for official DSA-versus-Democratic analysis. Eligibility
requires a full-platform category, at least 20 tokens, and no boilerplate flag. DSA National and
state/local DSA categories form the DSA group; DNC National and state Democratic Party categories
form the Democratic group.

### `data/analysis/model_topic_classifications.csv`

Local sentence-transformer output for every eligible candidate segment. It preserves exact text
and aggregated candidate/race/document/source provenance and adds:

- pinned model name and local device;
- predicted CAP topic code/name;
- cosine similarity;
- runner-up topic and similarity;
- top-two margin;
- keyword-baseline topic/score and agreement flag.

### `data/analysis/model_topic_validation.json`

Run-level counts and diagnostics: classified/unclassified rows, threshold, low-margin rows,
keyword agreement, input hash, source-document count, and corpus lineage. The legacy
quotation-level reviewed-code crosswalk is marked inapplicable to full-document segments.

### `data/analysis/primary_sticking_points.csv`

Committed, deduplicated snapshot of the source-supported candidate/opponent contrast table used
for topic and election-cycle charts.
