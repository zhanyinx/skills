# Figures and panels — the reference surface

`render-paper` is this surface's only parser, which is why it documents it — the same reason it
documents [`skeleton.md`](SKELETON-FORMAT.md), [`spine.md`](SPINE-FORMAT.md),
[the citation surface](CITATIONS.md) and [the annotation channel](ANNOTATION-CHANNEL.md).

**A drafting session names the thing it means; the render assigns the number or the letter.** A
number a session writes could be wrong-but-valid — pointing at a real figure that is not the one
meant — and no gate can catch that. Names remove the surface it needs.

## One namespace, one token class

```
@fig:registration-accuracy      a figure
@fig:dapi-overlay               a panel — the same syntax
```

A panel is not a new kind of object: **it is a figure that lives inside another figure.** So it is
referenced by the same token, looked up in the same table, and carries no syntax of its own.

**Parentage is carried by containment, never by syntax.** There is no `@fig:parent:panel` form and
no parent column in the roster. A panel's parent is the roster row whose legend declares it. This is
pandoc-crossref's own design — a subfigure is labelled and referenced identically to a figure — and
it is what makes the whole surface a thing an existing tool already resolves rather than an
invention.

Because parentage is containment, **a reference to a panel is a reference to the figure that
contains it**: it fixes that figure's number, and it satisfies that figure's roster row.

## Numbering

| class | resolved by |
|---|---|
| figures, tables, supplementary files | **first-mention order** in the assembled document |
| **panels** | **the legend's declaration order** — *not* first mention |

**The two rules are not unified, and the reason is physical.** A figure *number* appears nowhere but
the rendered text, while a panel *letter* appears in the rendered text **and in the artwork**.
First-mention lettering would mean that reordering two sentences silently invalidates the image —
and a render can renumber prose but cannot repaint a figure. The legend declares the figure's
composition, so its enumeration order *is* the layout order.

Each **kind** numbers in its own sequence, because a document numbers its figures and its tables
independently.

### The rendered forms

```
@fig:registration-accuracy   ->   fig. 1
@fig:dapi-overlay            ->   fig. 1 (a)
@fig:marker-schedule         ->   tbl. 1
@fig:power-analysis          ->   suppl. 1
```

These are pandoc-crossref's own spellings, taken rather than invented: the design rests on an
existing tool already resolving name to number, and a second spelling of the same relation is how
the two come apart. Which word a name takes comes from its **roster row**, never from the token — so
promoting a figure to supplementary is a one-line roster edit at **zero prose edits**, which is the
property names exist for. The venue's own typography is a downstream concern, exactly as the
citation style is.

A bracket group resolves **per key**, so a mixed `[@smith2020; @fig:dapi-overlay]` renders
`[1; fig. 1 (a)]`. The brackets are the source's own grouping and survive; a bare `@fig:name` takes
none, because `fig. 1` is already the whole rendered form.

## The roster

**Names only** — no order of its own, no numbers, **no panel rows and no parent field.** It maps
name to legend file, and it lives in [`skeleton.md`](SKELETON-FORMAT.md).

### The integrity check is symmetric, and the symmetry is the point

| direction | disposition |
|---|---|
| a name in prose that is neither a roster name nor a declared panel | **hard error, both modes** |
| a roster name nothing in the document points at | **hard error, both modes** |
| a declared panel nothing points at | **no check at all** |

Both halves are the same defect: **the emitted document is not the document the source describes.**
A name pointing at nothing is a reference to an object the document does not have, and a roster name
nothing points at is a figure that would be published and never discussed. Circulating damage is how
it spreads, so neither mode emits.

> **A figure roster is a manifest of this document's objects; a bibliography is a library, and
> over-provisioning is its normal state.**

That is why [the citation check](CITATIONS.md) has no second half and must not grow one. It is also
why a **declared panel** nothing references is not a problem: the roster carries no panel rows, so
there is no roster name left unreferenced, and a figure may legitimately hold a panel the prose
never calls out on its own.

**A panel reference satisfying its figure's row is containment, not a loosening of the rule.** The
rule is *a roster name referenced nowhere*, and a figure discussed through its panels is discussed.
Without that reading the check would hard-error the normal case: in the corpus this was calibrated
on, prose referenced panels almost exclusively — roughly 38 panel references were written before any
legend existed — so a figure named only through its panels is what a real paper looks like.

The row is **`slot / roster integrity`**, and it is **whole-document only**: *a roster name never
referenced* is undecidable from one unit's source, because the reference may live in any other unit.

## The legend's declaration block

**A legend is no longer purely prose — it carries a declaration grammar**, and it is the first draft
artifact with machine-read structure. The block is one section, one entry per panel, and **the entry
order is the lettering**:

```markdown
# Legend — registration accuracy

Registration holds every round in one frame, and the per-arm agreement is what the accuracy claim
rests on.

## Panels

@fig:dapi-overlay     DAPI cross-panel overlay, before and after registration. Constraint: the
                      same physical section, separately acquired. Scale bar required.
@fig:dice-by-arm      per-arm Dice, high and low accuracy against micro on and off, plus the
                      rigid-only and no-registration baselines.
```

| rule | why |
|---|---|
| an entry opens `@fig:<name>` at the **start of its line** | the entry order is the lettering, so an entry has to be findable without reading its prose |
| a continuation line is **indented** | a description is free text and wraps over as many lines as it needs |
| `## Panels` holds declarations and **nothing else** | a column-zero line that is not a declaration is a parse error, so a paragraph cannot drift into the block and shift the letters |
| a name is declared **once**, in **one** legend | one flat namespace: a name belongs to exactly one object |

**The block's shape is the brief's `## Inventory` zone's own** — `@fig:name` at column zero, the
description free text beside it — because for a figure legend that zone *relocates* here rather than
being rewritten. The **heading** is `## Panels` and not `## Inventory`, and that is deliberate: one
heading parsed by two grammars in two files, strict here and loose in a brief, is a grammar that can
disagree with itself, which is the defect the single-implementation rule exists to prevent. A reader
who knows the brief's inventory zone still recognises the block on sight, because the entries are
identical.

**Legends are not yet emitted into the document.** The render reads a legend for its declaration
block and nothing else. Emitting the legends in resolved-numeric order is a separate duty, and it
needs somewhere in the skeleton to put them.

**The block is authored at planning time**, by the legend's brief ticket, and **a `draft` session
may not reorder it** — reordering re-letters the artwork, so it is an amendment that escalates to a
`task` ticket. The reason it is planning-time is a real sequence: in the corpus this was calibrated
on, seven body sections were drafted before all four legends, with roughly **38 reader-facing panel
references written before any legend existed**. A panel name minted by the legend's *drafter*
arrives too late for every unit that needs it; the legend **briefs** already sit before the body
drafts.

**Absence is a legal state, twice over.** A legend file not written yet, and a legend with no
`## Panels` block — a figure or table with nothing to letter — both declare no panels. The block is
required by the panel *references*, not by the renderer, which is the same reason a missing
`references.bib` is not a parse error either.

## The parse errors

Outside comments and fences, **prose may not spell a figure number, a panel letter, or a name that
says where a panel sits.** Each is a parse error: exit `3`, nothing ran, no table.

| refused | example |
|---|---|
| a parenthesised letter or letter-range | `(a)`, `(c–d)`, `(a, b)` |
| a `Fig`-plus-number form | `Fig 2`, `Fig. 4b`, `Figure 3`, `figs 1` |
| a positional name, in either case | `@fig:panel-b`, `@fig:panel-B` — any name whose last hyphen-separated segment is a single letter |

Three shapes, one principle: **the source cannot express a stale identifier.** The parenthesised
letter is the one worth stating separately, because nothing else refuses it — it is syntactically
clean prose, and it sits in the artifact a figure split re-letters *first*.

A positional name is a panel letter wearing a name, so it is refused **wherever a name is written**:
in prose, in a legend's declaration block, and in a roster row. One predicate, three call sites,
because a rule about what a name may say cannot be allowed to disagree with itself. **Either case**,
because those three sites do not agree on case — a roster name and a panel declaration are lowercase
by their own grammar, and a reference is not — and a lowercase-only rule would let `@fig:panel-B`
through, silently at `--section`, where the roster row that would otherwise catch it is out of
scope.

### What the numbered form deliberately does not cover

**The `Table`- and `Suppl`-plus-number spellings are not refused**, even though the roster addresses
all three kinds through one namespace. `table` and its relatives are ordinary nouns that take a
measurement — *a table 1 mm thick*, *the water table 12 m below* — so a refusal over them fires on
prose that references nothing, and a gate that fires on clean prose is the noisy gate this whole
design is built against. `fig` and `figure` before a numeral have no such reading.

The defect is not lost with them. A table referred to by literal is **a roster name referenced
nowhere**, which is a hard error in both modes. It is reported one row later and less precisely, and
that is the price of a pattern with no false positives.

### Why the author-facing channel is exempt

The refusal reads reader-facing prose: every comment **and every brace** blanked. A comment never
reaches a reader, so nothing in one can be a stale reader-facing identifier. A brace's label is
different — it *is* substituted into the render — but only ever inside a gap token, `⟦HOLE: …⟧`,
which carries the gate bit and so cannot be submitted while it is open. `{{ ! redo (c–d) }}` puts a
panel letter in front of a reader of a *circulated draft*, conspicuously unfinished and impossible
to mistake for a resolved reference.

Refusing braces would refuse the one channel that exists for naming a reference the author cannot
yet make — which is the same reason the bare-hole lint reads that channel too: a hole is *allowed*
to be named there.

It is a **refusal, not a finding**, for the reason every refusal here is one: a finding is what
returned CLEAN over 98 em dashes. And it **cannot be configured per effort** — a configurable
refusal pattern is the override these rules exist to prevent, wearing a config file.

### Why it is affordable — the calibration

Measured over the calibration corpus, of the parenthesised-letter occurrences in reader-facing
prose, **21 of 21 were panel references or declaration markers, and zero were enumerators.** All
**37** legitimate letter-enumerator uses sat inside comments, which the refusal exempts by
construction — a comment never reaches a reader, so nothing in one can be a stale reader-facing
identifier.

So the cost is **stated rather than discovered**: a genuine letter enumerator cannot be written in
reader-facing prose. Where an author wants one, a comment carries it, or the alternatives become
full clauses — which is the better sentence anyway. A name whose last word is a single letter
(`@fig:vitamin-d`) is refused with it, and takes one more word (`@fig:vitamin-d-response`).

### It is not a gate

`--circulate` always succeeds over a *live* paper, and a parse error does not contradict that. An
open annotation never blocks circulation — it renders as a token and lands in the manifest. A parse
error governs **malformed source**: text the render cannot parse, so it has no behaviour and no gate
bit to honour. It sits in the same category as an unclosed brace.

## At `--section` granularity, nothing resolves

Every figure and panel token is **left unresolved and visible**, and **no placeholder form is
invented**. Both numbering rules read the whole document — first mention is document-wide, and a
legend is a whole-document input — so a section render that guessed would be guessing. The token
comes out as it went in.

## The figure split — the event this was confirmed on

A planning roster's Fig 2 covered a pipeline and the accuracy of the registration stage inside it.
During drafting it split in two.

- Under names the split is **a one-line roster edit**: one roster row becomes two, and one legend
  becomes two.
- Document-wide first-mention order reproduces the post-split numbering **exactly, at zero reference
  edits.**
- The two registration panels move to the new legend and become `(a)`, `(b)` **by position, at zero
  prose edits.**

A figure **split** is a thing a renderer that only renumbers forbids outright. And the split caught
a defect neither an audit nor a review pass found: afterwards, the frozen draft's `Fig 2c–d` **did
not dangle — it changed meaning.** The literal still resolved, to the wrong object, silently. That
is the failure a dangling-reference check cannot catch, and it is why the literal is a parse error
rather than a checked value.
