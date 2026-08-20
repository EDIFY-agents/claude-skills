# 00 — The System Graph

The whole system, wired. Everything meets at files.

---

## 1. The picture

```
                              a person with an idea
                                        │
                                   two sentences
                                        ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │  /spec        strongest model · bounded loop · one adversary launch   │
   │      reads ──▶ the graph (never the codebase directly)               │
   │      writes ─▶ specs/<feature>/spec.md   what · why · assertions     │
   └──────────────────────────────────────────────────────────────────────┘
                                        │
                              ◆ HUMAN GATE — ~5 min
                                        │
   ┌──────────────────────────────────────────────────────────────────────┐
   │  /plan        strongest model · SKIPPED for small work                │
   │      reads ──▶ spec.md + the graph                                   │
   │      writes ─▶ plan.md   technologies (+versions) · milestones ·     │
   │                          cross-cutting · context seeds · risks       │
   └──────────────────────────────────────────────────────────────────────┘
                                        │
                              ◆ HUMAN GATE — ~10 min
                                        │
   ┌──────────────────────────────────────────────────────────────────────┐
   │  /tasks       strongest model                                        │
   │      reads ──▶ spec.md + plan.md + graph (where·dependents·overlap)  │
   │      writes ─▶ tasks.md   phases · file:line · steps · done-when     │
   └──────────────────────────────────────────────────────────────────────┘
                                        │
                              ◆ HUMAN GATE — ~10 min
                                        │
   ┌──────────────────────────────────────────────────────────────────────┐
   │  /build       cheapest model that follows instructions · ONE RUN     │
   │                                                                      │
   │   ph0 ─▶ ph1 ─▶ ph2 ─▶ ph3 ─▶ ph4 ──────▶ ph5 ─▶ ph6 ─▶ ph7         │
   │   found  contr  VERIFY  core  ┌──┴──┬────┐ integ  hard   PROOF       │
   │          (freeze) │           T-8 ∥ T-9 ∥ T-10           │           │
   │                   │                                      │           │
   │              suite goes RED ─────── green ───────────────▶ /verify   │
   │                                                        (wrote no code)│
   │                                                                      │
   │   each task = ONE SPAWN: skill file + task block + decisions         │
   │                        + the 0–1 MCP servers scoped to role×phase    │
   │   each phase end     : exit check · regraph changed dirs             │
   └──────────────────────────────────────────────────────────────────────┘
                                        │
                    a diff · a green suite · verification.md
```

Three supporting pieces sit beside the pipeline rather than in it:

```
   /graph   ── a binary reads the source ──▶ .edify/graph/{nodes,edges}.tsv
              never a model.  answers: where · dependents · overlap · defines

   mcp.md   ── the registry of servers reaching OUTSIDE the repo
              pinned · scoped per role×phase · docs server is the default one

   /harvest ── public skills ──▶ screen ──▶ rewrite ──▶ ◆ HUMAN ──▶ library
              runs in EDIFY's repo only.  never in a client's.
```

## 2. The six edges that carry the system

Everything else is plumbing. These six are the design.

**`/spec` → the graph, not the codebase.** The specifying model never explores. It asks
the graph where things are and gets an exact answer. This is what makes `/spec` fast on a
repository nobody has read.

**`/plan` → an exact version on every technology row.** The decision is made once, with
its alternative named, at a pinned version. Without this, forty tasks each make it
independently and none of them writes it down.

**`/tasks` → `file:line` on every task.** Every reference resolved through the graph
before it is written. This is the edge that removes exploration from build time
entirely: a builder that knows which forty lines to open does not need to search, and
does not need to be smart.

**phase 2 → a red suite.** Every assertion becomes a failing executable test before any
implementing code exists. This is what turns "is this right?" from a judgment into a
count, which is what makes the cheap-model bet work in practice.

**`/build` → one spawn per task, one page per spawn.** Skill file and task block, plus
the zero or one MCP servers scoped to that role and phase. Everything else is pulled.
This is the edge that makes a forty-task feature affordable.

**phase end → regraph.** The directories that changed are re-extracted. This is what
stops phase 5 reinventing what phase 3 built — the anti-fragmentation mechanism, reduced
from a whole engine to one step in a loop.

## 3. What each artifact is read by

| artifact | written by | read by |
|---|---|---|
| `spec.md` | `/spec` | the human gate, `/plan`, `/tasks`, `/verify` |
| `plan.md` | `/plan` | the human gate, `/tasks`, `/verify` — **never `/build`** |
| `tasks.md` | `/tasks`; decisions appended during `/build` | the human gate, `/build`, every spawn, `/verify` |
| `verification.md` | `/verify` | humans, CI, review |
| `.edify/graph/` | the extractor binary | `/spec`, `/plan`, `/tasks`, any agent mid-task, `edify check` |
| `.edify/skills/` + `index.tsv` | `/harvest`, then `edify init` selection | every spawn |
| `.edify/mcp.md` | `edify init`, then reviewed edits | every spawn, scoped |
| `CLAUDE.md` | `edify init` | every session, once, at the start |

Eight things. Every arrow in §1 is one of these being written or read.

**`/build` not reading the plan is deliberate**, and it is the subtlest line in this
table. A builder with access to the reasoning has judgment again, and judgment at build
time is the one thing the executor is defined by not having.

## 4. The invariants

1. **No model writes the graph.** Not at install, not as a fallback, not for an
   uncovered language. A missing language means missing nodes, visibly.
2. **No model chooses a skill or an MCP server.** The task names a role and a phase;
   both resolve by exact-match lookup over sorted tables.
3. **No external content enters the graph.** A documentation server describes a package
   from outside our trust boundary; the graph describes this codebase and is trusted
   because nothing narrated is in it.
4. **No planning happens during `/build`.** A plan that turns out wrong stops the
   affected task and re-enters `/tasks`. It never adapts in place.
5. **No contract changes after phase 1.** A contract that moves while surfaces are being
   built against it is how a feature becomes a patchwork.
6. **No test is written after the code it tests.** Phase 2 precedes phase 3, and
   `/verify` reads git history to confirm it actually did.
7. **No state crosses in conversation.** Each command ends by writing a file; the next
   begins by reading it. A run that dies is resumed by reading `tasks.md`.
8. **Nothing here blocks.** Every check is visible, not preventive. Where a hard block is
   required, it is `/verify` in CI with a non-zero exit, owned by the client. Stated in
   the open because the alternative is governance theater.
