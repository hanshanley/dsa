"""Export the completed three-organization analysis without running inference."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import struct
import subprocess
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path("data/analysis/national_claims/full")
FIGURES = Path("figures/national_claims/full/topics")
WEBSITE_FIGURES = Path("figures/national_claims/full/themarginoferror/topics")
GROUPS = ("democratic", "republican", "dsa")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path):
    csv.field_size_limit(32 * 1024 * 1024)
    with path.open(encoding="utf-8", newline="") as stream:
        yield from csv.DictReader(stream, strict=True)


def validate(source: Path) -> tuple[dict, dict, list, list, list]:
    source = source.resolve()
    data = source / DATA
    summary = read_json(data / "analysis_summary.json")
    topics = read_json(data / "topics/summary.json")
    audit = read_json(data / "topics/replay_audit.json")
    labels = read_json(data / "topics/topic_labels.json")
    if (
        audit["status"] != "complete"
        or audit["label_inference_called"] is not False
        or audit["numerical_cache_reused"] is not True
        or topics["labeling_status"] != "complete"
        or topics["reviewed_labels"] != len(labels)
        or topics["topics"] != len(labels)
        or topics["claims"] != summary["claims"]
        or audit["claims"] != summary["claims"]
        or audit["reviewed_labels"] != len(labels)
        or audit["fit_manifest_sha256"] != topics["fit_manifest_sha256"]
        or set(topics["groups"]) != set(GROUPS)
        or summary["corpus"]["status"] != "complete"
        or any(label["review_status"] != "evidence_reviewed" for label in labels)
    ):
        raise ValueError("Publication requires a completed, reviewed three-group replay")
    for relative, expected in audit["substantive_artifacts_sha256"].items():
        path = (source / relative).resolve()
        if not path.is_relative_to(source) or digest(path) != expected:
            raise ValueError(f"Replay artifact changed: {relative}")
    for name, key in [
        ("claims.csv", "claims_sha256"),
        ("complete_sources.csv", "complete_sources_sha256"),
    ]:
        if digest(data / name) != summary[key]:
            raise ValueError(f"Complete corpus changed: {name}")
    claims = Counter()
    claim_ids = set()
    for row in rows(data / "analysis_claims.csv"):
        if not row["claim_text"].strip() or not row["evidence"].strip():
            raise ValueError("Analysis download must contain actual claims and evidence")
        claims[row["group"]] += 1
        claim_ids.add(row["claim_id"])
    if dict(claims) != summary["claims_by_group"] or sum(claims.values()) != len(claim_ids):
        raise ValueError("Analysis claim accounting does not match the completed corpus")
    documents = Counter(row["group"] for row in rows(data / "complete_sources.csv"))
    if dict(documents) != summary["documents_by_group"]:
        raise ValueError("Complete-source accounting does not match the completed corpus")
    representatives = list(rows(data / "topics/representatives.csv"))
    for label in labels:
        ids = {row["claim_id"] for row in representatives if row["topic_id"] == label["topic_id"]}
        if not set(label["supporting_claim_ids"]) <= ids <= claim_ids:
            raise ValueError(f"Missing source-linked label evidence: {label['topic_id']}")
    if (data / "topics/positions/selection_manifest.json").exists():
        from dsa_analysis.national_claim_topic_positions import reviewed_positions

        position_manifest, positions = reviewed_positions(data)
        position_summary = read_json(data / "topics/positions/summary.json")
        stems = {
            "all_groups",
            "democratic_vs_republican",
            "democratic_vs_dsa",
            "republican_vs_dsa",
        }
        if (
            topics.get("positions") != position_summary
            or position_summary["status"] != "complete"
            or set(position_summary["figures"]) != stems
            or set(position_manifest["topics"])
            != {label["topic_id"] for label in labels if label.get("displayed", True)}
            or position_summary["group_positions"] != len(positions) * 3
            or position_summary["pairwise_differences"] != len(positions) * 3
            or read_json(data / "topics/positions/group_positions.json") != positions
            or any(
                not (source / root / "positions" / f"{stem}{suffix}").is_file()
                for root in (FIGURES, WEBSITE_FIGURES)
                for stem in stems
                for suffix in (".png",)
            )
        ):
            raise ValueError(
                "Publication requires all reviewed positions and four complete atlases"
            )
    archive_path = data / "claim_documents.zip"
    metadata_path = data / "claim_documents.download.json"
    expected_archive = read_json(metadata_path) if metadata_path.exists() else None
    if not archive_path.exists():
        if expected_archive is None:
            raise ValueError("Missing complete download and its reproducible archive manifest")
        from dsa_analysis.national_claim_corpus import bundle

        bundle(
            data,
            figures=source / FIGURES.parent,
            report=source / "report/national_claim_analysis.md",
        )
    if expected_archive and (
        archive_path.stat().st_size != expected_archive["bytes"]
        or digest(archive_path) != expected_archive["sha256"]
    ):
        raise ValueError("Complete download does not match its published archive checksum")
    from PIL import Image

    for figure in (source / FIGURES.parent).rglob("*"):
        if not figure.is_file():
            continue
        if figure.suffix != ".png":
            raise ValueError("Publication figures must be PNG-only")
        with Image.open(figure) as image:
            if image.format != "PNG" or set(image.info) - {"dpi"}:
                raise ValueError("Public PNG contains nonpublication metadata")
            image.verify()
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Complete download failed ZIP integrity verification")
        members = set(archive.namelist())
        if any(
            name.startswith("figures/") and not name.endswith((".png", "/")) for name in members
        ):
            raise ValueError("Complete download figures must be PNG-only")
        for path in (data / "topics/positions").rglob("*"):
            if path.suffix in {".csv", ".json"}:
                relative = path.relative_to(data).as_posix()
                if relative not in members or archive.read(relative) != path.read_bytes():
                    raise ValueError(f"Complete download omits position evidence: {relative}")
        for name in [
            "analysis_claims.csv",
            "complete_sources.csv",
            "topics/topic_labels.json",
            "topics/shares.csv",
            "topics/representatives.csv",
        ]:
            if name not in members or archive.read(name) != (data / name).read_bytes():
                raise ValueError(f"Complete download contains stale content: {name}")
        for figure in (source / FIGURES.parent).rglob("*"):
            if figure.suffix != ".png" or figure.is_relative_to(source / WEBSITE_FIGURES.parent):
                continue
            relative = figure.relative_to(source).as_posix()
            member = f"figures/{figure.relative_to(source / FIGURES.parent).as_posix()}"
            if (
                relative not in audit["substantive_artifacts_sha256"]
                or member not in members
                or archive.read(member) != figure.read_bytes()
            ):
                raise ValueError(f"Complete download contains stale figure: {relative}")
        for figure in (source / WEBSITE_FIGURES.parent).rglob("*"):
            if figure.suffix != ".png":
                continue
            relative = figure.relative_to(source / WEBSITE_FIGURES.parent).as_posix()
            member = f"figures/themarginoferror/{relative}"
            if member not in members or archive.read(member) != figure.read_bytes():
                raise ValueError(f"Complete download contains stale website figure: {member}")
    return summary, topics, labels, representatives, list(rows(data / "topics/shares.csv"))


def evolution_data(source: Path) -> dict | None:
    directory = source / DATA / "topics/evolution"
    if not directory.exists():
        return None
    summary = read_json(directory / "summary.json")
    labels = read_json(directory / "topic_labels.json")
    periods = read_json(directory / "period_fits.json")
    if (
        summary["status"] != "complete"
        or summary["topics"] != len(labels)
        or summary["labels_available"] != len(labels)
        or summary["reviewed_labels"]
        != sum(label["review_status"] == "evidence_reviewed" for label in labels)
    ):
        raise ValueError("Period-specific topics must be complete with accurate review status")
    representatives = list(rows(directory / "representatives.csv"))
    shares = list(rows(directory / "shares.csv"))
    for label in labels:
        label["representatives"] = [
            row for row in representatives if row["topic_id"] == label["topic_id"]
        ]
        label["shares"] = [row for row in shares if row["topic_id"] == label["topic_id"]]
        if not set(label["supporting_claim_ids"]) <= {
            row["claim_id"] for row in label["representatives"]
        }:
            raise ValueError(f"Missing period-label evidence: {label['topic_id']}")
    return dict(summary=summary, periods=periods, topics=labels)


def density_map_data(source: Path, labels: list, representatives: list) -> dict:
    data = source / DATA
    claims = {row["claim_id"]: row for row in rows(data / "analysis_claims.csv")}
    assignments = list(rows(data / "topics/assignments.csv"))
    assigned = {row["claim_id"]: row for row in assignments}
    scored = list(rows(data / "expanded/scored_passages.csv"))
    if (
        len(assigned) != len(assignments)
        or set(assigned) != set(claims)
        or len(scored) != len(claims)
        or {row["claim_id"] for row in scored} != set(claims)
    ):
        raise ValueError("Interactive map requires every unique eligible claim and assignment")
    topic_ids = [label["topic_id"] for label in labels]
    points = []
    for row in scored:
        claim, assignment = claims[row["claim_id"]], assigned[row["claim_id"]]
        if row["group"] != claim["group"] or assignment["group"] != claim["group"]:
            raise ValueError(f"Interactive map group mismatch: {row['claim_id']}")
        if any(
            record.get("text_sha256") and record["text_sha256"] != claim.get("text_sha256")
            for record in (row, assignment)
        ):
            raise ValueError(f"Interactive map claim text mismatch: {row['claim_id']}")
        if assignment["topic_id"] not in topic_ids:
            raise ValueError(f"Unknown interactive issue: {assignment['topic_id']}")
        values = [
            float(row[name])
            for name in ("umap_x", "umap_y", *(f"{group}_log_density" for group in GROUPS))
        ]
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"Non-finite interactive map values: {row['claim_id']}")
        points.append(
            [
                row["claim_id"],
                *values[:2],
                topic_ids.index(assignment["topic_id"]),
                GROUPS.index(row["group"]),
                *values[2:],
            ]
        )
    topics = []
    positions_path = data / "topics/positions/group_positions.json"
    positions = (
        {review["topic_id"]: review for review in read_json(positions_path)}
        if positions_path.exists()
        else {}
    )
    fields = (
        "claim_id",
        "group",
        "claim_text",
        "evidence",
        "title",
        "publication_date",
        "source_url",
    )
    for label in labels:
        examples = []
        position = positions.get(label["topic_id"], {})
        for group in GROUPS:
            selected = [
                row
                for row in representatives
                if row["topic_id"] == label["topic_id"]
                and claims[row["claim_id"]]["group"] == group
            ][:2]
            if position:
                supporting = list(position["groups"][group]["supporting_claim_ids"])
                for difference in position["pairs"].values():
                    supporting.extend(
                        claim_id
                        for claim_id in difference["supporting_claim_ids"]
                        if claims[claim_id]["group"] == group
                    )
                selected = [{"claim_id": claim_id} for claim_id in dict.fromkeys(supporting)]
            if not selected:
                candidates = [
                    claim
                    for claim in claims.values()
                    if claim["group"] == group
                    and assigned[claim["claim_id"]]["topic_id"] == label["topic_id"]
                ]
                selected = candidates[:1]
            for example in selected:
                claim = claims[example["claim_id"]]
                if (
                    assigned[claim["claim_id"]]["topic_id"] != label["topic_id"]
                    or claim["group"] != group
                ):
                    raise ValueError(
                        f"Interactive evidence issue/group mismatch: {claim['claim_id']}"
                    )
                examples.append({field: claim.get(field, "") for field in fields})
        topics.append(
            {
                **{key: label.get(key, "") for key in ("topic_id", "title", "summary", "caveat")},
                "displayed": label.get("displayed", True),
                "examples": examples,
                "positions": position.get("groups", {}),
                "differences": position.get("pairs", {}),
            }
        )
    regions = list(rows(data / "expanded/density_region_evidence.csv"))
    bounds = {float(row["color_bound"]) for row in regions if "color_bound" in row}
    if len(bounds) > 1 or any(not math.isfinite(value) or value <= 0 for value in bounds):
        raise ValueError("Interactive map must preserve the original common density color bound")
    limits = []
    for column in (1, 2):
        values = [point[column] for point in points]
        low, high = min(values), max(values)
        pad = max((high - low) * 0.05, 1e-6)
        limits.append([low - pad, high + pad])
    return dict(
        schema_version=1,
        view="expanded",
        groups=list(GROUPS),
        columns=["claim_id", "x", "y", "topic", "group", *(f"{g}_log_density" for g in GROUPS)],
        points=points,
        topics=topics,
        limits=limits,
        color_bound=next(iter(bounds), 1.0),
    )


def export(source: Path, output: Path) -> dict:
    source, output = source.resolve(), output.resolve()
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Publication output must be outside the source checkout")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Publication output must be absent or empty")
    summary, topics, labels, representatives, shares = validate(source)
    density_map = density_map_data(source, labels, representatives)
    evolution = evolution_data(source)
    if subprocess.check_output(
        [
            "git",
            "-C",
            str(source),
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            str(DATA),
            str(FIGURES),
            str(WEBSITE_FIGURES),
            "report/national_claim_analysis.md",
        ],
        text=True,
    ).strip():
        raise ValueError("Publication inputs must be committed before export")
    revision = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    files = {}
    figures = []
    website_originals = {}
    downloads = []
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".platform-publication-", dir=output.parent) as tmp:
        staging = Path(tmp)

        def copy(original: Path, relative: str):
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
            files[relative] = digest(target)

        figure_sources = [
            (original, source / FIGURES, source / WEBSITE_FIGURES)
            for original in sorted((source / FIGURES).rglob("*"))
        ]
        for view in ("expanded", "strict"):
            figure_sources += [
                (original, source / FIGURES.parent, source / WEBSITE_FIGURES.parent)
                for original in sorted(
                    (source / FIGURES.parent / view / "density_details").glob("*")
                )
            ]
        figure_sources += [
            (original, source / FIGURES.parent, source / WEBSITE_FIGURES.parent)
            for original in sorted((source / FIGURES.parent).glob("topic_emphasis*"))
        ]
        for original, figure_root, website_root in figure_sources:
            if original.suffix != ".png":
                continue
            parent = original.parent.relative_to(figure_root)
            view = parent.as_posix() if parent != Path(".") else "reference"
            relative = f"figures/{view}/{original.name}"
            copy(original, relative)
            website_originals[relative] = website_root / parent / original.name
            if original.suffix == ".png":
                width, height = struct.unpack(">II", original.read_bytes()[16:24])
                figures.append(
                    dict(
                        view=view,
                        name=original.stem,
                        path=relative,
                        width=width,
                        height=height,
                    )
                )
        pngs = {figure["path"] for figure in figures}
        required = {
            f"figures/{view}/issues/{label['topic_id']}_{kind}.png"
            for label in labels
            if label.get("displayed", True)
            for view in ("expanded", "strict")
            for kind in ("overall", "time")
        }
        required.update(
            f"figures/{view}/{name}.png"
            for view in ("expanded", "strict")
            for name in ("topic_distribution", "vs_rest_emphasis", "pairwise_emphasis")
        )
        if evolution:
            required.update(
                f"figures/evolution/{view}/period_{period['period']}.png"
                for period in evolution["periods"]
                for view in ("expanded", "strict")
            )
        position_summary = source / DATA / "topics/positions/summary.json"
        if position_summary.exists():
            required.update(
                f"figures/positions/{stem}.png" for stem in read_json(position_summary)["figures"]
            )
        if not required <= pngs:
            raise ValueError("Missing complete expanded/strict issue-level comparison charts")
        if (source / WEBSITE_FIGURES).exists():
            for figure in figures:
                relative = f"{figure['view']}/{figure['name']}"
                copy(
                    website_originals[figure["path"]],
                    f"website-figures/{relative}.png",
                )
                figure["display_path"] = f"website-figures/{relative}.png"
                website = website_originals[figure["path"]]
                if struct.unpack(">II", website.read_bytes()[16:24]) != (
                    figure["width"],
                    figure["height"],
                ):
                    raise ValueError(f"Website figure dimensions changed: {relative}")
        for name in [
            "analysis_claims.csv",
            "claims.csv",
            "claims.jsonl",
            "complete_sources.csv",
            "source_coverage.csv",
            "claim_documents.zip",
            "analysis_summary.json",
            "topics/shares.csv",
            "topics/contrasts.csv",
            "topics/temporal_shares.csv",
            "topics/temporal_contrasts.csv",
            "topics/temporal_coverage.csv",
            "topics/topic_labels.json",
            "topics/representatives.csv",
            "topics/label_review.json",
            "topics/replay_audit.json",
            "topics/candidate_fits.csv",
            "topics/balanced_refits.csv",
        ]:
            relative = f"downloads/{name}"
            copy(source / DATA / name, relative)
            downloads.append(dict(path=relative, bytes=(staging / relative).stat().st_size))
        download_metadata = source / DATA / "claim_documents.download.json"
        if download_metadata.exists():
            relative = f"downloads/{download_metadata.name}"
            copy(download_metadata, relative)
            downloads.append(dict(path=relative, bytes=download_metadata.stat().st_size))
        if evolution:
            for original in sorted((source / DATA / "topics/evolution").glob("*")):
                if original.suffix in {".csv", ".json"}:
                    copy(original, f"downloads/topics/evolution/{original.name}")
        for original in sorted((source / DATA / "topics/positions").rglob("*")):
            if original.suffix in {".csv", ".json"}:
                relative = f"downloads/{original.relative_to(source / DATA).as_posix()}"
                copy(original, relative)
                downloads.append(dict(path=relative, bytes=original.stat().st_size))
        for original in sorted((source / DATA).glob("*/density_region_evidence.csv")):
            relative = f"downloads/{original.relative_to(source / DATA).as_posix()}"
            copy(original, relative)
            downloads.append(dict(path=relative, bytes=original.stat().st_size))
        copy(source / "report/national_claim_analysis.md", "downloads/methods-and-results.md")
        for label in labels:
            label["representatives"] = [
                row for row in representatives if row["topic_id"] == label["topic_id"]
            ]
            label["shares"] = [row for row in shares if row["topic_id"] == label["topic_id"]]
        publication = dict(
            schema_version=1,
            source_repository="hanshanley/dsa",
            source_revision=revision,
            summary=summary,
            topic_summary=topics,
            topics=[label for label in labels if label.get("displayed", True)],
            figures=figures,
            density_regions=[
                row
                for original in sorted((source / DATA).glob("*/density_region_evidence.csv"))
                for row in rows(original)
            ],
            downloads=downloads,
            evolution=evolution,
            positions=(
                read_json(source / DATA / "topics/positions/group_positions.json")
                if position_summary.exists()
                else []
            ),
        )
        (staging / "analysis.json").write_text(
            json.dumps(publication, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
        )
        files["analysis.json"] = digest(staging / "analysis.json")
        (staging / "density-map.json").write_text(
            json.dumps(density_map, ensure_ascii=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        files["density-map.json"] = digest(staging / "density-map.json")
        manifest = dict(
            schema_version=1,
            source_repository="hanshanley/dsa",
            source_revision=revision,
            scope="Completed Democratic, Republican, and DSA national analysis only",
            claims=summary["claims"],
            topics=len(labels),
            files=files,
        )
        (staging / "publication-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if output.exists():
            output.rmdir()
        staging.rename(output)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = export(args.source, args.output)
    print(f"Exported {result['claims']:,} claims and {result['topics']} reviewed topics")
