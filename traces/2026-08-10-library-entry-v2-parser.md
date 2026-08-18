# library-entry-v2-parser — upgrade entry_parser to `library-entry.2`

- **Queue item:** ROADMAP decisions 15/16 (adopt `library-entry.2`; genesis
  regenerated from empty, seen-key stays `(project, hash)`).
- **Why:** v1's line-delimited grammar quarantined multi-line (wrap-style)
  entries and prose containing literal pipes, losing promotion-grade
  content for no information gain. v2 makes the entry span marker-delimited
  (`[Lxxxx]` to next marker/terminator/EOF) with byte-exact pipe
  reconstruction, per the provider ruling and the critic-reworked design in
  docs/stream-schema.md.
- **Evidence consulted:** docs/stream-schema.md §"Entry detection & parsing
  — library-entry.2"; autonomous kit/contracts/library-entry.md (v2);
  ROADMAP.md decisions 15/16; the v1 entry_parser.py and its existing unit
  tests; real corpus reads (read-only) of morphos, synthetic-worlds/wont,
  synthetic-worlds/HYPERSAW, and Tonality LIBRARY.md files to validate the
  marker-open predecessor rule, terminator handling, and heading-style
  quarantine against actual entry shapes (not just the spec prose).
- **Alternatives rejected:** none considered — the design doc is ratified
  and cited as the specification; implementation followed it directly
  rather than re-deriving an alternate grammar.
- **Verify:** `./verify full`, exit 0, git `72d43a5` (pre-existing HEAD at
  dispatch time; this trace's own changes are uncommitted, staged for the
  lead's review/commit). `python3 -m unittest discover -q -s tests/unit -t .`
  — 80 tests, OK. `python3 tests/replay_check.py` — OK (golden, replay,
  idempotency).
- **Open questions:**
  1. **Brief-vs-reality mismatch on Tonality's LIBRARY.md** (flagged to the
     lead, not silently resolved): the brief's read-first corpus list
     states Tonality "still zero entries, zero quarantines." The file's
     preamble+fenced-template portion IS zero/zero, but the file also
     contains three real entries using a heading-style format
     (`### [L0001] <title>` + backtick-quoted fields + a bullet list body)
     that matches `^#+\s*\[?L\d{4}` exactly — the heading-style-entry
     quarantine rule the spec itself calls out (and ROADMAP decision 16
     cites as "20 [entries] across 8 projects, invisible under both
     contracts... filed as distillery-003"). Implemented per spec (these
     three quarantine visibly, with a distinct "heading-style entry marker"
     error) rather than per the brief's stated expectation. Verified via a
     read-only parse of the real file (not committed as a test — see below).
  2. **Existing fixtures required corpus-shape correction, not just API
     migration.** Real LIBRARYs blank-separate every entry (verified in
     HYPERSAW, morphos, wont); the marker-open predecessor rule needs this
     because a span, once open, stays open through content lines, so two
     back-to-back single-line entries with no blank between them fold into
     ONE span under v2. The pre-existing alpha/beta fixtures had no blank
     lines between their single-line entries (fine under v1's line-delimited
     grammar, broken under v2). Fixed by inserting blank lines between
     fixture entries — a corpus-shape correction, not a semantic change to
     what those entries assert.
  3. **v1→v2 regression scope, clarified rather than assumed:** alpha's
     pre-existing "duplicate raw line in one file" test (L0004 appearing
     twice) asserted both parsed as lessons under v1 (parser doesn't dedup;
     that's ingest's job). v2's contract adds a NEW rule — duplicate id
     within a file quarantines both — that the v1 test predates and
     contradicts. Updated the test to assert the new (correct, spec-mandated)
     behavior rather than treating it as a "same entry dict" v1-regression
     case, since the contract explicitly lists "duplicate id in a file" in
     its exhaustive still-quarantine list.
