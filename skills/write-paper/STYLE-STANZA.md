# The style stanza — schema

**This file is a schema, not a stanza. Nothing in it is in force.** It names the keys, their value
domains and their tier, and it ships a **values-blank** exemplar you fill in yourself. It carries no
filled value anywhere, and the one worked example below is labelled as an example and is not a
default.

That is deliberate and it is a distribution argument, not a matter of taste. `write-paper` installs
publicly, so a filled stanza shipped here would install one person's UK spelling, active "we" and
em-dash ban on every installer who never opens the file — a house style with the authorship filed
off. The tiers exist so that the preferences which *are* one person's stay one person's:

| tier | what it is | may `## Style` change it? |
|---|---|---|
| **1. Mechanical gate** | a countable prohibited token | **threshold only** — never the gate itself |
| **2. Craft invariant** | true of any academic prose in any house style | **no** — see `write-paper`'s `## Craft invariants` |
| **3. Preference** | this person's or this venue's house style | **yes — this is what the stanza is for** |
| **4. Diagnostic** | a measured number about the prose | n/a — reported, never a gate |

## Discovery — an ordered list, first hit wins

The **filled** stanza lives outside every skill, as a user-level file:

1. `~/.agents/style/academic-writing.md`
2. `~/.claude/style/academic-writing.md`

`~/.agents/` is first because it is the vendor-neutral root; the host-specific path is the fallback,
so an installer who only has `~/.claude/` is not silently in the absent case. First hit wins — the
second path is not merged into the first.

**Absent is a legal state, not an error.** See [Absent](#absent--invariants-hold-preferences-do-not-the-gate-still-runs).

## The key set is closed

| key | kind | domain | tier |
|---|---|---|---|
| `active-we` | scalar | `yes` / `no` | 3 |
| `plain-words` | scalar | `yes` / `no` | 3 |
| `build-in-steps` | scalar | `yes` / `no` | 3 |
| `spelling-variant` | scalar | `UK` / `US` / `established` | 3 |
| `em-dash-threshold` | integer | a finite non-negative integer | 1 (threshold only) |
| `terms` | list | terms, never sentences | — |

**`## Style` cannot add a key.** An effort wanting a preference outside this set writes **prose**,
which is advisory to the drafter and **not machine-read**. That is what keeps the set closed, and a
closed set is what makes the invariant collision below decidable at load rather than a judgement
call.

**A key is absent or it has a value; there is no third state.** For a Tier 3 scalar, absent means
*not stated* and the preference is not in force. It does not mean `no`, which states the preference
and declines it. The distinction is visible in the echo, and it is the difference between a
preference nobody has decided and one somebody has.

**`em-dash-threshold` is a number, and `off` is not a value.** No `off`, no `none`, no `∞`. An effort
may raise the bar as far as it likes — and that choice is then visible in the echo — but it cannot
remove the gate. The gate always runs and always reports its count. With no stanza at all the
threshold is the skill default, `0`.

**Three readers, two contributors.** `write-paper` reads every key; `review-paper` reads the Tier 3
preferences and `em-dash-threshold`; `assemble-paper` reads **`terms` only**, for term drift.
`wayfinder` owns the `## Style` section but names no key, being domain-agnostic.

## Composition — an effort states deltas, and inherits the rest

An effort's `## Style` is composed **over** the user-level file, key by key:

| `## Style` content | composition |
|---|---|
| a **scalar** key | **overrides** the default's value for that key |
| a **list** key | **unions** with the default's list |
| **free prose** (framing rules, venue notes) | **additive** — never overrides a key, never removes one |

**Wholesale replacement is refused.** An effort that wants to flip one thing would have to restate
every preference it still wants, and any it forgot would revert silently. These skills exist because
defects were invisible; wholesale would install a new invisible defect in the machinery built to kill
invisible defects.

**List-key removal is unsupported.** An effort cannot un-inherit a term. An inherited term the effort
never uses costs nothing, and `terms` covers terms and never sentences, which is what bounds the
harm.

## The values-blank exemplar

Copy this to the discovery path and fill in the values you want. **It ships blank, and blank is a
legal state to leave it in** — an unfilled key is a preference you have not stated, not one set to a
default somebody else chose.

```markdown
# Academic writing style

## Preferences

- active-we:
- plain-words:
- build-in-steps:
- spelling-variant:
- em-dash-threshold:
- terms:

## Notes

<!-- Free prose: framing rules, venue notes, anything outside the key set.
     Advisory to the drafter and never machine-read. -->
```

An effort's `## Style` section in its map takes the same shape, minus the file heading, and lists
**only the keys it changes**.

## Worked example — an example, never a default

> **Read this as a scenario, not as values to adopt.** It exists to show how a delta composes and how
> the echo reports provenance. None of these numbers or choices is a default, a recommendation, or in
> force anywhere.

A hypothetical user-level file:

```markdown
## Preferences

- active-we: yes
- spelling-variant: UK
- em-dash-threshold: 0
- terms: registration accuracy, immune content
```

A hypothetical effort's `## Style`, which changes two things and inherits the rest:

```markdown
## Style

- spelling-variant: US
- terms: karyotype

Target venue caps the abstract at 150 words and forbids subheadings in Results.
```

The composed stanza the session prints at the start of the seam:

```
Style stanza — composed from ~/.agents/style/academic-writing.md and the map's ## Style
  active-we           yes                                          default file
  plain-words         (not stated)                                 —
  build-in-steps      (not stated)                                 —
  spelling-variant    US                                           ## Style  (overrides UK)
  em-dash-threshold   0                                            default file
  terms               registration accuracy, immune content,       default file + ## Style
                      karyotype
  prose               venue: 150-word abstract, no Results subheadings   ## Style (advisory)
```

`spelling-variant` overrode; `terms` unioned rather than replaced, so the effort did not lose the two
inherited terms by naming a third; the prose is carried as advisory and changed no key; and the two
keys nobody stated are reported as **not stated** rather than filled in with something plausible.

## The echo — printed every seam, written nowhere

At the start of each drafting seam the session **prints the composed stanza**, every key with its
value and **where that value came from** — default file, `## Style`, or skill default. This is the
whole answer to the one real objection to composing by key: what voice is actually in force is
computed **once** and then read, rather than derived by eye from three files.

The echo is a **session-time report and is never written into the source.** Writing it in would
create a second artifact recording one fact, and it would go stale the moment `## Style` changed.

`review-paper` **re-derives** the stanza from the same two inputs rather than being handed the
drafter's copy, and **disagreement between the two derivations is a finding.**

## Absent — invariants hold, preferences do not, the gate still runs

Three cases, one behaviour, because they are the same state: no map at all; a map with no `## Style`;
the user-level file also absent.

- **Tier 2 invariants hold unchanged.** They were never in the stanza.
- **Tier 3 preferences are not in force.** The skill does **not** invent them.
- **Tier 1 keeps the skill default threshold of `0`**, so a standalone invocation is not the one path
  with no gate — and the standalone drafting session is exactly where 98 em dashes once survived six
  clean reviews.
- **The session says so in one line**, and offers to create the file from the exemplar above. Saying
  nothing is what would make a cold-start unit silently generic.

Under `wayfinder`'s own template `## Style` is omitted when an effort has **no drafting tickets**, so
its absence there means *"not a drafting effort"* and never *"no preferences"*.

## Naming an invariant as a key — refuse before drafting

| what `## Style` contains | response |
|---|---|
| a clause naming a **Tier 2 invariant** as a key | **refuse before drafting** — stop and ask |
| **prose** that reads as contradicting an invariant | a **`review-paper` finding** |

The asymmetry is detectability, and it must be stated as such rather than read as inconsistency. The
key set is closed, so a clause aimed at an invariant is an **unambiguous collision decidable at
load**; a prose contradiction needs judgement and cannot be.

The refusal fires **at session start, before any prose exists**, because the failure it prevents is
drafting a whole unit under a style the author believes is in force and is not — and it is an error
in the **map**, not in the prose, so it surfaces where it was authored.

*Warn and ignore the clause* is not the behaviour: a warning at session start scrolls past, and the
author then reads a finished unit believing a preference applied that never did.
