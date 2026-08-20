"""The project ledger: how many repositories the free plan has installed into.

The fifth gate, and the first one that is about how *much* rather than how *big*.
Three projects on free (`FREE_PROJECT_CAP`), unlimited on paid.

**It never leaves this machine.** There is no telemetry, ever
(`docs/pricing.md` §4 commitment 2), so the ledger is a readable TSV in
`user_config_dir()` rather than a hashed or hidden file (plan D-6). Obfuscating it
would buy nothing — nobody is being told about it — and would cost the person the
ability to see and manage their own limit with `cat`.

**A project's identity is its `git remote origin`** (D-7). A re-clone, a second
worktree, and a fresh CI checkout are all the same project. Keying on the path
would burn a slot every CI run, which turns the free tier into a bug report; a
generated UUID inside `.edify/` would get committed and then shared between users.
The resolved path is the fallback for a folder with no remote, which is exactly
the case where the path *is* the identity.

**It never breaks work already done.** Only a *new* project is refused. A
repository already in the ledger keeps installing forever, `known()` prunes rows
whose path is gone so a deleted repository returns its slot without anyone asking,
and every non-install command ignores the ledger entirely.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from ..paths import user_config_dir
from ..tsv import read_rows, write_rows

HEADER = ("key", "path", "first_seen")

#: What `register` returns. Three outcomes, and the caller decides which of them
#: is a failure — this module never raises, because "over the cap" is a fact
#: about a licence and not an error inside a ledger.
ALREADY = "already"
REGISTERED = "registered"
OVER_CAP = "over_cap"


@dataclass(frozen=True)
class Project:
    key: str
    path: str
    first_seen: int = 0

    @property
    def exists(self) -> bool:
        return Path(self.path).is_dir()

    @property
    def by_remote(self) -> bool:
        """Keyed on a git remote rather than a path — so a re-clone is free."""
        return not self.key.startswith("path:")

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "path": self.path,
            "first_seen": self.first_seen,
            "exists": self.exists,
            "keyed_on": "remote" if self.by_remote else "path",
        }


def ledger_path() -> Path:
    """`projects.tsv` beside the licence. `EDIFY_HOME` moves both together."""
    return user_config_dir() / "projects.tsv"


def canonical(root: Path | str) -> str:
    """One spelling of a path, for both the ledger and every comparison.

    Forward slashes even on Windows. `tsv.escape` doubles a backslash, so a native
    Windows path lands in the file with every separator doubled — reversible, and
    unreadable, which costs exactly the property D-6 is for. `paths.rel` already
    renders this way for the same reason.
    """
    try:
        return Path(root).expanduser().resolve().as_posix()
    except OSError:
        return Path(root).as_posix()


def key_for(root: Path | str) -> str:
    """This project's identity: its origin remote, else its resolved path.

    Normalised so `git@github.com:me/x.git` and `https://github.com/me/x` are one
    project — otherwise cloning over SSH after cloning over HTTPS costs a slot for
    no reason a person could ever guess.
    """
    remote = _origin(root)
    if remote:
        return _normalise_remote(remote)
    return "path:" + canonical(root)


def known() -> list[Project]:
    """Every project in the ledger whose folder is still there.

    Pruning on read rather than on a schedule: a deleted repository returns its
    slot the next time anything looks, with no command to run and no support
    ticket. The file is rewritten only when something actually went away.
    """
    rows = _read()
    live = [p for p in rows if p.exists]
    if len(live) != len(rows):
        _write(live)
    return live


def all_rows() -> list[Project]:
    """Everything on disk, pruned or not. For `license projects`, which shows both."""
    return _read()


def register(root: Path | str, cap: int | None) -> str:
    """Record this project, or say it does not fit. Never raises.

    `cap` is `None` on a paid plan, which means the ledger is still written — so
    a licence that lapses does not suddenly find three arbitrary projects in it —
    and never consulted.
    """
    key = key_for(root)
    resolved = canonical(root)
    rows = known()

    for row in rows:
        if row.key == key:
            if row.path != resolved:
                # The same project, moved or re-cloned somewhere else. Follow it
                # rather than adding a second row, which is the whole point of D-7.
                rows = [Project(key, resolved, row.first_seen) if r.key == key else r for r in rows]
                _write(rows)
            return ALREADY

    if cap is not None and len(rows) >= cap:
        return OVER_CAP

    rows.append(Project(key, resolved, int(time.time())))
    _write(rows)
    return REGISTERED


def forget(key_or_path: str) -> Project | None:
    """Release one slot, by key or by path. Returns what was removed, or None.

    Releasing a slot must not require a support ticket, so this takes whichever
    of the two things a person has in front of them.
    """
    wanted = str(key_or_path).strip()
    resolved = canonical(wanted)
    rows = _read()
    for row in rows:
        if row.key == wanted or row.path == wanted or (resolved and row.path == resolved):
            _write([r for r in rows if r.key != row.key])
            return row
    return None


def slots(cap: int | None) -> tuple[int, int | None]:
    """`(used, cap)` — what `license status` and the gate copy both print."""
    return len(known()), cap


# ---------------------------------------------------------------------------


def _read() -> list[Project]:
    out: list[Project] = []
    for row in read_rows(ledger_path()):
        if len(row) < 2:
            continue
        try:
            first_seen = int(row[2]) if len(row) > 2 and row[2] else 0
        except ValueError:
            first_seen = 0
        out.append(Project(row[0], row[1], first_seen))
    return out


def _write(rows: list[Project]) -> None:
    write_rows(ledger_path(), [[r.key, r.path, str(r.first_seen)] for r in rows], HEADER)


def _origin(root: Path | str) -> str:
    """`git remote get-url origin`, or nothing.

    `check=False` with a timeout, the pattern `doctor_cmd` already uses: a machine
    without git, or a folder that is not a checkout, is an ordinary case here and
    not a failure.
    """
    try:
        proc = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _normalise_remote(url: str) -> str:
    """`git@host:owner/repo.git` and `https://host/owner/repo` to one string."""
    value = url.strip().rstrip("/")
    for prefix in ("https://", "http://", "ssh://", "git://"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
            break
    else:
        if value.startswith("git@"):
            value = value[4:].replace(":", "/", 1)
    if "@" in value.split("/", 1)[0]:  # https://user@host/…
        value = value.split("@", 1)[1]
    if value.endswith(".git"):
        value = value[:-4]
    return value.lower()
