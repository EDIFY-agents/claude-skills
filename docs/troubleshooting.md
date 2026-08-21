# Troubleshooting

Start here, always:

```bash
edify doctor
```

It names what is wrong and why, in one line each. Everything below is a longer
version of one of those lines.

···  `edify doctor`

<img src="../assets/doctor.svg" alt="edify doctor output" width="100%">

---

## `edify: command not found`

The install worked; the shell cannot see it.

```bash
pipx ensurepath        # then open a new terminal
```

If you installed with `pip --user`, the directory is `python -m site --user-base`
plus `/bin` (or `\Scripts` on Windows). [INSTALL.md](../INSTALL.md) has the
per-platform detail.

```bash
edify self where       # which edify is this, and where did it come from
```

## `edify doctor` says **degraded · extractor**

Expected, and not an error. It means the built-in scanner is in use: Python is
parsed exactly, everything else is scanned. For parse-grade precision across the
rest:

```bash
brew install universal-ctags        # macOS
sudo apt install universal-ctags    # Debian / Ubuntu
edify graph build --extractor ctags
```

## `edify doctor` says **degraded · governance**

One or more files EDIFY installed have changed since install.

```bash
edify governance verify     # which files, and how they differ
```

- **You changed it on purpose** (a skill entry, `mcp.md`, `conventions.md`) —
  fine. `edify governance rebuild` re-baselines.
- **You did not** — `edify init --force` reinstalls EDIFY's own files and leaves
  everything else alone.

Note the difference `verify` is drawing: a file EDIFY owns being changed means
`upgrade` will overwrite it. A file your repository owns being maintained is what
`.edify/mcp.md` and `.edify/conventions.md` are *for*.

## `edify graph where` finds nothing

Work down this list:

```bash
edify graph stat            # is the language covered at all
edify graph build           # is the graph stale
```

1. **The language is not covered.** `graph stat` and `.edify/graph/meta`
   (`languages_uncovered`) will say so. The graph never invents a node, so a gap
   is visible rather than wrong.
2. **The graph is stale.** `edify graph build` re-extracts.
3. **The symbol is not exported** — the graph carries declarations, not every
   local binding.
4. **It should have been found.** That is a
   [graph gap](../.github/ISSUE_TEMPLATE/graph_gap.yml), and it is the most
   valuable issue you can file. Include the declaration verbatim.

## `/spec` does not exist in my agent

The command files land in each runtime's own directory, and `edify init` only
writes Claude Code's.

```bash
edify init new . --agents cursor,codex,gemini
edify skills sync     # if you added or removed an entry by hand
```

Check what your runtime reads in [agents.md](agents.md). Some tools need a
restart to notice new command files.

## The graph is huge / hits the free cap

The free tier covers 25,000 nodes. If you are over it:

```bash
edify graph stat            # where the nodes actually are
```

Vendored code, generated clients, and build output are the usual cause.
`.edify/graph/` respects your `.gitignore` plus its own ignore rules — see
[`src/edify/graph/ignore.py`](../src/edify/graph/ignore.py). Excluding generated
directories usually brings a repo well under the cap and produces a *better* map,
because generated code was never useful to the agent anyway.

If the repository is genuinely that large, that is the population EDIFY exists
for — see [pricing.md](pricing.md).

## `edify init` installed into the wrong directory

`init` finds its root by walking upward, so a new folder inside an existing
checkout installs into the parent. That is usually what you want, and sometimes
not.

```bash
edify setup ./service --yes    # pin the root exactly here
edify --repo ./service doctor  # or aim a single command
```

## Everything is broken and I want a clean install

```bash
edify setup . --fresh --yes
```

Clears EDIFY's own files first and leaves everything else — including a skill or
command you wrote by hand — exactly where it was.

## Something else

- [Discussions](https://github.com/EDIFY-agents/edify_public/discussions) — questions, answered in public.
- [Issues](https://github.com/EDIFY-agents/edify_public/issues/new/choose) — with `edify doctor` output and a
  reproduction.
- A **security** problem: do not open an issue. See [SECURITY.md](../SECURITY.md).
