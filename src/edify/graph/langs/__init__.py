"""Per-language extraction.

Two backends ship. `python_ast` parses with the standard library's syntax tree and
is exact. `patterns` is a declarative line scanner covering the rest, and it is
honest about being a scanner: `meta.method_<lang>` records which one produced a
language's nodes, so nobody mistakes a scan for a parse.

A third backend, `ctags`, wraps a pinned external extractor when one is installed.
Whichever runs, the output is the same TSV contract — the contract is the asset.
"""

from __future__ import annotations

from pathlib import Path

from ..model import Extraction
from . import markdown, patterns, python_ast, sqlish

# extension → language id. A language absent from this table produces a file node
# and nothing else, which is the visible-gap behaviour the design requires.
EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".vue": "vue",
    ".svelte": "svelte",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".cs": "csharp",
    ".swift": "swift",
    ".rb": "ruby",
    ".php": "php",
    ".sql": "sql",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".m": "objc",
    ".scala": "scala",
    ".dart": "dart",
    ".lua": "lua",
    ".ex": "elixir",
    ".exs": "elixir",
    ".sh": "shell",
    ".bash": "shell",
    ".md": "markdown",
    ".markdown": "markdown",
}

# Which backend owns which language. Everything not listed falls to `patterns`.
_EXACT = {"python": "ast", "markdown": "structural", "sql": "structural"}


def language_for(path: Path) -> str | None:
    return EXTENSIONS.get(path.suffix.lower())


def method_for(language: str) -> str:
    """`ast`, `structural`, or `scan` — recorded in meta so the gap is visible."""
    if language in _EXACT:
        return _EXACT[language]
    if language in patterns.RULES:
        return "scan"
    return "none"


def extract_file(rel_path: str, source: str, language: str) -> Extraction:
    """Run the right backend over one file's text."""
    if language == "python":
        return python_ast.extract(rel_path, source)
    if language == "markdown":
        return markdown.extract(rel_path, source)
    if language == "sql":
        return sqlish.extract(rel_path, source)
    return patterns.extract(rel_path, source, language)


def covered_languages() -> list[str]:
    covered = set(_EXACT) | set(patterns.RULES)
    return sorted(covered)
