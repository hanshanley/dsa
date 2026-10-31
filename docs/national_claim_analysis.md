# Claim-normalized national platform analysis

The new path analyzes **normalized claims instead of source passages**:
base local-Gemma extraction plus separately identified, source-bound assistant
corrections.
It preserves the passage-based study as a separate baseline and does not deploy
anything to The Margin of Error.

## Input chunks, not whole documents

The eligible input contains 135 documents and 478,335 policy-scoped words.
The deterministic partition has **2,623 chunks**: 1,118 Democratic, 931 Republican,
and 574 DSA. The target is 180 words; the **hard maximum is 240 source words**.
Long paragraphs are split at sentence boundaries where possible, otherwise at
whole-word boundaries. Short assertions and headings are not silently dropped.
Short documents can naturally fit within one bounded chunk.

Each call includes only that chunk, its metadata, and at most **1,200 characters
of preceding context** for reference resolution. It does not include the full
document. Context is not an extraction target. The source-fidelity revision sees
the same bounded source/context plus that chunk's proposed claims.

Every eligible source word is assigned once, in source order. Chunk/unit offsets
refer to the original scoped source text, with source hashes retained. Complete
documents are exported for audit/download; they are not sent wholesale to Gemma.

## Normalization and checks

Inference uses the cached 8-bit MLX conversion
`mlx-community/gemma-3-27b-it-8bit`, revision
`524cdc4f56a58ef94949ba65dc63a29c48362b1a`, locally on Apple Silicon.

The compact response has `claim_text`, `claim_types`, and integer `evidence_ids`.
Conditions, modality, named actors, time qualifications, negation, and quoted-speaker
attribution stay **inside each standalone claim's text**. Stance wording such as
"Support for" and "Commitment to" removes narrative boilerplate without treating
a document as the governmental implementing actor. Party identity remains metadata.
The five claim types are factual assertion, characterization, prediction,
policy position, and evaluation.

Each chunk receives extraction and a second source-fidelity revision. Both stages
have bounded structural retries; every raw response is preserved. Revision is
the same local model, **not an independent evaluator or human certification**.
Schema validity and exact evidence offsets do not establish semantic entailment
or factual truth. Known unresolved references and failures remain explicit.
Failed blocks do not silently become analysis input.
Repair requests retain a hash of the failed reply and its diagnostics, but do
not include the complete failed answer as a response-shaped example to copy.
They reiterate bracketed source-unit IDs and ask for exact source-attested names
containing pronoun-like words to remain quoted, not renamed. Raw attempts and
replaced records remain preserved. Each attempt records its actual request hash,
and response records identify the inference implementation version; these retry
instructions do not change the original source prompt or its cache fingerprint.
Retry requests encode the same source-unit text as JSON values keyed by bracketed
unit IDs, separating the evidence labels from numbered clauses inside the text.
JSON decoding recovers the original unit text unchanged; reference-only context
and revision drafts remain distinct. This presentation change does not certify
correct citations or source fidelity. `--retry-failed --block-id BLOCK_ID` can
target an individual failed block without regenerating successful or other
unselected blocks; unknown IDs are rejected before model initialization.

After extraction, a deterministic step replaces recognized source-organization
stance prefixes in **policy-position-only** claims: for example, "Democrats will
seek ..." becomes "Commitment to seek ...". The predicate is retained verbatim,
including negation, mechanisms and qualifications. Other organizations' names,
past actions, predictions and mixed-type claims are not rewritten. The original
model wording remains in `model_claim_text` and the raw responses; `claim_text`
contains the analysis wording. The extraction summary records this step's version
and affected count. Changed analysis text invalidates its downstream text caches,
without regenerating or overwriting the original inference records.

Exact case-insensitive claim duplicates within a document remain downloadable
with `duplicate_of`, but are excluded from fitting. Identical claims in different
documents retain their respective attributions. Flagged candidates cannot serve
as duplicate anchors: a later unflagged copy remains eligible. Model settings,
prompts, input hashes, and chunk ordering fingerprint the cache; changed configurations cannot
silently reuse old responses.

Assistant source-fidelity reviews exclude identified candidates without deleting
their raw wording or source evidence. A metadata-only adoption chunk was observed
to copy policy claims from reference-only context; those candidates are excluded.
This demonstrates that same-model revision and valid evidence offsets do not
guarantee that a claim is supported by its cited target unit. The reviews are
targeted checks, not a representative error estimate or corpus-wide certification.

### Targeted source-bound corrections

`full/source_repairs/` contains auditable corrections for failed extractions and
reviewed source-fidelity errors. Each record binds the entire bounded target,
reference-only context, exact raw-response bytes and normalization fingerprint.
A stale binding stops export. Corrections use the unchanged claim schema and
evidence validator; they do not rewrite raw replies or relax citation checks.
Only the target supplies claims; context can resolve references but cannot
contribute independent assertions.

An optional `replaces_claim_numbers` selects original candidates to supersede,
preserving valid neighbors' IDs and wording. Whole-block corrections also permit
an empty claim list for contents pages, credits and other non-policy material.
Superseded originals remain downloadable with `superseded_by_repair` and cannot
enter fitting or anchor duplicates. Replacement rows have
`normalization_origin=assistant_source_repair`, a correction hash in `repair_id`
and blank `model_claim_text`; they are not represented as Gemma output.

`model_status` and original diagnostics preserve failed model outcomes even when
effective `status=source_repaired` recovers the source content. Historical review
flags remain attached to original candidates; `unrepaired_flagged_model_claims`
separately counts flagged originals without a superseding correction. Repairs
preserve actors, reported speakers, conditions, timing and modality, and remove
context-only imports and non-policy inventions. These remain targeted assistant
judgments, not independent human gold or a representative accuracy estimate.

## Downstream analysis

`claim_text`, never its supporting source quotation, feeds the existing pinned
GTE encoder, shared UMAP dimension sweep, three-organization KDE contrasts,
exploratory regions, and document chronology. Expanded and platforms/programs-only
views fit separately. Organization samples are balanced and each document or
predefined fallback-period bundle receives equal aggregate KDE weight.
Both pinned tokenizers check each complete claim before fitting; claims over
the 256-token limit stop analysis rather than losing qualifiers to truncation.
Per-claim lengths and the text/model cache fingerprint are exported.

The existing pinned MiniLM/CAP topic method also classifies claims. The 0.2
minimum cosine threshold is unchanged; unclassified claims remain in the
denominator. Topic shares assign equal aggregate weight to each document/bundle,
so splitting more claims does not create another independent document.

The [full eligible-claim comparison](../report/national_claim_analysis.md) analyzes
**26,483 claims**: 11,870 Democratic, 9,460 Republican, and 5,153 DSA. The original
model outcomes remain 2,596 normalized and 27 failed chunks. Effective dispositions
are 2,462 model-normalized and 161 source-repaired chunks, including all 27 model
failures and all 134 blocks with identified review issues.

The repairs supply 1,041 replacement claims and supersede 1,078 original
candidates. Eligible claims comprise 25,442 model-origin and 1,041 assistant-origin
rows. All 26,679 original candidates remain downloadable alongside the replacements;
the complete candidate export therefore has 27,720 rows, not 26,483 analytical
observations. Thirteen corrections supply no replacement claims for non-policy
or context-only inventions. One source's unspecified "right to choose" is left
unresolved rather than assigned a substantive meaning.

Targeted assistant review covered 142 blocks and flagged 1,054 original candidates;
none remain without a superseding correction. Historical flags, supersession and
duplicates overlap, so their counts are not additive exclusion categories.
All source text, failed attempts and original wording remain preserved.
Unidentified semantic errors may remain; this is exploratory analysis, not
full-corpus semantic certification.

The expanded KDE completed with 10 dimensions; the strict KDE selected 5.
Expanded sampling uses 5,153 claims per organization; strict sampling uses 842.
The strict DSA input comprises three adopted documents, versus 122 documents
in the expanded input. Source-type and period sensitivity is not a measured
change in positions over time. The
[expanded document chronology](../data/analysis/national_claims/full/expanded/document_chronology.csv)
and [strict chronology](../data/analysis/national_claims/full/strict/document_chronology.csv)
summarize the independently fitted pooled spaces, not annual ideological trajectories.

A second offline run reproduced all 3,040 substantive files exactly and reused
the GTE cache. The embedding and topic-score arrays also matched byte-for-byte.
Replaying preserved model responses and correction records reproduced the
candidate exports exactly. All 3,040 ZIP members matched current files; both tokenizers stayed
below 256 tokens with no truncation. ZIP/SVG metadata and the analysis summary's
cache-use indicator are not required to match byte-for-byte across runs.
The [reproducibility audit](../data/analysis/national_claims/reproducibility_audit.json)
records measured counts and selected input/output hashes. The passage baseline
and selected sample remain unchanged.

The [earlier selected claim analysis](../report/national_claim_analysis_sample.md)
uses **199 individually unflagged pilot candidates**: 59 Democratic, 82 Republican,
and 58 DSA, representing 25 documents. Both KDE views and topic classification have
actually run. This is a selected, assistant-reviewed sample, **not full-document
coverage or an estimate of platform-wide emphasis**. Its frozen pilot wording is
distinct from the full extraction's revised normalization procedure.

## Run locally

### Learned topics and relative emphasis

`national_claim_topics` is a separate, resumable stage on the completed eligible
claim corpus and its cached GTE vectors. It does not rerun claim extraction,
encode new claim embeddings, reclassify CAP topics, or refit the KDE maps.

```bash
# CPU analysis, using preserved claims and validated cached embeddings.
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run python -m dsa_analysis.national_claim_topics prepare

# Local Gemma summaries, in the same isolated MLX environment as extraction.
# Do not overlap this with another local extraction/model job.
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run scripts/national_claim_topics.py label

# Independent numerical discovery within each observed four-year period.
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run python -m dsa_analysis.national_claim_topics evolution-prepare

# Label all period-qualified topics in one isolated local-model invocation.
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run scripts/national_claim_topics.py evolution-label

# Render both views, update the claim report, rebuild the complete source ZIP.
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run python -m dsa_analysis.national_claim_topics render

# Replay numerical/label caches and charts; verify complete ZIP member bytes.
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run python -m dsa_analysis.national_claim_topics audit
```

The existing isolated Gemma interpreter can also run the labeling script
directly with `PYTHONPATH=src`. The main project's Torch stack is not imported
by the labeling path. Model downloads require explicit `--download-model`.
All stages accept `--input`; `prepare --groups democratic republican dsa libertarian`
supports a completed, separately merged four-party input. No incomplete
Libertarian extraction is substituted into the completed three-party analysis.

**Discovery.** Seeded, unwhitened PCA retains up to 50 dimensions. The initial
HDBSCAN candidate is evaluated for assignment coverage. On the full corpus it
left roughly 88% of claims unclustered, so discovery evaluates a fallback grid
of weighted K-means fits (12/18/24/30 clusters). K-means gives each organization
equal aggregate weight and each within-organization document/fallback bundle
equal weight. HDBSCAN has no sample-weight input and is explicitly unweighted.
Model selection uses original-embedding cosine silhouette, coverage, and topic
concentration, not the strength of party contrasts. This run selects 24 topics.
The low silhouette and moderate balanced-refit agreement mean these are useful
exploratory partitions, not cleanly separated or independently validated
categories. K-means assigns every claim even when boundaries are fuzzy.

All eligible expanded claims share one versioned taxonomy. The strict view
reuses the same assignments and recomputes weights on its eligible bundles; it
does not independently refit or relabel topics. Noise remains an explicit
denominator category if the selected method produces it. Tiny/degenerate inputs
retain explicit no-fit/all-noise dispositions, rather than fabricated topics.
Fit IDs are only stable within the same input/model/configuration fingerprint.
A later four-party refit has a separate taxonomy and output directory.

**Keywords and summaries.** A corpus-wide TF-IDF vocabulary includes unigrams
and bigrams, excluding common boilerplate for keywords only. Weighted cluster
means receive a distinctive-term lift against the corpus mean. Actual claim
wording is never rewritten. Representative evidence combines central claims
with observed-group coverage and at most two examples from one group/bundle.
Local Gemma receives a bounded, tokenizer-audited packet, returns structured
titles/summaries/caveats and supporting claim IDs, and retains exact prompts,
raw replies, revisions, runtime details, and validation failures. Topic labels
cannot cite claims outside their packets. Political-actor and organizational
narrative clusters must be described as such, not relabeled as coherent policy
subjects. Valid JSON and supporting IDs do not by themselves establish
entailment; summaries need review against the actual packet.
`label_review.json` records that bounded evidence review for every topic, binding
each decision to the exact fit, evidence packet, and original model-record hashes.
Source-bound assistant revisions are explicitly distinguished from unchanged
Gemma wording. In the current run, 13 labels were revised to identify actor or
narrative clusters, retain opposing examples, or correct one invalid claim ID.
The original raw responses and failures are never rewritten. Stale review records
do not confer reviewed status on changed evidence or regenerated responses.

**Shares and contrasts.** Within each group/view, each claim's weight is
`1 / (claims in its bundle * represented bundles in its group)`. Summed topic
shares include unclustered mass and total one for available groups. Missing
groups are unavailable, never evidence of a zero share. The one-versus-rest
baseline is the arithmetic mean of other available organizations' shares,
not the share of their pooled claims.

Relative emphasis is `log2((share + 0.0001) / (baseline_share + 0.0001))`.
Pairwise contrasts use the same formula. The smoothing term is 0.01 percentage
points. Tables always retain actual unsmoothed shares, percentage-point
differences, and claim/document/bundle support. They also flag zero shares,
fewer than two supporting bundles on either comparison side, smoothing
sensitivity (changing the floor tenfold shifts a ratio by more than 0.5),
and leave-one-bundle-out sign or rank sensitivity (rank range at least three).
**All support levels remain ranked**, as requested. Warnings are not grounds
for silent removal. Large finite ratios against tiny baselines are not proof
of important, representative, or statistically significant differences.

Leave-one-bundle-out calculations keep the taxonomy fixed and renormalize
shares; they do not measure clustering uncertainty. Separate balanced
organization/bundle refits compare shared claim IDs in the fixed PCA space,
including noise, with adjusted Rand scores. Nearby candidate fits record
agreement with the selected fit. None of these diagnostics certifies topics
or removes the corpus's unequal period and source-type composition.

**Outputs.** CSV/JSON evidence under `topics/` includes every claim assignment,
keywords, full representative claims and exact original evidence, strict and
expanded shares, all ranked contrasts and warnings, candidate diagnostics,
balanced-refit sensitivity, local label packets/responses, and input/output
hashes. Both PNG and SVG charts show overall shares in aligned organization
columns with direct values and common scales. Group-versus-rest and pairwise
figures show **unsmoothed percentage-point differences**, not heatmap colors
or smoothed log ratios. The complete smoothed log2 ratios, shares and support
warnings remain in the contrast downloads.

The pooled fit and all 24 reviewed labels are unchanged. Three party-identity
clusters (`topic-007`, `topic-017`, `topic-024`) are excluded from substantive
charts, rankings and summaries: 21 subjects are displayed. Their claims remain
in overall and temporal denominators; the remaining shares are **not
renormalized**. Full assignments, source evidence and original review records
are retained. `topic_labels.json` marks presentation eligibility with
`displayed`; publication exports omit excluded topics from their presentation
index but retain the complete label download. The separately fitted period
taxonomies are not rewritten or treated as persistent pooled-topic identities.

Large, individual pairwise KDE maps now show at most three numbered supported
region representatives per page, retaining both saved regions in each zone
across two pages where present. Their colors use the common 95th-percentile
absolute **natural-log density contrast**, not the topic-share log2 ratio.
Density is estimated in higher-dimensional space; the UMAP coordinates only
display claims. Markers identify representative claims, not region boundaries.
The full claim, source title/date/locator, raw regional group support, and exact
representative contrast are exported in `expanded/density_region_evidence.csv`
and its strict equivalent. Regional memberships were not saved; a representative
score must not be presented as a regional mean. TF-IDF keywords are retrieval
aids, not reviewed subjects or evidence of policy agreement. Density PNGs
remain 200 DPI. Only the embedded point-cloud raster in density SVGs uses
125 DPI; headings, labels and scales remain vector-based. This keeps the
complete combined archive publishable without dropping claims or evidence.

The `render` stage verifies the current source, embedding, numerical-code and
output hashes before using labels. Stale or failed labels remain explicitly
provisional. Cached labels can replay without generating new responses.
Reports lead with these concrete distributions and source-linked examples,
while keeping the earlier CAP and KDE numerical results unchanged. The full claim/source
ZIP contains actual complete texts, claims, provenance, topic-stage CSV/JSON
evidence, all full-corpus PNG/SVG figures, and `report.md` with figure/data links
rewritten for the extracted archive. This is one combined deliverable, not separate
metadata-only and figure downloads. SVG identifiers and metadata are deterministic;
the topic replay audit checks exact PNG/SVG bytes and every archive member.
It does not retroactively extend the earlier KDE reproducibility certification:
existing CAP/KDE figures are restyled from their saved numerical tables without
refitting their models.

**Over time.** Rendering also exports `temporal_shares.csv`,
`temporal_contrasts.csv`, `temporal_changes.csv`, `temporal_coverage.csv`,
`temporal_document_dates.csv`, and explicit `temporal_exclusions.csv`. Four-year
bins begin in 2000; the last bin ends at the study's October 26, 2026 cutoff and
is partial. Known adoption dates take precedence over publication dates; year-
and month-only precision is preserved rather than assigning a fictitious day.
Missing/invalid or out-of-scope dates are excluded from temporal analysis with
their reasons, not from the pooled corpus.

The topic taxonomy is fixed, not refitted per period. Weights are recomputed
within each group/period/view, including when a fallback bundle spans periods.
Each topic has a standalone comparison bar chart and a standalone multi-group
timeline in `<view>/issues/`, in PNG and SVG. These replace the large per-group
time heatmaps and crowded multi-topic trend pages. Missing documents leave
gaps in lines, never zero topic shares. Topic titles wrap without truncation;
each topic's timeline uses the same zero-based scale across organizations and
both views, while different topics can have different vertical scales.
`temporal_coverage.csv` records per-period document and bundle support. There is no forward filling:
Republican reuse of the 2016 platform in 2020 is not a new text observation.
Strict DSA gaps remain visible rather than being filled with fallback statements.

Group-versus-rest temporal contrasts require all configured other organizations
in the same view/period, ensuring that the reference groups do not silently
change. Pairwise contrasts require both organizations. Adjacent-period
percentage-point changes are only computed when both neighboring periods are
observed for that group; no differences bridge an evidence gap. All periods'
raw shares, support, low-support/smoothing warnings and comparison group IDs
are downloadable. These are document-composition trajectories, not annual
position estimates, causal shifts, or sentiment/ideology trends.

The main analysis accepts `--topics` to prepare numerical topics and render
available cached labels; it never silently loads Gemma. When existing topic
artifacts are present, the normal report rebuild also restores their report
section after checking freshness.

**Independent period discovery.** This is an additional analysis, not a
replacement for pooled topics or fixed-topic trends. Every four-year period
gets its own PCA, clustering, vocabulary/keywords and representative evidence,
using only that period's claims and cached embeddings. Fewer than 50 claims
means no substantive fit. Candidate density parameters are minimum cluster
size 30 and minimum samples 5; density coverage below 50% triggers a weighted
K-means grid of 4/6/8/12 clusters, using the existing geometry/concentration
selection rule. Parameters are fixed across periods, not tuned for striking
group contrasts. Strict shares reuse each period's expanded fit.

The current corpus yields 64 topics across seven independent fits, not 64
globally distinct policy categories. In 2004–2007 and 2008–2011, the selected
density fits yield two clusters each with roughly 44% unclustered mass.
Plots retain unclustered shares and the report qualifies broad/mixed clusters;
small positive silhouettes do not make them validated policy taxonomies.
Within-period contrasts retain low-support and smoothing warnings. Versus-rest
comparisons require every configured group; missing observations are not zeros.

`topics/evolution/` contains assignments, shares, contrasts, local keywords,
full source-linked representatives, candidate diagnostics, balanced refits,
date/coverage dispositions, labels and review records. Period-qualified IDs
are not persistent topic identities. Original-space centroids use equal-group
and within-group bundle weights and are saved in `centroids.json`. For each
later topic, `adjacent_matches.csv` records the closest preceding-period
centroid. Only mutual nearest matches with cosine similarity at least 0.80
are candidate thematic continuities; all other matches remain uncertain.
No matching bridges a missing period. No result establishes issue birth,
death, splitting, merging, agreement or causal ideological change.

`evolution-prepare` is explicit. Routine rendering validates its prepared
inputs, numerical implementation and output hashes and refuses stale fits;
it never silently refits independent period topics or invokes a model.
Every published period-topic label receives the same hash-bound bounded
evidence review as pooled labels, retaining raw replies and identifying any
assistant revisions separately. The current 64 period-qualified labels are all
reviewed; 34 have explicit source-bound assistant revisions. This is bounded
representative-packet review, not independent human certification of each cluster.

**Publication styling.** All current full-corpus figures use the restrained
warm-paper palette from `hanshanley/uk_decline`, reference revision
`2c9dbb0715dfd737b36484fc395578d7e8a669af`. Democratic blue, Republican
terracotta and DSA gold remain consistent across charts. Default PNG/SVG
figures have the Substack background `#F7F5F0`; corresponding website versions
live under `figures/national_claims/full/themarginoferror/` with `#F5F5F5`.
PNG background conversion changes only exactly matching opaque pixels;
SVG copies replace the corresponding background fill. Data colors,
dimensions, text and values are unchanged. PNG originals use 200 DPI;
SVG identifiers and metadata are deterministic. Both versions, all temporal
evidence, actual claims and complete source texts enter the combined archive.

Standalone issue cards use a fixed 1800 × 1100-pixel canvas (9 × 5.5 inches),
wrapped titles and compact method notes. Overall comparisons use slim,
zero-based bars with an aligned value column. Timelines label each group's last
observed value beside the plot, rather than using headline-number blocks.
Close labels are separated with thin leader lines to their unchanged data
points. When the latest period is missing, the label names the earlier observed
period; groups without observations are identified explicitly. Neither
displaced labels nor missing periods alter the plotted values.

For the piece, six selected policy subjects also have paired overall/time
graphics on 2100 × 1200-pixel canvases (10.5 × 6 inches). These are editorial
illustrations, not a ranking of the largest contrasts. Both panels and both
views of an issue use the same zero-based percentage scale. Headlines use
unsmoothed observed shares; a largest/smallest ratio is shown only when it is
at least 1.5 and each side contributes at least two bundles. Otherwise the
headline reports the observed share range. Display names shorten the reviewed
labels without changing cluster membership, original labels or evidence.

### Claim extraction and full analysis

Keep Gemma inference in its isolated MLX environment; the main project retains
its existing Torch/analysis dependencies:

```bash
# Inspect the complete chunk inventory without loading Gemma.
uv run python -m dsa_analysis.national_claim_corpus --prepare-only

# Local Gemma inference; resumes completed chunks.
uv run scripts/national_claim_corpus.py

# Optional bounded smoke test, using exactly the same resumable input/cache.
uv run scripts/national_claim_corpus.py --max-new-blocks 3

# Explicitly retry failed blocks while retaining their previous raw responses.
uv run scripts/national_claim_corpus.py --retry-failed

# After extraction finishes: embeddings, topics, both KDE views, report and ZIP.
uv run python -m dsa_analysis.national_claim_analysis

# Reproduce the separate selected-pilot claim analysis.
uv run python -m dsa_analysis.national_claim_analysis --reviewed-sample
```

Model downloads are not implicit. Analysis can explicitly allow its pinned
model downloads with `--download-model`; Gemma expects its pinned cached snapshot.
The MLX script declares its isolated dependencies instead of changing the root
analysis environment.

If the isolated MLX environment is already installed, its Python can run the
same script directly without resolving another environment:
`/path/to/gemma-env/bin/python scripts/national_claim_corpus.py`.
Replace the interpreter path with that environment's actual Python path.
Successful cached chunks are revalidated and reused. Failed chunks are not
retried implicitly; `--retry-failed` preserves their old records in
`response_history/`. Repair attempts include the failed-response hash and error
diagnostics, not the complete failed answer.
Citation errors list the allowed bracketed source-unit IDs explicitly; numbered
list items, headings, and page numbers inside source text are not evidence IDs.
New responses record the implementation version. An already-running worker keeps
its loaded code; later invocations pick up updated repair feedback without
changing the source/model configuration or silently rewriting successful caches.

Outputs are separated under `data/analysis/national_claims/{full,reviewed_sample}/`
and `figures/national_claims/`. The command refuses to present an unfinished full
extraction as a completed comparison. `source_coverage.csv`, `block_status.csv`,
and `extraction_summary.json` distinguish unprocessed and failed chunks.
Each `claim_documents.zip` includes actual claims, complete source texts, provenance,
and available audit/results tables—not metadata-only downloads. Full extraction
also includes its raw model responses, retry history, source-bound correction
records and manifests.

### Group-position clustering atlases

The expanded corpus now has one combined atlas and all three pairwise atlases.
Each covers the 21 substantive pooled clusters, with a numbered map, individual
group summaries, weighted shares and support counts. Pairwise versions add
reviewed distinctions and unsmoothed percentage-point gaps. The frozen
higher-dimensional fit, assignments, excluded identity topics and denominators
are unchanged; reused two-dimensional coordinates are display-only.

```bash
uv run python -m dsa_analysis.national_claim_topic_positions prepare
# Read the actual packets and write source-bound reviews; schema checks are not semantic review.
uv run python -m dsa_analysis.national_claim_topic_positions render
uv run python -m dsa_analysis.national_claim_topics audit
```

Evidence selection alternates two central claims with one peripheral claim,
round-robin across bundles, up to 48 examples per group/topic. The 2,952 selected
claims retain complete wording, source excerpts, offsets, dates and provenance.
All 63 group summaries and 63 pairwise distinctions were assistant-reviewed
against those actual packets, with ambiguous attribution checked in source
evidence. Hash-bound reviews require supported IDs, both observed comparison
sides and multiple supporting bundles when available. Missing evidence never
becomes an inferred stance. Sampled synthesis is neither exhaustive stance
classification nor independent human certification.

Dots represent raw claims, not equal group mass. Pair-map colors are each
claim's frozen topic-share gap, not KDE density or ideological distance. Markers
locate weighted projected topic centres, not boundaries. Statements cover the
observed documents across years, not a current consensus. Cell-specific caveats
and all supporting claims appear in the report and complete downloads.

The full ZIP now exceeds GitHub's repository-file limit and is therefore a
single release asset, configured in `config/national_claim_publication_download.json`.
No evidence or figures are removed. `claim_documents.download.json` records its
size, SHA-256 and member count, and is excluded from the ZIP to avoid a circular
checksum. The archive itself is generated locally and ignored by Git. The
publication exporter reconstructs it from committed sources when absent and
requires its bytes to match the published checksum before exporting the complete
download. Smaller pilot archives retain their existing repository links.

```bash
uv run python -m unittest tests.test_national_claim_corpus \
  tests.test_national_claim_analysis tests.test_national_claims \
  tests.test_national_platforms tests.test_national_platform_kde -q
```
