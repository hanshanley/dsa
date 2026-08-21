from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from .narrative_analysis import hot_cold_characterization, umap_trustworthiness

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "processed" / "candidate_document_analysis_segments.csv"
DEFAULT_OUTPUT = ROOT / "data" / "analysis" / "provisional_gte_kde"
DEFAULT_FIGURE = ROOT / "figures" / "provisional_gte_kde.png"
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

    scored_rows = []
    hot_cold_documents = []
    for index, row in enumerate(rows):
        score = float(scores[index])
        zone = ""
        if row["group"] == "endorsed" and score >= endorsed_cutoff:
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
    _write_csv(output_directory / "segment_density_scores.csv", scored_rows)
    _write_csv(output_directory / "umap_dimension_sweep.csv", sweep_rows)
    _write_csv(output_directory / "hot_cold_terms.csv", characterization["rows"])
    _plot_density_fingerprint(
        scored_rows,
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
            "minimum_token_count": 8,
            "excluded_flags": ["boilerplate_flag", "exact_duplicate_flag"],
        },
        "retained_segments": len(rows),
        "group_counts": dict(group_counts),
        "candidate_counts": dict(
            Counter(
                row["group"]
                for row in {
                    (item["group"], item["race_id"], item["candidate_slug"]): item
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
            "counts": dict(zone_counts),
        },
        "top_hot_terms": characterization["hot_terms"],
        "top_cold_terms": characterization["cold_terms"],
        "outputs": {
            "scores": str((output_directory / "segment_density_scores.csv").relative_to(ROOT)),
            "sweep": str((output_directory / "umap_dimension_sweep.csv").relative_to(ROOT)),
            "terms": str((output_directory / "hot_cold_terms.csv").relative_to(ROOT)),
            "figure": str(figure_path.relative_to(ROOT)),
        },
    }
    _write_json(output_directory / "summary.json", summary)
    return ProvisionalKDEResult(
        retained_segments=len(rows),
        endorsed_segments=group_counts["endorsed"],
        opponent_segments=group_counts["opponent"],
        selected_dimensions=selected_dimensions,
        output_directory=output_directory,
    )


def load_eligible_segments(path: Path) -> list[dict[str, str]]:
    rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            role = row.get("role", "")
            if role not in {"endorsed", "opponent", "unopposed"}:
                continue
            if _is_true(row.get("boilerplate_flag")) or _is_true(
                row.get("exact_duplicate_flag")
            ):
                continue
            if int(row.get("token_count") or 0) < 8:
                continue
            text = (row.get("text") or "").strip()
            if not text:
                continue
            retained = dict(row)
            retained["group"] = "endorsed" if role in {"endorsed", "unopposed"} else "opponent"
            rows.append(retained)
    return rows


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
    by_candidate: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        if row["group"] == group:
            by_candidate[(row["race_id"], row["candidate_slug"])].append(index)
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
    figure, axis = plt.subplots(figsize=(10, 8))
    scatter = axis.scatter(
        x,
        y,
        c=score,
        cmap="coolwarm",
        vmin=-bound,
        vmax=bound,
        s=3,
        alpha=0.55,
        linewidths=0,
        rasterized=True,
    )
    axis.set_title("Provisional GTE multilingual KDE fingerprint")
    axis.set_xlabel("UMAP 1 (visualization only)")
    axis.set_ylabel("UMAP 2 (visualization only)")
    colorbar = figure.colorbar(scatter, ax=axis)
    colorbar.set_label("log(1 + DSA density) - log(1 + opponent density)")
    axis.text(
        0.01,
        0.01,
        f"Hot cutoff: {endorsed_cutoff:.4g} | Cold cutoff: {opponent_cutoff:.4g}",
        transform=axis.transAxes,
        fontsize=8,
    )
    figure.tight_layout()
    figure.savefig(figure_path, dpi=220)
    plt.close(figure)


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
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
