"""Every agent runtime EDIFY installs into, and where each one looks.

`.edify/` is canonical. A runtime does not read it — each one discovers its own
instructions and its own commands somewhere else, and they do not agree on a single
path between them. Claude Code reads `CLAUDE.md` and `.claude/`; Codex and Cursor read
`AGENTS.md`; Gemini reads `GEMINI.md`; Copilot reads `.github/copilot-instructions.md`.
An install that writes only `CLAUDE.md` is an install that is invisible to five of the
six tools a team actually has open.

So this module is the table, and it is only a table: paths, suffixes, and the shape
each runtime expects. Nothing here reads or writes a file — `host.py` does that, once,
for whichever targets were chosen. Adding a runtime is adding a row, not a code path.

Two things every row shares, and they are the reason the mirror is safe to re-run:

**Everything generated carries `MARKER_TEXT`.** That is what makes a file ours to
replace and, just as importantly, what makes a file somebody wrote by hand not ours.
It appears as an HTML comment in Markdown and a `#` comment in TOML, so the check is
for the text and not for the punctuation around it.

**Instruction files are merged, never overwritten.** EDIFY owns the block between
`BLOCK_BEGIN` and `BLOCK_END` in a file that belongs to the repository. Somebody wrote
the rest of `AGENTS.md` on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass

# The block EDIFY owns inside somebody else's instruction file.
BLOCK_BEGIN = "<!-- edify:begin -->"
BLOCK_END = "<!-- edify:end -->"

# The text every generated pointer carries. `written_by_edify` looks for this and not
# for a whole comment, because a TOML command file cannot hold an HTML one.
MARKER_TEXT = "edify:generated"
MARKER_MD = f"<!-- {MARKER_TEXT} — this file is a pointer; edit the file it names -->"
MARKER_TOML = f"# {MARKER_TEXT} — this file is a pointer; edit the file it names"

# The shape the command pointers had before there was a marker. A repository that ran
# an earlier `init` has six of them, and without this they would all be treated as
# somebody's own files and never brought up to date.
LEGACY_MARKERS = ("That file is the contract; this one only points at it.",)


@dataclass(frozen=True)
class Instructions:
    """One instruction file a runtime reads at the start of every session.

    `style` is the wrapper the runtime needs around the block, not the block itself:
    `plain` is Markdown as written, `mdc` is Cursor's rule format, which is Markdown
    with a frontmatter header that decides when the rule applies.
    """

    path: str
    style: str = "plain"  # plain | mdc


@dataclass(frozen=True)
class Target:
    """One agent runtime: what it reads, and where it discovers commands."""

    id: str
    label: str
    instructions: tuple[Instructions, ...]
    commands: str = ""  # directory for one command pointer per EDIFY command
    command_suffix: str = ".md"
    command_format: str = "markdown"  # markdown | toml
    skills: str = ""  # directory holding one directory per skill
    skill_file: str = "SKILL.md"
    agents: str = ""  # directory holding one flat file per subagent
    notes: str = ""

    @property
    def instruction_paths(self) -> tuple[str, ...]:
        return tuple(i.path for i in self.instructions)

    def trees(self) -> tuple[tuple[str, str], ...]:
        """`(directory, glob)` for every family of generated pointers this row has.

        Everything that has to walk a runtime's own tree — the governance scan, the
        clearing `init new` does first, the staleness check — walks it through here,
        so a row added above is covered by all three without touching any of them.
        """
        out: list[tuple[str, str]] = []
        if self.commands:
            out.append((self.commands, f"*{self.command_suffix}"))
        if self.skills:
            out.append((self.skills, f"*/{self.skill_file}"))
        if self.agents:
            out.append((self.agents, "*.md"))
        return tuple(out)


# -- the table ---------------------------------------------------------------
# Ordered as a person would read them: the runtime EDIFY was built against first,
# then the ones that share `AGENTS.md`, then the rest, then the fallback that is
# nothing but `AGENTS.md` for a tool nobody has written a row for yet.

TARGETS: tuple[Target, ...] = (
    Target(
        id="claude",
        label="Claude Code",
        instructions=(Instructions("CLAUDE.md"),),
        commands=".claude/commands",
        skills=".claude/skills",
        agents=".claude/agents",
        notes="commands, skills, and spawnable subagents",
    ),
    Target(
        id="codex",
        label="OpenAI Codex",
        instructions=(Instructions("AGENTS.md"),),
        commands=".codex/prompts",
        notes="AGENTS.md and saved prompts",
    ),
    Target(
        id="cursor",
        label="Cursor",
        instructions=(Instructions("AGENTS.md"), Instructions(".cursor/rules/edify.mdc", style="mdc")),
        commands=".cursor/commands",
        notes="AGENTS.md, an always-on rule, and slash commands",
    ),
    Target(
        id="gemini",
        label="Gemini CLI",
        instructions=(Instructions("GEMINI.md"),),
        commands=".gemini/commands",
        command_suffix=".toml",
        command_format="toml",
        notes="GEMINI.md and TOML custom commands",
    ),
    Target(
        id="copilot",
        label="GitHub Copilot",
        instructions=(Instructions(".github/copilot-instructions.md"),),
        commands=".github/prompts",
        command_suffix=".prompt.md",
        notes="repository instructions and prompt files",
    ),
    Target(
        id="windsurf",
        label="Windsurf",
        instructions=(Instructions(".windsurf/rules/edify.md"),),
        commands=".windsurf/workflows",
        notes="a repository rule and workflows",
    ),
    Target(
        id="agents",
        label="any other agent",
        instructions=(Instructions("AGENTS.md"),),
        notes="AGENTS.md only — the file the rest of them read",
    ),
)

BY_ID = {t.id: t for t in TARGETS}

# What `edify init new` installs when nobody says otherwise. Every row: the whole
# point of the command is a folder that works in whichever tool is opened next.
ALL_IDS = tuple(t.id for t in TARGETS)


def present(target: Target, root) -> bool:
    """Whether this runtime is already set up in this folder.

    The test is a directory the runtime keeps its own commands in, never an
    instruction file. `AGENTS.md` is three rows' answer and is just as likely to have
    been written by somebody who has never run EDIFY, and treating it as evidence
    would have `init` quietly start writing into `.codex/` and `.cursor/` in a
    repository that asked for neither.
    """
    return any((root / directory).is_dir() for directory, _ in target.trees())


def present_targets(root) -> list[Target]:
    return [t for t in TARGETS if present(t, root)]


def resolve(spec: str, host: str = "claude", root=None) -> list[Target]:
    """Which runtimes to write for.

        all | *          every row in the table
        none             nothing — `.edify/` only
        <ids…>           exactly these, comma- or space-separated
        "" (unset)       whichever runtimes are already set up here, and `--host`
                         when none are — which is what `init` has always done in a
                         folder nobody has run `init new` in

    That last rule is what keeps a folder honest. `init new` writes six instruction
    files; a plain `edify init` a week later must bring all six up to date, because
    five stale ones and one current one is worse than the state before either ran.

    An unknown id is not silently dropped: a person who typed `--agents cursur` asked
    for Cursor and would otherwise be told everything worked.
    """
    from .errors import EdifyError

    wanted = (spec or "").strip().lower()
    if not wanted:
        if host != "none" and root is not None:
            already = present_targets(root)
            if already:
                return already
        wanted = "none" if host == "none" else host
    if wanted in ("all", "*", "every"):
        return list(TARGETS)
    if wanted in ("none", "-"):
        return []

    picked: list[Target] = []
    unknown: list[str] = []
    for token in wanted.replace(",", " ").split():
        target = BY_ID.get(token)
        if target is None:
            unknown.append(token)
        elif target not in picked:
            picked.append(target)
    if unknown:
        raise EdifyError(
            f"no agent runtime called `{unknown[0]}`",
            hint=f"known ids: {', '.join(ALL_IDS)} — or `all`, or `none`",
        )
    return picked


def instruction_files(targets: list[Target]) -> list[Instructions]:
    """Every instruction file these targets read, deduplicated and in table order.

    `AGENTS.md` is three rows' answer and one file on disk. Writing it once is not an
    optimisation — writing it three times would merge EDIFY's block into a file that
    already had EDIFY's block, twice.
    """
    seen: dict[str, Instructions] = {}
    for target in targets:
        for item in target.instructions:
            seen.setdefault(item.path, item)
    return list(seen.values())


def all_trees() -> tuple[tuple[str, str], ...]:
    """Every generated-pointer directory in the table, for the scans that walk them all.

    Governance and clearing are about what is *on disk*, not about what was chosen
    this run: a folder set up for Cursor last month and for Claude today still has
    Cursor's pointers in it, and both of them are EDIFY's.
    """
    out: list[tuple[str, str]] = []
    for target in TARGETS:
        for tree in target.trees():
            if tree not in out:
                out.append(tree)
    return tuple(out)


def all_instruction_paths() -> tuple[str, ...]:
    seen: list[str] = []
    for target in TARGETS:
        for item in target.instructions:
            if item.path not in seen:
                seen.append(item.path)
    return tuple(seen)
