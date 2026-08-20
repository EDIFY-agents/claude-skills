---
name: tasks
description: A spec and a plan become a build plan.
model: strongest
ends-at: a human
---

# /tasks

Turn the approved documents into something a cheap model can execute without
thinking. The test is mechanical: if the builder has to think, this document was
incomplete.

## What you read

The approved `spec.md`, `plan.md` if there is one, and the graph. Every `file:line`
you write comes from a graph query, never from memory.

## What you write

`specs/<feature>/tasks.md`, in the format at `.edify/formats/tasks.format.md`. The
worked example beside it is the most important artifact in this system — the
difference between a good plan and a plausible one is entirely in that level of
detail, and it does not survive being described in the abstract.

## The passes

1. **Cut.** Every requirement and every closure-checklist row becomes one or more
   tasks. A task that discharges nothing is refused; that is where scope creep
   enters.
2. **Place.** For each task, `edify graph where` for the symbols it touches and
   `edify graph dependents` for everything that breaks. Write the exact file set
   and line ranges. A task that cannot be placed is a task the plan does not
   understand, and it blocks the gate rather than becoming build-time exploration.
3. **Order.** Assign phases by dependency, respecting the plan's milestone rules.
   Mark the contracts that freeze at the end of phase 1.
4. **Write phase 2.** Every assertion in the spec becomes a phase-2 task producing
   a *failing* test, at the verification kind the spec declared. This pass is not
   optional and is never merged into the tasks that implement the behaviour.
5. **Parallelise.** Within each phase, `edify graph overlap` between file sets
   including dependents. Exact, because the graph is exact. A task citing a whole
   file makes it a false positive and quietly collapses the phase to serial.
6. **Detail.** Steps and a done-check per task. This pass determines whether
   `/build` runs on a cheap model, and it is the pass most likely to be rushed.
7. **Close.** Fill `## Coverage`, one row per requirement and per checklist item,
   and check it is complete *before* showing it to anyone. An incomplete coverage
   table must never reach a gate looking complete.

Run `edify check` last. It reports a task with no discharge, no steps, or no
done-check; a whole-file reference on an edit; a phase-2 done-check that asserts
tests pass; and an empty coverage cell.

## What this command refuses

A task with no requirement behind it. A task with no done-check. A whole-file
reference on anything but a new file. A phase-2 task whose done-check asserts tests
*pass*. Starting implementation. Showing an incomplete coverage table as if it were
complete.

## The gate

Show the human the phase list, the coverage table, and the tasks. This is the last
cheap moment to say "that is not how we do it here."

Format: `.edify/formats/tasks.format.md` · Example: `.edify/formats/tasks.example.md`
