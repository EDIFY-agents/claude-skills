# 05 — Skills and Spawning

Four things: the format an entry is written in, what a skill file looks like on disk,
which files it is allowed to open, and what gets sent when an agent is launched.
Rationale is in `../08-agents-and-skills.md`; this is the shape.

---

## 1. The open knowledge format

The format comes first because everything below is an instance of it, and because a
consumer that only implements this section can already read the library.

**Markdown with flat YAML frontmatter, one entry per file, in a flat directory** — the
shape the ecosystem has converged on, kept for interoperability. Scalars only: no
nesting, no anchors, no multi-line values, no lists in block form. Multi-valued fields
are space-separated on one line, which keeps them diffable and parseable by a two-line
awk script.

| field | type | required | values |
|---|---|---|---|
| `name` | id | yes | `[a-z0-9-]+`, stable, unique, and by convention the filename without `.md` |
| `description` | string | yes | one line, what it is for |
| `kind` | enum | yes | `skill` \| `agent` |
| `role` | enum | yes | `planner` \| `adversary` \| `test` \| `implementer` \| `debugger` \| `verifier` |
| `phase` | list | yes | which of phases 0–7 it serves, space-separated |
| `tech` | list | yes | stack or domain ids from `edify/harvest/vocab.md`, or `any` |
| `provenance` | enum | yes | `original` \| `adapted` \| `client` |
| `license` | string | if `adapted` | SPDX id plus `repo@commit` of the upstream; `-` when `original` |

Two optional keys are tolerated beside the eight and carry no meaning to the lookup:
`source`, a one-line note on where an adapted entry's method came from in prose, and
`updated`, a date. Anything else is an unknown key.

The rest of the format, in full:

- **The frontmatter delimiter is `---` on its own line**, first line of the file and
  again after the last field. Nothing precedes it.
- **The body is the four sections** of §2, in that order, under budget.
- **Unknown key, missing required key, or a value outside its set = the file is
  invalid**, reported by `edify check` and skipped by the indexer. Loose metadata is
  fine for a wiki and useless for a lookup table.
- **The file is UTF-8, and only UTF-8 that renders as what it parses as.** Zero-width
  characters, bidirectional overrides, and unicode format characters send a candidate to
  quarantine — text that reads as one thing and parses as another is the whole trick.
  That scan runs on the way in, at harvest (`src/edify/harvest/screen.py`), because it is
  a question about a stranger's bytes rather than about an entry already in the library.

Eight fields. The nine that are gone — version, edition, eval status, work-kind,
service-archetype, surface, tier, depth, client-archetype — served the tier router, the
capability profiles, and the editions model, none of which exist any more. `provenance`
and `license` stay because shipping other people's work into a company's repository is
a legal question, not a governance one; what those two fields oblige is §6.

## 2. The skill file

```markdown
---
name: implementer-node
description: Implements a build task in a TypeScript/Node service codebase.
kind: skill
role: implementer
phase: 0 1 2 3 4 5
tech: typescript node
provenance: original
license: -
---

# Implementer — Node / TypeScript

## What you're doing
One task from a build plan. It names its files, the pattern to follow, the steps, and
the check that proves it worked. You do exactly that and nothing beside it.

## How the work goes
1. Read the task block. Open only the file ranges it names.
2. Open the pattern it points at and read it properly. That code is the convention —
   copy its shape, its naming, its error handling, its test style. Do not improve it.
3. If the task creates a symbol, ask the graph first whether one already exists:
   `edify graph where <name>`. Reuse beats writing.
4. Write the test before the code where the task's check is a test. The plan's check
   is the target; write toward it.
5. Do the steps in order. If a step is ambiguous, do the reading that resolves it —
   do not pick and move on.
6. Run the done-check exactly as written. Not a similar command; that one.
7. If it fails, fix your work. If it fails because the task is wrong, stop (below).

## When you're stuck
Two things end a task early, and both are one line rather than a workaround:
- **The task is wrong** — the file moved, the pattern does not exist, the step is
  impossible as written. Write `BLOCKED T-n: <what you found, with file:line>` and stop.
- **The task is silent on something real** — a format, a name, a default nobody chose.
  Pick the option the surrounding code already uses, and write it into `## Decisions`
  as one row. Then continue.

Do not restructure code the task did not name. Do not fix an unrelated bug you notice —
mention it in your report. Do not expand scope because it seems obvious; whoever wrote
the plan had the whole picture and you have one task.

## What you hand back
Four lines: the task id, the files you changed, the done-check output verbatim, and
either `done`, `blocked: <reason>`, or `decided: <the row you added>`.
```

Sixty-odd lines. That is a complete skill file, and most are shorter.

**What is not in it:** who the agent is, how expert it is, why the rules exist, what
EDIFY's principles are, general advice about writing good TypeScript, capitalized
imperatives, or anything about how careful to be. All four of those are how skill
files reached five hundred lines in the previous generation, and none of them improved
output.

**Budgets:** ≤80 lines for a skill, ≤150 for a deep specialist that carries real
stack-specific knowledge. Checked by `edify check`.

## 3. The index

`edify index` walks `skills/`, validates the frontmatter, and writes a sorted TSV:

```
role   phase  tech        name                 path
implementer  3  react      implementer-react    skills/implementer-react.md
implementer  3  typescript implementer-node     skills/implementer-node.md
verifier     6  any        verifier             skills/verifier.md
```

Sorted on `role · phase · tech`, so resolving a task's skill is a binary search over a
sorted file: sub-millisecond, no model, flat cost as the library grows. A task names
its role; the repository's stack supplies `tech`; the phase comes from the task
header. One lookup, one line of output, one file path.

Resolution order when nothing matches exactly: exact `tech` match, then `any`, then
the role's default. If none of the three resolve, the task fails at the gate rather
than at build time — a task whose role has no skill is a plan defect.

**A model never chooses.** Not because its judgment is bad, but because a lookup is
free, deterministic, and gives the same answer on Tuesday.

## 4. The context references

The closed list of paths a launched agent may open, and which roles open which. Anything
not on it is not reachable by policy but by construction: nothing tells the agent it is
there, and P6 says nothing will. Why each line is a pull rather than a push is
`../08-agents-and-skills.md` §4; this is the resolution.

| path | resolves from | roles | when |
|---|---|---|---|
| `.edify/skills/index.tsv` | `role · phase · tech` | the launcher | at resolution, before the spawn |
| `.edify/skills/<name>.md` | the index row | the launcher | pushed, once, above the cache line |
| `.edify/stack.tsv` | `edify init`, scraped | the launcher | supplies `tech` for the lookup |
| `.edify/mcp.md` | `role × phase` exact match | the launcher | §7, usually resolves to nothing |
| `specs/<feature>/tasks.md` | the task id | every role | one block, pushed |
| `specs/<feature>/tasks.md` `## Decisions` | — | every role | pushed when non-empty |
| the `file:line` ranges in the task | the task text | every role | pulled, at the cited range only |
| `.edify/graph/*.tsv` | `edify graph where`, `dependents` | every role | pulled, one query at a time |
| `.edify/conventions.md` | `edify init`, scraped | implementer, test | pulled when the stack matters |
| `.edify/formats/*.format.md` | the artifact being drafted | planner | pulled while drafting |
| `specs/<feature>/spec.md` | the feature | planner, adversary, verifier | pulled |
| `specs/<feature>/plan.md` | the feature | planner, debugger | pulled |

**Never, for any role:** another feature's `specs/` directory, a previous session's
transcript, the graph read as a file rather than queried, `harvest/staging/**` or
`harvest/quarantine/**`, or any external content written into `.edify/graph/`.

**`plan.md` is withheld from implementers**, and it is the subtlest line in the table: a
builder with access to the reasoning behind the plan has judgment again, and judgment at
build time is the one thing the executor is defined by not having. The debugger gets it
because by then the plan is what is under suspicion.

A skill file that needs something off this table is not permitted to go looking. The
entry is wrong, or the system is missing a capability, and both are `BLOCKED` lines
rather than exploration.

## 5. The laws a skill file answers to

`../01-principles.md` states eight design laws, and six of them are things a skill file
can actually violate. Two of the six are countable and the rest are not. Which is which
is written down here rather than left to be discovered, because P7 is explicit that a
rule with no mechanism behind it is guidance and gets labeled guidance.

**Checked** — `edify check`, implemented in `src/edify/formats/skill.py`:

| code | what it catches | law |
|---|---|---|
| `skill-over-budget` | body over 80 lines, or over 150 for `kind: agent` | P5 |
| `skill-missing-field` | one of the seven always-required keys absent | §1 |
| `skill-unknown-field` | a key outside the format | §1 |
| `skill-bad-name` | `name` not `[a-z0-9-]+` | §1 |
| `skill-bad-kind` · `-role` · `-phase` · `-provenance` | a value outside its set | §1 |
| `skill-missing-license` | `provenance: adapted` with no `license` | §6 |

An invalid file is reported **and skipped by the indexer**, which is the consequence that
matters: an entry that fails the format resolves for nothing, so it does not exist as far
as a task is concerned.

**Not checked** — read at review and at the harvest door:

| law | what a reader is looking for | the violation |
|---|---|---|
| **P5** explain, don't command | prose that briefs rather than orders | capitalized MUST blocks, a persona line, an expertise claim, a self-attestation section |
| **P3** file and line | every path in the body carrying a line range or the literal `new` | "see the auth module" |
| **P2** build dumb | no step that hands the agent a scope decision | "refactor as appropriate" |
| **P1** three documents and a map | no artifact named outside spec, plan, tasks, graph | an entry that writes its own side file |
| **P4** correct before code | a `role: test` entry that does not also implement | structural — the phase ladder separates them, not a checker |
| **P8** no scaffolding | every line about working *here* | "remember to handle errors" |

These stay unchecked on purpose rather than pending. A regex that hunts the word MUST
catches the word and not the register, and `edify check` reporting a clean file would
then mean less than it does now.

## 6. What `provenance` and `license` oblige

The two fields that survived a cut of nine, because this half is not ours to redesign.

| `provenance` | what it means | where it may ship | `license` |
|---|---|---|---|
| `original` | EDIFY worked out the method | anywhere the library ships | `-` |
| `adapted` | the method came from someone else's file | anywhere, once the licence permits it | SPDX id + `repo@commit`, required |
| `client` | true only for one customer's codebase | that repository, and nowhere else | `-` |

- **The allowlist is permissive-only and mechanical**: `MIT`, `Apache-2.0`,
  `BSD-2-Clause`, `BSD-3-Clause`, `ISC`, `Unlicense`, `CC0-1.0`, in
  `src/edify/harvest/screen.py`. Copyleft, unlicensed, and unresolvable strings are
  rejected — a reciprocal obligation reaching a customer's tree through a library they
  installed for other reasons is not ours to accept for them. A model never answers this
  question; a lookup table does.
- **Attribution travels.** MIT, BSD, and ISC require the copyright notice to survive;
  Apache-2.0 adds NOTICE. `license` carrying the upstream `repo@commit` is what makes
  that recoverable after a rewrite that changed most of the bytes.
- **Deletion is not authorship.** If the method is the upstream's, the entry is
  `adapted` however little of the original text remains.
- **`client` entries never enter `harvest/`** and never come back out into the library.
  A method worth generalizing is rewritten with the client's particulars — names, hosts,
  customers, anything personal — removed first.

## 7. The spawn payload

```
┌─ stable across launches of this role in this run ──────────┐
│  the skill file                            ~60 lines       │
│  the MCP servers scoped to role × phase    0–1, usually 0  │
└────────────────────────────────────────────────────────────┘
┌─ varies per task ──────────────────────────────────────────┐
│  the task block from tasks.md              ~25 lines       │
│  ## Decisions, if non-empty                ~5 lines        │
└────────────────────────────────────────────────────────────┘
```

About a page. That is the whole prompt.

**Not sent:** `spec.md`, `plan.md`, the rest of the task list, the repository structure,
the graph, any file contents, fact excerpts, or prior conversation. The task's
`file:line` references tell the agent which ranges to open, and it opens them itself.

**`plan.md` is withheld from the builder deliberately**, for the reason in §4 — and it is
withheld rather than merely unsent, which is why it appears on that table with its roles
named.

**MCP servers sit above the line** because a server's tool descriptions are identical
across launches of the same role — putting them in the volatile half would churn the
cache for no reason. Which servers load is an exact-match lookup on the task's role and
phase against `.edify/mcp.md` (`07-mcp.md` §2), and the common answer is none.

**The stable-then-volatile order is not cosmetic.** Everything above the line is
byte-identical across every launch of that role within a run, so the provider's prompt
cache serves it. A timestamp, a warning string, or a run id leaking above the line
silently halves the cache hit rate across a forty-task build. It costs nothing to get
right and is invisible when got wrong, which is why it is written down here.

## 8. The roles

| role | when | model | independence |
|---|---|---|---|
| planner | `/spec`, `/plan`, `/tasks` | strongest | — |
| adversary | `/spec`, after the draft | strongest | never the drafting session |
| test | phase 2, one task per assertion group | strong — a bad test is worse than none | may not also implement the code it tests |
| implementer | every phase 3–6 task | cheapest that follows instructions | — |
| debugger | after two failed checks | strongest — this is thinking work | gets the accumulated failure evidence |
| verifier | phase 7 and `/verify` | strong | never a session that wrote code |

The three independence rules are the only ceremony left in the system, and each costs one
extra launch. A session reviewing its own work agrees with itself; a builder declaring
its own work done is an assertion, not evidence; and an agent that writes both the test
and the code will make them agree, more fluently as models improve rather than less.

## 9. Choosing the model

There is no capability profile and no tier table. The rule is three lines:

- **Planning and adversarial work run on the strongest model available.** A mistake
  here is paid for again on every task.
- **Building runs on the cheapest model that follows instructions reliably.** If it
  cannot, that is evidence the plan was under-specified, not that the model was too
  small — check the plan before reaching for a bigger model.
- **The verifier is never weaker than what built the code.** A checker weaker than the
  maker quietly reintroduces self-attestation while looking like review.

Switch models only at a launch boundary. Switching mid-session throws away the cache.
