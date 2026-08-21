import unittest
import csv
import tempfile
from pathlib import Path

from dsa_analysis.provisional_kde import (
    _looks_like_navigation_or_form,
    balanced_kde_sample_indices,
    density_region_summaries,
    load_eligible_segments,
    select_dimension_elbow,
)


class ProvisionalKDETests(unittest.TestCase):
    def test_url_encoded_questionnaire_boilerplate_is_detected(self) -> None:
        self.assertTrue(
            _looks_like_navigation_or_form(
                "Org+Thank+you+for+your+interest+in+completing+this+questionnare."
            )
        )

    def test_density_region_excerpt_selects_substantive_sentence(self) -> None:
        rows = [
            {
                "zone": "shared",
                "umap_x": index / 100,
                "umap_y": index / 100,
                "log1p_density_ratio": 0.0,
                "candidate_unit_id": f"candidate-{index}",
                "candidate_name": "Candidate",
                "text": (
                    "10 Oct 2019 — 3 min read Share Candidate biography. "
                    "The candidate supports police accountability and community council "
                    "oversight through transparent public information."
                ),
                "token_count": "24",
            }
            for index in range(12)
        ]

        [region] = density_region_summaries(rows, max_regions_per_zone=1)

        self.assertTrue(region["representative_excerpt"].startswith("The candidate supports"))

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
                            "text": (
                                "A duplicated national platform statement with enough substantive "
                                "policy language to qualify for the embedding analysis corpus."
                            ),
                            "token_count": "20",
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
                            "text": (
                                "A shared questionnaire response containing enough attributable "
                                "candidate policy language to qualify for embedding analysis."
                            ),
                            "token_count": "20",
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

    def test_density_regions_summarize_hot_cold_and_shared_text(self) -> None:
        rows = []
        zone_specs = {
            "hot": (1.0, "worker union housing justice"),
            "cold": (-1.0, "business technology market growth"),
            "shared": (0.0, "healthcare school climate community"),
        }
        for zone_index, (zone, (score, text)) in enumerate(zone_specs.items()):
            for index in range(12):
                rows.append(
                    {
                        "zone": zone,
                        "umap_x": zone_index * 4 + index / 100,
                        "umap_y": zone_index * 3 + index / 100,
                        "log1p_density_ratio": score,
                        "candidate_unit_id": f"{zone}-{index}",
                        "candidate_name": f"Candidate {index}",
                        "text": f"{text} policy program for working families",
                        "token_count": "8",
                    }
                )

        regions = density_region_summaries(rows)

        self.assertEqual({row["zone"] for row in regions}, {"hot", "cold", "shared"})
        self.assertTrue(all(row["top_terms"] for row in regions))
        self.assertTrue(all(row["representative_excerpt"] for row in regions))
        self.assertTrue(all(row.get("density_region_id") for row in rows))
