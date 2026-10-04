"""Plans, entitlements, and the one limit the public edition keeps.

The public edition is the whole working system, on a repository of any size, in as
many repositories as a person likes, with no account. It has no caps except one:
the MCP registry scopes a single server into spawns. Every query, every check,
every command, `--json`, `--exit-code`, `edify upgrade` and the whole methodology
tree are free, forever.

Two licensed plans exist, and both add the same two things:

    mcp.multi   more than one server in the registry
    team        the team edition

`team` licences are issued on request; `partner` licences are issued free and
custom per client. Nothing is sold and no price is written anywhere in this
package.

`pro` and `enterprise` are retired. A token that still names one of them verifies,
and then resolves to the free plan with a stated reason, because a silent
downgrade is worse than a stated one. So does a token whose licence ID is on a
signed revocation list this release carries (`revocation`, REQ-54).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ..distribution import CONTACT
from ..errors import TierRequired
from ..paths import user_config_dir
from . import revocation
from .token import License, Verdict, parse

FREE_MCP_ENTRIES = 1

#: How far ahead `status` and `doctor` warn that a licence is ending (Q-15).
EXPIRY_WARNING_DAYS = 30

PLANS = ("free", "team", "partner")

#: Plans a token may still name but that no longer exist. They resolve to free,
#: and `current()` says why.
RETIRED_PLANS = ("pro", "enterprise")

# plan → the entitlements it carries.
_LICENSED = frozenset({"mcp.multi", "team"})

ENTITLEMENTS: dict[str, frozenset[str]] = {
    "free": frozenset(),
    "team": _LICENSED,
    "partner": _LICENSED,
}

FEATURE_NAMES = {
    "mcp.multi": f"more than {FREE_MCP_ENTRIES} server in the registry",
    "team": "the team edition",
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
        """Not the free plan.

        Nothing is paid for; the name is kept for the team-edition plugin seam.
        """
        return self.plan != "free"

    def allows(self, feature: str) -> bool:
        return feature in self.features

    def require(self, feature: str) -> None:
        if not self.allows(feature):
            raise TierRequired(FEATURE_NAMES.get(feature, feature))

    @property
    def warning(self) -> str:
        """A licence that works today and is ending soon. Empty otherwise."""
        lic = self.license
        if not self.paid or lic is None or not lic.expires_at:
            return ""
        if lic.days_left <= EXPIRY_WARNING_DAYS:
            return f"the licence ends in {lic.days_left} days — ask for a renewal: {CONTACT}"
        return ""

    @property
    def node_cap(self) -> int | None:
        """Always `None`. Kept so that `--json` readers get `null`, never a `KeyError`."""
        return None

    @property
    def mcp_cap(self) -> int | None:
        return None if self.allows("mcp.multi") else FREE_MCP_ENTRIES

    @property
    def project_cap(self) -> int | None:
        """Always `None`. Kept so that `--json` readers get `null`, never a `KeyError`."""
        return None

    def as_dict(self) -> dict[str, object]:
        return {
            "plan": self.plan,
            "source": self.source,
            "problem": self.problem,
            "warning": self.warning,
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
    if lic.id in revocation.revoked_ids():
        return Entitlement(
            plan="free",
            license=lic,
            source=source,
            problem=f"licence {lic.id} was revoked — ask for a new one: {CONTACT}",
            features=ENTITLEMENTS["free"],
        )
    if lic.plan in RETIRED_PLANS:
        return Entitlement(
            plan="free",
            license=lic,
            source=source,
            problem=f"the {lic.plan} plan is retired; team and partner replace it — ask for a new token",
            features=ENTITLEMENTS["free"],
        )
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
