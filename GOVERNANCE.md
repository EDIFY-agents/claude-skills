# Project Governance

Who decides what, and how that changes.

## Today: single-vendor, open contribution

EDIFY is built and maintained by EDIFY. Direction, the roadmap, the document
formats, and what the paid tier gates are decided by the maintainers. Anyone may
open issues, discussions, and pull requests, and they are reviewed on merit.

We state this plainly rather than describing a committee that does not exist. A
project with one maintainer and a governance document describing a technical
steering committee is telling you something false on its first page.

## What is open to contribution and what is not

| area | who decides |
|---|---|
| bug fixes, tests, docs, platform support | contributors — send the PR |
| new languages in the graph extractor | contributors, against the extractor contract |
| skill library entries | maintainers, after curation ([harvest](docs/design/architecture/10-harvest.md)) |
| the three document formats | maintainers — these are contracts; changing one invalidates every existing spec |
| the five commands and their boundaries | maintainers |
| pricing, gates, licensing | maintainers |
| the name and marks | maintainers ([TRADEMARK.md](TRADEMARK.md)) |

## How decisions get made in public

Anything that changes behaviour a user depends on goes through a
[discussion](https://github.com/EDIFY-agents/edify_public/discussions) before it goes through a PR. The reasoning is
written down in [`docs/design/`](docs/design/), which is the actual source of
truth for this project — including
[`10-what-we-dropped.md`](docs/design/10-what-we-dropped.md), which is the
ledger of everything cut and what the cut cost. A design dossier that lists only
additions is a sales document.

## Licence stability

The [FSL](LICENSE) grant is irrevocable and each released version converts to
Apache 2.0 on its second anniversary. **We cannot take that back.** A version
published today is Apache 2.0 in two years even if the company is gone, the
project is abandoned, or a future maintainer would rather it were not.

If EDIFY is acquired or discontinued, the conversion still runs on every version
already published. That is the point of choosing a licence with a dated
conversion instead of a promise.

## Becoming a maintainer

Sustained, high-quality contribution over time, plus judgment about what belongs
in the product — which mostly means a demonstrated willingness to argue *against*
adding things. Maintainers are invited, not applied for.

## If this project is abandoned

The [CHANGELOG](CHANGELOG.md) records every release date, so the Apache 2.0
conversion date of every version is computable without us. The methodology tree
under [`edify/`](edify/) is plain Markdown and useful without the CLI. The graph
format is documented, checksummed TSV that any tool can read.

Nothing here requires us to stay alive for your repository to keep working.
