"""The shipped style stanza is a schema, and it ships no house style.

`write-paper` installs publicly, so a filled value in its style asset installs
one person's spelling, voice and em-dash threshold on every installer who never
opens the file — a house style with the authorship filed off. The exemplar is
blank for that reason, and blank is exactly the property that decays silently:
one helpful edit filling in "sensible" values reads as an improvement and is the
defect. So it is asserted here rather than stated in prose, which is the same
reason the em-dash ban became a command — a rule an agent can talk itself out of
was violated 98 times through six clean reviews.

These tests read the shipped files directly, as `test_packaging.py` does. There
is no CLI seam here: the stanza is composed by a session, not by the renderer.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WRITE_PAPER = REPO_ROOT / "skills" / "write-paper"
ASSET = WRITE_PAPER / "STYLE-STANZA.md"
SKILL = WRITE_PAPER / "SKILL.md"

CLOSED_KEY_SET = {
    "active-we",
    "plain-words",
    "build-in-steps",
    "spelling-variant",
    "em-dash-threshold",
    "terms",
}

KEY_LINE = re.compile(r"^\s*-\s+([a-z-]+):(.*)$")
TABLE_KEY = re.compile(r"^\|\s*`([a-z-]+)`\s*\|")


def sections(text):
    """The file split into its `##` sections, keyed by heading.

    Fence-aware: the exemplar and the worked example are themselves markdown
    carrying `##` headings, and a splitter that counted those would cut the
    blocks it exists to read.
    """
    found = {}
    heading = None
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        if line.startswith("## ") and not fenced:
            heading = line.removeprefix("## ").strip()
            found[heading] = [heading]
        elif heading is not None:
            found[heading].append(line)
    return {name: "\n".join(body) for name, body in found.items()}


def fenced_blocks(text):
    """The bodies of every fenced block in one chunk of markdown."""
    blocks, current = [], None
    for line in text.splitlines():
        if line.startswith("```"):
            if current is None:
                current = []
            else:
                blocks.append("\n".join(current))
                current = None
        elif current is not None:
            current.append(line)
    return blocks


def key_lines(block):
    """Every `- key: value` line in a block, as (key, value) pairs."""
    pairs = []
    for line in block.splitlines():
        match = KEY_LINE.match(line)
        if match and match.group(1) in CLOSED_KEY_SET:
            pairs.append((match.group(1), match.group(2).strip()))
    return pairs


def the_one(matching, name):
    """The single section whose heading matches, asserted to be single."""
    matched = [body for heading, body in matching.items() if name in heading.lower()]
    assert len(matched) == 1, "expected exactly one %r section, found %d" % (
        name,
        len(matched),
    )
    return matched[0]


def asset():
    return sections(ASSET.read_text())


class TestTheAssetShips:
    def test_it_lives_in_the_skill_that_reads_it(self):
        """Self-consumed: a cross-skill reach breaks on partial install."""
        assert ASSET.is_file()

    def test_the_skill_points_at_it(self):
        assert ASSET.name in SKILL.read_text()


class TestTheExemplarIsValuesBlank:
    def test_every_key_is_present(self):
        exemplar = the_one(asset(), "values-blank exemplar")
        (block,) = fenced_blocks(exemplar)

        assert {key for key, _ in key_lines(block)} == CLOSED_KEY_SET

    def test_no_key_carries_a_value(self):
        exemplar = the_one(asset(), "values-blank exemplar")
        (block,) = fenced_blocks(exemplar)

        filled = [key for key, value in key_lines(block) if value != ""]

        assert filled == []


class TestNoHouseStyleShips:
    def test_filled_values_appear_only_under_an_example_label(self):
        """A filled key outside the worked example is a shipped default."""
        leaked = {
            heading
            for heading, body in asset().items()
            if "example" not in heading.lower()
            for block in fenced_blocks(body)
            if any(value for _, value in key_lines(block))
        }

        assert leaked == set()

    def test_there_is_at_most_one_worked_example(self):
        labelled = [h for h in asset() if "worked example" in h.lower()]

        assert len(labelled) <= 1

    def test_the_worked_example_disclaims_being_a_default(self):
        example = the_one(asset(), "worked example")

        assert "never a default" in example or "not a default" in example

    # The no-filled-key guard over a `SKILL.md` moved to
    # `test_skill_contract.py`, which runs it over all five rather than this
    # one. That assertion strictly contains the one that stood here.


class TestTheKeySetIsClosed:
    def test_the_schema_table_names_exactly_the_closed_set(self):
        table = the_one(asset(), "key set is closed")
        declared = {
            match.group(1)
            for line in table.splitlines()
            if (match := TABLE_KEY.match(line))
        }

        assert declared == CLOSED_KEY_SET

    def test_the_skill_names_the_same_set(self):
        """Two copies of the set that disagree is worse than one."""
        text = SKILL.read_text()
        named = {key for key in CLOSED_KEY_SET if "`%s`" % key in text}

        assert named == CLOSED_KEY_SET
