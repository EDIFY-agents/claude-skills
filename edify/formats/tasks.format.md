# The `tasks.md` format

The most important format in EDIFY. Its precision is the difference between a build
that runs on a cheap model in one pass and one that stalls on every third task.

Read `tasks.example.md` alongside this. This document states the contract; that one
shows what the contract feels like when satisfied.

---

## The phase ladder

Phases are horizontal layers. You finish a layer and the next one rests on it
without asking questions. A feature uses the phases it needs and omits the rest;
the numbering stays stable so `Phase 4` always means the same kind of work.

| # | phase | what lands here |
|---|---|---|
| 0 | Foundation | dependencies, config, feature flag, folder skeleton |
| 1 | Contracts | schema, migrations, types, API shapes, interfaces — **frozen at phase end** |
| 2 | Verification | every spec assertion as an executable test that **fails** |
| 3 | Core | domain logic: the thing the feature actually is |
| 4 | Surfaces | endpoints, screens, jobs — each against the frozen contracts |
| 5 | Integration | surfaces wired to core, mocks replaced, end-to-end paths |
| 6 | Hardening | error states, permissions, edge cases, logging, limits |
| 7 | Proof | run it for real, capture evidence, review the whole diff |

**The freeze rule.** Everything phase 1 produces is fixed when phase 1 ends. A task
in phase 4 that needs a contract change stops and becomes a `/tasks` amendment.
This single rule is what makes phase 4 parallel-safe and turns phase 5 into
confirmation rather than discovery.

**Phase 2 ends with the suite entirely red.** That is the correct state of a
codebase that has decided what finished means and is not finished. Every phase
after it is measured by how much of that red turns green — a count anyone can
watch, rather than a series of claims about progress.

**Phase 4 is where parallelism lives.** Phases 1, 5 and 7 are almost always serial:
a migration, an integration and a review each need the whole picture.

## Frontmatter

```yaml
---
feature: team-invitations
spec: spec.md
plan: —                  # plan.md, or — when the feature does not need one
status: draft            # draft | approved | amended
phases: 8
tasks: 16
date: 2026-08-06
---
```

## The document

```
# tasks — <feature>
## Phases            the ladder for this feature, one row each, with exit checks
## Phase N · <name>  one section per phase, containing its task blocks
## Coverage          every requirement and checklist row → the task that discharges it
## Decisions         append-only, written during the build, empty at the gate
```

`## Phases` is a table: number, name, the task ids in it, which of those are
parallel-safe together, and the **exit check** — the command that must pass before
the next phase starts. An exit check that is not a command anyone can run is not an
exit check.

## The task block

Every task answers five questions. A block missing any of them is not ready to
build.

```
### T-7 · <one line: what this task does>
Phase 4 · Role api · Skill implementer-node · Size s
Discharges REQ-4, CL-2
Depends on T-4, T-6 · Parallel with T-8, T-9

Files

| path | range | action |
|---|---|---|
| src/api/invitations.ts | — | new |
| src/api/router.ts | 22-38 | edit |

Follow the pattern at
- src/api/members.ts:18-77 — same handler shape: schema, service call, 201 + Location
- src/api/members.test.ts:9-52 — the test shape, including the auth fixture

Steps
1. …
2. …

Done when
- `npm test -- invitations` passes
- POST twice with the same token returns 200 and creates one row
```

**The header line** carries the bookkeeping: phase, role (which resolves to a skill
file by lookup — `edify skills resolve <role> <phase>`), and size. Nothing else
belongs there.

**`Discharges`** — the requirement or checklist ids from the spec. Required and
non-empty. A task that discharges nothing is refused at the gate, and that one rule
is where scope control actually happens.

**`Depends on` / `Parallel with`** — the execution graph. `Parallel with` is
computed with `edify graph overlap`, from file-set overlap including dependents.
Computed, not asserted.

**`Files`** — path, line range, action (`new` | `edit` | `delete`). Ranges are
required for `edit`; `new` files have none. The ranges come from graph queries. A
whole-file reference on an edit is the most common defect in this format and it is
invisible: it passes any shape check, it makes overlap detection return false
positives, and it makes the builder open four hundred lines it did not need.

**`Follow the pattern at`** — one or two pointers to places in this codebase that
already do this correctly, each with what to take from it. **This line is worth
more than a paragraph of description**, because it transfers the codebase's actual
conventions rather than someone's summary of them. It is the single
highest-leverage line in the format and the one planners skip. For genuinely novel
work, write `no precedent in this codebase` explicitly — a blank field reads like
an oversight and sends the builder looking.

**`Steps`** — numbered, in order, concrete enough to follow without choosing. Three
to eight is normal. The test: could someone who has never seen this feature do step
4 without asking a question? "Add validation" is not a step. "Add a `token` field to
the request schema at line 22, `string`, exactly 32 characters, required" is a step.

**`Done when`** — a command with its exact invocation, or a specific observable
outcome. Not "tests pass" — `npm test -- invitations`. Not "the endpoint works" —
"POST twice with the same token returns 200 and creates one row."

## Phase 2 blocks carry one extra line

```
### T-6 · Assertions A-4..A-9 as failing tests — invitation lifecycle
Phase 2 · Role test · Skill test-writer-node · Size m
Discharges A-4, A-5, A-6, A-7, A-8, A-9
Verification example, property (A-7)
...
Done when
- `npm test -- invitations/service` runs and reports 6 failing tests, 0 passing
- Each failure message names the assertion id it covers
```

`Verification` names the kinds this task implements, so the coverage table can be
checked against the spec's declared kinds. A task that quietly writes an example
test where the spec asked for a property test is a silent downgrade, and this line
is what makes it visible.

**The done-check asserts failure.** A phase-2 task whose tests pass on arrival has
either tested something that already existed or tested nothing, and both are worth
catching immediately.

## `## Coverage`

| source | what it is | asserted by | built by |
|---|---|---|---|
| REQ-1 | An admin can invite by email | T-4, T-5 | T-2, T-7, T-8 |
| CL-6 | Personal data has a retention rule | — | `waived` — the only datum is an email the admin already holds |
| REQ-6 | Expired invitations show a clear message | T-5 | `proof-only` — asserted in T-14 |

Three legal values in the right-hand columns: task ids, `waived` with a reason on
the same line, or `proof-only`. An empty cell means the plan is not ready, and the
check runs **before** a human sees the table.

A row with a builder and no asserter is a requirement nobody wrote a failing test
for: it will be built, it will look done, and nothing will ever have proved it.

## `## Decisions`

Append-only, written during `/build`, empty at the gate.

| # | decision | why | binds |
|---|---|---|---|
| D-1 | Invitation tokens are 32-char base32, not UUIDs | T-4's step 2 said "a token" without a format; base32 is what `src/auth/tokens.ts:14` already produces | T-7, T-9, T-11 |

Every subsequent spawn in the run carries this section. One or two per feature is
normal. Six means `/tasks` under-specified, and that is worth knowing before the
next feature.

## The three tests of a good plan

1. **The cheap-model test.** Could a small, fast model execute every task without
   asking a question? If not, this is prose about the work rather than the work.
2. **The stranger test.** Could an engineer who has never seen this codebase do T-7
   from the block alone plus the files it names?
3. **The coverage test.** Is every row in `## Coverage` filled, and does every task
   trace back to one?

## What `edify check` reports

A task with no discharge, no steps, or no done-check. A whole-file reference on an
edit. A file that is not on disk. A phase-2 done-check that asserts tests pass. An
assertion with no phase-2 task. An empty coverage cell. A phase with no exit check.
A dependency on a task that does not exist.
