# Verification comes first

**Define correct before implementation. Verify independently at the end.**

---

## The mechanism

Phase 2 of every build turns each assertion in the spec into an executable test
that **fails**, before any core logic exists. Everything after that is making red
go green.

That is what makes a cheap builder safe. It is not judging whether its work is
correct — it is hitting a target that already exists, and progress is a number
anyone can watch instead of a claim anyone has to trust.

```
/spec     assertions written down, in a human's words
/tasks    each assertion becomes a task with a done-check
/build    phase 2: those become failing tests
          phase 3+: make them pass
/verify   a session that wrote no code re-runs everything
```

## Why `/verify` runs in a fresh session

The session that wrote the code is the worst possible judge of it. It knows what
it meant, it remembers why it took a shortcut, and it has every incentive to read
its own output charitably.

So `/verify` runs with **no memory of writing anything**: it reads the spec, the
task list, and the diff, re-runs the suite, and writes
`specs/<feature>/verification.md` — a report anyone can read, and anyone can
re-run at any time, including six months later when the person who built it has
left.

## Checking the documents

```bash
edify check                # report what is wrong
edify check --fix          # fix what is mechanical
edify check --exit-code    # non-zero on error
edify check --json         # machine-readable
```

···  `edify check`

<img src="../assets/verify.svg" alt="edify check output" width="100%">

Findings carry a rule id (`plan-decision-no-version`) and a reason, not just a
complaint. The reason is the part that teaches.

## Nothing blocks

`edify check` prints. A person or a CI job decides what that means.

This is a deliberate position, not a gap. EDIFY does not claim enforcement it
does not have — the previous design had a hook spine that blocked writes, and it
was honest under exactly one agent runtime and degraded to advisory everywhere
else. [`10-what-we-dropped.md`](design/10-what-we-dropped.md) records the cut and
what it cost.

**If you want a hard gate, you own it**, in your CI, where gates belong:

```yaml
- run: edify check --exit-code
- run: edify governance verify --exit-code
```

## Verifying the harness itself

```bash
edify governance verify
```

Every file EDIFY installs is hashed and recorded in `.edify/governance.tsv` —
what it is, where it came from, under what licence, and its hash at the moment it
landed. `verify` tells you what changed since.

···  `edify governance list` · `verify`

<img src="../assets/governance.svg" alt="edify governance output" width="100%">

A control counts as governance if a person can look at it and tell whether the
work complied ([principle P7](design/01-principles.md)). A hash and a filename
qualify. A promise does not.

## Design detail

[`docs/design/07-verification.md`](design/07-verification.md) and
[`docs/design/architecture/08-verification.md`](design/architecture/08-verification.md).
