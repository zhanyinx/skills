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
- **The voice** — prior chapters, sections, or the person's own past writing to match in tone, sentence rhythm, and terminology.
- **The reference library** — an existing bibliography file (BibTeX, RIS, Zotero export, or plain reference list) and the citation style/format the target venue requires (author-year, numbered, journal-specific).

### 2. Draft at pre-agreed seams

For anything beyond a short passage, draft section by section, or paragraph-cluster by paragraph-cluster — not the whole piece in one pass. Agree the seams with the person up front if they haven't already been implied by the spec's own structure. Stop at each seam to confirm direction before continuing, unless the person has said to keep going.

### 3. Handle citations as you draft — never fabricate one

When a claim needs a citation:

- If a reference library was identified in step 1, pull the matching entry from it and insert the citation in the required format and key.
- If the claim needs a citation that isn't yet in the person's library, search for a real candidate, and verify — by actually reading the source, not just its title or a search snippet — that it supports the claim **in the direction stated**. A topically-relevant but directionally-wrong citation is worse than no citation.
- If no suitable source can be found or verified, don't insert a plausible-sounding placeholder. Mark it clearly (e.g., `[citation needed: <what the claim requires>]`) and flag it to the person rather than leaving an unmarked, ungrounded claim in the draft.
- When citing a source already discussed earlier in the piece, reuse the same key/format — don't introduce a second citation for the same work.

### 4. Keep cross-references consistent as you draft

When introducing a new figure, table, equation, or supplementary item, number it consistently with what already exists in the piece (no gaps, no reused numbers, panel letters assigned in the order they're introduced). When writing a forward or backward pointer ("see Methods," "as shown below," "described above"), make sure it will actually resolve to real content once the piece is assembled — don't leave a pointer to a section that hasn't been drafted yet without flagging it as a placeholder.

### 5. Check at every seam, before moving on

- Every specific claim, number, or citation traces to something actually provided or verified — not filled in from a plausible-sounding assumption.
- No new claim contradicts something already established earlier in the piece; if the new section needs to complicate or qualify an earlier claim, do that explicitly.
- Terminology matches what's used elsewhere in the piece — the same concept gets the same name throughout.
- The certainty language (demonstrates / suggests / is consistent with / indicates / may) matches the actual strength of what's being cited or reported — not the strength that would make the argument land more cleanly.
- Where a paragraph transitions into a new idea, the connective logic is stated, not just implied by proximity.

### 6. Review

Once the full draft — or a natural checkpoint within it — is done, run /review-paper comparing the new text against the spec and, if this is a revision, against the previous version. Address anything it surfaces before treating the section as finished.

### 7. Save

Save the finished piece to the appropriate output location, in the format the person needs (Markdown, Word doc, etc.) — check for a relevant skill (docx, pdf) if the deliverable needs a specific document format rather than plain text. Include or update the reference list/bibliography file alongside it if one is being maintained.
