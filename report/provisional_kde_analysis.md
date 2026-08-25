# Provisional GTE KDE region analysis

The KDE contains **38139** passages after deduplicating repeated text
within each candidate and election year:
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

| Region | Interpretation | Passages | Candidates | Distinctive terms | Representative source text |
| --- | --- | ---: | ---: | --- | --- |
| D1 | DSA-overrepresented | 2323 | 167 | energy, fuel, socialist, fossil, climate | Jabari Brisport: For both our planet and our communities, we must rapidly replace fossil fuels with clean renewable energy sources. |
| D2 | DSA-overrepresented | 840 | 124 | housing, prison, tenant, landlord, rent | Claire Valdez: Landlords have used algorithmic driven software like RealPage to collude with each other and raise rents across entire housing markets – costing tenants $3.8 billion nationwide in inflated... |
| O1 | Opponent-overrepresented | 4912 | 380 | housing, resident, school, development, council | Seth Grimes: Residents and businesses are looking for leaders who will tame development and rework planning processes, who will build the school capacity we lack and create the transportation solutions... |
| O2 | Opponent-overrepresented | 1461 | 108 | trump, donald, omar, harris, castro | Multi-candidate debate: HARRIS: First of all, Donald Trump came in making a whole lot of promises to working people that he did not keep. |
| S1 | Shared high-density | 2032 | 381 | tax, healthcare, cost, insurance, abortion | Ashley Hartmeier-Prigg: Affordability & Cost of Living: Expand affordable housing, lower health care and child care costs, and deliver tax relief for working families. |
| S2 | Shared high-density | 2736 | 513 | police, council, marijuana, public safety, diego | Byron Sigcho-Lopez: I will fight for additional reforms and oversight to restore public trust and prioritize public safety, including establishing the Civilian Police Accountability Council (CPAC). |

## Limits

This is a descriptive analysis of the recoverable corpus. Region labels summarize the text
actually present in each density area; they do not imply a complete nationwide census, causal
importance, or agreement merely because both groups occupy a shared region.
