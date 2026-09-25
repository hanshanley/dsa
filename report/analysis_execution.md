# Analysis execution and source coverage

Audit observed at **2026-09-25T03:25:21.216495+00:00**. Research cutoff: **2026-09-22**.
The machine-readable receipt is `data/analysis/execution_audit.json`, including input hashes.
An audit timestamp is not a claimed model execution time.

## Actual analysis artifacts

| Stage | Input/output status | Recorded completion time (UTC) |
| --- | --- | --- |
| lexical | current | 2026-09-25T03:24:10.211114+00:00 |
| local_classifier | current | 2026-09-25T03:20:28.536930+00:00 |
| candidate_kde | current | 2026-09-25T03:21:17.880416+00:00 |

The lexical corpus contains **2,866 passages** in
**209 deduplicated analysis documents**.
The local topic model assigned **2,557** passages and left
**309** unclassified. Topic assignment is not stance classification;
agreement with keyword rules is not measured accuracy. No independent reference labels exist.

The candidate KDE retains **2,825 passages**:
**989 endorsed / 1,836 other-Democrat**,
from **104 candidate-cycle units**.
It selected **5 dimensions**. Its candidate-cycle deduplication differs
from the classifier's group-cycle deduplication. It is exploratory and source-imbalanced:
names, geography, year, office, and document format can affect the result.
No retained region for a group is not evidence that its candidates have no distinctive policy.

## What the source-reviewed comparison actually measures

**1,186 attributed statements** support
**478 comparisons across 126 directly
paired cases**; **115** have policy-position pairs.
The remaining comparison kinds are kept separate from policy positions. Reused national
presidential material adds zero independent observations.

| Policy relationship | Timing-supported | Timing-qualified | Total selected pairs |
| --- | ---: | ---: | ---: |
| different_emphasis | 53 | 22 | 75 |
| different_mechanism | 27 | 15 | 42 |
| different_scope | 17 | 11 | 28 |
| different_strategy | 33 | 23 | 56 |
| explicit_disagreement | 6 | 3 | 9 |
| shared_position | 99 | 66 | 165 |

These are assistant source reviews, not independent human gold. The categories count selected
evidence, not population prevalence, whole-platform similarity, or whole-campaign salience.
Different strategies or mechanisms can coexist; omissions never count as opposition.
Timing-qualified versions are not claimed to have been available before the primary.
Read the actual quotations and reviewed interpretations in `platform_comparison.html` and
`policy_comparison_findings.md`.

The complete-response export contains **287 published responses**,
**178 same-question pairs**, and
**30 separately identified shared-topic interview pairs**.
Edited topic rounds do not prove identical unedited questions or complete original answers.
Complete published responses do not imply complete campaign platforms, and these pairings add no stance labels.
Separate complete-interview exports retain
**40 published response blocks**.
Those are the publisher's edited quotations, not verbatim unedited transcripts or additional
independent stance labels; full text and provenance are in `data/analysis/policy_evidence/complete_interview_answers/`.
The platform-text export retains **17 complete captured sources**
and **526 separately scoped campaign-text blocks**.
Complete extracted sources retain navigation and embedded quotations for audit; they are not
automatically treated as current candidate positions. Existing model documents are reused rather
than duplicated. See `data/analysis/policy_evidence/complete_campaign_platforms/`.

## What is still missing

Nationwide source completeness: **False**.
The strict registry contains **420 primary records** and
**1,913 participant/ballot-option records**:
**1,876 individual candidate/race records**,
**7 endorsed ballot campaigns**, and
**30 other non-person ballot choices**.
**470 individual candidate records**
have reviewed words. Ballot choices such as Scattered or No Preference are not people with
missing personal platforms; endorsed ballot campaigns still require campaign evidence.
The denominator excludes separately labeled shared-ballot contexts and does not count unique people.
Suspected duplicate registry contexts remain explicitly flagged pending source-preserving resolution.
Even a record with reviewed words may have only a partial platform.

| Cycle | Individual candidates | Endorsed ballot campaigns | Other ballot choices | With reviewed words | Policy evidence gaps |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2016 | 169 | 0 | 12 | 7 | 162 |
| 2017 | 6 | 0 | 0 | 4 | 2 |
| 2018 | 166 | 0 | 0 | 47 | 119 |
| 2019 | 23 | 0 | 0 | 7 | 16 |
| 2020 | 713 | 0 | 18 | 99 | 614 |
| 2021 | 137 | 0 | 0 | 25 | 112 |
| 2022 | 157 | 0 | 0 | 37 | 120 |
| 2023 | 71 | 0 | 0 | 10 | 61 |
| 2024 | 138 | 7 | 0 | 31 | 114 |
| 2025 | 76 | 0 | 0 | 30 | 46 |
| 2026 | 220 | 0 | 0 | 173 | 47 |

Candidate-level gaps remain in `data/analysis/policy_evidence/historical_candidate_inventory.csv`;
paired and unpaired cases remain in `race_policy_comparison_matrix.csv`.
Missing sources are unknowns, not evidence of policy silence.
The acquisition worklist `policy_research_worklist.csv` groups repeated same-cycle presidential
records for research efficiency only. Its **833**
open work units are not independent observations and do not establish source applicability.

## Jev

- `data/analysis/jev_policy_preserving_pilot/summary.json`: prepared; 220 passages; 0 live requests in the recorded run.

All older pilots remain separately accounted for in the JSON receipt. Preparation is not
inference. No accuracy-improvement claim is supported without executed predictions and
independently reviewed reference labels.
