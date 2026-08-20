"""The three platforms this installs on, and what each one does with a licence.

macOS is the one that changed: it used to land in `~/.config/edify`, which is a
Linux convention that a Mac user does not expect and a Mac backup tool does not
treat as application data. It now uses `~/Library/Application Support/edify`, and a
machine that already has the old directory keeps it — an upgrade that silently
orphans somebody's licence is worse than an inconsistent path.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from edify import paths
from edify.graph.ignore import IgnoreRules


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """No overrides, and a home directory that is not the developer's."""
    monkeypatch.delenv("EDIFY_HOME", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


MAC = {"os_name": "posix", "platform": "darwin"}
LINUX = {"os_name": "posix", "platform": "linux"}
WINDOWS = {"os_name": "nt", "platform": "win32"}


def test_macos_uses_application_support(clean_env: Path) -> None:
    assert paths.user_config_dir(**MAC) == clean_env / "Library" / "Application Support" / "edify"


def test_macos_keeps_an_existing_dot_config_install(clean_env: Path) -> None:
    legacy = clean_env / ".config" / "edify"
    legacy.mkdir(parents=True)
    assert paths.user_config_dir(**MAC) == legacy


def test_linux_uses_xdg(monkeypatch: pytest.MonkeyPatch, clean_env: Path) -> None:
    assert paths.user_config_dir(**LINUX) == clean_env / ".config" / "edify"

    monkeypatch.setenv("XDG_CONFIG_HOME", str(clean_env / "elsewhere"))
    assert paths.user_config_dir(**LINUX) == clean_env / "elsewhere" / "edify"


def test_windows_uses_appdata(monkeypatch: pytest.MonkeyPatch, clean_env: Path) -> None:
    monkeypatch.setenv("APPDATA", str(clean_env / "Roaming"))
    assert paths.user_config_dir(**WINDOWS) == clean_env / "Roaming" / "edify"


@pytest.mark.parametrize("where", [MAC, LINUX, WINDOWS], ids=["macos", "linux", "windows"])
def test_edify_home_wins_everywhere(
    monkeypatch: pytest.MonkeyPatch, clean_env: Path, where: dict
) -> None:
    """CI and the test suite depend on this: one variable, every platform."""
    monkeypatch.setenv("EDIFY_HOME", str(clean_env / "explicit"))
    assert paths.user_config_dir(**where) == clean_env / "explicit"


def test_the_default_is_this_machine(clean_env: Path) -> None:
    """No arguments means `os.name` and `sys.platform`, which is what every caller does."""
    assert paths.user_config_dir() == paths.user_config_dir(os.name, sys.platform)


def test_the_walk_ignores_what_macos_writes_into_a_source_tree(tmp_path: Path) -> None:
    """`.DS_Store` is not source, and a `.app` is a build product, not a directory."""
    rules = IgnoreRules(tmp_path)
    assert rules.skip_file(".DS_Store", "src/.DS_Store", 6148)
    assert rules.skip_dir("Edify.app", "build/Edify.app")
    assert rules.skip_dir("edify.dSYM", "build/edify.dSYM")
    assert rules.skip_dir("__MACOSX", "__MACOSX")
    assert not rules.skip_file("app.py", "src/app.py", 100)
    assert not rules.skip_dir("src", "src")


def test_a_cp1252_console_does_not_kill_a_command_that_already_worked(capsys) -> None:
    """Windows still defaults to a code page with no `→` and no `·`.

    A command that did its work and then died writing the sentence about it is the
    worst of both outcomes: the file is on disk and the exit code says failure. So
    an unencodable character degrades to a replacement rather than a traceback.
    """
    import io

    from edify.ui import Out

    narrow = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    out = Out(color=False)
    ui_emit = sys.modules["edify.ui"]._emit
    ui_emit("staged → harvest/staging/x · 40 lines", narrow)

    narrow.flush()
    written = narrow.buffer.getvalue().decode("cp1252")
    assert "staged" in written and "harvest/staging/x" in written
    assert "→" not in written  # replaced, not raised

    out.line("plain ascii still goes through untouched")
    assert "plain ascii" in capsys.readouterr().out
