"""The licence token: a signed claim, verified locally.

Shape: `edify1.<base64url(payload json)>.<base64url(signature)>`. The signature is
Ed25519 over the payload bytes. There is no network call, no activation server,
and no machine fingerprint — the token is a receipt, not a lock.

The payload's keys: `sub email plan seats iat exp features`, and, for team and
partner licences, `client admins bind kid`. Every key is optional, and unknown keys
are ignored, so a token issued by any version keeps parsing in every later one.
The licence ID is not a key: it is derived from the signed bytes (`licence_id`).

That is a deliberate position: the source is readable, the check is local, and
anyone determined can remove it. A licence is a contract, and pretending otherwise
would cost real users offline operation for no protection.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import time
from dataclasses import dataclass, field

from .ed25519 import verify

PREFIX = "edify1"

# The production issuing key. The private half never leaves the issuer, which
# signs by hand and is not shipped. It is a random 32-byte seed held in a
# secrets store — *not* a derivable one. The public key of an all-zeros seed,
# `3b6a27bc…59da29`, shipped in 0.1.0 and let anyone mint a `pro` token; the
# regression test in `tests/test_licensing.py` makes its return impossible.
DEFAULT_PUBLIC_KEY_HEX = "ceada7ea65d2959574910cd0c0fb1f5fd862d1da504deb4b27562361c4133ef5"

#: Every licence key this release trusts, indexed by `kid`. A token with no `kid`
#: is key 0. A rotated key is appended here and ships alongside the old one; the
#: old one is dropped only after the last token signed with it has expired.
PUBLIC_KEYS: tuple[str, ...] = (DEFAULT_PUBLIC_KEY_HEX,)

#: Larger than any honest token by two orders of magnitude.
MAX_TOKEN_BYTES = 16 * 1024


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
    #: The client the licence is issued to, and the handles allowed to administer it.
    client: str = ""
    admins: list[str] = field(default_factory=list)
    #: A repository root-commit SHA, or empty when the licence is not bound.
    bind: str = ""
    kid: int = 0
    #: The first 16 hex digits of sha256 over the signed payload. Every token has
    #: one, including those issued before the field was named, so a revocation
    #: list can name any of them.
    id: str = ""
    #: Which key verified it: `k<kid>` for a key this release ships, `override`
    #: for one supplied through `EDIFY_LICENSE_PUBKEY`.
    key: str = ""

    @property
    def expired(self) -> bool:
        return bool(self.expires_at) and time.time() > self.expires_at

    @property
    def days_left(self) -> int:
        if not self.expires_at:
            return -1
        return max(0, int((self.expires_at - time.time()) // 86400))

    def bound_to(self, roots: list[str]) -> bool:
        """True when the licence is unbound, or bound to one of these root commits.

        A repository can have several roots (merged histories); any one matching is
        enough. Either side may be abbreviated, as git abbreviates.
        """
        if not self.bind:
            return True
        return any(r and (r.lower().startswith(self.bind) or self.bind.startswith(r.lower())) for r in roots)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "subject": self.subject,
            "client": self.client,
            "email": self.email,
            "plan": self.plan,
            "seats": self.seats,
            "admins": self.admins,
            "bind": self.bind,
            "kid": self.kid,
            "key": self.key,
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


def override_keys() -> list[bytes]:
    """Keys from `EDIFY_LICENSE_PUBKEY`, comma-separated.

    They are tried *in addition to* the shipped keys, never instead of them, so
    setting the variable cannot make a genuine licence stop verifying. A licence
    verified this way says so (`key: override`).
    """
    raw = os.environ.get("EDIFY_LICENSE_PUBKEY", "").strip()
    return [k for k in (_unhex(part) for part in raw.split(",")) if k] if raw else []


def shipped_key(kid: int) -> bytes:
    """The shipped key with this id, or empty when this release does not carry it."""
    if 0 <= kid < len(PUBLIC_KEYS):
        return _unhex(PUBLIC_KEYS[kid])
    return b""


def licence_id(payload_bytes: bytes) -> str:
    return hashlib.sha256(payload_bytes).hexdigest()[:16]


def _unhex(raw: str) -> bytes:
    try:
        key = binascii.unhexlify(raw.strip())
    except (binascii.Error, ValueError):
        return b""
    return key if len(key) == 32 else b""


def parse(token: str) -> Verdict:
    """Verify a token and return the licence it carries, or why it does not."""
    token = token.strip()
    if not token:
        return Verdict(None, "no token")
    if len(token) > MAX_TOKEN_BYTES:
        return Verdict(None, "the token is too long to be an edify licence")
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != PREFIX:
        return Verdict(None, "not an edify licence token")

    try:
        payload_bytes = _b64decode(parts[1])
        signature = _b64decode(parts[2])
    except (binascii.Error, ValueError):
        return Verdict(None, "the token is not valid base64url")

    # The kid is read before the signature is checked only to pick the key; the
    # payload is trusted for nothing else until the signature verifies.
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = None
    kid = payload.get("kid", 0) if isinstance(payload, dict) else 0
    kid = kid if isinstance(kid, int) and not isinstance(kid, bool) else -1

    key_name = ""
    shipped = shipped_key(kid)
    if shipped and verify(payload_bytes, signature, shipped):
        key_name = f"k{kid}"
    elif any(verify(payload_bytes, signature, k) for k in override_keys()):
        key_name = "override"
    if not key_name:
        if kid >= len(PUBLIC_KEYS) and not override_keys():
            return Verdict(None, f"the token was signed with key {kid}, which this release does not carry — upgrade edify")
        return Verdict(None, "the signature does not match the issuing key")

    if not isinstance(payload, dict):
        return Verdict(None, "the payload is not a JSON object")
    try:
        lic = _license(payload, token)
    except (TypeError, ValueError) as exc:
        return Verdict(None, f"the payload is malformed ({exc})")
    lic.id = licence_id(payload_bytes)
    lic.key = key_name
    if lic.expired:
        return Verdict(None, f"the licence expired on {time.strftime('%Y-%m-%d', time.gmtime(lic.expires_at))}")
    return Verdict(lic)


def _license(payload: dict[str, object], token: str) -> License:
    def text_list(name: str) -> list[str]:
        value = payload.get(name) or []
        if not isinstance(value, list):
            raise ValueError(f"`{name}` is not a list")
        return [str(v) for v in value]

    seats = int(payload.get("seats", 1) or 1)  # type: ignore[arg-type]
    if seats < 1:
        raise ValueError("`seats` is below 1")
    kid = payload.get("kid", 0) or 0
    return License(
        subject=str(payload.get("sub", "")),
        email=str(payload.get("email", "")),
        plan=str(payload.get("plan", "free")).lower(),
        seats=seats,
        issued_at=int(payload.get("iat", 0) or 0),  # type: ignore[arg-type]
        expires_at=int(payload.get("exp", 0) or 0),  # type: ignore[arg-type]
        features=text_list("features"),
        raw=token,
        client=str(payload.get("client", "") or ""),
        admins=text_list("admins"),
        bind=str(payload.get("bind", "") or "").lower(),
        kid=int(kid),  # type: ignore[arg-type]
    )


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
