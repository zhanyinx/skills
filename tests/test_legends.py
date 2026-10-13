"""Legends: emitted after the reference list, numbered as their rows resolve,
and gated as the prose a reader meets.

A legend's prose is its file less two things that are not reader-facing — the
`#` title, which names the file, and the `## Panels` block, which the
namespace has already read. It is held to the source grammar and read into the
same rows as the body wherever a row reads every reader-facing line; the rows
that measure an argument's prose stay off it, because a caption is not one.

The fixture's roster lists its rows in an order that agrees with nothing — not
with first mention, and not with the order the legends come out in — because
the roster carries no order of its own.

These tests use the CLI as their only seam, like every other test here.
"""

from shipped_text import collapsed

CASE = "legends"

flat = collapsed


def source(paper):
    return paper / "MANUSCRIPT.working.md"


def legend(paper, name):
    return paper / "legends" / ("%s.md" % name)


def rewrite(path, old, new):
    """Give a fixture file one defect, by substitution."""
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new))


def row(report, name):
    """One verdict row of a report, verbatim, minus its name."""
    for line in report.splitlines():
        if line.strip().startswith(name):
            return line.strip()[len(name):].strip()
    return None


def legends_part(document):
    """The emitted legends, everything after their heading."""
    head, _, tail = document.partition("## Legends")
    assert tail, "no legends section in the document"
    return head, tail


# --------------------------------------------------------------------------
# the emitted document
# --------------------------------------------------------------------------


def test_the_whole_document_is_verbatim(render, golden):
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 0, result.report
    assert result.document == golden("legends-circulate.md")


def test_the_legends_follow_the_reference_list(render):
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")

    body, _ = legends_part(result.document)
    assert "\n## References\n" in body


def test_legends_come_out_by_kind_and_then_by_number(render):
    """Tables, figures, Extended Data figures, Extended Data tables,
    supplementary — and within a kind, the number the row resolved to. The
    roster lists `pipeline` before `registration-accuracy`, but the body
    mentions a panel of `registration-accuracy` first, so it is figure 1 and
    its legend comes first."""
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")

    _, legends = legends_part(result.document)
    headings = [line for line in legends.splitlines() if line.startswith("### ")]
    assert headings == [
        "### Tbl. 1",
        "### Fig. 1",
        "### Fig. 2",
        "### Ext. fig. 1",
        "### Ext. tbl. 1",
        "### Suppl. 1",
    ]
    assert legends.index("Registration holds every round") < legends.index("Five stages")


def test_a_panel_in_its_own_legend_is_its_bare_letter(render):
    """The caption already sits under the figure's number, so its own panels
    render as their letters. A panel of another figure renders as it does
    anywhere else."""
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")

    _, legends = legends_part(flat(result.document))
    assert "a shows the DAPI overlay before and after registration, on the stages of fig. 2 (a)." in legends
    assert "b shows per-arm Dice" in legends
    assert "a shows the stage graph and b a tile-boundary crop" in legends


def test_a_figure_named_in_another_legend_renders_as_usual(render):
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")

    _, legends = legends_part(flat(result.document))
    assert "Residual drift per round after registration, against fig. 1." in legends


def test_legend_citations_number_after_the_body_in_legend_order(render):
    """The body cites two keys, 1 and 2. The table's legend is emitted before
    the figures', so its new key is 3 and the figure legend's is 4. A key the
    body already cited keeps its number, and the one list holds them all."""
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")

    body, legends = legends_part(flat(result.document))
    assert "after Muhlberg [3]" in legends
    assert "per-arm Dice [4,2]" in legends
    assert "tile-boundary crop [2]" in legends
    assert "3. Muhlberg, Alexander." in body
    assert "4. Elhanani, Ofer" in body


def test_a_legend_with_no_panels_block_still_emits(render):
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")

    _, legends = legends_part(flat(result.document))
    assert "### Ext. tbl. 1 Every reagent, with its supplier and lot." in legends


def test_neither_the_title_nor_the_declaration_block_reaches_the_reader(render):
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")

    assert "Legend —" not in result.document
    assert "## Panels" not in result.document
    assert "DAPI cross-panel overlay" not in result.document
    assert "never reaches the reader" not in result.document


def test_a_section_render_carries_no_legends(paper, run_in):
    """A legend is a whole-document input. A section render neither emits the
    legends nor gates them, so a defect in one does not reach it."""
    live = paper(CASE)
    rewrite(legend(live, "pipeline"), "Five stages", "Five stages TBD")

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate", "--section", "results")

    assert result.exit_code == 0, result.report
    assert "## Legends" not in result.document
    assert row(result.report, "bare holes") == "PASS"


# --------------------------------------------------------------------------
# the gate over the legends
# --------------------------------------------------------------------------


def test_an_unwritten_legend_is_a_gap(paper, run_in):
    """A legend with a title and a declaration block and no prose is a gap on
    the same terms as an unfilled slot: a hole under its heading, and a gating
    row that names it."""
    live = paper(CASE)
    rewrite(
        legend(live, "pipeline"),
        "Five stages, each reproducible from the committed configuration. @fig:stage-graph shows the stage\n"
        "graph and @fig:seam-crop a tile-boundary crop [@hickey2022].\n",
        "",
    )

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 1, result.report
    assert row(result.report, "unfilled skeleton slot") == "FAIL — 1 (the legend of `pipeline`)"
    assert "### Fig. 2 ⟦HOLE: the legend of pipeline⟧" in flat(result.document)


def test_a_gating_annotation_in_a_legend_gates_and_lands_in_the_manifest(paper, run_in):
    live = paper(CASE)
    rewrite(legend(live, "pipeline"), "Five stages", "{{ ! @analyst stage count }} stages")

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 1, result.report
    assert row(result.report, "annotations (gating)") == (
        "FAIL — 1 (pipeline.md:3 `stage count`)"
    )
    assert "@analyst" in result.report.split("manifest")[1]
    assert "⟦HOLE: stage count⟧ stages" in result.document


def test_a_bare_hole_in_a_legend_is_reported_at_its_own_line(paper, run_in):
    live = paper(CASE)
    rewrite(legend(live, "reagent-list"), "and lot.", "and lot TBD.")

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert row(result.report, "bare holes") == "FAIL — 1 (reagent-list.md:3 `TBD`)"


def test_an_em_dash_in_a_legend_is_counted(paper, run_in):
    live = paper(CASE)
    rewrite(legend(live, "reagent-list"), "reagent, with", "reagent — with")

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert row(result.report, "em dashes (threshold 0)") == "FAIL — 1 (reagent-list.md:3)"


def test_a_legend_citation_with_no_entry_is_a_hard_error(paper, run_in):
    live = paper(CASE)
    rewrite(legend(live, "reagent-list"), "and lot.", "and lot [@nobody2024].")

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 2, result.report
    assert row(result.report, "citation → bib entry") == (
        "FAIL — 1 (reagent-list.md:3 `@nobody2024`)"
    )
    assert result.document == ""


def test_a_name_in_a_legend_the_document_does_not_carry_is_a_hard_error(paper, run_in):
    live = paper(CASE)
    rewrite(legend(live, "reagent-list"), "and lot.", "and lot, as @fig:lot-map shows.")

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 2, result.report
    assert row(result.report, "slot / roster integrity") == (
        "FAIL — 1 (reagent-list.md:3 `@fig:lot-map`)"
    )


def test_a_name_written_only_in_a_legend_is_still_referenced_nowhere(paper, run_in):
    """A legend describes its figure; it does not discuss it. `drift-by-round`
    is named in its own legend's neighbour and nowhere in the body."""
    live = paper(CASE)
    rewrite(source(live), " the drift stays flat across rounds (@fig:drift-by-round),", "")
    rewrite(legend(live, "reagent-list"), "and lot.", "and lot (@fig:drift-by-round).")

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 2, result.report
    assert row(result.report, "slot / roster integrity") == (
        "FAIL — 1 (`drift-by-round` is in the roster and referenced nowhere)"
    )


def test_the_rhythm_rows_read_the_body_only(render):
    """A caption is not an argument: the body holds six sentences, and the
    legends' sentences are not counted into them."""
    result = render(CASE, "MANUSCRIPT.working.md", "--circulate")

    assert row(result.report, "subject openings") == "6 used once (of 6 sentences)"


# --------------------------------------------------------------------------
# the source grammar over the legends
# --------------------------------------------------------------------------


def test_a_heading_in_a_legends_prose_is_a_parse_error(paper, run_in):
    live = paper(CASE)
    rewrite(legend(live, "reagent-list"), "Every reagent", "### Reagents\n\nEvery reagent")

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 3
    assert "reagent-list.md:3: `### Reagents` is a heading" in result.report


def test_an_anchor_in_a_legend_is_a_parse_error(paper, run_in):
    live = paper(CASE)
    rewrite(legend(live, "reagent-list"), "Every reagent", "<!-- slot: results -->\nEvery reagent")

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 3
    assert "reagent-list.md:3: `<!-- slot: results -->` is an anchor in a legend" in result.report


def test_a_panel_letter_literal_in_a_legend_is_a_parse_error(paper, run_in):
    """The lettering refusal holds in a legend as in the body: the letter is
    the render's to assign, never the prose's to spell."""
    live = paper(CASE)
    rewrite(legend(live, "pipeline"), "a tile-boundary crop", "(b) a tile-boundary crop")

    result = run_in(live, "MANUSCRIPT.working.md", "--circulate")

    assert result.exit_code == 3
    assert "pipeline.md:4" in result.report
