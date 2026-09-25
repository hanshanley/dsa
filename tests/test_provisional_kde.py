import unittest
import csv
import tempfile
from pathlib import Path

from dsa_analysis.provisional_kde import (
    _cluster_terms_look_substantive,
    _density_fingerprint_layout,
    _distinctive_region_terms,
    _looks_like_navigation_or_form,
    _looks_like_table_of_contents,
    _wrap_card_text,
    _write_kde_report,
    balanced_kde_sample_indices,
    density_region_summaries,
    load_eligible_segments,
    select_dimension_elbow,
)


class ProvisionalKDETests(unittest.TestCase):
    def test_report_uses_selected_dimension_in_cluster_description(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.md"
            _write_kde_report(path, {
                "retained_segments": 30,
                "group_counts": {"endorsed": 10, "opponent": 20},
                "selected_dimensions": 5,
                "density_regions": [],
            })
            text = path.read_text(encoding="utf-8")
            self.assertIn("selected 5-dimensional UMAP representation", text)
            self.assertNotIn("10-dimensional", text)
            self.assertIn("give candidates equal density weight", text)

    def test_card_text_wrapper_enforces_line_budget(self) -> None:
        wrapped = _wrap_card_text(
            "one two three four five six seven eight nine ten",
            width=10,
            max_lines=2,
        )

        self.assertEqual(len(wrapped.splitlines()), 2)
        self.assertTrue(wrapped.endswith("…"))

    def test_density_fingerprint_layout_stacks_three_region_cards(self) -> None:
        self.assertEqual(
            _density_fingerprint_layout(3),
            (3, 1, (1.35, 0.90)),
        )
        self.assertEqual(
            _density_fingerprint_layout(6),
            (3, 2, (1.08, 1.0)),
        )

    def test_region_terms_exclude_pronouns_contractions_and_filler(self) -> None:
        region_rows = [
            {
                "candidate_name": "Candidate",
                "text": (
                    "I'm really thinking about housing housing tenants rent eviction "
                    "and I think it's what we want."
                ),
            }
            for _ in range(10)
        ]
        background_rows = [
            {
                "candidate_name": "Other",
                "text": "Schools students education funding teachers.",
            }
            for _ in range(10)
        ]

        terms = _distinctive_region_terms(region_rows, [*region_rows, *background_rows])

        self.assertNotIn("i'm", terms)
        self.assertNotIn("really", terms)
        self.assertNotIn("think", terms)
        self.assertIn("housing", terms)

    def test_cluster_term_gate_rejects_coherent_nonpolitical_artifacts(self) -> None:
        self.assertFalse(
            _cluster_terms_look_substantive(
                ["podcast", "story", "chicago", "read", "aug"]
            )
        )
        self.assertFalse(
            _cluster_terms_look_substantive(
                ["withdrawal", "payout", "casino", "interac", "wallet"]
            )
        )
        self.assertFalse(
            _cluster_terms_look_substantive(
                ["actblue", "donation", "phone", "saved", "express"]
            )
        )
        self.assertFalse(
            _cluster_terms_look_substantive(
                ["council", "june", "interview", "ballot", "party"]
            )
        )
        self.assertTrue(
            _cluster_terms_look_substantive(
                ["housing", "tenant", "landlord", "rent", "eviction"]
            )
        )

    def test_url_encoded_questionnaire_boilerplate_is_detected(self) -> None:
        self.assertTrue(
            _looks_like_navigation_or_form(
                "Org+Thank+you+for+your+interest+in+completing+this+questionnare."
            )
        )

    def test_navigation_and_disclosure_fragments_are_detected(self) -> None:
        self.assertTrue(
            _looks_like_navigation_or_form(
                "High School football (Opens in new window) Friday Night Drive podcast"
            )
        )
        self.assertTrue(
            _looks_like_navigation_or_form(
                "Schedule Summary (required) Schedules attached Total number of pages"
            )
        )
        self.assertTrue(
            _looks_like_navigation_or_form(
                "Subscribe Issues Archive Articles Podcast This is a search field"
            )
        )
        self.assertTrue(
            _looks_like_navigation_or_form(
                "[PDF page 6] Table of Contents Agriculture Arts Business Civil Rights"
            )
        )
        self.assertTrue(_looks_like_navigation_or_form("��� ��M1�z h�M�/�$ ��"))
        self.assertTrue(
            _looks_like_navigation_or_form(
                "Instant Casino Fastest Withdrawal Methods Payout Interac e-Transfer"
            )
        )
        self.assertTrue(
            _looks_like_navigation_or_form(
                "Do you commit to visiting constituents who are incarcerated in state prisons?"
            )
        )
        self.assertTrue(
            _looks_like_navigation_or_form(
                "1705 Longworth House Office Building Washington, DC 20515 Phone Fax"
            )
        )
        self.assertTrue(
            _looks_like_table_of_contents(
                "Preamble America at 250 Declaration Constitution State Today Economy "
                "Education Housing Health Care Environment Energy"
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

        [region] = density_region_summaries(
            rows,
            max_regions_per_zone=1,
            min_candidate_count=1,
        )

        self.assertTrue(region["representative_excerpt"].startswith("The candidate supports"))

    def test_density_region_excerpt_prefers_relevant_text_over_central_navigation(self) -> None:
        rows = []
        for index in range(12):
            rows.append(
                {
                    "zone": "hot",
                    "umap_x": 0.0 if index == 0 else 1.0 + index / 100,
                    "umap_y": 0.0 if index == 0 else 1.0 + index / 100,
                    "log1p_density_ratio": 1.0,
                    "candidate_unit_id": f"candidate-{index}",
                    "candidate_name": f"Candidate {index}",
                    "source_type": "campaign_page",
                    "text": (
                        "Skip to main content Issues Get Involved Donate"
                        if index == 0
                        else (
                            "Our climate plan replaces fossil fuel infrastructure with "
                            "community-owned renewable energy."
                        )
                    ),
                    "token_count": "20",
                }
            )

        [region] = density_region_summaries(
            rows,
            max_regions_per_zone=1,
            min_candidate_count=1,
        )

        self.assertIn("climate plan", region["representative_excerpt"])

    def test_density_region_excerpt_does_not_attribute_debate_speaker_to_candidate(self) -> None:
        rows = [
            {
                "zone": "cold",
                "umap_x": index / 100,
                "umap_y": index / 100,
                "log1p_density_ratio": -1.0,
                "candidate_unit_id": f"candidate-{index}",
                "candidate_name": "Candidate",
                "source_type": "debate_transcript",
                "text": (
                    "HARRIS: Donald Trump made promises to working people that he did not keep."
                ),
                "token_count": "20",
            }
            for index in range(12)
        ]

        [region] = density_region_summaries(
            rows,
            max_regions_per_zone=1,
            min_candidate_count=1,
        )

        self.assertEqual(region["representative_candidate"], "Multi-candidate debate")

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

    def test_balanced_kde_sample_uses_all_provenance_units(self) -> None:
        rows = [
            {"group": "endorsed", "support_unit_ids": "document-a | document-b"},
            {"group": "endorsed", "support_unit_ids": "document-a"},
            {"group": "endorsed", "support_unit_ids": "document-b"},
            {"group": "endorsed", "support_unit_ids": "document-c"},
        ]

        selected = balanced_kde_sample_indices(
            rows,
            group="endorsed",
            limit=3,
            seed=1729,
        )
        represented = {
            document_id.strip()
            for index in selected
            for document_id in rows[index]["support_unit_ids"].split(" | ")
        }

        self.assertEqual(len(selected), 3)
        self.assertEqual(represented, {"document-a", "document-b", "document-c"})

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
                    fieldnames=["document_id", "election_date", "race_id"],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {"document_id": "document-nh", "election_date": "2020-02-11", "race_id": "race-nh"},
                        {"document_id": "document-ia", "election_date": "2020-02-03", "race_id": "race-ia"},
                    ]
                )
            self._write_registry(root / "race_registry.csv", ["race-nh", "race-ia"])

            rows = load_eligible_segments(segments_path, metadata_path)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["race_ids"], "race-ia | race-nh")
            self.assertEqual(rows[0]["provenance_row_count"], "2")

    def test_presidential_alias_dedup_retains_original_ballot_names(self):
        from dsa_analysis.io import write_csv
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [{
                "analysis_segment_id": str(i), "document_id": str(i), "race_id": "r",
                "candidate_name": name, "candidate_slug": slug, "role": "opponent",
                "text": "We support more affordable housing, stronger public schools, accessible healthcare and fair wages for working families across the country.",
                "token_count": "22", "sha256": "same", "boilerplate_flag": "false",
            } for i, (name, slug) in enumerate((
                ("Elizabeth Warren", "elizabeth-warren"),
                ("Elizabeth Ann Warren", "elizabeth-ann-warren"),
            ))]
            write_csv(root / "segments.csv", rows, list(rows[0]))
            metadata = [{
                "document_id": str(i), "race_id": "r", "election_date": "2020-02-11",
            } for i in range(2)]
            write_csv(root / "metadata.csv", metadata, list(metadata[0]))
            registry = [{
                "race_id": "r", "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                "office": "President",
            }]
            write_csv(root / "race_registry.csv", registry, list(registry[0]))
            [retained] = load_eligible_segments(root / "segments.csv", root / "metadata.csv")
            self.assertEqual(retained["candidate_unit_id"], "2020:elizabeth-warren")
            self.assertEqual(retained["source_candidate_names"], "Elizabeth Ann Warren | Elizabeth Warren")
            registry[0]["office"] = "City Council"
            write_csv(root / "race_registry.csv", registry, list(registry[0]))
            self.assertEqual(len(load_eligible_segments(root / "segments.csv", root / "metadata.csv")), 2)

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

            metadata_path = root / "metadata.csv"
            with metadata_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["document_id", "election_date", "race_id"])
                writer.writeheader()
                writer.writerows([
                    {"document_id": f"document-{name}", "election_date": "2020-03-03", "race_id": "race-1"}
                    for name in ("a", "b")
                ])
            self._write_registry(root / "race_registry.csv", ["race-1"])
            rows = load_eligible_segments(segments_path, metadata_path)

            self.assertEqual(len(rows), 2)
            self.assertEqual({row["candidate_slug"] for row in rows}, {"a", "b"})

    @staticmethod
    def _write_registry(path, race_ids):
        from dsa_analysis.io import write_csv
        rows = [{
            "race_id": race_id, "scope_kind": "tracked_dsa_endorsed_democratic_primary",
            "election_date": "2020-03-03", "endorsed_candidates": "Candidate",
        } for race_id in race_ids]
        write_csv(path, rows, list(rows[0]))

    def test_kde_uses_source_eligibility_and_primary_scope(self):
        from dsa_analysis.io import write_csv
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            changes = {
                "good": {},
                "quote": {"analysis_scope": "reviewed_quote"},
                "context": {"analysis_scope": "context_only"},
                "undated": {"publication_date": "", "campaign_window_status": "undated"},
                "unscoped": {"extraction_status": "shared_document_unscoped"},
                "outside": {"race_id": "not-a-primary"},
                "interview": {"source_type": "candidate_interview"},
            }
            metadata = [{
                "document_id": key, "election_date": "2020-03-03",
                "publication_date": "2020-02-01", "retrieved_at": "2026-09-24",
                "race_id": "race", "campaign_window_status": "in_window",
                "analysis_scope": "analysis", "extraction_status": "extracted",
                "source_type": "campaign_platform", "source_url": "https://candidate.example/issues",
                "final_url": "https://candidate.example/issues", **override,
            } for key, override in changes.items()]
            segments = [{
                "document_id": row["document_id"], "analysis_segment_id": row["document_id"],
                "race_id": row["race_id"], "candidate_slug": row["document_id"],
                "candidate_name": row["document_id"], "role": "endorsed", "token_count": "24",
                "boilerplate_flag": "false",
                "text": "We support public housing construction, better funded schools, affordable healthcare, expanded labor rights, and reliable public transportation for every community in our state.",
            } for row in metadata]
            write_csv(root / "metadata.csv", metadata, list(metadata[0]))
            write_csv(root / "segments.csv", segments, list(segments[0]))
            self._write_registry(root / "race_registry.csv", ["race"])
            rows = load_eligible_segments(root / "segments.csv", root / "metadata.csv")
            self.assertEqual([row["document_id"] for row in rows], ["good"])
            with self.assertRaisesRegex(ValueError, "requires source metadata"):
                load_eligible_segments(root / "segments.csv", root / "missing.csv")
            metadata[0]["race_id"] = "different"
            write_csv(root / "metadata.csv", metadata, list(metadata[0]))
            with self.assertRaisesRegex(ValueError, "disagree on race"):
                load_eligible_segments(root / "segments.csv", root / "metadata.csv")

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

        regions = density_region_summaries(rows, min_candidate_count=1)

        self.assertEqual({row["zone"] for row in regions}, {"hot", "cold", "shared"})
        self.assertTrue(all(row["top_terms"] for row in regions))
        self.assertTrue(all(row["representative_excerpt"] for row in regions))
        self.assertTrue(all("density_cluster_label" in row for row in rows))
        self.assertTrue(
            all(
                row.get("density_region_id")
                for row in rows
                if row["density_cluster_label"] >= 0
            )
        )

    def test_density_regions_use_hdbscan_in_semantic_space(self) -> None:
        import numpy as np

        rows = []
        semantic_coordinates = []
        for cluster, terms in enumerate(
            ("climate energy", "tenant rent", "healthcare insurance")
        ):
            for index in range(180):
                rows.append(
                    {
                        "zone": "hot",
                        "umap_x": index / 100,
                        "umap_y": index / 100,
                        "log1p_density_ratio": 1.0,
                        "candidate_unit_id": f"{cluster}-{index}",
                        "candidate_name": f"Candidate {cluster}-{index}",
                        "text": f"{terms} policy language for working families",
                        "token_count": "20",
                    }
                )
                semantic_coordinates.append(
                    [float(cluster * 10), index / 10_000]
                )

        regions = density_region_summaries(
            rows,
            max_regions_per_zone=3,
            semantic_coordinates=np.array(semantic_coordinates),
        )

        self.assertEqual(len(regions), 3)
        self.assertTrue(all(row["semantic_coherence"] > 0.9 for row in regions))
        self.assertEqual({row["region_id"] for row in regions}, {"D1", "D2", "D3"})
        self.assertTrue(
            all(0.0 <= row["mean_membership_probability"] <= 1.0 for row in regions)
        )
        self.assertEqual(
            sum(bool(row["displayed_on_map"]) for row in regions),
            2,
        )

    def test_hdbscan_leaves_isolated_semantic_point_as_noise(self) -> None:
        import numpy as np

        rows = []
        semantic_coordinates = []
        for cluster, terms in enumerate(("climate energy", "tenant rent")):
            for index in range(80):
                rows.append(
                    {
                        "zone": "hot",
                        "umap_x": float(cluster),
                        "umap_y": index / 100,
                        "log1p_density_ratio": 1.0,
                        "candidate_unit_id": f"{cluster}-{index}",
                        "candidate_name": f"Candidate {cluster}-{index}",
                        "text": f"{terms} policy language for working families",
                        "token_count": "20",
                    }
                )
                semantic_coordinates.append([float(cluster * 10), index / 10_000])
        noise_row = {
            "zone": "hot",
            "umap_x": 100.0,
            "umap_y": 100.0,
            "log1p_density_ratio": 1.0,
            "candidate_unit_id": "noise",
            "candidate_name": "Noise Candidate",
            "text": "Unrelated isolated semantic content with no nearby passages",
            "token_count": "20",
        }
        rows.append(noise_row)
        semantic_coordinates.append([100.0, 100.0])

        regions = density_region_summaries(
            rows,
            max_regions_per_zone=2,
            min_cluster_size=20,
            min_samples=5,
            semantic_coordinates=np.array(semantic_coordinates),
        )

        self.assertEqual(len(regions), 2)
        self.assertEqual(noise_row["density_cluster_label"], -1)
        self.assertNotIn("density_region_id", noise_row)
