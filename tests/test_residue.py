"""The two residue lints: the bare-hole token list (`G3`) and the workflow-phrase
lint (`C4`).

Both catch **the unmarkable residue** — unfinished text that is grammatical
reader-facing prose, so no bracket-stripping can see it. *"of order of XX"*
inside a finished-sounding sentence is a claim resting on a number that is
literally absent; *"is a submission-readiness item"* is author workflow state
written as a sentence the reader will read.

Both are calibrated on the corpus, and the measurements are the warrant for
refusing rather than warning. So they live here as tests and cannot silently
rot, and the two costs the calibration accepts are asserted as costs.

Every test invokes the CLI as a subprocess over a fixture paper and asserts on
what a caller can see: the exit code, the emitted document, the verdict report.
"""

import re

SOURCE = "MANUSCRIPT.working.md"

BARE_HOLES = "bare holes"
WORKFLOW_PHRASES = "workflow phrases"


def row(report, name):
    """One verdict row of a report, verbatim, minus its name."""
    for line in report.splitlines():
        if line.strip().startswith(name):
            return line.strip()[len(name) :].strip()
    return None


def hits_in(report, name):
    """How many hits one row reports, or 0 when it passed."""
    verdict = row(report, name)
    found = re.match(r"(?:FAIL|WARN) — (\d+) ", verdict or "")
    return int(found.group(1)) if found else 0


def warns_in_tally(report):
    """The `warn` count on the tally line, or 0 when it is absent.

    Absent rather than zero is the reported tier's own convention for its
    count, and this one follows it.
    """
    found = re.search(r"out of scope.*?(\d+) warn", report)
    return int(found.group(1)) if found else 0


class TestTheBareHoleListIsSubmitGating:
    """`G3`: the render is faithful either way — the hole is right there in the
    prose — but the work is unfinished, so it gates submission and never blocks
    circulation."""

    def test_circulate_still_emits(self, render):
        result = render("residue", SOURCE, "--circulate")

        assert result.document != ""
        assert "of order of XX" in result.document

    def test_submit_refuses_and_emits_nothing(self, render):
        result = render("residue", SOURCE, "--submit")

        assert result.exit_code == 1
        assert result.document == ""
        assert BARE_HOLES in result.report

    def test_the_refusal_prints_the_list(self, render):
        result = render("residue", SOURCE, "--submit")

        assert "--submit refused" in result.report
        assert "`XX`" in result.report
        assert "`XXX`" in result.report

    def test_each_hit_names_its_source_line(self, render):
        result = render("residue", SOURCE, "--check")

        assert re.search(r"%s:\d+ `XX`" % SOURCE, result.report)
        assert re.search(r"%s:\d+ `XXX`" % SOURCE, result.report)

    def test_the_row_fails_under_circulate_too(self, render):
        """A bare hole is a plain gating row: one gate, and the mode decides
        only whether the document is withheld."""
        result = render("residue", SOURCE, "--circulate")

        assert row(result.report, BARE_HOLES).startswith("FAIL")
        assert result.exit_code == 1


class TestTheTokenList:
    """`XX+`, `TBD`, `TK`, `FIXME`, `???` — short, dumb and paper-agnostic."""

    def test_every_token_is_caught(self, paper, run_in):
        where = paper("residue")
        source = where / SOURCE
        source.write_text(
            source.read_text().replace(
                "The residual distance is of order of XX,",
                "The residual distance is TBD, the TK value is missing, FIXME, and why???",
            )
        )

        result = run_in(where, SOURCE, "--check")

        for token in ("TBD", "TK", "FIXME", "???"):
            assert "`%s`" % token in result.report

    def test_a_longer_run_of_x_is_one_hit_not_many(self, paper, run_in):
        where = paper("karyotype")
        source = where / SOURCE
        source.write_text(source.read_text().replace("47,XXX", "49,XXXXX"))

        result = run_in(where, SOURCE, "--check")

        assert "`XXXXX`" in result.report

    def test_it_does_not_fire_inside_a_word(self, paper, run_in):
        """`TKI` is a tyrosine kinase inhibitor and `TBX21` is a gene. A list
        that fired inside words would be useless on biomedical prose."""
        result = run_in(paper("residue-calibration"), SOURCE, "--check")

        assert hits_in(result.report, BARE_HOLES) == 0

    def test_two_question_marks_are_not_three(self, paper, run_in):
        where = paper("residue-calibration")
        source = where / SOURCE
        source.write_text(
            source.read_text().replace(
                "carry\na per-arm comparison?", "carry\na per-arm comparison??"
            )
        )

        result = run_in(where, SOURCE, "--check")

        assert hits_in(result.report, BARE_HOLES) == 0


class TestTheLintSeesReaderFacingProseOnly:
    """The residue is what the *reader* meets. The author-facing channel is
    where a hole is allowed to be named, so a lint that read it would refuse
    the very mechanism the channel exists to provide."""

    def test_a_token_inside_an_annotation_label_is_not_a_bare_hole(self, render):
        """`{{ @lab-imaging TBD residual distance }}` is a *marked* hole. It
        lands in the manifest and the gate bit decides whether it blocks."""
        result = render("residue", SOURCE, "--check")

        assert "TBD residual distance" in result.report
        assert hits_in(result.report, BARE_HOLES) == 2

    def test_a_token_inside_a_comment_is_not_a_workflow_phrase(self, render):
        """A `TODO` in a comment is the author talking to the author. It never
        reaches the reader, so it is not residue."""
        result = render("residue", SOURCE, "--check")

        assert "TODO" not in row(result.report, WORKFLOW_PHRASES)

    def test_a_token_inside_a_fence_is_not_a_hit(self, render):
        """A fence is literal text being shown, not prose being claimed —
        nothing else in this parser reads inside one either."""
        result = render("residue", SOURCE, "--check")

        assert "FIXME" not in row(result.report, BARE_HOLES)


class TestTheWorkflowPhraseLint:
    """`C4`: submit-gating under `--submit`, and **warns** under `--circulate`.

    Its tells are far likelier to be legitimate prose than `XX` or `FIXME`
    are, so it must not put a failing row in front of an author who only wants
    to circulate a draft."""

    def test_submit_refuses(self, render):
        result = render("workflow-prose", SOURCE, "--submit")

        assert result.exit_code == 1
        assert result.document == ""
        assert row(result.report, WORKFLOW_PHRASES).startswith("FAIL")

    def test_circulate_warns_instead(self, render):
        result = render("workflow-prose", SOURCE, "--circulate")

        assert row(result.report, WORKFLOW_PHRASES).startswith("WARN")

    def test_circulate_emits_and_moves_no_exit_code(self, render):
        """The whole point of the asymmetry: a dumb lint must not disturb the
        everyday path."""
        result = render("workflow-prose", SOURCE, "--circulate")

        assert result.exit_code == 0
        assert result.document != ""

    def test_check_answers_the_submit_question_so_it_fails(self, render):
        """`review-paper` runs `--check` and reports the table verbatim. A row
        that warned there would hide the gate from the axis that reads it."""
        result = render("workflow-prose", SOURCE, "--check")

        assert result.exit_code == 1
        assert row(result.report, WORKFLOW_PHRASES).startswith("FAIL")

    def test_every_tell_is_caught(self, paper, run_in):
        where = paper("workflow-prose")
        source = where / SOURCE
        source.write_text(
            source.read_text().replace(
                "we should expect the residual distance to scale with the number of rounds, and it does.",
                "the exact figure is to be confirmed. TODO: note to self, this is a "
                "submission-readiness item.",
            )
        )

        result = run_in(where, SOURCE, "--check")

        for tell in ("to be confirmed", "TODO", "note to self", "submission-readiness"):
            assert "`%s`" % tell in result.report

    def test_a_warn_row_is_never_a_pass(self, render):
        """`G6` abolished `CLEAN` because one word cannot carry both
        checked-and-fine and never-looked. A warning printed as `PASS` would
        reintroduce exactly that."""
        result = render("workflow-prose", SOURCE, "--circulate")

        assert "WARN — 2" in result.report
        assert warns_in_tally(result.report) == 1


class TestNeitherLintChangesTheExitCodeBeyondTheWarningChannel:
    """The two lints reuse the existing gating tier and the exit-code-neutral
    advisory channel, and add no third exit-code path."""

    def test_a_warning_row_leaves_the_exit_code_at_zero(self, render):
        result = render("workflow-prose", SOURCE, "--circulate")

        assert result.exit_code == 0

    def test_a_clean_paper_is_still_clean(self, render):
        result = render("residue-calibration", SOURCE, "--circulate")

        assert result.exit_code == 0
        assert hits_in(result.report, BARE_HOLES) == 0
        assert hits_in(result.report, WORKFLOW_PHRASES) == 0

    def test_neither_lint_is_exposed_as_a_configurable_threshold(self, render):
        """A configurable refusal *is* the override these rules exist to
        prevent, wearing a config file (`CT2`).

        Asserted at the CLI, because the interface is where an override would
        have to appear to be usable. Note the one threshold flag that does
        exist and why it is not a counter-example: `--em-dash-threshold` tunes
        a **reported** row, which has no bucket in `failed` and so cannot reach
        the exit code at all. A threshold on a measurement is a reading
        instrument; a threshold on a refusal is an override.
        """
        result = render("residue", "--help")

        flags = set(re.findall(r"--[a-z][a-z-]*", result.document))

        assert flags == {
            "--circulate",
            "--submit",
            "--check",
            "--scaffold",
            "--section",
            "--paper",
            "--em-dash-threshold",
            "--help",
        }

    def test_the_one_threshold_flag_cannot_move_a_gating_row(self, paper, run_in):
        """The distinction the test above rests on, exercised rather than
        asserted: raising the em-dash bar as far as it goes leaves both residue
        refusals exactly where they were."""
        where = paper("residue")
        wide_open = run_in(where, SOURCE, "--check", "--em-dash-threshold", "9999")

        assert wide_open.exit_code == 1
        assert hits_in(wide_open.report, BARE_HOLES) == 2
        assert hits_in(wide_open.report, WORKFLOW_PHRASES) == 2



class TestTheCalibration:
    """`G3` measured the token list at **zero hits** across all thirteen
    section drafts and the mechanical baseline — zero false positives in 74 KB
    of biomedical prose — and **two hits** in the hand-revised manuscript,
    both inside reader-facing claims. That measurement is the warrant for
    refusing rather than warning.

    **What these tests are, and are not.** The corpus is an unpublished
    manuscript held outside this repo, so no test here re-runs that
    measurement. What they check is the *property* it was evidence for: zero
    hits over a fixture built to carry every near-miss shape biomedical prose
    contains, and two hits over the two shapes the audit recorded. So the
    behaviour the number stands for cannot rot unnoticed, but the 74 KB figure
    is a citation, not an assertion — re-run it against the corpus before
    trusting it again after changing either token list.
    """

    def test_zero_hits_across_near_miss_biomedical_prose(self, render):
        result = render("residue-calibration", SOURCE, "--check")

        assert hits_in(result.report, BARE_HOLES) == 0
        assert row(result.report, BARE_HOLES) == "PASS"

    def test_the_near_miss_prose_really_does_carry_the_near_misses(self, paper):
        """Guards the guard: a calibration fixture that lost its near misses
        would score zero for the wrong reason and nobody would notice."""
        text = (paper("residue-calibration") / SOURCE).read_text()

        for shape in ("TKI", "TBS", "46,XY", "FOXP3", "TBX21", "fixed", "XII", "TB"):
            assert shape in text

    def test_two_hits_in_the_hand_revised_shapes(self, render):
        result = render("residue", SOURCE, "--check")

        assert hits_in(result.report, BARE_HOLES) == 2

    def test_both_hits_sit_inside_reader_facing_claims(self, render):
        """This is why the tier is submit-gating and not advisory: each hole
        sits in a sentence that asserts something, so stripping it silently
        would convert a flagged gap into an unsupported claim."""
        result = render("residue", SOURCE, "--circulate")

        assert (
            "The residual distance is of order of XX, which is acceptable for the "
            "intensity analysis." in result.document
        )
        assert "the pipeline is compatible with XXX inputs" in result.document


class TestTheDocumentedCostOfTheBareHoleList:
    """**Documented cost, not desired behaviour.** `46,XX` and `47,XXX` are
    standard karyotype notation and `TK` is thymidine kinase; the list fires on
    all three. It is safe on this corpus only because the corpus contains none
    of them, and a wrong refusal breaks a paper that never asked for any of
    this.

    These tests assert what the list *currently rejects*, so that resolving the
    fog changes the behaviour deliberately and visibly instead of by someone
    quietly loosening a pattern.
    """

    def test_standard_karyotype_notation_is_currently_rejected(self, render):
        result = render("karyotype", SOURCE, "--submit")

        assert result.exit_code == 1
        assert "`XX`" in result.report
        assert "`XXX`" in result.report

    def test_thymidine_kinase_is_currently_rejected_too(self, render):
        result = render("karyotype", SOURCE, "--submit")

        assert "`TK`" in result.report

    def test_the_cost_is_bounded_the_karyotype_paper_circulates_freely(self, render):
        """The asymmetry that bounds the harm: `G3` is submit-gating, so this
        paper still renders a circulatable document."""
        result = render("karyotype", SOURCE, "--circulate")

        assert result.document != ""
        assert "Twelve were 46,XX and one carried 47,XXX" in result.document


class TestTheDocumentedCostOfTheWorkflowPhraseLint:
    """**Documented cost, not desired behaviour.** `pending` and `we should`
    are ordinary academic English — a pending trial is a fact about the
    literature and *"we should expect"* is a hedge, not a note to the author.
    The lint is short and dumb by design, so it fires on both.
    """

    def test_a_pending_trial_is_currently_rejected(self, render):
        result = render("workflow-prose", SOURCE, "--submit")

        assert result.exit_code == 1
        assert "`pending`" in result.report

    def test_a_hedge_is_currently_rejected_too(self, render):
        result = render("workflow-prose", SOURCE, "--submit")

        assert "`we should`" in result.report

    def test_the_cost_is_bounded_more_tightly_than_the_bare_hole_lists(self, render):
        """This lint warns under `--circulate` rather than failing, so its
        false positives cost an author nothing on the everyday path."""
        result = render("workflow-prose", SOURCE, "--circulate")

        assert result.exit_code == 0
        assert row(result.report, WORKFLOW_PHRASES).startswith("WARN")


class TestSectionGranularity:
    """One gate, two granularities — the lints are scoped the way every other
    row is, because prose exists at both."""

    def test_a_hit_outside_the_section_is_out_of_scope(self, render):
        result = render("residue", SOURCE, "--check", "--section", "methods")

        assert hits_in(result.report, BARE_HOLES) == 0

    def test_a_hit_inside_the_section_is_in_scope(self, render):
        result = render("residue", SOURCE, "--check", "--section", "results")

        assert hits_in(result.report, BARE_HOLES) == 1
        assert "`XX`" in result.report

    def test_neither_row_is_ever_out_of_scope(self, render):
        result = render("residue", SOURCE, "--check", "--section", "methods")

        assert row(result.report, BARE_HOLES) == "PASS"
        assert row(result.report, WORKFLOW_PHRASES) == "PASS"
