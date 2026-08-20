"""The library asks before it installs, and never blocks when there is nobody to ask.

A skill file is persistent trusted context: once it is in `.edify/skills/`, every
matching spawn loads it as instruction. So `init` shows the matched list and takes
an answer. The property that matters as much as the question is what happens without
a terminal — CI, a pipe, a model calling the binary — where the answer is the whole
matched set and nothing waits on input.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from edify import assets, library, ui
from edify.cli import main
from edify.errors import EdifyError
from edify.paths import Layout
from edify.ui import Out

STACK = ["python", "typescript", "sql", "express", "postgres"]


def candidates() -> list[library.Candidate]:
    return library.candidates_for_stack(assets.subtree("skills"), STACK)


def quiet_out() -> Out:
    return Out(json_mode=False, color=False)


def interactive_out(monkeypatch: pytest.MonkeyPatch, *answers: str) -> Out:
    """An `Out` that believes it is on a terminal, reading a script instead of a person."""
    monkeypatch.setattr(Out, "interactive", property(lambda self: True))
    scripted = iter(answers)
    monkeypatch.setattr("builtins.input", lambda *a: next(scripted))
    return Out(json_mode=False, color=False)


# -- with nobody to ask ------------------------------------------------------


def test_no_terminal_means_the_whole_matched_set_and_no_prompt() -> None:
    out = quiet_out()
    assert not out.interactive
    assert library.choose(out, candidates(), "auto") == candidates()


def test_a_terminal_is_not_enough_for_json_or_quiet_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ui, "_has_terminal", lambda: True)
    monkeypatch.delenv("CI", raising=False)
    assert not Out(json_mode=True).interactive
    assert not Out(quiet=True).interactive


@pytest.mark.parametrize("variable", ["EDIFY_ASSUME_YES", "EDIFY_NO_PROMPT", "CI"])
def test_the_environment_can_switch_the_question_off(
    monkeypatch: pytest.MonkeyPatch, variable: str
) -> None:
    """A build machine that happens to have a pty still must not be asked anything."""
    monkeypatch.setattr(ui, "_has_terminal", lambda: True)
    monkeypatch.delenv("CI", raising=False)
    assert Out().interactive

    monkeypatch.setenv(variable, "1")
    assert not Out().interactive
    assert library.choose(Out(), candidates(), "auto") == candidates()


# -- stating the answer up front ---------------------------------------------


def test_all_none_and_names() -> None:
    out, entries = quiet_out(), candidates()
    assert library.choose(out, entries, "all") == entries
    assert library.choose(out, entries, "none") == []

    picked = library.choose(out, entries, "planner verifier")
    assert [c.name for c in picked] == ["planner", "verifier"]

    picked = library.choose(out, entries, "planner.md,implementer-python")
    assert {c.name for c in picked} == {"planner", "implementer-python"}


def test_an_unknown_name_is_refused_rather_than_ignored() -> None:
    with pytest.raises(EdifyError) as exc:
        library.choose(quiet_out(), candidates(), "planner implementer-cobol")
    assert "implementer-cobol" in exc.value.message


# -- the question itself -----------------------------------------------------


def test_the_menu_answer_can_be_numbers_a_range_or_all(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = candidates()

    out = interactive_out(monkeypatch, "1-3")
    assert library.choose(out, entries, "auto") == entries[:3]

    out = interactive_out(monkeypatch, "1,3")
    assert library.choose(out, entries, "auto") == [entries[0], entries[2]]

    out = interactive_out(monkeypatch, "")  # enter takes the default
    assert library.choose(out, entries, "auto") == entries

    out = interactive_out(monkeypatch, "none")
    assert library.choose(out, entries, "auto") == []


def test_a_bad_answer_asks_again_rather_than_installing_the_wrong_thing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = interactive_out(monkeypatch, "99", "2")
    assert library.choose(out, candidates(), "ask") == [candidates()[1]]


def test_the_menu_goes_to_stderr_so_a_pipe_stays_clean(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    library.choose(interactive_out(monkeypatch, "all"), candidates(), "ask")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "the agent library" in captured.err


# -- through init ------------------------------------------------------------


def test_init_installs_only_what_was_chosen(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    monkeypatch.setattr(Out, "interactive", property(lambda self: True))
    monkeypatch.setattr("builtins.input", lambda *a: "planner verifier")

    assert main(["--repo", str(repo), "init"]) == 0
    assert {p.stem for p in Layout(repo).skills_dir.glob("*.md")} == {"planner", "verifier"}


def test_the_skills_flag_needs_no_terminal(repo: Path) -> None:
    assert main(["--repo", str(repo), "--quiet", "init", "--skills", "planner"]) == 0
    assert {p.stem for p in Layout(repo).skills_dir.glob("*.md")} == {"planner"}


def test_yes_takes_the_whole_matched_set_without_asking(
    monkeypatch: pytest.MonkeyPatch, repo: Path
) -> None:
    monkeypatch.setattr(Out, "interactive", property(lambda self: True))

    def refuse(*_args):  # a prompt here would hang a script that passed --yes
        raise AssertionError("--yes must not ask anything")

    monkeypatch.setattr("builtins.input", refuse)
    assert main(["--repo", str(repo), "init", "--yes"]) == 0
    assert len(list(Layout(repo).skills_dir.glob("*.md"))) >= 7


def test_declining_everything_still_leaves_a_working_install(repo: Path) -> None:
    assert main(["--repo", str(repo), "--quiet", "init", "--skills", "none"]) == 0
    layout = Layout(repo)
    assert list(layout.skills_dir.glob("*.md")) == []
    assert layout.skills_index.is_file()
    assert layout.claude_md.is_file()
    assert layout.governance.is_file()


def test_a_second_init_keeps_entries_it_did_not_ask_about(repo: Path) -> None:
    """`init` merges. An entry declined on the second run is not deleted behind you."""
    assert main(["--repo", str(repo), "--quiet", "init", "--skills", "all"]) == 0
    before = {p.stem for p in Layout(repo).skills_dir.glob("*.md")}

    assert main(["--repo", str(repo), "--quiet", "init", "--skills", "planner"]) == 0
    assert {p.stem for p in Layout(repo).skills_dir.glob("*.md")} == before
