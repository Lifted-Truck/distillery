# Stream operations — D2 design (`stream-ops.1`)

> Read-side operations over the `stream-record.1` journal: deterministic
> staleness annotation + provenance queries. Pure and deterministic — no
> model calls, no wall-clock in cores (a `today` date is injected at the
> edge exactly as D1's `swept` is). Consumes the D1 journal; produces query
> results only, mutating nothing. Scope pinned by ROADMAP decisions 9 & 11.
>
> **Archive/compaction is DEFERRED** (decision 11): speculative at current
> scale, and it introduces a D1-dedup seam (D1's `load_seen` scans only the
> live journal, so relocating records would cause re-append on the next
> changed-LIBRARY ingest). D2 queries therefore read the **live journal
> directly** — there is no live/archive union and no seam. The archive
> design (crash-atomic segments + `recover()` + the mandatory
> live∪archive dedup-conservation fix) lives in this file's git history and
> decision 11, to be revived designed-in when scale demands it.

## 1. Provenance queries (read-only, pure)

All queries are pure functions of the loaded live journal, emitting
deterministic, sorted JSON. Nothing mutates.

**Access boundary (charter §Domain, prose-enforced).** `bin/query` output is
for a **human, curator, or the D3 analyst** — never wired into a working
agent's retrieval context. The stream's whole point is that it is not
per-sweep retrieval. A stdout CLI cannot structurally prevent an agent from
piping it, so this is a caller-discipline boundary, stated here and on
`--help`; when a mechanism is available (a served interface with an
allowlist) it supersedes the prose (doctrine: freeze-by-mechanism, not
prose).

### `lessons --project <name>`
Every `kind:"lesson"` record whose `project == <name>`, in journal order.
Quarantines included only under `--include-quarantine`. Output carries
`origin`, `entry`, `swept`, `source_hash` — full provenance, never a summary.

### `recurrences [--near]`
Groups lesson records by **signature**, returns only groups spanning **≥2
distinct `project` values** (a lesson repeated within one project is history,
not recurrence; per-file ids collide — `L0001` exists in many projects — so
grouping is by signature, never by id). Two deterministic signatures:

- **exact** (default): `hash` — the `sha256(raw)[:16]` already on every
  record. Same line text in two projects.
- **near** (`--near`): a signature over the **parsed `entry.lesson` prose**
  (never re-parsed out of `raw` — a lesson body may legitimately contain
  ` | x:`, which pipe-stripping would amputate). Normalization is pinned,
  because it freezes into golden fixtures:

  ```python
  import unicodedata, re, hashlib
  norm = unicodedata.normalize("NFC", entry["lesson"].casefold())
  norm = re.sub(r"[ \t\n\r\f\v]+", " ", norm).strip()
  near_sig = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]
  ```
  `casefold()` first, then NFC (canonical idempotence), then collapse
  ASCII-whitespace runs, strip, hash. **"Near" = case + whitespace
  insensitive ONLY; punctuation stays significant** (decision 9). Anything
  fuzzier — stripping punctuation, stemming, synonymy — drifts toward
  meaning-matching, which is D3's job; the crisp minimal boundary keeps the
  D2/D3 line clean. Catches case/spacing restatements that exact-hash misses.

**Deterministic grouping only.** Semantic recurrence — demote-recur cycles,
non-textual failure signatures — is the D3 analyst's job (charter). If two
lessons don't share a signature, D2 reports nothing; D3 may still relate
them. D2 answers "the same text recurs"; D3 answers "the same *lesson*
recurs." D2 must not reach for embeddings or model calls.

### `staleness [--age-days N] [--today YYYY-MM-DD]`
Annotates every lesson record `fresh | stale` with a reason:

- `superseded` — some record in the **same project** carries
  `entry.supersedes == this.entry.id` (ids are per-file, so supersession is
  scoped per project). **Chains** resolve transitively: if L0004 supersedes
  L0003 and L0003 supersedes L0002, both L0003 and L0002 are `superseded`
  (each citing its immediate superseder); only the chain head is not.
- `aged` — `entry.added` is more than `N` days before the injected `today`.
- otherwise `fresh`.

Supersession outranks age. **No execution** of falsifiers or any embedded
command (decision 9). `today`/`N` are parameters — the core never reads the
clock.

## 2. CLI surface (edge adapter; wall-clock only here)
`bin/query lessons|recurrences|staleness [...]` — read-only, JSON to stdout.
`--today`/`--age-days` defaults are computed HERE; the cores take them as
arguments. `--help` states the human/curator/analyst access boundary (§1).
No lifecycle/mutation CLI in D2 (archive deferred).

## 3. Verify (D2 gate additions)
`full` adds golden query results over a committed **fixture** stream
(`tests/fixtures/stream/`, independent of the held real genesis data),
strict byte-match for: `lessons --project`, `recurrences` (exact) and
`recurrences --near`, and `staleness` at a pinned `--today`/`--age-days`.
Deterministic by construction; no round-trip (archive deferred).
