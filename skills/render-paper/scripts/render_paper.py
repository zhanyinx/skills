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

# The annotation channel's two axes, and nothing else. There is no kind enum:
# render behaviour is one axis, the gate bit is the other, and the one
# dimension they do not carry — who resolves it — is the free-text `@owner`.
HOLE = "HOLE"
VENUE_SLOT = "SLOT"  # `SLOT:` inside braces is a venue field, never a section
SILENT = "SILENT"

DEFAULT_OWNER = "@author"
LABEL_ADVISORY_CHARS = 80

NAME_WIDTH = 32
BEHAVIOUR_WIDTH = 6
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

# The reference surface: `@`-prefixed identifiers, and brackets that group them
# and contain nothing else. One rule covers citations and figures alike, which
# is why the identifier pattern is shared rather than duplicated per class.
#
# The trailing character may not be punctuation, so `@smith2020.` ends a
# sentence rather than swallowing the full stop into the key.
IDENTIFIER = r"[A-Za-z0-9_](?:[A-Za-z0-9_:.#$%&+?<>~/-]*[A-Za-z0-9_])?"

# The `@` must open the token. Without that guard the `@` inside an author's
# email address reads as a narrative citation, and a corresponding-author line
# in the back matter hard-errors against a key nobody wrote.
REFERENCE = re.compile(r"(?<![\w@])@(%s)" % IDENTIFIER)
CITATION_GROUP = re.compile(r"\[\s*@%s(?:\s*;\s*@%s)*\s*\]" % (IDENTIFIER, IDENTIFIER))
BRACKET = re.compile(r"[\[\]]")

# A figure lives in the same namespace behind the same `@`, and `figures and
# panels` owns resolving it. Here it is only ever *not a citation key*: the
# bracket grammar accepts it, the bibliography is never asked about it, and the
# render leaves any token carrying one verbatim.
FIGURE_PREFIX = "fig:"

# The render's own gap token. Its label is author-facing text that already sits
# in the prose by the time citations resolve, so the scan steps over it rather
# than numbering a key an author wrote inside a hole.
GAP_TOKEN = r"⟦[^⟧]*⟧"
CITATION_TOKEN = re.compile(
    r"(?P<gap>%s)|(?P<group>%s)|(?P<bare>%s)"
    % (GAP_TOKEN, CITATION_GROUP.pattern, REFERENCE.pattern),
    re.DOTALL,
)

BIB_ENTRY = re.compile(r"@(\w+)\s*\{", re.MULTILINE)
BIB_LINE_COMMENT = re.compile(r"^[ \t]*%.*$", re.MULTILINE)
BIB_FIELD = re.compile(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*")
BIB_PATH = "references.bib"

# `@string`, `@preamble` and `@comment` are BibTeX machinery, not entries, so
# they carry no citation key and are stepped over rather than refused.
BIB_NON_ENTRY = frozenset(["string", "preamble", "comment"])

# The reference list is deliberately style-neutral: the venue's citation style
# is a typesetting concern downstream, and encoding one here would put
# paper-specific text in the generator.
BIB_CONTAINER = ("journal", "booktitle", "publisher", "school", "institution")

BRACE_OPEN = re.compile(r"\{\{")
BRACE_CLOSE = re.compile(r"\}\}")
SLOT_INTENT = re.compile(r"^slot\s*:", re.IGNORECASE)
SLOT_MARK = re.compile(r"^SLOT:")
OWNER = re.compile(r"^@\S+")
REASONING_KEY = re.compile(r"^\{\{(.*?)\}\}\s*:(.*)$", re.DOTALL)

# The directional-word list is short, dumb and conservative, the way the other
# residue lints are, so the renderer stays paper-agnostic. It buys one manifest
# line, never a gate of its own: the direction inherits the hole's bit.
#
# Verbs of change, plus the comparatives of quality that commit a direction
# about the missing value itself. The bare quantifiers — `more`, `less`,
# `fewer`, `greater`, `smaller` — are deliberately absent: "more than 500 cells
# were counted, of which {{ the flagged count }} failed" commits no direction,
# and the manifest is the artifact that gets sent to a co-author, so a noisy
# one is a skipped one.
DIRECTIONAL = re.compile(
    r"\b("
    r"raise[sd]?|raising|lower(?:s|ed|ing)?|rise[sn]?|rose|fell|fall(?:s|en)?|"
    r"increase[sd]?|increasing|decrease[sd]?|decreasing|improve[sd]?|improving|"
    r"reduce[sd]?|reducing|gain(?:s|ed)?|drop(?:s|ped)?|exceed(?:s|ed)?|"
    r"outperform(?:s|ed)?|higher|better|worse|faster|slower|stronger|weaker"
    r")\b",
    re.IGNORECASE,
)

# What the prose diagnostics read, and what they refuse to read. Scope is
# defined rather than assumed: a count that walks over a table row or a quoted
# source title fires on text no author wrote as prose.
EM_DASH = "—"
TABLE_ROW = re.compile(r"^ {0,3}\|.*$", re.MULTILINE)
# Every bracket span in prose is a citation group, enforced by parse, so the
# diagnostics blank the one pattern the grammar admits rather than guessing at
# which spans carry a key.

# Sentence splitting is mechanical and conservative: a terminator followed by
# whitespace, unless what precedes it is an abbreviation or an initial. The
# list holds nothing that is also a word a sentence can end on — `no.` is left
# out for that reason, because merging two sentences corrupts every number
# measured over them, and `no.` for `number` is rare in body prose.
SENTENCE_END = re.compile(r"[.!?][\"'’”)\]]*(?=\s|$)")
ABBREVIATION = re.compile(
    r"(?:\b(?:et al|e\.g|i\.e|cf|vs|Fig|Figs|Eq|Ref|approx|ca|Dr|Prof|Mr|Mrs|Ms|St)\.|"
    r"\b[A-Z]\.)$"
)

# A word is a whitespace-delimited token with a letter or digit in it, so a
# standalone dash is punctuation rather than a word.
WORD = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*")

# The connectives that mark a turn. The list is deliberately short and dumb:
# the number it produces is read as a consequence of the em-dash gate forcing
# relation-first rewriting, never as a target to be hit.
# `while` is deliberately absent: in scientific prose it is usually temporal
# ("while the samples incubated"), and this number carries no threshold, so an
# inflated one is a false signal to the reader in the way a spurious `however`
# is. The count errs toward under-reporting.
ADVERSATIVE = re.compile(
    r"\b(?:however|but|yet|although|though|whereas|nevertheless|nonetheless|"
    r"conversely|despite|even so|by contrast|in contrast|in spite of)\b",
    re.IGNORECASE,
)

LONG_SENTENCE = 35

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

    def by_id(self, rung_id):
        for rung in self.rungs:
            if rung.id == rung_id:
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
# the bibliography
# --------------------------------------------------------------------------


class Bibliography:
    """The author's reference library, read from its declared path.

    The render **reads it and never contains it.** A bibliography compiled into
    the generator is the defect this replaces: it makes a key dangle against
    the *script* rather than against the author's library, so the reported
    dangling references were an artefact of the renderer and resolved cleanly
    against the real thing.

    Absence is a legal state, because the library is required by the
    *citations* and not by the renderer: a paper citing nothing has nothing to
    resolve. A paper that does cite gets the same dangling-reference hard error
    it would get for one missing key.
    """

    def __init__(self, path, entries):
        self.path = path
        self.entries = entries

    @property
    def present(self):
        return self.entries is not None

    def entry(self, key):
        return (self.entries or {}).get(key)


def read_bibliography(path):
    return Bibliography(path, parse_bibtex(path.read_text(), path) if path.exists() else None)


def parse_bibtex(text, path):
    """Every entry's key and fields, in file order.

    Only what resolving a citation needs is read. `@string`, `@preamble` and
    `@comment` carry no key and are stepped over; a `%` opening a line is a
    BibTeX comment and is blanked, with its length kept so a diagnostic still
    reports the file's own line numbers.
    """
    text = BIB_LINE_COMMENT.sub(lambda match: " " * len(match.group(0)), text)
    entries = {}
    cursor = 0
    while True:
        match = BIB_ENTRY.search(text, cursor)
        if match is None:
            return entries
        line = _line_of(text, match.start())
        close = _balanced(text, match.end() - 1, path, line)
        cursor = close + 1
        if match.group(1).lower() in BIB_NON_ENTRY:
            continue
        body = text[match.end() : close]
        key, _, fields = body.partition(",")
        key = key.strip()
        if not key:
            raise ParseError(
                "%s: `@%s{` opens an entry with no citation key"
                % (_where(path, line), match.group(1))
            )
        if key in entries:
            # Two entries under one key make every citation of it ambiguous,
            # and silently keeping the last one picks a source on the author's
            # behalf.
            raise ParseError(
                "%s: `%s` is the key of more than one entry"
                % (_where(path, line), key)
            )
        entries[key] = _bib_fields(fields, path, line)


def _balanced(text, open_at, path, line):
    """The offset of the `}` closing the `{` at `open_at`."""
    depth = 0
    cursor = open_at
    while cursor < len(text):
        char = text[cursor]
        if char == "\\":
            cursor += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return cursor
        cursor += 1
    raise ParseError("%s: an entry opens and never closes" % _where(path, line))


def _bib_fields(body, path, line):
    fields = {}
    cursor = 0
    while cursor < len(body):
        if body[cursor] in " \t\r\n,":
            cursor += 1
            continue
        match = BIB_FIELD.match(body, cursor)
        if match is None:
            raise ParseError(
                "%s: expected `field = value` in the entry, found `%s`"
                % (_where(path, line), _collapse(body[cursor : cursor + 20]))
            )
        value, cursor = _bib_value(body, match.end(), path, line)
        fields[match.group(1).lower()] = _bib_text(value)
    return fields


def _bib_value(body, cursor, path, line):
    """One field's raw value, and where it ended. Braced, quoted or bare."""
    while cursor < len(body) and body[cursor] in " \t\r\n":
        cursor += 1
    if cursor < len(body) and body[cursor] == "{":
        close = _balanced(body, cursor, path, line)
        return body[cursor + 1 : close], close + 1
    if cursor < len(body) and body[cursor] == '"':
        close = body.find('"', cursor + 1)
        if close < 0:
            raise ParseError("%s: a quoted value never closes" % _where(path, line))
        return body[cursor + 1 : close], close + 1
    end = body.find(",", cursor)
    end = len(body) if end < 0 else end
    return body[cursor:end], end


def _bib_text(value):
    """A field value as prose: the render is not a LaTeX engine, so this is a
    light touch — the protective braces dropped, and the common accent commands
    dropped with them.

    Nothing else is rewritten. BibTeX's `--` becomes an en dash in a page range
    and only there, because a DOI is the one field that must survive
    byte-exact and DOIs do contain double hyphens.
    """
    value = re.sub(r"\\[`'\"^~=.]\s*", "", value)
    return _collapse(value.replace("{", "").replace("}", ""))


def format_reference(number, key, entry):
    """One numbered reference line.

    Deliberately **style-neutral**: the venue's citation style is a typesetting
    concern downstream, and encoding one here would put paper-specific text in
    the generator — the thing this unit must never hold.
    """
    if entry is None:
        # Unreachable: a key with no entry is a hard error, and neither mode
        # emits under one. Spelled out anyway, because a silent drop here would
        # be a reference list shorter than the numbers pointing into it.
        return "%d. @%s" % (number, key)
    container = next(
        (entry[field] for field in BIB_CONTAINER if entry.get(field)), ""
    )
    if entry.get("volume"):
        container = ("%s %s" % (container, entry["volume"])).strip()
    if entry.get("pages"):
        pages = entry["pages"].replace("--", "–")
        container = "%s:%s" % (container, pages) if container else pages
    if entry.get("year"):
        container = ("%s (%s)" % (container, entry["year"])).strip()
    segments = [
        _authors(entry.get("author", "")),
        entry.get("title", ""),
        container,
        "doi:%s" % entry["doi"] if entry.get("doi") else entry.get("url", ""),
    ]
    # A segment may already end in its own punctuation — an initial does, an
    # abbreviated journal name does, and a title may end in `?` or an ellipsis —
    # so the separator is withheld rather than added and collapsed after, which
    # would eat the ellipsis it was collapsing.
    line = ""
    for part in segments:
        if not part:
            continue
        if line and line[-1] not in ".?!…":
            line += "."
        line = "%s %s" % (line, part) if line else part
    return "%d. %s" % (number, line if line[-1:] in ".?!…" else line + ".")


def _authors(author):
    """BibTeX's `and` separator spelled as `;`, and nothing else changed: an
    author's own name is not the generator's to reformat."""
    return "; ".join(part.strip() for part in re.split(r"\s+and\s+", author) if part.strip())


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


class Annotation:
    """One author-facing annotation, on both axes at once.

    `behaviour` decides what the reader sees — a `HOLE` renders as a
    conspicuous token, a `VENUE_SLOT` as a visible placeholder, a `SILENT` as
    nothing at all. `gate` decides whether it blocks `--submit`. The two are
    independent, which is what lets a verify flag be SILENT and still refuse a
    submission.
    """

    def __init__(self, behaviour, gate, owner, label, origin, line, slot_id=None):
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
        return _where(self.origin, self.line)

    @property
    def token(self):
        """What the reader sees. Uniform across both brace behaviours, so one
        grep finds every gap in a circulated paper."""
        return "⟦%s: %s⟧" % (self.behaviour, self.label)


class Citation:
    """One `@key` written in reader-facing prose, at the position it was
    written.

    The source position is what the check reports, and it is the reason
    citations are collected off the source rather than off the assembled
    document: by assembly time the blocks have been joined and every line
    number is gone.
    """

    def __init__(self, key, origin, line, slot_id=None):
        self.key = key
        self.origin = origin
        self.line = line
        self.slot_id = slot_id

    @property
    def where(self):
        return _where(self.origin, self.line)


class Source:
    """What the source files say, read once.

    Five things come out of one read and travel together from there to the
    gate: the anchored blocks in the order they appear, the prose that landed
    outside every slot, the annotation manifest, the citations, and the
    advisory warnings.
    """

    def __init__(self):
        self.blocks = []
        self.stray = []
        self.annotations = []
        self.citations = []
        self.warnings = []


def parse_source(paths):
    """Read the source into one `Source`.

    One file post-promotion, or every section source pre-promotion — the blocks
    concatenate, and the render orders them by the skeleton rather than by the
    order they were read in.
    """
    source = Source()
    for path in paths:
        _read_one_source(source, path.read_text(), path)
    return source


def scan_source(text, path):
    """Every comment in a source, in order, each paired with the slot it
    anchors — or with `None` when it is an ordinary comment — plus the fenced
    spans the scan skipped.

    Both readers of a source walk this one scan: the render's parser, which
    strips the channel, and the scaffold's split, which keeps it. A grammar
    with two implementations is a grammar that can disagree with itself. The
    fenced spans come back with it because the render's parser reads the brace
    channel off the same text, and it must skip exactly what this scan skipped.

    Parsing is span-based, never line-anchored: an annotation may wrap across
    any number of lines, and in the corpus this design was calibrated on, 13 of
    30 did, one of them over six lines. A line-anchored parser is the thing an
    implementer assumes away.
    """
    fenced = _fenced_spans(text)
    _refuse_unclosed_comment(text, path, fenced)
    _refuse_headings(text, path, fenced)
    return fenced, [
        (match, _anchor_slot_id(match, text, path))
        for match in COMMENT.finditer(text)
        # inside a fence it is literal text, not a comment
        if not _inside(fenced, match.start())
    ]


def _read_one_source(source, text, path):
    """One source file, read into `source`: the annotation channel first, then
    every comment stripped, then what is left split at the anchors."""
    fenced, comments = scan_source(text, path)

    # Braces are read off the text with every comment blanked to same-length
    # whitespace, so a reasoning comment's `{{label}}` join key is not itself
    # an annotation and every offset still points at the real source.
    advisories = []
    masked = _mask_comments(text, fenced)
    spans = _brace_spans(masked, path, fenced, advisories)
    bare = _blank_braces(masked, spans)

    # `bare` is exactly reader-facing prose: every comment and every brace
    # blanked to same-length whitespace, so the two channels an author writes
    # in are invisible here and every offset still points at the real source.
    _refuse_bracket_spans(bare, path, fenced)

    keyed = {}
    current = None
    pending = []
    cursor = 0

    # The trailing `(None, None)` is end of text. A file's tail is the same
    # case as the run-up to a comment — prose to substitute braces into and
    # attribute to the anchor above — so it takes the same code path rather
    # than a second copy of it.
    for match, slot_id in comments + [(None, None)]:
        stop = len(text) if match is None else match.start()
        taken = _chunk(spans, cursor, stop)
        pending.append(_substitute(text, cursor, stop, taken))
        source.annotations.extend(_attach(taken, current, masked, bare, advisories))
        source.citations.extend(_cited(bare, cursor, stop, current, path, fenced))
        if match is None:
            break
        cursor = match.end()
        if slot_id is not None:
            _attribute(_tidy("".join(pending)), current, path, source.stray)
            _close_raw(current, bare, match.start())
            pending = []
            current = Block(slot_id, path, _line_of(text, match.start()))
            current.raw_line = _line_of(text, match.end())
            current.raw_start = match.end()
            source.blocks.append(current)
            continue
        # Every comment is stripped, as a class. Three of them are then read
        # again for the manifest, and the rest are tracked nowhere.
        entry = _read_comment(match, text, path, current, keyed, advisories)
        if entry is not None:
            source.annotations.append(entry)

    _attribute(_tidy("".join(pending)), current, path, source.stray)
    _close_raw(current, bare, len(text))
    _join_reasoning(spans, keyed, path, advisories)
    source.warnings.extend(text for _, text in sorted(advisories))


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
        if len(annotation.label) > LABEL_ADVISORY_CHARS:
            advisories.append(
                (
                    annotation.line,
                    "%s: the label runs to %d characters, over the "
                    "%d-character advisory limit — reasoning belongs in a keyed "
                    "comment beside the brace"
                    % (annotation.where, len(annotation.label), LABEL_ADVISORY_CHARS),
                )
            )
        found.append(annotation)
    return found


def _brace_spans(masked, path, fenced, advisories):
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
                    _brace_annotation(
                        masked, opened_at, offset + 2, path, advisories
                    ),
                )
            )
            opened_at = None
    if opened_at is not None:
        raise ParseError(
            "%s:%d: unclosed brace `{{`" % (path.name, _line_of(masked, opened_at))
        )
    return spans


def _brace_annotation(text, start, end, path, advisories):
    """One brace, read against `{{ [!] [SLOT:] [@owner] <label> }}`.

    The three prefixes appear once each, in that order, and a remainder still
    carrying one of them is a parse error rather than a label that happens to
    start with `!` — because that reading would silently lose the gate bit,
    which is the one thing that decides whether a paper can be submitted.
    """
    line = _line_of(text, start)
    shown = _collapse(text[start + 2 : end - 2])
    where = _where(path, line)
    gate, behaviour, owner, label = _split_prefixes(shown)

    if not label:
        raise ParseError(
            "%s: `{{ %s }}` names no value — a brace names the missing value, "
            "and its reasoning goes in a keyed comment beside it" % (where, shown)
        )
    if label.startswith(("!", "@")) or SLOT_MARK.match(label):
        raise ParseError(
            "%s: `{{ %s }}` — the `!`, `SLOT:` and `@owner` prefixes appear "
            "once each, in that order" % (where, shown)
        )
    if behaviour is None and SLOT_INTENT.match(label):
        # Under the grammar a label opening `slot:` is a perfectly good noun
        # phrase, so this warns rather than refusing: inventing a refusal the
        # grammar does not ask for breaks a paper that never asked for any of
        # this. It still says so, because a mistyped marker would otherwise
        # become a HOLE silently.
        advisories.append(
            (
                line,
                "%s: `{{ %s }}` reads as a HOLE whose label opens `slot:` — if a "
                "venue slot was meant, the marker is `SLOT:`, uppercase, with no "
                "space before the colon" % (where, shown),
            )
        )
    return Annotation(behaviour or HOLE, gate, owner, label, path, line)


def _read_comment(match, text, path, block, keyed, advisories):
    """One stripped comment, read again for the manifest.

    A comment enters the manifest **if and only if** its first non-space
    character is `!` or `@`. That is what keeps the rung, the objection note
    and the section anchors out of a list of outstanding work sent to a
    co-author: nobody owes a rung.

    **Nothing here refuses.** A parse error is for what the source cannot
    express *into reader-facing prose*, and a comment never reaches the reader
    — so a malformed one warns and still enters, where the author will see it.
    The grammar is also thinner than a brace's: `@owner` is free text, and
    `SLOT:` marks a brace, so it is left in the label rather than read.
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
    gate, _, owner, label = _split_prefixes(shown, venue=False)
    if not label:
        # It opened with `!` or `@`, so the rule lists it; there is just
        # nothing after the prefixes to name what is owed.
        advisories.append(
            (
                line,
                "%s: `<!-- %s -->` is in the manifest because it opens with a "
                "prefix, but names nothing after it"
                % (_where(path, line), shown),
            )
        )
        label = shown
    return Annotation(
        SILENT,
        gate,
        owner,
        label,
        path,
        line,
        None if block is None else block.slot_id,
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


def _refuse_bracket_spans(bare, path, fenced):
    """Outside every comment and every fence, **every bracket character in
    prose must belong to a citation group.** Anything else is a parse error.

    The rule is stated over the characters rather than over `[…]` spans,
    because a span rule leaks twice: the outer pair of `[[@smith2020]]` is not
    part of any span, and an unclosed `[` never forms one at all — so both
    reach reader-facing prose as free text.

    The permissive form — *a `[…]` span is legal iff it contains an `@key`* —
    was rejected for the same reason one layer up: it admits
    `[verify this @smith2020]`, which renders as *(verify this Smith 2020)*.
    That is a free-text channel into reader-facing prose, which is the failure
    class this whole clause exists to close, re-opened inside the clause
    closing it.

    The refusal costs nothing on real text. Outside comments the calibration
    corpus held **70 bracket spans: 40 citations, 30 author-facing annotations,
    and zero other legitimate uses** — no markdown link, no reference link, no
    footnote in 74 KB of biomedical prose.
    """
    groups = [
        (match.start(), match.end())
        for match in CITATION_GROUP.finditer(bare)
        if not _inside(fenced, match.start())
    ]
    for match in BRACKET.finditer(bare):
        if _inside(fenced, match.start()) or _inside(groups, match.start()):
            continue
        raise ParseError(
            "%s: `%s` is not a citation group — brackets group `@key` "
            "references separated by `; ` and contain nothing else"
            % (_where(path, _line_of(bare, match.start())), _quote_bracket(bare, match.start()))
        )


def _quote_bracket(bare, start):
    """The malformed span, as much of it as there is: to its closing bracket
    when it has one, and to the end of its paragraph when it does not."""
    end = bare.find("\n\n", start)
    end = len(bare) if end < 0 else end
    close = bare.find("]", start + 1)
    return _collapse(bare[start : close + 1 if 0 <= close < end else end])


def _cited(bare, start, end, block, path, fenced):
    """Every citation key written in one chunk of prose, in source order.

    A `@fig:` identifier shares the namespace and is not a citation: the
    bibliography is never asked about it, and `figures and panels` owns
    resolving it.
    """
    found = []
    for match in REFERENCE.finditer(bare, start, end):
        if _inside(fenced, match.start()) or match.group(1).startswith(FIGURE_PREFIX):
            continue
        found.append(
            Citation(
                match.group(1),
                path,
                _line_of(bare, match.start()),
                None if block is None else block.slot_id,
            )
        )
    return found


def _blank_braces(masked, spans):
    """The text with every brace blanked to same-length whitespace too.

    The direction is committed by the **claim**, so the scan for it must not
    see the labels — and a label carrying a `!` gate bit would otherwise read
    as the end of a sentence.
    """
    return _blank_spans(masked, [(start, end) for start, end, _ in spans])


def _collapse(text):
    """Trimmed, with internal whitespace collapsed. Labels compare after this,
    so a brace that wraps six lines is one label and not six."""
    return re.sub(r"\s+", " ", text).strip()


def _split_prefixes(label, venue=True):
    """A collapsed label split into `[!] [SLOT:] [@owner] <label>`.

    One implementation, because the token order is **one fact**: the brace
    parser, the comment parser and the join key all read it, and this design
    has twice held that two artifacts recording one fact is how they drift.

    It strips and reports; it refuses nothing — each caller decides what is
    legal in its own channel. `venue=False` is the comment channel, where
    `SLOT:` is not part of the grammar and so stays in the label rather than
    being read off it and lost.
    """
    gate = label.startswith("!")
    if gate:
        label = label[1:].lstrip()

    behaviour = None
    mark = SLOT_MARK.match(label) if venue else None
    if mark:
        behaviour = VENUE_SLOT
        label = label[mark.end() :].lstrip()

    owner = None
    named = OWNER.match(label)
    if named:
        owner = named.group(0)
        label = label[named.end() :].lstrip()

    return gate, behaviour, owner, label


def _join_key(label):
    """A label as a join key: collapsed, and stripped of all three prefixes."""
    return _split_prefixes(_collapse(label))[3]


def _where(path, line):
    """One source position, spelled the one way every diagnostic spells it."""
    return "%s:%d" % (path.name, line)


def _direction(bare, start, end):
    """The directional word committed in the sentence resting on this hole.

    Six of seven gating annotations in the corpus sat under a committed
    direction written before the value existed — and deletion being the only
    closure means the obligation vanishes the moment the value is filled. So
    the direction is named while the hole is still open, on the hole's own
    manifest entry, inheriting the hole's gate bit and adding none.
    """
    sentence = _sentence_around(bare, start, end)
    found = DIRECTIONAL.search(sentence)
    return found.group(0) if found else None


def _sentence_around(bare, start, end):
    """The sentence a brace sits in, minus the brace itself — the direction is
    committed by the claim, never by the label.

    `bare` is the text with braces blanked as well as comments, so a label's
    own `!` gate bit cannot read as the end of a sentence.
    """
    left = 0
    for match in SENTENCE_END.finditer(bare, 0, start):
        left = match.end()
    paragraph = bare.rfind("\n\n", 0, start)
    if paragraph >= 0:
        left = max(left, paragraph + 2)

    right = len(bare)
    found = SENTENCE_END.search(bare, end)
    if found:
        right = found.end()
    paragraph = bare.find("\n\n", end)
    if paragraph >= 0:
        right = min(right, paragraph)
    return bare[left:start] + " " + bare[end:right]


def _block_alone(masked, start, end):
    """Nothing but whitespace between the brace and the blank line on either
    side. On the whole corpus that shape is always a venue slot — which is
    strong evidence and not the definition, so it warns."""
    left = masked.rfind("\n\n", 0, start)
    left = 0 if left < 0 else left + 2
    right = masked.find("\n\n", end)
    right = len(masked) if right < 0 else right
    return not (masked[left:start].strip() or masked[end:right].strip())


def _close_raw(block, bare, end):
    """A block's prose runs from its own anchor to the next one.

    It is sliced out of `bare` — every comment and every brace already blanked
    to same-length whitespace — because that is the one artifact in this unit
    that means *reader-facing prose*. Re-deriving it with a second pattern is
    how two implementations of one fact come to disagree.
    """
    if block is not None:
        block.raw = bare[block.raw_start : end]


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


def _mask_comments(text, fenced=()):
    """Blank every comment's content to same-length whitespace, keeping the
    newlines, so a scan over the result still reports the source's own line
    numbers and offsets. A fenced comment is literal text, so it survives.

    `fenced` defaults to none for a caller holding a fragment rather than a
    whole file, where a whole file's fence offsets would not line up anyway.
    """

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
        for match, slot_id in scan_source(text, path)[1]
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
    scoped = _blank_spans(raw, _fenced_spans(raw))
    for pattern in (TABLE_ROW, CITATION_GROUP):
        scoped = pattern.sub(_blank_match, scoped)
    return scoped


def _blank_spans(text, spans):
    """Blank the given character ranges of `text`."""
    for start, end in reversed(spans):
        text = text[:start] + _blanked(text[start:end]) + text[end:]
    return text


def _blank_match(match):
    """Blank what a pattern matched, for `re.sub`."""
    return _blanked(match.group(0))


def _blanked(text):
    """The same text, same length, same newlines, no content.

    Length and newlines are what make a reported line number the author's own,
    so nothing here ever deletes a character.
    """
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
    """The words of one sentence, as `WORD` above defines a word."""
    return WORD.findall(sentence)


def _line_in(block, scoped, offset):
    """The source line an offset into a block's prose sits on."""
    return block.raw_line + _line_of(scoped, offset) - 1


def _locations(spots):
    """`(file, line)` pairs as the report prints them.

    Bare line numbers over one source file, and file-qualified over several —
    pre-promotion the sections are still separate files, where a bare `line 3`
    could mean any of them. Each location prints once: the count already
    carries the multiplicity, and a line named twice reads as two places.
    """
    if not spots:
        return ""
    names = set(name for name, _ in spots)
    distinct = []
    for spot in spots:
        if spot not in distinct:
            distinct.append(spot)
    if len(names) == 1:
        lines = ", ".join(str(line) for _, line in distinct)
        return " (%s %s)" % ("line" if len(distinct) == 1 else "lines", lines)
    return " (%s)" % ", ".join("%s:%d" % spot for spot in distinct)


def _plural(count, noun):
    return "%d %s%s" % (count, noun, "" if count == 1 else "s")


# --------------------------------------------------------------------------
# the check registry
# --------------------------------------------------------------------------


class Verdict:
    """One row's outcome, and what it prints.

    Three of the four shapes are verdicts — `PASS`, `FAIL`, `SKIPPED` — and the
    fourth is a measurement, which is why a subclass may print a number where a
    verdict word would otherwise go.
    """

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
    return Verdict.over(slot_integrity_problems(paper.skeleton, paper.blocks, paper.stray))


def check_citation_entries(paper):
    """Every cited key has an entry in the author's library.

    **The check is asymmetric, and the asymmetry is the point.** A key with no
    entry is a dangling reference — a token pointing at nothing, structurally
    identical to a figure name absent from the roster, so it takes that tier. A
    library entry this document does not cite gets **no check at all**: a
    figure roster is a manifest of this document's objects, but a bibliography
    is a library, and over-provisioning is its normal state. Transposing the
    roster's symmetry here would hard-error a real paper forever over entries
    its author deliberately kept and deliberately did not cite, which makes the
    gate noisy and therefore skippable.

    An orphaned entry in the *rendered* list needs no check either: the list is
    built from the cited keys, so it is impossible by construction.

    Whole-document only: whether a key resolves is a fact about the document,
    and first-mention order is too.
    """
    if not paper.citations:
        return Verdict.over([])
    if not paper.bibliography.present:
        return Verdict.over(["no bibliography at `%s`" % BIB_PATH])
    problems = []
    dangling = set()
    for citation in paper.citations:
        if citation.key in dangling or paper.bibliography.entry(citation.key):
            continue
        dangling.add(citation.key)
        problems.append("%s `@%s`" % (citation.where, citation.key))
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
        if _originates(paper, unit) and unit.children:
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


# --------------------------------------------------------------------------
# the chain walk
#
# A graph query over the ladder's declared relations, never a reading of the
# prose — and it reads the **declared relation** and never the section type: a
# Methods unit may carry the paper's load-bearing claim, and a walk that
# expected an introduction to open every debt would false-fail on exactly that
# paper.
#
# Debts are opened and closed by **units**. A rung keys to one unit, so there
# is no debt edge inside a unit and nothing to check inside one; a rung naming
# a child slot is the `unit / rung pairing` row's finding, not this walk's.
#
# This is the mechanical half only. Whether prose that *claims* to close a debt
# actually closes it is judgement, and belongs to the review.
# --------------------------------------------------------------------------


def _debt_edges(spine):
    """Who opens each debt and who closes it — the join every row of the walk
    makes, so it is made once.

    A debt is identified by its id and never by its text: the id is the join
    key the ladder declares, and matching on the statement instead would leave
    two innocent spellings of one debt silently orphaning the edge.
    """
    openers = {}
    closers = {}
    for rung in spine.rungs:
        for debt, declared_closer, _statement in rung.opens:
            openers.setdefault(debt, []).append((rung, declared_closer))
        for debt in rung.closes:
            closers.setdefault(debt, []).append(rung)
    return openers, closers


def check_chain_bookkeeping(paper):
    """Every declared debt opened exactly once, closed exactly once, and none
    dangling at the end.

    Submit-gating: the render is faithful — the document says what the source
    says — and it is the argument that is unfinished, so an unclosed debt still
    circulates and only `--submit` refuses.
    """
    problems = []
    known = set(rung.id for rung in paper.spine.rungs)
    openers, closers = _debt_edges(paper.spine)

    for rung in paper.spine.rungs:
        for restated in rung.restates:
            if restated not in known:
                problems.append(
                    "%s restates %s, which is not a rung in this ladder"
                    % (rung.id, restated)
                )

    for debt in sorted(openers, key=_id_number):
        opening = [rung.id for rung, _declared in openers[debt]]
        closing = [rung.id for rung in closers.get(debt, [])]
        if len(opening) > 1:
            problems.append("`%s` is opened %s" % (debt, _repeated_by(opening)))
        if not closing:
            problems.append(
                "`%s` is opened by %s and never closed" % (debt, opening[0])
            )
        elif len(closing) > 1:
            problems.append("`%s` is closed %s" % (debt, _repeated_by(closing)))
        for _rung, declared_closer in openers[debt]:
            if declared_closer not in known:
                problems.append(
                    "`%s` declares %s closes it, which is not a rung in this ladder"
                    % (debt, declared_closer)
                )
            elif closing and declared_closer not in closing:
                problems.append(
                    "`%s` declares %s closes it, but %s %s"
                    % (
                        debt,
                        declared_closer,
                        _listed(closing),
                        "does" if len(closing) == 1 else "do",
                    )
                )

    for debt in sorted(closers, key=_id_number):
        if debt not in openers:
            for rung in closers[debt]:
                problems.append("%s closes `%s`, which no rung opens" % (rung.id, debt))

    return Verdict.over(problems)


def check_debt_precedence(paper):
    """Every debt is opened in a unit no later than the unit that closes it,
    read against the **skeleton's** order.

    The skeleton's order is the document's reading order, and the reader is who
    the rule protects: close a debt before the unit that opens it, and the
    payoff arrives before the promise. Reading order and argument order are
    different relations and may disagree, so the ladder's own order is not what
    this reads. `restates` carries no precedence — an abstract restates a rung
    the document has not reached yet, which is what an abstract is for.
    """
    order = dict((unit.id, index) for index, unit in enumerate(paper.skeleton.units))
    openers, closers = _debt_edges(paper.spine)

    problems = []
    for debt in sorted(openers, key=_id_number):
        closing = closers.get(debt, [])
        if len(openers[debt]) != 1 or len(closing) != 1:
            continue  # a debt opened or closed by nobody or by two is bookkeeping's
        opened_in = openers[debt][0][0].unit
        closed_in = closing[0].unit
        if opened_in not in order or closed_in not in order:
            continue  # a rung naming no unit is the pairing row's
        if order[opened_in] > order[closed_in]:
            problems.append(
                "`%s` is opened in `%s` and closed in `%s`, which the skeleton "
                "reads first" % (debt, opened_in, closed_in)
            )
    return Verdict.over(problems)


def _id_number(identifier):
    """`D10` sorts after `D2`, so a report's order is the ladder's own."""
    return int(identifier[1:])


def _repeated_by(rung_ids):
    """`twice, by R1 and R2` — how many rungs did it, and which."""
    count = "twice" if len(rung_ids) == 2 else "%d times" % len(rung_ids)
    return "%s, by %s" % (count, _listed(rung_ids))


def _listed(items):
    """`R1, R2 and R3` — an English list, so a row reads as a sentence."""
    if len(items) == 1:
        return items[0]
    return "%s and %s" % (", ".join(items[:-1]), items[-1])


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
        offset = scoped.find(EM_DASH)
        while offset >= 0:
            spots.append((block.origin.name, _line_in(block, scoped, offset)))
            offset = scoped.find(EM_DASH, offset + 1)
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
    """Whether this unit opens a debt, as the ladder declares it."""
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

    Every opening used more than once prints, however far down the order,
    because concentration is the thing being read and a moderately used
    opening is exactly what the audit's 6% was. The openings used once carry
    no concentration, so they arrive as their own count rather than by name —
    which keeps the row bounded without hiding a repeated opening behind a
    rank cut.
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
    shown = ["%s %d" % pair for pair in ranked if pair[1] > 1]
    once = [opening for opening, count in ranked if count == 1]
    if once:
        shown.append("%d used once" % len(once))
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


# --------------------------------------------------------------------------
# the locality test
#
# An amendment touching only the amending session's own slot is immediate; one
# touching another slot, or the order or levels of the tree, files a `task`
# ticket that blocks the draft ticket. See `SKELETON-FORMAT.md`, which holds
# the rule and the two lists.
#
# The render never sees a proposed amendment, so what it reports is what the
# two files fix before one is proposed: the tree an amendment would move, and
# the coupling that decides which side of the rule a move falls on.
# --------------------------------------------------------------------------


def report_locality(paper):
    """The tree an amendment moves, and the edges that tie one unit to another.

    A unit's own subtree is its to amend; the tree's order and levels are
    nobody's alone; and every edge leaving a unit — a debt it opens that
    another unit closes, a rung in another unit it restates — is a tie an
    amendment cannot move on its own.

    It reports and never gates, because a coupled argument is what a ladder
    *is*, not a defect in one.
    """
    edges = []
    _openers, closers = _debt_edges(paper.spine)
    for rung in paper.spine.rungs:
        for debt, _declared_closer, _statement in rung.opens:
            for other in closers.get(debt, []):
                if other.unit != rung.unit:
                    edges.append("`%s` %s→%s" % (debt, rung.unit, other.unit))
        for restated in rung.restates:
            other = paper.spine.by_id(restated)
            if other is not None and other.unit != rung.unit:
                edges.append("%s restates %s" % (rung.unit, other.unit))

    tree = "%s, %s" % (
        _plural(len(paper.skeleton.units), "unit"),
        _plural(len(paper.skeleton.slots), "slot"),
    )
    if not edges:
        return Number("%s, no cross-unit edge" % tree)
    return Number(
        "%s, %s (%s)"
        % (tree, _plural(len(edges), "cross-unit edge"), "; ".join(edges))
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
#   parse    brace grammar               (built)
#   parse    citation group              (built)
#   parse    reference literals          figures and panels
#   hard     slot integrity              (built; becomes slot / roster
#                                        integrity when figures land the
#                                        roster half of it)
#   hard     citation → bib entry        (built)
#   hard     unit / rung pairing         (built)
#   hard     originating slot children   (built)
#   gating   annotations (gating)        (built)
#   gating   unfilled skeleton slot      (built)
#   gating   bare holes                  residue lints
#   gating   workflow phrases            residue lints
#   gating   chain bookkeeping           (built)
#   gating   debt precedence             (built)
#   reported em dashes                   (built)
#   reported brief-to-prose overlap      overlap instrument
#   reported single-sentence body …      (built; paragraph order joins it with
#                                        the overlap instrument)
#   reported adversative ratio           (built)
#   reported subject openings            (built)
#   reported sentence length             (built)
#   reported locality test               (built)
#   reported supersession diff           supersession diff
#
# The parse-tier rows built here have no entry below: a parse error means
# nothing ran, so the table is absent rather than carrying their verdicts.
#
# A row name may be a function of the paper, for a row whose name carries the
# threshold the number was measured against.
REGISTRY = [
    ("slot integrity", HARD, DOCUMENT, check_slot_integrity),
    ("citation → bib entry", HARD, DOCUMENT, check_citation_entries),
    ("unit / rung pairing", HARD, None, check_unit_rung_pairing),
    ("originating slot children", HARD, None, check_originating_slot_children),
    ("annotations (gating)", GATING, None, check_gating_annotations),
    ("unfilled skeleton slot", GATING, None, check_unfilled_skeleton_slot),
    ("chain bookkeeping", GATING, DOCUMENT, check_chain_bookkeeping),
    ("debt precedence", GATING, DOCUMENT, check_debt_precedence),
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
    ("locality test", REPORTED, DOCUMENT, report_locality),
]

# The three Tier 4 diagnostics are whole-document only, and the em-dash count
# is not: the count blocks a drafting seam, and a seam is one section. The
# three are reported together over the finished piece, because a rhythm number
# published per seam is a number a drafter tunes at the seam — which is the
# behaviour `no threshold` exists to prevent.

# The parse-tier rows print `PASS` whenever a table prints at all, because a
# parse-tier failure suppresses the table.
PARSE_ROWS = [
    "skeleton / spine grammar",
    "source grammar",
    "brace grammar",
    "citation group",
]


# --------------------------------------------------------------------------
# the render
# --------------------------------------------------------------------------


class Paper:
    """One paper at one granularity: the two files, the source, and the slots
    in scope."""

    def __init__(
        self, skeleton, spine, bibliography, source, granularity, unit,
        em_dash_threshold,
    ):
        self.skeleton = skeleton
        self.spine = spine
        self.bibliography = bibliography
        self.blocks = source.blocks
        self.stray = source.stray
        self.annotations = source.annotations
        self.citations = source.citations
        self.warnings = source.warnings
        self.granularity = granularity
        self.unit = unit
        self.em_dash_threshold = em_dash_threshold
        self.slots = skeleton.subtree(unit) if unit is not None else skeleton.slots
        self.units = [unit] if unit is not None else skeleton.units
        self._prose = {}
        for block in self.blocks:
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
    numbers = {}
    for slot in paper.slots:
        out.append("\n%s %s\n" % ("#" * slot.level, slot.heading))
        prose = paper.prose_for(slot)
        if not prose and not slot.children:
            prose = _hole("prose for %s" % slot.id)
        if prose:
            if paper.granularity == DOCUMENT:
                prose = _resolve_citations(prose, numbers)
            out.append("\n%s\n" % prose)
    out.append(_reference_list(paper, numbers))
    return "".join(out)


def _resolve_citations(prose, numbers):
    """Every citation token in one slot's prose, replaced by its number.

    Numbers are assigned **by first mention in the assembled document**, which
    is why `numbers` is carried across the slots in render order rather than
    rebuilt per slot. A drafting session writes a key and never a number, so a
    number it might have written wrong — wrong-but-valid, and invisible to
    every check — is a thing it cannot type.

    Three things are stepped over. A gap token's label is author-facing text
    the render has already substituted into the prose, so a key inside one is
    not a citation of this document. Inside a fence nothing is parsed at all,
    here as everywhere else — a source showing the syntax is showing it, not
    using it. And a `@fig:` identifier belongs to the figure namespace, which
    resolves elsewhere.

    A mixed group resolves **per key, not per token**: the citations take their
    numbers and the figure names stay visible. Leaving the whole token verbatim
    would drop a real citation out of the reference list while the gate went on
    demanding an entry for it.
    """
    fenced = _fenced_spans(prose)

    def resolve(match):
        token = match.group(0)
        if match.group("gap") or _inside(fenced, match.start()):
            return token
        keys = REFERENCE.findall(token)
        cited = [key for key in keys if not key.startswith(FIGURE_PREFIX)]
        if not cited:
            return token
        for key in cited:
            numbers.setdefault(key, len(numbers) + 1)
        if len(cited) == len(keys):
            return "[%s]" % ",".join(str(numbers[key]) for key in keys)
        return "[%s]" % "; ".join(
            "@%s" % key if key.startswith(FIGURE_PREFIX) else str(numbers[key])
            for key in keys
        )

    return CITATION_TOKEN.sub(resolve, prose)


def _reference_list(paper, numbers):
    """The reference list, as a function of the cited keys.

    Nothing else can reach it, so an orphaned entry is impossible by
    construction rather than something a check has to look for. It is absent
    entirely when nothing is cited, and at `--section` granularity, where no
    key has a number because first-mention order is a whole-document fact.
    """
    if not numbers:
        return ""
    level = min(unit.level for unit in paper.skeleton.units) if paper.skeleton.units else 2
    lines = ["\n%s References\n\n" % ("#" * level)]
    for key, number in sorted(numbers.items(), key=lambda item: item[1]):
        lines.append("%s\n" % format_reference(number, key, paper.bibliography.entry(key)))
    return "".join(lines)


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

    Only the tiers that can gate have a bucket, so a reported row's FAIL lands
    nowhere at all. That is the mechanism by which it cannot reach the exit
    code: not a rule the caller has to honour, but a bucket that is not there.
    """
    rows = [(name, Verdict(PASS)) for name in PARSE_ROWS]
    failed = {HARD: [], GATING: []}
    for name, tier, scope, check in REGISTRY:
        label = name(paper) if callable(name) else name
        verdict = (
            Verdict.skipped()
            if scope == DOCUMENT and paper.granularity == SECTION
            else check(paper)
        )
        rows.append((label, verdict))
        if verdict.kind == FAIL and tier in failed:
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

    source_path = Path(args.source)
    granularity = SECTION if args.section is not None else DOCUMENT

    try:
        root = find_paper_root(source_path, Path(args.paper) if args.paper else None)
        if args.scaffold:
            # The scaffold writes the source rather than reading a finished
            # one, so it neither reads the ladder — the gate's input, with no
            # use here — nor runs a check: it emits no document to be wrong.
            # It is always one unit, so `--section` names that unit here rather
            # than choosing a granularity.
            return scaffold(
                source_path, parse_skeleton(root / "skeleton.md"), args.section
            )
        paths = source_paths(source_path)
        skeleton = parse_skeleton(root / "skeleton.md")
        spine = parse_spine(root / "spine.md")
        bibliography = read_bibliography(root / BIB_PATH)
        source = parse_source(paths)
        unit = None
        if granularity == SECTION:
            unit = derive_unit(skeleton, source.blocks, args.section)
    except ParseError as error:
        sys.stderr.write("render-paper: parse error — %s\n" % error)
        return EXIT_PARSE
    except HardError as error:
        sys.stderr.write("render-paper: %s\n" % error)
        return EXIT_HARD

    paper = Paper(
        skeleton, spine, bibliography, source, granularity, unit,
        args.em_dash_threshold,
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
