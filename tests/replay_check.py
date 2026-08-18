#!/usr/bin/env python3
"""replay_check — Layer-E gate for `./verify full` (ROADMAP D1 gate).

Three checks over the fixture tree, all via the real CLI:
  1. GOLDEN:   a fresh run's summary is byte-identical to tests/golden/fixture-summary.json
  2. REPLAY:   two fresh runs produce byte-identical stream.jsonl + ledger.json
  3. IDEMPOTENT: an immediate re-run is a no-op (zero appends/quarantines,
                 journal and ledger bytes unchanged)

Stdlib-only, deterministic (pinned --date). Run from the repo root. Exit 0
green, 1 red with a named failing check.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(REPO, "tests", "golden", "fixture-summary.json")
SWEEP = os.path.expanduser("~/Documents/Claude/autonomous/kit/sweep/sweep.py")
DATE = "2026-01-01"


def run_ingest(workdir):
    cmd = [
        sys.executable,
        os.path.join(REPO, "bin", "ingest"),
        "--registry", os.path.join(REPO, "tests", "fixtures", "registry.json"),
        "--sweep", SWEEP,
        "--stream", os.path.join(workdir, "stream.jsonl"),
        "--ledger", os.path.join(workdir, "ledger.json"),
        "--date", DATE,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    if proc.returncode != 0:
        print("replay_check: ingest exited %d\n%s" % (proc.returncode, proc.stderr))
        sys.exit(1)
    return proc.stdout


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def main():
    failures = []
    tmp = tempfile.mkdtemp(prefix="distillery-replay-")
    try:
        dir_a = os.path.join(tmp, "a")
        dir_b = os.path.join(tmp, "b")
        os.makedirs(dir_a)
        os.makedirs(dir_b)

        # 1. GOLDEN
        out_a = run_ingest(dir_a)
        golden = read_bytes(GOLDEN).decode("utf-8")
        if out_a != golden:
            failures.append("GOLDEN: summary differs from tests/golden/fixture-summary.json")

        # 2. REPLAY (fresh second environment)
        run_ingest(dir_b)
        for name in ("stream.jsonl", "ledger.json"):
            if read_bytes(os.path.join(dir_a, name)) != read_bytes(os.path.join(dir_b, name)):
                failures.append("REPLAY: %s not byte-identical across fresh runs" % name)

        # 3. IDEMPOTENT (re-run in place)
        before_stream = read_bytes(os.path.join(dir_a, "stream.jsonl"))
        before_ledger = read_bytes(os.path.join(dir_a, "ledger.json"))
        summary2 = json.loads(run_ingest(dir_a))
        if summary2["appended"] != 0 or summary2["quarantined"] != 0:
            failures.append(
                "IDEMPOTENT: second run appended=%d quarantined=%d (expected 0/0)"
                % (summary2["appended"], summary2["quarantined"])
            )
        if summary2["projects_changed"] != 0:
            failures.append(
                "IDEMPOTENT: second run projects_changed=%d (expected 0)"
                % summary2["projects_changed"]
            )
        if read_bytes(os.path.join(dir_a, "stream.jsonl")) != before_stream:
            failures.append("IDEMPOTENT: journal bytes changed on a no-op run")
        if read_bytes(os.path.join(dir_a, "ledger.json")) != before_ledger:
            failures.append("IDEMPOTENT: ledger bytes changed on a no-op run")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        for f in failures:
            print("replay_check: FAIL %s" % f)
        return 1
    print("replay_check: OK (golden, replay, idempotency)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
