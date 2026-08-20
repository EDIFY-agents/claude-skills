# 04 — The `tasks.md` Format

The most important format in EDIFY. The spec is what a human approves; this is what
actually gets built, and its precision is the difference between a build that runs on
a cheap model in one pass and a build that stalls on every third task.

The worked instance is `tasks.example.md`. Read it alongside this document — this one
states the contract, that one shows what the contract feels like when satisfied.

---

## 1. The phase ladder

Phases are horizontal layers. You finish a layer and the next one rests on it without
asking questions. A feature uses the phases it needs and omits the rest; the numbering
stays stable so `Phase 4` always means the same kind of work.

| # | phase | what lands here | role |
|---|---|---|---|
| 0 | **Foundation** | dependencies, config, feature flag, folder skeleton | build |
| 1 | **Contracts** | schema, migrations, types, API shapes, interfaces — **frozen at phase end** | data / api-design |
| 2 | **Verification** | every spec assertion as an executable test that **fails** | test |
| 3 | **Core** | domain logic: the thing the feature actually is | domain |
| 4 | **Surfaces** | endpoints, screens, jobs — each against the frozen contracts | api / frontend |
| 5 | **Integration** | surfaces wired to core, mocks replaced, end-to-end paths | integration |
| 6 | **Hardening** | error states, permissions, edge cases, logging, limits | reliability |
| 7 | **Proof** | run it for real, capture evidence, review the whole diff | verifier |

**The freeze rule.** Everything phase 1 produces is fixed when phase 1 ends. A task in
phase 4 that needs a contract change stops and becomes a `/tasks` amendment. This is
the single rule that makes phase 4 parallel-safe and makes phase 5 confirmation rather
than discovery — a contract that moves while three surfaces are built against it is
exactly how a feature becomes a patchwork.

**Phase 2 is the verification-first phase**, and its position is the design (`../07-verification.md`).
After contracts, because a test needs the shapes it asserts against. Before everything
else, because a suite written afterwards encodes the behavior the code has rather than
the behavior it should have. It ends with the whole suite red, and every phase after it
is measured by how much of that red turns green — which is what gives a cheap builder a
target instead of a judgment call.

Each of its tasks names the **verification kind** from the ladder: types, example test,
contract, property test, model check, or proof. An assertion about a pure function or a
data transformation defaults to a property test. A kind above `property` must have been
budgeted in `plan.md`, because an unbudgeted model check silently becomes an example
test during the build and nobody notices.

**Phase 4 is where parallelism lives.** Surfaces built against a frozen contract touch
disjoint files by construction. Phases 1, 5, and 7 are almost always serial: a
migration, an integration, and a review each need the whole picture.

## 2. The document

```
frontmatter
# tasks — <feature>
## Phases            the ladder for this feature, one row each, with exit checks
## Phase N · <name>  one section per phase, containing its task blocks
## Coverage          every requirement and checklist row → the task that discharges it
## Decisions         append-only, written during the build
```

**Frontmatter** — flat, six keys: `feature`, `spec` (the file it derives from),
`status` (`draft` | `approved` | `amended`), `phases`, `tasks`, `date`.

**`## Phases`** — the ladder as a table: number, name, the task ids in it, which of
those are parallel-safe together, and the **exit check** — the command that must pass
before the next phase starts. An exit check that is not a command anyone can run is
not an exit check.

## 3. The task block

Every task answers five questions. A block missing any of them is not ready to build.

```
### T-7 · <one line: what this task does>
Phase 4 · Role api · Skill implementer-node · Size s
Discharges REQ-4, CL-2
Depends on T-4, T-6 · Parallel with T-8, T-9

Files
| path | range | action |
|---|---|---|
| src/api/invitations.ts      | 1-64  | new  |
| src/api/router.ts           | 22-38 | edit |

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
file by lookup), and size. Nothing else belongs there.

**`Discharges`** — the requirement or checklist ids from the spec. Required and
non-empty. A task that discharges nothing is refused at the gate, and that one rule is
where scope control actually happens.

**`Depends on` / `Parallel with`** — the execution graph. `Parallel with` is computed
from file-set overlap including dependents, not asserted.

**`Files`** — path, line range, and action (`new` | `edit` | `delete`). Ranges are
required for `edit`; `new` files have none. The ranges come from graph queries, not
from memory. A whole-file reference on an edit is the most common defect in this
format and it is invisible: it passes any shape check, it makes overlap detection
return false positives, and it makes the builder open four hundred lines it did not
need.

**`Follow the pattern at`** — one or two pointers to places in this codebase that
already do this correctly, each with what to take from it. **This line is worth more
than a paragraph of description**, because it transfers the codebase's actual
conventions rather than someone's summary of them. It is the single highest-leverage
line in the whole format, and it is the one planners skip.

For genuinely novel work with no precedent, say so explicitly — `no precedent in this
codebase` — rather than leaving the field blank. A blank field reads like an oversight
and sends the builder looking.

**`Steps`** — numbered, in order, concrete enough to follow without choosing. Three to
eight is normal. The test: could someone who has never seen this feature do step 4
without asking a question? If a step requires a decision, the decision belonged at
plan time.

Steps are instructions, not narration. "Add validation" is not a step. "Add a `token`
field to the request schema at line 22, `string`, exactly 32 characters, required" is
a step.

**`Done when`** — how the builder knows it worked. A command with its exact
invocation, or a specific observable outcome. Not "tests pass" — `npm test --
invitations`. Not "the endpoint works" — "POST twice with the same token returns 200
and creates one row."

## 4. `## Coverage`

One row per requirement and per closure-checklist item in the spec:

| source | what it is | discharged by |
|---|---|---|
| REQ-1 | An admin can invite by email | T-4, T-7, T-11 |
| CL-3 | Invitation emails are rate-limited | T-12 |
| CL-6 | Personal data in invites has a retention rule | `waived` — no PII beyond the email, which the user already gave us |
| REQ-6 | Expired invitations show a clear message | `proof-only` — asserted in T-14 |

Three legal values in the right column: task ids, `waived` with a reason on the same
line, or `proof-only` for things checked rather than built. An empty cell means the
plan is not ready, and the check runs **before** a human sees the table — an
incomplete coverage table should never reach a gate looking complete.

This table is the mechanism that turns "we forgot the camera permission" from a
production incident into a blank cell someone notices in ten seconds.

## 5. `## Decisions`

Append-only, written during `/build`, empty at the gate.

| # | decision | why | binds |
|---|---|---|---|
| D-1 | Invitation tokens are 32-char base32, not UUIDs | T-4's step 2 said "a token" without a format; base32 is what `src/auth/tokens.ts:14` already produces | T-7, T-9, T-11 |

Every subsequent spawn in the run carries this section. It is the last remnant of the
previous design's decision log, and it survives for one reason: one-pass execution
removes fragmentation *across* sessions but not *within* a run, and two tasks
resolving the same open question differently is the same defect at smaller scale.

A decision appearing here is also a signal about the plan. One or two per feature is
normal. Six means `/tasks` under-specified, and that is worth knowing before the next
feature.

## 6. What makes a plan good, in three tests

1. **The cheap-model test.** Could a small, fast model execute every task without
   asking a question? If not, the plan is prose about the work rather than the work.
2. **The stranger test.** Could an engineer who has never seen this codebase do task
   T-7 from the block alone plus the files it names? If they would need to explore
   first, a `file:line` or a pattern pointer is missing.
3. **The coverage test.** Is every row in `## Coverage` filled, and does every task
   trace back to one? Empty cells on the left mean something was dropped; empty
   `Discharges` on the right mean something was invented.

A plan that passes all three builds in one run. A plan that fails any of them stalls
somewhere in phase 4, and the stall costs more than writing the plan properly did.
