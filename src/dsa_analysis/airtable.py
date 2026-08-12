import json
import re
import urllib.parse
import urllib.request
from typing import Any

from .io import write_csv
from .paths import PROCESSED_DIR, RAW_DIR

PAST_ENDORSEMENTS = (
    "https://airtable.com/embed/app41ni7RJppgXEBL/"
    "shrlm0oDQJkJsCnSr?backgroundColor=grayLight&viewControls=on"
)
CURRENT_ENDORSEMENTS = (
    "https://airtable.com/embed/app41ni7RJppgXEBL/"
    "shrlP3Do8lp7E52Ev?backgroundColor=grayLight&viewControls=on"
)
CHAPTER_DIRECTORY = (
    "https://airtable.com/embed/appVbWrpnpZXvsVJH/"
    "shrorpPIHVt83eIq0?backgroundColor=gray&viewControls=on"
)
USER_AGENT = "Mozilla/5.0 (compatible; dsa-analysis/0.1)"


def collect_national_endorsements() -> int:
    records: dict[str, dict[str, str]] = {}
    for label, url in (
        ("past", PAST_ENDORSEMENTS),
        ("current", CURRENT_ENDORSEMENTS),
    ):
        payload = fetch_shared_view(url)
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        (RAW_DIR / f"national-endorsements-{label}.json").write_text(
            json.dumps(payload, sort_keys=True),
            encoding="utf-8",
        )
        for row in normalize_table(payload):
            records[row["record_id"]] = _endorsement_row(row, url)

    rows = sorted(
        records.values(),
        key=lambda row: (row["election_date"], row["campaign"], row["record_id"]),
    )
    write_csv(
        PROCESSED_DIR / "national_endorsement_archive.csv",
        rows,
        [
            "record_id",
            "campaign",
            "office",
            "office_types",
            "national_endorsement",
            "election_date",
            "endorsing_chapters",
            "primary_result",
            "general_result",
            "created_time",
            "source_view_url",
        ],
    )
    return len(rows)


def collect_chapters() -> int:
    payload = fetch_shared_view(CHAPTER_DIRECTORY)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "chapter-directory.json").write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )
    normalized = normalize_table(payload)
    columns = sorted(
        {
            key
            for row in normalized
            for key in row
            if key not in {"record_id", "created_time"}
        }
    )
    rows = []
    for row in normalized:
        output = {
            "record_id": row["record_id"],
            "created_time": row["created_time"],
        }
        output.update({column: _stringify(row.get(column, "")) for column in columns})
        rows.append(output)
    write_csv(
        PROCESSED_DIR / "chapter_directory.csv",
        rows,
        ["record_id", "created_time", *columns],
    )
    return len(rows)


def fetch_shared_view(embed_url: str) -> dict[str, Any]:
    html_request = urllib.request.Request(
        embed_url,
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(html_request, timeout=60) as response:
        html = response.read().decode("utf-8")

    path_match = re.search(r'urlWithParams: "([^"]+)"', html)
    headers_match = re.search(r"var headers = (\{.*?\});", html)
    if not path_match or not headers_match:
        raise ValueError("Airtable shared-view bootstrap data was not found")

    relative_url = json.loads(f'"{path_match.group(1)}"')
    headers = json.loads(headers_match.group(1))
    headers.pop("x-airtable-accept-msgpack", None)
    headers.update({"User-Agent": USER_AGENT, "x-time-zone": "UTC"})
    data_url = urllib.parse.urljoin(embed_url, relative_url)
    data_request = urllib.request.Request(data_url, headers=headers)
    with urllib.request.urlopen(data_request, timeout=120) as response:
        return json.load(response)


def normalize_table(payload: dict[str, Any]) -> list[dict[str, Any]]:
    table = payload["data"]["table"]
    columns = {column["id"]: column for column in table["columns"]}
    rows = []
    for source_row in table["rows"]:
        row: dict[str, Any] = {
            "record_id": source_row["id"],
            "created_time": source_row.get("createdTime", ""),
        }
        for column_id, value in source_row.get("cellValuesByColumnId", {}).items():
            column = columns[column_id]
            row[column["name"]] = decode_value(column, value)
        rows.append(row)
    return rows


def decode_value(column: dict[str, Any], value: Any) -> Any:
    choices = (column.get("typeOptions") or {}).get("choices", {})
    if column["type"] == "select":
        return choices.get(value, {}).get("name", value)
    if column["type"] == "multiSelect":
        return [choices.get(item, {}).get("name", item) for item in value]
    if column["type"] == "foreignKey":
        return [
            item.get("foreignRowDisplayName", item.get("foreignRowId", ""))
            for item in value
        ]
    return value


def _endorsement_row(row: dict[str, Any], source_url: str) -> dict[str, str]:
    election_date = _stringify(row.get("Election Date", ""))[:10]
    national_endorsement = _stringify(row.get("Nat Endorsement", ""))
    if not national_endorsement and election_date:
        national_endorsement = f"Endorsed {election_date[:4]}"
    return {
        "record_id": row["record_id"],
        "campaign": _stringify(row.get("Campaign", "")),
        "office": _stringify(row.get("Office", "")),
        "office_types": _stringify(row.get("Office Type", "")),
        "national_endorsement": national_endorsement,
        "election_date": election_date,
        "endorsing_chapters": _stringify(row.get("Endorsing Chapter(s)", "")),
        "primary_result": _stringify(row.get("Primary Won?", "")),
        "general_result": _stringify(row.get("General/Overall Win", "")),
        "created_time": _stringify(row.get("created_time", "")),
        "source_view_url": source_url,
    }


def _stringify(value: Any) -> str:
    if isinstance(value, list):
        return " | ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)
