# 09 — The CLI

`edify` is the binary. It installs the harness, builds and queries the graph, resolves
skills, and checks formats. It is not the agent runtime and never wraps a model.

The previous design specified eleven command families — init, doctor, facts, compile,
upgrade, state, ledger, audit, validate, library, license. Six of those existed to
serve subsystems that are gone. What remains is four families and about a dozen
subcommands.

---

## 1. What the CLI is

A pure function over files. Every command reads files and writes files; none holds
state, opens a socket, or calls out to a network except `edify upgrade`. It runs
offline by default because the hardest customer to install into has no outbound
network and a procurement process for anything that does.

**Deterministic where it decides.** The commands that select, resolve, or index are
tables and lookups. `edify` may be invoked by a model; **no `edify` command lets a
model decide what is installed, indexed, or resolved.**

## 2. The surface

### Lifecycle

```
edify init new [PATH]               a folder from zero, for every agent — asks first
edify setup [PATH] [--fresh]        install everything into one folder, root pinned there
edify init [--stack auto|<ids>]     detect · extract · select skills · write CLAUDE.md
edify check [--fix]                 format check over specs, tasks, and skill files
edify upgrade                       pull a newer skill library and re-index
```

**`init new`** is the from-nothing install, and it differs from `setup` in two ways
that are the reason it exists rather than another flag.

**It installs for every agent runtime, not one.** `init` and `setup` write `CLAUDE.md`
and `.claude/`. On a machine with Codex, Cursor, Gemini, Copilot, or Windsurf open —
which is most of them — that install is present and unreachable: the methodology is in
`.edify/` and no runtime but one has been told where to look. `init new` writes the
instruction file each runtime actually reads and the command pointers into each
runtime's own directory, from one table (`src/edify/agents.py`): file path, command
directory, suffix, and format per row. Every instruction file carries the *same* block,
because two tools open on one repository must not be running two methodologies. Adding a
runtime is adding a row. `--agents` narrows the set; `--agents none` installs `.edify/`
and nothing else.

**It asks.** Eight questions, before anything is written. Detection reads the manifest
files; it cannot read that this is a rewrite of a system already in production, that the
person typing is the only one who knows the domain, or that nothing may touch migrations
without a plan. Those facts decide how an agent should behave here and there is one
place to get them. Two of the eight — which runtimes, and what detection missed — decide
what gets installed, which is why they are asked first and why the interview is not a
survey. The rest go to `.edify/profile.md`, which every instruction file points at,
which is recorded in the ledger as `answered` and never overwritten by `upgrade`, and
which is read back on a re-run so last time's answers are the defaults.

The rules from `../01-principles.md` hold unchanged. A question is never load-bearing:
with no terminal nothing is asked, no profile is written, and the full install happens
anyway. Every answer may be empty. And no `edify` command lets a *model* decide what is
installed — this one narrows a set that was already computed by lookup, at a terminal,
by a person.

**`setup`** is `init` with the root pinned and force on, and it exists because of one
trap. `init` finds the repository root by walking upward, so `mkdir service && cd
service && edify init` inside an existing checkout installs into the **parent** — into
the `.edify/` the outer repository already has, silently and with no error. `setup`
anchors the root at exactly the path it was given, never looks above it, and creates the
folder if it does not exist.

`--fresh` clears EDIFY's own surface before installing: `.edify/`, the runtime pointers
that carry the generated marker, and its block in every instruction file. Nothing else,
ever — a hand-written `SKILL.md`, a custom command, source code, and the rest of
somebody's `CLAUDE.md` all survive it. `--fresh` is a reinstall, not `rm -rf`. `init new`
clears the same way through the same function; two commands that both mean "install
everything, again, properly" must not have two ideas of what that covers.

**`init`** does seven things and then stops:

1. **Detect** — languages, frameworks, test runner, package manager, from the manifest
   files that are actually present.
2. **Extract** — run the graph extractor over the whole tree.
3. **Scrape conventions** — read the lint config, formatter config, type-checker
   settings, editor config, test layout, commit convention, and the CI job's real
   commands, and write `.edify/conventions.md`. Roughly fifteen lines, **zero model
   calls** (`../06-the-graph.md` §6).
4. **Select** — install the skill entries whose `tech` matches what was detected, plus
   the role entries every repository needs.
5. **Seed the MCP registry** — one entry, the documentation server, scoped to the
   planner and implementer roles (`07-mcp.md` §3).
6. **Write `CLAUDE.md`** — the fifteen-line router.
7. **Record what it installed** — `.edify/governance.tsv`, one row per file with its
   origin, provenance, licence, and hash (§ Governance below).

There is no constitution, no governance level, and no archetype — those were inputs to
subsystems that no longer exist. `init` itself still asks nothing beyond which library
entries to take; the interview belongs to `init new`, which is the command for a folder
that has no answers in it yet.

`init` on a repository that already has an AI instruction file **merges, never
overwrites**. Somebody wrote that file on purpose. Which files those are, with no
`--agents` given, is whichever runtimes are already set up in the folder — so a folder
`init new` prepared for six of them has all six kept current, rather than `CLAUDE.md`
updated and five left stale. A hand-written `AGENTS.md` is never taken as evidence that
Codex or Cursor is set up here: it is as likely to predate EDIFY as to have been written
by it, and reading it as a signal would have `init` start writing into `.codex/` in a
repository that asked for neither.

**`check`** is the whole validation story, and it is a command, not a gate. It reports:
a spec whose requirements lack assertions, or an assertion with no verification kind; a
plan technology row with no version or no alternative named; a context seed with no line
range; a task with no `Discharges`, no steps, or no done-check; a phase-2 task whose
done-check asserts tests pass rather than fail; a whole-file reference on an `edit`
action; a `## Coverage` row with an empty cell; a `file:line` that does not resolve
against the graph; a skill file over budget or with invalid frontmatter. `--fix` handles
only the mechanical ones — resolving a filename to a line range through the graph,
re-sorting the index.

Nothing in `check` blocks anything. A person runs it, or CI runs it, and it prints what
is wrong. That is the honest scope, and `../01-principles.md` P7 says why.

### Graph

```
edify graph build                   full extraction
edify graph update <dir>...         one or more directories — runs after each phase
edify graph where <name>            file:line and signature
edify graph dependents <symbol>     everything that breaks if this changes
edify graph defines <file>          what this file exports
edify graph overlap <a> <b>         do these file sets intersect, dependents included
```

Six subcommands, all mechanical, all sub-second. `06-graph.md` has the detail. These
are the commands `CLAUDE.md` points at, and they are the only part of the CLI a model
invokes routinely.

### Skills

```
edify skills list                   what is installed, with provenance and license
edify skills resolve <role> <phase> [tech]    → one file path
edify skills index                  re-sort the lookup table
edify skills add <path>             install one entry from the library
edify skills sync                   mirror the library into the host's skill directory
```

`resolve` is the lookup `/build` performs before every spawn. It is a binary search
over a sorted TSV and it prints one line.

`sync` closes a gap between "installed" and "usable". `.edify/skills/<name>.md` is
where an entry lives and `resolve` is how a build spawn finds it; neither is where the
host runtime looks. Claude Code discovers skills at `.claude/skills/<name>/SKILL.md`,
one directory each, and subagents at `.claude/agents/<name>.md`, one flat file each, so
until that mirror exists an installed entry is invisible in the session the person is
actually typing into. The mirror is **pointers**: each file carries the two fields the
runtime discovers on — `name` and the entry's own `description`, which is what it
matches relevance against — and then names the canonical path. A copy would go stale
the first time an entry changed and nothing would say so.

Which of the two directories an entry gets is its `kind`, and the distinction is not
presentational. The runtime *matches* a skill against what a session is already doing
and *spawns* an agent by name into a session that has no history, so a `kind: agent`
entry mirrored as a skill is loadable and unspawnable: `/build` resolves it, asks for a
subagent by that name, and gets nothing. `kind` had two legal values in the skill format
and one destination on disk until this was fixed, which is the shape of bug this whole
mirror exists to prevent — installed, indexed, governed, and unusable. `stale` reports
both families, including an entry that changed `kind` and left its old pointer behind.

It runs inside `init`, `upgrade`, `setup`, `skills add`, and the admission step of
`/harvest`; standalone for the case where a skill file was added or removed by hand.
There is no `--force`, because a pointer is derived output: one that differs from what
it should say is brought up to date, and one that EDIFY did not write is never touched
with or without a flag.

There is deliberately **no `skills install <url>`** and no registry browsing. Anything
that arrives from outside goes through `/harvest` and a human, in EDIFY's own
repository. An ad-hoc import is a stranger's text loaded as trusted instruction into
every matching session in a customer's codebase.

For the same reason `init` and `upgrade` **show the matched entries and take an
answer** before installing them. This does not weaken §1's rule that no `edify`
command lets a model decide what is installed: the set is still computed by lookup,
the question only narrows it, and it is asked of a person. Where there is no person —
no terminal, `--json`, `CI` in the environment — nothing is asked and the whole
matched set is installed, because a prompt that appears in a pipeline is a hang.
`--skills ask|all|none|<names>` and `--yes` state the answer up front.

### Governance

```
edify governance list               every file edify installed, and where it came from
edify governance verify             the ledger against what is on disk
edify governance rebuild            re-baseline after a deliberate change
```

`.edify/governance.tsv` records one row per installed file: path, kind, origin,
provenance, licence, sha256 at install, and the CLI version that wrote it. Skill
entries carried this in frontmatter from the first release; nothing else did, which
left the majority of the installed surface with no answer to "where did this come
from and has it changed".

It is a ledger, not a lock, and that is `../01-principles.md` P7 applied literally:
the control is that a person can read what was installed and check it, not that
anything is prevented. `verify` separates the origins EDIFY owns — a modified
`library`, `shipped`, or `generated` file, which `upgrade` will overwrite — from the
ones the repository owns, where an edit to `mcp.md` or `conventions.md` is the file
being used as intended. `--exit-code` is how a customer who needs a block owns one.

The host mirror is governed as `generated`, and only where EDIFY wrote it. Every
pointer carries a marker line, so a `SKILL.md` or a command file somebody wrote by hand
stays out of the ledger entirely — which is what keeps the hand-authored harvest skill
from being reported as modified every time anyone touches it, and stops the ledger
claiming authorship of a file it did not write.

The graph is deliberately not governed here. It is regenerated output, it changes on
every build, and `.edify/graph/meta` already carries its checksums.

### Servers

```
edify mcp list                      the registry, with what each entry is scoped to
edify mcp check                     each server responds and its version matches the pin
edify mcp for <role> <phase>        what a spawn in this position would load
```

`for` exists so the scoping is inspectable rather than implicit — "why did this task
have the browser loaded?" should be one command, not an investigation. The same posture
as skills applies: no browsing, no catalog, no `mcp add <url>`. An entry is a reviewed
change to `.edify/mcp.md` (`07-mcp.md`).

### Ship

```
edify version
edify doctor                        does the install work here: extractor present,
                                    graph parses, index resolves, CLAUDE.md matches
edify feedback [list|show|off|on]   four questions, written to a file on this machine
```

`doctor` is five checks and a green/amber/red line, where amber means "this works but
degraded, and here is which part": the extractor is present and pinned, the graph parses
and is not badly stale, the skill index resolves every role, every MCP entry responds at
its pinned version, and `CLAUDE.md` matches what `init` would write. It is not the
twelve-probe apparatus of the previous design because there are no hooks to probe, no
runtime surface to pin, and no compiled targets to hash.

**`feedback`** is the one place the product asks the user a question about itself, and
it is built to the shape `../../pricing.md` §4 requires. It writes a file under
the user's config directory and prints the `gh issue create` command and the URL that
would send it; sending is the person's action, on text they have read. Nothing is
transmitted, nothing is collected in the background, and `upgrade` remains the only
command in this CLI that opens a socket.

The invitation is one dim line on stderr as the CLI opens, at most once per released
version, only on a real terminal. It never asks anything inline — a command that
stops to interview you before doing what you typed is a command people learn to
avoid — and `edify feedback off` or `EDIFY_NO_FEEDBACK` ends it permanently. The only
state is a run counter and the version that last asked, in the user config directory,
written **only on interactive runs**, so a CI job or a model calling the binary leaves
no trace at all.

## 3. What the CLI is not

- **Not a wrapper around the agent.** No `edify chat`, no `edify run <prompt>`.
  Wrapping the runtime puts us in the path of its release velocity, which is the
  fastest-moving thing in this market and the last place to stand.
- **Not a package manager for the open ecosystem.** One curated library, one door.
- **Not a server.** No daemon, no dashboard, no web UI.
- **Not a gate.** Every check prints; nothing halts a session.
- **Not the extractor's owner.** It is pinned, wrapped, and replaceable. The TSV
  contract is the asset.

## 4. Distribution

**Today:** one dependency-free Python package, `edify-cli`, on PyPI, installed with
`pipx`, `uv`, or a Homebrew tap that wraps the same artifact. It runs identically on
macOS, Linux, and Windows, needs no compiler, and drags no runtime onto a build
server beyond a Python that is already there. `PUBLISHING.md` is how it is registered
and released; `INSTALL.md` is what a user reads.

**Where it is going:** a self-contained static binary per platform, in a compiled
language. The reasons are
unchanged from the previous analysis and one of them got stronger: the graph pipeline
already ships a static binary, so "one self-contained artifact per platform" is a shape
this product carries regardless. A scripting-runtime distribution reintroduces "install
a runtime on the build server", which is a real procurement objection in exactly the
accounts this product is for.

Everything works offline except `upgrade`, which also has a documented plain-archive
path.

## 5. Build order

The CLI is not the first thing built. The commands and the three formats come first,
used by hand, on real work — that is what produces the friction log that says which CLI
subcommands actually matter.

The one exception is the graph. `edify graph` has to exist before `/tasks` can produce a
plan with real `file:line` references, and a plan without those is a plan that transfers
its cost to build time. So the order is:

1. **The graph commands** — `build`, `update`, `where`, `dependents`, `overlap`.
   Nothing else in the system works properly without them.
2. **The five command files** — `/spec`, `/plan`, `/tasks`, `/build`, `/verify` — plus
   the three formats and the three examples. Run them by hand on real features.
3. **`skills resolve` and `index`** — the moment there is more than one skill file per
   role, which is quickly.
4. **`mcp for`** — the moment the registry has more than one entry, because unscoped
   servers are the tax this design exists to avoid.
5. **`init` and `check`** — when the first repository other than ours installs it.
   `init`'s conventions scrape lands here; it is a config reader, not an analysis, and
   it is a day of work.
6. **`doctor` and `upgrade`** — when somebody who is not us has to make it work.

Steps 1 and 2 are the product. Everything after is what makes it installable by a
stranger, and none of it should be built before a stranger needs it.
