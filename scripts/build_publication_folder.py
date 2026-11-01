"""Collect all current figures in Substack and Margin of Error publishing folders."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPICS = Path("figures/national_claims/full/topics")
BACKGROUNDS = {"substack": "#F5F5F5", "margin-of-error": "#F7F5F0"}


def publishing_bytes(source: Path, background: str | None) -> bytes:
    original = source.read_bytes()
    if background is None:
        return original
    from PIL import Image, ImageChops, ImageColor

    with Image.open(io.BytesIO(original)) as source_image:
        image = source_image.convert("RGBA")
    before = image.getpixel((0, 0))
    if before not in ((247, 245, 240, 255), (245, 245, 245, 255), (242, 239, 231, 255)):
        raise ValueError(f"Unrecognized publication background: {source}")
    after = (*ImageColor.getrgb(background), 255)
    if before == after:
        return original
    difference = ImageChops.difference(image, Image.new("RGBA", image.size, before))
    channels = difference.split()
    mask = channels[0]
    for channel in channels[1:]:
        mask = ImageChops.lighter(mask, channel)
    mask = mask.point(lambda value: 255 if value == 0 else 0)
    image.paste(after, mask=mask)
    output = io.BytesIO()
    image.save(output, format="PNG", dpi=(200, 200))
    return output.getvalue()


def figure_name(relative: Path, slugs: dict[str, str]) -> str:
    parts = list(relative.parts)
    prefix = ""
    if parts[0] == "topics":
        parts.pop(0)
    if parts[0] == "evolution":
        prefix = "supporting/"
        if parts[1] == "strict":
            prefix += "adopted-only/"
        return prefix + "period-themes/" + parts[-1].removeprefix("period_").replace("_", "-")
    if parts[0] in ("expanded", "strict"):
        if parts.pop(0) == "strict":
            prefix = "supporting/adopted-only/"
    path = Path(*parts)
    if parts[0] in ("issues", "piece"):
        topic_id = path.stem.split("_")[0]
        suffix = "combined" if parts[0] == "piece" else path.stem.split("_")[1]
        suffix = "timeline" if suffix == "time" else suffix
        return f"{prefix}issues/{slugs[topic_id]}-{suffix}.png"
    if parts[0] == "positions":
        return "positions/" + path.name.replace("_", "-")
    if parts[0] == "density_details":
        return (prefix or "supporting/") + "density/" + path.name.replace("_", "-")
    if path.name == "substack_overview.png":
        return prefix + "all-issues-overview.png"
    for original, readable in (
        ("topic_distribution", "attention-shares"),
        ("vs_rest_emphasis", "relative-emphasis"),
        ("pairwise_emphasis", "pairwise-gaps"),
        ("topic_emphasis", "cap-attention"),
    ):
        if path.stem == original or path.stem.startswith(original + "_"):
            page = path.stem.removeprefix(original).lstrip("_") or "1"
            category = (
                "cap"
                if original == "topic_emphasis" and prefix
                else ("supporting/cap" if original == "topic_emphasis" else "overviews")
            )
            return f"{prefix}{category}/{readable}-{page}.png"
    if path.name in ("coverage.png", "document_change.png", "pairwise_density.png"):
        return (prefix or "supporting/") + path.name.replace("_", "-")
    raise ValueError(f"A current figure needs a publishing name: {relative}")


def publication_files(root: Path) -> tuple[dict[str, Path], list[dict]]:
    labels = json.loads(
        (root / "data/analysis/national_claims/full/topics/topic_labels.json").read_text()
    )
    issues = sorted((label for label in labels if label["displayed"]), key=lambda x: x["title"])
    files = {
        "data/attention-share-ratios.csv": Path("figures/article/dsa_attention_share_ratios.csv"),
    }
    slugs = {}
    for label in issues:
        slug = re.sub(r"[^a-z0-9]+", "-", label["title"].lower()).strip("-")
        if not slug:
            raise ValueError("An issue needs a readable filename")
        label["slug"] = slug
        if slug in slugs.values():
            raise ValueError(f"Duplicate publishing filename: {slug}")
        slugs[label["topic_id"]] = slug
    full = TOPICS.parent
    for destination in BACKGROUNDS:
        collection = full
        required = [collection / "topics/expanded/substack_overview.png"]
        required.extend(
            collection / f"topics/expanded/issues/{label['topic_id']}_{suffix}.png"
            for label in issues
            for suffix in ("overall", "time")
        )
        missing = [str(path) for path in required if not (root / path).is_file()]
        if missing:
            raise ValueError(f"Publishing requires existing current figures: {', '.join(missing)}")
        for source in sorted((root / collection).rglob("*.png")):
            relative = source.relative_to(root / collection)
            if "themarginoferror" in relative.parts:
                continue
            name = f"{destination}/{figure_name(relative, slugs)}"
            if name in files:
                raise ValueError(f"Duplicate publishing filename: {name}")
            files[name] = source.relative_to(root)
    for original, name in (
        ("dsa_vs_major_parties_lead", "where-dsa-stands-apart"),
        ("dsa_lead_option_b-map-bottom", "alternatives/where-dsa-stands-apart-bottom"),
        ("dsa_lead_option_c-map-three", "alternatives/where-dsa-stands-apart-three"),
        ("dsa_vs_major_parties_attention_gaps", "supporting/dsa-attention-gaps"),
    ):
        source = Path(f"figures/article/{original}.png")
        if original == "dsa_vs_major_parties_lead" or (root / source).is_file():
            for destination in BACKGROUNDS:
                files[f"{destination}/{name}.png"] = source
    missing = [str(path) for path in files.values() if not (root / path).is_file()]
    if missing:
        raise ValueError(f"Publishing requires existing current figures: {', '.join(missing)}")
    return files, issues


def publication_guide(files: dict[str, Path], issues: list[dict]) -> str:
    lines = [
        "# Figures",
        "",
        "**Two destinations, one home for current figures.** Choose Substack or",
        "The Margin of Error, then use the same readable issue filenames.",
        "Substack uses `#F5F5F5`; The Margin of Error uses `#F7F5F0`,",
        "matching the destination themes in `hanshanley/china-us-relation-change`.",
        "Only background pixels change; chart marks, text, dimensions and values stay intact.",
        "",
        "```text",
        "figures/",
        "  substack/          Article images and Substack-background charts",
        "  margin-of-error/   Website-background charts",
        "  data/              Complete attention-share ratios",
        "```",
        "",
        "| Use | Substack | The Margin of Error |",
        "|---|---|---|",
        "| The DSA map with five attention ratios and dated statements | "
        "[where-dsa-stands-apart.png](substack/where-dsa-stands-apart.png) | "
        "[where-dsa-stands-apart.png](margin-of-error/where-dsa-stands-apart.png) |",
        "| All 21 substantive issues in one chart | "
        "[PNG](substack/all-issues-overview.png) | "
        "[PNG](margin-of-error/all-issues-overview.png) |",
        "| Named issue charts and combined article graphics | "
        "[Browse](substack/README.md#issue-charts) | "
        "[Browse](margin-of-error/README.md#issue-charts) |",
        "| Positions, overview pages, density maps and supporting figures | "
        "[Browse](substack/README.md) | [Browse](margin-of-error/README.md) |",
        "",
        "[All four attention-share ratios, including flagged identity clusters]"
        "(data/attention-share-ratios.csv).",
        "",
        "[Download the Substack lead PNG directly]"
        "(https://raw.githubusercontent.com/hanshanley/dsa/main/"
        "figures/substack/where-dsa-stands-apart.png). "
        "The [lead's exact values, dated statements and source anchors]"
        "(article/dsa_vs_major_parties_lead.json) remain alongside the original.",
        "",
        "## What goes where",
        "",
        "Both destinations use `issues/`, `positions/`, `overviews/`, and `supporting/`.",
        "Main folders contain the expanded comparison; `supporting/adopted-only/`",
        "contains strict-view sensitivity figures. `supporting/period-themes/`",
        "contains independently discovered period topics. Article alternatives",
        "are under each destination's `alternatives/`, not mixed with final lead images.",
        "",
        "The website uses its [live interactive map]"
        "(https://www.themarginoferror.com/party-platforms/) rather than the article lead.",
        "Complete claims, source texts and the analytical archive remain linked from",
        "[results and downloads](../README.md#results-and-downloads).",
    ]
    lines.extend(
        [
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
            "`manifest.json` records original paths, source and export SHA-256 hashes,",
            "and destination backgrounds. The check rejects missing or stale exports;",
            "CI runs it too.",
            "",
            "## Research originals and history",
            "",
            "`national_claims/full/` and `article/` retain the original analytical bytes",
            "for report links, replay hashes, releases and the website's pinned inputs.",
            "They are research inputs, not additional places to find publishing images.",
            "Earlier [reviewed-sample](national_claims/reviewed_sample/) and",
            "[passage-based](national_platforms/) figures remain historical.",
            "",
        ]
    )
    return "\n".join(lines)


def destination_guide(destination: str, files: dict[str, Path], issues: list[dict]) -> str:
    title = "Substack" if destination == "substack" else "The Margin of Error"
    lines = [
        f"# {title} figures",
        "",
        f"Current figures on `{BACKGROUNDS[destination]}`. [Switch destination](../README.md).",
        "",
        "[All-issue overview](all-issues-overview.png)",
    ]
    lines.append("[DSA article lead](where-dsa-stands-apart.png)")
    lines.extend(
        [
            "",
            "## Issue charts",
            "",
            "Overall and timeline are separate PNGs; Combined puts both in one article graphic.",
            "A dash means no combined graphic was generated for that issue.",
            "",
            "| Issue | Overall | Timeline | Combined |",
            "|---|---|---|---|",
        ]
    )
    for label in issues:
        base = f"issues/{label['slug']}"
        combined = f"{base}-combined.png"
        links = [
            f"[PNG]({base}-overall.png)",
            f"[PNG]({base}-timeline.png)",
            f"[PNG]({combined})" if f"{destination}/{combined}" in files else "—",
        ]
        lines.append(f"| {label['title']} | {' | '.join(links)} |")
    for category, heading in (
        ("positions", "Group positions"),
        ("overviews", "All-issue overview pages"),
        ("supporting", "Supporting and adopted-only figures"),
        ("alternatives", "Alternative article layouts"),
    ):
        names = sorted(
            name.removeprefix(destination + "/")
            for name in files
            if name.startswith(f"{destination}/{category}/")
        )
        if names:
            lines.extend(["", f"## {heading}", ""])
            lines.extend(f"- [{name}]({name})" for name in names)
    return "\n".join(lines) + "\n"


def export_publishing(root: Path, *, check: bool = False) -> dict:
    files, issues = publication_files(root)
    output = root / "figures"
    manifest = {}
    for name, source in sorted(files.items()):
        background = BACKGROUNDS.get(name.split("/")[0])
        content = publishing_bytes(root / source, background)
        record = {
            "source": source.as_posix(),
            "source_sha256": hashlib.sha256((root / source).read_bytes()).hexdigest(),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        if background is not None:
            record["background"] = background
        manifest[name] = record
        path = output / name
        if check:
            if not path.is_file():
                raise ValueError(f"Missing or stale publishing file: {name}")
            actual = path.read_bytes()
            if actual != content:
                if background is None:
                    raise ValueError(f"Missing or stale publishing file: {name}")
                from PIL import Image

                with Image.open(io.BytesIO(content)) as expected_image:
                    expected = expected_image.convert("RGBA")
                with Image.open(io.BytesIO(actual)) as actual_image:
                    actual_pixels = actual_image.convert("RGBA")
                if (
                    actual_pixels.size != expected.size
                    or actual_pixels.tobytes() != expected.tobytes()
                ):
                    raise ValueError(f"Missing or stale publishing file: {name}")
                record["sha256"] = hashlib.sha256(actual).hexdigest()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    documents = {
        "README.md": publication_guide(files, issues),
        "substack/README.md": destination_guide("substack", files, issues),
        "margin-of-error/README.md": destination_guide("margin-of-error", files, issues),
        "manifest.json": json.dumps({"files": manifest}, indent=2) + "\n",
    }
    if check:
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
