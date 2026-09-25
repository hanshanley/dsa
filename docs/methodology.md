# Methodology

## Sanitized publication representations

Public source snapshots have incidental API keys, authentication tokens, session identifiers
and signed URL credentials redacted. Their published hashes and byte counts refer to those
sanitized representations. `data/analysis/publication_redactions.json` retains the corresponding
original hashes and transformation categories without credential values. Original captures are
quarantined locally outside Git, not distributed as an alternative public copy.

This transformation is separate from source collection and does not change a source's publication,
revision or capture date. Source-version identifiers remain stable; candidate quotations, dates,
comparison interpretations and complete answers are compared with their pre-redaction semantic
fingerprints. Every affected usable source is replayed through the normal scoped extraction and
validation pipeline before analysis is regenerated.

## Research question

What do DSA and the Democratic Party officially say, and what issues distinguish
DSA-endorsed candidates from other Democrats in the same primaries?

## Scope

The election study begins January 1, 2016 and uses a dated research cutoff. Source discovery
begins January 1, 2015, independently of election-cycle attribution. A “DSA candidate” is a
candidate officially endorsed by DSA National or a local DSA chapter. Membership or a
self-description alone is not sufficient.
Primary-election dates are not document-publication dates. The persistent
`candidate_source_date_corrections.json` ledger rejects known unsupported dates using the
exact source URL and byte hash, including when a legacy queue reintroduces the same date under
another document ID. Corrected undated, post-primary live captures are excluded from dated
model inputs while their actual candidate statements remain in timing-qualified exports.
Extraction never substitutes a document's `effective_date` for a missing publication date.
An effective date can describe election context or a policy's intended application, not when
the public could read it. Genuine pre-primary archive captures still establish availability
without inventing an original publication day.
Discovery timestamps, sitemap revision dates and requested archive timestamps likewise do not
become publication dates. A requested archive that resolves to a live page is not an archived
version. Unscoped campaign redirects to another domain require identity and election-cycle
review, and known wrong-content versions are excluded by exact candidate/race/hash.
A job naming an archive replay fetches that replay first, not a currently live replacement.
Cached live bytes cannot satisfy an archive request merely because a manifest preserved the
requested timestamp. Failed archive requests remain explicit failures rather than silently
falling back to a different live edition.
An endorsement formally revoked before the primary does not qualify as active support at that
primary. Such candidacies stay in the historical registry with a sourced scope exclusion.
Their candidate statements remain in `excluded_candidate_statements.csv`, rather than being
deleted or counted as currently endorsed evidence. For example, the chapter's April 26, 2022
revocation notice excludes Brandy Brooks's July 19, 2022 primary candidacy; it does not alter
her separate 2018 endorsement.
Official returns also govern candidate-to-race corrections. The source-association correction
ledger binds a correction to an exact candidate, election date, source URL and retained byte
hash so a stale discovery queue cannot silently restore a cross-district pairing.

The endorsement census seeks every identifiable federal, state, and local Democratic primary
endorsement nationwide. Because local archives are decentralized and may be deleted, results
must include the coverage ledger and must not claim unknowable absolute completeness.

The canonical denominator is endorsement-first. Verified manual endorsements and adjudicated
DSA National records seed races before any quotation or campaign-document evidence is attached.
National records are classified as Democratic primary, nonpartisan primary, general-only,
unopposed, ballot or party position, noncandidate, or source unavailable. Only dated Democratic
primaries enter the candidate-group comparison; exclusions remain in the reconciliation
table. This prevents quotation availability from silently determining which races exist.

The separate nationwide congressional inventory is not endorsement-filtered. It preserves
every candidate-bearing source row in the recovered official FEC House/Senate results
workbooks, including all parties, zero-vote candidates, nonnumeric nomination flags, and
special-election appendices. It retains source cells and hashes rather than silently repairing
inconsistent source dates or IDs. Rows from overlapping publications and fusion ballot lines
are observations, not deduplicated candidates or elections.

Regular Senate seat expectations come from the Senate's independent Class I/II/III inventories;
the importer checks 100 class memberships and two seats per state. House seat counts are checked
against 435 voting seats per cycle, with nonvoting delegations separate. Where a current results
workbook is missing, a prior apportionment-era map supplies a checklist only, not an invented
roster. The 2024 general-ballot workbook is retained separately and never fills missing primary
results. Special-election calendars retain their own update dates and cannot imply coverage
through a later research cutoff.

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

Reviewed national presidential platforms may be displayed in other same-cycle primary
records only through the separately checked applicability table. The browser resolves
quotations and interpretations from the original review, verifies candidate identities and
the presidential election context, and labels every reused card. Such displays create no new
independent observations, do not imply state-specific campaigning, and do not establish
whether a candidate was still active after suspending a campaign.

Primary sticking points have two separate measures:

- **Explicit conflict:** a candidate or another Democrat directly contrasts positions, attacks a policy,
  or rebuts the other in an official source.
- **Coded divergence:** reviewed primary-source passages support materially different policy
  instruments or scopes even without a direct attack.

Mention counts are descriptive, not proof of importance. Salience requires corroboration such as
prominent platform placement, repeated treatment, debate time, or direct contrast.

Policy positions, campaign framing, and agenda items are counted separately. Previously
uncategorized statements receive a representation label only through an explicit review bound
to the exact quotation and source hashes; the topic name alone is not a classification rule.
This review adds no new statements or comparisons and does not turn assistant reviews into
independent human gold.

## Automated assistance

Scripts may retrieve documents, find candidate passages, transcribe media, and suggest topic
codes. Independent human certification requires a human reviewer to verify each excerpt against
the original page, PDF, audio, or video. The separately labeled assistant-source-reviewed
comparisons remain provisional with respect to that requirement. Generated summaries are never
evidence.

The September 2026 policy-evidence cleanup does not equate a successful fetch with attribution.
Candidate analysis excludes known post-primary documents, undated sources captured outside the
campaign window, unrelated homepage seeds, rolling indexes without article/excerpt scope,
unscoped shared documents, and races outside the
tracked Democratic-primary comparison. Exclusions remain in
`data/analysis/candidate_document_eligibility.csv`; raw sources are not erased.
These are eligibility screens, not a claim that every retained paragraph is a verified position.
Both sides must have substantive eligible text before a race counts as paired.
The candidate KDE applies the same metadata eligibility rules and primary-registry scope;
it cannot fall back to the older unscoped segment pool. Its manifest binds the exact segment,
metadata, registry and classifier-corpus hashes. A change to any of those invalidates the run.
The screening-version identifier also invalidates outputs when eligibility rules change without
changing raw source bytes. Both the local topic model and the GTE embedding model use pinned
model revisions.

Archive toolbar blocks and exact page controls are excluded before model passages are
assembled, without renumbering or altering the retained original paragraphs used for citations.
`rebuild-analysis-segments` replays this preparation from local retained text and exports the
excluded paragraph locators. Repeated substantive wording is a duplicate signal, not proof of
boilerplate: shared candidate positions must survive into the group-aware deduplication stage.
The preparation parser annotates HTML navigation, site controls, forms, and footers without
removing text from the retained extraction. A paragraph is structurally excluded only when all
its text fragments belong to a recognized control; mixed fragments remain for review. Every
structural exclusion must match the retained source hash and exact original paragraph text.
Class-based exclusions require specific component names, not substrings such as "menu" in
whole-page theme configuration classes. Regression tests and an actual-source audit check that
policy paragraphs survive as well as checking that publisher controls disappear.
Short exact control phrases are screened separately. These checks do not certify every retained
passage semantically. Speeches, candidate statements and press releases now require explicit
candidate-only scope just like interviews: a campaign-related article may still include other
speakers, reporter narration and publisher menus.

Original publication, revision, and archive capture are separate dates. Known revisions are
not backdated to initial publication. An explicitly identified official campaign-platform page
created before the current campaign window can enter through its retained in-window archived
edition; this exception does not admit old interviews as current policy. The original publication
date stays unchanged and the exact edition date used for eligibility is exported as
`temporal_evidence_date`. National-platform reuse checks that date, not only page creation.
The source-date correction ledger now repairs 339 metadata associations against retained bytes.
Many are copies of the same national source, not 339 independent sources.

`analyze` writes `data/analysis/execution_audit.json` and `report/analysis_execution.md`.
The receipt distinguishes audit observation time from actual recorded model completion times,
checks source-preparation dependencies as well as output-corpus hashes, and matches topic
prediction text and IDs to the actual input rows. A completed model with stale upstream
preparation is not current. The receipt separately counts policy positions and campaign frames,
shows timing-supported versus timing-qualified policy relationships, and keeps missing
candidate/race records visible by cycle. These are selected-evidence counts, not inferential
estimates of national agreement. Prepared Jev pilots are checked against the current corpus and
local prediction hashes; a request file does not prove inference or accuracy.

Registered complete interview blocks replay through `dsa_analysis.reviewed_interviews` before
the model corpus is rebuilt. Their source/candidate association must already have a validated
review, and the selected original paragraph locators are explicit in the bundle's specification.
Separate document IDs prevent a short reviewed quote from masquerading as full-text input.
The complete-response export preserves publisher edits and ellipses; it is not an unedited
transcript. Full response blocks add no independent stance labels by themselves.
The same replay mechanism exports complete captured campaign-platform sources and separately
scoped model blocks. Historical quotations, navigation and ambiguous questionnaire choice lists
can remain in the complete download without entering current candidate-model text. Existing
eligible documents are referenced rather than enrolled again to inflate text weight.

Edited broadcast topic rounds are explicitly distinguished from same-question questionnaires.
Their complete *published* response blocks are preserved, but the edit does not establish the
complete unedited answer or identical original interviewer wording. Each round binds its own
speaker heading and original paragraph range, preventing a later speaker from being attributed
to the first candidate.

Policy coverage distinguishes individual candidate/race records, endorsed ballot campaigns,
and other non-person ballot choices. Generic Scattered or No Preference totals remain in the
election data but are not people with missing platforms. An endorsed Uncommitted campaign still
requires campaign evidence. The acquisition worklist groups repeated presidential records by
cycle and an explicit name-alias map only for research efficiency; it does not create evidence,
merge election records, or establish that a platform version preceded every state primary.
Elizabeth Warren's middle-name variants are bound to the same FEC candidate ID in the retained
2020 workbook; those variants no longer make one national platform look like a multi-speaker
document or multiple independent KDE candidate units.

`python -m dsa_analysis.policy_comparison --ingest` reproduces the separately identified
assistant-source-reviewed candidate examples from retained, hash-pinned sources. The Colorado
interview check requires each quotation in a named-speaker paragraph. The supplemental New York
reviews combine exact retained-text matching with a separate semantic attribution review of
campaign-authored platforms and candidate answers; substring matching alone is not attribution.
Their candidates must also match the recovered Democratic primary ballot. Archive-capture dates
are recorded separately from unknown original publication dates.
An explicit reviewed alias can link a display name to an exact ballot-source candidate ID.
Direct official alias evidence and contextual same-race corroboration are separately labeled;
names are not fuzzily merged and the canonical speaker is not silently renamed. Identity-only
documents do not become campaign-policy evidence.
Shared nonpartisan ballots use an explicit separate comparison scope: the focal endorsed
candidate's actual party preference is preserved, and only declared Democrats are comparators.
Certified candidate lists can establish identity when numeric returns are unavailable, but
cannot supply votes or winners. Upcoming elections remain marked future; no other Democrat is
invented when the official qualified field contains only the focal candidate in that category.
Only explicitly registered
`candidate_excerpt` paragraphs enter the candidate corpus, not the interviewer's questions,
reporter's narration, or page navigation. The original edited interview remains the authority;
the candidate's factual claims are not independently verified by quote matching.
Interview, questionnaire, debate, forum, voter-guide and profile/op-ed sources require explicit
candidate-only scoping even if the source is associated with only one candidate. Otherwise the
full text is withheld with `mixed_speaker_source_requires_candidate_scope`. Curated, verified
quotations from those sources can still support the separate comparison dataset.
Assistant-reviewed examples keep `reviewed=false` in the human-review excerpt ledger and are
labeled `assistant_source_review_not_independent_human_gold` in the separate export.

Comparisons preserve shared positions, different policy scope, different emphasis, and different strategies.
For compound questionnaires, a stance must be bound to the specific proposition being compared:
answering that a candidate has never opposed a shelter is not opposition to housing assistance.
Question hashes and generic default labels are not policy claims. Reviewers must read the full
answer, retain a coherent short quotation, and summarize the actual commitment with its
conditions. File/hash/date validation is not itself semantic verification.
For repeated checkbox answers within a PDF page, an exact `answer_context` binds the short
response to its specific question. This context is retained for audit but is not treated as
candidate-authored quotation text or added to the quote-only model scope.
The complete-answer questionnaire export replays separately reviewed answer boundaries,
checks every numbered prompt and the final article-stop marker, and enrolls answer-only
paragraphs under distinct full-answer document IDs. It never overwrites quote-only records.
Matching questions does not assign a stance relationship or add to reviewed-comparison counts.
Interleaved surveys require an explicit answer-paragraph selection within each question and
a matching speaker prefix; other candidates' answers cannot enter that candidate's corpus.
When one shared question precedes several named candidate sections, explicit answer ranges
must lie inside the reviewed section boundary and follow an exact candidate-name heading.
Other offices' candidates, biographies, and publisher nonresponse notices remain outside the
candidate-answer corpus.
Interleaved multi-paragraph responses must begin with the reviewed candidate's name prefix
and cannot contain another listed candidate's response prefix. The full answer is retained
across its reviewed paragraphs; a first-paragraph snippet is not substituted for the complete
response.
Nonpolicy prompts and individually flagged attribution concerns remain in the complete
downloads but are excluded from policy-model inputs. Suspected publisher duplication is
preserved with a caveat, not silently repaired or treated as independent agreement.
All full answers, not just metadata, are included in both response and matched-pair downloads.
Publisher insertions within an answer, such as newsletter advertisements, are removed only
through exact-text, paragraph-bound exclusions with a review reason. The exported locator
lists only retained candidate paragraphs, so later corpus enrollment cannot reintroduce the
advertisement. These exclusions are separately recorded in the complete-answer download.
Publisher-controlled questions constrain the subject distribution, so even complete responses
cannot establish a whole campaign's relative issue salience. Embedded quotations and apparent
source wording errors remain visible rather than being silently converted into commitments.
For later-revised historical webpages, retained JSON-LD can verify the publisher's original
publication and later revision dates. The metadata node must identify the same page, not a
linked image or unrelated article, and both dates must match the retained bytes. A later
revision still makes the current answers timing-qualified; an old publication date does not
certify that the current body was available before the primary.
When a publisher explicitly says responses were added after first publication but gives no
revision day, the original date is retained and the exact update notice is bound to its source
paragraph. That source remains timing-qualified; the original date is neither erased nor
silently applied to the later contribution.
Opposite stance codes on different propositions do not establish disagreement. A dated party
platform comparison cannot project a current undated DSA page backward into an earlier cycle;
such pairs are withheld in `platform_comparison_eligibility.csv`. Organizational platforms remain
distinct from positions attributable to individual candidates.

Input hashes prevent the report from displaying a candidate topic or KDE figure as current after
the candidate corpus changes. Legacy automated contrast snapshots that lack their original
statement-evidence input are labeled unvalidated; they are not the new source-reviewed examples.

Archived URL identity preserves query parameters, and the actual final replay capture date takes
precedence over the requested snapshot date. Gzip responses are decoded with a bounded output
size while retaining the original wire bytes and source hash. Partial re-extraction batches
retain knowledge of other speakers sharing the same source; missing locators do not assign a
whole multi-candidate page to one person. Candidate filings/results are context, not policy
text, unless a reviewed candidate-authored section is explicitly scoped.
Year-only publication values remain unknown exact dates, with the supplied year retained in
notes; they are not promoted to January 1. Historical source-version uncertainty remains a
qualification even when the actual candidate answer has been recovered.

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
and state Democratic Party categories. If an official PDF combines a platform with a constitution
or bylaws, only the platform section is eligible; internal party-governance text is excluded at
the first explicit constitution/bylaws boundary.

Official-platform robustness uses two additional balance controls. First, feature prevalence is
computed at the document level: each platform contributes at most one observation to each
canonical policy feature, regardless of length or repetition. The semantic analysis separately
requires at least 10 quality-screened passages per platform; sparse fragments do not receive the
same aggregate weight as complete platforms. Second, the official-platform semantic fingerprint
fits both UMAP and Gaussian KDE on equal-size deterministic samples selected round-robin across
documents within each group. KDE then uses inverse within-document passage-frequency weights so
every eligible platform has equal aggregate density weight within its group. The public map draws
only this equal-size sample, while density scoring and clustering use all eligible passages. The
dimensionality sweep tests 2, 5, 10, 20, and 30 dimensions using trustworthiness; the current
corpus selects five dimensions. Coordinate standardization is also fit on the balanced sample,
and KDE uses Scott's bandwidth rule. HDBSCAN
(`min_cluster_size=10`, `min_samples=3`, leaf selection,
`allow_single_cluster=false`) identifies exploratory
DSA-overrepresented, Democratic-overrepresented, and shared high-density regions, retaining
unassigned points as noise. A prespecified 24-run sensitivity grid varies leaf versus
excess-of-mass selection, minimum cluster size (8, 10, 15, 20), and minimum samples (2, 3, 5).
The six-per-zone retention cap and substantive-support gates remain fixed across that grid so
the production and sensitivity counts are comparable. The region inventory is not treated as a
stable topic taxonomy when counts or assignment coverage vary across the grid. The 2D UMAP is
visualization only; each label is anchored to an actual region passage nearest the full-region
centroid.

Equal group samples prevent the much larger Democratic passage inventory from mechanically
dominating the fitted manifold or densities. They do not compensate for missing organizational
documents or remove the interpretive limitation created by substantially fewer recoverable DSA
platforms. Platform records whose current inventory status is not `verified` are excluded even if
an older extraction artifact remains on disk.

### Local-model topic classification

Topic emphasis follows the `state-politics` design:

- a published Comparative Agendas Project major-topic taxonomy in `config/cap_topics.json`;
- the configured `sentence-transformers/all-MiniLM-L6-v2` model;
- local MPS execution when available, otherwise local CPU;
- normalized embeddings and nearest-topic cosine similarity;
- a 0.20 minimum-similarity threshold, with below-threshold rows explicitly unclassified;
- runner-up topic and margin retained for every row;
- a transparent seed-term keyword baseline;
- a retained schema marker that the legacy quotation-level reviewed-code crosswalk is not
  applicable to full-document segments.

The default classifier uses no hosted model API. The model classifies the exact segment text in
`data/analysis/candidate_text_corpus.csv`; it does not generate replacement text or factual
claims. `data/analysis/model_topic_classifications.csv` retains exact text and aggregated
candidate, race, document, URL, and locator provenance beside every prediction and score.

Low-similarity and low-margin rows remain directly filterable.

### Optional Jev benchmark

`benchmark-jev` prepares a deterministic, round-robin sample across group and election-cycle
strata. Each request uses the exact passage, all CAP major-topic descriptions, and an explicit
`unclassified` choice. Candidate identity, endorsement group, local predictions, and reviewed
labels are not added to the request. The pilot compares topic assignment, not political stance.

Hosted execution requires both `--execute --allow-hosted` and `TYPESAFE_API_KEY`. The request
uses TypeSafe's documented Choice primitive and the versioned `jev-1.13.0` model; the model,
complete probability keys, finite probability range, probability sum, selected option, and
usage fields are validated before a response can become a prediction. Responses are cached by
the full request hash, so changing the rubric or model cannot reuse an incompatible prediction.
The canonical local output is never overwritten.

The API contract is documented at `https://docs.typesafe.ai/introduction/quickstart`,
`https://docs.typesafe.ai/primitives/choice`, and `https://docs.typesafe.ai/models` (checked
September 22, 2026). The live integration has not been exercised without API credentials.

`review.csv` omits both model predictions and endorsement-group metadata. Blank
`gold_topic_code` means unreviewed; the literal `unclassified` is an affirmative gold label.
A reviewed row requires a matching segment hash and `reviewed_by`. Accuracy, macro-F1 over
gold-supported classes, multiclass Brier score, and log loss are computed on the same reviewed
rows for the compared models where applicable. Cosine similarity is not a probability, so
probabilistic scores are reported only for Jev.

Without gold labels, agreement and classification coverage are diagnostic only and accuracy
remains null. The pilot is balanced across strata, not population-weighted, and overlapping
passages are not independent trials. Even a positive pilot accuracy difference does not by
itself establish a production improvement. No classifier replacement or nationwide conclusion
is authorized by the pilot.

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
points are clustered with HDBSCAN in the selected 10-dimensional UMAP representation. HDBSCAN
uses Euclidean distance, `min_cluster_size=60`, `min_samples=10`, excess-of-mass cluster
selection, and permits one cluster when a zone has no stable internal split. Points labeled
`-1` remain unassigned noise rather than being forced into a region. The complete region table
retains up to six substantive regions per category, while the visualization displays the top two.
Each region is labeled with locally distinctive terms, an extractive representative source
passage, segment count, and unique candidate count. These labels summarize underlying text and do not change the
higher-dimensional density calculation.
