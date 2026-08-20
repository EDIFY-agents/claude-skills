---
name: spec
description: A brief becomes a specification.
model: strongest
ends-at: a human
---

# /spec

Turn a couple of sentences into a specification a non-engineer can read and a
planner can build from. A mistake here is paid for again on every task downstream,
so this is the slow, expensive command and it is meant to be.

## What you read

The brief — whatever the person typed, or the file they pointed at. The graph, for
every claim about this codebase. The existing `specs/<feature>/spec.md` if you are
amending one. Not the codebase directly: `edify graph where`, `edify graph
dependents`, and `edify graph defines` answer structural questions exactly, and
exploring produces a slightly different answer every session.

## What you write

`specs/<feature>/spec.md`, in the format at `.edify/formats/spec.format.md`. The
worked example beside it is the calibration — read it before writing the first one.

## The loop, bounded at three passes

1. Capture the brief verbatim into `## Brief`. Never edit it afterwards. It is the
   only uncontaminated statement of intent in the system, and both the adversary
   and the final review check the result against it rather than against the draft
   that grew out of it.
2. Draft the intent clauses, the constraints, the requirements, the assertions, and
   the non-goals. Every claim about the codebase comes from a graph query.
3. Launch one adversary — a separate agent given only the brief and the finished
   draft, never your reasoning. Its question is: what does this feature entail that
   nobody asked for and the draft did not catch? Its findings append to
   `## What this entails` and `## Open questions`, marked adversary-found.
4. Re-read the draft against the brief. Every intent clause served by at least one
   requirement, every requirement by at least one assertion, every assertion
   carrying a verification kind from the ladder.
5. Stop when a pass finds nothing new, or at three passes. Hitting the bound is
   information: the brief is genuinely ambiguous, and the residue goes into
   `## Open questions` where a human sees it rather than into more token spend.

Run `edify check` before showing anyone the result.

## What this command refuses

Writing application code. A requirement with no assertion. An assertion that cannot
fail, or that carries no verification kind. Skipping the adversary because the
feature looks simple. A citation that is a bare filename rather than `file:line` or
the literal `new`. Naming a specific library or version — that is a decision, and
decisions belong to `/plan`.

## The gate

Show the human: the intent, the requirements, the closure checklist with open rows
highlighted, the open questions, and a rough cost band. They resolve the questions
or accept the defaults on the record, and approve. Five minutes, once per feature,
and it is the step that stops a beautifully built wrong thing.

Format: `.edify/formats/spec.format.md` · Example: `.edify/formats/spec.example.md`
