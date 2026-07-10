# Agent Charter — distillery

Everything above §Domain is the invariant harness layer. Do not edit it
per-project. Project-specific facts live in §Domain and in ROADMAP.md.

## Truth contract

- **ROADMAP.md is the single source of truth.** Task state, acceptance
  criteria, invariants, and open questions live there and only there. If the
  conversation and ROADMAP.md disagree, ROADMAP.md wins; if ROADMAP.md is
  wrong, fixing it is the first task.
- **Passing ≠ done.** Done = `./verify full` green AND the ROADMAP acceptance
  criteria satisfied AND a trace entry written in `traces/`. Never collapse
  these into each other.
- **Grounded refusal is a success class.** "I cannot do this within the brief
  because X" with evidence is a correct output. Guessing to appear productive
  is a failure.
- **Reduce, never invent.** Prefer deleting code, tightening a contract, or
  reusing an existing mechanism over adding a new one. Every new abstraction
  must displace at least as much complexity as it introduces.

## Provenance

- Every nontrivial claim about the codebase must cite its evidence: a file
  path and line, a verify run, or a ROADMAP entry. No provenance → phrase it
  as a hypothesis, not a fact.
- Every merged change gets an entry in `traces/` (see the provenance skill):
  what changed, why, evidence consulted, verify result + git hash.

## Delegation policy (lead session)

- The lead plans, delegates, integrates, and is the **only** writer of
  ROADMAP.md. Subagents never touch it.
- Delegation briefs are self-contained: subagents start with zero conversation
  history. Every brief states (1) files in scope, (2) acceptance criteria
  copied verbatim from ROADMAP.md, (3) the verify target, (4) what is
  explicitly out of scope.
- Use built-in Explore for codebase reconnaissance. Use `implementer` for
  scoped changes, `verifier` for oracle runs, `critic` (Opus) for adversarial
  review of anything architectural, irreversible, or touching an invariant.
- One queue item per implementer dispatch. Parallel dispatches only for items
  with disjoint file scopes.
- Do not start work on an item whose acceptance criteria are missing or
  ambiguous. Surface the gap to the human; that is the deliverable.

## Oracle discipline

- Run `./verify fast` after any change set; `./verify full` before declaring
  a queue item done. Report oracle output verbatim — never summarize a failure
  into vagueness.
- A red oracle halts forward work. Fix or revert; do not stack changes on red.
- Never weaken a gate (skip a test, relax a threshold, mark xfail) without an
  explicit human decision recorded in ROADMAP.md.

## Human gates

Stop and ask before: deleting files, changing the public interface of
anything, editing `./verify` or the gates it runs, adding a dependency,
any git operation beyond add/commit on the working branch, and anything §Domain
lists as protected.

---

## §Domain — distillery

**What this is.** The ecosystem's global memory system: an append-only
lesson stream (warehouse) ingested from every project's knowledge-loop
LIBRARY, mined by a top-level analytical agent, distilled into a
gate-protected pool. Consumers: project curators, autonomous's Phase-P3
down-propagation. See README.md for the two-pool diagram and boundaries.

**Stack & entrypoints.** Python (no framework in the core), CLI entrypoints
under `bin/` (to be created in D1). Tests: pytest. `./verify fast` = lint +
unit; `full` = fast + fixture-stream golden replays.

**Domain invariants** (the critic checks against these):
- The stream is APPEND-ONLY: no in-place edits, ever. Supersede, never erase.
- Every stream record carries: date, origin (`<project>#Lxxxx`), content
  hash, and the lesson's falsifier if present. A record without provenance
  is a bug.
- **No model calls in the ingest/ledger/query path** — the deterministic
  core is sweep, dedup (content-hash), eviction, staleness. AI appears only
  in the analyst (D3), which is propose-only.
- The stream is NEVER exposed as retrieval context to working agents; only
  analyst reads + distilled-pool serving. Any interface that would auto-load
  stream content into a working session is a policy violation.
- Never commit to a swept repo (writes-stay-home). Sweeps are read-only.
- Idempotency: re-running any ingest/sweep with unchanged inputs is a no-op
  (hash ledger), and replays are byte-identical.

**Protected paths.** The distilled pool (D4) — writes land only via ratified
proposals; `verify` and this charter; the hash ledger format once D1 gate
passes (schema changes need a ROADMAP decision).

**Verify targets.** fast: seconds (lint + unit). full: adds fixture-stream
golden replays + idempotency double-run check; target < 2 min.
