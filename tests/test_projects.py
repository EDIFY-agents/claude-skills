"""The fifth gate: the project ledger, the refusal, and the way back out.

The assertions that matter are the ones about *not* breaking things — a re-clone
is free, CI does not burn a slot every run, a deleted repository returns its slot
on its own, and a repository already installed keeps installing forever. A limit
that fails any of those is a bug report rather than a business model.
"""

from __future__ import annotations

import binascii
import json
import secrets
import subprocess
from pathlib import Path

import pytest

from edify.cli import main
from edify.errors import TierRequired
from edify.licensing import ed25519, projects, tier
from edify.licensing.token import issue


@pytest.fixture
def pro(monkeypatch: pytest.MonkeyPatch) -> None:
    """A real pro licence, signed with a throwaway key, in the environment."""
    seed = secrets.token_bytes(32)
    monkeypatch.setenv("EDIFY_LICENSE_PUBKEY", binascii.hexlify(ed25519.public_key(seed)).decode())
    monkeypatch.setenv(
        "EDIFY_LICENSE",
        issue({"sub": "x", "email": "a@b.c", "plan": "pro", "iat": 0, "exp": 0}, seed),
    )


def _install(path: Path, *extra: str) -> int:
    return main(["setup", str(path), "--no-graph", "--skills", "none", *extra])


# -- the ledger itself ------------------------------------------------------


def test_a_fresh_machine_has_no_projects() -> None:
    assert projects.known() == []


def test_registering_records_a_row(tmp_path: Path) -> None:
    root = tmp_path / "one"
    root.mkdir()
    assert projects.register(root, cap=3) == projects.REGISTERED
    rows = projects.known()
    assert len(rows) == 1
    assert rows[0].path == projects.canonical(root)


def test_registering_the_same_project_twice_is_not_a_second_slot(tmp_path: Path) -> None:
    root = tmp_path / "one"
    root.mkdir()
    projects.register(root, cap=3)
    assert projects.register(root, cap=3) == projects.ALREADY
    assert len(projects.known()) == 1


def test_the_cap_is_reported_rather_than_raised(tmp_path: Path) -> None:
    """`projects` never raises. Whether "over cap" is an error is the caller's call."""
    for i in range(3):
        (tmp_path / f"p{i}").mkdir()
        assert projects.register(tmp_path / f"p{i}", cap=3) == projects.REGISTERED
    (tmp_path / "p3").mkdir()
    assert projects.register(tmp_path / "p3", cap=3) == projects.OVER_CAP


def test_a_paid_plan_has_no_cap_but_is_still_recorded(tmp_path: Path) -> None:
    """So a licence that lapses does not find three arbitrary projects in the ledger."""
    for i in range(8):
        (tmp_path / f"p{i}").mkdir()
        assert projects.register(tmp_path / f"p{i}", cap=None) == projects.REGISTERED
    assert len(projects.known()) == 8


def test_the_ledger_is_readable_text(tmp_path: Path) -> None:
    """D-6: it never leaves this machine, so obfuscating it buys nothing and costs
    the person the ability to see and manage their own limit."""
    root = tmp_path / "one"
    root.mkdir()
    projects.register(root, cap=3)
    text = projects.ledger_path().read_text(encoding="utf-8")
    assert text.startswith("#key\tpath\tfirst_seen")
    # Readable means readable on Windows too: no escaped separators to decode by eye.
    assert projects.canonical(root) in text
    assert "\\\\" not in text


def test_a_deleted_repository_returns_its_slot(tmp_path: Path) -> None:
    """No command to run, no support ticket — `known()` prunes on read."""
    import shutil

    for i in range(3):
        (tmp_path / f"p{i}").mkdir()
        projects.register(tmp_path / f"p{i}", cap=3)
    shutil.rmtree(tmp_path / "p1")

    assert len(projects.known()) == 2
    (tmp_path / "new").mkdir()
    assert projects.register(tmp_path / "new", cap=3) == projects.REGISTERED


def test_forget_releases_a_slot_by_path(tmp_path: Path) -> None:
    root = tmp_path / "one"
    root.mkdir()
    projects.register(root, cap=3)
    removed = projects.forget(str(root))
    assert removed is not None and removed.path == projects.canonical(root)
    assert projects.known() == []


def test_forget_on_something_unknown_returns_nothing(tmp_path: Path) -> None:
    assert projects.forget(str(tmp_path / "never-seen")) is None


# -- identity: the decision that keeps CI working ---------------------------


def test_a_folder_with_no_remote_is_keyed_on_its_path(tmp_path: Path) -> None:
    key = projects.key_for(tmp_path)
    assert key.startswith("path:")
    assert projects.canonical(tmp_path) in key


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/edify-dev/edify.git",
        "https://github.com/edify-dev/edify",
        "git@github.com:edify-dev/edify.git",
        "ssh://git@github.com/edify-dev/edify.git",
        "https://github.com/edify-dev/edify/",
    ],
)
def test_every_way_of_writing_one_remote_is_one_project(url: str) -> None:
    """Cloning over SSH after cloning over HTTPS must not cost a slot."""
    assert projects._normalise_remote(url) == "github.com/edify-dev/edify"


def test_two_checkouts_of_one_repository_share_a_slot(tmp_path: Path) -> None:
    """D-7, and the reason for it: a fresh CI checkout every run would otherwise
    exhaust the free tier in three builds."""
    if not _git_available():
        pytest.skip("git is not on PATH")

    first = _fake_clone(tmp_path / "ci-run-1", "https://github.com/acme/service.git")
    second = _fake_clone(tmp_path / "ci-run-2", "https://github.com/acme/service.git")

    assert projects.register(first, cap=3) == projects.REGISTERED
    assert projects.register(second, cap=3) == projects.ALREADY
    assert len(projects.known()) == 1


def test_a_moved_checkout_follows_rather_than_duplicating(tmp_path: Path) -> None:
    if not _git_available():
        pytest.skip("git is not on PATH")

    first = _fake_clone(tmp_path / "a", "https://github.com/acme/thing.git")
    second = _fake_clone(tmp_path / "b", "https://github.com/acme/thing.git")
    projects.register(first, cap=3)
    projects.register(second, cap=3)
    rows = projects.known()
    assert len(rows) == 1
    assert rows[0].path == projects.canonical(second)


def test_two_different_repositories_are_two_projects(tmp_path: Path) -> None:
    if not _git_available():
        pytest.skip("git is not on PATH")

    a = _fake_clone(tmp_path / "a", "https://github.com/acme/one.git")
    b = _fake_clone(tmp_path / "b", "https://github.com/acme/two.git")
    projects.register(a, cap=3)
    projects.register(b, cap=3)
    assert len(projects.known()) == 2


# -- the gate, through the CLI ----------------------------------------------


def test_three_installs_are_free(tmp_path: Path) -> None:
    for i in range(3):
        assert _install(tmp_path / f"p{i}") == 0


def test_the_fourth_install_is_refused_with_the_price(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The M4 gate."""
    for i in range(3):
        _install(tmp_path / f"p{i}")
    capsys.readouterr()

    assert _install(tmp_path / "p3") == TierRequired.exit_code
    err = capsys.readouterr().err
    assert "fourth project" in err
    assert tier.PRO_PRICE in err
    assert "edify license buy" in err
    assert "edify license activate" in err


def test_a_refused_install_leaves_nothing_behind(tmp_path: Path) -> None:
    """An empty `.edify/` would make `require_installed` say yes to a repository
    that was never installed — worse than nothing."""
    for i in range(3):
        _install(tmp_path / f"p{i}")
    _install(tmp_path / "p3")
    assert not (tmp_path / "p3" / ".edify").exists()


def test_reinstalling_an_existing_project_is_never_refused(tmp_path: Path) -> None:
    """It never breaks work already done. This is the assertion that says so."""
    for i in range(3):
        _install(tmp_path / f"p{i}")
    for i in range(3):
        assert _install(tmp_path / f"p{i}", "--fresh") == 0


def test_a_pro_token_lifts_the_gate(tmp_path: Path, pro: None) -> None:
    for i in range(5):
        assert _install(tmp_path / f"p{i}") == 0
    assert len(projects.known()) == 5


def test_every_non_install_command_ignores_the_ledger(tmp_path: Path) -> None:
    for i in range(3):
        _install(tmp_path / f"p{i}")
    root = tmp_path / "p0"
    assert main(["--repo", str(root), "graph", "build"]) == 0
    assert main(["--repo", str(root), "check"]) in (0, 1)
    assert main(["--repo", str(root), "skills", "list"]) == 0
    assert main(["--repo", str(root), "version"]) == 0


def test_an_ordinary_install_says_nothing_about_price(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """§10 commitment 3: the price appears at a gate, and nowhere else."""
    assert _install(tmp_path / "only") == 0
    captured = capsys.readouterr()
    assert tier.PRO_PRICE not in captured.out + captured.err


# -- the entitlement --------------------------------------------------------


def test_free_carries_the_project_cap() -> None:
    assert tier.Entitlement().project_cap == tier.FREE_PROJECT_CAP == 3


def test_pro_carries_projects_unlimited() -> None:
    ent = tier.Entitlement(plan="pro", features=tier.ENTITLEMENTS["pro"])
    assert ent.allows("projects.unlimited")
    assert ent.project_cap is None


def test_the_new_feature_is_named_like_the_other_four() -> None:
    assert "projects.unlimited" in tier.FEATURE_NAMES
    assert set(tier.FEATURE_NAMES) >= set().union(*tier.ENTITLEMENTS.values())


def test_the_price_is_written_once() -> None:
    """It is one constant so it cannot drift, which is the whole reason it exists."""
    assert tier.PRO_PRICE == "$20 per user per month"
    assert tier.PRO_PRICE in TierRequired("x").message


# -- the commands -----------------------------------------------------------


def test_license_projects_lists_what_is_installed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _install(tmp_path / "p0")
    capsys.readouterr()
    assert main(["license", "projects"]) == 0
    out = capsys.readouterr().out
    assert projects.canonical(tmp_path / "p0") in out
    assert "1 of 3" in out


def test_license_projects_is_machine_readable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _install(tmp_path / "p0")
    capsys.readouterr()
    assert main(["--json", "license", "projects"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["cap"] == 3 and payload["used"] == 1


def test_license_projects_forget_frees_a_slot(tmp_path: Path) -> None:
    for i in range(3):
        _install(tmp_path / f"p{i}")
    assert main(["license", "projects", "forget", str(tmp_path / "p1")]) == 0
    assert _install(tmp_path / "p3") == 0


def test_forgetting_something_unknown_says_so(tmp_path: Path) -> None:
    assert main(["license", "projects", "forget", str(tmp_path / "nope")]) == 1


def test_license_status_shows_the_project_cap(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _install(tmp_path / "p0")
    capsys.readouterr()
    assert main(["license", "status"]) == 0
    out = capsys.readouterr().out
    assert "project cap" in out
    assert "3 projects" in out
    assert tier.PRO_PRICE in out  # somebody who typed this is asking


def test_license_status_json_carries_the_new_cap(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--json", "license", "status"]) == 0
    assert json.loads(capsys.readouterr().out)["project_cap"] == 3


# -- buy --------------------------------------------------------------------


def test_buy_prints_the_price_and_the_link(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["license", "buy"]) == 0
    out = capsys.readouterr().out
    assert tier.PRO_PRICE in out
    assert tier.BUY_URL in out


def test_buy_never_opens_a_browser_without_a_terminal(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A pipeline gets a string, not a surprise window."""
    import webbrowser

    def explode(*a, **k):  # pragma: no cover — the point is that it is not reached
        raise AssertionError("a browser was opened in a pipeline")

    monkeypatch.setattr(webbrowser, "open", explode)
    assert main(["license", "buy"]) == 0
    capsys.readouterr()
    assert main(["--json", "license", "buy"]) == 0
    assert json.loads(capsys.readouterr().out)["url"] == tier.BUY_URL


def test_seats_become_a_quantity(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--json", "license", "buy", "--seats", "7"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["seats"] == 7
    assert "quantity=7" in payload["url"]


def test_the_buy_url_is_overridable_for_stripe_test_mode(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """D-8, and the M5 gate: test mode is one environment variable away."""
    monkeypatch.setenv("EDIFY_BUY_URL", "https://buy.stripe.com/test_abc123")
    assert main(["--json", "license", "buy"]) == 0
    assert json.loads(capsys.readouterr().out)["url"] == "https://buy.stripe.com/test_abc123"


def test_an_overridden_url_still_takes_a_quantity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EDIFY_BUY_URL", "https://buy.stripe.com/test_abc?x=1")
    assert tier.buy_url(4) == "https://buy.stripe.com/test_abc?x=1&quantity=4"


# ---------------------------------------------------------------------------


def _git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def _fake_clone(path: Path, remote: str) -> Path:
    """A directory that answers `git remote get-url origin` — which is all D-7 reads."""
    path.mkdir(parents=True)
    for argv in (
        ["git", "init", "--quiet"],
        ["git", "remote", "add", "origin", remote],
    ):
        subprocess.run(argv, cwd=str(path), capture_output=True, timeout=30, check=True)
    return path
