---
name: wayfinder
description: Plan a huge chunk of work — more than one agent session can hold — as a shared map of investigation tickets on your issue tracker, and resolve them one at a time until the way to the destination is clear.
disable-model-invocation: true
---

A loose idea has arrived — too big for one agent session, and wrapped in fog: the way from here to the **destination** isn't visible yet. Wayfinding is about finding that way, not charging at the destination. This skill charts the way as a **shared map** on the repo's issue tracker, then works its tickets one at a time until the route is clear.

The destination varies per effort, and naming it is the first act of charting — it shapes every ticket. It might be a spec to hand off and iterate on, a decision to lock before planning starts, or a change made in place like a data-structure migration. The map is domain-agnostic — engineering work, course content, whatever fits the shape.

## Plan, don't do

Wayfinder is **planning** by default: each ticket resolves a decision, and the map is done when the way is clear — nothing left to decide before someone goes and does the thing. The pull to just do the work is usually the signal you've reached the edge of the map and it's time to hand off. An effort can override this in its **Notes** — carrying execution into the map itself — e.g. a manuscript-drafting effort using `draft` and `revise` tickets. Absent that override, produce decisions, not deliverables.

## Refer by name

Every map and ticket is an issue, so it has a **name** — its title. In everything the human reads — narration, the map's Decisions-so-far — refer to it by that name, never by a bare id, number, or slug. A wall of `#42, #43, #44` is illegible; names read at a glance. The id and URL don't vanish — a name wraps its link — but they ride *inside* the name, never stand in for it.

## The Map

The map is a single issue on this repo's issue tracker, labelled `wayfinder:map` — the canonical artifact. Its tickets are child issues of the map.

The map is an **index**, not a store. It lists the decisions made and points at the tickets that hold their detail; a decision lives in exactly one place — its ticket — so the map never restates it, only gists it and links.

**The map records decisions, never recomputable state.** Anything that is a function of the artifacts as they stand — a verdict, a count, a check that two lists still correspond — is re-runnable in a second, so it is not recorded here at all. **Asserting a *document property* in the map is banned outright**: nothing revalidates a recorded property, so it goes stale in silence, in the one view every session reads while it is orienting. A real map recorded two such properties as settled fact and both were false.

**Where the map, its child tickets, blocking, and frontier queries physically live is tracker-specific.** The issue tracker should have been provided to you — run `/setup-matt-pocock-skills` if not. Consult the tracker doc's "Wayfinding operations" section for how _this_ repo expresses them. If no tracker has been provided, default to the local-markdown tracker.

### The map body

The whole map at low resolution, loaded once per session. Open tickets are **not** listed — they are open child issues, found by query.

```markdown
## Destination

<what reaching the end of this map looks like — the spec, decision, or change this effort is finding its way to. One or two lines; every session orients to it before choosing a ticket.>

## Notes

<domain; skills every session should consult; standing preferences for this effort>

## Style

<keyed deltas against the drafting skill's key set, plus additive prose>

## Decisions so far

<!-- the index — one line per closed ticket: enough to judge relevance, then zoom the link for the detail the ticket holds -->

<!-- EXCEPT `draft` and `revise`, which are keyed by **unit**: exactly one line per unit, always current. A `revise` ticket's line takes the original's slot — nothing is lost, the superseded ticket stays reachable through the `revise` ticket's own **Supersedes** pointer -->

- [<closed ticket title>](link) — <one-line gist of the answer>

## Not yet specified

<!-- see "Fog of war": in-scope fog you can't ticket yet; graduates as the frontier advances -->

## Out of scope

<!-- see "Out of scope": work ruled beyond the destination; closed, never graduates -->
```

A map may carry additional `##` sections required by the domain skill its `## Notes` names. The domain skill owns their templates and their contents; wayfinder owns only the requirement that a declared section is instantiated.

`## Style` is the one such section shipped by name above, because holding every draft to it is a step in this skill's own loop. An effort with no drafting tickets has no domain skill declaring it and leaves it out.

### Tickets

Each ticket is a **child issue** of the map; the tracker's issue id is its identity. Its body is the question, sized to one 100K token agent session:

```markdown
## Question

<the decision or investigation this ticket resolves>
```

Each ticket carries a `wayfinder:<type>` label — one of `research`, `prototype`, `grilling`, `task`, `draft`, `revise` (see [Ticket Types](#ticket-types)).

A session **claims** a ticket by assigning it to the dev driving the map, **first**, before any work, so concurrent sessions skip it. That assignee _is_ the claim: an open, unassigned ticket is unclaimed.

Blocking uses the tracker's **native** dependency relationship — essential because it renders the frontier _visually_ in the tracker's own UI, so the human sees what's takeable without opening the map. Only a tracker that lacks native blocking falls back to a body convention. A ticket is **unblocked** when every ticket blocking it is closed; the **frontier** is the open, unblocked, unclaimed children — the edge of the known.

The answer isn't part of the body — it's recorded on resolution (see [Work through the map](#work-through-the-map)). Assets created while resolving a ticket are linked from the issue, not pasted in.

## Ticket Types

Every ticket is either **HITL** — human in the loop, worked *with* a human who speaks for themselves — or **AFK**, driven by the agent alone. A HITL ticket only resolves through that live exchange; the agent never stands in for the human's side of it (a grilling agent that answers its own questions has broken this).

- **Research** (AFK): Reading documentation, third-party APIs, or local resources like knowledge bases. Creates a markdown summary as a linked asset. Use when knowledge outside the current working directory is required.
- **Prototype** (HITL): Raise the fidelity of the discussion by making a cheap, rough, concrete artifact to react to — an outline, a rough take, a stub, or UI/logic code via the /prototype skill. Links the prototype as an asset. Use when "how should it look" or "how should it behave" is the key question.
- **Grilling** (HITL): Conversation via the /grilling and /domain-modeling skills, one question at a time. The default case.
- **Task** (HITL or AFK): Manual work that must happen before a *decision* can be made — nothing to decide, prototype, or research, but the discussion is blocked until it's done. Signing up for a service so its API can be judged, provisioning access, moving data so its shape can be seen. This is the one type that *does* rather than decides — and it earns its place by unblocking a decision, not by delivering the destination. The agent drives it alone where it can (AFK); otherwise it hands the human a precise checklist (HITL). Resolved when the work is done; the answer records what was done and any resulting facts (credentials location, new URLs, row counts) later tickets depend on.
- **Draft** (HITL, checkpointed): Produces prose — one **unit** of the piece, where a unit is one top-level skeleton slot and its subtree, 1:1 with its rung, its brief and its word budget — via the `/write-paper` skill. Valid only when this effort's Notes declare execution in scope (see "Plan, don't do").

  Its checkpoint is a **render plus a review**, not prose alone: render the unit with `/render-paper` at `--section` granularity, then run `/review-paper` over **the render, not the annotated source**.

  The ticket closes when the gate reports **zero FAILs** and every judgement finding is either **fixed**, **written back as a `!` annotation**, or **explicitly dispositioned with a reason**. **Silence is not a disposition.** There is no `CLEAN` verdict to record.

  The resolution records the drafted file, the gate's per-check table, and **the commit ref the prose closed at** — a later `revise` reconstructs that render from the ref.

  Like any ticket, a `draft` ticket can be blocked by open `task` tickets — a fact to confirm against code or an external party — that must resolve before the unit can be drafted faithfully. A load-bearing gap found *while* drafting does **not** hold the ticket open: it is written back as a `!` annotation and re-homed as its own `task` ticket blocking the whole-piece ticket.
- **Revise** (HITL, checkpointed): Re-drafts a unit whose `draft` ticket is **already closed**. Behind the same execution-in-scope gate as `draft`. A **new child issue**; the superseded `draft` ticket **stays closed, permanently** — reopening it would re-block every ticket downstream of it and make the frontier a function of history rather than of state, and this skill's out-of-scope rule leans on a closed ticket being unambiguously off the frontier.

  **The discriminator is mechanical: is the unit's `draft` ticket already closed?** A dirty per-section checkpoint is **not** a trigger — that happens while the ticket is still open, and its cure is more work inside that same open ticket. And `revise` is for changes to **prose**: a mechanical source-representation change with a **checkable invariant** — every unit's per-sentence set of cited sources unchanged, say — is a `task`, because a revision costs a full unit review and an invariant a machine can check costs nothing.

  **Four triggers**, each filed by the session that caused it:

  1. a **ladder amendment** — a `task` ticket amended a rung this unit was drafted against, and that ticket files it;
  2. a **skeleton amendment** — an escalated structural change under the locality test, filed by the ticket that escalated it;
  3. a **whole-piece chain-walk break** — every unit passed its own checkpoint and the document-absolute walk found a debt opened and never closed, or closed and never opened; the whole-piece ticket files one per unit it implicates;
  4. a **migration** — prose drafted under an older contract being brought onto the current one, filed by the effort running the migration.

  **Body:**

  ```markdown
  ## Revise

  **Supersedes:** <the closed draft ticket, by name and link> @ <commit ref>
  **Trigger:** <which of the four, naming the amending ticket>
  **Scope:** <what the trigger changed — the amended rung, the moved slot, the broken debt>
  ```

  **There is no field listing what must not change.** A keep-list is the shape the evidence already rejected: give a drafter a list of items and it drops some silently, and the agent that drops a claim is the same agent that would omit it from the list. The drop-guard is instead **mechanical** — a supersession diff against the old render, which `/render-paper` reconstructs from the recorded commit ref (`--supersedes`), reported as a **finding, never a gate**.

  **Its checkpoint is a strict superset of `draft`'s** — the full render, the full review, plus the supersession diff. **Never narrowed to the touched region.** Untouched prose passed against the **superseded** rung; if the trigger was a ladder amendment, the unit's obligations have moved, and prose that was correct under the old rung may be wrong under the new one without a single word of it changing.

  **Propagation:** whoever changes a rung **or its drafted actual** immediately runs the chain walk **over the downstream subgraph only**. Units whose inherited debt still closes are left alone; units where it no longer closes get their own `revise`. Direction is strictly downstream. The whole-piece chain walk remains the final backstop.

  **A `revise` may not be satisfied by an unconditional transform.** A migration is not filed as a sweep; it is per-unit, relation-first work.

  **Its map index line takes the original's slot** — the index is keyed by unit for both types, so a revision replaces the line it falsifies rather than sitting beside it.

**Whole-piece review.** A `draft` effort should include one `task`-labeled ticket, blocked on every `draft` ticket closing, that runs `/assemble-paper` — promotion plus the one editorial pass, once and irreversibly — then `/render-paper`, then `/review-paper` over the assembled whole rather than a single unit. Cross-references and cross-section contradictions are a different question than any one unit's local check, and only surface once everything is in place — this is the pass where the whole-document checks are **in scope** rather than printing `SKIPPED — OUT OF SCOPE AT THIS GRANULARITY`. It is also where a `task` ticket re-homing a load-bearing gap belongs, blocking this ticket rather than the `draft` ticket that found it.

## Fog of war

The map is _deliberately_ incomplete: don't chart what you can't yet see. Beyond the live tickets lies the **fog of war** — the dim view of decisions and investigations you can tell are coming but can't yet pin down, because they hang on questions still open. Resolving a ticket clears the fog ahead of it, graduating whatever's now specifiable into fresh tickets — one at a time, until the way to the destination is clear and no tickets remain.

The map's **Not yet specified** section is where that dim view is written down: the suspected question, the area to revisit later. It's the undiscovered frontier _toward_ the destination — everything here is in scope, just not sharp enough to ticket. Write as loosely or as fully as the view allows; it doubles as a signpost for collaborators reading where the effort is headed.

**Fog or ticket?** The test is whether you can state the question precisely now — _not_ whether you can answer it now.

- **Ticket when** the question is already sharp — even if it's blocked and you can't act on it yet.
- **Not yet specified when** you can't yet phrase it that sharply. Don't pre-slice the fog into ticket-sized pieces: it's coarser than a ticket, and one patch may graduate into several tickets, or none, once the frontier reaches it.

**Not yet specified** excludes what's already decided (Decisions so far), what's already a live ticket, and what's out of scope (the next section).

## Out of scope

Fog only ever gathers _toward_ the destination. The destination fixes the scope, so work beyond it is **out of scope** — it isn't fog, and it doesn't belong in **Not yet specified**. It gets its own **Out of scope** section on the map: work you've consciously ruled out of _this_ effort. Scope, not sharpness, lands it here.

Out-of-scope work never graduates — the frontier stops at the destination — so it returns only if the destination is redrawn, and then as a fresh effort, not a resumption.

Ruling something out of scope is a scoping act, not a step on the route. When a ticket that already exists turns out to sit past the destination — mis-scoped in while charting, or exposed by a resolution — **close it** (a closed ticket is unambiguously off the frontier) and leave one line in the **Out of scope** section: the gist plus why it's out of scope, linking the closed ticket. It stays out of **Decisions so far**, which records the route actually walked — a scope boundary isn't a step on it.

## Invocation

Two modes. Either way, **never resolve more than one ticket per session.**

### Chart the map

User invokes with a loose idea.

1. **Name the destination.** Run a `/grilling` and `/domain-modeling` session to pin down what this map is finding its way to — the spec, decision, or change. The destination fixes the scope, so it's settled first.
2. **Map the frontier.** Grill again, **breadth-first** this time: fan out across the whole space rather than deep on any one thread, surfacing the open decisions and the first steps takeable now. **If this surfaces no fog** — the way to the destination is already clear, the whole journey small enough for one session — you don't need a map. Stop and ask the user how they'd like to proceed.
3. **Create the map** (label `wayfinder:map`): Destination and Notes filled in, Decisions-so-far empty, the fog sketched into **Not yet specified** — and **instantiate every `##` section the domain skill named in `## Notes` declares.** A map missing a section its domain skill reads is a **charting defect**, not a drafting one. Leave a declared section empty rather than omitting it: empty is a state a reader can announce, absent is not.
4. **Create the tickets you can specify now** as child issues of the map — then wire blocking edges in a **second pass** (issues need ids before they can reference each other). Wiring sorts them into the frontier and the blocked; everything you can't yet specify stays in the fog — the **Not yet specified** section.
5. Stop — charting the map is one session's work; do not also resolve tickets.

### The two-map pattern (for efforts that carry execution)

An effort that carries execution runs as **two maps**, and their blocking edges mean different things. An effort that reinvents the pattern gets that difference wrong, and it is not derivable from the phase names.

- **The planning map** yields the settled inputs — for a drafting effort, the skeleton, the ladder, and one brief per unit. Its edge semantics: the **skeleton ticket blocks the ladder ticket**, and **the ladder ticket blocks every brief ticket** (a brief cannot be written against a rung that does not exist).
- **The draft map** yields the deliverable itself. Its edge semantics: **the ladder's debt edges *are* the blocking edges.** A unit that closes a debt is blocked by the unit that opens it. The frontier is therefore derived from the argument, and every parallelism the argument permits survives.

The draft map's `## Notes` carries only what is genuinely per-effort — the settled inputs and their paths. It does not restate the `draft` ticket type, the source/output file contract, the ordering, or the framing rules: those are skill-level, and framing rules belong in `## Style`. In a real draft map, five of seven `## Notes` blocks were skill-level decisions and one re-transcribed this skill's own `draft` type — a copy that was already wrong, because it turned on a verdict word abolished since.

### Work through the map

User invokes with a map (URL or number). A ticket is **optional** — without one, you pick the next decision, not the user.

1. Load the **map** — the low-res view, not every ticket body.
2. Choose the ticket. If the user named one, use it. Otherwise take the first frontier ticket in order. **Claim it**: assign it to yourself before any work.
3. Resolve it — **zoom as needed**: fetch the full body of any related or closed ticket on demand; invoke the skills the `## Notes` block names, and hold every draft to the map's `## Style` section. If in doubt, use `/grilling` and `/domain-modeling`.
4. Record the resolution: post the answer as a **resolution comment**, **close** the issue, and **append a context pointer** to the map's Decisions-so-far — except for a `draft` or `revise` ticket, whose line is keyed by **unit**: write that unit's single line, **replacing** whatever stood in its slot.
5. Add newly-surfaced tickets (create-then-wire); graduate any fog the answer has made specifiable, clearing each graduated patch from **Not yet specified** so it lives only as its new ticket. If the answer reveals a ticket — this one or another — sits beyond the destination, **rule it out of scope** rather than resolving it on the route. If the decision invalidates other parts of the map, update or delete those tickets.

The user may run unblocked tickets in parallel, so expect other sessions to be editing the tracker concurrently.
