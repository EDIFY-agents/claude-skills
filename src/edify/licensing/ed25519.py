"""Ed25519, in pure Python over the standard library.

RFC 8032, the reference construction. It is here for one reason: a licence has to
verify with no network and no third-party package, on an air-gapped build server,
because everything else in this product works offline and a licence check that
phones home would be the one thing that does not.

Verification is what the CLI uses. Signing is included because the issuer is part
of this repository (`tools/issue_license.py`) and a signer nobody can run is a
signer nobody can test. Neither is fast, and neither needs to be: one signature
verification per command invocation is roughly a millisecond.
"""

from __future__ import annotations

import hashlib

# Curve25519 in Edwards form, as specified.
_P = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)

_By = 4 * pow(5, _P - 2, _P) % _P
_Bx = 0  # filled in below


def _x_recover(y: int) -> int:
    xx = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P)
    x = pow(xx, (_P + 3) // 8, _P)
    if (x * x - xx) % _P != 0:
        x = (x * _I) % _P
    if x % 2 != 0:
        x = _P - x
    return x


_Bx = _x_recover(_By)
_B = (_Bx % _P, _By % _P, 1, (_Bx * _By) % _P)


def _edwards_add(p: tuple[int, int, int, int], q: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x1, y1, z1, t1 = p
    x2, y2, z2, t2 = q
    a = (y1 - x1) * (y2 - x2) % _P
    b = (y1 + x1) * (y2 + x2) % _P
    c = t1 * 2 * _D * t2 % _P
    dd = z1 * 2 * z2 % _P
    e, f, g, h = b - a, dd - c, dd + c, b + a
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _edwards_double(p: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    return _edwards_add(p, p)


def _scalar_mult(p: tuple[int, int, int, int], e: int) -> tuple[int, int, int, int]:
    q = (0, 1, 1, 0)
    while e > 0:
        if e & 1:
            q = _edwards_add(q, p)
        p = _edwards_double(p)
        e >>= 1
    return q


def _compress(p: tuple[int, int, int, int]) -> bytes:
    x, y, z, _ = p
    zinv = pow(z, _P - 2, _P)
    x = x * zinv % _P
    y = y * zinv % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decompress(data: bytes) -> tuple[int, int, int, int] | None:
    if len(data) != 32:
        return None
    value = int.from_bytes(data, "little")
    sign = value >> 255
    y = value & ((1 << 255) - 1)
    if y >= _P:
        return None
    x = _x_recover(y)
    if x & 1 != sign:
        x = _P - x
    point = (x, y, 1, x * y % _P)
    if not _on_curve(point):
        return None
    return point


def _on_curve(p: tuple[int, int, int, int]) -> bool:
    x, y, z, t = p
    return (
        (-x * x + y * y - z * z - _D * t * t) % _P == 0
        and (x * y) % _P == (z * t) % _P
    )


def _sha512_int(data: bytes) -> int:
    return int.from_bytes(hashlib.sha512(data).digest(), "little")


def public_key(seed: bytes) -> bytes:
    """The 32-byte public key for a 32-byte private seed."""
    if len(seed) != 32:
        raise ValueError("an ed25519 seed is 32 bytes")
    h = hashlib.sha512(seed).digest()
    a = _clamp(h[:32])
    return _compress(_scalar_mult(_B, a))


def sign(message: bytes, seed: bytes) -> bytes:
    if len(seed) != 32:
        raise ValueError("an ed25519 seed is 32 bytes")
    h = hashlib.sha512(seed).digest()
    a = _clamp(h[:32])
    prefix = h[32:]
    pub = _compress(_scalar_mult(_B, a))
    r = _sha512_int(prefix + message) % _L
    big_r = _compress(_scalar_mult(_B, r))
    k = _sha512_int(big_r + pub + message) % _L
    s = (r + k * a) % _L
    return big_r + int.to_bytes(s, 32, "little")


def verify(message: bytes, signature: bytes, pub: bytes) -> bool:
    """True only for a signature this public key actually produced.

    Every failure path returns False rather than raising, so a malformed licence
    is treated exactly like an absent one: the free plan, stated plainly.
    """
    if len(signature) != 64 or len(pub) != 32:
        return False
    big_r_bytes, s_bytes = signature[:32], signature[32:]
    s = int.from_bytes(s_bytes, "little")
    if s >= _L:
        return False
    big_r = _decompress(big_r_bytes)
    point_a = _decompress(pub)
    if big_r is None or point_a is None:
        return False
    k = _sha512_int(big_r_bytes + pub + message) % _L
    left = _scalar_mult(_B, s)
    right = _edwards_add(big_r, _scalar_mult(point_a, k))
    return _compress(left) == _compress(right)


def _clamp(data: bytes) -> int:
    a = bytearray(data)
    a[0] &= 248
    a[31] &= 127
    a[31] |= 64
    return int.from_bytes(bytes(a), "little")
