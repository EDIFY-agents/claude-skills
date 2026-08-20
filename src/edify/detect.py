"""Stack detection, from the manifest files that are actually present.

`edify init` step 1. No model call and no guessing: a framework is detected because
its name is in a dependency list, not because a directory is called `api`. What is
not detected is simply absent, and `init` says so.
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .graph.ignore import IgnoreRules
from .graph.langs import EXTENSIONS

# dependency name → the `tech` id used in skill frontmatter. Exact match on the
# declared name, because a substring match calls every repo with `react-scripts`
# a React repo.
FRAMEWORK_BY_DEP = {
    "react": "react",
    "react-dom": "react",
    "next": "nextjs",
    "vue": "vue",
    "nuxt": "vue",
    "svelte": "svelte",
    "@angular/core": "angular",
    "express": "express",
    "fastify": "fastify",
    "@nestjs/core": "nestjs",
    "koa": "express",
    "hono": "express",
    "prisma": "prisma",
    "@prisma/client": "prisma",
    "typeorm": "typeorm",
    "drizzle-orm": "drizzle",
    "pg": "postgres",
    "postgres": "postgres",
    "mysql2": "mysql",
    "mongoose": "mongodb",
    "redis": "redis",
    "django": "django",
    "flask": "flask",
    "fastapi": "fastapi",
    "sqlalchemy": "sqlalchemy",
    "psycopg": "postgres",
    "psycopg2": "postgres",
    "psycopg2-binary": "postgres",
    "asyncpg": "postgres",
    "pydantic": "pydantic",
    "celery": "celery",
    "boto3": "aws",
    "rails": "rails",
    "sinatra": "rails",
    "laravel/framework": "laravel",
    "symfony/framework-bundle": "symfony",
    "gin-gonic/gin": "gin",
    "labstack/echo": "echo",
    "spring-boot-starter-web": "spring",
    "actix-web": "actix",
    "axum": "axum",
    "tokio": "tokio",
}

TEST_RUNNER_BY_DEP = {
    "jest": "jest",
    "vitest": "vitest",
    "mocha": "mocha",
    "@playwright/test": "playwright",
    "cypress": "cypress",
    "ava": "ava",
    "pytest": "pytest",
    "unittest2": "unittest",
    "nose2": "nose2",
    "rspec": "rspec",
    "phpunit/phpunit": "phpunit",
    "junit": "junit",
}


@dataclass
class Stack:
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    package_manager: str = "-"
    test_runner: str = "-"
    manifests: list[str] = field(default_factory=list)
    file_counts: dict[str, int] = field(default_factory=dict)

    @property
    def tech(self) -> list[str]:
        """The ids a skill's `tech` field is matched against."""
        return sorted(set(self.languages) | set(self.frameworks))

    def as_dict(self) -> dict[str, object]:
        return {
            "languages": self.languages,
            "frameworks": self.frameworks,
            "package_manager": self.package_manager,
            "test_runner": self.test_runner,
            "manifests": self.manifests,
            "file_counts": self.file_counts,
        }


def detect(root: Path) -> Stack:
    stack = Stack()
    stack.file_counts = _census(root)
    stack.languages = _languages(stack.file_counts)

    frameworks: set[str] = set()
    for name, manifest in declared_packages(root).items():
        if manifest not in stack.manifests:
            stack.manifests.append(manifest)
        tech = FRAMEWORK_BY_DEP.get(name)
        if tech:
            frameworks.add(tech)
        runner = TEST_RUNNER_BY_DEP.get(name)
        if runner and stack.test_runner == "-":
            stack.test_runner = runner
    stack.frameworks = sorted(frameworks)
    stack.manifests.sort()

    stack.package_manager = _package_manager(root)
    if stack.test_runner == "-":
        stack.test_runner = _fallback_runner(root, stack.languages)
    return stack


def declared_packages(root: Path) -> dict[str, str]:
    """Declared dependency name → the manifest that declares it.

    Declared, not imported. An import of something no manifest names is a fact
    about the code and belongs in an edge, not in a package node.
    """
    out: dict[str, str] = {}

    pkg = root / "package.json"
    if pkg.is_file():
        data = _json(pkg)
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            for name in (data.get(section) or {}):
                out.setdefault(str(name), "package.json")

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        data = _toml(pyproject)
        project = data.get("project") or {}
        for entry in project.get("dependencies") or []:
            out.setdefault(_pep508_name(str(entry)), "pyproject.toml")
        for group in (project.get("optional-dependencies") or {}).values():
            for entry in group:
                out.setdefault(_pep508_name(str(entry)), "pyproject.toml")
        poetry = ((data.get("tool") or {}).get("poetry") or {}).get("dependencies") or {}
        for name in poetry:
            if name != "python":
                out.setdefault(str(name).lower(), "pyproject.toml")

    for req in ("requirements.txt", "requirements-dev.txt", "requirements/base.txt"):
        path = root / req
        if path.is_file():
            for line in _lines(path):
                line = line.split("#", 1)[0].strip()
                if line and not line.startswith("-"):
                    out.setdefault(_pep508_name(line), req)

    gomod = root / "go.mod"
    if gomod.is_file():
        for line in _lines(gomod):
            m = re.match(r"^\s*(?:require\s+)?([a-z0-9./\-]+\.[a-z]{2,}/[\w./\-]+)\s+v", line)
            if m:
                path = m.group(1)
                out.setdefault("/".join(path.split("/")[-2:]), "go.mod")

    cargo = root / "Cargo.toml"
    if cargo.is_file():
        data = _toml(cargo)
        for section in ("dependencies", "dev-dependencies", "build-dependencies"):
            for name in (data.get(section) or {}):
                out.setdefault(str(name), "Cargo.toml")

    gemfile = root / "Gemfile"
    if gemfile.is_file():
        for line in _lines(gemfile):
            m = re.match(r"""^\s*gem\s+['"]([^'"]+)['"]""", line)
            if m:
                out.setdefault(m.group(1), "Gemfile")

    composer = root / "composer.json"
    if composer.is_file():
        data = _json(composer)
        for section in ("require", "require-dev"):
            for name in (data.get(section) or {}):
                out.setdefault(str(name), "composer.json")

    for gradle in ("build.gradle", "build.gradle.kts"):
        path = root / gradle
        if path.is_file():
            for line in _lines(path):
                m = re.search(r"""['"]([\w.\-]+):([\w.\-]+):[\w.\-+]+['"]""", line)
                if m:
                    out.setdefault(m.group(2), gradle)

    pom = root / "pom.xml"
    if pom.is_file():
        text = pom.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"<artifactId>([\w.\-]+)</artifactId>", text):
            out.setdefault(m.group(1), "pom.xml")

    return out


# ---------------------------------------------------------------------------


def _languages(counts: dict[str, int]) -> list[str]:
    """Which languages this repository is actually written in.

    Two files, or a fifth of the source tree. The proportional half is what keeps a
    small repository from losing its only language; the absolute half is what keeps
    one stray script in a large repository from adding a language — and a skill file
    — that nobody works in.
    """
    total = sum(counts.values())
    if not total:
        return []
    kept = [
        lang
        for lang, count in counts.items()
        if count >= 2 or count / total >= 0.2
    ]
    return sorted(kept, key=lambda lang: (-counts[lang], lang))[:8]


def _census(root: Path) -> dict[str, int]:
    rules = IgnoreRules(root)
    counts: dict[str, int] = {}
    import os

    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        rel_dir = here.relative_to(root).as_posix()
        dirnames[:] = [
            d for d in dirnames if not rules.skip_dir(d, d if rel_dir == "." else f"{rel_dir}/{d}")
        ]
        for name in filenames:
            language = EXTENSIONS.get(Path(name).suffix.lower())
            if language and language != "markdown":
                counts[language] = counts.get(language, 0) + 1
    return counts


def _package_manager(root: Path) -> str:
    for lockfile, name in (
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("bun.lockb", "bun"),
        ("package-lock.json", "npm"),
        ("uv.lock", "uv"),
        ("poetry.lock", "poetry"),
        ("Pipfile.lock", "pipenv"),
        ("go.sum", "go"),
        ("Cargo.lock", "cargo"),
        ("Gemfile.lock", "bundler"),
        ("composer.lock", "composer"),
    ):
        if (root / lockfile).is_file():
            return name
    if (root / "requirements.txt").is_file():
        return "pip"
    if (root / "package.json").is_file():
        return "npm"
    return "-"


def _fallback_runner(root: Path, languages: list[str]) -> str:
    if (root / "pytest.ini").is_file() or (root / "conftest.py").is_file():
        return "pytest"
    if "go" in languages:
        return "go test"
    if "rust" in languages:
        return "cargo test"
    if "python" in languages:
        return "pytest"
    return "-"


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace")) or {}
    except (OSError, json.JSONDecodeError):
        return {}


def _toml(path: Path) -> dict:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _pep508_name(spec: str) -> str:
    return re.split(r"[\[<>=!~;\s]", spec.strip(), maxsplit=1)[0].strip().lower()
