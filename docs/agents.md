# Works with your agent

**EDIFY is not another coding agent. It makes your existing one more reliable.**

It does not wrap the agent runtime, host a model, or route between providers. The
five commands are Markdown files installed where your tool already looks for
commands, and the graph is a CLI your agent shells out to. That is the whole
integration surface, which is why adding a runtime is a day rather than a
quarter.

---

## Supported runtimes

| runtime | reads | commands land in | message |
|---|---|---|---|
| **Claude Code** | `CLAUDE.md` | `.claude/commands/`, `.claude/skills/`, `.claude/agents/` | works with your existing agent |
| **OpenAI Codex** | `AGENTS.md` | `.codex/prompts/` | same workflow, different runtime |
| **Cursor** | `AGENTS.md`, `.cursor/rules/edify.mdc` | `.cursor/commands/` | EDIFY adds structure around the agent |
| **Gemini CLI** | `GEMINI.md` | `.gemini/commands/` (TOML) | agent-agnostic workflow |
| **GitHub Copilot** | `.github/copilot-instructions.md` | `.github/prompts/` | use the agent you already pay for |
| **Windsurf** | `.windsurf/rules/edify.md` | `.windsurf/workflows/` | broad compatibility |
| **anything else** | `AGENTS.md` | — | the open standard, supported |

## Installing for all of them at once

`edify init` writes `CLAUDE.md` and `.claude/`. That install is invisible to the
five other tools your team has open.

```bash
edify init new ./service              # every runtime EDIFY knows — asks first
edify init new . --agents claude,cursor
edify init new . --yes                # ask nothing, install everything
```

`init new` pins the root where you point it, clears EDIFY's own files first,
installs every library entry, and writes the same block into every instruction
file each runtime actually reads.

**And it asks first.** Detection reads your `pyproject.toml`; it cannot read that
this is a rewrite of something already in production, or that nothing may touch
migrations without a plan. Eight short questions, before anything is written,
because two of them decide what gets installed. The answers go to
`.edify/profile.md`, which every instruction file points at and which is yours to
edit. Press enter to skip any of them.

With no terminal — CI, a pipe, a model calling the binary — nothing is asked, no
profile is written, and the full install happens anyway. **A question is never
load-bearing.**

A later `edify init` keeps every runtime already set up in the folder current,
rather than updating `CLAUDE.md` and leaving the other five stale.

## One methodology, many front doors

The five commands are installed once, to `.edify/commands/`, with thin pointers
under each runtime's own command directory. `/spec` resolves in whichever tool
you are typing into while the methodology stays in exactly one place.

The skill library is mirrored the same way — `.claude/skills/<name>/SKILL.md` per
entry, carrying the description the runtime matches on and pointing at
`.edify/skills/<name>.md`. An installed entry is discoverable in the session you
are typing into and still exists in one place.

```bash
edify skills sync    # rewrite the mirror if you add or remove an entry by hand
```

## What your agent sees

About fifteen lines in the instruction file. Not a constitution:

```markdown
# your-service
Stack: python · Tests: pytest

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

## Adding a runtime

The per-runtime knowledge is a table of "what file does it read, where do
commands go" in [`src/edify/agents.py`](../src/edify/agents.py). Adding one is
adding a row and a test. If your tool is missing,
[open an issue](https://github.com/EDIFY-agents/edify_public/issues/new/choose) — this is one of the easiest useful
contributions available.

## Your model contract is yours

EDIFY does not host, wrap, or route to a model, so what your agent sends to
Anthropic, OpenAI, or Google is governed by your contract with that vendor, not
by us. EDIFY changes *how much* has to be sent. See [privacy.md](privacy.md).
