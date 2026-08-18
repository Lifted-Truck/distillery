# distillery — ROADMAP

> **Single source of truth for this project's direction.** Phase gates are
> never weakened to pass. Ecosystem-level sequencing lives in
> autonomous/ROADMAP.md (Ecosystem tracks); this file defers to it on
> cross-project ordering only.

## Build sequence (phase-gated)

- **D0 — Charter.** Directory scaffolded, manifest drafted, brief filed with
  autonomous, boundaries stated. *Gate: human ratifies the manifest and this
  roadmap.* **CLOSED 2026-07-10** (user go-ahead; brief answered —
  contracts pinned below).
- **D1 — The stream (deterministic ingest).** Append-only journal schema
  (dated, provenance, origin LIBRARY id, content hash); ingest CLI that
  sweeps configured roots (hash-ledgered, skip-unchanged — reuse/extract the
  audit loop's SCAN, don't reimplement); idempotent re-runs. NO model calls
  anywhere in D1. *Gate: two consecutive sweeps over the real project tree —
  second is a no-op; injected duplicate lesson is detected; ledger replays
  byte-identical; `./verify full` green.* **CLOSED 2026-07-11** — gate met
  on the real tree (44 projects, 18 LIBRARYs → 28 records); double-sweep
  no-op, injected-dup `skipped_duplicate:8/appended:0`, ledger self-heals
  byte-identical, `./verify full` green (independent verifier). Trace:
  traces/2026-07-11-d1-stream-ingest.md. Follow-ups owed by the provider
  (distillery-002) and the daily-schedule wiring do not gate closure.
- **D2 — Stream operations.** Deterministic staleness
  annotation + provenance queries ("show every lesson from project X", "show
  recurrences of signature Y"). *Gate: golden query results (lessons /
  recurrences exact+near / staleness) over a fixture stream.* **Scope pinned
  2026-07-11 (decisions 9, 11):** deterministic staleness only (supersession
  + age); "signature" = deterministic content-hash / normalized-text
  grouping, NOT semantic detection (D3's boundary). **Eviction/compaction
  (segment + archive) DEFERRED** — see Deferred/demoted; it is speculative at
  current scale and introduces a D1-dedup seam that must be designed in, not
  bolted on. **CLOSED 2026-07-13** — `distillery/query.py` + `bin/query`
  (lessons/recurrences-exact+near/staleness), golden query gate over the
  13-record fixture stream green in the unit suite, `./verify full` green
  (59 tests, independent verifier). Two critic rounds shaped it (archive
  deferred; near-signature boundary ruled). Traces:
  traces/2026-07-13-d2-query-cli.md + traces/2026-07-13-d2-close.md.
- **D3 — The analyst.** **← current phase.** Fan-out read-only analysis over the stream
  (fresh-context subagents, distilled ≤2K-token findings); recurrence and
  contradiction detection; output = dated `proposals/<date>.proposal.md`
  (propose-only, ready-to-apply entries with origins + falsifiers — same
  staging pattern as the audit loop). *Gate: analyst run over the fixture
  stream surfaces a planted cross-project recurrence and a planted
  contradiction; zero direct writes to any pool.*
- **D4 — The distilled pool + serving.** Promotion gates implemented per the
  cross-proliferation standard (autonomous README §4c); how curators and
  projects consume the pool (retrieval interface, INDEX-first); wiring into
  autonomous Phase P3's down-propagation. *Gate: one lesson travels the full
  path — project LIBRARY → stream → analyst proposal → human-ratified
  promotion → consumed by a different project — with provenance intact at
  every hop.*

## Decisions on record

Moved to [DECISIONS.md](DECISIONS.md) (append-only) on 2026-08-18 —
kit 2.0.0 requires a standalone decision log. Decisions 1–20 migrated
verbatim; 21+ are recorded there. This file keeps task state,
acceptance criteria, invariants and open questions.

## Explicit debt (recorded, not hidden)

- **CLEARED 2026-08-18** — the parser was `library-entry.2` while the contract
  was v3; it is now v3 (DECISIONS 21). Block form admitted on read, `absorbs`
  registered as a real field. Accounting filed to autonomous as
  `report-003`: 23 cleared, 43 newly visible, 160/160 prior lessons
  preserved, 0 lost, append-only prefix intact.
- Mailbox contract-test fixtures still owe their v3 refresh (autonomous:
  "your obligation-2 mailbox refresh now has more to carry").

## Open questions (blocking, ask the human)

- (none currently) — the genesis fill remains gated only on `distillery-002`
  (decision 8, provider ball, respond-by 2026-07-18): committing the real
  stream now would bake in 7 quarantine records that a `library-entry.2`
  continuation grammar could later turn into lessons, permanently superseded
  in the append-only history. Not a blocker for D3 (the analyst reads the
  fixture stream; the real fill can follow the ruling).

## Answered (moved from open questions)

- **Storage form** (2026-07-10, human): **jsonl-in-git** — one append-only
  `stream/stream.jsonl` committed to this repo. Byte-identical replays and
  append-only-by-construction come free; SQLite may be added later as a
  *derived* index without touching the journal (a D2+ decision if queries
  demand it).
- **Sweep cadence** (2026-07-10, human): **daily** unattended ingest sweep
  (read-only + own-journal writes, authorized by the manifest). Idempotency
  makes no-op days free. Schedule wiring lands after the D1 gate passes.

- **Sweep scope** (2026-07-10): the canonical ecosystem allowlist at
  `autonomous/registry.json` (autonomous Decision 14). Rule-based; groups
  recurse one level (synthetic-worlds is a group of ~16 projects); harness/
  loop status is derived at sweep time — nonconforming or loop-less projects
  are recorded-and-quarantined, never sweep blockers.

## Deferred / demoted

- Ecosystem-lead role (see autonomous/ROADMAP.md — gated, post-D4).
- Embedding-based dedup/similarity (D1 uses content-hash + textual match;
  embeddings only if measurably needed).
- **Stream eviction / compaction (segment + archive)** — bounding the live
  working set once it grows large. Deferred from D2 (decision 11): speculative
  at 28 records (~180× below the 5000-record trigger) and it introduces a
  D1-dedup seam (archived keys leave `load_seen`'s live-only scan → re-append
  on the next changed-LIBRARY ingest). Revive when the live journal actually
  approaches the threshold; the design (crash-atomic segments + recover() +
  the mandatory dedup-union/key-index conservation fix) is captured in
  decision 11 and the git history of docs/stream-ops.md. Not a blocker for
  D3/D4 — the analyst reads the whole stream regardless of segmentation.
- **Human-facing roadmap roundup** — a digest of every project's
  ROADMAP/status for human viewing. **Owner: `dispatch`** (confirmed with
  the human 2026-07-11); NOT distillery — this is the *lesson* pipeline, not
  roadmap aggregation. Captured here only as a pointer so it is not re-raised
  against distillery; the work lives on dispatch's roadmap.
