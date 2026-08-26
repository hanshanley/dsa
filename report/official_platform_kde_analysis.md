# Official-platform semantic density analysis

This analysis compares the recoverable official DSA and Democratic platform corpora separately
from candidate rhetoric.

## Corpus and balancing

- DSA: 6 documents and 328 passages.
- Democratic: 38 documents and
  5,320 passages.
- UMAP fit: 328 passages per group, selected
  deterministically in round-robin order across documents.
- KDE fit: the same equal-sized, document-balanced samples.
- Density space: 5 dimensions; the 2D map is visualization only.

Equal sampling prevents the larger Democratic passage inventory from mechanically determining
the manifold or density estimates. It does not compensate for unavailable platforms or make
6 DSA documents equivalent in substantive coverage to
38 Democratic documents.

## Semantic regions

Regions are HDBSCAN communities in the selected-dimensional semantic space. The public map shows
the two strongest regions per zone; this table retains up to six.

| ID | Density zone | Passages | Platforms | HDBSCAN confidence | Distinctive terms | Representative exact passage |
|---|---|---:|---:|---:|---|---|
| D1 | DSA-overrepresented | 52 | 6 | 1.00 | society, goal, recruiting, come, collective | Transformational change in society does not come from moral righteousness or a checklist of policy positions, but from growing and wielding power. |
| M1 | Democratic-overrepresented | 1286 | 34 | 1.00 | student, affordable, infrastructure, environment, improve | ...support the use of restorative justice practices that help students and staff resolve conflicts peacefully and respectfully while helping to improve the teaching and learning... |
| S1 | Shared high-density | 704 | 41 | 1.00 | health, service, family, healthcare, worker | ● Access to improved healthcare services, including mental health services, for veterans and their families. |

Interpret overrepresentation as relative emphasis within the recoverable corpus, not universal
agreement, policy direction, or evidence that every candidate adopts an organization's platform.
