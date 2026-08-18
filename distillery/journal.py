"""journal — append-only jsonl operations for stream/stream.jsonl.

Serialization is byte-exact per docs/stream-schema.md:
    json.dumps(rec, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
written through open(path, "a", encoding="utf-8", newline="\n").

No wall-clock reads. Readers never crash on a malformed line (skip + visible
stderr warning). The sole permitted mutation of an existing journal is
truncating a crash-artifact partial trailing line before appending.
"""

import json
import os
import sys


def load_seen(path):
    """Scan the journal, returning the set of (project, hash) seen-keys.

    Invalid lines (bad JSON, or missing project/hash) are skipped with a
    visible stderr warning — never a crash.
    """
    seen = set()
    if not os.path.exists(path):
        return seen

    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            stripped = line.rstrip("\n")
            if not stripped:
                continue
            try:
                rec = json.loads(stripped)
            except ValueError as exc:
                print(
                    "journal: skipping invalid JSON at %s:%d: %s" % (path, line_no, exc),
                    file=sys.stderr,
                )
                continue
            try:
                seen.add((rec["project"], rec["hash"]))
            except (KeyError, TypeError):
                print(
                    "journal: skipping malformed record (missing project/hash) at %s:%d"
                    % (path, line_no),
                    file=sys.stderr,
                )
                continue
    return seen


def repair_partial_tail(path):
    """Truncate a crash-artifact partial trailing line (no final '\\n').

    Returns True if a repair was performed, False if the file was already
    well-formed (or absent/empty).
    """
    if not os.path.exists(path):
        return False

    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        if size == 0:
            return False
        f.seek(-1, os.SEEK_END)
        last_byte = f.read(1)

    if last_byte == b"\n":
        return False

    with open(path, "rb") as f:
        data = f.read()
    last_nl = data.rfind(b"\n")
    truncate_to = last_nl + 1 if last_nl != -1 else 0

    with open(path, "r+b") as f:
        f.truncate(truncate_to)
        f.flush()
        os.fsync(f.fileno())
    return True


def append_records(path, records):
    """Append records (list of dicts) with the exact wire serialization.

    Flushes and fsyncs before returning. No-op if records is empty (does not
    even open the file, so a no-op run never touches the journal's mtime).
    """
    if not records:
        return
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
            f.write("\n")
        f.flush()
        os.fsync(f.fileno())
