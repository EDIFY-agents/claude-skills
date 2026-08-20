---
name: test-writer-python
description: Turns spec assertions into failing tests in a Python codebase.
kind: skill
role: test
phase: 2
tech: python pytest django flask fastapi
provenance: original
license: -
---

# Test writer — Python

## What you're doing

Phase 2. Every assertion in the spec becomes an executable test that **fails**, at
the verification kind the spec declared, before any implementing code exists.

The suite you write is the definition of finished. Everything after this phase is
measured by how much of your red turns green.

## How the work goes

1. Read the task block. It names the assertion ids you cover and the kind for each.
2. Open the pattern pointer and copy the fixture setup exactly — the `conftest.py`
   fixtures, the database teardown, the client fixture. Yours should be
   indistinguishable from the tests already there.
3. One class or module per requirement, one test function per assertion, and **the
   assertion id in the test name**, so a failure output names what is unsatisfied.
4. Write against the contract frozen in phase 1. Import its models and schemas;
   never redeclare a shape.
5. For an assertion marked `property`, use the repository's property-testing library
   with a stated invariant and a bounded example count. If the repository has none,
   the plan should have budgeted one — say so rather than writing three examples and
   calling it a property test.
6. For an assertion marked `observation`, write no test. Add a skipped placeholder
   naming the phase-7 task that discharges it, so the assertion count stays honest.
7. Do not stub the implementation to make anything pass. The imports resolve to
   modules that do not exist yet; that is the expected failure at this phase.
8. Run the suite and confirm the count: N failing, 0 passing.

## The traps specific to this phase

- A test that passes on arrival tested something that already existed, or nothing.
- `pytest.raises` with no `match=` passes on the wrong exception message.
- A fixture with module scope that mutates shared state makes tests pass in one
  order and fail in another.
- Freezing time in one test and not the neighbouring one produces a suite that
  fails at midnight.
- Mocking the thing under test makes the suite agree with itself.

## When you're stuck

If an assertion cannot be written as a failing test, that is a finding about the
spec. Write `BLOCKED T-n: A-k cannot fail as written — <why>` and stop.

## What you hand back

The task id, the test files you wrote, the raw suite output showing the failing
count, and `done` or `blocked: <reason>`.
