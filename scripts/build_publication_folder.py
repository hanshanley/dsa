"""Collect current Substack figures under readable, stable publishing paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPICS = Path("figures/national_claims/full/topics")


def publication_files(root: Path) -> tuple[dict[str, Path], list[dict]]:
    labels = json.loads(
        (root / "data/analysis/national_claims/full/topics/topic_labels.json").read_text()
    )
    issues = sorted((label for label in labels if label["displayed"]), key=lambda x: x["title"])
    files = {
        "substack/where-dsa-stands-apart.png": Path(
            "figures/article/dsa_vs_major_parties_lead.png"
        ),
        "substack/all-issues-overview.png": TOPICS / "expanded/substack_overview.png",
        "data/attention-share-ratios.csv": Path("figures/article/dsa_attention_share_ratios.csv"),
    }
    for label in issues:
        slug = re.sub(r"[^a-z0-9]+", "-", label["title"].lower()).strip("-")
        if not slug:
            raise ValueError("An issue needs a readable filename")
        label["slug"] = slug
        for suffix, original in (("overall", "overall"), ("timeline", "time")):
            destination = f"substack/issues/{slug}-{suffix}.png"
            if destination in files:
                raise ValueError(f"Duplicate publishing filename: {destination}")
            files[destination] = TOPICS / f"expanded/issues/{label['topic_id']}_{original}.png"
        combined = TOPICS / f"expanded/piece/{label['topic_id']}.png"
        if (root / combined).is_file():
            files[f"substack/issues/{slug}-combined.png"] = combined
    for name in (
        "all_groups",
        "democratic_vs_republican",
        "democratic_vs_dsa",
        "republican_vs_dsa",
    ):
        files[f"substack/positions/{name.replace('_', '-')}.png"] = TOPICS / f"positions/{name}.png"
    missing = [str(path) for path in files.values() if not (root / path).is_file()]
    if missing:
        raise ValueError(f"Publishing requires existing current figures: {', '.join(missing)}")
    return files, issues


def publication_guide(files: dict[str, Path], issues: list[dict]) -> str:
    lines = [
        "# Ready to publish",
        "",
        "**For Substack, start here.** These are the current expanded-source PNGs",
        "with readable filenames. They are exact copies, not new fits or recolored images.",
        "",
        "| Use | File |",
        "|---|---|",
        "| The DSA map with five attention ratios and dated statements | "
        "[where-dsa-stands-apart.png](substack/where-dsa-stands-apart.png) |",
        "| All 21 substantive issues in one chart | "
        "[all-issues-overview.png](substack/all-issues-overview.png) |",
        "| All four attention comparisons, including identity clusters | "
        "[attention-share-ratios.csv](data/attention-share-ratios.csv) |",
        "",
        "[Download the Substack lead PNG directly]"
        "(https://raw.githubusercontent.com/hanshanley/dsa/main/"
        "publication/substack/where-dsa-stands-apart.png). "
        "The [lead's exact values, dated statements and source anchors]"
        "(../figures/article/dsa_vs_major_parties_lead.json) remain alongside the original.",
        "",
        "## Issue charts",
        "",
        "Use **Combined** for an article-ready overall comparison and timeline together.",
        "A dash means there is no combined graphic for that issue, not missing policy evidence.",
        "",
        "| Issue | Overall | Timeline | Combined |",
        "|---|---|---|---|",
    ]
    for label in issues:
        base = f"substack/issues/{label['slug']}"
        combined = f"{base}-combined.png"
        links = [
            f"[PNG]({base}-overall.png)",
            f"[PNG]({base}-timeline.png)",
            f"[PNG]({combined})" if combined in files else "—",
        ]
        lines.append(f"| {label['title']} | {' | '.join(links)} |")
    lines.extend(
        [
            "",
            "## Positions and other destinations",
            "",
            "[All three groups](substack/positions/all-groups.png) ·",
            "[Democratic–Republican](substack/positions/democratic-vs-republican.png) ·",
            "[Democratic–DSA](substack/positions/democratic-vs-dsa.png) ·",
            "[Republican–DSA](substack/positions/republican-vs-dsa.png)",
            "",
            "Website backgrounds remain in",
            "[the website figure collection](../figures/national_claims/full/themarginoferror/).",
            "Strict comparisons, alternatives and historical charts remain in the",
            "[full chart guide](../figures/README.md).",
            "Complete claims, source texts and the analytical archive are linked from",
            "[results and downloads](../README.md#results-and-downloads).",
            "",
            "## Refreshing this folder",
            "",
            "After regenerating canonical figures, run:",
            "",
            "```bash",
            "python scripts/build_publication_folder.py",
            "python scripts/build_publication_folder.py --check",
            "```",
            "",
            "`manifest.json` records each original path and SHA-256. The check rejects",
            "missing or stale copies; CI runs it too. Original research paths are unchanged.",
            "",
        ]
    )
    return "\n".join(lines)


def export_publishing(root: Path, *, check: bool = False) -> dict:
    files, issues = publication_files(root)
    output = root / "publication"
    manifest = {
        name: {
            "source": str(source),
            "sha256": hashlib.sha256((root / source).read_bytes()).hexdigest(),
        }
        for name, source in sorted(files.items())
    }
    documents = {
        "README.md": publication_guide(files, issues),
        "manifest.json": json.dumps({"files": manifest}, indent=2) + "\n",
    }
    if check:
        for name, record in manifest.items():
            path = output / name
            if (
                not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]
            ):
                raise ValueError(f"Missing or stale publishing file: {name}")
        for name, expected in documents.items():
            path = output / name
            if not path.is_file() or path.read_text() != expected:
                raise ValueError(f"Missing or stale publishing index: {name}")
        return manifest
    previous = output / "manifest.json"
    if previous.is_file():
        for name in json.loads(previous.read_text())["files"].keys() - files.keys():
            path = output / name
            if not path.resolve().is_relative_to(output.resolve()) or not path.is_file():
                raise ValueError(f"Invalid obsolete publishing file: {name}")
            path.unlink()
    for name, source in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / source, path)
    for name, content in documents.items():
        (output / name).write_text(content)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Reject missing or stale publishing copies"
    )
    args = parser.parse_args()
    manifest = export_publishing(ROOT, check=args.check)
    print(f"{'Verified' if args.check else 'Exported'} {len(manifest)} publishing files")


if __name__ == "__main__":
    main()
