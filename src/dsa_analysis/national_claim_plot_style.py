"""Publication styling aligned with hanshanley/uk_decline's house palette."""

from __future__ import annotations

from pathlib import Path
from textwrap import fill

import numpy as np

BG = "#F7F5F0"
PAGE_BG = "#F5F5F5"
COLORS = {
    "democratic": "#3D6F8C",
    "republican": "#C85A3D",
    "dsa": "#C2993E",
    "libertarian": "#4A7C59",
}
PLOT_STYLE = {
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "savefig.facecolor": BG,
    "text.color": "#1A1A1A",
    "axes.labelcolor": "#1A1A1A",
    "xtick.color": "#6B6B6B",
    "ytick.color": "#6B6B6B",
    "axes.edgecolor": "#D6D3CC",
    "axes.linewidth": 0.8,
    "grid.color": "#D6D3CC",
    "grid.alpha": 0.6,
    "grid.linewidth": 0.5,
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 17,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "figure.titlesize": 18,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.major.size": 0,
    "ytick.major.size": 0,
    "text.parse_math": False,
}


def house_style() -> None:
    import matplotlib.pyplot as plt

    plt.rcParams.update(PLOT_STYLE)


def issue_figure(title: str, subtitle: str):
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(9, 5.5))
    fig.set_gid("issue-card")
    fig.text(0.08, 0.955, "THE MARGIN OF ERROR", fontsize=8, color="#6B6B6B")
    fig.text(0.08, 0.905, fill(title, 48), va="top", fontsize=16, weight="bold", linespacing=1.2)
    fig.text(0.08, 0.755, subtitle, fontsize=9, color="#6B6B6B")
    note = fig.text(
        0.08,
        0.035,
        "Source: national political documents. Equal weight per document or source collection.",
        fontsize=7.5,
        color="#6B6B6B",
    )
    note.set_gid("source-note")
    return fig


def save_figure(fig, stem: Path) -> None:
    if not any(text.get_gid() == "source-note" for text in fig.texts):
        note = fig.text(
            0.01,
            -0.02,
            "Sources: national political documents. Analysis: The Margin of Error.",
            fontsize=8,
            color="#6B6B6B",
            style="italic",
        )
        note.set_gid("source-note")
    stem.parent.mkdir(parents=True, exist_ok=True)
    stem.with_suffix(".svg").unlink(missing_ok=True)
    fig.savefig(
        stem.with_suffix(".png"),
        dpi=200,
        bbox_inches=None if fig.get_gid() == "issue-card" else "tight",
        pad_inches=0 if fig.get_gid() == "issue-card" else 0.18,
        metadata={"Software": None},
    )


def comparison_page(
    title, subtitle, names, columns, values, upper, *, differences=False, summaries=None
):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter, MaxNLocator, PercentFormatter

    wrapped = None
    width, height = 12, 6.5
    if summaries is not None:
        if (
            differences
            or len(summaries) != len(columns)
            or any(len(column) != len(names) for column in summaries)
        ):
            raise ValueError("Position summaries must match overall-share columns and rows")
        wrapped = [
            [fill(text, 42, break_long_words=False, break_on_hyphens=False) for text in column]
            for column in summaries
        ]
        lines = max(len(text.splitlines()) for column in wrapped for text in column)
        width = 5 + 5 * len(columns)
        height = 3.2 + len(names) * max(0.65, 0.15 * lines + 0.1)
    left = 0.7 / width if wrapped is not None else 0.055
    bottom = 1.5 / height if wrapped is not None else 0.21
    content_height = (height - 3.2) / height if wrapped is not None else 0.57
    fig = plt.figure(figsize=(width, height))
    fig.set_gid("issue-card")
    fig.text(
        left, 1 - 0.45 / height if wrapped is not None else 0.95, title, fontsize=17, weight="bold"
    )
    fig.text(
        left,
        1 - 0.96 / height if wrapped is not None else 0.895,
        subtitle,
        fontsize=9,
        color="#6B6B6B",
    )
    labels = fig.add_axes(
        (left, bottom, 3.5 / width if wrapped is not None else 0.32, content_height)
    )
    labels.set_ylim(len(names) - 0.5, -0.5)
    labels.set_axis_off()
    for index, name in enumerate(names):
        labels.text(0, index, fill(name, 38), va="center", fontsize=9)
    for index, (heading, positive, negative) in enumerate(columns):
        axis = fig.add_axes(
            (
                (4.8 + index * 5) / width
                if wrapped is not None
                else 0.39 + index * 0.58 / len(columns),
                bottom,
                1.5 / width if wrapped is not None else 0.43 / len(columns),
                content_height,
            )
        )
        axis.set_title(heading, loc="left", fontsize=10, weight="normal", pad=14)
        for y, (value, warning) in enumerate(values[index]):
            color = "#6B6B6B"
            if value is None:
                detail = "No data"
            else:
                color = negative if differences and value < 0 else positive
                if names[y] == "Unclassified":
                    color = "#AAA69E"
                axis.barh(
                    y,
                    value,
                    height=0.12 * len(names) / (content_height * height)
                    if wrapped is not None
                    else 0.25,
                    color=color,
                    zorder=3,
                )
                detail = f"{value * 100:+.1f}" if differences else f"{value:.1%}"
                detail += "*" if warning else ""
            leftward = differences and value is not None and value < 0
            axis.annotate(
                detail,
                (value if value is not None else 0, y),
                xytext=(-4 if leftward else 4, 0),
                textcoords="offset points",
                ha="right" if leftward else "left",
                fontsize=8,
                va="center",
                color=color,
                annotation_clip=False,
                gid="bar-value",
            )
            if wrapped is not None:
                axis.text(
                    2 / 1.5,
                    y,
                    wrapped[index][y],
                    transform=axis.get_yaxis_transform(),
                    fontsize=9,
                    va="center",
                    color="#333333",
                    linespacing=1.2,
                    gid="group-position-summary",
                )
        axis.set_ylim(len(names) - 0.5, -0.5)
        axis.set_xlim(-upper if differences else 0, upper)
        axis.set_yticks([])
        axis.xaxis.set_major_locator(MaxNLocator(nbins=3, steps=[1, 2, 5, 10]))
        axis.xaxis.set_major_formatter(
            FuncFormatter(lambda value, _: f"{value * 100:g}")
            if differences
            else PercentFormatter(1, decimals=0)
        )
        axis.tick_params(axis="x", labelsize=8, pad=8)
        axis.spines["left"].set_visible(False)
        axis.grid(axis="x", alpha=0.35)
        axis.set_axisbelow(True)
        if differences:
            axis.axvline(0, color="#AAA69E", linewidth=0.7)
    fig.text(
        left,
        0.65 / height if wrapped is not None else 0.12,
        "Percentage-point gap: positive = first group has a larger share. "
        "* Support/sensitivity warning."
        if differences
        else "Weighted share of claims. Same scale in every column and on every page.",
        fontsize=8,
        color="#6B6B6B",
    )
    note = fig.text(
        left,
        0.23 / height if wrapped is not None else 0.05,
        "THE MARGIN OF ERROR | National political documents. "
        "Language emphasis, not policy agreement.",
        fontsize=7.5,
        color="#6B6B6B",
    )
    note.set_gid("source-note")
    return fig


def export_page_versions(figures: Path) -> dict:
    from PIL import Image, ImageColor

    destination = figures / "themarginoferror"
    for old in figures.rglob("*.svg"):
        old.unlink()
    sources = [
        p for p in figures.rglob("*") if p.suffix == ".png" and not p.is_relative_to(destination)
    ]
    expected = set()
    before = np.array((*ImageColor.getrgb(BG), 255), dtype=np.uint8)
    after = np.array((*ImageColor.getrgb(PAGE_BG), 255), dtype=np.uint8)
    for source in sources:
        target = destination / source.relative_to(figures)
        expected.add(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as image:
            pixels = np.array(image.convert("RGBA"))
        mask = np.all(pixels == before, axis=2)
        if not mask.any():
            raise ValueError(f"Missing publication background in {source}")
        pixels[mask] = after
        Image.fromarray(pixels).save(target, dpi=(200, 200))
    for old in destination.rglob("*"):
        if old.is_file() and old.suffix in {".png", ".svg"} and old not in expected:
            old.unlink()
    return {
        "substack_background": BG,
        "themarginoferror_background": PAGE_BG,
        "original_assets": len(sources),
        "page_assets": len(expected),
    }


def render_supporting(corpus: Path, figures: Path) -> None:
    from .national_claim_analysis import plot_topics
    from .national_platform_kde import plot_outputs
    from .national_platforms import ROOT, read_rows

    cap = corpus / "topic_emphasis.csv"
    if cap.exists():
        shares = [r for r in read_rows(cap) if r["view"] == "expanded"]
        for row in shares:
            row["share"] = float(row["share"])
        plot_topics(shares, figures, groups=tuple(dict.fromkeys(r["group"] for r in shares)))
    coverage = ROOT / "data/analysis/national_platforms/coverage.csv"
    if corpus.name != "full" or not coverage.exists():
        return
    import json

    for view in ("expanded", "strict"):
        directory = corpus / view
        if not (directory / "summary.json").exists():
            continue
        result = json.loads((directory / "summary.json").read_text())
        result["_scored"] = read_rows(directory / "scored_passages.csv")
        for row in result["_scored"]:
            for key, value in row.items():
                if key in {"umap_x", "umap_y"} or "_vs_" in key:
                    row[key] = float(value)
        result["_regions"] = read_rows(directory / "regions.csv")
        result["_documents"] = read_rows(directory / "document_chronology.csv")
        for row in result["_documents"]:
            if row["cosine_distance_from_previous"]:
                row["cosine_distance_from_previous"] = float(row["cosine_distance_from_previous"])
        plot_outputs(result, read_rows(coverage), figures / view)
        from .national_platforms import write_rows

        write_rows(directory / "density_region_evidence.csv", result.get("_density_evidence", []))
