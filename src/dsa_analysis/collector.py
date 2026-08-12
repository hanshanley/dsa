import hashlib
import json
import mimetypes
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from .io import read_json
from .paths import CONFIG_DIR, RAW_DIR

USER_AGENT = "dsa-analysis/0.1 (+source-first academic research)"


def collect_sources() -> tuple[int, int]:
    registry = read_json(CONFIG_DIR / "sources.json")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW_DIR / "manifest.jsonl"
    successes = 0
    failures = 0
    with manifest_path.open("a", encoding="utf-8") as manifest:
        for source in registry["sources"]:
            record = _collect_one(source)
            manifest.write(json.dumps(record, sort_keys=True) + "\n")
            if record["status"] == "ok":
                successes += 1
            else:
                failures += 1
    return successes, failures


def _collect_one(source: dict[str, object]) -> dict[str, object]:
    document_id = str(source["document_id"])
    url = str(source["url"])
    retrieved_at = datetime.now(UTC).isoformat()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            content = response.read()
            content_type = response.headers.get_content_type()
            suffix = _suffix(url, content_type)
            output_path = RAW_DIR / f"{document_id}{suffix}"
            output_path.write_bytes(content)
            return {
                "document_id": document_id,
                "url": url,
                "final_url": response.geturl(),
                "retrieved_at": retrieved_at,
                "status": "ok",
                "http_status": response.status,
                "content_type": content_type,
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "path": str(output_path.relative_to(RAW_DIR.parent.parent)),
            }
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return {
            "document_id": document_id,
            "url": url,
            "retrieved_at": retrieved_at,
            "status": "error",
            "error": f"{type(error).__name__}: {error}",
        }


def _suffix(url: str, content_type: str) -> str:
    path_suffix = Path(urlparse(url).path).suffix
    if path_suffix:
        return path_suffix
    return mimetypes.guess_extension(content_type) or ".bin"
