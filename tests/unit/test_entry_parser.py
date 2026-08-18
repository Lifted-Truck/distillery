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
        lessons, quarantines, meta = entry_parser.parse_library(text)
        self.assertEqual(lessons, [])
        self.assertEqual(quarantines, [])
        self.assertFalse(meta["unclosed_fence"])

    def test_structural_lines_ignored(self):
        text = "# Heading\n\nSome prose.\n- a bullet\n"
        lessons, quarantines, meta = entry_parser.parse_library(text)
        self.assertEqual(lessons, [])
        self.assertEqual(quarantines, [])

    def test_case_insensitive_attempt_detection_lowercase_l(self):
        # "[l..." (lowercase) is still an ATTEMPTED entry -> quarantines,
        # it must not silently vanish as structural text.
        text = "[l9999] whatever | candidate | added: 2026-01-01 | tags: x | lesson: l | evidence: e | falsifier: f\n"
        lessons, quarantines, meta = entry_parser.parse_library(text)
        self.assertEqual(lessons, [])
        self.assertEqual(len(quarantines), 1)

    def test_unclosed_fence_sets_meta(self):
        text = (
            "[L0001] before | candidate | added: 2026-01-01 | tags: x | "
            "lesson: l | evidence: e | falsifier: f\n"
            "\n"
            "```\n"
            "trailing fenced content never closes\n"
        )
        lessons, quarantines, meta = entry_parser.parse_library(text)
        self.assertEqual(len(lessons), 1)
        self.assertTrue(meta["unclosed_fence"])

    def test_heading_style_entry_quarantines_with_distinct_error(self):
        text = "### [L0099] heading-style entry\n\nSome prose after it.\n"
        lessons, quarantines, meta = entry_parser.parse_library(text)
        self.assertEqual(lessons, [])
        self.assertEqual(len(quarantines), 1)
        self.assertIn("heading-style", quarantines[0]["error"])
        self.assertEqual(quarantines[0]["line_no"], 1)


class TestAlphaFixture(unittest.TestCase):
    def setUp(self):
        self.text = _read("alpha")
        self.lessons, self.quarantines, self.meta = entry_parser.parse_library(self.text)

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

    def test_duplicate_id_in_file_quarantines_both(self):
        # v2 (docs/stream-schema.md, contract still-quarantine rule 1): a
        # duplicate id within one file quarantines BOTH occurrences -- this
        # is a deliberate behavior change from v1 (which had no such rule and
        # let both raw-identical L0004 lines parse as lessons; dedup was
        # journal/ingest's job, not the parser's).
        matches = [q for q in self.quarantines if q["raw"].startswith("[L0004]")]
        self.assertEqual(len(matches), 2)
        self.assertNotEqual(matches[0]["line_no"], matches[1]["line_no"])
        for m in matches:
            self.assertIn("duplicate id", m["error"])
            self.assertIn("L0004", m["error"])
        self.assertFalse(any(l["entry"]["id"] == "L0004" for l in self.lessons))

    def test_quarantine_count(self):
        # L12, l0002 (near-miss/lowercase id), L0003 (missing falsifier),
        # L0004 x2 (duplicate id) = 5.
        self.assertEqual(len(self.quarantines), 5)


class TestCrossProject(unittest.TestCase):
    def test_same_raw_line_parses_independently_in_two_projects(self):
        # entry_parser has no cross-call state; the same raw line parsed via
        # two independent parse_library() calls (standing in for two
        # projects' LIBRARYs) must produce byte-identical entries. Uses
        # beta's L0005 line verbatim -- alpha's own L0004 is now
        # intra-file-duplicated (a *different*, v2-only quarantine rule; see
        # TestAlphaFixture.test_duplicate_id_in_file_quarantines_both), which
        # would conflate the two concerns.
        line = (
            "[L0005] Beta only entry | tier: candidate | added: 2026-07-08 | "
            "tags: beta | lesson: Beta-only lesson used to pad the fixture set. | "
            "evidence: Present only in beta LIBRARY. | "
            "falsifier: If this vanishes, ingest lost a record. | supersedes: —\n"
        )
        lessons_a, _, _ = entry_parser.parse_library(line)
        lessons_b, _, _ = entry_parser.parse_library(line)
        self.assertEqual(len(lessons_a), 1)
        self.assertEqual(lessons_a[0]["raw"], lessons_b[0]["raw"])
        self.assertEqual(lessons_a[0]["entry"], lessons_b[0]["entry"])


class TestDeltaWrapFixture(unittest.TestCase):
    """The library-entry.2 upgrade's required new coverage (ROADMAP decision
    15/16): phantom-span guard, byte-exact reconstruction, repeated-label
    join, terminators vs blanks, placeholders, extra, segment-1-only tier,
    heading-style quarantine, negative still-quarantine cases."""

    def setUp(self):
        self.text = _read("delta-wrap")
        self.lessons, self.quarantines, self.meta = entry_parser.parse_library(self.text)
        self.by_id = {l["entry"]["id"]: l["entry"] for l in self.lessons}

    # -- 1. Phantom-span guard ------------------------------------------------

    def test_phantom_span_guard_single_entry_no_l0002_record(self):
        self.assertIn("L0001", self.by_id)
        self.assertIn("[L0002]", self.by_id["L0001"]["lesson"])
        self.assertNotIn("L0002", self.by_id)
        quarantine_ids = [q["raw"] for q in self.quarantines if q["raw"].startswith("[L0002]")]
        self.assertEqual(quarantine_ids, [])
        # evidence + falsifier survived intact on the entry the guard protects.
        self.assertTrue(self.by_id["L0001"]["evidence"])
        self.assertTrue(self.by_id["L0001"]["falsifier"])

    def test_genuine_duplicate_id_pair_quarantines_both(self):
        matches = [q for q in self.quarantines if q["raw"].startswith("[L0007]")]
        self.assertEqual(len(matches), 2)
        for m in matches:
            self.assertIn("duplicate id", m["error"])
        self.assertNotIn("L0007", self.by_id)

    # -- 2. Byte-exact reconstruction -----------------------------------------

    def test_byte_exact_pipe_reconstruction_no_respacing(self):
        lesson = self.by_id["L0004"]["lesson"]
        self.assertIn("|x|", lesson)
        self.assertNotIn("| x |", lesson)
        evidence = self.by_id["L0004"]["evidence"]
        self.assertIn("|x|", evidence)

    # -- 3. Repeated known labels ----------------------------------------------

    def test_repeated_evidence_labels_both_survive_with_label_restored(self):
        evidence = self.by_id["L0003"]["evidence"]
        self.assertIn("First evidence segment.", evidence)
        self.assertIn("Second evidence segment", evidence)
        self.assertIn("evidence:", evidence)  # repeat's own label text restored

    # -- 4. Terminators vs blanks ----------------------------------------------

    def test_interior_blank_folds_through_span(self):
        lesson = self.by_id["L0001"]["lesson"]
        self.assertIn("blank line directly above is interior", lesson)

    def test_trailing_heading_and_prose_stay_out_of_last_entry(self):
        l0009 = self.by_id.get("L0009")
        # L0009 quarantines (bad origin); check the raw folded text of that
        # quarantine record instead, plus the standalone heading quarantine.
        q_l0009 = next(q for q in self.quarantines if q["raw"].startswith("[L0009]"))
        self.assertNotIn("Notes", q_l0009["raw"])
        self.assertNotIn("trailing section", q_l0009["raw"])
        self.assertIsNone(l0009)

    def test_heading_style_entry_quarantines_distinctly(self):
        q = next(q for q in self.quarantines if "L0099" in q["raw"])
        self.assertIn("heading-style", q["error"])

    # -- 5. Placeholders ---------------------------------------------------------

    def test_supersedes_placeholder_with_note(self):
        entry = self.by_id["L0005"]
        self.assertNotIn("supersedes", entry)
        self.assertEqual(entry["supersedes_note"], "(refines L0001)")

    def test_supersedes_bare_placeholder_absent_no_note(self):
        entry = self.by_id["L0001"]
        self.assertNotIn("supersedes", entry)
        self.assertNotIn("supersedes_note", entry)

    def test_falsifier_placeholder_quarantines(self):
        q = next(q for q in self.quarantines if q["raw"].startswith("[L0008]"))
        self.assertIn("falsifier", q["error"])
        self.assertNotIn("L0008", self.by_id)

    # -- 6. extra ------------------------------------------------------------

    def test_unknown_label_lands_in_extra_and_continuation_joins(self):
        entry = self.by_id["L0006"]
        self.assertIn("extra", entry)
        self.assertIn("promoted", entry["extra"])
        self.assertTrue(entry["extra"]["promoted"].startswith("2026-08-01"))
        # the unlabeled segment after `promoted:` joined the extra value, not evidence.
        self.assertIn("still climbing", entry["extra"]["promoted"])
        self.assertNotIn("still climbing", entry["evidence"])

    # -- 7. Segment-1-only tier -----------------------------------------------

    def test_bare_tier_only_recognized_at_segment_one(self):
        # alpha#L0001 sets tier via segment 1 bare form.
        alpha_lessons, _, _ = entry_parser.parse_library(_read("alpha"))
        by_id = {l["entry"]["id"]: l["entry"] for l in alpha_lessons}
        self.assertEqual(by_id["L0001"]["tier"], "candidate")

    def test_later_bare_enum_word_joins_open_field_not_tier(self):
        text = (
            "[L0001] Title | candidate | added: 2026-08-01 | tags: x | "
            "lesson: candidate | evidence: e | falsifier: f\n"
        )
        lessons, quarantines, meta = entry_parser.parse_library(text)
        self.assertEqual(len(lessons), 1)
        entry = lessons[0]["entry"]
        self.assertEqual(entry["tier"], "candidate")
        # the SECOND "candidate" (in the lesson: segment) is plain content,
        # not re-interpreted as a bare tier assignment.
        self.assertEqual(entry["lesson"], "candidate")

    # -- 8. Heading-style / negative cases -------------------------------------

    def test_bad_origin_reference_quarantines(self):
        q = next(q for q in self.quarantines if q["raw"].startswith("[L0009]"))
        self.assertIn("origin", q["error"])

    def test_quarantine_count_delta_wrap(self):
        # L0007 x2 (dup id), L0008 (missing falsifier), L0009 (bad origin),
        # L0099 (heading-style) = 5.
        self.assertEqual(len(self.quarantines), 5)

    def test_lesson_count_delta_wrap(self):
        # L0001, L0003, L0004, L0005, L0006 = 5.
        self.assertEqual(len(self.lessons), 5)


class TestUnattachedSegment(unittest.TestCase):
    def test_unlabeled_segment_after_bare_tier_with_no_open_field_quarantines(self):
        # "never in corpus; visible if it ever occurs" (docs/stream-schema.md).
        text = (
            "[L0001] Title | candidate | stray unlabeled segment | "
            "added: 2026-08-01 | tags: x | lesson: l | evidence: e | falsifier: f\n"
        )
        lessons, quarantines, meta = entry_parser.parse_library(text)
        self.assertEqual(lessons, [])
        self.assertEqual(len(quarantines), 1)
        self.assertIn("unattached segment", quarantines[0]["error"])


if __name__ == "__main__":
    unittest.main()


class TestBackToBackPipeBearingMarkers(unittest.TestCase):
    # attest regression (2026-08-10 lead integration): real LIBRARYs may write
    # consecutive single-line entries with NO blank separators. A marker line
    # that itself carries a "|" opens a span even when its predecessor is
    # content; a pipeless [Lxxxx]-prefixed prose line (a cross-reference at a
    # wrap point) still folds into the open span. docs/stream-schema.md
    # §entry span.
    def test_attest_shape_back_to_back_entries_all_parse(self):
        text = (
            "# LIBRARY\n\n"
            "[L0001] First | candidate | added: 2026-07-06 | tags: a | lesson: x. | evidence: e1. | falsifier: f1. | supersedes: —\n"
            "[L0002] Second | candidate | added: 2026-07-08 | tags: b | lesson: y. | evidence: e2. | falsifier: f2. | supersedes: —\n"
            "[L0003] Third | candidate | added: 2026-07-09 | tags: c | lesson: z. | evidence: e3. | falsifier: f3. | supersedes: —\n"
        )
        lessons, quarantines, meta = entry_parser.parse_library(text)
        self.assertEqual([e["entry"]["id"] for e in lessons], ["L0001", "L0002", "L0003"])
        self.assertEqual(quarantines, [])

    def test_pipeless_crossref_line_still_folds(self):
        text = (
            "[L0012] Real | candidate | added: 2026-07-01 | tags: t\n"
            "| lesson: Related: [L0009] (why),\n"
            "[L0010] (curvature caps as safety), [L0011] (diagnostics).\n"
            "| evidence: e. | falsifier: f. | supersedes: —\n"
        )
        lessons, quarantines, meta = entry_parser.parse_library(text)
        self.assertEqual(len(lessons), 1)
        self.assertEqual(quarantines, [])
        self.assertIn("[L0010] (curvature caps", lessons[0]["entry"]["lesson"])
