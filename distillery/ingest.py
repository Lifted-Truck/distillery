"""ingest — the deterministic core of D1: sweep -> parse -> journal -> ledger.

No model calls, no network, no wall-clock reads. `date` is a parameter; the
only wall-clock read in the whole ingest path lives at the edge in
bin/ingest. Reuses the pinned shared sweep primitive
(autonomous/kit/sweep/sweep.py) for registry resolution and hash-ledgered
change detection — never reimplemented here.
"""

import hashlib
import json
import os

from distillery import entry_parser, journal

STREAM_RECORD_VERSION = "stream-record.1"
ENTRY_CONTRACT_VERSION = "library-entry.2"


def _sha256_16(data):
    return hashlib.sha256(data).hexdigest()[:16]


def write_ledger(ledger_path, new_ledger):
    """Write ledger.json byte-identical to sweep.py's --update-ledger output.

    A separate top-level function so a crash-ordering test can monkeypatch
    it to simulate a failure between the journal write and the ledger write.
    """
    parent = os.path.dirname(ledger_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(ledger_path, "w") as f:
        json.dump(new_ledger, f, indent=2, sort_keys=True)
        f.write("\n")


def _load_ledger(ledger_path):
    if not os.path.exists(ledger_path):
        return {}
    with open(ledger_path) as f:
        return json.load(f)


def run_ingest(registry, sweep_mod, stream_path, ledger_path, date):
    """Run one ingest pass. Returns the deterministic run summary dict.

    registry    -- loaded registry.json dict
    sweep_mod   -- the loaded sweep.py module (resolve/derive_status/sweep)
    stream_path -- path to stream.jsonl
    ledger_path -- path to ledger.json
    date        -- YYYY-MM-DD string (the "swept" stamp); never read here
    """
    ledger = _load_ledger(ledger_path)
    records = sweep_mod.sweep(registry, targets=["LIBRARY.md"], ledger=ledger)

    changed_records = []
    no_library = 0
    skipped_unchanged = 0

    for rec in records:
        if rec["hash"] is None:
            no_library += 1
            continue
        if rec["changed"]:
            changed_records.append(rec)
        else:
            skipped_unchanged += 1

    seen = journal.load_seen(stream_path)
    repaired = journal.repair_partial_tail(stream_path)

    new_records = []
    per_project = {}
    total_appended = 0
    total_skipped_dup = 0
    total_quarantined = 0
    unclosed_fence_files = 0

    for proj in changed_records:
        name = proj["name"]
        path = proj["path"]
        lib_path = os.path.join(path, "LIBRARY.md")

        with open(lib_path, "rb") as f:
            raw_bytes = f.read()
        # source_hash pins WHICH state of the file produced this record. The
        # file PATH is deliberately NOT stored: sweep returns machine-absolute
        # paths that would leak the local username + layout into the
        # append-only journal (ROADMAP decision 12). `project` + the registry
        # re-derive the LIBRARY path when needed; source_hash carries no path.
        source_hash = _sha256_16(raw_bytes)
        text = raw_bytes.decode("utf-8")

        lessons, quarantines, parse_meta = entry_parser.parse_library(text)
        if parse_meta["unclosed_fence"]:
            unclosed_fence_files += 1
        combined = [(l["line_no"], "lesson", l) for l in lessons]
        combined += [(q["line_no"], "quarantine", q) for q in quarantines]
        combined.sort(key=lambda t: t[0])

        appended = 0
        skipped_dup = 0
        quarantined = 0

        for line_no, kind, item in combined:
            raw = item["raw"]
            line_hash = _sha256_16(raw.encode("utf-8"))
            key = (name, line_hash)

            if key in seen:
                skipped_dup += 1
                continue
            seen.add(key)

            common = {
                "v": STREAM_RECORD_VERSION,
                "swept": date,
                "project": name,
                "source_hash": source_hash,
                "hash": line_hash,
                "raw": raw,
            }

            if kind == "lesson":
                entry = item["entry"]
                common["kind"] = "lesson"
                common["origin"] = "%s#%s" % (name, entry["id"])
                common["entry"] = entry
                common["entry_contract"] = ENTRY_CONTRACT_VERSION
                appended += 1
            else:
                common["kind"] = "quarantine"
                common["line_no"] = line_no
                common["error"] = item["error"]
                quarantined += 1

            new_records.append(common)

        total_appended += appended
        total_skipped_dup += skipped_dup
        total_quarantined += quarantined

        if appended or skipped_dup or quarantined:
            per_project[name] = {
                "appended": appended,
                "skipped_duplicate": skipped_dup,
                "quarantined": quarantined,
            }

    # Journal-before-ledger: fsync the journal append BEFORE the ledger write.
    journal.append_records(stream_path, new_records)

    new_ledger = {r["name"]: r["hash"] for r in records}
    write_ledger(ledger_path, new_ledger)

    return {
        "date": date,
        "projects_swept": len(records),
        "projects_changed": len(changed_records),
        "projects_skipped_unchanged": skipped_unchanged,
        "projects_no_library": no_library,
        "appended": total_appended,
        "skipped_duplicate": total_skipped_dup,
        "quarantined": total_quarantined,
        "repaired_partial_tail": repaired,
        "per_project": per_project,
        "unclosed_fence_files": unclosed_fence_files,
    }
