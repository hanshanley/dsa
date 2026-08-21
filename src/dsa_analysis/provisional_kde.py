from __future__ import annotations

import csv
import hashlib
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
    region_rows = density_region_summaries(scored_rows)
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
            candidate_unit_id = row.get("candidate_unit_id") or (
                f"{row.get('race_id', '')}:{row.get('candidate_slug', '')}"
            )
            by_candidate[candidate_unit_id].append(index)
    if not by_candidate:
        raise ValueError(f"No rows available for KDE group {group!r}")
    rng = random.Random(seed)
    for indices in by_candidate.values():
        rng.shuffle(indices)
    candidates = sorted(by_candidate)
    rng.shuffle(candidates)
    selected = []
    offset = 0
    while len(selected) < limit:
        added = False
        for candidate in candidates:
            indices = by_candidate[candidate]
            if offset < len(indices):
                selected.append(indices[offset])
                added = True
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
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    x = np.array([float(row["umap_x"]) for row in rows])
    y = np.array([float(row["umap_y"]) for row in rows])
    score = np.array([float(row["log1p_density_ratio"]) for row in rows])
    bound = max(abs(float(np.quantile(score, 0.01))), abs(float(np.quantile(score, 0.99))))
    figure = plt.figure(figsize=(18, 10))
    grid = figure.add_gridspec(1, 2, width_ratios=(1.75, 1.45), wspace=0.08)
    axis = figure.add_subplot(grid[0, 0])
    summary_axis = figure.add_subplot(grid[0, 1])
    scatter = axis.scatter(
        x,
        y,
        c=score,
        cmap="coolwarm",
        vmin=-bound,
        vmax=bound,
        s=2.5,
        alpha=0.32,
        linewidths=0,
        rasterized=True,
    )
    zone_styles = {
        "hot": ("#C94F36", "DSA-overrepresented"),
        "cold": ("#356D91", "Opponent-overrepresented"),
        "shared": ("#8A7A39", "Shared high-density"),
    }
    for zone, (color, label) in zone_styles.items():
        zone_rows = [row for row in rows if row.get("zone") == zone]
        if not zone_rows:
            continue
        axis.scatter(
            [float(row["umap_x"]) for row in zone_rows],
            [float(row["umap_y"]) for row in zone_rows],
            color=color,
            s=4,
            alpha=0.38,
            linewidths=0,
            rasterized=True,
            label=label,
        )
    for region in region_rows:
        color = zone_styles[str(region["zone"])][0]
        axis.text(
            float(region["centroid_x"]),
            float(region["centroid_y"]),
            str(region["region_id"]),
            ha="center",
            va="center",
            fontsize=9,
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
    axis.set_title("Where DSA-endorsed and opponent texts concentrate", fontsize=16)
    axis.set_xlabel("UMAP 1 (visualization only)")
    axis.set_ylabel("UMAP 2 (visualization only)")
    colorbar = figure.colorbar(scatter, ax=axis)
    colorbar.set_label("log(1 + DSA density) - log(1 + opponent density)")
    axis.legend(loc="upper right", frameon=False, fontsize=8)
    axis.text(
        0.01,
        0.01,
        (
            f"DSA cutoff: {endorsed_cutoff:.3g} | Opponent cutoff: "
            f"{opponent_cutoff:.3g}\nLabels summarize underlying segments; gray areas are not "
            "classified as distinctive regions."
        ),
        transform=axis.transAxes,
        fontsize=8,
    )
    summary_axis.axis("off")
    summary_axis.set_title(
        "Text character of labeled regions",
        loc="left",
        fontsize=15,
        pad=12,
    )
    for index, region in enumerate(region_rows):
        column = index % 2
        row_index = index // 2
        x_position = column * 0.51
        y_position = 0.94 - row_index * 0.31
        zone = str(region["zone"])
        color, zone_label = zone_styles[zone]
        summary_axis.text(
            x_position,
            y_position,
            f'{region["region_id"]}  {zone_label}',
            transform=summary_axis.transAxes,
            color=color,
            fontsize=10,
            fontweight="bold",
            va="top",
        )
        y_position -= 0.035
        summary_axis.text(
            x_position,
            y_position,
            textwrap.fill(
                f'Terms: {str(region["top_terms"]).replace("_", " ")}',
                width=34,
            ),
            transform=summary_axis.transAxes,
            color="#252525",
            fontsize=8.5,
            va="top",
        )
        y_position -= 0.07
        summary_axis.text(
            x_position,
            y_position,
            textwrap.fill(f'Example: {region["representative_excerpt"]}', width=40),
            transform=summary_axis.transAxes,
            color="#555555",
            fontsize=7.5,
            va="top",
            style="italic",
        )
        y_position -= 0.12
        summary_axis.text(
            x_position,
            y_position,
            (
                f'{region["segment_count"]} segments · '
                f'{region["candidate_count"]} candidate/cycle units'
            ),
            transform=summary_axis.transAxes,
            color="#777777",
            fontsize=7.5,
            va="top",
        )
    figure.suptitle(
        "Provisional GTE multilingual KDE fingerprint",
        fontsize=19,
        y=0.99,
    )
    figure.subplots_adjust(top=0.93, bottom=0.08, left=0.06, right=0.98)
    figure.savefig(figure_path, dpi=220)
    plt.close(figure)


def density_region_summaries(
    rows: Sequence[dict[str, Any]],
    *,
    max_regions_per_zone: int = 2,
) -> list[dict[str, Any]]:
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    prefixes = {"hot": "D", "cold": "O", "shared": "S"}
    output = []
    for zone in ("hot", "cold", "shared"):
        zone_rows = [row for row in rows if row.get("zone") == zone]
        if not zone_rows:
            continue
        cluster_count = min(
            max_regions_per_zone,
            max(1, len(zone_rows) // 350),
        )
        coordinates = np.array(
            [[float(row["umap_x"]), float(row["umap_y"])] for row in zone_rows]
        )
        standardized_coordinates = StandardScaler().fit_transform(coordinates)
        if (
            cluster_count == 1
            or len(zone_rows) < 4
            or np.allclose(np.ptp(standardized_coordinates, axis=0), 0.0)
        ):
            labels = np.zeros(len(zone_rows), dtype=int)
            cluster_count = 1
        else:
            labels = KMeans(
                n_clusters=cluster_count,
                random_state=SEED,
                n_init=20,
            ).fit_predict(standardized_coordinates)
        clusters = []
        for label in range(cluster_count):
            members = [
                row for row, assigned in zip(zone_rows, labels, strict=True) if assigned == label
            ]
            mean_score = sum(float(row["log1p_density_ratio"]) for row in members) / len(members)
            clusters.append(
                {
                    "members": members,
                    "mean_score": mean_score,
                    "rank_score": abs(mean_score) * (len(members) ** 0.5),
                }
            )
        clusters.sort(key=lambda cluster: float(cluster["rank_score"]), reverse=True)
        for rank, cluster in enumerate(clusters, start=1):
            members = cluster["members"]
            terms = _distinctive_region_terms(members, zone_rows)
            excerpt = _representative_region_excerpt(members, terms)
            region_id = f"{prefixes[zone]}{rank}"
            for row in members:
                row["density_region_id"] = region_id
            output.append(
                {
                    "region_id": region_id,
                    "zone": zone,
                    "segment_count": len(members),
                    "candidate_count": len(
                        {str(row.get("candidate_unit_id", "")) for row in members}
                    ),
                    "mean_log1p_density_ratio": round(
                        float(cluster["mean_score"]),
                        12,
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
                    "representative_candidate": _representative_candidate(members, excerpt),
                }
            )
    return output


def _distinctive_region_terms(
    region_rows: Sequence[dict[str, Any]],
    zone_rows: Sequence[dict[str, Any]],
    *,
    top_n: int = 5,
) -> list[str]:
    from .text_analysis import tokenize

    excluded = {
        "also",
        "all",
        "applause",
        "august",
        "campaign",
        "candidate",
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
        "form",
        "her",
        "information",
        "issue",
        "local",
        "lemon",
        "make",
        "name",
        "need",
        "new",
        "news",
        "one",
        "people",
        "politic",
        "primary",
        "race",
        "running",
        "said",
        "schedule",
        "she",
        "sport",
        "state",
        "support",
        "senator",
        "tapper",
        "thank",
        "vote",
        "vice",
        "website",
        "work",
        "would",
        "year",
        "newsletter",
        "office",
        "org",
        "questionnaire",
        "com",
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


def _representative_region_excerpt(
    rows: Sequence[dict[str, Any]],
    terms: Sequence[str],
) -> str:
    from .text_analysis import tokenize

    term_set = set(terms)
    candidates = []
    for row in rows:
        text = str(row.get("text", ""))
        if _looks_like_navigation_or_form(text):
            continue
        spans = [
            span.strip()
            for span in re.split(r"(?<=[.!?])\s+|\n+", text)
            if 10 <= len(span.split()) <= 60
            and not _looks_like_navigation_or_form(span)
        ]
        for span in spans or [text]:
            normalized = " ".join(span.split())
            if not normalized:
                continue
            candidates.append(
                (
                    len(term_set & set(tokenize(normalized))),
                    min(len(normalized.split()), 40),
                    -int(bool(re.match(r"^[A-Z][A-Z .'-]{1,20}:", normalized))),
                    row,
                    normalized,
                )
            )
    if not candidates:
        return "[No high-confidence representative excerpt; inspect the region CSV.]"
    _, _, _, _, excerpt = max(candidates, key=lambda candidate: candidate[:3])
    return excerpt if len(excerpt) <= 135 else excerpt[:132].rstrip() + "..."


def _looks_like_navigation_or_form(text: str) -> bool:
    from urllib.parse import unquote_plus

    normalized = " ".join(unquote_plus(text).casefold().split())
    return any(
        marker in normalized
        for marker in (
            "(back to top)",
            "candidate questionnaire",
            "candidate roundups",
            "california form 700",
            "check back for more information",
            "name of source (not an acronym)",
            "news story election",
            "politics + government",
            "politics & government",
            "schedule d income",
            "servpro of",
            "sign up for the free",
            "stay in the know",
            "thank you for your interest in completing this question",
            "new yorkers get",
        )
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
        "cold": "Opponent-overrepresented",
        "shared": "Shared high-density",
    }
    region_lines = []
    for region in summary["density_regions"]:
        excerpt = str(region["representative_excerpt"]).replace("|", "\\|")
        terms = str(region["top_terms"]).replace("_", " ").replace(" | ", ", ")
        region_lines.append(
            "| {region_id} | {zone} | {segments} | {candidates} | {terms} | "
            "{candidate}: {excerpt} |".format(
                region_id=region["region_id"],
                zone=zone_labels[str(region["zone"])],
                segments=region["segment_count"],
                candidates=region["candidate_count"],
                terms=terms,
                candidate=region["representative_candidate"] or "Representative segment",
                excerpt=excerpt,
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""# Provisional GTE KDE region analysis

The KDE contains **{summary["retained_segments"]}** candidate/cycle-deduplicated segments:
**{summary["group_counts"]["endorsed"]}** from DSA-endorsed candidates and
**{summary["group_counts"]["opponent"]}** from opponents. Density estimation is performed in
**{summary["selected_dimensions"]} dimensions**; the two-dimensional map is used only for
visualization.

![Labeled KDE regions](../figures/provisional_gte_kde.png)

## Interpreting the labeled regions

- **D regions** are spatial groupings among DSA-endorsed segments above the endorsed-group
  upper-quartile density-ratio cutoff.
- **O regions** are spatial groupings among opponent segments below the opponent-group
  lower-quartile cutoff.
- **S regions** are high-joint-density areas with small absolute density differences. They
  represent semantic overlap, not proof of identical positions.
- Terms are locally distinctive document-prevalence terms from the underlying region text.
  Examples are extractive source passages, not generated paraphrases.

| Region | Interpretation | Segments | Candidate/cycles | Distinctive terms | Representative source text |
| --- | --- | ---: | ---: | --- | --- |
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
