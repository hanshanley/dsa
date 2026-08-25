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
- Each zone is divided into 12 candidate subregions in the selected 10-dimensional semantic
  representation. The table retains up to six substantive, sufficiently supported regions;
  the map displays the top two per category to remain legible.
- Terms are locally distinctive document-prevalence terms from the underlying subregion text.
  Examples are extractive source passages, not generated paraphrases.

| Region | Interpretation | On map | Passages | Candidates | Distinctive terms | Representative source text |
| --- | --- | --- | ---: | ---: | --- | --- |
| D1 | DSA-overrepresented | Yes | 333 | 80 | housing, tenant, landlord, rent, eviction | Claire Valdez: Second: Housing as a human right: For far too long, real estate has had a stranglehold on New Y ork City, and the result has been the violent eviction and displacement of our Black and... |
| D2 | DSA-overrepresented | Yes | 346 | 77 | energy, climate, renewable, climate change, fossil | Jabari Brisport: Since the passage of the Climate Leadership and Community Protection Act (“CLCPA”) in 2019, New York State has not done nearly enough to combat climate change and invest in renewable energy... |
| D3 | DSA-overrepresented | No | 273 | 56 | socialist, america, socialism, progressive, chapter | Rebecca Parson: ...She got involved, quickly becoming a co-leader of Tacoma’s chapter of Indivisible, a grassroots progressive organization created shortly after Trump’s election and the publisher of the... |
| D4 | DSA-overrepresented | No | 229 | 60 | worker, union, wage, labor, minimum wage | Melat Kiros: That means: • Passing the PRO Act to make it easier for workers to organize, form unions, and collectively bargain • Ending at-will employment, strengthening wrongful termination... |
| D5 | DSA-overrepresented | No | 376 | 90 | movement, money, talking, win, electoral | Sianay Chase Clifford: “Unfortunately, what is really kind of sick and twisted about electoral politics is if that’s your message, you still need money to be able to share that message.” |
| D6 | DSA-overrepresented | No | 79 | 44 | healthcare, single payer, universal, health, care | Christian Celeste Tate: We will pass the New York Health Act to make healthcare universal, we will fully fund the hospitals that treat our community, and we will refuse to walk back access to the care that New... |
| M1 | Other-Democrat-overrepresented | Yes | 566 | 80 | food, reserve, farm, agricultural, agriculture | Chris Wilhelm: The agricultural reserve is one of the things that makes Montgomery County unique, so the county government should be supporting career pathways to promote agriculture and food service. |
| M2 | Other-Democrat-overrepresented | Yes | 619 | 157 | transportation, transit, bike, bus, lane | Brandy H. M. Brooks: ...developments that include support for and connections to transit infrastructure - whether that means building in safe walking and bike paths to buses and trains, building roads with... |
| M3 | Other-Democrat-overrepresented | No | 905 | 183 | housing, affordable housing, unit, affordable, development | James Robert Walkinshaw: ...to increase wages that will allow county residents of all communities to thrive in Fairfax County, invest in our affordable housing fund to preserve and expand affordable units, and ensure... |
| M4 | Other-Democrat-overrepresented | No | 359 | 42 | trump, donald, tlaib, american, war | Richard Gonzalez: Nevertheless, Donald Trump is our president, and I respect the office and acknowledge his investiture by the American people through our country’s democratic process. |
| M5 | Other-Democrat-overrepresented | No | 785 | 166 | small business, government, agency, business, performance | Rini Sampath: My administration believes the city government should be a relationship builder rather than a transactional regulator, which is why I have committed to a line-by-line review of every city... |
| M6 | Other-Democrat-overrepresented | No | 1068 | 168 | california, school, student, education, governor | Tim Myers: California’s vast, decentralized school system, with millions of students and billions of tax dollars, lacks the coordination and leadership needed to ensure that every student, regardless... |
| S1 | Shared high-density | Yes | 191 | 66 | tax, income, corporation, revenue, pay | Ashley Hartmeier-Prigg: We must fully fund our schools and we can only do that with revenue system reform that gives tax relief to seniors and folks living on fixed incomes while demanding that corporations and... |
| S2 | Shared high-density | Yes | 239 | 88 | abortion, reproductive, women, access, wade | Jumaane Williams: Women’s Reproductive Choice I believe, unequivocally, that women deserve the freedom to make their own health choices and that all women must have access to safe and legal abortions. |
| S3 | Shared high-density | No | 587 | 230 | resident, process, council, zoning, development | Rossana Rodríguez Sánchez: We have instituted Participatory Budgeting and Community Driven Zoning processes that have engaged thousands of residents. |
| S4 | Shared high-density | No | 339 | 76 | insurance, healthcare, medicare for all, cost, medicare | Elizabeth Warren: ...the choice. A broken system that leaves millions behind while costs keep going up and insurance companies keep sucking billions of dollars in profits out of the system – or, for about the... |
| S5 | Shared high-density | No | 766 | 284 | worked, elected, served, leadership, family | Lesley J. Lopez: Before that, I’ve worked in various communication roles, including the Congressional Hispanic Caucus and the National Immigration Forum where I fought to improve the lives of immigrant... |
| S6 | Shared high-density | No | 329 | 144 | school, education, student, teacher, funding | Erika Uyterhoeven: ...and labor unions in the inside-outside campaign that won the Student Opportunity Act and its $1.5 billion in new funding for public schools, targeted at special education, English... |

## Limits

This is a descriptive analysis of the recoverable corpus. Region labels summarize the text
actually present in each density area; they do not imply a complete nationwide census, causal
importance, or agreement merely because both groups occupy a shared region.
