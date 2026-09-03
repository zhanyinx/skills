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

See `SKILL.md`, `SKELETON-FORMAT.md`, `SPINE-FORMAT.md` and `ANNOTATION-CHANNEL.md`
beside this script.
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
# parse iff the source cannot express the thing at all.
HARD = "hard"
GATING = "gating"

# The three verdicts, and nothing else. No single-word verdict is emitted
# anywhere: one word cannot carry checked-and-fine against never-looked.
PASS = "PASS"
FAIL = "FAIL"
SKIPPED = "SKIPPED — OUT OF SCOPE AT THIS GRANULARITY"

DOCUMENT = "document"
SECTION = "section"

# The annotation channel's two axes, and nothing else. There is no kind enum:
# render behaviour is one axis, the gate bit is the other, and the one
# dimension they do not carry — who resolves it — is the free-text `@owner`.
HOLE = "HOLE"
VENUE_SLOT = "SLOT"  # `SLOT:` inside braces is a venue field, never a section
SILENT = "SILENT"

DEFAULT_OWNER = "@author"
LABEL_ADVISORY = 80

NAME_WIDTH = 26
BEHAVIOUR_WIDTH = 6
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

BRACE_OPEN = re.compile(r"\{\{")
BRACE_CLOSE = re.compile(r"\}\}")
SLOT_INTENT = re.compile(r"^slot\s*:", re.IGNORECASE)
SLOT_MARK = re.compile(r"^SLOT:")
OWNER = re.compile(r"^@\S+")
REASONING_KEY = re.compile(r"^\{\{(.*?)\}\}\s*:(.*)$", re.DOTALL)
SENTENCE_END = re.compile(r"[.!?](?=\s|$)")

# The directional-word list is short, dumb and conservative, the way the other
# residue lints are, so the renderer stays paper-agnostic. It buys one manifest
# line, never a gate of its own: the direction inherits the hole's bit.
DIRECTIONAL = re.compile(
    r"\b("
    r"raise[sd]?|raising|lower(?:s|ed|ing)?|rise[sn]?|rose|fell|fall(?:s|en)?|"
    r"increase[sd]?|increasing|decrease[sd]?|decreasing|improve[sd]?|improving|"
    r"reduce[sd]?|reducing|gain(?:s|ed)?|drop(?:s|ped)?|exceed(?:s|ed)?|"
    r"outperform(?:s|ed)?|higher|better|worse|greater|smaller|more|fewer|less|"
    r"faster|slower|stronger|weaker"
    r")\b",
    re.IGNORECASE,
)

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


class Annotation:
    """One author-facing annotation, on both axes at once.

    `behaviour` decides what the reader sees — a `HOLE` renders as a
    conspicuous token, a `VENUE_SLOT` as a visible placeholder, a `SILENT` as
    nothing at all. `gate` decides whether it blocks `--submit`. The two are
    independent, which is what lets a verify flag be SILENT and still refuse a
    submission.
    """

    def __init__(self, behaviour, gate, owner, label, origin, line, slot_id):
        self.behaviour = behaviour
        self.gate = gate
        self.owner = owner or DEFAULT_OWNER
        self.label = label
        self.origin = origin
        self.line = line
        self.slot_id = slot_id
        self.reasoning = None
        self.direction = None

    @property
    def where(self):
        return "%s:%d" % (self.origin.name, self.line)

    @property
    def token(self):
        """What the reader sees. Uniform across both brace behaviours, so one
        grep finds every gap in a circulated paper."""
        return "⟦%s: %s⟧" % (self.behaviour, self.label)


def parse_source(paths):
    """Read the source and return the anchored blocks in the order they appear,
    the prose sitting outside every slot, the annotation manifest, and the
    advisory warnings.

    One file post-promotion, or every section source pre-promotion — the blocks
    concatenate, and the render orders them by the skeleton rather than by the
    order they were read in.
    """
    blocks = []
    stray = []
    annotations = []
    warnings = []
    for path in paths:
        found, outside, marked, advised = _parse_one_source(path.read_text(), path)
        blocks.extend(found)
        stray.extend(outside)
        annotations.extend(marked)
        warnings.extend(advised)
    return blocks, stray, annotations, warnings


def _parse_one_source(text, path):
    """One source file: read the annotation channel, strip every comment, and
    split what is left at the anchors.

    Parsing is span-based, never line-anchored: an annotation may wrap across
    any number of lines, and in the corpus this design was calibrated on, 13 of
    30 did, one of them over six lines. A line-anchored parser is the thing an
    implementer assumes away.
    """
    fenced = _fenced_spans(text)
    _refuse_unclosed_comment(text, path, fenced)
    _refuse_headings(text, path, fenced)

    # Braces are read off the text with every comment blanked to same-length
    # whitespace, so a reasoning comment's `{{label}}` join key is not itself
    # an annotation and every offset still points at the real source.
    masked = _mask_comments(text, fenced)
    spans = _brace_spans(masked, path, fenced)
    bare = _blank_spans(masked, spans)

    blocks = []
    stray = []
    annotations = []
    advisories = []
    keyed = {}
    current = None
    pending = []
    cursor = 0
    braces = []

    for match in COMMENT.finditer(text):
        if _inside(fenced, match.start()):
            continue  # inside a fence it is literal text, not a comment
        taken = _chunk(spans, cursor, match.start())
        pending.append(_substitute(text, cursor, match.start(), taken))
        braces.extend(taken)
        annotations.extend(_attach(taken, current, masked, bare, advisories))
        cursor = match.end()
        slot_id = _anchor_slot_id(match, text, path)
        if slot_id is not None:
            _attribute(_tidy("".join(pending)), current, path, stray)
            pending = []
            current = Block(slot_id, path, _line_of(text, match.start()))
            blocks.append(current)
            continue
        # Every comment is stripped, as a class. Three of them are then read
        # again for the manifest, and the rest are tracked nowhere.
        entry = _read_comment(match, text, path, current, keyed)
        if entry is not None:
            annotations.append(entry)

    taken = _chunk(spans, cursor, len(text))
    pending.append(_substitute(text, cursor, len(text), taken))
    braces.extend(taken)
    annotations.extend(_attach(taken, current, masked, bare, advisories))
    _attribute(_tidy("".join(pending)), current, path, stray)

    _join_reasoning(braces, keyed, path, advisories)
    advisories.sort(key=lambda advisory: advisory[0])
    return blocks, stray, annotations, [text for _, text in advisories]


def _chunk(spans, start, end):
    """The brace spans lying in `[start, end)`, in source order."""
    return [span for span in spans if start <= span[0] < end]


def _substitute(text, start, end, spans):
    """The prose of one chunk, with every brace replaced by its render token.

    A HOLE and a SLOT both come out as a token; nothing is ever dropped,
    because stripping a gap silently converts a flagged hole into an
    unsupported claim the author never learns about.
    """
    out = []
    cursor = start
    for span_start, span_end, annotation in spans:
        out.append(text[cursor:span_start])
        out.append(annotation.token)
        cursor = span_end
    out.append(text[cursor:end])
    return "".join(out)


def _attach(spans, block, masked, bare, advisories):
    """Give each brace in a chunk the slot it sits under, and run the two
    advisory lints over it."""
    found = []
    for span_start, span_end, annotation in spans:
        annotation.slot_id = None if block is None else block.slot_id
        if annotation.behaviour == HOLE:
            annotation.direction = _direction(bare, span_start, span_end)
            if _block_alone(masked, span_start, span_end):
                advisories.append(
                    (
                        annotation.line,
                        "%s: the bare brace `{{ %s }}` stands alone in its own "
                        "block, so it is probably a `SLOT:`"
                        % (annotation.where, annotation.label),
                    )
                )
        if len(annotation.label) > LABEL_ADVISORY:
            advisories.append(
                (
                    annotation.line,
                    "%s: the label runs to %d characters, over the "
                    "%d-character advisory limit — reasoning belongs in a keyed "
                    "comment beside the brace"
                    % (annotation.where, len(annotation.label), LABEL_ADVISORY),
                )
            )
        found.append(annotation)
    return found


def _brace_spans(masked, path, fenced):
    """Every `{{ … }}` span outside every comment and fence, as one linear walk
    over the `{{` and `}}` tokens.

    The walk, rather than a regex, is what lets an unclosed brace name the
    brace that never closed instead of the next one along. A malformed brace is
    a parse error and not a gate: it has no behaviour and no gate bit to
    honour, so it sits in the same category as an unclosed comment.
    """
    tokens = [
        (match.start(), True)
        for match in BRACE_OPEN.finditer(masked)
        if not _inside(fenced, match.start())
    ]
    tokens += [
        (match.start(), False)
        for match in BRACE_CLOSE.finditer(masked)
        if not _inside(fenced, match.start())
    ]
    tokens.sort()

    spans = []
    opened_at = None
    for offset, opening in tokens:
        if opening and opened_at is not None:
            raise ParseError(
                "%s:%d: unclosed brace `{{`" % (path.name, _line_of(masked, opened_at))
            )
        if opening:
            opened_at = offset
        elif opened_at is None:
            raise ParseError(
                "%s:%d: unmatched `}}`" % (path.name, _line_of(masked, offset))
            )
        else:
            spans.append(
                (
                    opened_at,
                    offset + 2,
                    _brace_annotation(masked, opened_at, offset + 2, path),
                )
            )
            opened_at = None
    if opened_at is not None:
        raise ParseError(
            "%s:%d: unclosed brace `{{`" % (path.name, _line_of(masked, opened_at))
        )
    return spans


def _brace_annotation(text, start, end, path):
    """One brace, read against `{{ [!] [SLOT:] [@owner] <label> }}`.

    The three prefixes appear once each, in that order, and a remainder still
    carrying one of them is a parse error rather than a label that happens to
    start with `!` — because that reading would silently lose the gate bit,
    which is the one thing that decides whether a paper can be submitted.
    """
    shown = _collapse(text[start + 2 : end - 2])
    where = "%s:%d" % (path.name, _line_of(text, start))
    label = shown

    gate = label.startswith("!")
    if gate:
        label = label[1:].lstrip()

    behaviour = HOLE
    if SLOT_INTENT.match(label):
        mark = SLOT_MARK.match(label)
        if not mark:
            raise ParseError(
                "%s: `{{ %s }}` claims to be a venue slot — the marker is "
                "`SLOT:`, uppercase, with no space before the colon"
                % (where, shown)
            )
        behaviour = VENUE_SLOT
        label = label[mark.end() :].lstrip()

    owner = None
    named = OWNER.match(label)
    if named:
        owner = named.group(0)
        label = label[named.end() :].lstrip()

    if not label:
        raise ParseError(
            "%s: `{{ %s }}` names no value — a brace names the missing value, "
            "and its reasoning goes in a keyed comment beside it" % (where, shown)
        )
    if label.startswith(("!", "@")) or SLOT_INTENT.match(label):
        raise ParseError(
            "%s: `{{ %s }}` — the `!`, `SLOT:` and `@owner` prefixes appear "
            "once each, in that order" % (where, shown)
        )
    return Annotation(
        behaviour, gate, owner, label, path, _line_of(text, start), None
    )


def _read_comment(match, text, path, block, keyed):
    """One stripped comment, read again for the manifest.

    A comment enters the manifest **if and only if** its first non-space
    character is `!` or `@`. That is what keeps the rung, the objection note
    and the section anchors out of a list of outstanding work sent to a
    co-author: nobody owes a rung.
    """
    content = match.group(1).strip()
    line = _line_of(text, match.start())

    reasoning = REASONING_KEY.match(content)
    if reasoning:
        keyed.setdefault(_join_key(reasoning.group(1)), []).append(
            (_collapse(reasoning.group(2)), line)
        )
        return None
    if not content.startswith(("!", "@")):
        return None  # an ordinary author comment: stripped, tracked nowhere

    shown = _collapse(content)
    where = "%s:%d" % (path.name, line)
    label = shown
    gate = label.startswith("!")
    if gate:
        label = label[1:].lstrip()
    owner = None
    named = OWNER.match(label)
    if named:
        owner = named.group(0)
        label = label[named.end() :].lstrip()
    if not label:
        raise ParseError(
            "%s: `<!-- %s -->` names no value" % (where, shown)
        )
    if label.startswith(("!", "@")):
        raise ParseError(
            "%s: `<!-- %s -->` — the `!` and `@owner` prefixes appear once "
            "each, in that order" % (where, shown)
        )
    return Annotation(
        SILENT, gate, owner, label, path, line, None if block is None else block.slot_id
    )


def _join_reasoning(braces, keyed, path, advisories):
    """Attach each keyed comment to the brace it keys.

    The label is the join key, and the grammar fixes token order but not
    whitespace — drafting produced two spellings of one label without intent,
    which orphaned the reasoning **silently**. Normalisation closes that, and a
    key matching no brace warns rather than vanishing.
    """
    for key, entries in keyed.items():
        reasoning, line = entries[0]
        matched = [
            annotation for _, _, annotation in braces if annotation.label == key
        ]
        for annotation in matched:
            annotation.reasoning = reasoning
        if not matched:
            advisories.append(
                (
                    line,
                    "%s:%d: `{{%s}}` keys no brace in this source, so its "
                    "reasoning is attached to nothing" % (path.name, line, key),
                )
            )
        # Keeping the first and dropping the rest silently is the orphan defect
        # one step along, so it warns for the same reason and at the same tier.
        for _, repeated in entries[1:]:
            advisories.append(
                (
                    repeated,
                    "%s:%d: `{{%s}}` is keyed again here, and only the comment "
                    "at line %d is attached" % (path.name, repeated, key, line),
                )
            )


def _blank_spans(masked, spans):
    """The text with every brace blanked to same-length whitespace too.

    The direction is committed by the **claim**, so the scan for it must not
    see the labels — and a label carrying a `!` gate bit would otherwise read
    as the end of a sentence.
    """
    out = list(masked)
    for start, end, _ in spans:
        for offset in range(start, end):
            if out[offset] != "\n":
                out[offset] = " "
    return "".join(out)


def _collapse(text):
    """Trimmed, with internal whitespace collapsed. Labels compare after this,
    so a brace that wraps six lines is one label and not six."""
    return re.sub(r"\s+", " ", text).strip()


def _join_key(label):
    """A label as a join key: collapsed, and stripped of all three prefixes.

    Tolerant by design. A malformed key inside a comment is not reader-facing,
    so it warns through `_join_reasoning` rather than refusing the render.
    """
    key = _collapse(label)
    if key.startswith("!"):
        key = key[1:].lstrip()
    mark = SLOT_MARK.match(key)
    if mark:
        key = key[mark.end() :].lstrip()
    named = OWNER.match(key)
    if named:
        key = key[named.end() :].lstrip()
    return key


def _direction(masked, start, end):
    """The directional word committed in the sentence resting on this hole.

    Six of seven gating annotations in the corpus sat under a committed
    direction written before the value existed — and deletion being the only
    closure means the obligation vanishes the moment the value is filled. So
    the direction is named while the hole is still open, on the hole's own
    manifest entry, inheriting the hole's gate bit and adding none.
    """
    sentence = _sentence_around(masked, start, end)
    found = DIRECTIONAL.search(sentence)
    return found.group(0) if found else None


def _sentence_around(masked, start, end):
    """The sentence a brace sits in, minus the brace itself — the direction is
    committed by the claim, never by the label."""
    left = 0
    for match in SENTENCE_END.finditer(masked, 0, start):
        left = match.end()
    paragraph = masked.rfind("\n\n", 0, start)
    if paragraph >= 0:
        left = max(left, paragraph + 2)

    right = len(masked)
    found = SENTENCE_END.search(masked, end)
    if found:
        right = found.end()
    paragraph = masked.find("\n\n", end)
    if paragraph >= 0:
        right = min(right, paragraph)
    return masked[left:start] + " " + masked[end:right]


def _block_alone(masked, start, end):
    """Nothing but whitespace between the brace and the blank line on either
    side. On the whole corpus that shape is always a venue slot — which is
    strong evidence and not the definition, so it warns."""
    left = masked.rfind("\n\n", 0, start)
    left = 0 if left < 0 else left + 2
    right = masked.find("\n\n", end)
    right = len(masked) if right < 0 else right
    return not (masked[left:start].strip() or masked[end:right].strip())


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


def _mask_comments(text, fenced):
    """Blank every comment's content to same-length whitespace, keeping the
    newlines, so a scan over the result still reports the source's own line
    numbers and offsets. A fenced comment is literal text, so it survives."""

    def blank(match):
        if _inside(fenced, match.start()):
            return match.group(0)
        return "".join("\n" if char == "\n" else " " for char in match.group(0))

    return COMMENT.sub(blank, text)


def _refuse_headings(text, path, fenced):
    """The skeleton owns every heading at every level, and the render injects
    them on every pass. So a heading in a source is not a thing the source can
    express: it would render as a heading the skeleton never declared.

    Both markdown spellings count. The underlined form is the one an editor
    reaches for by hand, so leaving it out would leave the surface open.
    """
    masked = _mask_comments(text, fenced)
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


def check_gating_annotations(paper):
    """No annotation carrying the gate bit is still open.

    The render is faithful either way — a gap comes out as a token and lands in
    the manifest — but the work is unfinished, so this gates submission and
    never blocks circulation. Both brace behaviours and SILENT are in scope:
    the bit is independent of what the reader sees, which is what lets a verify
    flag emit nothing and still refuse a submission.
    """
    problems = [
        "%s `%s`" % (annotation.where, annotation.label)
        for annotation in paper.annotations_in_scope
        if annotation.gate
    ]
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


# Row order is this registry's order, and it is fixed: `review-paper` reports
# the table verbatim, so the order is an interface. Rows arrive as the checks
# behind them are built; a row is never printed without a check behind it,
# because a row with nothing behind it reads as a pass.
#
# The registry's declared order, with the rows not yet built named in place:
#
#   parse    skeleton / spine grammar    (built)
#   parse    source grammar              (built)
#   parse    brace grammar               (built)
#   parse    citation group              citations
#   parse    reference literals          figures and panels
#   hard     slot integrity              (built; becomes slot / roster
#                                        integrity when figures land the
#                                        roster half of it)
#   hard     citation → bib entry        citations
#   hard     unit / rung pairing         (built)
#   hard     originating slot children   (built)
#   gating   annotations (gating)        (built)
#   gating   unfilled skeleton slot      (built)
#   gating   bare holes                  residue lints
#   gating   workflow phrases            residue lints
#   gating   chain bookkeeping           chain walk
#   reported (the diagnostics, the overlap instrument, the locality test)
#
# The two parse-tier rows built here have no entry below: a parse error means
# nothing ran, so the table is absent rather than carrying their verdicts.
REGISTRY = [
    ("slot integrity", HARD, DOCUMENT, check_slot_integrity),
    ("unit / rung pairing", HARD, None, check_unit_rung_pairing),
    ("originating slot children", HARD, None, check_originating_slot_children),
    ("annotations (gating)", GATING, None, check_gating_annotations),
    ("unfilled skeleton slot", GATING, None, check_unfilled_skeleton_slot),
]

# The parse-tier rows print `PASS` whenever a table prints at all, because a
# parse-tier failure suppresses the table.
PARSE_ROWS = ["skeleton / spine grammar", "source grammar", "brace grammar"]


# --------------------------------------------------------------------------
# the render
# --------------------------------------------------------------------------


class Paper:
    """One paper at one granularity: the two files, the source, and the slots
    in scope."""

    def __init__(
        self,
        skeleton,
        spine,
        blocks,
        stray,
        annotations,
        warnings,
        granularity,
        unit,
    ):
        self.skeleton = skeleton
        self.spine = spine
        self.blocks = blocks
        self.stray = stray
        self.annotations = annotations
        self.warnings = warnings
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

    @property
    def annotations_in_scope(self):
        """The annotations the gate can speak for at this granularity.

        The **gate** is scoped the way every other row is. The **manifest** is
        not: it enters whole, because it is `f(source)` recomputed per render
        and an absolute input to a diff-relative judgement axis.
        """
        if self.granularity == DOCUMENT:
            return self.annotations
        in_scope = set(slot.id for slot in self.slots)
        return [
            annotation
            for annotation in self.annotations
            if annotation.slot_id in in_scope
        ]


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
    return "⟦%s: %s⟧" % (HOLE, label)


def format_manifest(annotations):
    """Every open annotation, grouped by `@owner`.

    Grouping by owner is what makes it **sendable**: an experimentalist can be
    handed their own group and nothing else. It is printed whether or not it is
    empty, because an absent manifest reads as nobody having looked — and it is
    an input to a judgement axis that has no previous manifest to diff.
    """
    lines = [""]
    if annotations:
        gating = sum(1 for annotation in annotations if annotation.gate)
        lines.append(
            "%smanifest — %d open annotation%s, %d carrying the gate bit"
            % (INDENT, len(annotations), "" if len(annotations) == 1 else "s", gating)
        )
    else:
        lines.append("%smanifest — no open annotations" % INDENT)
    lines.append(
        "%s→ f(source), recomputed at every render; deletion is the only closure"
        % INDENT
    )

    width = max([len(annotation.where) for annotation in annotations] or [0])
    for owner in sorted(set(annotation.owner for annotation in annotations)):
        lines.append("")
        lines.append("%s%s" % (INDENT, owner))
        for annotation in annotations:
            if annotation.owner != owner:
                continue
            lines.append(
                "%s%s%s  %s  %s  %s"
                % (
                    INDENT,
                    INDENT,
                    "!" if annotation.gate else " ",
                    annotation.behaviour.ljust(BEHAVIOUR_WIDTH),
                    annotation.where.ljust(width),
                    annotation.label,
                )
            )
            for name, value in (
                ("direction", _direction_line(annotation)),
                ("reasoning", annotation.reasoning),
            ):
                if value:
                    lines.append("%s%s: %s" % (" " * 7, name, value))
    return "\n".join(lines) + "\n"


def _direction_line(annotation):
    if annotation.direction is None:
        return None
    return "`%s` is committed before this value exists" % annotation.direction


def format_warnings(warnings):
    """Advisory, and advisory means advisory: never a row, never an exit code.

    A hard cap on either lint was rejected — it over- and under-fires, refusing
    a legitimate 110-character noun phrase while passing a 90-character
    imperative.
    """
    if not warnings:
        return ""
    lines = ["", "%swarnings — advisory; never a refusal" % INDENT, ""]
    lines.extend("%s%s%s" % (INDENT, INDENT, warning) for warning in warnings)
    return "\n".join(lines) + "\n"


def format_report(rows, granularity):
    """The table `review-paper` reports verbatim, so its shape is an interface."""
    lines = []
    counts = {PASS: 0, FAIL: 0, SKIPPED: 0}
    for name, verdict in rows:
        lines.append("%s%s %s" % (INDENT, name.ljust(NAME_WIDTH - 1), verdict.render()))
        counts[verdict.kind] += 1
    lines.append("")
    lines.append(
        "%s%d pass, %d fail, %d out of scope"
        % (INDENT, counts[PASS], counts[FAIL], counts[SKIPPED])
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
            failed[tier].append((name, verdict))
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
    return parser


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
        blocks, stray, annotations, warnings = parse_source(paths)
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
        skeleton, spine, blocks, stray, annotations, warnings, granularity, unit
    )
    rows, failed = run_gate(paper)
    report = (
        format_report(rows, granularity)
        + format_manifest(paper.annotations)
        + format_warnings(paper.warnings)
    )

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
