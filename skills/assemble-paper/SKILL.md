---
name: assemble-paper
description: "Promote independently-drafted sections into one annotated working manuscript, then make the one editorial pass that reads the whole document end to end — cross-section repetition, repeated caveats and contribution framing, term drift, missing connective logic — without altering claims, evidence, or citations. Runs once, after every section and legend draft has closed. Writes the source; it does not produce the reader-facing document, which /render-paper does."
disable-model-invocation: true
---

`assemble-paper` has two jobs and no others: it **promotes** the drafted units into one annotated
working manuscript, once and irreversibly, and it makes **the one editorial pass that reads the whole
document end to end**.

It holds no mechanical duty that another skill could disagree with it about. Concatenation, heading
injection, numbering and the reference list all belong to `render-paper`; it holds no spine
authority; it creates no annotation.

## Why this exists

The cut this pass makes — the same fact stated in full in three units — is the one defect in the
whole pipeline that nothing else can reach, and the reason is structural rather than a matter of
diligence:

- **A drafting session cannot see it.** A `write-paper` session receives the ladder, its own brief
  and the sources that brief cites, and never another unit's prose. So a session drafting the
  registration unit has no visibility into the protocol unit already having explained why DAPI is
  the shared anchor, and independently re-derives it. Individually reasonable, collectively bloated.
- **A review cannot fix it.** `review-paper` may only write `SILENT` annotations, which emit
  nothing. De-duplication **is a cut**, and a skill that cannot change what the reader sees cannot
  make one.

So the detection and the cut stay in one place. Splitting them would recreate exactly the
overlapping ownership this pipeline is built to avoid.

## Process

### 1. Pin the manuscript order

Take the order from `skeleton.md`, which is authoritative. It is not a question to ask and not a
thing to infer from the filesystem: a missing or malformed `skeleton.md` is a parse error, so
`render-paper` refuses to run at all and there is nothing to assemble until it is fixed.

### 2. Promote

Write the annotated working manuscript to `MANUSCRIPT.working.md` — every unit's source in the
skeleton's order, annotations intact, anchors and no headings. Nothing is edited on the way in: the
promotion moves the source, it does not improve it.

**This is a promotion, and it is irreversible.** `drafts/` and `briefs/` freeze as history, and
re-assembly from sections is no longer possible. From now on a new section is drafted straight into
the working manuscript at its slot.

**It comes before the editorial pass, not after.** That is the whole point of promoting: the pass
below is whole-document work, and a through-line cannot be revised across thirteen files. It is
also the only shape the write authority allows — the drafted sections belong to the drafting
session, and this skill's one writable artifact is the working manuscript.

### 3. Make the editorial pass

Render the promoted source and read it:

```
render-paper MANUSCRIPT.working.md --circulate
```

That is the whole piece as a reader meets it — headings injected, the comment channel stripped, every
gap a conspicuous token. If it refuses with a parse error, nothing ran: fix what the error names
before going further.

This is the only pass anyone makes over the whole piece with the whole piece in front of them.
Scan all of it, not just the boundaries — the highest-value catches sit pages apart, and sampling
it unit by unit is the exact vantage point every drafting session already had, from which the
defects below are invisible. Every fix is written back into `MANUSCRIPT.working.md`, never into a
render.

- **Redundant restatement** — the end of one unit previews what the next immediately says. Cut the
  thinner restatement, keep the fuller original.
- **Cross-section repetition** — the same fact, mechanism, or explanation stated in full more than
  once across units. This is the highest-value catch at this stage, and it is the one thing no other
  skill can see. Keep the fullest, most appropriately-placed version — usually the first — and
  replace every later instance with a short callback that **names the proposition, never the
  section**: "the shared DAPI anchor" or "reproducibility by construction", never "as described
  above" or "as described in Implementation". Check first whether the later unit needs the fact
  restated at all or only needs to refer to it; do not simply shorten each restatement in place.
- **Repeated caveat or scope statement** — a limitation or piece of framing restated in full every
  time it becomes relevant. State it fully at its first, most natural occurrence — "the comparison
  is between two proxies for the same quantity, measured on the same sections" — and let every later
  recurrence be a brief pointer naming the proposition, "the proxy-to-proxy comparison".
- **Repeated contribution framing** — more than one unit independently flags the same material as
  the paper's central contribution. Not wrong at any single occurrence, but stacked across units it
  reads as the piece repeatedly telling the reader how to feel about itself. Keep at most one clear
  statement.
- **Term drift** — the same concept named differently across units. If the map's `## Style` section
  pins the term via its `terms` list, use that; otherwise pick the term established earliest and
  hold it constant, flagging the choice if it isn't obvious which should win.
- **Missing or dangling connective logic** — two units land with no logical link. Add one connecting
  clause that names the proposition being carried forward. Don't invent a claim to bridge them — if
  there's no real link, flag it as a structural gap.

**The callback names the proposition and never the container.** A callback that names a section is
meta-narration of exactly the kind the drafting rules ban, and a de-duplication pass that emits one
per cut converts repetition into a table of contents in prose — which is a worse defect, not a
smaller one. Test: delete every section name from the manuscript and reshuffle it; a legal callback
still parses.

### 4. Hand off

```
render-paper MANUSCRIPT.working.md --circulate > MANUSCRIPT.md
```

Then run `/review-paper` over that render, with the whole-document checks now in scope rather than
printing `SKIPPED — OUT OF SCOPE AT THIS GRANULARITY`.

## Boundaries

- **Never alters a claim, adds a citation, or touches evidence.** Trimming a repeated restatement to
  a callback is a flow fix, not a claim change — as long as the surviving instance still says
  everything the trimmed one asserted. If the two instances differ in what they *claim*, that is a
  contradiction to flag, not a repetition to trim.
- **Never resolves a genuine contradiction by silently picking a side.** Flag it.
- **Holds no spine authority whatsoever** — not the seam check, not the chain walk, not the ladder.
  The seam check belongs to the drafting session, the bookkeeping walk to `render-paper`, and the
  discharge question to `review-paper`'s Fidelity axis.
- **Creates no annotation.** It reads the channel and writes prose; every `HOLE`, `SLOT` and
  `SILENT` it finds is carried into the working manuscript untouched. Everything this pass flags
  rather than fixes is raised with the author in the session — a flag is a sentence to a person,
  never a marker left in the source.
- **Renumbers nothing, and checks no heading.** Citations and figures resolve by first-mention
  order, panels by legend declaration order, headings are injected from the skeleton on every pass,
  and the reference list is built from cited keys — all of it in the render, none of it here.
- **Reads only `terms` from the map's `## Style` section**, for the term-drift bullet. It owns none
  of the voice tiers.
- **Runs once**, after every section and legend draft has closed. There is no second run, because
  after promotion there are no sections left to assemble.

## Vocabulary

*unit* — one top-level skeleton slot and its subtree; the thing a rung, a brief, a `draft` ticket and
a word budget all key on, 1:1. *slot* — a section position in the heading tree; note the deliberate
collision with `SLOT:` inside an annotation brace, which marks a venue back-matter field instead.
*proposition* — one item of a brief's argument zone, and the thing a callback names. *promotion* —
the one-way move from `drafts/<unit>.md` to `MANUSCRIPT.working.md` as the source.
