"""The queries. Everything the system asks the graph reduces to these.

`where` · `dependents` · `defines` · `overlap` · `references`. Each is a scan or a
lookup over sorted text: no model, no network, no state, and the same answer on
Tuesday.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass

from .model import Node
from .store import GraphStore


@dataclass(frozen=True)
class Hit:
    node: Node
    signature: str

    def line(self) -> str:
        return f"{self.node.ref}\t{self.node.kind}\t{self.node.name}"


def where(store: GraphStore, name: str, kind: str | None = None, limit: int = 50) -> list[Node]:
    """Where is this defined — file, line, kind.

    Exact match first. Only when nothing matches exactly does it fall back to a
    case-insensitive and then a glob match, so an exact name never returns a
    fuzzy answer.
    """
    exact = [n for n in store.by_name.get(name, []) if kind in (None, n.kind)]
    if exact:
        return _ordered(exact)[:limit]

    lowered = name.lower()
    ci = [
        n
        for n in store.nodes
        if n.name.lower() == lowered and kind in (None, n.kind)
    ]
    if ci:
        return _ordered(ci)[:limit]

    if any(ch in name for ch in "*?["):
        globbed = [
            n
            for n in store.nodes
            if kind in (None, n.kind) and fnmatch.fnmatch(n.name, name)
        ]
        return _ordered(globbed)[:limit]

    substring = [
        n
        for n in store.nodes
        if kind in (None, n.kind)
        and n.kind not in ("file", "module")
        and lowered in n.name.lower()
    ]
    return _ordered(substring)[:limit]


def defines(store: GraphStore, file: str) -> list[Node]:
    """What this file exports. Asked before writing a helper that may exist."""
    target = file.replace("\\", "/").lstrip("./")
    nodes = store.by_file.get(target)
    if nodes is None:
        matches = [f for f in store.by_file if f.endswith("/" + target) or f == target]
        if len(matches) != 1:
            matches = [f for f in store.by_file if fnmatch.fnmatch(f, target)]
        nodes = [n for f in matches for n in store.by_file[f]]
    return _ordered([n for n in nodes if n.kind not in ("file",)])


def dependents(store: GraphStore, name: str, depth: int = 1) -> list[Node]:
    """Everything that breaks if this changes.

    Depth 1 is the direct callers and importers. Deeper walks the transitive
    closure, which is what makes a task's file set complete rather than
    optimistic — and what `overlap` uses.
    """
    seeds = {n.id for n in where(store, name)}
    if not seeds:
        return []
    return _reverse_closure(store, seeds, depth)


def dependent_files(store: GraphStore, files: list[str], depth: int = 1) -> set[str]:
    """The blast radius of a set of files, as a set of files.

    The closure runs file to file rather than node to node. One file's import may
    land on another's module node while a second lands on its file node, and at
    the level this question is asked — can these two tasks run at once — those are
    the same thing.
    """
    normalised = {f.replace("\\", "/").lstrip("./") for f in files}
    incoming: dict[str, set[str]] = {}
    for edge in store.edges:
        if edge.relation not in ("references", "imports", "exposes"):
            continue
        src = store.by_id.get(edge.src)
        dst = store.by_id.get(edge.dst)
        if src is None or dst is None or src.file == dst.file:
            continue
        incoming.setdefault(dst.file, set()).add(src.file)

    out = set(normalised)
    frontier = set(normalised)
    for _ in range(max(1, depth)):
        nxt = {f for target in frontier for f in incoming.get(target, ()) if f not in out}
        if not nxt:
            break
        out |= nxt
        frontier = nxt
    return out


def references(store: GraphStore, name: str) -> list[Node]:
    """Who calls or imports this. The other direction from `defines`."""
    return dependents(store, name, depth=1)


@dataclass
class Overlap:
    overlapping: set[str]
    a_radius: set[str]
    b_radius: set[str]

    @property
    def safe(self) -> bool:
        return not self.overlapping


def overlap(store: GraphStore, a: list[str], b: list[str], depth: int = 1) -> Overlap:
    """Do these two file sets intersect, dependents included.

    This is what makes parallel execution provably safe instead of hopefully
    safe. A task that cites a whole file inflates its radius and quietly collapses
    a phase to serial execution, which is why `edify check` complains about one.
    """
    ra = dependent_files(store, a, depth)
    rb = dependent_files(store, b, depth)
    return Overlap(overlapping=ra & rb, a_radius=ra, b_radius=rb)


def resolve_ref(store: GraphStore, ref: str) -> Node | None:
    """`path/to/file.ts:22-38` or `path/to/file.ts` → the file node, if it exists."""
    path = ref.split(":", 1)[0].replace("\\", "/").lstrip("./")
    for node in store.by_file.get(path, []):
        if node.kind == "file":
            return node
    return None


def line_range_for(store: GraphStore, file: str, name: str) -> tuple[int, int] | None:
    """The line range of a named symbol in a file — what `check --fix` writes.

    The end is the line before the next symbol in the same file, which is exact
    enough to open the right code and never wrong in a way that hides something.
    """
    target = file.replace("\\", "/").lstrip("./")
    in_file = sorted(
        (n for n in store.by_file.get(target, []) if n.kind in ("symbol", "route", "table")),
        key=lambda n: n.line,
    )
    for i, node in enumerate(in_file):
        if node.name == name or node.name.rsplit(".", 1)[-1] == name:
            end = in_file[i + 1].line - 1 if i + 1 < len(in_file) else node.line + 40
            return node.line, max(node.line, end)
    return None


# ---------------------------------------------------------------------------


def _reverse_closure(store: GraphStore, seeds: set[str], depth: int) -> list[Node]:
    incoming: dict[str, set[str]] = {}
    for edge in store.edges:
        if edge.relation in ("references", "imports", "exposes"):
            incoming.setdefault(edge.dst, set()).add(edge.src)

    # An import may land on a file node or on its module node depending on the
    # language. They are the same place, so the walk treats them as one.
    for nodes in store.by_file.values():
        pair = [n.id for n in nodes if n.kind in ("file", "module")]
        for node_id in pair:
            for sibling in pair:
                if sibling != node_id:
                    incoming.setdefault(node_id, set()).update(incoming.get(sibling, set()))

    seen: set[str] = set()
    frontier = set(seeds)
    for _ in range(max(1, depth)):
        nxt: set[str] = set()
        for node_id in frontier:
            for src in incoming.get(node_id, ()):
                if src not in seen and src not in seeds:
                    seen.add(src)
                    nxt.add(src)
        if not nxt:
            break
        frontier = nxt

    return _ordered([store.by_id[i] for i in seen if i in store.by_id])


def _ordered(nodes: list[Node]) -> list[Node]:
    rank = {"symbol": 0, "route": 1, "table": 2, "module": 3, "package": 4, "doc-section": 5, "file": 6}
    unique = {n.id: n for n in nodes}
    return sorted(unique.values(), key=lambda n: (rank.get(n.kind, 9), n.file, n.line, n.name))
