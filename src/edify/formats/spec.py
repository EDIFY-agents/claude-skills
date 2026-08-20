"""`spec.md` — what is being built and why.

Parses the sections a downstream command actually consumes: the requirements, the
assertions with their verification kinds, the closure checklist, and the open
questions. Everything else in the file is for a human and is left alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .document import Document, Row, parse_document

# The whole legal set, cheapest to strongest (`docs/design/architecture/08-verification.md` §1).
VERIFICATION_KINDS = ("types", "example", "contract", "property", "model", "proof", "observation")

# Above this rung an assertion has to be budgeted in plan.md, because an
# unbudgeted model check silently becomes an example test during the build.
BUDGETED_KINDS = ("model", "proof")

REQUIRED_SECTIONS = ("brief", "intent", "constraints", "requirements", "assertions")
EXPECTED_SECTIONS = REQUIRED_SECTIONS + ("what this entails", "open questions", "non-goals")


@dataclass
class Requirement:
    id: str
    text: str
    assertions: list[str]
    line: int


@dataclass
class Assertion:
    id: str
    text: str
    kind: str
    citation: str
    line: int


@dataclass
class ChecklistItem:
    id: str
    text: str
    status: str
    line: int


@dataclass
class Spec:
    doc: Document
    feature: str = ""
    status: str = ""
    requirements: list[Requirement] = field(default_factory=list)
    assertions: list[Assertion] = field(default_factory=list)
    checklist: list[ChecklistItem] = field(default_factory=list)
    open_questions: list[Row] = field(default_factory=list)

    @property
    def rel(self) -> str:
        return self.doc.rel

    def assertion_ids(self) -> set[str]:
        return {a.id for a in self.assertions}

    def requirement_ids(self) -> set[str]:
        return {r.id for r in self.requirements}

    def checklist_ids(self) -> set[str]:
        return {c.id for c in self.checklist}

    def kind_of(self, assertion_id: str) -> str:
        for a in self.assertions:
            if a.id == assertion_id:
                return a.kind
        return ""


def parse(path: Path, rel: str | None = None) -> Spec:
    doc = parse_document(path, rel)
    spec = Spec(doc=doc)
    spec.feature = doc.frontmatter.get("feature", "")
    spec.status = doc.frontmatter.get("status", "")

    section = doc.section("Requirements")
    if section:
        for table in section.tables:
            id_col = table.column("id", "#")
            text_col = table.column("requirement", "what it is", "description")
            asserts_col = table.column("assertions", "asserted by", "proven by")
            for row in table.rows:
                rid = _clean(row.get(id_col if id_col >= 0 else 0))
                if not rid or rid.startswith("-"):
                    continue
                spec.requirements.append(
                    Requirement(
                        id=rid,
                        text=row.get(text_col if text_col >= 0 else 1),
                        assertions=_ids(row.get(asserts_col)) if asserts_col >= 0 else [],
                        line=row.line,
                    )
                )

    section = doc.section("Assertions")
    if section:
        for table in section.tables:
            id_col = table.column("id", "#")
            text_col = table.column("assertion", "statement", "what it is")
            kind_col = table.column("verification", "kind", "verified by", "how")
            cite_col = table.column("citation", "where", "cite")
            for row in table.rows:
                aid = _clean(row.get(id_col if id_col >= 0 else 0))
                if not aid or aid.startswith("-"):
                    continue
                spec.assertions.append(
                    Assertion(
                        id=aid,
                        text=row.get(text_col if text_col >= 0 else 1),
                        kind=_clean(row.get(kind_col)).lower() if kind_col >= 0 else "",
                        citation=row.get(cite_col) if cite_col >= 0 else "",
                        line=row.line,
                    )
                )

    section = doc.section("What this entails", "Closure checklist")
    if section:
        for table in section.tables:
            id_col = table.column("id", "#")
            text_col = table.column("entails", "what it is", "item", "requirement")
            status_col = table.column("status", "state", "satisfied by", "resolution")
            for row in table.rows:
                cid = _clean(row.get(id_col if id_col >= 0 else 0))
                if not cid or cid.startswith("-"):
                    continue
                spec.checklist.append(
                    ChecklistItem(
                        id=cid,
                        text=row.get(text_col if text_col >= 0 else 1),
                        status=row.get(status_col) if status_col >= 0 else "",
                        line=row.line,
                    )
                )

    section = doc.section("Open questions")
    if section:
        for table in section.tables:
            spec.open_questions.extend(table.rows)

    return spec


def _clean(value: str) -> str:
    return value.strip().strip("`*_ ")


def _ids(value: str) -> list[str]:
    out: list[str] = []
    for token in value.replace(",", " ").split():
        token = _clean(token)
        if token and token not in ("-", "—", "none"):
            out.append(token)
    return out
