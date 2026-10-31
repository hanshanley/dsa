"""Offline, source-bound chunk audit and fixed-representation weighting sensitivity."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
from sklearn.neighbors import KernelDensity
from sklearn.preprocessing import StandardScaler

from .national_claim_analysis import analysis_rows
from .national_claim_corpus import export_results, within_chunk_duplicate_basis
from .national_claim_topics import claim_weights, displayed_topics, load_inputs
from .national_platform_kde import balance_weights, fit_indices
from .national_platforms import GROUPS, digest, read_rows, write_json, write_rows
from .provisional_kde import SEED


def chunk_weights(rows: list[dict]) -> np.ndarray:
    if any(not row.get("block_id") for row in rows):
        raise ValueError("Chunk weighting requires extraction block IDs")
    counts = Counter((row["group"], row["bundle_id"], row["block_id"]) for row in rows)
    chunks = Counter((group, bundle) for group, bundle, _ in counts)
    bundles = Counter(group for group, _ in chunks)
    return np.array(
        [
            1
            / bundles[row["group"]]
            / chunks[row["group"], row["bundle_id"]]
            / counts[row["group"], row["bundle_id"], row["block_id"]]
            for row in rows
        ],
        dtype=float,
    )


def parse_numbers(value: str) -> set[int]:
    result = set()
    for item in value.split("|"):
        bounds = [int(number.strip()) for number in item.strip().split("-")]
        if len(bounds) == 1:
            result.add(bounds[0])
        elif len(bounds) == 2 and 1 <= bounds[0] <= bounds[1]:
            result.update(range(bounds[0], bounds[1] + 1))
        else:
            raise ValueError("Invalid source-review claim range")
    return result


def prepare_cleaned(corpus: Path, output: Path, review: dict) -> dict:
    if review.get("schema_version") != 1 or not review.get("reviewer"):
        raise ValueError("Invalid chunk source review")
    originals = read_rows(corpus / "claims.csv")
    by_block = defaultdict(list)
    for row in originals:
        by_block[row["block_id"]].append(row)
    reviews = {row["block_id"]: row for row in read_rows(corpus / "semantic_review.csv")}
    seen = set()
    for decision in review["exclusions"]:
        block = decision["block_id"]
        if (
            block not in by_block
            or block in seen
            or decision["basis_sha256"] != within_chunk_duplicate_basis(by_block[block])
        ):
            raise ValueError(f"Stale or unknown chunk source review: {block}")
        seen.add(block)
        numbers = parse_numbers(decision["claim_numbers"])
        existing = reviews.get(block, {})
        numbers |= (
            parse_numbers(existing["flagged_claim_numbers"])
            if existing.get("flagged_claim_numbers")
            else set()
        )
        if not numbers <= {
            int(row["claim_id"].rsplit("-", 1)[1])
            for row in by_block[block]
            if row["normalization_origin"] == "local_gemma"
        }:
            raise ValueError("Source review references an unknown original claim")
        if not decision.get("notes"):
            raise ValueError("Source exclusions require a rationale")
        reviews[block] = {
            "block_id": block,
            "review_status": "issues_found",
            "flagged_claim_numbers": " | ".join(map(str, sorted(numbers))),
            "omissions": existing.get("omissions", ""),
            "notes": " ".join(filter(None, (existing.get("notes"), decision["notes"]))),
            "reviewer": review["reviewer"],
        }
    output.mkdir()
    for filename in ("complete_sources.csv", "normalization_manifest.json"):
        shutil.copy2(corpus / filename, output / filename)
    for directory in ("responses", "response_history", "source_repairs"):
        if (corpus / directory).exists():
            shutil.copytree(corpus / directory, output / directory)
    write_rows(output / "semantic_review.csv", list(reviews.values()))
    write_json(output / "within_chunk_duplicates.json", review["duplicates"])
    blocks = read_rows(corpus / "blocks.csv")
    for block in blocks:
        block["units"] = json.loads(block["units"])
        for field in ("source_start", "source_end", "words"):
            block[field] = int(block[field])
    summary = export_results(
        blocks, output, json.loads((corpus / "normalization_manifest.json").read_text())
    )
    cleaned = read_rows(output / "claims.csv")
    if [(r["claim_id"], r["claim_text"], r["evidence"]) for r in originals] != [
        (r["claim_id"], r["claim_text"], r["evidence"]) for r in cleaned
    ]:
        raise ValueError("Chunk review changed original claim membership, wording or evidence")
    return summary


def subject_comparison(
    rows: list[dict], variants: dict[str, np.ndarray], assignments: dict[str, str], labels: dict
) -> list[dict]:
    result = []
    shown = displayed_topics(labels)
    for group in GROUPS:
        shares = {
            name: {
                topic: sum(
                    float(weights[i])
                    for i, row in enumerate(rows)
                    if row["group"] == group and assignments[row["claim_id"]] == topic
                )
                for topic in labels
            }
            for name, weights in variants.items()
        }
        ranks = {
            name: {
                topic: rank
                for rank, topic in enumerate(sorted(shown, key=lambda t: (-values[t], t)), 1)
            }
            for name, values in shares.items()
        }
        for topic, label in labels.items():
            a, b, c = (shares[name][topic] for name in ("A", "B", "C"))
            result.append(
                {
                    "group": group,
                    "topic_id": topic,
                    "title": label["title"],
                    "displayed_subject": topic in shown,
                    "published_claim_share": a,
                    "cleaned_claim_share": b,
                    "cleaned_chunk_share": c,
                    "cleanup_delta_pp": 100 * (b - a),
                    "chunk_weight_delta_pp": 100 * (c - b),
                    "total_delta_pp": 100 * (c - a),
                    **{f"{name}_rank": values.get(topic, "") for name, values in ranks.items()},
                }
            )
    return result


def frozen_density(
    corpus: Path, rows: list[dict], embeddings: np.ndarray, variants: dict, output: Path
) -> dict:
    import umap

    frozen = json.loads((corpus / "expanded/summary.json").read_text())
    samples = fit_indices(rows, groups=GROUPS)
    indices = sorted(i for selected in samples.values() for i in selected)
    reducer = umap.UMAP(
        n_neighbors=min(15, len(indices) - 1),
        min_dist=0.1,
        metric="cosine",
        n_components=frozen["dimensions"],
        random_state=SEED,
        n_jobs=1,
    )
    reducer.fit_transform(embeddings[indices])
    coordinates = reducer.transform(embeddings)
    standardized = StandardScaler().fit(coordinates[indices]).transform(coordinates)
    old = {row["segment_id"]: row for row in read_rows(corpus / "expanded/scored_passages.csv")}
    replay_error = {}
    for group, selected in samples.items():
        estimator = KernelDensity(kernel="gaussian", bandwidth=frozen["bandwidth"]).fit(
            standardized[selected], sample_weight=balance_weights(rows, selected)
        )
        actual = estimator.score_samples(standardized)
        expected = np.array([float(old[row["claim_id"]][f"{group}_log_density"]) for row in rows])
        replay_error[group] = float(np.max(np.abs(actual - expected)))
    if max(replay_error.values()) > 1e-4:
        raise ValueError(f"Original frozen density-space replay mismatch: {replay_error}")
    write_rows(
        output / "frozen_coordinates.csv",
        [
            {"claim_id": row["claim_id"]}
            | {
                f"dimension_{dimension}": float(value)
                for dimension, value in enumerate(standardized[i], 1)
            }
            for i, row in enumerate(rows)
        ],
    )
    densities = {}
    for name, weights in variants.items():
        print(
            f"Fitting {name}: all eligible claims, frozen {frozen['dimensions']}D space", flush=True
        )
        densities[name] = {}
        for group in GROUPS:
            selected = [i for i, row in enumerate(rows) if row["group"] == group and weights[i] > 0]
            estimator = KernelDensity(kernel="gaussian", bandwidth=frozen["bandwidth"]).fit(
                standardized[selected], sample_weight=weights[selected]
            )
            densities[name][group] = estimator.score_samples(standardized)
    scored, contrasts = [], []
    for i, row in enumerate(rows):
        scored.append(
            {"claim_id": row["claim_id"], "group": row["group"], "block_id": row["block_id"]}
            | {
                f"{name}_{group}_log_density": float(values[group][i])
                for name, values in densities.items()
                for group in GROUPS
            }
        )
    for first, second in combinations(GROUPS, 2):
        values = {name: groups[first] - groups[second] for name, groups in densities.items()}
        for name, delta in (
            ("cleanup", values["B"] - values["A"]),
            ("chunk_weight", values["C"] - values["B"]),
            ("total", values["C"] - values["A"]),
        ):
            contrasts.append(
                {
                    "pair": f"{first}_vs_{second}",
                    "change": name,
                    "median_absolute_log_contrast_change": float(np.median(np.abs(delta))),
                    "p95_absolute_log_contrast_change": float(np.quantile(np.abs(delta), 0.95)),
                    "sign_changed_fraction": float(
                        np.mean(
                            np.sign(values["B" if name == "cleanup" else "C"])
                            != np.sign(values["A" if name != "chunk_weight" else "B"])
                        )
                    ),
                }
            )
    write_rows(output / "density_scores.csv", scored)
    write_rows(output / "density_contrast_changes.csv", contrasts)
    return {
        "dimensions": frozen["dimensions"],
        "bandwidth": frozen["bandwidth"],
        "original_sampled_density_max_replay_error": replay_error,
        "sampling": (
            "A/B/C sensitivity KDEs fit all eligible claims, not the original equal-group "
            "subsamples. Common replay-verified frozen UMAP and bandwidth; no encoder, "
            "topic, representation-sampling or bandwidth refit."
        ),
    }


def run(corpus: Path, output: Path, review_path: Path) -> dict:
    corpus, output = corpus.resolve(), output.resolve()
    if output.exists() or output.is_relative_to(corpus) or corpus.is_relative_to(output):
        raise ValueError("Sensitivity output must be a new directory separate from its corpus")
    files = sorted(path for path in corpus.rglob("*") if path.is_file())
    hashes = {str(path.relative_to(corpus)): digest(path.read_bytes()) for path in files}
    rows, embeddings, basis = load_inputs(corpus, GROUPS)
    review = json.loads(review_path.read_text())
    output.mkdir(parents=True)
    shutil.copy2(review_path, output / "source_bound_review.json")
    cleaned_summary = prepare_cleaned(corpus, output / "cleaned", review)
    cleaned = analysis_rows(
        read_rows(output / "cleaned/claims.csv"),
        read_rows(output / "cleaned/complete_sources.csv"),
    )
    by_id = {row["claim_id"]: i for i, row in enumerate(rows)}
    retained = [by_id[row["claim_id"]] for row in cleaned]
    for row in cleaned:
        if row["text_sha256"] != rows[by_id[row["claim_id"]]]["text_sha256"]:
            raise ValueError("Sensitivity changed retained embedding text")
    variants = {"A": claim_weights(rows), "B": np.zeros(len(rows)), "C": np.zeros(len(rows))}
    variants["B"][retained] = claim_weights(cleaned)
    variants["C"][retained] = chunk_weights(cleaned)
    for name, weights in variants.items():
        for group in GROUPS:
            if not np.isclose(
                sum(weights[i] for i, r in enumerate(rows) if r["group"] == group), 1
            ):
                raise ValueError(f"Invalid {name}/{group} total mass")
    assignments = {
        row["claim_id"]: row["topic_id"] for row in read_rows(corpus / "topics/assignments.csv")
    }
    if set(assignments) != set(by_id):
        raise ValueError("Frozen issue assignments must exactly cover baseline claims")
    labels = {
        row["topic_id"]: row
        for row in json.loads((corpus / "topics/topic_labels.json").read_text())
    }
    blocks = defaultdict(list)
    for i, row in enumerate(rows):
        blocks[row["block_id"]].append(i)
    audit, candidates = [], []
    for block, indices in blocks.items():
        spans = Counter((rows[i]["source_start"], rows[i]["source_end"]) for i in indices)
        audit.append(
            {
                "block_id": block,
                "group": rows[indices[0]]["group"],
                "document_id": rows[indices[0]]["document_id"],
                "baseline_claims": len(indices),
                "cleaned_unique_claims": sum(variants["B"][i] > 0 for i in indices),
                "exact_evidence_spans": len(spans),
                "largest_shared_span_claim_count": max(spans.values()),
            }
        )
        similarities = embeddings[indices] @ embeddings[indices].T
        for first, second in zip(*np.where(np.triu(similarities >= 0.985, 1)), strict=True):
            left, right = rows[indices[first]], rows[indices[second]]
            candidates.append(
                {
                    "block_id": block,
                    "group": left["group"],
                    "claim_id": left["claim_id"],
                    "other_claim_id": right["claim_id"],
                    "cosine_similarity": float(similarities[first, second]),
                    "claim_text": left["claim_text"],
                    "other_claim_text": right["claim_text"],
                    "evidence": left["evidence"],
                    "other_evidence": right["evidence"],
                    "disposition": "source_excluded"
                    if any(variants["B"][by_id[r["claim_id"]]] == 0 for r in (left, right))
                    else "retain_distinct_or_uncertain",
                }
            )
    write_rows(output / "chunk_audit.csv", audit)
    write_rows(output / "duplicate_candidates.csv", candidates)
    subjects = subject_comparison(rows, variants, assignments, labels)
    write_rows(output / "subject_sensitivity.csv", subjects)
    write_rows(
        output / "claim_weights.csv",
        [
            {"claim_id": row["claim_id"], "group": row["group"], "block_id": row["block_id"]}
            | {f"{name}_weight": float(weights[i]) for name, weights in variants.items()}
            for i, row in enumerate(rows)
        ],
    )
    print("Audit and subject comparisons complete; replaying frozen density space", flush=True)
    density = frozen_density(corpus, rows, embeddings, variants, output)
    if hashes != {str(path.relative_to(corpus)): digest(path.read_bytes()) for path in files}:
        raise ValueError("Baseline files changed during sensitivity analysis")
    summary = {
        "status": "complete_fixed_representation_sensitivity_not_a_published_replacement",
        "baseline_claims": len(rows),
        "cleaned_unique_claims": len(cleaned),
        "baseline_blocks": len(blocks),
        "reviewed_candidate_pairs": len(candidates),
        "reviewed_semantic_duplicates": cleaned_summary["reviewed_within_chunk_duplicates"],
        "excluded_baseline_claims_by_group": dict(
            Counter(row["group"] for i, row in enumerate(rows) if variants["B"][i] == 0)
        ),
        "largest_displayed_chunk_weight_delta_pp": max(
            abs(float(row["chunk_weight_delta_pp"])) for row in subjects if row["displayed_subject"]
        ),
        "density": density,
        "baseline_basis": basis,
        "baseline_hashes": hashes,
        "review_sha256": digest(review_path.read_bytes()),
        "implementation_sha256": digest(Path(__file__).read_bytes()),
        "baseline_unchanged": True,
        "website_unchanged": True,
        "review_scope": review["scope"],
        "candidate_review": review["candidate_review"],
    }
    write_json(output / "summary.json", summary)
    with zipfile.ZipFile(output / "complete_sensitivity.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output.rglob("*")):
            if path.is_file() and path.name != "complete_sensitivity.zip":
                archive.write(path, path.relative_to(output))
        for name in ("claims.csv", "claims.jsonl", "complete_sources.csv", "blocks.csv"):
            archive.write(corpus / name, Path("baseline") / name)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.corpus, args.output, args.reviews)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in {"baseline_hashes", "baseline_basis"}},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
