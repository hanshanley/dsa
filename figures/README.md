# Figures

**Two destinations, one home for current figures.** Choose Substack or
The Margin of Error, then use the same readable issue filenames.
Substack uses `#F5F5F5`; The Margin of Error uses `#F7F5F0`,
matching the destination themes in `hanshanley/china-us-relation-change`.
Only background pixels change; chart marks, text, dimensions and values stay intact.

```text
figures/
  substack/          Article images and Substack-background charts
  margin-of-error/   Website-background charts
  data/              Complete attention-share ratios
```

| Use | Substack | The Margin of Error |
|---|---|---|
| The DSA map with five attention ratios and dated statements | [where-dsa-stands-apart.png](substack/where-dsa-stands-apart.png) | [where-dsa-stands-apart.png](margin-of-error/where-dsa-stands-apart.png) |
| All 21 substantive issues in one chart | [PNG](substack/all-issues-overview.png) | [PNG](margin-of-error/all-issues-overview.png) |
| Named issue charts and combined article graphics | [Browse](substack/README.md#issue-charts) | [Browse](margin-of-error/README.md#issue-charts) |
| Positions, overview pages, density maps and supporting figures | [Browse](substack/README.md) | [Browse](margin-of-error/README.md) |

[All four attention-share ratios, including flagged identity clusters](data/attention-share-ratios.csv).

[Download the Substack lead PNG directly](https://raw.githubusercontent.com/hanshanley/dsa/main/figures/substack/where-dsa-stands-apart.png). The [lead's exact values, dated statements and source anchors](article/dsa_vs_major_parties_lead.json) remain alongside the original.

## What goes where

Both destinations use `issues/`, `positions/`, `overviews/`, and `supporting/`.
Main folders contain the expanded comparison; `supporting/adopted-only/`
contains strict-view sensitivity figures. `supporting/period-themes/`
contains independently discovered period topics. Article alternatives
are under each destination's `alternatives/`, not mixed with final lead images.

The website uses its [live interactive map](https://www.themarginoferror.com/party-platforms/) rather than the article lead.
Complete claims, source texts and the analytical archive remain linked from
[results and downloads](../README.md#results-and-downloads).

## Refreshing this folder

After regenerating canonical figures, run:

```bash
python scripts/build_publication_folder.py
python scripts/build_publication_folder.py --check
```

`manifest.json` records original paths, source and export SHA-256 hashes,
and destination backgrounds. The check rejects missing or stale exports;
CI runs it too.

## Research originals and history

`national_claims/full/` and `article/` retain the original analytical bytes
for report links, replay hashes, releases and the website's pinned inputs.
They are research inputs, not additional places to find publishing images.
Earlier [reviewed-sample](national_claims/reviewed_sample/) and
[passage-based](national_platforms/) figures remain historical.
