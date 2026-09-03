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

### assemble-paper

Stitch the independently-drafted sections and figure legends of a manuscript into one continuously-readable document — resolving transitions, redundant seams, and voice/terminology drift between sections — without altering claims, evidence, or citations. Runs once every section draft exists, before the final whole-manuscript `review-paper` pass.

### review-paper

Review a piece of academic writing since a fixed point along two axes — **Fidelity** (does the text accurately represent its evidence, sources, and literature?) and **Craft** (is the prose clear, non-redundant, correctly hedged?) — plus a direct **cross-reference integrity** check. The two axes run as parallel sub-agents; results are reported side by side.

## How they fit together

`wayfinder` plans a paper as a map of tickets. Its `draft` tickets call `write-paper` to produce each section, and `review-paper` checks each section at its checkpoint. Once every section draft has closed, `assemble-paper` stitches them into one manuscript and `review-paper` runs a final pass over the assembled whole.

## Working on these skills

The `SKILL.md` files in this repository are the source of truth. If you develop the skills from a clone, `scripts/link-skills.sh` replaces each installed skill directory with a symlink to this repo's `skills/<name>`, so an edit committed here is the edit that runs — with no copy step on release:

```bash
scripts/link-skills.sh --dry-run   # show what would change
scripts/link-skills.sh             # link ~/.agents/skills/<name> -> skills/<name>
```

It is idempotent, and moves any real directory it finds in place aside to `<name>.pre-link-backup` rather than deleting it. It manages `~/.agents/skills` and nothing else — set `AGENT_SKILLS_DIR` to point it elsewhere. If you installed the skills with `npx skills` or the plugin marketplace above, that installer owns its own layout and this script isn't for you.
