import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from dsa_analysis.coverage import build_coverage_ledger, coverage_chapters
from dsa_analysis.document_corpus import classify_campaign_window
from dsa_analysis.io import read_csv, write_csv
from dsa_analysis.queue import build_research_queue
from dsa_analysis.wayback_crawler import (
    _discover_chapter,
    _status,
    discover_wayback_urls,
    infer_election_year,
)


class HistoricalDiscoveryTests(unittest.TestCase):
    def test_2015_campaign_evidence_remains_in_2016_election_window(self):
        self.assertEqual(classify_campaign_window("2016-06-14", "2015-06-22"), "in_window")
        self.assertEqual(infer_election_year("https://example.org/2015/endorsements/", "2020"), "2015")
        self.assertEqual(infer_election_year("https://example.org/2027/endorsements/", "2026"), "2027")

    def test_disappeared_chapter_and_single_endorsement_do_not_look_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config"
            config.mkdir()
            (config / "sources.json").write_text(json.dumps({
                "study_start": "2016-01-01", "source_start": "2015-01-01",
                "research_cutoff": "2026-09-22",
            }))
            write_csv(root / "chapter_directory.csv", [{
                "record_id": "current", "Name": "Current", "State": "NY", "Website": "",
            }], ["record_id", "Name", "State", "Website"])
            write_csv(root / "national_endorsement_archive.csv", [], [
                "record_id", "office_types",
            ])
            write_csv(root / "local_endorsements_verified.csv", [{
                "chapter": "Historical DSA", "state": "CA", "election_year": "2016",
                "source_url": "https://example.org/2015/endorsement",
            }], ["chapter", "state", "election_year", "source_url"])
            with (
                patch("dsa_analysis.coverage.PROCESSED_DIR", root),
                patch("dsa_analysis.coverage.MANUAL_DIR", root),
                patch("dsa_analysis.coverage.CONFIG_DIR", config),
                patch("dsa_analysis.queue.PROCESSED_DIR", root),
                patch("dsa_analysis.queue.CONFIG_DIR", config),
            ):
                chapters = coverage_chapters()
                self.assertEqual(len(chapters), 2)
                _, count = build_research_queue()
                self.assertEqual(count, 24)
                build_coverage_ledger()
                ledger = read_csv(root / "coverage_ledger.csv")
            verified_lead = next(row for row in ledger if (
                row["chapter"] == "Historical DSA" and row["election_year"] == "2016"
            ))
            self.assertEqual(verified_lead["status"], "found_unverified")
            self.assertIn("not_exhaustive", verified_lead["search_method"])
            self.assertEqual(sum(row["election_year"] == "2015" for row in ledger), 2)

    def test_archive_query_uses_configured_2015_lookback_without_url_collapse(self):
        chapter = {"record_id": "one", "Name": "Example", "State": "NY",
                   "Website": "https://example.org"}
        config = {"study_start": "2016-01-01", "source_start": "2015-01-01",
                  "research_cutoff": "2026-09-22"}
        with (
            patch("dsa_analysis.wayback_crawler.read_json", return_value=config),
            patch("dsa_analysis.wayback_crawler.urllib.request.urlopen") as request,
            patch("dsa_analysis.wayback_crawler.json.load", return_value=[
                ["timestamp", "original", "statuscode", "digest"],
                ["20150622000000", "https://example.org/2015/endorsements/", "200", "digest"],
            ]),
        ):
            rows, status = _discover_chapter(chapter, timeout=5)
        query = parse_qs(urlparse(request.call_args.args[0].full_url).query)
        self.assertEqual(query["from"], ["20150101"])
        self.assertEqual(query["to"], ["20260922"])
        self.assertNotIn("collapse", query)
        self.assertEqual(rows[0]["year"], "2015")
        self.assertEqual(status["crawl_status"], "found_unverified")

    def test_failed_archive_batch_preserves_prior_discoveries_and_untouched_statuses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            chapters = [
                {"record_id": key, "Name": key, "State": "NY", "Website": f"https://{key}.org"}
                for key in ("old", "new")
            ]
            write_csv(root / "chapter_directory.csv", chapters, list(chapters[0]))
            prior = _status(chapters[0], "found_unverified", matching_urls=1)
            write_csv(root / "wayback_crawl_status.csv", [prior], list(prior))
            archive = {
                "archive_id": "a", "chapter_record_id": "old", "chapter": "old", "state": "NY",
                "timestamp": "20150101000000", "year": "2015", "url": "https://old.org/endorse",
                "digest": "d", "archive_url": "https://web.archive.org/example",
                "review_status": "verified",
            }
            write_csv(root / "wayback_endorsement_urls.csv", [archive], list(archive))
            with (
                patch("dsa_analysis.wayback_crawler.PROCESSED_DIR", root),
                patch("dsa_analysis.wayback_crawler._discover_chapter",
                      return_value=([], _status(chapters[1], "source_unavailable",
                                                error="network timeout"))),
                patch("dsa_analysis.wayback_crawler.time.sleep"),
            ):
                checked, retained = discover_wayback_urls(workers=1, limit=1, timeout=5)
            self.assertEqual((checked, retained), (1, 1))
            self.assertEqual(read_csv(root / "wayback_endorsement_urls.csv"), [archive])
            self.assertEqual(len(read_csv(root / "wayback_crawl_status.csv")), 2)


if __name__ == "__main__":
    unittest.main()
