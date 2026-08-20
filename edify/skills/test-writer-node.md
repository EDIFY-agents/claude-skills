---
name: test-writer-node
description: Turns spec assertions into failing tests in a TypeScript or JavaScript codebase.
kind: skill
role: test
phase: 2
tech: typescript javascript jest vitest react
provenance: original
license: -
---

# Test writer — Node / TypeScript

## What you're doing

Phase 2. Every assertion in the spec becomes an executable test that **fails**, at
the verification kind the spec declared, before any implementing code exists.

The suite you write is the definition of finished. Everything after this phase is
measured by how much of your red turns green, which is what lets a cheap model
build reliably: it is not judging its own work, it is hitting a target.

## How the work goes

1. Read the task block. It names the assertion ids you cover and the kind for each.
2. Open the pattern pointer and copy the fixture setup exactly — the factory
   helpers, the teardown, the auth fixture. Every test in this repository uses it
   and yours should be indistinguishable.
3. One `describe` per requirement, one `it` per assertion, and **the assertion id in
   the test name**, so a failure output names what is unsatisfied.
4. Write against the contract frozen in phase 1. Import its types and schemas; never
   redeclare a shape.
5. For an assertion marked `property`, write a generated-input test with the stated
   invariant and the shrink configuration the neighbouring property test uses. Do
   not downgrade it to three examples — the spec chose `property` because the rule
   holds over all inputs, not over three of them.
6. For an assertion marked `observation`, write no test. Add a skipped placeholder
   named for the phase-7 task that discharges it, so the assertion count stays
   honest.
7. Do not stub the implementation to make anything pass. The imports resolve to
   modules that do not exist yet; that is the expected failure at this phase.
8. Run the suite and confirm the count: N failing, 0 passing. Then run the type
   check — the tests must compile against the frozen contract even while failing.

## The traps specific to this phase

- A test that passes on arrival tested something that already existed, or tested
  nothing. Both are worth catching now.
- A snapshot test written before the code snapshots nothing and goes green later
  against whatever was built. Assert values, not snapshots.
- An assertion on a subset of an unauthenticated response body will not catch a
  leak. Assert the exact key set.
- Mocking the thing under test makes the suite agree with itself.

## When you're stuck

If an assertion cannot be written as a failing test, that is a real finding about
the spec, not a formatting problem. Write `BLOCKED T-n: A-k cannot fail as written
— <why>` and stop.

## What you hand back

The task id, the test files you wrote, the raw suite output showing the failing
count, and `done` or `blocked: <reason>`.
