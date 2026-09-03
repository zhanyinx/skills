# The three map sections — `## Style`, `## Spine`, `## Skeleton`

A wayfinder map is domain-agnostic: it names no academic-writing section and owns no template for
one. What it owns is the **requirement** that a map instantiates every `##` section the domain
skill its `## Notes` names declares. **This skill is that domain skill for academic writing**, and
these are the three sections it declares. It ships all three together because it is the only unit
that reads all three — the style stanza at session start, the ladder as the rung it is drafting
against, the skeleton as the tree it writes anchors into.

> **The template lives with its reader.** `wayfinder` names no domain section; `write-paper` ships
> the three map-section templates; `render-paper` documents the two file formats.

**A map missing a section this skill reads is a charting defect, not a drafting one.** Leave a
declared section **empty** rather than omitting it: empty is a state a reader can announce, absent
is not. This is not hypothetical — a framing rule once sat unread in a map's `## Notes` while three
skills looked for it under `## Style`, and the frame it banned was denied seven times in seven
independent sections with nothing detecting it.

## Two rules that bind all three

**Inline if short, link if long.** Each section carries the one or two facts a session needs in
order to orient, inline, plus a link to the mutable file that holds the detail. The map is an
**index**, not a store.

**The map records decisions, never recomputable state.** A gate verdict is `f(source)` and
re-runnable in a second, so it is not recorded in the map at all. Asserting a *document property*
in one — *"anchors ↔ roster 1:1"*, *"all references resolve"* — is banned outright: a real map
recorded both as settled fact and both were false.

**All three are omitted when the effort has no drafting tickets.** Their absence therefore means
*"not a drafting effort"*, never *"no preferences"* and never *"no structure"*.

## `## Style`

**Keyed deltas against the drafting skill's key set, plus additive prose.**

That sentence is the whole of the template's own instruction, deliberately. The key set, its value
domains, its tiers and its composition rules live in [`STYLE-STANZA.md`](STYLE-STANZA.md), the
schema this skill ships, in exactly one place; enumerating them here would put an academic-writing
vocabulary into a map template and give one fact two homes. An effort wanting a preference outside
the key set writes prose, which is advisory to the drafter and not machine-read.

`## Style` is where framing rules live — global to the effort, never per-unit. They sat in briefs
only because there was nowhere else to put them, and a framing rule in a brief is one
transcription away from reaching the reader.

```markdown
## Style

<keyed deltas against the drafting skill's key set, one per line>

<additive prose: framing rules, venue notes>
```

The section may be present and **empty**. An empty `## Style` and an absent one are different
states and a drafting session announces which it found.

## `## Spine`

**The central claim, inline. The ladder, by link.**

```markdown
## Spine

<the central claim, in one or two sentences>

The claim ladder: [`spine.md`](path/to/spine.md) — mutable; one drafted actual per rung, always
current.
```

The full ladder inline was rejected twice over: it would make the map a store rather than an index,
and every draft resolution would be editing the same block concurrently. The ladder holds exactly
**one actual per rung**, overwritten rather than appended, and git is the trail. A ladder carrying
superseded actuals beside current ones forces every downstream drafter to work out which line is
live.

No skill owns `spine.md`. A wayfinder planning ticket creates it as its linked asset; each `draft`
resolution updates its own drafted actual; a rung itself is amended by a `task` ticket.

## `## Skeleton`

**The venue's limit and the title, inline. The tree, by link.**

```markdown
## Skeleton

<venue>, <document-level limit>. Title: <the H1 text, or "unfilled">.

The heading tree and the roster: [`skeleton.md`](path/to/skeleton.md) — settled input; a drafting
session amends its own slot only.
```

The two inline facts are the ones a session needs before it opens a file: the limit is what
per-unit word budgets are allocated *from*, and the title's state says whether a `task` ticket is
still owed. **The slot table is never inlined** — it is the store failure again, and a drafting
session may amend its own slot, so an inline copy goes stale the first time one does.

The title may legitimately be unfilled. It is a skeleton field rather than a unit — no title rung,
no title brief, no title slot — and a later `task` ticket fills it, because a title is the central
claim compressed and is better written once the argument exists.

## What these sections do not carry

- **No per-unit word budgets.** Those are brief contents. The skeleton names the total; the brief
  spends it.
- **No sub-heading counts.** No number is stored anywhere: an originating slot has **zero**
  children, checked mechanically from the skeleton plus the spine, and every child row names the
  object it partitions on.
- **No restatement of the `draft` ticket type, the source and output file contract, or the drafting
  order.** Those are skill-level. A map that re-transcribes them has two artifacts recording one
  fact, and the copy is already the one that goes stale.
- **No gate verdict, and no assertion about the document's state.** See the second rule above.
