"""Claim-text embeddings, three-organization KDEs and weighted CAP topics."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from .model_topics import Topic
from .national_claim_corpus import CLAIMS_ROOT, FULL_OUTPUT, bundle
from .national_claims import PILOT_OUTPUT
from .national_platform_kde import COLORS, LABELS, analyze_view, encode, plot_outputs
from .national_platforms import (
    GROUPS,
    MAX_LENGTH,
    OUTPUT,
    ROOT,
    STRICT_TYPES,
    digest,
    read_rows,
    write_json,
    write_rows,
)
from .provisional_kde import MODEL_NAME, MODEL_REVISION

TOPIC_CONFIG = ROOT / "config/cap_topics.json"
SAMPLE_OUTPUT = CLAIMS_ROOT / "reviewed_sample"


def prepare_reviewed_sample(output: Path = SAMPLE_OUTPUT) -> dict:
    if output.resolve() in {PILOT_OUTPUT.resolve(), FULL_OUTPUT.resolve(), OUTPUT.resolve()}:
        raise ValueError("The frozen pilot, full extraction and baseline must not be overwritten")
    original = read_rows(PILOT_OUTPUT / "claims.csv")
    selected, seen = [], {}
    for row in original:
        if row["review_status"] != "reviewed_no_issue_observed":
            continue
        key = (row["document_id"], row["claim_text"].casefold())
        duplicate = seen.get(key, "")
        seen.setdefault(key, row["claim_id"])
        selected.append(
            {
                **row,
                "analysis_eligible": not bool(duplicate),
                "duplicate_of": duplicate,
                "quality_status": "assistant_reviewed_unflagged_not_independent_gold",
            }
        )
    output.mkdir(parents=True, exist_ok=True)
    write_rows(output / "claims.csv", selected)
    write_rows(output / "complete_sources.csv", read_rows(PILOT_OUTPUT / "complete_sources.csv"))
    write_rows(output / "semantic_review.csv", read_rows(PILOT_OUTPUT / "semantic_review.csv"))
    write_rows(output / "sample_blocks.csv", read_rows(PILOT_OUTPUT / "blocks.csv"))
    summary = {
        "status": "reviewed_sample_not_full_corpus",
        "claims": len(selected),
        "analysis_claims": sum(bool(row["analysis_eligible"]) for row in selected),
        "claims_by_group": dict(Counter(row["group"] for row in selected)),
        "sample_blocks": 60,
        "sample_documents": len(read_rows(PILOT_OUTPUT / "complete_sources.csv")),
        "quality": (
            "Selected pilot candidates with no individually observed assistant-review issue; "
            "not a representative sample, independent human gold or semantic certification"
        ),
        "normalization": "Frozen pilot claim wording; full extraction uses the structured schema",
        "pilot_claims_sha256": digest((PILOT_OUTPUT / "claims.csv").read_bytes()),
        "pilot_review_sha256": digest((PILOT_OUTPUT / "semantic_review.csv").read_bytes()),
    }
    write_json(output / "extraction_summary.json", summary)
    return summary


def analysis_rows(claims: list[dict], sources: list[dict]) -> list[dict]:
    by_id = {source["document_id"]: source for source in sources}
    rows, seen = [], set()
    for claim in claims:
        if str(claim.get("analysis_eligible", "")).lower() != "true" or claim.get("duplicate_of"):
            continue
        identifier = claim["claim_id"]
        if identifier in seen:
            raise ValueError(f"Duplicate claim ID: {identifier}")
        seen.add(identifier)
        source = by_id[claim["document_id"]]
        text = source["scoped_text"]
        start, end = int(claim["source_start"]), int(claim["source_end"])
        if (
            claim["group"] != source["group"]
            or claim["source_sha256"] != source["sha256"]
            or claim["scoped_text_sha256"] != source["text_sha256"]
            or digest(text) != source["text_sha256"]
            or not 0 <= start < end <= len(text)
            or text[start:end] != claim["evidence"]
            or not claim["claim_text"].strip()
        ):
            raise ValueError(f"Claim/source provenance mismatch: {identifier}")
        rows.append(
            {
                **claim,
                "segment_id": identifier,
                "text": claim["claim_text"],
                "text_sha256": digest(claim["claim_text"]),
                "bundle_id": source.get("bundle_id") or source["document_id"],
                "strict": source["document_type"] in STRICT_TYPES,
                "locator": claim.get("locator") or f"scoped characters {start}:{end}",
                "adoption_date": source.get("adoption_date", ""),
                "version_date": source.get("version_date", ""),
            }
        )
    return rows


def audit_claim_lengths(rows: list[dict], output: Path, *, download_model: bool = False) -> dict:
    config = json.loads(TOPIC_CONFIG.read_text())
    models = {
        "gte": (MODEL_NAME, MODEL_REVISION),
        "topics": (config["model"], config["model_revision"]),
    }
    key = {
        "models": {
            name: {"name": model, "revision": revision}
            for name, (model, revision) in models.items()
        },
        "ordered_text_hash": digest("\n".join(digest(row["text"]) for row in rows)),
        "limit": MAX_LENGTH,
    }
    manifest_path = output / "claim_tokenization_manifest.json"
    path = output / "claim_token_lengths.csv"
    audited = None
    if path.exists() and manifest_path.exists():
        try:
            cached = read_rows(path)
            if (
                json.loads(manifest_path.read_text()) == key
                and [row["claim_id"] for row in cached] == [row["claim_id"] for row in rows]
                and all(int(row[f"{name}_tokens"]) > 0 for row in cached for name in models)
            ):
                audited = cached
        except (ValueError, KeyError, OSError):
            pass
    if audited is None:
        from transformers import AutoTokenizer

        audited = [{"claim_id": row["claim_id"]} for row in rows]
        for name, (model, revision) in models.items():
            tokenizer = AutoTokenizer.from_pretrained(
                model,
                revision=revision,
                trust_remote_code=name == "gte",
                local_files_only=not download_model,
            )
            tokens = tokenizer([row["text"] for row in rows], truncation=False)["input_ids"]
            for row, values in zip(audited, tokens, strict=True):
                row[f"{name}_tokens"] = len(values)
        write_rows(path, audited)
        write_json(manifest_path, key)
    oversized = [
        row["claim_id"]
        for row in audited
        if any(int(row[f"{name}_tokens"]) > MAX_LENGTH for name in models)
    ]
    if oversized:
        raise ValueError(
            f"{len(oversized)} claims exceed the {MAX_LENGTH}-token encoder limit; "
            f"refusing silent truncation. See {path}"
        )
    return {
        "limit": MAX_LENGTH,
        "maximum_tokens": {
            name: max(int(row[f"{name}_tokens"]) for row in audited) for name in models
        },
        "truncated_claims": 0,
    }


def topic_predictions(rows: list[dict], similarities: np.ndarray, config: dict) -> list[dict]:
    topics = config["topics"]
    if similarities.shape != (len(rows), len(topics)) or not np.isfinite(similarities).all():
        raise ValueError("Invalid topic similarity matrix")
    predictions = []
    for row, scores in zip(rows, similarities, strict=True):
        order = np.argsort(-scores, kind="stable")
        first, second = int(order[0]), int(order[1])
        selected = topics[first] if scores[first] >= float(config["minimum_similarity"]) else None
        predictions.append(
            {
                **row,
                "topic_code": str(selected["code"]) if selected else "",
                "topic_name": selected["name"] if selected else "Unclassified",
                "similarity": float(scores[first]),
                "runner_up_code": str(topics[second]["code"]),
                "runner_up_name": topics[second]["name"],
                "runner_up_similarity": float(scores[second]),
                "margin": float(scores[first] - scores[second]),
            }
        )
    return predictions


def topic_shares(predictions: list[dict], config: dict, view: str) -> list[dict]:
    counts = Counter((row["group"], row["bundle_id"]) for row in predictions)
    bundles = {
        group: len({row["bundle_id"] for row in predictions if row["group"] == group})
        for group in GROUPS
    }
    totals, claims = Counter(), Counter()
    for row in predictions:
        key = (row["group"], row["topic_code"])
        totals[key] += 1 / counts[(row["group"], row["bundle_id"])] / bundles[row["group"]]
        claims[key] += 1
    topics = [(str(row["code"]), row["name"]) for row in config["topics"]]
    return [
        {
            "view": view,
            "group": group,
            "topic_code": code,
            "topic_name": name,
            "share": totals[(group, code)],
            "claims": claims[(group, code)],
            "group_bundles": bundles[group],
        }
        for group in GROUPS
        for code, name in [*topics, ("", "Unclassified")]
    ]


def classify_topics(
    rows: list[dict],
    output: Path,
    *,
    download_model: bool = False,
) -> tuple[list[dict], dict]:
    config = json.loads(TOPIC_CONFIG.read_text())
    key = {
        "model": config["model"],
        "revision": config["model_revision"],
        "config_sha256": digest(TOPIC_CONFIG.read_bytes()),
        "ordered_text_hash": digest("\n".join(digest(row["text"]) for row in rows)),
        "claims": len(rows),
        "topics": len(config["topics"]),
        "max_length": 256,
        "normalization": "l2",
    }
    path, manifest_path = output / "topic_similarities.npy", output / "topic_manifest.json"
    similarities = None
    if path.exists() and manifest_path.exists():
        try:
            if json.loads(manifest_path.read_text()) == key:
                cached = np.load(path, allow_pickle=False)
                if (
                    cached.shape == (len(rows), len(config["topics"]))
                    and np.isfinite(cached).all()
                    and (np.abs(cached) <= 1.00001).all()
                ):
                    similarities = cached
        except (ValueError, OSError):
            pass
    reused = similarities is not None
    if similarities is None:
        import torch
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(
            config["model"],
            revision=config["model_revision"],
            local_files_only=not download_model,
            device="mps" if torch.backends.mps.is_available() else "cpu",
        )
        model.max_seq_length = key["max_length"]
        topics = [
            Topic(
                code=int(row["code"]),
                name=row["name"],
                description=row["description"],
                seeds=tuple(row["seeds"]),
            )
            for row in config["topics"]
        ]
        topic_vectors = model.encode(
            [topic.embedding_text for topic in topics],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        vectors = model.encode(
            [row["text"] for row in rows],
            batch_size=64,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=True,
        )
        similarities = vectors @ topic_vectors.T
        topic_predictions(rows, similarities, config)
        np.save(path, similarities)
        write_json(manifest_path, key)
    predictions = topic_predictions(rows, similarities, config)
    write_rows(output / "topic_assignments.csv", predictions)
    return predictions, {**key, "cache_reused": reused}


def plot_topics(shares: list[dict], figures: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    names = list(dict.fromkeys(row["topic_name"] for row in shares))
    names.sort(key=lambda name: max(row["share"] for row in shares if row["topic_name"] == name))
    fig, axis = plt.subplots(figsize=(9, 8))
    for index, group in enumerate(GROUPS):
        values = {row["topic_name"]: row["share"] for row in shares if row["group"] == group}
        axis.scatter(
            [values[name] for name in names],
            np.arange(len(names)) + (index - 1) * 0.18,
            color=COLORS[group],
            s=23,
            label=LABELS[group],
        )
    axis.set_yticks(range(len(names)), names)
    axis.xaxis.set_major_formatter(PercentFormatter(1))
    axis.set_xlim(left=0)
    axis.set_xlabel("Share of claims, equal document / fallback-period-bundle weight")
    axis.grid(axis="x", color="#e5e5e5", linewidth=0.6)
    axis.set_axisbelow(True)
    axis.legend(frameon=False, loc="lower right")
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.tick_params(axis="y", length=0)
    fig.tight_layout()
    fig.savefig(figures / "topic_emphasis.png", dpi=180)
    fig.savefig(figures / "topic_emphasis.svg")
    plt.close(fig)


def write_report(output: Path, summary: dict, shares: list[dict], figures: Path) -> Path:
    sample = summary["corpus"]["status"] == "reviewed_sample_not_full_corpus"
    destination = (
        ROOT
        / "report"
        / ("national_claim_analysis_sample.md" if sample else "national_claim_analysis.md")
    )
    figure_path = f"../{figures.relative_to(ROOT).as_posix()}"
    data_path = f"../{output.relative_to(ROOT).as_posix()}"
    lines = [
        "# National platforms: claim-based analysis",
        "",
        (
            "**Provisional selected-sample result, not a full-corpus comparison.** "
            "This run uses the pilot's individually unflagged assistant-reviewed claims. "
            "The original sample covered 60 blocks, not complete documents; selection after "
            "review introduces additional bias. These shares do not estimate "
            "platform-wide emphasis."
            if sample
            else "**Full eligible-source normalization with automated screening, "
            "not human-certified "
            "claims or fact-checking.** All source chunks and any failed/unresolved extractions "
            "remain auditable in the coverage tables and raw responses."
        ),
        "",
        "The analytical text is the **claim**, not its original evidence passage. "
        "The separate passage-based analysis and its outputs remain unchanged.",
        "",
        "| Organization | Claims analyzed | Documents | Document / fallback bundles |",
        "|---|---:|---:|---:|",
    ]
    for group in GROUPS:
        lines.append(
            f"| {LABELS[group]} | {summary['claims_by_group'].get(group, 0)} "
            f"| {summary['documents_by_group'][group]} | {summary['bundles_by_group'][group]} |"
        )
    lines += ["", "## Semantic density", ""]
    expanded = summary["views"]["expanded"]
    if expanded["status"] == "complete":
        lines += [
            f"![Pairwise density of claim language]({figure_path}/expanded/pairwise_density.png)",
            "",
            f"The shared representation uses {expanded['dimensions']} dimensions for KDE; "
            "the two-dimensional display is not the density-estimation space. Sampling balances "
            "organizations and gives each document/fallback-period bundle equal aggregate density "
            "weight. Positive contrasts mean greater first-organization language density, "
            "not agreement, ideological direction, or causal differences.",
        ]
    else:
        lines.append(f"No expanded KDE: {expanded['reason']}.")
    strict = summary["views"]["strict"]
    lines += [
        "",
        f"Platforms/programs-only sensitivity: **{strict['status']}**."
        + (
            f" {strict['reason']}."
            if "reason" in strict
            else f" Its independently fitted space has {strict['dimensions']} dimensions; "
            "its coordinates cannot be compared directly with the expanded map."
        ),
        "",
        "## Topics",
        "",
        f"![Document-weighted CAP topic emphasis]({figure_path}/topic_emphasis.png)",
        "",
        "The existing pinned MiniLM classifier compares normalized claim text with CAP topic "
        "descriptions (minimum cosine similarity 0.2). Each claim receives at most one topic; "
        "unclassified claims remain in the denominator. This is exploratory classification, "
        "not validated topic gold. Topic shares use equal aggregate document/fallback-bundle "
        "weights, not raw claim counts.",
        "",
        "| Organization | Largest weighted topic shares in this input |",
        "|---|---|",
    ]
    for group in GROUPS:
        ranked = sorted(
            [row for row in shares if row["group"] == group and row["view"] == "expanded"],
            key=lambda row: -row["share"],
        )[:3]
        lines.append(
            f"| {LABELS[group]} | "
            + "; ".join(f"{row['topic_name']} {row['share']:.1%}" for row in ranked)
            + " |"
        )
    if strict["status"] == "complete" and expanded["status"] == "complete":
        lines += [
            "",
            "DSA's adopted-only input contains "
            f"{strict['group_documents']['dsa']} documents and "
            f"{strict['group_passages']['dsa']:,} claims, compared with "
            f"{expanded['group_documents']['dsa']} documents and "
            f"{expanded['group_passages']['dsa']:,} claims in the expanded input.",
        ]
        leading = {
            view: max(
                (
                    row
                    for row in shares
                    if row["view"] == view and row["group"] == "dsa" and row["topic_code"]
                ),
                key=lambda row: row["share"],
                default=None,
            )
            for view in ("expanded", "strict")
        }
        if all(row and row["share"] > 0 for row in leading.values()):
            first, second = leading["expanded"], leading["strict"]
            lines += [
                f"The largest classified DSA topic is {first['topic_name']} "
                f"({first['share']:.1%}) in the expanded input and "
                f"{second['topic_name']} ({second['share']:.1%}) in the strict input. "
                "This sensitivity reflects source-type and period composition, "
                "not a measured change in positions over time.",
            ]
    lines += [
        "",
        "## Provenance and reproduction",
        "",
        "Full extraction uses source chunks of at most 240 words, sentence-aware splitting of "
        "long paragraphs, and at most 1,200 preceding-context characters. The prompt requires "
        "preservation of actors, stance/modality, conditions, temporal scope and reported-speaker "
        "attribution; automated revision does not certify that every requirement was met. Source "
        "organization remains metadata rather than a mechanically repeated embedding prefix. "
        "Exact within-document claim duplicates are retained in downloads but excluded "
        "from fitting.",
        "",
        f"- [Complete claim/source download, not metadata only]({data_path}/claim_documents.zip)",
        f"- [Claims and exact supporting source offsets]({data_path}/claims.csv)",
        f"- [Complete source texts]({data_path}/complete_sources.csv)",
        f"- [Topic assignments]({data_path}/topic_assignments.csv)",
        f"- [Weighted topic shares, both views]({data_path}/topic_emphasis.csv)",
        f"- [Machine-readable analysis summary]({data_path}/analysis_summary.json)",
        "",
        "Source documents retain their original attribution. Claims describe what sources assert; "
        "they do not independently establish truth. Pooling mixes periods and genres. Missing "
        "historical sources, including the final 2015 DSA strategy, remain missing rather than "
        "being inferred from later documents. No website deployment is performed.",
        "",
    ]
    if not sample:
        lines += [
            f"Extraction status: **{summary['corpus']['status']}**; "
            "chunk dispositions: "
            f"`{json.dumps(summary['corpus']['blocks_by_status'], sort_keys=True)}`.",
            f"[Source coverage]({data_path}/source_coverage.csv) / "
            f"[Chunk dispositions]({data_path}/block_status.csv)",
            "",
        ]
    destination.write_text("\n".join(lines), encoding="utf-8")
    return destination


def run_analysis(
    output: Path = FULL_OUTPUT,
    *,
    reviewed_sample: bool = False,
    download_model: bool = False,
) -> dict:
    if output.resolve() == OUTPUT.resolve() or OUTPUT.resolve() in output.resolve().parents:
        raise ValueError("Do not overwrite the passage baseline")
    if reviewed_sample:
        prepare_reviewed_sample(output)
    corpus = json.loads((output / "extraction_summary.json").read_text())
    if corpus["status"] == "running":
        raise ValueError("Full-source extraction is still running; do not mislabel it as complete")
    rows = analysis_rows(
        read_rows(output / "claims.csv"), read_rows(output / "complete_sources.csv")
    )
    if not rows:
        raise ValueError("No eligible normalized claims")
    write_rows(output / "analysis_claims.csv", rows)
    tokenization = audit_claim_lengths(rows, output, download_model=download_model)
    embeddings, reused = encode(rows, output, download_model=download_model)
    predictions, topic_manifest = classify_topics(rows, output, download_model=download_model)
    config = json.loads(TOPIC_CONFIG.read_text())
    selected_ids = {row["document_id"] for row in rows}
    coverage = [
        row for row in read_rows(OUTPUT / "coverage.csv") if row["document_id"] in selected_ids
    ]
    figures = ROOT / "figures/national_claims" / output.name
    figures.mkdir(parents=True, exist_ok=True)
    views, shares = {}, []
    for view in ("expanded", "strict"):
        indices = [index for index, row in enumerate(rows) if view == "expanded" or row["strict"]]
        selected = [rows[index] for index in indices]
        result = analyze_view(selected, embeddings[indices], output / view)
        views[view] = {key: value for key, value in result.items() if not key.startswith("_")}
        view_ids = {row["document_id"] for row in selected}
        plot_outputs(
            result,
            [row for row in coverage if row["document_id"] in view_ids],
            figures=figures / view,
        )
        shares.extend(topic_shares([predictions[index] for index in indices], config, view))
    write_rows(output / "topic_emphasis.csv", shares)
    plot_topics([row for row in shares if row["view"] == "expanded"], figures)
    summary = {
        "corpus": corpus,
        "analytical_unit": "Normalized claim text; original source evidence is audit-only",
        "claims": len(rows),
        "claims_by_group": dict(Counter(row["group"] for row in rows)),
        "documents_by_group": {
            group: len({row["document_id"] for row in rows if row["group"] == group})
            for group in GROUPS
        },
        "bundles_by_group": {
            group: len({row["bundle_id"] for row in rows if row["group"] == group})
            for group in GROUPS
        },
        "views": views,
        "embedding_cache_reused": reused,
        "topic_model": topic_manifest,
        "claims_sha256": digest((output / "claims.csv").read_bytes()),
        "complete_sources_sha256": digest((output / "complete_sources.csv").read_bytes()),
        "tokenization": tokenization,
        "baseline_modified": False,
        "website_deployed": False,
    }
    write_json(output / "analysis_summary.json", summary)
    report = write_report(output, summary, shares, figures)
    bundle(output)
    print(f"Claim analysis: {len(rows)} claims; report {report.relative_to(ROOT)}", flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=FULL_OUTPUT)
    parser.add_argument("--reviewed-sample", action="store_true")
    parser.add_argument("--download-model", action="store_true")
    args = parser.parse_args()
    output = SAMPLE_OUTPUT if args.reviewed_sample and args.input == FULL_OUTPUT else args.input
    run_analysis(output, reviewed_sample=args.reviewed_sample, download_model=args.download_model)


if __name__ == "__main__":
    main()
