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

Draft a piece of academic writing — paper section, chapter, grant, or assay/protocol report — from a spec, outline, or set of results/notes, with reference management and consistent cross-referencing. Drafts at pre-agreed seams, never fabricates a citation, and checks fidelity/craft at every checkpoint via `review-paper`.

### review-paper

Review a piece of academic writing since a fixed point along two axes — **Fidelity** (does the text accurately represent its evidence, sources, and literature?) and **Craft** (is the prose clear, non-redundant, correctly hedged?) — plus a direct **cross-reference integrity** check. The two axes run as parallel sub-agents; results are reported side by side.

### render-paper

Build a paper's document from its `skeleton.md` and run the mechanical gate over it. It injects every heading from the skeleton on every pass, strips the author-facing comment channel by syntax, marks every gap as a conspicuous token, and reports a per-check verdict table in which a check that never looked is a printed row rather than a silent pass. The answer to *"is this paper done"* is an exit code: `--circulate` always emits, `--submit` refuses while any gate bit is open, `--check` runs the gate alone.

It holds every mechanical duty and no prose judgement, so no two skills can disagree about a mechanical fact. Python 3, standard library only; it ships its own script and the formats of the two files it parses — [`skeleton.md`](skills/render-paper/SKELETON-FORMAT.md) and [`spine.md`](skills/render-paper/SPINE-FORMAT.md).

## How they fit together

`wayfinder` plans a paper as a map of tickets. Its `draft` tickets call `write-paper` to produce each section, and `review-paper` checks each section at its checkpoint and the whole piece once assembled. `render-paper` is what all three call for anything mechanical: it builds the document and runs the gate, and its exit code is the one refusal authority.

## Tests

```bash
pip install pytest
pytest
```

The suite runs from the repository root and drives `render-paper` through its CLI over the fixture papers in `tests/fixtures/`. Tests and fixtures sit outside every skill directory, so nothing in the test tree ships to an installer.
