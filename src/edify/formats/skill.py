"""The skill file: eight frontmatter fields and a short plain body.

Loose metadata is fine for a wiki and useless for a lookup table, so an unknown
key, a missing required key, or a value outside its set makes the file invalid —
reported by `edify check` and skipped by the indexer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .document import parse_document

REQUIRED_FIELDS = ("name", "description", "kind", "role", "phase", "tech", "provenance")
OPTIONAL_FIELDS = ("license", "source", "updated")
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

KINDS = ("skill", "agent")
ROLES = ("planner", "adversary", "test", "implementer", "debugger", "verifier")
PROVENANCE = ("original", "adapted", "client")
PHASES = tuple(str(n) for n in range(8))

# ≤80 lines for a skill, ≤150 for a deep specialist carrying real stack-specific
# knowledge. Past about eighty lines the marginal line displaces the actual work.
BUDGET = {"skill": 80, "agent": 150}

_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass
class Skill:
    path: Path
    rel: str
    name: str = ""
    description: str = ""
    kind: str = ""
    role: str = ""
    phases: list[str] = field(default_factory=list)
    tech: list[str] = field(default_factory=list)
    provenance: str = ""
    license: str = ""
    source: str = ""
    body_lines: int = 0
    total_lines: int = 0
    field_lines: dict[str, int] = field(default_factory=dict)
    unknown_fields: list[str] = field(default_factory=list)

    @property
    def budget(self) -> int:
        return BUDGET.get(self.kind, 80)

    @property
    def over_budget(self) -> bool:
        return self.body_lines > self.budget

    def index_rows(self) -> list[list[str]]:
        """One row per (role, phase, tech) triple — the shape `resolve` searches."""
        rows: list[list[str]] = []
        techs = self.tech or ["any"]
        phases = self.phases or ["-"]
        for phase in phases:
            for tech in techs:
                rows.append([self.role, phase, tech, self.name, self.rel])
        return rows


def parse(path: Path, rel: str | None = None) -> Skill:
    doc = parse_document(path, rel)
    skill = Skill(path=path, rel=rel or path.as_posix())
    skill.total_lines = len(doc.lines)
    skill.body_lines = max(0, len(doc.lines) - doc.frontmatter_end)
    skill.field_lines = dict(doc.frontmatter_lines)

    fm = doc.frontmatter
    skill.name = fm.get("name", "")
    skill.description = fm.get("description", "")
    skill.kind = fm.get("kind", "")
    skill.role = fm.get("role", "")
    skill.phases = doc.list_field("phase")
    skill.tech = doc.list_field("tech")
    skill.provenance = fm.get("provenance", "")
    skill.license = fm.get("license", "")
    skill.source = fm.get("source", "")
    skill.unknown_fields = [k for k in fm if k not in ALL_FIELDS]
    return skill


def validate(skill: Skill) -> list[tuple[str, str, int]]:
    """(code, message, line) for everything wrong with this file's metadata."""
    problems: list[tuple[str, str, int]] = []

    def at(key: str) -> int:
        return skill.field_lines.get(key, 1)

    for key in REQUIRED_FIELDS:
        value = getattr(skill, "phases" if key == "phase" else key, "")
        if not value:
            problems.append(("skill-missing-field", f"required frontmatter key `{key}` is missing", 1))

    if skill.name and not _NAME.match(skill.name):
        problems.append(("skill-bad-name", f"`name: {skill.name}` is not [a-z0-9-]+", at("name")))
    if skill.kind and skill.kind not in KINDS:
        problems.append(("skill-bad-kind", f"`kind: {skill.kind}` is not one of {'|'.join(KINDS)}", at("kind")))
    if skill.role and skill.role not in ROLES:
        problems.append(("skill-bad-role", f"`role: {skill.role}` is not one of {'|'.join(ROLES)}", at("role")))
    for phase in skill.phases:
        if phase not in PHASES:
            problems.append(("skill-bad-phase", f"phase `{phase}` is not 0-7", at("phase")))
    if skill.provenance and skill.provenance not in PROVENANCE:
        problems.append(
            ("skill-bad-provenance", f"`provenance: {skill.provenance}` is not one of {'|'.join(PROVENANCE)}", at("provenance"))
        )
    if skill.provenance == "adapted" and not skill.license:
        problems.append(
            ("skill-missing-license", "an adapted skill needs `license` — an SPDX id plus repo@commit", at("provenance"))
        )
    for key in skill.unknown_fields:
        problems.append(("skill-unknown-field", f"unknown frontmatter key `{key}`", at(key)))
    if skill.over_budget:
        problems.append(
            (
                "skill-over-budget",
                f"{skill.body_lines} lines of body, budget is {skill.budget} for kind `{skill.kind or 'skill'}`",
                1,
            )
        )
    return problems


def load_all(directory: Path, root: Path | None = None) -> list[Skill]:
    out: list[Skill] = []
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.md")):
        rel = path.relative_to(root).as_posix() if root else path.name
        out.append(parse(path, rel))
    return out
