# FAQ

---

### Is this another coding agent?

No. EDIFY does not host a model, wrap an agent runtime, or route between
providers. It gives the agent you already use better context, an explicit plan,
and independent verification. If you cancel your Claude Code or Cursor
subscription, EDIFY does nothing at all.

### Does it work with the agent I use?

Claude Code, OpenAI Codex, Cursor, Gemini CLI, GitHub Copilot, Windsurf, and
anything that reads `AGENTS.md`. See [agents.md](agents.md). One `edify init new`
sets a folder up for all of them at once.

### How is this different from Spec Kit?

Spec Kit is the closest free alternative and it is a good tool. The differences
that matter:

- **The graph.** EDIFY mechanically extracts a map of your codebase — symbols,
  routes, tables, and the edges between them — so the agent asks a question
  instead of reading files until it runs out of context. Nothing in that map is
  ever written by a model.
- **Verification-first.** Phase 2 of every build turns spec assertions into
  failing tests before any core logic exists, and `/verify` runs in a session
  that wrote no code.
- **Agent-agnostic by construction**, not by porting.

The honest answer to "which is better" is a
[benchmark](benchmarks.md) that has not finished running. When it has, it will be
published including the tasks where EDIFY loses.

### Does it send my code anywhere?

No. There is no telemetry of any kind, and exactly two commands open a socket —
`edify upgrade` and `edify self update` — both by explicit user action, both with
an offline path. This is [enforced in CI](../.github/workflows/guard.yml) and you
can grep for it yourself. See [privacy.md](privacy.md).

Your *agent* sends code to its vendor; that is your contract with them, and EDIFY
is not in the path.

### Will it slow me down?

Yes, for the first three commands. `/spec`, `/plan`, and `/tasks` are slow and
expensive and end at a human reading them. `/build` is fast and cheap.

That is the trade the whole product makes: think hard once, then build without
thinking. If your task is small enough that thinking once is not worth it, EDIFY
is ceremony and you should not use it for that task.

### Is it worth it for a small project?

**No, and we would rather say so.** A frontier model in auto mode is already
excellent on a small codebase. The value starts where the codebase stops fitting
in the context window — roughly, where you have stopped being able to explain the
repository to a new hire in an afternoon.

### What does it cost?

Free, forever, with no account, up to a 25,000-node graph (~200–300k lines), one
server in the registry, and three projects on one machine. Above that, $20 per
user per month. Five gates and only five. See [pricing.md](pricing.md).

### Can I remove the licence check?

Technically, yes — the source is readable and the check is local. We say that
plainly rather than pretending otherwise, because breaking offline operation to
defend against it would cost every honest user something real.

Paying is a contract, not a technical protection measure. What actually stops a
*company* from reselling EDIFY is [the licence](../LICENSE) and
[the trademark](../TRADEMARK.md).

### Is it open source?

It is **source-available**, under the [Functional Source
License](license.md), and every version becomes Apache 2.0 two years after
release. We do not call it open source, because it is not OSI-approved and
claiming otherwise would be a false claim on the first page.

### What languages does the graph cover?

Python is parsed with a real syntax tree. Everything else is covered by a
declarative line scanner, or parse-grade if you install Universal Ctags. A
language the extractor does not cover has **no nodes at all** rather than guessed
ones — `edify graph stat` names the gaps. See [graph.md](graph.md).

### Does it need a network, a server, or a database?

None of the three. No daemon, no database, no account, no runtime dependencies —
`[project] dependencies` is empty and stays empty. Python 3.10+ is the whole
requirement.

### Does it block bad changes?

No, and this is deliberate. `edify check` prints; you or your CI decide what that
means. `--exit-code` is how you build a gate **you** own. EDIFY does not claim
enforcement it does not have —
[`10-what-we-dropped.md`](design/10-what-we-dropped.md) records the enforcement
machinery that was cut and what the cut cost.

### Can I use it in CI?

Yes, and it is designed for it. With no terminal, nothing is asked, nothing is
written outside the repository, and the full install happens anyway. A question
is never load-bearing.

```yaml
- run: edify check --exit-code
- run: edify governance verify --exit-code
```

### Who is behind this, and what if you disappear?

EDIFY, a single-vendor project — see [GOVERNANCE.md](../GOVERNANCE.md), which
says so plainly rather than describing a steering committee that does not exist.

If the project is abandoned: every published version still converts to Apache 2.0
on schedule, the methodology tree is plain Markdown that works without the CLI,
and the graph is documented checksummed TSV any tool can read.

### How do I help?

Run it on one real task and tell us what broke — `edify feedback`, or an
[issue](https://github.com/EDIFY-agents/edify_public/issues/new/choose). A [graph gap](../.github/ISSUE_TEMPLATE/graph_gap.yml)
report is the single most valuable thing we receive.
