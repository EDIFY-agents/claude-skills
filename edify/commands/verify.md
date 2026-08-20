---
name: verify
description: The code becomes evidence.
model: strong, and never a session that wrote code
ends-at: a report anyone can read
---

# /verify

Re-run everything yourself and write down what actually came out. This command runs
things. It does not decide things, and it never edits code.

## What you read

The repository, `spec.md`, `tasks.md`, and `plan.md` if there is one.

## What you write

`specs/<feature>/verification.md` — four sections, readable by someone who was not
in the room.

## The passes

1. **Re-run everything.** The full suite, the type check, the lint, invoked exactly
   as the spec's constraints say to invoke them. Capture the raw output. A summary
   of a test run is a claim about a test run, and the entire reason this runs in a
   fresh session is that claims about one's own work carry no information.
2. **Confirm the ordering.** Read `git log` and confirm the tests for each
   assertion landed before the code that satisfies them. A suite written afterwards
   encodes the behaviour the code has rather than the behaviour the spec asked for,
   and this is the only mechanical way to know which happened.
3. **Exercise it for real.** Where an acceptance scenario can be run — start the
   service and make real calls, drive the interface, run the job against fixtures —
   do that and paste the transcript. This is where the class of failure that passes
   every unit test surfaces.
4. **Walk the coverage table.** Every row marked satisfied with its evidence,
   waived with its reason, or blocked with what is missing. Check each assertion
   against the verification kind the spec declared: a property test that became an
   example test is a silent downgrade, and it is reported, not accepted.
5. **Check the plan's gates**, if there is a plan. Milestone gates are separate
   from spec assertions and are otherwise never checked by anything.
6. **Read the diff as one design.** The one judgment call: is there one way of
   doing each thing here, or several? Name specifics — a second helper duplicating
   an existing one, two error-handling styles, inconsistent vocabulary between
   modules. Write down what was checked; never assert it was clean.

## The report

```
## Ran        every command, its exact invocation, and its raw output
## Ordering   per assertion: test commit → code commit, or a note that it was not
## Coverage   every row: satisfied (evidence) | waived (reason) | blocked (what)
## One design what was checked for duplication and drift, and what was found
```

## What this command refuses

Editing code. Running in a session that wrote code. A summary where raw output
belongs. Marking a row satisfied without evidence. Passing an assertion whose
declared verification kind was silently downgraded.

## Where it runs

Phase 7 of every build, in a fresh agent. In CI on every push, where passes 1 and 4
are the mechanical half. By hand, whenever anyone wants it. This is also where a
team that needs a hard block puts one: `/verify` in CI with a non-zero exit is the
enforcement EDIFY itself does not ship, owned by the people it protects.
