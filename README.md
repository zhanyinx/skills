# skills

Skills for Claude / ChatGPT and other models.

Each skill lives under `skills/<name>/SKILL.md`, describing when and how it applies.

## Install

Install into your project (or a global agent config) with the [`skills`](https://github.com/vercel-labs/skills) package manager — no clone needed:

```bash
# into the current project's .claude/skills/
npx skills@latest add zhanyinx/skills

# or globally, into your user-level agent config
npx skills@latest add zhanyinx/skills --global
```

Or add it as an auto-updating Claude Code plugin marketplace:

```
/plugin marketplace add zhanyinx/skills
/plugin install zhanyinx-skills@zhanyinx
```

## Skills

### wayfinder

Plan a huge chunk of work — more than one agent session can hold — as a shared map of investigation tickets on your issue tracker, and resolve them one at a time until the way to the destination is clear.

Based on the [wayfinder skill by Matt Pocock](https://github.com/mattpocock), with one addition: a **`draft` ticket type** and the surrounding "Plan, don't do" override that lets a map carry execution — not just decisions — for academic writing efforts. A `draft` ticket plans, then produces prose via `write-paper`, checkpoints it through `review-paper`, and a whole-piece `review-paper` pass runs once every section is assembled. This connects wayfinding to the two paper skills below.

### write-paper

Draft **one unit** — one top-level section and its subtree — from its brief, the claim ladder, the skeleton and the style stanza. The seam is given rather than negotiated, and a session receives the whole ladder, its own brief and the sources that brief cites and nothing else: no other unit's brief, no other unit's prose. So cross-section repetition is something a drafting session cannot author around, and it stays visible to the one pass that may cut it.

It carries **construction rules only** — rules that hold while the sentence is being written, not after. Body prose, no headings at any level, every figure, panel and citation by stable name, and anything unverifiable written as a hole carrying the gate bit rather than a plausible-sounding placeholder. It invokes `render-paper` at each seam, treats an em-dash count over the threshold as blocking that seam, and reviews **the render** rather than the annotated source.

### review-paper

Review a piece of academic writing since a fixed point along two axes — **Fidelity** (does the text accurately represent its evidence, sources, and literature?) and **Craft** (is the prose clear, non-redundant, correctly hedged?) — plus a direct **cross-reference integrity** check. The two axes run as parallel sub-agents; results are reported side by side.

### assemble-paper

Promote the independently-drafted units into one annotated working manuscript, then make the one editorial pass that reads the whole document end to end. It holds the two jobs nothing else in the pipeline can do: the promotion is one-way, so everything after it is genuinely whole-document work; and the cut it makes — the same fact stated in full in three units — is invisible to a drafting session, which never sees another unit's prose, and unmakeable by a review, which may only write annotations that emit nothing.

Every mechanical duty is absent by design: no concatenation, no headings, no numbering, no spine authority. When it de-duplicates it leaves a callback that **names the proposition and never the section**, so the pass cannot turn repetition into a table of contents in prose.

### render-paper

Build a paper's document from its `skeleton.md` and run the mechanical gate over it. It injects every heading from the skeleton on every pass, strips the author-facing comment channel by syntax, marks every gap as a conspicuous token, and reports a per-check verdict table in which a check that never looked is a printed row rather than a silent pass. The answer to *"is this paper done"* is an exit code: `--circulate` always emits, `--submit` refuses while any gate bit is open, `--check` runs the gate alone. A fourth mode, `--scaffold`, writes rather than reads: it seeds one unit's source with every anchor in that unit's subtree, in skeleton order, so a drafting session cannot type a misordered or missing one.

It holds every mechanical duty and no prose judgement, so no two skills can disagree about a mechanical fact. Python 3, standard library only; it ships its own script and the formats of the two files it parses — [`skeleton.md`](skills/render-paper/SKELETON-FORMAT.md) and [`spine.md`](skills/render-paper/SPINE-FORMAT.md).

## How they fit together

`wayfinder` plans a paper as a map of tickets. Its `draft` tickets call `write-paper` to produce each section, and `review-paper` checks each section at its checkpoint. Once every draft has closed, `assemble-paper` runs once — it promotes the sections into the working manuscript and makes the whole-document editorial pass — and `review-paper` then runs over the assembled whole. `render-paper` is what all four call for anything mechanical: it builds the document and runs the gate, and its exit code is the one refusal authority.

## Tests

```bash
pip install pytest
pytest
```

The suite runs from the repository root and drives `render-paper` through its CLI over the fixture papers in `tests/fixtures/`. Tests and fixtures sit outside every skill directory, so nothing in the test tree ships to an installer.
