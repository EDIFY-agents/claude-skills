# EDIFY — Architecture

**Date:** 2026-08-06
**Status:** Canonical, buildable blueprint for the redesigned system.
**Supersedes:** `Research/design/architecture/` (00–11), kept as historical record.

The dossier one level up (`../`) answers *what* is built and why. This folder answers
*what shape it has on disk*: the formats, the command contracts, the CLI surface, the
folder trees, and the worked examples that calibrate them.

---

## Reading order

| doc | what it defines |
|---|---|
| `00-system-graph.md` | how the parts wire together — the whole system in one picture |
| `01-folder-structure.md` | the source tree, the installed tree, and the root instruction file |
| `02-commands.md` | the seven commands as contracts — inputs, outputs, refusals |
| `03-plan-format.md` | the `plan.md` format: technology decisions, milestones, context seeds |
| `04-tasks-format.md` | the `tasks.md` format: phases, task anatomy, the two closure tables |
| `05-skills-and-spawning.md` | the open knowledge format, the skill file shape, the context references a role may open, the laws `edify check` enforces, the spawn payload |
| `06-graph.md` | the graph's on-disk form, the extractor, and the query surface |
| `07-mcp.md` | the server registry — reaching outside the repo, scoped per role and phase |
| `08-verification.md` | the verification kinds, phase 2, and the `/verify` contract |
| `09-cli.md` | the redesigned `edify` binary |
| `10-harvest.md` | the one curation skill — the four steps and the human door, what a candidate has to look like to be admitted, and the law behind the screen |

## The three worked examples

Formats are stated once and shown once. All three exemplars are real artifacts from
real products rather than invented illustrations, which is why they calibrate:

| artifact | format doc | example |
|---|---|---|
| `spec.md` | `../03-the-spec.md` | `../spec-ex.md` |
| `plan.md` | `03-plan-format.md` | `../plan-ex.md` |
| `tasks.md` | `04-tasks-format.md` | `tasks.example.md` |

## The three rules this folder follows

1. **The dossier wins on why; this folder wins on shape.** Where they overlap, the
   dossier is cited rather than restated. A blueprint that re-argues a design is drift
   waiting to happen.
2. **Every format is defined once and shown once.** The format document states the
   contract; the example shows a real instance. Nothing teaches a format inside a
   command body — that is how a command grows to five hundred lines.
3. **Status is observed, not assumed.** Nothing in this folder exists on disk yet beyond
   the documents themselves. §Status below says so, dated, with the command that
   rechecks it.

## What is deliberately not here

- **No schema files.** The previous design had fourteen, each with a shape definition, a
  golden exemplar, and a handoff contract. Three artifacts remain, each defined by one
  format document plus one worked example. A validator that checks the format is a
  convenience command (`edify check`), never a gate.
- **No enforcement table.** There is nothing that mechanically blocks, so there is
  nothing to tabulate. `../01-principles.md` P7 states what replaced it, and
  `08-verification.md` §5 says where a client who needs a hard block puts one.
- **No policy files.** No constitution, tiering table, capability profile, or waiver
  policy. What survived is the spec's constraints section and the plan's decisions table.
- **No compiler and no per-tool target trees.** One canonical tree; a second AI tool gets
  its instruction file written, not generated.

## Status — 2026-08-07

| component | state | recheck with |
|---|---|---|
| this blueprint | 11 documents + 1 worked example | `ls design/architecture/` |
| the dossier | 11 documents + EDIFY's own spec | `ls design/` |
| implementation | **built** — `edify-cli` 0.1.0 in `src/edify/`, 105 tests green | `pytest && edify doctor` |
| the graph extractor | built in, deterministic: Python parsed by syntax tree, 19 languages scanned, an adapter for a pinned external extractor behind `--extractor ctags`. The TSV contract is what we own | `edify graph stat` |
| the skill library | 12 original entries across all six roles, every one under budget | `edify skills list` |
| the MCP registry | one entry shipped and seeded by `edify init`; version left unpinned on purpose so `check` reports it | `edify mcp list` |
| commercial | designed and implemented — see `../../pricing.md` | `edify license status` |

**Status as of 2026-08-07.** The build order in `09-cli.md` §5 said the graph
commands come first and everything after is what makes it installable by a stranger.
Steps 1–6 are done; the one item deliberately left is step 4's second half — a
registry with more than one entry has nothing to say until a repository needs one.

**Relationship to `EDIFY-mrk1/`.** That tree is the previous design's seed: four
commands, eleven schemas, four policy files, two shell scripts, and a fourteen-entry
friction log from one dogfooded feature. It is the best evidence available about what
this pipeline feels like to run, and its friction log is a direct input to this
redesign — in particular the entry recording that a spec-section-exists check is
satisfied by writing a paragraph, which is the origin of the verification ladder in
`08-verification.md`. It is not a structural reference: the shape it implements is the
shape this folder replaces.
