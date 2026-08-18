# genesis-commit-roundup — the warehouse enters version control; distillery-004 filed

- **Queue item:** unqueued (human-directed roundup + genesis commit);
  recorded against ROADMAP decisions 16/17.
- **Why:** The D1 genesis hold's two conditions were discharged — the
  absolute-path leak was fixed before any data persisted (decision 12) and
  the contract ambiguities were ruled, with the journal regenerated from
  empty under `library-entry.2` (decision 16). Holding longer would have
  been the recursive perfect-moment trap: there will always be a pending
  ruling. D3's analyst wants a versioned substrate.
- **Roundup sweep (2026-08-12):** 63 projects swept, 7 changed, 12 new
  lessons + 5 quarantines. New: HYPERSAW consolidation (5 canonical),
  plainsynth (2, new project), Place#L0012, FOUNDATIONS#L0005,
  Tonality-Live (2). Quarantines: 2 HYPERSAW consolidation-grammar
  (→ distillery-004), 3 spectrogen heading-style (→ distillery-003, now
  failing loudly instead of silently — the v2 heading rule working).
- **Genesis commit (`f20289f`):** 168 records = 138 lessons + 30
  quarantines, 63 projects, uniformly `library-entry.2`. Pre-commit
  leak-scan: 0 hits for `/`-prefixed, `/Users/`, `~/`, or the username
  across every string in every record. Append-only in force from here.
  Accepted cost: 3 spectrogen quarantines pending a ruling — correct under
  the current contract; a ruling supersedes rather than falsifies them.
- **Evidence consulted:** stream/stream.jsonl (post-sweep), ROADMAP
  decisions 12/14/16/17 and the §Open-questions hold rationale, dispatch's
  traces/2026-07-13-portable-facts.md (the leak they had to filter-branch
  because they committed first), bin/query recurrence output (both modes
  empty over the live stream).
- **Alternatives rejected:** (a) keep holding until distillery-003 rules —
  rejected as recursive (the class of pending rulings never empties) and
  low-cost (3 of 168 records, superseded not falsified); (b) gitignore the
  stream permanently and treat it as regenerable cache — rejected: D3 needs
  a stable, citable substrate, and "reproducible" is not "reproduced
  identically after a LIBRARY edits itself".
- **distillery-004 filed** (ball: provider): `supersedes` is single-valued
  but consolidation is many-to-one, and "absorbs" ≠ "replaces" (folded-in
  evidence vs invalidation). Three options offered; weak stated preference
  for a distinct `absorbs:` field. Also nudged the two open filings
  (distillery-003; report-002 §3 grammar rules + bare-tier discrepancy).
- **Candidate #3 forming, deliberately NOT designated:** a four-project
  convergence on *verify the verifier* with zero textual recurrence. Both
  D2 signature queries return empty, so it is invisible to deterministic
  detection — the sharpest D3 test case yet. Designation requires the
  analyst's proposal; asserting it by hand would bypass the machinery D3
  exists to build (decision 13's routing discipline).
- **Verify:** `./verify full` exit 0 — 82 tests + replay_check OK; re-stamped
  post-commit at `f20289f`.
- **Open questions:** three provider filings outstanding (002 §3, 003, 004);
  mailbox contract-test fixture refresh still owed (tracked). D3 is the open
  phase.
