import unittest

from dsa_analysis.airtable import decode_value


class AirtableTests(unittest.TestCase):
    def test_select_values_are_decoded(self) -> None:
        column = {
            "type": "select",
            "typeOptions": {
                "choices": {"sel1": {"id": "sel1", "name": "Endorsed 2020"}}
            },
        }
        self.assertEqual(decode_value(column, "sel1"), "Endorsed 2020")

    def test_foreign_keys_use_display_names(self) -> None:
        column = {"type": "foreignKey"}
        value = [{"foreignRowId": "rec1", "foreignRowDisplayName": "New York City"}]
        self.assertEqual(decode_value(column, value), ["New York City"])


if __name__ == "__main__":
    unittest.main()
