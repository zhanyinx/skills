"""Reading the Markdown the skills ship, as structure rather than as prose.

A `SKILL.md` carries two kinds of `##` line that look identical: its own
headings, and the headings *inside* a fenced template it ships for someone else
to copy. Anything that tells them apart by string search gets the wrong one —
`## Out of scope` appears in `charting`'s map-body template ninety lines before
the section of that name. So every helper here masks fenced blocks first.

It lives outside both test modules because the alternative is the defect the
tests themselves are about: one fact with more than one home. The style key set
in particular is defined in `write-paper`'s `STYLE-STANZA.md` and asserted
against by two different modules.
"""

import re

# A fenced block of any kind, and the typed `markdown` blocks that are the
# templates a skill ships for copying.
ANY_FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
MARKDOWN_BLOCK = re.compile(r"^```markdown\n(.*?)^```", re.MULTILINE | re.DOTALL)
SECTION = re.compile(r"^## (.+)$", re.MULTILINE)

# The style stanza's closed key set, whose one home is `write-paper`'s
# `STYLE-STANZA.md`. Two modules assert that a template names none of them.
STYLE_KEYS = (
    "active-we",
    "plain-words",
    "build-in-steps",
    "spelling-variant",
    "em-dash-threshold",
    "terms",
)


def collapsed(text):
    """The text as one line, every run of whitespace collapsed to one space.

    Two things need it. An assertion reads as prose rather than depending on
    where the source wrapped its lines; and a phrase asserted *absent* is
    otherwise absent for the wrong reason — a deleted exemplar re-introduced
    across a line break is the same sentence to a reader and a different string
    to `in`, so a contract check that skipped this step would pass on a file
    that had put it back.
    """
    return re.sub(r"\s+", " ", text)


def without_fences(text):
    """The text with every fenced block blanked, offsets preserved.

    Blanking rather than deleting, so an index into the result still points at
    the same character of the original.
    """
    return ANY_FENCE.sub(lambda block: re.sub(r"[^\n]", " ", block.group(0)), text)


def section_of(text, heading):
    """One section of a document, from its heading to the next heading of the
    same level or shallower.

    Both ends are found in the fence-masked text: a heading that also appears
    inside a shipped template must not be mistaken for the real one, at either
    end of the span.
    """
    masked = without_fences(text)
    level = len(heading) - len(heading.lstrip("#"))
    start = re.search(r"^%s$" % re.escape(heading), masked, re.MULTILINE)
    assert start, "no `%s` heading outside a fenced block" % heading
    following = re.compile(r"^#{1,%d} " % level, re.MULTILINE)
    end = following.search(masked, start.end())
    return text[start.start() : end.start() if end else len(text)]


def slot_of(template, name):
    """One `##` slot's body, from a template someone is meant to copy."""
    for slot in re.split(r"^## ", template, flags=re.MULTILINE)[1:]:
        head, _, body = slot.partition("\n")
        if head.strip() == name:
            return body.strip()
    raise AssertionError("no `## %s` slot in the template" % name)
