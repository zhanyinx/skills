"""The helpers that read a shipped `SKILL.md` have their own failure mode.

A skill's headings and the headings inside a template it ships for copying are
the same characters on the page. `wayfinder` really does carry `## Out of scope`
in its map-body template ninety lines above its own section of that name, so a
helper that finds a section by plain string search silently returns the
template's copy — and every assertion made against that span is then asserting
about the wrong text while still passing.

These pin the distinction on a fixture built to have it, rather than on the
skill, so the guard survives an edit to the skill that happens to remove the
collision.
"""

from pathlib import Path

from shipped_text import STYLE_KEYS, section_of, slot_of, without_fences

REPO_ROOT = Path(__file__).resolve().parent.parent

# A document whose template ships headings that collide with the document's
# own, in both directions: `## Notes` appears only inside the fence, and
# `## Out of scope` appears inside it *before* the real section.
COLLIDING = """# A skill

## The body

```markdown
## Notes

<the template's notes>

## Out of scope

<the template's out-of-scope>
```

Prose after the fence.

### A subsection

Belonging to `## The body`.

## Out of scope

The real section.

## Afterwards

Not part of it.
"""


class TestSectionOf:
    def test_a_heading_inside_a_fence_is_not_the_section(self):
        """The defect: `index()` finds the template's copy first."""
        found = section_of(COLLIDING, "## Out of scope")

        assert found.startswith("## Out of scope\n\nThe real section.")

    def test_a_section_ends_at_the_next_heading_of_its_level(self):
        found = section_of(COLLIDING, "## Out of scope")

        assert "Afterwards" not in found

    def test_a_subsection_ends_at_its_parents_next_sibling(self):
        """A `###` runs to the next heading of the same level *or shallower*.
        Stopping only at the next `###` would run it past its parent to the end
        of the file, and an assertion about the subsection would then be an
        assertion about everything after it."""
        found = section_of(COLLIDING, "### A subsection")

        assert "Belonging to" in found
        assert "The real section." not in found

    def test_a_section_absorbs_its_own_subsections(self):
        found = section_of(COLLIDING, "## The body")

        assert "A subsection" in found
        assert "The real section." not in found

    def test_a_heading_that_exists_only_inside_a_fence_is_refused(self):
        """Better a failure naming the heading than a span of the wrong text."""
        try:
            section_of(COLLIDING, "## Notes")
        except AssertionError as refusal:
            assert "## Notes" in str(refusal)
        else:
            raise AssertionError("a fence-only heading was accepted as a section")


class TestWithoutFences:
    def test_offsets_are_preserved(self):
        assert len(without_fences(COLLIDING)) == len(COLLIDING)

    def test_line_numbers_are_preserved(self):
        assert without_fences(COLLIDING).count("\n") == COLLIDING.count("\n")

    def test_fenced_content_is_gone_and_prose_is_not(self):
        masked = without_fences(COLLIDING)

        assert "the template's notes" not in masked
        assert "Prose after the fence." in masked


class TestSlotOf:
    def test_a_slot_is_read_from_the_template(self):
        template = "## One\n\n<first>\n\n## Two\n\n<second>\n"

        assert slot_of(template, "Two") == "<second>"

    def test_an_absent_slot_is_refused_by_name(self):
        try:
            slot_of("## One\n\n<first>\n", "Three")
        except AssertionError as refusal:
            assert "Three" in str(refusal)
        else:
            raise AssertionError("an absent slot was accepted")


class TestTheKeySetHasOneHome:
    def test_the_keys_are_the_ones_the_schema_defines(self):
        """The tuple two test modules assert against is a transcription, so it
        is itself checked against the schema that owns it."""
        schema = (REPO_ROOT / "skills" / "write-paper" / "STYLE-STANZA.md").read_text()

        for key in STYLE_KEYS:
            assert "`%s`" % key in schema
