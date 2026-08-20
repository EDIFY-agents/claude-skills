---
name: implementer-react
description: Implements a build task in a React or Next.js front end.
kind: skill
role: implementer
phase: 0 3 4 5 6
tech: react nextjs vue svelte
provenance: original
license: -
---

# Implementer — front end

## What you're doing

One surface task: a screen, a component, or a route, built against a contract that
was frozen at the end of phase 1. It names its files, the pattern to follow, the
steps, and the check.

## How the work goes

1. Read the task block. Open only the ranges it names.
2. Open the pattern pointer — usually an existing page that does the same shape of
   thing — and copy its state machine exactly. Most pages in a codebase render the
   same four states in the same order: loading, error, ready, submitted. Matching
   that is worth more than any styling decision you could make.
3. Use the generated or shared API client the codebase already has. Do not write a
   `fetch` by hand next to a client that exists.
4. Import request and response types from the frozen contract. Never redeclare a
   shape a phase-1 task defined.
5. Render **one message per error code**, not one generic failure. The spec's error
   states name each case, and a single "something went wrong" discards the work
   that decided what each case means.
6. Follow the existing routing registration — the same array, the same block, the
   same public-versus-authenticated distinction.
7. Write the test with the same request-mocking setup the neighbouring test uses,
   one handler per state.
8. Run the done-check exactly as written, then the type check.

## The traps specific to this stack

- A missing loading state renders an empty screen that looks like a bug to a user
  and like success to a test.
- A key on a list that is an array index re-orders wrongly the moment the list
  changes. Use the id the data already has.
- An effect that fetches without a cleanup or an abort races itself on fast
  navigation.
- An unauthenticated page's response body is the whole security surface: render
  only what the contract returns, and assert the exact key set in the test rather
  than a subset.

## When you're stuck

- **The task is wrong** — write `BLOCKED T-n: <what you found, with file:line>` and
  stop.
- **The task is silent on something real** — copy the neighbouring page, add one
  row to `## Decisions`, and continue.

Do not restyle components the task did not name. Do not introduce a state library
the plan did not decide on.

## What you hand back

The task id, the files you changed, the done-check output verbatim, and `done`,
`blocked: <reason>`, or `decided: <the row>`.
