---
name: write-paper
description: "Draft a piece of academic writing — paper section, chapter, grant, or assay/protocol report — based on a spec, outline, or set of results/notes, with reference management and consistent cross-referencing."
disable-model-invocation: true
---

Draft the piece of writing described by the user, from the spec, outline, notes, or results provided.

Use /review-paper once the draft is complete, and at any natural checkpoint along the way where a self-contained chunk is finished.

## Process

### 1. Pin the spec

Whatever the user points to is the spec — an outline, a notes file, a set of results/figures/data the piece needs to report on, prior sections to match in voice and terminology, or a stated argument structure. For grants, this includes the funder's required section structure (e.g., Specific Aims/Significance/Innovation/Approach) and any page or word limits. If none of this exists yet, ask what the piece needs to establish and in what order, before drafting.

Also identify, if they exist:
- **The evidence base** — the actual data, figures, statistics, or source material each section will need to represent faithfully. A claim with no evidence base behind it is a claim to flag, not to invent support for.
- **The voice** — if this draft is a wayfinder ticket, check the map's `## Style` section first; it overrides inferring voice from context alone. Otherwise, prior chapters, sections, or the person's own past writing to match in tone, sentence rhythm, and terminology. See `## Default voice` below for this person's established baseline when nothing more specific is pinned.
- **The reference library** — an existing bibliography file (BibTeX, RIS, Zotero export, or plain reference list) and the citation style/format the target venue requires (author-year, numbered, journal-specific).

### 2. Draft at pre-agreed seams

For anything beyond a short passage, draft section by section, or paragraph-cluster by paragraph-cluster — not the whole piece in one pass. Agree the seams with the person up front if they haven't already been implied by the spec's own structure. Stop at each seam to confirm direction before continuing, unless the person has said to keep going.

### 3. Handle citations as you draft — never fabricate one

When a claim needs a citation:

- If a reference library was identified in step 1, pull the matching entry from it and insert the citation in the required format and key.
- If the claim needs a citation that isn't yet in the person's library, search for a real candidate, and verify — by actually reading the source, not just its title or a search snippet — that it supports the claim **in the direction stated**. A topically-relevant but directionally-wrong citation is worse than no citation.
- If no suitable source can be found or verified, don't insert a plausible-sounding placeholder. Mark it clearly (e.g., `[citation needed: <what the claim requires>]`) and flag it to the person rather than leaving an unmarked, ungrounded claim in the draft.
- When citing a source already discussed earlier in the piece, reuse the same key/format — don't introduce a second citation for the same work.
- When a claim rests on a specific technical detail (a tool's exact algorithm, what it does or doesn't model, a benchmark result), verify the claim against the actual source rather than a remembered impression of it — this person has repeatedly asked for this kind of check before finalizing text, and it has caught real errors (e.g., confirming ASHLAR's registration is rigid/translational-only, confirming what InstanSeg and CellSAM each natively support).

### 4. Keep cross-references consistent as you draft

When introducing a new figure, table, equation, or supplementary item, number it consistently with what already exists in the piece (no gaps, no reused numbers, panel letters assigned in the order they're introduced). When writing a forward or backward pointer ("see Methods," "as shown below," "described above"), make sure it will actually resolve to real content once the piece is assembled — don't leave a pointer to a section that hasn't been drafted yet without flagging it as a placeholder.

### 5. Check at every seam, before moving on

- Every specific claim, number, or citation traces to something actually provided or verified — not filled in from a plausible-sounding assumption.
- No new claim contradicts something already established earlier in the piece; if the new section needs to complicate or qualify an earlier claim, do that explicitly.
- Terminology matches what's used elsewhere in the piece — the same concept gets the same name throughout.
- The certainty language (demonstrates / suggests / is consistent with / indicates / may) matches the actual strength of what's being cited or reported — not the strength that would make the argument land more cleanly.
- Where a paragraph transitions into a new idea, the connective logic is stated, not just implied by proximity.
- No sentence describes the text's own structural role ("this is covered in the next section," "here we establish...") — let the content carry its point directly; a brief's instruction to defer detail elsewhere is satisfied by not including that detail, not by narrating the deferral.
- No em dashes, by default — use a comma, colon, or a sentence break instead, unless the map's `## Style` section or the person's own established usage says otherwise.
- No sentence grades its own importance ("this is the headline contribution," "the load-bearing result," "critically" used as a badge rather than a genuine logical connective). State what something is or does; let the reader judge its weight. This applies throughout a piece, not just once — don't relocate the emphasis to a different sentence, cut it.
- A caveat, scope limit, or piece of framing (e.g., "this is concordance among proxies, not validation against a ground truth") is stated once, at the point it's first needed, and referenced briefly thereafter rather than restated in full each time it's relevant again.

### 6. Review

Once the full draft — or a natural checkpoint within it — is done, run /review-paper comparing the new text against the spec and, if this is a revision, against the previous version. Address anything it surfaces before treating the section as finished.

### 7. Save

Save the finished piece to the appropriate output location, in the format the person needs (Markdown, Word doc, etc.) — check for a relevant skill (docx, pdf) if the deliverable needs a specific document format rather than plain text. Include or update the reference list/bibliography file alongside it if one is being maintained.

## Default voice

When no other voice signal is pinned (no map `## Style` section, no prior section to match), draft in this person's established default rather than a generic academic register:

- **Active, "we" throughout.** "We correct uneven illumination," not "illumination is corrected." Convert passive constructions and nominalizations as a matter of course, not just when flagged.
- **State the goal, then what was done, then the result with its figure reference, then the interpretation** — in that order, for any results-reporting paragraph. When a second, related analysis follows the same goal, introduce it with "In addition, we also..." or "We next asked whether..." rather than re-deriving the motivation from scratch.
- **Attach the figure reference to the sentence describing what is shown**, not to the end of a paragraph of interpretation that follows it.
- **Build an argument or comparison up in steps** rather than stating the conclusion flatly first — e.g., establish that a simpler baseline already helps before naming the best-performing configuration, rather than naming the winner in the same breath as the setup.
- **Plain, concrete words over technical-sounding or Latinate ones** where a simpler word says the same thing: "works well for" not "suits"; "feeds" or "is read by" not "is consumed by"; "cannot explain/account for" not "cannot manufacture." When in doubt, prefer the word a colleague would use out loud.
- **Short, declarative sentences over long chained ones.** Where a sentence stacks two or three distinct claims across commas, semicolons, or relative clauses, default to splitting it, one claim per sentence, unless the claims are tightly enough coupled that splitting would orphan one half.
- **A transition sentence at the start of a new section**, linking back to what the previous section just established, rather than opening cold on a new topic.
- **UK spelling** (optimised, containerise, licence as noun, catalogue) if the piece has used it so far; hold whichever variant (UK/US) is already established, consistently.
