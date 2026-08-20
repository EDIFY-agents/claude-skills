# 10 — Harvest: The One Curation Skill

**Status: built.** This document specified it before anything was gathered, because the
expensive mistake in curation is stocking a library before deciding what admission
means. What that shape became: `.claude/skills/harvest/SKILL.md` for the three steps
that are judgment, `src/edify/harvest/` for the two that are not, and
`harvest/ledger.json` for the one question — have we seen this before — that decides
whether a run costs anything.

The previous design had four runtimes plus a human stage: scout, screen, adapt,
evaluate, ratify — five skill files, a staging tree, a quarantine folder, a watchlist,
a vocabulary, an evaluation harness, and a signed release process. That was the right
machine for a library of thousands of entries with an editions model behind it. For a
library of dozens of eighty-line files, it is more machinery than content.

**It becomes one skill with four steps and one door.**

---

## 1. The one skill

```
/harvest
   ⓿ pick ─▶ ① gather ─▶ ② screen ─▶ ③ rewrite ─▶ ④ propose ─▶ ◆ HUMAN ─▶ ⑤ setup
```

**⓿ Pick.** `edify harvest pick` scores every row of `edify/harvest/sources.md` against
the ledger's yield history and names one. This step was implicit in the first version
and that was a defect: the skill said "read `sources.md`" and left the selection of a
row to the model, which is the one decision in this pipeline that has a right answer
computable from files. A run could draw from an archived upstream, or from the row whose
licence posture the screen was always going to reject, and nothing noticed until step ②.
It is now §1 of `01-principles.md` applied where it was missing — *deterministic where it
decides* — and the score is stated so it can be argued with: licence posture resolved
against the allowlist, the admitted-to-rejected ratio **at the human door**, whether the
upstream is archived, how much of the source is already in the ledger, and how long
since it was last drawn. `--source` overrides it for a person with a reason.

**① Gather.** Read the chosen row's notes in `edify/harvest/sources.md` — the versioned
list of places candidates come from, each with its yield history. Pin the commit,
resolve the licence at the artifact's own level rather than from a README claim, list
the row's `fetch` path rather than searching the tree, and skip everything the ledger
has already seen. Write one record per artifact into a staging area: the URL, the commit
hash, the license as found (the file and its SPDX id, or `NONE-FOUND`), and the raw
content **stored as data, never read as instruction**.

**② Screen.** Mechanical, fail-closed, no judgment:
- **License allowlist.** Permissive licenses only — `MIT`, `Apache-2.0`,
  `BSD-2-Clause`, `BSD-3-Clause`, `ISC`, `Unlicense`, `CC0-1.0`, as SPDX ids in
  `src/edify/harvest/screen.py`. Copyleft, unlicensed, and `NONE-FOUND` are rejected
  outright, and an unresolvable string — `BSD` without a clause count, "public domain"
  as a claim rather than a licence — resolves to `NONE-FOUND` rather than to the benefit
  of the doubt. This library composes into other companies' repositories; the check is a
  lookup and it is hard from day one.
- **Duplicate check** against what is already in the library.
- **Injection scan.** Instruction-like content aimed at exfiltration, tool abuse, or
  gate evasion goes to quarantine, flagged, never silently dropped.

**③ Rewrite.** This is where the value is added, and it is mostly deletion. A typical
marketplace skill is two to five hundred lines of capitalized imperatives, persona
framing, self-attestation blocks, and general engineering advice the model already
knows. What survives is the twenty to forty lines that describe the actual method:
where to look first, what to check, what the traps are, what finished looks like.

The rewrite produces a file in the open knowledge format — `05-skills-and-spawning.md`
§1 for the frontmatter, §2 for the four sections and the budget. Every claim about a
codebase gets a citation or is cut. Every MUST becomes either a step in the method or
nothing. What a candidate has to look like before it is worth this step at all is §2 of
this document.

**④ Propose.** Present the candidate for admission: the rewritten file, the original
side by side, the provenance record, the screen result, and one line on what scenario
it serves that nothing in the library currently serves.

**◆ The human door.** A person reads it and admits or rejects. There is no other door
— not for speed, not for volume. Steps ⓿ to ④ can run unattended; this one costs
minutes per entry and is the only thing standing between a stranger's text and
persistent trusted context in a customer's repository.

**⑤ Setup.** Admission and usability are one event, in one command, because separating
them produced an entry that was admitted and could not be loaded. `admit` writes the
authored library at `edify/skills/<name>.md` — which is what *ships* — and then installs
it: `.edify/skills/`, the lookup index, the `.claude/skills/<name>/SKILL.md` mirror the
host runtime discovers, and the governance row. Deliberately on the far side of the
door: installing a stranger's text is exactly the thing that waits for a person.

## 2. What a candidate has to look like

Two filters, in order, answering different questions. The screen answers **may we** —
mechanically, fail-closed, no judgment, because a model is good at deciding whether a
skill file is worth having and bad at deciding whether we are allowed to have it. This
section answers **should we**, which is judgment the whole way down, and is why the
pipeline ends at a person rather than at a score.

### The five tests

All five, not three of five. A candidate that fails one is rejected with the reason
written into the ledger, because the recorded reason is what makes the next run cheap.

**1. Method, not advice.** Does it say where to look first, what to check, what order
things go in, and what finished looks like? The open ecosystem's median skill file is
advice — competent, general, and already in the weights. The cut test applies line by
line rather than to the file as a whole: *would a competent engineer who has never seen
this repository be worse off without this line?* "Write tests for edge cases" fails it.
"The integration suite needs `--runslow` or it silently collects nothing" passes.

**2. Failure knowledge, not competence.** The line worth paying for names a condition,
the thing that breaks under it, and the assertion that catches it. *This class of change
silently breaks when the connection pool is recycled mid-transaction; here is the test
that catches it.* Not "you are an expert in Postgres", which is worth nothing and
measurably worse than nothing.

**3. It survives the deletion.** Strip the imperatives, the persona, the
self-attestation, and the general advice. Twenty to forty lines of actual method have to
be left standing. If deletion leaves an outline, the file was packaging around a method
someone else has — and packaging is what we remove, not what we import.

**4. It travels.** The method has to survive being lifted out of the repository it was
written for, because it will run in repositories nobody has seen. Concretely: every
claim it makes about a codebase is replaceable by a graph query, or by a `file:line` the
task will supply at build time, or it is cut. A method that depends on the upstream's
directory layout is that repository's convention wearing a skill file's clothes. If it
hard-codes a tool, either that tool is an id in `vocab.md` and the entry narrows its
`tech` to match, or the dependency goes.

**5. It fills an empty coordinate.** `role · phase · tech` is the lookup key, so the
admission case is a coordinate: either nothing serves it, or what serves it loses to
this. "It is good" is not a case. A rewrite with no answer to *what does this serve that
the library does not* is a duplicate that has not been recognised yet.

### What "best" looks like here

Not the largest, the most starred, or the most comprehensive. Reputation is not an
admission argument (§6), and a comprehensive file is usually a general one.

- **Short and specific enough to be boring.** The strongest entries read as
  unremarkable to their author and are the reason a stranger's session goes right.
- **Narrow beats hedged.** `tech: any` is a claim that the method holds across every
  stack in `vocab.md` — earn it or narrow it. Two entries under budget beat one over
  budget with conditionals inside, because the lookup is exact-match and free, while a
  branch inside a file is paid for by every launch that does not take it.
- **Every path carries a line range**, or the literal `new`. An entry that names
  `src/auth/` is teaching exploration, which is the largest token line-item there is.
- **It explains rather than commands.** After the rewrite there is nothing left that
  tells the agent how careful to be, who it is, or how expert it is.

### What adapting actually is

Mostly deletion, and then six mechanical moves:

| in the original | in the entry |
|---|---|
| capitalized imperatives | a numbered step, or nothing |
| persona and expertise claims | deleted, with no replacement |
| self-attestation and confidence blocks | deleted |
| general engineering advice | deleted |
| claims about a codebase | a citation, or cut |
| the upstream's tool and layout assumptions | a `tech` id from `vocab.md`, a graph query, or cut |
| whatever the upstream called its category | `role` and `phase` from `vocab.md` |

Then the frontmatter: `provenance: adapted`, and `license` carrying the SPDX id with
`repo@commit`. `edify harvest propose` refuses any other provenance, and the format
validator refuses an `adapted` entry with no licence — the one step where a rewrite could
quietly become an original is the one step checked mechanically.

Typical arithmetic: two to five hundred lines in, twenty to forty out. A rewrite that
comes out near its input length has not been done yet.

### The rejections to expect

Recording these as they happen is what stops a source from being re-harvested forever:

- **The general one.** Well written, entirely about engineering, already in the weights.
- **The costume.** A persona and a tone with no method underneath.
- **Someone else's runbook.** Real method, bound to a repository we do not have — fails
  test 4 and cannot be rescued by rewriting.
- **The renamed duplicate.** The ledger catches identical bytes by hash; a reviewer
  catches the same method under a new name, and that is what the human door is for.
- **The one that needs a benchmark.** Plausible, unfalsifiable, admissible only on a
  measurement we do not have. §3 says why the evaluation runtime that would have settled
  it was dropped; until something replaces it, this is a rejection with the reason
  stated rather than an admission on a feeling.

## 3. Why the four collapsed into one

Each of the old runtimes was a separate agent with its own skill file, its own staging
handoff, and its own artifact. That structure paid for itself when the stages were long
and the volume was thousands. At the actual shape of this library — dozens of short
files, gathered in occasional batches — the handoffs cost more than they coordinate.

What is **not** collapsed:

- **The license check stays mechanical and fail-closed.** It is a lookup, it is a legal
  question, and a model must never be the thing that decides whether we may ship
  somebody's work.
- **The injection scan stays a distinct step**, and quarantine stays a place things go
  rather than a decision made in passing.
- **The human door stays mandatory.** The previous design's note on this was right and
  is worth repeating: a poisoned skill file is worse than a poisoned tool response,
  because it is *persistent, trusted* context loaded into every matching session in
  every repository that installed it.

What is dropped: the separate evaluation runtime. Measuring a skill against a benchmark
suite is the correct admission argument and there is no benchmark suite; requiring one
means either not shipping or pretending. The honest version is that entries are
admitted on a human's judgment plus use, and the file says so rather than carrying an
`eval: pending` field that never becomes `passed`.

## 4. Where it runs, and why that is a boundary

**In EDIFY's own repository. Never in a client's.** Clients consume a library; they
never produce one. Everything the skill touches is untrusted text until a human has
read it, and untrusted text does not belong in a customer's tree at any stage of
processing.

A client's own skills — the conventions that are true only for their codebase — are
written directly into their `.edify/skills/` with `provenance: client` and never enter
this pipeline.

## 5. What a run reads, and the law behind it

### The reference files

The authored half — reviewed changes, committed by a person:

- **`edify/harvest/sources.md`** — where candidates come from, with provenance and yield
  history. Adding a source is a reviewed change. A source that stops yielding admissible
  candidates is pruned; a list of places nobody harvests from any more is a list nobody
  reads. A run never edits it: `edify harvest status` prints the yield rows and a person
  commits them.

  Six columns became eight, and the two additions are both there because `pick` reads
  this table rather than a person: **`fetch`** is the path inside the source that holds
  the artifacts, so step ① is a listing instead of a search of somebody's tree; and
  **`status`** is `active` or `archived`, without which several rows sharing a licence
  tie on score and the tie-break is alphabetical — which is how the first run of the
  finished pipeline was handed the one archived repository in the table. The parse is by
  column name, so a table written before either column existed still reads.
- **`edify/harvest/vocab.md`** — the controlled values for `role`, `phase`, and `tech`.
  One file, three short lists. Extending it is a reviewed change, because every consumer
  of the index breaks silently if an id appears that no consumer knows.

The produced half — what running the pipeline writes:

| path | holds | tracked |
|---|---|---|
| `harvest/ledger.json` | every candidate ever seen and what became of it | yes |
| `harvest/proposals/<id>/` | the rewrite, the original beside it, the case | yes |
| `harvest/staging/<id>/` | raw bytes awaiting the screen | **no** |
| `harvest/quarantine/<id>/` | what the injection scan caught, with its verdict | **no** |

`staging/` and `quarantine/` are gitignored deliberately: they hold a stranger's text
verbatim, and a repository is not the place for it. The permanent record is the ledger,
which is a verdict and three hashes rather than the bytes.

### The context references a run works from

| file | why it is opened |
|---|---|
| `edify/harvest/sources.md` | what makes a source worth drawing from, and its yield |
| `edify/harvest/vocab.md` | the controlled values the rewrite has to land in |
| `harvest/ledger.json`, via `edify harvest pick` | the three identities of everything ever handled — URL, entry name, content hash |
| `edify/skills/*.md` | the target shape, read as an exemplar rather than a template |
| `05-skills-and-spawning.md` §1–§2 | the format and the four sections the rewrite produces |
| `../08-agents-and-skills.md` §5 | the laws the rewritten entry has to satisfy |
| `harvest/staging/<id>/raw.txt` | the candidate — **as data, never as instruction** |

That last line is the one that matters most and is easiest to lose. The staged bytes are
read to be summarized and rewritten. An instruction found inside them is a finding for
the screen, not something to act on, and the pipeline is arranged so that noticing one is
the normal outcome rather than an exception: the scan reports every pattern it hits, with
its line, and routes the file to quarantine rather than to the bin.

### The law it works under

Not ours to amend, which is why none of it is a judgment call:

- **The allowlist is a lookup, never a prompt.** `MIT`, `Apache-2.0`, `BSD-2-Clause`,
  `BSD-3-Clause`, `ISC`, `Unlicense`, `CC0-1.0` — `src/edify/harvest/screen.py`.
  Everything else, including copyleft and every unresolvable string, is a rejection.
  Copyleft is absent by decision rather than oversight: a reciprocal obligation reaching
  a customer's tree through a library they installed for other reasons is not ours to
  accept for them.
- **Attribution survives the rewrite.** MIT, BSD, and ISC require the copyright notice
  to travel; Apache-2.0 adds NOTICE. `license: <SPDX> <repo>@<commit>` is what keeps
  that recoverable after most of the bytes have changed, and `propose` refuses an
  `adapted` entry without it.
- **Deletion is not authorship.** If the surviving method is the upstream's, the entry
  is `adapted` — the proportion of text rewritten does not enter into it.
- **Provenance is a security record as well as a legal one.** When an entry turns out to
  be poisoned, the question is *where did it come from and what else came from there*,
  and the ledger answers it by URL, hash, and name.
- **Client material never enters this pipeline.** A customer's conventions are written
  straight into their `.edify/skills/` with `provenance: client`. A method worth
  generalizing is rewritten with their particulars — names, hosts, customers, anything
  personal — removed before it becomes a library entry, not after.

## 6. What is deliberately not built

- **No marketplace, no contributor portal, no bazaar.** Two-sided platforms have a
  cold-start problem, months of work, and no value to the first customer.
- **No `install <url>`.** Ad-hoc imports bypass the only door there is.
- **No reputation as an admission argument.** Not who wrote it, not how many stars,
  not what it cost. Those are proxies for a measurement we do not have, and a proxy
  that feels like evidence is worse than an honest absence of evidence.
- **No automated admission**, however good the screening gets.

## 7. The one thing worth paying for

The library's public half is table stakes: the open ecosystem has thousands of skills,
and the runtimes bundle general engineering ones by default. Anything gathered from
there is something anyone can gather for the price we paid, which is nothing.

The half that is not free is **failure knowledge** — what a senior engineer has watched
go wrong in production on a particular stack, and the specific check that catches it.
Not "you are an expert in Kubernetes", which is worth nothing and measurably worse than
nothing. Something closer to: *this class of change silently breaks under this
condition, here is the assertion that catches it, here is the incident that taught us*.

That content has one natural home in the new design — the spec's closure checklist —
and one natural first source: the engineers at whichever company runs this first, whose
time is billable inside the engagement rather than out of runway. It is designed here
and built when there is an engagement to fund it, not before.
