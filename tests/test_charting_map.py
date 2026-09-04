"""The map `charting` charts is read by skills `charting` knows nothing about.

That split is the whole hazard. A section can be read by three skills, shipped
as a slot by a fourth, and written by none — which is what happened: a framing
rule sat in a real map's `## Notes` while every skill that could have enforced
it looked under `## Style`, and the frame it banned was denied seven times in
seven independent sections with nothing detecting it.

These tests hold the half of the closure `charting` owns. Charting
**instantiates every declared section**, so a reader always has a state to
announce; and the slot `charting` ships carries no domain vocabulary, so the
key set keeps exactly one home. The rest pin the two things a map cannot get
wrong once it carries execution: what its blocking edges mean, and what its
index is allowed to assert.

The seam is the shipped `SKILL.md`, read through `shipped_text` so that a
heading of the skill and a heading inside the template the skill ships are
never confused for one another. Where a rule's whole content is its wording —
the `## Style` slot, which is specified to say one exact thing — the assertion
is on the wording; the assertions that catch a drifting rewrite are the
negative ones, which say what may never appear.
"""

import re
from pathlib import Path

import pytest
from shipped_text import MARKDOWN_BLOCK, SECTION, STYLE_KEYS, section_of, slot_of

REPO_ROOT = Path(__file__).resolve().parent.parent
CHARTING = REPO_ROOT / "skills" / "charting" / "SKILL.md"

# Sections a domain skill declares. `charting` names none of them when it
# states the requirement, because naming one is how a domain-agnostic skill
# starts carrying a domain.
DOMAIN_SECTIONS = ("Spine", "Skeleton")

# Named in full, because a section is located by its whole heading line.
TWO_MAP = "### The two-map pattern (for efforts that carry execution)"


@pytest.fixture(scope="module")
def skill():
    return CHARTING.read_text()


@pytest.fixture(scope="module")
def map_body(skill):
    """The map-body template — the block a charting session copies."""
    return MARKDOWN_BLOCK.search(skill, skill.index("### The map body")).group(1)


class TestChartingInstantiatesEveryDeclaredSection:
    """The class-A defect: an artifact read by three skills and written by
    none. Charting is the one step that can close it, because charting is
    where a map's sections come into existence at all."""

    def test_charting_instantiates_the_sections_the_domain_skill_declares(self, skill):
        step = section_of(skill, "### Chart the map")

        assert "instantiate every" in step
        assert "the domain skill" in step

    def test_a_missing_declared_section_is_a_charting_defect(self, skill):
        step = section_of(skill, "### Chart the map")

        assert "charting defect" in step

    def test_an_empty_declared_section_is_correct_and_an_absent_one_is_not(self, skill):
        """Empty is a state a reader can announce; absent is not. Two readers
        downstream are specified to announce which they found, and that
        announcement is only possible if charting made the distinction real."""
        step = section_of(skill, "### Chart the map")

        assert "empty" in step.lower()
        assert "absent" in step.lower()


class TestTheGenericMapBodySentence:
    """`charting` owns the requirement; the domain skill owns the template
    and the contents. The sentence stating that must name no domain section,
    or it is contradicted by its own wording."""

    def test_the_map_body_says_it_may_carry_domain_sections(self, skill):
        body = section_of(skill, "### The map body")

        assert "additional `##` sections" in body

    def test_the_sentence_names_no_domain_section(self, skill):
        body = section_of(skill, "### The map body")
        start = body.index("additional `##` sections")
        statement = body[start:].split("\n\n")[0]

        assert [name for name in DOMAIN_SECTIONS if name in statement] == []

    def test_the_domain_skill_owns_the_templates_and_charting_the_requirement(
        self, skill
    ):
        body = section_of(skill, "### The map body")
        start = body.index("additional `##` sections")
        statement = body[start:].split("\n\n")[0]

        assert "owns" in statement
        assert "requirement" in statement


class TestTheStyleSlot:
    """The slot `charting` ships. Its text is one line, deliberately: the key
    set, its value domains and its composition rules live in the drafting
    skill's schema, in exactly one place."""

    def test_the_slot_is_shipped_in_the_map_body(self, map_body):
        assert "Style" in SECTION.findall(map_body)

    def test_the_slot_says_only_keyed_deltas_plus_additive_prose(self, map_body):
        slot = slot_of(map_body, "Style")

        assert (
            slot
            == "<keyed deltas against the drafting skill's key set, plus additive prose>"
        )

    def test_an_effort_with_no_drafting_tickets_leaves_it_out(self, skill):
        """The slot ships by name, so without this the template would mandate
        it on a data-migration map. Its absence has a meaning downstream —
        *not a drafting effort* — which a mandated empty slot would erase."""
        body = section_of(skill, "### The map body")

        assert "no drafting tickets" in body

    def test_the_slot_enumerates_no_key(self, skill):
        """Anywhere in the skill, not just the slot: a key named in passing is
        the second home just as surely. Matched in the two forms the key set is
        written in — a code span and a stanza line — because `terms` is also an
        ordinary English word."""
        named = [
            key
            for key in STYLE_KEYS
            if "`%s`" % key in skill or re.search(r"^- %s:" % key, skill, re.MULTILINE)
        ]

        assert named == []


class TestDraftsAreHeldToStyleUnconditionally:
    """Under charting the section always exists when declared, so the hedge
    that let a drafting session skip it has nothing left to hedge against —
    and while it stood, `charting` and the drafting skill disagreed about
    whether `## Style` was optional or overriding."""

    def test_the_where_one_exists_hedge_is_gone(self, skill):
        assert "where one exists" not in skill

    def test_resolving_still_holds_every_draft_to_the_maps_style(self, skill):
        step = section_of(skill, "### Work through the map")

        assert "hold every draft to the map's `## Style`" in step


class TestTheTwoMapPattern:
    """Two maps, two edge semantics. Not derivable from the phase names, so an
    effort that reinvents the pattern gets it wrong."""

    def test_the_pattern_is_documented_where_charting_happens(self, skill):
        """Its reader is whoever charts a map, and charting is this skill's own
        Invocation step — so the block sits under it, not in a section of its
        own that a charting session has no reason to read."""
        assert TWO_MAP in skill
        assert skill.index("## Invocation") < skill.index(TWO_MAP)
        assert skill.index(TWO_MAP) < skill.index("### Work through the map")

    def test_the_planning_maps_edges_run_skeleton_to_ladder_to_briefs(self, skill):
        block = section_of(skill, TWO_MAP)

        assert "planning map" in block
        assert "skeleton ticket blocks the ladder ticket" in block
        assert "blocks every brief ticket" in block

    def test_the_draft_maps_edges_are_the_ladders_debt_edges(self, skill):
        """So the frontier is derived from the argument, and every parallelism
        the argument permits survives."""
        block = section_of(skill, TWO_MAP)

        assert "draft map" in block
        assert "debt edges" in block
        assert "blocking edges" in block
        assert "frontier" in block

    def test_the_draft_maps_notes_carries_only_what_is_per_effort(self, skill):
        """Five of seven blocks in the real draft map's `## Notes` were
        skill-level decisions, and one re-transcribed the `draft` ticket type
        — already wrong, because it turned on a verdict word abolished since."""
        block = section_of(skill, TWO_MAP)
        notes = block[block.index("`## Notes`") :]

        assert "per-effort" in notes
        for restated in ("ticket type", "file contract", "ordering", "framing rules"):
            assert restated in notes


class TestTheIndexIsKeyedByUnit:
    """A `draft` ticket's index line is not a stub — it makes claims a
    revision falsifies, in the view every session reads before choosing a
    ticket."""

    def test_draft_and_revise_carry_one_line_per_unit(self, map_body):
        index = slot_of(map_body, "Decisions so far")

        assert "`draft`" in index and "`revise`" in index
        assert "one line per unit" in index

    def test_a_revisions_line_takes_the_originals_slot(self, map_body):
        index = slot_of(map_body, "Decisions so far")

        assert "takes the original's slot" in index

    def test_the_superseded_ticket_stays_reachable(self, map_body):
        """Nothing is lost: the pointer already exists on the `revise` ticket,
        so the index needs no hand-maintained supersession marker."""
        index = slot_of(map_body, "Decisions so far")

        assert "Supersedes" in index

    def test_the_revise_type_points_at_the_rule(self, skill):
        """The type that causes a slot to be taken over says so. The pointer
        was deliberately withheld until the keying it refers to existed, so
        that no text quoted a rule the file did not yet carry."""
        revise = skill[skill.index("- **Revise** (HITL, checkpointed)") :]
        revise = revise[: revise.index("\n**Whole-piece review.**")]

        assert "index line takes the original's slot" in revise

    def test_resolving_a_draft_replaces_rather_than_appends(self, skill):
        """The template states the rule, but the step that writes the index is
        the one a session actually follows — and it said *append*, which is how
        a revision would come to sit beside the line it falsifies."""
        step = section_of(skill, "### Work through the map")

        assert "replacing" in step
        assert "keyed by **unit**" in step

    def test_every_other_type_is_still_one_line_per_ticket(self, map_body):
        index = slot_of(map_body, "Decisions so far")

        assert "one line per closed ticket" in index


class TestTheMapRecordsDecisionsNeverRecomputableState:
    """A real map recorded two document properties as settled fact and both
    were false."""

    def test_the_rule_is_stated_where_the_map_is_defined(self, skill):
        section = section_of(skill, "## The Map")

        assert "records decisions" in section
        assert "recomputable state" in section

    def test_asserting_a_document_property_is_banned(self, skill):
        section = section_of(skill, "## The Map")

        assert "document property" in section

    def test_the_index_carries_no_count_and_no_verdict(self, map_body):
        """A word count, a paragraph count and a review verdict are all
        statements about prose a revision may have replaced — and the index is
        read at the moment a session is orienting."""
        index = slot_of(map_body, "Decisions so far")

        assert "word count" not in index.lower()
        assert "verdict" not in index.lower()
