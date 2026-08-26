# Official-platform semantic density analysis

This analysis compares the recoverable official DSA and Democratic platform corpora separately
from candidate rhetoric.

## Corpus and balancing

- DSA: 6 documents and 327 passages.
- Democratic: 35 documents and
  4,983 passages.
- Coverage composition: DSA has 3 national and
  3 subnational platforms; Democratic coverage has
  3 national and 32
  subnational platforms.
- Eligibility gate: platforms need at least
  10 quality-screened passages;
  3 sparse documents and
  119 navigation/form passages were excluded.
- UMAP fit: 327 passages per group, selected
  deterministically in round-robin order across documents.
- KDE fit: the same equal-sized samples, representing
  6 DSA and
  35 Democratic documents.
- KDE weights: inverse within-document passage frequency, giving each represented platform equal
  aggregate density weight within its group.
- Density space: 5 dimensions; the 2D map is visualization only.

Equal sampling prevents the larger Democratic passage inventory from mechanically determining
the manifold or density estimates. It does not compensate for unavailable platforms or make
6 DSA documents equivalent in substantive coverage to
35 Democratic documents.

## Semantic regions

Regions are HDBSCAN communities in the selected-dimensional semantic space with single-cluster
fallback disabled to avoid treating an entire density zone as one broad semantic region.
Of 5,310 eligible passages,
1,992 pass the density-zone thresholds,
796 of those are HDBSCAN noise, and
485 enter clusters that do not pass the retained
top-six-per-zone and substantive-support gates.
711 enter the 15
retained regions below. The public map shows
6 regions covering
262 passages.

These subregions are exploratory rather than a stable topic taxonomy. Across
24 prespecified HDBSCAN configurations, holding the
six-per-zone retention cap and substantive-support gates fixed, the number of retained regions
ranges from 6 to
17, and assigned passage counts range from
501 to
1,990. See
`clustering_sensitivity.csv` for the full accounting and `platform_coverage.csv` for every
included or excluded platform. `analysis_flow.csv` reconciles every passage count.

| ID | Density zone | Passages | Platforms | HDBSCAN confidence | Distinctive terms | Representative exact passage |
|---|---|---:|---:|---:|---|---|
| D1 | DSA-overrepresented | 49 | 6 | 0.89 | collective, liberation, join, necessary, come | ...a strategy toward STL DSA as a mass socialist organization firmly rooted in the multi-racial working class, powered and empowered by its members in the fight for our collective liberation. |
| D2 | DSA-overrepresented | 13 | 5 | 0.96 | donor, nationalist, controlled, attack, far | The center-right Democratic Party is controlled by its elite donor class, and cannot act as an effective political counter to the nationalist far right. |
| D3 | DSA-overrepresented | 13 | 6 | 1.00 | helped, gaza, won, wage, strike | We’ve won higher wages and better working conditions by going on strike as unionized teachers, auto workers, nurses, and graduate students. |
| M1 | Democratic-overrepresented | 123 | 25 | 0.81 | water, land, pollution, management, environmental | Our state faces many other environmental challenges such as wetlands conservation, forestry management, protection of public waters, management of commercial animal waste, solid waste... |
| M2 | Democratic-overrepresented | 31 | 14 | 0.94 | education, school, high-quality, student, teacher | Democrats recognize and honor all the professionals who work in public schools to support students’ education—teachers, education support professionals, and specialized staff. |
| M3 | Democratic-overrepresented | 163 | 8 | 0.60 | arkansan, health, healthcare, insurance, fight | As a record number of Arkansans have health insurance, many still struggle to afford the prescription drugs necessary to live a meaningful life. |
| M4 | Democratic-overrepresented | 33 | 2 | 0.95 | violence, separation, dreamer, harassment, limited | Nebraska Democrats oppose discrimination, harassment, and bullying against any person for reasons including but not limited to: actual or perceived race, ethnicity, religion, familial... |
| M5 | Democratic-overrepresented | 23 | 15 | 0.97 | school, student, level, funding, teacher | Implement culturally responsive policies at every level within our schools by providing training for all school staff, school board members, and students, and by applying best practices to... |
| M6 | Democratic-overrepresented | 48 | 13 | 0.89 | jobs, investment, technology, infrastructure, economic | Transportation & Infrastructure Democrats believe in state and federal investment in public infrastructure and transportation to improve our state’s economic competitiveness, create jobs... |
| S1 | Shared high-density | 21 | 15 | 0.90 | financing, donor, money, contribution, disclosure | We believe money is not speech and government at all levels must require disclosures and regulate, limit, or prohibit campaign contributions and expenditures. |
| S2 | Shared high-density | 25 | 12 | 0.92 | voter, voting, paper, elected, ranked-choice | ...county, and state governments in their efforts to upgrade old voting equipment and machines with modern systems, including voter-verified paper ballots, to ensure that all voters are able... |
| S3 | Shared high-density | 42 | 11 | 0.93 | health, prescription, care, healthcare, price | [PDF page 18] ● Increased federal funding for community health centers, the Veterans Health Administration, the Indian Health Service, public hospital systems, disability care, mental... |
| S4 | Shared high-density | 22 | 9 | 0.96 | drug, treatment, addiction, disorder, use | Whenever possible, Democrats will prioritize prevention and treatment over incarceration when tackling addiction and substance use disorder. |
| S5 | Shared high-density | 46 | 6 | 0.75 | biden, trump, economic, ally, alliance | President Biden will continue to work closely with the EU on emerging political and economic challenges and work with our European and Indo-Pacific allies to disrupt Russia’s emerging... |
| S6 | Shared high-density | 59 | 9 | 0.73 | disability, service, education, access, protection | ...nutrition, clothing, shelter, freedom of religious practices, disability access, family unity, legal defense, a living wage for their work, and access to basic education services... |

Interpret overrepresentation as relative emphasis within the recoverable corpus, not universal
agreement, policy direction, or evidence that every candidate adopts an organization's platform.
The national/subnational coverage mismatch and parameter sensitivity preclude treating the region
inventory as a definitive partition of either organization's agenda.
