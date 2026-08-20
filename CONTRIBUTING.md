# Contributing to EDIFY

Thank you for considering it. This document is short because the process is
short.

---

## The fastest useful contribution

Run EDIFY on one real task in a repository you actually work in, and tell us
what broke.

```bash
pipx install edify-cli
cd your-repository
edify init
edify doctor
```

If `edify doctor` is anything other than green, that is a bug report and we
want it. If the graph missed a symbol you expected, that is a **graph gap** —
there is an issue template for exactly that, and those reports are the single
most valuable thing we receive.

## Before you open a pull request

| you want to | do this first |
|---|---|
| fix a bug | open an issue, or just send the PR if it is small and obvious |
| add a language to the graph extractor | open an issue — the extractor contract is in [`docs/design/architecture/06-graph.md`](docs/design/architecture/06-graph.md) |
| add or change a skill library entry | read [`docs/design/architecture/10-harvest.md`](docs/design/architecture/10-harvest.md); entries are curated, not merged on sight |
| change a document format | open a **discussion**, not an issue — formats are contracts and changing one invalidates existing specs |
| add a runtime dependency | open a discussion and expect resistance; see below |
| change positioning, pricing, or claims | open a discussion |

## The one hard rule: no runtime dependencies

`[project] dependencies` in `pyproject.toml` is empty and stays empty.

This is not minimalism as taste. EDIFY installs on locked-down build servers
where every added package is a procurement conversation, and "no dependencies"
is a property the product sells. A PR that adds one will be declined regardless
of how good it is otherwise. Optional extras are fine — `treesitter` is one —
provided the tool degrades cleanly and `edify doctor` reports which backend is
in use.

## Development setup

```bash
git clone https://github.com/edify-dev/edify && cd edify
pip install -e ".[dev]"
pytest
```

The suite checks that this repository satisfies what EDIFY asks of yours: every
skill file valid and under budget, every command file short, and every worked
example parsing against the format it calibrates. If you change a format, the
examples must still parse.

```bash
pytest -q                      # the whole suite
pytest tests/test_graph.py -q  # one file
edify check                    # the documents in this repo
edify governance verify        # has anything EDIFY installed drifted
```

## What a good pull request looks like

- **One thing.** A PR that fixes a bug and reformats a file is two PRs.
- **A test that failed before it.** This project builds verification-first and
  applies that to itself.
- **The existing voice.** Comments here explain *why*, not *what*. Match the
  density and the register of the file you are editing.
- **No new dependency.** See above.
- **`pytest` green** and `edify check` no worse than it was.

## Contributor licensing (please read — it is four sentences)

EDIFY is released under the [Functional Source License](LICENSE)
(FSL-1.1-Apache-2.0), and each version converts to Apache 2.0 after two years.

By submitting a contribution you certify the [Developer Certificate of
Origin](https://developercertificate.org/) — that you wrote it, or have the
right to submit it — and you grant EDIFY a perpetual, worldwide, non-exclusive,
royalty-free, irrevocable licence to use, reproduce, modify, sublicense, and
distribute your contribution, **including under licences other than the FSL**.

That last clause is what lets us keep the two-year Apache 2.0 conversion
promise, ship commercial builds, and relicense the whole project more
permissively later without hunting down every contributor. It does not take
your copyright — you keep it, and you can do anything you like with your own
work elsewhere.

Sign off your commits:

```bash
git commit -s -m "graph: cover Kotlin object declarations"
```

## Reporting a security issue

Do not open an issue. See [SECURITY.md](SECURITY.md).

## Where conversation happens

- **[Issues](https://github.com/edify-dev/edify/issues)** — reproducible bugs, install problems, graph gaps.
- **[Discussions](https://github.com/edify-dev/edify/discussions)** — questions, ideas, benchmark
  methodology, "is this the right approach", showing what you built.

There is no Discord. When there is a recurring community that needs one, there
will be. Until then, everything stays public, searchable, and next to the code.
