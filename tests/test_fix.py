"""`edify check --fix` does the two mechanical repairs and nothing else.

A tool that guesses at a decision produces a document that looks approved and was
not, so everything except resolving a range through the graph and re-sorting the
index is left for a person.
"""

from __future__ import annotations

from pathlib import Path

from edify.cli import main
from edify.formats import tasks as tasks_format
from edify.formats.fix import fix_repository
from edify.graph.store import GraphStore
from edify.paths import Layout

TASKS = """\
---
feature: invitations
spec: spec.md
status: draft
phases: 1
tasks: 1
date: 2026-08-06
---

# tasks — invitations

## Phases

| # | phase | tasks | parallel-safe | exit check |
|---|---|---|---|---|
| 3 | Core | T-1 | — | `npm test` |

## Phase 3 · Core

### T-1 · Extend the member service

Phase 3 · Role implementer · Skill implementer-node · Size s
Discharges REQ-1
Depends on — · Parallel with —

Files

| path                   | range | action |
|------------------------|-------|--------|
| src/api/members.ts     |       | edit   |

Follow the pattern at
- src/api/members.ts:3-7 — the service shape

Steps
1. Add an invite method beside `MemberService`.

Done when
- `npm test -- members` passes

## Coverage

| source | what it is | asserted by | built by |
|---|---|---|---|
| REQ-1 | An admin can invite by email | — | T-1 |
"""


def test_fix_resolves_a_whole_file_edit_to_a_line_range(installed: Path) -> None:
    feature = installed / "specs" / "invitations"
    feature.mkdir(parents=True)
    (feature / "tasks.md").write_text(TASKS, encoding="utf-8")

    layout = Layout(installed)
    before = tasks_format.parse(feature / "tasks.md")
    assert not before.by_id("T-1").files[0].has_range

    repairs = fix_repository(layout, GraphStore(layout))
    assert len(repairs) == 1
    assert "resolved" in repairs[0].what

    after = tasks_format.parse(feature / "tasks.md")
    ref = after.by_id("T-1").files[0]
    assert ref.has_range
    assert ref.bounds is not None
    # `MemberService` is named in the steps, so the range is that symbol's, not the
    # whole file's.
    assert ref.bounds[0] == 3


def test_fix_leaves_a_document_with_nothing_mechanical_alone(installed: Path) -> None:
    feature = installed / "specs" / "invitations"
    feature.mkdir(parents=True)
    fixed = TASKS.replace("| src/api/members.ts     |       | edit   |",
                          "| src/api/members.ts     | 3-7   | edit   |")
    (feature / "tasks.md").write_text(fixed, encoding="utf-8")

    layout = Layout(installed)
    before = (feature / "tasks.md").read_text(encoding="utf-8")
    assert fix_repository(layout, GraphStore(layout)) == []
    assert (feature / "tasks.md").read_text(encoding="utf-8") == before


def test_fix_does_not_invent_a_missing_done_check(installed: Path) -> None:
    """The other findings are decisions. A repair for one would be a guess."""
    feature = installed / "specs" / "invitations"
    feature.mkdir(parents=True)
    stripped = TASKS.replace("Done when\n- `npm test -- members` passes\n", "")
    (feature / "tasks.md").write_text(stripped, encoding="utf-8")

    assert main(["--repo", str(installed), "--quiet", "check", "--fix"]) == 0
    assert "Done when" not in (feature / "tasks.md").read_text(encoding="utf-8")


def test_the_index_is_rebuilt_and_stays_sorted(installed: Path) -> None:
    from edify import skills as skills_index

    layout = Layout(installed)
    skills_index.build_index(layout)
    lines = [
        line for line in layout.skills_index.read_text(encoding="utf-8").splitlines()
        if not line.startswith("#")
    ]
    assert lines == sorted(lines)
