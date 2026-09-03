---
name: render-paper
description: "Build a paper's document from its skeleton and run the mechanical gate over it — heading injection, the per-check verdict table, and the exit code that answers \"is this paper done\"."
disable-model-invocation: true
---

`render-paper` owns every mechanical duty in the paper pipeline: it builds the document, and it runs
every mechanical check. It holds no paper-specific text, judges nothing, and creates no annotation.
Three callers invoke it — a drafting session at its seam, a review as its first phase, and the author
asking for a deliverable — and there is exactly one implementation, so no two skills can disagree
about a mechanical fact.

The script is `scripts/render_paper.py`, Python 3, standard library only. It ships inside this skill
and is consumed only from here.

## The files it reads

All are declared inputs at the paper root, beside the source:

- [`skeleton.md`](SKELETON-FORMAT.md) — the heading tree, its order and levels, the roster, the
  document title and the venue limit.
- [`spine.md`](SPINE-FORMAT.md) — the claim ladder: the central claim, and one rung per unit.
- `briefs/<unit>.md` — one brief per unit, read by the overlap instrument.

`render-paper` is the only parser of the first two, which is why it documents their formats. **No
skill owns either file.** A planning ticket creates each; a drafting session may amend its own slot
only.

The brief is different: this is its only *parser*, but the drafting skill is the unit that ships its
two templates, so what this one fixes is **the six zone headings** and nothing else — a full format
spec here would be a second artifact recording one fact, which is how the two drift. (The templates
are not built yet; these headings are what they will have to match.)

```
## Argument              ← reader-facing, an originating unit's propositions
## Inventory             ← reader-facing, the facts a unit must convey
## Must not claim
## Sheds
## Verify before prose
## Sources
```

**Exactly two zones are reader-facing**, and they are the only zones whose content may legitimately
appear in the prose. Every other zone is instruction by virtue of **where it sits** — positional
separation, no marker strings. A zone heading this parser does not know is reported in the row, not
raised: the brief feeds reported rows only, so an unreadable one must not change the exit code.

**An absent brief is a legal state.** Briefs arrive as units are planned, and the row says which
units have none rather than counting them as nothing to report.

## Modes

```
render-paper <source> --circulate            emit a circulatable document
render-paper <source> --submit               emit a submittable one, or refuse
render-paper <source> --check                run the gate only; emit no document
render-paper <source> --scaffold             pre-seed one unit's anchors into its source
                      --section [<unit>]     modifier: section granularity
```

**There is no default mode.** The caller states which artifact it wants. `<source>` is one file
(post-promotion, `MANUSCRIPT.working.md`) or a directory of section sources (pre-promotion,
`drafts/`); with a directory, the render order is the skeleton's, never the filesystem's.

`--section` takes a unit — one top-level skeleton slot and its subtree. Bare `--section` derives the
unit from the source's anchors, and says so if the source anchors more than one.

`--scaffold` is the one mode that **writes the source** rather than reading a finished one, and the
one that takes `--section` as the **name of a unit** rather than as a granularity: it seeds one unit
and only one. See *The scaffold* below.

**The document goes to stdout. The verdict table and every diagnostic go to stderr.** So
`render-paper MANUSCRIPT.working.md --circulate > MANUSCRIPT.md` writes the render and leaves the
table on the terminal.

## Exit codes — the contract every other unit reads

| code | meaning |
|---|---|
| `0` | no FAIL at this granularity |
| `1` | at least one submit-gating FAIL. `--submit` refuses and prints the list; `--circulate` still emits |
| `2` | at least one hard error, or the renderer cannot run at all. **Neither mode emits** |
| `3` | a parse error. **Nothing ran** |

The tier answers one question: **would the render emit something false?**

- **Hard error, both modes** iff the emitted document is not the document the source describes: an
  anchor naming a slot the skeleton does not carry, one slot anchored twice, prose sitting outside
  every slot, a unit and its rung not pairing 1:1, an originating unit bearing children.
- **Submit-gating** iff the render is faithful but the work is unfinished: an unfilled skeleton slot,
  or an unfilled document title.
- **Parse error** iff the source cannot express the thing at all: a malformed anchor, a heading in a
  source, an unclosed comment, a malformed `skeleton.md` or `spine.md`, or either of those two
  missing — the render cannot run without them. **A missing brief is not in this tier**: it feeds
  reported rows only, so its absence is a legal state the row states.
- **Reported** iff it is a prose fact: brief-to-prose overlap, the finite-verb test, single-sentence
  body paragraphs and paragraph order. A reported row **cannot fail and never reaches the exit
  code**, and it carries **no threshold** — turning a prose fact into a floor is what this design
  refuses, because the judgement axes exist for exactly that.

### A parse error is not a gate

`--circulate` always succeeds over a *live* paper — an open gap is the normal state of one, and
every gap comes out as a conspicuous, greppable token. A parse error is a different thing: it is not
an open gap the render declines to gate on, it is text the render cannot parse, so it has no
behaviour and no gate bit to honour. It sits in the same category as an unclosed brace.

So when a parse error fires, **nothing ran, and the table is absent rather than full of failures.**
A table with every row failing would claim that every check looked and every check objected. None of
them looked. What prints instead is one line naming the file, the line and the malformation.

## The verdict table

`review-paper` reports this table **verbatim** and describes none of its rows, so its shape is an
interface, not formatting.

```
$ render-paper MANUSCRIPT.working.md --check --section results

  skeleton / spine grammar  PASS
  source grammar            PASS
  slot integrity            SKIPPED — OUT OF SCOPE AT THIS GRANULARITY
  unit / rung pairing       PASS
  originating slot children PASS
  unfilled skeleton slot    FAIL — 1 (`results-accuracy`)
  brief-to-prose overlap    1 flagged, 1 expected — results: "Registration accuracy is credible on a metr…"
  paragraphs (originating)  single-sentence 1 (results ¶2); brief-order 3 of 4 (results)

  4 pass, 1 fail, 1 out of scope, 2 reported
  → NOT a claim that this section is finished
```

- **Row order is the check registry's order and is fixed**, so the table is diffable across runs.
- **Three verdicts only:** `PASS`, `FAIL`, and `SKIPPED — OUT OF SCOPE AT THIS GRANULARITY`. A check
  that never looked is a **printed row**, never silently a pass. One word cannot carry the difference
  between checked-and-fine and never-checked, which is why no single-word verdict is emitted anywhere.
- A **reported** row carries no verdict at all — it prints **numbers**. A prose fact has no verdict
  to give: `PASS` over one would claim the number is fine, which is a judgement this unit does not
  make, and `FAIL` would be the threshold it refuses. The counts line names them separately for the
  same reason.
- A `FAIL` carries its count and what failed.
- The table closes with the counts and the line saying it is **not** a claim that the section (or the
  document) is finished. A gate with no FAILs is a statement about mechanism, never about judgement.
- **A row is never printed without a check behind it.** The registry grows as the checks are built;
  a row with nothing behind it would read as a pass, which is the defect this table exists to kill.

The two parse-tier rows are printed as `PASS` whenever a table prints at all, because a parse-tier
failure suppresses the table.

## The scaffold

```
render-paper drafts/methods.md --scaffold --section methods
```

Before a drafting session writes a word, its source already carries **every anchor in its subtree,
in skeleton order**. A misordered, duplicated or omitted anchor is then something the session
**cannot type**, rather than something a rule forbids — the same construction move as heading
injection, one level down.

- **Anchors are what live in a source; headings are not.** The scaffold writes no heading text,
  because injecting the headings is the render's job on **every** pass.
- **It is idempotent.** The seeded form is exactly what the scaffold reads back, so a second run
  changes nothing — which is what makes it safe to re-run after a skeleton amendment, where it adds
  the new slot's anchor and moves no prose.
- **A parent slot may bear prose**, so scaffolding a parent with children seeds the parent's anchor,
  then its children's: the parent's own prose is whatever ends up before the first child anchor.
- **It is always one unit**, because that is what a drafting session opens. `--section <unit>`
  names it; with no `--section`, the unit is **derived from the anchors already in the source**, and
  a source that does not name exactly one is refused rather than guessed at. Seeding a slot whose
  prose lives in another unit's file is how a source acquires the anchor the next render calls a
  duplicate, so the scaffold never reaches outside the unit's subtree.
- **A slot already anchored is kept even when it sits outside that subtree.** Post-promotion the
  source is one file holding every unit, so dropping them would delete another unit's prose to seed
  this one's.
- **The source is rewritten in place**, and created when it does not exist yet. Nothing goes to
  stdout, and there is no verdict table: the scaffold runs no check, because it emits no document
  that could be false. What sits between the anchors is kept verbatim — **the author-facing comment
  channel included**, because the comment strip belongs to the render and a mode that rewrites the
  source must not take an author's notes with it. Only the anchors' order and the blank lines
  between the blocks are the scaffold's to set. Text before the source's **first** anchor belongs to
  no slot, exactly as the render reads it, and stays at the head of the file — so a comment written
  there is a note on the file, never on the slot that happens to follow it.
- **The ladder is not read.** `spine.md` is the gate's input; the anchors come from the skeleton
  alone, and a declared input with no use here would be a refusal of a legal state.
- **Wherever it would have to guess, it refuses and writes nothing**: a slot anchored twice, an
  anchor naming no skeleton slot, prose sitting outside every slot, a source naming no single unit,
  a directory in place of a source. The first three are the gate's own facts, read by **the gate's
  own predicate**, so the scaffold cannot refuse what the gate would pass; and a guess would move or
  merge prose the author never asked it to touch.
- **Its exit codes are the same contract minus the gate** — `0`, `2` for a refusal, `3` for a parse
  error, and never `1`: there is no gate here to fail.

## Construction duties

1. **Inject every heading** from the skeleton, at its level, with its exact text, on **every** pass.
   The source carries a section **anchor** per slot and no headings at all, so a hand pass that
   demotes levels from the top and stops halfway through cannot be typed. Heading injection is
   determinate; no judgement is encoded in the renderer. A heading typed into a source is refused as
   a parse error, so the skeleton's authority over the tree holds by mechanism and not by good
   intentions.
2. **Strip the author-facing comment channel by syntax** — every HTML comment, as a class, never by
   a marker string. Parsing is span-based, never line-anchored: a comment may wrap any number of
   lines. The renderer emits no comment of its own, so there is no such thing as a comment the render
   preserves. Inside a fenced code block nothing is parsed at all — not a comment, not an anchor, not
   a heading — because a source showing anchor syntax in a fence is showing it, not using it.
3. **Concatenate**, pre-promotion only. Post-promotion the source is already one document.
4. **Mark the output as generated.** Every render opens with a front-matter banner naming the render
   as output. It is not a comment, because a render that emits its own comments is how a comment
   leaks into reader-facing text.
5. **Never silently strip a gap.** An unfilled slot renders as `⟦HOLE: prose for <slot id>⟧` and an
   unfilled title as `⟦HOLE: the document title⟧` — a uniform, greppable token. Silently dropping one
   would turn a flagged gap into an unsupported claim the author never learns about. A **parent** slot
   is the exception that is not a gap: its own prose is permitted rather than owed, so a parent with
   children renders its heading and lets the children carry the prose.

## The overlap instrument

The instrument that catches prose mirroring its own brief. A drafting session that walks its brief
one bullet per paragraph produces a list of labelled blocks rather than a manuscript, and the corpus
this design was calibrated on shows it happening — the audit's own phrase for what it found is
*transcribed near-verbatim from the briefs*.

**A shared span is a run of five words or more that a unit's prose and its brief share verbatim**,
measured inside one sentence of each and never across two: a run bridging a full stop is an
adjacency, not a phrase anybody moved. Case and punctuation are ignored when matching, a run of
nothing but function words is not a phrase, and the match is word-level so a re-wrapped line still
matches. The row then **quotes the span as the prose wrote it** — what the author has to go and find
is the phrase, and `Nextflow >= 25.04.0` is not findable as `nextflow 25.04.0`.

**The zone the span came from decides the instrument, not the unit:**

| zone | instrument |
|---|---|
| `## Argument` | every shared span is **flagged**. Its propositions are phrased as what the reader must end up accepting, so verbatim overlap with one **is** the defect, and no exemption is needed |
| `## Inventory` | **the finite-verb test**: a shared span is **expected** unless it predicates. An inventory item is a fact the prose must convey — `MIT`, `ghcr.io/org/tool`, `scale bar required` all reach the prose as themselves — and one that predicates is either the drafter transcribing or the brief author slipping into phrasing, which is how the format enforces itself |

**The finite-verb test is a closed list plus one guarded rule, and deliberately no more.** The
closed list is the finite forms of *be*, *have*, *do* and the modals, which are closed-class words,
so the list is complete rather than a sample and needs no per-paper extension — which it must not
have. The one rule catches a third-person present verb: a word ending in `-s`, not closed off by
punctuation, not first or last in the span, and not preceded by a determiner, number or
preposition. So *illumination correction **suppresses** tile-boundary seams* is flagged and *5 DSL2
stages, DAPI as common anchor* is not.

`-ed` is deliberately **not** a tell: *scale bar required* is an expected span, and an `-ed` rule
would flag it. A bare `-s` rule is equally refused — it reads every plural noun as a verb, and an
instrument that fires forever on a legend is an instrument nobody reads. The residual cost is a
plural noun that sits mid-span with no punctuation after it and no determiner before it, which can
read as a verb; the row prints the span, so a reader sees which one it was.

**Not yet wired: the `## Style` term exemption.** The exemption list for the overlap check is the
effort map's `## Style` *terms*, and the map is not yet an input to this unit — it arrives with the
style stanza. Until then a mandated term long enough to be a substantial phrase is reported. The
exemption covers **terms, never sentences**, which is what keeps the check from being hollowed out
by its own carve-out.

## Paragraph shape — originating units only

Two structural measures, both reported, both **suspended for a non-originating unit**:

- **single-sentence body paragraphs**, attributed to their unit and their position in it;
- **paragraph order** against the brief's item order — how many paragraphs sit at the position of
  the brief item they are about, which is the one-bullet-per-paragraph walk, counted. It is reported
  against the unit's **own paragraph count** — never against the item count, and never against the
  brief's derived paragraph budget: a draft that walks three items and then writes five more
  paragraphs is not mirroring, a denominator stopping at the items would never look at the five, and
  a budget is a plan where the paragraphs are the fact.

Both invert for a non-originating unit, which is why neither runs there. Order tracking the brief is
what a venue's field order and a figure's lettering **mandate**, so it is the requirement rather
than the defect; and a panel caption is not a unit of argument, so a one-sentence paragraph is its
normal shape. Run either on a legend and it fires forever. There the finite-verb test carries the
whole load.

A unit's brief items are the sentences of its reader-facing zone, less the ladder line: `Rung:`,
`Closes:`, `Opens:` and `Restates:` carry the unit's relation to the rung above it, and a relation
is bookkeeping rather than something the prose must convey. `## Argument` is read first, so a unit
that is **both originating and inventory-carrying** is ordered against its propositions and an
originating unit whose only reader-facing zone is `## Inventory` is still ordered against its
items.

**Both rows are per-unit, so neither is ever out of scope.** `--section` narrows them to the one
unit; whole-document granularity measures every unit and names each in the row.

## What it must not do

- Hold any paper-specific text. No bibliography, no section names, no per-paper fixes. Every
  judgement fix is written back into the **source**, never encoded in the generator: a fix that lives
  in the generator regresses the moment the generator stops being run.
- Create any annotation **in the source**. It renders a gap as a token; it never writes one.
- Hold any spine authority beyond the mechanical bookkeeping walk.
- Judge anything. Every check is decidable by parse; anything else belongs to a judgement axis.

## Vocabulary

*unit* — one top-level skeleton slot and its subtree; the thing a rung, a brief, a `draft` ticket and
a word budget all key on, 1:1. *slot* — a section position in the heading tree. **Note the deliberate
collision:** in the annotation channel, `SLOT:` inside braces marks a *venue back-matter field*. Two
different concepts, one word; every passage where both could apply qualifies which is meant.
*originating* / *non-originating* — a unit that opens a debt, versus one that closes, restates or
inventories. *argument brief* / *inventory brief* — the two brief formats, one axis: whether the
unit opens a debt. *proposition* — one item of an argument zone. *shared span* — a run of words a
unit's prose and its brief have verbatim in common.

## Tests

`pytest` from the repository root. The tests invoke this script as a subprocess over fixture papers
in `tests/fixtures/` and assert on the exit code, the emitted document and the verdict table; the
table and the document are compared against golden files verbatim, because a formatting change is an
interface change. No test imports the script.
