# distillery

**The global memory system** for the development ecosystem: every project's
knowledge loop feeds an append-only stream; a top-level analytical agent mines
it; distilled, gate-checked lessons flow back out. Two pools, one direction of
trust.

*Part of the autonomous-paradigm ecosystem. Standards, doctrine, and the
ecosystem roadmap live in [autonomous](https://github.com/Lifted-Truck/autonomous)
(`~/Documents/Claude/autonomous/`) — this project executes; that repo governs.
Decision of record: autonomous/DECISIONS.md #11 (two-pool design), #12
(this project's charter).*

*Last verified current: 2026-07-10 (scaffold day — nothing built yet).*

## The two pools

```
per-project LIBRARYs ──sweep──▶ THE STREAM (append-only warehouse)
   (operational, small,           every candidate lesson, dated,
    curated, working-agent         provenance attached. Read by
    retrieval)                     the ANALYST ONLY — never
                                   retrieval context for working
                                   agents.
                                        │
                                   analyst findings
                                   (propose-only)
                                        ▼
                              THE DISTILLED POOL (mart)
                              entered ONLY through promotion
                              gates (see cross-proliferation
                              standard, autonomous README §4c);
                              consumed by curators / down-
                              propagation.
```

**The load-bearing rule:** the stream is never read by working agents. Its
value is longitudinal — recurrence patterns, demote-recur cycles,
cross-project failure signatures that per-sweep convergence detection
structurally misses. Findings enter circulation only through the distilled
pool's gates. (Evidence: selective memory beat comprehensive 39% vs 13% —
autonomous/research/2026-07-10-memory-governance.md.)

## Boundaries (what this project may and may not do)

- **Reads** every project's LIBRARY/INDEX via the sweep (hash-ledgered,
  skip-unchanged — the audit loop's SCAN mechanics).
- **Writes** only its own pools and proposals. Never commits to swept repos
  (writes-stay-home, INTEGRATIONS policy). Distilled-pool writes are
  propose-only until a human (later: the curator) ratifies.
- **Deterministic core**: sweep, ledger, dedup, eviction, staleness checks
  are code. AI judges *promotions* and mines *patterns* — nothing else
  (AI/deterministic boundary).
- Relationship to the existing audit loop
  ([agent-knowledge-loop](https://github.com/Lifted-Truck/agent-knowledge-loop)):
  the audit loop is the vertical promote-up path and STAYS canonical for
  scope-level promotion. Distillery adds the warehouse + analyst layer beside
  it — it consumes the same LIBRARY format and must not fork it.

## Where to start

1. Read [ROADMAP.md](ROADMAP.md) — phases D0–D4 with gates. D1 (stream schema
   + deterministic ingest) is the open front.
2. Read [CLAUDE.md](CLAUDE.md) §Domain for invariants and protected paths.
3. Our intake brief against the standards repo lives at
   `autonomous/integrations/distillery/brief.md` — what we need from kit v2
   and whose ball it is.
4. [project.manifest.json](project.manifest.json) is the spin-up survey's
   answers (provisional — confirm with the human before D2).

## Possible future

The ecosystem roadmap (autonomous/ROADMAP.md, Ecosystem tracks) flags this
project as the candidate **operational lead** of the ecosystem once mature:
the analyst here is the natural seed of the ecosystem-level curator/governor.
That promotion is gated and not yet decided — build the pools first.
