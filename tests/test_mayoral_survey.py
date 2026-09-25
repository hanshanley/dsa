import unittest

from dsa_analysis.mayoral_survey import parse_response


class MayoralSurveyTests(unittest.TestCase):
    def test_no_code_preserves_substantive_explanation(self):
        q = {"option1": "First", "option2": "Second"}
        code, label, explanation, reference = parse_response(
            "0 | The candidate supplied a <strong>different</strong> approach. | Candidate statement", q,
        )
        self.assertEqual(code, "0")
        self.assertEqual(label, "")
        self.assertEqual(explanation, "The candidate supplied a different approach.")
        self.assertEqual(reference, "Candidate statement")

    def test_undefined_options_and_unknown_codes_fail_explicitly(self):
        with self.assertRaisesRegex(ValueError, "undefined option"):
            parse_response("3 | Some explanation", {"option1": "First"})
        with self.assertRaisesRegex(ValueError, "Unknown publisher response"):
            parse_response("not-a-code | Some explanation", {"option1": "First"})

    def test_option_is_not_substituted_for_candidate_words(self):
        code, label, explanation, reference = parse_response("1", {"option1": "Publisher option wording"})
        self.assertEqual(label, "Publisher option wording")
        self.assertEqual((explanation, reference), ("", ""))


if __name__ == "__main__":
    unittest.main()
