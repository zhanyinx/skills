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
import io
import re
import subprocess
import sys
import tarfile
import tempfile
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

# The four verdicts, and nothing else. No single-word verdict is emitted
# anywhere: one word cannot carry checked-and-fine against never-looked.
PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
SKIPPED = "SKIPPED — OUT OF SCOPE AT THIS GRANULARITY"

# A fifth outcome, which is not a verdict at all: the row prints a number.
NUMBER = "number"

DOCUMENT = "document"
SECTION = "section"

# The three modes that render or gate. `--scaffold` writes the source and
# returns before a gate exists, so it is not one of them.
CIRCULATE = "circulate"
SUBMIT = "submit"
CHECK = "check"

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

# A figure lives in the same namespace behind the same `@`, and is never a
# citation key: the bracket grammar accepts it, and the bibliography is never
# asked about it.
FIGURE_PREFIX = "fig:"

# The rendered forms are pandoc-crossref's own — `fig. 1`, and `fig. 1 (a)` for
# a panel. `K3`'s winning argument is that an existing tool already resolves
# name → number, so inventing a second spelling for the same relation is how
# the two come apart. Which word a name takes is a property of its **roster
# row**, never of the token: promoting a figure to supplementary is a one-line
# roster edit at zero prose edits, and that is the property names exist for.
# The venue's own typography is a downstream concern, as the citation style is.
FIGURE_LABEL = {"figure": "fig.", "table": "tbl.", "supplementary": "suppl."}
ROSTER_KINDS = tuple(FIGURE_LABEL)

# The legend's declaration block: one section, one entry per panel, and the
# entry order is the lettering. The prefix is required on a declaration for the
# same reason it is required on a reference — one namespace, one token class.
PANEL_SECTION = "Panels"
PANEL_DECLARATION = re.compile(r"^@(%s%s)(?:\s|$)" % (FIGURE_PREFIX, IDENTIFIER))

# The three literals the source cannot express, all of them stale identifiers
# the render would have no way to correct.
#
# A parenthesised letter or letter-range is syntactically clean prose, so
# nothing else refuses it — and it is the artifact a figure split re-letters
# *first*. On the real split this design was calibrated against, a frozen
# draft's `Fig 2c–d` **did not dangle; it changed meaning**, which is the one
# failure no dangling-reference check can catch.
PANEL_LETTER = re.compile(r"\(\s*[A-Za-z](?:\s*[-–—,;]\s*[A-Za-z])*\s*\)")

# `Fig`+number(+letter). **The figure spellings only, and deliberately not the
# table or supplementary ones**, even though the roster addresses all three
# kinds through one namespace: `table` and its relatives are ordinary nouns that
# take a measurement — *a table 1 mm thick*, *the water table 12 m below* — so a
# refusal over them fires on prose that references nothing. `fig` and `figure`
# before a numeral have no such reading.
#
# The defect is not lost with them. A stale `Table 1` means the roster name that
# table carries is referenced nowhere, which is a hard error in both modes; it
# is reported one row later and less precisely, which is the price of a pattern
# with no false positives.
NUMBERED_LITERAL = re.compile(
    r"\b(?:fig|figs|figure|figures)\b\.?\s*\d+[a-z]?", re.IGNORECASE
)

# A name whose last hyphen-separated segment is a single letter is a panel
# letter wearing a name — `@fig:panel-b` — which is the stale identifier a
# stable name exists to remove, merely spelled inside the namespace. Refused
# wherever a name is written: in prose, in a legend's declaration block, and in
# the roster, because one predicate with three call sites cannot disagree with
# itself about what a name may say.
#
# Both cases, because the three call sites do not agree on case: a roster name
# and a panel declaration are `SLOT_ID`, which is lowercase, but a **reference**
# is an `IDENTIFIER`, which is not. A lowercase-only pattern would refuse
# `@fig:panel-b` everywhere and let `@fig:panel-B` through — and let it through
# silently at `--section`, where the roster row that would otherwise have caught
# it is out of scope.
POSITIONAL_NAME = re.compile(r"(?:^|-)[A-Za-z]$")

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

# The supersession diff's two declared conventions. `DRAFTS_DIR` is where a
# unit's prose lives before promotion, so it is where the old side of a
# post-promotion revision is found; it is named here because this is the only
# check that looks for it.
#
# The drop bar is **a constant and not a caller's option**, unlike the em-dash
# threshold. The row cannot gate, so a knob would buy an effort nothing it
# cannot already have by reading the two counts the row always prints — and one
# more input on a revision's interface is one more thing to mistake for a
# keep-list.
GIT = "git"
DRAFTS_DIR = "drafts"
SUPERSESSION_DROP_PERCENT = 25
RENDERED_HEADING = re.compile(r"^#{1,6} .*$", re.MULTILINE)

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
# which spans carry a key. `CITATION_GROUP` is defined once, with the citation
# surface.

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

# The brief's six zone headings, of which exactly two are reader-facing — the
# only zones whose content may legitimately appear in the prose.
ARGUMENT = "Argument"
INVENTORY = "Inventory"
READER_FACING_ZONES = (ARGUMENT, INVENTORY)
BRIEF_ZONES = READER_FACING_ZONES + (
    "Must not claim",
    "Sheds",
    "Verify before prose",
    "Sources",
)

# The ladder line is bookkeeping, not something the prose must convey: it names
# the unit's relation to the rung above it, and a drafter copying it is copying
# a relation, not lifting a claim.
RELATION_LINE = re.compile(r"^(rung|closes|opens|restates)\s*:", re.IGNORECASE)

# The punctuation that closes a word off, which is what separates an inventory
# item's final plural noun from a predication's verb.
CLOSING = ",;:.!?)]\"”"

# A shared run this long is a phrase somebody moved, not a coincidence of
# grammar. The corpus's own shortest transcribed span — *illumination
# correction suppresses tile-boundary seams* — is five words, and its expected
# spans (`MIT`, `scale bar required`, `tile-boundary crop, before/after BaSiC`)
# are all shorter, so the floor separates them before either instrument runs.
PHRASE_WORDS = 5
QUOTE_WIDTH = 56

# Function words carry no phrasing, so a run made of nothing else is grammar
# rather than transcription.
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

# The finite forms a finite verb can take without ambiguity. Every one is a
# closed-class word, so the list is complete rather than a sample, and it needs
# no extension per paper — which it must not have, since paper-specific text in
# the renderer is what this unit is forbidden to hold.
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

# The two residue lints. Both catch **the unmarkable residue**: unfinished text
# that is grammatical reader-facing prose, so no bracket-stripping can see it.
# Both are short, dumb and conservative, which is what keeps the renderer
# paper-agnostic — there is no paper's name, no section of one, and no phrase
# only one manuscript would contain in either.
#
# `G3`'s bare-hole token list. It scored **zero hits** across all thirteen
# section drafts and the mechanical baseline — zero false positives in 74 KB of
# biomedical prose — and **two hits** in the hand-revised manuscript, both
# inside reader-facing claims. That is a measurement made once on a corpus held
# outside this repo, not something the tests re-run; what they re-run is the
# property it was evidence for. Both hits are why the tier is submit-gating
# rather than advisory: each hole sits in a sentence that asserts something, so
# stripping it silently would convert a flagged gap into an unsupported claim.
#
# Word-bounded, because biomedical prose is full of near misses — `TKI` is a
# tyrosine kinase inhibitor, `TBX21` a gene, `TBS` a buffer. Case-sensitive,
# because every token on the list is a placeholder by convention.
BARE_HOLE = re.compile(r"\bXX+\b|\bTBD\b|\bTK\b|\bFIXME\b|\?{3,}")

# `C4`'s workflow-phrase lint. The corpus carried six *"is a submission-readiness
# item"* sentences inside a section the reader reads, and no bracket-based check
# could see one of them.
WORKFLOW_PHRASE = re.compile(
    r"submission-readiness|to be confirmed|\bTODO\b|note to self|"
    r"\bwe should\b|\bpending\b",
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
                if kind not in ROSTER_KINDS:
                    raise ParseError(
                        "%s: `%s` is not a roster kind (%s)"
                        % (where, kind, ", ".join(ROSTER_KINDS))
                    )
                if not SLOT_ID.match(name):
                    raise ParseError(
                        "%s: `%s` is not a name (lowercase, digits, hyphens)"
                        % (where, name)
                    )
                _refuse_positional_name(name, where)
                if not legend:
                    raise ParseError(
                        "%s: `%s` has no legend path — a roster row names the "
                        "file that declares the object's panels, and the file "
                        "may be written later" % (where, name)
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
# the figure namespace
# --------------------------------------------------------------------------


class Figures:
    """This document's objects in **one flat namespace**: every roster name,
    and every panel its legends declare.

    A panel is not a new kind of object — it is a figure that lives inside
    another figure — so it is referenced by the same `@fig:name` token and
    looked up in the same table. **Parentage is carried by containment, never
    by syntax:** a panel's parent is the roster row whose legend declares it,
    which is why there is no `@fig:parent:panel` form and no parent column in
    the roster.

    Numbers are handed out **as `resolve` is called**, and the render calls it
    while walking the assembled document in skeleton order — so first-mention
    order is a property of that one walk rather than of a second traversal that
    could disagree with it. Letters are **not** handed out: a panel's letter is
    fixed by its position in the legend's declaration block before any prose is
    read. That asymmetry is the whole design, and it has a physical cause — a
    figure number appears only in the rendered text, while a panel letter
    appears in the text **and in the artwork**, and a render can renumber prose
    but cannot repaint a figure.
    """

    def __init__(self, roster, panels=()):
        self.kind = {}
        self.parent = {}
        self.letter = {}
        for kind, name, _ in roster:
            self.kind[name] = kind
            self.parent[name] = name
        for figure, declared in panels:
            for index, name in enumerate(declared):
                self.parent[name] = figure
                self.letter[name] = _letter(index)
        self._numbers = {}
        self._sequences = {}

    def figure_for(self, name):
        """The roster row `name` belongs to — itself for a roster name, its
        containing figure for a panel, `None` for a name this document does not
        carry.

        Containment lives here rather than at the call sites, because *which
        object does this name belong to* is the one question the namespace
        exists to answer.
        """
        return self.parent.get(name)

    def known(self, name):
        return self.figure_for(name) is not None

    def resolve(self, name):
        """The rendered form of one reference, or `None` for a name this
        document does not carry.

        An unknown name is a hard error the gate has already reported by the
        time anything is emitted, so this leaves the token verbatim rather than
        holding a second opinion about the tier.
        """
        figure = self.figure_for(name)
        if figure is None:
            return None
        kind = self.kind[figure]
        if figure not in self._numbers:
            # One sequence per kind: a document numbers its figures and its
            # tables independently, and every venue expects that.
            self._sequences[kind] = self._sequences.get(kind, 0) + 1
            self._numbers[figure] = self._sequences[kind]
        rendered = "%s %d" % (FIGURE_LABEL[kind], self._numbers[figure])
        if name == figure:
            return rendered
        return "%s (%s)" % (rendered, self.letter[name])


def read_figures(root, skeleton):
    """This document's objects, read once: the roster, and the panels every
    legend it names declares.

    The namespace is assembled here because this is the only place that holds
    the roster **and** every legend at once, and a collision is a fact about
    the pair rather than about either one.
    """
    declared = []
    # Every roster name is claimed before any legend is read, so a collision is
    # caught whichever of the two the reader meets first: seeding lazily would
    # let a panel take the name of a figure declared further down the roster.
    where = dict((name, "the roster") for _, name, _ in skeleton.roster)
    for _, name, legend in skeleton.roster:
        panels = parse_legend(root / legend)
        for panel in panels:
            if panel in where:
                raise ParseError(
                    "%s: `@fig:%s` is declared here and already named in %s — "
                    "a figure and a panel share one flat namespace, so a name "
                    "belongs to exactly one object"
                    % (legend, panel, where[panel])
                )
            where[panel] = legend
        declared.append((name, panels))
    return Figures(skeleton.roster, declared)


def parse_legend(path):
    """The panel names one legend declares, in **declaration order**.

    A legend is the first draft artifact carrying machine-read structure, and
    this block is the whole of it: `## Panels`, one entry per panel, in the
    order the figure lays them out. That order **is** the lettering, because
    the legend declares the figure's composition — so reordering the block
    re-letters the artwork, which is why a drafting session may not reorder it
    and an amendment must escalate.

    The block is authored at **planning** time, by the legend's brief ticket. A
    panel name minted by the legend's *drafter* arrives too late for every unit
    that references it: in the corpus this was calibrated on, seven body
    sections were drafted before all four legends, with roughly 38
    reader-facing panel references written before any legend existed.

    Absence is a legal state twice over — a legend file not written yet, and a
    legend with no `## Panels` block, which is a figure or a table with nothing
    to letter. Both declare no panels. The block is required by the panel
    *references*, not by the renderer, which is the same reason a missing
    bibliography is not a parse error either.
    """
    if not path.exists():
        return []
    where = "%s `## %s`" % (path.name, PANEL_SECTION)
    names = []
    for line in _sections(path.read_text()).get(PANEL_SECTION, []):
        if not line.strip() or line[:1].isspace():
            # A blank line, or the continuation of the entry above: an entry's
            # description is free text and wraps over as many lines as it
            # needs, exactly as the brief's inventory zone does.
            continue
        match = PANEL_DECLARATION.match(line)
        if match is None:
            raise ParseError(
                "%s: `%s` is not a panel declaration — an entry opens "
                "`@fig:<name>` at the start of its line, and this section "
                "holds declarations and nothing else"
                % (where, _collapse(line))
            )
        name = figure_name(match.group(1))
        if not SLOT_ID.match(name):
            raise ParseError(
                "%s: `%s` is not a name (lowercase, digits, hyphens)"
                % (where, match.group(1))
            )
        _refuse_positional_name(name, where)
        if name in names:
            raise ParseError(
                "%s: `@fig:%s` is declared twice — one entry per panel, and "
                "its position is the panel's letter" % (where, name)
            )
        names.append(name)
    return names


def figure_name(key):
    """The name behind a `@fig:` identifier.

    The prefix marks the **namespace**, not the kind: what a name renders as
    comes from its roster row, so the prefix is stripped once here and the
    namespace is keyed on bare names everywhere else.
    """
    return key[len(FIGURE_PREFIX):]


def _letter(index):
    """`a`, `b`, … `z`, `aa` — the spreadsheet sequence, so a legend that
    declares more panels than the alphabet holds still letters them all rather
    than running off the end of it."""
    letters = ""
    while True:
        index, remainder = divmod(index, 26)
        letters = chr(ord("a") + remainder) + letters
        if index == 0:
            return letters
        index -= 1


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


# `Finding` and `Citation` are the same shape — one token, where it was
# written, and the slot it sits under — because both are things read off the
# *source* rather than off the assembled document, for the same reason: by
# assembly time the blocks have been joined and every line number is gone.
# They are two classes and not one because they are two concepts with two
# reasons for existing, and the shape is small enough that sharing it would
# buy less than the coupling costs. If a third arrives, share it then.
class Finding:
    """One residue hit: where it is, and the text that matched.

    It carries the slot it sits under for the same reason an annotation does —
    the gate is scoped by granularity, so a hit outside the section under
    render is out of scope rather than silently in it.
    """

    def __init__(self, token, origin, line, slot_id=None):
        self.token = token
        self.origin = origin
        self.line = line
        self.slot_id = slot_id

    @property
    def where(self):
        return _where(self.origin, self.line)


class Reference:
    """One `@`-prefixed identifier written in reader-facing prose, at the
    position it was written — a citation key or a figure name, since the two
    are one reference surface.

    The source position is what the checks report, and it is the reason
    references are collected off the source rather than off the assembled
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

    Eight things come out of one read and travel together from there to the
    gate: the anchored blocks in the order they appear, the prose that landed
    outside every slot, the annotation manifest, the citations, the figure and
    panel references, the advisory warnings, and the two residue lints'
    findings.
    """

    def __init__(self):
        self.blocks = []
        self.stray = []
        self.annotations = []
        self.citations = []
        self.figure_references = []
        self.warnings = []
        self.bare_holes = []
        self.workflow_phrases = []


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
    # an annotation and every offset still points at the real source. The
    # prose diagnostics read that same text back through `Block.raw`, which is
    # why the blanking keeps every newline the source had.
    advisories = []
    masked = _mask_comments(text, fenced)
    spans = _brace_spans(masked, path, fenced, advisories)
    bare = _without_braces(masked, spans)

    # `bare` is exactly reader-facing prose: every comment and every brace
    # blanked to same-length whitespace, so the two channels an author writes
    # in are invisible here and every offset still points at the real source.
    _refuse_bracket_spans(bare, path, fenced)
    _refuse_reference_literals(bare, path, fenced)

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
        citations, named = _referenced(bare, cursor, stop, current, path, fenced)
        source.citations.extend(citations)
        source.figure_references.extend(named)
        # Both lints read `bare` — the text with every comment and every brace
        # blanked to same-length whitespace — so they see exactly the prose the
        # reader will meet, and still report the source's own line numbers.
        # That is the same text and the same window the citation scan above
        # takes, and for the same reason. Reading the author-facing channel
        # instead would refuse the very mechanism that channel exists to
        # provide: a hole is *allowed* to be named there, and a `TODO` in a
        # comment never reaches a reader.
        holes, phrases = _residue(bare, cursor, stop, current, path, fenced)
        source.bare_holes.extend(holes)
        source.workflow_phrases.extend(phrases)
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


def _refuse_reference_literals(bare, path, fenced):
    """Outside every comment and every fence, **prose may not spell a figure
    number, a panel letter, or a name that says where a panel sits.**

    Three shapes, one principle: *the source cannot express a stale
    identifier.* A number a drafting session types can be wrong-but-valid —
    pointing at a real figure that is not the one meant — and no gate can catch
    that, which is why the surface it needs is removed rather than checked.

    It is a **refusal, not a finding**, for the reason every refusal here is
    one: a finding is what returned CLEAN over 98 em dashes. And it **cannot be
    configured per effort** — a configurable refusal pattern is the override
    these rules exist to prevent, wearing a config file. Its cost is therefore
    stated rather than discovered: a legitimate parenthesised enumerator cannot
    be written in reader-facing prose. Measured on the calibration corpus,
    **21 of 21 parenthesised-letter occurrences in reader-facing prose were
    panel references or declaration markers, and zero were enumerators**, while
    all **37** legitimate `(a)`/`(b)` enumerator uses sat inside comments, which
    the refusal exempts by construction.
    """
    for pattern, why in (
        (
            PANEL_LETTER,
            "a panel letter belongs to the artwork and to the rendered text, "
            "never to the source — reference the panel by name",
        ),
        (
            NUMBERED_LITERAL,
            "a figure or table number exists only in rendered output — "
            "reference the object by name",
        ),
    ):
        for match in pattern.finditer(bare):
            if _inside(fenced, match.start()):
                continue
            raise ParseError(
                "%s: `%s` is a reference literal — %s"
                % (
                    _where(path, _line_of(bare, match.start())),
                    _collapse(match.group(0)),
                    why,
                )
            )
    for match in REFERENCE.finditer(bare):
        key = match.group(1)
        if _inside(fenced, match.start()) or not key.startswith(FIGURE_PREFIX):
            continue
        _refuse_positional_name(
            figure_name(key), _where(path, _line_of(bare, match.start()))
        )


def _refuse_positional_name(name, where):
    """A name says what a panel shows, never where it sits.

    Position is the one thing a name may not carry, because re-ordering panels
    is a legend edit and a name that encodes position would be silently
    invalidated by it — which is the defect literal letters have, arriving by a
    second route.
    """
    if POSITIONAL_NAME.search(name):
        raise ParseError(
            "%s: `@%s%s` is a positional name — a name describes its content, "
            "never its position, because the legend's declaration order is "
            "what assigns the letters" % (where, FIGURE_PREFIX, name)
        )


def _quote_bracket(bare, start):
    """The malformed span, as much of it as there is: to its closing bracket
    when it has one, and to the end of its paragraph when it does not."""
    end = bare.find("\n\n", start)
    end = len(bare) if end < 0 else end
    close = bare.find("]", start + 1)
    return _collapse(bare[start : close + 1 if 0 <= close < end else end])


def _referenced(bare, start, end, block, path, fenced):
    """Every reference written in one chunk of prose, in source order, split
    into the citation keys and the figure names.

    **One walk, two lists.** The two classes share a token and are told apart
    by the `fig:` prefix and nothing else, so scanning twice would be two
    implementations of one grammar — and the one thing they must agree on is
    which of them owns a given token.
    """
    citations = []
    figures = []
    for match in REFERENCE.finditer(bare, start, end):
        if _inside(fenced, match.start()):
            continue
        key = match.group(1)
        reference = Reference(
            key,
            path,
            _line_of(bare, match.start()),
            None if block is None else block.slot_id,
        )
        (figures if key.startswith(FIGURE_PREFIX) else citations).append(reference)
    return citations, figures


def _without_braces(masked, spans):
    """The text with every brace blanked as well as every comment.

    The direction is committed by the **claim**, so the scan for it must not
    see the labels — and a label carrying a `!` gate bit would otherwise read
    as the end of a sentence. It blanks through `_blank_spans`, the same
    length- and newline-preserving helper the prose diagnostics use, so every
    offset still points at the author's own text.
    """
    return _blank_spans(masked, [(start, end) for start, end, _ in spans])


def _residue(bare, start, stop, block, path, fenced):
    """Both residue lints over one chunk of reader-facing prose: the bare holes
    and the workflow phrases, in that order.

    One walk for both, because they take the same six arguments over the same
    text and differ only in their pattern — two call sites passing one clump
    twice is how the two come to be scanned over different spans.

    A fence is skipped: it is literal text being shown, not prose being
    claimed, and nothing else in this parser reads inside one either.

    Scanning `bare` in place rather than a slice keeps every offset pointing at
    the real source, so `_line_of` reports the source's own line. **A `\\b` at
    `start` is judged against the character actually there; one at `stop` is
    not** — `endpos` reads as end of text, the one asymmetry in `re`'s window.
    It costs nothing here only because every `stop` is a comment's `<`, which
    `_mask_comments` has blanked to a space, so both readings agree. A chunk
    that ever ends mid-word would need the boundary re-derived, not re-cropped.
    """
    return [
        [
            Finding(
                match.group(0),
                path,
                _line_of(bare, match.start()),
                None if block is None else block.slot_id,
            )
            for match in pattern.finditer(bare, start, stop)
            if not _inside(fenced, match.start())
        ]
        for pattern in (BARE_HOLE, WORKFLOW_PHRASE)
    ]


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


def roster_integrity_problems(skeleton, figures, referenced):
    """The two ways a document's references and its roster misdescribe each
    other: a name in prose the document does not carry, and a roster name the
    prose never points at.

    **The check is symmetric, and the symmetry is what separates it from the
    bibliography's.** A roster is a manifest of *this document's* objects, so
    an object nothing points at is damage — a figure that would be published
    and never discussed. A library is over-provisioned by nature, which is why
    the citation check has no second half and must not grow one.

    Parentage is carried by containment on **both** sides. A reference to a
    panel resolves because its legend declares it, and it satisfies its
    figure's roster row, because a reference to a panel *is* a reference to the
    figure the panel lives in. A declared panel the prose never names is no
    problem at all: the roster carries no panel rows, so there is no roster
    name left unreferenced, and a figure may legitimately hold a panel the
    prose does not call out on its own.
    """
    problems = []
    dangling = set()
    pointed_at = set()
    # One walk answers both halves: a reference either names nothing, or it
    # names the object it points at through containment.
    for reference in referenced:
        figure = figures.figure_for(figure_name(reference.key))
        if figure is not None:
            pointed_at.add(figure)
        elif reference.key not in dangling:
            dangling.add(reference.key)
            problems.append("%s `@%s`" % (reference.where, reference.key))
    for _, name, _ in skeleton.roster:
        if name not in pointed_at:
            problems.append("`%s` is in the roster and referenced nowhere" % name)
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
# the brief, and the overlap instrument over it
# --------------------------------------------------------------------------
#
# `briefs/<unit>.md` is a declared input, one per unit, beside the source. This
# is the brief's only *parser*, but not its format's owner: the drafting skill
# is the unit that ships the two templates, and what this file fixes is the six
# zone headings it parses and nothing else. So the parse surface stays a list
# of headings, and a template that renames a zone shows up here as an unparsed
# zone rather than as silence.
#
# Exactly two zones are reader-facing, and they are the only zones whose content
# may legitimately appear in the prose. Every other zone is instruction by
# virtue of where it sits — positional separation, no marker strings.


class Token:
    """One word, where it sits in its clause, and whether punctuation closes it
    off.

    The punctuation is kept because it is what separates an inventory item's
    plural noun from a predication's verb: `5 DSL2 stages, DAPI as anchor` ends
    its noun on a comma, and `illumination correction suppresses tile-boundary
    seams` does not. The offsets are kept so a span can be quoted as the prose
    wrote it rather than as this tokeniser saw it.
    """

    __slots__ = ("word", "closed", "start", "end")

    def __init__(self, word, closed, start, end):
        self.word = word
        self.closed = closed
        self.start = start
        self.end = end


class Clause:
    """One sentence: its own text, and its own words.

    A shared span is measured inside one clause and never across two, because a
    run that bridges a full stop is an adjacency rather than a phrase: nobody
    transcribed *…per marker pair. Registration…*, the two texts merely happen
    to order their own items the same way.
    """

    __slots__ = ("text", "tokens", "words")

    def __init__(self, text):
        self.text = text
        self.tokens = tokenize(text)
        self.words = [token.word for token in self.tokens]


class Span:
    """A run of words a unit's prose and its brief have verbatim in common."""

    __slots__ = ("clause", "start", "length")

    def __init__(self, clause, start, length):
        self.clause = clause
        self.start = start
        self.length = length

    @property
    def tokens(self):
        return self.clause.tokens[self.start : self.start + self.length]

    def quote(self):
        """The span as the prose wrote it — case, punctuation and all.

        Printed rather than the normalised words, because what the author has
        to go and find is the phrase, and `Nextflow >= 25.04.0` is not findable
        as `nextflow 25 04 0`.
        """
        tokens = self.tokens
        text = " ".join(self.clause.text[tokens[0].start : tokens[-1].end].split())
        return text if len(text) <= QUOTE_WIDTH else text[: QUOTE_WIDTH - 1] + "…"

    def carries_content(self):
        """A run of nothing but function words is grammar rather than
        transcription. Two content words is the smallest run that could have
        been lifted."""
        return sum(1 for token in self.tokens if token.word not in FUNCTION_WORDS) >= 2

    def predicates(self):
        """The finite-verb test: does this shared span predicate something?

        A closed list plus one guarded morphological rule, and deliberately no
        more. `-ed` is not a tell — the corpus's own *scale bar required* is an
        expected span — and a bare `-s` rule fires on every plural noun, which
        is the failure a legend cannot survive: an instrument that fires forever
        is an instrument nobody reads.
        """
        tokens = self.tokens
        for index, token in enumerate(tokens):
            if token.word in FINITE_FORMS:
                return True
            if _third_person_present(tokens, index):
                return True
        return False


def _third_person_present(tokens, index):
    """Whether this word is a third-person present verb rather than a plural
    noun — the one morphological rule the finite-verb test carries, and every
    guard it needs to stay conservative."""
    word = tokens[index].word
    if len(word) < 4 or not word.endswith("s"):
        return False
    if word.endswith(("ss", "us", "is", "ies", "'s", "’s")):
        return False
    if index == 0 or index == len(tokens) - 1:
        return False  # a span's last word has nothing left to predicate about
    if tokens[index].closed:
        return False  # punctuation closes an item, so this is its final noun
    previous = tokens[index - 1].word
    return previous not in NOT_A_SUBJECT and not previous[0].isdigit()


class Brief:
    """One unit's brief: its zones, or the one reason nothing can be measured.

    A brief this parser cannot read is reported in the row rather than raised.
    Every row the brief feeds is reported-only, so raising would make an
    unreadable brief change the exit code — and the brief is an input to a
    prose fact, never to the document the render emits.
    """

    def __init__(self, path, zones=None, problem=None):
        self.path = path
        self.zones = zones or {}
        self.problem = problem

    @property
    def readable(self):
        return self.problem is None

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

    @property
    def items(self):
        """What the brief states, in the order it states them, less the ladder
        line: `Rung:`, `Closes:`, `Opens:` and `Restates:` carry the unit's
        relation to the rung above it, and a relation is bookkeeping rather
        than something the prose must convey.

        The argument zone first, because a unit that is both originating and
        inventory-carrying is expressible, and its propositions are what its
        paragraphs are ordered against.
        """
        for name, _ in self.reader_facing:
            lines = [
                line.strip()
                for line in self.zones[name]
                if line.strip() and not RELATION_LINE.match(line.strip())
            ]
            found = sentences(" ".join(lines))
            if found:
                return found
        return []

    def overlap(self, prose):
        """The spans a unit's prose shares with this brief's reader-facing
        zones, split by the instrument the zone they came from carries.

        The zone decides the instrument, not the unit: `## Argument`'s
        propositions are phrased as what the reader must accept, so verbatim
        overlap with one *is* the defect and needs no verb test; an inventory
        item is a fact the prose must convey, so a shared span is expected
        unless it predicates.
        """
        clauses = _clauses(prose)
        flagged = []
        expected = 0
        seen = set()
        for name, zone_text in self.reader_facing:
            windows = _windows(_clauses(zone_text))
            for number, clause in enumerate(clauses):
                for span in _shared_spans(windows, clause):
                    key = (number, span.start, span.length)
                    if not span.carries_content() or key in seen:
                        continue
                    seen.add(key)
                    if name == ARGUMENT or span.predicates():
                        flagged.append(span)
                    else:
                        expected += 1
        return flagged, expected


def parse_brief(path):
    """The unit's brief, or `None` where the unit has none.

    An absent brief is a legal state: briefs arrive as units are planned, and a
    unit with no brief yet is a unit nothing has been measured against. The row
    says so, rather than counting it as nothing to report.
    """
    if not path.exists():
        return None
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError) as error:
        return Brief(path, problem="cannot be read — %s" % error)
    zones = _sections(text)
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


def tokenize(text):
    """The words of one clause, each with its offset and whether punctuation
    closes it off. `WORD` above is the word this shares with every other
    diagnostic."""
    tokens = []
    for match in WORD.finditer(text):
        after = text[match.end() : match.end() + 1]
        tokens.append(
            Token(
                match.group(0).lower(),
                after in CLOSING or after == "",
                match.start(),
                match.end(),
            )
        )
    return tokens


def _clauses(text):
    """The text as one `Clause` per sentence, over the same paragraph and
    sentence splits every other diagnostic reads."""
    return [
        Clause(sentence)
        for paragraph, _ in paragraphs(text, 1)
        for sentence in sentences(paragraph)
    ]


def _windows(clauses):
    """Every `PHRASE_WORDS`-long window of the brief, by the clause it sits in,
    so a match can be extended along that clause and no further."""
    windows = {}
    for clause in clauses:
        for start in range(len(clause.words) - PHRASE_WORDS + 1):
            windows.setdefault(
                tuple(clause.words[start : start + PHRASE_WORDS]), []
            ).append((clause.words, start))
    return windows


def _shared_spans(windows, clause):
    """Every maximal run of `PHRASE_WORDS` words or more that this clause of the
    prose shares verbatim with the brief.

    Word-level rather than character-level, because what this catches is a
    phrase reused, and a phrase survives a re-wrapped line.
    """
    spans = []
    words = clause.words
    index = 0
    while index <= len(words) - PHRASE_WORDS:
        found = windows.get(tuple(words[index : index + PHRASE_WORDS]))
        if found is None:
            index += 1
            continue
        longest = PHRASE_WORDS
        for brief_words, start in found:
            length = PHRASE_WORDS
            while (
                index + length < len(words)
                and start + length < len(brief_words)
                and words[index + length] == brief_words[start + length]
            ):
                length += 1
            longest = max(longest, length)
        spans.append(Span(clause, index, longest))
        index += longest
    return spans


def unit_paragraphs(paper, unit):
    """The in-scope paragraphs of every block in a unit's subtree.

    The same scoped prose every other diagnostic reads, so an annotation, a
    table row and a fenced block are no more visible to the overlap instrument
    than they are to the em-dash count.
    """
    subtree = set(slot.id for slot in paper.skeleton.subtree(unit))
    found = []
    for block, scoped in in_scope(paper):
        if block.slot_id in subtree:
            found.extend(text for text, _ in paragraphs(scoped, block.raw_line))
    return found


def _content_words(text):
    return set(
        token.word for token in tokenize(text) if token.word not in FUNCTION_WORDS
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


def _mirrored(unit_prose, items):
    """How many paragraphs sit at the position of the brief item they are
    about — the one-bullet-per-paragraph walk, counted.

    Reported against the unit's own paragraph count, never against the item
    count: a draft that walks three items and then writes five more paragraphs
    is not mirroring, and a denominator stopping at the items would never look
    at the five.
    """
    return sum(
        1
        for index, paragraph in enumerate(unit_prose)
        if _matching_item(paragraph, items) == index
    )


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

    def advisory(self):
        """The same verdict in the advisory channel: a `WARN` moves no exit
        code.

        It is a `WARN` and not a `PASS` because `G6` abolished `CLEAN` for
        exactly this reason — one word cannot carry checked-and-fine against
        checked-and-objected, and a warning printed as a pass reintroduces the
        misleading verdict the table exists to replace.
        """
        return Verdict(WARN if self.problems else PASS, self.problems)

    def render(self):
        if self.kind not in (WARN, FAIL):
            return self.kind
        return "%s — %d (%s)" % (
            self.kind,
            len(self.problems),
            "; ".join(self.problems),
        )


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


def check_slot_roster_integrity(paper):
    """An anchor names a slot the skeleton carries, no slot is anchored twice,
    no prose sits outside every slot, every figure or panel name in prose is a
    name this document carries, and every roster name is pointed at.

    **One row, because it is one defect:** the emitted document is not the
    document the source describes. A broken tree and a reference to an object
    the document does not have are the same failure wearing two shapes, and
    circulating damage is how it spreads — so this is a hard error rather than
    a gate.

    Whole-document only. Whether a slot is anchored twice, or anchored nowhere,
    is a fact about the whole document; so is *a roster name never referenced*,
    which is undecidable from one unit's source because the reference may live
    in any other unit.
    """
    return Verdict.over(
        slot_integrity_problems(paper.skeleton, paper.blocks, paper.stray)
        + roster_integrity_problems(
            paper.skeleton, paper.figures, paper.figure_references
        )
    )


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


def check_bare_holes(paper):
    """No bare hole is left in reader-facing prose.

    A hole nobody marked is the one class of gap this design cannot route: the
    manifest never hears about it, so the author is never told, and the
    sentence around it reads as finished. `--circulate` still emits — the hole
    is right there in the prose, so the render is faithful — but the work is
    unfinished, so submission is refused.

    **Documented cost:** `46,XX` and `47,XXX` are standard karyotype notation
    and `TK` is thymidine kinase, and the list fires on all three. It is safe
    here only because the calibration corpus contains none of them, and a wrong
    refusal breaks a paper that never asked for any of this. The cost is
    carried as fog rather than as configuration, because a configurable refusal
    *is* the override these rules exist to prevent, wearing a config file. What
    bounds the harm is the tier: a karyotype paper circulates freely.
    """
    return Verdict.over(_residue_problems(paper.bare_holes_in_scope))


def check_workflow_phrases(paper):
    """No author workflow state is written as a sentence the reader will read.

    Its tells are far likelier to be legitimate prose than a bare hole's are —
    a pending trial is a fact about the literature and *"we should expect"* is a
    hedge, not a note to the author — so this check sits one tier softer: it
    **warns** under `--circulate` and refuses only the submit question. That is
    the whole asymmetry, and it is deliberate: a dumb lint must not put a
    failing row in front of an author who only wants to circulate a draft.
    """
    return Verdict.over(_residue_problems(paper.workflow_phrases_in_scope))


def _residue_problems(findings):
    """One line per hit, spelled the way a gating annotation's line is spelled
    — the position, then the text — because an author acts on both the same
    way."""
    return ["%s `%s`" % (finding.where, finding.token) for finding in findings]


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


def check_brief_overlap(paper):
    """How much of each unit's brief reached its prose verbatim.

    A drafting session that walks its brief one bullet per paragraph produces a
    list of labelled blocks rather than a manuscript, and the corpus shows it
    happening: the audit's own phrase for what it found is *transcribed
    near-verbatim from the briefs*. Both numbers are reported and neither is a
    floor — a threshold here would be a rule about prose, and rules about prose
    are what the judgement axes are for.
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
        if not brief.readable:
            notes.append("%s: %s" % (brief.path.name, brief.problem))
            continue
        spans, counted = brief.overlap("\n\n".join(unit_paragraphs(paper, unit)))
        expected += counted
        flagged.extend('%s: "%s"' % (unit.id, span.quote()) for span in spans)

    text = "%d flagged, %d expected" % (len(flagged), expected)
    detail = flagged + notes
    if absent:
        detail.append("no brief for %s" % ", ".join(absent))
    if detail:
        text += " — %s" % "; ".join(detail)
    return Number(text)


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
        "%d in %s%s%s"
        % (
            len(spots),
            _plural(len(originating), "originating unit"),
            _locations(spots),
            _brief_order(paper, originating),
        )
    )


def _brief_order(paper, originating):
    """How many of each unit's paragraphs sit at the position of the brief item
    they are about — the one-bullet-per-paragraph walk, counted.

    Suspended for a non-originating unit alongside the single-sentence count,
    and for the same reason: order tracking the brief is what a venue's field
    order and a figure's lettering *mandate* there, so it is the requirement
    rather than the defect.
    """
    walks = []
    notes = []
    for unit in originating:
        brief = paper.brief_for(unit)
        prose = unit_paragraphs(paper, unit)
        if brief is None or not brief.readable or not prose:
            # Said already, and once: the overlap row above names every unit
            # with no brief and every brief this parser cannot read, and an
            # undrafted unit is what `unfilled skeleton slot` fails on. Two
            # rows carrying one fact is how the two of them drift.
            continue
        items = brief.items
        if not items:
            notes.append("%s: the brief states no reader-facing item" % unit.id)
            continue
        walks.append("%d of %d (%s)" % (_mirrored(prose, items), len(prose), unit.id))

    order = ""
    if walks:
        order += "; brief-order %s" % ", ".join(walks)
    if notes:
        order += "; brief-order not measured (%s)" % "; ".join(notes)
    return order


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


# --------------------------------------------------------------------------
# the supersession diff
# --------------------------------------------------------------------------
#
# `RV4`. When a unit is re-drafted, the author learns what the revision
# silently lost. **A diff-relative reading is the wrong instrument for a fresh
# draft and the right one here:** for a supersession the diff is not an
# approximation of the question, it *is* the question.
#
# **A finding, never a gate.** A revision that correctly removes 2,000 words,
# because the ladder amendment deleted the rung those words served, must not be
# blocked by its own success. Two mechanisms keep it that way rather than one
# rule: the row sits in the reported tier, which `run_gate` gives no bucket the
# exit code reads, and it prints a `Number`, which is not a verdict and has no
# `FAIL` to print.
#
# **There is no keep-list**, here or anywhere in the interface. A list of what
# must not change would be written by the same agent that drops a claim, and it
# would omit the dropped claim too, so the drop-guard is mechanical.


class Supersession:
    """The old side of one supersession, or the reason there is not one.

    Three states, and the row prints all three: no ref was named, a ref was
    named and its old render could not be rebuilt, or the old render itself.
    Two of them are findings rather than errors, which is why the reason
    travels as a string on this object instead of being raised.
    """

    def __init__(self, ref, old=None, problem=None):
        self.ref = ref
        self.old = old
        self.problem = problem


def supersession(ref, root, source_path, paper):
    """The old render of this unit, rebuilt from the commit the original draft
    ticket closed at.

    Renders are ephemeral (`C7`), but the render is a **pure function of the
    source** and git is the audit trail (`A8`): check the source out at that
    commit and run **the same render**, at the same section anchor. Post
    promotion one side comes from the working manuscript and the other from the
    frozen drafts, and that is still well-defined, because `K5` guarantees
    **anchors — not headings — are what live in the source.**

    **Nothing here may raise.** The row it feeds is reported-only, so a missing
    binary, a ref nobody kept, a tree carrying no source and a source the old
    skeleton can no longer describe are all *findings*: they print in the row
    and reach no exit code. The breadth of the `except` is the point rather
    than an oversight — enumerating the ways git and an old tree can disappoint
    is how one of them comes to escape and refuse a render the author asked
    for.
    """
    if ref is None or paper.granularity != SECTION:
        return None
    try:
        with tempfile.TemporaryDirectory() as directory:
            old_root = Path(directory).resolve()
            _check_out(root, ref, old_root)
            old = load_paper(
                _old_source(old_root, root, source_path, paper.unit),
                old_root,
                SECTION,
                paper.unit.id,
                paper.em_dash_threshold,
            )
        return Supersession(ref, old=old)
    except Exception as error:
        return Supersession(ref, problem=_reason(error))


def _check_out(root, ref, destination):
    """The paper root as of one commit, written into `destination`.

    A tar stream rather than a second worktree: `git archive` names one
    tree-ish and touches neither the index nor the working tree, so rebuilding
    the old side cannot disturb the render the author is waiting for.
    """
    prefix = _git(root, "rev-parse", "--show-prefix").decode().strip().rstrip("/")
    stream = _git(
        root, "archive", "--format=tar", "%s:%s" % (ref, prefix) if prefix else ref
    )
    with tarfile.open(fileobj=io.BytesIO(stream), mode="r|") as archive:
        for member in archive:
            if not member.isfile():
                # A regular file is the only thing the render reads, so nothing
                # else is written. A symlink or a device node would be a way
                # out of this directory and buys the diff nothing.
                continue
            path = (destination / member.name).resolve()
            if destination not in path.parents:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.extractfile(member).read())


def _old_source(old_root, root, source_path, unit):
    """Where this unit's prose lived at the old ref.

    **The same relative path first** — every pre-promotion revision, and every
    revision of a revision. Then `drafts/<unit>.md`, which is the one other
    place it can be: post-promotion the working manuscript carries the unit and
    the frozen draft carries what it superseded, and both go through the same
    render at the same anchor.
    """
    try:
        candidates = [source_path.resolve().relative_to(root.resolve())]
    except ValueError:
        # A `--paper` root the source does not sit under. The relative path is
        # not a path inside the old tree at all, so only the declared drafts
        # location is left.
        candidates = []
    candidates.append(Path(DRAFTS_DIR) / ("%s.md" % unit.id))
    for candidate in candidates:
        if (old_root / candidate).exists():
            return old_root / candidate
    raise HardError("the tree at this ref carries no source for `%s`" % unit.id)


def _git(root, *args):
    """One git command in the paper root, or the error it exited with."""
    return subprocess.run(
        [GIT, "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout


def _reason(error):
    """One line naming what went wrong, in git's own words where it has any."""
    if isinstance(error, subprocess.CalledProcessError):
        said = (error.stderr or b"").decode("utf-8", "replace").strip().splitlines()
        if said:
            return said[0].removeprefix("fatal: ")
        return "`git %s` exited %d" % (error.cmd[3], error.returncode)
    if isinstance(error, FileNotFoundError) and error.filename == GIT:
        return "no `%s` on the path" % GIT
    return str(error) or error.__class__.__name__


def check_supersession(paper):
    """What this revision lost, measured against the old render of one unit.

    Five structural losses, in one row, because they are one question — *what
    went missing that nobody declared?* — and an author reading the answer
    needs the body counts beside the list to size it.
    """
    superseded = paper.superseded
    if superseded is None:
        # Not a pass: a fresh draft has no old side, and one word cannot carry
        # checked-and-fine against never-looked.
        return Number("not a supersession — no `--supersedes` ref")
    if superseded.old is None:
        return Number("old side unavailable — %s" % superseded.problem)

    old = superseded.old
    lost = (
        _lost_headings(old, paper)
        + _lost_figure_references(old, paper)
        + _lost_citations(old, paper)
        + _vanished_gates(old, paper)
    )
    body = _body_delta(old, paper)
    if not lost:
        return Number("%s, no structural loss" % body)
    return Number("%s; %s" % (body, "; ".join(lost)))


def _body_delta(old, new):
    """The two body word counts, and how far the drop fell.

    **The counts print on both sides of the bar**, the way every threshold in
    this gate prints its number: the bar decides what is worth a line, never
    what is worth measuring.
    """
    before, after = _body_words(old), _body_words(new)
    text = "body %d → %d words" % (before, after)
    if not before or before == after:
        return text
    percent = abs(after - before) * 100 // before
    if after > before:
        return "%s (up %d%%)" % (text, percent)
    past = ""
    if (before - after) * 100 > SUPERSESSION_DROP_PERCENT * before:
        past = ", past the %d%% bar" % SUPERSESSION_DROP_PERCENT
    return "%s (down %d%%%s)" % (text, percent, past)


def _body_words(paper):
    """How many words of body prose this unit carries.

    The same text every other reported number is measured over — annotations,
    citation groups, tables, fenced blocks and comments blanked, headings never
    there in the first place — so the count a revision is sized by is the count
    the rest of the table reports on.
    """
    return sum(len(words(scoped)) for _block, scoped in in_scope(paper))


def _lost_headings(old, new):
    """A heading-level block the old render carried and the new one does not.

    Read off the **two renders** rather than off the two skeletons, because the
    render is what a reader meets and the level is part of what it says: a slot
    dropped from the tree and a slot moved to another level both take a heading
    out of this unit's render, and `K5` puts every heading there on every pass.
    """
    after = _headings(new)
    gone = [heading for heading in _headings(old) if heading not in after]
    return ["heading lost (%s)" % _quoted(gone)] if gone else []


def _headings(paper):
    """Every heading line of one render, level included."""
    return RENDERED_HEADING.findall(render_document(paper))


def _lost_figure_references(old, new):
    """A figure or panel reference present before and absent after.

    **One class, because under `PN1` a figure and a panel are one token
    class** — the same `@` surface, the same roster, told apart by nothing this
    check reads. A per-class branch here would be a second opinion about which
    of the two owns a given token.
    """
    gone = _tokens(old.figure_references_in_scope) - _tokens(
        new.figure_references_in_scope
    )
    return ["figure reference lost (%s)" % _quoted(sorted(gone))] if gone else []


def _lost_citations(old, new):
    """A reference that has lost its only in-text anchor.

    Absent from the unit **and** from the rest of the source, because that is
    what the words say and both sides are in hand: a key still cited in another
    unit costs the document no reference at all.

    Its own class rather than the figure one above, because the consequences
    differ. A figure name nothing points at is a hard error the gate already
    carries; the reference list is built from the **cited keys** (`CT5`), so a
    dropped key silently drops a reference and no other check looks.
    """
    gone = _tokens(old.citations_in_scope) - _tokens(new.citations)
    if not gone:
        return []
    return ["reference lost its only anchor (%s)" % _quoted(sorted(gone))]


def _tokens(references):
    """Every reference in the set, as the prose wrote it — the `@` included, the
    way every other row of this table names one."""
    return set("@%s" % reference.key for reference in references)


def _vanished_gates(old, new):
    """A gate-bit annotation the old side carried, gone from the new one, and
    gone with its prose.

    **Deletion is the only closure, so *gone* alone says nothing:**
    substituting the real value is exactly how a hole is closed, and it leaves
    the sentence standing. What separates the closure from the loss is
    therefore the **prose**, and the test is the one this file already uses for
    verbatim survival — whether the paragraph that carried the hole left a run
    of `PHRASE_WORDS` words behind. A filled hole leaves its paragraph; a
    deleted block leaves nothing.
    """
    still_open = _open_gates(new)
    surviving = _word_runs("\n".join(scoped for _block, scoped in in_scope(new)))
    gone = []
    for annotation in old.annotations_in_scope:
        if not annotation.gate:
            continue
        if (annotation.behaviour, annotation.label) in still_open:
            continue
        if _traced(_carrying_paragraph(old, annotation), surviving):
            continue
        gone.append(annotation.token)
    return ["gate annotation vanished unclosed (%s)" % _quoted(gone)] if gone else []


def _open_gates(paper):
    """Every gate-bit annotation this side still carries, by what identifies one
    across two renders: the behaviour it renders as, and its label."""
    return set(
        (annotation.behaviour, annotation.label)
        for annotation in paper.annotations_in_scope
        if annotation.gate
    )


def _carrying_paragraph(paper, annotation):
    """The paragraph the annotation's brace was written into, with the brace
    already blanked — the paragraph as a substituted value would leave it, minus
    the value itself.
    """
    for block, scoped in in_scope(paper):
        if block.slot_id != annotation.slot_id or block.origin != annotation.origin:
            continue
        for text, line in paragraphs(scoped, block.raw_line):
            if line <= annotation.line <= line + text.count("\n"):
                return text
    return ""


def _traced(paragraph, surviving):
    """Whether the prose that carried a hole is still in the revised unit."""
    runs = _word_runs(paragraph)
    if runs:
        return bool(runs & surviving)
    # Shorter than one run: a hole standing in a fragment, which the warnings
    # channel already has its own opinion about. The honest test left is
    # whether the few words it did carry are all still there.
    carried = words(paragraph)
    left = set(word for run in surviving for word in run)
    return bool(carried) and set(carried) <= left


def _word_runs(text):
    """Every `PHRASE_WORDS`-long run of words in one piece of prose.

    The unit of verbatim survival, at the length the overlap instrument already
    fixed: a shorter run is two texts about one subject agreeing by accident.
    It is its own function and not that instrument's `_windows`, which keys
    runs by the clause they sit in — a shared span never bridges a full stop
    there, and here the question is only whether the prose is still anywhere in
    the unit.
    """
    found = words(text)
    return set(
        tuple(found[start : start + PHRASE_WORDS])
        for start in range(len(found) - PHRASE_WORDS + 1)
    )


def _quoted(items):
    return ", ".join("`%s`" % item for item in items)


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
#   parse    reference literals          (built)
#   hard     slot / roster integrity     (built; the roster half joined the
#                                        slot half when figures landed, and
#                                        the row took its full name)
#   hard     citation → bib entry        (built)
#   hard     unit / rung pairing         (built)
#   hard     originating slot children   (built)
#   gating   annotations (gating)        (built)
#   gating   unfilled skeleton slot      (built)
#   gating   bare holes                  (built)
#   gating   workflow phrases            (built; warns on `--circulate`)
#   gating   chain bookkeeping           (built)
#   gating   debt precedence             (built)
#   reported em dashes                   (built)
#   reported brief-to-prose overlap      (built)
#   reported single-sentence body …      (built, and paragraph order joined it
#                                        with the overlap instrument)
#   reported adversative ratio           (built)
#   reported subject openings            (built)
#   reported sentence length             (built)
#   reported locality test               (built)
#   reported supersession diff           (built; the one row that is section
#                                        granularity only, because one unit at
#                                        a time is what a supersession is)
#
# The parse-tier rows built here have no entry below: a parse error means
# nothing ran, so the table is absent rather than carrying their verdicts.
#
# A row name may be a function of the paper, for a row whose name carries the
# threshold the number was measured against.
REGISTRY = [
    ("slot / roster integrity", HARD, DOCUMENT, check_slot_roster_integrity),
    ("citation → bib entry", HARD, DOCUMENT, check_citation_entries),
    ("unit / rung pairing", HARD, None, check_unit_rung_pairing),
    ("originating slot children", HARD, None, check_originating_slot_children),
    ("annotations (gating)", GATING, None, check_gating_annotations),
    ("unfilled skeleton slot", GATING, None, check_unfilled_skeleton_slot),
    ("bare holes", GATING, None, check_bare_holes),
    ("workflow phrases", GATING, None, check_workflow_phrases),
    ("chain bookkeeping", GATING, DOCUMENT, check_chain_bookkeeping),
    ("debt precedence", GATING, DOCUMENT, check_debt_precedence),
    (em_dash_row, REPORTED, None, check_em_dashes),
    ("brief-to-prose overlap", REPORTED, None, check_brief_overlap),
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
    ("supersession diff", REPORTED, SECTION, check_supersession),
]

# The three Tier 4 diagnostics are whole-document only, and the em-dash count
# is not: the count blocks a drafting seam, and a seam is one section. The
# three are reported together over the finished piece, because a rhythm number
# published per seam is a number a drafter tunes at the seam — which is the
# behaviour `no threshold` exists to prevent.

# The one mode-dependent fact in the whole gate: these checks **warn** rather
# than fail under `--circulate`, and gate the submit question as usual. It is a
# set of checks rather than a fourth tier because the tier answers one question
# — *would the render emit something false?* — and folding a second question
# into that value is how a tier comes to be switched on twice. Keyed on the
# check itself rather than on the row's printed name, which is a display
# string and not an identity.
#
# A check earns a place here by being deliberately dumb: one whose false
# positives are likely enough that failing an author who only wants to
# circulate a draft would cost more than the check catches.
ADVISORY_ON_CIRCULATE = {check_workflow_phrases}

# The parse-tier rows print `PASS` whenever a table prints at all, because a
# parse-tier failure suppresses the table.
PARSE_ROWS = [
    "skeleton / spine grammar",
    "source grammar",
    "brace grammar",
    "citation group",
    "reference literals",
]


# --------------------------------------------------------------------------
# the render
# --------------------------------------------------------------------------


class Paper:
    """One paper at one granularity: the two files, the source, and the slots
    in scope."""

    def __init__(
        self, skeleton, spine, briefs, bibliography, figures, source, granularity,
        unit, em_dash_threshold,
    ):
        self.skeleton = skeleton
        self.spine = spine
        self.briefs = briefs
        self.bibliography = bibliography
        self.figures = figures
        self.blocks = source.blocks
        self.stray = source.stray
        self.annotations = source.annotations
        self.citations = source.citations
        self.figure_references = source.figure_references
        self.warnings = source.warnings
        self.bare_holes = source.bare_holes
        self.workflow_phrases = source.workflow_phrases
        self.granularity = granularity
        self.unit = unit
        self.em_dash_threshold = em_dash_threshold
        # The old side of a supersession, attached by the CLI when
        # `--supersedes` names a ref. It arrives after construction rather than
        # as an argument because it is *another paper*, loaded by the same
        # loader that built this one, and a constructor that could build one
        # would be a loader that can recurse.
        self.superseded = None
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

    def brief_for(self, unit):
        return self.briefs.get(unit.id)

    @property
    def annotations_in_scope(self):
        """The annotations the gate can speak for at this granularity.

        The **gate** is scoped the way every other row is. The **manifest** is
        not: it enters whole, because it is `f(source)` recomputed per render
        and an absolute input to a diff-relative judgement axis.
        """
        return self._in_scope(self.annotations)

    @property
    def bare_holes_in_scope(self):
        return self._in_scope(self.bare_holes)

    @property
    def workflow_phrases_in_scope(self):
        return self._in_scope(self.workflow_phrases)

    @property
    def citations_in_scope(self):
        return self._in_scope(self.citations)

    @property
    def figure_references_in_scope(self):
        return self._in_scope(self.figure_references)

    def _in_scope(self, found):
        """Anything carrying a `slot_id`, scoped to this granularity.

        One implementation for all five, because "is this in scope" is one
        fact: five copies of it is how a section render comes to gate on a
        different set than the row above it claims.
        """
        if self.granularity == DOCUMENT:
            return found
        in_scope = set(slot.id for slot in self.slots)
        return [one for one in found if one.slot_id in in_scope]


def load_paper(source_path, root, granularity, named_unit, em_dash_threshold):
    """One render's whole input, read from one paper root.

    **The render is a pure function of the source, and this is that function's
    argument list.** The supersession diff rebuilds the old side by calling it
    again over the same paper checked out at an earlier commit, so a second
    reader of these files would be a second render — and two renders of one
    source are two things that can disagree about it.

    Raises, as every parser below it does: a caller that wants a finding rather
    than an exit code catches it.
    """
    paths = source_paths(source_path)
    skeleton = parse_skeleton(root / "skeleton.md")
    spine = parse_spine(root / "spine.md")
    bibliography = read_bibliography(root / BIB_PATH)
    figures = read_figures(root, skeleton)
    source = parse_source(paths)
    briefs = load_briefs(root, skeleton)
    unit = None
    if granularity == SECTION:
        unit = derive_unit(skeleton, source.blocks, named_unit)
    return Paper(
        skeleton, spine, briefs, bibliography, figures, source, granularity, unit,
        em_dash_threshold,
    )


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
                prose = _resolve_references(prose, numbers, paper.figures)
            out.append("\n%s\n" % prose)
    out.append(_reference_list(paper, numbers))
    return "".join(out)


def _resolve_references(prose, numbers, figures):
    """Every reference token in one slot's prose, replaced by what it resolves
    to — a citation by its number, a figure or panel by its rendered form.

    **One walk for both classes**, because `@`-prefixed identifiers are one
    reference surface and a single token may carry either. Numbers are assigned
    **by first mention in the assembled document**, which is why `numbers` and
    `figures` are both carried across the slots in render order rather than
    rebuilt per slot. A drafting session writes a name and never a number, so a
    number it might have written wrong — wrong-but-valid, and invisible to
    every check — is a thing it cannot type.

    Two things are stepped over. A gap token's label is author-facing text the
    render has already substituted into the prose, so a name inside one is not
    a reference of this document. And inside a fence nothing is parsed at all,
    here as everywhere else — a source showing the syntax is showing it, not
    using it.

    A group resolves **per key, not per token**, so a mixed
    `[@smith2020; @fig:overlay]` renders `[1; fig. 2]`. Leaving the whole token
    verbatim would drop a real citation out of the reference list while the
    gate went on demanding an entry for it.

    **The brackets are the source's own grouping, so they survive**: a group
    renders as a group and a bare token renders bare, which is the one thing
    that keeps `@fig:overlay` from acquiring citation brackets it never had.
    """
    fenced = _fenced_spans(prose)

    def resolve(match):
        token = match.group(0)
        if match.group("gap") or _inside(fenced, match.start()):
            return token
        # The prefix decides the class **once**. Reading it back out of the
        # rendered form — *is this piece all digits?* — would couple the bracket
        # style to `FIGURE_LABEL` never holding a digit, which is a promise
        # nothing here makes.
        pieces = []
        every_piece_a_citation = True
        for key in REFERENCE.findall(token):
            if key.startswith(FIGURE_PREFIX):
                every_piece_a_citation = False
                pieces.append(figures.resolve(figure_name(key)) or "@%s" % key)
            else:
                pieces.append(str(numbers.setdefault(key, len(numbers) + 1)))
        if match.group("bare"):
            # A narrative citation still takes the numeric style's brackets —
            # `@muhlberg2020` and `[@muhlberg2020]` both render `[4]`, because
            # in a numbered style the two positions do not differ. A figure
            # takes none: `fig. 1` is already the whole rendered form.
            if every_piece_a_citation:
                return "[%s]" % pieces[0]
            return pieces[0]
        if every_piece_a_citation:
            return "[%s]" % ",".join(pieces)
        return "[%s]" % "; ".join(pieces)

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
    counts = {PASS: 0, WARN: 0, FAIL: 0, SKIPPED: 0, NUMBER: 0}
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
    if counts[WARN]:
        # Counted apart from the fails, and printed only when something warned:
        # a permanent `0 warn` on every table would make "nothing warned" and
        # "this build does not warn" the same line, and the reported tier
        # already settled that question for its own count this way.
        tally += ", %d warn" % counts[WARN]
    if counts[NUMBER]:
        # Counted apart from the verdicts, because a number is not one.
        tally += ", %d reported" % counts[NUMBER]
    lines.append(tally)
    lines.append(
        "%s→ NOT a claim that this %s is finished"
        % (INDENT, SECTION if granularity == SECTION else DOCUMENT)
    )
    return "\n".join(lines) + "\n"


def run_gate(paper, mode):
    """Every row in registry order, and the failed rows by tier.

    Only the tiers that can gate have a bucket, so a reported row's FAIL lands
    nowhere at all. That is the mechanism by which it cannot reach the exit
    code: not a rule the caller has to honour, but a bucket that is not there.

    A row's `scope` is the granularity it can speak at, and `None` is both: a
    whole-document row prints `SKIPPED` under `--section`, and the supersession
    diff — one unit at a time, by definition — prints it over a whole document.
    One comparison for both directions, because *can this row speak here* is
    one question.

    An `ADVISORY_ON_CIRCULATE` check is the one row whose verdict depends on
    the mode: under `--circulate` its `FAIL` becomes a `WARN`, which no bucket
    accepts either, and under the two modes that answer the submit question —
    `--submit` and `--check`, the one `review-paper` runs — it is an ordinary
    gating failure. The table's *shape* is mode-independent, because
    `review-paper` reports it verbatim. `mode` is a property of the invocation
    rather than of the paper, so it arrives here and not on `Paper`.
    """
    rows = [(name, Verdict(PASS)) for name in PARSE_ROWS]
    failed = {HARD: [], GATING: []}
    for name, tier, scope, check in REGISTRY:
        label = name(paper) if callable(name) else name
        verdict = (
            Verdict.skipped()
            if scope is not None and scope != paper.granularity
            else check(paper)
        )
        if check in ADVISORY_ON_CIRCULATE and mode == CIRCULATE:
            verdict = verdict.advisory()
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
        "--supersedes",
        default=None,
        metavar="REF",
        help="the commit ref the superseded draft closed at; the supersession "
        "diff reports what this revision lost against the render at that ref, "
        "and reports it only",
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
        paper = load_paper(
            source_path, root, granularity, args.section, args.em_dash_threshold
        )
    except ParseError as error:
        sys.stderr.write("render-paper: parse error — %s\n" % error)
        return EXIT_PARSE
    except HardError as error:
        sys.stderr.write("render-paper: %s\n" % error)
        return EXIT_HARD

    # Outside the two handlers above, and deliberately: the old side of a
    # supersession is a finding, so the way it fails is a row and never an exit
    # code.
    paper.superseded = supersession(args.supersedes, root, source_path, paper)
    mode = SUBMIT if args.submit else CHECK if args.check else CIRCULATE
    rows, failed = run_gate(paper, mode)
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
