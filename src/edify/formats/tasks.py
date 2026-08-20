"""`tasks.md` — exactly what will change, where, in what order.

The most important format in the system. Its precision is the difference between a
build that runs on a cheap model in one pass and one that stalls on every third
task, so this parser is strict about the five questions every task block answers:
where does it land, what does right look like, what are the steps, how do I know it
worked, and what does it depend on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .document import Document, Row, Section, Table, parse_document

PHASE_NAMES = {
    0: "Foundation",
    1: "Contracts",
    2: "Verification",
    3: "Core",
    4: "Surfaces",
    5: "Integration",
    6: "Hardening",
    7: "Proof",
}

FILE_ACTIONS = ("new", "edit", "delete")

_TASK_HEADING = re.compile(r"^(?P<id>T-\d+[a-z]?)\s*[·:\-—]\s*(?P<title>.+)$")
_PHASE_FIELD = re.compile(r"\bPhase\s+(?P<phase>\d+)\b", re.IGNORECASE)
_ROLE_FIELD = re.compile(r"\bRole\s+(?P<role>[\w\-]+)", re.IGNORECASE)
_SKILL_FIELD = re.compile(r"\bSkill\s+(?P<skill>[\w\-]+)", re.IGNORECASE)
_SIZE_FIELD = re.compile(r"\bSize\s+(?P<size>xs|s|m|l|xl)\b", re.IGNORECASE)
_DISCHARGES = re.compile(r"^\s*Discharges\s+(?P<ids>.+)$", re.IGNORECASE)
_VERIFICATION = re.compile(r"^\s*Verification\s+(?P<kinds>.+)$", re.IGNORECASE)
_DEPENDS = re.compile(r"^\s*Depends on\s+(?P<ids>.*?)(?:·|$)", re.IGNORECASE)
_PARALLEL = re.compile(r"Parallel with\s+(?P<ids>.+)$", re.IGNORECASE)
_RANGE = re.compile(r"^(?P<start>\d+)\s*[-–]\s*(?P<end>\d+)$")


@dataclass
class FileRef:
    path: str
    range: str
    action: str
    line: int

    @property
    def has_range(self) -> bool:
        return bool(_RANGE.match(self.range.strip()) or self.range.strip().isdigit())

    @property
    def bounds(self) -> tuple[int, int] | None:
        text = self.range.strip()
        m = _RANGE.match(text)
        if m:
            return int(m.group("start")), int(m.group("end"))
        if text.isdigit():
            return int(text), int(text)
        return None


@dataclass
class Task:
    id: str
    title: str
    line: int
    end_line: int
    phase: int | None = None
    role: str = ""
    skill: str = ""
    size: str = ""
    discharges: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    parallel_with: list[str] = field(default_factory=list)
    files: list[FileRef] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    done_when: list[str] = field(default_factory=list)
    files_table_line: int = 0

    @property
    def edits(self) -> list[FileRef]:
        return [f for f in self.files if f.action.lower() == "edit"]

    @property
    def paths(self) -> list[str]:
        return [f.path for f in self.files]


@dataclass
class Phase:
    number: int
    name: str
    task_ids: list[str]
    parallel: str
    exit_check: str
    line: int


@dataclass
class CoverageRow:
    source: str
    what: str
    cells: list[str]
    line: int

    @property
    def discharged(self) -> str:
        return " ".join(c for c in self.cells if c.strip())


@dataclass
class Tasks:
    doc: Document
    feature: str = ""
    status: str = ""
    spec_ref: str = ""
    tasks: list[Task] = field(default_factory=list)
    phases: list[Phase] = field(default_factory=list)
    coverage: list[CoverageRow] = field(default_factory=list)
    decisions: list[Row] = field(default_factory=list)

    @property
    def rel(self) -> str:
        return self.doc.rel

    def by_id(self, task_id: str) -> Task | None:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def in_phase(self, number: int) -> list[Task]:
        return [t for t in self.tasks if t.phase == number]


def parse(path: Path, rel: str | None = None) -> Tasks:
    doc = parse_document(path, rel)
    out = Tasks(doc=doc)
    out.feature = doc.frontmatter.get("feature", "")
    out.status = doc.frontmatter.get("status", "")
    out.spec_ref = doc.frontmatter.get("spec", "")

    current_phase: int | None = None
    for section in doc.sections:
        if section.level == 2:
            m = re.match(r"^phase\s+(\d+)", section.key)
            current_phase = int(m.group(1)) if m else None
            if section.key.startswith("phases"):
                out.phases.extend(_phases(section))
            elif section.key.startswith("coverage"):
                out.coverage.extend(_coverage(section))
            elif section.key.startswith("decisions"):
                for table in section.tables:
                    out.decisions.extend(table.rows)
            continue

        heading = _TASK_HEADING.match(section.title)
        if heading and section.level == 3:
            out.tasks.append(_task(section, heading, current_phase))

    return out


# ---------------------------------------------------------------------------


def _task(section: Section, heading: re.Match[str], fallback_phase: int | None) -> Task:
    task = Task(
        id=heading.group("id"),
        title=heading.group("title").strip(),
        line=section.line,
        end_line=section.end_line,
        phase=fallback_phase,
    )

    block: str | None = None
    for offset, raw in enumerate(section.lines):
        lineno = section.line + 1 + offset
        line = raw.rstrip()
        stripped = line.strip()
        lowered = stripped.lower()

        m = _PHASE_FIELD.search(line)
        if m and not task.role:
            task.phase = int(m.group("phase"))
        m = _ROLE_FIELD.search(line)
        if m and not task.role:
            task.role = m.group("role")
        m = _SKILL_FIELD.search(line)
        if m and not task.skill:
            task.skill = m.group("skill")
        m = _SIZE_FIELD.search(line)
        if m and not task.size:
            task.size = m.group("size").lower()

        m = _DISCHARGES.match(line)
        if m:
            task.discharges = _ids(m.group("ids"))
            continue
        m = _VERIFICATION.match(line)
        if m:
            task.verification = _kinds(m.group("kinds"))
            continue
        m = _DEPENDS.match(line)
        if m:
            task.depends_on = _ids(m.group("ids"))
        m = _PARALLEL.search(line)
        if m:
            task.parallel_with = _ids(m.group("ids"))

        if lowered in ("files", "**files**", "files:"):
            block = "files"
            continue
        if lowered.startswith("follow the pattern"):
            block = "pattern"
            continue
        if lowered in ("steps", "**steps**", "steps:"):
            block = "steps"
            continue
        if lowered.startswith("done when"):
            block = "done"
            continue
        if stripped.startswith("#") or lowered.startswith("files:"):
            block = None

        if block == "pattern" and stripped.startswith(("-", "*")):
            task.patterns.append(stripped.lstrip("-* ").strip())
        elif block == "pattern" and stripped and not stripped.startswith("|"):
            if task.patterns:
                task.patterns[-1] += " " + stripped
        elif block == "steps" and re.match(r"^\d+[.)]\s+", stripped):
            task.steps.append(re.sub(r"^\d+[.)]\s+", "", stripped))
        elif block == "steps" and stripped and task.steps and not stripped.startswith("|"):
            task.steps[-1] += " " + stripped
        elif block == "done" and stripped.startswith(("-", "*")):
            task.done_when.append(stripped.lstrip("-* ").strip())
        elif block == "done" and stripped and task.done_when and not stripped.startswith("|"):
            task.done_when[-1] += " " + stripped

    for table in section.tables:
        path_col = table.column("path", "file")
        range_col = table.column("range", "lines")
        action_col = table.column("action")
        if path_col < 0 or action_col < 0:
            continue
        task.files_table_line = table.line
        for row in table.rows:
            path_value = row.get(path_col).strip("`")
            if not path_value or set(path_value) <= {"-", "—"}:
                continue
            task.files.append(
                FileRef(
                    path=path_value,
                    range=row.get(range_col) if range_col >= 0 else "",
                    action=row.get(action_col),
                    line=row.line,
                )
            )
    return task


def _phases(section: Section) -> list[Phase]:
    out: list[Phase] = []
    for table in section.tables:
        num_col = table.column("#", "phase number")
        name_col = table.column("phase", "name")
        tasks_col = table.column("tasks")
        parallel_col = table.column("parallel-safe", "parallel")
        exit_col = table.column("exit check", "exit")
        for row in table.rows:
            raw_num = row.get(num_col if num_col >= 0 else 0)
            if not raw_num.strip().isdigit():
                continue
            out.append(
                Phase(
                    number=int(raw_num.strip()),
                    name=row.get(name_col) if name_col >= 0 else "",
                    task_ids=_ids(row.get(tasks_col)) if tasks_col >= 0 else [],
                    parallel=row.get(parallel_col) if parallel_col >= 0 else "",
                    exit_check=row.get(exit_col) if exit_col >= 0 else "",
                    line=row.line,
                )
            )
    return out


def _coverage(section: Section) -> list[CoverageRow]:
    out: list[CoverageRow] = []
    for table in section.tables:
        for row in table.rows:
            source = row.get(0)
            if not source or set(source) <= {"-", "—", " "}:
                continue
            out.append(
                CoverageRow(
                    source=source,
                    what=row.get(1),
                    cells=[row.get(i) for i in range(2, max(3, len(table.headers)))],
                    line=row.line,
                )
            )
    return out


def _ids(value: str) -> list[str]:
    out: list[str] = []
    for token in re.split(r"[,\s·∥]+", value):
        token = token.strip().strip("`*_")
        if token and token not in ("-", "—", "and", "all", "none"):
            out.append(token)
    return out


def _kinds(value: str) -> list[str]:
    cleaned = re.sub(r"\([^)]*\)", " ", value)
    return [t.strip().lower() for t in re.split(r"[,\s]+", cleaned) if t.strip()]
