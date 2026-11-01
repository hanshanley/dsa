"""Export the reviewed caucus comparison for the website without fitting models."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

from dsa_caucus_analysis import CLAIMS, CORPUS, RESULTS, ROOT
from publish_dsa_caucuses import review_basis, validated_labels

from dsa_analysis.national_platforms import digest, read_rows, write_json


def publication_data() -> dict:
    summary = json.loads((RESULTS / "summary.json").read_text())
    for name, expected in summary["result_hashes"].items():
        if digest((RESULTS / name).read_bytes()) != expected:
            raise ValueError(f"Caucus result changed: {name}")
    inputs = {
        "claims": CLAIMS / "claims.csv",
        "sources": CORPUS / "complete_sources.csv",
        "embeddings": RESULTS / "embeddings.npy",
        "comparison_implementation": ROOT / "scripts/dsa_caucus_comparison.py",
    }
    if any(digest(path.read_bytes()) != summary["input_hashes"][key]
           for key, path in inputs.items()):
        raise ValueError("Caucus inputs do not match the reviewed fit")
    representatives = read_rows(RESULTS / "topic_representatives.csv")
    labels = validated_labels(
        summary,
        json.loads((RESULTS / "reviewed_topic_labels.json").read_text()),
        representatives,
    )
    claims = {row["claim_id"]: row for row in read_rows(RESULTS / "analysis_claims.csv")}
    sources = {row["caucus"]: row for row in read_rows(CORPUS / "complete_sources.csv")}
    if len(claims) != summary["eligible_claims"] or len(sources) != 13:
        raise ValueError("Incomplete caucus claim/source accounting")
    groups = sorted(
        [{"id": group, "name": source["organization"]} for group, source in sources.items()],
        key=lambda group: group["name"],
    )
    shares = read_rows(RESULTS / "attention_shares.csv")
    ratios = read_rows(RESULTS / "attention_share_ratios.csv")
    topics = []
    for topic, label in sorted(labels.items(), key=lambda item: item[1]["title"]):
        entries = []
        for group in groups:
            share, = [r for r in shares if r["topic_id"] == topic and r["group"] == group["id"]]
            ratio, = [r for r in ratios if r["topic_id"] == topic
                      and r["group"] == group["id"] and r["comparison"] == "equal_caucus_rest"]
            value = float(share["attention_share"])
            baseline = float(ratio["baseline_attention_share"])
            relative = float(ratio["attention_share_ratio"]) if baseline else None
            if not 0 <= value <= 1 or (baseline and not math.isclose(relative, value / baseline)):
                raise ValueError(f"Invalid caucus attention ratio: {topic}/{group['id']}")
            examples = []
            for example in representatives:
                if example["topic_id"] != topic or example["group"] != group["id"]:
                    continue
                claim = claims[example["claim_id"]]
                source = sources[group["id"]]
                excerpt = source["complete_text"][
                    int(claim["complete_source_start"]):int(claim["complete_source_end"])
                ]
                if excerpt != claim["evidence"] or claim["group"] != group["id"]:
                    raise ValueError(f"Caucus evidence changed: {claim['claim_id']}")
                examples.append({key: claim[key] for key in (
                    "claim_id", "claim_text", "evidence", "source_url", "title", "locator",
                )})
            if bool(int(share["claims"])) != bool(examples):
                raise ValueError(f"Missing caucus representatives: {topic}/{group['id']}")
            entries.append({
                **group, "share": value, "claims": int(share["claims"]),
                "baseline": baseline, "ratio": relative, "examples": examples,
            })
        topics.append({"id": topic, "title": label["title"], "summary": label["summary"],
                       "groups": entries})
    revision = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    return {
        "source_revision": revision,
        "review_basis_hash": review_basis(summary),
        "eligible_claims": len(claims),
        "groups": groups,
        "topics": topics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("Caucus export destination must be absent or empty")
    data = publication_data()
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / "analysis.json", data)
    print(f"Exported {len(data['topics'])} themes and {len(data['groups'])} caucuses")


if __name__ == "__main__":
    main()
