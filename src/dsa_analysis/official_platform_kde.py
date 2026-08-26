from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sklearn.neighbors import KernelDensity
from sklearn.preprocessing import StandardScaler

from .narrative_analysis import hot_cold_characterization, umap_trustworthiness
from .provisional_kde import (
    MODEL_NAME,
    MODEL_REVISION,
    SEED,
    _encode_segments,
    _plot_density_fingerprint,
    _write_csv,
    balanced_kde_sample_indices,
    density_region_summaries,
    select_dimension_elbow,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "analysis" / "organizational_context_text_corpus.csv"
DEFAULT_OUTPUT = ROOT / "data" / "analysis" / "official_platform_gte_kde"
DEFAULT_FIGURE = ROOT / "figures" / "official_platform_gte_kde.png"
DEFAULT_REPORT = ROOT / "report" / "official_platform_kde_analysis.md"


@dataclass(frozen=True)
class OfficialPlatformKDEResult:
    retained_segments: int
    dsa_segments: int
    democratic_segments: int
    selected_dimensions: int
    output_directory: Path


def run_official_platform_kde(
    *,
    input_path: Path = DEFAULT_INPUT,
    output_directory: Path = DEFAULT_OUTPUT,
    figure_path: Path = DEFAULT_FIGURE,
    batch_size: int = 48,
    max_length: int = 256,
    force_embeddings: bool = False,
) -> OfficialPlatformKDEResult:
    import numpy as np
    import umap

    rows = load_official_platform_segments(input_path)
    group_counts = Counter(row["group"] for row in rows)
    if not group_counts["endorsed"] or not group_counts["opponent"]:
        raise ValueError("Official platform KDE requires both DSA and Democratic text")

    output_directory.mkdir(parents=True, exist_ok=True)
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_hash = _platform_corpus_hash(rows)
    embeddings_path = output_directory / "embeddings.npy"
    embedding_manifest_path = output_directory / "embedding_manifest.json"
    embeddings = None
    if not force_embeddings and embeddings_path.exists() and embedding_manifest_path.exists():
        manifest = json.loads(embedding_manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("corpus_hash") == corpus_hash
            and manifest.get("model_revision") == MODEL_REVISION
            and manifest.get("segment_count") == len(rows)
        ):
            embeddings = np.load(embeddings_path)
    if embeddings is None:
        embeddings = _encode_segments(
            [row["text"] for row in rows],
            batch_size=batch_size,
            max_length=max_length,
        )
        np.save(embeddings_path, embeddings)
        _write_json(
            embedding_manifest_path,
            {
                "model_name": MODEL_NAME,
                "model_revision": MODEL_REVISION,
                "normalization": "l2",
                "max_length": max_length,
                "segment_count": len(rows),
                "corpus_hash": corpus_hash,
            },
        )

    per_group_limit = min(group_counts.values())
    fit_indices = {
        group: balanced_kde_sample_indices(
            rows,
            group=group,
            limit=per_group_limit,
            seed=SEED,
        )
        for group in ("endorsed", "opponent")
    }
    balanced_indices = np.array(
        sorted(fit_indices["endorsed"] + fit_indices["opponent"]),
        dtype=int,
    )

    sweep_rows = []
    for dimension in (2, 5, 10, 20, 30):
        reducer = umap.UMAP(
            n_neighbors=15,
            min_dist=0.1,
            metric="cosine",
            n_components=dimension,
            random_state=SEED,
        )
        projection = reducer.fit_transform(embeddings[balanced_indices])
        trust = umap_trustworthiness(
            embeddings[balanced_indices].tolist(),
            projection.tolist(),
            n_neighbors=5,
        )["trustworthiness"]
        sweep_rows.append({"dimensions": dimension, "trustworthiness": float(trust)})
    selected_dimensions = select_dimension_elbow(sweep_rows)

    selected_reducer = umap.UMAP(
        n_neighbors=15,
        min_dist=0.1,
        metric="cosine",
        n_components=selected_dimensions,
        random_state=SEED,
    )
    selected_reducer.fit(embeddings[balanced_indices])
    selected_coordinates = selected_reducer.transform(embeddings)
    scaler = StandardScaler().fit(selected_coordinates[balanced_indices])
    standardized = scaler.transform(selected_coordinates)

    visualization_reducer = umap.UMAP(
        n_neighbors=15,
        min_dist=0.1,
        metric="cosine",
        n_components=2,
        random_state=SEED,
    )
    visualization_reducer.fit(embeddings[balanced_indices])
    visualization_coordinates = visualization_reducer.transform(embeddings)

    log_densities: dict[str, Any] = {}
    bandwidths: dict[str, float] = {}
    for group in ("endorsed", "opponent"):
        count = len(fit_indices[group])
        bandwidth = count ** (-1.0 / (selected_dimensions + 4))
        bandwidths[group] = bandwidth
        kde = KernelDensity(
            bandwidth=bandwidth,
            kernel="gaussian",
            algorithm="ball_tree",
            leaf_size=40,
        ).fit(standardized[fit_indices[group]])
        log_densities[group] = kde.score_samples(standardized)

    groups = np.array([row["group"] for row in rows])
    log1p_dsa = np.logaddexp(0.0, log_densities["endorsed"])
    log1p_democratic = np.logaddexp(0.0, log_densities["opponent"])
    scores = log1p_dsa - log1p_democratic
    raw_log_ratios = log_densities["endorsed"] - log_densities["opponent"]
    dsa_cutoff = float(np.quantile(scores[groups == "endorsed"], 0.75))
    democratic_cutoff = float(np.quantile(scores[groups == "opponent"], 0.25))
    joint_log_density = np.minimum(
        log_densities["endorsed"],
        log_densities["opponent"],
    )
    shared_score_cutoff = float(np.quantile(np.abs(scores), 0.25))
    shared_candidates = np.abs(scores) <= shared_score_cutoff
    shared_density_cutoff = float(np.quantile(joint_log_density[shared_candidates], 0.5))

    scored_rows = []
    zone_documents = []
    for index, row in enumerate(rows):
        score = float(scores[index])
        zone = ""
        if (
            abs(score) <= shared_score_cutoff
            and joint_log_density[index] >= shared_density_cutoff
        ):
            zone = "shared"
        elif row["group"] == "endorsed" and score >= dsa_cutoff:
            zone = "hot"
        elif row["group"] == "opponent" and score <= democratic_cutoff:
            zone = "cold"
        scored = dict(row)
        scored.update(
            {
                "umap_x": float(visualization_coordinates[index, 0]),
                "umap_y": float(visualization_coordinates[index, 1]),
                "dsa_log_density": float(log_densities["endorsed"][index]),
                "democratic_log_density": float(log_densities["opponent"][index]),
                "raw_log_density_ratio": float(raw_log_ratios[index]),
                "log1p_density_ratio": score,
                "joint_log_density": float(joint_log_density[index]),
                "zone": zone,
            }
        )
        scored_rows.append(scored)
        if zone:
            zone_documents.append({"group": zone, "text": row["text"]})

    characterization = hot_cold_characterization(
        zone_documents,
        positive_group="hot",
        negative_group="cold",
        min_document_frequency=3,
        top_n=30,
        quantiles=(0.1, 0.2, 0.3, 0.4),
    )
    region_rows = density_region_summaries(
        scored_rows,
        semantic_coordinates=standardized,
        min_cluster_size=10,
        min_samples=3,
        min_candidate_count=2,
    )
    _write_csv(output_directory / "segment_density_scores.csv", scored_rows)
    _write_csv(output_directory / "umap_dimension_sweep.csv", sweep_rows)
    _write_csv(output_directory / "hot_cold_terms.csv", characterization["rows"])
    _write_csv(output_directory / "density_regions.csv", region_rows)
    _plot_density_fingerprint(
        scored_rows,
        region_rows=region_rows,
        figure_path=figure_path,
        endorsed_cutoff=dsa_cutoff,
        opponent_cutoff=democratic_cutoff,
        title="Where official DSA and Democratic platforms differ — and overlap",
        map_title="Semantic map of official platform language",
        subtitle=(
            "UMAP and KDE are fit on equal, document-balanced samples from each group; "
            "cards summarize HDBSCAN regions in the selected-dimensional space."
        ),
        hot_label="More common in official DSA platforms",
        cold_label="More common in official Democratic platforms",
        unit_label="platforms",
    )

    document_counts = Counter(
        row["group"]
        for row in {
            (row["group"], row["candidate_unit_id"]): row for row in rows
        }.values()
    )
    zone_counts = Counter(row["zone"] for row in scored_rows if row["zone"])
    summary = {
        "status": "recoverable_platform_corpus",
        "warning": (
            "Equal-sample KDE controls passage-volume imbalance but cannot correct for missing "
            "platforms or the smaller number of recoverable DSA documents."
        ),
        "input_path": str(input_path.relative_to(ROOT)),
        "corpus_hash": corpus_hash,
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "seed": SEED,
        "retained_segments": len(rows),
        "group_counts": {
            "dsa": group_counts["endorsed"],
            "democratic": group_counts["opponent"],
        },
        "document_counts": {
            "dsa": document_counts["endorsed"],
            "democratic": document_counts["opponent"],
        },
        "dimension_sweep": sweep_rows,
        "selected_dimensions": selected_dimensions,
        "dimension_selection_rule": (
            "smallest tested dimension within 0.005 trustworthiness of the maximum"
        ),
        "umap_fit": {
            "sampling": "equal-size deterministic document-balanced sample by group",
            "per_group_count": per_group_limit,
            "n_neighbors": 15,
            "metric": "cosine",
        },
        "kde": {
            "coordinate_standardization": "z-score fit on the balanced UMAP sample",
            "kernel": "gaussian",
            "bandwidth_rule": "Scott n^(-1/(d+4))",
            "fit_sampling": "equal-size deterministic document-balanced sample by group",
            "fit_counts": {
                "dsa": len(fit_indices["endorsed"]),
                "democratic": len(fit_indices["opponent"]),
            },
            "bandwidths": {
                "dsa": bandwidths["endorsed"],
                "democratic": bandwidths["opponent"],
            },
        },
        "zones": {
            "dsa_hot_quantile": 0.75,
            "dsa_hot_cutoff": dsa_cutoff,
            "democratic_cold_quantile": 0.25,
            "democratic_cold_cutoff": democratic_cutoff,
            "shared_absolute_score_quantile": 0.25,
            "shared_absolute_score_cutoff": shared_score_cutoff,
            "shared_joint_density_quantile": 0.5,
            "shared_joint_density_cutoff": shared_density_cutoff,
            "counts": dict(zone_counts),
        },
        "region_clustering": {
            "algorithm": "HDBSCAN",
            "space": f"{selected_dimensions}-dimensional standardized semantic representation",
            "metric": "euclidean",
            "min_cluster_size": 10,
            "min_samples": 3,
            "cluster_selection_method": "eom",
            "retained_subregions_per_zone": 6,
            "displayed_subregions_per_zone": 2,
        },
        "density_regions": region_rows,
    }
    _write_json(output_directory / "summary.json", summary)
    _write_report(summary, region_rows, DEFAULT_REPORT)
    return OfficialPlatformKDEResult(
        retained_segments=len(rows),
        dsa_segments=group_counts["endorsed"],
        democratic_segments=group_counts["opponent"],
        selected_dimensions=selected_dimensions,
        output_directory=output_directory,
    )


def load_official_platform_segments(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    rows = []
    for row in source_rows:
        source_group = row.get("group", "").strip()
        if source_group not in {"dsa", "democratic"}:
            continue
        document_ids = [
            value.strip()
            for value in row.get("context_document_ids", "").split(" | ")
            if value.strip()
        ]
        if not document_ids or not row.get("text", "").strip():
            continue
        rows.append(
            {
                "analysis_segment_id": row["corpus_segment_id"],
                "group": "endorsed" if source_group == "dsa" else "opponent",
                "candidate_unit_id": document_ids[0],
                "support_unit_ids": row.get("context_document_ids", ""),
                "candidate_name": row.get("organizations", ""),
                "source_type": row.get("platform_types", ""),
                "source_url": row.get("source_urls", ""),
                "segment_locator": row.get("locators", ""),
                "text": row["text"].strip(),
                "token_count": row.get("token_count", ""),
                "official_group": source_group,
                "context_document_ids": row.get("context_document_ids", ""),
                "context_categories": row.get("context_categories", ""),
                "organizations": row.get("organizations", ""),
                "titles": row.get("titles", ""),
                "cycle_years": row.get("cycle_years", ""),
            }
        )
    return rows


def _platform_corpus_hash(rows: list[dict[str, str]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(row["analysis_segment_id"].encode())
        digest.update(b"\0")
        digest.update(row["text"].encode())
        digest.update(b"\n")
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_report(
    summary: dict[str, Any],
    regions: list[dict[str, Any]],
    path: Path,
) -> None:
    labels = {
        "hot": "DSA-overrepresented",
        "cold": "Democratic-overrepresented",
        "shared": "Shared high-density",
    }
    table_rows = []
    for region in regions:
        excerpt = str(region["representative_excerpt"]).replace("|", "\\|")
        terms = str(region["top_terms"]).replace("_", " ").replace(" | ", ", ")
        table_rows.append(
            (
                f'| {region["region_id"]} | {labels[str(region["zone"])]} | '
                f'{region["segment_count"]} | {region["candidate_count"]} | '
                f'{float(region["mean_membership_probability"]):.2f} | {terms} | '
                f'{excerpt} |'
            )
        )
    document_counts = summary["document_counts"]
    group_counts = summary["group_counts"]
    text = f"""# Official-platform semantic density analysis

This analysis compares the recoverable official DSA and Democratic platform corpora separately
from candidate rhetoric.

## Corpus and balancing

- DSA: {document_counts["dsa"]} documents and {group_counts["dsa"]:,} passages.
- Democratic: {document_counts["democratic"]} documents and
  {group_counts["democratic"]:,} passages.
- UMAP fit: {summary["umap_fit"]["per_group_count"]:,} passages per group, selected
  deterministically in round-robin order across documents.
- KDE fit: the same equal-sized, document-balanced samples.
- Density space: {summary["selected_dimensions"]} dimensions; the 2D map is visualization only.

Equal sampling prevents the larger Democratic passage inventory from mechanically determining
the manifold or density estimates. It does not compensate for unavailable platforms or make
{document_counts["dsa"]} DSA documents equivalent in substantive coverage to
{document_counts["democratic"]} Democratic documents.

## Semantic regions

Regions are HDBSCAN communities in the selected-dimensional semantic space. The public map shows
the two strongest regions per zone; this table retains up to six.

| ID | Density zone | Passages | Platforms | HDBSCAN confidence | Distinctive terms | Representative exact passage |
|---|---|---:|---:|---:|---|---|
{chr(10).join(table_rows)}

Interpret overrepresentation as relative emphasis within the recoverable corpus, not universal
agreement, policy direction, or evidence that every candidate adopts an organization's platform.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
