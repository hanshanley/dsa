import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.text_analysis import (
    FIGURE_DIR,
    TABLE_DIR,
    _candidate_segment_corpus,
    _official_segment_corpus,
    _eligible_segment,
    _official_group,
    analyze_text,
    candidate_record_coverage,
    cosine_similarity,
    mpif_rows,
    official_feature_prevalence,
    policy_overlap_rows,
    shared_affirmative_mechanisms,
    tokenize,
)


class TextAnalysisTests(unittest.TestCase):
    def test_tokenize_removes_stopwords_and_normalizes_possessives(self):
        self.assertEqual(
            tokenize("The workers’ movement supports public ownership."),
            ["worker", "movement", "ownership"],
        )

    def test_tokenize_canonicalizes_policy_phrases(self):
        self.assertEqual(
            tokenize("Medicare for All and rent control support working-class tenants."),
            ["medicare_for_all", "rent_control", "working_class", "tenant"],
        )

    def test_cosine_similarity_bounds(self):
        self.assertAlmostEqual(cosine_similarity("public housing", "public housing"), 1.0)
        self.assertEqual(cosine_similarity("housing", "healthcare"), 0.0)

    def test_mpif_direction(self):
        rows = mpif_rows(
            [
                {"group": "endorsed", "text": "workers workers union"},
                {"group": "opponent", "text": "business business market"},
            ],
            "endorsed",
            "opponent",
            minimum_total=1,
        )
        by_feature = {row["feature"]: row for row in rows}
        self.assertEqual(by_feature["worker"]["favored_group"], "endorsed")
        self.assertEqual(by_feature["business"]["favored_group"], "opponent")

    def test_segment_eligibility_excludes_short_and_boilerplate_text(self):
        base = {"text": "substantive text", "token_count": "20", "boilerplate_flag": "false"}
        self.assertTrue(_eligible_segment(base))
        self.assertFalse(_eligible_segment({**base, "token_count": "19"}))
        self.assertFalse(_eligible_segment({**base, "boilerplate_flag": "true"}))

    def test_official_categories_group_dsa_and_democratic_full_platforms(self):
        self.assertEqual(_official_group("dsa_national | dsa_state_local"), "dsa")
        self.assertEqual(
            _official_group("dnc_national | state_democratic_party"),
            "democratic",
        )
        with self.assertRaises(ValueError):
            _official_group("dsa_national | dnc_national")

    def test_official_corpus_uses_current_verification_and_platform_section(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata_path = root / "organizational_context_document_metadata.csv"
            inventory_path = root / "inventory.csv"
            segments_path = root / "segments.csv"
            output_path = root / "corpus.csv"
            self._write_csv(
                metadata_path,
                [
                    {
                        "context_document_id": "combined",
                        "title": "Platform, Constitution and Bylaws",
                    },
                    {"context_document_id": "invalidated", "title": "Old Platform"},
                ],
            )
            self._write_csv(
                inventory_path,
                [
                    {"context_entry_id": "verified", "verification_status": "verified"},
                    {
                        "context_entry_id": "invalid",
                        "verification_status": "source_unavailable",
                    },
                ],
            )
            base = {
                "full_platform_categories": "state_democratic_party",
                "boilerplate_flag": "false",
                "token_count": "20",
                "context_categories": "state_democratic_party",
                "states": "Missouri",
                "state_codes": "MO",
                "cycle_years": "2026",
                "organizations": "Missouri Democratic Party",
                "titles": "Platform, Constitution and Bylaws",
                "platform_types": "state_party_platform",
                "locator": "paragraph 1",
                "exact_duplicate_hash": "duplicate",
                "fetch_id": "fetch",
            }
            self._write_csv(
                segments_path,
                [
                    {
                        **base,
                        "context_document_id": "combined",
                        "context_entry_ids": "verified",
                        "analysis_segment_id": "platform",
                        "segment_index": "0",
                        "sha256": "platform-hash",
                        "text": "Platform of Missouri with twenty substantive policy words "
                        "about schools workers health housing climate rights and fair wages.",
                    },
                    {
                        **base,
                        "context_document_id": "combined",
                        "context_entry_ids": "verified",
                        "analysis_segment_id": "constitution",
                        "segment_index": "1",
                        "sha256": "constitution-hash",
                        "text": "Constitution of Missouri with twenty procedural words about "
                        "committee officers meetings bylaws elections and internal governance.",
                    },
                    {
                        **base,
                        "context_document_id": "invalidated",
                        "context_entry_ids": "invalid",
                        "analysis_segment_id": "invalid",
                        "segment_index": "0",
                        "sha256": "invalid-hash",
                        "text": "An extracted stale platform passage that must not remain "
                        "after its source verification status changes.",
                    },
                ],
            )

            with (
                patch("dsa_analysis.text_analysis.PROCESSED_DIR", root),
                patch("dsa_analysis.text_analysis.OFFICIAL_INVENTORY_PATH", inventory_path),
                patch("dsa_analysis.text_analysis.OFFICIAL_SEGMENTS_PATH", segments_path),
                patch("dsa_analysis.text_analysis.OFFICIAL_CORPUS_PATH", output_path),
            ):
                documents, rows = _official_segment_corpus()

            self.assertEqual([row["text_sha256"] for row in rows], ["platform-hash"])
            self.assertEqual(len(documents), 1)
            self.assertNotIn("Constitution", documents[0]["text"])

    def test_official_prevalence_balances_unequal_document_counts(self):
        rows = official_feature_prevalence(
            [
                {"document_id": "dsa-1", "group": "dsa", "text": "workers and unions"},
                {"document_id": "dsa-2", "group": "dsa", "text": "workers"},
                {"document_id": "dem-1", "group": "democratic", "text": "workers"},
                {"document_id": "dem-2", "group": "democratic", "text": "small business"},
                {"document_id": "dem-3", "group": "democratic", "text": "small business"},
                {"document_id": "dem-4", "group": "democratic", "text": "small business"},
            ]
        )
        by_feature = {row["feature"]: row for row in rows}
        self.assertEqual(by_feature["worker"]["dsa_documents"], "2")
        self.assertEqual(by_feature["worker"]["democratic_documents"], "1")
        self.assertEqual(by_feature["worker"]["dsa_share"], "1.000000")
        self.assertEqual(by_feature["worker"]["democratic_share"], "0.250000")
        self.assertEqual(by_feature["small_business"]["dsa_share"], "0.000000")
        self.assertEqual(by_feature["small_business"]["democratic_share"], "0.750000")

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_candidate_coverage_uses_registry_queue_denominator(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            summary_path = Path(directory) / "full_text_queue_summary.csv"
            fields = [
                "queue_source",
                "group",
                "election_year",
                "current_status",
                "candidate_count",
                "race_count",
            ]
            rows = [
                ("endorsed", "verified", "3"),
                ("endorsed", "found_unverified", "5"),
                ("opponent", "verified", "7"),
                ("opponent", "not_searched", "11"),
                ("opponent", "source_unavailable", "13"),
            ]
            with summary_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for group, status, count in rows:
                    writer.writerow(
                        {
                            "queue_source": "registry",
                            "group": group,
                            "election_year": "2024",
                            "current_status": status,
                            "candidate_count": count,
                            "race_count": "1",
                        }
                    )
            with patch(
                "dsa_analysis.text_analysis.FULL_TEXT_QUEUE_SUMMARY_PATH",
                summary_path,
            ):
                coverage = {row["group"]: row for row in candidate_record_coverage()}
            self.assertEqual(
                coverage["endorsed"]["candidate_race_records_with_extracted_text"],
                "3",
            )
            self.assertEqual(
                coverage["endorsed"]["candidate_race_records_without_extracted_text"],
                "5",
            )
            self.assertEqual(
                coverage["opponent"]["candidate_race_records_without_extracted_text"],
                "24",
            )
            self.assertAlmostEqual(
                float(coverage["opponent"]["extracted_share"]),
                7 / 31,
                places=6,
            )

    def test_policy_overlap_excludes_tiny_shared_prevalence(self):
        rows = policy_overlap_rows(
            [
                {
                    "feature": "healthcare",
                    "endorsed_share": "0.20",
                    "opponent_share": "0.18",
                    "difference": "0.02",
                },
                {
                    "feature": "universal_basic_income",
                    "endorsed_share": "0.001",
                    "opponent_share": "0.001",
                    "difference": "0.0",
                },
            ]
        )

        self.assertEqual([row["feature"] for row in rows], ["healthcare"])
        self.assertEqual(rows[0]["shared_emphasis"], "0.180000")

    def test_shared_mechanisms_require_both_groups_and_exclude_negation(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "segments.csv"
            fields = [
                "race_id",
                "candidate_name",
                "role",
                "source_type",
                "text",
                "token_count",
                "boilerplate_flag",
            ]
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "race_id": "race-1",
                            "candidate_name": "Endorsed",
                            "role": "endorsed",
                            "source_type": "policy_page",
                            "text": "We will enact rent control and build tenant power across the city.",
                            "token_count": "20",
                            "boilerplate_flag": "false",
                        },
                        {
                            "race_id": "race-1",
                            "candidate_name": "Opponent",
                            "role": "opponent",
                            "source_type": "candidate_questionnaire",
                            "text": "I support rent control as one tool for keeping homes affordable.",
                            "token_count": "20",
                            "boilerplate_flag": "false",
                        },
                        {
                            "race_id": "race-2",
                            "candidate_name": "Endorsed",
                            "role": "endorsed",
                            "source_type": "policy_page",
                            "text": "Our platform supports a public option for every resident.",
                            "token_count": "20",
                            "boilerplate_flag": "false",
                        },
                        {
                            "race_id": "race-2",
                            "candidate_name": "Opponent",
                            "role": "opponent",
                            "source_type": "policy_page",
                            "text": "I oppose the public option and prefer another approach.",
                            "token_count": "20",
                            "boilerplate_flag": "false",
                        },
                        {
                            "race_id": "race-3",
                            "candidate_name": "Endorsed",
                            "role": "endorsed",
                            "source_type": "policy_page",
                            "text": "We support a public option as an immediate coverage expansion.",
                            "token_count": "20",
                            "boilerplate_flag": "false",
                        },
                        {
                            "race_id": "race-3",
                            "candidate_name": "Opponent",
                            "role": "opponent",
                            "source_type": "policy_page",
                            "text": "There should be no public option in the final legislation.",
                            "token_count": "20",
                            "boilerplate_flag": "false",
                        },
                    ]
                )

            rows = shared_affirmative_mechanisms(path)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["feature"], "rent_control")
        self.assertEqual(rows[0]["race_id"], "race-1")

    def test_candidate_corpus_deduplicates_shared_text_across_state_races(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            segment_path = root / "segments.csv"
            metadata_path = root / "metadata.csv"
            output_path = root / "corpus.csv"
            text = "A national platform segment with enough substantive policy words."
            segment_fields = [
                "analysis_segment_id", "document_id", "candidate_slug", "candidate_name",
                "race_id", "role", "source_type", "segment_index", "locator", "text",
                "token_count", "sha256", "exact_duplicate_hash", "boilerplate_flag",
            ]
            with segment_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=segment_fields)
                writer.writeheader()
                for state, document_id in (("nh", "doc-nh"), ("ia", "doc-ia")):
                    writer.writerow(
                        {
                            "analysis_segment_id": f"segment-{state}",
                            "document_id": document_id,
                            "candidate_slug": "candidate",
                            "candidate_name": "Candidate",
                            "race_id": f"race-{state}",
                            "role": "endorsed",
                            "source_type": "official_campaign_platform",
                            "segment_index": "1",
                            "locator": "paragraph 1",
                            "text": text,
                            "token_count": "20",
                            "sha256": "text-hash",
                            "exact_duplicate_hash": "duplicate-hash",
                            "boilerplate_flag": "false",
                        }
                    )
            metadata_fields = [
                "document_id", "election_date", "source_url", "archive_url", "final_url",
                "publication_date", "text_sha256",
            ]
            with metadata_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=metadata_fields)
                writer.writeheader()
                for document_id in ("doc-nh", "doc-ia"):
                    writer.writerow(
                        {
                            "document_id": document_id,
                            "election_date": "2016-02-09",
                            "source_url": "https://example.org/platform",
                            "text_sha256": "document-hash",
                        }
                    )
            with (
                patch("dsa_analysis.text_analysis.CANDIDATE_SEGMENTS_PATH", segment_path),
                patch("dsa_analysis.text_analysis.CANDIDATE_METADATA_PATH", metadata_path),
                patch("dsa_analysis.text_analysis.CORPUS_PATH", output_path),
            ):
                documents, segments = _candidate_segment_corpus()
            self.assertEqual(len(documents), 1)
            self.assertEqual(len(segments), 1)
            self.assertEqual(segments[0]["race_ids"], "race-ia | race-nh")
            self.assertEqual(segments[0]["provenance_row_count"], "2")

    def test_analysis_generates_figures_and_manifest(self):
        model_figure = FIGURE_DIR / "model_topic_emphasis_difference.svg"
        created_placeholder = not model_figure.exists()
        if created_placeholder:
            model_figure.parent.mkdir(parents=True, exist_ok=True)
            model_figure.write_text("<svg/>", encoding="utf-8")
        try:
            stats = analyze_text()
            self.assertGreater(stats["candidate_documents"], 0)
            self.assertGreater(stats["candidate_segments"], 0)
            self.assertGreater(stats["official_segments"], 0)
            self.assertGreater(stats["sticking_points"], 0)
            self.assertEqual(stats["figure_count"], 10)
            self.assertEqual(stats["generated_figure_count"], 9)
            self.assertTrue((FIGURE_DIR / "policy_language_difference.svg").exists())
            self.assertTrue((FIGURE_DIR / "policy_language_overlap.svg").exists())
            self.assertTrue(
                (FIGURE_DIR / "shared_affirmative_policy_mechanisms.svg").exists()
            )
            self.assertTrue((FIGURE_DIR / "official_policy_contrasts.svg").exists())
            self.assertTrue(
                (FIGURE_DIR / "official_platform_document_prevalence.svg").exists()
            )
            self.assertTrue(model_figure.exists())
            self.assertTrue((TABLE_DIR / "analysis_manifest.json").exists())
            self.assertTrue(
                (TABLE_DIR / "official_platform_document_prevalence.csv").exists()
            )
        finally:
            if created_placeholder:
                model_figure.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
