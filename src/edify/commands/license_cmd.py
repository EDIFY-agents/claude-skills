"""`edify license` — what this machine is entitled to, and how to change it.

`status` says which plan this machine is on and what a licence would add;
`activate` installs a signed token; `deactivate` removes it. There is no purchase
and no price: the public edition is every command, uncapped, and a team or
partner licence is issued on request.

Offline throughout. Activation writes a signed token to a file; nothing is sent
anywhere, and no command in this CLI opens a socket to check a plan.
"""

from __future__ import annotations

import time
from pathlib import Path

from ..context import Context
from ..distribution import CONTACT
from ..errors import EdifyError
from ..licensing import revocation, tier
from ..licensing.binding import root_commits
from ..licensing.token import License, parse
from ..ui import MARKS


def status(ctx: Context) -> int:
    ent = ctx.entitlement
    data = ent.as_dict()
    binding = _binding(ctx, ent.license) if ent.license else None
    data["binding"] = binding
    data["revocations"] = revocation.load().as_dict()
    ctx.out.data(data)

    ctx.out.field("plan", ent.plan)
    if ent.license:
        lic = ent.license
        who = lic.client or lic.email or lic.subject or "unnamed"
        ctx.out.field("licensed", f"{who} · {lic.seats} seat(s)")
        if lic.admins:
            ctx.out.field("admins", ", ".join(lic.admins))
        ctx.out.field("licence id", f"{lic.id} · key {lic.key}")
        if lic.expires_at:
            when = time.strftime("%Y-%m-%d", time.gmtime(lic.expires_at))
            ctx.out.field("expires", f"{when} ({lic.days_left} days)")
        if binding:
            ctx.out.field("bound to", f"{lic.bind[:12]} · {binding['detail']}")
    if ent.problem:
        ctx.out.warn(f"a licence was found and not accepted: {ent.problem}")
    if ent.warning:
        ctx.out.warn(ent.warning)
    ctx.out.field("source", str(ent.source))
    ctx.out.line("")

    ctx.out.line(ctx.out.c("entitlements", "muted"))
    for feature, description in sorted(tier.FEATURE_NAMES.items()):
        allowed = ent.allows(feature)
        if ctx.out.fancy:
            # At a terminal, the site's state device: enforced, or not covered.
            mark = ctx.out.c(MARKS["pass"], "signal") if allowed else ctx.out.c(MARKS["uncovered"], "faint")
        else:
            mark = "[yes]" if allowed else "[no ]"
        ctx.out.line(f"  {mark} {feature:<19} {ctx.out.c(description, 'dim')}")
    ctx.out.line("")
    ctx.out.field("registry", 'unlimited' if ent.mcp_cap is None else f'{ent.mcp_cap} server')
    if not ent.paid:
        ctx.out.line("")
        ctx.out.line("public edition — every command, uncapped, no account")
        ctx.out.line(f"team edition  edify license activate <token>  ·  ask for one: {CONTACT}")
    return 0


def activate(ctx: Context) -> int:
    token = _token_or_file(ctx.args.token.strip())

    verdict = parse(token)
    if not verdict.valid or verdict.license is None:
        raise EdifyError(f"not activated — {verdict.reason}")

    lic = verdict.license
    if lic.id in revocation.revoked_ids():
        raise EdifyError(f"not activated — licence {lic.id} was revoked")

    path = tier.save(token)
    ctx.out.data({"path": str(path), "license": lic.as_dict()})
    ctx.out.ok(f"{lic.plan} plan activated for {lic.client or lic.email or lic.subject or 'this machine'}")
    ctx.out.line(str(path))
    if lic.plan in tier.RETIRED_PLANS:
        ctx.out.warn(f"the {lic.plan} plan is retired — this machine runs the public edition; ask for a new token")
    binding = _binding(ctx, lic)
    if binding and not binding["matches"]:
        ctx.out.warn(f"this licence is bound to another repository ({binding['detail']})")
    return 0


def _token_or_file(value: str) -> str:
    """The token itself, or the contents of the file it names.

    A token is checked for first: a team token is longer than a path component may
    be, and asking the filesystem about it raises rather than answering no.
    """
    if value.startswith("edify1."):
        return value
    try:
        path = Path(value).expanduser()
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return value


def _binding(ctx: Context, lic: License) -> dict[str, object] | None:
    """Whether a bound licence matches the repository this command runs in."""
    if not lic.bind:
        return None
    roots, problem = root_commits(ctx.layout.root)
    if problem:
        return {"bind": lic.bind, "matches": False, "detail": problem}
    matches = lic.bound_to(roots)
    detail = "this repository" if matches else f"this repository's root is {roots[0][:12]}"
    return {"bind": lic.bind, "matches": matches, "detail": detail}


def deactivate(ctx: Context) -> int:
    removed = tier.clear()
    ctx.out.data({"removed": removed})
    ctx.out.line("licence removed" if removed else "no licence file to remove")
    return 0
