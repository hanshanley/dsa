"""Isolated, source-bound DSA caucus claim extraction and comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dsa_analysis.national_claim_corpus import extract_corpus
from dsa_analysis.national_platforms import digest, read_rows, write_json, write_rows

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/analysis/dsa_caucuses/sources"
CLAIMS = ROOT / "data/analysis/dsa_caucuses/claims"
RESULTS = ROOT / "data/analysis/dsa_caucuses/comparison"
LEDGER = ROOT / "data/manual/dsa_caucus_sources.json"


def scoped_text(text: str, source: dict) -> tuple[str, int, int]:
    start, end = 0, len(text)
    if marker := source.get("scope_start"):
        find = text.rfind if source.get("scope_start_occurrence") == "last" else text.find
        start = find(marker)
        if start < 0:
            raise ValueError(f"Missing start boundary: {source['document_id']}")
    if marker := source.get("scope_end"):
        find = text.rfind if source.get("scope_end_occurrence") == "last" else text.find
        end = find(marker, start)
        if end < 0:
            raise ValueError(f"Missing end boundary: {source['document_id']}")
    result = text[start:end].strip()
    start += len(text[start:end]) - len(text[start:end].lstrip())
    end = start + len(result)
    if len(result.split()) < 100:
        raise ValueError(f"Insufficient political text: {source['document_id']}")
    return result, start, end


def prepare_sources(root: Path = ROOT) -> dict:
    ledger = json.loads((root / LEDGER.relative_to(ROOT)).read_text())
    records = json.loads((root / "data/raw/dsa_caucuses/retrieval.json").read_text())
    retrieved = {row["document_id"]: row for row in records}
    sources, coverage = [], []
    for source in ledger["sources"]:
        record = retrieved[source["document_id"]]
        if record["status"] != "retrieved":
            raise ValueError(f"Missing primary document: {source['document_id']}")
        text = (root / record["text_file"]).read_text()
        html = (root / record["raw_html"]).read_bytes()
        if digest(text) != record["complete_text_sha256"] or digest(html) != record["html_sha256"]:
            raise ValueError(f"Retrieval hash mismatch: {source['document_id']}")
        scoped, start, end = scoped_text(text, source)
        # Blank navigation in place so claim locators remain exact character
        # offsets into the complete, untouched capture.
        for line in source.get("excluded_lines", []):
            scoped = scoped.replace(f"\n{line}\n", f"\n{' ' * len(line)}\n")
        sources.append(
            {
                **source,
                "caucus": source["group"],
                # The shared extractor's organization remains DSA; the title and
                # document ID bind every claim to its actual authoring caucus.
                "group": "dsa",
                "title": f"{source['organization']}: {source['title']}",
                "bundle_id": source["document_id"],
                "sha256": record["html_sha256"],
                "text_sha256": digest(scoped),
                "complete_text_sha256": digest(text),
                "complete_text": text,
                "scoped_text": scoped,
                "complete_scope_start": start,
                "complete_scope_end": end,
                "retrieved_at": record["retrieved_at"],
                "final_url": record["final_url"],
                "duplicate_of": "",
            }
        )
        coverage.append(
            {
                "document_id": source["document_id"],
                "group": "dsa",
                "caucus": source["group"],
                "status": "eligible",
                "text_sha256": digest(scoped),
                "words": len(scoped.split()),
                "publication_date": source["publication_date"],
                "version_date": source.get("version_date", ""),
            }
        )
    output = root / CORPUS.relative_to(ROOT)
    output.mkdir(parents=True, exist_ok=True)
    write_rows(output / "complete_sources.csv", sources)
    write_rows(output / "coverage.csv", coverage)
    summary = {
        "status": "primary_corpus_prepared",
        "caucuses_and_networks": len({row["caucus"] for row in sources}),
        "documents": len(sources),
        "scoped_words": sum(row["words"] for row in coverage),
        "discovery_sources_excluded_from_denominators": ledger["discovery_sources"],
        "roster_disposition": ledger["roster_disposition"],
        "supplemental_sources_excluded_from_primary_denominators": ledger["supplemental_sources"],
        "scope": ledger["scope"],
        "counts_are_documents_not_membership_or_influence": True,
    }
    write_json(output / "summary.json", summary)
    return summary


def caucus_claim_rows(claims: list[dict], sources: list[dict]) -> list[dict]:
    documents = {row["document_id"]: row for row in sources}
    result = []
    for claim in claims:
        if str(claim["analysis_eligible"]).lower() != "true":
            continue
        source = documents[claim["document_id"]]
        start, end = int(claim["source_start"]), int(claim["source_end"])
        if source["scoped_text"][start:end] != claim["evidence"]:
            raise ValueError(f"Claim evidence mismatch: {claim['claim_id']}")
        result.append(
            {
                **claim,
                "group": source["caucus"],
                "organization": source["organization"],
                "bundle_id": source["document_id"],
                "text": claim["claim_text"],
                "strict": False,
                "complete_source_start": int(source["complete_scope_start"]) + start,
                "complete_source_end": int(source["complete_scope_start"]) + end,
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "extract", "analyze"))
    parser.add_argument("--max-new-blocks", type=int)
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    if args.stage == "analyze":
        from dsa_caucus_comparison import analyze

        print(json.dumps(analyze(), indent=2))
        return
    if args.stage == "prepare":
        print(json.dumps(prepare_sources(), indent=2))
    summary = extract_corpus(
        output=CLAIMS,
        corpus=CORPUS,
        prepare_only=args.stage == "prepare",
        max_new_blocks=args.max_new_blocks,
        retry_failed=args.retry_failed,
    )
    rows = caucus_claim_rows(
        read_rows(CLAIMS / "claims.csv"), read_rows(CORPUS / "complete_sources.csv")
    )
    write_rows(CLAIMS / "caucus_claims.csv", rows)
    print(json.dumps({"extraction": summary, "eligible_caucus_claims": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
