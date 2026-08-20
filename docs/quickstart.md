# Quickstart

From nothing to a verified change, in about ten minutes. You need Python 3.10+
and a coding agent you already use.

---

## 1 · Install

```bash
pipx install edify-cli          # or: uv tool install edify-cli
```

Per-platform detail, PATH fixes, and where EDIFY keeps its files:
[INSTALL.md](../INSTALL.md).

## 2 · Install the harness into a repository

```bash
cd your-repository
edify init
```

`init` does seven things and then stops: detect the stack, extract the graph,
scrape conventions from your config files, install the skill entries your stack
matches, seed the server registry, write a fifteen-line `CLAUDE.md`, and record
every file it put there.

It asks exactly one question — which library entries to install, because those
become trusted instruction in every matching session and you should see the list
first.

```bash
edify init --yes                      # the whole matched set, no question
edify init --skills planner,verifier  # exactly these
edify init --skills none              # none; add them later
```

**Using something other than Claude Code?** Use `init new`, which writes the
instruction file *every* runtime reads rather than just `CLAUDE.md`:

```bash
edify init new .                      # asks eight short questions first
edify init new . --agents cursor,codex
```

## 3 · Check the install

```bash
edify doctor
```

···  `edify doctor`

<img src="../assets/doctor.svg" alt="edify doctor output" width="100%">

Green is fine. Amber is fine — it names what is degraded and why. Red means see
[troubleshooting.md](troubleshooting.md).

## 4 · Look at the map

```bash
edify graph where <a symbol you know>
edify graph dependents <the same symbol>
```

If your symbol comes back with the right file and line, the graph is working. If
it does not, that is a [graph gap](../.github/ISSUE_TEMPLATE/graph_gap.yml) and
we want the report.

## 5 · Run the workflow on one real task

Open your agent in this repository and type:

```
/spec
```

Then `/plan` (only if the feature needs one), `/tasks`, `/build`, `/verify`.

| command | what it does | ends at |
|---|---|---|
| `/spec` | a brief becomes a specification | a human |
| `/plan` | spec → technology decisions and milestones | a human |
| `/tasks` | spec + plan + graph → a phased task list | a human |
| `/build` | task list → working software | a diff and a green suite |
| `/verify` | the code → evidence | a report anyone can read |

The first three are slow and end at a human reading them. That is the point:
think hard once, then build without thinking.

## 6 · Read what it wrote

```
specs/<feature>/
  spec.md            what is being built and why
  plan.md            when the feature needs one
  tasks.md           exactly what changes, where, in what order
  verification.md    written by /verify
```

```bash
edify check          # is anything wrong with those documents
edify check --fix    # fix what can be fixed mechanically
```

---

## Pick a good first task

EDIFY earns its keep where the codebase stops fitting in a context window. A good
first task is one that:

- touches **three or more files** that are not next to each other,
- has a **correctness condition you can state** ("existing sessions must not be
  invalidated"),
- and has previously gone wrong when handed straight to an agent.

A bad first task is a one-file change a frontier model already does perfectly.
You will conclude EDIFY is ceremony, and for that task you will be right.

## Then tell us what broke

```bash
edify feedback
```

Four questions, written to a file on your machine. Nothing is sent — it prints a
`gh issue create` command and you decide. Or open a
[discussion](https://github.com/edify-dev/edify/discussions) directly.
