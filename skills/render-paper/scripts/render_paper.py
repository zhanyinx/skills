#!/usr/bin/env python3
"""render-paper — build the document from the skeleton, and run the gate.

Python 3, standard library only. No third-party import at runtime.

The document is written to stdout; the verdict table and every diagnostic go to
stderr. `--check` writes no document at all, and `--scaffold` writes no document
either: it seeds the source in place with the anchors the skeleton declares.

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
# parse iff the source cannot express the thing at all; reported iff it is a
# prose fact, which is decidable but carries no consequence — a threshold on
# one is exactly what this design refuses, so a reported row cannot fail and
# never reaches the exit code.
HARD = "hard"
GATING = "gating"
REPORTED = "reported"

# The three verdicts, and nothing else. No single-word verdict is emitted
# anywhere: one word cannot carry checked-and-fine against never-looked.
PASS = "PASS"
FAIL = "FAIL"
SKIPPED = "SKIPPED — OUT OF SCOPE AT THIS GRANULARITY"

DOCUMENT = "document"
SECTION = "section"

NAME_WIDTH = 26
INDENT = "  "

SLOT_ID = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
COMMENT = re.compile(r"<!--(.*?)-->", re.DOTALL)
ANCHOR_INTENT = re.compile(r"^slot\s*:", re.IGNORECASE)
ANCHOR = re.compile(r"^slot\s*:\s*(\S+)\s*$")
ANCHOR_FORM = "<!-- slot: %s -->"
HEADING = re.compile(r"^ {0,3}#{1,6}(\s|$)")
SETEXT = re.compile(r"^ {0,3}(=+|-+)\s*$")
FENCE = re.compile(r"^ {0,3}(?:```|~~~)", re.MULTILINE)
RUNG_HEADING = re.compile(r"^###\s+(\S+)\s+—\s+(.+?)\s*$")
RUNG_FIELD = re.compile(r"^-\s+([a-z-]+)\s*:\s*(.*?)\s*$")
OPENS_VALUE = re.compile(r"^(D\d+)\s+\(closed by (R\d+)\)\s+—\s+(\S.*)$")
DEBT_ID = re.compile(r"^D\d+$")
RUNG_ID = re.compile(r"^R\d+$")

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


def scan_source(text, path):
    """Every comment in a source, in order, each paired with the slot it
    anchors — or with `None` when it is an ordinary comment.

    Both readers of a source walk this one scan: the render's parser, which
    strips the channel, and the scaffold's split, which keeps it. A grammar
    with two implementations is a grammar that can disagree with itself.

    Parsing is span-based, never line-anchored: a comment may wrap across any
    number of lines, and in the corpus this design was calibrated on, 13 of 30
    annotations did.
    """
    fenced = _fenced_spans(text)
    _refuse_unclosed_comment(text, path, fenced)
    _refuse_headings(text, path, fenced)
    return [
        (match, _anchor_slot_id(match, text, path))
        for match in COMMENT.finditer(text)
        # inside a fence it is literal text, not a comment
        if not _inside(fenced, match.start())
    ]


def _parse_one_source(text, path):
    """One source file: strip the author-facing comment channel, and split what
    is left at the anchors."""
    blocks = []
    stray = []
    current = None
    pending = []
    cursor = 0

    for match, slot_id in scan_source(text, path):
        pending.append(text[cursor : match.start()])
        cursor = match.end()
        if slot_id is None:
            continue  # every comment is stripped, as a class
        _attribute(_tidy("".join(pending)), current, path, stray)
        pending = []
        current = Block(slot_id, path, _line_of(text, match.start()))
        blocks.append(current)

    pending.append(text[cursor:])
    _attribute(_tidy("".join(pending)), current, path, stray)
    return blocks, stray


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


def slot_integrity_problems(skeleton, anchored, stray):
    """The three ways a source's anchors misdescribe the document: an anchor
    naming a slot the skeleton does not carry, one slot anchored twice, and
    prose sitting outside every slot.

    One predicate, two consequences — the gate reports it as a row, and the
    scaffold refuses to rewrite a source it would have to guess about. Two
    implementations of it could disagree about the same three facts.
    """
    problems = ["prose outside every slot in %s" % path.name for path, _ in stray]
    seen = {}
    for block in anchored:
        if skeleton.by_id(block.slot_id) is None:
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
    return problems


def derive_unit(skeleton, anchored, named):
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
    units = []
    for block in anchored:
        slot = skeleton.by_id(block.slot_id)
        if slot is None:
            continue
        unit = skeleton.unit_of(slot)
        if unit not in units:
            units.append(unit)
    if len(units) != 1:
        raise HardError(
            "the source anchors %d units, so `--section` cannot tell which one is "
            "meant — name it as `--section <unit>`" % len(units)
        )
    return units[0]


# --------------------------------------------------------------------------
# the scaffold
# --------------------------------------------------------------------------


class Region:
    """One anchor in a source, and every byte between it and the next one.

    A `Block` is the same anchor after the render's parser has stripped the
    comment channel out of it. Two types, because the two texts are not the
    same text: one is what renders, the other is what was typed.
    """

    def __init__(self, slot_id, origin, line, text):
        self.slot_id = slot_id
        self.origin = origin
        self.line = line
        self.text = text


def split_at_anchors(text, path):
    """The source split at its anchors, keeping what lies between them
    verbatim, plus the lead — the text before the first anchor, which belongs
    to no slot.

    The render's parser strips the comment channel, which is the one thing a
    mode that rewrites the source must not do: an author's notes are the
    source's own content. So the scaffold reads the same anchors through the
    same scan, and keeps everything else exactly as it was typed.
    """
    anchors = [
        (slot_id, match.start(), match.end())
        for match, slot_id in scan_source(text, path)
        if slot_id is not None
    ]
    lead = text[: anchors[0][1]] if anchors else text
    regions = []
    for index, (slot_id, start, end) in enumerate(anchors):
        stop = anchors[index + 1][1] if index + 1 < len(anchors) else len(text)
        regions.append(Region(slot_id, path, _line_of(text, start), text[end:stop]))
    return lead, regions


def scaffold(source, skeleton, named_unit):
    """Seed a unit's source with every anchor in its subtree, in skeleton order.

    A misordered, duplicated or omitted anchor becomes something a drafting
    session cannot type, rather than something a rule forbids. Headings are
    never written: injecting them is the render's job on every pass, and a
    heading in a source is a parse error.

    Idempotent by construction — the seeded form is exactly what the split
    reads back, so a second run rebuilds the bytes the first one wrote, and a
    skeleton amendment can be re-seeded safely.
    """
    if source.is_dir():
        raise HardError(
            "%s is a directory; --scaffold seeds one source file, because one "
            "source is what carries one unit's anchors" % source
        )
    try:
        text = source.read_text() if source.exists() else ""
    except OSError as error:
        raise HardError("%s: cannot be read — %s" % (source, error.strerror))
    lead, regions = split_at_anchors(text, source)

    # Wherever the scaffold would have to guess, it refuses instead: it
    # rewrites the file, and a guess would move or merge prose the author never
    # asked it to touch. These are the gate's own three facts, read by the gate's
    # own predicate, so the scaffold cannot refuse what the gate would pass.
    lead_prose = _tidy(_mask_comments(lead))
    problems = slot_integrity_problems(
        skeleton, regions, [(source, lead_prose)] if lead_prose else []
    )
    if problems:
        raise HardError(
            "%s — the scaffold rewrites the source, so it refuses rather than "
            "guess" % "; ".join(problems)
        )

    # The scaffold is always one unit: that is what a drafting session opens,
    # and seeding a slot whose prose lives in another unit's file is how a
    # source acquires an anchor the next render calls a duplicate. Naming the
    # unit is `--section`'s job; an already-anchored source names its own.
    unit = derive_unit(skeleton, regions, named_unit)
    prose = {region.slot_id: region.text.strip() for region in regions}
    subtree = {slot.id for slot in skeleton.subtree(unit)}
    # A slot already anchored is kept even when it sits outside the subtree.
    # Post-promotion the source is one file holding every unit, so dropping
    # them would delete another unit's prose to seed this one's.
    wanted = [slot for slot in skeleton.slots if slot.id in subtree or slot.id in prose]

    parts = [lead.strip()] if lead.strip() else []
    for slot in wanted:
        parts.append(ANCHOR_FORM % slot.id)
        if prose.get(slot.id):
            parts.append(prose[slot.id])
    seeded = "\n\n".join(parts) + "\n"

    if seeded == text:
        sys.stderr.write(
            "render-paper: %s already carries every anchor in `%s`, in skeleton "
            "order — unchanged\n" % (source, unit.id)
        )
        return EXIT_OK
    try:
        source.write_text(seeded)
    except OSError as error:
        raise HardError("%s: cannot be written — %s" % (source, error.strerror))
    added = [slot.id for slot in wanted if slot.id not in prose]
    sys.stderr.write(
        "render-paper: seeded %s with `%s` — %d anchor%s in skeleton order%s\n"
        % (
            source,
            unit.id,
            len(wanted),
            "" if len(wanted) == 1 else "s",
            (", %d added (%s)" % (len(added), ", ".join("`%s`" % one for one in added)))
            if added
            else "",
        )
    )
    return EXIT_OK


# --------------------------------------------------------------------------
# the brief — read here, owned elsewhere
# --------------------------------------------------------------------------
#
# `briefs/<unit>.md` is a declared input, one per unit, beside the source. This
# is the brief's only *parser*, but not its format's owner: the drafting skill
# ships the two templates, and what this file fixes is the six zone headings it
# parses and nothing else. So the parse surface stays a list of headings, and a
# template change that renames a zone shows up here as an unparsed zone rather
# than as silence.
#
# Exactly two zones are reader-facing, and they are the only zones whose content
# may legitimately appear in the prose. Every other zone is instruction by
# virtue of where it sits — positional separation, no marker strings.

ARGUMENT = "Argument"
INVENTORY = "Inventory"
READER_FACING_ZONES = (ARGUMENT, INVENTORY)
BRIEF_ZONES = READER_FACING_ZONES + (
    "Must not claim",
    "Sheds",
    "Verify before prose",
    "Sources",
)

# The ladder line is bookkeeping, not a proposition: it names the unit's
# relation to the rung above it, and a drafter copying it into the prose is
# copying a relation, not lifting a claim.
RELATION_LINE = re.compile(r"^(rung|closes|opens|restates)\s*:", re.IGNORECASE)

# A word, keeping what a term keeps: internal hyphens, dots, slashes and the
# comparison operators a version constraint carries, so `tile-boundary`,
# `ghcr.io/org/tool` and `≥ 25.04.0` survive tokenisation as themselves.
TOKEN = re.compile(r"[a-z0-9][a-z0-9'’./+≥<>=-]*")
TRAILING = "'’./-"
CLOSING = ",;:.!?)]\"”"
SENTENCE_END = re.compile(r"(?<=[.!?])[\"”)]?\s+")
ABBREVIATION = re.compile(r"(^|\s)(e\.g|i\.e|cf|vs|fig|eq|al|ca|approx|ref)\.$", re.I)

# A shared run this long is a phrase somebody moved, not a coincidence of
# grammar. The corpus's own shortest transcribed span — *illumination
# correction suppresses tile-boundary seams* — is five words, and its expected
# spans (`MIT`, `scale bar required`, `tile-boundary crop, before/after BaSiC`)
# are all shorter, so the floor separates them before either instrument runs.
SUBSTANTIAL = 5

# Function words carry no phrasing, so a run made of nothing else is grammar
# rather than transcription. Two content words is the smallest run that could
# have been lifted.
FUNCTION_WORDS = {
    "a", "an", "and", "any", "are", "as", "at", "be", "been", "being", "both",
    "but", "by", "can", "could", "did", "do", "does", "each", "either", "every",
    "for", "from", "had", "has", "have", "her", "his", "how", "in", "into",
    "is", "it", "its", "may", "might", "must", "no", "nor", "not", "of", "on",
    "one", "only", "or", "our", "over", "per", "shall", "should", "so", "some",
    "such", "than", "that", "the", "their", "them", "then", "there", "these",
    "they", "this", "those", "through", "to", "under", "up", "was", "we",
    "were", "what", "when", "where", "which", "while", "who", "will", "with",
    "would", "you", "your",
}

# The finite forms a finite verb can take without ambiguity. Every one of them
# is a closed-class word, so the list is complete rather than a sample, and it
# needs no extension per paper — which it must not have, since paper-specific
# text in the renderer is what this unit is forbidden to hold.
FINITE_FORMS = {
    "is", "are", "was", "were", "am", "has", "have", "had", "do", "does",
    "did", "can", "could", "may", "might", "must", "shall", "should", "will",
    "would", "cannot", "isn't", "aren't", "wasn't", "weren't", "hasn't",
    "haven't", "hadn't", "doesn't", "don't", "didn't", "can't", "couldn't",
    "won't", "wouldn't", "shouldn't", "mustn't",
}

# What cannot be the subject a finite verb agrees with. A word ending in `s`
# after one of these is a plural noun, not a third-person present verb.
NOT_A_SUBJECT = {
    "a", "an", "the", "this", "these", "those", "its", "their", "our", "his",
    "her", "some", "any", "no", "each", "every", "all", "both", "few", "many",
    "more", "most", "other", "several", "such", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten", "of", "in", "on", "at", "by",
    "for", "from", "to", "with", "into", "over", "under", "per", "against",
    "across", "and", "or", "plus", "versus", "vs",
}


class Token:
    """One word, and whether punctuation closes it off.

    The punctuation is kept because it is what separates an inventory item's
    plural noun from a predication's verb: `5 DSL2 stages, DAPI as anchor` ends
    its noun on a comma, and `illumination correction suppresses tile-boundary
    seams` does not.
    """

    __slots__ = ("word", "closed")

    def __init__(self, word, closed):
        self.word = word
        self.closed = closed


class Brief:
    """One unit's brief: its zones, or the one reason nothing can be measured.

    A brief this parser cannot read is reported in the row rather than raised.
    Every row this instrument owns is reported-only, so raising would make an
    unreadable brief change the exit code — and the brief is an input to a
    prose fact, never to the document the render emits.
    """

    def __init__(self, path, zones=None, problem=None):
        self.path = path
        self.zones = zones or {}
        self.problem = problem

    def zone(self, name):
        return "\n".join(self.zones.get(name, []))

    @property
    def reader_facing(self):
        """The zones whose content may legitimately reach the prose, in the
        order this parser fixes."""
        return [
            (name, self.zone(name))
            for name in READER_FACING_ZONES
            if name in self.zones
        ]


def parse_brief(path):
    """The unit's brief, or `None` where the unit has none.

    An absent brief is a legal state: briefs arrive as units are planned, and a
    unit with no brief yet is a unit nothing has been measured against. The row
    says so, rather than counting it as nothing to report.
    """
    if not path.exists():
        return None
    zones = _sections(path.read_text())
    unparsed = [name for name in zones if name not in BRIEF_ZONES]
    if unparsed:
        return Brief(
            path,
            problem="unparsed zone `## %s`, so its content is measured against "
            "nothing" % unparsed[0],
        )
    if not any(name in zones for name in READER_FACING_ZONES):
        return Brief(
            path,
            problem="no `## %s` or `## %s` zone, so it has no reader-facing zone"
            % (ARGUMENT, INVENTORY),
        )
    return Brief(path, zones=zones)


def load_briefs(root, skeleton):
    """One brief per unit, keyed by unit — the same 1:1 the rung, the word
    budget and the `draft` ticket all key on."""
    return dict(
        (unit.id, parse_brief(root / "briefs" / ("%s.md" % unit.id)))
        for unit in skeleton.units
    )


# --------------------------------------------------------------------------
# the overlap instrument
# --------------------------------------------------------------------------


def _tokenize(text):
    lowered = text.lower()
    tokens = []
    for match in TOKEN.finditer(lowered):
        word = match.group(0).rstrip(TRAILING)
        if not word:
            continue
        after = lowered[match.end() : match.end() + 1]
        closed = (
            bool(match.group(0)[len(word) :])  # the punctuation the word carries
            or after in CLOSING
            or after == ""  # a clause's last word closes on the clause
        )
        tokens.append(Token(word, closed))
    return tokens


def _paragraphs(prose):
    return [block.strip() for block in re.split(r"\n\s*\n", prose) if block.strip()]


def _sentences(text):
    """Sentence-split on terminal punctuation, holding an abbreviation
    together — `e.g.` mid-paragraph does not make a paragraph of two."""
    parts = []
    for part in SENTENCE_END.split(text.strip()):
        part = part.strip()
        if not part:
            continue
        if parts and ABBREVIATION.search(parts[-1]):
            parts[-1] = "%s %s" % (parts[-1], part)
        else:
            parts.append(part)
    return parts


def _clauses(text):
    """The text as token lists, one per sentence.

    A shared span is measured inside one sentence and never across two,
    because a run that bridges a full stop is an adjacency rather than a
    phrase: nobody transcribed *…per marker pair. Registration…*, the two
    texts merely happen to order their own items the same way.
    """
    return [
        _tokenize(sentence)
        for block in _paragraphs(text)
        for sentence in _sentences(block)
    ]


def _grams(clauses):
    """Every `SUBSTANTIAL`-word window in the brief, by the clause it sits in."""
    grams = {}
    for words in clauses:
        for start in range(len(words) - SUBSTANTIAL + 1):
            grams.setdefault(tuple(words[start : start + SUBSTANTIAL]), []).append(
                (words, start)
            )
    return grams


def _shared_spans(grams, prose_words):
    """Every maximal run of `SUBSTANTIAL` words or more that this clause of the
    prose shares verbatim with the brief, as index ranges into the clause.

    Word-level rather than character-level, because what this catches is a
    phrase reused, and a phrase survives a re-wrapped line.
    """
    spans = []
    index = 0
    while index <= len(prose_words) - SUBSTANTIAL:
        found = grams.get(tuple(prose_words[index : index + SUBSTANTIAL]))
        if found is None:
            index += 1
            continue
        longest = SUBSTANTIAL
        for words, start in found:
            length = SUBSTANTIAL
            while (
                index + length < len(prose_words)
                and start + length < len(words)
                and prose_words[index + length] == words[start + length]
            ):
                length += 1
            longest = max(longest, length)
        spans.append((index, longest))
        index += longest
    return spans


def _substantial(span):
    return sum(1 for token in span if token.word not in FUNCTION_WORDS) >= 2


def _has_finite_verb(span):
    """The finite-verb test: does this shared span predicate something?

    A closed list plus one guarded morphological rule, and deliberately no
    more. `-ed` is not a tell — the corpus's own *scale bar required* is an
    expected span — and a bare `-s` rule fires on every plural noun, which is
    the failure a legend cannot survive: an instrument that fires forever is an
    instrument nobody reads.
    """
    for index, token in enumerate(span):
        if token.word in FINITE_FORMS:
            return True
        if _third_person_present(span, index):
            return True
    return False


def _third_person_present(span, index):
    word = span[index].word
    if len(word) < 4 or not word.endswith("s"):
        return False
    if word.endswith(("ss", "us", "is", "ies", "'s", "’s")):
        return False
    if index == 0 or index == len(span) - 1:
        return False  # a span's last word has nothing left to predicate about
    if span[index].closed:
        return False  # punctuation closes an item, so this is its final noun
    previous = span[index - 1].word
    return previous not in NOT_A_SUBJECT and not previous[0].isdigit()


def _quote(span):
    text = " ".join(token.word for token in span)
    return text if len(text) <= 56 else text[:55] + "…"


def measure_overlap(brief, prose_text):
    """The spans a unit's prose shares with its brief's reader-facing zones,
    split by the instrument the zone they came from carries.

    The zone decides the instrument, not the unit: `## Argument`'s propositions
    are phrased as what the reader must accept, so verbatim overlap with one
    *is* the defect and needs no verb test; an inventory item is a fact the
    prose must convey, so a shared span is expected unless it predicates.
    """
    prose = _clauses(prose_text)
    flagged = []
    expected = 0
    seen = set()
    for name, zone_text in brief.reader_facing:
        grams = _grams([[token.word for token in clause] for clause in _clauses(zone_text)])
        for number, clause in enumerate(prose):
            words = [token.word for token in clause]
            for start, length in _shared_spans(grams, words):
                span = clause[start : start + length]
                if not _substantial(span) or (number, start, length) in seen:
                    continue
                seen.add((number, start, length))
                if name == ARGUMENT or _has_finite_verb(span):
                    flagged.append(_quote(span))
                else:
                    expected += 1
    return flagged, expected


# --------------------------------------------------------------------------
# paragraph shape — originating units only
# --------------------------------------------------------------------------


def _argument_items(brief):
    """The brief's propositions, in the order the brief states them.

    Sentences of the `## Argument` zone, less the ladder line: a proposition is
    phrased as what the reader must end up accepting, which is a sentence, and
    the relation line is bookkeeping.
    """
    lines = [
        line
        for line in brief.zones.get(ARGUMENT, [])
        if line.strip() and not RELATION_LINE.match(line.strip())
    ]
    return _sentences(" ".join(line.strip() for line in lines))


def _content_words(text):
    return set(
        token.word for token in _tokenize(text) if token.word not in FUNCTION_WORDS
    )


def _matching_item(paragraph, items):
    """The brief item this paragraph is about, or `-1` where it is about none.

    Content-word overlap, floored at two: one shared word is a shared topic,
    and two is the smallest evidence that a paragraph was built on an item.
    """
    words = _content_words(paragraph)
    best, score = -1, 1
    for index, item in enumerate(items):
        shared = len(words & _content_words(item))
        if shared > score:
            best, score = index, shared
    return best


def _mirrored(paragraphs, items):
    """How many paragraphs sit at the position of the brief item they are
    about — the one-bullet-per-paragraph walk, counted."""
    span = min(len(paragraphs), len(items))
    return (
        sum(
            1
            for index in range(span)
            if _matching_item(paragraphs[index], items) == index
        ),
        span,
    )


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


class Measurement:
    """A reported row's outcome: numbers, never a verdict.

    A reported row carries a prose fact, and a prose fact has no verdict to
    give — `PASS` over one would claim the number is fine, which is a judgement
    this unit does not make, and `FAIL` would be the threshold the design
    refuses. So it prints what it measured, it can never fail, and it never
    reaches the exit code.
    """

    def __init__(self, text):
        self.kind = REPORTED
        self.problems = []
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
    return Verdict.over(slot_integrity_problems(paper.skeleton, paper.blocks, paper.stray))


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


def report_brief_overlap(paper):
    """How much of each unit's brief reached its prose verbatim.

    A drafting session that walks its brief one bullet per paragraph produces a
    list of labelled blocks rather than a manuscript, and the corpus shows it
    happening: the audit's own phrase for what it found is *transcribed
    near-verbatim from the briefs*. Both numbers are reported and neither is a
    floor — a threshold here would be a rule about prose, and rules about prose
    is what the judgement axes are for.
    """
    flagged = []
    expected = 0
    notes = []
    absent = []
    for unit in paper.units:
        brief = paper.brief_for(unit)
        if brief is None:
            absent.append("`%s`" % unit.id)
            continue
        if brief.problem:
            notes.append("%s: %s" % (brief.path.name, brief.problem))
            continue
        spans, expected_here = measure_overlap(brief, paper.prose_of_unit(unit))
        expected += expected_here
        flagged.extend('%s: "%s"' % (unit.id, span) for span in spans)

    text = "%d flagged, %d expected" % (len(flagged), expected)
    detail = flagged + notes
    if absent:
        detail.append("no brief for %s" % ", ".join(absent))
    if detail:
        text += " — %s" % "; ".join(detail)
    return Measurement(text)


def report_paragraph_shape(paper):
    """Single-sentence body paragraphs, and how far each unit's paragraphs walk
    its brief's items in order.

    **Originating units only.** For a non-originating unit both measures
    invert: order tracking the brief is what a venue's field order and a
    figure's lettering *mandate*, and a panel caption is not a unit of
    argument, so a single-sentence paragraph is its normal shape. Run either on
    a legend and it fires forever. There, the finite-verb test carries the whole
    load.
    """
    originating = [unit for unit in paper.units if _originates(paper, unit)]
    if not originating:
        return Measurement("no originating unit in scope")

    singles = []
    walks = []
    notes = []
    for unit in originating:
        paragraphs = _paragraphs(paper.prose_of_unit(unit))
        singles.extend(
            "%s ¶%d" % (unit.id, number)
            for number, paragraph in enumerate(paragraphs, start=1)
            if len(_sentences(paragraph)) == 1
        )
        brief = paper.brief_for(unit)
        if brief is None or brief.problem:
            notes.append("%s: no brief this parser can read" % unit.id)
            continue
        items = _argument_items(brief)
        if not items:
            notes.append("%s: the brief states no proposition" % unit.id)
            continue
        if not paragraphs:
            notes.append("%s: no drafted prose" % unit.id)
            continue
        mirrored, span = _mirrored(paragraphs, items)
        walks.append("%d of %d (%s)" % (mirrored, span, unit.id))

    text = "single-sentence %d" % len(singles)
    if singles:
        text += " (%s)" % ", ".join(singles)
    if walks:
        text += "; brief-order %s" % ", ".join(walks)
    if notes:
        text += "; brief-order not measured (%s)" % "; ".join(notes)
    return Measurement(text)


def _originates(paper, unit):
    rung = paper.spine.rung_for(unit.id)
    return rung is not None and rung.originating


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
#   reported em dashes                  the reported tier
#   reported brief-to-prose overlap     (built)
#   reported paragraphs (originating)   (built)
#   reported the Tier 4 diagnostics     the reported tier
#   reported locality test              chain walk
#   reported supersession diff          the supersession diff
#
# The two parse-tier rows built here have no entry below: a parse error means
# nothing ran, so the table is absent rather than carrying their verdicts.
REGISTRY = [
    ("slot integrity", HARD, DOCUMENT, check_slot_integrity),
    ("unit / rung pairing", HARD, None, check_unit_rung_pairing),
    ("originating slot children", HARD, None, check_originating_slot_children),
    ("unfilled skeleton slot", GATING, None, check_unfilled_skeleton_slot),
    ("brief-to-prose overlap", REPORTED, None, report_brief_overlap),
    ("paragraphs (originating)", REPORTED, None, report_paragraph_shape),
]

# The parse-tier rows print `PASS` whenever a table prints at all, because a
# parse-tier failure suppresses the table.
PARSE_ROWS = ["skeleton / spine grammar", "source grammar"]


# --------------------------------------------------------------------------
# the render
# --------------------------------------------------------------------------


class Paper:
    """One paper at one granularity: the two files, the source, and the slots
    in scope."""

    def __init__(self, skeleton, spine, briefs, blocks, stray, granularity, unit):
        self.skeleton = skeleton
        self.spine = spine
        self.briefs = briefs
        self.blocks = blocks
        self.stray = stray
        self.granularity = granularity
        self.unit = unit
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

    def prose_of_unit(self, unit):
        """Every slot in the unit's subtree, in skeleton order. A unit is what a
        brief keys on, so a unit's prose is what its brief is measured
        against."""
        return "\n\n".join(
            prose
            for prose in (
                self.prose_for(slot) for slot in self.skeleton.subtree(unit)
            )
            if prose
        )

    def brief_for(self, unit):
        return self.briefs.get(unit.id)


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
    counts = {PASS: 0, FAIL: 0, SKIPPED: 0, REPORTED: 0}
    for name, verdict in rows:
        lines.append("%s%s %s" % (INDENT, name.ljust(NAME_WIDTH - 1), verdict.render()))
        counts[verdict.kind] += 1
    lines.append("")
    lines.append(
        "%s%d pass, %d fail, %d out of scope, %d reported"
        % (INDENT, counts[PASS], counts[FAIL], counts[SKIPPED], counts[REPORTED])
    )
    lines.append(
        "%s→ NOT a claim that this %s is finished"
        % (INDENT, SECTION if granularity == SECTION else DOCUMENT)
    )
    return "\n".join(lines) + "\n"


def run_gate(paper):
    """Every row in registry order, and the failed rows by tier."""
    rows = [(name, Verdict(PASS)) for name in PARSE_ROWS]
    failed = {HARD: [], GATING: []}
    for name, tier, scope, check in REGISTRY:
        verdict = (
            Verdict.skipped()
            if scope == DOCUMENT and paper.granularity == SECTION
            else check(paper)
        )
        rows.append((name, verdict))
        if verdict.kind == FAIL:
            failed[tier].append((name, verdict))  # only a tier with a gate has one
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
        help="pre-seed a unit's source with every anchor in its subtree, in "
        "skeleton order; writes the source in place",
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
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    source = Path(args.source)
    granularity = SECTION if args.section is not None else DOCUMENT

    try:
        root = find_paper_root(source, Path(args.paper) if args.paper else None)
        if args.scaffold:
            # The scaffold writes the source rather than reading a finished
            # one, so it neither reads the ladder — the gate's input, with no
            # use here — nor runs a check: it emits no document to be wrong.
            # It is always one unit, so `--section` names that unit here rather
            # than choosing a granularity.
            return scaffold(source, parse_skeleton(root / "skeleton.md"), args.section)
        paths = source_paths(source)
        skeleton = parse_skeleton(root / "skeleton.md")
        spine = parse_spine(root / "spine.md")
        blocks, stray = parse_source(paths)
        briefs = load_briefs(root, skeleton)
        unit = None
        if granularity == SECTION:
            unit = derive_unit(skeleton, blocks, args.section)
    except ParseError as error:
        sys.stderr.write("render-paper: parse error — %s\n" % error)
        return EXIT_PARSE
    except HardError as error:
        sys.stderr.write("render-paper: %s\n" % error)
        return EXIT_HARD

    paper = Paper(skeleton, spine, briefs, blocks, stray, granularity, unit)
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
