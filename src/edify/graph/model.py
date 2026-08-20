"""What a node and an edge are.

Granularity is the public surface: files, modules, exported symbols, routes,
tables, packages, doc sections. Local variables are not indexed — they churn on
every commit and answer questions a model resolves better by reading the function.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

NODE_KINDS = ("file", "module", "symbol", "route", "table", "package", "doc-section")
EDGE_KINDS = ("defines", "references", "imports", "exposes", "documents", "migrates")


def node_id(kind: str, file: str, name: str) -> str:
    """A stable id.

    Space-separated in the manner of the code-indexing standard's symbol strings,
    so an external indexer can be pointed at this format without translation.
    The id is derived only from things that survive a reformat: the kind, the
    file, and the name. Not the line — a symbol that moves down ten lines is the
    same symbol.
    """
    if kind in ("table", "package"):
        return f"{kind} . {name}"
    if kind in ("file", "module"):
        return f"{kind} {file} ."
    return f"{kind} {file} {name}"


def fingerprint(signature: str) -> str:
    """Twelve hex characters of the normalised signature.

    Enough to tell "this symbol changed shape" from "this symbol moved", which is
    the only question the column is asked.
    """
    normalised = " ".join(signature.split())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    file: str
    line: int
    name: str
    fingerprint: str = "-"

    def row(self) -> list[str]:
        return [self.id, self.kind, self.file, str(self.line), self.name, self.fingerprint]

    @staticmethod
    def from_row(row: list[str]) -> "Node":
        while len(row) < 6:
            row = row + ["-"]
        try:
            line = int(row[3])
        except ValueError:
            line = 0
        return Node(row[0], row[1], row[2], line, row[4], row[5])

    @property
    def ref(self) -> str:
        """The `file:line` form every reference in the system is written in (P3)."""
        return f"{self.file}:{self.line}" if self.line else self.file


@dataclass(frozen=True)
class Edge:
    src: str
    relation: str
    dst: str

    def row(self) -> list[str]:
        return [self.src, self.relation, self.dst]

    @staticmethod
    def from_row(row: list[str]) -> "Edge":
        return Edge(row[0], row[1], row[2] if len(row) > 2 else "")


@dataclass
class Extraction:
    """What one extractor pass produced, before reference resolution."""

    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    # (source node id, referenced name, relation) — resolved against the global
    # index after the walk, and dropped when it resolves to nothing in the repo.
    # An unresolved reference is an external one, and external things are not in
    # this graph.
    pending_refs: list[tuple[str, str, str]] = field(default_factory=list)
    languages: set[str] = field(default_factory=set)

    def extend(self, other: "Extraction") -> None:
        self.nodes.extend(other.nodes)
        self.edges.extend(other.edges)
        self.pending_refs.extend(other.pending_refs)
        self.languages |= other.languages
