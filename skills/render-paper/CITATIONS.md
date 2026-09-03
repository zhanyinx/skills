# The citation surface

`render-paper` is this surface's only parser, which is why it documents it — the same reason it
documents [`skeleton.md`](SKELETON-FORMAT.md), [`spine.md`](SPINE-FORMAT.md) and
[the annotation channel](ANNOTATION-CHANNEL.md).

**A drafting session references a source by stable key and never by number.** A number it writes
could be wrong-but-valid — pointing at a real entry that is not the one meant — and no gate can
catch that. Keys remove the surface it needs. The render turns keys into numbers, and builds the
reference list from the keys that were cited.

## The grammar

```
@smith2020                      narrative position
[@smith2020]                    parenthetical
[@hickey2022; @elhanani2023]    grouped parenthetical
```

**Inside brackets: keys and `;` separators only.** No prefixes, no suffixes, no locators, no free
text of any kind. A key is a letter, digit or `_` followed by any of `A-Z a-z 0-9 _ : . # $ % & + ?
< > ~ / -`, and it may not end on punctuation — so `@smith2020.` ends a sentence rather than
swallowing the full stop.

This is a **strict subset of pandoc**, so citeproc parses everything the source expresses and
nothing here diverges from it; we refuse pandoc's permissive parts rather than invent our own.
Name → number resolution happens **inside `render-paper`**, because `--check` must run with no
external tool present.

A `@fig:name` identifier shares the `@` namespace and is **not** a citation: the bibliography is
never asked about it, and [figures and panels](SKILL.md) own resolving it. The bracket grammar
accepts it, and the render leaves any token carrying one verbatim.

## Every other bracket span is a parse error

Outside comments and fences, a `[…]` span in prose **must** be a citation group. Anything else is a
parse error: exit `3`, nothing ran, no table.

The permissive form — *a `[…]` span is legal iff it contains an `@key`* — was rejected for a
specific reason. Pandoc's bracket prefix is free text, so that rule admits `[verify this
@smith2020]`, which renders as *"(verify this Smith 2020)"*. **That is a free-text channel into
reader-facing prose, which is the failure class this clause exists to close, re-opened inside the
clause closing it.**

It is a **refusal, not a finding**, for the reason every refusal here is one: a finding is what
returned CLEAN over 98 em dashes, and a prose-stated invariant with no mechanism is worth nothing.
And it **cannot be configured per effort** — a configurable refusal pattern is the override these
rules exist to prevent, wearing a config file.

### Why it is affordable — the calibration

Measured over the calibration corpus, outside comments: **70 bracket spans, 40 citations, 30
author-facing annotations, and zero other legitimate uses.** No markdown link, no reference link, no
footnote, no task box in 74 KB of biomedical prose; the one `[24][25]` that looks like a reference
link is two adjacent numeric citations. Three further spans sat inside comments, exempt by
construction.

So the refusal has **no false positives on real text**, and its whole cost is stated rather than
discovered: a markdown link cannot be written in reader-facing prose. A paper's cross-references are
`@key` and `@fig:name`, and its URLs live in the bibliography.

The 30 annotations were written in **nine improvised syntaxes**, none of which anything refused, and
six review passes read past every one. They belong in
[the annotation channel](ANNOTATION-CHANNEL.md) — a brace, not a bracket. In particular
`[citation needed: <what the claim requires>]` is **deleted** as a form: an unfound citation is a
hole with the gate bit set, so it is written `{{ ! <what the claim requires> }}`.

### It is not a gate

`--circulate` always succeeds over a *live* paper, and a parse error does not contradict that. `C3`
governs **open annotations**, and an open annotation never blocks circulation — it renders as a
token and lands in the manifest. A parse error governs **malformed source**. A stray
`[author to supply: …]` is not an open annotation the render declines to gate on; it is text the
render cannot parse, so it has no behaviour and no gate bit to honour. It is in the same category as
an unclosed `{{`.

## The bibliography

**An author-owned declared input at a declared path: `references.bib` at the paper root**, beside
`skeleton.md` and `spine.md`. BibTeX, because it is what a reference manager already exports; a
library kept in another format is converted to it by the author.

**The render reads it and never contains it.** A bibliography compiled into the generator is the
defect this replaces: it makes a key dangle against the *script* rather than against the author's
library, so the dangling references such a renderer reports are its own artefact and resolve cleanly
against the real thing.

Only what resolving a citation needs is read: the entry key, and the `author`, `title`, `journal` /
`booktitle` / `publisher` / `school` / `institution`, `volume`, `pages`, `year`, `doi` and `url`
fields. `@string`, `@preamble` and `@comment` carry no key and are stepped over. A `%` opening a line
is a BibTeX comment. A malformed file is a parse error, like a malformed `skeleton.md`.

**Absence is a legal state.** The library is required by the *citations*, not by the renderer: a
paper citing nothing has nothing to resolve. A paper that does cite and has no library gets the same
dangling-reference hard error it would get for one missing key.

### The integrity check is asymmetric, and the asymmetry is the point

| direction | disposition |
|---|---|
| key in prose with no bibliography entry | **hard error, both modes** |
| entry in the rendered list that nothing cites | **impossible by construction** |
| entry in the bibliography this document does not cite | **no check at all** |

> **A figure roster is a manifest of this document's objects; a bibliography is a library, and
> over-provisioning is its normal state.**

A key with no entry is a **dangling reference** — a token pointing at nothing, structurally
identical to a figure name absent from the roster, so it takes that tier. Freezing the hard-error
tier without it would let a dangling citation circulate while hard-erroring the same defect for
figures.

Transposing the roster's *symmetry*, though, would hard-error the calibration corpus forever over
**eight entries its author deliberately kept and deliberately did not cite**, six of them marked
*"do NOT cite"* — making the gate noisy, and therefore skippable, which is the failure this whole
design is built against.

## Numbering and the reference list

**Citations number by first mention in the assembled document** — after concatenation and heading
injection, in skeleton order, never in the order the source files were read.

The evidence is not a defect count; it is what an author did about the cost. One real
`assemble.py` deferred renumbering in its own note because a pending citation *"would be the first
citation and shift every number"* — and when that citation landed it was numbered **24/25, appended
last, despite being the document's first citation.** A wrong-but-valid literal, minted deliberately,
that no gate could catch. (Renumbering that manuscript to first-mention order changes **15 of 17**
numbers, which is why it was never done.)

Both forms resolve to the same numeric token, because in a numbered style narrative and
parenthetical position do not differ: `@muhlberg2020` and `[@muhlberg2020]` both render `[4]`, and a
group renders `[2,3]`. The author writes the surrounding name — *"as Muhlberg and colleagues [4]
describe"* — because the name is prose and the number is not.

A key inside a gap token's label is **not** a citation of this document: the label is author-facing
text the render has already substituted into the prose, and the scan steps over it.

**The reference list is `f(cited keys)`.** Nothing else can reach it, so an orphaned entry is
impossible by construction rather than something a check looks for. It is appended under a
`References` heading at unit level, numbered in citation order, and it is **absent entirely** when
nothing is cited.

Its formatting is deliberately **style-neutral** — author, title, container, volume, pages, year,
DOI. The venue's citation style is a typesetting concern downstream; encoding one here would put
paper-specific text in the generator, which is the thing this unit must never hold.

## `--section` resolves nothing

At section granularity every citation token is emitted **verbatim and visible** — `[@hickey2022]`
stays `[@hickey2022]` — and there is no reference list. First-mention order is a fact about the
whole document, and a section cannot know it.

**No placeholder form is invented.** A placeholder would be a second surface to learn, to get stale,
and to be mistaken for the real one. The `citation → bib entry` row prints
`SKIPPED — OUT OF SCOPE AT THIS GRANULARITY`, never silently as a pass.

The bracket refusal, by contrast, fires at **both** granularities: a parse error is not a gate, so
granularity does not scope it. The source cannot express the thing at all.
