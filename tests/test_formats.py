"""The three formats and the rules `edify check` applies to them."""

from __future__ import annotations

from pathlib import Path

import pytest

from edify.formats import plan as plan_format
from edify.formats import spec as spec_format
from edify.formats import tasks as tasks_format
from edify.formats.check import check_repository
from edify.formats.finding import Level
from edify.graph import extract
from edify.paths import Layout

GOOD_SPEC = """\
---
feature: invitations
status: approved
date: 2026-08-06
---

# spec — invitations

## Brief
Let an admin invite someone by email.

## Intent
1. An admin can bring a new person into a workspace without an engineer.

## Constraints
Node 20, vitest, `npm test`.

## Requirements

| id | requirement | assertions |
|---|---|---|
| REQ-1 | An admin can invite someone by email | A-1, A-2 |

## Assertions

| id | assertion | verification | citation |
|---|---|---|---|
| A-1 | A token is 32 characters of base32 | property | src/auth/tokens.ts:3-5 |
| A-2 | Accepting an expired invite returns 410 | example | new |

## What this entails

| id | what it entails | status |
|---|---|---|
| CL-1 | The migration has a rollback | REQ-1 |

## Open questions

| # | question | readings | adopted | who |
|---|---|---|---|---|

## Non-goals
Bulk import.
"""

GOOD_TASKS = """\
---
feature: invitations
spec: spec.md
status: approved
phases: 3
tasks: 3
date: 2026-08-06
---

# tasks — invitations

## Phases

| # | phase | tasks | parallel-safe | exit check |
|---|---|---|---|---|
| 1 | Contracts | T-1 | — | `npm run typecheck` |
| 2 | Verification | T-2 | — | `npm test` reports 2 failing, 0 passing |
| 3 | Core | T-3 | — | `npm test -- invitations` |

## Phase 1 · Contracts

### T-1 · Add the invitations table

Phase 1 · Role implementer · Skill implementer-postgres · Size s
Discharges REQ-1, CL-1
Depends on — · Parallel with —

Files

| path | range | action |
|---|---|---|
| migrations/0028_invites.up.sql | — | new |

Follow the pattern at
- migrations/0027_members.up.sql:1-5 — the same table conventions

Steps
1. Create the table with the columns the contract names.
2. Write the matching down migration.

Done when
- `npm run migrate:test` applies and rolls back cleanly

## Phase 2 · Verification

### T-2 · Assertions A-1 and A-2 as failing tests

Phase 2 · Role test · Skill test-writer-node · Size s
Discharges A-1, A-2
Verification property, example
Depends on T-1 · Parallel with —

Files

| path | range | action |
|---|---|---|
| tests/assertions/invites.test.ts | — | new |

Follow the pattern at
- src/auth/tokens.ts:3-9 — the shape the property test generates against

Steps
1. Write one test per assertion, named for the assertion id.

Done when
- `npm test -- invites` reports 2 failing, 0 passing

## Phase 3 · Core

### T-3 · Implement the invitation service

Phase 3 · Role implementer · Skill implementer-node · Size m
Discharges REQ-1
Depends on T-1, T-2 · Parallel with —

Files

| path | range | action |
|---|---|---|
| src/api/members.ts | 1-9 | edit |

Follow the pattern at
- src/api/members.ts:3-7 — the service shape

Steps
1. Add the invite method beside `add`.

Done when
- `npm test -- invites` passes

## Coverage

| source | what it is | asserted by | built by |
|---|---|---|---|
| REQ-1 | An admin can invite by email | T-2 | T-1, T-3 |
| CL-1 | The migration has a rollback | — | T-1 |

## Decisions

| # | decision | why | binds |
|---|---|---|---|
"""


def write_feature(repo: Path, spec: str = GOOD_SPEC, tasks: str = GOOD_TASKS) -> Path:
    feature = repo / "specs" / "invitations"
    feature.mkdir(parents=True, exist_ok=True)
    (feature / "spec.md").write_text(spec, encoding="utf-8")
    (feature / "tasks.md").write_text(tasks, encoding="utf-8")
    return feature


def codes(repo: Path) -> dict[str, Level]:
    layout = Layout(repo)
    layout.edify.mkdir(parents=True, exist_ok=True)
    extract.build(layout)
    from edify.graph.store import GraphStore

    return {f.code: f.level for f in check_repository(layout, GraphStore(layout))}


# -- parsing ---------------------------------------------------------------


def test_spec_parses_its_tables(repo: Path) -> None:
    feature = write_feature(repo)
    spec = spec_format.parse(feature / "spec.md")
    assert spec.requirement_ids() == {"REQ-1"}
    assert spec.assertion_ids() == {"A-1", "A-2"}
    assert spec.kind_of("A-1") == "property"
    assert spec.checklist_ids() == {"CL-1"}


def test_tasks_parses_a_block_completely(repo: Path) -> None:
    feature = write_feature(repo)
    parsed = tasks_format.parse(feature / "tasks.md")
    assert [t.id for t in parsed.tasks] == ["T-1", "T-2", "T-3"]

    t3 = parsed.by_id("T-3")
    assert t3.phase == 3
    assert t3.role == "implementer"
    assert t3.skill == "implementer-node"
    assert t3.size == "m"
    assert t3.discharges == ["REQ-1"]
    assert t3.depends_on == ["T-1", "T-2"]
    assert [f.path for f in t3.files] == ["src/api/members.ts"]
    assert t3.files[0].bounds == (1, 9)
    assert t3.steps and t3.done_when and t3.patterns

    t2 = parsed.by_id("T-2")
    assert t2.verification == ["property", "example"]
    assert len(parsed.phases) == 3
    assert len(parsed.coverage) == 2


def test_plan_parses_decisions_and_seeds(tmp_path: Path) -> None:
    path = tmp_path / "plan.md"
    path.write_text(
        "---\nfeature: x\nstatus: draft\n---\n\n# plan — x\n\n"
        "## Technology decisions\n\n"
        "| # | decision | version | beat | why |\n|---|---|---|---|---|\n"
        "| D-1 | Use library Y | 2.3 | library Z | smaller |\n"
        "| D-2 | Keep the existing logger | 1.0 | — | default |\n\n"
        "### M1 — the first milestone\n\nContext seeds\n"
        "  src/auth/tokens.ts:3-9   the generator it extends\n",
        encoding="utf-8",
    )
    parsed = plan_format.parse(path)
    assert [d.id for d in parsed.decisions] == ["D-1", "D-2"]
    assert parsed.decisions[0].version == "2.3"
    assert parsed.decisions[1].is_default
    assert any(s.path == "src/auth/tokens.ts" and s.has_range for s in parsed.seeds)


# -- check rules -----------------------------------------------------------


def test_a_well_formed_feature_reports_no_errors(repo: Path) -> None:
    write_feature(repo)
    found = codes(repo)
    errors = {c for c, level in found.items() if level is Level.ERROR}
    assert errors == set(), errors


def test_a_requirement_with_no_assertion_is_an_error(repo: Path) -> None:
    spec = GOOD_SPEC.replace("| REQ-1 | An admin can invite someone by email | A-1, A-2 |",
                             "| REQ-1 | An admin can invite someone by email | |")
    write_feature(repo, spec=spec)
    assert "spec-requirement-unasserted" in codes(repo)


def test_an_assertion_with_no_verification_kind_is_an_error(repo: Path) -> None:
    spec = GOOD_SPEC.replace("| A-2 | Accepting an expired invite returns 410 | example | new |",
                             "| A-2 | Accepting an expired invite returns 410 | | new |")
    write_feature(repo, spec=spec)
    assert "spec-assertion-no-kind" in codes(repo)


def test_a_phase_two_check_that_asserts_passing_is_an_error(repo: Path) -> None:
    tasks = GOOD_TASKS.replace("- `npm test -- invites` reports 2 failing, 0 passing",
                               "- `npm test -- invites` passes")
    write_feature(repo, tasks=tasks)
    assert "phase2-asserts-pass" in codes(repo)


def test_a_whole_file_edit_is_a_warning(repo: Path) -> None:
    tasks = GOOD_TASKS.replace("| src/api/members.ts | 1-9 | edit |",
                               "| src/api/members.ts | — | edit |")
    write_feature(repo, tasks=tasks)
    found = codes(repo)
    assert found.get("task-whole-file-edit") is Level.WARN


def test_a_task_that_discharges_nothing_is_an_error(repo: Path) -> None:
    tasks = GOOD_TASKS.replace("Discharges REQ-1, CL-1\n", "\n")
    write_feature(repo, tasks=tasks)
    assert "task-discharges-nothing" in codes(repo)


def test_an_empty_coverage_cell_is_an_error(repo: Path) -> None:
    tasks = GOOD_TASKS.replace("| CL-1 | The migration has a rollback | — | T-1 |",
                               "| CL-1 | The migration has a rollback | | |")
    write_feature(repo, tasks=tasks)
    assert "coverage-empty-cell" in codes(repo)


def test_an_assertion_with_no_phase_two_task_is_an_error(repo: Path) -> None:
    tasks = GOOD_TASKS.replace("Discharges A-1, A-2", "Discharges A-1")
    write_feature(repo, tasks=tasks)
    assert "phase2-assertion-untested" in codes(repo)


def test_a_missing_file_on_an_edit_is_an_error(repo: Path) -> None:
    tasks = GOOD_TASKS.replace("| src/api/members.ts | 1-9 | edit |",
                               "| src/api/gone.ts | 1-9 | edit |")
    write_feature(repo, tasks=tasks)
    assert "task-file-missing" in codes(repo)


def test_a_phase_with_no_exit_check_is_an_error(repo: Path) -> None:
    tasks = GOOD_TASKS.replace("| 3 | Core | T-3 | — | `npm test -- invitations` |",
                               "| 3 | Core | T-3 | — | |")
    write_feature(repo, tasks=tasks)
    assert "phase-no-exit-check" in codes(repo)


def test_a_dependency_on_a_task_that_does_not_exist_is_an_error(repo: Path) -> None:
    tasks = GOOD_TASKS.replace("Depends on T-1, T-2 · Parallel with —",
                               "Depends on T-1, T-99 · Parallel with —")
    write_feature(repo, tasks=tasks)
    assert "task-unknown-dependency" in codes(repo)


def test_a_loose_version_in_a_plan_is_an_error(repo: Path) -> None:
    write_feature(repo)
    (repo / "specs" / "invitations" / "plan.md").write_text(
        "---\nfeature: invitations\nstatus: draft\n---\n\n# plan — invitations\n\n"
        "## Technology decisions\n\n"
        "| # | decision | version | beat | why |\n|---|---|---|---|---|\n"
        "| D-1 | Use library Y | ^2.3 | library Z | smaller |\n",
        encoding="utf-8",
    )
    assert "plan-decision-loose-version" in codes(repo)


# -- skills ----------------------------------------------------------------


def test_an_invalid_skill_is_reported_and_not_indexed(installed: Path) -> None:
    from edify import skills as skills_index

    layout = Layout(installed)
    (layout.skills_dir / "broken.md").write_text(
        "---\nname: Broken Name\nkind: skill\nrole: wizard\nphase: 9\n"
        "tech: any\nprovenance: original\ndescription: x\n---\n\n# broken\n",
        encoding="utf-8",
    )
    found = {f.code for f in check_repository(layout, None)}
    assert "skill-bad-role" in found
    assert "skill-bad-name" in found
    assert "skill-bad-phase" in found

    _, skipped = skills_index.build_index(layout)
    assert any("broken.md" in s for s in skipped)
