"""Independent period-topic discovery, evidence, and cautious thematic matching."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np

from .national_claim_topics import (
    NOISE,
    claim_weights,
    config,
    contrasts,
    current_labels,
    distributions,
    fit_topics,
    load_inputs,
    topic_evidence,
)
from .national_platforms import (
    DEFAULT_CUTOFF,
    GROUPS,
    ROOT,
    digest,
    read_rows,
    write_json,
    write_rows,
)

MINIMUM_CLAIMS = 50
MATCH_THRESHOLD = 0.8


def adjacent_matches(centroids: dict[str, dict[str, np.ndarray]]) -> list[dict]:
    matches = []
    periods = sorted(centroids)
    for previous, period in zip(periods, periods[1:]):
        if int(period[:4]) - int(previous[:4]) != 4:
            continue
        earlier, later = centroids[previous], centroids[period]
        if not earlier or not later:
            continue
        old_ids, new_ids = sorted(earlier), sorted(later)
        similarity = np.array([[later[b] @ earlier[a] for a in old_ids] for b in new_ids])
        for i, topic in enumerate(new_ids):
            j = int(np.argmax(similarity[i]))
            reverse = int(np.argmax(similarity[:, j]))
            score = float(similarity[i, j])
            matches.append(
                {
                    "period": period,
                    "topic_id": topic,
                    "previous_period": previous,
                    "previous_topic_id": old_ids[j],
                    "cosine_similarity": score,
                    "mutual_nearest": reverse == i,
                    "above_threshold": score >= MATCH_THRESHOLD,
                    "threshold": MATCH_THRESHOLD,
                    "interpretation": (
                        "candidate_thematic_continuity"
                        if score >= MATCH_THRESHOLD and reverse == i
                        else "uncertain_match_not_proof_of_new_topic"
                    ),
                    "warnings": "independent_partitions;source_composition;not_validated_identity",
                }
            )
    return matches


def prepare(corpus: Path, *, groups: tuple[str, ...] = GROUPS) -> dict:
    from .national_claim_topic_time import temporal_tables

    rows, embeddings, input_basis = load_inputs(corpus, groups)
    sources = read_rows(corpus / "complete_sources.csv")
    dates = temporal_tables(rows, [NOISE] * len(rows), sources, groups, 0.0001)
    dated = {r["document_id"]: int(r["period_start"]) for r in dates["temporal_document_dates.csv"]}
    settings = {
        **config(),
        "kmeans_clusters": [4, 6, 8, 12],
        "min_cluster_sizes": [30],
        "min_samples": [5],
        "representatives": 6,
        "max_claims_per_bundle": 2,
    }
    basis = {
        "inputs": input_basis,
        "settings": settings,
        "minimum_claims": MINIMUM_CLAIMS,
        "matching_threshold": MATCH_THRESHOLD,
        "implementation_sha256": NUMERICAL_IMPLEMENTATION,
        "date_rule": "Adoption then publication; same four-year periods as fixed-topic trends",
    }
    directory = corpus / "topics/evolution"
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "fit_manifest.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if (
            old.get("evolution_basis") == basis
            and old.get("outputs")
            and all(
                (directory / name).exists() and digest((directory / name).read_bytes()) == value
                for name, value in old.get("outputs", {}).items()
            )
        ):
            return {**old["summary"], "cache_reused": True}
    tables = {
        name: []
        for name in (
            "assignments.csv",
            "keywords.csv",
            "representatives.csv",
            "shares.csv",
            "contrasts.csv",
            "candidate_fits.csv",
            "balanced_refits.csv",
        )
    }
    fits, centroids = [], {}
    for first in sorted(set(dated.values())):
        indices = [i for i, row in enumerate(rows) if dated.get(row["document_id"]) == first]
        if not indices:
            continue
        period = f"{first}-{min(first + 3, int(DEFAULT_CUTOFF[:4]))}"
        selected = [rows[i] for i in indices]
        vectors = embeddings[indices]
        period_info = {
            "period": period,
            "period_start": first,
            "claims": len(selected),
            "documents": len({r["document_id"] for r in selected}),
            "groups_present": sorted({r["group"] for r in selected}),
        }
        if len(selected) < MINIMUM_CLAIMS:
            fits.append({**period_info, "status": "insufficient_evidence", "topics": 0})
            centroids[period] = {}
            continue
        assigned, _, fit, candidates, refits = fit_topics(selected, vectors, settings)
        assigned = [f"period-{first}-{t}" if t != NOISE else NOISE for t in assigned]
        keywords, examples = topic_evidence(selected, vectors, assigned, settings)
        shares = distributions(selected, assigned, groups)
        ratios = contrasts(shares, groups, settings["epsilon"])
        available = {
            view: {r["group"] for r in shares if r["view"] == view and r["available"]}
            for view in ("expanded", "strict")
        }
        ratios = [
            r for r in ratios if r["comparison"] != "vs_rest" or available[r["view"]] == set(groups)
        ]
        for ratio in ratios:
            ratio["warnings"] += (
                ";" if ratio["warnings"] else ""
            ) + "independent_period_taxonomy;single_period_not_annual_estimate"
        records = [
            {
                "claim_id": r["claim_id"],
                "topic_id": topic,
                "group": r["group"],
                "document_id": r["document_id"],
                "bundle_id": r["bundle_id"],
                "text_sha256": r["text_sha256"],
                "strict": r["strict"],
            }
            for r, topic in zip(selected, assigned, strict=True)
        ]
        for name, values in (
            ("assignments.csv", records),
            ("keywords.csv", keywords),
            ("representatives.csv", examples),
            ("shares.csv", shares),
            ("contrasts.csv", ratios),
            ("candidate_fits.csv", candidates),
            ("balanced_refits.csv", refits),
        ):
            tables[name].extend({"period": period, **r} for r in values)
        weights = claim_weights(selected)
        centroids[period] = {}
        for topic in sorted(set(assigned) - {NOISE}):
            use = np.array(assigned) == topic
            vector = np.average(vectors[use], axis=0, weights=weights[use])
            centroids[period][topic] = vector / max(float(np.linalg.norm(vector)), 1e-12)
        fits.append(
            {**period_info, "status": fit["status"], "topics": len(centroids[period]), "fit": fit}
        )
    tables["adjacent_matches.csv"] = adjacent_matches(centroids)
    tables["document_dates.csv"] = dates["temporal_document_dates.csv"]
    tables["date_exclusions.csv"] = dates["temporal_exclusions.csv"]
    tables["coverage.csv"] = dates["temporal_coverage.csv"]
    for name, values in tables.items():
        write_rows(directory / name, values)
    write_json(directory / "period_fits.json", fits)
    write_json(
        directory / "centroids.json",
        {
            period: {topic: vector.tolist() for topic, vector in values.items()}
            for period, values in centroids.items()
        },
    )
    summary = {
        "status": "complete",
        "periods": len(fits),
        "topics": sum(r["topics"] for r in fits),
        "claims_assigned": len(tables["assignments.csv"]),
        "claims_not_fitted": len(rows) - len(tables["assignments.csv"]),
        "groups": list(groups),
        "taxonomy": "Independent discovery in each period; numeric IDs do not match across fits",
        "qualification": (
            "Uses only each period's claims and embeddings for its PCA, clustering and keywords. "
            "Centroid matches are descriptive similarities, not proof of emergence, "
            "disappearance, splits, merges, stance change, or causal change."
        ),
    }
    write_json(
        manifest_path,
        {
            "basis": {"config": settings},
            "evolution_basis": basis,
            "summary": summary,
            "outputs": {
                name: digest((directory / name).read_bytes())
                for name in [*tables, "period_fits.json", "centroids.json"]
            },
        },
    )
    return {**summary, "cache_reused": False}


def plot(directory: Path, figures: Path, labels: dict, groups: tuple[str, ...]) -> None:
    from textwrap import fill

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    from .national_claim_plot_style import COLORS, house_style, save_figure
    from .national_platform_kde import LABELS

    house_style()
    shares = read_rows(directory / "shares.csv")
    keywords = read_rows(directory / "keywords.csv")
    periods = list(dict.fromkeys(r["period"] for r in shares))
    for view in ("expanded", "strict"):
        destination = figures / "evolution" / view
        destination.mkdir(parents=True, exist_ok=True)
        for path in destination.glob("period_*.png"):
            path.unlink()
        for path in destination.glob("period_*.svg"):
            path.unlink()
        for period in periods:
            selected = [r for r in shares if r["period"] == period and r["view"] == view]
            topics = sorted(
                {r["topic_id"] for r in selected} - {NOISE},
                key=lambda t: -sum(float(r["share"] or 0) for r in selected if r["topic_id"] == t),
            )
            if not topics:
                continue
            topics += [NOISE]
            names = [
                "Unclustered (not a policy topic)"
                if t == NOISE
                else (
                    labels.get(t, {}).get("title")
                    or " / ".join(r["term"] for r in keywords if r["topic_id"] == t)[:70]
                    + " [keyword-only]"
                )
                for t in topics
            ]
            fig, axis = plt.subplots(
                figsize=(13, max(4.5, len(topics) * 0.60 + 1.8)), layout="constrained"
            )
            for group in groups:
                lookup = {r["topic_id"]: r for r in selected if r["group"] == group}
                if not any(r["available"] == "True" for r in lookup.values()):
                    continue
                axis.scatter(
                    [float(lookup[t]["share"]) for t in topics],
                    range(len(topics)),
                    color=COLORS[group],
                    label=LABELS[group],
                    s=32,
                    zorder=3,
                )
            axis.set_yticks(range(len(topics)), [fill(name, 43) for name in names])
            axis.invert_yaxis()
            axis.set_xlim(left=0)
            axis.xaxis.set_major_formatter(PercentFormatter(1))
            axis.grid(axis="x")
            axis.set_axisbelow(True)
            axis.set_title(f"Topics discovered in {period} | {view}", loc="left", pad=18)
            axis.set_xlabel(
                "Weighted share within observed period; independent period taxonomy.\n"
                "Missing organizations are omitted, not zero. Final period is partial."
            )
            axis.legend(frameon=False, loc="best")
            save_figure(fig, destination / f"period_{period}")
            plt.close(fig)


def report_section(directory: Path, figures: Path, labels: dict) -> str:
    from .national_platform_kde import LABELS

    fits = json.loads((directory / "period_fits.json").read_text())
    shares = read_rows(directory / "shares.csv")
    matches = read_rows(directory / "adjacent_matches.csv")
    examples = read_rows(directory / "representatives.csv")
    data = f"../{directory.resolve().relative_to(ROOT.resolve()).as_posix()}"
    images = f"../{figures.resolve().relative_to(ROOT.resolve()).as_posix()}/evolution"
    reviewed = sum(r.get("review_status") == "evidence_reviewed" for r in labels.values())
    revised = sum(
        r.get("label_origin") == "assistant_source_bound_revision" for r in labels.values()
    )
    lines = [
        "### Independently discovered topics within each period",
        "",
        "Unlike the fixed-topic trends above, each period gets its own PCA, clustering, "
        "keywords and evidence packets, using only documents observed in that period. "
        "The number and meaning of clusters can differ. The strict view reuses that "
        "period's expanded assignments; it does not fit sparse adopted-only evidence separately.",
        "",
        "Names summarize bounded local-Gemma evidence packets, not a pre-existing policy "
        "taxonomy. Source-bound assistant revisions are identified below and in the "
        "review record; original model replies remain unchanged.",
        "",
        f"**Evidence review:** {reviewed}/{sum(r['topics'] for r in fits)} period-topic labels "
        f"reviewed against bounded representative claims; {revised} source-bound assistant "
        "revisions. This is not independent human gold or whole-cluster validation.",
        "",
        "Adjacent-period centroid cosine similarities suggest possible thematic continuity. "
        "Only mutual nearest matches above 0.80 are called candidates. Neither a low similarity "
        "nor an unmatched topic proves that an issue first appeared or disappeared. Source "
        "coverage, rhetorical framing and cluster boundaries can all change.",
        "",
        f"[Period fits and diagnostics]({data}/period_fits.json) · "
        f"[Within-period shares]({data}/shares.csv) · "
        f"[Within-period contrasts and warnings]({data}/contrasts.csv) · "
        f"[Adjacent-period similarities]({data}/adjacent_matches.csv) · "
        f"[Representative source evidence]({data}/representatives.csv) · "
        f"[Label review and provenance]({data}/label_review.json) · "
        f"[Period coverage]({data}/coverage.csv)",
        "",
    ]
    groups = json.loads((directory / "fit_manifest.json").read_text())["summary"]["groups"]
    for fit in fits:
        period = fit["period"]
        selected_fit = fit.get("fit", {}).get("selected_parameters", {})
        lines += [
            f"#### {period}: observed themes",
            "",
            f"{fit['claims']:,} claims from {fit['documents']} documents; "
            f"{fit['topics']} independently discovered topics. "
            f"Fit status: {fit['status']}. "
            + (
                f"Cosine silhouette: {selected_fit['cosine_silhouette']:.3f}."
                if selected_fit
                else ""
            ),
            "",
        ]
        if selected_fit:
            lines += [
                f"Method: `{selected_fit['method']}`; "
                f"unweighted assignment coverage: {selected_fit['coverage']:.1%}. "
                "Low separation and mixed narrative clusters limit policy interpretation. "
                + (
                    "Two broad clusters plus substantial unclustered mass are not a complete "
                    "account of the issues discussed."
                    if fit["topics"] == 2 and selected_fit["coverage"] < 1
                    else ""
                ),
                "",
            ]
        if not fit["topics"]:
            lines += ["Insufficient evidence for substantive period-topic discovery.", ""]
            continue
        for view in ("expanded", "strict"):
            lines += [
                f"**{view.capitalize()} reading:** topic shares below are within this period, "
                "not measurements of a permanent political position.",
                "",
            ]
            for group in groups:
                ranked = sorted(
                    [
                        r
                        for r in shares
                        if r["period"] == period
                        and r["view"] == view
                        and r["group"] == group
                        and r["topic_id"] != NOISE
                        and r["available"] == "True"
                    ],
                    key=lambda r: -float(r["share"]),
                )
                if not ranked:
                    lines.append(f"- {LABELS[group]}: no observed documents in this view.")
                    continue
                leading = [
                    f"{labels.get(r['topic_id'], {}).get('title', r['topic_id'])} "
                    f"({float(r['share']):.1%})"
                    for r in ranked[:2]
                ]
                lines.append(
                    f"- {LABELS[group]}: "
                    + "; ".join(leading)
                    + f". Based on {ranked[0]['group_bundles']} bundle(s); "
                    + "unclustered share "
                    + next(
                        f"{float(r['share']):.1%}"
                        for r in shares
                        if r["period"] == period
                        and r["view"] == view
                        and r["group"] == group
                        and r["topic_id"] == NOISE
                    )
                    + ". Source composition limits interpretation."
                )
            lines += [
                "",
                f"![Period-specific topics, {view}]({images}/{view}/period_{period}.png)",
                "",
            ]
        lines += [
            "| Period topic | Closest preceding theme | Cosine | Interpretation |",
            "|---|---|---:|---|",
        ]
        for match in matches:
            if match["period"] == period:
                title = labels.get(match["topic_id"], {}).get("title", match["topic_id"])
                previous = labels.get(match["previous_topic_id"], {}).get(
                    "title", match["previous_topic_id"]
                )
                lines.append(
                    f"| {title} | {previous} ({match['previous_period']}) | "
                    f"{float(match['cosine_similarity']):.3f} | {match['interpretation']} |"
                )
        lines += ["", "Period-specific label summaries and inspectable source examples:", ""]
        for topic in sorted({r["topic_id"] for r in shares if r["period"] == period} - {NOISE}):
            label = labels.get(topic, {})
            lines += [
                f"**{label.get('title', topic)}** (`{topic}`): "
                + label.get("summary", "Keyword-only label; local-model summary unavailable."),
                "",
                f"Caveat: {label.get('caveat') or 'Mixed positions can share a subject.'}",
                "",
            ]
            if label.get("label_origin") == "assistant_source_bound_revision":
                lines += [
                    "**Provenance:** source-bound assistant revision; original Gemma "
                    "response retained unchanged.",
                    "",
                ]
            for example in [r for r in examples if r["topic_id"] == topic][:2]:
                text = example["claim_text"].replace("\n", " ")
                lines += [
                    f"> {text}",
                    "",
                    f"{LABELS[example['group']]} — [{example['title']}]({example['source_url']}); "
                    f"`{example['claim_id']}`.",
                    "",
                ]
    return "\n".join(line.rstrip() for line in lines)


def generate(corpus: Path, figures: Path, *, prepare_if_missing: bool = True) -> dict:
    directory = corpus / "topics/evolution"
    if not (directory / "fit_manifest.json").exists() and not prepare_if_missing:
        return {"status": "not_prepared"}
    pooled = json.loads((corpus / "topics/fit_manifest.json").read_text())
    if prepare_if_missing:
        summary = prepare(corpus, groups=tuple(pooled["summary"]["groups"]))
    else:
        manifest = json.loads((directory / "fit_manifest.json").read_text())
        _, _, inputs = load_inputs(corpus, tuple(pooled["summary"]["groups"]))
        expected_settings = {
            **config(),
            "kmeans_clusters": [4, 6, 8, 12],
            "min_cluster_sizes": [30],
            "min_samples": [5],
            "representatives": 6,
            "max_claims_per_bundle": 2,
        }
        basis = manifest["evolution_basis"]
        if (
            basis["inputs"] != inputs
            or basis["implementation_sha256"] != NUMERICAL_IMPLEMENTATION
            or basis["settings"] != expected_settings
            or basis["minimum_claims"] != MINIMUM_CLAIMS
            or basis["matching_threshold"] != MATCH_THRESHOLD
            or not manifest.get("outputs")
            or any(
                not (directory / name).exists() or digest((directory / name).read_bytes()) != sha
                for name, sha in manifest["outputs"].items()
            )
        ):
            raise ValueError(
                "Stale period topics: run evolution-prepare explicitly before rendering"
            )
        summary = {**manifest["summary"], "cache_reused": True}
    labels = current_labels(directory)
    write_json(directory / "topic_labels.json", list(labels.values()))
    summary = {
        **summary,
        "labels_available": len(labels),
        "reviewed_labels": sum(
            r.get("review_status") == "evidence_reviewed" for r in labels.values()
        ),
        "assistant_revised_labels": sum(
            r.get("label_origin") == "assistant_source_bound_revision" for r in labels.values()
        ),
    }
    write_json(directory / "summary.json", summary)
    plot(directory, figures, labels, tuple(pooled["summary"]["groups"]))
    return summary


NUMERICAL_IMPLEMENTATION = digest(
    "\n".join(inspect.getsource(function) for function in (adjacent_matches, prepare))
)
