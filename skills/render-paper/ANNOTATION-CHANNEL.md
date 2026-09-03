# The annotation channel — the format

The annotation channel is how an author writes author-facing content into the source and knows
exactly which of it the reader will see. A missing value, a venue field, a private note, a
reviewer's finding — each is written in one of two syntaxes, and the syntax decides what the reader
gets.

**The invariant: all author-facing content lives in the marked channel.** An unmarked author-facing
sentence is a defect, not a style choice.

`render-paper` is the channel's only parser, which is why the format is documented here, beside the
code that reads it.

## Two syntaxes, split by visibility

| syntax | behaviour | the render |
|---|---|---|
| `{{ … }}` with no `SLOT:` | `HOLE` | **must** appear — a conspicuous, uniform, greppable token |
| `{{ SLOT: … }}` | `SLOT` | **must** appear — a visible placeholder |
| `<!-- … -->` | `SILENT` | **must never** appear — every comment is stripped |

**The strip is by syntax and by class, never by a marker string.** Every HTML comment goes, and the
renderer emits no comment of its own, so there is no such thing as a comment the render preserves.
That is structural, not a lint: the 2,264-character leak this design was written against was a
generator emitting its own comments and cutting at a literal marker string.

**Parsing is span-based, never line-anchored.** An annotation may wrap any number of lines: 13 of
the 30 real annotations in the calibration corpus did, and one ran over six lines. A line-anchored
parser is the thing an implementer assumes away.

## The brace grammar

```
{{ [!] [SLOT:] [@owner] <label> }}
```

- **`!`** — the **gate bit**. Present: blocks `--submit`. Absent: does not. Always leading.
- **`SLOT:`** — marks a venue slot: uppercase, no space before the colon. Absent: it is a `HOLE`.
- **`@owner`** — optional, free text, defaults to `@author`.
- **`<label>`** — a **noun phrase naming the missing value**, and nothing more.

The three prefixes appear **once each, in that order**. A remainder still carrying one of them is a
parse error rather than a label that happens to start with `!`, because that reading would silently
lose the bit that decides whether the paper can be submitted.

Braces rather than brackets: brackets are not recognisable as a class — the calibration corpus held
40 citation spans against 30 annotation spans, and `{{`/`}}` occurred in it zero times.

### `HOLE` is the default; `SLOT` is marked

A bare brace is a `HOLE`. `SLOT:` marks the rare case — 6 of 30 in the corpus, all of them venue
back-matter. **The render warns when a bare brace stands alone in its own block**, because on the
whole corpus that shape is always a slot. A warning and not an error: position is strong evidence,
not the definition.

### The brace names the value; reasoning goes in a keyed comment

Illegal inside a brace: a second sentence, an imperative, and reasoning grafted on after an em
dash. Reasoning moves to a comment **adjacent to the brace, keyed by repeating the label**:

```markdown
…generated with {{! the production registration arm }}.
<!-- {{the production registration arm}}: VALIS accuracy preset + micro-registration state
     used for the accuracy figure. The pipeline ships medium-preset / micro-off, overridable
     per run; the figure's invocation is not committed. Reconcile before filling this in. -->
```

That is a real 547-character annotation that became a paragraph of editorial reasoning mid-Methods.
**Its actual hole is four words.**

**A label over 80 characters warns and never refuses.** A hard cap was rejected: it over- and
under-fires at once, refusing a legitimate 110-character noun phrase while passing a 90-character
imperative.

### Label normalisation

The label is the **join key** between a brace and its reasoning comment, and the grammar fixes token
order but not whitespace. Drafting produced two spellings of one label without intent —
`{{! winning registration arm }}` in the prose against `{{ ! winning registration arm }}` in the
comment — which orphaned the reasoning **silently**.

> **Labels compare after collapsing internal whitespace, trimming, and stripping the `!`, `SLOT:`
> and `@owner` prefixes.**

A keyed comment matching no brace **warns**; it never vanishes.

### No kind vocabulary

The taxonomy is **the two axes and nothing else** — render behaviour, and the gate bit. There is no
kind enum: the nine wild forms the corpus improvised encode nothing the axes miss (`confirm` and
`supply` collapse into `SILENT` and `HOLE`). The one dimension the axes do not carry is **who
resolves it**, which is the free-text `@owner`, and its payoff is that grouping the manifest by
owner makes it **sendable**.

## The comment grammar, and what enters the manifest

Every comment is stripped. Three different things live in comments, and the manifest has to tell
them apart:

> **A comment enters the manifest if and only if its first non-space character is `!` or `@`.**

```markdown
<!-- !@author unverified: the six paired fractions are not in any committed table -->
        → a SILENT annotation. Gates. In the manifest, under @author.
<!-- @author waiting on the IRB number before submission -->
        → a SILENT annotation. Does not gate. In the manifest.
<!-- {{the production registration arm}}: …reasoning… -->
        → reasoning keyed to that brace. Not a manifest entry of its own.
<!-- superseded the FlowPath paragraph, see draft-map -->
        → an ordinary author comment. Stripped, tracked nowhere.
```

**Author workflow state lives here** — the "remains a submission-readiness item" sentence is an
`@owner` comment, never reader-facing prose.

**Three things are ordinary comments, deliberately** — stripped, and tracked nowhere: the **rung**
comment, the **`<!-- obj: … -->`** objection note, and the **section anchors**. A rung is not a gap;
nobody owes it; and it must never appear in a list of outstanding work sent to a co-author.

## The verify flag

A verify flag is **`SILENT` plus the gate bit**, and nothing else. Every review axis reads the
render, but a `SILENT` annotation emits nothing — and a comment enters the manifest only if it
starts with `!` or `@`, so a plain verify note is in **neither the render nor the manifest, invisible
twice over.** The fix follows from what a verify flag means: an unverified claim is exactly what must
not reach a journal, so a verify flag carries `!`.

```
verify flag  ≡  SILENT + `!`
    render   → emits nothing, by design
    manifest → listed, because of the bit
    --submit → refuses while any is open
```

## The manifest

Recomputed from the source at **every render**, so it cannot go stale, and printed on stderr under
every mode — `--check` included, because the review's first phase is `--check`.

```
  manifest — 10 open annotations, 3 carrying the gate bit
  → f(source), recomputed at every render; deletion is the only closure

  @author
    !  HOLE    MANUSCRIPT.working.md:28  the production registration arm
       reasoning: VALIS accuracy preset plus micro-registration state…
    !  HOLE    MANUSCRIPT.working.md:36  best-arm Dice
       direction: `raised` is committed before this value exists
       SLOT    MANUSCRIPT.working.md:50  data availability statement

  @lab-imaging
    !  SILENT  MANUSCRIPT.working.md:32  unverified: the six paired fractions are not in any…
```

**Grouped by `@owner`**, which is what makes it sendable: an experimentalist is handed their own
group and nothing else.

**It is printed whether or not it is empty.** An absent manifest reads as nobody having looked, and
it is an absolute input to a judgement axis that has no previous manifest to diff against — so it
**enters whole, never diffed**, including at `--section` granularity, where the *gate* is scoped the
way every other check is but the manifest is not.

### The directional clause

Six of seven gating annotations in the corpus sat under a committed **directional** word written
before the value existed — *"raised Dice to `{{! best-arm Dice }}`"*. The gate stops submission, but
nothing stops the author filling a value that **contradicts** the direction, and at that moment
deletion closes the annotation and the obligation vanishes.

> **A directional claim resting on an open `HOLE` inherits that hole's gate bit and one manifest
> line naming the direction.**

So the direction is named while the hole is still open, on the hole's own entry. It **inherits** the
bit and adds none: an ungated hole under a directional word gets the line and still does not block
submission. The word list is short, dumb and conservative, the way the residue lints are, so the
renderer stays paper-agnostic.

## Creation rights

| unit | may create |
|---|---|
| `write-paper` | `HOLE`, `SLOT`, `SILENT` |
| `review-paper` | **`SILENT` only** |
| `assemble-paper` / the render | **none** |
| the author, by hand | anything |

`review-paper` writes its findings back into the working source, but only as `SILENT`. **Because
`SILENT` emits nothing, a review is structurally incapable of changing what the reader sees** —
which is what makes it safe for a judging skill to write into the artifact it judges. It is also why
the editorial pass cannot be folded into `review-paper`: cross-section de-duplication *is a cut*, and
a `SILENT`-only skill cannot make one.

The render creates none. It renders a gap as a token; it never writes one into the source.

## Deletion is the only closure

Resolving a `HOLE` or a `SLOT` means **substituting the real value**. Resolving a `SILENT` means
**deleting the comment**. There is no `RESOLVED` marker and no tombstone.

```
BEFORE   raised Dice to {{! best-arm Dice }} from {{! rigid-only Dice }}.
AFTER    raised Dice to 0.89 from 0.71.
```

Two load-bearing consequences: **the manifest is `f(source)`**, recomputed at every render, so it
cannot go stale; and **git is the audit trail** — `git log -S'best-arm Dice'`. The corpus's own
`RESOLVED` convention died at four uses, which is the empirical basis, and it is why no entry carries
a history field.

## The tiers

| the source says | tier |
|---|---|
| a malformed or unclosed brace, an unmatched `}}`, a brace naming no value, prefixes out of order, a near-miss `SLOT:` | **parse error**, exit `3` |
| an open annotation carrying the gate bit, in any behaviour | **submit-gating**, exit `1` |
| a label over 80 characters, a bare brace block-alone, a keyed comment matching no brace | **warning**, exit code untouched |

**An open annotation never blocks `--circulate`** — it renders as a token and lands in the manifest.
A malformed brace is a different thing: it is not an open gap the render is declining to gate on, it
is text the render **cannot parse**, so it has no behaviour and no gate bit to honour. That is why
the two sit in different tiers, and why "`--circulate` always succeeds" and "a malformed brace is a
parse error" are not in conflict.

**A gap is never silently stripped.** Strip the token and the sentence is ungrammatical; drop the
clause and an unsupported assertion ships and the author never learns it vanished.

## Where nothing is parsed

Inside a fenced code block, nothing is parsed at all — not a brace, not a comment, not an anchor,
not a heading. A source showing annotation syntax in a fence is showing it, not using it.
