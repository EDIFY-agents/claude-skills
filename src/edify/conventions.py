"""The conventions scrape. A config read, not an analysis — zero model calls.

Every convention below is already stated in a file on disk: the lint config, the
formatter, the type-checker's strictness, the editor config, the test layout, the
commit convention, and the CI job's real commands. Reading them costs a few hundred
milliseconds and nothing else.

What a scrape cannot get — where fixtures live, which patterns are finished versus
legacy, the module nobody should touch — is covered by the task format's
`Follow the pattern at` pointer, which transfers a convention more reliably than a
paragraph describing it. That is why there is no discovery pass here.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from .detect import Stack

_LINTERS = {
    ".eslintrc": "eslint",
    ".eslintrc.js": "eslint",
    ".eslintrc.cjs": "eslint",
    ".eslintrc.json": "eslint",
    ".eslintrc.yml": "eslint",
    "eslint.config.js": "eslint (flat)",
    "eslint.config.mjs": "eslint (flat)",
    "biome.json": "biome",
    ".rubocop.yml": "rubocop",
    ".golangci.yml": "golangci-lint",
    ".golangci.yaml": "golangci-lint",
    "clippy.toml": "clippy",
    ".flake8": "flake8",
    "setup.cfg": "flake8/setup.cfg",
    ".pylintrc": "pylint",
}

_FORMATTERS = {
    ".prettierrc": "prettier",
    ".prettierrc.json": "prettier",
    ".prettierrc.js": "prettier",
    "prettier.config.js": "prettier",
    ".editorconfig": "editorconfig",
    "rustfmt.toml": "rustfmt",
    ".rustfmt.toml": "rustfmt",
}


def scrape(root: Path, stack: Stack) -> str:
    """The `.edify/conventions.md` body. Roughly fifteen to twenty-five lines."""
    lines: list[str] = ["# Conventions", ""]
    lines.append(
        "Scraped from the configuration files in this repository by `edify init`. "
        "No model produced any line here. Regenerate with `edify init --force`."
    )
    lines.append("")

    facts: list[tuple[str, str]] = []

    facts.append(("Languages", ", ".join(stack.languages) or "none detected"))
    if stack.frameworks:
        facts.append(("Frameworks", ", ".join(stack.frameworks)))
    facts.append(("Package manager", stack.package_manager))
    facts.append(("Test runner", stack.test_runner))

    linters = [name for f, name in _LINTERS.items() if (root / f).is_file()]
    if linters:
        facts.append(("Lint", ", ".join(sorted(set(linters)))))
    formatters = [name for f, name in _FORMATTERS.items() if (root / f).is_file()]
    if formatters:
        facts.append(("Format", ", ".join(sorted(set(formatters)))))

    ruff = _ruff(root)
    if ruff:
        facts.append(("Ruff", ruff))
    ts = _typescript(root)
    if ts:
        facts.append(("TypeScript", ts))
    mypy = _mypy(root)
    if mypy:
        facts.append(("Type checking", mypy))
    indent = _editorconfig(root)
    if indent:
        facts.append(("Indent", indent))

    layout = _test_layout(root)
    if layout:
        facts.append(("Tests live in", layout))
    commit = _commit_convention(root)
    if commit:
        facts.append(("Commits", commit))

    for label, value in facts:
        lines.append(f"- **{label}**: {value}")

    scripts = _scripts(root)
    if scripts:
        lines.append("")
        lines.append("## Commands, as this repository actually invokes them")
        lines.append("")
        for name, command in scripts:
            lines.append(f"- `{name}` → `{command}`")

    ci = _ci_commands(root)
    if ci:
        lines.append("")
        lines.append("## What CI runs")
        lines.append("")
        for command in ci:
            lines.append(f"- `{command}`")

    lines.append("")
    lines.append(
        "Anything not listed here was not stated in a config file. It is not missing "
        "because nobody looked — it is missing because nothing on disk declares it."
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------


def _ruff(root: Path) -> str | None:
    data = _toml(root / "pyproject.toml")
    ruff = (data.get("tool") or {}).get("ruff") or {}
    if not ruff and (root / "ruff.toml").is_file():
        ruff = _toml(root / "ruff.toml")
    if not ruff:
        return None
    bits = []
    if ruff.get("line-length"):
        bits.append(f"line length {ruff['line-length']}")
    select = (ruff.get("lint") or {}).get("select") or ruff.get("select")
    if select:
        bits.append("rules " + ",".join(str(s) for s in select[:8]))
    return "; ".join(bits) or "configured"


def _typescript(root: Path) -> str | None:
    path = root / "tsconfig.json"
    if not path.is_file():
        return None
    data = _jsonc(path)
    opts = data.get("compilerOptions") or {}
    bits = []
    bits.append("strict on" if opts.get("strict") else "strict off")
    if opts.get("target"):
        bits.append(f"target {opts['target']}")
    if opts.get("noUncheckedIndexedAccess"):
        bits.append("noUncheckedIndexedAccess")
    return ", ".join(bits)


def _mypy(root: Path) -> str | None:
    data = _toml(root / "pyproject.toml")
    mypy = (data.get("tool") or {}).get("mypy") or {}
    if mypy:
        return "mypy strict" if mypy.get("strict") else "mypy"
    if (root / "mypy.ini").is_file():
        return "mypy"
    if (root / ".mypy.ini").is_file():
        return "mypy"
    return None


def _editorconfig(root: Path) -> str | None:
    path = root / ".editorconfig"
    if not path.is_file():
        return None
    style = size = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\s*indent_style\s*=\s*(\w+)", line)
        if m and style is None:
            style = m.group(1)
        m = re.match(r"\s*indent_size\s*=\s*(\w+)", line)
        if m and size is None:
            size = m.group(1)
    if not style and not size:
        return None
    return f"{style or 'unspecified'} {size or ''}".strip()


def _test_layout(root: Path) -> str | None:
    candidates = []
    for name in ("tests", "test", "spec", "__tests__", "src/test", "e2e"):
        if (root / name).is_dir():
            candidates.append(f"{name}/")
    colocated = list(root.glob("src/**/*.test.*"))[:1] or list(root.glob("src/**/*_test.go"))[:1]
    if colocated:
        candidates.append("beside the code they test")
    return ", ".join(candidates) if candidates else None


def _commit_convention(root: Path) -> str | None:
    for name in ("commitlint.config.js", ".commitlintrc", ".commitlintrc.json"):
        if (root / name).is_file():
            return "conventional commits (commitlint configured)"
    if (root / ".gitmessage").is_file():
        return "template in .gitmessage"
    return None


def _scripts(root: Path) -> list[tuple[str, str]]:
    """The build, test, lint and typecheck commands, exactly as declared."""
    wanted = ("build", "test", "lint", "typecheck", "type-check", "check", "dev", "start")
    out: list[tuple[str, str]] = []
    pkg = root / "package.json"
    if pkg.is_file():
        scripts = (_jsonc(pkg).get("scripts") or {})
        pm = _pm_prefix(root)
        for name in wanted:
            if name in scripts:
                out.append((f"{pm} run {name}", str(scripts[name])))
    makefile = root / "Makefile"
    if makefile.is_file():
        for line in makefile.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^([a-zA-Z][\w\-]*):\s*(?:[\w\- ]*)$", line)
            if m and m.group(1) in wanted:
                out.append((f"make {m.group(1)}", "see Makefile"))
    return out[:10]


def _pm_prefix(root: Path) -> str:
    for lockfile, pm in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("bun.lockb", "bun")):
        if (root / lockfile).is_file():
            return pm
    return "npm"


def _ci_commands(root: Path) -> list[str]:
    """The `run:` lines from CI workflows — the commands that actually gate a merge."""
    out: list[str] = []
    workflows = root / ".github" / "workflows"
    if workflows.is_dir():
        for path in sorted(workflows.glob("*.y*ml"))[:4]:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                m = re.match(r"\s*-?\s*run:\s*(.+)$", line)
                if m:
                    command = m.group(1).strip().strip("|>").strip()
                    if command and command not in out and len(command) < 120:
                        out.append(command)
    for name in (".gitlab-ci.yml", "Jenkinsfile", ".circleci/config.yml"):
        path = root / name
        if path.is_file():
            out.append(f"declared in {name}")
    return out[:12]


def _toml(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _jsonc(path: Path) -> dict:
    """tsconfig.json is JSON with comments often enough to be worth handling."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    text = re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    try:
        return json.loads(text) or {}
    except json.JSONDecodeError:
        return {}
