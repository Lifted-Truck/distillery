# library-entry-v3 — contract migration, and a near-miss on append-only

- **Queue item:** the explicit debt recorded at the kit 2.4.1 retrofit;
  discharges response-003 obligations 1–2. DECISIONS 21, 22.
- **Why:** the parser declared `library-entry.2` while the contract had been
  v3 since 2026-08-10. Sequenced ahead of D3 implementation deliberately:
  the analyst mines the stream, and v3 changes what is *in* it (block-form
  entries become visible; `absorbs` adds graph edges D3 walks).
- **Evidence consulted:** kit/contracts/library-entry.md (normative — the
  contract itself records that a response letter never is); response-003
  (block form, three adopted rules, bare-tier correction); response-004
  (`absorbs` = (b)); the real LIBRARYs of Catena, Antiphon, Limen,
  spectrogen, Plexus, Sympath, resume-workshop, Tonality, HYPERSAW,
  morphos, attest.
- **What the corpus taught that the contract's examples could not:** unit
  tests written from the spec passed while three projects failed. Labels are
  capitalised in the wild (`**Lesson:**`), and Tonality pipe-joins
  backticked fields with no leading pipe. Both fixed with regression tests
  naming the project that forced them. Antiphon was NOT rescued: it has no
  `lesson` label and writes `tag` singular — genuine absences, and inventing
  an unlabelled-prose rule to improve our own numbers is the failure the
  quarantine stance exists to prevent.
- **The near-miss (DECISIONS 22 / LIBRARY L0007):** regeneration was reused
  after its precondition ("journal uncommitted") had lapsed, erasing three
  lessons HYPERSAW had consolidated away at source. Every gate was green;
  it surfaced only as a regression column in the accounting. Restored from
  git, re-done as an append, which forced the `(project, hash, kind)`
  seen-key decision 16 had deferred to exactly this upgrade.
- **Alternatives rejected:** (a) keep regenerating and accept the loss —
  rejected, it breaks the charter's load-bearing invariant; (b) rescue
  Antiphon with an alias — rejected as inventing grammar; (c) do v3 after
  D3 — rejected, D3 would have mined a corpus missing 66 entries.
- **Verify:** `./verify full` exit 0 — 112 tests + replay_check. Stream
  198 → 270 records, append-only prefix verified byte-wise against
  `git show HEAD~1:stream/stream.jsonl`.
- **Open questions:** two filed to autonomous in report-003 (state the
  case-insensitivity rule; rule on Antiphon). Mailbox fixture refresh still
  owed. D3 implementation is now unblocked on a v3 corpus.
