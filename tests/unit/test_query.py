import json
import os
import subprocess
import sys
import unittest

from distillery import query

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
FIXTURE_STREAM = os.path.join(REPO_ROOT, "tests", "fixtures", "stream", "stream.jsonl")
GOLDEN_DIR = os.path.join(REPO_ROOT, "tests", "golden")
BIN_QUERY = os.path.join(REPO_ROOT, "bin", "query")


def _lesson(project, entry_id, lesson_text, added, supersedes=None, origin=None):
    entry = {
        "id": entry_id,
        "title": "t",
        "tier": "candidate",
        "added": added,
        "tags": ["x"],
        "lesson": lesson_text,
        "evidence": "e.",
        "falsifier": "f.",
    }
    if supersedes:
        entry["supersedes"] = supersedes
    raw = "[%s] t | candidate | added: %s | tags: x | lesson: %s | evidence: e. | falsifier: f." % (
        entry_id,
        added,
        lesson_text,
    )
    return {
        "v": "stream-record.1",
        "kind": "lesson",
        "swept": "2026-07-05",
        "project": project,
        "source": "x",
        "source_hash": "0" * 16,
        "hash": "h-%s-%s" % (project, entry_id),
        "raw": raw,
        "origin": origin or ("%s#%s" % (project, entry_id)),
        "entry": entry,
        "entry_contract": "library-entry.1",
    }


class TestLoadJournal(unittest.TestCase):
    def test_loads_fixture_stream_in_order(self):
        records = query.load_journal(FIXTURE_STREAM)
        self.assertEqual(len(records), 13)
        self.assertEqual(records[0]["origin"], "alpha#L0001")
        self.assertEqual(records[-1]["kind"], "quarantine")

    def test_skips_invalid_json_line_with_warning(self, ):
        import io
        import contextlib
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "stream.jsonl")
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write('{"a":1}\n')
                f.write("not json\n")
                f.write("\n")
                f.write('{"a":2}\n')
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                records = query.load_journal(path)
            self.assertEqual(records, [{"a": 1}, {"a": 2}])
            self.assertIn("skipping invalid JSON", buf.getvalue())


class TestLessonsByProject(unittest.TestCase):
    def setUp(self):
        self.records = query.load_journal(FIXTURE_STREAM)

    def test_alpha_lessons_in_journal_order(self):
        result = query.lessons_by_project(self.records, "alpha")
        origins = [r["origin"] for r in result]
        self.assertEqual(
            origins,
            ["alpha#L0001", "alpha#L0002", "alpha#L0003", "alpha#L0004", "alpha#L0005", "alpha#L0006"],
        )
        self.assertTrue(all(r["kind"] == "lesson" for r in result))

    def test_beta_lessons_excludes_quarantine_by_default(self):
        result = query.lessons_by_project(self.records, "beta")
        self.assertEqual([r["origin"] for r in result], ["beta#L0005", "beta#L0001"])

    def test_beta_include_quarantine_interleaves_in_journal_order(self):
        result = query.lessons_by_project(self.records, "beta", include_quarantine=True)
        kinds = [(r["kind"], r.get("origin", r.get("project"))) for r in result]
        # journal order: beta#L0005 (line 6), beta#L0001 (line 9), quarantine (line 13)
        self.assertEqual(
            kinds,
            [("lesson", "beta#L0005"), ("lesson", "beta#L0001"), ("quarantine", "beta")],
        )

    def test_unknown_project_returns_empty(self):
        self.assertEqual(query.lessons_by_project(self.records, "nope"), [])


class TestNearSignature(unittest.TestCase):
    def test_case_insensitive(self):
        self.assertEqual(query.near_signature("Hello World"), query.near_signature("hello world"))

    def test_whitespace_collapsed(self):
        self.assertEqual(
            query.near_signature("hello   world\t\n"), query.near_signature("hello world")
        )

    def test_nfc_normalization(self):
        # "é" as a single codepoint vs "e" + combining acute (NFD)
        precomposed = "café"
        decomposed = "café"
        self.assertEqual(query.near_signature(precomposed), query.near_signature(decomposed))

    def test_trailing_punctuation_is_NOT_normalized_away(self):
        # Pinned normalization (docs/stream-ops.md) is casefold + NFC + ASCII
        # whitespace-collapse + strip only -- it does not touch punctuation.
        # A trailing period is a real difference under the pinned algorithm.
        self.assertNotEqual(
            query.near_signature("abstraction."), query.near_signature("abstraction")
        )

    def test_pinned_formula_exact(self):
        import hashlib
        import re
        import unicodedata

        text = "  Some   Lesson\tText\n"
        norm = unicodedata.normalize("NFC", text.casefold())
        norm = re.sub(r"[ \t\n\r\f\v]+", " ", norm).strip()
        expected = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]
        self.assertEqual(query.near_signature(text), expected)


class TestRecurrencesExact(unittest.TestCase):
    def setUp(self):
        self.records = query.load_journal(FIXTURE_STREAM)

    def test_finds_alpha_beta_L0005_group_only(self):
        groups = query.recurrences(self.records, near=False)
        self.assertEqual(len(groups), 1)
        g = groups[0]
        self.assertEqual(g["signature"], "cfc86559051d0fab")
        self.assertEqual(g["projects"], ["alpha", "beta"])
        self.assertEqual(g["origins"], ["alpha#L0005", "beta#L0005"])

    def test_id_collision_beta_gamma_L0001_not_grouped(self):
        groups = query.recurrences(self.records, near=False)
        all_origins = set()
        for g in groups:
            all_origins.update(g["origins"])
        self.assertNotIn("beta#L0001", all_origins)
        self.assertNotIn("gamma#L0001", all_origins)

    def test_within_project_gamma_pair_not_grouped(self):
        groups = query.recurrences(self.records, near=False)
        all_origins = set()
        for g in groups:
            all_origins.update(g["origins"])
        self.assertNotIn("gamma#L0002", all_origins)
        self.assertNotIn("gamma#L0003", all_origins)

    def test_groups_sorted_by_signature(self):
        groups = query.recurrences(self.records, near=False)
        sigs = [g["signature"] for g in groups]
        self.assertEqual(sigs, sorted(sigs))


class TestRecurrencesNear(unittest.TestCase):
    def setUp(self):
        self.records = query.load_journal(FIXTURE_STREAM)

    def test_exact_recurrence_also_groups_under_near(self):
        # Identical text is trivially near-equal too.
        groups = query.recurrences(self.records, near=True)
        origin_sets = [set(g["origins"]) for g in groups]
        self.assertIn({"alpha#L0005", "beta#L0005"}, origin_sets)

    def test_fixture_alpha_gamma_L0006_near_groups_across_projects(self):
        # The fixture's near-recurrence pair (alpha#L0006 / gamma#L0006)
        # differs by case + internal whitespace ONLY (both end with a period).
        # Under the pinned near_signature (casefold + NFC + ASCII-whitespace
        # collapse + strip; punctuation stays significant, ROADMAP decision 9)
        # they share a near-signature and group -- and exact mode does NOT
        # group them (different raw), so --near finds a group --exact misses.
        near_groups = query.recurrences(self.records, near=True)
        near_origins = {o for g in near_groups for o in g["origins"]}
        self.assertIn("alpha#L0006", near_origins)
        self.assertIn("gamma#L0006", near_origins)

        exact_groups = query.recurrences(self.records, near=False)
        exact_origins = {o for g in exact_groups for o in g["origins"]}
        self.assertNotIn("alpha#L0006", exact_origins)
        self.assertNotIn("gamma#L0006", exact_origins)

    def test_synthetic_near_case_whitespace_recurrence_groups_across_projects(self):
        recs = [
            _lesson("p1", "L0001", "Prefer deleting code over adding an abstraction", "2026-01-01"),
            _lesson("p2", "L0001", "prefer  deleting   code over adding an abstraction", "2026-01-02"),
        ]
        groups = query.recurrences(recs, near=True)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["projects"], ["p1", "p2"])
        self.assertEqual(groups[0]["origins"], ["p1#L0001", "p2#L0001"])

    def test_synthetic_within_project_near_pair_not_grouped(self):
        recs = [
            _lesson("p1", "L0001", "Same text here", "2026-01-01"),
            _lesson("p1", "L0002", "same   text here", "2026-01-02"),
        ]
        groups = query.recurrences(recs, near=True)
        self.assertEqual(groups, [])


class TestStaleness(unittest.TestCase):
    def setUp(self):
        self.records = query.load_journal(FIXTURE_STREAM)

    def _by_origin(self, results):
        return {r["origin"]: r for r in results}

    def test_supersession_chain(self):
        results = self._by_origin(query.staleness(self.records, "2026-07-11", 180))
        self.assertEqual(results["alpha#L0002"]["status"], "stale")
        self.assertEqual(results["alpha#L0002"]["reason"], "superseded")
        self.assertEqual(results["alpha#L0002"]["superseded_by"], "alpha#L0003")

        self.assertEqual(results["alpha#L0003"]["status"], "stale")
        self.assertEqual(results["alpha#L0003"]["reason"], "superseded")
        self.assertEqual(results["alpha#L0003"]["superseded_by"], "alpha#L0004")

        self.assertEqual(results["alpha#L0004"]["status"], "fresh")
        self.assertIsNone(results["alpha#L0004"]["reason"])
        self.assertIsNone(results["alpha#L0004"]["superseded_by"])

    def test_supersession_scoped_per_project_id_collision_unaffected(self):
        # beta#L0001 / gamma#L0001 are unrelated per-file-id collisions; make
        # sure supersession lookups are keyed by (project, id), not id alone.
        results = self._by_origin(query.staleness(self.records, "2026-07-11", 180))
        self.assertEqual(results["beta#L0001"]["status"], "fresh")
        self.assertEqual(results["gamma#L0001"]["status"], "fresh")

    def test_aged_when_not_superseded_supersession_outranks_aged(self):
        # Inline fixture: an old lesson that is NOT superseded must be aged.
        old_not_superseded = _lesson("p1", "L0001", "old lesson", "2026-01-01")
        old_but_superseded = [
            _lesson("p2", "L0001", "old lesson v1", "2026-01-01"),
            _lesson("p2", "L0002", "old lesson v2", "2026-01-02", supersedes="L0001"),
        ]
        recs = [old_not_superseded] + old_but_superseded
        results = self._by_origin(query.staleness(recs, "2026-07-11", 180))

        # aged, not superseded
        self.assertEqual(results["p1#L0001"]["status"], "stale")
        self.assertEqual(results["p1#L0001"]["reason"], "aged")
        self.assertIsNone(results["p1#L0001"]["superseded_by"])

        # superseded AND old -- supersession must win, precedence explicit
        self.assertEqual(results["p2#L0001"]["status"], "stale")
        self.assertEqual(results["p2#L0001"]["reason"], "superseded")
        self.assertEqual(results["p2#L0001"]["superseded_by"], "p2#L0002")

    def test_fresh_lesson_not_aged_not_superseded(self):
        recs = [_lesson("p1", "L0001", "fresh lesson", "2026-07-01")]
        results = self._by_origin(query.staleness(recs, "2026-07-11", 180))
        self.assertEqual(results["p1#L0001"]["status"], "fresh")
        self.assertIsNone(results["p1#L0001"]["reason"])
        self.assertIsNone(results["p1#L0001"]["superseded_by"])

    def test_journal_order_preserved(self):
        results = query.staleness(self.records, "2026-07-11", 180)
        origins = [r["origin"] for r in results]
        expected = [r["origin"] for r in self.records if r["kind"] == "lesson"]
        self.assertEqual(origins, expected)


class TestGoldenCLI(unittest.TestCase):
    """Re-run bin/query and assert stdout == committed golden bytes."""

    def _run(self, *args):
        result = subprocess.run(
            [sys.executable, BIN_QUERY, "--stream", FIXTURE_STREAM] + list(args),
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def _assert_matches_golden(self, golden_name, *args):
        golden_path = os.path.join(GOLDEN_DIR, golden_name)
        with open(golden_path, "r", encoding="utf-8") as f:
            expected = f.read()
        actual = self._run(*args)
        self.assertEqual(actual, expected)

    def test_lessons_alpha_golden(self):
        self._assert_matches_golden("q-lessons-alpha.json", "lessons", "--project", "alpha")

    def test_recurrences_golden(self):
        self._assert_matches_golden("q-recurrences.json", "recurrences")

    def test_recurrences_near_golden(self):
        self._assert_matches_golden("q-recurrences-near.json", "recurrences", "--near")

    def test_staleness_golden(self):
        self._assert_matches_golden(
            "q-staleness.json", "staleness", "--today", "2026-07-11", "--age-days", "180"
        )


if __name__ == "__main__":
    unittest.main()
