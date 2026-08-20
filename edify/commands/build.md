---
name: build
description: A plan becomes working software.
model: cheapest that follows written instructions
ends-at: a diff and a green suite
---

# /build

Execute the whole task list in one run, phases in order. This command does not
plan, does not choose, does not research, and does not improvise.

## What you read

The approved `tasks.md`. That is the only input. The spec and the plan are
deliberately withheld: a builder with access to the reasoning behind the plan has
judgment again, and judgment at build time is the one thing the executor is defined
by not having.

## What you write

Code, and the `## Decisions` section of `tasks.md`.

## The run

```
for each phase in order:
    for each parallel-safe group in the phase:
        spawn one agent per task
          payload: skill file + task block + ## Decisions
          servers: edify mcp for <role> <phase>      # usually zero or one
    run the phase exit check
    edify graph update <the directories that changed>
    append any forced decision to ## Decisions
```

Resolve the skill with `edify skills resolve <role> <phase>` — one lookup, one
line, one file path. Never browse the skills directory to decide.

Phase 2 ends with the suite entirely red. That is the correct state and the target
every later phase is measured against. Phase 7 is `/verify` in a fresh agent that
wrote none of the code.

## The three rules that define this executor

- **It does not plan.** No restructuring, no "while I'm here", no better idea.
- **It does not explore.** The task says where; the graph answers structure; the
  docs server answers library questions. If none of the three has the answer, the
  plan was incomplete and that is a finding, not a gap to fill with judgment.
- **It does not adapt.** A task that cannot be done as written stops, writes one
  blocker line, and the run continues with independent tasks.

## On failure

A failed done-check is retried once. On the second failure the debugger runs with
the accumulated evidence. On the third the task is marked blocked and the run
continues on tasks that do not depend on it. A blocked task at the end of a run is
a `/tasks` amendment — a normal Tuesday, not a crisis.

## What this command refuses

Running against an unapproved plan. Running phases out of order. Editing a contract
frozen at the end of phase 1. Making a design decision the plan left open without
recording it in `## Decisions`. Declaring a task done without its check passing.
