"""Territorial federal-primary results and disposition accounting."""

import argparse
import csv
import hashlib
from pathlib import Path

from .io import write_csv
from .paths import ANALYSIS_DATA_DIR, RAW_DIR
from .state_results import FIELDS

RAW_SUBDIR = "territorial_primaries"
RESULT_FILENAME = "territorial_primary_results.csv"

ACCOUNTING_FIELDS = [
    "cycle", "election_date", "state_code", "chamber", "district", "term",
    "stage", "primary_party", "status", "candidate_names", "source_urls",
    "locators", "notes",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_guam_2024(path: Path) -> list[dict]:
    output = []
    source_url = "https://gec.guam.gov/2024-primary-election-official-results/"
    source_html = path.parent / "gu-2024-primary-official-results.html"
    source_hash = _sha256(source_html)
    with path.open(newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), 2):
            write_in = row["write_in"] == "true"
            output.append({
                "contest_id": (
                    "gu-2024-08-03-house-00-regular-"
                    + row["primary_party"].lower()
                ),
                "cycle": "2024",
                "election_date": "2024-08-03",
                "stage": "primary",
                "state_code": "GU",
                "chamber": "House",
                "district": "00",
                "term": "regular",
                "election_system": "partisan_primary",
                "primary_party": row["primary_party"],
                "candidate_name": row["candidate_name"],
                "candidate_source_id": f"gu-2024-{number}",
                "party": "" if write_in else row["primary_party"],
                "write_in": write_in,
                "votes": int(row["votes"]),
                "source_id": "gu-2024-delegate-certified",
                "source_url": source_url,
                "source_sha256": source_hash,
                "source_locators": (
                    "gu-2024-primary-official-results.html:"
                    + row["source_locator"]
                ),
                "reporting_units": 1,
            })
    return output


def parse_vi_2026(path: Path) -> list[dict]:
    output = []
    source_url = (
        "https://vivote.gov/wp-content/uploads/2026/08/Territorial-Summary.pdf"
    )
    source_hash = _sha256(path)
    with path.open(newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), 2):
            write_in = row["write_in"] == "true"
            output.append({
                "contest_id": "vi-2026-08-01-house-00-regular-all",
                "cycle": "2026", "election_date": "2026-08-01",
                "stage": "primary", "state_code": "VI", "chamber": "House",
                "district": "00", "term": "regular",
                "election_system": "nonpartisan_primary", "primary_party": "",
                "candidate_name": row["candidate_name"],
                "candidate_source_id": f"vi-2026-{number}",
                "party": "", "write_in": write_in, "votes": int(row["votes"]),
                "source_id": "vi-2026-delegate-certified",
                "source_url": source_url, "source_sha256": source_hash,
                "source_locators": row["source_locator"], "reporting_units": 1,
            })
    return output


def _accounting(results: list[dict]) -> list[dict]:
    rows = []
    for party in ("Democratic", "Republican"):
        group = [row for row in results if row["primary_party"] == party]
        rows.append({
            "cycle": "2024", "election_date": "2024-08-03",
            "state_code": "GU", "chamber": "House", "district": "00",
            "term": "regular", "stage": "primary", "primary_party": party,
            "status": "results_complete",
            "candidate_names": " | ".join(row["candidate_name"] for row in group),
            "source_urls": group[0]["source_url"],
            "locators": " | ".join(row["source_locators"] for row in group),
            "notes": "Certified Guam Election Commission delegate primary totals.",
        })
    vi_group = [row for row in results if row["state_code"] == "VI"]
    rows.append({
        "cycle": "2026", "election_date": "2026-08-01",
        "state_code": "VI", "chamber": "House", "district": "00",
        "term": "regular", "stage": "primary", "primary_party": "",
        "status": "results_partial",
        "candidate_names": " | ".join(row["candidate_name"] for row in vi_group),
        "source_urls": vi_group[0]["source_url"],
        "locators": " | ".join(row["source_locators"] for row in vi_group),
        "notes": (
            "Certified numeric totals are preserved separately because the report does "
            "not establish a primary ballot category."
        ),
    })
    rows.append({
        "cycle": "2024", "election_date": "2024-08-03",
        "state_code": "VI", "chamber": "House", "district": "00",
        "term": "regular", "stage": "primary", "primary_party": "",
        "status": "unresolved", "candidate_names": "",
        "source_urls": (
            "https://vivote.gov/wp-content/uploads/2024/08/"
            "Official-Territorial-Results.pdf"
        ),
        "locators": "complete-certified-territorial-primary-report-pages-1-2",
        "notes": (
            "The certified territorial summary contains no delegate contest, but it does "
            "not explicitly state that no delegate primary was required or held."
        ),
    })
    for party in ("Democratic", "Republican"):
        rows.append({
            "cycle": "2026", "election_date": "2026-08-01",
            "state_code": "VI", "chamber": "House", "district": "00",
            "term": "regular", "stage": "primary", "primary_party": party,
            "status": "unresolved", "candidate_names": "",
            "source_urls": vi_group[0]["source_url"], "locators": "",
            "notes": (
                "The certified report does not identify which party ballot, if any, "
                "contains the delegate contest; numeric totals do not satisfy this slot."
            ),
        })
    unresolved = (
        ("GU", "2026", "2026-08-01", "https://gec.guam.gov/category/results/"),
        ("PR", "2024", "2024-06-02", "https://www.ceepur.org/primarias2024/"),
    )
    for state, cycle, date, url in unresolved:
        rows.append({
            "cycle": cycle, "election_date": date, "state_code": state,
            "chamber": "House", "district": "00", "term": "regular",
            "stage": "primary", "primary_party": "",
            "status": "unresolved", "candidate_names": "",
            "source_urls": url, "locators": "",
            "notes": (
                "No complete certified federal-primary contest table or explicit "
                "no-primary statement was recovered in the bounded search."
            ),
        })
    rows.append({
        "cycle": "2026", "election_date": "", "state_code": "PR",
        "chamber": "House", "district": "00", "term": "regular",
        "stage": "primary", "primary_party": "", "status": "not_scheduled",
        "candidate_names": "",
        "source_urls": (
            "https://www.ceepur.org/subastas/docs/2026/RFP-Escrutinio/es/"
            "SOLICITUD-DE-PROPUESTAS-ESCRUTINIO-ELECTRONICO-2028-%28final%29.pdf"
        ),
        "locators": "footnote-7-and-footnote-9",
        "notes": (
            "Official CEE procurement document states the next party primaries are "
            "June 6, 2028 and identifies Resident Commissioner as a federal office."
        ),
    })
    return rows


def collect_territorial_primaries(
    raw_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict:
    raw_dir = raw_dir or RAW_DIR / RAW_SUBDIR
    output_dir = output_dir or ANALYSIS_DATA_DIR / "congressional"
    ledger = output_dir / "territories"
    ledger.mkdir(parents=True, exist_ok=True)
    source_path = raw_dir / "guam/gu-2024-delegate-reviewed-extraction.csv"
    results = parse_guam_2024(source_path)
    vi_path = raw_dir / "virgin_islands/vi-2026-delegate-certified.csv"
    vi_partial = parse_vi_2026(vi_path)
    write_csv(output_dir / RESULT_FILENAME, results, FIELDS)
    write_csv(ledger / "partial_results.csv", vi_partial, FIELDS)
    accounting = _accounting(results + vi_partial)
    write_csv(ledger / "party_accounting.csv", accounting, ACCOUNTING_FIELDS)
    sources = [
        {
            "source_id": "gu-2024-delegate-certified",
            "source_url": "https://gec.guam.gov/2024-primary-election-official-results/",
            "raw_filename": "guam/gu-2024-delegate-reviewed-extraction.csv",
            "sha256": _sha256(source_path),
            "status": "reviewed_extraction_from_certified_source",
            "artifact_kind": "reviewed_extraction",
            "parent_source": "guam/gu-2024-primary-official-results.html",
            "parent_sha256": _sha256(
                raw_dir / "guam/gu-2024-primary-official-results.html"
            ),
        },
        {
            "source_id": "vi-2026-delegate-certified",
            "source_url": (
                "https://vivote.gov/wp-content/uploads/2026/08/"
                "Territorial-Summary.pdf"
            ),
            "raw_filename": "virgin_islands/vi-2026-delegate-certified.csv",
            "sha256": _sha256(vi_path),
            "status": "partial_numeric_party_unknown",
            "artifact_kind": "reviewed_extraction",
            "parent_source": "virgin_islands/vi-2026-primary-official.pdf",
            "parent_sha256": _sha256(
                raw_dir / "virgin_islands/vi-2026-primary-official.pdf"
            ),
        },
        {
            "source_id": "vi-2024-primary-territorial-report",
            "source_url": (
                "https://vivote.gov/wp-content/uploads/2024/08/"
                "Official-Territorial-Results.pdf"
            ),
            "raw_filename": "virgin_islands/vi-2024-primary-official.pdf",
            "sha256": _sha256(
                raw_dir / "virgin_islands/vi-2024-primary-official.pdf"
            ),
            "status": "source_record_unresolved",
            "artifact_kind": "official_certified_report",
            "parent_source": "",
            "parent_sha256": "",
        },
        {
            "source_id": "pr-2026-schedule",
            "source_url": accounting[-1]["source_urls"],
            "raw_filename": "puerto_rico/pr-2026-next-primary-schedule.pdf",
            "sha256": _sha256(
                raw_dir / "puerto_rico/pr-2026-next-primary-schedule.pdf"
            ),
            "status": "not_scheduled_verified",
            "artifact_kind": "official_schedule_evidence",
            "parent_source": "puerto_rico/pr-2026-next-primary-schedule.pdf",
            "parent_sha256": _sha256(
                raw_dir / "puerto_rico/pr-2026-next-primary-schedule.pdf"
            ),
        },
    ]
    write_csv(ledger / "source_manifest.csv", sources, list(sources[0]))
    summary = [
        {
            "territory": row["state_code"], "cycle": row["cycle"],
            "status": row["status"], "source_urls": row["source_urls"],
            "notes": row["notes"],
        }
        for row in accounting
        if row["status"] in {"unresolved", "not_scheduled", "results_partial"}
    ]
    write_csv(
        ledger / "coverage_summary.csv",
        summary,
        ["territory", "cycle", "status", "source_urls", "notes"],
    )
    inventory = [
        {
            "path": str(path.relative_to(raw_dir.parents[2])),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in (
            source_path,
            raw_dir / "guam/gu-2024-primary-official-results.html",
            raw_dir / "guam/gu-2024-primary-certified-results.pdf",
            vi_path,
            raw_dir / "virgin_islands/vi-2024-primary-official.pdf",
            raw_dir / "virgin_islands/vi-2026-primary-official.pdf",
            raw_dir / "puerto_rico/pr-2026-next-primary-schedule.pdf",
        )
    ]
    write_csv(ledger / "raw_artifacts.csv", inventory, ["path", "sha256", "bytes"])
    return {
        "result_rows": len(results),
        "contests": len({row["contest_id"] for row in results}),
        "accounting_rows": len(accounting),
        "unresolved_units": sum(row["status"] == "unresolved" for row in accounting),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    summary = collect_territorial_primaries(args.raw_dir, args.output_dir)
    print(" ".join(f"{key}={value}" for key, value in summary.items()))


if __name__ == "__main__":
    main()
