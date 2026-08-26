from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import random
import re
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from .narrative_analysis import hot_cold_characterization, umap_trustworthiness

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "processed" / "candidate_document_analysis_segments.csv"
DEFAULT_METADATA = ROOT / "data" / "processed" / "candidate_document_metadata.csv"
DEFAULT_OUTPUT = ROOT / "data" / "analysis" / "provisional_gte_kde"
DEFAULT_FIGURE = ROOT / "figures" / "provisional_gte_kde.png"
DEFAULT_REPORT = ROOT / "report" / "provisional_kde_analysis.md"
MODEL_NAME = "Alibaba-NLP/gte-multilingual-base"
MODEL_REVISION = "9bbca17d9273fd0d03d5725c7a4b0f6b45142062"
SEED = 1729


@dataclass(frozen=True)
class ProvisionalKDEResult:
    retained_segments: int
    endorsed_segments: int
    opponent_segments: int
    selected_dimensions: int
    output_directory: Path


def run_provisional_kde(
    *,
    input_path: Path = DEFAULT_INPUT,
    output_directory: Path = DEFAULT_OUTPUT,
    figure_path: Path = DEFAULT_FIGURE,
    batch_size: int = 48,
    max_length: int = 256,
    sweep_sample_size: int = 5_000,
    kde_fit_per_group: int = 5_000,
    force_embeddings: bool = False,
) -> ProvisionalKDEResult:
    import numpy as np
    import umap
    from sklearn.neighbors import KernelDensity
    from sklearn.preprocessing import StandardScaler

    rows = load_eligible_segments(input_path)
    if not rows:
        raise ValueError("No eligible endorsed/opponent segments were found")
    output_directory.mkdir(parents=True, exist_ok=True)
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    corpus_hash = _corpus_hash(rows)
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

    rng = np.random.default_rng(SEED)
    sample_indices = np.sort(
        rng.choice(len(rows), size=min(sweep_sample_size, len(rows)), replace=False)
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
        projection = reducer.fit_transform(embeddings[sample_indices])
        trust = umap_trustworthiness(
            embeddings[sample_indices].tolist(),
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
    selected_coordinates = selected_reducer.fit_transform(embeddings)
    standardized = StandardScaler().fit_transform(selected_coordinates)

    visualization_reducer = umap.UMAP(
        n_neighbors=15,
        min_dist=0.1,
        metric="cosine",
        n_components=2,
        random_state=SEED,
    )
    visualization_coordinates = visualization_reducer.fit_transform(embeddings)

    groups = np.array([row["group"] for row in rows])
    fit_indices: dict[str, list[int]] = {}
    log_densities: dict[str, Any] = {}
    bandwidths: dict[str, float] = {}
    for group in ("endorsed", "opponent"):
        fit_indices[group] = balanced_kde_sample_indices(
            rows,
            group=group,
            limit=kde_fit_per_group,
            seed=SEED,
        )
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

    log1p_endorsed = np.logaddexp(0.0, log_densities["endorsed"])
    log1p_opponent = np.logaddexp(0.0, log_densities["opponent"])
    scores = log1p_endorsed - log1p_opponent
    raw_log_ratios = log_densities["endorsed"] - log_densities["opponent"]
    endorsed_cutoff = float(np.quantile(scores[groups == "endorsed"], 0.75))
    opponent_cutoff = float(np.quantile(scores[groups == "opponent"], 0.25))
    joint_log_density = np.minimum(
        log_densities["endorsed"],
        log_densities["opponent"],
    )
    shared_score_cutoff = float(np.quantile(np.abs(scores), 0.25))
    shared_candidates = np.abs(scores) <= shared_score_cutoff
    shared_density_cutoff = float(np.quantile(joint_log_density[shared_candidates], 0.5))

    scored_rows = []
    hot_cold_documents = []
    for index, row in enumerate(rows):
        score = float(scores[index])
        zone = ""
        if (
            abs(score) <= shared_score_cutoff
            and joint_log_density[index] >= shared_density_cutoff
        ):
            zone = "shared"
        elif row["group"] == "endorsed" and score >= endorsed_cutoff:
            zone = "hot"
        elif row["group"] == "opponent" and score <= opponent_cutoff:
            zone = "cold"
        scored = dict(row)
        scored.update(
            {
                "umap_x": float(visualization_coordinates[index, 0]),
                "umap_y": float(visualization_coordinates[index, 1]),
                "endorsed_log_density": float(log_densities["endorsed"][index]),
                "opponent_log_density": float(log_densities["opponent"][index]),
                "raw_log_density_ratio": float(raw_log_ratios[index]),
                "log1p_density_ratio": score,
                "joint_log_density": float(joint_log_density[index]),
                "zone": zone,
            }
        )
        scored_rows.append(scored)
        if zone:
            hot_cold_documents.append({"group": zone, "text": row["text"]})

    characterization = hot_cold_characterization(
        hot_cold_documents,
        positive_group="hot",
        negative_group="cold",
        min_document_frequency=5,
        top_n=30,
        quantiles=(0.1, 0.2, 0.3, 0.4),
    )
    region_rows = density_region_summaries(
        scored_rows,
        semantic_coordinates=standardized,
    )
    _write_csv(output_directory / "segment_density_scores.csv", scored_rows)
    _write_csv(output_directory / "umap_dimension_sweep.csv", sweep_rows)
    _write_csv(output_directory / "hot_cold_terms.csv", characterization["rows"])
    _write_csv(output_directory / "density_regions.csv", region_rows)
    _plot_density_fingerprint(
        scored_rows,
        region_rows=region_rows,
        figure_path=figure_path,
        endorsed_cutoff=endorsed_cutoff,
        opponent_cutoff=opponent_cutoff,
    )

    group_counts = Counter(row["group"] for row in rows)
    zone_counts = Counter(row["zone"] for row in scored_rows if row["zone"])
    summary = {
        "status": "provisional",
        "warning": (
            "The full-text sufficiency audit still fails. Results describe the currently "
            "recoverable segmented corpus and must not be treated as a complete census."
        ),
        "input_path": str(input_path.relative_to(ROOT)),
        "input_sha256": _file_hash(input_path),
        "corpus_hash": corpus_hash,
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "seed": SEED,
        "filter": {
            "roles": ["endorsed", "opponent", "unopposed"],
            "minimum_token_count": 20,
            "excluded_flags": ["boilerplate_flag"],
            "excluded_source_types": ["filing", "official_election_source"],
            "deduplication": (
                "one exact-text segment per candidate, group, and election cycle; "
                "repeated state-race provenance retained"
            ),
        },
        "retained_segments": len(rows),
        "group_counts": dict(group_counts),
        "candidate_counts": dict(
            Counter(
                row["group"]
                for row in {
                    (item["group"], item["candidate_unit_id"]): item
                    for item in rows
                }.values()
            )
        ),
        "dimension_sweep": sweep_rows,
        "selected_dimensions": selected_dimensions,
        "dimension_selection_rule": (
            "smallest tested dimension within 0.005 trustworthiness of the maximum"
        ),
        "kde": {
            "coordinate_standardization": "joint z-score",
            "kernel": "gaussian",
            "bandwidth_rule": "Scott n^(-1/(d+4))",
            "fit_sampling": "deterministic round-robin candidate-balanced sample",
            "fit_counts": {key: len(value) for key, value in fit_indices.items()},
            "bandwidths": bandwidths,
        },
        "zones": {
            "endorsed_hot_quantile": 0.75,
            "endorsed_hot_cutoff": endorsed_cutoff,
            "opponent_cold_quantile": 0.25,
            "opponent_cold_cutoff": opponent_cutoff,
            "shared_absolute_score_quantile": 0.25,
            "shared_absolute_score_cutoff": shared_score_cutoff,
            "shared_joint_density_quantile": 0.5,
            "shared_joint_density_cutoff": shared_density_cutoff,
            "counts": dict(zone_counts),
        },
        "density_regions": region_rows,
        "region_clustering": {
            "algorithm": "HDBSCAN",
            "space": f"{selected_dimensions}-dimensional standardized semantic representation",
            "metric": "euclidean",
            "min_cluster_size": 60,
            "min_samples": 10,
            "cluster_selection_method": "eom",
            "allow_single_cluster": True,
            "retained_subregions_per_zone": 6,
            "displayed_subregions_per_zone": 2,
            "noise_points_by_zone": {
                zone: sum(
                    row.get("zone") == zone
                    and int(row.get("density_cluster_label", -1)) == -1
                    for row in scored_rows
                )
                for zone in ("hot", "cold", "shared")
            },
            "selection": (
                "mean HDBSCAN membership probability, support, and density-ratio strength"
            ),
        },
        "top_hot_terms": characterization["hot_terms"],
        "top_cold_terms": characterization["cold_terms"],
        "outputs": {
            "scores": str((output_directory / "segment_density_scores.csv").relative_to(ROOT)),
            "sweep": str((output_directory / "umap_dimension_sweep.csv").relative_to(ROOT)),
            "terms": str((output_directory / "hot_cold_terms.csv").relative_to(ROOT)),
            "regions": str((output_directory / "density_regions.csv").relative_to(ROOT)),
            "figure": str(figure_path.relative_to(ROOT)),
            "report": str(DEFAULT_REPORT.relative_to(ROOT)),
        },
    }
    _write_json(output_directory / "summary.json", summary)
    _write_kde_report(DEFAULT_REPORT, summary)
    return ProvisionalKDEResult(
        retained_segments=len(rows),
        endorsed_segments=group_counts["endorsed"],
        opponent_segments=group_counts["opponent"],
        selected_dimensions=selected_dimensions,
        output_directory=output_directory,
    )


def load_eligible_segments(
    path: Path,
    metadata_path: Path = DEFAULT_METADATA,
) -> list[dict[str, str]]:
    metadata = {}
    if metadata_path.exists():
        with metadata_path.open(encoding="utf-8", newline="") as handle:
            metadata = {
                row["document_id"]: row
                for row in csv.DictReader(handle)
                if row.get("document_id")
            }
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            role = row.get("role", "")
            if role not in {"endorsed", "opponent", "unopposed"}:
                continue
            if _is_true(row.get("boilerplate_flag")):
                continue
            if int(row.get("token_count") or 0) < 20:
                continue
            if row.get("source_type", "").strip() in {
                "filing",
                "official_election_source",
            }:
                continue
            text = (row.get("text") or "").strip()
            if not text:
                continue
            if _looks_like_navigation_or_form(text):
                continue
            retained = dict(row)
            retained["group"] = "endorsed" if role in {"endorsed", "unopposed"} else "opponent"
            document = metadata.get(row.get("document_id", ""), {})
            election_date = (
                document.get("election_date", "").strip()
                or row.get("election_date", "").strip()
            )
            cycle = election_date[:4] if election_date else "unknown"
            retained["cycle"] = cycle
            retained["candidate_unit_id"] = f"{cycle}:{row.get('candidate_slug', '').strip()}"
            text_hash = (
                row.get("exact_duplicate_hash", "").strip()
                or row.get("sha256", "").strip()
                or hashlib.sha256(text.encode("utf-8")).hexdigest()
            )
            grouped[
                (
                    retained["group"],
                    cycle,
                    row.get("candidate_slug", "").strip(),
                    text_hash,
                )
            ].append(retained)

    rows = []
    for duplicates in grouped.values():
        retained = dict(duplicates[0])
        retained["race_ids"] = " | ".join(
            sorted({row.get("race_id", "").strip() for row in duplicates if row.get("race_id")})
        )
        retained["document_ids"] = " | ".join(
            sorted(
                {
                    row.get("document_id", "").strip()
                    for row in duplicates
                    if row.get("document_id")
                }
            )
        )
        retained["analysis_segment_ids"] = " | ".join(
            sorted(
                {
                    row.get("analysis_segment_id", "").strip()
                    for row in duplicates
                    if row.get("analysis_segment_id")
                }
            )
        )
        retained["provenance_row_count"] = str(len(duplicates))
        rows.append(retained)
    return sorted(
        rows,
        key=lambda row: (
            row["group"],
            row["candidate_unit_id"],
            row.get("sha256", ""),
            row.get("analysis_segment_id", ""),
        ),
    )


def select_dimension_elbow(
    rows: Sequence[dict[str, float | int]], tolerance: float = 0.005
) -> int:
    if not rows:
        raise ValueError("Dimension sweep rows must not be empty")
    maximum = max(float(row["trustworthiness"]) for row in rows)
    eligible = [
        int(row["dimensions"])
        for row in rows
        if maximum - float(row["trustworthiness"]) <= tolerance
    ]
    return min(eligible)


def balanced_kde_sample_indices(
    rows: Sequence[dict[str, str]],
    *,
    group: str,
    limit: int,
    seed: int,
) -> list[int]:
    by_candidate: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        if row["group"] == group:
            unit_ids = [
                value.strip()
                for value in row.get("support_unit_ids", "").split(" | ")
                if value.strip()
            ]
            if not unit_ids:
                unit_ids = [
                    row.get("candidate_unit_id")
                    or f"{row.get('race_id', '')}:{row.get('candidate_slug', '')}"
                ]
            for unit_id in unit_ids:
                by_candidate[unit_id].append(index)
    if not by_candidate:
        raise ValueError(f"No rows available for KDE group {group!r}")
    rng = random.Random(seed)
    for indices in by_candidate.values():
        rng.shuffle(indices)
    candidates = sorted(by_candidate)
    rng.shuffle(candidates)
    selected = []
    selected_set: set[int] = set()
    offset = 0
    while len(selected) < limit:
        added = False
        for candidate in candidates:
            indices = by_candidate[candidate]
            if offset < len(indices):
                index = indices[offset]
                added = True
                if index in selected_set:
                    continue
                selected.append(index)
                selected_set.add(index)
                if len(selected) == limit:
                    break
        if not added:
            break
        offset += 1
    return sorted(selected)


def _encode_segments(texts: Sequence[str], *, batch_size: int, max_length: int) -> Any:
    import torch
    from sentence_transformers import SentenceTransformer

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = SentenceTransformer(
        MODEL_NAME,
        revision=MODEL_REVISION,
        trust_remote_code=True,
        device=device,
    )
    model.max_seq_length = max_length
    return model.encode(
        list(texts),
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )


def _plot_density_fingerprint(
    rows: Sequence[dict[str, Any]],
    *,
    region_rows: Sequence[dict[str, Any]],
    figure_path: Path,
    endorsed_cutoff: float,
    opponent_cutoff: float,
    title: str = "Where DSA-endorsed candidates and other Democrats differ — and overlap",
    map_title: str = "Semantic map of campaign language",
    subtitle: str = (
        "Highlighted regions summarize recurring language in the recoverable campaign-text "
        "corpus; cards show locally distinctive terms and a central source passage."
    ),
    hot_label: str = "More common in DSA-endorsed text",
    cold_label: str = "More common in other Democrats' text",
    unit_label: str = "candidates",
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    x = np.array([float(row["umap_x"]) for row in rows])
    y = np.array([float(row["umap_y"]) for row in rows])
    displayed_regions = [
        region for region in region_rows if bool(region.get("displayed_on_map", True))
    ]
    card_rows, card_columns, width_ratios = _density_fingerprint_layout(
        len(displayed_regions)
    )
    figure = plt.figure(figsize=(18, 10.5), facecolor="#FAFAF8")
    grid = figure.add_gridspec(1, 2, width_ratios=width_ratios, wspace=0.08)
    axis = figure.add_subplot(grid[0, 0])
    card_grid = grid[0, 1].subgridspec(
        card_rows,
        card_columns,
        hspace=0.13,
        wspace=0.10,
    )
    axis.set_facecolor("#F4F4F1")
    axis.scatter(
        x,
        y,
        color="#C9CBC8",
        s=2.5,
        alpha=0.15,
        linewidths=0,
        rasterized=True,
    )
    zone_styles = {
        "hot": ("#C84A32", "#FBEDE8", hot_label),
        "cold": ("#2F6F98", "#EAF2F7", cold_label),
        "shared": ("#8A7525", "#F5F1DE", "Common to both groups"),
    }
    for zone, (color, _, label) in zone_styles.items():
        zone_rows = [row for row in rows if row.get("zone") == zone]
        if not zone_rows:
            continue
        axis.scatter(
            [float(row["umap_x"]) for row in zone_rows],
            [float(row["umap_y"]) for row in zone_rows],
            color=color,
            s=5.5,
            alpha=0.55,
            linewidths=0,
            rasterized=True,
            label=label,
        )
    for region in displayed_regions:
        color = zone_styles[str(region["zone"])][0]
        axis.text(
            float(region["centroid_x"]),
            float(region["centroid_y"]),
            str(region["region_id"]),
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            color="white",
            bbox={
                "boxstyle": "round,pad=0.28",
                "facecolor": color,
                "edgecolor": "white",
                "linewidth": 0.8,
                "alpha": 0.95,
            },
        )
    x_low, x_high = np.quantile(x, [0.003, 0.997])
    y_low, y_high = np.quantile(y, [0.003, 0.997])
    x_pad = (x_high - x_low) * 0.04
    y_pad = (y_high - y_low) * 0.04
    axis.set_xlim(x_low - x_pad, x_high + x_pad)
    axis.set_ylim(y_low - y_pad, y_high + y_pad)
    axis.set_title(map_title, fontsize=17, loc="left", pad=14)
    axis.set_xlabel("UMAP dimension 1")
    axis.set_ylabel("UMAP dimension 2")
    axis.legend(
        loc="upper left",
        frameon=True,
        facecolor="white",
        edgecolor="#DDDDDD",
        fontsize=9,
        markerscale=2,
    )
    axis.grid(color="white", linewidth=0.8, alpha=0.8)
    axis.text(
        0.01,
        0.01,
        (
            "Nearby points contain semantically similar passages. "
            "Gray points are not assigned to a highlighted region.\n"
            "The two-dimensional map is for visualization only; extreme outliers are clipped."
        ),
        transform=axis.transAxes,
        fontsize=8.5,
        color="#555555",
    )
    for index, region in enumerate(displayed_regions):
        column = index % card_columns
        row_index = index // card_columns
        card = figure.add_subplot(card_grid[row_index, column])
        card.set_xticks([])
        card.set_yticks([])
        zone = str(region["zone"])
        color, background, zone_label = zone_styles[zone]
        card.set_facecolor(background)
        for spine in card.spines.values():
            spine.set_color(color)
            spine.set_linewidth(1.2)
        card.text(
            0.055,
            0.91,
            str(region["region_id"]),
            transform=card.transAxes,
            color="white",
            fontsize=9.5,
            fontweight="bold",
            va="center",
            ha="left",
            bbox={
                "boxstyle": "round,pad=0.24",
                "facecolor": color,
                "edgecolor": color,
                "linewidth": 0,
            },
        )
        card.text(
            0.14 if card_columns == 1 else 0.17,
            0.91,
            textwrap.fill(zone_label, width=56 if card_columns == 1 else 31),
            transform=card.transAxes,
            color=color,
            fontsize=10.5 if card_columns == 1 else 9.5,
            fontweight="bold",
            va="center",
            linespacing=0.95,
        )
        card.text(
            0.055,
            0.74,
            "DISTINCTIVE LANGUAGE",
            transform=card.transAxes,
            color="#666666",
            fontsize=7.5,
            fontweight="bold",
            va="top",
        )
        card.text(
            0.055,
            0.67,
            textwrap.fill(
                str(region["top_terms"]).replace("_", " ").replace(" | ", " · "),
                width=68 if card_columns == 1 else 42,
            ),
            transform=card.transAxes,
            color="#252525",
            fontsize=9.5,
            va="top",
        )
        candidate = str(region.get("representative_candidate", "")).strip()
        source_label = str(region.get("representative_source_type", "")).replace("_", " ")
        card.text(
            0.055,
            0.51,
            "REPRESENTATIVE PASSAGE",
            transform=card.transAxes,
            color="#666666",
            fontsize=7.5,
            fontweight="bold",
            va="top",
        )
        card.text(
            0.055,
            0.455,
            textwrap.fill(
                " · ".join(part for part in (candidate, source_label) if part),
                width=76 if card_columns == 1 else 55,
            ),
            transform=card.transAxes,
            color="#555555",
            fontsize=7.3,
            fontweight="bold",
            va="top",
            linespacing=0.95,
        )
        card.text(
            0.055,
            0.355,
            textwrap.fill(
                f'“{region["representative_excerpt"]}”',
                width=72 if card_columns == 1 else 49,
            ),
            transform=card.transAxes,
            color="#3F3F3F",
            fontsize=8.7,
            va="top",
            style="italic",
        )
        card.text(
            0.055,
            0.08,
            (
                f'{int(region["segment_count"]):,} passages from '
                f'{int(region["candidate_count"]):,} {unit_label}'
            ),
            transform=card.transAxes,
            color="#5F5F5F",
            fontsize=8.5,
            va="bottom",
        )
    figure.suptitle(
        title,
        fontsize=21,
        y=0.985,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.947,
        subtitle,
        ha="center",
        fontsize=11,
        color="#555555",
    )
    figure.subplots_adjust(top=0.90, bottom=0.07, left=0.05, right=0.985)
    figure.savefig(figure_path, dpi=220)
    plt.close(figure)


def _density_fingerprint_layout(
    displayed_region_count: int,
) -> tuple[int, int, tuple[float, float]]:
    if displayed_region_count <= 0:
        return 1, 1, (1.45, 0.85)
    if displayed_region_count <= 3:
        return displayed_region_count, 1, (1.35, 0.90)
    return (displayed_region_count + 1) // 2, 2, (1.08, 1.0)


def density_region_summaries(
    rows: Sequence[dict[str, Any]],
    *,
    max_regions_per_zone: int = 6,
    displayed_regions_per_zone: int = 2,
    min_cluster_size: int = 60,
    min_samples: int = 10,
    min_candidate_count: int = 20,
    allow_single_cluster: bool = True,
    cluster_selection_method: str = "eom",
    semantic_coordinates: Any | None = None,
) -> list[dict[str, Any]]:
    import numpy as np
    from sklearn.cluster import HDBSCAN
    from sklearn.preprocessing import StandardScaler

    prefixes = {"hot": "D", "cold": "M", "shared": "S"}
    output = []
    row_indices = {id(row): index for index, row in enumerate(rows)}
    for zone in ("hot", "cold", "shared"):
        zone_rows = [row for row in rows if row.get("zone") == zone]
        if not zone_rows:
            continue
        visualization_coordinates = np.array(
            [[float(row["umap_x"]), float(row["umap_y"])] for row in zone_rows]
        )
        if semantic_coordinates is None:
            clustering_coordinates = StandardScaler().fit_transform(
                visualization_coordinates
            )
        else:
            clustering_coordinates = np.array(
                [semantic_coordinates[row_indices[id(row)]] for row in zone_rows]
            )
        effective_min_cluster_size = min(
            min_cluster_size,
            max(2, len(zone_rows) // 2),
        )
        effective_min_samples = min(
            min_samples,
            max(1, effective_min_cluster_size - 1),
        )
        if len(zone_rows) < 4 or np.allclose(
            np.ptp(clustering_coordinates, axis=0),
            0.0,
        ):
            labels = np.zeros(len(zone_rows), dtype=int)
            probabilities = np.ones(len(zone_rows), dtype=float)
        else:
            clusterer = HDBSCAN(
                min_cluster_size=effective_min_cluster_size,
                min_samples=effective_min_samples,
                metric="euclidean",
                cluster_selection_method=cluster_selection_method,
                allow_single_cluster=allow_single_cluster,
                n_jobs=1,
                copy=False,
            )
            labels = clusterer.fit_predict(clustering_coordinates)
            probabilities = clusterer.probabilities_
        for index, row in enumerate(zone_rows):
            row["density_cluster_label"] = int(labels[index])
            row["density_cluster_probability"] = round(
                float(probabilities[index]),
                6,
            )
        clusters = []
        zone_score_scale = max(
            (
                abs(float(row["log1p_density_ratio"]))
                for row in zone_rows
            ),
            default=1.0,
        )
        for label in sorted(set(int(value) for value in labels if int(value) >= 0)):
            member_indices = [
                index
                for index, assigned in enumerate(labels)
                if assigned == label
            ]
            members = [zone_rows[index] for index in member_indices]
            candidate_count = len(
                {
                    unit.strip()
                    for row in members
                    for unit in str(
                        row.get("support_unit_ids")
                        or row.get("candidate_slug")
                        or row.get("candidate_name")
                        or row.get("candidate_unit_id", "")
                    ).split(" | ")
                    if unit.strip()
                }
            )
            if candidate_count < min_candidate_count:
                continue
            member_coordinates = clustering_coordinates[member_indices]
            centroid = np.mean(member_coordinates, axis=0)
            mean_distance = float(
                np.mean(np.linalg.norm(member_coordinates - centroid, axis=1))
            )
            coherence = 1.0 / (1.0 + mean_distance)
            mean_score = sum(float(row["log1p_density_ratio"]) for row in members) / len(members)
            strength = abs(mean_score) / max(zone_score_scale, 1e-12)
            membership_probability = float(np.mean(probabilities[member_indices]))
            terms = _distinctive_region_terms(members, zone_rows)
            if not _cluster_terms_look_substantive(terms):
                continue
            clusters.append(
                {
                    "members": members,
                    "mean_score": mean_score,
                    "coherence": coherence,
                    "candidate_count": candidate_count,
                    "terms": terms,
                    "membership_probability": membership_probability,
                    "rank_score": (
                        membership_probability
                        * math.log1p(len(members))
                        * (1.0 + strength)
                    ),
                }
            )
        clusters.sort(key=lambda cluster: float(cluster["rank_score"]), reverse=True)
        for rank, cluster in enumerate(clusters[:max_regions_per_zone], start=1):
            members = cluster["members"]
            terms = cluster["terms"]
            if semantic_coordinates is None:
                evidence_coordinates = np.array(
                    [[float(row["umap_x"]), float(row["umap_y"])] for row in members]
                )
            else:
                evidence_coordinates = np.array(
                    [semantic_coordinates[row_indices[id(row)]] for row in members]
                )
            excerpt, representative = _representative_region_evidence(
                members,
                terms,
                evidence_coordinates,
            )
            region_id = f"{prefixes[zone]}{rank}"
            for row in members:
                row["density_region_id"] = region_id
            output.append(
                {
                    "region_id": region_id,
                    "zone": zone,
                    "displayed_on_map": rank <= displayed_regions_per_zone,
                    "segment_count": len(members),
                    "candidate_count": int(cluster["candidate_count"]),
                    "mean_log1p_density_ratio": round(
                        float(cluster["mean_score"]),
                        12,
                    ),
                    "semantic_coherence": round(
                        float(cluster["coherence"]),
                        6,
                    ),
                    "mean_membership_probability": round(
                        float(cluster["membership_probability"]),
                        6,
                    ),
                    "centroid_x": round(
                        sum(float(row["umap_x"]) for row in members) / len(members),
                        6,
                    ),
                    "centroid_y": round(
                        sum(float(row["umap_y"]) for row in members) / len(members),
                        6,
                    ),
                    "top_terms": " | ".join(terms),
                    "representative_excerpt": excerpt,
                    "representative_candidate": str(
                        representative.get("candidate_name", "")
                    ),
                    "representative_source_type": str(
                        representative.get("source_type", "")
                    ),
                }
            )
    return output


def _cluster_terms_look_substantive(terms: Sequence[str]) -> bool:
    noise_terms = {
        "attached",
        "aug",
        "casino",
        "donate",
        "elected",
        "event",
        "facebook",
        "fppc",
        "interac",
        "instagram",
        "join",
        "july",
        "menu",
        "min",
        "newsletter",
        "opinion",
        "payout",
        "podcast",
        "read",
        "search",
        "schedule",
        "season",
        "sign",
        "story",
        "subscribe",
        "team",
        "football",
        "open",
        "twitter",
        "wallet",
        "withdrawal",
        "volunteer",
        "caucuse",
    }
    normalized_terms = {term.casefold().replace("-", "_") for term in terms}
    return len(normalized_terms & noise_terms) < 3


def _distinctive_region_terms(
    region_rows: Sequence[dict[str, Any]],
    zone_rows: Sequence[dict[str, Any]],
    *,
    top_n: int = 5,
) -> list[str]:
    from .text_analysis import tokenize

    excluded = {
        "about",
        "across",
        "actually",
        "after",
        "also",
        "all",
        "because",
        "before",
        "being",
        "could",
        "did",
        "does",
        "doing",
        "don't",
        "during",
        "each",
        "even",
        "every",
        "from",
        "going",
        "had",
        "has",
        "have",
        "he",
        "he's",
        "here",
        "hers",
        "herself",
        "him",
        "himself",
        "how",
        "hope",
        "i'd",
        "i'll",
        "i'm",
        "i've",
        "into",
        "it",
        "it's",
        "itself",
        "just",
        "kind",
        "know",
        "like",
        "lot",
        "me",
        "mine",
        "more",
        "most",
        "my",
        "myself",
        "our",
        "ours",
        "ourselves",
        "really",
        "should",
        "some",
        "than",
        "that",
        "that's",
        "their",
        "theirs",
        "them",
        "themselves",
        "there",
        "there's",
        "these",
        "they",
        "they're",
        "they've",
        "thing",
        "think",
        "this",
        "those",
        "through",
        "together",
        "under",
        "value",
        "very",
        "want",
        "was",
        "we",
        "we're",
        "we've",
        "were",
        "what",
        "what's",
        "when",
        "where",
        "which",
        "who",
        "who's",
        "whom",
        "why",
        "will",
        "with",
        "you",
        "you'd",
        "you'll",
        "you're",
        "you've",
        "your",
        "yours",
        "yourself",
        "yourselves",
        "applause",
        "adopted",
        "approved",
        "august",
        "assembly",
        "board",
        "campaign",
        "candidate",
        "courtesy",
        "contact",
        "course",
        "convention",
        "country",
        "city",
        "county",
        "date",
        "democrat",
        "democratic",
        "district",
        "dsa",
        "editor",
        "election",
        "email",
        "experience",
        "forward",
        "endorsement",
        "endorsed",
        "facebook",
        "form",
        "her",
        "his",
        "information",
        "issue",
        "linkedin",
        "local",
        "lemon",
        "mayor",
        "make",
        "majority",
        "major",
        "member",
        "meet",
        "name",
        "need",
        "neither",
        "new",
        "news",
        "one",
        "order",
        "other",
        "page",
        "people",
        "platform",
        "politic",
        "positive",
        "primary",
        "program",
        "race",
        "ran",
        "read",
        "receive",
        "received",
        "run",
        "running",
        "said",
        "schedule",
        "seat",
        "she",
        "sport",
        "state",
        "share",
        "support",
        "something",
        "senator",
        "tapper",
        "thank",
        "taxe",
        "top",
        "true",
        "vote",
        "vice",
        "website",
        "window",
        "win",
        "work",
        "would",
        "get",
        "say",
        "year",
        "yeah",
        "newsletter",
        "nextdoor",
        "office",
        "org",
        "questionnaire",
        "press",
        "provide",
        "release",
        "photo",
        "pdf",
        "reddit",
        "san",
        "bash",
        "bluesky",
        "com",
        "believe",
        "including",
    }
    for row in region_rows:
        excluded.update(tokenize(str(row.get("candidate_name", ""))))
    region_documents = [
        set(tokenize(str(row.get("text", "")))) - excluded for row in region_rows
    ]
    region_row_ids = {id(row) for row in region_rows}
    background_rows = [row for row in zone_rows if id(row) not in region_row_ids]
    background_documents = [
        set(tokenize(str(row.get("text", "")))) - excluded for row in background_rows
    ]
    region_counts = Counter(term for document in region_documents for term in document)
    background_counts = Counter(term for document in background_documents for term in document)
    minimum_count = max(3, len(region_documents) // 100)
    scored = []
    for term, count in region_counts.items():
        if count < minimum_count or len(term) < 3 or term.isdigit():
            continue
        region_share = count / max(len(region_documents), 1)
        background_share = background_counts[term] / max(len(background_documents), 1)
        score = region_share * math.log(
            (region_share + 0.002) / (background_share + 0.002)
        )
        scored.append((score, region_share, term))
    scored.sort(reverse=True)
    return [term for _, _, term in scored[:top_n]]


def _representative_region_evidence(
    rows: Sequence[dict[str, Any]],
    terms: Sequence[str],
    coordinates: Any,
) -> tuple[str, dict[str, Any]]:
    import numpy as np

    from .text_analysis import tokenize

    term_set = set(terms)
    centroid = np.mean(coordinates, axis=0)
    distances = np.linalg.norm(coordinates - centroid, axis=1)
    distance_scale = max(float(np.quantile(distances, 0.9)), 1e-9)
    candidates = []
    for row_index, row in enumerate(rows):
        raw_text = str(row.get("text", ""))
        raw_normalized = raw_text.casefold()
        if any(
            marker in raw_normalized
            for marker in ("<abbr title=", "<h4>", "<h5>")
        ):
            continue
        text = _clean_excerpt_text(raw_text)
        spans = [
            span.strip()
            for span in re.split(r"(?<=[.!?;])\s+|\n+", text)
            if 10 <= len(span.split()) <= 60
            and not _looks_like_navigation_or_form(span)
            and not _looks_like_table_of_contents(span)
        ]
        if (
            not spans
            and not _looks_like_navigation_or_form(text)
            and not _looks_like_table_of_contents(text)
        ):
            spans = [text]
        for span in spans:
            normalized = " ".join(span.split())
            if not normalized:
                continue
            term_share = len(term_set & set(tokenize(normalized))) / max(len(term_set), 1)
            source_quality = _representative_source_quality(
                str(row.get("source_type", ""))
            )
            centrality = 1.0 - min(float(distances[row_index]) / distance_scale, 1.0)
            speaker_penalty = float(
                bool(re.match(r"^(?:MODERATOR|TAPPER|LEMON|BASH|QUESTION):", normalized))
            )
            candidates.append(
                (
                    term_share,
                    (
                        0.55 * centrality
                        + 0.10 * source_quality
                        - speaker_penalty
                    ),
                    centrality,
                    row,
                    normalized,
                )
            )
    if not candidates:
        return (
            "[No high-confidence representative passage; inspect the region CSV.]",
            {},
        )
    _, _, _, representative, excerpt = max(
        candidates,
        key=lambda candidate: candidate[:3],
    )
    excerpt = _trim_representative_excerpt(excerpt, term_set)
    if "debate" in str(representative.get("source_type", "")).casefold():
        representative = dict(representative)
        representative["candidate_name"] = "Multi-candidate debate"
    return excerpt, representative


def _trim_representative_excerpt(
    excerpt: str,
    terms: set[str],
    *,
    max_length: int = 190,
) -> str:
    if len(excerpt) <= max_length:
        return excerpt
    lowered = excerpt.casefold()
    positions = [lowered.find(term.casefold()) for term in terms]
    positions = [position for position in positions if position >= 0]
    center = min(positions) if positions else 0
    start = max(0, center - max_length // 3)
    end = min(len(excerpt), start + max_length)
    if end - start < max_length:
        start = max(0, end - max_length)
    if start:
        next_space = excerpt.find(" ", start)
        start = next_space + 1 if next_space >= 0 else start
    if end < len(excerpt):
        previous_space = excerpt.rfind(" ", start, end)
        end = previous_space if previous_space > start else end
    snippet = excerpt[start:end].strip()
    if start:
        snippet = "..." + snippet.lstrip(" ,;:-")
    if end < len(excerpt):
        snippet = snippet.rstrip(" ,;:-") + "..."
    return snippet


def _clean_excerpt_text(text: str) -> str:
    cleaned = html.unescape(text)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return " ".join(cleaned.split())


def _representative_source_quality(source_type: str) -> int:
    normalized = source_type.casefold()
    if any(
        marker in normalized
        for marker in ("platform", "policy", "questionnaire", "campaign_page")
    ):
        return 2
    if any(marker in normalized for marker in ("statement", "interview", "op_ed")):
        return 1
    return 0


def _looks_like_navigation_or_form(text: str) -> bool:
    from urllib.parse import unquote_plus

    normalized = " ".join(unquote_plus(text).casefold().split())
    if "\ufffd" in normalized:
        return True
    visible_characters = [character for character in normalized if not character.isspace()]
    if visible_characters:
        ascii_share = sum(character.isascii() for character in visible_characters) / len(
            visible_characters
        )
        if ascii_share < 0.8:
            return True
    if normalized.startswith("do you commit to ") and normalized.endswith("?"):
        return True
    if re.search(r"(?:\b\d+\s+){5,}", normalized):
        return True
    navigation_tokens = re.findall(r"[a-z]+", normalized)
    if sum(
        navigation_tokens[index] == navigation_tokens[index + 1]
        for index in range(len(navigation_tokens) - 1)
    ) >= 2:
        return True
    return any(
        marker in normalized
        for marker in (
            "(back to top)",
            "candidate questionnaire",
            "candidate q&a",
            "candidate roundups",
            "california form 700",
            "check back for more information",
            "conversation …",
            "by elections committee",
            "email facebook linkedin",
            "<abbr title=",
            "<h4>",
            "<h5>",
            "name of source (not an acronym)",
            "news story election",
            "newsletter subscribe",
            "opens in new window",
            "politics + government",
            "politics & government",
            "political party:",
            "read more issue",
            "schedule d income",
            "schedule summary (required)",
            "schedules attached",
            "servpro of",
            "sign up for the free",
            "skip to main content",
            "stay in the know",
            "subscribe issues archive",
            "table of contents",
            "thank you for your interest in completing this question",
            "this is a search field",
            "total number of pages including this cover page",
            "instant casino",
            "house office building washington",
            "phone fax",
            "withdrawal methods payout",
            "interac e-transfer",
            "roundup of the week's stories",
            "new yorkers get",
            "why are you running for county council",
        )
    )


def _looks_like_table_of_contents(text: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    title_case_share = sum(word[0].isupper() for word in words) / max(len(words), 1)
    return (
        len(words) >= 10
        and title_case_share >= 0.5
        and not re.search(r"[.!?]", text)
    )


def _representative_candidate(
    rows: Sequence[dict[str, Any]],
    excerpt: str,
) -> str:
    for row in rows:
        normalized = " ".join(str(row.get("text", "")).split())
        if excerpt.removesuffix("...")[:100] in normalized:
            return str(row.get("candidate_name", ""))
    return ""


def _write_kde_report(path: Path, summary: dict[str, Any]) -> None:
    zone_labels = {
        "hot": "DSA-overrepresented",
        "cold": "Other-Democrat-overrepresented",
        "shared": "Shared high-density",
    }
    region_lines = []
    for region in summary["density_regions"]:
        excerpt = str(region["representative_excerpt"]).replace("|", "\\|")
        terms = str(region["top_terms"]).replace("_", " ").replace(" | ", ", ")
        region_lines.append(
            "| {region_id} | {zone} | {map_status} | {segments} | {candidates} | "
            "{confidence} | {terms} | "
            "{candidate}: {excerpt} |".format(
                region_id=region["region_id"],
                zone=zone_labels[str(region["zone"])],
                map_status="Yes" if region["displayed_on_map"] else "No",
                segments=region["segment_count"],
                candidates=region["candidate_count"],
                confidence=f'{float(region["mean_membership_probability"]):.2f}',
                terms=terms,
                candidate=region["representative_candidate"] or "Representative segment",
                excerpt=excerpt,
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""# Provisional GTE KDE region analysis

The KDE contains **{summary["retained_segments"]}** passages after deduplicating repeated text
within each candidate and election year:
**{summary["group_counts"]["endorsed"]}** from DSA-endorsed candidates and
**{summary["group_counts"]["opponent"]}** from other Democrats. Density estimation is performed in
**{summary["selected_dimensions"]} dimensions**; the two-dimensional map is used only for
visualization.

![Labeled KDE regions](../figures/provisional_gte_kde.png)

## Interpreting the labeled regions

- **D regions** are spatial groupings among DSA-endorsed segments above the endorsed-group
  upper-quartile density-ratio cutoff.
- **M regions** are semantically coherent groupings among other-Democrat passages below that
  group's lower-quartile density-ratio cutoff.
- **S regions** are high-joint-density areas with small absolute density differences. They
  represent semantic overlap, not proof of identical positions.
- HDBSCAN identifies variable-shape clusters in the selected 10-dimensional UMAP representation
  (`min_cluster_size=60`, `min_samples=10`, Euclidean metric, EOM selection). Noise points remain
  unassigned. The table retains up to six substantive, sufficiently supported regions per zone;
  the map displays the top two per category to remain legible.
- Terms are locally distinctive document-prevalence terms from the underlying subregion text.
  Examples are extractive source passages, not generated paraphrases.

| Region | Interpretation | On map | Passages | Candidates | HDBSCAN confidence | Distinctive terms | Representative source text |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
{chr(10).join(region_lines)}

## Limits

This is a descriptive analysis of the recoverable corpus. Region labels summarize the text
actually present in each density area; they do not imply a complete nationwide census, causal
importance, or agreement merely because both groups occupy a shared region.
""",
        encoding="utf-8",
    )


def _corpus_hash(rows: Iterable[dict[str, str]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(row["analysis_segment_id"].encode())
        digest.update(b"\0")
        digest.update(row["text"].encode())
        digest.update(b"\n")
    return digest.hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0])
    seen = set(fieldnames)
    for row in rows[1:]:
        for field in row:
            if field not in seen:
                seen.add(field)
                fieldnames.append(field)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
