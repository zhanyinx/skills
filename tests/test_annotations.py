"""The annotation channel — the two brace behaviours, the manifest, the gate bit.

Every test invokes the CLI as a subprocess over a fixture paper and asserts on
what a caller can see: the exit code, the emitted document, the verdict report.

The `annotations` fixture carries **every** annotation form at once — both
brace behaviours, both comment classes, a reasoning comment keyed by a second
spelling of its label, a brace wrapping six lines, and four comments that must
be tracked nowhere.
"""

SOURCE = "MANUSCRIPT.working.md"


def manifest_of(report):
    """The manifest block of one report, verbatim."""
    if "manifest —" not in report:
        return ""
    block = report.split("manifest —", 1)[1]
    return block.split("warnings —", 1)[0]


def warnings_of(report):
    """The warnings block of one report, verbatim."""
    if "warnings —" not in report:
        return ""
    return report.split("warnings —", 1)[1].split("--submit refused", 1)[0]


def owners_in(report):
    """The `@owner` group headings of a manifest, in the order they print."""
    return [
        line.strip()
        for line in manifest_of(report).splitlines()
        if line.startswith("  @")
    ]


class TestCirculateOverEveryFormAtOnce:
    """`--circulate` always succeeds over a live paper: a HOLE comes out as a
    conspicuous uniform token, a SLOT as a visible placeholder, a SILENT as
    nothing at all."""

    def test_circulate_emits_the_whole_document(self, render, golden):
        result = render("annotations", SOURCE, "--circulate")

        assert result.document == golden("annotations-circulate.md")

    def test_it_emits_while_three_gate_bits_are_open(self, render):
        result = render("annotations", SOURCE, "--circulate")

        assert result.exit_code == 1
        assert result.document != ""

    def test_every_hole_becomes_one_conspicuous_uniform_token(self, render):
        result = render("annotations", SOURCE, "--circulate")

        assert "⟦HOLE: the production registration arm⟧" in result.document
        assert "⟦HOLE: best-arm Dice⟧" in result.document
        assert "⟦HOLE: rigid-only Dice⟧" in result.document
        assert "⟦HOLE: the funder acknowledgement⟧" in result.document

    def test_the_hole_token_is_the_one_an_unfilled_slot_uses(self, render):
        # Uniform means one token class for every gap, so one grep finds them
        # all. A second spelling would need a second grep nobody runs.
        result = render("annotations", SOURCE, "--circulate")
        holes = [word for word in result.document.split() if word.startswith("⟦")]

        assert holes
        for hole in holes:
            assert hole.startswith("⟦HOLE:") or hole.startswith("⟦SLOT:")

    def test_a_slot_becomes_a_visible_placeholder(self, render):
        result = render("annotations", SOURCE, "--circulate")

        assert "⟦SLOT: data availability statement⟧" in result.document
        assert "⟦SLOT: ethics approval number⟧" in result.document

    def test_a_silent_annotation_emits_nothing(self, render):
        result = render("annotations", SOURCE, "--circulate")

        assert "waiting on the IRB number" not in result.document
        assert "the six paired fractions" not in result.document

    def test_no_brace_survives_as_a_brace(self, render):
        result = render("annotations", SOURCE, "--circulate")

        assert "{{" not in result.document
        assert "}}" not in result.document

    def test_submit_over_the_same_source_refuses_and_emits_nothing(self, render):
        result = render("annotations", SOURCE, "--submit")

        assert result.exit_code == 1
        assert result.document == ""


class TestNoCommentOfAnyShapeSurvives:
    """The strip is by syntax and by class, never by a marker string: the
    2,264-character leak in the corpus was a generator cutting at a literal
    marker. So a comment that *looks* like a marker and a comment that looks
    like nothing are both gone, for the same reason."""

    def test_a_comment_that_looks_like_a_marker_string_is_gone(self, render):
        result = render("annotations", SOURCE, "--circulate")

        assert "DRAFT NOTES" not in result.document

    def test_a_comment_that_looks_like_nothing_is_gone(self, render):
        result = render("annotations", SOURCE, "--circulate")

        assert "<!--" not in result.document
        assert "-->" not in result.document

    def test_the_reasoning_comment_is_gone_from_the_render(self, render):
        result = render("annotations", SOURCE, "--circulate")

        assert "VALIS accuracy preset" not in result.document

    def test_the_ordinary_comments_are_gone_too(self, render):
        result = render("annotations", SOURCE, "--circulate")

        assert "overstates how novel" not in result.document
        assert "R1 — abstract" not in result.document


class TestAGapIsNeverSilentlyStripped:
    """Strip the token and the sentence is ungrammatical; drop the clause and
    an unsupported assertion ships and the author never learns it vanished."""

    def test_the_sentence_resting_on_a_missing_number_keeps_both_the_claim_and_the_gap(
        self, render
    ):
        result = render("annotations", SOURCE, "--circulate")

        assert (
            "Registration raised Dice to ⟦HOLE: best-arm Dice⟧ from "
            "⟦HOLE: rigid-only Dice⟧, which is what the" in result.document
        )

    def test_and_the_author_learns_of_it_from_the_manifest(self, render):
        result = render("annotations", SOURCE, "--circulate")

        assert "best-arm Dice" in manifest_of(result.report)


class TestTheManifest:
    def test_it_prints_under_every_mode(self, render):
        for mode in ("--check", "--circulate", "--submit"):
            result = render("annotations", SOURCE, mode)

            assert "best-arm Dice" in manifest_of(result.report)

    def test_it_is_grouped_by_owner(self, render):
        result = render("annotations", SOURCE, "--check")

        assert owners_in(result.report) == ["@author", "@lab-imaging"]

    def test_an_owner_group_carries_exactly_what_that_owner_owes(self, render):
        # The payoff of grouping: an experimentalist can be sent their own
        # group and nothing else.
        result = render("annotations", SOURCE, "--check")
        group = manifest_of(result.report).split("@lab-imaging")[1]

        assert "the six paired fractions" in group
        assert "pooled over both arms" in group
        assert "best-arm Dice" not in group

    def test_an_unowned_annotation_defaults_to_the_author(self, render):
        result = render("annotations", SOURCE, "--check")
        group = manifest_of(result.report).split("@author")[1].split("@lab-imaging")[0]

        assert "the funder acknowledgement" in group

    def test_it_names_the_source_location_of_every_entry(self, render):
        result = render("annotations", SOURCE, "--check")

        for line in manifest_of(result.report).splitlines():
            if line.startswith("    ") and line.strip():
                assert SOURCE in line or line.strip().startswith(
                    ("reasoning:", "direction:")
                )

    def test_it_reports_both_behaviours_and_the_bit(self, render):
        result = render("annotations", SOURCE, "--check")
        manifest = manifest_of(result.report)

        assert "HOLE" in manifest
        assert "SLOT" in manifest
        assert "SILENT" in manifest
        assert "10 open annotations, 3 carrying the gate bit" in manifest

    def test_it_is_recomputed_from_the_source_so_it_cannot_go_stale(
        self, paper, run_in
    ):
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(source.read_text().replace("{{! best-arm Dice }}", "0.89"))

        result = run_in(where, SOURCE, "--check")

        assert "best-arm Dice" not in manifest_of(result.report)
        assert "9 open annotations, 2 carrying the gate bit" in result.report

    def test_a_paper_with_no_annotations_still_prints_a_manifest(self, render):
        # Absent would read as "nobody looked". The manifest is an input to a
        # judgement axis, so it says so when it is empty.
        result = render("pre-promotion", "drafts", "--check")

        assert "manifest — no open annotations" in result.report


class TestWhatEntersTheManifest:
    """A comment enters the manifest **iff** its first non-space character is
    `!` or `@`. That rule is what keeps the rung, the objection note and the
    section anchors out of a list of outstanding work sent to a co-author."""

    def test_a_rung_comment_is_tracked_nowhere(self, render):
        # Nobody owes a rung.
        result = render("annotations", SOURCE, "--check")

        assert "abstract: establishes" not in result.report

    def test_an_objection_note_is_tracked_nowhere(self, render):
        result = render("annotations", SOURCE, "--check")

        assert "overstates how novel" not in result.report

    def test_a_section_anchor_is_tracked_nowhere(self, render):
        result = render("annotations", SOURCE, "--check")

        for line in manifest_of(result.report).splitlines():
            assert "slot:" not in line

    def test_a_comment_that_opens_with_a_bang_enters_and_gates(self, render):
        result = render("annotations", SOURCE, "--check")
        entry = manifest_of(result.report).split("the six paired fractions")[0]

        assert entry.rstrip().endswith("unverified:")
        assert "!  SILENT" in entry

    def test_a_comment_that_opens_with_an_owner_enters_and_does_not_gate(
        self, render
    ):
        result = render("annotations", SOURCE, "--check")
        entry = manifest_of(result.report).split("waiting on the IRB number")[0]

        assert entry.rstrip().endswith("SILENT  MANUSCRIPT.working.md:11")
        assert not entry.rstrip().split("\n")[-1].strip().startswith("!")


class TestTheSubmitRefusal:
    def test_submit_refuses_while_any_gate_bit_is_open(self, render):
        result = render("annotations", SOURCE, "--submit")

        assert result.exit_code == 1
        assert "--submit refused" in result.report

    def test_and_prints_the_list_of_what_is_open(self, render):
        result = render("annotations", SOURCE, "--submit")
        refusal = result.report.split("--submit refused")[1]

        assert "the production registration arm" in refusal
        assert "best-arm Dice" in refusal
        assert "the six paired fractions" in refusal

    def test_a_hole_without_the_bit_does_not_block_submission(self, paper, run_in):
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(
            source.read_text()
            .replace("{{! the production registration arm }}", "{{ the production registration arm }}")
            .replace("{{! best-arm Dice }}", "{{ best-arm Dice }}")
            .replace(
                "<!-- !@lab-imaging unverified:", "<!-- @lab-imaging unverified:"
            )
        )

        result = run_in(where, SOURCE, "--submit")

        assert result.exit_code == 0
        assert result.document != ""
        assert "⟦HOLE: best-arm Dice⟧" in result.document

    def test_the_open_bits_are_a_printed_row_of_the_verdict_table(self, render):
        result = render("annotations", SOURCE, "--check")

        assert "annotations (gating)      FAIL — 3" in result.report


class TestSpanBasedParsing:
    """13 of the 30 real annotations wrapped across lines and one across six.
    A line-anchored parser is the thing an implementer assumes away."""

    def test_a_brace_wrapping_six_lines_parses_as_one_annotation(self, render):
        result = render("annotations", SOURCE, "--check")
        matched = [
            line
            for line in manifest_of(result.report).splitlines()
            if "pooled over both arms" in line
        ]

        assert len(matched) == 1

    def test_and_renders_as_one_token_on_one_line(self, render):
        result = render("annotations", SOURCE, "--circulate")

        assert (
            "⟦HOLE: the mean and standard deviation of the per-round Dice "
            "coefficient across every marker pair in the paired-fraction "
            "subset, pooled over both arms⟧" in result.document
        )

    def test_a_comment_wrapping_three_lines_joins_as_one_reasoning_comment(
        self, render
    ):
        result = render("annotations", SOURCE, "--check")

        assert "Reconcile before filling this in." in manifest_of(result.report)


class TestLabelNormalisation:
    """The label is the join key between a brace and its reasoning comment, and
    the grammar fixes token order but not whitespace. Two spellings of one
    label orphaned the comment silently in the corpus."""

    def test_a_second_spelling_of_one_label_still_joins_its_reasoning(self, render):
        # The brace reads `{{! the production registration arm }}`; the comment
        # keys it as `{{ !  the   production  registration arm }}`.
        result = render("annotations", SOURCE, "--check")
        entry = manifest_of(result.report).split("the production registration arm")[1]

        assert "reasoning: VALIS accuracy preset" in entry

    def test_the_reasoning_is_attached_to_its_own_brace_and_not_listed_alone(
        self, render
    ):
        result = render("annotations", SOURCE, "--check")

        assert "10 open annotations" in result.report

    def test_a_reasoning_comment_keyed_to_no_brace_warns_rather_than_vanishing(
        self, paper, run_in
    ):
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(
            source.read_text().replace(
                "<!-- {{ !  the   production  registration arm }}:",
                "<!-- {{ the producton registration arm }}:",
            )
        )

        result = run_in(where, SOURCE, "--check")

        assert "the producton registration arm" in warnings_of(result.report)
        assert "keys no brace" in warnings_of(result.report)

    def test_a_second_comment_keyed_to_one_brace_warns_rather_than_vanishing(
        self, paper, run_in
    ):
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(
            source.read_text().replace(
                "<!-- !@lab-imaging unverified:",
                "<!-- {{the production registration arm}}: and reconcile the preset -->\n"
                "<!-- !@lab-imaging unverified:",
            )
        )

        result = run_in(where, SOURCE, "--check")

        assert "is keyed again here" in warnings_of(result.report)
        assert "reasoning: VALIS accuracy preset" in manifest_of(result.report)

    def test_the_normalised_label_is_what_the_token_carries(self, render):
        result = render("annotations", SOURCE, "--circulate")

        assert "⟦HOLE: the production registration arm⟧" in result.document


class TestTheAdvisoryLints:
    """Advisory means advisory: neither of these moves the exit code."""

    def test_a_label_over_eighty_characters_warns(self, render):
        result = render("annotations", SOURCE, "--check")

        assert "over the 80-character advisory limit" in warnings_of(result.report)

    def test_a_long_label_never_refuses(self, paper, run_in):
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(
            source.read_text()
            .replace("{{! the production registration arm }}", "the accuracy preset")
            .replace("{{! best-arm Dice }}", "0.89")
            .replace("<!-- !@lab-imaging unverified:", "<!-- @lab-imaging unverified:")
        )

        result = run_in(where, SOURCE, "--check")

        assert result.exit_code == 0
        assert "over the 80-character advisory limit" in warnings_of(result.report)

    def test_a_bare_brace_alone_in_its_own_block_warns_that_it_is_probably_a_slot(
        self, render
    ):
        result = render("annotations", SOURCE, "--check")
        warnings = warnings_of(result.report)

        assert "the funder acknowledgement" in warnings
        assert "probably a `SLOT:`" in warnings

    def test_a_marked_slot_alone_in_its_own_block_does_not_warn(self, render):
        result = render("annotations", SOURCE, "--check")

        assert "ethics approval number" not in warnings_of(result.report)

    def test_a_brace_mid_sentence_does_not_warn(self, render):
        result = render("annotations", SOURCE, "--check")

        assert "best-arm Dice" not in warnings_of(result.report)

    def test_position_is_evidence_and_not_the_definition(self, render):
        # The block-alone brace warns and still behaves as the HOLE it is.
        result = render("annotations", SOURCE, "--circulate")

        assert "⟦HOLE: the funder acknowledgement⟧" in result.document


class TestTheVerifyFlag:
    """A verify flag is SILENT plus the gate bit, and nothing else: an
    unverified claim is exactly what must not reach a journal."""

    def test_it_emits_nothing(self, render):
        result = render("annotations", SOURCE, "--circulate")

        assert "unverified" not in result.document

    def test_it_is_in_the_manifest_because_of_the_bit(self, render):
        result = render("annotations", SOURCE, "--check")

        assert "the six paired fractions are not in any committed table" in manifest_of(
            result.report
        )

    def test_it_blocks_submission(self, paper, run_in):
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(
            source.read_text()
            .replace("{{! the production registration arm }}", "the accuracy preset")
            .replace("{{! best-arm Dice }}", "0.89")
        )

        result = run_in(where, SOURCE, "--submit")

        assert result.exit_code == 1
        assert result.document == ""
        assert "the six paired fractions" in result.report.split("--submit refused")[1]

    def test_a_plain_verify_note_with_no_bit_is_invisible_twice_over(
        self, paper, run_in
    ):
        # The defect the clause exists to close: without the bit a verify note
        # is in neither the render nor the manifest.
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(
            source.read_text().replace(
                "<!-- !@lab-imaging unverified: the six paired fractions are not in any "
                "committed table -->",
                "<!-- verify the six paired fractions against a committed table -->",
            )
        )

        result = run_in(where, SOURCE, "--check")

        assert "six paired fractions" not in manifest_of(result.report)
        assert "annotations (gating)      FAIL — 2" in result.report


class TestTheDirectionalClause:
    """A directional word is committed before the value exists, and `A8`
    deletes the annotation the moment the value is filled — so the direction
    has to be named while the hole is still open."""

    def test_a_hole_under_a_directional_word_gets_one_manifest_line(self, render):
        result = render("annotations", SOURCE, "--check")
        entry = manifest_of(result.report).split("best-arm Dice")[1]

        assert "direction: `raised` is committed before this value exists" in entry

    def test_the_line_names_the_direction_once_and_not_per_word(self, render):
        result = render("annotations", SOURCE, "--check")
        entry = manifest_of(result.report).split("best-arm Dice")[1].split("HOLE")[0]

        assert entry.count("direction:") == 1

    def test_a_directional_claim_inherits_the_holes_gate_bit(self, render):
        # `raised` governs two holes in one sentence; the bit is the hole's, so
        # the gated one blocks and the ungated one does not.
        result = render("annotations", SOURCE, "--submit")
        refusal = result.report.split("--submit refused")[1]

        assert "best-arm Dice" in refusal
        assert "rigid-only Dice" not in refusal

    def test_but_both_carry_the_direction_line(self, render):
        result = render("annotations", SOURCE, "--check")
        entry = manifest_of(result.report).split("rigid-only Dice")[1]

        assert "direction: `raised` is committed before this value exists" in entry

    def test_a_hole_under_no_directional_word_carries_no_direction_line(self, render):
        result = render("annotations", SOURCE, "--check")
        entry = manifest_of(result.report).split("the funder acknowledgement")[1]

        assert "direction:" not in entry


class TestBraceGrammarIsAParseError:
    """The source cannot express a malformed brace: it has no behaviour and no
    gate bit to honour, so it is in the same category as an unclosed comment."""

    def test_an_unclosed_brace_is_a_parse_error(self, paper, run_in):
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(
            source.read_text().replace("{{! best-arm Dice }}", "{{! best-arm Dice")
        )

        result = run_in(where, SOURCE, "--check")

        assert result.exit_code == 3
        assert "unclosed brace" in result.report
        assert "PASS" not in result.report

    def test_an_unmatched_closing_brace_is_a_parse_error(self, paper, run_in):
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(
            source.read_text().replace("{{! best-arm Dice }}", "best-arm Dice }}")
        )

        result = run_in(where, SOURCE, "--check")

        assert result.exit_code == 3
        assert "unmatched `}}`" in result.report

    def test_a_brace_naming_nothing_is_a_parse_error(self, paper, run_in):
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(source.read_text().replace("{{! best-arm Dice }}", "{{ ! }}"))

        result = run_in(where, SOURCE, "--check")

        assert result.exit_code == 3
        assert "names no value" in result.report

    def test_prefixes_out_of_order_are_a_parse_error(self, paper, run_in):
        # `!` is always leading, so `SLOT: !` would silently lose the gate bit.
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(
            source.read_text().replace(
                "{{ SLOT: ethics approval number }}", "{{ SLOT: ! ethics approval number }}"
            )
        )

        result = run_in(where, SOURCE, "--check")

        assert result.exit_code == 3
        assert "once each, in that order" in result.report

    def test_a_near_miss_slot_marker_is_a_parse_error(self, paper, run_in):
        # A brace whose first token claims to be `SLOT:` and is not would
        # otherwise become a HOLE silently.
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(
            source.read_text().replace(
                "{{ SLOT: ethics approval number }}", "{{ slot: ethics approval number }}"
            )
        )

        result = run_in(where, SOURCE, "--check")

        assert result.exit_code == 3
        assert "claims to be a venue slot" in result.report

    def test_a_brace_inside_a_comment_is_not_a_brace(self, render):
        # The reasoning comment holds `{{…}}` as a join key, not as an
        # annotation of its own.
        result = render("annotations", SOURCE, "--check")

        assert result.exit_code == 1
        assert "10 open annotations" in result.report

    def test_a_brace_inside_a_fence_is_not_a_brace(self, paper, run_in):
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(
            source.read_text().replace(
                "{{ the funder acknowledgement }}",
                "```\n{{ SLOT: shown, not used }}\n```",
            )
        )

        result = run_in(where, SOURCE, "--check")

        assert "shown, not used" not in manifest_of(result.report)


class TestCreationRightsAreDocumentedAndHonoured:
    def test_the_render_creates_no_annotation_in_the_source(self, paper, run_in):
        where = paper("annotations")
        source = where / SOURCE
        before = source.read_bytes()

        run_in(where, SOURCE, "--circulate")
        run_in(where, SOURCE, "--check")

        assert source.read_bytes() == before

    def test_the_grid_is_documented_beside_the_script(self):
        from conftest import SCRIPT

        grid = (SCRIPT.parent.parent / "ANNOTATION-CHANNEL.md").read_text()

        assert "`write-paper`" in grid
        assert "`review-paper`" in grid
        assert "`assemble-paper`" in grid
        assert "`SILENT` only" in grid
        assert "the render creates none" in grid.lower()


class TestDeletionIsTheOnlyClosure:
    def test_a_resolved_marker_is_an_ordinary_comment_tracked_nowhere(self, render):
        result = render("annotations", SOURCE, "--check")

        assert "superseded" not in manifest_of(result.report)
        assert "RESOLVED" not in result.report

    def test_no_tombstone_reaches_the_render(self, render):
        result = render("annotations", SOURCE, "--circulate")

        assert "RESOLVED" not in result.document
        assert "superseded" not in result.document

    def test_substituting_the_value_closes_the_hole_and_leaves_the_sentence(
        self, paper, run_in
    ):
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(
            source.read_text()
            .replace("{{! best-arm Dice }}", "0.89")
            .replace("{{ rigid-only Dice }}", "0.71")
        )

        result = run_in(where, SOURCE, "--circulate")

        assert "Registration raised Dice to 0.89 from 0.71, which is what the" in (
            result.document
        )
        assert "best-arm Dice" not in result.report

    def test_deleting_a_silent_comment_closes_it(self, paper, run_in):
        where = paper("annotations")
        source = where / SOURCE
        source.write_text(
            source.read_text().replace(
                "<!-- @author waiting on the IRB number before submission -->\n", ""
            )
        )

        result = run_in(where, SOURCE, "--check")

        assert "IRB number" not in result.report
        assert "9 open annotations" in result.report


class TestSectionGranularity:
    """The gate is scoped to the granularity, the way every other row is. The
    manifest is not: it enters whole, because it is an absolute input to a
    diff-relative axis."""

    def test_the_gate_sees_only_this_units_annotations(self, render):
        result = render("annotations", SOURCE, "--check", "--section", "back-matter")

        assert result.exit_code == 0
        assert "annotations (gating)      PASS" in result.report

    def test_the_manifest_still_enters_whole(self, render):
        result = render("annotations", SOURCE, "--check", "--section", "back-matter")

        assert "10 open annotations, 3 carrying the gate bit" in result.report
        assert "best-arm Dice" in manifest_of(result.report)

    def test_a_section_submit_refuses_on_its_own_units_bits(self, render):
        result = render("annotations", SOURCE, "--submit", "--section", "results")

        assert result.exit_code == 1
        assert result.document == ""
        assert "best-arm Dice" in result.report.split("--submit refused")[1]

    def test_but_not_on_another_units(self, render):
        result = render("annotations", SOURCE, "--submit", "--section", "back-matter")

        assert result.exit_code == 0
        assert "⟦SLOT: ethics approval number⟧" in result.document
