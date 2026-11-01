<div align="center">
  <h1>Democratic, Republican, and DSA Platforms</h1>
  <p>National policy documents, structured claims, and political language, 2000–2026.</p>
  <p>
    <a href="#overview">Overview</a> ·
    <a href="figures/README.md">Chart guide</a> ·
    <a href="#results-and-downloads">Results &amp; data</a> ·
    <a href="#sources-and-coverage">Sources</a> ·
    <a href="#methods">Methods</a> ·
    <a href="#reproduce">Reproduce</a>
  </p>
</div>

---

## Overview

A source-first comparison of **national Democratic Party, Republican Party, and
Democratic Socialists of America documents**, covering January 1, 2000 through
October 26, 2026. Candidate campaigns, state parties, and local DSA chapters are
outside this comparison.

**Current analysis:** 26,069 eligible claims from 135 documents, organized into
24 shared topics. Charts compare **21 substantive issues**; the three party-identity
clusters remain in the denominators and complete data, but not issue rankings.
The analysis also tracks observed four-year periods and independently discovers
74 period-specific topics within seven periods.

**[Explore the live analysis](https://www.themarginoferror.com/party-platforms/)** ·
[Read the report](report/national_claim_analysis.md) ·
[Get images for Substack](publication/README.md)

### Finding the right files

| Need | Start here |
|---|---|
| This DSA image for Substack | [where-dsa-stands-apart.png](publication/substack/where-dsa-stands-apart.png) |
| Other publication-ready images | [Publishing folder: named issues, overview and positions](publication/README.md) |
| Ratios for every issue | [attention-share-ratios.csv](publication/data/attention-share-ratios.csv) |
| Full analytical data and sources | [Results and downloads](#results-and-downloads) |
| Code and reproduction | [Methods](#methods) · [Reproduce](#reproduce) |

Use `publication/` for final deliverables. The deeper `figures/`, `data/` and
`report/` paths retain canonical research outputs and history; you do not need
to browse them to find a Substack image.

Claims come from local Gemma extraction with separately identified, source-bound
assistant corrections. Topic names and position summaries are reviewed against
source evidence. This is an exploratory comparison of documented language and
attention, not a measure of agreement or independent human certification.

### Where DSA gives more attention

<p align="center">
  <a href="publication/substack/where-dsa-stands-apart.png?rev=attention-shares">
    <img src="publication/substack/where-dsa-stands-apart.png?rev=attention-shares" width="1100" alt="Original embedding graph with five numbered issues, attention-share comparisons and dated DSA statements beside it">
  </a>
</p>

*Five issues with the largest positive DSA attention-share gaps against the
equal-weight Democratic–Republican average, with at least two DSA source bundles.
Callouts show both shares, their ratio, and dated DSA paraphrases.
[Full-size PNG](figures/article/dsa_vs_major_parties_lead.png) ·
[Exact values and source anchors](figures/article/dsa_vs_major_parties_lead.json).*

**Attention share** is an issue's proportion of weighted policy claims, giving
each document or predefined fallback bundle equal weight within its party.
The combined baseline is the arithmetic average of Democratic and Republican
shares. Ratios use unrounded values; a zero denominator is undefined. They do
not measure spending, voter support, or agreement.

**Map colors measure something different:** light purple indicates denser
combined Democrat & Republican language; gold indicates denser DSA language.
The original 26,069 embedding points, coordinates, fitted densities and common
color scale are unchanged. Numbered markers locate reviewed examples, not
issue boundaries.

[Complete attention-share ratios (CSV)](figures/article/dsa_attention_share_ratios.csv)
includes all 24 topics, every party's share, the combined average, percentage-point
gaps, and four directed ratios: **Democratic / Republican**, **DSA / Democratic**,
**DSA / Republican**, and **DSA / the Democratic–Republican average**. The live
analysis shows the selected comparison on the map and all four ratios under
each issue. Identity clusters are explicitly flagged; undefined ratios are blank
in the CSV.

<details>
<summary>Alternative article layouts</summary>

All options retain the same embedding map and source-backed, dated DSA statements.
A is the current lead; B and C show three examples.

| Option | Layout | Image and source data |
|---|---|---|
| A | Map with five statements beside it | [PNG](figures/article/dsa_lead_option_a-map-five.png) · [Data](figures/article/dsa_lead_option_a-map-five.json) |
| B | Wide map with three statements below | [PNG](figures/article/dsa_lead_option_b-map-bottom.png) · [Data](figures/article/dsa_lead_option_b-map-bottom.json) |
| C | Map with three larger statements beside it | [PNG](figures/article/dsa_lead_option_c-map-three.png) · [Data](figures/article/dsa_lead_option_c-map-three.json) |

Rebuild alternatives without changing the current lead:
`python scripts/build_dsa_article_lead.py --variants-only`.
Rebuild the lead and separate
[absolute attention-gap bars](figures/article/dsa_vs_major_parties_attention_gaps.png)
with `python scripts/build_dsa_article_lead.py`.
These standalone article images are not embedded in the website.

</details>

## Results and downloads

**One complete analytical download:**
[Report, analysis figures, result tables, claims, complete sources, raw replies,
history and corrections](https://github.com/hanshanley/dsa/releases/download/claim-source-cleaned-platforms-2026-10-31/claim_documents.zip).
Unzip it and open `report.md`; its chart and table links point to included files.
The archive includes both Substack and The Margin of Error PNG versions.
Its [checksum and size](data/analysis/national_claims/full/claim_documents.download.json)
are tracked, and the exporter can rebuild the identical ZIP offline.
The article leads and attention-ratio CSV are linked separately above.

### Inspect the actual claims

**[All 26,069 analyzed claims (CSV)](data/analysis/national_claims/full/analysis_claims.csv)**
contains the actual wording, organization, document title and dates, source URL,
quoted evidence, offsets, quality flags, and model/correction provenance.

[All 27,726 preserved claim records (CSV)](data/analysis/national_claims/full/claims.csv)
and [JSONL](data/analysis/national_claims/full/claims.jsonl) also retain excluded,
superseded and duplicate candidates. The `analysis_eligible`, `duplicate_of`,
and repair fields distinguish analyzed records from history. Download these
large files if GitHub's preview is unavailable.

[Complete source texts](data/analysis/national_claims/full/complete_sources.csv) and
[representative claims by topic](data/analysis/national_claims/full/topics/representatives.csv)
provide original context and a smaller starting point for reading.

### Overall learned-topic distributions

| Result | Data and explanation |
|---|---|
| Overall attention | [Weighted topic shares](data/analysis/national_claims/full/topics/shares.csv) · [All four attention-share ratios](figures/article/dsa_attention_share_ratios.csv) |
| Relative emphasis | [Ranked contrasts and support warnings](data/analysis/national_claims/full/topics/contrasts.csv) |
| Topics over time | [Period shares](data/analysis/national_claims/full/topics/temporal_shares.csv) · [Observed coverage](data/analysis/national_claims/full/topics/temporal_coverage.csv) |
| Independently discovered period themes | [Shares](data/analysis/national_claims/full/topics/evolution/shares.csv) · [Fit diagnostics](data/analysis/national_claims/full/topics/evolution/period_fits.json) · [Source examples](data/analysis/national_claims/full/topics/evolution/representatives.csv) |
| Reviewed names and positions | [Label provenance](data/analysis/national_claims/full/topics/label_review.json) · [Source-linked group positions and distinctions](report/national_claim_analysis.md#group-positions-on-the-shared-clustering) |

The [chart guide](figures/README.md) links all 21 individual issues, six selected
article graphics, position atlases, supporting density maps, and alternate
backgrounds. Overall charts show weighted shares; relative-emphasis charts show
unsmoothed percentage-point gaps. Identity-cluster shares are not renormalized away.

<details>
<summary>Overview and position atlases</summary>

<p align="center">
  <img src="figures/national_claims/full/topics/expanded/substack_overview.png" width="1100" alt="All 21 substantive subjects compared across Democratic, Republican and DSA national documents">
</p>

[Overview PNG](figures/national_claims/full/topics/expanded/substack_overview.png) ·
[Individual issue charts](figures/national_claims/full/topics/expanded/issues/) ·
[Selected article charts](figures/national_claims/full/topics/expanded/piece/) ·
[Website versions](figures/national_claims/full/themarginoferror/)

Four source-linked atlases pair semantic maps with weighted shares and
individualized positions: [all three groups](figures/national_claims/full/topics/positions/all_groups.png),
[Democratic–Republican](figures/national_claims/full/topics/positions/democratic_vs_republican.png),
[Democratic–DSA](figures/national_claims/full/topics/positions/democratic_vs_dsa.png), and
[Republican–DSA](figures/national_claims/full/topics/positions/republican_vs_dsa.png).
Pairwise atlases also state documented policy distinctions. Their colors show
topic-share gaps, not ideological distance.

[Detailed density comparisons](report/national_claim_analysis.md#detailed-density-comparisons)
retain larger maps and numbered, source-linked examples.

</details>

## Sources and coverage

| Organization | Eligible claims | Expanded documents | Strict documents |
|---|---:|---:|---:|
| Democratic Party | 11,811 | 7 | 7 |
| Republican Party | 9,150 | 6 | 6 |
| DSA | 5,108 | 122 | 3 |

The **expanded view** includes labeled DSA national resolutions and statements
where comprehensive platforms are unavailable. The **strict view** retains
adopted platforms/programs only. Historical Democratic and Republican texts are
labeled American Presidency Project reproductions, not party-hosted originals.
The website presents the expanded comparison; strict results remain downloadable.

Republican reuse of the 2016 platform in 2020 adds no independent observation.
The website's dotted timeline bridge connects 2016 and 2024 without inventing
a 2020 value. Period tables retain the missing Republican 2020–2023 observation.
The final 2024–2026 period is partial.

**The full final 2015 DSA strategy remains unrecovered.** Recovered adopted
priorities and the later summary are separate documents, not substitutes.
Missing recovered publications do not imply an absence of positions. Drafts,
proposals, voting results and later annotations are not automatically adopted wording.

The [source ledger](data/manual/national_platform_sources.csv),
[historical search and gap log](data/manual/national_platform_search_disposition.csv),
and [coverage inventory](data/analysis/national_platforms/coverage.csv) preserve
dates, adoption qualifications, provenance and exclusions.
The wider source archive contains **478 complete-text records and 85 deduplicated
original PDFs**, including supplementary and excluded evidence; these are not
478 independently modeled documents.

<details>
<summary>Source-recovery chronology</summary>

<p align="center">
  <img src="figures/national_platforms/coverage.png" width="1100" alt="Chronology of recovered national documents, distinguishing DSA fallback evidence and source qualifications">
</p>

</details>

## Methods

**Claims and source fidelity.** Gemma receives bounded chunks of at most 240
source words and limited reference-only context. Claims should retain actors,
mechanisms, modality, time, conditions and speaker attribution. Raw replies,
original wording, hashes and evidence offsets remain available. Structural
validation, same-model revision and targeted assistant review are not
fact-checking or corpus-wide semantic certification; unidentified errors may remain.

All 2,623 extraction chunks have effective dispositions. The 162 source-bound
corrections address reviewed errors and all 27 failed model chunks while
preserving original outcomes. They supply 1,047 replacement claims and supersede
1,084 originals; 13 zero-claim corrections dispose of unsupported material.
The analyzed input has 25,022 model-origin and 1,047 assistant-origin claims.
Other identified unsupported claims and within-document duplicates are excluded
without inventing replacements.

**Shares and density.** Pinned GTE embeddings support the shared taxonomy and
UMAP/KDE maps; MiniLM/CAP classification is a supporting reference analysis.
Both tokenizers enforce their limits without silent truncation. Sampling balances
organizations, and each document or predefined DSA fallback-period bundle receives
equal aggregate weight. Expanded and strict shares use the same topic assignments;
their KDEs fit separately and have noncomparable coordinates.

The combined website density comparison uses a **50/50 mixture of fitted
Democratic and Republican KDE densities**, not an average of log densities or
a merged platform. Attention ratios instead divide weighted issue shares.
Neither density nor attention measures policy agreement.

**Review and interpretation.** All 24 pooled and 74 period-specific topic labels
have source-bound reviews, with original Gemma replies preserved. The pooled
review covers 3,311 distinct central claims. A separate 2,971-claim sample supports
63 group summaries and 63 pairwise distinctions across the 21 displayed issues.
Sampling starts near topic centers and spans observed periods, bundles and
documents; it does not deliberately seek peripheral stances.

Pooled results mix periods and genres. Summaries describe observed documents
across years, not an exhaustive or current consensus. The topic partition has
low separation (cosine silhouette 0.060) and moderate balanced-refit agreement
(adjusted Rand 0.649–0.693): it is an exploratory organizational aid.
Timelines describe observed source composition, not annual population estimates.
Adjacent-period embedding similarities suggest possible thematic links, not
proof that issues emerge, disappear, split or merge. The 2008–2011 period fit
has only two substantive clusters and leaves about 48% of claims unclustered.

[Full methods and reproduction](docs/national_claim_analysis.md) ·
[Extraction summary](data/analysis/national_claims/full/extraction_summary.json) ·
[Chunk dispositions](data/analysis/national_claims/full/block_status.csv) ·
[Targeted review log](data/analysis/national_claims/full/semantic_review.csv) ·
[Source corrections](data/analysis/national_claims/full/source_repairs/)

<details>
<summary>Preservation checks and historical sensitivity</summary>

[Cache-subset provenance](data/analysis/national_claims/full/cache_subset_provenance.json)
records exact claim/text-verified reuse of GTE, CAP and token-length caches.
[Source-preservation verification](data/analysis/national_claims/full/publication_source_validation.json)
checks unchanged originals, raw replies/history and archived labels.
[Topic-stage replay](data/analysis/national_claims/full/topics/replay_audit.json)
verifies current tables, named PNG figures and archive members without new inference.
The [earlier reproducibility audit](data/analysis/national_claims/reproducibility_audit.json)
is historical, not certification of the current corpus's hashes.

The separate [within-chunk sensitivity](data/analysis/national_claims/chunk_sensitivity/summary.json)
compares a frozen baseline, source-cleaned claims with existing weights, and the
same cleaned claims with equal mass per nonempty chunk. Targeted review excluded
235 claims (22 Democratic, 213 Republican); none of the 50 strongest similarity
pairs justified a semantic merge. Shared evidence and similar wording alone
do not establish duplication.

Chunk weighting changed displayed shares by at most 0.81 percentage points and
the sign of pairwise density contrasts at 3.1–4.5% of fixed query claims, not policy
positions. It remains a sensitivity, not the primary method. The current primary
retains bundle/claim weights; its net reduction of 414 claims from the 26,483
baseline reflects source-quality dispositions and exact-duplicate eligibility,
not accepted semantic merges.

The [complete sensitivity archive](data/analysis/national_claims/chunk_sensitivity/complete_sensitivity.zip)
preserves claims, sources, replies/history, reviews, weights, coordinates and
density scores. Its [validation manifest](data/analysis/national_claims/chunk_sensitivity/validation.json)
records 52 passing focused tests and exact 10D density replay; two pre-existing
plotting-test failures also reproduce in the untouched baseline.

</details>

## Reproduce

Use Python 3.12 or later and `uv`, from the repository root:

```bash
uv sync --frozen

# Reproduce the full eligible-claim comparison.
# Allow downloading pinned models on the first run.
uv run python -m dsa_analysis.national_claim_analysis --download-model
```

Omit `--download-model` once models are cached. Full extraction uses a separate
local MLX environment; follow the
[Gemma instructions](docs/national_claim_analysis.md#run-locally).
Full claim analysis refuses unfinished extraction. Source fetching is explicit,
not part of the default offline analysis.

```bash
uv run python -m unittest tests.test_national_claim_corpus tests.test_national_claim_analysis -q
```

<details>
<summary>Earlier analyses and deferred work</summary>

The [199-claim pilot](report/national_claim_analysis_sample.md) covers 25 documents;
it is neither representative nor the current dataset. Its
[claims and complete sources](data/analysis/national_claims/reviewed_sample/claim_documents.zip)
are retained. Reproduce it with:
`uv run python -m dsa_analysis.national_claim_analysis --reviewed-sample --download-model`.

The [passage-based baseline](report/national_platform_analysis.md) predates the
claim-based comparison. Its [complete source archive](data/analysis/national_platforms/source_documents.zip)
and [offline audit](data/analysis/national_platforms/reproducibility_audit.json)
remain separate. Reproduce it with:
`uv run dsa-analysis national-platform-analysis --download-model`.

The **Libertarian expansion is deferred**. Its partial extraction is preserved,
not included above; see the [four-party scope notes](docs/national_four_party_analysis.md).
The earlier [candidate and Democratic-primary study](docs/candidate_analysis.md)
is also separate from the national comparison.

</details>

## Repository guide

| Location | Contents |
|---|---|
| [`publication/`](publication/) | Ready-to-use Substack images by name and complete attention ratios |
| [`src/dsa_analysis/`](src/dsa_analysis/) | Extraction, corpus preparation, analysis and CLI |
| [`data/manual/`](data/manual/) | Curated source ledgers and qualifications |
| [`data/analysis/`](data/analysis/) | Complete texts, claims, provenance and result tables |
| [`report/`](report/) · [`figures/`](figures/) | Reports and charts, separated by analysis |
| [`docs/`](docs/) · [`tests/`](tests/) | Methods, reproduction guides and regression tests |
| [`files/research_archive/`](files/research_archive/) | Preserved legacy research captures and working artifacts |

Original authors and publishers retain their rights. GitHub hosts the research
artifacts; [The Margin of Error](https://www.themarginoferror.com/party-platforms/)
presents the live expanded analysis with interactive maps, source evidence,
attention-share ratios and observed-period timelines.
