"""Layer-0 guards on the D3 Layer-E fixture (docs/analyst.md §2 plants).

These do NOT test the analyst (that is Layer-E, measured, non-blocking).
They pin the fixture's *adversarial properties*, so the D3 gate cannot
silently become easy: if a plant drifts into something D2 already catches,
or the decoy stops being the tempting one, the gate would still pass while
measuring nothing. These assertions make that drift a CI failure.
"""

import json
import os
import unittest

from distillery import query

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
D3_STREAM = os.path.join(REPO_ROOT, "tests", "fixtures", "stream-d3", "stream.jsonl")

RECURRENCE_PLANT = ("orchard#L0001", "groves/willow#L0003")
CONTRADICTION_PLANT = ("orchard#L0002", "groves/willow#L0004")
DECOY = ("orchard#L0003", "groves/willow#L0005")


def _group(origin):
    # docs/analyst.md §1d.5: ungrouped projects have NO group, never a
    # shared empty-string one.
    project = origin.split("#")[0]
    return project.split("/")[0] if "/" in project else None


class TestD3FixtureProperties(unittest.TestCase):
    def setUp(self):
        self.records = query.load_journal(D3_STREAM)
        self.lessons = [r for r in self.records if r["kind"] == "lesson"]
        self.by_origin = {r["origin"]: r for r in self.lessons}

    def test_all_planted_origins_exist(self):
        for pair in (RECURRENCE_PLANT, CONTRADICTION_PLANT, DECOY):
            for origin in pair:
                self.assertIn(origin, self.by_origin, "%s missing from D3 fixture" % origin)

    def test_recurrence_plant_is_invisible_to_D2(self):
        # The whole point of D3: if D2's deterministic signatures can see it,
        # the plant measures nothing about semantic detection.
        self.assertEqual(query.recurrences(self.records, near=False), [])
        self.assertEqual(query.recurrences(self.records, near=True), [])

    def test_recurrence_plant_shares_no_tag(self):
        # Mirrors the real corpus: the candidate-#3 family shares zero tags
        # pairwise across its four projects. A plant that shared a tag would
        # measure the easy path.
        a, b = (set(self.by_origin[o]["entry"]["tags"]) for o in RECURRENCE_PLANT)
        self.assertEqual(a & b, set(), "plant must share no tag with its pair")

    def test_decoy_is_more_tempting_than_the_plant(self):
        # Adversarial property: tag-joining or keyword-matching finds the
        # WRONG pair. An analyst that reports the decoy has false-positived.
        plant_shared = set.intersection(*(set(self.by_origin[o]["entry"]["tags"]) for o in RECURRENCE_PLANT))
        decoy_shared = set.intersection(*(set(self.by_origin[o]["entry"]["tags"]) for o in DECOY))
        self.assertGreater(
            len(decoy_shared), len(plant_shared),
            "the decoy must be easier to find than the real plant, or the "
            "fixture rewards shallow matching",
        )

    def test_recurrence_plant_is_cross_group(self):
        # Not single_group -> route is unconstrained, so the Layer-E run
        # exercises real routing rather than the forced-undecided path.
        groups = [_group(o) for o in RECURRENCE_PLANT]
        self.assertIn(None, groups, "one plant origin should be an ungrouped project")
        self.assertNotEqual(groups[0], groups[1])

    def test_contradiction_plant_is_same_tag_opposite_guidance(self):
        a, b = (self.by_origin[o]["entry"] for o in CONTRADICTION_PLANT)
        self.assertTrue(set(a["tags"]) & set(b["tags"]), "contradiction pair should share a topic tag")
        self.assertNotEqual(a["lesson"], b["lesson"])

    def test_fixture_is_valid_stream_records(self):
        for r in self.records:
            self.assertIn(r["kind"], ("lesson", "quarantine"))
            self.assertEqual(len(r["hash"]), 16)
            for field in ("v", "swept", "project", "source_hash", "raw"):
                self.assertIn(field, r)
            if r["kind"] == "lesson":
                self.assertEqual(r["entry_contract"], "library-entry.2")
                for field in ("id", "title", "tier", "added", "tags", "lesson", "evidence", "falsifier"):
                    self.assertIn(field, r["entry"])

    def test_fixture_carries_a_quarantine_for_coverage_accounting(self):
        self.assertTrue(any(r["kind"] == "quarantine" for r in self.records))

    def test_no_absolute_paths(self):
        # Same guard as the journal (ROADMAP decision 12).
        blob = json.dumps(self.records)
        self.assertNotIn("/Users/", blob)


if __name__ == "__main__":
    unittest.main()
