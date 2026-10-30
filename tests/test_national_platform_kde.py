import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from dsa_analysis.national_platform_kde import (
    analyze_view,
    balance_weights,
    document_chronology,
    embedding_key,
    encode,
    fit_indices,
    pairwise_scores,
    region_summaries,
    write_report,
)
from dsa_analysis.national_platforms import GROUPS, SUPPORTED_GROUPS, write_json, write_rows


def rows():
    return [
        {
            "segment_id": f"{group}-{index}",
            "document_id": f"{group}-{index % 2}",
            "bundle_id": f"{group}-{index % 2}",
            "group": group,
            "title": "National program",
            "document_type": "program",
            "publication_date": "2024" if index % 2 == 0 else "2026-09",
            "source_url": "https://example.test",
            "locator": f"paragraph {index}",
            "text": f"{group} housing healthcare energy workers government reform number {index}",
        }
        for group, count in zip(GROUPS, (20, 16, 10), strict=True)
        for index in range(count)
    ]


class NationalKDETests(unittest.TestCase):
    def test_four_party_balancing_and_all_six_named_contrasts(self):
        corpus = rows()
        corpus += [
            {**row, "group": "libertarian", "bundle_id": f"libertarian-{index % 2}"}
            for index, row in enumerate(rows()[:12])
        ]
        selected = fit_indices(corpus, groups=SUPPORTED_GROUPS)
        self.assertEqual(set(selected), set(SUPPORTED_GROUPS))
        self.assertEqual({len(values) for values in selected.values()}, {10})
        scores = pairwise_scores(
            {group: np.array([-float(i)]) for i, group in enumerate(SUPPORTED_GROUPS)},
            groups=SUPPORTED_GROUPS,
        )
        self.assertEqual(len(scores), 6)
        self.assertEqual(scores["democratic_vs_libertarian"][0], 3)
        self.assertEqual(scores["dsa_vs_libertarian"][0], 1)
        with self.assertRaisesRegex(ValueError, "covering all rows"):
            fit_indices(corpus)

    def test_early_cutoff_report_omits_unavailable_policy_examples(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources.csv"
            report = root / "report.md"
            write_rows(sources, [], fields=["document_id", "scoped_text"])
            results = {view: {"status": "complete"} for view in ("expanded", "strict")}
            write_report(results, [], "2020-12-31", report, sources)
            self.assertNotIn("## Reviewed policy examples", report.read_text())
            self.assertNotIn("Evidence: `democratic-2024`", report.read_text())

    def test_narrow_cli_does_not_invoke_candidate_pipeline(self):
        from dsa_analysis.cli import main

        with (
            patch("sys.argv", ["dsa-analysis", "national-platform-analysis", "--fetch-only"]),
            patch(
                "dsa_analysis.national_platform_kde.run_national_platform_analysis",
                return_value={"status": "sources_collected"},
            ) as run,
            patch("dsa_analysis.cli.build_race_registry", side_effect=AssertionError),
            patch("dsa_analysis.cli.analyze_text", side_effect=AssertionError),
        ):
            main()
        self.assertTrue(run.call_args.kwargs["fetch_only"])

    def test_balancing_covers_all_groups_and_documents_deterministically(self):
        corpus = rows()
        selected = fit_indices(corpus)
        self.assertEqual(selected, fit_indices(corpus))
        self.assertEqual({len(values) for values in selected.values()}, {10})
        for group, indices in selected.items():
            self.assertEqual({corpus[i]["group"] for i in indices}, {group})
            self.assertEqual(len({corpus[i]["bundle_id"] for i in indices}), 2)

    def test_bundle_weights_not_statement_counts_determine_mass(self):
        corpus = [{"bundle_id": "period-a"}] * 8 + [{"bundle_id": "program-b"}] * 2
        weights = balance_weights(corpus, list(range(10)))
        self.assertAlmostEqual(weights[:8].sum(), weights[8:].sum())

    def test_pairwise_scores_use_named_first_minus_second_direction(self):
        scores = pairwise_scores(
            {
                "democratic": np.array([-1.0]),
                "republican": np.array([-3.0]),
                "dsa": np.array([-2.0]),
            }
        )
        self.assertEqual(scores["democratic_vs_republican"][0], 2)
        self.assertEqual(scores["democratic_vs_dsa"][0], 1)
        self.assertEqual(scores["republican_vs_dsa"][0], -1)

    def test_small_group_returns_explicit_insufficient_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            corpus = [row for row in rows() if row["group"] != "dsa"]
            result = analyze_view(
                corpus,
                np.ones((len(corpus), 3)),
                Path(temporary),
            )
            self.assertEqual(result["status"], "insufficient_evidence")
            self.assertIn("ten eligible passages", result["reason"])
            self.assertNotIn("groups", result)
            expanded = analyze_view(
                corpus,
                np.ones((len(corpus), 3)),
                Path(temporary),
                groups=SUPPORTED_GROUPS,
            )
            self.assertEqual(expanded["groups"], list(SUPPORTED_GROUPS))

    def test_embedding_key_changes_with_text_order_or_tokenization(self):
        corpus = rows()
        key = embedding_key(corpus)
        self.assertNotEqual(key, embedding_key(list(reversed(corpus))))
        self.assertNotEqual(key, embedding_key(corpus, max_length=128))
        self.assertNotEqual(key, embedding_key([{**corpus[0], "text": "new"}, *corpus[1:]]))

    def test_valid_cache_avoids_model_loading(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            corpus = rows()
            np.save(directory / "embeddings.npy", np.ones((len(corpus), 768)) / np.sqrt(768))
            write_json(directory / "embedding_manifest.json", embedding_key(corpus))
            with patch("sentence_transformers.SentenceTransformer", side_effect=AssertionError):
                embeddings, cached = encode(corpus, directory)
            self.assertTrue(cached)
            self.assertEqual(embeddings.shape[0], len(corpus))

    def test_invalid_embedding_shapes_or_values_force_offline_reencoding(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            corpus = rows()
            expected = np.ones((len(corpus), 768)) / np.sqrt(768)
            for invalid in (
                np.ones((len(corpus), 2)),
                np.full((len(corpus), 768), np.nan),
            ):
                np.save(directory / "embeddings.npy", invalid)
                write_json(directory / "embedding_manifest.json", embedding_key(corpus))
                with patch("sentence_transformers.SentenceTransformer") as model:
                    model.return_value.encode.return_value = expected
                    embeddings, cached = encode(corpus, directory)
                    self.assertTrue(model.call_args.kwargs["local_files_only"])
                self.assertFalse(cached)
                np.testing.assert_allclose(embeddings, expected)

    def test_shared_region_requires_passage_support_from_both_organizations(self):
        corpus = rows()
        coordinates = np.random.default_rng(1).normal(size=(len(corpus), 2))
        densities = {group: np.zeros(len(corpus)) for group in GROUPS}
        scores = pairwise_scores(densities)
        scores["democratic_vs_dsa"] = np.array(
            [100.0 if row["group"] == "dsa" else 0.0 for row in corpus]
        )
        with patch("dsa_analysis.national_platform_kde.HDBSCAN") as cluster:
            cluster.return_value.fit_predict.side_effect = lambda points: np.zeros(
                len(points),
                dtype=int,
            )
            regions, _ = region_summaries(corpus, coordinates, densities, scores)
        self.assertFalse(
            any(
                row["pair"] == "democratic_vs_dsa" and row["zone"] == "shared_language"
                for row in regions
            )
        )

    def test_document_chronology_uses_original_embeddings_without_interpolation(self):
        corpus = rows()
        embeddings = np.array(
            [[1.0, 0.0] if row["publication_date"] == "2024" else [0.0, 1.0] for row in corpus]
        )
        documents = document_chronology(corpus, embeddings)
        self.assertEqual(len(documents), 6)
        for group in GROUPS:
            selected = [row for row in documents if row["group"] == group]
            self.assertEqual(selected[0]["cosine_distance_from_previous"], "")
            self.assertEqual(selected[1]["cosine_distance_from_previous"], 1.0)
