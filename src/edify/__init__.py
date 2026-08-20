"""EDIFY — three documents and a map.

A harness that sits around an AI coding agent and makes it work reliably on large
codebases. This package is the `edify` binary: it installs the harness, builds and
queries the graph, resolves skills, and checks formats.

It is not the agent runtime and it never wraps a model.
"""

__version__ = "0.1.0"

# The on-disk contract version for `.edify/graph/`. Bumping it means an existing
# graph is rebuilt rather than misread.
GRAPH_SCHEMA = 1

# The on-disk contract version for `.edify/skills/index.tsv`.
INDEX_SCHEMA = 1

__all__ = ["__version__", "GRAPH_SCHEMA", "INDEX_SCHEMA"]
