import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.text_analysis import (
    FIGURE_DIR,
    TABLE_DIR,
    _candidate_segment_corpus,
    _eligible_segment,
    _official_group,
    analyze_text,
    candidate_record_coverage,
    cosine_similarity,
    mpif_rows,
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
            self.assertEqual(stats["figure_count"], 6)
            self.assertTrue((FIGURE_DIR / "policy_language_difference.svg").exists())
            self.assertTrue((FIGURE_DIR / "official_policy_contrasts.svg").exists())
            self.assertTrue(model_figure.exists())
            self.assertTrue((TABLE_DIR / "analysis_manifest.json").exists())
        finally:
            if created_placeholder:
                model_figure.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
