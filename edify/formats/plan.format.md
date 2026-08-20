# The `plan.md` format

The technical handoff between the spec and the task list. It carries every decision
that binds more than one task, so no task has to make one. The worked instance is
`plan.example.md`.

Written when the feature introduces a technology, spans milestones, needs
cross-cutting strategy, or will be built by more than one person. Skipped
otherwise, and skipping it is the normal case.

---

## Frontmatter

```yaml
---
feature: team-invitations
spec: spec.md
status: draft            # draft | approved | amended
milestones: 6
date: 2026-08-06
supersedes: —
---
```

## The sections

```
# plan — <feature>
## Milestones            the sequence, then the dependency rules with their reasons
## Technology decisions  each row naming the alternative it beat, at an exact version
## Cross-cutting         migrations, variants, assets, shared components, verification budget
## Per-milestone         goal · requirements · gate · size · files · context seeds
## Parallelization       what may overlap, what may not
## Risks                 each mapped to the milestone that mitigates it
```

## `## Milestones`

| id | delivers | requirements covered | gate | size |
|---|---|---|---|---|
| M1 | capture and calibration skeleton | REQ-1, REQ-2, REQ-5 | three calibrations within ±5% | M |

Then the dependency rules in prose, one line each, **each stating why**:

> M2 must complete before M3, M4 and M5 — they all consume its pipeline output.

The reason matters because `/tasks` uses the rule to assign phases, and a rule with
no reason is a rule nobody can safely relax when the plan is amended.

## `## Technology decisions`

| # | decision | version | beat | why |
|---|---|---|---|---|
| D-1 | Pose estimation runs on-device with a bundled model | model-x 0.10 | a cloud inference API | the spec's offline constraint kills every cloud option |
| D-2 | Local transfer uses embedded server library Y | 2.3 | library Z, raw sockets | Y is 400 KB and already a transitive dependency; Z adds 6 MB for features unused here |

**A row names the alternative it beat.** A row with no alternative is a default,
which is fine and should say so — a default is much cheaper to revisit than a
decision, and the difference matters when someone reopens it in six months.

**Versions are exact.** `2.3`, not `^2.3`, not "latest". This column is what the
documentation server is pointed at, and it is what makes a builder write against
the API that is installed rather than the one it remembers.

## `## Cross-cutting`

Everything no single task can own because it is a property of the whole build. What
appears here is repository-specific; what is universal is the reason — two tasks
each making an independently reasonable choice produce an inconsistent system.

- **Migration ownership** — version number → milestone → what it adds. Allocated
  here, once, so two tasks never claim the same number.
- **Build variants** — what each includes, declares, and forbids.
- **Bundled assets** — each asset, its size, its variant, and a total. A size budget
  stated here is a budget; discovered at the end it is a problem.
- **Shared components** — introduced in one milestone and reused in three others,
  named here so the later three do not each build their own.
- **Verification budget** — every assertion the spec marks `model` or `proof`, with
  its tool and the milestone carrying the cost.

## `## Per-milestone`

```
### M2 — pose inference and signal processing

Goal:         per-frame inference, outlier rejection, filtering, differentiation
Requirements: REQ-3, REQ-6..REQ-10
Gate:         ≥85% retention on clean input, ≥95% rejection on occluded
Size:         L
Migration:    V2 (frame table)

Affected files
  src/vision/inference.ts          new
  src/db/schema.ts:118-146         edit

Context seeds
  spec.md:44-71                the assertions this milestone must satisfy
  src/vision/frame.ts:12-58    the existing frame type it extends
```

**The context seeds are why this document pays for itself.** `(file, line-start,
line-end, why)`, resolved against the graph at plan time so `/tasks` inherits them
instead of re-deriving them. A seed without a line range transfers its cost
downstream, which is the whole thing the plan exists to prevent.

## `## Parallelization` and `## Risks`

Parallelization is stated at the milestone level; `/tasks` computes the exact
task-level answer from the graph. A milestone pair marked parallel here that the
graph later shows overlapping is a planning error worth catching.

Risks get one row each: what it is, which milestone it lands in, and the specific
thing in this plan that mitigates it. A risk with no mitigation has been noticed
rather than handled, and the row should say so rather than looking handled.

## What this is not

Not a design document — no function signatures or data structures beyond the
contracts. Not read by the builder. Not a schedule: sizes and sequences, never
dates. A plan that carries dates becomes wrong on a schedule and gets ignored on
the same one.

## What `edify check` reports

A technology row with no version, or a loose one (`^2.3`, `latest`). A row naming
no alternative and not calling itself a default. A context seed with no line range,
or one that does not resolve against the graph.
