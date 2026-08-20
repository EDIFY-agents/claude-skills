# 06 — The Graph

**The failure it prevents:** blindness. A model cannot see a codebase it cannot fit
in its context, so every session re-derives the same map — expensively, slowly, and
slightly differently each time. Exploration is the largest single token line-item in
agentic coding and the largest source of inconsistency between sessions.

**The design goal:** any structural question about the codebase is answered in
milliseconds, identically every time, with no model in the path.

This is the piece of the previous design that survives completely intact, and it is
the only thing `CLAUDE.md` points at.

---

## 1. What it is

A mechanically extracted map of the codebase, stored as sorted text:

```
.edify/graph/
  nodes.tsv    # id  kind  file  line  name  signature-fingerprint
  edges.tsv    # from-id  relation  to-id
  meta         # the commit it was built from, the extractor and its version, checksums
```

**Node kinds:** file, module, symbol (exported function, class, constant), route,
table, package, doc-section.
**Edge kinds:** defines, references, imports, exposes, documents, migrates.

Both files are sorted and checksummed, so rebuilding produces byte-identical output
and a diff of the graph is a diff of the codebase's structure. At the scale that
matters — roughly a hundred thousand exported symbols for a million lines of code —
lookups are sub-second with ordinary text tools and no index server.

**Granularity is the public surface, deliberately.** Local variables are not indexed.
They change with every commit, they would multiply the index roughly tenfold, and
nothing consumes them: a model reads a function body better than any index describes
it. The graph exists for the questions a model *cannot* answer by reading — questions
about things it has not read.

## 2. It is never written by a model

A deterministic extractor builds it. Not at install, not later, not as a fallback,
not for a language the extractor does not cover.

This is the rule the whole value rests on. The graph is trusted precisely because no
model touched it — one narrated edge and every consumer downstream is resting on a
guess that looks like a fact. Where the extractor cannot cover a language, **the
graph simply has no nodes for that language**, and that gap is visible and honest.
Missing coverage is a tooling task. It is never a prompt.

The extractor is a pinned third-party binary whose output we own: static, zero
dependencies, works offline, parses via syntax trees rather than heuristics. If it
disappears or fails a license review, the TSV format is the contract and a
replacement is written to it. We adopt the naming conventions of the established
code-indexing standard so existing indexers can feed it, without taking that standard
on as a runtime dependency.

## 3. The three questions it answers

Everything the system asks of the graph reduces to three queries, shipped as commands
so nobody re-derives them:

- **`where <name>`** — where is this defined, what is its signature, what file and
  line. This is what turns a plan's prose into a `file:line` reference, and what lets
  a builder open exactly the right forty lines instead of the whole file.
- **`dependents <symbol>`** — everything that would break if this changed. This is
  blast radius, and it is what makes a plan's file sets complete rather than
  optimistic.
- **`overlap <task-a> <task-b>`** — do these two tasks touch intersecting sets of
  files, including dependents. This is what makes parallel execution provably safe
  instead of hopefully safe.

A fourth use needs no query of its own: before writing a new helper, ask the graph
whether one already exists. That check is why a large feature built in one pass does
not end up with three functions that do the same thing.

## 4. Freshness

The graph records the commit it was built from. Three moments keep it honest:

1. **After each phase of a build**, the directories that changed are re-extracted, so
   phase 4 can see the symbols phase 2 created. This is the mechanism that stops
   later work reinventing earlier work inside a single run.
2. **At the end of a build**, a full rebuild.
3. **At the start of a session**, a cheap comparison against the current commit. If
   the code has moved substantially, the session says so — a visible line, not a
   silent stale answer.

Stale is worse than absent. An absent graph makes an agent explore, which is slow. A
stale graph makes it confident and wrong, which is expensive later.

## 5. Why this is the only thing `CLAUDE.md` references

The root instruction file is fifteen lines: what this repository is, the three
commands, and where the graph lives with the three queries it answers. Nothing else.

Not because pointers are elegant, but because instructions rot. Prose rules degrade as
a conversation grows and go stale with every model release; a path to a mechanically
regenerated data file does neither. Everything a session needs to know about *this
codebase* is derivable from the graph on demand, and everything it needs to know about
*this feature* is in the spec and the task list. A root file that tries to carry
either is a file that will be wrong within a month and consulted for a year.

## 6. Why there is no architecture-discovery pass before the spec

A natural instinct is to add a setup step before `/spec` that studies the codebase and
writes down its architecture, its design principles, and its coding conventions — so
that everything afterwards has them. The instinct is right about the need and wrong
about the mechanism, and the difference is worth stating because it is the single
easiest place to reintroduce the previous design's landfill.

Split the thing being asked for into three parts, because they have three different
answers.

**The architecture — where everything is and what depends on what.** This is the graph.
It is already built, already mechanical, already free of tokens, and already more
accurate than any prose description of it, because it is derived rather than
interpreted. Adding an AI pass that writes an architecture document is adding a
lower-fidelity, immediately-stale copy of a file we already have.

**The coding conventions — how this codebase writes code.** Almost entirely mechanical,
and this is the part worth building. The lint configuration, the formatter
configuration, the type-checker strictness settings, the editor config, the test
framework and its layout, the commit-message convention, the package manager's lockfile,
the CI workflow's actual commands: every one of those is a file on disk stating a
convention, and reading them is a scrape, not an analysis. `edify init` produces a
fifteen-line `conventions` block from those files **with no model call at all** — which
is exactly the "without losing tokens" answer, because a config scrape costs nothing.

What the scrape cannot get — where fixtures live, which patterns are considered
finished versus legacy, the module nobody should touch — is covered better and cheaper
by the task format's `Follow the pattern at` pointer (`05-the-tasks.md` §2). Showing a
builder one place in the codebase that already does the job correctly transfers a
convention more reliably than any paragraph describing it.

**The design principles — why the architecture is the way it is.** Not derivable, and
also not worth an AI pass: a model reading the code and inferring intent produces a
plausible story, not the actual reason, and a plausible wrong story about why a system
is shaped this way is more damaging than an admitted blank. If someone on the team knows
why, that is a short human-written file, dated, kept optional. If nobody knows, empty is
the honest state and it should stay empty.

**The verdict: no setup command.** `edify init` gains a mechanical conventions scrape
alongside the graph extraction — zero model calls, a few hundred milliseconds. Nothing
else. A step whose output is one part duplicate, one part scrape, and one part
confabulation should not exist, and the temptation to add it is exactly the pressure P8
exists to resist.

## 7. What is deliberately not built

- **No graph database, no server, no daemon.** Sorted text and a binary that reads it.
  A query engine would be faster than necessary and would not run on an air-gapped
  network without a procurement conversation.
- **No embeddings, no vector search.** Semantic similarity is a good answer to a
  question this system does not ask. Every query above is exact.
- **No variable-level indexing.** Churn exceeds value.
- **No agent-written knowledge files.** The previous design's `knowledge/` folder of
  model-authored prose about the codebase, kept "fresh" by another model, is the
  landfill this replaced. Derivable knowledge is derived. Knowledge that is not
  derivable — why a thing is the way it is, what is dangerous to touch — is a short
  human-written section in the spec, dated, and it is the only prose about the
  codebase the system trusts.
