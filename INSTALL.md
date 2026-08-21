# Installing EDIFY

`edify` is a single Python package with **no dependencies**. It installs on macOS,
Linux, and Windows the same way, needs no compiler, no network at run time, and no
procurement conversation about a runtime it drags in behind it.

Requirements: **Python 3.10 or newer**. That is the whole list.

---

## macOS

### With pipx (recommended)

`pipx` puts the binary on your PATH in its own virtual environment, so `edify` never
collides with a project's dependencies.

```bash
brew install pipx        # or: python3 -m pip install --user pipx
pipx ensurepath          # adds ~/.local/bin to PATH; open a new shell after this
pipx install edify-cli

edify version
```

### With uv

```bash
brew install uv
uv tool install edify-cli
```

### With Homebrew directly

```bash
brew install EDIFY-agents/tap/edify
```

The tap is published from this repository's `packaging/homebrew/edify.rb`. It
installs the same PyPI artifact, wrapped in Homebrew's own Python virtualenv.

### If `edify: command not found`

The package installed but its directory is not on your PATH. Almost always one of:

| shell | file | line to add |
|---|---|---|
| zsh (the macOS default) | `~/.zshrc` | `export PATH="$HOME/.local/bin:$PATH"` |
| bash | `~/.bash_profile` | `export PATH="$HOME/.local/bin:$PATH"` |
| fish | `~/.config/fish/config.fish` | `fish_add_path ~/.local/bin` |

`pipx ensurepath` writes that line for you; you still have to open a new shell.

On Apple Silicon, Homebrew lives in `/opt/homebrew` rather than `/usr/local`. If
`brew` itself works but the tools it installs do not, `eval "$(/opt/homebrew/bin/brew shellenv)"`
in your shell profile is the missing piece.

### Where macOS keeps EDIFY's own files

```
~/Library/Application Support/edify/license      the licence token, if you have one
~/Library/Application Support/edify/state        run count and whether the feedback line is on
~/Library/Application Support/edify/feedback/    anything `edify feedback` wrote, unsent
```

Nothing else on the machine is touched, and nothing outside a repository is written
by a non-interactive run. A machine that already has `~/.config/edify` from an older
install keeps using it — upgrading never orphans a licence. `EDIFY_HOME` overrides
the location entirely.

### Apple's quarantine

Not applicable. There is no downloaded binary and no code signature to check: `pip`,
`pipx`, `uv`, and `brew` all install a Python package from PyPI over TLS, and
Gatekeeper does not gate that.

---

## Linux

```bash
pipx install edify-cli          # or: uv tool install edify-cli
```

Configuration lives in `$XDG_CONFIG_HOME/edify`, or `~/.config/edify`.

## Windows

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
pipx install edify-cli
```

Configuration lives in `%APPDATA%\edify`.

---

## Verifying the install

```bash
cd your-repository
edify init
edify doctor
```

`doctor` prints a line per subsystem and a green/amber/red verdict. **Amber is a
normal result**: with no Universal Ctags on the machine, the built-in extractor
parses Python exactly and scans everything else, and `doctor` says so rather than
implying parse-grade coverage it does not have.

Optional, for parse-grade extraction across the rest of your stack:

```bash
brew install universal-ctags          # macOS
sudo apt install universal-ctags      # Debian/Ubuntu
edify graph build --extractor ctags
```

## What `init` asks

One question: which entries from the agent library to install. They become trusted
instruction in every matching session, so you see the list before any of it lands.

With no terminal — CI, a pipe, a model calling the binary — nothing is asked and the
whole stack-matched set is installed. To state the answer up front:

```bash
edify init --yes                       # the whole matched set, no question
edify init --skills none               # none of it; add entries later
edify init --skills planner,verifier   # exactly these
```

## Setting a folder up from zero, for every agent

`edify init` writes `CLAUDE.md` and `.claude/`. If your team also has Codex, Cursor,
Gemini, Copilot, or Windsurf open, that install is invisible to them. `edify init new`
pins the root where you point it, creates the folder if it is missing, clears EDIFY's
own files first, installs every library entry, and writes the instruction file and
command pointers each runtime actually reads.

```bash
edify init new ./service               # ask, then install for every runtime
edify init new . --agents claude,cursor
edify init new . --yes                 # ask nothing, install everything
```

It asks eight short questions before installing anything — which runtimes, what stack
detection missed, who you are, your role, what is being built, what done looks like, how
much an agent should explain, and what it must never do here. Enter skips any of them.
The answers land in `.edify/profile.md`, which every instruction file points at and
which is yours to edit; a re-run offers them back as the defaults. With no terminal
nothing is asked and no profile is written.

## Installing from a checkout

```bash
git clone https://github.com/EDIFY-agents/edify_public
cd edify_public
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

`EDIFY_ASSETS` points the asset resolver at a checkout's `edify/` directory if you
need to run an installed binary against an edited methodology tree.

## Updating from a checkout

`edify upgrade` pulls a newer **skill library**. `edify self update` replaces the
**CLI itself** — the two are different things and neither does the other's job.

```bash
edify self where                    # which edify is this, and where did it come from
edify self update --dry-run         # the exact install command, run nothing
edify self update                   # reinstall from the checkout this code came from
edify self update --from ~/src/edify --editable
```

`self update` shells out to whichever tool put `edify` on PATH — uv, pipx, or pip —
because only that tool can correctly replace it. A hardcoded `pip install` into a uv
tool environment produces a second, shadowed copy, which is the worst possible outcome
for a command named "update". Detection reads `sys.prefix`; when it is wrong,
`--manager uv|pipx|pip` overrides it, and `edify self where` prints what was detected
before anything is installed. After a successful install the *new* binary is asked for
its version, so a shadowed copy shows up as a version that did not move.

`--editable` installs in place, so later edits to the checkout need no reinstall at all.

**This is one of the two commands that can reach the network.** Building a wheel from a
checkout fetches `hatchling` unless it is already cached. `--offline` is the opt-in that
refuses to reach out and fails cleanly instead.

**On Windows the running `edify.exe` may be locked** by the shell you typed into.
`self update` detects that failure and prints the exact command to run from another
shell rather than reporting a success it did not have.

`self update` never touches `.edify/` in any repository. Reinstalling the harness into a
checkout is `edify setup . --fresh`.

## The free plan, and what a licence lifts

Nothing here needs an account. The free plan is a whole working system: every command,
every query, every check, the whole methodology tree, on repositories up to 25,000 graph
nodes, in up to three projects on one machine.

```bash
edify license status                   # what this machine is entitled to
edify license projects                 # which repositories are using a slot
edify license projects forget PATH     # release one
edify license buy --seats 1            # the pro plan, and where to pay
edify license activate <token>         # the token you were emailed
```

`edify license buy` opens a **browser**, not a socket, and prints the URL instead under
`--json`, `--quiet`, or with no terminal. Activation writes a signed token to a file and
verifies it locally — there is no activation server and no phone-home, so a licence works
on an air-gapped machine and keeps working if we are down.

The project count lives in `projects.tsv` beside the licence and never leaves your
machine. A project is keyed on its git remote where it has one, so a re-clone, a second
worktree, and a fresh CI checkout are one project rather than three; a repository you
delete returns its slot on its own. Only a **new** project is ever refused.

`EDIFY_LICENSE` carries a token in CI without writing a file. `EDIFY_LICENSE_PUBKEY`
points verification at a self-hosted issuer. `EDIFY_HOME` moves the licence, the project
ledger, and the feedback file together — which is also how a test isolates all three.

## Uninstalling

```bash
pipx uninstall edify-cli                        # or: brew uninstall edify
rm -rf ~/Library/Application\ Support/edify     # macOS; ~/.config/edify elsewhere
```

Inside a repository, EDIFY's footprint is `.edify/`, `specs/`, one command directory per
agent runtime it was asked for (`.claude/`, `.codex/`, `.cursor/`, `.gemini/`,
`.github/prompts/`, `.windsurf/`), and a marked block inside each runtime's instruction
file. `edify governance list` prints every file it put there, so removing it is a list
you can read rather than a hunt — and every generated file carries a marker line, so a
skill, prompt, or command you wrote yourself is not in that list and is not touched by
removing EDIFY.

To reinstall the lot in place rather than remove it, `edify setup . --fresh` or
`edify init new .` clears exactly that footprint and writes it again.
