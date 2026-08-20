# 07 — Verification

**The failure it prevents:** "done" as a sentence somebody writes about their own work.
A build that reports success, a suite that was written after the code and therefore
tests what the code does rather than what it should do, and a feature that passes every
check it defined for itself.

**The design principle:** *verification-first*. Not test-first at the task level —
that is a habit. Verification-first at the **feature** level: the executable definition
of correct exists, and fails, before the code that satisfies it is written.

---

## 1. What verification-first actually means here

Every assertion in `spec.md` is a statement that can fail. Phase 2 of the build turns
every one of them into an **executable test that fails**, before any core logic,
surface, or integration exists.

That single ordering change does four things nothing else in this system does:

**It makes the spec executable.** An assertion that cannot be turned into a failing
test was not an assertion — it was a wish with a table row. Discovering that in phase 2
costs an hour. Discovering it in the proof phase costs the feature.

**It gives a cheap builder an objective target.** This is the piece that makes the whole
"plan hard, build dumb" bet work. A small model does not have to judge whether its work
is right; it has a red test and it makes the test green. Progress is a count, not an
opinion, and the count is visible at every moment of the run.

**It removes the after-the-fact-suite failure.** A test written after the code encodes
the behavior the code has. It goes green immediately, it feels like diligence, and it
proves nothing. Writing the tests first is the only mechanical defense, and reading git
history is the only way to confirm it happened.

**It makes the proof phase a re-run rather than an investigation.** By the time phase 7
arrives, the definition of correct has existed since phase 2 and everything since then
has been measured against it.

## 2. The verification ladder

Not every assertion deserves the same rigor, and the difference is large — a type
annotation costs nothing and a machine-checked proof costs weeks. So each assertion in
the spec declares **how it is verified**, and the kinds form a ladder from cheapest to
strongest.

| # | kind | what it proves | cost | use when |
|---|---|---|---|---|
| 1 | **types** | a whole class of errors is unrepresentable | ~zero | always — strict mode on, no escape hatches |
| 2 | **example test** | this input produces that output | low | the default for behavior |
| 3 | **contract** — pre/post conditions, invariants asserted in code | the function's own rules hold on every call the tests make | low | any function with a stated invariant |
| 4 | **property test** | the rule holds across hundreds of generated inputs | moderate | **the highest-value rung; see §3** |
| 5 | **model check** — a state machine or protocol explored exhaustively | no reachable state violates the invariant | high | concurrency, protocols, state machines, anything with an ordering hazard |
| 6 | **proof** — machine-checked | the property holds for all inputs, period | very high | only where being wrong is catastrophic and the surface is small |

**The rule: pick the strongest kind that is cheap for this assertion.** Not the
strongest available — the strongest that costs little here. Most assertions land on
rungs 1 through 4. A few land on 5. Almost none land on 6, and a design that pretends
otherwise is selling.

**Types are a formal method and are treated as one.** A type checker is a proof checker
for a small logic, it runs in a second, and it is already installed. Strict mode with no
escape hatches is the cheapest formal verification available and it is skipped more
often than any other rung on this ladder.

## 3. Property-based testing is the rung that pays

If one thing from this document changes how a team works, it should be this.

An example test says *this input gives that output*. A property test says *for every
input satisfying these conditions, this relationship holds* — and then generates
hundreds of inputs trying to break it, shrinking any failure to the smallest case that
still fails.

It is the practical middle of the ladder: far stronger than examples, far cheaper than
a proof, available as a mature library in every language a real project uses, and it
finds the class of bug that example tests structurally cannot — the empty list, the
duplicate key, the boundary, the unicode, the reordering, the thing nobody thought of
because thinking of it is exactly what examples require.

Properties worth reaching for, in rough order of how often they apply: round-trips
(parse then serialize returns the input), invariants (the balance never goes negative),
idempotence (applying twice equals applying once), commutativity where order should not
matter, and oracle comparison against a slow obviously-correct implementation.

Where properties belong in this system: an assertion about a **pure function or a data
transformation** should default to a property test, and the spec should say so. That is
a defaulting rule, not a mandate, and it is the single highest-leverage line in the
verification design.

## 4. Where model checking and proofs are actually worth it

Honesty first: for most software, they are not. The cost is real, the tooling has a
learning curve, and the surface that benefits is narrow. A design that requires them
everywhere will be ignored everywhere, which is worse than not asking.

**Model checking earns its cost** when the bug you fear is an *ordering* bug — a
protocol, a distributed handshake, a lock or lease, a state machine with more
transitions than anyone can enumerate by hand, a migration whose steps can interleave
with live traffic. These are exactly the bugs that example tests miss, that reproduce
once in ten thousand runs, and that cost a weekend to diagnose. A small specification
of the state machine, checked exhaustively, is a day of work that pays for itself the
first time.

**Proofs earn their cost** on a small, stable, catastrophic surface: a cryptographic
primitive, a parser exposed to hostile input, a consensus core, a safety interlock.
Small because proof effort scales badly with size; stable because a proof re-done every
sprint is a tax; catastrophic because otherwise a property test at a thousandth of the
cost is the better trade.

**The design rule:** the spec may name kind 5 or 6 for an assertion, and when it does,
the plan must name the tool and the milestone that carries the cost — because a
verification kind nobody budgeted for silently downgrades to kind 2 during the build,
and nobody notices that it happened.

## 5. `/verify` — execution, not judgment

A separate command, and deliberately a thin one. It **runs** things; it does not decide
things.

What it does: re-runs the full suite itself rather than trusting any reported output,
with the raw output captured. Runs the acceptance scenarios as real flows where that is
possible — starts the service and makes real calls, drives the interface, executes the
job against fixtures. Confirms from git history that the tests preceded the code. Walks
the coverage table and marks each row satisfied with its evidence, waived with its
reason, or blocked with what is missing.

What it does not do: edit code, judge quality, or make anything pass.

**It is re-runnable at any time** — mid-build, before a review, in CI, by anyone. That
is the reason it is a command rather than only a phase: the same evidence a human wants
at the end is evidence CI wants on every push, and a check that only exists inside an
agent run is a check that exists once.

It runs in a fresh session that wrote none of the code. The reason is structural rather
than a matter of trust: a session that produced work will read its own output as
correct, reliably and cheaply, and produce a review that looks like diligence and
carries no information.

## 6. Where verification sits in the build

The phase ladder puts it second, and the position is the design:

```
0 Foundation → 1 Contracts (frozen) → 2 VERIFICATION → 3 Core → 4 Surfaces
                                                → 5 Integration → 6 Hardening → 7 Proof
```

Phase 2 comes **after** contracts because a test needs the shapes it asserts against,
and **before** everything else because that is what makes it verification-first rather
than a habit. It leaves the repository with a suite that fails completely — which is
the correct and healthy state of a codebase that has decided what it means to be
finished and has not yet finished.

Phase 7 is the same machinery run by someone else: `/verify`, in a fresh session, plus
the one judgment call that cannot be mechanized — reading the whole diff as one design
and asking whether there is one way of doing each thing or several.

## 7. What this does not claim

- **Not "formally verified software".** EDIFY makes a ladder available and names when
  each rung is worth climbing. Most projects will live on rungs 1 to 4, and that is the
  correct outcome, not a failure to reach the top.
- **Not proof of absence of bugs.** A green suite says the assertions hold. Whether the
  assertions were the right ones is what the spec gate and the adversary are for, and
  neither is mechanical.
- **Not a blocker.** Nothing here stops a session. `/verify` reports; a person or a CI
  job decides what to do about the report. That is the same honest scope every other
  control in this system carries.
