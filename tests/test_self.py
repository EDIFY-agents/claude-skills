"""`edify self` — manager detection, the install argv, and the two honest failures.

`selfinstall` is pure functions on purpose, so every decision that matters here is
tested without installing anything or running a subprocess. The two places that do
run one — the install and the version read-back — are patched, because a test that
actually reinstalled the developer's CLI would be a test nobody runs twice.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from edify import selfinstall
from edify.cli import main
from edify.errors import EdifyError

MANIFEST = '[project]\nname = "edify-cli"\nversion = "0.1.0"\n'
OTHER_MANIFEST = '[project]\nname = "something-else"\nversion = "9.9.9"\n'


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    root = tmp_path / "edify-checkout"
    root.mkdir()
    (root / "pyproject.toml").write_text(MANIFEST, encoding="utf-8")
    return root


# -- detection --------------------------------------------------------------


@pytest.mark.parametrize(
    "prefix, expected",
    [
        ("/home/x/.local/share/uv/tools/edify-cli", "uv"),
        (r"C:\Users\x\AppData\Roaming\uv\tools\edify-cli", "uv"),
        ("/home/x/.local/share/pipx/venvs/edify-cli", "pipx"),
        (r"C:\Users\x\pipx\venvs\edify-cli", "pipx"),
        ("/usr", "pip"),
        ("/home/x/project/.venv", "pip"),
        ("/usr/local/Cellar/python@3.12/3.12.4/Frameworks", "pip"),
    ],
)
def test_the_manager_is_read_from_the_prefix_path(prefix: str, expected: str) -> None:
    assert selfinstall.detect_manager(prefix) == expected


def test_an_unknown_layout_falls_back_to_pip() -> None:
    """pip is the safe default: it installs into the environment it is run from,
    so a wrong guess is a no-op rather than a shadowed second copy."""
    assert selfinstall.detect_manager("/somewhere/nobody/expected") == "pip"


# -- the install argv -------------------------------------------------------


def test_uv_replaces_rather_than_adds() -> None:
    argv = selfinstall.install_command("uv", "/src")
    assert argv[:3] == ["uv", "tool", "install"]
    assert "--force" in argv and "--reinstall" in argv
    assert argv[-1] == "/src"


def test_pipx_forces_and_takes_editable() -> None:
    argv = selfinstall.install_command("pipx", "/src", editable=True)
    assert argv[:3] == ["pipx", "install", "--force"]
    assert "--editable" in argv


def test_pip_runs_through_this_interpreter_not_whatever_pip_is_on_path() -> None:
    argv = selfinstall.install_command("pip", "/src")
    assert argv[:4] == [sys.executable, "-m", "pip", "install"]
    assert "--force-reinstall" in argv


def test_offline_is_passed_through_per_manager() -> None:
    assert "--offline" in selfinstall.install_command("uv", "/src", offline=True)
    assert "--no-index" in selfinstall.install_command("pip", "/src", offline=True)
    pipx = selfinstall.install_command("pipx", "/src", offline=True)
    assert "--pip-args" in pipx and "--no-index" in pipx


def test_an_unknown_manager_is_refused_with_the_list() -> None:
    with pytest.raises(EdifyError) as exc:
        selfinstall.install_command("conda", "/src")
    assert "uv" in (exc.value.hint or "")


# -- resolving the source ---------------------------------------------------


def test_an_explicit_checkout_is_accepted(checkout: Path) -> None:
    assert selfinstall.resolve_source(str(checkout)) == checkout.resolve()


def test_a_directory_that_is_not_an_edify_checkout_is_refused(tmp_path: Path) -> None:
    other = tmp_path / "other"
    other.mkdir()
    (other / "pyproject.toml").write_text(OTHER_MANIFEST, encoding="utf-8")
    with pytest.raises(EdifyError) as exc:
        selfinstall.resolve_source(str(other))
    assert "not an edify checkout" in exc.value.message


def test_a_missing_directory_is_refused_before_anything_is_installed(tmp_path: Path) -> None:
    with pytest.raises(EdifyError):
        selfinstall.resolve_source(str(tmp_path / "nope"))


def test_is_source_checkout_reads_the_distribution_name(checkout: Path, tmp_path: Path) -> None:
    assert selfinstall.is_source_checkout(checkout)
    assert not selfinstall.is_source_checkout(tmp_path)


def test_the_running_source_is_this_repository() -> None:
    """These tests import from `src/`, so the walk up must find this checkout."""
    source = selfinstall.running_source()
    assert source is not None
    assert (source / "pyproject.toml").is_file()


# -- lock detection ---------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "error: Access is denied. (os error 5)",
        "PermissionError: [WinError 32] The process cannot access the file because it is "
        "being used by another process",
        "OSError: [Errno 26] Text file busy",
        "failed to remove file `edify.exe`",
    ],
)
def test_a_held_open_binary_is_recognised(text: str) -> None:
    assert selfinstall.looks_locked(text)


def test_an_ordinary_failure_is_not_mistaken_for_a_lock() -> None:
    assert not selfinstall.looks_locked("ERROR: No matching distribution found for hatchling")


def test_the_unlock_hint_is_the_command_to_run_elsewhere(checkout: Path) -> None:
    hint = selfinstall.unlock_hint("uv", checkout)
    assert "uv tool install" in hint
    assert str(checkout) in hint


# -- the command ------------------------------------------------------------


def test_self_where_prints_what_was_detected(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["self", "where"]) == 0
    out = capsys.readouterr().out
    assert "installer" in out
    assert "update with" in out


def test_self_where_is_machine_readable(capsys: pytest.CaptureFixture[str]) -> None:
    import json

    assert main(["--json", "self", "where"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["manager"] in selfinstall.MANAGERS
    assert payload["version"]


def test_dry_run_prints_the_command_and_installs_nothing(
    checkout: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*a, **k):  # pragma: no cover — the point is that it is not reached
        raise AssertionError("--dry-run ran the installer")

    monkeypatch.setattr(subprocess, "run", explode)
    assert main(["self", "update", "--from", str(checkout), "--dry-run"]) == 0
    assert str(checkout) in capsys.readouterr().out


def test_dry_run_prints_the_same_argv_the_real_run_would_use(
    checkout: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import json

    assert main(["--json", "self", "update", "--from", str(checkout),
                 "--manager", "uv", "--dry-run"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ran"] is False
    assert payload["command"] == selfinstall.install_command("uv", checkout)


def test_a_locked_binary_is_reported_with_the_command_to_run_elsewhere(
    checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Never a success it did not have — the exact failure Windows produces."""
    from edify.commands import self_cmd

    monkeypatch.setattr(
        self_cmd, "_run",
        lambda argv: (1, "error: failed to remove file `edify.exe`: Access is denied. (os error 5)"),
    )
    code = main(["self", "update", "--from", str(checkout), "--manager", "uv"])
    assert code == EdifyError.exit_code


def test_a_locked_binary_names_the_reinstall_command_in_the_hint(
    checkout: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from edify.commands import self_cmd

    monkeypatch.setattr(self_cmd, "_run", lambda argv: (1, "Access is denied"))
    main(["self", "update", "--from", str(checkout), "--manager", "uv"])
    err = capsys.readouterr().err
    assert "uv tool install" in err


def test_an_ordinary_install_failure_is_reported_as_itself(
    checkout: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from edify.commands import self_cmd

    monkeypatch.setattr(
        self_cmd, "_run",
        lambda argv: (1, "ERROR: No matching distribution found for hatchling"),
    )
    assert main(["self", "update", "--from", str(checkout), "--manager", "pip"]) != 0
    err = capsys.readouterr().err
    assert "could not install" in err
    assert "hatchling" in err


def test_a_successful_update_reports_the_version_transition(
    checkout: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from edify.commands import self_cmd

    monkeypatch.setattr(self_cmd, "_run", lambda argv: (0, "installed"))
    monkeypatch.setattr(self_cmd, "_installed_version", lambda: "0.1.1")
    assert main(["self", "update", "--from", str(checkout), "--manager", "uv"]) == 0
    err = capsys.readouterr().err
    assert "0.1.1" in err


def test_an_unchanged_version_is_stated_rather_than_celebrated(
    checkout: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A shadowed second copy looks exactly like this, so the note says so."""
    from edify import __version__
    from edify.commands import self_cmd

    monkeypatch.setattr(self_cmd, "_run", lambda argv: (0, ""))
    monkeypatch.setattr(self_cmd, "_installed_version", lambda: __version__)
    assert main(["self", "update", "--from", str(checkout), "--manager", "uv"]) == 0
    err = capsys.readouterr().err
    assert "did not change" in err


def test_update_does_not_touch_any_repository(
    checkout: Path, installed: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`self update` replaces the CLI. Reinstalling the harness is `edify setup`."""
    from edify.commands import self_cmd

    before = sorted(p.name for p in (installed / ".edify").iterdir())
    monkeypatch.setattr(self_cmd, "_run", lambda argv: (0, ""))
    monkeypatch.setattr(self_cmd, "_installed_version", lambda: "0.1.0")
    main(["--repo", str(installed), "self", "update", "--from", str(checkout), "--manager", "uv"])
    assert sorted(p.name for p in (installed / ".edify").iterdir()) == before


def test_self_with_no_subcommand_prints_the_family_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        main(["self"])
    assert "update" in capsys.readouterr().out
