"""`render-paper` — the CLI, the exit-code contract, the verdict table.

Every test invokes the CLI as a subprocess over a fixture paper and asserts on
what a caller can see: the exit code, the emitted document, the verdict report.
"""

PASS = "PASS"
SKIPPED = "SKIPPED — OUT OF SCOPE AT THIS GRANULARITY"

# The verdict column starts here: the report's two-space indent, the width the
# row names are padded to, and the single space after it.
VERDICT_COLUMN = 34


def rows_of(report):
    """The verdict table as `{row name: what that row printed}`."""
    return dict(
        (line[:VERDICT_COLUMN].strip(), line[VERDICT_COLUMN:].strip())
        for line in table_lines(report)
    )


def table_lines(report):
    """The report's rows: everything above the blank line before the tally."""
    lines = []
    for line in report.splitlines():
        if not line.strip():
            break
        lines.append(line)
    return lines


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
        assert rows_of(result.report)["slot integrity"].startswith("FAIL")
        assert "anchored twice" in result.report

    def test_an_anchor_naming_no_skeleton_slot_is_a_hard_error(self, render):
        result = render("orphan-slot", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 2
        assert rows_of(result.report)["slot integrity"].startswith("FAIL")
        assert "absent from the skeleton" in result.report

    def test_an_originating_slot_bearing_children_is_a_hard_error(self, render):
        result = render("originating-children", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 2
        assert rows_of(result.report)["originating slot children"].startswith("FAIL")
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

        rows = rows_of(result.report)

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
        assert rows_of(result.report)["unfilled skeleton slot"] == PASS


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

    def test_scaffold_is_one_of_the_named_modes(self, render):
        result = render("clean", "MANUSCRIPT.working.md", "--scaffold", "--check")

        assert result.exit_code == 2
        assert result.document == ""
        assert "not allowed with" in result.report

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

    def test_it_holds_no_paper_specific_text(self):
        """The renderer holds no paper's name, no section of one, and no phrase
        only one manuscript would contain — which is what lets the two residue
        lints be word lists rather than a per-paper configuration file.

        Read as a shipped artifact, the way the stdlib-only check above reads
        it. The words are drawn from the corpus this design was calibrated on
        and from the fixture papers: if any of them ever appears here, some
        paper's text has leaked into the generator.

        Note what is *not* on this list, and why. `karyotype`, `thymidine
        kinase` and `DAPI` all appear in the script — the first two naming the
        notation the bare-hole list is known to reject, the third as an example
        in the overlap instrument. Those are general facts about biomedical
        prose, which is exactly the kind a paper-agnostic renderer may know.
        What it may not know is *which* paper: its name, its metric, or a
        sentence out of it.
        """
        from conftest import SCRIPT

        text = SCRIPT.read_text()

        for leaked in (
            "MIRAGE",
            "Dice",
            "confocal",
            "paraformaldehyde",
            "spinning-disk",
        ):
            assert leaked not in text


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
        assert rows_of(result.report)["unit / rung pairing"].startswith("FAIL")
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
        assert rows_of(result.report)["unfilled skeleton slot"] == PASS

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
        assert rows_of(result.report)["unfilled skeleton slot"] == "FAIL — 1 (the document title)"

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


class TestTheReportedTier:
    """Numbers, never verdicts, and never the exit code.

    The em-dash count is measured against a threshold; the three Tier 4
    diagnostics carry no threshold at all, because a threshold on a rhetorical
    move is satisfied by sprinkling `however`.
    """

    def test_the_table_is_verbatim(self, render, golden):
        result = render("prose-diagnostics", "MANUSCRIPT.working.md", "--check")

        assert result.report == golden("prose-diagnostics-check.txt")

    def test_the_em_dash_row_carries_the_count_the_threshold_and_the_lines(
        self, render
    ):
        result = render("prose-diagnostics", "MANUSCRIPT.working.md", "--check")

        rows = rows_of(result.report)

        assert "em dashes (threshold 0)" in rows
        assert rows["em dashes (threshold 0)"] == "FAIL — 3 (lines 4, 18, 23)"

    def test_a_count_over_threshold_leaves_the_exit_code_alone(self, render):
        result = render("prose-diagnostics", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0

    def test_and_submit_still_emits_the_document(self, render):
        result = render("prose-diagnostics", "MANUSCRIPT.working.md", "--submit")

        assert result.exit_code == 0
        assert "refused" not in result.report
        assert "## Results and discussion" in result.document

    def test_the_count_is_scoped_to_prose(self, render):
        # The fixture carries seven em dashes and three of them are prose: the
        # others sit in a comment, a table row, a fence and a citation group,
        # so an unscoped count would fire on a quoted source title.
        result = render("prose-diagnostics", "MANUSCRIPT.working.md", "--check")

        assert rows_of(result.report)["em dashes (threshold 0)"].endswith(
            "3 (lines 4, 18, 23)"
        )

    def test_the_threshold_comes_from_the_caller(self, render):
        result = render(
            "prose-diagnostics",
            "MANUSCRIPT.working.md",
            "--check",
            "--em-dash-threshold",
            "3",
        )

        rows = rows_of(result.report)

        assert "em dashes (threshold 3)" in rows
        assert rows["em dashes (threshold 3)"] == "PASS — 3 (lines 4, 18, 23)"

    def test_a_passing_count_is_still_reported(self, render):
        # The gate always runs and always reports its count, so raising the bar
        # cannot make the number invisible.
        result = render(
            "prose-diagnostics",
            "MANUSCRIPT.working.md",
            "--check",
            "--em-dash-threshold",
            "99",
        )

        assert "3 (lines 4, 18, 23)" in result.report

    def test_the_skill_level_default_threshold_is_zero(self, render):
        result = render("clean", "MANUSCRIPT.working.md", "--check")

        assert "em dashes (threshold 0)" in rows_of(result.report)

    def test_an_em_dash_in_a_comment_is_not_prose(self, render):
        # The clean fixture's first line is a comment carrying an em dash.
        result = render("clean", "MANUSCRIPT.working.md", "--check")

        assert rows_of(result.report)["em dashes (threshold 0)"] == "PASS — 0"

    def test_a_negative_threshold_is_refused(self, render):
        result = render(
            "clean", "MANUSCRIPT.working.md", "--check", "--em-dash-threshold", "-1"
        )

        assert result.exit_code == 2
        assert "finite non-negative integer" in result.report

    def test_there_is_no_off_no_none_and_no_infinity(self, render):
        for value in ("off", "none", "inf", "∞", "1.5"):
            result = render(
                "clean",
                "MANUSCRIPT.working.md",
                "--check",
                "--em-dash-threshold",
                value,
            )

            assert result.exit_code == 2
            assert "finite non-negative integer" in result.report

    def test_the_em_dash_count_runs_at_section_granularity(self, render):
        # It blocks the seam in `write-paper`, so it cannot be whole-document
        # only — the seam is a section.
        result = render(
            "prose-diagnostics",
            "MANUSCRIPT.working.md",
            "--check",
            "--section",
            "results",
        )

        assert rows_of(result.report)["em dashes (threshold 0)"] == (
            "FAIL — 2 (lines 18, 23)"
        )

    def test_the_tier_four_diagnostics_carry_numbers_and_no_verdict(self, render):
        result = render("prose-diagnostics", "MANUSCRIPT.working.md", "--check")

        rows = rows_of(result.report)

        for name in ("adversative ratio", "subject openings", "sentence length"):
            assert name in rows
            assert PASS not in rows[name]
            assert "FAIL" not in rows[name]
            assert SKIPPED not in rows[name]

    def test_the_adversative_ratio_is_a_ratio_over_sentences(self, render):
        result = render("prose-diagnostics", "MANUSCRIPT.working.md", "--check")

        assert rows_of(result.report)["adversative ratio"] == (
            "2 of 9 sentences (22%)"
        )

    def test_the_subject_openings_are_a_distribution(self, render):
        result = render("prose-diagnostics", "MANUSCRIPT.working.md", "--check")

        openings = rows_of(result.report)["subject openings"]

        assert openings.startswith("The 4")
        assert "of 9 sentences" in openings

    def test_the_sentence_length_row_carries_mean_cv_and_share_over_35(self, render):
        result = render("prose-diagnostics", "MANUSCRIPT.working.md", "--check")

        length = rows_of(result.report)["sentence length"]

        assert "mean " in length
        assert "CV " in length
        assert "over 35 words" in length

    def test_the_tier_four_rows_are_out_of_scope_at_section_granularity(self, render):
        # Whole-piece only: a number reported per seam is a number a drafter
        # tunes at the seam, which is what `no threshold` exists to prevent.
        result = render(
            "prose-diagnostics",
            "MANUSCRIPT.working.md",
            "--check",
            "--section",
            "results",
        )

        rows = rows_of(result.report)

        for name in ("adversative ratio", "subject openings", "sentence length"):
            assert rows[name] == SKIPPED

    def test_single_sentence_body_paragraphs_are_reported(self, render):
        result = render("prose-diagnostics", "MANUSCRIPT.working.md", "--check")

        assert rows_of(result.report)["single-sentence body paragraphs"] == (
            "2 in 1 originating unit (lines 8, 10)"
        )

    def test_they_are_suspended_for_a_non_originating_unit(self, render):
        # A unit that only closes or restates is not a unit of argument, so
        # §4a's single-sentence signature does not transfer to it.
        result = render(
            "prose-diagnostics",
            "MANUSCRIPT.working.md",
            "--check",
            "--section",
            "results",
        )

        assert rows_of(result.report)["single-sentence body paragraphs"] == (
            "0 in 0 originating units"
        )

    def test_no_reported_row_changes_the_exit_code(self, paper, run_in):
        # Every reported row failing at once, over a paper whose gating and
        # hard rows all pass.
        where = paper("prose-diagnostics")
        source = where / "MANUSCRIPT.working.md"
        source.write_text(
            source.read_text().replace(
                "Registration drift is unaddressed.",
                "Registration drift — unaddressed — is the gap.",
            )
        )

        for mode in ("--check", "--circulate", "--submit"):
            result = run_in(where, "MANUSCRIPT.working.md", mode)

            assert result.exit_code == 0
            assert "FAIL" in result.report

    def test_locations_are_file_qualified_over_a_directory_of_sources(
        self, paper, run_in
    ):
        # Pre-promotion the sections are still separate files, where a bare
        # `line 4` could mean any of them.
        where = paper("pre-promotion")
        for name in ("abstract.md", "results.md"):
            source = where / "drafts" / name
            source.write_text(source.read_text().replace(", and", " — and"))

        result = run_in(where, "drafts", "--check")

        assert rows_of(result.report)["em dashes (threshold 0)"] == (
            "FAIL — 2 (abstract.md:4, results.md:4)"
        )

    def test_an_abbreviation_does_not_end_a_sentence(self, paper, run_in):
        # `Fig. 2` is mid-sentence; `no.` is a word a sentence can end on, and
        # merging two sentences would corrupt every number measured over them.
        where = paper("clean")
        source = where / "MANUSCRIPT.working.md"
        source.write_text(
            source.read_text().replace(
                "We register cyclic imaging panels across rounds and report the accuracy "
                "of that registration.",
                "Drift is visible in Fig. 2 of the earlier report. Whether it was ever "
                "corrected: no. We report the accuracy of the registration.",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert "(8 sentences)" in rows_of(result.report)["sentence length"]

    def test_a_bracket_span_with_no_citation_key_is_prose(self, paper, run_in):
        # Blanking a bracket span that is not a citation group would shorten
        # the sentence every number is measured over, and hide an em dash
        # sitting in prose the author wrote.
        where = paper("prose-diagnostics")
        source = where / "MANUSCRIPT.working.md"
        source.write_text(
            source.read_text().replace(
                "Registration drift is unaddressed.",
                "Registration drift [the earlier review — unaddressed] is the gap.",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert rows_of(result.report)["em dashes (threshold 0)"] == (
            "FAIL — 4 (lines 4, 8, 18, 23)"
        )

    def test_every_row_prints_its_verdict_in_the_same_column(self, render):
        # The table is an interface `review-paper` reports verbatim, and the
        # column is what a longer row name breaks silently.
        result = render("prose-diagnostics", "MANUSCRIPT.working.md", "--check")

        for line in table_lines(result.report):
            assert line[VERDICT_COLUMN - 1] == " "
            assert line[VERDICT_COLUMN] != " "


class TestScaffold:
    """`--scaffold` pre-seeds a unit's source with every anchor in its subtree,
    in skeleton order, so a misordered, duplicated or omitted anchor is
    something a drafting session cannot type rather than something a rule
    forbids."""

    def test_it_seeds_every_anchor_in_the_subtree_in_skeleton_order(
        self, paper, run_in, golden
    ):
        where = paper("clean")

        result = run_in(where, "methods.md", "--scaffold", "--section", "methods")

        assert result.exit_code == 0
        assert (where / "methods.md").read_text() == golden("scaffold-methods.md")

    def test_it_writes_no_heading_into_the_source(self, paper, run_in):
        # Heading injection is the render's job on every pass, so the skeleton's
        # heading text has no business in a source at all.
        where = paper("clean")

        run_in(where, "methods.md", "--scaffold", "--section", "methods")
        seeded = (where / "methods.md").read_text()

        assert "#" not in seeded
        assert "Imaging" not in seeded
        assert "Registration" not in seeded

    def test_running_it_twice_changes_nothing(self, paper, run_in):
        where = paper("clean")

        run_in(where, "methods.md", "--scaffold", "--section", "methods")
        first = (where / "methods.md").read_text()
        second = run_in(where, "methods.md", "--scaffold", "--section", "methods")

        assert second.exit_code == 0
        assert (where / "methods.md").read_text() == first
        assert "unchanged" in second.report

    def test_it_is_idempotent_over_a_source_that_already_carries_prose(
        self, paper, run_in
    ):
        where = paper("clean")
        source = where / "MANUSCRIPT.working.md"

        first_run = run_in(where, "MANUSCRIPT.working.md", "--scaffold", "--section", "methods")
        first = source.read_text()
        run_in(where, "MANUSCRIPT.working.md", "--scaffold", "--section", "methods")

        assert first_run.exit_code == 0
        assert source.read_text() == first

    def test_a_parent_s_own_prose_stays_before_its_first_child_anchor(
        self, paper, run_in
    ):
        # A parent slot may bear prose, and its own prose is exactly the text
        # preceding its first child anchor.
        where = paper("clean")
        source = where / "methods.md"
        source.write_text(
            "<!-- slot: methods -->\n\n"
            "The pipeline runs as five stages.\n"
        )

        result = run_in(where, "methods.md", "--scaffold", "--section", "methods")

        assert result.exit_code == 0
        assert source.read_text() == (
            "<!-- slot: methods -->\n\n"
            "The pipeline runs as five stages.\n\n"
            "<!-- slot: methods-imaging -->\n\n"
            "<!-- slot: methods-registration -->\n"
        )

    def test_a_skeleton_amendment_adds_its_anchor_and_moves_no_prose(
        self, paper, run_in
    ):
        where = paper("clean")
        source = where / "MANUSCRIPT.working.md"
        skeleton = where / "skeleton.md"
        run_in(where, "MANUSCRIPT.working.md", "--scaffold", "--section", "methods")
        skeleton.write_text(
            skeleton.read_text().replace(
                "| methods-registration | 3 | Registration | procedure |",
                "| methods-registration | 3 | Registration | procedure |\n"
                "| methods-drift | 3 | Drift | procedure |",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--scaffold", "--section", "methods")
        seeded = source.read_text()

        assert result.exit_code == 0
        assert "<!-- slot: methods-drift -->" in seeded
        assert seeded.index("<!-- slot: methods-drift -->") > seeded.index(
            "Registration proceeds pairwise"
        )
        assert seeded.index("<!-- slot: methods-drift -->") < seeded.index(
            "<!-- slot: results -->"
        )
        assert "Accuracy is sufficient for per-arm comparison" in seeded

    def test_it_preserves_the_author_facing_comment_channel(self, paper, run_in):
        where = paper("clean")

        result = run_in(where, "MANUSCRIPT.working.md", "--scaffold", "--section", "methods")
        seeded = (where / "MANUSCRIPT.working.md").read_text()

        assert result.exit_code == 0
        assert "R1 — abstract" in seeded
        assert "confirm the tool list" in seeded
        assert "superseded outline" in seeded

    def test_it_leaves_every_slot_outside_the_unit_alone(self, paper, run_in):
        where = paper("clean")
        source = where / "MANUSCRIPT.working.md"
        source.write_text(
            source.read_text().replace(
                "<!-- slot: methods-registration -->\n\n"
                "Registration proceeds pairwise against the DAPI channel, "
                "which every round shares.\n",
                "",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--scaffold", "--section", "methods")
        seeded = source.read_text()

        assert result.exit_code == 0
        assert "<!-- slot: methods-registration -->" in seeded
        assert "We register cyclic imaging panels" in seeded
        assert "Cyclic imaging acquires one panel per round" in seeded
        assert "Accuracy is sufficient for per-arm comparison" in seeded

    def test_it_orders_the_anchors_by_the_skeleton_and_not_by_the_source(
        self, paper, run_in
    ):
        # The unit is derived from the anchors already there, so a source that
        # names its own unit needs no `--section`.
        where = paper("clean")
        source = where / "methods.md"
        source.write_text(
            "<!-- slot: methods-registration -->\n\nRegistration proceeds pairwise.\n\n"
            "<!-- slot: methods-imaging -->\n\nPanels were acquired per round.\n"
        )

        result = run_in(where, "methods.md", "--scaffold")
        seeded = source.read_text()

        assert result.exit_code == 0
        assert (
            seeded.index("<!-- slot: methods -->")
            < seeded.index("<!-- slot: methods-imaging -->")
            < seeded.index("<!-- slot: methods-registration -->")
        )
        assert seeded.index("Panels were acquired") < seeded.index(
            "Registration proceeds"
        )

    def test_it_seeds_only_the_unit_its_source_names(self, paper, run_in):
        # Pre-promotion every unit has its own file, so seeding a slot whose
        # prose lives in a sibling file is how a source acquires the anchor the
        # next render calls a duplicate.
        where = paper("pre-promotion")
        source = where / "drafts" / "results.md"

        result = run_in(where, "drafts/results.md", "--scaffold")
        seeded = source.read_text()

        assert result.exit_code == 0
        assert "<!-- slot: results -->" in seeded
        assert "abstract" not in seeded

    def test_what_the_scaffold_writes_is_what_the_render_reads(
        self, paper, run_in, golden
    ):
        # The anchor the scaffold writes and the anchor the render parses are
        # one grammar; a seeded paper renders to the same document as the
        # hand-written one it was seeded from.
        where = paper("pre-promotion")

        run_in(where, "drafts/abstract.md", "--scaffold")
        run_in(where, "drafts/results.md", "--scaffold")
        result = run_in(where, "drafts", "--circulate")

        assert result.exit_code == 0
        assert result.document == golden("pre-promotion-circulate.md")

    def test_a_seeded_unit_renders_as_holes_rather_than_as_damage(
        self, paper, run_in
    ):
        where = paper("clean")

        run_in(where, "methods.md", "--scaffold", "--section", "methods")
        result = run_in(where, "methods.md", "--circulate", "--section")

        assert result.exit_code == 1
        assert "## Methods" in result.document
        assert "⟦HOLE: prose for methods-imaging⟧" in result.document

    def test_it_needs_no_spine(self, paper, run_in):
        # Scaffolding seeds anchors from the skeleton alone; the ladder is the
        # gate's input, and a check with no use here would be a check that
        # refuses a legal state.
        where = paper("clean")
        (where / "spine.md").unlink()

        result = run_in(where, "methods.md", "--scaffold", "--section", "methods")

        assert result.exit_code == 0
        assert (where / "methods.md").exists()

    def test_it_emits_no_document(self, paper, run_in):
        where = paper("clean")

        result = run_in(where, "methods.md", "--scaffold", "--section", "methods")

        assert result.document == ""

    def test_a_fenced_anchor_is_not_an_anchor_here_either(self, paper, run_in):
        # A source showing anchor syntax in a fence is showing it, not using
        # it — so the scaffold must neither split there nor seed the slot.
        where = paper("fenced")
        source = where / "MANUSCRIPT.working.md"

        result = run_in(where, "MANUSCRIPT.working.md", "--scaffold", "--section", "results")
        seeded = source.read_text()

        assert result.exit_code == 0
        assert seeded.count("<!-- slot: not-an-anchor -->") == 1
        assert "<!-- an unclosed comment, shown as text" in seeded
        assert seeded.index("<!-- slot: not-an-anchor -->") > seeded.index(
            "<!-- slot: results -->"
        )


class TestScaffoldRefusals:
    """Scaffold rewrites the source, so wherever it would have to guess it
    refuses instead, and writes nothing at all."""

    def test_a_slot_anchored_twice_is_refused_and_nothing_is_written(
        self, paper, run_in
    ):
        where = paper("duplicate-slot")
        source = where / "MANUSCRIPT.working.md"
        before = source.read_text()

        result = run_in(where, "MANUSCRIPT.working.md", "--scaffold")

        assert result.exit_code == 2
        assert "anchored twice" in result.report
        assert source.read_text() == before

    def test_an_anchor_naming_no_skeleton_slot_is_refused(self, paper, run_in):
        where = paper("orphan-slot")
        source = where / "MANUSCRIPT.working.md"
        before = source.read_text()

        result = run_in(where, "MANUSCRIPT.working.md", "--scaffold")

        assert result.exit_code == 2
        assert "absent from the skeleton" in result.report
        assert source.read_text() == before

    def test_prose_outside_every_slot_is_refused(self, paper, run_in):
        where = paper("stray-prose")
        source = where / "drafts" / "results.md"
        before = source.read_text()

        result = run_in(where, "drafts/results.md", "--scaffold")

        assert result.exit_code == 2
        assert "prose outside every slot in results.md" in result.report
        assert source.read_text() == before

    def test_a_malformed_anchor_is_a_parse_error_and_nothing_is_written(
        self, paper, run_in
    ):
        where = paper("malformed-anchor")
        source = where / "MANUSCRIPT.working.md"
        before = source.read_text()

        result = run_in(where, "MANUSCRIPT.working.md", "--scaffold")

        assert result.exit_code == 3
        assert "malformed anchor" in result.report
        assert source.read_text() == before

    def test_a_heading_in_the_source_is_a_parse_error(self, paper, run_in):
        where = paper("heading-in-source")
        source = where / "MANUSCRIPT.working.md"
        before = source.read_text()

        result = run_in(where, "MANUSCRIPT.working.md", "--scaffold")

        assert result.exit_code == 3
        assert "is a heading" in result.report
        assert source.read_text() == before

    def test_a_directory_is_not_a_unit_s_source(self, paper, run_in):
        where = paper("pre-promotion")

        result = run_in(where, "drafts", "--scaffold")

        assert result.exit_code == 2
        assert "one source file" in result.report

    def test_a_source_it_cannot_read_stays_inside_the_exit_code_contract(
        self, paper, run_in
    ):
        # `2` is "the renderer cannot run at all", and an unreadable source is
        # exactly that — never a traceback, which no caller can read.
        import os

        import pytest

        if os.geteuid() == 0:
            # Root reads it anyway, so the refusal cannot be provoked — and a
            # check that never looked is never silently a pass.
            pytest.skip("running as root")
        where = paper("clean")
        source = where / "MANUSCRIPT.working.md"
        source.chmod(0o000)

        result = run_in(where, "MANUSCRIPT.working.md", "--scaffold", "--section", "methods")
        source.chmod(0o644)

        assert result.exit_code == 2
        assert "cannot be read" in result.report

    def test_a_source_it_cannot_write_stays_inside_it_too(self, paper, run_in):
        where = paper("clean")

        result = run_in(
            where, "MANUSCRIPT.working.md/nope.md", "--scaffold", "--section", "methods"
        )

        assert result.exit_code == 2
        assert "cannot be written" in result.report

    def test_a_fresh_source_with_no_named_unit_asks_for_one(self, paper, run_in):
        where = paper("clean")

        result = run_in(where, "methods.md", "--scaffold", "--section")

        assert result.exit_code == 2
        assert "--section <unit>" in result.report
        assert not (where / "methods.md").exists()


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
        assert rows_of(result.report)["chain bookkeeping"].startswith("FAIL")
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
        assert rows_of(result.report)["chain bookkeeping"] == PASS

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
        assert rows_of(result.report)["debt precedence"] == PASS

    def test_a_restating_rung_ahead_of_what_it_restates_is_not_a_precedence_failure(
        self, render
    ):
        # The clean fixture's abstract restates R4 and sits first. `restates`
        # carries no precedence: an abstract restates what the paper has not
        # said yet, which is what an abstract is for.
        result = render("clean", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert rows_of(result.report)["debt precedence"] == PASS


class TestTheWalkReadsTheDeclaredRelation:
    """The walk reads the declared relation and never the section type, or it
    false-fails on the paper's load-bearing claim."""

    def test_a_load_bearing_claim_carried_by_methods_passes(self, render):
        result = render("load-bearing-methods", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert rows_of(result.report)["chain bookkeeping"] == PASS
        assert rows_of(result.report)["debt precedence"] == PASS

    def test_a_unit_bearing_children_closes_a_debt(self, render):
        # `results` closes D1 and carries two child slots. Debts are opened and
        # closed by units, so there is no debt edge inside a unit and nothing
        # for the walk to look at there.
        result = render("load-bearing-methods", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert rows_of(result.report)["originating slot children"] == PASS

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
        assert rows_of(result.report)["chain bookkeeping"] == PASS
        assert rows_of(result.report)["debt precedence"] == PASS

    def test_the_two_rows_are_out_of_scope_at_section_granularity(self, render):
        result = render(
            "clean", "MANUSCRIPT.working.md", "--check", "--section", "methods"
        )

        assert rows_of(result.report)["chain bookkeeping"] == SKIPPED
        assert rows_of(result.report)["debt precedence"] == SKIPPED


class TestTheLocalityTest:
    """The locality test is mechanically decidable from the two files, which is
    what makes it a check rather than a habit. It reports; it never gates."""

    def test_the_row_carries_numbers_and_never_a_verdict(self, render):
        result = render("clean", "MANUSCRIPT.working.md", "--check")

        reported = rows_of(result.report)["locality test"]

        assert reported.startswith("4 units")
        assert PASS not in reported
        assert "FAIL" not in reported

    def test_it_names_the_edges_that_escalate(self, render):
        result = render("clean", "MANUSCRIPT.working.md", "--check")

        reported = rows_of(result.report)["locality test"]

        assert "`D1` introduction→results" in reported
        assert "abstract restates results" in reported

    def test_a_reported_row_never_changes_the_exit_code(self, render):
        result = render("clean", "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert "0 fail" in result.report
        assert rows_of(result.report)["locality test"].startswith("4 units")

    def test_it_is_out_of_scope_at_section_granularity(self, render):
        result = render(
            "clean", "MANUSCRIPT.working.md", "--check", "--section", "methods"
        )

        assert rows_of(result.report)["locality test"] == SKIPPED

class TestTheOverlapInstrument:
    """The instrument that catches prose mirroring its own brief. The zone the
    shared span came from decides which instrument applies to it."""

    OVERLAP = "brief-to-prose overlap"

    def test_the_table_is_verbatim(self, render, golden):
        result = render("brief-mirror", "MANUSCRIPT.working.md", "--check")

        assert result.report == golden("brief-mirror-check.txt")

    def test_a_phrase_shared_with_the_argument_zone_is_flagged(self, render):
        result = render("brief-mirror", "MANUSCRIPT.working.md", "--check")

        assert 'results: "Registration accuracy is credible on a metric' in (
            rows_of(result.report)[self.OVERLAP]
        )

    def test_the_row_carries_numbers_and_no_verdict(self, render):
        result = render("brief-mirror", "MANUSCRIPT.working.md", "--check")
        row = rows_of(result.report)[self.OVERLAP]

        assert row.startswith("4 flagged, 1 expected")
        assert PASS not in row
        assert "FAIL" not in row
        assert "threshold" not in row

    def test_it_changes_no_exit_code_and_gates_no_submission(self, render):
        # Every paragraph of the fixture's originating unit is transcribed from
        # its brief. Nothing about that is a gate.
        for mode in ("--check", "--submit"):
            result = render("brief-mirror", "MANUSCRIPT.working.md", mode)

            assert result.exit_code == 0

    def test_the_brief_is_a_declared_input_at_the_paper_root(self, paper, run_in):
        where = paper("brief-mirror")
        (where / "briefs" / "results.md").unlink()

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert "no brief for `results`" in rows_of(result.report)[self.OVERLAP]

    def test_an_absent_brief_is_said_rather_than_counted_as_nothing(self, render):
        result = render("unfilled-slot", "MANUSCRIPT.working.md", "--check")

        assert rows_of(result.report)[self.OVERLAP] == (
            "0 flagged, 0 expected — no brief for `abstract`, `results`"
        )

    def test_a_zone_this_parser_does_not_know_is_reported_not_raised(
        self, paper, run_in
    ):
        where = paper("brief-mirror")
        brief = where / "briefs" / "results.md"
        brief.write_text(brief.read_text().replace("## Argument", "## Propositions"))

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert "unparsed zone `## Propositions`" in rows_of(result.report)[self.OVERLAP]

    def test_a_brief_with_no_reader_facing_zone_is_reported_too(self, paper, run_in):
        where = paper("brief-mirror")
        brief = where / "briefs" / "availability.md"
        brief.write_text(brief.read_text().replace("## Inventory", "## Sheds"))

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert "no `## Argument` or `## Inventory` zone" in (
            rows_of(result.report)[self.OVERLAP]
        )

    def test_a_brief_that_cannot_be_read_at_all_is_reported_not_raised(
        self, paper, run_in
    ):
        where = paper("brief-mirror")
        (where / "briefs" / "results.md").write_bytes(
            b"# Brief\n\n## Argument\n\xff\xfe\n"
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert "Traceback" not in result.report
        assert "results.md: cannot be read" in rows_of(result.report)[self.OVERLAP]

    def test_only_a_reader_facing_zone_is_measured(self, paper, run_in):
        # `## Must not claim` is an instruction, and an instruction reaching
        # the prose verbatim is a different defect with a different owner.
        where = paper("brief-mirror")
        source = where / "MANUSCRIPT.working.md"
        source.write_text(
            source.read_text().replace(
                "The figure\nreports that metric for every arm.",
                "Any head-to-head performance win over a named tool is out of scope.",
            )
        )

        result = run_in(where, "MANUSCRIPT.working.md", "--check")

        assert result.exit_code == 0
        assert "head-to-head performance win" not in result.report

    def test_the_span_is_quoted_as_the_prose_wrote_it(self, paper, run_in):
        # What the author has to go and find is the phrase, so the row prints
        # the prose's own case and punctuation, not the normalised words.
        where = paper("brief-mirror")
        brief = where / "briefs" / "availability.md"
        brief.write_text(
            brief.read_text().replace(
                "release notes: the container digest, the tag, and the build date.",
                "every stage runs under Nextflow >= 25.04.0.",
            )
        )
        source = where / "MANUSCRIPT.working.md"
        source.write_text(
            source.read_text().replace(
                "The release notes carry the container digest, the tag, and the build date.",
                "Every stage runs under Nextflow >= 25.04.0.",
            )
        )

        result = run_in(
            where, "MANUSCRIPT.working.md", "--check", "--section", "availability"
        )

        assert 'availability: "Every stage runs under Nextflow >= 25.04.0"' in (
            rows_of(result.report)[self.OVERLAP]
        )

    def test_the_row_is_per_unit_and_so_never_out_of_scope(self, render):
        for granularity in ([], ["--section", "results"]):
            result = render(
                "brief-mirror", "MANUSCRIPT.working.md", "--check", *granularity
            )

            assert rows_of(result.report)[self.OVERLAP] != SKIPPED


class TestTheFiniteVerbTest:
    """An inventory item is a fact the prose must convey, so a shared span is
    expected — unless it predicates, which is the drafter transcribing or the
    brief author slipping into phrasing."""

    OVERLAP = "brief-to-prose overlap"

    def test_a_shared_inventory_span_with_a_finite_verb_is_flagged(self, render):
        result = render("brief-mirror", "MANUSCRIPT.working.md", "--check")

        assert 'availability: "The container image is freely available' in (
            rows_of(result.report)[self.OVERLAP]
        )

    def test_a_shared_inventory_span_with_no_finite_verb_is_expected(self, render):
        result = render(
            "brief-mirror", "MANUSCRIPT.working.md", "--check", "--section", "availability"
        )
        row = rows_of(result.report)[self.OVERLAP]

        assert row.startswith("1 flagged, 1 expected")
        assert "container digest" not in row

    def test_a_third_person_present_verb_is_a_finite_verb(self, paper, run_in):
        # The corpus's own flagged inventory span: `suppresses` is the whole
        # difference between an item and a sentence about one.
        where = paper("brief-mirror")
        brief = where / "briefs" / "availability.md"
        brief.write_text(
            brief.read_text().replace(
                "release notes: the container digest, the tag, and the build date.",
                "illumination correction suppresses tile-boundary seams in every arm.",
            )
        )
        source = where / "MANUSCRIPT.working.md"
        source.write_text(
            source.read_text().replace(
                "The release notes carry the container digest, the tag, and the build date.",
                "Illumination correction suppresses tile-boundary seams in every arm.",
            )
        )

        result = run_in(
            where, "MANUSCRIPT.working.md", "--check", "--section", "availability"
        )

        assert rows_of(result.report)[self.OVERLAP].startswith("2 flagged, 0 expected")

    def test_a_plural_noun_closing_an_item_is_not_a_finite_verb(self, paper, run_in):
        # The failure to avoid: an instrument that reads every plural as a verb
        # fires forever on a legend, and an instrument that fires forever is one
        # nobody reads. The punctuation an item ends its noun on is the guard.
        where = paper("brief-mirror")
        brief = where / "briefs" / "availability.md"
        brief.write_text(
            brief.read_text().replace(
                "release notes: the container digest, the tag, and the build date.",
                "five DSL2 stages, DAPI as the common anchor across rounds.",
            )
        )
        source = where / "MANUSCRIPT.working.md"
        source.write_text(
            source.read_text().replace(
                "The release notes carry the container digest, the tag, and the build date.",
                "The pipeline runs five DSL2 stages, DAPI as the common anchor across rounds.",
            )
        )

        result = run_in(
            where, "MANUSCRIPT.working.md", "--check", "--section", "availability"
        )

        assert rows_of(result.report)[self.OVERLAP].startswith("1 flagged, 1 expected")


class TestParagraphOrder:
    """Paragraph order joins the single-sentence row, and is suspended with it
    for a non-originating unit: order tracking the brief is what a venue's
    field order and a figure's lettering mandate there."""

    PARAGRAPHS = "single-sentence body paragraphs"

    def test_order_is_reported_for_an_originating_unit(self, render):
        result = render(
            "brief-mirror", "MANUSCRIPT.working.md", "--check", "--section", "results"
        )

        assert "brief-order 3 of 3 (results)" in rows_of(result.report)[self.PARAGRAPHS]

    def test_a_non_originating_unit_is_measured_by_neither(self, render, golden):
        result = render(
            "brief-mirror",
            "MANUSCRIPT.working.md",
            "--check",
            "--section",
            "availability",
        )

        assert result.report == golden("brief-mirror-section-check.txt")
        assert rows_of(result.report)[self.PARAGRAPHS] == "0 in 0 originating units"

    def test_order_is_reported_against_the_unit_s_own_paragraph_count(
        self, paper, run_in
    ):
        # A draft that walks three items and then writes two more paragraphs is
        # not mirroring, and a denominator stopping at the items would never
        # look at the two.
        where = paper("brief-mirror")
        source = where / "MANUSCRIPT.working.md"
        source.write_text(
            source.read_text().replace(
                "<!-- slot: availability -->",
                "Nothing in the crop settles how far the six cases reach.\n\n"
                "That question is what the next rung inherits.\n\n"
                "<!-- slot: availability -->",
            )
        )

        result = run_in(
            where, "MANUSCRIPT.working.md", "--check", "--section", "results"
        )

        assert "brief-order 3 of 5 (results)" in rows_of(result.report)[self.PARAGRAPHS]

    def test_an_originating_unit_carrying_an_inventory_zone_is_still_ordered(
        self, paper, run_in
    ):
        # A unit that is both originating and inventory-carrying is expressible,
        # and its order is measured against whatever its reader-facing zone
        # states.
        where = paper("brief-mirror")
        brief = where / "briefs" / "results.md"
        brief.write_text(brief.read_text().replace("## Argument", "## Inventory"))

        result = run_in(
            where, "MANUSCRIPT.working.md", "--check", "--section", "results"
        )

        assert "brief-order 3 of 3 (results)" in rows_of(result.report)[self.PARAGRAPHS]

    def test_the_ladder_line_is_not_a_proposition(self, paper, run_in):
        # `Opens:` in the argument zone is bookkeeping, so moving it to the top
        # of the zone must not shift every proposition's position by one.
        where = paper("brief-mirror")
        brief = where / "briefs" / "results.md"
        brief.write_text(
            brief.read_text()
            .replace(
                "## Argument\nRegistration",
                "## Argument\nOpens: reproducibility of the pipeline -> R2.\nRegistration",
            )
            .replace("seams.\nOpens: reproducibility of the pipeline -> R2.\n", "seams.\n")
        )

        result = run_in(
            where, "MANUSCRIPT.working.md", "--check", "--section", "results"
        )

        assert "brief-order 3 of 3 (results)" in rows_of(result.report)[self.PARAGRAPHS]

    def test_an_absent_brief_is_not_reported_twice(self, paper, run_in):
        # The overlap row above already names every unit with no brief, and two
        # rows carrying one fact is how the two of them drift.
        where = paper("brief-mirror")
        (where / "briefs" / "results.md").unlink()

        result = run_in(
            where, "MANUSCRIPT.working.md", "--check", "--section", "results"
        )
        rows = rows_of(result.report)

        assert "no brief for `results`" in rows["brief-to-prose overlap"]
        assert "brief-order" not in rows[self.PARAGRAPHS]

    def test_a_brief_stating_no_item_is_said_because_nothing_else_says_it(
        self, paper, run_in
    ):
        where = paper("brief-mirror")
        brief = where / "briefs" / "results.md"
        brief.write_text("# Brief — Results\n\n## Argument\n\n## Sources\nCONTEXT.md\n")

        result = run_in(
            where, "MANUSCRIPT.working.md", "--check", "--section", "results"
        )

        assert "brief-order not measured (results: the brief states no reader-facing" in (
            rows_of(result.report)[self.PARAGRAPHS]
        )
