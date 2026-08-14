import csv
import gzip
import json
from pathlib import Path
from typing import Any


def read_csv(path: Path) -> list[dict[str, str]]:
    if path.exists():
        handle = path.open(newline="", encoding="utf-8")
    elif path.with_suffix(path.suffix + ".gz").exists():
        handle = gzip.open(
            path.with_suffix(path.suffix + ".gz"),
            mode="rt",
            newline="",
            encoding="utf-8",
        )
    else:
        raise FileNotFoundError(path)
    with handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def merge_notes(*values: str) -> str:
    notes = []
    seen = set()
    for value in values:
        for note in value.split(" | "):
            note = note.strip()
            if note and note not in seen:
                seen.add(note)
                notes.append(note)
    return " | ".join(notes)


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
