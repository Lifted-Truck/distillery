# The analyst — D3 design (`analyst.1`)

> The first phase where AI enters the pipeline. It is **propose-only**: the
> analyst reads the stream and writes nothing but a dated proposal file that
> a human ratifies. Scope pinned by ROADMAP decisions 9 (D2/D3 boundary),
> 13 (routing taxonomy + promotion boundary), 18 (this design's rulings).
>
> Critic-reviewed 2026-08-12 (REJECT → this revision). The rejected draft
> partitioned by tag; executed over the committed stream that reached
> **43 of 138 lessons and found none of the three known targets**. It also
> carried a fabricated justification. Both are recorded here rather than
> quietly dropped: the corpus measurements below are computed, and any
> claim about the corpus in this document is either computed or labelled a
> hypothesis (CLAUDE.md §Provenance).

## 0. The AI/deterministic boundary, made mechanical

Doctrine: *AI may interpret language, propose, and judge; AI may NOT be in
the path of scheduling, metrics, validation, or signal processing.* D1 and
D2 held that line by having no model calls at all. D3 cannot — semantic
recurrence is the point — so the boundary becomes a **mechanism**:

**The same edge/core split that has held since D1.** `--date` injects the
wall clock at the CLI edge so the ingest core stays pure; the analyst
injects **model findings** at the edge so the validation/render core stays
pure. The core is a pure function of `(stream_records, findings) →
proposal`, testable in CI with recorded findings and **zero model calls**.

**The provenance guard.** Every finding must carry, per cited origin, a
`support_quote` — a verbatim span from that origin's own lesson text.
Quoting is **mandatory, not opt-in**: a finding that cites origins without
quotes is rejected, which both blocks the cheapest fabrication (real
origins, invented relationship) and proves the agent actually read the
text it is generalizing from.

*Pinned match predicate* (frozen, like `near_signature` in stream-ops.md —
whatever ships becomes the contract):
```python
def _norm(s):
    s = unicodedata.normalize("NFC", s.casefold())
    return re.sub(r"[ \t\n\r\f\v]+", " ", s).strip()
# support_quote q supports origin o iff:
#   len(_norm(q)) >= 40 and _norm(q) in _norm(record.entry["lesson"])
```
*Origin→record resolution*: an origin may map to **N records** (an in-place
LIBRARY edit yields a new hash → a new record; `synthetic-worlds/FOUNDATIONS#L0005`,
`synthetic-worlds/HYPERSAW#L0003`, `synthetic-worlds/HYPERSAW#L0004` each
have exactly 2 today). **One record is authoritative throughout: the latest
in journal order.** It is what the deep pass is given, what the quote is
matched against, and what the proposal renders — never a mix. (Today all
three duplicate-origin pairs have byte-identical `lesson` text, differing
only in `title`/`tier`/`evidence`/`recurred`, which is exactly why a
mixing bug here would surface late and confusingly.)

**What this guard does NOT catch** (stated because doctrine forbids
conflating guaranteed with measured): real origins + an invented
*relationship* between them; a claim that generalizes far past what its
quotes support; a real quote that doesn't actually support the claim. Those
are judgment, and judgment is the human's at D4. The guard is a floor on
fabrication, not a ceiling on error. Rejections are recorded in the
proposal's audit block, so a systematically-fabricating analyst is
*observable*, not merely blocked.

## 1. Pipeline — two passes, full coverage by construction

```
stream.jsonl ──shard──▶ full-text slices ──scout──▶ candidate origin sets
  (deterministic)                          (model)         │
                                                     re-bundle (deterministic)
                                                           ▼
proposal ◀──render──── findings ◀──deep──── full-text candidate slices
     (deterministic)      (validate)   (model)
```

Measured sizing (computed 2026-08-12 over the committed stream): 138
lessons, **123,017 chars of lesson text ≈ 31K tokens**, max single lesson
3,059 chars.

`SHARD_CHAR_BUDGET = 150_000` — pinned **above** the current corpus so the
committed stream yields **exactly one shard**. This is deliberate: with one
shard every candidate is intra-shard and nomination never depends on the
title index (below). A Layer-0 assertion pins `shard_count == 1` over the
committed stream, so "the corpus outgrew one shard" is a **visible event
that triggers redesign of the cross-shard join**, not a silent degradation
into title-only nomination. The audit block records budget and shard count.

*Honest scaling note*: sharding + a broadcast corpus-wide index is O(N²/B)
in index cost and does **not** survive 10× growth (at 10× the broadcast
index would exceed the corpus itself). Sharding is here for structure and
for the visible-event property, not as a scaling story; what replaces the
index above one shard is an open design question, deliberately unanswered
until the assertion fires.

### 1a. Shard (deterministic, no model calls)
Lessons in **journal order**, split on a pinned character budget
(`SHARD_CHAR_BUDGET`, a named constant). Every lesson lands in exactly one
shard: **coverage is 138/138 by construction**, not by predicate. No tag
logic — human tag vocabularies are project-local by design (the manifest
has each project declare its own), and the corpus proves they do not align
across projects: the six "verify the verifier" records share **zero** tags
pairwise across their four projects (`plugin-platform,
extraction-discipline` / `oracle-calibration, foundations-seams` /
`harness-tooling, oracle-discipline` / `testing, calibration, epistemics,
…`). Tag equality is the wrong join key for semantic recurrence.

**Excluded from analysis** (counted in the coverage block): quarantine
records (not lessons yet), and lessons marked `superseded` by D2's
staleness (proposing a superseded lesson wastes the scarcest resource in
the system — human ratification; 0 lessons are superseded today, so this
is currently a no-op).

**Dispositioned lessons are NOT excluded.** Decision 13 says later runs
must *see* prior dispositions — not that the lessons vanish. Excluding them
would make a lesson permanently invisible the moment it is routed once,
even as new sibling evidence arrives later, and dispositions live in an
append-only journal where that mistake is unrecallable. Instead: the
disposition travels into the deep pass as context, and rule 1d.9 rejects a
finding only if its origin set is a **subset** of an already-dispositioned
finding's origin set. A finding that adds a genuinely new origin is a new
finding.

### 1b. Scout pass (model)
One fresh-context subagent per shard. **All slice content is passed inline
in the prompt; the agent is granted no file-reading tools** (§3) — a
`Read`/`Grep`/`Glob` grant would let it open `stream/stream.jsonl` directly
and defeat the confinement it is supposed to enforce. Output: **candidate
origin sets only** — `{origins[], why_short}` — deliberately *not* claims
or falsifiers, because a scout must not generalize across text it hasn't
read.

At today's pinned budget there is exactly one shard, so nomination is
always from full text. The **title+origin index of the whole corpus**
(15,850 chars, computed) is passed only when `shard_count > 1`, and is
explicitly a degraded mode: it is enough to nominate "this resembles
`synthetic-worlds/FOUNDATIONS#L0005`", never enough to author a claim.
Origins are always written with their full registry name including group
prefix, since rule 1d.5 keys on exactly that prefix.

### 1c. Re-bundle + deep pass (deterministic bundling; model analysis)
Candidate origin sets are deduplicated and each is re-bundled
deterministically into a slice carrying the **full text of exactly those
origins** — for an origin with N records, the **latest in journal order**
only, the same record the proposal renders and the same one quotes are
matched against (bundling one record while validating against another would
let a quote validated on an older text accompany a claim rendered from a
newer one). One fresh-context subagent per candidate authors the finding:
`kind`, `claim`, per-origin `support_quote`, `falsifier`, proposed `route`,
`single_origin` flag. ≤2K tokens per finding.

Finding kinds:
- `recurrence` — the same transferable lesson in ≥2 projects, texts
  differing (textual matches are D2's job).
- `contradiction` — two lessons whose guidance cannot both be followed;
  the analyst must state the incompatibility, not merely note tension.
- `single-origin` — proposed on quality alone; carries decision 13's
  `single-origin` flag and requires human sponsorship. **Capped** at
  `MAX_SINGLE_ORIGIN` per run (recurrence outranks eloquence — an
  uncapped run can flood the human gate with eloquence).

### 1d. Validate (deterministic, no model calls)
In order; every rejection recorded with its reason:
1. **Schema** — required fields; `kind` enum; `route` ∈ {`pool`,
   `group-scope`, `provider-docs`, `machine-local`, `reference`,
   `merge-as-evidence`, `undecided`} (decision 13, verbatim); ≥1 origin.
2. **Provenance guard**, two distinct failures with different remedies —
   conflating them makes the guard a false-negative amplifier on exactly
   the highest-breadth findings (a 6-origin finding would be ~6× more
   likely to die on one mistyped em-dash than a 2-origin one):
   - *origin does not exist* → **reject the finding** (fabrication).
   - *origin exists but its `support_quote` fails the predicate* → **drop
     that origin**, record it, and re-apply rules 3–6; reject only if
     breadth then collapses. A mistyped quote is a transcription error,
     not fabricated provenance.
3. **Cross-project rule** — a `recurrence` spanning <2 distinct projects is
   rejected (a lesson repeated within one project is history).
4. **Rename aliasing** — origins are resolved through a pinned alias table
   before the project count (a registry rename re-appends lessons under a
   new name — `tonality-Live` → `Tonality-Live` today — and must not read
   as a cross-project recurrence; stream-schema.md:43 warns of exactly
   this).
5. **Group breadth** (decision 18, human-ruled). Group is defined
   precisely, because the naive reading inverts the rule: 34 of 138
   lessons are in **ungrouped** top-level projects (morphos 13, attest 10,
   Tonality-Live 7, Portolan 2, harness-grader 1, juce-rag 1), and treating
   "no prefix" as a shared empty-string group would force `undecided` on
   findings spanning two *independent* top-level projects — the
   highest-breadth class in the corpus, exactly what decision 13 exists to
   promote.
   ```python
   group = origin.split("/")[0] if "/" in origin else None
   single_group = all(g is not None for g in groups) and len(set(groups)) == 1
   ```
   When `single_group`, **force `route: undecided`**.
   The analyst may argue for pool altitude in its reasoning; it may not
   claim it unopposed. (104 of 138 lessons are `synthetic-worlds/*`; every
   known candidate is siblings-only, so this is the common case, not the
   corner.)
6. **D2 overlap** — demote to a D2 pointer only if the origin set adds
   **nothing beyond a single D2 signature group**; a D2-visible pair inside
   a larger semantic family is kept and its D2-visible subset annotated.
7. **Falsifier** — non-empty and not a restatement of the claim. (Quality
   judgment is the human's at D4; this is the empty/degenerate floor.)
8. **Dedup** — findings with identical origin sets merge, preserving both
   claims (claims ordered by the merged finding's lowest origin in journal
   order); a merge with conflicting routes forces `undecided`.
9. **Prior disposition** — reject if the origin set is a **subset** of an
   already-dispositioned finding's origin set (§1a). A finding adding a new
   origin survives.
10. **Size** — each finding's rendered length must be ≤ `FINDING_CHAR_CAP`
    (a char proxy for the ROADMAP's "≤2K-token findings" — a tokenizer
    would be a dependency; the acceptance criterion gets an oracle either
    way).

`MAX_SINGLE_ORIGIN` selects survivors in **journal order of each finding's
lowest origin**; those cut are recorded as rejections with reason
`single_origin_cap` (an unpinned cap would break §1f's byte-determinism).

**Default route is `undecided`** (decision 13): the analyst routes only
when confident, and anything contested surfaces with the tension stated.

### 1e. Disposition annotations (append-only, own journal)
Decision 13 requires non-pool routes to annotate the stream so later runs
see prior dispositions instead of re-proposing forever. Annotations are a
**new record kind** (`kind: "disposition"`, `stream-record.2`) appended to
our own journal after human ratification — never edits. Because this
touches a protected path it is ratified as ROADMAP decision 18, not
improvised. §1a filters annotated lessons out of analysis.

### 1f. Render (deterministic)
`proposals/<date>.proposal.md`: front-matter (date, stream hash, record
count, analyst version, **model actually used** — never a configured
value, or the audit lies); one section per surviving finding (claim,
origins with their bounded `support_quote` spans — *not* full lesson
bodies), falsifier, route, flags); then an **audit block**: shards,
candidates nominated, findings received, rejections by reason, coverage
(lessons analyzed / total / excluded-with-reason). Byte-deterministic
given `(records, findings)`.

**The proposal is not a pool.** `proposals/` is staging; nothing enters the
distilled pool without human ratification at D4.

## 2. Oracles — guaranteed vs measured (never conflated)

- **Layer-0 (deterministic, CI-blocking, zero model calls).** The core is a
  pure function; tests feed recorded-findings fixtures, including
  adversarial ones — fabricated origin, missing/short/misquoted
  `support_quote`, single-project "recurrence", rename-aliased pair,
  single-group family (must force `undecided`), D2-visible pair, empty
  falsifier, conflicting-route merge, dispositioned-subset, ungrouped-pair
  (must NOT be single_group), quote-fails-but-origin-exists (drop origin,
  don't reject) — each asserted rejected/demoted/degraded with the right
  reason. Rendering golden-matched. Plus `shard_count == 1` over the
  committed stream (§1a's visible-event assertion). **Also Layer-0**: parse
  **every** agent file the analyst uses (`.claude/agents/analyst-scout.md`
  and `analyst-deep.md` — two distinct model roles, so both are named and
  both are tested) and assert the `tools:` key **exists**, its parsed set
  **equals** a pinned allowlist, and `model:` is present. Equality, not a
  blocklist: a blocklist misses the next write-capable tool nobody thought
  of, and — worse — an *omitted* `tools:` key means the agent inherits
  everything while a naive parse yields an empty list that a blocklist
  blesses. The strongest violation must not be the one the test passes.
  **These are guarantees.**
- **Layer-E (behavioral, measured, non-blocking).** A real run over the
  fixture stream must surface the planted recurrence and contradiction and
  **not** the decoy. Model output is nondeterministic → measured, never
  golden-matched, never CI-gating. Each run **appends a result line** to a
  tracked `evals/analyst-runs.tsv` (date, model id, plants-found,
  false-positives, findings, rejections, git hash) so a capability
  regression is *visible* rather than silently green. **This is evidence,
  not a guarantee.**

The ROADMAP D3 gate is satisfied by a **dated, recorded Layer-E run** for
detection plus Layer-0 for the zero-writes and provenance properties
(decision 18 — recorded so this is a stated gate design, not a quiet
weakening).

### The plants (a SEPARATE fixture stream)
Plants live in `tests/fixtures/stream-d3/stream.jsonl`, **not** in the D2
fixture (13 records today, not 14). The D2 fixture is read by four
committed goldens — `q-staleness.json` annotates *every* lesson, so any
addition breaks it, and regenerating goldens means editing the gates
`./verify` runs, a CLAUDE.md human gate. A separate D3 fixture avoids
touching a passing gate to make a new feature convenient, which is the
shape of a weakened gate even when the intent is benign.

- **Semantic recurrence**, invisible to D2 *and* to tag-joining: two
  lessons in different projects stating the same transferable lesson in
  unrelated vocabulary, sharing **no tag** — mirroring the real corpus,
  where the targets share none. A Layer-0 test asserts D2's exact and near
  signatures both return empty on the pair, so the plant cannot silently
  degrade into something D2 would catch.
- **Contradiction**: two lessons whose guidance is directly incompatible.
- **Decoy**: a pair with superficially similar vocabulary that is *not* the
  same lesson. Layer-E records precision, not just recall; a run that
  reports the decoy is a worse run, and the metric says so.
- The finding's origin set must be **exactly** the planted pair — not
  merely contain it (a 14-record fixture is small enough that a superset
  guess would otherwise score as success).

## 3. What the analyst must NOT do — mechanism vs prose, labelled
- **Write anything** — *mechanism*: committed
  `.claude/agents/analyst-scout.md` and `analyst-deep.md` granting the
  **narrowest possible tool set** — no Write, and **no Bash** (Bash is
  write-capable: every other "read-only" agent in this repo has it, and the
  pretool hook blocks only destructive patterns, not writes). Model pinned
  explicitly, never inherited (doctrine §Model routing). Asserted by the
  Layer-0 allowlist-equality test, plus a `git status --porcelain`
  before/after check in Layer-E **scoped to exclude `proposals/` and
  `evals/`** (a successful run writes both by design; an unscoped check
  always fails, which invites weakening it rather than scoping it).
- **Receive the whole stream in one context** — *mechanism*: slice content
  is passed **inline in the prompt** and the agents hold no file-reading
  tools. (Granting `Read`/`Grep`/`Glob` would let an agent open
  `stream/stream.jsonl` itself, making this prose wearing a mechanism's
  label — the error class this section exists to prevent.)
- **Invent provenance** — *mechanism*: §0's mandatory pinned quote guard.
- **Decide promotion** — *mechanism*: it emits a `route`; only a human
  ratifies at D4, and §1d.5 forces `undecided` on single-group families.
- **Be used as retrieval for working agents** — ***prose-enforced***, like
  the equivalent boundary in stream-ops.md §1. A CLI and a committed
  markdown file cannot structurally prevent a working agent from reading
  them. Mitigations: proposals quote bounded spans, never full bodies; the
  leak assertion extends to `proposals/`.

## 4. CLI
`bin/analyze [--stream PATH] [--date YYYY-MM-DD] [--out DIR]
[--findings PATH]` — wall clock at the edge only. (No `--dry-run`:
`--out <tmpdir>` already validates without committing, so the flag would
not displace its own complexity.)

A `--findings` file carries the **stream hash it was produced from** *and
the model id that produced it*; replay asserts the hash matches and copies
the model id into the proposal. The stream is append-only and grows daily,
so replaying yesterday's findings against today's corpus would silently
revalidate against different data — and §1f's "model actually used" is only
non-fiction if the id travels with the findings rather than being read back
from config.

`confidence` is deliberately **not** a field: its only plausible use is a
threshold, and a model scalar in the validation path is exactly what
§Domain forbids.
