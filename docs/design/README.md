# EDIFY — Design Dossier

**Date:** 2026-08-06
**Status:** Canonical design. This folder replaces `Research/design/` as the design
source of truth.
**Supersedes:** `Research/design/` (00–10) and `Research/design/architecture/`
(00–11), kept as historical record and as the source of the parts carried forward.

---

## What changed, and why this is a rewrite rather than an edit

The previous dossier was designed in June and July 2026 against a model that needed to
be told how to think. It answered that with five engines, nine design laws, fourteen
artifact schemas, an always-on hook spine, a tier router, capability profiles, a concern
matrix, obligation closure, assumption registers, decision logs, phase contracts, and an
enforcement-parity ledger. Every one of those was a defensible answer to a real failure
we had measured.

Then the failures stopped happening.

Running the pipeline through 2026-07 and 2026-08 on real work, in auto mode, with no
hooks firing, the frontier model did not need most of it. It plans well. It retrieves
well. It follows a written instruction without being threatened. The ceremony that
remained was not preventing errors — it was producing artifacts nobody read, in a
pipeline slow enough that people worked around it.

**Four things did not stop happening**, and all four are structural rather than
intelligence-bound — which is exactly why a better model does not fix them:

1. **It cannot see a large codebase.** Not "does not understand" — cannot see. Every
   session starts blind and re-derives the same map, expensively and slightly
   differently each time.
2. **It fragments across sessions.** Work split over many sessions is done in parts, in
   different ways, never as one coherent whole. Session seventeen cannot see what
   session three decided. This was the founding EDIFY insight and it is still true.
3. **It builds what was asked instead of what was meant.** An ambiguous brief produces a
   confident, well-built, wrong thing.
4. **It writes against libraries it remembers rather than the ones installed.** Weights
   are a snapshot; dependencies move weekly. This is the one class of hallucination that
   in-repository citations cannot catch, because the cited thing is not in the
   repository.

So EDIFY shrinks to what fixes those four, and drops the rest.

## The new shape, in one line

> **Three documents and a map. Think hard once, then build without thinking.**

| artifact | fixes | who writes it |
|---|---|---|
| **`spec.md`** | building the wrong thing | a frontier model + an adversary + one human gate |
| **`plan.md`** | technology decisions nobody made on purpose | a frontier model + one human gate |
| **`tasks.md`** | fragmentation | a frontier model + one human gate |
| **the graph** | blindness in a large codebase | a deterministic extractor, never a model |
| **the MCP registry** | inventing a library's API | a curated list, scoped per role |

Everything a developer does is four commands: `/spec`, `/plan`, `/tasks`, `/build`. The
first three are slow and expensive and end at a human. The fourth is fast and cheap and
ends at working software. A fifth, `/verify`, runs the evidence and can be re-run by
anyone at any time.

## Reading order

| doc | what it defines |
|---|---|
| `01-principles.md` | the eight laws this design must satisfy |
| `02-system-overview.md` | the artifacts, the loader, and the life of one feature |
| `03-the-spec.md` | what `spec.md` carries — intent, assertions, closure, open questions |
| `04-the-plan.md` | what `plan.md` carries — technology decisions, milestones, cross-cutting strategy |
| `05-the-tasks.md` | the phase ladder and the task anatomy — the LEGO rule |
| `06-the-graph.md` | how a model sees a codebase it cannot fit in its context |
| `07-verification.md` | verification-first, the verification ladder, and where formal methods actually pay |
| `08-agents-and-skills.md` | the open knowledge format, skill files, what a skill may read, the laws it answers to, and the spawn payload |
| `09-context-and-mcp.md` | reaching outside the repository without taxing every session |
| `10-what-we-dropped.md` | the subtraction ledger, and an honest account of what is lost with each cut |
| [`../pricing.md`](../pricing.md) | how this is paid for: offline licensing, the free/paid split, and the commitments that come with it |
| `spec.md` | the specification for EDIFY itself — what we are building and how |
| `architecture/` | the buildable blueprint: formats, commands, CLI, folder trees, worked examples |

Two exemplars sit beside them, both real artifacts from real products rather than
invented illustrations: `spec-ex.md` for what a good specification reads like, and
`plan-ex.md` for what a good technical plan reads like. The third,
`architecture/tasks.example.md`, is the worked task list.

## What did not change

The mission is the same: **enable every team to leverage AI in complex scenarios and
complex codebases, with governance.** What changed is the definition of governance.

Governance used to mean *a control that mechanically blocks a violation* — hooks,
validators, gates that fail closed. It now means *a written record a human approved and
anyone can check the work against*. The spec says what will be built. The plan says with
what, and over what alternatives. The task list says exactly what will change, in which
file, at which line, in what order. The tests say what correct means, and they exist
before the code does. The run produces a diff that either matches or does not.

That is weaker than a hook and stronger than nothing, and it is honest about which it
is. `10-what-we-dropped.md` states the cost of the trade in full rather than claiming
there was none.
