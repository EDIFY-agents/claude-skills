"""`edify init` — seven things, and then it stops.

Detect · extract · scrape conventions · select skills · seed the registry · write
`CLAUDE.md` · record what it installed. No interview, no constitution, no governance
level, and no archetype.

The one question it asks is which library entries to take, because those become
trusted instruction in every matching session and a person should see the list
first. With no terminal it asks nothing and installs the stack-matched set.

`init` on a repository that already has an AI instruction file **merges, never
overwrites**. Somebody wrote that file on purpose.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .. import (
    __version__, agents, anim, assets, governance, host, interview, library,
    skills as skills_index,
)
from ..agents import BLOCK_BEGIN, BLOCK_END, Instructions
from ..conventions import scrape
from ..context import Context
from ..detect import Stack, detect
from ..errors import TierRequired
from ..graph import extract
from ..licensing import projects, tier
from ..tsv import write_rows

# Kept under their old names because `setup` and anything else that reasoned about
# the block imported them from here first. The definition lives in `agents.py` now,
# with the rest of what a runtime reads.
CLAUDE_BEGIN = BLOCK_BEGIN
CLAUDE_END = BLOCK_END


def run(ctx: Context) -> int:
    root = ctx.layout.root
    out = ctx.out
    force = ctx.args.force

    # `setup` and `init new` print the wordmark themselves before their own opening
    # lines, and say so with `caller_opens` — otherwise it appears twice in eight
    # lines. Mirrors `caller_closes` at the bottom of this function.
    if not getattr(ctx.args, "caller_opens", False):
        anim.banner(out)

    out.note(f"repository root: {root}")

    # 1 · detect ---------------------------------------------------------
    stack = detect(root)
    if ctx.args.stack and ctx.args.stack != "auto":
        declared = [t.strip().lower() for t in ctx.args.stack.replace(",", " ").split() if t.strip()]
        stack.frameworks = sorted(set(stack.frameworks) | set(declared))
    out.line(f"stack     {', '.join(stack.tech) or 'nothing detected'}")
    out.line(f"manager   {stack.package_manager}   test runner {stack.test_runner}")

    # The fifth gate, and the only place it is enforced. `setup` and `init new`
    # both route through this function, so one call covers all three install paths
    # and there is no second copy to drift. Only a *new* project is ever refused:
    # a repository already in the ledger keeps installing, forever.
    #
    # Before the `.edify/` mkdir, not after: a refused install must leave nothing
    # behind, and an empty `.edify/` is worse than nothing — `require_installed`
    # would then say this repository is installed when it is not.
    verdict = projects.register(root, ctx.entitlement.project_cap)
    if verdict == projects.OVER_CAP:
        raise TierRequired(f"a {tier.ordinal(ctx.entitlement.project_cap + 1)} project")

    ctx.layout.edify.mkdir(parents=True, exist_ok=True)
    if verdict == projects.REGISTERED:
        used, cap = projects.slots(ctx.entitlement.project_cap)
        if cap is not None:
            out.note(f"projects  {used} of {cap} on the free plan · `edify license projects`")

    _write_stack(ctx, stack)

    # 2 · extract --------------------------------------------------------
    result = None
    if not ctx.args.no_graph:
        with anim.spinner(out, "reading every file, building the map"):
            result = extract.build(
                ctx.layout, backend=ctx.args.extractor, node_cap=ctx.entitlement.node_cap
            )
        out.line(f"graph     {result.nodes} nodes · {result.edges} edges · {result.files} files")
        if result.uncovered:
            out.line(
                "          not covered: "
                + ", ".join(sorted(result.uncovered))
                + " — these have no nodes, which is stated rather than guessed"
            )
        if result.truncated_at is not None:
            out.warn(f"graph truncated at {result.truncated_at:,} nodes (free plan)")
            out.note(f"          {tier.upsell()}")
    else:
        out.line("graph     skipped (--no-graph)")

    # 3 · conventions ----------------------------------------------------
    if force or not ctx.layout.conventions.exists():
        ctx.layout.conventions.write_text(scrape(root, stack), encoding="utf-8")
        out.line("conventions  scraped from config files · zero model calls")
    else:
        out.line("conventions  kept (already present)")

    # 4 · select skills --------------------------------------------------
    # No spinner around this one: `_install_skills` may stop and ask which entries
    # to take, and an animation painting over a question is a question nobody can
    # read. `Out.interactive` and `Out.animated` are both true at a terminal.
    installed, declined, unmatched = _install_skills(ctx, stack, force)
    detail = f"skills    {installed} installed"
    if declined:
        detail += f" · {declined} declined"
    detail += f" · {unmatched} in the library did not match this stack"
    out.line(detail)
    rows, invalid = skills_index.build_index(ctx.layout)
    out.line(f"index     {rows} lookup rows")
    for problem in invalid:
        out.warn(f"skipped in index — {problem}")

    # 5 · seed the registry ----------------------------------------------
    if force or not ctx.layout.mcp.exists():
        ctx.layout.mcp.write_text(assets.read("mcp", "default-registry.md"), encoding="utf-8")
        out.line("mcp       registry seeded with one entry: the documentation server")
    else:
        out.line("mcp       kept (already present)")

    # 6 · the methodology surface and CLAUDE.md --------------------------
    commands = _install_commands(ctx, force)
    out.line(f"commands  {commands} installed under .edify/commands/")
    _install_formats(ctx, force)

    targets = agents.resolve(
        getattr(ctx.args, "agents", ""),
        getattr(ctx.args, "host", "claude"),
        root=ctx.layout.root,
    )
    for path, action in _write_instructions(ctx, stack, targets):
        out.line(f"{path.ljust(31)} {action}")

    if targets:
        out.line(f"agents    {len(targets)} runtime(s) — each one's own commands and skills:")
    with anim.spinner(out, "mirroring skills into each runtime"):
        lines = _sync_host(ctx, targets)
    for kind, text in lines:
        (out.warn if kind == "warn" else out.line)(text)
    ctx.layout.specs.mkdir(parents=True, exist_ok=True)

    profile = getattr(ctx, "profile", None)
    if profile is not None and interview.write(ctx.layout.profile, profile):
        out.line("profile   .edify/profile.md — your answers, which every session reads")

    # 7 · record what was installed --------------------------------------
    ledger = governance.rebuild(ctx.layout)
    out.line(
        f"governance {len(ledger)} files recorded in .edify/governance.tsv"
        " — origin, licence, and hash for each"
    )

    out.data(
        {
            "root": str(root),
            "stack": stack.as_dict(),
            "graph": result.as_dict() if result else None,
            "skills_installed": installed,
            "skills_declined": declined,
            "index_rows": rows,
            "governed_files": len(ledger),
            "agents": [t.id for t in targets],
            "instructions": [i.path for i in agents.instruction_files(targets)],
            "profile": profile.as_dict() if profile is not None else None,
        }
    )
    # A caller that prints its own closing summary says so, so the person is not told
    # what to do next twice in eight lines.
    if not getattr(ctx.args, "caller_closes", False):
        out.line("")
        out.line("Next: /spec — write the spec before anything else.")
    return 0


# ---------------------------------------------------------------------------


def _write_stack(ctx: Context, stack: Stack) -> None:
    rows = [["language", lang] for lang in stack.languages]
    rows += [["framework", fw] for fw in stack.frameworks]
    rows += [
        ["package_manager", stack.package_manager],
        ["test_runner", stack.test_runner],
        ["edify_version", __version__],
    ]
    write_rows(ctx.layout.stack, rows, ("key", "value"))


def _install_skills(ctx: Context, stack: Stack, force: bool) -> tuple[int, int, int]:
    """Install the entries the person kept. Returns (installed, declined, unmatched).

    An entry already on disk that is declined this time is left alone rather than
    deleted — `init` merges. `edify skills list` shows what is there, and removing
    one is `rm`, which is a thing a person can see themselves doing.
    """
    source = assets.subtree("skills")
    ctx.layout.skills_dir.mkdir(parents=True, exist_ok=True)
    candidates = library.candidates_for_stack(source, stack.tech)
    spec = "all" if getattr(ctx.args, "yes", False) else getattr(ctx.args, "skills", "auto")
    chosen = library.choose(ctx.out, candidates, spec)
    chosen_paths = {c.path for c in chosen}

    for candidate in chosen:
        target = ctx.layout.skills_dir / candidate.path.name
        if target.exists() and not force:
            continue
        shutil.copyfile(candidate.path, target)

    total = len(list(source.glob("*.md")))
    return len(chosen), len(candidates) - len(chosen), max(0, total - len(candidates))


def _install_commands(ctx: Context, force: bool) -> int:
    source = assets.subtree("commands")
    ctx.layout.commands_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted(source.glob("*.md")):
        target = ctx.layout.commands_dir / path.name
        if not target.exists() or force:
            shutil.copyfile(path, target)
        count += 1
    return count


def _install_formats(ctx: Context, force: bool) -> None:
    source = assets.subtree("formats")
    ctx.layout.formats_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob("*.md")):
        target = ctx.layout.formats_dir / path.name
        if not target.exists() or force:
            shutil.copyfile(path, target)


def _sync_host(ctx: Context, targets: list[agents.Target]) -> list[tuple[str, str]]:
    """Each runtime's own directories: one pointer per command, skill, and agent.

    A library entry under `.edify/skills/` is installed as far as `edify skills list`
    is concerned and invisible to the runtime the person is typing into, which
    discovers skills at `.claude/skills/<name>/SKILL.md` and subagents at
    `.claude/agents/<name>.md`. `host.sync_target` writes that mirror and `kind`
    decides which of the two an entry gets; `host.stale` reports the pointers whose
    entry has since been removed or changed kind, because a capability the runtime
    offers and then cannot read is worse than one it never knew about.

    It **returns** its lines rather than printing them, because it runs inside the
    spinner and a `print` racing an animation is two half-written lines. The caller
    emits them once the region is erased.
    """
    lines: list[tuple[str, str]] = []
    if not targets:
        return lines
    skipped: list = []
    for target in targets:
        written = host.sync_target(ctx.layout, target)
        if not written:
            continue
        counts: dict[str, int] = {}
        for item in written:
            counts[item.kind] = counts.get(item.kind, 0) + (1 if item.action != "skipped" else 0)
        skipped += [item for item in written if item.action == "skipped"]
        parts = [f"{counts.get('command', 0)} commands"]
        if target.skills:
            parts.append(f"{counts.get('skill', 0)} skills")
        if target.agents:
            parts.append(f"{counts.get('agent', 0)} agents")
        lines.append(("line", f"  {target.id.ljust(9)} {' · '.join(parts)}  ({target.label})"))

    for item in skipped:
        lines.append(("warn", f"kept your own file at {ctx.layout.rel(item.path)} — not an edify pointer"))
    for path in host.stale(ctx.layout):
        lines.append(
            ("warn", f"{ctx.layout.rel(path)} points at an entry that is no longer installed — safe to delete")
        )
    return lines


def _write_instructions(ctx: Context, stack: Stack, targets: list[agents.Target]) -> list[tuple[str, str]]:
    """One instruction file per runtime, deduplicated. `(path, what happened)` each.

    `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` and the rest all carry the same block: the
    same commands resolve, the same graph answers the same questions, and a team with
    two tools open should not be running two methodologies. Only the wrapper differs.
    """
    body = _instruction_body(ctx, stack)
    out: list[tuple[str, str]] = []
    for item in agents.instruction_files(targets):
        path = ctx.layout.root / item.path
        out.append((item.path, _merge_block(path, body, item)))
    return out


def _merge_block(path: Path, body: str, item: Instructions) -> str:
    """Fifteen lines. Merged into an existing file, never over it."""
    block = f"{BLOCK_BEGIN}\n{body}\n{BLOCK_END}\n"

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_header(item) + block, encoding="utf-8")
        return "written"

    existing = path.read_text(encoding="utf-8")
    if BLOCK_BEGIN in existing and BLOCK_END in existing:
        start = existing.index(BLOCK_BEGIN)
        end = existing.index(BLOCK_END) + len(BLOCK_END)
        updated = existing[:start] + block.rstrip("\n") + existing[end:]
        path.write_text(updated, encoding="utf-8")
        return "updated (edify block replaced)"

    separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    path.write_text(existing + separator + "\n" + block, encoding="utf-8")
    return "merged (existing content kept above)"


def _header(item: Instructions) -> str:
    """What has to sit outside the block for this runtime to read the file at all.

    Cursor decides whether a rule applies from its frontmatter, so a `.mdc` file
    without `alwaysApply` is a file Cursor has and never loads. It goes outside the
    markers because it belongs to the file rather than to the block, and a re-run that
    replaces the block leaves it where it is.
    """
    if item.style == "mdc":
        return (
            "---\n"
            "description: EDIFY — the harness this repository is built with\n"
            "alwaysApply: true\n"
            "---\n\n"
        )
    return ""


def _instruction_body(ctx: Context, stack: Stack) -> str:
    template = assets.read("templates", "CLAUDE.md")
    languages = ", ".join(stack.languages) or "not detected"
    frameworks = ", ".join(stack.frameworks)
    stack_line = languages + (f" · {frameworks}" if frameworks else "")
    body = (
        template.replace("{{repo}}", ctx.layout.root.name)
        .replace("{{stack}}", stack_line)
        .replace("{{test}}", stack.test_runner)
        .strip()
    )
    # The interview's answers, in the two lines that are worth spending context on
    # every session. Everything else it asked stays in `.edify/profile.md`.
    profile = getattr(ctx, "profile", None)
    extra = interview.block_lines(profile) if profile is not None else []
    return body + ("\n\n" + "\n".join(extra) if extra else "")
