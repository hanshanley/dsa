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
