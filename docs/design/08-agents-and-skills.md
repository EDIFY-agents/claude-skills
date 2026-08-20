# 08 — Agents and Skills

**The failure it prevents:** the spawn tax. Every agent launch pays for a cold start,
and what gets pushed into that cold start is paid for on every single launch whether
or not it is used. A five-hundred-line skill file, a constitution, a decision history,
and a repository tour, multiplied by forty task spawns, is most of the cost of a
build and most of the reason builds are slow.

**The design goal:** a spawn payload that fits on a page, and skill files a new hire
could read.

---

## 1. The open knowledge format

Everything after this section assumes one format, so it goes first.

A skill is **one markdown file with flat YAML frontmatter, in a flat directory**.
Nothing else: no manifest that has to agree with the directory, no per-entry folder, no
packaging step, no build. Git tracks it, any forge renders it, `grep` finds it, and a
two-line awk script parses it. That is the shape the open ecosystem converged on, and we
keep it for interoperability rather than taste — an entry written for EDIFY stays
readable by anything else that reads skill files, and an entry written elsewhere is one
rewrite away from being readable here.

"Open knowledge" is meant in both of its senses, and they are separate obligations. The
**format** is open: no proprietary container, no lock-in, no tool required to read an
entry beyond the one that reads text. The **content** is open in the licensing sense:
every entry carries a licence that permits redistribution and derivative work under the
Open Definition's permissive reading, because this library composes into other companies'
repositories and a reciprocal obligation travelling into a customer's tree is not ours to
accept on their behalf. The mechanical half of that is the licence screen in
`architecture/10-harvest.md` §1 ②; the obligations it leaves behind are §5 below.

The fields, and this is the whole list:

| field | required | what it is | what it is for |
|---|---|---|---|
| `name` | yes | stable identifier, `[a-z0-9-]+`, matches the filename | the join key everything else uses |
| `description` | yes | one line: what this is for | what a person reads when choosing to keep it |
| `kind` | yes | `skill` or `agent` | whether it is loaded as a payload or launched as a runtime |
| `role` | yes | the job it fills — `planner`, `adversary`, `test`, `implementer`, `debugger`, `verifier` | first lookup key; a task names its role |
| `phase` | yes | which of phases 0–7 it serves, space-separated | second lookup key; a task header carries its phase |
| `tech` | yes | stack or domain ids from `edify/harvest/vocab.md`, or `any` | third lookup key; the repository's stack supplies it |
| `provenance` | yes | `original`, `adapted`, or `client` | who wrote the method, which decides what may ship where |
| `license` | when adapted | SPDX id plus `repo@commit` of the upstream | the attribution that has to survive the rewrite |

Eight fields, down from seventeen. The nine that were dropped — version, edition,
evaluation status, work-kind, service-archetype, surface, tier, depth,
client-archetype — existed to serve the tiering router, the capability profiles, and
the editions model, all of which are gone. `provenance` and `license` stay because
harvesting other people's work into a library that ships to companies is a legal
question, not a governance one, and legal questions do not get simpler when a design
does.

The library compiles to one sorted lookup table keyed on `role · phase · tech`. Finding
the right skill is an exact-match lookup: one line of output, sub-millisecond, no model
involved, flat cost as the library grows. Adding a capability changes the library and
never changes a command.

**A model never decides which skill applies.** The task says its role; the role and the
stack resolve to a file. This is not distrust of the model's judgment — it is that a
lookup is free, deterministic, and reproducible, and asking a model to browse a directory
to make the same decision costs tokens and gives a different answer on Tuesday.

## 2. What a skill file is

A short, plain explanation of how a competent engineer does one kind of job inside a
large codebase. Not a specification, not a policy, not a persona. It reads like a
colleague explaining how the work actually goes.

The shape, in order:

- **Frontmatter** — the metadata that makes it findable (§1). Eight lines.
- **What you're doing** — two or three lines. The job, plainly.
- **How the work goes** — the numbered method. This is the body and most of the file.
- **When you're stuck** — what to do instead of improvising: which line to write,
  where, and then stop.
- **What you hand back** — the short structured report the run collects.

**Budget: ≤80 lines for a skill, ≤150 for a deep specialist.** The previous design
allowed 150 and 400 and used all of it; the reduction is the single largest
efficiency change in this redesign, and it holds because most of what filled those
lines was policy restatement and MUST blocks that are gone.

## 3. How they are written

The rule is: **explain how to work, not what to obey.**

A good skill file is written the way you would brief a strong engineer who is new to
the codebase and does not know your conventions. It tells them the sequence — look
here first, then check this, copy the shape of that, run this before you say you're
done. It names the traps specific to this kind of work. It says what "finished" looks
like.

What it never contains: capitalized imperatives with nothing behind them, claims
about who the agent is or how expert it is, restatements of rules that live in the
spec, general engineering advice the model already knows better than we do, or
anything about the model's own reliability. Those are the four ways skill files got
long, and none of them made output better.

An honest test before adding a line: *would a competent engineer who has never seen
this repository be worse off without this line?* If the line is about engineering in
general rather than about working here, cut it. The model knows how to write a test.
It does not know that in this codebase the fixtures live in an unusual place and the
integration suite needs a flag.

## 4. What a skill may read: the context references

A skill file is short because almost nothing is carried into the session with it. What
replaces the carrying is a small, named, closed set of places the agent may go — each
one a file at a path, none of them a search. This is the list. A skill file that needs
context not on it is describing a capability the system does not have, and that is a
finding rather than a licence to explore.

| reference | who reaches for it | how it arrives | why it is not pushed |
|---|---|---|---|
| `.edify/skills/<name>.md` | the launching command | pushed at spawn | it is the one thing pushed, which is the point of keeping it to a page |
| `.edify/skills/index.tsv` | the launching command | exact-match lookup | a resolution table, never context |
| `specs/<feature>/tasks.md` | every role | one block, pushed | the block carries what the spec decided; the rest is another agent's work |
| `specs/<feature>/spec.md` | planner, adversary, verifier | pulled | a builder gets the assertions through its task, already resolved |
| `specs/<feature>/plan.md` | planner, debugger | pulled — **withheld from implementers** | reasoning restores judgment, and judgment at build time is what the executor is defined by not having |
| `.edify/graph/*.tsv`, via `edify graph where` and `dependents` | any role | pulled per query | a map is queried; carrying it is paying for a million lines to answer one question |
| the `file:line` ranges the task names | every role | pulled | P3 is what makes this affordable — a cited range opens without exploring |
| `.edify/conventions.md` | implementer, test | pulled once when the stack matters | scraped from config files, no model wrote a line of it |
| `.edify/formats/*.format.md` | planner | pulled while drafting | only the role producing an artifact needs its format |
| `.edify/stack.tsv` | the launching command | read at resolution | supplies `tech` for the lookup |
| `.edify/mcp.md` | the launching command | scoped to `role × phase` | a connected server taxes every session for value taken twice |

**Off the list for every role, in every phase:** another feature's spec, plan, or task
list; a previous session's conversation; the graph as a file rather than a query; any
file under `harvest/staging/` or `harvest/quarantine/`, which hold a stranger's bytes
verbatim; and external content of any kind entering the graph, which
`01-principles.md` rules out as an anti-goal rather than a preference.

The distinction underneath the whole table is **push versus pull**, and it is P6. Pushed
context costs tokens on every launch whether or not it gets used, and it costs them at
the most expensive moment. Pulled context costs nothing until the agent actually needs
it, and the agent is a better judge of that than the planner was.

## 5. The laws a skill file answers to

Two kinds, and conflating them is how policy files got written. The first kind we wrote
and may amend in writing. The second kind we did not write and may not.

**The design laws** — `01-principles.md`, and these six are the ones a skill file can
actually violate:

| law | what it means for a skill file | what the violation looks like |
|---|---|---|
| **P2** plan hard, build dumb | the file explains method; it never asks the agent to decide scope | "use your judgment about how far to refactor" |
| **P3** every reference is a file and a line | any path it names carries a line range, or the literal `new` | "see the auth module" |
| **P4** correct exists before the code | the test role writes failing tests from the spec's assertions, and does not implement them | a skill that writes tests after the code it also wrote |
| **P5** instructions explain, they do not command | no MUST blocks, no persona, no expertise claim, no self-attestation | "You are a world-class Rust engineer. You MUST always…" |
| **P6** pull context, never push it | it names where to look; it does not carry what it found | a repository tour pasted into the file |
| **P8** nothing a better model makes unnecessary | every line is about working *here*, not about engineering | "remember to handle errors" |

The budget — **≤80 lines for a skill, ≤150 for a deep specialist** — is P5 made
countable, and `edify check` counts it. It is not austerity for its own sake: past about
eighty lines the marginal line displaces the actual work in the model's context.

**Actual law** — the part that is not ours to amend, and the reason `provenance` and
`license` survived a cut that removed nine other fields:

- **An adapted entry ships someone else's expression.** `license` records the SPDX id
  and the upstream `repo@commit` so attribution survives a rewrite that changed most of
  the bytes.
- **The permissive allowlist is a composition decision, not a philosophical one.**
  MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Unlicense, CC0-1.0 — the set is in
  `src/edify/harvest/screen.py` and it is a lookup, never a prompt. Copyleft is absent
  deliberately: a reciprocal obligation arriving in a customer's repository through a
  library they installed for other reasons is a liability we would be creating for them.
- **Attribution obligations outlive the rewrite.** MIT, BSD, and ISC require the
  copyright notice to travel; Apache-2.0 adds its NOTICE requirement. CC0 and Unlicense
  require nothing, and the record is kept anyway, because provenance is a security
  property as much as a legal one — when an entry turns out to be poisoned, the question
  asked is *where did this come from and what else came from there*.
- **Deletion is not authorship.** The rewrite is where the value is added, and it does
  not launder provenance. If what survives is the upstream's method, the entry is
  `adapted` however little of the original text remains. `original` means we worked out
  the method.
- **A client's text is the client's.** `provenance: client` entries are written directly
  into that repository, never enter the harvest pipeline, and never come back out into
  the library. An incident worth generalizing is rewritten as a method with the client's
  particulars — names, hosts, customers, anything personal — removed before it is
  knowledge rather than after.

## 6. The spawn payload

When `/build` launches an agent for a task, it sends exactly this:

```
1. the skill file for the task's role          (~60 lines)
2. the task block from tasks.md                (~20 lines)
3. the ## Decisions section, if non-empty      (~5 lines)
```

That is the prompt. Roughly a page.

Everything else on §4's table is reachable and none of it is sent: not the spec, not the
rest of the task list, not the repository structure, not fact excerpts, not prior
conversation, not the graph, and no file contents at all. The task's `file:line`
references tell the agent exactly which ranges to open, and it opens them itself.

One further economy: launches of the same role within a run keep their first part
byte-identical — same skill file, same preamble — so the provider's prompt cache
serves it. What varies goes at the end. A warning string or a timestamp leaking into
the front of the prompt silently halves the cache hit rate across a forty-task run,
which is a real cost for a formatting mistake.

## 7. The roles

Small and fixed. The library supplies many entries per role; the roles themselves
rarely change.

| role | when it runs | model |
|---|---|---|
| **planner** | `/spec`, `/plan`, `/tasks` | strongest |
| **adversary** | `/spec`, after the draft | strongest, and never the drafting session |
| **test** | phase 2 — the assertions, as failing tests | strong; a bad test is worse than no test |
| **implementer** | every build task from phase 3 on | cheapest that follows instructions |
| **debugger** | after a task fails its check twice | strongest — this is thinking work |
| **verifier** | the proof phase, and `/verify` on demand | strong, and never a session that wrote code |

Three independence rules, and they are the only ceremony that survives from the previous
design:

- **The adversary is not the author.** A drafting session reviewing its own draft agrees
  with itself, produces something that looks like diligence, and contains no information.
- **The test writer is not the implementer.** An agent that writes both will make them
  agree — and will do that more fluently as models improve, not less. This is why phase 2
  is a phase rather than a habit inside every task.
- **The verifier did not write the code.** "Done" is not a sentence the builder gets to
  write about its own work. The verifier re-runs everything itself and pastes what
  actually came out.

All three are cheap — roughly one extra launch each per feature — and all three are the
difference between evidence and assertion.

## 8. Where the library comes from

Skill files are gathered from the open ecosystem, screened, rewritten into the shape
above, and admitted by a human. That machine is one skill, `/harvest`, described in
`architecture/10-harvest.md`. It runs in EDIFY's own repository and never in a
client's, because the text it handles is untrusted until a person has read it: a
poisoned skill file is persistent trusted context loaded into every matching session
in every repository that installed it.

Adapting a public skill into EDIFY form is mostly deletion. The typical marketplace
skill is a few hundred lines of imperatives, persona framing, and general engineering
advice; what survives the rewrite is the twenty lines that describe the actual method.
That reduction is the value the library adds, and it is why the library is curated
rather than mirrored.
