# The mechanism sweep

**Every rule stated in prose in the five `SKILL.md` files, and what makes it bite.**

This is the manual half of the skill contract check. It exists because of one measurement: the
em-dash ban was a rule in the right skill, unambiguously worded, and it was violated 98 times
through six clean reviews. Nothing counted, so nothing caught it, and a Craft review that read it
as a labelled heuristic weighed 98 of them and called the prose fine. The conclusion the rework
drew is that **a rule is finished when it is a mechanism or a deletion, and not when it is
well-written.**

So this sweep asks one question of every rule on the page: *what happens if a session ignores it?*
Five answers count as a mechanism. A rule with none of them is residue, and §3 lists what residue
survives and why.

| mechanism | what it is | example |
|---|---|---|
| **gate row** | a `render-paper` check with a verdict and a bucket in the exit code | a reference literal in prose is a parse error |
| **unexpressible** | the source cannot say the wrong thing | headings are injected, so a source cannot carry a drifting heading tree |
| **refusal at load** | the session stops before producing anything | `## Style` naming a Tier 2 invariant as a key |
| **paired re-derivation** | two units derive the same thing independently, and disagreement *is* the finding | rationale leak; the composed style stanza |
| **test** | an assertion in `tests/` over the shipped text or the script | this sweep's companion, `tests/test_skill_contract.py` |

The sweep was run over `origin/main` at `4be8288`, after tickets #13–#19 landed.

---

## 1. Rules with a mechanism, by skill

### `render-paper`

Every rule this skill states is a check it runs, which is the point of the unit: it is the pipeline's
only mechanism-holder, and the other four invoke it rather than restating it. The fifteen gating
rows and eight reported rows are specified in `SKILL.md` and asserted in `tests/test_render_paper.py`,
`test_annotations.py`, `test_citations.py`, `test_figures.py`, `test_residue.py`,
`test_supersession.py` and `test_worked_example.py`. Its file-format rules are enforced by being the
only parser of the formats.

One rule here is about the skill rather than the document — *no threshold on a refusal, and no flag
to relax one* — and its mechanism is the absence of the flag. There is no configuration surface to
find.

### `write-paper`

| rule | mechanism |
|---|---|
| body prose only, no headings at any level | **unexpressible** — headings are injected from the skeleton every render; a heading in a source is a parse error |
| write only between the anchors | **unexpressible** — a misordered, duplicated or omitted anchor is a parse error, and prose after a child anchor renders under that child |
| references by stable name, never a number or a positional name | **gate row** — `reference literals` |
| inside brackets, keys and `;` only | **gate row** — `citation group` |
| a name not in the roster | **gate row** — `slot / roster integrity` |
| an unverifiable claim becomes a gate-bit hole | **gate row** — `annotations (gating)`, plus `bare holes` for the residue form that is grammatical prose |
| the debt check — inherited debts closed, own debts left open | **gate rows** — `chain bookkeeping`, `debt precedence`, `unit / rung pairing` |
| an originating unit has no child slots | **gate row** — `originating slot children` |
| the em-dash count blocks the seam | **gate row** — `em dashes (threshold N)`, run as a command over the drafted text rather than attested to. The threshold is a finite non-negative integer, so the gate cannot be switched off |
| `## Style` may not name a Tier 2 invariant | **refusal at load** — the key set is closed, so the collision is decidable rather than a judgement call |
| the composed stanza is echoed with provenance | **paired re-derivation** — `review-paper` composes it again from the same two inputs and never accepts this echo; disagreement is a finding |
| a justifying clause answers a named, reader-raisable objection | **paired re-derivation** — the `obj` comment is the drafter's naming; the Craft axis re-derives the objection from the rendered sentence and never reads the comment |
| a framing constraint is obeyed by not invoking the frame | **paired re-derivation** — the `Rationale Leak` smell's negated-frame clause catches the denial form. The construction and its counter-example both ship here, asserted by `test_skill_contract.py` |
| name the proposition, never the container | judgement, with a stated test — delete every section name and reshuffle; a legal sentence still parses. The **narrow** form is what is enforced: naming a container in the act of closing a debt |
| no filled Tier 3 value ships | **test** — `test_style_stanza.py` over the asset, `test_skill_contract.py` over all five skill files |
| the brief carries no ban, and the paragraph rule is stated here and nowhere else | **test** — `test_shipped_templates.py` asserts each template's zone set is closed and exactly one zone is reader-facing, so a template cannot grow a zone holding an instruction to the writer. `BRIEF-FORMAT.md` states the ban; the rule itself lives in step 5 |
| no rule may be satisfied by an unconditional transform | judgement, and it binds the whole pipeline. Both of this skill's statements of it are asserted to agree, and so is `review-paper`'s |

### `assemble-paper`

| rule | mechanism |
|---|---|
| the manuscript order is the skeleton's | **unexpressible** — a malformed `skeleton.md` is a parse error, so there is nothing to assemble until it is fixed |
| promotion before the editorial pass, and it is irreversible | **structural** — the pass is whole-document work and a through-line cannot be revised across thirteen files. The write-authority grid gives this skill exactly one writable artifact |
| scan the whole piece, not just the boundaries | **structural** — promotion is what puts the whole piece in front of one reader. Sampling unit by unit is the vantage point every drafting session already had, and it is the promotion that removes it |
| the callback names the proposition, never the container | judgement, with the same stated test as the drafting rule, plus the closed bullet set asserted by `test_skill_contract.py` |
| renumbers nothing, checks no heading, creates no annotation | **unexpressible** — all of it happens in the render, on every pass |
| deletion is the only closure; no change log | **deletion** — the step that maintained one is gone, and `RESOLVED` appears nowhere. Both asserted |
| reads only `terms` from `## Style` | **test** — no other style key is named in this file |

### `review-paper`

| rule | mechanism |
|---|---|
| the gate is the only refusal authority | **gate row** — this skill emits no verdict and no exit code; a finding becomes blocking only as a SILENT annotation carrying the gate bit, which the gate then enforces |
| this skill may create SILENT annotations only | **gate row** — the creation-rights grid, enforced by the render |
| every axis reads the render, never the source | **unexpressible** — the render strips the comment channel, so an axis reading it cannot see annotation scaffolding as prose |
| the fixed point is a pair, and the gate takes none | **gate row** — the gate always reads the whole render at the granularity asked for, so an inherited defect cannot be invisible |
| `--supersedes` only for a supersession | **gate row** — the row reports *not a supersession* when it is absent, so the state is printed rather than assumed |
| derive the stanza yourself; never accept the drafter's echo | **paired re-derivation**, the other half of `write-paper`'s echo |
| re-derive the objection; never read the `obj` comment | **paired re-derivation** — and the render strips the comment anyway, so the wrong input is not reachable |
| the Tier 2 invariants are not overridable | **refusal at load** for the key collision; **test** for the two copies agreeing |
| `Em Dash` is not a smell | **deletion** — it left the baseline for a gate row that cannot weigh it. Both halves asserted |
| there is no `CLEAN` verdict and no single-word verdict at all | **test** — every occurrence of the token in all five files is asserted to be a statement denying it |
| the Tier 4 diagnostics carry no threshold | **structural** — they have no bucket in the exit code, so a bar attached to one could not do anything |

### `wayfinder`

| rule | mechanism |
|---|---|
| the map records decisions, never recomputable state | **test** — `test_wayfinder_map.py`, including the outright ban on asserting a document property |
| charting instantiates every declared section | **test** — same module |
| `draft` and `revise` are keyed by unit, one line each | **test** — same module |
| a `revise` names no keep-list | **deletion**, replaced by a mechanism — the supersession diff, reconstructed from the recorded commit ref |
| a `revise` checkpoint is a strict superset, never narrowed | **gate row** — the full render, the full review, plus the supersession row |
| a `revise` may not be satisfied by an unconditional transform | judgement, the pipeline-wide Tier 2 ban |
| a load-bearing gap does not hold its ticket open | **gate row** — it is written back as a `!` annotation, so the refusal moves to `--submit` |
| the draft map's `## Notes` carries only per-effort facts | **test** — same module |
| a `draft` closes on zero gate FAILs, with every finding fixed, written back, or dispositioned — silence being none of the three | **gate row** for the FAIL half; **test** for the three dispositions, which this file and `review-paper` both state |
| the checkpoint reviews the render and never the annotated source | **test** — the rule is restated in three files, and all three are asserted to carry it |

The last two are the duplications `wayfinder` was always going to carry: a ticket type has to state
its own closing condition, and a skill may not read another skill's directory. The third of that set
is the abolished `CLEAN` verdict, asserted over all five files.

---

## 2. What the sweep changed

One finding, and it is the reason the sweep is part of the ticket rather than a nicety.

**The transform ban is stated three times, and only two of the three were guarded.**
`write-paper` states it twice — once in step 5 as a construction rule binding the sentence being
written, once under `## Craft invariants` as the Tier 2 invariant it is — and `review-paper` states
it a third time, binding the fixes a reviewer recommends. The spec fixes all three, so this is not
a duplication to remove; it is three copies of one fact that can drift. The cross-file pair was
already asserted equal. The pair inside `write-paper` was not, and now is.

---

## 3. Residue — rules with no mechanism, and why each stays

Four. Each is recorded rather than deleted, and the reason is given, because an undocumented
acceptance is how the em-dash bullet survived six reviews.

**`write-paper`: "No sentence grades its own importance."** The one construction rule with no
downstream consumer at all — no gate row, and no smell in the Craft baseline named for it. Its
nearest neighbour is `Overclaim`, which catches the qualifier family (`the first`, `entirely`,
`essentially`) but not a sentence announcing its own weight. It stays because the spec fixes the
step-5 list verbatim and fixes the baseline at fifteen smells; adding a sixteenth or dropping the
bullet would each be a deviation decided here rather than there. **Recorded as the accepted cost:
this rule is enforced by the drafting session's compliance and by nothing else.**

**`review-paper`: the gate table is reported verbatim — not summarised, reranked, merged, or
restated in prose.** Nothing can check a report, because a report is not an artifact the pipeline
reads back. What is guarded is that the instruction stays on the page, and that the vocabulary it
would be restated into does not exist: there is no `CLEAN` and no single-word verdict, both
asserted. **Accepted: the residue is the report itself, and it is unreachable by construction.**

**`wayfinder`: refer to every ticket by name, and never resolve more than one ticket per session.**
Both govern narration and session conduct rather than an artifact, so no mechanism is possible —
there is nothing on disk to check. Both predate this rework and neither is touched by it.
**Accepted, and out of scope for this effort.**

**`wayfinder` uses *slot* in a third sense.** The settled vocabulary names two — a section position
in the heading tree, and `SLOT:` in an annotation brace marking a venue back-matter field — and
requires any passage where both could apply to say which is meant. `wayfinder` carries no
annotation brace, so the deliberate collision cannot bite there; the contract check asserts exactly
that, and asserts the qualification in the three files where it can. But `wayfinder` also writes
that a revision's index line "takes the original's slot", which is a line's position in the map
index and neither settled sense. **Accepted: the map index is not a heading tree and carries no
braces, so neither settled sense is reachable in that passage, and the phrase is ordinary English
for a position.** Recorded so the next reader does not take it for the vocabulary.

---

## 4. How to re-run it

The mechanical half is `pytest tests/test_skill_contract.py`, which runs in the same suite and in
CI. The manual half is this document, and it goes stale the moment a `SKILL.md` gains a rule. The
question to ask of any new one is the question at the top: *what happens if a session ignores it?*
If the answer is "nothing", the rule is not finished.

The contract check's own assertions were verified to bite by reintroducing each defect it names —
29 mutations across the five files, every one caught. Two holes surfaced that way and were closed:
a literal restored across a line break, and a literal restored capitalised at the head of a
sentence. Both had passed a naive `in` check.
