"""`.edify/mcp.md` — the server registry, pinned and scoped per role × phase.

One table, seven columns, and the two that carry the design are `roles` and
`phases`. A connected server injects its tool descriptions into every session
whether or not they are used; scoping per spawn is what stops eight servers across
a forty-task build becoming a tax paid three hundred and twenty times.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .document import parse_document
from .skill import ROLES

COLUMNS = ("server", "version", "provides", "roles", "phases", "network", "source")
NETWORKS = ("outbound", "internal", "local")


@dataclass
class Server:
    name: str
    version: str
    provides: str
    roles: list[str]
    phases: list[str]
    network: str
    source: str
    line: int

    def scoped_to(self, role: str, phase: str) -> bool:
        """Exact-match lookup. A model never decides which servers load."""
        if "any" not in self.roles and role not in self.roles:
            return False
        if "any" not in self.phases and str(phase) not in self.phases:
            return False
        return True


@dataclass
class Registry:
    path: Path
    servers: list[Server] = field(default_factory=list)

    def for_spawn(self, role: str, phase: str) -> list[Server]:
        return [s for s in self.servers if s.scoped_to(role, phase)]

    def get(self, name: str) -> Server | None:
        for server in self.servers:
            if server.name == name:
                return server
        return None


def parse(path: Path) -> Registry:
    registry = Registry(path=path)
    if not path.is_file():
        return registry
    doc = parse_document(path)
    for table in doc.tables:
        cols = {name: table.column(name) for name in COLUMNS}
        if cols["server"] < 0:
            continue
        for row in table.rows:
            name = row.get(cols["server"]).strip("`")
            if not name or set(name) <= {"-", "—", " "}:
                continue
            registry.servers.append(
                Server(
                    name=name,
                    version=row.get(cols["version"]) if cols["version"] >= 0 else "",
                    provides=row.get(cols["provides"]) if cols["provides"] >= 0 else "",
                    roles=_tokens(row.get(cols["roles"])) if cols["roles"] >= 0 else [],
                    phases=_tokens(row.get(cols["phases"])) if cols["phases"] >= 0 else [],
                    network=row.get(cols["network"]).lower() if cols["network"] >= 0 else "",
                    source=row.get(cols["source"]) if cols["source"] >= 0 else "",
                    line=row.line,
                )
            )
    return registry


def validate(registry: Registry) -> list[tuple[str, str, int]]:
    problems: list[tuple[str, str, int]] = []
    seen: set[str] = set()
    for server in registry.servers:
        if server.name in seen:
            problems.append(("mcp-duplicate", f"`{server.name}` is declared twice", server.line))
        seen.add(server.name)
        if not server.version or server.version in ("-", "—", "latest", "*"):
            problems.append(
                (
                    "mcp-unpinned",
                    f"`{server.name}` has no exact version — `edify doctor` cannot check the pin",
                    server.line,
                )
            )
        if server.network and server.network not in NETWORKS:
            problems.append(
                ("mcp-bad-network", f"`network: {server.network}` is not one of {'|'.join(NETWORKS)}", server.line)
            )
        for role in server.roles:
            if role not in ROLES and role != "any":
                problems.append(("mcp-bad-role", f"`{server.name}` is scoped to unknown role `{role}`", server.line))
        for phase in server.phases:
            if phase != "any" and not (phase.isdigit() and 0 <= int(phase) <= 7):
                problems.append(("mcp-bad-phase", f"`{server.name}` is scoped to unknown phase `{phase}`", server.line))
        if not server.roles and not server.phases:
            problems.append(
                (
                    "mcp-unscoped",
                    f"`{server.name}` is scoped to nothing, so it would load nowhere — say `any` if that is meant",
                    server.line,
                )
            )
    return problems


def _tokens(value: str) -> list[str]:
    out: list[str] = []
    for token in value.replace(",", " ").split():
        token = token.strip().strip("`*")
        if token and token not in ("-", "—"):
            out.append(token.lower())
    return out
