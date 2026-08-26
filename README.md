<div align="center">
  <h1>DSA and Democratic Primary Discourse</h1>
  <p><strong>A source-first national comparison of campaigns, platforms, and policy language since 2016.</strong></p>
  <p>
    <a href="#what-the-campaigns-emphasize">Findings</a> ·
    <a href="#semantic-map">Semantic map</a> ·
    <a href="#data-and-coverage">Data</a> ·
    <a href="#methods">Methods</a> ·
    <a href="#reproduce-the-analysis">Reproduce</a>
  </p>
</div>

---

## What this project asks

How do DSA-endorsed candidates describe politics differently from other Democrats in the same
primaries—and where do they speak in similar terms?

This repository builds an auditable national dataset of DSA endorsements, reconstructs the
corresponding Democratic-primary fields, collects exact campaign and organizational text, and
compares the resulting language. Sources include campaign platforms, policy pages,
questionnaires, debates, interviews, speeches, press releases, archived websites, and official
DSA and Democratic Party platforms.

The analysis measures **emphasis and language**, not ideology by assumption. Missing evidence is
recorded as missing; it is never interpreted as a candidate holding no position.

## Semantic map

<p align="center">
  <img src="figures/provisional_gte_kde.png" width="1200" alt="Semantic map comparing DSA-endorsed candidates and other Democrats">
</p>

The map embeds **36,650 deduplicated campaign-text passages** with
[`Alibaba-NLP/gte-multilingual-base`](https://huggingface.co/Alibaba-NLP/gte-multilingual-base).
Nearby points contain semantically similar language. Red regions are denser among DSA-endorsed
candidate texts, blue regions among other Democrats, and gold regions are common to both groups.

The strongest recurring distinctions are:

- **DSA-overrepresented:** socialist and movement-building language; climate and renewable
  energy; tenants and eviction; labor and wages; Palestine/Israel; and universal health care.
- **Other-Democrat-overrepresented:** California education; agriculture and land preservation;
  transit and bicycle infrastructure; housing development; and waste and recycling.
- **Shared high-density language:** education and candidate experience; immigration and the
  border; zoning and development; legal experience; taxes and revenue; and political leadership.

The cards use source-attributed passages selected for both topical relevance and proximity to
each region's semantic center. The two-dimensional projection is for visualization; density is
estimated in the selected 10-dimensional representation.
The [complete semantic-region table](data/analysis/provisional_gte_kde/density_regions.csv)
lists up to six HDBSCAN regions per category and marks the two shown on the map. HDBSCAN runs
on the selected 10-dimensional UMAP representation; unclustered points remain explicit noise.

## What the campaigns emphasize

<p align="center">
  <img src="outputs/figures/text_analysis/policy_language_difference.svg" width="1100" alt="Comparison of policy-language prevalence in DSA-endorsed and other Democratic campaign documents">
</p>

The clearest language pattern is not simply “left versus moderate.” DSA-endorsed campaigns more
often foreground **rights, class, workers, unions, tenants, rent, and universal public
programs**. Other Democrats more often foreground **business, small business, technology, markets,
training, and administrative delivery**.

These are document-level mention rates. A term appearing more often indicates greater emphasis,
not necessarily endorsement.

## Where the agendas overlap

<p align="center">
  <img src="outputs/figures/text_analysis/policy_language_overlap.svg" width="1050" alt="Issues discussed by both DSA-endorsed candidates and other Democrats">
</p>

Both groups devote substantial attention to health care, workers, business, affordable housing,
unions, training, climate change, and rent. Shared attention does not establish agreement:
candidates may diagnose the same problem while proposing different mechanisms.

The stricter comparison below counts primaries where both sides affirmatively use the same
concrete policy phrase.

<p align="center">
  <img src="outputs/figures/text_analysis/shared_affirmative_policy_mechanisms.svg" width="980" alt="Shared affirmative policy mechanisms within Democratic primaries">
</p>

Affordable housing is the most common shared mechanism language, followed by minimum wage,
Green New Deal, public housing, Medicare for All, single payer, and rent control. Negated or
explicitly oppositional mentions are excluded; exact paired passages remain available for
review.

## Official platforms

Candidate rhetoric is analyzed separately from organizational platforms. The official corpus
contains DSA national and state/local programs alongside DNC and state Democratic Party
platforms. The current analysis contains **6 DSA documents (328 passages)** and **38 Democratic
documents (5,320 passages)** after excluding sources whose current verification status is not
usable. The imbalance is handled two ways: document prevalence gives each platform one
observation per feature, while the semantic fingerprint fits UMAP and KDE to equal-size,
round-robin document-balanced samples from each group.

By category, the analyzed set contains 3 DSA national documents, 3 DSA state/local documents,
3 DNC national platforms, and 35 state Democratic Party platforms. The coverage ledger retains
154 explicit platform gaps; these remain missing data rather than evidence of organizational
silence.

<p align="center">
  <img src="figures/official_platform_gte_kde.png" width="1100" alt="Document-balanced semantic density map of official DSA and Democratic platforms">
</p>

The selected five-dimensional representation separates a recurring DSA region about collective
power and transformational social change from a Democratic-platform region centered on students,
affordability, infrastructure, and environmental administration. A shared high-density region
contains health, service, family, and worker language. The document-prevalence result separately
shows the strongest DSA-side differences for social housing, working-class, tenant, Green New
Deal, and Medicare for All language. These are relative emphasis patterns in the recoverable
corpus, not evidence that every organization or candidate holds the same position.

<p align="center">
  <img src="outputs/figures/text_analysis/official_platform_document_prevalence.svg" width="1050" alt="Document-level policy language prevalence in official DSA and Democratic platforms">
</p>

| DSA / DSA-endorsed emphasis | Democratic platform / other-Democrat emphasis |
| --- | --- |
| Housing as a right; tenants; rent control; social and public housing | Housing supply, development, and administrative delivery |
| Single payer and Medicare for All | Public-option and incremental coverage mechanisms |
| Living wages, unions, workers, and collective power | Training, pathways, small business, and labor-market opportunity |
| Movement-building and working-class political power | Governing competence, coalition breadth, and institutional implementation |
| Collective or public ownership and decommodification | Regulated, competitive capitalism |

<p align="center">
  <img src="outputs/figures/text_analysis/official_policy_contrasts.svg" width="1050" alt="Reviewed contrasts between official DSA and Democratic Party policy language">
</p>

## Data and coverage

| Corpus component | Current coverage |
| --- | ---: |
| Strict in-scope Democratic or Minnesota DFL primaries | **421** |
| Races with substantive campaign text on both sides | **268** |
| Candidates with substantive text | **942** |
| Substantive candidate documents | **1,585** |
| Eligible source passages | **39,310** |
| Deduplicated candidate analysis documents | **1,341** |
| Deduplicated candidate analysis passages | **38,207** |
| Organizational documents successfully extracted | **93 / 93** |
| Full organizational platforms in lexical analysis | **44** (**6 DSA; 38 Democratic**) |

The corpus spans 2016–2026. It is broad enough for descriptive analysis of the recovered
materials, but it is **not a claim of complete nationwide text coverage**. The audit retains
891 retryable candidate-source gaps, and 19 other-Democrat records still lack verified first-party
evidence. See [`docs/completeness.md`](docs/completeness.md) for the completion criteria and
[`data/processed/full_text_audit_summary.json`](data/processed/full_text_audit_summary.json) for
the machine-readable audit.

## Evidence standard

Substantive findings must trace to exact text from official organizations, campaigns, debates,
interviews, or attributable candidate responses. Journalism and search results may locate
sources but do not substitute for primary evidence.

Every analyzed passage retains its candidate, race, document, URL, source type, date, and
locator. `source_unavailable`, `searched_not_found`, and unresolved records remain explicit
unknowns.

## Methods

### Document-level language

Policy phrases are normalized before counting. Each feature is measured as the share of
candidate-election documents containing that phrase, preventing a campaign that repeats one
term many times from dominating the comparison.

### Semantic density

Eligible passages are embedded with the pinned multilingual GTE model and L2-normalized.
Dimensionality is selected by a trustworthiness sweep; KDE is estimated in 10 dimensions with
candidate-balanced fitting and Scott's bandwidth rule. UMAP is used only for the two-dimensional
display.

Official platforms use a separate five-dimensional sweep result. Both the UMAP manifold and KDE
are fit on **328 passages per group**, sampled deterministically in round-robin order across
documents. This prevents the larger Democratic passage inventory from mechanically determining
the geometry or density estimates, but it cannot replace missing DSA state/local platforms or
erase the 6-versus-38 document-coverage limitation.

### Agreement and disagreement

- **Overlap** identifies issues discussed by both groups.
- **Shared affirmative mechanisms** require both sides in the same primary to use the same
  concrete mechanism phrase without local negation.
- **Explicit conflicts** are direct, source-supported candidate contrasts; analyst-coded
  divergences are kept separate.

Full details are in [`docs/methodology.md`](docs/methodology.md), with field definitions in
[`docs/data_dictionary.md`](docs/data_dictionary.md).

## Key outputs

- [`data/analysis/candidate_text_corpus.csv`](data/analysis/candidate_text_corpus.csv) — exact
  deduplicated candidate passages with full provenance
- [`data/analysis/provisional_gte_kde/density_regions.csv`](data/analysis/provisional_gte_kde/density_regions.csv)
  — all substantive semantic regions (up to six per category), terms, counts, representative
  evidence, and an indicator for the two per category displayed on the map
- [`outputs/tables/text_analysis/candidate_feature_prevalence.csv`](outputs/tables/text_analysis/candidate_feature_prevalence.csv)
  — document-level phrase prevalence by candidate group
- [`outputs/tables/text_analysis/official_platform_document_prevalence.csv`](outputs/tables/text_analysis/official_platform_document_prevalence.csv)
  — document-balanced policy-feature prevalence across official DSA and Democratic platforms
- [`data/analysis/official_platform_gte_kde/density_regions.csv`](data/analysis/official_platform_gte_kde/density_regions.csv)
  — HDBSCAN regions underlying the balanced official-platform KDE map
- [`report/official_platform_kde_analysis.md`](report/official_platform_kde_analysis.md)
  — official-platform KDE dimensions, balancing, region table, and limitations
- [`outputs/tables/text_analysis/shared_affirmative_policy_mechanisms.csv`](outputs/tables/text_analysis/shared_affirmative_policy_mechanisms.csv)
  — exact paired evidence for shared mechanisms
- [`report/text_analysis.md`](report/text_analysis.md) — lexical, overlap, and agreement analysis
- [`report/provisional_kde_analysis.md`](report/provisional_kde_analysis.md) — region-by-region
  semantic interpretation
- [`report/draft.md`](report/draft.md) — generated canonical research report

## Reproduce the analysis

The project requires Python 3.12 and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/hanshanley/dsa.git
cd dsa
uv sync
uv run dsa-analysis validate
uv run dsa-analysis provisional-kde
uv run dsa-analysis analyze-text
uv run dsa-analysis classify-topics
uv run dsa-analysis analyze-text
uv run dsa-analysis analyze
```

Run the full test suite with:

```bash
uv run python -m unittest discover -s tests
```

## Repository guide

- `src/dsa_analysis/` — collection, extraction, audit, and analysis code
- `data/manual/` — reviewed source registrations and adjudications
- `data/processed/` — generated corpora, coverage queues, and audit outputs
- `data/analysis/` — analysis-ready snapshots and model outputs
- `outputs/` — reproducible tables and SVG figures
- `figures/` — semantic-density visualization
- `docs/` — methodology, codebook, completeness criteria, and data dictionary
- `tests/` — regression and validation tests
