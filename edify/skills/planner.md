---
name: planner
description: Writes a spec, a plan, or a task list against the graph rather than by exploring.
kind: skill
role: planner
phase: 0 1 2 3 4 5 6 7
tech: any
provenance: original
license: -
---

# Planner

## What you're doing

Producing one of the three documents — a spec, a plan, or a task list — before any
code exists. Everything downstream is paid for again if this is wrong, so this is
the slow step and it is meant to be.

## How the work goes

1. Read the input document in full: the brief for a spec, the spec for a plan, both
   for a task list. Read the whole thing before writing anything.
2. Answer every structural question with the graph, not by opening files.
   `edify graph where <name>` gives file, line and kind. `edify graph dependents
   <symbol>` gives everything that breaks. `edify graph defines <file>` says what a
   file exports. These are exact and take milliseconds; exploring takes minutes and
   gives a slightly different answer each session.
3. Before writing that something must be built, ask the graph whether it already
   exists. Reuse beats writing, and a large feature built in one pass should not
   end up with three functions that do the same thing.
4. Every reference you write is `file:line` or `file:line-line`, or the literal
   `new`. A bare filename passes review and transfers its cost to whoever runs the
   task, one step downstream, where nobody attributes it.
5. When you cannot place something against the graph, that is information: you do
   not yet know where the work lands. Say so in the document rather than writing a
   filename and moving on.
6. Read `.edify/conventions.md` once. It is a scrape of this repository's config
   files — lint, formatter, type checker, test layout, the CI job's real commands —
   and it is what the build will be measured against.
7. Run `edify check` before you show anything to anyone. It reports the defects
   this format has: a requirement with no assertion, a technology row with no
   version, a task with no done-check, an empty coverage cell.

## When you're stuck

- **The input is ambiguous.** Do not pick and move on. Write the readings the
  ambiguity allows, say which one this draft adopted and why, and put it in
  `## Open questions`. The human gate is five minutes and it exists for exactly
  this.
- **The graph has no nodes for a language in this repository.** Check
  `.edify/graph/meta` for `languages_uncovered`. That gap is real, not a lookup
  failure — say what you could not place rather than guessing at it.

## What you hand back

The document written to its path, the output of `edify check` verbatim, and one
line naming what the human has to decide at the gate.
