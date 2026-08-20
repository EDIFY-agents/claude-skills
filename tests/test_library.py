"""The shipped methodology tree checks itself.

Everything EDIFY asks of a customer's repository, it has to satisfy in its own: the
skill files are valid and under budget, the command files are short, the worked
examples parse against the formats they calibrate, and the default registry is
pinned and scoped.
"""

from __future__ import annotations

import pytest

from edify import assets
from edify.formats import mcp as mcp_format
from edify.formats import skill as skill_format
from edify.formats import tasks as tasks_format
from edify.formats.document import parse_document

SKILLS = sorted(assets.subtree("skills").glob("*.md"))
COMMANDS = sorted(assets.subtree("commands").glob("*.md"))


def test_the_library_is_not_empty() -> None:
    assert len(SKILLS) >= 10
    assert {p.stem for p in COMMANDS} == {"spec", "plan", "tasks", "build", "verify"}


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.stem)
def test_every_skill_is_valid_and_under_budget(path) -> None:
    skill = skill_format.parse(path, path.name)
    problems = skill_format.validate(skill)
    assert problems == [], problems
    assert skill.name == path.stem, "the filename and the `name` field have to agree"


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.stem)
def test_no_skill_commands_or_claims_an_identity(path) -> None:
    """P5: instructions explain, they do not command."""
    text = path.read_text(encoding="utf-8")
    body = text.split("---", 2)[-1]
    for banned in ("MUST ", "YOU MUST", "NEVER FORGET", "You are an expert", "As an expert"):
        assert banned not in body, f"{path.name} contains `{banned}`"


@pytest.mark.parametrize("path", COMMANDS, ids=lambda p: p.stem)
def test_every_command_file_is_short(path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 100, f"{path.name} is {len(lines)} lines; the budget is 100"


def test_every_role_has_at_least_one_entry() -> None:
    roles = {skill_format.parse(p, p.name).role for p in SKILLS}
    assert set(skill_format.ROLES) <= roles


def test_the_worked_spec_example_calibrates_tone_and_says_so(tmp_path) -> None:
    """This exemplar teaches voice, not section layout, and has to admit it.

    A reader who takes it for a format instance will write a product vision where a
    spec belongs, so the shipped copy carries a framing note pointing at
    `spec.format.md` for the contract.
    """
    source = assets.subtree("formats") / "spec.example.md"
    text = source.read_text(encoding="utf-8")
    assert "worked example for `spec.format.md`" in text
    assert "The shape\n> is what to copy, not the length" in text

    doc = parse_document(source)
    assert len(doc.sections) > 20
    assert doc.section("Core Product Rules") is not None


def test_the_worked_tasks_example_parses_completely() -> None:
    source = assets.subtree("formats") / "tasks.example.md"
    parsed = tasks_format.parse(source)

    assert len(parsed.tasks) == 16
    assert len(parsed.phases) == 8
    assert len(parsed.coverage) == 13

    for task in parsed.tasks:
        assert task.phase is not None, f"{task.id} has no phase"
        assert task.discharges, f"{task.id} discharges nothing"
        assert task.steps, f"{task.id} has no steps"
        assert task.done_when, f"{task.id} has no done-check"

    phase_two = parsed.in_phase(2)
    assert phase_two
    for task in phase_two:
        assert task.verification, f"{task.id} names no verification kinds"
        assert any("fail" in check.lower() for check in task.done_when)


def test_the_worked_tasks_example_has_no_whole_file_edits() -> None:
    parsed = tasks_format.parse(assets.subtree("formats") / "tasks.example.md")
    for task in parsed.tasks:
        for ref in task.edits:
            assert ref.has_range, f"{task.id} edits {ref.path} with no line range"


def test_the_default_registry_is_scoped() -> None:
    registry = mcp_format.parse(assets.subtree("mcp") / "default-registry.md")
    assert len(registry.servers) == 1
    docs = registry.get("docs")
    assert docs is not None
    assert docs.roles and docs.phases
    # A phase 0 foundation task loads nothing; a phase 4 implementer loads docs.
    assert not docs.scoped_to("planner", "0")
    assert docs.scoped_to("implementer", "4")


def test_the_manifest_declares_what_it_pins() -> None:
    manifest = assets.manifest()
    assert manifest["edify"]
    assert manifest["graph-schema"] == "1"
    assert manifest["extractor"] == "builtin"


def test_the_version_is_the_same_in_all_three_places() -> None:
    """`__init__`, `pyproject.toml`, and the manifest. PUBLISHING.md §2 bumps all three.

    A release where they disagree ships a wheel whose `edify version` and whose
    `pip show` are different numbers, and every governance row it writes is stamped
    with the wrong one.
    """
    import re
    from pathlib import Path

    from edify import __version__

    root = Path(__file__).resolve().parent.parent
    declared = re.search(r'^version = "([^"]+)"', (root / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    assert declared, "pyproject.toml has no version"
    assert declared.group(1) == __version__
    assert assets.manifest()["edify"] == __version__
