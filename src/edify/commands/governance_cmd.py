"""`edify governance` — what EDIFY put here, and whether it is still what it put.

Three subcommands and no enforcement. `verify` prints and, with `--exit-code`,
returns non-zero so a customer who needs a hard block owns one in their own CI. The
same honest scope `edify check` has, for the same reason.
"""

from __future__ import annotations

from .. import governance
from ..context import Context


def list_(ctx: Context) -> int:
    ctx.layout.require_installed()
    records = governance.load(ctx.layout) if ctx.layout.governance.is_file() else governance.scan(ctx.layout)

    ctx.out.data([r.as_dict() for r in records])
    ctx.out.table(
        ["path", "kind", "origin", "provenance", "license", "source"],
        [[r.path, r.kind, r.origin, r.provenance, r.license, r.source] for r in records],
    )
    counts = governance.summary(records)
    ctx.out.line("")
    ctx.out.line(
        f"{len(records)} files · " + " · ".join(f"{n} {origin}" for origin, n in sorted(counts.items()))
    )
    return 0


def verify(ctx: Context) -> int:
    ctx.layout.require_installed()
    problems = governance.verify(ctx.layout)

    ctx.out.data(
        {
            "problems": [p.as_dict() for p in problems],
            "serious": sum(1 for p in problems if p.serious),
        }
    )

    for problem in problems:
        colour = "red" if problem.state == "missing" else "yellow" if problem.serious else "dim"
        ctx.out.line(f"{ctx.out.c(problem.state.ljust(10), colour)} {problem.path}  {problem.detail}")

    serious = [p for p in problems if p.serious]
    if not problems:
        ctx.out.line("every governed file is what the ledger says it is")
    else:
        ctx.out.line("")
        ctx.out.line(f"{len(serious)} to look at · {len(problems) - len(serious)} edited by this repository")

    if getattr(ctx.args, "exit_code", False) and serious:
        return 2
    return 0


def rebuild(ctx: Context) -> int:
    """Re-baseline. Run it after a deliberate change, so the next `verify` is quiet."""
    ctx.layout.require_installed()
    records = governance.rebuild(ctx.layout)
    ctx.out.data({"files": len(records), "ledger": ctx.layout.rel(ctx.layout.governance)})
    ctx.out.line(f"{len(records)} files recorded in {ctx.layout.rel(ctx.layout.governance)}")
    return 0
