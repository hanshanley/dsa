"""Isolated four-party comparison, reusing the preserved three-party extraction."""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

from .national_claim_analysis import analysis_rows, run_analysis
from .national_claim_corpus import CLAIMS_ROOT, FULL_OUTPUT, bundle
from .national_platforms import (
    DEFAULT_CUTOFF,
    GROUPS,
    ROOT,
    SUPPORTED_GROUPS,
    digest,
    fetch_sources,
    load_ledger,
    prepare_corpus,
    read_rows,
    write_json,
    write_rows,
)

LEDGER = ROOT / "data/manual/libertarian_platform_sources.csv"
RAW = ROOT / "data/raw/libertarian_platforms"
CORPUS = ROOT / "data/analysis/libertarian_platforms"
LIBERTARIAN_CLAIMS = CLAIMS_ROOT / "libertarian"
OUTPUT = CLAIMS_ROOT / "four_party"
REPORT = ROOT / "report/national_claim_analysis_four_party.md"
COMPONENT_FILES = (
    "normalization_manifest.json",
    "runtime.json",
    "extraction_summary.json",
    "complete_sources.csv",
    "blocks.csv",
    "block_status.csv",
    "source_coverage.csv",
    "semantic_review.csv",
)


def prepare_sources(*, fetch: bool = False, download_model: bool = False) -> dict:
    from transformers import AutoTokenizer

    from .provisional_kde import MODEL_NAME, MODEL_REVISION

    ledger = load_ledger(LEDGER)
    if {row["group"] for row in ledger} != {"libertarian"}:
        raise ValueError("The separate Libertarian ledger must contain only national LP documents")
    if fetch:
        fetch_sources(ledger, raw=RAW)
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        revision=MODEL_REVISION,
        trust_remote_code=True,
        local_files_only=not download_model,
    )
    passages, coverage = prepare_corpus(
        ledger, tokenizer, raw=RAW, output=CORPUS, cutoff=DEFAULT_CUTOFF
    )
    failures = [
        row["document_id"] for row in coverage if row["status"] == "extraction_or_capture_error"
    ]
    if failures:
        raise ValueError(f"Libertarian source captures/extractions failed: {failures}")
    return {
        "documents": sum(row["status"] == "eligible" for row in coverage),
        "passages": sum(row["eligible"] for row in passages),
        "dispositions": dict(Counter(row["status"] for row in coverage)),
    }


def merge_components(
    *,
    base: Path = FULL_OUTPUT,
    libertarian: Path = LIBERTARIAN_CLAIMS,
    output: Path = OUTPUT,
) -> dict:
    sources = {"three_party": base.resolve(), "libertarian": libertarian.resolve()}
    output = output.resolve()
    if any(
        output == source or output in source.parents or source in output.parents
        for source in sources.values()
    ):
        raise ValueError("Merged output must not overwrite or contain either extraction component")
    claims, documents, statuses, coverage, components = [], [], [], [], {}
    seen_claims, seen_documents, seen_blocks = set(), set(), set()
    summaries = []
    for name, source in sources.items():
        required = set(COMPONENT_FILES) - {"runtime.json", "semantic_review.csv"}
        missing = {filename for filename in required if not (source / filename).is_file()}
        if missing:
            raise ValueError(f"Component evidence is incomplete: {name}: {sorted(missing)}")
        files = {
            filename: source / filename
            for filename in COMPONENT_FILES
            if (source / filename).is_file()
        }
        for directory in ("responses", "response_history", "source_repairs"):
            files.update(
                (path.relative_to(source).as_posix(), path)
                for path in sorted((source / directory).glob("*.json"))
            )
        hashes = {relative: digest(path.read_bytes()) for relative, path in files.items()}
        hashes["claims.csv"] = digest((source / "claims.csv").read_bytes())
        summary = json.loads((source / "extraction_summary.json").read_text())
        if summary["status"] not in {"complete", "complete_with_exclusions"} or summary.get(
            "components"
        ):
            raise ValueError(f"Component is not a completed standalone extraction: {name}")
        allowed = set(GROUPS) if name == "three_party" else {"libertarian"}
        component_claims = read_rows(source / "claims.csv")
        component_documents = read_rows(source / "complete_sources.csv")
        component_statuses = read_rows(source / "block_status.csv")
        if (
            {row["group"] for row in component_documents} != allowed
            or any(row["group"] not in allowed for row in component_claims + component_statuses)
            or any(row["status"] == "not_run" for row in component_statuses)
            or len(component_claims) != summary["claims"]
            or len(component_statuses) != summary["blocks"]
            or {path.stem for path in (source / "responses").glob("*.json")}
            != {row["block_id"] for row in component_statuses}
            or Counter(row["status"] for row in component_statuses) != summary["blocks_by_status"]
            or len(analysis_rows(component_claims, component_documents))
            != summary["analysis_claims"]
        ):
            raise ValueError(
                f"Component scope, provenance or extraction accounting mismatch: {name}"
            )
        manifest = json.loads((source / "normalization_manifest.json").read_text())
        if manifest["fingerprint"] != summary["fingerprint"]:
            raise ValueError(f"Component normalization fingerprint mismatch: {name}")
        for rows, key, seen, target in (
            (component_claims, "claim_id", seen_claims, claims),
            (component_documents, "document_id", seen_documents, documents),
            (component_statuses, "block_id", seen_blocks, statuses),
        ):
            for row in rows:
                if row[key] in seen:
                    raise ValueError(f"Repeated {key} across components: {row[key]}")
                seen.add(row[key])
                target.append({**row, "normalization_component": name})
        coverage.extend(
            {**row, "normalization_component": name}
            for row in read_rows(source / "source_coverage.csv")
        )
        destination = output / "components" / name
        if destination.exists():
            unexpected = {
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file()
            } - set(files)
            if unexpected:
                raise ValueError(f"Stale component evidence requires a separate output: {name}")
        for relative, path in files.items():
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            if digest(target.read_bytes()) != hashes[relative]:
                raise ValueError(f"Component changed during preservation: {name}/{relative}")
        if any(digest(path.read_bytes()) != hashes[relative] for relative, path in files.items()):
            raise ValueError(f"Component changed during merge: {name}")
        if digest((source / "claims.csv").read_bytes()) != hashes["claims.csv"]:
            raise ValueError(f"Component claims changed during merge: {name}")
        components[name] = {
            "original_output": source.relative_to(ROOT).as_posix()
            if source.is_relative_to(ROOT)
            else source.name,
            "fingerprint": manifest["fingerprint"],
            "groups": sorted(allowed),
            "input_sha256": hashes,
            "preserved_files": sorted(files),
            "claims": len(component_claims),
            "analysis_claims": summary["analysis_claims"],
        }
        summaries.append(summary)
    write_rows(output / "claims.csv", claims)
    with (output / "claims.jsonl").open("w", encoding="utf-8") as handle:
        for row in claims:
            handle.write(
                json.dumps(
                    {
                        **row,
                        "analysis_eligible": row["analysis_eligible"].lower() == "true",
                        "source_start": int(row["source_start"]),
                        "source_end": int(row["source_end"]),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    write_rows(output / "complete_sources.csv", documents)
    write_rows(
        output / "coverage.csv",
        [
            {
                **{
                    key: row.get(key, "")
                    for key in (
                        "document_id",
                        "group",
                        "document_type",
                        "publication_date",
                        "adoption_date",
                        "version_date",
                        "title",
                        "source_url",
                        "bundle_id",
                    )
                },
                "status": "eligible",
            }
            for row in documents
        ],
    )
    write_rows(output / "block_status.csv", statuses)
    write_rows(output / "source_coverage.csv", coverage)
    write_json(
        output / "normalization_components.json",
        {
            "schema_version": 1,
            "groups": list(SUPPORTED_GROUPS),
            "components": components,
            "qualification": (
                "Separate source-bound normalization fingerprints; original claim IDs retained"
            ),
        },
    )
    counts = Counter(row["status"] for row in statuses)
    total_fields = (
        "blocks",
        "claims",
        "analysis_claims",
        "documents",
        "source_words",
        "assistant_source_repaired_blocks",
        "assistant_source_repaired_claims",
        "superseded_model_claims",
        "exact_within_document_duplicates",
        "assistant_flagged_claims",
        "unrepaired_flagged_model_claims",
        "blocks_with_unresolved_references",
        "inference_seconds",
        "generation_tokens",
    )
    merged = {
        "status": "complete_with_exclusions" if counts["validation_failed"] else "complete",
        "groups": list(SUPPORTED_GROUPS),
        "components": components,
        **{field: sum(summary.get(field, 0) for summary in summaries) for field in total_fields},
        "blocks_by_status": dict(counts),
        "model_blocks_by_status": dict(
            sum((Counter(summary["model_blocks_by_status"]) for summary in summaries), Counter())
        ),
        "claims_by_group": dict(Counter(row["group"] for row in claims)),
        "quality": (
            "Automated screening and targeted assistant repairs, not human gold or fact-checking"
        ),
        "baseline_modified": False,
    }
    write_json(output / "extraction_summary.json", merged)
    bundle(output)
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("sources", "merge", "analyze"))
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--download-model", action="store_true")
    args = parser.parse_args()
    if args.command == "sources":
        result = prepare_sources(fetch=args.fetch, download_model=args.download_model)
    else:
        if args.fetch:
            parser.error("--fetch is only valid for sources")
        result = merge_components()
        if args.command == "analyze":
            result = run_analysis(
                OUTPUT,
                groups=SUPPORTED_GROUPS,
                coverage_path=OUTPUT / "coverage.csv",
                report=REPORT,
                download_model=args.download_model,
            )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
