---
name: write-paper
description: "Draft one unit of a piece of academic writing — one top-level section and its subtree, in a paper, chapter, grant, or assay/protocol report — from its brief, the claim ladder, the skeleton and the style stanza. Body prose only, no headings, every figure, panel and citation referenced by stable name. Writes the source; /render-paper builds the document and runs the mechanical gate."
disable-model-invocation: true
---

`write-paper` drafts **one seam**, and the seam is **one unit**: one top-level slot in the heading
tree, together with its subtree. A unit is 1:1 with its rung on the claim ladder, its brief, its
`draft` ticket and its word budget, so the seam is **given rather than negotiated** — nothing here
infers a section boundary or agrees one after the fact.

It carries **construction rules only**: rules that hold while the sentence is being written, not
after the paragraph has been built around it. Every mechanical fact belongs to `render-paper`, which
this skill invokes at each seam and never duplicates.

What a drafting session may emit:

> **Body prose only.** **No headings at any level.** **`@fig:name` and `@key`, never literals.**
> **Annotations only in the three classes this skill may create** — `HOLE`, `SLOT`, `SILENT`. **No
> sentence naming a container in the act of closing a debt.**

## Why the session sees so little

The inputs step 1 lists are deliberately narrow, and the narrowness is a mechanism rather than an
economy. It makes cross-section repetition something a drafting session **cannot author around**
rather than something it is asked to avoid: a session that cannot read the protocol unit's prose
cannot trim its own re-derivation of it, and a session that could read it would be inventing a
through-line nobody handed it. The repetition stays fully visible to `assemble-paper`, which is the
one pass that reads the whole document with the whole document in front of it, and the only unit
permitted to cut.

The ladder arrives **whole and live** rather than as a window on the adjacent rungs, for two reasons.
Debts are non-local by nature — one rung opens what a rung three later closes — so a local window
hides exactly the edge the ladder exists to carry. And plan-to-output drift is real and silent: a
debt closed against what an earlier rung *planned* may be closed against text that was never
written, which is why the ladder you read is annotated with what was actually drafted.

## Process

### 1. Pin the spec

Whatever the user points to is the spec — an outline, a notes file, a set of results/figures/data the
piece needs to report on, or a stated argument structure. For grants, this includes the funder's
required section structure (e.g., Specific Aims/Significance/Innovation/Approach) and any page or
word limits. If none of this exists yet, ask what the piece needs to establish and in what order,
before drafting.

Also identify, if they exist:

- **The skeleton** — `skeleton.md`: the heading tree, its order and levels, the figure roster (names
  only), and the document-level limit. This is a settled input; a drafting session does not choose
  structure. If there is no skeleton (a direct invocation with no planning map), synthesise a minimal
  single-slot one, **say out loud that you are doing so**, and render from it. Absent is a legal
  state; heading-bearing prose is not.
- **The spine** — `spine.md`: the whole claim ladder, annotated with drafted actuals. You receive the
  whole ladder, your own brief, and the sources your own brief cites — and nothing else. No other
  unit's brief. No other unit's prose.
- **The brief** — `briefs/<unit>.md`, either an argument brief or an inventory brief. It carries the
  unit's propositions, what it must not claim, what it sheds to another unit, what to verify before
  prose, and its sources. It carries one unit-level word budget and no sub-allocation.
- **The style stanza** — compose the effective stanza from the map's `## Style` deltas over the
  user-level default file, and **print it at session start with each value's provenance**. Say which
  state you are in: **stanza found, found empty, or running on skill defaults.** The echo is a
  session-time report, never written into the source. If `## Style` names a Tier 2 craft invariant as
  a key, **stop and ask** — do not draft. [`STYLE-STANZA.md`](STYLE-STANZA.md) holds the schema, the
  values-blank exemplar and the composition rules; four of them bind every session:

  - **Discovery is an ordered list, first hit wins** — `~/.agents/style/academic-writing.md`, then
    `~/.claude/style/academic-writing.md`. The vendor-neutral root is first so an installer who has
    only `~/.claude/` is not silently in the absent case.
  - **The key set is closed** — `active-we`, `plain-words`, `build-in-steps`, `spelling-variant`,
    `em-dash-threshold`, `terms`. An effort wanting anything else writes **prose**, which is advisory
    to you and never machine-read. A closed set is what makes the invariant collision decidable at
    load instead of a judgement call.
  - **Compose by key, never wholesale** — a scalar **overrides**, a list **unions**, prose is
    **additive**. An effort states only its deltas, because one that had to restate every preference
    it still wanted would silently revert each one it forgot.
  - **`em-dash-threshold` is a finite non-negative integer** — no `off`, no `none`, no `∞`. An effort
    may raise the bar visibly; it cannot remove the gate.
- **The evidence base** — the actual data, figures, statistics, or source material each section will
  need to represent faithfully. A claim with no evidence base behind it is a claim to flag, not to
  invent support for.
- **The reference library** — an existing bibliography at a declared path (BibTeX, RIS, Zotero
  export, or plain reference list), and the citation style the target venue requires. You cite by
  **key**; the render assigns numbers and formats them.

**Announcing the stanza's state is not politeness, it is the mechanism.** A drafting skill that reads
`## Style` by name and says nothing when the section is missing is how a framing rule sat unread in a
map's `## Notes` while three skills looked for it in `## Style`, and a banned frame was denied seven
times in seven independent sections with nothing detecting it. When no stanza is found: Tier 2
invariants hold unchanged, the em-dash threshold keeps its skill default of **0**, and **Tier 3
preferences are not in force — this skill does not invent them.** Say so in one line, and offer to
create the file.

### 2. Draft at pre-agreed seams

Draft seam by seam, never the whole piece in one pass, and stop at each seam to confirm direction
before continuing.

**The seam is the unit, and for map-tracked work it is neither negotiable nor inferred** — the
skeleton and the ladder fixed it at planning time. On a direct invocation with no map, agree the
seams with the person up front.

Open the source with the scaffold, which pre-seeds every anchor in the unit's subtree, in skeleton
order:

```
render-paper drafts/<unit>.md --scaffold --section <unit>
```

**Write only between the anchors.** A misordered, duplicated or omitted anchor is then something you
cannot type rather than something a rule forbids. A parent slot's own prose is exactly the text
before its first child anchor; there is no way to express parent prose *after* a child, because prose
following a child anchor renders under that child's heading. Write **no heading at any level** — the
skeleton owns the tree and the render injects every heading on every pass, so a heading typed into a
source is a parse error.

### 3. Handle citations as you draft — never fabricate one

When a claim needs a citation:

- If a reference library was identified in step 1, pull the matching entry from it and cite it by its
  **key**.
- If the claim needs a citation that isn't yet in the person's library, search for a real candidate,
  and verify — by actually reading the source, not just its title or a search snippet — that it
  supports the claim **in the direction stated**. A topically-relevant but directionally-wrong
  citation is worse than no citation.
- When a claim rests on a specific technical detail — a tool's exact algorithm, what it does or does
  not model, a benchmark result — verify that detail against the actual source rather than a
  remembered impression of it.
- If no suitable source can be found or verified, don't insert a plausible-sounding placeholder.
  Write the gap as a hole carrying the gate bit, `{{ ! <what the claim requires> }}`, and raise it
  with the person. An unverified claim is precisely what must not reach a journal, so the gate bit is
  the default here rather than an escalation.
- When citing a source already discussed earlier in the piece, reuse the same key — don't introduce a
  second identifier for the same work.

**The citation surface, and the whole of it:**

```
@smith2020                      narrative position
[@smith2020]                    parenthetical
[@hickey2022; @elhanani2023]    grouped parenthetical
```

**Inside brackets: keys and `;` separators only.** No prefixes, no suffixes, no locators, no free text
of any kind: `[…]` is reserved for citation groups, and step 4 carries the rest of the reference
surface. **The source never holds a rendered citation.** Numbers, the reference
list and the venue's citation style are all render concerns: citations resolve to numbers by
first-mention order in the assembled document, and the rendered reference list is built from the keys
actually cited.

### 4. Reference figures, panels and citations by name — never by number

Every figure, panel and citation is referenced by a **stable name**: `@fig:registration-accuracy`,
`@fig:dapi-overlay`, `@smith2020`, `[@hickey2022; @elhanani2023]`. Numbers and panel letters exist
only in rendered output. Do not write `Fig 2`, `Fig. 4b`, `(c-d)`, `[7]`, or a positional name like
`@fig:panel-b` — each is a **parse error**, and the render will refuse.

A name that is not in the roster is a hard error, so add it to `skeleton.md` (your own slot only) or
file a `task` ticket if another unit references the figure.

For a forward or backward pointer, name the **proposition**, never the container — see step 5.

**A panel is a figure that lives inside another figure**: the same syntax, one flat namespace, with
parentage carried by containment rather than by syntax. **Panel names come from the legend's
declaration block**, a settled input authored at planning time, and **a drafting session may not
reorder it.** Panels letter by declaration order rather than by first mention, because a panel letter
appears in the artwork as well as in the text and a render can renumber prose but cannot repaint a
figure. Reordering the declaration block is an escalation to the planning ticket, not an edit here.

### 5. Construction rules — these hold while you write the sentence, not after

- **The debt check.** Every debt your rung inherits is closed in this text; every debt your rung must
  leave open is still open. For a non-originating unit the question is different: does what you wrote
  match the relation you declared — `Closes:` or `Restates:` — and nothing more? Check against the
  ladder's `establishes`, never against another unit's prose.
- **Name the proposition, never the container.** Closing an inherited debt is obligatory in prose,
  and it is done by naming the claim: "Reproducibility by construction says nothing about whether the
  registration is correct, and that is what @fig:registration-accuracy tests." Not "As described in
  Implementation above...". Test: delete every section name from the manuscript and reshuffle it — a
  legal sentence still parses.

  This bans naming the container **in the act of closing a debt**. An ordinary procedural
  cross-reference ("Methods specifies the procedures"; "Additional files carry the full per-arm
  results") is legal and often expected by the venue.
- **A justifying clause may be drafted only as the answer to a named, reader-raisable objection**,
  and you write the objection down beside the sentence as you draft it:

      <!-- obj: how far does six cases generalise? -->
      ...widens the immune-content range spanned by only six cases, which limits generalisation.

  Naming the objection **is** the test. Ask who could raise it: a reader of the published paper, from
  the evidence alone, means keep it, stated as a fact about the study. Only someone who saw the
  planning means it is rationale leak. A clause whose objection can only be phrased as "why did you
  write it that way" cannot be written into the comment, so it does not get drafted.
- **A framing constraint is obeyed by not invoking the frame, never by denying it.** "Six cases,
  three high and three low, chosen to span the immune-content range; how far the result carries
  beyond them is untested." Not "consistent with a proof of concept rather than a validation." The
  denial plants the word and the comparison in the reader's head, which is what the constraint
  existed to prevent. Test: the banned word does not appear at all, and the reader still knows
  exactly what was and was not shown.
- **Interpretation never precedes the result it interprets**, and **the figure reference attaches to
  the sentence stating what is shown**, not to a trailing interpretation sentence.
- **Removing an em dash is relation-first.** Name the relation — apposition, elaboration, contrast,
  concession, causation — then use the construction that carries *that* relation, which the
  subordination invariant below states. Never find-and-replace. Budget for this: on a real section it
  was the single most expensive act of the redraft, larger than the brief rewrite and the annotation
  migration combined.
- **No uniform paragraph or section shape.** There is no mandated move sequence and no mandated
  transition sentence. Which units reach back is decided by the ladder's debt edges.
- **No rule here may be satisfied by an unconditional transform over finished prose.** Every rule
  that removes or converts a construction requires reading what that construction was doing first. A
  rule that can be executed by find-and-replace will be, and the result is flatter than the text it
  replaced.
- Every specific claim, number, or citation traces to something actually provided or verified.
  Anything you cannot confirm becomes `{{ ! <the missing value> }}`, not a plausible-sounding
  placeholder.
- No new claim contradicts something already established; terminology matches the piece; certainty
  language (demonstrates / suggests / is consistent with / indicates / may) matches the evidence
  strength rather than the strength that would make the argument land more cleanly.
- No sentence grades its own importance. State what something is or does; let the reader judge its
  weight. Do not relocate the emphasis to a different sentence — cut it.

**Rationale leak is checked twice, deliberately** — the one shared duty in this pipeline. This skill
owns the **construction** rule above; `review-paper` owns a named `Rationale Leak` smell and
**re-derives the objection independently from the rendered sentence**, never reading your `obj`
comment. **Disagreement between the two namings is the finding.** A review that read the drafter's
declared objection would be accepting the drafter's own framing, which is the failure mode that
produced the leak.

### 6. Review at the checkpoint

**Run the gate first**, over the unit, for fast feedback:

```
render-paper drafts/<unit>.md --check --section <unit> --em-dash-threshold N
```

`N` is `em-dash-threshold` from the composed stanza; the **skill default is 0**, so a standalone
invocation is not the one path with no gate. **The em-dash count blocks this seam** — over the
threshold, the seam does not close. It is an actual command over the drafted text, never a bullet you
attest to: an em dash marks a logical relation without naming it, it is exactly as countable as a
figure reference, and as a self-attested bullet the ban was violated 98 times through six clean
reviews. An effort may raise the bar as far as it likes, visibly, and cannot remove the gate.

The row itself is **reported**: it carries `PASS` or `FAIL` against the threshold and moves no exit
code, because gating submission is reserved to the annotation gate bit. **The block is this skill's,
and it reads that row** — which is exactly why the count has to come from the command. A number you
did not produce is a number you cannot round down.

Invoking `--check` here duplicates no ownership: every mechanical check has one implementation in
`render-paper`, and duplicate *invocation* of a single implementation is free.

**Then render the unit and review the render:**

```
render-paper drafts/<unit>.md --circulate --section <unit>
```

Run /review-paper over **the render, not the annotated source**. The render is ephemeral — never
tracked, never committed. Reviewing the source is how six sections once passed a per-section
checkpoint while carrying 37 annotation markers between them: the reviewer read the brackets as
scaffolding. The render shows reader-facing prose with every reference token left unresolved, because
a section render cannot resolve a number the whole document owns.

There is no `CLEAN` verdict to record. The gate prints a per-check table; the judgement axes report
findings. The ticket closes when the gate reports zero FAILs and every judgement finding is fixed,
written back as a `!` annotation, or explicitly dispositioned with a reason. **Silence is not a
disposition.**

Record the **commit ref** your prose closed at in the ticket resolution, alongside the drafted file. A
later `revise` reconstructs this render from that ref.

### 7. Save

The source is **`drafts/<unit>.md`** pre-promotion and **`MANUSCRIPT.working.md`, at this unit's
slot**, post-promotion. **Never write `MANUSCRIPT.md`** — that name belongs to a render, which is
output. Update the bibliography at its declared path if one is being maintained; the render reads it
from there and never contains it.

The source is always Markdown. When the person needs the deliverable in a specific document format
rather than plain text, that is a property of the render rather than of the source, so check for a
relevant skill (docx, pdf) at handoff.

**Annotate the ladder with what was actually drafted.** One test decides what that costs: does the
debt still close?

- A rung that establishes less than planned but **still opens what the next rung needs** — record the
  hedge as the actual and continue. This is the normal outcome of verifying facts against a repo.
- A rung that **cannot close its inherited debt**, or that must leave open a debt nobody closes —
  **stop.** File a `task` ticket blocking the dependent rungs. The ladder is what gets fixed, not the
  prose.

The ladder holds exactly **one actual per rung, always current**: the drafted actual is overwritten
and git is the trail. A ladder carrying superseded actuals beside current ones makes every downstream
drafter work out which line is live.

## Craft invariants

**Tier 2 of the style stanza: true of any academic prose in any house style, enforced by judgement at
drafting and at review, and not overridable by `## Style`.** The key set `## Style` may use is closed,
so a clause naming one of these as a key is an unambiguous collision — the session **refuses before
drafting** rather than merging it. Prose in `## Style` that reads as contradicting an invariant is a
`review-paper` finding instead, because that one needs judgement and cannot be decided at load.

For contrast: **Tier 1** is a mechanical gate over a countable prohibited token, and `## Style` may
move its threshold but cannot remove the gate. **Tier 3** is preference — this person's or this
venue's house style — and it is exactly what `## Style` is for.

- **No rule in this skill may be satisfied by an unconditional transform over finished prose.** Every
  rule that removes or converts a construction requires reading what that construction was doing
  first. A rule that can be executed by find-and-replace will be, and it binds every unit in the
  pipeline, not only this one.
- **Subordination must remain available.** An em dash marks a logical relation without naming it, so
  once the relation is named, reach for the construction that carries *that* relation: a relative
  clause or paired commas for apposition, a colon for elaboration, a subordinating conjunction
  (`although`, `whereas`, `while`) for contrast or concession, a semicolon for a balanced pair. Read
  that as an invariant and never as a menu — picking from the list without reading the relation is
  the banned transform in a new costume. The list it replaced, *comma, colon, or a sentence break*,
  took subordination to zero on a real revision pass, because comma and sentence break coordinate or
  terminate and only the colon subordinates, weakly. This is also what makes the em-dash threshold
  safe to configure: an effort may flip the number and can never switch off naming the relation.
- **Convert a passive when the actor is load-bearing and hidden**, and leave it when the actor is
  irrelevant or the object is the topic. "Slides were stained" is correct; the actor is a technician
  and nobody needs them named. There is no convert-them-all default: "as a matter of course" is an
  instruction not to ask what this particular passive is doing.
- **Interpretation never precedes the result it interprets**, and **the figure reference attaches to
  the sentence stating what is shown.** These are the two pairwise constraints that survive from a
  deleted four-move paragraph template: a uniformly-applied
  template produces identically-shaped paragraphs, and mandating a restatement of goal and method in
  every results paragraph makes the paragraph do the rung's job out loud.
- **A unit may open by *using* what came before** — restating the proposition as a premise it now
  builds on — and may **never** refer to a section, the text, or the reader's position in it.
  "Registration accurate to 1.2 µm lets us compare the same cell across panels", not "As established
  in Implementation, registration is accurate to 1.2 µm." Same content, no container. **There is no
  mandate**: which units reach back is decided by the ladder's debt edges, and a per-boundary
  transition ritual is what makes openings uniform.
- **A child slot partitions by an object or a procedure, never by a claim.** A claim is carried by
  prose motion, by opening and closing debts; giving a claim its own labelled box is the alternative
  to motion. This binds at planning time, where the child headings are chosen, so the surface for the
  defect never reaches a drafting session.

Nothing in Tier 3 is invented here, and **no filled Tier 3 value ships with this skill.** A shipped
default voice is one person's house style with the authorship filed off, installed on everyone who
never edits the file, so a preference in force always traces to the effort's `## Style` or to the
user-level default file and never to here. What ships instead is
[`STYLE-STANZA.md`](STYLE-STANZA.md): the **keyed schema** — names, domains and tiers — and a
**values-blank exemplar**, with one worked example labelled as an example and never as a default.
The exemplar carries no values because neutral-looking ones would re-create the leak one level down.

## Residual risks

Two facts a session should know before it starts, both measured on a real section:

- **The em-dash conversion dominates seam cost.** Converting 21 em dashes was the single most
  expensive act of the redraft, larger than the brief rewrite and the annotation migration combined.
  **Budget for it at the seam**, while the relation each dash was carrying is still fresh, rather than
  meeting it as a blocking gate once the unit is otherwise finished.
- **The adversative ratio moves as a *consequence* of that conversion, so nobody tunes it.** Naming
  relations produced four adversative connectives from zero with none targeted, which is why the
  near-zero adversative count and the 98 em dashes are one defect seen from two directions. Read the
  number `render-paper` reports as a consequence of the relation work; never target it.

## Boundaries

- **Chooses no structure.** The heading tree, its order and levels, and the figure roster are settled
  inputs. A drafting session may amend **its own slot** in `skeleton.md` and nothing else; anything
  wider is an escalation to the planning ticket.
- **Numbers nothing and formats no citation.** Heading injection, concatenation, numbering, the
  reference list and the comment strip are all `render-paper`'s, on every pass.
- **Reads no other unit's prose or brief**, and writes no other unit's slot.
- **Owns no mechanical check.** Every check invoked at the seam is `render-paper`'s single
  implementation; a mechanical rule restated here as prose would be a second, disagreeing copy.
- **Creates annotations in all three classes** — `HOLE`, `SLOT` and `SILENT`, with the gate bit `!`
  where the value must not reach submission — **and is the only unit that may.** A review writes
  `SILENT` alone; `assemble-paper` and the render write none. `SLOT` here is the annotation sense, a
  venue back-matter field, not a position in the heading tree. Resolving one means substituting the
  real value or deleting the comment: there is no `RESOLVED` marker and no tombstone.
- **Never assembles.** Promotion into `MANUSCRIPT.working.md` and the whole-document editorial pass
  are `assemble-paper`'s, once, after every draft has closed.

## Vocabulary

*unit* — one top-level skeleton slot and its subtree; the thing a rung, a brief, a `draft` ticket and
a word budget all key on, 1:1. *slot* — a section position in the heading tree; **note the deliberate
collision** with `SLOT:` inside an annotation brace, which marks a venue back-matter field instead.
*spine* — the artifact and the map section; *claim ladder* — its structure; *rung* — one unit's
obligation; *debt* — an open proposition passed forward from one rung to another. *argument brief* /
*inventory brief* — the two brief formats; *proposition* — one item of a brief's argument zone;
*shed* — content explicitly leaving the unit. *originating* / *non-originating* — a unit that opens a
debt, versus one that closes, restates or inventories. *HOLE / SLOT / SILENT* — the three render
behaviours; *the gate bit* — the leading `!` that blocks `--submit`.
