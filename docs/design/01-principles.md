# 01 — Design Laws

Eight laws, down from nine. They constrain EDIFY itself, not the code EDIFY helps
write. Every design decision in this folder must satisfy all eight. A proposal that
violates one is either wrong or requires the law to be amended in writing.

The nine laws of the previous dossier are not repudiated — five are carried forward in
a shorter form, two were dissolved by the model getting better, and two were replaced by
their consequences. The mapping is in `10-what-we-dropped.md`.

---

## P1 — Three documents and a map

The system produces exactly four durable things per repository: a **spec** per feature,
a **plan** per feature that needs one, a **task list** per feature, and a **graph** of
the codebase. Anything proposed that is not one of those — or a tool that writes one,
reads one, or searches one — is not part of EDIFY.

Each document has one audience and one job. The spec answers *what and why*, and a
non-engineer can read it. The plan answers *how, with what technology, in what order*,
and it is where every choice that binds more than one task is made once. The task list
answers *exactly what changes, where, in what sequence*, and it is written to be
followed rather than interpreted. The graph answers *where is everything*.

This is a hard boundary because the previous design lost to its own artifact count.
Fourteen schemas meant fourteen files to write, validate, keep consistent, and read; in
practice the obligation list, the assumption register, and the phase contracts were
produced correctly and consumed by nobody.

Where a dropped artifact carried something genuinely load-bearing, it becomes a
**section** of one of the three documents, not a file of its own. Obligations become
the spec's closure checklist. Assumptions become the spec's open questions. The decision
log becomes the task list's decisions section. One file, several sections, one place to
look.

## P2 — Plan hard, build dumb

All thinking happens before the first line of code.

`/spec`, `/plan`, and `/tasks` run on the strongest model available, take as long as
they take, and each end at a human who reads and approves. `/build` runs on the cheapest
model that can follow a written instruction, does not plan, does not choose, does not
research, and does not improvise. It reads a task, does what the task says, checks what
the task says to check, and moves to the next one.

The test of a good `tasks.md` is therefore mechanical: **if the builder had to think,
the plan was incomplete.** A task that says "refactor the auth module appropriately" is
a defect. A task that says "in `src/auth/session.ts:88-140`, replace the inline expiry
check with a call to `isExpired()` from `src/auth/clock.ts:12`, then run `npm test --
auth`" is a task.

This law is what makes cheap models viable, and cheap models are what make building a
large feature in one run affordable.

## P3 — Every reference is a file and a line

No task, no context handoff, no claim about the codebase names a file without a line
range — or the literal `new` for a file that does not exist yet.

`src/import.py` and `src/import.py:88-114` look equally correct in review. Only the
second lets an agent start work without exploring first, and exploration is both the
largest token line-item and the largest source of quietly different answers between
sessions. A whole-file reference does not fail; it transfers its cost to whoever runs
the task, one step downstream, where nobody attributes it.

The graph exists to make this cheap to satisfy. A reference that cannot be resolved
against the graph is a signal that the planner does not actually know where the work
lands, which is worth catching at the plan gate rather than at build time.

## P4 — The executable definition of correct exists before the code

Verification-first, at the feature level rather than the task level. Every assertion in
the spec becomes a **failing** executable test in phase 2 of the build, before any core
logic, surface, or integration is written.

Three things follow, and each is load-bearing:

- An assertion that cannot become a failing test was never an assertion. Finding that
  in phase 2 costs an hour; finding it at the end costs the feature.
- A cheap builder gets an objective target instead of a judgment call. It does not
  decide whether its work is right — it makes a red test green. This is what makes P2's
  bet work in practice rather than in principle.
- A suite written after the code encodes the behavior the code has. It goes green
  immediately, it feels like diligence, and it proves nothing. Ordering is the only
  mechanical defense.

Each assertion also declares *how strongly* it is verified, on a ladder from types
through example tests, contracts, and property tests to model checking and proof. The
rule is to pick the strongest kind that is cheap for that assertion — not the strongest
available. `07-verification.md` has the ladder and where each rung is worth climbing.

## P5 — Instructions explain, they do not command

A skill file is a short, plain explanation of how a competent engineer does this
particular job inside a large codebase. It reads like an experienced colleague telling
a new hire how the work actually goes.

No capitalized MUST blocks. No personas or expertise claims — a role identity is a
persuasion device wearing a lab coat, and it measurably does not help. No
self-attestation sections. No threats, urgency, or role-play pressure. No restating of
policy that lives somewhere else.

Hard budget: **≤80 lines for a skill, ≤150 for a deep specialist.** The previous design
allowed 150 and 400 and used all of it. The reduction is not austerity for its own
sake — a long instruction file is one the model has to hold in context alongside the
actual work, and past about eighty lines the marginal line is displacing something more
useful.

## P6 — Pull context, never push it

A spawn payload is the skill file for the agent's role, the task block, and the
`file:line` references that task names. That is the whole prompt.

Nothing else is pushed. Not the spec, not the plan, not the decision history, not a
repository tour, not fact excerpts "in case they help". Everything else the agent
needs, it **pulls** — one graph query, one file read at a cited range, one call to a
documentation server when the question is about a library rather than this codebase.

The same law governs everything outside the repository. External tools reachable over
MCP are declared in a registry and **scoped to the roles and phases that need them**,
never connected globally: a connected server injects its tool descriptions into every
session whether or not they are used, and eight servers across a forty-task build is a
tax paid three hundred and twenty times for value taken twice.

Push costs tokens on every launch whether or not the material is used, and it costs them
at the most expensive moment. Pull costs nothing until needed. The measure of this law
working is that a spawn prompt fits comfortably on a page.

## P7 — Governance is what a human can read and check

A control counts as governance if a person can look at it and tell whether the work
complied. Four things satisfy that: an approved spec, an approved plan, an approved task
list, and the diff the run produced.

EDIFY no longer claims mechanically enforced governance, because it no longer ships
hooks that block. What it ships instead is legibility: at any moment, what was supposed
to be built is written down, which technologies were chosen and over what is written
down, what will change is written down to the line, and the difference between plan and
result is a diff anybody can read. Where a client needs a hard block — a bank, a
regulated path — that is a CI check they own, written against these files, and EDIFY
says so rather than implying it ships one.

Stated plainly so nobody has to infer it: **advisory means advisory.** A rule with no
mechanism behind it is guidance, is labeled guidance, and is expected to be violable.
The previous dossier's own anti-goal against governance theater still binds, and under
this law it binds harder, because there is less mechanism left to hide behind.

## P8 — Nothing that a better model makes unnecessary

Every piece of scaffolding must answer: *what does this do that the next model
generation will not do on its own?* If the honest answer is "nothing, but it helps
today's model", it is a temporary configuration entry, not architecture — and it carries
a note saying when to check whether it is still earning its place.

The survivors pass this test by construction. A larger context window does not give a
model a map of a million-line repository it has never seen. A smarter model still starts
each session with no memory of the last one, still cannot resolve an ambiguity the
person who wrote the brief never resolved, and still cannot know today's API of a
library that shipped after its training data.

This law is the reason this dossier exists. The previous one was full of scaffolding
that helped a June 2026 model and was drag by August. That was not a failure of that
design; it was the predictable half-life of scaffolding, and P8 is the mechanism for
noticing it on schedule rather than in hindsight.

---

## Anti-goals

- **No agent runtime, no model router, no orchestration framework.** EDIFY rides the
  host runtime and its release velocity.
- **No hook spine, no always-on enforcement layer, no validator that gates.** Format
  checking exists as a command a human or CI can run, never as an invisible gate.
- **No policy tree** — no constitution file, no tier table, no capability profile, no
  waiver policy, no enforcement-parity ledger. What survived of all of them is one
  section of `spec.md` and the plan's technology decisions.
- **No prompt magic** — no personas, no expertise claims, no persuasion blocks, no
  urgency framing.
- **No marketplace**, for skills or for MCP servers. Two curated registries, one door
  each.
- **No external content in the graph**, at any stage, for any reason.
- **No server, no daemon, no database.** Files, and a binary that reads them.
