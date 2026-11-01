import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.build_dsa_article_lead import (
    attention_share_records,
    combined_density_contrast,
    rank_attention_areas,
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
from scripts.build_publication_folder import export_publishing, publication_files


class PublishingFolderTest(unittest.TestCase):
    def make_source(self, root):
        from PIL import Image

        labels = [
            {"topic_id": "topic-003", "title": "Labor & unions", "displayed": True},
            {"topic_id": "topic-008", "title": "Party identity", "displayed": False},
        ]
        path = root / "data/analysis/national_claims/full/topics/topic_labels.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(labels))
        sources = [
            "figures/article/dsa_vs_major_parties_lead.png",
            "figures/article/dsa_attention_share_ratios.csv",
            "figures/national_claims/full/topics/expanded/substack_overview.png",
            "figures/national_claims/full/topics/expanded/issues/topic-003_overall.png",
            "figures/national_claims/full/topics/expanded/issues/topic-003_time.png",
            "figures/national_claims/full/topics/expanded/piece/topic-003.png",
        ]
        sources.extend(
            f"figures/national_claims/full/topics/positions/{name}.png"
            for name in (
                "all_groups",
                "democratic_vs_republican",
                "democratic_vs_dsa",
                "republican_vs_dsa",
            )
        )
        sources.extend(
            [
                "figures/national_claims/full/expanded/density_details/democratic_vs_dsa_1.png",
                "figures/national_claims/full/strict/density_details/democratic_vs_dsa_1.png",
                "figures/national_claims/full/topics/strict/issues/topic-003_overall.png",
                "figures/national_claims/full/strict/coverage.png",
            ]
        )
        for source in sources:
            path = root / source
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".csv":
                path.write_bytes(b"topic,ratio\nlabor,5.5\n")
                continue
            background = "#F2EFE7" if "/article/" in source else "#F7F5F0"
            image = Image.new("RGBA", (4, 4), background)
            image.putpixel((1, 1), (200, 90, 61, 255))
            image.putpixel((2, 2), (247, 245, 240, 128))
            image.save(path)
        return root / "figures/article/dsa_vs_major_parties_lead.png"

    def test_publishing_backgrounds_preserve_chart_pixels_and_detect_stale_sources(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lead = self.make_source(root)
            original = lead.read_bytes()
            manifest = export_publishing(root)
            self.assertEqual(export_publishing(root, check=True), manifest)
            self.assertEqual(lead.read_bytes(), original)
            self.assertIn("substack/issues/labor-unions-combined.png", manifest)
            self.assertIn("margin-of-error/issues/labor-unions-combined.png", manifest)
            for destination, background in (
                ("substack", (245, 245, 245, 255)),
                ("margin-of-error", (247, 245, 240, 255)),
            ):
                for name in ("where-dsa-stands-apart.png", "issues/labor-unions-overall.png"):
                    with Image.open(root / "figures" / destination / name) as image:
                        self.assertEqual(image.getpixel((0, 0)), background)
                        self.assertEqual(image.getpixel((1, 1)), (200, 90, 61, 255))
                        self.assertEqual(image.getpixel((2, 2)), (247, 245, 240, 128))
            website = root / "figures/margin-of-error/issues/labor-unions-overall.png"
            self.assertEqual(
                website.read_bytes(),
                (
                    root
                    / "figures/national_claims/full/topics/expanded/issues/topic-003_overall.png"
                ).read_bytes(),
            )
            self.assertIn("margin-of-error/supporting/density/democratic-vs-dsa-1.png", manifest)
            self.assertIn(
                "margin-of-error/supporting/adopted-only/issues/labor-unions-overall.png",
                manifest,
            )
            self.assertIn(
                "margin-of-error/supporting/adopted-only/density/democratic-vs-dsa-1.png",
                manifest,
            )
            self.assertIn("margin-of-error/supporting/adopted-only/coverage.png", manifest)
            self.assertFalse(any("adopted-only/supporting/" in name for name in manifest))
            self.assertFalse(any("identity" in name or "topic-" in name for name in manifest))
            ratios = root / "figures/data/attention-share-ratios.csv"
            self.assertEqual(
                ratios.read_bytes(),
                (root / "figures/article/dsa_attention_share_ratios.csv").read_bytes(),
            )
            with Image.open(lead) as image:
                image.putpixel((1, 1), (61, 111, 140, 255))
                image.save(lead)
            with self.assertRaisesRegex(ValueError, "stale publishing file"):
                export_publishing(root, check=True)
            export_publishing(root)
            export_publishing(root, check=True)

    def test_missing_inputs_and_colliding_issue_names_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lead = self.make_source(root)
            original = lead.read_bytes()
            lead.unlink()
            with self.assertRaisesRegex(ValueError, "existing current figures"):
                export_publishing(root)
            self.assertFalse((root / "figures/substack").exists())
            lead.write_bytes(original)
            path = root / "data/analysis/national_claims/full/topics/topic_labels.json"
            labels = json.loads(path.read_text())
            labels.append({"topic_id": "topic-009", "title": "Labor-unions", "displayed": True})
            path.write_text(json.dumps(labels))
            with self.assertRaisesRegex(ValueError, "Duplicate publishing filename"):
                publication_files(root)

    def test_refresh_removes_only_previously_managed_obsolete_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_source(root)
            export_publishing(root)
            old = root / "figures/substack/issues/labor-unions-overall.png"
            unowned = old.with_name("my-draft.png")
            unowned.write_bytes(b"keep my draft")
            path = root / "data/analysis/national_claims/full/topics/topic_labels.json"
            labels = json.loads(path.read_text())
            labels[0]["title"] = "Worker protections"
            path.write_text(json.dumps(labels))
            export_publishing(root)
            self.assertFalse(old.exists())
            self.assertEqual(unowned.read_bytes(), b"keep my draft")
            self.assertTrue(old.with_name("worker-protections-overall.png").exists())
            export_publishing(root, check=True)

    def test_unrecognized_source_background_is_rejected(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lead = self.make_source(root)
            Image.new("RGBA", (4, 4), "#FFFFFF").save(lead)
            with self.assertRaisesRegex(ValueError, "Unrecognized publication background"):
                export_publishing(root)

    def test_checks_pixels_across_png_encodings_not_just_manifest_hashes(self):
        import hashlib

        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_source(root)
            manifest = export_publishing(root)
            name = "substack/where-dsa-stands-apart.png"
            target = root / "figures" / name
            index = root / "figures/manifest.json"

            def update_hash():
                manifest[name]["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
                index.write_text(json.dumps({"files": manifest}, indent=2) + "\n")

            with Image.open(target) as image:
                image.save(target, compress_level=0)
            update_hash()
            export_publishing(root, check=True)
            with Image.open(target) as image:
                image.putpixel((1, 1), (0, 0, 0, 255))
                image.save(target)
            update_hash()
            with self.assertRaisesRegex(ValueError, "stale publishing file"):
                export_publishing(root, check=True)


class ArticleLeadTest(unittest.TestCase):
    def test_every_lead_layout_keeps_full_embedding_map_and_central_anchors(self):
        from matplotlib.figure import Figure

        records = [
            dict(
                title=title,
                anchor_coordinates=[index, index],
                snippet="Demilitarize police departments.",
                source_date="2024-08",
                document_type="program",
                attention_ratio=5.51299931734491 if index == 0 else 4.602112630128374,
                shares={"dsa": 0.09294009293158682 if index == 0 else 0.06135244587941502},
                combined_share=0.016858353789230517 if index == 0 else 0.013331365572794253,
            )
            for index, title in enumerate(
                (
                    "Institutional Power, Oppression, and Social Conflict",
                    "Criminal Justice, Policing, and Incarceration",
                )
            )
        ]
        data = dict(
            points=[
                [f"claim-{index}", index, index + 0.5, 0, index, 0, 0, index] for index in range(3)
            ],
            limits=[[-2, 3], [-1, 4]],
            color_bound=2,
        )

        def check_figure(figure, *args, **kwargs):
            axis = figure.axes[0]
            scatter = axis.collections[0]
            self.assertEqual(scatter.get_offsets().tolist(), [[0, 0.5], [1, 1.5], [2, 2.5]])
            self.assertEqual(scatter.get_array().tolist(), [0, 1, 2])
            self.assertEqual(scatter.get_clim(), (-2, 2))
            self.assertEqual(axis.get_xlim(), (-2, 3))
            self.assertEqual(axis.get_ylim(), (-1, 4))
            self.assertEqual([text.get_text() for text in axis.texts], ["1", "2"])
            self.assertEqual([text.get_position() for text in axis.texts], [(0, 0), (1, 1)])
            self.assertFalse(axis.patches)
            labels = [text.get_text() for text in figure.texts]
            self.assertIn("5.5\u00d7", labels)
            self.assertIn("4.6\u00d7", labels)
            self.assertIn("DSA 9.29%  \u00b7  Democrat & Republican 1.69%", labels)
            self.assertTrue(
                any(
                    "colors show language density, not attention shares" in label
                    for label in labels
                )
            )
            if layout != "map-bottom":
                self.assertIn("POLICY ATTENTION SHARES", labels)
                headings = [text for text in figure.texts if text.get_text().startswith("1  ")]
                self.assertGreater(headings[0].get_position()[1], 0.9)
                figure.canvas.draw()
                renderer = figure.canvas.get_renderer()
                boxes = [text.get_window_extent(renderer) for text in figure.texts]
                for index, box in enumerate(boxes):
                    self.assertGreaterEqual(box.x0, 0)
                    self.assertGreaterEqual(box.y0, 0)
                    self.assertLessEqual(box.x1, figure.bbox.width)
                    self.assertLessEqual(box.y1, figure.bbox.height)
                    for other in boxes[index + 1 :]:
                        self.assertFalse(
                            min(box.x1, other.x1) - max(box.x0, other.x0) > 1
                            and min(box.y1, other.y1) - max(box.y0, other.y0) > 1
                        )

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(Figure, "savefig", autospec=True, side_effect=check_figure):
                for layout in ("map-five", "map-bottom", "map-three"):
                    with self.subTest(layout=layout):
                        render_variant(data, records, Path(directory) / "lead.png", layout)

    def test_attention_areas_rank_positive_share_gaps_not_density_or_ratios(self):
        groups = ["democratic", "republican", "dsa"]
        cases = [
            ("large", 0.3, 0.1, True, 2),
            ("small", 0.2, 0.15, True, 2),
            ("ratio", 0.04, 0.001, True, 2),
            ("lower", 0.02, 0.1, True, 2),
            ("identity", 0.9, 0.0001, False, 2),
            ("sparse", 0.99, 0, True, 1),
            ("zero", 0.1, 0, True, 2),
        ]
        claims, points, topics, rows = [], [], [], []
        for index, (topic_id, dsa, baseline, displayed, bundles) in enumerate(cases):
            examples = []
            for bundle in range(bundles):
                claim_id = f"{topic_id}-{bundle}"
                claims.append(
                    dict(
                        claim_id=claim_id, group="dsa", bundle_id=f"b{bundle}", source_url="source"
                    )
                )
                points.append(
                    [claim_id, bundle, index, index, 2, 0, 0, -100 if topic_id == "large" else 100]
                )
                examples.append(dict(claim_id=claim_id, group="dsa"))
            topics.append(
                dict(topic_id=topic_id, title=topic_id, displayed=displayed, examples=examples)
            )
            rows.extend(
                dict(
                    topic_id=topic_id,
                    group=group,
                    share=str(dsa if group == "dsa" else baseline),
                    view="expanded",
                    available="True",
                )
                for group in groups
            )
        data = dict(groups=groups, points=points, topics=topics, limits=[[-1, 2], [-1, 8]])
        records = rank_attention_areas(data, claims, rows)
        all_records = attention_share_records(topics, rows)
        self.assertEqual(len(all_records), len(cases))
        self.assertFalse(next(r for r in all_records if r["topic_id"] == "identity")["displayed"])
        self.assertIsNone(
            next(r for r in all_records if r["topic_id"] == "zero")["attention_ratio"]
        )
        self.assertEqual(
            [record["topic_id"] for record in records], ["large", "zero", "small", "ratio"]
        )
        self.assertAlmostEqual(records[0]["attention_ratio"], 3)
        self.assertAlmostEqual(records[0]["gap"], 0.2)
        self.assertIsNone(records[1]["attention_ratio"])
        self.assertEqual(records[0]["anchor_claim_id"], "large-1")
        with self.assertRaisesRegex(ValueError, "Missing observed party shares"):
            rank_attention_areas(data, claims, rows[1:])
        with self.assertRaisesRegex(ValueError, "Invalid or duplicate"):
            rank_attention_areas(data, claims, rows + [rows[0]])
        for value in ("nan", "-0.1", "1.1"):
            with self.subTest(invalid_share=value):
                invalid = [dict(row) for row in rows]
                invalid[0]["share"] = value
                with self.assertRaisesRegex(ValueError, "Invalid or duplicate"):
                    rank_attention_areas(data, claims, invalid)

    def test_all_attention_comparisons_use_unrounded_shares_and_explicit_directions(self):
        labels = [dict(topic_id="issue", title="Issue")]
        values = {"democratic": 0.012345, "republican": 0.034567, "dsa": 0.056789}
        rows = [
            dict(topic_id="issue", group=group, share=str(value), view="expanded", available="True")
            for group, value in values.items()
        ]
        record = attention_share_records(labels, rows)[0]
        self.assertEqual(record["democratic_republican_ratio"], 0.012345 / 0.034567)
        self.assertEqual(record["dsa_democratic_ratio"], 0.056789 / 0.012345)
        self.assertEqual(record["dsa_republican_ratio"], 0.056789 / 0.034567)
        self.assertEqual(record["attention_ratio"], 0.056789 / ((0.012345 + 0.034567) / 2))
        for row in rows:
            if row["group"] != "dsa":
                row["share"] = "0"
        zero = attention_share_records(labels, rows)[0]
        for field in (
            "democratic_republican_ratio",
            "dsa_democratic_ratio",
            "dsa_republican_ratio",
            "attention_ratio",
        ):
            self.assertIsNone(zero[field])

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
