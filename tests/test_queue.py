import unittest

from dsa_analysis.paths import PROCESSED_DIR
from dsa_analysis.queue import build_research_queue


@unittest.skipUnless(
    (PROCESSED_DIR / "national_endorsement_archive.csv").exists()
    and (PROCESSED_DIR / "chapter_directory.csv").exists(),
    "official Airtable sources have not been collected",
)
class QueueTests(unittest.TestCase):
    def test_queue_builds_from_collected_sources(self) -> None:
        candidates, coverage = build_research_queue()
        self.assertGreater(candidates, 250)
        self.assertGreater(coverage, 2000)


if __name__ == "__main__":
    unittest.main()
