import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from dsa_analysis.national_claim_topic_positions import (
    NO_DIFFERENCE,
    NO_POSITION,
    generate,
    plot_atlases,
    reviewed_positions,
    select_examples,
)
from dsa_analysis.national_platforms import digest, write_json, write_rows


class PositionAtlasTests(unittest.TestCase):
    def fixture(self, root):
        directory = root / "topics/positions"
        (directory / "packets").mkdir(parents=True)
        (directory / "reviews").mkdir()
        (root / "claims.csv").write_text("unchanged corpus\n")
        write_json(root / "topics/fit_manifest.json", {})
        write_rows(directory / "evidence.csv", [{"claim_id": "d1"}])
        groups = ("democratic", "republican", "dsa")
        packet = {
            "groups": {
                group: {
                    "examples": [
                        {"claim_id": group + suffix, "bundle_id": suffix} for suffix in ("1", "2")
                    ]
                }
                for group in groups
            }
        }
        packet_path = directory / "packets/topic-001.json"
        write_json(packet_path, packet)
        packet_hash = digest(packet_path.read_bytes())
        review = {
            "topic_id": "topic-001",
            "packet_sha256": packet_hash,
            "review_status": "evidence_reviewed",
            "review_origin": "assistant_source_bound_review",
            "groups": {
                group: {
                    "summary": "Documents advocate a policy.",
                    "caveat": "",
                    "supporting_claim_ids": [group + "1", group + "2"],
                }
                for group in groups
            },
            "pairs": {
                f"{first}_vs_{second}": {
                    "summary": "Observed documents differ in their proposed policies.",
                    "supporting_claim_ids": [first + "1", second + "1"],
                }
                for first, second in (
                    ("democratic", "republican"),
                    ("democratic", "dsa"),
                    ("republican", "dsa"),
                )
            },
        }
        write_json(directory / "reviews/topic-001.json", review)
        write_json(
            directory / "selection_manifest.json",
            {
                "fit_manifest_sha256": digest((root / "topics/fit_manifest.json").read_bytes()),
                "claims_sha256": digest((root / "claims.csv").read_bytes()),
                "evidence_sha256": digest((directory / "evidence.csv").read_bytes()),
                "packet_sha256": {"topic-001": packet_hash},
                "groups": groups,
                "topics": ["topic-001"],
            },
        )
        return directory, review

    def test_review_rejects_stale_packets_wrong_group_ids_and_one_sided_pairs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory, review = self.fixture(root)
            self.assertEqual(len(reviewed_positions(root)[1]), 1)
            review["groups"]["democratic"]["supporting_claim_ids"] = ["republican1"]
            write_json(directory / "reviews/topic-001.json", review)
            with self.assertRaisesRegex(ValueError, "Unsupported group position"):
                reviewed_positions(root)
            review["groups"]["democratic"]["supporting_claim_ids"] = ["democratic1"]
            write_json(directory / "reviews/topic-001.json", review)
            with self.assertRaisesRegex(ValueError, "multiple supporting bundles"):
                reviewed_positions(root)
            review["groups"]["democratic"]["supporting_claim_ids"] = ["democratic1", "democratic2"]
            review["pairs"]["democratic_vs_republican"]["supporting_claim_ids"] = ["democratic1"]
            write_json(directory / "reviews/topic-001.json", review)
            with self.assertRaisesRegex(ValueError, "Unsupported pairwise difference"):
                reviewed_positions(root)
            (directory / "packets/topic-001.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "packet changed"):
                reviewed_positions(root)

    def test_unprepared_positions_do_not_start_inference(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(generate(Path(temporary), Path(temporary)), {"status": "not_prepared"})

    def test_absent_group_cannot_receive_an_inferred_position(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory, review = self.fixture(root)
            packet_path = directory / "packets/topic-001.json"
            packet = json.loads(packet_path.read_text())
            packet["groups"]["dsa"]["examples"] = []
            write_json(packet_path, packet)
            manifest_path = directory / "selection_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["packet_sha256"]["topic-001"] = digest(packet_path.read_bytes())
            write_json(manifest_path, manifest)
            review["packet_sha256"] = manifest["packet_sha256"]["topic-001"]
            review["groups"]["dsa"].update(summary=NO_POSITION, supporting_claim_ids=[])
            for first in ("democratic", "republican"):
                review["pairs"][f"{first}_vs_dsa"].update(
                    summary=NO_DIFFERENCE, supporting_claim_ids=[first + "1"]
                )
            write_json(directory / "reviews/topic-001.json", review)
            self.assertEqual(len(reviewed_positions(root)[1]), 1)
            review["groups"]["dsa"]["summary"] = "Supports a policy without observed claims."
            write_json(directory / "reviews/topic-001.json", review)
            with self.assertRaisesRegex(ValueError, "Unsupported group position"):
                reviewed_positions(root)

    def test_selection_spans_bundles_and_includes_peripheral_claims(self):
        rows = [
            {"claim_id": f"{bundle}-{index}", "bundle_id": bundle}
            for bundle in ("many", "few")
            for index in range(6)
        ]
        embeddings = np.array([[1 - index / 10, index / 10] for index in range(6)] * 2)
        selected = select_examples(list(range(12)), rows, embeddings, np.array([1, 0]), limit=6)
        self.assertEqual(len(selected), 6)
        self.assertEqual({rows[index]["bundle_id"] for index in selected}, {"many", "few"})
        self.assertIn(5, selected)
        self.assertIn(11, selected)

    def test_joint_and_all_pair_atlases_show_positions_and_exact_share_gaps(self):
        import matplotlib.pyplot as plt

        groups = ("democratic", "republican", "dsa")
        rows = [
            {
                "topic_id": "topic-001",
                "group": group,
                "bundle_id": group,
                "umap_x": index,
                "umap_y": index / 2,
            }
            for index, group in enumerate(groups)
        ]
        with tempfile.TemporaryDirectory() as temporary:
            directory, review = self.fixture(Path(temporary))
            shares = [
                {
                    "view": "expanded",
                    "topic_id": "topic-001",
                    "group": group,
                    "share": share,
                    "claims": 2,
                    "bundles": 2,
                }
                for group, share in zip(groups, (0.2, 0.3, 0.1))
            ]
            captured = {}

            def capture(fig, stem, **kwargs):
                fig.canvas.draw()
                renderer = fig.canvas.get_renderer()
                width, height = fig.bbox.width, fig.bbox.height
                for text in fig.texts:
                    box = text.get_window_extent(renderer)
                    self.assertGreaterEqual(box.x0, 0)
                    self.assertLessEqual(box.x1, width, text.get_text())
                    self.assertGreaterEqual(box.y0, 0)
                    self.assertLessEqual(box.y1, height)
                captured[stem.name] = [text.get_text() for text in fig.texts]

            with patch("dsa_analysis.national_claim_plot_style.save_figure", side_effect=capture):
                stems = plot_atlases(
                    rows,
                    {"topic-001": {"title": "A concrete policy subject"}},
                    [review],
                    shares,
                    directory,
                )
            self.assertEqual(len(stems), 4)
            self.assertIn("Documents advocate a policy.", captured["all_groups"])
            self.assertIn("-10.0 percentage points", captured["democratic_vs_republican"])
            self.assertIn("+10.0 percentage points", captured["democratic_vs_dsa"])
            self.assertIn("+20.0 percentage points", captured["republican_vs_dsa"])
            self.assertFalse(plt.get_fignums())
