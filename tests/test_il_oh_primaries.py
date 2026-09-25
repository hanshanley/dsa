import csv
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from dsa_analysis.il_oh_primaries import (
    parse_illinois_results,
    parse_ohio_results,
)


class IllinoisOhioPrimaryTests(unittest.TestCase):
    def test_illinois_parser_preserves_unopposed_and_write_in_status(self):
        html = """
        <div class="gridview-title-bar">
          <div><div>1ST CONGRESS</div></div>
          <a>Download Results</a>
        </div>
        <div class="gridview-container"><table>
          <tr><th>Candidate</th><th>Party</th><th>Total Votes</th><th>Percent</th></tr>
          <tr><td><a href="CandidateDetailEO.aspx?CandidateID=ballot&amp;x=1">
          Ballot Candidate</a></td><td>DEMOCRATIC</td><td>1,234</td><td>100%</td></tr>
          <tr><td><a href="CandidateDetailEO.aspx?CandidateID=writein&amp;x=1">
          Named Write-In</a></td><td>REPUBLICAN</td><td>3</td><td>100%</td></tr>
          <tr><td>Vote Totals</td><td></td><td>1,237</td><td></td></tr>
        </table></div>
        """
        detail_fields = [
            "cycle", "contest_name", "candidate_name", "candidate_source_id",
            "party", "write_in", "source_url", "raw_filename", "raw_sha256",
        ]
        detail_rows = [
            {
                "cycle": "2024", "contest_name": "1ST CONGRESS",
                "candidate_name": "Ballot Candidate", "candidate_source_id": "ballot",
                "party": "DEMOCRATIC", "write_in": "No", "source_url": "",
                "raw_filename": "", "raw_sha256": "",
            },
            {
                "cycle": "2024", "contest_name": "1ST CONGRESS",
                "candidate_name": "Named Write-In", "candidate_source_id": "writein",
                "party": "REPUBLICAN", "write_in": "Yes", "source_url": "",
                "raw_filename": "", "raw_sha256": "",
            },
        ]
        source = {
            "source_id": "il-test",
            "date": "2024-03-19",
            "url": "https://example.test/illinois",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "results.html"
            page.write_text(html)
            details = root / "details.csv"
            with details.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=detail_fields)
                writer.writeheader()
                writer.writerows(detail_rows)
            with self.assertRaises(ValueError):
                parse_illinois_results(page, details, source)

            # Add the other 16 districts to satisfy statewide coverage validation.
            additions = []
            extra_details = []
            for district in range(2, 18):
                additions.append(
                    f'<div class="gridview-title-bar"><div>{district}TH CONGRESS</div>'
                    f'</div><div><table><tr><td><a href="CandidateDetailEO.aspx?'
                    f'CandidateID=id{district}">Candidate {district}</a></td>'
                    '<td>DEMOCRATIC</td><td>10</td><td>100%</td></tr></table></div>'
                )
                extra_details.append({
                    "cycle": "2024", "contest_name": f"{district}TH CONGRESS",
                    "candidate_name": f"Candidate {district}",
                    "candidate_source_id": f"id{district}", "party": "DEMOCRATIC",
                    "write_in": "No", "source_url": "", "raw_filename": "",
                    "raw_sha256": "",
                })
            page.write_text(html + "".join(additions))
            with details.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=detail_fields)
                writer.writeheader()
                writer.writerows(detail_rows + extra_details)
            rows = parse_illinois_results(page, details, source)
        write_in = next(row for row in rows if row["candidate_name"] == "Named Write-In")
        self.assertTrue(write_in["write_in"])
        self.assertEqual(write_in["party"], "")
        self.assertEqual(write_in["primary_party"], "Republican")

    def test_ohio_parser_distinguishes_regular_and_special_house_primaries(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "U.S. Congress"
        sheet.append([
            "Election", None, None, None, None, None,
            "U.S. Senator", "Representative to Congress - District 01",
            "Representative to Congress - District 06\nUnexpired Term Ending 01/03/2025",
        ])
        sheet.append([
            "County Name", None, None, None, None, None,
            "Example Senator (D)", "Example House (D)", "Special Candidate (D)",
        ])
        sheet.append(["Total", None, None, None, None, None, 100, 200, 300])
        source = {
            "source_id": "oh-test",
            "date": "2024-03-19",
            "party": "Democratic",
            "url": "https://example.test/ohio.xlsx",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ohio.xlsx"
            workbook.save(path)
            rows = parse_ohio_results(path, source)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["chamber"], "Senate")
        special = next(row for row in rows if row["term"] == "special")
        self.assertEqual(special["district"], "06")
        self.assertEqual(special["votes"], 300)


if __name__ == "__main__":
    unittest.main()
