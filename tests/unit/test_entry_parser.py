import os
import unittest

from distillery import entry_parser

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fixtures", "projects")


def _read(name):
    path = os.path.join(FIXTURES, name, "LIBRARY.md")
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestFenceAndBasicShape(unittest.TestCase):
    def test_fence_toggle_suppresses_contained_lines(self):
        text = (
            "```\n"
            "[L0001] fenced | candidate | added: 2026-01-01 | tags: x | "
            "lesson: l | evidence: e | falsifier: f\n"
            "```\n"
            "not a fence, not an entry\n"
        )
        lessons, quarantines = entry_parser.parse_library(text)
        self.assertEqual(lessons, [])
        self.assertEqual(quarantines, [])

    def test_structural_lines_ignored(self):
        text = "# Heading\n\nSome prose.\n- a bullet\n"
        lessons, quarantines = entry_parser.parse_library(text)
        self.assertEqual(lessons, [])
        self.assertEqual(quarantines, [])

    def test_case_insensitive_attempt_detection_lowercase_l(self):
        # "[l..." (lowercase) is still an ATTEMPTED entry -> quarantines,
        # it must not silently vanish as structural text.
        text = "[l9999] whatever | candidate | added: 2026-01-01 | tags: x | lesson: l | evidence: e | falsifier: f\n"
        lessons, quarantines = entry_parser.parse_library(text)
        self.assertEqual(lessons, [])
        self.assertEqual(len(quarantines), 1)


class TestAlphaFixture(unittest.TestCase):
    def setUp(self):
        self.text = _read("alpha")
        self.lessons, self.quarantines = entry_parser.parse_library(self.text)

    def test_bare_and_labeled_tier_both_parse(self):
        by_id = {l["entry"]["id"]: l["entry"] for l in self.lessons}
        self.assertIn("L0001", by_id)
        self.assertIn("L0002", by_id)
        self.assertEqual(by_id["L0001"]["tier"], "candidate")
        self.assertEqual(by_id["L0002"]["tier"], "candidate")
        self.assertEqual(
            by_id["L0001"]["lesson"],
            "Bare tier form parses the same as labeled tier form.",
        )
        self.assertEqual(
            by_id["L0002"]["lesson"],
            "Labeled tier form is the dominant shape in real LIBRARYs.",
        )

    def test_fenced_template_example_not_ingested(self):
        # The fenced [L0001] "example" line must not surface as a lesson.
        self.assertFalse(
            any(l["entry"].get("lesson") == "example lesson" for l in self.lessons)
        )
        self.assertFalse(
            any(q.get("raw", "").startswith("[L0001] example") for q in self.quarantines)
        )

    def test_near_miss_lines_quarantine_not_vanish(self):
        raws = [q["raw"] for q in self.quarantines]
        self.assertTrue(any(r.startswith("[L12]") for r in raws))
        self.assertTrue(any(r.startswith("[l0002]") for r in raws))

    def test_required_field_placeholder_quarantines(self):
        matches = [q for q in self.quarantines if q["raw"].startswith("[L0003]")]
        self.assertEqual(len(matches), 1)
        self.assertIn("falsifier", matches[0]["error"])

    def test_optional_placeholder_supersedes_absent(self):
        l0001 = next(l for l in self.lessons if l["entry"]["id"] == "L0001")
        self.assertNotIn("supersedes", l0001["entry"])
        l0002 = next(l for l in self.lessons if l["entry"]["id"] == "L0002")
        self.assertNotIn("supersedes", l0002["entry"])

    def test_duplicate_raw_line_within_project_both_parsed_by_parser(self):
        # entry_parser itself does not dedup; dedup is journal/ingest's job.
        matches = [l for l in self.lessons if l["entry"]["id"] == "L0004"]
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]["raw"], matches[1]["raw"])
        self.assertNotEqual(matches[0]["line_no"], matches[1]["line_no"])

    def test_quarantine_count(self):
        self.assertEqual(len(self.quarantines), 3)


class TestCrossProject(unittest.TestCase):
    def test_same_raw_line_parses_independently_in_two_projects(self):
        alpha_lessons, _ = entry_parser.parse_library(_read("alpha"))
        beta_lessons, _ = entry_parser.parse_library(_read("beta"))
        alpha_shared = next(l for l in alpha_lessons if l["entry"]["id"] == "L0004")
        beta_shared = next(l for l in beta_lessons if l["entry"]["id"] == "L0004")
        self.assertEqual(alpha_shared["raw"], beta_shared["raw"])
        self.assertEqual(alpha_shared["entry"], beta_shared["entry"])


if __name__ == "__main__":
    unittest.main()
