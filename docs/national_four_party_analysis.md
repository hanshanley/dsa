# Four-party national platform comparison

The Libertarian expansion uses the same national-only scope and January 1,
2000 through October 26, 2026 cutoff. Candidate platforms and state/local
organizations remain excluded. The completed three-party extraction and
analysis are preserved, not regenerated.

## Current status and sources

Source recovery and pipeline regression tests are complete. Libertarian-only
claim extraction is in progress; no completed four-party numerical result is
claimed yet.

The [source ledger](../data/manual/libertarian_platform_sources.csv) records
11 adopted editions: 2000, 2002, 2004, 2006, 2008, 2010, 2012, 2014, 2016, 2018,
and 2022. The first five are historical HTML reproductions from LPedia, the
Libertarian National Committee's historical preservation project. The other
six use original party PDFs preserved by that archive, including their
adoption statements. Archive introductions, tables of contents and navigation
are outside analytical scope. PDF page markers and credits remain auditable
and are not substantive policy evidence.

The archive index explicitly records no platform changes in 2020 or 2024.
Those are applicability/reuse links to 2018 and 2022, not new independent
documents. The 2026 Platform Committee chair's report independently explains
that the 2024 convention had no time for platform issues.

**2026 adoption remains unresolved.** The current official platform matches
the original adopted 2022 PDF except for singular/plural `government(s)` in
the Statement of Principles, after removing PDF page markers and page numbers
and normalizing case/punctuation. Its official WordPress metadata says
July 28, 2026 was the last modification; that is not an adoption date. The
captured 2026 committee report contains proposals, not evidence that they
were adopted. Neither a missing archive entry nor the live page is treated
as proof of an unchanged 2026 convention outcome.

[Coverage and dispositions](../data/analysis/libertarian_platforms/coverage.csv),
[publication chronology](../data/analysis/libertarian_platforms/year_coverage.csv),
[complete source texts](../data/analysis/libertarian_platforms/complete_sources.csv)
and the [full source download](../data/analysis/libertarian_platforms/source_documents.zip)
are available now. [Research provenance](../data/analysis/libertarian_platforms/source_research.json)
links preserved official-page, archive-affiliation, convention and committee
captures with their hashes. Complete raw captures and metadata are retained
under `data/raw/libertarian_platforms/`, including the supplementary research.

## Isolated extraction and analysis

The Libertarian input contains 65,463 scoped words in 340 bounded chunks.
The model, prompt, source-fidelity revision and validation rules are unchanged.
Only the separate Libertarian component receives new inference.

```bash
# Build the source corpus from preserved captures and cached tokenizer.
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run python -m dsa_analysis.national_four_party sources

# Inspect/prepare the isolated extraction without loading Gemma.
uv run python -m dsa_analysis.national_claim_corpus \
  --corpus data/analysis/libertarian_platforms \
  --output data/analysis/national_claims/libertarian --prepare-only

# Use the existing isolated MLX runner; successful chunks resume unchanged.
uv run scripts/national_claim_corpus.py \
  --corpus data/analysis/libertarian_platforms \
  --output data/analysis/national_claims/libertarian

# After extraction/review: merge components, then fit both four-party views.
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run python -m dsa_analysis.national_four_party analyze
```

Fetching is explicit with `sources --fetch`; model downloads are explicit
with `--download-model`. Inference requires the pinned cached Gemma snapshot
and its isolated MLX environment, as in the
[existing extraction instructions](national_claim_analysis.md#run-locally).
Do not overlap model jobs.

The merger retains original claim IDs, candidate wording, supersession
relationships and component-specific normalization fingerprints. Manifests,
source texts, blocks, original replies, retries, reviews and corrections are
preserved under `components/`; no shared normalization fingerprint is invented.
Merged rows name their normalization component and the component manifest
records input-file hashes. Complete downloads contain actual claims and
source texts, not metadata alone.

Four-party outputs live under `data/analysis/national_claims/four_party/`,
`figures/national_claims/four_party/` and
`report/national_claim_analysis_four_party.md`. The shared fitting uses all
four organizations, equal-organization sampling and equal aggregate
document/fallback-bundle weights, producing six pairwise contrasts. Strict
and expanded maps are fitted separately; neither replaces or shares
coordinates with the preserved three-party maps. Results describe language
in the selected historical input, not ideological distance or policy agreement.
