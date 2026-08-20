# 10 — The Subtraction Ledger

Every cut, why it was made, and what is lost. Written as a ledger rather than a
summary because a redesign that only lists what it added is a sales document. The
right-hand column is the part that matters: each of these cuts has a cost, and the
cost is stated rather than argued away.

---

## 1. What was removed

| removed | why | what is lost |
|---|---|---|
| **The hook spine** — session-start, write-gate, command-gate, post-write, subagent-complete | Never fully landed, and the failures it was designed to block stopped happening in practice. Its enforcement was also honest only under one runtime; everywhere else it degraded to advisory anyway. | Nothing mechanically blocks a scope violation, a secret, or a budget overrun any more. These become visible in the diff instead of prevented at the write. For a client who needs the block, it is a CI check they own. |
| **The tier router (T0–T3)** | Ceremony-scaling was solving a problem that phases solve better and more legibly. A tier was a number that decided how much process ran; a phase list is the process, written out. | Risk-proportional ceremony is now the planner's judgment rather than a scored table. A money-path change and a copy change get the same shape of plan, differing only in content — though the verification ladder recovers most of it, since a critical path earns a stronger verification kind and a copy change does not. |
| **Capability profiles** | An indirection layer for ceremony that keyed off model class. With ceremony mostly gone, the layer had nothing to configure. | Upgrading to a stronger model is no longer a one-line switch that sheds ceremony — there is no ceremony left to shed, which is the same outcome by a different route. |
| **`constitution.md`** and the policy tree (tiering, waivers, capability profile, enforcement parity) | Four policy files two directories from where the work happens, restating things the builder needed at the moment of building. | Cross-feature consistency now rests on the spec's constraints section and the plan's decisions table being written correctly each time, rather than on one file. This is the cut most likely to be wrong; see §3. |
| **`/phase-tasks`** as a command | Phases were never a process — they were the structure of the plan. Making them a command created a whole artifact family (`phases.md`, one contract per phase) to carry what a heading carries. | Nothing. This is the cleanest cut in the ledger. |
| **`obligations.md`, `assumptions.md`, `decision-log.md`, `phases.md`, `phase-N.contract.md`, `state.md`** as separate files | Six of the fourteen artifacts. Each had a schema, a golden exemplar, and a handoff contract; most were produced correctly and read by nobody. | The content survives as sections (`03-the-spec.md` §1, `05-the-tasks.md` §3). What is lost is machine-separability — you can no longer validate the obligation table independently of the spec. |
| **Fourteen schemas, the validator, and validate-on-write/validate-on-read** | Schema conformance was advisory for the entire life of the previous design and never once caught a real defect that a human reading the file did not. | "An artifact that fails validation does not exist" is no longer true, because nothing validates by default. Format checking is now a command anyone can run, not a gate. |
| **The concern matrix as a versioned library** (13 families, ~90 templates) | The full matrix was expensive to maintain and mostly re-derived what a strong model produces from the spec anyway. | The closure checklist survives in the spec, but it is now generated per feature rather than looked up from a curated table. Coverage will be less uniform across features. This is a real loss and §3 flags it. |
| **The ledger, the audit chain, budgets, and cost gates** | Real telemetry never landed; the numbers carried a `~` for the entire life of the design. Governing spend with estimates is theater. | No per-feature economics, no budget halt, no tamper-evident trail. Cost is now whatever the run costs, visible in the provider's own billing. |
| **Agent memory with expiry, anchors, and distillation** | Resumption-grade memory for a system that no longer spans sessions within a feature. The build is one run. | Cross-feature learning is now carried by the graph, the specs on disk, and the humans — not by a memory file. |
| **Compiled multi-tool targets** (`.claude/`, `.github/`, AGENTS.md) and the compiler | One source compiled into per-tool formats was correct in principle and produced drift-checking machinery larger than the drift it prevented. | Supporting a second AI tool now means writing its instruction file, not running a compiler. Revisit when a client actually uses two. |
| **Editions, licensing, signed releases, seats** | Business-model machinery ahead of a business model. | Nothing today. It comes back when there is revenue to protect. |
| **Nine frontmatter fields** on library entries | They served the router, the profiles, and the editions model, all gone. | Selection is now coarser: role, phase, and tech rather than seven axes. In a library of dozens this is fine; in a library of thousands it would not be. |

## 1b. What was kept after being nearly cut, and what was added back

Three things went into this rewrite as candidates for deletion and came out larger. They
are listed separately because "we reconsidered" is more useful to a future reader than a
tidy story of pure subtraction.

| item | first instinct | what changed the answer |
|---|---|---|
| **`plan.md`** (`04-the-plan.md`) | fold technology choices into the spec's constraints section | Choices and constraints are different things, and mixing them makes a decision look like a law of nature. More concretely: a technology decision binds every task and appears in `tasks.md` only as consequences, so folding it in means deciding it forty times or never writing it down. It is the third document. |
| **`/verify`** (`07-verification.md`) | keep it only as phase 7 of the build | A check that exists only inside an agent run exists once. The same evidence a person wants at the end is what CI wants on every push, and it is where a client who needs a hard block puts one. So it is both a phase and a command — execution-only, re-runnable by anyone. |
| **The MCP registry** (`09-context-and-mcp.md`) | leave external tools to whatever the runtime is already configured with | The graph solves in-repository context completely and leaves the out-of-repository half to recollection, which is where confidently wrong code comes from once everything else is fixed. A scoped, pinned registry costs one table and closes the last hallucination class. |

And one thing that is genuinely new rather than reconsidered: **verification-first as a
build phase** (P4). The previous design had test-first as a policy enforced by reading
git history after the fact. Making it phase 2 — every spec assertion as a failing test
before any implementation — is what converts a cheap builder's job from judgment into
hitting a target, and it came directly from the first dogfood run's finding that a
high-severity obligation could be closed by writing a paragraph.

## 2. What survived, and why each one earns its place

Each survivor answers P8 — *what does this do that the next model generation will not
do on its own?*

- **The spec** — a better model cannot resolve an ambiguity the person who wrote the
  brief never resolved. Someone has to decide, and it has to be written down.
- **The closure checklist inside it** — a stronger model misses fewer implied duties
  and still misses them silently. A checklist turns a silent miss into a blank cell.
- **The adversary** — self-review is structurally uninformative regardless of how
  smart the reviewer is. Independence is not a capability question.
- **The task list** — the model's plan is good; the problem is that it makes a new
  one each session. Writing it down once is what makes it the same plan on Thursday.
- **Phases and the freeze rule** — dependency ordering is what makes one-pass
  execution possible at all, and freezing contracts is what makes parallel work safe.
- **The graph** — a bigger context window does not hand a model a map of a repository
  it has never opened.
- **`file:line` discipline** — this is the graph's output made usable, and it is what
  removes exploration from the critical path.
- **The small skill library** — not because the model needs instruction, but because
  it does not know this codebase's local conventions, and eighty lines is the cheapest
  way to tell it.
- **The verifier** — "done" being self-reported is a structural problem, not an
  intelligence one.
- **The plan's technology table** — a model can pick a good library; it cannot know
  which one this organization already pays for, standardized on, or got burned by. And
  no model remembers what it picked last Tuesday in a different session.
- **Tests before code** — a model that writes both will make them agree, and it will do
  that more fluently as it gets better, not less. Ordering is the only defense and it is
  not a capability question.
- **The MCP registry** — weights are a snapshot; dependencies move weekly. A model
  trained tomorrow still will not know the API of a library released the day after.

Everything else was scaffolding for a model that needed scaffolding.

## 3. The three cuts most likely to be wrong

Stated plainly, with the signal that would mean reversing them.

**The constitution.** Repeating the constraints in each spec is fine at one or two
features a week and is obviously wrong at fifty. **Reverse if:** specs start disagreeing
with each other about versions or conventions, or the constraints section starts getting
copied stale. The fix is a small included file plus the mechanical `conventions.md`
scrape (`06-the-graph.md` §6), not the old policy tree.

**The concern matrix.** Generating the closure checklist per feature from a strong
model is good but not uniform, and uniformity is exactly what a compliance-minded
client is buying. **Reverse if:** two features in the same repository produce
materially different checklists for the same class of change, or a real miss ships
that a curated row would have caught. The fix is a checklist file per repository
seeded from real misses — much smaller than the old ninety-template matrix.

**Mechanical enforcement.** Dropping hooks is correct for a team that reads its own
diffs and wrong for an organization that needs to prove compliance to a third party.
**Reverse if:** a client's requirement is "prove nothing can bypass this" rather than
"show me what happened". The fix is a CI job over the three artifacts, not an
in-session hook — the check belongs where it cannot be skipped by whoever is running
the session.

## 4. The nine old laws, mapped

| old law | fate |
|---|---|
| P1 — enforce mechanically, instruct minimally | **Halved.** The instruct-minimally half became the new **P5** and got stricter (80 lines, not 150). The enforce-mechanically half was dropped with the hooks, and the new **P7** states honestly what replaced it. |
| P2 — never invent runtime surface | **Absorbed as practice.** No longer a law because the system references almost no runtime surface to invent. Its spirit reappears in the MCP registry's version pinning. |
| P3 — the model is the engine, the harness is rails | **Kept and sharpened** into the new **P8**. |
| P4 — ceremony is configuration, not architecture | **Superseded.** There is no ceremony left to configure, which was the goal the law was aiming at. |
| P5 — files are the only memory; every artifact has a schema | **Kept in half.** Files are still the only memory. Schemas as an enforced contract are gone; three worked examples replaced fourteen of them. |
| P6 — context is a budget, claims need citations | **Split and hardened.** The citation half became the new **P3** — from "claims need citations" to "every reference is a file and a line". The budget half became the new **P6**, which states the mechanism rather than the goal: pull, never push. |
| P7 — no feature without evidence | **Kept in spirit, dropped as a gate.** The benchmark harness it required never existed; requiring evidence from a suite that does not exist is how a law becomes decoration. Reinstated the day the suite runs. |
| P8 — fail closed, recover from anchors | **Dropped.** Fail-closed needs something that fails. Recovery is now git, used normally. |
| P9 — one source, compiled targets | **Dropped with the compiler.** Returns if a second tool is genuinely in use. |
| — | **New: P4**, the executable definition of correct exists before the code. Nothing in the old set said this; test-first was a policy inside the execution engine, checked after the fact. |

## 5. The honest summary

The previous design was right about the problems and overbuilt for the model that
existed when it was written. About two thirds of it was scaffolding whose half-life
was shorter than its build time — which is not a mistake anyone made, it is the
predictable economics of building process around a technology improving this fast.

What is left is small enough to build in weeks rather than months, and every piece of
it survives the question *what will the next model still not do for itself?* That is
the only durable filter available, and this dossier is what passes through it.
