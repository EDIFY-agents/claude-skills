"""The map: every file, module, exported symbol, route and table, with edges.

Mechanically extracted, never written by a model — not at install, not as a
fallback, not for a language the extractor does not cover. Where a language is not
covered the graph has no nodes for it and `meta` says so.
"""

from .model import Edge, Node, EDGE_KINDS, NODE_KINDS
from .store import GraphStore, load

__all__ = ["Edge", "Node", "EDGE_KINDS", "NODE_KINDS", "GraphStore", "load"]
