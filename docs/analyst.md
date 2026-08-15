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
LIBRARY edit yields a new hash → a new record; `FOUNDATIONS#L0005`,
`HYPERSAW#L0003`, `HYPERSAW#L0004` each have 2 today). The quote may match
**any** record sharing the origin; the proposal renders the **latest in
journal order** and records which record id the quote matched.

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
3,059 chars. The corpus fits in one context today; sharding exists so the
design survives 10× growth, not because it is needed now.

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
records (not lessons yet); lessons marked `superseded` by D2's staleness
(proposing a superseded lesson wastes the scarcest resource in the system —
human ratification); and lessons carrying a prior **disposition
annotation** (§1e).

### 1b. Scout pass (model; read-only)
One fresh-context subagent per shard, each holding the **full text** of its
shard's lessons. Output: **candidate origin sets only** — `{origins[],
why_short}` — deliberately *not* claims or falsifiers, because a scout has
seen only its own shard and must not generalize across text it hasn't read.
Cross-shard candidates are reachable because scouts also receive a
**title+origin index of the whole corpus** (~15KB) alongside their full-text
shard: enough to nominate "this looks like FOUNDATIONS#L0005", not enough
to author a claim about it.

### 1c. Re-bundle + deep pass (deterministic bundling; model analysis)
Candidate origin sets are deduplicated and each is re-bundled
deterministically into a slice carrying the **full text of exactly those
origins**. One fresh-context subagent per candidate authors the finding:
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
2. **Provenance guard** — every origin exists; every origin carries a
   `support_quote` satisfying §0's pinned predicate. Fail → reject.
3. **Cross-project rule** — a `recurrence` spanning <2 distinct projects is
   rejected (a lesson repeated within one project is history).
4. **Rename aliasing** — origins are resolved through a pinned alias table
   before the project count (a registry rename re-appends lessons under a
   new name — `tonality-Live` → `Tonality-Live` today — and must not read
   as a cross-project recurrence; stream-schema.md:43 warns of exactly
   this).
5. **Group breadth** (decision 18, human-ruled) — if all origins share one
   group prefix, set `single_group: true` and **force `route: undecided`**.
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
   claims; a merge with conflicting routes forces `undecided`.

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
  falsifier, conflicting-route merge — each asserted rejected/demoted with
  the right reason. Rendering golden-matched. **Also Layer-0**: parse
  `.claude/agents/analyst.md` frontmatter and assert its tool list contains
  no write-capable tool (§3). **These are guarantees.**
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

### The plants (fixture stream extension)
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
- **Write anything** — *mechanism*: a committed `.claude/agents/analyst.md`
  granting `tools: Read, Grep, Glob` — **no Bash** (Bash is write-capable:
  every other "read-only" agent in this repo has it, and the pretool hook
  blocks only destructive patterns, not writes) and no Write. Model pinned
  explicitly, never inherited (doctrine §Model routing). Asserted by a
  Layer-0 frontmatter test and a `git status --porcelain` before/after
  check in Layer-E.
- **Receive the whole stream in one context** — *mechanism*: shards; the
  corpus-wide index is titles+origins only.
- **Invent provenance** — *mechanism*: §0's mandatory pinned quote guard.
- **Decide promotion** — *mechanism*: it emits a `route`; only a human
  ratifies at D4, and §1d.5 forces `undecided` on single-group families.
- **Be used as retrieval for working agents** — ***prose-enforced***, like
  the equivalent boundary in stream-ops.md §1. A CLI and a committed
  markdown file cannot structurally prevent a working agent from reading
  them. Mitigations: proposals quote bounded spans, never full bodies; the
  leak assertion extends to `proposals/`.

## 4. CLI
`bin/analyze [--stream PATH] [--date YYYY-MM-DD] [--out DIR] [--dry-run]
[--findings PATH]` — wall clock at the edge only. A `--findings` file
carries the **stream hash it was produced from**; replay asserts equality
(the stream is append-only and grows daily — replaying yesterday's findings
against today's corpus would silently revalidate against different data).

`confidence` is deliberately **not** a field: its only plausible use is a
threshold, and a model scalar in the validation path is exactly what
§Domain forbids.
