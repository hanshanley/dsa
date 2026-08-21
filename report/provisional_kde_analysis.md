# Provisional GTE KDE region analysis

The KDE contains **38139** candidate/cycle-deduplicated segments:
**12650** from DSA-endorsed candidates and
**25489** from opponents. Density estimation is performed in
**10 dimensions**; the two-dimensional map is used only for
visualization.

![Labeled KDE regions](../figures/provisional_gte_kde.png)

## Interpreting the labeled regions

- **D regions** are spatial groupings among DSA-endorsed segments above the endorsed-group
  upper-quartile density-ratio cutoff.
- **O regions** are spatial groupings among opponent segments below the opponent-group
  lower-quartile cutoff.
- **S regions** are high-joint-density areas with small absolute density differences. They
  represent semantic overlap, not proof of identical positions.
- Terms are locally distinctive document-prevalence terms from the underlying region text.
  Examples are extractive source passages, not generated paraphrases.

| Region | Interpretation | Segments | Candidate/cycles | Distinctive terms | Representative source text |
| --- | --- | ---: | ---: | --- | --- |
| D1 | DSA-overrepresented | 2323 | 187 | energy, fuel, socialist, fossil, climate | Marguerite Green: I think that we have to remember that this is why people are hesitant to change—they’re worried about jobs, and we have to be priori... |
| D2 | DSA-overrepresented | 840 | 139 | housing, prison, tenant, landlord, rent | Claire Valdez: Claire supports returning to that model, allowing localities to set rent adjustments based on local housing data, and legislation th... |
| O1 | Opponent-overrepresented | 4912 | 386 | housing, resident, school, development, council | Seth Grimes: Residents and businesses are looking for leaders who will tame development and rework planning processes, who will build the school... |
| O2 | Opponent-overrepresented | 1461 | 108 | trump, donald, bash, omar, country | Cory Booker: (APPLAUSE) GABBARD: Donald Trump won this election because far too many people in this country felt like they'd been left behind by... |
| S1 | Shared high-density | 2032 | 393 | tax, healthcare, cost, insurance, abortion | Ky Fireside: To the extent we can create an orderly way of handling health care so people know what is available to them and providers and insura... |
| S2 | Shared high-density | 2736 | 536 | police, council, contact, seat, mayor | Seth Anderson-Oberman: In October, 2022, the City Controller's office, on the request of City Council, authored a withering analysis of Philadelphia Police... |

## Limits

This is a descriptive analysis of the recoverable corpus. Region labels summarize the text
actually present in each density area; they do not imply a complete nationwide census, causal
importance, or agreement merely because both groups occupy a shared region.
