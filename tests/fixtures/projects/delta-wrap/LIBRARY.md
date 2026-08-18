# Delta-Wrap LIBRARY

Fixture project for distillery `library-entry.2` parser tests. Not a real
project. Wrap-style entries, corpus-shaped per docs/stream-schema.md
§"Entry detection & parsing — library-entry.2".

---

[L0001] Multi-line entry with an interior blank line and a cross-reference
| tier: candidate | added: 2026-08-01
| tags: fixture
| lesson: This entry wraps across several physical lines on purpose. Related:
  [L0002] (see also L0002 for the companion note, which does not exist as its
  own entry in this fixture — this physical line must fold into L0001's
  lesson, never open a phantom span, per the marker-open predecessor rule).

  The blank line directly above is interior to this entry's span and must be
  skipped, not treated as a terminator (wont's house style).
| evidence: Constructed for the distillery v2 parser's phantom-span guard test.
| falsifier: If a standalone L0002 record (lesson or quarantine) appears from
  this fixture, the guard has failed.
| supersedes: —

---

[L0003] Repeated evidence labels both survive
| tier: candidate | added: 2026-08-01
| tags: fixture
| lesson: A field label may repeat; every repeat must continuation-join onto
  the same value rather than overwrite it.
| evidence: First evidence segment.
| falsifier: If only one evidence segment survives parsing, the join failed.
| evidence: Second evidence segment, appended independently of the first.
| supersedes: —

<a id="anchor-1"></a>

[L0004] Prose pipes inside a value must round-trip byte-exact | tier: candidate | added: 2026-08-01 | tags: fixture | lesson: The bound |x| never exceeds one after normalization. | evidence: Measured |x| across the fixture corpus. | falsifier: If |x| respaces to | x | anywhere in the parsed value, reconstruction is broken. | supersedes: —

[L0005] Supersedes placeholder with a preserved annotation | tier: candidate | added: 2026-08-01 | tags: fixture | lesson: A dash placeholder on supersedes still carries a note when one is present. | evidence: Authored directly for this fixture. | falsifier: If the note is dropped, the graph edge is lost. | supersedes: — (refines L0001)

[L0006] Unknown label followed by an unlabeled continuation | tier: candidate | added: 2026-08-01 | tags: fixture | lesson: An unknown labeled segment opens extra; an unlabeled segment right after it must join that extra value, not the previous known field. | evidence: Authored directly for this fixture. | falsifier: If the continuation lands on evidence instead of extra, the open-field tracking is wrong. | promoted: 2026-08-01 | still climbing as of the fixture's authoring | supersedes: —

---

[L0007] Duplicate id first occurrence | tier: candidate | added: 2026-08-01 | tags: fixture | lesson: Two entries share this id on purpose. | evidence: Authored directly for this fixture. | falsifier: If only one of the pair quarantines, the duplicate-id rule is half-applied.

[L0007] Duplicate id second occurrence | tier: candidate | added: 2026-08-01 | tags: fixture | lesson: This is the second entry sharing L0007. | evidence: Authored directly for this fixture. | falsifier: If only one of the pair quarantines, the duplicate-id rule is half-applied.

[L0008] Missing falsifier placeholder | tier: candidate | added: 2026-08-01 | tags: fixture | lesson: A required field carrying only a dash placeholder must quarantine. | evidence: Authored directly for this fixture. | falsifier: —

[L0009] Bad origin reference | tier: candidate | added: 2026-08-01 | tags: fixture | lesson: An origin value that is not project#Lxxxx and not a placeholder must quarantine. | evidence: Authored directly for this fixture. | falsifier: If this parses as a lesson, origin validation regressed. | origin: wend-L0007

### [L0099] Heading-style entry must quarantine, not vanish

## Notes

This trailing section is prose after the last real entry. It must never fold
into L0009 or any other entry — the heading directly above is a terminator.
