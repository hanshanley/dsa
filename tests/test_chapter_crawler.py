import unittest

from dsa_analysis.chapter_crawler import (
    has_discovery_term,
    is_endorsement_page,
    normalize_url,
    parse_sitemap,
    parse_wordpress_search,
)


class ChapterCrawlerTests(unittest.TestCase):
    def test_url_normalization(self) -> None:
        self.assertEqual(normalize_url("example.org"), "https://example.org/")

    def test_discovery_terms(self) -> None:
        self.assertTrue(has_discovery_term("/2024-endorsements/"))
        self.assertFalse(has_discovery_term("/about-us/"))

    def test_endorsement_text_detection(self) -> None:
        self.assertTrue(is_endorsement_page("2024 slate", "We endorsed Jane Doe."))
        self.assertFalse(is_endorsement_page("About", "Chapter history and bylaws."))

    def test_wordpress_search_parser(self) -> None:
        value = '[{"url":"https://example.org/endorsements/"}]'
        self.assertEqual(
            parse_wordpress_search(value),
            ["https://example.org/endorsements/"],
        )

    def test_sitemap_parser(self) -> None:
        self.assertEqual(
            parse_sitemap("<url><loc>https://example.org/a</loc></url>"),
            ["https://example.org/a"],
        )


if __name__ == "__main__":
    unittest.main()
