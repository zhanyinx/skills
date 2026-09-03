# `briefs/<unit>.md` — the two formats

A brief is what one drafting session is told about the unit it is about to write. There is **one
brief per unit** — *section* here means *unit*, one top-level slot and its subtree — and it is 1:1
with the unit's rung, its `draft` ticket and its word budget, the same four-way cardinality
everything else in this pipeline keys on.

It is written by the unit's **brief planning ticket**, which the ladder ticket blocks: a brief
cannot be written against a rung that does not exist. `write-paper` reads it and never writes it.

> **The brief shrinks by relocation, not by compression.**

Every fat part of a brief already has a home some other artifact owns. Framing rules belong in the
map's `## Style`; cross-unit dependencies *are* the ladder's debt edges and the draft map's
blocking edges, recorded once there; a constraint's **defence** stays in the planning ticket; tier
definitions and per-metric explanations are **pointers** to the sources. A brief gets fat by
re-transcribing the very sources it cites, and a fat brief is a brief a drafter can walk one bullet
per paragraph.

`render-paper` **parses** this file — the overlap instrument measures the prose against it — but
does not own the format. What the renderer fixes is the six zone headings below and nothing else,
so a brief that renames a zone is reported as an unparsed zone rather than passing in silence.

## The axis — which of the two formats

The split does **not** run on "argumentative versus not". It runs on **whether the unit opens a
debt**, which is computable from the ladder rather than from a judgement about the unit's
character:

| the unit | its brief |
|---|---|
| **originating** — opens a debt the next unit inherits | **argument brief**, whose reader-facing zone is `## Argument` |
| **non-originating** — closes a debt, restates a rung, or inventories | **inventory brief**, whose reader-facing zone is `## Inventory` |

Reading it off the ladder keeps every unit attached to the spine, so the debt-precedence check
needs no class of unit it must skip. It also refuses the wrong intuition: a self-contained figure
legend carries take-homes because the venue requires them, so *"non-argumentative"* is simply the
wrong word for it.

The two formats **share four of their five zones**, so there is one artifact to learn rather than
two — and a unit that is both originating and inventory-carrying is expressible, by carrying both
reader-facing zones.

## The file

Six `##` zones, and **exactly one of them is reader-facing**: the only zone whose content may
legitimately appear in the drafted prose. Every other zone is instruction or bookkeeping **by
virtue of where it sits** — positional separation, no marker strings, because marker-based
stripping is what failed before.

| zone | reader-facing | what it holds |
|---|---|---|
| `## Argument` | **yes** | the rung's `establishes`, decomposed into at most three propositions |
| `## Inventory` | **yes** | the facts and constraints the unit must convey, as items |
| `## Must not claim` | no | the constraints, **without their defence** |
| `## Sheds` | no | content explicitly leaving this unit, and where it goes |
| `## Verify before prose` | no | what the drafter must confirm before writing it |
| `## Sources` | no | pointers to the evidence base, never a transcription of it |

An argument brief carries `## Argument`; an inventory brief carries `## Inventory`; both carry the
other four. A brief with neither reader-facing zone has nothing to measure the prose against, and
is reported as such.

### The header line

Above the first zone, on one line: the **ladder line**, then the **budget**.

```
Rung: R4 of 5.                                  <- originating
Closes: claim A's reproducibility debt.         <- non-originating
Restates: R4 (two-metrics-two-jobs).            <- non-originating
```

**The relation cannot be nothing.** A unit that closes a debt invisibly is a unit the precedence
check reports as never closing it — a false failure on the paper's load-bearing claim, which is
worse than no check at all. And `Restates:` earns its own relation because a restating unit must
not *establish*: a legend is the one place a new claim can enter a paper without ever being
reviewed as argument, since nobody reads a legend as part of the ladder. `Restates: R4` makes its
items checkable against R4's `establishes` instead of free-floating.

An originating unit that also closes an inherited debt states both edges as `Closes:` / `Opens:`
lines closing its `## Argument` zone. Those lines are the relation, not a proposition: they are
excluded from the proposition count and from what the overlap instrument measures.

### `## Argument` — at most three propositions

> The rung's `establishes`, decomposed into **at most three propositions**, phrased as **what the
> reader must end up accepting** — never as sentences that could be dropped into the draft as-is.
> The count must be **strictly below** the unit's paragraph budget.

Under-provisioning forces synthesis; over-provisioning forces undocumented selection. Give a
drafter more items than it has room for and it drops some silently — measured once at 2,767 words
down to 584, with a whole Limitations block gone and nothing saying so. Being strictly below the
paragraph budget makes a one-proposition-per-paragraph walk **arithmetically impossible**, so the
session has to build connective and evidential structure to reach the budget.

A single short prose statement of the argument instead of a list was rejected: the leaks arrive by
near-verbatim transcription, and argument-shaped prose in a brief is *more* liftable than a list,
not less.

### `## Inventory` — items, never phrasings

> The facts and constraints the unit must convey, **never a phrasing of them.** A finished caption
> title is banned from the brief outright.

This is the argument zone's anti-liftability principle transposed from propositions to facts, and
the same cut `## Must not claim` makes between a constraint and its defence. The evidence is a
legend draft that ran to 1,139 words against its own brief's 220–300 target, and overran **by
transcription**: its brief supplied draft captions, labelled *"interpretive, human to refine"*, and
the draft lifted their titles verbatim. That brief's defect was never a missing rung. It was a
draft in disguise.

**The item ceiling is structural, not numeric:** **one item per real-world object being
inventoried** — one per panel, one per venue-mandated field, one per released artifact. An item not
indexed by such an object is not inventory and belongs in one of the other four zones. This is why
a figure with roughly twenty-five listed items collapses to four: twenty-one of them were never
inventory. The argument zone's ≤3 cannot be transplanted here — a figure genuinely has four panels,
and a cap on reality is a cap that gets ignored.

#### For a figure legend, this zone relocates

**A legend's panel list is authored at planning time, in the legend file's own declaration block**,
by the legend's brief ticket. The legend's *draft* ticket writes prose around a block it **may not
reorder**; reordering it is a skeleton amendment, escalated to the planning ticket.

The reason is sequencing, and it is the direct cause of a measured defect: a real manuscript
drafted all seven body sections before all four legends, with roughly **38 reader-facing panel
references written before any legend existed**. A panel name minted by the legend's *drafter*
arrives too late for every unit that needs it, whereas the legend **briefs** already sit before the
body drafts. The cost is accepted knowingly — the render must parse legend files to resolve panel
names, so a legend is no longer purely prose.

**For a non-figure inventory — an availability statement, a venue's back-matter fields, a released
artifact list — `## Inventory` stands exactly as written above**, because those items have no other
home.

### `## Must not claim` — the constraint, never its defence

The constraint survives; the argument for it stays in the planning ticket. *No p-value* is a
constraint and belongs here. *"3-vs-3 cannot reach significance and a test is off-framing"* is its
defence, and a defence in a brief is a planning rationale one transcription away from reaching the
reader as a claim.

### `## Sheds` and `## Verify before prose`

Both stay as lists. Neither is reader-facing, so neither can become a paragraph.

**`## Verify before prose` has a defined exit:** anything the drafter cannot confirm becomes a
`{{ ! … }}` annotation in the working draft, carrying the gate bit. It does not become a
plausible-sounding placeholder, and it does not quietly go unwritten.

### `## Sources`

Pointers — ADRs, a context file, a prior-work summary. The drafting session reads the sources its
own brief cites. Restating a source's content here is how the brief got fat in the first place.

## The word budget

**One unit-level word budget. No sub-allocation.** A per-block allocation is a layout instruction
wearing a number: it names the containers and their sizes, and the drafter fills them in order.
**Children get no budget at all**, so a per-block allocation has nowhere to be written —
`Fig 2 ~800 / Fig 4 ~1,200 / Limitations ~500` is inexpressible, by construction.

The **paragraph budget is derived**, roughly words ÷ 150, and it exists **only** as the denominator
for the ≤3 proposition ceiling and for the paragraph-order check. **It is never a target**, because
a target paragraph count is itself a layout instruction. It is never written into the brief.

For a **non-originating** unit the derived paragraph budget loses both of those jobs, so an
inventory brief carries the unit-level word budget and nothing else.

The document-level limit that per-unit budgets are allocated *from* lives in `skeleton.md`. **The
skeleton names the total; the brief spends it.**

## What a brief may not contain

- **No paragraph plan.** No layout, no block list, no "two result blocks and a shared tail". This
  is the literal string that once leaked into drafted prose as narration of its own structure.
- **No per-block word allocation**, per the section above.
- **No mandated move sequence** and no mandated transition sentence. Which units reach back is
  decided by the ladder's debt edges, not by a template.
- **No template sentence spine.** A literal sentence the writer is told to fill and use is the same
  object the items-never-phrasings rule bans. The field *values* survive as items; stringing them
  into a sentence is the drafter's job. Venue-mandated exact sentences need no carve-out here —
  they are `SLOT` annotations in the working draft, which is where they already live.
- **No literal prose-level markup**, annotation markers included. A brief states what a passage
  must establish; it may not mandate a literal string that will appear in the drafted prose.
- **No cross-unit lines.** *"Depends on Implementation. Feeds the Fig 2 legend."* is deleted, not
  relocated: those are the ladder's debt edges and the draft map's blocking edges, and two
  artifacts recording one fact is how they drift apart.
- **No ban on paragraph-tracks-brief.** An instruction to the writer, written inside the brief, is
  exactly the class of content that leaked before. The rule lives in this skill, stated once, and
  is never re-transcribed into an artifact where it can be lifted. The format does not make the
  rule unnecessary — the overlap check is what enforces it — but the rule's home is the skill, not
  the brief.

## How the brief is measured

The ≤3 ceiling constrains the brief's **author**. What constrains the **drafter** is **overlap**,
because rationale leak, layout narration and bullet mirroring are one mechanism under three
headings: text transcribed near-verbatim from the brief.

`render-paper --check` reports it, and **the zone decides the instrument, not the unit**:

| zone | instrument |
|---|---|
| `## Argument` | any **substantial shared phrase** between brief and prose is flagged |
| `## Inventory` | **the finite-verb test** — a shared verbatim span is *expected* if it has no finite verb, *flagged* if it has one |

| shared span | verdict |
|---|---|
| `MIT`, `ghcr.io/org/tool`, `Nextflow ≥ 25.04.0` | expected — no finite verb |
| `tile-boundary crop, before/after BaSiC`, `scale bar required` | expected — no finite verb |
| `Illumination correction suppresses tile-boundary seams` | **flagged** — *suppresses* |
| `The source code is freely available under the MIT license at…` | **flagged** — *is* |

The finite-verb test does two jobs with one instrument: it catches the drafter transcribing *and*
the brief author slipping from an item into a phrasing, so **the format enforces itself** rather
than relying on an instruction written inside the brief.

No exemption is needed for `## Argument`: its propositions are required to be phrased as what the
reader must accept, so verbatim overlap with one **is** the defect rather than a false positive.
The exemption list is the map's `## Style` **terms** — populated by construction, since a style
stanza that mandates verbatim reuse of a term would otherwise fight the lint. **It covers terms,
never sentences**, and it is not extended to inventory items: a repo URL is not a style term.

Two further checks ride the same pass, **for originating units only**: single-sentence body
paragraphs are flagged, and paragraph order is checked against brief item order. **Both are
suspended for non-originating units**, because both invert there — order-tracks-brief is *mandated*
by a venue's field order and by panel lettering, and a panel caption is not a unit of argument.
Run them on a legend and they fire forever.

**Every one of these is a reported finding, never a gate.** Gating submission is reserved to the
annotation gate bit.

## Argument brief — the template

An example, not a default. Roughly 150 words, against an original of roughly 1,050 that specified
the same 2,500-word unit; the difference is entirely relocation.

```markdown
# Brief — Results and Discussion

Rung: R4 of 5.  Budget: ~2,500 words.

## Argument
Registration accuracy is credible on a metric VALIS does not control
(@fig:registration-accuracy).
Imaging-derived immune quantification tracks two orthogonal transcriptomic proxies
across six cases (@fig:proof-of-concept).
Closes: R3's accuracy debt.   Opens: generalisation beyond six cases -> R5.

## Must not claim
Any head-to-head performance win over <named tools>.
"First at WSI scale."  Any correlation coefficient, CI, or p-value.

## Sheds
Full per-arm table -> Additional files.  Competitor positioning -> Background.
Procedures -> Methods.

## Verify before prose
VALIS ANHIR "top-2 / first open-source" wording.
That high-accuracy + micro-on is the arm used for the concordance figure.

## Sources
ADR-0001, ADR-0002, ADR-0003, CONTEXT.md, prior-work-citation-landscape.md
```

## Inventory brief — the template

The same file with `## Argument` replaced by `## Inventory`, the other four zones unchanged.

```markdown
# Brief — Fig 2 legend

Restates: R4 (two-metrics-two-jobs).   Budget: ~220-300 words.

## Inventory
@fig:stage-graph      pipeline stage-graph: 5 DSL2 stages, DAPI as common anchor.
                      Schematic.
@fig:seam-crop        tile-boundary crop, before/after BaSiC. Constraint: a
                      side-effect of illumination correction, not a stitching
                      module. Scale bar required.
@fig:dapi-overlay     DAPI cross-panel overlay, before/after registration.
                      Constraint: same physical section, separately acquired.
                      Scale bar required.
@fig:dice-by-arm      per-arm Dice (+ VALIS-internal TRE), high/low x micro on/off,
                      plus rigid-only and no-registration baselines.
                      Direction: registration improves DAPI overlap over both.

## Must not claim
Any head-to-head against <named tools>.  "First at WSI scale."  MI (dropped).

## Sheds
Full per-arm table -> Additional files.  Performance -> Additional files.

## Verify before prose
Production arm = high-accuracy + micro-on.  Dice binarization rule (Methods).

## Sources
ADR-0001, CONTEXT.md, briefs/results-discussion.md
```

Note the panel **names**, not letters: declaration order determines the letters, and prose never
types one. **This is the legend case, so the four `@fig:` items above are authored in the legend
file's declaration block rather than here** — the zone is shown in place to fix the format. A
non-figure inventory keeps them in the brief.
