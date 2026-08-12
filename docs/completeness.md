# Completeness standard

The project is complete only when all of the following conditions hold for the period beginning
January 1, 2016:

1. Every current or historically identified DSA chapter has a resolved record for every election
   year: `verified`, `searched_not_found`, or `source_unavailable` with an explanation.
2. Every DSA National and local-chapter candidate endorsement found in official pages, archived
   pages, voter guides, statements, newsletters, or official social accounts is either verified
   into the dataset or explicitly rejected as a false lead.
3. Every endorsed candidacy is classified by election type. Partisan Democratic primaries,
   nonpartisan primaries, blanket primaries, and top-two primaries remain distinct.
4. Every candidate appearing on the same certified primary ballot is recorded, not only the
   winner, runner-up, incumbent, or best-funded opponent.
5. The endorsed candidate and every opponent have reviewed first-party policy evidence or an
   explicit `source_unavailable` result after documented searching.
6. Every reported sticking point links both sides' exact words and distinguishes an explicit
   campaign conflict from an analyst-coded policy difference.
7. `uv run dsa-analysis validate --strict` passes.

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
