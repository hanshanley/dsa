from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dsa_analysis.narrative_analysis import (
    build_embedding_cache_metadata,
    build_knn_edges,
    cosine_dp_means,
    evaluate_umap_dimension_sweep,
    estimate_kde_density,
    fit_umap_projection,
    hot_cold_characterization,
    load_narrative_analysis_config,
    narrative_lift,
    resolve_selected_cosine_distance,
    resolve_selected_cosine_threshold,
    sample_threshold_pairs,
    select_cosine_threshold,
    select_pair_annotations,
    umap_trustworthiness,
    validate_embedding_cache_metadata,
    validate_pair_annotations,
)


class NarrativeAnalysisTests(unittest.TestCase):
    def test_load_config_exposes_deterministic_seed(self):
        config = load_narrative_analysis_config()
        self.assertEqual(config["seed"], 1729)
        self.assertEqual(config["embedding_cache"]["normalization"], "l2")
        self.assertEqual(config["threshold_sampling"]["thresholds"][0], 0.55)
        self.assertEqual(config["knn"]["k"], 64)
        self.assertEqual(config["leiden"]["objective"], "rb_configuration")
        self.assertEqual(config["umap"]["dimension_sweep"], [2, 5, 10, 20, 30])

    def test_embedding_cache_metadata_round_trip(self):
        texts = ["housing justice", "labor power"]
        embeddings = [[3.0, 4.0], [5.0, 12.0]]
        metadata = build_embedding_cache_metadata(
            texts,
            embeddings,
            model_name="mini-test-model",
            identifiers=["a", "b"],
        )
        self.assertTrue(metadata["normalized"])
        self.assertEqual(metadata["vector_count"], 2)
        validate_embedding_cache_metadata(
            metadata,
            texts,
            embeddings,
            identifiers=["a", "b"],
        )

    def test_sample_threshold_pairs_balances_strata(self):
        pairs = [
            {"pair_id": "p1", "similarity": 0.49, "race_id": "r1", "candidate_id": "c1"},
            {"pair_id": "p2", "similarity": 0.51, "race_id": "r1", "candidate_id": "c2"},
            {"pair_id": "p3", "similarity": 0.5, "race_id": "r2", "candidate_id": "c3"},
            {"pair_id": "p4", "similarity": 0.48, "race_id": "r2", "candidate_id": "c4"},
        ]
        sampled = sample_threshold_pairs(
            pairs,
            thresholds=[0.5],
            band_width=0.02,
            max_per_threshold=2,
            seed=7,
        )
        self.assertEqual(len(sampled["pairs"]), 2)
        self.assertEqual({row["race_id"] for row in sampled["pairs"]}, {"r1", "r2"})
        self.assertEqual(sampled["provenance"]["seed"], 7)

    def test_select_cosine_threshold_uses_balanced_accuracy(self):
        result = select_cosine_threshold(
            [
                {"pair_id": "p1", "similarity": 0.82, "selected_label": "match"},
                {"pair_id": "p2", "similarity": 0.74, "selected_label": "match"},
                {"pair_id": "p3", "similarity": 0.69, "selected_label": "match"},
                {"pair_id": "p4", "similarity": 0.66, "selected_label": "mismatch"},
                {"pair_id": "p5", "similarity": 0.61, "selected_label": "mismatch"},
                {"pair_id": "p6", "similarity": 0.56, "selected_label": "mismatch"},
                {"pair_id": "p7", "similarity": 0.72, "selected_label": "uncertain"},
            ],
            thresholds=[0.55, 0.6, 0.65, 0.68, 0.7, 0.75, 0.8],
        )
        self.assertEqual(result["selected_threshold"], 0.68)
        self.assertEqual(result["provenance"]["excluded_rows"], 1)

    def test_validate_pair_annotations_rejects_duplicates(self):
        with self.assertRaisesRegex(ValueError, "duplicate annotation"):
            validate_pair_annotations(
                [
                    {"pair_id": "p1", "annotator_id": "a1", "label": "match"},
                    {"pair_id": "p1", "annotator_id": "a1", "label": "mismatch"},
                ]
            )

    def test_select_pair_annotations_separates_majority_from_review(self):
        selected = select_pair_annotations(
            [
                {"pair_id": "p1", "annotator_id": "a1", "label": "match"},
                {"pair_id": "p1", "annotator_id": "a2", "label": "match"},
                {"pair_id": "p2", "annotator_id": "a1", "label": "match"},
                {"pair_id": "p2", "annotator_id": "a2", "label": "mismatch"},
            ]
        )
        by_pair = {row["pair_id"]: row for row in selected["pairs"]}
        self.assertEqual(by_pair["p1"]["status"], "selected")
        self.assertEqual(by_pair["p1"]["selected_label"], "match")
        self.assertEqual(by_pair["p2"]["status"], "needs_review")

    def test_build_knn_edges_constructs_mutual_links(self):
        result = build_knn_edges(
            ["a", "b", "c"],
            [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]],
            k=1,
            min_similarity=0.1,
            mutual=True,
        )
        self.assertEqual(
            result["edges"],
            [{"source": "a", "target": "b", "similarity": 0.993883734674}],
        )

    def test_build_knn_edges_uses_selected_threshold_when_requested(self):
        result = build_knn_edges(
            ["a", "b", "c"],
            [[1.0, 0.0], [0.96, 0.04], [0.0, 1.0]],
            k=2,
            config={
                "threshold_selection": {"selected_cosine_threshold": 0.95},
            },
        )
        self.assertEqual(
            result["provenance"]["threshold_source"],
            "config.threshold_selection.selected_cosine_threshold",
        )
        self.assertEqual(len(result["edges"]), 1)

    def test_run_leiden_clustering_raises_explicit_dependency_error(self):
        with patch(
            "dsa_analysis.narrative_analysis.importlib.import_module",
            side_effect=ImportError("missing"),
        ):
            from dsa_analysis.narrative_analysis import run_leiden_clustering

            with self.assertRaisesRegex(RuntimeError, "python-igraph"):
                run_leiden_clustering(["a"], [])

    def test_narrative_lift_uses_candidate_and_race_balancing(self):
        result = narrative_lift(
            [
                {
                    "group": "endorsed",
                    "race_id": "r1",
                    "candidate_id": "c1",
                    "narratives": ["housing"],
                },
                {
                    "group": "endorsed",
                    "race_id": "r1",
                    "candidate_id": "c1",
                    "narratives": ["housing"],
                },
                {
                    "group": "endorsed",
                    "race_id": "r1",
                    "candidate_id": "c2",
                    "narratives": ["labor"],
                },
                {
                    "group": "opponent",
                    "race_id": "r1",
                    "candidate_id": "c3",
                    "narratives": ["housing"],
                },
                {
                    "group": "opponent",
                    "race_id": "r2",
                    "candidate_id": "c4",
                    "narratives": ["housing"],
                },
            ],
            narrative_key="narratives",
            positive_group="endorsed",
            negative_group="opponent",
        )
        by_narrative = {row["narrative"]: row for row in result["rows"]}
        self.assertAlmostEqual(by_narrative["housing"]["positive_share"], 0.5)
        self.assertAlmostEqual(by_narrative["housing"]["negative_share"], 1.0)
        self.assertEqual(by_narrative["housing"]["favored_group"], "opponent")

    def test_umap_helpers_raise_explicit_dependency_errors(self):
        with patch(
            "dsa_analysis.narrative_analysis.importlib.import_module",
            side_effect=ImportError("missing"),
        ):
            with self.assertRaisesRegex(RuntimeError, "umap-learn"):
                fit_umap_projection([[1.0, 0.0], [0.0, 1.0]])
            with self.assertRaisesRegex(RuntimeError, "scikit-learn"):
                umap_trustworthiness(
                    [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]],
                    [[0.0], [0.5], [1.0]],
                )
            with self.assertRaisesRegex(RuntimeError, "scipy"):
                estimate_kde_density([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])

    def test_umap_trustworthiness_clamps_neighbors_and_handles_tiny_samples(self):
        calls = []

        def fake_trustworthiness(original, projected, *, n_neighbors):
            calls.append(n_neighbors)
            return 0.75

        with patch(
            "dsa_analysis.narrative_analysis._optional_dependency",
            return_value=SimpleNamespace(trustworthiness=fake_trustworthiness),
        ):
            result = umap_trustworthiness(
                [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]],
                [[0.0, 0.0], [0.1, 0.0], [1.0, 1.0], [0.9, 1.0]],
                n_neighbors=5,
            )
        self.assertEqual(calls, [1])
        self.assertEqual(result["provenance"]["effective_n_neighbors"], 1)
        tiny = umap_trustworthiness([[1.0, 0.0], [0.0, 1.0]], [[0.0], [1.0]])
        self.assertEqual(tiny["trustworthiness"], 1.0)
        self.assertTrue(tiny["provenance"]["degenerate_sample"])

    def test_umap_dimension_sweep_uses_requested_dimensions(self):
        with (
            patch(
                "dsa_analysis.narrative_analysis.fit_umap_projection",
                side_effect=lambda embeddings, **kwargs: {
                    "coordinates": [[float(kwargs["n_components"])]]
                },
            ),
            patch(
                "dsa_analysis.narrative_analysis.umap_trustworthiness",
                side_effect=lambda original, projected, **kwargs: {
                    "trustworthiness": projected[0][0] / 100
                },
            ),
        ):
            result = evaluate_umap_dimension_sweep(
                [[1.0, 0.0], [0.0, 1.0]],
                dimensions=[2, 5, 10],
            )
        self.assertEqual([row["dimensions"] for row in result["rows"]], [10, 5, 2])

    def test_hot_cold_characterization_combines_tfidf_and_npmi(self):
        result = hot_cold_characterization(
            [
                {"group": "hot", "tokens": ["rent", "rent", "tenant"]},
                {"group": "hot", "tokens": ["rent", "housing"]},
                {"group": "cold", "tokens": ["market", "market", "growth"]},
                {"group": "cold", "tokens": ["market", "business"]},
            ],
            positive_group="hot",
            negative_group="cold",
        )
        by_term = {row["term"]: row for row in result["rows"]}
        self.assertEqual(by_term["rent"]["favored_group"], "hot")
        self.assertEqual(by_term["market"]["favored_group"], "cold")
        self.assertTrue(result["stable_hot_terms"])
        self.assertTrue(result["stable_cold_terms"])

    def test_hot_cold_requires_both_groups(self):
        with self.assertRaisesRegex(ValueError, "both comparison groups"):
            hot_cold_characterization(
                [{"group": "hot", "tokens": ["rent", "tenant"]}],
                positive_group="hot",
                negative_group="cold",
            )

    def test_kde_validation_raises_clear_errors_before_scipy(self):
        with self.assertRaisesRegex(ValueError, "at least 3 points"):
            estimate_kde_density([[0.0, 0.0], [1.0, 1.0]])
        with self.assertRaisesRegex(ValueError, "non-collinear variation"):
            estimate_kde_density([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]])

    def test_cosine_dp_means_splits_two_clusters(self):
        result = cosine_dp_means(
            ["a", "b", "c", "d"],
            [[1.0, 0.0], [0.95, 0.05], [0.0, 1.0], [0.05, 0.95]],
            max_distance=0.1,
        )
        clusters = {row["identifier"]: row["cluster_id"] for row in result["assignments"]}
        self.assertEqual(clusters["a"], clusters["b"])
        self.assertEqual(clusters["c"], clusters["d"])
        self.assertNotEqual(clusters["a"], clusters["c"])
        self.assertEqual(result["provenance"]["cluster_count"], 2)

    def test_selected_threshold_helpers_feed_dp_means(self):
        config = {"threshold_selection": {"selected_cosine_threshold": 0.9}}
        self.assertAlmostEqual(resolve_selected_cosine_threshold(config), 0.9)
        self.assertAlmostEqual(resolve_selected_cosine_distance(config), 0.1)
        result = cosine_dp_means(
            ["a", "b"],
            [[1.0, 0.0], [0.9, 0.1]],
            config=config,
        )
        self.assertEqual(
            result["provenance"]["threshold_source"],
            "config.threshold_selection.selected_cosine_threshold",
        )

    def test_selected_threshold_rejects_one_point_zero(self):
        with self.assertRaisesRegex(ValueError, r"interval \(0, 1\)"):
            resolve_selected_cosine_threshold(
                {"threshold_selection": {"selected_cosine_threshold": 1.0}}
            )
        with self.assertRaisesRegex(ValueError, r"interval \(0, 1\)"):
            cosine_dp_means(
                ["a", "b"],
                [[1.0, 0.0], [0.9, 0.1]],
                config={"threshold_selection": {"selected_cosine_threshold": 1.0}},
            )


if __name__ == "__main__":
    unittest.main()
