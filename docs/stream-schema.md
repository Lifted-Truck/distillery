# Stream journal schema — `stream-record.1`

> The wire format of the warehouse. After the D1 gate passes this format is
> a **protected path** (CLAUDE.md §Domain): schema changes require a ROADMAP
> decision and a version bump (`stream-record.2`), never silent drift.
> Input contract: `library-entry.1` (autonomous `kit/contracts/library-entry.md`,
> pinned per ROADMAP decision 3). Critic-reviewed 2026-07-10
> (APPROVE-WITH-CHANGES; all blockers folded in — see traces/).

## Files

| File | Role |
|---|---|
| `stream/stream.jsonl` | The append-only journal. One JSON object per line. |
| `stream/ledger.json` | Hash ledger (per-project LIBRARY.md content hash, sweep-primitive semantics). Owned by distillery; consumed by nobody else. |

Both are committed to git (ROADMAP answered: jsonl-in-git). The journal is
**append-only**: supersede by appending, never edit or delete a line. (Sole
exception: crash-artifact truncation, §Durability below.)

## Serialization (byte-exact, replay-critical)

Every record is written as:

```python
json.dumps(rec, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
```

written through a handle opened `open(path, "a", encoding="utf-8", newline="\n")`
(no locale dependence, no platform newline translation). UTF-8, no BOM, LF
endings. This exact writer is the *only* writer; golden replays pin `--date`
and assert byte identity.

## Record kinds

### Common fields (every record)

| Field | Type | Meaning |
|---|---|---|
| `v` | `"stream-record.1"` | Schema version stamp (INTEGRATIONS rule 4). |
| `kind` | `"lesson"` \| `"quarantine"` | Record class. |
| `swept` | `YYYY-MM-DD` | Ingest date. **Injected by the CLI adapter** (`--date`, defaulting to today at the edge); the deterministic core never reads the wall clock. |
| `project` | string | Registry name (e.g. `synthetic-worlds/Wend`), as resolved by the sweep primitive. Registry name IS project identity: a directory rename is a new project and its lessons re-append under the new name — accepted accumulation, documented so the D3 analyst does not read a rename as a cross-project recurrence. This is the **portable** file identifier — the LIBRARY path is `registry-resolve(project)/LIBRARY.md`, re-derivable from `project` + the registry, so no path string is stored (see ROADMAP decision 12). |
| `source_hash` | 16-hex | `sha256(file_bytes)[:16]` of the source LIBRARY.md **as read by this ingest** — pins which state of the file produced this record. Carries no path (no username/layout leak). |
| `hash` | 16-hex | `sha256(raw.encode("utf-8"))[:16]` — content hash of the source line. |
| `raw` | string | The source LIBRARY.md line after Python `str.strip()` (Unicode-whitespace-aware — a trailing NBSP and a trailing space normalize identically; provenance is verbatim *modulo edge whitespace*). |

### `kind: "lesson"` — a successfully parsed entry

| Field | Type | Meaning |
|---|---|---|
| `origin` | `"<project>#Lxxxx"` | Charter-required provenance pointer. `project` is the registry name; `Lxxxx` the entry id. |
| `entry` | object | The parsed form per `library-entry.1` (id, title, tier, added, tags, lesson, evidence, falsifier, and optional origin/supersedes/recurred). The lesson's own `origin` field (promotion back-links) is distinct from the record's `origin`. |
| `entry_contract` | `"library-entry.1"` | Which grammar parsed `entry` — survives future `library-entry.2` migrations. |

### `kind: "disposition"` — a ratified routing decision (`stream-record.2`)

Added by ROADMAP decision 18 for D3. Records that a human ratified a
routing decision about a finding, so later analyst runs see prior
dispositions instead of re-proposing forever (decision 13). Appended after
ratification; never an edit.

**Version semantics**: `v` is **per-record**, not global. Existing
`lesson`/`quarantine` records keep `v: "stream-record.1"` and are never
rewritten (append-only); only `disposition` records carry
`v: "stream-record.2"`. A mixed-version journal is therefore normal and
expected — readers dispatch on `kind`, and `v` records which contract
shaped that record.

Common fields apply **selectively** — most describe a source LIBRARY line,
which a disposition has none of:

| Field | Applies | Meaning |
|---|---|---|
| `v` | yes | `"stream-record.2"`. |
| `kind` | yes | `"disposition"`. |
| `swept` | yes | Ratification date, injected at the CLI edge. |
| `project` | **no** | A disposition spans origins, often across projects. |
| `source_hash` | **no** | No source file. |
| `raw` | **no** | No source line. |
| `hash` | yes | `sha256` of the canonical JSON of `{origins, route, proposal}` — the dedup identity, so re-ratifying the same disposition is a no-op. |
| `origins` | yes | The finding's origin list, sorted. |
| `route` | yes | The ratified route (decision 13 enum). |
| `proposal` | yes | The proposal file that carried the finding. |
| `note` | optional | The human's reasoning. |

**`load_seen` compatibility is required**: `journal.load_seen`
(`journal.py:41`) keys on `(project, hash)` and warns on any record missing
either. A disposition has no `project`, so the seen-key derivation must be
made kind-aware **before** the first disposition is appended, or every
future ingest run prints a spurious warning per disposition. Ingest's
`(project, hash)` dedup for lessons/quarantines is unchanged.

**Reproducibility consequence, stated plainly**: once dispositions exist,
the journal is **no longer reproducible from the LIBRARYs alone** — a
disposition is human ratification, not swept content. This retires the
"regenerate from empty" escape hatch that decision 16 used for the
`library-entry.2` upgrade. Any future contract upgrade must migrate
forward (or re-derive lessons while preserving dispositions), not
regenerate. Recorded here because it is the kind of property that is
invisible until the moment it is needed.

### `kind: "quarantine"` — a malformed entry line

| Field | Type | Meaning |
|---|---|---|
| `line_no` | int | 1-based line number in the source LIBRARY.md. |
| `error` | string | The parse/validation error, human-readable. |

Per the `library-entry.1` validation stance: malformed entries quarantine
**visibly**, never silently drop, never block the sweep. Quarantine records
participate in `(project, hash)` dedup — a malformed line quarantines once,
not on every sweep.

## Entry detection & parsing — `library-entry.2` (ROADMAP decision 15)

> Upgraded from `library-entry.1` per the provider ruling in
> `autonomous/integrations/distillery/response-002.md` ("the parser's job is
> to lose nothing; the promotion gate's job is to judge"). Records carry
> `entry_contract: "library-entry.2"` from the upgrade forward; existing
> `.1` records are history, never rewritten.

**Entry span (multi-line entries are valid).** A stripped line matching
case-insensitive `^\[l` outside a fence **opens an entry span** when the
*preceding* physical line is blank, structural, or start-of-file, **or when
the marker line itself contains a `|`** (a real single-line entry always
carries pipe-delimited fields — attest writes back-to-back entries with no
blank separators — while a `[Lxxxx]` cross-reference at the start of a
wrapped prose line, morphos L0012's "Related: [L0009] … / [L0010] …",
carries none and must NOT open a phantom span). Corpus-verified over all
registry LIBRARYs on 2026-08-10. The span
runs until the next marker, a **terminator**, or EOF. Terminators (all
end the span; nothing folds past them until the next marker): fence lines
(``` — fenced regions are never ingested; an unbalanced fence increments an
`unclosed_fence` counter in the run summary rather than silently swallowing
the file), markdown headings (`^#`), horizontal rules (`^-{3,}$`,
`^\*{3,}$`, `^_{3,}$`), and HTML anchor lines (`^<a\b`, wont's house
style). Blank lines inside a span are skipped, NOT terminators (wont's
entries contain interior blanks). Non-structural span lines fold with
single spaces into the entry's `raw` — the whole entry is the provenance
unit, and the folded raw is what is hashed. (Known, accepted loss: a code
span hard-wrapped across lines gains an interior space.) Content after the
final entry folds into it unless separated by a heading or rule — which now
genuinely terminates (pinned by a negative contract fixture). A heading
line that itself begins with an entry id (`^#+\s*\[?L\d{4}`) quarantines
visibly — 20 real heading-style entries across 8 projects are otherwise
invisible; the gap is filed with the provider (distillery-003), not
silently cemented.

**Segment parsing over the folded raw** (split on `|`; **byte-exact
reconstruction rule**: every field's value is the `"|".join(...)` of its
raw segments, so joining restores the *exact* splitting pipe — `|v|³` stays
`|v|³`, never ` | v | ³`):
- Header: `[Lxxxx] <title>`. Near-miss ids (`[L12]`, `[l0001]`) quarantine
  with a clear error; they never vanish. A **duplicate id within a file
  quarantines both** (contract still-quarantine rule 1) — this is also what
  makes any residual false-marker class visible instead of silent.
- **Segment 1 only**, if it exactly matches the tier enum → `tier`
  (canonical contract rule; the ruling-letter's "enum match anywhere" is a
  documented discrepancy filed back to the provider — we implement the
  contract file, `kit/contracts/library-entry.md`, which consumers validate
  against).
- A segment matching `^\s*(tier|added|tags|origin|lesson|evidence|falsifier|supersedes|recurred)\s*:`
  opens that field. A **repeat** of an already-seen known label
  continuation-joins into the existing value (with its label text and pipe
  restored) — never last-wins (morphos L0007 carries two `evidence:` and
  two `falsifier:` segments; both survive). The unruled repeat case is
  filed with the provider.
- Any other **labeled** segment (`^\s*[\w-]+\s*:`, unknown word —
  hyphenated labels included) is preserved under the entry's `extra` map
  (`additionalProperties: string`; repeats join with a restored pipe). An
  `extra` segment becomes the open field for continuation purposes
  (locality preserves byte-exact reconstruction).
- Any other **unlabeled** segment continuation-joins onto the currently
  open field with the splitting `|` restored. Before any field is open it
  rejoins the title; with no open field available (e.g. directly after a
  bare tier) it quarantines as an unattached segment (never in corpus;
  visible if it ever occurs).

**Placeholders.** On an **optional** field (`origin`, `supersedes`,
`recurred`), a value matching `^[—–-]\s*(.*)$` means absent; a non-empty
remainder is preserved as `<field>_note` (annotations are graph edges, not
noise). On a **required** field a placeholder still quarantines —
`falsifier: —` is a missing falsifier.

**What still quarantines** is the contract's exhaustive list copied
verbatim from `kit/contracts/library-entry.md` (duplicate id in a file;
missing/placeholder required fields; id/tier/date shape violations; an
`origin`/`supersedes` value that is neither a valid `L\d{4}` reference nor
a placeholder) — negative fixtures pin each so the forgiveness cannot
creep. The gate is not weakened.

**Seen-key: unchanged, `(project, hash)`.** The quarantine→lesson
transition problem is moot for the genesis fill: the journal has never been
committed or consumed, so it is **regenerated from empty under
`library-entry.2`** (ROADMAP decision 16) — one contract version in the
journal, no dangling resolved quarantines, no invariant amendment. The
seam returns for any post-publication contract upgrade; options for that
future decision (kind-in-key, or supersession links on quarantine records)
are recorded in decision 16, deliberately not built now.

## Dedup / idempotency semantics

- **Seen-key = `(project, hash)`**, both record kinds. A record is appended
  iff its key does not already appear in the journal. The seen-set is
  derived by scanning the journal (full scan per run — acceptable at
  warehouse scale; segmentation is D2's compaction job).
- 16-hex = 64-bit hashes: birthday bound ≈ 2³² records, orders of magnitude
  beyond warehouse scale. Identical raw lines within one project
  intentionally collapse to one record.
- Re-sweeping an unchanged LIBRARY is skipped upstream by the ledger; a
  changed LIBRARY is re-parsed in full, and only unseen lines append.
- An in-place edit to an entry (e.g. a `recurred:` annotation) yields a new
  hash → a new record. History accumulates; the latest record for a given
  record-`origin` is the current view. Nothing is rewritten.
- **Cross-project duplicates are NOT deduped** — the same lesson text under
  two projects is two records. Recurrence detection is the analyst's job
  (D3), not ingest's.
- Deleted LIBRARY lines produce nothing; the stream keeps history.

## Observability: the run summary (what "detected" means)

Every ingest run emits a deterministic JSON summary on stdout:
per-project and total counts of `appended`, `skipped_duplicate`,
`quarantined`, plus `projects_swept` / `projects_changed` / `projects_skipped_unchanged`.
Byte-identical journals cannot distinguish "correctly deduped" from
"silently dropped" — the summary can, and the D1 gate asserts on it
(ROADMAP decision 6): an injected same-`(project, hash)` duplicate must
show `skipped_duplicate ≥ 1` and `appended = 0` for that line.

## Durability & crash recovery (write ordering)

- **Journal-before-ledger, always.** Order per run: parse → append records
  → flush + `os.fsync` the journal → only then write `ledger.json`. The
  ledger may only ever *lag* the journal; a stale ledger self-heals on the
  next run (re-parse + dedup = no double records). The reverse order could
  silently lose lessons (ledger says "unchanged," journal never got them)
  and is forbidden.
- **Partial trailing line** (crash mid-append, final line lacks `\n` or is
  invalid JSON without a newline): it is a crash artifact, not a record —
  it never durably existed. The writer truncates it before appending
  (the sole permitted mutation of the journal) and reports the repair
  visibly in the run summary. Readers never crash on it: any line that
  fails JSON parse is skipped with a visible warning.

## Ordering (determinism)

Within one ingest run, appends are ordered by: registry resolution order
(the sweep primitive's stable order), then source line number. Two runs
over identical inputs produce byte-identical journals.

## Invariant restated (charter §Domain)

Every record carries date (`swept`), origin (`origin` for lessons;
`project`+`line_no` for quarantines), file provenance (`project` identifies
the file via the registry; `source_hash` pins its state), content `hash`,
and the falsifier whenever one parses. A record without provenance is a bug.
**No absolute path — ever — in any record** (ROADMAP decision 12): sweep
returns machine-absolute paths that would bake the local username + layout
into an append-only file bound for a public remote; `project` is the
portable identifier and `source_hash` the state pin, so the path string is
redundant and dropped. No model calls anywhere in this path.
