---
name: review-paper
description: Review a piece of academic writing — paper, grant, or assay/protocol report — since a fixed point (a previous draft, or the outline/spec alone if there is no previous draft) along two axes — Fidelity (does the text accurately represent the evidence, sources, and literature behind it?) and Craft (is the prose itself well-built — clear, non-redundant, correctly hedged?) — plus a direct cross-reference integrity check. Runs the two axes as parallel sub-agents and reports all three side by side. Use when the user wants to review a draft, a revision, a manuscript section, a grant, or asks to "review since X" or "check this draft."
---

Three-part review of the text between a fixed point and the current draft:

- **Cross-references** — do internal figure/table/equation/section references resolve, stay consistent, and match numbering elsewhere in the piece? Checked directly, not as a sub-agent — it's mechanical, not a judgement call.
- **Fidelity** — does the text accurately represent the evidence, data, and literature it cites, and does it match what the outline/spec/results actually establish?
- **Craft** — is the prose itself well-constructed: clear, non-redundant, consistently termed, correctly hedged?

Fidelity and Craft run as **parallel sub-agents** so they don't pollute each other's context; the cross-reference pass runs first and directly, since it's pattern-matching rather than judgement.

## Process

### 1. Pin the fixed point

Whatever the user says is the fixed point — a previous draft file, a specific section range, a commit (if the manuscript is in git), or "the outline" if there is no earlier draft to diff against. If they didn't specify one, ask.

If two versions exist, produce a diff (via `diff`/`git diff` for plain text/LaTeX/Markdown, or a side-by-side read if the fixed point is a Word doc without tracked changes). If there's no earlier version, the "diff" is the full draft read against the spec — say so, and proceed.

### 2. Cross-reference integrity check (direct, no sub-agent)

Scan the diff (or full draft) for every internal reference — figures, panels, tables, extended-data items, equations, supplementary sections, "see above/below" pointers — and check:

- Every reference resolves to something that actually exists elsewhere in the piece or in the supplied materials (no reference to Fig. 5 if there is no Fig. 5; no panel `c` cited if the figure only has `a`–`b`).
- Numbering is consistent and sequential where the piece implies it should be (no gaps, no duplicate panel labels, no figure referenced out of the order it's introduced without reason).
- No leftover editing artifacts: stray comment markers (e.g., `[YZ1.1]`), doubled or malformed labels (e.g., `6jk` where `6j,k` was meant, `6k-ll`), or citation placeholders that were never filled in.
- Citation-key consistency: the same source is cited under the same key/format throughout, and every in-text citation has a corresponding entry in the reference list (and vice versa — no orphaned bibliography entries, no citations missing from it).

Report this as its own short section — it needs no sub-agent and no judgement call, so resolve it before spawning the two axes below.

### 3. Identify the fidelity source

Look for what the text is supposed to be faithful *to*, in this order:

1. An outline, grant-specific structure (e.g., Specific Aims/Significance/Innovation/Approach), or set of notes the draft was written from.
2. The underlying data, results, figures, or source excerpts the paragraph in question is reporting on.
3. Prior sections of the same piece, which later sections must not contradict.
4. The literature itself, for every citation — see step 4.

If nothing at all is available to check a claim against — no outline, no data, no citation — say so in the report rather than silently skipping it; an un-groundable claim is itself a finding.

### 4. Verify literature citations

This is a required action, not a passive smell to note in passing. For every citation in the diff — new, or whose surrounding claim changed — confirm what the source *actually* found, not just that it's topically related:

- If the source's content is already available in context (uploaded, previously fetched), re-read it against the specific claim being made.
- If it isn't, retrieve it (web search / fetch) and check the claim's **direction**, not just its subject — a citation can be topically on point while reporting the opposite finding, understating, or overstating what the draft attributes to it. This is the single most consequential class of error this skill exists to catch: a wrong-direction citation reads as solid support right up until someone checks it.
- Flag not just wrong citations but citations that are directionally correct but overstated (e.g., a single-study finding presented as settled where the literature is actually split).

### 5. Identify the craft sources

Anything the piece documents about its own style: a house style guide, journal author guidelines, grant-funder formatting rules, a style note from the user, or prior chapters/sections establishing the voice and terminology to match.

On top of whatever is documented, the Craft axis always carries the **prose smell baseline** below. Two rules bind it:

- **The documented style overrides.** Where a style guide or the user's own established usage endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Each smell is a labelled heuristic, never a hard violation — flag it, don't mandate a fix.

Each smell reads *what it is* → *how to fix*; match it against the draft:

- **Overclaim** — a verb or qualifier ("demonstrates," "proves," "the first," "entirely," "essentially") asserts more certainty than the underlying evidence supports. → downgrade to the verb the evidence actually earns.
- **Unsupported Causal Claim** — the text implies mechanism or causation where the underlying result only shows correlation, sufficiency, or a modeling assumption. → name the actual inferential step.
- **Hedge Mismatch** — the certainty language doesn't match the evidence strength anywhere in the piece, in either direction. → recalibrate the verb to the evidence, not just downward.
- **Buried Contradiction** — a claim conflicts with something established earlier in the piece, without acknowledgment. → resolve explicitly, or flag as an open tension.
- **Smoothed Transition Gap** — a paragraph break or connective phrase papers over an actual logical leap between two ideas that haven't actually been connected. → make the missing inferential link explicit.
- **Dangling Modifier / Unclear Antecedent** — a clause, pronoun, or participial phrase doesn't clearly attach to what it's meant to modify. → rewrite so the referent is unambiguous.
- **Term Drift** — the same concept is named differently in different places, or the same term is reused for two different things. → pick one term per concept and hold it constant.
- **Redundant Restatement** — a clause or sentence repeats a point already made without adding precision. → cut, or merge into the earlier statement.
- **Scope Creep** — content appears that wasn't called for by the outline/spec and isn't load-bearing for the argument. → cut, or flag for a "future work" pointer.
- **Passive Obfuscation** — passive voice or a nominalization hides who or what is doing the acting, where the actor matters for clarity. → make the actor explicit.

### 6. Spawn both sub-agents in parallel

Send a single message with two `Agent` tool calls. Use the `general-purpose` subagent for both.

**Fidelity sub-agent prompt** — include:

- The diff (or full draft, if no prior version) and the fixed-point description.
- The outline/spec/results/prior-sections identified in step 3.
- The literature-verification results from step 4 (or instruct the sub-agent to run that verification itself if it has search access and step 4 wasn't pre-run).
- The brief: "Report — per paragraph or claim where relevant — (a) every claim that outruns its cited source or underlying data, with the specific divergence; (b) any citation whose actual finding contradicts, understates, or overstates what the draft attributes to it — this is the highest-priority finding type; (c) any claim that contradicts something established earlier in the piece. Distinguish claims you checked and found wrong from claims you simply couldn't verify. Under 400 words."

**Craft sub-agent prompt** — include:

- The diff (or full draft).
- Any style-guide files or established-usage examples found in step 5, **plus the prose smell baseline** pasted in full.
- The brief: "Report — per sentence or paragraph where relevant — (a) every place the diff violates a documented style rule: cite the rule; and (b) any baseline prose smell you spot: name it and quote the passage. Distinguish hard violations of documented style from baseline smells, which are always judgement calls. Under 400 words."

### 7. Aggregate

Present three sections — `## Cross-references`, `## Fidelity`, `## Craft` — verbatim or lightly cleaned. Do **not** merge or rerank findings across sections.

End with a one-line summary: total findings per section, and the single most consequential issue overall (a wrong-direction citation or an internally contradicted claim should generally outrank a style smell — cross-references and prose issues are usually fixable in seconds, a mischaracterized citation can invalidate an argument).

## Why separate axes

A piece of writing can pass one axis and fail another:

- Clean, well-organized prose that overclaims what the data show or cites a source that says the opposite → **Craft pass, Fidelity fail.**
- An airtight, fully-supported argument delivered in redundant or ambiguously-modified sentences → **Fidelity pass, Craft fail.**
- Everything above is fine, but Fig. 4c doesn't exist and three citations share a key → **Fidelity and Craft both pass, cross-references fail.**

Reporting them separately stops one from masking the others.
