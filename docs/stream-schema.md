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

### `kind: "quarantine"` — a malformed entry line

| Field | Type | Meaning |
|---|---|---|
| `line_no` | int | 1-based line number in the source LIBRARY.md. |
| `error` | string | The parse/validation error, human-readable. |

Per the `library-entry.1` validation stance: malformed entries quarantine
**visibly**, never silently drop, never block the sweep. Quarantine records
participate in `(project, hash)` dedup — a malformed line quarantines once,
not on every sweep.

## Entry-line detection (what gets parsed vs ignored vs quarantined)

Detection runs line-by-line with **fenced-code-block tracking**: a line whose
stripped form starts with ``` toggles fence state, and every line inside a
fence is structural regardless of content (real LIBRARYs carry literal
`[Lxxxx]`/`[L0001]` template examples inside fences — ingesting one would be
provenance corruption in an append-only store).

Outside fences, on the stripped line:

- A line matching case-insensitive `^\[l` is an **attempted entry** — it is
  parsed and lands as `lesson` or `quarantine`. Near-misses (`[L12]`,
  `[l0001]`, `[L 0001]`) quarantine with a clear error; they never vanish.
- Everything else (markdown headers, prose, blanks) is **structural**,
  ignored.

### Parser tolerance (ROADMAP decision 5)

- Tier accepted as bare (`| candidate |`, contract grammar) or labeled
  (`| tier: candidate |`, dominant in real LIBRARYs).
- **Optional** fields (`origin`, `supersedes`, `recurred`) valued `—`, `-`,
  or empty are treated as absent. A **required** field valued `—`/`-`/empty
  is a violation and quarantines — normalization never masks a missing
  required field.
- After normalization the parsed object must satisfy the `library-entry.1`
  JSON-Schema (required fields, id pattern `^L\d{4}$`, tier enum, date
  shape, non-empty tags/lesson/evidence/falsifier) — anything else
  quarantines.

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
