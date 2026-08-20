"""`edify init new` — a folder from zero, for every agent, after asking what it is for.

Three things this has to get right, and they are the three ways the command could look
like it worked and not have:

**Every runtime, not one.** An install that writes `CLAUDE.md` and stops is invisible
to Codex, Cursor, Gemini, Copilot, and Windsurf. The test is per runtime: its
instruction file exists, its command directory has the five pointers in the shape that
runtime parses, and the block in every instruction file is the same block.

**Somebody's own files survive.** `new` clears EDIFY's surface first, which is a
delete loop running over `.claude/`, `.cursor/`, `.github/` and three more. A hand-
written skill, a hand-written prompt, and the prose above the block in `AGENTS.md` all
have to come out the other side untouched, along with the source code.

**The questions change the install.** An interview whose answers are written to a file
and otherwise ignored is a survey. Two of the eight decide what gets installed, and
those are tested for changing it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from edify import agents, interview
from edify.cli import main
from edify.paths import Layout
from edify.ui import Out

HAND_WRITTEN = "---\nname: mine\ndescription: something a person wrote.\n---\n\nMy own method.\n"


def run(*args: str) -> int:
    return main(["--quiet", *args])


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    """A folder with source code in it and nothing else."""
    root = tmp_path / "service"
    (root / "app").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "service"\ndependencies = ["fastapi"]\n', encoding="utf-8"
    )
    (root / "app" / "main.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
    return root


@pytest.fixture
def answers(monkeypatch: pytest.MonkeyPatch):
    """Make this invocation look like a person at a terminal, and script the answers.

    `out.interactive` is the one place the CLI decides whether it may ask anything, so
    it is the one thing that has to be faked. Everything else runs for real: the same
    questions in the same order, through the same `ask`. Anything not scripted is
    answered the way pressing enter answers it — with the question's own default.
    """
    by_prompt = {q.prompt: q.key for q in interview.QUESTIONS}

    def script(**given: str):
        assert set(given) <= {q.key for q in interview.QUESTIONS}, "scripted a question nobody asks"
        monkeypatch.setattr(Out, "interactive", property(lambda self: True))

        def ask(self, question: str, default: str = "") -> str:
            return given.get(by_prompt.get(question, ""), default)

        monkeypatch.setattr(Out, "ask", ask)

    return script


# -- every runtime ----------------------------------------------------------


def test_it_writes_an_instruction_file_for_every_runtime(folder: Path) -> None:
    assert run("init", "new", str(folder), "--yes", "--no-graph") == 0

    for path in agents.all_instruction_paths():
        assert (folder / path).is_file(), f"{path} is missing — that runtime reads nothing"


def test_every_instruction_file_carries_the_same_block(folder: Path) -> None:
    """Two tools open on one repository must not be running two methodologies."""
    assert run("init", "new", str(folder), "--yes", "--no-graph") == 0

    blocks = set()
    for path in agents.all_instruction_paths():
        text = (folder / path).read_text(encoding="utf-8")
        assert agents.BLOCK_BEGIN in text and agents.BLOCK_END in text
        start = text.index(agents.BLOCK_BEGIN)
        end = text.index(agents.BLOCK_END) + len(agents.BLOCK_END)
        blocks.add(text[start:end])
        assert ".edify/graph/" in text, f"{path} does not point at the map"
    assert len(blocks) == 1


def test_every_runtime_gets_its_commands_in_the_shape_it_parses(folder: Path) -> None:
    assert run("init", "new", str(folder), "--yes", "--no-graph") == 0

    for target in agents.TARGETS:
        if not target.commands:
            continue
        found = sorted(p.name for p in (folder / target.commands).glob(f"*{target.command_suffix}"))
        assert len(found) == 5, f"{target.id} has {found}"
        pointer = (folder / target.commands / f"spec{target.command_suffix}").read_text(encoding="utf-8")
        assert agents.MARKER_TEXT in pointer, f"{target.id}'s pointer is not marked as ours"
        assert ".edify/commands/spec.md" in pointer, "the contract has to stay in one place"


def test_the_gemini_pointer_is_valid_toml(folder: Path) -> None:
    """An HTML comment in a TOML file is a parse error, not a nicety."""
    tomllib = pytest.importorskip("tomllib")
    assert run("init", "new", str(folder), "--yes", "--no-graph") == 0

    parsed = tomllib.loads((folder / ".gemini" / "commands" / "spec.toml").read_text(encoding="utf-8"))
    assert parsed["description"] == "EDIFY /spec"
    assert ".edify/commands/spec.md" in parsed["prompt"]


def test_the_cursor_rule_is_always_applied(folder: Path) -> None:
    """A `.mdc` file without `alwaysApply` is a file Cursor has and never loads."""
    assert run("init", "new", str(folder), "--yes", "--no-graph") == 0

    text = (folder / ".cursor" / "rules" / "edify.mdc").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "alwaysApply: true" in text.split("---")[1]


def test_skills_are_mirrored_where_the_runtime_looks_for_them(folder: Path) -> None:
    assert run("init", "new", str(folder), "--yes", "--no-graph") == 0

    installed = {p.stem for p in (folder / ".edify" / "skills").glob("*.md") if p.stem != "index"}
    assert installed, "nothing was installed, so this test proves nothing"
    for name in installed:
        assert (folder / ".claude" / "skills" / name / "SKILL.md").is_file()


def test_a_named_subset_installs_only_those_runtimes(folder: Path) -> None:
    assert run("init", "new", str(folder), "--yes", "--no-graph", "--agents", "claude,codex") == 0

    assert (folder / "CLAUDE.md").is_file()
    assert (folder / "AGENTS.md").is_file()
    assert (folder / ".codex" / "prompts" / "spec.md").is_file()
    assert not (folder / "GEMINI.md").exists()
    assert not (folder / ".cursor").exists()
    assert not (folder / ".github").exists()


def test_an_unknown_runtime_is_an_error_and_not_a_shrug(folder: Path) -> None:
    """Somebody who typed `--agents cursur` asked for Cursor."""
    assert run("init", "new", str(folder), "--yes", "--no-graph", "--agents", "cursur") != 0


def test_agents_none_installs_the_harness_and_no_runtime_files(folder: Path) -> None:
    assert run("init", "new", str(folder), "--yes", "--no-graph", "--agents", "none") == 0

    assert (folder / ".edify" / "skills").is_dir()
    for path in agents.all_instruction_paths():
        assert not (folder / path).exists()


def test_plain_init_is_still_claude_alone(folder: Path) -> None:
    """`new` is the command that changed. `init` writes what it always wrote."""
    assert run("--repo", str(folder), "init", "--yes", "--no-graph") == 0

    assert (folder / "CLAUDE.md").is_file()
    assert not (folder / "GEMINI.md").exists()
    assert not (folder / ".cursor").exists()


def test_a_later_plain_init_keeps_every_runtime_current(folder: Path) -> None:
    """Five stale instruction files and one current one is worse than either state."""
    assert run("init", "new", str(folder), "--yes", "--no-graph") == 0
    (folder / "GEMINI.md").unlink()
    (folder / ".github" / "copilot-instructions.md").write_text("gone stale\n", encoding="utf-8")

    assert run("--repo", str(folder), "init", "--yes", "--no-graph") == 0

    assert (folder / "GEMINI.md").is_file(), "a runtime set up here was left behind"
    copilot = (folder / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
    assert "gone stale" in copilot, "somebody's own text is kept"
    assert ".edify/graph/" in copilot, "and the block is merged back in"


def test_a_hand_written_agents_md_does_not_conscript_other_runtimes(folder: Path) -> None:
    """`AGENTS.md` is as likely to predate EDIFY as to have been written by it, so it
    is never the evidence that Codex or Cursor is set up here."""
    (folder / "AGENTS.md").write_text("# my notes\n", encoding="utf-8")

    assert run("--repo", str(folder), "init", "--yes", "--no-graph") == 0
    assert not (folder / ".codex").exists()
    assert not (folder / ".cursor").exists()


def test_skills_sync_updates_every_runtime_set_up_here(folder: Path) -> None:
    assert run("init", "new", str(folder), "--yes", "--no-graph") == 0
    pointer = folder / ".windsurf" / "workflows" / "spec.md"
    pointer.write_text(f"{agents.MARKER_TEXT}\nstale\n", encoding="utf-8")

    assert run("--repo", str(folder), "skills", "sync") == 0
    assert ".edify/commands/spec.md" in pointer.read_text(encoding="utf-8")


# -- the folder -------------------------------------------------------------


def test_it_installs_into_the_folder_it_was_given_not_the_parent(folder: Path) -> None:
    """The trap `init` walks into: a new folder inside a checkout has a root above it."""
    (folder / ".git").mkdir()
    target = folder / "services" / "billing"

    assert run("init", "new", str(target), "--yes", "--no-graph") == 0
    assert (target / ".edify" / "skills").is_dir()
    assert not (folder / ".edify").exists(), "it installed into the parent repository"


def test_it_creates_a_folder_that_does_not_exist(tmp_path: Path) -> None:
    target = tmp_path / "brand" / "new"
    assert run("init", "new", str(target), "--yes", "--no-graph") == 0
    assert (target / ".edify" / "governance.tsv").is_file()


def test_it_refuses_a_path_that_is_a_file(tmp_path: Path) -> None:
    target = tmp_path / "notadir"
    target.write_text("x", encoding="utf-8")
    assert run("init", "new", str(target), "--yes", "--no-graph") != 0


def test_a_rerun_clears_our_files_and_keeps_everybody_elses(folder: Path) -> None:
    assert run("init", "new", str(folder), "--yes", "--no-graph") == 0

    mine = folder / ".claude" / "skills" / "mine" / "SKILL.md"
    mine.parent.mkdir(parents=True, exist_ok=True)
    mine.write_text(HAND_WRITTEN, encoding="utf-8")
    my_prompt = folder / ".codex" / "prompts" / "mine.md"
    my_prompt.write_text(HAND_WRITTEN, encoding="utf-8")
    existing = (folder / "AGENTS.md").read_text(encoding="utf-8")
    (folder / "AGENTS.md").write_text("# my own notes\nkeep me\n\n" + existing, encoding="utf-8")
    stale_pointer = folder / ".gemini" / "commands" / "spec.toml"
    stale_pointer.write_text("# edify:generated\ndescription = \"stale\"\n", encoding="utf-8")

    assert run("init", "new", str(folder), "--yes", "--no-graph") == 0

    assert (folder / "app" / "main.py").read_text(encoding="utf-8") == "def hello():\n    return 1\n"
    assert mine.read_text(encoding="utf-8") == HAND_WRITTEN
    assert my_prompt.read_text(encoding="utf-8") == HAND_WRITTEN
    assert "keep me" in (folder / "AGENTS.md").read_text(encoding="utf-8")
    assert "stale" not in stale_pointer.read_text(encoding="utf-8"), "our own pointer is ours to replace"


def test_keep_reinstalls_without_clearing_first(folder: Path) -> None:
    assert run("init", "new", str(folder), "--yes", "--no-graph") == 0
    edited = folder / ".edify" / "skills" / "verifier.md"
    edited.write_text("clobbered\n", encoding="utf-8")

    assert run("init", "new", str(folder), "--yes", "--no-graph", "--keep") == 0
    assert edited.read_text(encoding="utf-8") != "clobbered\n", "`new` still means install everything"


def test_everything_it_writes_is_in_the_ledger(folder: Path) -> None:
    assert run("init", "new", str(folder), "--yes", "--no-graph") == 0

    ledger = (folder / ".edify" / "governance.tsv").read_text(encoding="utf-8")
    for path in ("CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursor/commands/spec.md", ".gemini/commands/spec.toml"):
        assert path in ledger, f"{path} was installed and is unaccounted for"
    assert run("--repo", str(folder), "governance", "verify", "--exit-code") == 0


# -- the questions ----------------------------------------------------------


def test_with_nobody_to_ask_it_asks_nothing_and_installs_everything(folder: Path) -> None:
    """A question is never load-bearing: no terminal, no interview, full install."""
    assert run("init", "new", str(folder), "--no-graph") == 0

    assert not (folder / ".edify" / "profile.md").exists()
    assert (folder / "CLAUDE.md").is_file()
    assert (folder / "GEMINI.md").is_file()


def test_the_answers_are_written_where_every_session_reads_them(folder: Path, answers) -> None:
    answers(
        name="Ada",
        role="staff engineer",
        building="a billing service that replaces the one in production",
        done="invoices reconcile against the ledger",
        constraints="never touch migrations without a plan",
        explain="teaching",
    )
    assert run("init", "new", str(folder), "--no-graph") == 0

    profile = (folder / ".edify" / "profile.md").read_text(encoding="utf-8")
    assert "Ada" in profile
    assert "a billing service" in profile
    assert "never touch migrations without a plan" in profile

    block = (folder / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Ada" in block, "the one line worth spending context on every session"
    assert ".edify/profile.md" in block, "and a pointer at the rest"


def test_the_profile_is_governed_as_the_repositorys_own_file(folder: Path, answers) -> None:
    answers(name="Ada", building="a billing service")
    assert run("init", "new", str(folder), "--no-graph") == 0

    row = next(
        line
        for line in (folder / ".edify" / "governance.tsv").read_text(encoding="utf-8").splitlines()
        if line.startswith(".edify/profile.md")
    )
    assert "answered" in row
    assert run("--repo", str(folder), "governance", "verify", "--exit-code") == 0


def test_the_answer_about_runtimes_decides_what_is_installed(folder: Path, answers) -> None:
    """Two of the eight questions change the install. This is one of them."""
    answers(agents="claude gemini")
    assert run("init", "new", str(folder), "--no-graph") == 0

    assert (folder / "CLAUDE.md").is_file()
    assert (folder / "GEMINI.md").is_file()
    assert not (folder / ".cursor").exists()
    assert not (folder / ".github").exists()


def test_the_answer_about_the_stack_reaches_the_library(folder: Path, answers) -> None:
    """The other one: a tech id detection could not see still selects its entries."""
    answers(stack="postgres")
    assert run("init", "new", str(folder), "--no-graph") == 0

    names = {p.stem for p in (folder / ".edify" / "skills").glob("*.md")}
    assert "implementer-postgres" in names, "the answer was written down and ignored"


def test_a_rerun_keeps_the_profile_when_it_is_told_not_to_ask(folder: Path, answers) -> None:
    answers(name="Ada", building="a billing service", constraints="never touch migrations")
    assert run("init", "new", str(folder), "--no-graph") == 0
    before = (folder / ".edify" / "profile.md").read_text(encoding="utf-8")

    assert run("init", "new", str(folder), "--no-graph", "--no-interview") == 0
    assert (folder / ".edify" / "profile.md").read_text(encoding="utf-8") == before
    assert "Ada" in (folder / "CLAUDE.md").read_text(encoding="utf-8")


def test_an_abandoned_interview_still_installs(folder: Path, answers) -> None:
    """Enter skips a question; every question skipped is not an error."""
    answers(name="", role="", building="", done="", constraints="", explain="")
    assert run("init", "new", str(folder), "--no-graph") == 0

    assert (folder / "CLAUDE.md").is_file()
    assert "Who you are working with" not in (folder / "CLAUDE.md").read_text(encoding="utf-8")


# -- the profile file itself ------------------------------------------------


def test_a_profile_round_trips_through_the_file(tmp_path: Path) -> None:
    """A re-run offers last time's answers, so they have to survive being written."""
    profile = interview.Profile(
        answers={
            "name": "Ada",
            "role": "staff engineer",
            "building": "a billing service that replaces the one in production",
            "done": "invoices reconcile against the ledger",
            "constraints": "never touch migrations without a plan",
            "agents": "claude cursor",
        },
        asked=True,
    )
    path = tmp_path / "profile.md"
    assert interview.write(path, profile)

    back = interview.load(path)
    assert back.get("name") == "Ada"
    assert back.get("role") == "staff engineer"
    assert back.get("building").startswith("a billing service")
    assert back.get("constraints") == "never touch migrations without a plan"
    assert back.get("agents") == "claude cursor"


def test_an_empty_profile_writes_no_file(tmp_path: Path) -> None:
    path = tmp_path / "profile.md"
    assert not interview.write(path, interview.Profile())
    assert not path.exists()


def test_a_hand_edited_profile_is_read_back_as_far_as_it_can_be(tmp_path: Path) -> None:
    """This file is meant to be edited. Reformatting it must not lose everything."""
    path = tmp_path / "profile.md"
    path.write_text(
        "# whatever heading I like\n\n## What is being built\n\nA thing.\nOn two lines.\n",
        encoding="utf-8",
    )
    assert interview.load(path).get("building") == "A thing. On two lines."


@pytest.mark.parametrize("flag", ["--stack", "--skills", "--agents", "--host", "--extractor", "--yes"])
def test_it_takes_the_flags_init_takes(flag: str) -> None:
    """`init new` is `init` with the root pinned, so a flag one takes the other takes."""
    from edify.cli import build_parser

    parser = build_parser()
    init = parser._subparsers._group_actions[0].choices["init"]
    new = init._subparsers._group_actions[0].choices["new"]
    assert flag in {s for action in new._actions for s in action.option_strings}


def test_the_layout_knows_every_instruction_file(folder: Path) -> None:
    """Governance and clearing both walk this list; a runtime missing from it is a
    runtime whose files nothing accounts for."""
    paths = {Path(p).as_posix() for p in agents.all_instruction_paths()}
    assert {"CLAUDE.md", "AGENTS.md", "GEMINI.md"} <= paths
    assert {Layout(folder).rel(p) for p in Layout(folder).instruction_files()} == paths
