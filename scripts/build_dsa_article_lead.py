"""Render the article-only lead from reviewed, weighted subject shares."""

import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ("dsa", "democratic", "republican")
COLORS = ("#c39a36", "#3d7699", "#c65a3b")
PAPER = "#f2efe7"
INK = "#242321"


def rank_attention_gaps(labels: list[dict], rows: list[dict]) -> list[dict]:
    shares = {
        (row["topic_id"], row["group"]): float(row["share"])
        for row in rows
        if row["view"] == "expanded" and row["available"] == "True"
    }
    ranked = []
    for label in labels:
        if not label.get("displayed", True):
            continue
        topic = label["topic_id"]
        if any((topic, group) not in shares for group in GROUPS):
            raise ValueError(f"Missing observed party shares for {topic}")
        values = {group: shares[topic, group] for group in GROUPS}
        combined = (values["democratic"] + values["republican"]) / 2
        ranked.append(
            dict(
                topic_id=topic,
                title=label["title"],
                shares=values,
                combined_share=combined,
                gap=values["dsa"] - combined,
            )
        )
    return sorted(ranked, key=lambda row: (-abs(row["gap"]), row["topic_id"]))[:3]


def render(records: list[dict], output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.labelcolor": INK})
    fig = plt.figure(figsize=(12.8, 7.2), facecolor=PAPER)
    fig.text(0.065, 0.952, "NATIONAL PARTY DOCUMENTS  /  2000\u20132026", fontsize=9.5)
    fig.text(
        0.065,
        0.884,
        "Where DSA stands apart",
        fontsize=31,
        fontfamily="DejaVu Serif",
        fontweight="bold",
    )
    fig.text(
        0.065,
        0.830,
        "The three largest attention gaps versus the Democratic\u2013Republican average",
        fontsize=12,
    )
    fig.legend(
        [Patch(facecolor=color) for color in COLORS],
        ["DSA", "Democratic", "Republican"],
        loc="upper left",
        bbox_to_anchor=(0.059, 0.790),
        frameon=False,
        ncol=3,
        fontsize=10.5,
        columnspacing=2.5,
        handlelength=1.2,
    )
    maximum = (
        math.ceil(max(100 * value for row in records for value in row["shares"].values()) / 5) * 5
    )
    import textwrap

    for index, row in enumerate(records):
        left = 0.065 + index * 0.30
        title = row["title"].replace("Israel-Palestine", "Israel\u2013Palestine")
        fig.text(
            left,
            0.697,
            textwrap.fill(title, width=29),
            fontsize=13.5,
            fontfamily="DejaVu Serif",
            fontweight="bold",
            va="top",
            linespacing=1.25,
        )
        fig.text(left, 0.566, f"{100 * row['gap']:+.1f} pp", fontsize=17, fontweight="bold")
        fig.text(
            left,
            0.530,
            f"DSA {'above' if row['gap'] > 0 else 'below'} the major-party average",
            fontsize=9.3,
            color="#625d53",
        )
        ax = fig.add_axes((left + 0.065, 0.314, 0.195, 0.176), facecolor=PAPER)
        values = [100 * row["shares"][group] for group in GROUPS]
        ax.barh([2, 1, 0], values, height=0.43, color=COLORS, zorder=3)
        ax.set_yticks([2, 1, 0], ["DSA", "Democratic", "Republican"], fontsize=9.3)
        ax.set_xlim(0, maximum * 1.17)
        ax.set_xticks(
            [0, maximum / 2, maximum],
            [f"{value:g}%" for value in (0, maximum / 2, maximum)],
            fontsize=8.8,
        )
        ax.tick_params(axis="both", length=0, pad=7, colors="#625d53")
        ax.grid(axis="x", color="#ded8cd", linewidth=0.65, zorder=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        for y, value in zip([2, 1, 0], values):
            ax.text(value + maximum * 0.025, y, f"{value:.1f}%", va="center", fontsize=10)
        fig.text(
            left,
            0.252,
            f"Major-party average: {100 * row['combined_share']:.1f}%",
            fontsize=9.5,
            color="#625d53",
        )
    fig.add_artist(
        Line2D(
            [0.065, 0.94], [0.205, 0.205], transform=fig.transFigure, color="#bcb5a8", linewidth=0.6
        )
    )
    fig.text(
        0.065,
        0.156,
        "Ranked by absolute DSA share minus (Democratic share + Republican share) / 2.",
        fontsize=9.2,
    )
    fig.text(
        0.065,
        0.112,
        "Weighted document/fallback-bundle attention. "
        "Identity topics are not ranked; shares are not renormalized.",
        fontsize=9.2,
    )
    fig.text(
        0.065,
        0.068,
        "Attention differences are not measures of policy disagreement. "
        "2024\u20132026 is a partial period.",
        fontsize=9.2,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        output,
        dpi=200,
        facecolor=PAPER,
        metadata={"Title": "Where DSA stands apart", "Software": "dsa-analysis"},
    )
    plt.close(fig)


def main() -> None:
    data = ROOT / "data/analysis/national_claims/full/topics"
    labels_path, shares_path = data / "topic_labels.json", data / "shares.csv"
    labels = json.loads(labels_path.read_text())
    with shares_path.open(newline="") as handle:
        records = rank_attention_gaps(labels, list(csv.DictReader(handle)))
    output = ROOT / "figures/article/dsa_vs_major_parties_lead.png"
    render(records, output)
    metadata = dict(
        article_only=True,
        ranking=(
            "largest absolute weighted attention gap; "
            "DSA minus equal-weight Democratic/Republican average"
        ),
        input_sha256={
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (labels_path, shares_path)
        },
        topics=records,
        image_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
    )
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
