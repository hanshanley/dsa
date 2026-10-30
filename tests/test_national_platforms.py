import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.national_platforms import (
    ContentParser,
    digest,
    export_document_archive,
    fetch_sources,
    ledger_status,
    load_ledger,
    prepare_corpus,
    read_rows,
    scope_text,
    split_passages,
    write_json,
    write_rows,
)


class Tokenizer:
    def num_special_tokens_to_add(self, pair=False):
        return 2

    def __call__(self, text, add_special_tokens=True, return_offsets_mapping=False):
        offsets = [match.span() for match in re.finditer(r"\S+", text)]
        result = {"input_ids": list(range(len(offsets) + (2 if add_special_tokens else 0)))}
        if return_offsets_mapping:
            result["offset_mapping"] = offsets
        return result


def entry(identifier="dsa-2024", **updates):
    return {
        "document_id": identifier,
        "group": "dsa",
        "organization_level": "national",
        "document_type": "program",
        "adoption_status": "adopted",
        "publication_date": "2024",
        "title": "National program",
        "source_url": "https://example.test/program",
        "alternate_url": "",
        "source_class": "first_party",
        "verification_status": "verified",
        "reuse_of": "",
        "bundle_id": "",
        "html_class": "content",
        "scope_start": "",
        "scope_end": "",
        "notes": "",
        **updates,
    }


def capture(raw, row, content):
    data = content.encode()
    (raw / f"{row['document_id']}.source").write_bytes(data)
    write_json(
        raw / f"{row['document_id']}.json",
        {
            "source_url": row["source_url"],
            "final_url": row["source_url"],
            "content_type": "text/html",
            "retrieved_at": "2026-10-26T00:00:00Z",
            "sha256": digest(data),
        },
    )


class NationalCorpusTests(unittest.TestCase):
    def test_isolated_libertarian_coverage_and_dsa_only_fallback_rule(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            row = entry("libertarian-2022", group="libertarian", document_type="platform")
            ledger = root / "ledger.csv"
            write_rows(ledger, [row])
            self.assertEqual(load_ledger(ledger), [row])
            capture(
                root,
                row,
                '<article class="content">'
                + "".join(
                    f"<p>National policy evidence passage {i} supporting individual rights.</p>"
                    for i in range(10)
                )
                + "</article>",
            )
            passages, coverage = prepare_corpus(
                [row], Tokenizer(), raw=root, output=root / "output"
            )
            self.assertEqual(coverage[0]["status"], "eligible")
            self.assertTrue(all(passage["strict"] for passage in passages))
            self.assertEqual(
                {row["group"] for row in read_rows(root / "output/year_coverage.csv")},
                {"libertarian"},
            )
            write_rows(ledger, [{**row, "document_type": "statement"}])
            with self.assertRaisesRegex(ValueError, "restricted to national DSA"):
                load_ledger(ledger)

    def test_national_groups_and_reuse_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ledger.csv"
            rows = [
                entry("dsa-2024"),
                entry("democratic-2024", group="democratic"),
                entry("republican-2016", group="republican"),
                entry("republican-2020", group="republican", reuse_of="republican-2016"),
            ]
            write_rows(path, rows)
            self.assertEqual(len(load_ledger(path)), 4)
            for updates in (
                {"organization_level": "state"},
                {"group": "candidate"},
                {"reuse_of": "dsa-2024"},
            ):
                write_rows(path, [*rows[:-1], {**rows[-1], **updates}])
                with self.assertRaises(ValueError):
                    load_ledger(path)

    def test_cutoff_draft_and_uncertain_dates(self):
        self.assertEqual(ledger_status(entry(), "2024-12-31"), "eligible")
        self.assertEqual(
            ledger_status(entry(), "2024-06-30"),
            "outside_cutoff_or_uncertain_boundary",
        )
        self.assertEqual(
            ledger_status(entry(adoption_status="draft"), "2026-10-26"),
            "adoption_unverified",
        )
        self.assertEqual(
            ledger_status(entry(reuse_of="dsa-old"), "2026-10-26"),
            "reused_document",
        )
        self.assertEqual(
            ledger_status(entry(version_date="2025-04-15"), "2024-12-31"),
            "version_after_cutoff",
        )

    def test_html_scope_and_token_limit_preserve_traceability(self):
        parser = ContentParser("content")
        parser.feed(
            '<nav>OUTSIDE</nav><article class="content"><p>first<br/>second'
            '<img src="x">third</p><script>HIDDEN</script><nav>SKIP</nav>'
            "<p>last</p></article><footer>OUTSIDE</footer>"
        )
        self.assertEqual(parser.text(), "first\n\nsecondthird\n\nlast")
        scoped = scope_text(
            "A intro END noise B conclusion STOP",
            {
                "document_id": "dsa-test",
                "scope_start": "A || B",
                "scope_end": "END || STOP",
            },
        )
        self.assertEqual(scoped, "A intro\n\nB conclusion")
        text = " ".join(f"word{number}" for number in range(100))
        chunks = split_passages(text, Tokenizer(), max_length=24)
        self.assertTrue(all(chunk["token_count"] <= 24 for chunk in chunks))
        self.assertTrue(all(chunk["text"] in text for chunk in chunks))
        self.assertEqual(" ".join(chunk["text"] for chunk in chunks), text)

    def test_mirrors_reuse_strict_views_bundles_and_full_text_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            raw = Path(temporary)
            base = entry("dsa-base")
            mirror = entry("dsa-mirror")
            cross_group = entry("democratic-base", group="democratic")
            reused = entry("dsa-reused", reuse_of="dsa-base")
            statement_a = entry(
                "dsa-statement-a",
                document_type="statement",
                adoption_status="official_statement",
                bundle_id="dsa-period",
            )
            statement_b = {**statement_a, "document_id": "dsa-statement-b"}
            long = "\n".join(
                f"<p>National housing workers policy evidence passage {i} for all people.</p>"
                for i in range(10)
            )
            short = "<p>Public healthcare evidence for every person without financial hardship.</p>"
            for row in (base, mirror, cross_group):
                capture(raw, row, f'<article class="content">{long}</article>')
            for row in (statement_a, statement_b):
                text = short if row == statement_a else long.replace("National", "Additional")
                capture(raw, row, f'<article class="content">{text}</article>')
            passages, coverage = prepare_corpus(
                [base, mirror, cross_group, reused, statement_a, statement_b],
                Tokenizer(),
                raw=raw,
                output=raw / "output",
            )
            statuses = {row["document_id"]: row["status"] for row in coverage}
            self.assertEqual(statuses["dsa-mirror"], "duplicate_document")
            self.assertEqual(statuses["dsa-reused"], "reused_document")
            self.assertEqual(statuses["democratic-base"], "eligible")
            self.assertEqual(statuses["dsa-statement-a"], "eligible")
            self.assertFalse(
                next(row["strict"] for row in passages if row["document_id"] == "dsa-statement-a")
            )
            sources = read_rows(raw / "output/complete_sources.csv")
            self.assertIn("passage 9", sources[0]["complete_text"])
            self.assertTrue(all(row["locator"] and row["source_sha256"] for row in passages))
            self.assertEqual(
                len(sources),
                len((raw / "output/complete_sources.jsonl").read_text().splitlines()),
            )

    def test_historical_winter_footers_do_not_enter_model_passages(self):
        for footer in (
            "page 4 • Democratic Left • Winter 2002",
            "Democratic Left • Winter 2006 • Page 4",
            "page 2 • Democratic Left • Fall-Winter 2001",
        ):
            text = (
                "Workers need public healthcare and democratic control of the economy. "
                f"{footer} Protect labor rights and expand access to public education."
            )
            passages = split_passages(text, Tokenizer())
            self.assertEqual(len(passages), 1)
            self.assertNotIn("Democratic Left", passages[0]["text"])
            self.assertIn(footer, text)

    def test_changed_source_url_invalidates_fetch_and_prepare_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            raw = Path(temporary)
            row = entry()
            capture(raw, row, '<article class="content">Old capture</article>')
            changed = {**row, "source_url": "https://example.test/new-version"}
            _, coverage = prepare_corpus([changed], Tokenizer(), raw=raw, output=raw / "out")
            self.assertEqual(coverage[0]["status"], "extraction_or_capture_error")
            with patch("dsa_analysis.national_platforms.subprocess.run") as run:
                run.return_value.returncode = 1
                run.return_value.stderr = "not available"
                attempts = fetch_sources([changed], raw)
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0]["url"], changed["source_url"])

    def test_official_api_preserves_complete_article(self):
        with tempfile.TemporaryDirectory() as temporary:
            raw = Path(temporary)
            row = entry()
            content = "<p>Public policy supporting every working person without exclusion.</p>"
            data = json.dumps({"content": {"rendered": content}}).encode()
            (raw / f"{row['document_id']}.source").write_bytes(data)
            write_json(
                raw / f"{row['document_id']}.json",
                {
                    "source_url": row["source_url"],
                    "final_url": row["source_url"],
                    "retrieved_at": "2026-10-26",
                    "content_type": "application/json",
                    "sha256": digest(data),
                },
            )
            _, coverage = prepare_corpus([row], Tokenizer(), raw=raw, output=raw / "out")
            self.assertEqual(coverage[0]["status"], "sparse_bundle")
            source = read_rows(raw / "out/complete_sources.csv")[0]
            self.assertEqual(
                source["complete_text"],
                "Public policy supporting every working person without exclusion.",
            )

    def test_complete_html_export_excludes_website_credentials_and_chrome(self):
        with tempfile.TemporaryDirectory() as temporary:
            raw = Path(temporary)
            row = entry(scope_start="Start policy", scope_end="End policy")
            capture(
                raw,
                row,
                '<script>window.theme_token="website-only"</script>'
                '<nav>Site navigation</nav><article class="content">'
                "<p>Document preface</p><p>Start policy supporting every working person "
                "without exclusion.</p><p>End policy</p></article>",
            )
            with patch(
                "dsa_analysis.national_platforms.extract_document_text",
                side_effect=AssertionError("Do not export the surrounding website"),
            ):
                prepare_corpus([row], Tokenizer(), raw=raw, output=raw / "out")
            source = read_rows(raw / "out/complete_sources.csv")[0]
            self.assertIn("Document preface", source["complete_text"])
            self.assertNotIn("Document preface", source["scoped_text"])
            self.assertNotIn("theme_token", source["complete_text"])
            self.assertNotIn("Site navigation", source["complete_text"])
            with zipfile.ZipFile(raw / "out/source_documents.zip") as archive:
                texts = b"\n".join(archive.read(name) for name in archive.namelist())
                self.assertIn(b"Document preface", texts)
                self.assertNotIn(b"theme_token", texts)
                self.assertNotIn(b"Site navigation", texts)

    def test_document_archive_deduplicates_pdfs_and_rebuilds_without_raw_captures(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw, output = root / "raw", root / "out"
            raw.mkdir()
            output.mkdir()
            pdf = b"%PDF-1.4\noriginal public document\n%%EOF\n"
            rows = []
            for identifier in ("dsa-first", "dsa-second"):
                row = entry(identifier)
                capture(raw, row, pdf.decode())
                meta_path = raw / f"{identifier}.json"
                metadata = json.loads(meta_path.read_text())
                metadata["content_type"] = "application/octet-stream"
                write_json(meta_path, metadata)
                rows.append(
                    {
                        **row,
                        **metadata,
                        "document_format": "pdf",
                        "complete_text": "Complete policy text including its preface.",
                        "complete_text_sha256": digest(
                            "Complete policy text including its preface."
                        ),
                    }
                )
            write_rows(output / "complete_sources.csv", rows)
            path = export_document_archive(output, raw)
            original = path.read_bytes()
            with zipfile.ZipFile(path) as archive:
                pdfs = [name for name in archive.namelist() if name.startswith("pdfs/")]
                self.assertEqual(len(pdfs), 1)
                self.assertEqual(archive.read(pdfs[0]), pdf)
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(len(manifest), 2)
                self.assertEqual(manifest[0]["pdf_path"], manifest[1]["pdf_path"])
                self.assertEqual(manifest[0]["pdf_source_url"], rows[0]["source_url"])
                self.assertEqual(manifest[0]["pdf_retrieved_at"], rows[0]["retrieved_at"])
            export_document_archive(output, root / "absent")
            self.assertEqual(path.read_bytes(), original)
            (raw / "dsa-first.source").write_bytes(b"%PDF-1.4\ncorrupt capture")
            with self.assertRaisesRegex(ValueError, "hash or format mismatch"):
                export_document_archive(output, raw)
            self.assertEqual(path.read_bytes(), original)
            path.unlink()
            export_document_archive(output, root / "absent")
            with zipfile.ZipFile(path) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                self.assertTrue(
                    all(
                        row["pdf_status"] == "capture_unavailable_complete_text_included"
                        for row in manifest
                    )
                )
                self.assertTrue(all(row["text_path"] in archive.namelist() for row in manifest))

    def test_offline_snapshot_reproduces_corpus_without_raw_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            raw = Path(temporary)
            row = entry()
            capture(
                raw,
                row,
                (
                    '<article class="content"><p>'
                    "Public policy supporting every working person without exclusion."
                    "</p></article>"
                ),
            )
            metadata_path = raw / f"{row['document_id']}.json"
            metadata = json.loads(metadata_path.read_text())
            metadata["requested_url"] = "https://web.archive.org/web/20241231/https://example.org/"
            write_json(metadata_path, metadata)
            output = raw / "out"
            original, _ = prepare_corpus([row], Tokenizer(), raw=raw, output=output)
            exports = {
                name: (output / name).read_bytes()
                for name in ("complete_sources.csv", "complete_sources.jsonl")
            }
            with patch(
                "dsa_analysis.national_platforms.extract_document_text",
                side_effect=AssertionError("Raw extractor must not run"),
            ):
                offline, coverage = prepare_corpus(
                    [row],
                    Tokenizer(),
                    raw=raw / "absent",
                    output=output,
                )
            self.assertEqual(original, offline)
            self.assertEqual(coverage[0]["status"], "sparse_bundle")
            for name, content in exports.items():
                self.assertEqual((output / name).read_bytes(), content)
