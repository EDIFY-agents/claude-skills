"""Markdown with flat YAML frontmatter, parsed with line numbers throughout.

Line numbers are the point. Every finding, every citation, and every `--fix` needs
to say where, and a parser that loses position produces reports nobody can act on.

The frontmatter reader deliberately handles scalars and space-separated lists only
— no nesting, no anchors, no multi-line values. That is the metadata format
(`docs/design/architecture/05-skills-and-spawning.md` §2), and a stricter reader is what
keeps the index a two-line awk script for anyone who wants one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_TABLE_SEP = re.compile(r"^\s*\|?[\s:\-|]+\|[\s:\-|]*$")


@dataclass
class Row:
    cells: list[str]
    line: int

    def get(self, index: int) -> str:
        return self.cells[index].strip() if index < len(self.cells) else ""


@dataclass
class Table:
    headers: list[str]
    rows: list[Row]
    line: int

    def column(self, *names: str) -> int:
        """The index of the first header matching any of `names`, or -1."""
        lowered = [h.strip().lower() for h in self.headers]
        for name in names:
            target = name.lower()
            for i, header in enumerate(lowered):
                if header == target:
                    return i
            for i, header in enumerate(lowered):
                if target in header:
                    return i
        return -1


@dataclass
class Section:
    title: str
    level: int
    line: int
    end_line: int
    lines: list[str] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    @property
    def key(self) -> str:
        return self.title.strip().lower()


@dataclass
class Document:
    path: Path
    rel: str
    lines: list[str]
    frontmatter: dict[str, str] = field(default_factory=dict)
    frontmatter_lines: dict[str, int] = field(default_factory=dict)
    frontmatter_end: int = 0
    sections: list[Section] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)

    def section(self, *titles: str) -> Section | None:
        wanted = [t.strip().lower() for t in titles]
        for section in self.sections:
            if section.key in wanted:
                return section
        for section in self.sections:
            if any(w in section.key for w in wanted):
                return section
        return None

    def has_frontmatter(self) -> bool:
        return bool(self.frontmatter) or self.frontmatter_end > 0

    def list_field(self, key: str) -> list[str]:
        return [v for v in self.frontmatter.get(key, "").split() if v]


def parse_document(path: Path, rel: str | None = None) -> Document:
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_text(text, path, rel or path.as_posix())


def parse_text(text: str, path: Path, rel: str) -> Document:
    lines = text.splitlines()
    doc = Document(path=path, rel=rel, lines=lines)

    body_start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() in ("---", "..."):
                body_start = i + 1
                doc.frontmatter_end = i + 1
                break
        for i in range(1, doc.frontmatter_end - 1):
            raw = lines[i]
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            key, sep, value = raw.partition(":")
            if not sep:
                continue
            key = key.strip()
            doc.frontmatter[key] = value.strip().strip("\"'")
            doc.frontmatter_lines[key] = i + 1

    current: Section | None = None
    in_fence = False
    pending_table: list[str] = []
    pending_start = 0

    def flush_table() -> None:
        nonlocal pending_table, pending_start
        if len(pending_table) >= 2:
            table = _build_table(pending_table, pending_start)
            if table:
                doc.tables.append(table)
                if current is not None:
                    current.tables.append(table)
        pending_table = []
        pending_start = 0

    for index, raw in enumerate(lines[body_start:], start=body_start):
        lineno = index + 1
        if _FENCE.match(raw):
            flush_table()
            in_fence = not in_fence
            if current is not None:
                current.lines.append(raw)
            continue

        if not in_fence:
            heading = _HEADING.match(raw)
            if heading:
                flush_table()
                if current is not None:
                    current.end_line = lineno - 1
                current = Section(
                    title=heading.group(2).strip(),
                    level=len(heading.group(1)),
                    line=lineno,
                    end_line=len(lines),
                )
                doc.sections.append(current)
                continue

            if raw.lstrip().startswith("|"):
                if not pending_table:
                    pending_start = lineno
                pending_table.append(raw)
            else:
                flush_table()

        if current is not None:
            current.lines.append(raw)

    flush_table()
    if current is not None:
        current.end_line = len(lines)
    return doc


def _build_table(block: list[str], start: int) -> Table | None:
    if len(block) < 2 or not _TABLE_SEP.match(block[1]):
        return None
    headers = _cells(block[0])
    rows = [Row(_cells(line), start + offset) for offset, line in enumerate(block[2:], start=2)]
    return Table(headers=headers, rows=rows, line=start)


def _cells(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [c.strip() for c in stripped.split("|")]


# ---------------------------------------------------------------------------
# citations
# ---------------------------------------------------------------------------

# `src/auth/session.ts:88-140`, `src/auth/session.ts:12`, or the literal `new`.
CITATION = re.compile(
    r"(?P<path>(?:[\w.\-]+/)*[\w.\-]+\.[A-Za-z0-9]{1,10})(?::(?P<start>\d+)(?:-(?P<end>\d+))?)?"
)


@dataclass(frozen=True)
class Citation:
    path: str
    start: int | None
    end: int | None
    line: int
    raw: str

    @property
    def has_range(self) -> bool:
        return self.start is not None


def citations(text: str, first_line: int = 1) -> list[Citation]:
    """Every `file` or `file:line[-line]` in a block of text, with its line."""
    out: list[Citation] = []
    for offset, raw_line in enumerate(text.splitlines()):
        for m in CITATION.finditer(raw_line):
            path = m.group("path")
            if path.startswith("http") or "://" in raw_line[max(0, m.start() - 8) : m.start()]:
                continue
            out.append(
                Citation(
                    path=path,
                    start=int(m.group("start")) if m.group("start") else None,
                    end=int(m.group("end")) if m.group("end") else None,
                    line=first_line + offset,
                    raw=m.group(0),
                )
            )
    return out
