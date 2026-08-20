"""The skill index and the resolution lookup.

`resolve` is what `/build` performs before every spawn: a lookup over a sorted TSV
keyed on `role · phase · tech`, one line of output, no model involved. Not because
a model's judgment is bad — because a lookup is free, deterministic, and gives the
same answer on Tuesday.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import EdifyError
from .formats import skill as skill_format
from .paths import Layout
from .tsv import read_rows, write_rows

INDEX_HEADER = ("role", "phase", "tech", "name", "path")


@dataclass(frozen=True)
class Entry:
    role: str
    phase: str
    tech: str
    name: str
    path: str

    def row(self) -> list[str]:
        return [self.role, self.phase, self.tech, self.name, self.path]


def build_index(layout: Layout) -> tuple[int, list[str]]:
    """Walk `.edify/skills/`, validate, and write the sorted lookup table.

    An invalid file is skipped rather than indexed, and its name is returned so
    the caller can say so. Loose metadata is fine for a wiki and useless here.
    """
    skipped: list[str] = []
    rows: list[list[str]] = []
    for skill in skill_format.load_all(layout.skills_dir, layout.root):
        problems = skill_format.validate(skill)
        blocking = [p for p in problems if p[0] != "skill-over-budget"]
        if blocking:
            skipped.append(f"{skill.rel}: {blocking[0][1]}")
            continue
        rows.extend(skill.index_rows())
    write_rows(layout.skills_index, rows, INDEX_HEADER)
    return len(rows), skipped


def load_index(layout: Layout) -> list[Entry]:
    if not layout.skills_index.is_file():
        raise EdifyError(
            "no skill index",
            hint="run `edify skills index`",
        )
    return [Entry(*row[:5]) for row in read_rows(layout.skills_index) if len(row) >= 5]


def resolve(layout: Layout, role: str, phase: str, tech: str | None = None) -> Entry:
    """Exact tech match, then `any`, then the role's default.

    If none of the three resolve, the task fails at the gate rather than at build
    time — a task whose role has no skill is a plan defect, and the cheap moment
    to find it is before anything runs.
    """
    entries = load_index(layout)
    by_role = [e for e in entries if e.role == role]
    if not by_role:
        raise EdifyError(
            f"no skill for role `{role}`",
            hint="`edify skills list` shows what is installed; a role with no skill is a plan defect",
        )

    in_phase = [e for e in by_role if e.phase == str(phase)] or by_role

    if tech:
        wanted = {t.strip().lower() for t in tech.replace(",", " ").split() if t.strip()}
        exact = [e for e in in_phase if e.tech.lower() in wanted]
        if exact:
            return sorted(exact, key=lambda e: (e.tech, e.name))[0]

    generic = [e for e in in_phase if e.tech.lower() == "any"]
    if generic:
        return sorted(generic, key=lambda e: e.name)[0]

    return sorted(in_phase, key=lambda e: (e.tech, e.name))[0]


def select_for_stack(source_dir: Path, tech: list[str]) -> list[Path]:
    """Which library entries this repository's stack matches.

    A Python API repository does not receive the React implementer. Every unused
    skill file is context cost and, for anything sourced from outside, attack
    surface.
    """
    wanted = {t.lower() for t in tech}
    chosen: list[Path] = []
    for path in sorted(source_dir.glob("*.md")):
        skill = skill_format.parse(path, path.name)
        if not skill.role:
            continue
        techs = {t.lower() for t in skill.tech}
        if "any" in techs or techs & wanted:
            chosen.append(path)
    return chosen
