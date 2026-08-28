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

    def test_heading_style_marker_now_opens_a_block_span_v3(self):
        # v3: "### [Lxxxx] ..." is the block-form entry marker (contract
        # §Block form), not a rejected shape -- it OPENS a span rather than
        # producing the v2-only "heading-style entry marker" quarantine
        # (that error text is retired; see the contract's still-quarantine
        # list, "no new absence"). Lacking any fields, it still quarantines
        # -- just for the ordinary "missing tier" reason, proving the block
        # marker didn't get a free pass on validation.
        text = "### [L0099] heading-style entry\n\nSome prose after it.\n"
        lessons, quarantines, meta = entry_parser.parse_library(text)
        self.assertEqual(lessons, [])
        self.assertEqual(len(quarantines), 1)
        self.assertNotIn("heading-style", quarantines[0]["error"])
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
        # v3: the "### [L0099] ..." heading now opens a block span (see
        # test_heading_style_marker_now_opens_a_block_span_v3) rather than
        # emitting the retired v2-only "heading-style entry marker" error.
        # It still quarantines -- no fields ever fold into it, since the
        # blank line and the following "## Notes" heading (a plain
        # terminator, no Lxxxx shape) close the span before any field line
        # arrives -- but for the ordinary "missing tier" reason.
        q = next(q for q in self.quarantines if "L0099" in q["raw"])
        self.assertNotIn("heading-style", q["error"])
        self.assertIn("tier", q["error"])

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


class TestBlockFormShapes(unittest.TestCase):
    """v3 block form (contract §Block form, READ-only): the three corpus
    heading shapes, each field delimiter, and the middot inline-bold
    separator. Corpus-grounded in ~/Documents/Claude/synthetic-worlds'
    Catena (bracketed), Antiphon (bare + em-dash), and spectrogen/
    resume-workshop (bare, title deferred to next line)."""

    _FIELDS = (
        "tier: candidate | added: 2026-08-01 | tags: fixture | "
        "lesson: A block-form lesson. | evidence: Block-form evidence. | "
        "falsifier: Block-form falsifier."
    )

    def _by_id(self, text):
        lessons, quarantines, meta = entry_parser.parse_library(text)
        return {l["entry"]["id"]: l["entry"] for l in lessons}, quarantines

    # -- 1. All three heading shapes agree on the parsed entry ---------------

    def test_bracketed_id_and_title_shape(self):
        text = "### [L0001] Bracketed title\n| %s\n" % self._FIELDS
        by_id, quarantines = self._by_id(text)
        self.assertEqual(quarantines, [])
        self.assertIn("L0001", by_id)
        self.assertEqual(by_id["L0001"]["title"], "Bracketed title")
        self.assertEqual(by_id["L0001"]["tier"], "candidate")
        self.assertEqual(by_id["L0001"]["entry_form"], "block")

    def test_bare_id_em_dash_title_shape(self):
        text = "### L0001 — Em-dash title\n| %s\n" % self._FIELDS
        by_id, quarantines = self._by_id(text)
        self.assertEqual(quarantines, [])
        self.assertEqual(by_id["L0001"]["title"], "Em-dash title")
        self.assertEqual(by_id["L0001"]["tier"], "candidate")

    def test_all_three_shapes_produce_equivalent_fields(self):
        bracketed, _ = self._by_id("### [L0001] Same title\n| %s\n" % self._FIELDS)
        em_dash, _ = self._by_id("### L0001 — Same title\n| %s\n" % self._FIELDS)
        for field in ("tier", "added", "tags", "lesson", "evidence", "falsifier"):
            self.assertEqual(bracketed["L0001"][field], em_dash["L0001"][field])
        self.assertEqual(bracketed["L0001"]["title"], em_dash["L0001"]["title"])

    # -- 2. Bare id, title on the FOLLOWING line (resume-workshop shape) -----

    def test_bare_id_title_on_next_line(self):
        text = "### L0001\nTitle on the next line\n| %s\n" % self._FIELDS
        by_id, quarantines = self._by_id(text)
        self.assertEqual(quarantines, [])
        self.assertEqual(by_id["L0001"]["title"], "Title on the next line")
        # The title line itself must NOT be swallowed as field content.
        self.assertNotIn("Title on the next line", by_id["L0001"]["lesson"])

    # -- 3. Field delimiters + middot inline bold -----------------------------

    def test_pipe_delimiter(self):
        text = "### [L0001] Pipe fields\n| %s\n" % self._FIELDS
        by_id, quarantines = self._by_id(text)
        self.assertEqual(quarantines, [])
        self.assertEqual(by_id["L0001"]["lesson"], "A block-form lesson.")

    def test_bold_delimiter(self):
        text = (
            "### [L0001] Bold fields\n"
            "**tier:** candidate\n"
            "**added:** 2026-08-01\n"
            "**tags:** fixture\n"
            "**lesson:** A bold-form lesson.\n"
            "**evidence:** Bold-form evidence.\n"
            "**falsifier:** Bold-form falsifier.\n"
        )
        by_id, quarantines = self._by_id(text)
        self.assertEqual(quarantines, [])
        self.assertEqual(by_id["L0001"]["lesson"], "A bold-form lesson.")
        self.assertEqual(by_id["L0001"]["tags"], ["fixture"])

    def test_bullet_bold_delimiter(self):
        text = (
            "### [L0001] Bullet fields\n"
            "- **tier:** candidate\n"
            "- **added:** 2026-08-01\n"
            "- **tags:** fixture\n"
            "- **lesson:** A bullet-form lesson.\n"
            "- **evidence:** Bullet-form evidence.\n"
            "- **falsifier:** Bullet-form falsifier.\n"
        )
        by_id, quarantines = self._by_id(text)
        self.assertEqual(quarantines, [])
        self.assertEqual(by_id["L0001"]["lesson"], "A bullet-form lesson.")

    def test_middot_separated_inline_bold_fields(self):
        text = (
            "### [L0001] Middot fields\n"
            "**tier:** candidate · **added:** 2026-08-01 · **tags:** fixture\n"
            "**lesson:** A middot-form lesson.\n"
            "**evidence:** Middot-form evidence.\n"
            "**falsifier:** Middot-form falsifier.\n"
        )
        by_id, quarantines = self._by_id(text)
        self.assertEqual(quarantines, [])
        self.assertEqual(by_id["L0001"]["tier"], "candidate")
        self.assertEqual(by_id["L0001"]["added"], "2026-08-01")
        self.assertEqual(by_id["L0001"]["tags"], ["fixture"])

    # -- 4. No new absence: a block entry still quarantines without falsifier

    def test_block_entry_missing_falsifier_still_quarantines(self):
        text = (
            "### [L0001] No falsifier\n"
            "| tier: candidate | added: 2026-08-01 | tags: fixture | "
            "lesson: l | evidence: e\n"
        )
        lessons, quarantines, meta = entry_parser.parse_library(text)
        self.assertEqual(lessons, [])
        self.assertEqual(len(quarantines), 1)
        self.assertIn("falsifier", quarantines[0]["error"])

    # -- 5. A non-entry heading still terminates a span, no phantom record ---

    def test_non_entry_heading_terminates_span_no_record(self):
        text = "### [L0001] Real entry\n| %s\n\n## Entries\n\nTrailing prose.\n" % self._FIELDS
        lessons, quarantines, meta = entry_parser.parse_library(text)
        self.assertEqual(len(lessons), 1)
        self.assertEqual(quarantines, [])
        self.assertNotIn("Entries", lessons[0]["entry"]["falsifier"])
        self.assertNotIn("Trailing prose", lessons[0]["entry"]["falsifier"])


class TestAbsorbsField(unittest.TestCase):
    """v3 amendment (distillery-004): `absorbs` is a comma-separated list of
    L\\d{4} references with an optional free-text remainder preserved as
    `absorbs_note`. Corpus-grounded in HYPERSAW L0016/L0031: the note text
    itself contains commas, so the field cannot be parsed by a plain
    comma-split of the whole value."""

    _HEADER = (
        "[L0001] Title | candidate | added: 2026-08-01 | tags: x | "
        "lesson: l | evidence: e | falsifier: f | "
    )

    def _parse_one(self, absorbs_segment):
        text = self._HEADER + absorbs_segment + "\n"
        lessons, quarantines, meta = entry_parser.parse_library(text)
        return lessons, quarantines

    def test_absorbs_comma_list_no_note(self):
        lessons, quarantines = self._parse_one("absorbs: L0011, L0021, L0034")
        self.assertEqual(quarantines, [])
        self.assertEqual(lessons[0]["entry"]["absorbs"], ["L0011", "L0021", "L0034"])
        self.assertNotIn("absorbs_note", lessons[0]["entry"])

    def test_absorbs_single_ref_with_note(self):
        lessons, quarantines = self._parse_one("absorbs: L0011 (note here)")
        self.assertEqual(quarantines, [])
        self.assertEqual(lessons[0]["entry"]["absorbs"], ["L0011"])
        self.assertEqual(lessons[0]["entry"]["absorbs_note"], "(note here)")

    def test_absorbs_em_dash_note_with_internal_commas(self):
        # HYPERSAW's real shape: the note itself contains commas.
        lessons, quarantines = self._parse_one(
            "absorbs: L0011, L0021, L0034 — shell-path, superset and layer "
            "blindness respectively; consolidated 2026-08-11"
        )
        self.assertEqual(quarantines, [])
        entry = lessons[0]["entry"]
        self.assertEqual(entry["absorbs"], ["L0011", "L0021", "L0034"])
        self.assertEqual(
            entry["absorbs_note"],
            "shell-path, superset and layer blindness respectively; consolidated 2026-08-11",
        )

    def test_absorbs_invalid_reference_quarantines(self):
        lessons, quarantines = self._parse_one("absorbs: notavalidref")
        self.assertEqual(lessons, [])
        self.assertEqual(len(quarantines), 1)
        self.assertIn("absorbs", quarantines[0]["error"])

    def test_absorbs_bad_element_in_list_quarantines(self):
        lessons, quarantines = self._parse_one("absorbs: L0011, badref")
        self.assertEqual(lessons, [])
        self.assertEqual(len(quarantines), 1)
        self.assertIn("absorbs", quarantines[0]["error"])

    def test_absorbs_placeholder_absent_no_note(self):
        lessons, quarantines = self._parse_one("absorbs: —")
        self.assertEqual(quarantines, [])
        self.assertNotIn("absorbs", lessons[0]["entry"])
        self.assertNotIn("absorbs_note", lessons[0]["entry"])

    def test_absorbs_does_not_land_in_extra(self):
        # The contract's named defect (2026-08-18, hypersaw-001 round 2):
        # `absorbs` was added to prose/schema/quarantine-list but not the
        # label-opening rule, so it fell through to `extra` and the graph
        # edge became unwalkable.
        lessons, quarantines = self._parse_one("absorbs: L0011, L0021, L0034")
        self.assertEqual(quarantines, [])
        entry = lessons[0]["entry"]
        self.assertNotIn("extra", entry)
        self.assertIn("absorbs", entry)


if __name__ == "__main__":
    unittest.main()


class TestBlockFormRealCorpusShapes(unittest.TestCase):
    """Shapes found only by parsing the real corpus (2026-08-18 lead
    integration). Unit tests written from the contract's examples passed
    while three real projects still failed — the contract prints labels
    lowercase and unwrapped, the corpus writes them capitalised, backticked,
    and pipe-joined without a leading pipe."""

    def test_capitalised_bold_labels_parse(self):
        # resume-workshop writes **Lesson:** / **Evidence:** / **Falsifier:**.
        # Case-sensitive matching sent all three to `extra`, so every entry
        # quarantined as "required field 'lesson' missing" — 5 complete
        # entries lost to letter case.
        text = (
            "### L0001\n"
            "**A privacy scan restricted to tracked files is blind**\n"
            "| tier: candidate | added: 2026-07-29 | tags: pii-harness\n"
            "\n"
            "**Lesson:** Scan tracked plus untracked-but-not-ignored files.\n"
            "**Evidence:** the gate reported green before git add.\n"
            "**Falsifier:** a tracked-only scan that still catches new files.\n"
        )
        lessons, quarantines, _ = entry_parser.parse_library(text)
        self.assertEqual(quarantines, [])
        self.assertEqual(len(lessons), 1)
        e = lessons[0]["entry"]
        self.assertEqual(e["id"], "L0001")
        self.assertIn("untracked", e["lesson"])
        self.assertIn("green", e["evidence"])
        self.assertIn("tracked-only", e["falsifier"])
        self.assertNotIn("extra", e)

    def test_backticked_pipe_joined_fields_parse(self):
        # Tonality writes `tier: candidate` | `added: …` | `tags: …` — the
        # line does NOT start with a pipe, so a leading-pipe rule saw one
        # segment and `tier` swallowed the rest ("invalid tier: 'candidate` |
        # `added: …'"). Backticks are presentation; the pipe is a delimiter.
        text = (
            "### [L0001] A new MCP tool requires a conformance case\n"
            "\n"
            "`tier: candidate` | `added: 2026-07-07` | `tags: workflow, contracts` | `supersedes: —`\n"
            "\n"
            "- **lesson:** Add the CASES entry and regenerate.\n"
            "- **evidence:** test_every_tool_has_a_conformance_case fails.\n"
            "- **falsifier:** a tool added without a case that still passes.\n"
        )
        lessons, quarantines, _ = entry_parser.parse_library(text)
        self.assertEqual(quarantines, [])
        self.assertEqual(len(lessons), 1)
        e = lessons[0]["entry"]
        self.assertEqual(e["tier"], "candidate")
        self.assertEqual(e["added"], "2026-07-07")
        self.assertEqual(e["tags"], ["workflow", "contracts"])
        self.assertNotIn("supersedes", e)  # placeholder → absent

    def test_block_entry_missing_lesson_label_still_quarantines(self):
        # Antiphon's shape: tier/added/evidence/falsifier are labelled, but
        # the lesson is UNLABELLED prose and the tag label is singular. v3
        # admits new delimiters and NO NEW ABSENCE, so this quarantines
        # rather than being rescued by guessing that prose means `lesson`.
        text = (
            "### L0001 — A gate that has never fired is not known to be a gate\n"
            "**tag:** `oracle-boundary` · **tier:** candidate · **added:** 2026-07-13\n"
            "\n"
            "Some unlabelled prose that is morally the lesson.\n"
            "\n"
            "**evidence:** the five-case negative test run at scaffolding.\n"
            "**falsifier:** a gate that passes its negative test but misses a real one.\n"
        )
        lessons, quarantines, _ = entry_parser.parse_library(text)
        self.assertEqual(lessons, [])
        self.assertEqual(len(quarantines), 1)
