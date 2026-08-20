# The codebase graph

**A map extracted from your code. Not invented by another model.**

Every file, module, exported symbol, route and table, with the edges between
them, as sorted checksummed text. A rebuild over unchanged source is
byte-identical, so a graph diff is a structural diff of the codebase.

---

## What it answers

```bash
edify graph where isExpired            # → src/auth/clock.ts:12  symbol  isExpired
edify graph dependents createSession   # everything that breaks if it changes
edify graph defines src/api/router.ts  # what this file exports
edify graph references generate        # who calls or imports this
edify graph overlap "a.ts b.ts" "c.ts" # can these two tasks run at once
```

···  `edify graph where` · `dependents` · `defines`

<img src="../assets/graph-where.svg" alt="edify graph queries" width="100%">

These are the questions an agent otherwise answers by reading files until it
runs out of context — every session, from scratch, slightly differently each
time.

## It is never written by a model

Not at install, not as a fallback, not for a language the extractor does not
cover.

Where a language is not covered, the graph has **no nodes for it**, and
`meta.languages_uncovered` says which. A missing symbol is a visible gap. An
invented one is a guess wearing the costume of a fact, and it is worse than
nothing, because the agent will trust it.

```bash
edify graph stat        # nodes, edges, files, and which languages are covered
cat .edify/graph/meta   # including method_<language>: parsed or scanned
```

## Coverage, stated honestly

| | how | precision |
|---|---|---|
| Python | real syntax tree (`ast`) | exact |
| everything else, by default | declarative line scanner | good, not exact |
| everything else, with ctags | Universal Ctags | parse-grade |

`meta.method_<language>` records which was used, so **a scan is never mistaken
for a parse**. For parse-grade precision across the rest:

```bash
# macOS: brew install universal-ctags   ·   Debian: apt install universal-ctags
edify graph build --extractor ctags
```

The TSV contract is the asset; the extractor is replaceable by construction. If
your language is missed or mis-located, that is a
[graph gap report](../.github/ISSUE_TEMPLATE/graph_gap.yml) — the most useful
issue this project receives.

## What lands on disk

```
.edify/graph/
  nodes.tsv     one line per file, module, symbol, route, table
  edges.tsv     one line per relationship, sorted
  meta          counts, languages, extraction method, checksums
```

Sorted, checksummed, plain text. It is regenerable, so commit it or ignore it by
taste — `.gitignore` ignores it by default. Committing it makes structural change
visible in review; ignoring it keeps diffs quiet.

The graph is deliberately **not** in `.edify/governance.tsv`: it is regenerated
output and carries its own checksums.

## How the agent uses it

`CLAUDE.md` (and `AGENTS.md`, `GEMINI.md`, and the rest) points at it in about
three lines:

```markdown
## The codebase map
.edify/graph/ — every symbol, route, and table, with the edges between them.
  edify graph where <name>        → file:line and signature
  edify graph dependents <symbol> → everything that breaks if it changes
Search the graph before reading files. Never guess a path.
```

That is the whole integration. The agent runs a command and gets a location
instead of burning context rediscovering the repository.

## Size

The free tier covers graphs up to **25,000 nodes** — roughly a 200–300k-line
repository. Below that a frontier model in auto mode is already good and EDIFY is
genuinely optional, which is why the free plan is complete there. See
[pricing.md](pricing.md).

## Design detail

[`docs/design/06-the-graph.md`](design/06-the-graph.md) is the reasoning;
[`docs/design/architecture/06-graph.md`](design/architecture/06-graph.md) is the
buildable contract, including the TSV schema and the extractor interface.
