"""Three-organization national-platform analysis, isolated from legacy outputs."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
from sklearn.cluster import HDBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.manifold import trustworthiness
from sklearn.neighbors import KernelDensity
from sklearn.preprocessing import StandardScaler

from .national_platforms import (
    DEFAULT_CUTOFF,
    GROUPS,
    LEDGER,
    MAX_LENGTH,
    OUTPUT,
    RAW,
    ROOT,
    SUPPORTED_GROUPS,
    date_bounds,
    digest,
    fetch_sources,
    load_ledger,
    prepare_corpus,
    read_rows,
    write_json,
    write_rows,
)
from .provisional_kde import (
    MODEL_NAME,
    MODEL_REVISION,
    SEED,
    balanced_kde_sample_indices,
    select_dimension_elbow,
)

FIGURES = ROOT / "figures/national_platforms"
REPORT = ROOT / "report/national_platform_analysis.md"
LABELS = {
    "democratic": "Democratic",
    "republican": "Republican",
    "dsa": "DSA",
    "libertarian": "Libertarian",
}
COLORS = {
    "democratic": "#47758a",
    "republican": "#a4584b",
    "dsa": "#8b7453",
    "libertarian": "#786494",
}
PAIRS = tuple(combinations(GROUPS, 2))


def balance_weights(rows: list[dict], indices: list[int]) -> np.ndarray:
    counts = Counter(rows[index]["bundle_id"] for index in indices)
    return np.array([1.0 / counts[rows[index]["bundle_id"]] for index in indices])


def fit_indices(rows: list[dict], *, groups: tuple[str, ...] = GROUPS) -> dict[str, list[int]]:
    counts = Counter(row["group"] for row in rows)
    if (
        len(groups) < 2
        or len(set(groups)) != len(groups)
        or set(groups) - set(SUPPORTED_GROUPS)
        or set(counts) - set(groups)
    ):
        raise ValueError(
            "Analysis groups must be distinct supported organizations covering all rows"
        )
    if any(counts[group] < 10 for group in groups):
        raise ValueError("At least ten eligible passages per organization are required")
    limit = min(counts.values())
    selected = {}
    for group in groups:
        units = {row["bundle_id"] for row in rows if row["group"] == group}
        if limit < len(units):
            raise ValueError("Balanced sample cannot represent every document/bundle")
        selected[group] = balanced_kde_sample_indices(
            [{**row, "support_unit_ids": row["bundle_id"]} for row in rows],
            group=group,
            limit=limit,
            seed=SEED,
        )
    return selected


def pairwise_scores(
    log_densities: dict[str, np.ndarray], *, groups: tuple[str, ...] = GROUPS
) -> dict[str, np.ndarray]:
    return {
        f"{first}_vs_{second}": log_densities[first] - log_densities[second]
        for first, second in combinations(groups, 2)
    }


def embedding_key(rows: list[dict], max_length: int = MAX_LENGTH) -> dict:
    return {
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "max_length": max_length,
        "normalization": "l2",
        "ordered_text_hash": digest("\n".join(digest(row["text"]) for row in rows)),
        "segment_count": len(rows),
        "embedding_dimensions": 768,
    }


def encode(
    rows: list[dict],
    directory: Path,
    *,
    batch_size: int = 48,
    download_model: bool = False,
    force: bool = False,
) -> tuple[np.ndarray, bool]:
    key = embedding_key(rows)
    manifest_path, array_path = directory / "embedding_manifest.json", directory / "embeddings.npy"
    if not force and manifest_path.exists() and array_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            array = np.load(array_path, allow_pickle=False)
            valid = (
                manifest == key
                and array.shape == (len(rows), 768)
                and np.isfinite(array).all()
                and np.allclose(np.linalg.norm(array, axis=1), 1, atol=1e-3)
            )
        except (OSError, ValueError):
            valid = False
        if valid:
            return array, True
    import torch
    from sentence_transformers import SentenceTransformer

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = SentenceTransformer(
        MODEL_NAME,
        revision=MODEL_REVISION,
        trust_remote_code=True,
        local_files_only=not download_model,
        device=device,
    )
    model.max_seq_length = MAX_LENGTH
    array = model.encode(
        [row["text"] for row in rows],
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    )
    if array.shape != (len(rows), 768) or not np.isfinite(array).all():
        raise ValueError("Encoder produced invalid embeddings")
    np.save(array_path, array)
    write_json(manifest_path, key)
    return array, False


def analyze_view(
    rows: list[dict],
    embeddings: np.ndarray,
    directory: Path,
    *,
    groups: tuple[str, ...] = GROUPS,
) -> dict:
    import umap

    directory.mkdir(parents=True, exist_ok=True)
    try:
        samples = fit_indices(rows, groups=groups)
    except ValueError as error:
        for filename in (
            "scored_passages.csv",
            "sampling.csv",
            "regions.csv",
            "clustering_audit.csv",
            "dimension_sweep.csv",
            "document_chronology.csv",
            "pairwise_summary.csv",
        ):
            (directory / filename).unlink(missing_ok=True)
        summary = {
            "status": "insufficient_evidence",
            "groups": list(groups),
            "reason": str(error),
            "group_passages": dict(Counter(row["group"] for row in rows)),
            "group_documents": {
                group: len({row["document_id"] for row in rows if row["group"] == group})
                for group in groups
            },
        }
        write_json(directory / "summary.json", summary)
        return summary
    indices = sorted(index for values in samples.values() for index in values)
    count = len(indices)
    neighbors = min(15, count - 1)
    trust_neighbors = min(5, (count - 1) // 2)
    dimensions = [dimension for dimension in (2, 5, 10, 20, 30) if dimension < count - 1]
    sweep, reducers = [], {}
    for dimension in dimensions:
        reducer = umap.UMAP(
            n_neighbors=neighbors,
            min_dist=0.1,
            metric="cosine",
            n_components=dimension,
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
                        n_neighbors=trust_neighbors,
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
    densities = {}
    bandwidth = len(samples[groups[0]]) ** (-1.0 / (selected + 4))
    for group in groups:
        estimator = KernelDensity(kernel="gaussian", bandwidth=bandwidth).fit(
            standardized[samples[group]],
            sample_weight=balance_weights(rows, samples[group]),
        )
        densities[group] = estimator.score_samples(standardized)
    scores = pairwise_scores(densities, groups=groups)
    sampled = set(indices)
    scored = []
    for index, row in enumerate(rows):
        scored.append(
            {
                **row,
                "umap_x": float(visual[index, 0]),
                "umap_y": float(visual[index, 1]),
                "sampled": index in sampled,
                **{f"{group}_log_density": float(densities[group][index]) for group in groups},
                **{pair: float(values[index]) for pair, values in scores.items()},
            }
        )
    regions, cluster_audit = region_summaries(rows, standardized, densities, scores, groups=groups)
    documents = document_chronology(rows, embeddings)
    diagnostics = density_diagnostics(rows, scores, groups=groups)
    summary = {
        "status": "complete",
        "groups": list(groups),
        "dimensions": selected,
        "bandwidth": bandwidth,
        "seed": SEED,
        "group_passages": dict(Counter(row["group"] for row in rows)),
        "group_documents": {
            group: len({row["document_id"] for row in rows if row["group"] == group})
            for group in groups
        },
        "group_bundles": {
            group: len({row["bundle_id"] for row in rows if row["group"] == group})
            for group in groups
        },
        "group_sample_sizes": {group: len(values) for group, values in samples.items()},
        "region_count": len(regions),
        "document_types": {
            group: dict(
                Counter(
                    {
                        row["document_id"]: row["document_type"]
                        for row in rows
                        if row["group"] == group
                    }.values()
                )
            )
            for group in groups
        },
        "weighting": "Equal organization samples; equal document/fallback-period-bundle KDE mass",
        "density_space": "Standardized selected-dimensional shared UMAP; 2D is display only",
    }
    write_rows(directory / "dimension_sweep.csv", sweep)
    write_rows(directory / "scored_passages.csv", scored)
    write_rows(
        directory / "regions.csv",
        regions,
        fields=[
            "pair",
            "zone",
            "cluster",
            "passages",
            "documents",
            "bundles",
            "terms",
            "group_support",
            "segment_id",
            "document_id",
            "source_url",
            "locator",
            "excerpt",
        ],
    )
    write_rows(directory / "clustering_audit.csv", cluster_audit)
    write_rows(directory / "document_chronology.csv", documents)
    write_rows(directory / "pairwise_summary.csv", diagnostics)
    write_rows(
        directory / "sampling.csv",
        [
            {
                "segment_id": rows[index]["segment_id"],
                "group": group,
                "bundle_id": rows[index]["bundle_id"],
                "weight": float(weight),
            }
            for group in groups
            for index, weight in zip(
                samples[group], balance_weights(rows, samples[group]), strict=True
            )
        ],
    )
    write_json(directory / "summary.json", summary)
    return {
        **summary,
        "_scored": scored,
        "_documents": documents,
        "_regions": regions,
        "_diagnostics": diagnostics,
    }


def density_diagnostics(
    rows: list[dict], scores: dict, *, groups: tuple[str, ...] = GROUPS
) -> list[dict]:
    result = []
    for first, second in combinations(groups, 2):
        pair = f"{first}_vs_{second}"
        for group in (first, second):
            indices = [index for index, row in enumerate(rows) if row["group"] == group]
            weights = balance_weights(rows, indices)
            result.append(
                {
                    "pair": pair,
                    "source_group": group,
                    "weighted_fraction_favoring_first": float(
                        np.average(
                            scores[pair][indices] > 0,
                            weights=weights,
                        )
                    ),
                    "weighted_mean_log_ratio": float(
                        np.average(
                            scores[pair][indices],
                            weights=weights,
                        )
                    ),
                    "qualification": (
                        "Descriptive fitted-density diagnostic, not accuracy or policy agreement; "
                        "coordinate systems refit separately across views"
                    ),
                }
            )
    return result


def region_summaries(
    rows, coordinates, densities, scores, *, groups: tuple[str, ...] = GROUPS
) -> tuple[list[dict], list[dict]]:
    regions, audit = [], []
    for first, second in combinations(groups, 2):
        pair = f"{first}_vs_{second}"
        eligible = np.array([row["group"] in {first, second} for row in rows])
        values = scores[pair]
        shared_limit = np.quantile(np.abs(values[eligible]), 0.25)
        joint = np.minimum(densities[first], densities[second])
        shared_mask = eligible & (np.abs(values) <= shared_limit)
        shared_density = np.median(joint[shared_mask])
        masks = {
            "shared_language": shared_mask & (joint >= shared_density),
            f"{first}_relative": (
                eligible
                & (np.array([row["group"] == first for row in rows]))
                & (
                    values
                    >= np.quantile(
                        values[[r["group"] == first for r in rows]],
                        0.75,
                    )
                )
            ),
            f"{second}_relative": (
                eligible
                & (np.array([row["group"] == second for row in rows]))
                & (
                    values
                    <= np.quantile(
                        values[[r["group"] == second for r in rows]],
                        0.25,
                    )
                )
            ),
        }
        for zone, mask in masks.items():
            zone_indices = np.flatnonzero(mask)
            if len(zone_indices) < 10:
                audit.append(
                    {
                        "pair": pair,
                        "zone": zone,
                        "passages": len(zone_indices),
                        "noise": len(zone_indices),
                        "retained_regions": 0,
                    }
                )
                continue
            labels = HDBSCAN(
                min_cluster_size=5,
                min_samples=3,
                allow_single_cluster=False,
                cluster_selection_method="leaf",
                copy=True,
            ).fit_predict(coordinates[zone_indices])
            candidates = []
            for label in sorted(set(labels) - {-1}):
                members = [int(i) for i in zone_indices[labels == label]]
                units = {rows[i]["bundle_id"] for i in members}
                if len(units) < 2:
                    continue
                groups = {rows[i]["group"] for i in members}
                if zone == "shared_language" and groups != {first, second}:
                    continue
                vectorizer = TfidfVectorizer(stop_words="english", max_features=500)
                try:
                    matrix = vectorizer.fit_transform([rows[i]["text"] for i in members])
                except ValueError:
                    continue
                terms = vectorizer.get_feature_names_out()
                top = np.argsort(np.asarray(matrix.mean(axis=0)).ravel())[-4:][::-1]
                centroid = coordinates[members].mean(axis=0)
                nearest = min(
                    members,
                    key=lambda i: float(np.linalg.norm(coordinates[i] - centroid)),
                )
                source = rows[nearest]
                candidates.append(
                    {
                        "pair": pair,
                        "zone": zone,
                        "cluster": int(label),
                        "passages": len(members),
                        "documents": len({rows[i]["document_id"] for i in members}),
                        "bundles": len(units),
                        "terms": ", ".join(terms[top]),
                        "group_support": json.dumps(
                            dict(Counter(rows[i]["group"] for i in members))
                        ),
                        "segment_id": source["segment_id"],
                        "document_id": source["document_id"],
                        "source_url": source["source_url"],
                        "locator": source["locator"],
                        "excerpt": " ".join(source["text"].split()[:25]),
                    }
                )
            retained = sorted(candidates, key=lambda row: (-row["passages"], row["cluster"]))[:2]
            regions.extend(retained)
            audit.append(
                {
                    "pair": pair,
                    "zone": zone,
                    "passages": len(zone_indices),
                    "noise": int(np.sum(labels == -1)),
                    "retained_regions": len(retained),
                }
            )
    return regions, audit


def document_chronology(rows: list[dict], embeddings: np.ndarray) -> list[dict]:
    by_doc = defaultdict(list)
    for index, row in enumerate(rows):
        by_doc[row["document_id"]].append(index)
    documents, centroids = [], {}
    for identifier, indices in by_doc.items():
        vector = embeddings[indices].mean(axis=0)
        vector /= max(np.linalg.norm(vector), 1e-12)
        centroids[identifier] = vector
        source = rows[indices[0]]
        documents.append(
            {
                key: source[key]
                for key in [
                    "document_id",
                    "group",
                    "title",
                    "publication_date",
                    "document_type",
                    "bundle_id",
                    "source_url",
                ]
            }
        )
        documents[-1].update(
            {
                "adoption_date": source.get("adoption_date", ""),
                "version_date": source.get("version_date", ""),
            }
        )
    documents.sort(key=lambda row: (row["group"], row["publication_date"], row["document_id"]))
    previous = {}
    for row in documents:
        prior = previous.get(row["group"])
        row["previous_document_id"] = prior or ""
        row["cosine_distance_from_previous"] = (
            float(np.clip(1 - centroids[row["document_id"]] @ centroids[prior], 0, 2))
            if prior
            else ""
        )
        row["qualification"] = "Document language change; not an ideology scale or annual estimate"
        previous[row["group"]] = row["document_id"]
    return documents


def plot_outputs(result: dict, coverage: list[dict], figures: Path = FIGURES) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm

    def publication_year(value):
        lower, upper = date_bounds(value)
        start = lower.replace(month=1, day=1)
        days = (start.replace(year=start.year + 1) - start).days
        return lower.year + ((lower - start).days + (upper - lower).days / 2) / days

    groups = tuple(result.get("groups", GROUPS))
    pairs = tuple(combinations(groups, 2))
    figures.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.facecolor": "white",
        }
    )
    if result["status"] == "complete":
        rows = result["_scored"]
        panel_rows = (len(pairs) + 2) // 3
        fig, axes = plt.subplots(
            panel_rows, 3, figsize=(13, 4.2 * panel_rows), sharex=True, sharey=True, squeeze=False
        )
        axes = axes.ravel()
        fig.subplots_adjust(bottom=0.25 if panel_rows == 1 else 0.14, right=0.92, wspace=0.08)
        for axis in axes[len(pairs) :]:
            axis.set_visible(False)
        for coordinate, set_limits in (
            ("umap_x", axes[0].set_xlim),
            ("umap_y", axes[0].set_ylim),
        ):
            values = [r[coordinate] for r in rows]
            padding = max(float(np.ptp(values)) * 0.05, 1e-6)
            set_limits(min(values) - padding, max(values) + padding)
        all_values = [
            abs(row[f"{a}_vs_{b}"]) for a, b in pairs for row in rows if row["group"] in {a, b}
        ]
        bound = max(float(np.quantile(all_values, 0.95)), 1e-6)
        norm = TwoSlopeNorm(vmin=-bound, vcenter=0, vmax=bound)
        for axis, (first, second) in zip(axes[: len(pairs)], pairs, strict=True):
            selected = [r for r in rows if r["group"] in {first, second}]
            image = axis.scatter(
                [r["umap_x"] for r in selected],
                [r["umap_y"] for r in selected],
                c=[r[f"{first}_vs_{second}"] for r in selected],
                cmap="RdBu",
                norm=norm,
                s=7,
                alpha=0.7,
                linewidths=0,
                rasterized=True,
            )
            axis.set_title(f"{LABELS[first]} / {LABELS[second]}", fontsize=11, loc="left")
            axis.set_xticks([])
            axis.set_yticks([])
            axis.set_xlabel("Shared 2D semantic display")
            label_bounds = []
            for zone in (f"{first}_relative", f"{second}_relative", "shared_language"):
                regions = [
                    r
                    for r in result["_regions"]
                    if r["pair"] == f"{first}_vs_{second}" and r["zone"] == zone
                ]
                if not regions:
                    continue
                evidence = next(r for r in selected if r["segment_id"] == regions[0]["segment_id"])
                position = np.array([evidence["umap_x"], evidence["umap_y"]])
                x_min, x_max = axis.get_xlim()
                fraction = (position[0] - x_min) / (x_max - x_min)
                align = "left" if fraction < 0.2 else "right" if fraction > 0.8 else "center"
                label = axis.text(
                    *position,
                    " / ".join(regions[0]["terms"].split(", ")[:2]),
                    fontsize=8,
                    color="#333333",
                    ha=align,
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 2},
                )
                fig.canvas.draw()
                bounds = label.get_window_extent(fig.canvas.get_renderer()).expanded(1.06, 1.3)
                if any(bounds.overlaps(other) for other in label_bounds):
                    label.remove()
                else:
                    label_bounds.append(bounds)
        bar = fig.colorbar(
            image,
            cax=fig.add_axes(
                (0.94, 0.29, 0.012, 0.53) if panel_rows == 1 else (0.94, 0.22, 0.012, 0.65)
            ),
        )
        bar.set_label("Log density ratio: + first / − second", fontsize=9)
        fig.text(
            0.08,
            0.07 if panel_rows == 1 else 0.045,
            "Densities estimated in the higher-dimensional shared space. "
            "Color indicates relative language density, not policy agreement.",
            fontsize=9,
            color="#555555",
        )
        fig.savefig(figures / "pairwise_density.png", dpi=190)
        fig.savefig(figures / "pairwise_density.svg")
        plt.close(fig)
        fig, axis = plt.subplots(figsize=(9, 3.8))
        for group in groups:
            docs = [r for r in result["_documents"] if r["group"] == group]
            for fallback in (False, True):
                selected = [
                    r
                    for r in docs
                    if (r["document_type"] not in {"platform", "program"}) == fallback
                    and r["cosine_distance_from_previous"] != ""
                ]
                if not selected:
                    continue
                axis.scatter(
                    [publication_year(r["publication_date"]) for r in selected],
                    [r["cosine_distance_from_previous"] for r in selected],
                    color=COLORS[group],
                    marker="x" if fallback else "o",
                    s=25 if fallback else 38,
                    alpha=0.65 if fallback else 1,
                    label=f"{LABELS[group]}{' fallback' if fallback else ''}",
                )
        axis.set_xlim(1999.5, 2027)
        axis.set_ylabel("Change from preceding document\n(cosine distance)")
        axis.set_xlabel("Document year (gaps are not interpolated)")
        axis.legend(frameon=False, fontsize=8, ncol=len(groups))
        fig.tight_layout()
        fig.savefig(figures / "document_change.png", dpi=180)
        plt.close(fig)
    else:
        for filename in ("pairwise_density.png", "pairwise_density.svg", "document_change.png"):
            (figures / filename).unlink(missing_ok=True)
    fig, axis = plt.subplots(figsize=(11, 2.7 + max(0, len(groups) - 3) * 0.3))
    for index, group in enumerate(groups):
        for status, marker in [
            ("eligible", "o"),
            ("reused_document", "s"),
            ("other", "x"),
        ]:
            selected = [
                row
                for row in coverage
                if row["group"] == group
                and row["publication_date"]
                and (
                    row["status"] == status
                    if status != "other"
                    else row["status"] not in {"eligible", "reused_document"}
                )
            ]
            axis.scatter(
                [publication_year(row["publication_date"]) for row in selected],
                [index] * len(selected),
                marker=marker,
                c=COLORS[group],
                s=32,
                alpha=0.65,
                label={
                    "eligible": "Eligible source",
                    "reused_document": "Reused text",
                    "other": "Excluded / unresolved",
                }[status]
                if index == 0
                else None,
            )
    axis.set_yticks(range(len(groups)), [LABELS[g] for g in groups])
    axis.set_xlim(1999.5, 2027)
    axis.set_xticks(range(2000, 2027, 2))
    axis.set_xlabel("Publication year (known date precision); empty years do not imply no position")
    axis.legend(frameon=False, ncol=3, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 1.24))
    fig.tight_layout()
    fig.savefig(figures / "coverage.png", dpi=180)
    plt.close(fig)


def write_report(
    results: dict,
    coverage: list[dict],
    cutoff: str,
    report: Path = REPORT,
    sources_path: Path = OUTPUT / "complete_sources.csv",
) -> None:
    lines = [
        "# National platforms: Democratic, Republican, and DSA",
        "",
        f"National organizational documents, January 1, 2000 through {cutoff}. "
        "Candidate and state/local texts are excluded. This is a pooled comparison of "
        "recoverable language, not a continuous history of organizational positions.",
        "",
        "![Source chronology](../figures/national_platforms/coverage.png)",
        "",
        "## Corpus and sensitivity",
        "",
        "| View | Status | Democratic documents / passages | Republican documents / passages | "
        "DSA documents / passages |",
        "|---|---|---:|---:|---:|",
    ]
    for view, result in results.items():
        counts = [
            f"{result.get('group_documents', {}).get(group, 0)} / "
            f"{result.get('group_passages', {}).get(group, 0)}"
            for group in GROUPS
        ]
        lines.append(f"| {view} | {result['status']} | {' | '.join(counts)} |")
        if result["status"] != "complete":
            lines.extend(["", f"{view}: {result['reason']}", ""])
    lines.extend(
        [
            "",
            "The expanded view adds explicitly labeled DSA national statements/resolutions. "
            "The strict view uses adopted platforms/programs only. Each view fits its own "
            "balanced representation: map coordinates and numerical density scales are not "
            "directly comparable across views.",
            "",
            "The strict and expanded results both retain the same underlying party-platform "
            "documents; only labeled fallback evidence differs. DSA's recovered platforms are "
            "from 2021 onward, not a representative sample of its entire 2000–2026 history. "
            "The complete adopted 2021 platform is preserved in an immutable December 30, "
            "2021 archive snapshot, whose page metadata records publication and modification "
            "on November 9, 2021. It replaces the previously used API page modified in 2025; "
            "the versions are not counted as independent platforms.",
            "",
            "| View | Balanced passages per organization | KDE dimensions | "
            "DSA source composition |",
            "|---|---:|---:|---|",
        ]
    )
    for view, result in results.items():
        composition = result.get("document_types", {}).get("dsa", {})
        sample_size = result.get("group_sample_sizes", {}).get("dsa", 0)
        lines.append(
            f"| {view} | {sample_size} | {result.get('dimensions', '—')} | "
            f"{', '.join(f'{count} {kind}' for kind, count in composition.items())} |"
        )
    lines.extend(
        [
            "",
            "The per-view `pairwise_summary.csv` records document/bundle-weighted density "
            "preferences. These fitted-sample diagnostics are not classifier accuracy, "
            "policy agreement rates, or directly comparable log-density scales. Smaller "
            "DSA corpora constrain both balanced fits. Sparse support and UMAP sampling "
            "make individual exploratory regions unstable; reviewed policy examples below "
            "are established from sources independently of those regions.",
            "",
            "## Pooled semantic comparison",
            "",
            "![Pairwise density](../figures/national_platforms/pairwise_density.png)",
            "",
            "All three densities share one representation within each view. Positive log ratios "
            "favor the first organization in a panel; negative ratios favor the second. "
            "Shared language does not establish shared policy or agreement. Different decades "
            "and genres are pooled; historical composition can drive apparent distinctions.",
            "",
            "### Exploratory regions",
            "",
            "| Comparison | Relative-language zone | Terms | Passages / documents | "
            "Source evidence |",
            "|---|---|---|---:|---|",
        ]
    )
    for row in results["expanded"].get("_regions", []):
        lines.append(
            f"| {row['pair']} | {row['zone']} | {row['terms']} | "
            f"{row['passages']} / {row['documents']} | "
            f"`{row['segment_id']}`; {row['locator']} |"
        )
    lines.extend(
        [
            "",
            "Terms are descriptive TF-IDF labels, not independently reviewed policy categories. "
            "HDBSCAN regions require at least two independent document/period bundles; noise "
            "and retained-region counts are recorded in `clustering_audit.csv`. Shared regions "
            "must contain "
            "passages from both organizations. At most two regions per "
            "pairwise zone are shown. Source-linked short excerpts are in `regions.csv`; "
            "complete passage text is in `scored_passages.csv`.",
            "",
            "## Document chronology",
            "",
            "![Document language change](../figures/national_platforms/document_change.png)",
            "",
            "Distances compare adjacent recovered document centroids within an organization "
            "in the original normalized GTE space, not on a left–right scale. Fallback "
            "statements and full platforms are different genres. Dates retain source "
            "precision; no annual interpolation is performed. First documents have no "
            "preceding observation. See each view's `document_chronology.csv`.",
            "",
            "## Source qualifications",
            "",
        ]
    )
    for row in coverage:
        if row["status"] != "eligible":
            lines.append(f"- **{row['document_id']}**: {row['status']}. {row['notes']}")
    lines.extend(
        [
            "",
            "Empty years in `year_coverage.csv` mean no recovered publication in this "
            "inventory, not that an organization had no platform or position. The GOP 2020 "
            "reuse record contributes no second independent copy of its 2016 text. "
            "The DSA 2025 R34 decision likewise retains the 2024 program until replacement "
            "without adding a second independent text; the adopted resolution and vote "
            "are retained in the full-text resolution inventory. "
            "Every currently exposed official statement-catalog entry from December 2012 "
            "through December 2020 was screened, with full included and excluded text "
            "preserved. This does not recover deleted pages or establish exhaustive coverage "
            "of other publication types or all historical years. See the source ledger, "
            "full-text historical statement inventory, fetch-attempt log, and "
            "`data/manual/national_platform_search_disposition.csv` for period-specific "
            "searches and explicit unsearched boundaries.",
            "",
            "## Methods and reproduction",
            "",
            f"GTE: `{MODEL_NAME}` at `{MODEL_REVISION}`, normalized embeddings; "
            f"maximum {MAX_LENGTH} tokens including special tokens. Long paragraphs are "
            "split on original character offsets; short fragments, page markers, and known "
            "magazine footers are excluded from model passages. Complete source extraction "
            "and exact scoped article text remain separately downloadable.",
            "",
            "UMAP uses deterministic, equal-sized organization samples stratified by "
            "document or predefined four-year DSA fallback bundle. KDE gives each sampled "
            "document/bundle equal total weight within its organization. Bundles need at "
            "least ten passages. Both sampling and weighting use the same units. The dimension "
            "sweep selects the smallest dimension within 0.005 trustworthiness of the maximum; "
            "KDE uses standardized selected-dimensional coordinates and Scott bandwidth. "
            "The 2D map is display-only; sparse corpora produce explicit insufficient-evidence "
            "results.",
            "",
            "```sh",
            "uv run dsa-analysis national-platform-analysis --fetch",
            "uv run dsa-analysis national-platform-analysis",
            "```",
            "",
            "Collection is explicit; the default command uses local captures (or hash-verified "
            "complete-text exports when captures are absent) and a cached "
            "model only. `--download-model` explicitly permits obtaining the pinned model. "
            "`--fetch-only` collects without running the model. No candidate pipeline runs.",
            "",
            "All outputs: `data/analysis/national_platforms/`. Downloads include "
            "`complete_sources.csv` and `.jsonl` (complete extracted and scoped texts), "
            "`passages.csv` (full model passages, not metadata alone), `coverage.csv`, "
            "`year_coverage.csv`, `historical_statement_inventory.csv` and `.jsonl` "
            "(complete text and screening reasons for every catalog entry), "
            "`historical_resolution_inventory.csv` and `.jsonl` (original convention "
            "documents and adoption evidence, including complete 2025 results with "
            "R34 separately scoped), `historical_strategy_inventory.csv` and `.jsonl` "
            "(all strategy-catalog texts and screening decisions), "
            "`historical_convention_inventory.csv` and `.jsonl` (complete 2019 proposals "
            "cross-referenced to final votes), `source_documents.zip` (individual complete "
            "texts, scoped texts, deduplicated original PDFs and a provenance manifest), "
            "`historical_document_link_disposition.csv` (all 61 final-results links and "
            "recovery outcomes), and the "
            "expanded/strict analysis tables. Sources retain "
            "their original attribution and rights; institutional reproductions are labeled "
            "as such rather than represented as party-hosted originals.",
            "",
            "Supplementary recovery records preserve the complete 2017 convention minutes, "
            "June 2019 proposal packet, official final 2019 results, and six original 2015 "
            "proposal PDFs without changing the fitted corpus or figures. All 85 proposals "
            "extracted from the June packet are retained with voting-status checks. All "
            "61 final-results links now have complete recovered documents: 60 original "
            "PDFs and R41's complete archived Google Doc text, including R34's base text, "
            "passed Amendment #1, and separately linked R74. Public archive captures "
            "recovered the 87-page Credentials Committee report, the 16-page Medicare "
            "for All report, and R41 after their live exports became unavailable. "
            "The live failures and successful archive routes remain recorded; R41 is "
            "also preserved independently in the public packet. Additional 2017 originals "
            "include the complete archived resolution proposal packet, the 18-page "
            "results/rationales PDF, and the 13-page harassment policy PDF. All 34 "
            "inserted-text operations from an independent archived viewer were checked "
            "against the complete packet, including final footnotes. The results PDF "
            "contains rationales rather than complete resolutions; the packet's later "
            "annotations do not establish blanket final adopted wording, and a live "
            "policy export is not independently a frozen 2017 capture. A "
            "pre-convention proposal is not automatically adopted: R34 passed as amended, "
            "so its unamended packet text is not verified final wording; candidate-specific "
            "R74 is absent from this packet. The full final 2015 strategy remains unrecovered.",
            "",
        ]
    )
    historical = [
        row
        for row in coverage
        if row["group"] == "dsa" and row["status"] == "eligible" and row["bundle_id"]
    ]
    if historical:
        recovery_lines = [
            "## Historical DSA recovery",
            "",
            "Recovered national resolutions include the 2001 priorities and war/terrorism "
            "texts, the complete 2003 priorities and accompanying policy resolutions, the "
            "2004 NPC resolution, the 2005 priorities, the November 2007 Economic Justice "
            "Agenda, the 2009 priorities, the full ten-page 2011 priorities and accompanying "
            "adopted resolutions, the complete 2013 and 2015 priorities, and the 2017 "
            "priorities. The 2011 full original replaces its magazine summary in model "
            "input; the summary remains in the full-text resolution inventory. The official "
            "Social and Economic Bill of Rights, identified as DSA's 2010 document in the "
            "adopted 2011 priorities, is recovered from its December 2012 republication. "
            "Its bundle follows republication because the original adoption date is not "
            "established. The 2016 strategy remains an explicitly labeled summary, not the "
            "unrecovered longer 2015 strategy. Complete original pages, PDFs and magazine "
            "issues remain downloadable, while model scopes remove other authors' articles, "
            "contents, repeated summaries, fundraising, internal administration and "
            "candidate-specific sections. Early scan OCR and print hyphenation are retained "
            "and can affect the semantic analysis.",
            "",
            "| Fallback period bundle | Eligible documents | Model passages |",
            "|---|---:|---:|",
        ]
        for bundle in sorted({row["bundle_id"] for row in historical}):
            documents = [row for row in historical if row["bundle_id"] == bundle]
            recovery_lines.append(
                f"| {bundle.removeprefix('dsa-fallback-')} | {len(documents)} | "
                f"{sum(int(row['passage_count']) for row in documents)} |"
            )
        inventory_path = sources_path.parent / "historical_statement_inventory.csv"
        if inventory_path.exists():
            inventory = read_rows(inventory_path)
            included = sum(row["screening_status"] == "included_fallback" for row in inventory)
            recovery_lines.extend(
                [
                    "",
                    f"The full-text historical statement inventory contains {len(inventory)} "
                    f"catalog records: {included} included as fallback evidence and "
                    f"{len(inventory) - included} excluded with individual reasons. "
                    "The rule retains nationally issued policy statements and broad policy "
                    "agendas, but excludes campaign endorsements/results-only pieces, "
                    "administration, personal tributes/case appeals, chapter authorship, "
                    "unverified affiliated-body-only positions, link indexes and duplicate "
                    "translations. Translations remain in complete downloads but do not "
                    "double-count model passages. Twelve-month or four-year coverage is "
                    "not inferred from a single document.",
                ]
            )
        recovery_lines.extend(
            [
                "",
                "The additional full-text recovery inventories screen all five linked 2003 "
                "resolution pages, recover all four visibly listed adopted 2011 resolutions "
                "(including the already modeled LGBTQ resolution, not counted twice), "
                "and retain every entry in the 14-record strategy catalog. The pre-2000 "
                "*Where We Stand* text is preserved as applicability context, not mislabeled "
                "as a new post-2000 platform. Other background essays are not promoted "
                "to adopted organizational policy merely because DSA hosts them.",
                "",
                "Bundles follow verified adoption periods where available and otherwise "
                "publication; December 2012 migration/republication dates are not original "
                "adoption dates. All six fallback period bundles meet the unchanged "
                "ten-passage gate, but this does not establish annual or comprehensive "
                "platform coverage. The 2000 editorial remains unverified and the full "
                "underlying 2015 strategy remains unrecovered despite checks of the "
                "convention report, archived convention/FAQ/agenda/resolution pages, "
                "strategy pages and official media catalogs. The 2015 priorities are a "
                "different, now recovered adopted resolution. The official 2025 "
                "post-convention compendium records R34 adopted unamended 900–291 after "
                "its substitute was rejected 532–651. R34 supersedes the 2021 platform "
                "and retains the current Workers Deserve More program pending revision. "
                "The October 16, 2025 site snapshot identifies that current text as the "
                "2024 program. This establishes 2025 reuse, not a newly written platform; "
                "the nominal 2025 PDF URL serving 2026-drafted content is not backdated.",
                "",
            ]
        )
        position = lines.index("## Pooled semantic comparison")
        lines[position:position] = recovery_lines
    findings = ROOT / "data/manual/national_platform_findings.csv"
    if findings.exists():
        sources = {row["document_id"]: row for row in read_rows(sources_path)}
        findings_lines = [
            "## Reviewed policy examples (2024)",
            "",
            "These matched-cycle examples distinguish common policy subjects from different "
            "proposed mechanisms. They come directly from available 2024 documents, not "
            "from KDE labels or a presumed ideological ordering.",
            "",
            "| Topic | Democratic | Republican | DSA |",
            "|---|---|---|---|",
        ]
        topics = defaultdict(dict)
        for row in read_rows(findings):
            if row["document_id"] not in sources:
                continue
            source = sources[row["document_id"]]
            if row["evidence"] not in source["scoped_text"]:
                raise ValueError(f"Untraceable finding: {row['document_id']} / {row['topic']}")
            topics[row["topic"]][row["group"]] = row["finding"]
        for topic, positions in topics.items():
            cells = " | ".join(positions.get(group, "Not recovered") for group in GROUPS)
            findings_lines.append(f"| {topic} | {cells} |")
        findings_lines.extend(
            [
                "",
                "The reviewed findings ledger records the source document identifier and "
                "an exact supporting span for every recovered cell "
                "and the report builder checks each against the complete source text. "
                "These examples do not imply that a document lacks other relevant proposals.",
                "",
            ]
        )
        if topics:
            position = lines.index("## Pooled semantic comparison")
            lines[position:position] = findings_lines
    if results["expanded"]["status"] != "complete":
        lines = [
            line
            for line in lines
            if not line.startswith(("![Pairwise density]", "![Document language change]"))
        ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_national_platform_analysis(
    *,
    ledger: Path = LEDGER,
    raw: Path = RAW,
    output: Path = OUTPUT,
    figures: Path = FIGURES,
    report: Path = REPORT,
    cutoff: str = DEFAULT_CUTOFF,
    fetch: bool = False,
    fetch_only: bool = False,
    batch_size: int = 48,
    download_model: bool = False,
    force_embeddings: bool = False,
) -> dict:
    rows = load_ledger(ledger)
    if fetch or fetch_only:
        fetch_sources(rows, raw)
    if fetch_only:
        return {"status": "sources_collected"}
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        revision=MODEL_REVISION,
        trust_remote_code=True,
        local_files_only=not download_model,
    )
    passages, coverage = prepare_corpus(rows, tokenizer, raw=raw, output=output, cutoff=cutoff)
    attempts = raw / "fetch_attempts.jsonl"
    if attempts.exists():
        (output / "fetch_attempts.jsonl").write_text(attempts.read_text(), encoding="utf-8")
    eligible = [row for row in passages if row["eligible"]]
    if not eligible:
        raise ValueError("No eligible captured passages; collect sources with --fetch first")
    print(f"Encoding {len(eligible)} eligible national passages", flush=True)
    embeddings, cached = encode(
        eligible,
        output,
        batch_size=batch_size,
        download_model=download_model,
        force=force_embeddings,
    )
    results = {}
    for view in ("expanded", "strict"):
        indices = [i for i, row in enumerate(eligible) if view == "expanded" or row["strict"]]
        print(f"Analyzing {view}: {len(indices)} passages", flush=True)
        results[view] = analyze_view(
            [eligible[i] for i in indices],
            embeddings[indices],
            output / view,
        )
    plot_outputs(results["expanded"], coverage, figures)
    write_report(results, coverage, cutoff, report, output / "complete_sources.csv")
    summary = {
        "cutoff": cutoff,
        "ledger_sha256": digest(ledger.read_bytes()),
        "embedding_cache_reused": cached,
        "source_status_counts": dict(Counter(row["status"] for row in coverage)),
        "views": {
            view: {key: value for key, value in result.items() if not key.startswith("_")}
            for view, result in results.items()
        },
    }
    write_json(output / "summary.json", summary)
    return summary
