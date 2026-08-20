# 08 — Verification

Phase 2 of the build, the `/verify` command, and the ladder that decides how strongly
each assertion is checked. Rationale is in `../07-verification.md`; this is the shape.

---

## 1. The verification kinds

Every assertion in `spec.md` declares one. This is the whole legal set, ordered from
cheapest to strongest:

| kind | written as | proves |
|---|---|---|
| `types` | a type annotation, strict mode on | the error class is unrepresentable |
| `example` | one test, one input, one expected output | this case behaves |
| `contract` | a pre/post condition or invariant asserted in the code | the function's own rules hold on every call the tests make |
| `property` | a generated-input test with a stated invariant | the rule holds across hundreds of cases, shrunk to the smallest failure |
| `model` | a state machine or protocol specification, checked exhaustively | no reachable state violates the invariant |
| `proof` | a machine-checked proof | the property holds for all inputs |
| `observation` | a human looks, with evidence attached | last resort — requires a transcript, screenshot, or recording |

**The selection rule: the strongest kind that is *cheap* for this assertion.** Not the
strongest available. Most assertions land on `types` through `property`. A few land on
`model`. Almost none land on `proof`, and a system that pretends otherwise is selling.

**Defaults, so nobody has to decide from scratch:**

- A pure function or data transformation → `property`.
- A behavior with a specific interesting case → `example`.
- Anything expressible in the type system → `types`, *in addition to* whatever else it
  gets. Types are free and additive.
- An ordering, concurrency, or protocol hazard → `model`.
- Anything at `model` or `proof` must be named in `plan.md`'s verification budget
  (`03-plan-format.md` §5), because an unbudgeted model check silently downgrades to an
  example test during the build and nobody notices it happened.

**`observation` is the only kind that cannot be re-run mechanically**, so it carries the
tightest requirement: the evidence is pasted raw — a transcript, a captured screen, a
recording — never summarized. "I checked and it works" is not an observation, it is a
claim.

## 2. Phase 2: turning assertions into failing tests

Phase 2 of the ladder (`04-tasks-format.md` §1) has one job: **every assertion in the
spec becomes an executable test that fails.**

Its tasks look like every other task — files, pattern pointer, steps, done-check — with
one addition to the header:

```
### T-6 · Assertions A-4..A-9 as failing tests — invitation lifecycle
Phase 2 · Role test · Skill test-writer-node · Size m
Discharges A-4, A-5, A-6, A-7, A-8, A-9
Verification example, property (A-7)
Depends on T-3 · Parallel with T-7

Files
| path | range | action |
|---|---|---|
| src/invitations/service.test.ts | — | new |

Follow the pattern at
- src/members/service.test.ts:1-44 — fixture setup: makeWorkspace(), makeUser(), the
  truncate in afterEach. Copy this exactly; every service test in this repo uses it.
- src/auth/tokens.property.test.ts:1-30 — the property-test shape for A-7, including
  the generator and the shrink configuration.

Steps
1. …

Done when
- `npm test -- invitations/service` runs and reports 6 failing tests, 0 passing
- Each failure message names the assertion id it covers
```

Two things in that block are specific to phase 2 and both matter.

**`Verification` in the header** names the kinds this task implements, so the coverage
table can be checked against the spec's declared kinds. A task that quietly writes an
example test where the spec asked for a property test is a silent downgrade, and this
line is what makes it visible.

**The done-check asserts failure.** `runs and reports 6 failing tests, 0 passing` — not
"tests pass". A phase-2 task whose tests pass on arrival has either tested something
that already existed or tested nothing, and both are worth catching immediately.

**Phase 2 leaves the repository red**, entirely and correctly. That is the state of a
codebase that has decided what finished means and is not finished. Every phase after it
is measured by how much of that red turns green, which is the objective target that
makes a cheap builder safe (P2, P4).

## 3. `/verify` — the command

**Reads:** the repository, `spec.md`, `tasks.md`, and `plan.md` if there is one.
**Writes:** `specs/<feature>/verification.md`.
**Model:** strong, and **never a session that wrote any of the code**.
**Runs:** on demand, in CI, and as phase 7 of every build.

It **runs** things. It does not decide things, and it never edits code.

**The passes:**

1. **Re-run everything.** The full suite, the type check, the lint, invoked exactly as
   the spec's constraints say to invoke them. Raw output captured, never a summary and
   never a reported result taken on trust.
2. **Confirm the ordering.** Read git history and confirm the tests for each assertion
   landed before the code that satisfies them. A suite written afterwards encodes the
   behavior the code has; this pass is the only mechanical way to know which happened.
3. **Exercise it for real.** Where an acceptance scenario can be run — start the
   service and make real calls, drive the interface, run the job against fixtures — do
   that, and paste the transcript. This is where the class of failure that passes every
   unit test surfaces.
4. **Walk the coverage table.** Every row from `tasks.md` marked `satisfied` with its
   evidence, `waived` with its reason, or `blocked` with what is missing. Every
   assertion checked against the verification kind the spec declared for it — a
   downgrade is reported, not accepted.
5. **Check the plan's gates**, if there is a plan. Milestone gates are separate from
   spec assertions and are otherwise never checked by anything.
6. **Read the diff as one design.** The one judgment call: is there one way of doing
   each thing here, or several? Named specifically — a second helper that duplicates an
   existing one, two error-handling styles, inconsistent vocabulary between modules.
   Written down with what was checked, never asserted as clean.

**Refuses:** editing code; running in a session that wrote code; a summary where raw
output belongs; marking a row satisfied without evidence; passing an assertion whose
declared kind was silently downgraded.

## 4. The report

`verification.md` — one file, four sections, readable by someone who was not in the
room:

```
## Ran            every command, its exact invocation, and its raw output
## Ordering       per assertion: test commit → code commit, or a note that it was not
## Coverage       every row: satisfied (evidence) | waived (reason) | blocked (what)
## One design     what was checked for duplication and drift, and what was found
```

The raw output is the point. A summary of a test run is a claim about a test run, and
the entire reason this command exists in a fresh session is that claims about one's own
work are structurally uninformative.

## 5. Where it runs

| moment | who runs it | scope |
|---|---|---|
| phase 7 of a build | a fresh agent that wrote no code | the whole feature |
| in CI, on every push | the CI job | passes 1 and 4 — the mechanical half |
| by hand, any time | anyone | whatever they ask for |

The reason it is a command and not only a phase: the same evidence a person wants at the
end is evidence CI wants on every push, and a check that exists only inside an agent run
is a check that exists once. This is also where a client who needs a hard block puts it
— `/verify` in CI with a non-zero exit is the enforcement EDIFY itself does not ship
(`../01-principles.md` P7), owned by the people it protects.

## 6. What this does not claim

- **Not formally verified software.** A ladder is made available and each rung is named
  with when it is worth climbing. Most projects live on rungs 1–4 and that is correct.
- **Not proof that the assertions were the right ones.** A green suite says the
  assertions hold. Whether they were the right assertions is the spec gate and the
  adversary, and neither is mechanical.
- **Not a gate.** `/verify` reports. A person or a CI job decides what the report means.
  Same honest scope as every other control in this system.
