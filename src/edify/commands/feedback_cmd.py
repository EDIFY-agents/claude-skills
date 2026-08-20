"""`edify feedback` — say how this is going, to a file on this machine.

The command writes and prints. It never opens a socket: `edify upgrade` is the only
command in this CLI that does, and adding a second one for a satisfaction survey
would trade the product's central claim for a funnel metric.
"""

from __future__ import annotations

from .. import feedback
from ..context import Context
from ..errors import EdifyError


def new(ctx: Context) -> int:
    message = (getattr(ctx.args, "message", None) or "").strip()

    if message:
        entry = feedback.Entry(answers={"doing": message})
    else:
        entry = feedback.interview(ctx.out)
        if entry is None:
            raise EdifyError(
                "there is no terminal here to ask",
                hint='use `edify feedback --message "..."`, which needs no prompt',
            )
        if not any(v.strip() for v in entry.answers.values()):
            ctx.out.line("nothing written — every answer was empty")
            return 0

    path = feedback.write(entry)
    ctx.out.data({"path": str(path), "sent": False, "how": feedback.how_to_send(path)})
    ctx.out.line(f"written  {path}")
    ctx.out.line("")
    ctx.out.line("Nothing left this machine. When you want us to read it:")
    for line in feedback.how_to_send(path):
        ctx.out.line(f"  {line}")
    return 0


def list_(ctx: Context) -> int:
    entries = feedback.existing()
    ctx.out.data([str(p) for p in entries])
    if not entries:
        ctx.out.line("nothing written yet — `edify feedback` asks four questions")
        return 0
    for path in entries:
        first = _subject(path)
        ctx.out.line(f"{path.stem}  {first}")
    ctx.out.line("")
    ctx.out.line(f"{len(entries)} in {feedback.directory()} · none of it has been sent anywhere")
    return 0


def show(ctx: Context) -> int:
    entries = feedback.existing()
    if not entries:
        ctx.out.line("nothing written yet")
        return 0
    wanted = getattr(ctx.args, "which", None)
    path = entries[-1]
    if wanted:
        matches = [p for p in entries if p.stem == wanted or p.stem.lstrip("0") == wanted.lstrip("0")]
        if not matches:
            raise EdifyError(f"no feedback entry `{wanted}`", hint="`edify feedback list` shows them")
        path = matches[0]
    ctx.out.data({"path": str(path), "body": path.read_text(encoding="utf-8")})
    ctx.out.line(path.read_text(encoding="utf-8").rstrip())
    return 0


def off(ctx: Context) -> int:
    feedback.set_enabled(False)
    ctx.out.line("the feedback invitation will not appear again")
    ctx.out.line(f"turn it back on with `edify feedback on` · state lives in {feedback.state_path()}")
    return 0


def on(ctx: Context) -> int:
    feedback.set_enabled(True)
    ctx.out.line("the feedback invitation is on — at most one line, once per released version")
    return 0


def _subject(path) -> str:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "-")):
            return stripped[:70]
    return "(no answers)"
