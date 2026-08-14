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

Committed row-level input for the reproducible text and topic graphs. It is exported from
`data/processed/candidate_statement_evidence.csv` by
`dsa_analysis.text_analysis._load_or_export_analysis_data`.

Key fields:

- `statement_key`, `race_id`, `candidate_name`, `election_date`, `party`, `role`
- `evidence_status`: `verified` or `source_unavailable`
- `topic`, `subtopic`, `stance`: reviewed codes constrained by `config/taxonomy.json`
- `quote`: exact first-party wording
- `source_url`, `source_type`, `published_date`, `locator`
- `direct_opponent_name`, `notes`

Verified duplicate quotations are deduplicated by candidate, election, role, topic, and exact
quote. Source-unavailable rows are deduplicated by candidate, election, and role.

### `data/analysis/model_topic_classifications.csv`

Local sentence-transformer output for every verified exact quotation. It preserves the exact
quote and source URL and adds:

- pinned model name and local device;
- predicted CAP topic code/name;
- cosine similarity;
- runner-up topic and similarity;
- top-two margin;
- keyword-baseline topic/score and agreement flag.

### `data/analysis/model_topic_validation.json`

Run-level counts and diagnostics: classified/unclassified rows, threshold, low-margin rows,
keyword agreement, and reviewed-code crosswalk agreement.

### `data/analysis/primary_sticking_points.csv`

Committed, deduplicated snapshot of the source-supported candidate/opponent contrast table used
for topic and election-cycle charts.
