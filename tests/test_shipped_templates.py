"""The templates `write-paper` ships are the ones every effort copies.

`render-paper` parses a brief but does not own its format, so the two live in
different files and can drift apart in silence: a shipped template that renames
a zone hands every effort a brief the overlap instrument reports as unparsed and
measures nothing against. These tests close that gap through the same seam every
other test uses — the CLI, over a fixture paper whose briefs are the shipped
templates verbatim.

The rest pin the two ceilings the brief format exists to enforce, because both
are properties of the template text itself: at most three propositions, and one
budget per unit with no sub-allocation.
"""

import re
import shutil
from pathlib import Path

import pytest
from shipped_text import MARKDOWN_BLOCK as FENCE
from shipped_text import SECTION as ZONE
from shipped_text import STYLE_KEYS

REPO_ROOT = Path(__file__).resolve().parent.parent
WRITE_PAPER = REPO_ROOT / "skills" / "write-paper"
BRIEF_FORMAT = WRITE_PAPER / "BRIEF-FORMAT.md"
MAP_SECTIONS = WRITE_PAPER / "MAP-SECTIONS.md"
SKILL = WRITE_PAPER / "SKILL.md"

RELATION_LINE = re.compile(r"^(rung|closes|opens|restates)\s*:", re.IGNORECASE)
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")

# The zone headings `render-paper`'s brief parser knows. A template heading
# outside this set is an unparsed zone, which the instrument reports and then
# measures nothing against.
READER_FACING = ("Argument", "Inventory")
BRIEF_ZONES = READER_FACING + (
    "Must not claim",
    "Sheds",
    "Verify before prose",
    "Sources",
)

# `## Style`'s map-section template may name none of the style keys: the key
# set has one home, and a domain-agnostic map template that enumerated it would
# be the second. `STYLE_KEYS` is imported rather than transcribed for the same
# reason — this module and the `wayfinder` one both assert against it.


def brief_templates():
    """The brief templates the format doc ships, keyed by reader-facing zone."""
    blocks = [
        block
        for block in FENCE.findall(BRIEF_FORMAT.read_text())
        if block.startswith("# Brief")
    ]
    return dict(
        (
            next(zone for zone in ZONE.findall(block) if zone in READER_FACING),
            block,
        )
        for block in blocks
    )


def zone_of(template, name):
    """One zone's lines, less the ladder line — which names the unit's relation
    to the rung above it and is bookkeeping rather than a proposition."""
    body = template.split("## %s\n" % name, 1)[1].split("\n## ", 1)[0]
    return [
        line.strip()
        for line in body.splitlines()
        if line.strip() and not RELATION_LINE.match(line.strip())
    ]


@pytest.fixture
def paper_from_templates(tmp_path, run_in):
    """A fixture paper whose two briefs are the shipped templates verbatim.

    `brief-mirror` is the fixture with one originating unit and one
    non-originating one, so it takes one template each — the same pairing the
    ladder makes.
    """
    where = tmp_path / "shipped"
    shutil.copytree(REPO_ROOT / "tests" / "fixtures" / "brief-mirror", where)
    templates = brief_templates()
    (where / "briefs" / "results.md").write_text(templates["Argument"])
    (where / "briefs" / "availability.md").write_text(templates["Inventory"])
    return run_in(where, "MANUSCRIPT.working.md", "--check")


class TestBothTemplatesShip:
    def test_the_format_doc_ships_one_template_per_format(self):
        assert sorted(brief_templates()) == ["Argument", "Inventory"]

    def test_each_carries_exactly_one_reader_facing_zone(self):
        for name, template in brief_templates().items():
            facing = [z for z in ZONE.findall(template) if z in READER_FACING]

            assert facing == [name]

    def test_the_other_four_zones_are_shared_unchanged(self):
        argument, inventory = (
            [z for z in ZONE.findall(template) if z not in READER_FACING]
            for template in (
                brief_templates()["Argument"],
                brief_templates()["Inventory"],
            )
        )

        assert argument == inventory == list(BRIEF_ZONES[2:])


class TestTheRendererParsesThem:
    """The acceptance the two files cannot verify separately."""

    def test_neither_template_carries_a_zone_the_parser_does_not_know(
        self, paper_from_templates
    ):
        assert "unparsed zone" not in paper_from_templates.report

    def test_neither_template_lacks_a_reader_facing_zone(self, paper_from_templates):
        assert "no `## Argument` or `## Inventory` zone" not in (
            paper_from_templates.report
        )

    def test_the_briefs_are_read_rather_than_reported_unreadable(
        self, paper_from_templates
    ):
        assert "cannot be read" not in paper_from_templates.report
        assert paper_from_templates.exit_code == 0


class TestTheCeilingsTheFormatExistsToEnforce:
    def test_the_argument_zone_states_at_most_three_propositions(self):
        lines = zone_of(brief_templates()["Argument"], "Argument")
        propositions = [
            sentence
            for sentence in SENTENCE_BREAK.split(" ".join(lines))
            if sentence.strip()
        ]

        assert 0 < len(propositions) <= 3

    def test_one_budget_per_template_and_no_sub_allocation(self):
        # A per-block allocation is a layout instruction wearing a number, and
        # a child slot has no budget to write one into.
        for template in brief_templates().values():
            assert template.count("Budget:") == 1

    def test_the_ladder_line_is_specified_for_both_formats(self):
        for template in brief_templates().values():
            header = template.splitlines()[2]

            assert RELATION_LINE.match(header)


class TestTheMapSectionTemplates:
    def test_all_three_ship_as_one_asset(self):
        text = MAP_SECTIONS.read_text()

        for section in ("## `## Style`", "## `## Spine`", "## `## Skeleton`"):
            assert section in text

    def test_the_style_template_enumerates_no_key(self):
        text = MAP_SECTIONS.read_text()

        assert [key for key in STYLE_KEYS if key in text] == []


class TestTheSkillPointsAtWhatItShips:
    """An asset nothing points at is an asset nothing reads — the defect that
    left a framing rule unread in a map while three skills looked for it."""

    def test_both_assets_are_linked_from_the_skill(self):
        text = SKILL.read_text()

        assert "(BRIEF-FORMAT.md)" in text
        assert "(MAP-SECTIONS.md)" in text
