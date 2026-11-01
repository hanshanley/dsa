import json
import tempfile
import unittest
from pathlib import Path

from dsa_analysis.national_platforms import digest, read_rows
from scripts.dsa_caucus_analysis import caucus_claim_rows, prepare_sources, scoped_text
from scripts.dsa_caucus_comparison import attention_tables
from scripts.publish_dsa_caucuses import review_basis, validated_labels


class CaucusSourceTest(unittest.TestCase):
    def test_scope_uses_actual_section_not_contents_and_preserves_offsets(self):
        policy = " ".join(["Policy"] * 120)
        text = f"Contents\nStart\nEnd\n\nStart\n {policy} \nEnd\nJoin"
        source = {
            "document_id": "example",
            "scope_start": "Start",
            "scope_start_occurrence": "last",
            "scope_end": "End",
        }
        scoped, start, end = scoped_text(text, source)
        self.assertEqual(text[start:end], scoped)
        self.assertEqual(scoped, f"Start\n {policy}")
        self.assertNotIn("Join", scoped)

    def test_missing_boundaries_do_not_silently_include_unscoped_material(self):
        with self.assertRaisesRegex(ValueError, "Missing end boundary"):
            scoped_text("Policy " * 120, {"document_id": "example", "scope_end": "Missing"})

    def test_preparation_excludes_guides_and_supplements_and_keeps_unknown_dates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manual, raw = root / "data/manual", root / "data/raw/dsa_caucuses"
            manual.mkdir(parents=True)
            raw.mkdir(parents=True)
            text, html = "Policy " * 120, b"<html>Original source</html>"
            source = {
                "document_id": "one",
                "group": "first-caucus",
                "organization": "First Caucus",
                "title": "Principles",
                "publication_date": "",
            }
            ledger = {
                "sources": [source],
                "discovery_sources": [{"document_id": "guide"}],
                "supplemental_sources": [{"document_id": "local-draft"}],
                "roster_disposition": [],
                "scope": "Test primary sources only",
            }
            (manual / "dsa_caucus_sources.json").write_text(json.dumps(ledger))
            (raw / "one.txt").write_text(text)
            (raw / "one.html").write_bytes(html)
            (raw / "retrieval.json").write_text(
                json.dumps(
                    [
                        {
                            **source,
                            "status": "retrieved",
                            "text_file": "data/raw/dsa_caucuses/one.txt",
                            "raw_html": "data/raw/dsa_caucuses/one.html",
                            "html_sha256": digest(html),
                            "complete_text_sha256": digest(text),
                            "retrieved_at": "2026-11-01",
                            "final_url": "https://example.org",
                        }
                    ]
                )
            )
            result = prepare_sources(root)
            rows = read_rows(root / "data/analysis/dsa_caucuses/sources/complete_sources.csv")
            self.assertEqual(result["documents"], 1)
            self.assertEqual([row["document_id"] for row in rows], ["one"])
            self.assertEqual(rows[0]["publication_date"], "")
            self.assertEqual(rows[0]["caucus"], "first-caucus")
            (raw / "one.txt").write_text("Changed source")
            with self.assertRaisesRegex(ValueError, "Retrieval hash mismatch"):
                prepare_sources(root)

    def test_claims_keep_caucus_and_exact_complete_document_evidence_offsets(self):
        sources = [
            {
                "document_id": "one",
                "caucus": "first",
                "organization": "First Caucus",
                "scoped_text": "Support universal care.",
                "complete_scope_start": "100",
            },
            {
                "document_id": "two",
                "caucus": "second",
                "organization": "Second Caucus",
                "scoped_text": "Support universal care.",
                "complete_scope_start": "200",
            },
        ]
        claims = [
            {
                "claim_id": f"claim-{source['document_id']}",
                "document_id": source["document_id"],
                "analysis_eligible": "True",
                "group": "dsa",
                "source_start": 0,
                "source_end": 23,
                "evidence": "Support universal care.",
                "claim_text": "Support for universal care.",
            }
            for source in sources
        ]
        for claim in claims:
            claim["source_end"] = len(claim["evidence"])
        rows = caucus_claim_rows(claims, sources)
        self.assertEqual([row["group"] for row in rows], ["first", "second"])
        self.assertEqual([row["complete_source_start"] for row in rows], [100, 200])
        claims[0]["evidence"] = "Unsupported text."
        with self.assertRaisesRegex(ValueError, "Claim evidence mismatch"):
            caucus_claim_rows(claims, sources)

    def test_document_balanced_shares_and_all_directed_unsmoothed_ratios(self):
        rows = [
            {"group": "a", "bundle_id": "a1", "document_id": "a1"},
            {"group": "a", "bundle_id": "a1", "document_id": "a1"},
            {"group": "a", "bundle_id": "a2", "document_id": "a2"},
            {"group": "b", "bundle_id": "b1", "document_id": "b1"},
            {"group": "b", "bundle_id": "b1", "document_id": "b1"},
            {"group": "c", "bundle_id": "c1", "document_id": "c1"},
        ]
        shares, ratios = attention_tables(
            rows, ["issue", "unclustered", "issue", "other", "other", "issue"]
        )
        indexed = {(row["group"], row["topic_id"]): row for row in shares}
        self.assertEqual(indexed["a", "issue"]["attention_share"], 0.75)
        self.assertEqual(indexed["a", "unclustered"]["attention_share"], 0.25)
        for group in ("a", "b", "c"):
            self.assertAlmostEqual(
                sum(row["attention_share"] for row in shares if row["group"] == group), 1
            )
        issue = {
            (row["group"], row["baseline_groups"]): row
            for row in ratios
            if row["topic_id"] == "issue"
        }
        self.assertEqual(len(issue), 9)
        self.assertEqual(issue["a", "c"]["attention_share_ratio"], 0.75)
        self.assertAlmostEqual(issue["c", "a"]["attention_share_ratio"], 1 / 0.75)
        self.assertEqual(issue["a", "b"]["status"], "undefined_zero_denominator")
        self.assertEqual(issue["a", "b"]["attention_share_ratio"], "")
        self.assertEqual(issue["b", "a"]["attention_share_ratio"], 0)
        self.assertEqual(issue["a", "b,c"]["attention_share_ratio"], 1.5)

    def test_labels_require_current_membership_and_actual_source_support(self):
        summary = {
            "input_hashes": {"claims": "original"},
            "result_hashes": {"topic_assignments.csv": "original-membership"},
        }
        examples = [
            {"topic_id": "topic-001", "claim_id": "one"},
            {"topic_id": "topic-001", "claim_id": "two"},
        ]
        review = {
            "basis_hash": review_basis(summary),
            "topics": {
                "topic-001": {
                    "title": "Labor",
                    "summary": "Labor organizing proposals.",
                    "supporting_claim_ids": ["one", "two"],
                }
            },
        }
        self.assertEqual(validated_labels(summary, review, examples), review["topics"])
        summary["result_hashes"]["topic_assignments.csv"] = "different-membership"
        with self.assertRaisesRegex(ValueError, "do not match"):
            validated_labels(summary, review, examples)
        review["basis_hash"] = review_basis(summary)
        review["topics"]["topic-001"]["supporting_claim_ids"] = ["one", "invented"]
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            validated_labels(summary, review, examples)


if __name__ == "__main__":
    unittest.main()
