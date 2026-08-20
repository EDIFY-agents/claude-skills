# 06 — The Graph

The on-disk form, the extractor, the queries, and the freshness rules. Rationale is in
`../06-the-graph.md`.

---

## 1. On disk

```
.edify/graph/
  nodes.tsv    id \t kind \t file \t line \t name \t fingerprint
  edges.tsv    from-id \t relation \t to-id
  meta         commit, extractor, extractor-version, languages-covered, checksums
```

**Node kinds:** `file` `module` `symbol` `route` `table` `package` `doc-section`
**Edge kinds:** `defines` `references` `imports` `exposes` `documents` `migrates`

Both files are **sorted and checksummed**, so a rebuild on unchanged source produces
byte-identical output. That property is what makes a graph diff a structural diff of
the codebase, and what makes "did the graph change?" a `cmp`, not an analysis.

Ids follow the naming conventions of the established code-indexing standard, so an
existing indexer for a language we do not cover can be pointed at this format without
translation. The standard is the input dialect; the TSV is the contract.

**Granularity is the public surface.** Exported symbols, routes, tables, modules,
files — not local variables. Locals churn on every commit, would multiply the index
roughly tenfold, and answer questions a model resolves better by reading the function.

**Scale.** Roughly a hundred thousand exported symbols for a million lines of code.
Sorted TSV at that size answers a lookup in well under a second with `awk` or a binary
search, on a laptop, with no index server and nothing running in the background.

## 2. The queries

Four commands. Everything the system asks reduces to these.

| query | answers | used by |
|---|---|---|
| `edify graph where <name>` | file, line, signature | `/tasks` placing a task; any agent resolving a reference |
| `edify graph dependents <symbol>` | everything that breaks if this changes | `/tasks` computing a complete file set |
| `edify graph overlap <files-a> <files-b>` | do these two sets intersect, including dependents | `/tasks` marking parallel-safe tasks |
| `edify graph defines <file>` | what this file exports | an agent checking whether a helper already exists |

Each is a scan or a binary search over sorted text. No model, no network, no state.

**The rule these exist to enforce:** an agent never explores the codebase to answer a
structural question the graph already answers. Exploration is the largest token
line-item in agentic coding and the largest source of two sessions reaching different
conclusions about the same repository.

## 3. The extractor

A pinned third-party binary, wrapped. The requirements it has to meet, in priority
order:

1. **Deterministic.** No model anywhere in the indexing path.
2. **Zero dependencies, single artifact.** It has to run on a locked-down machine
   without a procurement conversation.
3. **Syntax-tree based**, not regex heuristics.
4. **Broad language coverage**, with the gaps visible rather than papered over.
5. **Fast enough to re-run per directory** after each build phase.

The candidate identified in the previous design's research — a static C binary with no
dependencies, tree-sitter parsing, and coverage in the hundred-and-fifty-language
range — meets all five and is the one to evaluate first. **Adoption is blocked on a
license and provenance review.** If that review fails, we write a small tree-sitter
extractor to the same TSV contract; the contract is the thing we own, and the
extractor is replaceable by construction.

We wrap it as a batch extractor that emits our three files. We do not run it as a live
service inside sessions, and we do not use its semantic or vector search — every query
in §2 is exact.

**Where a language is not covered, the graph has no nodes for it.** That gap is
visible in `meta`'s `languages-covered` field and is honest. It is never filled by
asking a model to describe the code, at any stage, for any reason. One narrated edge
and everything downstream is resting on a guess wearing the costume of a fact.

## 4. Freshness

| when | what runs |
|---|---|
| `edify init` | full extraction |
| after each build phase | `edify graph update <changed dirs>` |
| end of a build | full extraction |
| session start | compare `meta.commit` to HEAD; print one line if it has moved |

The per-phase update is the anti-fragmentation mechanism reduced to one step: it is
what lets phase 4 see the symbols phase 2 created, and without it later work reinvents
earlier work inside the same run.

**Stale is worse than absent.** An absent graph makes an agent explore, which is slow
and obvious. A stale graph makes it confident and wrong, which is expensive and
discovered later. Hence the session-start check is a visible line, not a silent
fallback.

## 5. What is deliberately not built

- **No graph database, no server, no daemon.** Sorted text and a binary.
- **No embeddings, no vector search.** Semantic similarity answers a question this
  system does not ask.
- **No variable-level indexing.** Churn exceeds value.
- **No agent-written nodes or edges, ever.** This is the invariant the whole value
  rests on.
- **No semantic sidecar.** The previous design carried a second edge file for
  relationships the pipeline discovered — decision-to-module, task-to-table. With
  seven artifacts collapsed into two, those relationships are simply columns in
  `tasks.md`, where a human can read them.
