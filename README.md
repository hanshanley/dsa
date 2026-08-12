# DSA positions and Democratic primary contrasts

This project builds an auditable dataset and report from what political organizations and
candidates actually said. It covers 2016 onward and distinguishes official party texts,
DSA endorsements, candidates' statements, opponents' statements, explicit campaign conflicts,
and analyst-coded policy differences.

Journalism and third-party trackers may locate primary sources, but do not substantiate claims.

## Quick start

```bash
uv run dsa-analysis init-db
uv run dsa-analysis validate
uv run dsa-analysis analyze
uv run python -m unittest discover -s tests -v
```

Fetch registered sources into `data/raw/` with:

```bash
uv run dsa-analysis collect
uv run dsa-analysis collect-endorsements
uv run dsa-analysis collect-chapters
uv run dsa-analysis build-queue
uv run dsa-analysis crawl-chapters
uv run dsa-analysis extract-endorsement-mentions
uv run dsa-analysis extract-local-leads
uv run dsa-analysis crawl-wayback
uv run dsa-analysis filter-wayback
uv run dsa-analysis fetch-archive-pages
uv run dsa-analysis build-coverage-ledger
uv run dsa-analysis merge-endorsement-reviews
uv run dsa-analysis build-opponent-queue
uv run dsa-analysis collect-voter-guides
uv run dsa-analysis finalize-endorsement-verification
uv run dsa-analysis prepare-opponent-batches
uv run dsa-analysis merge-opponent-reviews
uv run dsa-analysis prepare-statement-batches
uv run dsa-analysis prepare-partial-statement-batches
uv run dsa-analysis merge-statement-reviews
uv run dsa-analysis analyze-sticking-points
uv run dsa-analysis build-priorities
uv run dsa-analysis validate --strict
```

Collection records retrieval time, HTTP metadata, SHA-256 hashes, and failures. Machine-generated
transcripts must be verified before supporting a report claim.

## Evidence workflow

1. Register an official source in `data/manual/documents.csv`.
2. Add endorsements and race metadata to `data/manual/endorsements.csv`.
3. Add every primary-ballot candidate to `data/manual/race_candidates.csv`.
4. Add exact passages to `data/manual/excerpts.csv`, including page or timestamp.
5. Add candidate/opponent differences to `data/manual/contrasts.csv`.
6. Run `validate`, resolve errors, then run `analyze`.

See `docs/methodology.md`, `docs/codebook.md`, `docs/data_dictionary.md`, and
`docs/completeness.md`.
