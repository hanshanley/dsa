"""Caucus-specific numerical fitting with the existing pinned semantic methods."""

from __future__ import annotations

import json
from collections import Counter
from itertools import permutations
from pathlib import Path

import numpy as np
from dsa_caucus_analysis import CLAIMS, CORPUS, RESULTS, caucus_claim_rows

from dsa_analysis.national_claim_analysis import audit_claim_lengths
from dsa_analysis.national_claim_topics import (
    NOISE,
    claim_weights,
    fit_topics,
    topic_evidence,
)
from dsa_analysis.national_platform_kde import encode
from dsa_analysis.national_platforms import digest, read_rows, write_json, write_rows
from dsa_analysis.provisional_kde import (
    SEED,
    balanced_kde_sample_indices,
    select_dimension_elbow,
)

SETTINGS = {
    "seed": SEED,
    "pca_components": 50,
    "min_cluster_sizes": [30, 50, 100],
    "min_samples": [5, 10],
    "minimum_density_coverage": 0.5,
    "kmeans_clusters": [6, 9, 12, 15],
    "silhouette_sample": 2000,
    "balanced_refits": 2,
    "keywords": 10,
    "representatives": 26,
    "max_claims_per_bundle": 2,
}


def attention_tables(rows: list[dict], assignments: list[str]) -> tuple[list[dict], list[dict]]:
    if len(rows) != len(assignments) or not rows:
        raise ValueError("Attention tables require exactly one assignment per eligible claim")
    groups = sorted({row["group"] for row in rows})
    topics = sorted(set(assignments) | {NOISE})
    weights = claim_weights(rows)
    mass, counts, documents = Counter(), Counter(), {}
    for row, topic, weight in zip(rows, assignments, weights, strict=True):
        key = row["group"], topic
        mass[key] += float(weight)
        counts[key] += 1
        documents.setdefault(key, set()).add(row["document_id"])
    shares = [
        {
            "group": group,
            "topic_id": topic,
            "attention_share": mass[group, topic],
            "claims": counts[group, topic],
            "supporting_documents": len(documents.get((group, topic), set())),
            "denominator_documents": len(
                {row["document_id"] for row in rows if row["group"] == group}
            ),
        }
        for group in groups
        for topic in topics
    ]
    ratios = []
    for topic in topics:
        comparisons = [(first, [second]) for first, second in permutations(groups, 2)]
        comparisons += [(group, [other for other in groups if other != group]) for group in groups]
        for first, baseline in comparisons:
            numerator = mass[first, topic]
            denominator = float(np.mean([mass[group, topic] for group in baseline]))
            ratios.append(
                {
                    "topic_id": topic,
                    "group": first,
                    "baseline_groups": ",".join(baseline),
                    "comparison": "pairwise" if len(baseline) == 1 else "equal_caucus_rest",
                    "attention_share": numerator,
                    "baseline_attention_share": denominator,
                    "attention_share_ratio": numerator / denominator if denominator else "",
                    "difference_percentage_points": 100 * (numerator - denominator),
                    "status": "defined" if denominator else "undefined_zero_denominator",
                    "single_document_snapshot": True,
                }
            )
    return shares, ratios


def fit_densities(rows: list[dict], embeddings: np.ndarray, directory: Path) -> dict:
    import umap
    from sklearn.manifold import trustworthiness
    from sklearn.neighbors import KernelDensity
    from sklearn.preprocessing import StandardScaler

    counts = Counter(row["group"] for row in rows)
    if min(counts.values()) < 10:
        raise ValueError("Shared caucus KDE requires at least ten eligible claims per group")
    limit = min(counts.values())
    samples = {
        group: balanced_kde_sample_indices(
            [{**row, "support_unit_ids": row["bundle_id"]} for row in rows],
            group=group,
            limit=limit,
            seed=SEED,
        )
        for group in sorted(counts)
    }
    indices = sorted(index for values in samples.values() for index in values)
    sweep, reducers = [], {}
    for dimension in (2, 5, 10, 20, 30):
        if dimension >= len(indices) - 1:
            continue
        reducer = umap.UMAP(
            n_neighbors=min(15, len(indices) - 1),
            n_components=dimension,
            min_dist=0.1,
            metric="cosine",
            random_state=SEED,
            n_jobs=1,
        )
        projection = reducer.fit_transform(embeddings[indices])
        sweep.append(
            {
                "dimensions": dimension,
                "trustworthiness": float(
                    trustworthiness(
                        embeddings[indices],
                        projection,
                        n_neighbors=min(5, (len(indices) - 1) // 2),
                        metric="cosine",
                    )
                ),
            }
        )
        reducers[dimension] = reducer
    selected = select_dimension_elbow(sweep)
    coordinates = reducers[selected].transform(embeddings)
    standardized = StandardScaler().fit(coordinates[indices]).transform(coordinates)
    visual = reducers[2].transform(embeddings)
    bandwidth = limit ** (-1 / (selected + 4))
    densities = {
        group: KernelDensity(kernel="gaussian", bandwidth=bandwidth)
        .fit(
            standardized[values],
            sample_weight=claim_weights([rows[index] for index in values]),
        )
        .score_samples(standardized)
        for group, values in samples.items()
    }
    sampled = set(indices)
    write_rows(
        directory / "density_coordinates.csv",
        [
            {
                "claim_id": row["claim_id"],
                "group": row["group"],
                "umap_x": float(visual[index, 0]),
                "umap_y": float(visual[index, 1]),
                "sampled": index in sampled,
                **{
                    f"{group}_log_density": float(values[index])
                    for group, values in densities.items()
                },
            }
            for index, row in enumerate(rows)
        ],
    )
    write_rows(directory / "dimension_sweep.csv", sweep)
    write_rows(
        directory / "density_sampling.csv",
        [
            {"group": group, "claim_id": rows[index]["claim_id"]}
            for group, values in samples.items()
            for index in values
        ],
    )
    np.savez(
        directory / "density_space.npz",
        ordered_claim_ids=np.array([row["claim_id"] for row in rows]),
        standardized_coordinates=standardized,
    )
    return {
        "dimensions": selected,
        "bandwidth": bandwidth,
        "sampled_claims_per_caucus": limit,
        "seed": SEED,
        "density_space": "Common standardized selected-dimensional UMAP; 2D is display only",
        "interpretation": "Language density, not agreement, ideological distance or membership",
    }


def analyze() -> dict:
    extraction = json.loads((CLAIMS / "extraction_summary.json").read_text())
    if extraction["status"] not in {"complete", "complete_with_exclusions"}:
        raise ValueError("Caucus numerical analysis requires all extraction blocks attempted")
    sources = read_rows(CORPUS / "complete_sources.csv")
    rows = caucus_claim_rows(read_rows(CLAIMS / "claims.csv"), sources)
    expected = {row["caucus"] for row in sources}
    if {row["group"] for row in rows} != expected:
        raise ValueError("An authoring caucus has no eligible claims; do not silently omit it")
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_rows(RESULTS / "analysis_claims.csv", rows)
    tokens = audit_claim_lengths(rows, RESULTS)
    embeddings, reused = encode(rows, RESULTS, batch_size=16)
    assignments, coordinates, summary, candidates, sensitivity = fit_topics(
        rows, embeddings, SETTINGS
    )
    keywords, examples = topic_evidence(rows, embeddings, assignments, SETTINGS)
    shares, ratios = attention_tables(rows, assignments)
    write_rows(
        RESULTS / "topic_assignments.csv",
        [
            {"claim_id": row["claim_id"], "group": row["group"], "topic_id": topic}
            for row, topic in zip(rows, assignments, strict=True)
        ],
    )
    for name, values in (
        ("topic_keywords", keywords),
        ("topic_representatives", examples),
        ("topic_selection", candidates),
        ("topic_balanced_sensitivity", sensitivity),
        ("attention_shares", shares),
        ("attention_share_ratios", ratios),
    ):
        write_rows(RESULTS / f"{name}.csv", values)
    np.save(RESULTS / "topic_pca_coordinates.npy", coordinates)
    density = fit_densities(rows, embeddings, RESULTS)
    result = {
        "status": "numerical_fit_complete_labels_and_source_review_pending",
        "eligible_claims": len(rows),
        "claims_by_caucus": dict(Counter(row["group"] for row in rows)),
        "documents": len(sources),
        "topic_fit": summary,
        "density_fit": density,
        "tokenization": tokens,
        "embeddings_reused": reused,
        "settings": SETTINGS,
        "extraction": extraction,
        "attention_estimand": "Equal documents within caucus; all eligible claims in denominator",
        "ratio_estimand": "Unrounded attention shares; no smoothing; zero denominator undefined",
        "input_hashes": {
            "claims": digest((CLAIMS / "claims.csv").read_bytes()),
            "sources": digest((CORPUS / "complete_sources.csv").read_bytes()),
            "embeddings": digest((RESULTS / "embeddings.npy").read_bytes()),
            "comparison_implementation": digest(Path(__file__).read_bytes()),
        },
        "result_hashes": {
            path.name: digest(path.read_bytes())
            for path in sorted(RESULTS.iterdir())
            if path.suffix in {".csv", ".npy", ".npz"}
        },
    }
    write_json(RESULTS / "summary.json", result)
    return result
