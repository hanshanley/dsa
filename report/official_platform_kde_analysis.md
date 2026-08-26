# Official-platform semantic density analysis

This analysis compares the recoverable official DSA and Democratic platform corpora separately
from candidate rhetoric.

## Corpus and balancing

- DSA: 6 documents and 328 passages.
- Democratic: 38 documents and
  5,109 passages.
- UMAP fit: 328 passages per group, selected
  deterministically in round-robin order across documents.
- KDE fit: the same equal-sized samples, representing
  6 DSA and
  38 Democratic documents.
- KDE weights: inverse within-document passage frequency, giving each represented platform equal
  aggregate density weight within its group.
- Density space: 5 dimensions; the 2D map is visualization only.

Equal sampling prevents the larger Democratic passage inventory from mechanically determining
the manifold or density estimates. It does not compensate for unavailable platforms or make
6 DSA documents equivalent in substantive coverage to
38 Democratic documents.

## Semantic regions

Regions are HDBSCAN communities in the selected-dimensional semantic space with single-cluster
fallback disabled to avoid treating an entire density zone as one broad semantic region. The
public map shows the two strongest regions per zone; this table retains up to six.

| ID | Density zone | Passages | Platforms | HDBSCAN confidence | Distinctive terms | Representative exact passage |
|---|---|---:|---:|---:|---|---|
| D1 | DSA-overrepresented | 30 | 6 | 0.90 | liberation, economy, feminism, capable, advancing | Neither major party is capable of advancing a positive program that meets the needs of the people. |
| D2 | DSA-overrepresented | 18 | 5 | 0.86 | far, donor, nationalist, controlled, attack | The center-right Democratic Party is controlled by its elite donor class, and cannot act as an effective political counter to the nationalist far right. |
| D3 | DSA-overrepresented | 10 | 2 | 1.00 | recruiting, color, relationship, further, elected | Maintain ongoing relationships with elected officials we’ve supported, to use their position to further our priorities Shift from primarily choosing among already-existing campaigns for... |
| M1 | Democratic-overrepresented | 43 | 11 | 0.94 | government, everyone, build, position, transparency | We believe that we are “Stronger Together.” A society and system of government that benefits everyone, is better for everyone. |
| M2 | Democratic-overrepresented | 167 | 7 | 0.64 | arkansan, access, insurance, healthcare, care | We will work with health professionals to support a robust mental health workforce and ensure that all Arkansans have access to mental health care. |
| M3 | Democratic-overrepresented | 43 | 12 | 0.92 | school, student, education, college, teacher | Democrats will work to expand access to career and technical education, magnet schools for science and the arts, International Baccalaureate programs, and early college high schools to... |
| M4 | Democratic-overrepresented | 42 | 12 | 0.90 | energy, clean, climate change, pollution, water | We will take bold steps to slash carbon pollution and protect clean air, ensure no Rhode Islanders are left behind as we accelerate the transition to a clean energy economy, and be... |
| M5 | Democratic-overrepresented | 25 | 12 | 0.98 | water, pollution, natural, land, carbon | We will take bold steps to slash carbon pollution and protect clean air at home, lead the fight against climate change around the world, ensure no Americans are left out or left behind as... |
| M6 | Democratic-overrepresented | 17 | 8 | 0.97 | worker, strongly, financial, proposal, family | Article 1: Economy & Labor Oregon Democrats believe w orkers are the foundation of our economy, and all workers and their families deserve a fair share. |
| S1 | Shared high-density | 41 | 4 | 0.91 | trump, biden, ally, world, administration | When he entered office, President Biden moved to quickly and decisively repair the damage that Trump had done to America’s relationships with our allies and our reputation around the world. |
| S2 | Shared high-density | 27 | 11 | 0.97 | war, peace, international, iran, humanitarian | The United States has a responsibility to advance international peace, ensuring that its actions adhere to international humanitarian law, protect civilian lives, and reflect core... |
| S3 | Shared high-density | 43 | 13 | 0.80 | healthcare, care, provider, patient, health | Patient autonomy in all health decisions, including reproductive choices and end-of-life care. |
| S4 | Shared high-density | 14 | 6 | 0.99 | discrimination, federal, housing, ice, employment | Prohibit discrimination based on sex, sexual orientation, or gender identity in all areas, including public accommodations and facilities, education, federal funding, employment, housing... |
| S5 | Shared high-density | 12 | 7 | 0.99 | health, emergency, facility, disease, improve | That adequate investment in public health programs to prevent the spread of contagious disease, ensure adequate supplies during public health emergencies, and to provide means for all... |
| S6 | Shared high-density | 12 | 7 | 0.99 | incarcerated, prison, marijuana, jail, drug | and (d) Expand prison and jail facilities for the treatment of drug addiction and mental illness if incarceration cannot be avoided; |

Interpret overrepresentation as relative emphasis within the recoverable corpus, not universal
agreement, policy direction, or evidence that every candidate adopts an organization's platform.
