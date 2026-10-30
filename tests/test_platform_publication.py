import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_platform_publication import (
    DATA,
    WEBSITE_FIGURES,
    digest,
    evolution_data,
    export,
    validate,
)


class PlatformPublicationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name) / "source"
        self.data = self.source / DATA
        (self.data / "topics").mkdir(parents=True)
        claims = [
            dict(claim_id=group, group=group, claim_text="A policy claim.", evidence="Source text.")
            for group in ("democratic", "republican", "dsa")
        ]
        self.write_csv("analysis_claims.csv", claims)
        self.write_csv("claims.csv", claims)
        self.write_csv(
            "complete_sources.csv",
            [dict(group=row["group"], complete_text="Complete policy document.") for row in claims],
        )
        self.write_csv(
            "topics/representatives.csv", [dict(topic_id="topic-001", claim_id="democratic")]
        )
        self.write_csv("topics/shares.csv", [dict(topic_id="topic-001", share="1")])
        self.write_json(
            "topics/topic_labels.json",
            [
                dict(
                    topic_id="topic-001",
                    review_status="evidence_reviewed",
                    supporting_claim_ids=["democratic"],
                )
            ],
        )
        self.write_json(
            "topics/summary.json",
            dict(
                claims=3,
                groups=["democratic", "republican", "dsa"],
                labeling_status="complete",
                topics=1,
                reviewed_labels=1,
                fit_manifest_sha256="fit",
            ),
        )
        self.write_json(
            "analysis_summary.json",
            dict(
                claims=3,
                claims_by_group={row["group"]: 1 for row in claims},
                documents_by_group={row["group"]: 1 for row in claims},
                claims_sha256=digest(self.data / "claims.csv"),
                complete_sources_sha256=digest(self.data / "complete_sources.csv"),
                corpus=dict(status="complete"),
            ),
        )
        self.write_json(
            "topics/replay_audit.json",
            dict(
                status="complete",
                label_inference_called=False,
                numerical_cache_reused=True,
                claims=3,
                reviewed_labels=1,
                fit_manifest_sha256="fit",
                substantive_artifacts_sha256={
                    (DATA / "topics/topic_labels.json").as_posix(): digest(
                        self.data / "topics/topic_labels.json"
                    )
                },
            ),
        )
        self.archive()

    def write_json(self, name, value):
        (self.data / name).write_text(json.dumps(value), encoding="utf-8")

    def write_csv(self, name, records):
        with (self.data / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)

    def archive(self):
        with zipfile.ZipFile(self.data / "claim_documents.zip", "w") as archive:
            for name in [
                "analysis_claims.csv",
                "complete_sources.csv",
                "topics/topic_labels.json",
                "topics/shares.csv",
                "topics/representatives.csv",
            ]:
                archive.write(self.data / name, name)

    def test_completed_corpus_contains_claim_wording_and_source_evidence(self):
        summary, _, labels, representatives, _ = validate(self.source)
        self.assertEqual(summary["claims"], 3)
        self.assertEqual(labels[0]["supporting_claim_ids"], [representatives[0]["claim_id"]])

    def test_unfinished_labels_are_rejected(self):
        summary = json.loads((self.data / "topics/summary.json").read_text())
        summary["labeling_status"] = "pending"
        self.write_json("topics/summary.json", summary)
        with self.assertRaisesRegex(ValueError, "completed, reviewed"):
            validate(self.source)

    def test_changed_reviewed_artifact_is_rejected(self):
        with (self.data / "topics/topic_labels.json").open("a") as stream:
            stream.write(" ")
        with self.assertRaisesRegex(ValueError, "Replay artifact changed"):
            validate(self.source)

    def test_metadata_only_analysis_is_rejected(self):
        self.write_csv(
            "analysis_claims.csv",
            [dict(claim_id="democratic", group="democratic", claim_text="", evidence="")],
        )
        with self.assertRaisesRegex(ValueError, "actual claims and evidence"):
            validate(self.source)

    def test_stale_combined_download_is_rejected(self):
        self.write_csv("topics/shares.csv", [dict(topic_id="topic-001", share="0.5")])
        with self.assertRaisesRegex(ValueError, "stale content"):
            validate(self.source)

    def test_source_and_existing_outputs_are_not_overwritten(self):
        with self.assertRaisesRegex(ValueError, "outside the source"):
            export(self.source, self.source / "publication")
        output = Path(self.tmp.name) / "existing"
        output.mkdir()
        (output / "keep.txt").write_text("Keep existing work.")
        with self.assertRaisesRegex(ValueError, "absent or empty"):
            export(self.source, output)
        self.assertEqual((output / "keep.txt").read_text(), "Keep existing work.")

    def test_partial_period_labels_are_not_published(self):
        (self.data / "topics/evolution").mkdir()
        self.write_json(
            "topics/evolution/summary.json",
            dict(status="complete", topics=2, labels_available=1, reviewed_labels=0),
        )
        self.write_json(
            "topics/evolution/topic_labels.json",
            [dict(topic_id="period-2000-topic-001", review_status="unreviewed")],
        )
        self.write_json("topics/evolution/period_fits.json", [])
        with self.assertRaisesRegex(ValueError, "complete with accurate review status"):
            evolution_data(self.source)

    def test_unarchived_website_variants_are_rejected(self):
        path = self.source / WEBSITE_FIGURES / "expanded/topic_distribution.png"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"Changed website variant")
        with self.assertRaisesRegex(ValueError, "stale website figure"):
            validate(self.source)


if __name__ == "__main__":
    unittest.main()
