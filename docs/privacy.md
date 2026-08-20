# Privacy and offline behaviour

**Your code stays your code.**

There is no telemetry in EDIFY. Not anonymous, not aggregate, not opt-out.
Nothing in this tool reports what you ran, what repository you ran it in, or
that you installed it.

---

## Why it is built this way

The buyer here is frequently the person who has to explain to somebody external
what touched the source tree. A tool that phones home loses that conversation
before it starts — and a build server in a serious account often has no outbound
network at all, so a tool that needs one is a tool that does not run.

## What opens a socket

Exactly two commands, both by explicit user action:

| command | what it fetches | how to refuse |
|---|---|---|
| `edify upgrade` | a newer curated skill library | `--from ARCHIVE` installs from a local file; air-gapped path documented |
| `edify self update` | a newer release, via uv / pipx / pip | `--offline` refuses outright |

**Everything else is a pure function over files.** Every other command reads
files and writes files. None holds state, and none opens a socket while doing
your work — including `edify license activate`, which verifies an Ed25519
signature locally against a key compiled into the binary.

You do not have to take our word for it:

```bash
# every network call site in the source
grep -rnE '(urlopen|urlretrieve|requests\.|httpx\.|socket\.socket)' src/
```

CI enforces this on every push — see
[`.github/workflows/guard.yml`](../.github/workflows/guard.yml). A network call
appearing outside those two commands fails the build, and is a
[security bug](../SECURITY.md) if it ever ships.

## What EDIFY writes, and where

Inside your repository, and nowhere else during ordinary work:

```
.edify/          the graph, the skills, the commands, the registry, the ledger
CLAUDE.md        ~15 lines — and one instruction file per agent runtime
specs/           what you and your agent wrote
```

On your machine, under your platform's config directory (`EDIFY_HOME` moves it):

```
licence          the signed token, if you activated one
projects.tsv     which repositories are using a free slot — plain, readable text
feedback/        anything you wrote with `edify feedback`, unsent
```

A non-interactive run — CI, a pipe, a model calling the binary — writes nothing
outside the repository at all. That is asserted in
[CI](../.github/workflows/ci.yml), not just claimed.

## The project ledger

`projects.tsv` holds one line per project: key, path, first seen. **Nothing about
it is ever sent anywhere**, so there is nothing to gain by hashing or hiding it
and plenty to lose — you can read your own limit.

```bash
edify license projects              # what is using a slot
edify license projects forget PATH  # release one
```

A project is keyed on its git remote, so a re-clone, a second worktree, and a
fresh CI checkout count once. A repository whose folder is gone returns its slot
the next time anything reads the ledger.

## Feedback, since there is no telemetry

Feedback works the other way round: you write it, you read it, you send it.

```bash
edify feedback        # four questions → a file under your config directory
edify feedback list   # what you have written; none of it has been sent
edify feedback off    # the one-line invitation never appears again
```

The file stays on your machine. `edify feedback` prints a `gh issue create`
command and a URL, and sending it is something *you* do, having read it.

The invitation itself is one dim line on stderr, shown at most once per released
version, only on a real terminal, and never inside CI or a pipe.

## The supply chain

`[project] dependencies` is empty and stays empty. EDIFY runs on the Python
standard library alone, so there is nothing in the dependency tree to compromise
but Python itself. That constraint is enforced in
[CI](../.github/workflows/guard.yml) and is the one hard rule in
[CONTRIBUTING.md](../CONTRIBUTING.md).

Optional extras — `tree-sitter` for parse-grade extraction — are never required,
and `edify doctor` reports which backend is actually in use.

## Your agent is a separate question

EDIFY does not host, wrap, or route to a model. When your coding agent sends your
code to Anthropic, OpenAI, Google, or anyone else, that is your agent's data
policy and your contract with that vendor — EDIFY is not in the path and cannot
change it.

What EDIFY changes is *how much* has to be sent: the graph answers "where is
this, and what breaks if it changes" from local files instead of by pasting the
repository into a context window.
