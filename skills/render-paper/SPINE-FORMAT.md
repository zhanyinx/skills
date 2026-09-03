# `spine.md` — the format

The spine is a **claim ladder with open debts**: one central claim, decomposed into ordered **rungs**,
one rung per unit. It is what carries the through-line. A forward-only chain of takeaways was
rejected for this job, because prose that only ever advances reads as a list of things regardless of
how well its sentences are built — **a debt is what forces prose to turn back on itself; a takeaway
is not.**

`render-paper` is its only parser, which is why the format is documented here, beside the code that
reads it. The bookkeeping walk over this file is a graph query over declared metadata, never a
reading of the prose.

**No skill owns this file.** Its own planning ticket creates it, blocked on the skeleton ticket
(rungs cannot be assigned to units not yet chosen) and blocking every brief ticket (a brief cannot be
written against a rung that does not exist). A drafting session updates **its own rung's drafted
actual** and nothing else; amending a rung is a `task` ticket — see *Amendment* below.

## The file

```markdown
# Spine — <effort name>

## Central claim

Cross-panel registration is accurate enough to support per-arm comparison.

## Rungs

### R1 — abstract

- establishes: the pipeline registers cyclic panels accurately
- restates: R4

### R2 — introduction

- establishes: cross-panel drift is unaddressed by the existing tooling
- opens: D1 (closed by R4) — whether the registration this pipeline performs is accurate

### R3 — methods

- establishes: the procedures are reproducible from the committed configuration
- actual: drafted, hedged — the CI gate is a stub and the weights are unarchived

### R4 — results

- establishes: registration accuracy supports per-arm comparison
- closes: D1
```

## `## Central claim`

One sentence. The whole ladder decomposes it.

## `## Rungs`

One `### R<n> — <unit>` heading per rung. `<n>` counts from 1 and ascends without gaps: the rungs are
**ordered**, and the order is the argument's.

`<unit>` is a **top-level slot id** from [`skeleton.md`](SKELETON-FORMAT.md). The cardinality rule is
1:1 and exact:

> **One top-level skeleton slot and its subtree = one rung = one brief = one `draft` ticket = one
> word budget.**

So a rung naming something that is not a top-level slot, two rungs for one unit, or a unit with no
rung, all mean this ladder is not a ladder for this skeleton. Each is a **hard error** — a printed
row, `unit / rung pairing`, rather than a malformation of this file, because the fact is about the
two files together and either one alone reads perfectly well. A rung spanning two top-level slots is
illegal: the ladder decomposes instead, and the second slot takes a **non-originating** rung. A
venue-mandated Results/Discussion split therefore never forces an artificial argument split.

### The four relations

Each rung carries relation lines, one per line, as `- <relation>: <value>`.

| relation | cardinality | value |
|---|---|---|
| `establishes` | **exactly one** | the proposition this unit must leave the reader holding |
| `opens` | zero or more | `D<n> (closed by R<n>) — <statement>`: the debt this unit deliberately leaves unresolved, and the rung that closes it |
| `closes` | zero or more | `D<n>` — the inherited debt this unit discharges |
| `restates` | zero or more | `R<n>` — a rung whose propositions this unit re-presents without establishing anything new |
| `actual` | **at most one** | what was *drafted*, as against what was planned |

There are **four** relations, not three: `restates` is what an abstract, a conclusion or a summary
figure legend does, and a unit that restates is non-originating.

**A debt is identified by its id, never by its text.** `D<n>` is declared by the rung that opens it
and referenced by the rung that closes it, and the id is the join key. The statement after the
em dash is for the reader of the ladder. Matching debts by their prose instead would be a join key
with no normalisation, and two innocent spellings of one debt would silently orphan the edge.

### `originating`, and what it costs the skeleton

A unit that carries an `opens` line **originates**. One that only closes, restates or inventories
does not. An originating unit must carry **zero children** in the skeleton — the child-count rule,
computed from both files. This is the one rule that reads the skeleton and the spine together, which
is why the two formats land together.

### The drafted actual

The ladder holds **exactly one** `actual` per rung, always current, and a drafting session
**overwrites** it. It is never appended to, and there is no history field: a ladder carrying
superseded actuals beside current ones forces every later drafter to work out which line is live —
one artifact recording one fact twice, which is worse than two artifacts recording it once. Git is
the trail.

The actual exists because plan-to-output drift is real and silent. A drafting session receives the
**whole** ladder annotated with actuals, so that it closes a debt against the text that exists rather
than against what an earlier rung planned to write.

## The chain walk

`render-paper` walks the declared relations and reports the argument's bookkeeping. It is a graph
query over declared metadata: it reads the four relations and nothing else — never the prose, and
**never the section type.**

### `chain bookkeeping` — submit-gating

Every declared debt is **opened exactly once, closed exactly once, and none is left dangling at the
end.** The row fails on:

| the walk finds | the row says |
|---|---|
| two rungs opening `D1` | `D1` is opened twice, by R1 and R2 |
| two rungs closing `D1` | `D1` is closed twice, by R3 and R4 |
| `D1` opened and no rung closing it | `D1` is opened by R2 and never closed |
| `closes: D9` where no rung opens `D9` | R4 closes `D9`, which no rung opens |
| `opens: D1 (closed by R4)` but R3 closes it | `D1` declares R4 closes it, but R3 does |
| a `closed by` or a `restates` naming no rung | … which is not a rung in this ladder |

Submit-gating rather than a hard error: the render is faithful — the document says what the source
says — and what is unfinished is the argument. So an unclosed debt still circulates, and `--submit`
refuses.

### `debt precedence` — submit-gating

> Every debt is opened in a unit **no later than** the unit that closes it.

Read against the **skeleton's** order, which is the document's reading order, because the reader is
who the rule protects: close a debt before the unit that opens it and the payoff arrives before the
promise. The ladder's own order is not what this reads — reading order and argument order are
different relations and may disagree, and the skeleton is authoritative on order.

`restates` carries **no** precedence. An abstract restates a rung the document has not reached yet,
which is what an abstract is for.

### What the walk does not do

**It never reads the section type.** A Methods unit may carry the paper's load-bearing claim, and a
walk that expected an introduction to open every debt would false-fail on exactly that paper. Only
the declared relation decides which rung originates.

**Debts are opened and closed by units.** A rung keys to one unit, so there is no debt edge inside a
unit and nothing to check inside one; a rung naming a child slot is the `unit / rung pairing` row's
finding, not this walk's.

**It is the mechanical half only.** Whether prose that *claims* to close a debt actually closes it is
judgement, and belongs to the review's Fidelity axis.

## The unit's prose obligation

Closing an inherited debt is obligatory **in prose** — but by naming the proposition, never the
container:

```
BANNED (names the container):
  "As described in Implementation above, the pipeline is reproducible; Results reports
   the numbers these procedures produced."

REQUIRED (names the claim):
  "Reproducibility by construction says nothing about whether the registration is
   correct, and that is what @fig:registration-accuracy tests."
```

The test: delete every section name from the manuscript and reshuffle it, and a legal sentence still
parses.

**The ban is narrow.** It is *naming the container in the act of closing a debt*, and not "no
sentence naming a section" — read blanket, that kills the ordinary procedural cross-references a
venue expects (*"Methods specifies the procedures…"*, *"Additional files carry the full per-arm
results"*) and makes a brief's own sheds zone self-contradictory.

**The rung never becomes prose.** It rides at the head of the unit's source as an ordinary HTML
comment, stripped by syntax, invisible to the reader, and tracked in no manifest: nobody owes a rung,
so it must never appear in a list of outstanding work sent to a co-author. It is not the unit's topic
sentence either — a layout instruction transcribed as a claim to the reader is its own defect.

## Amendment — record hedges, escalate breaks

One test: **does the debt still close?**

- A rung that establishes **less than planned but still opens what the next rung needs** → record the
  hedge as the `actual` and continue. This is the *normal* outcome of verifying facts against a
  repository.
- A rung that **cannot close its inherited debt**, or must leave open a debt nobody closes → **stop**,
  and file a `task` ticket blocking the dependent rungs. **The ladder is what gets fixed, not the
  prose.**

## Debt edges are blocking edges

The ladder's debt edges become the draft map's native blocking edges: a unit that closes a debt is
blocked by the unit that opens it. The frontier is therefore derived from the argument rather than
hand-declared, and every parallelism the argument actually permits survives.
