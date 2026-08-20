"""`edify check --fix` — the mechanical repairs, and only those.

Two things are safe to do without judgment: resolve a filename to a line range
through the graph, and re-sort the skill index. Everything else `check` reports is
a decision, and a tool that guesses at a decision produces a document that looks
approved and was not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..graph.queries import defines, line_range_for
from ..graph.store import GraphStore
from ..paths import Layout
from . import tasks as tasks_format


@dataclass
class Repair:
    file: str
    line: int
    before: str
    after: str
    what: str


def fix_repository(layout: Layout, store: GraphStore | None) -> list[Repair]:
    repairs: list[Repair] = []
    if store is None or not store.exists():
        return repairs
    if not layout.specs.is_dir():
        return repairs

    for feature_dir in sorted(p for p in layout.specs.iterdir() if p.is_dir()):
        tasks_path = feature_dir / "tasks.md"
        if tasks_path.is_file():
            repairs.extend(_fix_task_ranges(tasks_path, layout, store))
    return repairs


def _fix_task_ranges(path: Path, layout: Layout, store: GraphStore) -> list[Repair]:
    """Fill an empty `range` cell on an `edit` row from the graph.

    The range chosen is the span of the file's exported symbols where the file has
    any, which is the honest answer to "which lines matter here" without pretending
    to know which symbol the task means. A file with no symbols is left alone.
    """
    parsed = tasks_format.parse(path, layout.rel(path))
    lines = path.read_text(encoding="utf-8").splitlines()
    repairs: list[Repair] = []

    for task in parsed.tasks:
        for ref in task.files:
            if ref.action.strip().lower() != "edit" or ref.has_range:
                continue
            span = _span_for(store, ref.path, task)
            if span is None:
                continue
            index = ref.line - 1
            if index < 0 or index >= len(lines):
                continue
            before = lines[index]
            after = _replace_range_cell(before, f"{span[0]}-{span[1]}")
            if after == before:
                continue
            lines[index] = after
            repairs.append(
                Repair(
                    file=parsed.rel,
                    line=ref.line,
                    before=before.strip(),
                    after=after.strip(),
                    what=f"{task.id}: resolved `{ref.path}` to a line range through the graph",
                )
            )

    if repairs:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return repairs


def _span_for(store: GraphStore, file: str, task: tasks_format.Task) -> tuple[int, int] | None:
    # If a step names a symbol that lives in this file, that symbol's range is the
    # right answer and is much narrower than the file's.
    for step in task.steps:
        for token in re.findall(r"`([A-Za-z_][\w.]*)`", step):
            span = line_range_for(store, file, token)
            if span:
                return span
    nodes = [n for n in defines(store, file) if n.kind in ("symbol", "route", "table")]
    if not nodes:
        return None
    first = min(n.line for n in nodes)
    last = max(n.line for n in nodes)
    return first, max(first, last)


def _replace_range_cell(line: str, value: str) -> str:
    """Put `value` in the second cell of a markdown table row, keeping the shape."""
    if not line.strip().startswith("|"):
        return line
    parts = line.split("|")
    if len(parts) < 4:
        return line
    target = parts[2]
    width = len(target)
    replacement = f" {value} "
    if len(replacement) < width:
        replacement = replacement.ljust(width)
    parts[2] = replacement
    return "|".join(parts)
