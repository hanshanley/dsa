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
**25,464 claims**: 11,496 Democratic, 9,074 Republican, and 4,894 DSA. All 2,623
chunks were attempted; 2,596 normalized and 27 failed chunks remain explicitly
excluded. Targeted assistant review covered 142 blocks and flagged 1,054
candidates. Flags and duplicates can overlap; these counts are not additive
exclusion categories. All source text, failed attempts, and original wording
remain preserved. Unidentified semantic errors may remain; this is exploratory
analysis, not full-corpus semantic certification.

Both strict and expanded KDEs completed with 10 dimensions. Expanded sampling
uses 4,894 claims per organization; strict sampling uses 743 per organization.
The strict DSA input comprises three adopted documents, versus 122 documents
in the expanded input. Source-type and period sensitivity is not a measured
change in positions over time. The
[expanded document chronology](../data/analysis/national_claims/full/expanded/document_chronology.csv)
and [strict chronology](../data/analysis/national_claims/full/strict/document_chronology.csv)
summarize the independently fitted pooled spaces, not annual ideological trajectories.

A second offline run reproduced all 2,879 substantive files exactly and reused
the GTE cache. All 2,879 ZIP members matched current files; both tokenizers stayed
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
also includes its raw model responses and manifests.

```bash
uv run python -m unittest tests.test_national_claim_corpus \
  tests.test_national_claim_analysis tests.test_national_claims \
  tests.test_national_platforms tests.test_national_platform_kde -q
```
