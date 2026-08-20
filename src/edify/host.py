"""The host runtimes' view of what is installed.

`.edify/` is the canonical tree and the only one EDIFY reasons about. A host runtime
discovers its own capabilities somewhere else, in shapes that differ per runtime and,
for Claude Code, in three shapes at once: commands at `.claude/commands/<name>.md`,
skills at `.claude/skills/<name>/SKILL.md` one directory each, and subagents at
`.claude/agents/<name>.md`. A library entry that exists only under `.edify/skills/`
is installed as far as `edify skills list` is concerned and invisible to the runtime
the person is actually typing into.

Which runtimes those are is `agents.py`, and this module takes the table as given:
one row means one set of directories to write into, and adding Cursor or Gemini to the
install is adding a row rather than a branch here.

Which of the three an entry gets is `kind`, and it is not cosmetic. The runtime
*matches* a skill against what the session is doing and *spawns* an agent by name, so
a `kind: agent` entry mirrored into `.claude/skills/` is loadable and unspawnable —
`/build` resolves it, asks for a subagent by that name, and gets nothing. That was
the state until this module learned the difference: `kind` had two legal values in
the skill format and one destination on disk.

So this module writes the mirror, and the mirror is **pointers**. Each generated file
carries the two fields the host discovers on (`name`, `description`) and then names
the canonical path; the method itself stays in exactly one place. A copy would go
stale the first time a skill file changed and nothing would say so.

Everything written here is `origin: generated` in `.edify/governance.tsv`, so
`edify governance verify` reports a hand-edit to a pointer as what it is: an edit to
a file EDIFY will overwrite.

One file is deliberately not touched: a `SKILL.md` that EDIFY did not generate. The
harvest skill in EDIFY's own repository is hand-authored at
`.claude/skills/harvest/SKILL.md` and is not a mirror of anything — overwriting it
with a pointer to a file that does not exist is the kind of helpfulness nobody asks
for twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import agents as agent_table
from . import assets
from .agents import Target
from .formats import skill as skill_format
from .paths import Layout

# The line every generated file carries, so `written_by_edify` is a read rather than
# a guess and a person opening one knows what it is in the first two seconds.
MARKER = agent_table.MARKER_MD
MARKER_TOML = agent_table.MARKER_TOML

# The shape the command pointers had before there was a marker. A repository that ran
# an earlier `init` has six of them, and without this they would all be treated as
# somebody's own files and never brought up to date.
LEGACY_MARKERS = agent_table.LEGACY_MARKERS


@dataclass
class Written:
    path: Path
    kind: str  # command | skill | agent
    name: str
    action: str  # written | kept | skipped
    target: str = "claude"  # which runtime this pointer is for


def sync(layout: Layout, *, host: str = "claude", agents: str = "") -> list[Written]:
    """Mirror the installed commands and skills into every chosen runtime's directories.

    There is no `force`, and that is the point. A pointer is derived output: if it
    differs from what it should say it is brought up to date, because a pointer at a
    file that has been renamed is worse than no pointer at all. And a file that is not
    one of ours is never written, with or without a flag — `init --force` means
    "replace what EDIFY installed", never "replace what you wrote".

    `agents` names the runtimes; unset, it means whichever ones are already set up in
    this folder, falling back to `host` when none are.
    """
    out: list[Written] = []
    for target in agent_table.resolve(agents, host, root=layout.root):
        out += sync_target(layout, target)
    return out


def sync_target(layout: Layout, target: Target) -> list[Written]:
    """One runtime's whole mirror: its commands, and its skills where it has them."""
    return _sync_commands(layout, target) + _sync_library(layout, target)


def _sync_commands(layout: Layout, target: Target) -> list[Written]:
    """Thin pointers so `/spec` resolves in the runtime.

    Written from the shipped set rather than from `.edify/commands/`, so a repository
    that has not run `init` yet still gets the full five.
    """
    if not target.commands:
        return []
    target_dir = layout.root / target.commands
    target_dir.mkdir(parents=True, exist_ok=True)
    out: list[Written] = []
    for source in sorted(assets.subtree("commands").glob("*.md")):
        name = source.stem
        pointer = target_dir / f"{name}{target.command_suffix}"
        body = _command_pointer(name, target)
        out.append(_write(pointer, body, "command", name, target.id))
    return out


def _command_pointer(name: str, target: Target) -> str:
    """The same two sentences, in whichever file format this runtime parses.

    The body never varies: read the contract, follow it. Only the wrapper does, and a
    runtime that reads TOML gets a `#` marker rather than an HTML comment because an
    HTML comment in a TOML file is a parse error, not a nicety.
    """
    instruction = (
        f"Read `.edify/commands/{name}.md` and follow it for this repository.\n"
        f"That file is the contract; this one only points at it."
    )
    if target.command_format == "toml":
        return (
            f"{MARKER_TOML}\n"
            f'description = "EDIFY /{name}"\n'
            f'prompt = """\n{instruction}\n"""\n'
        )
    return f"---\ndescription: EDIFY /{name}\n---\n\n{MARKER}\n\n{instruction}\n"


def _sync_library(layout: Layout, target: Target) -> list[Written]:
    """Every installed entry, each into the directory its `kind` belongs in.

    The description is copied rather than pointed at, in both shapes: it is what the
    runtime matches on when it decides whether a skill is relevant and what it reads
    when it decides which subagent to spawn, so a pointer whose description said "see
    the other file" would never be chosen. The coordinates go in beside it because
    `role · phase · tech` is what `/build` resolves on, and a person reading `.claude/`
    should be able to see why this entry exists without opening two files.

    A runtime with no skill directory of its own — most of them — gets nothing here,
    and that is correct rather than a gap: its instruction file names `.edify/skills/`
    and `edify skills resolve`, which is the whole library through one door.
    """
    if not (target.skills or target.agents):
        return []
    entries = skill_format.load_all(layout.skills_dir, layout.root)
    out: list[Written] = []
    for entry in entries:
        if not entry.name:
            continue  # an invalid file is not indexed, so it is not mirrored either
        if entry.kind == "agent" and target.agents:
            path = layout.root / target.agents / f"{entry.name}.md"
            out.append(_write(path, _agent_pointer(entry), "agent", entry.name, target.id))
        elif target.skills:
            path = layout.root / target.skills / entry.name / target.skill_file
            out.append(_write(path, _skill_pointer(entry), "skill", entry.name, target.id))
    return out


def _coordinates(entry: skill_format.Skill) -> str:
    return " · ".join([entry.role or "-", " ".join(entry.phases) or "-", " ".join(entry.tech) or "any"])


def _attribution(entry: skill_format.Skill) -> str:
    """Where this entry came from, on the face of the pointer.

    An adapted entry carries somebody else's licence, and the person who has to
    honour it is the one reading `.claude/`, not the one reading the source tree.
    """
    line = f"- **provenance** {entry.provenance or '-'}"
    if entry.license and entry.license != "-":
        line += f" · **licence** {entry.license}"
    return line


def _skill_pointer(entry: skill_format.Skill) -> str:
    return (
        f"---\nname: {entry.name}\ndescription: {entry.description}\n---\n\n"
        f"{MARKER}\n\n"
        f"# {entry.name}\n\n"
        f"Read `{entry.rel}` and follow it. That file is the entry; this one only points at it.\n\n"
        f"- **resolves at** `{_coordinates(entry)}` (role · phase · tech)\n"
        f"{_attribution(entry)}\n\n"
        f"`edify skills resolve {entry.role or '<role>'} <phase>` is what a build spawn runs to get here.\n"
    )


def _agent_pointer(entry: skill_format.Skill) -> str:
    """A subagent definition, which is one flat file and not a directory.

    Same pointer discipline as a skill — the method stays in `.edify/skills/` and this
    file carries only what the runtime discovers on. The difference is that a spawn
    starts with no history, so the pointer says to read the entry *first*: an agent
    that begins work before loading the method it was spawned for is the failure this
    shape exists to prevent.
    """
    return (
        f"---\nname: {entry.name}\ndescription: {entry.description}\n---\n\n"
        f"{MARKER}\n\n"
        f"# {entry.name}\n\n"
        f"Read `{entry.rel}` in full before doing anything else, then follow it. That file is\n"
        f"the entry; this one only points at it.\n\n"
        f"- **resolves at** `{_coordinates(entry)}` (role · phase · tech)\n"
        f"{_attribution(entry)}\n\n"
        f"The task you were spawned with names its own files and assertions. This entry is the\n"
        f"method; it never overrides the task.\n"
    )


def _write(path: Path, body: str, kind: str, name: str, target: str = "claude") -> Written:
    if path.exists():
        current = _text(path)
        if not _ours(current):
            return Written(path, kind, name, "skipped", target)
        if current == body:
            return Written(path, kind, name, "kept", target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return Written(path, kind, name, "written", target)


def written_by_edify(path: Path) -> bool:
    """Whether this file is one of ours, and therefore ours to replace."""
    return _ours(_text(path))


def _ours(text: str) -> bool:
    return agent_table.MARKER_TEXT in text or any(legacy in text for legacy in LEGACY_MARKERS)


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def stale(layout: Layout) -> list[Path]:
    """Generated skill and agent pointers whose entry is no longer installed.

    An entry removed from `.edify/skills/` leaves a pointer behind, and a pointer to a
    file that is gone is a capability the runtime will offer and then fail to read.
    Both families are walked, in every runtime that has them, including the case an
    entry changes `kind`: flipping `skill` to `agent` writes the new pointer and leaves
    the old one, which is one entry offered twice with only one of them working.

    Only ever our own files, and only ever reported — deleting is the caller's call.
    """
    entries = [s for s in skill_format.load_all(layout.skills_dir, layout.root) if s.name]
    installed = {s.name for s in entries}
    agents = {s.name for s in entries if s.kind == "agent"}
    out: list[Path] = []

    for target in agent_table.TARGETS:
        if target.skills:
            skills_dir = layout.root / target.skills
            if skills_dir.is_dir():
                for child in sorted(skills_dir.iterdir()):
                    pointer = child / target.skill_file
                    if not (child.is_dir() and pointer.is_file() and written_by_edify(pointer)):
                        continue
                    # Gone from the library, or still installed but now an agent —
                    # either way this file is a pointer nothing stands behind.
                    if child.name not in installed or child.name in agents:
                        out.append(pointer)

        if target.agents:
            agents_dir = layout.root / target.agents
            if agents_dir.is_dir():
                for pointer in sorted(agents_dir.glob("*.md")):
                    if not written_by_edify(pointer):
                        continue
                    if pointer.stem not in agents:
                        out.append(pointer)

    return out


def clear(layout: Layout) -> list[tuple[Path, str]]:
    """Remove EDIFY's own surface and nothing else. `(path, what happened to it)`.

    Three families, and the third is the one that needs care. `.edify/` is entirely
    ours. The runtime pointers — commands, skills, and agents, across every runtime in
    the table — are ours only where they carry the marker, so a command, skill, or
    subagent somebody wrote by hand stays. An instruction file (`CLAUDE.md`,
    `AGENTS.md`, `GEMINI.md`, …) is somebody else's file with our block in it, so the
    block goes and the file does not, and the report says which of those happened
    rather than calling both "removed".

    Shared by `setup --fresh` and `init new`, which both mean "install everything,
    again, properly" and would otherwise each have their own idea of what that clears.
    """
    import shutil

    cleared: list[tuple[Path, str]] = []

    if layout.edify.is_dir():
        shutil.rmtree(layout.edify)
        cleared.append((layout.edify, "removed"))

    for directory, pattern in layout.host_trees():
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob(pattern)):
            if not written_by_edify(path):
                continue
            path.unlink()
            cleared.append((path, "removed"))
            # A skill is a directory per entry, so an emptied one goes with it. A
            # command and an agent are flat files, and their directory is shared.
            if path.parent != directory and not any(path.parent.iterdir()):
                path.parent.rmdir()

    for path in layout.instruction_files():
        if not path.is_file():
            continue
        text = _text(path)
        if agent_table.BLOCK_BEGIN not in text or agent_table.BLOCK_END not in text:
            continue
        start = text.index(agent_table.BLOCK_BEGIN)
        end = text.index(agent_table.BLOCK_END) + len(agent_table.BLOCK_END)
        rest = (text[:start] + text[end:]).strip()
        if _has_content(rest):
            path.write_text(rest + "\n", encoding="utf-8")
            cleared.append((path, "edify block removed from"))
        else:
            # Nothing but our block was in it, so the file was ours after all. A
            # Cursor rule file keeps a frontmatter header outside the block, and a
            # file that is nothing but a header is a leftover, not somebody's work.
            path.unlink()
            cleared.append((path, "removed"))

    return cleared


def _has_content(text: str) -> bool:
    """Whether anything but a frontmatter header survived the block's removal."""
    lines = text.strip().splitlines()
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                lines = lines[i + 1:]
                break
    return any(line.strip() for line in lines)
