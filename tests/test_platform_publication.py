import base64
import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.build_platform_publication import (
    DATA,
    FIGURES,
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
            for figure in (self.source / FIGURES).rglob("*"):
                if figure.is_file():
                    archive.write(
                        figure, f"figures/topics/{figure.relative_to(self.source / FIGURES)}"
                    )

    def prepare_export(self, omitted=()):
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
        )
        audit = json.loads((self.data / "topics/replay_audit.json").read_text())
        for view in ("expanded", "strict"):
            for name in (
                "topic_distribution",
                "vs_rest_emphasis",
                "pairwise_emphasis",
                "issues/topic-001_overall",
                "issues/topic-001_time",
            ):
                for suffix in (".png", ".svg"):
                    relative = f"{view}/{name}{suffix}"
                    if relative in omitted:
                        continue
                    figure = self.source / FIGURES / relative
                    figure.parent.mkdir(parents=True, exist_ok=True)
                    figure.write_bytes(png if suffix == ".png" else b'<svg width="1" height="1"/>')
                    audit["substantive_artifacts_sha256"][
                        figure.relative_to(self.source).as_posix()
                    ] = digest(figure)
        self.write_json("topics/replay_audit.json", audit)
        for name in (
            "claims.jsonl",
            "source_coverage.csv",
            "topics/contrasts.csv",
            "topics/temporal_shares.csv",
            "topics/temporal_contrasts.csv",
            "topics/temporal_coverage.csv",
            "topics/label_review.json",
            "topics/candidate_fits.csv",
            "topics/balanced_refits.csv",
        ):
            (self.data / name).write_text("{}\n" if name.endswith(".json") else "")
        (self.source / "report").mkdir()
        (self.source / "report/national_claim_analysis.md").write_text("Fixture methods.")
        self.archive()

    def test_issue_figures_export_with_originals_and_hashes(self):
        self.prepare_export()
        output = Path(self.tmp.name) / "publication"
        with patch(
            "scripts.build_platform_publication.subprocess.check_output", side_effect=["", "a" * 40]
        ):
            manifest = export(self.source, output)
        publication = json.loads((output / "analysis.json").read_text())
        issue_figures = [figure for figure in publication["figures"] if "/issues" in figure["view"]]
        self.assertEqual(len(issue_figures), 4)
        for figure in issue_figures:
            path = figure["path"]
            original = self.source / FIGURES / Path(path).relative_to("figures")
            self.assertEqual((output / path).read_bytes(), original.read_bytes())
            self.assertEqual(manifest["files"][path], digest(original))
            self.assertTrue((output / path.replace(".png", ".svg")).is_file())

    def test_missing_issue_scope_is_rejected_without_partial_output(self):
        self.prepare_export(
            omitted=("strict/issues/topic-001_time.png", "strict/issues/topic-001_time.svg")
        )
        output = Path(self.tmp.name) / "publication"
        with patch(
            "scripts.build_platform_publication.subprocess.check_output", side_effect=["", "a" * 40]
        ):
            with self.assertRaisesRegex(ValueError, "issue-level comparison charts"):
                export(self.source, output)
        self.assertFalse(output.exists())
        self.assertEqual(list(output.parent.glob(".platform-publication-*")), [])

    def test_missing_original_svg_is_rejected(self):
        self.prepare_export(omitted=("strict/issues/topic-001_time.svg",))
        with patch(
            "scripts.build_platform_publication.subprocess.check_output", side_effect=["", "a" * 40]
        ):
            with self.assertRaisesRegex(ValueError, "original SVG"):
                export(self.source, Path(self.tmp.name) / "publication")

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
