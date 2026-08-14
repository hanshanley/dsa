# Democratic Socialists of America (DSA) positions and Democratic Party Positions Contrast

This project is a source-first study of what the Democratic Socialists of America, the
Democratic Party, and candidates in Democratic primaries have said since 2016.

It builds an auditable national dataset of DSA endorsements, identifies the other candidates in
those primaries, collects exact passages from first-party sources, and analyzes where their
positions align or diverge. The resulting data supports a report on the policy and strategic
differences between DSA, Democratic Party platforms, DSA-endorsed candidates, and their primary
opponents.

## At a glance: where the language differs

The completed, strictly validated census contains **2,640 chapter-years**, **1,254 endorsed
candidacies**, **3,518 official roster rows**, **7,350 exact evidence rows**, and **1,388
source-supported candidate/opponent contrasts**.

| DSA / DSA-endorsed emphasis | Democratic platform / opponent emphasis |
| --- | --- |
| Housing as a right; tenants; rent control; social and public housing | Business, opportunity, market mechanisms, and administrative delivery |
| Single-payer and Medicare for All | Public-option and incremental coverage mechanisms |
| Living wages, unions, workers, and collective power | Training, pathways, small business, and labor-market opportunity |
| Movement-building and working-class political power | Governing competence, coalition breadth, and institutional implementation |
| Collective/public ownership and decommodification | Regulated, competitive capitalism |

![Difference in DSA-endorsed and Democratic-opponent policy language](outputs/figures/text_analysis/policy_language_difference.svg)

The graph above compares the share of candidate/election documents containing each normalized
policy feature. Red features appear in more DSA-endorsed candidate documents; blue features
appear in more Democratic opponent documents. See the
[full text-analysis report](report/text_analysis.md) for methods, issue emphasis, similarity,
sticking points, evidence coverage, and limitations.

### Data behind the graphs

- [`data/analysis/candidate_text_corpus.csv`](data/analysis/candidate_text_corpus.csv) contains
  the exact candidate quote, candidate, election date, endorsed/opponent role, source URL, source
  type, locator, and evidence status used by the analysis.
- [`data/analysis/model_topic_classifications.csv`](data/analysis/model_topic_classifications.csv)
  retains every exact quote and source URL alongside the local model topic, cosine similarity,
  runner-up topic, margin, and keyword-baseline result.
- [`data/analysis/primary_sticking_points.csv`](data/analysis/primary_sticking_points.csv)
  contains the deduplicated candidate/opponent contrasts used in the issue and cycle graphs.
- [`config/cap_topics.json`](config/cap_topics.json) defines the published Comparative Agendas
  Project topic scheme embedded by the pinned local model.
- [`data/analysis/model_topic_validation.json`](data/analysis/model_topic_validation.json)
  reports thresholding, low-margin rows, keyword agreement, and reviewed-code crosswalk
  agreement.

The model never invents replacement text. It classifies the exact quotation retained in the same
row. For each model topic:

```text
topic share = locally classified exact quotations in topic / all classified quotations
topic difference = DSA-endorsed share - Democratic-opponent share
```

## What the project does

- Collects current and historical endorsements from DSA National and local chapters.
- Tracks which chapter-year records have been searched so gaps are explicit rather than silently
  treated as no endorsements.
- Reconstructs Democratic primary ballot rosters for endorsed candidates.
- Collects exact candidate and opponent statements from official pages, documents, interviews,
  debates, and archived sources.
- Compares DSA and Democratic Party texts within the election cycle in which they were published.
- Separates direct, explicit conflicts from analyst-coded policy divergences.
- Validates provenance, source status, review state, and coding before generating tables and a
  draft report.

## Evidence standard

Substantive findings must be supported by exact quotations from official organizational or
campaign sources. Journalism, search results, and third-party trackers can help locate evidence,
but they do not substantiate a claim on their own.

Automated tools may retrieve pages, discover leads, and suggest structured data. A human reviewer
must verify every excerpt used in the report against the original page, PDF, audio, or video.
Missing evidence is recorded with statuses such as `not_searched`, `searched_not_found`,
`source_unavailable`, and `found_unverified`; absence of a statement is not interpreted as a
position.

## Outputs

- `data/manual/` contains reviewed source metadata, excerpts, endorsements, race rosters, and
  coded contrasts.
- `data/processed/` contains collection results, research queues, coverage ledgers, verified
  endorsements, and the SQLite research database.
- `outputs/tables/` contains generated analysis tables.
- `outputs/figures/text_analysis/` contains reproducible SVG text-analysis graphs.
- `outputs/tables/text_analysis/` contains TF-IDF, MPIF, similarity, topic, cycle, and manifest
  tables used by those figures.
- `report/draft.md` contains the generated research report and current dataset status.
- `report/text_analysis.md` explains the graph methods and summarizes the principal lexical
  findings.

## Repository guide

- `src/dsa_analysis/` — collection, crawling, adjudication, validation, and analysis code
- `config/` — source registry and policy taxonomy
- `files/research_archive/` — downloaded top-level JSON/HTML research captures retained for
  reproducibility without cluttering the repository root
- `docs/methodology.md` — research design and source hierarchy
- `docs/codebook.md` — coding rules
- `docs/data_dictionary.md` — dataset fields
- `docs/completeness.md` — coverage and completion criteria
- `tests/` — validation and analysis tests

## Running the project

The project requires Python 3.12 and uses `uv` for its development environment. The main entry
point is `dsa-analysis`; run `uv run dsa-analysis --help` to see the collection and research
commands.

To rebuild the reviewed data and report:

```bash
uv run dsa-analysis init-db
uv run dsa-analysis validate
uv run dsa-analysis analyze
uv run dsa-analysis analyze-text
```

`analyze-text` runs the pinned local `sentence-transformers/all-MiniLM-L6-v2` model; no hosted
model API is used. It compares:

- reviewed official DSA excerpts with reviewed Democratic Party platform excerpts; and
- verified statements by DSA-endorsed candidates with verified statements by their Democratic
  primary opponents.

It generates mean TF-IDF, weighted log-odds most-informative-feature (MPIF) scores, topic shares,
document-level feature prevalence, within-topic cosine similarity, evidence coverage, and
sticking-point counts by topic and cycle. Policy phrases such as `Medicare for All`,
`rent control`, and `public option` are normalized before scoring. Common plural variants are
lightly lemmatized. Identical candidate quotes repeated through multiple endorsement queues are
deduplicated by candidate and election. The generated `analysis_manifest.json` records input
hashes and method parameters.

## Text-analysis graph gallery

The figures use one consistent publication palette throughout: DSA red for endorsed/DSA text,
Democratic blue for opponent/DNC text, charcoal labels, and a warm neutral background.

### Policy language

![Difference in policy language](outputs/figures/text_analysis/policy_language_difference.svg)

### Official DSA and Democratic Party language

![Official policy mechanism contrasts](outputs/figures/text_analysis/official_policy_contrasts.svg)

### Local-model policy emphasis

![Local-model policy emphasis difference](outputs/figures/text_analysis/model_topic_emphasis_difference.svg)

### Direct evidence and explicit conflicts

![Verified evidence by cycle](outputs/figures/text_analysis/verified_evidence_by_cycle.svg)

![Explicit conflicts by cycle](outputs/figures/text_analysis/explicit_conflicts_by_cycle.svg)

![Source type difference](outputs/figures/text_analysis/source_type_difference.svg)

Run the test suite with:

```bash
uv run python -m unittest discover -s tests
```
