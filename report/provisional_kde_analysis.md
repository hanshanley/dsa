# Provisional GTE KDE region analysis

The KDE contains **36613** passages after deduplicating repeated text
within each candidate and election year:
**12226** from DSA-endorsed candidates and
**24387** from other Democrats. Density estimation is performed in
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
| D1 | DSA-overrepresented | Yes | 680 | 114 | 0.91 | socialist, progressive, movement, political, electoral | Robert LeVertis Bell: ...campaigns, I saw in real time how people were deepening their political understanding, how people were becoming strong organizers, how people were and still are building something that is... |
| D2 | DSA-overrepresented | Yes | 341 | 74 | 0.78 | energy, climate, renewable, climate change, fossil | Jabari Brisport: Since the passage of the Climate Leadership and Community Protection Act (“CLCPA”) in 2019, New York State has not done nearly enough to combat climate change and invest in renewable energy... |
| D3 | DSA-overrepresented | No | 386 | 83 | 0.69 | housing, tenant, landlord, rent, eviction | Claire Valdez: Second: Housing as a human right: For far too long, real estate has had a stranglehold on New Y ork City, and the result has been the violent eviction and displacement of our Black and... |
| D4 | DSA-overrepresented | No | 251 | 52 | 0.74 | prison, bail, incarceration, sex, jail | Zohran Mamdani: I will also work to dismantle mass incarceration in New York by opposing the construction of new state prisons and jails, divesting from our $3 billion/year carceral system, and investing... |
| D5 | DSA-overrepresented | No | 67 | 22 | 0.98 | israel, palestinian, israeli, palestine, military | Claire Valdez: government has funded and supported Israel as it entrenches apartheid and military occupation across Palestine. |
| D6 | DSA-overrepresented | No | 70 | 42 | 0.97 | healthcare, single payer, universal, health, care | Jumaane Williams: I will work with our State leaders to resist health care cuts coming out of Washington and ensure that all New Yorkers are provided with affordable, universal, access to the care that they... |
| M1 | Other-Democrat-overrepresented | Yes | 3554 | 337 | 0.98 | housing, transit, resident, neighborhood, affordable housing | Gary Goodweather: ...I would closely monitor traffic, parking, public safety, and housing impacts on nearby neighborhoods to ensure the project does not negatively affect existing residents or accelerate... |
| M2 | Other-Democrat-overrepresented | Yes | 554 | 74 | 0.90 | food, reserve, farm, agricultural, agriculture | Chris Wilhelm: The agricultural reserve is one of the things that makes Montgomery County unique, so the county government should be supporting career pathways to promote agriculture and food service. |
| M3 | Other-Democrat-overrepresented | No | 783 | 139 | 0.97 | california, school, student, education, governor | Tim Myers: California’s vast, decentralized school system, with millions of students and billions of tax dollars, lacks the coordination and leadership needed to ensure that every student, regardless... |
| M4 | Other-Democrat-overrepresented | No | 117 | 41 | 0.89 | actblue, phone, donation, saved, express | Jordan Herrera: $5 $25 $50 $100 $250 Other If you’ve saved your payment with ActBlue Express, your donation will go through immediately. |
| M5 | Other-Democrat-overrepresented | No | 265 | 41 | 0.74 | trump, donald, america, american, nato | Richard Gonzalez: Nevertheless, Donald Trump is our president, and I respect the office and acknowledge his investiture by the American people through our country’s democratic process. |
| M6 | Other-Democrat-overrepresented | No | 120 | 53 | 0.87 | gun, guns, violence, check, weapon | Sol A. Flores: ...single most important action that Congress could take to curb gun violence would be to require universal background checks to ensure that guns do not get into the hands of criminals... |
| S1 | Shared high-density | Yes | 284 | 108 | 0.99 | council, june, interview, house, ballot | Maurice "Mo" Troop: He is one of eight Democrats and two Republicans seeking one of the four City Council seats on the ballot in the May 18 municipal primary. |
| S2 | Shared high-density | Yes | 91 | 24 | 0.97 | attorney, travis, case, prosecutor, criminal | Erin Martinson: As a prosecutor with the Travis County Attorney’s Office, I led the protective order division and transformed it into a statewide model for other offices. |
| S3 | Shared high-density | No | 89 | 47 | 0.96 | zoning, process, development, prerogative, aldermanic | Mueze Bawany: ...Alderman should have decision making authority about what development comes to their ward and what zoning changes are approved, however, I can also acknowledge that the history of... |
| S4 | Shared high-density | No | 272 | 157 | 0.91 | worked, grew, school, organizer, teacher | Marcela Mitaynes: I’ve lived in this district since I was a child-- I grew up here, an undocumented kid in an undocumented family, went to public schools here, raised my daughter here, and have been working... |
| S5 | Shared high-density | No | 178 | 94 | 0.99 | mississippi, party, senate, congress, matter | Jensen Bohren: On that unlikely scenario, we will continue to fight for Mississippi by running for Senate, either in our district or, depending on circumstances, in 2020. |
| S6 | Shared high-density | No | 262 | 142 | 0.80 | police, violence, public safety, gun, crime | Kenyan R. McDuffie: Public Safety & Justice Reform Established a public-health approach to violence prevention while strengthening police transparency, youth justice, and access to legal representation. |

## Limits

This is a descriptive analysis of the recoverable corpus. Region labels summarize the text
actually present in each density area; they do not imply a complete nationwide census, causal
importance, or agreement merely because both groups occupy a shared region.
