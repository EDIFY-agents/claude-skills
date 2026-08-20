"""The CLI end to end: init, the queries, resolution, scoping, doctor, check."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from edify import skills as skills_index
from edify.cli import main
from edify.paths import Layout


def run(repo: Path, *args: str) -> int:
    return main(["--repo", str(repo), *args])


def run_json(capsys: pytest.CaptureFixture[str], repo: Path, *args: str):
    code = main(["--repo", str(repo), "--json", *args])
    out = capsys.readouterr().out
    return code, json.loads(out) if out.strip() else None


# -- init ------------------------------------------------------------------


def test_init_writes_the_installed_tree(installed: Path) -> None:
    layout = Layout(installed)
    assert layout.nodes.is_file()
    assert layout.edges.is_file()
    assert layout.meta.is_file()
    assert layout.skills_index.is_file()
    assert layout.mcp.is_file()
    assert layout.conventions.is_file()
    assert layout.claude_md.is_file()
    assert (layout.commands_dir / "spec.md").is_file()
    assert (layout.formats_dir / "tasks.example.md").is_file()


def test_init_installs_an_entry_for_every_part_of_the_stack(installed: Path) -> None:
    names = {p.stem for p in Layout(installed).skills_dir.glob("*.md")}
    # The fixture is genuinely polyglot — TypeScript, Python, SQL, express, postgres.
    assert {"implementer-node", "implementer-postgres", "implementer-python"} <= names
    # Nothing in it is Go or React, so neither entry is installed.
    assert "implementer-go" not in names
    assert "implementer-react" not in names
    # Every repository needs the role entries that apply regardless of stack.
    assert {"planner", "adversary", "verifier", "debugger"} <= names


def test_a_single_stack_repository_gets_only_its_own_entries(tmp_path: Path) -> None:
    """A Python API repository does not receive the React implementer.

    Every unused skill file is context cost and, for anything sourced from outside,
    attack surface.
    """
    root = tmp_path / "api"
    (root / "app").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "api"\ndependencies = ["fastapi", "sqlalchemy"]\n', encoding="utf-8"
    )
    for name in ("main", "models", "routes"):
        (root / "app" / f"{name}.py").write_text("def f():\n    return 1\n", encoding="utf-8")

    assert run(root, "--quiet", "init") == 0
    names = {p.stem for p in Layout(root).skills_dir.glob("*.md")}
    assert "implementer-python" in names
    assert names.isdisjoint({"implementer-node", "implementer-react", "implementer-go"})


def test_claude_md_is_short_and_points_at_the_graph(installed: Path) -> None:
    text = Layout(installed).claude_md.read_text(encoding="utf-8")
    assert ".edify/graph/" in text
    assert "edify graph where" in text
    body = [line for line in text.splitlines() if line.strip() and not line.startswith("<!--")]
    assert len(body) <= 20


def test_init_merges_into_an_existing_instruction_file(repo: Path) -> None:
    (repo / "CLAUDE.md").write_text("# Our house rules\nSomebody wrote this on purpose.\n", encoding="utf-8")
    assert run(repo, "--quiet", "init") == 0

    text = (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Our house rules" in text
    assert "Somebody wrote this on purpose." in text
    assert ".edify/graph/" in text


def test_re_running_init_replaces_only_the_edify_block(repo: Path) -> None:
    (repo / "CLAUDE.md").write_text("# Ours\nkeep me\n", encoding="utf-8")
    run(repo, "--quiet", "init")
    first = (repo / "CLAUDE.md").read_text(encoding="utf-8")
    run(repo, "--quiet", "init", "--force")
    second = (repo / "CLAUDE.md").read_text(encoding="utf-8")

    assert second.count("<!-- edify:begin -->") == 1
    assert "keep me" in second
    assert first.count("<!-- edify:begin -->") == 1


def test_init_writes_host_command_pointers(installed: Path) -> None:
    pointer = installed / ".claude" / "commands" / "spec.md"
    assert pointer.is_file()
    text = pointer.read_text(encoding="utf-8")
    assert ".edify/commands/spec.md" in text
    # A pointer carries no methodology, so it cannot go stale.
    assert len(text.splitlines()) < 10


def test_conventions_are_scraped_from_the_config_files(installed: Path) -> None:
    text = Layout(installed).conventions.read_text(encoding="utf-8")
    assert "vitest" in text
    assert "strict on" in text
    assert "npm run test" in text
    assert "No model produced any line here" in text


# -- queries ---------------------------------------------------------------


def test_graph_where_prints_a_file_and_line(capsys: pytest.CaptureFixture[str], installed: Path) -> None:
    assert run(installed, "graph", "where", "generate") == 0
    assert "src/auth/tokens.ts:3" in capsys.readouterr().out


def test_graph_where_reports_a_miss_without_inventing_one(
    capsys: pytest.CaptureFixture[str], installed: Path
) -> None:
    assert run(installed, "graph", "where", "definitelyNotHere") == 1
    assert "nothing named" in capsys.readouterr().out


def test_json_output_is_machine_readable(capsys: pytest.CaptureFixture[str], installed: Path) -> None:
    code, payload = run_json(capsys, installed, "graph", "where", "MemberService")
    assert code == 0
    assert payload[0]["file"] == "src/api/members.ts"
    assert payload[0]["kind"] == "symbol"


def test_overlap_exits_non_zero_when_sets_intersect(installed: Path) -> None:
    assert run(installed, "graph", "overlap", "src/auth/tokens.ts", "src/api/members.ts") == 1
    assert run(installed, "graph", "overlap", "src/tools.py", "src/api/router.ts") == 0


# -- resolution and scoping ------------------------------------------------


def test_skills_resolve_returns_one_path(capsys: pytest.CaptureFixture[str], installed: Path) -> None:
    assert run(installed, "skills", "resolve", "implementer", "4") == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1
    assert out[0].endswith(".md")


def test_resolution_prefers_the_stack_then_any(installed: Path) -> None:
    layout = Layout(installed)
    assert skills_index.resolve(layout, "implementer", "4", "typescript").name == "implementer-node"
    assert skills_index.resolve(layout, "implementer", "4", "cobol").name == "implementer-general"
    assert skills_index.resolve(layout, "verifier", "7").name == "verifier"


def test_a_role_with_no_skill_fails_rather_than_guessing(installed: Path) -> None:
    from edify.errors import EdifyError

    with pytest.raises(EdifyError):
        skills_index.resolve(Layout(installed), "archaeologist", "3")


def test_mcp_scoping_is_exact(capsys: pytest.CaptureFixture[str], installed: Path) -> None:
    assert run(installed, "mcp", "for", "implementer", "4") == 0
    assert "docs" in capsys.readouterr().out

    assert run(installed, "mcp", "for", "planner", "0") == 0
    assert "none" in capsys.readouterr().out


# -- check and doctor ------------------------------------------------------


def test_check_on_a_fresh_install_reports_nothing(
    capsys: pytest.CaptureFixture[str], installed: Path
) -> None:
    assert run(installed, "check") == 0
    assert "0 errors" in capsys.readouterr().out


def test_check_never_blocks_unless_asked(installed: Path) -> None:
    feature = installed / "specs" / "broken"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# spec — broken\n\nnothing here\n", encoding="utf-8")

    assert run(installed, "check") == 0                 # reports, does not block
    assert run(installed, "check", "--exit-code") == 2  # the customer's own gate


def test_doctor_reports_each_part(capsys: pytest.CaptureFixture[str], installed: Path) -> None:
    assert run(installed, "doctor") == 0
    out = capsys.readouterr().out
    for part in ("install", "extractor", "graph", "skills", "CLAUDE.md", "license"):
        assert part in out


def test_doctor_is_red_before_init(capsys: pytest.CaptureFixture[str], repo: Path) -> None:
    assert run(repo, "doctor") == 1
    assert "edify init" in capsys.readouterr().out


def test_a_command_needing_the_graph_says_so_before_init(
    capsys: pytest.CaptureFixture[str], repo: Path
) -> None:
    assert run(repo, "graph", "where", "generate") == 4
    assert "edify graph build" in capsys.readouterr().err


def test_upgrade_is_declined_on_the_free_plan(capsys: pytest.CaptureFixture[str], installed: Path) -> None:
    assert run(installed, "upgrade", "--check") == 7
    err = capsys.readouterr().err
    assert "pro plan" in err
    # A gate names the price and both doors — buying one, and activating a token
    # somebody already has. Neither is useful without the other.
    assert "$20 per user per month" in err
    assert "edify license buy" in err
    assert "edify license activate" in err


def test_version_needs_no_repository(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main(["--repo", str(tmp_path), "version"]) == 0
    assert "edify" in capsys.readouterr().out
