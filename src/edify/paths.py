"""Where everything lives, and how the repository root is found.

The installed tree is nine paths (`docs/design/architecture/01-folder-structure.md` §2).
This module is the only place those names are written down.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .errors import NotInstalled

# Markers that identify a repository root, in the order they are trusted.
ROOT_MARKERS = (
    ".edify",
    ".git",
    "pyproject.toml",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
    "Gemfile",
)


def find_root(start: str | os.PathLike[str] | None = None) -> Path:
    """Walk up from `start` to the nearest repository root.

    `.edify` and `.git` win outright. A manifest file only counts if nothing
    above it is a stronger marker, which keeps a monorepo package from being
    mistaken for the repository.
    """
    here = Path(start or os.environ.get("EDIFY_REPO") or Path.cwd()).resolve()
    if here.is_file():
        here = here.parent
    strong: Path | None = None
    weak: Path | None = None
    for candidate in [here, *here.parents]:
        if (candidate / ".edify").is_dir() or (candidate / ".git").exists():
            strong = candidate
            break
        if weak is None:
            for marker in ROOT_MARKERS[2:]:
                if (candidate / marker).exists():
                    weak = candidate
                    break
    return strong or weak or here


@dataclass(frozen=True)
class Layout:
    """The installed tree, resolved against one repository root."""

    root: Path

    # -- .edify ----------------------------------------------------------

    @property
    def edify(self) -> Path:
        return self.root / ".edify"

    @property
    def graph_dir(self) -> Path:
        return self.edify / "graph"

    @property
    def nodes(self) -> Path:
        return self.graph_dir / "nodes.tsv"

    @property
    def edges(self) -> Path:
        return self.graph_dir / "edges.tsv"

    @property
    def meta(self) -> Path:
        return self.graph_dir / "meta"

    @property
    def skills_dir(self) -> Path:
        return self.edify / "skills"

    @property
    def skills_index(self) -> Path:
        return self.skills_dir / "index.tsv"

    @property
    def commands_dir(self) -> Path:
        return self.edify / "commands"

    @property
    def formats_dir(self) -> Path:
        return self.edify / "formats"

    @property
    def mcp(self) -> Path:
        return self.edify / "mcp.md"

    @property
    def conventions(self) -> Path:
        return self.edify / "conventions.md"

    @property
    def stack(self) -> Path:
        return self.edify / "stack.tsv"

    @property
    def profile(self) -> Path:
        """What the person said when `edify init new` asked. Theirs to edit, and the
        one file here that was not derived from something already on disk."""
        return self.edify / "profile.md"

    @property
    def governance(self) -> Path:
        """The ledger: every file EDIFY put in this repository, and where it came from."""
        return self.edify / "governance.tsv"

    # -- the host runtime's own tree --------------------------------------
    # `.edify/` is canonical and `.claude/` is the mirror, so these names are here
    # rather than spelled inline wherever something writes one. Three families,
    # because Claude Code discovers three things in three different shapes and an
    # entry filed under the wrong one is installed and undiscoverable.

    @property
    def host_dir(self) -> Path:
        return self.root / ".claude"

    @property
    def host_commands(self) -> Path:
        """`/spec` and friends — one flat file per command."""
        return self.host_dir / "commands"

    @property
    def host_skills(self) -> Path:
        """One directory per skill, each holding a `SKILL.md`."""
        return self.host_dir / "skills"

    @property
    def host_agents(self) -> Path:
        """One flat file per subagent. A `kind: agent` entry belongs here and not
        under `host_skills` — the runtime spawns from this directory and matches
        skills from that one, so the choice decides whether the entry can be a
        spawn at all."""
        return self.host_dir / "agents"

    # Every family as (directory, glob), for everything that has to walk all of them:
    # the governance scan, the clearing `setup --fresh` and `init new` do, and the
    # staleness check. Every runtime in the table, not only the one this run chose —
    # a folder set up for Cursor last month still has Cursor's pointers in it, and
    # they are EDIFY's to account for whether or not Cursor was named today.
    def host_trees(self) -> tuple[tuple[Path, str], ...]:
        from .agents import all_trees

        return tuple((self.root / directory, pattern) for directory, pattern in all_trees())

    def instruction_files(self) -> tuple[Path, ...]:
        """`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, and the rest — every file a runtime
        reads at the start of a session and EDIFY owns one block inside."""
        from .agents import all_instruction_paths

        return tuple(self.root / path for path in all_instruction_paths())

    # -- harvest ---------------------------------------------------------
    # EDIFY's own repository only (`10-harvest.md` §3). Everything under here is
    # untrusted text until a person has read it, and untrusted text does not belong
    # in a customer's tree at any stage of processing — which is why `edify init`
    # copies commands, formats, skills, and mcp, and never this.

    @property
    def harvest(self) -> Path:
        return self.root / "harvest"

    @property
    def harvest_ledger(self) -> Path:
        return self.harvest / "ledger.json"

    @property
    def harvest_staging(self) -> Path:
        return self.harvest / "staging"

    @property
    def harvest_quarantine(self) -> Path:
        return self.harvest / "quarantine"

    @property
    def harvest_proposals(self) -> Path:
        return self.harvest / "proposals"

    @property
    def library(self) -> Path:
        """The authored library an admitted entry lands in — the source tree, not an install."""
        return self.root / "edify" / "skills"

    @property
    def harvest_refs(self) -> Path:
        """`sources.md` and `vocab.md`, which are authored files rather than run state."""
        return self.root / "edify" / "harvest"

    def is_edify_repo(self) -> bool:
        """Whether this is the repository harvest is allowed to run in.

        The marker is the authored methodology tree itself. A client repository has
        `.edify/` and no `edify/harvest/`, so the boundary is checkable rather than
        merely documented.
        """
        return (self.harvest_refs / "sources.md").is_file()

    # -- the rest of the tree --------------------------------------------

    @property
    def specs(self) -> Path:
        return self.root / "specs"

    @property
    def claude_md(self) -> Path:
        return self.root / "CLAUDE.md"

    def feature(self, name: str) -> Path:
        return self.specs / name

    # -- checks ----------------------------------------------------------

    def installed(self) -> bool:
        return self.edify.is_dir()

    def require_installed(self) -> None:
        if not self.installed():
            raise NotInstalled(str(self.root))

    def rel(self, path: str | os.PathLike[str]) -> str:
        """A repository-relative POSIX path. Every path we write is in this form."""
        p = Path(path)
        try:
            p = p.resolve().relative_to(self.root)
        except ValueError:
            return Path(path).as_posix()
        return p.as_posix()


def layout(start: str | os.PathLike[str] | None = None) -> Layout:
    return Layout(find_root(start))


def user_config_dir(os_name: str | None = None, platform: str | None = None) -> Path:
    """Where a licence and machine-local state live. Never inside a repository.

    One directory per platform, each the one that platform's users expect:

        macOS     ~/Library/Application Support/edify
        Windows   %APPDATA%\\edify
        elsewhere $XDG_CONFIG_HOME/edify, or ~/.config/edify

    `EDIFY_HOME` overrides all of it, and an existing `~/.config/edify` wins on
    macOS — a machine that already has a licence there keeps it rather than
    silently losing it to a directory this version happens to prefer.

    The platform is a parameter so the other two can be tested from any one of
    them. Patching `os.name` to find out would change what `pathlib` builds.
    """
    os_name = os_name or os.name
    platform = platform or sys.platform

    override = os.environ.get("EDIFY_HOME")
    if override:
        return Path(override).expanduser()
    if os_name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "edify"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "edify"
    if platform == "darwin":
        legacy = Path.home() / ".config" / "edify"
        if legacy.is_dir():
            return legacy
        return Path.home() / "Library" / "Application Support" / "edify"
    return Path.home() / ".config" / "edify"
