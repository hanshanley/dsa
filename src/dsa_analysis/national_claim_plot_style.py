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
    "svg.hashsalt": "national-claim-topics-v2",
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
        "Source: national political documents. Equal document / fallback-bundle weights.",
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
    for extension in ("png", "svg"):
        fig.savefig(
            stem.with_suffix(f".{extension}"),
            dpi=200,
            bbox_inches=None if fig.get_gid() == "issue-card" else "tight",
            pad_inches=0 if fig.get_gid() == "issue-card" else 0.18,
            metadata={"Date": None} if extension == "svg" else None,
        )


def export_page_versions(figures: Path) -> dict:
    from PIL import Image, ImageColor

    destination = figures / "themarginoferror"
    sources = [
        p
        for p in figures.rglob("*")
        if p.suffix in {".png", ".svg"} and not p.is_relative_to(destination)
    ]
    expected = set()
    before = np.array((*ImageColor.getrgb(BG), 255), dtype=np.uint8)
    after = np.array((*ImageColor.getrgb(PAGE_BG), 255), dtype=np.uint8)
    for source in sources:
        target = destination / source.relative_to(figures)
        expected.add(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == ".png":
            with Image.open(source) as image:
                pixels = np.array(image.convert("RGBA"))
            mask = np.all(pixels == before, axis=2)
            if not mask.any():
                raise ValueError(f"Missing publication background in {source}")
            pixels[mask] = after
            Image.fromarray(pixels).save(target, dpi=(200, 200))
        else:
            target.write_text(source.read_text().replace(BG.lower(), PAGE_BG.lower()))
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
