"""`edify doctor` — does the install work here.

Five checks and a green/amber/red line, where amber means "this works but degraded,
and here is which part". Not the twelve-probe apparatus of the previous design:
there are no hooks to probe, no runtime surface to pin, and no compiled targets to
hash.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from .. import __version__, assets, governance, skills as skills_index
from ..commands.init_cmd import _instruction_body
from ..context import Context
from ..detect import detect
from ..formats import skill as skill_format
from ..graph.langs import ctags

GREEN, AMBER, RED = "ok", "degraded", "broken"


@dataclass
class Check:
    name: str
    state: str
    detail: str


def run(ctx: Context) -> int:
    checks = [
        _install(ctx),
        _extractor(ctx),
        _graph(ctx),
        _index(ctx),
        _governance(ctx),
        _claude(ctx),
        _license(ctx),
    ]
    ctx.out.data([c.__dict__ for c in checks])

    for check in checks:
        colour = {GREEN: "green", AMBER: "yellow", RED: "red"}[check.state]
        ctx.out.line(f"{ctx.out.c(check.state.ljust(9), colour)} {check.name.ljust(12)} {check.detail}")

    ctx.out.line("")
    if any(c.state == RED for c in checks):
        ctx.out.line(ctx.out.c("red — something here does not work", "red"))
        return 1
    if any(c.state == AMBER for c in checks):
        ctx.out.line(ctx.out.c("amber — this works, degraded, in the places named above", "yellow"))
        return 0
    ctx.out.line(ctx.out.c("green", "green"))
    return 0


# ---------------------------------------------------------------------------


def _install(ctx: Context) -> Check:
    if not ctx.layout.installed():
        return Check("install", RED, f"no .edify/ under {ctx.layout.root} — run `edify init`")
    try:
        root = assets.asset_root()
    except Exception as exc:  # the methodology tree is missing from the install
        return Check("install", RED, str(exc))
    count = len(list((root / "skills").glob("*.md")))
    return Check("install", GREEN, f"edify {__version__} · library of {count} skill entries")


def _extractor(ctx: Context) -> Check:
    external = ctags.available()
    if external:
        return Check("extractor", GREEN, f"{ctags.version()} · syntax-tree parsing")
    return Check(
        "extractor",
        AMBER,
        "built-in backend: Python is parsed exactly, everything else is scanned"
        " — install Universal Ctags for parse-grade precision on the rest",
    )


def _graph(ctx: Context) -> Check:
    if not ctx.store.exists():
        return Check("graph", RED, "no graph on disk — run `edify graph build`")
    problems = ctx.store.verify_checksums()
    if problems:
        return Check("graph", RED, problems[0])

    meta = ctx.store.meta
    detail = f"{meta.get('nodes', '?')} nodes · {meta.get('edges', '?')} edges"
    uncovered = meta.get("languages_uncovered", "-")
    if uncovered not in ("-", ""):
        detail += f" · no nodes for {uncovered}"
    if meta.get("truncated_at"):
        return Check("graph", AMBER, detail + f" · truncated at {meta['truncated_at']} (free plan)")

    head = _head(ctx)
    recorded = meta.get("commit", "-")
    if head and recorded not in ("-", "") and head != recorded:
        return Check("graph", AMBER, detail + " · built from a different commit — re-run `edify graph build`")
    if uncovered not in ("-", ""):
        return Check("graph", AMBER, detail)
    return Check("graph", GREEN, detail)


def _index(ctx: Context) -> Check:
    entries = skill_format.load_all(ctx.layout.skills_dir, ctx.layout.root)
    if not entries:
        return Check("skills", RED, "no skills installed — run `edify init`")
    if not ctx.layout.skills_index.is_file():
        return Check("skills", RED, "no index.tsv — run `edify skills index`")

    roles = {s.role for s in entries if s.role}
    unresolvable = []
    for role in sorted(roles):
        try:
            skills_index.resolve(ctx.layout, role, "3")
        except Exception:
            unresolvable.append(role)
    if unresolvable:
        return Check("skills", RED, "these roles do not resolve: " + ", ".join(unresolvable))

    over = [s.rel for s in entries if s.over_budget]
    if over:
        return Check("skills", AMBER, f"{len(entries)} entries · over budget: {', '.join(over[:3])}")
    return Check("skills", GREEN, f"{len(entries)} entries · every role resolves")


def _governance(ctx: Context) -> Check:
    """Amber, never red. A ledger that disagrees with the disk is information."""
    if not ctx.layout.governance.is_file():
        return Check("governance", AMBER, "no ledger — run `edify governance rebuild`")
    try:
        recorded = governance.load(ctx.layout)
        problems = governance.verify(ctx.layout)
    except Exception as exc:  # an unreadable ledger is a real fault, not a nuance
        return Check("governance", RED, str(exc))

    serious = [p for p in problems if p.serious]
    if serious:
        first = serious[0]
        return Check(
            "governance",
            AMBER,
            f"{len(recorded)} files recorded · {len(serious)} differ — {first.path} is {first.state}",
        )
    detail = f"{len(recorded)} files recorded · each with an origin, a licence, and a hash"
    edited = len(problems) - len(serious)
    if edited:
        detail += f" · {edited} edited by this repository, which is allowed"
    return Check("governance", GREEN, detail)


def _claude(ctx: Context) -> Check:
    """Every instruction file on disk, not only Claude's.

    A folder set up by `edify init new` has five or six of them and they all carry the
    same block, so one of them going stale — a command renamed, the graph section
    edited away — is the same failure whichever file it happened in. The check is named
    for `CLAUDE.md` because that is the one every install has.
    """
    present = [p for p in ctx.layout.instruction_files() if p.is_file()]
    if not present:
        return Check("CLAUDE.md", RED, "missing — run `edify init`")

    expected = _instruction_body(ctx, detect(ctx.layout.root))
    wanted = [line for line in expected.splitlines() if line.strip().startswith("/")]
    for path in present:
        rel = ctx.layout.rel(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        if ".edify/graph/" not in text:
            return Check("CLAUDE.md", AMBER, f"{rel} does not point at the graph, which is the one thing it is for")
        if [line for line in wanted if line not in text]:
            return Check("CLAUDE.md", AMBER, f"{rel} does not list every command `edify init` would write")

    named = ", ".join(ctx.layout.rel(p) for p in present)
    return Check("CLAUDE.md", GREEN, f"{len(present)} instruction file(s) · {named} · each points at the graph")


def _license(ctx: Context) -> Check:
    ent = ctx.entitlement
    if ent.problem:
        return Check("license", AMBER, f"running free — {ent.problem}")
    if ent.paid and ent.license and ent.license.days_left in range(0, 15):
        return Check("license", AMBER, f"{ent.plan} · expires in {ent.license.days_left} days")

    # The project ledger, because "why was my install refused?" should be one line
    # in `doctor` rather than an investigation. Reading it is free and local.
    cap = ent.project_cap
    if cap is None:
        return Check("license", GREEN, f"{ent.plan} · projects unlimited")
    try:
        from ..licensing import projects
        used = len(projects.known())
    except OSError:
        return Check("license", GREEN, f"{ent.plan}")
    detail = f"{ent.plan} · {used} of {cap} projects"
    if used >= cap:
        return Check("license", AMBER, f"{detail} — the next new one needs the pro plan")
    return Check("license", GREEN, detail)


def _head(ctx: Context) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ctx.layout.root),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""
