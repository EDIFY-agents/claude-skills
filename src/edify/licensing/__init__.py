"""Offline licensing: a signed receipt, verified locally, with no phone-home.

Everything in EDIFY works with no network. A licence check is not going to be the
one exception, so the token carries its own proof and the verification is a
signature check against an embedded public key.
"""

from . import projects
from .tier import (
    BUY_URL,
    FREE_PROJECT_CAP,
    PRO_PRICE,
    Entitlement,
    buy_url,
    clear,
    current,
    license_path,
    save,
)
from .token import License, issue, parse

__all__ = [
    "BUY_URL",
    "Entitlement",
    "FREE_PROJECT_CAP",
    "License",
    "PRO_PRICE",
    "buy_url",
    "clear",
    "current",
    "issue",
    "license_path",
    "parse",
    "projects",
    "save",
]
