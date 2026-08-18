import importlib.util
import json
import re
import os
import tempfile
import unittest

from distillery import ingest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
FIXTURES_REGISTRY = os.path.join(REPO_ROOT, "tests", "fixtures", "registry.json")
SWEEP_PATH = os.path.expanduser("~/Documents/Claude/autonomous/kit/sweep/sweep.py")
ALPHA_LIBRARY = os.path.join(REPO_ROOT, "tests", "fixtures", "projects", "alpha", "LIBRARY.md")

# Written as a regex, never a bare "/Users/" literal: this file is itself
# scanned by the repo's leak_gate, and a literal would match itself. The kit's
# own gate documents the same trap and uses the same dodge. (Bonus: this form
# also catches /home/<user>/ and embedded paths, not just a leading slash.)
_ABS_HOME = re.compile(r"/(Users|home)/[^/]+/")


def _load_sweep():
    spec = importlib.util.spec_from_file_location("distillery_test_sweep", SWEEP_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(
    os.path.isfile(SWEEP_PATH),
    "pinned sweep primitive not found at %s (see ROADMAP decision 3)" % SWEEP_PATH,
)
class TestIngestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.sweep_mod = _load_sweep()
        with open(FIXTURES_REGISTRY) as f:
            self.registry = json.load(f)
        self.tmpdir = tempfile.TemporaryDirectory()
        self.stream_path = os.path.join(self.tmpdir.name, "stream.jsonl")
        self.ledger_path = os.path.join(self.tmpdir.name, "ledger.json")
        self.date = "2026-07-10"
        # registry.json fixture uses paths relative to the repo root.
        self._old_cwd = os.getcwd()
        os.chdir(REPO_ROOT)

    def tearDown(self):
        os.chdir(self._old_cwd)
        self.tmpdir.cleanup()

    def _run(self, stream_path=None, ledger_path=None):
        return ingest.run_ingest(
            self.registry,
            self.sweep_mod,
            stream_path or self.stream_path,
            ledger_path or self.ledger_path,
            self.date,
        )

    def _read_jsonl(self, path):
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    # -- (a) first run: expected records, deterministic order ---------------

    def test_first_run_counts(self):
        summary = self._run()
        self.assertEqual(summary["date"], self.date)
        self.assertEqual(summary["projects_swept"], 5)
        self.assertEqual(summary["projects_changed"], 4)
        self.assertEqual(summary["projects_skipped_unchanged"], 0)
        self.assertEqual(summary["projects_no_library"], 1)
        self.assertEqual(summary["appended"], 10)
        self.assertEqual(summary["quarantined"], 9)
        self.assertEqual(summary["skipped_duplicate"], 1)
        self.assertFalse(summary["repaired_partial_tail"])
        self.assertEqual(summary["unclosed_fence_files"], 0)

        records = self._read_jsonl(self.stream_path)
        self.assertEqual(len(records), 19)  # 10 lessons + 9 quarantines
        for rec in records:
            self.assertEqual(rec["v"], "stream-record.1")
            self.assertEqual(rec["swept"], self.date)
            self.assertIn(rec["kind"], ("lesson", "quarantine"))

    def test_no_record_carries_an_absolute_path(self):
        # ROADMAP decision 12: sweep returns machine-absolute paths; none may
        # be baked into the append-only journal (username/layout leak into a
        # public remote). `project` + registry re-derive the file. Mirrors
        # dispatch's test_facts_carry_no_absolute_path. Guards every string
        # value in every record, recursively.
        self._run()
        records = self._read_jsonl(self.stream_path)

        def strings(obj):
            if isinstance(obj, str):
                yield obj
            elif isinstance(obj, dict):
                for v in obj.values():
                    yield from strings(v)
            elif isinstance(obj, list):
                for v in obj:
                    yield from strings(v)

        for rec in records:
            for s in strings(rec):
                self.assertFalse(
                    s.startswith("/") or _ABS_HOME.search(s) or s.startswith("~/"),
                    "record leaks an absolute path: %r in %r" % (s, rec.get("origin") or rec.get("raw")),
                )

    def test_first_run_ordering_registry_then_line_number(self):
        self._run()
        records = self._read_jsonl(self.stream_path)
        projects_order = [r["project"] for r in records]
        # alpha entries precede beta entries precede gamma entries.
        last_alpha = max(i for i, p in enumerate(projects_order) if p == "alpha")
        first_beta = min(i for i, p in enumerate(projects_order) if p == "beta")
        last_beta = max(i for i, p in enumerate(projects_order) if p == "beta")
        first_gamma = min(i for i, p in enumerate(projects_order) if p == "gamma")
        self.assertLess(last_alpha, first_beta)
        self.assertLess(last_beta, first_gamma)

        # within alpha, ascending line_no order (lessons+quarantines interleaved)
        alpha_recs = [r for r in records if r["project"] == "alpha"]
        alpha_line_nos = []
        for r in alpha_recs:
            if r["kind"] == "quarantine":
                alpha_line_nos.append(r["line_no"])
        self.assertEqual(alpha_line_nos, sorted(alpha_line_nos))

    def test_lesson_record_shape_and_provenance(self):
        self._run()
        records = self._read_jsonl(self.stream_path)
        l0002 = next(
            r for r in records
            if r["kind"] == "lesson" and r["entry"]["id"] == "L0002" and r["project"] == "alpha"
        )
        self.assertEqual(l0002["origin"], "alpha#L0002")
        self.assertEqual(l0002["entry_contract"], "library-entry.2")
        # No path field is stored (ROADMAP decision 12): `project` + registry
        # re-derive the file; source_hash pins its state. Absolute paths would
        # leak the local username/layout into the append-only journal.
        self.assertNotIn("source", l0002)
        self.assertEqual(len(l0002["source_hash"]), 16)
        self.assertEqual(len(l0002["hash"]), 16)
        self.assertNotIn("supersedes", l0002["entry"])

    def test_quarantine_record_shape(self):
        self._run()
        records = self._read_jsonl(self.stream_path)
        q = next(
            r for r in records
            if r["kind"] == "quarantine" and r["project"] == "alpha" and r["raw"].startswith("[L0003]")
        )
        self.assertIn("falsifier", q["error"])
        self.assertIsInstance(q["line_no"], int)

    def test_per_project_breakdown(self):
        summary = self._run()
        self.assertEqual(
            summary["per_project"]["alpha"],
            {"appended": 2, "skipped_duplicate": 1, "quarantined": 4},
        )
        self.assertEqual(
            summary["per_project"]["beta"],
            {"appended": 2, "skipped_duplicate": 0, "quarantined": 0},
        )
        self.assertEqual(
            summary["per_project"]["gamma"],
            {"appended": 1, "skipped_duplicate": 0, "quarantined": 0},
        )
        self.assertEqual(
            summary["per_project"]["delta-wrap"],
            {"appended": 5, "skipped_duplicate": 0, "quarantined": 5},
        )
        self.assertNotIn("delta", summary["per_project"])

    # -- (b) idempotency: second run is a no-op -----------------------------

    def test_idempotent_second_run(self):
        self._run()
        with open(self.stream_path, "rb") as f:
            stream_1 = f.read()
        with open(self.ledger_path, "rb") as f:
            ledger_1 = f.read()

        summary2 = self._run()
        self.assertEqual(summary2["appended"], 0)
        self.assertEqual(summary2["skipped_duplicate"], 0)
        self.assertEqual(summary2["quarantined"], 0)
        self.assertEqual(summary2["projects_changed"], 0)
        self.assertEqual(summary2["projects_skipped_unchanged"], 4)
        self.assertEqual(summary2["per_project"], {})

        with open(self.stream_path, "rb") as f:
            stream_2 = f.read()
        with open(self.ledger_path, "rb") as f:
            ledger_2 = f.read()
        self.assertEqual(stream_1, stream_2)
        self.assertEqual(ledger_1, ledger_2)

    # -- (c) byte-identical replay across two fresh tmp dirs ----------------

    def test_byte_identical_replay_fresh_dirs(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            s1, l1 = os.path.join(d1, "stream.jsonl"), os.path.join(d1, "ledger.json")
            s2, l2 = os.path.join(d2, "stream.jsonl"), os.path.join(d2, "ledger.json")
            self._run(stream_path=s1, ledger_path=l1)
            self._run(stream_path=s2, ledger_path=l2)
            with open(s1, "rb") as f:
                b1 = f.read()
            with open(s2, "rb") as f:
                b2 = f.read()
            with open(l1, "rb") as f:
                lb1 = f.read()
            with open(l2, "rb") as f:
                lb2 = f.read()
            self.assertEqual(b1, b2)
            self.assertEqual(lb1, lb2)

    # -- (d) duplicate detection: injected duplicate line -------------------

    def test_duplicate_detection_injected_line(self):
        self._run()
        with open(ALPHA_LIBRARY, encoding="utf-8") as f:
            original = f.read()
        target_line = next(l for l in original.splitlines() if l.startswith("[L0002]"))
        try:
            with open(ALPHA_LIBRARY, "a", encoding="utf-8") as f:
                # Blank-line separated (corpus convention, docs/stream-schema.md
                # marker-open predecessor rule): appending directly with no
                # blank would fold the injected line into the still-open
                # preceding entry's span instead of opening its own.
                f.write("\n" + target_line + "\n")

            summary2 = self._run()
            self.assertGreaterEqual(
                summary2["per_project"].get("alpha", {}).get("skipped_duplicate", 0), 1
            )
            self.assertEqual(summary2["appended"], 0)
        finally:
            with open(ALPHA_LIBRARY, "w", encoding="utf-8") as f:
                f.write(original)

    def test_journal_prefix_is_append_only_across_a_changed_file(self):
        # The journal is append-only (CLAUDE.md §Domain): appending new
        # records to an already-ingested file must never rewrite prior
        # bytes. Run once, mutate a fixture LIBRARY (new blank-separated
        # entry), run again, and assert the first journal's bytes are an
        # exact prefix of the second's.
        self._run()
        with open(self.stream_path, "rb") as f:
            journal_before = f.read()

        with open(ALPHA_LIBRARY, encoding="utf-8") as f:
            original = f.read()
        new_entry = (
            "\n[L0011] Appended for the prefix-guard test | tier: candidate | "
            "added: 2026-07-11 | tags: fixture | lesson: A new entry appended "
            "between two ingest runs. | evidence: Authored for "
            "test_journal_prefix_is_append_only_across_a_changed_file. | "
            "falsifier: If the journal's prior bytes moved, append-only broke.\n"
        )
        try:
            with open(ALPHA_LIBRARY, "a", encoding="utf-8") as f:
                f.write(new_entry)

            summary2 = self._run()
            self.assertEqual(
                summary2["per_project"].get("alpha", {}).get("appended", 0), 1
            )

            with open(self.stream_path, "rb") as f:
                journal_after = f.read()

            self.assertGreater(len(journal_after), len(journal_before))
            self.assertEqual(journal_after[: len(journal_before)], journal_before)
        finally:
            with open(ALPHA_LIBRARY, "w", encoding="utf-8") as f:
                f.write(original)

    # -- (e) ledger-lag self-heal --------------------------------------------

    def test_ledger_lag_self_heals(self):
        self._run()
        os.remove(self.ledger_path)
        with open(self.stream_path, "rb") as f:
            stream_before = f.read()

        summary2 = self._run()
        self.assertEqual(summary2["appended"], 0)
        self.assertEqual(summary2["quarantined"], 0)
        self.assertTrue(os.path.exists(self.ledger_path))

        with open(self.stream_path, "rb") as f:
            stream_after = f.read()
        self.assertEqual(stream_before, stream_after)

    # -- (f) journal-before-ledger crash ordering ----------------------------

    def test_journal_before_ledger_crash_ordering(self):
        original_write_ledger = ingest.write_ledger

        def raising(*_args, **_kwargs):
            raise RuntimeError("simulated crash before ledger write")

        ingest.write_ledger = raising
        try:
            with self.assertRaises(RuntimeError):
                self._run()
        finally:
            ingest.write_ledger = original_write_ledger

        # The journal must already contain the records despite the crash.
        self.assertTrue(os.path.exists(self.stream_path))
        records = self._read_jsonl(self.stream_path)
        self.assertEqual(len(records), 19)
        self.assertFalse(os.path.exists(self.ledger_path))

        # A re-run completes the ledger and appends nothing new. Since the
        # crash left no ledger behind, this re-run re-parses in full (same
        # as the ledger-lag self-heal case); journal dedup still catches
        # every line so nothing new is appended or quarantined.
        summary2 = self._run()
        self.assertEqual(summary2["appended"], 0)
        self.assertEqual(summary2["quarantined"], 0)
        self.assertTrue(os.path.exists(self.ledger_path))
        records_after = self._read_jsonl(self.stream_path)
        self.assertEqual(len(records_after), 19)


if __name__ == "__main__":
    unittest.main()
