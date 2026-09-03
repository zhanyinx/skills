---
name: review-paper
description: "Review a piece of academic writing — paper, grant, or assay/protocol report — in three parts: the mechanical gate, whose verdict table is reported verbatim over the whole render, plus Fidelity (does the text represent the evidence, sources and literature behind it?) and Craft (is the prose well-built — clear, non-redundant, correctly hedged?), which run as parallel sub-agents over a paired fixed point. The gate takes no fixed point and no single-word verdict is emitted. Use when the user wants to review a draft, a revision, one unit of a manuscript, or a grant, or asks to \"check this draft.\""
---

Three parts, and they differ in kind rather than in subject:

- **The gate** — `render-paper`'s per-check verdict table, reported **verbatim**. Mechanical, and
  the only refusal authority in the pipeline. It takes **no fixed point**: it always reads the whole
  render at the granularity asked for, so a defect inherited unchanged from an earlier draft cannot
  be invisible.
- **Fidelity** — does the text accurately represent the evidence, data and literature it cites; does
  it match what the brief and the claim ladder say this unit establishes; and does every debt it
  claims to close actually close?
- **Craft** — is the prose itself well-built: clear, non-redundant, consistently termed, correctly
  hedged?

Fidelity and Craft run as **parallel sub-agents** so they don't pollute each other's context. The
gate runs first and directly, because it is a command rather than a judgement.

> **This skill reports; it never gates.** A finding becomes blocking by being written back into the
> source as a SILENT annotation carrying the gate bit, which the gate then enforces — see step 8. So
> there is exactly one refusal authority, it is mechanical, and a serious judgement finding reaches
> it through a documented route rather than through a second, arguable one. Report-versus-refusal is
> a false dichotomy.

## Process

### 1. Pin the fixed point — for the judgement phase only

The gate (step 2) takes no fixed point; it always reads the whole render. Steps 3-7 do.

The fixed point is a **pair**: `(previous render, skeleton revision)`.

```
skeleton revision SAME     -> the diff is a valid scope
skeleton revision DIFFERS  -> the diff is VOID; both judgement axes read the whole document
no previous render         -> the whole document (the first whole-piece review, always)
```

**One line of `skeleton.md` can make two renders differ everywhere while moving no prose, and a
prose diff represents none of it.** Reading renders already handles most of that hazard: a slot
reorder or a roster addition renumbers things and shows up as a large render diff. The residue is
the amendment that moves almost no characters and still changes which cross-section reasoning holds
— a level-only change, a slot rename. Hence the pair. Ask which skeleton revision the previous
render was built from; if nobody can name it, the diff is void and both axes read the whole
document.

**A supersession is the one case where a diff is the correct instrument rather than an
approximation.** For a fresh draft, reviewing a diff instead of a document is the bug this pairing
exists to contain. For a `revise` ticket replacing prose that already shipped, the diff is not an
approximation of the question, it *is* the question.

**Every axis reads the render, never the annotated source.** Render it fresh:

```
render-paper <source> --circulate [--section <unit>] > <a scratch path>
```

`<source>` is `drafts/<unit>.md` pre-promotion and `MANUSCRIPT.working.md` after it. Never review
`MANUSCRIPT.md`: it is a persisted render that may lag its source, and a review of a stale render is
a review of a document that no longer exists. The render shows reader-facing prose with every
reference token left unresolved, because a section render cannot resolve a number the whole document
owns — **an unresolved reference token is not a finding.** Reviewing the source is how six sections
once passed a per-section checkpoint while carrying 37 annotation markers between them: the reviewer
read the brackets as scaffolding.

### 2. Run the gate and report it verbatim

```
render-paper <source> --check [--section <unit>] [--em-dash-threshold N] [--supersedes <ref>]
```

Report the **exit code** and the **per-check verdict table verbatim**. Do not summarise it, do not
rerank it, do not merge it into the judgement findings, and **do not restate any individual check in
prose.**

`N` is the em-dash threshold from the effective stanza, which you derive yourself in step 5; the
skill default is `0`. Derive that one value before running this, so the table reports the bar the
effort actually set rather than a bar it had visibly raised.

**Pass `--supersedes` when, and only when, this is a review of a supersession** — a `revise` ticket
naming the commit ref its superseded draft closed at. That is the one input which makes the
supersession row report what the revision lost instead of *not a supersession*; the row is a finding
and never a gate, so carry it into the report and leave the disposition to the author. Never pass it
for a fresh draft: there is no old side, and a diff-relative reading of one is the bug this pairing
exists to contain.

Whole-document checks at section granularity print `SKIPPED — OUT OF SCOPE AT THIS GRANULARITY`.
**That is a printed row, not a pass.** Carry every such row into the report; dropping them is what
turns *never looked* back into silence.

**There is no `CLEAN` verdict, here or anywhere in this skill's output, and no single-word verdict at
all.** One word cannot carry the difference between checked-and-fine and never-looked.

**Why this step describes none of the checks.** A check described in a `SKILL.md` is a check an agent
can talk itself out of: the em-dash ban sat in this file as a bullet, unambiguous and in the right
skill, and was violated **98 times through six clean reviews**. Every mechanical check has exactly
one implementation and exactly one description, both in `render-paper`. This step's whole duty is to
run it and print what it said. A restatement here would be a second description to reconcile — and
the one a session would reason with.

The manifest prints under `--check` too. It belongs to step 3, not to this table.

### 3. Identify the fidelity source

Look for what the text is supposed to be faithful *to*, in this order:

1. The unit's brief, an outline, a grant-specific structure (e.g. Specific Aims / Significance /
   Innovation / Approach), or the notes the draft was written from — **and the claim ladder's
   `establishes` for this unit**, which states what the unit owes the argument.
2. The underlying data, results, figures, or source excerpts the paragraph in question is reporting
   on.
3. Prior units of the same piece, which later units must not contradict.
4. The literature itself, for every citation — see step 4.

Then one input that is not a source but an absolute: **the whole manifest, exactly as the render
printed it.** It **enters whole and is never diffed.** It is `f(source)`, recomputed at every render,
so there is no previous manifest to diff against, and a manifest entry is an **absolute** input to a
diff-relative axis. A verify flag is a SILENT annotation carrying the gate bit: it emits nothing into
the render, by design, so the axis that most needs it is otherwise the one axis that cannot see it.
Letting Fidelity read the source instead was rejected — a source-reading reviewer is the one that
read 37 brackets as scaffolding and passed six times.

If nothing at all is available to check a claim against — no brief, no data, no citation — say so in
the report rather than silently skipping it; **an un-groundable claim is itself a finding.**

### 4. Verify literature citations

This is a required action, not a passive smell to note in passing. For every citation in scope — new,
or whose surrounding claim changed — confirm what the source *actually* found, not just that it's
topically related:

- If the source's content is already available in context (uploaded, previously fetched), re-read it
  against the specific claim being made.
- If it isn't, retrieve it (web search / fetch) and check the claim's **direction**, not just its
  subject — a citation can be topically on point while reporting the opposite finding, understating,
  or overstating what the draft attributes to it. This is the single most consequential class of
  error this skill exists to catch: a wrong-direction citation reads as solid support right up until
  someone checks it.
- Flag not just wrong citations but citations that are directionally correct but overstated (e.g. a
  single-study finding presented as settled where the literature is actually split).

**Where this stops.** Verifying a claim's direction against a source is a different question from
whether a DOI string was confirmed, and only the first is yours. **There is no
bibliography-verification gate.** The bibliography is the author's library at a declared path, and an
unverified DOI is input hygiene — a property of that library rather than of the document. It becomes
a `task` ticket blocking the whole-piece ticket. Folding it in here would hide a cheap mechanical
check behind an expensive judgement one.

### 5. Craft sources, the stanza you derive yourself, and the prose smell baseline

The style in force has four tiers, and only two of them are judgement:

| tier | what it is | where it is enforced |
|---|---|---|
| 1 | a mechanical gate over a countable prohibited token — the em-dash threshold | a row in the table; `## Style` may move the number and can never remove the gate |
| 2 | invariants true of any academic prose in any house style | judgement, at drafting and here. **Not overridable** |
| 3 | preference — this person's or this venue's house style | `## Style` and the user-level default file. This is what *documented style* means below |
| 4 | a measured number about the prose | rows in the table, reported with **no threshold** |

**Derive the effective stanza yourself.** Compose it from the same two inputs the drafting session
used — the map's `## Style` deltas over the user-level default file — and **never accept the
drafter's echo of it.** That echo is a session-time report, not an input to this review.
**Disagreement between your derivation and theirs is a finding**, and it is the same shape as the
objection re-derivation in `Rationale Leak` below: a review that reads the drafter's copy is
accepting the drafter's framing of the very thing it was asked to check.

Where the piece is not map-tracked, the documented style is whatever it documents about itself: a
house style guide, journal author guidelines, grant-funder formatting rules, a style note from the
user, or prior chapters establishing the voice and terminology to match.

**Report `## Style` prose that reads as contradicting a Tier 2 invariant.** A clause naming an
invariant as a *key* is an unambiguous collision decidable at load, and the drafting session refuses
before drafting; a prose contradiction needs judgement, so it lands here. When no stanza is found at
all — no map, no `## Style`, no default file — **Tier 2 holds unchanged, Tier 1 keeps its default of
`0`, and Tier 3 is not in force.** Do not invent Tier 3, and do not flag prose for departing from a
preference nobody declared.

#### The Tier 2 invariants

Not overridable by any `## Style`, so they are stated apart from the baseline and are never
suppressed by documented style:

- **No fix may be an unconditional transform over finished prose.** Every rule that removes or
  converts a construction requires reading what that construction was doing first. A rule that can
  be executed by find-and-replace will be, and the result is flatter than the text it replaced. This
  one binds the fixes *you* recommend, not only the draft.
- **Subordination must remain available.** An em dash marks a logical relation without naming it;
  once the relation is named, the right construction is the one that carries *that* relation — a
  relative clause or paired commas for apposition, a colon for elaboration, a subordinating
  conjunction (`although`, `whereas`, `while`) for contrast or concession, a semicolon for a balanced
  pair. So never flag a relative clause or a semicolon as complexity to be split out: those are the
  honest replacements for the token Tier 1 counts, and a split-by-default rule would have the
  drafter install subordination and then take it out again.
- **Convert a passive when the actor is load-bearing and hidden**; leave it when the actor is
  irrelevant or the object is the topic. "Slides were stained" is correct — the actor is a technician
  and nobody needs them named. There is no convert-them-all default: *as a matter of course* is an
  instruction not to ask what this particular passive is doing, and one revision pass under it took a
  section to 22% `We`-initial sentences.
- **Interpretation never precedes the result it interprets**, and **the figure reference attaches to
  the sentence stating what is shown.**
- **A unit may open by *using* what came before** — restating the proposition as a premise it now
  builds on — and may never name a section, the text, or the reader's position in it **in the act of
  closing a debt.** "Registration accurate to 1.2 µm lets us compare the same cell across panels",
  not "As established in Implementation, registration is accurate to 1.2 µm." The ban is narrow, and
  read blanket it kills seven ordinary procedural cross-references a venue expects: those are legal.
  There is also no mandate to reach back at all — which units do is decided by the ladder's debt
  edges, and a per-boundary transition ritual is what makes openings uniform.

#### The prose smell baseline

On top of whatever is documented, the Craft axis always carries the baseline below. Two rules bind
it, and neither reaches Tier 2:

- **The documented style overrides.** Where a style guide or the user's own established usage
  endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Each smell is a labelled heuristic, never a hard violation — flag it,
  don't mandate a fix.

Each smell reads *what it is* → *how to fix*; match it against the render:

- **Overclaim** — a verb or qualifier ("demonstrates," "proves," "the first," "entirely,"
  "essentially") asserts more certainty than the underlying evidence supports. → downgrade to the
  verb the evidence actually earns.
- **Unsupported Causal Claim** — the text implies mechanism or causation where the underlying result
  only shows correlation, sufficiency, or a modeling assumption. → name the actual inferential step.
- **Hedge Mismatch** — the certainty language doesn't match the evidence strength anywhere in the
  piece, in either direction. → recalibrate the verb to the evidence, not just downward.
- **Buried Contradiction** — a claim conflicts with something established earlier in the piece,
  without acknowledgment. → resolve explicitly, or flag as an open tension.
- **Smoothed Transition Gap** — a paragraph break or connective phrase papers over an actual logical
  leap between two ideas that haven't actually been connected. → make the missing inferential link
  explicit.
- **Dangling Modifier / Unclear Antecedent** — a clause, pronoun, or participial phrase doesn't
  clearly attach to what it's meant to modify. → rewrite so the referent is unambiguous.
- **Term Drift** — the same concept is named differently in different places, or the same term is
  reused for two different things. → pick one term per concept and hold it constant.
- **Redundant Restatement** — a clause or sentence repeats a point already made without adding
  precision. → cut, or merge into the earlier statement.
- **Scope Creep** — content appears that wasn't called for by the brief and isn't load-bearing for
  the argument. → cut, or flag for a "future work" pointer.
- **Passive Obfuscation** — passive voice or a nominalization hides who or what is doing the acting,
  **where the actor is load-bearing.** → make the actor explicit. Leave it where the actor is
  irrelevant or the object is the topic.
- **Meta-narration / Signposting** — a sentence describes the text's own structural role ("this is
  described in the next section," "here we establish...") instead of just making the point the
  paragraph exists to make. → cut the narration; let the content carry the motivation directly, with
  no stage direction.
- **Rationale Leak** — the internal argument about how to frame a choice, rendered as a claim to the
  reader. Distinct from Meta-narration because the cure differs: meta-narration is cured by
  deletion, rationale leak by **rewrite** — keep the fact, cut the defence. Name the objection the
  sentence pre-empts and ask who could raise it: a reader of the published paper, from the evidence
  alone, means keep; only someone who saw the planning means leak. **Derive the objection yourself
  from the rendered sentence** — never read the drafter's `obj` comment, which the render strips
  anyway. Disagreement between your naming and theirs is the finding. Also flag a **negated frame**:
  a sentence that invokes a banned frame in order to reject it ("not validation", "not a benchmarked
  win"). The denial plants the word the constraint existed to prevent, and it passes the objection
  test, so this is the clause that catches it.
- **Filler adversative** — `however`, `while`, `whereas` marking no real contrast. → cut it, or
  supply the contrast it promises.
- **Repeated grammatical subject** — the same subject opening consecutive sentences. Judgement:
  three "we" openings in a row can be right.
- **Uniform paragraph shape** — consecutive paragraphs built on the same move sequence. Fires
  per-seam for within-section uniformity and whole-piece for across-section.

**Rationale leak is the one duty with two owners**, deliberately. `write-paper` owns the
construction rule — the objection is named and written down beside the sentence as it is drafted —
and this skill re-derives the objection independently from the rendered sentence. A review that read
the drafter's declared objection would be accepting the drafter's own framing, which is precisely
the failure mode that produced the leak. **Disagreement between the two namings *is* the finding.**

### 6. Spawn both sub-agents in parallel

Send a single message with two `Agent` tool calls. Use the `general-purpose` subagent for both.

**Fidelity sub-agent prompt** — include:

- The render in scope: the diff if step 1 left the diff valid, otherwise the whole render — plus the
  fixed-point pair as you resolved it.
- The brief, the claim ladder, and the data / results / prior units identified in step 3.
- **The whole manifest**, as the render printed it, undiffed.
- The literature-verification results from step 4 (or instruct the sub-agent to run that
  verification itself if it has search access and step 4 wasn't pre-run).
- The brief: "Report — per paragraph or claim where relevant — (a) every claim that outruns its cited
  source or underlying data, with the specific divergence; (b) any citation whose actual finding
  contradicts, understates, or overstates what the draft attributes to it — this is the
  highest-priority finding type; (c) any claim that contradicts something established earlier in the
  piece; (d) for every debt this unit claims to close, does the prose actually close it — not whether
  the metadata says so, which the gate already checked, but whether the argument discharges the
  proposition. Name any debt whose closure is asserted but not performed. Distinguish claims you
  checked and found wrong from claims you simply couldn't verify. Under 400 words."

**Craft sub-agent prompt** — include:

- The render in scope.
- **The composed style stanza with each value's provenance**, as you derived it in step 5, and **the
  Tier 2 invariant list, stated separately** — it is not overridable, so it must not arrive looking
  like part of the baseline.
- Any style-guide files or established-usage examples found in step 5, **plus the prose smell
  baseline pasted in full.**
- The brief: "Report — per sentence or paragraph where relevant — (a) every place the prose violates
  a documented style rule: cite the rule; (b) every place it breaks a Tier 2 invariant, which no
  documented style can override; and (c) any baseline prose smell you spot: name it and quote the
  passage. Distinguish invariant breaks and hard violations of documented style from baseline smells,
  which are always judgement calls. Under 400 words."

Neither axis is asked for a verdict, because neither has one to give.

### 7. Aggregate

Present three sections — `## Gate`, `## Fidelity`, `## Craft` — verbatim or lightly cleaned. Do
**not** merge or rerank findings across sections.

`## Gate` carries the exit code and the verdict table **verbatim**, including every
`SKIPPED — OUT OF SCOPE AT THIS GRANULARITY` row and the closing line saying the table is **not** a
claim that the section or the document is finished. At section granularity, say that in the report's
own words as well as the table's: a section review is a report about one unit at one granularity,
never a statement that the unit is done.

**The Tier 4 diagnostics — the adversative ratio, the subject-opening distribution, and the
sentence-length mean, coefficient of variation and share over 35 words — are reported together, with
no thresholds.** They are numbers, not verdicts. Do not lift one out of the table and attach a bar
to it, and do not ask either axis to weigh one.

> **Read the adversative ratio as a consequence, never as a target.** It moves *because* the em-dash
> gate forces relation-first rewriting: in the worked example it went **0 → 4 with none targeted.**
> Tuning it directly is forbidden, and the ratio's real test is the chain walk — **a low ratio beside
> a ladder full of closed debts is the finding; a low ratio alone is not**, and a genuinely
> procedural Methods section concedes nothing, correctly.

End with a one-line summary: total findings per section, and the single most consequential issue
overall. A wrong-direction citation or a debt asserted-but-not-closed should generally outrank a
style smell — a prose issue is usually fixable in seconds, a mischaracterized citation can invalidate
an argument. **The summary names an issue; it never names a state**, and no single word stands in for
the table.

### 8. Findings that must not be ignored

This skill reports; it never gates. A finding becomes blocking by being written back into the
**source** (not the render) as a SILENT annotation carrying the gate bit:

```markdown
<!-- !@author unverified: the six paired fractions are not in any committed table -->
```

You may create **SILENT annotations only.** Because SILENT emits nothing, a review is structurally
incapable of changing what the reader sees — which is what makes it safe to write into the artifact
you are judging. Findings then become durable, inherit the manifest, and outlive the session that
found them. `!` is the gate bit and blocks `--submit`; a note that should be visible to a co-author
without blocking submission is the same comment without it. Deletion is the only closure — there is
no `RESOLVED` marker and no tombstone, and git is the audit trail.

**You read the render; you write the source. There is no contradiction.**

Every finding leaves this review in one of three states: **fixed, written back as a `!` annotation,
or explicitly dispositioned with a reason. Silence is not a disposition** — and that is why this step
exists at all. Reports evaporate: this skill once returned a clean verdict over a document holding
26 live annotations, and the report is gone while the annotations are still there.

A written-back gap does not hold the drafting ticket open. It is re-homed as its own `task` ticket
blocking the whole-piece ticket, which gives it an owner and tracker visibility without freezing the
frontier — the refusal has already moved to `--submit`.

**What this skill may not write:** anything else. It never writes `MANUSCRIPT.md`, never edits prose,
and never makes a cut. Cross-section de-duplication — the same fact stated in full in three units —
*is* a cut, and a SILENT-only skill cannot make one, which is what keeps that pass in
`assemble-paper` rather than here.

## Why separate axes

A piece of writing can pass one axis and fail another:

- Clean, well-organized prose that overclaims what the data show or cites a source that says the
  opposite → **Craft finds nothing, Fidelity finds the defect.**
- An airtight, fully-supported argument delivered in redundant or ambiguously-modified sentences →
  **Fidelity finds nothing, Craft finds the defect.**
- Everything above is fine, but an annotation carrying the gate bit is still open, or a debt was
  opened and never closed → **neither axis has anything to say, and the gate fails.**

Reporting them separately stops one from masking the others. It is also why the gate is reported
before either axis and never merged into them: of the three, it is the only one that can refuse.

## What the gate took over

The cross-reference integrity check that used to be step 2 is gone, and not because it stopped
mattering. Most of what it looked for is now **impossible by construction**: headings are injected
at every render rather than written, so a heading tree cannot drift; citations and figures resolve to
first-mention order and panels to legend declaration order, so numbering cannot be out of sequence;
and the reference list is built from the keys actually cited, so an orphaned bibliography entry has
nowhere to come from. Leftover editing artifacts are parse errors — the render refuses rather than
emitting them. What genuinely survived is a row in the verdict table.

So there is nothing left here to check by hand, and no bullet list describing it. That list was the
last place in this skill where a mechanical check carried a second description, and a second
description is what a session reasons with when it wants to reason its way past the first.
