"""`edify check` — the whole validation story, and it is a command, not a gate.

A person runs it, or CI runs it, and it prints what is wrong. Nothing halts a
session. `--exit-code` exists because a customer who needs a hard block should own
one; that is the honest scope in `docs/design/01-principles.md` P7.
"""

from __future__ import annotations

from ..context import Context
from ..formats.check import check_repository
from ..formats.finding import Level
from ..formats.fix import fix_repository


def run(ctx: Context) -> int:
    ctx.layout.require_installed()
    out = ctx.out

    repairs = []
    if ctx.args.fix:
        store = ctx.store if ctx.store.exists() else None
        repairs = fix_repository(ctx.layout, store)
        for repair in repairs:
            out.line(f"fixed {repair.file}:{repair.line} — {repair.what}")
        if repairs:
            out.line("")

    findings = check_repository(ctx.layout, ctx.store if ctx.store.exists() else None)
    if not ctx.store.exists():
        out.note("no graph — reference resolution was skipped. Run `edify graph build` for the full check.")

    errors = [f for f in findings if f.level is Level.ERROR]
    warnings = [f for f in findings if f.level is Level.WARN]
    infos = [f for f in findings if f.level is Level.INFO]

    out.data(
        {
            "findings": [f.as_dict() for f in findings],
            "repairs": [r.__dict__ for r in repairs],
            "errors": len(errors),
            "warnings": len(warnings),
        }
    )

    for finding in findings:
        if finding.level is Level.ERROR:
            out.line(ctx.out.c(finding.render(), "red"))
        elif finding.level is Level.WARN:
            out.line(ctx.out.c(finding.render(), "yellow"))
        else:
            out.line(finding.render())

    if findings:
        out.line("")
    out.line(f"{len(errors)} errors · {len(warnings)} warnings · {len(infos)} notes")
    if not findings:
        out.line("nothing to report")

    if ctx.args.exit_code and errors:
        return 2
    if ctx.args.exit_code and ctx.args.strict and warnings:
        return 2
    return 0
