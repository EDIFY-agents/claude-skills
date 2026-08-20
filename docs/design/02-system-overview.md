# 02 — System Overview

EDIFY is three documents, a map, two small registries, and five commands that produce
and consume them. There are no engines, no planes, and no policy tree. This document is
the whole system in one read; the rest of the folder is detail.

---

## 1. The three documents

**`specs/<feature>/spec.md`** — what is being built and why. Written once per feature by
a frontier model working from a short brief, argued with by a second model that has
never seen the draft, and approved by a human. It carries the intent, the testable
assertions, everything the feature entails that nobody asked for, the open questions,
and the non-goals. It is the only place a human writes product judgment into the system,
and a non-engineer can read it. Detail: `03-the-spec.md`.

**`specs/<feature>/plan.md`** — how, with what, and in what order. The technology
decisions, each naming the alternative it beat. The milestones and the dependency rules
between them. The cross-cutting strategy nothing else can own: migration numbering, build
variants, bundled assets, shared components. The risks, each mapped to the milestone that
mitigates it. Written for features large enough to need it, skipped for the ones that are
not. Detail: `04-the-plan.md`.

**`specs/<feature>/tasks.md`** — exactly what will change, where, in what order.
Structured in phases; each task names its files and line ranges, the pattern to follow,
the numbered steps, and the check that proves it worked. Complete enough that following
it requires no judgment. Detail: `05-the-tasks.md`.

## 2. The map and the two registries

**`.edify/graph/`** — a mechanically extracted map of the codebase: every file, module,
exported symbol, route, and table, with the edges between them, as sorted text. Never
written by a model. It is how a plan gets line-accurate references without exploring,
and how an agent mid-task answers a structural question in a millisecond instead of a
thousand tokens. Detail: `06-the-graph.md`.

**The skill library** — short, plain descriptions of how to do a particular kind of
engineering work, in a metadata format that makes them findable by exact lookup rather
than by a model reading through them. Spawning an agent means: look up the skill for
this task's role, load that file, load the task block, launch. Nothing else. That is
the entire agent architecture. Detail: `08-agents-and-skills.md`.

**The MCP registry** — the servers this repository may reach for things that are not in
it: current library documentation above all, plus whatever the team's own systems
require. Declared once, pinned, and **scoped to the roles and phases that need them**
rather than connected globally. Detail: `09-context-and-mcp.md`.

## 3. The five commands

| command | what it does | model | ends at |
|---|---|---|---|
| `/spec` | brief → specification | strongest | a human |
| `/plan` | spec + graph → technology decisions and milestones | strongest | a human |
| `/tasks` | spec + plan + graph → phased task list | strongest | a human |
| `/build` | task list → working software | cheapest that follows instructions | a diff and a green suite |
| `/verify` | the code → evidence | strong; never a session that wrote code | a report anyone can read |

Plus two that run themselves: `/graph`, which is a binary and never a model, and
`/harvest`, which stocks the skill library and lives in EDIFY's own repository rather
than a client's.

The shape of a normal day: `/spec`, read it, approve. `/plan` if the work is large
enough to need one. `/tasks`, read it, approve. `/build`, go get coffee. `/verify` runs
inside the build and again in CI, and anyone can run it by hand at any time.

## 4. The life of one feature

**Setup, once per repository.** `edify init` detects the stack, runs the extractor to
build the graph, installs the subset of skill files this repository's stack actually
matches, seeds the MCP registry with the documentation server, and writes a fifteen-line
`CLAUDE.md` whose main content is a pointer to the graph. There is no interview, no
constitution, and no governance level to choose.

**Specify.** The developer runs `/spec` with a couple of sentences. The command reads
the graph rather than exploring, drafts the spec, then launches one adversary agent whose
only input is the original brief and the draft, and whose only job is to find what the
brief did not say: the ambiguity, the platform duty nobody mentioned, the error state
with no defined behavior. Its findings land in the closure checklist and the open
questions. The human resolves them or accepts the defaults on the record, and approves.
This is the expensive step and it is meant to be — everything downstream is paid for
again if this is wrong.

**Plan.** For work that introduces a technology, spans milestones, or needs cross-cutting
strategy, `/plan` makes those choices once and writes down what each beat. For everything
else this step is skipped, and skipping it is the normal case.

**Task.** `/tasks` reads the approved spec, the plan if there is one, and the graph, and
writes the phased task list. Every requirement maps to at least one task; every task maps
back to a requirement. Every task names its files with line ranges, resolved against the
graph. The human reads it — the last cheap moment to disagree — and approves.

**Build.** `/build` executes the whole list in one run, phases in order. Phase 2 is
verification: every assertion in the spec becomes a failing executable test before any
core logic exists. Everything after that is making red tests green, which is what lets a
cheap model work reliably — it is not judging its output, it is hitting a target.
Within a phase, tasks whose file sets do not overlap run in parallel. After each phase
the exit check runs and the graph is re-extracted for the directories that changed.

**Prove.** The last phase is `/verify` in a fresh session that wrote none of the code:
the suite re-run rather than trusted, the acceptance scenarios exercised as real flows,
the coverage table walked row by row, and one human-shaped judgment — is this one design
or several?

**When the plan is wrong.** It sometimes is. The builder is forbidden from adapting, so
it stops, writes one line into the task list saying what it found and which task it
contradicts, and continues with tasks that do not depend on the broken one. The developer
re-runs `/tasks` scoped to the affected phase. Replanning is cheap, normal, and visible —
not a crisis and not an improvisation.

## 5. How the four failures get fixed

**Blindness.** The graph replaces exploration. A planner asks where a symbol is defined
and who depends on it; a builder asks whether a helper already exists. Both get an answer
in milliseconds from sorted text, identical every time, with no model in the path.

**Fragmentation.** Two mechanisms, both cheap. The plan is written whole before any code
exists, so the design is decided once by one mind rather than seventeen times by seventeen
sessions. And `/build` runs the whole plan in one session, so there is no session boundary
to lose coherence across; where a decision does get made mid-run, it is appended to the
task list and every later spawn carries it.

This is a real change in strategy. The previous design accepted fragmentation as
inevitable and built machinery to detect and repair it. The new design mostly avoids it
instead. The repair machinery shrinks to one section and one final review, because there
is much less to repair.

**Wrong thing built.** The adversary at spec time, and three human gates before any code
exists. Two of them cost a person five minutes.

**Invented interfaces.** The plan names the library and the version; the documentation
server makes that version's real API available at the moment a builder needs it. Neither
half works alone.

## 6. What a repository looks like after installation

```
CLAUDE.md              # ~15 lines: what this repo is, the commands, where the graph is
.edify/
  graph/               # nodes.tsv, edges.tsv, meta — mechanical, regenerable
  skills/              # the matched subset of the library, one file each
  index.tsv            # the lookup table over those skills
  mcp.md               # the server registry: pinned, scoped per role and phase
specs/
  <feature>/
    spec.md
    plan.md            # when the feature needs one
    tasks.md
```

Seven paths. Compare the previous design's client tree: two root files, ten `.edify`
subfolders, two compiled tool targets, and eight artifacts per feature.

There is nothing to commit-or-not-commit, nothing machine-local, no ledger, no audit
chain, no session folder, no memory folder with expiry metadata. `.edify/graph/` is
regenerable and may be committed or ignored by taste. Everything else is source.

## 7. What EDIFY still does not do

It does not wrap the agent runtime, host a model, or route between providers. It does not
run a server. It does not enforce anything at runtime. It does not manage dependencies,
deploys, or CI. It does not attempt to make a weak model competent — it makes a competent
model efficient, and the difference is the whole product.
