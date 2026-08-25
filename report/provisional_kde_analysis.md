# Provisional GTE KDE region analysis

The KDE contains **36657** passages after deduplicating repeated text
within each candidate and election year:
**12234** from DSA-endorsed candidates and
**24423** from other Democrats. Density estimation is performed in
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
- Each zone is first divided into six candidate subregions in the selected 10-dimensional
  semantic representation. Only the two subregions with the strongest combination of semantic
  coherence, textual support, and density-ratio strength are published.
- Terms are locally distinctive document-prevalence terms from the underlying subregion text.
  Examples are extractive source passages, not generated paraphrases.

| Region | Interpretation | Passages | Candidates | Distinctive terms | Representative source text |
| --- | --- | ---: | ---: | --- | --- |
| D1 | DSA-overrepresented | 314 | 76 | housing, tenant, landlord, rent, eviction | Claire Valdez: Second: Housing as a human right: For far too long, real estate has had a stranglehold on New Y ork City, and the result has been the violent eviction and displacement of our Black and... |
| D2 | DSA-overrepresented | 700 | 121 | socialist, think, really, i'm, progressive | Paul Prescod: Other kinds of movement, DSA, that broad coalition, I think that's a strength that I'm bringing to this, is having a foot firmly in the world of the left, progressive left broadly speaking... |
| M1 | Other-Democrat-overrepresented | 569 | 75 | food, reserve, farm, agricultural, agriculture | Chris Wilhelm: The agricultural reserve is one of the things that makes Montgomery County unique, so the county government should be supporting career pathways to promote agriculture and food service. |
| M2 | Other-Democrat-overrepresented | 2106 | 275 | housing, transit, affordable housing, transportation, development | Fatmata Barrie: ...Ride On routes and frequency as well as fight for public transportation fiscal notes to be added for new developments so we as county legislators are ensuring new housing and transit... |
| S1 | Shared high-density | 729 | 210 | school, student, education, tax, funding | Erika Uyterhoeven: ...and labor unions in the inside-outside campaign that won the Student Opportunity Act and its $1.5 billion in new funding for public schools, targeted at special education, English... |
| S2 | Shared high-density | 486 | 198 | police, violence, mental, crime, enforcement | JuanPablo Prieto: We do not want to overpolice our communities, instead we want to bring resources to combat the root of crime including food assistance, access to good paying jobs, and mental health... |

## Limits

This is a descriptive analysis of the recoverable corpus. Region labels summarize the text
actually present in each density area; they do not imply a complete nationwide census, causal
importance, or agreement merely because both groups occupy a shared region.
