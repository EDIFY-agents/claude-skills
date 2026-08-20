"""`edify mcp` — the registry, and what a spawn in a given position would load.

`for` exists so the scoping is inspectable rather than implicit. "Why did this task
have the browser loaded?" should be one command, not an investigation.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from ..context import Context
from ..formats import mcp as mcp_format
from ..licensing import tier


def list_(ctx: Context) -> int:
    ctx.layout.require_installed()
    registry = mcp_format.parse(ctx.layout.mcp)
    if not registry.servers:
        ctx.out.line("the registry is empty — everything works with it empty")
        return 0

    cap = ctx.entitlement.mcp_cap
    ctx.out.data(
        [
            {
                "server": s.name,
                "version": s.version,
                "provides": s.provides,
                "roles": s.roles,
                "phases": s.phases,
                "network": s.network,
                "source": s.source,
            }
            for s in registry.servers
        ]
    )
    ctx.out.table(
        ["server", "version", "roles", "phases", "network", "provides"],
        [
            [s.name, s.version, " ".join(s.roles) or "—", " ".join(s.phases) or "—", s.network, s.provides[:48]]
            for s in registry.servers
        ],
    )
    if cap is not None and len(registry.servers) > cap:
        ctx.out.warn(
            f"{len(registry.servers)} servers declared; the free plan covers {cap}."
            " Entries beyond the first are listed but not scoped into spawns."
        )
        ctx.out.note(tier.upsell())
    return 0


def for_(ctx: Context) -> int:
    ctx.layout.require_installed()
    registry = mcp_format.parse(ctx.layout.mcp)
    servers = registry.for_spawn(ctx.args.role, ctx.args.phase)

    cap = ctx.entitlement.mcp_cap
    if cap is not None:
        allowed = {s.name for s in registry.servers[:cap]}
        withheld = [s for s in servers if s.name not in allowed]
        servers = [s for s in servers if s.name in allowed]
        for server in withheld:
            ctx.out.warn(f"`{server.name}` is beyond the free plan's registry limit and was not loaded")

    ctx.out.data([{"server": s.name, "version": s.version, "network": s.network} for s in servers])
    if not servers:
        ctx.out.line("none")
        return 0
    for server in servers:
        ctx.out.line(f"{server.name}@{server.version}\t{server.network}")
    return 0


def check(ctx: Context) -> int:
    """Each server responds and its version matches the pin — where that is knowable.

    A server we cannot probe is reported as unprobeable rather than as passing.
    An unreachable `outbound` server on an air-gapped network is absent and says
    so; a silent fallback to recollection is the failure this exists to prevent.
    """
    ctx.layout.require_installed()
    registry = mcp_format.parse(ctx.layout.mcp)
    configured = _configured_servers(ctx.layout.root)

    rows = []
    results = []
    worst = 0
    for server in registry.servers:
        state, detail = _probe(server, configured)
        rows.append([server.name, server.version, state, detail])
        results.append({"server": server.name, "state": state, "detail": detail})
        if state == "missing":
            worst = max(worst, 1)

    for problem in mcp_format.validate(registry):
        ctx.out.warn(f"{ctx.layout.rel(ctx.layout.mcp)}:{problem[2]}: {problem[1]}")

    ctx.out.data(results)
    ctx.out.table(["server", "pinned", "state", "detail"], rows)
    return worst


# ---------------------------------------------------------------------------


def _configured_servers(root: Path) -> dict[str, dict]:
    """What the host runtime is actually configured to launch, if it says so."""
    for candidate in (root / ".mcp.json", root / "mcp.json", root / ".claude" / "mcp.json"):
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            servers = data.get("mcpServers") or data.get("servers") or {}
            if isinstance(servers, dict):
                return servers
    return {}


def _probe(server: mcp_format.Server, configured: dict[str, dict]) -> tuple[str, str]:
    entry = configured.get(server.name)
    if entry is None:
        if not configured:
            return "unprobeable", "no host mcp configuration found in this repository"
        return "missing", "declared in the registry, not configured for the host runtime"

    command = entry.get("command")
    if not command:
        return "configured", "remote transport — the pin cannot be checked from here"
    if not shutil.which(str(command)):
        return "missing", f"`{command}` is not on PATH"

    try:
        out = subprocess.run(
            [str(command), "--version"], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return "configured", "does not answer --version; the pin cannot be checked"
    text = (out.stdout + out.stderr).strip().splitlines()
    reported = text[0] if text else ""
    if server.version and server.version in reported:
        return "ok", reported[:60]
    return "drifted", f"reports `{reported[:40]}`, registry pins `{server.version}`"
