"""The `edify` binary.

A pure function over files. Every command reads files and writes files; none holds
state, opens a socket, or calls out to a network except `edify upgrade`, which
pulls a skill library, and `edify self update`, which builds a wheel and may fetch
its build backend. Both say so in their own docstrings, and both have an offline
mode that fails cleanly rather than reaching out.

Deterministic where it decides. `edify` may be invoked by a model; no `edify`
command lets a model decide what is installed, indexed, or resolved.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from . import agents as agent_table
from .context import build_context
from .errors import EdifyError

USAGE = """edify — three documents and a map

lifecycle
  edify init new [PATH]               a folder from zero, for every agent — asks first
  edify setup [PATH] [--fresh]        install everything into one folder, root pinned there
  edify init [--yes] [--skills ...]   detect · extract · choose skills · write CLAUDE.md
  edify check [--fix] [--exit-code]   format check over specs, tasks, and skill files
  edify upgrade                       pull a newer skill library and re-index

graph
  edify graph build                   full extraction
  edify graph update <dir>...         one or more directories — runs after each phase
  edify graph where <name>            file:line and signature
  edify graph dependents <symbol>     everything that breaks if this changes
  edify graph references <name>       who calls or imports this
  edify graph defines <file>          what this file exports
  edify graph overlap <a> <b>         do these file sets intersect, dependents included
  edify graph stat                    what is in the map

skills
  edify skills list                   what is installed, with provenance and license
  edify skills resolve <role> <phase> [tech]
  edify skills index                  re-sort the lookup table
  edify skills add <path>             install one entry
  edify skills sync                   mirror the library into .claude/ — skills/<name>/SKILL.md,
                                      agents/<name>.md by `kind`

harvest (EDIFY's own repository only)
  edify harvest pick [--source N]     which source to draw from, and what not to gather again
  edify harvest stage --url ... --name ... --content PATH
  edify harvest screen [ID...]        licence · duplicate · injection, fail-closed
  edify harvest propose ID --file PATH --case "..."
  edify harvest admit ID --by NAME    the human door — never unattended
  edify harvest reject ID --reason "..."
  edify harvest status                the ledger, and the yield rows for sources.md

governance
  edify governance list               every file edify installed, and where it came from
  edify governance verify             the ledger against what is on disk
  edify governance rebuild            re-baseline after a deliberate change

servers
  edify mcp list                      the registry, with what each entry is scoped to
  edify mcp check                     each server responds and its version matches the pin
  edify mcp for <role> <phase>        what a spawn in this position would load

ship
  edify doctor                        does the install work here
  edify self where                    which edify is this, and where did it come from
  edify self update [--from PATH]     put an edited checkout behind the `edify` binary
  edify license status|activate|deactivate
  edify license buy [--seats N]       the pro plan, and where to pay for it
  edify license projects [forget ...] which repositories are using a free slot
  edify feedback [list|show|off|on]   four questions, written to a file on this machine
  edify version
"""


# Read from the table rather than typed out, so help text and behaviour cannot drift.
# `agents` is pure data — no graph, no filesystem — so importing it here costs nothing.
_AGENT_IDS = ", ".join(agent_table.ALL_IDS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="edify",
        description="A harness that makes an AI coding agent work reliably on large codebases.",
        add_help=True,
    )
    parser.add_argument("--repo", metavar="PATH", help="the repository root (default: search upward from cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output on stdout")
    parser.add_argument("--no-color", action="store_true", help="never emit ANSI colour")
    parser.add_argument("--quiet", "-q", action="store_true", help="answers only, no notes")
    parser.add_argument("--no-anim", action="store_true",
                        help="no banner and no animation; static lines instead")
    parser.add_argument("--version", action="version", version=f"edify {__version__}")

    sub = parser.add_subparsers(dest="command")

    # -- lifecycle -------------------------------------------------------
    # `setup` takes the same flags as `init` because it *is* `init` with the root
    # pinned to one folder and force on. Anything accepted by one is accepted by both.
    p_setup = sub.add_parser("setup", help="install everything into one folder, root pinned there")
    p_setup.add_argument("path", nargs="?", default=".", help="the folder to install into (created if missing)")
    p_setup.add_argument("--fresh", action="store_true",
                         help="remove edify's own files first — .edify/, its host pointers, its CLAUDE.md block")
    p_setup.add_argument("--stack", default="auto", help="`auto`, or explicit tech ids to add to what was detected")
    p_setup.add_argument("--no-graph", action="store_true", help="skip extraction (run `edify graph build` later)")
    p_setup.add_argument("--extractor", default="builtin", choices=("builtin", "ctags"))
    p_setup.add_argument("--host", default="claude", choices=("claude", "none"),
                         help="write the host runtime's command and skill pointers")
    p_setup.add_argument("--agents", default="", metavar="all|none|IDS",
                         help=f"which agent runtimes to write files for ({_AGENT_IDS}); default: --host")
    p_setup.add_argument("--skills", default="all", metavar="ask|all|none|NAMES",
                         help="which library entries to install (default: all — setup means everything)")
    p_setup.add_argument("--yes", "-y", action="store_true", help="take every default answer, ask nothing")
    p_setup.add_argument("--force", action="store_true", help="implied — setup always installs over its own files")
    p_setup.set_defaults(func=_setup)

    p_init = sub.add_parser("init", help="install the harness into this repository")
    p_init.add_argument("--stack", default="auto", help="`auto`, or explicit tech ids to add to what was detected")
    p_init.add_argument("--force", action="store_true", help="overwrite files init would otherwise keep")
    p_init.add_argument("--no-graph", action="store_true", help="skip extraction (run `edify graph build` later)")
    p_init.add_argument("--extractor", default="builtin", choices=("builtin", "ctags"))
    p_init.add_argument("--host", default="claude", choices=("claude", "none"),
                        help="write thin command pointers for a host runtime")
    p_init.add_argument("--skills", default="auto", metavar="ask|all|none|NAMES",
                        help="which library entries to install (default: ask when there is a terminal)")
    p_init.add_argument("--yes", "-y", action="store_true",
                        help="take every default answer — install the whole matched set, ask nothing")
    p_init.add_argument("--agents", default="", metavar="all|none|IDS",
                        help=f"which agent runtimes to write files for ({_AGENT_IDS}); default: --host")
    p_init.set_defaults(func=_init)

    # `init new` — the from-nothing install. It is a subcommand of `init` rather than
    # a command of its own because it is the same install: one root, every runtime,
    # and the questions detection cannot answer.
    init_sub = p_init.add_subparsers(dest="init_command")
    p_new = init_sub.add_parser(
        "new", help="set a folder up from zero, for every agent, after asking what it is for"
    )
    p_new.add_argument("path", nargs="?", default=".", help="the folder to install into (created if missing)")
    p_new.add_argument("--agents", default="all", metavar="all|none|IDS",
                       help=f"which agent runtimes to write files for ({_AGENT_IDS})")
    p_new.add_argument("--stack", default="auto", help="`auto`, or explicit tech ids to add to what was detected")
    p_new.add_argument("--skills", default="all", metavar="ask|all|none|NAMES",
                       help="which library entries to install (default: all — `new` means everything)")
    p_new.add_argument("--no-interview", action="store_true",
                       help="install without asking anything; keeps an existing .edify/profile.md")
    p_new.add_argument("--keep", action="store_true",
                       help="do not clear edify's own files first — reinstall over what is there")
    p_new.add_argument("--no-graph", action="store_true", help="skip extraction (run `edify graph build` later)")
    p_new.add_argument("--extractor", default="builtin", choices=("builtin", "ctags"))
    p_new.add_argument("--host", default="claude", choices=("claude", "none"),
                       help="kept for symmetry with `init`; `--agents` is what decides here")
    p_new.add_argument("--yes", "-y", action="store_true", help="take every default answer, ask nothing")
    p_new.add_argument("--force", action="store_true", help="implied — `new` always installs over its own files")
    p_new.set_defaults(func=_init_new)

    p_check = sub.add_parser("check", help="report what is wrong with the documents")
    p_check.add_argument("--fix", action="store_true", help="apply the mechanical repairs only")
    p_check.add_argument("--exit-code", action="store_true", help="exit non-zero when there are errors (for CI)")
    p_check.add_argument("--strict", action="store_true", help="with --exit-code, treat warnings as errors")
    p_check.set_defaults(func=_check)

    p_upgrade = sub.add_parser("upgrade", help="pull a newer skill library and re-index")
    p_upgrade.add_argument("--channel", default="stable")
    p_upgrade.add_argument("--archive", metavar="PATH", help="install from a local archive instead of the network")
    p_upgrade.add_argument("--check", action="store_true", help="report what is available and change nothing")
    p_upgrade.add_argument("--skills", default="auto", metavar="ask|all|none|NAMES",
                           help="which entries in the archive to install (default: ask when there is a terminal)")
    p_upgrade.add_argument("--yes", "-y", action="store_true", help="install every valid entry, ask nothing")
    p_upgrade.set_defaults(func=_upgrade)

    # -- graph -----------------------------------------------------------
    p_graph = sub.add_parser("graph", help="build and query the map")
    graph_sub = p_graph.add_subparsers(dest="graph_command")

    g_build = graph_sub.add_parser("build", help="full extraction")
    g_build.add_argument("--extractor", default="builtin", choices=("builtin", "ctags"))
    g_build.set_defaults(func=_graph_build)

    g_update = graph_sub.add_parser("update", help="re-extract one or more directories")
    g_update.add_argument("dirs", nargs="+")
    g_update.add_argument("--extractor", default="builtin", choices=("builtin", "ctags"))
    g_update.set_defaults(func=_graph_update)

    g_where = graph_sub.add_parser("where", help="file:line and kind for a name")
    g_where.add_argument("name")
    g_where.add_argument("--kind", choices=("file", "module", "symbol", "route", "table", "package", "doc-section"))
    g_where.set_defaults(func=_graph_where)

    g_dep = graph_sub.add_parser("dependents", help="everything that breaks if this changes")
    g_dep.add_argument("symbol")
    g_dep.add_argument("--depth", type=int, default=1)
    g_dep.set_defaults(func=_graph_dependents)

    g_ref = graph_sub.add_parser("references", help="who calls or imports this")
    g_ref.add_argument("name")
    g_ref.set_defaults(func=_graph_references)

    g_def = graph_sub.add_parser("defines", help="what this file exports")
    g_def.add_argument("file")
    g_def.set_defaults(func=_graph_defines)

    g_ov = graph_sub.add_parser("overlap", help="do these two file sets intersect")
    g_ov.add_argument("a")
    g_ov.add_argument("b")
    g_ov.add_argument("--depth", type=int, default=1)
    g_ov.set_defaults(func=_graph_overlap)

    g_stat = graph_sub.add_parser("stat", help="what is in the map")
    g_stat.set_defaults(func=_graph_stat)

    # -- skills ----------------------------------------------------------
    p_skills = sub.add_parser("skills", help="the installed library and the spawn lookup")
    skills_sub = p_skills.add_subparsers(dest="skills_command")

    s_list = skills_sub.add_parser("list", help="what is installed, with provenance and licence")
    s_list.set_defaults(func=_skills_list)

    s_resolve = skills_sub.add_parser("resolve", help="the one file a spawn in this position loads")
    s_resolve.add_argument("role")
    s_resolve.add_argument("phase")
    s_resolve.add_argument("tech", nargs="?")
    s_resolve.set_defaults(func=_skills_resolve)

    s_index = skills_sub.add_parser("index", help="re-sort the lookup table")
    s_index.set_defaults(func=_skills_index)

    s_add = skills_sub.add_parser("add", help="install one entry from a local file")
    s_add.add_argument("path")
    s_add.set_defaults(func=_skills_add)

    s_sync = skills_sub.add_parser("sync", help="mirror the library into each runtime's skill directory")
    s_sync.add_argument("--host", default="claude", choices=("claude", "none"))
    s_sync.add_argument("--agents", default="", metavar="all|none|IDS",
                        help=f"which agent runtimes to mirror into ({_AGENT_IDS}); default: the ones set up here")
    s_sync.set_defaults(func=_skills_sync)

    # -- harvest ---------------------------------------------------------
    # Four steps that run unattended and one that never does.
    p_harvest = sub.add_parser("harvest", help="turn a public capability into a library entry")
    harvest_sub = p_harvest.add_subparsers(dest="harvest_command")

    h_pick = harvest_sub.add_parser("pick", help="which source to draw from, and what not to gather again")
    h_pick.add_argument("--count", type=int, default=5, help="how many new candidates this run is aiming for")
    h_pick.add_argument("--source", default="", metavar="NAME",
                        help="draw from this row instead of the best-scoring one")
    h_pick.add_argument("--all", action="store_true", help="print every row with its score, not just the choice")
    h_pick.set_defaults(func=_harvest_pick)

    h_stage = harvest_sub.add_parser("stage", help="record one gathered artifact, or refuse a repeat")
    h_stage.add_argument("--url", required=True, help="where it came from")
    h_stage.add_argument("--name", required=True, help="the entry name it would take, [a-z0-9-]+")
    h_stage.add_argument("--content", required=True, metavar="PATH", help="the raw bytes, already on disk")
    h_stage.add_argument("--commit", default="", help="the commit hash it was read at")
    h_stage.add_argument("--license", default="", help="the licence as found, or nothing — which means NONE-FOUND")
    h_stage.add_argument("--source", default="", help="which row of sources.md this came from")
    h_stage.set_defaults(func=_harvest_stage)

    h_screen = harvest_sub.add_parser("screen", help="licence, duplicate, injection — mechanical and fail-closed")
    h_screen.add_argument("ids", nargs="*", help="candidates to screen (default: everything staged)")
    h_screen.set_defaults(func=_harvest_screen)

    h_propose = harvest_sub.add_parser("propose", help="present a rewrite for admission")
    h_propose.add_argument("id")
    h_propose.add_argument("--file", required=True, metavar="PATH", help="the rewritten entry")
    h_propose.add_argument("--case", required=True, help="one line: the scenario nothing in the library serves")
    h_propose.set_defaults(func=_harvest_propose)

    h_admit = harvest_sub.add_parser("admit", help="a person read it and says yes")
    h_admit.add_argument("id")
    h_admit.add_argument("--by", required=True, help="who read it")
    h_admit.set_defaults(func=_harvest_admit)

    h_reject = harvest_sub.add_parser("reject", help="a person read it and says no")
    h_reject.add_argument("id")
    h_reject.add_argument("--reason", required=True, help="why — this is what makes the next run cheap")
    h_reject.add_argument("--by", default="", help="who read it")
    h_reject.set_defaults(func=_harvest_reject)

    h_status = harvest_sub.add_parser("status", help="the ledger, by state and by source")
    h_status.set_defaults(func=_harvest_status)

    # -- governance ------------------------------------------------------
    p_gov = sub.add_parser("governance", help="what edify installed here, and whether it is unchanged")
    gov_sub = p_gov.add_subparsers(dest="governance_command")

    v_list = gov_sub.add_parser("list", help="every governed file, with origin and licence")
    v_list.set_defaults(func=_governance_list)

    v_verify = gov_sub.add_parser("verify", help="the ledger against what is on disk")
    v_verify.add_argument("--exit-code", action="store_true",
                          help="exit non-zero when a governed file is missing, modified, or unrecorded")
    v_verify.set_defaults(func=_governance_verify)

    v_rebuild = gov_sub.add_parser("rebuild", help="re-baseline the ledger after a deliberate change")
    v_rebuild.set_defaults(func=_governance_rebuild)

    # -- mcp -------------------------------------------------------------
    p_mcp = sub.add_parser("mcp", help="the server registry")
    mcp_sub = p_mcp.add_subparsers(dest="mcp_command")

    m_list = mcp_sub.add_parser("list", help="the registry, with what each entry is scoped to")
    m_list.set_defaults(func=_mcp_list)

    m_check = mcp_sub.add_parser("check", help="each server responds and its version matches the pin")
    m_check.set_defaults(func=_mcp_check)

    m_for = mcp_sub.add_parser("for", help="what a spawn in this position would load")
    m_for.add_argument("role")
    m_for.add_argument("phase")
    m_for.set_defaults(func=_mcp_for)

    # -- ship ------------------------------------------------------------
    p_doctor = sub.add_parser("doctor", help="does the install work here")
    p_doctor.set_defaults(func=_doctor)

    # `self` is the binary talking about itself. Not `upgrade`, which pulls a newer
    # skill library — two different things, kept under two names on purpose.
    p_self = sub.add_parser("self", help="the `edify` binary itself: where it is, and updating it")
    self_sub = p_self.add_subparsers(dest="self_command")

    sf_where = self_sub.add_parser("where", help="which edify is this, and where did it come from")
    sf_where.set_defaults(func=_self_where)

    sf_update = self_sub.add_parser("update", help="reinstall the CLI from a source checkout")
    sf_update.add_argument("--from", dest="from_path", metavar="PATH",
                           help="the checkout to install from (default: the one this code came from)")
    sf_update.add_argument("--manager", default="", choices=("", "uv", "pipx", "pip"),
                           help="override the detected installer; `edify self where` prints what was detected")
    sf_update.add_argument("--editable", action="store_true",
                           help="install in place, so later edits need no reinstall")
    sf_update.add_argument("--offline", action="store_true",
                           help="never reach the network; fails cleanly when the build backend is not cached")
    sf_update.add_argument("--dry-run", action="store_true",
                           help="print the install command and change nothing")
    sf_update.set_defaults(func=_self_update)

    p_license = sub.add_parser("license", help="what this machine is entitled to")
    license_sub = p_license.add_subparsers(dest="license_command")
    l_status = license_sub.add_parser("status", help="plan, entitlements, and limits")
    l_status.set_defaults(func=_license_status)
    l_activate = license_sub.add_parser("activate", help="install a licence token")
    l_activate.add_argument("token", help="the token itself, or a path to a file containing it")
    l_activate.set_defaults(func=_license_activate)
    l_deactivate = license_sub.add_parser("deactivate", help="remove the licence from this machine")
    l_deactivate.set_defaults(func=_license_deactivate)

    # Opens a browser, not a socket. Under --json, --quiet, or with no terminal it
    # prints the URL and stops.
    l_buy = license_sub.add_parser("buy", help="the pro plan, its price, and where to pay")
    l_buy.add_argument("--seats", type=int, default=1, help="how many seats to buy")
    l_buy.set_defaults(func=_license_buy)

    l_projects = license_sub.add_parser(
        "projects", help="which repositories are using a slot on the free plan"
    )
    l_projects.set_defaults(func=_license_projects)
    projects_sub = l_projects.add_subparsers(dest="projects_command")
    l_forget = projects_sub.add_parser("forget", help="release one slot")
    l_forget.add_argument("which", metavar="PATH", help="the project's path, or its ledger key")
    l_forget.set_defaults(func=_license_projects_forget)

    p_feedback = sub.add_parser("feedback", help="how this is going — written to a file on this machine")
    p_feedback.add_argument("--message", "-m", help="one line instead of the four questions")
    p_feedback.set_defaults(func=_feedback_new)
    feedback_sub = p_feedback.add_subparsers(dest="feedback_command")
    f_list = feedback_sub.add_parser("list", help="what you have written, and where it is")
    f_list.set_defaults(func=_feedback_list)
    f_show = feedback_sub.add_parser("show", help="print one entry")
    f_show.add_argument("which", nargs="?", help="the entry's number (default: the last one)")
    f_show.set_defaults(func=_feedback_show)
    f_off = feedback_sub.add_parser("off", help="never show the invitation again")
    f_off.set_defaults(func=_feedback_off)
    f_on = feedback_sub.add_parser("on", help="show the invitation again")
    f_on.set_defaults(func=_feedback_on)

    p_version = sub.add_parser("version", help="print the version")
    p_version.set_defaults(func=_version)

    return parser


# -- dispatch ---------------------------------------------------------------
# Imports live inside the handlers so `edify version` does not pay for the graph.


def _setup(ctx):
    from .commands import setup_cmd

    return setup_cmd.run(ctx)


def _init(ctx):
    from .commands import init_cmd

    return init_cmd.run(ctx)


def _init_new(ctx):
    from .commands import init_new_cmd

    return init_new_cmd.run(ctx)


def _check(ctx):
    from .commands import check_cmd

    return check_cmd.run(ctx)


def _upgrade(ctx):
    from .commands import upgrade_cmd

    return upgrade_cmd.run(ctx)


def _graph_build(ctx):
    from .commands import graph_cmd

    return graph_cmd.build(ctx)


def _graph_update(ctx):
    from .commands import graph_cmd

    return graph_cmd.update(ctx)


def _graph_where(ctx):
    from .commands import graph_cmd

    return graph_cmd.where(ctx)


def _graph_dependents(ctx):
    from .commands import graph_cmd

    return graph_cmd.dependents(ctx)


def _graph_references(ctx):
    from .commands import graph_cmd

    return graph_cmd.references(ctx)


def _graph_defines(ctx):
    from .commands import graph_cmd

    return graph_cmd.defines(ctx)


def _graph_overlap(ctx):
    from .commands import graph_cmd

    return graph_cmd.overlap(ctx)


def _graph_stat(ctx):
    from .commands import graph_cmd

    return graph_cmd.stat(ctx)


def _skills_list(ctx):
    from .commands import skills_cmd

    return skills_cmd.list_(ctx)


def _skills_resolve(ctx):
    from .commands import skills_cmd

    return skills_cmd.resolve(ctx)


def _skills_index(ctx):
    from .commands import skills_cmd

    return skills_cmd.index(ctx)


def _skills_add(ctx):
    from .commands import skills_cmd

    return skills_cmd.add(ctx)


def _skills_sync(ctx):
    from .commands import skills_cmd

    return skills_cmd.sync(ctx)


def _harvest_pick(ctx):
    from .commands import harvest_cmd

    return harvest_cmd.pick(ctx)


def _harvest_stage(ctx):
    from .commands import harvest_cmd

    return harvest_cmd.stage(ctx)


def _harvest_screen(ctx):
    from .commands import harvest_cmd

    return harvest_cmd.screen(ctx)


def _harvest_propose(ctx):
    from .commands import harvest_cmd

    return harvest_cmd.propose(ctx)


def _harvest_admit(ctx):
    from .commands import harvest_cmd

    return harvest_cmd.admit(ctx)


def _harvest_reject(ctx):
    from .commands import harvest_cmd

    return harvest_cmd.reject(ctx)


def _harvest_status(ctx):
    from .commands import harvest_cmd

    return harvest_cmd.status(ctx)


def _governance_list(ctx):
    from .commands import governance_cmd

    return governance_cmd.list_(ctx)


def _governance_verify(ctx):
    from .commands import governance_cmd

    return governance_cmd.verify(ctx)


def _governance_rebuild(ctx):
    from .commands import governance_cmd

    return governance_cmd.rebuild(ctx)


def _mcp_list(ctx):
    from .commands import mcp_cmd

    return mcp_cmd.list_(ctx)


def _mcp_check(ctx):
    from .commands import mcp_cmd

    return mcp_cmd.check(ctx)


def _mcp_for(ctx):
    from .commands import mcp_cmd

    return mcp_cmd.for_(ctx)


def _doctor(ctx):
    from .commands import doctor_cmd

    return doctor_cmd.run(ctx)


def _self_where(ctx):
    from .commands import self_cmd

    return self_cmd.where(ctx)


def _self_update(ctx):
    from .commands import self_cmd

    return self_cmd.update(ctx)


def _license_status(ctx):
    from .commands import license_cmd

    return license_cmd.status(ctx)


def _license_activate(ctx):
    from .commands import license_cmd

    return license_cmd.activate(ctx)


def _license_deactivate(ctx):
    from .commands import license_cmd

    return license_cmd.deactivate(ctx)


def _license_buy(ctx):
    from .commands import license_cmd

    return license_cmd.buy(ctx)


def _license_projects(ctx):
    from .commands import license_cmd

    return license_cmd.projects(ctx)


def _license_projects_forget(ctx):
    from .commands import license_cmd

    return license_cmd.projects_forget(ctx)


def _feedback_new(ctx):
    from .commands import feedback_cmd

    return feedback_cmd.new(ctx)


def _feedback_list(ctx):
    from .commands import feedback_cmd

    return feedback_cmd.list_(ctx)


def _feedback_show(ctx):
    from .commands import feedback_cmd

    return feedback_cmd.show(ctx)


def _feedback_off(ctx):
    from .commands import feedback_cmd

    return feedback_cmd.off(ctx)


def _feedback_on(ctx):
    from .commands import feedback_cmd

    return feedback_cmd.on(ctx)


def _version(ctx):
    ctx.out.data({"version": __version__})
    ctx.out.line(f"edify {__version__}")
    return 0


# ---------------------------------------------------------------------------


def _invite(ctx, args) -> None:
    """The one line asking how this is going, printed as the CLI opens.

    Silent unless there is a real terminal, and at most once per released version.
    It never asks anything here — a command that stops to interview you before doing
    what you typed is a command people learn to avoid.
    """
    if getattr(args, "command", None) == "feedback":
        return
    from . import feedback

    try:
        feedback.maybe_invite(ctx.out)
    except OSError:
        pass  # a feedback prompt is never a reason for a command to fail


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not getattr(args, "func", None):
        # A family named with no subcommand prints that family's help, which is
        # more useful than the top-level usage the user has already seen.
        for family in ("graph", "skills", "harvest", "governance", "mcp", "license", "self"):
            if getattr(args, "command", None) == family:
                parser.parse_args([family, "--help"])
        print(USAGE)
        return 0 if getattr(args, "command", None) is None else 2

    ctx = build_context(args)
    _invite(ctx, args)
    try:
        return args.func(ctx) or 0
    except EdifyError as exc:
        ctx.out.error(exc.message, exc.hint)
        return exc.exit_code
    except KeyboardInterrupt:
        ctx.out.error("interrupted")
        return 130
    except BrokenPipeError:
        return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
