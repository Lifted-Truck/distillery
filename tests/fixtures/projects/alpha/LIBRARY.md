# Alpha LIBRARY

Fixture project for distillery D1 tests. Do not treat as a real project.

Template example (must NOT be ingested — it lives inside a fenced code
block, per the fence-tracking rule in docs/stream-schema.md):

```
[L0001] example | tier: candidate | added: 2026-01-01 | tags: x | lesson: example lesson | evidence: example evidence | falsifier: example falsifier | supersedes: —
```

## Entries

Real LIBRARYs blank-separate entries (corpus-verified, docs/stream-schema.md
§library-entry.2 marker-open predecessor rule) — each entry below is its own
span, opened by a blank-line predecessor.

[L0001] Bare tier form | candidate | added: 2026-07-07 | tags: measurement | lesson: Bare tier form parses the same as labeled tier form. | evidence: Ran ingest against a bare-tier line. | falsifier: If bare tier stops parsing, this is false. | supersedes: —

[L0002] Labeled tier form | tier: candidate | added: 2026-07-07 | tags: measurement | lesson: Labeled tier form is the dominant shape in real LIBRARYs. | evidence: Ran ingest against a labeled-tier line. | falsifier: If labeled tier stops parsing, this is false. | supersedes: —

[L12] short id missing digits | tier: candidate | added: 2026-07-07 | tags: x | lesson: bad id | evidence: e | falsifier: f

[l0002] lowercase bracket id | tier: candidate | added: 2026-07-07 | tags: x | lesson: bad id casing | evidence: e | falsifier: f

[L0003] Missing falsifier | tier: candidate | added: 2026-07-07 | tags: measurement | lesson: This entry has an empty falsifier placeholder. | evidence: Observed a dash in the falsifier field. | falsifier: —

[L0004] Shared across projects | tier: candidate | added: 2026-07-07 | tags: shared | lesson: This exact line appears verbatim in two different projects. | evidence: Copy-pasted into alpha and beta LIBRARYs. | falsifier: If cross-project dedup collapses this, that is a bug. | supersedes: —

[L0004] Shared across projects | tier: candidate | added: 2026-07-07 | tags: shared | lesson: This exact line appears verbatim in two different projects. | evidence: Copy-pasted into alpha and beta LIBRARYs. | falsifier: If cross-project dedup collapses this, that is a bug. | supersedes: —
