# 05 — The Tasks

**The failure it prevents:** fragmentation. Work split across many sessions gets done
in parts, in different ways, never as one coherent whole — three naming conventions,
two validation layers, one design that became two designs.

**The design goal:** a plan complete enough that building it requires no judgment, so
the whole feature can be built in one pass by a cheap model, and so the design was
decided once rather than seventeen times.

`tasks.md` is the most important file in EDIFY. The spec is what a human approves;
the task list is what actually gets built.

---

## 1. Phases: build it like LEGO

A phase is a horizontal layer of the build. You finish a layer, and everything in the
next layer can rest on it without asking questions. That is the entire idea, and it
is why the previous design's `/phase-tasks` command is gone: phases were never a
separate process, they were always just the structure of the plan.

The standard ladder — a feature uses the phases it needs and skips the rest:

| # | phase | what lands | the role that owns it |
|---|---|---|---|
| 0 | **Foundation** | dependencies, config, folder skeleton, feature flag, scaffolding | build engineer |
| 1 | **Contracts** | data model, migrations, types, API shapes, interfaces — *frozen at the end of this phase* | data / API architect |
| 2 | **Verification** | every assertion in the spec, as an executable test that **fails** | test engineer |
| 3 | **Core** | the domain logic: pure functions, algorithms, the thing the feature actually is | domain engineer |
| 4 | **Surfaces** | endpoints, screens, CLI commands, jobs — each built against the frozen contracts | API engineer, frontend engineer |
| 5 | **Integration** | surfaces wired to core, mocks replaced by real providers, end-to-end paths | integration engineer |
| 6 | **Hardening** | error states, permissions, edge cases, logging, performance | reliability engineer |
| 7 | **Proof** | run it for real, capture evidence, review the whole diff as one design | verifier |

**Why this order and not another.** It is dependency order, and dependency order is
what allows one-pass execution. Phase 1 freezes the shapes everything else builds
against, which is what makes phase 4 parallelizable: two engineers building two
surfaces against a frozen contract cannot collide, and their integration in phase 5
is confirmation rather than discovery. Phase 6 is separate from phases 3–5 because
error handling written while you are building the happy path is error handling that
matches the happy path you imagined. Phase 7 is separate because the person who wrote
the code is the worst available judge of whether it works.

**Phase 2 is the one that changes how the build feels.** It comes after contracts
because a test needs the shapes it asserts against, and before everything else because
that is what makes this verification-first rather than a good intention (P4). It leaves
the repository with a suite that fails completely, which is the correct state of a
codebase that has decided what finished means and is not finished.

Everything from phase 3 onward is then making red tests green. That is the mechanism
that makes a cheap builder safe: it is not judging whether its work is right, it is
hitting a target that already exists. Progress becomes a count anyone can watch rather
than a series of claims. `07-verification.md` covers how strongly each assertion is
verified — the ladder from types through property tests to model checking.

**The freeze rule is the load-bearing one.** Once phase 1 ends, its contracts do not
change during the build. A task in phase 4 that needs a contract change is a
`/tasks` amendment, not an edit — because a contract that moves while three surfaces
are being built against it is precisely how a feature becomes a patchwork.

**Roles are jobs, not identities.** "Domain engineer" names which skill file gets
loaded and what kind of work the task is, exactly as a team lead assigns a ticket to
whoever does that work. It is not a persona the model is asked to inhabit, and the
skill file it points at contains no claim about who the agent is (P4).

## 2. The anatomy of a task

Every task answers five questions, and a task missing any of them is not ready to
build:

1. **Where does this land?** Files, with line ranges. `new` for files that do not
   exist yet. Resolved against the graph, not remembered (P3).
2. **What does it look like when it is right?** A pointer to an existing place in the
   codebase that already does this correctly — the pattern to copy. This one line is
   worth more than a paragraph of description, because it transfers the codebase's
   actual conventions rather than a description of them.
3. **What are the steps?** Numbered, in order, concrete enough to follow without
   choosing. Three to eight is typical. If a step needs a decision, the decision was
   supposed to be made at plan time.
4. **How do I know it worked?** A command that runs and passes, or a specific
   observable outcome. Not "tests pass" — the exact invocation.
5. **What does it depend on?** The task ids that must be done first. This is the
   graph that lets `/build` order and parallelize the work.

Plus the bookkeeping: an id, the phase, the role, a size, and which spec requirement
it discharges. A task that discharges nothing is refused — that is where scope creep
enters, and refusing it costs one line.

The worked example is `architecture/tasks.example.md`. It is a complete task list for
a real feature, and it is the reference for what a well-written task looks like — not
a template to fill in, but a calibration for how much precision is enough.

## 3. Closure: nothing dropped between the spec and the plan

Two tables at the bottom of `tasks.md` do the bookkeeping a model reliably skips:

**`## Coverage`** — one row per requirement and per closure-checklist item from the
spec, naming the task that discharges it, or `waived` with a reason, or `proof-only`
for the things that are checked rather than built. The plan is not ready while a row
is empty. This is the mechanism that makes "we forgot the camera permission" into a
blank cell someone sees at the gate.

**`## Decisions`** — append-only, written during the build. When a builder is forced
to decide something the plan did not settle, one line goes here: what was decided,
why, and which tasks it binds. Every subsequent spawn carries this section. It is the
last remnant of the old decision log, and it survives because it is the cheapest
possible fix for the one coherence failure that one-pass execution does not
eliminate: two tasks in the same run resolving the same open question differently.

## 4. How the plan is produced

`/tasks` reads the approved spec and the graph. It does not read the codebase — every
file:line it writes comes from a graph query, which is why the references are
accurate and why the command is fast despite running on the strongest model.

Its passes, in order:

1. **Cut the work into tasks**, each traceable to a requirement or a checklist item.
2. **Place each task** — query the graph for where the symbols it touches live, and
   for everything that depends on them. Write the file:line sets.
3. **Assign phases** by dependency, and mark which contracts freeze at the end of
   phase 1.
4. **Mark parallelism** — within a phase, tasks whose file sets do not overlap can
   run at the same time. The graph makes overlap exact rather than guessed.
5. **Write the coverage table** and check it is full before showing anyone.

Then the human gate: the phase list, the coverage table, and the task list itself.
This is the last cheap moment to say "that is not how we do it here", and it is worth
the ten minutes it costs to read.

## 5. Building it

`/build` walks the plan. Phases in order. Within a phase, disjoint tasks in parallel
up to a small limit, the rest in sequence. Each task is one spawn: the role's skill
file, the task block, the decisions section. The builder does the steps, runs the
check, and reports.

Three rules, and they are the whole executor:

- **It does not plan.** No restructuring, no "while I'm here", no better idea.
- **It does not explore.** The task says where the work is; the graph answers
  anything structural; if neither has the answer, the plan was incomplete.
- **It does not adapt.** A task that cannot be done as written stops, writes a
  blocker line, and the run continues with independent tasks.

At the end of each phase, the phase's exit check runs — usually the test suite, plus
a graph rebuild for the directories that changed so later phases see what earlier
ones created. At the end of the last phase, a fresh agent that wrote none of the code
runs the proof phase.

This is why a cheap model works here, and it is worth being precise about why: the
model is not being asked to be smart. It is being asked to follow eight numbered
steps into two named files and run one command. That is a task a small model does
reliably, and it does it fast and for very little money. All of the intelligence was
spent upstream, once, by a model that had the whole picture — which is also the only
place intelligence was ever worth paying for.
