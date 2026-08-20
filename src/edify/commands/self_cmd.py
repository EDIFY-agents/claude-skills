"""`edify self` — the binary talking about itself.

Two commands, and the split between them is deliberate: one reads, one writes.

    edify self where     which edify is this, and where did it come from
    edify self update    put an edited checkout behind that binary

**This is not `edify upgrade`.** `upgrade` pulls a newer *skill library* into
`.edify/`; `self update` replaces the CLI. Two different things, two names, and
the closing line of each says which one the person probably wanted.

**This is the second command that reaches the network.** `cli.py` claims none do
except `upgrade`, and building a wheel from a checkout fetches `hatchling` unless
it is already cached, so the claim is amended here rather than quietly broken.
`--offline` is the opt-in that fails cleanly instead of reaching out.

**It does not touch `.edify/` in any repository.** Updating the CLI and
reinstalling the harness into a checkout are separate operations; the second one
is `edify setup . --fresh`.
"""

from __future__ import annotations

import json
import subprocess
import sys

from .. import __version__, selfinstall
from ..context import Context
from ..errors import EdifyError

#: An install builds a wheel and may resolve a build backend over the network.
#: Generous, because a slow first build on a cold cache is not a failure.
TIMEOUT = 600


def where(ctx: Context) -> int:
    """Which edify is this, and where did it come from. Reads only."""
    info = selfinstall.describe()
    ctx.out.data(info)

    ctx.out.line("version      edify " + info["version"])
    ctx.out.line("binary       " + (info["executable"] or "not resolvable from argv[0]"))
    ctx.out.line("interpreter  " + info["interpreter"])
    ctx.out.line("prefix       " + info["prefix"])
    ctx.out.line("package      " + info["package"])
    ctx.out.line("installer    " + info["manager"] + "   (override with --manager)")
    ctx.out.line("source       " + (info["source"] or "none — this is a built install, not a checkout"))

    argv = selfinstall.install_command(
        info["manager"], info["source"] or ".", editable=bool(info["source"])
    )
    ctx.out.line("")
    ctx.out.line("update with  " + " ".join(argv))
    return 0


def update(ctx: Context) -> int:
    """Reinstall `edify` from a source checkout, using the tool that installed it."""
    out = ctx.out
    args = ctx.args

    source = selfinstall.resolve_source(
        getattr(args, "from_path", None), repo_root=ctx.layout.root
    )
    manager = getattr(args, "manager", "") or selfinstall.detect_manager()
    editable = bool(getattr(args, "editable", False))
    offline = bool(getattr(args, "offline", False))
    argv = selfinstall.install_command(manager, source, editable=editable, offline=offline)

    before = __version__
    out.note("source    " + str(source))
    out.note("installer " + manager + (" (editable)" if editable else ""))

    if getattr(args, "dry_run", False):
        out.data({"source": str(source), "manager": manager, "command": argv, "ran": False})
        out.line(" ".join(argv))
        out.note("nothing was installed — this is --dry-run")
        return 0

    with _spinner(ctx, "installing edify from " + str(source)):
        code, output = _run(argv)

    if code != 0:
        if selfinstall.looks_locked(output):
            raise EdifyError(
                "the running edify could not be replaced — this binary is open in this shell",
                hint=selfinstall.unlock_hint(manager, source, editable=editable),
            )
        raise EdifyError(
            manager + " could not install from " + str(source) + " (exit " + str(code) + ")",
            hint=_first_useful_line(output) or "run the command above by hand to see the whole failure",
        )

    after = _installed_version()
    out.data(
        {
            "source": str(source),
            "manager": manager,
            "command": argv,
            "ran": True,
            "version_before": before,
            "version_after": after,
        }
    )
    if after and after != before:
        out.ok("edify " + before + " -> " + after)
    elif after:
        # Not a failure — reinstalling an unchanged version is the common case
        # while developing. But it is also exactly what a shadowed second copy
        # looks like, so the sentence says both rather than only the happy one.
        out.ok("edify " + after + " installed from " + str(source))
        out.note("the version did not change. If you expected it to, `edify self where` "
                 "shows which binary is answering.")
    else:
        out.ok("installed from " + str(source))
        out.note("the new binary did not report a version; check `edify self where`")

    out.line("")
    out.line("This replaced the CLI. To reinstall the harness into a repository, "
             "run `edify setup . --fresh`.")
    return 0


# ---------------------------------------------------------------------------


def _run(argv: list[str]) -> tuple[int, str]:
    """Run the installer. Its output is captured so a failure can be read."""
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
        )
    except FileNotFoundError:
        return 127, argv[0] + " is not on PATH"
    except subprocess.TimeoutExpired:
        return 124, "timed out after " + str(TIMEOUT) + "s"
    except OSError as exc:
        return 1, str(exc)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _installed_version() -> str:
    """Ask the *new* binary what it is.

    Deliberately invoked as a fresh subprocess rather than read from the module
    already imported here — the whole point is to find out what the next
    invocation will be, and a shadowed install shows up as a version that did not
    move (plan, Risks).
    """
    for argv in (["edify", "version", "--json"], [sys.executable, "-m", "edify.cli", "version", "--json"]):
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode != 0:
            continue
        try:
            return str(json.loads(proc.stdout).get("version", ""))
        except (ValueError, AttributeError):
            continue
    return ""


def _first_useful_line(output: str) -> str:
    for line in reversed((output or "").splitlines()):
        line = line.strip()
        if line and not line.startswith(("Resolved", "Prepared", "Downloaded")):
            return line[:200]
    return ""


def _spinner(ctx: Context, label: str):
    """The infinity, while the installer runs.

    `anim.spinner` decides whether to paint: at a terminal it does, and everywhere
    else the label is printed once as a static line.
    """
    from .. import anim

    return anim.spinner(ctx.out, label)
