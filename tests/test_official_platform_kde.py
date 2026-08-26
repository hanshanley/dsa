import csv
import tempfile
import unittest
from pathlib import Path

from dsa_analysis.official_platform_kde import (
    _document_balance_weights,
    _prepare_platform_analysis_rows,
    load_official_platform_segments,
)


class OfficialPlatformKDETests(unittest.TestCase):
    def test_platform_analysis_gate_excludes_sparse_and_navigation_only_sources(self):
        rows = [
            {
                "analysis_segment_id": f"good-{index}",
                "group": "endorsed",
                "official_group": "dsa",
                "support_unit_ids": "document-good",
                "candidate_unit_id": "document-good",
                "candidate_name": "Good platform",
                "source_type": "dsa_national_program",
                "text": f"Substantive worker housing policy passage number {index}.",
                "organizations": "Good platform",
                "titles": "Program",
                "cycle_years": "2024",
            }
            for index in range(3)
        ]
        rows.extend(
            [
                {
                    "analysis_segment_id": "sparse",
                    "group": "opponent",
                    "official_group": "democratic",
                    "support_unit_ids": "document-sparse",
                    "candidate_unit_id": "document-sparse",
                    "candidate_name": "Sparse platform",
                    "source_type": "state_party_platform",
                    "text": "One isolated policy passage.",
                    "organizations": "Sparse platform",
                    "titles": "Platform",
                    "cycle_years": "2024",
                },
                {
                    "analysis_segment_id": "navigation",
                    "group": "endorsed",
                    "official_group": "dsa",
                    "support_unit_ids": "document-good",
                    "candidate_unit_id": "document-good",
                    "candidate_name": "Good platform",
                    "source_type": "dsa_national_program",
                    "text": "EVENTS EVENTS Resources Resources Take Action Take Action DONATE DONATE",
                    "organizations": "Good platform",
                    "titles": "Program",
                    "cycle_years": "2024",
                },
            ]
        )

        eligible, coverage, audit = _prepare_platform_analysis_rows(
            rows,
            minimum_passages=2,
        )

        self.assertEqual(len(eligible), 3)
        self.assertEqual(audit["text_quality_excluded_passages"], 1)
        self.assertEqual(audit["excluded_platforms"], 1)
        self.assertEqual(
            {row["document_id"]: row["eligible"] for row in coverage},
            {"document-good": True, "document-sparse": False},
        )

    def test_document_balance_weights_equalize_platform_contributions(self):
        rows = [
            {"support_unit_ids": "document-a"},
            {"support_unit_ids": "document-a"},
            {"support_unit_ids": "document-b"},
        ]

        self.assertEqual(
            _document_balance_weights(rows, [0, 1, 2]),
            [0.5, 0.5, 1.0],
        )

    def test_loader_maps_groups_and_platform_documents(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "platforms.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "corpus_segment_id",
                        "context_document_ids",
                        "group",
                        "organizations",
                        "platform_types",
                        "source_urls",
                        "locators",
                        "text",
                        "token_count",
                        "context_categories",
                        "titles",
                        "cycle_years",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "corpus_segment_id": "segment-dsa",
                        "context_document_ids": "dsa-document",
                        "group": "dsa",
                        "organizations": "DSA",
                        "platform_types": "national_program",
                        "source_urls": "https://example.org/dsa",
                        "locators": "paragraph 1",
                        "text": "Working-class power and social housing.",
                        "token_count": "20",
                    }
                )
                writer.writerow(
                    {
                        "corpus_segment_id": "segment-dem",
                        "context_document_ids": "dem-document",
                        "group": "democratic",
                        "organizations": "Democratic Party",
                        "platform_types": "national_party_platform",
                        "source_urls": "https://example.org/dem",
                        "locators": "paragraph 2",
                        "text": "Affordable education and health care.",
                        "token_count": "20",
                    }
                )
            rows = load_official_platform_segments(path)
        self.assertEqual([row["group"] for row in rows], ["endorsed", "opponent"])
        self.assertEqual(rows[0]["candidate_unit_id"], "dsa-document")
        self.assertEqual(rows[1]["candidate_unit_id"], "dem-document")


if __name__ == "__main__":
    unittest.main()
