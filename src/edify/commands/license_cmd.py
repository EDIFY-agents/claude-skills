"""`edify license` — what this machine is entitled to, and how to change it.

Offline throughout. Activation writes a signed token to a file; nothing is sent
anywhere, and no command in this CLI opens a socket to check a plan.

`buy` is the one apparent exception and is not one: it opens a **browser**, it does
not open a socket. Under `--json`, `--quiet`, or with no terminal it prints the URL
instead, so a pipeline gets a string rather than a surprise window (plan D-8).

`projects` and `projects forget` are the fifth gate's front door. Releasing a slot
must not require a support ticket, and seeing what is using them must not require
knowing where the ledger lives.
"""

from __future__ import annotations

import time
import webbrowser
from pathlib import Path

from ..context import Context
from ..errors import EdifyError
from ..licensing import projects as projects_mod
from ..licensing import tier
from ..licensing.token import parse


def status(ctx: Context) -> int:
    ent = ctx.entitlement
    ctx.out.data(ent.as_dict())

    ctx.out.line(f"plan      {ent.plan}")
    if ent.license:
        lic = ent.license
        ctx.out.line(f"licensed  {lic.email or lic.subject or 'unnamed'} · {lic.seats} seat(s)")
        if lic.expires_at:
            when = time.strftime("%Y-%m-%d", time.gmtime(lic.expires_at))
            ctx.out.line(f"expires   {when} ({lic.days_left} days)")
    if ent.problem:
        ctx.out.warn(f"a licence was found and not accepted: {ent.problem}")
    ctx.out.line(f"source    {ent.source}")
    ctx.out.line("")

    ctx.out.line("entitlements")
    for feature, description in sorted(tier.FEATURE_NAMES.items()):
        mark = "yes" if ent.allows(feature) else "no "
        ctx.out.line(f"  [{mark}] {feature:<19} {description}")
    ctx.out.line("")
    cap = ent.node_cap
    ctx.out.line(f"graph cap     {'unlimited' if cap is None else f'{cap:,} nodes'}")
    mcap = ent.mcp_cap
    ctx.out.line(f"registry cap  {'unlimited' if mcap is None else f'{mcap} server'}")
    pcap = ent.project_cap
    used = len(projects_mod.known())
    ctx.out.line(
        f"project cap   {'unlimited' if pcap is None else f'{pcap} projects'}"
        f"   ({used} installed · `edify license projects`)"
    )
    if not ent.paid:
        ctx.out.line("")
        ctx.out.line("Everything else is free, forever, with no account:")
        ctx.out.line("  every command, every query, every check, the whole methodology tree.")
        ctx.out.line("")
        # The second of exactly two places the price appears without a gate having
        # been hit. Somebody who typed `license status` is asking.
        ctx.out.line(f"pro           {tier.PRO_PRICE} · `edify license buy`")
    return 0


def activate(ctx: Context) -> int:
    token = ctx.args.token.strip()
    if Path(token).expanduser().is_file():
        token = Path(token).expanduser().read_text(encoding="utf-8").strip()

    verdict = parse(token)
    if not verdict.valid or verdict.license is None:
        raise EdifyError(f"not activated — {verdict.reason}")

    path = tier.save(token)
    lic = verdict.license
    ctx.out.data({"path": str(path), "license": lic.as_dict()})
    ctx.out.ok(f"{lic.plan} plan activated for {lic.email or lic.subject or 'this machine'}")
    ctx.out.line(str(path))
    return 0


def deactivate(ctx: Context) -> int:
    removed = tier.clear()
    ctx.out.data({"removed": removed})
    ctx.out.line("licence removed" if removed else "no licence file to remove")
    return 0


def buy(ctx: Context) -> int:
    """Open the Payment Link, or print it when there is nobody to open it for.

    It opens a browser; it does not open a socket. `edify` still reaches the
    network in exactly two commands, and this is not one of them.
    """
    seats = max(1, int(getattr(ctx.args, "seats", 1) or 1))
    url = tier.buy_url(seats)
    ctx.out.data({"plan": "pro", "price": tier.PRO_PRICE, "seats": seats, "url": url})

    ctx.out.line(f"pro       {tier.PRO_PRICE}")
    ctx.out.line(f"seats     {seats}")
    ctx.out.line("")
    ctx.out.line("what it lifts")
    for feature in sorted(tier.ENTITLEMENTS["pro"]):
        ctx.out.line(f"  {feature:<20} {tier.FEATURE_NAMES.get(feature, feature)}")
    ctx.out.line("")
    ctx.out.line(url)

    if not ctx.out.interactive:
        # A pipeline, a CI job, or a model's tool call. A browser window nobody
        # asked for is worse than a URL, so this prints one and stops.
        return 0
    opened = False
    try:
        opened = bool(webbrowser.open(url))
    except Exception:  # noqa: BLE001 — no browser is not a failure of this command
        opened = False
    if opened:
        ctx.out.note("opened in your browser")
    else:
        ctx.out.note("no browser could be opened — the link above is the whole of it")
    ctx.out.note("the token arrives by email; activate it with `edify license activate <token>`")
    return 0


def projects(ctx: Context) -> int:
    """Which repositories are using a slot, and which rows are already stale."""
    rows = projects_mod.all_rows()
    live = [r for r in rows if r.exists]
    cap = ctx.entitlement.project_cap

    ctx.out.data(
        {
            "cap": cap,
            "used": len(live),
            "ledger": str(projects_mod.ledger_path()),
            "projects": [r.as_dict() for r in rows],
        }
    )

    if not rows:
        ctx.out.line("no projects yet — the first `edify setup` records one")
        return 0

    ctx.out.table(
        ["project", "keyed on", "first seen", "state"],
        [
            [
                r.path,
                "remote" if r.by_remote else "path",
                time.strftime("%Y-%m-%d", time.gmtime(r.first_seen)) if r.first_seen else "-",
                "ok" if r.exists else "gone (its slot is already free)",
            ]
            for r in sorted(rows, key=lambda r: r.first_seen)
        ],
    )
    ctx.out.line("")
    ctx.out.line(
        f"using    {len(live)} of {'unlimited' if cap is None else cap}"
        f"   ledger: {projects_mod.ledger_path()}"
    )
    if cap is not None and len(live) >= cap:
        ctx.out.line("")
        ctx.out.line(f"a {tier.ordinal(cap + 1)} project is {tier.PRO_PRICE}"
                     " — `edify license buy`")
        ctx.out.line("release one with `edify license projects forget <path>`")
    return 0


def projects_forget(ctx: Context) -> int:
    """Release one slot. Never a support ticket."""
    removed = projects_mod.forget(ctx.args.which)
    ctx.out.data({"removed": removed.as_dict() if removed else None})
    if removed is None:
        raise EdifyError(
            f"nothing in the ledger matches `{ctx.args.which}`",
            hint="`edify license projects` lists what is there, by path",
        )
    ctx.out.ok(f"released {removed.path}")
    ctx.out.note("installing there again takes the slot back")
    return 0
