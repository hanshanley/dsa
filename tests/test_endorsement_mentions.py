import unittest

from dsa_analysis.endorsement_mentions import ENDORSEMENT_PATTERN, YEAR_PATTERN


class EndorsementMentionTests(unittest.TestCase):
    def test_endorsement_variants(self) -> None:
        self.assertIsNotNone(ENDORSEMENT_PATTERN.search("We endorsed Jane Doe."))
        self.assertIsNotNone(ENDORSEMENT_PATTERN.search("Current endorsements"))

    def test_year_detection(self) -> None:
        self.assertEqual(YEAR_PATTERN.findall("2015 2016 2024 2027"), ["2016", "2024"])


if __name__ == "__main__":
    unittest.main()
