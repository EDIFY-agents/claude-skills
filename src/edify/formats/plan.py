"""`plan.md` — how, with what, and in what order.

Two sections carry the weight and both are checked: the technology decisions, where
a row without an exact version or a named alternative is not a decision, and the
context seeds, where a pointer without a line range transfers its cost downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .document import Citation, Document, citations, parse_document

EXPECTED_SECTIONS = (
    "milestones",
    "technology decisions",
    "cross-cutting",
    "per-milestone",
    "risks",
)


@dataclass
class Decision:
    id: str
    text: str
    version: str
    beat: str
    why: str
    line: int

    @property
    def is_default(self) -> bool:
        """A row with no alternative is a default, and should say so."""
        lowered = self.beat.strip().lower()
        return lowered in ("", "-", "—", "default", "n/a", "none")


@dataclass
class Milestone:
    id: str
    delivers: str
    requirements: list[str]
    gate: str
    size: str
    line: int


@dataclass
class Plan:
    doc: Document
    feature: str = ""
    status: str = ""
    decisions: list[Decision] = field(default_factory=list)
    milestones: list[Milestone] = field(default_factory=list)
    seeds: list[Citation] = field(default_factory=list)
    verification_budget: list[str] = field(default_factory=list)

    @property
    def rel(self) -> str:
        return self.doc.rel


def parse(path: Path, rel: str | None = None) -> Plan:
    doc = parse_document(path, rel)
    plan = Plan(doc=doc)
    plan.feature = doc.frontmatter.get("feature", "")
    plan.status = doc.frontmatter.get("status", "")

    section = doc.section("Technology decisions", "Decisions")
    if section:
        for table in section.tables:
            id_col = table.column("#", "id")
            text_col = table.column("decision", "what")
            version_col = table.column("version")
            beat_col = table.column("beat", "alternative", "over")
            why_col = table.column("why", "reason")
            for row in table.rows:
                did = row.get(id_col if id_col >= 0 else 0).strip()
                if not did or set(did) <= {"-", "—", " "}:
                    continue
                plan.decisions.append(
                    Decision(
                        id=did,
                        text=row.get(text_col if text_col >= 0 else 1),
                        version=row.get(version_col) if version_col >= 0 else "",
                        beat=row.get(beat_col) if beat_col >= 0 else "",
                        why=row.get(why_col) if why_col >= 0 else "",
                        line=row.line,
                    )
                )

    section = doc.section("Milestones")
    if section:
        for table in section.tables:
            id_col = table.column("id", "#")
            delivers_col = table.column("delivers", "goal", "what")
            reqs_col = table.column("requirements covered", "requirements", "covers")
            gate_col = table.column("gate")
            size_col = table.column("size")
            for row in table.rows:
                mid = row.get(id_col if id_col >= 0 else 0).strip()
                if not mid or set(mid) <= {"-", "—", " "}:
                    continue
                plan.milestones.append(
                    Milestone(
                        id=mid,
                        delivers=row.get(delivers_col) if delivers_col >= 0 else "",
                        requirements=[
                            t.strip()
                            for t in row.get(reqs_col).replace(",", " ").split()
                            if reqs_col >= 0 and t.strip()
                        ],
                        gate=row.get(gate_col) if gate_col >= 0 else "",
                        size=row.get(size_col) if size_col >= 0 else "",
                        line=row.line,
                    )
                )

    plan.seeds = _seeds(doc)
    section = doc.section("Cross-cutting")
    if section:
        for line in section.lines:
            lowered = line.lower()
            if "verification budget" in lowered or "model check" in lowered or "proof" in lowered:
                plan.verification_budget.append(line.strip())
    return plan


def _seeds(doc: Document) -> list[Citation]:
    """Every citation under a `Context seeds` heading or block."""
    out: list[Citation] = []
    for section in doc.sections:
        collecting = section.key.startswith("context seeds")
        start = section.line + 1
        for offset, line in enumerate(section.lines):
            stripped = line.strip().lower()
            if stripped.startswith("context seeds"):
                collecting = True
                continue
            if collecting:
                if not line.strip():
                    if out and not stripped:
                        collecting = collecting and True
                    continue
                if line.strip().startswith("#") or stripped.startswith("affected files"):
                    collecting = False
                    continue
                out.extend(citations(line, first_line=start + offset))
    return out
