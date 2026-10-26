# National platforms: Democratic, Republican, and DSA

National organizational documents, January 1, 2000 through 2026-10-26. Candidate and state/local texts are excluded. This is a pooled comparison of recoverable language, not a continuous history of organizational positions.

![Source chronology](../figures/national_platforms/coverage.png)

## Corpus and sensitivity

| View | Status | Democratic documents / passages | Republican documents / passages | DSA documents / passages |
|---|---|---:|---:|---:|
| expanded | complete | 7 / 2333 | 6 / 2376 | 7 / 352 |
| strict | complete | 7 / 2333 | 6 / 2376 | 3 / 311 |

The expanded view adds explicitly labeled DSA national statements/resolutions. The strict view uses adopted platforms/programs only. Each view fits its own balanced representation: map coordinates and numerical density scales are not directly comparable across views.

The strict and expanded results both retain the same underlying party-platform documents; only labeled fallback evidence differs. DSA's recovered platforms are from 2021 onward, not a representative sample of its entire 2000–2026 history. The recovered 2021 platform page was last modified in April 2025: its publication, adoption, and version dates are separate fields, and earlier cutoffs exclude that later page version.

| View | Balanced passages per organization | KDE dimensions | DSA source composition |
|---|---:|---:|---|
| expanded | 352 | 5 | 1 platform, 2 program, 1 resolution, 3 statement |
| strict | 311 | 5 | 1 platform, 2 program |

The per-view `pairwise_summary.csv` records document/bundle-weighted density preferences. These fitted-sample diagnostics are not classifier accuracy, policy agreement rates, or directly comparable log-density scales. Smaller DSA corpora constrain both balanced fits. Sparse support and UMAP sampling make individual exploratory regions unstable; reviewed policy examples below are established from sources independently of those regions.

## Reviewed policy examples (2024)

These matched-cycle examples distinguish common policy subjects from different proposed mechanisms. They come directly from available 2024 documents, not from KDE labels or a presumed ideological ordering.

| Topic | Democratic | Republican | DSA |
|---|---|---|---|
| Healthcare | Make expanded ACA premium tax credits permanent. | Promote healthcare choice and competition while protecting Medicare. | Medicare for All without premiums or cost-sharing. |
| Energy | Incentivize clean-energy and grid investment. | Remove restrictions on oil and gas and coal production. | Publicly own major energy infrastructure alongside a fossil-fuel transition. |
| Immigration | Combine border enforcement with citizenship pathways for Dreamers and others. | Expand deportation to a historically large operation. | End immigrant detention and deportations and provide immediate amnesty regardless of status. |

The reviewed findings ledger records the source document identifier and an exact supporting span for every recovered cell and the report builder checks each against the complete source text. These examples do not imply that a document lacks other relevant proposals.

## Pooled semantic comparison

![Pairwise density](../figures/national_platforms/pairwise_density.png)

All three densities share one representation within each view. Positive log ratios favor the first organization in a panel; negative ratios favor the second. Shared language does not establish shared policy or agreement. Different decades and genres are pooled; historical composition can drive apparent distinctions.

### Exploratory regions

| Comparison | Relative-language zone | Terms | Passages / documents | Source evidence |
|---|---|---|---:|---|
| democratic_vs_republican | shared_language | schools, students, school, education | 31 / 12 | `republican-2004-0431`; scoped paragraph 513, chunk 1 |
| democratic_vs_republican | shared_language | energy, oil, gas, american | 29 / 11 | `republican-2016-0183`; scoped paragraph 229, chunk 1 |
| democratic_vs_republican | democratic_relative | housing, workers, care, people | 41 / 7 | `democratic-2016-0119`; scoped paragraph 141, chunk 1 |
| democratic_vs_republican | democratic_relative | global, economic, africa, work | 23 / 6 | `democratic-2020-0442`; scoped paragraph 495, chunk 1 |
| democratic_vs_republican | republican_relative | education, support, republicans, schools | 21 / 6 | `republican-2024-0095`; scoped paragraph 146, chunk 1 |
| democratic_vs_republican | republican_relative | tax, code, rates, federal | 21 / 5 | `republican-2000-0041`; scoped paragraph 53, chunk 1 |
| democratic_vs_dsa | shared_language | health, care, coverage, affordable | 25 / 5 | `dsa-2021-adopted-0214`; scoped paragraph 271, chunk 1 |
| democratic_vs_dsa | shared_language | israel, president, state, security | 24 / 8 | `democratic-2004-0064`; scoped paragraph 68, chunk 1 |
| democratic_vs_dsa | democratic_relative | president, trump, biden, america | 55 / 3 | `democratic-2020-0354`; scoped paragraph 389, chunk 1 |
| democratic_vs_dsa | democratic_relative | veterans, military, families, care | 29 / 7 | `democratic-2024-0424`; scoped paragraph 532, chunk 1 |
| democratic_vs_dsa | dsa_relative | dsa, rights, lgbtq, advocates | 13 / 4 | `dsa-2012-fiscal-0005`; scoped paragraph 5, chunk 1 |
| democratic_vs_dsa | dsa_relative | end, war, sanctions, military | 8 / 3 | `dsa-2021-adopted-0259`; scoped paragraph 323, chunk 1 |
| republican_vs_dsa | shared_language | tax, income, credit, code | 32 / 5 | `republican-2012-0034`; scoped paragraph 56, chunk 1 |
| republican_vs_dsa | shared_language | end, justice, criminal, prison | 20 / 6 | `republican-2012-0253`; scoped paragraph 324, chunk 1 |
| republican_vs_dsa | republican_relative | veterans, military, care, service | 42 / 5 | `republican-2016-0334`; scoped paragraph 407, chunk 1 |
| republican_vs_dsa | republican_relative | education, support, republicans, schools | 29 / 5 | `republican-2004-0586`; scoped paragraph 722, chunk 1 |
| republican_vs_dsa | dsa_relative | dsa, rights, lgbtq, advocates | 12 / 4 | `dsa-2012-fiscal-0005`; scoped paragraph 5, chunk 1 |
| republican_vs_dsa | dsa_relative | end, gaza, palestinian, military | 9 / 4 | `dsa-2021-adopted-0277`; scoped paragraph 345, chunk 1 |

Terms are descriptive TF-IDF labels, not independently reviewed policy categories. HDBSCAN regions require at least two independent document/period bundles; noise and retained-region counts are recorded in `clustering_audit.csv`. Shared regions must contain passages from both organizations. At most two regions per pairwise zone are shown. Source-linked short excerpts are in `regions.csv`; complete passage text is in `scored_passages.csv`.

## Document chronology

![Document language change](../figures/national_platforms/document_change.png)

Distances compare adjacent recovered document centroids within an organization in the original normalized GTE space, not on a left–right scale. Fallback statements and full platforms are different genres. Dates retain source precision; no annual interpolation is performed. First documents have no preceding observation. See each view's `document_chronology.csv`.

## Source qualifications

- **republican-2020-reuse**: reused_document. 2020 RNC resolution; applicability record only; no new independent platform text
- **dsa-2021-draft**: found_unverified. Explicit second draft excluded; adopted text separately recovered from official WordPress page API
- **dsa-2025-program**: found_unverified. Retrieved PDF authors note says drafted April-June 2026; upload directory is NOT historical version evidence; excluded pending historical recovery
- **dsa-2000-election-lead**: found_unverified. Official magazine archive; recover and scope institutional statement separately from individual-authored articles
- **dsa-2005-katrina-lead**: sparse_bundle. Complete institutional statement on PDF pages 12-13; fundraising postscript excluded; OCR and print hyphenation retained

Empty years in `year_coverage.csv` mean no recovered publication in this inventory, not that an organization had no platform or position. The GOP 2020 reuse record contributes no second independent copy of its 2016 text. DSA fallback recovery is selective rather than exhaustive, and many historical years remain uncovered. See the source ledger, fetch-attempt log, and `data/manual/national_platform_search_disposition.csv` for period-specific searches and explicit unsearched boundaries.

## Methods and reproduction

GTE: `Alibaba-NLP/gte-multilingual-base` at `9bbca17d9273fd0d03d5725c7a4b0f6b45142062`, normalized embeddings; maximum 256 tokens including special tokens. Long paragraphs are split on original character offsets; short fragments, page markers, and known magazine footers are excluded from model passages. Complete source extraction and exact scoped article text remain separately downloadable.

UMAP uses deterministic, equal-sized organization samples stratified by document or predefined four-year DSA fallback bundle. KDE gives each sampled document/bundle equal total weight within its organization. Bundles need at least ten passages. Both sampling and weighting use the same units. The dimension sweep selects the smallest dimension within 0.005 trustworthiness of the maximum; KDE uses standardized selected-dimensional coordinates and Scott bandwidth. The 2D map is display-only; sparse corpora produce explicit insufficient-evidence results.

```sh
uv run dsa-analysis national-platform-analysis --fetch
uv run dsa-analysis national-platform-analysis
```

Collection is explicit; the default command uses local captures (or hash-verified complete-text exports when captures are absent) and a cached model only. `--download-model` explicitly permits obtaining the pinned model. `--fetch-only` collects without running the model. No candidate pipeline runs.

All outputs: `data/analysis/national_platforms/`. Downloads include `complete_sources.csv` and `.jsonl` (complete extracted and scoped texts), `passages.csv` (full model passages, not metadata alone), `coverage.csv`, `year_coverage.csv`, and the expanded/strict analysis tables. Sources retain their original attribution and rights; institutional reproductions are labeled as such rather than represented as party-hosted originals.
