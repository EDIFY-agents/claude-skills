"""`edify license`: status, activate and deactivate, with no purchase and no price."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from edify.cli import main


def run(repo: Path, *args: str) -> int:
    return main(["--repo", str(repo), *args])


def run_json(capsys: pytest.CaptureFixture[str], repo: Path, *args: str):
    code = main(["--repo", str(repo), "--json", *args])
    out = capsys.readouterr().out
    return code, json.loads(out) if out.strip() else None


def test_free_status_names_activate_and_no_price(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    assert run(tmp_path, "license", "status") == 0
    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert "$" not in text
    assert "edify license activate" in text


def test_license_projects_is_gone(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        run(tmp_path, "license", "projects")
    assert exc.value.code == 2


def test_status_json_still_carries_the_retired_caps_as_null(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    code, data = run_json(capsys, tmp_path, "license", "status")
    assert code == 0
    assert data["node_cap"] is None
    assert data["project_cap"] is None


def _keypair(monkeypatch: pytest.MonkeyPatch) -> bytes:
    import binascii
    import secrets

    from edify.licensing import ed25519, revocation

    seed = secrets.token_bytes(32)
    monkeypatch.setenv("EDIFY_LICENSE_PUBKEY", binascii.hexlify(ed25519.public_key(seed)).decode())
    monkeypatch.setattr(revocation, "_registered", [])
    return seed


def test_status_shows_the_client_admins_licence_id_and_binding(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from edify.licensing import tier
    from edify.licensing.token import issue, parse

    seed = _keypair(monkeypatch)
    value = issue({"sub": "acme", "client": "Acme", "plan": "team", "seats": 10,
                   "admins": ["ana", "bo"], "bind": "a" * 40, "iat": 0, "exp": 0}, seed)
    tier.save(value)
    code, data = run_json(capsys, tmp_path, "license", "status")
    assert code == 0
    assert data["license"]["client"] == "Acme"
    assert data["license"]["admins"] == ["ana", "bo"]
    assert data["license"]["id"] == parse(value).license.id
    assert data["binding"]["matches"] is False
    assert data["revocations"]["count"] == 0

    assert run(tmp_path, "license", "status") == 0
    text = capsys.readouterr().out
    assert "ana, bo" in text and parse(value).license.id in text


def test_activate_refuses_a_revoked_licence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from edify.licensing import revocation, tier
    from edify.licensing.token import issue, parse

    seed = _keypair(monkeypatch)
    value = issue({"sub": "leaked", "plan": "team", "iat": 0, "exp": 0}, seed)
    listing = tmp_path / "revoked.tsv"
    listing.write_text(revocation.write({parse(value).license.id}, seed), encoding="utf-8")
    monkeypatch.setattr(revocation, "EMBEDDED", listing)

    code = run(tmp_path, "license", "activate", value)
    assert code != 0
    assert not tier.license_path().exists()


def test_activate_takes_a_team_token_pasted_on_the_command_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A team token is longer than a filename may be (255 bytes on Linux). Checking
    whether it names a file raised `OSError` instead of answering no, so the very
    command the licence email gives crashed."""
    from edify.licensing import tier
    from edify.licensing.token import issue

    seed = _keypair(monkeypatch)
    value = issue({"sub": "acme", "client": "Acme Inc", "email": "lead@acme.dev", "plan": "team",
                   "seats": 10, "admins": ["ana", "bo"], "bind": "a" * 40, "iat": 0, "exp": 0}, seed)
    assert len(value) > 255
    assert run(tmp_path, "license", "activate", value) == 0
    assert tier.license_path().read_text(encoding="utf-8").strip() == value

    # Not a token and too long to be a path: refused as a token, never a crash.
    assert run(tmp_path, "license", "activate", "x" * 400) != 0
