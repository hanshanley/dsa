# Methodology

This analysis asks **what national Democratic, Republican, and DSA documents
talk about, and how their language differs**. It does not measure which
policies work, what voters believe, or how closely the organizations agree.

## 1. Collect national documents

The main comparison covers January 1, 2000 through October 26, 2026:

| Organization | Documents | Analyzed claims |
|---|---:|---:|
| Democratic Party | 7 | 11,811 |
| Republican Party | 6 | 9,150 |
| DSA | 122 | 5,108 |

Democratic and Republican inputs are national platforms. DSA inputs also
include official national resolutions and policy statements where platforms
are unavailable. Candidate campaigns, state parties, and local chapters
are outside this comparison.

The Republican Party's reuse of its 2016 platform in 2020 is not counted as
a new independent document. Drafts and uncertain adoption are not treated
as adopted policy. Historical gaps remain explicit, including the unrecovered
full final 2015 DSA strategy.

## 2. Turn the text into claims

A local Gemma model reads short source chunks and extracts standalone claims:
individual policies, assertions, or evaluations. A second pass checks the
claims against the same source. Claims retain their actors, qualifications,
dates, and supporting passages.

Targeted assistant reviews exclude identified errors and make source-bound
corrections where appropriate. Exact within-document duplicates are excluded
from analysis. Original claims, replies, evidence, and corrections are
preserved, including records that are not analyzed.

The final comparison uses **26,069 eligible claims**. Model checks and targeted
reviews are not independent human verification; unnoticed errors may remain.

## 3. Group related claims

GTE embeddings turn each claim into a numerical representation of its language.
Related claims are grouped into **24 shared topics**; their names and position
summaries are reviewed against actual source passages.

Charts display **21 substantive issues**. Three party-identity topics remain
in the data and all denominators, but are left out of issue rankings.
These clusters are an exploratory way to organize the text, not definitive
boundaries between policy areas.

## 4. Compare attention shares

An issue's **attention share** is its proportion of weighted claims.
Within each organization, each document or predefined DSA fallback-period
bundle receives equal total weight; claims share that weight equally.
This stops a longer document, or many short statements within one bundle,
from dominating simply because it supplies more claims.

For example, if an issue has a 10% DSA share and a 5% Democratic share,
the DSA/Democratic ratio is **2**. It receives twice the weighted attention
in the observed DSA documents. That does not mean twice the policy support.

The combined Democratic–Republican baseline is the average of their two
shares, giving each party equal weight. Ratios use unrounded shares;
a zero denominator is undefined, not an infinite reported ratio.

## 5. Map political language

UMAP supplies the two-dimensional display. Kernel density estimation (KDE)
compares where each organization's language is concentrated in a shared
higher-dimensional space. The displayed map is a projection, not the space
where density is measured.

**Map colors show relative language density; bars and ratios show attention
shares.** These are different quantities. Similar language can express
opposing policies, so closeness or overlapping density does not prove agreement.
The combined-party density uses an equal mixture of the Democratic and
Republican densities.

## 6. Check sensitivity and interpret cautiously

The main view includes eligible DSA resolutions and statements. A separate
adopted-platforms/programs-only view checks how source selection affects
results. It has only three DSA documents, and its separately fitted map
coordinates cannot be compared directly with the main map.

Timelines summarize documents in observed four-year periods, not annual
party positions. Missing observations remain gaps; the final period is partial.
Independently discovered period topics are separate from the shared taxonomy.

The corpus mixes dates and document types, and historical DSA coverage is
uneven. A low share is not proof of opposition or indifference. Source-backed
summaries describe the observed documents, not every member's beliefs or a
current consensus. The lead image's September 2026 examples illustrate current
national policies; its ratios still summarize the historical corpus.

## Read more

[Full technical methods and reproduction](docs/national_claim_analysis.md) ·
[National report](docs/reports/national_claim_analysis.md) ·
[Source ledger](data/manual/national_platform_sources.csv) ·
[Complete data and downloads](README.md#results-and-downloads).

The [DSA caucus comparison](docs/dsa_caucus_analysis.md) is a separate snapshot
with its own sources, topics, and denominators. The
[legacy candidate-study methodology](docs/methodology.md) concerns a different
research question and does not define this national comparison.
