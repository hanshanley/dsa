# Local Gemma claim-extraction pilot

This is an isolated preprocessing experiment for the national Democratic,
Republican, and DSA corpus, **not a replacement for the published passage-based
analysis**. No claim-based embeddings, UMAP, or KDE are fitted by this command.
Nothing is deployed to The Margin of Error.

## Design

The pilot takes 20 source blocks per organization from the existing
hash-verified, policy-scoped, eligible source corpus. Sampling cycles through
document types and eight-year publication strata, then through documents within
each stratum. Stable hash ordering makes selection independent of CSV row order.
The organizations are interleaved during inference.

Blocks are complete scoped paragraphs containing 40–140 whitespace-separated
words. This deliberately bounded pilot does **not** evaluate very long
paragraphs, very short fragments, or full-document extraction completeness.
Up to 2,000 preceding source characters provide reference-resolution context;
their offsets are retained separately. Context is not another extraction target.
Publication strata describe the available source dates, not inferred adoption
dates or continuous historical coverage.

Gemma extracts factual assertions, characterizations, predictions, policy
positions, and evaluations. Types may overlap. The prompt requires preservation
of negation, modality, conditions, uncertainty, actors, attribution, and temporal
scope. It explicitly distinguishes a proposal from an accomplished fact.
Generic document attribution avoids mechanically adding a party name to every
potential embedding input. No minimum claim length is imposed.

The model is `mlx-community/gemma-3-27b-it-8bit`, pinned to revision
`524cdc4f56a58ef94949ba65dc63a29c48362b1a`, an **8-bit conversion** of
`google/gemma-3-27b-it`, not the original unquantized checkpoint. Inference is
local, text-only MLX-VLM, greedy (`temperature=0`), with seed 0 and a 4,096-token
output cap. The exact prompt, generation settings, source hashes, and input
fingerprint are in `pilot_manifest.json`; observed runtime versions and model
configuration hash are in `runtime.json`. Greedy settings do not guarantee
bitwise-identical results across hardware and library versions.

## Run on an Apple Silicon Mac

The inference dependencies are isolated from the existing Torch/GTE environment
using the script's pinned dependency declaration:

```bash
# Inspect the sample and rebuild cached exports; never loads/downloads a model.
uv run python -m dsa_analysis.national_claims --prepare-only

# Explicitly authorize the initial model download (approximately 31 GB).
uv run --script scripts/national_claim_pilot.py --download-model

# Resume using the local checkpoint and completed per-block response cache.
uv run --script scripts/national_claim_pilot.py
```

The baseline `pyproject.toml` and `uv.lock` are unchanged. Where a package proxy
prevents `uv` from installing the isolated script environment, use a separate
virtual environment with the same declared versions:

```bash
python3.12 -m venv .venv/gemma-pilot
.venv/gemma-pilot/bin/python -m pip install \
  'mlx==0.32.4' 'mlx-vlm==0.3.12' 'mlx-lm==0.30.7' 'transformers==5.1.0'
PYTHONPATH=src .venv/gemma-pilot/bin/python -m dsa_analysis.national_claims --download-model
```

Completed responses are written atomically. A changed input, prompt, model
revision, or generation configuration requires a different `--output` directory;
stale cached responses are rejected. `--per-group` and `--max-tokens` are bounded
pilot controls, not changes to source eligibility. Model downloads require the
explicit flag when the pinned snapshot is not already cached.

## Evidence and validation

Outputs are under `data/analysis/national_claim_pilot/`:

- `blocks.csv`: exact input blocks, context, source identifiers, and offsets.
- `complete_sources.csv`: complete and scoped text of every sampled document.
- `responses/`: unedited model responses, timing, and generation metrics.
- `claims.csv` and `claims.jsonl`: structurally valid candidate claims with exact
  evidence spans and source offsets.
- `block_status.csv`: missing runs, validation errors, unresolved references, and
  review status; rejected candidates remain recoverable in the raw responses.
- `pilot_documents.zip`: complete sampled sources, input blocks, candidate
  claims, statuses, configuration, and summary—not a metadata-only download.
- `summary.json`: observed counts, inference time, generated tokens, and peak
  memory. Inference time excludes download, installation, and model loading.

Validation accepts a bare JSON object or one complete JSON code fence, never
arbitrary JSON extracted from surrounding prose. Unknown types, malformed
objects, duplicate claims within a block, invented or altered quotations, and
output-cap hits are flagged. An exact quotation proves traceability, **not**
semantic support, completeness, correct attribution, or truth.

Every automatically exported claim remains `analysis_eligible=False`.
Source-level fidelity review must precede any corpus-wide rollout. A later
claim-based sensitivity analysis must retain the existing organization/document/
period-bundle weighting and compare against the original passage baseline;
additional extracted claims must not turn a prolific document into additional
independent document support.

## Calibration and interpretation

The initial three-block calibration is preserved under `calibration/`, with its
original prompt, response cache, and runtime metadata. It exposed unresolved
narrator pronouns and evidence punctuation changed during splitting. The revised
prompt adds explicit self-containment rules and examples requiring the original
whole sentence as evidence for each split claim. Calibration is separate from
the subsequent 60-block pilot and must not be pooled into its throughput or
quality counts.

This is extraction, not fact-checking. The useful question is whether the model
preserves each document's assertions while standardizing the unit of analysis.
It can also remove rhetorical emphasis or introduce a shared model writing
style. Passing a small pilot would justify broader testing, not demonstrate that
claim-based KDE is a superior or unbiased measure of organizational positions.
