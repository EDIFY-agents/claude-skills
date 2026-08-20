# 02 — The Commands

Seven, down from eight — but four of them a developer types, and the shape is different
in the way that matters: three slow thinking commands ending at a human, one fast dumb
executor, and three mechanical ones.

Every command file is ≤100 lines and contains: what it reads, the loop it runs, what it
refuses, what it writes, and one line pointing at the relevant format and example. No
format teaching, no policy prose, no restated laws.

---

## `/spec` — a brief becomes a specification

**Reads:** the brief (an argument, or a couple of sentences typed in), the graph, the
existing spec if amending.
**Writes:** `specs/<feature>/spec.md`.
**Model:** the strongest available. A mistake here is paid for on every task downstream.

**The loop**, bounded at three passes:

1. Capture the brief verbatim into `## Brief`. Never edited afterwards — it is what the
   adversary and the final review check against.
2. Draft: intent clauses, constraints, requirements, assertions, non-goals. Every claim
   about the codebase comes from a graph query, never from exploring.
3. Launch **one adversary** — a separate agent given only the brief and the draft, never
   the drafting reasoning. Its question: what does this feature entail that nobody asked
   for and the draft did not catch? Findings append to `## What this entails` and
   `## Open questions`, marked adversary-found.
4. Re-read the draft against the brief. Every intent clause served by at least one
   requirement; every requirement by at least one assertion; every assertion carrying a
   verification kind from the ladder (`08-verification.md` §1).
5. Stop when a pass finds nothing new, or at three passes. Hitting the bound is
   information — the residue goes into `## Open questions` where a human sees it.

**Gate:** the human sees intent, requirements, the closure checklist with open rows
highlighted, the open questions, and a rough cost band.

**Refuses:** writing application code; a requirement with no assertion; an assertion that
cannot fail; an assertion with no verification kind; skipping the adversary because the
feature "looks simple"; a citation that is a bare filename rather than `file:line` or
`new`; naming a specific library or version — that is a decision, and decisions are
`/plan`'s.

**Format:** `formats/spec.format.md` · **Example:** `../spec-ex.md`

---

## `/plan` — a specification becomes technical decisions and a sequence

**Reads:** the approved `spec.md`, the graph.
**Writes:** `specs/<feature>/plan.md`.
**Model:** the strongest available.
**Skipped** unless the feature introduces a technology, spans milestones, needs
cross-cutting strategy, or will be built by more than one person (`03-plan-format.md` §1).

**The passes:**

1. **Cut into milestones** by dependency, and write the dependency rules with their
   reasons — `/tasks` relaxes rules on amendment and cannot do that safely without them.
2. **Decide the technology**, each row naming the alternative it beat and an exact
   version. A row with no alternative is labeled a default, not dressed as a decision.
3. **Write the cross-cutting strategy** — migration numbers allocated once, build
   variants, bundled assets with a size budget, shared components, and the verification
   budget for anything above `property` on the ladder.
4. **Resolve the context seeds** — per milestone, `(file, line-start, line-end, why)`
   pointers, resolved against the graph so `/tasks` inherits them instead of re-deriving.
5. **Map the risks**, each to the milestone that mitigates it.

**Gate:** the human sees the milestone sequence, the decisions with their alternatives,
and the risks. This is where an architectural disagreement is cheap.

**Refuses:** specifying function signatures or data structures beyond the contracts —
that is `/tasks`, which has the graph queries to make them accurate; a technology row
with no version; a context seed without a line range; carrying dates.

**Format:** `03-plan-format.md` · **Example:** `../plan-ex.md`

---

## `/tasks` — spec and plan become a build plan

**Reads:** the approved `spec.md`, `plan.md` if it exists, the graph.
**Writes:** `specs/<feature>/tasks.md`.
**Model:** the strongest available.

**The passes:**

1. **Cut** — every requirement and every closure-checklist row becomes one or more
   tasks. A task that discharges nothing is refused; that is where scope creep enters.
2. **Place** — for each task, query the graph: `where` for the symbols it touches,
   `dependents` for everything that breaks. Write the exact file set and line ranges. A
   task that cannot be placed is a task the plan does not understand, and it blocks the
   gate.
3. **Order** — assign phases by dependency (`04-tasks-format.md` §1), respecting the
   plan's milestone rules. Mark the contracts that freeze at the end of phase 1.
4. **Write phase 2** — every assertion in the spec becomes a phase-2 task producing a
   *failing* test, at the verification kind the spec declared. This pass is not
   optional and is not merged into the tasks that implement the behavior.
5. **Parallelize** — within each phase, compute `overlap` between file sets including
   dependents. Exact, because the graph is exact; a task citing a whole file makes it a
   false positive and quietly collapses the phase to serial execution.
6. **Detail** — steps and done-check per task. This pass determines whether `/build` can
   run on a cheap model, and it is the pass most likely to be rushed.
7. **Close** — fill `## Coverage`, one row per requirement and checklist item, and check
   it is complete *before* showing it to anyone.

**Gate:** the human sees the phase list, the coverage table, and the tasks. The last
cheap moment to say "that is not how we do it here."

**Refuses:** a task with no requirement behind it; a task with no done-check; a
whole-file reference on anything but a new file; a phase-2 task whose done-check asserts
tests *pass*; starting implementation; showing an incomplete coverage table as if it
were complete.

**Format:** `04-tasks-format.md` · **Example:** `tasks.example.md`

---

## `/build` — a plan becomes working software

**Reads:** the approved `tasks.md`. That is the only input — the spec and plan are
deliberately withheld, because a builder that reads them has judgment again.
**Writes:** code, and the `## Decisions` section of `tasks.md`.
**Model:** the cheapest that follows written instructions reliably. The debugger and the
verifier step back up.

**The run:**

```
for each phase in order:
    for each parallel-safe group in the phase:
        spawn one agent per task
          payload: skill file + task block + decisions
          servers: mcp.where(role, phase)      # usually zero or one
    run the phase exit check
    re-extract the graph for the directories that changed
    append any forced decision to ## Decisions
```

Phase 2 ends with the suite entirely red — the correct state, and the target every later
phase is measured against. Phase 7 is `/verify` in a fresh agent.

**The three rules that define the executor:**

- **It does not plan.** No restructuring, no "while I'm here", no better idea.
- **It does not explore.** The task says where; the graph answers structure; the docs
  server answers library questions; if none of the three has the answer, the plan was
  incomplete and that is a finding.
- **It does not adapt.** A task that cannot be done as written stops, writes one blocker
  line, and the run continues with independent tasks.

**On failure:** a failed done-check is retried once. On the second failure the debugger
runs with the accumulated evidence. On the third the task is marked blocked and the run
continues on tasks that do not depend on it. A blocked task at the end of a run is a
`/tasks` amendment — a normal Tuesday, not a crisis.

**Refuses:** running against an unapproved plan; running phases out of order; editing a
contract frozen at phase 1; making a design decision the plan left open without recording
it; declaring a task done without its check passing.

---

## `/verify` — the code becomes evidence

**Reads:** the repository, `spec.md`, `tasks.md`, `plan.md`.
**Writes:** `specs/<feature>/verification.md`.
**Model:** strong, and **never a session that wrote code**.

Re-runs everything itself, confirms from git history that tests preceded code, exercises
the acceptance scenarios as real flows, walks the coverage table, checks the plan's
milestone gates, and reads the whole diff as one design. It runs things; it does not
decide things, and it never edits code.

Runs as phase 7 of every build, in CI on every push, and by hand whenever anyone wants
it. Full contract: `08-verification.md` §3.

---

## `/graph` — source becomes a map

Runs the extractor. No model, at any point, for any reason.

`build` does a full extraction; `update <dir>` does one directory, which runs after each
phase. Records the source commit and checksums into `meta`. Where the extractor does not
cover a language, the graph has no nodes for it and says so. Details: `06-graph.md`.

---

## `/harvest` — public capability becomes a library entry

Runs in EDIFY's own repository, never in a client's, because everything it touches is
untrusted text until a human has read it. Gather, screen, rewrite, propose; a person
admits. Designed in `10-harvest.md`, and built: the method is
`.claude/skills/harvest/SKILL.md`, the mechanical steps are `edify harvest`, and
`harvest/ledger.json` is what stops the second run repeating the first.

---

## What the previous eight became

| previous command | now |
|---|---|
| `/spec` | `/spec`, absorbing the brief, obligations, and assumptions — and shedding technology choices to `/plan` |
| — | **`/plan`**, new: the technology decisions and milestone sequence that previously lived nowhere |
| `/tasks` | `/tasks`, absorbing phase planning, adding the phase-2 verification pass, dropping tier scoring |
| `/phase-tasks plan` | gone — phases are headings in `tasks.md` |
| `/phase-tasks run` | `/build`, running the whole plan rather than one phase |
| `/verify` | **`/verify`**, kept — but execution-only, re-runnable by anyone, and also phase 7 |
| `/ship` | gone — the evidence is the diff, the green suite, and the approved documents |
| `/facts` | `/graph`, keeping the graph and dropping the seven flat fact files |
| `/doctor` | `edify doctor` (`09-cli.md`) — four checks, a convenience, not a gate |
| `/edify-init` | `edify init` — detect, extract, scrape conventions, select, seed the MCP registry, write `CLAUDE.md`. No interview |
