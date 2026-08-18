# library-entry-v3-block-form-absorbs — upgrade parser from library-entry.2 to .3

- **Queue item:** unqueued: implementer brief (upgrade `distillery/entry_parser.py`
  to `library-entry.3`, dispatched directly, no ROADMAP id cited in the brief)
- **Why:** `library-entry.3` (autonomous `kit/contracts/library-entry.md`)
  admits a READ-only heading-delimited "block form" (Catena/Limen bracketed,
  Antiphon bare+em-dash, resume-workshop bare+title-on-next-line) so ~20
  complete entries across 8+ projects stop being invisible, and fixes a named
  defect where the v3 `absorbs` amendment was added to prose/schema/
  quarantine-list but never to the label-opening rule, so `absorbs:` fell
  through to `extra` and the graph edge (fold-in, not invalidation — distinct
  from `supersedes`) stayed unwalkable.
- **Evidence consulted:** the contract in full; `distillery/entry_parser.py`
  (v2); `tests/unit/test_entry_parser.py` (v2); `distillery/ingest.py`;
  `tests/unit/test_ingest.py`; real corpus reads of Catena, Antiphon, Limen,
  spectrogen, HYPERSAW (`~/Documents/Claude/synthetic-worlds/`), morphos and
  attest (`~/Documents/Claude/`) LIBRARY.md files; v2-vs-v3 baseline diff run
  via `git show HEAD:distillery/entry_parser.py` against the same corpus.
- **What changed:**
  - `_BLOCK_MARKER_RE` (`^#{2,6}\s+\[?L\d{4}\]?`) recognized as the ONE
    exception to "headings are structural terminators" — it closes any open
    span and opens a new block span. A block span accumulates raw lines
    (for the stored, audit `raw`) and separately resolves (id, title,
    field_lines); the title is either on the heading line (bracketed or
    em-dash form) or deferred to the first following non-empty line
    (resume-workshop form), which is then consumed as title, not field
    content.
  - `_block_field_segments` normalizes the three field delimiters
    (`| label: value`, `**label:** value`, `- **label:** value`) plus
    middot-separated inline bold fields into plain `"label: value"` text;
    `_block_to_parse_raw` rewrites the whole block into a synthetic
    line-form raw and hands it to the UNCHANGED `_parse_entry` — block form
    inherits every validation rule (required fields, tier enum, placeholder
    handling, repeated-label join, literal-pipe round-trip) with zero
    duplicated logic. The v2 "heading-style entry marker" quarantine error
    is retired (those entries now parse or quarantine on their own merits).
  - `absorbs` added to `_KNOWN_LABELS` (the fix for the named defect) and to
    `_OPTIONAL_REFS`. `_parse_absorbs` handles the real corpus shape: a
    comma-separated leading run of `L\d{4}` refs followed by a free-text
    remainder that may itself contain commas (HYPERSAW's
    `L0011, L0021, L0034 — shell-path, superset and layer blindness
    respectively; consolidated 2026-08-11`) — a plain comma-split would
    break on the note's internal commas, so only the clean leading run is
    comma-split; a remainder starting with a stray comma is a genuinely
    invalid list element and quarantines (still-quarantine rule 4).
  - `entry_form: "block"` recorded on block-parsed entries per the v3 JSON
    Schema (omitted on line-form entries — default/canonical, adding no
    footprint there).
  - `distillery/ingest.py`: `ENTRY_CONTRACT_VERSION` bumped to
    `"library-entry.3"`.
  - `tests/unit/test_entry_parser.py`: two v2 tests updated (the "heading-style"
    error text is retired, replaced by ordinary field-validation quarantines,
    per the brief's explicit note); new coverage added: all three block
    heading shapes + their field-equivalence, title-on-next-line, all three
    delimiters + middot, missing-falsifier-still-quarantines, non-entry
    heading still terminates with no phantom record, and the full `absorbs`
    surface (list, note, em-dash note with internal commas, invalid ref,
    invalid list element, placeholder-absent, not-landing-in-extra). 49
    tests in this file, all green.
  - `tests/unit/test_ingest.py`: one pinned literal (`entry_contract` ==
    `"library-entry.2"`) updated to `"library-entry.3"` — a mechanical
    consequence of the explicitly-requested version bump, not a scope
    expansion; no fixture counts changed.
  - No new fixture project added (fixture registry / golden counts
    untouched) — required block-form coverage was added as literal-text
    unit tests instead, avoiding any risk to the pinned
    `tests/golden/fixture-summary.json` counts.
- **Alternatives rejected:** duplicating validation logic for block form
  (rejected — contract explicitly frames block form as "same label set",
  and `_parse_entry` already encodes every validation rule; duplicating it
  would violate "reduce, never invent" and risk the two forms drifting);
  comma-splitting the whole `absorbs` value (rejected — breaks on the real
  corpus's internal-comma notes, per HYPERSAW).
- **Verify:** `./verify full`, exit 0, git `3ff1d34`
  (`.harness/last-verify.json`). `python3 -m unittest discover -q -s
  tests/unit -t .` — 108 tests, OK.
- **Real-corpus validation (read-only, v2 baseline measured via the prior
  commit's parser against the same files):**

  | project | v2 (lessons/quarantines) | v3 (lessons/quarantines) |
  |---|---|---|
  | Catena | 0 / 6 | 5 / 1 |
  | Antiphon | 0 / 3 | 0 / 3 (unchanged — see open question) |
  | Limen | 0 / 1 | 1 / 0 |
  | spectrogen | 0 / 5 | 5 / 0 |
  | HYPERSAW | 33 / 0 | 33 / 0 (unchanged count; `absorbs` now a real field on L0016/L0031, no longer in `extra`) |
  | morphos | 14 / 2 | 14 / 2 (unchanged) |
  | attest | 11 / 0 | 11 / 0 (unchanged) |

- **Open questions:**
  1. **Antiphon does not recover under v3, and the brief's "~3" hint implied
     it would.** Evidence: Antiphon's block entries use `**tag:**` (singular)
     never `**tags:**` (the required field), and never write a `**lesson:**`
     label at all — the entry's main paragraph is unlabeled prose
     immediately following the metadata line (`~/Documents/Claude/
     synthetic-worlds/Antiphon/LIBRARY.md:9-10`). Per the contract's literal
     text ("Fields carry the same label set... in any of these
     delimiters"), an un-labeled paragraph and a mis-spelled label are not
     covered by any of the three sanctioned shapes, so `tags`/`lesson`
     never open and the entry is genuinely malformed under v3 as specified
     — this is a corpus/contract mismatch, not a parser defect (confirmed:
     the mis-glued unlabeled paragraph continuation-joins onto whichever
     field is currently open, here `added`, producing the somewhat
     confusing "invalid added date" quarantine reason instead of a cleaner
     "missing lesson/tags" one — same continuation-join rule the v2 corpus
     already exercises, not new behavior). I did not invent an accommodation
     (aliasing `tag`→`tags`, or treating unlabeled paragraphs as implicit
     `lesson`) because neither is licensed by the contract text and both
     would be guessing at a ruling that belongs to a human/lead decision.
  2. **A latent terminator edge case, exposed (not introduced) by block
     form's multi-line spans:** Catena's L0001 loses its `falsifier` and
     `supersedes` fields because a physical line inside its wrapped
     `evidence:` paragraph happens to start with `#4` (a decision
     cross-reference, `~/Documents/Claude/synthetic-worlds/Catena/
     LIBRARY.md:27`) — the terminator regex `_HEADING_RE = ^#` (unchanged
     from v2, and matching the contract's literal "a markdown heading
     (`^#`)" text with no required following space) treats it as a heading
     and closes the span early. Brief explicitly scoped "Structural
     terminators — already implemented, now contract-owned. No change," so
     I did not touch this. Flagging because it is corpus-real (not a
     synthetic edge case) and asymmetric with the block-marker regex, which
     DOES require `\s+` after the hashes — a future contract ruling may want
     to require the same for the general terminator.
  3. The brief's morphos/attest expected counts (13/2, 10/0) do not match
     what I measured for either v2 or v3 (14/2, 11/0) — reported as
     measured, not reconciled; the acceptance criterion ("must be UNCHANGED
     from v2") holds regardless of which absolute number is correct.
