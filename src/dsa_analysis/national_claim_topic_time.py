"""Observed-document topic trajectories on the fixed expanded-corpus taxonomy."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

from .national_claim_topics import NOISE, PLOT_STYLE, contrasts, distributions
from .national_platforms import (
    DEFAULT_CUTOFF,
    date_bounds,
    digest,
    read_rows,
    write_json,
    write_rows,
)

START_YEAR = 2000
PERIOD_YEARS = 4


def temporal_tables(
    rows: list[dict],
    assignments: list[str],
    sources: list[dict],
    groups: tuple[str, ...],
    epsilon: float,
    *,
    cutoff: str = DEFAULT_CUTOFF,
) -> dict[str, list[dict]]:
    if len(rows) != len(assignments):
        raise ValueError("Temporal assignment row count mismatch")
    by_id = {source["document_id"]: source for source in sources}
    last_year = date_bounds(cutoff)[0].year
    taxonomy = set(assignments)
    dated, excluded = {}, []
    for identifier, source in by_id.items():
        field = "adoption_date" if source.get("adoption_date") else "publication_date"
        value = source.get(field, "")
        try:
            lower, upper = date_bounds(value)
            first = START_YEAR + ((lower.year - START_YEAR) // PERIOD_YEARS) * PERIOD_YEARS
            if (
                lower.year < START_YEAR
                or lower > date_bounds(cutoff)[0]
                or upper.year >= first + PERIOD_YEARS
            ):
                raise ValueError("Date outside study or ambiguous across periods")
        except ValueError as error:
            excluded.append(
                {
                    "document_id": identifier,
                    "date_field": field,
                    "date_value": value,
                    "reason": str(error),
                }
            )
            continue
        dated[identifier] = {
            "period_start": first,
            "date_field": field,
            "date_value": value,
            "date_lower": lower.isoformat(),
            "date_upper": upper.isoformat(),
        }
    shares, ratios, coverage = [], [], []
    for first in range(START_YEAR, last_year + 1, PERIOD_YEARS):
        last = min(first + PERIOD_YEARS - 1, last_year)
        period = {
            "period_start": first,
            "period_end": last,
            "period": f"{first}-{last}",
            "partial_period": first + PERIOD_YEARS - 1 > last_year,
        }
        indices = [
            i
            for i, row in enumerate(rows)
            if dated.get(row["document_id"], {}).get("period_start") == first
        ]
        selected = [rows[i] for i in indices]
        labels = [assignments[i] for i in indices]
        period_shares = distributions(selected, labels, groups, taxonomy=taxonomy)
        period_ratios = contrasts(period_shares, groups, epsilon)
        for view in ("expanded", "strict"):
            available = {
                row["group"] for row in period_shares if row["view"] == view and row["available"]
            }
            for group in groups:
                evidence = [
                    row
                    for row in selected
                    if row["group"] == group and (view == "expanded" or row["strict"])
                ]
                documents = {row["document_id"] for row in evidence}
                units = {row["bundle_id"] for row in evidence}
                warnings = []
                if not documents:
                    warnings.append("no_observed_document")
                elif len(units) < 2:
                    warnings.append("single_bundle")
                if len(available) < len(groups):
                    warnings.append("incomplete_fixed_group_baseline")
                coverage.append(
                    {
                        **period,
                        "view": view,
                        "group": group,
                        "available": bool(documents),
                        "claims": len(evidence),
                        "documents": len(documents),
                        "bundles": len(units),
                        "document_ids": ";".join(sorted(documents)),
                        "source_types": json.dumps(
                            dict(
                                Counter(
                                    by_id[identifier]["document_type"] for identifier in documents
                                )
                            ),
                            sort_keys=True,
                        ),
                        "warnings": ";".join(warnings),
                    }
                )
        shares.extend({**period, **row} for row in period_shares)
        for row in period_ratios:
            if (
                row["comparison"] == "vs_rest"
                and len(row["baseline_groups"].split(",")) != len(groups) - 1
            ):
                continue
            row["warnings"] += (
                ";" if row["warnings"] else ""
            ) + "observed_document_period_not_annual_estimate"
            ratios.append({**period, **row})
    indexed = {
        (row["period_start"], row["view"], row["group"], row["topic_id"]): row for row in shares
    }
    changes = []
    for row in shares:
        previous = indexed.get(
            (row["period_start"] - PERIOD_YEARS, row["view"], row["group"], row["topic_id"])
        )
        if not previous or not row["available"] or not previous["available"]:
            continue
        changes.append(
            {
                "period": row["period"],
                "previous_period": previous["period"],
                "view": row["view"],
                "group": row["group"],
                "topic_id": row["topic_id"],
                "share": row["share"],
                "previous_share": previous["share"],
                "percentage_point_change": 100 * (row["share"] - previous["share"]),
                "group_bundles": row["group_bundles"],
                "previous_group_bundles": previous["group_bundles"],
                "warnings": (
                    "source_composition_not_causal_change"
                    + (
                        ";single_bundle"
                        if min(row["group_bundles"], previous["group_bundles"]) < 2
                        else ""
                    )
                ),
            }
        )
    dates = [{"document_id": identifier, **values} for identifier, values in sorted(dated.items())]
    return {
        "temporal_shares.csv": shares,
        "temporal_contrasts.csv": ratios,
        "temporal_coverage.csv": coverage,
        "temporal_changes.csv": changes,
        "temporal_document_dates.csv": dates,
        "temporal_exclusions.csv": excluded,
    }


def plot_temporal(
    tables: dict[str, list[dict]],
    figures: Path,
    labels: dict,
    groups: tuple[str, ...],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator, PercentFormatter

    from .national_claim_plot_style import COLORS, issue_figure, save_figure
    from .national_platform_kde import LABELS

    plt.rcParams.update(PLOT_STYLE)
    shares = tables["temporal_shares.csv"]
    for view in ("expanded", "strict"):
        destination = figures / view
        for stem in ("time_trends_", *(f"time_{group}_" for group in groups)):
            for path in destination.glob(f"{stem}*"):
                if path.suffix in {".png", ".svg"}:
                    path.unlink()
    topics = sorted({row["topic_id"] for row in shares} - {NOISE})
    if not topics:
        return
    periods = list(dict.fromkeys(row["period"] for row in shares))
    partial = {row["period"] for row in shares if row["partial_period"] in (True, "True")}
    period_labels = [
        f"{period[:4]}-{period[-2:]}{'*' if period in partial else ''}" for period in periods
    ]
    title = lambda topic: labels.get(topic, {}).get("title", topic)  # noqa: E731
    for view in ("expanded", "strict"):
        destination = figures / view / "issues"
        destination.mkdir(parents=True, exist_ok=True)
        for path in destination.glob("*_time.*"):
            if path.suffix in {".png", ".svg"}:
                path.unlink()
        lookup = {
            (row["group"], row["topic_id"], row["period"]): row["share"]
            for row in shares
            if row["view"] == view
        }
        for topic in topics:
            maximum = max(float(row["share"] or 0) for row in shares if row["topic_id"] == topic)
            upper = max(0.01, np.ceil(maximum * 1.15 * 100) / 100)
            fig = issue_figure(
                title(topic),
                f"Within-period share of claims | {view.capitalize()} sources | "
                f"Latest period: {periods[-1]}{'*' if periods[-1] in partial else ''}",
            )
            axis = fig.add_axes((0.08, 0.21, 0.86, 0.42))
            for index, (group, x) in enumerate(zip(groups, np.linspace(0.08, 0.75, len(groups)))):
                values = np.array(
                    [
                        float(lookup[group, topic, period])
                        if lookup[group, topic, period] != ""
                        else np.nan
                        for period in periods
                    ]
                )
                fig.text(x, 0.755, LABELS[group], color=COLORS[group], fontsize=10, weight="bold")
                fig.text(
                    x,
                    0.69,
                    f"{values[-1]:.1%}" if np.isfinite(values[-1]) else "No data",
                    fontsize=20,
                    color=COLORS[group],
                    weight="bold",
                )
                axis.plot(
                    range(len(periods)),
                    values,
                    marker=("o", "s", "D", "^")[index],
                    markersize=3.5,
                    linewidth=2,
                    color=COLORS[group],
                )
                if np.isfinite(values[-1]):
                    axis.scatter(
                        len(periods) - 1,
                        values[-1],
                        s=40,
                        color=COLORS[group],
                        edgecolors="white",
                        linewidths=1,
                        zorder=4,
                    )
            axis.set_xticks(range(len(periods)), period_labels, fontsize=9)
            axis.set_xlim(-0.15, len(periods) - 0.7)
            axis.yaxis.set_major_formatter(PercentFormatter(1, decimals=1 if upper < 0.04 else 0))
            axis.yaxis.set_major_locator(MaxNLocator(nbins=4, min_n_ticks=3, steps=[1, 2, 5, 10]))
            axis.set_ylim(0, upper)
            axis.grid(axis="y")
            axis.set_axisbelow(True)
            axis.spines["left"].set_visible(False)
            fig.text(
                0.08,
                0.115,
                "Observed four-year periods; missing documents leave gaps, not zero shares.",
                fontsize=8.5,
                color="#6B6B6B",
            )
            fig.text(
                0.08,
                0.075,
                f"*Final period ends {DEFAULT_CUTOFF}. Equal document/bundle weights; "
                "source composition varies.",
                fontsize=8,
                color="#6B6B6B",
            )
            save_figure(fig, destination / f"{topic}_time")
            plt.close(fig)


def generate(
    corpus: Path,
    rows: list[dict],
    assignments: list[str],
    groups: tuple[str, ...],
    epsilon: float,
    figures: Path,
    labels: dict,
) -> dict:
    tables = temporal_tables(
        rows, assignments, read_rows(corpus / "complete_sources.csv"), groups, epsilon
    )
    directory = corpus / "topics"
    for name, records in tables.items():
        write_rows(directory / name, records)
    plot_temporal(tables, figures, labels, groups)
    summary = {
        "period_years": PERIOD_YEARS,
        "start_year": START_YEAR,
        "cutoff": DEFAULT_CUTOFF,
        "date_rule": "Adoption date when recorded, otherwise publication date; preserve precision",
        "taxonomy": "Fixed expanded-corpus topics; no per-period refits",
        "weighting": "Equal within-period document/fallback-bundle mass per organization",
        "relative_baseline": "All other configured groups required; no changing vs-rest baselines",
        "carry_forward": False,
        "exclusions": len(tables["temporal_exclusions.csv"]),
        "implementation_sha256": digest(Path(__file__).read_bytes()),
    }
    write_json(directory / "temporal_summary.json", summary)
    return summary
