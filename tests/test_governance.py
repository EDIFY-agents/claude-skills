"""Every file EDIFY installs is recorded, and the record can be checked.

The claim under test is the one `docs/design/01-principles.md` P7 makes: a control counts
as governance if a person can look at it and tell whether the work complied. So the
ledger has to cover the whole installed surface — not just the skill files, which
were the only ones carrying provenance before — and `verify` has to tell the
difference between a file EDIFY owns being changed and a file the repository owns
being maintained.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from edify import governance
from edify.cli import main
from edify.paths import Layout


def run(repo: Path, *args: str) -> int:
    return main(["--repo", str(repo), *args])


def test_init_records_every_file_it_installed(installed: Path) -> None:
    layout = Layout(installed)
    assert layout.governance.is_file()

    recorded = {r.path for r in governance.load(layout)}
    expected = {
        ".edify/skills/planner.md",
        ".edify/commands/spec.md",
        ".edify/formats/tasks.example.md",
        ".edify/mcp.md",
        ".edify/conventions.md",
        ".claude/commands/spec.md",
        "CLAUDE.md",
    }
    assert expected <= recorded


def test_every_record_carries_an_origin_a_licence_and_a_hash(installed: Path) -> None:
    for record in governance.load(Layout(installed)):
        assert record.origin in governance.ORIGINS
        assert record.edify
        assert record.source
        # CLAUDE.md is the one file EDIFY does not own outright, so it is the one
        # file with no hash. Everything else is hashed at the moment it lands.
        if record.kind == "instructions":
            assert record.sha256 == "-"
        else:
            assert len(record.sha256) == 64
            assert record.license != "-" or record.origin == "scraped"


def test_a_fresh_install_verifies_clean(installed: Path) -> None:
    assert governance.verify(Layout(installed)) == []
    assert run(installed, "governance", "verify", "--exit-code") == 0


def test_a_changed_library_file_is_reported_as_modified(installed: Path) -> None:
    layout = Layout(installed)
    skill = layout.skills_dir / "planner.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "\nand also do this\n", encoding="utf-8")

    problems = {p.path: p for p in governance.verify(layout)}
    assert problems[".edify/skills/planner.md"].state == "modified"
    assert problems[".edify/skills/planner.md"].serious
    assert run(installed, "governance", "verify", "--exit-code") == 2


def test_editing_the_registry_is_not_a_violation(installed: Path) -> None:
    """`.edify/mcp.md` is seeded once and then the repository's to maintain."""
    layout = Layout(installed)
    layout.mcp.write_text(layout.mcp.read_text(encoding="utf-8") + "\na note\n", encoding="utf-8")

    problems = {p.path: p for p in governance.verify(layout)}
    assert problems[".edify/mcp.md"].state == "edited"
    assert not problems[".edify/mcp.md"].serious
    assert run(installed, "governance", "verify", "--exit-code") == 0


def test_a_deleted_file_and_an_unrecorded_one_are_both_reported(installed: Path) -> None:
    layout = Layout(installed)
    (layout.commands_dir / "spec.md").unlink()
    stranger = layout.skills_dir / "stranger.md"
    stranger.write_text(
        "---\nname: stranger\ndescription: from somewhere else\nkind: skill\nrole: implementer\n"
        "phase: 4\ntech: any\nprovenance: client\n---\n\nbody\n",
        encoding="utf-8",
    )

    states = {p.path: p.state for p in governance.verify(layout)}
    assert states[".edify/commands/spec.md"] == "missing"
    assert states[".edify/skills/stranger.md"] == "unrecorded"


def test_rebuild_re_baselines_a_deliberate_change(installed: Path) -> None:
    layout = Layout(installed)
    skill = layout.skills_dir / "verifier.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "\nour own addition\n", encoding="utf-8")
    assert governance.verify(layout)

    assert run(installed, "--quiet", "governance", "rebuild") == 0
    assert governance.verify(layout) == []


def test_skills_add_lands_in_the_ledger(installed: Path, tmp_path: Path) -> None:
    entry = tmp_path / "client-rule.md"
    entry.write_text(
        "---\nname: client-rule\ndescription: a rule this client needs.\nkind: skill\n"
        "role: implementer\nphase: 4\ntech: any\nprovenance: client\n---\n\nDo the thing.\n",
        encoding="utf-8",
    )
    assert run(installed, "--quiet", "skills", "add", str(entry)) == 0

    recorded = {r.path: r for r in governance.load(Layout(installed))}
    assert recorded[".edify/skills/client-rule.md"].provenance == "client"
    assert governance.verify(Layout(installed)) == []


def test_the_graph_is_deliberately_not_governed(installed: Path) -> None:
    """It is regenerated output with its own checksums, and it changes every build."""
    recorded = {r.path for r in governance.load(Layout(installed))}
    assert not [p for p in recorded if p.startswith(".edify/graph/")]

    assert run(installed, "--quiet", "graph", "build") == 0
    assert governance.verify(Layout(installed)) == []


def test_list_is_machine_readable(capsys: pytest.CaptureFixture[str], installed: Path) -> None:
    assert main(["--repo", str(installed), "--json", "governance", "list"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) > 20
    assert {"path", "kind", "origin", "provenance", "license", "source", "sha256"} <= set(payload[0])


def test_doctor_reports_governance(capsys: pytest.CaptureFixture[str], installed: Path) -> None:
    assert run(installed, "doctor") == 0
    assert "governance" in capsys.readouterr().out
