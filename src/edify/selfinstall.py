"""Where this `edify` came from, and how to put a newer one in its place.

`edify upgrade` is already taken and means something else entirely — it pulls a
newer *skill library*. This module is about the binary itself: which tool put
`edify` on PATH, which checkout the running code was imported from, and the exact
argv that would reinstall one from the other.

Everything here is a pure function. Nothing runs a subprocess, writes a file, or
prints — `commands/self_cmd.py` does all of that. That is what makes the part
worth getting right unit-testable without ever installing anything.

**The manager is detected, not assumed** (plan D-1, D-2). The binary was put on
PATH by uv, pipx, or pip, and only that tool can correctly replace it. A hardcoded
`pip install` into a uv tool environment produces a second, shadowed copy — the
worst possible outcome for a command named "update". `uv/tools/edify-cli` and
`pipx/venvs/edify-cli` are structural path segments rather than conventions, so
`sys.prefix` is enough to tell them apart, and `--manager` overrides when it is
not, which makes a mis-detection cost one flag rather than a broken install.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .errors import EdifyError

#: The distribution name in `pyproject.toml`. A directory is a usable source
#: checkout only if its manifest names this — otherwise `--from .` typed in the
#: wrong folder would cheerfully install something else over `edify`.
DIST_NAME = "edify-cli"

MANAGERS = ("uv", "pipx", "pip")


def is_source_checkout(path: Path | str) -> bool:
    """Does this directory hold a `pyproject.toml` naming `edify-cli`?"""
    manifest = Path(path) / "pyproject.toml"
    try:
        text = manifest.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return False
    # A dependency-free parse: `name = "edify-cli"` on its own line. `tomllib`
    # would do this on 3.11+ and not on 3.10, which this package supports.
    for line in text.splitlines():
        stripped = line.strip().replace(" ", "")
        if stripped == 'name="' + DIST_NAME + '"':
            return True
        if stripped == "name='" + DIST_NAME + "'":
            return True
    return False


def running_source() -> Path | None:
    """The checkout the running `edify` was imported from, when there is one.

    Walks up from the package directory looking for a manifest that names
    `edify-cli`. On an editable install this resolves directly to the repository;
    on a wheel install there is no such manifest above `site-packages`, so it
    returns None and `resolve_source` falls back to the repository root.
    """
    from . import __file__ as package_file

    for parent in Path(package_file).resolve().parents:
        if is_source_checkout(parent):
            return parent
    return None


def resolve_source(explicit: str | None = None, repo_root: Path | str | None = None) -> Path:
    """Which checkout to install from: `--from`, else the running one, else the repo.

    Raises rather than guessing. Installing from a directory that is not an
    `edify-cli` checkout is not an update, and finding that out afterwards costs
    the person the working binary they started with.
    """
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_dir():
            raise EdifyError(
                str(path) + " is not a directory",
                hint="--from takes a path to an edify checkout",
            )
        if not is_source_checkout(path):
            raise EdifyError(
                str(path) + " is not an edify checkout",
                hint="its pyproject.toml does not name `" + DIST_NAME + "`",
            )
        return path

    source = running_source()
    if source is not None:
        return source

    if repo_root is not None and is_source_checkout(repo_root):
        return Path(repo_root).resolve()

    raise EdifyError(
        "no edify source checkout to install from",
        hint="run this inside a clone of the repository, or pass `--from PATH`",
    )


def detect_manager(prefix: Path | str | None = None) -> str:
    """Which tool installed this binary, read from `sys.prefix`'s path segments.

    uv keeps tool environments under `uv/tools/<dist>` and pipx under
    `pipx/venvs/<dist>`; both are structural rather than conventional. Anything
    else — a plain venv, a system Python, a `pip install -e .` — is `pip`, which
    is also the right default: pip installs into the environment it is run from,
    so a wrong guess there is a no-op rather than a shadowed second copy.
    """
    prefix = Path(prefix if prefix is not None else sys.prefix)
    parts = [p.lower() for p in prefix.parts]
    for i, part in enumerate(parts):
        nxt = parts[i + 1] if i + 1 < len(parts) else ""
        if part == "uv" and nxt == "tools":
            return "uv"
        if part == "pipx" and nxt in ("venvs", "venv"):
            return "pipx"
    if "uv" in parts:
        return "uv"
    if "pipx" in parts:
        return "pipx"
    return "pip"


def install_command(
    manager: str,
    source: Path | str,
    editable: bool = False,
    offline: bool = False,
) -> list[str]:
    """The exact argv that reinstalls `edify` from `source` using `manager`.

    Returned rather than run, so `--dry-run` prints the same list the real run
    executes. There is no second code path for the two, which is the only way
    `--dry-run` can be trusted to describe what will happen.
    """
    if manager not in MANAGERS:
        raise EdifyError(
            "unknown installer `" + str(manager) + "`",
            hint="--manager takes one of: " + ", ".join(MANAGERS),
        )
    src = str(source)

    if manager == "uv":
        argv = ["uv", "tool", "install", "--force", "--reinstall"]
        if editable:
            argv.append("--editable")
        if offline:
            argv.append("--offline")
        argv.append(src)
        return argv

    if manager == "pipx":
        argv = ["pipx", "install", "--force"]
        if editable:
            argv.append("--editable")
        # pipx has no --offline of its own; it forwards pip options verbatim.
        if offline:
            argv += ["--pip-args", "--no-index"]
        argv.append(src)
        return argv

    argv = [sys.executable, "-m", "pip", "install", "--force-reinstall"]
    if editable:
        argv.append("--editable")
    if offline:
        argv.append("--no-index")
    argv.append(src)
    return argv


def binary_path() -> str:
    """The `edify` that is running, as the shell resolved it.

    `sys.argv[0]` is what was invoked; on a console-script install that is the
    launcher on PATH, which is what a person means by "which edify is this".
    """
    argv0 = sys.argv[0] if sys.argv else ""
    if not argv0:
        return ""
    try:
        return str(Path(argv0).resolve())
    except OSError:
        return argv0


def package_dir() -> Path:
    from . import __file__ as package_file

    return Path(package_file).resolve().parent


def describe() -> dict[str, str]:
    """Everything `edify self where` prints, as data. No side effects at all."""
    from . import __version__

    source = running_source()
    return {
        "version": __version__,
        "executable": binary_path(),
        "interpreter": sys.executable,
        "prefix": sys.prefix,
        "package": str(package_dir()),
        "manager": detect_manager(),
        "source": str(source) if source is not None else "",
        "editable": "yes" if source is not None else "no",
    }


#: What an installer says when the running `edify.exe` is held open by this very
#: process. Windows cannot replace a running executable, so the failure has to be
#: recognised and reported with the command to run from another shell — never
#: swallowed, and never reported as the success it was not.
LOCKED_MARKERS = (
    "access is denied",
    "permission denied",
    "being used by another process",
    "used by another process",
    "text file busy",
    "winerror 5",
    "winerror 32",
    "failed to remove file",
    "failed to persist",
)


def looks_locked(text: str) -> bool:
    """Did this installer failure come from the running binary being held open?"""
    low = (text or "").lower()
    return any(marker in low for marker in LOCKED_MARKERS)


def unlock_hint(manager: str, source: Path | str, editable: bool = False) -> str:
    """The exact one-liner to run from another shell when the binary is locked."""
    argv = install_command(manager, source, editable=editable)
    return "close this shell, then run: " + " ".join(_quote(a) for a in argv)


def _quote(arg: str) -> str:
    return '"' + arg + '"' if " " in arg else arg
