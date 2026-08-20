---
name: implementer-go
description: Implements a build task in a Go service codebase.
kind: skill
role: implementer
phase: 0 1 3 4 5 6
tech: go gin echo
provenance: original
license: -
---

# Implementer — Go

## What you're doing

One task from a build plan in a Go service. It names its files, the pattern to
follow, the steps, and the check.

## How the work goes

1. Read the task block. Open only the ranges it names.
2. Open the pattern pointer and copy its shape: how the handler is wired, how
   errors are wrapped, how the interface is declared next to its consumer, how the
   table test is laid out.
3. Before writing a helper, `edify graph where <name>`. Duplicated helpers across
   packages are the usual outcome of a large feature built without one.
4. Keep the exported surface as small as the task needs. An identifier that starts
   with a capital letter is API; everything that does not have to be is not.
5. Wrap errors with `%w` and context, in whatever phrasing the surrounding code
   already uses. Do not introduce a second error package.
6. Write the test as a table test if the neighbouring tests are table tests. Run
   `go test ./... -race` when the repository's CI does; a data race that only shows
   under `-race` is still a data race.
7. Run the done-check exactly as written, then `go vet` and the repository's
   linter.

## The traps specific to this stack

- A loop variable captured by a goroutine before Go 1.22 is the same variable every
  iteration. Check the `go` directive in `go.mod` before relying on either
  behaviour.
- A `context.Context` that is not threaded through means a cancelled request keeps
  working. Pass the one you were given; do not reach for `context.Background()` in
  a request path.
- A deferred `Close` inside a loop does not run until the function returns.
- A nil map is readable and panics on write.
- An interface satisfied by a nil pointer is not itself nil, which is how a
  returned error that "is nil" is not.

## When you're stuck

- **The task is wrong** — write `BLOCKED T-n: <what you found, with file:line>` and
  stop.
- **The task is silent on something real** — pick what the surrounding code does,
  add one row to `## Decisions`, and continue.

Do not restructure packages the task did not name. Do not add a dependency the plan
did not decide on.

## What you hand back

The task id, the files you changed, the done-check output verbatim, and `done`,
`blocked: <reason>`, or `decided: <the row>`.
