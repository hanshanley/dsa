# Provisional GTE KDE region analysis

The KDE contains **2825** passages after deduplicating repeated text
within each candidate and election year:
**989** from DSA-endorsed candidates and
**1836** from other Democrats. Density estimation is performed in
**5 dimensions**; the two-dimensional map is used only for
visualization.

![Labeled KDE regions](../figures/provisional_gte_kde.png)

## Interpreting the labeled regions

- **D regions** are spatial groupings among DSA-endorsed segments above the endorsed-group
  upper-quartile density-ratio cutoff.
- **M regions** are semantically coherent groupings among other-Democrat passages below that
  group's lower-quartile density-ratio cutoff.
- **S regions** are high-joint-density areas with small absolute density differences. They
  represent semantic overlap, not proof of identical positions.
- HDBSCAN identifies variable-shape clusters in the selected 5-dimensional UMAP representation
  (`min_cluster_size=60`, `min_samples=10`, Euclidean metric, EOM selection). Noise points remain
  unassigned. The table retains up to six substantive, sufficiently supported regions per zone;
  the map displays the top two per category to remain legible.
- Terms are locally distinctive document-prevalence terms from the underlying subregion text.
  Examples are extractive source passages, not generated paraphrases.

| Region | Interpretation | On map | Passages | Candidates | HDBSCAN confidence | Distinctive terms | Representative source text |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| D1 | DSA-overrepresented | Yes | 93 | 21 | 0.91 | worker, wage, employer, union, labor | Kareem Kandil: ...rate of compensation for public works projects, a prevailing wage works to stop union shops from being underbid for their work and helps all workers receive an adequate wage for their... |
| D2 | DSA-overrepresented | Yes | 152 | 21 | 0.70 | tenant, yorker, housing, landlord, home | Claire Valdez: The Housing Access Voucher Program will provide the most vulnerable New Yorkers – including low-income families facing eviction, unhoused people, or those facing a loss of housing due to... |
| S1 | Shared high-density | Yes | 200 | 63 | 1.00 | school, education, council, bike, student | Shahana K. Hanif: Investing in public schools will require an overhaul of NYC’s education system: a system which continues to segregate students, abandons those with learning and physical disabilities... |

## Limits

This is a descriptive analysis of the recoverable corpus. Region labels summarize the text
actually present in each density area; they do not imply a complete nationwide census, causal
importance, or agreement merely because both groups occupy a shared region.
Names, places, source formats, offices, and election years can influence these language regions.
Round-robin sampling limits concentration only when the fitting cap is reached; it does not
give candidates equal density weight. A category with no retained region is not evidence that
those candidates lack distinctive policies.
