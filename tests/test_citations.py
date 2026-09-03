"""The citation surface: the grammar, the bracket refusal, the bibliography,
and first-mention numbering.

A drafting session references a source by **stable key** and never by number,
so a number it writes cannot be wrong-but-valid and invisible to every check.
The render turns keys into numbers by first-mention order in the assembled
document and builds the reference list from the cited keys — which makes an
orphaned bibliography entry impossible rather than checked.

These tests use the CLI as their only seam, like every other test here.
"""

import re

import pytest

CASE = "citations"
CALIBRATION = "calibration"

# The nine syntaxes the calibration corpus improvised for its 30 inline
# annotations, generically. Each one is reader-facing prose the render cannot
# parse, and each was invisible to six review passes.
IMPROVISED = [
    "[author to supply: the registration arm]",
    "[author to supply]",
    "[EXPERIMENTALIST TO SUPPLY: the marker-to-round ordering]",
    "[author to confirm: how the signature was computed]",
    "[Author-supplied: the approving ethics committee]",
    "[Author-supplied.]",
    '[Author to finalise — e.g. "a cross-panel pipeline"]',
    "[citation needed: a review of the field]",
    "[release tag / commit SHA — to be filled on submission]",
]


def source(paper):
    return paper / "MANUSCRIPT.working.md"


def rewrite(paper, old, new):
    """Give a fixture paper one defect, by substitution in its source."""
    path = source(paper)
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new))


# --------------------------------------------------------------------------
# the grammar
# --------------------------------------------------------------------------


def test_the_three_legal_forms_all_parse(render):
    """`@key` narratively, `[@key]` parenthetically, `[@a; @b]` grouped."""
    result = render(CASE, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 0, result.report


def test_a_bracket_span_that_is_not_a_citation_group_is_a_parse_error(paper, run_in):
    """`A9` as corrected by `CT3`. Pandoc's permissive bracket prefix is
    refused: `[verify this @smith2020]` renders as *(verify this Smith 2020)*,
    a free-text channel into reader-facing prose — which is the first failure
    class re-opened inside the clause that closes it."""
    live = paper(CASE)
    rewrite(live, "[@gatenbee2023]", "[verify this @gatenbee2023]")
    result = run_in(live, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 3
    assert "parse error" in result.report
    assert "verify this @gatenbee2023" in result.report


def test_a_parse_error_means_nothing_ran(paper, run_in):
    """No verdict table, no manifest — a table with every row failing would
    claim that every check looked. None of them looked."""
    live = paper(CASE)
    rewrite(live, "[@hickey2022]", "[citation needed: a review of the field]")
    result = run_in(live, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 3
    assert "PASS" not in result.report
    assert "manifest" not in result.report
    assert result.document == ""


def test_the_refusal_names_the_file_and_the_line(paper, run_in):
    live = paper(CASE)
    rewrite(live, "[@hickey2022; @elhanani2023]", "[see @hickey2022]")
    result = run_in(live, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 3
    assert "MANUSCRIPT.working.md:9" in result.report


def test_a_locator_inside_the_brackets_is_refused(paper, run_in):
    """No prefixes, no suffixes, no locators. The surface is a strict subset of
    pandoc, so citeproc parses everything we emit; we refuse pandoc's
    permissive parts rather than diverge from it."""
    live = paper(CASE)
    rewrite(live, "[@gatenbee2023]", "[@gatenbee2023, p. 14]")
    result = run_in(live, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 3


def test_a_comma_separated_group_is_refused(paper, run_in):
    """`;` separates, and nothing else does."""
    live = paper(CASE)
    rewrite(live, "[@hickey2022; @elhanani2023]", "[@hickey2022, @elhanani2023]")
    result = run_in(live, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 3


def test_an_empty_bracket_span_is_refused(paper, run_in):
    live = paper(CASE)
    rewrite(live, "[@gatenbee2023]", "[]")
    result = run_in(live, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 3


def test_a_bracket_span_inside_a_comment_is_not_refused(paper, run_in):
    """The refusal is for what the source cannot express into *reader-facing*
    prose, and a comment never reaches the reader."""
    live = paper(CASE)
    rewrite(
        live,
        "The pipeline runs as five stages",
        "<!-- [author to supply: the stage count] -->\nThe pipeline runs as five stages",
    )
    result = run_in(live, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 0, result.report


def test_a_bracket_span_inside_a_brace_is_not_refused(paper, run_in):
    """A brace is the annotation channel; its label is author-facing text that
    the render emits as a uniform token, never as prose of its own."""
    live = paper(CASE)
    rewrite(
        live,
        "one round per marker pair.",
        "one round per marker pair, at {{ ! the [pending] objective magnification }}.",
    )
    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")
    assert result.exit_code == 1, result.report
    assert "⟦HOLE: the [pending] objective magnification⟧" in result.document


def test_a_bracket_span_inside_a_fence_is_not_refused(paper, run_in):
    """Inside a fence nothing is parsed at all: a source showing the syntax is
    showing it, not using it."""
    live = paper(CASE)
    rewrite(
        live,
        "The pipeline runs as five stages",
        "```\n[author to supply: an example]\n```\n\nThe pipeline runs as five stages",
    )
    result = run_in(live, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 0, result.report


def test_a_bracket_span_wrapping_lines_is_still_one_span(paper, run_in):
    """Span-based parsing, never line-anchored."""
    live = paper(CASE)
    rewrite(live, "[@gatenbee2023]", "[author to supply:\nthe registration arm]")
    result = run_in(live, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 3
    assert "author to supply: the registration arm" in result.report


# --------------------------------------------------------------------------
# the bibliography
# --------------------------------------------------------------------------


def test_a_key_with_no_bibliography_entry_is_a_hard_error(paper, run_in):
    """A citation with no entry is a dangling reference — a token pointing at
    nothing, structurally identical to a figure name absent from the roster, so
    it takes that tier. Neither mode emits."""
    live = paper(CASE)
    rewrite(live, "[@gatenbee2023] and report", "[@gatenbee2024] and report")
    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")
    assert result.exit_code == 2
    assert "citation → bib entry" in result.report
    assert "@gatenbee2024" in result.report
    assert result.document == ""


def test_an_uncited_bibliography_entry_gets_no_check_at_all(render):
    """A figure roster is a manifest of this document's objects; a bibliography
    is a library, and over-provisioning is its normal state. The fixture's
    library carries an entry marked *do NOT cite*, and the gate is silent about
    it — the asymmetry is deliberate."""
    result = render(CASE, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 0, result.report
    assert "uncited2019" not in result.report


def test_an_uncited_entry_never_reaches_the_reference_list(render):
    """The list is `f(cited keys)`, so an orphaned entry is impossible by
    construction rather than checked for."""
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")
    assert "uncited2019" not in result.document
    assert "nothing in this document cites" not in result.document


def test_a_missing_bibliography_is_the_same_dangling_reference(paper, run_in):
    """The render reads the bibliography from its declared path and never
    contains it, so an absent library is not a fallback to a built-in one."""
    live = paper(CASE)
    (live / "references.bib").unlink()
    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")
    assert result.exit_code == 2
    assert "references.bib" in result.report
    assert result.document == ""


def test_a_paper_that_cites_nothing_needs_no_bibliography(paper, run_in, render):
    """The declared input is required by the citations, not by the renderer: a
    paper with no citation has nothing to resolve."""
    live = paper(CASE)
    (live / "references.bib").unlink()
    text = source(live).read_text()
    source(live).write_text(re.sub(r" ?\[@[^\]]*\]| @[a-z]+\d{4}", "", text))
    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")
    assert result.exit_code == 0, result.report
    assert "## References" not in result.document


def test_a_malformed_bibliography_is_a_parse_error(paper, run_in):
    live = paper(CASE)
    (live / "references.bib").write_text("@article{hickey2022,\n  title = {unclosed\n")
    result = run_in(live, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 3
    assert "references.bib" in result.report


# --------------------------------------------------------------------------
# first-mention numbering and the reference list
# --------------------------------------------------------------------------


def test_citations_number_by_first_mention_in_the_assembled_document(render):
    """Not by the order of the bibliography, and not by the order the source
    files were read in. The fixture's library is ordered hickey, elhanani,
    gatenbee, muhlberg; the document mentions gatenbee first."""
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")
    assert result.exit_code == 0, result.report
    body = result.document
    assert "across rounds [1] and report" in body
    assert "one panel per round [2,3]" in body
    assert "as Muhlberg and colleagues [4]" in body


def test_a_repeated_key_keeps_its_first_number(render):
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")
    assert "round shares it [1]." in result.document
    assert "the drift left open [2]." in result.document


def test_no_key_survives_into_the_rendered_document(render):
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")
    assert "@gatenbee2023" not in result.document
    assert "@muhlberg2020" not in result.document


def test_the_reference_list_is_a_function_of_the_cited_keys(render):
    """Built from the cited keys, in citation-number order."""
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")
    references = result.document.split("## References", 1)
    assert len(references) == 2, "the render emits no reference list"
    listed = [
        line for line in references[1].splitlines() if re.match(r"^\d+\. ", line)
    ]
    assert len(listed) == 4
    assert listed[0].startswith("1. Gatenbee")
    assert listed[1].startswith("2. Hickey")
    assert listed[2].startswith("3. Elhanani")
    assert listed[3].startswith("4. Muhlberg")


def test_the_reference_list_carries_the_entry_fields(render):
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")
    assert "Virtual alignment of pathology image series" in result.document
    assert "Nature Communications" in result.document
    assert "2023" in result.document


# --------------------------------------------------------------------------
# `--section` granularity
# --------------------------------------------------------------------------


def test_at_section_granularity_every_token_is_left_unresolved_and_visible(render):
    """No number is assigned, because first-mention order is a fact about the
    whole document and a section cannot know it. And no placeholder form is
    invented: a placeholder is a second surface to learn and to get stale."""
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate", "--section", "results")
    assert result.exit_code == 0, result.report
    assert "the drift left open [@hickey2022]." in result.document
    assert "[1]" not in result.document
    assert "## References" not in result.document


def test_the_bib_entry_check_is_out_of_scope_at_section_granularity(render):
    """Whether every key resolves is a fact about the whole document. A check
    that never looked is a printed row, never silently a pass."""
    result = render(CASE, "MANUSCRIPT.working.md", "--check", "--section", "results")
    assert result.exit_code == 0, result.report
    assert re.search(
        r"citation → bib entry\s+SKIPPED — OUT OF SCOPE AT THIS GRANULARITY",
        result.report,
    )


def test_the_bracket_refusal_still_fires_at_section_granularity(paper, run_in):
    """A parse error is not a gate, so granularity does not scope it: the
    source cannot express the thing at all."""
    live = paper(CASE)
    rewrite(live, "[@hickey2022].", "[author to supply: the closing figure].")
    result = run_in(live, "MANUSCRIPT.working.md", "--check", "--section", "results")
    assert result.exit_code == 3


# --------------------------------------------------------------------------
# the calibration
# --------------------------------------------------------------------------
#
# Measured on the calibration corpus, outside comments: **70 bracket spans, 40
# citations, 30 annotations, and zero other legitimate uses.** No markdown
# link, no reference link, no footnote, no task box in 74 KB of biomedical
# prose — the one `[24][25]` that looks like a reference link is two adjacent
# numeric citations. Three further spans sit inside comments, exempt by
# construction. That measurement is what licenses a refusal rather than a
# finding: refusing every non-citation bracket span costs nothing on real text.
#
# The `calibration` fixture reproduces that distribution at its measured shape,
# and its mention sequence is the corpus's own.


def test_the_corpus_distribution_renders_clean(render):
    """40 citation spans and 30 annotations, and nothing in the source that the
    render cannot parse."""
    result = render(CALIBRATION, "MANUSCRIPT.working.md", "--circulate")
    assert result.exit_code == 0, result.report
    assert "manifest — 30 open annotations" in result.report
    body = result.document.split("## References", 1)[0]
    assert len(re.findall(r"\[\d+(?:,\d+)*\]", body)) == 40


def test_the_three_bracket_spans_inside_comments_are_exempt(render):
    """The corpus's own count, and the reason the exemption is by construction
    rather than by a marker string: a comment never reaches the reader."""
    live = render(CALIBRATION, "MANUSCRIPT.working.md", "--circulate")
    source_text = (live.paper / "MANUSCRIPT.working.md").read_text()
    outside = re.sub(r"<!--.*?-->", "", source_text, flags=re.DOTALL)
    inside = len(re.findall(r"\[[^\[\]]*\]", source_text, re.DOTALL)) - len(
        re.findall(r"\[[^\[\]]*\]", outside, re.DOTALL)
    )
    assert inside == 3
    assert live.exit_code == 0, live.report


def test_the_corpus_mention_sequence_renumbers_to_first_mention_order(render):
    """The whole point, on the corpus's own sequence."""
    result = render(CALIBRATION, "MANUSCRIPT.working.md", "--circulate")
    listed = [
        line.split(". ", 1)[1].split(",")[0]
        for line in result.document.split("## References", 1)[1].splitlines()
        if re.match(r"^\d+\. ", line)
    ]
    assert listed == [
        "Foy",
        "Sturm",
        "Gatenbee",
        "Hickey",
        "Elhanani",
        "Gatenbee",
        "Muhlberg",
        "Bankhead",
        "Schapiro",
        "Berg",
        "Lowe",
        "Fischler",
        "Greenwald",
        "Klein",
        "Avants",
        "Finotello",
        "Stringer",
    ]


def test_the_documents_first_citation_is_numbered_one(render):
    """The load-bearing evidence, inverted.

    In the corpus the first two citations in the document were numbered **24
    and 25**, appended last — because renumbering by hand *"would be the first
    citation and shift every number"*. A wrong-but-valid literal, minted
    deliberately, that no gate could catch. Under keys the render assigns 1 and
    2 and nobody has to decide anything.
    """
    result = render(CALIBRATION, "MANUSCRIPT.working.md", "--circulate")
    body = result.document.split("## References", 1)[0]
    assert re.search(r"disagree with imaging on the same cohort \[1,2\]", body)
    assert "1. Foy" in result.document


def test_the_three_uncited_entries_get_no_check_at_all(render):
    """The corpus kept eight entries it deliberately did not cite, six marked
    *do NOT cite*. The gate is silent about all of them."""
    result = render(CALIBRATION, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 0, result.report
    assert "uncited" not in result.report
    assert "uncited" not in result.document


@pytest.mark.parametrize("span", IMPROVISED, ids=range(len(IMPROVISED)))
def test_each_improvised_annotation_syntax_is_refused_in_prose(paper, run_in, span):
    """Nine syntaxes, one refusal. The corpus improvised all nine because
    nothing refused any of them, and six review passes read past every one."""
    live = paper(CALIBRATION)
    rewrite(live, "[@hickey2022]", span)
    result = run_in(live, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 3
    assert "not a citation group" in result.report


def test_a_markdown_link_is_refused_and_that_is_the_measured_cost(paper, run_in):
    """The refusal's whole cost, stated rather than discovered: a markdown link
    cannot be written in reader-facing prose. It is affordable because the
    corpus contains **zero** of them — a paper's cross-references are `@key`
    and `@fig:name`, and its URLs live in the bibliography."""
    live = paper(CALIBRATION)
    rewrite(live, "[@hickey2022]", "[the protocol](https://example.org/protocol)")
    result = run_in(live, "MANUSCRIPT.working.md", "--check")
    assert result.exit_code == 3
