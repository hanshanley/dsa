import hashlib
import importlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .io import read_json
from .paths import CONFIG_DIR

NARRATIVE_ANALYSIS_CONFIG = CONFIG_DIR / "narrative_analysis.json"
DEFAULT_ANNOTATION_LABELS = frozenset({"match", "mismatch", "uncertain"})
TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")


def load_narrative_analysis_config(path: Path | None = None) -> dict[str, Any]:
    return read_json(path or NARRATIVE_ANALYSIS_CONFIG)


def resolve_selected_cosine_threshold(
    config: Mapping[str, Any] | None = None,
) -> float:
    config_data = dict(config or load_narrative_analysis_config())
    threshold = config_data.get("threshold_selection", {}).get(
        "selected_cosine_threshold"
    )
    if threshold is None:
        raise ValueError(
            "Set threshold_selection.selected_cosine_threshold or provide an "
            "explicit threshold."
        )
    threshold_value = float(threshold)
    if not 0 < threshold_value < 1:
        raise ValueError("selected cosine threshold must be in the interval (0, 1)")
    return threshold_value


def resolve_selected_cosine_distance(
    config: Mapping[str, Any] | None = None,
) -> float:
    return 1.0 - resolve_selected_cosine_threshold(config)


def normalize_embedding(vector: Sequence[float]) -> list[float]:
    values = [float(value) for value in vector]
    if not values:
        raise ValueError("Embedding vectors must not be empty")
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise ValueError("Embedding vectors must have non-zero length")
    return [value / norm for value in values]


def normalize_embeddings(embeddings: Sequence[Sequence[float]]) -> list[list[float]]:
    return [normalize_embedding(vector) for vector in embeddings]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Cosine similarity requires vectors with equal dimensions")
    left_unit = normalize_embedding(left)
    right_unit = normalize_embedding(right)
    return sum(a * b for a, b in zip(left_unit, right_unit, strict=True))


def build_embedding_cache_metadata(
    texts: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    *,
    model_name: str,
    identifiers: Sequence[str] | None = None,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if identifiers is not None and len(identifiers) != len(texts):
        raise ValueError("Identifiers must align with texts")
    normalized = normalize_embeddings(embeddings)
    config_data = dict(config or load_narrative_analysis_config())
    cache_config = dict(config_data.get("embedding_cache", {}))
    rounded_embeddings = [
        [round(value, 12) for value in vector] for vector in normalized
    ]
    dimensions = len(normalized[0]) if normalized else 0
    metadata = {
        "schema_version": int(cache_config.get("schema_version", 1)),
        "config_version": str(config_data.get("config_version", "1")),
        "model_name": model_name,
        "normalized": True,
        "normalization": str(cache_config.get("normalization", "l2")),
        "hash_algorithm": str(cache_config.get("hash_algorithm", "sha256")),
        "vector_count": len(normalized),
        "dimensions": dimensions,
        "seed": int(config_data.get("seed", 0)),
        "text_sha256": _stable_hash([str(text) for text in texts]),
        "embedding_sha256": _stable_hash(rounded_embeddings),
    }
    if identifiers is not None:
        metadata["identifier_sha256"] = _stable_hash([str(value) for value in identifiers])
    metadata["cache_key"] = _stable_hash(
        {
            "model_name": model_name,
            "vector_count": metadata["vector_count"],
            "dimensions": dimensions,
            "text_sha256": metadata["text_sha256"],
            "embedding_sha256": metadata["embedding_sha256"],
            "identifier_sha256": metadata.get("identifier_sha256", ""),
        }
    )
    metadata["provenance"] = {
        "method": "build_embedding_cache_metadata",
        "seed": metadata["seed"],
        "config_version": metadata["config_version"],
        "hash_algorithm": metadata["hash_algorithm"],
        "vector_count": metadata["vector_count"],
        "dimensions": dimensions,
    }
    return metadata


def validate_embedding_cache_metadata(
    metadata: Mapping[str, Any],
    texts: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    *,
    identifiers: Sequence[str] | None = None,
) -> None:
    expected = build_embedding_cache_metadata(
        texts,
        embeddings,
        model_name=str(metadata["model_name"]),
        identifiers=identifiers,
        config={
            "config_version": metadata.get("config_version", "1"),
            "seed": metadata.get("seed", 0),
            "embedding_cache": {
                "schema_version": metadata.get("schema_version", 1),
                "normalization": metadata.get("normalization", "l2"),
                "hash_algorithm": metadata.get("hash_algorithm", "sha256"),
            },
        },
    )
    mismatches = []
    for field in (
        "schema_version",
        "config_version",
        "model_name",
        "normalized",
        "normalization",
        "hash_algorithm",
        "vector_count",
        "dimensions",
        "seed",
        "text_sha256",
        "embedding_sha256",
        "cache_key",
        "identifier_sha256",
    ):
        if field in metadata or field in expected:
            if metadata.get(field) != expected.get(field):
                mismatches.append(field)
    if mismatches:
        joined = ", ".join(mismatches)
        raise ValueError(f"Embedding cache metadata mismatch for: {joined}")


def sample_threshold_pairs(
    pairs: Sequence[Mapping[str, Any]],
    *,
    thresholds: Sequence[float],
    band_width: float,
    max_per_threshold: int,
    score_key: str = "similarity",
    id_key: str = "pair_id",
    balance_keys: Sequence[str] = ("race_id",),
    seed: int | None = None,
) -> dict[str, Any]:
    if not thresholds:
        raise ValueError("thresholds must not be empty")
    if band_width < 0:
        raise ValueError("band_width must be non-negative")
    if max_per_threshold < 1:
        raise ValueError("max_per_threshold must be at least 1")
    config_data = load_narrative_analysis_config()
    sampled_seed = int(config_data.get("seed", 0) if seed is None else seed)
    assigned: dict[float, list[dict[str, Any]]] = defaultdict(list)
    sorted_thresholds = sorted(float(value) for value in thresholds)
    for row in pairs:
        pair_id = str(row[id_key]).strip()
        score = float(row[score_key])
        threshold = min(sorted_thresholds, key=lambda value: (abs(score - value), value))
        distance = abs(score - threshold)
        if distance > band_width:
            continue
        enriched = dict(row)
        enriched[id_key] = pair_id
        enriched[score_key] = score
        enriched["threshold"] = threshold
        enriched["distance_to_threshold"] = round(distance, 12)
        enriched["_balance_key"] = tuple(str(row.get(key, "")) for key in balance_keys) or ("",)
        assigned[threshold].append(enriched)
    sampled_rows = []
    counts_by_threshold = {}
    for threshold in sorted_thresholds:
        threshold_rows = assigned.get(threshold, [])
        selected = _balanced_round_robin(
            threshold_rows,
            limit=max_per_threshold,
            seed=sampled_seed,
            id_key=id_key,
        )
        counts_by_threshold[str(threshold)] = len(selected)
        for row in selected:
            stripped = dict(row)
            stripped.pop("_balance_key", None)
            sampled_rows.append(stripped)
    sampled_rows.sort(
        key=lambda row: (
            float(row["threshold"]),
            float(row["distance_to_threshold"]),
            str(row[id_key]),
        )
    )
    return {
        "pairs": sampled_rows,
        "provenance": {
            "method": "sample_threshold_pairs",
            "seed": sampled_seed,
            "thresholds": sorted_thresholds,
            "band_width": band_width,
            "max_per_threshold": max_per_threshold,
            "pair_count": len(sampled_rows),
            "counts_by_threshold": counts_by_threshold,
            "balance_keys": list(balance_keys),
        },
    }


def select_cosine_threshold(
    rows: Sequence[Mapping[str, Any]],
    *,
    thresholds: Sequence[float],
    score_key: str = "similarity",
    label_key: str = "selected_label",
    positive_label: str = "match",
    negative_label: str = "mismatch",
) -> dict[str, Any]:
    if not thresholds:
        raise ValueError("thresholds must not be empty")
    normalized_thresholds = []
    for value in thresholds:
        threshold = float(value)
        if not 0 < threshold < 1:
            raise ValueError("thresholds must be in the interval (0, 1)")
        normalized_thresholds.append(threshold)
    positive = positive_label.strip().lower()
    negative = negative_label.strip().lower()
    comparable = []
    excluded = 0
    for row in rows:
        label = str(row.get(label_key, "")).strip().lower()
        if label not in {positive, negative}:
            excluded += 1
            continue
        comparable.append(
            {
                **row,
                score_key: float(row[score_key]),
                label_key: label,
            }
        )
    if not comparable:
        raise ValueError("No comparable annotated pairs were provided")
    metrics = []
    for threshold in sorted(normalized_thresholds):
        true_positive = false_positive = true_negative = false_negative = 0
        for row in comparable:
            predicted_positive = float(row[score_key]) >= threshold
            actual_positive = row[label_key] == positive
            if predicted_positive and actual_positive:
                true_positive += 1
            elif predicted_positive:
                false_positive += 1
            elif actual_positive:
                false_negative += 1
            else:
                true_negative += 1
        precision = true_positive / max(true_positive + false_positive, 1)
        recall = true_positive / max(true_positive + false_negative, 1)
        specificity = true_negative / max(true_negative + false_positive, 1)
        balanced_accuracy = (recall + specificity) / 2
        agreement = (true_positive + true_negative) / len(comparable)
        f1 = 0.0
        if precision + recall > 0:
            f1 = (2 * precision * recall) / (precision + recall)
        metrics.append(
            {
                "threshold": threshold,
                "tp": true_positive,
                "fp": false_positive,
                "tn": true_negative,
                "fn": false_negative,
                "precision": round(precision, 12),
                "recall": round(recall, 12),
                "specificity": round(specificity, 12),
                "balanced_accuracy": round(balanced_accuracy, 12),
                "agreement": round(agreement, 12),
                "f1": round(f1, 12),
            }
        )
    selected = max(
        metrics,
        key=lambda row: (
            float(row["balanced_accuracy"]),
            float(row["precision"]),
            float(row["recall"]),
            float(row["threshold"]),
        ),
    )
    return {
        "selected_threshold": float(selected["threshold"]),
        "metrics": metrics,
        "provenance": {
            "method": "select_cosine_threshold",
            "pair_count": len(comparable),
            "excluded_rows": excluded,
            "positive_label": positive,
            "negative_label": negative,
            "selection_metric": "balanced_accuracy",
            "tie_breakers": ["precision", "recall", "higher_threshold"],
        },
    }


def validate_pair_annotations(
    annotations: Sequence[Mapping[str, Any]],
    *,
    pair_key: str = "pair_id",
    annotator_key: str = "annotator_id",
    label_key: str = "label",
    allowed_labels: Iterable[str] = DEFAULT_ANNOTATION_LABELS,
) -> list[dict[str, Any]]:
    allowed = {str(label).strip().lower() for label in allowed_labels}
    cleaned = []
    seen = set()
    errors = []
    for index, row in enumerate(annotations, start=1):
        pair_id = str(row.get(pair_key, "")).strip()
        annotator_id = str(row.get(annotator_key, "")).strip()
        label = str(row.get(label_key, "")).strip().lower()
        if not pair_id:
            errors.append(f"row {index}: missing {pair_key}")
        if not annotator_id:
            errors.append(f"row {index}: missing {annotator_key}")
        if label not in allowed:
            errors.append(f"row {index}: invalid {label_key}={label!r}")
        key = (pair_id, annotator_id)
        if pair_id and annotator_id and key in seen:
            errors.append(
                "row "
                f"{index}: duplicate annotation for pair={pair_id} "
                f"annotator={annotator_id}"
            )
        seen.add(key)
        cleaned.append(
            {
                **row,
                pair_key: pair_id,
                annotator_key: annotator_id,
                label_key: label,
            }
        )
    if errors:
        raise ValueError("; ".join(errors))
    return cleaned


def select_pair_annotations(
    annotations: Sequence[Mapping[str, Any]],
    *,
    pair_key: str = "pair_id",
    annotator_key: str = "annotator_id",
    label_key: str = "label",
    min_votes: int = 2,
    review_status: str = "needs_review",
) -> dict[str, Any]:
    if min_votes < 1:
        raise ValueError("min_votes must be at least 1")
    cleaned = validate_pair_annotations(
        annotations,
        pair_key=pair_key,
        annotator_key=annotator_key,
        label_key=label_key,
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in cleaned:
        grouped[str(row[pair_key])].append(row)
    rows = []
    selected_count = 0
    for pair_id in sorted(grouped):
        group = grouped[pair_id]
        counts = Counter(str(row[label_key]) for row in group)
        ordered = counts.most_common()
        top_label, top_count = ordered[0]
        runner_up = ordered[1][1] if len(ordered) > 1 else 0
        status = "selected" if top_count >= min_votes and top_count > runner_up else review_status
        if status == "selected":
            selected_count += 1
        rows.append(
            {
                pair_key: pair_id,
                "selected_label": top_label if status == "selected" else "",
                "status": status,
                "vote_count": len(group),
                "support": top_count,
                "margin": top_count - runner_up,
                "label_counts": json.dumps(dict(sorted(counts.items())), sort_keys=True),
            }
        )
    return {
        "pairs": rows,
        "provenance": {
            "method": "select_pair_annotations",
            "pair_count": len(rows),
            "selected_count": selected_count,
            "min_votes": min_votes,
            "review_status": review_status,
        },
    }


def build_knn_edges(
    identifiers: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    *,
    k: int,
    min_similarity: float | None = None,
    mutual: bool = True,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if len(identifiers) != len(embeddings):
        raise ValueError("Identifiers and embeddings must align")
    if k < 1:
        raise ValueError("k must be at least 1")
    threshold_source = "explicit"
    if min_similarity is None:
        min_similarity = resolve_selected_cosine_threshold(config)
        threshold_source = "config.threshold_selection.selected_cosine_threshold"
    ids = [str(value) for value in identifiers]
    vectors = normalize_embeddings(embeddings)
    neighbor_lists: dict[int, list[tuple[int, float]]] = {}
    weight_by_pair: dict[tuple[int, int], float] = {}
    for left_index, left_vector in enumerate(vectors):
        scores = []
        for right_index, right_vector in enumerate(vectors):
            if left_index == right_index:
                continue
            similarity = sum(
                left * right
                for left, right in zip(left_vector, right_vector, strict=True)
            )
            if similarity >= min_similarity:
                scores.append((right_index, similarity))
        scores.sort(key=lambda item: (-item[1], ids[item[0]]))
        neighbor_lists[left_index] = scores[:k]
        for right_index, similarity in neighbor_lists[left_index]:
            pair = tuple(sorted((left_index, right_index)))
            weight_by_pair[pair] = max(weight_by_pair.get(pair, -1.0), similarity)
    selected_edges = []
    for left_index, neighbors in neighbor_lists.items():
        for right_index, _similarity in neighbors:
            right_lookup = {neighbor for neighbor, _score in neighbor_lists.get(right_index, [])}
            if mutual and left_index not in right_lookup:
                continue
            pair = tuple(sorted((left_index, right_index)))
            if not mutual or pair[0] == left_index:
                selected_edges.append(pair)
    unique_pairs = sorted(set(selected_edges))
    rows = [
        {
            "source": ids[left_index],
            "target": ids[right_index],
            "similarity": round(weight_by_pair[(left_index, right_index)], 12),
        }
        for left_index, right_index in unique_pairs
    ]
    rows.sort(key=lambda row: (-float(row["similarity"]), row["source"], row["target"]))
    return {
        "edges": rows,
        "provenance": {
            "method": "build_knn_edges",
            "node_count": len(ids),
            "edge_count": len(rows),
            "k": k,
            "min_similarity": min_similarity,
            "mutual": mutual,
            "threshold_source": threshold_source,
        },
    }


def run_leiden_clustering(
    identifiers: Sequence[str],
    edges: Sequence[Mapping[str, Any]],
    *,
    resolution: float = 1.0,
    objective: str = "modularity",
    seed: int = 0,
    min_cluster_size: int = 1,
) -> dict[str, Any]:
    igraph = _optional_dependency(
        "igraph",
        "Install `python-igraph` and `leidenalg` to run Leiden clustering.",
    )
    leidenalg = _optional_dependency(
        "leidenalg",
        "Install `python-igraph` and `leidenalg` to run Leiden clustering.",
    )
    ids = [str(value) for value in identifiers]
    id_to_index = {value: index for index, value in enumerate(ids)}
    graph = igraph.Graph()
    graph.add_vertices(len(ids))
    graph.vs["name"] = ids
    igraph_edges = []
    weights = []
    for row in edges:
        source = str(row["source"])
        target = str(row["target"])
        if source == target:
            continue
        igraph_edges.append((id_to_index[source], id_to_index[target]))
        weights.append(float(row.get("weight", row.get("similarity", 1.0))))
    if igraph_edges:
        graph.add_edges(igraph_edges)
    partition_class = _leiden_partition_class(leidenalg, objective)
    partition_kwargs = {"weights": weights or None, "seed": seed}
    if objective != "modularity":
        partition_kwargs["resolution_parameter"] = resolution
    partition = leidenalg.find_partition(graph, partition_class, **partition_kwargs)
    membership = list(partition.membership)
    cluster_sizes = Counter(membership)
    rows = [
        {
            "identifier": identifier,
            "cluster_id": membership[index],
            "cluster_size": cluster_sizes[membership[index]],
            "retained": cluster_sizes[membership[index]] >= min_cluster_size,
        }
        for index, identifier in enumerate(ids)
    ]
    return {
        "assignments": rows,
        "provenance": {
            "method": "run_leiden_clustering",
            "seed": seed,
            "resolution": resolution,
            "objective": objective,
            "node_count": len(ids),
            "edge_count": len(igraph_edges),
            "min_cluster_size": min_cluster_size,
        },
    }


def narrative_lift(
    rows: Sequence[Mapping[str, Any]],
    *,
    narrative_key: str,
    group_key: str = "group",
    positive_group: str,
    negative_group: str,
    candidate_key: str = "candidate_id",
    race_key: str = "race_id",
    smoothing: float = 1e-6,
) -> dict[str, Any]:
    if smoothing <= 0:
        raise ValueError("smoothing must be positive")
    weights = _candidate_race_balanced_weights(
        rows,
        group_key=group_key,
        race_key=race_key,
        candidate_key=candidate_key,
    )
    weighted_presence: dict[str, Counter[str]] = defaultdict(Counter)
    weighted_totals = Counter()
    support = Counter()
    for row, weight in zip(rows, weights, strict=True):
        group = str(row[group_key])
        weighted_totals[group] += weight
        narratives = _coerce_labels(row.get(narrative_key, ""))
        for narrative in narratives:
            weighted_presence[group][narrative] += weight
            support[narrative] += 1
    all_narratives = sorted(
        set(weighted_presence[positive_group]) | set(weighted_presence[negative_group])
    )
    scored_rows = []
    for narrative in all_narratives:
        positive_share = weighted_presence[positive_group][narrative] / max(
            weighted_totals[positive_group], 1e-12
        )
        negative_share = weighted_presence[negative_group][narrative] / max(
            weighted_totals[negative_group], 1e-12
        )
        ratio = (positive_share + smoothing) / (negative_share + smoothing)
        log_lift = math.log(ratio, 2)
        scored_rows.append(
            {
                "narrative": narrative,
                "positive_share": round(positive_share, 12),
                "negative_share": round(negative_share, 12),
                "lift_ratio": round(ratio, 12),
                "log2_lift": round(log_lift, 12),
                "favored_group": positive_group if log_lift >= 0 else negative_group,
                "support": support[narrative],
            }
        )
    scored_rows.sort(
        key=lambda row: (-abs(float(row["log2_lift"])), row["narrative"])
    )
    return {
        "rows": scored_rows,
        "provenance": {
            "method": "narrative_lift",
            "positive_group": positive_group,
            "negative_group": negative_group,
            "row_count": len(rows),
            "seed": load_narrative_analysis_config().get("seed", 0),
            "balancing": "equal race weight per group, equal candidate weight per race",
        },
    }


def fit_umap_projection(
    embeddings: Sequence[Sequence[float]],
    *,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    metric: str = "cosine",
    n_components: int = 2,
    seed: int = 0,
) -> dict[str, Any]:
    umap = _optional_dependency(
        "umap",
        "Install `umap-learn` to compute UMAP projections.",
    )
    vectors = normalize_embeddings(embeddings)
    reducer = umap.UMAP(
        n_neighbors=min(n_neighbors, max(len(vectors) - 1, 2)),
        min_dist=min_dist,
        metric=metric,
        n_components=n_components,
        random_state=seed,
    )
    coordinates = reducer.fit_transform(vectors)
    return {
        "coordinates": [
            [float(value) for value in row] for row in coordinates.tolist()
        ],
        "provenance": {
            "method": "fit_umap_projection",
            "seed": seed,
            "n_neighbors": n_neighbors,
            "min_dist": min_dist,
            "metric": metric,
            "n_components": n_components,
        },
    }


def evaluate_umap_dimension_sweep(
    embeddings: Sequence[Sequence[float]],
    *,
    dimensions: Sequence[int],
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    metric: str = "cosine",
    seed: int = 0,
) -> dict[str, Any]:
    if not dimensions:
        raise ValueError("dimensions must not be empty")
    rows = []
    for dimension in dimensions:
        projection = fit_umap_projection(
            embeddings,
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            metric=metric,
            n_components=int(dimension),
            seed=seed,
        )
        trust = umap_trustworthiness(
            embeddings,
            projection["coordinates"],
            n_neighbors=min(5, max(len(embeddings) - 1, 1)),
        )
        rows.append(
            {
                "dimensions": int(dimension),
                "trustworthiness": round(float(trust["trustworthiness"]), 12),
            }
        )
    rows.sort(
        key=lambda row: (-float(row["trustworthiness"]), int(row["dimensions"]))
    )
    return {
        "rows": rows,
        "provenance": {
            "method": "evaluate_umap_dimension_sweep",
            "dimensions": [int(value) for value in dimensions],
            "seed": seed,
            "n_neighbors": n_neighbors,
            "min_dist": min_dist,
            "metric": metric,
        },
    }


def umap_trustworthiness(
    original_embeddings: Sequence[Sequence[float]],
    projected_embeddings: Sequence[Sequence[float]],
    *,
    n_neighbors: int = 5,
) -> dict[str, Any]:
    if n_neighbors < 1:
        raise ValueError("n_neighbors must be at least 1")
    sample_count = len(original_embeddings)
    if sample_count == 0:
        raise ValueError("original_embeddings must not be empty")
    if len(projected_embeddings) != sample_count:
        raise ValueError(
            "original_embeddings and projected_embeddings must have equal lengths"
        )
    if sample_count < 3:
        return {
            "trustworthiness": 1.0,
            "provenance": {
                "method": "umap_trustworthiness",
                "requested_n_neighbors": n_neighbors,
                "effective_n_neighbors": 0,
                "sample_count": sample_count,
                "degenerate_sample": True,
            },
        }
    max_neighbors = max(1, (sample_count - 1) // 2)
    effective_n_neighbors = min(n_neighbors, max_neighbors)
    manifold = _optional_dependency(
        "sklearn.manifold",
        "Install `scikit-learn` to score UMAP trustworthiness.",
    )
    value = manifold.trustworthiness(
        normalize_embeddings(original_embeddings),
        [list(map(float, vector)) for vector in projected_embeddings],
        n_neighbors=effective_n_neighbors,
    )
    return {
        "trustworthiness": float(value),
        "provenance": {
            "method": "umap_trustworthiness",
            "requested_n_neighbors": n_neighbors,
            "effective_n_neighbors": effective_n_neighbors,
            "sample_count": sample_count,
            "degenerate_sample": False,
        },
    }


def estimate_kde_density(
    points: Sequence[Sequence[float]],
    *,
    grid_size: int = 25,
    padding: float = 0.05,
    bandwidth: float | None = None,
) -> dict[str, Any]:
    if grid_size < 2:
        raise ValueError("grid_size must be at least 2")
    coordinates = [[float(value) for value in point] for point in points]
    if not coordinates:
        raise ValueError("points must not be empty")
    if len(coordinates) < 3:
        raise ValueError("KDE density estimation requires at least 3 points")
    if any(len(point) != 2 for point in coordinates):
        raise ValueError("KDE density estimation expects 2D points")
    if not _has_rank_2(coordinates):
        raise ValueError(
            "KDE density estimation requires 2D points with non-collinear variation"
        )
    scipy_stats = _optional_dependency(
        "scipy.stats",
        "Install `scipy` to estimate KDE densities.",
    )
    x_values = [point[0] for point in coordinates]
    y_values = [point[1] for point in coordinates]
    x_pad = max(max(x_values) - min(x_values), 1.0) * padding
    y_pad = max(max(y_values) - min(y_values), 1.0) * padding
    x_grid = _linspace(min(x_values) - x_pad, max(x_values) + x_pad, grid_size)
    y_grid = _linspace(min(y_values) - y_pad, max(y_values) + y_pad, grid_size)
    try:
        kde = scipy_stats.gaussian_kde(
            [[point[0] for point in coordinates], [point[1] for point in coordinates]],
            bw_method=bandwidth,
        )
    except Exception as error:
        raise ValueError(
            "KDE density estimation requires full-rank numeric samples"
        ) from error
    density = []
    for y_value in y_grid:
        row = []
        for x_value in x_grid:
            row.append(float(kde([[x_value], [y_value]])[0]))
        density.append(row)
    return {
        "x_grid": x_grid,
        "y_grid": y_grid,
        "density": density,
        "provenance": {
            "method": "estimate_kde_density",
            "grid_size": grid_size,
            "padding": padding,
            "bandwidth": bandwidth,
            "point_count": len(coordinates),
        },
    }


def hot_cold_characterization(
    documents: Sequence[Mapping[str, Any]],
    *,
    group_key: str = "group",
    positive_group: str,
    negative_group: str,
    tokens_key: str = "tokens",
    text_key: str = "text",
    min_document_frequency: int = 1,
    top_n: int = 10,
    quantiles: Sequence[float] = (0.1, 0.2, 0.3, 0.4),
) -> dict[str, Any]:
    if min_document_frequency < 1:
        raise ValueError("min_document_frequency must be at least 1")
    if not quantiles:
        raise ValueError("quantiles must not be empty")
    prepared = []
    document_frequency = Counter()
    observed_groups = set()
    for row in documents:
        group = str(row[group_key])
        tokens = _coerce_tokens(row, tokens_key=tokens_key, text_key=text_key)
        if not tokens:
            continue
        counts = Counter(tokens)
        prepared.append((group, counts))
        observed_groups.add(group)
        for token in counts:
            document_frequency[token] += 1
    if positive_group not in observed_groups or negative_group not in observed_groups:
        raise ValueError(
            "hot/cold characterization requires documents for both comparison groups"
        )
    total_documents = len(prepared)
    inverse_document_frequency = {
        token: math.log((1 + total_documents) / (1 + count)) + 1.0
        for token, count in document_frequency.items()
    }
    mean_tfidf = defaultdict(Counter)
    group_sizes = Counter()
    term_group_document_counts = defaultdict(Counter)
    for group, counts in prepared:
        total_terms = sum(counts.values())
        group_sizes[group] += 1
        for token, count in counts.items():
            mean_tfidf[group][token] += (
                count / max(total_terms, 1)
            ) * inverse_document_frequency[token]
        for token in counts:
            term_group_document_counts[token][group] += 1
    rows = []
    for token, count in document_frequency.items():
        if count < min_document_frequency:
            continue
        positive_tfidf = mean_tfidf[positive_group][token] / max(group_sizes[positive_group], 1)
        negative_tfidf = mean_tfidf[negative_group][token] / max(group_sizes[negative_group], 1)
        positive_npmi = _npmi(
            term_group_document_counts[token][positive_group],
            document_frequency[token],
            group_sizes[positive_group],
            total_documents,
        )
        negative_npmi = _npmi(
            term_group_document_counts[token][negative_group],
            document_frequency[token],
            group_sizes[negative_group],
            total_documents,
        )
        tfidf_difference = positive_tfidf - negative_tfidf
        npmi_difference = positive_npmi - negative_npmi
        composite_score = tfidf_difference + npmi_difference
        rows.append(
            {
                "term": token,
                "positive_mean_tfidf": round(positive_tfidf, 12),
                "negative_mean_tfidf": round(negative_tfidf, 12),
                "tfidf_difference": round(tfidf_difference, 12),
                "positive_npmi": round(positive_npmi, 12),
                "negative_npmi": round(negative_npmi, 12),
                "npmi_difference": round(npmi_difference, 12),
                "composite_score": round(composite_score, 12),
                "favored_group": positive_group
                if composite_score >= 0
                else negative_group,
            }
        )
    rows.sort(
        key=lambda row: (
            -abs(float(row["tfidf_difference"])) - abs(float(row["npmi_difference"])),
            row["term"],
        )
    )
    hot_terms = [row for row in rows if row["favored_group"] == positive_group][:top_n]
    cold_terms = [row for row in rows if row["favored_group"] == negative_group][:top_n]
    stable_hot_terms, stable_cold_terms, quantile_rows = _quantile_stability(
        rows,
        quantiles=quantiles,
        positive_group=positive_group,
        negative_group=negative_group,
        top_n=top_n,
    )
    return {
        "rows": rows,
        "hot_terms": hot_terms,
        "cold_terms": cold_terms,
        "stable_hot_terms": stable_hot_terms,
        "stable_cold_terms": stable_cold_terms,
        "quantile_rows": quantile_rows,
        "provenance": {
            "method": "hot_cold_characterization",
            "document_count": total_documents,
            "positive_group": positive_group,
            "negative_group": negative_group,
            "min_document_frequency": min_document_frequency,
            "top_n": top_n,
            "quantiles": [float(value) for value in quantiles],
        },
    }


def cosine_dp_means(
    identifiers: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    *,
    max_distance: float | None = None,
    max_iterations: int = 25,
    seed: int | None = None,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if len(identifiers) != len(embeddings):
        raise ValueError("Identifiers and embeddings must align")
    threshold_source = "explicit"
    if max_distance is None:
        max_distance = resolve_selected_cosine_distance(config)
        threshold_source = "config.threshold_selection.selected_cosine_threshold"
    if not identifiers:
        return {
            "assignments": [],
            "centroids": [],
            "provenance": {
                "method": "cosine_dp_means",
                "seed": load_narrative_analysis_config().get("seed", 0)
                if seed is None
                else seed,
                "iterations": 0,
                "cluster_count": 0,
                "max_distance": max_distance,
                "threshold_source": threshold_source,
            },
        }
    if max_distance <= 0:
        raise ValueError("max_distance must be positive")
    vectors = normalize_embeddings(embeddings)
    assignments = [-1] * len(vectors)
    centroids = [vectors[0][:]]
    iterations_used = 0
    for iteration in range(1, max_iterations + 1):
        iterations_used = iteration
        proposed_assignments = []
        working_centroids = [centroid[:] for centroid in centroids]
        for vector in vectors:
            distances = [
                1.0 - sum(
                    left * right
                    for left, right in zip(vector, centroid, strict=True)
                )
                for centroid in working_centroids
            ]
            best_index, best_distance = min(
                enumerate(distances), key=lambda item: (item[1], item[0])
            )
            if best_distance > max_distance:
                working_centroids.append(vector[:])
                proposed_assignments.append(len(working_centroids) - 1)
            else:
                proposed_assignments.append(best_index)
        grouped = defaultdict(list)
        for index, cluster_id in enumerate(proposed_assignments):
            grouped[cluster_id].append(vectors[index])
        ordered_clusters = sorted(grouped)
        remap = {cluster_id: position for position, cluster_id in enumerate(ordered_clusters)}
        remapped_assignments = [remap[cluster_id] for cluster_id in proposed_assignments]
        new_centroids = []
        for cluster_id in ordered_clusters:
            mean = [
                sum(vector[column] for vector in grouped[cluster_id])
                / len(grouped[cluster_id])
                for column in range(len(vectors[0]))
            ]
            try:
                new_centroids.append(normalize_embedding(mean))
            except ValueError:
                new_centroids.append(grouped[cluster_id][0][:])
        if remapped_assignments == assignments:
            centroids = new_centroids
            break
        assignments = remapped_assignments
        centroids = new_centroids
    cluster_sizes = Counter(assignments)
    assignment_rows = []
    for identifier, vector, cluster_id in zip(identifiers, vectors, assignments, strict=True):
        similarity = sum(
            left * right
            for left, right in zip(vector, centroids[cluster_id], strict=True)
        )
        assignment_rows.append(
            {
                "identifier": str(identifier),
                "cluster_id": cluster_id,
                "similarity": round(similarity, 12),
                "distance": round(1.0 - similarity, 12),
                "cluster_size": cluster_sizes[cluster_id],
            }
        )
    return {
        "assignments": assignment_rows,
        "centroids": [[round(value, 12) for value in centroid] for centroid in centroids],
        "provenance": {
            "method": "cosine_dp_means",
            "seed": load_narrative_analysis_config().get("seed", 0)
            if seed is None
            else seed,
            "iterations": iterations_used,
            "cluster_count": len(centroids),
            "max_distance": max_distance,
            "threshold_source": threshold_source,
        },
    }


def _balanced_round_robin(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int,
    seed: int,
    id_key: str,
) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[tuple(row["_balance_key"])].append(dict(row))
    ordered_keys = sorted(buckets)
    for key in ordered_keys:
        buckets[key].sort(
            key=lambda row: (
                float(row["distance_to_threshold"]),
                _seeded_sort_key(seed, str(row[id_key])),
                str(row[id_key]),
            )
        )
    selected = []
    while len(selected) < limit:
        progressed = False
        for key in ordered_keys:
            if buckets[key]:
                selected.append(buckets[key].pop(0))
                progressed = True
                if len(selected) == limit:
                    break
        if not progressed:
            break
    return selected


def _candidate_race_balanced_weights(
    rows: Sequence[Mapping[str, Any]],
    *,
    group_key: str,
    race_key: str,
    candidate_key: str,
) -> list[float]:
    buckets: dict[str, dict[str, dict[str, list[int]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for index, row in enumerate(rows):
        group = str(row[group_key])
        race = str(row[race_key])
        candidate = str(row[candidate_key])
        buckets[group][race][candidate].append(index)
    weights = [0.0] * len(rows)
    for races in buckets.values():
        race_weight = 1.0 / len(races)
        for candidates in races.values():
            candidate_weight = race_weight / len(candidates)
            for indexes in candidates.values():
                row_weight = candidate_weight / len(indexes)
                for index in indexes:
                    weights[index] = row_weight
    return weights


def _quantile_stability(
    rows: Sequence[Mapping[str, Any]],
    *,
    quantiles: Sequence[float],
    positive_group: str,
    negative_group: str,
    top_n: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    ordered_positive = sorted(
        rows,
        key=lambda row: (-float(row["composite_score"]), row["term"]),
    )
    ordered_negative = sorted(
        rows,
        key=lambda row: (float(row["composite_score"]), row["term"]),
    )
    hot_sets = []
    cold_sets = []
    quantile_rows = []
    row_count = len(rows)
    for quantile in sorted(float(value) for value in quantiles):
        if not 0 < quantile <= 1:
            raise ValueError("quantiles must be in the interval (0, 1]")
        limit = max(1, math.ceil(row_count * quantile))
        hot_slice = [
            row for row in ordered_positive[:limit] if row["favored_group"] == positive_group
        ][:top_n]
        cold_slice = [
            row for row in ordered_negative[:limit] if row["favored_group"] == negative_group
        ][:top_n]
        hot_sets.append({row["term"] for row in hot_slice})
        cold_sets.append({row["term"] for row in cold_slice})
        quantile_rows.append(
            {
                "quantile": quantile,
                "hot_terms": [row["term"] for row in hot_slice],
                "cold_terms": [row["term"] for row in cold_slice],
            }
        )
    stable_hot = set.intersection(*hot_sets) if hot_sets else set()
    stable_cold = set.intersection(*cold_sets) if cold_sets else set()
    stable_hot_terms = [
        row for row in ordered_positive if row["term"] in stable_hot
    ][:top_n]
    stable_cold_terms = [
        row for row in ordered_negative if row["term"] in stable_cold
    ][:top_n]
    return stable_hot_terms, stable_cold_terms, quantile_rows


def _coerce_labels(value: Any) -> set[str]:
    if isinstance(value, str):
        return {label for label in (item.strip() for item in value.split("|")) if label}
    if isinstance(value, Iterable):
        return {str(item).strip() for item in value if str(item).strip()}
    return set()


def _coerce_tokens(
    row: Mapping[str, Any],
    *,
    tokens_key: str,
    text_key: str,
) -> list[str]:
    if tokens_key in row and row[tokens_key]:
        tokens = row[tokens_key]
        if isinstance(tokens, str):
            return [token for token in TOKEN_PATTERN.findall(tokens.lower()) if token]
        return [
            token
            for token in (str(value).strip().lower() for value in tokens)
            if token
        ]
    text = str(row.get(text_key, "")).lower()
    return TOKEN_PATTERN.findall(text)


def _leiden_partition_class(leidenalg, objective: str):
    if objective == "modularity":
        return leidenalg.ModularityVertexPartition
    if objective in {"rb", "rbconfiguration", "rb_configuration"}:
        return leidenalg.RBConfigurationVertexPartition
    raise ValueError(f"Unsupported Leiden objective: {objective}")


def _linspace(start: float, stop: float, count: int) -> list[float]:
    if count == 1:
        return [float(start)]
    step = (stop - start) / (count - 1)
    return [start + step * index for index in range(count)]


def _npmi(co_occurrence: int, x_count: int, y_count: int, total_count: int) -> float:
    if co_occurrence <= 0 or x_count <= 0 or y_count <= 0 or total_count <= 0:
        return -1.0
    p_xy = co_occurrence / total_count
    if p_xy >= 1.0:
        return 1.0
    p_x = x_count / total_count
    p_y = y_count / total_count
    pmi = math.log(p_xy / (p_x * p_y))
    return pmi / (-math.log(p_xy))


def _has_rank_2(points: Sequence[Sequence[float]], *, tolerance: float = 1e-12) -> bool:
    anchor = points[0]
    baseline = None
    for point in points[1:]:
        delta = (point[0] - anchor[0], point[1] - anchor[1])
        if abs(delta[0]) > tolerance or abs(delta[1]) > tolerance:
            baseline = delta
            break
    if baseline is None:
        return False
    for point in points[1:]:
        delta = (point[0] - anchor[0], point[1] - anchor[1])
        cross_product = baseline[0] * delta[1] - baseline[1] * delta[0]
        if abs(cross_product) > tolerance:
            return True
    return False


def _optional_dependency(module_name: str, message: str):
    try:
        return importlib.import_module(module_name)
    except ImportError as error:
        raise RuntimeError(message) from error


def _seeded_sort_key(seed: int, value: str) -> int:
    digest = hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _stable_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
