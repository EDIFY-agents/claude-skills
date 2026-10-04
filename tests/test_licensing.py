"""Licensing: the signature, the plans, and the four gates.

The whole path is exercised with a throwaway key pair, so these tests prove that
issuing, verifying, and gating actually work rather than that they are wired up.
"""

from __future__ import annotations

import binascii
import secrets
import time

import pytest

from edify.errors import TierRequired
from edify.licensing import ed25519, tier
from edify.licensing import token as token_mod
from edify.licensing.token import issue, parse


@pytest.fixture
def keypair(monkeypatch: pytest.MonkeyPatch) -> bytes:
    seed = secrets.token_bytes(32)
    public = ed25519.public_key(seed)
    monkeypatch.setenv("EDIFY_LICENSE_PUBKEY", binascii.hexlify(public).decode())
    return seed


def test_sign_and_verify_round_trip() -> None:
    seed = secrets.token_bytes(32)
    public = ed25519.public_key(seed)
    message = b"the graph is never written by a model"
    signature = ed25519.sign(message, seed)
    assert ed25519.verify(message, signature, public)
    assert not ed25519.verify(message + b"!", signature, public)


def test_a_signature_from_another_key_is_rejected() -> None:
    good, bad = secrets.token_bytes(32), secrets.token_bytes(32)
    message = b"payload"
    assert not ed25519.verify(message, ed25519.sign(message, bad), ed25519.public_key(good))


def test_rfc8032_test_vector() -> None:
    """Vector 1 from RFC 8032 §7.1 — proof this is Ed25519 and not something near it."""
    seed = binascii.unhexlify(
        "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
    )
    expected_public = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    assert binascii.hexlify(ed25519.public_key(seed)).decode() == expected_public

    signature = ed25519.sign(b"", seed)
    assert binascii.hexlify(signature).decode() == (
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc6"
        "1e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
    )


def test_a_valid_team_token_carries_its_entitlements(keypair: bytes) -> None:
    token = issue(
        {"sub": "acct_1", "email": "dev@example.com", "plan": "team", "seats": 1,
         "iat": int(time.time()), "exp": int(time.time()) + 86400},
        keypair,
    )
    verdict = parse(token)
    assert verdict.valid
    assert verdict.license.plan == "team"

    tier.save(token)
    ent = tier.current()
    assert ent.plan == "team"
    assert ent.allows("mcp.multi")
    assert ent.mcp_cap is None
    assert ent.node_cap is None


def test_an_expired_token_falls_back_to_free_and_says_why(keypair: bytes) -> None:
    token = issue(
        {"sub": "acct_1", "plan": "team", "iat": 0, "exp": int(time.time()) - 10}, keypair
    )
    tier.save(token)
    ent = tier.current()
    assert ent.plan == "free"
    assert "expired" in ent.problem


def test_a_tampered_token_falls_back_to_free(keypair: bytes) -> None:
    token = issue({"sub": "acct_1", "plan": "team", "iat": 0, "exp": 0}, keypair)
    head, payload, signature = token.split(".")
    forged = f"{head}.{payload[:-2]}AA.{signature}"

    tier.save(forged)
    ent = tier.current()
    assert ent.plan == "free"
    assert ent.problem


def test_no_licence_is_the_free_plan_with_working_limits() -> None:
    ent = tier.current()
    assert ent.plan == "free"
    assert ent.node_cap is None
    assert ent.mcp_cap == tier.FREE_MCP_ENTRIES

    with pytest.raises(TierRequired):
        ent.require("mcp.multi")


def test_the_environment_variable_carries_a_licence_for_ci(
    keypair: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = issue({"sub": "ci", "plan": "team", "seats": 20, "iat": 0, "exp": 0}, keypair)
    monkeypatch.setenv("EDIFY_LICENSE", token)
    ent = tier.current()
    assert ent.plan == "team"
    assert ent.allows("team")
    assert ent.source == "EDIFY_LICENSE"


def test_an_extra_feature_on_a_token_only_adds(keypair: bytes) -> None:
    token = issue(
        {"sub": "x", "plan": "free", "iat": 0, "exp": 0, "features": ["mcp.multi"]},
        keypair,
    )
    tier.save(token)
    ent = tier.current()
    assert ent.plan == "free"
    assert ent.allows("mcp.multi")
    assert not ent.allows("team")


# -- M1 · the shipped issuing key -------------------------------------------
# 0.1.0 shipped `DEFAULT_PUBLIC_KEY_HEX` as the public key of an all-zeros seed,
# which meant anyone could mint a `pro` token with 32 zero bytes. These two tests
# fail if that key — or any key derivable from a trivially-guessable seed — ever
# comes back, whether by a revert, a bad merge, or a placeholder left in.


def _trivial_seeds() -> list[bytes]:
    """Seeds a person would reach for without thinking: all-zeros, all-ones, a
    single repeated byte, and the low counting integers rendered big-endian."""
    seeds = [bytes([b]) * 32 for b in range(256)]
    seeds += [n.to_bytes(32, "big") for n in range(1, 64)]
    return seeds


def test_the_shipped_key_is_not_derivable_from_a_trivial_seed() -> None:
    shipped = binascii.unhexlify(token_mod.DEFAULT_PUBLIC_KEY_HEX)
    assert len(shipped) == 32
    for seed in _trivial_seeds():
        assert ed25519.public_key(seed) != shipped, (
            "the shipped issuing key is derivable from a guessable seed — anyone can "
            "mint a licence. Run the issuer's keygen and commit only the public half."
        )


def test_the_zero_seed_key_that_shipped_in_0_1_0_is_gone() -> None:
    weak = "3b6a27bcceb6a42d62a3a8d02a6f0d73653215771de243a63ac048a18b59da29"
    assert token_mod.DEFAULT_PUBLIC_KEY_HEX != weak
    assert binascii.hexlify(ed25519.public_key(bytes(32))).decode() == weak


def test_a_token_signed_with_the_zero_seed_no_longer_verifies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nothing minted against the old key survives, which is the point of M1."""
    monkeypatch.delenv("EDIFY_LICENSE_PUBKEY", raising=False)
    forged = issue({"sub": "anyone", "plan": "pro", "iat": 0, "exp": 0}, bytes(32))
    verdict = parse(forged)
    assert not verdict.valid
    assert "signature" in verdict.reason


# -- team and partner licences at scale -------------------------------------
# The fields a team licence carries, the licence ID, key rotation and the signed
# revocation list. Every token issued before these existed must keep working.


def _payload_bytes(value: str) -> bytes:
    return token_mod._b64decode(value.split(".")[1])


def test_a_partner_licence_carries_its_client_seats_admins_and_expiry(keypair: bytes) -> None:
    """A-88: seats=25, expiry 2027-09-01 and custom features parse to exactly those."""
    exp = 1819843199  # 2027-09-01T23:59:59Z
    value = issue(
        {"sub": "uoft-lab", "client": "U of T Design Lab", "email": "lab@utoronto.ca",
         "plan": "partner", "seats": 25, "admins": ["ana", "bo"], "iat": 0, "exp": exp,
         "features": ["mcp.multi"]},
        keypair,
    )
    lic = parse(value).license
    assert lic is not None
    assert (lic.plan, lic.seats, lic.expires_at) == ("partner", 25, exp)
    assert lic.client == "U of T Design Lab"
    assert lic.admins == ["ana", "bo"]
    assert lic.bind == ""
    assert lic.as_dict()["admins"] == ["ana", "bo"]


def test_the_licence_id_is_derived_from_the_signed_bytes(keypair: bytes) -> None:
    """No field needed, so a token issued before the ID existed has one too."""
    value = issue({"sub": "old", "plan": "team", "seats": 3, "iat": 0, "exp": 0}, keypair)
    lic = parse(value).license
    assert lic is not None
    assert lic.id == token_mod.licence_id(_payload_bytes(value))
    assert len(lic.id) == 16
    assert lic.id != parse(issue({"sub": "old", "plan": "team", "seats": 4, "iat": 0, "exp": 0}, keypair)).license.id


def test_a_token_names_the_key_that_verified_it(keypair: bytes) -> None:
    lic = parse(issue({"plan": "team", "iat": 0, "exp": 0}, keypair)).license
    assert lic is not None and lic.key == "override" and lic.kid == 0


def test_a_rotated_key_verifies_tokens_that_name_it(monkeypatch: pytest.MonkeyPatch) -> None:
    old, new = secrets.token_bytes(32), secrets.token_bytes(32)
    monkeypatch.delenv("EDIFY_LICENSE_PUBKEY", raising=False)
    monkeypatch.setattr(token_mod, "PUBLIC_KEYS", (
        binascii.hexlify(ed25519.public_key(old)).decode(),
        binascii.hexlify(ed25519.public_key(new)).decode(),
    ))
    before = parse(issue({"plan": "team", "iat": 0, "exp": 0}, old)).license
    after = parse(issue({"plan": "team", "iat": 0, "exp": 0, "kid": 1}, new)).license
    assert before is not None and before.key == "k0"
    assert after is not None and after.key == "k1"
    # A token claiming key 0 but signed by key 1 is not accepted.
    assert not parse(issue({"plan": "team", "iat": 0, "exp": 0}, new)).valid


def test_a_token_from_a_newer_key_says_to_upgrade(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EDIFY_LICENSE_PUBKEY", raising=False)
    verdict = parse(issue({"plan": "team", "iat": 0, "exp": 0, "kid": 7}, secrets.token_bytes(32)))
    assert not verdict.valid
    assert "upgrade" in verdict.reason


def test_the_override_key_adds_to_the_shipped_key_and_never_replaces_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shipped, other = secrets.token_bytes(32), secrets.token_bytes(32)
    monkeypatch.setattr(token_mod, "PUBLIC_KEYS", (binascii.hexlify(ed25519.public_key(shipped)).decode(),))
    monkeypatch.setenv("EDIFY_LICENSE_PUBKEY", binascii.hexlify(ed25519.public_key(other)).decode())
    lic = parse(issue({"plan": "team", "iat": 0, "exp": 0}, shipped)).license
    assert lic is not None and lic.key == "k0"


@pytest.mark.parametrize(
    "payload",
    [
        {"plan": "team", "seats": "many"},
        {"plan": "team", "seats": -3},
        {"plan": "team", "admins": "ana"},
        {"plan": "team", "exp": "soon"},
        {"plan": "team", "kid": "zero"},
    ],
)
def test_a_signed_but_malformed_payload_is_refused_not_crashed(keypair: bytes, payload: dict) -> None:
    verdict = parse(issue(payload, keypair))
    assert not verdict.valid
    assert verdict.reason


def test_a_payload_that_is_not_an_object_is_refused(keypair: bytes) -> None:
    from edify.licensing.ed25519 import sign

    body = b'["team"]'
    value = f"edify1.{token_mod._b64encode(body)}.{token_mod._b64encode(sign(body, keypair))}"
    verdict = parse(value)
    assert not verdict.valid and "object" in verdict.reason


def test_an_oversized_token_is_refused_before_any_work() -> None:
    assert "too long" in parse("edify1." + "A" * 20000 + ".x").reason


def test_binding_matches_the_root_commit_full_or_abbreviated(keypair: bytes) -> None:
    root = "4acd6922cb98f6522450fdd50598a32f8b583b85"
    lic = parse(issue({"plan": "team", "bind": root[:12], "iat": 0, "exp": 0}, keypair)).license
    assert lic is not None
    assert lic.bound_to([root])
    assert lic.bound_to(["0" * 40, root])
    assert not lic.bound_to(["0" * 40])
    assert not lic.bound_to([])
    unbound = parse(issue({"plan": "partner", "iat": 0, "exp": 0}, keypair)).license
    assert unbound is not None and unbound.bound_to([])


def test_the_root_commit_of_a_real_repository(tmp_path) -> None:
    import subprocess

    from edify.licensing.binding import root_commits

    roots, problem = root_commits(tmp_path)
    assert roots == [] and problem
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-q", "--allow-empty", "-m", "root"], check=True)
    roots, problem = root_commits(tmp_path)
    assert problem == "" and len(roots) == 1 and len(roots[0]) == 40


def test_a_licence_ending_within_thirty_days_warns(keypair: bytes) -> None:
    tier.save(issue({"plan": "team", "iat": 0, "exp": int(time.time()) + 10 * 86400}, keypair))
    ent = tier.current()
    assert ent.plan == "team"
    assert "renewal" in ent.warning
    tier.save(issue({"plan": "team", "iat": 0, "exp": int(time.time()) + 90 * 86400}, keypair))
    assert tier.current().warning == ""


# -- the revocation list ----------------------------------------------------


@pytest.fixture
def revocations(tmp_path, monkeypatch: pytest.MonkeyPatch):
    from edify.licensing import revocation

    path = tmp_path / "revoked.tsv"
    monkeypatch.setattr(revocation, "EMBEDDED", path)
    monkeypatch.setattr(revocation, "_registered", [])
    return path


def test_a_revoked_licence_resolves_to_free_and_says_so(keypair: bytes, revocations) -> None:
    from edify.licensing import revocation

    value = issue({"plan": "team", "seats": 5, "iat": 0, "exp": 0}, keypair)
    tier.save(value)
    assert tier.current().plan == "team"

    lid = parse(value).license.id
    revocations.write_text(revocation.write({lid}, keypair), encoding="utf-8")
    ent = tier.current()
    assert ent.plan == "free"
    assert "revoked" in ent.problem and lid in ent.problem
    assert not ent.allows("team")


def test_an_edited_revocation_list_is_ignored_and_reported(keypair: bytes, revocations) -> None:
    from edify.licensing import revocation

    value = issue({"plan": "team", "iat": 0, "exp": 0}, keypair)
    lid = parse(value).license.id
    signed = revocation.write({lid}, keypair)
    revocations.write_text(signed.replace(lid, "0" * 16), encoding="utf-8")
    tier.save(value)
    assert tier.current().plan == "team"
    loaded = revocation.load()
    assert loaded.ids == frozenset()
    assert loaded.problems and "signature" in loaded.problems[0]


def test_an_unsigned_or_absent_list_revokes_nothing(keypair: bytes, revocations) -> None:
    from edify.licensing import revocation

    assert revocation.revoked_ids() == frozenset()
    revocations.write_text("edify-revoked\t1\tkid=0\n0123456789abcdef\n", encoding="utf-8")
    assert revocation.revoked_ids() == frozenset()


def test_the_team_edition_can_register_its_own_list(keypair: bytes, revocations, tmp_path) -> None:
    from edify.licensing import revocation

    value = issue({"plan": "partner", "iat": 0, "exp": 0}, keypair)
    extra = tmp_path / "team-revoked.tsv"
    extra.write_text(revocation.write({parse(value).license.id}, keypair), encoding="utf-8")
    revocation.register(extra)
    tier.save(value)
    assert tier.current().plan == "free"


def test_the_revocation_list_refuses_anything_but_licence_ids(keypair: bytes) -> None:
    from edify.licensing import revocation

    with pytest.raises(ValueError):
        revocation.write({"acme@example.com"}, keypair)
