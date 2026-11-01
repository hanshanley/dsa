"""Render article-only density and attention figures from published results."""

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ("dsa", "democratic", "republican")
COLORS = ("#c39a36", "#3d7699", "#c65a3b")
PAPER = "#f2efe7"
INK = "#242321"
DISPLAY_LABELS = {
    "Institutional Power, Oppression, and Social Conflict": "Power, oppression\n& social conflict",
    "Criminal Justice, Policing, and Incarceration": "Policing &\nincarceration",
    "Community Investment, Housing, and Social Support": "Housing &\ncommunity support",
    "Israel-Palestine Peace, Security, and Palestinian Rights": "Israel\u2013Palestine",
    "Economic Prosperity Narratives and Development Models": "Prosperity &\ndevelopment models",
}


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


def combined_density_contrast(point: list) -> float:
    democratic, republican, dsa = point[5:8]
    maximum = max(democratic, republican)
    mixture = maximum + math.log(
        (math.exp(democratic - maximum) + math.exp(republican - maximum)) / 2
    )
    return dsa - mixture


def rank_density_areas(data: dict, claims: list[dict]) -> list[dict]:
    lookup = {claim["claim_id"]: claim for claim in claims}
    points = {point[0]: point for point in data["points"]}
    if (
        len(lookup) != len(claims)
        or len(points) != len(data["points"])
        or set(lookup) != set(points)
    ):
        raise ValueError("Density ranking requires exact unique claim membership")
    dsa_group = data["groups"].index("dsa")
    for point in points.values():
        if data["groups"][point[4]] != lookup[point[0]]["group"]:
            raise ValueError("Density ranking claim group mismatch")
        if not all(math.isfinite(value) for value in point[1:]):
            raise ValueError("Non-finite density ranking input")
    bundles = {
        claim_id: claim.get("bundle_id") or claim.get("document_id")
        for claim_id, claim in lookup.items()
        if claim["group"] == "dsa"
    }
    if any(not bundle for bundle in bundles.values()):
        raise ValueError("Missing DSA source bundle")
    counts = Counter(bundles.values())
    ranked = []
    for index, topic in enumerate(data["topics"]):
        if not topic["displayed"]:
            continue
        members = [
            point for point in points.values() if point[3] == index and point[4] == dsa_group
        ]
        bundle_count = len({bundles[point[0]] for point in members})
        if bundle_count < 2:
            continue
        weights = [1 / counts[bundles[point[0]]] for point in members]
        mass = sum(weights)
        contrast = (
            sum(
                weight * combined_density_contrast(point) for point, weight in zip(members, weights)
            )
            / mass
        )
        if contrast <= 0:
            continue
        center = [
            sum(weight * point[column] for point, weight in zip(members, weights)) / mass
            for column in (1, 2)
        ]
        examples = [
            points[example["claim_id"]]
            for example in topic["examples"]
            if example["group"] == "dsa"
            and combined_density_contrast(points[example["claim_id"]]) > 0
        ]
        if not examples:
            raise ValueError(f"No reviewed DSA-heavy example for {topic['topic_id']}")
        anchor = min(
            examples,
            key=lambda point: (
                sum(
                    ((point[column] - center[column - 1]) / (limits[1] - limits[0])) ** 2
                    for column, limits in zip((1, 2), data["limits"])
                ),
                point[0],
            ),
        )
        ranked.append(
            dict(
                topic_id=topic["topic_id"],
                title=topic["title"],
                mean_log_density_contrast=contrast,
                dsa_claims=len(members),
                dsa_bundles=bundle_count,
                anchor_claim_id=anchor[0],
                anchor_coordinates=anchor[1:3],
                anchor_log_density_contrast=combined_density_contrast(anchor),
                anchor_source_url=lookup[anchor[0]]["source_url"],
            )
        )
    return sorted(
        ranked, key=lambda record: (-record["mean_log_density_contrast"], record["topic_id"])
    )[:5]


def render_density(data: dict, records: list[dict], output: Path) -> None:
    import textwrap

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, Normalize

    plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK})
    fig = plt.figure(figsize=(16, 10), facecolor=PAPER)
    fig.text(
        0.045, 0.946, "NATIONAL PARTY DOCUMENTS  /  2000\u20132026", fontsize=10.5, color="#625d53"
    )
    fig.text(
        0.045,
        0.888,
        "Where DSA stands apart",
        fontsize=27,
        fontfamily="DejaVu Serif",
        fontweight="bold",
    )
    fig.text(
        0.045,
        0.844,
        "Five areas of denser language vs. Democrats + Republicans",
        fontsize=14.5,
        color="#625d53",
    )
    axis = fig.add_axes((0.035, 0.19, 0.69, 0.61), facecolor=PAPER)
    palette = LinearSegmentedColormap.from_list("combined_density", ["#b19cd9", PAPER, "#c2993e"])
    bound = data["color_bound"]
    normalization = Normalize(-bound, bound, clip=True)
    points = data["points"]
    axis.scatter(
        [point[1] for point in points],
        [point[2] for point in points],
        c=[combined_density_contrast(point) for point in points],
        cmap=palette,
        norm=normalization,
        s=1.8,
        alpha=0.78,
        linewidths=0,
        rasterized=True,
    )
    axis.set_xlim(data["limits"][0])
    axis.set_ylim(data["limits"][1])
    axis.set_axis_off()
    for number, record in enumerate(records, 1):
        x, y = record["anchor_coordinates"]
        axis.text(
            x,
            y,
            str(number),
            fontsize=12.5,
            ha="center",
            va="center",
            color=INK,
            bbox=dict(boxstyle="circle,pad=0.3", facecolor=PAPER, edgecolor=INK, linewidth=0.65),
            zorder=5,
        )
        top = 0.748 - (number - 1) * 0.11
        fig.text(
            0.755, top, str(number), fontsize=12.5, color="#8d6c25", fontweight="bold", va="top"
        )
        fig.text(
            0.785,
            top,
            DISPLAY_LABELS.get(record["title"], textwrap.fill(record["title"], width=22)),
            fontsize=17,
            va="top",
            linespacing=1.35,
        )
    color_axis = fig.add_axes((0.045, 0.143, 0.68, 0.008))
    bar = fig.colorbar(
        plt.cm.ScalarMappable(norm=normalization, cmap=palette),
        cax=color_axis,
        orientation="horizontal",
        ticks=[-bound, 0, bound],
    )
    bar.outline.set_visible(False)
    bar.ax.set_xticklabels([f"{-bound:.2f}", "0", f"+{bound:.2f}"])
    bar.ax.tick_params(length=0, labelsize=11, pad=6, colors="#625d53")
    fig.text(0.045, 0.094, "Denser Democratic + Republican language", fontsize=12, color=INK)
    fig.text(0.725, 0.094, "Denser DSA language", fontsize=12, color=INK, ha="right")
    fig.text(
        0.045,
        0.035,
        "Equal-weight major-party baseline. Numbers locate examples, not boundaries. "
        "Concentration is not policy agreement.",
        fontsize=10.5,
        color="#625d53",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        output,
        dpi=225,
        facecolor=PAPER,
        metadata={"Title": "Where DSA stands apart", "Software": "dsa-analysis"},
    )
    plt.close(fig)


def render_attention_gaps(records: list[dict], output: Path) -> None:
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
    from build_platform_publication import DATA, density_map_data

    data = ROOT / "data/analysis/national_claims/full/topics"
    labels_path, shares_path = data / "topic_labels.json", data / "shares.csv"
    labels = json.loads(labels_path.read_text())
    with shares_path.open(newline="") as handle:
        records = rank_attention_gaps(labels, list(csv.DictReader(handle)))
    output = ROOT / "figures/article/dsa_vs_major_parties_attention_gaps.png"
    render_attention_gaps(records, output)
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
    full = ROOT / DATA
    representatives_path = data / "representatives.csv"
    claims_path = full / "analysis_claims.csv"
    with representatives_path.open(newline="") as handle:
        representatives = list(csv.DictReader(handle))
    with claims_path.open(newline="") as handle:
        claims = list(csv.DictReader(handle))
    density = density_map_data(ROOT, labels, representatives)
    records = rank_density_areas(density, claims)
    if len(records) != 5:
        raise ValueError("The article lead requires five supported DSA-heavy issues")
    output = ROOT / "figures/article/dsa_vs_major_parties_lead.png"
    render_density(density, records, output)
    inputs = [
        labels_path,
        representatives_path,
        claims_path,
        full / "expanded/scored_passages.csv",
        full / "expanded/density_region_evidence.csv",
        data / "assignments.csv",
        data / "positions/group_positions.json",
    ]
    metadata = dict(
        article_only=True,
        ranking="largest positive source-balanced mean combined log density contrast at DSA claims",
        contrast="log p(DSA) - log((p(Democratic) + p(Republican)) / 2)",
        weighting="equal DSA bundle mass, equal eligible claim mass within each bundle",
        minimum_dsa_bundles=2,
        anchor_selection=(
            "reviewed positive-contrast DSA example nearest the weighted 2D issue center"
        ),
        map_claims=len(density["points"]),
        display_labels={
            record["topic_id"]: DISPLAY_LABELS.get(record["title"], record["title"]).replace(
                "\n", " "
            )
            for record in records
        },
        color_bound=density["color_bound"],
        input_sha256={
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in inputs
        },
        topics=records,
        image_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
    )
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
