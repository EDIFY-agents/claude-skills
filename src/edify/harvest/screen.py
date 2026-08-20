"""Step ② — mechanical, fail-closed, no judgment.

Three checks, and none of them is a reading. A model is good at deciding whether a
skill file is *worth* having and bad at deciding whether we are *allowed* to have
it, so the second question is answered by a lookup table here and never by a prompt.

Precedence when several checks fail: an injection hit always wins and sends the
candidate to **quarantine**, because a flagged file preserved on disk is worth more
than a rejected one thrown away — someone will want to know what was attempted. A
licence or duplicate failure with a clean scan is a plain **reject**.

Every check is negative-by-default. An unrecognised licence string is not "probably
fine"; it is `NONE-FOUND`, and `NONE-FOUND` is rejected.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

# Permissive only, as SPDX ids. Copyleft is absent deliberately rather than by
# oversight: this library composes into other companies' repositories, and a
# reciprocal obligation travelling into a customer's tree is not ours to accept.
ALLOWED_LICENSES = (
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "Unlicense",
    "CC0-1.0",
)

# What people actually write in a LICENSE header, mapped to the id it means. An
# input that is not in this table and not already an allowed id stays unresolved.
_LICENSE_ALIASES = {
    "mit": "MIT",
    "mit license": "MIT",
    "expat": "MIT",
    "apache 2": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "apache-2": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "asl-2.0": "Apache-2.0",
    "bsd": "",  # ambiguous between 2- and 3-clause, so it resolves to nothing
    "bsd-2": "BSD-2-Clause",
    "bsd 2-clause": "BSD-2-Clause",
    "simplified bsd": "BSD-2-Clause",
    "bsd-3": "BSD-3-Clause",
    "bsd 3-clause": "BSD-3-Clause",
    "new bsd": "BSD-3-Clause",
    "isc": "ISC",
    "unlicense": "Unlicense",
    "the unlicense": "Unlicense",
    "cc0": "CC0-1.0",
    "cc0 1.0": "CC0-1.0",
    "public domain": "",  # a claim, not a licence
}

# Instruction-like content aimed at the three things a skill file could do to the
# session that loads it. Each pattern is deliberately narrow: this scan routes to a
# human, so a false positive costs a minute and a false negative costs a customer.
INJECTION_PATTERNS: tuple[tuple[str, str, str], ...] = (
    # -- gate evasion: talking past the instructions that are already loaded
    ("override-instructions", r"ignore\s+(all\s+)?(the\s+)?(previous|prior|above|earlier)\s+instructions",
     "tells the session to discard its instructions"),
    ("override-system", r"(disregard|override|forget)\s+(the\s+)?(system\s+prompt|your\s+(system\s+)?instructions|all\s+rules)",
     "tells the session to discard its system prompt"),
    ("persona-reset", r"\byou\s+are\s+now\s+(a|an|in)\b|\bdeveloper\s+mode\b|\bjailbreak\b",
     "attempts a persona or mode reset"),
    ("conceal", r"(do\s+not|don't|never)\s+(tell|inform|mention\s+to|show)\s+(the\s+)?(user|human|operator)",
     "asks the session to keep something from the person running it"),
    ("silent-action", r"\b(silently|without\s+(asking|confirmation|informing|telling))\s+(run|execute|delete|push|commit|send|install)",
     "asks for an unannounced action"),
    # -- gate evasion: the checks EDIFY exists to keep
    ("skip-verification", r"(skip|bypass|disable|avoid)\s+(the\s+)?(tests?|test\s+suite|review|verification|linting|type\s?check|ci)",
     "asks for a check to be skipped"),
    ("no-verify", r"--no-verify|--no-gpg-sign|--force-with-lease\s+.*--no-verify",
     "asks for a git hook or signature to be bypassed"),
    ("auto-approve", r"(always|automatically)\s+(approve|accept|say\s+yes|confirm)",
     "asks for blanket approval"),
    # -- exfiltration
    ("secret-read", r"(\.env\b|\.aws/credentials|\.ssh/id_[a-z0-9]+|~/\.netrc|id_rsa)",
     "names a credential file"),
    ("secret-egress", r"(curl|wget|Invoke-WebRequest|fetch\()[^\n]{0,120}(\$\{?[A-Z_]{2,}(KEY|TOKEN|SECRET|PASSWORD)|process\.env|os\.environ)",
     "sends environment values to a network endpoint"),
    ("env-egress", r"(process\.env|os\.environ)[^\n]{0,120}(curl|wget|https?://|requests\.(post|get)|fetch\()",
     "reads the environment next to a network call"),
    ("encoded-exec", r"(base64\s+(-d|--decode)|atob\()[^\n]{0,60}\|\s*(sh|bash|zsh|python)",
     "decodes and executes in one step"),
    # -- tool abuse
    ("destructive", r"rm\s+-rf\s+[~/]|git\s+push\s+(--force|-f)\b|git\s+reset\s+--hard\s+origin|DROP\s+(TABLE|DATABASE)",
     "names a destructive command"),
    ("permission-widening", r"chmod\s+777|sudo\s+(su|-i)\b|Set-ExecutionPolicy\s+Bypass",
     "widens permissions"),
)

_COMPILED = tuple((code, re.compile(pat, re.IGNORECASE), why) for code, pat, why in INJECTION_PATTERNS)

# Zero-width and bidirectional control characters. Legitimate prose in a skill file
# has no use for them, and text that renders as one thing and parses as another is
# the whole trick.
_HIDDEN = {
    "​": "zero-width space",
    "‌": "zero-width non-joiner",
    "‍": "zero-width joiner",
    "⁠": "word joiner",
    "﻿": "zero-width no-break space",
    "‪": "bidi override",
    "‫": "bidi override",
    "‭": "bidi override",
    "‮": "bidi override",
    "⁦": "bidi isolate",
    "⁧": "bidi isolate",
    "⁨": "bidi isolate",
}


@dataclass
class Check:
    code: str
    ok: bool
    detail: str
    line: int = 0

    def to_json(self) -> dict:
        return {"code": self.code, "ok": self.ok, "detail": self.detail, "line": self.line}


@dataclass
class Verdict:
    verdict: str  # pass | reject | quarantine
    checks: list[Check] = field(default_factory=list)

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]

    def to_json(self) -> dict:
        return {"verdict": self.verdict, "checks": [c.to_json() for c in self.checks]}


# -- the three checks -------------------------------------------------------


def resolve_license(found: str) -> str:
    """An SPDX id from whatever the repository actually said, or `NONE-FOUND`.

    Unresolvable is the same answer as absent. "BSD" and "public domain" both land
    here, and both are the caller's problem to pin down rather than ours to guess.
    """
    text = (found or "").strip()
    if not text or text.upper() in ("NONE-FOUND", "NONE", "-", "UNKNOWN"):
        return "NONE-FOUND"
    for spdx in ALLOWED_LICENSES:
        if text.lower() == spdx.lower():
            return spdx
    return _LICENSE_ALIASES.get(text.lower(), "") or "NONE-FOUND"


def check_license(found: str) -> Check:
    spdx = resolve_license(found)
    if spdx in ALLOWED_LICENSES:
        return Check("license", True, f"{spdx} is on the allowlist")
    return Check(
        "license",
        False,
        f"`{found or 'NONE-FOUND'}` resolves to {spdx} — the allowlist is {', '.join(ALLOWED_LICENSES)}",
    )


def check_duplicate(name: str, content_sha: str, library_dirs: list[Path], existing_shas: dict[str, str]) -> Check:
    """Against the installed library by name, and against everything ever seen by hash."""
    for directory in library_dirs:
        if not directory.is_dir():
            continue
        if (directory / f"{name}.md").is_file():
            return Check("duplicate", False, f"{name} already exists at {(directory / f'{name}.md').as_posix()}")
    if content_sha in existing_shas:
        return Check("duplicate", False, f"identical bytes already handled as {existing_shas[content_sha]}")
    return Check("duplicate", True, "no entry with this name or these bytes")


def scan_injection(content: str) -> list[Check]:
    """Every hit, with its line. Never the first hit only — the report is the point."""
    hits: list[Check] = []
    lines = content.splitlines()

    for code, pattern, why in _COMPILED:
        for number, line in enumerate(lines, start=1):
            if pattern.search(line):
                hits.append(Check(code, False, f"{why}: {line.strip()[:120]}", number))
                break  # one hit per pattern is enough to route this to a human

    for number, line in enumerate(lines, start=1):
        for ch, label in _HIDDEN.items():
            if ch in line:
                hits.append(Check("hidden-characters", False, f"{label} (U+{ord(ch):04X}) in the text", number))
                break

    for number, line in enumerate(lines, start=1):
        if any(unicodedata.category(ch) == "Cf" and ch not in _HIDDEN for ch in line):
            hits.append(Check("format-characters", False, "unicode format characters in the text", number))
            break

    return hits


def screen(
    *,
    name: str,
    license_found: str,
    content: str,
    content_sha: str,
    library_dirs: list[Path],
    existing_shas: dict[str, str],
) -> Verdict:
    """All three checks, all reported, one verdict.

    Nothing short-circuits. A candidate that fails the licence check is still
    scanned, because "what did this file try to do" is a question worth an answer
    even when the file is going in the bin either way.
    """
    checks = [check_license(license_found), check_duplicate(name, content_sha, library_dirs, existing_shas)]
    injection = scan_injection(content)
    checks.extend(injection)
    if not injection:
        checks.append(Check("injection", True, "no instruction-like content found"))

    if injection:
        return Verdict("quarantine", checks)
    if any(not c.ok for c in checks):
        return Verdict("reject", checks)
    return Verdict("pass", checks)
