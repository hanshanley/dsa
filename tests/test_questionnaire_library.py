import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from dsa_analysis.document_corpus import RawDocumentCapture
from dsa_analysis.io import read_csv, write_csv
from dsa_analysis.questionnaire_library import collect_questionnaires


class QuestionnaireLibraryTests(unittest.TestCase):
    def test_full_body_and_publisher_local_dates_are_retained_without_policy_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = [{
                "race_id": "race", "scope_kind": "tracked_dsa_endorsed_democratic_primary",
                "election_year": "2025", "election_date": "2025-06-24", "office": "City Council",
                "jurisdiction": "District 1", "all_candidates": "Jane Example | Other Candidate",
            }]
            write_csv(root / "race_registry.csv", registry, list(registry[0]))
            stamp = int(datetime(2025, 4, 27, 3, tzinfo=UTC).timestamp() * 1000)
            payload = {
                "website": {"timeZone": "America/New_York"},
                "pagination": {"nextPage": False},
                "items": [{
                    "id": "safe-id", "title": "Candidate Answers to JOLDC: Jane Example for City Council",
                    "fullUrl": "/news/jane", "publishOn": stamp, "updatedOn": stamp,
                    "body": "<p>Complete candidate answer with its context.</p>",
                }],
            }
            body = json.dumps(payload).encode()
            capture = RawDocumentCapture(
                document_id="index", source_url="https://jimowles.org/news?format=json",
                final_url="https://jimowles.org/news?format=json", retrieved_at="2026-09-23",
                content_type="application/json", encoding="utf-8", content_bytes=body,
                byte_count=len(body), sha256=hashlib.sha256(body).hexdigest(),
            )
            with (
                patch("dsa_analysis.questionnaire_library.ROOT", root),
                patch("dsa_analysis.questionnaire_library.RAW_DIR", root / "raw"),
                patch("dsa_analysis.questionnaire_library.ANALYSIS_DATA_DIR", root / "analysis"),
                patch("dsa_analysis.questionnaire_library.PROCESSED_DIR", root),
                patch("dsa_analysis.questionnaire_library.fetch_raw_document", return_value=capture),
            ):
                result = collect_questionnaires(max_pages=1, pause_seconds=0)
            output = root / "analysis" / "policy_evidence" / "questionnaire_library"
            record = read_csv(output / "source_catalog.csv")[0]
            self.assertEqual(record["publication_date"], "2025-04-26")
            self.assertEqual((root / record["complete_body_path"]).read_text(), payload["items"][0]["body"])
            self.assertTrue(result["complete_public_index_pass"])
            self.assertFalse(result["semantic_review_complete"])
            self.assertIn("discovery_lead", read_csv(output / "registry_source_leads.csv")[0]["status"])


if __name__ == "__main__":
    unittest.main()
