"""The mechanism behind the deletions.

The four sharpest findings in the audit behind this rework are class D — *the
rule actively causes the defect* — and their cure is a deletion. A deletion is
the one kind of edit that leaves nothing on the page to point at afterwards, so
it is also the one kind that can be silently undone: re-adding a deleted
exemplar reads as restoring a helpful example, and the rule it violates is
three sections away.

That is the failure mode the 98 em dashes measured the cost of. The em-dash ban
was a rule in the right skill, unambiguous, and violated 98 times through six
clean reviews, because nothing counted. So the deletions here get a count of
their own: every literal that had to go is asserted absent, every replacement
that had to land in the same file is asserted present, and the sets that could
drift apart are asserted equal rather than described as equal in prose.

Three properties make this different from grepping the files by hand.

**Literals are matched with whitespace collapsed.** A phrase re-introduced with
a line break in the middle of it is the same phrase to a reader and a different
string to `in`. Every literal assertion below runs on collapsed text, so
re-wrapping cannot hide a restoration.

**A closed set beats an absence.** Where the spec retired some bullets from a
list and kept others, the assertion is over the whole list rather than over the
retired names: that fires when a retired bullet comes back *and* when a kept one
quietly leaves. An absence assertion only catches the first.

**Naming a token in order to abolish it is not emitting it.** All five skills
say there is no `CLEAN` verdict, so `"CLEAN" not in text` fails on correct
files. The discriminator below reads the statement each occurrence sits in and
asks whether that statement denies the token or hands it out.

Scope is the five shipped `SKILL.md` files. The assets beside them carry the
same abolitions in their own prose (`render-paper`'s `CITATIONS.md` deletes the
bracketed citation-needed form by name), and the checks each skill actually runs
live in `render-paper`'s own test modules; this one is about the contract the
five skill files state.

The judgement half of the same ticket is `docs/mechanism-sweep.md`: every rule
in the five files, what makes it bite, and the four that nothing does. This
module is what that document points at, and the residue it records is what this
module could not be asked to check.
"""

import re
from pathlib import Path

from shipped_text import section_of, without_fences

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS = REPO_ROOT / "skills"

# The five units, in pipeline order: plan, draft, assemble, review, and the one
# that renders and checks for all of them.
UNITS = ("wayfinder", "write-paper", "assemble-paper", "review-paper", "render-paper")

# A top-level bullet's bold label, which is how every list the spec fixes as a
# closed set names its members.
BULLET_LABEL = re.compile(r"^- \*\*(.+?)\*\*", re.MULTILINE)

# The `## Style` keys, whose one home is `write-paper`'s `STYLE-STANZA.md`. A
# filled one in a `SKILL.md` is a shipped house style; `test_style_stanza.py`
# guards the asset, this module guards all five skill files.
FILLED_KEY = re.compile(
    r"^\s*-\s+(active-we|plain-words|build-in-steps|spelling-variant"
    r"|em-dash-threshold|terms):[ \t]*(\S.*)$",
    re.MULTILINE,
)


def shipped(unit):
    """One shipped `SKILL.md`, verbatim."""
    return (SKILLS / unit / "SKILL.md").read_text()


def collapsed(text):
    """The text as one line, every run of whitespace collapsed to one space.

    Every literal assertion in this module goes through here. A deleted phrase
    re-introduced across a line break is the same sentence to a reader, and
    `"number it consistently with what already exists" in text` is False the
    moment the line wraps between two of those words — so a check that skipped
    this step would pass on a file that had put the mandate back.
    """
    return re.sub(r"\s+", " ", text)


def carries(unit, literal):
    """Whether a shipped skill file carries a phrase, as a reader would read it.

    Collapsed and case-insensitive. Case matters here for the same reason
    whitespace does and no other: the four deleted phrases were sentence
    fragments lifted out of bullets, and the obvious way to put one back is at
    the start of a sentence, capitalised. A case-sensitive check passes on
    exactly that restoration, which was measured — the mutation that put the
    numbering mandate back as `Number it consistently…` went uncaught until
    this function stopped being `in`.
    """
    return literal.lower() in collapsed(shipped(unit)).lower()


# A line that starts a new statement rather than continuing the one above:
# a table row, a bullet, a numbered step, a heading, a quote, or a fence.
STARTS_A_STATEMENT = re.compile(r"^(?:\||[-*+] |\d+\. |#|>|```)")


def statements(text):
    """The document as whitespace-collapsed statements.

    A statement is the unit a claim is made in, which in this Markdown is one
    of two shapes. A table row or a list item is a statement whatever
    punctuation it carries, because a verdict table's row ends at the newline
    and not at a full stop. Prose is a statement per sentence.

    Both shapes wrap across lines, and the wrap is where a naive splitter goes
    wrong in both directions: it cuts a sentence in half, so a denial on one
    line stops reaching the token on the next, and it cuts a bullet into pieces
    that each look like a whole claim. So lines are gathered into their
    statement first and split into sentences second.

    Fenced blocks stay in. A verdict table printed inside a fence is exactly
    where an output token would appear.
    """
    for block in re.split(r"\n[ \t]*\n", text):
        gathered = []
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if gathered and STARTS_A_STATEMENT.match(stripped):
                yield from sentences(gathered)
                gathered = []
            gathered.append(stripped)
        if gathered:
            yield from sentences(gathered)


def sentences(lines):
    """One gathered statement, split into sentences if it is prose.

    A row or an item is never split: `| CLEAN | not a verdict |` carries a full
    stop nowhere and a pipe everywhere, and splitting it on punctuation would
    let a denial in one cell excuse a token in another.
    """
    whole = collapsed(" ".join(lines))
    if STARTS_A_STATEMENT.match(whole):
        yield whole
        return
    for sentence in re.split(r"(?<=[.!?:])\s+", whole):
        if sentence.strip():
            yield sentence.strip()


# A statement that denies the token rather than handing it out. `no`, `not`,
# `never` and `abolish` are the four ways the five files say it, and the
# negation has to reach the token: a row that emitted `CLEAN` while mentioning
# some unrelated "not" elsewhere in the row would otherwise pass.
DENIAL = re.compile(r"\b(?:no|not|never|abolish\w*)\b[^.]{0,80}?CLEAN")


def emits_as_verdict(statement):
    """Whether a statement carrying `CLEAN` hands the token out as an output.

    The token has to be nameable — a skill cannot abolish a verdict without
    saying which one — so absence is not the property to check. This asks the
    narrower question the abolition actually implies: does any statement carry
    the token without denying it?
    """
    return "CLEAN" in statement and not DENIAL.search(statement)


def bullet_labels(text, heading):
    """The bold labels of the top-level bullets in one section.

    Fence-aware through `section_of`, so a template a skill ships for copying
    cannot be mistaken for the section itself.
    """
    return [label for label in BULLET_LABEL.findall(section_of(text, heading))]


def steps(text):
    """The numbered process steps a skill declares, by name."""
    return re.findall(r"^### (\d+)\. (.+)$", without_fences(text), re.MULTILINE)


# ---------------------------------------------------------------------------
# The mechanisms above, pinned on text built to have the defect they exist for.
# Both of them return the wrong answer under the naive implementation, and both
# would then pass silently over the whole corpus.
# ---------------------------------------------------------------------------


class TestCollapsed:
    def test_a_phrase_broken_across_lines_is_found(self):
        """The defect: a restored mandate hides behind a line wrap."""
        wrapped = "…and\nnumber it consistently with what\nalready exists in the piece."

        assert "number it consistently with what already exists" in collapsed(wrapped)

    def test_indentation_does_not_separate_words(self):
        assert collapsed("one\n      two") == "one two"


class TestCarries:
    def test_a_deleted_phrase_restored_capitalised_is_found(self):
        """The measured hole. Every one of the four deletions is a fragment
        lifted out of a bullet, so the natural way to put one back is at the
        head of a sentence — and the case-sensitive version of this check
        passed on exactly that."""
        assert "number it consistently".lower() in collapsed(
            "Number it consistently with what already exists."
        ).lower()

    def test_it_reads_the_shipped_file(self):
        assert carries("write-paper", "stable name")
        assert not carries("write-paper", "a phrase no skill would ever ship")


class TestEmitsAsVerdict:
    def test_a_verdict_table_row_emits(self):
        assert emits_as_verdict("| CLEAN | nothing to report |")

    def test_a_sentence_abolishing_the_token_does_not(self):
        assert not emits_as_verdict("There is no `CLEAN` verdict to record.")

    def test_the_denial_has_to_reach_the_token(self):
        """A row that hands out the verdict is not excused by carrying the word
        `not` somewhere else in the row."""
        assert emits_as_verdict(
            "| CLEAN | every check passed, and the gate did not refuse |"
        )

    def test_abolished_counts_as_a_denial(self):
        assert not emits_as_verdict("`G6` abolished CLEAN for the gate.")


class TestStatements:
    def test_a_table_row_is_its_own_statement(self):
        """Rows carry no full stop, so a sentence splitter would swallow a
        whole table into one statement and any denial anywhere in it would
        excuse every row."""
        table = "| PASS | fine |\n| CLEAN | not a verdict anyone prints |\n"

        assert list(statements(table)) == [
            "| PASS | fine |",
            "| CLEAN | not a verdict anyone prints |",
        ]

    def test_prose_splits_at_sentence_ends(self):
        assert list(statements("First one. Second one.")) == [
            "First one.",
            "Second one.",
        ]

    def test_a_wrapped_sentence_is_one_statement(self):
        """The defect that matters: `review-paper` wraps its own abolition
        sentence, so a per-line splitter separates the denial from the token and
        reports the file as emitting a verdict it explicitly refuses."""
        assert list(statements("a sentence broken\nacross two lines.")) == [
            "a sentence broken across two lines."
        ]

    def test_a_wrapped_bullet_is_one_statement(self):
        wrapped = "- **A label** — a claim that runs on\n  to a second line.\n"

        assert list(statements(wrapped)) == [
            "- **A label** — a claim that runs on to a second line."
        ]

    def test_a_bullet_ends_at_the_next_bullet(self):
        assert list(statements("- first\n- second\n")) == ["- first", "- second"]

    def test_a_row_is_not_split_on_its_own_punctuation(self):
        """A denial in one cell must not excuse a token in another."""
        assert list(statements("| CLEAN | not a verdict. |")) == [
            "| CLEAN | not a verdict. |"
        ]


# ---------------------------------------------------------------------------
# §12 — the required deletions, each asserted against the file it left.
# ---------------------------------------------------------------------------


class TestTheDeletedExemplarsAreGone:
    """A rule that is superseded but whose violating example stays on the page
    is not fixed; the example is what a model copies."""

    DELETED = (
        "concordance among proxies",
        "number it consistently",
        "[citation needed",
    )

    def test_the_negated_frame_caveat_is_gone_from_the_drafting_rules(self):
        """The sharpest of the four. The rule said don't invoke the banned
        frame; the example beside it invoked it in order to deny it, and the
        manuscript denied that frame in seven independent sections. The
        construction was supplied by example, so the example is the defect."""
        assert not carries("write-paper", "concordance among proxies")

    def test_the_negated_frame_caveat_is_gone_from_the_editorial_pass(self):
        """It shipped in two units. Deleting one copy leaves the construction
        available from the other."""
        assert not carries("assemble-paper", "concordance among proxies")

    def test_the_number_it_consistently_mandate_is_gone(self):
        """Numbering is a render act — a drafting session that numbered
        anything would be writing the one thing the render overwrites."""
        assert not carries("write-paper", "number it consistently")

    def test_the_bracketed_citation_needed_literal_is_gone(self):
        """`[…]` is reserved for citation groups, so the old placeholder was
        both a parse error and a gap the gate could not see."""
        assert not carries("write-paper", "[citation needed")

    def test_no_unit_carries_any_of_the_four(self):
        """The four left the files that shipped them; none of the other three
        picked one up."""
        stray = {
            (unit, literal)
            for unit in UNITS
            for literal in self.DELETED
            if carries(unit, literal)
        }

        assert stray == set()


class TestTheReplacementsLandedInTheSameFile:
    """Each deletion had to be made in the same edit as the rule replacing it.
    A file that lost the exemplar and never gained the construction leaves a
    drafting session with the constraint and no way to honour it, which is
    worse than the exemplar was."""

    def test_the_gate_bit_hole_form_replaces_the_bracketed_literal(self):
        citations = collapsed(
            section_of(
                shipped("write-paper"),
                "### 3. Handle citations as you draft — never fabricate one",
            )
        )

        assert "{{ ! <what the claim requires> }}" in citations

    def test_the_reference_by_name_text_replaces_the_numbering_mandate(self):
        """The replacement is not silence about numbering: the step says where
        numbers do exist, and names the positional forms that are parse
        errors."""
        by_name = collapsed(
            section_of(
                shipped("write-paper"),
                "### 4. Reference figures, panels and citations by name — never by number",
            )
        )

        assert "stable name" in by_name
        assert "Numbers and panel letters exist only in rendered output" in by_name
        for refused in ("`Fig 2`", "`Fig. 4b`", "`[7]`", "`@fig:panel-b`"):
            assert refused in by_name
        assert "parse error" in by_name

    def test_the_positive_scope_construction_replaces_the_negated_frame(self):
        rules = collapsed(
            section_of(
                shipped("write-paper"),
                "### 5. Construction rules — these hold while you write the sentence, "
                "not after",
            )
        )

        assert (
            "A framing constraint is obeyed by not invoking the frame, never by denying it"
            in rules
        )

    def test_the_positive_scope_construction_ships_its_counter_example(self):
        """The construction alone is a rule in prose. What makes it usable is
        the pair — the sentence that honours the constraint, and beside it the
        denial that does not — because denial was the only construction the
        drafter previously had."""
        rules = collapsed(
            section_of(
                shipped("write-paper"),
                "### 5. Construction rules — these hold while you write the sentence, "
                "not after",
            )
        )
        bullet = rules[rules.index("A framing constraint is obeyed") :]

        assert "chosen to span the immune-content range" in bullet
        assert "Not \"consistent with a proof of concept rather than a validation.\"" in bullet
        assert "the banned word does not appear at all" in bullet

    def test_the_editorial_pass_caveat_example_carries_no_negated_frame(self):
        """`assemble-paper`'s copy is replaced by an example of the same shape
        with the negation taken out, not by the construction rule — the
        editorial pass shortens a caveat, it does not draft one."""
        bullets = section_of(shipped("assemble-paper"), "### 3. Make the editorial pass")
        caveat = collapsed(
            next(
                bullet
                for bullet in re.split(r"^- ", bullets, flags=re.MULTILINE)
                if bullet.startswith("**Repeated caveat")
            )
        )
        example = re.search(r"“(.+?)”|\"(.+?)\"", caveat)
        assert example, "the repeated-caveat bullet ships no example to check"
        stated = next(group for group in example.groups() if group)

        assert not re.search(r"\bnot\b|\brather than\b|n't\b", stated), stated


class TestEmDashLeftTheCraftBaseline:
    """It failed 98 times because it sat in a list framed as "never a hard
    violation", which licensed the Craft agent to weigh 98 of them and call the
    prose fine. Leaving it there is what licensed that."""

    # Eleven smells survived the rework and four were added. Asserted as a
    # closed set rather than as `Em Dash`'s absence: that catches a
    # re-addition, and also catches a rewrite that drops one of the fifteen.
    BASELINE = (
        "Overclaim",
        "Unsupported Causal Claim",
        "Hedge Mismatch",
        "Buried Contradiction",
        "Smoothed Transition Gap",
        "Dangling Modifier / Unclear Antecedent",
        "Term Drift",
        "Redundant Restatement",
        "Scope Creep",
        "Passive Obfuscation",
        "Meta-narration / Signposting",
        "Rationale Leak",
        "Filler adversative",
        "Repeated grammatical subject",
        "Uniform paragraph shape",
    )

    def smells(self):
        """The baseline's smell labels, minus the two rules that bind the list
        rather than naming a smell."""
        labels = bullet_labels(shipped("review-paper"), "#### The prose smell baseline")
        return [label for label in labels if not label.endswith(".")]

    def test_the_baseline_is_exactly_the_fifteen_surviving_smells(self):
        assert tuple(self.smells()) == self.BASELINE

    def test_no_smell_names_the_em_dash(self):
        """Stated separately from the set equality above, because this is the
        finding and the set is the mechanism."""
        assert [smell for smell in self.smells() if "em dash" in smell.lower()] == []

    def test_the_count_became_a_gate_row_instead(self):
        """It left the baseline for somewhere that cannot weigh it. A deletion
        with no mechanism behind it would have left nothing counting."""
        assert "| `em dashes (threshold N)` |" in shipped("render-paper")

    def test_the_two_rules_that_bind_the_baseline_survive(self):
        """Both are what keep the baseline out of Tier 2, so dropping either
        would silently promote fifteen heuristics to invariants."""
        labels = bullet_labels(shipped("review-paper"), "#### The prose smell baseline")

        assert labels[:2] == [
            "The documented style overrides.",
            "Always a judgement call.",
        ]


class TestCleanIsNeverAnOutputToken:
    """`G6` abolished the verdict pipeline-wide, not just in the skill that
    used to print it. Every occurrence in the five files has to be a statement
    saying there is no such verdict."""

    def test_no_unit_hands_the_token_out(self):
        emitted = {
            unit: statement
            for unit in UNITS
            for statement in statements(shipped(unit))
            if emits_as_verdict(statement)
        }

        assert emitted == {}

    def test_the_abolition_is_stated_and_not_merely_implied(self):
        """Absence would satisfy the letter of it. But the token was a habit
        across the pipeline, and a skill that never mentions it leaves a
        session free to invent it — so the three skills whose output could
        carry a verdict say there is none."""
        for unit in ("wayfinder", "write-paper", "review-paper"):
            assert "CLEAN" in shipped(unit), unit

    def test_the_verdict_vocabulary_is_the_gate_report_only(self):
        """What replaced it: a per-check table whose tokens are the render's,
        and no single-word verdict at all."""
        review = collapsed(shipped("review-paper"))

        assert "no single-word verdict" in review


class TestTheRetiredBulletsAreGone:
    """Four retirements, each a replacement-by-construction rather than a
    rewrite. All four are asserted through the list or the step sequence that
    would have held them, so the assertion also fires if what survived them
    goes missing."""

    KEPT_BULLETS = (
        "Redundant restatement",
        "Cross-section repetition",
        "Repeated caveat or scope statement",
        "Repeated contribution framing",
        "Term drift",
        "Missing or dangling connective logic",
    )

    KEPT_STEPS = (
        ("1", "Pin the manuscript order"),
        ("2", "Promote"),
        ("3", "Make the editorial pass"),
        ("4", "Hand off"),
    )

    def test_the_editorial_pass_carries_exactly_the_six_kept_bullets(self):
        """Two left: heading-and-numbering consistency, and dangling pointers."""
        labels = bullet_labels(
            shipped("assemble-paper"), "### 3. Make the editorial pass"
        )

        assert tuple(labels) == self.KEPT_BULLETS

    def test_heading_and_numbering_consistency_is_gone(self):
        """Two separate deletions landed on this one bullet — headings are
        injected from the skeleton every pass, and the reference list is built
        from cited keys — and together they retire it."""
        assert not carries("assemble-paper", "heading and numbering consistency")

    def test_dangling_pointers_is_gone(self):
        """Naming a section became illegal and every reference became
        mechanical, so there is no pointer left to dangle. The connective-logic
        bullet keeps the word `dangling` for a different subject, which is why
        the closed set above is the real guard."""
        labels = bullet_labels(
            shipped("assemble-paper"), "### 3. Make the editorial pass"
        )

        assert "Dangling pointers" not in labels

    def test_the_concatenation_step_is_gone(self):
        """Concatenation is the render's, on every pass. What stands in its
        place is a promotion, which is a different act: it moves the source and
        is irreversible."""
        assert steps(shipped("assemble-paper")) == list(self.KEPT_STEPS)

    def test_the_skill_says_the_render_owns_what_the_steps_stopped_doing(self):
        """The step went away and the duty did not evaporate — the boundary
        says where it went, which is what keeps a session from re-deriving it."""
        boundaries = collapsed(section_of(shipped("assemble-paper"), "## Boundaries"))

        assert "Renumbers nothing, and checks no heading" in boundaries

    def test_the_mark_what_changed_step_is_gone(self):
        """Deletion is the only closure and git is the audit trail. The
        hand-maintained change log it replaced died at four uses."""
        assert not carries("assemble-paper", "mark what changed")
        # `RESOLVED` stays case-sensitive: it was a marker, and the skill's own
        # boundaries legitimately say it never *resolves* a contradiction by
        # picking a side. Folding case here would fire on that sentence.
        assert "RESOLVED" not in shipped("assemble-paper")


# ---------------------------------------------------------------------------
# The settled vocabulary, and the one collision left deliberately in place.
# ---------------------------------------------------------------------------


class TestTheSettledVocabularyIsUsedVerbatim:
    # Which units are obliged to carry which term. Not every term belongs in
    # every file — `overlap check` is the renderer's lint and `argument brief`
    # is not the reviewer's input — so the obligation is per concept, and a
    # unit that carries the concept has to spell it the settled way.
    OBLIGED = {
        "unit": UNITS,
        "slot": UNITS,
        "rung": ("wayfinder", "write-paper", "render-paper"),
        "debt": ("wayfinder", "write-paper", "review-paper", "render-paper"),
        "spine": ("write-paper", "assemble-paper", "render-paper"),
        "claim ladder": ("write-paper", "review-paper", "render-paper"),
        "argument brief": ("write-paper", "render-paper"),
        "inventory brief": ("write-paper", "render-paper"),
        "proposition": ("write-paper", "assemble-paper", "review-paper", "render-paper"),
        "shed": ("write-paper", "review-paper", "render-paper"),
        "originating": ("write-paper", "render-paper"),
        "non-originating": ("write-paper", "render-paper"),
        "the gate bit": ("write-paper", "review-paper", "render-paper"),
    }

    # The definition of `unit` is the one sentence three separate `##
    # Vocabulary` sections all state, so it is the one most able to drift.
    UNIT_DEFINITION = (
        "one top-level skeleton slot and its subtree; the thing a rung, a brief, "
        "a `draft` ticket and a word budget all key on, 1:1"
    )

    def test_every_obliged_unit_carries_the_term(self):
        missing = {
            (term, unit)
            for term, units in self.OBLIGED.items()
            for unit in units
            if term not in collapsed(shipped(unit))
        }

        assert missing == set()

    def test_the_three_render_behaviours_are_named_together(self):
        """`HOLE / SLOT / SILENT` is one vocabulary, and a file naming two of
        the three has a gap rather than a shorthand."""
        for unit in ("write-paper", "assemble-paper", "render-paper"):
            text = shipped(unit)
            assert {"HOLE", "SLOT", "SILENT"} <= set(re.findall(r"\b[A-Z]{4,6}\b", text)), unit

    def test_the_unit_definition_does_not_drift_between_vocabularies(self):
        """Three files define it. One sentence, three copies — which is the
        shape this whole rework exists to remove, and here it is unavoidable:
        a skill may not read another skill's directory, because a partial
        install would leave it pointing at a file that is not there. So the
        copies are asserted equal instead."""
        defining = [
            unit
            for unit in UNITS
            if "## Vocabulary" in without_fences(shipped(unit))
        ]

        assert defining == ["write-paper", "assemble-paper", "render-paper"]
        for unit in defining:
            vocabulary = collapsed(section_of(shipped(unit), "## Vocabulary"))
            assert self.UNIT_DEFINITION in vocabulary, unit

    def test_no_unit_carries_retired_vocabulary(self):
        """Words the rework replaced. Each was settled enough to be quoted
        verbatim in other resolutions, which is what makes transcribing the
        original a live hazard."""
        retired = ("checklist brief", "sub-heading budget", "kind enum")
        strays = {
            (unit, word)
            for unit in UNITS
            for word in retired
            if carries(unit, word)
            and not re.search(
                r"\b(?:no|not|never)\b[^.]{0,40}?" + re.escape(word),
                collapsed(shipped(unit)),
                re.IGNORECASE,
            )
        }

        assert strays == set()


class TestTheSlotCollisionIsQualified:
    """`slot` means a section position in the heading tree, and `SLOT:` inside
    an annotation brace marks a venue back-matter field. Two concepts, one
    word, kept deliberately rather than renamed — so the rule is that a passage
    where both could apply says which is meant."""

    def carries_both_senses(self, unit):
        text = shipped(unit)
        return "SLOT:" in text and re.search(r"\bslots?\b", text)

    def test_every_unit_carrying_both_senses_qualifies_the_collision(self):
        """Mechanically decidable, which is the only reason this is a check and
        not a sweep note: a file carrying `SLOT:` at all is a file where the
        collision can bite."""
        for unit in UNITS:
            if not self.carries_both_senses(unit):
                continue
            text = collapsed(shipped(unit))
            assert "collision" in text, unit
            assert "venue back-matter field" in text, unit
            assert "heading tree" in text, unit

    def test_the_units_that_cannot_be_bitten_are_the_two_without_annotations(self):
        """Stated rather than skipped. `review-paper` and `wayfinder` use only
        the heading-tree sense, so they owe no qualification — and if either
        ever gains an annotation brace, the test above starts applying to it and
        this one says why."""
        exempt = [unit for unit in UNITS if not self.carries_both_senses(unit)]

        assert exempt == ["wayfinder", "review-paper"]


class TestTheTierTwoInvariantsHaveOneSet:
    """The list has two owners, forced rather than chosen: `write-paper` states
    it as construction rules, and the Craft axis is specified to receive it, so
    `review-paper` restates it in review-facing form. A skill may not read
    another skill's directory, so there is no third place to put it. Same shape
    as the rationale-leak duty, and the same drift risk — two copies that can
    disagree silently."""

    # Each invariant keyed by the phrase both copies share. The wording around
    # it differs by role on purpose: one binds the sentence being written, the
    # other binds the fix being recommended.
    SHARED = (
        "unconditional transform over finished prose",
        "Subordination must remain available",
        "the actor is load-bearing and hidden",
        "Interpretation never precedes the result it interprets",
        "may open by *using* what came before",
    )

    # The one asymmetry, and it is specified: a child slot partitions by an
    # object or a procedure and never by a claim, enforced at planning where
    # the child headings are chosen. There is no review-facing form of a rule
    # whose surface never reaches a draft.
    PLANNING_ONLY = "partitions by an object or a procedure, never by a claim"

    def test_both_owners_carry_every_shared_invariant(self):
        owned = collapsed(section_of(shipped("write-paper"), "## Craft invariants"))
        restated = collapsed(
            section_of(shipped("review-paper"), "#### The Tier 2 invariants")
        )

        missing = {
            (invariant, where)
            for invariant in self.SHARED
            for where, text in (("write-paper", owned), ("review-paper", restated))
            if invariant not in text
        }

        assert missing == set()

    def test_neither_copy_carries_an_invariant_the_other_does_not(self):
        """The set equality, which is the actual drift guard: a sixth invariant
        added to one copy fails here even though every existing assertion still
        passes."""
        owned = bullet_labels(shipped("write-paper"), "## Craft invariants")
        restated = bullet_labels(shipped("review-paper"), "#### The Tier 2 invariants")

        assert len(restated) == len(self.SHARED)
        assert len(owned) == len(self.SHARED) + 1

    def test_the_one_asymmetry_is_the_planning_time_invariant(self):
        owned = collapsed(section_of(shipped("write-paper"), "## Craft invariants"))
        restated = collapsed(
            section_of(shipped("review-paper"), "#### The Tier 2 invariants")
        )

        assert self.PLANNING_ONLY in owned
        assert self.PLANNING_ONLY not in restated

    def test_the_asymmetry_says_where_it_binds(self):
        """What makes it an asymmetry rather than a gap. Without the clause
        naming planning time, the missing review-facing copy reads as an
        omission and the next edit adds it."""
        owned = collapsed(section_of(shipped("write-paper"), "## Craft invariants"))
        clause = owned[owned.index(self.PLANNING_ONLY) :]

        assert "binds at planning time" in clause

    def test_the_transform_ban_agrees_with_itself_inside_the_owning_skill(self):
        """`write-paper` states the transform ban twice — once as a
        construction rule that binds the sentence being written, once as the
        Tier 2 invariant it is. The spec fixes both, so this is a third copy of
        one fact and the only one the cross-file assertion above does not
        reach. Found by the mechanism sweep, which is the whole reason the
        sweep is not optional."""
        write_paper = shipped("write-paper")
        stated = [
            statement
            for statement in statements(write_paper)
            if "unconditional transform over finished prose" in statement
        ]

        assert len(stated) == 2
        for statement in stated:
            assert "reading what that construction was doing first" in statement
            assert "find-and-replace" in statement

    def test_both_copies_say_the_tier_is_not_overridable(self):
        """The property that made them Tier 2. A copy that lost it would let a
        `## Style` key switch off an invariant, which is the configuration
        failure the tier split exists to prevent."""
        assert "not overridable by `## Style`" in collapsed(
            section_of(shipped("write-paper"), "## Craft invariants")
        )
        assert "Not overridable" in collapsed(
            section_of(shipped("review-paper"), "#### The Tier 2 invariants")
        )


class TestNoHouseStyleShipsInAnySkillFile:
    """Supersedes `test_style_stanza.py`'s single-file guard, which asserted
    this of `write-paper` alone. The leak is not particular to the skill that
    owns the schema: `review-paper` derives the effective stanza and
    `assemble-paper` reads `terms` from it, so a filled value in either installs
    the same house style with the authorship filed off."""

    def test_no_unit_carries_a_filled_style_key(self):
        filled = {
            (unit, key, value)
            for unit in UNITS
            for key, value in FILLED_KEY.findall(shipped(unit))
        }

        assert filled == set()

    def test_the_key_set_has_exactly_one_home(self):
        """`write-paper` names the closed set because it ships the schema. No
        other skill file may, or the set has two copies that can disagree."""
        naming = {
            unit
            for unit in UNITS
            for key in ("active-we", "plain-words", "spelling-variant")
            if "`%s`" % key in shipped(unit)
        }

        assert naming == {"write-paper"}
