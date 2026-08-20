"""SQL: tables, and the migrations that create them.

Tables are first-class nodes because a task that touches one needs to find it, and
because a migration file is the one place a schema decision is written down. A file
under a migrations directory emits a `migrates` edge to every table it names, which
is what makes "which migration created this table" a query rather than a grep.
"""

from __future__ import annotations

import re

from ..model import Edge, Extraction, Node, fingerprint, node_id

_CREATE_TABLE = re.compile(
    r"create\s+(?:or\s+replace\s+)?(?:unlogged\s+|temp(?:orary)?\s+)?table\s+"
    r"(?:if\s+not\s+exists\s+)?[`\"\[]?(?P<name>[A-Za-z_][A-Za-z0-9_.]*)[`\"\]]?",
    re.IGNORECASE,
)
_ALTER_TABLE = re.compile(
    r"alter\s+table\s+(?:if\s+exists\s+)?[`\"\[]?(?P<name>[A-Za-z_][A-Za-z0-9_.]*)[`\"\]]?",
    re.IGNORECASE,
)
_DROP_TABLE = re.compile(
    r"drop\s+table\s+(?:if\s+exists\s+)?[`\"\[]?(?P<name>[A-Za-z_][A-Za-z0-9_.]*)[`\"\]]?",
    re.IGNORECASE,
)
_CREATE_INDEX = re.compile(
    r"create\s+(?:unique\s+)?index\s+(?:concurrently\s+)?(?:if\s+not\s+exists\s+)?"
    r"[`\"\[]?(?P<name>[A-Za-z_][A-Za-z0-9_.]*)[`\"\]]?",
    re.IGNORECASE,
)
_VIEW = re.compile(
    r"create\s+(?:or\s+replace\s+)?(?:materialized\s+)?view\s+"
    r"(?:if\s+not\s+exists\s+)?[`\"\[]?(?P<name>[A-Za-z_][A-Za-z0-9_.]*)[`\"\]]?",
    re.IGNORECASE,
)

_MIGRATION_DIRS = ("migrations/", "migrate/", "db/migrate/", "alembic/versions/", "sql/migrations/")


def extract(rel_path: str, source: str) -> Extraction:
    out = Extraction(languages={"sql"})
    file_id = node_id("file", rel_path, ".")
    is_migration = any(part in rel_path.lower() for part in _MIGRATION_DIRS)

    for lineno, raw in enumerate(source.splitlines(), start=1):
        line = raw.split("--", 1)[0]
        if not line.strip():
            continue

        for pattern, kind in ((_CREATE_TABLE, "table"), (_VIEW, "table")):
            m = pattern.search(line)
            if m:
                _emit_table(out, m.group("name"), rel_path, lineno, line, file_id, defines=True)

        for pattern in (_ALTER_TABLE, _DROP_TABLE):
            m = pattern.search(line)
            if m:
                _emit_table(out, m.group("name"), rel_path, lineno, line, file_id, defines=False)

        m = _CREATE_INDEX.search(line)
        if m:
            name = m.group("name")
            sym_id = node_id("symbol", rel_path, name)
            out.nodes.append(
                Node(sym_id, "symbol", rel_path, lineno, name, fingerprint(line.strip()))
            )
            out.edges.append(Edge(file_id, "defines", sym_id))

    if is_migration:
        for node in list(out.nodes):
            if node.kind == "table":
                out.edges.append(Edge(file_id, "migrates", node.id))
    return out


def _emit_table(
    out: Extraction, name: str, rel_path: str, lineno: int, line: str, file_id: str, defines: bool
) -> None:
    table_id = node_id("table", rel_path, name)
    if defines:
        out.nodes.append(Node(table_id, "table", rel_path, lineno, name, fingerprint(line.strip())))
        out.edges.append(Edge(file_id, "defines", table_id))
    else:
        out.pending_refs.append((file_id, name, "references"))
