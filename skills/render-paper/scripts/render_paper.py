#!/usr/bin/env python3
"""render-paper — build the document from the skeleton, and run the gate.

Python 3, standard library only. No third-party import at runtime.

The document is written to stdout; the verdict table and every diagnostic go to
stderr. `--check` writes no document at all.

Exit codes are the contract every other unit reads:

    0   no FAIL at this granularity
    1   at least one submit-gating FAIL
    2   at least one hard error, or the renderer cannot run
    3   a parse error — nothing ran, so no table is printed

See `SKILL.md`, `SKELETON-FORMAT.md` and `SPINE-FORMAT.md` beside this script.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_GATING = 1
EXIT_HARD = 2
EXIT_PARSE = 3

# Check tiers. The tier answers one question: would the render emit something
# false? Hard iff the emitted document is not the document the source
# describes; gating iff the render is faithful but the work is unfinished;
# parse iff the source cannot express the thing at all. Reported iff the fact
# is worth an author's attention and no exit code: a reported row is a
# measurement, and gating submission is reserved to the annotation gate bit.
HARD = "hard"
GATING = "gating"
REPORTED = "reported"

# The three verdicts, and nothing else. No single-word verdict is emitted
# anywhere: one word cannot carry checked-and-fine against never-looked.
PASS = "PASS"
FAIL = "FAIL"
SKIPPED = "SKIPPED — OUT OF SCOPE AT THIS GRANULARITY"

# A fourth outcome, which is not a verdict at all: the row prints a number.
NUMBER = "number"

DOCUMENT = "document"
SECTION = "section"

NAME_WIDTH = 32
INDENT = "  "

SLOT_ID = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
COMMENT = re.compile(r"<!--(.*?)-->", re.DOTALL)
ANCHOR_INTENT = re.compile(r"^slot\s*:", re.IGNORECASE)
ANCHOR = re.compile(r"^slot\s*:\s*(\S+)\s*$")
HEADING = re.compile(r"^ {0,3}#{1,6}(\s|$)")
SETEXT = re.compile(r"^ {0,3}(=+|-+)\s*$")
FENCE = re.compile(r"^ {0,3}(?:```|~~~)", re.MULTILINE)
RUNG_HEADING = re.compile(r"^###\s+(\S+)\s+—\s+(.+?)\s*$")
RUNG_FIELD = re.compile(r"^-\s+([a-z-]+)\s*:\s*(.*?)\s*$")
OPENS_VALUE = re.compile(r"^(D\d+)\s+\(closed by (R\d+)\)\s+—\s+(\S.*)$")
DEBT_ID = re.compile(r"^D\d+$")
RUNG_ID = re.compile(r"^R\d+$")

# What the prose diagnostics read, and what they refuse to read. Scope is
# defined rather than assumed: a count that walks over a table row or a quoted
# source title fires on text no author wrote as prose.
EM_DASH = "—"
TABLE_ROW = re.compile(r"^ {0,3}\|.*$", re.MULTILINE)
BRACKET_SPAN = re.compile(r"\[[^\[\]]*\]")
BRACE_SPAN = re.compile(r"\{[^{}]*\}")

# Sentence splitting is mechanical and conservative: a terminator followed by
# whitespace, unless what precedes it is an abbreviation or an initial.
SENTENCE_END = re.compile(r"[.!?][\"'’”)\]]*(?=\s|$)")
ABBREVIATION = re.compile(
    r"(?:\b(?:et al|e\.g|i\.e|cf|vs|Fig|Figs|Eq|Ref|no|approx|ca|Dr|Prof|Mr|Mrs|Ms|St)\.|"
    r"\b[A-Z]\.)$"
)

# A word is a whitespace-delimited token with a letter or digit in it, so a
# standalone dash is punctuation rather than a word.
WORD = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*")

# The connectives that mark a turn. The list is deliberately short and dumb:
# the number it produces is read as a consequence of the em-dash gate forcing
# relation-first rewriting, never as a target to be hit.
ADVERSATIVE = re.compile(
    r"\b(?:however|but|yet|although|though|whereas|while|nevertheless|nonetheless|"
    r"conversely|despite|even so|by contrast|in contrast|in spite of)\b",
    re.IGNORECASE,
)

LONG_SENTENCE = 35
OPENINGS_SHOWN = 5

# The skill-level default threshold. Zero is honestly achievable and
# ungameable: removing a dash forces the relation work, and doing that work
# badly still yields an honest count.
EM_DASH_DEFAULT = 0

BANNER = (
    "---\n"
    "generated-by: render-paper\n"
    "do-not-edit: this file is output; edit the source it was rendered from\n"
    "---\n"
)


class ParseError(Exception):
    """The source, the skeleton or the spine cannot be parsed, so nothing ran."""


class HardError(Exception):
    """The renderer cannot produce the document the source describes."""


# --------------------------------------------------------------------------
# the two file formats this unit owns
# --------------------------------------------------------------------------


class Slot:
    def __init__(self, id, level, heading, partitions_on):
        self.id = id
        self.level = level
        self.heading = heading
        self.partitions_on = partitions_on
        self.parent = None
        self.children = []


class Skeleton:
    def __init__(self, title, limit, slots, roster):
        self.title = title
        self.limit = limit
        self.slots = slots
        self.roster = roster

    @property
    def units(self):
        """The top-level slots. One unit = one top-level slot and its subtree."""
        return [slot for slot in self.slots if slot.parent is None]

    def by_id(self, slot_id):
        for slot in self.slots:
            if slot.id == slot_id:
                return slot
        return None

    def subtree(self, unit):
        """`unit` and its descendants, in skeleton order."""
        out = []
        collecting = False
        for slot in self.slots:
            if slot is unit:
                collecting = True
            elif collecting and slot.parent is None:
                break
            if collecting:
                out.append(slot)
        return out

    def unit_of(self, slot):
        while slot.parent is not None:
            slot = slot.parent
        return slot


class Rung:
    def __init__(self, id, unit):
        self.id = id
        self.unit = unit
        self.establishes = None
        self.opens = []
        self.closes = []
        self.restates = []
        self.actual = None

    @property
    def originating(self):
        """A unit that opens a debt originates; one that only closes,
        restates or inventories does not."""
        return bool(self.opens)


class Spine:
    def __init__(self, claim, rungs):
        self.claim = claim
        self.rungs = rungs

    def rung_for(self, unit_id):
        for rung in self.rungs:
            if rung.unit == unit_id:
                return rung
        return None


def _sections(text):
    """Split a markdown file into `## <name>` sections."""
    out = {}
    name = None
    body = []
    for line in text.splitlines():
        if line.startswith("## "):
            if name is not None:
                out[name] = body
            name = line[3:].strip()
            body = []
        elif name is not None:
            body.append(line)
    if name is not None:
        out[name] = body
    return out


def _table(lines, where):
    """Parse a pipe table into a list of row-cell lists, header first."""
    rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(re.match(r"^:?-{2,}:?$", cell) for cell in cells):
            continue
        rows.append(cells)
    if not rows:
        raise ParseError("%s: no table rows" % where)
    return rows


def _expect_header(rows, expected, where):
    if [cell.lower() for cell in rows[0]] != expected:
        raise ParseError(
            "%s: table header is %s, expected %s"
            % (where, " | ".join(rows[0]), " | ".join(expected))
        )
    return rows[1:]


def parse_skeleton(path):
    if not path.exists():
        raise ParseError("%s: declared input is missing" % path.name)
    sections = _sections(path.read_text())
    for required in ("Document", "Slots"):
        if required not in sections:
            raise ParseError("%s: no `## %s` section" % (path.name, required))

    where = "%s `## Document`" % path.name
    fields = {}
    for cells in _expect_header(
        _table(sections["Document"], where), ["field", "value"], where
    ):
        if len(cells) != 2:
            raise ParseError("%s: row is not `| field | value |`" % where)
        if cells[0] in fields:
            raise ParseError("%s: duplicate field `%s`" % (where, cells[0]))
        fields[cells[0]] = cells[1]
    for key in fields:
        if key not in ("title", "limit"):
            raise ParseError("%s: unknown field `%s`" % (where, key))
    for key in ("title", "limit"):
        if key not in fields:
            raise ParseError("%s: no `%s` field" % (where, key))
    if not fields["limit"]:
        raise ParseError("%s: the `limit` field is empty" % where)
    # The `title` row is required and its value is not: a title is the central
    # claim compressed, so the skeleton ticket may leave the H1 to be filled
    # late. An unfilled title is a hole with the gate bit, never a parse error.

    where = "%s `## Slots`" % path.name
    slots = []
    seen = set()
    for cells in _expect_header(
        _table(sections["Slots"], where),
        ["slot", "level", "heading", "partitions-on"],
        where,
    ):
        if len(cells) != 4:
            raise ParseError(
                "%s: row is not `| slot | level | heading | partitions-on |`"
                % where
            )
        slot_id, level, heading, partitions_on = cells
        if not SLOT_ID.match(slot_id):
            raise ParseError(
                "%s: `%s` is not a slot id (lowercase, digits, hyphens)"
                % (where, slot_id)
            )
        if slot_id in seen:
            raise ParseError("%s: duplicate slot id `%s`" % (where, slot_id))
        seen.add(slot_id)
        if not level.isdigit():
            raise ParseError(
                "%s: slot `%s` has level `%s`, expected an integer"
                % (where, slot_id, level)
            )
        if not heading:
            raise ParseError("%s: slot `%s` has no heading text" % (where, slot_id))
        slots.append(Slot(slot_id, int(level), heading, partitions_on))

    if not slots:
        raise ParseError("%s: no slots" % where)
    if slots[0].level != 2:
        raise ParseError(
            "%s: first slot `%s` is level %d, expected 2 — the H1 is the "
            "document title, not a slot" % (where, slots[0].id, slots[0].level)
        )

    # Parentage is carried by level, the way a heading tree carries it.
    stack = []
    for slot in slots:
        if slot.level < 2:
            raise ParseError(
                "%s: slot `%s` is level %d, expected 2 or deeper"
                % (where, slot.id, slot.level)
            )
        while stack and stack[-1].level >= slot.level:
            stack.pop()
        if stack:
            if slot.level > stack[-1].level + 1:
                raise ParseError(
                    "%s: slot `%s` is level %d under a level %d slot — the tree "
                    "skips a level" % (where, slot.id, slot.level, stack[-1].level)
                )
            slot.parent = stack[-1]
            stack[-1].children.append(slot)
        elif slot.level != 2:
            raise ParseError(
                "%s: slot `%s` is level %d with no parent"
                % (where, slot.id, slot.level)
            )
        stack.append(slot)

    # Every child row names the object it partitions on, because a child slot
    # must partition by an object or a procedure and never by a claim.
    for slot in slots:
        if slot.parent is not None and not slot.partitions_on:
            raise ParseError(
                "%s: child slot `%s` has no `partitions-on`" % (where, slot.id)
            )
        if slot.parent is None and slot.partitions_on:
            raise ParseError(
                "%s: top-level slot `%s` carries `partitions-on`, which is a "
                "child-row field" % (where, slot.id)
            )

    roster = []
    if "Roster" in sections:
        body = "\n".join(sections["Roster"]).strip()
        if body:
            where = "%s `## Roster`" % path.name
            for cells in _expect_header(
                _table(sections["Roster"], where),
                ["kind", "name", "legend"],
                where,
            ):
                if len(cells) != 3:
                    raise ParseError(
                        "%s: row is not `| kind | name | legend |`" % where
                    )
                kind, name, legend = cells
                if kind not in ("figure", "table", "supplementary"):
                    raise ParseError(
                        "%s: `%s` is not a roster kind (figure, table, "
                        "supplementary)" % (where, kind)
                    )
                if not SLOT_ID.match(name):
                    raise ParseError(
                        "%s: `%s` is not a name (lowercase, digits, hyphens)"
                        % (where, name)
                    )
                roster.append((kind, name, legend))

    return Skeleton(fields["title"], fields["limit"], slots, roster)


def parse_spine(path):
    if not path.exists():
        raise ParseError("%s: declared input is missing" % path.name)
    sections = _sections(path.read_text())
    for required in ("Central claim", "Rungs"):
        if required not in sections:
            raise ParseError("%s: no `## %s` section" % (path.name, required))

    claim = "\n".join(sections["Central claim"]).strip()
    if not claim:
        raise ParseError("%s `## Central claim`: no claim" % path.name)

    rungs = []
    current = None
    for line in sections["Rungs"]:
        if line.startswith("### "):
            heading = RUNG_HEADING.match(line)
            if not heading:
                raise ParseError(
                    "%s `## Rungs`: `%s` is not `### R<n> — <unit>`" % (path.name, line.strip())
                )
            rung_id, unit = heading.group(1), heading.group(2)
            if not RUNG_ID.match(rung_id):
                raise ParseError("%s `## Rungs`: `%s` is not a rung id" % (path.name, rung_id))
            if rung_id != "R%d" % (len(rungs) + 1):
                raise ParseError(
                    "%s `## Rungs`: rung `%s` is out of order, expected `R%d` — rungs are "
                    "ordered" % (path.name, rung_id, len(rungs) + 1)
                )
            current = Rung(rung_id, unit)
            rungs.append(current)
            continue
        if not line.strip():
            continue
        if current is None:
            raise ParseError(
                "%s `## Rungs`: `%s` sits before the first rung" % (path.name, line.strip())
            )
        field = RUNG_FIELD.match(line)
        if not field:
            raise ParseError(
                "%s `## Rungs`: `%s` is not `- <relation>: <value>`" % (path.name, line.strip())
            )
        key, value = field.group(1), field.group(2)
        where = "%s `## Rungs` %s" % (path.name, current.id)
        if not value:
            raise ParseError("%s: `%s` has no value" % (where, key))
        if key == "establishes":
            if current.establishes is not None:
                raise ParseError("%s: two `establishes` lines" % where)
            current.establishes = value
        elif key == "opens":
            opens = OPENS_VALUE.match(value)
            if not opens:
                raise ParseError(
                    "%s: `opens` is not `D<n> (closed by R<n>) — <statement>`" % where
                )
            current.opens.append((opens.group(1), opens.group(2), opens.group(3)))
        elif key == "closes":
            if not DEBT_ID.match(value):
                raise ParseError("%s: `closes: %s` is not a debt id" % (where, value))
            current.closes.append(value)
        elif key == "restates":
            if not RUNG_ID.match(value):
                raise ParseError("%s: `restates: %s` is not a rung id" % (where, value))
            current.restates.append(value)
        elif key == "actual":
            if current.actual is not None:
                raise ParseError(
                    "%s: two `actual` lines — the drafted actual is overwritten, never appended"
                    % where
                )
            current.actual = value
        else:
            raise ParseError(
                "%s: unknown relation `%s` (establishes, opens, closes, restates, actual)"
                % (where, key)
            )

    if not rungs:
        raise ParseError("%s `## Rungs`: no rungs" % path.name)
    for rung in rungs:
        if rung.establishes is None:
            raise ParseError(
                "%s `## Rungs` %s: no `establishes` line" % (path.name, rung.id)
            )

    # One unit is one rung, 1:1. That is a fact about the two files together
    # rather than about this file's grammar, so it is a printed row in the
    # table and not a parse error: see `check_unit_rung_pairing`.
    return Spine(claim, rungs)


# --------------------------------------------------------------------------
# the source
# --------------------------------------------------------------------------


class Block:
    def __init__(self, slot_id, origin, line):
        self.slot_id = slot_id
        self.origin = origin
        self.line = line
        self.prose = ""
        # The same prose as the source still holds it, comments blanked rather
        # than closed up, and the line it starts on. A diagnostic reporting
        # `line 22` has to mean the author's line 22, so the text it scans
        # keeps every newline the source had.
        self.raw = ""
        self.raw_line = line
        self.raw_start = 0


def parse_source(paths):
    """Read the source and return the anchored blocks in the order they appear,
    plus any prose sitting outside every slot.

    One file post-promotion, or every section source pre-promotion — the blocks
    concatenate, and the render orders them by the skeleton rather than by the
    order they were read in.
    """
    blocks = []
    stray = []
    for path in paths:
        found, outside = _parse_one_source(path.read_text(), path)
        blocks.extend(found)
        stray.extend(outside)
    return blocks, stray


def _parse_one_source(text, path):
    """One source file: strip the author-facing comment channel, and split what
    is left at the anchors.

    Parsing is span-based, never line-anchored: a comment may wrap across any
    number of lines, and in the corpus this design was calibrated on, 13 of 30
    annotations did.
    """
    fenced = _fenced_spans(text)
    _refuse_unclosed_comment(text, path, fenced)
    _refuse_headings(text, path, fenced)

    masked = _mask_comments(text)
    blocks = []
    stray = []
    current = None
    pending = []
    cursor = 0

    for match in COMMENT.finditer(text):
        if _inside(fenced, match.start()):
            continue  # inside a fence it is literal text, not a comment
        pending.append(text[cursor : match.start()])
        cursor = match.end()
        slot_id = _anchor_slot_id(match, text, path)
        if slot_id is None:
            continue  # every comment is stripped, as a class
        _attribute(_tidy("".join(pending)), current, path, stray)
        _close_raw(current, masked, match.start())
        pending = []
        current = Block(slot_id, path, _line_of(text, match.start()))
        current.raw_line = _line_of(text, match.end())
        current.raw_start = match.end()
        blocks.append(current)

    pending.append(text[cursor:])
    _attribute(_tidy("".join(pending)), current, path, stray)
    _close_raw(current, masked, len(text))
    return blocks, stray


def _close_raw(block, masked, end):
    """A block's prose runs from its own anchor to the next one."""
    if block is not None:
        block.raw = masked[block.raw_start : end]


def _attribute(prose, block, path, stray):
    """Prose belongs to the anchor above it, or to no slot at all."""
    if block is not None:
        block.prose = prose
    elif prose:
        stray.append((path, prose))


def _anchor_slot_id(match, text, path):
    """The slot a comment anchors, or `None` if the comment is not an anchor.

    A comment whose first token is `slot:` in any case is **claiming** to be an
    anchor, and only the lowercase keyword followed by one slot id is one. So a
    near miss errors rather than vanishing silently under the comment strip.
    """
    content = match.group(1).strip()
    if not ANCHOR_INTENT.match(content):
        return None
    anchor = ANCHOR.match(content)
    if not anchor or not SLOT_ID.match(anchor.group(1)):
        raise ParseError(
            "%s:%d: malformed anchor `%s` — an anchor is `<!-- slot: <slot id> -->`, "
            "with `slot` in lowercase and one slot id after it"
            % (path.name, _line_of(text, match.start()), match.group(0).strip())
        )
    return anchor.group(1)


def _refuse_unclosed_comment(text, path, fenced):
    """Checked before anything else reads the text: an unclosed comment means
    every line after it is inside a comment, so nothing downstream can tell
    prose from annotation."""
    opened = [
        found.start()
        for found in re.finditer(r"<!--", text)
        if not _inside(fenced, found.start())
    ]
    closed = [
        found.start()
        for found in COMMENT.finditer(text)
        if not _inside(fenced, found.start())
    ]
    if len(opened) > len(closed):
        raise ParseError(
            "%s:%d: unclosed comment" % (path.name, _line_of(text, opened[len(closed)]))
        )


def _fenced_spans(text):
    """The character ranges inside fenced code blocks.

    Nothing is parsed inside one: not a comment, not an anchor, not a heading.
    A source showing anchor syntax in a fence is showing it, not using it.
    """
    spans = []
    opened_at = None
    for match in FENCE.finditer(text):
        if opened_at is None:
            opened_at = match.start()
        else:
            closing_line_end = text.find("\n", match.end())
            spans.append(
                (opened_at, len(text) if closing_line_end < 0 else closing_line_end + 1)
            )
            opened_at = None
    if opened_at is not None:
        spans.append((opened_at, len(text)))
    return spans


def _inside(spans, offset):
    return any(start <= offset < end for start, end in spans)


def _line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def _mask_comments(text):
    """Blank every comment's content, keeping the newlines, so a scan over the
    result still reports the source's own line numbers."""

    def blank(match):
        return "".join("\n" if char == "\n" else " " for char in match.group(0))

    return COMMENT.sub(blank, text)


def _refuse_headings(text, path, fenced):
    """The skeleton owns every heading at every level, and the render injects
    them on every pass. So a heading in a source is not a thing the source can
    express: it would render as a heading the skeleton never declared.

    Both markdown spellings count. The underlined form is the one an editor
    reaches for by hand, so leaving it out would leave the surface open.
    """
    masked = _mask_comments(text)
    offset = 0
    previous = ""
    for number, line in enumerate(masked.splitlines(), start=1):
        start = offset
        offset += len(line) + 1
        if _inside(fenced, start):
            previous = line
            continue
        underlined = SETEXT.match(line) and previous.strip() and not HEADING.match(previous)
        if HEADING.match(line) or underlined:
            shown = previous.strip() if underlined else line.strip()
            raise ParseError(
                "%s:%d: `%s` is a heading — a source carries anchors, never headings, "
                "and the skeleton owns every heading at every level"
                % (path.name, number, shown)
            )
        previous = line


def _tidy(prose):
    """Close the gaps a stripped comment leaves, and nothing else."""
    prose = re.sub(r"[ \t]+\n", "\n", prose)
    prose = re.sub(r"\n{3,}", "\n\n", prose)
    return prose.strip()


def source_paths(source):
    """One file, or every `*.md` in a directory — pre-promotion the sections are
    still separate files, and concatenation is this unit's duty."""
    if source.is_dir():
        paths = sorted(source.glob("*.md"))
        if not paths:
            raise HardError("%s: no `*.md` source files" % source)
        return paths
    if not source.exists():
        raise HardError("%s: no such source" % source)
    return [source]


def find_paper_root(source, override):
    if override is not None:
        return override
    start = source if source.is_dir() else source.parent
    for candidate in [start] + list(start.resolve().parents):
        if (candidate / "skeleton.md").exists():
            return candidate
    return start


# --------------------------------------------------------------------------
# the prose the diagnostics measure
# --------------------------------------------------------------------------
#
# Every number in the reported tier is measured over the same text, and the
# scope is stated rather than assumed: annotations, citation groups, tables,
# fenced blocks and comments are out, and headings never arrive in the first
# place because the skeleton owns them and the render injects them.
#
# Blanking, not deleting: every excluded span is replaced by spaces and its
# newlines are kept, so a count still reports the author's own line numbers.


def scope_prose(raw):
    """The prose a diagnostic may read, with everything else blanked out."""
    scoped = _blank(raw, _fenced_spans(raw))
    for pattern in (TABLE_ROW, BRACKET_SPAN, BRACE_SPAN):
        scoped = pattern.sub(_spaces, scoped)
    return scoped


def _blank(text, spans):
    for start, end in reversed(spans):
        text = text[:start] + _blanked(text[start:end]) + text[end:]
    return text


def _spaces(match):
    return _blanked(match.group(0))


def _blanked(text):
    return "".join("\n" if char == "\n" else " " for char in text)


def in_scope(paper):
    """Every in-scope block, paired with the prose a diagnostic may read."""
    scope = set(slot.id for slot in paper.slots)
    return [
        (block, scope_prose(block.raw))
        for block in paper.blocks
        if block.slot_id in scope
    ]


def paragraphs(scoped, first_line):
    """The blank-line-separated paragraphs of one block, each with its line."""
    found = []
    lines = []
    start = None
    for offset, line in enumerate(scoped.splitlines()):
        if line.strip():
            if start is None:
                start = first_line + offset
            lines.append(line)
        elif lines:
            found.append(("\n".join(lines), start))
            lines, start = [], None
    if lines:
        found.append(("\n".join(lines), start))
    return found


def sentences(text):
    """The sentences of one paragraph.

    A trailing fragment with no terminator is a sentence: a paragraph ending in
    a colon is still text a reader reads, and dropping it would understate
    every number measured over it.
    """
    found = []
    start = 0
    for match in SENTENCE_END.finditer(text):
        head = text[start : match.end()]
        if ABBREVIATION.search(head.rstrip()):
            continue
        if head.strip():
            found.append(head.strip())
        start = match.end()
    tail = text[start:].strip()
    if tail:
        found.append(tail)
    return found


def sentences_in_scope(paper):
    """Every sentence in scope, in source order."""
    found = []
    for block, scoped in in_scope(paper):
        for text, _ in paragraphs(scoped, block.raw_line):
            found.extend(sentences(text))
    return found


def words(sentence):
    return WORD.findall(sentence)


def _locations(spots):
    """`(file, line)` pairs as the report prints them.

    Bare line numbers over one source file, and file-qualified over several —
    pre-promotion the sections are still separate files, where a bare `line 3`
    could mean any of them.
    """
    if not spots:
        return ""
    names = set(name for name, _ in spots)
    if len(names) == 1:
        lines = ", ".join(str(line) for _, line in spots)
        return " (%s %s)" % ("line" if len(spots) == 1 else "lines", lines)
    return " (%s)" % ", ".join("%s:%d" % spot for spot in spots)


def _plural(count, noun):
    return "%d %s%s" % (count, noun, "" if count == 1 else "s")


# --------------------------------------------------------------------------
# the check registry
# --------------------------------------------------------------------------


class Verdict:
    """One row's outcome: which of the three verdicts, and what failed."""

    def __init__(self, kind, problems=()):
        self.kind = kind
        self.problems = list(problems)

    @classmethod
    def over(cls, problems):
        return cls(FAIL if problems else PASS, problems)

    @classmethod
    def skipped(cls):
        return cls(SKIPPED)

    def render(self):
        if self.kind != FAIL:
            return self.kind
        return "%s — %d (%s)" % (FAIL, len(self.problems), "; ".join(self.problems))


class Count(Verdict):
    """A count measured against a threshold.

    The count and its locations print on both sides of the threshold, because
    the gate always runs and always reports its number: raising the bar makes
    the bar visible, never the count invisible.
    """

    def __init__(self, count, threshold, spots):
        Verdict.__init__(self, FAIL if count > threshold else PASS)
        self.count = count
        self.spots = list(spots)

    def render(self):
        return "%s — %d%s" % (self.kind, self.count, _locations(self.spots))


class Number(Verdict):
    """A measurement, printed with no verdict word at all.

    A threshold here would be a floor on a rhetorical move, and the cheapest
    way to clear such a floor is to sprinkle `however` over paragraphs that
    concede nothing. So these rows carry numbers, and the reader does the
    reading.
    """

    def __init__(self, text):
        Verdict.__init__(self, NUMBER)
        self.text = text

    def render(self):
        return self.text


def check_slot_integrity(paper):
    """An anchor names a slot the skeleton carries, no slot is anchored twice,
    and no prose sits outside every slot.

    A broken tree is damage, and circulating damage is how it spreads, so this
    is a hard error rather than a gate. Whole-document only: whether a slot is
    anchored twice, or anchored nowhere, is a fact about the whole document.
    """
    problems = ["prose outside every slot in %s" % path.name for path, _ in paper.stray]
    seen = {}
    for block in paper.blocks:
        if paper.skeleton.by_id(block.slot_id) is None:
            problems.append(
                "%s:%d anchors `%s`, absent from the skeleton"
                % (block.origin.name, block.line, block.slot_id)
            )
        elif block.slot_id in seen:
            first = seen[block.slot_id]
            problems.append(
                "`%s` anchored twice, at %s:%d and %s:%d"
                % (
                    block.slot_id,
                    first.origin.name,
                    first.line,
                    block.origin.name,
                    block.line,
                )
            )
        else:
            seen[block.slot_id] = block
    return Verdict.over(problems)


def check_unit_rung_pairing(paper):
    """One unit is one rung, 1:1.

    A rung spanning two units is illegal — the ladder decomposes instead, and
    the second unit takes a non-originating rung. Read from both files, so it
    is reported rather than raised: the render still runs, and the document it
    would emit is not the document the ladder describes.
    """
    problems = []
    paired = set()
    for rung in paper.spine.rungs:
        slot = paper.skeleton.by_id(rung.unit)
        if slot is None or slot.parent is not None:
            problems.append("%s names `%s`, which is not a unit" % (rung.id, rung.unit))
        elif rung.unit in paired:
            problems.append("`%s` carries two rungs" % rung.unit)
        else:
            paired.add(rung.unit)
    for unit in paper.units:
        if unit.id not in paired:
            problems.append("`%s` carries no rung" % unit.id)
    return Verdict.over(problems)


def check_originating_slot_children(paper):
    """An originating unit has zero children.

    A unit that opens a debt must carry its argument in prose motion; a stack
    of labelled boxes is what a reader meets instead of an argument. Read from
    both files, so it fires the moment the ladder exists.
    """
    problems = []
    for unit in paper.units:
        rung = paper.spine.rung_for(unit.id)
        if rung is not None and rung.originating and unit.children:
            problems.append(
                "`%s` opens a debt and carries %d children"
                % (unit.id, len(unit.children))
            )
    return Verdict.over(problems)


def check_unfilled_skeleton_slot(paper):
    """An unfilled slot is a hole with the gate bit set, so the skeleton's own
    slot list is the completion checklist.

    A parent slot's prose is whatever precedes its first child anchor, and it is
    permitted rather than owed — a unit that spends its children on an opening
    paragraph is exactly the stack of labelled blocks this design refuses. So
    only a leaf owes prose, and a parent is finished when its children are.
    """
    problems = ["`%s`" % slot.id for slot in paper.slots if _owes_prose(paper, slot)]
    if paper.granularity == DOCUMENT and not paper.skeleton.title:
        problems.append("the document title")
    return Verdict.over(problems)


def _owes_prose(paper, slot):
    return not slot.children and not paper.prose_for(slot)


def em_dash_row(paper):
    """The row name carries the threshold, so the number is read against the
    bar that was actually in force."""
    return "em dashes (threshold %d)" % paper.em_dash_threshold


def check_em_dashes(paper):
    """Count the em dashes in body prose, against the caller's threshold.

    An em dash marks a logical relation without naming it, and the ban failed
    98 times as a bullet a drafting session self-attested to. It is exactly as
    countable as a figure reference, so it is counted.

    Reported here, and a blocking gate at the drafting seam: one
    implementation, invoked twice. What it never does is move the exit code —
    gating submission is reserved to the annotation gate bit.
    """
    spots = []
    for block, scoped in in_scope(paper):
        for offset, char in enumerate(scoped):
            if char == EM_DASH:
                spots.append(
                    (block.origin.name, block.raw_line + scoped.count("\n", 0, offset))
                )
    return Count(len(spots), paper.em_dash_threshold, spots)


def check_single_sentence_paragraphs(paper):
    """Single-sentence body paragraphs, in originating units only.

    Suspended everywhere else: a unit that only closes or restates a debt is
    not a unit of argument, and a panel caption is not one either, so the
    single-sentence signature does not transfer. Run it on a legend and it
    fires forever.
    """
    originating = [unit for unit in paper.units if _originates(paper, unit)]
    spots = []
    for block, scoped in in_scope(paper):
        slot = paper.skeleton.by_id(block.slot_id)
        if slot is None or paper.skeleton.unit_of(slot) not in originating:
            continue
        for text, line in paragraphs(scoped, block.raw_line):
            if len(sentences(text)) == 1:
                spots.append((block.origin.name, line))
    return Number(
        "%d in %s%s"
        % (len(spots), _plural(len(originating), "originating unit"), _locations(spots))
    )


def _originates(paper, unit):
    rung = paper.spine.rung_for(unit.id)
    return rung is not None and rung.originating


def check_adversative_ratio(paper):
    """The share of sentences that mark a turn.

    Read as a consequence, never as a target: the number moves because the
    em-dash gate forces relation-first rewriting. A low ratio beside a ladder
    full of closed debts is the finding; a low ratio alone is not, and a
    genuinely procedural Methods section concedes nothing, correctly.
    """
    found = sentences_in_scope(paper)
    if not found:
        return Number("0 of 0 sentences")
    turning = [one for one in found if ADVERSATIVE.search(one)]
    return Number(
        "%d of %s (%d%%)"
        % (
            len(turning),
            _plural(len(found), "sentence"),
            round(100.0 * len(turning) / len(found)),
        )
    )


def check_subject_openings(paper):
    """How the sentences in scope begin, most frequent first.

    A distribution rather than a cap: a ceiling on `We`-initial sentences has
    the adversative floor's problem in reverse, and the measured drafting rate
    was 6%. The opening word is what the audit measured, so it is what this
    reports.
    """
    found = sentences_in_scope(paper)
    if not found:
        return Number("0 sentences")
    tally = {}
    for one in found:
        opening = words(one)
        if opening:
            tally[opening[0]] = tally.get(opening[0], 0) + 1
    ranked = sorted(tally.items(), key=lambda pair: (-pair[1], pair[0]))
    shown = ["%s %d" % pair for pair in ranked[:OPENINGS_SHOWN]]
    if len(ranked) > OPENINGS_SHOWN:
        shown.append("+%d more" % (len(ranked) - OPENINGS_SHOWN))
    return Number(
        "%s (of %s)" % (", ".join(shown), _plural(len(found), "sentence"))
    )


def check_sentence_length(paper):
    """Mean, coefficient of variation, and the share over 35 words.

    Three numbers rather than a cap, because a cap is an unconditional
    transform over finished prose and what it removes is subordination. These
    are the numbers that would have caught a flat rhythm at the time.
    """
    found = sentences_in_scope(paper)
    if not found:
        return Number("0 sentences")
    lengths = [len(words(one)) for one in found]
    mean = sum(lengths) / float(len(lengths))
    variance = sum((length - mean) ** 2 for length in lengths) / float(len(lengths))
    long_ones = [length for length in lengths if length > LONG_SENTENCE]
    return Number(
        "mean %.1f, CV %.2f, %d%% over %d words (%s)"
        % (
            mean,
            (variance ** 0.5) / mean if mean else 0.0,
            round(100.0 * len(long_ones) / len(lengths)),
            LONG_SENTENCE,
            _plural(len(found), "sentence"),
        )
    )


# Row order is this registry's order, and it is fixed: `review-paper` reports
# the table verbatim, so the order is an interface. Rows arrive as the checks
# behind them are built; a row is never printed without a check behind it,
# because a row with nothing behind it reads as a pass.
#
# The registry's declared order, with the rows not yet built named in place:
#
#   parse    skeleton / spine grammar    (built)
#   parse    source grammar              (built)
#   parse    brace grammar               annotation channel
#   parse    citation group              citations
#   parse    reference literals          figures and panels
#   hard     slot integrity              (built; becomes slot / roster
#                                        integrity when figures land the
#                                        roster half of it)
#   hard     citation → bib entry        citations
#   hard     unit / rung pairing         (built)
#   hard     originating slot children   (built)
#   gating   annotations (gating)        annotation channel
#   gating   unfilled skeleton slot      (built)
#   gating   bare holes                  residue lints
#   gating   workflow phrases            residue lints
#   gating   chain bookkeeping           chain walk
#   reported em dashes                   (built)
#   reported brief-to-prose overlap      overlap instrument
#   reported single-sentence body …      (built; paragraph order joins it with
#                                        the overlap instrument)
#   reported adversative ratio           (built)
#   reported subject openings            (built)
#   reported sentence length             (built)
#   reported K8 locality test            chain walk
#   reported supersession diff           supersession diff
#
# The two parse-tier rows built here have no entry below: a parse error means
# nothing ran, so the table is absent rather than carrying their verdicts.
#
# A row name may be a function of the paper, for a row whose name carries the
# threshold the number was measured against.
REGISTRY = [
    ("slot integrity", HARD, DOCUMENT, check_slot_integrity),
    ("unit / rung pairing", HARD, None, check_unit_rung_pairing),
    ("originating slot children", HARD, None, check_originating_slot_children),
    ("unfilled skeleton slot", GATING, None, check_unfilled_skeleton_slot),
    (em_dash_row, REPORTED, None, check_em_dashes),
    (
        "single-sentence body paragraphs",
        REPORTED,
        None,
        check_single_sentence_paragraphs,
    ),
    ("adversative ratio", REPORTED, DOCUMENT, check_adversative_ratio),
    ("subject openings", REPORTED, DOCUMENT, check_subject_openings),
    ("sentence length", REPORTED, DOCUMENT, check_sentence_length),
]

# The three Tier 4 diagnostics are whole-document only, and the em-dash count
# is not: the count blocks a drafting seam, and a seam is one section. The
# three are reported together over the finished piece, because a rhythm number
# published per seam is a number a drafter tunes at the seam — which is the
# behaviour `no threshold` exists to prevent.

# The parse-tier rows print `PASS` whenever a table prints at all, because a
# parse-tier failure suppresses the table.
PARSE_ROWS = ["skeleton / spine grammar", "source grammar"]


# --------------------------------------------------------------------------
# the render
# --------------------------------------------------------------------------


class Paper:
    """One paper at one granularity: the two files, the source, and the slots
    in scope."""

    def __init__(
        self, skeleton, spine, blocks, stray, granularity, unit, em_dash_threshold
    ):
        self.skeleton = skeleton
        self.spine = spine
        self.blocks = blocks
        self.stray = stray
        self.granularity = granularity
        self.unit = unit
        self.em_dash_threshold = em_dash_threshold
        self.slots = skeleton.subtree(unit) if unit is not None else skeleton.slots
        self.units = [unit] if unit is not None else skeleton.units
        self._prose = {}
        for block in blocks:
            if block.slot_id in self._prose:
                # Two anchors claiming one slot is a hard error, and at whole
                # document granularity nothing is emitted. Keep both blocks'
                # prose regardless: dropping one would lose text from a section
                # render, where that check is out of scope and so cannot say so.
                self._prose[block.slot_id] += "\n\n" + block.prose
            else:
                self._prose[block.slot_id] = block.prose

    def prose_for(self, slot):
        return self._prose.get(slot.id, "")


def derive_unit(skeleton, blocks, named):
    """`--section <unit>`, or `--section` alone over a source that anchors
    exactly one unit."""
    if named:
        unit = skeleton.by_id(named)
        if unit is None:
            raise HardError("`%s` is not a slot in the skeleton" % named)
        if unit.parent is not None:
            raise HardError(
                "`%s` is a child slot; a unit is one top-level slot and its subtree"
                % named
            )
        return unit
    anchored = []
    for block in blocks:
        slot = skeleton.by_id(block.slot_id)
        if slot is None:
            continue
        unit = skeleton.unit_of(slot)
        if unit not in anchored:
            anchored.append(unit)
    if len(anchored) != 1:
        raise HardError(
            "the source anchors %d units, so `--section` cannot tell which one is "
            "meant — name it as `--section <unit>`" % len(anchored)
        )
    return anchored[0]


def render_document(paper):
    """Inject every heading from the skeleton, at its level, with its exact
    text, on every pass.

    A gap is never silently stripped: an unfilled slot and an unfilled title
    both come out as a conspicuous, uniform, greppable token, because dropping
    one would turn a flagged gap into an unsupported claim the author never
    learns about.
    """
    out = [BANNER]
    if paper.granularity == DOCUMENT:
        out.append("\n# %s\n" % (paper.skeleton.title or _hole("the document title")))
    for slot in paper.slots:
        out.append("\n%s %s\n" % ("#" * slot.level, slot.heading))
        prose = paper.prose_for(slot)
        if not prose and not slot.children:
            prose = _hole("prose for %s" % slot.id)
        if prose:
            out.append("\n%s\n" % prose)
    return "".join(out)


def _hole(label):
    return "⟦HOLE: %s⟧" % label


def format_report(rows, granularity):
    """The table `review-paper` reports verbatim, so its shape is an interface."""
    lines = []
    counts = {PASS: 0, FAIL: 0, SKIPPED: 0, NUMBER: 0}
    for name, verdict in rows:
        lines.append("%s%s %s" % (INDENT, name.ljust(NAME_WIDTH - 1), verdict.render()))
        counts[verdict.kind] += 1
    lines.append("")
    tally = "%s%d pass, %d fail, %d out of scope" % (
        INDENT,
        counts[PASS],
        counts[FAIL],
        counts[SKIPPED],
    )
    if counts[NUMBER]:
        # Counted apart from the verdicts, because a number is not one.
        tally += ", %d reported" % counts[NUMBER]
    lines.append(tally)
    lines.append(
        "%s→ NOT a claim that this %s is finished"
        % (INDENT, SECTION if granularity == SECTION else DOCUMENT)
    )
    return "\n".join(lines) + "\n"


def run_gate(paper):
    """Every row in registry order, and the failed rows by tier.

    A reported row's failure is collected like any other and read by nobody:
    only the hard and gating buckets reach the exit code.
    """
    rows = [(name, Verdict(PASS)) for name in PARSE_ROWS]
    failed = {HARD: [], GATING: [], REPORTED: []}
    for name, tier, scope, check in REGISTRY:
        label = name(paper) if callable(name) else name
        verdict = (
            Verdict.skipped()
            if scope == DOCUMENT and paper.granularity == SECTION
            else check(paper)
        )
        rows.append((label, verdict))
        if verdict.kind == FAIL:
            failed[tier].append((label, verdict))
    return rows, failed


# --------------------------------------------------------------------------
# the CLI
# --------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="render-paper",
        description="Build the document from the skeleton, and run the gate.",
    )
    parser.add_argument("source", help="the source file, or a directory of section sources")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--circulate",
        action="store_true",
        help="emit a circulatable document: every gap a conspicuous token",
    )
    mode.add_argument(
        "--submit",
        action="store_true",
        help="emit a submittable document; refuse while any gating check fails",
    )
    mode.add_argument(
        "--check", action="store_true", help="run the gate only; emit no document"
    )
    mode.add_argument(
        "--scaffold",
        action="store_true",
        help="pre-seed a unit's source with every anchor in its subtree",
    )
    parser.add_argument(
        "--section",
        nargs="?",
        const="",
        default=None,
        metavar="UNIT",
        help="section granularity: one unit and its subtree",
    )
    parser.add_argument(
        "--paper",
        default=None,
        metavar="DIR",
        help="the paper root; defaults to the nearest ancestor holding skeleton.md",
    )
    parser.add_argument(
        "--em-dash-threshold",
        type=threshold,
        default=EM_DASH_DEFAULT,
        metavar="N",
        help="how many em dashes the prose may carry; the caller's `## Style` "
        "supplies it, and the skill default is %d" % EM_DASH_DEFAULT,
    )
    return parser


def threshold(value):
    """A threshold is a finite non-negative integer.

    There is no `off`, no `none` and no infinity. An effort may raise the bar
    as far as it likes, visibly, and cannot remove the gate: the gate always
    runs and always reports its count.
    """
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "`%s` is not a finite non-negative integer — a threshold has no "
            "`off`, no `none` and no infinity" % value
        )
    if number < 0:
        raise argparse.ArgumentTypeError(
            "`%s` is not a finite non-negative integer" % value
        )
    return number


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.scaffold:
        sys.stderr.write(
            "render-paper: --scaffold is not built yet; a unit's anchors must be "
            "seeded by hand until it is\n"
        )
        return EXIT_HARD

    source = Path(args.source)
    granularity = SECTION if args.section is not None else DOCUMENT

    try:
        root = find_paper_root(source, Path(args.paper) if args.paper else None)
        paths = source_paths(source)
        skeleton = parse_skeleton(root / "skeleton.md")
        spine = parse_spine(root / "spine.md")
        blocks, stray = parse_source(paths)
        unit = None
        if granularity == SECTION:
            unit = derive_unit(skeleton, blocks, args.section)
    except ParseError as error:
        sys.stderr.write("render-paper: parse error — %s\n" % error)
        return EXIT_PARSE
    except HardError as error:
        sys.stderr.write("render-paper: %s\n" % error)
        return EXIT_HARD

    paper = Paper(
        skeleton, spine, blocks, stray, granularity, unit, args.em_dash_threshold
    )
    rows, failed = run_gate(paper)
    report = format_report(rows, granularity)

    if failed[HARD]:
        sys.stderr.write(report)
        return EXIT_HARD
    if failed[GATING] and args.submit:
        sys.stderr.write(report)
        sys.stderr.write(
            "\n%s--submit refused: %d gating check%s failed\n"
            % (INDENT, len(failed[GATING]), "" if len(failed[GATING]) == 1 else "s")
        )
        for name, verdict in failed[GATING]:
            sys.stderr.write(
                "%s%s%s: %s\n" % (INDENT, INDENT, name, "; ".join(verdict.problems))
            )
        return EXIT_GATING

    if not args.check:
        sys.stdout.write(render_document(paper))
    sys.stderr.write(report)
    return EXIT_GATING if failed[GATING] else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
