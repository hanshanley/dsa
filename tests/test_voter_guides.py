import unittest

from dsa_analysis.voter_guides import _district_near, _office_hint


class VoterGuideTests(unittest.TestCase):
    def test_district_detection(self) -> None:
        self.assertEqual(_district_near("Candidate District 9 Opposed", 0), "District 9")

    def test_office_hint(self) -> None:
        self.assertEqual(
            _office_hint("A City Council contest in Los Angeles", "District 9"),
            "City Council District 9",
        )


if __name__ == "__main__":
    unittest.main()
