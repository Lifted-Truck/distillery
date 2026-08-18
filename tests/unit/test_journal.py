import contextlib
import io
import json
import os
import tempfile
import unittest

from distillery import journal


class TestJournal(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmpdir.name, "stream.jsonl")

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write_raw(self, content):
        with open(self.path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    def test_load_seen_missing_file_returns_empty_set(self):
        self.assertEqual(journal.load_seen(self.path), set())

    def test_load_seen_basic(self):
        rec1 = {"project": "alpha", "hash": "aaaa", "kind": "lesson"}
        rec2 = {"project": "beta", "hash": "bbbb", "kind": "lesson"}
        self._write_raw(json.dumps(rec1) + "\n" + json.dumps(rec2) + "\n")
        seen = journal.load_seen(self.path)
        self.assertEqual(seen, {("alpha", "aaaa", "lesson"), ("beta", "bbbb", "lesson")})

    def test_load_seen_skips_invalid_middle_line_with_warning_not_crash(self):
        good1 = json.dumps({"project": "alpha", "hash": "aaaa", "kind": "lesson"})
        good2 = json.dumps({"project": "beta", "hash": "bbbb", "kind": "lesson"})
        content = good1 + "\n" + "{not valid json at all\n" + good2 + "\n"
        self._write_raw(content)

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            seen = journal.load_seen(self.path)

        self.assertEqual(seen, {("alpha", "aaaa", "lesson"), ("beta", "bbbb", "lesson")})
        self.assertIn("invalid", stderr.getvalue().lower())

    def test_load_seen_skips_record_missing_project_or_hash(self):
        good = json.dumps({"project": "alpha", "hash": "aaaa", "kind": "lesson"})
        malformed = json.dumps({"project": "beta"})  # missing hash
        self._write_raw(good + "\n" + malformed + "\n")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            seen = journal.load_seen(self.path)
        self.assertEqual(seen, {("alpha", "aaaa", "lesson")})

    def test_repair_partial_tail_truncates_and_reports(self):
        good = json.dumps({"project": "alpha", "hash": "aaaa", "kind": "lesson"}) + "\n"
        partial = '{"project": "beta", "hash": "bb'  # no trailing newline
        self._write_raw(good + partial)

        repaired = journal.repair_partial_tail(self.path)
        self.assertTrue(repaired)

        with open(self.path, encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, good)

        # Subsequent append yields a fully valid file.
        journal.append_records(self.path, [{"project": "gamma", "hash": "cccc"}])
        with open(self.path, encoding="utf-8") as f:
            lines = [l for l in f.read().split("\n") if l]
        self.assertEqual(len(lines), 2)
        for line in lines:
            json.loads(line)  # must not raise

    def test_repair_no_op_when_file_already_well_formed(self):
        good = json.dumps({"project": "alpha", "hash": "aaaa", "kind": "lesson"}) + "\n"
        self._write_raw(good)
        repaired = journal.repair_partial_tail(self.path)
        self.assertFalse(repaired)
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(f.read(), good)

    def test_repair_no_op_when_file_missing(self):
        self.assertFalse(journal.repair_partial_tail(self.path))

    def test_append_records_exact_serialization(self):
        rec = {"b": 1, "a": 2, "unicode": "café"}
        journal.append_records(self.path, [rec])
        with open(self.path, "rb") as f:
            data = f.read()
        expected = (
            json.dumps(rec, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        self.assertEqual(data, expected)

    def test_append_records_empty_list_is_noop_does_not_create_file(self):
        journal.append_records(self.path, [])
        self.assertFalse(os.path.exists(self.path))

    def test_dedup_seen_set_covers_both_record_kinds(self):
        lesson = {"project": "alpha", "hash": "h1", "kind": "lesson"}
        quarantine = {"project": "alpha", "hash": "h2", "kind": "quarantine"}
        journal.append_records(self.path, [lesson, quarantine])
        seen = journal.load_seen(self.path)
        self.assertEqual(seen, {("alpha", "h1", "lesson"), ("alpha", "h2", "quarantine")})

    def test_same_raw_reclassified_by_a_contract_upgrade_is_not_blocked(self):
        # ROADMAP decision 16, deferred to the first post-publication contract
        # upgrade (library-entry.3). A v2 quarantine and its v3 lesson share
        # project AND hash -- the bytes did not change, the grammar did. With
        # kind in the key the lesson can still append, and the historical
        # quarantine survives as append-only history.
        q = {"project": "alpha", "hash": "same", "kind": "quarantine"}
        journal.append_records(self.path, [q])
        seen = journal.load_seen(self.path)
        self.assertIn(("alpha", "same", "quarantine"), seen)
        self.assertNotIn(("alpha", "same", "lesson"), seen)


if __name__ == "__main__":
    unittest.main()
