<!-- edify:begin -->
# EDIFY
Stack: python  ·  Tests: pytest

## Commands
/spec   — write the spec before anything else
/plan   — technology decisions and milestones, for work that needs them
/tasks  — turn an approved spec into the phased build plan
/build  — execute an approved plan, start to finish
/verify — re-run everything and produce the evidence

## The codebase map
.edify/graph/ — every symbol, route, and table, with the edges between them.
  edify graph where <name>        → file:line and signature
  edify graph dependents <symbol> → everything that breaks if it changes
Search the graph before reading files. Never guess a path.

## Where things live
Features: specs/<feature>/   Skills: .edify/skills/   Servers: .edify/mcp.md
<!-- edify:end -->

## Contributing to this repository

EDIFY is built with EDIFY. Beyond the block above, three rules bind every change
here — see [CONTRIBUTING.md](CONTRIBUTING.md) for the rest:

1. **No runtime dependencies.** `[project] dependencies` is empty and stays
   empty. CI fails a PR that adds one.
2. **No network call** outside `edify upgrade` and `edify self update`. CI greps
   for this on every push.
3. **The graph is never written by a model.** A missing symbol is a visible gap;
   an invented one is a guess wearing the costume of a fact.

The design dossier in [`docs/design/`](docs/design/) is the source of truth —
`01-principles.md` has the eight laws every decision satisfies, and
`10-what-we-dropped.md` is the ledger of every cut and what it cost. Read the
relevant one before proposing a change to behaviour.

Commits are signed off (`git commit -s`).
