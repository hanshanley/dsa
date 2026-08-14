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
