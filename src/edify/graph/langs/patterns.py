"""The declarative line scanner.

One rule table per language, matched line by line with comment lines skipped. It
is a scanner, not a parser, and `meta` records that: a language extracted here is
marked `scan`, and `edify doctor` says what that costs. Install a pinned external
extractor (`--extractor ctags`) or the tree-sitter extra when a language needs
parse-grade precision.

A rule that would need to look at more than one line does not belong here. The
honest failure of a scanner is a missing symbol, and a missing symbol is visible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..model import Edge, Extraction, Node, fingerprint, node_id


@dataclass(frozen=True)
class Rule:
    """One line pattern that yields one node."""

    pattern: re.Pattern[str]
    kind: str = "symbol"           # symbol | route | table
    name_group: str = "name"
    method_group: str | None = None  # for routes: the HTTP verb


@dataclass(frozen=True)
class LangRules:
    rules: tuple[Rule, ...]
    imports: tuple[re.Pattern[str], ...] = ()
    line_comment: tuple[str, ...] = ("//",)
    block_comment: tuple[str, str] | None = ("/*", "*/")


_ID = r"[A-Za-z_$][A-Za-z0-9_$]*"

# --------------------------------------------------------------------------
# JavaScript / TypeScript
# --------------------------------------------------------------------------

_JSTS = LangRules(
    rules=(
        Rule(re.compile(rf"^\s*export\s+(?:default\s+)?(?:async\s+)?function\s*\*?\s*(?P<name>{_ID})")),
        Rule(re.compile(rf"^\s*export\s+(?:abstract\s+)?class\s+(?P<name>{_ID})")),
        Rule(re.compile(rf"^\s*export\s+(?:declare\s+)?(?:const|let|var)\s+(?P<name>{_ID})")),
        Rule(re.compile(rf"^\s*export\s+(?:declare\s+)?(?:interface|type|enum)\s+(?P<name>{_ID})")),
        Rule(re.compile(rf"^\s*export\s+default\s+class\s+(?P<name>{_ID})")),
        Rule(re.compile(rf"^\s*module\.exports\.(?P<name>{_ID})\s*=")),
        Rule(re.compile(rf"^\s*exports\.(?P<name>{_ID})\s*=")),
        Rule(
            re.compile(
                rf"(?:app|router|api|server|route)\s*\.\s*(?P<method>get|post|put|patch|delete|head|options|all|use)"
                r"\s*\(\s*['\"`](?P<name>[^'\"`]+)['\"`]"
            ),
            kind="route",
            method_group="method",
        ),
    ),
    imports=(
        re.compile(r"""^\s*import\s+(?:[^'"]*\s+from\s+)?['"](?P<mod>[^'"]+)['"]"""),
        re.compile(r"""^\s*export\s+[^'"]*\s+from\s+['"](?P<mod>[^'"]+)['"]"""),
        re.compile(r"""require\(\s*['"](?P<mod>[^'"]+)['"]\s*\)"""),
    ),
)

# --------------------------------------------------------------------------
# Go
# --------------------------------------------------------------------------

_GO = LangRules(
    rules=(
        Rule(re.compile(r"^func\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")),
        Rule(re.compile(r"^func\s+\([^)]*\)\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")),
        Rule(re.compile(r"^type\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+(?:struct|interface|func|\[|map|chan|\*?[A-Za-z])")),
        Rule(re.compile(r"^(?:const|var)\s+(?P<name>[A-Z][A-Za-z0-9_]*)\s")),
        Rule(
            re.compile(
                r"""\.\s*(?P<method>Get|Post|Put|Patch|Delete|Head|Handle|HandleFunc)\s*\(\s*"(?P<name>[^"]+)\""""
            ),
            kind="route",
            method_group="method",
        ),
    ),
    imports=(re.compile(r"""^\s*(?:[A-Za-z_.]+\s+)?"(?P<mod>[^"]+)"\s*$"""),),
)

# --------------------------------------------------------------------------
# Rust
# --------------------------------------------------------------------------

_RUST = LangRules(
    rules=(
        Rule(re.compile(r"^\s*pub(?:\([^)]*\))?\s+(?:async\s+)?(?:unsafe\s+)?fn\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)")),
        Rule(re.compile(r"^\s*pub(?:\([^)]*\))?\s+(?:struct|enum|trait|union)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)")),
        Rule(re.compile(r"^\s*pub(?:\([^)]*\))?\s+(?:const|static)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)")),
        Rule(re.compile(r"^\s*pub(?:\([^)]*\))?\s+type\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)")),
        Rule(re.compile(r"^\s*(?:pub\s+)?mod\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)")),
    ),
    imports=(re.compile(r"^\s*use\s+(?P<mod>[A-Za-z_][A-Za-z0-9_:]*)"),),
)

# --------------------------------------------------------------------------
# JVM and .NET family — Java, Kotlin, C#, Scala, Swift, Dart
# --------------------------------------------------------------------------

_JVM = LangRules(
    rules=(
        Rule(
            re.compile(
                r"^\s*(?:public|internal|open|sealed|abstract|final|data|static|\s)*"
                r"(?:class|interface|enum|record|struct|object|trait|protocol|actor)\s+"
                r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
            )
        ),
        Rule(
            re.compile(
                r"^\s*(?:public|internal|open|override|suspend|static|final|async|\s)+"
                r"(?:[A-Za-z_][A-Za-z0-9_<>,\[\]\.\?]*\s+)?"
                r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*[{:]"
            )
        ),
        Rule(re.compile(r"^\s*(?:public\s+|internal\s+)?fun\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")),
        Rule(re.compile(r"^\s*(?:public\s+)?func\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")),
        Rule(
            re.compile(
                r"""@(?P<method>Get|Post|Put|Patch|Delete|Request)Mapping\s*\(\s*(?:value\s*=\s*)?["'](?P<name>[^"']+)["']"""
            ),
            kind="route",
            method_group="method",
        ),
        Rule(
            re.compile(
                r"""\[Http(?P<method>Get|Post|Put|Patch|Delete)\s*\(\s*["'](?P<name>[^"']+)["']"""
            ),
            kind="route",
            method_group="method",
        ),
    ),
    imports=(
        re.compile(r"^\s*import\s+(?:static\s+)?(?P<mod>[A-Za-z_][A-Za-z0-9_.]*)"),
        re.compile(r"^\s*using\s+(?P<mod>[A-Za-z_][A-Za-z0-9_.]*)\s*;"),
    ),
)

# --------------------------------------------------------------------------
# Ruby / PHP / Elixir / Lua / shell — declaration keywords, one per line
# --------------------------------------------------------------------------

_RUBY = LangRules(
    rules=(
        Rule(re.compile(r"^\s*(?:class|module)\s+(?P<name>[A-Z][A-Za-z0-9_:]*)")),
        Rule(re.compile(r"^\s*def\s+(?P<name>[a-zA-Z_][A-Za-z0-9_?!.]*)")),
        Rule(
            re.compile(
                r"""^\s*(?P<method>get|post|put|patch|delete|resources?)\s+['"](?P<name>[^'"]+)['"]"""
            ),
            kind="route",
            method_group="method",
        ),
    ),
    imports=(re.compile(r"""^\s*require(?:_relative)?\s+['"](?P<mod>[^'"]+)['"]"""),),
    line_comment=("#",),
    block_comment=None,
)

_PHP = LangRules(
    rules=(
        Rule(re.compile(r"^\s*(?:abstract\s+|final\s+)?(?:class|interface|trait|enum)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)")),
        Rule(re.compile(r"^\s*(?:public\s+|private\s+|protected\s+|static\s+)*function\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")),
        Rule(
            re.compile(
                r"""Route::(?P<method>get|post|put|patch|delete|any)\s*\(\s*['"](?P<name>[^'"]+)['"]"""
            ),
            kind="route",
            method_group="method",
        ),
    ),
    imports=(re.compile(r"^\s*use\s+(?P<mod>[A-Za-z_\\][A-Za-z0-9_\\]*)"),),
    line_comment=("//", "#"),
)

_ELIXIR = LangRules(
    rules=(
        Rule(re.compile(r"^\s*defmodule\s+(?P<name>[A-Z][A-Za-z0-9_.]*)")),
        Rule(re.compile(r"^\s*def(?:p)?\s+(?P<name>[a-z_][A-Za-z0-9_?!]*)")),
        Rule(
            re.compile(r"""^\s*(?P<method>get|post|put|patch|delete)\s+"(?P<name>[^"]+)\""""),
            kind="route",
            method_group="method",
        ),
    ),
    imports=(re.compile(r"^\s*(?:import|alias|use)\s+(?P<mod>[A-Z][A-Za-z0-9_.]*)"),),
    line_comment=("#",),
    block_comment=None,
)

_LUA = LangRules(
    rules=(Rule(re.compile(r"^\s*(?:local\s+)?function\s+(?P<name>[A-Za-z_][A-Za-z0-9_.:]*)")),),
    imports=(re.compile(r"""require\s*\(?\s*['"](?P<mod>[^'"]+)['"]"""),),
    line_comment=("--",),
    block_comment=None,
)

_SHELL = LangRules(
    rules=(
        Rule(re.compile(r"^\s*(?:function\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(\s*\)\s*\{")),
    ),
    line_comment=("#",),
    block_comment=None,
)

_C = LangRules(
    rules=(
        Rule(re.compile(r"^\s*(?:typedef\s+)?(?:struct|enum|union)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\{")),
        Rule(
            re.compile(
                r"^[A-Za-z_][A-Za-z0-9_\s\*]*?\b(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*\{"
            )
        ),
        Rule(re.compile(r"^\s*#define\s+(?P<name>[A-Z_][A-Z0-9_]*)")),
    ),
    imports=(re.compile(r'^\s*#include\s+[<"](?P<mod>[^>"]+)[>"]'),),
)

RULES: dict[str, LangRules] = {
    "javascript": _JSTS,
    "typescript": _JSTS,
    "vue": _JSTS,
    "svelte": _JSTS,
    "go": _GO,
    "rust": _RUST,
    "java": _JVM,
    "kotlin": _JVM,
    "csharp": _JVM,
    "scala": _JVM,
    "swift": _JVM,
    "dart": _JVM,
    "objc": _C,
    "ruby": _RUBY,
    "php": _PHP,
    "elixir": _ELIXIR,
    "lua": _LUA,
    "shell": _SHELL,
    "c": _C,
    "cpp": _C,
}


def extract(rel_path: str, source: str, language: str) -> Extraction:
    out = Extraction(languages={language})
    spec = RULES.get(language)
    if spec is None:
        return out

    file_id = node_id("file", rel_path, ".")
    module_id = node_id("module", rel_path, ".")
    module_name = _module_name(rel_path)
    out.nodes.append(Node(module_id, "module", rel_path, 1, module_name))
    out.edges.append(Edge(file_id, "defines", module_id))

    in_block = False
    seen: set[str] = set()
    for lineno, raw in enumerate(source.splitlines(), start=1):
        line, in_block = _strip_comments(raw, spec, in_block)
        if not line.strip():
            continue

        for pattern in spec.imports:
            m = pattern.search(line)
            if m:
                out.pending_refs.append((file_id, m.group("mod"), "imports"))
                # A named import is a reference to a specific symbol, which is what
                # makes `dependents <symbol>` answer "who uses this" rather than
                # only "who imports this file".
                for name in _named_specifiers(line):
                    out.pending_refs.append((file_id, name, "references"))

        for rule in spec.rules:
            m = rule.pattern.search(line)
            if not m:
                continue
            name = m.group(rule.name_group)
            if not name or name in _NOISE:
                continue
            if rule.kind == "route":
                method = (m.group(rule.method_group) or "any").upper() if rule.method_group else "ANY"
                name = f"{method} {name}"
            key = f"{rule.kind}:{name}"
            if key in seen:
                continue
            seen.add(key)
            sym_id = node_id(rule.kind, rel_path, name)
            out.nodes.append(
                Node(sym_id, rule.kind, rel_path, lineno, name, fingerprint(line.strip()))
            )
            out.edges.append(Edge(module_id, "defines", sym_id))
            break  # one node per line; the first matching rule is the specific one

    return out


# Keywords that survive a loose pattern and are never symbols.
_NOISE = {
    "if", "for", "while", "switch", "catch", "return", "else", "do", "try",
    "func", "function", "class", "new", "await", "typeof", "case", "with",
}


_BRACED = re.compile(r"[{(]\s*(?P<names>[^{}()]*?)\s*[})]")


def _named_specifiers(line: str) -> list[str]:
    """`import { a, b as c } from '...'` → ['a', 'b']. Also Go's and Rust's braces."""
    m = _BRACED.search(line)
    if not m:
        return []
    out: list[str] = []
    for part in m.group("names").split(","):
        token = part.strip()
        if not token or token in ("*", "default"):
            continue
        token = re.split(r"\s+as\s+", token)[0].strip()
        token = token.removeprefix("type ").strip()
        if re.fullmatch(_ID, token):
            out.append(token)
    return out


def _module_name(rel_path: str) -> str:
    stem = rel_path.rsplit("/", 1)[-1]
    return stem.rsplit(".", 1)[0]


def _strip_comments(raw: str, spec: LangRules, in_block: bool) -> tuple[str, bool]:
    """Blank out comment content without disturbing line numbering."""
    line = raw
    if spec.block_comment:
        open_tok, close_tok = spec.block_comment
        if in_block:
            end = line.find(close_tok)
            if end == -1:
                return "", True
            line = " " * (end + len(close_tok)) + line[end + len(close_tok) :]
            in_block = False
        start = line.find(open_tok)
        while start != -1:
            end = line.find(close_tok, start + len(open_tok))
            if end == -1:
                line = line[:start]
                return line, True
            line = line[:start] + " " * (end + len(close_tok) - start) + line[end + len(close_tok) :]
            start = line.find(open_tok)
    stripped = line.lstrip()
    for marker in spec.line_comment:
        if stripped.startswith(marker):
            return "", in_block
    return line, in_block
