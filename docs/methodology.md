# Methodology

## Research question

What do DSA and the Democratic Party officially say, and what issues distinguish
DSA-endorsed candidates from other Democrats in the same primaries?

## Scope

The study begins January 1, 2016 and uses a dated research cutoff. A “DSA candidate” is a
candidate officially endorsed by DSA National or a local DSA chapter. Membership or a
self-description alone is not sufficient.

The endorsement census seeks every identifiable federal, state, and local Democratic primary
endorsement nationwide. Because local archives are decentralized and may be deleted, results
must include the coverage ledger and must not claim unknowable absolute completeness.

The canonical denominator is endorsement-first. Verified manual endorsements and adjudicated
DSA National records seed races before any quotation or campaign-document evidence is attached.
National records are classified as Democratic primary, nonpartisan primary, general-only,
unopposed, ballot or party position, noncandidate, or source unavailable. Only dated Democratic
primaries enter the candidate-group comparison; exclusions remain in the reconciliation
table. This prevents quotation availability from silently determining which races exist.

National presidential endorsements are expanded into state and territory contests rather than
stored as one synthetic nationwide primary. `import-2016-presidential-primaries` and
`import-2020-presidential-primaries` ingest the official FEC election workbooks, retain every
certified Democratic ballot option in contests containing the endorsed candidate, and attach
the national DSA endorsement date to each resulting race.

## Source hierarchy

1. Adopted platforms, programs, resolutions, constitutions, and endorsement notices.
2. Official campaign policy pages, releases, speeches, debates, questionnaires, and interviews.
3. Archived posts from official organization or candidate accounts.
4. Third-party material used only for discovery, election metadata, or explicitly labeled
   context.

Every substantive position requires an exact quotation from levels 1–3. An endorsement does not
prove that a candidate adopts every DSA position.

## Comparison design

Party texts are compared within election cycles. DSA is not projected backward from later
documents, and the Democratic national platform is not treated as identical to every Democratic
candidate.

Primary sticking points have two separate measures:

- **Explicit conflict:** a candidate or another Democrat directly contrasts positions, attacks a policy,
  or rebuts the other in an official source.
- **Coded divergence:** reviewed primary-source passages support materially different policy
  instruments or scopes even without a direct attack.

Mention counts are descriptive, not proof of importance. Salience requires corroboration such as
prominent platform placement, repeated treatment, debate time, or direct contrast.

## Automated assistance

Scripts may retrieve documents, find candidate passages, transcribe media, and suggest topic
codes. A human reviewer must verify every excerpt used in the report against the original page,
PDF, audio, or video. Generated summaries are never evidence.

## Missing data

The dataset distinguishes `not_searched`, `searched_not_found`, `source_unavailable`,
`found_unverified`, and `verified`. No-position-found is not interpreted as opposition or support.
Candidate-level source research decisions are retained in
`data/manual/candidate_document_search_resolutions.csv`; verified sources are also added to
`candidate_documents.csv`. This keeps completed unsuccessful searches distinct from fetch or
extraction failures and prevents candidates without recovered text from disappearing silently.
## Reproducible lexical comparison

Run `uv run dsa-analysis analyze-text` after candidate and organizational full-document segment
corpora have been rebuilt.

The command creates two text comparisons:

1. official full-platform DSA segments versus Democratic Party platform segments; and
2. full-document DSA-endorsed candidate passages versus passages from other Democrats.

Eligible segments contain at least 20 tokens and exclude flagged boilerplate. Exact candidate
text is counted once per group and cycle, preventing shared national platforms from being
multiplied across state races while retaining every candidate, race, document, source, and
locator in the snapshot. TF-IDF uses document-normalized unigram frequencies and smoothed
inverse document frequency. MPIF uses weighted log-odds z-scores with an informative Dirichlet
prior over unigrams and adjacent bigrams.

Before scoring, common policy phrases are mapped to canonical features, including
`medicare_for_all`, `green_new_deal`, `single_payer`, `public_option`, `rent_control`,
`social_housing`, `living_wage`, `working_class`, and `small_business`. Common plural forms are
lightly lemmatized, and campaign boilerplate terms are excluded. The generated
`normalization_rules.csv` makes phrase mappings auditable. Document-prevalence results report the
share of candidate/election documents containing each feature as a robustness check against
repetition by a small number of campaigns. The difference figure requires an absolute prevalence
gap of at least 0.5 percentage points. Features common to both groups are reported separately in
the shared-emphasis table and paired-bar figure using the smaller of the two group prevalences;
shared mention is treated as agenda overlap, not automatically as policy agreement.

A stricter within-primary agreement signal requires both an endorsed candidate and another Democrat
to use the same concrete normalized mechanism phrase, such as `rent_control`,
`medicare_for_all`, or `public_option`. Mentions preceded by explicit oppositional or negating
language are excluded. This remains a high-precision language signal rather than a complete
stance classifier, so the generated table retains both exact excerpts for review.

Coverage shares use the registry-wide candidate/race denominator from
`data/processed/full_text_queue_summary.csv`. Candidate counts with `current_status=verified` are
treated as having extracted text; every other queue status remains in the denominator as without
extracted text.

These measures describe recoverable language. They do not infer positions from missing sources,
measure sincerity or policy quality, or prove that a lexical difference caused an election
outcome. Official MPIF input is restricted to generated organizational-context rows identified
as full platforms. DSA National and state/local DSA categories are grouped against DNC National
and state Democratic Party categories.

### Local-model topic classification

Topic emphasis follows the `state-politics` design:

- a published Comparative Agendas Project major-topic taxonomy in `config/cap_topics.json`;
- pinned `sentence-transformers/all-MiniLM-L6-v2` weights;
- local MPS execution when available, otherwise local CPU;
- normalized embeddings and nearest-topic cosine similarity;
- a 0.20 minimum-similarity threshold, with below-threshold rows explicitly unclassified;
- runner-up topic and margin retained for every row;
- a transparent seed-term keyword baseline;
- a retained schema marker that the legacy quotation-level reviewed-code crosswalk is not
  applicable to full-document segments.

No hosted model API is used. The model classifies the exact segment text in
`data/analysis/candidate_text_corpus.csv`; it does not generate replacement text or factual
claims. `data/analysis/model_topic_classifications.csv` retains exact text and aggregated
candidate, race, document, URL, and locator provenance beside every prediction and score.

Low-similarity and low-margin rows remain directly filterable.

## Full-document narrative corpus

Narrative analysis and the lexical/topic pipeline now derive from the same complete campaign
document collection, although they may apply different downstream eligibility and modeling
rules. Documents are stored with content-addressed raw provenance and deterministically
segmented; transcriptless audio/video and unscoped multi-candidate documents are excluded.

The comparison denominator is the canonical nationwide registry of tracked DSA-endorsed
Democratic primaries and every identified certified Democratic candidate. Candidate documents
remain separate from the organizational-context corpus, which contains DNC platforms, DSA
national programs or resolutions, state Democratic Party platforms, and official local DSA
electoral documents. State-cycle rows explicitly distinguish verified full platforms,
carry-forward documents, drafts or convention packets, searched-not-found results, and
non-platform electoral context.

Run the collection stages with:

```bash
uv run dsa-analysis build-race-registry
uv run dsa-analysis regather-candidate-documents
uv run dsa-analysis build-organizational-context
uv run dsa-analysis fetch-organizational-context
uv run dsa-analysis extract-organizational-context
uv run dsa-analysis audit-full-text
```

`audit-full-text` is a hard gate. Narrative clustering must not proceed while retryable candidate
searches remain or while paired-race, year, source-class, or imbalance checks fail.

## Narrative clustering and fingerprint

Analysis units are normalized full-document segments embedded with the pinned
`Alibaba-NLP/gte-multilingual-base` revision.
The cosine threshold is selected from human judgments at 0.55, 0.60, 0.65, 0.68, 0.70, 0.75,
and 0.80; no production threshold is selected before annotation. For the chosen threshold, the
pipeline constructs a cosine K-nearest-neighbor graph with `K=64`, runs weighted Leiden
RBConfiguration community detection at resolution 1.0, and retains communities with at least
four members. Cosine DP-Means at the same human-selected threshold is a robustness analysis.

Narrative lift and density comparisons use candidate/race-balanced weights because campaigns
contribute unequal text volumes. UMAP dimensions 2, 5, 10, 20, and 30 are compared using
trustworthiness before KDE dimensionality is fixed. Hot/cold-zone TF-IDF and NPMI characterize
the resulting density contrast; the two-dimensional projection is visualization only.
For interpretability, DSA-overrepresented, other-Democrat-overrepresented, and shared high-joint-density
points are grouped spatially within the visualization. Each displayed region is labeled with
locally distinctive terms, an extractive representative source passage, segment count, and
unique candidate count. These labels summarize underlying text and do not change the
higher-dimensional density calculation.
