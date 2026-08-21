import unittest

from dsa_analysis.provisional_kde import (
    balanced_kde_sample_indices,
    select_dimension_elbow,
)


class ProvisionalKDETests(unittest.TestCase):
    def test_select_dimension_elbow_uses_smallest_near_maximum(self) -> None:
        rows = [
            {"dimensions": 2, "trustworthiness": 0.86},
            {"dimensions": 5, "trustworthiness": 0.941},
            {"dimensions": 10, "trustworthiness": 0.95},
            {"dimensions": 20, "trustworthiness": 0.951},
            {"dimensions": 30, "trustworthiness": 0.952},
        ]

        self.assertEqual(select_dimension_elbow(rows), 10)

    def test_balanced_kde_sample_round_robins_candidates(self) -> None:
        rows = [
            {"group": "endorsed", "race_id": "race-1", "candidate_slug": "a"},
            {"group": "endorsed", "race_id": "race-1", "candidate_slug": "a"},
            {"group": "endorsed", "race_id": "race-2", "candidate_slug": "b"},
            {"group": "endorsed", "race_id": "race-2", "candidate_slug": "b"},
            {"group": "opponent", "race_id": "race-1", "candidate_slug": "c"},
        ]

        selected = balanced_kde_sample_indices(
            rows,
            group="endorsed",
            limit=2,
            seed=1729,
        )

        self.assertEqual(len(selected), 2)
        self.assertEqual(
            {rows[index]["candidate_slug"] for index in selected},
            {"a", "b"},
        )
