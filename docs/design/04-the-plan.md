# 04 — The Plan

**The failure it prevents:** the technology decision that nobody made on purpose. The
library got chosen by whichever task needed it first, the migration numbering got
invented twice, the model file got bundled into the wrong build variant, and none of it
appears in any document — it appears as consequences, forty tasks later, in code.

**The design goal:** one file where every technical choice that binds more than one
task is made once, argued once, and approved once.

---

## 1. Why this is a separate artifact

The spec answers *what and why*. The task list answers *exactly what changes, where*.
Between them sits a class of decision that belongs to neither:

- **Which library, which version, and why that one** rather than the two alternatives.
- **The milestone sequence** — what ships first, what gates each stage, what can only
  start after something else lands.
- **Cross-cutting strategy** — migration numbering and ownership, build variants,
  bundled assets and their size budget, shared UI components, config surface.
- **Risks and their mitigations**, each mapped to the milestone that carries it.

Putting these in the spec makes the spec unreadable to the person who most needs to
read it — the one deciding whether the right thing is being built. Putting them in the
task list means deciding them forty times, in forty places, by whoever hits them first.

So: **`spec.md` → `plan.md` → `tasks.md`.** Three documents, each with one audience and
one job. The reference is `plan-ex.md`, a real plan for a real product: twelve
milestones across five phases, dependency rules stated as rules, per-milestone affected
files, migration version ownership, asset bundling budgets, and risks mapped to the
milestone that mitigates them.

## 2. What the plan carries

**`## Milestones and sequencing`** — the milestones, what each delivers, and the
dependency rules between them as explicit statements: *M2 must complete before M3, M4,
and M5 because they all consume its pipeline output*. A diagram is fine; the rules are
what `/tasks` reads. Each milestone names the requirements it covers and the gate that
closes it.

**`## Technology decisions`** — one row per choice that binds more than one task. What
was chosen, at what version, what it was chosen over, and the reason in one sentence.
This is the section that most often does not exist anywhere, and its absence is why the
same argument gets had three times.

The rule that keeps it honest: **a decision here names the alternative it beat.** A row
with no alternative is not a decision, it is a default — which is fine, and should say
so, because a default is much cheaper to revisit than a decision.

**`## Cross-cutting strategy`** — the things that cannot be owned by any one task
because they are properties of the whole build. Migration version allocation and which
milestone owns each. Build variants and what each includes. Bundled assets and the size
budget. Shared components and where they are introduced. Anything where two tasks
making independent reasonable choices produces an inconsistent system.

**`## Per-milestone detail`** — for each milestone: the goal, the requirements covered,
the gate, a size, the affected files as far as they are known, and — the load-bearing
part — the **context seeds**: `(file, line-start, line-end, why)` pointers into the
spec and the codebase that `/tasks` uses to place work without exploring. This is where
the plan pays for itself: it is the bridge between prose and `file:line`.

**`## Parallelization`** — which milestones can run at the same time and why, and which
sequences are forbidden. Stated at the milestone level; `/tasks` computes it exactly at
the task level from the graph.

**`## Risks`** — one row per risk: what it is, which milestone it lands in, and the
specific thing in the plan that mitigates it. A risk with no mitigation row is a risk
that has been noticed rather than handled, and it should say that plainly.

## 3. When the plan is skipped

Not every feature needs one. Writing a plan for a two-task change is the ceremony this
design exists to remove.

**Write a plan when any of these is true:**
- The feature introduces a technology, library, or service the repository does not
  already use.
- It spans more than one milestone or more than one shippable stage.
- It needs cross-cutting strategy: a migration sequence, a build variant, a bundled
  asset, a shared component.
- Two or more people will build parts of it.

**Skip it otherwise.** `/spec` → `/tasks` is the normal path for normal work, and the
plan is what appears when the work is genuinely large. If a repository's plans are all
one page, they are ceremony and should stop being written.

## 4. How it is produced

`/plan` reads the approved spec and the graph. It is a strong-model command with a
human gate, like the two around it.

Its passes: cut the work into milestones by dependency; make and record the technology
decisions, each naming its alternative; write the cross-cutting strategy; for each
milestone, resolve the context seeds against the graph so they are `file:line` and not
prose; map the risks.

The one thing it must not do is design the code. A plan that specifies function
signatures has taken `/tasks`'s job and taken it without the graph queries that make
those signatures accurate.

## 5. What the plan binds

Everything downstream reads it and nothing downstream overrides it:

- `/tasks` reads the milestones to assign phases, the context seeds to place tasks
  without exploring, and the cross-cutting strategy to know which migration number a
  task owns and which build variant it targets.
- `/build` never reads it directly — the task list carries what a builder needs. This
  matters: the plan is a planning input, and letting a builder read it would reintroduce
  judgment into execution.
- The proof phase checks the result against the plan's gates, not only the spec's
  assertions.

A change to the plan mid-build is the same operation as a change to the task list: it
stops, it is written down, a human sees it, and the affected tasks are re-derived.
Silently building something the plan does not describe is how the plan becomes fiction,
and a fictional plan is worse than no plan because people trust it.
