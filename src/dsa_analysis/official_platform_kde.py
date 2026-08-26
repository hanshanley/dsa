from __future__ import annotations

import copy
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
    _looks_like_navigation_or_form,
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
MIN_PLATFORM_PASSAGES = 10


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

    loaded_rows = load_official_platform_segments(input_path)
    rows, coverage_rows, eligibility_audit = _prepare_platform_analysis_rows(
        loaded_rows,
        minimum_passages=MIN_PLATFORM_PASSAGES,
    )
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
    balanced_index_set = set(int(index) for index in balanced_indices)

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
        ).fit(
            standardized[fit_indices[group]],
            sample_weight=_document_balance_weights(rows, fit_indices[group]),
        )
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
                "included_in_balanced_map_sample": index in balanced_index_set,
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
        allow_single_cluster=False,
        cluster_selection_method="leaf",
    )
    sensitivity_rows = _clustering_sensitivity_rows(
        scored_rows,
        semantic_coordinates=standardized,
    )
    baseline_sensitivity = next(
        row
        for row in sensitivity_rows
        if row["cluster_selection_method"] == "leaf"
        and row["min_cluster_size"] == 10
        and row["min_samples"] == 3
    )
    if int(baseline_sensitivity["region_count"]) != len(region_rows):
        raise ValueError("Clustering sensitivity baseline does not match production regions")
    highlighted_count = sum(bool(row["zone"]) for row in scored_rows)
    hdbscan_noise_count = sum(
        bool(row["zone"]) and int(row.get("density_cluster_label", -1)) < 0
        for row in scored_rows
    )
    retained_region_count = len(region_rows)
    retained_region_passages = sum(int(region["segment_count"]) for region in region_rows)
    displayed_regions = [
        region for region in region_rows if bool(region["displayed_on_map"])
    ]
    displayed_region_passages = sum(
        int(region["segment_count"]) for region in displayed_regions
    )
    clustered_not_retained_count = (
        highlighted_count - hdbscan_noise_count - retained_region_passages
    )
    analysis_flow_rows = [
        {
            "stage": "loaded",
            "passage_count": eligibility_audit["loaded_passages"],
            "share_of_eligible": "",
            "description": "Official-platform passages entering the analysis screen.",
        },
        {
            "stage": "excluded_text_quality",
            "passage_count": eligibility_audit["text_quality_excluded_passages"],
            "share_of_eligible": "",
            "description": "Navigation, form, or boilerplate-like passages excluded.",
        },
        {
            "stage": "excluded_platform_coverage",
            "passage_count": eligibility_audit["coverage_gate_excluded_passages"],
            "share_of_eligible": "",
            "description": (
                f"Passages excluded because their platform had fewer than "
                f"{MIN_PLATFORM_PASSAGES} quality-screened passages."
            ),
        },
        {
            "stage": "eligible",
            "passage_count": len(scored_rows),
            "share_of_eligible": 1.0,
            "description": "Passages eligible for density scoring.",
        },
        {
            "stage": "unhighlighted",
            "passage_count": len(scored_rows) - highlighted_count,
            "share_of_eligible": (len(scored_rows) - highlighted_count) / len(scored_rows),
            "description": "Eligible passages outside the prespecified density-zone gates.",
        },
        {
            "stage": "highlighted",
            "passage_count": highlighted_count,
            "share_of_eligible": highlighted_count / len(scored_rows),
            "description": "Eligible passages passing a DSA, Democratic, or shared zone gate.",
        },
        {
            "stage": "hdbscan_noise",
            "passage_count": hdbscan_noise_count,
            "share_of_eligible": hdbscan_noise_count / len(scored_rows),
            "description": "Highlighted passages labeled as HDBSCAN noise.",
        },
        {
            "stage": "clustered_not_retained",
            "passage_count": clustered_not_retained_count,
            "share_of_eligible": clustered_not_retained_count / len(scored_rows),
            "description": (
                "Highlighted passages in clusters outside the retained top-six-per-zone "
                "or substantive-support gates."
            ),
        },
        {
            "stage": "retained_regions",
            "passage_count": retained_region_passages,
            "share_of_eligible": retained_region_passages / len(scored_rows),
            "description": "Highlighted passages assigned to the retained region inventory.",
        },
        {
            "stage": "displayed_regions",
            "passage_count": displayed_region_passages,
            "share_of_eligible": displayed_region_passages / len(scored_rows),
            "description": "Eligible passages in the six regions displayed on the public map.",
        },
    ]
    accounting_note = (
        f"Balanced map sample: {len(fit_indices['endorsed']):,} DSA + "
        f"{len(fit_indices['opponent']):,} Democratic passages  ·  "
        f"{highlighted_count:,} pass density-zone gates  ·  "
        f"{retained_region_passages:,} enter {retained_region_count} retained regions  ·  "
        f"{len(displayed_regions)} regions shown"
    )
    _write_csv(output_directory / "platform_coverage.csv", coverage_rows)
    _write_csv(output_directory / "analysis_flow.csv", analysis_flow_rows)
    _write_csv(output_directory / "clustering_sensitivity.csv", sensitivity_rows)
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
            "Equal-size map sample; platform-balanced KDE; exploratory HDBSCAN regions in the "
            "selected-dimensional semantic space."
        ),
        accounting_note=accounting_note,
        hot_label="More common in official DSA platforms",
        cold_label="More common in official Democratic platforms",
        unit_label="platforms",
    )

    document_counts = Counter(
        group
        for group, _ in {
            (row["group"], document_id.strip())
            for row in rows
            for document_id in row["support_unit_ids"].split(" | ")
            if document_id.strip()
        }
    )
    fit_document_counts = {
        output_group: len(
            {
                document_id.strip()
                for index in fit_indices[input_group]
                for document_id in rows[index]["support_unit_ids"].split(" | ")
                if document_id.strip()
            }
        )
        for output_group, input_group in (
            ("dsa", "endorsed"),
            ("democratic", "opponent"),
        )
    }
    fit_document_passage_ranges = {}
    for output_group, input_group in (
        ("dsa", "endorsed"),
        ("democratic", "opponent"),
    ):
        counts = Counter(
            document_id.strip()
            for index in fit_indices[input_group]
            for document_id in rows[index]["support_unit_ids"].split(" | ")
            if document_id.strip()
        )
        values = sorted(counts.values())
        fit_document_passage_ranges[output_group] = {
            "minimum": min(values),
            "median": float(np.median(values)),
            "maximum": max(values),
        }
    zone_counts = Counter(row["zone"] for row in scored_rows if row["zone"])
    level_counts = Counter(
        (row["group"], row["platform_level"])
        for row in coverage_rows
        if row["eligible"]
    )
    sensitivity_region_counts = [
        int(row["region_count"]) for row in sensitivity_rows
    ]
    sensitivity_assigned_counts = [
        int(row["assigned_passages"]) for row in sensitivity_rows
    ]
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
        "eligibility": {
            **eligibility_audit,
            "minimum_passages_per_platform": MIN_PLATFORM_PASSAGES,
            "eligible_level_counts": {
                "dsa": {
                    "national": level_counts[("dsa", "national")],
                    "subnational": level_counts[("dsa", "subnational")],
                },
                "democratic": {
                    "national": level_counts[("democratic", "national")],
                    "subnational": level_counts[("democratic", "subnational")],
                },
            },
        },
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
            "sampling": "equal-size deterministic document-stratified sample by group",
            "per_group_count": per_group_limit,
            "n_neighbors": 15,
            "metric": "cosine",
        },
        "kde": {
            "coordinate_standardization": "z-score fit on the balanced UMAP sample",
            "kernel": "gaussian",
            "bandwidth_rule": "Scott n^(-1/(d+4))",
            "fit_sampling": "equal-size deterministic document-stratified sample by group",
            "fit_counts": {
                "dsa": len(fit_indices["endorsed"]),
                "democratic": len(fit_indices["opponent"]),
            },
            "fit_document_counts": fit_document_counts,
            "fit_document_passage_ranges": fit_document_passage_ranges,
            "sample_weighting": (
                "inverse passage frequency within each contributing document; each platform "
                "has equal aggregate weight within its group"
            ),
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
            "unhighlighted_count": len(scored_rows) - highlighted_count,
        },
        "region_clustering": {
            "algorithm": "HDBSCAN",
            "space": f"{selected_dimensions}-dimensional standardized semantic representation",
            "metric": "euclidean",
            "min_cluster_size": 10,
            "min_samples": 3,
            "cluster_selection_method": "leaf",
            "allow_single_cluster": False,
            "retained_subregions_per_zone": 6,
            "displayed_subregions_per_zone": 2,
            "highlighted_passages": highlighted_count,
            "hdbscan_noise_passages": hdbscan_noise_count,
            "clustered_not_retained_passages": clustered_not_retained_count,
            "retained_region_count": retained_region_count,
            "retained_region_passages": retained_region_passages,
            "displayed_region_count": len(displayed_regions),
            "displayed_region_passages": displayed_region_passages,
            "sensitivity_specifications": len(sensitivity_rows),
            "sensitivity_region_cap_per_zone": 6,
            "sensitivity_region_count_range": [
                min(sensitivity_region_counts),
                max(sensitivity_region_counts),
            ],
            "sensitivity_assigned_passage_range": [
                min(sensitivity_assigned_counts),
                max(sensitivity_assigned_counts),
            ],
            "interpretation_status": "exploratory_parameter_sensitive",
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


def _prepare_platform_analysis_rows(
    rows: list[dict[str, str]],
    *,
    minimum_passages: int,
) -> tuple[list[dict[str, str]], list[dict[str, Any]], dict[str, Any]]:
    quality_rows = [
        row for row in rows if not _looks_like_navigation_or_form(row["text"])
    ]
    passage_counts = Counter(
        document_id.strip()
        for row in quality_rows
        for document_id in row["support_unit_ids"].split(" | ")
        if document_id.strip()
    )
    metadata: dict[str, dict[str, Any]] = {}
    for row in rows:
        platform_level = (
            "national"
            if "national" in row.get("source_type", "").lower()
            else "subnational"
        )
        for document_id in row["support_unit_ids"].split(" | "):
            document_id = document_id.strip()
            if not document_id:
                continue
            item = metadata.setdefault(
                document_id,
                {
                    "document_id": document_id,
                    "group": row["official_group"],
                    "platform_level": platform_level,
                    "organizations": set(),
                    "platform_types": set(),
                    "titles": set(),
                    "cycle_years": set(),
                },
            )
            for field, key in (
                ("organizations", "organizations"),
                ("source_type", "platform_types"),
                ("titles", "titles"),
                ("cycle_years", "cycle_years"),
            ):
                item[key].update(
                    value.strip()
                    for value in row.get(field, "").split(" | ")
                    if value.strip()
                )
    eligible_documents = {
        document_id
        for document_id, count in passage_counts.items()
        if count >= minimum_passages
    }
    eligible_rows = []
    for row in quality_rows:
        retained_document_ids = [
            document_id.strip()
            for document_id in row["support_unit_ids"].split(" | ")
            if document_id.strip() in eligible_documents
        ]
        if not retained_document_ids:
            continue
        retained = dict(row)
        retained["support_unit_ids"] = " | ".join(retained_document_ids)
        retained["context_document_ids"] = retained["support_unit_ids"]
        retained["candidate_unit_id"] = retained_document_ids[0]
        eligible_rows.append(retained)
    coverage_rows = []
    for document_id, item in sorted(
        metadata.items(),
        key=lambda pair: (pair[1]["group"], pair[0]),
    ):
        passage_count = passage_counts[document_id]
        eligible = document_id in eligible_documents
        coverage_rows.append(
            {
                "document_id": document_id,
                "group": item["group"],
                "platform_level": item["platform_level"],
                "organizations": " | ".join(sorted(item["organizations"])),
                "platform_types": " | ".join(sorted(item["platform_types"])),
                "titles": " | ".join(sorted(item["titles"])),
                "cycle_years": " | ".join(sorted(item["cycle_years"])),
                "quality_screened_passages": passage_count,
                "eligible": eligible,
                "exclusion_reason": (
                    ""
                    if eligible
                    else f"fewer_than_{minimum_passages}_quality_screened_passages"
                ),
            }
        )
    return (
        eligible_rows,
        coverage_rows,
        {
            "loaded_passages": len(rows),
            "text_quality_excluded_passages": len(rows) - len(quality_rows),
            "coverage_gate_excluded_passages": len(quality_rows) - len(eligible_rows),
            "eligible_passages": len(eligible_rows),
            "loaded_platforms": len(metadata),
            "eligible_platforms": len(eligible_documents),
            "excluded_platforms": len(metadata) - len(eligible_documents),
        },
    )


def _clustering_sensitivity_rows(
    rows: list[dict[str, Any]],
    *,
    semantic_coordinates: Any,
) -> list[dict[str, Any]]:
    output = []
    for selection_method in ("leaf", "eom"):
        for min_cluster_size in (8, 10, 15, 20):
            for min_samples in (2, 3, 5):
                regions = density_region_summaries(
                    copy.deepcopy(rows),
                    semantic_coordinates=semantic_coordinates,
                    max_regions_per_zone=6,
                    displayed_regions_per_zone=6,
                    min_cluster_size=min_cluster_size,
                    min_samples=min_samples,
                    min_candidate_count=2,
                    allow_single_cluster=False,
                    cluster_selection_method=selection_method,
                )
                counts = Counter(region["zone"] for region in regions)
                output.append(
                    {
                        "cluster_selection_method": selection_method,
                        "min_cluster_size": min_cluster_size,
                        "min_samples": min_samples,
                        "dsa_region_count": counts["hot"],
                        "democratic_region_count": counts["cold"],
                        "shared_region_count": counts["shared"],
                        "region_count": len(regions),
                        "assigned_passages": sum(
                            int(region["segment_count"]) for region in regions
                        ),
                    }
                )
    return output


def _platform_corpus_hash(rows: list[dict[str, str]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(row["analysis_segment_id"].encode())
        digest.update(b"\0")
        digest.update(row["support_unit_ids"].encode())
        digest.update(b"\0")
        digest.update(row["text"].encode())
        digest.update(b"\n")
    return digest.hexdigest()


def _document_balance_weights(
    rows: list[dict[str, str]],
    indices: list[int],
) -> list[float]:
    document_counts = Counter(
        document_id.strip()
        for index in indices
        for document_id in rows[index]["support_unit_ids"].split(" | ")
        if document_id.strip()
    )
    if not document_counts:
        raise ValueError("Official-platform KDE rows do not contain support-unit provenance")
    return [
        sum(
            1.0 / document_counts[document_id.strip()]
            for document_id in rows[index]["support_unit_ids"].split(" | ")
            if document_id.strip()
        )
        for index in indices
    ]


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
    eligibility = summary["eligibility"]
    clustering = summary["region_clustering"]
    dsa_levels = eligibility["eligible_level_counts"]["dsa"]
    democratic_levels = eligibility["eligible_level_counts"]["democratic"]
    text = f"""# Official-platform semantic density analysis

This analysis compares the recoverable official DSA and Democratic platform corpora separately
from candidate rhetoric.

## Corpus and balancing

- DSA: {document_counts["dsa"]} documents and {group_counts["dsa"]:,} passages.
- Democratic: {document_counts["democratic"]} documents and
  {group_counts["democratic"]:,} passages.
- Coverage composition: DSA has {dsa_levels["national"]} national and
  {dsa_levels["subnational"]} subnational platforms; Democratic coverage has
  {democratic_levels["national"]} national and {democratic_levels["subnational"]}
  subnational platforms.
- Eligibility gate: platforms need at least
  {eligibility["minimum_passages_per_platform"]} quality-screened passages;
  {eligibility["excluded_platforms"]} sparse documents and
  {eligibility["text_quality_excluded_passages"]} navigation/form passages were excluded.
- UMAP fit: {summary["umap_fit"]["per_group_count"]:,} passages per group, selected
  deterministically in round-robin order across documents.
- KDE fit: the same equal-sized samples, representing
  {summary["kde"]["fit_document_counts"]["dsa"]} DSA and
  {summary["kde"]["fit_document_counts"]["democratic"]} Democratic documents.
- KDE weights: inverse within-document passage frequency, giving each represented platform equal
  aggregate density weight within its group.
- Density space: {summary["selected_dimensions"]} dimensions; the 2D map is visualization only.

Equal sampling prevents the larger Democratic passage inventory from mechanically determining
the manifold or density estimates. It does not compensate for unavailable platforms or make
{document_counts["dsa"]} DSA documents equivalent in substantive coverage to
{document_counts["democratic"]} Democratic documents.

## Semantic regions

Regions are HDBSCAN communities in the selected-dimensional semantic space with single-cluster
fallback disabled to avoid treating an entire density zone as one broad semantic region.
Of {summary["retained_segments"]:,} eligible passages,
{clustering["highlighted_passages"]:,} pass the density-zone thresholds,
{clustering["hdbscan_noise_passages"]:,} of those are HDBSCAN noise, and
{clustering["clustered_not_retained_passages"]:,} enter clusters that do not pass the retained
top-six-per-zone and substantive-support gates.
{clustering["retained_region_passages"]:,} enter the {clustering["retained_region_count"]}
retained regions below. The public map shows
{clustering["displayed_region_count"]} regions covering
{clustering["displayed_region_passages"]:,} passages.

These subregions are exploratory rather than a stable topic taxonomy. Across
{clustering["sensitivity_specifications"]} prespecified HDBSCAN configurations, holding the
six-per-zone retention cap and substantive-support gates fixed, the number of retained regions
ranges from {clustering["sensitivity_region_count_range"][0]} to
{clustering["sensitivity_region_count_range"][1]}, and assigned passage counts range from
{clustering["sensitivity_assigned_passage_range"][0]:,} to
{clustering["sensitivity_assigned_passage_range"][1]:,}. See
`clustering_sensitivity.csv` for the full accounting and `platform_coverage.csv` for every
included or excluded platform. `analysis_flow.csv` reconciles every passage count.

| ID | Density zone | Passages | Platforms | HDBSCAN confidence | Distinctive terms | Representative exact passage |
|---|---|---:|---:|---:|---|---|
{chr(10).join(table_rows)}

Interpret overrepresentation as relative emphasis within the recoverable corpus, not universal
agreement, policy direction, or evidence that every candidate adopts an organization's platform.
The national/subnational coverage mismatch and parameter sensitivity preclude treating the region
inventory as a definitive partition of either organization's agenda.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
