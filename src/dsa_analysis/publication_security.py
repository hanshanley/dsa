"""Remove incidental credentials from source snapshots and audit publication blobs."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import re
import subprocess
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_from_bytes

VERSION = "publication-credential-redaction-v1"
MAX_EXPANDED_BYTES = 512 * 1024 * 1024
PLACEHOLDER = b"REDACTED"


def source_version_digest(source: dict) -> str:
    """Keep source-version identifiers stable across a documented publication redaction."""
    ledger = Path(__file__).resolve().parents[2] / "data/analysis/publication_redactions.json"
    if not ledger.exists():
        return source["sha256"]
    matches = [
        row for row in json.loads(ledger.read_text())["files"]
        if row["path"] == source.get("raw_path")
    ]
    if not matches:
        return source["sha256"]
    if len(matches) != 1 or matches[0]["public_sha256"] != source["sha256"]:
        raise ValueError("Published source does not match its redaction provenance")
    return matches[0]["original_sha256"]


RULES = {
    "google_api_key": re.compile(rb"AIza[0-9A-Za-z_-]{35}"),
    "github_token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{70,})\b"),
    "aws_access_identifier": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "mapbox_token": re.compile(rb"\b(?:pk|sk|tk)\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    "jwt": re.compile(rb"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    "slack_token": re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "openai_key": re.compile(rb"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}\b"),
    "private_key": re.compile(
        rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"
        rb"[\s\S]+?-----END (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"
    ),
}
QUERY_SECRET = re.compile(
    rb"(?i)(?:[?&;]|&amp;|\\u0026|%26|%3f)"
    rb"(?:x-amz-(?:signature|credential|security-token)|awsaccesskeyid|signature|sig|"
    rb"access_token|auth_token|api_key|apikey|token|pwd)"
    rb"(?:=|%3d)(?P<value>[^&\s<>\"'\\#]+)"
)
SESSION_ID = re.compile(rb"(?i);jsessionid=(?P<value>[A-Za-z0-9._-]+)")
ASSIGNMENT = re.compile(
    rb"""(?ix)
    (?<![a-z0-9_.-])(?:["']|\\["'])?
    [a-z0-9_.-]{0,45}
    (?:api[_-]?key|api[_-]?secret|secret[_-]?key|client[_-]?secret|
       access[_-]?token|auth[_-]?token|session[_-]?token|softwarestatement)
    [a-z0-9_.-]{0,15}
    (?:["']|\\["'])?\s*[:=]\s*(?:["']|\\["'])
    (?P<value>[a-z0-9_./+=:-]{12,})
    """
)
TOKEN_ASSIGNMENT = re.compile(
    rb"""(?ix)(?<![a-z0-9_])
    (?:["']|\\["'])?(?:token|auth|bitoken|gmrenderkey|clienttoken|entitlementsapikey)
    (?:["']|\\["'])?\s*[:=]\s*(?:["']|\\["'])
    (?P<value>[a-z0-9_./+=:-]{12,})
    """
)
OPAQUE = re.compile(rb"(?<![A-Za-z0-9_+/=-])[A-Za-z0-9_+/-]{48,}={0,2}(?![A-Za-z0-9_+/=-])")


@dataclass(frozen=True)
class Finding:
    kind: str
    start: int
    end: int


def marker(length: int) -> bytes:
    return (PLACEHOLDER + b"_" * length)[:length]


def is_redacted(value: bytes) -> bool:
    return value.startswith(PLACEHOLDER) and not value.removeprefix(PLACEHOLDER).strip(b"_")


def literal_pattern(values: list[bytes]) -> re.Pattern[bytes] | None:
    variants = set()
    for value in values:
        if len(value) < 8 or is_redacted(value):
            continue
        variants.add(value)
        variants.add(value.replace(b"/", b"\\/"))
        encoded = value
        for _ in range(3):
            encoded = quote_from_bytes(encoded, safe="").encode()
            variants.add(encoded)
    if not variants:
        return None
    trie = {}
    for value in variants:
        node = trie
        for byte in value:
            node = node.setdefault(byte, {})
        node[None] = {}

    def expression(node):
        prefix = bytearray()
        while len(node) == 1 and None not in node:
            byte, node = next(iter(node.items()))
            prefix.append(byte)
        branches = [
            re.escape(bytes([byte])) + expression(child)
            for byte, child in node.items() if byte is not None
        ]
        if None in node:
            branches.append(b"")
        tail = branches[0] if len(branches) == 1 else b"(?:" + b"|".join(branches) + b")"
        return re.escape(bytes(prefix)) + tail

    return re.compile(expression(trie))


def findings(data: bytes, literals: re.Pattern[bytes] | None = None) -> list[Finding]:
    result = [
        Finding(kind, match.start(), match.end())
        for kind, pattern in RULES.items() for match in pattern.finditer(data)
    ]
    for kind, pattern in (
        ("signed_or_authenticated_url", QUERY_SECRET),
        ("session_url", SESSION_ID),
        ("credential_assignment", ASSIGNMENT),
        ("opaque_client_token", TOKEN_ASSIGNMENT),
    ):
        for match in pattern.finditer(data):
            if not is_redacted(match["value"]):
                result.append(Finding(kind, match.start("value"), match.end("value")))
    if literals is not None:
        result.extend(Finding("scanner_identified_value", m.start(), m.end()) for m in literals.finditer(data))
    return result


def sanitize(
    data: bytes, literals: re.Pattern[bytes] | None = None, *, depth: int = 0,
) -> tuple[bytes, Counter]:
    if depth > 4:
        raise ValueError("Publication redaction nesting exceeds the supported limit")
    if data.startswith(b"\x1f\x8b"):
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as handle:
            decoded = handle.read(MAX_EXPANDED_BYTES + 1)
        if len(decoded) > MAX_EXPANDED_BYTES:
            raise ValueError("Compressed publication payload exceeds the expansion limit")
        clean, counts = sanitize(decoded, literals, depth=depth + 1)
        return (gzip.compress(clean, mtime=0), counts) if clean != decoded else (data, counts)
    if data.startswith(b"PK\x03\x04"):
        counts = Counter()
        updates = {}
        with zipfile.ZipFile(io.BytesIO(data)) as source:
            entries = source.infolist()
            for index, info in enumerate(entries):
                if info.file_size > MAX_EXPANDED_BYTES:
                    raise ValueError("Archive publication member exceeds the expansion limit")
                content = source.read(info)
                clean, found = sanitize(content, literals, depth=depth + 1)
                if clean != content:
                    updates[index] = clean
                counts.update(found)
            if not updates:
                return data, counts
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w") as target:
                for index, info in enumerate(entries):
                    target.writestr(info, updates[index] if index in updates else source.read(info))
        return output.getvalue(), counts
    counts = Counter()

    def encoded(match: re.Match[bytes]) -> bytes:
        value = match[0]
        if depth >= 3 or len(value) > 8 * 1024 * 1024:
            return value
        try:
            decoded = base64.b64decode(value + b"=" * (-len(value) % 4), altchars=b"-_", validate=True)
            decoded.decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return value
        if not findings(decoded, literals):
            return value
        clean, found = sanitize(decoded, literals, depth=depth + 1)
        counts.update(found)
        counts["encoded_container"] += 1
        output = base64.urlsafe_b64encode(clean) if b"-" in value or b"_" in value else base64.b64encode(clean)
        return output if value.endswith(b"=") else output.rstrip(b"=")

    # Do not reinterpret arbitrary binary payloads as encoded textual containers.
    textual = b"\x00" not in data[:4096]
    current = OPAQUE.sub(encoded, data) if textual else data
    spans = findings(current, literals)
    if not spans:
        return current, counts
    intervals = []
    for item in sorted(spans, key=lambda f: (f.start, -f.end)):
        counts[item.kind] += 1
        if intervals and item.start <= intervals[-1][1]:
            intervals[-1] = (intervals[-1][0], max(intervals[-1][1], item.end))
        else:
            intervals.append((item.start, item.end))
    parts, offset = [], 0
    for start, end in intervals:
        parts.extend((current[offset:start], marker(end - start)))
        offset = end
    parts.append(current[offset:])
    return b"".join(parts), counts


def scan_git(ref: str | None = None, *, all_staged: bool = False) -> list[dict]:
    if ref is None:
        entries = subprocess.check_output(["git", "ls-files", "-s", "-z"]).split(b"\0")
        blobs = [(entry.split(b"\t", 1)[1].decode(), entry.split()[1].decode()) for entry in entries if entry]
        if not all_staged:
            changed = set(subprocess.check_output([
                "git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT", "-z",
            ]).decode().split("\0")) - {""}
            changed_shards = {
                re.sub(r"\.part-\d+$", "", path) for path in changed
                if re.search(r"\.gz\.part-\d+$", path)
            }
            blobs = [(path, oid) for path, oid in blobs if path in changed or any(
                path.startswith(prefix + ".part-") for prefix in changed_shards
            )]
    else:
        entries = subprocess.check_output(["git", "ls-tree", "-r", "-z", ref]).split(b"\0")
        blobs = [
            (entry.split(b"\t", 1)[1].decode(), entry.split()[2].decode())
            for entry in entries if entry and entry.split()[1] == b"blob"
        ]
    failures = []
    shards: dict[str, list[tuple[int, str]]] = {}
    ordinary = []
    for path, oid in blobs:
        match = re.fullmatch(r"(.+\.gz)\.part-(\d+)", path)
        if match:
            shards.setdefault(match[1], []).append((int(match[2]), oid))
        else:
            ordinary.append((path, oid))
    for path, parts in shards.items():
        parts.sort()
        if [n for n, _ in parts] != list(range(len(parts))):
            raise ValueError("Publication archive parts are missing or out of order")
        data = b"".join(subprocess.check_output(["git", "cat-file", "blob", oid]) for _, oid in parts)
        clean, counts = sanitize(data)
        if clean != data:
            failures.append({"path": path + ".parts", "kinds": dict(counts)})
    for path, oid in ordinary:
        data = subprocess.check_output(["git", "cat-file", "blob", oid])
        clean, counts = sanitize(data)
        if clean != data:
            failures.append({"path": path, "kinds": dict(counts)})
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan publication blobs without printing credential values.")
    parser.add_argument("--ref", help="Git tree to audit; default is the staged index.")
    parser.add_argument("--all-staged", action="store_true", help="Audit the entire staged tree, not only changed paths.")
    args = parser.parse_args()
    failures = scan_git(args.ref, all_staged=args.all_staged)
    print(json.dumps({"credential_values_printed": False, "findings": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
