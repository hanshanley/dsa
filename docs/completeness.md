# Completeness standard

The election study begins January 1, 2016. Source discovery begins January 1, 2015, so prior-year
endorsements and campaign material for 2016 primaries are retained. The congressional
special-election inventory also keeps 2015 contests. Source publication dates and election
dates must not be conflated.

The project is complete only when all of the following conditions hold:

1. Every current or historically identified DSA chapter has a resolved record for every election
   year: `verified`, `searched_not_found`, or `source_unavailable` with an explanation.
2. Every DSA National and local-chapter candidate endorsement found in official pages, archived
   pages, voter guides, statements, newsletters, or official social accounts is either verified
   into the dataset or explicitly rejected as a false lead.
3. Every endorsed candidacy is classified by election type. Partisan Democratic primaries,
   nonpartisan primaries, blanket primaries, and top-two primaries remain distinct.
4. Every candidate appearing on the same certified primary ballot is recorded, not only the
   winner, runner-up, incumbent, or best-funded other Democrat.
5. The endorsed candidate and every other Democrat in the primary have reviewed first-party policy evidence or an
   explicit `source_unavailable` result after documented searching.
6. Every reported sticking point links both sides' exact words and distinguishes an explicit
   campaign conflict from an analyst-coded policy difference.
7. `uv run dsa-analysis validate --strict` passes.
8. The nationwide congressional inventory covers every regular House seat and the independently
   verified Senate class in every 2016–2026 cycle, with nonvoting delegations separately retained.
   This inventory includes all parties, not only DSA-endorsed contests.
9. Every special election, primary, runoff, repeat election, convention, and unopposed nomination
   is reconciled against election-authority sources. Named candidates, aggregate write-ins,
   fusion ballot lines, and repeated observations are not conflated.
10. Every claimed primary roster includes the losing candidates. FEC filings, a general-ballot
    nominee list, a seat checklist, or a scheduled election date cannot establish primary-roster
    completeness.

## What counts as a completed search

Finding one verified endorsement does not complete a chapter-year census. Likewise, crawling
URLs without reviewing their contents, a transient fetch failure, and a truncated archive search
cannot be promoted to a completed search. Current-year reviews predating the research cutoff
remain open.

Explicit chapter-year resolutions may be recorded in
`data/manual/chapter_year_resolutions.csv` with `coverage_id`, `status`, `searched_on`,
`evidence_urls`, and `notes`. Status must be `verified`, `searched_not_found`, or
`source_unavailable`, with substantive search notes and source locators. The absence of this file
does not create default resolutions. Historically identified chapters are retained even if
absent from the current directory.

`audit-census` writes a row-level ledger of known gaps and a year-by-year accounting;
`collect-congressional` writes a separate all-party congressional inventory. Neither command's
successful execution means the underlying census is complete. Consult the `complete` field,
not merely the exit status. The congressional importer deliberately remains uncertified until
the election-specific roster, date, special-election, and text-coverage obligations are resolved.

## Source limitations

No official nationwide archive aggregates local DSA endorsements. Chapter websites and accounts
must be searched individually, including historical archives.

No free government dataset covers every federal, state, county, municipal, school-board,
judicial, and special-district primary. Federal and many state races can be resolved with FEC,
OpenElections, and official state results. The local long tail requires election-authority
records; commercial BallotReady or Ballotpedia data can accelerate discovery but cannot replace
official verification.

`source_unavailable` is not silently treated as no endorsement or no position. It is retained as
a documented limitation and excluded from substantive frequency denominators.
