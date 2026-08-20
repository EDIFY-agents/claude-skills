# 03 — The `plan.md` Format

The technical handoff between the spec and the task list. It carries every decision
that binds more than one task, so that no task has to make one. Rationale is in
`../04-the-plan.md`; this is the shape.

The worked instance is `../plan-ex.md` — a real plan for a real product: twelve
milestones across five phases, dependency rules stated as rules, per-milestone affected
files, migration version ownership, asset bundling budgets, and risks mapped to the
milestone that mitigates each.

---

## 1. When it exists

Not every feature gets one, and that is the point. Write a plan when **any** of these
is true:

- the feature introduces a technology, library, or external service the repository does
  not already use;
- it spans more than one milestone or shippable stage;
- it needs cross-cutting strategy — a migration sequence, a build variant, a bundled
  asset, a shared component, a config surface;
- more than one person will build parts of it.

Otherwise `/spec` → `/tasks` directly. A one-page plan is ceremony, and a repository
whose plans are all one page should stop writing them.

## 2. The document

```
frontmatter
# plan — <feature>
## Milestones            the sequence and the dependency rules
## Technology decisions  each naming the alternative it beat
## Cross-cutting         migrations, variants, assets, shared components
## Per-milestone         goal · requirements · gate · size · files · context seeds
## Parallelization       what may overlap, what may not
## Risks                 each mapped to the milestone that mitigates it
```

**Frontmatter** — flat, six keys: `feature`, `spec`, `status`
(`draft` | `approved` | `amended`), `milestones`, `date`, and `supersedes` when a plan
replaces an earlier one.

## 3. `## Milestones`

The sequence, and then the rules. A diagram is welcome; the rules are what `/tasks`
reads:

```
M1 → M2 → M3 ↘
        M4  → M6 → ✅ stage gate
        M5 ↗
```

| id | delivers | requirements covered | gate | size |
|---|---|---|---|---|
| M1 | capture + calibration skeleton | REQ-1, REQ-2, REQ-5 | three calibrations within ±5% | M |

Then the dependency rules in prose, one line each, each stating **why**:

> M2 must complete before M3, M4, and M5 — they all consume its pipeline output.
> M6 comes last in the stage; it reads every metric the others produce.

"Why" matters because `/tasks` uses the rule to assign phases, and a rule with no reason
is a rule nobody can safely relax when the plan is amended.

## 4. `## Technology decisions`

The section that most often exists nowhere.

| # | decision | version | beat | why |
|---|---|---|---|---|
| D-1 | Pose estimation runs on-device with a bundled model | model X 0.10 | a cloud inference API | the spec's constraint is fully offline; no cloud option survives it |
| D-2 | Local file transfer over the hotspot uses embedded server library Y | 2.3 | library Z, raw sockets | Y is 400 KB and already a transitive dependency; Z adds 6 MB for features unused here |

**A row names the alternative it beat.** A row with no alternative is not a decision, it
is a default — which is fine and should say so, because a default is much cheaper to
revisit than a decision, and the difference matters when someone reopens it in six
months.

**Versions are exact.** `2.3`, not `^2.3`, not "latest". This column is what the MCP
documentation server is pointed at (`07-mcp.md`), and it is what makes a builder write
against the API that is installed rather than the one it remembers.

## 5. `## Cross-cutting`

Everything no single task can own because it is a property of the whole build. What
appears here is repository-specific; what is universal is the *reason* — two tasks each
making an independently reasonable choice produce an inconsistent system.

The recurring families:

- **Migration ownership** — a table of version number → milestone → what it adds.
  Numbers are allocated here, once, so two tasks never claim the same one.
- **Build variants** — what each variant includes, what it declares, what it forbids.
- **Bundled assets** — each asset, its size, and the variant it ships in, with a total.
  A size budget stated here is a budget; discovered at the end it is a problem.
- **Shared components** — a component introduced in one milestone and reused in three
  others, named here so the later three do not each build their own.
- **Verification budget** — any assertion the spec marks above `property` on the ladder
  (`08-verification.md`) names its tool and the milestone carrying the cost here. An
  unbudgeted model check silently becomes an example test during the build.

## 6. `## Per-milestone`

For each milestone: the goal in a sentence, the requirements covered, the gate that
closes it, a size, the affected files as far as they are known, and the **context
seeds**.

```
### M2 — pose inference and signal processing

Goal:         per-frame inference, outlier rejection, filtering, differentiation
Requirements: REQ-3, REQ-6..REQ-10
Gate:         ≥85% retention on clean input, ≥95% rejection on occluded
Size:         L
Migration:    V2 (frame table)

Affected files
  src/vision/inference.ts          new
  src/vision/outlier.ts            new
  src/signal/filter.ts             new
  src/db/schema.ts:118-146         edit

Context seeds
  spec.md:44-71        the assertions this milestone must satisfy
  spec.md:96-110       the error states it owns
  src/vision/frame.ts:12-58   the existing frame type it extends
  docs/contracts/pose.md:1-90 the frozen contract
```

**The context seeds are the reason this document pays for itself.** They are
`(file, line-start, line-end, why)` — the bridge from prose to `file:line`, resolved
against the graph at plan time so `/tasks` inherits them instead of re-deriving them.
A seed without a line range is a seed that transfers its cost downstream (P3).

## 7. `## Parallelization` and `## Risks`

**Parallelization** — which milestones may overlap and why, and which sequences are
forbidden. Stated at the milestone level; `/tasks` computes the exact task-level answer
from the graph. A milestone pair marked parallel here that the graph later shows
overlapping is a planning error worth catching, not a conflict to resolve at build time.

**Risks** — one row each: what it is, which milestone it lands in, and **the specific
thing in this plan that mitigates it**. A risk with no mitigation row has been noticed
rather than handled, and it should say that in the row rather than looking handled.

## 8. `## Consumed by`

What each downstream reader needs, and what breaks without it:

| reader | reads | precision needed | cost of shortfall |
|---|---|---|---|
| `/tasks` | milestones + dependency rules | every rule states its reason | phases get assigned by guess and cannot be safely relaxed on amendment |
| `/tasks` | context seeds | `file:line-line`, not filenames | `/tasks` re-explores; the whole reason the plan exists is lost |
| `/tasks` | cross-cutting | migration numbers allocated, variants named | two tasks claim the same migration number, or target different variants |
| the builder, indirectly | technology decisions | exact versions | the builder writes against a remembered API instead of the installed one |
| `/verify` | milestone gates | each gate is a runnable check or a stated observation | the proof phase checks the spec's assertions and silently skips the plan's gates |
| the human gate | decisions + risks | every decision names its alternative | the approver sees a conclusion without its argument and cannot disagree usefully |

## 9. What the plan is not

- **Not a design document.** It does not specify function signatures or data structures
  beyond the contracts. That is `/tasks`'s job, and `/tasks` has the graph queries that
  make those accurate.
- **Not read by the builder.** `/build` reads `tasks.md` only. Letting a builder read
  the plan would put judgment back into execution, which is the one thing P2 forbids.
- **Not a schedule.** Sizes and sequences, not dates. A plan that carries dates becomes
  wrong on a schedule and gets ignored on the same schedule.
