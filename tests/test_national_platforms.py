import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.national_platforms import (
    ContentParser,
    digest,
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
            output = raw / "out"
            original, _ = prepare_corpus([row], Tokenizer(), raw=raw, output=output)
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
