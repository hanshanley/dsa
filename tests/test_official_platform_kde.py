import csv
import tempfile
import unittest
from pathlib import Path

from dsa_analysis.official_platform_kde import load_official_platform_segments


class OfficialPlatformKDETests(unittest.TestCase):
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
