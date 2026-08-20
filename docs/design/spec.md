# EDIFY

## Product Vision

EDIFY is a harness that sits around an AI coding agent and makes it work reliably on
large, real codebases — the kind with a million lines, fifteen years of history, four
languages, and nobody left who remembers why the payments module is like that.

It is not a model, not an agent framework, and not a wrapper around a chat interface.
It is three documents and a map: a **specification** of what is being built, a **plan**
of how and with what, a **task list** of exactly what will change and in what order, and
a **graph** of the codebase that lets any agent find anything in milliseconds without
reading it first.

A frontier model with a plain setup writes excellent code and still fails on serious
projects. Not from lack of intelligence — from four structural gaps that no model
generation closes:

- It cannot see a codebase it cannot fit in its context.
- It fragments across sessions: the same work done in parts, in different ways, never as
  one whole.
- It builds what was asked instead of what was meant.
- It writes against the library it remembers instead of the one installed.

EDIFY closes exactly those four and deliberately gets out of the way of everything else.

## Core Philosophy

**Think hard once. Then build without thinking.**

All of the intelligence in a software project is spent in three places: deciding what to
build, deciding what to build it with, and deciding how it fits into what already
exists. All three happen before any code is written. Everything after that is execution,
and execution does not need a frontier model — it needs an unambiguous instruction and a
way to check the result.

So EDIFY splits the work along that line and refuses to blur it. The spec, the plan, and
the task list get the strongest model available, take as long as they take, and each end
at a human who reads and approves. The build gets the cheapest model that can follow a
written instruction, runs the whole feature in one pass, and is forbidden from planning,
exploring, or improvising.

**And it makes "right" mechanical before the building starts.** Phase 2 of every build
turns each assertion in the spec into an executable test that fails. Everything after
that is making red go green. The builder is not judging whether its work is correct; it
is hitting a target that already exists, and progress is a number anyone can watch
instead of a claim anyone has to trust.

This has a consequence worth stating plainly, because it is the test of whether the
system is working: **if the builder had to think, the plan was incomplete.** A stalled
build is not a model failure. It is a planning defect, visible at the exact task where it
occurred, and fixable by amending one file.

The second commitment: **nothing survives that the next model generation makes
unnecessary.** Every piece of this system had to answer that question and most of its
predecessor's did not. What is left is small enough to build in weeks and durable enough
to still be useful when the models are twice as good.

## Who This Is For

### The primary user: an engineer on a large team, in a large codebase

They already use an AI coding agent and it already works well for them on small,
self-contained changes. Where it stops working is the change that touches nine files
across four modules, needs a migration, and has to match conventions established by
people who left. There, the agent explores for ten minutes, produces something plausible,
and gets it subtly wrong in a way that surfaces in code review or, worse, in production.

They do not want a new workflow. They want the same agent to stop being blind.

### The buyer: whoever is accountable for what ships

An engineering leader, a platform team, or — in the accounts where this matters most —
whoever has to explain to somebody external what was built and why. They need the work to
be legible: what was supposed to happen, what was chosen and over what, what actually
happened, and the difference, in files a person can read without running anything.

### Not the user

A solo developer on a small project. A frontier model in auto mode is already excellent
there, EDIFY adds process they do not need, and we should say so rather than sell them
something. The value starts where the codebase stops fitting in the context window.

## What It Actually Does

Four commands a developer types, one that anyone can re-run.

**`/spec`** turns two sentences into a specification. It reads the graph rather than
exploring, drafts the spec, then launches a second agent — which has never seen the
drafting session — whose only job is to find what the brief did not say. The ambiguity
nobody resolved. The permission the platform requires. The error state with no defined
behavior. Those land in the spec as open questions and as a closure checklist, and a
human spends five minutes resolving them.

**`/plan`** makes the technology decisions once, each naming the alternative it beat and
the exact version chosen, and sequences the work into milestones with the cross-cutting
strategy nothing else can own — migration numbering, build variants, bundled assets,
shared components. Skipped for work that does not need it, which is most work.

**`/tasks`** turns the approved documents into a build plan. It cuts the work into tasks,
places each one against the graph so every task names its files and line ranges, orders
them into phases, and computes which can run at the same time. A human reads it. This is
the last cheap moment to say "that is not how we do it here."

**`/build`** executes the plan in one run. Phases in order, disjoint tasks in parallel,
one agent per task, each launched with a single page: the skill file for its role, the
task block, and the zero-or-one external tools scoped to that role and phase. It does not
plan, does not explore, does not adapt.

**`/verify`** re-runs everything itself, confirms from git history that the tests came
first, exercises the acceptance scenarios as real flows, and walks the coverage table. It
runs as the last phase of every build in a session that wrote no code, in CI on every
push, and by hand whenever anyone wants it.

## The Three Documents

### `spec.md` — what is being built

One file per feature. It carries the brief verbatim, the numbered intent, the constraints
that are *given* (target platform, versions already installed, offline requirement, the
real build and test commands), the requirements with their testable assertions,
everything the feature entails that nobody asked for, the open questions, and the
non-goals.

Each assertion declares **how strongly it is verified** — types, example test, contract,
property test, model check, or proof — and the rule is to pick the strongest kind that is
cheap for that assertion, not the strongest available. An assertion about a pure function
defaults to a property test.

### `plan.md` — how, with what, in what order

The technology decisions, each with an exact version and the alternative it beat. The
milestones and the dependency rules between them, each rule stating its reason. The
cross-cutting strategy. The context seeds — `(file, line-start, line-end, why)` pointers
resolved against the graph so `/tasks` inherits them instead of re-deriving them. The
risks, each mapped to the milestone that mitigates it.

Written when the feature introduces a technology, spans milestones, needs cross-cutting
strategy, or will be built by more than one person. Skipped otherwise, and skipping it is
the normal case.

### `tasks.md` — exactly what will change

Structured in phases: foundation, contracts, **verification**, core, surfaces,
integration, hardening, proof. You finish a layer and the next one rests on it without
asking questions — LEGO, not a to-do list.

Everything phase 1 produces is **frozen** when phase 1 ends. That single rule is what
makes the surfaces phase parallel-safe and turns integration into confirmation rather
than discovery.

Every task answers five questions: where does this land (files, with line ranges), what
does it look like when it is right (a pointer to code in this repository that already
does it correctly), what are the steps (numbered, unambiguous), how do I know it worked
(a command, exactly as invoked), and what does it depend on.

The worked reference is `architecture/tasks.example.md`. That file is the product's most
important artifact, because the difference between a good plan and a plausible one is
entirely in that level of detail, and it does not survive being described in the
abstract.

## The Map and the Two Registries

**The graph** — a mechanically extracted map: every file, module, exported symbol, route,
and table, with the edges between them, as sorted text. Built by a deterministic binary.
Never by a model, at any stage, for any reason — including where a language is not
covered, in which case the graph simply has no nodes for it and says so. It answers three
questions in under a second: where is this defined, what breaks if it changes, and do
these two sets of files overlap. It is the only thing the repository's root instruction
file points at.

**The skill library** — short, plain descriptions of how a competent engineer does one
kind of job in a large codebase. Eighty lines each. Found by exact lookup on
`role · phase · tech`, never by a model reading a directory to decide.

**The MCP registry** — the servers this repository may reach for things that are not in
it. One entry by default: a documentation server that serves the real API of the exact
library version the plan named. Every entry is pinned and **scoped to the roles and
phases that need it**, because a connected server injects its tool descriptions into
every session whether or not they are used.

## Constraints

- **The harness** — markdown files with flat YAML frontmatter. Git-native, readable on
  any forge, no build step.
- **The binary** — a self-contained static executable per platform, in a compiled
  language, no runtime dependency. Forced by two facts: the graph extractor is already a
  static binary, and the accounts that need this most will not install a language runtime
  on a build server without a procurement process.
- **The extractor** — a pinned third-party static binary, wrapped, emitting our TSV
  contract. Adoption is blocked on a license and provenance review; if that fails we
  write a small syntax-tree extractor to the same contract. The contract is the asset.
- **Offline by default.** Everything works with no network except `upgrade` and any MCP
  server marked `outbound`, which are simply absent on an air-gapped network and say so.
- **No server, no daemon, no database.** Files, and a binary that reads them.
- **The host runtime is not ours.** EDIFY rides the AI coding agent's runtime and its
  release velocity, and references as little of its surface as possible.

## What This Entails

The duties this product creates beyond the features above.

- **Every skill file that comes from outside carries its license and its upstream
  commit.** This library composes into other companies' repositories. Permissive licenses
  only; unlicensed content is rejected at the door, mechanically, as a lookup rather than
  a judgment.
- **Untrusted text never enters a customer's repository.** Gathering, screening, and
  rewriting public skills happens in EDIFY's own repository, behind a human. A poisoned
  skill file is persistent trusted context in every session that loads it.
- **External tool output is untrusted input.** Marked with origin and version, never
  written into the graph, flagged rather than followed when it contains directives.
- **The graph never contains model-authored or externally-fetched content.** One narrated
  edge and every downstream consumer is resting on a guess wearing the costume of a fact.
- **Missing coverage is visible.** A language the extractor does not handle produces a
  gap that is stated, not filled by inference. A server that cannot be reached is absent
  and says so, rather than silently falling back to recollection.
- **Installing into an existing repository merges, never overwrites.** Somebody wrote
  that instruction file on purpose.
- **Every claim about enforcement is honest.** EDIFY does not block anything at runtime.
  Where a hard block is required, it is `/verify` in CI with a non-zero exit, owned by the
  customer, and we say so rather than implying we ship one.

## Core Product Rules

1. Three documents and a map: a spec, a plan, a task list, a graph. Anything that is not
   one of those, or a tool that writes or reads one, is not part of EDIFY.
2. All thinking happens before the build. The builder follows instructions and never
   plans.
3. Every reference to code is a file and a line range, or the literal `new`.
4. The executable definition of correct exists, and fails, before the code that satisfies
   it. Each assertion declares how strongly it is verified.
5. A model never writes the graph, never chooses which skill applies, and never chooses
   which external server loads.
6. Contracts freeze at the end of phase 1 and do not move during the build.
7. An agent launch carries one skill file, one task block, and the servers scoped to its
   role and phase. Everything else is pulled on demand, not pushed.
8. Instructions explain how the work goes; they never command, and they never claim an
   identity. Eighty lines for a skill, a hundred and fifty for a specialist.
9. The adversary is not the author, and the verifier did not write the code.
10. Nothing survives that the next model generation makes unnecessary. Every piece of
    scaffolding carries the question of when to check whether it still earns its place.
11. Governance means a human can read what was supposed to happen, what was chosen, what
    happened, and the difference. It does not mean anything is mechanically prevented,
    and we do not say otherwise.

## Open Questions

| # | question | reading adopted | who resolves |
|---|---|---|---|
| Q-1 | Does the constraints section repeated per spec drift once a repository has fifty of them? | Accept the repetition; the fix if it drifts is a small included file plus the mechanical conventions scrape, not a policy tree | first team past ~20 features |
| Q-2 | Is the closure checklist, generated per feature, uniform enough for a customer whose value is compliance? | Accept per-feature generation; a seeded per-repository checklist is the fix if two features diverge on the same class of change | first compliance-driven engagement |
| Q-3 | Does the extractor pass a license and provenance review? | Assume yes; if not, write a small syntax-tree extractor to the same TSV contract at roughly twice the cost, same slot in the build order | before the graph commands are built |
| Q-4 | How cheap can the build model be before the plan has to compensate? | Start at the cheapest instruction-following class and move up only on evidence; a stall is first read as a planning defect, not a model deficiency | first ten real builds |
| Q-5 | Does one-pass execution hold for a feature of forty tasks, or does something force a session boundary? | Assume it holds; if it does not, the resume path is reading `tasks.md`, which already works | first large feature |
| Q-6 | Is the phase-2 verification pass affordable, or does writing every assertion as a failing test cost more than it saves? | Assume it pays, because it is what makes the cheap builder work at all — but the cost is real and unmeasured | first five features, measured as phase-2 tokens against total build tokens |
| Q-7 | How often is `plan.md` actually written, in practice? | Assume a minority of features. If it turns out to be most of them, the skip rule is wrong; if it is almost none, the artifact is not earning its place | after ~20 features |

## Non-Goals

- Not an agent runtime, a model router, or an orchestration framework.
- Not a wrapper around the chat interface. No `edify run <prompt>`.
- Not a package manager for the open prompt ecosystem, and not a marketplace for external
  tool servers. Two curated registries, one door each.
- Not a server, dashboard, or web product.
- Not a runtime enforcement layer. Nothing blocks; everything is visible.
- Not formally verified software. A verification ladder is made available and each rung is
  named with when it is worth climbing. Most projects will live on the lower four rungs,
  and that is the correct outcome rather than a failure to reach the top.
- Not a system for making a weak model competent. It makes a competent model efficient,
  and the difference is the whole product.
- Not a replacement for code review, CI, or engineering judgment. It makes all three
  cheaper by making the intent, the choices, and the plan explicit before the diff exists.

## How Success Is Measured

Not by process compliance. Four observable things:

1. **A feature that would have taken a day of back-and-forth builds in one pass.** The
   plan is read once, the build runs once, and the diff matches the plan.
2. **A new engineer's first change to an unfamiliar module lands correctly**, because the
   plan told them exactly where it goes and which existing code to copy.
3. **The suite that proves the feature was written before the feature**, and `git log`
   shows it.
4. **Somebody who was not in the room can read the spec, the plan, the task list, and the
   diff, and tell whether the right thing was built.** That is the whole governance claim,
   and it is either true when you look or it is not.

If a team runs EDIFY and cannot point at those four, the harness is ceremony and should be
deleted rather than defended.
