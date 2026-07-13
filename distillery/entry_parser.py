"""entry_parser — pure parser for LIBRARY.md text per the `library-entry.1`
contract (autonomous kit/contracts/library-entry.md) and the fence/tolerance
rules in docs/stream-schema.md.

Pure function of (text) -> (lessons, quarantines). No I/O, no wall-clock, no
model calls. Every attempted-entry line (case-insensitive ``^\\[l`` outside a
fenced code block) lands in exactly one of the two lists — never silently
dropped.
"""

import re

_TIER_ENUM = ("candidate", "canonical", "proliferated")

_KNOWN_KEYS = {
    "tier",
    "added",
    "tags",
    "origin",
    "lesson",
    "evidence",
    "falsifier",
    "supersedes",
    "recurred",
}

_REQUIRED = ("tier", "added", "tags", "lesson", "evidence", "falsifier")

_PLACEHOLDERS = ("—", "-", "")  # em-dash, hyphen, empty

_ATTEMPT_RE = re.compile(r"^\[l", re.IGNORECASE)
_HEADER_RE = re.compile(r"^\[(L\d{4})\]\s*(.*)$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ORIGIN_ITEM_RE = re.compile(r"^[^#]+#L\d{4}$")
_SUPERSEDES_RE = re.compile(r"^L\d{4}$")


def parse_library(text):
    """Parse one LIBRARY.md's full text.

    Returns (lessons, quarantines):
      lessons     -> [{"line_no": int, "raw": str, "entry": {...}}, ...]
      quarantines -> [{"line_no": int, "raw": str, "error": str}, ...]
    """
    lessons = []
    quarantines = []
    in_fence = False

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()

        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not _ATTEMPT_RE.match(stripped):
            continue

        entry, error = _parse_entry_line(stripped)
        if error is not None:
            quarantines.append({"line_no": line_no, "raw": stripped, "error": error})
        else:
            lessons.append({"line_no": line_no, "raw": stripped, "entry": entry})

    return lessons, quarantines


def _parse_entry_line(line):
    """Parse one attempted-entry line. Returns (entry_dict, None) or (None, error)."""
    segments = [s.strip() for s in line.split("|")]
    header = segments[0]

    m = _HEADER_RE.match(header)
    if not m:
        return None, "invalid id/title header %r (expected [Lxxxx] <title>)" % header

    entry_id, title = m.group(1), m.group(2).strip()
    if not title:
        return None, "missing title"

    fields = {}
    unknown = []
    for seg in segments[1:]:
        if not seg:
            continue
        if seg in _TIER_ENUM:
            fields["tier"] = seg
            continue
        if ":" in seg:
            key, _, val = seg.partition(":")
            key = key.strip().lower()
            val = val.strip()
            if key in _KNOWN_KEYS:
                fields[key] = val
            else:
                unknown.append(seg)
        else:
            unknown.append(seg)

    if unknown:
        return None, "unrecognized segment(s): %s" % "; ".join(unknown)

    for name in _REQUIRED:
        if name not in fields or fields[name] in _PLACEHOLDERS:
            return None, "required field '%s' missing or empty" % name

    if fields["tier"] not in _TIER_ENUM:
        return None, "invalid tier: %r" % fields["tier"]

    if not _DATE_RE.match(fields["added"]):
        return None, "invalid added date: %r (expected YYYY-MM-DD)" % fields["added"]

    tags = [t.strip() for t in fields["tags"].split(",") if t.strip()]
    if not tags:
        return None, "tags must be a non-empty list"

    entry = {
        "id": entry_id,
        "title": title,
        "tier": fields["tier"],
        "added": fields["added"],
        "tags": tags,
        "lesson": fields["lesson"],
        "evidence": fields["evidence"],
        "falsifier": fields["falsifier"],
    }

    if "origin" in fields and fields["origin"] not in _PLACEHOLDERS:
        origin_items = [o.strip() for o in fields["origin"].split(",") if o.strip()]
        if not origin_items:
            return None, "origin present but empty after normalization"
        for item in origin_items:
            if not _ORIGIN_ITEM_RE.match(item):
                return None, "invalid origin item: %r" % item
        entry["origin"] = origin_items

    if "supersedes" in fields and fields["supersedes"] not in _PLACEHOLDERS:
        if not _SUPERSEDES_RE.match(fields["supersedes"]):
            return None, "invalid supersedes: %r" % fields["supersedes"]
        entry["supersedes"] = fields["supersedes"]

    if "recurred" in fields and fields["recurred"] not in _PLACEHOLDERS:
        entry["recurred"] = fields["recurred"]

    return entry, None
