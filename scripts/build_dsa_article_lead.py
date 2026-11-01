"""Render article-only concentration and attention figures from published results."""

import argparse
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
SNIPPETS = {
    "dsa-2021-adopted-normalized-6b522fa83bc9-003": (
        "DSA links militarized borders, racist immigration laws and the prison industrial "
        "complex to wage suppression and working-class division."
    ),
    "dsa-2024-program-normalized-b789b4710c28-006": "Demilitarize police departments.",
    "dsa-2010-social-economic-rights-normalized-edb91d554823-010": (
        "Government should promote housing co-ops and nonprofit/community development "
        "corporations committed to revitalizing communities."
    ),
    "dsa-2004-israel-palestine-normalized-3bb1d6b334dc-002": (
        "The U.S. and EU should pressure the Palestinian Authority to do all it can "
        "to stop attacks on Israeli civilians."
    ),
    "dsa-2024-program-normalized-c0035893561c-004": (
        "DSA argues that billionaires profit from controlling access to housing, "
        "healthcare and education."
    ),
}
SNIPPET_CLAIM_SHA256 = {
    "dsa-2021-adopted-normalized-6b522fa83bc9-003": (
        "26fa3be04ecf60cbb9fe65e35909214ee52771e60b1d7baaf74906239a4a5e8a"
    ),
    "dsa-2024-program-normalized-b789b4710c28-006": (
        "a59081c2ed74563e4a740892cc83abbfdc5d6cef4b80ec69b7b3acf5f754ff4b"
    ),
    "dsa-2010-social-economic-rights-normalized-edb91d554823-010": (
        "2d58601570c156dda97942c85ccd5d89bbfdb4ae938b9e4508ba254733135bfd"
    ),
    "dsa-2004-israel-palestine-normalized-3bb1d6b334dc-002": (
        "d362a42551c1fc975e5d572794351931e51c2b8152a22cdd18231516b604220a"
    ),
    "dsa-2024-program-normalized-c0035893561c-004": (
        "dbc13771670910116c140bc5a9dae53ab9eb28a42d02b362fce7ed2424ae40d9"
    ),
}


def snippet_records(records: list[dict], claims: list[dict]) -> list[dict]:
    lookup = {claim["claim_id"]: claim for claim in claims}
    result = []
    for record in records:
        claim = lookup[record["anchor_claim_id"]]
        if claim["group"] != "dsa" or claim["analysis_eligible"] != "True":
            raise ValueError("Article snippets require eligible central DSA anchors")
        if claim["claim_id"] not in SNIPPETS:
            raise ValueError("Changed article anchor requires a new source-bound paraphrase")
        if (
            hashlib.sha256(claim["claim_text"].encode()).hexdigest()
            != SNIPPET_CLAIM_SHA256[claim["claim_id"]]
        ):
            raise ValueError("Changed claim text requires a new source-bound paraphrase")
        result.append(
            dict(
                **record,
                snippet=SNIPPETS[claim["claim_id"]],
                snippet_basis="assistant paraphrase of the preserved reviewed central claim",
                source_claim_text=claim["claim_text"],
                source_evidence=claim["evidence"],
                source_sha256=claim["source_sha256"],
                document_id=claim["document_id"],
                document_title=claim["title"],
                document_type=claim["document_type"],
                source_date=claim["publication_date"],
                density_ratio=math.exp(record["mean_log_density_contrast"]),
            )
        )
    return result


def render_variant(data: dict, records: list[dict], output: Path, layout: str) -> None:
    import textwrap

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, Normalize

    plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK})
    if layout not in ("map-five", "map-bottom", "map-three"):
        raise ValueError(f"Unknown article layout: {layout}")
    bottom = layout == "map-bottom"
    five = layout == "map-five"
    selected = records if five else records[:3]
    fig = plt.figure(figsize=(18, 13.5 if five else 12 if bottom else 10), facecolor=PAPER)
    fig.text(
        0.045, 0.950, "NATIONAL PARTY DOCUMENTS  /  2000\u20132026", fontsize=11, color="#625d53"
    )
    fig.text(
        0.045,
        0.885,
        "Where DSA stands apart",
        fontsize=34,
        fontfamily="DejaVu Serif",
        fontweight="bold",
    )
    fig.text(
        0.045,
        0.837,
        f"{'Five' if five else 'Three'} DSA-heavy areas vs. Democrats + Republicans",
        fontsize=17,
        color="#625d53",
    )
    map_box = (0.08, 0.365, 0.84, 0.445) if bottom else (0.035, 0.185, 0.605, 0.625)
    axis = fig.add_axes(map_box, facecolor=PAPER)
    palette = LinearSegmentedColormap.from_list(
        "combined_density", ["#b19cd9", "#e0d6c4", "#c2993e"]
    )
    bound = data["color_bound"]
    normalization = Normalize(-bound, bound, clip=True)
    axis.scatter(
        [point[1] for point in data["points"]],
        [point[2] for point in data["points"]],
        c=[combined_density_contrast(point) for point in data["points"]],
        cmap=palette,
        norm=normalization,
        s=4.5,
        alpha=1,
        linewidths=0,
        rasterized=True,
    )
    axis.set_xlim(data["limits"][0])
    axis.set_ylim(data["limits"][1])
    original_panel_ratio = (16 * 0.69) / (10 * 0.61)
    axis.set_aspect(
        (data["limits"][0][1] - data["limits"][0][0])
        / (data["limits"][1][1] - data["limits"][1][0])
        / original_panel_ratio
    )
    axis.set_axis_off()
    next_top = 0.805 if five else 0.77
    renderer = fig.canvas.get_renderer()
    for number, record in enumerate(selected, 1):
        axis.text(
            *record["anchor_coordinates"],
            str(number),
            fontsize=15,
            fontweight="bold",
            ha="center",
            va="center",
            bbox=dict(boxstyle="circle,pad=0.35", facecolor=PAPER, edgecolor=INK, linewidth=0.8),
            zorder=5,
        )
        x = 0.045 + (number - 1) * 0.312 if bottom else 0.655
        top = 0.29 if bottom else next_top
        title = (
            f"{number}  " + textwrap.fill(DISPLAY_LABELS[record["title"]].replace("\n", " "), 28)
            if bottom
            else f"{number}  {DISPLAY_LABELS[record['title']]}"
        )
        heading = fig.text(
            x,
            top,
            title,
            fontsize=20 if five else 18 if bottom else 21,
            fontweight="bold",
            va="top",
            linespacing=1.2,
        )
        ratio_top = (
            top
            - heading.get_window_extent(renderer).height / fig.bbox.height
            - 5 / (fig.get_figheight() * 72)
        )
        ratio = fig.text(
            x,
            ratio_top,
            f"{record['density_ratio']:.1f}\u00d7 the baseline density",
            fontsize=15 if bottom else 16.5,
            fontweight="bold",
            va="top",
            color="#8d6c25",
        )
        body_top = (
            ratio_top
            - ratio.get_window_extent(renderer).height / fig.bbox.height
            - 5 / (fig.get_figheight() * 72)
        )
        statement = fig.text(
            x,
            body_top,
            textwrap.fill(
                f"{record['source_date'][:4]} {record['document_type']} \u2014 {record['snippet']}",
                43 if bottom else 52,
            ),
            fontsize=13 if bottom else 15,
            va="top",
            linespacing=1.25,
            color=INK,
        )
        if not bottom:
            next_top = (
                body_top
                - statement.get_window_extent(renderer).height / fig.bbox.height
                - 12 / (fig.get_figheight() * 72)
            )
    legend_box = (0.25, 0.331, 0.5, 0.007) if bottom else (0.045, 0.138, 0.605, 0.007)
    color_axis = fig.add_axes(legend_box)
    bar = fig.colorbar(
        plt.cm.ScalarMappable(norm=normalization, cmap=palette),
        cax=color_axis,
        orientation="horizontal",
        ticks=[],
    )
    bar.outline.set_visible(False)
    fig.text(
        legend_box[0],
        legend_box[1] - 0.019,
        "Denser Democrat & Republican language",
        fontsize=11.5,
        va="top",
        color="#625d53",
    )
    fig.text(
        legend_box[0] + legend_box[2],
        legend_box[1] - 0.019,
        "Denser DSA language",
        fontsize=11.5,
        va="top",
        ha="right",
        color="#625d53",
    )
    fig.text(
        0.045,
        0.059,
        "Original embedding map \u00b7 equal-weight Democrat & Republican baseline "
        "\u00b7 numbered examples, not region boundaries",
        fontsize=10.5,
        color="#625d53",
    )
    fig.text(
        0.045,
        0.034,
        "Dated DSA statements are paraphrased. Language concentration is not policy agreement.",
        fontsize=10.5,
        color="#625d53",
    )
    fig.text(
        0.045,
        0.014,
        "Multipliers: bundle-balanced geometric mean density ratios at DSA claims, "
        "not attention shares.",
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
        "Five DSA-heavy issues vs. Democrats + Republicans",
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

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--variants-only",
        action="store_true",
        help="Render three source-backed draft options without replacing the published lead",
    )
    args = parser.parse_args()
    data = ROOT / "data/analysis/national_claims/full/topics"
    labels_path, shares_path = data / "topic_labels.json", data / "shares.csv"
    labels = json.loads(labels_path.read_text())
    with shares_path.open(newline="") as handle:
        records = rank_attention_gaps(labels, list(csv.DictReader(handle)))
    output = ROOT / "figures/article/dsa_vs_major_parties_attention_gaps.png"
    if not args.variants_only:
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
    if not args.variants_only:
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
    if args.variants_only:
        variants = snippet_records(records, claims)
        for name, layout in (
            ("a-map-five", "map-five"),
            ("b-map-bottom", "map-bottom"),
            ("c-map-three", "map-three"),
        ):
            output = ROOT / f"figures/article/dsa_lead_option_{name}.png"
            render_variant(density, variants, output, layout)
            metadata = dict(
                article_only=True,
                draft_option=layout,
                ranking=(
                    "largest positive source-balanced mean "
                    "combined log density contrast at DSA claims"
                ),
                contrast="log p(DSA) - log((p(Democratic) + p(Republican)) / 2)",
                density_ratio_basis=(
                    "exp(bundle-balanced mean log density contrast at DSA claims); "
                    "geometric mean density ratio, not attention share"
                ),
                presentation="original embedding map with dated central DSA paraphrases",
                map_claims=len(density["points"]),
                map_limits=density["limits"],
                color_bound=density["color_bound"],
                color_palette=["#b19cd9", "#e0d6c4", "#c2993e"],
                map_points_sha256=hashlib.sha256(
                    json.dumps(density["points"], separators=(",", ":")).encode()
                ).hexdigest(),
                weighting="equal DSA bundle mass, equal eligible claim mass within each bundle",
                topics=variants if layout == "map-five" else variants[:3],
                source_lead_sha256=hashlib.sha256(
                    (ROOT / "figures/article/dsa_vs_major_parties_lead.json").read_bytes()
                ).hexdigest(),
                image_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
            )
            output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
            print(output)
        return
    output = ROOT / "figures/article/dsa_vs_major_parties_lead.png"
    render_variant(density, snippet_records(records, claims), output, "map-five")
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
        presentation="original embedding map with five dated central DSA paraphrases",
        snippets=snippet_records(records, claims),
        ranking="largest positive source-balanced mean combined log density contrast at DSA claims",
        contrast="log p(DSA) - log((p(Democratic) + p(Republican)) / 2)",
        density_ratio_basis=(
            "exp(bundle-balanced mean log density contrast at DSA claims); "
            "geometric mean density ratio, not attention share"
        ),
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
        color_palette=["#b19cd9", "#e0d6c4", "#c2993e"],
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
