"""query — pure, deterministic read-side operations over the D1 journal.

Per docs/stream-ops.md (`stream-ops.1`): all functions here are pure
functions of an already-loaded list of journal records (dicts). No wall-clock
reads, no model calls, no mutation of the journal. `today`/`age_days` for
staleness() are parameters injected by the caller (bin/query), never read
from the clock in this module.

Access boundary (charter §Domain, prose-enforced): output of these functions
is for a human, curator, or the D3 analyst — never wired into a working
agent's retrieval context.
"""

import datetime
import hashlib
import json
import re
import sys
import unicodedata


def load_journal(path):
    """Load stream.jsonl into a list of record dicts, in file order.

    Mirrors journal.load_seen's tolerance: a line that fails JSON parsing is
    skipped with a visible stderr warning, never a crash. Blank lines are
    skipped silently (they carry no record).
    """
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            stripped = line.rstrip("\n")
            if not stripped:
                continue
            try:
                rec = json.loads(stripped)
            except ValueError as exc:
                print(
                    "query: skipping invalid JSON at %s:%d: %s" % (path, line_no, exc),
                    file=sys.stderr,
                )
                continue
            records.append(rec)
    return records


def lessons_by_project(records, project, include_quarantine=False):
    """Every kind=="lesson" record for `project`, in journal order.

    If include_quarantine, that project's kind=="quarantine" records are
    interleaved in journal order as well.
    """
    kinds = {"lesson"} if not include_quarantine else {"lesson", "quarantine"}
    return [r for r in records if r.get("project") == project and r.get("kind") in kinds]


def near_signature(lesson_text):
    """16-hex signature over normalized lesson prose (pinned, see docs/stream-ops.md).

    casefold() first, then NFC, then collapse ASCII-whitespace runs, strip.
    """
    norm = unicodedata.normalize("NFC", lesson_text.casefold())
    norm = re.sub(r"[ \t\n\r\f\v]+", " ", norm).strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def recurrences(records, near=False):
    """Group lesson records by signature; keep only groups spanning >=2 distinct projects.

    exact (near=False): signature is record["hash"].
    near (near=True): signature is near_signature(record["entry"]["lesson"]).

    Returns a deterministic list of
        {"signature": sig, "projects": [sorted distinct projects],
         "origins": [sorted origins]}
    sorted by signature. Lessons only; quarantines are ignored.
    """
    groups = {}
    for r in records:
        if r.get("kind") != "lesson":
            continue
        if near:
            sig = near_signature(r["entry"]["lesson"])
        else:
            sig = r["hash"]
        groups.setdefault(sig, []).append(r)

    result = []
    for sig, group_records in groups.items():
        projects = sorted({r["project"] for r in group_records})
        if len(projects) < 2:
            continue
        origins = sorted(r["origin"] for r in group_records)
        result.append({"signature": sig, "projects": projects, "origins": origins})

    result.sort(key=lambda g: g["signature"])
    return result


def staleness(records, today, age_days):
    """Annotate every lesson record fresh|stale, in journal order.

    Returns a list of
        {"origin": ..., "status": "fresh"|"stale",
         "reason": "superseded"|"aged"|None, "superseded_by": origin-or-None}

    Supersession is scoped per project (ids are per-file) and resolves
    transitively via immediate-superseder citation. Supersession outranks
    aged. `today`/`age_days` are parameters; the clock is never read here.
    """
    lessons = [r for r in records if r.get("kind") == "lesson"]

    # Map (project, entry_id) -> origin of the record that supersedes it,
    # per docs/stream-ops.md: "entry.supersedes == this.entry.id" within the
    # same project.
    superseded_by = {}
    for r in lessons:
        entry = r["entry"]
        supersedes = entry.get("supersedes")
        if supersedes:
            key = (r["project"], supersedes)
            superseded_by[key] = r["origin"]

    today_date = datetime.date.fromisoformat(today)
    cutoff = datetime.timedelta(days=age_days)

    result = []
    for r in lessons:
        entry = r["entry"]
        key = (r["project"], entry["id"])
        if key in superseded_by:
            result.append(
                {
                    "origin": r["origin"],
                    "status": "stale",
                    "reason": "superseded",
                    "superseded_by": superseded_by[key],
                }
            )
            continue

        added = datetime.date.fromisoformat(entry["added"])
        if today_date - added > cutoff:
            result.append(
                {
                    "origin": r["origin"],
                    "status": "stale",
                    "reason": "aged",
                    "superseded_by": None,
                }
            )
            continue

        result.append(
            {
                "origin": r["origin"],
                "status": "fresh",
                "reason": None,
                "superseded_by": None,
            }
        )

    return result
