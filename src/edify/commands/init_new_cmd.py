"""`edify init new [PATH]` — a folder, from nothing, for whichever agent is opened.

Three commands now install, and they differ in what they assume:

    edify init          a repository already under way. Finds its root by walking up,
                        keeps every file already there, merges into an instruction
                        file somebody else wrote. One runtime: Claude Code.
    edify setup PATH    the same install, with the root pinned to one folder so a new
                        directory inside a checkout does not install into its parent.
    edify init new      a folder set up from zero. Root pinned, EDIFY's own surface
                        cleared first, every library entry installed, and an
                        instruction file written for **every** agent runtime in the
                        table — CLAUDE.md, AGENTS.md, GEMINI.md, the Copilot file, the
                        Cursor rule — each with the same block in it.

And one thing none of the others do: it asks. Detection reads `package.json` and finds
the test runner. It cannot find out that this is a rewrite of something already in
production, that the person typing is the only one who knows the domain, or that
nothing may touch the payments module without a migration plan. Those facts decide how
an agent should behave in this repository and there is exactly one place to get them,
so `init new` asks eight short questions before it installs anything, writes the
answers to `.edify/profile.md`, and points every instruction file at that file.

The questions are asked **first**, because two of them change what gets installed —
which runtimes, and what detection missed. An interview after the install would be a
survey.

With no terminal — CI, a pipe, a model calling the binary — nothing is asked, no
profile is written, and the install is the full one. A question is never load-bearing.
"""

from __future__ import annotations

from pathlib import Path

from .. import agents, anim, host, interview
from ..context import Context
from ..errors import EdifyError
from ..paths import Layout
from . import init_cmd


def run(ctx: Context) -> int:
    root = Path(getattr(ctx.args, "path", None) or ".").expanduser()
    if root.exists() and not root.is_dir():
        raise EdifyError(f"{root} is a file, not a folder")

    created = not root.exists()
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()

    # The root is pinned, not searched. `find_root` walks upward, so `mkdir service &&
    # cd service && edify init` inside an existing checkout installs into the parent —
    # silently, into the same `.edify/` the outer repository already has.
    layout = Layout(root)
    out = ctx.out

    # Once, above the first line, and `init_cmd` is told not to print a second.
    anim.banner(out)
    ctx.args.caller_opens = True

    out.line(f"init new  {root}{' (created)' if created else ''}")
    out.line("          a folder set up from zero, for every agent that reads a repository")

    # 1 · ask, before anything is written ---------------------------------
    profile = _interview(ctx, layout)

    # 2 · what the answers changed ----------------------------------------
    ctx.args.agents = interview.agents_spec(profile, getattr(ctx.args, "agents", "all") or "all")
    extra = interview.extra_tech(profile)
    if extra:
        declared = getattr(ctx.args, "stack", "auto")
        base = "" if declared in ("auto", "", None) else declared
        ctx.args.stack = " ".join(filter(None, [base, *extra]))

    chosen = agents.resolve(ctx.args.agents, getattr(ctx.args, "host", "claude"), root=root)
    out.line("")
    if chosen:
        out.line("installing for:")
        for target in chosen:
            out.line(f"  {target.id.ljust(9)} {target.label.ljust(22)} {target.notes}")
    else:
        out.line("installing for: nothing but .edify/ — no runtime files were asked for")

    # 3 · clear EDIFY's own surface ---------------------------------------
    # `init new` means everything, again, properly. `--keep` is for re-running it over
    # a folder whose pointers are fine and whose answers have changed.
    if not getattr(ctx.args, "keep", False):
        cleared = host.clear(layout)
        out.line("")
        out.line(f"fresh     {len(cleared)} edify-owned path(s) cleared before installing")
        for path, action in cleared:
            out.note(f"  {action} {layout.rel(path)}")

    # 4 · install ----------------------------------------------------------
    ctx.args.force = True  # `new` means install everything, not merge into it
    ctx.args.caller_closes = True  # the closing summary below is this command's
    if getattr(ctx.args, "skills", "all") in ("auto", "", None):
        ctx.args.skills = "all"

    scoped = Context(args=ctx.args, layout=layout, out=out, profile=profile)
    out.line("")
    code = init_cmd.run(scoped)
    if code != 0:
        return code

    _closing(ctx, layout, chosen, profile)
    return 0


# ---------------------------------------------------------------------------


def _interview(ctx: Context, layout: Layout) -> interview.Profile:
    """The questions, with a re-run offering last time's answers as the defaults.

    `--yes` and `--no-interview` both skip them, and so does having nobody to ask.
    They are not the same thing said twice: `--yes` is "take every default", which is
    what a script means, and `--no-interview` is "install, and I will write the profile
    myself", which is what somebody with a profile already in hand means.
    """
    if getattr(ctx.args, "yes", False) or getattr(ctx.args, "no_interview", False):
        return interview.load(layout.profile)

    previous = interview.load(layout.profile)
    defaults = {k: v for k, v in previous.filled.items()}
    defaults.setdefault("name", interview.default_name())
    defaults.setdefault("agents", getattr(ctx.args, "agents", "all") or "all")

    profile = interview.ask(ctx.out, defaults=defaults)
    if not profile.asked and previous.filled:
        # No terminal, but a previous run's answers are on disk. Keeping them is the
        # only behaviour that does not quietly throw away what somebody typed.
        return previous
    return profile


def _closing(ctx: Context, layout: Layout, chosen: list[agents.Target], profile: interview.Profile) -> None:
    out = ctx.out
    files = [item.path for item in agents.instruction_files(chosen)]
    width = max([len(p) for p in [*files, ".edify/profile.md", ".edify/"]] or [10])

    out.line("")
    out.line("what is on disk now")
    out.line(f"  {'.edify/'.ljust(width)}  the harness: graph, skills, commands, formats, registry, ledger")
    for path in files:
        out.line(f"  {path.ljust(width)}  read at the start of every session")
    if profile.filled:
        out.line(f"  {'.edify/profile.md'.ljust(width)}  your answers — edit them whenever they change")
    out.line("")
    out.line("Next: /spec — write the spec before anything else.")
