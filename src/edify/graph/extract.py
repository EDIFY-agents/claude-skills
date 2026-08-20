"""The extraction pass: walk, extract, resolve, write.

No model at any point, for any reason — not at install, not as a fallback, not for
a language the extractor does not cover. Where a language is not covered the graph
has no nodes for it and `meta.languages_uncovered` says which.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .. import __version__
from ..errors import EdifyError
from ..paths import Layout
from .ignore import IgnoreRules
from .langs import EXTENSIONS, covered_languages, ctags, extract_file, language_for, method_for
from .model import Edge, Extraction, Node, node_id
from .store import GraphStore


@dataclass
class ExtractResult:
    nodes: int = 0
    edges: int = 0
    files: int = 0
    skipped: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    uncovered: dict[str, int] = field(default_factory=dict)
    backend: str = "builtin"
    truncated_at: int | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "files": self.files,
            "skipped": self.skipped,
            "languages": self.languages,
            "uncovered": self.uncovered,
            "backend": self.backend,
            "truncated_at": self.truncated_at,
        }


def build(
    layout: Layout,
    backend: str = "builtin",
    node_cap: int | None = None,
    subdirs: list[str] | None = None,
) -> ExtractResult:
    """Full extraction, or a directory-scoped update when `subdirs` is given."""
    root = layout.root
    if not root.is_dir():
        raise EdifyError(f"{root} is not a directory")

    rules = IgnoreRules(root)
    scan_roots = _scan_roots(root, subdirs)
    files = _walk(root, scan_roots, rules)

    result = ExtractResult(backend=backend)
    result.files = len(files)

    extraction = Extraction()
    if backend == "ctags":
        if ctags.available() is None:
            raise EdifyError(
                "no Universal Ctags on PATH",
                hint="install it, or run without `--extractor ctags` to use the built-in backend",
            )
        extraction.extend(ctags.extract_tree(root, files))
        result.backend = "ctags"

    for rel in files:
        path = root / rel
        language = language_for(path)
        file_node = Node(node_id("file", rel, "."), "file", rel, 1, rel)
        extraction.nodes.append(file_node)

        if language is None:
            continue
        if method_for(language) == "none":
            result.uncovered[language] = result.uncovered.get(language, 0) + 1
            continue
        if backend == "ctags" and language != "markdown":
            # The external extractor already covered code. Markdown sections and
            # SQL tables are ours either way — it does not emit them.
            if language != "sql":
                result.languages[language] = result.languages.get(language, 0) + 1
                continue

        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            result.skipped += 1
            continue

        extraction.extend(extract_file(rel, source, language))
        result.languages[language] = result.languages.get(language, 0) + 1

    _resolve_packages(root, extraction)
    edges = _resolve_refs(extraction)

    nodes = extraction.nodes
    if node_cap is not None and len(nodes) > node_cap:
        result.truncated_at = node_cap
        keep = {n.id for n in _prioritise(nodes)[:node_cap]}
        nodes = [n for n in nodes if n.id in keep]
        edges = [e for e in edges if e.src in keep and e.dst in keep]

    store = GraphStore(layout)
    if subdirs:
        nodes, edges = _merge_with_existing(store, nodes, edges, scan_roots, root)

    meta = _meta(root, result, extraction)
    written = store.write(nodes, edges, meta)
    result.nodes = int(written["nodes"])
    result.edges = int(written["edges"])
    return result


# ---------------------------------------------------------------------------
# the walk
# ---------------------------------------------------------------------------


def _scan_roots(root: Path, subdirs: list[str] | None) -> list[Path]:
    if not subdirs:
        return [root]
    out: list[Path] = []
    for raw in subdirs:
        candidate = (root / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            raise EdifyError(f"{raw} is outside the repository at {root}") from None
        if not candidate.is_dir():
            raise EdifyError(f"{raw} is not a directory")
        out.append(candidate)
    return out


def _walk(root: Path, scan_roots: list[Path], rules: IgnoreRules) -> list[str]:
    """Repository-relative POSIX paths, sorted. Sorted because determinism."""
    found: set[str] = set()
    for start in scan_roots:
        for dirpath, dirnames, filenames in os.walk(start):
            here = Path(dirpath)
            rel_dir = here.relative_to(root).as_posix()
            dirnames[:] = sorted(
                d
                for d in dirnames
                if not rules.skip_dir(d, f"{rel_dir}/{d}".lstrip("./") if rel_dir != "." else d)
            )
            for name in filenames:
                rel = (here / name).relative_to(root).as_posix()
                try:
                    size = (here / name).stat().st_size
                except OSError:
                    continue
                if rules.skip_file(name, rel, size):
                    continue
                found.add(rel)
    return sorted(found)


# ---------------------------------------------------------------------------
# resolution
# ---------------------------------------------------------------------------


def _resolve_refs(extraction: Extraction) -> list[Edge]:
    """Turn pending name references into edges, or drop them.

    A reference that does not resolve inside the repository is an external one,
    and external things are not in this graph. Dropping is the correct outcome —
    inventing a node for `express` would be narration.
    """
    by_name: dict[str, list[str]] = {}
    by_module_path: dict[str, str] = {}
    for node in extraction.nodes:
        by_name.setdefault(node.name, []).append(node.id)
        tail = node.name.rsplit(".", 1)[-1]
        if tail != node.name:
            by_name.setdefault(tail, []).append(node.id)
        if node.kind == "module":
            by_module_path[_module_key(node.file)] = node.id

    # A relative import (`../auth/tokens`) resolves against the importing file's
    # directory, which this pass does not carry. Matching on the path's tail
    # resolves it when exactly one module ends that way, and declines when more
    # than one does — an ambiguous edge is a coin toss, not a fact.
    by_suffix: dict[str, list[str]] = {}
    for key, node_ref in by_module_path.items():
        parts = key.split("/")
        for i in range(len(parts)):
            by_suffix.setdefault("/".join(parts[i:]), []).append(node_ref)

    edges = list(extraction.edges)
    for src, target, relation in extraction.pending_refs:
        resolved = _lookup(target, by_name, by_module_path, by_suffix)
        if not resolved:
            continue
        for dst in resolved:
            if dst != src:
                edges.append(Edge(src, relation, dst))
    return edges


def _lookup(
    target: str,
    by_name: dict[str, list[str]],
    by_module_path: dict[str, str],
    by_suffix: dict[str, list[str]],
) -> list[str]:
    # A path-like import: './auth/session', 'src/auth/session', 'app.auth.session'
    cleaned = target.strip().lstrip("./").replace("\\", "/")
    for candidate in (cleaned, cleaned.replace(".", "/")):
        key = _module_key(candidate)
        if key in by_module_path:
            return [by_module_path[key]]
        suffixed = by_suffix.get(key, [])
        if len(suffixed) == 1:
            return suffixed
    # A bare name: resolve only when it is unambiguous. Two symbols with the same
    # name in different files is not an edge, it is a coin toss.
    hits = by_name.get(target) or by_name.get(target.rsplit(".", 1)[-1]) or []
    return hits if len(hits) == 1 else []


def _module_key(path: str) -> str:
    key = path.strip().strip("/")
    for suffix in (
        ".py", ".pyi", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs",
        ".java", ".kt", ".rb", ".php", ".cs", ".swift",
    ):
        if key.endswith(suffix):
            key = key[: -len(suffix)]
            break
    if key.endswith("/index"):
        key = key[: -len("/index")]
    if key.endswith("/__init__"):
        key = key[: -len("/__init__")]
    if key.endswith("/mod"):
        key = key[: -len("/mod")]
    return key


def _resolve_packages(root: Path, extraction: Extraction) -> None:
    """Declared dependencies become `package` nodes.

    Read from manifests only — never from an import statement, because an import
    of something that is not declared is a fact about the code, not a package.
    """
    from ..detect import declared_packages

    for name, manifest in declared_packages(root).items():
        pkg_id = node_id("package", manifest, name)
        extraction.nodes.append(Node(pkg_id, "package", manifest, 1, name))


def _prioritise(nodes: list[Node]) -> list[Node]:
    """Ordering used only when a node cap truncates the graph.

    Keep the public surface first: the map is worth more with every exported
    symbol and half the file nodes than the other way round.
    """
    rank = {"symbol": 0, "route": 1, "table": 2, "module": 3, "package": 4, "file": 5, "doc-section": 6}
    return sorted(nodes, key=lambda n: (rank.get(n.kind, 9), n.file, n.line, n.name))


def _merge_with_existing(
    store: GraphStore, nodes: list[Node], edges: list[Edge], scan_roots: list[Path], root: Path
) -> tuple[list[Node], list[Edge]]:
    """A directory update replaces that directory's nodes and keeps the rest."""
    if not store.exists():
        return nodes, edges
    prefixes = tuple(
        (r.relative_to(root).as_posix().rstrip("/") + "/") if r != root else "" for r in scan_roots
    )
    if "" in prefixes:
        return nodes, edges

    kept_nodes = [n for n in store.nodes if not n.file.startswith(prefixes)]
    kept_ids = {n.id for n in kept_nodes} | {n.id for n in nodes}
    kept_edges = [
        e for e in store.edges if e.src in kept_ids and e.dst in kept_ids and _outside(e, store, prefixes)
    ]
    return kept_nodes + nodes, kept_edges + edges


def _outside(edge: Edge, store: GraphStore, prefixes: tuple[str, ...]) -> bool:
    src = store.by_id.get(edge.src)
    return not (src and src.file.startswith(prefixes))


# ---------------------------------------------------------------------------
# meta
# ---------------------------------------------------------------------------


def _meta(root: Path, result: ExtractResult, extraction: Extraction) -> dict[str, str]:
    covered = sorted(result.languages)
    meta = {
        "commit": _head_commit(root),
        "extractor": result.backend,
        "extractor_version": ctags.version() if result.backend == "ctags" else f"edify {__version__}",
        "languages_covered": " ".join(covered) or "-",
        "languages_uncovered": " ".join(sorted(result.uncovered)) or "-",
        "files_scanned": str(result.files),
    }
    for language in covered:
        meta[f"method_{language}"] = (
            "external" if result.backend == "ctags" and language not in ("markdown", "sql")
            else method_for(language)
        )
    if result.truncated_at is not None:
        meta["truncated_at"] = str(result.truncated_at)
    return meta


def _head_commit(root: Path) -> str:
    """The commit the graph was built from, or `-` where there is no git.

    `-` is honest and the freshness check reads it as "cannot tell". A fabricated
    value here would make a stale graph look current, which is the failure mode
    this field exists to prevent.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "-"
    value = out.stdout.strip()
    return value if out.returncode == 0 and value else "-"


def known_extensions() -> list[str]:
    return sorted(EXTENSIONS)


def known_languages() -> list[str]:
    return covered_languages()
