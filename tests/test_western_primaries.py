import csv
import unittest

from dsa_analysis.paths import ANALYSIS_DATA_DIR, RAW_DIR
from dsa_analysis.state_results import FIELDS
from dsa_analysis.western_primaries import (
    AK_SOURCES,
    AZ_2024_RESULTS,
    AZ_2026_RESULTS,
    NV_COUNTIES,
    NV_NO_PRIMARY_CONTESTS,
    NV_OPEN_CONTESTS,
    collect_western_primaries,
    parse_alaska,
    parse_arizona_2026,
    parse_nevada_clark_2026,
    NV_2026_CLARK_SOURCE,
)


class WesternPrimaryTests(unittest.TestCase):
    def test_alaska_uses_one_nonpartisan_ballot_and_preserves_zero(self):
        source = AK_SOURCES[1]
        path = RAW_DIR / "western_primaries" / source["filename"]
        rows = parse_alaska(path, source)
        self.assertEqual(len(rows), 31)
        self.assertEqual({row["primary_party"] for row in rows}, {""})
        self.assertEqual({row["election_system"] for row in rows}, {"nonpartisan_top_four"})
        self.assertTrue(all(row["reporting_units"] > 0 for row in rows))

    def test_arizona_reviewed_extraction_preserves_write_ins_and_all_districts(self):
        house = {
            district for chamber, district, _ in AZ_2024_RESULTS if chamber == "House"
        }
        self.assertEqual(house, {f"{number:02}" for number in range(1, 10)})
        write_ins = [
            name
            for candidates in AZ_2024_RESULTS.values()
            for name, _, write_in in candidates
            if write_in
        ]
        self.assertEqual(
            set(write_ins),
            {
                "Dustin Paul Williams", "Eduardo Quintana", "Nicholas N. Glenn",
                "Vincent Beck-Jones", "Athena Eastwood", "Isiah Gallegos",
            },
        )

    def test_arizona_2026_every_district_party_total_matches_canvass(self):
        expected = {
            ("01", "Republican"): 87774, ("01", "Democratic"): 73523,
            ("01", "Libertarian"): 289,
            ("02", "Republican"): 89205, ("02", "Democratic"): 65118,
            ("02", "Libertarian"): 328,
            ("03", "Republican"): 437, ("03", "Democratic"): 37553,
            ("03", "Green"): 5, ("03", "No Labels"): 571,
            ("04", "Republican"): 39431, ("04", "Democratic"): 57095,
            ("04", "No Labels"): 1500,
            ("05", "Republican"): 89206, ("05", "Democratic"): 46731,
            ("06", "Republican"): 76481, ("06", "Democratic"): 78310,
            ("06", "Libertarian"): 277, ("06", "Green"): 29,
            ("07", "Republican"): 21934, ("07", "Democratic"): 59304,
            ("08", "Republican"): 69182, ("08", "Democratic"): 47636,
            ("09", "Republican"): 79336, ("09", "Democratic"): 35700,
        }
        actual = {
            (district, party): sum(votes for _, votes, _ in candidates)
            for (_, district, party), candidates in AZ_2026_RESULTS.items()
        }
        self.assertEqual(actual, expected)
        rows = parse_arizona_2026({
            "source_id": "az-2026-primary-official-canvass",
            "state": "AZ",
            "date": "2026-07-21",
            "filename": "az/2026/az-2026-primary-official-canvass.pdf",
            "url": "https://example.test",
        })
        self.assertEqual(len(rows), 37)
        self.assertEqual(len({row["contest_id"] for row in rows}), 25)
        self.assertEqual(sum(row["write_in"] for row in rows), 4)

    def test_utah_2026_district_one_is_certified_as_single_county(self):
        path = (
            RAW_DIR / "western_primaries" / "ut" / "2026"
            / "ut-2026-primary-statewide-certification.txt"
        )
        text = path.read_text()
        self.assertIn("The following races are single-county races.", text)
        self.assertIn("U.S. House District 1 Democratic BEN MCADAMS", text)

    def test_nevada_open_accounting_is_exact_and_excludes_no_primary_contests(self):
        open_keys = {
            (cycle, chamber, district, party)
            for cycle, _, chamber, district, party, _ in NV_OPEN_CONTESTS
        }
        no_primary_keys = {
            (cycle, chamber, district, party)
            for cycle, _, chamber, district, party in NV_NO_PRIMARY_CONTESTS
        }
        self.assertEqual(
            {key for key in open_keys if key[0] == "2024"},
            {
                ("2024", "Senate", "S", "Democratic"),
                ("2024", "Senate", "S", "Republican"),
                ("2024", "House", "01", "Republican"),
                ("2024", "House", "02", "Republican"),
                ("2024", "House", "03", "Democratic"),
                ("2024", "House", "03", "Republican"),
                ("2024", "House", "04", "Democratic"),
                ("2024", "House", "04", "Republican"),
            },
        )
        self.assertEqual(len({key for key in open_keys if key[0] == "2026"}), 3)
        self.assertTrue(open_keys.isdisjoint(no_primary_keys))
        self.assertEqual(
            sum(count for cycle, *_, count in NV_OPEN_CONTESTS if cycle == "2026"),
            30,
        )

    def test_nevada_inventory_requires_all_seventeen_counties_per_cycle(self):
        self.assertEqual(len(NV_COUNTIES), 17)
        self.assertEqual(len(set(NV_COUNTIES)), 17)
        self.assertEqual(
            set(NV_COUNTIES),
            {
                "Carson City", "Churchill", "Clark", "Douglas", "Elko",
                "Esmeralda", "Eureka", "Humboldt", "Lander", "Lincoln", "Lyon",
                "Mineral", "Nye", "Pershing", "Storey", "Washoe", "White Pine",
            },
        )
        summary = collect_western_primaries()
        self.assertEqual(summary["nv_county_slots"], 34)
        path = (
            ANALYSIS_DATA_DIR / "congressional" / "western"
            / "nv_county_source_inventory.csv"
        )
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 34)
        self.assertEqual(sum(row["status"] == "captured_final" for row in rows), 13)
        failed = {
            (row["cycle"], row["county"])
            for row in rows
            if row["status"] == "route_exhausted_no_artifact"
        }
        self.assertEqual(failed, {
                ("2024", "Carson City"), ("2026", "Carson City"),
                ("2024", "Douglas"), ("2026", "Douglas"),
                ("2024", "Elko"), ("2026", "Elko"),
                ("2024", "Washoe"), ("2026", "Washoe"),
                ("2024", "Clark"),
                ("2024", "Esmeralda"), ("2026", "Esmeralda"),
                ("2024", "Lander"), ("2026", "Lander"),
                ("2024", "Lincoln"), ("2026", "Lincoln"),
                ("2024", "Mineral"), ("2026", "Mineral"),
                ("2024", "Pershing"), ("2026", "Pershing"),
                ("2024", "Storey"), ("2026", "White Pine"),
            })
        self.assertFalse({row["status"] for row in rows} - {
            "captured_final", "route_exhausted_no_artifact",
        })

    def test_clark_2026_closes_single_county_house_districts(self):
        path = RAW_DIR / "western_primaries" / NV_2026_CLARK_SOURCE["filename"]
        rows = parse_nevada_clark_2026(path, NV_2026_CLARK_SOURCE)
        self.assertEqual(len(rows), 17)
        self.assertEqual(len({row["contest_id"] for row in rows}), 4)
        totals = {
            (row["district"], row["primary_party"]): 0
            for row in rows
        }
        for row in rows:
            totals[(row["district"], row["primary_party"])] += row["votes"]
        self.assertEqual(
            totals,
            {
                ("01", "Democratic"): 44292,
                ("01", "Republican"): 31744,
                ("03", "Democratic"): 45808,
                ("03", "Republican"): 35198,
            },
        )
        expected_names = {
            ("01", "Democratic"): {
                "Cornejo, Gabriel", "Hoover, Joy", "Paniagua, Luis", "Titus, Dina",
            },
            ("01", "Republican"): {
                "Arnold, Marie Encar", "Blockey, Jim", "Boris, Michael",
                "Buck, Carrie Ann", 'Saga, Rick "indicted"',
            },
            ("03", "Democratic"): {
                "Lally, James A.", "Lee, Susie", "Robinson, Terrill", "West, Brandon",
            },
            ("03", "Republican"): {
                "Anderson, Tera", "Gunter, Jeff", "Nagy, Aury", "O'Donnell, Marty",
            },
        }
        actual_names = {}
        for row in rows:
            actual_names.setdefault(
                (row["district"], row["primary_party"]), set(),
            ).add(row["candidate_name"])
        self.assertEqual(actual_names, expected_names)
        self.assertNotIn("Unresolved Write-In", {
            row["candidate_name"] for row in rows
        })

    def test_partial_clark_contests_never_enter_canonical_results(self):
        summary = collect_western_primaries()
        self.assertEqual(summary["candidate_rows"], 152)
        self.assertEqual(summary["contests"], 59)
        self.assertEqual(summary["partial_candidate_rows"], 17)
        self.assertEqual(summary["partial_contests"], 4)
        root = ANALYSIS_DATA_DIR / "congressional"
        with (root / "western_primary_results.csv").open(
            newline="", encoding="utf-8",
        ) as handle:
            canonical = list(csv.DictReader(handle))
        with (root / "western" / "partial_primary_results.csv").open(
            newline="", encoding="utf-8",
        ) as handle:
            partial = list(csv.DictReader(handle))
        partial_contests = {row["contest_id"] for row in partial}
        self.assertEqual(len(partial), 17)
        self.assertTrue(partial_contests)
        self.assertTrue(partial_contests.isdisjoint(
            {row["contest_id"] for row in canonical}
        ))

    def test_canonical_schema_includes_stage(self):
        self.assertIn("stage", FIELDS)
        self.assertEqual(len(FIELDS), 20)


if __name__ == "__main__":
    unittest.main()
