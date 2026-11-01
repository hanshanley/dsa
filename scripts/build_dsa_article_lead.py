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
    "Labor Rights, Unionization, and Worker Protections": "Labor & unions",
    "Voting Rights, Election Rules, and Representation": "Voting & elections",
    "Economic Hardship, Poverty, and Housing Insecurity": "Poverty & housing\ninsecurity",
}
CURRENT_PROGRAM = "dsa-2026-program"
CURRENT_PROGRAM_SHA256 = "d32e0662f983d42ace583b3804ab0b3cc9ca31d4a49926c08ab562d7c9cf45fb"
CURRENT_SNIPPET_CLAIMS = {
    "topic-020": "dsa-2026-program-normalized-40060dd6f6dd-repair-d40710b9eecc-007",
    "topic-022": "dsa-2026-program-normalized-40060dd6f6dd-010",
    "topic-003": "dsa-2026-program-normalized-f85f1b0f20e0-004",
    "topic-005": "dsa-2026-program-normalized-d326f1020c4f-repair-94c56feee2ed-006",
    "topic-019": "dsa-2026-program-normalized-3ba469ba4e69-011",
}
SNIPPETS = {
    CURRENT_SNIPPET_CLAIMS["topic-020"]: (
        "DSA calls for ending ICE detention and deportations, amnesty for immigrants "
        "regardless of status, and a path to citizenship for permanent residents."
    ),
    CURRENT_SNIPPET_CLAIMS["topic-022"]: (
        "DSA calls for ending military and economic aid to Israel and Palestinian "
        "self-determination in a free Palestine with Jerusalem as its capital."
    ),
    CURRENT_SNIPPET_CLAIMS["topic-003"]: (
        "DSA calls for protecting every worker's right to unionize and strike, "
        "in every industry, and backing members who organize to democratize their unions."
    ),
    CURRENT_SNIPPET_CLAIMS["topic-005"]: (
        "DSA calls for proportional representation and ranked-choice voting in all "
        "elections, expanding the House and abolishing the Senate."
    ),
    CURRENT_SNIPPET_CLAIMS["topic-019"]: (
        "DSA calls for new publicly owned social housing, universal rent control "
        "and guaranteed legal counsel for every tenant."
    ),
}
SNIPPET_CLAIM_SHA256 = {
    CURRENT_SNIPPET_CLAIMS["topic-020"]: (
        "7272037af02dcbb6cfeda826496b4caf0a7819d01888e5a36684642355f5cce6"
    ),
    CURRENT_SNIPPET_CLAIMS["topic-022"]: (
        "796836cea12f6afb62de353831a884b2cd2328dc92aa4720859aba65f5c94781"
    ),
    CURRENT_SNIPPET_CLAIMS["topic-003"]: (
        "2048ab20154644381130fa08384ec4d998bcf9e70ab112518601d8e4ade58fca"
    ),
    CURRENT_SNIPPET_CLAIMS["topic-005"]: (
        "56daa564d0efdc2427ee3c4e21a269a5e0118ae027a08bf9cd8dbc23572e556d"
    ),
    CURRENT_SNIPPET_CLAIMS["topic-019"]: (
        "9b20c1fe3c4416e746790ecec8e2f0aaa7eef50065d45751ac9f9cda5520b2c1"
    ),
}
SNIPPET_EVIDENCE_SHA256 = {
    CURRENT_SNIPPET_CLAIMS["topic-020"]: (
        "f36ca0d1521d31258fb2d3fdc6d6e17042b4888b8c58f66aafcd7695e273d7cf"
    ),
    CURRENT_SNIPPET_CLAIMS["topic-022"]: (
        "f36ca0d1521d31258fb2d3fdc6d6e17042b4888b8c58f66aafcd7695e273d7cf"
    ),
    CURRENT_SNIPPET_CLAIMS["topic-003"]: (
        "ad95644e6821595473dd78c1b5ac16bb23f501991ed7329d4b6a8cde82b3faa2"
    ),
    CURRENT_SNIPPET_CLAIMS["topic-005"]: (
        "08ff669e10b8430aacb68743740269ab0e0e504d32dd34a5180bceb16384a717"
    ),
    CURRENT_SNIPPET_CLAIMS["topic-019"]: (
        "2c6195d6247207ca392f887cfbae949a4186b9ac73a22b600e92e2b988bb1343"
    ),
}


def snippet_records(records: list[dict], claims: list[dict], data: dict) -> list[dict]:
    lookup = {claim["claim_id"]: claim for claim in claims}
    points = {point[0]: point for point in data["points"]}
    result = []
    for record in records:
        claim_id = CURRENT_SNIPPET_CLAIMS.get(record["topic_id"])
        if claim_id not in lookup or claim_id not in points:
            raise ValueError("Article issue requires a preserved current-program claim")
        claim, point = lookup[claim_id], points[claim_id]
        if claim["group"] != "dsa" or claim["analysis_eligible"] != "True":
            raise ValueError("Article snippets require eligible DSA program claims")
        if (
            claim["document_id"] != CURRENT_PROGRAM
            or claim["document_type"] != "program"
            or claim["publication_date"] != "2026-09"
            or claim["source_sha256"] != CURRENT_PROGRAM_SHA256
        ):
            raise ValueError("Changed program source requires a new source-bound paraphrase")
        if data["groups"][point[4]] != "dsa":
            raise ValueError("Current-program policy must belong to DSA")
        if (
            hashlib.sha256(claim["claim_text"].encode()).hexdigest()
            != SNIPPET_CLAIM_SHA256[claim["claim_id"]]
        ):
            raise ValueError("Changed claim text requires a new source-bound paraphrase")
        if (
            hashlib.sha256(claim["evidence"].encode()).hexdigest()
            != SNIPPET_EVIDENCE_SHA256[claim_id]
        ):
            raise ValueError("Changed program evidence requires a new source-bound paraphrase")
        result.append(
            {
                **record,
                "anchor_scope": "central historical issue example, not the current policy passage",
                "policy_source_claim_id": claim_id,
                "policy_source_topic_id": data["topics"][point[3]]["topic_id"],
                "policy_source_coordinates": point[1:3],
                "source_url": claim["source_url"],
                "snippet": SNIPPETS[claim_id],
                "snippet_basis": (
                    "assistant paraphrase of the source-bound September 2026 national "
                    "program passage; historical map anchors and topic assignments unchanged"
                ),
                "source_claim_text": claim["claim_text"],
                "source_evidence": claim["evidence"],
                "source_sha256": claim["source_sha256"],
                "document_id": claim["document_id"],
                "document_title": claim["title"],
                "document_type": claim["document_type"],
                "source_date": claim["publication_date"],
            }
        )
    return result


def render_variant(data: dict, records: list[dict], output: Path, layout: str) -> None:
    import textwrap

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    from matplotlib.lines import Line2D

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
        f"{'Five' if five else 'Three'} issues with higher DSA attention shares",
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
    if not bottom:
        fig.text(0.655, 0.950, "POLICY ATTENTION SHARES", fontsize=11, color="#625d53")
    next_top = 0.918
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
            (
                top
                - heading.get_window_extent(renderer).height / fig.bbox.height
                - 5 / (fig.get_figheight() * 72)
            )
            if bottom
            else top
        )
        ratio = fig.text(
            x if bottom else 0.955,
            ratio_top,
            f"{record['attention_ratio']:.1f}\u00d7"
            if record["attention_ratio"] is not None
            else "n/a",
            fontsize=15 if bottom else 25,
            fontweight="bold",
            va="top",
            ha="left" if bottom else "right",
            color="#8d6c25",
        )
        if bottom:
            comparison_top = (
                ratio_top
                - ratio.get_window_extent(renderer).height / fig.bbox.height
                - 5 / (fig.get_figheight() * 72)
            )
        else:
            comparison_top = (
                top
                - max(
                    heading.get_window_extent(renderer).height,
                    ratio.get_window_extent(renderer).height,
                )
                / fig.bbox.height
                - 7 / (fig.get_figheight() * 72)
            )
        comparison = fig.text(
            x,
            comparison_top,
            f"DSA {100 * record['shares']['dsa']:.2f}%  \u00b7  "
            f"Democrat & Republican {100 * record['combined_share']:.2f}%",
            fontsize=13.5,
            va="top",
            color="#8d6c25",
        )
        source_top = (
            comparison_top
            - comparison.get_window_extent(renderer).height / fig.bbox.height
            - 5 / (fig.get_figheight() * 72)
        )
        if bottom:
            body_top = source_top
            body = (
                f"{record['source_date'][:4]} {record['document_type']} \u2014 {record['snippet']}"
            )
        else:
            source = fig.text(
                x,
                source_top,
                f"{record['source_date'][:4]} {record['document_type']}",
                fontsize=11.5,
                va="top",
                color="#625d53",
            )
            body_top = (
                source_top
                - source.get_window_extent(renderer).height / fig.bbox.height
                - 5 / (fig.get_figheight() * 72)
            )
            body = record["snippet"]
        statement = fig.text(
            x,
            body_top,
            textwrap.fill(body, 43 if bottom else 49),
            fontsize=13 if bottom else 16.5,
            va="top",
            linespacing=1.25,
            color=INK,
        )
        if not bottom:
            statement_bottom = (
                body_top - statement.get_window_extent(renderer).height / fig.bbox.height
            )
            next_top = statement_bottom - 22 / (fig.get_figheight() * 72)
            if number < len(selected):
                divider_y = statement_bottom - 10 / (fig.get_figheight() * 72)
                fig.add_artist(
                    Line2D(
                        [x, 0.955],
                        [divider_y, divider_y],
                        transform=fig.transFigure,
                        color="#d7d1c5",
                        linewidth=0.6,
                    )
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
        "Original embedding map: colors show language density, not attention shares; "
        "numbers locate historical issue examples.",
        fontsize=10.5,
        color="#625d53",
    )
    fig.text(
        0.045,
        0.034,
        "Statements: DSA's September 2026 program, paraphrased. "
        "Attention shares: bundle-balanced claims across 2000\u20132026.",
        fontsize=10.5,
        color="#625d53",
    )
    fig.text(
        0.045,
        0.014,
        "Multipliers: DSA attention share / the equal-weight Democrat & Republican "
        "average; not policy agreement.",
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


def attention_share_records(labels: list[dict], rows: list[dict]) -> list[dict]:
    shares = {}
    for row in rows:
        if row["view"] != "expanded" or row["available"] != "True":
            continue
        key = row["topic_id"], row["group"]
        value = float(row["share"])
        if key in shares or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Invalid or duplicate observed attention share")
        shares[key] = value
    result = []
    for label in labels:
        topic_id = label["topic_id"]
        if any((topic_id, group) not in shares for group in GROUPS):
            raise ValueError(f"Missing observed party shares for {topic_id}")
        values = {group: shares[topic_id, group] for group in GROUPS}
        combined = (values["democratic"] + values["republican"]) / 2
        result.append(
            dict(
                topic_id=topic_id,
                title=label["title"],
                displayed=label.get("displayed", True),
                shares=values,
                combined_share=combined,
                gap=values["dsa"] - combined,
                attention_ratio=values["dsa"] / combined if combined else None,
                democratic_republican_ratio=(
                    values["democratic"] / values["republican"] if values["republican"] else None
                ),
                dsa_democratic_ratio=(
                    values["dsa"] / values["democratic"] if values["democratic"] else None
                ),
                dsa_republican_ratio=(
                    values["dsa"] / values["republican"] if values["republican"] else None
                ),
            )
        )
    return result


def rank_attention_areas(data: dict, claims: list[dict], rows: list[dict]) -> list[dict]:
    lookup = {claim["claim_id"]: claim for claim in claims}
    points = {point[0]: point for point in data["points"]}
    if (
        len(lookup) != len(claims)
        or len(points) != len(data["points"])
        or set(lookup) != set(points)
    ):
        raise ValueError("Attention examples require exact unique claim membership")
    for point in points.values():
        if data["groups"][point[4]] != lookup[point[0]]["group"]:
            raise ValueError("Attention example claim group mismatch")
    metrics = {r["topic_id"]: r for r in attention_share_records(data["topics"], rows)}
    bundles = {
        claim_id: claim.get("bundle_id") or claim.get("document_id")
        for claim_id, claim in lookup.items()
        if claim["group"] == "dsa"
    }
    if any(not bundle for bundle in bundles.values()):
        raise ValueError("Missing DSA source bundle")
    counts = Counter(bundles.values())
    dsa_group = data["groups"].index("dsa")
    ranked = []
    for index, topic in enumerate(data["topics"]):
        if not topic["displayed"]:
            continue
        topic_id = topic["topic_id"]
        if metrics[topic_id]["gap"] <= 0:
            continue
        members = [
            point for point in points.values() if point[3] == index and point[4] == dsa_group
        ]
        bundle_count = len({bundles[point[0]] for point in members})
        if bundle_count < 2:
            continue
        weights = [1 / counts[bundles[point[0]]] for point in members]
        mass = sum(weights)
        center = [
            sum(weight * point[column] for point, weight in zip(members, weights)) / mass
            for column in (1, 2)
        ]
        examples = [points[e["claim_id"]] for e in topic["examples"] if e["group"] == "dsa"]
        if not examples:
            raise ValueError(f"No reviewed DSA example for {topic_id}")
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
                **metrics[topic_id],
                dsa_claims=len(members),
                dsa_bundles=bundle_count,
                anchor_claim_id=anchor[0],
                anchor_coordinates=anchor[1:3],
                anchor_source_url=lookup[anchor[0]]["source_url"],
            )
        )
    return sorted(ranked, key=lambda record: (-record["gap"], record["topic_id"]))[:5]


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
        share_rows = list(csv.DictReader(handle))
    ratios_path = ROOT / "figures/article/dsa_attention_share_ratios.csv"
    ratios_path.parent.mkdir(parents=True, exist_ok=True)
    with ratios_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            lineterminator="\n",
            fieldnames=(
                "topic_id",
                "topic_title",
                "substantive_issue",
                "dsa_share_pct",
                "democratic_share_pct",
                "republican_share_pct",
                "democrat_republican_average_share_pct",
                "attention_gap_pp",
                "dsa_attention_share_ratio",
                "democratic_republican_attention_share_ratio",
                "dsa_democratic_attention_share_ratio",
                "dsa_republican_attention_share_ratio",
            ),
        )
        writer.writeheader()
        for record in sorted(
            attention_share_records(labels, share_rows),
            key=lambda r: (
                not r["displayed"],
                r["attention_ratio"] is None,
                -(r["attention_ratio"] or 0),
                r["topic_id"],
            ),
        ):
            writer.writerow(
                dict(
                    topic_id=record["topic_id"],
                    topic_title=record["title"],
                    substantive_issue=record["displayed"],
                    dsa_share_pct=100 * record["shares"]["dsa"],
                    democratic_share_pct=100 * record["shares"]["democratic"],
                    republican_share_pct=100 * record["shares"]["republican"],
                    democrat_republican_average_share_pct=100 * record["combined_share"],
                    attention_gap_pp=100 * record["gap"],
                    dsa_attention_share_ratio=record["attention_ratio"],
                    democratic_republican_attention_share_ratio=record[
                        "democratic_republican_ratio"
                    ],
                    dsa_democratic_attention_share_ratio=record["dsa_democratic_ratio"],
                    dsa_republican_attention_share_ratio=record["dsa_republican_ratio"],
                )
            )
    records = rank_attention_gaps(labels, share_rows)
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
    records = rank_attention_areas(density, claims, share_rows)
    if len(records) != 5:
        raise ValueError("The article lead requires five supported positive DSA attention gaps")
    if args.variants_only:
        variants = snippet_records(records, claims, density)
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
                    "largest positive weighted attention-share gap; "
                    "DSA minus equal-weight Democratic/Republican average"
                ),
                map_contrast="log p(DSA) - log((p(Democratic) + p(Republican)) / 2)",
                attention_ratio_basis=(
                    "DSA subject share / "
                    "((Democratic subject share + Republican subject share) / 2); "
                    "null when the baseline share is zero"
                ),
                presentation=(
                    "original density map with September 2026 national DSA policy paraphrases "
                    "and full-period attention-share comparisons"
                ),
                map_claims=len(density["points"]),
                map_limits=density["limits"],
                color_bound=density["color_bound"],
                color_palette=["#b19cd9", "#e0d6c4", "#c2993e"],
                map_points_sha256=hashlib.sha256(
                    json.dumps(density["points"], separators=(",", ":")).encode()
                ).hexdigest(),
                weighting=(
                    "equal bundle mass within each organization, "
                    "equal eligible claim mass within each bundle"
                ),
                shares_sha256=hashlib.sha256(shares_path.read_bytes()).hexdigest(),
                attention_share_ratios_csv=ratios_path.name,
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
    render_variant(density, snippet_records(records, claims, density), output, "map-five")
    inputs = [
        labels_path,
        shares_path,
        representatives_path,
        claims_path,
        full / "expanded/scored_passages.csv",
        full / "expanded/density_region_evidence.csv",
        data / "assignments.csv",
        data / "positions/group_positions.json",
    ]
    metadata = dict(
        article_only=True,
        attention_share_ratios_csv=ratios_path.name,
        presentation=(
            "original density map with five September 2026 DSA program paraphrases "
            "and full-period attention-share comparisons"
        ),
        snippets=snippet_records(records, claims, density),
        ranking=(
            "largest positive weighted attention-share gap; "
            "DSA minus equal-weight Democratic/Republican average"
        ),
        map_contrast="log p(DSA) - log((p(Democratic) + p(Republican)) / 2)",
        attention_ratio_basis=(
            "DSA subject share / ((Democratic subject share + Republican subject share) / 2); "
            "null when the baseline share is zero"
        ),
        weighting=(
            "equal bundle mass within each organization, "
            "equal eligible claim mass within each bundle"
        ),
        minimum_dsa_bundles=2,
        anchor_selection=(
            "reviewed DSA example nearest the bundle-balanced weighted 2D issue center; "
            "marker does not encode an attention share"
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
