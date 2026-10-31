"""Source-bound group positions on the frozen pooled claim taxonomy."""

from __future__ import annotations

import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from textwrap import fill

import numpy as np

from .national_platform_kde import LABELS
from .national_platforms import GROUPS, read_rows, write_json, write_rows

MAX_EXAMPLES = 48
SUMMARY_WORDS = 36
DIFFERENCE_WORDS = 30
QUALIFICATION = (
    "Source-bound assistant synthesis of bundle-diverse examples, not independent human "
    "certification or an exhaustive stance classification. Statements describe the "
    "observed documents across years, not every member's beliefs or a current consensus."
)
NO_POSITION = "No sampled claims; no group position inferred."
NO_DIFFERENCE = "Insufficient sampled evidence to compare group positions."


def select_examples(indices, rows, embeddings, centroid, limit=MAX_EXAMPLES):
    by_bundle = defaultdict(list)
    for index in indices:
        by_bundle[rows[index]["bundle_id"]].append(index)
    ranked = {}
    for bundle, members in sorted(by_bundle.items()):
        ordered = sorted(
            members,
            key=lambda index: (-float(embeddings[index] @ centroid), rows[index]["claim_id"]),
        )
        sequence = []
        while ordered:
            sequence.extend(ordered[:2])
            del ordered[:2]
            if ordered:
                sequence.append(ordered.pop())
        ranked[bundle] = sequence
    selected = []
    for offset in range(max((len(value) for value in ranked.values()), default=0)):
        for members in ranked.values():
            if offset < len(members):
                selected.append(members[offset])
                if len(selected) == limit:
                    return selected
    return selected


def prepare(corpus: Path) -> dict:
    from .national_claim_topics import (
        canonical,
        claim_weights,
        current_labels,
        digest,
        displayed_topics,
        load_inputs,
    )

    directory = corpus / "topics"
    fit_path = directory / "fit_manifest.json"
    fit = json.loads(fit_path.read_text())
    groups = tuple(fit["summary"]["groups"])
    rows, embeddings, basis = load_inputs(corpus, groups)
    if basis != fit["basis"]:
        raise ValueError("Position evidence requires the unchanged pooled fit")
    assignments = read_rows(directory / "assignments.csv")
    if [row["claim_id"] for row in rows] != [row["claim_id"] for row in assignments]:
        raise ValueError("Position assignment row order does not match claims")
    if any(
        digest((directory / name).read_bytes()) != expected
        for name, expected in fit["outputs"].items()
    ):
        raise ValueError("Position evidence requires intact fitted artifacts")
    labels = current_labels(directory)
    topics = sorted(displayed_topics(labels))
    weights = claim_weights(rows)
    target = directory / "positions"
    packets = target / "packets"
    packets.mkdir(parents=True, exist_ok=True)
    records = []
    packet_hashes = {}
    for topic in topics:
        members = [index for index, row in enumerate(assignments) if row["topic_id"] == topic]
        centroid = np.average(embeddings[members], axis=0, weights=weights[members])
        centroid /= max(float(np.linalg.norm(centroid)), 1e-12)
        packet = {
            "topic_id": topic,
            "title": labels[topic]["title"],
            "pooled_summary": labels[topic]["summary"],
            "pooled_caveat": labels[topic].get("caveat", ""),
            "groups": {},
            "qualification": QUALIFICATION,
        }
        for group in groups:
            indices = [index for index in members if rows[index]["group"] == group]
            selected = select_examples(indices, rows, embeddings, centroid)
            examples = []
            for index in selected:
                row = rows[index]
                fields = {
                    key: row.get(key, "")
                    for key in (
                        "claim_id",
                        "group",
                        "bundle_id",
                        "document_id",
                        "title",
                        "publication_date",
                        "adoption_date",
                        "source_url",
                        "source_sha256",
                        "locator",
                        "claim_types",
                    )
                }
                examples.append({**fields, "claim_text": row["text"], "strict": row["strict"]})
                records.append(
                    {
                        "topic_id": topic,
                        **fields,
                        "claim_text": row["text"],
                        "evidence": row["evidence"],
                        "source_start": row["source_start"],
                        "source_end": row["source_end"],
                        "strict": row["strict"],
                    }
                )
            packet["groups"][group] = {
                "claims": len(indices),
                "bundles": len({rows[index]["bundle_id"] for index in indices}),
                "documents": len({rows[index]["document_id"] for index in indices}),
                "examples": examples,
            }
        path = packets / f"{topic}.json"
        write_json(path, packet)
        packet_hashes[topic] = digest(path.read_bytes())
    write_rows(target / "evidence.csv", records)
    manifest = {
        "schema_version": 1,
        "fit_manifest_sha256": digest(fit_path.read_bytes()),
        "claims_sha256": basis["claims_sha256"],
        "groups": list(groups),
        "topics": topics,
        "view": "expanded",
        "selection": {
            "max_examples_per_group_topic": MAX_EXAMPLES,
            "method": (
                "Round-robin across bundles, alternating two claims nearest the frozen "
                "weighted topic centroid with one peripheral claim. No stance-based selection."
            ),
        },
        "packet_sha256": packet_hashes,
        "evidence_sha256": digest((target / "evidence.csv").read_bytes()),
        "qualification": QUALIFICATION,
    }
    write_json(target / "selection_manifest.json", manifest)
    return {
        "topics": len(topics),
        "examples": len(records),
        "basis_sha256": digest(canonical(manifest)),
    }


def reviewed_positions(corpus: Path) -> tuple[dict, list[dict]]:
    from .national_claim_topics import digest

    directory = corpus / "topics/positions"
    manifest = json.loads((directory / "selection_manifest.json").read_text())
    if (
        manifest["fit_manifest_sha256"]
        != digest((corpus / "topics/fit_manifest.json").read_bytes())
        or manifest["claims_sha256"] != digest((corpus / "claims.csv").read_bytes())
        or manifest["evidence_sha256"] != digest((directory / "evidence.csv").read_bytes())
    ):
        raise ValueError("Stale position evidence manifest")
    reviews = []
    groups = manifest["groups"]
    for topic in manifest["topics"]:
        packet_path = directory / "packets" / f"{topic}.json"
        expected = manifest["packet_sha256"][topic]
        if digest(packet_path.read_bytes()) != expected:
            raise ValueError(f"Position evidence packet changed: {topic}")
        packet = json.loads(packet_path.read_text())
        path = directory / "reviews" / f"{topic}.json"
        if not path.exists():
            raise ValueError(f"Missing source-bound position review: {topic}")
        review = json.loads(path.read_text())
        if (
            review["topic_id"] != topic
            or review["packet_sha256"] != expected
            or review["review_status"] != "evidence_reviewed"
            or review["review_origin"] != "assistant_source_bound_review"
            or set(review["groups"]) != set(groups)
        ):
            raise ValueError(f"Invalid position review: {topic}")
        for group in groups:
            statement = review["groups"][group]
            examples = packet["groups"][group]["examples"]
            lookup = {example["claim_id"]: example for example in examples}
            supporting = statement["supporting_claim_ids"]
            if (
                not statement["summary"].strip()
                or len(statement["summary"].split()) > SUMMARY_WORDS
                or not set(supporting) <= set(lookup)
                or (examples and not supporting)
                or (not examples and supporting)
                or (not examples and statement["summary"] != NO_POSITION)
                or len(statement.get("caveat", "").split()) > 24
            ):
                raise ValueError(f"Unsupported group position: {topic}/{group}")
            if (
                len({example["bundle_id"] for example in examples}) >= 2
                and len({lookup[claim]["bundle_id"] for claim in supporting}) < 2
            ):
                raise ValueError(f"Position needs multiple supporting bundles: {topic}/{group}")
        pairs = {f"{first}_vs_{second}" for first, second in combinations(groups, 2)}
        if set(review["pairs"]) != pairs:
            raise ValueError(f"Missing pairwise position differences: {topic}")
        for pair, difference in review["pairs"].items():
            first, second = pair.split("_vs_")
            ids = {
                example["claim_id"]: group
                for group in (first, second)
                for example in packet["groups"][group]["examples"]
            }
            supporting = difference["supporting_claim_ids"]
            observed = {group for group in (first, second) if packet["groups"][group]["examples"]}
            if (
                not difference["summary"].strip()
                or len(difference["summary"].split()) > DIFFERENCE_WORDS
                or not set(supporting) <= set(ids)
                or {ids[claim] for claim in supporting} != observed
                or (len(observed) != 2 and difference["summary"] != NO_DIFFERENCE)
            ):
                raise ValueError(f"Unsupported pairwise difference: {topic}/{pair}")
        reviews.append(review)
    return manifest, reviews


def map_markers(fig, axis, rows, topics, weights):
    occupied = []
    for number, topic in enumerate(topics, 1):
        indices = [index for index, row in enumerate(rows) if row["topic_id"] == topic]
        if not indices:
            continue
        point = tuple(
            np.average(
                [float(rows[index][key]) for index in indices],
                weights=weights[indices],
            )
            for key in ("umap_x", "umap_y")
        )
        candidates = [(0, 0)] + [
            (radius * np.cos(angle), radius * np.sin(angle))
            for radius in (16, 32, 48, 64, 80, 96)
            for angle in np.linspace(0, 2 * np.pi, 12, endpoint=False)
        ]
        for offset in candidates:
            label = axis.annotate(
                str(number),
                xy=point,
                xytext=offset,
                textcoords="offset points",
                ha="center",
                va="center",
                fontsize=9,
                weight="bold",
                bbox={"boxstyle": "circle,pad=0.25", "fc": "#F7F5F0", "ec": "#77736D"},
                arrowprops={"arrowstyle": "-", "color": "#77736D", "linewidth": 0.6},
            )
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            box = label.get_bbox_patch().get_window_extent(renderer)
            bounds = axis.get_window_extent(renderer)
            if (
                bounds.contains(box.x0, box.y0)
                and bounds.contains(box.x1, box.y1)
                and not any(box.overlaps(other) for other in occupied)
            ):
                occupied.append(box)
                break
            label.remove()
        else:
            raise ValueError(f"Cannot place nonoverlapping topic marker: {topic}")


def plot_atlases(rows, labels, reviews, shares, figures: Path, groups=GROUPS) -> list[str]:
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
    from matplotlib.lines import Line2D

    from .national_claim_plot_style import BG, COLORS, house_style, save_figure
    from .national_claim_topics import claim_weights

    house_style()
    topics = [review["topic_id"] for review in reviews]
    lookup = {review["topic_id"]: review for review in reviews}
    shares = {(row["group"], row["topic_id"]): row for row in shares if row["view"] == "expanded"}
    weights = claim_weights(rows)
    pairs = list(combinations(groups, 2))
    bound = (
        max(
            (
                abs(float(shares[first, topic]["share"]) - float(shares[second, topic]["share"]))
                * 100
                for first, second in pairs
                for topic in topics
            ),
            default=0,
        )
        or 1
    )
    destination = figures / "positions"
    destination.mkdir(parents=True, exist_ok=True)
    expected = ["all_groups"] + [f"{first}_vs_{second}" for first, second in pairs]
    for old in destination.glob("*"):
        if old.suffix in {".png", ".svg"} and old.stem not in expected:
            old.unlink()
    for pair in [None, *pairs]:
        columns = list(groups) if pair is None else [*pair, "difference"]
        texts = []
        for topic in topics:
            review = lookup[topic]
            texts.append(
                [
                    fill(
                        review["pairs"][f"{pair[0]}_vs_{pair[1]}"]["summary"]
                        if column == "difference"
                        else review["groups"][column]["summary"],
                        48,
                    )
                    for column in columns
                ]
            )
        row_heights = [
            max(1, 0.43 + max(text.count("\n") + 1 for text in cells) * 10 * 1.24 / 72)
            for cells in texts
        ]
        height = 9 + sum(row_heights)
        fig = plt.figure(figsize=(17, height))
        fig.set_gid("issue-card")
        title = (
            "Where the groups cluster - and what their documents say"
            if pair is None
            else f"{LABELS[pair[0]]} and {LABELS[pair[1]]}: the substantive differences"
        )
        fig.text(0.055, 1 - 0.55 / height, title, fontsize=22, weight="bold")
        fig.text(
            0.055,
            1 - 0.97 / height,
            f"Expanded national documents | {len(topics)} substantive pooled clusters | "
            "Group-specific, source-bound synthesis across observed years",
            fontsize=11,
            color="#6B6B6B",
        )
        axis = fig.add_axes((0.055, 1 - 6.4 / height, 0.49, 4.95 / height))
        selected_indices = [
            index
            for index, row in enumerate(rows)
            if row["topic_id"] in topics and (pair is None or row["group"] in pair)
        ]
        selected = [rows[index] for index in selected_indices]
        if pair is None:
            for group in groups:
                subset = [row for row in selected if row["group"] == group]
                axis.scatter(
                    [float(row["umap_x"]) for row in subset],
                    [float(row["umap_y"]) for row in subset],
                    s=5,
                    color=COLORS[group],
                    alpha=0.25,
                    linewidths=0,
                    rasterized=True,
                    label=LABELS[group],
                )
            axis.legend(
                loc="upper left",
                frameon=False,
                fontsize=10,
                markerscale=2,
                ncol=len(groups),
            )
        else:
            gaps = {
                topic: (
                    float(shares[pair[0], topic]["share"]) - float(shares[pair[1], topic]["share"])
                )
                * 100
                for topic in topics
            }
            image = axis.scatter(
                [float(row["umap_x"]) for row in selected],
                [float(row["umap_y"]) for row in selected],
                c=[gaps[row["topic_id"]] for row in selected],
                cmap=LinearSegmentedColormap.from_list(
                    "topic_gap", [COLORS[pair[1]], BG, COLORS[pair[0]]]
                ),
                norm=TwoSlopeNorm(vmin=-bound, vcenter=0, vmax=bound),
                s=5,
                alpha=0.4,
                linewidths=0,
                rasterized=True,
            )
            bar = fig.colorbar(
                image,
                cax=fig.add_axes((0.08, 1 - 6.72 / height, 0.44, 0.12 / height)),
                orientation="horizontal",
            )
            bar.ax.tick_params(labelsize=8)
            bar.set_label(
                f"Topic-share gap, percentage points: {LABELS[pair[0]]} minus {LABELS[pair[1]]}",
                fontsize=8,
            )
        for key, setter in (("umap_x", axis.set_xlim), ("umap_y", axis.set_ylim)):
            coordinates = np.array([float(row[key]) for row in rows])
            pad = max(float(np.ptp(coordinates)) * 0.07, 1e-6)
            setter(float(coordinates.min()) - pad, float(coordinates.max()) + pad)
        axis.set_axis_off()
        map_markers(fig, axis, selected, topics, weights[selected_indices])
        fig.text(0.59, 1 - 1.55 / height, "The numbered topics", fontsize=12, weight="bold")
        split = (len(topics) + 1) // 2
        for index, topic in enumerate(topics):
            column, offset = divmod(index, split)
            fig.text(
                0.59 + column * 0.19,
                1 - (1.95 + offset * 0.44) / height,
                fill(f"{index + 1}. {labels[topic]['title']}", 33),
                fontsize=8.5,
                va="top",
                linespacing=1.05,
            )
        table_top = height - 7.8
        starts = (0.28, 0.51, 0.74)
        fig.text(0.055, (table_top + 0.3) / height, "Topic", fontsize=11, weight="bold")
        for x, column in zip(starts, columns):
            fig.text(
                x,
                (table_top + 0.3) / height,
                "Documented distinction" if column == "difference" else LABELS[column],
                fontsize=11,
                weight="bold",
                color="#1A1A1A" if column == "difference" else COLORS[column],
            )
        y = table_top
        for number, (topic, cells, row_height) in enumerate(
            zip(topics, texts, row_heights, strict=True), 1
        ):
            fig.text(
                0.055,
                y / height,
                fill(f"{number}. {labels[topic]['title']}", 29),
                fontsize=10,
                weight="bold",
                va="top",
            )
            for x, column, text in zip(starts, columns, cells, strict=True):
                if column == "difference":
                    gap = (
                        float(shares[pair[0], topic]["share"])
                        - float(shares[pair[1], topic]["share"])
                    ) * 100
                    detail = f"{gap:+.1f} percentage points"
                    color = COLORS[pair[0] if gap >= 0 else pair[1]]
                else:
                    support = shares[column, topic]
                    caution = "*" if lookup[topic]["groups"][column].get("caveat") else ""
                    detail = (
                        f"{float(support['share']):.1%} | {support['claims']} claims | "
                        f"{support['bundles']} bundles{caution}"
                    )
                    color = COLORS[column]
                fig.text(x, y / height, detail, fontsize=8.5, color=color, va="top")
                fig.text(
                    x,
                    (y - 0.23) / height,
                    text,
                    fontsize=10,
                    va="top",
                    linespacing=1.24,
                )
            y -= row_height
            fig.add_artist(
                Line2D(
                    [0.055, 0.955],
                    [(y + 0.14) / height] * 2,
                    transform=fig.transFigure,
                    color="#D6D3CC",
                    linewidth=0.5,
                )
            )
        fig.text(
            0.055,
            0.72 / height,
            "Numbers locate weighted topic centres in a reused 2D display, not cluster boundaries. "
            "Clusters were fitted in higher-dimensional embeddings.",
            fontsize=9,
            color="#6B6B6B",
        )
        fig.text(
            0.055,
            0.48 / height,
            "Dots are claims; shares use equal document / fallback-bundle weights. "
            "Identity clusters are omitted without renormalizing. "
            "* Cell-specific cautions are in the source-linked review.",
            fontsize=9,
            color="#6B6B6B",
        )
        note = fig.text(
            0.055,
            0.24 / height,
            "THE MARGIN OF ERROR | Sampled source-bound assistant synthesis, "
            "not exhaustive beliefs "
            "or a current consensus. Map emphasis is not policy agreement.",
            fontsize=9,
            color="#6B6B6B",
        )
        note.set_gid("source-note")
        stem = "all_groups" if pair is None else f"{pair[0]}_vs_{pair[1]}"
        save_figure(fig, destination / stem, svg_dpi=100)
        plt.close(fig)
    return expected


def generate(corpus: Path, figures: Path) -> dict:
    from .national_claim_topics import digest

    directory = corpus / "topics/positions"
    if not (directory / "selection_manifest.json").exists():
        return {"status": "not_prepared"}
    manifest, reviews = reviewed_positions(corpus)
    assignments = {row["claim_id"]: row for row in read_rows(corpus / "topics/assignments.csv")}
    rows = read_rows(corpus / "expanded/scored_passages.csv")
    if len(rows) != len(assignments) or {row["claim_id"] for row in rows} != set(assignments):
        raise ValueError("Position atlas coordinates do not cover the frozen claim assignments")
    for row in rows:
        assignment = assignments[row["claim_id"]]
        if (
            row["group"] != assignment["group"]
            or digest(row["text"]) != assignment["text_sha256"]
            or not all(np.isfinite(float(row[key])) for key in ("umap_x", "umap_y"))
        ):
            raise ValueError(f"Position display provenance mismatch: {row['claim_id']}")
        row["topic_id"] = assignment["topic_id"]
    labels = {
        row["topic_id"]: row
        for row in json.loads((corpus / "topics/topic_labels.json").read_text())
    }
    stems = plot_atlases(
        rows,
        labels,
        reviews,
        read_rows(corpus / "topics/shares.csv"),
        figures,
        groups=tuple(manifest["groups"]),
    )
    write_json(directory / "group_positions.json", reviews)
    result = {
        "status": "complete",
        "view": "expanded",
        "topics": len(reviews),
        "group_positions": len(reviews) * len(manifest["groups"]),
        "pairwise_differences": len(reviews) * len(list(combinations(manifest["groups"], 2))),
        "figures": stems,
        "selection_manifest_sha256": digest((directory / "selection_manifest.json").read_bytes()),
        "coordinates_sha256": digest((corpus / "expanded/scored_passages.csv").read_bytes()),
        "qualification": QUALIFICATION,
    }
    write_json(directory / "summary.json", result)
    return result


def report_section(corpus: Path, figures: Path) -> str:
    directory = corpus / "topics/positions"
    if not (directory / "summary.json").exists():
        return ""
    manifest, reviews = reviewed_positions(corpus)
    evidence = {row["claim_id"]: row for row in read_rows(directory / "evidence.csv")}
    labels = {
        row["topic_id"]: row["title"]
        for row in json.loads((corpus / "topics/topic_labels.json").read_text())
    }
    lines = [
        "### Cluster maps with individualized group positions",
        "",
        "One large atlas combines all three groups; three further atlases compare each pair. "
        "Each shows all 21 substantive pooled clusters, with separately reviewed position "
        "summaries and explicit documented differences. These use the expanded corpus only. "
        "The frozen clusters are projected onto the saved expanded display, not refitted in 2D.",
        "",
        "The combined map colors claims by organization. Pairwise map colors show the "
        "unsmoothed weighted **topic-share gap**, not KDE density or policy distance. "
        "Numbered markers locate weighted projected topic centres, not boundaries. "
        "All original denominators and all 24 assignments remain in downloads.",
        "",
        f"**Review scope:** {QUALIFICATION} The packet selection cycles across bundles, "
        "including central and peripheral claims; it is not a random sample or exhaustive "
        "coding of all within-topic policy positions. Contradictions and scope cautions "
        "are retained below. Read the sources before describing a present-day group belief.",
        "",
    ]
    for stem, heading in [
        ("all_groups", "All three groups"),
        *[
            (f"{a}_vs_{b}", f"{LABELS[a]} and {LABELS[b]}")
            for a, b in combinations(manifest["groups"], 2)
        ],
    ]:
        relative = f"../figures/national_claims/{corpus.name}/topics/positions/{stem}"
        lines += [
            f"**{heading}**",
            "",
            f"![{heading}: clusters and stated positions]({relative}.png)",
            "",
            f"[Full-resolution PNG]({relative}.png) / [Vector SVG]({relative}.svg)",
            "",
        ]
    relative_data = f"../data/analysis/national_claims/{corpus.name}/topics/positions"
    lines += [
        f"[Full position review]({relative_data}/group_positions.json) / "
        f"[All sampled claims and source evidence]({relative_data}/evidence.csv)",
        "",
    ]
    for number, review in enumerate(reviews, 1):
        lines += [f"#### Position cluster {number}: {labels[review['topic_id']]}", ""]
        for group in manifest["groups"]:
            position = review["groups"][group]
            lines.append(f"**{LABELS[group]}:** {position['summary']}")
            if position.get("caveat"):
                lines.append(f"Scope caution: {position['caveat']}")
            for claim in position["supporting_claim_ids"]:
                row = evidence[claim]
                text = row["claim_text"].replace("|", "\\|")
                lines.append(
                    f"- {text} ([{row['title']}]({row['source_url']}); "
                    f"{row['publication_date']}; {row['locator']}; `{claim}`)"
                )
            lines.append("")
        lines.append("**Pairwise distinctions:**")
        for pair, difference in review["pairs"].items():
            first, second = pair.split("_vs_")
            lines.append(f"- {LABELS[first]} / {LABELS[second]}: {difference['summary']}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    import argparse

    from .national_claim_corpus import FULL_OUTPUT
    from .national_claim_topics import render

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "render"))
    parser.add_argument("--input", type=Path, default=FULL_OUTPUT)
    args = parser.parse_args()
    result = prepare(args.input) if args.action == "prepare" else render(args.input)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
