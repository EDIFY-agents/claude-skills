"""Asking for feedback without becoming a tool that phones home.

`docs/pricing.md` §4 commits to no telemetry — not anonymous, not
aggregate, not opt-out. These tests are that commitment written down as assertions:
nothing is transmitted, nothing is collected in the background, nothing is written
into the customer's repository, and a non-interactive run leaves no trace at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from edify import feedback
from edify.cli import main
from edify.ui import Out


def interactive_out(monkeypatch: pytest.MonkeyPatch, *answers: str) -> Out:
    monkeypatch.setattr(Out, "interactive", property(lambda self: True))
    scripted = iter(answers)
    monkeypatch.setattr("builtins.input", lambda *a: next(scripted))
    return Out(json_mode=False, color=False)


# -- the invitation ----------------------------------------------------------


def test_a_run_with_no_terminal_writes_nothing_at_all(isolated_home: Path, installed: Path) -> None:
    """CI, a pipe, and a model calling the binary leave no trace on this machine."""
    assert main(["--repo", str(installed), "--quiet", "graph", "stat"]) == 0
    assert not feedback.state_path().exists()


def test_the_invitation_waits_and_then_appears_exactly_once(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out = interactive_out(monkeypatch)

    for _ in range(feedback.INVITE_AFTER_RUNS - 1):
        feedback.maybe_invite(out)
    assert "edify feedback" not in capsys.readouterr().err

    feedback.maybe_invite(out)
    assert "edify feedback" in capsys.readouterr().err

    for _ in range(5):
        feedback.maybe_invite(out)
    assert "edify feedback" not in capsys.readouterr().err


def test_the_invitation_is_on_stderr_and_never_touches_the_answer(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out = interactive_out(monkeypatch)
    for _ in range(feedback.INVITE_AFTER_RUNS):
        feedback.maybe_invite(out)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "How is EDIFY working" in captured.err


def test_off_is_permanent_and_on_brings_it_back(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], installed: Path
) -> None:
    assert main(["--repo", str(installed), "--quiet", "feedback", "off"]) == 0
    assert feedback.disabled()

    out = interactive_out(monkeypatch)
    for _ in range(10):
        feedback.maybe_invite(out)
    assert capsys.readouterr().err == ""

    assert main(["--repo", str(installed), "--quiet", "feedback", "on"]) == 0
    assert not feedback.disabled()


def test_an_environment_variable_switches_it_off_without_writing_anything(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EDIFY_NO_FEEDBACK", "1")
    out = interactive_out(monkeypatch)
    for _ in range(10):
        feedback.maybe_invite(out)
    assert capsys.readouterr().err == ""
    assert not feedback.state_path().exists()


def test_the_feedback_command_itself_never_triggers_the_invitation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], installed: Path
) -> None:
    monkeypatch.setattr(Out, "interactive", property(lambda self: True))
    feedback._save({"runs": "50"})
    monkeypatch.setattr("builtins.input", lambda *a: "")

    assert main(["--repo", str(installed), "feedback", "-m", "fine"]) == 0
    assert "How is EDIFY working" not in capsys.readouterr().err


# -- writing one entry -------------------------------------------------------


def test_an_entry_is_a_local_file_and_the_command_says_how_to_send_it(
    capsys: pytest.CaptureFixture[str], isolated_home: Path, installed: Path
) -> None:
    assert main(["--repo", str(installed), "feedback", "-m", "the graph is the whole product"]) == 0
    out = capsys.readouterr().out

    entries = feedback.existing()
    assert len(entries) == 1
    assert entries[0].is_relative_to(isolated_home)
    assert "the graph is the whole product" in entries[0].read_text(encoding="utf-8")

    assert "Nothing left this machine" in out
    assert "gh issue create" in out


def test_nothing_is_ever_written_into_the_repository(isolated_home: Path, installed: Path) -> None:
    before = {p for p in installed.rglob("*") if p.is_file()}
    assert main(["--repo", str(installed), "--quiet", "feedback", "-m", "hello"]) == 0
    assert {p for p in installed.rglob("*") if p.is_file()} == before


def test_the_interview_asks_four_questions_and_records_the_answers(
    monkeypatch: pytest.MonkeyPatch, installed: Path
) -> None:
    interactive_out(monkeypatch, "a migration", "the graph", "the spec took ages", "less ceremony", "")
    assert main(["--repo", str(installed), "feedback"]) == 0

    body = feedback.existing()[0].read_text(encoding="utf-8")
    for answer in ("a migration", "the graph", "the spec took ages", "less ceremony"):
        assert answer in body
    assert "contact:" not in body


def test_an_all_empty_interview_writes_no_file(monkeypatch: pytest.MonkeyPatch, installed: Path) -> None:
    interactive_out(monkeypatch, "", "", "", "", "")
    assert main(["--repo", str(installed), "feedback"]) == 0
    assert feedback.existing() == []


def test_with_no_terminal_and_no_message_it_says_so_rather_than_hanging(installed: Path) -> None:
    assert main(["--repo", str(installed), "feedback"]) == 1


def test_list_and_show_read_back_what_is_there(
    capsys: pytest.CaptureFixture[str], installed: Path
) -> None:
    main(["--repo", str(installed), "--quiet", "feedback", "-m", "first note"])
    main(["--repo", str(installed), "--quiet", "feedback", "-m", "second note"])

    assert main(["--repo", str(installed), "feedback", "list"]) == 0
    listing = capsys.readouterr().out
    assert "first note" in listing and "second note" in listing
    assert "none of it has been sent anywhere" in listing

    assert main(["--repo", str(installed), "feedback", "show", "0001"]) == 0
    assert "first note" in capsys.readouterr().out


def test_an_entry_records_the_install_and_nothing_about_the_codebase(installed: Path) -> None:
    """A person can read the whole file before deciding anybody else should see it."""
    main(["--repo", str(installed), "--quiet", "feedback", "-m", "a note"])
    body = feedback.existing()[0].read_text(encoding="utf-8")

    assert "edify:" in body and "python:" in body
    assert str(installed) not in body
    assert installed.name not in body
