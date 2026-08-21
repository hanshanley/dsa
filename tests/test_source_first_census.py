import unittest

from dsa_analysis.io import read_csv
from dsa_analysis.paths import ANALYSIS_DATA_DIR, MANUAL_DIR


class SourceFirstCensusTests(unittest.TestCase):
    def test_mike_sylvester_2016_verified_primary_is_in_manual_census(self) -> None:
        documents = {row["document_id"]: row for row in read_csv(MANUAL_DIR / "documents.csv")}
        candidate_documents = {
            row["candidate_document_id"]: row
            for row in read_csv(MANUAL_DIR / "candidate_documents.csv")
        }
        endorsements = read_csv(MANUAL_DIR / "endorsements.csv")
        race_candidates = read_csv(MANUAL_DIR / "race_candidates.csv")

        self.assertIn("dsa-members-run-office-2016", documents)
        self.assertIn("maine-strep-dem-primary-2016-results", documents)
        self.assertEqual(
            documents["maine-strep-dem-primary-2016-results"]["url"],
            "https://www.maine.gov/sos/cec/elec/results/2016/June16/STREPDEM.xlsx",
        )

        sylvester = next(
            row for row in endorsements if row["endorsement_id"] == "endorsement-mike-sylvester-2016"
        )
        self.assertEqual(sylvester["race_id"], "me-house-39-dem-primary-2016")
        self.assertEqual(sylvester["candidate_name"], "Mike Sylvester")
        self.assertEqual(sylvester["endorsement_source_document_id"], "dsa-members-run-office-2016")
        self.assertEqual(sylvester["election_date"], "2016-06-14")

        roster = [
            row
            for row in race_candidates
            if row["race_id"] == "me-house-39-dem-primary-2016"
        ]
        self.assertEqual(len(roster), 2)
        self.assertEqual({row["candidate_name"] for row in roster}, {"Mike Sylvester", "Andrew Edwards"})
        self.assertEqual({row["role"] for row in roster}, {"endorsed", "opponent"})
        self.assertEqual(
            {row["candidate_name"]: row["source_url"] for row in roster},
            {
                "Mike Sylvester": documents["maine-strep-dem-primary-2016-results"]["url"],
                "Andrew Edwards": documents["maine-strep-dem-primary-2016-results"]["url"],
            },
        )
        self.assertEqual(
            documents["dsa-members-run-office-2016"]["url"],
            "https://www.dsausa.org/blog/dsa_members_run_for_office_to_continue_the_political_revolution_dl/",
        )
        self.assertEqual(
            candidate_documents["candidate-doc-portland-profile-sylvester-2016"]["locator"],
            "from: Sylvester, 46",
        )
        self.assertEqual(
            candidate_documents["candidate-doc-portland-profile-edwards-2016"]["source_url"],
            "https://web.archive.org/web/20160607163830/http://www.pressherald.com/2016/05/30/hd-39-newcomers-seek-house-nomination/",
        )
        self.assertEqual(
            candidate_documents["candidate-doc-andrew-edwards-ballotpedia-2016"]["analysis_scope"],
            "context_only",
        )

    def test_mike_connolly_2016_verified_primary_is_in_manual_census_and_retained_in_snapshot(self) -> None:
        documents = {row["document_id"]: row for row in read_csv(MANUAL_DIR / "documents.csv")}
        candidate_documents = {
            row["candidate_document_id"]: row
            for row in read_csv(MANUAL_DIR / "candidate_documents.csv")
        }
        endorsements = read_csv(MANUAL_DIR / "endorsements.csv")
        race_candidates = read_csv(MANUAL_DIR / "race_candidates.csv")
        corpus = read_csv(ANALYSIS_DATA_DIR / "candidate_text_corpus.csv")

        self.assertIn("boston-dsa-mike-connolly-confirmation-2023", documents)
        self.assertIn("ma-26th-middlesex-dem-primary-2016-results", documents)
        self.assertIn("mike-connolly-progressive-platform-2016", documents)
        self.assertEqual(
            documents["ma-26th-middlesex-dem-primary-2016-results"]["url"],
            "https://electionstats.state.ma.us/elections/view/129704",
        )
        self.assertEqual(
            documents["mike-connolly-progressive-platform-2016"]["archive_url"],
            "http://web.archive.org/web/20160807044232/http://www.mikeconnolly.org:80/progressive_platform",
        )
        self.assertEqual(
            documents["mike-connolly-progressive-platform-2016"]["url"],
            "http://www.mikeconnolly.org/progressive_platform",
        )

        connolly = next(
            row for row in endorsements if row["endorsement_id"] == "endorsement-mike-connolly-2016"
        )
        self.assertEqual(connolly["race_id"], "ma-house-26th-middlesex-dem-primary-2016")
        self.assertEqual(connolly["candidate_name"], "Mike Connolly")
        self.assertEqual(
            connolly["endorsement_source_document_id"],
            "boston-dsa-mike-connolly-confirmation-2023",
        )
        self.assertEqual(connolly["endorsing_body"], "Boston DSA")
        self.assertEqual(connolly["election_date"], "2016-09-08")

        roster = [
            row
            for row in race_candidates
            if row["race_id"] == "ma-house-26th-middlesex-dem-primary-2016"
        ]
        self.assertEqual(len(roster), 2)
        self.assertEqual(
            {row["candidate_name"] for row in roster},
            {"Mike Connolly", "Timothy J. Toomey, Jr."},
        )
        self.assertEqual({row["role"] for row in roster}, {"endorsed", "opponent"})
        self.assertEqual(
            {row["candidate_name"]: row["source_url"] for row in roster},
            {
                "Mike Connolly": documents["ma-26th-middlesex-dem-primary-2016-results"]["url"],
                "Timothy J. Toomey, Jr.": documents["ma-26th-middlesex-dem-primary-2016-results"]["url"],
            },
        )
        self.assertEqual(
            candidate_documents["candidate-doc-mike-connolly-platform-2016"]["source_url"],
            "http://web.archive.org/web/20160807044232/http://www.mikeconnolly.org:80/progressive_platform",
        )
        self.assertEqual(
            candidate_documents["candidate-doc-mike-connolly-sierra-club-2016"]["source_url"],
            "http://web.archive.org/web/20160830204857/http://www.mikeconnolly.org:80/endorsed_by_sierra_club_massachusetts",
        )
        self.assertEqual(
            candidate_documents["candidate-doc-mike-connolly-scatv-2016"]["source_url"],
            "http://web.archive.org/web/20160828215944/http://www.mikeconnolly.org:80/mike_connolly_scatv",
        )
        self.assertEqual(
            candidate_documents["candidate-doc-tim-toomey-homepage-2016"]["source_url"],
            "https://web.archive.org/web/20160828203156/https://timtoomey.org/",
        )
        self.assertEqual(
            candidate_documents["candidate-doc-tim-toomey-transportation-2016"]["live_url"],
            "https://timtoomey.org/transportation/",
        )
        self.assertEqual(
            candidate_documents["candidate-doc-debate-srt-connolly-2016"]["locator"],
            "time 00:02:21,220-00:03:21,260 | time 00:56:53,950-00:57:31,540",
        )

        self.assertTrue(
            any(
                row["candidate_name"] == "Mike Connolly"
                and row["election_date"] == "2016-09-08"
                for row in corpus
            )
        )

    def test_presidential_expansion_is_manual_but_debbie_medina_is_not(self) -> None:
        endorsements = read_csv(MANUAL_DIR / "endorsements.csv")
        names = {row["candidate_name"] for row in endorsements}
        self.assertNotIn("Debbie Medina", names)
        self.assertIn("Bernie Sanders", names)


if __name__ == "__main__":
    unittest.main()
