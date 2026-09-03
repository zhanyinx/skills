"""`render-paper` — the CLI, the exit-code contract, the verdict table.

Every test invokes the CLI as a subprocess over a fixture paper and asserts on
what a caller can see: the exit code, the emitted document, the verdict report.
"""

PASS = "PASS"
SKIPPED = "SKIPPED — OUT OF SCOPE AT THIS GRANULARITY"


def verdict_for(report, name):
    """What one row of the table printed, read out of the table by row name."""
    for line in report.splitlines():
        stripped = line.strip()
        if stripped.startswith(name + " "):
            return stripped[len(name) :].strip()
    raise AssertionError("no `%s` row in this table:\n%s" % (name, report))


class TestCheckMode:
    def test_clean_paper_passes_every_check_and_exits_zero(self, render, golden):
        result = render("clean", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert result.report == golden("clean-check.txt")

    def test_check_emits_no_document(self, render):
        result = render("clean", "MANUSCRIPT.working.md", "--check")

        assert result.document == ""


class TestHeadingInjection:
    def test_circulate_injects_every_heading_from_the_skeleton(self, render, golden):
        result = render("clean", "MANUSCRIPT.working.md", "--circulate")

        assert result.exit_code == 0
        assert result.document == golden("clean-circulate.md")

    def test_a_heading_in_a_source_is_refused(self, render):
        result = render("heading-in-source", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 3
        assert "`## Accuracy` is a heading" in result.report

    def test_an_underlined_heading_in_a_source_is_refused_too(self, paper, run_in):
        where = paper("clean")
        source = where / "MANUSCRIPT.working.md"
        source.write_text(
            source.read_text().replace(
                "Panels were acquired", "Acquisition\n-----------\n\nPanels were acquired"
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 3
        assert "`Acquisition` is a heading" in result.report

    def test_a_heading_inside_a_comment_is_neither_refused_nor_rendered(self, render):
        # The clean fixture carries a comment whose second line reads
        # `## superseded outline`, so the heading scan has to see through the
        # comment channel rather than over it.
        result = render("clean", "MANUSCRIPT.working.md", "--circulate")

        assert result.exit_code == 0
        assert "superseded outline" not in result.document

    def test_no_comment_of_any_shape_survives_into_the_render(self, render):
        result = render("clean", "MANUSCRIPT.working.md", "--circulate")

        assert "<!--" not in result.document
        assert "confirm the tool list" not in result.document
        assert "R1 — abstract" not in result.document

    def test_submit_over_a_finished_paper_emits_the_same_document(self, render, golden):
        result = render("clean", "MANUSCRIPT.working.md", "--submit")

        assert result.exit_code == 0
        assert result.document == golden("clean-circulate.md")


class TestHardErrorTier:
    """A hard error means the emitted document is not the document the source
    describes, so it emits nothing, in both render modes."""

    def test_a_slot_anchored_twice_is_a_hard_error(self, render):
        result = render("duplicate-slot", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 2
        assert "slot integrity            FAIL" in result.report
        assert "anchored twice" in result.report

    def test_an_anchor_naming_no_skeleton_slot_is_a_hard_error(self, render):
        result = render("orphan-slot", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 2
        assert "slot integrity            FAIL" in result.report
        assert "absent from the skeleton" in result.report

    def test_an_originating_slot_bearing_children_is_a_hard_error(self, render):
        result = render("originating-children", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 2
        assert "originating slot children FAIL" in result.report
        assert "opens a debt and carries 2 children" in result.report

    def test_a_hard_error_emits_nothing_under_circulate(self, render):
        result = render("duplicate-slot", "MANUSCRIPT.working.md", "--circulate")

        assert result.exit_code == 2
        assert result.document == ""

    def test_a_hard_error_emits_nothing_under_submit(self, render):
        result = render("duplicate-slot", "MANUSCRIPT.working.md", "--submit")

        assert result.exit_code == 2
        assert result.document == ""


class TestSubmitGatingTier:
    """The render is faithful but the work is unfinished, so `--circulate`
    still emits and `--submit` refuses."""

    def test_an_unfilled_slot_fails_the_gate(self, render, golden):
        result = render("unfilled-slot", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 1
        assert result.report == golden("unfilled-slot-check.txt")

    def test_circulate_still_emits_and_marks_the_gap(self, render):
        result = render("unfilled-slot", "MANUSCRIPT.working.md", "--circulate")

        assert result.exit_code == 1
        assert "## Results" in result.document
        assert "⟦HOLE: prose for results⟧" in result.document

    def test_submit_refuses_and_prints_the_list(self, render, golden):
        result = render("unfilled-slot", "MANUSCRIPT.working.md", "--submit")

        assert result.exit_code == 1
        assert result.document == ""
        assert result.report.startswith(golden("unfilled-slot-check.txt"))
        assert "--submit refused: 1 gating check failed" in result.report
        assert "unfilled skeleton slot: `results`" in result.report


class TestParseErrorTier:
    """A parse error means nothing ran, so the table is absent rather than
    full of failures."""

    def test_a_malformed_anchor_is_a_parse_error(self, render):
        result = render("malformed-anchor", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 3
        assert "malformed anchor" in result.report

    def test_a_parse_error_prints_no_table(self, render):
        result = render("malformed-anchor", "MANUSCRIPT.working.md", "--check")

        assert "PASS" not in result.report
        assert "FAIL" not in result.report
        assert "pass, " not in result.report

    def test_a_parse_error_emits_no_document_in_either_mode(self, render):
        for mode in ("--circulate", "--submit"):
            result = render("malformed-anchor", "MANUSCRIPT.working.md", mode)

            assert result.exit_code == 3
            assert result.document == ""

    def test_a_child_slot_with_no_partitions_on_is_a_parse_error(self, render):
        result = render("malformed-skeleton", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 3
        assert "child slot `results-accuracy` has no `partitions-on`" in result.report


class TestSectionGranularity:
    def test_whole_document_rows_are_printed_as_skipped(self, render):
        result = render("clean", "MANUSCRIPT.working.md", "--check", "--section", "methods")

        rows = dict(
            (line[:27].strip(), line[27:].strip())
            for line in result.report.splitlines()
            if line.startswith("  ") and line[2:3] != " "
        )

        assert "slot integrity" in rows
        assert rows["slot integrity"] != PASS
        assert rows["slot integrity"] == SKIPPED

    def test_the_section_table_is_verbatim(self, render, golden):
        result = render("clean", "MANUSCRIPT.working.md", "--check", "--section", "methods")

        assert result.exit_code == 0
        assert result.report == golden("clean-section-check.txt")

    def test_a_section_render_injects_only_its_own_subtree(self, render, golden):
        result = render(
            "clean", "MANUSCRIPT.working.md", "--circulate", "--section", "methods"
        )

        assert result.document == golden("clean-section-circulate.md")

    def test_the_unit_is_derived_when_section_is_bare(self, render, golden):
        result = render("unfilled-slot", "MANUSCRIPT.working.md", "--check", "--section")

        assert result.exit_code == 0
        assert "unfilled skeleton slot    PASS" in result.report


class TestTheCLIContract:
    def test_there_is_no_default_mode(self, render):
        result = render("clean", "MANUSCRIPT.working.md")

        assert result.exit_code == 2
        assert result.document == ""
        assert "--circulate" in result.report

    def test_two_modes_at_once_are_refused(self, render):
        result = render("clean", "MANUSCRIPT.working.md", "--check", "--submit")

        assert result.exit_code == 2
        assert result.document == ""

    def test_scaffold_is_a_named_mode(self, render):
        result = render("clean", "MANUSCRIPT.working.md", "--scaffold")

        assert result.document == ""
        assert "--scaffold" in result.report

    def test_clean_is_not_an_output_token(self, render):
        for mode in ("--check", "--circulate", "--submit"):
            result = render("clean", "MANUSCRIPT.working.md", mode)

            assert "CLEAN" not in result.report
            assert "CLEAN" not in result.document


class TestPrePromotion:
    """Before promotion the sections are still separate files, so the source
    is a directory and the order is the skeleton's, never the filesystem's."""

    def test_a_directory_of_section_sources_renders_in_skeleton_order(
        self, render, golden
    ):
        result = render("pre-promotion", "drafts", "--circulate")

        assert result.exit_code == 0
        assert result.document == golden("pre-promotion-circulate.md")

    def test_the_paper_root_is_found_from_a_source_below_it(self, render):
        result = render("pre-promotion", "drafts/abstract.md", "--check", "--section")

        assert result.exit_code == 0


class TestWhatShips:
    def test_the_runtime_imports_only_the_standard_library(self):
        import re
        import sys

        from conftest import SCRIPT

        imported = set()
        for line in SCRIPT.read_text().splitlines():
            match = re.match(r"^(?:import|from) ([a-zA-Z_][\w.]*)", line)
            if match:
                imported.add(match.group(1).split(".")[0])

        assert imported
        assert imported <= set(sys.stdlib_module_names)

    def test_the_skill_ships_the_script_it_consumes(self):
        from conftest import SCRIPT

        assert SCRIPT.exists()
        assert SCRIPT.parent.parent.name == "render-paper"


class TestProseOutsideEverySlot:
    def test_prose_before_a_source_file_s_first_anchor_is_a_hard_error(self, render):
        result = render("stray-prose", "drafts", "--check")

        assert result.exit_code == 2
        assert "prose outside every slot in results.md" in result.report

    def test_that_prose_never_lands_under_another_slot(self, render):
        result = render("stray-prose", "drafts", "--circulate")

        assert result.document == ""


class TestUnclosedComment:
    def test_an_unclosed_comment_is_a_parse_error(self, render):
        result = render("unclosed-comment", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 3
        assert "MANUSCRIPT.working.md:9: unclosed comment" in result.report
        assert "PASS" not in result.report


class TestTheSkeletonFormat:
    """The format `render-paper` documents is only real where a malformation
    stops the render, so every rule the format spec states is a parse error."""

    def test_a_missing_skeleton_is_a_parse_error(self, paper, run_in):
        where = paper("clean")
        (where / "skeleton.md").unlink()

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 3
        assert "skeleton.md: declared input is missing" in result.report

    def test_a_missing_venue_limit_is_a_parse_error(self, paper, run_in):
        where = paper("clean")
        skeleton = where / "skeleton.md"
        skeleton.write_text(
            skeleton.read_text().replace("| limit | 4000 words |\n", "")
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 3
        assert "no `limit` field" in result.report

    def test_a_word_budget_cannot_be_written_into_the_skeleton(self, paper, run_in):
        where = paper("clean")
        skeleton = where / "skeleton.md"
        skeleton.write_text(
            skeleton.read_text().replace(
                "| limit | 4000 words |", "| limit | 4000 words |\n| budget | 800 words |"
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 3
        assert "unknown field `budget`" in result.report

    def test_a_tree_that_skips_a_level_is_a_parse_error(self, paper, run_in):
        where = paper("clean")
        skeleton = where / "skeleton.md"
        skeleton.write_text(
            skeleton.read_text().replace(
                "| methods-imaging | 3 | Imaging | procedure |",
                "| methods-imaging | 4 | Imaging | procedure |",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 3
        assert "skips a level" in result.report

    def test_a_roster_carries_names_only(self, paper, run_in):
        where = paper("clean")
        skeleton = where / "skeleton.md"
        skeleton.write_text(
            skeleton.read_text().replace(
                "| figure | registration-accuracy |", "| panel | registration-accuracy-b |"
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 3
        assert "is not a roster kind" in result.report


class TestTheSpineFormat:
    def test_a_missing_spine_is_a_parse_error(self, paper, run_in):
        where = paper("clean")
        (where / "spine.md").unlink()

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 3
        assert "spine.md: declared input is missing" in result.report

    def test_a_second_drafted_actual_is_a_parse_error(self, paper, run_in):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(
            spine.read_text().replace(
                "- closes: D1",
                "- closes: D1\n- actual: drafted as planned\n- actual: drafted, hedged",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 3
        assert "the drafted actual is overwritten, never appended" in result.report

    def test_rungs_are_ordered(self, paper, run_in):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(spine.read_text().replace("### R3 — methods", "### R7 — methods"))

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 3
        assert "is out of order, expected `R3`" in result.report

    def test_a_relation_outside_the_four_is_a_parse_error(self, paper, run_in):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(
            spine.read_text().replace(
                "- restates: R4", "- takeaway: the pipeline works"
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 3
        assert "unknown relation `takeaway`" in result.report


class TestUnitRungPairing:
    """One unit is one rung, 1:1. A mismatch is a fact about the two files
    together rather than a malformation of either, so it is a printed row."""

    def test_a_unit_with_no_rung_is_a_hard_error(self, paper, run_in):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(spine.read_text().split("### R4 — results")[0].rstrip() + "\n")

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 2
        assert "unit / rung pairing       FAIL" in result.report
        assert "`results` carries no rung" in result.report

    def test_a_rung_naming_something_that_is_not_a_unit_is_a_hard_error(
        self, paper, run_in
    ):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(
            spine.read_text().replace("### R3 — methods", "### R3 — methods-imaging")
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 2
        assert "R3 names `methods-imaging`, which is not a unit" in result.report

    def test_the_pairing_is_checked_at_section_granularity_too(self, paper, run_in):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(
            spine.read_text().replace("### R3 — methods", "### R3 — methods-imaging")
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check", "--section", "methods")

        assert result.exit_code == 2
        assert SKIPPED not in result.report.split("unit / rung pairing")[1].split("\n")[0]


class TestParentSlotsBearProseOptionally:
    """A parent slot's own prose is permitted, not owed: a unit forced to fill
    one would need a manufactured first child, which is the stack of labelled
    blocks this design refuses."""

    def test_a_parent_with_no_prose_of_its_own_passes(self, paper, run_in):
        where = paper("clean")
        source = where / "MANUSCRIPT.working.md"
        source.write_text(
            source.read_text().replace(
                "The pipeline runs as five stages, each reproducible from the "
                "committed configuration.\n",
                "",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert "unfilled skeleton slot    PASS" in result.report

    def test_and_renders_its_heading_with_no_hole_under_it(self, paper, run_in):
        where = paper("clean")
        source = where / "MANUSCRIPT.working.md"
        source.write_text(
            source.read_text().replace(
                "The pipeline runs as five stages, each reproducible from the "
                "committed configuration.\n",
                "",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--circulate")

        assert "## Methods\n\n### Imaging" in result.document
        assert "HOLE" not in result.document


class TestAnUnfilledTitle:
    """A title is the central claim compressed, so the skeleton ticket may
    leave the H1 to be filled late."""

    def test_an_unfilled_title_gates_rather_than_failing_to_parse(self, paper, run_in):
        where = paper("clean")
        skeleton = where / "skeleton.md"
        skeleton.write_text(
            skeleton.read_text().replace(
                "| title | Registration accuracy in cyclic imaging |", "| title | |"
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 1
        assert "unfilled skeleton slot    FAIL — 1 (the document title)" in result.report

    def test_and_circulate_marks_it_in_the_h1(self, paper, run_in):
        where = paper("clean")
        skeleton = where / "skeleton.md"
        skeleton.write_text(
            skeleton.read_text().replace(
                "| title | Registration accuracy in cyclic imaging |", "| title | |"
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--circulate")

        assert result.exit_code == 1
        assert "# ⟦HOLE: the document title⟧" in result.document


class TestFencedCodeBlocks:
    """Inside a fence nothing is parsed: a source showing anchor syntax in a
    fence is showing it, not using it."""

    def test_a_fenced_anchor_is_not_an_anchor(self, render):
        result = render("fenced", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert "not-an-anchor" not in result.report

    def test_a_fenced_comment_is_neither_stripped_nor_unclosed(self, render):
        result = render("fenced", "MANUSCRIPT.working.md", "--circulate")

        assert result.exit_code == 0
        assert "<!-- slot: not-an-anchor -->" in result.document
        assert "<!-- an unclosed comment, shown as text" in result.document

    def test_a_fenced_heading_is_not_a_heading(self, render):
        result = render("fenced", "MANUSCRIPT.working.md", "--circulate")

        assert result.exit_code == 0
        assert "# stage 2" in result.document


class TestNoProseIsEverDroppedSilently:
    def test_a_slot_anchored_twice_keeps_both_blocks_at_section_granularity(
        self, render
    ):
        # At section granularity `slot integrity` is out of scope, so nothing
        # can report the duplicate — which is exactly why the render must not
        # quietly pick one of the two blocks and drop the other.
        result = render(
            "duplicate-slot", "MANUSCRIPT.working.md", "--circulate", "--section", "abstract"
        )

        assert result.exit_code == 0
        assert "The paper measures one thing." in result.document
        assert "A second block claiming the same slot." in result.document


class TestChainBookkeeping:
    """The chain walk is a graph query over declared metadata: every declared
    debt opened exactly once, closed exactly once, none dangling at the end.

    Submit-gating, because the render is faithful — the document says what the
    source says — and it is the argument that is unfinished.
    """

    def test_a_debt_nobody_closes_fails_the_gate(self, paper, run_in):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(spine.read_text().replace("- closes: D1\n", ""))

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 1
        assert verdict_for(result.report, "chain bookkeeping").startswith("FAIL")
        assert "`D1` is opened by R2 and never closed" in result.report

    def test_a_debt_opened_twice_fails_the_gate(self, paper, run_in):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(
            spine.read_text().replace(
                "- restates: R4",
                "- opens: D1 (closed by R4) — whether the registration is accurate",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 1
        assert "`D1` is opened twice, by R1 and R2" in result.report

    def test_a_debt_closed_twice_fails_the_gate(self, paper, run_in):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(
            spine.read_text().replace(
                "- establishes: the procedures are reproducible from the committed"
                " configuration",
                "- establishes: the procedures are reproducible from the committed"
                " configuration\n- closes: D1",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 1
        assert "`D1` is closed twice, by R3 and R4" in result.report

    def test_closing_a_debt_no_rung_opens_fails_the_gate(self, paper, run_in):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(spine.read_text().replace("- closes: D1", "- closes: D9"))

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 1
        assert "R4 closes `D9`, which no rung opens" in result.report

    def test_the_declared_closer_must_be_the_rung_that_closes(self, paper, run_in):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(
            spine.read_text()
            .replace("- closes: D1\n", "")
            .replace(
                "- establishes: the procedures are reproducible from the committed"
                " configuration",
                "- establishes: the procedures are reproducible from the committed"
                " configuration\n- closes: D1",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 1
        assert "`D1` declares R4 closes it, but R3 does" in result.report

    def test_the_declared_closer_is_checked_against_every_rung_that_closes(
        self, paper, run_in
    ):
        # Two rungs close D1 and neither is the declared one, so the ladder is
        # wrong twice over — and the second finding must not vanish behind the
        # first.
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(
            spine.read_text()
            .replace("- closes: D1\n", "")
            .replace("- restates: R4", "- restates: R4\n- closes: D1")
            .replace(
                "- establishes: the procedures are reproducible from the committed"
                " configuration",
                "- establishes: the procedures are reproducible from the committed"
                " configuration\n- closes: D1",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 1
        assert "`D1` is closed twice, by R1 and R3" in result.report
        assert "`D1` declares R4 closes it, but R1 and R3 do" in result.report

    def test_a_declared_closer_that_is_not_a_rung_fails_the_gate(self, paper, run_in):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(spine.read_text().replace("(closed by R4)", "(closed by R9)"))

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 1
        assert (
            "`D1` declares R9 closes it, which is not a rung in this ladder"
            in result.report
        )

    def test_a_restated_rung_that_does_not_exist_fails_the_gate(self, paper, run_in):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(spine.read_text().replace("- restates: R4", "- restates: R9"))

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 1
        assert "R1 restates R9, which is not a rung in this ladder" in result.report

    def test_an_unclosed_debt_still_circulates_and_refuses_submission(
        self, paper, run_in
    ):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(spine.read_text().replace("- closes: D1\n", ""))

        circulated = run_in(where, "MANUSCRIPT.working.md", "--circulate")
        submitted = run_in(where, "MANUSCRIPT.working.md", "--submit")

        assert circulated.exit_code == 1
        assert "## Results and discussion" in circulated.document
        assert submitted.exit_code == 1
        assert submitted.document == ""
        assert (
            "chain bookkeeping: `D1` is opened by R2 and never closed"
            in submitted.report
        )


class TestDebtPrecedence:
    """Every debt is opened in a unit no later than the unit that closes it, or
    the reader meets the payoff before the promise."""

    def test_a_debt_closed_before_it_is_opened_fails_the_gate(self, paper, run_in):
        where = paper("clean")
        spine = where / "spine.md"
        spine.write_text(
            spine.read_text()
            .replace("- restates: R4", "- restates: R4\n- closes: D2")
            .replace(
                "- closes: D1",
                "- closes: D1\n- opens: D2 (closed by R1) — whether the drift is bounded",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 1
        assert (
            "`D2` is opened in `results` and closed in `abstract`, which the "
            "skeleton reads first" in result.report
        )
        assert verdict_for(result.report, "chain bookkeeping") == PASS

    def test_precedence_is_the_skeletons_order_and_not_the_ladders(self, paper, run_in):
        # The abstract is the ladder's *last* rung and the document's *first*
        # unit. A debt it opens and a later unit closes respects the reading
        # order, and reading order is what the reader meets the promise in.
        where = paper("load-bearing-methods")
        spine = where / "spine.md"
        spine.write_text(
            spine.read_text()
            .replace("- closes: D1", "- closes: D1\n- closes: D2")
            .replace(
                "- restates: R2",
                "- restates: R2\n- opens: D2 (closed by R2) — whether one pixel is"
                " enough",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert verdict_for(result.report, "debt precedence") == PASS

    def test_a_restating_rung_ahead_of_what_it_restates_is_not_a_precedence_failure(
        self, render
    ):
        # The clean fixture's abstract restates R4 and sits first. `restates`
        # carries no precedence: an abstract restates what the paper has not
        # said yet, which is what an abstract is for.
        result = render("clean", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert verdict_for(result.report, "debt precedence") == PASS


class TestTheWalkReadsTheDeclaredRelation:
    """The walk reads the declared relation and never the section type, or it
    false-fails on the paper's load-bearing claim."""

    def test_a_load_bearing_claim_carried_by_methods_passes(self, render):
        result = render("load-bearing-methods", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert verdict_for(result.report, "chain bookkeeping") == PASS
        assert verdict_for(result.report, "debt precedence") == PASS

    def test_a_unit_bearing_children_closes_a_debt(self, render):
        # `results` closes D1 and carries two child slots. Debts are opened and
        # closed by units, so there is no debt edge inside a unit and nothing
        # for the walk to look at there.
        result = render("load-bearing-methods", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert verdict_for(result.report, "originating slot children") == PASS

    def test_a_rung_naming_a_child_slot_is_the_pairings_finding_not_the_walks(
        self, paper, run_in
    ):
        where = paper("load-bearing-methods")
        spine = where / "spine.md"
        spine.write_text(
            spine.read_text().replace("### R2 — results", "### R2 — results-accuracy")
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 2
        assert "R2 names `results-accuracy`, which is not a unit" in result.report
        assert verdict_for(result.report, "chain bookkeeping") == PASS
        assert verdict_for(result.report, "debt precedence") == PASS

    def test_the_two_rows_are_out_of_scope_at_section_granularity(self, render):
        result = render(
            "clean", "MANUSCRIPT.working.md", "--check", "--section", "methods"
        )

        assert verdict_for(result.report, "chain bookkeeping") == SKIPPED
        assert verdict_for(result.report, "debt precedence") == SKIPPED


class TestTheLocalityTest:
    """The locality test is mechanically decidable from the two files, which is
    what makes it a check rather than a habit. It reports; it never gates."""

    def test_the_row_carries_numbers_and_never_a_verdict(self, render):
        result = render("clean", "MANUSCRIPT.working.md", "--check")

        reported = verdict_for(result.report, "locality test")

        assert reported.startswith("4 units")
        assert PASS not in reported
        assert "FAIL" not in reported

    def test_it_names_the_edges_that_escalate(self, render):
        result = render("clean", "MANUSCRIPT.working.md", "--check")

        reported = verdict_for(result.report, "locality test")

        assert "`D1` introduction→results" in reported
        assert "abstract restates results" in reported

    def test_a_reported_row_never_changes_the_exit_code(self, render):
        result = render("clean", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert "0 fail" in result.report
        assert "1 reported" in result.report

    def test_it_is_out_of_scope_at_section_granularity(self, render):
        result = render(
            "clean", "MANUSCRIPT.working.md", "--check", "--section", "methods"
        )

        assert verdict_for(result.report, "locality test") == SKIPPED
