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
  byte-identical; `./verify full` green.* **← current phase**
- **D2 — Stream operations.** Eviction/compaction policy for the warehouse
  (append-only ≠ unbounded working set: segment + archive), staleness
  annotation (falsifier re-run where lessons carry verification commands),
  provenance queries ("show every lesson from project X", "show recurrences
  of signature Y"). *Gate: golden query results over a fixture stream;
  archive/restore round-trip.*
- **D3 — The analyst.** Fan-out read-only analysis over the stream
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

## Decisions on record (append-only)

1. **Names/pools per autonomous Decision 11** — append-only stream (analyst
   only) + distilled pool (gate-entered). The stream is never working-agent
   retrieval context.
2. **Reuse the audit loop's SCAN mechanics** rather than reimplementing —
   file a brief with agent-knowledge-loop if extraction into a shared
   primitive is needed.
3. **Pins** (2026-07-10, per autonomous's response to distillery-001):
   `library-entry.1` (validation contract; malformed entries quarantine
   visibly, never block) and the shared sweep primitive
   (`autonomous/kit/sweep/sweep.py`; our own ledger file). P3 hand-off
   recorded: gates implemented HERE, spec canonical in autonomous doctrine.
   Owed: contract-test fixtures for `library-entry.1` (author during D1,
   file via the integrations channel).

## Open questions (blocking, ask the human)

- Sweep cadence for ingest (daily? on the audit loop's weekly rhythm?).
- Storage form for the stream (jsonl-in-git vs SQLite+jsonl à la Beads).

## Answered (moved from open questions)

- **Sweep scope** (2026-07-10): the canonical ecosystem allowlist at
  `autonomous/registry.json` (autonomous Decision 14). Rule-based; groups
  recurse one level (synthetic-worlds is a group of ~16 projects); harness/
  loop status is derived at sweep time — nonconforming or loop-less projects
  are recorded-and-quarantined, never sweep blockers.

## Deferred / demoted

- Ecosystem-lead role (see autonomous/ROADMAP.md — gated, post-D4).
- Embedding-based dedup/similarity (D1 uses content-hash + textual match;
  embeddings only if measurably needed).
