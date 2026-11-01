"""Publish reviewed caucus results without touching national-party figures."""

from __future__ import annotations

import json
import textwrap
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
from dsa_caucus_analysis import CLAIMS, CORPUS, RESULTS, ROOT

from dsa_analysis.national_platforms import digest, read_rows, write_json

BACKGROUNDS = {"substack": "#F5F5F5", "margin-of-error": "#F7F5F0"}
MAJOR_GROUPS = (
    "socialist-majority",
    "groundwork",
    "emerge",
    "marxist-unity",
    "springs-of-revolution",
    "bread-and-roses",
)


def review_basis(summary: dict) -> str:
    return digest(
        json.dumps(
            {"inputs": summary["input_hashes"], "results": summary["result_hashes"]},
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def validated_labels(summary: dict, review: dict, examples: list[dict]) -> dict:
    if review.get("basis_hash") != review_basis(summary):
        raise ValueError("Reviewed labels do not match current numerical inputs")
    evidence = defaultdict(set)
    for row in examples:
        evidence[row["topic_id"]].add(row["claim_id"])
    labels = review.get("topics", {})
    if set(labels) != set(evidence):
        raise ValueError("Every current learned topic requires source-reviewed labels")
    for topic, label in labels.items():
        support = label.get("supporting_claim_ids", [])
        if (
            not label.get("title")
            or not label.get("summary")
            or len(set(support)) < 2
            or set(support) - evidence[topic]
        ):
            raise ValueError(f"Unsupported topic label: {topic}")
    return labels


def make_figures(
    output: Path,
    background: str,
    labels: dict,
    shares: list[dict],
    ratios: list[dict],
    organizations: dict[str, str],
    densities: list[dict],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
    from scipy.special import logsumexp

    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "text.color": "#343434",
            "axes.labelcolor": "#343434",
            "axes.edgecolor": "#bbbbbb",
            "figure.facecolor": background,
            "axes.facecolor": background,
            "savefig.facecolor": background,
        }
    )
    groups = sorted(organizations, key=lambda group: organizations[group])
    topics = sorted(labels, key=lambda topic: labels[topic]["title"])
    values = {(row["group"], row["topic_id"]): float(row["attention_share"]) for row in shares}
    matrix = np.array([[values[group, topic] for group in groups] for topic in topics])
    cmap = LinearSegmentedColormap.from_list("attention", [background, "#b79a61"])
    figure, axis = plt.subplots(figsize=(16, max(8.5, len(topics) * 0.52 + 1.6)))
    axis.imshow(matrix, cmap=cmap, vmin=0, vmax=max(float(matrix.max()), 0.01), aspect="auto")
    axis.set_xticks(
        range(len(groups)), [textwrap.fill(organizations[group], 14) for group in groups]
    )
    axis.xaxis.tick_top()
    axis.tick_params(axis="both", length=0, pad=10)
    axis.tick_params(axis="x", labelsize=9)
    axis.set_yticks(
        range(len(topics)), [textwrap.fill(labels[topic]["title"], 29) for topic in topics]
    )
    for row in range(len(topics)):
        for column in range(len(groups)):
            axis.text(column, row, f"{matrix[row, column]:.1%}", ha="center", va="center")
    for spine in axis.spines.values():
        spine.set_visible(False)
    figure.suptitle("What DSA caucuses give attention to", x=0.03, ha="left", fontsize=20)
    figure.text(
        0.03,
        0.025,
        "Share of document-balanced claims in each issue. "
        "Unclustered claims remain in denominators.\n"
        "One flagship statement per caucus/network; "
        "not membership, policy agreement or a timeline.",
        fontsize=10,
    )
    figure.tight_layout(rect=(0, 0.07, 1, 0.92))
    figure.savefig(output / "caucus-attention-shares.png", dpi=160)
    plt.close(figure)

    for topic in topics:
        ordered = sorted(groups, key=lambda group: (-values[group, topic], organizations[group]))
        indexed = {
            row["group"]: row
            for row in ratios
            if row["topic_id"] == topic and row["comparison"] == "equal_caucus_rest"
        }
        figure, axis = plt.subplots(figsize=(11, 7))
        axis.barh(
            range(len(ordered)),
            [100 * values[group, topic] for group in ordered],
            color="#a68b56",
            height=0.6,
        )
        axis.set_yticks(range(len(ordered)), [organizations[group] for group in ordered])
        axis.invert_yaxis()
        axis.set_xlim(0, max(5, max(values[group, topic] for group in groups) * 140))
        axis.set_xlabel("Attention share (%)")
        axis.set_title(labels[topic]["title"], loc="left", fontsize=17, pad=16)
        for index, group in enumerate(ordered):
            ratio = indexed[group]["attention_share_ratio"]
            multiplier = f"{float(ratio):.1f}×" if ratio != "" else "undefined"
            axis.text(
                100 * values[group, topic] + 0.4,
                index,
                f"{values[group, topic]:.1%} · {multiplier}",
                va="center",
                fontsize=10,
            )
        axis.spines[["top", "right", "left"]].set_visible(False)
        axis.tick_params(axis="y", length=0)
        figure.text(
            0.03,
            0.025,
            f"Multipliers compare with the equal-weight average of the other "
            f"{len(groups) - 1} caucuses/networks.\n"
            "Ratios use unrounded shares; zero denominator = undefined. Single-document snapshot.",
            fontsize=9,
        )
        figure.tight_layout(rect=(0, 0.08, 1, 1))
        figure.savefig(output / f"{topic}-attention.png", dpi=160)
        plt.close(figure)
        pairs = {
            (row["group"], row["baseline_groups"]): row["attention_share_ratio"]
            for row in ratios
            if row["topic_id"] == topic and row["comparison"] == "pairwise"
        }
        colors = np.full((len(groups), len(groups)), np.nan)
        for row, first in enumerate(groups):
            for column, second in enumerate(groups):
                ratio = pairs.get((first, second), "")
                if ratio != "":
                    colors[row, column] = np.log2(max(float(ratio), 1 / 16))
        ratio_cmap = LinearSegmentedColormap.from_list(
            "attention-ratio", ["#817395", background, "#af8e45"]
        )
        figure, axis = plt.subplots(figsize=(13, 11))
        axis.imshow(
            np.ma.masked_invalid(colors),
            cmap=ratio_cmap,
            norm=TwoSlopeNorm(vmin=-4, vcenter=0, vmax=4),
        )
        axis.set_xticks(
            range(len(groups)),
            [organizations[group] for group in groups],
            rotation=55,
            ha="right",
            rotation_mode="anchor",
        )
        axis.tick_params(axis="x", labelsize=8, length=0, pad=8)
        axis.set_yticks(range(len(groups)), [organizations[group] for group in groups])
        axis.tick_params(axis="y", labelsize=10, length=0, pad=8)
        for row, first in enumerate(groups):
            for column, second in enumerate(groups):
                if first == second:
                    continue
                ratio = pairs[first, second]
                text = f"{float(ratio):.2g}×" if ratio != "" else "—"
                axis.text(column, row, text, ha="center", va="center", fontsize=9)
        axis.set_xlabel("Denominator caucus/network", labelpad=15)
        axis.set_title(labels[topic]["title"] + ": all attention ratios", loc="left", pad=18)
        for spine in axis.spines.values():
            spine.set_visible(False)
        figure.text(
            0.03,
            0.025,
            "Each cell = row attention share / column attention share. — = undefined "
            "(zero denominator); diagonal omitted.\n"
            "Gold = higher row share, purple = lower; color clips at 16× and 1/16×. "
            "Printed values and CSV use unsmoothed ratios.",
            fontsize=9,
        )
        figure.tight_layout(rect=(0, 0.07, 1, 1))
        figure.savefig(output / f"{topic}-all-ratios.png", dpi=160)
        plt.close(figure)

    if densities:
        coordinates = np.array([[float(row["umap_x"]), float(row["umap_y"])] for row in densities])
        log_density = np.array(
            [[float(row[f"{group}_log_density"]) for group in groups] for row in densities]
        )
        contrasts = np.column_stack(
            [
                log_density[:, index]
                - (
                    logsumexp(np.delete(log_density, index, axis=1), axis=1)
                    - np.log(len(groups) - 1)
                )
                for index in range(len(groups))
            ]
        )
        cap = max(float(np.quantile(np.abs(contrasts), 0.95)), 1e-6)
        contrast_cmap = LinearSegmentedColormap.from_list(
            "caucus-density", ["#786895", background, "#af8e45"]
        )
        figure, axes = plt.subplots(3, 2, figsize=(13, 12), sharex=True, sharey=True)
        for axis, group in zip(axes.ravel(), MAJOR_GROUPS, strict=True):
            index = groups.index(group)
            image = axis.scatter(
                coordinates[:, 0],
                coordinates[:, 1],
                c=contrasts[:, index],
                s=6,
                cmap=contrast_cmap,
                norm=TwoSlopeNorm(vmin=-cap, vcenter=0, vmax=cap),
                linewidths=0,
                rasterized=True,
            )
            axis.set_title(organizations[group], loc="left", fontsize=13)
            axis.set_xticks([])
            axis.set_yticks([])
            for spine in axis.spines.values():
                spine.set_visible(False)
        figure.suptitle("Selected DSA caucuses and networks", x=0.05, ha="left", fontsize=19)
        figure.subplots_adjust(left=0.05, right=0.90, bottom=0.10, top=0.93, hspace=0.12)
        color_axis = figure.add_axes((0.92, 0.20, 0.015, 0.60))
        figure.colorbar(image, cax=color_axis).set_label(
            "Log density contrast: purple = other caucuses; gold = named group", labelpad=12
        )
        figure.text(
            0.05,
            0.025,
            f"Each group versus the equal-density average of all {len(groups) - 1} others, "
            "in one common map.\n"
            "Density is fitted in higher-dimensional space; the 2D map is display only. "
            "Language density is not agreement.",
            fontsize=10,
        )
        figure.savefig(output / "major-caucus-language-density.png", dpi=160)
        plt.close(figure)


def publish() -> dict:
    summary = json.loads((RESULTS / "summary.json").read_text())
    for name, path in (
        ("claims", CLAIMS / "claims.csv"),
        ("sources", CORPUS / "complete_sources.csv"),
        ("embeddings", RESULTS / "embeddings.npy"),
    ):
        if digest(path.read_bytes()) != summary["input_hashes"][name]:
            raise ValueError(f"Stale numerical input: {name}")
    for name, expected in summary["result_hashes"].items():
        if digest((RESULTS / name).read_bytes()) != expected:
            raise ValueError(f"Stale numerical output: {name}")
    review = json.loads((RESULTS / "reviewed_topic_labels.json").read_text())
    examples = read_rows(RESULTS / "topic_representatives.csv")
    labels = validated_labels(summary, review, examples)
    shares = read_rows(RESULTS / "attention_shares.csv")
    ratios = read_rows(RESULTS / "attention_share_ratios.csv")
    # CSV blanks remain undefined rather than becoming zero.
    for row in ratios:
        if row["attention_share_ratio"] != "":
            row["attention_share_ratio"] = float(row["attention_share_ratio"])
    sources = read_rows(CORPUS / "complete_sources.csv")
    organizations = {source["caucus"]: source["organization"] for source in sources}
    densities = read_rows(RESULTS / "density_coordinates.csv")
    for destination, background in BACKGROUNDS.items():
        make_figures(
            ROOT / "figures" / destination / "caucuses",
            background,
            labels,
            shares,
            ratios,
            organizations,
            densities,
        )
    lines = [
        "# DSA caucuses: programs, strategy and attention",
        "",
        f"**{summary['eligible_claims']:,} eligible normalized claims; "
        f"{len(sources)} flagship statements.** Snapshot collected November 1, 2026.",
        "",
        "This compares documented political language, not membership, influence or agreement. "
        "Guides are discovery-only; "
        "local drafts and regional coalitions remain separate supplements.",
        "",
        "![Caucus attention shares](../../figures/substack/caucuses/caucus-attention-shares.png)",
        "",
        "![Shared language-density map]"
        "(../../figures/substack/caucuses/major-caucus-language-density.png)",
        "",
        "## Largest attention share in each subject",
        "",
        "These are shares of extracted claims, not measures of support or caucus size. "
        "The baseline gives each of the other twelve groups equal weight. "
        "Small claim counts and different statement styles can produce large contrasts.",
        "",
        "| Subject | Highest-share caucus/network | Attention share | "
        "Other groups, averaged | Ratio |",
        "|---|---|---:|---:|---:|",
    ]
    for topic, label in sorted(labels.items(), key=lambda item: item[1]["title"]):
        highest = max(
            (row for row in shares if row["topic_id"] == topic),
            key=lambda row: float(row["attention_share"]),
        )
        comparison = next(
            row
            for row in ratios
            if row["topic_id"] == topic
            and row["group"] == highest["group"]
            and row["comparison"] == "equal_caucus_rest"
        )
        ratio = comparison["attention_share_ratio"]
        multiplier = f"{ratio:.2f}×" if ratio != "" else "undefined"
        lines.append(
            f"| {label['title']} | {organizations[highest['group']]} | "
            f"{float(highest['attention_share']):.1%} | "
            f"{float(comparison['baseline_attention_share']):.1%} | {multiplier} |"
        )
    lines += [
        "",
        "## Source-backed subjects",
        "",
    ]
    by_topic = defaultdict(list)
    for example in examples:
        by_topic[example["topic_id"]].append(example)
    for topic, label in sorted(labels.items(), key=lambda item: item[1]["title"]):
        lines += [f"### {label['title']}", "", label["summary"], ""]
        lines += [
            "<details>",
            "<summary>Primary-source examples by caucus</summary>",
            "",
        ]
        shown = set()
        for example in by_topic[topic]:
            if example["group"] in shown:
                continue
            shown.add(example["group"])
            name = organizations[example["group"]]
            lines.append(
                f"- **{name}:** {example['claim_text']} "
                f"([source]({example['source_url']}); `{example['claim_id']}`)."
            )
        lines += [
            "",
            "</details>",
            "",
            f"![Attention](../../figures/substack/caucuses/{topic}-attention.png)",
            "",
            f"[All caucus-pair ratios](../../figures/substack/caucuses/{topic}-all-ratios.png)",
            "",
        ]
    lines += [
        "## Coverage and qualifications",
        "",
        "| Caucus/network | Eligible claims | Statement date | Primary statement |",
        "|---|---:|---|---|",
    ]
    for source in sources:
        date = source.get("version_date") or source["publication_date"] or "Not stated"
        lines.append(
            f"| {source['organization']} | {summary['claims_by_caucus'][source['caucus']]} "
            f"| {date} | [{source['title']}]({source['source_url']}) |"
        )
    lines += [
        "",
        "## Methods and complete data",
        "",
        "Attention shares equalize documents within each caucus; all eligible claims, including "
        "unclustered material, remain in denominators. Directed ratios use unrounded shares, "
        "without smoothing. A zero denominator is undefined. The combined baseline averages "
        "other caucuses equally, not by membership or claim count.",
        "",
        "One document per group does not support sampling error bars or a historical trend. "
        "Known statement dates are distinct from the retrieval date. The source ledger records "
        "networks, local/regional supplements, "
        "an adoption-uncertain draft, and unrecovered groups.",
        "",
        f"Extraction attempted all {summary['extraction']['blocks']} bounded chunks. "
        f"{summary['extraction']['model_blocks_by_status'].get('validation_failed', 0)} "
        "model chunks failed validation; "
        f"{summary['extraction']['blocks_by_status'].get('validation_failed', 0)} "
        "remain without usable recovery. "
        f"{summary['extraction']['assistant_flagged_claims']} candidate claims were flagged "
        "in targeted source review. Failed chunks and flagged originals do not enter "
        "attention-share denominators. "
        f"{summary['extraction']['assistant_source_repaired_claims']} source-bound "
        "assistant corrections are separately identified and included when eligible. "
        "Original responses, failed dispositions, evidence and retry history are retained. "
        "Source-fidelity revision and targeted assistant review are not independent human gold.",
        "",
        "Attention is measured only among eligible extracted claims, not all words or every "
        "position in the original statements. Extraction failures and exclusions can change "
        "the shares. Statement dates and writing styles differ; this is not a contemporaneous "
        "roster or a ranking of caucus strength. Learned topics summarize overlapping language, "
        "not mutually exclusive ideological camps.",
        "",
        f"The selected {summary['topic_fit']['selected_parameters']['clusters']}-topic model "
        "has an original-embedding cosine silhouette of "
        f"{summary['topic_fit']['selected_parameters']['cosine_silhouette']:.3f}. "
        "That weak separation calls for coarse, overlapping interpretations, not precise "
        "ideological boundaries; the complete download includes the candidate fits and "
        "balanced-refit sensitivity results.",
        "",
        "[Methods](../../docs/dsa_caucus_analysis.md) · "
        "[Complete claims and evidence]"
        "(../../data/analysis/dsa_caucuses/comparison/analysis_claims.csv) · "
        "[All directed attention ratios]"
        "(../../data/analysis/dsa_caucuses/comparison/attention_share_ratios.csv) · "
        "[Complete analysis download](../../data/analysis/dsa_caucuses/dsa_caucus_analysis.zip)",
        "",
    ]
    report = ROOT / "docs/reports/dsa_caucus_analysis.md"
    report.write_text("\n".join(lines))
    members = []
    for directory in (
        ROOT / "data/analysis/dsa_caucuses",
        ROOT / "figures/substack/caucuses",
        ROOT / "figures/margin-of-error/caucuses",
    ):
        members += [
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix != ".zip" and path.name != "publication_manifest.json"
        ]
    ledger = json.loads((ROOT / "data/manual/dsa_caucus_sources.json").read_text())
    records = json.loads((ROOT / "data/raw/dsa_caucuses/retrieval.json").read_text())
    ids = {source["document_id"] for source in ledger["sources"] + ledger["supplemental_sources"]}
    withheld = json.loads((ROOT / "data/raw/dsa_caucuses/publication.json").read_text())
    excluded = {row["path"] for row in withheld["withheld_original_html"]}
    for record in records:
        if record["document_id"] in ids:
            for key in ("text_file", "raw_source", "raw_html"):
                if record.get(key) and record[key] not in excluded:
                    members.append(ROOT / record[key])
    members += [
        report,
        ROOT / "docs/dsa_caucus_analysis.md",
        ROOT / "data/manual/dsa_caucus_sources.json",
        ROOT / "data/raw/dsa_caucuses/retrieval.json",
        ROOT / "data/raw/dsa_caucuses/publication.json",
        ROOT / "scripts/dsa_caucus_analysis.py",
        ROOT / "scripts/dsa_caucus_comparison.py",
        Path(__file__).resolve(),
    ]
    archive = ROOT / "data/analysis/dsa_caucuses/dsa_caucus_analysis.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in sorted(set(members)):
            info = zipfile.ZipInfo(str(path.relative_to(ROOT)), date_time=(2026, 11, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, path.read_bytes())
    result = {
        "status": "reviewed_comparison_published_locally",
        "archive_sha256": digest(archive.read_bytes()),
        "archive_bytes": archive.stat().st_size,
        "archive_members": len(set(members)),
        "review_basis_hash": review_basis(summary),
        "complete_claim_sets_included": True,
        "complete_primary_source_texts_included": True,
        "backgrounds": BACKGROUNDS,
        "files": [
            {"path": str(path.relative_to(ROOT)), "sha256": digest(path.read_bytes())}
            for path in sorted(set(members))
        ],
    }
    write_json(ROOT / "data/analysis/dsa_caucuses/publication_manifest.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(publish(), indent=2))
