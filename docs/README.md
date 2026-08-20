# EDIFY documentation

**Your coding agent is fast. Make it reliable.**

---

## Start here

| | |
|---|---|
| [**Quickstart**](quickstart.md) | install → `init` → one real task, in about ten minutes |
| [**Install**](../INSTALL.md) | per-platform detail, PATH fixes, where EDIFY keeps its files |
| [**Troubleshooting**](troubleshooting.md) | what `edify doctor` is telling you |
| [**FAQ**](faq.md) | the questions people actually ask first |

## Using it

| | |
|---|---|
| [**CLI reference**](cli.md) | every command, with real output |
| [**The codebase graph**](graph.md) | what it maps, what it covers, and what it refuses to guess |
| [**Verification**](verification.md) | why correct is defined before implementation |
| [**Works with your agent**](agents.md) | Claude Code, Codex, Cursor, Gemini CLI, Copilot, Windsurf |

## Trust

| | |
|---|---|
| [**Privacy and offline behaviour**](privacy.md) | no telemetry, and the two commands that open a socket |
| [**Benchmarks**](benchmarks.md) | same model, same repo, same task — methodology, in public |
| [**Pricing**](pricing.md) | five gates, and why each one exists |
| [**Licence, in plain English**](license.md) | what FSL lets you do, and the two-year Apache 2.0 conversion |
| [**Security policy**](../SECURITY.md) | scope, reporting, and what is deliberately out of scope |

## How it was designed

The [`design/`](design/) dossier is the source of truth for this project — the
reasoning, not the marketing.

| | |
|---|---|
| [`01-principles.md`](design/01-principles.md) | the eight laws every decision here satisfies |
| [`02-system-overview.md`](design/02-system-overview.md) | how the pieces fit |
| [`03-the-spec.md`](design/03-the-spec.md) · [`04-the-plan.md`](design/04-the-plan.md) · [`05-the-tasks.md`](design/05-the-tasks.md) | the three documents |
| [`06-the-graph.md`](design/06-the-graph.md) | the map |
| [`07-verification.md`](design/07-verification.md) | evidence over assertion |
| [`08-agents-and-skills.md`](design/08-agents-and-skills.md) | spawning and the curated library |
| [`09-context-and-mcp.md`](design/09-context-and-mcp.md) | what gets loaded, and when |
| [**`10-what-we-dropped.md`**](design/10-what-we-dropped.md) | **every cut, why, and what it cost** |
| [`architecture/`](design/architecture/) | the buildable blueprint — formats, CLI, graph, harvest |

> `10-what-we-dropped.md` is the one to read if you are deciding whether to trust
> this project. A design dossier that lists only what was added is a sales
> document.

## Contributing

[CONTRIBUTING.md](../CONTRIBUTING.md) · [GOVERNANCE.md](../GOVERNANCE.md) ·
[CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) · [TRADEMARK.md](../TRADEMARK.md)

The fastest useful contribution is running EDIFY on one real task and telling us
what broke.
