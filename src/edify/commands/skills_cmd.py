"""`edify skills` — what is installed, and which file a spawn loads.

`resolve` is the lookup `/build` performs before every spawn. It prints one line.

There is deliberately no `skills install <url>` and no registry browsing. Anything
arriving from outside goes through `/harvest` and a human in EDIFY's own
repository: an ad-hoc import is a stranger's text loaded as trusted instruction
into every matching session in a customer's codebase.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .. import governance, host, skills as skills_index
from ..context import Context
from ..errors import EdifyError
from ..formats import skill as skill_format
from ..tsv import read_rows


def list_(ctx: Context) -> int:
    ctx.layout.require_installed()
    entries = skill_format.load_all(ctx.layout.skills_dir, ctx.layout.root)
    if not entries:
        ctx.out.line("no skills installed")
        return 0

    rows = []
    for skill in entries:
        rows.append(
            [
                skill.name or "(invalid)",
                skill.role or "-",
                " ".join(skill.phases) or "-",
                " ".join(skill.tech) or "-",
                skill.provenance or "-",
                skill.license or "-",
                f"{skill.body_lines}/{skill.budget}",
            ]
        )
    ctx.out.data(
        [
            {
                "name": s.name,
                "role": s.role,
                "phases": s.phases,
                "tech": s.tech,
                "provenance": s.provenance,
                "license": s.license,
                "lines": s.body_lines,
                "budget": s.budget,
                "path": s.rel,
            }
            for s in entries
        ]
    )
    ctx.out.table(["name", "role", "phase", "tech", "provenance", "license", "lines"], rows)
    return 0


def resolve(ctx: Context) -> int:
    ctx.layout.require_installed()
    tech = ctx.args.tech or _stack_tech(ctx)
    entry = skills_index.resolve(ctx.layout, ctx.args.role, ctx.args.phase, tech)
    ctx.out.data({"role": entry.role, "phase": entry.phase, "tech": entry.tech, "name": entry.name, "path": entry.path})
    ctx.out.line(entry.path)
    return 0


def index(ctx: Context) -> int:
    ctx.layout.require_installed()
    rows, skipped = skills_index.build_index(ctx.layout)
    ctx.out.data({"rows": rows, "skipped": skipped})
    ctx.out.line(f"{rows} rows")
    for problem in skipped:
        ctx.out.warn(f"skipped — {problem}")
    return 0


def sync(ctx: Context) -> int:
    """Mirror the installed library into each agent runtime's own directories.

    `.edify/skills/<name>.md` is where an entry lives and `edify skills resolve` is
    how a build spawn finds it. Neither is where Claude Code looks: it discovers
    skills at `.claude/skills/<name>/SKILL.md`, one directory each, and subagents at
    `.claude/agents/<name>.md`, one flat file each. `kind` decides which an entry gets.
    Until that mirror exists an installed entry is invisible to the runtime the person
    is typing into, which is the gap this closes.

    Which runtimes, with no `--agents`, is whichever ones are already set up in this
    folder — a folder `init new` prepared for six of them gets all six updated here.

    Run by `init`, `upgrade`, `setup`, and the last step of an admission. Standalone
    for the case where a skill file was added or removed by hand.
    """
    ctx.layout.require_installed()
    written = host.sync(
        ctx.layout,
        host=getattr(ctx.args, "host", "claude"),
        agents=getattr(ctx.args, "agents", ""),
    )
    leftovers = host.stale(ctx.layout)
    # These are governed files, so the ledger moves with them. Without this the next
    # `governance verify` reports every pointer this command just wrote as unrecorded.
    governance.rebuild(ctx.layout)

    ctx.out.data(
        {
            "written": [
                {"path": ctx.layout.rel(w.path), "kind": w.kind, "name": w.name, "action": w.action}
                for w in written
            ],
            "stale": [ctx.layout.rel(p) for p in leftovers],
        }
    )
    if not written:
        ctx.out.line("nothing to mirror")
        return 0

    rows = [[ctx.layout.rel(w.path), w.kind, w.action] for w in written]
    ctx.out.table(["path", "kind", "action"], rows)
    changed = sum(1 for w in written if w.action == "written")
    ctx.out.line("")
    ctx.out.line(f"{changed} written · {len(written) - changed} already current")
    for item in written:
        if item.action == "skipped":
            ctx.out.warn(f"kept your own file at {ctx.layout.rel(item.path)} — not an edify pointer")
    for path in leftovers:
        ctx.out.warn(f"{ctx.layout.rel(path)} points at an entry that is no longer installed — safe to delete")
    return 0


def add(ctx: Context) -> int:
    """Install one entry from the shipped library, or a local file.

    Local only, by design. A path on disk is something a person can read before it
    becomes trusted context; a URL is not.
    """
    ctx.layout.require_installed()
    source = Path(ctx.args.path).expanduser()
    if not source.is_file():
        raise EdifyError(f"{source} is not a file")
    if source.suffix != ".md":
        raise EdifyError("a skill entry is a markdown file with flat YAML frontmatter")

    parsed = skill_format.parse(source, source.name)
    problems = [p for p in skill_format.validate(parsed) if p[0] != "skill-over-budget"]
    if problems:
        for _, message, _line in problems:
            ctx.out.error(message)
        raise EdifyError("not installed — the frontmatter is invalid")

    target = ctx.layout.skills_dir / source.name
    ctx.layout.skills_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    rows, _ = skills_index.build_index(ctx.layout)
    host.sync(ctx.layout)
    governance.rebuild(ctx.layout)
    ctx.out.line(f"installed {parsed.name} → {ctx.layout.rel(target)} · index now {rows} rows")
    mirror = (
        f".claude/agents/{parsed.name}.md"
        if parsed.kind == "agent"
        else f".claude/skills/{parsed.name}/SKILL.md"
    )
    ctx.out.note(f"mirrored to {mirror}")
    return 0


def _stack_tech(ctx: Context) -> str:
    """The repository's own stack, so `resolve` needs only a role and a phase."""
    values: list[str] = []
    for row in read_rows(ctx.layout.stack):
        if len(row) >= 2 and row[0] in ("language", "framework"):
            values.append(row[1])
    return " ".join(values)
