# Provisional GTE KDE region analysis

The KDE contains **36650** passages after deduplicating repeated text
within each candidate and election year:
**12234** from DSA-endorsed candidates and
**24416** from other Democrats. Density estimation is performed in
**10 dimensions**; the two-dimensional map is used only for
visualization.

![Labeled KDE regions](../figures/provisional_gte_kde.png)

## Interpreting the labeled regions

- **D regions** are spatial groupings among DSA-endorsed segments above the endorsed-group
  upper-quartile density-ratio cutoff.
- **M regions** are semantically coherent groupings among other-Democrat passages below that
  group's lower-quartile density-ratio cutoff.
- **S regions** are high-joint-density areas with small absolute density differences. They
  represent semantic overlap, not proof of identical positions.
- HDBSCAN identifies variable-shape clusters in the selected 10-dimensional UMAP representation
  (`min_cluster_size=60`, `min_samples=10`, Euclidean metric, EOM selection). Noise points remain
  unassigned. The table retains up to six substantive, sufficiently supported regions per zone;
  the map displays the top two per category to remain legible.
- Terms are locally distinctive document-prevalence terms from the underlying subregion text.
  Examples are extractive source passages, not generated paraphrases.

| Region | Interpretation | On map | Passages | Candidates | HDBSCAN confidence | Distinctive terms | Representative source text |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| D1 | DSA-overrepresented | Yes | 649 | 113 | 0.87 | socialist, progressive, movement, political, electoral | Robert LeVertis Bell: ...campaigns, I saw in real time how people were deepening their political understanding, how people were becoming strong organizers, how people were and still are building something that is... |
| D2 | DSA-overrepresented | Yes | 346 | 77 | 0.74 | energy, climate, renewable, climate change, fossil | Jabari Brisport: Since the passage of the Climate Leadership and Community Protection Act (“CLCPA”) in 2019, New York State has not done nearly enough to combat climate change and invest in renewable energy... |
| D3 | DSA-overrepresented | No | 333 | 80 | 0.65 | housing, tenant, landlord, rent, eviction | Claire Valdez: Second: Housing as a human right: For far too long, real estate has had a stranglehold on New Y ork City, and the result has been the violent eviction and displacement of our Black and... |
| D4 | DSA-overrepresented | No | 229 | 60 | 0.74 | worker, union, wage, labor, minimum wage | Melat Kiros: That means: • Passing the PRO Act to make it easier for workers to organize, form unions, and collectively bargain • Ending at-will employment, strengthening wrongful termination... |
| D5 | DSA-overrepresented | No | 75 | 24 | 0.95 | israel, palestinian, military, palestine, israeli | Claire Valdez: government has funded and supported Israel as it entrenches apartheid and military occupation across Palestine. |
| D6 | DSA-overrepresented | No | 79 | 44 | 0.94 | healthcare, single payer, universal, health, care | Christian Celeste Tate: We will pass the New York Health Act to make healthcare universal, we will fully fund the hospitals that treat our community, and we will refuse to walk back access to the care that New... |
| M1 | Other-Democrat-overrepresented | Yes | 849 | 148 | 0.98 | california, school, student, education, teacher | Tim Myers: I am endorsed by those most responsible for student success—from the classroom teachers of CTA to the school principals of United Administrators of Southern California, and Cindy Marten... |
| M2 | Other-Democrat-overrepresented | Yes | 379 | 57 | 0.73 | reserve, farm, food, agricultural, agriculture | Chris Wilhelm: The agricultural reserve is one of the things that makes Montgomery County unique, so the county government should be supporting career pathways to promote agriculture and food service. |
| M3 | Other-Democrat-overrepresented | No | 502 | 143 | 0.87 | transportation, transit, bus, bike, lane | Brandy H. M. Brooks: ...developments that include support for and connections to transit infrastructure - whether that means building in safe walking and bike paths to buses and trains, building roads with... |
| M4 | Other-Democrat-overrepresented | No | 467 | 141 | 0.96 | alderman, university, political, bachelor, degree | Katie Sieracki: She’s running for: 33rd Ward alderman Her political/civic background: Progressive Campaign Advance Team Lead, Special Education and Clean Water Advocate Her occupation: Managing Director of... |
| M5 | Other-Democrat-overrepresented | No | 576 | 142 | 0.82 | housing, unit, affordable housing, affordable, zoning | Radwan Chowdhury: It will prioritize workforce and missing middle housing while ensuring deeply affordable units are included through strengthened inclusionary zoning. |
| M6 | Other-Democrat-overrepresented | No | 75 | 32 | 0.95 | waste, composting, recycling, incinerator, incineration | Hamza Khan: ...should be moving toward a long-term strategy centered on waste reduction, reuse, composting, recycling modernization, and circular economy principles rather than continued dependence... |
| S1 | Shared high-density | Yes | 209 | 132 | 0.92 | education, school, served, worked, teacher | Stephanie Gallardo: I have served as a local building representative for my high school, and was also elected to the Board of Directors for our state educator union, the Washington Education Association (WEA). |
| S2 | Shared high-density | Yes | 67 | 25 | 0.99 | border, immigration, immigrant, trump, mike | Sol A. Flores: I am enraged by Donald Trump’s orders to begin constructing a border wall, double down on enforcement efforts that will instill fear and unjustly target immigrant communities, and threaten... |
| S3 | Shared high-density | No | 271 | 131 | 0.85 | process, resident, zoning, council, development | Jeanette B Taylor: In my ward I have supported more public, democratic processes such as the Community Development Table composed of 20th Ward residents who work with my office to make decisions about... |
| S4 | Shared high-density | No | 70 | 30 | 0.99 | travis, attorney, criminal, court, case | Erin Martinson: As a prosecutor with the Travis County Attorney’s Office, I led the protective order division and transformed it into a statewide model for other offices. |
| S5 | Shared high-density | No | 184 | 63 | 0.77 | tax, corporation, income, revenue, pay | Ashley Hartmeier-Prigg: We must fully fund our schools and we can only do that with revenue system reform that gives tax relief to seniors and folks living on fixed incomes while demanding that corporations and... |
| S6 | Shared high-density | No | 207 | 99 | 0.91 | leadership, party, matter, take, legislator | Brian W. Jones: So whenever you go into a situation like that, no matter your personality or no matter your background and you’re trying to upset the political and power structure of an area, you’re going... |

## Limits

This is a descriptive analysis of the recoverable corpus. Region labels summarize the text
actually present in each density area; they do not imply a complete nationwide census, causal
importance, or agreement merely because both groups occupy a shared region.
