import unittest
import csv
import tempfile
from pathlib import Path

from dsa_analysis.provisional_kde import (
    balanced_kde_sample_indices,
    load_eligible_segments,
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

    def test_load_segments_retains_one_duplicate_per_candidate_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            segments_path = root / "segments.csv"
            metadata_path = root / "metadata.csv"
            fields = [
                "analysis_segment_id",
                "document_id",
                "candidate_slug",
                "candidate_name",
                "race_id",
                "role",
                "text",
                "token_count",
                "sha256",
                "exact_duplicate_hash",
                "exact_duplicate_flag",
                "boilerplate_flag",
            ]
            with segments_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for state in ("nh", "ia"):
                    writer.writerow(
                        {
                            "analysis_segment_id": f"segment-{state}",
                            "document_id": f"document-{state}",
                            "candidate_slug": "candidate",
                            "candidate_name": "Candidate",
                            "race_id": f"race-{state}",
                            "role": "endorsed",
                            "text": "A duplicated national platform statement with policy substance.",
                            "token_count": "9",
                            "sha256": "same-text",
                            "exact_duplicate_hash": "same-text",
                            "exact_duplicate_flag": "true",
                            "boilerplate_flag": "false",
                        }
                    )
            with metadata_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["document_id", "election_date"],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {"document_id": "document-nh", "election_date": "2020-02-11"},
                        {"document_id": "document-ia", "election_date": "2020-02-03"},
                    ]
                )

            rows = load_eligible_segments(segments_path, metadata_path)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["race_ids"], "race-ia | race-nh")
            self.assertEqual(rows[0]["provenance_row_count"], "2")

    def test_load_segments_keeps_same_text_for_different_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            segments_path = root / "segments.csv"
            fields = [
                "analysis_segment_id",
                "document_id",
                "candidate_slug",
                "candidate_name",
                "race_id",
                "role",
                "election_date",
                "text",
                "token_count",
                "sha256",
                "exact_duplicate_hash",
                "exact_duplicate_flag",
                "boilerplate_flag",
            ]
            with segments_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for candidate in ("a", "b"):
                    writer.writerow(
                        {
                            "analysis_segment_id": f"segment-{candidate}",
                            "document_id": f"document-{candidate}",
                            "candidate_slug": candidate,
                            "candidate_name": candidate.upper(),
                            "race_id": "race-1",
                            "role": "opponent",
                            "election_date": "2020-03-03",
                            "text": "A shared questionnaire prompt with candidate-attributed text.",
                            "token_count": "9",
                            "sha256": "same-text",
                            "exact_duplicate_hash": "same-text",
                            "exact_duplicate_flag": "true",
                            "boilerplate_flag": "false",
                        }
                    )

            rows = load_eligible_segments(
                segments_path,
                root / "missing-metadata.csv",
            )

            self.assertEqual(len(rows), 2)
            self.assertEqual({row["candidate_slug"] for row in rows}, {"a", "b"})
