"""A repository's identity for licence binding: its root commit (REQ-52).

A `team` licence may name the root commit of the repository it is for. The root
commit survives renames, forks of the remote and moves on disk, and needs no
network to read. A shallow clone hides it, so a shallow clone reports that rather
than guessing (plan.md R-9).
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def root_commits(repo: Path) -> tuple[list[str], str]:
    """The repository's root commits, or why they cannot be read."""
    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=10, check=False,
        )

    try:
        shallow = git("rev-parse", "--is-shallow-repository")
        if shallow.returncode != 0:
            return [], "not a git repository"
        if shallow.stdout.strip() == "true":
            return [], "a shallow clone hides the root commit — run `git fetch --unshallow`"
        roots = git("rev-list", "--max-parents=0", "HEAD")
    except (OSError, subprocess.SubprocessError):
        return [], "git is not available"
    if roots.returncode != 0:
        return [], "the repository has no commits yet"
    return [line.strip() for line in roots.stdout.splitlines() if line.strip()], ""
