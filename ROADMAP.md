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
4. **Test runner = stdlib `unittest`** (2026-07-10): pytest/ruff are not
   installed on this machine and adding them is a gated dependency decision;
   the ecosystem convention (autonomous `./verify`) is stdlib-only
   `python3 -m unittest`. Tests are written as `unittest.TestCase` (pytest
   runs these unchanged if provisioned later). Revisit if/when the human
   provisions pytest+ruff.
5. **Parser tolerance for `library-entry.1`** (2026-07-10): real LIBRARYs
   write `tier: candidate` (labeled) where the contract grammar shows a bare
   `<tier>`, and use `—` for empty optional fields. The parser accepts both
   the bare and labeled tier form and treats `—`/`-`/empty optional fields
   as absent; anything violating the parsed-form schema quarantines. This
   liberal reading is surfaced to autonomous in the contract-test fixtures
   (their resident can object via the channel).
6. **D1 gate "duplicate detected" pinned** (2026-07-10, critic finding 4):
   the injected duplicate is a same-`(project, hash)` line; "detected" means
   the ingest run summary (deterministic JSON on stdout) reports it as
   `skipped_duplicate` with zero appends. Cross-project duplicates are
   deliberately KEPT (recurrence is D3's job, per this roadmap) — the gate
   does not test those. Byte-identity of the journal alone cannot
   distinguish deduped from dropped; the summary is the observable.
   Schema doc: docs/stream-schema.md (critic-reviewed, blockers folded in:
   file-level provenance fields, fence-aware line detection,
   journal-before-ledger crash ordering, run-summary observability).
7. **Contract-test fixtures FILED** (2026-07-11, exchange `distillery-002`,
   ball: provider, respond-by 2026-07-18): 13 line-level cases + a
   round-trip LIBRARY fixture at
   `autonomous/integrations/distillery/contract-tests/`. Decision-5
   tolerance readings are flagged for objection; two contract ambiguities
   surfaced for a ruling (pipes inside free-text fields; unknown labeled
   segments — our parser and the fixtures avoid both pending the answer).
   Discharges the "owed" item in decision 3. Our parser must pass these
   same fixtures (cross-check at the D1 gate).
8. **Wrapped-entry gap found on first real sweep** (2026-07-11): morphos,
   edgewise, and wont write LIBRARY entries across multiple physical lines;
   the contract is one-entry-per-line, so their 7 entries quarantine
   (visibly, with raw lines + provenance preserved — re-parseable after a
   ruling). Ruling requested in exchange `distillery-002`: strict contract
   (offending projects fix their loops) vs continuation-line grammar in a
   `library-entry.2`. Distillery does NOT extend the parser beyond the
   pinned contract meanwhile.

9. **D2 scope pinned** (2026-07-11, human ruling): staleness is
   deterministic — a lesson is stale if superseded (a later record carries
   `supersedes: <its id>`) or aged past a documented threshold. No execution
   of embedded verification commands (evidence: 0/21 D1-corpus lessons carry
   an executable falsifier; `library-entry.1` has no executable-check field;
   executing swept content is untrusted-code execution). Falsifier-execution
   staleness is deferred until a lesson class with executable checks is
   actually defined (a `library-entry.2` concern, overlaps distillery-002).
   Recurrence queries group by deterministic signature (content-hash /
   normalized text); semantic recurrence stays D3's.
10. **Stream single-writer invariant + flock-before-cron gate** (2026-07-11):
    the daily ingest cron will be the first automated stream writer. Current
    guarantee = documented single-writer invariant (at most one
    stream-mutating process at a time; ingest is run manually, sequentially).
    **Hard gate:** an `fcntl.flock` on `stream/.lock` acquired by D1 append
    MUST land before the daily cron is wired. (This originally also covered
    archive-vs-append; archive is now deferred — decision 11 — so today the
    only mutator is ingest, and the flock requirement travels with the
    cron-wiring task.)
11. **D2 archive/compaction DEFERRED** (2026-07-11, human ruling after two
    critic rounds): D2 ships provenance queries + deterministic staleness
    only. Rationale: at 28 records we are ~180× below the 5000-record
    segment threshold, so archive machinery is speculative infrastructure;
    and the second critic round proved it introduces a **D1-dedup seam** —
    D1's `load_seen` scans only the live journal (`journal.py:17-49`,
    `ingest.py:70`), so once archiving relocates records out of live, the
    next changed-LIBRARY re-ingest re-appends the archived lessons
    (duplicate `(project,hash)` across live+archive, silently dropped by any
    restore-dedup). **When archive is built (a future scale-triggered
    phase), the fix is mandatory and designed-in, not bolted-on:** the dedup
    seen-set must cover live ∪ archive (union-scan, or a durable
    (project,hash) key-index archiving never touches), with a conservation
    gate — archive a fixture, re-ingest a changed library that had archived
    lessons, assert zero re-append. Until then D2 queries read the live
    journal directly; no live/archive union exists, so no seam.
12. **No path string in any record — drop `source`** (2026-07-17, human
    ruling; closes the D1 open question). Records dropped the absolute
    `source` path: sweep returns machine-absolute paths that bake the local
    username + layout into an append-only journal bound for a public remote.
    `project` (registry name) is the portable file identifier — the LIBRARY
    path is `registry-resolve(project)/LIBRARY.md`, re-derivable — and
    `source_hash` pins the file's state, so a stored path is redundant AND
    leaky. Relativizing was rejected: the roster spans multiple roots
    (`~/Documents/Claude/*`, `~/Documents/Tonality`, …), so "repo-relative
    to one root" is ill-defined. Kept `stream-record.1` (no real data ever
    persisted `source`, so a `.2` bump would be ceremony). Guarded by
    `test_no_record_carries_an_absolute_path`. **Provenance intact:**
    `project`+registry = which file, `source_hash` = which state.
    *Cross-project reference:* dispatch hit the identical leak in its FACTS
    collector and resolved it the same way (drop the path, `name` is the id,
    guard test) — dispatch decision 7, traces/2026-07-13-portable-facts.md.
    We adopted the *principle* (writes-stay-home: each repo rules its own),
    and — because we HELD the genesis data — fixed it with a plain edit
    where dispatch had to rewrite committed git history.
13. **Promotion boundary + routing taxonomy ratified** (2026-07-17, human).
    Governs D3's proposal format and D4's gates; sharpens autonomous README
    §4c without relaxing any of its gates.
    - **Hard gates inherited from §4c** (unchanged): qualified at source
      (canonical, or independently found by ≥2 siblings); generalizes beyond
      origin (litmus: statable without naming the origin's code);
      dedup-by-merge preserving concrete evidence; provenance + falsifier
      never dropped; parent = intersection, not union — when in doubt, don't
      promote.
    - **Transfer breadth decides altitude**: top pool = cross-DOMAIN
      transfer; niche-shared lessons (e.g. eigensolver numerics) route to
      the group scope owned by the audit loop. Slots downstream are scarce
      (~100–150 CLAUDE.md instructions; selective beat comprehensive 39% vs
      13% — autonomous/research/2026-07-10-memory-governance.md).
    - **Routing taxonomy — a PROPOSAL VOCABULARY, not delivery machinery.**
      Each D3 proposal entry carries
      `route: pool | group-scope | provider-docs | machine-local |
      reference | merge-as-evidence | undecided` + reasoning. Distillery
      delivers ONLY the pool route (its own D4 gate). Other routes are
      handed to their owners: group-scope → audit loop's next cycle;
      provider-docs → a brief via the integrations channel; machine-local →
      surfaced to the human (their ~/.claude/CLAUDE.md; machine-local
      content must NEVER enter the pool — it is bound for a public remote);
      reference/merge-as-evidence → distillery's own annotations. No
      automated cross-repo delivery, ever (writes-stay-home + reduce).
    - **Default route is `undecided`**, surfaced to the human with the
      tension stated. Asymmetry: misrouting AWAY from the pool is cheap
      (stream keeps everything; re-proposal is free); misrouting INTO it
      spends a scarce slot and curator trust. When torn, don't route — ask.
    - **Recurrence outranks eloquence**: analyst proposes pool entry on
      OBSERVED recurrence (≥2 independent origins). Single-origin lessons
      are proposable only with an explicit `single-origin` flag for human
      sponsorship (ratified alongside this decision).
    - **Falsifier quality is a promotion gate**: at D4, a falsifier must
      name a checkable observation ("if this stops working" fails).
      Judgment is allowed — promotion is the AI-judgment + human-ratification
      zone.
    - **Every non-pool route writes a stream annotation** against the
      record's origin (append-only, our own journal) so later analyst runs
      see prior dispositions instead of re-proposing forever.
    - **Pool health metric is CONSUMPTION, not size** — recorded now,
      deliberately: the pool growing slowly (perhaps 2–3 entries while the
      stream holds hundreds) is the design working, not failing. Future
      pressure to loosen routing to make the pool look productive meets
      this recorded decision, not an open question. Measure: does a curator
      pull an entry down; does it survive its falsifier.
    Current-corpus calibration (2026-07-17): under this boundary, 0 of 21
    stream lessons enter the top pool today — 1 formally qualifies but
    routes to group scope (Curvature#L0001); the strongest candidate
    (Wend#L0001, Goodhart) awaits a second independent occurrence or human
    sponsorship. This slow start is expected and correct.
14. **First human-sponsored promotion candidate designated:
    `synthetic-worlds/HYPERSAW#L0019`** (2026-07-29, human sponsorship in
    session — the decision-13 single-origin path exercised for the first
    time). "Humanised timing is CORRECTED error, not independent jitter":
    canonical at source (human review recorded in-entry), generalizes
    beyond origin (any onset-timing humanisation, MIDI or audio, incl.
    multi-agent performance timing), falsifier passes the quality gate
    (matched-variance listening test with lag-1 autocorrelation as the
    manipulated variable; claim scope explicitly bounded). Audience spans
    multiple scope subtrees (synthetic-worlds group + Tonality lineage +
    audio-plugin projects) → top-pool altitude per decision 13. Ingested
    2026-07-29 with provenance. **Role: the live test article for D4's
    full-path gate** (LIBRARY → stream → analyst proposal → ratified
    promotion → consumed by a different project). Near-term visibility to
    the synthetic-worlds scope is the audit loop's canonical vertical path,
    not an ad-hoc distillery broadcast. Field note: the same sweep
    quarantined 4 of HYPERSAW's 19 entries on exactly the distillery-002
    ambiguities (pipes-in-prose — now observed in the wild — and a new
    annotated-placeholder pattern, `supersedes: — (refines …)`); one
    quarantined entry (L0016, detector-calibration) is itself
    domain-general. Contract friction is now costing real promotion-worthy
    content; evidence appended to the overdue distillery-002 filing.

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
