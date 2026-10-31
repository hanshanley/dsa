# National platforms: claim-based analysis

<!-- learned-topics:start -->
## Learned topic distributions and relative emphasis

**24 learned topics; 0 unclustered claims. 24/24 named labels available.**

**21 topics shown.** The three party-identity clusters are omitted from substantive charts, rankings and topic summaries. Their claims remain in all denominators; the remaining topics are not renormalized. Original assignments and all reviewed labels remain in the reproducibility downloads.

**Where these names came from:** cached claim embeddings were reduced with PCA and clustered together across the expanded corpus. Weighted K-means selected the pooled clusters after the density-fit coverage check. Local Gemma proposed names using distinctive keywords and bounded representative-claim packets; source-bound assistant review revised misleading names. They are not CAP's predefined policy categories and do not establish shared policy positions.

One shared expanded-corpus taxonomy is used for both views. Shares give each document/fallback bundle equal weight within its organization, including unclustered claims in the denominator. The reference for each group is the equally weighted mean of the other groups, not the larger pooled claim corpus.

Log2 ratios use a 0.0001 share floor: +1 is approximately twice the topic share away from the floor. All contrasts remain ranked, including fragile ones. Zero shares, low bundle support, smoothing sensitivity and leave-one-bundle-out instability are warnings, not grounds for silent exclusion. These are exploratory language-emphasis differences, not agreement, significance, or ideological distance.

Discovery uses PCA with **weighted_kmeans**. Low density-cluster coverage triggers a weighted K-means fallback; K-means gives each group equal mass and each within-group bundle equal mass. HDBSCAN itself is unweighted. Parameter and balanced-refit diagnostics are downloaded. K-means partitions claims even at fuzzy topic boundaries; topics can mix subtopics and opposing positions. Period/genre composition differs. Model summaries are evidence-bound interpretations, not independently certified classifications or fact-checks.

[All shares](../data/analysis/national_claims/full/topics/shares.csv) · [All ranked contrasts and warnings](../data/analysis/national_claims/full/topics/contrasts.csv) · [Topic assignments](../data/analysis/national_claims/full/topics/assignments.csv) · [Representative claims and exact source evidence](../data/analysis/national_claims/full/topics/representatives.csv) · [Fit diagnostics](../data/analysis/national_claims/full/topics/candidate_fits.csv) · [Balanced refits](../data/analysis/national_claims/full/topics/balanced_refits.csv)

**Label evidence review:** 24/24 topics reviewed against their actual representative claims; 13 labels have explicitly identified source-bound assistant revisions. Original Gemma replies and validation failures remain unchanged. This is assistant review, not independent human certification.

[Label review and exact provenance](../data/analysis/national_claims/full/topics/label_review.json)

**Measured fit limitations:** PCA retains 59.9% of embedding variance; original-space cosine silhouette is 0.058. Balanced-refit adjusted Rand indices are 0.628, 0.606 (1 would mean identical partitions). These are exploratory topic partitions; separation and refit diagnostics do not certify a definitive policy taxonomy.

### Cluster maps with individualized group positions

One large atlas combines all three groups; three further atlases compare each pair. Each shows all 21 substantive pooled clusters, with separately reviewed position summaries and explicit documented differences. These use the expanded corpus only. The frozen clusters are projected onto the saved expanded display, not refitted in 2D.

The combined map colors claims by organization. Pairwise map colors show the unsmoothed weighted **topic-share gap**, not KDE density or policy distance. Numbered markers locate weighted projected topic centres, not boundaries. All original denominators and all 24 assignments remain in downloads.

**Review scope:** Source-bound assistant synthesis of bundle-diverse examples, not independent human certification or an exhaustive stance classification. Statements describe the observed documents across years, not every member's beliefs or a current consensus. The packet selection cycles across bundles, including central and peripheral claims; it is not a random sample or exhaustive coding of all within-topic policy positions. Contradictions and scope cautions are retained below. Read the sources before describing a present-day group belief.

**All three groups**

![All three groups: clusters and stated positions](../figures/national_claims/full/topics/positions/all_groups.png)

[Full-resolution PNG](../figures/national_claims/full/topics/positions/all_groups.png)

**Democratic and Republican**

![Democratic and Republican: clusters and stated positions](../figures/national_claims/full/topics/positions/democratic_vs_republican.png)

[Full-resolution PNG](../figures/national_claims/full/topics/positions/democratic_vs_republican.png)

**Democratic and DSA**

![Democratic and DSA: clusters and stated positions](../figures/national_claims/full/topics/positions/democratic_vs_dsa.png)

[Full-resolution PNG](../figures/national_claims/full/topics/positions/democratic_vs_dsa.png)

**Republican and DSA**

![Republican and DSA: clusters and stated positions](../figures/national_claims/full/topics/positions/republican_vs_dsa.png)

[Full-resolution PNG](../figures/national_claims/full/topics/positions/republican_vs_dsa.png)

[Full position review](../data/analysis/national_claims/full/topics/positions/group_positions.json) / [All sampled claims and source evidence](../data/analysis/national_claims/full/topics/positions/evidence.csv)

#### Position cluster 1: Energy, Infrastructure, and Economic Development

**Democratic:** Documents support clean-energy investment, resilient infrastructure, climate regulation, renewable incentives, and ending oil-and-gas subsidies, alongside broader rural, housing, manufacturing, trade, and worker-investment proposals.
Scope caution: This broad bucket also contains unrelated economic proposals and retrospective administration claims.
- Commitment to invest in advanced energy technologies to build the clean energy economy and create millions of new, good “Green Collar” American jobs. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 130268:131484; `democratic-2008-normalized-3b4380265be8-006`)
- Commitment to incentivize wind, solar, and other renewable energy over the development of new natural gas power plants. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 92328:92834; `democratic-2016-normalized-68c57aa9b811-011`)
- Commitment to upgrade and make resilient energy, water, wastewater, and transportation infrastructure. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 149910:151357; `democratic-2020-normalized-9ec56284fa6b-008`)
- Commitment to eliminate tens of billions of dollars in subsidies for oil and gas companies. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 42913:43499; `democratic-2024-normalized-92fa6cad93aa-003`)

**Republican:** Documents support domestic energy supply and independence through markets, fossil fuels, nuclear power, and pipelines, while earlier texts also endorse renewables, efficiency, and climate-risk responses.
Scope caution: Energy sources and climate framing vary across years; the bucket also includes trade and general growth claims.
- Commitment to meeting the challenge of long-term global climate change by relying on markets and new technologies to improve energy efficiency. ([2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform); 2004; scoped characters 219327:219736; `republican-2004-normalized-53cdfe529adc-008`)
- Commitment to pursue dramatic increases in the use of all forms of safe, affordable, reliable, and clean nuclear power. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 93211:93916; `republican-2008-normalized-d092c115d3e5-006`)
- Commitment to approve the Keystone XL Pipeline and to streamline permitting for the development of other oil and natural gas pipelines. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 67887:68398; `republican-2012-normalized-a941803afe27-003`)
- Commitment to end market-distorting restrictions on oil, natural gas, and coal. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 15857:16203; `republican-2024-normalized-007a594371a0-012`)

**DSA:** Documents support Green New Deal programs, rapid fossil-fuel phaseout, massive public investment, and public or social ownership of energy, transit, infrastructure, and major industry.
Scope caution: Fallback documents also include broad economic restructuring, organizational, and unrelated movement claims.
- Support for social ownership of all major industry and infrastructure. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 23410:23467; `dsa-2021-adopted-normalized-067c1b4d0c0e-011`)
- Support for public ownership over major transportation and energy infrastructure and natural resources. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 7352:8203; `dsa-2024-program-normalized-f23d4047d972-013`)
- Support for phasing out the use of fossil fuels. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 5915:7099; `dsa-2026-program-normalized-cc87289e0395-029`)
- Commitment to fight to restructure the U.S. economy in a democratic direction. ([2009 convention national priorities resolution](https://dlarchive.dsausa.org/wp-content/uploads/2018/12/DL_2010_V037_03.pdf); 2009; scoped characters 1653:3096; `dsa-2009-priorities-normalized-69ef366c0cec-004`)

**Pairwise distinctions:**
- Democratic / Republican: Democratic documents emphasize clean public investment and renewable incentives; Republican documents emphasize market-led supply, pipelines, and fossil-energy expansion, despite earlier climate and renewable provisions.
- Democratic / DSA: Both support clean-energy transition; Democratic documents use regulation, incentives, and investment, while DSA documents call for fossil-fuel phaseout and public or social ownership.
- Republican / DSA: Republican documents favor market-led domestic production including fossil fuels and pipelines; DSA documents favor public ownership, massive public investment, and phasing out fossil fuels.

#### Position cluster 2: Community and Economic Support for Vulnerable Populations

**Democratic:** Documents support targeted federal investment, Medicaid and community-based services, affordable housing, mental-health and substance-use treatment, and assistance for veterans, disabled people, low-income communities, and returning citizens.
Scope caution: The broad packet includes unrelated security, technology, trade, and environmental claims.
- Support for strengthening Medicaid for families. ([2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform); 2004; scoped characters 80669:80875; `democratic-2004-normalized-cbac9887f90d-002`)
- Commitment to help lift people with disabilities out of poverty. ([2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); 2012; scoped characters 100171:101045; `democratic-2012-normalized-c23a3db91fb4-005`)
- Commitment to make investments in building the capacity of the Medicaid system to provide home and community-based services. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 85900:87271; `democratic-2020-normalized-7c42c0046338-005`)
- Commitment to boost access to transitional housing, affordable housing, mental health and substance use treatment to help returning citizens succeed upon their release. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 124205:125155; `democratic-2024-normalized-e7f0490f5d0f-006`)

**Republican:** Documents support safety-net delivery through public-private or local partnerships, training and self-sufficiency services, homeownership, and targeted aid for veterans, Native communities, foster families, low-income families, and seniors.
Scope caution: The packet mixes social support with policing, regulatory relief, administration, and stray factual records.
- Commitment to establish stronger public-private partnerships for safety net providers and hospitals in rural and underserved communities. ([2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform); 2000; scoped characters 92920:93402; `republican-2000-normalized-76e7e2418f31-008`)
- Support for offering training, transportation, and child care services to help people become self-sufficient. ([2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform); 2004; scoped characters 251901:252254; `republican-2004-normalized-8eb776d9223a-009`)
- Support for continued improvement of early childhood programs, such as Head Start, for low-income families. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 122717:123192; `republican-2008-normalized-f944b52cd2a1-007`)
- Commitment to support Policies that help Seniors remain in their homes and maintain Financial Security. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 21860:22119; `republican-2024-normalized-639254060a0e-009`)

**DSA:** Documents support social housing and rent control, expanded public resources and Social Security, emergency shelter and cash aid, community public safety, and investment in neglected communities.
Scope caution: Many fallback examples concern organizational capacity or unrelated factual material rather than social provision.
- Support for defending and expanding Social Security. ([An Economic Justice Agenda - adopted November 2007](https://www.dsausa.org/wp-json/wp/v2/strategy/612); 2012-12-23; scoped characters 21183:21216; `dsa-2007-economic-justice-normalized-500c699fb1db-001`)
- Support for erecting emergency shelters, complete with healthcare and food, for the unhoused, domestic violence survivors, and college students. ([Now is the Time for Solidarity: DSA National Statement on COVID-2019/Es la hora de solidaridad: Comunicación nacional de DSA acerca de COVID-19](https://www.dsausa.org/wp-json/wp/v2/statement/4626); 2020-03-12; scoped characters 5147:6138; `dsa-statement-4626-normalized-5e02e4c93b6d-008`)
- Support for establishing universal rent-control. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 6467:7350; `dsa-2024-program-normalized-b789b4710c28-009`)
- Support for massively investing in good jobs, quality housing and infrastructure in neglected minority communities. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 4779:5913; `dsa-2026-program-normalized-3ba469ba4e69-019`)

**Pairwise distinctions:**
- Democratic / Republican: Democratic documents emphasize federal funding and service expansion; Republican documents pair targeted benefits with public-private partnerships, self-sufficiency services, homeownership, and locally administered poverty responses.
- Democratic / DSA: Democratic documents expand targeted programs and community services; DSA documents add universal rent control, public social housing, direct emergency aid, and preservation of working-poor programs.
- Republican / DSA: Republican documents emphasize targeted assistance, partnerships, and self-sufficiency; DSA documents emphasize public social housing, rent control, direct aid, and expanded collective provision.

#### Position cluster 3: Labor Rights and Unionization

**Democratic:** Documents support easier union organizing and collective bargaining, stronger labor-law enforcement, strike protections, expanded rights for excluded workers, higher minimum wages, overtime protections, and labor standards in trade.
Scope caution: Several examples are retrospective achievements or worker-related facts rather than new policy commitments.
- Support for reforming labor laws to protect the rights of workers, including public employees, to bargain contracts and organize on a level playing field without interference. ([2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform); 2004; scoped characters 64881:65517; `democratic-2004-normalized-f23414e33192-006`)
- Commitment to fight to ban the permanent replacement of striking workers, so that workers can stand up for themselves without worrying about losing their livelihoods. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 27669:29134; `democratic-2008-normalized-dd4bcb4c56df-011`)
- Commitment to restore and protect workers' rights to organize and bargain collectively. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 151965:153106; `democratic-2020-normalized-fc967cb6cbce-003`)
- Support for codifying a right to organize for domestic workers, farm workers, and other unprotected laborers. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 18243:19386; `democratic-2024-normalized-8af3eb44deaa-005`)

**Republican:** Documents affirm voluntary union participation while supporting state or national right-to-work laws, union financial disclosure, repeal of Davis-Bacon, employer flexibility, workforce training, and selected worker protections.
Scope caution: The packet combines labor policy with retirement, welfare, immigration verification, and civil-service claims.
- Affirmation of the right of individuals to voluntarily participate in labor organizations and to bargain collectively. ([2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform); 2000; scoped characters 65540:66210; `republican-2000-normalized-5bbdd676d52d-001`)
- Affirmation of both the right of individuals to voluntarily participate in labor organizations and bargain collectively and the right of states to enact Right-to-Work laws. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 81300:81949; `republican-2008-normalized-5b0f314c5424-001`)
- Support the enactment of a National Right-to-Work law to promote worker freedom and greater economic liberty. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 35273:36184; `republican-2012-normalized-9b00c73c5686-008`)
- Support for repeal of the Davis-Bacon law, which limits employment and drives up construction and maintenance costs for the benefit of unions. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 23432:24172; `republican-2016-normalized-1a84c35198a9-008`)

**DSA:** Documents support broad rights to organize, bargain, and strike; labor-law reform and enforcement; union democratization; living wages; worker ownership; job guarantees; and protections regardless of industry or immigration status.
Scope caution: Fallback material includes factual descriptions and adjacent employment, pension, and unemployment policies.
- Support for strengthening labor’s power in the marketplace by guaranteeing a true right to organize and to bargain collectively. ([An Economic Justice Agenda - adopted November 2007](https://www.dsausa.org/wp-json/wp/v2/strategy/612); 2012-12-23; scoped characters 11788:12343; `dsa-2007-economic-justice-normalized-43ac027d547d-001`)
- Support for continuing to work with labor and its allies to pass meaningful labor law reform that would restore a real right to organize and strike and ensure that the NLRB enforces these laws. ([2009 convention national priorities resolution](https://dlarchive.dsausa.org/wp-content/uploads/2018/12/DL_2010_V037_03.pdf); 2009; scoped characters 3097:4220; `dsa-2009-priorities-normalized-7fbe4754d605-004`)
- Support for protecting all workers’ rights to strike and form a union. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 7352:8203; `dsa-2024-program-normalized-f23d4047d972-002`)
- Support for union members who organize reform caucuses, democratize their unions, and take political action. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 9334:9953; `dsa-2026-program-normalized-f85f1b0f20e0-005`)

**Pairwise distinctions:**
- Democratic / Republican: Democratic documents seek easier organizing and stronger bargaining and strike protections; Republican documents preserve voluntary unionism while advancing right-to-work, union disclosure, and Davis-Bacon repeal.
- Democratic / DSA: Both support organizing and bargaining rights; DSA documents additionally emphasize universal strike rights, union democratization, worker ownership, and a federal jobs guarantee.
- Republican / DSA: Republican documents emphasize voluntary unionism and right-to-work restrictions; DSA documents seek expansive organizing and strike rights, stronger enforcement, and democratic unions.

#### Position cluster 4: Economic Growth and Development Narratives

**Democratic:** Documents assert that clean-energy, infrastructure, education, housing, small-business, and middle-class investments generate jobs and prosperity, while minimum-wage and equal-pay policies reduce poverty.
Scope caution: This narrative bucket mixes predictions, causal assertions, retrospective achievements, and unrelated records; outcomes were not fact-checked.
- A more energy efficient economy will gain a competitive edge for new manufacturing and jobs that stay in the United States. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 39298:40246; `democratic-2008-normalized-225b92127bb1-006`)
- Supporting small business and entrepreneurship can grow jobs faster in America. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 30246:31317; `democratic-2016-normalized-e54a859b456a-002`)
- Evidence-based investments in jobs, housing, education, and the arts will make the nation more prosperous. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 106051:106506; `democratic-2020-normalized-11c6d091feaf-027`)
- Raising the minimum wage to $15 an hour and guaranteeing equal pay for women will pull millions of families out of poverty. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 64422:65058; `democratic-2020-normalized-5956fd15c018-010`)

**Republican:** Documents attribute growth and jobs to tax cuts, deregulation, free trade, technology, private-sector expansion, abundant domestic energy, and energy exports, often presenting prosperity as enabling other goals.
Scope caution: These are document assertions and predictions, not verified effects; the packet includes stray facts and credits.
- Cutting tax rates, simplifying the tax code, deregulating industries, and opening world markets to American enterprise resulted in tremendous growth in the 1980s. ([2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform); 2000; scoped characters 6170:6843; `republican-2000-normalized-79e5ffd6ad69-015`)
- Economic growth supported by free trade and free markets creates new jobs and higher incomes. ([2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform); 2004; scoped characters 66567:66961; `republican-2004-normalized-d0360dc943ed-011`)
- Reducing regulation encourages business formation and job creation. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 6970:8207; `republican-2012-normalized-5a227161d13d-005`)
- Energy exports will grow the United States' economy. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 85433:86102; `republican-2016-normalized-cffadfbf3490-006`)

**DSA:** Documents portray growth as unequally distributed and link sustainable prosperity to public infrastructure, decarbonization, public banking, social programs, green union jobs, and reduced military spending.
Scope caution: The packet is heavily narrative, mixing policy, criticism, history, predictions, and unverified causal assertions.
- The great economic expansion of the last decade primarily benefited the well off. ([2001 convention national priorities resolution](https://www.dsausa.org/files/2019/07/DL-2001-Convention-Coverage.pdf); 2002; scoped characters 525:1792; `dsa-2001-convention-priorities-normalized-f35a6ece882e-007`)
- The United States economy can be restructured in an ecologically sustainable direction and one that provides good jobs at good wages only if the federal government invests significantly in infrastructure development, alternative energy, and mass-transit technologies. ([2009 convention national priorities resolution](https://dlarchive.dsausa.org/wp-content/uploads/2018/12/DL_2010_V037_03.pdf); 2009; scoped characters 5541:6944; `dsa-2009-priorities-normalized-e439cbeb16b4-003`)
- The “trickle down” philosophy has never yielded a significant increase in investment but has led to major gains in corporate profits. ([Drain the Swamp: Defeat the Trump Tax Cuts](https://www.dsausa.org/wp-json/wp/v2/statement/404); 2017-11-27; scoped characters 950:2047; `dsa-statement-404-normalized-d6649fb869e5-008`)
- The unified, democratic, and public banking system will provide stagnant and de-industrialized areas with long-term, dependable access to loans for the productive sectors of the economy with a focus on manufacturing co-operatives and the green transition. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 30034:30233; `dsa-2021-adopted-normalized-29ef349cf189-003`)

**Pairwise distinctions:**
- Democratic / Republican: Democratic documents link public and clean-energy investment and wage gains to prosperity; Republican documents stress tax cuts, deregulation, trade, private enterprise, and domestic energy.
- Democratic / DSA: Both connect green investment with jobs; Democratic documents emphasize broad investment-led growth, while DSA documents foreground unequal gains, public ownership, decarbonization, and unionized green employment.
- Republican / DSA: Republican documents credit market liberalization and energy production for growth; DSA documents criticize unequal and trickle-down growth and prescribe public investment, decarbonization, and social provision.

#### Position cluster 5: Rights, Freedoms, and Governmental Legitimacy

**Democratic:** Documents support human and civil rights, rule-governed and impartial institutions, equal treatment, political self-determination, Tribal sovereignty and treaty obligations, and balancing religious freedom with other civil rights.
Scope caution: This broad principles bucket includes unrelated policy, institutional, and factual statements.
- Commitment to continue to press for human rights, the rule of law, and political freedom. ([2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); 2000; scoped characters 147542:148412; `democratic-2000-normalized-93fadee8da59-006`)
- Support for the administration of justice to be fair and impartial. ([2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); 2012; scoped characters 102714:103551; `democratic-2012-normalized-a10b8a8482df-005`)
- Commitment to advance the ability of all persons to live with dignity, security, and respect, regardless of who they are or who they love. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 257854:258637; `democratic-2020-normalized-33dbf90bb2e3-001`)
- Commitment to continue to honor both religious freedom and other civil rights, not put them at war with one another. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 186917:187231; `democratic-2024-normalized-1e0b4a5c659c-009`)

**Republican:** Documents describe rights as inherent or God-given and government as their protector, while supporting religious liberty, state and local authority, due process, Tribal relations, and individual responsibility.
Scope caution: The packet does not establish one comprehensive constitutional theory and includes unrelated factual and programmatic claims.
- Rights inhere in individuals, not in groups. ([2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform); 2000; scoped characters 59045:59466; `republican-2000-normalized-bf4d1857ffda-006`)
- Government does not confer rights to life, liberty, and property, but is instituted by men to protect the rights that man already possesses. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 52431:52879; `republican-2008-normalized-92a9f5c7906a-006`)
- Everyone's due process and civil rights must be safeguarded. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 123472:123898; `republican-2016-normalized-b45c1b90580b-004`)
- The First Amendment Right to Religious Liberty protects the Right to act in accordance with those Beliefs, not just in places of Worship, but in everyday life. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 30155:30786; `republican-2024-normalized-8da9a39b9f7f-003`)

**DSA:** Documents support self-determination and decolonization, Indigenous sovereignty and treaties, social and economic rights to housing and care, equal civic participation, and community-controlled justice.
Scope caution: Fallback examples mix principles, predictions, foreign conflicts, organizing strategy, and descriptive claims.
- A series of basic human social and economic rights are detailed whose implementation would help to achieve freedom and dignity for all. ([A Social and Economic Bill of Rights](https://www.dsausa.org/wp-json/wp/v2/strategy/617); 2012-12-23; scoped characters 3013:3524; `dsa-2010-social-economic-rights-normalized-b43e2bacee7b-005`)
- A truly democratic, community-controlled justice system should promote peace and healing, not arbitrary, self-perpetuating violence. ([The System Is Not Broken, It Is Working As Designed](https://www.dsausa.org/wp-json/wp/v2/statement/399); 2017-06-27; scoped characters 3354:3665; `dsa-statement-399-normalized-c97e71412451-004`)
- Support for self-determination for all oppressed people. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 17354:17741; `dsa-2021-adopted-normalized-3a5ba8ba26bb-001`)
- Honor tribal sovereignty. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 4779:5913; `dsa-2026-program-normalized-3ba469ba4e69-repair-75f4dcce5dbb-003`)

**Pairwise distinctions:**
- Democratic / Republican: Democratic documents stress equal treatment, civil rights, and institutional impartiality; Republican documents stress pre-existing individual rights, religious exercise, limited governmental intrusion, and state authority.
- Democratic / DSA: Both support civil equality and Indigenous sovereignty; DSA documents additionally frame housing, care, and social provision as rights and emphasize decolonization and community-controlled justice.
- Republican / DSA: Republican documents foreground inherent individual and religious rights protected by government; DSA documents foreground social-economic rights, collective self-determination, Indigenous sovereignty, and decolonization.

#### Position cluster 6: American Leadership and National-Power Narratives

**Democratic:** Documents portray U.S. leadership as drawing on alliances, international institutions, diplomacy, democracy, innovation, economic strength, and military capability, with American security and prosperity reinforced by strong partners.
Scope caution: This narrative bucket includes retrospective achievements, patriotic language, and unrelated domestic facts.
- The United States shares its deepest values with democracies. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 109102:109568; `democratic-2008-normalized-9444e34d73ce-004`)
- The United States is stronger when it has its allies at its side. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 165663:166275; `democratic-2016-normalized-c9e0fc219fb0-016`)
- Belief that American security and prosperity are enhanced when the United States leads in shaping the rules, forging the agreements, and steering the institutions that guide international relations. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 231499:232144; `democratic-2020-normalized-41964e67e6c4-006`)
- The United States is strongest when its partners are strong. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 232787:233374; `democratic-2024-normalized-306753327989-006`)

**Republican:** Documents portray America as exceptionally strong and freedom-leading, linking global influence to military and economic power, alliances, diplomacy, domestic manufacturing, energy resources, innovation, and national unity.
Scope caution: The packet mixes policy, aspiration, patriotic characterization, historical claims, and stray geographic or editorial records.
- America is preserving the peace by working with more than 80 allied nations and international institutions to isolate and confront terrorists and outlaw regimes. ([2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform); 2004; scoped characters 14536:15292; `republican-2004-normalized-76b5fb08ee36-004`)
- America's diplomatic abilities must be an integral part of America's national security system. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 22133:22666; `republican-2008-normalized-e390325d5783-014`)
- In an American century, America will have the strongest economy and the strongest military in the world. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 151956:152467; `republican-2012-normalized-7815bee1d725-005`)
- If the United States does not have Domestic Manufacturing with low Inflation, not only will the U.S. Economy—and even U.S. Military Equipment and Supplies—be at the mercy of Foreign Nations, but U.S. Towns, Communities, and People cannot thrive. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 3760:4324; `republican-2024-normalized-a2d535d470e7-001`)

**DSA:** Documents criticize U.S. military dominance, territorial control, intervention, and corporate-state power while supporting territorial and Indigenous sovereignty, noninterference, reduced imperial spending, and redirected domestic investment.
Scope caution: Many examples are fallback factual accusations or historical narratives rather than direct policy positions.
- The United States today spends more on its armed forces than does the rest of the world combined. ([An Economic Justice Agenda - adopted November 2007](https://www.dsausa.org/wp-json/wp/v2/strategy/612); 2012-12-23; scoped characters 3286:3751; `dsa-2007-economic-justice-normalized-53bb7ce424c7-006`)
- The US has a long and bloody track record of actions to maintain US imperial dominance in the region. ([DSA Statement on Venezuela](https://www.dsausa.org/wp-json/wp/v2/statement/1492); 2019-01-24; scoped characters 67:717; `dsa-statement-1492-normalized-373728069d3c-004`)
- Support for self-determination and full sovereignty for Hawai’i, Puerto Rico, Amerika Sāmoa (American Samoa), Guåhån (Guam), Northern Mariana Islands, Virgin Islands, and for all indigenous nations whose ancestral lands are within current US borders. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 62873:63259; `dsa-2021-adopted-normalized-5589a830d2a3-003`)
- People worldwide deserve to live without U.S. interference. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 7145:8285; `dsa-2026-program-normalized-40060dd6f6dd-repair-d40710b9eecc-005`)

**Pairwise distinctions:**
- Democratic / Republican: Both portray U.S. leadership through strength and alliances; Democratic documents emphasize rules and institutions, while Republican documents more explicitly foreground supremacy, patriotism, manufacturing, and energy.
- Democratic / DSA: Democratic documents endorse alliance- and institution-based U.S. leadership; DSA documents challenge U.S. territorial control and intervention and call for sovereignty and noninterference.
- Republican / DSA: Republican documents celebrate American power and freedom-leading influence; DSA documents describe imperial dominance and military overreach and support territorial independence and reduced U.S. interference.

#### Position cluster 7: Immigration Policy: Reform, Enforcement, and Detention

**Democratic:** Documents combine border security and targeted enforcement with comprehensive reform, pathways to citizenship, protected asylum and family unity, expanded legal immigration, due process, and more humane detention and naturalization processes.
Scope caution: Enforcement, legalization, detention, and administrative emphases vary across years in this mixed bucket.
- Commitment to improve security at borders and entry-points to block individuals and weapons that would harm the United States. ([2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform); 2004; scoped characters 48574:48976; `democratic-2004-normalized-03b3f8c96731-005`)
- The Department of Homeland Security is prioritizing the deportation of criminals who endanger communities over the deportation of immigrants who do not pose a threat, such as children who came here through no fault of their own and are pursuing an education. ([2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); 2012; scoped characters 66775:67885; `democratic-2012-normalized-8c2f2e66c5fc-005`)
- All detention centers will provide access to competent interpreters who speak migrants' native languages and dialects. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 196963:198034; `democratic-2020-normalized-d3bd0e54948d-005`)
- Legislation must secure the border, reform the asylum system, expand legal immigration, and keep families together by supporting a pathway for long-term undocumented individuals. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 196661:197050; `democratic-2024-normalized-213ea50d0c93-002`)

**Republican:** Documents welcome legal immigration and sometimes citizenship while prioritizing border security, enforcement, removal, detention, penalties, screening, limits on family migration, and merit-based admission.
Scope caution: Proposals shift across years, with later packets containing stronger deportation and enforcement language; several examples are unrelated.
- Support for reforming the immigration system to ensure that it is legal, safe, orderly and humane. ([2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform); 2004; scoped characters 247583:248711; `republican-2004-normalized-c4dde1b37f8c-001`)
- Support for assisting the journey of legally present newcomers to full citizenship. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 104800:105396; `republican-2012-normalized-40fe6a061706-003`)
- Support for building a wall along the southern border and protecting all ports of entry. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 108141:109480; `republican-2016-normalized-3d9e76db88bb-001`)
- Commitment to prioritize merit-based immigration, ensuring those admitted to the United States contribute positively to U.S. society and economy, and never become a drain on public resources. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 14099:14347; `republican-2024-normalized-048e2be2d61f-009`)

**DSA:** Documents support ending detention and deportations, abolishing ICE, demilitarizing the border, protecting asylum, immediate amnesty or citizenship pathways, broader legal migration, and immigrant access to jobs and services.
Scope caution: Fallback documents include bill commentary and migration-system critiques, but selected policy direction is consistent across periods.
- Support for passing comprehensive immigration reform legislation that grants immediate permanent resident status to undocumented workers currently in the United States and establishes an expeditious and non-punitive road to citizenship for these workers and their families. ([An Economic Justice Agenda - adopted November 2007](https://www.dsausa.org/wp-json/wp/v2/strategy/612); 2012-12-23; scoped characters 27998:29403; `dsa-2007-economic-justice-normalized-3a71f1b7e983-006`)
- Support for demilitarizing the border and ending all immigrant detention and abolishing ICE. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 65000:65071; `dsa-2021-adopted-normalized-7a7bd5c278de-002`)
- Support for immediate amnesty for all immigrants regardless of current immigration status. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 8205:9248; `dsa-2024-program-normalized-9d88be1f8868-017`)
- End U.S. Immigration and Customs Enforcement detention and deportations. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 7145:8285; `dsa-2026-program-normalized-40060dd6f6dd-repair-d40710b9eecc-007`)

**Pairwise distinctions:**
- Democratic / Republican: Both include legal immigration and border management; Democratic documents pair enforcement with legalization and humane process, while Republican documents emphasize removal, detention, penalties, and admission limits.
- Democratic / DSA: Democratic documents retain border enforcement and prioritized deportation within legalization reforms; DSA documents call for ending deportations and detention, abolishing ICE, and demilitarizing borders.
- Republican / DSA: Republican documents prioritize border enforcement, detention, deportation, and merit-based admission; DSA documents seek abolition of ICE detention and deportations, amnesty, asylum protection, and freer migration.

#### Position cluster 8: Voting Rights, Election Rules, and Representation

**Democratic:** Documents support restoring and enforcing the Voting Rights Act, opposing voter suppression and partisan or racial gerrymandering, and protecting voting access for returning citizens.
Scope caution: The packet also contains gun, policing, constitutional, and other civil-rights claims outside election policy.
- Support for restoring the full protections of the Voting Rights Act. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 80174:80810; `democratic-2016-normalized-4292f2af0201-001`)
- Commitment to stamp out voter suppression in all its forms. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 5092:5834; `democratic-2020-normalized-fcd461184fac-009`)
- Commitment to protect the right to vote for returning citizens. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 124205:125155; `democratic-2024-normalized-e7f0490f5d0f-009`)
- Support for ending partisan and racial gerrymandering. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 80174:80810; `democratic-2016-normalized-4292f2af0201-005`)

**Republican:** Documents support citizen voting rights while endorsing voter identification, proof of citizenship, same-day voting, paper ballots, and citizen-based apportionment.
Scope caution: Examples mix election rules with unrelated constitutional, criminal-justice, firearms, and speech positions.
- Support for the right of states to require an official government-issued photo identification for voting. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 62697:63176; `republican-2008-normalized-42539f6998d6-010`)
- Pledge to protect the voting rights of every citizen. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 68925:70221; `republican-2016-normalized-89c33cf0a59f-002`)
- Support for securing elections, including same day voting, voter identification, paper ballots, and proof of citizenship. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 7906:8016; `republican-2024-normalized-a213c71f3943-005`)
- Support for the apportionment of representatives among the States according to the number of citizens to preserve the principle of one-person, one-vote. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 49406:49717; `republican-2012-normalized-eb222674fa31-006`)

**DSA:** Documents support broad voting access, including rights for noncitizens and people with convictions, abolition of the Electoral College, same-day registration, and public campaign financing.
Scope caution: Peripheral examples address workplace democracy, policing, courts, housing, and other rights rather than elections.
- Support for extending full voting rights to people with criminal convictions and noncitizens. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 9250:9982; `dsa-2024-program-normalized-0037e0c6a9c8-001`)
- Support for restoring the right to vote for incarcerated people and people with criminal convictions. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 8326:9332; `dsa-2026-program-normalized-d326f1020c4f-002`)
- Support for the elimination of the undemocratic Electoral College. ([2003 resolution on electoral reform](https://web.archive.org/web/20040110235906id_/http://www.dsausa.org/convention2003/report/r-electoral.html); 2003; scoped characters 565:619; `dsa-2003-electoral-normalized-6d2b6566d517-007`)
- Public financing of campaigns should be enacted nationally, as proposed by Minnesota’s late Senator Paul Wellstone and others. ([An Economic Justice Agenda - adopted November 2007](https://www.dsausa.org/wp-json/wp/v2/strategy/612); 2012-12-23; scoped characters 34995:35208; `dsa-2007-economic-justice-normalized-08f0c8f5ef33-006`)
- Support for same-day voter registration and 24-hour voting on weekends or a national holiday for Election Day. ([2003 resolution on electoral reform](https://web.archive.org/web/20040110235906id_/http://www.dsausa.org/convention2003/report/r-electoral.html); 2003; scoped characters 464:563; `dsa-2003-electoral-normalized-6d2b6566d517-006`)

**Pairwise distinctions:**
- Democratic / Republican: Democratic documents emphasize restoring federal voting protections and opposing suppression; Republican documents combine voting-rights language with identification, citizenship-proof, and citizen-apportionment rules.
- Democratic / DSA: Both support expanded voting protection; DSA documents explicitly extend voting to noncitizens and incarcerated people and abolish the Electoral College.
- Republican / DSA: Republican documents require voter identification and citizenship proof; DSA documents extend voting to noncitizens and people with convictions and favor Electoral College abolition.

#### Position cluster 9: Presidential Records, Promises, and Critiques

**Democratic:** Documents praise Clinton, Obama, and Biden records on budgets, coverage, infrastructure, and alliances, while criticizing Bush-era deficits, Iraq claims, special-interest governance, and environmental policy.
Scope caution: The packet mixes proposed future administrations, retrospective claims, campaign criticism, and achievements whose causality was not independently checked.
- Under Bill Clinton's leadership in the 1990s, a budget surplus was built. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 10130:10676; `democratic-2008-normalized-70b894483988-003`)
- Twenty million people gained health insurance coverage under President Obama's leadership. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 181:714; `democratic-2016-normalized-bd681f711028-003`)
- Under President Biden, the United States is rebuilding roads, bridges, ports, airports, water systems, electric grids, and broadband. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 11102:11739; `democratic-2024-normalized-9be95fb035db-008`)
- More than a year ago, President Bush stood on an aircraft carrier under a banner that proclaimed "mission accomplished." ([2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform); 2004; scoped characters 18817:19137; `democratic-2004-normalized-92a8088c5dda-011`)
- In President George Bush's government, polluters write environmental laws and oil company profits matter more than hard science and cold facts. ([2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform); 2004; scoped characters 96735:96947; `democratic-2004-normalized-94090ec19c04-001`)

**Republican:** Documents praise Bush-era defense, AIDS, and bioterrorism actions, criticize Obama-era defense and executive policies, and portray Biden-era borders, inflation, crime, and conflict negatively.
Scope caution: Most examples are retrospective assertions or opponent critiques; claimed effects and causal responsibility were not fact-checked.
- President Bush fulfilled a promise to begin transforming how the nation organizes and equips itself to fight 21st Century adversaries. ([2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform); 2004; scoped characters 60159:60640; `republican-2004-normalized-a2113b2e5302-001`)
- President George W. Bush's health initiatives—AIDS relief under PEPFAR and the Global Fund to Fight AIDS, Tuberculosis, and Malaria—continue to save millions of lives. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 216060:216795; `republican-2016-normalized-28a344099db9-003`)
- President Obama has reduced the defense budget by over $487 billion over the next decade. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 153120:153863; `republican-2012-normalized-e3f9e5a181c1-002`)
- The President has used executive orders to enact national policies in areas constitutionally reserved solely to Congress. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 40065:40935; `republican-2016-normalized-c41609634a5d-006`)
- After nearly four years of the Biden administration, America is rocked by Open Borders. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 2210:2408; `republican-2024-normalized-51f7b85d22c5-013`)

**DSA:** Documents criticize Biden military and drilling priorities, Bush bank bailouts, Clinton financial deregulation and NAFTA, and Obama deportations and Venezuela policy, while welcoming Obama-era Cuba normalization.
Scope caution: Examples include foreign presidents and historical narratives; asserted records, motives, and causal links were not independently verified.
- Under Joe Biden, the United States has prioritized funding a massive military budget and expanding oil drilling. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 2869:3829; `dsa-2024-program-normalized-43f2e9413efb-003`)
- The George W. Bush administration bailed out the banks that caused the financial crisis with trillions of dollars of taxpayers' money. ([2011 adopted resolution supporting Occupy Wall Street](https://web.archive.org/web/20130108175617id_/http://www.dsausa.org/convention2011/report/Resolution%20Supporting%20OWS.pdf); 2011; scoped characters 1344:2451; `dsa-2011-ows-resolution-normalized-e3136ce5f7d1-010`)
- The Clinton administration repealed the Glass-Steagall Act and legalized over-the-counter derivatives trading. ([2011 adopted resolution supporting Occupy Wall Street](https://web.archive.org/web/20130108175617id_/http://www.dsausa.org/convention2011/report/Resolution%20Supporting%20OWS.pdf); 2011; scoped characters 1344:2451; `dsa-2011-ows-resolution-normalized-e3136ce5f7d1-004`)
- Obama deported 3.2 million people, more than any president before or after. ([For a moratorium on deportations, with no exceptions/Para una moratoria de las deportaciones, sin excepciones](https://www.dsausa.org/wp-json/wp/v2/statement/4621); 2020-03-11; scoped characters 2720:3380; `dsa-statement-4621-normalized-9d208ba95cab-005`)
- The Democratic Socialists of America celebrates the Obama administration’s move toward the normalization of diplomatic relationships between the United States and Cuba. ([DSA Statement on US Normalizing Relations with Cuba](https://www.dsausa.org/wp-json/wp/v2/statement/373); 2014-12-18; scoped characters 0:634; `dsa-statement-373-normalized-45ed973bceb0-001`)

**Pairwise distinctions:**
- Democratic / Republican: Each side praises aligned administrations and criticizes opponents: Democratic documents highlight Obama-Biden domestic gains; Republican documents emphasize Bush security actions and Biden-era disorder.
- Democratic / DSA: Democratic documents credit Obama-Biden achievements; DSA documents criticize several Democratic administrations on deportation, deregulation, trade, military spending, and sanctions, while approving Cuba normalization.
- Republican / DSA: Republican documents praise Bush security and health initiatives; DSA documents fault Bush-era bank bailouts and criticize interventionist policies across administrations.

#### Position cluster 10: Taxation of Income, Wealth, and Corporations

**Democratic:** Documents support middle-class and family tax relief, targeted child and earned-income credits, higher contributions from wealthy taxpayers, estate-tax restoration, and selected corporate-rate or incentive reforms.
Scope caution: Positions vary by year and include both tax increases or loophole closures and targeted corporate or family tax reductions.
- Commitment to offer additional tax cuts for middle class families. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 60487:61548; `democratic-2008-normalized-fe2cabd6d37b-005`)
- Commitment to make sure the wealthy pay their fair share in taxes. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 60168:60904; `democratic-2020-normalized-d9a1dc68d808-007`)
- Support for restoring fair taxation on multimillion dollar estates. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 40163:40780; `democratic-2016-normalized-9957d3b08ad7-004`)
- Commitment to reform the tax code to be more progressive and equitable, and reduce barriers for working families to benefit from targeted tax breaks, including the Earned Income Tax Credit and the Child Tax Credit. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 60906:61517; `democratic-2020-normalized-d4d1663f3068-001`)
- Commitment to reforming the corporate tax code to lower tax rates for companies in the United States. ([2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); 2012; scoped characters 31475:32488; `democratic-2012-normalized-f75fff4be951-010`)

**Republican:** Documents support lower family, worker, investment, and corporate taxes; permanent Trump tax provisions; expanded child credits; and tax structures intended to encourage saving and business growth.
Scope caution: Examples span broad rate cuts, targeted credits, tariff-linked predictions, and reforms whose stated economic effects were not verified.
- Support for tax reform that takes 6 million families off the tax rolls, cuts the rate for those who remain on the tax rolls, and doubles the child tax credit to $1,000. ([2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform); 2000; scoped characters 44515:44684; `republican-2000-normalized-72d4d20b0778-002`)
- Support for reducing the corporate tax rate to keep U.S. corporations competitive internationally. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 12248:13175; `republican-2012-normalized-cf8e70a905aa-013`)
- Commitment to make permanent the provisions of the Trump Tax Cuts and Jobs Act that doubled the standard deduction, expanded the Child Tax Credit, and spurred economic growth for all Americans. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 15857:16203; `republican-2024-normalized-007a594371a0-003`)
- Support for a tax code that encourages personal savings. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 71482:71826; `republican-2008-normalized-903fa1c9b13d-008`)
- Commitment to eliminate taxes on tips for millions of restaurant and hospitality workers. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 15857:16203; `republican-2024-normalized-007a594371a0-004`)

**DSA:** Documents support progressive income and corporate taxation, taxes on wealth, inheritances, capital gains, and financial transactions, closing corporate loopholes, and reducing regressive sales and excise taxes.
Scope caution: Revenue estimates and claims that particular taxes fund public programs are document assertions, not independently validated causal or fiscal findings.
- Support for taxing financial transactions, capital gains, luxury purchases, and domestic and global corporations. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 32385:32672; `dsa-2021-adopted-normalized-7ace82695f5d-019`)
- Support for establishing a wealth tax for the wealthiest in society. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 7352:8203; `dsa-2024-program-normalized-f23d4047d972-009`)
- Support for increasing effective corporate taxation through the elimination of corporate tax loopholes and corporate “tax expenditures”. ([Reject the Fiscal Cliff](https://www.dsausa.org/wp-json/wp/v2/statement/355); 2012-12-21; scoped characters 4357:4952; `dsa-2012-fiscal-normalized-675dfbae09ee-011`)
- Support for a fair and progressive income and corporate tax structure. ([2011 adopted resolution supporting Occupy Wall Street](https://web.archive.org/web/20130108175617id_/http://www.dsausa.org/convention2011/report/Resolution%20Supporting%20OWS.pdf); 2011; scoped characters 2452:3839; `dsa-2011-ows-resolution-normalized-654ff8ab0cb5-007`)
- Support for reducing and eliminating regressive sales and excise taxes that punish the working class. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 32385:32672; `dsa-2021-adopted-normalized-7ace82695f5d-015`)

**Pairwise distinctions:**
- Democratic / Republican: Both offer family tax relief; Democratic documents pair it with progressive taxation, while Republican documents emphasize broader rate reductions, permanence, saving, investment, and corporate competitiveness.
- Democratic / DSA: Both support more progressive taxation; DSA documents specify wealth, transaction, inheritance, and broad corporate taxes, while Democratic documents combine higher-end taxation with targeted relief.
- Republican / DSA: Republican documents seek lower investment and corporate rates; DSA documents seek higher corporate, wealth, capital-gains, inheritance, and financial-transaction taxes while reducing regressive consumption taxes.

#### Position cluster 11: Public Education: Access, Standards, and Accountability

**Democratic:** Documents support increased public-school investment, equitable access and funding, achievement standards and accountability, community schools, and public options including magnet, charter, teacher-led, and career schools.
Scope caution: Approaches vary over time, including standardized accountability, later opposition to punitive test-based treatment, and support for selected public-school choice.
- Support for increasing investments to guarantee all students can access high-quality public schools, no matter where they live. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 121780:122351; `democratic-2020-normalized-3e1d1d365c73-005`)
- Support for equitable and adequate state funding for public education. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 110675:111651; `democratic-2016-normalized-d699b43d99c3-006`)
- Commitment to holding schools, districts, communities, and states accountable for raising achievement levels for all students. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 107544:107958; `democratic-2016-normalized-45d35ed14449-011`)
- Support for helping schools to lift student achievement, rather than punishing them based on state standardized tests. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 74850:76410; `democratic-2024-normalized-0bc5902e5d0e-005`)
- Commitment to work to expand public school options for low-income youth, including magnet schools, charter schools, teacher-led schools, and career academies. ([2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); 2012; scoped characters 23384:24391; `democratic-2012-normalized-1c0d70ee0925-009`)

**Republican:** Documents support parental choice through charter, private, parochial, home, virtual, and technical schooling, vouchers and tax credits, alongside local control, discipline, merit pay, and academic expectations.
Scope caution: The packet also includes public-school disability funding and broad access language; choice mechanisms and accountability policies vary across years.
- Support for choice in education for all families, especially those with children trapped in dangerous and failing schools, whether through charter schools, vouchers or tax credits for attending faith-based or other nonpublic schools, or the option of home schooling. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 125221:126660; `republican-2008-normalized-224fe729171f-002`)
- Support for financing mechanisms that make educational choices available to all children, including education savings accounts, vouchers and tuition tax credits. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 143320:144248; `republican-2016-normalized-e6566783314d-repair-e4af6ec3f523-002`)
- Support for Universal School Choice in every State in America. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 23482:23731; `republican-2024-normalized-63d28569ddf1-009`)
- Support for returning Education to the States. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 25272:25305; `republican-2024-normalized-631b8e76912c-010`)
- Support for merit pay for good teachers. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 137006:137533; `republican-2012-normalized-064968664904-003`)

**DSA:** Documents support free, publicly funded education from pre-K through college, student-debt cancellation, desegregation, inclusive and bias-free schools, reduced testing, and funding detached from local property taxes.
Scope caution: Examples also include pandemic reopening demands, sex education, LGBTQ student rights, and historical narratives rather than one unified school-governance proposal.
- Support for providing free, quality public education from pre-K to college. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 4779:5913; `dsa-2026-program-normalized-3ba469ba4e69-005`)
- Support for canceling all student loan debt. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 6467:7350; `dsa-2024-program-normalized-b789b4710c28-008`)
- Support for implementing and fully funding programs for desegregation and integration for all public schools. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 20294:20384; `dsa-2021-adopted-normalized-6c07162ee087-002`)
- Support for democratizing and funding instruction inclusive of all students while minimizing testing at all levels of education. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 29390:29603; `dsa-2021-adopted-normalized-6c02b493f903-009`)
- Support for disconnecting property taxes from school funding and fully funding public education. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 29784:29861; `dsa-2021-adopted-normalized-29ef349cf189-001`)

**Pairwise distinctions:**
- Democratic / Republican: Democratic documents emphasize public-school investment and equity with some public options; Republican documents extend choice to private, religious, home, voucher, and tax-credit pathways.
- Democratic / DSA: Both support public education access and equitable funding; DSA documents additionally demand tuition-free higher education, debt cancellation, desegregation, reduced testing, and property-tax funding separation.
- Republican / DSA: Republican documents prioritize parental choice across public and private providers; DSA documents frame education as a free public right and seek debt cancellation and public-system funding.

#### Position cluster 12: Reproductive Rights and Gender-Affirming Care

**Democratic:** Documents support legal abortion and reproductive freedom, contraception and family planning, repealing funding restrictions, IVF access, pregnancy protections, and opposition to bans on gender-affirming care.
Scope caution: The packet also covers violence, marriage equality, and broader sex-discrimination protections; terminology and policy scope change across years.
- Strong and unequivocal support for Roe v. Wade and a woman's right to choose a safe and legal abortion, regardless of ability to pay. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 142353:142577; `democratic-2008-normalized-58e656571334-009`)
- Commitment to fight to protect and codify the right to reproductive freedom. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 124349:125100; `democratic-2020-normalized-c3e3058c15da-004`)
- Commitment to support the repeal of the Helms Amendment, which limits safe access to abortion. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 257236:257852; `democratic-2020-normalized-c28dad59ba3f-012`)
- Commitment to protect a woman's right to access IVF. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 146621:147237; `democratic-2024-normalized-49ca2c582b14-004`)
- Support for vigorously opposing state and federal bans on gender-affirming health care. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 171503:171935; `democratic-2024-normalized-9fb427e7c407-003`)

**Republican:** Documents oppose abortion, support constitutional or statutory fetal-life protections and funding bans, and endorse informed-consent or waiting-period rules; 2024 examples also support birth control, prenatal care, and IVF.
Scope caution: The packet records temporal variation and adjacent gender-policy claims; one example rejects punitive action against women obtaining abortions.
- Support for a human life amendment to the Constitution. ([2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform); 2000; scoped characters 59468:60411; `republican-2000-normalized-9eed2dd44520-005`)
- Call for a permanent ban on all federal funding and subsidies for abortion and healthcare plans that include abortion coverage. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 126431:127175; `republican-2012-normalized-358189a39e4a-006`)
- Support for laws requiring informed consent prior to abortion. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 60055:60641; `republican-2012-normalized-66d078ccdda4-001`)
- Commitment to support policies that advance access to Birth Control. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 30895:31424; `republican-2024-normalized-8da9a39b9f7f-012`)
- Commitment to support policies that advance IVF (fertility treatments). ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 30895:31424; `republican-2024-normalized-8da9a39b9f7f-013`)

**DSA:** Documents support abortion access without legal restrictions, Hyde repeal, universal reproductive and gender-affirming care, bodily autonomy, and rights for pregnant people, LGBTQ parents, and gender-diverse people.
Scope caution: Examples combine policy demands with historical court narratives and opponent descriptions; quoted legal and political claims were not independently verified.
- Support for repeal of the Hyde Amendment and all legal restrictions on abortion access. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 35175:35249; `dsa-2021-adopted-normalized-0a25e1af4692-005`)
- Support for free abortion on demand. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 35150:35173; `dsa-2021-adopted-normalized-0a25e1af4692-004`)
- Support for guaranteed gender-affirming health care. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 6467:7350; `dsa-2024-program-normalized-b789b4710c28-repair-1a7d74b0c436-003`)
- End policies that oppress bodily autonomy and intimate life, including patriarchal restrictions on abortion, childbirth, childraising, gender expression, transition, marriage and divorce. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 5915:7099; `dsa-2026-program-normalized-cc87289e0395-repair-d00a2e493932-006`)
- Women, gender nonconforming people and trans men who may become pregnant should have the right to decide whether to terminate or continue a pregnancy. ([Uniting to Build a Socialist Feminist Movement](https://www.dsausa.org/wp-json/wp/v2/statement/388); 2017-05-01; scoped characters 777:1367; `dsa-statement-388-normalized-472e2eb2aeff-009`)

**Pairwise distinctions:**
- Democratic / Republican: Democratic documents protect legal abortion and repeal funding limits; Republican documents oppose abortion and support fetal-life amendments, funding bans, consent rules, and waiting periods.
- Democratic / DSA: Both protect abortion and gender-affirming care; DSA documents explicitly demand free abortion, removal of all access restrictions, and broader bodily-autonomy guarantees.
- Republican / DSA: Republican documents restrict abortion and its public funding; DSA documents seek unrestricted, free abortion and universal reproductive and gender-affirming care.

#### Position cluster 13: International Security and Cooperation Strategies

**Democratic:** Documents support alliances, multilateral institutions, diplomacy, arms control, collective defense, democracy support, counterterrorism, and cooperation against nuclear, cyber, humanitarian, and regional security threats.
Scope caution: The packet combines cooperative diplomacy with military deterrence and intervention-related positions; specific regional approaches and emphases vary over time.
- Commitment to rebuild alliances, partnerships, and institutions necessary to confront common threats and enhance common security. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 97932:98420; `democratic-2008-normalized-2f22bd733321-001`)
- Commitment to use diplomacy and development to confront global threats. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 138544:138882; `democratic-2016-normalized-cba8bb3f1bb4-010`)
- Commitment to lower global threats by reinforcing nuclear arms control. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 279543:279966; `democratic-2020-normalized-c64d298fbba5-025`)
- Commitment to reaffirm America's commitment to defending allies. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 279543:279966; `democratic-2020-normalized-c64d298fbba5-021`)
- Commitment to counter cyber threats. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 123180:124203; `democratic-2024-normalized-94ca68ceacfc-011`)

**Republican:** Documents support alliances and selected multilateral cooperation alongside larger or modernized forces, missile and nuclear defenses, counterterrorism, pressure on hostile states, and peace through strength.
Scope caution: Examples mix diplomacy, trade, military buildup, deterrence, blockade, and regional assistance; predicted security effects were not independently tested.
- The Republican vision of peace through strength requires a sustained international effort, which complements military activities, to develop and maintain alliances and relationships that will lead to greater peace and stability. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 20951:21183; `republican-2008-normalized-47f1bf186f86-005`)
- Support for funding, developing, and deploying a multi-layered missile defense system. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 178614:179078; `republican-2016-normalized-fbf2085e7ad8-002`)
- Support for modernizing nuclear weapons and their delivery platforms. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 178614:179078; `republican-2016-normalized-fbf2085e7ad8-003`)
- Commitment to strengthen Economic, Military, and Diplomatic capabilities to protect the American way of life from the malign influences of Countries that stand against the United States around the World. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 34160:34351; `republican-2024-normalized-e8e86f62671d-011`)
- Commitment to end the global chaos and restore Peace through Strength, reducing geopolitical risks and lowering commodity prices. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 11058:11264; `republican-2024-normalized-8d8835191786-007`)

**DSA:** Documents support multilateral diplomacy and international courts while opposing U.S. wars, sanctions, militarism, and authoritarian alliances; they favor military cuts, nuclear abolition, sovereignty, and humanitarian cooperation.
Scope caution: Some documents permit limited multilateral force or peacekeeping, so the packet is not uniformly pacifist; regional prescriptions vary historically.
- Support for working cooperatively with other governments and through the United Nations to solve global problems. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 58529:58627; `dsa-2021-adopted-normalized-bf23fd771fc3-001`)
- Support for respecting the authority of the International Criminal Court. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 8205:9248; `dsa-2024-program-normalized-9d88be1f8868-004`)
- End all U.S. foreign wars. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 7145:8285; `dsa-2026-program-normalized-40060dd6f6dd-repair-d40710b9eecc-002`)
- Support for renouncing the use of nuclear weapons and other weapons of mass destruction, and pursuing agreements with other governments to abolish such weapons. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 60361:60505; `dsa-2021-adopted-normalized-d37f0cebbfee-006`)
- Support for greatly reducing the U.S. military budget. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 8205:9248; `dsa-2024-program-normalized-9d88be1f8868-007`)

**Pairwise distinctions:**
- Democratic / Republican: Both support alliances and deterrence; Democratic documents stress diplomacy, arms control, and institutions, while Republican documents emphasize force expansion, missile defense, nuclear modernization, and strength.
- Democratic / DSA: Both support multilateral cooperation; Democratic documents retain collective defense and deterrence, while DSA documents seek major military cuts, nuclear abolition, sanctions removal, and ending foreign wars.
- Republican / DSA: Republican documents favor missile defenses, nuclear modernization, and peace through strength; DSA documents favor nuclear abolition, military-budget reductions, sanctions removal, and ending U.S. wars.

#### Position cluster 14: U.S. Military Involvement and the War on Terror

**Democratic:** Documents describe terrorism and proliferation threats, support defeating al-Qaeda and securing weapons materials, criticize Iraq's costs and distraction, favor ending that war, and note burdens on troops.
Scope caution: The packet mixes policy positions with threat assessments, war records, veteran impacts, and unverified claims about adversaries and military outcomes.
- All bomb-making material worldwide needs to be found, cataloged, and locked away. ([2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform); 2004; scoped characters 14451:14715; `democratic-2004-normalized-8f1afc3f94bb-007`)
- Commitment to defeat Al Qaeda in Afghanistan and Pakistan, where those who attacked the U.S. on 9-11 reside and are resurgent. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 76236:76429; `democratic-2008-normalized-a660afb3bf0d-007`)
- Ending the war in Iraq is a goal. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 74445:74467; `democratic-2008-normalized-8ea5d753fbc6-001`)
- The war in Iraq distracted the United States from confronting many of the most fundamental national security challenges facing the United States, including the danger posed by international terrorist organizations that threaten the American homeland. ([2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); 2012; scoped characters 114618:115262; `democratic-2012-normalized-13e519c73835-005`)
- Eleven years of continuous military operations and repeated deployments to Iraq and Afghanistan have stretched U.S. forces and strained their families. ([2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); 2012; scoped characters 155075:155400; `democratic-2012-normalized-0012a775903a-005`)

**Republican:** Documents portray terrorism, hostile states, proliferation, and military readiness as major threats; they support destroying ISIS, success in Iraq, stronger forces, missile defense, and faster intelligence support.
Scope caution: Many examples are threat predictions or evaluations rather than policy; asserted consequences, readiness gaps, and adversary intentions were not fact-checked.
- The United States must destroy ISIS. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 198084:199629; `republican-2016-normalized-edb41c383f7b-repair-b3d1abffc553-004`)
- Success in Iraq will deny al Qaeda a safe haven. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 41967:42720; `republican-2008-normalized-43bc9fa261d5-006`)
- If the United States does not have a Strong Military, it will not be able to defend its interests and will be at the mercy of Hostile Nations. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 4899:5316; `republican-2024-normalized-908167445e74-001`)
- America and its allies face a deadly threat from ballistic missiles armed with the world's most dangerous weapons. ([2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform); 2004; scoped characters 61102:61843; `republican-2004-normalized-a840632cc70d-005`)
- Intelligence information should be provided more quickly to the warfighter and the policy maker. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 8415:8796; `republican-2008-normalized-2f1b40a7ccb9-014`)

**DSA:** Documents oppose U.S. occupations, overseas bases, Iraq and Syria intervention, and expansive military spending; they support bringing troops home while acknowledging targeted intelligence and security measures against terrorism.
Scope caution: Examples include historical narratives and causal claims that U.S. wars intensified terrorism or instability; those assertions were not independently verified.
- Close U.S. overseas military bases. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 8205:9248; `dsa-2024-program-normalized-9d88be1f8868-repair-e0ecacd53027-001`)
- Bring U.S. troops home to the United States. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 8205:9248; `dsa-2024-program-normalized-9d88be1f8868-repair-e0ecacd53027-002`)
- Dramatically slash US military spending to a level sufficient for a genuine national defense, not the projection of power outside the country. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 58352:58494; `dsa-2021-adopted-normalized-a26aa576943f-008`)
- Opposition to United States military intervention in the civil war in Syria. ([Statement on U.S. Action Against Syria](https://www.dsausa.org/wp-json/wp/v2/statement/364); 2013-09-02; scoped characters 0:461; `dsa-statement-364-normalized-50865307df58-001`)
- There can be no doubt that more effective anti-terrorist measures, including more effective intelligence gathering, better security measures, and policing of the skies, are necessary. ([DSA statement on the September 11 terrorist attacks](https://dlarchive.dsausa.org/wp-content/uploads/2018/12/DL_2001_V029_02.pdf); 2001; scoped characters 0:1400; `dsa-2001-september-11-normalized-2872d1c0c23f-005`)

**Pairwise distinctions:**
- Democratic / Republican: Both identify terrorism and proliferation threats; Democratic documents criticize Iraq's diversion and support ending it, while Republican documents argue Iraqi success denies terrorist safe haven.
- Democratic / DSA: Democratic documents retain targeted military action against al-Qaeda while ending Iraq; DSA documents seek troop withdrawal, base closures, deep military cuts, and opposition to intervention.
- Republican / DSA: Republican documents call for destroying ISIS and stronger military capacity; DSA documents oppose intervention, close overseas bases, return troops, and reduce spending to territorial defense.

#### Position cluster 15: Opposition to Policies and Governing Authorities

**Democratic:** Across years, documents oppose Republican or administration actions involving arms, surveillance, social-program cuts, privatization, and foreign policy, while also recording criticisms of governing performance.
Scope caution: The packet combines policy opposition with factual and evaluative attacks across unrelated domestic and foreign issues.
- Opposition to Republican plans to endanger U.S. security with massive unilateral cuts in the U.S. arsenal. ([2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); 2000; scoped characters 140689:140708; `democratic-2000-normalized-35991a3208e1-001`)
- Rejection of the use of national security letters to spy on citizens who are not suspected of a crime. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 155352:155975; `democratic-2008-normalized-fa1cd1900e67-007`)
- Commitment to oppose Republican plans to slash funding and block grant Medicaid and SNAP, which would harm millions of Americans. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 115903:116156; `democratic-2016-normalized-f4e2c14968d7-011`)
- Opposition to all efforts to privatize the U.S. Postal Service. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 20658:21096; `democratic-2024-normalized-e4e0fee5728c-011`)

**Republican:** Documents reject regulation, bailouts, international constraints, and administration actions, often invoking economic costs, constitutional limits, national sovereignty, or private-sector autonomy.
Scope caution: Examples range from specific policy commitments to broad retrospective accusations and claims about foreign governments.
- Strong opposition to the Kyoto Protocol and similar mandatory carbon emissions controls that harm economic growth and destroy American jobs. ([2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform); 2004; scoped characters 219327:219736; `republican-2004-normalized-53cdfe529adc-010`)
- Opposition to government bailouts of private institutions. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 82425:83439; `republican-2008-normalized-12c182215fbf-005`)
- Opposition to the adoption or ratification of international treaties that weaken or encroach upon American sovereignty. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 62202:62437; `republican-2012-normalized-f832db2b0dc6-008`)
- Commitment to slash regulations that stifle jobs, freedom, innovation, and make everything more expensive. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 14880:15051; `republican-2024-normalized-3cf23a1200a0-001`)

**DSA:** Documents oppose militarism, sanctions, privatization, austerity, corporate influence, and undemocratic institutions, criticizing Republican, Democratic, bipartisan, governmental, and labor leadership across years.
Scope caution: Targets and claim types vary substantially; this is opposition language, not one unified policy program.
- DSA rejects the Bush administration’s plan for a UN-endorsed multilateral military force. ([2003 resolution on the occupation of Iraq](https://web.archive.org/web/20040110235717id_/http://www.dsausa.org/convention2003/report/r-iraq.html); 2003; scoped characters 1922:2527; `dsa-2003-iraq-normalized-db1b9f74155d-003`)
- The Obama administration bailed out the banks without any strings attached. ([2011 adopted resolution supporting Occupy Wall Street](https://web.archive.org/web/20130108175617id_/http://www.dsausa.org/convention2011/report/Resolution%20Supporting%20OWS.pdf); 2011; scoped characters 1344:2451; `dsa-2011-ows-resolution-normalized-e3136ce5f7d1-012`)
- Opposition to using economic and financial sanctions to punish other countries, such as Cuba, Venezuela, and Iran, that dare to act independently of the United States. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 59090:59393; `dsa-2021-adopted-normalized-bf23fd771fc3-005`)
- Neither major party is capable of advancing a positive program for the 2024 elections that meets the needs of the majority of Americans. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 0:1303; `dsa-2024-program-normalized-c668d0328bc5-009`)

**Pairwise distinctions:**
- Democratic / Republican: Democratic examples defend social programs and civil liberties against cuts or surveillance; Republican examples resist regulation, bailouts, and international authority.
- Democratic / DSA: Democratic examples primarily contest Republican or named-administration measures; DSA examples also indict Democratic administrations, bipartisan elites, corporate influence, and governing institutions.
- Republican / DSA: Republican examples resist governmental and international constraints while favoring autonomy; DSA examples attack sanctions, militarism, austerity, privatization, and corporate control.

#### Position cluster 16: Healthcare System Goals and Approaches

**Democratic:** Documents repeatedly seek universal or broadly accessible affordable coverage, strengthening Medicare and Medicaid, widening eligibility, reducing prescription and out-of-pocket costs, and supporting preventive care.
Scope caution: Specific mechanisms and populations vary by year; several examples describe records or system problems rather than proposals.
- Commitment to move the nation closer to the goal of providing universal health coverage for all Americans. ([2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); 2000; scoped characters 84738:85540; `democratic-2000-normalized-07a86d3aa6c5-010`)
- Commitment to ensure that all Americans—regardless of immigration status—have access to quality health care. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 56962:57929; `democratic-2016-normalized-a06765db4456-004`)
- Commitment to build a health care system that provides universal health care coverage. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 75631:76409; `democratic-2020-normalized-3542c1bfdbb3-010`)
- Commitment to strengthen coverage across all health plans. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 216908:217600; `democratic-2024-normalized-aa0b71876216-002`)

**Republican:** Documents support affordable access through consumer choice, competition, insurers and providers, targeted coverage, primary care, and protection or restructuring of Medicare and Medicaid.
Scope caution: Approaches vary from program protection to defined contributions; some examples concern adjacent health or Social Security issues.
- All Americans should have access to high-quality and affordable health care. ([2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform); 2000; scoped characters 89042:89820; `republican-2000-normalized-83e6d37c1b34-002`)
- Commitment to not put government between patients and their health care providers. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 106820:106898; `republican-2008-normalized-4e30b857ac84-001`)
- A defined-contribution model is the only way to limit costs and restore consumer choice for patients and introduce competition. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 85434:86632; `republican-2012-normalized-924e7ef8a7e7-002`)
- Commitment to expand access to Primary Care. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 21860:22119; `republican-2024-normalized-639254060a0e-008`)

**DSA:** Documents advocate universal single-payer or Medicare for All coverage without premiums or cost sharing, regardless of status, alongside public facilities, expanded services, and cost controls.
Scope caution: Earlier documents sometimes support interim public options or state routes; a few examples are pandemic guidance or descriptive claims.
- A single-payer system is equivalent to “Medicare for all,” and not just for the poor or the currently uninsured. ([An Economic Justice Agenda - adopted November 2007](https://www.dsausa.org/wp-json/wp/v2/strategy/612); 2012-12-23; scoped characters 20350:21181; `dsa-2007-economic-justice-normalized-969c50089fd8-010`)
- Support for progressively extending and strengthening Medicare/Medicaid until it covers U.S. residents of all ages, while installing effective cost controls. ([Reject the Fiscal Cliff](https://www.dsausa.org/wp-json/wp/v2/statement/355); 2012-12-21; scoped characters 5367:5510; `dsa-2012-fiscal-normalized-2b868cee0576-003`)
- Support for ensuring everyone, regardless of employment, immigration, or insurance status, receives the healthcare they need — including free testing and treatment, mental healthcare, and long-term care for people with disabilities. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 49863:50482; `dsa-2021-adopted-normalized-c37abde20ad2-001`)
- Support for Medicare for All providing universal health care without premiums, copays or deductibles. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 6467:7350; `dsa-2024-program-normalized-b789b4710c28-repair-1a7d74b0c436-001`)
- Support for expanding healthcare access and quality by investing in new public hospitals and clinics. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 4779:5913; `dsa-2026-program-normalized-3ba469ba4e69-008`)

**Pairwise distinctions:**
- Democratic / Republican: Democratic examples emphasize universal coverage and public-program expansion; Republican examples emphasize consumer choice, provider competition, targeted access, and limiting government intermediation.
- Democratic / DSA: Both seek broad access, but Democratic examples retain multiple plans and strengthen existing programs, while DSA examples specify one public single-payer program without premiums or copays.
- Republican / DSA: Republican examples rely on choice, competition, insurers, and purchasing pools; DSA examples replace fragmented insurance with federally administered universal single-payer coverage.

#### Position cluster 17: Economic hardship and financial insecurity

**Democratic:** Documents describe poverty, job loss, unaffordable housing and health care, food insecurity, and racial wealth disparities, often locating hardship in recession, discrimination, or weak protections.
Scope caution: The narrative cluster also contains environmental, trade, and isolated biographical claims not directly about household insecurity.
- Millions of Americans are struggling under the mounting burden of life's everyday costs. ([2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform); 2004; scoped characters 799:967; `democratic-2004-normalized-eb1979bf3bc4-011`)
- One in five U.S. families struggles with food insecurity. ([2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); 2012; scoped characters 98921:99419; `democratic-2012-normalized-0cea95a4c23e-002`)
- Decades of red-lining, rising income inequality, and predatory lending practices targeting low-income families and people of color have made homeownership all but impossible for millions of working families. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 53533:54392; `democratic-2020-normalized-7f5f6135a575-002`)
- The nation's teachers, nurses, firefighters, and other essential workers are struggling with housing costs that outpace their incomes, leaving them unable to live near their workplaces. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 69540:70730; `democratic-2024-normalized-51d7cbe64123-004`)

**Republican:** Documents describe hardship through lost jobs and homes, rising health, food, and energy costs, inflation, trade deficits, and poverty, sometimes assigning responsibility to Democratic administrations.
Scope caution: Examples mix household hardship with business, government-budget, climate, and foreign-development claims.
- Rising health insurance costs cause families to go without insurance. ([2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform); 2004; scoped characters 184049:185269; `republican-2004-normalized-5fb0b69ca72f-004`)
- Many Americans have experienced the burden of lost jobs, lost homes, and lost hopes, and the middle class has felt that burden most acutely. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 1183:1326; `republican-2012-normalized-cde29fc831f3-010`)
- The number of Americans living in poverty has increased by 7 million under President Obama and the Democratic Party. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 6140:6803; `republican-2016-normalized-c9a8ddf744a5-003`)
- Inflation is a crushing tax on American families. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 9360:9909; `republican-2024-normalized-7eea32ad5c94-003`)

**DSA:** Documents connect low wages, rent burdens, austerity, indebtedness, unemployment, and eroding services to elite or capitalist power, emphasizing disproportionate harms to workers and marginalized communities.
Scope caution: Examples span predictions, structural diagnoses, specific crises, climate harms, and several peripheral factual claims.
- The economic recession will increase already morally unacceptable levels of inequality by worsening the conditions of low-wage workers and threatening the living standards of the middle class. ([2001 convention national priorities resolution](https://www.dsausa.org/files/2019/07/DL-2001-Convention-Coverage.pdf); 2002; scoped characters 0:523; `dsa-2001-convention-priorities-normalized-ef8a3eb37787-002`)
- The inability of working people to buy the very goods their enhanced productivity produces led to indebtedness and fiscal and trade imbalances that caused the Great Recession. ([2011 adopted convention priorities - full ten-page resolution](https://web.archive.org/web/20130108175613id_/http://www.dsausa.org/convention2011/report/Priorities%20Resolution.pdf); 2011; scoped characters 1465:3009; `dsa-2011-priorities-full-normalized-ed8e3a0bf92d-002`)
- Public austerity and incarceration endanger communities and make it difficult for many people to pay for rent, food, childcare, or housing. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 24811:25556; `dsa-2021-adopted-normalized-1870bd662c8e-005`)
- Millions struggle with low wages, dangerous working conditions, and limited control over their own lives. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 1305:2868; `dsa-2024-program-normalized-c0035893561c-002`)
- The price of gas and rent is causing distress. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 1757:3011; `dsa-2026-program-normalized-7484933df369-005`)

**Pairwise distinctions:**
- Democratic / Republican: Democratic examples foreground poverty, housing, food insecurity, and racial disparities; Republican examples foreground inflation, trade, lost jobs and homes, and cost pressures.
- Democratic / DSA: Democratic examples document hardship and discriminatory barriers; DSA examples more explicitly attribute insecurity to austerity, capitalist elites, weakened services, and worker disempowerment.
- Republican / DSA: Republican examples stress prices, trade, downturns, and administration performance; DSA examples stress class power, austerity, low wages, and unequal crisis burdens.

#### Position cluster 18: Critiques and Alternatives to Capitalism

**Democratic:** A small, mixed set criticizes concentrated corporate and special-interest power, unequal rules, exploitation, and attacks on workers, while generally seeking fairer markets rather than capitalism's abolition.
Scope caution: Only 22 claims appear, and several concern unrelated foreign affairs, child labor, or broad economic description.
- A free market was never meant to be a free license to take whatever one can get, however one can get it. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 58768:59466; `democratic-2008-normalized-32fbc1d828df-006`)
- The political system is under assault by those who believe that special interests should be able to buy whatever they want in society, including the government. ([2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); 2012; scoped characters 62579:63036; `democratic-2012-normalized-8faac26492b5-004`)
- Large corporations have concentrated their control over markets to a greater degree than Americans have seen in decades—further evidence that the deck is stacked for those at the top. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 37822:38431; `democratic-2016-normalized-7359200e1c62-009`)
- The President says that capitalism without competition isn't capitalism, it's exploitation. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 62626:63049; `democratic-2024-normalized-da9ab87f7a1b-010`)

**Republican:** Documents praise free enterprise, private-sector innovation, property ownership, and linked economic and political freedom, while condemning Marxism, bureaucracy, government redistribution, and crony capitalism.
Scope caution: The packet includes foreign-policy ideology and historical description alongside domestic economic positions.
- That system is poised to sweep away both the counterproductive vestiges of protectionism and the backwater remnants of Marxism. ([2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform); 2000; scoped characters 18056:18681; `republican-2000-normalized-40552b3c6fa4-014`)
- Belief in the free market as the best tool to sustained prosperity and opportunity for all. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 82425:83439; `republican-2008-normalized-12c182215fbf-007`)
- The private sector is the only way to safeguard or improve Internet systems. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 92482:93546; `republican-2012-normalized-14dd71bc18fa-010`)
- Support for others to rally to the cause of fighting crony capitalism. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 118823:119969; `republican-2016-normalized-c44984055aab-013`)

**DSA:** Documents describe capitalism as exploitative and undemocratic, advocate its abolition or transformation, and propose working-class control, public banking, cooperatives, solidarity economies, and decommodified essentials.
Scope caution: Some examples describe interim reforms or organizational strategy rather than a complete post-capitalist design.
- In the near term, democratic socialists struggle for reforms that shift power and resources away from corporate elites and put them in the hands of ordinary people. ([2003 adopted working mission statement](https://web.archive.org/web/20040227005032id_/http://www.dsausa.org/convention2003/report/r-mission.html); 2003; scoped characters 0:814; `dsa-2003-mission-normalized-20f699d8e4de-002`)
- Working people can only truly govern their destiny when they achieve democratic control of the wealth their labor (paid and unpaid) creates by building a democratic socialist society. ([2011 adopted convention priorities - full ten-page resolution](https://web.archive.org/web/20130108175613id_/http://www.dsausa.org/convention2011/report/Priorities%20Resolution.pdf); 2011; scoped characters 1465:3009; `dsa-2011-priorities-full-normalized-ed8e3a0bf92d-004`)
- Commitment to use information about workplace cooperatives, public banks and participatory budgeting to educate themselves and others about practical alternatives to capitalism as embodied in a solidarity economy. ([2013 convention political and organizational priorities](https://web.archive.org/web/20140108003017id_/http://www.dsausa.org/convention_2013_report_priorities); 2013-12-01; scoped characters 1985:2623; `dsa-2013-priorities-normalized-29c443fef256-008`)
- The group fights for the abolition of capitalism and the creation of a democratically run economy that provides for people’s needs. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 25750:26880; `dsa-2021-adopted-normalized-e66dc1af24d6-008`)
- Capitalism is the cause of violence, unemployment, and a climate crisis that poses an existential threat to life on earth. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 1305:2868; `dsa-2024-program-normalized-c0035893561c-005`)

**Pairwise distinctions:**
- Democratic / Republican: Democratic examples criticize concentrated power and unfair market rules; Republican examples defend free enterprise and private-sector primacy while separately opposing crony capitalism.
- Democratic / DSA: Democratic examples seek competition, fair rules, and corporate accountability within markets; DSA examples identify capitalism itself as exploitative and advocate democratic economic replacement.
- Republican / DSA: Republican examples treat private enterprise and ownership as foundations of freedom; DSA examples seek working-class democratic control and abolition of capitalist ownership relations.

#### Position cluster 19: Criminal Justice: Punishment, Accountability, and Prison Reform

**Democratic:** Documents move between tough punishment and accountability for violence, and opposition to torture, secret detention, sentencing disparities, marijuana imprisonment, and inhumane prison treatment.
Scope caution: The cluster includes international crime, hate crimes, human rights, and peripheral accountability claims beyond prison reform.
- Support for tough punishment of violent crime. ([2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform); 2004; scoped characters 53040:54311; `democratic-2004-normalized-821dd4b5fe65-002`)
- Opposition to maintaining a network of secret prisons to jail people beyond the reach of the law. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 156479:157362; `democratic-2008-normalized-4dbc67c6b105-006`)
- Sentencing decisions should be based on the facts of each case, including the severity of the offense and individuals' circumstances. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 110706:111372; `democratic-2020-normalized-9e6e8f488e4b-001`)
- Sending people to prison for possession of marijuana has upended too many lives and incarcerated people for conduct that many states no longer prohibit. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 120961:121705; `democratic-2024-normalized-ad4155f8a786-002`)

**Republican:** Documents call for prosecution, incarceration, mandatory sentences, denied parole, deportation, and tough penalties targeting violent or repeat offenders, gangs, trafficking, fraud, and unauthorized immigration.
Scope caution: Examples also include foreign repression, discrimination, terrorism, cargo security, and several weakly related claims.
- Individuals, including juveniles, who are repeat offenders or who commit serious crimes need to be prosecuted and punished. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 135860:136428; `republican-2008-normalized-e1dee5e96afa-003`)
- Demand for tough penalties for those who practice identity theft, deal in fraudulent documents, and traffic in human beings. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 101161:102609; `republican-2012-normalized-5b6d6308ba2e-010`)
- Gang membership should be a deportable offense. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 108141:109480; `republican-2016-normalized-3d9e76db88bb-008`)
- Commitment to lock up violent offenders. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 7056:7174; `republican-2024-normalized-b90fbe592293-017`)

**DSA:** Documents portray policing and prisons as racially and economically coercive, demand releases and accountability for state violence, and later advocate demilitarization and abolition of police and prisons.
Scope caution: Earlier and peripheral examples also demand prosecution or justice for terrorism, corporate lawbreaking, and official misconduct.
- The action of the Ferguson, Missouri, police department exemplifies the dangers to the lives of ordinary Americans, particularly people of color, posed by overly aggressive, heavily armed police forces. ([Justice for Michael Brown: Community Control of Police & Equality for All](https://www.dsausa.org/wp-json/wp/v2/statement/400); 2014-08-21; scoped characters 97:475; `dsa-statement-400-normalized-e1fda3d8ccab-003`)
- A vast, brutal machinery of police and prisons, security and surveillance agencies, immigration and border enforcement, courts and prosecutors disorganize working class communities through the routine application of violence, intimidation, and coercion. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 9022:9537; `dsa-2021-adopted-normalized-5746209c69bc-008`)
- Demand for individuals in prisons, jails, detention centers, and camps to be let go. ([Now is the Time for Solidarity: DSA National Statement on COVID-2019/Es la hora de solidaridad: Comunicación nacional de DSA acerca de COVID-19](https://www.dsausa.org/wp-json/wp/v2/statement/4626); 2020-03-12; scoped characters 4421:5145; `dsa-statement-4626-normalized-b8f72e138725-005`)
- Demilitarize police departments as a step toward fully abolishing the police and prison system characterized as protecting the rich and jailing the poor. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 5915:7099; `dsa-2026-program-normalized-cc87289e0395-repair-d00a2e493932-001`)

**Pairwise distinctions:**
- Democratic / Republican: Democratic examples combine punishment with due process, sentencing reform, and prison safeguards; Republican examples more directly emphasize incarceration, mandatory penalties, deportation, and denied parole.
- Democratic / DSA: Democratic examples reform sentencing and treatment while retaining criminal-justice institutions; DSA examples describe those institutions as structurally coercive and advocate releases, demilitarization, and abolition.
- Republican / DSA: Republican examples expand punitive enforcement against offenders and gangs; DSA examples attribute violence to policing and prisons and seek to reduce or abolish their power.

#### Position cluster 20: Israeli-Palestinian Conflict: Sovereignty, Rights, and Assistance

**Democratic:** Documents support Israel's security and self-defense alongside negotiated two-state peace, Palestinian freedom and statehood, restored assistance and diplomacy, and, in 2024, a ceasefire-linked reconstruction path.
Scope caution: Emphasis shifts by year, and the packet includes broader Middle East and Iran claims.
- Support for the creation of a democratic Palestinian state dedicated to living in peace and security side by side with the Jewish State of Israel. ([2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform); 2004; scoped characters 31086:31937; `democratic-2004-normalized-ed1dec9e1db7-003`)
- Commitment to ensure that Israel always has the ability to defend itself. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 143052:143954; `democratic-2016-normalized-8c63c7382aed-014`)
- Support for a negotiated two-state solution that upholds the right of Palestinians to live in freedom and security in a viable state of their own. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 283509:283910; `democratic-2020-normalized-3c29dbc1688d-006`)
- According to President Biden, a ceasefire deal would create the conditions for a better future for the Palestinian people, one of self-determination, dignity, security, and freedom, and ultimately a state of their own. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 256243:257078; `democratic-2024-normalized-9d1d7d44ab30-012`)

**Republican:** Documents prioritize Israel's security, Jewish-state status, defensible borders, self-defense, Jerusalem, and bilateral negotiation; earlier platforms conditionally support a Palestinian state, while 2016 rejects occupation language.
Scope caution: The 2024 packet contribution is sparse and not a full Israeli-Palestinian policy statement.
- Support for President Bush's vision of two states, Israel and Palestine, living side by side in peace and security. ([2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform); 2004; scoped characters 116552:117233; `republican-2004-normalized-f14ff84db296-006`)
- America supports Israel's right to exist as a Jewish state able to defend itself against homicide bombings, rocket and mortar fire, and other attacks against its people. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 40361:41296; `republican-2008-normalized-ec14bb449444-005`)
- Support for Israel's right to exist as a Jewish state with secure, defensible borders. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 195980:196013; `republican-2012-normalized-2bab5f5039fa-005`)
- The U.S. rejects the false notion that Israel is an occupier. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 201204:201994; `republican-2016-normalized-6c739454c2b4-004`)

**DSA:** Documents support Palestinian self-determination, rights, return, and ending occupation and aid to Israel; earlier examples also condemn attacks on civilians and support negotiated two-state peace.
Scope caution: Later documents add BDS, ceasefire, free-Palestine, and genocide-accountability language, showing substantial cross-year evolution.
- The U.S. and the European Union should pressure the Palestinian Authority to do all in its power to cease attacks on Israeli civilians. ([NPC resolution on Israel's occupation of the West Bank and Gaza](https://dlarchive.dsausa.org/wp-content/uploads/2018/12/DL_2004_V032_02.pdf); 2004; scoped characters 5833:7153; `dsa-2004-israel-palestine-normalized-3bb1d6b334dc-002`)
- Democratic Socialists of America urges the U.S. government and the international community to ensure that the temporary ceasefire in Gaza leads to a sustained diplomatic effort to negotiate a just, two-state solution to the conflict between the Palestinian and Israeli peoples. ([NPC statement on Israeli-Palestinian conflict](https://dlarchive.dsausa.org/wp-content/uploads/2018/12/DL_2009_V037_01.pdf); 2009-06; scoped characters 1322:2822; `dsa-2009-middle-east-lead-normalized-6447902d562f-009`)
- Stand in solidarity with the Palestinian struggle against apartheid, colonialism, and military occupation, and for equality, human rights, and self-determination, including the Boycott, Divestment and Sanctions (BDS) movement. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 57356:57582; `dsa-2021-adopted-normalized-a26aa576943f-002`)
- Support for ending military and economic aid to Israel. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 8205:9248; `dsa-2024-program-normalized-9d88be1f8868-002`)
- Support for recognizing the rights of the Palestinian people, including the right of return. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 7145:8285; `dsa-2026-program-normalized-40060dd6f6dd-007`)

**Pairwise distinctions:**
- Democratic / Republican: Both include Israel's security and negotiated statehood, but Democratic examples explicitly pair these with Palestinian freedom and assistance; Republican examples stress defensible borders and conditions.
- Democratic / DSA: Democratic examples combine Israeli security with negotiated Palestinian statehood; DSA examples center ending occupation and aid, Palestinian return, BDS, and later ceasefire and accountability.
- Republican / DSA: Republican examples reject occupation framing and emphasize Israel's self-defense; DSA examples characterize occupation as central, demand ending aid, and assert Palestinian return and resistance rights.

#### Position cluster 21: Trump Administration Records and Partisan Critiques

**Democratic:** From 2016 through 2024, documents criticize Trump on alliances and diplomacy, war and rights, labor, pandemic management, jobs, health programs, political violence, and democratic norms.
Scope caution: These are partisan evaluations and asserted records across many domains, not one policy position.
- Donald Trump would overturn more than 50 years of American foreign policy by abandoning NATO partners. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 144805:145853; `democratic-2016-normalized-b4f43c23e8c1-006`)
- President Trump's failure to pay attention to early intelligence reports about the pandemic wasted critical weeks in which preparation for the outbreak could have occurred. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 10390:11531; `democratic-2020-normalized-bb1bcc2747c2-001`)
- President Trump's dereliction of duty has caused the loss of tens of millions of American jobs. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 2561:2985; `democratic-2020-normalized-8a45b4bf8105-007`)
- Donald Trump weakened global democratic norms. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 233376:233831; `democratic-2024-normalized-306753327989-009`)
- Donald Trump attempted to cut health care, affordable housing, and Social Security during his presidency. ([2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); 2024; scoped characters 165552:166140; `democratic-2024-normalized-63be03f4582c-004`)

**Republican:** The 2024 examples praise Trump's trade, energy, growth, manufacturing, border, and national-pride record and promise continuation; one 2016 example attacks Obama's executive immigration actions.
Scope caution: Only 15 examples appear, from two bundles; the evidence is overwhelmingly the 2024 platform.
- A president mocked America's immigration laws by making himself superior to the will of the nation. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 106870:108139; `republican-2016-normalized-6168430fdff6-003`)
- President Trump turned American trade policy around, protecting U.S. producers and renegotiating failed agreements. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 16205:16227; `republican-2024-normalized-007a594371a0-009`)
- Under President Trump, the U.S. became the Number One Producer of Oil and Natural Gas in the World. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 9939:10370; `republican-2024-normalized-7eea32ad5c94-008`)
- President Donald J. Trump's Policies spurred Historic Economic Growth, Job Creation, and a Resurgence of American Manufacturing. ([2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform); 2024; scoped characters 1737:2208; `republican-2024-normalized-51f7b85d22c5-009`)

**DSA:** Documents criticize Trump-era immigration, labor, LGBTQ, Iran, Yemen, sanctions, and crisis policies, depict nationalist scapegoating, and later fault Democrats for adopting Trump-like immigration positions.
Scope caution: The packet is concentrated in 2016–2023 statements and includes predictions, campaign analysis, and organizational observations.
- A groundswell of racist and anti-immigrant political organization exists, represented most dramatically by Donald Trump’s presidential campaign. ([Resistance Rising - published summary of DSA strategy](https://www.dsausa.org/files/2016/06/Resistance_Rising.pdf); 2016-06; scoped characters 5846:7498; `dsa-2016-strategy-normalized-92f137c832c0-006`)
- Donald Trump has opposed marriage equality and committed himself to the harassment of countless LGBTQIA+ women, people of color, indigenous cousins and immigrants. ([Statement on Lesbian, Gay, Bisexual, Transgender, Queer and Intersex Rights](https://www.dsausa.org/wp-json/wp/v2/statement/409); 2017-05-11; scoped characters 3735:4365; `dsa-statement-409-normalized-335a09bbcb79-006`)
- Donald Trump has reimplemented brutal, unilateral sanctions against Iran that are inflicting real suffering on Iranian civilians in no way responsible for the policies of their government. ([Urgent Call For Action Against A U.S. War On Iran](https://www.dsausa.org/wp-json/wp/v2/statement/4386); 2020-01-03; scoped characters 985:1776; `dsa-statement-4386-normalized-89aab4241a6d-004`)
- The Trump administration’s proposed payroll tax cut would endanger some vulnerable populations by gutting funding to Social Security and Medicare. ([Now is the Time for Solidarity: DSA National Statement on COVID-2019/Es la hora de solidaridad: Comunicación nacional de DSA acerca de COVID-19](https://www.dsausa.org/wp-json/wp/v2/statement/4626); 2020-03-12; scoped characters 6140:6921; `dsa-statement-4626-normalized-d7c9a92b264d-005`)
- The program characterizes Democratic elites as embracing Trump immigration policies that it calls racist. ([Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); 2024-08; scoped characters 2869:3829; `dsa-2024-program-normalized-43f2e9413efb-repair-d5f43d07d995-002`)

**Pairwise distinctions:**
- Democratic / Republican: Democratic examples portray Trump's record as harmful across diplomacy, health, jobs, and democracy; Republican 2024 examples portray it as economic, energy, trade, and border success.
- Democratic / DSA: Both criticize Trump, but Democratic examples defend alliances, public programs, and administration competence; DSA examples emphasize class, labor, anti-imperial, immigration, and bipartisan continuity critiques.
- Republican / DSA: Republican 2024 examples praise Trump's economic, energy, and border record; DSA examples condemn his anti-labor, anti-immigrant, sanctions, and militarized foreign policies.
### Detailed density comparisons

Each large map is paired with numbered representative claims and the saved region's claim/bundle support. Keywords are retrieval aids, not reviewed topic labels. Markers locate the selected examples, not region boundaries. Natural-log density contrasts are evaluated in the higher-dimensional KDE space, not the two-dimensional display. A positive value means denser first-group language; it is not a topic-share ratio, policy agreement or a regional average.

![Detailed density map, expanded](../figures/national_claims/full/topics/../expanded/density_details/democratic_vs_republican_1.png)

| Marker | Keywords | Claims / documents / bundles | Raw group counts | Example ln ratio | Source-linked claim |
|---|---|---:|---|---:|---|
| 1 | americans, pandemic, covid, 19 | 42 / 5 / 5 | {"democratic": 42} | +1.30 | The COVID-19 pandemic has made a difference in values painfully and brutally clear. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 74949:75582) |
| 2 | drug, medicare, seniors, prescription | 38 / 9 / 9 | {"republican": 10, "democratic": 28} | +0.03 | The current Medicare drug program allows drug companies to change the price of prescriptions more frequently than seniors can change their plans. ([2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform); 2004; scoped characters 83427:83892) |
| 3 | religious, right, freedom, rights | 57 / 6 / 6 | {"republican": 57} | -1.46 | Assertion of every citizen's right to apply religious values to public policy. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 51296:52670) |

[Complete region evidence](../data/analysis/national_claims/full/topics/../expanded/density_region_evidence.csv)

![Detailed density map, expanded](../figures/national_claims/full/topics/../expanded/density_details/democratic_vs_republican_2.png)

| Marker | Keywords | Claims / documents / bundles | Raw group counts | Example ln ratio | Source-linked claim |
|---|---|---:|---|---:|---|
| 1 | democrats, believe, united, democratic | 40 / 5 / 5 | {"democratic": 40} | +3.31 | The Democratic Party believes the United States has the responsibility to shape globalization so that it reflects the needs and values of the American people. ([2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); 2000; scoped characters 115472:115724) |
| 2 | russia, nuclear, states, united | 36 / 11 / 11 | {"democratic": 15, "republican": 21} | -0.08 | There are today more positive, practical ways to reassure Russia that missile defenses are a search for common security, not for unilateral advantage. ([2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform); 2000; scoped characters 171646:172834) |
| 3 | washington, district, columbia, federal | 33 / 6 / 6 | {"republican": 33} | -1.07 | Washington is identified. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 203495:203505) |

[Complete region evidence](../data/analysis/national_claims/full/topics/../expanded/density_region_evidence.csv)

![Detailed density map, expanded](../figures/national_claims/full/topics/../expanded/density_details/democratic_vs_dsa_1.png)

| Marker | Keywords | Claims / documents / bundles | Raw group counts | Example ln ratio | Source-linked claim |
|---|---|---:|---|---:|---|
| 1 | africa, commitment, african, administration | 81 / 7 / 7 | {"democratic": 81} | +2.76 | Commitment to continue partnering with African nations to combat al-Qaeda affiliates in places like Somalia. ([2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); 2012; scoped characters 141623:142380) |
| 2 | vote, support, voting, commitment | 69 / 13 / 10 | {"dsa": 12, "democratic": 57} | -0.45 | Commitment to fight to end long lines at voting booths. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 158596:160012) |
| 3 | commitment, socialism, capitalism, socialist | 29 / 12 / 7 | {"dsa": 29} | -6.40 | Commitment to talk socialism and endeavor to educate the public as to the role the undemocratic nature of capitalism has played in causing the current economic crisis. ([2011 adopted convention priorities - full ten-page resolution](https://web.archive.org/web/20130108175613id_/http://www.dsausa.org/convention2011/report/Priorities%20Resolution.pdf); 2011; scoped characters 10717:12079) |

[Complete region evidence](../data/analysis/national_claims/full/topics/../expanded/density_region_evidence.csv)

![Detailed density map, expanded](../figures/national_claims/full/topics/../expanded/density_details/democratic_vs_dsa_2.png)

| Marker | Keywords | Claims / documents / bundles | Raw group counts | Example ln ratio | Source-linked claim |
|---|---|---:|---|---:|---|
| 1 | obama, president, administration, barack | 75 / 3 / 3 | {"democratic": 75} | +1.87 | President Obama's administration has enhanced opportunities for English-language learning and immigrant integration. ([2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); 2012; scoped characters 66775:67885) |
| 2 | transit, public, transportation, rail | 44 / 9 / 9 | {"democratic": 37, "dsa": 7} | +0.25 | Support for investment in public transportation including rail, because businesses can only function when workers can get to their place of employment. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 133738:135336) |
| 3 | democratic, socialists, america, reject | 28 / 16 / 4 | {"dsa": 28} | -10.28 | The Democratic Socialists of America reject xenophobia. ([Now is the Time for Solidarity: DSA National Statement on COVID-2019/Es la hora de solidaridad: Comunicación nacional de DSA acerca de COVID-19](https://www.dsausa.org/wp-json/wp/v2/statement/4626); 2020-03-12; scoped characters 1977:2224) |

[Complete region evidence](../data/analysis/national_claims/full/topics/../expanded/density_region_evidence.csv)

![Detailed density map, expanded](../figures/national_claims/full/topics/../expanded/density_details/republican_vs_dsa_1.png)

| Marker | Keywords | Claims / documents / bundles | Raw group counts | Example ln ratio | Source-linked claim |
|---|---|---:|---|---:|---|
| 1 | farmers, agriculture, agricultural, farm | 59 / 5 / 5 | {"republican": 59} | +2.32 | The success of America's farmers and ranchers is essential to the success of the American economy. ([2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform); 2004; scoped characters 220985:221644) |
| 2 | support, banks, choice, financial | 43 / 13 / 11 | {"republican": 24, "dsa": 19} | +0.44 | Support for the regulation of international and domestic financial transactions. ([2001 convention resolution on war and terrorism](https://www.dsausa.org/files/2019/07/DL-2001-Convention-Coverage.pdf); 2002; scoped characters 0:1258) |
| 3 | democratic, socialists, america, reject | 28 / 16 / 4 | {"dsa": 28} | -8.80 | The Democratic Socialists of America reject xenophobia. ([Now is the Time for Solidarity: DSA National Statement on COVID-2019/Es la hora de solidaridad: Comunicación nacional de DSA acerca de COVID-19](https://www.dsausa.org/wp-json/wp/v2/statement/4626); 2020-03-12; scoped characters 1977:2224) |

[Complete region evidence](../data/analysis/national_claims/full/topics/../expanded/density_region_evidence.csv)

![Detailed density map, expanded](../figures/national_claims/full/topics/../expanded/density_details/republican_vs_dsa_2.png)

| Marker | Keywords | Claims / documents / bundles | Raw group counts | Example ln ratio | Source-linked claim |
|---|---|---:|---|---:|---|
| 1 | russia, states, united, nuclear | 56 / 5 / 5 | {"republican": 56} | +3.34 | The United States condemns the Russian Federation's attempts to intimidate states formerly under Soviet domination in order to prevent their deploying missile defenses. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 36984:38163) |
| 2 | support, public, criminals, opposition | 43 / 10 / 9 | {"republican": 28, "dsa": 15} | +0.11 | Courts should not tie the hands of prison officials in dealing with problems in correctional institutions. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 170396:171105) |
| 3 | commitment, socialism, socialist, capitalism | 26 / 11 / 6 | {"dsa": 26} | -3.88 | Commitment to talk socialism and endeavor to educate the public as to the role the undemocratic nature of capitalism has played in causing the current economic crisis. ([2011 adopted convention priorities - full ten-page resolution](https://web.archive.org/web/20130108175613id_/http://www.dsausa.org/convention2011/report/Priorities%20Resolution.pdf); 2011; scoped characters 10717:12079) |

[Complete region evidence](../data/analysis/national_claims/full/topics/../expanded/density_region_evidence.csv)

![Detailed density map, strict](../figures/national_claims/full/topics/../strict/density_details/democratic_vs_republican_1.png)

| Marker | Keywords | Claims / documents / bundles | Raw group counts | Example ln ratio | Source-linked claim |
|---|---|---:|---|---:|---|
| 1 | gore, al, clinton, president | 98 / 2 / 2 | {"democratic": 98} | +2.07 | Al Gore will stand firm in support of the Davis-Bacon act and the Service Contract act. ([2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); 2000; scoped characters 59642:60497) |
| 2 | iran, iranian, nuclear, people | 64 / 12 / 12 | {"democratic": 33, "republican": 31} | +0.06 | Iran is a growing threat in the region. ([2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); 2008; scoped characters 105183:106121) |
| 3 | veterans, military, service, freedom | 32 / 5 / 5 | {"republican": 32} | -0.72 | The sacrifices of the men and women of the territories who protect freedom through service in the U.S. Armed Forces are honored. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 124581:125546) |

[Complete region evidence](../data/analysis/national_claims/full/topics/../strict/density_region_evidence.csv)

![Detailed density map, strict](../figures/national_claims/full/topics/../strict/density_details/democratic_vs_republican_2.png)

| Marker | Keywords | Claims / documents / bundles | Raw group counts | Example ln ratio | Source-linked claim |
|---|---|---:|---|---:|---|
| 1 | commitment, workers, support, labor | 81 / 7 / 7 | {"democratic": 81} | +0.72 | Support for prioritizing and strongly enforcing provisions on decent work and worker's rights in all American diplomatic, trade, and programmatic efforts. ([2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); 2016; scoped characters 160604:161072) |
| 2 | president, bush, george, america | 35 / 3 / 3 | {"republican": 32, "democratic": 3} | -0.09 | Under President Bush's leadership, the Administration has nearly doubled the amount of spectrum available for innovative wireless broadband applications such as Wi-Fi and Wi-Max. ([2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform); 2004; scoped characters 194292:194901) |
| 3 | constitution, states, government, law | 29 / 6 / 6 | {"republican": 29} | -0.95 | No expansion of governmental powers should occur at the expense of constitutional liberties. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 139226:139700) |

[Complete region evidence](../data/analysis/national_claims/full/topics/../strict/density_region_evidence.csv)

![Detailed density map, strict](../figures/national_claims/full/topics/../strict/density_details/democratic_vs_dsa_1.png)

| Marker | Keywords | Claims / documents / bundles | Raw group counts | Example ln ratio | Source-linked claim |
|---|---|---:|---|---:|---|
| 1 | gore, al, clinton, president | 98 / 2 / 2 | {"democratic": 98} | +3.23 | Al Gore will stand firm in support of the Davis-Bacon act and the Service Contract act. ([2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); 2000; scoped characters 59642:60497) |
| 2 | commitment, support, public, lands | 66 / 8 / 8 | {"democratic": 60, "dsa": 6} | +0.43 | Commitment to remediate Superfund and other contaminated sites to protect children's health. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 161561:162330) |
| 3 | dsa, fights, capitalist, state | 21 / 3 / 3 | {"dsa": 21} | -11.68 | DSA strongly opposes rainbow capitalism, in which banks, police, and corporations wrap themselves in Pride flags during June in order to make profit, all while exploiting queer workers. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 34344:34951) |

[Complete region evidence](../data/analysis/national_claims/full/topics/../strict/density_region_evidence.csv)

![Detailed density map, strict](../figures/national_claims/full/topics/../strict/density_details/democratic_vs_dsa_2.png)

| Marker | Keywords | Claims / documents / bundles | Raw group counts | Example ln ratio | Source-linked claim |
|---|---|---:|---|---:|---|
| 1 | america, people, americans, american | 29 / 7 / 7 | {"democratic": 29} | +4.06 | Americans believe that their fates and fortunes are bound to rise and fall together. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 1155:1610) |
| 2 | tax, support, taxes, commitment | 57 / 10 / 10 | {"dsa": 6, "democratic": 51} | -0.16 | Easier and more equitable access to tax provisions will help working families build wealth. ([2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); 2020; scoped characters 60906:61517) |
| 3 | capitalism, future, people, work | 17 / 2 / 2 | {"dsa": 17} | -4.31 | In a future without capitalism, work may not be solely a means to pay bills. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 0:1295) |

[Complete region evidence](../data/analysis/national_claims/full/topics/../strict/density_region_evidence.csv)

![Detailed density map, strict](../figures/national_claims/full/topics/../strict/density_details/republican_vs_dsa_1.png)

| Marker | Keywords | Claims / documents / bundles | Raw group counts | Example ln ratio | Source-linked claim |
|---|---|---:|---|---:|---|
| 1 | small, businesses, business, new | 34 / 5 / 5 | {"republican": 34} | +3.39 | Small businesses create most of the country's new jobs. ([2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform); 2008; scoped characters 74579:74921) |
| 2 | transportation, infrastructure, support, railroad | 55 / 7 / 7 | {"republican": 52, "dsa": 3} | -0.14 | The 1998 Transportation Equity Act for the Twenty-First Century and this year's Aviation Investment and Reform Act unlock transportation trust funds to invest dollars motorists and the traveling public have already paid. ([2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform); 2000; scoped characters 127148:127938) |
| 3 | dsa, fights, capitalist, state | 21 / 3 / 3 | {"dsa": 21} | -10.19 | DSA strongly opposes rainbow capitalism, in which banks, police, and corporations wrap themselves in Pride flags during June in order to make profit, all while exploiting queer workers. ([2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); 2021-11-09; scoped characters 34344:34951) |

[Complete region evidence](../data/analysis/national_claims/full/topics/../strict/density_region_evidence.csv)

![Detailed density map, strict](../figures/national_claims/full/topics/../strict/density_details/republican_vs_dsa_2.png)

| Marker | Keywords | Claims / documents / bundles | Raw group counts | Example ln ratio | Source-linked claim |
|---|---|---:|---|---:|---|
| 1 | space, innovation, sustain, preeminence | 23 / 5 / 5 | {"republican": 23} | +3.52 | NASA's work has produced spectacular results, including building the world's most powerful rockets, landing men on the Moon, sending robotic spacecraft throughout the solar system and beyond, building the International Space Station, and launching space-based telescopes that allow scientists to better understand the universe. ([2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform); 2012; scoped characters 113240:114249) |
| 2 | judges, court, congress, amendment | 38 / 8 / 8 | {"dsa": 2, "republican": 36} | -0.05 | Appointments of constitutionally-minded Supreme Court justices will enable courts to begin to reverse the long line of activist decisions — including Roe, Obergefell, and the Obamacare cases — that have usurped Congress's and states' lawmaking authority. ([2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform); 2016; scoped characters 42621:44015) |
| 3 | capitalism, future, people, work | 17 / 2 / 2 | {"dsa": 17} | -3.18 | In a future without capitalism, work may not be solely a means to pay bills. ([Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); 2026-09; scoped characters 0:1295) |

[Complete region evidence](../data/analysis/national_claims/full/topics/../strict/density_region_evidence.csv)

### Expanded distribution

Largest absolute shares across all observed periods (not necessarily the most distinctive topics):

- **Democratic:** Community and Economic Support for Vulnerable Populations (8.9%); International Security and Cooperation Strategies (7.3%); Energy, Infrastructure, and Economic Development (6.7%).
- **Republican:** Opposition to Policies and Governing Authorities (7.6%); American Leadership and National-Power Narratives (7.3%); Community and Economic Support for Vulnerable Populations (6.4%).
- **DSA:** Critiques and Alternatives to Capitalism (8.3%); Voting Rights, Election Rules, and Representation (7.6%); Economic hardship and financial insecurity (6.5%).

Identity and narrative clusters describe rhetoric, not substantive policy priorities. Pooled shares mix periods and document genres; read the period analyses below before interpreting them as enduring differences.

![Topic shares, expanded](../figures/national_claims/full/topics/expanded/topic_distribution.png)

![Topic shares, expanded](../figures/national_claims/full/topics/expanded/topic_distribution_2.png)

![Topic shares, expanded](../figures/national_claims/full/topics/expanded/topic_distribution_3.png)

![Relative emphasis, expanded](../figures/national_claims/full/topics/expanded/vs_rest_emphasis.png)

![Relative emphasis, expanded](../figures/national_claims/full/topics/expanded/vs_rest_emphasis_2.png)

![Relative emphasis, expanded](../figures/national_claims/full/topics/expanded/vs_rest_emphasis_3.png)

Largest relative-emphasis ratios (all support levels remain eligible):

| Group | Topic | Share | Other-group mean | Difference (pp) | log2 ratio | Warnings |
|---|---|---:|---:|---:|---:|---|
| Democratic | Presidential Records, Promises, and Critiques | 6.7% | 1.7% | +5.02 | +1.97 | none |
| Democratic | Trump Administration Records and Partisan Critiques | 3.3% | 0.9% | +2.36 | +1.82 | bundle_sensitive_rank |
| Democratic | Energy, Infrastructure, and Economic Development | 6.7% | 3.5% | +3.28 | +0.96 | none |
| Republican | Rights, Freedoms, and Governmental Legitimacy | 6.3% | 3.2% | +3.10 | +0.98 | none |
| Republican | American Leadership and National-Power Narratives | 7.3% | 3.8% | +3.49 | +0.94 | none |
| Republican | Opposition to Policies and Governing Authorities | 7.6% | 4.5% | +3.05 | +0.74 | none |
| DSA | Critiques and Alternatives to Capitalism | 8.3% | 0.4% | +7.94 | +4.37 | none |
| DSA | Israeli-Palestinian Conflict: Sovereignty, Rights, and Assistance | 5.8% | 1.1% | +4.66 | +2.36 | none |
| DSA | Labor Rights and Unionization | 6.5% | 2.5% | +3.98 | +1.36 | none |

Pairwise contrast panels:

![Pairwise emphasis, expanded](../figures/national_claims/full/topics/expanded/pairwise_emphasis.png)

![Pairwise emphasis, expanded](../figures/national_claims/full/topics/expanded/pairwise_emphasis_2.png)

![Pairwise emphasis, expanded](../figures/national_claims/full/topics/expanded/pairwise_emphasis_3.png)

### Strict distribution

Largest absolute shares across all observed periods (not necessarily the most distinctive topics):

- **Democratic:** Community and Economic Support for Vulnerable Populations (8.9%); International Security and Cooperation Strategies (7.3%); Energy, Infrastructure, and Economic Development (6.7%).
- **Republican:** Opposition to Policies and Governing Authorities (7.6%); American Leadership and National-Power Narratives (7.3%); Community and Economic Support for Vulnerable Populations (6.4%).
- **DSA:** Voting Rights, Election Rules, and Representation (14.6%); Critiques and Alternatives to Capitalism (12.3%); Labor Rights and Unionization (8.1%).

Identity and narrative clusters describe rhetoric, not substantive policy priorities. Pooled shares mix periods and document genres; read the period analyses below before interpreting them as enduring differences.

![Topic shares, strict](../figures/national_claims/full/topics/strict/topic_distribution.png)

![Topic shares, strict](../figures/national_claims/full/topics/strict/topic_distribution_2.png)

![Topic shares, strict](../figures/national_claims/full/topics/strict/topic_distribution_3.png)

![Relative emphasis, strict](../figures/national_claims/full/topics/strict/vs_rest_emphasis.png)

![Relative emphasis, strict](../figures/national_claims/full/topics/strict/vs_rest_emphasis_2.png)

![Relative emphasis, strict](../figures/national_claims/full/topics/strict/vs_rest_emphasis_3.png)

Largest relative-emphasis ratios (all support levels remain eligible):

| Group | Topic | Share | Other-group mean | Difference (pp) | log2 ratio | Warnings |
|---|---|---:|---:|---:|---:|---|
| Democratic | Presidential Records, Promises, and Critiques | 6.7% | 1.5% | +5.21 | +2.15 | none |
| Democratic | Trump Administration Records and Partisan Critiques | 3.3% | 0.9% | +2.35 | +1.80 | none |
| Democratic | American Leadership and National-Power Narratives | 6.6% | 4.0% | +2.64 | +0.73 | bundle_sensitive_rank |
| Republican | Rights, Freedoms, and Governmental Legitimacy | 6.3% | 2.5% | +3.78 | +1.33 | none |
| Republican | Opposition to Policies and Governing Authorities | 7.6% | 3.8% | +3.82 | +1.01 | bundle_sensitive_rank |
| Republican | American Leadership and National-Power Narratives | 7.3% | 3.7% | +3.63 | +0.99 | none |
| DSA | Critiques and Alternatives to Capitalism | 12.3% | 0.4% | +11.89 | +4.93 | none |
| DSA | Labor Rights and Unionization | 8.1% | 2.5% | +5.61 | +1.69 | none |
| DSA | Israeli-Palestinian Conflict: Sovereignty, Rights, and Assistance | 3.3% | 1.1% | +2.16 | +1.54 | bundle_sensitive_rank |

Pairwise contrast panels:

![Pairwise emphasis, strict](../figures/national_claims/full/topics/strict/pairwise_emphasis.png)

![Pairwise emphasis, strict](../figures/national_claims/full/topics/strict/pairwise_emphasis_2.png)

![Pairwise emphasis, strict](../figures/national_claims/full/topics/strict/pairwise_emphasis_3.png)

### Topics over time

**Fixed-topic trends:** the same topic assignments are tracked in four-year adoption/publication periods. Within each period, each document/fallback bundle has equal group weight. Adoption dates take precedence when recorded; original date precision is retained. Missing periods remain gaps: neither reused platforms nor absent publications are carried forward as new independent observations. The final period is partial.

Relative time-series contrasts require all configured comparison groups for group-versus-rest baselines; pairwise contrasts require both organizations. These charts describe the changing composition of observed documents, not annual party positions or causal changes. One-document periods are visibly counted and flagged in the downloadable tables.

[Period coverage and support](../data/analysis/national_claims/full/topics/temporal_coverage.csv) · [All period shares](../data/analysis/national_claims/full/topics/temporal_shares.csv) · [Time-specific relative emphasis](../data/analysis/national_claims/full/topics/temporal_contrasts.csv) · [Adjacent observed-period changes](../data/analysis/national_claims/full/topics/temporal_changes.csv) · [Exact date choices](../data/analysis/national_claims/full/topics/temporal_document_dates.csv) · [Date exclusions](../data/analysis/national_claims/full/topics/temporal_exclusions.csv)

#### Expanded time views

Largest adjacent observed-period changes on the **fixed pooled taxonomy**. These can reflect changing rhetoric or document composition, not policy movement:

- **Democratic:** Presidential Records, Promises, and Critiques: +23.2 percentage points (2020-2023 → 2024-2026; 1 → 1 bundles); Presidential Records, Promises, and Critiques: -13.0 percentage points (2012-2015 → 2016-2019; 1 → 1 bundles).

- **Republican:** Presidential Records, Promises, and Critiques: -10.1 percentage points (2004-2007 → 2008-2011; 1 → 1 bundles); Presidential Records, Promises, and Critiques: +8.3 percentage points (2000-2003 → 2004-2007; 1 → 1 bundles).

- **DSA:** U.S. Military Involvement and the War on Terror: -21.7 percentage points (2000-2003 → 2004-2007; 1 → 1 bundles); Israeli-Palestinian Conflict: Sovereignty, Rights, and Assistance: -13.3 percentage points (2008-2011 → 2012-2015; 1 → 1 bundles).

#### Figures for the piece

These six selected policy subjects pair the overall comparison with its timeline. Headlines are calculated from observed, unsmoothed shares; ratios require at least two contributing bundles on both sides. All groups remain visible, and both panels share a zero-based percentage scale. Short chart names are display labels, not new clusters or stance labels.

| Issue | Combined overall and timeline |
|---|---|
| Labor and unions | [PNG](../figures/national_claims/full/topics/expanded/piece/topic-003.png) |
| Taxes on income, wealth and corporations | [PNG](../figures/national_claims/full/topics/expanded/piece/topic-011.png) |
| Public education | [PNG](../figures/national_claims/full/topics/expanded/piece/topic-012.png) |
| Reproductive rights and gender-affirming care | [PNG](../figures/national_claims/full/topics/expanded/piece/topic-013.png) |
| Healthcare | [PNG](../figures/national_claims/full/topics/expanded/piece/topic-018.png) |
| Israel-Palestine | [PNG](../figures/national_claims/full/topics/expanded/piece/topic-022.png) |
#### Individual issue comparisons

Each standalone chart compares all organizations on one topic. Overall bars and observed-period lines are separate figures, suitable for individual embedding. Axes are shared across organizations and both views of the same topic; different issues can have different vertical scales. Missing evidence remains a gap. Actor and narrative topics retain their qualifications rather than being presented as coherent policy issues.

| Topic | Overall comparison | Over time |
|---|---|---|
| Energy, Infrastructure, and Economic Development | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-001_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-001_time.png) |
| Community and Economic Support for Vulnerable Populations | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-002_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-002_time.png) |
| Labor Rights and Unionization | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-003_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-003_time.png) |
| Economic Growth and Development Narratives | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-004_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-004_time.png) |
| Rights, Freedoms, and Governmental Legitimacy | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-005_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-005_time.png) |
| American Leadership and National-Power Narratives | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-006_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-006_time.png) |
| Immigration Policy: Reform, Enforcement, and Detention | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-008_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-008_time.png) |
| Voting Rights, Election Rules, and Representation | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-009_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-009_time.png) |
| Presidential Records, Promises, and Critiques | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-010_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-010_time.png) |
| Taxation of Income, Wealth, and Corporations | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-011_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-011_time.png) |
| Public Education: Access, Standards, and Accountability | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-012_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-012_time.png) |
| Reproductive Rights and Gender-Affirming Care | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-013_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-013_time.png) |
| International Security and Cooperation Strategies | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-014_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-014_time.png) |
| U.S. Military Involvement and the War on Terror | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-015_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-015_time.png) |
| Opposition to Policies and Governing Authorities | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-016_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-016_time.png) |
| Healthcare System Goals and Approaches | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-018_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-018_time.png) |
| Economic hardship and financial insecurity | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-019_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-019_time.png) |
| Critiques and Alternatives to Capitalism | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-020_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-020_time.png) |
| Criminal Justice: Punishment, Accountability, and Prison Reform | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-021_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-021_time.png) |
| Israeli-Palestinian Conflict: Sovereignty, Rights, and Assistance | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-022_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-022_time.png) |
| Trump Administration Records and Partisan Critiques | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-023_overall.png) | [PNG](../figures/national_claims/full/topics/expanded/issues/topic-023_time.png) |

![One-topic comparison over time](../figures/national_claims/full/topics/expanded/issues/topic-003_time.png)

#### Strict time views

Largest adjacent observed-period changes on the **fixed pooled taxonomy**. These can reflect changing rhetoric or document composition, not policy movement:

- **Democratic:** Presidential Records, Promises, and Critiques: +23.2 percentage points (2020-2023 → 2024-2026; 1 → 1 bundles); Presidential Records, Promises, and Critiques: -13.0 percentage points (2012-2015 → 2016-2019; 1 → 1 bundles).

- **Republican:** Presidential Records, Promises, and Critiques: -10.1 percentage points (2004-2007 → 2008-2011; 1 → 1 bundles); Presidential Records, Promises, and Critiques: +8.3 percentage points (2000-2003 → 2004-2007; 1 → 1 bundles).

- **DSA:** Community and Economic Support for Vulnerable Populations: -7.0 percentage points (2020-2023 → 2024-2026; 1 → 2 bundles); Israeli-Palestinian Conflict: Sovereignty, Rights, and Assistance: +3.9 percentage points (2020-2023 → 2024-2026; 1 → 2 bundles).

#### Figures for the piece

These six selected policy subjects pair the overall comparison with its timeline. Headlines are calculated from observed, unsmoothed shares; ratios require at least two contributing bundles on both sides. All groups remain visible, and both panels share a zero-based percentage scale. Short chart names are display labels, not new clusters or stance labels.

| Issue | Combined overall and timeline |
|---|---|
| Labor and unions | [PNG](../figures/national_claims/full/topics/strict/piece/topic-003.png) |
| Taxes on income, wealth and corporations | [PNG](../figures/national_claims/full/topics/strict/piece/topic-011.png) |
| Public education | [PNG](../figures/national_claims/full/topics/strict/piece/topic-012.png) |
| Reproductive rights and gender-affirming care | [PNG](../figures/national_claims/full/topics/strict/piece/topic-013.png) |
| Healthcare | [PNG](../figures/national_claims/full/topics/strict/piece/topic-018.png) |
| Israel-Palestine | [PNG](../figures/national_claims/full/topics/strict/piece/topic-022.png) |
#### Individual issue comparisons

Each standalone chart compares all organizations on one topic. Overall bars and observed-period lines are separate figures, suitable for individual embedding. Axes are shared across organizations and both views of the same topic; different issues can have different vertical scales. Missing evidence remains a gap. Actor and narrative topics retain their qualifications rather than being presented as coherent policy issues.

| Topic | Overall comparison | Over time |
|---|---|---|
| Energy, Infrastructure, and Economic Development | [PNG](../figures/national_claims/full/topics/strict/issues/topic-001_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-001_time.png) |
| Community and Economic Support for Vulnerable Populations | [PNG](../figures/national_claims/full/topics/strict/issues/topic-002_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-002_time.png) |
| Labor Rights and Unionization | [PNG](../figures/national_claims/full/topics/strict/issues/topic-003_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-003_time.png) |
| Economic Growth and Development Narratives | [PNG](../figures/national_claims/full/topics/strict/issues/topic-004_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-004_time.png) |
| Rights, Freedoms, and Governmental Legitimacy | [PNG](../figures/national_claims/full/topics/strict/issues/topic-005_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-005_time.png) |
| American Leadership and National-Power Narratives | [PNG](../figures/national_claims/full/topics/strict/issues/topic-006_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-006_time.png) |
| Immigration Policy: Reform, Enforcement, and Detention | [PNG](../figures/national_claims/full/topics/strict/issues/topic-008_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-008_time.png) |
| Voting Rights, Election Rules, and Representation | [PNG](../figures/national_claims/full/topics/strict/issues/topic-009_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-009_time.png) |
| Presidential Records, Promises, and Critiques | [PNG](../figures/national_claims/full/topics/strict/issues/topic-010_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-010_time.png) |
| Taxation of Income, Wealth, and Corporations | [PNG](../figures/national_claims/full/topics/strict/issues/topic-011_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-011_time.png) |
| Public Education: Access, Standards, and Accountability | [PNG](../figures/national_claims/full/topics/strict/issues/topic-012_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-012_time.png) |
| Reproductive Rights and Gender-Affirming Care | [PNG](../figures/national_claims/full/topics/strict/issues/topic-013_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-013_time.png) |
| International Security and Cooperation Strategies | [PNG](../figures/national_claims/full/topics/strict/issues/topic-014_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-014_time.png) |
| U.S. Military Involvement and the War on Terror | [PNG](../figures/national_claims/full/topics/strict/issues/topic-015_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-015_time.png) |
| Opposition to Policies and Governing Authorities | [PNG](../figures/national_claims/full/topics/strict/issues/topic-016_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-016_time.png) |
| Healthcare System Goals and Approaches | [PNG](../figures/national_claims/full/topics/strict/issues/topic-018_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-018_time.png) |
| Economic hardship and financial insecurity | [PNG](../figures/national_claims/full/topics/strict/issues/topic-019_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-019_time.png) |
| Critiques and Alternatives to Capitalism | [PNG](../figures/national_claims/full/topics/strict/issues/topic-020_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-020_time.png) |
| Criminal Justice: Punishment, Accountability, and Prison Reform | [PNG](../figures/national_claims/full/topics/strict/issues/topic-021_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-021_time.png) |
| Israeli-Palestinian Conflict: Sovereignty, Rights, and Assistance | [PNG](../figures/national_claims/full/topics/strict/issues/topic-022_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-022_time.png) |
| Trump Administration Records and Partisan Critiques | [PNG](../figures/national_claims/full/topics/strict/issues/topic-023_overall.png) | [PNG](../figures/national_claims/full/topics/strict/issues/topic-023_time.png) |

![One-topic comparison over time](../figures/national_claims/full/topics/strict/issues/topic-003_time.png)

### Independently discovered topics within each period

Unlike the fixed-topic trends above, each period gets its own PCA, clustering, keywords and evidence packets, using only documents observed in that period. The number and meaning of clusters can differ. The strict view reuses that period's expanded assignments; it does not fit sparse adopted-only evidence separately.

Names summarize bounded local-Gemma evidence packets, not a pre-existing policy taxonomy. Source-bound assistant revisions are identified below and in the review record; original model replies remain unchanged.

**Evidence review:** 64/64 period-topic labels reviewed against bounded representative claims; 34 source-bound assistant revisions. This is not independent human gold or whole-cluster validation.

Adjacent-period centroid cosine similarities suggest possible thematic continuity. Only mutual nearest matches above 0.80 are called candidates. Neither a low similarity nor an unmatched topic proves that an issue first appeared or disappeared. Source coverage, rhetorical framing and cluster boundaries can all change.

[Period fits and diagnostics](../data/analysis/national_claims/full/topics/evolution/period_fits.json) · [Within-period shares](../data/analysis/national_claims/full/topics/evolution/shares.csv) · [Within-period contrasts and warnings](../data/analysis/national_claims/full/topics/evolution/contrasts.csv) · [Adjacent-period similarities](../data/analysis/national_claims/full/topics/evolution/adjacent_matches.csv) · [Representative source evidence](../data/analysis/national_claims/full/topics/evolution/representatives.csv) · [Label review and provenance](../data/analysis/national_claims/full/topics/evolution/label_review.json) · [Period coverage](../data/analysis/national_claims/full/topics/evolution/coverage.csv)

#### 2000-2003: observed themes

3,379 claims from 10 documents; 12 independently discovered topics. Fit status: complete. Cosine silhouette: 0.070.

Method: `weighted_kmeans`; unweighted assignment coverage: 100.0%. Low separation and mixed narrative clusters limit policy interpretation.

**Expanded reading:** topic shares below are within this period, not measurements of a permanent political position.

- Democratic: Economic growth, distribution and competitiveness (16.4%); Party identities, missions and competing narratives (15.6%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- Republican: Voting rights, benefits and state labor laws (19.5%); Economic growth, distribution and competitiveness (16.5%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- DSA: Responses to Terrorism and International Political Freedom (19.9%); Coalition building and mixed institutional commitments (17.6%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.

![Period-specific topics, expanded](../figures/national_claims/full/topics/evolution/expanded/period_2000-2003.png)

**Strict reading:** topic shares below are within this period, not measurements of a permanent political position.

- Democratic: Economic growth, distribution and competitiveness (16.4%); Party identities, missions and competing narratives (15.6%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- Republican: Voting rights, benefits and state labor laws (19.5%); Economic growth, distribution and competitiveness (16.5%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- DSA: no observed documents in this view.

![Period-specific topics, strict](../figures/national_claims/full/topics/evolution/strict/period_2000-2003.png)

| Period topic | Closest preceding theme | Cosine | Interpretation |
|---|---|---:|---|

Period-specific label summaries and inspectable source examples:

**Economic growth, distribution and competitiveness** (`period-2000-topic-001`): Claims discuss economic expansion, its distributional effects and national competitiveness. Democratic examples emphasize growth and worker skills; Republican examples credit tax, regulatory and trade policies; DSA examples argue that growth mainly benefited the well-off.

Caveat: Descriptions of economic performance and its causes are document assertions, not independently verified economic findings.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> With trade and investments in giving American workers the skills they need, the U.S. can out-compete workers anywhere in the world.

Democratic — [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); `democratic-2000-normalized-2d154b3bd0b8-014`.

> The great economic expansion of the last decade primarily benefited the well off.

DSA — [2001 convention national priorities resolution](https://www.dsausa.org/files/2019/07/DL-2001-Convention-Coverage.pdf); `dsa-2001-convention-priorities-normalized-f35a6ece882e-007`.

**Voting rights, benefits and state labor laws** (`period-2000-topic-002`): Examples range from defending voting rights and restoring felon suffrage to unemployment benefits, immigrant due process and benefits, charitable giving and education, and state right-to-work laws.

Caveat: Mixed policy cluster; immigrant due-process claims do not establish a position on immigrant suffrage.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Commitment to improve benefits in the nation's unemployment system.

Democratic — [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); `democratic-2000-normalized-6f5c11a781d7-014`.

> Support for efforts to defend the right to vote.

DSA — [2003 resolution on electoral reform](https://web.archive.org/web/20040110235906id_/http://www.dsausa.org/convention2003/report/r-electoral.html); `dsa-2003-electoral-normalized-6d2b6566d517-012`.

**Global Poverty, Economic Inequality, and Political Instability** (`period-2000-topic-003`): Claims address global poverty, with one noting over a billion people live on less than $1 a day. Several claims link economic conditions – including recession and inequality – to political instability and the growth of extremist groups. The U.S. is also described as facing internal challenges related to drug violence.

Caveat: Mixed subtopics: includes international development, domestic drug policy, and critiques of U.S. intelligence.

> More than 1 billion of the Earth's inhabitants live on less than $1 a day, inviting social dislocation, violence, and war.

Democratic — [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); `democratic-2000-normalized-db6e404196a5-009`.

> Military action that leaves in place an international economy that promotes poverty and inequality throughout the world cannot prevent the growth of extremist groups.

DSA — [2001 convention national priorities resolution](https://www.dsausa.org/files/2019/07/DL-2001-Convention-Coverage.pdf); `dsa-2001-convention-priorities-normalized-f35a6ece882e-006`.

**Coalition building and mixed institutional commitments** (`period-2000-topic-004`): DSA examples concern collaboration with communities of color and a coalition campaign for Wal-Mart workers. Other examples address legal and civil-society institutions, civil-rights enforcement, nonprofit protections and action on AIDS.

Caveat: Broad organizing and commitment language, not a single policy issue; the AIDS example does not establish a civil-society position.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Commitment to continue to support the development of judiciary, legal systems, media and civil society organizations.

Democratic — [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); `democratic-2000-normalized-93fadee8da59-008`.

> Commitment to consistently look for opportunities to work with activists in communities of color.

DSA — [2001 convention national priorities resolution](https://www.dsausa.org/files/2019/07/DL-2001-Convention-Coverage.pdf); `dsa-2001-convention-priorities-normalized-cf1eef463e22-008`.

**Party identities, missions and competing narratives** (`period-2000-topic-005`): Democratic claims link party beliefs to Social Security and communities, while a Republican example criticizes a Democratic tax increase and another frames party outreach. DSA examples describe its democratic-socialist mission and coalition strategy.

Caveat: Party self-descriptions and criticisms across unrelated policies, not a shared stance on Social Security or taxation.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Democrats believe in using prosperity to save Social Security.

Democratic — [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); `democratic-2000-normalized-0c700669dee2-004`.

> DSA aims to establish democratic socialism by helping to build progressive coalitions to win victories that move the United States towards greater democracy.

DSA — [2003 adopted working mission statement](https://web.archive.org/web/20040227005032id_/http://www.dsausa.org/convention2003/report/r-mission.html); `dsa-2003-mission-normalized-20f699d8e4de-006`.

**Gore-centered campaign and presidential-leadership narratives** (`period-2000-topic-006`): Democratic examples describe Gore's after-school agenda and cooperation with Armenia. Republican examples describe the scope of Gore's security agenda and the importance of presidential leadership on environmental issues.

Caveat: Actor-centered campaign language across unrelated policies, not a single policy position.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Al Gore believes in expanding after-school programs.

Democratic — [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); `democratic-2000-normalized-6bd9c0fed2ac-006`.

> Vice President Gore's "new security agenda" adds disease, climate, and all the world's ethnic or religious conflicts to an undiminished set of existing American responsibilities.

Republican — [2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform); `republican-2000-normalized-82a5e5527427-001`.

**Public School Choice and Educational Approaches** (`period-2000-topic-007`): These claims concern approaches to public education, including charter schools and magnet schools, as well as options like homeschooling. Both parties express support for expanding school choice, though through different mechanisms like allowing federal dollars to follow students or supporting various public school options. The claims also mention civic education requirements within schools.

Caveat: Mixed subtopics: school choice, curriculum, and parental options are all present.

> Support for democracy education, civic education, and service requirements in schools.

Democratic — [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); `democratic-2000-normalized-f946cf8e17d5-007`.

> Support for assisting states in closing the achievement gap and empowering needy families to escape persistently failing schools by allowing federal dollars to follow their children to the school of their choice.

Republican — [2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform); `republican-2000-normalized-c62b161acb55-002`.

**Responses to Terrorism and International Political Freedom** (`period-2000-topic-008`): These claims address responses to terrorism, with commitments to opposing concessions to terrorists and opposing unilateral responses. They also include commitments to promoting democracy, human rights, and political freedom internationally. Positions vary between supporting broad educational campaigns and protests and opposing government intervention in commerce.

Caveat: Mixed subtopics: includes both responses to specific events and broader foreign policy commitments.

> Commitment to continue to support the spread of democracy across Africa, Asia, and the Middle East.

Democratic — [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); `democratic-2000-normalized-93fadee8da59-007`.

> Commitment to participate, with others, in broad educational campaigns and protests consistent with its values on the issues of terrorism and the response to it.

DSA — [2001 convention national priorities resolution](https://www.dsausa.org/files/2019/07/DL-2001-Convention-Coverage.pdf); `dsa-2001-convention-priorities-normalized-fabd62226cf6-002`.

**Counterterrorism Policy and International Security** (`period-2000-topic-009`): These claims address policies related to combating terrorism, including assisting other governments and isolating state sponsors. Both Democratic and Republican platforms express commitment to strengthening defenses against weapons proliferation and maintaining military strength in this context. The Democratic Socialists of America acknowledge terrorist attacks and support limited multilateral armed force.

Caveat: Mixed positions can share a subject.

> Commitment to strengthen defense against the proliferation of conventional and unconventional weapons that threaten America.

Democratic — [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); `democratic-2000-normalized-053310f26dff-001`.

> Support for the limited and directed use of multilateral armed force.

DSA — [2001 convention resolution on war and terrorism](https://www.dsausa.org/files/2019/07/DL-2001-Convention-Coverage.pdf); `dsa-2001-war-terrorism-normalized-7bbb1e1c3390-008`.

**Republican party narratives and competing policy descriptions** (`period-2000-topic-010`): Democratic examples criticize Republican Medicare proposals involving HMOs and premiums. Republican examples describe support for new ideas, private sectors, open markets and open societies.

Caveat: Partisan criticism and self-description across several subjects; claims about Republican proposals are attributed assertions, not verified outcomes.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> The Republican Party has supported plans that would force elderly patients into HMOs.

Democratic — [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); `democratic-2000-normalized-6f072c85794d-011`.

> Republicans promote the development of new ideas and private sectors.

Republican — [2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform); `republican-2000-normalized-6ebdc3abd700-006`.

**Access to and Protection of Medicare and Healthcare** (`period-2000-topic-011`): Claims address access to healthcare, with both parties expressing support for it. Democrats emphasize ensuring full medical care for vulnerable populations and emergency coverage, while Republicans focus on protecting Medicare and ensuring access to high-quality, affordable care. Both parties acknowledge healthcare as a significant issue for Americans.

Caveat: Claims represent stated positions of the Democratic and Republican parties; no other groups are represented.

> Seniors and disabled Americans cannot afford to receive only part of the medical care they need.

Democratic — [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); `democratic-2000-normalized-d9166350088d-004`.

> Commitment to protect Medicare.

Republican — [2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform); `republican-2000-normalized-47da552ce620-003`.

**U.S. Policy Regarding Iraq and Saddam Hussein** (`period-2000-topic-012`): Claims address the U.S. stance toward removing Saddam Hussein from power in Iraq. The claims also describe the state of Iraq, including infrastructure destruction and the unraveling of efforts to control weapons of mass destruction. Differing perspectives are present regarding past successes in containing Iraq's power.

Caveat: Claims present positions on Iraq, but do not detail comprehensive policy proposals beyond regime change and proliferation concerns.

> The U.S. will work to see Saddam Hussein out of power.

Democratic — [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform); `democratic-2000-normalized-ad3592354251-008`.

> Iraq is being ravaged.

DSA — [2003 resolution on the occupation of Iraq](https://web.archive.org/web/20040110235717id_/http://www.dsausa.org/convention2003/report/r-iraq.html); `dsa-2003-iraq-normalized-aeabf36dcf1a-013`.

#### 2004-2007: observed themes

3,669 claims from 6 documents; 2 independently discovered topics. Fit status: complete. Cosine silhouette: 0.093.

Method: `hdbscan`; unweighted assignment coverage: 56.1%. Low separation and mixed narrative clusters limit policy interpretation. Two broad clusters plus substantial unclustered mass are not a complete account of the issues discussed.

**Expanded reading:** topic shares below are within this period, not measurements of a permanent political position.

- Democratic: Mixed domestic priorities and foreign-policy commitments (59.8%); Human rights, democratic institutions and economic justice (0.1%). Based on 1 bundle(s); unclustered share 40.1%. Source composition limits interpretation.
- Republican: Mixed domestic priorities and foreign-policy commitments (60.9%); Human rights, democratic institutions and economic justice (0.0%). Based on 1 bundle(s); unclustered share 39.1%. Source composition limits interpretation.
- DSA: Mixed domestic priorities and foreign-policy commitments (17.1%); Human rights, democratic institutions and economic justice (7.2%). Based on 1 bundle(s); unclustered share 75.7%. Source composition limits interpretation.

![Period-specific topics, expanded](../figures/national_claims/full/topics/evolution/expanded/period_2004-2007.png)

**Strict reading:** topic shares below are within this period, not measurements of a permanent political position.

- Democratic: Mixed domestic priorities and foreign-policy commitments (59.8%); Human rights, democratic institutions and economic justice (0.1%). Based on 1 bundle(s); unclustered share 40.1%. Source composition limits interpretation.
- Republican: Mixed domestic priorities and foreign-policy commitments (60.9%); Human rights, democratic institutions and economic justice (0.0%). Based on 1 bundle(s); unclustered share 39.1%. Source composition limits interpretation.
- DSA: no observed documents in this view.

![Period-specific topics, strict](../figures/national_claims/full/topics/evolution/strict/period_2004-2007.png)

| Period topic | Closest preceding theme | Cosine | Interpretation |
|---|---|---:|---|
| Mixed domestic priorities and foreign-policy commitments | Voting rights, benefits and state labor laws (2000-2003) | 0.952 | candidate_thematic_continuity |
| Human rights, democratic institutions and economic justice | Coalition building and mixed institutional commitments (2000-2003) | 0.926 | candidate_thematic_continuity |

Period-specific label summaries and inspectable source examples:

**Mixed domestic priorities and foreign-policy commitments** (`period-2004-topic-001`): Democratic examples concern family well-being and competitiveness; DSA examples concern Social Security, workplace safety, labor rights and antidiscrimination. Republican examples endorse Bush's Middle East freedom strategy.

Caveat: A broad mixed cluster, not a single policy issue; domestic-only labeling would omit the Republican foreign-policy examples.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Belief that strong, healthy families build a stronger America.

Democratic — [2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform); `democratic-2004-normalized-6a60b850a081-003`.

> Support for defending and expanding Social Security.

DSA — [An Economic Justice Agenda - adopted November 2007](https://www.dsausa.org/wp-json/wp/v2/strategy/612); `dsa-2007-economic-justice-normalized-500c699fb1db-001`.

**Human rights, democratic institutions and economic justice** (`period-2004-topic-002`): One Democratic example ties Russia's international integration to human rights, democratic institutions and independent media. DSA examples advocate progressive taxation, public goods, social insurance, labor rights and global institutions that improve living and human-rights standards.

Caveat: Broad domestic and international agendas; no Republican example is present in this packet and shared subject matter does not establish common positions.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Respect for human rights, the rule of law, and Russia's fledgling democratic institutions and independent media outlets are essential to Russia's continued integration into international institutions and the global economy.

Democratic — [2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform); `democratic-2004-normalized-c823381ac4e5-003`.

> By uniting behind a program that restores faith in democratic government, re-institutes progressive taxation, defends and extends public goods and social insurance, restores and expands labor rights, and builds just global institutions, democratic forces can curb the power of corporate elites and reverse corporate globalization’s exacerbation of inequality.

DSA — [An Economic Justice Agenda - adopted November 2007](https://www.dsausa.org/wp-json/wp/v2/strategy/612); `dsa-2007-economic-justice-normalized-9bc5b8b5d38b-001`.

#### 2008-2011: observed themes

3,029 claims from 8 documents; 2 independently discovered topics. Fit status: complete. Cosine silhouette: 0.109.

Method: `hdbscan`; unweighted assignment coverage: 55.9%. Low separation and mixed narrative clusters limit policy interpretation. Two broad clusters plus substantial unclustered mass are not a complete account of the issues discussed.

**Expanded reading:** topic shares below are within this period, not measurements of a permanent political position.

- Democratic: Government Economic Role and Public Spending (64.9%); Israeli-Palestinian security, rights and two-state diplomacy (0.7%). Based on 1 bundle(s); unclustered share 34.4%. Source composition limits interpretation.
- Republican: Government Economic Role and Public Spending (44.2%); Israeli-Palestinian security, rights and two-state diplomacy (0.9%). Based on 1 bundle(s); unclustered share 54.8%. Source composition limits interpretation.
- DSA: Government Economic Role and Public Spending (39.2%); Israeli-Palestinian security, rights and two-state diplomacy (12.5%). Based on 1 bundle(s); unclustered share 48.3%. Source composition limits interpretation.

![Period-specific topics, expanded](../figures/national_claims/full/topics/evolution/expanded/period_2008-2011.png)

**Strict reading:** topic shares below are within this period, not measurements of a permanent political position.

- Democratic: Government Economic Role and Public Spending (64.9%); Israeli-Palestinian security, rights and two-state diplomacy (0.7%). Based on 1 bundle(s); unclustered share 34.4%. Source composition limits interpretation.
- Republican: Government Economic Role and Public Spending (44.2%); Israeli-Palestinian security, rights and two-state diplomacy (0.9%). Based on 1 bundle(s); unclustered share 54.8%. Source composition limits interpretation.
- DSA: no observed documents in this view.

![Period-specific topics, strict](../figures/national_claims/full/topics/evolution/strict/period_2008-2011.png)

| Period topic | Closest preceding theme | Cosine | Interpretation |
|---|---|---:|---|
| Government Economic Role and Public Spending | Mixed domestic priorities and foreign-policy commitments (2004-2007) | 0.988 | candidate_thematic_continuity |
| Israeli-Palestinian security, rights and two-state diplomacy | Mixed domestic priorities and foreign-policy commitments (2004-2007) | 0.812 | uncertain_match_not_proof_of_new_topic |

Period-specific label summaries and inspectable source examples:

**Government Economic Role and Public Spending** (`period-2008-topic-001`): These claims address the role of the U.S. federal government in the economy, with commitments to both restructuring the economy and limiting government intrusion. There are also stated goals to provide assistance to states and localities, alongside commitments to end wasteful spending on ineffective programs. These positions reflect differing views on the appropriate level and type of government involvement.

Caveat: mixed-subtopic/stance

> Commitment to work to provide real opportunities for all Americans suffering from disadvantage.

Democratic — [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); `democratic-2008-normalized-4794e91f1cfe-006`.

> Commitment to fight to restructure the U.S. economy in a democratic direction.

DSA — [2009 convention national priorities resolution](https://dlarchive.dsausa.org/wp-content/uploads/2018/12/DL_2010_V037_03.pdf); `dsa-2009-priorities-normalized-69ef366c0cec-004`.

**Israeli-Palestinian security, rights and two-state diplomacy** (`period-2008-topic-002`): Democratic and Republican examples discuss Israel's security and diplomatic partners, including a Republican two-state vision. DSA examples criticize occupation and injustice while calling for a sustained negotiated two-state settlement following the Gaza ceasefire.

Caveat: Positions differ in emphasis and conditions; no supplied example establishes unconditional support.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> The United States should stand with Israel against those who seek its destruction.

Democratic — [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform); `democratic-2008-normalized-0ef47ff2a906-003`.

> The Israeli state has a right to defend its people, but after more than 60 years of self-defense and 40 years of an unjust occupation of the West Bank and Gaza, it should be self-evident that peace and security for Israel cannot be achieved by injustice towards another people.

DSA — [NPC statement on Israeli-Palestinian conflict](https://dlarchive.dsausa.org/wp-content/uploads/2018/12/DL_2009_V037_01.pdf); `dsa-2009-middle-east-lead-normalized-8976b05dabb1-001`.

#### 2012-2015: observed themes

4,382 claims from 30 documents; 12 independently discovered topics. Fit status: complete. Cosine silhouette: 0.056.

Method: `weighted_kmeans`; unweighted assignment coverage: 100.0%. Low separation and mixed narrative clusters limit policy interpretation.

**Expanded reading:** topic shares below are within this period, not measurements of a permanent political position.

- Democratic: Obama administration records, proposals and partisan critiques (17.9%); Public services, workforce support and benefit commitments (17.1%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- Republican: Civil liberties, rights proposals and constitutional protections (13.3%); Committee acknowledgments, named actors and mixed social statements (12.2%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- DSA: Voting, speech and gun-rights disputes (16.7%); International Democratic Promotion and Labor Solidarity (16.5%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.

![Period-specific topics, expanded](../figures/national_claims/full/topics/evolution/expanded/period_2012-2015.png)

**Strict reading:** topic shares below are within this period, not measurements of a permanent political position.

- Democratic: Obama administration records, proposals and partisan critiques (17.9%); Public services, workforce support and benefit commitments (17.1%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- Republican: Civil liberties, rights proposals and constitutional protections (13.3%); Committee acknowledgments, named actors and mixed social statements (12.2%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- DSA: no observed documents in this view.

![Period-specific topics, strict](../figures/national_claims/full/topics/evolution/strict/period_2012-2015.png)

| Period topic | Closest preceding theme | Cosine | Interpretation |
|---|---|---:|---|
| Party narratives, federalism and economic priorities | Government Economic Role and Public Spending (2008-2011) | 0.937 | uncertain_match_not_proof_of_new_topic |
| U.S. Military Operations and International Security | Government Economic Role and Public Spending (2008-2011) | 0.899 | uncertain_match_not_proof_of_new_topic |
| Obama administration records, proposals and partisan critiques | Government Economic Role and Public Spending (2008-2011) | 0.893 | uncertain_match_not_proof_of_new_topic |
| American economic strength and international-role narratives | Government Economic Role and Public Spending (2008-2011) | 0.929 | uncertain_match_not_proof_of_new_topic |
| Public services, workforce support and benefit commitments | Government Economic Role and Public Spending (2008-2011) | 0.977 | candidate_thematic_continuity |
| Healthcare reform, coverage, choice and projected savings | Government Economic Role and Public Spending (2008-2011) | 0.900 | uncertain_match_not_proof_of_new_topic |
| International Democratic Promotion and Labor Solidarity | Government Economic Role and Public Spending (2008-2011) | 0.943 | uncertain_match_not_proof_of_new_topic |
| Economic Security and Employment Opportunities | Government Economic Role and Public Spending (2008-2011) | 0.934 | uncertain_match_not_proof_of_new_topic |
| Civil liberties, rights proposals and constitutional protections | Government Economic Role and Public Spending (2008-2011) | 0.947 | uncertain_match_not_proof_of_new_topic |
| Voting, speech and gun-rights disputes | Government Economic Role and Public Spending (2008-2011) | 0.894 | uncertain_match_not_proof_of_new_topic |
| Economic Conditions and Crisis in the US | Government Economic Role and Public Spending (2008-2011) | 0.873 | uncertain_match_not_proof_of_new_topic |
| Committee acknowledgments, named actors and mixed social statements | Government Economic Role and Public Spending (2008-2011) | 0.900 | uncertain_match_not_proof_of_new_topic |

Period-specific label summaries and inspectable source examples:

**Party narratives, federalism and economic priorities** (`period-2012-topic-001`): Republican self-descriptions address federal balance and opportunity; Democratic examples support equal opportunity and criticize Republican tax priorities. DSA examples discuss right-wing control of state and local government and ending Bush-era tax cuts for the top 2%.

Caveat: Party self-description and criticism across unrelated policies, not a coherent federalism-only topic.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Democrats encourage initiatives to remove barriers to equal opportunity in employment, education, and business opportunities.

Democratic — [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); `democratic-2012-normalized-c23a3db91fb4-008`.

> The Right controls many state and local governments.

DSA — [2013 convention political and organizational priorities](https://web.archive.org/web/20140108003017id_/http://www.dsausa.org/convention_2013_report_priorities); `dsa-2013-priorities-normalized-d4dec7ab5bbe-016`.

**U.S. Military Operations and International Security** (`period-2012-topic-002`): Claims address U.S. military involvement in conflicts like those in Iraq and Afghanistan, and the strain on U.S. forces. Positions vary from ending al-Qaeda safe havens and deterring adversaries to opposing intervention in Syria and retaining all options for security threats.

Caveat: Mixed stances on specific interventions and the scope of military action.

> Eleven years of continuous military operations and repeated deployments to Iraq and Afghanistan have stretched U.S. forces and strained their families.

Democratic — [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); `democratic-2012-normalized-0012a775903a-005`.

> Support for multilateral international efforts that deny military and economic resources to authoritarian forces of all ideological stripes.

DSA — [DSA Statement on the Islamic State and the Crisis in Iraq and Syria](https://www.dsausa.org/wp-json/wp/v2/statement/377); `dsa-statement-377-normalized-9e74d19c9f2d-007`.

**Obama administration records, proposals and partisan critiques** (`period-2012-topic-003`): Democratic examples credit Obama with mortgage assistance and a work-study pledge. DSA examples support expanded student-debt repayment and describe diplomatic ties with Cuba. Republican examples assert defense-budget reductions and criticize Obamacare as expanded government control.

Caveat: An actor-centered cluster across unrelated policies; document assertions are not independently verified accomplishments or outcomes.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> President Obama helped five million families restructure their loans to help them stay in their homes.

Democratic — [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); `democratic-2012-normalized-70fd3ee45647-002`.

> Support for President Barack Obama to issue an executive order to expand his administration’s income-based 10-year payment plan for retiring student debt.

DSA — [2013 convention political and organizational priorities](https://web.archive.org/web/20140108003017id_/http://www.dsausa.org/convention_2013_report_priorities); `dsa-2013-priorities-normalized-f54ca343c778-001`.

**American economic strength and international-role narratives** (`period-2012-topic-004`): Democratic and Republican examples link economic development and global opportunities to American strength and competitiveness; a Republican example also emphasizes military strength. DSA examples refer to triumphs in the United States and an international obligation to reward coexistence and moderation.

Caveat: Broad national and international narratives, not evidence that all three groups share an economic-strength agenda.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Support for strong economic development for those who live under the U.S. flag.

Democratic — [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); `democratic-2012-normalized-b5a0b9382373-005`.

> Work will continue to bring similar triumphs to the United States and beyond.

DSA — [The Greek People Reject Austerity: Now the Rest of the World Must Join Them](https://www.dsausa.org/wp-json/wp/v2/statement/402); `dsa-statement-402-normalized-f9e9b5e33cc3-006`.

**Public services, workforce support and benefit commitments** (`period-2012-topic-005`): Democratic examples support veterans' education and healthcare access and strengthening Medicaid. DSA examples support education and healthcare investment and programs for vulnerable people. Republican examples support workforce retraining and survivors' benefits.

Caveat: Mixed program commitments, not exclusively healthcare or education; shared support language does not imply equivalent programs.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Commitment to improve access to education and health care, especially for rural veterans.

Democratic — [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); `democratic-2012-normalized-30b94785803a-007`.

> Commitment to work with coalitions to preserve programs that benefit the working poor and most vulnerable.

DSA — [Reject the Fiscal Cliff](https://www.dsausa.org/wp-json/wp/v2/statement/355); `dsa-2012-fiscal-normalized-2b868cee0576-005`.

**Healthcare reform, coverage, choice and projected savings** (`period-2012-topic-006`): Democratic examples credit health reform with family security and projected Medicare savings. DSA examples describe uninsured people and a projected single-payer saving. Republican examples support healthcare choice and affordable care for older people.

Caveat: Savings and coverage figures are attributed document claims, not independently verified estimates; the packet does not establish a common reform approach.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Historic health care reform was enacted to provide economic security for families.

Democratic — [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); `democratic-2012-normalized-da1d6566f5d3-010`.

> Prior to the passage of health reform in 2010, 47 million United States citizens had no health insurance.

DSA — [A Social and Economic Bill of Rights](https://www.dsausa.org/wp-json/wp/v2/strategy/617); `dsa-2010-social-economic-rights-normalized-08c6cbb50586-003`.

**International Democratic Promotion and Labor Solidarity** (`period-2012-topic-007`): These claims address support for democratic movements and civil society internationally, alongside commitments to labor movements. Both Democrats and Republicans express support for democracy, though with differing regional focuses and framing, while the DSA emphasizes solidarity with global justice movements and international socialist efforts.

Caveat: Mixed subtopics: includes both general democratic promotion and specific regional foreign policy positions (Syria).

> Commitment to continue to fight for a strong labor movement.

Democratic — [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); `democratic-2012-normalized-c23a3db91fb4-003`.

> The Democratic Socialists of America stands in solidarity with those fighting for social and racial justice in the United States and around the globe.

DSA — [In Solidarity With Those Arrested In Ferguson](https://www.dsausa.org/wp-json/wp/v2/statement/361); `dsa-statement-361-normalized-d6239bf500fe-007`.

**Economic Security and Employment Opportunities** (`period-2012-topic-008`): Claims address policies related to economic security, including income security and access to employment. These policies range from tax cuts and lower healthcare costs to supporting workers' rights and reforming the tax code to stimulate job creation. Differing approaches are presented, with some focusing on private sector growth and others on income assurance.

Caveat: Mixed subtopics of income security, job creation, and tax policy are present.

> American families who are working multiple jobs and struggling to pay the bills were helped through tax cuts, lower health care costs, and affordable student loans.

Democratic — [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); `democratic-2012-normalized-da1d6566f5d3-013`.

> In a society that assures income security, loss of a job will open opportunities to new employment without the pressure to accept the first job offer that emerges.

DSA — [A Social and Economic Bill of Rights](https://www.dsausa.org/wp-json/wp/v2/strategy/617); `dsa-2010-social-economic-rights-normalized-87e9c919def2-001`.

**Civil liberties, rights proposals and constitutional protections** (`period-2012-topic-009`): Democratic examples support universal rights and antidiscrimination enforcement. DSA examples propose a constitutional voting and representation right and defend voting, immigrant, reproductive and LGBTQ rights. Republican examples assert self-defense rights and a right to apply religious values to public policy.

Caveat: A mixture of rights assertions, proposed guarantees and policy commitments, not proof that every described protection is already guaranteed to citizens.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Commitment to continue to support the exercise of universal rights.

Democratic — [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); `democratic-2012-normalized-c3ba20b3ad55-005`.

> Support for enacting a constitutional right to vote and to be fairly represented.

DSA — [Defend and Expand Democracy: Statement on the Voting Rights Act Supreme Court Decision](https://www.dsausa.org/wp-json/wp/v2/statement/384); `dsa-statement-384-normalized-4db8b1a5732c-006`.

**Voting, speech and gun-rights disputes** (`period-2012-topic-010`): Democratic examples oppose disenfranchisement and voting restrictions. DSA examples describe a Texas redistricting decision and accuse Republicans of undemocratic power retention. Republican examples oppose the Fairness Doctrine and federal licensing or registration of law-abiding gun owners.

Caveat: Mixed rights disputes and partisan accusations, not solely an electoral-policy cluster; asserted events and motives are not independently verified.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Refusal to allow the use of political pretexts to disenfranchise American citizens.

Democratic — [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); `democratic-2012-normalized-fef136903755-006`.

> The Justice Department struck down a state legislative redistricting plan in Texas that severely limited representation for Latino voters.

DSA — [Defend and Expand Democracy: Statement on the Voting Rights Act Supreme Court Decision](https://www.dsausa.org/wp-json/wp/v2/statement/384); `dsa-statement-384-normalized-8bfe021af1fe-004`.

**Economic Conditions and Crisis in the US** (`period-2012-topic-011`): Claims describe a prolonged economic crisis, referencing the Great Depression as a comparative benchmark. Multiple claims point to financial hardship for families and economic challenges for US territories. The Democratic and Republican parties both acknowledge a crisis, while the DSA links tax code changes to job losses.

Caveat: Mixed subtopics of national economic crisis, territorial economies, and tax policy.

> The country was in the midst of the greatest economic crisis since the Great Depression four years ago.

Democratic — [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); `democratic-2012-normalized-f97dee824c45-002`.

> Sequestration cuts will harm millions of low-income Americans.

DSA — [Cancel the Sequester; Create Jobs!](https://www.dsausa.org/wp-json/wp/v2/statement/363); `dsa-statement-363-normalized-71b1af7648bf-002`.

**Committee acknowledgments, named actors and mixed social statements** (`period-2012-topic-012`): Republican examples identify committee members. Democratic examples quote Ledbetter on legislation and support for women and families. DSA examples condemn the Charleston church murders and support a proposed White House poverty conference.

Caveat: Includes non-policy personnel metadata and unrelated social statements; the cluster must not be interpreted as a coherent policy emphasis.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Lilly Ledbetter says Lilly Ledbetter is proud of the legislation that bears Lilly Ledbetter's name.

Democratic — [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform); `democratic-2012-normalized-394545949e28-012`.

> Condemnation of the murder of nine people at Charleston's AME Church.

DSA — [To Properly Mourn the Murder Victims at the Emanuel AME Church We Must Rededicate Ourselves to the Fight Against Racism](https://www.dsausa.org/wp-json/wp/v2/statement/357); `dsa-statement-357-normalized-de930c3754d2-repair-56e946f43c24-005`.

#### 2016-2019: observed themes

5,183 claims from 54 documents; 12 independently discovered topics. Fit status: complete. Cosine silhouette: 0.053.

Method: `weighted_kmeans`; unweighted assignment coverage: 100.0%. Low separation and mixed narrative clusters limit policy interpretation.

**Expanded reading:** topic shares below are within this period, not measurements of a permanent political position.

- Democratic: Mixed domestic organizing and international commitments (30.6%); Democratic Party Positions on Political Campaigns and Issues (14.6%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- Republican: Employment and Economic Opportunity for Workers (17.5%); Civil rights, legal enforcement and state labor authority (16.4%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- DSA: Socialist organizing and mixed economic or humanitarian commitments (26.3%); Foreign Government Actions and Human Rights Abuses (17.8%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.

![Period-specific topics, expanded](../figures/national_claims/full/topics/evolution/expanded/period_2016-2019.png)

**Strict reading:** topic shares below are within this period, not measurements of a permanent political position.

- Democratic: Mixed domestic organizing and international commitments (30.6%); Democratic Party Positions on Political Campaigns and Issues (14.6%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- Republican: Employment and Economic Opportunity for Workers (17.5%); Civil rights, legal enforcement and state labor authority (16.4%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- DSA: no observed documents in this view.

![Period-specific topics, strict](../figures/national_claims/full/topics/evolution/strict/period_2016-2019.png)

| Period topic | Closest preceding theme | Cosine | Interpretation |
|---|---|---:|---|
| Democratic Party Positions on Political Campaigns and Issues | Party narratives, federalism and economic priorities (2012-2015) | 0.946 | uncertain_match_not_proof_of_new_topic |
| Employment and Economic Opportunity for Workers | Economic Security and Employment Opportunities (2012-2015) | 0.981 | candidate_thematic_continuity |
| Civil rights, legal enforcement and state labor authority | Civil liberties, rights proposals and constitutional protections (2012-2015) | 0.990 | candidate_thematic_continuity |
| Healthcare access, coverage, costs and legislative disputes | Healthcare reform, coverage, choice and projected savings (2012-2015) | 0.988 | candidate_thematic_continuity |
| Mixed domestic organizing and international commitments | Public services, workforce support and benefit commitments (2012-2015) | 0.976 | candidate_thematic_continuity |
| Reproductive funding, immigration, discipline and gun-rights disputes | Voting, speech and gun-rights disputes (2012-2015) | 0.990 | candidate_thematic_continuity |
| US Foreign Policy: Humanitarian Aid and Global Leadership | American economic strength and international-role narratives (2012-2015) | 0.990 | candidate_thematic_continuity |
| Trump-centered and competing presidential narratives | Voting, speech and gun-rights disputes (2012-2015) | 0.836 | uncertain_match_not_proof_of_new_topic |
| Economic hardship, housing and competing policy explanations | Economic Conditions and Crisis in the US (2012-2015) | 0.989 | candidate_thematic_continuity |
| Foreign Government Actions and Human Rights Abuses | U.S. Military Operations and International Security (2012-2015) | 0.963 | candidate_thematic_continuity |
| Republican identity, policy critiques and partisan opposition | Party narratives, federalism and economic priorities (2012-2015) | 0.964 | candidate_thematic_continuity |
| Socialist organizing and mixed economic or humanitarian commitments | International Democratic Promotion and Labor Solidarity (2012-2015) | 0.978 | candidate_thematic_continuity |

Period-specific label summaries and inspectable source examples:

**Democratic Party Positions on Political Campaigns and Issues** (`period-2016-topic-001`): Claims focus on the Democratic Party's stated positions on job creation and foreign policy, as well as accusations regarding healthcare and abortion. The Democratic Socialists of America (DSA) state a strategy of supporting Democratic candidates, particularly progressive and socialist ones.

Caveat: Mixed subtopics: campaign strategy, healthcare, foreign policy, and social issues are all represented.

> Democrats are focused on creating good jobs in communities across America.

Democratic — [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); `democratic-2016-normalized-9b1d0772b2c6-002`.

> Currently, the Democratic Party is inching towards alignment around the impeachment of President Donald Trump.

DSA — [DSA National Political Committee (NPC) Statement on Impeachment](https://www.dsausa.org/wp-json/wp/v2/statement/4192); `dsa-statement-4192-normalized-0081d76339ad-002`.

**Employment and Economic Opportunity for Workers** (`period-2016-topic-002`): These claims concern policies related to creating and accessing employment opportunities. Both Democratic and Republican platforms express support for job creation, though with differing emphases on supporting workers and removing regulations. The DSA focuses on a 'just transition' for workers and frontline communities.

Caveat: Mixed positions can share a subject.

> Support for creating good-paying jobs that can support a middle-class life.

Democratic — [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); `democratic-2016-normalized-4bac4fec2ba2-011`.

> Bernie Sanders’ plan includes extensive provisions for a just transition that builds power for workers.

DSA — [National DSA Ecosocialists support Bernie Sanders’ Green New Deal](https://www.dsausa.org/wp-json/wp/v2/statement/4013); `dsa-statement-4013-normalized-0e688c5b7733-008`.

**Civil rights, legal enforcement and state labor authority** (`period-2016-topic-003`): Democratic examples support restoring Voting Rights Act protections and strengthening fair housing law. DSA examples support equal rights and addressing wrongful killing, injury and detention. Republican examples support immigration-law enforcement and states' authority to enact right-to-work laws.

Caveat: Different legal subjects, not evidence that civil-rights protections and state authority are mutually exclusive positions.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Support for restoring the full protections of the Voting Rights Act.

Democratic — [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); `democratic-2016-normalized-4292f2af0201-001`.

> Support for addressing those who have been wrongly killed, hurt, and detained.

DSA — [Statement of Solidarity with the Chilean People](https://www.dsausa.org/wp-json/wp/v2/statement/4267); `dsa-statement-4267-normalized-a87200f2da12-007`.

**Healthcare access, coverage, costs and legislative disputes** (`period-2016-topic-004`): Democratic examples propose comprehensive primary care and ending a retiree-health prefunding mandate. DSA examples describe proposed coverage and warn that the AHCA would cut Medicaid. Republican examples describe Medicare and Medicaid beneficiaries and support provider options and cost containment.

Caveat: Statements describe different proposals and disputed effects; numbers and predicted legislative outcomes are not independently verified.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Commitment to fight for a comprehensive system of primary health care, including dental, mental health care, and low-cost prescription drugs.

Democratic — [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); `democratic-2016-normalized-ecd47e7958b3-013`.

> The American Health Care Act (AHCA) will gut Medicaid, a single-payer system that covers 74 million low-income, disabled and elderly Americans.

DSA — [Trump Care Must not Pass the Senate: Building a Movement for “Medicare for All”](https://www.dsausa.org/wp-json/wp/v2/statement/392); `dsa-statement-392-normalized-913c404ed427-004`.

**Mixed domestic organizing and international commitments** (`period-2016-topic-005`): Democratic examples support homeland security and the Women, Peace, and Security action plan. Republican examples support developing peoples' autonomy and America-first trade agreements. DSA examples prioritize socialist education, movement organizing and local action against racist policing, arrests and deportations.

Caveat: Broad commitment language spanning unrelated domestic and international subjects, not a common national-security agenda.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Commitment to strengthen homeland security.

Democratic — [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); `democratic-2016-normalized-cba8bb3f1bb4-006`.

> Commitment to prioritize social movement work and public socialist education.

DSA — [2017 convention national priorities resolution](https://www.dsausa.org/wp-json/wp/v2/blog/3035); `dsa-2017-priorities-normalized-1bd328679060-004`.

**Reproductive funding, immigration, discipline and gun-rights disputes** (`period-2016-topic-006`): DSA examples describe the Hyde Amendment and Title X abortion-funding restrictions. Democratic examples reject religious immigration tests and discriminatory school discipline. Republican examples oppose gun-owner registration and deprivation of gun rights without due process.

Caveat: Mixed rights and regulation subjects; only the DSA examples in this packet concern reproductive healthcare funding.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Rejection of attempts to impose a religious test to bar immigrants or refugees from entering the United States.

Democratic — [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); `democratic-2016-normalized-bba3819c4be8-001`.

> The 1976 Hyde Amendment bans Medicaid funds being used for abortions.

DSA — [Uniting to Build a Socialist Feminist Movement](https://www.dsausa.org/wp-json/wp/v2/statement/388); `dsa-statement-388-normalized-472e2eb2aeff-012`.

**US Foreign Policy: Humanitarian Aid and Global Leadership** (`period-2016-topic-007`): These claims address the United States' role in international affairs, specifically concerning humanitarian aid and global leadership. Positions vary from supporting US leadership as a 'beacon of hope' to advocating for independence of overseas territories and providing aid to Syrian refugees. Both military and economic cooperation are mentioned as components of US foreign policy.

Caveat: Mixed stances on the nature and extent of US global engagement are present.

> Support for maintaining the United States' role as a beacon of hope for people seeking safety, freedom, and security.

Democratic — [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); `democratic-2016-normalized-fd7836178d2b-003`.

> Commitment to the independence of all other overseas territories and dependencies controlled, occupied, or otherwise exploited by the USA.

DSA — [Statement on Decolonization](https://www.dsausa.org/wp-json/wp/v2/statement/4011); `dsa-statement-4011-normalized-69fb3a9ceddd-003`.

**Trump-centered and competing presidential narratives** (`period-2016-topic-008`): Democratic examples criticize Trump's approach to NATO and allies. DSA examples accuse Trump of divisive rhetoric and hostility toward marginalized groups. Republican examples promise a different military approach to climate change and criticize an unnamed president over immigration law.

Caveat: Actor-centered rhetoric includes unnamed presidential references; not every example concerns Trump and accusations are not independently verified.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Donald Trump would overturn more than 50 years of American foreign policy by abandoning NATO partners.

Democratic — [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); `democratic-2016-normalized-b4f43c23e8c1-006`.

> Donald Trump’s statement is a narrative used to divide people.

DSA — [DSA Statement on Georgia Abortion Law](https://www.dsausa.org/wp-json/wp/v2/statement/2185); `dsa-statement-2185-normalized-caaebbe8a88d-003`.

**Economic hardship, housing and competing policy explanations** (`period-2016-topic-009`): Democratic examples address housing costs and racial wealth and income gaps. DSA examples criticize capitalist austerity and social-spending cuts. Republican examples attribute increased poverty to Obama and describe territorial economic challenges.

Caveat: Document diagnoses and partisan causal claims across several economic subjects, not independently verified explanations.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Commitment to combat the affordable housing crisis and skyrocketing rents in many parts of the country, which is leading too many families and workers to be pushed out of communities where they work.

Democratic — [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); `democratic-2016-normalized-d67c83c72be1-004`.

> Neoliberal capitalist austerity policies enacted by governments the world over, including Wall Street Democrats in the U.S., force poor and working people to compete with each other to survive.

DSA — [DSA stands in solidarity with Christchurch](https://www.dsausa.org/wp-json/wp/v2/statement/1896); `dsa-statement-1896-normalized-ead9022fbed2-001`.

**Foreign Government Actions and Human Rights Abuses** (`period-2016-topic-010`): Claims address alleged human rights violations by foreign governments, specifically citing actions in Iran, Syria, and the Middle East/Africa. These claims characterize governments as perpetrators of violence, terrorism sponsorship, and genocide. Differing claims focus on the role of U.S. intervention in Central American political turmoil.

Caveat: Mixed subtopics: claims address both accusations against foreign governments and critiques of U.S. foreign policy.

> Characterization of Iran as violating the human rights of its population.

Democratic — [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); `democratic-2016-normalized-8c63c7382aed-007`.

> U.S. intervention and imperialism have contributed to political turmoil in Honduras and Nicaragua.

DSA — [Statement on Central American Caravan/DSA se solidariza con la actual caravana centroamericana en un éxodo a los Estados Unidos](https://www.dsausa.org/wp-json/wp/v2/statement/1083); `dsa-statement-1083-normalized-89cb4e70281a-002`.

**Republican identity, policy critiques and partisan opposition** (`period-2016-topic-011`): Democratic examples oppose Republican regulatory cuts and alleged voter disenfranchisement. DSA examples criticize an insurance-premium provision and oppose ACA repeal. Republican examples assert American exceptionalism and religious diversity within the party.

Caveat: Actor-centered self-description and criticism across unrelated policies; not a common regulation or voting-rights stance.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Commitment to stop Republican efforts to hamstring regulators through budget cuts.

Democratic — [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); `democratic-2016-normalized-5f15e986f0a9-003`.

> The Republican bill allows insurers to charge older individuals five times the insurance premiums of younger individuals.

DSA — [Defeat ‘Repeal and Replace’: Move towards ‘Medicare for All’](https://www.dsausa.org/wp-json/wp/v2/statement/405); `dsa-statement-405-normalized-ddfc652250b5-006`.

**Socialist organizing and mixed economic or humanitarian commitments** (`period-2016-topic-012`): DSA examples describe solidarity against capitalism and nonviolent action for social justice. A Democratic example proposes humanitarian aid for Syrian and Iraqi civilians. Republican examples oppose crony capitalism and tax increases and favor markets for wealth and Social Security.

Caveat: Mixed organizational and policy statements; humanitarian assistance describes one supplied example, not the whole cluster.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Given the immense scale of human suffering in Syria, Democrats will lead the international community in providing greater humanitarian assistance to civilian victims of war in Syria and Iraq, especially displaced refugees.

Democratic — [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform); `democratic-2016-normalized-9c61e4f3f556-005`.

> DSA fights capitalism with solidarity.

DSA — [DSA Statement on Georgia Abortion Law](https://www.dsausa.org/wp-json/wp/v2/statement/2185); `dsa-statement-2185-normalized-4656dc715a5f-017`.

#### 2020-2023: observed themes

3,669 claims from 23 documents; 12 independently discovered topics. Fit status: complete. Cosine silhouette: 0.088.

Method: `weighted_kmeans`; unweighted assignment coverage: 100.0%. Low separation and mixed narrative clusters limit policy interpretation.

**Expanded reading:** topic shares below are within this period, not measurements of a permanent political position.

- Democratic: Community and Regional Economic Development Initiatives (17.5%); U.S. Foreign Policy and International Cooperation (17.0%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- Republican: no observed documents in this view.
- DSA: Structural racism, policing, housing and economic power (17.2%); Law Enforcement Reform and Abolition Policies (16.6%). Based on 2 bundle(s); unclustered share 0.0%. Source composition limits interpretation.

![Period-specific topics, expanded](../figures/national_claims/full/topics/evolution/expanded/period_2020-2023.png)

**Strict reading:** topic shares below are within this period, not measurements of a permanent political position.

- Democratic: Community and Regional Economic Development Initiatives (17.5%); U.S. Foreign Policy and International Cooperation (17.0%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- Republican: no observed documents in this view.
- DSA: Law Enforcement Reform and Abolition Policies (24.7%); Labor Rights and Worker Protections (14.3%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.

![Period-specific topics, strict](../figures/national_claims/full/topics/evolution/strict/period_2020-2023.png)

| Period topic | Closest preceding theme | Cosine | Interpretation |
|---|---|---:|---|
| Community and Regional Economic Development Initiatives | Employment and Economic Opportunity for Workers (2016-2019) | 0.963 | candidate_thematic_continuity |
| U.S. Foreign Policy and International Cooperation | Mixed domestic organizing and international commitments (2016-2019) | 0.978 | candidate_thematic_continuity |
| Immigration, Rights, and Labor Movement Growth | US Foreign Policy: Humanitarian Aid and Global Leadership (2016-2019) | 0.959 | candidate_thematic_continuity |
| Law Enforcement Reform and Abolition Policies | Civil rights, legal enforcement and state labor authority (2016-2019) | 0.982 | candidate_thematic_continuity |
| Labor Rights and Worker Protections | Employment and Economic Opportunity for Workers (2016-2019) | 0.937 | uncertain_match_not_proof_of_new_topic |
| Democratic party narratives, campaign preferences and criticism | Democratic Party Positions on Political Campaigns and Issues (2016-2019) | 0.994 | candidate_thematic_continuity |
| Universal Healthcare Coverage and Access in the US | Healthcare access, coverage, costs and legislative disputes (2016-2019) | 0.974 | candidate_thematic_continuity |
| COVID-19 Pandemic: Health and Economic Impacts | Economic hardship, housing and competing policy explanations (2016-2019) | 0.941 | uncertain_match_not_proof_of_new_topic |
| Structural racism, policing, housing and economic power | Economic hardship, housing and competing policy explanations (2016-2019) | 0.945 | candidate_thematic_continuity |
| Trump-centered diplomatic criticism and organizing narratives | Trump-centered and competing presidential narratives (2016-2019) | 0.974 | candidate_thematic_continuity |
| Palestinian Self-Determination and U.S. Policy Responses | Foreign Government Actions and Human Rights Abuses (2016-2019) | 0.842 | uncertain_match_not_proof_of_new_topic |
| DSA identity, social justice and Social Security opposition | Socialist organizing and mixed economic or humanitarian commitments (2016-2019) | 0.977 | candidate_thematic_continuity |

Period-specific label summaries and inspectable source examples:

**Community and Regional Economic Development Initiatives** (`period-2020-topic-001`): These claims focus on directing resources to communities experiencing economic hardship, including low-income, urban, and rural areas. Support is expressed for strengthening infrastructure and institutions within these communities, alongside programs for desegregation and integration. Claims also address immediate needs like emergency shelter and advocate for economic stimulus.

Caveat: Mixed positions can share a subject.

> Commitment to drive increased resources to communities with the highest need, including those with the highest concentrations of low-income students, impoverished urban areas impacted by gentrification, and rural areas.

Democratic — [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); `democratic-2020-normalized-5e55d1004289-004`.

> Support for securing adequate compensation and living standards, as well as effective infrastructure, healthcare, and institutions in communities and abroad.

DSA — [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); `dsa-2021-adopted-normalized-e66dc1af24d6-005`.

**U.S. Foreign Policy and International Cooperation** (`period-2020-topic-002`): These claims concern the role of the United States in global affairs, specifically through foreign policy and international partnerships. Positions vary between integrating climate change into foreign policy and demilitarization, alongside a rejection of propping up 'imperialism and violence'. Claims also support working through the United Nations to solve global problems.

Caveat: Mixed stances on the means and goals of U.S. engagement are present.

> Commitment to fully integrate climate change into U.S. foreign policy and national security strategies.

Democratic — [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); `democratic-2020-normalized-e26a509f96b5-002`.

> Support for demilitarization, decolonization, and striving for a future of international solidarity and cooperation toward global climate justice.

DSA — [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); `dsa-2021-adopted-normalized-7a4fcef26ad9-008`.

**Immigration, Rights, and Labor Movement Growth** (`period-2020-topic-003`): Several claims address the positive contributions of immigrants to the United States, including building communities and achieving victories for immigrant rights. These claims are connected to a broader discussion of labor movements and the power of the working class, particularly in relation to immigration policy. The documents also note a recent rise in the U.S. socialist movement.

Caveat: mixed-subtopic/stance

> The United States gets an extraordinary return on its investments in the prevention and alleviation of poverty, hunger, disease, and conflict with less than one percent of its annual budget.

Democratic — [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); `democratic-2020-normalized-703017acd51e-016`.

> Through class conflict in the workplace and in society more broadly, the American working class exercised enough power to win many of the rights that exist today.

DSA — [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); `dsa-2021-adopted-normalized-6c07162ee087-011`.

**Law Enforcement Reform and Abolition Policies** (`period-2020-topic-004`): Several claims concern reforming or abolishing aspects of law enforcement, including ending racial and religious profiling ("democratic-2020-normalized-11c6d091feaf-010", "democratic-2020-normalized-64ec6becb761-005"). Other claims advocate for more extensive changes, such as ending deportations, repealing police bills of rights, and reinvesting in communities ("dsa-2021-adopted-normalized-7a7bd5c278de-003", "dsa-2021-adopted-normalized-f68f363413a6-008").

Caveat: Claims primarily reflect positions of the Democratic party and the DSA.

> Commitment to ban racial and religious profiling in law enforcement.

Democratic — [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); `democratic-2020-normalized-11c6d091feaf-010`.

> Support for ending all deportations and enforcement actions, immigration detention, private prison contracts, and deputization of local police forces.

DSA — [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); `dsa-2021-adopted-normalized-7a7bd5c278de-003`.

**Labor Rights and Worker Protections** (`period-2020-topic-005`): These claims focus on strengthening labor rights, including the right to organize and bargain collectively, and improving job quality and security for workers. Both groups advocate for policies supporting workers, including the right to strike and protections regardless of immigration status, with some advocating for broader healthcare and climate policies tied to union jobs.

Caveat: Mixed positions can share a subject.

> Commitment to fight to raise wages for working people and improve job quality and security.

Democratic — [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); `democratic-2020-normalized-4521936cc397-001`.

> Support for labor rights for all, regardless of immigration status.

DSA — [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); `dsa-2021-adopted-normalized-6b522fa83bc9-008`.

**Democratic party narratives, campaign preferences and criticism** (`period-2020-topic-006`): Democratic examples describe commitments to children and education. DSA examples favor Sanders' immigration platform, criticize mainstream Democrats' donors and criticize Democratic leaders' response to Barrett's confirmation.

Caveat: Actor-centered campaign and party narratives, not a children-and-education-only policy cluster; judgments about candidates and motives remain attributed claims.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Democrats are committed to creating a society where children are safe and can thrive physically, emotionally, educationally, and spiritually.

Democratic — [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); `democratic-2020-normalized-cf9ab893acce-012`.

> Bernie Sanders has the strongest platform for immigrant rights of any of the Democratic candidates.

DSA — [For a moratorium on deportations, with no exceptions/Para una moratoria de las deportaciones, sin excepciones](https://www.dsausa.org/wp-json/wp/v2/statement/4621); `dsa-statement-4621-normalized-932b136c3755-003`.

**Universal Healthcare Coverage and Access in the US** (`period-2020-topic-007`): Multiple claims focus on establishing universal healthcare coverage for all US residents, including those without employment or insurance. The claims specifically mention Medicare for All as a potential system and emphasize access for non-citizens and those needing long-term or mental healthcare. Both the Democratic party and the DSA express support for improving healthcare access and affordability.

Caveat: Mixed positions can share a subject.

> Commitment to build a health care system that provides universal health care coverage.

Democratic — [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); `democratic-2020-normalized-3542c1bfdbb3-010`.

> Support for a national healthcare system like Medicare For All.

DSA — [For those Grieving and Raging Today](https://www.dsausa.org/wp-json/wp/v2/statement/5581); `dsa-statement-5581-normalized-20cd15748fbe-003`.

**COVID-19 Pandemic: Health and Economic Impacts** (`period-2020-topic-008`): Claims focus on the health and economic consequences of the COVID-19 pandemic, particularly for vulnerable populations. These include concerns about access to care for communities of color and the disproportionate impact on workers, poor people, and marginalized groups. The pandemic has also exposed existing racial and economic health disparities.

Caveat: Mixed positions can share a subject.

> The lack of guaranteed paid sick leave and paid family leave is catastrophic for public health in the midst of the COVID-19 pandemic.

Democratic — [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); `democratic-2020-normalized-440c88ef847f-017`.

> With the COVID-19 outbreak and a looming economic recession, hospital workers, poor and unhoused people, the elderly, incarcerated people, the immunocompromised, immigrants, and other marginalized groups will likely bear the most impact.

DSA — [Now is the Time for Solidarity: DSA National Statement on COVID-2019/Es la hora de solidaridad: Comunicación nacional de DSA acerca de COVID-19](https://www.dsausa.org/wp-json/wp/v2/statement/4626); `dsa-statement-4626-normalized-6ac57c252fad-004`.

**Structural racism, policing, housing and economic power** (`period-2020-topic-009`): Democratic examples oppose structural racism and describe barriers to homeownership from red-lining, inequality and predatory lending. DSA examples connect policing, prisons, borders and criminalization to racial and working-class oppression and the protection of economic power.

Caveat: Related but distinct housing and criminal-justice narratives; the packet does not establish red-lining as a cause of policing or criminalization.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Commitment to root out structural and systemic racism in the economy and society.

Democratic — [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); `democratic-2020-normalized-0b9b0d310f69-001`.

> Militarized borders, xenophobic/racist immigration laws, and an abusive prison industrial complex suppress wages and divide the working class.

DSA — [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/); `dsa-2021-adopted-normalized-6b522fa83bc9-003`.

**Trump-centered diplomatic criticism and organizing narratives** (`period-2020-topic-010`): Democratic examples criticize Trump's effects on American credibility and diplomacy. DSA examples criticize withdrawal from the Iran agreement and military escalation, and describe membership growth during the Trump administration.

Caveat: Actor-centered criticism and organizational history, not solely foreign policy or independently verified effects of presidential actions.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> President Trump has tarnished U.S. credibility.

Democratic — [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); `democratic-2020-normalized-f4a47a1af77b-010`.

> Donald Trump unilaterally pulled out of the Iran Nuclear Agreement, in spite of Iran’s compliance with it.

DSA — [Urgent Call For Action Against A U.S. War On Iran](https://www.dsausa.org/wp-json/wp/v2/statement/4386); `dsa-statement-4386-normalized-89aab4241a6d-003`.

**Palestinian Self-Determination and U.S. Policy Responses** (`period-2020-topic-011`): Claims address policies concerning the Palestinian people, including support for a two-state solution and restoration of U.S. assistance. Multiple claims express support for Palestinian self-determination, including the right of return for refugees and an end to military occupation. Differing approaches are present, with some advocating for a negotiated two-state solution while others support the Boycott, Divestment, and Sanctions movement.

Caveat: mixed-subtopic/stance

> Commitment to restore critical assistance to the Palestinian people in the West Bank and Gaza, consistent with U.S. law.

Democratic — [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); `democratic-2020-normalized-3c29dbc1688d-012`.

> Palestinians in the United States demand the right to resist their oppression.

DSA — [DSA endorses vision and policy demand statement of Freedom is the Future](https://www.dsausa.org/wp-json/wp/v2/statement/4489); `dsa-statement-4489-normalized-783bbde2a3e3-repair-f17a6ab3053c-001`.

**DSA identity, social justice and Social Security opposition** (`period-2020-topic-012`): DSA examples describe democratic socialism for working-class people, socialist feminism, racial equality and freedom from oppression. One Democratic example opposes cutting, privatizing or weakening Social Security.

Caveat: Broad organizational identity and a separate Social Security commitment, not several supplied Social Security claims or a coherent single policy.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Opposition to every effort to cut, privatize, or weaken Social Security.

Democratic — [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform); `democratic-2020-normalized-adb3cd71f6fa-010`.

> DSA's movement for democratic socialism stands for all working class people.

DSA — [For a moratorium on deportations, with no exceptions/Para una moratoria de las deportaciones, sin excepciones](https://www.dsausa.org/wp-json/wp/v2/statement/4621); `dsa-statement-4621-normalized-70579fa7af56-002`.

#### 2024-2026: observed themes

3,172 claims from 4 documents; 12 independently discovered topics. Fit status: complete. Cosine silhouette: 0.107.

Method: `weighted_kmeans`; unweighted assignment coverage: 100.0%. Low separation and mixed narrative clusters limit policy interpretation.

**Expanded reading:** topic shares below are within this period, not measurements of a permanent political position.

- Democratic: Low-Income Support Programs and Tax Policy (24.9%); Biden-centered policy praise and criticism (22.7%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- Republican: Voting rights, public safety and state-level votes (21.9%); Economic and National Priorities for the United States (18.1%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- DSA: Socialist organizing and Democratic economic narratives (24.5%); Labor Standards and Economic Support for Workers (20.4%). Based on 2 bundle(s); unclustered share 0.0%. Source composition limits interpretation.

![Period-specific topics, expanded](../figures/national_claims/full/topics/evolution/expanded/period_2024-2026.png)

**Strict reading:** topic shares below are within this period, not measurements of a permanent political position.

- Democratic: Low-Income Support Programs and Tax Policy (24.9%); Biden-centered policy praise and criticism (22.7%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- Republican: Voting rights, public safety and state-level votes (21.9%); Economic and National Priorities for the United States (18.1%). Based on 1 bundle(s); unclustered share 0.0%. Source composition limits interpretation.
- DSA: Socialist organizing and Democratic economic narratives (24.5%); Labor Standards and Economic Support for Workers (20.4%). Based on 2 bundle(s); unclustered share 0.0%. Source composition limits interpretation.

![Period-specific topics, strict](../figures/national_claims/full/topics/evolution/strict/period_2024-2026.png)

| Period topic | Closest preceding theme | Cosine | Interpretation |
|---|---|---:|---|
| Biden-centered policy praise and criticism | U.S. Foreign Policy and International Cooperation (2020-2023) | 0.834 | uncertain_match_not_proof_of_new_topic |
| Trump-centered evaluations and criticism of Democratic alignment | Trump-centered diplomatic criticism and organizing narratives (2020-2023) | 0.973 | candidate_thematic_continuity |
| Economic Regulation and Labor Standards | Structural racism, policing, housing and economic power (2020-2023) | 0.955 | candidate_thematic_continuity |
| Immigration Enforcement, Detention, and Deportation Policies | Law Enforcement Reform and Abolition Policies (2020-2023) | 0.930 | uncertain_match_not_proof_of_new_topic |
| Economic and National Priorities for the United States | U.S. Foreign Policy and International Cooperation (2020-2023) | 0.950 | candidate_thematic_continuity |
| Low-Income Support Programs and Tax Policy | Immigration, Rights, and Labor Movement Growth (2020-2023) | 0.942 | candidate_thematic_continuity |
| Party identity, security and institutional commitments | Democratic party narratives, campaign preferences and criticism (2020-2023) | 0.896 | candidate_thematic_continuity |
| Voting rights, public safety and state-level votes | Law Enforcement Reform and Abolition Policies (2020-2023) | 0.986 | candidate_thematic_continuity |
| Labor Standards and Economic Support for Workers | Community and Regional Economic Development Initiatives (2020-2023) | 0.963 | candidate_thematic_continuity |
| US Policy Regarding Israel and Palestine | U.S. Foreign Policy and International Cooperation (2020-2023) | 0.920 | uncertain_match_not_proof_of_new_topic |
| Healthcare Access and Coverage Policies | Universal Healthcare Coverage and Access in the US (2020-2023) | 0.989 | candidate_thematic_continuity |
| Socialist organizing and Democratic economic narratives | DSA identity, social justice and Social Security opposition (2020-2023) | 0.915 | candidate_thematic_continuity |

Period-specific label summaries and inspectable source examples:

**Biden-centered policy praise and criticism** (`period-2024-topic-001`): Democratic examples credit Biden with anti-discrimination executive orders and reestablishing the White House Council on Native American Affairs. Republican examples blame his administration for open borders and global instability. A DSA example criticizes military funding and oil drilling.

Caveat: Competing actor-centered accounts across unrelated subjects, not verified administration effects or a single policy issue.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> President Biden signed two Executive Orders to combat bias, discrimination and hate-based violence.

Democratic — [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); `democratic-2024-normalized-567f3057384a-010`.

> Under Joe Biden, the United States has prioritized funding a massive military budget and expanding oil drilling.

DSA — [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); `dsa-2024-program-normalized-43f2e9413efb-003`.

**Trump-centered evaluations and criticism of Democratic alignment** (`period-2024-topic-002`): Democratic examples accuse Trump of weakening democratic norms and failing to restore manufacturing jobs. Republican examples credit him with national pride and trade-policy improvements. DSA examples warn about another Trump victory and criticize alleged Democratic alignment with his policies.

Caveat: Political evaluations and predictions across multiple subjects, not verified presidential effects or evidence of a shared stance.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Donald Trump weakened global democratic norms.

Democratic — [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); `democratic-2024-normalized-306753327989-009`.

> The alleged embrace of Trump immigration policies, Gaza support and suppression of student protests is said to undermine trust placed in Biden and Democrats.

DSA — [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); `dsa-2024-program-normalized-43f2e9413efb-repair-d5f43d07d995-005`.

**Economic Regulation and Labor Standards** (`period-2024-topic-003`): Claims address economic regulation, with Democrats opposing right-to-work laws that lower wages and Republicans advocating for deregulation to stimulate jobs and innovation. Both parties frame economic issues as impacting workers, though with differing proposed solutions and diagnoses of the problem. The DSA claims the system is failing the working class.

Caveat: Mixed subtopics of labor standards, economic regulation, and political critique.

> Opposition to state right-to-work laws, which drive down wages and leave workers unsafe.

Democratic — [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); `democratic-2024-normalized-8af3eb44deaa-002`.

> Accelerating declines in living standards are exploited by the Christian nationalist right and figures like Donald Trump.

DSA — [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); `dsa-2024-program-normalized-c0035893561c-010`.

**Immigration Enforcement, Detention, and Deportation Policies** (`period-2024-topic-004`): Claims address policies related to immigration enforcement, specifically detention and deportation. Positions range from increased enforcement and deportation of those who have violated U.S. laws ('republican-2024-normalized-048e2be2d61f-003') to abolishing and ending detention/deportations by U.S. Immigration and Customs Enforcement ('dsa-2026-program-normalized-40060dd6f6dd-repair-d40710b9eecc-006'). There is also a commitment to combat drug trafficking ('democratic-2024-normalized-94ca68ceacfc-002').

Caveat: Includes a claim about drug trafficking, which is related but distinct from the core immigration focus.

> Commitment to combat drug trafficking.

Democratic — [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); `democratic-2024-normalized-94ca68ceacfc-002`.

> Abolish U.S. Immigration and Customs Enforcement.

DSA — [Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); `dsa-2026-program-normalized-40060dd6f6dd-repair-d40710b9eecc-006`.

**Economic and National Priorities for the United States** (`period-2024-topic-005`): Claims focus on prioritizing American workers and jobs, with commitments to investment and economic growth. Positions diverge on foreign policy, ranging from ending foreign wars to restoring 'Peace through Strength'. There is also a critique of business relationships with the government.

Caveat: Mixed subtopics of domestic economic policy, foreign policy, and critiques of corporate influence.

> Commitment to keep investing in American workers, American jobs, and American families.

Democratic — [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); `democratic-2024-normalized-9be95fb035db-004`.

> End all U.S. foreign wars.

DSA — [Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); `dsa-2026-program-normalized-40060dd6f6dd-repair-d40710b9eecc-002`.

**Low-Income Support Programs and Tax Policy** (`period-2024-topic-006`): Claims discuss support for low-income workers through programs like the Earned Income Tax Credit and SNAP benefits.  There is also mention of tax implications related to tariffs, and a claim about wealth concentration among the top one percent. These claims represent differing perspectives on economic support and tax policy.

Caveat: mixed-subtopic/stance

> The American Rescue Plan tripled the maximum Earned Income Tax Credit for millions of low-income workers.

Democratic — [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); `democratic-2024-normalized-31862ca12465-007`.

> The top one percent has gotten richer and richer.

DSA — [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); `dsa-2024-program-normalized-c0035893561c-003`.

**Party identity, security and institutional commitments** (`period-2024-topic-007`): Republican examples propose border security and a stronger military. Democratic examples describe mutual support and AI safety/privacy standards. DSA examples criticize the two-party choice and advocate multiparty democracy.

Caveat: Mixed identity, security, technology and electoral-system language, not a coherent national-security-only cluster.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Democrats believe in an America where people look out for one another and leave no one behind.

Democratic — [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); `democratic-2024-normalized-31862ca12465-001`.

> In most races, Americans will have the choice between far-right Republicans and corporate Democrats.

DSA — [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); `dsa-2024-program-normalized-c668d0328bc5-002`.

**Voting rights, public safety and state-level votes** (`period-2024-topic-008`): DSA examples advocate voting access, ending suppression and restoring voting rights after convictions and during incarceration. Democratic examples oppose hate crimes and white-nationalist terrorism and support safety and justice. Republican examples defend peaceful living and state-level votes on the 'Issue of Life'.

Caveat: Voting access and broader safety/rights commitments; these examples do not establish a common stance on electoral integrity.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> Commitment to combat hate crimes and white nationalist terrorism.

Democratic — [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); `democratic-2024-normalized-1e0b4a5c659c-002`.

> Support for expanding and protecting voting rights and ending voter suppression.

DSA — [Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf); `dsa-2026-program-normalized-d326f1020c4f-005`.

**Labor Standards and Economic Support for Workers** (`period-2024-topic-009`): Several groups express support for policies impacting workers, including raising the federal minimum wage and providing labor rights to immigrants. There is also stated commitment to supporting working parents and expanding tax benefits for working people. These claims suggest a focus on economic support for workers through both wage policies and tax measures.

Caveat: Claims span multiple subtopics within labor and economic policy, and represent varying approaches.

> Support for raising the federal minimum wage to at least $15-an-hour.

Democratic — [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); `democratic-2024-normalized-11fdd9f0c413-003`.

> Support for providing labor rights to all immigrants.

DSA — [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); `dsa-2024-program-normalized-9d88be1f8868-019`.

**US Policy Regarding Israel and Palestine** (`period-2024-topic-010`): Claims address US policy toward Israel, with support for Israel in conflict expressed alongside calls to end military and economic aid. Positions also include recognizing Palestinian rights, including the right of return and resistance to occupation. These claims demonstrate differing approaches to the Israeli-Palestinian conflict.

Caveat: Mixed stances on aid, recognition, and resistance are present.

> The United States strongly supports Israel in the fight against Hamas.

Democratic — [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); `democratic-2024-normalized-ad8875381e40-009`.

> Support for ending military and economic aid to Israel.

DSA — [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); `dsa-2024-program-normalized-9d88be1f8868-002`.

**Healthcare Access and Coverage Policies** (`period-2024-topic-011`): These claims focus on policies related to healthcare access and coverage. Positions vary from expanding the Affordable Care Act and strengthening all health plans to guaranteeing reproductive and gender-affirming care, alongside commitments to Medicare and Social Security.

Caveat: Mixed positions can share a subject.

> Commitment to fight to protect and expand the Affordable Care Act, making quality care more accessible and affordable.

Democratic — [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); `democratic-2024-normalized-c361ec3d94e7-008`.

> Support for guaranteed reproductive health care.

DSA — [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); `dsa-2024-program-normalized-b789b4710c28-repair-1a7d74b0c436-002`.

**Socialist organizing and Democratic economic narratives** (`period-2024-topic-012`): DSA examples seek working-class political power and a socialist or democratic socialist society. Democratic examples defend competition within capitalism and credit Democrats with Social Security's passage.

Caveat: Different economic and organizational visions; the Democratic examples do not endorse socialism or a democratic socialist republic.

**Provenance:** source-bound assistant revision; original Gemma response retained unchanged.

> The President says that capitalism without competition isn't capitalism, it's exploitation.

Democratic — [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform); `democratic-2024-normalized-da9ab87f7a1b-010`.

> With working-class government, strong unions and social movements organizing everywhere, DSA hopes to build a socialist society where people take priority over profit.

DSA — [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf); `dsa-2024-program-normalized-d601340193eb-repair-ede159c9a402-001`.


### Publication figure versions

Publication figures are PNG-only and use the warm #F7F5F0 Substack house style. Matching #F5F5F5 versions for The Margin of Error are included under `figures/themarginoferror/` in the complete archive. Only background colors change between versions; plotted values, labels and dimensions are identical.

### Topic summaries and evidence

#### topic-001: Energy, Infrastructure, and Economic Development

Claims concern investment, energy production, infrastructure, and economic development. Democratic examples emphasize clean energy and public investment; Republican examples include reducing fossil-fuel restrictions and technological approaches to petroleum dependence. A DSA example calls for democratic economic restructuring. Other examples address rural investment and affordable housing.

**Caveat:** A broad investment-and-development cluster, not exclusively an energy topic. Shared subject matter does not imply a shared policy stance.

**Label provenance:** source-bound assistant revision of the preserved Gemma response; see the label-review record.

**Distinctive phrases:** energy, clean, infrastructure, american, economy, natural, sustainable, promote, trade, global

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 6.7% | 792 | 7 | 7 |
| expanded | Republican | 4.8% | 265 | 6 | 6 |
| expanded | DSA | 2.1% | 80 | 21 | 9 |
| strict | Democratic | 6.7% | 792 | 7 | 7 |
| strict | Republican | 4.8% | 265 | 6 | 6 |
| strict | DSA | 4.0% | 41 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Commitment to eliminate tens of billions of dollars in subsidies for oil and gas companies. (`democratic-2024-normalized-92fa6cad93aa-003`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 42913:43499 |
| DSA | Commitment to fight to restructure the U.S. economy in a democratic direction. (`dsa-2009-priorities-normalized-69ef366c0cec-004`) | [2009 convention national priorities resolution](https://dlarchive.dsausa.org/wp-content/uploads/2018/12/DL_2010_V037_03.pdf) scoped characters 1653:3096 |
| Republican | Commitment to end market-distorting restrictions on oil, natural gas, and coal. (`republican-2024-normalized-007a594371a0-012`) | [2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform) scoped characters 15857:16203 |
| Democratic | Commitment to invest in the American heartland and rural communities. (`democratic-2020-normalized-e2e95c8e92fd-001`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 46121:47422 |
| Democratic | Commitment to fight to implement the most significant investments in America in generations. (`democratic-2024-normalized-acb049933b3f-012`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 21884:22348 |
| Democratic | Commitment to invest significant new resources in clean energy generation and distribution. (`democratic-2020-normalized-aab0c6ab7f9f-008`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 90178:90902 |
| Democratic | Commitment to protect and grow the global economy. (`democratic-2016-normalized-355accb7d3ef-006`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 169126:169400 |
| Democratic | Commitment to promote economic opportunity and prosperity in the Americas. (`democratic-2016-normalized-755f6fab8c61-006`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 166287:167091 |
| Republican | Commitment to put American workers first. (`republican-2024-normalized-048e2be2d61f-011`) | [2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform) scoped characters 14099:14347 |
| Democratic | Commitment to invest in advanced energy technologies to build the clean energy economy and create millions of new, good “Green Collar” American jobs. (`democratic-2008-normalized-3b4380265be8-006`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 130268:131484 |
| Republican | Commitment to aggressively support technological advances to reduce petroleum dependence. (`republican-2008-normalized-dd4b307d1b57-006`) | [2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform) scoped characters 98266:98650 |
| Democratic | Commitment to increase the U.S. supply of affordable housing. (`democratic-2008-normalized-aece53525f28-repair-6b93c1abe4b1-009`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 32612:34070 |

#### topic-002: Community and Economic Support for Vulnerable Populations

Multiple groups express commitment to supporting communities and vulnerable populations through increased resources and programs. This includes investment in low-income communities, rural areas, and communities of color, as well as support for foster care and adoptive families. Claims also address the need to preserve programs benefiting the working poor and improve infrastructure.

**Distinctive phrases:** housing, programs, veterans, resources, communities, funding, local, public, help, federal

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 8.9% | 1104 | 7 | 7 |
| expanded | Republican | 6.4% | 643 | 6 | 6 |
| expanded | DSA | 5.5% | 260 | 48 | 9 |
| strict | Democratic | 8.9% | 1104 | 7 | 7 |
| strict | Republican | 6.4% | 643 | 6 | 6 |
| strict | DSA | 5.2% | 66 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Commitment to increase funding for programs that support the creation and preservation of affordable housing options for essential workers. (`democratic-2024-normalized-51d7cbe64123-005`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 69540:70730 |
| DSA | Support for securing adequate compensation and living standards, as well as effective infrastructure, healthcare, and institutions in communities and abroad. (`dsa-2021-adopted-normalized-e66dc1af24d6-005`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 25750:26880 |
| Republican | Support for better meeting state needs. (`republican-2008-normalized-fd4bbde75007-008`) | [2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform) scoped characters 126725:127315 |
| Republican | Support for offering training, transportation, and child care services to help people become self-sufficient. (`republican-2004-normalized-8eb776d9223a-009`) | [2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform) scoped characters 251901:252254 |
| Republican | Commitment to establish stronger public-private partnerships for safety net providers and hospitals in rural and underserved communities. (`republican-2000-normalized-76e7e2418f31-008`) | [2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform) scoped characters 92920:93402 |
| Democratic | Commitment to fight to train and support the workforce in community-based settings. (`democratic-2016-normalized-a86063b3af32-002`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 117668:118077 |
| Democratic | Support for directing more federal resources to lifting up communities that have been left out and left behind. (`democratic-2016-normalized-a9bcc4d230c7-011`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 65372:65998 |
| DSA | Commitment to work with coalitions to preserve programs that benefit the working poor and most vulnerable. (`dsa-2012-fiscal-normalized-2b868cee0576-005`) | [Reject the Fiscal Cliff](https://www.dsausa.org/wp-json/wp/v2/statement/355) scoped characters 5512:5999 |
| Democratic | Commitment to drive increased resources to communities with the highest need, including those with the highest concentrations of low-income students, impoverished urban areas impacted by gentrification, and rural areas. (`democratic-2020-normalized-5e55d1004289-004`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 204524:205189 |
| Republican | Support for the efforts of foster and adoptive families. (`republican-2008-normalized-8aa7aa1bad1e-012`) | [2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform) scoped characters 147575:148226 |
| Democratic | Commitment to invest in low-income communities, urban and rural areas, and communities of color by strengthening the Community Reinvestment Act. (`democratic-2020-normalized-562fcd433911-007`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 121179:121503 |
| Democratic | Commitment to support and supplement the struggling foster care system. (`democratic-2008-normalized-9fc71187ff8d-007`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 138517:139956 |

#### topic-003: Labor Rights and Unionization

These claims concern policies related to labor rights, specifically the ability of workers to organize and collectively bargain. Positions vary, with some advocating for expanded rights for all workers, including those currently unprotected, and others supporting 'right-to-work' laws. Multiple groups express support for strengthening unions and protecting workers' rights to strike.

**Distinctive phrases:** workers, labor, union, wage, unions, work, minimum wage, worker, minimum, pay

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 3.4% | 399 | 7 | 7 |
| expanded | Republican | 1.6% | 159 | 6 | 6 |
| expanded | DSA | 6.5% | 311 | 49 | 9 |
| strict | Democratic | 3.4% | 399 | 7 | 7 |
| strict | Republican | 1.6% | 159 | 6 | 6 |
| strict | DSA | 8.1% | 71 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Commitment to fight for labor laws that facilitate the collective bargaining process. (`democratic-2012-normalized-18cc338046ac-010`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 47039:48229 |
| DSA | Support for labor rights for all, regardless of immigration status. (`dsa-2021-adopted-normalized-6b522fa83bc9-008`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 64302:64494 |
| Republican | Support the enactment of a National Right-to-Work law to promote worker freedom and greater economic liberty. (`republican-2012-normalized-9b00c73c5686-008`) | [2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform) scoped characters 35273:36184 |
| Democratic | Commitment to fight to raise wages for working people and improve job quality and security. (`democratic-2020-normalized-4521936cc397-001`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 31987:33381 |
| Democratic | Commitment to continue to fight for a strong labor movement. (`democratic-2012-normalized-c23a3db91fb4-003`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 100171:101045 |
| Democratic | Commitment to strengthen labor rights for more than 20 million public-sector employees in the United States by passing the Public Service Freedom to Negotiate Act. (`democratic-2020-normalized-c00aaa88c694-007`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 35689:36005 |
| Democratic | Commitment to allow unions to organize and lift up workers. (`democratic-2008-normalized-aece53525f28-008`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 32612:34070 |
| Democratic | Commitment to make it easier for public and private workers to exercise their right to organize and join unions. (`democratic-2016-normalized-7ba2e6e4e2f2-002`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 9736:10261 |
| DSA | Support for protecting all workers’ rights to strike and form a union. (`dsa-2024-program-normalized-f23d4047d972-002`) | [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf) scoped characters 7352:8203 |
| Democratic | Support for codifying a right to organize for domestic workers, farm workers, and other unprotected laborers. (`democratic-2024-normalized-8af3eb44deaa-005`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 18243:19386 |
| DSA | Support for the right to strike for all workers. (`dsa-2021-adopted-normalized-8861a9fa1bd2-009`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 24555:24590 |
| Democratic | Support for increased funding for efforts to protect workers' rights. (`democratic-2004-normalized-7fe56cf462ee-010`) | [2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform) scoped characters 60446:61419 |

#### topic-004: Economic Growth and Development Narratives

Multiple claims address economic growth as a central goal, with some linking it to infrastructure investment and job creation. Both Democratic and Republican claims emphasize economic growth as a means to improve living standards and reduce poverty, though they differ on the methods to achieve it. Democrats specifically highlight infrastructure and clean energy as drivers of growth, while Republicans focus on deregulation and economic freedom.

**Caveat:** Includes retrospective records and asserted economic relationships, not only policy proposals. The extracted causal assertions are not fact-checked here.

**Label provenance:** source-bound assistant revision of the preserved Gemma response; see the label-review record.

**Distinctive phrases:** economic, economy, energy, jobs, thanked, thanked contributions, growth, percent, richer, contributions

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 4.8% | 578 | 7 | 7 |
| expanded | Republican | 6.2% | 667 | 6 | 6 |
| expanded | DSA | 3.0% | 177 | 46 | 9 |
| strict | Democratic | 4.8% | 578 | 7 | 7 |
| strict | Republican | 6.2% | 667 | 6 | 6 |
| strict | DSA | 1.6% | 17 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Investments in infrastructure and manufacturing are helping millions of people thrive. (`democratic-2024-normalized-484cf745805e-012`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 26108:26821 |
| DSA | The United States economy can be restructured in an ecologically sustainable direction and one that provides good jobs at good wages only if the federal government invests significantly in infrastructure development, alternative energy, and mass-transit technologies. (`dsa-2009-priorities-normalized-e439cbeb16b4-003`) | [2009 convention national priorities resolution](https://dlarchive.dsausa.org/wp-content/uploads/2018/12/DL_2010_V037_03.pdf) scoped characters 5541:6944 |
| Republican | Cutting tax rates, simplifying the tax code, deregulating industries, and opening world markets to American enterprise resulted in tremendous growth in the 1980s. (`republican-2000-normalized-79e5ffd6ad69-015`) | [2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform) scoped characters 6170:6843 |
| Democratic | President Obama and Democrats around the country are fighting back from the deepest economic crisis since the Great Depression by laying the foundations for an economy that out-educates, out-builds, and out-innovates the rest of the world. (`democratic-2012-normalized-952aa542eb75-007`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 169318:169935 |
| Republican | By balancing environmental goals with economic growth and job creation, the American economy has made possible the investment needed to safeguard natural resources, protect endangered species, and create healthier living conditions. (`republican-2008-normalized-62e53c9c4a9e-005`) | [2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform) scoped characters 103314:103888 |
| Democratic | President Obama and Democrats around the country are fighting back from the deepest economic crisis since the Great Depression by growing the middle class. (`democratic-2012-normalized-952aa542eb75-006`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 169318:169935 |
| Democratic | When women and girls are healthy, educated, and able to participate economically, their families and communities prosper, poverty decreases, and economies grow. (`democratic-2016-normalized-0db34fffef9d-003`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 151572:152604 |
| Democratic | When women and girls are healthy, educated, and able to participate economically, their families and communities prosper, poverty decreases, and economies grow. (`democratic-2024-normalized-3f92cb29beb8-004`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 272534:273282 |
| Republican | Economic growth allows people to lift their lives out of poverty. (`republican-2004-normalized-d0360dc943ed-012`) | [2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform) scoped characters 66567:66961 |
| Democratic | Countries like Germany, Spain and Brazil have reaped the benefits of economic growth from clean energy. (`democratic-2008-normalized-0db7badf177c-009`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 38350:39296 |
| Democratic | Growing economic ties between the United States, Mexico, and Canada can address environmental and social issues of common concern. (`democratic-2000-normalized-40f95e67a678-005`) | [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform) scoped characters 142697:143836 |
| Republican | Economic freedom expands the prosperity pie. (`republican-2008-normalized-d1ed35d0f511-005`) | [2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform) scoped characters 68577:69006 |

#### topic-005: Rights, Freedoms, and Governmental Legitimacy

Claims invoke dignity, rights, freedom, self-determination, and legitimate government. Examples range from Democratic commitments to civil and cultural rights and DSA support for oppressed peoples' self-determination to Republican statements about inherent rights and consent of the governed.

**Caveat:** A broad principles-and-rights cluster. The Republican account of pre-existing rights is not a constitutional philosophy established for every group.

**Label provenance:** source-bound assistant revision of the preserved Gemma response; see the label-review record.

**Distinctive phrases:** right, rights, honor, government, liberty, people, respect, human right, freedom, constitution

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 3.3% | 347 | 7 | 7 |
| expanded | Republican | 6.3% | 651 | 6 | 6 |
| expanded | DSA | 3.0% | 186 | 56 | 8 |
| strict | Democratic | 3.3% | 347 | 7 | 7 |
| strict | Republican | 6.3% | 651 | 6 | 6 |
| strict | DSA | 1.6% | 15 | 2 | 2 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Commitment to continue to honor treaty and trust obligations and respect cultural rights. (`democratic-2012-normalized-48ae95fce867-011`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 81282:82098 |
| DSA | Support for self-determination for all oppressed people. (`dsa-2021-adopted-normalized-3a5ba8ba26bb-001`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 17354:17741 |
| Republican | Commitment to consistently act in accord with the greatest values of the country – freedom and opportunity for all. (`republican-2004-normalized-81ee1b93e20b-013`) | [2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform) scoped characters 3355:3751 |
| Democratic | Commitment to advance the ability of all persons to live with dignity, security, and respect, regardless of who they are or who they love. (`democratic-2020-normalized-33dbf90bb2e3-001`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 257854:258637 |
| Democratic | Commitment to return the Nation to its best traditions, including a commitment to government by law. (`democratic-2008-normalized-e9dff83589f8-014`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 158242:158579 |
| Democratic | Commitment to redress the systemic injustices that have long plagued society. (`democratic-2020-normalized-77dee5aebf82-002`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 3590:3945 |
| Democratic | Support for restoring the ethic of public service through service in the military, reserve forces, or diplomatic corps that keep the nation free and safe. (`democratic-2008-normalized-c45994410b23-006`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 90785:91502 |
| Democratic | Commitment to continue to honor both religious freedom and other civil rights, not put them at war with one another. (`democratic-2024-normalized-1e0b4a5c659c-009`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 186917:187231 |
| Democratic | Commitment to continue to press for human rights, the rule of law, and political freedom. (`democratic-2000-normalized-93fadee8da59-006`) | [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform) scoped characters 147542:148412 |
| Republican | Affirmation of the inherent dignity and worth of all people. (`republican-2004-normalized-8d20cde354c0-002`) | [2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform) scoped characters 265883:266781 |
| Republican | The only just government is one that governs with the consent of the governed. (`republican-2012-normalized-a59fcef5e8a6-008`) | [2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform) scoped characters 3587:4102 |
| Republican | Government does not confer rights to life, liberty, and property, but is instituted by men to protect the rights that man already possesses. (`republican-2008-normalized-92a9f5c7906a-006`) | [2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform) scoped characters 52431:52879 |

#### topic-006: American Leadership and National-Power Narratives

Claims describe America's international role, national strength, ideals, competitiveness, and relations with allies. Democratic and Republican examples often portray U.S. leadership positively; a DSA example criticizes the scale of military spending. These are claims about national identity and power, not a single agreed foreign-policy program.

**Caveat:** Political narrative and national identity overlap with foreign-policy language.

**Label provenance:** source-bound assistant revision of the preserved Gemma response; see the label-review record.

**Distinctive phrases:** america, united states, united, states, american, world, americans, american people, people, country

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 6.6% | 718 | 7 | 7 |
| expanded | Republican | 7.3% | 697 | 6 | 6 |
| expanded | DSA | 1.0% | 54 | 23 | 8 |
| strict | Democratic | 6.6% | 718 | 7 | 7 |
| strict | Republican | 7.3% | 697 | 6 | 6 |
| strict | DSA | 0.7% | 5 | 2 | 2 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | The United States is strongest when its partners are strong. (`democratic-2024-normalized-306753327989-006`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 232787:233374 |
| DSA | The United States today spends more on its armed forces than does the rest of the world combined. (`dsa-2007-economic-justice-normalized-53bb7ce424c7-006`) | [An Economic Justice Agenda - adopted November 2007](https://www.dsausa.org/wp-json/wp/v2/strategy/612) scoped characters 3286:3751 |
| Republican | In an American century, America will have the strongest economy and the strongest military in the world. (`republican-2012-normalized-7815bee1d725-005`) | [2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform) scoped characters 151956:152467 |
| Democratic | America leads with purpose. (`democratic-2016-normalized-37111ca02619-017`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 133798:134369 |
| Democratic | Through collective effort, Americans can overcome challenges. (`democratic-2012-normalized-db94890967e2-008`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 63857:64224 |
| Democratic | The United States shares its deepest values with democracies. (`democratic-2008-normalized-9444e34d73ce-004`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 109102:109568 |
| Republican | Affirmation of America's role in leading the world toward greater freedom, opportunity, and prosperity. (`republican-2004-normalized-a269dca8c6eb-001`) | [2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform) scoped characters 70595:71734 |
| Republican | America represents a set of ideals that speak to the highest aspirations of humanity. (`republican-2008-normalized-b2da0054c741-007`) | [2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform) scoped characters 140908:141272 |
| Republican | America is preserving the peace by working with more than 80 allied nations and international institutions to isolate and confront terrorists and outlaw regimes. (`republican-2004-normalized-76b5fb08ee36-004`) | [2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform) scoped characters 14536:15292 |
| Republican | Support for ensuring America remains competitive in the global marketplace. (`republican-2012-normalized-22c5dd831d0a-004`) | [2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform) scoped characters 70208:70984 |
| Republican | The United States supports closer cooperation in both military and economic matters with those on the front lines of civilization's battle against the forces of evil. (`republican-2016-normalized-28a344099db9-008`) | [2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform) scoped characters 216797:217293 |
| Democratic | America is stronger abroad and safer at home because of this principled leadership. (`democratic-2016-normalized-667eb0d7cebb-014`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 131984:132768 |

#### topic-008: Immigration Policy: Reform, Enforcement, and Detention

These claims concern U.S. immigration policy, with positions ranging from comprehensive reform and paths to citizenship to enforcing existing laws and screening immigrants. A key point of divergence is the issue of immigration detention, with some groups advocating for its complete end while others do not explicitly address it. Positions also vary on the process of immigration itself, with some advocating for faster and more efficient processes.

**Caveat:** mixed-subtopic/stance

**Distinctive phrases:** immigration, immigrants, illegal, border, deportations, aliens, illegal aliens, immigrant, migration, enforcement

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 1.7% | 219 | 7 | 7 |
| expanded | Republican | 2.7% | 155 | 6 | 6 |
| expanded | DSA | 3.0% | 133 | 27 | 9 |
| strict | Democratic | 1.7% | 219 | 7 | 7 |
| strict | Republican | 2.7% | 155 | 6 | 6 |
| strict | DSA | 4.8% | 34 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Commitment to enact comprehensive immigration reform. (`democratic-2016-normalized-a06765db4456-008`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 56962:57929 |
| DSA | Commitment to end immigration detention. (`dsa-2021-adopted-normalized-989abebd4619-007`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 13904:14050 |
| Republican | Support for enforcing U.S. immigration laws. (`republican-2016-normalized-fbf2085e7ad8-009`) | [2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform) scoped characters 179080:179795 |
| Republican | Support for properly screening refugees and other immigrants entering the United States from any country. (`republican-2016-normalized-fbf2085e7ad8-010`) | [2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform) scoped characters 179080:179795 |
| Republican | Support for efforts to enforce the law while welcoming immigrants who enter America through legal avenues. (`republican-2004-normalized-4c0905a0028b-003`) | [2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform) scoped characters 249888:249914 |
| Republican | Support for enforcing the law while welcoming immigrants who enter America through legal avenues. (`republican-2004-normalized-a736627d9796-003`) | [2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform) scoped characters 248713:249289 |
| DSA | Support for providing an expeditious path to citizenship for undocumented immigrants. (`dsa-statement-384-normalized-4db8b1a5732c-005`) | [Defend and Expand Democracy: Statement on the Voting Rights Act Supreme Court Decision](https://www.dsausa.org/wp-json/wp/v2/statement/384) scoped characters 490:947 |
| Democratic | Commitment to create a humane, 21st century immigration system that benefits all Americans. (`democratic-2020-normalized-0b9b0d310f69-006`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 5836:6328 |
| DSA | Support for ending all immigrant detention. (`dsa-2024-program-normalized-9d88be1f8868-015`) | [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf) scoped characters 8205:9248 |
| Democratic | Commitment to eliminate unfair barriers to naturalization, reduce application backlogs, and make immigration processes faster, more efficient, and less costly. (`democratic-2020-normalized-c822277bd644-004`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 192741:193625 |
| DSA | Support for demilitarizing the border and ending all immigrant detention in the US. (`dsa-2021-adopted-normalized-bf23fd771fc3-002`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 58629:58695 |
| DSA | Commitment to actively take parts in campaigns to achieve immigration reform. (`dsa-statement-366-normalized-bd9e79bce6b7-012`) | [After the Election: Keeping Fighting](https://www.dsausa.org/wp-json/wp/v2/statement/366) scoped characters 4920:5167 |

#### topic-009: Voting Rights, Election Rules, and Representation

Claims address access to voting, representation, and election rules. Democratic and DSA examples support restoring voting protections and opposing suppression; DSA examples also address incarcerated people and criminal convictions. A Republican example supports state photo-identification requirements.

**Caveat:** Includes opposing approaches to election rules and an adjacent civil-rights claim about profiling; not every example advocates expanding access.

**Label provenance:** source-bound assistant revision of the preserved Gemma response; see the label-review record.

**Distinctive phrases:** voting, vote, abolishing, committee member, committee, member, ending, elections, voting rights, electoral

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 4.3% | 525 | 7 | 7 |
| expanded | Republican | 6.0% | 537 | 6 | 6 |
| expanded | DSA | 7.6% | 266 | 56 | 9 |
| strict | Democratic | 4.3% | 525 | 7 | 7 |
| strict | Republican | 6.0% | 537 | 6 | 6 |
| strict | DSA | 14.6% | 131 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Support for restoring the full protections of the Voting Rights Act. (`democratic-2016-normalized-4292f2af0201-001`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 80174:80810 |
| DSA | Support for expanding and protecting voting rights and ending voter suppression. (`dsa-2026-program-normalized-d326f1020c4f-005`) | [Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf) scoped characters 8326:9332 |
| Republican | Support for the right of states to require an official government-issued photo identification for voting. (`republican-2008-normalized-42539f6998d6-010`) | [2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform) scoped characters 62697:63176 |
| DSA | Support for restoring the right to vote for incarcerated people and people with criminal convictions. (`dsa-2026-program-normalized-d326f1020c4f-002`) | [Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf) scoped characters 8326:9332 |
| Democratic | Support for efforts to defeat ill-motivated voter suppression tactics. (`democratic-2016-normalized-f5fefdce7197-004`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 81496:81998 |
| DSA | Support for enacting a constitutional right to vote and to be fairly represented. (`dsa-statement-384-normalized-4db8b1a5732c-006`) | [Defend and Expand Democracy: Statement on the Voting Rights Act Supreme Court Decision](https://www.dsausa.org/wp-json/wp/v2/statement/384) scoped characters 490:947 |
| DSA | Support for restoration of full voting rights to convicted felons. (`dsa-2003-electoral-normalized-6d2b6566d517-011`) | [2003 resolution on electoral reform](https://web.archive.org/web/20040110235906id_/http://www.dsausa.org/convention2003/report/r-electoral.html) scoped characters 1117:1171 |
| DSA | Support for guaranteeing the right to vote. (`dsa-2021-adopted-normalized-e91b86120260-018`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 8052:8079 |
| DSA | Support for efforts to defend the right to vote. (`dsa-2003-electoral-normalized-6d2b6566d517-012`) | [2003 resolution on electoral reform](https://web.archive.org/web/20040110235906id_/http://www.dsausa.org/convention2003/report/r-electoral.html) scoped characters 1173:1362 |
| DSA | Support for passage of the John Lewis Voting Rights Act, reenacting and strengthening the Voting Rights Act. (`dsa-2021-adopted-normalized-5746209c69bc-002`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 8531:8626 |
| Democratic | Commitment to restore the full power of the Voting Rights Act. (`democratic-2020-normalized-fcd461184fac-008`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 5092:5834 |
| Democratic | Commitment to ban racial and religious profiling in law enforcement. (`democratic-2020-normalized-11c6d091feaf-010`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 104939:105773 |

#### topic-010: Presidential Records, Promises, and Critiques

Claims name presidents or administrations when describing records, campaign promises, or criticism. Examples span Biden's infrastructure and gun legislation, Obama's alliances and student work-study, Bush's military policy, and Gore's education promises. Other examples criticize Biden's drilling, military spending, or border policy.

**Caveat:** A presidential-actor cluster spanning domestic and foreign policy, not a coherent international-alliances topic or a shared administration position.

**Label provenance:** source-bound assistant revision of the preserved Gemma response; see the label-review record.

**Distinctive phrases:** president, biden, president biden, obama, president obama, bush, president bush, administration, obama administration, signed

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 6.7% | 935 | 7 | 7 |
| expanded | Republican | 2.7% | 309 | 6 | 6 |
| expanded | DSA | 0.7% | 35 | 17 | 6 |
| strict | Democratic | 6.7% | 935 | 7 | 7 |
| strict | Republican | 2.7% | 309 | 6 | 6 |
| strict | DSA | 0.3% | 1 | 1 | 1 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Under President Biden, the United States is rebuilding roads, bridges, ports, airports, water systems, electric grids, and broadband. (`democratic-2024-normalized-9be95fb035db-008`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 11102:11739 |
| DSA | Under Joe Biden, the United States has prioritized funding a massive military budget and expanding oil drilling. (`dsa-2024-program-normalized-43f2e9413efb-003`) | [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf) scoped characters 2869:3829 |
| Republican | President Bush fulfilled a promise to begin transforming how the nation organizes and equips itself to fight 21st Century adversaries. (`republican-2004-normalized-a2113b2e5302-001`) | [2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform) scoped characters 60159:60640 |
| Democratic | With President Biden's leadership, Congress passed the Bipartisan Safer Communities Act (BSCA). (`democratic-2024-normalized-a7600837d3e2-007`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 112787:113607 |
| Democratic | Under Barack Obama, the U.S. will rebuild ties to allies in Europe and Asia. (`democratic-2008-normalized-2f22bd733321-010`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 98422:99191 |
| Democratic | President Obama pledged to double the number of work-study jobs available to students. (`democratic-2012-normalized-ec12f322f1a7-007`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 25287:26795 |
| Democratic | President Obama has worked to methodically strengthen alliances with Europe and Asia. (`democratic-2012-normalized-1567641ad953-006`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 132712:133240 |
| Republican | President Bush has rallied America to its calling to make the world safer and better. (`republican-2004-normalized-bb8654a75b0d-001`) | [2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform) scoped characters 13371:13771 |
| Democratic | Under Barack Obama, the U.S. will strengthen partnerships throughout the Americas and Africa. (`democratic-2008-normalized-2f22bd733321-011`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 98422:99191 |
| Republican | After nearly four years of the Biden administration, America is rocked by Open Borders. (`republican-2024-normalized-51f7b85d22c5-013`) | [2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform) scoped characters 2210:2408 |
| Democratic | With Al Gore as President, the U.S. will make schools safe havens for students to learn and teachers to teach. (`democratic-2000-normalized-fadbed899274-006`) | [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform) scoped characters 68469:69590 |
| Republican | The next Republican president will direct joint action with the United States in military conflict when necessary. (`republican-2000-normalized-f7d97bfd0c6d-010`) | [2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform) scoped characters 198182:198815 |

#### topic-011: Taxation of Income, Wealth, and Corporations

These claims concern policies regarding taxation, with a focus on income, wealth, and corporations. Positions vary from lowering taxes to incentivize saving and investment, to raising taxes on corporations and the wealthy, and expanding tax benefits for working families. There is also support for making the tax code fairer for the middle class.

**Distinctive phrases:** tax, taxes, raising taxes, tax credit, tax cuts, credit, cuts, income, tax code, raising

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 2.8% | 328 | 7 | 7 |
| expanded | Republican | 3.6% | 357 | 6 | 6 |
| expanded | DSA | 2.8% | 159 | 27 | 8 |
| strict | Democratic | 2.8% | 328 | 7 | 7 |
| strict | Republican | 3.6% | 357 | 6 | 6 |
| strict | DSA | 2.5% | 20 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Commitment to offer tax relief to hard working, middle-class families for the cost squeeze they have faced for years from rising health care, childcare, education, and other expenses. (`democratic-2016-normalized-1300e37ca20b-001`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 41367:41763 |
| DSA | Support for taxing financial transactions, capital gains, luxury purchases, and domestic and global corporations. (`dsa-2021-adopted-normalized-7ace82695f5d-019`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 32385:32672 |
| Republican | Support for eliminating taxes on interest, dividends, and capital gains altogether for lower and middle-income taxpayers. (`republican-2012-normalized-cf8e70a905aa-003`) | [2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform) scoped characters 12028:12139 |
| Republican | Strong support for tax reform. (`republican-2012-normalized-f95e92c5e588-006`) | [2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform) scoped characters 96929:97665 |
| Republican | Support for replacing high tax rates that discourage thrift with incentives to save. (`republican-2008-normalized-903fa1c9b13d-010`) | [2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform) scoped characters 71482:71826 |
| DSA | Support for imposing just and progressive taxes on the rich. (`dsa-2021-adopted-normalized-918420373a3a-004`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 47800:47889 |
| Republican | Support for lowering tax rates wherever they penalize thrift or discourage investment. (`republican-2016-normalized-98c6d92cf7ef-001`) | [2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform) scoped characters 8697:9408 |
| Democratic | Commitment to protect and expand tax benefits for working people and families with children. (`democratic-2024-normalized-a56d1bbc115f-010`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 37939:38133 |
| Democratic | Commitment to make sure the wealthy pay their fair share in taxes. (`democratic-2020-normalized-d9a1dc68d808-007`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 60168:60904 |
| DSA | Support for raising taxes on for-profit corporations. (`dsa-2024-program-normalized-f23d4047d972-006`) | [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf) scoped characters 7352:8203 |
| Democratic | Support for making child care and dependent tax credits significantly more generous. (`democratic-2020-normalized-5e55d1004289-008`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 205191:205948 |
| Democratic | Commitment to cut costs and make the tax code fairer for the middle class. (`democratic-2024-normalized-a56d1bbc115f-003`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 37136:37901 |

#### topic-012: Public Education: Access, Standards, and Accountability

These claims concern policies related to public education, including access to quality schools and funding for all students. There is support for various school options, from traditional public schools to charter and magnet schools, alongside commitments to raising achievement levels and closing achievement gaps. Claims also address accountability measures and approaches to school discipline.

**Caveat:** Mixed stances on school choice and accountability approaches are present.

**Distinctive phrases:** education, schools, school, students, teachers, student, public, children, learning, college

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 5.4% | 601 | 7 | 7 |
| expanded | Republican | 5.0% | 427 | 6 | 6 |
| expanded | DSA | 2.4% | 118 | 32 | 9 |
| strict | Democratic | 5.4% | 601 | 7 | 7 |
| strict | Republican | 5.0% | 427 | 6 | 6 |
| strict | DSA | 2.3% | 17 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Support for democracy education, civic education, and service requirements in schools. (`democratic-2000-normalized-f946cf8e17d5-007`) | [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform) scoped characters 25610:25867 |
| DSA | Support for providing free, quality public education from pre-K to college. (`dsa-2026-program-normalized-3ba469ba4e69-005`) | [Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf) scoped characters 4779:5913 |
| Republican | Support for parental options, including home schooling. (`republican-2008-normalized-88e1cfdc81cd-012`) | [2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform) scoped characters 121530:122395 |
| Democratic | Commitment to raising achievement levels for low-income students. (`democratic-2016-normalized-45d35ed14449-012`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 107544:107958 |
| Democratic | Support for expansion of charter schools, magnet schools, site-based schools, year-round schools, and other nontraditional public school options. (`democratic-2000-normalized-68dc8fee2e45-002`) | [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform) scoped characters 32708:33021 |
| Democratic | Commitment to close the achievement gap in education. (`democratic-2008-normalized-4794e91f1cfe-008`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 148569:149340 |
| DSA | Support for creating a truly democratic public education system. (`dsa-2007-economic-justice-normalized-500c699fb1db-014`) | [An Economic Justice Agenda - adopted November 2007](https://www.dsausa.org/wp-json/wp/v2/strategy/612) scoped characters 22261:22310 |
| Republican | Support for overhauling standards on school discipline. (`republican-2024-normalized-631b8e76912c-001`) | [2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform) scoped characters 24072:24281 |
| Democratic | Support for helping schools to lift student achievement, rather than punishing them based on state standardized tests. (`democratic-2024-normalized-0bc5902e5d0e-005`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 74850:76410 |
| Democratic | Support for increasing investments to guarantee all students can access high-quality public schools, no matter where they live. (`democratic-2020-normalized-3e1d1d365c73-005`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 121780:122351 |
| Democratic | Commitment to holding schools, districts, communities, and states accountable for raising achievement levels for all students. (`democratic-2016-normalized-45d35ed14449-011`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 107544:107958 |
| DSA | Support for democratizing and funding instruction inclusive of all students while minimizing testing at all levels of education. (`dsa-2021-adopted-normalized-6c02b493f903-009`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 29390:29603 |

#### topic-013: Reproductive Rights and Gender-Affirming Care

Claims concern reproductive rights, abortion access or restrictions, gender-affirming care, and related discrimination. Democratic and DSA examples support access and oppose restrictions, while a Republican example supports a ban on sex-selective abortions.

**Caveat:** Shared health-and-rights subject matter includes opposing abortion positions and related claims about pregnancy discrimination and violence against women.

**Label provenance:** source-bound assistant revision of the preserved Gemma response; see the label-review record.

**Distinctive phrases:** abortion, gender, women, marriage, reproductive, gender affirming, sex, sexual, affirming, discrimination

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 2.7% | 336 | 7 | 7 |
| expanded | Republican | 3.2% | 297 | 6 | 6 |
| expanded | DSA | 2.7% | 157 | 26 | 7 |
| strict | Democratic | 2.7% | 336 | 7 | 7 |
| strict | Republican | 3.2% | 297 | 6 | 6 |
| strict | DSA | 4.9% | 44 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Commitment to fight to protect and codify the right to reproductive freedom. (`democratic-2020-normalized-c3e3058c15da-004`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 124349:125100 |
| DSA | Support for reproductive justice for all. (`dsa-2021-adopted-normalized-0a25e1af4692-001`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 35005:35033 |
| Republican | Support for legislation to ban sex-selective abortions—gender discrimination in its most lethal form. (`republican-2012-normalized-19a1514122c4-004`) | [2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform) scoped characters 58975:60053 |
| Democratic | Commitment to always protect sexual and reproductive health and rights. (`democratic-2020-normalized-c28dad59ba3f-009`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 257236:257852 |
| Democratic | Commitment to defend all women's right to reproductive health care. (`democratic-2024-normalized-30cecb1c1c2f-011`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 164059:165173 |
| DSA | Support for guaranteed reproductive health care. (`dsa-2024-program-normalized-b789b4710c28-repair-1a7d74b0c436-002`) | [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf) scoped characters 6467:7350 |
| Democratic | Commitment to continue to support efforts to protect women against pregnancy discrimination. (`democratic-2012-normalized-3760905b0bc6-007`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 88897:90061 |
| Democratic | Support for vigorously opposing state and federal bans on gender-affirming health care. (`democratic-2024-normalized-9fb427e7c407-003`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 171503:171935 |
| Democratic | Commitment to end health insurance discrimination against contraception. (`democratic-2008-normalized-2d53ea9068c0-005`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 25211:25580 |
| Democratic | Support for the Violence Against Women Act. (`democratic-2008-normalized-01b3baa97bcb-018`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 145248:145705 |
| DSA | Support for repeal of the Hyde Amendment and all legal restrictions on abortion access. (`dsa-2021-adopted-normalized-0a25e1af4692-005`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 35175:35249 |
| DSA | Support for guaranteed gender-affirming health care. (`dsa-2024-program-normalized-b789b4710c28-repair-1a7d74b0c436-003`) | [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf) scoped characters 6467:7350 |

#### topic-014: International Security and Cooperation Strategies

Multiple groups express commitment to addressing global threats through international cooperation and multilateral efforts. This includes strengthening alliances, responding to humanitarian crises, and working through organizations like the United Nations. There is also stated support for demilitarization and reducing reliance on nuclear weapons.

**Distinctive phrases:** international, foreign, peace, military, nations, countries, nato, nuclear, multilateral, china

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 7.3% | 813 | 7 | 7 |
| expanded | Republican | 5.2% | 466 | 6 | 6 |
| expanded | DSA | 3.3% | 115 | 36 | 9 |
| strict | Democratic | 7.3% | 813 | 7 | 7 |
| strict | Republican | 5.2% | 466 | 6 | 6 |
| strict | DSA | 4.1% | 37 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Commitment to use diplomacy and development to confront global threats. (`democratic-2016-normalized-cba8bb3f1bb4-010`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 138544:138882 |
| DSA | Support for working cooperatively with other governments and through the United Nations to solve global problems. (`dsa-2021-adopted-normalized-bf23fd771fc3-001`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 58529:58627 |
| Republican | Commitment to provide assistance to other governments combating terrorism. (`republican-2000-normalized-92ef81be6519-006`) | [2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform) scoped characters 220627:221348 |
| Democratic | Commitment to strengthen national and multilateral capabilities to advance peace, security, and opportunity. (`democratic-2012-normalized-4811ef89e242-012`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 142382:142915 |
| Democratic | Commitment to pursue a tough, smart, and principled national security strategy. (`democratic-2008-normalized-793b790195aa-002`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 73188:73987 |
| Democratic | Commitment to forge a more effective global response to terrorism. (`democratic-2008-normalized-315e0437eb1c-001`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 79057:79689 |
| Democratic | Commitment to push for the ratification of the Comprehensive Nuclear-Test-Ban Treaty. (`democratic-2016-normalized-238f5c974856-010`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 147931:148868 |
| Democratic | Commitment to continue responding to humanitarian crises around the globe together with the American people and the international community. (`democratic-2012-normalized-b76da717e9d1-001`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 153225:154243 |
| Democratic | Commitment to reinforce alliances and partnerships that enhance collective security. (`democratic-2020-normalized-8ee0debcb266-004`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 238038:238895 |
| Democratic | Commitment to work to maintain a strong, credible deterrent while reducing overreliance and excessive expenditure on nuclear weapons. (`democratic-2020-normalized-5aac5456948b-008`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 253108:253582 |
| DSA | Support for multilateral international efforts that deny military and economic resources to authoritarian forces of all ideological stripes. (`dsa-statement-377-normalized-9e74d19c9f2d-007`) | [DSA Statement on the Islamic State and the Crisis in Iraq and Syria](https://www.dsausa.org/wp-json/wp/v2/statement/377) scoped characters 5745:6576 |
| DSA | Support for demilitarization, decolonization, and striving for a future of international solidarity and cooperation toward global climate justice. (`dsa-2021-adopted-normalized-7a4fcef26ad9-008`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 45725:45849 |

#### topic-015: U.S. Military Involvement and the War on Terror

Claims address ongoing U.S. military operations and the perceived threats of terrorism and weapons proliferation. Multiple claims reference the war in Iraq and its impact on U.S. forces, including overextension and casualties, while others acknowledge the broader 'War on Terror' and evolving threats. The claims also note the human cost of these conflicts.

**Caveat:** Mixed stances on the war's justification and consequences are present.

**Distinctive phrases:** iraq, military, war, attacks, terrorist, terrorists, weapons, troops, forces, afghanistan

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 3.9% | 362 | 7 | 7 |
| expanded | Republican | 4.3% | 489 | 6 | 6 |
| expanded | DSA | 4.5% | 174 | 37 | 9 |
| strict | Democratic | 3.9% | 362 | 7 | 7 |
| strict | Republican | 4.3% | 489 | 6 | 6 |
| strict | DSA | 1.6% | 8 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Eleven years of continuous military operations and repeated deployments to Iraq and Afghanistan have stretched U.S. forces and strained their families. (`democratic-2012-normalized-0012a775903a-005`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 155075:155400 |
| DSA | Americans have been subject to terrorist attacks. (`dsa-2001-convention-priorities-normalized-ef8a3eb37787-006`) | [2001 convention national priorities resolution](https://www.dsausa.org/files/2019/07/DL-2001-Convention-Coverage.pdf) scoped characters 0:523 |
| Republican | The War on Terror is ongoing. (`republican-2004-normalized-001ec5f5792c-002`) | [2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform) scoped characters 145524:145910 |
| Republican | America has declared war against terrorists. (`republican-2004-normalized-bb8654a75b0d-008`) | [2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform) scoped characters 14011:14534 |
| Democratic | The war in Iraq distracted the United States from confronting many of the most fundamental national security challenges facing the United States, including the danger posed by international terrorist organizations that threaten the American homeland. (`democratic-2012-normalized-13e519c73835-005`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 114618:115262 |
| DSA | U.S. troops are being routinely killed in Iraq. (`dsa-2003-iraq-normalized-aeabf36dcf1a-005`) | [2003 resolution on the occupation of Iraq](https://web.archive.org/web/20040110235717id_/http://www.dsausa.org/convention2003/report/r-iraq.html) scoped characters 741:1920 |
| Democratic | U.S. service members are in harm's way in the war against terror. (`democratic-2004-normalized-eb1979bf3bc4-006`) | [2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform) scoped characters 561:797 |
| Republican | A generation of American efforts to slow proliferation of weapons of mass destruction has unraveled as Iraq defied the international community. (`republican-2000-normalized-7247b1f63c2c-009`) | [2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform) scoped characters 155603:156031 |
| Democratic | The war in Iraq has overextended America's armed services. (`democratic-2004-normalized-f735ec2b6129-001`) | [2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform) scoped characters 35814:36207 |
| Democratic | The capacity to inflict damage from nuclear, biological, and cyber attacks is spreading to other countries and potentially to terrorist groups. (`democratic-2008-normalized-1ebff02cce7f-009`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 82789:83281 |
| Republican | America faces a new and rapidly evolving threat from terrorism and international crime. (`republican-2000-normalized-f21f2ecaf855-001`) | [2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform) scoped characters 219253:219463 |
| DSA | U.S. wars in the Middle East have left a bloody legacy, killing over a million people. (`dsa-statement-4386-normalized-89aab4241a6d-008`) | [Urgent Call For Action Against A U.S. War On Iran](https://www.dsausa.org/wp-json/wp/v2/statement/4386) scoped characters 1778:2287 |

#### topic-016: Opposition to Policies and Governing Authorities

Claims reject or criticize policies, administrations, or governing authority across several subjects. Examples oppose disenfranchisement, asserted presidential powers, international emissions agreements, U.N. Agenda 21, police training exchanges, or proposed Medicaid and SNAP changes.

**Caveat:** A mixed opposition-and-authority cluster, not one sovereignty policy. Domestic rights and social-program disputes coexist with international issues.

**Label provenance:** source-bound assistant revision of the preserved Gemma response; see the label-review record.

**Distinctive phrases:** administration, current administration, current, politicians, government, bush administration, bush, rejected, failed, republican

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 3.5% | 380 | 7 | 7 |
| expanded | Republican | 7.6% | 776 | 6 | 6 |
| expanded | DSA | 5.6% | 339 | 82 | 9 |
| strict | Democratic | 3.5% | 380 | 7 | 7 |
| strict | Republican | 7.6% | 776 | 6 | 6 |
| strict | DSA | 4.1% | 29 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Refusal to allow the use of political pretexts to disenfranchise American citizens. (`democratic-2012-normalized-fef136903755-006`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 93325:94115 |
| DSA | Commitment to prohibit training exchanges between U.S. law enforcement and global military and policing entities. (`dsa-2021-adopted-normalized-989abebd4619-012`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 14243:14341 |
| Republican | Opposition to any attempts to create race-based governments within the United States. (`republican-2008-normalized-44c3a0e30932-007`) | [2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform) scoped characters 142613:143556 |
| Democratic | Rejection of proposals to continue George Bush's economic policies. (`democratic-2008-normalized-636e039420f7-001`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 71580:71706 |
| Democratic | Rejection of sweeping claims of "inherent" presidential power. (`democratic-2008-normalized-fa1cd1900e67-010`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 155352:155975 |
| Democratic | President Obama's administration recognizes that one size does not fit all. (`democratic-2012-normalized-61aa77f5ee6e-012`) | [2012 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2012-democratic-party-platform) scoped characters 96526:97707 |
| Republican | Strong opposition to the Kyoto Protocol and similar mandatory carbon emissions controls that harm economic growth and destroy American jobs. (`republican-2004-normalized-53cdfe529adc-010`) | [2004 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2004-republican-party-platform) scoped characters 219327:219736 |
| Republican | The current administration's efforts have encouraged anti-Americanism. (`republican-2000-normalized-c753d8516acd-012`) | [2000 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2000-republican-party-platform) scoped characters 204124:204552 |
| Republican | Opposition to any U.S. domestic government that is not bound by the U.S. Constitution or Bill of Rights. (`republican-2008-normalized-44c3a0e30932-repair-6c5b9bf17f07-001`) | [2008 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2008-republican-party-platform) scoped characters 142613:143556 |
| Republican | Rejection of U.N. Agenda 21 as erosive of U.S. sovereignty. (`republican-2016-normalized-689538531846-007`) | [2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform) scoped characters 218921:219722 |
| Democratic | Commitment to oppose Republican plans to slash funding and block grant Medicaid and SNAP, which would harm millions of Americans. (`democratic-2016-normalized-f4e2c14968d7-011`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 115903:116156 |
| Republican | Opposition to the policy of Mutually Assured Destruction. (`republican-2016-normalized-fbf2085e7ad8-004`) | [2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform) scoped characters 178614:179078 |

#### topic-018: Healthcare System Goals and Approaches

Claims address goals for the healthcare system, including access, affordability, and universal coverage. Approaches vary from strengthening existing plans and increasing choice to advocating for a national system like Medicare for All. Multiple claims emphasize improving access to healthcare, while others focus on cost control.

**Caveat:** Claims represent positions from multiple groups with differing approaches.

**Distinctive phrases:** health, care, health care, medicare, insurance, medical, healthcare, coverage, health insurance, medicaid

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 5.5% | 668 | 7 | 7 |
| expanded | Republican | 5.3% | 536 | 6 | 6 |
| expanded | DSA | 3.7% | 275 | 38 | 8 |
| strict | Democratic | 5.5% | 668 | 7 | 7 |
| strict | Republican | 5.3% | 536 | 6 | 6 |
| strict | DSA | 3.1% | 36 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Commitment to provide access to affordable health insurance. (`democratic-2008-normalized-4d9ec60a89b1-004`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 69161:70120 |
| DSA | Support for a national healthcare system like Medicare For All. (`dsa-statement-5581-normalized-20cd15748fbe-003`) | [For those Grieving and Raging Today](https://www.dsausa.org/wp-json/wp/v2/statement/5581) scoped characters 3169:3606 |
| Republican | Support for increasing healthcare choice and options. (`republican-2012-normalized-1205d70085c8-002`) | [2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform) scoped characters 125557:126429 |
| Democratic | Commitment to strengthen coverage across all health plans. (`democratic-2024-normalized-aa0b71876216-002`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 216908:217600 |
| Democratic | Commitment to build a health care system that provides universal health care coverage. (`democratic-2020-normalized-3542c1bfdbb3-010`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 75631:76409 |
| Democratic | Commitment to improve health care access and affordability in the U.S. territories. (`democratic-2020-normalized-9a7a1ac81e6e-014`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 185817:186318 |
| Democratic | Commitment to fight for a comprehensive system of primary health care, including dental, mental health care, and low-cost prescription drugs. (`democratic-2016-normalized-ecd47e7958b3-013`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 117013:117666 |
| Democratic | Support for better health care. (`democratic-2024-normalized-11fdd9f0c413-005`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 31363:32475 |
| Republican | Commitment to keep healthcare costs low. (`republican-2012-normalized-167d656433b4-015`) | [2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform) scoped characters 132926:133734 |
| Republican | More than 100 million Americans depend on Medicare or Medicaid for their healthcare. (`republican-2016-normalized-591801711d53-008`) | [2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform) scoped characters 98175:98901 |
| Democratic | Commitment to end unaffordable, unavailable health care. (`democratic-2008-normalized-fa59aac8d141-010`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 4336:5162 |
| DSA | Support for health justice through Medicare for All. (`dsa-statement-6001-normalized-15ebe59edbf0-003`) | [This Struggle is Real, Part 2: Amy Coney Barrett’s Confirmation and the Rotten System](https://www.dsausa.org/wp-json/wp/v2/statement/6001) scoped characters 1409:1459 |

#### topic-019: Economic hardship and financial insecurity

Multiple sources acknowledge widespread economic struggles among Americans, including difficulties affording basic necessities like rent, food, and housing. These hardships disproportionately affect marginalized groups, including African Americans and Latinos, and are exacerbated by financial crises and economic downturns. The struggles extend to essential workers and impact the middle class both domestically and internationally.

**Distinctive phrases:** poor, recession, economic, working, unemployment, poverty, economic recession, crisis, class, living standards

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 4.2% | 498 | 7 | 7 |
| expanded | Republican | 4.1% | 440 | 6 | 6 |
| expanded | DSA | 6.5% | 375 | 63 | 9 |
| strict | Democratic | 4.2% | 498 | 7 | 7 |
| strict | Republican | 4.1% | 440 | 6 | 6 |
| strict | DSA | 4.0% | 35 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Poverty exists in the United States. (`democratic-2008-normalized-408264aea1cd-006`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 32023:32030 |
| DSA | Millions struggle with low wages, dangerous working conditions, and limited control over their own lives. (`dsa-2024-program-normalized-c0035893561c-002`) | [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf) scoped characters 1305:2868 |
| Republican | Many Americans have experienced the burden of lost jobs, lost homes, and lost hopes, and the middle class has felt that burden most acutely. (`republican-2012-normalized-cde29fc831f3-010`) | [2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform) scoped characters 1183:1326 |
| DSA | Households are struggling to pay rent, mortgages, utilities, and other needed expenses. (`dsa-statement-4955-normalized-6b70e9adf907-007`) | [DSA Endorses Increased Transit Funding in the Face of COVID-19](https://www.dsausa.org/wp-json/wp/v2/statement/4955) scoped characters 3038:3482 |
| DSA | Poor, working-class, and already marginalized people have suffered the most during past crises. (`dsa-statement-4626-normalized-6ac57c252fad-003`) | [Now is the Time for Solidarity: DSA National Statement on COVID-2019/Es la hora de solidaridad: Comunicación nacional de DSA acerca de COVID-19](https://www.dsausa.org/wp-json/wp/v2/statement/4626) scoped characters 82:497 |
| Democratic | The economy is struggling. (`democratic-2008-normalized-3a4c640c1fa0-015`) | [2008 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2008-democratic-party-platform) scoped characters 816:958 |
| DSA | Public austerity and incarceration endanger communities and make it difficult for many people to pay for rent, food, childcare, or housing. (`dsa-2021-adopted-normalized-1870bd662c8e-005`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 24811:25556 |
| Democratic | The nation's teachers, nurses, firefighters, and other essential workers are struggling with housing costs that outpace their incomes, leaving them unable to live near their workplaces. (`democratic-2024-normalized-51d7cbe64123-004`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 69540:70730 |
| Democratic | Millions of Americans are struggling under the mounting burden of life's everyday costs. (`democratic-2004-normalized-eb1979bf3bc4-011`) | [2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform) scoped characters 799:967 |
| DSA | Militarized borders, xenophobic/racist immigration laws, and an abusive prison industrial complex suppress wages and divide the working class. (`dsa-2021-adopted-normalized-6b522fa83bc9-003`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 63528:64300 |
| Democratic | African Americans and Latinos lost more than half of their net worth as a result of the housing crisis and the Great Recession. (`democratic-2016-normalized-fcee54a1c348-003`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 46632:47261 |
| DSA | Recurrent international financial crises have wiped out much of the middle classes of Latin America and Southeast Asia. (`dsa-2007-economic-justice-normalized-53bb7ce424c7-004`) | [An Economic Justice Agenda - adopted November 2007](https://www.dsausa.org/wp-json/wp/v2/strategy/612) scoped characters 2937:3265 |

#### topic-020: Critiques and Alternatives to Capitalism

These claims primarily concern critiques of capitalism, focusing on its exploitative nature and the pursuit of alternatives. Several claims advocate for shifting power and resources away from corporate elites and towards ordinary people, and envision a future without for-profit systems for essential services. The claims also address the need for worker self-organization and democratic control of wealth.

**Distinctive phrases:** capitalism, future capitalism, class, working class, future, capitalism people, socialist, working, capitalist, society

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 0.2% | 22 | 6 | 6 |
| expanded | Republican | 0.6% | 59 | 6 | 6 |
| expanded | DSA | 8.3% | 386 | 63 | 9 |
| strict | Democratic | 0.2% | 22 | 6 | 6 |
| strict | Republican | 0.6% | 59 | 6 | 6 |
| strict | DSA | 12.3% | 99 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | The President says that capitalism without competition isn't capitalism, it's exploitation. (`democratic-2024-normalized-da9ab87f7a1b-010`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 62626:63049 |
| DSA | In overcoming the order of capitalism, the working class will not only liberate itself from its own shackles, but all of humanity from the parasitic death-drive of capitalism. (`dsa-2021-adopted-normalized-49ef8772becb-005`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 1531:2250 |
| Republican | Support for others to rally to the cause of fighting crony capitalism. (`republican-2016-normalized-c44984055aab-013`) | [2016 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2016-republican-party-platform) scoped characters 118823:119969 |
| DSA | Neoliberal capitalist austerity policies enacted by governments the world over, including Wall Street Democrats in the U.S., force poor and working people to compete with each other to survive. (`dsa-statement-1896-normalized-ead9022fbed2-001`) | [DSA stands in solidarity with Christchurch](https://www.dsausa.org/wp-json/wp/v2/statement/1896) scoped characters 1225:1928 |
| DSA | Support for freedom of working-class self-organization and democratic political action. (`dsa-2021-adopted-normalized-989abebd4619-013`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 14343:14417 |
| DSA | Workers deserve better living conditions than capitalism provides. (`dsa-2026-program-normalized-07742d0be50e-repair-bdbc17da534a-004`) | [Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf) scoped characters 1296:1702 |
| DSA | In a future without capitalism, food, education, energy, medicine, and transportation may not be for-profit businesses. (`dsa-2026-program-normalized-977a2c8a9837-010`) | [Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf) scoped characters 0:1295 |
| DSA | Working people can only truly govern their destiny when they achieve democratic control of the wealth their labor (paid and unpaid) creates by building a democratic socialist society. (`dsa-2011-priorities-full-normalized-ed8e3a0bf92d-004`) | [2011 adopted convention priorities - full ten-page resolution](https://web.archive.org/web/20130108175613id_/http://www.dsausa.org/convention2011/report/Priorities%20Resolution.pdf) scoped characters 1465:3009 |
| DSA | As socialists, the group fights for the right to economic self-determination against a system in which access to the labor market affects the ability to secure stable housing, food, medical care, and so many other human rights. (`dsa-statement-4192-normalized-6765e8eb100b-009`) | [DSA National Political Committee (NPC) Statement on Impeachment](https://www.dsausa.org/wp-json/wp/v2/statement/4192) scoped characters 2345:3298 |
| DSA | Commitment to challenge attacks of neoliberal capitalist austerity on the rights and freedoms of citizens. (`dsa-2013-priorities-normalized-d4dec7ab5bbe-002`) | [2013 convention political and organizational priorities](https://web.archive.org/web/20140108003017id_/http://www.dsausa.org/convention_2013_report_priorities) scoped characters 24:708 |
| DSA | In the near term, democratic socialists struggle for reforms that shift power and resources away from corporate elites and put them in the hands of ordinary people. (`dsa-2003-mission-normalized-20f699d8e4de-002`) | [2003 adopted working mission statement](https://web.archive.org/web/20040227005032id_/http://www.dsausa.org/convention2003/report/r-mission.html) scoped characters 0:814 |
| DSA | A capitalist system exploits workers instead of benefiting them. (`dsa-2010-social-economic-rights-normalized-3b733e07abe8-010`) | [A Social and Economic Bill of Rights](https://www.dsausa.org/wp-json/wp/v2/strategy/617) scoped characters 28827:29345 |

#### topic-021: Criminal Justice: Punishment, Accountability, and Prison Reform

These claims address criminal justice, with a focus on punishment for violent offenders and accountability for abuses. Positions vary from supporting 'tough punishment' and locking up offenders to demands for release from detention and addressing wrongful harm. The claims also touch on the broader societal impacts of criminalization and violence.

**Caveat:** Mixed stances on the extent and nature of criminal justice reform are present.

**Distinctive phrases:** police, criminal, crime, violence, identified, violent, justice, policing, people, data centers

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 2.2% | 264 | 7 | 7 |
| expanded | Republican | 3.8% | 369 | 6 | 6 |
| expanded | DSA | 5.9% | 451 | 79 | 9 |
| strict | Democratic | 2.2% | 264 | 7 | 7 |
| strict | Republican | 3.8% | 369 | 6 | 6 |
| strict | DSA | 3.7% | 36 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Commitment to condemn the mistreatment of imprisoned individuals wherever it occurs. (`democratic-2020-normalized-11616ff575d6-015`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 264637:265088 |
| DSA | Disproportionate violence by policing and prisons accelerates institutional incentives to violate and imprison millions of people. (`dsa-2021-adopted-normalized-13ca43c6c588-006`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 9539:10172 |
| Republican | Commitment to lock up violent offenders. (`republican-2024-normalized-b90fbe592293-017`) | [2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform) scoped characters 7056:7174 |
| DSA | Disproportionate violence by policing and prisons widens divisions between people. (`dsa-2021-adopted-normalized-13ca43c6c588-004`) | [2021 adopted DSA Political Platform - immutable December 2021 snapshot](https://web.archive.org/web/20211230205416id_/https://www.dsausa.org/dsa-political-platform-from-2021-convention/) scoped characters 9539:10172 |
| DSA | Migrants, people of color and working class people are disproportionately criminalized in the United States. (`dsa-statement-4621-normalized-9d208ba95cab-006`) | [For a moratorium on deportations, with no exceptions/Para una moratoria de las deportaciones, sin excepciones](https://www.dsausa.org/wp-json/wp/v2/statement/4621) scoped characters 3382:4175 |
| Democratic | Support for tough punishment of violent crime. (`democratic-2004-normalized-821dd4b5fe65-002`) | [2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform) scoped characters 53040:54311 |
| DSA | Support for addressing those who have been wrongly killed, hurt, and detained. (`dsa-statement-4267-normalized-a87200f2da12-007`) | [Statement of Solidarity with the Chilean People](https://www.dsausa.org/wp-json/wp/v2/statement/4267) scoped characters 1551:1740 |
| Republican | Commitment to crush gang violence. (`republican-2024-normalized-b90fbe592293-016`) | [2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform) scoped characters 7056:7174 |
| DSA | Punish brutality by U.S. federal agents. (`dsa-2026-program-normalized-40060dd6f6dd-repair-d40710b9eecc-008`) | [Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf) scoped characters 7145:8285 |
| Democratic | Commitment to hold to account those who perpetrate human rights abuses. (`democratic-2020-normalized-11616ff575d6-016`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 264637:265088 |
| Democratic | Drug producing nations like Colombia have seen their societies torn apart by the intersection of criminal activity, political discord, and terrorism. (`democratic-2000-normalized-987b8bb7d15c-001`) | [2000 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2000-democratic-party-platform) scoped characters 121596:122397 |
| DSA | Demand for individuals in prisons, jails, detention centers, and camps to be let go. (`dsa-statement-4626-normalized-b8f72e138725-005`) | [Now is the Time for Solidarity: DSA National Statement on COVID-2019/Es la hora de solidaridad: Comunicación nacional de DSA acerca de COVID-19](https://www.dsausa.org/wp-json/wp/v2/statement/4626) scoped characters 4421:5145 |

#### topic-022: Israeli-Palestinian Conflict: Sovereignty, Rights, and Assistance

Claims concern Israeli security and Palestinian sovereignty, assistance, occupation, return, and military aid. Republican examples support Israel and its security; Democratic examples include two-state peace and Palestinian assistance; DSA examples emphasize Palestinian rights and ending arms sales.

**Caveat:** These are opposing positions on shared subject matter, not agreement. A topic share does not measure which side a group supports.

**Label provenance:** source-bound assistant revision of the preserved Gemma response; see the label-review record.

**Distinctive phrases:** israel, palestinian, israeli, gaza, palestinians, peace, palestinian people, hamas, west bank, occupation

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 1.1% | 118 | 7 | 7 |
| expanded | Republican | 1.2% | 123 | 6 | 6 |
| expanded | DSA | 5.8% | 222 | 22 | 9 |
| strict | Democratic | 1.1% | 118 | 7 | 7 |
| strict | Republican | 1.2% | 123 | 6 | 6 |
| strict | DSA | 3.3% | 15 | 3 | 3 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Commitment to the creation of a comprehensive, just and lasting peace between Israel and its neighbors. (`democratic-2004-normalized-0ad85f479ed5-007`) | [2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform) scoped characters 30512:31084 |
| DSA | Support for national sovereignty for the Palestinian people. (`dsa-2024-program-normalized-9d88be1f8868-006`) | [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf) scoped characters 8205:9248 |
| Republican | Support for Israel. (`republican-2012-normalized-2bab5f5039fa-001`) | [2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform) scoped characters 195980:196013 |
| DSA | Support for recognizing the right of the Palestinian people to resist military occupation. (`dsa-2026-program-normalized-40060dd6f6dd-008`) | [Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf) scoped characters 7145:8285 |
| DSA | Demand for the fulfillment of the right of all Palestinians to return to their homeland. (`dsa-statement-4489-normalized-5fbb11361e70-001`) | [DSA endorses vision and policy demand statement of Freedom is the Future](https://www.dsausa.org/wp-json/wp/v2/statement/4489) scoped characters 3651:4116 |
| Republican | Support for Israel's right to exist as a Jewish state with secure, defensible borders. (`republican-2012-normalized-2bab5f5039fa-005`) | [2012 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2012-republican-party-platform) scoped characters 195980:196013 |
| Democratic | Commitment to restore critical assistance to the Palestinian people in the West Bank and Gaza, consistent with U.S. law. (`democratic-2020-normalized-3c29dbc1688d-012`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 283912:284685 |
| DSA | Demand for an end to Israel’s structural violence and systematic destruction of Palestinian lives and livelihoods. (`dsa-statement-4489-normalized-5fbb11361e70-011`) | [DSA endorses vision and policy demand statement of Freedom is the Future](https://www.dsausa.org/wp-json/wp/v2/statement/4489) scoped characters 4662:5130 |
| DSA | Support for recognizing the rights of the Palestinian people, including the right of return. (`dsa-2026-program-normalized-40060dd6f6dd-007`) | [Workers Deserve More 2026 print version](https://program.dsausa.org/wp-content/uploads/2026/09/WDM-Program.pdf) scoped characters 7145:8285 |
| Democratic | Support for the creation of a democratic Palestinian state dedicated to living in peace and security side by side with the Jewish State of Israel. (`democratic-2004-normalized-ed1dec9e1db7-003`) | [2004 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2004-democratic-party-platform) scoped characters 31086:31937 |
| DSA | Opposition to retaliatory measures against the Palestinian Authority. (`dsa-statement-398-normalized-299214ac7782-007`) | [Statement on Israel-Palestine](https://www.dsausa.org/wp-json/wp/v2/statement/398) scoped characters 760:1125 |
| DSA | Support for ending weapons sales to Israel. (`dsa-2024-program-normalized-9d88be1f8868-003`) | [Workers Deserve More 2024](https://program.dsausa.org/wp-content/uploads/2024/08/DSA_2024Program.pdf) scoped characters 8205:9248 |

#### topic-023: Trump Administration Records and Partisan Critiques

Claims explicitly discuss Donald Trump across foreign relations, trade, immigration, manufacturing, labor, civil rights, and national identity. Democratic and DSA examples predominantly criticize him; Republican examples praise his trade policy and national leadership.

**Caveat:** An actor-centered, mixed-policy cluster with opposing evaluations, not exclusively a foreign-and-trade-policy topic.

**Label provenance:** source-bound assistant revision of the preserved Gemma response; see the label-review record.

**Distinctive phrases:** trump, donald, donald trump, president trump, trump administration, president, president donald, immigration policies, administration, maga

| View | Group | Share | Claims | Documents | Bundles |
|---|---|---:|---:|---:|---:|
| expanded | Democratic | 3.3% | 543 | 3 | 3 |
| expanded | Republican | 0.6% | 15 | 2 | 2 |
| expanded | DSA | 1.2% | 110 | 29 | 5 |
| strict | Democratic | 3.3% | 543 | 3 | 3 |
| strict | Republican | 0.6% | 15 | 2 | 2 |
| strict | DSA | 1.2% | 5 | 2 | 2 |

| Group | Full representative claim | Source and locator |
|---|---|---|
| Democratic | Donald Trump weakened global democratic norms. (`democratic-2024-normalized-306753327989-009`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 233376:233831 |
| DSA | Under Donald Trump, the U.S. has severely restricted immigration. (`dsa-statement-1083-normalized-e634a3021adc-004`) | [Statement on Central American Caravan/DSA se solidariza con la actual caravana centroamericana en un éxodo a los Estados Unidos](https://www.dsausa.org/wp-json/wp/v2/statement/1083) scoped characters 1574:2061 |
| Republican | President Trump turned American trade policy around, protecting U.S. producers and renegotiating failed agreements. (`republican-2024-normalized-007a594371a0-009`) | [2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform) scoped characters 16205:16227 |
| Democratic | As President, Donald Trump failed to bring manufacturing jobs home. (`democratic-2024-normalized-acb049933b3f-001`) | [2024 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2024-democratic-party-platform) scoped characters 21098:21882 |
| Democratic | Donald Trump would overturn more than 50 years of American foreign policy by abandoning NATO partners. (`democratic-2016-normalized-b4f43c23e8c1-006`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 144805:145853 |
| Democratic | President Trump has tarnished U.S. credibility. (`democratic-2020-normalized-f4a47a1af77b-010`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 224266:224581 |
| Democratic | President Trump has weakened U.S. alliances. (`democratic-2020-normalized-f4a47a1af77b-009`) | [2020 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2020-democratic-party-platform) scoped characters 224266:224581 |
| Democratic | Donald Trump has personally hired union-busting firms to undermine workers' rights. (`democratic-2016-normalized-7ba2e6e4e2f2-009`) | [2016 Democratic Party Platform](https://www.presidency.ucsb.edu/documents/2016-democratic-party-platform) scoped characters 10263:10733 |
| DSA | Donald Trump has opposed marriage equality and committed himself to the harassment of countless LGBTQIA+ women, people of color, indigenous cousins and immigrants. (`dsa-statement-409-normalized-335a09bbcb79-006`) | [Statement on Lesbian, Gay, Bisexual, Transgender, Queer and Intersex Rights](https://www.dsausa.org/wp-json/wp/v2/statement/409) scoped characters 3735:4365 |
| DSA | Donald Trump blames Mexican immigrants, Muslim terrorists, Black protesters, China’s economic and military power and American leaders for barriers to America’s “greatness”. (`dsa-statement-352-normalized-ac77172a6b86-005`) | [Fighting Back Against the Rising Tide of Nativist and Racist Reaction](https://www.dsausa.org/wp-json/wp/v2/statement/352) scoped characters 1944:3138 |
| Republican | President Donald J. Trump reignited the American Spirit and called for renewed National Pride. (`republican-2024-normalized-51f7b85d22c5-008`) | [2024 Republican Party Platform](https://www.presidency.ucsb.edu/documents/2024-republican-party-platform) scoped characters 1737:2208 |
| DSA | Donald Trump unilaterally pulled out of the Iran Nuclear Agreement, in spite of Iran’s compliance with it. (`dsa-statement-4386-normalized-89aab4241a6d-003`) | [Urgent Call For Action Against A U.S. War On Iran](https://www.dsausa.org/wp-json/wp/v2/statement/4386) scoped characters 985:1776 |

<!-- learned-topics:end -->

**Full eligible-source claim analysis with automated screening, not human-certified claims or fact-checking.** All source chunks and any failed/unresolved extractions remain auditable in the coverage tables and raw responses.

The analytical text is the **claim**, not its original evidence passage. The separate passage-based analysis and its outputs remain unchanged.

| Organization | Claims analyzed | Documents | Document / fallback bundles |
|---|---:|---:|---:|
| Democratic | 11870 | 7 | 7 |
| Republican | 9460 | 6 | 6 |
| DSA | 5153 | 122 | 9 |

## Semantic density

[Compact density overview](../figures/national_claims/full/expanded/pairwise_density.png). For detailed maps and source-linked representative claims, see the learned-topic section's detailed density comparisons.

The shared representation uses 10 dimensions for KDE; the two-dimensional display is not the density-estimation space. Sampling balances organizations and gives each document/fallback-period bundle equal aggregate density weight. Positive contrasts mean greater first-organization language density, not agreement, ideological direction, or causal differences.

Platforms/programs-only sensitivity: **complete**. Its independently fitted space has 5 dimensions; its coordinates cannot be compared directly with the expanded map.

## Topics

![Document-weighted CAP topic emphasis](../figures/national_claims/full/topic_emphasis.png)
![Document-weighted CAP topic emphasis, continued](../figures/national_claims/full/topic_emphasis_2.png)

The existing pinned MiniLM classifier compares normalized claim text with CAP topic descriptions (minimum cosine similarity 0.2). Each claim receives at most one topic; unclassified claims remain in the denominator. This is exploratory classification, not validated topic gold. Topic shares use equal aggregate document/fallback-bundle weights, not raw claim counts.

| Organization | Largest weighted topic shares in this input |
|---|---|
| Democratic | Unclassified 13.8%; International affairs 9.1%; Social welfare 7.9% |
| Republican | Unclassified 15.0%; Defense and veterans 8.4%; International affairs 7.9% |
| DSA | Unclassified 13.6%; Social welfare 11.3%; Government operations 9.7% |

DSA's adopted-only input contains 3 documents and 842 claims, compared with 122 documents and 5,153 claims in the expanded input.
The largest classified DSA topic is Social welfare (11.3%) in the expanded input and Social welfare (12.9%) in the strict input. This sensitivity reflects source-type and period composition, not a measured change in positions over time.

## Provenance and reproduction

Full extraction uses source chunks of at most 240 words, sentence-aware splitting of long paragraphs, and at most 1,200 preceding-context characters. The prompt requires preservation of actors, stance/modality, conditions, temporal scope and reported-speaker attribution; automated revision does not certify that every requirement was met. Source organization remains metadata rather than a mechanically repeated embedding prefix. Exact within-document claim duplicates are retained in downloads but excluded from fitting.

- [Complete claim/source download, not metadata only](https://github.com/hanshanley/dsa/releases/download/claim-public-pngs-2026-10-31/claim_documents.zip)
- [Claims and exact supporting source offsets](../data/analysis/national_claims/full/claims.csv)
- [Complete source texts](../data/analysis/national_claims/full/complete_sources.csv)
- [Topic assignments](../data/analysis/national_claims/full/topic_assignments.csv)
- [Weighted topic shares, both views](../data/analysis/national_claims/full/topic_emphasis.csv)
- [Machine-readable analysis summary](../data/analysis/national_claims/full/analysis_summary.json)

Source documents retain their original attribution. Claims describe what sources assert; they do not independently establish truth. Pooling mixes periods and genres. Missing historical sources, including the final 2015 DSA strategy, remain missing rather than being inferred from later documents. No website deployment is performed.

Extraction status: **complete**; effective chunk dispositions: `{"normalized": 2462, "source_repaired": 161}`.
[Source coverage](../data/analysis/national_claims/full/source_coverage.csv) / [Chunk dispositions](../data/analysis/national_claims/full/block_status.csv)

Original Gemma chunk outcomes remain `{"normalized": 2596, "validation_failed": 27}`. Targeted assistant source corrections cover **161 chunks** and supply **1,041 replacement claims**; **1,078 original candidates** are superseded, not erased. Zero-claim corrections explicitly dispose of non-policy material rather than inventing assertions.

Each correction is bound to the exact target, reference-only context, raw-response bytes and normalization fingerprint. Unaffected model claims retain their original IDs and wording; superseded originals remain in the download but cannot enter fitting or anchor duplicates. Corrected rows have `normalization_origin=assistant_source_repair` and a blank `model_claim_text`, never a falsely attributed Gemma reply. Original model failures and diagnostics remain failures in `model_status`, even when a source correction recovers their content. This is targeted assistant source-entailment work, not independent human gold or factual verification.

Archived original-candidate review flags: **1,054**; flagged model candidates still lacking a superseding correction: **0**. Historical flags are not a count of unresolved errors in replacement claims.
[Source-bound correction records](../data/analysis/national_claims/full/source_repairs/)
