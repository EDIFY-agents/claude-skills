---
name: implementer-python
description: Implements a build task in a Python service or library codebase.
kind: skill
role: implementer
phase: 0 1 3 4 5 6
tech: python django flask fastapi sqlalchemy pydantic celery
provenance: original
license: -
---

# Implementer — Python

## What you're doing

One task from a build plan in a Python codebase. It names its files, the pattern to
follow, the steps, and the check. You do exactly that.

## How the work goes

1. Read the task block. Open only the ranges it names.
2. Open the pattern pointer and copy its shape: how the module is laid out, how
   errors are raised and caught, how the test fixtures are built, whether the
   codebase uses dataclasses, pydantic models, or plain dicts. That file is the
   convention.
3. Before writing a helper, `edify graph where <name>`. The graph parses Python
   with a real syntax tree, so its answers about this language are exact.
4. Match the type-annotation level of the surrounding code. If the module is fully
   annotated and the repository runs mypy or pyright, annotate fully; if it is not,
   do not annotate half of it.
5. Respect the import style already present — absolute or relative, and where the
   `__init__.py` re-exports live. `edify graph defines <file>` shows what a module
   already exports.
6. Run the done-check exactly as written, then the type check and the linter if the
   repository has them. `.edify/conventions.md` names the real commands.

## The traps specific to this stack

- A mutable default argument (`def f(x=[])`) is shared across calls. Use `None` and
  build inside.
- A bare `except:` swallows `KeyboardInterrupt` and `SystemExit`. Catch the
  exception the code actually raises.
- In an async codebase, a synchronous call in an async path blocks the loop for
  every request. Check whether the surrounding functions are `async def` before
  reaching for a blocking client.
- An ORM query inside a loop is the N+1 that shows up under load and never in a
  test. Follow whatever eager-loading pattern the codebase already uses.
- Session and transaction boundaries belong where the existing code puts them. A
  commit in a service function of a codebase that commits in the request layer is
  a rollback that will not roll back.

## When you're stuck

- **The task is wrong** — write `BLOCKED T-n: <what you found, with file:line>` and
  stop.
- **The task is silent on something real** — pick what the surrounding code does,
  add one row to `## Decisions`, and continue.

Do not restructure what the task did not name. Do not add a dependency the plan did
not decide on.

## What you hand back

The task id, the files you changed, the done-check output verbatim, and `done`,
`blocked: <reason>`, or `decided: <the row>`.
