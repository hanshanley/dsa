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


def draw_issue_timeline(
    axis, series: dict[str, np.ndarray], period_labels: list[str], upper: float
):
    from matplotlib.ticker import MaxNLocator, PercentFormatter

    from .national_claim_plot_style import COLORS
    from .national_platform_kde import LABELS

    endpoints = []
    for index, (group, values) in enumerate(series.items()):
        axis.plot(
            range(len(period_labels)),
            values,
            marker=("o", "s", "D", "^")[index],
            markersize=3,
            linewidth=1.7,
            color=COLORS[group],
        )
        observed = np.flatnonzero(np.isfinite(values))
        if len(observed):
            last = observed[-1]
            detail = f"{values[last]:.1%}"
            if last != len(period_labels) - 1:
                detail += f" ({period_labels[last]})"
            endpoints.append((values[last] / upper, group, detail, last == len(period_labels) - 1))
        else:
            endpoints.append((0.0, group, "No observations", False))
    # Keep close-valued series labels readable without moving their data points.
    endpoints.sort(key=lambda item: item[0])
    positions = np.clip([item[0] for item in endpoints], 0.05, 0.95)
    axis_height = axis.get_position().height * axis.figure.get_size_inches()[1]
    heights = np.array([9 / 72 * (1 if item[3] else 2.5) / axis_height for item in endpoints])
    for index in range(1, len(positions)):
        gap = (heights[index - 1] + heights[index]) / 2 + 0.035
        positions[index] = max(positions[index], positions[index - 1] + gap)
    if positions[-1] + heights[-1] / 2 > 0.97:
        positions -= positions[-1] + heights[-1] / 2 - 0.97
    for position, (value_position, group, detail, current) in zip(positions, endpoints):
        if current and abs(position - value_position) > 0.02:
            axis.annotate(
                "",
                xy=(len(period_labels) - 1, value_position * upper),
                xycoords="data",
                xytext=(1.025, position),
                textcoords="axes fraction",
                arrowprops={"arrowstyle": "-", "color": "#AAA69E", "linewidth": 0.6},
                annotation_clip=False,
            )
        separator = " " if current else "\n"
        axis.text(
            1.035,
            position,
            f"{LABELS[group]}{separator}{detail}",
            transform=axis.transAxes,
            va="center",
            fontsize=9,
            color=COLORS[group],
            linespacing=1.5,
        )
    axis.set_xticks(range(len(period_labels)), period_labels, fontsize=8)
    axis.tick_params(axis="y", labelsize=9, pad=8)
    axis.tick_params(axis="x", pad=8)
    axis.set_xlim(-0.15, len(period_labels) - 0.7)
    axis.yaxis.set_major_formatter(PercentFormatter(1, decimals=1 if upper < 0.04 else 0))
    axis.yaxis.set_major_locator(MaxNLocator(nbins=4, min_n_ticks=3, steps=[1, 2, 5, 10]))
    axis.set_ylim(0, upper)
    axis.grid(axis="y")
    axis.set_axisbelow(True)
    axis.spines["left"].set_visible(False)


def plot_temporal(
    tables: dict[str, list[dict]],
    figures: Path,
    labels: dict,
    groups: tuple[str, ...],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from .national_claim_plot_style import issue_figure, save_figure

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
                f"Share of claims over time | {view.capitalize()} sources",
            )
            axis = fig.add_axes((0.08, 0.27, 0.68, 0.42))
            series = {
                group: np.array(
                    [
                        float(lookup[group, topic, period])
                        if lookup[group, topic, period] != ""
                        else np.nan
                        for period in periods
                    ]
                )
                for group in groups
            }
            draw_issue_timeline(axis, series, period_labels, upper)
            fig.text(
                0.08,
                0.13,
                "Four-year periods. Gaps mean no observed documents; "
                "labels show the last observation.",
                fontsize=7.5,
                color="#6B6B6B",
            )
            fig.text(
                0.08,
                0.085,
                f"*2024-26 ends {DEFAULT_CUTOFF}. "
                "Source composition varies; not a measure of agreement.",
                fontsize=7.5,
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
