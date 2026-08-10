"""entry_parser — pure parser for LIBRARY.md text per the `library-entry.2`
contract (autonomous kit/contracts/library-entry.md) and the entry-span /
segment rules in docs/stream-schema.md §"Entry detection & parsing —
library-entry.2" (ROADMAP decision 15/16).

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
    "recurred",
)

_REQUIRED = ("tier", "added", "tags", "lesson", "evidence", "falsifier")

_OPTIONAL_REFS = ("origin", "supersedes", "recurred")

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

_HEADING_RE = re.compile(r"^#")
_HEADING_ENTRY_RE = re.compile(r"^#+\s*\[?L\d{4}")
_HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
_ANCHOR_RE = re.compile(r"^<a\b")
_FENCE_RE = re.compile(r"^```")

_KNOWN_LABEL_RE = re.compile(r"^\s*(%s)\s*:" % "|".join(_KNOWN_LABELS))
_EXTRA_LABEL_RE = re.compile(r"^\s*([\w-]+)\s*:")
_PLACEHOLDER_RE = re.compile(r"^[—–-]\s*(.*)$")


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
    attempts = []  # [(line_no, folded_raw)], in encounter order

    in_fence = False
    current = None  # {"line_no": int, "parts": [str, ...]} or None
    prev_class = "sof"  # "sof" | "blank" | "structural" | "content"

    def close_current():
        nonlocal current
        if current is not None:
            raw = " ".join(current["parts"])
            attempts.append((current["line_no"], raw))
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
            close_current()
            if _HEADING_ENTRY_RE.match(stripped):
                quarantines.append({
                    "line_no": line_no,
                    "raw": stripped,
                    "error": "heading-style entry marker %r (entries must be "
                             "[Lxxxx]-prefixed lines, never markdown headings)" % stripped,
                })
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
            # L0012's "Related:" list) carries none and must keep folding.
            if prev_class in ("blank", "structural", "sof") or "|" in stripped:
                close_current()
                current = {"line_no": line_no, "parts": [stripped]}
            elif current is not None:
                current["parts"].append(stripped)
            # else: pipeless marker-shaped line preceded by unrelated content
            # with no open span -- never observed in the corpus; treated as
            # ordinary text (neither opened nor quarantined) rather than
            # invented.
            prev_class = "content"
            continue

        if current is not None:
            current["parts"].append(stripped)
        prev_class = "content"

    close_current()
    unclosed_fence = in_fence

    parsed = []  # [(line_no, raw, "ok"/"error", entry_or_error_str)]
    for line_no, raw in attempts:
        entry, error = _parse_entry(raw)
        if error is not None:
            parsed.append((line_no, raw, "error", error))
        else:
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
            label = m_known.group(1)
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

    if extra_parts:
        entry["extra"] = {
            label: "|".join(parts).strip() for label, parts in extra_parts.items()
        }

    return entry, None
