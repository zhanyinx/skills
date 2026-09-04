# `skeleton.md` — the format

The skeleton is the explicit file the render builds the document from. It fixes every heading, its
level, its text and its order, plus the roster of figures, tables and supplementary files. It is
produced by the skeleton planning ticket and is a settled input to every drafting session.

`render-paper` is its only parser, which is why the format is documented here, beside the code that
reads it.

**No skill owns this file.** A charting planning ticket creates it as its linked asset. A drafting
session may amend **its own slot only**. Anything that touches another slot, or the order or levels
of the tree, files a `task` ticket that blocks the draft ticket — see *Amendment* below.

## The file

Three sections. `## Document` and `## Slots` are required; `## Roster` may be absent when the paper
has no figures, tables or supplementary files.

```markdown
# Skeleton — <effort name>

## Document

| field | value |
|---|---|
| title | Registration accuracy in cyclic imaging |
| limit | 4000 words |

## Slots

| slot | level | heading | partitions-on |
|---|---|---|---|
| abstract | 2 | Abstract | |
| introduction | 2 | Introduction | |
| methods | 2 | Methods | |
| methods-imaging | 3 | Imaging | procedure |
| methods-registration | 3 | Registration | procedure |
| results | 2 | Results and discussion | |

## Roster

| kind | name | legend |
|---|---|---|
| figure | registration-accuracy | legends/registration-accuracy.md |
```

### `## Document`

Exactly two fields, both required, no others:

| field | what it is |
|---|---|
| `title` | the H1 text, and the only H1 the document has. It appears in no source prose. The **row** is required and its **value** is not: an empty title is a hole with the gate bit, never a parse error |
| `limit` | the document-level venue limit — a word or page count. A whole-document fact, and what per-unit word budgets are allocated *from*. Required, and not empty: a venue's limit is known before any prose is |

The title is a **field, not a unit**: no title rung, no title brief, no title slot. The abstract
keeps its unit. The planning ticket may leave the title unfilled and a later `task` ticket fill it,
because a title is the central claim compressed and is better written after the argument exists.

### `## Slots`

The table's **row order is the document's reading order**, and the skeleton is authoritative on it.
Reading order and argument order are different relations and may disagree — Methods sits last in many
venues but its results feed Results. Precedence goes to the skeleton, because venue structure is a
hard external constraint the argument cannot renegotiate. The claim ladder holds a veto over order,
expressed as an amendment request, never as a silent reordering.

| column | rule |
|---|---|
| `slot` | the slot id: lowercase letters, digits and hyphens. Unique across the file. This is what a source anchor names |
| `level` | the heading level, `2` or deeper. The first row must be level 2, and the tree may not skip a level |
| `heading` | the exact heading text the render injects. Never written into a source |
| `partitions-on` | **required on every child row**, and empty on every top-level row |

**Parentage is carried by level**, the way a heading tree carries it: a slot's parent is the nearest
preceding slot of a smaller level. A **unit** is one top-level slot and its subtree.

`partitions-on` names the object or procedure a child slot partitions on — `procedure`,
`pipeline stage`, `venue field`. It is required because a child slot must partition by an object or
a procedure and **never by a claim**: a claim is carried by prose motion, by opening and closing
debts, and giving a claim its own labelled box is the alternative to motion. Writing the object down
at planning time is where that choice is visible. The value is free text and is never compared
across siblings — a discipline-agnostic skill cannot enumerate the next field's objects, and
comparing free text would be a join key with no normalisation.

**There is no sub-heading budget.** No number is stored anywhere. The constraint on children is a
function of the ladder relation instead, and it is mechanical: see *The child-count rule*.

### `## Roster`

**Names only.** The roster maps name → legend file, and it carries no order of its own, no numbers,
no panel rows and no parent field. Legends are emitted in resolved-numeric order at render, so a
legend file needs no number in its own name. Numbering happens in the render, from first-mention
order, and never in the source.

| column | rule |
|---|---|
| `kind` | `figure`, `table` or `supplementary`. It fixes which word the reference renders as and which sequence it numbers in — so promoting a figure to supplementary is this one edit, at zero prose edits |
| `name` | the stable name prose refers to: lowercase letters, digits and hyphens. It describes the object's **content**; a name whose last hyphen-separated segment is a single letter is positional and a parse error |
| `legend` | the path to the legend file, required and not empty. The **file** may be written later; the row names where its `## Panels` block will be |

**Panels have no rows here, and that is what makes the roster stable under a figure split.** A
panel's name is declared in its figure's legend, so parentage is carried by containment: a reference
to a panel resolves through the legend and satisfies its figure's roster row. Splitting one figure
into two is therefore one roster line and two legends, at zero prose edits — see
[figures and panels](FIGURES.md).

A roster name **nothing in the document points at** is a hard error, and so is a name in prose that
is neither a roster name nor a declared panel. The roster is a manifest of *this document's*
objects, which is the whole difference from the bibliography, where over-provisioning is normal and
gets no check at all.

## What the skeleton does not hold

- **per-unit word budgets** — one budget per unit, and children get none, so a per-block allocation
  has nowhere to be written
- **citation anchors** and **the bibliography** — the bibliography is an author-owned declared input
  at its own path, `references.bib` at the paper root; see [the citation surface](CITATIONS.md)
- **the sheds list** — content explicitly leaving a unit

All four are brief contents. **The skeleton names the total; the brief spends it.**

## The source's side of the contract: anchors

A source carries **no headings at any level** — a heading typed into a source is a parse error, in
either markdown spelling (`## Imaging` or an underlined `Imaging` / `-------`), since it would render
as a heading the skeleton never declared. Inside a fenced code block nothing is parsed at all, so a
source may show anchor or heading syntax in a fence without using it. A source carries one anchor per
slot:

```markdown
<!-- slot: methods -->
```

The anchors are not typed by hand: `render-paper <source> --scaffold` seeds a source with every
anchor in a unit's subtree, in skeleton order, before the drafting session starts, and the session
writes only between them.

An anchor is an ordinary HTML comment, so it is stripped like every other comment and enters no
manifest — nobody owes an anchor. A comment whose first token is `slot:` is claiming to be an
anchor, and one that is not exactly `<!-- slot: <slot id> -->` is a **malformed anchor**: a parse
error, so that a mistyped anchor errors instead of silently vanishing under the comment strip.

A slot's prose is the text from its anchor to the next one. A **parent slot may bear prose**: its own
prose is exactly the text preceding its first child anchor. There is no way to express "parent prose
after a child", which is the same limitation Markdown and LaTeX already have.

Parent prose is **permitted, not owed.** Only a leaf slot owes prose, and a parent is finished when
its children are. Requiring an opening paragraph of every parent would make a unit that spends its
children manufacture a first child to hold it — `Overview`, `Summary` — which produces exactly the
stack of labelled blocks this design exists to prevent. An empty **leaf** is a different thing: it is
a hole with the gate bit set, and it is what makes the skeleton's slot list the completion checklist.

## The child-count rule

> An **originating** unit has **zero** children.

Computed from `skeleton.md` **plus** [`spine.md`](SPINE-FORMAT.md), so it fires the moment the ladder
exists, and no style preference may raise it. A unit that opens a debt must carry its argument in
prose motion; a stack of labelled boxes is what a reader meets instead of an argument. A
non-originating unit — one that closes, restates or inventories — may carry as many children as its
venue expects, which is why a Methods section's seven procedure headings are not a defect.

## Amendment — the locality test

The test is mechanically decidable from `skeleton.md` plus `spine.md`, so a drafting session never
has to judge whether its change is "big".

**Immediate**, and needs no ticket: adding a roster name only this unit references; adding a child
slot inside the amending session's own subtree. Re-run `--scaffold` after one: it is idempotent, so
it adds the new slot's anchor and moves no prose.

**Escalated to a `task` ticket that blocks the draft ticket:** reordering slots, changing an existing
slot's level, removing a slot, renaming a slot that other prose points at, a figure split another
unit references, reordering a legend's declaration block.

Because it is mechanical it is a check, and it prints as the **reported** `locality test` row:

```
  locality test             4 units, 6 slots, 2 cross-unit edges (abstract restates results; `D1` introduction→results)
```

The render never sees a proposed amendment, so what the row reports is what the two files fix before
one is proposed: **the tree an amendment would move**, and **the coupling** that decides which side
of the rule a move falls on. A unit's own subtree is its to amend; the tree's order and levels are
nobody's alone; and every edge leaving a unit — a debt it opens that another unit closes, a rung in
another unit it restates — is a tie an amendment cannot move on its own. The two lists above stay
the rule; the row is the paper's own numbers against it.

It **reports rather than gates**: a coupled argument is what a ladder *is*, not a defect in one.
