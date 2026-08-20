# Examples

What EDIFY's documents actually look like when they are written well.

---

## Worked documents

These are the calibration examples that ship inside the CLI (`edify/formats/`)
and are installed into your repository at `.edify/formats/`. Your agent reads
them alongside the format contract, because a contract tells you the sections and
an example tells you the *standard*.

| file | format it calibrates | what to look at |
|---|---|---|
| [`spec.example.md`](worked-documents/spec.example.md) | `spec.format.md` | tone and completeness — *why* before *what*, the user before the features, hard product rules that bound everything above them |
| [`plan.example.md`](worked-documents/plan.example.md) | `plan.format.md` | every decision naming the alternative it beat and an exact version; every open question naming who resolves it and when |
| [`tasks.example.md`](worked-documents/tasks.example.md) | `tasks.format.md` | tasks anchored to real files and line ranges, with a done-check that is checkable |

**They are three different features on purpose.** The spec and plan are one
product (IRA7 BIOMECH); the task list is another (team invitations). Each was
chosen because it is the best available demonstration of *that* format, not
because the three form a tidy narrative. A synthetic end-to-end example that
looks neat teaches the wrong lesson — real documents are this long, this
specific, and this opinionated.

The spec is longer than most specs need to be, because the product is large.
**The shape is what to copy, not the length.**

## Checking your own documents against the formats

```bash
edify check              # what is wrong, with a rule id and a reason
edify check --fix        # fix what is mechanical
edify check --exit-code  # non-zero on error — a gate you own
```

The rule ids are the teachable part: `plan-decision-no-version` means a decision
named a range instead of a version, and the reason line says why that matters
(it is what the documentation server gets pointed at).

## The formats themselves

The contracts live next to the examples:

- [`edify/formats/spec.format.md`](../edify/formats/spec.format.md)
- [`edify/formats/plan.format.md`](../edify/formats/plan.format.md)
- [`edify/formats/tasks.format.md`](../edify/formats/tasks.format.md)

And the reasoning behind each, in the design dossier:
[the spec](../docs/design/03-the-spec.md) ·
[the plan](../docs/design/04-the-plan.md) ·
[the tasks](../docs/design/05-the-tasks.md).

## Trying it on your own repository

The best example is your codebase and one real task you have already watched an
agent get wrong. [Quickstart](../docs/quickstart.md) has the ten-minute path, and
[how to pick a good first task](../docs/quickstart.md#pick-a-good-first-task) is
the part worth reading before you start.
