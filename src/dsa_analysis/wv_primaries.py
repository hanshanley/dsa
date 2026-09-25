"""Account for blocked West Virginia congressional primary result sources."""

import argparse
import csv
import hashlib
from pathlib import Path

from .io import write_csv
from .paths import ANALYSIS_DATA_DIR, RAW_DIR
from .state_results import FIELDS

RAW_SUBDIR = "wv_primaries"
RESULT_FILENAME = "wv_primary_results.csv"

ACCOUNTING_FIELDS = [
    "cycle", "election_date", "state_code", "chamber", "district", "term",
    "stage", "primary_party", "status", "candidate_names", "source_urls",
    "locators", "notes",
]

SOURCES = (
    {
        "source_id": "wv-2024-primary-clarity",
        "cycle": "2024",
        "date": "2024-05-14",
        "url": (
            "https://results.enr.clarityelections.com/WV/120641/"
            "web.317647/#/summary"
        ),
    },
    {
        "source_id": "wv-2026-primary-clarity",
        "cycle": "2026",
        "date": "2026-05-12",
        "url": (
            "https://results.enr.clarityelections.com/WV/126209/"
            "web.345435/#/summary"
        ),
    },
)

SENATE_SCHEDULE = {
    ("WV", "2024"): {"term": "regular", "election_date": "2024-05-14"},
    ("WV", "2026"): {"term": "regular", "election_date": "2026-05-12"},
}


def validate_clarity_payload(payload: bytes) -> None:
    if not payload:
        raise ValueError("Empty Clarity response is not election data")
    text = payload[:200].decode("utf-8", errors="ignore").casefold()
    if "captcha" in text or "access denied" in text:
        raise ValueError("Blocked Clarity response is not election data")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _accounting() -> list[dict]:
    rows = []
    for source in SOURCES:
        for district in ("01", "02"):
            for party in ("Democratic", "Republican"):
                rows.append({
                    "cycle": source["cycle"],
                    "election_date": source["date"],
                    "state_code": "WV",
                    "chamber": "House",
                    "district": district,
                    "term": "regular",
                    "stage": "primary",
                    "primary_party": party,
                    "status": "unresolved",
                    "candidate_names": "",
                    "source_urls": source["url"],
                    "locators": "",
                    "notes": (
                        "Official Clarity route identified, but shell and data files returned "
                        "empty bodies. Empty HTTP 200 responses are not treated as no races."
                    ),
                })
        senate_schedule = SENATE_SCHEDULE.get(("WV", source["cycle"]))
        if senate_schedule is not None:
            for party in ("Democratic", "Republican"):
                rows.append({
                    "cycle": source["cycle"],
                    "election_date": senate_schedule["election_date"],
                    "state_code": "WV", "chamber": "Senate", "district": "S",
                    "term": senate_schedule["term"], "stage": "primary",
                    "primary_party": party, "status": "unresolved",
                    "candidate_names": "",
                    "source_urls": (
                        source["url"]
                        + (
                            " | https://www.fec.gov/documents/5910/2026pdates.pdf"
                            if source["cycle"] == "2026" else ""
                        )
                    ),
                    "locators": "",
                    "notes": (
                        "Regular Senate election is independently scheduled; certified "
                        "numeric primary results were not recovered."
                    ),
                })
    return rows


def collect_wv_primaries(
    raw_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict:
    raw_dir = raw_dir or RAW_DIR / RAW_SUBDIR
    output_dir = output_dir or ANALYSIS_DATA_DIR / "congressional"
    ledger = output_dir / "wv"
    ledger.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / RESULT_FILENAME, [], FIELDS)
    accounting = _accounting()
    write_csv(ledger / "party_contest_accounting.csv", accounting, ACCOUNTING_FIELDS)
    manifest = []
    for source in SOURCES:
        manifest.append({
            "source_id": source["source_id"], "state_code": "WV",
            "election_date": source["date"], "source_url": source["url"],
            "raw_filename": "", "sha256": "", "candidate_rows": 0,
            "contests": 0, "status": "empty_clarity_payload_unresolved",
            "notes": "No empty response was interpreted as data.",
        })
    report_path = raw_dir / "wv-2026-primary-report-page.html"
    if report_path.exists():
        manifest.append({
            "source_id": "wv-2026-primary-report", "state_code": "WV",
            "election_date": "2026-05-12",
            "source_url": (
                "https://sos.wv.gov/article/2026-primary-election-report-"
                "secretary-state-kris-warner-reports-252008-ballots-were-cast"
            ),
            "raw_filename": report_path.name, "sha256": _sha256(report_path),
            "candidate_rows": 0, "contests": 0,
            "status": "certification_context_only",
            "notes": "Report confirms certification but does not provide candidate totals.",
        })
    write_csv(ledger / "source_manifest.csv", manifest, list(manifest[0]))
    return {
        "result_rows": 0,
        "accounting_rows": len(accounting),
        "sources": len(manifest),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    summary = collect_wv_primaries(args.raw_dir, args.output_dir)
    print(" ".join(f"{key}={value}" for key, value in summary.items()))


if __name__ == "__main__":
    main()
