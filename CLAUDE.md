# skills

Yinxiu Zhan's skills for planning and writing academic papers, shipped as an installable
Claude Code plugin. Every skill has a `SKILL.md` under `skills/<name>/`, and most are nothing else.

A skill that holds mechanism rather than judgement also ships what that mechanism needs, inside its
own directory and consumed only from there — `render-paper` ships `scripts/render_paper.py` and the
formats of the two files it parses. A skill never reaches into another skill's directory, because a
partial install would leave it calling a file that is not there.

## Tests

`pytest` from the repository root. Tests and fixtures live in `tests/`, outside every skill
directory, so nothing in the test tree ships to an installer. The runtime is Python 3 and the
standard library; `pytest` is a test-only dependency.

Every rule a `SKILL.md` states is either a mechanism or a deletion; a rule that is neither is not
finished. `tests/test_skill_contract.py` holds the mechanically decidable half of that over all
five skill files, and [`docs/mechanism-sweep.md`](docs/mechanism-sweep.md) records the judgement
half — every rule, what makes it bite, and the residue that nothing does.

## Agent skills

### Issue tracker

Issues live as GitHub issues in `zhanyinx/skills`, managed with the `gh` CLI.
See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical roles, each label string equal to its name: `needs-triage`, `needs-info`,
`ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — one `CONTEXT.md` and `docs/adr/` at the repo root, both created lazily rather
than upfront. See `docs/agents/domain.md`.
