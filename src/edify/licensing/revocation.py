"""Revoked licences: a signed list of licence IDs, shipped with a release.

A token is valid until it expires, and nothing is fetched to ask whether it still
should be. So a leaked or withdrawn licence is stopped the only offline way there
is: the next release carries its ID, signed with the licence key, and `tier`
treats a revoked licence as no licence (REQ-54).

The list holds licence IDs and nothing else — no client names and no emails —
because it ships in the public wheel. It is written by the private issuer
(`revocations sign`), never by hand. An absent list is an empty one. A list whose
signature does not verify is ignored and reported, never trusted, since a list
can only ever take entitlements away.

    # comment lines
    edify-revoked<TAB>1<TAB>kid=0<TAB>issued=2026-10-02
    0123456789abcdef
    ...
    signature<TAB><base64url Ed25519 over every byte above this line>

The team edition adds its own list with `register()`.
"""

from __future__ import annotations

import base64
import binascii
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from .ed25519 import verify
from .token import override_keys, shipped_key

HEADER = "edify-revoked"
VERSION = "1"

#: The list this release ships. Absent until the first revocation.
EMBEDDED = Path(__file__).with_name("revoked.tsv")

_ID = re.compile(r"^[0-9a-f]{16}$")
_registered: list[Path] = []


@dataclass
class RevocationList:
    ids: frozenset[str] = frozenset()
    sources: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {"count": len(self.ids), "sources": self.sources, "problems": self.problems}


def register(path: Path) -> None:
    """Add a signed list to the ones consulted. For the team edition's own list."""
    if path not in _registered:
        _registered.append(path)


def load() -> RevocationList:
    """Every verified list, merged. Read per call: the files are a few hundred bytes."""
    ids: set[str] = set()
    sources: list[str] = []
    problems: list[str] = []
    for path in [EMBEDDED, *_registered]:
        if not path.is_file():
            continue
        found, problem = read(path.read_text(encoding="utf-8"))
        if problem:
            problems.append(f"{path.name}: {problem}")
            continue
        ids |= found
        sources.append(str(path))
    return RevocationList(frozenset(ids), sources, problems)


def revoked_ids() -> frozenset[str]:
    return load().ids


def read(text: str) -> tuple[frozenset[str], str]:
    """The IDs a signed list carries, or why the list is not trusted."""
    text = text.replace("\r\n", "\n")
    marker = text.rfind("\nsignature\t")
    if marker < 0:
        return frozenset(), "unsigned"
    body = text[: marker + 1]
    sig_line = text[marker + 1 :].strip()
    try:
        signature = _b64decode(sig_line.split("\t", 1)[1].strip())
    except (IndexError, binascii.Error, ValueError):
        return frozenset(), "the signature is not base64url"

    lines = [ln for ln in body.splitlines() if ln.strip() and not ln.startswith("#")]
    if not lines:
        return frozenset(), "no header"
    head = lines[0].split("\t")
    if head[0] != HEADER or len(head) < 2 or head[1] != VERSION:
        return frozenset(), f"not a version {VERSION} revocation list"
    kid = 0
    for part in head[2:]:
        if part.startswith("kid="):
            try:
                kid = int(part[4:])
            except ValueError:
                return frozenset(), "the key id is not a number"

    payload = body.encode("utf-8")
    keys = [k for k in [shipped_key(kid), *override_keys()] if k]
    if not any(verify(payload, signature, k) for k in keys):
        return frozenset(), "the signature does not verify"

    ids = {ln.split("\t", 1)[0].strip().lower() for ln in lines[1:]}
    bad = sorted(i for i in ids if not _ID.match(i))
    if bad:
        return frozenset(), f"not a licence ID: {bad[0]}"
    return frozenset(ids), ""


def write(ids: set[str] | frozenset[str], seed: bytes, kid: int = 0, now: int | None = None) -> str:
    """Sign a list. Used by the private issuer and by the tests."""
    from .ed25519 import sign

    clean = sorted({i.strip().lower() for i in ids})
    bad = [i for i in clean if not _ID.match(i)]
    if bad:
        raise ValueError(f"not a licence ID: {bad[0]}")
    day = time.strftime("%Y-%m-%d", time.gmtime(now if now is not None else time.time()))
    body = (
        "# edify revocation list — licence IDs only, signed with the licence key.\n"
        "# Written by the private issuer (`revocations sign`). Never edit by hand:\n"
        "# an edited list fails its signature and is ignored.\n"
        f"{HEADER}\t{VERSION}\tkid={kid}\tissued={day}\n"
        + "".join(f"{i}\n" for i in clean)
    )
    signature = sign(body.encode("utf-8"), seed)
    return body + f"signature\t{_b64encode(signature)}\n"


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
