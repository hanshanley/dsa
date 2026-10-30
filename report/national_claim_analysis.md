# National platforms: claim-based analysis

**Full eligible-source claim analysis with automated screening, not human-certified claims or fact-checking.** All source chunks and any failed/unresolved extractions remain auditable in the coverage tables and raw responses.

The analytical text is the **claim**, not its original evidence passage. The separate passage-based analysis and its outputs remain unchanged.

| Organization | Claims analyzed | Documents | Document / fallback bundles |
|---|---:|---:|---:|
| Democratic | 11870 | 7 | 7 |
| Republican | 9460 | 6 | 6 |
| DSA | 5153 | 122 | 9 |

## Semantic density

![Pairwise density of claim language](../figures/national_claims/full/expanded/pairwise_density.png)

The shared representation uses 10 dimensions for KDE; the two-dimensional display is not the density-estimation space. Sampling balances organizations and gives each document/fallback-period bundle equal aggregate density weight. Positive contrasts mean greater first-organization language density, not agreement, ideological direction, or causal differences.

Platforms/programs-only sensitivity: **complete**. Its independently fitted space has 5 dimensions; its coordinates cannot be compared directly with the expanded map.

## Topics

![Document-weighted CAP topic emphasis](../figures/national_claims/full/topic_emphasis.png)

The existing pinned MiniLM classifier compares normalized claim text with CAP topic descriptions (minimum cosine similarity 0.2). Each claim receives at most one topic; unclassified claims remain in the denominator. This is exploratory classification, not validated topic gold. Topic shares use equal aggregate document/fallback-bundle weights, not raw claim counts.

| Organization | Largest weighted topic shares in this input |
|---|---|
| Democratic | Unclassified 13.8%; International affairs 9.1%; Social welfare 7.9% |
| Republican | Unclassified 15.0%; Defense and veterans 8.4%; International affairs 7.9% |
| DSA | Unclassified 13.6%; Social welfare 11.3%; Government operations 9.7% |

DSA's adopted-only input contains 3 documents and 842 claims, compared with 122 documents and 5,153 claims in the expanded input.
The largest classified DSA topic is Social welfare (11.3%) in the expanded input and Social welfare (12.9%) in the strict input. This sensitivity reflects source-type and period composition, not a measured change in positions over time.

## Provenance and reproduction

Full extraction uses source chunks of at most 240 words, sentence-aware splitting of long paragraphs, and at most 1,200 preceding-context characters. The prompt requires preservation of actors, stance/modality, conditions, temporal scope and reported-speaker attribution; automated revision does not certify that every requirement was met. Source organization remains metadata rather than a mechanically repeated embedding prefix. Exact within-document claim duplicates are retained in downloads but excluded from fitting.

- [Complete claim/source download, not metadata only](../data/analysis/national_claims/full/claim_documents.zip)
- [Claims and exact supporting source offsets](../data/analysis/national_claims/full/claims.csv)
- [Complete source texts](../data/analysis/national_claims/full/complete_sources.csv)
- [Topic assignments](../data/analysis/national_claims/full/topic_assignments.csv)
- [Weighted topic shares, both views](../data/analysis/national_claims/full/topic_emphasis.csv)
- [Machine-readable analysis summary](../data/analysis/national_claims/full/analysis_summary.json)

Source documents retain their original attribution. Claims describe what sources assert; they do not independently establish truth. Pooling mixes periods and genres. Missing historical sources, including the final 2015 DSA strategy, remain missing rather than being inferred from later documents. No website deployment is performed.

Extraction status: **complete**; effective chunk dispositions: `{"normalized": 2462, "source_repaired": 161}`.
[Source coverage](../data/analysis/national_claims/full/source_coverage.csv) / [Chunk dispositions](../data/analysis/national_claims/full/block_status.csv)

Original Gemma chunk outcomes remain `{"normalized": 2596, "validation_failed": 27}`. Targeted assistant source corrections cover **161 chunks** and supply **1,041 replacement claims**; **1,078 original candidates** are superseded, not erased. Zero-claim corrections explicitly dispose of non-policy material rather than inventing assertions.

Each correction is bound to the exact target, reference-only context, raw-response bytes and normalization fingerprint. Unaffected model claims retain their original IDs and wording; superseded originals remain in the download but cannot enter fitting or anchor duplicates. Corrected rows have `normalization_origin=assistant_source_repair` and a blank `model_claim_text`, never a falsely attributed Gemma reply. Original model failures and diagnostics remain failures in `model_status`, even when a source correction recovers their content. This is targeted assistant source-entailment work, not independent human gold or factual verification.

Archived original-candidate review flags: **1,054**; flagged model candidates still lacking a superseding correction: **0**. Historical flags are not a count of unresolved errors in replacement claims.
[Source-bound correction records](../data/analysis/national_claims/full/source_repairs/)
