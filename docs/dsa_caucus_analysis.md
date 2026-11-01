# DSA caucus comparison

This is a separate snapshot of caucus programs and political strategy, not an
extension of the historical national-party corpus. Primary inputs are thirteen
flagship statements available on November 1, 2026. Springs of Revolution is
identified as a network rather than a caucus. Document counts are not membership,
electoral strength, or influence.

## Sources

The [curated ledger](../data/manual/dsa_caucus_sources.json) records exact scope
boundaries, source URLs, known dates, and qualifications. Complete captures and
their hashes are preserved separately from modeled text. A retrieval date is not
an adoption date. North Star's statement dates to 2019 with a June 2023 update;
Socialist Majority explicitly records June 14, 2024 adoption; Reform &
Revolution records January 18, 2026 adoption.

The public corpus includes every complete primary statement, not just metadata.
Original SMC and Groundwork page HTML is retained locally but not republished:
embedded website application tokens fail the existing publication scanner.
Their complete extracted text and original artifact hashes are preserved.
No scanner rules are weakened to publish those page internals.

City & State and the LSC-authored guide are discovery sources only. The latter
explicitly disclaims representing LSC consensus. Neither guide contributes claims
to a caucus attention-share denominator.

The public Mass Action, Mass Work, and Red Line documents are recovered
supplements, not missing primary sources. Their text concerns a Vermont caucus,
a Twin Cities caucus draft, and a regional coalition, respectively. These do not
silently enter the national comparison. Constellation remains unrecovered;
Red Labor's stale domain serves unrelated content. Those gaps do not demonstrate
the absence of political positions.

## Extraction and numerical methods

The existing pinned local Gemma extractor processes bounded source chunks with a
separate source-fidelity revision. It retains original replies, retry history,
claim classifications, exact evidence offsets, and failure dispositions.
The shared extractor uses DSA as its parent organization; every document title
identifies its authoring caucus, and downstream rows join that caucus by document
ID. Identical wording from different caucuses retains both source attributions.

The pinned GTE encoder, explicit untruncated token checks, learned-topic candidate
selection, balanced refit diagnostics, shared UMAP dimension sweep, and weighted
KDE follow the existing analysis. Caucus topics are fitted independently; old
party-topic numbers and density values are not reused.

Attention shares give equal weight to documents within each caucus and retain
unclustered claims in the denominator. All directed caucus pairs are exported.
The rest-of-caucuses baseline averages each other caucus's share equally.
Ratios use unrounded shares without smoothing; a zero denominator is undefined.

One flagship document per caucus is a snapshot, not repeated independent evidence.
No error bars, historical trajectories, membership weights, or ideological-distance
claims are inferred. Topic labels and reported positions require review of actual
source-backed evidence before publication; automated extraction is not human gold.

Targeted assistant review checks central topic examples, their cited source
passages, and narrator attributions. Its exclusions are recorded in
`claims/semantic_review.csv`; original claims and replies remain available.
Source-bound records in `claims/source_repairs/` recover narrowly correctable
actors, qualifications, references, proposal modality, and evidence IDs. They
bind the exact source block, model response bytes, and extraction fingerprint.
These records are identified as assistant corrections, not successful model
generation; failed-model replies are never silently rewritten.
The `source_review_*` files preserve initial-fit review material and its exact
basis, including subsequently excluded wording; they are audit history, not
the current eligible claim set.
This is not an exhaustive independent human audit. Failed chunks and excluded
claims do not enter attention-share denominators, and their absence can affect
the results. The report states both counts. Differences in statement dates,
writing style, and normalization granularity also limit comparisons.

## Commands

Run from the repository root using the corresponding installed browser, local
Gemma, and numerical runtimes. Cached model revisions are required; these commands
do not implicitly download models.

```sh
node scripts/fetch_dsa_caucus_sources.mjs
PYTHONPATH=src:scripts python scripts/fetch_dsa_caucus_supplements.py
PYTHONPATH=src:scripts python scripts/dsa_caucus_analysis.py prepare
PYTHONPATH=src:scripts python scripts/dsa_caucus_analysis.py extract
PYTHONPATH=src:scripts python scripts/dsa_caucus_analysis.py extract --retry-failed
PYTHONPATH=src:scripts python scripts/dsa_caucus_analysis.py analyze
```

After the current topic evidence has been read and source-bound labels recorded
in `comparison/reviewed_topic_labels.json`, publish with
`PYTHONPATH=src:scripts python scripts/publish_dsa_caucuses.py`. The review's
basis hash binds exact claims, sources, assignments, shares, and fitted outputs;
stale or unsupported labels fail rather than silently following new topic IDs.

The browser collector accepts `PLAYWRIGHT_MODULE_PATH` for an existing Playwright
installation. PDF recovery reuses the project's optional pypdf reader or native
macOS PDFKit fallback. Keep the same prepared corpus fingerprint when resuming
extraction; changing source boundaries requires a fresh extraction directory.

Data lives under `data/analysis/dsa_caucuses/`, independently of national-party
outputs. Publishing figures belong in `figures/substack/caucuses/` and
`figures/margin-of-error/caucuses/`, with the existing destination backgrounds.
Complete claim sets, source evidence, and original normalization records accompany
the final comparison, not metadata-only downloads.
