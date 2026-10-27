# Claim-normalized national platform analysis

The new path analyzes **Gemma-normalized claims instead of source passages**.
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

Exact case-insensitive claim duplicates within a document remain downloadable
with `duplicate_of`, but are excluded from fitting. Identical claims in different
documents retain their respective attributions. Model settings, prompts, input
hashes, and chunk ordering fingerprint the cache; changed configurations cannot
silently reuse old responses.

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

The [first completed claim analysis](../report/national_claim_analysis_sample.md)
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
`response_history/`. Repair attempts include the failed response and its errors.

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
