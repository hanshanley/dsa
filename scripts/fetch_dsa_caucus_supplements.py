"""Collect public supplemental documents without altering flagship snapshots."""

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from dsa_analysis.document_corpus import _extract_pdf_text
from dsa_analysis.national_platforms import digest, write_json

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ledger = json.loads((ROOT / "data/manual/dsa_caucus_sources.json").read_text())
    path = ROOT / "data/raw/dsa_caucuses/retrieval.json"
    records = {row["document_id"]: row for row in json.loads(path.read_text())}
    for source in ledger["supplemental_sources"]:
        request = Request(source["download_url"], headers={"User-Agent": "DSA-source-research/1.0"})
        with urlopen(request, timeout=60) as response:
            raw, final_url = response.read(), response.url
        if source["format"] == "pdf":
            if not raw.startswith(b"%PDF"):
                raise ValueError("Public download is not a PDF")
            title, text = _extract_pdf_text(raw)
            extension = "pdf"
        else:
            title, text = source["title"], raw.decode("utf-8-sig")
            extension = "export.txt"
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if len(text.split()) < 100 or "<!doctype html" in text.lower():
            raise ValueError(f"Missing political document: {source['document_id']}")
        record = {
            **source,
            "status": "retrieved",
            "retrieved_at": datetime.now(UTC).isoformat(),
            "final_url": final_url,
            "embedded_document_title": title,
            "raw_source": f"data/raw/dsa_caucuses/{source['document_id']}.{extension}",
            "text_file": f"data/raw/dsa_caucuses/{source['document_id']}.txt",
            "source_sha256": digest(raw),
            "complete_text_sha256": digest(text),
        }
        (ROOT / record["raw_source"]).write_bytes(raw)
        (ROOT / record["text_file"]).write_text(text)
        records[source["document_id"]] = record
        print(f"{source['document_id']}: {len(text.split())} words; {source['role']}", flush=True)
    write_json(path, list(records.values()))


if __name__ == "__main__":
    main()
