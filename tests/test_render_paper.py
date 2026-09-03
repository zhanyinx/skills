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
