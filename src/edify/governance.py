"""The ledger: every file EDIFY put in this repository, and where it came from.

A skill file has carried its own provenance since the first release. Nothing else
did — a command file, a format example, the seeded registry and the scraped
conventions all arrived with no record of what installed them, from which version,
or whether anybody has changed them since. That is a gap in exactly the thing
`docs/design/01-principles.md` P7 asks for: a control counts as governance if a person
can look at it and tell whether the work complied.

So every file EDIFY writes is recorded in `.edify/governance.tsv`, one row each:
where it is, what it is, where it came from, under what licence, and its hash at the
moment it was installed. `edify governance verify` reads that back against the disk.

It is a ledger, not a lock. Nothing here prevents an edit — it makes one visible,
which is the whole claim. Five origins, and `verify` treats them differently
because they are owned by different people:

    library    a curated skill entry — EDIFY's to replace, so an edit is a warning
    shipped    a command or format file — same
    seeded     the MCP registry, written once and then the repository's to maintain
    scraped    conventions, derived from this repository's own config files
    generated  a host command pointer
    merged     CLAUDE.md, AGENTS.md and the rest, where EDIFY owns a block and
               somebody else owns the file
    answered   .edify/profile.md — what a person said when `init new` asked

The graph is deliberately not in here. It is regenerated output, it changes on every
build, and it already carries its own checksums in `.edify/graph/meta`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .errors import EdifyError
from .formats import skill as skill_format
from .host import written_by_edify
from .paths import Layout
from .tsv import read_rows, sha256_file, write_rows

LEDGER_HEADER = ("path", "kind", "origin", "provenance", "license", "source", "sha256", "edify")

# The licence the shipped methodology tree is under — the same one this repository
# carries, so `edify governance list`, LICENSE, and the README cannot drift apart.
# Skill entries override it from their own frontmatter, which is how an adapted
# entry stays governed by its upstream.
SHIPPED_LICENSE = "FSL-1.1-Apache-2.0"

ORIGINS = ("library", "shipped", "seeded", "scraped", "generated", "merged", "answered")

# An edit to one of these is EDIFY's business: `upgrade` will overwrite it.
EDIFY_OWNED = ("library", "shipped", "generated")


@dataclass(frozen=True)
class Record:
    path: str
    kind: str
    origin: str
    provenance: str
    license: str
    source: str
    sha256: str
    edify: str

    def row(self) -> list[str]:
        return [
            self.path,
            self.kind,
            self.origin,
            self.provenance,
            self.license,
            self.source,
            self.sha256,
            self.edify,
        ]

    def as_dict(self) -> dict[str, str]:
        return dict(zip(LEDGER_HEADER, self.row()))


@dataclass(frozen=True)
class Problem:
    path: str
    state: str  # missing | modified | edited | unrecorded
    detail: str

    @property
    def serious(self) -> bool:
        """`edited` is a repository doing what it is entitled to do with its own file."""
        return self.state in ("missing", "modified", "unrecorded")

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "state": self.state, "detail": self.detail}


# -- deriving the ledger from the disk ---------------------------------------


def scan(layout: Layout) -> list[Record]:
    """What is on the governed surface right now, with each file's attribution.

    A pure function over files, like everything else in this CLI: run it twice over
    an unchanged tree and it produces the same rows in the same order.
    """
    records: list[Record] = []

    for path in sorted(layout.skills_dir.glob("*.md")):
        records.append(_skill_record(layout, path))

    for path in sorted(layout.commands_dir.glob("*.md")):
        records.append(_shipped_record(layout, path, "command"))

    for path in sorted(layout.formats_dir.glob("*.md")):
        records.append(_shipped_record(layout, path, "format"))

    if layout.mcp.is_file():
        records.append(
            Record(
                path=layout.rel(layout.mcp),
                kind="registry",
                origin="seeded",
                provenance="original",
                license=SHIPPED_LICENSE,
                source=f"edify-cli@{__version__}",
                sha256=sha256_file(layout.mcp),
                edify=__version__,
            )
        )

    if layout.conventions.is_file():
        records.append(
            Record(
                path=layout.rel(layout.conventions),
                kind="conventions",
                origin="scraped",
                provenance="client",
                license="-",
                source="this repository's own config files",
                sha256=sha256_file(layout.conventions),
                edify=__version__,
            )
        )

    # The host runtime's mirror — commands, skills, and agents. All three families are
    # generated pointers, so an edit to one is EDIFY's business and `init` will bring it
    # back in line. A file EDIFY did not write is somebody's own and stays out of the
    # ledger; that is what keeps the hand-authored harvest skill from being reported as
    # modified every time anyone touches it, and it is why a hand-written subagent under
    # `.claude/agents/` is left alone the same way.
    for pointers, pattern in layout.host_trees():
        if not pointers.is_dir():
            continue
        for path in sorted(pointers.glob(pattern)):
            if not written_by_edify(path):
                continue
            records.append(
                Record(
                    path=layout.rel(path),
                    kind="pointer",
                    origin="generated",
                    provenance="original",
                    license=SHIPPED_LICENSE,
                    source=f"edify-cli@{__version__}",
                    sha256=sha256_file(path),
                    edify=__version__,
                )
            )

    # Every instruction file any runtime reads — CLAUDE.md, AGENTS.md, GEMINI.md, the
    # Copilot file, the Cursor rule. Hashed as `-` on purpose: EDIFY owns the block
    # between its markers and nothing else in the file, so hashing the whole thing
    # would report every edit somebody makes to their own instructions as a
    # governance event.
    for path in layout.instruction_files():
        if not path.is_file():
            continue
        records.append(
            Record(
                path=layout.rel(path),
                kind="instructions",
                origin="merged",
                provenance="client",
                license="-",
                source=f"edify-cli@{__version__} owns the edify:begin/end block only",
                sha256="-",
                edify=__version__,
            )
        )

    if layout.profile.is_file():
        # The one file here nobody derived from anything: a person answered eight
        # questions. Recorded so `list` accounts for it, hashed so an edit shows, and
        # `answered` so nothing EDIFY does later treats it as ours to replace.
        records.append(
            Record(
                path=layout.rel(layout.profile),
                kind="profile",
                origin="answered",
                provenance="client",
                license="-",
                source="answered at `edify init new`",
                sha256=sha256_file(layout.profile),
                edify=__version__,
            )
        )

    return records


def _skill_record(layout: Layout, path: Path) -> Record:
    parsed = skill_format.parse(path, layout.rel(path))
    # `license: -` in an original entry means "whatever EDIFY ships under". An
    # adapted entry names its upstream licence and that is what governs it.
    declared = parsed.license if parsed.license not in ("", "-") else SHIPPED_LICENSE
    return Record(
        path=layout.rel(path),
        kind=parsed.kind or "skill",
        origin="library",
        provenance=parsed.provenance or "-",
        license=declared,
        source=parsed.source or f"edify-cli@{__version__}",
        sha256=sha256_file(path),
        edify=__version__,
    )


def _shipped_record(layout: Layout, path: Path, kind: str) -> Record:
    return Record(
        path=layout.rel(path),
        kind=kind,
        origin="shipped",
        provenance="original",
        license=SHIPPED_LICENSE,
        source=f"edify-cli@{__version__}",
        sha256=sha256_file(path),
        edify=__version__,
    )


# -- reading and writing the ledger ------------------------------------------


def rebuild(layout: Layout) -> list[Record]:
    """Re-derive the ledger from the disk and write it. The baseline moves to now."""
    records = scan(layout)
    write_rows(layout.governance, [r.row() for r in records], LEDGER_HEADER)
    return records


def load(layout: Layout) -> list[Record]:
    if not layout.governance.is_file():
        raise EdifyError(
            "no governance ledger",
            hint="run `edify governance rebuild` — or `edify init`, which writes one",
        )
    out: list[Record] = []
    for row in read_rows(layout.governance):
        if len(row) >= len(LEDGER_HEADER):
            out.append(Record(*row[: len(LEDGER_HEADER)]))
    return out


def verify(layout: Layout) -> list[Problem]:
    """The ledger against the disk. Three ways they disagree, and they differ in kind."""
    recorded = {r.path: r for r in load(layout)}
    present = {r.path: r for r in scan(layout)}
    problems: list[Problem] = []

    for path in sorted(set(recorded) | set(present)):
        was = recorded.get(path)
        now = present.get(path)
        if was and not now:
            problems.append(Problem(path, "missing", f"recorded as {was.origin}, not on disk"))
            continue
        if now and not was:
            problems.append(
                Problem(path, "unrecorded", f"on disk as {now.origin}, absent from the ledger")
            )
            continue
        assert was and now
        if was.sha256 in ("-", "") or now.sha256 in ("-", ""):
            continue
        if was.sha256 != now.sha256:
            state = "modified" if was.origin in EDIFY_OWNED else "edited"
            detail = (
                f"changed since it was installed ({was.origin}) — `edify upgrade` will replace it"
                if state == "modified"
                else f"changed since it was written ({was.origin}) — this file is yours to edit"
            )
            problems.append(Problem(path, state, detail))
    return problems


def summary(records: list[Record]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.origin] = counts.get(record.origin, 0) + 1
    return counts
