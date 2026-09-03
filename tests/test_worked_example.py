"""The worked example, end to end: the design's own evidence, as a regression.

The rework spec argued its case on one redrafted section, and recorded eleven
measured properties that improved. Those numbers were a claim in a document.
Here they are a test.

**The fixture is a before/after pair.** `before.md` is the two units as the old
design drafted them: self-minted headings, figures and panels referenced by
literal number, author-facing gaps in improvised bracket spans, and a block of
drafting notes sitting in the stream a reader reads.
`MANUSCRIPT.working.md` is what they become under the new one, inside a whole
document, so the roster resolves against real first-mention order rather than a
section's.

**Neither file is corpus text.** The measured corpus is an unpublished
manuscript held elsewhere and cannot be a fixture here, which is the same call
`skills/render-paper/SKILL.md` already records for the residue calibration and
`tests/fixtures/residue-calibration` for its own near misses. What is
reproduced is the *event*, transposed onto the neutral cyclic-imaging domain
the other fixtures already use: the same two units, carrying the same defect
classes, at the counts below.

| property | before | after |
|---|---|---|
| em dashes | 21 | 0 |
| headings minted by the drafter | 4 (one H1, three H2) | 0 |
| `Fig N` literals | 16, eleven panel-level | 0 |
| bracket spans that are not citations | 8 | 0 |
| negated frames | 2 | 0 |
| adversative connectives | 0 | 4 |

**Those counts are exact, and they are the only ones that are.** The first five
are the ticket's; the sixth is the side effect the worked example recorded, and
it falls out of the redraft rather than being aimed at. Three further rows of
the worked example's own table are *not* carried, because they are properties
of a manuscript's length rather than of a defect class and transposing them
would mean padding prose to hit a word count: body words (1,887 to 1,626), the
brief's length (~1,900 words to 172), and the nine undifferentiated gaps
resolving to six HOLEs, one SILENT and two relocations. The fixture's before
text carries six gaps, so the relocation half of that last row is not shown
here at all. Nothing in the ticket asks for the three, and this module claims
none of them.

**Two kinds of assertion, and the difference is the point.** The counts above
are measured by this module directly, with its own patterns, because the before
text is not a source the renderer can parse at all: it is refused at its first
heading, so no table ever prints over it and there is no renderer-measured
"before". Everything else is asserted through the CLI, over the after text,
exactly as every other test here does it.

**Eight of the fourteen audit defect classes are prevented by construction**,
and for those the assertion is the refusal, never a count of zero — a count of
zero says the text happens not to carry the defect, and a parse error says the
source cannot express it. `RENDER_PAPER_PREVENTS` names the eight and how
each is prevented; `OWNED_ELSEWHERE` names the rest and who owns them, so the
roll-call is complete on the page rather than implied.
"""

import re

import pytest

CASE = "worked-example"
AFTER = "MANUSCRIPT.working.md"
BEFORE = "before.md"


# --------------------------------------------------------------------------
# the measurements
# --------------------------------------------------------------------------

# These patterns are this module's own, and deliberately not the renderer's.
# The before text is refused before any check looks at it, so the "before" half
# of every delta has to be measured by something that is not the gate. An
# independent instrument is also the honest one here: a delta measured with the
# tool under test on both sides proves less than one measured beside it.
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
EM_DASH = "—"
HEADING = re.compile(r"^#{1,6} \S", re.MULTILINE)
FIGURE_LITERAL = re.compile(r"\b(?:fig|figs|figure|figures)\b\.?\s*\d+[a-z]?", re.IGNORECASE)
BRACKET_SPAN = re.compile(r"\[[^\[\]]*\]")
CITATION_GROUP = re.compile(r"^\[@[A-Za-z0-9_:.\-]+(?:\s*;\s*@[A-Za-z0-9_:.\-]+)*\]$")
# `R6`'s shape: the banned frame invoked in a trailing negation so that it can
# be rejected. Narrow on purpose — R6 is a construction rule `write-paper` owns
# and a named smell `review-paper` carries, and neither is mechanical, so this
# is a measurement of two known constructions and not a lint.
NEGATED_FRAME = re.compile(r",\s+not\s+(?:an?|the)?\s*\w+")

# The two the before text carries, quoted. The pattern above is deliberately
# broad and would report a zero for many reasons; these say which two
# constructions actually left.
THE_TWO_NEGATED_FRAMES = (
    "this is concordance among proxies, not validation against a ground truth",
    "The comparison reported here is internal, not a benchmark against competing pipelines",
)
ADVERSATIVE = re.compile(r"\b(?:although|whereas)\b", re.IGNORECASE)


def reader_facing(paper, name):
    """One fixture file with every comment removed.

    The audit's own cut: what a reader meets. It is what makes the two files
    comparable, since the after text carries its author-facing content in
    comments and the before text carries the same content in prose — which is
    the defect.
    """
    return COMMENT.sub("", (paper / name).read_text())


def bracket_spans(text):
    """Every bracket span that is not a citation group."""
    return [span for span in BRACKET_SPAN.findall(text) if not CITATION_GROUP.match(span)]


def row(report, name):
    """One verdict row of a report, verbatim, minus its name."""
    for line in report.splitlines():
        if line.strip().startswith(name):
            return line.strip()[len(name) :].strip()
    return None


def rewrite(paper, old, new):
    """Give the after text one defect from the before text, and hand the paper
    back so a call can sit inside the invocation it sets up.

    Named as `tests/test_figures.py` and `tests/test_citations.py` name it. The
    anchor must be unique, because every anchor here has a twin inside a
    comment and a comment is exempt from all of these — which is the exemption
    worth pinning, and a silent match on the wrong one would pin nothing.
    """
    path = paper / AFTER
    text = path.read_text()
    assert text.count(old) == 1, "the anchor must be unique: %r" % old
    path.write_text(text.replace(old, new))
    return paper


# --------------------------------------------------------------------------
# the roll-call
# --------------------------------------------------------------------------

# The audit's fourteen defect classes, split by who prevents each. Eight land
# on `render-paper` alone, and the spec's traceability table is the source.
#
# **Eight land here; six of the eight are impossible.** The two counts are not
# the same claim and the table keeps them apart, because collapsing them is how
# a gate comes to be described as a guarantee. `1b` and `1c` land on
# `render-paper` alone and are still expressible: the source can write them and
# the render says so. Six cannot be written at all.
#
# `how` is what this module asserts for that class, and the three values are
# not interchangeable:
#
#   PARSE       the source cannot express it. Exit 3, and nothing ran.
#   GATING      the source can express it and the render says so. A FAIL row.
#   STRUCTURAL  there is nothing to express. The output is a function of the
#               input, so the defect has no surface to arrive on.
PARSE, GATING, STRUCTURAL = "parse", "gating", "structural"

RENDER_PAPER_PREVENTS = {
    "0": (STRUCTURAL, "whole-piece review returned CLEAN"),
    "1a": (PARSE, "inline annotations in improvised bracket syntaxes"),
    "1b": (GATING, "raw untagged holes"),
    "1c": (GATING, "author workflow state written as reader-facing prose"),
    "2a": (PARSE, "two H1 titles"),
    "2b": (PARSE, "broken heading levels, stray H1 mid-section"),
    "2c": (PARSE, "figure-number drift, first-mention violation"),
    "6c": (STRUCTURAL, "orphaned reference entries"),
}

# The rest. Named here so the roll-call is complete: this module asserts what
# `render-paper` does for each, which for most of them is to measure rather
# than to refuse.
OWNED_ELSEWHERE = {
    "3": "rationale leak — `write-paper` constructs, `review-paper` re-derives",
    "4": "paragraphs mirror brief bullets — `write-paper`; measured here, never gated",
    "5": "flat rhythm — a blocking em-dash count, and diagnostics that never gate",
    "6a": "silent content loss at revision — `wayfinder`, plus the supersession diff",
    "6b": "callbacks are meta-narration — `write-paper` makes the container illegal",
    "6d": "the clean manuscript is not regenerable — two files, and the render is `f(source)`",
}


def test_the_roll_call_is_eight_of_fourteen():
    """Eight of the fourteen land on `render-paper` alone. The claim is only
    worth making if the module says which eight, so the table is asserted
    rather than described."""
    assert len(RENDER_PAPER_PREVENTS) == 8
    assert len(RENDER_PAPER_PREVENTS) + len(OWNED_ELSEWHERE) == 14
    assert not set(RENDER_PAPER_PREVENTS) & set(OWNED_ELSEWHERE)


def test_six_of_those_eight_are_impossible_and_two_are_merely_gated():
    """The distinction the ticket's phrase elides, kept explicit.

    `PARSE` and `STRUCTURAL` are impossibility: the source cannot express it,
    or there is nothing to express. `GATING` is a refusal a source can still
    trip, and calling it prevention would claim more than the mechanism does.
    """
    dispositions = [how for how, _ in RENDER_PAPER_PREVENTS.values()]

    assert sum(1 for how in dispositions if how in (PARSE, STRUCTURAL)) == 6
    assert sum(1 for how in dispositions if how == GATING) == 2


# --------------------------------------------------------------------------
# the deltas
# --------------------------------------------------------------------------


class TestTheBeforeTextCarriesWhatItWasMeasuredWith:
    """A delta needs both ends. A fixture that quietly lost its defects would
    make every after-count pass for the wrong reason and nobody would notice,
    which is the same guard `tests/fixtures/residue-calibration` exists for."""

    def test_twenty_one_em_dashes(self, paper):
        assert reader_facing(paper(CASE), BEFORE).count(EM_DASH) == 21

    def test_four_headings_the_drafter_minted(self, paper):
        text = reader_facing(paper(CASE), BEFORE)

        assert len(HEADING.findall(text)) == 4
        assert len(re.findall(r"^# \S", text, re.MULTILINE)) == 1
        assert len(re.findall(r"^## \S", text, re.MULTILINE)) == 3

    def test_sixteen_figure_literals_eleven_of_them_panel_level(self, paper):
        found = FIGURE_LITERAL.findall(reader_facing(paper(CASE), BEFORE))

        assert len(found) == 16
        assert sum(1 for one in found if one[-1].isalpha()) == 11

    def test_eight_bracket_spans_that_are_not_citations(self, paper):
        assert len(bracket_spans(reader_facing(paper(CASE), BEFORE))) == 8

    def test_two_negated_frames(self, paper):
        text = reader_facing(paper(CASE), BEFORE)

        assert len(NEGATED_FRAME.findall(text)) == 2
        for frame in THE_TWO_NEGATED_FRAMES:
            assert frame in " ".join(text.split())

    def test_the_drafting_notes_sit_in_the_reader_facing_stream(self, paper):
        """`1a`'s worst instance: not an annotation but a whole block of
        author-facing text, unmarked, in the file a reader reads."""
        assert "DRAFT NOTES" in reader_facing(paper(CASE), BEFORE)


class TestTheRedraftCarriesNoneOfThem:
    """The other end of every delta, measured the same way on the same cut."""

    def test_no_em_dashes(self, paper):
        assert reader_facing(paper(CASE), AFTER).count(EM_DASH) == 0

    def test_no_headings(self, paper):
        assert HEADING.findall(reader_facing(paper(CASE), AFTER)) == []

    def test_no_figure_literals(self, paper):
        assert FIGURE_LITERAL.findall(reader_facing(paper(CASE), AFTER)) == []

    def test_no_bracket_spans_that_are_not_citations(self, paper):
        assert bracket_spans(reader_facing(paper(CASE), AFTER)) == []

    def test_no_negated_frames(self, paper):
        """`NEGATED_FRAME` is broad — it matches any trailing *"…, not X"* —
        so the zero is backed by the two named constructions as well as by the
        pattern. The pattern alone would be a weak guarantee; the quotes say
        which two shapes left."""
        text = " ".join(reader_facing(paper(CASE), AFTER).split())

        assert NEGATED_FRAME.findall(text) == []
        for frame in THE_TWO_NEGATED_FRAMES:
            assert frame not in text


class TestTheAdversativeCountMovedAsAConsequence:
    """`V3` and `V4` are one finding seen from two directions.

    Removing the twenty-one dashes relation-first, with no find-and-replace
    pass, produced four adversative connectives that the before text did not
    carry. The diagnostic moves as a *consequence* of the gate, which is why
    `V4` refuses to gate it: presenting the two as independent knobs invites
    someone to tune the diagnostic directly.
    """

    def test_the_before_text_carries_none(self, paper):
        assert ADVERSATIVE.findall(reader_facing(paper(CASE), BEFORE)) == []

    def test_the_redraft_carries_four(self, paper):
        found = ADVERSATIVE.findall(reader_facing(paper(CASE), AFTER))

        assert len(found) == 4
        assert sum(1 for one in found if one.lower() == "although") == 1
        assert sum(1 for one in found if one.lower() == "whereas") == 3

    def test_the_render_reports_them_and_gates_on_nothing(self, render):
        result = render(CASE, AFTER, "--check")

        assert row(result.report, "adversative ratio") == "4 of 78 sentences (5%)"


# --------------------------------------------------------------------------
# the before text, handed to the renderer
# --------------------------------------------------------------------------


class TestTheBeforeTextIsNotASourceTheDesignCanExpress:
    """The headline. The old draft is not text the new design gates and finds
    wanting; it is text the new design cannot parse. Eleven of its sixteen
    figure literals, its four headings and its eight bracket spans are each a
    refusal on their own."""

    def test_it_is_refused_at_its_first_heading(self, render):
        result = render(CASE, BEFORE, "--circulate")

        assert result.exit_code == 3
        assert "`# Results and Discussion` is a heading" in result.report

    def test_nothing_ran_so_no_table_printed(self, render):
        """A parse error is not a gate. A table with every row failing would
        claim every check looked and every check objected; none of them
        looked."""
        result = render(CASE, BEFORE, "--check")

        assert "PASS" not in result.report
        assert "FAIL" not in result.report
        assert result.document == ""


# --------------------------------------------------------------------------
# the eight, one at a time
# --------------------------------------------------------------------------


# Each row gives the after text one defect the before text carries, at one
# spot, and names the refusal it earns. The anchor is prose rather than a
# comment on purpose: a comment is exempt from every one of these, which is
# what makes the exemption worth pinning.
IMPOSSIBLE = [
    (
        "1a",
        "{{! best-arm Dice }}",
        "[author to supply: best-arm Dice value]",
        "is not a citation group",
    ),
    (
        "2a",
        "<!-- slot: results-discussion -->",
        "<!-- slot: results-discussion -->\n\n# Results and Discussion",
        "`# Results and Discussion` is a heading",
    ),
    (
        "2b",
        "The second metric closes that gap.",
        "## Registration accuracy\n\nThe second metric closes that gap.",
        "`## Registration accuracy` is a heading",
    ),
    (
        "2c",
        "alternatives (@fig:registration-accuracy)",
        "alternatives (Fig 2)",
        "`Fig 2` is a reference literal",
    ),
    (
        "2c",
        "space (@fig:anchor-overlay)",
        "space (Fig 2c)",
        "`Fig 2c` is a reference literal",
    ),
    (
        "2c",
        "here (@fig:dice-by-arm)",
        "here (b)",
        "`(b)` is a reference literal",
    ),
]


@pytest.mark.parametrize(
    "defect_class, anchor, defect, refusal",
    IMPOSSIBLE,
    ids=["%s %s" % (one[0], one[2][:24]) for one in IMPOSSIBLE],
)
def test_the_parse_tier_classes_cannot_be_written(
    paper, run_in, defect_class, anchor, defect, refusal
):
    """`1a`, `2a`, `2b`, `2c`: the source cannot express it.

    The assertion is the refusal and the exit code, never a count of zero. A
    zero says this text happens not to carry the defect; exit 3 says no text
    can.
    """
    assert RENDER_PAPER_PREVENTS[defect_class][0] == PARSE

    result = run_in(rewrite(paper(CASE), anchor, defect), AFTER, "--circulate")

    assert result.exit_code == 3
    assert refusal in result.report
    assert result.document == ""


class TestTheBareHolesClassIsGatedRatherThanRefused:
    """`1b`: the render is faithful — the hole is right there in the prose —
    but the work is unfinished. So it is a FAIL row and not a parse error, and
    the count is what the assertion reads."""

    HOLE = ("corresponding fall in the residual error.", "residual error of order of XX.")

    def test_the_row_fails_and_names_the_token(self, paper, run_in):
        assert RENDER_PAPER_PREVENTS["1b"][0] == GATING

        result = run_in(rewrite(paper(CASE), *self.HOLE), AFTER, "--check")

        assert row(result.report, "bare holes").startswith("FAIL — 1")
        assert "`XX`" in row(result.report, "bare holes")

    def test_circulate_still_emits_with_the_hole_in_it(self, paper, run_in):
        result = run_in(rewrite(paper(CASE), *self.HOLE), AFTER, "--circulate")

        assert "of order of XX" in result.document

    def test_the_redraft_itself_is_clean(self, render):
        assert row(render(CASE, AFTER, "--check").report, "bare holes") == "PASS"


class TestTheWorkflowPhraseClassIsTheOneSoftenedRow:
    """`1c`: the same defect, one tier softer, because its tells are much
    likelier to be legitimate prose. It warns under `--circulate` and refuses
    the submit question, and that asymmetry is the assertion."""

    PHRASE = (
        "Additional files carry the full per-arm results;",
        "Archiving the panel stacks is a submission-readiness item. "
        "Additional files carry the full per-arm results;",
    )

    def test_it_warns_under_circulate(self, paper, run_in):
        assert RENDER_PAPER_PREVENTS["1c"][0] == GATING

        result = run_in(rewrite(paper(CASE), *self.PHRASE), AFTER, "--circulate")

        assert row(result.report, "workflow phrases").startswith("WARN — 1")

    def test_it_fails_the_submit_question(self, paper, run_in):
        result = run_in(rewrite(paper(CASE), *self.PHRASE), AFTER, "--check")

        assert row(result.report, "workflow phrases").startswith("FAIL — 1")

    def test_the_redraft_itself_is_clean(self, render):
        assert row(render(CASE, AFTER, "--check").report, "workflow phrases") == "PASS"


class TestOrphanedReferenceEntriesHaveNoSurfaceToArriveOn:
    """`6c`: the reference list is `f(cited keys)`, so an over-provisioned
    library is the normal state of one and an orphan is not a thing that can
    exist in the output. There is no row to assert, which is the point: the
    assertion is on the emitted document."""

    ORPHAN = (
        "\n@article{uncited2020,\n"
        "  author = {Nobody, A.},\n"
        "  title = {Never referenced by this document},\n"
        "  year = {2020}\n"
        "}\n"
    )

    def over_provisioned(self, paper):
        """The fixture with one more entry in its library than the document
        cites."""
        home = paper(CASE)
        library = home / "references.bib"
        library.write_text(library.read_text() + self.ORPHAN)
        return home

    def test_an_uncited_entry_never_reaches_the_reference_list(self, paper, run_in):
        assert RENDER_PAPER_PREVENTS["6c"][0] == STRUCTURAL

        result = run_in(self.over_provisioned(paper), AFTER, "--circulate")

        assert "Never referenced by this document" not in result.document
        assert result.document.count("\n1. ") == 1

    def test_and_it_raises_nothing(self, paper, run_in):
        """An over-provisioned library is legal. The check has no second half
        and must not grow one."""
        result = run_in(self.over_provisioned(paper), AFTER, "--check")

        assert row(result.report, "citation → bib entry") == "PASS"


class TestThereIsNoCleanVerdictToReturn:
    """`0`: the class that reframed the audit. A whole-piece review returned
    `CLEAN` over ninety-eight em dashes because one word had to carry both
    checked-and-fine and never-checked. The table prints one row per check, an
    out-of-scope check prints that it was out of scope, and no word in the
    output means finished."""

    def test_a_section_render_says_which_checks_never_looked(self, render):
        assert RENDER_PAPER_PREVENTS["0"][0] == STRUCTURAL

        result = render(CASE, AFTER, "--check", "--section", "results-discussion")

        skipped = [
            line.strip()
            for line in result.report.splitlines()
            if "SKIPPED — OUT OF SCOPE AT THIS GRANULARITY" in line
        ]
        assert len(skipped) == 8
        assert "8 out of scope" in result.report

    def test_no_row_and_no_tally_says_clean(self, render):
        result = render(CASE, AFTER, "--check")

        assert "CLEAN" not in result.report

    def test_a_gate_with_no_fails_is_still_not_a_claim_of_finished(self, render):
        result = render(CASE, AFTER, "--check")

        assert "→ NOT a claim that this document is finished" in result.report


# --------------------------------------------------------------------------
# the other six, and what `render-paper` does for them
# --------------------------------------------------------------------------


class TestTheClassesAnotherUnitOwns:
    """Six of the fourteen are not prevented here, and the regression says so
    rather than leaving the silence to be read as coverage."""

    def test_rationale_leak_leaves_its_objections_in_the_channel(self, render):
        """`3`: `write-paper` owns the construction — the objection is named in
        a comment rather than argued at the reader — and every comment is
        stripped as a class, so what the render can assert is the strip."""
        result = render(CASE, AFTER, "--circulate")
        source = (result.paper / AFTER).read_text()

        assert source.count("<!-- obj:") == 3
        assert "obj:" not in result.document

    def test_the_brief_is_measured_against_the_prose_and_never_gated(self, render):
        """`4`: the overlap instrument is a reported row. The redraft's brief
        is 172 words of argument the prose does not transcribe, so the
        measurement is zero — and a zero here moves no exit code either way."""
        result = render(CASE, AFTER, "--check")

        assert row(result.report, "brief-to-prose overlap").startswith("0 flagged")

    def test_the_rhythm_diagnostics_carry_numbers_and_never_verdicts(self, render):
        """`5`: `V2`'s em-dash count blocks at the seam; `V4`'s diagnostics
        report and gate on nothing. Both are in the reported tier, and neither
        reaches the exit code."""
        result = render(CASE, AFTER, "--check")

        assert row(result.report, "em dashes (threshold 0)") == "PASS — 0"
        for name in ("subject openings", "sentence length", "adversative ratio"):
            assert not row(result.report, name).startswith(("PASS", "FAIL", "WARN"))
        assert "6 reported" in result.report

    def test_the_supersession_diff_reports_and_never_gates(self, render):
        """`6a`: the row landed with its own ticket, and it stays owned
        elsewhere — `wayfinder` makes `revise` a type with a mechanical
        discriminator, and the row is the drop-guard beside it, **a finding
        rather than a gate.**

        It is reconstructed across two drafts from the *history*, which a
        fixture pair does not have, and it runs over one unit at a time. So
        what this pair asserts is what holds with no ref to hand: the row is
        printed at both granularities — a row is never printed without a check
        behind it — and it prints no `FAIL` at either. That it moves no exit
        code is pinned where the ref exists, in `test_supersession.py`, over a
        revision that legitimately deletes most of a unit.
        """
        assert "6a" in OWNED_ELSEWHERE

        document = render(CASE, AFTER, "--check")
        section = render(CASE, AFTER, "--check", "--section", "results-discussion")

        assert row(document.report, "supersession diff") == (
            "SKIPPED — OUT OF SCOPE AT THIS GRANULARITY"
        )
        assert "not a supersession" in row(section.report, "supersession diff")
        assert "FAIL" not in row(document.report, "supersession diff")
        assert "FAIL" not in row(section.report, "supersession diff")

    def test_no_sentence_names_a_container_to_close_a_debt(self, paper):
        """`6b`: `S3` makes the container the illegal object. Naming a
        proposition is legal and a procedural cross-reference is legal; the
        banned move is meta-narration that tells the reader where they are.

        Not mechanical, so this is a measurement of the shape the audit
        recorded, and not a lint."""
        text = reader_facing(paper(CASE), AFTER)

        assert not re.search(r"\bAs (?:described|discussed|noted) (?:in|above)\b", text)
        assert not re.search(r"\b(?:Results|Methods|Background) (?:reports|reported)\b", text)

    def test_the_render_is_a_function_of_the_source(self, render):
        """`6d`: the clean manuscript was not regenerable because judgement
        fixes went into the generator. Two renders of one unedited source are
        byte-identical, and the output says not to edit it."""
        first = render(CASE, AFTER, "--circulate")
        second = render(CASE, AFTER, "--circulate")

        assert first.document == second.document
        assert first.document.startswith(
            "---\ngenerated-by: render-paper\n"
            "do-not-edit: this file is output; edit the source it was rendered from\n---\n"
        )


# --------------------------------------------------------------------------
# and the redraft itself
# --------------------------------------------------------------------------


class TestTheRedraftRenders:
    """The end-to-end statement. Not that the after text avoids the defects —
    that is the delta above — but that the whole renderer runs over it and
    produces the document the worked example says it produces."""

    def test_the_headings_come_from_the_skeleton(self, render):
        result = render(CASE, AFTER, "--circulate")

        assert "## Results and discussion" in result.document
        assert "## Limitations and future work" in result.document

    def test_the_sub_heading_budget_was_zero_and_stayed_zero(self, render):
        """The strictest available test of the through-line: the before text
        carried three H2 sub-headings inside one section, and the redraft
        carries none, with nothing added to compensate."""
        result = render(CASE, AFTER, "--circulate")

        body = result.document.split("## Results and discussion", 1)[1]
        body = body.split("## Limitations and future work", 1)[0]
        assert HEADING.findall(body) == []

    def test_no_author_facing_text_reaches_the_reader(self, render):
        """`A1` strips every comment as a class, so the rung note, the three
        objection notes and the reasoning comment cannot arrive by any path."""
        result = render(CASE, AFTER, "--circulate")

        assert "<!--" not in result.document
        assert "RUNG R5" not in result.document
        assert "unverified" not in result.document

    def test_the_split_roster_numbers_itself(self, render):
        """The figure split cost one roster line and zero prose edits, and
        first-mention order over the whole document reproduces by construction
        the numbering the live manuscript reached by hand."""
        result = render(CASE, AFTER, "--circulate")

        assert "(fig. 1)" in result.document  # protocol-schematic
        assert "(fig. 2)" in result.document  # pipeline
        assert "(fig. 3)" in result.document  # phenotyping
        assert "(fig. 4)" in result.document  # registration-accuracy
        assert "(fig. 5)" in result.document  # proof-of-concept

    def test_panels_letter_from_their_legend_and_not_from_first_mention(self, render):
        result = render(CASE, AFTER, "--circulate")

        assert "(fig. 4 (a))" in result.document
        assert "(fig. 4 (b))" in result.document
        assert "(fig. 5 (a))" in result.document
        assert "(fig. 5 (b))" in result.document

    def test_every_gap_comes_out_as_a_conspicuous_token(self, render):
        """`C3`: silent stripping was ruled out because each of these sits
        under a committed directional word. Strip `⟦HOLE: best-arm Dice⟧` and
        the sentence is ungrammatical; drop the clause and an unsupported
        assertion goes out and the author never learns."""
        result = render(CASE, AFTER, "--circulate")

        assert result.document.count("⟦HOLE: ") == 6
        flowed = " ".join(result.document.split())
        assert "raised Dice to ⟦HOLE: best-arm Dice⟧ from ⟦HOLE: rigid-only Dice⟧" in flowed

    def test_the_manifest_is_the_seven_things_the_author_owes(self, render):
        """Not eleven. The rung note, the three objection notes and the
        reasoning comment are ordinary comments: stripped, and tracked
        nowhere."""
        result = render(CASE, AFTER, "--check")

        assert "manifest — 7 open annotations, 7 carrying the gate bit" in result.report
        assert result.report.count("!  HOLE") == 6
        assert result.report.count("!  SILENT") == 1

    def test_a_directional_word_resting_on_an_open_hole_says_so(self, render):
        """`F5`'s regression, closed: the direction was committed before the
        value existed, so the manifest line names the direction and filling the
        value forces a confrontation with the word."""
        result = render(CASE, AFTER, "--check")

        assert "direction: `improved` is committed before this value exists" in result.report
        assert "direction: `higher` is committed before this value exists" in result.report

    def test_circulate_emits_and_submit_refuses(self, render):
        """The gate bit is the whole difference. An open gap is the normal
        state of a live paper, and the same source that circulates freely
        cannot be submitted."""
        circulated = render(CASE, AFTER, "--circulate")
        submitted = render(CASE, AFTER, "--submit")

        assert circulated.exit_code == 1 and circulated.document != ""
        assert submitted.exit_code == 1 and submitted.document == ""
        assert "--submit refused: 1 gating check failed" in submitted.report

    def test_the_section_render_is_the_drafting_seam(self, render):
        """`C7` makes the per-section render the `draft` checkpoint, and the
        em-dash count is the reported row that *measures* at section
        granularity, because a seam is one section. The rhythm diagnostics stay
        whole-document; the supersession diff is the other way round, and runs
        here and nowhere else."""
        result = render(CASE, AFTER, "--check", "--section", "results-discussion")

        assert row(result.report, "em dashes (threshold 0)") == "PASS — 0"
        assert row(result.report, "adversative ratio") == (
            "SKIPPED — OUT OF SCOPE AT THIS GRANULARITY"
        )
