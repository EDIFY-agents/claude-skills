"""Stack detection reads manifests, not directory names.

A framework is detected because its name is in a dependency list. What is not
declared is not detected, and `init` says so rather than inferring it.
"""

from __future__ import annotations

from pathlib import Path

from edify.detect import declared_packages, detect


def test_the_fixture_stack_is_read_from_its_manifests(repo: Path) -> None:
    stack = detect(repo)
    assert "typescript" in stack.languages
    assert "python" in stack.languages
    assert set(stack.frameworks) == {"express", "postgres"}
    assert stack.package_manager == "npm"
    assert stack.test_runner == "vitest"
    assert "package.json" in stack.manifests


def test_a_single_file_project_keeps_its_only_language(tmp_path: Path) -> None:
    """A small repository must not lose the language it is written in."""
    root = tmp_path / "small"
    (root / "src").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = ["fastapi"]\n', encoding="utf-8"
    )
    (root / "src" / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")

    stack = detect(root)
    assert stack.languages == ["python"]
    assert stack.frameworks == ["fastapi"]


def test_one_stray_script_does_not_become_a_language(tmp_path: Path) -> None:
    """The inverse: a lone helper in a large tree must not add a stack entry."""
    root = tmp_path / "big"
    (root / "src").mkdir(parents=True)
    for i in range(30):
        (root / "src" / f"mod{i}.ts").write_text("export const x = 1;\n", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "release.rb").write_text("puts 'hi'\n", encoding="utf-8")

    stack = detect(root)
    assert stack.languages == ["typescript"]
    assert "ruby" not in stack.languages


def test_packages_are_declared_not_imported(repo: Path) -> None:
    """An import of something no manifest names is a fact about code, not a package."""
    (repo / "src" / "sneaky.ts").write_text(
        "import lodash from 'lodash';\nexport const x = lodash;\n", encoding="utf-8"
    )
    declared = declared_packages(repo)
    assert "express" in declared
    assert "lodash" not in declared


def test_nothing_declared_means_nothing_detected(tmp_path: Path) -> None:
    root = tmp_path / "bare"
    root.mkdir()
    (root / "notes.txt").write_text("no code here\n", encoding="utf-8")

    stack = detect(root)
    assert stack.languages == []
    assert stack.frameworks == []
    assert stack.package_manager == "-"
    assert stack.test_runner == "-"
