"""Plans, entitlements, and the five places a limit is enforced.

The free plan is a whole working system on a small repository. The paid plan is
what the actual buyer needs, and the split is drawn along the same line the product
vision draws: EDIFY's value starts where the codebase stops fitting in a context
window, so the free ceiling sits just under that.

Five gates, and they are the only five (`docs/pricing.md` §2):

    graph.unlimited     a graph larger than the free node ceiling
    library.upgrade     pulling new curated skill entries with `edify upgrade`
    mcp.multi           more than one server in the registry
    projects.unlimited  installing into more than the free project ceiling
    team                more than one seat on one licence

`projects.unlimited` is the newest and the only one about how *much* rather than
how *big*. It is enforced at install time only, in one place — `init_cmd.run`,
through which `setup` and `init new` also route — and its ledger is a readable
file on this machine that nothing ever sends anywhere. `licensing/projects.py`
holds it and says why.

Everything else — every query, every check, every command, `--json`, `--exit-code`,
the whole methodology tree — is free, forever, with no account.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ..errors import TierRequired
from ..paths import user_config_dir
from .token import License, Verdict, parse

FREE_NODE_CAP = 25_000
FREE_MCP_ENTRIES = 1
#: How many repositories the free plan installs into. Q-7 in
#: `docs/pricing.md` records that this number moves on evidence from the
#: first fifty installs rather than on a guess made now — which is why it is one
#: constant and not a number typed into four gate messages.
FREE_PROJECT_CAP = 3

#: The price, written once. A price typed in four places is a price that drifts,
#: and the one that gets missed is always the one a stranger reads first.
PRO_PRICE = "$20 per user per month"

#: Where a person goes to pay. `EDIFY_BUY_URL` overrides it, which is how Stripe
#: test mode is reached without shipping a test link (plan D-8).
BUY_URL = "https://buy.stripe.com/edify-pro"

PLANS = ("free", "pro", "team", "enterprise")

# plan → the entitlements it carries.
_PAID = frozenset({"graph.unlimited", "library.upgrade", "mcp.multi", "projects.unlimited"})

ENTITLEMENTS: dict[str, frozenset[str]] = {
    "free": frozenset(),
    "pro": _PAID,
    "team": _PAID | {"team"},
    "enterprise": _PAID | {"team"},
}

FEATURE_NAMES = {
    "graph.unlimited": f"a graph larger than {FREE_NODE_CAP:,} nodes",
    "library.upgrade": "`edify upgrade`",
    "mcp.multi": f"more than {FREE_MCP_ENTRIES} server in the registry",
    "projects.unlimited": f"more than {FREE_PROJECT_CAP} projects on one machine",
    "team": "more than one seat",
}


@dataclass
class Entitlement:
    """What this machine is allowed to do, and where that came from."""

    plan: str = "free"
    license: License | None = None
    source: str = "none"
    problem: str = ""
    features: frozenset[str] = field(default_factory=frozenset)

    @property
    def paid(self) -> bool:
        return self.plan != "free"

    def allows(self, feature: str) -> bool:
        return feature in self.features

    def require(self, feature: str) -> None:
        if not self.allows(feature):
            raise TierRequired(FEATURE_NAMES.get(feature, feature))

    @property
    def node_cap(self) -> int | None:
        return None if self.allows("graph.unlimited") else FREE_NODE_CAP

    @property
    def mcp_cap(self) -> int | None:
        return None if self.allows("mcp.multi") else FREE_MCP_ENTRIES

    @property
    def project_cap(self) -> int | None:
        return None if self.allows("projects.unlimited") else FREE_PROJECT_CAP

    def as_dict(self) -> dict[str, object]:
        return {
            "plan": self.plan,
            "source": self.source,
            "problem": self.problem,
            "features": sorted(self.features),
            "node_cap": self.node_cap,
            "mcp_cap": self.mcp_cap,
            "project_cap": self.project_cap,
            "license": self.license.as_dict() if self.license else None,
        }


def license_path() -> Path:
    override = os.environ.get("EDIFY_LICENSE_FILE")
    if override:
        return Path(override).expanduser()
    return user_config_dir() / "license"


def current() -> Entitlement:
    """Resolve the entitlement for this invocation.

    Order: the `EDIFY_LICENSE` environment variable, so CI can carry a token
    without writing a file; then the licence file. A token that fails to verify
    falls back to free and says why, because a silent downgrade is worse than a
    stated one.
    """
    token = os.environ.get("EDIFY_LICENSE", "").strip()
    source = "EDIFY_LICENSE"
    if not token:
        path = license_path()
        if path.is_file():
            token = path.read_text(encoding="utf-8").strip()
            source = str(path)
    if not token:
        return Entitlement(plan="free", source="none", features=ENTITLEMENTS["free"])

    verdict: Verdict = parse(token)
    if not verdict.valid or verdict.license is None:
        return Entitlement(
            plan="free", source=source, problem=verdict.reason, features=ENTITLEMENTS["free"]
        )

    lic = verdict.license
    plan = lic.plan if lic.plan in PLANS else "free"
    features = set(ENTITLEMENTS.get(plan, frozenset()))
    # An explicit feature list on the token can only add, never remove — that is
    # how a bespoke enterprise agreement is expressed without a new plan name.
    features |= {f for f in lic.features if f in FEATURE_NAMES}
    return Entitlement(plan=plan, license=lic, source=source, features=frozenset(features))


def save(token: str) -> Path:
    path = license_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token.strip() + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def clear() -> bool:
    path = license_path()
    if path.is_file():
        path.unlink()
        return True
    return False


def buy_url(seats: int = 1) -> str:
    """The Payment Link, with a quantity when more than one seat is wanted.

    `EDIFY_BUY_URL` overrides the constant so Stripe test mode is one variable
    away. Read at call time rather than at import, because the tests set it.
    """
    base = os.environ.get("EDIFY_BUY_URL", "").strip() or BUY_URL
    if seats and seats > 1:
        joiner = "&" if "?" in base else "?"
        return f"{base}{joiner}quantity={seats}"
    return base


def upsell() -> str:
    """The one line printed under a soft cap that warns rather than raises.

    One string, so the graph-truncation warning, the registry-cap warning, and any
    later one cannot each word the price differently. `TierRequired` carries the
    same sentence for the caps that do raise.
    """
    return f"the pro plan lifts this — {PRO_PRICE} · `edify license buy`"


def ordinal(n: int) -> str:
    """`4` -> `fourth`. The gate says "a fourth project", not "project 4"."""
    words = {
        1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
        6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
    }
    return words.get(n, f"{n}th")
