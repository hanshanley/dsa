# National platforms: Democratic, Republican, and DSA

National organizational documents, January 1, 2000 through 2026-10-26. Candidate and state/local texts are excluded. This is a pooled comparison of recoverable language, not a continuous history of organizational positions.

![Source chronology](../figures/national_platforms/coverage.png)

## Corpus and sensitivity

| View | Status | Democratic documents / passages | Republican documents / passages | DSA documents / passages |
|---|---|---:|---:|---:|
| expanded | complete | 7 / 2333 | 6 / 2376 | 113 / 1410 |
| strict | complete | 7 / 2333 | 6 / 2376 | 3 / 309 |

The expanded view adds explicitly labeled DSA national statements/resolutions. The strict view uses adopted platforms/programs only. Each view fits its own balanced representation: map coordinates and numerical density scales are not directly comparable across views.

The strict and expanded results both retain the same underlying party-platform documents; only labeled fallback evidence differs. DSA's recovered platforms are from 2021 onward, not a representative sample of its entire 2000–2026 history. The complete adopted 2021 platform is preserved in an immutable December 30, 2021 archive snapshot, whose page metadata records publication and modification on November 9, 2021. It replaces the previously used API page modified in 2025; the versions are not counted as independent platforms.

| View | Balanced passages per organization | KDE dimensions | DSA source composition |
|---|---:|---:|---|
| expanded | 1410 | 5 | 1 platform, 2 program, 9 resolution, 101 statement |
| strict | 309 | 5 | 1 platform, 2 program |

The per-view `pairwise_summary.csv` records document/bundle-weighted density preferences. These fitted-sample diagnostics are not classifier accuracy, policy agreement rates, or directly comparable log-density scales. Smaller DSA corpora constrain both balanced fits. Sparse support and UMAP sampling make individual exploratory regions unstable; reviewed policy examples below are established from sources independently of those regions.

## Historical DSA recovery

Recovered national resolutions include the 2001 priorities and war/terrorism texts, the 2004 NPC resolution, the 2005 priorities, the November 2007 Economic Justice Agenda, the 2009 priorities, the complete 2013 priorities, and the 2017 priorities. The 2011 priorities and 2016 strategy publications explicitly identify themselves as summaries; their full underlying resolutions are not claimed recovered. Magazine issues remain complete in source downloads, while model scopes remove other authors' articles, contents, captions, fundraising and candidate-specific sections. Early scan OCR and print hyphenation are retained and can affect the semantic analysis.

| Fallback period bundle | Eligible documents | Model passages |
|---|---:|---:|
| 2000-2003 | 3 | 13 |
| 2004-2007 | 4 | 112 |
| 2008-2011 | 4 | 26 |
| 2012-2015 | 26 | 255 |
| 2016-2019 | 52 | 500 |
| 2020-2023 | 21 | 195 |

The full-text historical statement inventory contains 156 catalog records: 97 included as fallback evidence and 59 excluded with individual reasons. The rule retains nationally issued policy statements and broad policy agendas, but excludes campaign endorsements/results-only pieces, administration, personal tributes/case appeals, chapter authorship, unverified affiliated-body-only positions, link indexes and duplicate translations. Translations remain in complete downloads but do not double-count model passages. Twelve-month or four-year coverage is not inferred from a single document.

Bundles follow verified adoption periods where available and otherwise publication; December 2012 migration/republication dates are not original adoption dates. All six fallback period bundles meet the unchanged ten-passage gate, but this does not establish annual or comprehensive platform coverage. The 2000 editorial remains unverified, the 2003 priorities and full 2011/2015 underlying texts remain unrecovered, and no separate final 2025 platform is invented. The October 16, 2025 program-site snapshot describes the 2024 program; the December 2025 NPC newsletter confirms a program-development resolution/committee, not a recovered final new platform.

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
| democratic_vs_republican | shared_language | america, nation, people, country | 46 / 13 | `democratic-2008-0209`; scoped paragraph 261, chunk 2 |
| democratic_vs_republican | shared_language | drug, medicare, prescription, seniors | 39 / 11 | `democratic-2000-0164`; scoped paragraph 203, chunk 1 |
| democratic_vs_republican | democratic_relative | workers, americans, wealth, democrats | 25 / 6 | `democratic-2024-0030`; scoped paragraph 93, chunk 1 |
| democratic_vs_republican | democratic_relative | care, child, families, parents | 23 / 7 | `democratic-2024-0116`; scoped paragraph 192, chunk 1 |
| democratic_vs_republican | republican_relative | republican, republicans, american, military | 38 / 6 | `republican-2012-0282`; scoped paragraph 359, chunk 1 |
| democratic_vs_republican | republican_relative | cuba, cuban, support, family | 28 / 5 | `republican-2004-0233`; scoped paragraph 281, chunk 1 |
| democratic_vs_dsa | shared_language | voting, vote, rights, people | 29 / 8 | `democratic-2020-0276`; scoped paragraph 300, chunk 1 |
| democratic_vs_dsa | shared_language | health, care, coverage, healthcare | 20 / 7 | `dsa-2021-adopted-0216`; scoped paragraph 274, chunk 1 |
| democratic_vs_dsa | democratic_relative | american, world, america, global | 46 / 7 | `democratic-2016-0231`; scoped paragraph 279, chunk 1 |
| democratic_vs_dsa | democratic_relative | nuclear, weapons, treaty, materials | 35 / 7 | `democratic-2008-0133`; scoped paragraph 164, chunk 1 |
| democratic_vs_dsa | dsa_relative | workers, strike, dsa, members | 27 / 6 | `dsa-statement-4233-0005`; scoped paragraph 5, chunk 1 |
| democratic_vs_dsa | dsa_relative | dsa, rights, relationships, supports | 19 / 5 | `dsa-2011-lgbtq-0003`; scoped paragraph 4, chunk 1 |
| republican_vs_dsa | shared_language | voting, vote, voter, electoral | 32 / 11 | `republican-2008-0144`; scoped paragraph 203, chunk 1 |
| republican_vs_dsa | shared_language | banks, development, postal, service | 21 / 6 | `dsa-2021-adopted-0116`; scoped paragraph 158, chunk 1 |
| republican_vs_dsa | republican_relative | nato, united, states, europe | 42 / 6 | `republican-2024-0138`; scoped paragraph 211, chunk 1 |
| republican_vs_dsa | republican_relative | american, republican, republicans, america | 27 / 6 | `republican-2004-0151`; scoped paragraph 190, chunk 1 |
| republican_vs_dsa | dsa_relative | workers, strike, dsa, members | 27 / 6 | `dsa-statement-4233-0005`; scoped paragraph 5, chunk 1 |
| republican_vs_dsa | dsa_relative | dsa, rights, relationships, supports | 19 / 5 | `dsa-2011-lgbtq-0003`; scoped paragraph 4, chunk 1 |

Terms are descriptive TF-IDF labels, not independently reviewed policy categories. HDBSCAN regions require at least two independent document/period bundles; noise and retained-region counts are recorded in `clustering_audit.csv`. Shared regions must contain passages from both organizations. At most two regions per pairwise zone are shown. Source-linked short excerpts are in `regions.csv`; complete passage text is in `scored_passages.csv`.

## Document chronology

![Document language change](../figures/national_platforms/document_change.png)

Distances compare adjacent recovered document centroids within an organization in the original normalized GTE space, not on a left–right scale. Fallback statements and full platforms are different genres. Dates retain source precision; no annual interpolation is performed. First documents have no preceding observation. See each view's `document_chronology.csv`.

## Source qualifications

- **republican-2020-reuse**: reused_document. 2020 RNC resolution; applicability record only; no new independent platform text
- **dsa-2021-draft**: found_unverified. Explicit second draft excluded; complete adopted text separately recovered in immutable December 2021 official-page snapshot.
- **dsa-2025-program**: found_unverified. Retrieved PDF authors note says drafted April-June 2026; upload directory is NOT historical version evidence; excluded pending historical recovery; requested December 2025 Wayback PDF returned actual July 17 2026 snapshot, not historical 2025 evidence. October 16 2025 program-site snapshot still describes 2024 program. December 18 2025 NPC newsletter confirms R34 Workers Deserve More Forever and a program-development committee, not a recovered final new 2025 platform.
- **dsa-2000-election-lead**: found_unverified. Full magazine recovered; unsigned electoral editorial and quotation of a 1993 resolution do not establish a newly adopted 2000 policy document. Excluded rather than backdated; 2001 national resolutions cover this four-year fallback period.

Empty years in `year_coverage.csv` mean no recovered publication in this inventory, not that an organization had no platform or position. The GOP 2020 reuse record contributes no second independent copy of its 2016 text. Every currently exposed official statement-catalog entry from December 2012 through December 2020 was screened, with full included and excluded text preserved. This does not recover deleted pages or establish exhaustive coverage of other publication types or all historical years. See the source ledger, full-text historical statement inventory, fetch-attempt log, and `data/manual/national_platform_search_disposition.csv` for period-specific searches and explicit unsearched boundaries.

## Methods and reproduction

GTE: `Alibaba-NLP/gte-multilingual-base` at `9bbca17d9273fd0d03d5725c7a4b0f6b45142062`, normalized embeddings; maximum 256 tokens including special tokens. Long paragraphs are split on original character offsets; short fragments, page markers, and known magazine footers are excluded from model passages. Complete source extraction and exact scoped article text remain separately downloadable.

UMAP uses deterministic, equal-sized organization samples stratified by document or predefined four-year DSA fallback bundle. KDE gives each sampled document/bundle equal total weight within its organization. Bundles need at least ten passages. Both sampling and weighting use the same units. The dimension sweep selects the smallest dimension within 0.005 trustworthiness of the maximum; KDE uses standardized selected-dimensional coordinates and Scott bandwidth. The 2D map is display-only; sparse corpora produce explicit insufficient-evidence results.

```sh
uv run dsa-analysis national-platform-analysis --fetch
uv run dsa-analysis national-platform-analysis
```

Collection is explicit; the default command uses local captures (or hash-verified complete-text exports when captures are absent) and a cached model only. `--download-model` explicitly permits obtaining the pinned model. `--fetch-only` collects without running the model. No candidate pipeline runs.

All outputs: `data/analysis/national_platforms/`. Downloads include `complete_sources.csv` and `.jsonl` (complete extracted and scoped texts), `passages.csv` (full model passages, not metadata alone), `coverage.csv`, `year_coverage.csv`, `historical_statement_inventory.csv` and `.jsonl` (complete text and screening reasons for every catalog entry), and the expanded/strict analysis tables. Sources retain their original attribution and rights; institutional reproductions are labeled as such rather than represented as party-hosted originals.
