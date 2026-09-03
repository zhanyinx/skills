"""Figures and panels: one namespace, the roster, legend declarations, and
lettering.

A drafting session names the thing it means; the render assigns the number or
the letter. A figure and a panel are **one flat namespace and one token
class** — parentage is carried by containment, never by syntax — so a panel is
referenced exactly as a figure is, and a panel name describes content rather
than position.

The two numbering rules differ for a physical reason and are not unified: a
figure *number* appears only in rendered text, but a panel *letter* appears in
the text **and in the artwork**, and a render can renumber prose but cannot
repaint a figure. So figures resolve by **first-mention order** and panels by
**the legend's declaration order**.

These tests use the CLI as their only seam, like every other test here.
"""

import re

import pytest

CASE = "figures"

# The roster half of the hard-error row `#2` opened for the slot half. One row
# for both, because an anchor naming a slot the skeleton does not carry and a
# reference naming an object the roster does not carry are the same defect:
# the emitted document is not the document the source describes.
ROW = "slot / roster integrity"


def source(paper):
    return paper / "MANUSCRIPT.working.md"


def rewrite(paper, old, new):
    """Give a fixture paper one defect, by substitution in its source."""
    path = source(paper)
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new))


def flat(text):
    """`text` with every run of whitespace collapsed, so an assertion reads as
    prose rather than depending on where the source wrapped its lines."""
    return re.sub(r"\s+", " ", text)


def row(report, name):
    """One verdict row of a report, verbatim, minus its name."""
    for line in report.splitlines():
        if line.strip().startswith(name):
            return line.strip()[len(name):].strip()
    return None


# --------------------------------------------------------------------------
# numbering
# --------------------------------------------------------------------------


def test_a_figure_resolves_by_first_mention_order(render):
    """The roster lists `pipeline` first and carries no order of its own. The
    document mentions a panel of `registration-accuracy` first, so that is
    figure 1."""
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 0, result.report
    assert "the drift left open (fig. 1)" in flat(result.document)


def test_a_panel_letters_by_the_legends_declaration_order(render):
    """The decisive case, and the reason the two rules are not unified.

    `dice-by-arm` is mentioned **first** in the document and declared
    **second** in the legend; `dapi-overlay` is mentioned last and declared
    first. Under first-mention lettering the two would swap letters, and the
    artwork would be wrong with no edit to any figure.
    """
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 0, result.report
    assert "the measurement that settles it (fig. 1 (b))" in flat(result.document)
    assert "which every round shares (fig. 1 (a))" in flat(result.document)


# --------------------------------------------------------------------------
# the roster
# --------------------------------------------------------------------------


def test_a_figure_name_not_in_the_roster_is_a_hard_error(paper, run_in):
    """A token pointing at nothing. The emitted document would carry a
    reference to an object the document does not have, so neither mode
    emits."""
    live = paper(CASE)
    rewrite(live, "@fig:dice-by-arm", "@fig:nowhere")

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 2
    assert row(result.report, ROW).startswith("FAIL")
    assert "`@fig:nowhere`" in result.report
    assert result.document == ""


def test_the_hard_error_names_the_file_and_the_line(paper, run_in):
    live = paper(CASE)
    rewrite(live, "@fig:dice-by-arm", "@fig:nowhere")

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert re.search(r"MANUSCRIPT\.working\.md:\d+ `@fig:nowhere`", result.report)


def test_a_roster_name_never_referenced_is_a_hard_error(paper, run_in):
    """The symmetric half, and the asymmetry with the bibliography is the
    point: a roster is a manifest of **this document's** objects, so an object
    nothing points at is damage. A library is over-provisioned by nature, which
    is why the citation check has no such half."""
    live = paper(CASE)
    skeleton = live / "skeleton.md"
    skeleton.write_text(
        skeleton.read_text()
        + "| figure | discarded-arm | legends/discarded-arm.md |\n"
    )

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 2
    assert row(result.report, ROW).startswith("FAIL")
    assert "`discarded-arm`" in result.report


def test_a_figure_referenced_only_through_its_panels_is_referenced(render):
    """Parentage is carried by containment, so a reference to a panel *is* a
    reference to the figure that contains it. `pipeline` is named nowhere in
    the prose; `@fig:stage-graph`, which its legend declares, is."""
    result = render(CASE, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 0, result.report
    assert row(result.report, ROW) == "PASS"


def test_a_declared_panel_no_prose_references_is_not_an_error(render):
    """`seam-crop` is declared in the pipeline legend and referenced nowhere.
    The roster carries no panel rows, so there is no roster name to be
    unreferenced — and a figure may legitimately have a panel the prose never
    calls out on its own."""
    result = render(CASE, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 0, result.report


def test_the_row_is_whole_document_only(render):
    """*A roster name never referenced* is undecidable from one unit's source,
    because the reference may live in any other unit."""
    result = render(CASE, "MANUSCRIPT.working.md", "--check", "--section", "results")

    assert row(result.report, ROW) == "SKIPPED — OUT OF SCOPE AT THIS GRANULARITY"


# --------------------------------------------------------------------------
# the parse errors
# --------------------------------------------------------------------------


LITERALS = [
    "(a)",
    "(c-d)",
    "(c–d)",
    "(a, b)",
    "Fig 2",
    "Fig. 4b",
    "Figure 3",
    "figs 1",
]


@pytest.mark.parametrize("literal", LITERALS, ids=range(len(LITERALS)))
def test_a_reference_literal_in_prose_is_a_parse_error(paper, run_in, literal):
    """Three rules, one principle: **the source cannot express a stale
    identifier.** A number or a letter typed into prose is a thing the render
    can neither check nor correct, so it has no legal spelling at all."""
    live = paper(CASE)
    rewrite(live, "(@fig:dice-by-arm)", literal)

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 3
    assert "reference literal" in result.report


@pytest.mark.parametrize("name", ["panel-b", "panel-B", "b"])
def test_a_positional_name_in_prose_is_a_parse_error(paper, run_in, name):
    """`@fig:panel-b` is a panel letter wearing a name: the same stale
    identifier, spelled inside the namespace that exists to remove it.

    **In either case**, because the predicate's three call sites do not agree
    on case: a roster name and a panel declaration are lowercase by their own
    grammar, and a reference is not. Checked here at `--section`, where the
    roster row that would otherwise have caught the name is out of scope — so
    only the refusal can.
    """
    live = paper(CASE)
    rewrite(live, "@fig:dice-by-arm", "@fig:%s" % name)

    result = run_in(live, "MANUSCRIPT.working.md", "--check", "--section", "introduction")

    assert result.exit_code == 3
    assert "positional name" in result.report


def test_a_table_literal_is_not_refused_and_the_roster_half_catches_it(paper, run_in):
    """The refusal covers the **figure** spellings only, and the omission is
    deliberate: `table` and its relatives are ordinary nouns that take a
    measurement, so a refusal over them fires on prose that references nothing.

    The defect is not lost with them. A table referred to by literal is a
    roster name referenced nowhere, which is a hard error in both modes — one
    row later and less precisely, which is the price of a pattern with no false
    positives.
    """
    live = paper(CASE)
    rewrite(live, "(@fig:antibody-panel)", "Table 1")

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 2
    assert "`antibody-panel` is in the roster and referenced nowhere" in result.report


def test_an_ordinary_noun_before_a_numeral_is_not_a_reference_literal(paper, run_in):
    """What the omission buys: *a table 1 mm thick* references nothing, and a
    refusal that fired on it would be the noisy gate this design is built
    against."""
    live = paper(CASE)
    rewrite(live, "one round per marker pair", "on a table 1 mm thick")

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 0, result.report


def test_a_parse_error_means_nothing_ran(paper, run_in):
    """No table, because none of the checks looked. A table with every row
    failing would claim they all did."""
    live = paper(CASE)
    rewrite(live, "(@fig:dice-by-arm)", "(c–d)")

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 3
    assert result.document == ""
    assert "PASS" not in result.report


def test_the_refusal_names_the_file_and_the_line(paper, run_in):
    live = paper(CASE)
    rewrite(live, "(@fig:dice-by-arm)", "(c–d)")

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert re.search(r"MANUSCRIPT\.working\.md:\d+", result.report)


def test_a_parenthesised_letter_inside_a_comment_is_not_refused(paper, run_in):
    """Exempt **by construction**, not by a marker string: a comment never
    reaches the reader, so nothing in one can be a stale reader-facing
    identifier."""
    live = paper(CASE)
    rewrite(live, "(@fig:dice-by-arm)", "(@fig:dice-by-arm)\n<!-- panels (a) and (b) -->")

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 0, result.report


def test_a_parenthesised_letter_inside_a_brace_is_not_refused(paper, run_in):
    """The author-facing channel is not reader-facing prose either."""
    live = paper(CASE)
    rewrite(live, "(@fig:dice-by-arm)", "{{ ! which panels (a) and (b) end up showing }}")

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 1, result.report
    assert row(result.report, "reference literals") == "PASS"


def test_a_reference_literal_inside_a_fence_is_not_refused(paper, run_in):
    """Inside a fence nothing is parsed at all, here as everywhere else: a
    source showing the syntax is showing it, not using it."""
    live = paper(CASE)
    rewrite(
        live,
        "(@fig:dice-by-arm)",
        "(@fig:dice-by-arm)\n\n```\nnever write Fig 2c, or (c–d)\n```",
    )

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 0, result.report


def test_the_parse_row_prints_pass_whenever_a_table_prints(render):
    result = render(CASE, "MANUSCRIPT.working.md", "--check")

    assert row(result.report, "reference literals") == "PASS"


def test_the_refusal_still_fires_at_section_granularity(paper, run_in):
    """A refusal is not a check, so it has no granularity to be out of scope
    at."""
    live = paper(CASE)
    rewrite(live, "(@fig:dice-by-arm)", "(c–d)")

    result = run_in(live, "MANUSCRIPT.working.md", "--check", "--section", "introduction")

    assert result.exit_code == 3


def test_a_positional_name_in_the_roster_is_a_parse_error(paper, run_in):
    live = paper(CASE)
    skeleton = live / "skeleton.md"
    skeleton.write_text(
        skeleton.read_text().replace("| figure | pipeline |", "| figure | pipeline-a |")
    )

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 3
    assert "describes its content" in result.report


def test_a_positional_name_in_a_legend_is_a_parse_error(paper, run_in):
    """One predicate, three call sites. A name that says where it sits is
    refused where it is declared as well as where it is used."""
    live = paper(CASE)
    legend = live / "legends" / "pipeline.md"
    legend.write_text(legend.read_text().replace("@fig:seam-crop", "@fig:panel-b"))

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 3
    assert "describes its content" in result.report


# --------------------------------------------------------------------------
# granularity
# --------------------------------------------------------------------------


def test_at_section_granularity_every_token_is_left_unresolved_and_visible(render):
    """Nothing is resolved and **no placeholder form is invented**: both
    numbering rules read the whole document — first mention is document-wide,
    and a legend is a whole-document input — so a section render that guessed
    would be guessing."""
    result = render(
        CASE, "MANUSCRIPT.working.md", "--circulate", "--section", "introduction"
    )

    assert result.exit_code == 0, result.report
    assert "(@fig:dice-by-arm)" in result.document
    assert "fig." not in result.document


def test_a_panel_token_survives_a_section_render_byte_exact(render):
    """The token comes out as it went in, so the section render is a readable
    copy of the source rather than a second numbering scheme."""
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate", "--section", "methods")

    assert result.exit_code == 0, result.report
    assert "(@fig:dapi-overlay)" in result.document
    assert "(@fig:stage-graph)" in result.document


def test_the_whole_document_is_verbatim(render, golden):
    """Every reference resolved, in one document: two figures numbered by first
    mention, four panels lettered by declaration, a table and a supplementary
    file each numbering in their own sequence."""
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")

    assert result.document == golden("figures-circulate.md")


# --------------------------------------------------------------------------
# the calibration: the parenthesised-letter rule
# --------------------------------------------------------------------------
#
# `K3` kills `Fig 2` but not `(c–d)`, which is syntactically clean prose and a
# perfectly stale-able identifier — and it sits in the artifact a figure split
# re-letters *first*. Measured over the calibration corpus, of the
# parenthesised-letter occurrences in reader-facing prose, **21 of 21 were
# panel references or declaration markers and zero were enumerators**, while
# all **37** legitimate letter-enumerator uses sat inside comments, which the
# refusal exempts by construction.
#
# The `panel-calibration` fixture reproduces that distribution at its measured
# shape: the 21 in the form the design gives them, and the 37 where the corpus
# had them.


CALIBRATION = "panel-calibration"

ENUMERATOR = re.compile(r"\(\s*[A-Za-z](?:\s*[-–—,;]\s*[A-Za-z])*\s*\)")
PANEL_REFERENCE = re.compile(r"\(@fig:[a-z-]+\)")


def outside_comments(text):
    """`text` with every comment blanked to same-length whitespace, which is
    exactly what the refusal reads."""
    return re.sub(
        r"<!--.*?-->", lambda match: " " * len(match.group(0)), text, flags=re.DOTALL
    )


def test_the_corpus_distribution_renders_clean(render):
    """21 panel references, 37 enumerators in comments, and nothing in the
    source the render cannot parse.

    All 21 letters appear in the **output**, which is the whole asymmetry: the
    render is the only place a panel letter may be spelled, and the source is
    the only place it may not.
    """
    result = render(CALIBRATION, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 0, result.report
    assert len(re.findall(r"fig\. \d+ \([a-z]+\)", result.document)) == 21


def test_the_corpus_holds_21_reader_facing_panel_references_and_no_literal(render):
    """The distribution the refusal was measured against."""
    live = render(CALIBRATION, "MANUSCRIPT.working.md", "--check")
    reader_facing = outside_comments((live.paper / "MANUSCRIPT.working.md").read_text())

    assert len(PANEL_REFERENCE.findall(reader_facing)) == 21
    assert ENUMERATOR.findall(reader_facing) == []


@pytest.mark.parametrize("index", range(21))
def test_the_rule_fires_on_each_of_the_21_occurrences(paper, run_in, index):
    """21 of 21. Each panel reference is put back as the literal it replaced,
    one at a time, and each one is refused at its own line."""
    live = paper(CALIBRATION)
    path = live / "MANUSCRIPT.working.md"
    text = path.read_text()
    spans = [match.span() for match in PANEL_REFERENCE.finditer(outside_comments(text))]
    assert len(spans) == 21
    start, end = spans[index]
    path.write_text(text[:start] + "(c–d)" + text[end:])

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 3
    assert "reference literal" in result.report
    assert ":%d" % (text[:start].count("\n") + 1) in result.report


def test_the_37_enumerator_uses_inside_comments_are_exempt(render):
    """Exempt **by construction**, which is why the exemption needs no marker
    string and cannot be got wrong: a comment never reaches a reader, so
    nothing in one can be a stale reader-facing identifier."""
    live = render(CALIBRATION, "MANUSCRIPT.working.md", "--circulate")
    text = (live.paper / "MANUSCRIPT.working.md").read_text()
    inside = len(ENUMERATOR.findall(text)) - len(
        ENUMERATOR.findall(outside_comments(text))
    )

    assert inside == 37
    assert live.exit_code == 0, live.report


def test_a_legitimate_enumerator_in_prose_is_currently_rejected(paper, run_in):
    """The refusal's whole cost, stated rather than discovered: a genuine
    letter enumerator cannot be written in reader-facing prose. It is
    affordable because the corpus contains **zero** of them outside comments,
    and where an author wants one, a comment or a list of full clauses carries
    it."""
    live = paper(CALIBRATION)
    rewrite(
        live,
        "(@fig:dice-by-arm).",
        "at three settings: (a) high accuracy, (b) low accuracy, (c) rigid only.",
    )

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 3
    assert "reference literal" in result.report


def test_the_cost_is_not_a_configuration_surface(paper, run_in):
    """**A refusal cannot be configured per effort** — a configurable refusal
    pattern is the override these rules exist to prevent, wearing a config
    file. So the cost is carried as documented cost, and the CLI offers no way
    to switch the rule off."""
    result = run_in(paper(CALIBRATION), "--help")

    assert result.exit_code == 0
    for word in ("literal", "letter", "panel", "allow", "ignore", "disable"):
        assert word not in result.document.lower(), word


# --------------------------------------------------------------------------
# the calibration: the figure split
# --------------------------------------------------------------------------
#
# Confirmed on a real event. A planning roster's Fig 2 covered the pipeline and
# the accuracy of the registration stage inside it, and during drafting it
# split in two. Under names the split is **a one-line roster edit**:
# document-wide first-mention order reproduces the live post-split numbering
# **exactly, at zero reference edits**, and the two registration panels move to
# the new legend and become `(a)`, `(b)` **by position, also at zero prose
# edits**.
#
# The `figure-split` fixture carries both states — its `split/` directory holds
# the post-split skeleton and the two legends that replace one — and the same
# source is rendered from each.


SPLIT = "figure-split"


def apply_split(live):
    """The whole cost of the split: the roster's one line becomes two, and one
    legend becomes two. No prose is touched."""
    split = live / "split"
    (live / "skeleton.md").write_text((split / "skeleton.md").read_text())
    for legend in sorted((split / "legends").glob("*.md")):
        (live / "legends" / legend.name).write_text(legend.read_text())
    (live / "legends" / "pipeline-and-registration.md").unlink()


def resolved(document):
    """Every resolved reference in a document, in document order."""
    return re.findall(r"(?:fig|tbl|suppl)\. \d+(?: \([a-z]+\))?", document)


def roster_rows(live):
    return [
        line
        for line in (live / "skeleton.md").read_text().splitlines()
        if line.startswith("| figure ")
    ]


def test_before_the_split_one_figure_carries_all_four_panels(render):
    result = render(SPLIT, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 0, result.report
    assert resolved(result.document) == [
        "fig. 1",
        "fig. 2 (a)",
        "fig. 2 (b)",
        "fig. 2 (c)",
        "fig. 2 (d)",
        "fig. 3",
        "fig. 4",
    ]


def test_the_split_costs_zero_reference_edits(paper, run_in):
    """The load-bearing property. Renumbering that manuscript by hand was never
    done because it would have changed most of its numbers; here the source is
    byte-identical across the split."""
    live = paper(SPLIT)
    before = source(live).read_text()

    apply_split(live)
    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 0, result.report
    assert source(live).read_text() == before


def test_first_mention_order_reproduces_the_post_split_numbering(paper, run_in):
    """`pipeline` keeps 2 because its first-mentioned panel comes first;
    `registration-accuracy` takes 3; and the two downstream figures shift to 4
    and 5 with nothing edited but the roster."""
    live = paper(SPLIT)
    apply_split(live)

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 0, result.report
    assert resolved(result.document) == [
        "fig. 1",
        "fig. 2 (a)",
        "fig. 2 (b)",
        "fig. 3 (a)",
        "fig. 3 (b)",
        "fig. 4",
        "fig. 5",
    ]


def test_the_two_moved_panels_re_letter_by_position(paper, run_in):
    """`(c)`, `(d)` become `(a)`, `(b)` because they are first and second in
    the legend they moved to — which is the whole reason panels letter by
    declaration order and not by first mention: the letters follow the artwork,
    and the artwork is what the legend declares."""
    live = paper(SPLIT)
    before = run_in(live, "MANUSCRIPT.working.md", "--circulate")
    apply_split(live)

    after = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert "registration is scored on (fig. 2 (c))" in flat(before.document)
    assert "both baselines (fig. 2 (d))" in flat(before.document)
    assert "registration is scored on (fig. 3 (a))" in flat(after.document)
    assert "both baselines (fig. 3 (b))" in flat(after.document)


def test_the_split_is_one_roster_line(paper, run_in):
    """One row becomes two. That is the entire edit the author makes."""
    live = paper(SPLIT)
    before = roster_rows(live)

    apply_split(live)

    assert len(roster_rows(live)) == len(before) + 1


def test_the_literal_would_have_changed_meaning_rather_than_dangling(paper, run_in):
    """The defect neither the audit nor a review found: after the split, the
    frozen draft's `Fig 2c` **did not dangle — it changed meaning.**

    Post-split, figure 2's third panel is the stage timing, where pre-split it
    was the DAPI overlay. A literal would still have resolved, to the wrong
    object, silently. A name follows the object instead — which is why the
    literal is a parse error and not a checked value.
    """
    live = paper(SPLIT)
    apply_split(live)
    rewrite(
        live,
        "against a common anchor (@fig:stage-graph).",
        "against a common anchor (@fig:stage-graph), and each stage's wall-clock is "
        "reported with it (@fig:stage-timing).",
    )

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 0, result.report
    assert "wall-clock is reported with it (fig. 2 (c))" in flat(result.document)


# --------------------------------------------------------------------------
# one reference surface, two classes
# --------------------------------------------------------------------------


def test_a_mixed_group_resolves_per_key_not_per_token(paper, run_in):
    """`@`-prefixed identifiers are one surface, and a single group may carry
    either class. Each key takes its own rendered form: leaving the token alone
    would drop a real citation out of the reference list while the gate went on
    demanding a bibliography entry for it."""
    live = paper(CASE)
    (live / "references.bib").write_text(
        "@article{smith2020,\n"
        "  author = {Smith, A.},\n"
        "  title = {Registration across rounds},\n"
        "  journal = {Journal of Imaging},\n"
        "  year = {2020},\n"
        "}\n"
    )
    rewrite(live, "(@fig:dapi-overlay)", "[@smith2020; @fig:dapi-overlay]")

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 0, result.report
    assert "[1; fig. 1 (a)]" in result.document


def test_a_figure_name_is_never_asked_of_the_bibliography(render):
    """The `figures` fixture cites nothing and has no library, and every
    `@fig:` name in it resolves. A paper with figures and no citations needs no
    `references.bib` at all."""
    result = render(CASE, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 0, result.report
    assert row(result.report, "citation → bib entry") == "PASS"


# --------------------------------------------------------------------------
# the legend declaration grammar
# --------------------------------------------------------------------------


def legend(live, name="pipeline"):
    return live / "legends" / ("%s.md" % name)


def test_a_column_zero_line_that_is_not_a_declaration_is_a_parse_error(paper, run_in):
    """`## Panels` holds declarations and nothing else, so a paragraph cannot
    drift into the block and shift the letters."""
    live = paper(CASE)
    path = legend(live)
    path.write_text(path.read_text() + "\nAnd the timing is reported separately.\n")

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 3
    assert "is not a panel declaration" in result.report


def test_an_indented_continuation_is_part_of_the_entry_above(paper, run_in):
    """A description is free text and wraps over as many lines as it needs."""
    live = paper(CASE)
    path = legend(live)
    path.write_text(path.read_text() + "                      Scale bar required.\n")

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 0, result.report


def test_a_declaration_without_the_prefix_is_a_parse_error(paper, run_in):
    """One namespace, one token class — a declaration is spelled exactly as a
    reference is."""
    live = paper(CASE)
    path = legend(live)
    path.write_text(path.read_text().replace("@fig:seam-crop", "@seam-crop"))

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 3
    assert "is not a panel declaration" in result.report


def test_a_panel_declared_twice_in_one_legend_is_a_parse_error(paper, run_in):
    """One entry per panel, because the entry's position *is* the letter."""
    live = paper(CASE)
    path = legend(live)
    path.write_text(path.read_text().replace("@fig:seam-crop", "@fig:stage-graph"))

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 3
    assert "declared twice" in result.report


def test_one_name_in_two_legends_is_a_parse_error(paper, run_in):
    """One flat namespace: a name belongs to exactly one object, so a panel
    cannot be declared by two figures."""
    live = paper(CASE)
    path = legend(live)
    path.write_text(path.read_text().replace("@fig:seam-crop", "@fig:dapi-overlay"))

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 3
    assert "one flat namespace" in result.report


def test_a_panel_colliding_with_a_roster_name_is_a_parse_error(paper, run_in):
    live = paper(CASE)
    path = legend(live)
    path.write_text(path.read_text().replace("@fig:seam-crop", "@fig:registration-accuracy"))

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 3
    assert "one flat namespace" in result.report


def test_a_legend_may_declare_more_panels_than_the_alphabet_holds(paper, run_in):
    """The 27th panel letters `aa`. A figure with 27 panels is not a real
    figure, but a defined answer beats an exception thrown from inside the
    resolver."""
    live = paper(CASE)
    path = legend(live)
    declared = "\n".join(
        "@fig:stage-%02d      stage %d of the pipeline." % (number, number)
        for number in range(1, 28)
    )
    path.write_text("# Legend — pipeline\n\n## Panels\n\n%s\n" % declared)
    rewrite(live, "@fig:stage-graph", "@fig:stage-27")

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 0, result.report
    assert "committed configuration (fig. 2 (aa))" in flat(result.document)


def test_a_legend_file_that_does_not_exist_yet_is_legal(render):
    """`power-analysis` has a roster row and no file. Legends are drafted after
    the body sections that reference their panels, so a missing legend declares
    no panels rather than refusing the render."""
    result = render(CASE, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 0, result.report


def test_a_legend_with_no_panels_block_is_legal(render):
    """`antibody-panel` is a table with one picture and nothing to letter."""
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")

    assert "schedule (tbl. 1)" in flat(result.document)


def test_a_roster_row_with_no_legend_path_is_a_parse_error(paper, run_in):
    """The row names where the block will be. Leaving it empty would make *no
    panels ever* and *no panels yet* the same state."""
    live = paper(CASE)
    skeleton = live / "skeleton.md"
    skeleton.write_text(
        skeleton.read_text().replace(
            "| figure | pipeline | legends/pipeline.md |", "| figure | pipeline | |"
        )
    )

    result = run_in(live, "MANUSCRIPT.working.md", "--check")

    assert result.exit_code == 3
    assert "has no legend path" in result.report
