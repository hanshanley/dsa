"""Claim-text embeddings, three-organization KDEs and weighted CAP topics."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

from .model_topics import Topic
from .national_claim_corpus import CLAIMS_ROOT, FULL_OUTPUT, bundle
from .national_claims import PILOT_OUTPUT
from .national_platform_kde import LABELS, analyze_view, encode, plot_outputs
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


def topic_shares(
    predictions: list[dict],
    config: dict,
    view: str,
    *,
    groups: tuple[str, ...] = GROUPS,
) -> list[dict]:
    counts = Counter((row["group"], row["bundle_id"]) for row in predictions)
    bundles = {
        group: len({row["bundle_id"] for row in predictions if row["group"] == group})
        for group in groups
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
        for group in groups
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


def plot_topics(shares: list[dict], figures: Path, *, groups: tuple[str, ...] = GROUPS) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from .national_claim_plot_style import COLORS, comparison_page, house_style, save_figure

    house_style()

    selected = [row for row in shares if row.get("view", "expanded") == "expanded"]
    names = sorted(
        {row["topic_name"] for row in selected},
        key=lambda name: (
            -max(float(row["share"]) for row in selected if row["topic_name"] == name),
            name,
        ),
    )
    if not names:
        return
    upper = max(0.05, np.ceil(max(float(row["share"]) for row in selected) * 20) / 20)
    page_size = 11
    pages = math.ceil(len(names) / page_size)
    expected = {f"topic_emphasis{'' if page == 0 else f'_{page + 1}'}" for page in range(pages)}
    for old in figures.glob("topic_emphasis*"):
        if old.suffix in {".png", ".svg"} and old.stem not in expected:
            old.unlink()
    for page, start in enumerate(range(0, len(names), page_size)):
        chunk = names[start : start + page_size]
        fig = comparison_page(
            "Where the documents put their emphasis",
            f"CAP policy categories | Overall weighted share of claims | "
            f"Expanded sources | {page + 1} / {pages}",
            chunk,
            [(LABELS[group], COLORS[group], COLORS[group]) for group in groups],
            [
                [
                    (
                        next(
                            (
                                float(row["share"])
                                for row in selected
                                if row["group"] == group and row["topic_name"] == name
                            ),
                            None,
                        ),
                        False,
                    )
                    for name in chunk
                ]
                for group in groups
            ],
            upper,
        )
        fig.texts[-2].set_text(
            "Same scale on every page. Unclassified claims remain in the denominator. "
            "Equal document / fallback-bundle weights."
        )
        save_figure(fig, figures / f"topic_emphasis{'' if page == 0 else f'_{page + 1}'}")
        plt.close(fig)


def write_report(
    output: Path,
    summary: dict,
    shares: list[dict],
    figures: Path,
    *,
    groups: tuple[str, ...] = GROUPS,
    report: Path | None = None,
) -> Path:
    shares = [{**row, "share": float(row["share"])} for row in shares]
    sample = summary["corpus"]["status"] == "reviewed_sample_not_full_corpus"
    destination = report or (
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
            else "**Full eligible-source claim analysis with automated screening, "
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
    for group in groups:
        lines.append(
            f"| {LABELS[group]} | {summary['claims_by_group'].get(group, 0)} "
            f"| {summary['documents_by_group'][group]} | {summary['bundles_by_group'][group]} |"
        )
    lines += ["", "## Semantic density", ""]
    expanded = summary["views"]["expanded"]
    if expanded["status"] == "complete":
        lines += [
            f"[Compact density overview]({figure_path}/expanded/pairwise_density.png). "
            "For detailed maps and source-linked representative claims, see the "
            "learned-topic section's detailed density comparisons.",
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
        *[
            f"![Document-weighted CAP topic emphasis, continued]({figure_path}/{path.name})"
            for path in sorted(figures.glob("topic_emphasis_*.png"))
        ],
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
    for group in groups:
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
        corpus = summary["corpus"]
        lines += [
            f"Extraction status: **{corpus['status']}**; effective chunk dispositions: "
            f"`{json.dumps(corpus['blocks_by_status'], sort_keys=True)}`.",
            f"[Source coverage]({data_path}/source_coverage.csv) / "
            f"[Chunk dispositions]({data_path}/block_status.csv)",
            "",
        ]
        if corpus.get("assistant_source_repaired_blocks"):
            lines += [
                "Original Gemma chunk outcomes remain "
                f"`{json.dumps(corpus['model_blocks_by_status'], sort_keys=True)}`. "
                f"Targeted assistant source corrections cover "
                f"**{corpus['assistant_source_repaired_blocks']:,} chunks** and supply "
                f"**{corpus['assistant_source_repaired_claims']:,} replacement claims**; "
                f"**{corpus['superseded_model_claims']:,} original candidates** are "
                "superseded, not erased. Zero-claim corrections explicitly dispose of "
                "non-policy material rather than inventing assertions.",
                "",
                "Each correction is bound to the exact target, reference-only context, "
                "raw-response bytes and normalization fingerprint. Unaffected model claims "
                "retain their original IDs and wording; superseded originals remain in the "
                "download but cannot enter fitting or anchor duplicates. Corrected rows have "
                "`normalization_origin=assistant_source_repair` and a blank "
                "`model_claim_text`, never a falsely attributed Gemma reply. Original model "
                "failures and diagnostics remain failures in `model_status`, even when a "
                "source correction recovers their content. This is targeted assistant "
                "source-entailment work, not independent human gold or factual verification.",
                "",
                f"Archived original-candidate review flags: "
                f"**{corpus['assistant_flagged_claims']:,}**; flagged model candidates "
                f"still lacking a superseding correction: "
                f"**{corpus['unrepaired_flagged_model_claims']:,}**. Historical flags are "
                "not a count of unresolved errors in replacement claims.",
                (
                    f"[Component manifests, original responses and source corrections]"
                    f"({data_path}/components/)"
                    if corpus.get("components")
                    else f"[Source-bound correction records]({data_path}/source_repairs/)"
                ),
                "",
            ]
    if summary["corpus"].get("components"):
        lines += [
            "The four-party input reuses the separately published three-party claims without "
            "regenerating or rewording them. Only Libertarian source chunks receive new inference. "
            "Each claim records its normalization component; constituent manifests, original "
            "responses, retry histories and corrections remain under `components/`. There is "
            "no fabricated shared normalization fingerprint. New four-party maps are fitted "
            "jointly and do not replace the preserved three-party results.",
            "",
            f"[Component provenance and file hashes]({data_path}/normalization_components.json)",
            "",
        ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8")
    return destination


def run_analysis(
    output: Path = FULL_OUTPUT,
    *,
    reviewed_sample: bool = False,
    download_model: bool = False,
    groups: tuple[str, ...] = GROUPS,
    coverage_path: Path = OUTPUT / "coverage.csv",
    report: Path | None = None,
    topics: bool = False,
) -> dict:
    if output.resolve() == OUTPUT.resolve() or OUTPUT.resolve() in output.resolve().parents:
        raise ValueError("Do not overwrite the passage baseline")
    if groups != GROUPS:
        protected = (FULL_OUTPUT.resolve(), SAMPLE_OUTPUT.resolve(), PILOT_OUTPUT.resolve())
        protected_reports = {
            ROOT / "report" / name
            for name in (
                "national_claim_analysis.md",
                "national_claim_analysis_sample.md",
                "national_claim_pilot.md",
            )
        }
        if (
            any(output.resolve() == path or path in output.resolve().parents for path in protected)
            or report is None
            or report.resolve() in protected_reports
        ):
            raise ValueError(
                "Additional organizations require separate outputs and an explicit separate report"
            )
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
    if set(row["group"] for row in rows) - set(groups):
        raise ValueError("Selected analysis groups do not cover all claims")
    write_rows(output / "analysis_claims.csv", rows)
    tokenization = audit_claim_lengths(rows, output, download_model=download_model)
    embeddings, reused = encode(rows, output, download_model=download_model)
    predictions, topic_manifest = classify_topics(rows, output, download_model=download_model)
    config = json.loads(TOPIC_CONFIG.read_text())
    selected_ids = {row["document_id"] for row in rows}
    coverage = [row for row in read_rows(coverage_path) if row["document_id"] in selected_ids]
    figures = ROOT / "figures/national_claims" / output.name
    figures.mkdir(parents=True, exist_ok=True)
    views, shares = {}, []
    for view in ("expanded", "strict"):
        indices = [index for index, row in enumerate(rows) if view == "expanded" or row["strict"]]
        selected = [rows[index] for index in indices]
        result = analyze_view(selected, embeddings[indices], output / view, groups=groups)
        views[view] = {key: value for key, value in result.items() if not key.startswith("_")}
        view_ids = {row["document_id"] for row in selected}
        plot_outputs(
            result,
            [row for row in coverage if row["document_id"] in view_ids],
            figures=figures / view,
        )
        shares.extend(
            topic_shares([predictions[index] for index in indices], config, view, groups=groups)
        )
    write_rows(output / "topic_emphasis.csv", shares)
    plot_topics([row for row in shares if row["view"] == "expanded"], figures, groups=groups)
    summary = {
        "corpus": corpus,
        "analytical_unit": "Normalized claim text; original source evidence is audit-only",
        "claims": len(rows),
        "claims_by_group": dict(Counter(row["group"] for row in rows)),
        "documents_by_group": {
            group: len({row["document_id"] for row in rows if row["group"] == group})
            for group in groups
        },
        "bundles_by_group": {
            group: len({row["bundle_id"] for row in rows if row["group"] == group})
            for group in groups
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
    report = write_report(output, summary, shares, figures, groups=groups, report=report)
    if topics or (output / "topics/fit_manifest.json").exists():
        from .national_claim_topics import prepare as prepare_topics
        from .national_claim_topics import render as render_topics

        if topics:
            prepare_topics(output, groups=groups)
        summary["learned_topics"] = render_topics(output, report=report)
        write_json(output / "analysis_summary.json", summary)
    bundle(output, figures=figures, report=report)
    print(f"Claim analysis: {len(rows)} claims; report {report.relative_to(ROOT)}", flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=FULL_OUTPUT)
    parser.add_argument("--reviewed-sample", action="store_true")
    parser.add_argument("--download-model", action="store_true")
    parser.add_argument(
        "--topics",
        action="store_true",
        help="Prepare shared learned topics and render cached labels; no new Gemma inference",
    )
    args = parser.parse_args()
    output = SAMPLE_OUTPUT if args.reviewed_sample and args.input == FULL_OUTPUT else args.input
    run_analysis(
        output,
        reviewed_sample=args.reviewed_sample,
        download_model=args.download_model,
        topics=args.topics,
    )


if __name__ == "__main__":
    main()
