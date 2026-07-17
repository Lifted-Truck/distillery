# drop-source-path — no absolute path in any stream record

- **Queue item:** closes the D1 open question ("`source` absolute vs
  repo-relative"); ROADMAP decision 12.
- **Why:** `stream-record.1` stored the source LIBRARY's *absolute* path.
  Sweep returns machine-absolute paths (`/Users/<user>/…`), so this baked the
  local username + directory layout into an append-only journal bound for a
  public remote — a portability + privacy leak. Dropped the path entirely:
  `project` (registry name) is the portable file id (LIBRARY path =
  `registry-resolve(project)/LIBRARY.md`, re-derivable) and `source_hash`
  pins the file's state, so a stored path is both redundant and leaky.
- **Evidence consulted:** dispatch's identical resolution — dispatch
  ROADMAP decision 7 + traces/2026-07-13-portable-facts.md (its FACTS
  collector leaked sweep's `project["path"]`; fix = drop the path, `name` is
  the id, guard test `test_facts_carry_no_absolute_path`). Relayed by the
  human. distillery/ingest.py:113 (the record builder that emitted `source`);
  docs/stream-schema.md common-fields table; ROADMAP D1 open question.
- **Alternatives rejected:** (a) repo-relative path — ill-defined: the roster
  spans multiple roots (`~/Documents/Claude/*`, `~/Documents/Tonality`), so
  "relative to one root" has no answer; `project` already is the portable id,
  so a second path field is redundant (reduce, never invent). (b) Bump to
  `stream-record.2` — ceremony: no real data ever persisted `source` (the
  genesis fill was held), so `.1` is corrected in place before it is
  populated, ratified by decision 12. (c) Borrow dispatch's ruling directly —
  rejected per writes-stay-home; adopted the *principle* and recorded our own
  decision.
- **Change set:** ingest.py drops `source` from the record (keeps the file
  read + source_hash); docs/stream-schema.md updated (common fields +
  invariant restated); fixture stream + goldens regenerated without `source`;
  test_ingest / test_query updated; new guard
  `test_no_record_carries_an_absolute_path` (recursively asserts no record
  string starts with `/`, contains `/Users/`, or starts with `~/`).
- **No history rewrite needed** (unlike dispatch): distillery never committed
  real stream data — only the fixture's harmless relative-fake `source`
  values, now removed going forward. Holding the genesis data (D1 close)
  turned a filter-branch into a plain edit.
- **Verify:** `./verify full` exit 0 — 60 tests (+1 guard) + replay_check OK.
  Recorded hash re-stamped post-commit.
- **Open questions:** none new. Genesis fill still gated only on
  `distillery-002` (multi-line ruling). D3 unblocked (reads the fixture).
