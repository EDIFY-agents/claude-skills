"""`edify check` — the rule engine.

Every rule here comes from `docs/design/architecture/09-cli.md` §2. Nothing blocks: the
command prints what is wrong and a person or a CI job decides what that means.
`--exit-code` exists so a customer who needs a hard block can own one, which is the
honest scope stated in `docs/design/01-principles.md` P7.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..graph.queries import resolve_ref
from ..graph.store import GraphStore
from ..paths import Layout
from . import mcp as mcp_format
from . import plan as plan_format
from . import skill as skill_format
from . import spec as spec_format
from . import tasks as tasks_format
from .document import citations
from .finding import Finding, Level, sort_findings

# A phase-2 done-check has to assert failure. "passes" on arrival means the task
# tested something that already existed, or tested nothing.
_ASSERTS_FAILURE = re.compile(r"\b(fail|failing|red|0 passing|no passing)\b", re.IGNORECASE)
_ASSERTS_PASS = re.compile(r"\b(pass|passes|passing|green|succeeds?)\b", re.IGNORECASE)


def check_repository(layout: Layout, store: GraphStore | None = None) -> list[Finding]:
    """Everything under `specs/`, plus the installed skills and the registry."""
    findings: list[Finding] = []
    graph = store if (store and store.exists()) else None

    if layout.specs.is_dir():
        for feature_dir in sorted(p for p in layout.specs.iterdir() if p.is_dir()):
            findings.extend(check_feature(layout, feature_dir, graph))

    findings.extend(check_skills(layout))
    findings.extend(check_mcp(layout))
    return sort_findings(findings)


def check_feature(layout: Layout, feature_dir: Path, graph: GraphStore | None) -> list[Finding]:
    findings: list[Finding] = []
    spec_path = feature_dir / "spec.md"
    plan_path = feature_dir / "plan.md"
    tasks_path = feature_dir / "tasks.md"

    parsed_spec = None
    parsed_plan = None

    if spec_path.is_file():
        parsed_spec = spec_format.parse(spec_path, layout.rel(spec_path))
        findings.extend(check_spec(parsed_spec))
    if plan_path.is_file():
        parsed_plan = plan_format.parse(plan_path, layout.rel(plan_path))
        findings.extend(check_plan(parsed_plan, graph))
    if tasks_path.is_file():
        parsed_tasks = tasks_format.parse(tasks_path, layout.rel(tasks_path))
        findings.extend(check_tasks(parsed_tasks, parsed_spec, parsed_plan, graph, layout))
    return findings


# ---------------------------------------------------------------------------
# spec.md
# ---------------------------------------------------------------------------


def check_spec(spec: spec_format.Spec) -> list[Finding]:
    out: list[Finding] = []
    rel = spec.rel

    for name in spec_format.REQUIRED_SECTIONS:
        if spec.doc.section(name) is None:
            out.append(
                Finding(Level.ERROR, rel, 1, "spec-missing-section", f"no `## {name.title()}` section")
            )

    if not spec.requirements:
        out.append(Finding(Level.ERROR, rel, 1, "spec-no-requirements", "no requirements table"))
    if not spec.assertions:
        out.append(Finding(Level.ERROR, rel, 1, "spec-no-assertions", "no assertions table"))

    known = spec.assertion_ids()
    for req in spec.requirements:
        if not req.assertions:
            out.append(
                Finding(
                    Level.ERROR,
                    rel,
                    req.line,
                    "spec-requirement-unasserted",
                    f"{req.id} has no assertion — a requirement with no assertion is a wish",
                )
            )
        for aid in req.assertions:
            if known and aid not in known:
                out.append(
                    Finding(
                        Level.ERROR, rel, req.line, "spec-unknown-assertion",
                        f"{req.id} names {aid}, which is not in the assertions table",
                    )
                )

    for assertion in spec.assertions:
        if not assertion.kind:
            out.append(
                Finding(
                    Level.ERROR, rel, assertion.line, "spec-assertion-no-kind",
                    f"{assertion.id} declares no verification kind",
                    hint="one of: " + ", ".join(spec_format.VERIFICATION_KINDS),
                )
            )
        elif assertion.kind not in spec_format.VERIFICATION_KINDS:
            out.append(
                Finding(
                    Level.ERROR, rel, assertion.line, "spec-assertion-bad-kind",
                    f"{assertion.id} declares `{assertion.kind}`, which is not on the ladder",
                    hint="one of: " + ", ".join(spec_format.VERIFICATION_KINDS),
                )
            )
        if assertion.citation:
            out.extend(_citation_findings(rel, assertion.citation, assertion.line, "spec-citation-no-range"))

    served = {aid for req in spec.requirements for aid in req.assertions}
    if served:
        for assertion in spec.assertions:
            if assertion.id not in served:
                out.append(
                    Finding(
                        Level.WARN, rel, assertion.line, "spec-orphan-assertion",
                        f"{assertion.id} serves no requirement",
                    )
                )

    for item in spec.checklist:
        if not item.status.strip() or set(item.status.strip()) <= {"-", "—"}:
            out.append(
                Finding(
                    Level.WARN, rel, item.line, "spec-checklist-open",
                    f"{item.id} is open — the human gate is what this row is for",
                )
            )
    return out


def _citation_findings(rel: str, text: str, line: int, code: str) -> list[Finding]:
    """Every reference is a file and a line, or the literal `new` (P3)."""
    if text.strip().lower() in ("new", "-", "—", ""):
        return []
    out: list[Finding] = []
    for citation in citations(text, first_line=line):
        if not citation.has_range:
            out.append(
                Finding(
                    Level.WARN, rel, line, code,
                    f"`{citation.path}` is cited without a line range",
                    hint="`src/import.py` and `src/import.py:88-114` look equally correct in review; only the second lets an agent start work",
                )
            )
    return out


# ---------------------------------------------------------------------------
# plan.md
# ---------------------------------------------------------------------------


def check_plan(plan: plan_format.Plan, graph: GraphStore | None) -> list[Finding]:
    out: list[Finding] = []
    rel = plan.rel

    if not plan.decisions:
        out.append(
            Finding(Level.WARN, rel, 1, "plan-no-decisions", "no technology decisions table")
        )

    for decision in plan.decisions:
        if not decision.version or decision.version in ("-", "—"):
            out.append(
                Finding(
                    Level.ERROR, rel, decision.line, "plan-decision-no-version",
                    f"{decision.id} names no exact version",
                    hint="`2.3`, not `^2.3` and not `latest` — this is what the docs server is pointed at",
                )
            )
        elif re.search(r"[\^~*]|latest", decision.version, re.IGNORECASE):
            out.append(
                Finding(
                    Level.ERROR, rel, decision.line, "plan-decision-loose-version",
                    f"{decision.id} has a range, not a version: `{decision.version}`",
                )
            )
        if decision.is_default and "default" not in decision.text.lower():
            out.append(
                Finding(
                    Level.WARN, rel, decision.line, "plan-decision-no-alternative",
                    f"{decision.id} names no alternative it beat — say it is a default rather than dressing it as a decision",
                )
            )

    for seed in plan.seeds:
        if not seed.has_range:
            out.append(
                Finding(
                    Level.WARN, rel, seed.line, "plan-seed-no-range",
                    f"context seed `{seed.path}` has no line range",
                    hint="a seed without a range transfers its cost to /tasks, which is the reason the plan exists",
                )
            )
        elif graph is not None and resolve_ref(graph, seed.path) is None:
            out.append(
                Finding(
                    Level.WARN, rel, seed.line, "plan-seed-unresolved",
                    f"`{seed.path}` does not resolve against the graph",
                )
            )
    return out


# ---------------------------------------------------------------------------
# tasks.md
# ---------------------------------------------------------------------------


def check_tasks(
    tasks: tasks_format.Tasks,
    spec: spec_format.Spec | None,
    plan: plan_format.Plan | None,
    graph: GraphStore | None,
    layout: Layout,
) -> list[Finding]:
    out: list[Finding] = []
    rel = tasks.rel

    if not tasks.tasks:
        out.append(Finding(Level.ERROR, rel, 1, "tasks-empty", "no task blocks"))
        return out

    known_ids = {t.id for t in tasks.tasks}
    spec_ids: set[str] = set()
    if spec is not None:
        spec_ids = spec.requirement_ids() | spec.assertion_ids() | spec.checklist_ids()

    for task in tasks.tasks:
        out.extend(_check_task(task, tasks, spec, graph, layout, known_ids, spec_ids))

    out.extend(_check_phases(tasks))
    out.extend(_check_coverage(tasks, spec))
    out.extend(_check_phase_two(tasks, spec, plan))
    return out


def _check_task(
    task: tasks_format.Task,
    tasks: tasks_format.Tasks,
    spec: spec_format.Spec | None,
    graph: GraphStore | None,
    layout: Layout,
    known_ids: set[str],
    spec_ids: set[str],
) -> list[Finding]:
    out: list[Finding] = []
    rel = tasks.rel

    if task.phase is None:
        out.append(Finding(Level.ERROR, rel, task.line, "task-no-phase", f"{task.id} declares no phase"))
    if not task.role:
        out.append(Finding(Level.ERROR, rel, task.line, "task-no-role", f"{task.id} declares no role"))
    if not task.discharges:
        out.append(
            Finding(
                Level.ERROR, rel, task.line, "task-discharges-nothing",
                f"{task.id} discharges nothing — this is where scope creep enters",
            )
        )
    for did in task.discharges:
        if spec_ids and did not in spec_ids:
            out.append(
                Finding(
                    Level.WARN, rel, task.line, "task-unknown-discharge",
                    f"{task.id} discharges {did}, which is not in the spec",
                )
            )
    if not task.steps:
        out.append(Finding(Level.ERROR, rel, task.line, "task-no-steps", f"{task.id} has no steps"))
    if not task.done_when:
        out.append(
            Finding(Level.ERROR, rel, task.line, "task-no-done-check", f"{task.id} has no done-check")
        )
    if not task.files and task.phase != 7:
        out.append(
            Finding(Level.WARN, rel, task.line, "task-no-files", f"{task.id} names no files")
        )
    if not task.patterns and task.phase not in (7,):
        out.append(
            Finding(
                Level.WARN, rel, task.line, "task-no-pattern",
                f"{task.id} points at no existing pattern",
                hint="say `no precedent in this codebase` explicitly rather than leaving it blank",
            )
        )

    for dep in task.depends_on + task.parallel_with:
        if dep not in known_ids:
            out.append(
                Finding(Level.ERROR, rel, task.line, "task-unknown-dependency", f"{task.id} names unknown task {dep}")
            )

    for ref in task.files:
        action = ref.action.strip().lower()
        if action not in tasks_format.FILE_ACTIONS:
            out.append(
                Finding(
                    Level.ERROR, rel, ref.line, "task-bad-action",
                    f"{task.id} file action `{ref.action}` is not new|edit|delete",
                )
            )
        if action == "edit" and not ref.has_range:
            out.append(
                Finding(
                    Level.WARN, rel, ref.line, "task-whole-file-edit",
                    f"{task.id} edits `{ref.path}` with no line range",
                    hint="a whole-file reference passes any shape check, inflates overlap, and makes the builder open lines it did not need",
                )
            )
        if action in ("edit", "delete") and not (layout.root / ref.path).exists():
            out.append(
                Finding(
                    Level.ERROR, rel, ref.line, "task-file-missing",
                    f"{task.id} {action}s `{ref.path}`, which is not on disk",
                )
            )
        if action == "new" and (layout.root / ref.path).exists():
            out.append(
                Finding(
                    Level.WARN, rel, ref.line, "task-new-file-exists",
                    f"{task.id} marks `{ref.path}` as new, but it already exists",
                )
            )

    for pattern in task.patterns:
        if "no precedent" in pattern.lower():
            continue
        for citation in citations(pattern, first_line=task.line):
            if not citation.has_range:
                out.append(
                    Finding(
                        Level.WARN, rel, task.line, "task-pattern-no-range",
                        f"{task.id} points at `{citation.path}` with no line range",
                    )
                )
            elif graph is not None and resolve_ref(graph, citation.path) is None:
                out.append(
                    Finding(
                        Level.WARN, rel, task.line, "task-pattern-unresolved",
                        f"{task.id} points at `{citation.path}`, which does not resolve against the graph",
                    )
                )

    for check in task.done_when:
        if check.strip().lower() in ("tests pass", "it works", "the endpoint works", "done"):
            out.append(
                Finding(
                    Level.WARN, rel, task.line, "task-vague-done-check",
                    f"{task.id} done-check `{check}` is not a command or an observable outcome",
                )
            )
    return out


def _check_phases(tasks: tasks_format.Tasks) -> list[Finding]:
    out: list[Finding] = []
    rel = tasks.rel
    declared = {p.number for p in tasks.phases}
    used = {t.phase for t in tasks.tasks if t.phase is not None}

    for number in sorted(used - declared):
        out.append(
            Finding(Level.WARN, rel, 1, "tasks-phase-undeclared", f"phase {number} has tasks but no row in `## Phases`")
        )
    for phase in tasks.phases:
        if not phase.exit_check.strip() or set(phase.exit_check.strip()) <= {"-", "—"}:
            out.append(
                Finding(
                    Level.ERROR, rel, phase.line, "phase-no-exit-check",
                    f"phase {phase.number} has no exit check",
                    hint="an exit check that is not a command anyone can run is not an exit check",
                )
            )
        for tid in phase.task_ids:
            task = tasks.by_id(tid)
            if task is None:
                out.append(
                    Finding(Level.ERROR, rel, phase.line, "phase-unknown-task", f"phase {phase.number} lists unknown task {tid}")
                )
            elif task.phase is not None and task.phase != phase.number:
                out.append(
                    Finding(
                        Level.ERROR, rel, phase.line, "phase-task-mismatch",
                        f"`## Phases` puts {tid} in phase {phase.number}; its block says phase {task.phase}",
                    )
                )
    return out


def _check_coverage(tasks: tasks_format.Tasks, spec: spec_format.Spec | None) -> list[Finding]:
    out: list[Finding] = []
    rel = tasks.rel
    if not tasks.coverage:
        out.append(
            Finding(Level.ERROR, rel, 1, "tasks-no-coverage", "no `## Coverage` table")
        )
        return out

    for row in tasks.coverage:
        if not row.discharged.strip():
            out.append(
                Finding(
                    Level.ERROR, rel, row.line, "coverage-empty-cell",
                    f"{row.source} is discharged by nothing",
                    hint="task ids, `waived` with a reason on the same line, or `proof-only`",
                )
            )
        elif "waived" in row.discharged.lower() and len(row.discharged.strip()) < 12:
            out.append(
                Finding(
                    Level.WARN, rel, row.line, "coverage-waived-no-reason",
                    f"{row.source} is waived with no reason on the same line",
                )
            )

    if spec is not None:
        covered = {r.source.strip().strip("`*") for r in tasks.coverage}
        for missing in sorted((spec.requirement_ids() | spec.checklist_ids()) - covered):
            out.append(
                Finding(
                    Level.ERROR, rel, 1, "coverage-missing-row",
                    f"{missing} is in the spec and has no row in `## Coverage`",
                )
            )
    return out


def _check_phase_two(
    tasks: tasks_format.Tasks,
    spec: spec_format.Spec | None,
    plan: plan_format.Plan | None,
) -> list[Finding]:
    """Phase 2 leaves the repository red, entirely and correctly."""
    out: list[Finding] = []
    rel = tasks.rel
    phase_two = tasks.in_phase(2)

    if spec is not None and spec.assertions and not phase_two:
        out.append(
            Finding(
                Level.ERROR, rel, 1, "phase2-missing",
                "the spec has assertions and there is no phase 2",
                hint="every assertion becomes a failing executable test before any core logic exists",
            )
        )

    for task in phase_two:
        for check in task.done_when:
            if _ASSERTS_FAILURE.search(check):
                break
        else:
            if task.done_when:
                out.append(
                    Finding(
                        Level.ERROR, rel, task.line, "phase2-asserts-pass",
                        f"{task.id} is in phase 2 and its done-check does not assert failure",
                        hint="`reports 6 failing tests, 0 passing` — not `tests pass`",
                    )
                )
        if not task.verification:
            out.append(
                Finding(
                    Level.WARN, rel, task.line, "phase2-no-verification-kinds",
                    f"{task.id} names no verification kinds",
                    hint="a task that quietly writes an example test where the spec asked for a property test is a silent downgrade",
                )
            )
        for kind in task.verification:
            if kind not in spec_format.VERIFICATION_KINDS:
                out.append(
                    Finding(
                        Level.ERROR, rel, task.line, "phase2-bad-kind",
                        f"{task.id} names verification kind `{kind}`, which is not on the ladder",
                    )
                )
            elif kind in spec_format.BUDGETED_KINDS and (plan is None or not plan.verification_budget):
                out.append(
                    Finding(
                        Level.WARN, rel, task.line, "phase2-unbudgeted-kind",
                        f"{task.id} uses `{kind}`, which plan.md does not budget",
                        hint="an unbudgeted model check silently becomes an example test during the build",
                    )
                )

    if spec is not None and phase_two:
        asserted = {aid for t in phase_two for aid in t.discharges}
        for missing in sorted(spec.assertion_ids() - asserted):
            out.append(
                Finding(
                    Level.ERROR, rel, 1, "phase2-assertion-untested",
                    f"assertion {missing} has no phase-2 task writing it as a failing test",
                )
            )

    # A phase-3+ task whose done-check asserts failure is the inverse mistake.
    for task in tasks.tasks:
        if task.phase is not None and task.phase >= 3:
            for check in task.done_when:
                if _ASSERTS_FAILURE.search(check) and not _ASSERTS_PASS.search(check):
                    out.append(
                        Finding(
                            Level.WARN, rel, task.line, "task-asserts-failure-late",
                            f"{task.id} is in phase {task.phase} and its done-check asserts failure",
                        )
                    )
                    break
    return out


# ---------------------------------------------------------------------------
# skills and servers
# ---------------------------------------------------------------------------


def check_skills(layout: Layout) -> list[Finding]:
    out: list[Finding] = []
    directory = layout.skills_dir
    if not directory.is_dir():
        return out

    seen: dict[str, str] = {}
    for skill in skill_format.load_all(directory, layout.root):
        rel = skill.rel
        for code, message, line in skill_format.validate(skill):
            level = Level.WARN if code == "skill-over-budget" else Level.ERROR
            out.append(Finding(level, rel, line, code, message))
        if skill.name:
            if skill.name in seen:
                out.append(
                    Finding(Level.ERROR, rel, 1, "skill-duplicate-name", f"`{skill.name}` is also declared in {seen[skill.name]}")
                )
            seen[skill.name] = rel

    if not layout.skills_index.is_file():
        out.append(
            Finding(
                Level.WARN, layout.rel(layout.skills_index), 1, "skills-no-index",
                "no index.tsv — spawns cannot resolve a skill",
                hint="run `edify skills index`",
            )
        )
    return out


def check_mcp(layout: Layout) -> list[Finding]:
    out: list[Finding] = []
    if not layout.mcp.is_file():
        return out
    registry = mcp_format.parse(layout.mcp)
    rel = layout.rel(layout.mcp)
    for code, message, line in mcp_format.validate(registry):
        level = Level.WARN if code in ("mcp-unscoped",) else Level.ERROR
        out.append(Finding(level, rel, line, code, message))
    return out
