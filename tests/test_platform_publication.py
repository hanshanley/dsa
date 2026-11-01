import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.build_dsa_article_lead import (
    combined_density_contrast,
    rank_attention_gaps,
    rank_density_areas,
    render_variant,
    snippet_records,
)
from scripts.build_platform_publication import (
    DATA,
    FIGURES,
    WEBSITE_FIGURES,
    density_map_data,
    digest,
    evolution_data,
    export,
    validate,
)


class ArticleLeadTest(unittest.TestCase):
    def test_lead_bars_show_geometric_density_ratios_in_ranked_order(self):
        import math

        from matplotlib.figure import Figure

        records = [
            dict(
                title=title,
                mean_log_density_contrast=math.log(value),
                density_ratio=value,
                snippet="Demilitarize police departments.",
                source_date="2024-08",
                document_type="program",
            )
            for title, value in (
                ("Institutional Power, Oppression, and Social Conflict", 8),
                ("Criminal Justice, Policing, and Incarceration", 4),
            )
        ]

        def check_figure(figure, *args, **kwargs):
            axis = figure.axes[0]
            self.assertEqual(len(axis.patches), 2)
            for bar, expected in zip(axis.patches, (8, 4)):
                self.assertAlmostEqual(bar.get_width(), expected)
            self.assertTrue(axis.yaxis_inverted())
            self.assertEqual(list(axis.lines[0].get_xdata()), [1, 1])
            self.assertEqual([text.get_text() for text in axis.texts], ["8.0×", "4.0×"])

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(Figure, "savefig", autospec=True, side_effect=check_figure):
                render_variant(records, Path(directory) / "lead.png", "bars")

    def test_snippets_reject_changed_central_claim_wording(self):
        claim = dict(
            claim_id="dsa-2024-program-normalized-b789b4710c28-006",
            group="dsa",
            analysis_eligible="True",
            claim_text="Support for militarizing police departments.",
        )
        with self.assertRaisesRegex(ValueError, "Changed claim text"):
            snippet_records([dict(anchor_claim_id=claim["claim_id"])], [claim])

    def test_combined_density_uses_arithmetic_mixture_and_stays_finite(self):
        import math

        self.assertAlmostEqual(
            combined_density_contrast([None, 0, 0, 0, 2, math.log(2), math.log(8), math.log(5)]),
            0,
        )
        self.assertAlmostEqual(
            combined_density_contrast([None, 0, 0, 0, 2, -10000, -10002, -9999]),
            1 + math.log(2) - math.log1p(math.exp(-2)),
        )

    def test_density_ranking_keeps_original_bundle_weights_and_only_supported_positive_issues(self):
        records = [
            ("a1", 0, "large", 4),
            ("a2", 0, "small", 0),
            ("b1", 1, "large", 100),
            ("b2", 1, "large", 100),
            ("b3", 1, "large", 100),
            ("i1", 2, "identity-one", 200),
            ("i2", 2, "identity-two", 200),
            ("n1", 3, "negative-one", -2),
            ("n2", 3, "negative-two", -2),
        ]
        claims = [
            dict(claim_id=claim, group="dsa", bundle_id=bundle, source_url="https://www.dsausa.org")
            for claim, _, bundle, _ in records
        ]
        data = dict(
            groups=["democratic", "republican", "dsa"],
            limits=[[0, 10], [0, 10]],
            points=[
                [claim, index, index, topic, 2, 0, 0, contrast]
                for index, (claim, topic, _, contrast) in enumerate(records)
            ],
            topics=[
                dict(
                    topic_id=name,
                    title=name,
                    displayed=name != "identity",
                    examples=[
                        dict(claim_id=claim, group="dsa")
                        for claim, topic, _, _ in records
                        if topic == index
                    ],
                )
                for index, name in enumerate(("balanced", "single-bundle", "identity", "negative"))
            ],
        )
        ranked = rank_density_areas(data, claims)
        self.assertEqual([record["topic_id"] for record in ranked], ["balanced"])
        self.assertAlmostEqual(ranked[0]["mean_log_density_contrast"], 0.8)
        self.assertEqual(ranked[0]["dsa_bundles"], 2)
        self.assertEqual(ranked[0]["anchor_claim_id"], "a1")
        self.assertGreater(ranked[0]["anchor_log_density_contrast"], 0)
        data["points"][0][0] = "foreign"
        with self.assertRaisesRegex(ValueError, "exact unique claim membership"):
            rank_density_areas(data, claims)

    def test_largest_absolute_gaps_include_less_attention_and_exclude_identity(self):
        labels = [
            dict(topic_id=topic, title=topic, displayed=topic != "identity")
            for topic in ("one", "two", "three", "identity")
        ]
        values = {
            "one": (0.02, 0.04, 0.20),
            "two": (0.20, 0.20, 0.05),
            "three": (0.02, 0.02, 0.08),
            "identity": (0.001, 0.001, 0.99),
        }
        rows = [
            dict(view="expanded", group=group, topic_id=topic, available="True", share=str(value))
            for topic, shares in values.items()
            for group, value in zip(("democratic", "republican", "dsa"), shares)
        ]
        rows.append(dict(view="strict", group="dsa", topic_id="three", available="True", share="1"))
        ranked = rank_attention_gaps(labels, rows)
        self.assertEqual([row["topic_id"] for row in ranked], ["one", "two", "three"])
        self.assertAlmostEqual(ranked[0]["combined_share"], 0.03)
        for record, gap in zip(ranked, (0.17, -0.15, 0.06)):
            self.assertAlmostEqual(record["gap"], gap)
        self.assertEqual(ranked[0]["shares"]["dsa"], 0.20)

    def test_missing_party_cannot_be_silently_ranked(self):
        with self.assertRaisesRegex(ValueError, "Missing observed party shares"):
            rank_attention_gaps(
                [dict(topic_id="one", title="One")],
                [dict(view="expanded", group="dsa", topic_id="one", available="True", share="0.2")],
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
        (self.data / "expanded").mkdir()
        self.write_csv(
            "topics/assignments.csv",
            [
                dict(claim_id=row["claim_id"], topic_id="topic-001", group=row["group"])
                for row in claims
            ],
        )
        self.write_csv(
            "expanded/scored_passages.csv",
            [
                dict(
                    claim_id=row["claim_id"],
                    group=row["group"],
                    umap_x=index + 0.25,
                    umap_y=index + 0.5,
                    democratic_log_density=-1,
                    republican_log_density=-2,
                    dsa_log_density=-3,
                )
                for index, row in enumerate(claims)
            ],
        )
        (self.data / "expanded/density_region_evidence.csv").write_text("color_bound\n")
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

    def test_density_positions_preserve_reviewed_summaries_and_support(self):
        (self.data / "topics/positions").mkdir()
        groups = {
            group: dict(
                summary=f"{group} source position.",
                caveat="Selected evidence.",
                supporting_claim_ids=[group],
            )
            for group in ("democratic", "republican", "dsa")
        }
        pairs = {
            "democratic_vs_republican": dict(
                summary="Reviewed contrast.", supporting_claim_ids=["democratic", "republican"]
            )
        }
        self.write_json(
            "topics/positions/group_positions.json",
            [dict(topic_id="topic-001", groups=groups, pairs=pairs)],
        )
        labels = json.loads((self.data / "topics/topic_labels.json").read_text())
        topic = density_map_data(self.source, labels, [])["topics"][0]
        self.assertEqual(topic["positions"], groups)
        self.assertEqual(topic["differences"], pairs)
        self.assertEqual({example["claim_id"] for example in topic["examples"]}, set(groups))
        groups["democratic"]["supporting_claim_ids"] = ["dsa"]
        self.write_json(
            "topics/positions/group_positions.json",
            [dict(topic_id="topic-001", groups=groups, pairs=pairs)],
        )
        with self.assertRaisesRegex(ValueError, "evidence issue/group mismatch"):
            density_map_data(self.source, labels, [])

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
            for figure in (self.source / FIGURES.parent).rglob("*"):
                if figure.is_file():
                    archive.write(
                        figure, f"figures/{figure.relative_to(self.source / FIGURES.parent)}"
                    )

    def prepare_export(self, omitted=()):
        from PIL import Image

        image = io.BytesIO()
        Image.new("RGB", (1, 1)).save(image, format="PNG")
        png = image.getvalue()
        audit = json.loads((self.data / "topics/replay_audit.json").read_text())
        for view in ("expanded", "strict"):
            for name in (
                "topic_distribution",
                "vs_rest_emphasis",
                "pairwise_emphasis",
                "issues/topic-001_overall",
                "issues/topic-001_time",
            ):
                for suffix in (".png",):
                    relative = f"{view}/{name}{suffix}"
                    if relative in omitted:
                        continue
                    figure = self.source / FIGURES / relative
                    figure.parent.mkdir(parents=True, exist_ok=True)
                    figure.write_bytes(png)
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
        self.assertEqual(publication["density_regions"], [])
        issue_figures = [figure for figure in publication["figures"] if "/issues" in figure["view"]]
        self.assertEqual(len(issue_figures), 4)
        for figure in issue_figures:
            path = figure["path"]
            original = self.source / FIGURES / Path(path).relative_to("figures")
            self.assertEqual((output / path).read_bytes(), original.read_bytes())
            self.assertEqual(manifest["files"][path], digest(original))
            self.assertFalse((output / path.replace(".png", ".svg")).exists())
        self.assertFalse(list(output.rglob("*.svg")))

    def test_complete_archive_rebuilds_offline_and_checks_published_checksum(self):
        from dsa_analysis.national_claim_corpus import bundle

        self.prepare_export()
        bundle(
            self.data,
            figures=self.source / FIGURES.parent,
            report=self.source / "report/national_claim_analysis.md",
        )
        original = (self.data / "claim_documents.zip").read_bytes()
        (self.data / "claim_documents.zip").unlink()
        validate(self.source)
        self.assertEqual((self.data / "claim_documents.zip").read_bytes(), original)
        metadata = json.loads((self.data / "claim_documents.download.json").read_text())
        metadata["sha256"] = "wrong"
        self.write_json("claim_documents.download.json", metadata)
        with self.assertRaisesRegex(ValueError, "archive checksum"):
            validate(self.source)

    def test_excluded_labels_stay_in_downloads_but_not_publication_topics(self):
        self.prepare_export()
        labels = json.loads((self.data / "topics/topic_labels.json").read_text())
        labels.append(
            {**labels[0], "topic_id": "identity", "displayed": False, "supporting_claim_ids": []}
        )
        self.write_json("topics/topic_labels.json", labels)
        with (self.data / "topics/representatives.csv").open() as stream:
            representatives = list(csv.DictReader(stream))
        self.write_csv("topics/representatives.csv", representatives)
        summary = json.loads((self.data / "topics/summary.json").read_text())
        summary.update(topics=2, reviewed_labels=2)
        self.write_json("topics/summary.json", summary)
        audit = json.loads((self.data / "topics/replay_audit.json").read_text())
        audit["reviewed_labels"] = 2
        for relative in audit["substantive_artifacts_sha256"]:
            audit["substantive_artifacts_sha256"][relative] = digest(self.source / relative)
        self.write_json("topics/replay_audit.json", audit)
        self.archive()
        output = Path(self.tmp.name) / "publication"
        with patch(
            "scripts.build_platform_publication.subprocess.check_output", side_effect=["", "a" * 40]
        ):
            export(self.source, output)
        self.assertEqual(len(json.loads((output / "analysis.json").read_text())["topics"]), 1)
        archived_labels = json.loads((output / "downloads/topics/topic_labels.json").read_text())
        self.assertEqual(len(archived_labels), 2)

    def test_detailed_density_figures_and_evidence_are_exported(self):
        self.prepare_export()
        audit = json.loads((self.data / "topics/replay_audit.json").read_text())
        for suffix in (".png",):
            source = self.source / FIGURES / f"expanded/topic_distribution{suffix}"
            figure = (
                self.source
                / FIGURES.parent
                / "expanded/density_details"
                / f"democratic_vs_republican_1{suffix}"
            )
            figure.parent.mkdir(parents=True, exist_ok=True)
            figure.write_bytes(source.read_bytes())
            audit["substantive_artifacts_sha256"][figure.relative_to(self.source).as_posix()] = (
                digest(figure)
            )
        self.write_json("topics/replay_audit.json", audit)
        self.write_csv(
            "expanded/density_region_evidence.csv",
            [{"example_text": "A complete claim.", "example_log_density_ratio": 1.25}],
        )
        self.archive()
        output = Path(self.tmp.name) / "publication"
        with patch(
            "scripts.build_platform_publication.subprocess.check_output", side_effect=["", "a" * 40]
        ):
            export(self.source, output)
        self.assertTrue(
            (output / "figures/expanded/density_details/democratic_vs_republican_1.png").is_file()
        )
        self.assertEqual(
            (output / "downloads/expanded/density_region_evidence.csv").read_bytes(),
            (self.data / "expanded/density_region_evidence.csv").read_bytes(),
        )
        self.assertEqual(
            json.loads((output / "analysis.json").read_text())["density_regions"],
            [{"example_text": "A complete claim.", "example_log_density_ratio": "1.25"}],
        )

    def test_density_map_preserves_coordinates_topics_and_paired_source_claims(self):
        self.write_csv("expanded/density_region_evidence.csv", [dict(color_bound=4.0)])
        labels = json.loads((self.data / "topics/topic_labels.json").read_text())
        with (self.data / "topics/representatives.csv").open() as stream:
            representatives = list(csv.DictReader(stream))
        result = density_map_data(self.source, labels, representatives)
        self.assertEqual(result["points"][0], ["democratic", 0.25, 0.5, 0, 0, -1.0, -2.0, -3.0])
        self.assertEqual(result["color_bound"], 4.0)
        self.assertEqual(
            {row["group"] for row in result["topics"][0]["examples"]},
            {"democratic", "republican", "dsa"},
        )
        self.assertTrue(
            all(row["evidence"] == "Source text." for row in result["topics"][0]["examples"])
        )

    def test_density_map_rejects_missing_assignments_and_nonfinite_coordinates(self):
        labels = json.loads((self.data / "topics/topic_labels.json").read_text())
        self.write_csv(
            "topics/assignments.csv",
            [dict(claim_id="democratic", topic_id="topic-001", group="democratic")],
        )
        with self.assertRaisesRegex(ValueError, "every unique eligible claim"):
            density_map_data(self.source, labels, [])
        self.write_csv(
            "topics/assignments.csv",
            [
                dict(claim_id=group, topic_id="topic-001", group=group)
                for group in ("democratic", "republican", "dsa")
            ],
        )
        with (self.data / "expanded/scored_passages.csv").open() as stream:
            scored = list(csv.DictReader(stream))
        scored[0]["umap_x"] = "nan"
        self.write_csv("expanded/scored_passages.csv", scored)
        with self.assertRaisesRegex(ValueError, "Non-finite"):
            density_map_data(self.source, labels, [])

    def test_missing_issue_scope_is_rejected_without_partial_output(self):
        self.prepare_export(omitted=("strict/issues/topic-001_time.png",))
        output = Path(self.tmp.name) / "publication"
        with patch(
            "scripts.build_platform_publication.subprocess.check_output", side_effect=["", "a" * 40]
        ):
            with self.assertRaisesRegex(ValueError, "issue-level comparison charts"):
                export(self.source, output)
        self.assertFalse(output.exists())
        self.assertEqual(list(output.parent.glob(".platform-publication-*")), [])

    def test_stale_svg_source_or_archive_is_rejected(self):
        self.prepare_export()
        stale = self.source / FIGURES / "obsolete.svg"
        stale.write_text("<svg/>")
        with self.assertRaisesRegex(ValueError, "PNG-only"):
            validate(self.source)
        stale.unlink()
        with zipfile.ZipFile(self.data / "claim_documents.zip", "a") as archive:
            archive.writestr("figures/obsolete.svg", "<svg/>")
        with self.assertRaisesRegex(ValueError, "PNG-only"):
            validate(self.source)

    def test_nonpublication_png_metadata_is_rejected(self):
        from PIL import Image
        from PIL.PngImagePlugin import PngInfo

        self.prepare_export()
        figure = self.source / FIGURES / "strict/issues/topic-001_time.png"
        metadata = PngInfo()
        metadata.add_text("Comment", "Internal render notes")
        Image.new("RGB", (1, 1)).save(figure, pnginfo=metadata)
        audit = json.loads((self.data / "topics/replay_audit.json").read_text())
        audit["substantive_artifacts_sha256"][figure.relative_to(self.source).as_posix()] = digest(
            figure
        )
        self.write_json("topics/replay_audit.json", audit)
        self.archive()
        with patch(
            "scripts.build_platform_publication.subprocess.check_output", side_effect=["", "a" * 40]
        ):
            with self.assertRaisesRegex(ValueError, "nonpublication metadata"):
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
        from PIL import Image

        path = self.source / WEBSITE_FIGURES / "expanded/topic_distribution.png"
        path.parent.mkdir(parents=True)
        Image.new("RGB", (1, 1)).save(path)
        with self.assertRaisesRegex(ValueError, "stale website figure"):
            validate(self.source)


if __name__ == "__main__":
    unittest.main()
