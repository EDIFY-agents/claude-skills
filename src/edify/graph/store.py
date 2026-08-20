"""Reading and writing `.edify/graph/`.

Three files: nodes.tsv, edges.tsv, meta. Sorted and checksummed, so a rebuild on
unchanged source is byte-identical and a graph diff is a structural diff of the
codebase.
"""

from __future__ import annotations

from pathlib import Path

from .. import GRAPH_SCHEMA
from ..errors import GraphMissing
from ..paths import Layout
from ..tsv import read_kv, read_rows, sha256_file, write_kv, write_rows
from .model import Edge, Node

NODE_HEADER = ("id", "kind", "file", "line", "name", "fingerprint")
EDGE_HEADER = ("from", "relation", "to")


class GraphStore:
    """The graph on disk, loaded lazily.

    Nodes and edges are read on first use and kept in memory for the life of one
    command. At the scale that matters — around a hundred thousand exported
    symbols for a million lines — that is tens of megabytes and one pass over
    sorted text.
    """

    def __init__(self, layout: Layout):
        self.layout = layout
        self._nodes: list[Node] | None = None
        self._edges: list[Edge] | None = None
        self._by_name: dict[str, list[Node]] | None = None
        self._by_id: dict[str, Node] | None = None
        self._by_file: dict[str, list[Node]] | None = None

    # -- presence --------------------------------------------------------

    def exists(self) -> bool:
        return self.layout.nodes.exists()

    def require(self) -> None:
        if not self.exists():
            raise GraphMissing()

    # -- loading ---------------------------------------------------------

    @property
    def nodes(self) -> list[Node]:
        if self._nodes is None:
            self.require()
            self._nodes = [Node.from_row(r) for r in read_rows(self.layout.nodes)]
        return self._nodes

    @property
    def edges(self) -> list[Edge]:
        if self._edges is None:
            self.require()
            self._edges = [Edge.from_row(r) for r in read_rows(self.layout.edges)]
        return self._edges

    @property
    def by_name(self) -> dict[str, list[Node]]:
        if self._by_name is None:
            index: dict[str, list[Node]] = {}
            for n in self.nodes:
                index.setdefault(n.name, []).append(n)
                # The last segment too, so `where accept` finds `Service.accept`.
                tail = n.name.rsplit(".", 1)[-1]
                if tail != n.name:
                    index.setdefault(tail, []).append(n)
            self._by_name = index
        return self._by_name

    @property
    def by_id(self) -> dict[str, Node]:
        if self._by_id is None:
            self._by_id = {n.id: n for n in self.nodes}
        return self._by_id

    @property
    def by_file(self) -> dict[str, list[Node]]:
        if self._by_file is None:
            index: dict[str, list[Node]] = {}
            for n in self.nodes:
                index.setdefault(n.file, []).append(n)
            self._by_file = index
        return self._by_file

    @property
    def meta(self) -> dict[str, str]:
        return read_kv(self.layout.meta)

    # -- writing ---------------------------------------------------------

    def write(self, nodes: list[Node], edges: list[Edge], meta: dict[str, str]) -> dict[str, str]:
        """Write all three files and return the meta actually recorded."""
        self.layout.graph_dir.mkdir(parents=True, exist_ok=True)
        seen_nodes: dict[str, Node] = {}
        for n in nodes:
            # First writer wins on a duplicate id, which makes the result
            # independent of directory iteration order.
            seen_nodes.setdefault(n.id, n)
        deduped_nodes = sorted(seen_nodes.values(), key=lambda n: n.id)
        deduped_edges = sorted({(e.src, e.relation, e.dst) for e in edges})

        nodes_sha = write_rows(self.layout.nodes, (n.row() for n in deduped_nodes), NODE_HEADER)
        edges_sha = write_rows(
            self.layout.edges, ([s, r, d] for s, r, d in deduped_edges), EDGE_HEADER
        )
        full = dict(meta)
        full.update(
            {
                "schema": str(GRAPH_SCHEMA),
                "nodes": str(len(deduped_nodes)),
                "edges": str(len(deduped_edges)),
                "nodes_sha256": nodes_sha,
                "edges_sha256": edges_sha,
            }
        )
        write_kv(self.layout.meta, full)
        self._nodes = deduped_nodes
        self._edges = [Edge(s, r, d) for s, r, d in deduped_edges]
        self._by_name = self._by_id = self._by_file = None
        return full

    # -- integrity -------------------------------------------------------

    def verify_checksums(self) -> list[str]:
        """Complaints, one line each. Empty means the files match their meta."""
        problems: list[str] = []
        meta = self.meta
        for path, key in ((self.layout.nodes, "nodes_sha256"), (self.layout.edges, "edges_sha256")):
            recorded = meta.get(key)
            if not recorded:
                problems.append(f"{path.name}: no checksum recorded in meta")
                continue
            actual = sha256_file(path)
            if actual != recorded:
                problems.append(f"{path.name}: content does not match its recorded checksum")
        if meta.get("schema") and meta["schema"] != str(GRAPH_SCHEMA):
            problems.append(
                f"graph schema is {meta['schema']}, this edify writes {GRAPH_SCHEMA}"
                " — run `edify graph build`"
            )
        return problems


def load(layout: Layout) -> GraphStore:
    return GraphStore(layout)


def graph_paths(root: Path) -> tuple[Path, Path, Path]:
    base = root / ".edify" / "graph"
    return base / "nodes.tsv", base / "edges.tsv", base / "meta"
