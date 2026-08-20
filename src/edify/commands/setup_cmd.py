"""`edify setup [PATH]` — the whole harness, in a folder, from nothing.

`init` is the incremental one: it finds the repository root by walking upward, keeps
every file that is already there, and merges into an instruction file somebody else
wrote. That is the right behaviour for a repository under way and the wrong behaviour
twice over for a folder you are starting in:

**It installs somewhere else.** `find_root` walks up until it finds `.edify/`, `.git/`,
or a manifest, so `mkdir service && cd service && edify init` inside an existing
checkout installs into the *parent* — the same `.edify/` the outer repository already
has, silently. `setup` anchors the root at exactly the path it was given and never
looks above it. A folder that does not exist yet is created.

**It keeps what is there.** "Install everything, again, properly" is not what `init`
does without `--force`, and `--force` still leaves behind the files a previous version
wrote under names this one no longer uses. `--fresh` removes EDIFY's own surface
first — `.edify/`, the host pointers it generated, and its block in `CLAUDE.md` — and
then installs the lot. Nothing outside that surface is touched, ever: `--fresh` is not
`rm -rf`, and a folder with source code in it comes out with the source code in it.

Everything else is `init`, called with `force` on, so there is one install path and not
two that drift.
"""

from __future__ import annotations

from pathlib import Path

from .. import anim
from ..context import Context
from ..errors import EdifyError
from ..host import clear as host_clear
from ..paths import Layout
from . import init_cmd


def run(ctx: Context) -> int:
    root = Path(getattr(ctx.args, "path", None) or ".").expanduser()
    if root.exists() and not root.is_dir():
        raise EdifyError(f"{root} is a file, not a folder")

    created = not root.exists()
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()

    # The one thing `setup` does that `init` cannot: pin the root rather than search
    # for it, so a new folder inside an existing checkout installs into the new folder.
    layout = Layout(root)
    scoped = Context(args=ctx.args, layout=layout, out=ctx.out)

    # The wordmark opens the install, once, above `setup`'s own first line rather
    # than in the middle of it. `caller_opens` is how `init_cmd` is told not to
    # print a second one — the same shape as `caller_closes` at the other end.
    anim.banner(ctx.out)
    ctx.args.caller_opens = True

    ctx.out.line(f"setup     {root}{' (created)' if created else ''}")

    if getattr(ctx.args, "fresh", False):
        cleared = _clear(layout)
        ctx.out.line(f"fresh     {len(cleared)} edify-owned path(s) cleared before installing")
        for path, action in cleared:
            ctx.out.note(f"  {action} {layout.rel(path)}")

    # `init` merges by default; setup means install everything, so force is on.
    scoped.args.force = True
    ctx.out.line("")
    return init_cmd.run(scoped)


def _clear(layout: Layout) -> list[tuple[Path, str]]:
    """Remove EDIFY's own surface and nothing else. `(path, what happened to it)`.

    The work is `host.clear`, which `init new` also runs. Two commands that both mean
    "install everything, again, properly" must not each have their own idea of what
    that clears — the second one to be written would inevitably miss a family the
    first one knew about.
    """
    return host_clear(layout)
