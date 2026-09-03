---
name: assemble-paper
description: "Stitch independently-drafted sections and figure legends of a manuscript into one continuously-readable document — resolving transitions, redundant seams, and voice/terminology drift between sections — without altering claims, evidence, or citations. Use once all section drafts exist and before the final /review-paper pass over the whole manuscript."
disable-model-invocation: true
---

Assemble the independently-drafted sections and figure legends of a manuscript into a
single, continuously-readable document — smoothing the seams between them without
touching what they say.

## Why this exists

`/write-paper` drafts one seam — a section or paragraph-cluster — at a time, deliberately:
each session sees only its own brief, which is what keeps drafting focused. The cost is
that no session reads the whole manuscript end-to-end, so sections can land with problems
that only exist *between* them: one section pre-summarizes what the next immediately says,
the same concept gets named two different ways in two sections, "as described above" points
at nothing once the final order is fixed, or two sections simply sit back-to-back with no
connective logic. This is the one pass that reads the whole thing and fixes exactly that
layer — nothing else.

For this person specifically, the highest-value catch at this stage is usually **cross-section
repetition**: a fact, a caveat, or a piece of motivating context stated in full in one section
recurs, restated rather than referenced, in a later section. Because `/write-paper` drafts
each section in isolation, a session drafting the registration section has no visibility
into the fact that the protocol section already explained why DAPI is a shared anchor, and
independently re-derives the same explanation. Individually reasonable, collectively bloated
— this is the single most common and most consequential edit at assembly time, more so than
any individual sentence's phrasing.

## What this is not

Not a rewrite, and not a review. `/review-paper`'s Fidelity, Craft, and cross-reference axes
still run afterward, over the assembled whole — this skill doesn't replace or duplicate
that judgement, it just produces the single document for that pass to run over. Never adds,
cuts, or reinterprets a claim, a citation, or evidence — if a seam can't be smoothed without
changing what a section asserts, flag it; don't resolve it in favor of flow.

## Process

### 1. Pin the manuscript order

Take the section/figure-legend order from the map or outline that generated the drafts
(e.g. a wayfinder map's structure ticket). If no order is already fixed, ask before
assembling.

### 2. Concatenate

Bring the drafts together in that order into one working document.

### 3. Fix each seam

At every boundary between two originally-separate drafts, and scanning the whole
document for anything that spans more than one boundary:

- **Redundant restatement** — the end of one section previews what the next section
  immediately says. Cut the thinner restatement, keep the fuller original.
- **Cross-section repetition** — the same fact, mechanism, or explanation is stated in full
  more than once across sections (not just at an adjacent boundary — this pattern shows up
  pages apart, e.g. a protocol detail explained in Background, restated near-verbatim in
  Implementation, and restated again in Results). Keep the fullest, most appropriately-placed
  version — usually the first — and replace every later instance with a short callback
  ("as described above," "the shared DAPI channel introduced above") that carries only the
  one clause actually needed for the local sentence to make sense. Do not simply shorten each
  restatement in place; check first whether the later section needs the fact restated at all,
  or only needs to refer to it.
- **Repeated caveat or scope statement** — a limitation, a caveat, or a piece of framing
  ("this is concordance among proxies, not validation," "we make no claim of absolute-fraction
  agreement") is restated in full every time it becomes relevant again, rather than stated
  once and referenced. State it fully at its first, most natural occurrence; every later
  recurrence should be a brief pointer, not a re-statement of the full reasoning.
- **Repeated contribution framing** — more than one section independently flags the same
  material as the paper's central/headline/load-bearing contribution. This is not wrong at
  any single occurrence, but stacked across sections it reads as the piece repeatedly telling
  the reader how to feel about itself. Keep at most one clear statement of what the central
  contribution is (Abstract and/or Conclusions is usually the right home); in sections that
  describe the mechanism itself (Implementation, Results), let the description carry its own
  weight rather than re-flagging it as "the" contribution each time.
- **Term drift** — the same concept named differently across sections. If a wayfinder map's `## Style` section pins the term, use that; otherwise pick the term established earliest in the piece and hold it constant, flagging the choice if it isn't obvious which term should win.
- **Missing or dangling transition** — two sections land with no connective logic
  between them. Add one connecting sentence or clause. Don't invent a claim to bridge
  them — if there's no real logical link, flag it as a structural gap rather than
  forcing one.
- **Dangling pointers** — "as shown above" / "described in Methods" that don't resolve
  once sections sit in final order. Fix the pointer, or flag it if it can't be resolved
  without content from a section not yet drafted.
- **Heading and numbering consistency** — renumber citations, figures, and figure panels
  to match first-mention order in the final assembled sequence. Sections drafted in
  isolation almost always number independently (each brief's own "citation 1," "Fig. 1"),
  so this is expected work, not an edge case: walk the assembled document in order,
  reassign each citation/figure/panel the number matching where it's *first* mentioned,
  and propagate every renumbering to all its later mentions and to the reference list /
  figure legends. This is mechanical — do it, don't just flag it. `/review-paper`'s
  cross-reference step re-checks the result afterward as a final, independent pass.
  Note that a figure can legitimately be *introduced* in one section (e.g. a schematic
  panel shown in Implementation) and *revisited* for additional panels later (e.g. its
  quantitative panels shown in Results) — this is not a numbering problem as long as the
  figure's first mention, wherever it falls, is the one that fixes its number.

### 4. Mark what changed

Keep a visible, running list distinguishing:
- fixes made silently (a cut redundant sentence, an added connective phrase, a repeated
  caveat trimmed to a callback) — mechanical, no judgement call, no need to flag
  individually in the final list beyond the log, and
- anything flagged instead of fixed (an ambiguous term choice, a missing logical link, a
  contradiction surfaced between sections, a repetition where it's unclear which instance
  should survive) — the person decides these, not this skill.

### 5. Save and hand off

Save the assembled manuscript as a single file. Then run `/review-paper` with the assembled
whole as the fixed point — this is the unit its Fidelity, Craft, and cross-reference passes
should run over, not any individual section draft.

## Boundaries

- Never alters a claim, adds a citation, or touches evidence — that's `/write-paper`'s
  territory during drafting, not this skill's during assembly. Renumbering an existing
  citation/figure to fix first-mention order is not covered by this — the reference
  itself, and what it supports, stays untouched; only its number changes.
- Never resolves a genuine contradiction between two sections by silently picking a side —
  flag it (this is `/review-paper`'s Buried Contradiction, surfaced early rather than left
  for that pass to find cold).
- Trimming a repeated restatement to a callback is a flow fix, not a claim change, as long
  as the surviving instance still says everything the trimmed one asserted. If the two
  instances actually differ in what they claim (not just how fully they restate it), that's
  a contradiction to flag, not a repetition to trim.
- Runs once, after every section/legend draft has closed. Re-run only if a later edit
  reopens more than one section at a time.
