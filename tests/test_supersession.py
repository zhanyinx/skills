"""The supersession diff (`RV4`): what a re-draft silently lost.

A `revise` ticket replaces prose that already shipped, and the hazard is the
loss nobody declares — 2,767 words down to 584 with a whole block gone, in the
corpus this design was audited against. So the render compares the **old render**
of one unit against the **new render** and reports five structural losses: body
word count falling past a threshold, a heading-level block gone, a figure or
panel reference gone, a reference that has lost its only in-text anchor, and a
gate-bit annotation that vanished without being closed.

**It is a finding, never a gate.** A revision that correctly removes 2,000 words
because the ladder amendment deleted the rung those words served must not be
blocked by its own success, so every test here that asserts a loss also asserts
that the exit code did not move.

**There is no keep-list.** A list of what must not change would be written by
the same agent that drops a claim, and it would omit the dropped claim too, so
the drop-guard is mechanical and the interface carries no such field.

The old side comes from git: renders are ephemeral, but the render is a pure
function of the source and the commit the draft ticket closed at is the audit
trail. Every test invokes the CLI as a subprocess over a fixture paper in a
repository of its own and asserts on what a caller can see.
"""

import re
import shutil

CASE = "supersession"
SOURCE = "MANUSCRIPT.working.md"
UNIT = "methods"
ROW = "supersession diff"

# The gate-bit hole the fixture's `methods` carries, and the paragraph it sits
# in. Closing it means substituting the value and leaving the sentence standing;
# deleting the paragraph is what makes it vanish unclosed.
HOLE = "{{! the registration preset }}"
GATE_PARAGRAPH = (
    "Registration ran against the {{! the registration preset }} arm, and the accuracy figure was\n"
    "produced from that arm rather than from the shipped default.\n"
)


def row(report, name):
    """One verdict row of a report, verbatim, minus its name."""
    for line in report.splitlines():
        if line.strip().startswith(name):
            return line.strip()[len(name) :].strip()
    return None


def source_of(root):
    return root / SOURCE


def revise(root, before, after):
    """Rewrite the working source the way a `revise` ticket does."""
    path = source_of(root)
    text = path.read_text()
    assert before in text, "the fixture no longer carries %r" % before
    path.write_text(text.replace(before, after))


def drop_most_of_methods(root):
    """A revision that legitimately deletes most of a unit.

    Every slot keeps prose, so `unfilled skeleton slot` stays clean and the only
    thing left to move the exit code would be this row.
    """
    text = source_of(root).read_text()
    start = text.index("<!-- slot: methods -->")
    end = text.index("<!-- slot: methods-imaging -->")
    source_of(root).write_text(
        text[:start]
        + "<!-- slot: methods -->\n\nThe pipeline runs as five stages.\n\n"
        + text[end:]
    )


def words_in(verdict):
    """The two body word counts one row reports."""
    found = re.search(r"body (\d+) → (\d+) words", verdict)
    return (int(found.group(1)), int(found.group(2))) if found else None


class TestTheDiffRunsOverOneUnitAgainstOneRef:
    """The diff is per-unit and takes the commit ref the original draft closed
    at. A whole-document render has no old side to compare a unit against, and
    says so the way every other out-of-scope row does."""

    def test_the_row_reports_the_two_body_word_counts(self, versioned, run_in):
        root, ref = versioned(CASE)
        drop_most_of_methods(root)

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        assert words_in(row(result.report, ROW)) is not None

    def test_the_counts_are_the_old_render_against_the_new(self, versioned, run_in):
        root, ref = versioned(CASE)
        drop_most_of_methods(root)

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        old, new = words_in(row(result.report, ROW))
        assert old > new

    def test_whole_document_granularity_is_out_of_scope(self, versioned, run_in):
        root, ref = versioned(CASE)
        drop_most_of_methods(root)

        result = run_in(root, SOURCE, "--check", "--supersedes", ref)

        assert row(result.report, ROW) == "SKIPPED — OUT OF SCOPE AT THIS GRANULARITY"

    def test_without_a_ref_the_row_says_so_rather_than_passing(
        self, versioned, run_in
    ):
        root, _ref = versioned(CASE)

        result = run_in(root, SOURCE, "--check", "--section", UNIT)

        assert "not a supersession" in row(result.report, ROW)

    def test_a_row_with_no_old_side_is_never_a_pass(self, versioned, run_in):
        root, _ref = versioned(CASE)

        result = run_in(root, SOURCE, "--check", "--section", UNIT)

        assert "PASS" not in row(result.report, ROW)

    def test_the_row_prints_in_registry_order_after_the_locality_test(
        self, versioned, run_in
    ):
        root, ref = versioned(CASE)

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        names = [line.strip().split("  ")[0] for line in result.report.splitlines()]
        assert names.index(ROW) == names.index("locality test") + 1


class TestTheFiveStructuralLosses:
    """All five classes are detected, and each names what went missing."""

    def test_body_word_count_falling_past_the_threshold(self, versioned, run_in):
        root, ref = versioned(CASE)
        drop_most_of_methods(root)

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        assert "past the" in row(result.report, ROW)

    def test_a_drop_inside_the_threshold_is_not_flagged(self, versioned, run_in):
        root, ref = versioned(CASE)
        revise(root, " through the procedure", "")

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        verdict = row(result.report, ROW)
        assert "past the" not in verdict
        assert "no structural loss" in verdict

    def test_a_heading_level_block_present_before_and_absent_after(
        self, versioned, run_in
    ):
        root, ref = versioned(CASE)
        skeleton = root / "skeleton.md"
        skeleton.write_text(
            "".join(
                line
                for line in skeleton.read_text().splitlines(True)
                if "methods-registration" not in line
            )
        )
        text = source_of(root).read_text()
        source_of(root).write_text(
            text[: text.index("<!-- slot: methods-registration -->")]
        )

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        verdict = row(result.report, ROW)
        assert "heading" in verdict
        assert "Registration" in verdict

    def test_a_figure_reference_present_before_and_absent_after(
        self, versioned, run_in
    ):
        root, ref = versioned(CASE)
        revise(root, "\n(@fig:pipeline)", "")

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        assert "@fig:pipeline" in row(result.report, ROW)

    def test_a_reference_that_lost_its_only_in_text_anchor(self, versioned, run_in):
        root, ref = versioned(CASE)
        revise(root, "the earlier mapping work published @hickey2022, and", "and")

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        assert "@hickey2022" in row(result.report, ROW)

    def test_a_key_still_anchored_elsewhere_has_not_lost_its_only_anchor(
        self, versioned, run_in
    ):
        """`@gatenbee2023` is cited in `results` as well, so dropping it from
        `methods` costs the document no reference at all — and the reference
        list is built from the cited keys, which is the fact this class is
        about."""
        root, ref = versioned(CASE)
        revise(root, "round by round [@gatenbee2023]", "round by round")

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        assert "@gatenbee2023" not in row(result.report, ROW)

    def test_a_gate_bit_annotation_that_vanished_without_being_closed(
        self, versioned, run_in
    ):
        root, ref = versioned(CASE)
        revise(root, GATE_PARAGRAPH + "\n", "")

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        verdict = row(result.report, ROW)
        assert "vanished" in verdict
        assert "the registration preset" in verdict

    def test_a_gate_bit_annotation_deleted_in_place_is_reported(
        self, versioned, run_in
    ):
        """The marker taken out and no value put in: the paragraph survives
        word for word, and the claim now rests on nothing.

        This is the shape the class is really about. The old side's prose
        already carries the brace blanked, so a supplied value is the one thing
        that leaves the paragraph longer — and this revision leaves it exactly
        as long.
        """
        root, ref = versioned(CASE)
        revise(root, "the %s arm" % HOLE, "the arm")

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        verdict = row(result.report, ROW)
        assert "vanished" in verdict
        assert "the registration preset" in verdict

    def test_a_gate_bit_annotation_closed_by_substitution_is_not_a_loss(
        self, versioned, run_in
    ):
        """Substituting the real value **is** the closure — there is no
        `RESOLVED` marker and no tombstone — so nothing was lost."""
        root, ref = versioned(CASE)
        revise(root, HOLE, "medium-preset")

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        verdict = row(result.report, ROW)
        assert "vanished" not in verdict
        assert "no structural loss" in verdict

    def test_a_renamed_heading_is_not_a_lost_one(self, versioned, run_in):
        """A block **is** a slot: the skeleton owns the words and the render
        injects them on every pass, so a rename is the same block under a new
        name. Diffing the rendered words instead would call every rename a
        loss."""
        root, ref = versioned(CASE)
        skeleton = root / "skeleton.md"
        skeleton.write_text(
            skeleton.read_text().replace(
                "| methods-registration | 3 | Registration |",
                "| methods-registration | 3 | Image registration |",
            )
        )

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        verdict = row(result.report, ROW)
        assert "heading" not in verdict
        assert "no structural loss" in verdict

    def test_every_class_reports_at_once(self, versioned, run_in):
        root, ref = versioned(CASE)
        drop_most_of_methods(root)

        verdict = row(
            run_in(
                root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref
            ).report,
            ROW,
        )

        assert "past the" in verdict
        assert "@fig:pipeline" in verdict
        assert "@hickey2022" in verdict
        assert "vanished" in verdict


class TestAFindingNeverAGate:
    """A revision that correctly removes most of a unit must not be blocked by
    its own success. The row is in the reported tier, which has no bucket the
    exit code reads, and it prints a number rather than a verdict."""

    def test_check_still_exits_zero(self, versioned, run_in):
        root, ref = versioned(CASE)
        drop_most_of_methods(root)

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        assert result.exit_code == 0

    def test_circulate_still_emits(self, versioned, run_in):
        root, ref = versioned(CASE)
        drop_most_of_methods(root)

        result = run_in(
            root, SOURCE, "--circulate", "--section", UNIT, "--supersedes", ref
        )

        assert result.exit_code == 0
        assert result.document != ""

    def test_submit_still_emits(self, versioned, run_in):
        root, ref = versioned(CASE)
        drop_most_of_methods(root)

        result = run_in(
            root, SOURCE, "--submit", "--section", UNIT, "--supersedes", ref
        )

        assert result.exit_code == 0
        assert result.document != ""

    def test_the_row_never_prints_a_verdict_word(self, versioned, run_in):
        root, ref = versioned(CASE)
        drop_most_of_methods(root)

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        verdict = row(result.report, ROW)
        assert "FAIL" not in verdict
        assert "PASS" not in verdict

    def test_the_loss_is_tallied_as_reported_and_never_as_a_fail(
        self, versioned, run_in
    ):
        root, ref = versioned(CASE)
        drop_most_of_methods(root)

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        assert "0 fail" in result.report


class TestTheOldSideComesFromGit:
    """The old side is reconstructed by checking the source out at the ref and
    running the same render. Every way that can fail is reported in the row and
    refuses nothing."""

    def test_an_unknown_ref_is_reported_and_never_refuses(self, versioned, run_in):
        root, _ref = versioned(CASE)
        # The fixture's own open hole is filled first, so nothing but this row
        # is left that could move the exit code.
        revise(root, HOLE, "medium-preset")

        result = run_in(
            root, SOURCE, "--check", "--section", UNIT, "--supersedes", "nosuchref"
        )

        assert result.exit_code == 0
        assert "unavailable" in row(result.report, ROW)

    def test_a_paper_outside_git_is_reported_and_never_refuses(self, paper, run_in):
        root = paper(CASE)
        revise(root, HOLE, "medium-preset")

        result = run_in(
            root, SOURCE, "--check", "--section", UNIT, "--supersedes", "HEAD"
        )

        assert result.exit_code == 0
        assert "unavailable" in row(result.report, ROW)

    def test_the_old_side_reads_the_committed_source_not_the_working_one(
        self, versioned, run_in
    ):
        """The whole point of the ref: the old count is the count as committed,
        and it does not move when the working tree does."""
        root, ref = versioned(CASE)
        unrevised = words_in(
            row(
                run_in(
                    root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref
                ).report,
                ROW,
            )
        )
        drop_most_of_methods(root)

        revised = words_in(
            row(
                run_in(
                    root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref
                ).report,
                ROW,
            )
        )

        assert unrevised == (unrevised[0], unrevised[0])
        assert revised[0] == unrevised[0]

    def test_a_pre_promotion_draft_diffs_against_the_same_file(
        self, versioned, run_in
    ):
        """Pre-promotion the source is `drafts/<unit>.md`, and the old side is
        that same path at the ref."""
        root, ref = versioned("pre-promotion")

        result = run_in(
            root, "drafts", "--check", "--section", "results", "--supersedes", ref
        )

        assert words_in(row(result.report, ROW)) is not None

    def test_a_promoted_unit_diffs_against_the_frozen_draft(self, versioned, run_in):
        """Post-promotion one side comes from the working manuscript and the
        other from the frozen `drafts/<unit>.md` — well-defined because both go
        through the same render at the same **anchor**, and anchors, not
        headings, are what live in the source.

        The promotion here moves the prose and changes none of it, so the row
        finding nothing is the assertion: it located the old side, rendered it
        at the same anchor, and the two agree.
        """
        root, ref = versioned("pre-promotion")
        (root / SOURCE).write_text(
            "\n\n".join(
                (root / "drafts" / name).read_text()
                for name in ("abstract.md", "results.md")
            )
        )
        shutil.rmtree(root / "drafts")

        result = run_in(
            root, SOURCE, "--check", "--section", "results", "--supersedes", ref
        )

        verdict = row(result.report, ROW)
        assert "unavailable" not in verdict
        assert "no structural loss" in verdict

    def test_the_old_side_is_the_source_that_anchors_the_unit(
        self, versioned, commit, run_in
    ):
        """The realistic post-promotion shape: at the old ref the manuscript
        **already exists**, holding the units promoted before this one, while
        this unit's prose is still in its draft.

        Picking the old side by existence renders a manuscript that anchors
        nothing for the unit, and a body of zero words reports as no loss at
        all — the drop-guard handing back a silent all-clear. So the source that
        anchors the unit is the one that decides.
        """
        root, _first = versioned("pre-promotion")
        (root / SOURCE).write_text((root / "drafts" / "abstract.md").read_text())
        (root / "drafts" / "abstract.md").unlink()
        ref = commit(root, "the abstract promoted; results still a draft")

        (root / SOURCE).write_text(
            "%s\n\n%s"
            % (
                (root / SOURCE).read_text(),
                (root / "drafts" / "results.md").read_text(),
            )
        )
        shutil.rmtree(root / "drafts")

        result = run_in(
            root, SOURCE, "--check", "--section", "results", "--supersedes", ref
        )

        verdict = row(result.report, ROW)
        assert words_in(verdict)[0] > 0
        assert "no structural loss" in verdict


class TestThereIsNoKeepList:
    """A keep-list would be written by the same agent that drops a claim, and it
    would omit the dropped claim too. So the interface has no such field, and
    that absence is asserted rather than assumed."""

    def test_the_interface_takes_a_ref_and_nothing_else(self, versioned, run_in):
        root, _ref = versioned(CASE)

        result = run_in(root, SOURCE, "--help")

        assert "--supersedes" in result.document

    def test_no_option_takes_a_list_of_what_must_not_change(self, versioned, run_in):
        root, _ref = versioned(CASE)

        result = run_in(root, SOURCE, "--help")

        assert "keep" not in result.document.lower()


class TestFiguresAndPanelsAreOneTokenClass:
    """Under `PN1` a figure and a panel are one token class, so this check needs
    no per-class branch: a lost panel reference reports through the same class,
    in the same words, as a lost figure reference."""

    def test_a_lost_panel_reference_reports(self, versioned, run_in):
        root, ref = versioned(CASE)
        revise(root, " (@fig:stage-graph)", "")

        result = run_in(root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref)

        assert "@fig:stage-graph" in row(result.report, ROW)

    def test_a_panel_and_a_figure_report_in_one_class(self, versioned, run_in):
        root, ref = versioned(CASE)
        revise(root, " (@fig:stage-graph)", "")
        revise(root, "\n(@fig:pipeline)", "")

        verdict = row(
            run_in(
                root, SOURCE, "--check", "--section", UNIT, "--supersedes", ref
            ).report,
            ROW,
        )

        assert len(re.findall(r"figure reference lost", verdict)) == 1
        assert "@fig:stage-graph" in verdict
        assert "@fig:pipeline" in verdict
