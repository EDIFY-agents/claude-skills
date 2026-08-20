# EDIFY manifest

What this install is, and what it pins. Read by `edify doctor` and `edify upgrade`.

- edify: 0.1.0
- library: 0.1.0
- graph-schema: 1
- index-schema: 1
- extractor: builtin
- extractor-alternative: universal-ctags
- extractor-min-version: 6.0.0

## The extractor

The built-in backend parses Python with the standard library's syntax tree and
scans every other covered language with a declarative line-pattern table.
`meta.method_<language>` in `.edify/graph/meta` records which one produced each
language's nodes, so a scan is never mistaken for a parse.

Where parse-grade precision is needed across the rest of the stack, install
Universal Ctags and run `edify graph build --extractor ctags`. The TSV contract is
what EDIFY owns; the extractor is replaceable by construction, and
`src/edify/graph/langs/ctags.py` is the only file that changes when it is replaced.

## What no model touches

The graph, at any stage, for any reason — including where a language is not
covered, in which case the graph has no nodes for it and `meta.languages_uncovered`
says which. Skill resolution and server scoping are exact-match lookups over sorted
tables.
