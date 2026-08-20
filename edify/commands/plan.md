---
name: plan
description: A specification becomes technical decisions and a sequence.
model: strongest
ends-at: a human
---

# /plan

Make every decision that binds more than one task, once, so that no task has to
make one. Skipped for most features, and skipping it is the normal case.

## When this runs at all

Write a plan when any of these is true: the feature introduces a technology,
library, or external service this repository does not already use; it spans more
than one milestone or shippable stage; it needs cross-cutting strategy — a
migration sequence, a build variant, a bundled asset, a shared component, a config
surface; or more than one person will build parts of it.

Otherwise go straight from `/spec` to `/tasks`. A one-page plan is ceremony, and a
repository whose plans are all one page should stop writing them.

## What you read

The approved `spec.md`, and the graph. Nothing else.

## What you write

`specs/<feature>/plan.md`, in the format at `.edify/formats/plan.format.md`.

## The passes

1. **Cut into milestones** by dependency, and write each dependency rule with its
   reason. `/tasks` relaxes rules when a plan is amended and cannot do that safely
   without knowing why each one exists.
2. **Decide the technology.** Each row names the alternative it beat and an exact
   version — `2.3`, not `^2.3` and not `latest`. A row with no alternative is a
   default, and should say so rather than being dressed as a decision; a default is
   much cheaper to revisit six months later.
3. **Write the cross-cutting strategy.** Migration numbers allocated once here so
   two tasks never claim the same one. Build variants. Bundled assets with a size
   budget stated rather than discovered. Shared components named so three later
   milestones do not each build their own. And the verification budget for any
   assertion the spec marks above `property` on the ladder.
4. **Resolve the context seeds** — per milestone, `(file, line-start, line-end,
   why)` resolved against the graph, so `/tasks` inherits them instead of
   re-deriving them. A seed without a line range transfers its cost downstream,
   which is the whole thing this document exists to prevent.
5. **Map the risks**, each to the milestone that mitigates it. A risk with no
   mitigation has been noticed rather than handled, and the row should say that
   rather than looking handled.

Run `edify check` before the gate.

## What this command refuses

Specifying function signatures or data structures beyond the contracts — that is
`/tasks`, which has the graph queries to make them accurate. A technology row with
no exact version. A context seed with no line range. Carrying dates: sizes and
sequences, never a schedule.

## The gate

Show the human the milestone sequence, the decisions with their alternatives, and
the risks. This is where an architectural disagreement is cheap.

Format: `.edify/formats/plan.format.md` · Example: `.edify/formats/plan.example.md`
