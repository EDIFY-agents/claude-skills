# CLI reference

`edify` installs the harness, builds and queries the graph, resolves skills, and
checks formats. It is a pure function over files: every command reads files and
writes files, and none holds state or opens a socket while doing your work.

Global flags: `--repo PATH` · `--json` · `--no-color` · `--quiet` · `--version`

---

## Install

| command | what it does |
|---|---|
| `edify init` | install the harness into this repository (asks which skills) |
| `edify init --yes` | …the whole matched set, no question |
| `edify init --skills a,b` | …exactly these entries; `none` for none |
| `edify init new PATH` | a folder from zero, for **every** agent runtime — asks first |
| `edify init new . --agents claude,cursor` | only these runtimes |
| `edify setup PATH` | pin the root here, create the folder if missing, install everything |
| `edify setup . --fresh` | clear EDIFY's own files first, leave everything else |

`init` finds its root by walking upward, so a new folder inside an existing
checkout installs into the parent. `setup` pins the root where you point it.

## The graph

| command | what it answers |
|---|---|
| `edify graph build` | full extraction |
| `edify graph build --extractor ctags` | parse-grade precision beyond Python |
| `edify graph where NAME` | where is this — file, line, kind |
| `edify graph dependents NAME` | everything that breaks if it changes |
| `edify graph defines FILE` | what this file exports |
| `edify graph references NAME` | who calls or imports this |
| `edify graph overlap "a.ts b.ts" "c.ts"` | can these two tasks run at once |
| `edify graph stat` | nodes, edges, files, languages, coverage |

···  `edify graph where` · `dependents` · `defines`

<img src="../assets/graph-where.svg" alt="edify graph queries" width="100%">

See [graph.md](graph.md) for what is covered and what is not.

## The documents

| command | what it does |
|---|---|
| `edify check` | report what is wrong with the spec, plan, and task list |
| `edify check --fix` | fix what can be fixed mechanically |
| `edify check --exit-code` | non-zero on error — this is how you make a CI gate |
| `edify check --json` | machine-readable findings |

···  `edify check`

<img src="../assets/verify.svg" alt="edify check output" width="100%">

**Nothing blocks.** `edify check` prints; a person or a CI job decides what that
means. If you need a hard block, that is `--exit-code` or `/verify` in your own
CI, owned by you.

## Skills and servers

| command | what it does |
|---|---|
| `edify skills list` | the installed library, with role, phase, tech, budget |
| `edify skills resolve implementer 4` | the one file a spawn at that phase loads |
| `edify skills add NAME` | install one entry from the library |
| `edify skills sync` | rewrite the per-runtime mirror after a hand edit |
| `edify mcp list` | the server registry |
| `edify mcp for implementer 4` | what servers that spawn would load |

## Governance

| command | what it does |
|---|---|
| `edify governance list` | every file EDIFY installed: origin, provenance, licence, hash |
| `edify governance verify` | is it still what was installed |
| `edify governance verify --exit-code` | …as a gate you own |
| `edify governance rebuild` | re-baseline after a deliberate change |

···  `edify governance list` · `verify`

<img src="../assets/governance.svg" alt="edify governance output" width="100%">

`verify` separates a file EDIFY owns being changed — `upgrade` will overwrite it
— from a file your repository owns being maintained, which is what `.edify/mcp.md`
and `.edify/conventions.md` are for. The graph is deliberately not in the ledger:
it is regenerated output and carries its own checksums.

## Health, licence, feedback

| command | what it does |
|---|---|
| `edify doctor` | does the install work here |
| `edify self where` | which `edify` is this, and where did it come from |
| `edify self update` | replace the binary — hands fetching to uv, pipx, or pip |
| `edify self update --offline` | refuse to touch the network |
| `edify license status` | plan, entitlements, and limits |
| `edify license projects` | which repositories are using a free slot |
| `edify license projects forget PATH` | release one |
| `edify license buy --seats N` | opens a browser, not a socket |
| `edify license activate TOKEN` | the token you were emailed — verified locally |
| `edify feedback` | four questions, written to a file on this machine |
| `edify feedback list` | what you have written; none of it has been sent |
| `edify feedback off` | never show the invitation again |
| `edify upgrade` | pull a newer curated library and re-index |
| `edify upgrade --from ARCHIVE` | …from a local file, for an air-gapped machine |

···  `edify license status`

<img src="../assets/license.svg" alt="edify license status" width="100%">

## The two commands that open a socket

`edify upgrade` and `edify self update`. That is the complete list, it is
[enforced in CI](../.github/workflows/guard.yml), and both have an offline path.
See [privacy.md](privacy.md).
