# Changelog

All notable changes to `edify-cli`. The format follows Keep a Changelog; versioning
is semantic on the CLI surface.

Two contract versions move independently of the CLI version and are recorded in
`.edify/graph/meta` and `edify/manifest.md`: `graph-schema` (bumping it rebuilds an
existing graph rather than misreading it) and `index-schema`.

## [Unreleased]

### Licence — MIT → FSL-1.1-Apache-2.0

The project moves from the MIT License to the **[Functional Source
License](LICENSE)**, version 1.1, with an Apache 2.0 Future License.

Nothing a *user* could do under MIT is withdrawn: use at work, on commercial code,
in production, at any company size; read, modify, fork, self-host, redistribute.
The single restriction added is a Competing Use — selling EDIFY, or a rebranded
EDIFY, as a product or hosted service.

Under MIT, the five gates in `src/edify/licensing/tier.py` could be deleted and
the result sold, legally, by anyone. Defending that technically would mean
obfuscation or a phone-home, and both cost every honest user something real —
`docs/pricing.md` §4 commits to neither. A licence is the honest place to put that
boundary.

**Every released version converts to Apache 2.0 on its second anniversary**,
irrevocably, with a patent grant. Release dates are in this file, so the
conversion date of any version is computable without us.

- `LICENSE` — FSL-1.1-Apache-2.0, replacing the MIT text.
- `NOTICE` — copyright, third-party material, and the trademark reservation.
- `TRADEMARK.md` — what the licence deliberately does not grant: the name.
- `docs/license.md` — the plain-English version, including why not MIT and why
  not AGPL, and stating plainly that this is source-available and not OSI open
  source.
- `governance.py` — `SHIPPED_LICENSE` is now `FSL-1.1-Apache-2.0`, so
  `edify governance list`, `LICENSE`, and the README cannot drift apart.
- `CONTRIBUTING.md` — DCO sign-off plus an explicit inbound grant, which is what
  keeps the two-year Apache 2.0 conversion promise keepable.

### The ship release — a real issuing key, `edify self update`, the ∞, and a way to pay

Four things stood between EDIFY and a person paying for it. They all land here.

#### A real issuing key

`DEFAULT_PUBLIC_KEY_HEX` shipped in 0.1.0 as the public key of an **all-zeros seed**.
Anyone could mint a `pro` or `team` token with 32 zero bytes. It has been replaced with
a real random key whose private half never enters this repository, and
`tests/test_licensing.py` now fails if a key derivable from any trivially-guessable seed
comes back — by revert, by bad merge, or by a placeholder left in.

Tokens carry `exp`, so anything issued against the old key simply stops verifying. That
is the desired outcome and not a migration.

#### `edify self update` — the CLI can update itself

`edify upgrade` pulls a newer **skill library**. It could not put an edited checkout
behind the `edify` binary, and nothing else could either.

- **`edify self update [--from PATH]`** shells out to whichever tool put `edify` on
  PATH — uv, pipx, or pip — because only that tool can correctly replace it. A hardcoded
  `pip install` into a uv tool environment produces a second, shadowed copy, which is
  the worst possible outcome for a command named "update".
- **`edify self where`** prints which binary is answering, its interpreter, prefix,
  package path, detected installer, and source checkout — before anything is installed.
- Detection reads `sys.prefix` path segments (`uv/tools/…`, `pipx/venvs/…`); `--manager`
  overrides it, so a mis-detection costs one flag rather than a broken install. After a
  successful install the *new* binary is asked for its version, so a shadowed copy shows
  up as a version that did not move.
- `--dry-run` prints the exact argv and changes nothing — the same argv the real run
  uses, from the same function, so it can be trusted.
- **On Windows the running `edify.exe` may be locked.** That failure is detected and
  reported with the exact command to run from another shell, never as a success it did
  not have.
- **This is the second command that can reach the network**, because building a wheel
  fetches `hatchling` unless it is cached. Said out loud in the module docstring rather
  than quietly breaking the claim in `cli.py`; `--offline` fails cleanly instead.
- It never touches `.edify/` in any repository. That is `edify setup . --fresh`, and the
  closing line says so.

#### The install has a face

`edify init` and `edify setup` did real work and printed nothing while doing it.

- **An ASCII wordmark** opens every install, once — `setup` and `init new` print it and
  tell `init_cmd` not to print a second, mirroring the existing `caller_closes`.
- **An animated ∞** paints to stderr while extraction, skill install, and host mirroring
  run. It is a **lemniscate of Gerono** (`x = cos t`, `y = sin 2t / 2`), which is evenly
  parameterised, so a constant-speed head reads as constant-speed motion; Bernoulli's
  crowds at the origin and looks like a stutter.
- **Precomputed frames, not a live plotter.** `dependencies = []` is a hard constraint,
  so the animation is a tuple of strings built once at import — which also makes it
  testable: frame count, uniform width, one head per frame, ASCII-safety.
- **Two glyph sets, chosen by probing the stream encoding.** A cp1252 Windows console
  gets `O o .`; anything that can encode them gets `● ○ ·`. A command that did its work
  and then died printing its own decoration is the worst of both outcomes.
- **`Out.animated`** is the one place tty, `--json`, `--quiet`, `--no-anim`,
  `EDIFY_NO_ANIM`, `CI`, and `TERM=dumb` are decided — beside the existing
  `Out.interactive`, so no call site invents a second rule.
- Decoration is never load-bearing: a painter exception disables the animation and the
  command carries on. The cursor is restored in a `finally` and again at `atexit`, so
  Ctrl-C never leaves a headless terminal behind.
- `--json` output is byte-identical to before, and a non-tty run emits no escape codes.

#### The fifth gate, and a way to pay

- **Three projects on the free plan** (`FREE_PROJECT_CAP`), unlimited on paid.
  `projects.unlimited` joins the four existing entitlements; the tier docstring that
  said "four gates, and they are the only four" now says five.
- **The ledger is a readable TSV** in `user_config_dir()`, one row per project: key,
  path, first seen. It never leaves the machine — there is no telemetry, ever — so
  hashing or hiding it would buy nothing and cost you the ability to read your own limit.
- **A project is keyed on its `git remote origin`**, falling back to the resolved path.
  A re-clone, a second worktree, and a fresh CI checkout are one project. Keying on the
  path would burn a slot every CI run.
- **It never breaks work already done.** Only a *new* project is refused. A repository
  already in the ledger keeps installing, a deleted repository returns its slot the next
  time anything reads the ledger, and every non-install command ignores it entirely. A
  refused install leaves nothing behind — not even an empty `.edify/`.
- **`edify license projects`** lists what is using a slot, with `forget <path>` beside
  it. Releasing a slot is not a support ticket.
- **`edify license buy [--seats N]`** prints the plan and the price and opens a Stripe
  Payment Link in a browser — it opens a browser, it does not open a socket. Under
  `--json`, `--quiet`, or with no terminal it prints the URL and stops.
  `EDIFY_BUY_URL` overrides the link, which is how test mode is reached.
- **The price is one constant**, `PRO_PRICE`, so it cannot drift. It appears at a gate,
  in `edify license status`, and in the two soft caps that warn rather than raise
  (graph truncation, the registry cap). **Nowhere else** — no periodic reminder was
  added, and that was decided rather than overlooked.
- No new exit code: the project gate raises the existing `TierRequired` (exit 7), which
  already means "this needs the paid plan".
- `edify doctor`'s licence line now names the projects used.

#### The issuer

the licence issuer (private tooling) refuses to sign with a zero or single-repeated-byte seed or a
small counting integer, requires a real email, defaults `--days` to a billing month plus
the seven-day grace `docs/pricing.md` §3 specifies, prints a paste-ready customer
email, and appends an audit line to a gitignored `tools/.issued.tsv` that
the issuer's `issued` subcommand reads back. `keygen` refuses to overwrite an existing seed
without `--force`, because doing so invalidates every licence signed with it.

There is no webhook, no Postgres, and no transactional email in this build. That is
deferred deliberately: the token format does not change when the webhook lands, so every
token issued by hand stays valid.

#### New environment variables

| variable | effect |
|---|---|
| `EDIFY_NO_ANIM` | no banner, no animation; static lines instead |
| `EDIFY_BUY_URL` | overrides the Payment Link, for Stripe test mode |


### `edify init new` — a folder set up from zero, for whichever agent is opened

`init` and `setup` wrote `CLAUDE.md` and `.claude/`, and that was the whole install.
On a machine with Codex, Cursor, Gemini, Copilot, or Windsurf open — which is most of
them — EDIFY was installed and unreachable: the methodology existed in `.edify/` and no
runtime but one had been told where to look. The new command closes that, and asks the
questions detection cannot answer.

- **`edify init new [PATH]`.** The root is pinned where you point it (a new folder
  inside an existing checkout no longer installs into the parent), the folder is created
  if missing, EDIFY's own files are cleared first, and every library entry is installed.
  `--keep` reinstalls without clearing; `--agents` narrows the runtimes; `--yes` and
  `--no-interview` skip the questions.
- **Every runtime, from one table.** `src/edify/agents.py` is the table — instruction
  file, command directory, file suffix, and format per runtime — and `host.py` writes
  from it. Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot, Windsurf, and a
  generic `AGENTS.md` row for anything else. All seven instruction files carry the same
  block, so two tools open on one repository cannot be running two methodologies.
  Gemini's pointers are TOML, so the generated marker is a `#` comment there and an HTML
  comment everywhere else; Cursor's rule carries the `alwaysApply` header it needs to be
  loaded at all. Adding a runtime is adding a row.
- **It asks first, and two of the answers change the install.** Eight short questions
  before anything is written: which runtimes, what detection missed, who you are, your
  role, what is being built, what done looks like, how much to explain, and what an
  agent must never do here. The runtimes answer decides what gets installed and the
  stack answer reaches the library selection, so the interview is not a survey. The rest
  is written to `.edify/profile.md`, which every instruction file points at, recorded in
  the ledger under a new `answered` origin that `upgrade` will never overwrite, and
  read back on a re-run so last time's answers are the defaults. Enter skips any
  question. With no terminal nothing is asked, no profile is written, and the full
  install happens anyway — a question is never load-bearing.
- **Clearing is one implementation, not two.** `setup --fresh` and `init new` both call
  `host.clear`, which walks every runtime's directories and every instruction file. A
  pointer without EDIFY's marker is somebody's own file and is never touched; the block
  is removed from an instruction file somebody else owns, and the file itself only goes
  when nothing but the block was in it.
- **A later `edify init` keeps every runtime current.** With no `--agents`, the runtimes
  are whichever ones are already set up in the folder, falling back to `--host` when
  none are. Five stale instruction files and one current one is worse than either state.
  A hand-written `AGENTS.md` is never taken as evidence that Codex or Cursor is set up
  here, so `init` does not start writing into `.codex/` in a repository that asked for
  neither. `edify skills sync` follows the same rule, and `edify doctor` now checks
  every instruction file on disk rather than `CLAUDE.md` alone.

### `/harvest` picks its own source, and the pipeline runs end to end

`/harvest` was written and could not complete a run. Three reasons, and the first one
made the other two unreachable.

- **`edify/harvest/sources.md` had no sources.** One placeholder row, `| — | — | — |`,
  which the parser correctly discarded — so `edify harvest pick` printed "no sources
  listed" and step ① had nothing to fetch. The table now carries six real rows with
  their licence verified at the repository rather than inferred from a README badge,
  including two rows that are there to be *refused* correctly: `anthropics/skills` has
  no root LICENSE and per-directory terms, and `awesome-claude-code` is CC BY-NC-ND,
  which is neither allowlisted nor adaptable and is therefore an `index` row — read for
  links, never staged.
- **Nothing chose a row.** `pick` printed the whole table and left selection to the
  caller, which meant the one decision in the pipeline computable from files was a
  model's mood. `pick` now scores every row against the ledger — licence posture,
  admitted-to-rejected ratio at the human door, archived status, ledger exhaustion,
  months since the last draw — and names one, with the arithmetic printed and
  `--source NAME` to override. Two new columns feed it: `fetch`, so gathering is a
  listing instead of a search, and `status`, without which rows sharing a licence tie
  and the alphabetical tie-break hands the run an archived upstream. The parse is by
  column name, so an older table still reads.
- **Admission did not install.** `admit` copied the rewrite into `edify/skills/` — the
  authored tree that ships — and stopped, leaving an entry that was admitted and could
  not be loaded by anything. It now installs, indexes, mirrors, and re-records
  governance in the same command, on the far side of the door where it belongs.

The skill file names the fetch mechanics it had left implicit (pin the commit, resolve
the licence per artifact, `curl` for bytes rather than WebFetch — staging a model's
summary of a candidate poisons the hash the ledger identifies it by) and says what to do
about the commonest quarantine, which is a candidate that *quotes* the anti-pattern the
scan looks for.

### Installed skills are visible to the host runtime

An entry under `.edify/skills/` was installed as far as `edify skills list` was
concerned and invisible in the session the person was typing into, because Claude Code
discovers skills at `.claude/skills/<name>/SKILL.md`, one directory each.

- **`edify skills sync`**, and the same mirror inside `init`, `upgrade`, `setup`,
  `skills add`, and admission. Each file is a pointer carrying the two fields the
  runtime discovers on — `name` and the entry's own `description`, which is what
  relevance is matched against — plus the `role · phase · tech` coordinate, and then the
  canonical path. A copy would go stale the first time an entry changed.
- No `--force`: a pointer is derived output, so one that is out of date is brought
  current, and one EDIFY did not write is never touched. Every generated file carries a
  marker, which is how a hand-authored `SKILL.md` stays out of both the mirror and the
  governance ledger.
- Governance records the mirror as `generated`, and only where the marker is present —
  so `verify` no longer reports our own output as unrecorded, nor claims authorship of
  a command file somebody else wrote.

### `edify setup [PATH] [--fresh]` — the whole harness, in one folder

`init` finds its root by walking upward, so `mkdir service && cd service && edify init`
inside an existing checkout installs into the **parent**, silently, into the `.edify/`
the outer repository already has. `setup` pins the root at exactly the path given,
creates the folder if it is missing, and installs everything with force on.

`--fresh` clears EDIFY's own surface first — `.edify/`, the marked host pointers, and
its block in `CLAUDE.md` — and nothing else, ever: source code, a hand-written
`SKILL.md`, a custom command, and the rest of somebody's `CLAUDE.md` all survive it. It
is a reinstall, not `rm -rf`.

### `/harvest` — public capability becomes a library entry

`10-harvest.md` was designed and not written. It is written now, as one skill with
four steps and one door, and the door does not open by itself.

- `.claude/skills/harvest/SKILL.md` and `/harvest` — the method a model follows:
  gather, screen, rewrite, propose, stop. The contract is deliberately **not** in
  `.edify/commands/`, because harvest runs in EDIFY's own repository and is never
  installed into a client's. `edify harvest` refuses anywhere without the authored
  `edify/harvest/` tree, so the boundary is checkable rather than documented.
- `edify harvest pick | stage | screen | propose | admit | reject | status`. The
  first four run unattended; `admit` requires a person at a terminal and there is
  no flag that changes that. Fetching stays outside the CLI — `stage` records what
  arrived, so `edify` still opens no socket except `upgrade`.
- **`harvest/ledger.json`** — every candidate ever seen, and what became of it. A
  candidate is recognised by three independent identities: its URL, the sha256 of
  its raw bytes, and the entry name it would take. Any one matching is a match,
  because the same file moves between repositories, gets re-tagged, and arrives
  renamed. Nothing is gathered, screened, or proposed twice, and the reason
  recorded against a rejection is what makes the next run cheap.
- The screen is mechanical and fail-closed: a permissive-licence allowlist where
  unresolvable means `NONE-FOUND` and `NONE-FOUND` is rejected, a duplicate check
  by name and by hash, and an injection scan for exfiltration, tool abuse, gate
  evasion, and hidden characters. An injection hit sends the candidate to
  `harvest/quarantine/` flagged rather than to the bin — someone will want to know
  what was attempted. Nothing short-circuits; every failure is reported.
- `staging/` and `quarantine/` are in `.gitignore`. They hold a stranger's text
  verbatim; the permanent record is the ledger's verdict and three hashes.

### Fixed

- A `→` or `·` in command output no longer kills the command on a Windows console
  that defaults to cp1252. `edify skills add` and every other line that carried one
  did its work and then died writing the sentence about it — the file on disk, the
  exit code saying failure. Unencodable characters now degrade to a replacement.

### Governance over every installed file

- `.edify/governance.tsv` — one row for every file EDIFY writes into a repository:
  path, kind, origin, provenance, licence, sha256, and the version that installed
  it. Skill entries carried provenance already; command files, format examples, the
  seeded registry, the scraped conventions, the host pointers, and `CLAUDE.md` did
  not. Written by `init`, `upgrade`, and `skills add`.
- `edify governance list | verify | rebuild`, and a governance line in `edify doctor`.
- `verify` distinguishes a file EDIFY owns being **modified** — `upgrade` will
  replace it — from a file the repository owns being **edited**, which is what
  `mcp.md` and `conventions.md` are for. It prints; `--exit-code` makes it a gate
  the customer owns, the same posture as `edify check`.
- The graph is deliberately outside the ledger: regenerated output with its own
  checksums in `.edify/graph/meta`.

### The library asks before it installs

- `edify init` shows the entries your stack matched and takes an answer, because a
  skill file is trusted instruction in every matching session. `--skills
  ask|all|none|<names>` and `--yes` state the answer up front.
- `edify upgrade` asks the same question about entries arriving from an archive.
- **With no terminal nothing is asked** and the whole matched set is installed, so
  CI, a pipe, and a model calling the binary behave exactly as before. `CI`,
  `EDIFY_ASSUME_YES`, and `EDIFY_NO_PROMPT` also switch the question off.

### Feedback, with no telemetry added

- `edify feedback` asks four questions and writes the answers to a file under the
  user's config directory, then prints the `gh` command and the URL that would send
  it. **Nothing is transmitted**; `edify upgrade` remains the only command that
  opens a socket, and `docs/pricing.md` §4 is unchanged.
- A one-line invitation on stderr as the CLI opens: at most once per released
  version, only on a real terminal, never in CI or a pipe. `edify feedback off`, or
  `EDIFY_NO_FEEDBACK`, ends it permanently.
- `edify feedback list | show | off | on`.

### macOS

- The config directory follows the platform: `~/Library/Application Support/edify`
  on macOS, `%APPDATA%\edify` on Windows, `$XDG_CONFIG_HOME/edify` elsewhere. A Mac
  that already has `~/.config/edify` keeps it — an upgrade never orphans a licence.
- The walk ignores what macOS writes into a source tree: `.DS_Store`, `__MACOSX`,
  and bundle directories (`.app`, `.framework`, `.dSYM`, `.xcassets`, `.lproj`).
- `INSTALL.md` — pipx, uv, and Homebrew, with the PATH fixes people actually hit.
- `packaging/homebrew/edify.rb` — the tap formula, reviewed alongside the code it
  installs.
- CI installs and drives the built wheel on macOS as well as Linux, and runs the
  `pipx` path a Mac user is told to use.

### Publishing

- The release runbook (private) — registering the name, PyPI trusted publishing via GitHub OIDC,
  the TestPyPI rehearsal, the per-release checklist, and the Homebrew tap.
- `.github/workflows/release.yml` — tag-driven, no API tokens, refuses to publish
  when the git tag and the package version disagree, and smoke-installs the wheel on
  macOS, Linux, and Windows before it uploads anything.
- The version is asserted identical in `src/edify/__init__.py`, `pyproject.toml`, and
  `edify/manifest.md`.

## [0.1.0] — 2026-08-07

First release. The graph commands and the methodology surface — steps 1 and 2 of the
build order in `docs/design/architecture/09-cli.md` §5 — plus the install path a stranger
needs.

### The map

- `edify graph build` — deterministic extraction over the whole tree. A rebuild on
  unchanged source is byte-identical, so a graph diff is a structural diff.
- `edify graph update <dir>...` — directory-scoped re-extraction, merged into the
  existing graph. This is what runs after each build phase.
- `edify graph where | dependents | defines | overlap | references | stat`.
- Python is parsed with a real syntax tree; 19 other languages are covered by a
  declarative line scanner; Markdown headings and SQL tables are structural.
  `meta.method_<language>` records which, so a scan is never mistaken for a parse.
- An uncovered language produces a file node and nothing else, and
  `meta.languages_uncovered` names it. No model writes the graph at any stage.
- Optional adapter for an external syntax-tree extractor: `--extractor ctags`.

### The documents

- `edify check` — the whole validation story, over specs, plans, tasks, skill files
  and the server registry. It reports; it never blocks. `--exit-code` is there so a
  team that needs a hard block can own one.
- `edify check --fix` — the two mechanical repairs only: resolving a filename to a
  line range through the graph, and re-sorting the skill index.
- Parsers for `spec.md`, `plan.md`, `tasks.md`, skill frontmatter, and `mcp.md`.

### The install

- `edify init` — detect the stack, extract the graph, scrape conventions from the
  config files with zero model calls, install the matching skill entries, seed the
  server registry, and write a fifteen-line `CLAUDE.md`. Merges into an existing
  instruction file; never overwrites it.
- `edify skills list | resolve | index | add` — resolution is a lookup over a sorted
  TSV, never a model reading a directory.
- `edify mcp list | check | for` — scoping per role and phase is inspectable.
- `edify doctor` — five checks and a green/amber/red line.
- `edify upgrade` — the one command that reaches the network, with `--archive` for
  air-gapped machines. Every entry is validated and licence-checked before it lands.

### The methodology tree

- Five command files: `/spec`, `/plan`, `/tasks`, `/build`, `/verify`.
- Three format contracts and their three worked examples.
- Twelve skill entries across all six roles, every one under budget.
- The harvest design, its two reference files, and the default one-entry registry.

### Commercial

- Offline licence verification: Ed25519 in pure Python over the standard library,
  checked against the RFC 8032 §7.1 test vector. No network call, no activation
  server, no machine binding.
- `edify license status | activate | deactivate`.
- Free plan: everything, forever, no account, up to 25,000 graph nodes. Four paid
  entitlements — `graph.unlimited`, `library.upgrade`, `mcp.multi`, `team`.
- the licence issuer (private tooling) — the issuer, so the whole path is testable end to end.
- Full commercial design in `docs/pricing.md`.

### Known limits

- The built-in extractor scans rather than parses everything except Python,
  Markdown and SQL. `edify doctor` reports this as amber and names the fix.
- `edify mcp check` cannot verify a pin for a server with a remote transport or one
  that does not answer `--version`. It reports that as unprobeable rather than as
  passing.
- Standalone binaries are not built yet (M4 in the release milestones). The
  install path today is `pipx` or `uv tool`.
