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

All five are declared inputs at the paper root, beside the source:

- [`skeleton.md`](SKELETON-FORMAT.md) — the heading tree, its order and levels, the roster, the
  document title and the venue limit.
- [`spine.md`](SPINE-FORMAT.md) — the claim ladder: the central claim, and one rung per unit.
- `briefs/<unit>.md` — one brief per unit, read by the overlap instrument.
- `references.bib` — the author's reference library. See [the citation surface](CITATIONS.md).
- each roster row's **legend file**, at the path that row declares, for the `## Panels` block that
  fixes the panel names and their letters. See [figures and panels](FIGURES.md).

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

**An absent brief is a legal state.** Briefs arrive as units are planned, and the row names the units
that have none rather than counting them as nothing to report.

The bibliography is different in kind: it is **author-owned**, in a format this unit did not
invent, and the render **reads it and never writes it**. Absence is a legal state — a paper citing
nothing has nothing to resolve.

## The channel it reads inside the source

[The annotation channel](ANNOTATION-CHANNEL.md) — `{{ … }}` **must** appear in the render, an HTML
comment **must never** — plus the manifest, the gate bit, and the creation-rights grid. Same reason
the file formats are documented here: `render-paper` is the channel's only parser.

```
{{ [!] [SLOT:] [@owner] <label> }}      ! is the gate bit; bare is a HOLE; SLOT: is a venue field
<!-- !@owner <label> -->                SILENT; in the manifest iff it opens with `!` or `@`
```

## The reference surface inside the source

[The citation surface](CITATIONS.md) — `@key` narratively, `[@key]` parenthetically, `[@a; @b]`
grouped, and **inside brackets nothing but keys and `;`**. A source references by **stable key and
never by number**; the render assigns the numbers by first mention and builds the reference list
from the cited keys.

Outside comments and fences, **every other `[…]` span in prose is a parse error** — the calibration
that makes that affordable, and the whole cost of it, are in that document.

## Modes

```
render-paper <source> --circulate            emit a circulatable document
render-paper <source> --submit               emit a submittable one, or refuse
render-paper <source> --check                run the gate only; emit no document
render-paper <source> --scaffold             pre-seed one unit's anchors into its source
                      --section [<unit>]     modifier: section granularity
                      --em-dash-threshold N  modifier: the em-dash bar, default 0
                      --supersedes <ref>     modifier: the commit the superseded draft closed at
```

**There is no default mode.** The caller states which artifact it wants. `<source>` is one file
(post-promotion, `MANUSCRIPT.working.md`) or a directory of section sources (pre-promotion,
`drafts/`); with a directory, the render order is the skeleton's, never the filesystem's.

`--section` takes a unit — one top-level skeleton slot and its subtree. Bare `--section` derives the
unit from the source's anchors, and says so if the source anchors more than one.

`--scaffold` is the one mode that **writes the source** rather than reading a finished one, and the
one that takes `--section` as the **name of a unit** rather than as a granularity: it seeds one unit
and only one. See *The scaffold* below.

`--supersedes` takes the commit ref a `revise` ticket's superseded draft closed at, and feeds one
reported row. It is a modifier on `--section`, because a supersession is one unit: over a whole
document the row prints `SKIPPED`. See [the supersession diff](#the-supersession-diff).

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
  every slot, a figure or panel name absent from the roster and every legend, a roster name nothing
  in the document points at, a unit and its rung not pairing 1:1, an originating unit bearing
  children, a citation key with no bibliography entry.
- **Submit-gating** iff the render is faithful but the work is unfinished: an open annotation
  carrying the gate bit, an unfilled skeleton slot, an unfilled document title, a debt the ladder
  never closes, a debt closed before it is opened, a bare hole left in reader-facing prose, or
  author workflow state written as a sentence the reader will read. The last of those is the **one
  mode-dependent row in the gate** — it fails `--submit` and `--check` and merely `WARN`s under
  `--circulate`, so the same source at the same granularity exits `1` for the first two and `0` for
  the third. The table above still holds either way, because a `WARN` is not a `FAIL`; see
  [the two residue lints](#the-two-residue-lints) for why that row alone is softened.
- **Parse error** iff the source cannot express the thing at all: a malformed anchor, a heading in a
  source, an unclosed comment, a malformed or unclosed brace, a bracket in prose outside a citation
  group, a [reference literal](FIGURES.md#the-parse-errors) — a parenthesised panel letter, a
  `Fig`-plus-number form, or a positional name — a malformed `skeleton.md`, `spine.md`,
  `references.bib` or legend declaration block, a missing `skeleton.md` or `spine.md`. **Only a
  brace, a bracket or a literal can refuse, never a comment** — a parse error is for what the source
  cannot express into *reader-facing* prose, and a comment never reaches the reader.
  A **missing `references.bib` is not** a parse error: the library is required by the citations
  rather than by the renderer, so it is the hard error above, and a paper citing nothing needs no
  library at all.
- **Reported** iff the fact is worth an author's attention and no exit code: the em-dash count, the
  prose diagnostics, the locality test, and the supersession diff. **A reported row never changes the
  exit code**, in any mode — see below.

A `warnings` block on stderr sits under every tier and moves **no** exit code: a brace label over 80
characters, a bare brace standing alone in its own block, a label that opens `slot:` in case `SLOT:`
was meant, and a keyed comment that matches no brace. A hard cap or a refusal on any of them was
rejected — each over- and under-fires at once, and a wrong refusal breaks a paper that never asked
for any of this. It is **not** the reported tier: a reported row is a measured fact with a printed
row of its own, while a warning is advice about one annotation, printed only when there is one.

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
$ render-paper MANUSCRIPT.working.md --check --section methods

  skeleton / spine grammar        PASS
  source grammar                  PASS
  brace grammar                   PASS
  citation group                  PASS
  reference literals              PASS
  slot / roster integrity         SKIPPED — OUT OF SCOPE AT THIS GRANULARITY
  citation → bib entry            SKIPPED — OUT OF SCOPE AT THIS GRANULARITY
  unit / rung pairing             PASS
  originating slot children       PASS
  annotations (gating)            PASS
  unfilled skeleton slot          FAIL — 1 (`methods-imaging`)
  bare holes                      PASS
  workflow phrases                PASS
  chain bookkeeping               SKIPPED — OUT OF SCOPE AT THIS GRANULARITY
  debt precedence                 SKIPPED — OUT OF SCOPE AT THIS GRANULARITY
  em dashes (threshold 0)         FAIL — 2 (line 26)
  brief-to-prose overlap          0 flagged, 2 expected
  single-sentence body paragraphs 0 in 0 originating units
  adversative ratio               SKIPPED — OUT OF SCOPE AT THIS GRANULARITY
  subject openings                SKIPPED — OUT OF SCOPE AT THIS GRANULARITY
  sentence length                 SKIPPED — OUT OF SCOPE AT THIS GRANULARITY
  locality test                   SKIPPED — OUT OF SCOPE AT THIS GRANULARITY
  supersession diff               not a supersession — no `--supersedes` ref

  10 pass, 2 fail, 8 out of scope, 3 reported
  → NOT a claim that this section is finished

  manifest — 1 open annotation, 0 carrying the gate bit
  → f(source), recomputed at every render; deletion is the only closure

  @author
       SLOT    MANUSCRIPT.working.md:50  data availability statement
```

**The manifest follows the table under every mode, `--check` included**, and it is printed whether
or not it is empty — an absent manifest reads as nobody having looked. The **gate** is scoped to the
granularity the way every row is; the **manifest is not**, because it is `f(source)` and an absolute
input to a diff-relative judgement axis. See [the channel](ANNOTATION-CHANNEL.md).

- **Row order is the check registry's order and is fixed**, so the table is diffable across runs.
- **Four verdicts only:** `PASS`, `WARN`, `FAIL`, and `SKIPPED — OUT OF SCOPE AT THIS GRANULARITY`.
  A check that never looked is a **printed row**, never silently a pass. One word cannot carry the
  difference between checked-and-fine and never-checked, which is why no single-word verdict is
  emitted anywhere.
- A `FAIL` carries its count and what failed, and a `WARN` carries the same in the advisory channel.
  **A `WARN` moves no exit code.** It exists so that a check which objects under one mode and merely
  notes it under another cannot print as a pass; exactly one row uses it, and
  [the two residue lints](#the-two-residue-lints) explain which and why. Like the reported count, the
  `warn` tally appears only when something warned.
- **A reported row carries a number instead of a verdict**, and is tallied apart from the
  verdicts, because a measurement is not a verdict. The `locality test` row prints
  `4 units, 6 slots, 2 cross-unit edges (…)` where a gate row prints `PASS`; what to do about the
  number is judgement the render does not hold. The one exception is the em-dash count, which is
  measured against a threshold and so takes `PASS` or `FAIL` — and still moves no exit code. Where a
  reported row is whole-document only, it prints `SKIPPED` like any other out-of-scope row.
- The table closes with the counts and the line saying it is **not** a claim that the section (or the
  document) is finished. A gate with no FAILs is a statement about mechanism, never about judgement.
  Every row is counted once, under what it printed, so the counts sum to the rows.
- **A row is never printed without a check behind it.** The registry grows as the checks are built;
  a row with nothing behind it would read as a pass, which is the defect this table exists to kill.

The parse-tier rows are printed as `PASS` whenever a table prints at all, because a parse-tier
failure suppresses the table.

## The two residue lints

Every other check reads structure. These two read **prose**, because some unfinished text is
grammatical reader-facing prose that no bracket-stripping can see:

> …the residual distance is of order of XX, which is acceptable for our analysis…
>
> …archiving the panel stacks is a submission-readiness item.

Neither sentence carries a bracket, an annotation or a marker. Both are the residue an
annotation-based channel leaves behind, and both would reach a journal by being well-formed.

| lint | tokens | tier |
|---|---|---|
| **bare holes** | `XX+`, `TBD`, `TK`, `FIXME`, `???` | submit-gating |
| **workflow phrases** | `submission-readiness`, `to be confirmed`, `TODO`, `note to self`, `we should`, `pending` | submit-gating; **`WARN` under `--circulate`** |

Both are short, dumb and conservative, and that is what keeps this skill paper-agnostic: **the
renderer holds no paper's name, no section of one, and no phrase only one manuscript would
contain.** The bare-hole list is word-bounded and case-sensitive, because biomedical prose is full
of near misses — `TKI` is a tyrosine kinase inhibitor, `TBX21` a gene, `TBS` a buffer.

**They read the reader's text, not the author's.** Both scan the source with every comment and
every brace blanked, so a `{{ ! TBD residual }}` is a *marked* hole that the manifest and the gate
bit already handle, a `TODO` inside a comment is the author talking to the author, and a `FIXME`
inside a fence is literal text being shown. Only what the reader will actually meet is residue.

### Why the asymmetry between them

The bare-hole list is a **plain gating row**: it fails in every mode, `--circulate` still emits, and
`--submit` refuses. Its tokens are placeholders by convention, so a hit is nearly always real.

The workflow-phrase lint's tells are much likelier to be legitimate prose — a *pending* trial is a
fact about the literature and *"we should expect"* is a hedge — so it sits one tier softer: it
**warns** under `--circulate` and refuses only the submit question (`--submit`, and the `--check`
that `review-paper` runs). A deliberately dumb lint must not put a failing row in front of an author
who only wants to circulate a draft.

That is one field on the registry row, not a fourth tier. The tier answers one question — *would the
render emit something false?* — and folding a second question into it is how a tier comes to be
switched on twice.

### The calibration, and the cost it accepts

Two different things are recorded here, and they are not the same kind of claim.

**The measurement, made once, on a corpus that is not in this repo.** The bare-hole list scored
**zero hits** across all thirteen section drafts and the mechanical baseline — **zero false
positives in 74 KB of biomedical prose** — and **two hits** in the hand-revised manuscript, both
inside reader-facing claims. That is a historical fact about one corpus, cited from the defect audit
that produced it, and **nothing in this repo re-runs it**: the corpus is an unpublished manuscript
held elsewhere, so it cannot be a fixture here.

It is the measurement that warrants refusing rather than warning. Both hits sit in sentences that
assert something — one concluding *"which is ok for our analysis"* on the basis of a number that is
literally absent — so stripping either silently would convert a flagged gap into an unsupported
claim.

**The property, asserted on every test run.** What `tests/test_residue.py` checks is the behaviour
the measurement was evidence *for*: zero hits over a fixture built to carry every near-miss shape
biomedical prose contains, and two hits over the two shapes the audit recorded, both landing inside
reader-facing claims. A second test guards the guard — a calibration fixture that quietly lost its
near misses would score zero for the wrong reason and nobody would notice.

So the number cannot rot into a lie unnoticed, but do not read it as a live measurement: **if you
change either token list, the property is re-checked for you and the 74 KB figure is not.** Re-run
it against the corpus before trusting it again.

**The refusals are safe on this corpus, not in general, and the tests say so as an accepted cost:**

- `46,XX` and `47,XXX` are standard karyotype notation and `TK` is thymidine kinase. The bare-hole
  list rejects all three.
- `pending` and `we should` are ordinary academic English. The workflow-phrase lint rejects both.

A wrong refusal breaks a paper that never asked for any of this, so each is asserted in a **negative
fixture recording what the lint currently rejects** — documented cost, not desired behaviour — so
that sharpening either one is a deliberate, visible change and not a quietly loosened pattern.

**Neither is a configurable threshold**, and there is no flag to relax either. A configurable
refusal *is* the override these rules exist to prevent, wearing a config file. `--em-dash-threshold`
is not a counter-example: it tunes a **reported** row, which has no bucket in the gate and so cannot
reach the exit code at all. A threshold on a measurement is a reading instrument; a threshold on a
refusal is an override. What bounds the harm here instead is the tier: a karyotype paper circulates
freely and is refused only at submission, and a paper with a pending trial in its introduction does
not even see a failing row until it submits.

## The reported tier

Eight rows carrying **numbers, never verdicts**, and **never the exit code**. They are the prose
facts an author and a review both need. Gating submission is reserved to the annotation gate bit, so
a number here can be over any bar and `--submit` still emits.

| row | what it reports | threshold |
|---|---|---|
| `em dashes (threshold N)` | the count in body prose, and every line it sits on, each named once | **yes**, from the caller |
| `brief-to-prose overlap` | spans a unit's prose shares verbatim with its brief: how many are flagged, how many expected, and each flagged span quoted | none |
| `single-sentence body paragraphs` | the count, and the lines, over originating units only — plus **paragraph order** against the brief, which joins this row | none |
| `adversative ratio` | sentences that mark a turn, over sentences in scope | none |
| `subject openings` | how the sentences begin, most frequent first; every opening used more than once by name, the rest as a count of openings used once | none |
| `sentence length` | mean, coefficient of variation, share over 35 words | none |
| `locality test` | the tree an amendment moves, and every edge tying one unit to another | none |
| `supersession diff` | the two body word counts, and every structural loss this revision did not declare | **yes**, a constant no caller can move |

**The em-dash count is the one measured against a bar.** An em dash marks a logical relation without
naming it; the ban failed 98 times as a bullet a drafting session attested to, and it is exactly as
countable as a figure reference. So it is counted here, and the same count is a **blocking gate at
the drafting seam** — one implementation, invoked twice. **How to remove one is not this unit's
business:** that is a drafting invariant, enforced by judgement where the prose is written.

**The threshold is a finite non-negative integer**, supplied by the caller from its `## Style`, and
the skill default is **0**. There is no `off`, no `none` and no infinity: an effort may raise the bar
as far as it likes, visibly, and cannot remove the gate. **The count prints on both sides of the
bar**, so raising it makes the bar visible and never the number invisible.

**The other three are the Tier 4 diagnostics** — the style stanza's fourth tier, *a measured number
about the prose* — and they are reported together, **with no threshold at all**, by design. An em-dash count is a *ceiling on a
prohibited token* — zero is honestly achievable and ungameable, since removing a dash forces the
relation work and doing that work badly still yields an honest count. An adversative count would be
a *floor on a rhetorical move*, and the cheapest way to clear a floor is to sprinkle `however` over
paragraphs that concede nothing. **Read the adversative ratio as a consequence, never as a target:**
it moves because the em-dash gate forces relation-first rewriting. A low ratio beside a ladder full
of closed debts is the finding; a low ratio alone is not, and a genuinely procedural Methods section
concedes nothing, correctly.

**The three diagnostics are whole-document only** and print `SKIPPED — OUT OF SCOPE AT THIS
GRANULARITY` under `--section`: a rhythm number published per seam is a number a drafter tunes at the
seam, which is what carrying no threshold exists to prevent. **The em-dash count is not**, because it
blocks a drafting seam and a seam is one section. **Single-sentence body paragraphs run at both**, and
are suspended for a unit that only closes or restates a debt — a unit that is not one of argument,
and a panel caption is not one either, so the single-sentence signature does not transfer. The row
then prints `0 in 0 originating units`, which says why the number is zero.

**Paragraph order joins that row and takes the same suspension.** It reports how many of a unit's
paragraphs sit at the position of the brief item they are about — the one-bullet-per-paragraph walk,
counted — against the unit's **own paragraph count**, never against the item count and never against
the brief's derived paragraph budget: a draft that walks three items and then writes five more
paragraphs is not mirroring, a denominator stopping at the items would never look at the five, and a
budget is a plan where the paragraphs are the fact. It inverts for a non-originating unit exactly as
the single-sentence count does, because order tracking the brief is what a venue's field order and a
figure's lettering **mandate** there. Run either on a legend and it fires forever; the finite-verb
test carries the whole load.

A unit's brief items are the sentences of its reader-facing zone, less the ladder line: `Rung:`,
`Closes:`, `Opens:` and `Restates:` carry the unit's relation to the rung above it, and a relation is
bookkeeping rather than something the prose must convey. `## Argument` is read first, so a unit that
is **both originating and inventory-carrying** is ordered against its propositions, and an
originating unit whose only reader-facing zone is `## Inventory` is still ordered against its items.
**Where a brief is absent or unreadable this row stays silent about it**, because the overlap row
above already names every such unit, and two rows carrying one fact is how the two of them drift.

### The overlap instrument

The row that catches prose mirroring its own brief. A drafting session that walks its brief one
bullet per paragraph produces a list of labelled blocks rather than a manuscript, and the corpus this
design was calibrated on shows it happening — the audit's own phrase for what it found is
*transcribed near-verbatim from the briefs*.

**A shared span is a run of five words or more that a unit's prose and its brief share verbatim**,
measured inside one sentence of each and never across two: a run bridging a full stop is an
adjacency, not a phrase anybody moved. Case is ignored when matching, a run of nothing but function
words is not a phrase, and the match is word-level so a re-wrapped line still matches. The row then
**quotes the span as the prose wrote it** — what the author has to go and find is the phrase, and
`Nextflow >= 25.04.0` is not findable as `nextflow 25 04 0`.

**The zone the span came from decides the instrument, not the unit:**

| zone | instrument |
|---|---|
| `## Argument` | every shared span is **flagged**. Its propositions are phrased as what the reader must end up accepting, so verbatim overlap with one **is** the defect, and no exemption is needed |
| `## Inventory` | **the finite-verb test**: a shared span is **expected** unless it predicates. An inventory item is a fact the prose must convey — `MIT`, `ghcr.io/org/tool`, `scale bar required` all reach the prose as themselves — and one that predicates is either the drafter transcribing or the brief author slipping into phrasing, which is how the format enforces itself |

**The finite-verb test is a closed list plus one guarded rule, and deliberately no more.** The closed
list is the finite forms of *be*, *have*, *do* and the modals, which are closed-class words, so the
list is complete rather than a sample and needs no per-paper extension — which it must not have. The
one rule catches a third-person present verb: a word ending in `-s`, not closed off by punctuation,
not first or last in the span, and not preceded by a determiner, number or preposition. So
*illumination correction **suppresses** tile-boundary seams* is flagged and *5 DSL2 stages, DAPI as
common anchor* is not.

`-ed` is deliberately **not** a tell: *scale bar required* is an expected span, and an `-ed` rule
would flag it. A bare `-s` rule is equally refused — it reads every plural noun as a verb, and an
instrument that fires forever on a legend is an instrument nobody reads. The residual cost is a
plural noun that sits mid-span with no punctuation after it and no determiner before it, which can
read as a verb; the row prints the span, so a reader sees which one it was.

**Both this row and paragraph order are per-unit, so neither is ever out of scope.** `--section`
narrows them to the one unit; whole-document granularity measures every unit and names each in the
row.

**Not yet wired: the `## Style` term exemption.** The exemption list for the overlap check is the
effort map's `## Style` *terms*, and the map is not yet an input to this unit — it arrives with the
style stanza. Until then a mandated term long enough to be a substantial phrase is reported. The
exemption covers **terms, never sentences**, which is what keeps the check from being hollowed out by
its own carve-out.

### What the numbers are measured over

Scope is **defined, not assumed**, or the count fires on text no author wrote as prose. In scope: the
body prose of every anchored slot at this granularity. Out of scope: HTML comments, annotation
braces, citation groups, pipe-table rows, and fenced code blocks. There is no third case for a
bracket span with no key — **every bracket character in prose belongs to a citation group, enforced
by parse**, so a span with no key never reaches a diagnostic. Headings never arrive at all — the
skeleton owns them and the render injects them. Every excluded span is **blanked rather than
deleted**, so a reported line number is the author's own line number.

A sentence ends at `.`, `!` or `?` followed by whitespace, unless what precedes it is an abbreviation
or an initial. A word is a whitespace-delimited token with a letter or a digit in it, so a standalone
dash is punctuation. A paragraph is a run of non-blank lines.

### The supersession diff

```
render-paper MANUSCRIPT.working.md --check --section methods --supersedes 9f31c02
```

When a unit is re-drafted, the author learns **what the revision silently lost**. The row compares
the **old render** of that unit against the **new render** and reports five structural losses:

| loss | what it says |
|---|---|
| body word count | *body 2767 → 584 words (down 78%, past the 25% bar)* — the counts print either way |
| a heading-level block gone | *heading lost (`### Registration`)*, read off the two renders, so a level change counts too |
| a figure or panel reference gone | *figure reference lost (`@fig:overlay`)* |
| a reference that lost its only in-text anchor | *reference lost its only anchor (`@muhlberg2020`)* |
| a gate-bit annotation that vanished unclosed | *gate annotation vanished unclosed (`⟦HOLE: best-arm Dice⟧`)* |

**A diff-relative reading is the wrong instrument for a fresh draft and the right one here.** For a
`revise` ticket the diff is not an approximation of the question, it *is* the question. A fresh draft
has no old side, and the row says *not a supersession — no `--supersedes` ref* rather than passing.

**It is a finding, never a gate.** A revision that correctly removes 2,000 words, because the ladder
amendment deleted the rung those words served, must not be blocked by its own success. Two
mechanisms hold that rather than one rule: the row sits in the reported tier, which has no bucket the
exit code reads, and it prints a number, which has no `FAIL` to print.

**There is no keep-list field** on a revision, here or anywhere in the interface. A list of what must
not change would be written by the same agent that drops a claim, and it would omit the dropped
claim too. So the drop-guard is **mechanical**, and the drop bar is a **constant** rather than an
option: the row cannot gate, so a knob would buy an effort nothing it does not already have from the
two counts the row always prints.

**Where the old side comes from.** Renders are ephemeral, but the render is a **pure function of the
source** and git is the audit trail: the source is checked out at the commit the original `draft`
ticket closed at — as a `git archive` stream into a scratch directory, so neither the index nor the
working tree is touched — and **the same render** runs over it, at the same section anchor.
Post-promotion one side comes from `MANUSCRIPT.working.md` and the other from the frozen
`drafts/<unit>.md`, which is well-defined because **anchors, not headings, are what live in the
source**. Every way that can fail — no `git`, a ref nobody kept, a tree with no source in it, a
source the old skeleton can no longer describe — prints as `old side unavailable — …` in the row and
**reaches no exit code**.

**One unit at a time**, so this is the one row that is *section granularity only*: over a whole
document it prints `SKIPPED — OUT OF SCOPE AT THIS GRANULARITY`, the same way a whole-document row
does under `--section`.

**A figure and a panel are one token class**, so the check needs no per-class branch: a lost panel
reference reports in the same class, in the same words, as a lost figure reference.

**Deletion is the only closure, so *gone* alone says nothing** about the fifth loss. Substituting the
real value is exactly how a hole is closed, and it leaves the sentence standing. What separates the
closure from the loss is therefore the **prose**: a gate-bit annotation is reported only when the
paragraph that carried it left no verbatim run of five words behind. A filled hole leaves its
paragraph; a deleted block leaves nothing.

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
   lines, and so may a brace. The renderer emits no comment of its own, so there is no such thing as
   a comment the render preserves. Inside a fenced code block nothing is parsed at all — not a
   comment, not a brace, not an anchor, not a heading — because a source showing anchor syntax in a
   fence is showing it, not using it.
3. **Concatenate**, pre-promotion only. Post-promotion the source is already one document.
4. **Mark the output as generated.** Every render opens with a front-matter banner naming the render
   as output. It is not a comment, because a render that emits its own comments is how a comment
   leaks into reader-facing text.
5. **Never silently strip a gap.** Every gap comes out as one uniform, greppable token, so one grep
   finds them all: `⟦HOLE: <label>⟧` for a brace and for an unfilled slot or title alike, and
   `⟦SLOT: <label>⟧` for a venue field. Silently dropping one would turn a flagged gap into an
   unsupported claim the author never learns about — strip the token and the sentence is
   ungrammatical, drop the clause and an unsupported assertion ships. A **parent** slot is the
   exception that is not a gap: its own prose is permitted rather than owed, so a parent with
   children renders its heading and lets the children carry the prose.
6. **Emit the manifest.** Every open annotation, grouped by `@owner` so it is sendable, recomputed
   from the source on every render so it cannot go stale.
7. **Resolve the references.** Citations and figures by **first-mention order in the assembled
   document**, and **panels by their legend's declaration order** — a figure number appears only in
   the rendered text, but a panel letter appears in the artwork too, and a render can renumber prose
   but cannot repaint a figure. The reference list is built from the **cited keys**, so an orphaned
   entry is impossible by construction rather than checked for, and the bibliography is read from its
   declared path and never contained. At `--section` granularity every token is left **unresolved and
   visible**, and no placeholder form is invented. See [the citation surface](CITATIONS.md) and
   [figures and panels](FIGURES.md).
8. **Parse the legend declaration blocks.** A legend is the first draft artifact with machine-read
   structure: its `## Panels` block fixes the panel names and, by its entry order, their letters.

## What it must not do

- Hold any paper-specific text. No bibliography, no section names, no venue citation style, no
  per-paper fixes. Every judgement fix is written back into the **source**, never encoded in the
  generator: a fix that lives in the generator regresses the moment the generator stops being run.
- Create any annotation **in the source**. It renders a gap as a token; it never writes one. The
  creation-rights grid is in [the channel](ANNOTATION-CHANNEL.md): `write-paper` may create all
  three behaviours, `review-paper` may create `SILENT` only, and the render and the assembler create
  none.
- Hold any spine authority beyond the mechanical bookkeeping walk.
- Judge anything. Every check is decidable by parse; anything else belongs to a judgement axis.
- **Expose any refusal as a configurable threshold.** There is no flag, no file and no environment
  variable that relaxes either [residue lint](#the-two-residue-lints), and the same holds for every
  other refusal here. A configurable refusal *is* the override these rules exist to prevent, wearing
  a config file. `--em-dash-threshold` is the one threshold on the interface and it is not an
  exception: it tunes a **reported** row, which cannot reach the exit code. Where a refusal is known
  to cost something, the cost is carried in a **test** asserting what it currently rejects, so
  changing it is deliberate and visible.

## Vocabulary

*unit* — one top-level skeleton slot and its subtree; the thing a rung, a brief, a `draft` ticket and
a word budget all key on, 1:1. *slot* — a section position in the heading tree. **Note the deliberate
collision:** in the annotation channel, `SLOT:` inside braces marks a *venue back-matter field*. Two
different concepts, one word; every passage where both could apply qualifies which is meant.
*originating* / *non-originating* — a unit that opens a debt, versus one that closes, restates or
inventories. *argument brief* / *inventory brief* — the two brief formats, one axis: whether the unit
opens a debt. *proposition* — one item of an argument zone. *shared span* — a run of words a unit's
prose and its brief have verbatim in common. *HOLE* / *SLOT* / *SILENT* — what the reader sees, and
the only render-behaviour vocabulary there is; *the gate bit* — whether an annotation blocks
`--submit`, independent of what the reader sees. **There is no kind enum**: the two axes plus the
free-text `@owner` carry everything, and `@owner` is the one that makes the manifest sendable.
*key* — the stable name a source cites a source by; *citation group* — a `[…]` span holding keys and
`;` and nothing else; *the reference list* — what the render builds from the cited keys, which is
never the bibliography and never all of it. *residue* — unfinished text that is grammatical
reader-facing prose, so the annotation channel never sees it and no bracket-stripping can find it;
what [the two lints](#the-two-residue-lints) exist for. *name* — the stable identifier a source
refers to one of this document's own objects by; *roster* — the manifest of those objects, names
only; *panel* — a figure that lives inside another figure, referenced by the same token, with
parentage carried by containment; *declaration block* — a legend's `## Panels` section, whose entry
order **is** the lettering; *reference literal* — a figure number, a panel letter or a positional
name typed into prose, which is a parse error. See [figures and panels](FIGURES.md).

## Tests

`pytest` from the repository root. The tests invoke this script as a subprocess over fixture papers
in `tests/fixtures/` and assert on the exit code, the emitted document and the verdict table; the
table and the document are compared against golden files verbatim, because a formatting change is an
interface change. No test imports the script.
