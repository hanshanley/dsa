"""Observed-document topic trajectories on the fixed expanded-corpus taxonomy."""

from __future__ import annotations

import json
import math
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
    from matplotlib.colors import Normalize, TwoSlopeNorm
    from matplotlib.ticker import PercentFormatter

    from .national_platform_kde import COLORS, LABELS

    plt.rcParams.update(PLOT_STYLE)
    shares, ratios = tables["temporal_shares.csv"], tables["temporal_contrasts.csv"]
    for view in ("expanded", "strict"):
        destination = figures / view
        for stem in ("time_trends_", *(f"time_{group}_" for group in groups)):
            for path in destination.glob(f"{stem}*"):
                if path.suffix in {".png", ".svg"}:
                    path.unlink()
    coverage = {
        (row["view"], row["group"], row["period"]): row for row in tables["temporal_coverage.csv"]
    }
    topics = sorted(
        {row["topic_id"] for row in shares} - {NOISE},
        key=lambda topic: (
            -sum(
                float(row["share"] or 0)
                for row in shares
                if row["view"] == "expanded" and row["topic_id"] == topic
            )
        ),
    )
    if not topics:
        return
    periods = list(dict.fromkeys(row["period"] for row in shares))
    maximum = max(float(row["share"] or 0) for row in shares)
    title = lambda topic: labels.get(topic, {}).get("title", topic)  # noqa: E731
    for view in ("expanded", "strict"):
        destination = figures / view
        destination.mkdir(parents=True, exist_ok=True)
        lookup = {
            (row["group"], row["topic_id"], row["period"]): row["share"]
            for row in shares
            if row["view"] == view
        }
        relative = {
            (row["group"], row["topic_id"], row["period"]): row["log2_ratio"]
            for row in ratios
            if row["view"] == view and row["comparison"] == "vs_rest"
        }
        for group in groups:
            for metric, source, norm, cmap_name in (
                ("share", lookup, Normalize(0, maximum), "Blues"),
                ("relative", relative, TwoSlopeNorm(vmin=-3, vcenter=0, vmax=3), "RdBu_r"),
            ):
                data = np.array(
                    [
                        [
                            float(source.get((group, topic, period), np.nan))
                            if source.get((group, topic, period), "") != ""
                            else np.nan
                            for period in periods
                        ]
                        for topic in topics
                    ]
                )
                fig, axis = plt.subplots(
                    figsize=(12, max(5, len(topics) * 0.35 + 2)), layout="constrained"
                )
                cmap = plt.get_cmap(cmap_name).copy()
                cmap.set_bad("#e6e6e6")
                image = axis.imshow(data, aspect="auto", cmap=cmap, norm=norm)
                axis.set_yticks(range(len(topics)), [title(topic) for topic in topics])
                period_labels = [
                    f"{period}\n"
                    f"{coverage[view, group, period]['documents']}d / "
                    f"{coverage[view, group, period]['bundles']}b"
                    for period in periods
                ]
                axis.set_xticks(range(len(periods)), period_labels, rotation=30, ha="right")
                metric_name = "shares" if metric == "share" else "relative emphasis"
                axis.set_title(
                    f"{LABELS[group]}: topic {metric_name} over time | {view}",
                    loc="left",
                    pad=15,
                )
                axis.set_xlabel(
                    "Observed adoption/publication period; d = documents, b = bundles; "
                    "gray = unavailable.\n"
                    "Final period is partial. No carry-forward or annual-position estimates."
                    + (
                        "\nRelative emphasis requires every comparison group; "
                        "colors saturate at +/-3."
                        if metric == "relative"
                        else ""
                    )
                )
                bar = fig.colorbar(image, ax=axis, shrink=0.65)
                if metric == "share":
                    bar.ax.yaxis.set_major_formatter(PercentFormatter(1))
                    bar.set_label("Weighted topic share")
                else:
                    bar.set_label("log2 share ratio vs fixed other groups")
                for extension in ("png", "svg"):
                    fig.savefig(
                        destination / f"time_{group}_{metric}.{extension}",
                        dpi=180,
                        metadata={"Date": None} if extension == "svg" else None,
                    )
                plt.close(fig)
        for page, start in enumerate(range(0, len(topics), 6), 1):
            chunk = topics[start : start + 6]
            fig, axes = plt.subplots(
                math.ceil(len(chunk) / 2),
                2,
                figsize=(14, 3 * math.ceil(len(chunk) / 2) + 1),
                squeeze=False,
                layout="constrained",
            )
            for axis, topic in zip(axes.ravel(), chunk, strict=False):
                for group in groups:
                    values = [
                        float(lookup[group, topic, period])
                        if lookup[group, topic, period] != ""
                        else np.nan
                        for period in periods
                    ]
                    axis.plot(
                        range(len(periods)),
                        values,
                        marker="o",
                        markersize=4,
                        linewidth=1.5,
                        color=COLORS[group],
                        label=LABELS[group],
                    )
                axis.set_title(title(topic), fontsize=10, loc="left")
                axis.set_xticks(range(len(periods)), periods, rotation=30, ha="right", fontsize=8)
                axis.yaxis.set_major_formatter(PercentFormatter(1))
                axis.set_ylim(0, maximum * 1.08)
                axis.grid(axis="y", color="#e5e5e5", linewidth=0.6)
                axis.set_axisbelow(True)
            for axis in axes.ravel()[len(chunk) :]:
                axis.set_visible(False)
            axes.ravel()[0].legend(frameon=False, fontsize=8)
            fig.suptitle(
                f"Topic shares over time | {view} | page {page}\n"
                "Observed documents only; gaps are missing evidence, not zero positions.",
                fontsize=12,
            )
            for extension in ("png", "svg"):
                fig.savefig(
                    destination / f"time_trends_{page}.{extension}",
                    dpi=180,
                    metadata={"Date": None} if extension == "svg" else None,
                )
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
