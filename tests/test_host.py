"""The host runtime's mirror, and installing into one folder.

Two gaps these cover, both of them things that looked done and were not:

An entry under `.edify/skills/` is installed as far as `edify skills list` is
concerned and invisible to Claude Code, which discovers skills at
`.claude/skills/<name>/SKILL.md`. So the mirror is tested for existing at all, for
carrying the description the runtime matches on, and for never overwriting a file
EDIFY did not write.

And `init` finds its root by walking upward, so `mkdir service && edify init` inside a
checkout installs into the parent. `setup` pins the root, which is the whole reason it
exists — the test that matters is that the parent comes out untouched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from edify import host
from edify.cli import main

HAND_WRITTEN = "---\nname: mine\ndescription: something a person wrote.\n---\n\nMy own method.\n"

AGENT_ENTRY = """\
---
name: migration-specialist
description: Executes one schema migration task against a live Postgres database.
kind: agent
role: implementer
phase: 5
tech: postgres
provenance: original
---

## When this applies

A task that changes a table other code already reads.

## The method

Take the lock last.

## What it does not do

Decide whether the migration is worth making.

## Done

The migration applies and rolls back on a copy of production.
"""


def _install_agent(root: Path) -> Path:
    """One `kind: agent` entry in the library, and the mirror brought up to date."""
    from edify.cli import main

    entry = root / ".edify" / "skills" / "migration-specialist.md"
    entry.write_text(AGENT_ENTRY, encoding="utf-8")
    assert main(["--repo", str(root), "--quiet", "skills", "sync"]) == 0
    return entry


# -- the mirror -------------------------------------------------------------


def test_init_writes_a_skill_md_per_installed_entry(installed: Path):
    """The gap this closes: `.edify/skills/` is not where the runtime looks."""
    entries = sorted(p.stem for p in (installed / ".edify" / "skills").glob("*.md") if p.stem != "index")
    assert entries, "the fixture installed no skills, so this test proves nothing"
    for name in entries:
        pointer = installed / ".claude" / "skills" / name / "SKILL.md"
        assert pointer.is_file(), f"{name} is installed and the runtime cannot see it"


def test_the_pointer_carries_the_description_the_runtime_matches_on(installed: Path):
    """A pointer whose description said "see the other file" would never be loaded."""
    entry = (installed / ".edify" / "skills" / "verifier.md").read_text(encoding="utf-8")
    described = next(line for line in entry.splitlines() if line.startswith("description:"))

    pointer = (installed / ".claude" / "skills" / "verifier" / "SKILL.md").read_text(encoding="utf-8")
    assert described in pointer
    assert ".edify/skills/verifier.md" in pointer, "the method has to stay in one place"
    assert "role · phase · tech" in pointer


def test_the_mirror_is_idempotent(installed: Path):
    before = {p: p.read_bytes() for p in (installed / ".claude" / "skills").rglob("SKILL.md")}
    assert main(["--repo", str(installed), "--quiet", "skills", "sync"]) == 0
    after = {p: p.read_bytes() for p in (installed / ".claude" / "skills").rglob("SKILL.md")}
    assert before == after


def test_a_skill_file_that_is_not_ours_is_never_overwritten(installed: Path):
    """`--force` means "replace what EDIFY installed", never "replace what you wrote"."""
    mine = installed / ".claude" / "skills" / "mine" / "SKILL.md"
    mine.parent.mkdir(parents=True)
    mine.write_text(HAND_WRITTEN, encoding="utf-8")

    assert main(["--repo", str(installed), "--quiet", "init", "--force"]) == 0
    assert mine.read_text(encoding="utf-8") == HAND_WRITTEN


def test_a_pointer_is_brought_up_to_date_without_being_asked(installed: Path):
    """A pointer at a file that has been renamed is worse than no pointer."""
    pointer = installed / ".claude" / "skills" / "verifier" / "SKILL.md"
    pointer.write_text(pointer.read_text(encoding="utf-8").replace("verifier.md", "gone.md"), encoding="utf-8")

    assert main(["--repo", str(installed), "--quiet", "skills", "sync"]) == 0
    assert ".edify/skills/verifier.md" in pointer.read_text(encoding="utf-8")


def test_a_pointer_whose_entry_is_gone_is_reported_not_deleted(installed: Path):
    (installed / ".edify" / "skills" / "verifier.md").unlink()
    assert main(["--repo", str(installed), "--quiet", "skills", "index"]) == 0

    from edify.paths import Layout

    leftovers = host.stale(Layout(installed))
    assert [p.parent.name for p in leftovers] == ["verifier"]
    assert leftovers[0].is_file(), "reporting is the job here; deleting is the caller's call"


def test_the_mirror_is_governed_and_a_hand_written_one_is_not(installed: Path):
    """`verify` must not report our own output as unrecorded, or somebody's file as ours."""
    mine = installed / ".claude" / "skills" / "mine" / "SKILL.md"
    mine.parent.mkdir(parents=True)
    mine.write_text(HAND_WRITTEN, encoding="utf-8")

    assert main(["--repo", str(installed), "--quiet", "governance", "rebuild"]) == 0
    ledger = (installed / ".edify" / "governance.tsv").read_text(encoding="utf-8")
    assert ".claude/skills/verifier/SKILL.md" in ledger
    assert ".claude/skills/mine/SKILL.md" not in ledger
    assert main(["--repo", str(installed), "--quiet", "governance", "verify", "--exit-code"]) == 0


def test_host_none_writes_no_mirror(repo: Path):
    assert main(["--repo", str(repo), "--quiet", "init", "--host", "none"]) == 0
    assert not (repo / ".claude").exists()


# -- agents -----------------------------------------------------------------
# `kind` has had two legal values since the format was written and one destination
# on disk. A `kind: agent` entry mirrored as a skill is loadable and unspawnable.


def test_an_agent_entry_lands_in_claude_agents_and_not_claude_skills(installed: Path):
    _install_agent(installed)

    pointer = installed / ".claude" / "agents" / "migration-specialist.md"
    assert pointer.is_file(), "an admitted agent the runtime cannot spawn is not installed"
    assert not (installed / ".claude" / "skills" / "migration-specialist").exists()

    text = pointer.read_text(encoding="utf-8")
    assert "description: Executes one schema migration task" in text, "the runtime chooses on this"
    assert ".edify/skills/migration-specialist.md" in text, "the method has to stay in one place"


def test_a_skill_entry_still_lands_in_claude_skills(installed: Path):
    """The routing is by `kind`, so the other branch has to keep working."""
    _install_agent(installed)
    assert (installed / ".claude" / "skills" / "verifier" / "SKILL.md").is_file()
    assert not (installed / ".claude" / "agents" / "verifier.md").exists()


def test_changing_kind_leaves_the_old_pointer_and_it_is_reported(installed: Path):
    """One entry offered twice, with only one of them working — `stale` catches it."""
    from edify.paths import Layout

    entry = installed / ".edify" / "skills" / "migration-specialist.md"
    entry.write_text(AGENT_ENTRY.replace("kind: agent", "kind: skill"), encoding="utf-8")
    assert main(["--repo", str(installed), "--quiet", "skills", "sync"]) == 0
    assert (installed / ".claude" / "skills" / "migration-specialist" / "SKILL.md").is_file()

    entry.write_text(AGENT_ENTRY, encoding="utf-8")
    assert main(["--repo", str(installed), "--quiet", "skills", "sync"]) == 0

    leftovers = host.stale(Layout(installed))
    assert [p.parent.name for p in leftovers] == ["migration-specialist"]
    assert leftovers[0].is_file(), "reporting is the job here; deleting is the caller's call"


def test_an_agent_pointer_whose_entry_is_gone_is_reported(installed: Path):
    from edify.paths import Layout

    _install_agent(installed)
    (installed / ".edify" / "skills" / "migration-specialist.md").unlink()
    assert main(["--repo", str(installed), "--quiet", "skills", "index"]) == 0

    leftovers = host.stale(Layout(installed))
    assert [p.name for p in leftovers] == ["migration-specialist.md"]


def test_the_agent_mirror_is_governed_and_a_hand_written_one_is_not(installed: Path):
    _install_agent(installed)
    mine = installed / ".claude" / "agents" / "mine.md"
    mine.write_text(HAND_WRITTEN, encoding="utf-8")

    assert main(["--repo", str(installed), "--quiet", "governance", "rebuild"]) == 0
    ledger = (installed / ".edify" / "governance.tsv").read_text(encoding="utf-8")
    assert ".claude/agents/migration-specialist.md" in ledger
    assert ".claude/agents/mine.md" not in ledger
    assert main(["--repo", str(installed), "--quiet", "governance", "verify", "--exit-code"]) == 0


def test_fresh_clears_our_agent_pointer_and_keeps_a_hand_written_one(installed: Path):
    _install_agent(installed)
    ours = installed / ".claude" / "agents" / "migration-specialist.md"
    mine = installed / ".claude" / "agents" / "mine.md"
    mine.write_text(HAND_WRITTEN, encoding="utf-8")

    assert main(["--quiet", "setup", str(installed), "--fresh", "--yes", "--no-graph"]) == 0
    assert not ours.exists(), "a generated pointer is EDIFY's to remove"
    assert mine.read_text(encoding="utf-8") == HAND_WRITTEN


# -- setup ------------------------------------------------------------------


def test_setup_installs_into_the_folder_it_was_given_not_the_parent(repo: Path):
    """The trap `init` walks into: a new folder inside a checkout has a root above it."""
    (repo / ".git").mkdir()
    target = repo / "services" / "billing"

    assert main(["--quiet", "setup", str(target), "--yes", "--no-graph"]) == 0
    assert (target / ".edify" / "skills").is_dir()
    assert (target / ".claude" / "skills").is_dir()
    assert not (repo / ".edify").exists(), "setup installed into the parent repository"


def test_setup_creates_a_folder_that_does_not_exist(tmp_path: Path):
    target = tmp_path / "brand" / "new"
    assert main(["--quiet", "setup", str(target), "--yes", "--no-graph"]) == 0
    assert (target / ".edify" / "governance.tsv").is_file()
    assert (target / "CLAUDE.md").is_file()


def test_setup_refuses_a_path_that_is_a_file(tmp_path: Path):
    target = tmp_path / "notadir"
    target.write_text("x", encoding="utf-8")
    assert main(["--quiet", "setup", str(target), "--yes", "--no-graph"]) != 0


def test_setup_reinstalls_everything_over_an_existing_install(tmp_path: Path):
    target = tmp_path / "again"
    assert main(["--quiet", "setup", str(target), "--yes", "--no-graph"]) == 0
    edited = target / ".edify" / "skills" / "verifier.md"
    edited.write_text("clobbered\n", encoding="utf-8")

    assert main(["--quiet", "setup", str(target), "--yes", "--no-graph"]) == 0
    assert edited.read_text(encoding="utf-8") != "clobbered\n", "setup means install everything, again"


def test_fresh_removes_edifys_surface_and_leaves_everything_else(tmp_path: Path):
    target = tmp_path / "fresh"
    target.mkdir()
    (target / "app.py").write_text("x = 1\n", encoding="utf-8")
    assert main(["--quiet", "setup", str(target), "--yes", "--no-graph"]) == 0

    mine = target / ".claude" / "skills" / "mine" / "SKILL.md"
    mine.parent.mkdir(parents=True)
    mine.write_text(HAND_WRITTEN, encoding="utf-8")
    notes = (target / "CLAUDE.md").read_text(encoding="utf-8")
    (target / "CLAUDE.md").write_text("## my own notes\nkeep me\n\n" + notes, encoding="utf-8")

    assert main(["--quiet", "setup", str(target), "--fresh", "--yes", "--no-graph"]) == 0

    assert (target / "app.py").read_text(encoding="utf-8") == "x = 1\n"
    assert mine.read_text(encoding="utf-8") == HAND_WRITTEN
    assert "keep me" in (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert (target / ".edify" / "skills" / "verifier.md").is_file(), "and it reinstalled after clearing"


def test_fresh_on_a_folder_with_nothing_in_it_is_not_an_error(tmp_path: Path):
    target = tmp_path / "empty"
    assert main(["--quiet", "setup", str(target), "--fresh", "--yes", "--no-graph"]) == 0
    assert (target / ".edify").is_dir()


@pytest.mark.parametrize("flag", ["--stack", "--skills", "--host", "--extractor"])
def test_setup_takes_the_same_flags_as_init(flag: str):
    """`setup` *is* `init` with the root pinned, so a flag one takes the other takes."""
    from edify.cli import build_parser

    parser = build_parser()
    setup = next(
        action for action in parser._subparsers._group_actions[0].choices.items() if action[0] == "setup"
    )[1]
    assert flag in {s for action in setup._actions for s in action.option_strings}
