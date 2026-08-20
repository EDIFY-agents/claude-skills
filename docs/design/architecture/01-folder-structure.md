# 01 — Folder Structure

Two trees: the **source tree** we author and version, and the **installed tree**
`edify init` puts into a repository. The installed tree is small enough to read in
one screen, which is the point.

---

## 1. The source tree

```
edify/
  manifest.md              # version, the pinned extractor and its checksum
  commands/                # the methodology surface — one file per command
    spec.md
    plan.md
    tasks.md
    build.md
    verify.md
  formats/                 # the three artifact formats + their worked examples
    spec.format.md
    spec.example.md        # → design/spec-ex.md, promoted
    plan.format.md
    plan.example.md        # → design/plan-ex.md, promoted
    tasks.format.md
    tasks.example.md
  skills/                  # the library — one file per capability
    index.tsv              #   the sorted lookup table, generated
    implementer-general.md
    implementer-react.md
    implementer-python.md
    test-writer-node.md
    verifier.md
    adversary.md
    debugger.md
    ...
  mcp/
    default-registry.md    #   the one entry `edify init` seeds: the docs server
  harvest/                 # the curation skill + its two reference files
    harvest.md
    sources.md             #   where candidates come from, with yield history
    vocab.md               #   the controlled values for role · phase · tech
  bin/                     # the edify binary's source
```

Eleven paths at the top level, two of which are directories of short markdown files.
Compare the previous design's source tree: eight command folders, fourteen schema pairs,
four policy files, a concerns folder, an agents folder, a five-stage curation folder, a
staging area, a library, a templates tree, a compiler, and a doctor script.

**What each command file is.** Roughly 60–100 lines: what it reads, the loop it runs,
what it refuses, what it writes, and one line pointing at the format and its example.
It contains no format teaching and no policy prose. Contracts in `02-commands.md`.

**Why formats and examples sit together.** The format document is the contract; the
example is the calibration. `src/import.py` and `src/import.py:88-114` both satisfy
any shape rule anyone would write down — only an example shows which one is meant.
The example is the cheaper half of the pair and does more work.

## 2. The installed tree

```
<repo>/
  CLAUDE.md                # ~15 lines — §3
  AGENTS.md                # the same fifteen lines, for the runtimes that read this
  GEMINI.md                # …one per runtime `edify init new` was asked for — §2.1
  .edify/
    graph/
      nodes.tsv            # id  kind  file  line  name  fingerprint
      edges.tsv            # from  relation  to
      meta                 # source commit, extractor version, checksums
    skills/                # only the entries this repo's stack matched
      index.tsv
      *.md
    mcp.md                 # the server registry — pinned, scoped per role × phase
    conventions.md         # scraped from lint/format/tsconfig/CI — no model call
    profile.md             # what a person answered when `init new` asked — §2.1
  specs/
    <feature>/
      spec.md
      plan.md              # when the feature needs one
      tasks.md
      verification.md      # written by /verify
```

Ten paths, plus one instruction file per agent runtime that was asked for (§2.1).
Everything under `.edify/graph/` is regenerable and may be committed or
ignored by preference — committing it makes `git diff` show structural change, which
some teams like. Everything else is source and is committed.

**`conventions.md` costs nothing to produce.** It is a scrape of the config files
already on disk — lint rules, formatter settings, type-checker strictness, test layout,
commit convention, the CI job's real commands — performed by `edify init` with **no
model call at all**. Roughly fifteen lines. It exists because those conventions are what
a builder needs and what no graph query answers, and it is a scrape rather than an
analysis because a scrape is free and an analysis is a guess. The reasoning, and why
there is no AI-driven architecture-discovery pass, is in `../06-the-graph.md` §6.

There is no audit chain, no memory folder, no session folder, no schemas folder, and no
concerns folder.

## 2.1 One instruction file per runtime, and why that reversed

This document originally said there was no `AGENTS.md`: if a repository also used
another AI tool, its instruction file was written by hand and said the same fifteen
things `CLAUDE.md` says. That was wrong in practice for one reason — nobody writes it,
and nobody rewrites it when the fifteen lines change. What actually happened was a
repository where Claude Code had the map and Cursor had a stale copy of half of it.

So `edify init new` writes them all, and `edify init` keeps whichever ones exist current.
The table lives in `src/edify/agents.py`, one row per runtime:

| runtime | instruction file | commands land in |
|---|---|---|
| Claude Code | `CLAUDE.md` | `.claude/commands/`, `.claude/skills/`, `.claude/agents/` |
| OpenAI Codex | `AGENTS.md` | `.codex/prompts/` |
| Cursor | `AGENTS.md`, `.cursor/rules/edify.mdc` | `.cursor/commands/` |
| Gemini CLI | `GEMINI.md` | `.gemini/commands/` (TOML) |
| GitHub Copilot | `.github/copilot-instructions.md` | `.github/prompts/` |
| Windsurf | `.windsurf/rules/edify.md` | `.windsurf/workflows/` |
| anything else | `AGENTS.md` | — |

Three properties hold this together. **One block, many files** — every instruction file
carries the identical `edify:begin`/`edify:end` block, so two tools open on one
repository cannot be running two methodologies, and `AGENTS.md` is written once no
matter how many rows name it. **Pointers, never copies** — each command file names
`.edify/commands/<name>.md` and stops; the method stays in one place and a rename cannot
leave six files lying. **A marker decides ownership** — everything generated carries
`edify:generated`, which is what makes a file EDIFY's to replace and a hand-written one
untouchable, and it is the *text* that is checked rather than the comment syntax, since
a TOML command file cannot hold an HTML comment.

**`profile.md` is the one file here nobody derived.** Everything else in the installed
tree is a function of files already on disk. This one is eight answers a person typed
when `edify init new` asked: who they are, what is being built, what done looks like,
how much to explain, and what an agent must never do in this repository. It is recorded
in the ledger under its own origin, `answered`, which nothing EDIFY does later will
overwrite. Where there is no terminal to ask at, the file does not exist and every
instruction file omits the section that points at it.

**Selection at install.** `edify init` detects the stack — languages, frameworks,
test runner, package manager — and installs only the skill entries whose `tech` field
matches, plus the role entries every repository needs. A Python API repository does
not receive the React implementer. Every unused skill file is context cost and, for
anything sourced from outside, attack surface.

## 3. `CLAUDE.md` — the whole file

Fifteen lines. This is not a summary of a longer file; it is the file.

```markdown
# <repo name>
<what this is, one line>  ·  Stack: <languages + versions, one line>

## Commands
/spec   — write the spec before anything else
/plan   — technology decisions and milestones, for work that needs them
/tasks  — turn an approved spec into the phased build plan
/build  — execute an approved plan, start to finish
/verify — re-run everything and produce the evidence

## The codebase map
.edify/graph/ — every symbol, route, and table, with the edges between them.
  edify graph where <name>        → file:line and signature
  edify graph dependents <symbol> → everything that breaks if it changes
Search the graph before reading files. Never guess a path.

## Where things live
Features: specs/<feature>/   Skills: .edify/skills/   Servers: .edify/mcp.md
```

**What is never in it:** code standards, workflow prose, subagent routing tables,
tool lists, version pins, inlined skill content, or anything that will be wrong in a
month. Pressure to add a line means the graph or the spec is missing something — fix
that.

**Why it is this short.** Prose instructions degrade as a conversation grows and go
stale with every model release. A path to a mechanically regenerated data file does
neither. Everything a session needs to know about the codebase is derivable from the
graph on demand; everything it needs to know about the current work is in the spec
and the plan. A root file carrying either would be wrong within a month and consulted
for a year.

## 4. What deliberately has no folder

- **No `knowledge/`.** Derivable knowledge is derived into the graph. Knowledge that
  is not derivable — why something is the way it is, what is dangerous to touch — is
  a short dated section in the spec, and it is the only prose about the codebase the
  system trusts.
- **No per-tool source trees.** One canonical tree. Per-tool output, if it ever
  exists, is written not generated.
- **No policy tree.** No constitution, tiering table, capability profile, or waiver
  file. What survived is the spec's `## Stack and constraints` section.
- **No staging area in a client repository.** Untrusted third-party text is handled
  in EDIFY's own repository, behind a human, and never in a customer's tree.
- **No server, no database, no daemon.** Files, and a binary that reads them.
