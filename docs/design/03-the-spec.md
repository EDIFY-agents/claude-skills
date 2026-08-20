# 03 — The Spec

**The failure it prevents:** a confident, well-engineered, wrong thing. The model
builds what was asked; nobody wrote down what was meant, what the feature implies on
this platform, or which version of which language it has to work with.

**The design goal:** one file a human reads in ten minutes and can honestly approve,
carrying everything the plan and the build will need and nothing they will not.

---

## 1. One file, and what it absorbed

The previous design split specification across five files: the brief, the spec, the
obligation list, the assumption register, and the decision log. Each had a schema, a
golden exemplar, and a handoff contract. In practice the spec was read, the
obligations table was skimmed at the gate, and the other three were produced
correctly and never opened again.

They are now **sections of `spec.md`**:

| was a file | is now a section | why it survived |
|---|---|---|
| `brief.md` | `## Brief` — the ask, verbatim | the adversary needs the unedited original to argue against the draft |
| `obligations.md` | `## What this entails` | the camera-permission failure is real and nothing else catches it |
| `assumptions.md` | `## Open questions` | the highest-value five minutes a human spends is here |
| `decision-log.md` | moved to `tasks.md` `## Decisions` | it is a build-time record, not a spec-time one |

## 2. What the spec carries

**`## Brief`** — what the person actually asked for, in their words, unedited. Three
lines is normal. It is preserved because it is the only uncontaminated statement of
intent in the system, and both the adversary and the final review check the result
against it rather than against the draft that grew out of it.

**`## Intent`** — numbered clauses, one per distinct thing the feature must
accomplish. Stable numbering; clauses are appended or struck, never renumbered.
This is the fixed star: every requirement traces to a clause, and a clause with no
requirement serving it is an incomplete spec.

**`## Constraints`** — the section that replaced the constitution, and the one most
often gotten wrong by omission. It states what is **given**: the languages and versions
already in use, the target platforms and their floors (Android API level, browser
baseline, runtime version), the package manager and test runner already installed, the
real build/test/lint/run commands, and the requirements that are not up for
negotiation — offline operation, no outbound network, a compliance boundary, a
performance floor.

**Given, not chosen.** Which library to use, at which version, over which alternative,
is a *decision*, and decisions live in `plan.md` (`04-the-plan.md`). The line is worth
holding: a constraint is something the feature must work within; a decision is something
someone picked. Mixing them makes the spec unreadable to the person who most needs to
read it, and makes a decision look like a law of nature.

Why here rather than in a project-level policy file: because it is what the planner and
the builder need at the moment they need it, it changes per feature more often than
anyone admits, and a policy file two directories away is a file nobody reads. Repeating
ten lines of constraint in each spec is cheaper than maintaining a constitution, a
compiler that distributes it, and a mechanism that keeps them in sync.

**`## Requirements`** — a table. Each row: an id, the requirement in one sentence, and
the assertions that prove it. A requirement with no assertion is a wish.

**`## Assertions`** — a table. Each row: an id, one statement that can fail, **how
strongly it is verified**, and a citation. The verification kind comes from the ladder
in `07-verification.md` — types, example test, contract, property test, model check, or
proof — and the rule is to pick the strongest kind that is *cheap* for this assertion,
not the strongest available. An assertion about a pure function or a data transformation
defaults to a property test. The citation is `file:line` or the literal `new` (P3).

This column is not bookkeeping. Phase 2 of the build turns every row here into a failing
executable test before any code exists (P4), so an assertion that cannot be written as a
failing test is an assertion that was never one — and the cheapest moment to discover
that is while writing this table.

**`## What this entails`** — the closure checklist. Everything the feature implies
that nobody asked for: the permission it needs declared and requested, the migration
and its rollback, the error and empty and loading states, the authorization check on
the new endpoint, the logs and the alert threshold, the translation keys, the
retention rule on the personal-data field. Each row is either satisfied by a
requirement, deliberately waived with a reason, or open — and an open row is what the
human gate is for.

This is the one piece of the old Completeness Engine that survives intact, because it
is the one that a better model does not make unnecessary: the model misses fewer of
these than it used to, but a miss is still silent, and a checklist turns a silent miss
into a visible row.

**`## Open questions`** — every ambiguity in the brief, each with the readings it
allows, which one the draft adopted, and who resolves it. The human either resolves
them or accepts the defaults on the record. An unresolved question with real
consequences blocks the gate; everything else is accepted as a stated assumption and
resurfaces in the final review as "we assumed X."

**`## Non-goals`** — what this feature explicitly does not do. Cheap to write, and it
is what the plan and the final review check scope creep against.

## 3. How it is produced

`/spec` runs a short bounded loop, not a single pass. Draft, then re-read the draft
against the brief and the graph, then fix what does not line up, and stop when a pass
finds nothing new — or at three passes, whichever comes first. Hitting the bound is
information: it means the brief is genuinely ambiguous, and the residue goes into
open questions where a human sees it, rather than into more token spend.

Two model calls carry the weight. The first drafts. The second is an **adversary**
that receives only the brief and the finished draft — never the drafting session's
reasoning — and answers one question: what does this feature entail that nobody asked
for and the draft did not catch? Its findings append to the closure checklist and the
open questions, marked as adversary-found.

The separation is not ceremony. An author reviewing its own draft agrees with itself,
reliably and cheaply, and produces a review that looks like diligence and contains no
information.

## 4. The gate

The human is shown: the intent, the requirements, the closure checklist with any open
rows highlighted, the open questions, and a rough cost band. They approve, amend, or
send it back. Approval is a commit — the spec is now the thing the plan is derived
from and the thing the result is checked against.

Five minutes, once per feature. It is the only mandatory human step in the system
besides the plan gate, and skipping it is how teams end up with a beautifully built
wrong thing.

## 5. What good looks like

`design/spec-ex.md` — the IRA7 BIOMECH specification — is the reference for tone and
completeness. It is a real spec for a real product, written in plain language, with
the product philosophy stated before the feature list, the user named, the platform
constraints explicit, and hard product rules at the end that bound everything above
them. It is longer than most specs need to be because the product is large; the shape
is what to copy, not the length.

The one thing to carry from it above all: it says *why* before *what*, and every
feature in it is traceable to a question the user actually has. A spec that opens
with a component list has already lost the thread.
