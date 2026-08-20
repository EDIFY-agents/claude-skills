# Sources

Where candidates come from, with provenance and yield history. Adding a source is a
reviewed change. A source that stops yielding admissible candidates is pruned — a
list of places nobody harvests from any more is a list nobody reads.

`fetch` is the path inside the source that holds the artifacts, so step ① is a
listing rather than a search. The `admitted` and `rejected` columns here are the last
committed snapshot; the live counts come from the ledger, which is the thing that
actually knows — `edify harvest status` prints the rows to commit.

| source | kind | fetch | licence posture | status | admitted | rejected | last run |
|---|---|---|---|---|---|---|---|
| github.com/open-gsd/gsd-core | repository | `skills/`, `agents/` on `next` | MIT (root LICENSE) | active | 0 | 0 | never |
| github.com/obra/superpowers | repository | `skills/` | MIT (root LICENSE) | active | 0 | 0 | never |
| github.com/wshobson/agents | repository | `plugins/*/skills/`, `plugins/*/agents/` | MIT (root LICENSE) | active | 0 | 0 | never |
| github.com/anthropics/skills | repository | `skills/` | per-skill — no root LICENSE | active | 0 | 0 | never |
| github.com/github/awesome-copilot | repository | `skills/`, `instructions/` | MIT (root LICENSE) | active | 0 | 0 | never |
| github.com/anthropics/claude-code-security-review | repository | `claudecode/prompts.py`, `claudecode/findings_filter.py` | MIT (root LICENSE) | active | 0 | 0 | never |
| github.com/humanlayer/humanlayer | repository | `.claude/commands/`, `.claude/agents/` | Apache-2.0 (LICENSE file — the API says NOASSERTION) | active | 0 | 0 | never |
| github.com/bmad-code-org/BMAD-METHOD | repository | `src/bmm-skills/`, `src/core-skills/` | MIT (LICENSE file — the API says NOASSERTION) | active | 0 | 0 | never |
| github.com/wshobson/commands | repository | `workflows/`, `tools/` | MIT (root LICENSE) | active | 0 | 0 | never |
| github.com/VoltAgent/awesome-claude-code-subagents | repository | `categories/` | MIT (root LICENSE) | active | 0 | 0 | never |
| github.com/openai/codex | repository | `codex-rs/core/*_prompt.md`, `codex-rs/core/templates/` | Apache-2.0 (root LICENSE) | active | 0 | 0 | never |
| github.com/Aider-AI/aider | repository | `aider/coders/*_prompts.py` | Apache-2.0 (LICENSE.txt) | active | 0 | 0 | never |
| github.com/google-gemini/gemini-cli | repository | `packages/core/src/core/prompts.ts` | Apache-2.0 (root LICENSE) | active | 0 | 0 | never |
| github.com/sst/opencode | repository | `packages/opencode/src/session/prompt/` | MIT (root LICENSE) | active | 0 | 0 | never |
| github.com/SWE-agent/SWE-agent | repository | `config/`, `config/exotic/` | MIT (root LICENSE) | active | 0 | 0 | never |
| github.com/cline/cline | repository | `.clinerules/` | Apache-2.0 (root LICENSE) | active | 0 | 0 | never |
| github.com/github/spec-kit | repository | `templates/commands/` | MIT (root LICENSE) | active | 0 | 0 | never |
| github.com/danielmiessler/fabric | repository | `data/patterns/` | MIT (root LICENSE) | active | 0 | 0 | never |
| github.com/PatrickJS/awesome-cursorrules | repository | `rules/` | CC0-1.0 (root LICENSE) | active | 0 | 0 | never |
| github.com/anthropics/claude-cookbooks | repository | `skills/custom_skills/` | MIT (root LICENSE) | active | 0 | 0 | never |
| github.com/microsoft/vscode-copilot-chat | repository | `src/extension/prompts/node/agent/`, `.../panel/` | MIT (LICENSE.txt) | archived | 0 | 0 | never |
| github.com/gsd-build/get-shit-done | repository | `agents/`, `commands/` | MIT (root LICENSE) | archived | 0 | 0 | never |
| github.com/hesreallyhim/awesome-claude-code | index | `README.md` | CC-BY-NC-ND-4.0 — index only | active | 0 | 0 | never |
| engagement — the first customer's engineers | engagement | the spec's closure checklist | client, by agreement | active | 0 | 0 | never |

### What each row costs to draw from

- **open-gsd/gsd-core** — the live half of GSD after the May 2026 governance split.
  MIT at the root, so the posture is clean. It is a spec-driven workflow system, which
  means most of what is in `skills/` is *its own* pipeline — the parts that fail test 4
  because they are bound to its layout. What is worth the rewrite is anything naming a
  failure and its check.
- **obra/superpowers** — MIT, `skills/` at the root, framed by its author as a
  development methodology rather than a persona pack. Whether that makes it a better
  source than the others is a claim the yield columns will settle and this note will
  not: nothing in this table is ranked on how it describes itself.
- **wshobson/agents** — MIT, and large. Volume is not a recommendation: a marketplace
  of agent definitions is mostly role framing, which is the costume rejection. Draw
  from it for stacks the library has no entry for.
- **anthropics/skills** — **no root LICENSE file.** The README says "many skills in
  this repo are open source (Apache 2.0)" and that the document-creation skills are
  source-available rather than open source. So the licence is per-directory and has to
  be read per artifact; where the artifact's own directory does not carry one, it is
  `NONE-FOUND` and the screen rejects it. Do not stage the whole tree on the strength
  of the README sentence.
- **github/awesome-copilot** — MIT at the root, and the largest body of stack-bound
  method in the open ecosystem: 407 directories under `skills/`, 192 files under
  `instructions/`. Draw from those two and not from `agents/`, which is 224 persona
  files and the costume rejection at volume. What earns a rewrite is the migration and
  optimisation set — `postgresql-optimization`, `javax-to-jakarta-migration`,
  `java-21-to-java-25-upgrade`, `react19-concurrent-patterns` — where the file names a
  version boundary, what breaks across it, and the check. The cost is a Microsoft and
  Azure skew: a large fraction of both directories is bound to Dataverse, Power BI, or
  Azure Verified Modules, and that is test 4 unless the method survives the product
  being deleted from it.
- **anthropics/claude-code-security-review** — MIT at the root, and unusual here in
  that the method is not in a markdown file: it is the audit prompt in
  `claudecode/prompts.py` and the exclusion rules in `claudecode/findings_filter.py`.
  That second file is test 2 in its purest form — finding classes that are false
  positives, each with the reason it is one — and it is worth the awkwardness of
  lifting a method out of a string constant. Cite `file:line`, not the module. The
  evals beside it are the upstream's measurement of the upstream, not a claim we get
  to repeat.
- **humanlayer/humanlayer** — Apache-2.0. Its `LICENSE` is the Apache text under a
  title line, so GitHub's licence endpoint answers `NOASSERTION` — read the file and
  stage `Apache-2.0`. The API disagreeing with the file is not a `NONE-FOUND`, and a
  screen rejection built on the API's answer is a wrong licence string to fix at step
  ①, not a verdict. `.claude/commands/` holds a research-plan-implement loop written
  for codebases too large to hold at once (`create_plan.md`, `implement_plan.md`,
  `debug.md`, `local_review.md`). Expect half of it to fail test 4 on `hld/` and
  `hlyr/`, which are its own product.
- **bmad-code-org/BMAD-METHOD** — MIT, with the same licence-API problem as humanlayer:
  a contributor preamble above the MIT text, so the endpoint says `NOASSERTION` and the
  file says MIT. `src/bmm-skills/` and `src/core-skills/` are the artifacts; everything
  around them is a workflow system that competes with this one, which is test 4 at
  scale. It also carries a `TRADEMARK.md`, so the text is adaptable and the name is
  not — a rewrite never keeps "BMAD" in `name` or in prose.
- **wshobson/commands** — MIT, and the companion to the `wshobson/agents` row above.
  Same author, opposite content: a command is a procedure and an agent definition is a
  costume, so this is the half of that output with a route through test 1. The ones
  naming an order of operations are in `workflows/` — `incident-response.md`,
  `performance-optimization.md`, `legacy-modernize.md`. `tools/` is 42 files and
  thinner, mostly scaffolding.
- **VoltAgent/awesome-claude-code-subagents** — MIT, 100+ definitions under
  `categories/`. Listed for one purpose: `02-language-specialists` and
  `07-specialized-domains` cover stacks `vocab.md` names and the library has no entry
  for. Expect the costume rejection on most of it, and prune the row if two draws
  yield nothing — a second marketplace producing what the first produced is a row
  nobody reads.
- **openai/codex** — Apache-2.0, and unusual in this table for keeping its system
  prompts as plain markdown at the root of `codex-rs/core/` rather than buried in a
  string constant: one file per model, plus `templates/` for `review/`, `collab/`,
  `agents/`, and `personalities/`. These are a shipped agent's actual operating
  instructions rather than somebody's description of one, which is the difference
  between test 1 passing and failing. The cost is test 4: much of each file is bound to
  Codex's own sandbox, approval modes, and `apply_patch` tool. What survives the
  deletion of those is the editing discipline and the stop conditions.
- **Aider-AI/aider** — Apache-2.0, and the closest thing here to test 2 inside a
  production harness. `aider/coders/` holds one prompt module per edit format —
  `editblock`, `udiff`, `wholefile`, `patch` — and beside each sits the coder that
  repairs what the model got wrong. The failure knowledge is in that pairing:
  `udiff_prompts.py` exists because unified diffs are the format models botch, and the
  code next to it names how they botch it. Same awkwardness as the security-review row,
  so cite `file:line` and not the module. `architect_prompts.py` is role framing and is
  the costume rejection.
- **google-gemini/gemini-cli** — Apache-2.0, and one artifact:
  `packages/core/src/core/prompts.ts` carries the whole system prompt as a template
  literal. One careful draw rather than a standing subscription, because there is
  nothing else in it. Most of the file is Gemini CLI's own tool names; the part that
  travels is the explain-then-act loop and the insistence on verifying with the
  project's own commands, and it has to be lifted clean of `run_shell_command` and
  `replace` or it is that product's convention.
- **sst/opencode** — MIT. The repository moved to `anomalyco/opencode` and the old path
  still redirects, including on `raw.githubusercontent.com`, so this row keeps the name
  it is known by — but a redirect is not a guarantee, which is one more reason every
  fetch pins `--commit`. `packages/opencode/src/session/prompt/` is fourteen plain
  `.txt` files, one per model family, and that makes it the cheapest comparison in the
  table: the same job written five ways tells you which instructions are about the work
  and which are about the model. `plan.txt` and `beast.txt` hold the method; the rest is
  tone, and tone is the costume rejection.
- **SWE-agent/SWE-agent** — MIT, and the one upstream here that measures itself against
  a benchmark instead of against its own README. `config/*.yaml` is agent configuration:
  tool definitions carrying their own failure modes, per-step instructions, and a
  demonstration trajectory. `config/exotic/` is the half worth reading —
  `windowed_replace_late_repro.yaml` names a thing that goes wrong and the shape that
  avoids it, which is test 2 stated as a config. The cost is that a YAML config is not a
  skill file, so the rewrite is a real translation rather than the usual deletion, and
  it is the one row where step ③ may cost more than it saves.
- **cline/cline** — Apache-2.0, small, and unusually honest: `.clinerules/` is the rules
  its own maintainers work under rather than a marketplace listing, so nothing in it was
  written to be impressive. `debug-harness.md` first. Ten files total, so expect the row
  to be exhausted in one or two runs and prune it then rather than drawing a third time.
- **github/spec-kit** — MIT, and a competing spec-driven workflow, which is test 4 at the
  same scale BMAD is. Draw from `templates/commands/` and nowhere else. `analyze.md`,
  `clarify.md`, and `checklist.md` name what to check and in what order, and that
  survives the removal of `.specify/`; `implement.md` and `tasks.md` are its pipeline
  describing itself, and ours already exists.
- **danielmiessler/fabric** — MIT, `data/patterns/` at 256 directories, each holding a
  `system.md`. The largest single body of task prompts in the table and the lowest
  expected hit rate in it, because most patterns aim at prose rather than at code. Draw
  **by name and never by listing the directory**: the engineering few are
  `analyze_incident`, `review_design`, `review_code`, `create_design_document`, and
  `create_stride_threat_model`. Working down the listing is how a run spends its whole
  budget on summarisation prompts.
- **PatrickJS/awesome-cursorrules** — CC0-1.0, which is on the allowlist and carries no
  obligation at all, and that is the only thing recommending it over the other rule
  collections. `rules/` is 257 `.mdc` files and the name tells you which are worth the
  bytes: a file named for a stack is a convention list and fails test 4, while the few
  named for a discipline — `anti-overengineering.mdc`, `clean-code.mdc`,
  `anti-sycophancy-code-discipline-cursorrules-prompt-file.mdc` — are where a method
  might be. Expect duplicates of `awesome-copilot` and let the hash check catch them.
- **anthropics/claude-cookbooks** — MIT **at the root**, which is the whole difference
  between this row and the `anthropics/skills` row above, and why both are listed rather
  than one. `skills/custom_skills/` is three worked examples of the skill format written
  by the people who defined it. Three directories is not a supply, so this is a shape
  reference rather than a source: draw it once to settle a format question, then prune.
  The notebooks beside it are `.ipynb` teaching material, which is advice.
- **microsoft/vscode-copilot-chat** — MIT, and **archived**: the repository is frozen, so
  it is a fixed set that ranks below every live row. Still worth one draw, because it is
  the only place in the table where a shipped agent's prompts are versioned as
  composable pieces rather than one blob. `src/extension/prompts/node/agent/` puts
  per-model variants (`anthropicPrompts.tsx`, `geminiPrompts.tsx`) beside a common
  `defaultAgentInstructions.tsx`, and `backgroundSummarizer.ts` and
  `executionSubagentPrompt.tsx` are two of the hardest problems in this space with
  somebody's real answer attached. The cost is TSX: the method is interleaved with
  component structure, so reading it is closer to reading a program than a document.
- **gsd-build/get-shit-done** — **archived**, and it has no `skills/`: the workflow
  lives in `agents/` and `commands/`. MIT, and a stable `repo@commit` for attribution,
  but frozen — nothing new arrives here. Kept because it is the upstream most of the
  forks descend from, so it settles who wrote something first. Prune it once it has
  been drawn once.
- **hesreallyhim/awesome-claude-code** — **CC BY-NC-ND 4.0**, which is NonCommercial
  and NoDerivatives, and therefore not on the allowlist and not adaptable. It is a
  directory: read it to find *where* things are, then draw from the repository the
  link points at under that repository's own licence. Never stage its bytes.
- **the engagement row** — §7 of `docs/design/architecture/10-harvest.md`: the half that is
  not free is failure knowledge from engineers who have watched it go wrong. It stays
  in the table with a zero yield because that is the honest state until there is an
  engagement to fund it.

## What makes a source worth listing

A source is worth listing when its content is **method** rather than **advice**.
The open ecosystem has thousands of skill files and the runtimes bundle general
engineering ones by default; anything gathered from there is something anyone can
gather for the price we paid, which is nothing.

The half that is not free is **failure knowledge** — what a senior engineer has
watched go wrong in production on a particular stack, and the specific check that
catches it. Not "you are an expert in Kubernetes", which is worth nothing and
measurably worse than nothing. Something closer to: *this class of change silently
breaks under this condition, here is the assertion that catches it, here is the
incident that taught us*.

That content has one natural home — the spec's closure checklist — and one natural
first source: the engineers at whichever company runs this first, whose time is
billable inside an engagement rather than out of runway.

There is one public class that comes closer than the marketplaces do, and it is why
half this table is now something other than a skill directory: **the prompts a shipped
agent actually runs on**. Codex, aider, opencode, gemini-cli, SWE-agent and
vscode-copilot-chat all ship theirs in the open, and they differ from a marketplace
listing in the way that matters — a marketplace skill is written to be adopted, so it
is optimised for looking convincing to a reader, while a harness prompt is written to
survive contact with a model on a real repository and every line in it is there
because something went wrong without it. That is failure knowledge, arrived at by
someone else's evaluation loop rather than by their taste.

Two costs come with the class, and both are paid at step ③. The method is usually in
a string constant, a `.ts` template literal, a `.tsx` component, or a YAML config
rather than in a document, so the rewrite is a translation and the citation is a
`file:line`. And a shipped prompt is welded to its own harness — its tool names, its
approval model, its sandbox — so test 4 does most of the rejecting. A run that draws
from these rows should expect a lower count and a higher value per entry than a run
that draws from a marketplace, and should not make up the difference by widening.

## Which row a run draws from

`edify harvest pick` scores every row and names one. The score is a lookup over this
table and the ledger — a licence posture that resolves to an allowlisted SPDX id, the
admitted-to-rejected ratio at the human door, whether the upstream is archived, how
much of the source is already in the ledger, and how long since it was last drawn. It
is deterministic on purpose: the row a run draws from is not a thing a model should
decide differently on Tuesday.

`status` is `active` or `archived`, and it is here because without it the four MIT rows
tie and the tie-break is alphabetical — which handed the first run the one archived
repository in the table. An archived source still ranks above an ineligible one; it
just goes last among the live ones.

A row whose posture does not resolve is never chosen, because a run that stages from
it is a run the screen rejects. An `index` row is chosen only for its links.

`--source <name>` overrides the score, for when a person has a reason.

## Recording a run

One row per source per run. `admitted` and `rejected` are counts from the human
door, not from the screen — a source with a high screen pass rate and a low
admission rate is producing plausible files, which is the failure mode worth
noticing.

## What is deliberately not here

No marketplace, no contributor portal, no bazaar. No `install <url>`: an ad-hoc
import bypasses the only door there is. No reputation as an admission argument —
not who wrote it, not how many stars, not what it cost. Those are proxies for a
measurement we do not have, and a proxy that feels like evidence is worse than an
honest absence of evidence. The star counts are absent from this table for that
reason, and the notes above are about licence and layout, which are facts.

Two categories are absent on purpose, and both look like they belong here.

**The Creative Commons documentation corpora** — OWASP's cheat sheets (CC BY-SA 4.0),
Google's engineering practices (CC BY 3.0, and archived), the Kubernetes docs (CC BY
4.0). These are the closest public thing to the failure knowledge this file calls the
half that is not free, and none of them resolves to an id on the allowlist in
`screen.py`. That is a decision about which obligations travel into a customer's
repository, so the way to harvest one is to argue for the id in `ALLOWED_LICENSES` and
have a person agree — never to stage it and hope, and never to paraphrase it into an
entry with a `NONE-FOUND` provenance, which is the same violation with the evidence
removed.

**The architecture and postmortem indexes** — `awesome-scalability`, `awesome-sre`,
`post-mortems`. Their own licences are permissive, so they read as eligible, but an
`index` row is only worth what sits at the end of its links, and theirs are
copyrighted engineering blog posts rather than licensed repositories. The
`awesome-claude-code` row works because its links land on MIT repositories; these land
on nothing that can be staged.

A third is absent now that the table has a row for shipped harness prompts, because it
is the obvious next thing somebody adds and it is not the same category.

**The leaked system prompt collections** — the repositories mirroring the prompts of
tools that never published them. They are the richest-looking material in the whole
ecosystem and none of it is ours to take. A licence file in a mirror grants what the
mirrorer owns, which is nothing: the upstream never released the text, so the id at the
root of the mirror is a claim about somebody else's copyright and `stage --license`
would be recording it as fact. The rows added here are the opposite case and the line
between them is the whole point — Codex, aider, opencode, gemini-cli, SWE-agent and
vscode-copilot-chat put their prompts in their own repositories under their own
licence, on purpose. Published is the test, not available.
