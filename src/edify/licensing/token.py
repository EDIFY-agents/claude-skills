"""The licence token: a signed claim, verified locally.

Shape: `edify1.<base64url(payload json)>.<base64url(signature)>`. The signature is
Ed25519 over the payload bytes. There is no network call, no activation server,
and no machine fingerprint — the token is a receipt, not a lock.

That is a deliberate position and `docs/pricing.md` states it: the source
is readable, the check is local, and anyone determined can remove it. Paying is a
contract, and pretending otherwise would cost real users offline operation for no
protection.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import time
from dataclasses import dataclass, field

from .ed25519 import verify

PREFIX = "edify1"

# The production issuing key. The private half never leaves the issuer (see
# `docs/pricing.md` §3, D-7). It is a random 32-byte seed held in a
# secrets store — *not* a derivable one. The public key of an all-zeros seed,
# `3b6a27bc…59da29`, shipped in 0.1.0 and let anyone mint a `pro` token; the
# regression test in `tests/test_licensing.py` makes its return impossible.
DEFAULT_PUBLIC_KEY_HEX = "ceada7ea65d2959574910cd0c0fb1f5fd862d1da504deb4b27562361c4133ef5"


@dataclass
class License:
    subject: str = ""
    email: str = ""
    plan: str = "free"
    seats: int = 1
    issued_at: int = 0
    expires_at: int = 0
    features: list[str] = field(default_factory=list)
    raw: str = ""

    @property
    def expired(self) -> bool:
        return bool(self.expires_at) and time.time() > self.expires_at

    @property
    def days_left(self) -> int:
        if not self.expires_at:
            return -1
        return max(0, int((self.expires_at - time.time()) // 86400))

    def as_dict(self) -> dict[str, object]:
        return {
            "subject": self.subject,
            "email": self.email,
            "plan": self.plan,
            "seats": self.seats,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "expired": self.expired,
            "days_left": self.days_left,
            "features": self.features,
        }


@dataclass
class Verdict:
    license: License | None
    reason: str = ""

    @property
    def valid(self) -> bool:
        return self.license is not None


def public_key() -> bytes:
    """The verifying key.

    `EDIFY_LICENSE_PUBKEY` overrides it so a self-hosted or enterprise issuer can
    sign its own tokens. That is a supported deployment, documented, and it is the
    same reason the gate is a contract rather than a protection measure.
    """
    raw = os.environ.get("EDIFY_LICENSE_PUBKEY", DEFAULT_PUBLIC_KEY_HEX).strip()
    try:
        key = binascii.unhexlify(raw)
    except (binascii.Error, ValueError):
        return b""
    return key if len(key) == 32 else b""


def parse(token: str) -> Verdict:
    """Verify a token and return the licence it carries, or why it does not."""
    token = token.strip()
    if not token:
        return Verdict(None, "no token")
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != PREFIX:
        return Verdict(None, "not an edify licence token")

    try:
        payload_bytes = _b64decode(parts[1])
        signature = _b64decode(parts[2])
    except (binascii.Error, ValueError):
        return Verdict(None, "the token is not valid base64url")

    key = public_key()
    if not key:
        return Verdict(None, "no usable verifying key")
    if not verify(payload_bytes, signature, key):
        return Verdict(None, "the signature does not match the issuing key")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return Verdict(None, "the payload is not JSON")

    lic = License(
        subject=str(payload.get("sub", "")),
        email=str(payload.get("email", "")),
        plan=str(payload.get("plan", "free")).lower(),
        seats=int(payload.get("seats", 1) or 1),
        issued_at=int(payload.get("iat", 0) or 0),
        expires_at=int(payload.get("exp", 0) or 0),
        features=[str(f) for f in (payload.get("features") or [])],
        raw=token,
    )
    if lic.expired:
        return Verdict(None, f"the licence expired on {time.strftime('%Y-%m-%d', time.gmtime(lic.expires_at))}")
    return Verdict(lic)


def issue(payload: dict[str, object], seed: bytes) -> str:
    """Sign a payload. Used by the issuer, and by the tests that prove this works."""
    from .ed25519 import sign

    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = sign(body, seed)
    return f"{PREFIX}.{_b64encode(body)}.{_b64encode(signature)}"


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)
