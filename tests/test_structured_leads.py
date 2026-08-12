import unittest

from dsa_analysis.structured_leads import parse_leads


class StructuredLeadTests(unittest.TestCase):
    def test_direct_endorsement(self) -> None:
        text = (
            "Tucson DSA endorses Sadie Shaw's campaign "
            "for Tucson City Council Ward 3."
        )
        self.assertEqual(
            parse_leads(text),
            [("Sadie Shaw", "Tucson City Council Ward 3")],
        )

    def test_multiple_candidates(self) -> None:
        text = (
            "Milwaukee DSA endorsed two candidates: Ryan Clancy for Wisconsin "
            "State Assembly District 19 and Darrin Madison for Wisconsin State "
            "Assembly District 10."
        )
        self.assertEqual(len(parse_leads(text)), 2)


if __name__ == "__main__":
    unittest.main()
