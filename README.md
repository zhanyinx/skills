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

## How they fit together

`wayfinder` plans a paper as a map of tickets. Its `draft` tickets call `write-paper` to produce each section, and `review-paper` checks each section at its checkpoint and the whole piece once assembled.
