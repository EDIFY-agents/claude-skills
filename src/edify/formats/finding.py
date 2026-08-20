"""What `edify check` produces.

A finding is a line a person can act on: where it is, what rule noticed it, and
what to do. Findings are reported, never enforced — `docs/design/01-principles.md` P7
says why, and `--exit-code` is how a customer who needs a hard block gets one in
their own CI, owned by them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Level(str, Enum):
    ERROR = "error"      # the format contract is broken; a downstream command will misread it
    WARN = "warn"        # legal but costly — a whole-file reference, an over-budget skill
    INFO = "info"        # worth knowing, never worth stopping for


@dataclass(frozen=True)
class Finding:
    level: Level
    file: str
    line: int
    code: str
    message: str
    hint: str = ""

    def render(self) -> str:
        where = f"{self.file}:{self.line}" if self.line else self.file
        out = f"{where}: {self.level.value}: [{self.code}] {self.message}"
        if self.hint:
            out += f"\n    {self.hint}"
        return out

    def as_dict(self) -> dict[str, object]:
        return {
            "level": self.level.value,
            "file": self.file,
            "line": self.line,
            "code": self.code,
            "message": self.message,
            "hint": self.hint,
        }


def sort_findings(findings: list[Finding]) -> list[Finding]:
    order = {Level.ERROR: 0, Level.WARN: 1, Level.INFO: 2}
    return sorted(findings, key=lambda f: (f.file, f.line, order[f.level], f.code))
