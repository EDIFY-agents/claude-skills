"""The graph: determinism, coverage, and the four queries.

Determinism is the property everything else rests on. If a rebuild over unchanged
source is not byte-identical, a graph diff stops being a structural diff and "did
this change?" stops being a comparison.
"""

from __future__ import annotations

from pathlib import Path

from edify.graph import extract, queries
from edify.graph.store import GraphStore
from edify.paths import Layout


def build(repo: Path) -> tuple[Layout, GraphStore]:
    layout = Layout(repo)
    layout.edify.mkdir(parents=True, exist_ok=True)
    extract.build(layout)
    return layout, GraphStore(layout)


def test_rebuild_is_byte_identical(repo: Path) -> None:
    layout, _ = build(repo)
    first_nodes = layout.nodes.read_bytes()
    first_edges = layout.edges.read_bytes()

    extract.build(layout)
    assert layout.nodes.read_bytes() == first_nodes
    assert layout.edges.read_bytes() == first_edges


def test_meta_records_checksums_and_no_timestamp(repo: Path) -> None:
    layout, store = build(repo)
    meta = store.meta
    assert meta["nodes_sha256"] and meta["edges_sha256"]
    assert store.verify_checksums() == []
    # A timestamp in meta would make every rebuild differ, which is exactly the
    # property the format exists to have.
    assert not any(key in meta for key in ("generated", "timestamp", "built_at"))


def test_python_is_parsed_exactly(repo: Path) -> None:
    _, store = build(repo)
    hits = queries.where(store, "Retrier")
    assert [n.kind for n in hits] == ["symbol"]
    assert hits[0].file == "src/tools.py"

    methods = {n.name for n in queries.defines(store, "src/tools.py")}
    assert "Retrier.run" in methods
    assert "MAX_RETRIES" in methods
    assert "with_retry" in methods


def test_typescript_exports_and_routes(repo: Path) -> None:
    _, store = build(repo)
    assert queries.where(store, "generate")[0].file == "src/auth/tokens.ts"
    assert {n.name for n in queries.defines(store, "src/api/members.ts")} >= {
        "MemberService",
        "ROLES",
    }
    routes = {n.name for n in store.nodes if n.kind == "route"}
    assert routes == {"GET /members", "POST /members"}


def test_sql_tables_and_migration_edges(repo: Path) -> None:
    _, store = build(repo)
    tables = [n for n in store.nodes if n.kind == "table"]
    assert [n.name for n in tables] == ["members"]
    migrates = [e for e in store.edges if e.relation == "migrates"]
    assert len(migrates) == 1


def test_dependents_follows_a_named_import(repo: Path) -> None:
    _, store = build(repo)
    dependents = {n.file for n in queries.dependents(store, "generate")}
    assert "src/api/members.ts" in dependents


def test_overlap_is_depth_aware(repo: Path) -> None:
    _, store = build(repo)
    # tokens → members → router. Adjacent at depth 2, not at depth 1.
    shallow = queries.overlap(store, ["src/auth/tokens.ts"], ["src/api/router.ts"], depth=1)
    deep = queries.overlap(store, ["src/auth/tokens.ts"], ["src/api/router.ts"], depth=2)
    assert shallow.safe
    assert not deep.safe
    assert "src/api/router.ts" in deep.overlapping


def test_unrelated_files_never_overlap(repo: Path) -> None:
    _, store = build(repo)
    result = queries.overlap(store, ["src/tools.py"], ["src/api/router.ts"], depth=3)
    assert result.safe


def test_uncovered_language_gets_no_nodes_and_says_so(repo: Path) -> None:
    (repo / "src" / "thing.zig").write_text("pub fn main() void {}\n", encoding="utf-8")
    layout = Layout(repo)
    layout.edify.mkdir(parents=True, exist_ok=True)
    extract.build(layout)
    store = GraphStore(layout)

    # The file is on the map; nothing was invented about its contents.
    assert any(n.file == "src/thing.zig" and n.kind == "file" for n in store.nodes)
    assert not any(n.file == "src/thing.zig" and n.kind == "symbol" for n in store.nodes)


def test_node_cap_truncates_and_records_it(repo: Path) -> None:
    layout = Layout(repo)
    layout.edify.mkdir(parents=True, exist_ok=True)
    result = extract.build(layout, node_cap=5)
    assert result.truncated_at == 5
    assert result.nodes <= 5
    assert GraphStore(layout).meta["truncated_at"] == "5"


def test_directory_update_keeps_the_rest(repo: Path) -> None:
    layout, store = build(repo)
    before = {n.id for n in store.nodes}

    (repo / "src" / "api" / "invites.ts").write_text(
        "export function newInvite(): string {\n  return 'x';\n}\n", encoding="utf-8"
    )
    extract.build(layout, subdirs=["src/api"])

    after = GraphStore(layout)
    names = {n.name for n in after.nodes}
    assert "newInvite" in names
    # Nothing outside src/api was disturbed.
    assert {n.id for n in after.nodes if n.file.startswith("src/auth/")} == {
        i for i in before if i.endswith("generate") or "src/auth/" in i
    } & {n.id for n in after.nodes if n.file.startswith("src/auth/")}
    assert any(n.file == "src/tools.py" for n in after.nodes)


def test_ignored_directories_are_not_walked(repo: Path) -> None:
    vendored = repo / "node_modules" / "left-pad"
    vendored.mkdir(parents=True)
    (vendored / "index.js").write_text("export function leftPad() {}\n", encoding="utf-8")

    _, store = build(repo)
    assert not any("node_modules" in n.file for n in store.nodes)
