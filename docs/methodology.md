# Methodology

## Research question

What do DSA and the Democratic Party officially say, and what issues distinguish
DSA-endorsed candidates from their opponents in Democratic primaries?

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
primaries enter the candidate-versus-opponent analysis; exclusions remain in the reconciliation
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

- **Explicit conflict:** a candidate or opponent directly contrasts positions, attacks a policy,
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

Run `uv run dsa-analysis analyze-text` after the reviewed evidence and sticking-point datasets
have been rebuilt.

The command creates two text comparisons:

1. official DSA statements versus Democratic National Committee platform excerpts; and
2. DSA-endorsed candidate statements versus statements by Democratic primary opponents.

Candidate quotations duplicated because multiple DSA bodies endorsed the same candidate in the
same election are counted once. TF-IDF uses document-normalized unigram frequencies and smoothed
inverse document frequency. MPIF uses weighted log-odds z-scores with an informative Dirichlet
prior over unigrams and adjacent bigrams.

Before scoring, common policy phrases are mapped to canonical features, including
`medicare_for_all`, `green_new_deal`, `single_payer`, `public_option`, `rent_control`,
`social_housing`, `living_wage`, `working_class`, and `small_business`. Common plural forms are
lightly lemmatized, and campaign boilerplate terms are excluded. The generated
`normalization_rules.csv` makes phrase mappings auditable. Document-prevalence results report the
share of candidate/election documents containing each feature as a robustness check against
repetition by a small number of campaigns.

These measures describe recoverable language. They do not infer positions from missing sources,
measure sincerity or policy quality, or prove that a lexical difference caused an election
outcome. The official DSA/DNC corpus is intentionally limited to manually reviewed exact
excerpts, so its MPIF results should be read as descriptive rather than exhaustive.

### Local-model topic classification

Topic emphasis follows the `state-politics` design:

- a published Comparative Agendas Project major-topic taxonomy in `config/cap_topics.json`;
- pinned `sentence-transformers/all-MiniLM-L6-v2` weights;
- local MPS execution when available, otherwise local CPU;
- normalized embeddings and nearest-topic cosine similarity;
- a 0.20 minimum-similarity threshold, with below-threshold rows explicitly unclassified;
- runner-up topic and margin retained for every row;
- a transparent seed-term keyword baseline;
- diagnostic agreement against the existing reviewed-code crosswalk.

No hosted model API is used. The model classifies the exact quotation in
`data/analysis/candidate_text_corpus.csv`; it does not generate replacement text or factual
claims. `data/analysis/model_topic_classifications.csv` retains the exact quotation and source URL
beside every prediction, score, runner-up and margin.

The crosswalk agreement is a diagnostic rather than an independent gold-standard accuracy
estimate. Low-similarity and low-margin rows remain directly filterable.

## Full-document narrative corpus

Narrative analysis does not use `candidate_text_corpus.csv` as its input. That file is a
quotation-level evidence snapshot. The narrative corpus instead collects complete campaign
policy pages, platforms, releases, speeches, interviews, questionnaires, voter guides, and
publisher-provided transcripts within each primary's campaign window. Documents are stored with
content-addressed raw provenance and deterministically segmented; transcriptless audio/video and
unscoped multi-candidate documents are excluded from analysis.

The comparison denominator is the canonical nationwide registry of tracked DSA-endorsed
Democratic primaries and every identified certified Democratic opponent. Candidate documents
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

Analysis units are normalized full-document segments embedded with the pinned local MiniLM model.
The cosine threshold is selected from human judgments at 0.55, 0.60, 0.65, 0.68, 0.70, 0.75,
and 0.80; no production threshold is selected before annotation. For the chosen threshold, the
pipeline constructs a cosine K-nearest-neighbor graph with `K=64`, runs weighted Leiden
RBConfiguration community detection at resolution 1.0, and retains communities with at least
four members. Cosine DP-Means at the same human-selected threshold is a robustness analysis.

Narrative lift and density comparisons use candidate/race-balanced weights because campaigns
contribute unequal text volumes. UMAP dimensions 2, 5, 10, 20, and 30 are compared using
trustworthiness before KDE dimensionality is fixed. Hot/cold-zone TF-IDF and NPMI characterize
the resulting density contrast; the two-dimensional projection is visualization only.
