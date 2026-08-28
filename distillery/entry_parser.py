"""entry_parser — pure parser for LIBRARY.md text per the `library-entry.3`
contract (autonomous kit/contracts/library-entry.md) and the entry-span /
segment rules in docs/stream-schema.md §"Entry detection & parsing —
library-entry.2" (ROADMAP decision 15/16). v3 is a superset of v2 (see the
contract's own changelog): structural terminators, the span-open condition
and repeated-known-label continuation-join were already implemented as v2
behavior and are now contract-owned, unchanged here.

Pure function of (text) -> (lessons, quarantines, meta). No I/O, no
wall-clock, no model calls. Every attempted-entry span lands in exactly one
of the two lists — never silently dropped.

Entry span model (multi-line entries are valid, ROADMAP decision 16):
  A stripped line matching case-insensitive ``^\\[l`` outside a fence opens a
  span, but ONLY if the immediately preceding physical line is blank,
  structural (a terminator-shaped line), or start-of-file. This is the
  phantom-span guard: a wrapped-prose line that happens to start with
  ``[Lxxxx]`` (e.g. morphos L0012's "Related: [L0009] .../ [L0010] (curvature
  caps...") is preceded by ordinary prose, so it folds into the still-open
  span instead of spawning a phantom entry. Terminators (fence delimiters,
  ``^#`` headings, ``^-{3,}$``/``^\\*{3,}$``/``^_{3,}$`` rules, ``^<a\\b``
  anchors) ALWAYS close an open span, unconditionally -- the predecessor
  gate applies only to the marker-open decision, never to terminators.
  Blank lines are skipped, not terminators (wont's entries wrap across an
  interior blank). Non-structural lines fold into the span's raw with a
  single space; that folded raw is what gets split on ``|`` below.

Block form (v3, READ-only): a heading matching ``^#{2,6}\\s+\\[?L\\d{4}\\]?``
is the ONE stated exception to "headings are structural terminators" -- it
terminates any open span AND opens a new block span (contract §Block form).
Three corpus shapes (Catena/Limen bracketed, Antiphon bare+em-dash,
resume-workshop bare+title-on-next-line) all reduce to the same (id, title,
field lines) triple; those field lines are then rewritten into a synthetic
line-form raw (`_block_to_parse_raw`) and handed to the SAME `_parse_entry`
that validates line-form entries. This is deliberate, not laziness: it means
block form inherits every validation rule (required fields, tier enum,
placeholder handling, repeated-label join, literal-pipe round-trip) for
free, with zero duplicated logic -- "reduce, never invent". A heading that
does NOT match the block-marker shape stays a plain terminator, unchanged
from v2.
"""

import re

_TIER_ENUM = ("candidate", "canonical", "proliferated")

_KNOWN_LABELS = (
    "tier",
    "added",
    "tags",
    "origin",
    "lesson",
    "evidence",
    "falsifier",
    "supersedes",
    "absorbs",
    "recurred",
)

_REQUIRED = ("tier", "added", "tags", "lesson", "evidence", "falsifier")

# supersedes: that entry was WRONG, don't promote it (invalidate-don't-erase).
# absorbs: those entries are now special cases of THIS one; their evidence
# CONTRIBUTES to this entry's weight (fold-in, not invalidation). The
# distinction is load-bearing for D3's promotion judgment -- collapsing them
# would make a consolidation indistinguishable from a multi-way invalidation.
_OPTIONAL_REFS = ("origin", "supersedes", "recurred", "absorbs")

# Required-field placeholders: EXACT match only (never a prefix test) -- a
# genuine value that happens to start with a hyphen ("-5 dB drop") must never
# be mistaken for a missing-field placeholder. Optional-field placeholders
# use the broader prefix-capturing regex below, per the annotated-placeholder
# rule (`supersedes: — (refines L0001)`).
_REQUIRED_PLACEHOLDERS = ("—", "–", "-", "")

_ATTEMPT_RE = re.compile(r"^\[l", re.IGNORECASE)
_HEADER_RE = re.compile(r"^\[(L\d{4})\]\s*(.*)$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ORIGIN_ITEM_RE = re.compile(r"^[^#]+#L\d{4}$")
_SUPERSEDES_RE = re.compile(r"^L\d{4}$")
# Leading comma-separated run of valid L\d{4} tokens, capturing whatever
# follows (empty / a dash-annotation / stray leftover) as group 2 -- see
# _parse_absorbs for why this shape (not a plain comma-split) is required.
_ABSORBS_LEAD_RE = re.compile(r"^((?:L\d{4}\s*,\s*)*L\d{4})(.*)$")

_HEADING_RE = re.compile(r"^#")
# The block-form entry marker (contract §Block form): 2-6 hashes, then an
# optionally-bracketed Lxxxx id. Deliberately narrower than a bare "#" so an
# H1 title never opens a block span. This is the ONE heading shape that is
# an exception to "headings are structural terminators".
_BLOCK_MARKER_RE = re.compile(r"^(#{2,6})\s+\[?(L\d{4})\]?(.*)$")
_DASH_PREFIX_RE = re.compile(r"^[—–-]\s*(.*)$")
_HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
_ANCHOR_RE = re.compile(r"^<a\b")
_FENCE_RE = re.compile(r"^```")

# Case-INSENSITIVE: resume-workshop writes "**Lesson:**", Antiphon
# "**evidence:**". The contract prints labels lowercase but its own
# distillery-003 audit ("Antiphon, Catena, Limen and resume-workshop each
# carry lesson, evidence and falsifier") only holds under a
# case-insensitive read. Filed to autonomous to state explicitly.
_KNOWN_LABEL_RE = re.compile(r"^\s*(%s)\s*:" % "|".join(_KNOWN_LABELS),
                             re.IGNORECASE)
_EXTRA_LABEL_RE = re.compile(r"^\s*([\w-]+)\s*:")
_PLACEHOLDER_RE = re.compile(r"^[—–-]\s*(.*)$")

# Block-form field-line delimiters (contract §Block form): a field carries
# the same label set as line form, wrapped in one of three ways. Middot (·)
# additionally separates several inline bold fields on one physical line.
_BLOCK_PIPE_RE = re.compile(r"^\|\s*(.*)$")
_BLOCK_BULLET_RE = re.compile(r"^-\s+(.*)$")
_BLOCK_BOLD_RE = re.compile(r"^\*\*([\w-]+):\*\*\s*(.*)$")
_MIDDOT = "·"


def parse_library(text):
    """Parse one LIBRARY.md's full text.

    Returns (lessons, quarantines, meta):
      lessons     -> [{"line_no": int, "raw": str, "entry": {...}}, ...]
      quarantines -> [{"line_no": int, "raw": str, "error": str}, ...]
      meta        -> {"unclosed_fence": bool}

    "line_no" is the marker line's number; "raw" is the folded raw (single
    line for single-line entries, space-joined for multi-line ones).
    """
    lessons = []
    quarantines = []
    attempts = []  # [(line_no, raw_for_storage, parse_input, form)], in order

    in_fence = False
    # current is None, or one of:
    #   {"kind": "line",  "line_no": int, "parts": [str, ...]}
    #   {"kind": "block", "line_no": int, "raw_lines": [...], "id": str,
    #    "title": str or None (None = pending, resolved by the first
    #    following non-empty line per the resume-workshop shape),
    #    "field_lines": [...]}
    current = None
    prev_class = "sof"  # "sof" | "blank" | "structural" | "content"

    def fold_line(stripped):
        # Append one physical content line into whichever span is open,
        # handling the block form's title-pending state uniformly so every
        # caller (plain prose, a marker-shaped fold) shares one rule: the
        # FIRST content line after a titleless block heading is consumed as
        # the title, never as a field line (contract: "that line is then
        # consumed as the title, not as field content").
        if current["kind"] == "line":
            current["parts"].append(stripped)
        else:
            current["raw_lines"].append(stripped)
            if current["title"] is None:
                current["title"] = stripped
            else:
                current["field_lines"].append(stripped)

    def close_current():
        nonlocal current
        if current is None:
            return
        if current["kind"] == "line":
            raw = " ".join(current["parts"])
            attempts.append((current["line_no"], raw, raw, "line"))
        else:
            raw = " ".join(current["raw_lines"])
            parse_input = _block_to_parse_raw(
                current["id"], current["title"] or "", current["field_lines"]
            )
            attempts.append((current["line_no"], raw, parse_input, "block"))
        current = None

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()

        if _FENCE_RE.match(stripped):
            close_current()
            in_fence = not in_fence
            prev_class = "structural"
            continue

        if in_fence:
            # Fenced content is never ingested and never opens/extends a span.
            continue

        if _HEADING_RE.match(stripped):
            m_block = _BLOCK_MARKER_RE.match(stripped)
            if m_block:
                # The stated exception (contract §Block form): this heading
                # shape terminates any open span AND opens a new block span.
                close_current()
                entry_id = m_block.group(2)
                remainder = m_block.group(3).strip()
                m_dash = _DASH_PREFIX_RE.match(remainder)
                title = (m_dash.group(1).strip() if m_dash else remainder)
                current = {
                    "kind": "block",
                    "line_no": line_no,
                    "raw_lines": [stripped],
                    "id": entry_id,
                    "title": title if title else None,
                    "field_lines": [],
                }
                prev_class = "content"
                continue
            # An ordinary heading (no Lxxxx marker shape) is a plain
            # terminator, same as v2 -- it closes but never opens.
            close_current()
            prev_class = "structural"
            continue

        if _HR_RE.match(stripped) or _ANCHOR_RE.match(stripped):
            close_current()
            prev_class = "structural"
            continue

        if stripped == "":
            prev_class = "blank"
            continue

        if _ATTEMPT_RE.match(stripped):
            # A marker opens a span when its predecessor is blank/structural/
            # start-of-file, OR when the marker line itself carries a "|" —
            # a real single-line entry always does (attest writes back-to-back
            # pipe-bearing entries with no blank separators), while a wrapped
            # prose line beginning with a [Lxxxx] cross-reference (morphos
            # L0012's "Related:" list) carries none and must keep folding
            # (into whichever span kind is currently open, line or block).
            if prev_class in ("blank", "structural", "sof") or "|" in stripped:
                close_current()
                current = {"line_no": line_no, "kind": "line", "parts": [stripped]}
            elif current is not None:
                fold_line(stripped)
            # else: pipeless marker-shaped line preceded by unrelated content
            # with no open span -- never observed in the corpus; treated as
            # ordinary text (neither opened nor quarantined) rather than
            # invented.
            prev_class = "content"
            continue

        if current is not None:
            fold_line(stripped)
        prev_class = "content"

    close_current()
    unclosed_fence = in_fence

    parsed = []  # [(line_no, raw, "ok"/"error", entry_or_error_str)]
    for line_no, raw, parse_input, form in attempts:
        entry, error = _parse_entry(parse_input)
        if error is not None:
            parsed.append((line_no, raw, "error", error))
        else:
            if form == "block":
                # v3 JSON Schema: which serialization this was READ from.
                # Line is canonical for writing; recorded so a later
                # migration can find block-form entries without re-parsing.
                entry["entry_form"] = "block"
            parsed.append((line_no, raw, "ok", entry))

    # Duplicate id within a file quarantines BOTH (contract still-quarantine
    # rule 1) -- checked across all successfully-parsed entries in this file.
    id_counts = {}
    for line_no, raw, kind, payload in parsed:
        if kind == "ok":
            id_counts[payload["id"]] = id_counts.get(payload["id"], 0) + 1

    for line_no, raw, kind, payload in parsed:
        if kind == "error":
            quarantines.append({"line_no": line_no, "raw": raw, "error": payload})
        elif id_counts[payload["id"]] > 1:
            quarantines.append({
                "line_no": line_no,
                "raw": raw,
                "error": "duplicate id %r within file (%d occurrences)"
                         % (payload["id"], id_counts[payload["id"]]),
            })
        else:
            lessons.append({"line_no": line_no, "raw": raw, "entry": payload})

    return lessons, quarantines, {"unclosed_fence": unclosed_fence}


def _block_field_segments(field_lines):
    """Convert block-form field lines into a flat list of 'label: value' (or
    bare unlabeled-continuation) strings, in encounter order.

    Handles all three delimiters (`| label: value`, `**label:** value`,
    `- **label:** value`) and middot-separated inline bold fields on one
    line. A line that matches none of the three shapes is passed through
    verbatim as an unlabeled continuation segment -- `_parse_entry`'s
    existing open-field continuation-join then folds it onto whichever
    field is open, exactly as it already does for line-form prose (this is
    what makes multi-physical-line block values, e.g. Catena's wrapped
    `lesson:` bullets, work with no new code).
    """
    segments = []
    for line in field_lines:
        # A block field line may carry SEVERAL fields, separated by middots
        # (Antiphon: "**tier:** x · **added:** y") or by pipes (Tonality:
        # "`tier: candidate` | `added: ...` | `tags: ...`"). Splitting on the
        # pipe rather than only stripping a leading one is corpus-forced:
        # Tonality's line begins with a backtick, so a leading-pipe rule sees
        # the whole line as one segment and the tier value swallows the rest.
        parts = []
        for chunk in line.split(_MIDDOT):
            parts.extend(chunk.split("|"))
        for part in parts:
            part = part.strip()
            if not part:
                continue
            m_bullet = _BLOCK_BULLET_RE.match(part)
            if m_bullet:
                part = m_bullet.group(1).strip()
            # Tonality wraps whole fields in a markdown code span:
            # `tier: candidate` | `added: 2026-07-07`. The backticks are
            # presentation, not delimiters -- strip a matched pair so the
            # label underneath is visible to the label rules.
            if len(part) > 1 and part.startswith("`") and part.endswith("`"):
                part = part[1:-1].strip()
            m_bold = _BLOCK_BOLD_RE.match(part)
            if m_bold:
                segments.append("%s: %s" % (m_bold.group(1), m_bold.group(2)))
            else:
                # Already canonical ("label: value" from the pipe form) or
                # genuinely unlabeled prose -- either way, pass through.
                segments.append(part)
    return segments


def _block_to_parse_raw(entry_id, title, field_lines):
    """Rewrite one block span's (id, title, field lines) into a synthetic
    line-form raw, so it can be handed to `_parse_entry` unchanged. This is
    an internal parse-time construction ONLY -- the entry's stored "raw" is
    the original literal text (see close_current), never this string.
    """
    header = "[%s] %s" % (entry_id, title)
    segments = _block_field_segments(field_lines)
    if not segments:
        return header
    return header + "|" + "|".join(segments)


def _parse_entry(raw):
    """Parse one folded entry raw. Returns (entry_dict, None) or (None, error)."""
    segments = raw.split("|")
    header_raw = segments[0]

    m = _HEADER_RE.match(header_raw)
    if not m:
        return None, "invalid id/title header %r (expected [Lxxxx] <title>)" % header_raw.strip()

    entry_id = m.group(1)
    title_first = m.group(2)

    # open_field: "title" | None | <known label str> | ("extra", label)
    open_field = "title"
    raw_parts = {"title": [title_first]}
    extra_parts = {}
    known_seen = set()
    extra_seen = set()
    tier_bare = None

    for i in range(1, len(segments)):
        seg = segments[i]
        trimmed = seg.strip()

        if i == 1 and trimmed in _TIER_ENUM:
            # Segment-1-only bare tier (canonical contract rule): the SAME
            # enum word appearing later as an unlabeled segment must NOT be
            # re-treated as tier -- it joins whatever field is open there.
            tier_bare = trimmed
            open_field = None
            continue

        m_known = _KNOWN_LABEL_RE.match(seg)
        if m_known:
            # lower(): the label regex is case-insensitive, but parsed-form
            # keys are always the contract's lowercase names.
            label = m_known.group(1).lower()
            if label in known_seen:
                # Repeat of an already-seen known label continuation-joins
                # into the existing value, label text and pipe restored --
                # never last-wins (morphos L0007: two evidence:, two
                # falsifier: segments, both survive).
                raw_parts[label].append(seg)
            else:
                known_seen.add(label)
                raw_parts[label] = [seg[m_known.end():]]
            open_field = label
            continue

        m_extra = _EXTRA_LABEL_RE.match(seg)
        if m_extra:
            label = m_extra.group(1)
            if label in extra_seen:
                extra_parts[label].append(seg)
            else:
                extra_seen.add(label)
                extra_parts[label] = [seg[m_extra.end():]]
            open_field = ("extra", label)
            continue

        # Unlabeled segment: continuation-joins onto the currently open
        # field, splitting pipe restored (byte-exact: "|".join later).
        if open_field is None:
            return None, "unattached segment (no open field): %r" % trimmed
        if open_field == "title":
            raw_parts["title"].append(seg)
        elif isinstance(open_field, tuple):
            extra_parts[open_field[1]].append(seg)
        else:
            raw_parts[open_field].append(seg)

    title = "|".join(raw_parts["title"]).strip()
    if not title:
        return None, "missing title"

    def joined(label):
        if label not in raw_parts:
            return None
        return "|".join(raw_parts[label]).strip()

    tier = joined("tier") if "tier" in raw_parts else tier_bare
    added = joined("added")
    tags_raw = joined("tags")
    lesson = joined("lesson")
    evidence = joined("evidence")
    falsifier = joined("falsifier")

    if tier is None or tier not in _TIER_ENUM:
        return None, "invalid tier: %r" % (tier,)

    if added is None or added in _REQUIRED_PLACEHOLDERS:
        return None, "required field 'added' missing or empty"
    if not _DATE_RE.match(added):
        return None, "invalid added date: %r (expected YYYY-MM-DD)" % added

    if tags_raw is None or tags_raw in _REQUIRED_PLACEHOLDERS:
        return None, "required field 'tags' missing or empty"
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    if not tags:
        return None, "tags must be a non-empty list"

    for name, value in (("lesson", lesson), ("evidence", evidence), ("falsifier", falsifier)):
        if value is None or value in _REQUIRED_PLACEHOLDERS:
            return None, "required field '%s' missing or empty" % name

    entry = {
        "id": entry_id,
        "title": title,
        "tier": tier,
        "added": added,
        "tags": tags,
        "lesson": lesson,
        "evidence": evidence,
        "falsifier": falsifier,
    }

    for field in _OPTIONAL_REFS:
        value = joined(field)
        if value is None:
            continue
        m_ph = _PLACEHOLDER_RE.match(value)
        if m_ph:
            note = m_ph.group(1).strip()
            if note:
                entry["%s_note" % field] = note
            continue
        if field == "origin":
            origin_items = [o.strip() for o in value.split(",") if o.strip()]
            if not origin_items:
                return None, "origin present but empty after normalization"
            for item in origin_items:
                if not _ORIGIN_ITEM_RE.match(item):
                    return None, "invalid origin item: %r" % item
            entry["origin"] = origin_items
        elif field == "supersedes":
            if not _SUPERSEDES_RE.match(value):
                return None, "invalid supersedes: %r" % value
            entry["supersedes"] = value
        elif field == "recurred":
            entry["recurred"] = value
        elif field == "absorbs":
            absorbs, absorbs_note, err = _parse_absorbs(value)
            if err is not None:
                return None, err
            entry["absorbs"] = absorbs
            if absorbs_note:
                entry["absorbs_note"] = absorbs_note

    if extra_parts:
        entry["extra"] = {
            label: "|".join(parts).strip() for label, parts in extra_parts.items()
        }

    return entry, None


def _parse_absorbs(value):
    """Parse an `absorbs` value already known NOT to be the whole-field
    placeholder (that case is handled generically before this is called).
    Returns (list_of_ids, note_or_empty, error_or_None).

    Grammar: a comma-separated run of `L\\d{4}` references, optionally
    followed by free-text remainder (HYPERSAW's real shape: `L0011, L0021,
    L0034 — shell-path, superset and layer blindness respectively;
    consolidated 2026-08-11` -- note the em-dash note ITSELF contains
    commas, so the note can't be extracted by comma-splitting the whole
    value; only the LEADING run of clean references is comma-split).

    A remainder that starts with a stray comma (e.g. "L0011, badref") means
    the list continuation broke down -- that's a genuinely invalid element,
    not a note, and quarantines per the contract's still-quarantine rule 4
    ("every element must be a valid reference; one bad element quarantines
    the entry"). Any other non-empty remainder is free text: a leading dash
    is stripped (mirrors the other reference fields' placeholder-note
    convention) but a remainder needs no dash to count as a note --
    `absorbs: L0011 (see also)` is legitimate prose, not a broken list.
    """
    m = _ABSORBS_LEAD_RE.match(value.strip())
    if not m:
        return None, None, "invalid absorbs value: %r (expected comma-separated L\\d{4} references)" % value
    ids = re.findall(r"L\d{4}", m.group(1))
    remainder = m.group(2).strip()
    if remainder.startswith(","):
        return None, None, "invalid absorbs item after %s: %r" % (ids[-1], remainder)
    if not remainder:
        return ids, "", None
    m_dash = _DASH_PREFIX_RE.match(remainder)
    note = m_dash.group(1).strip() if m_dash else remainder
    return ids, note, None
