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

## The two files it reads

Both are declared inputs at the paper root, beside the source:

- [`skeleton.md`](SKELETON-FORMAT.md) — the heading tree, its order and levels, the roster, the
  document title and the venue limit.
- [`spine.md`](SPINE-FORMAT.md) — the claim ladder: the central claim, and one rung per unit.

`render-paper` is their only parser, which is why it documents their formats. **No skill owns either
file.** A planning ticket creates each; a drafting session may amend its own slot only.

## The channel it reads inside the source

[The annotation channel](ANNOTATION-CHANNEL.md) — `{{ … }}` **must** appear in the render, an HTML
comment **must never** — plus the manifest, the gate bit, and the creation-rights grid. Same reason
the two file formats are documented here: `render-paper` is the channel's only parser.

```
{{ [!] [SLOT:] [@owner] <label> }}      ! is the gate bit; bare is a HOLE; SLOT: is a venue field
<!-- !@owner <label> -->                SILENT; in the manifest iff it opens with `!` or `@`
```

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
- **Submit-gating** iff the render is faithful but the work is unfinished: an open annotation
  carrying the gate bit, an unfilled skeleton slot, or an unfilled document title.
- **Parse error** iff the source cannot express the thing at all: a malformed anchor, a heading in a
  source, an unclosed comment, a malformed or unclosed brace, a malformed `skeleton.md` or
  `spine.md`, a declared input that is missing. **Only a brace can refuse, never a comment** — a
  parse error is for what the source cannot express into *reader-facing* prose, and a comment never
  reaches the reader.

A `warnings` block on stderr sits under all three tiers and moves **no** exit code: a brace label
over 80 characters, a bare brace standing alone in its own block, a label that opens `slot:` in case
`SLOT:` was meant, and a keyed comment that matches no brace. A hard cap or a refusal on any of them
was rejected — each over- and under-fires at once, and a wrong refusal breaks a paper that never
asked for any of this.

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

  skeleton / spine grammar  PASS
  source grammar            PASS
  brace grammar             PASS
  slot integrity            SKIPPED — OUT OF SCOPE AT THIS GRANULARITY
  unit / rung pairing       PASS
  originating slot children PASS
  annotations (gating)      PASS
  unfilled skeleton slot    FAIL — 1 (`methods-imaging`)

  6 pass, 1 fail, 1 out of scope
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
- **Three verdicts only:** `PASS`, `FAIL`, and `SKIPPED — OUT OF SCOPE AT THIS GRANULARITY`. A check
  that never looked is a **printed row**, never silently a pass. One word cannot carry the difference
  between checked-and-fine and never-checked, which is why no single-word verdict is emitted anywhere.
- A `FAIL` carries its count and what failed.
- The table closes with the counts and the line saying it is **not** a claim that the section (or the
  document) is finished. A gate with no FAILs is a statement about mechanism, never about judgement.
- **A row is never printed without a check behind it.** The registry grows as the checks are built;
  a row with nothing behind it would read as a pass, which is the defect this table exists to kill.

The three parse-tier rows are printed as `PASS` whenever a table prints at all, because a parse-tier
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

## What it must not do

- Hold any paper-specific text. No bibliography, no section names, no per-paper fixes. Every
  judgement fix is written back into the **source**, never encoded in the generator: a fix that lives
  in the generator regresses the moment the generator stops being run.
- Create any annotation **in the source**. It renders a gap as a token; it never writes one. The
  creation-rights grid is in [the channel](ANNOTATION-CHANNEL.md): `write-paper` may create all
  three behaviours, `review-paper` may create `SILENT` only, and the render and the assembler create
  none.
- Hold any spine authority beyond the mechanical bookkeeping walk.
- Judge anything. Every check is decidable by parse; anything else belongs to a judgement axis.

## Vocabulary

*unit* — one top-level skeleton slot and its subtree; the thing a rung, a brief, a `draft` ticket and
a word budget all key on, 1:1. *slot* — a section position in the heading tree. **Note the deliberate
collision:** in the annotation channel, `SLOT:` inside braces marks a *venue back-matter field*. Two
different concepts, one word; every passage where both could apply qualifies which is meant.
*originating* / *non-originating* — a unit that opens a debt, versus one that closes, restates or
inventories. *HOLE* / *SLOT* / *SILENT* — what the reader sees, and the only render-behaviour
vocabulary there is; *the gate bit* — whether an annotation blocks `--submit`, independent of what
the reader sees. **There is no kind enum**: the two axes plus the free-text `@owner` carry
everything, and `@owner` is the one that makes the manifest sendable.

## Tests

`pytest` from the repository root. The tests invoke this script as a subprocess over fixture papers
in `tests/fixtures/` and assert on the exit code, the emitted document and the verdict table; the
table and the document are compared against golden files verbatim, because a formatting change is an
interface change. No test imports the script.
