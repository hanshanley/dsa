import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

from dsa_analysis.national_claim_topic_time import temporal_tables
from dsa_analysis.national_claim_topics import (
    NOISE,
    audit,
    bundle_sensitivity,
    canonical,
    claim_weights,
    config,
    contrasts,
    current_labels,
    distributions,
    evidence_packets,
    fit_topics,
    label_topics,
    load_inputs,
    prepare,
    render,
    stable_topics,
    topic_evidence,
    validate_label,
)
from dsa_analysis.national_platform_kde import embedding_key
from dsa_analysis.national_platforms import GROUPS, SUPPORTED_GROUPS, digest, write_json, write_rows
from tests.test_national_claim_corpus import response
from tests.test_national_claims import coverage, sources


def row(identifier, group="dsa", bundle="one", strict=True):
    return {
        "claim_id": identifier,
        "group": group,
        "bundle_id": bundle,
        "strict": strict,
        "document_id": bundle,
        "text": "Support for universal public health care.",
    }


class ClaimTopicsTests(unittest.TestCase):
    def test_temporal_dates_gaps_weights_and_fixed_comparison_baselines(self):
        definitions = [
            ("d00", "democratic", "2000", "", True, "health"),
            ("d04", "democratic", "2004", "", True, "labor"),
            ("d08", "democratic", "2008", "", True, "health"),
            ("r00", "republican", "2000", "", True, "labor"),
            ("r08", "republican", "2008", "", True, "health"),
            ("s03", "dsa", "2004", "2003-11", False, "health"),
            ("s08", "dsa", "2008", "", True, "labor"),
            ("unknown", "dsa", "", "", False, "labor"),
        ]
        rows = [
            row(identifier, group, identifier, strict)
            for (identifier, group, _, _, strict, _) in definitions
        ]
        sources = [
            {
                "document_id": identifier,
                "publication_date": publication,
                "adoption_date": adoption,
                "document_type": "platform" if strict else "statement",
            }
            for identifier, _, publication, adoption, strict, _ in definitions
        ]
        tables = temporal_tables(
            rows, [definition[-1] for definition in definitions], sources, GROUPS, 0.0001
        )
        shares = {
            (r["period_start"], r["view"], r["group"], r["topic_id"]): r
            for r in tables["temporal_shares.csv"]
        }
        self.assertEqual(shares[2000, "expanded", "democratic", "labor"]["share"], 0)
        self.assertEqual(shares[2004, "expanded", "republican", "labor"]["share"], "")
        self.assertFalse(shares[2004, "expanded", "republican", "labor"]["available"])
        self.assertEqual(shares[2000, "expanded", "dsa", "health"]["share"], 1)
        self.assertEqual(shares[2000, "strict", "dsa", "health"]["share"], "")
        self.assertEqual(tables["temporal_exclusions.csv"][0]["document_id"], "unknown")
        dated = next(r for r in tables["temporal_document_dates.csv"] if r["document_id"] == "s03")
        self.assertEqual(dated["date_field"], "adoption_date")
        self.assertEqual(dated["date_value"], "2003-11")
        self.assertEqual(dated["period_start"], 2000)
        rest = [r for r in tables["temporal_contrasts.csv"] if r["comparison"] == "vs_rest"]
        self.assertTrue(rest)
        self.assertFalse(any(r["period_start"] == 2004 for r in rest))
        self.assertFalse(any(r["view"] == "strict" and r["period_start"] == 2000 for r in rest))
        self.assertTrue(all(len(r["baseline_groups"].split(",")) == 2 for r in rest))
        changes = tables["temporal_changes.csv"]
        self.assertFalse(any(r["group"] == "republican" for r in changes))
        change = next(
            r
            for r in changes
            if (r["period"], r["view"], r["group"], r["topic_id"])
            == ("2004-2007", "expanded", "democratic", "health")
        )
        self.assertEqual(change["percentage_point_change"], -100)

    def test_equal_bundle_mass_and_strict_subset_share_one_taxonomy(self):
        rows = [
            row("a"),
            row("b"),
            row("c", bundle="two", strict=False),
            row("d", "democratic"),
        ]
        weights = claim_weights(rows)
        np.testing.assert_allclose(weights, [0.25, 0.25, 0.5, 1])
        shares = distributions(rows, ["health", "health", "labor", NOISE], GROUPS)
        lookup = {(r["view"], r["group"], r["topic_id"]): r for r in shares}
        self.assertEqual(lookup["expanded", "dsa", "health"]["share"], 0.5)
        self.assertEqual(lookup["strict", "dsa", "health"]["share"], 1)
        self.assertEqual(lookup["strict", "dsa", "labor"]["share"], 0)
        self.assertEqual(lookup["expanded", "democratic", NOISE]["share"], 1)
        self.assertFalse(lookup["expanded", "republican", "health"]["available"])
        self.assertEqual(lookup["expanded", "republican", "health"]["share"], "")
        duplicated = [*rows[:2], row("extra"), *rows[2:]]
        other = distributions(duplicated, ["health"] * 3 + ["labor", NOISE], GROUPS)
        self.assertEqual(
            [(r["view"], r["group"], r["topic_id"], r["share"]) for r in shares],
            [(r["view"], r["group"], r["topic_id"], r["share"]) for r in other],
        )

    def test_ratios_use_equal_groups_not_pooled_counts_and_keep_fragile_rankings(self):
        rows = [row("a", "democratic")] * 100
        rows += [row("b", "republican"), row("c", "dsa"), row("d", "dsa")]
        assignments = ["health"] * 100 + ["labor", "health", "labor"]
        shares = distributions(rows, assignments, GROUPS)
        ratios = contrasts(shares, GROUPS, 0.0001)
        first = next(
            r
            for r in ratios
            if (r["view"], r["comparison"], r["group"], r["topic_id"])
            == ("expanded", "vs_rest", "democratic", "health")
        )
        self.assertEqual(first["baseline_share"], 0.25)
        self.assertAlmostEqual(first["log2_ratio"], np.log2(1.0001 / 0.2501))
        self.assertIn("low_bundle_support", first["warnings"])
        self.assertEqual(first["rank"], 1)
        self.assertTrue(any("zero_share" in r["warnings"] for r in ratios))
        reverse = contrasts(shares, tuple(reversed(GROUPS)), 0.0001)
        a = next(
            r
            for r in ratios
            if (r["view"], r["comparison"], r["group"], r["baseline_groups"], r["topic_id"])
            == ("expanded", "pairwise", "democratic", "dsa", "health")
        )
        b = next(
            r
            for r in reverse
            if (r["view"], r["comparison"], r["group"], r["baseline_groups"], r["topic_id"])
            == ("expanded", "pairwise", "dsa", "democratic", "health")
        )
        self.assertAlmostEqual(a["log2_ratio"], -b["log2_ratio"])

    def test_bundle_sensitivity_preserves_topics_that_disappear_when_bundle_removed(self):
        rows = [
            row("a", "democratic", "a"),
            row("b", "democratic", "b"),
            row("c", "republican", "a"),
            row("d", "republican", "b"),
            row("e", "dsa", "a"),
            row("f", "dsa", "b"),
        ]
        assignments = ["health", "labor", "labor", "labor", "labor", "labor"]
        ratios = contrasts(distributions(rows, assignments, GROUPS), GROUPS, 0.0001)
        bundle_sensitivity(rows, assignments, GROUPS, ratios, 0.0001)
        target = next(
            r
            for r in ratios
            if (r["view"], r["comparison"], r["group"], r["topic_id"])
            == ("expanded", "vs_rest", "democratic", "health")
        )
        self.assertEqual(target["leave_one_bundle_out_min"], 0)
        self.assertIn("smoothing_sensitive", target["warnings"])

    def test_four_party_shares_and_separate_ids(self):
        rows = [row(group, group, group) for group in SUPPORTED_GROUPS]
        shares = distributions(rows, ["health"] * 4, SUPPORTED_GROUPS)
        self.assertEqual(len(shares), 16)
        ratios = contrasts(shares, SUPPORTED_GROUPS, 0.0001)
        self.assertEqual(
            len([r for r in ratios if r["view"] == "expanded" and r["comparison"] == "pairwise"]),
            12,
        )
        self.assertTrue(all(r["log2_ratio"] == 0 for r in ratios))
        self.assertEqual(
            stable_topics(np.array([9, 2, -1]), [row("a"), row("b"), row("c")]),
            ["topic-001", "topic-002", NOISE],
        )

    def test_small_and_degenerate_inputs_are_explicit_noise(self):
        settings = config()
        topics, _, summary, _, _ = fit_topics([row("a")], np.ones((1, 3)), settings)
        self.assertEqual(topics, [NOISE])
        self.assertEqual(summary["status"], "degenerate_input")
        rows = [row(str(i)) for i in range(8)]
        topics, _, summary, _, _ = fit_topics(
            rows, np.random.default_rng(1).normal(size=(8, 3)), settings
        )
        self.assertEqual(topics, [NOISE] * 8)
        self.assertEqual(summary["status"], "insufficient_evidence")

    def test_keywords_and_representatives_keep_actual_claim_ids_and_bundle_limits(self):
        rows = [row(str(i), bundle=str(i // 5)) for i in range(20)]
        vectors = np.random.default_rng(1).normal(size=(20, 8))
        terms, examples = topic_evidence(rows, vectors, ["health"] * 20, config())
        self.assertTrue(terms)
        self.assertTrue(all(item["term"] != "support" for item in terms))
        self.assertEqual({e["claim_id"] for e in examples} <= {r["claim_id"] for r in rows}, True)
        counts = {}
        for example in examples:
            counts[example["bundle_id"]] = counts.get(example["bundle_id"], 0) + 1
        self.assertTrue(all(value <= 2 for value in counts.values()))

    def test_labels_reject_invented_evidence_and_offline_replay_does_not_infer(self):
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary)
            directory = corpus / "topics"
            directory.mkdir()
            write_json(directory / "fit_manifest.json", {"basis": {"config": config()}})
            write_rows(
                directory / "representatives.csv",
                [
                    {"topic_id": "health", **row("a"), "claim_text": "Support public care."},
                    {"topic_id": "health", **row("b"), "claim_text": "Support universal care."},
                ],
            )
            write_rows(directory / "keywords.csv", [{"topic_id": "health", "term": "public care"}])
            value = {
                "title": "Health care access",
                "summary": "The claims concern public care.",
                "caveat": "",
                "supporting_claim_ids": ["a", "b"],
            }
            packet = {"claims": [{"claim_id": "a"}, {"claim_id": "b"}]}
            with self.assertRaisesRegex(ValueError, "unsupported"):
                validate_label(json.dumps({**value, "supporting_claim_ids": ["fake"]}), packet)
            replies = [{"text": "{}"}, {"text": json.dumps(value)}]
            with patch("dsa_analysis.national_claim_topics.subprocess.check_output") as check:
                check.return_value = ""
                result = label_topics(
                    corpus, extractor=lambda *_: replies.pop(0), token_count=lambda _: 10
                )
            self.assertEqual(result["status"], "complete")
            result = label_topics(
                corpus,
                extractor=lambda *_: self.fail("offline cache must not infer"),
                token_count=lambda _: 10,
            )
            self.assertEqual(result["labeled"], 1)
            self.assertEqual(current_labels(directory)["health"]["title"], value["title"])
            reviewed = {
                "fit_manifest_sha256": digest((directory / "fit_manifest.json").read_bytes()),
                "topics": [
                    {
                        "topic_id": "health",
                        "source_record_sha256": digest(
                            (directory / "labels/health.json").read_bytes()
                        ),
                        "evidence_packet_sha256": digest(canonical(evidence_packets(directory)[0])),
                        "label_origin": "assistant_source_bound_revision",
                        "label": {**value, "title": "Public healthcare access"},
                    }
                ],
            }
            write_json(directory / "label_review.json", reviewed)
            resolved = current_labels(directory)["health"]
            self.assertEqual(resolved["title"], "Public healthcare access")
            self.assertEqual(resolved["review_status"], "evidence_reviewed")
            reviewed["topics"][0]["label_origin"] = "local_gemma"
            write_json(directory / "label_review.json", reviewed)
            with self.assertRaisesRegex(ValueError, "attributed"):
                current_labels(directory)
            reviewed["topics"][0]["label_origin"] = "assistant_source_bound_revision"
            reviewed["topics"][0]["label"]["supporting_claim_ids"] = ["invented"]
            write_json(directory / "label_review.json", reviewed)
            with self.assertRaisesRegex(ValueError, "unsupported"):
                current_labels(directory)
            reviewed["topics"][0]["source_record_sha256"] = "stale"
            write_json(directory / "label_review.json", reviewed)
            self.assertEqual(current_labels(directory)["health"]["review_status"], "unreviewed")
            write_json(
                directory / "fit_manifest.json", {"basis": {"config": {**config(), "seed": 2}}}
            )
            self.assertEqual(current_labels(directory), {})

    def test_input_gate_refuses_running_extraction_before_loading_any_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            write_json(path / "extraction_summary.json", {"status": "running"})
            with self.assertRaisesRegex(ValueError, "completed"):
                load_inputs(path, GROUPS)

    def test_prepare_cache_provenance_render_and_complete_archive(self):
        from dsa_analysis.national_claim_analysis import analysis_rows
        from dsa_analysis.national_claim_corpus import build_blocks, validate_response

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            corpus = root / "data/full"
            corpus.mkdir(parents=True)
            source_rows = sources()
            claims = [
                validate_response(response(), block)[0][0]
                for block in build_blocks(source_rows, coverage(source_rows))
            ]
            write_rows(corpus / "claims.csv", claims)
            write_rows(corpus / "complete_sources.csv", source_rows)
            write_json(corpus / "extraction_summary.json", {"status": "complete"})
            write_json(corpus / "analysis_summary.json", {"baseline_modified": False})
            rows = analysis_rows(claims, source_rows)
            vectors = np.random.default_rng(1).normal(size=(len(rows), 768))
            vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
            np.save(corpus / "embeddings.npy", vectors)
            write_json(corpus / "embedding_manifest.json", embedding_key(rows))
            first = prepare(corpus)
            self.assertFalse(first["cache_reused"])
            with patch(
                "dsa_analysis.national_claim_topics.fit_topics",
                side_effect=AssertionError("cached preparation must not refit"),
            ):
                self.assertTrue(prepare(corpus)["cache_reused"])
            figure_directory = root / "figures/national_claims/full/topics/strict"
            figure_directory.mkdir(parents=True)
            stale_figures = [
                figure_directory / "topic_distribution_9.png",
                figure_directory / "time_trends_9.svg",
            ]
            for path in stale_figures:
                path.write_text("stale previous taxonomy")
            report = root / "report/national_claim_analysis.md"
            report.parent.mkdir()
            report.write_text(
                "# Analysis\n\n[Complete download](../data/full/claim_documents.zip)\n"
            )
            write_json(corpus / "topics/topic_labels.json", [{"topic_id": "obsolete"}])
            with patch("dsa_analysis.national_claim_topics.ROOT", root):
                summary = render(corpus)
                self.assertEqual(audit(corpus)["status"], "complete")
            self.assertTrue(all(not path.exists() for path in stale_figures))
            self.assertEqual(json.loads((corpus / "topics/topic_labels.json").read_text()), [])
            self.assertEqual(summary["labeling_status"], "complete")
            self.assertIn(
                "learned_topics", json.loads((corpus / "analysis_summary.json").read_text())
            )
            self.assertTrue(
                (
                    root / "figures/national_claims/full/topics/strict/topic_distribution.png"
                ).exists()
            )
            with zipfile.ZipFile(corpus / "claim_documents.zip") as archive:
                self.assertEqual(archive.read("claims.csv"), (corpus / "claims.csv").read_bytes())
                self.assertEqual(
                    archive.read("complete_sources.csv"),
                    (corpus / "complete_sources.csv").read_bytes(),
                )
                self.assertIn("topics/assignments.csv", archive.namelist())
                figure = "figures/topics/strict/topic_distribution.png"
                self.assertEqual(
                    archive.read(figure),
                    (figure_directory / "topic_distribution.png").read_bytes(),
                )
                portable_report = archive.read("report.md").decode()
                self.assertIn("Complete download (this extracted bundle)", portable_report)
                self.assertNotIn("](claim_documents.zip)", portable_report)
                self.assertIn("[All shares](topics/shares.csv)", portable_report)
                self.assertIn("figures/topics/strict/topic_distribution.png", portable_report)
            write_rows(corpus / "claims.csv", list(reversed(claims)))
            with (
                patch(
                    "dsa_analysis.national_claim_topics.fit_topics",
                    side_effect=AssertionError("changed claim ordering must refit"),
                ),
                self.assertRaisesRegex(AssertionError, "must refit"),
            ):
                prepare(corpus)
            vectors[0] *= 2
            np.save(corpus / "embeddings.npy", vectors)
            with self.assertRaisesRegex(ValueError, "provenance"):
                load_inputs(corpus, GROUPS)

    def test_failed_labels_remain_incomplete_and_packet_is_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary)
            directory = corpus / "topics"
            directory.mkdir()
            settings = {**config(), "max_prompt_tokens": 2}
            write_json(directory / "fit_manifest.json", {"basis": {"config": settings}})
            write_rows(
                directory / "representatives.csv",
                [
                    {"topic_id": "health", **row(str(i)), "claim_text": f"Health claim {i}."}
                    for i in range(10)
                ],
            )
            write_rows(directory / "keywords.csv", [{"topic_id": "health", "term": "care"}])
            observed = []

            def generator(prompt, *_):
                packet = json.loads(prompt.split("EVIDENCE PACKET:\n")[1])
                observed.append(len(packet["claims"]))
                return {"text": "not valid json"}

            result = label_topics(
                corpus,
                extractor=generator,
                token_count=lambda text: len(
                    json.loads(text.split("EVIDENCE PACKET:\n")[1])["claims"]
                ),
            )
            self.assertEqual(result["status"], "incomplete")
            self.assertEqual(observed, [2, 2])
            self.assertEqual(current_labels(directory), {})


if __name__ == "__main__":
    unittest.main()
