"""The questions `edify init new` asks before it installs anything.

Everything else in this CLI is a pure function over files: it reads what is on disk
and writes what follows from it. Detection can find the language, the package manager,
and the test runner. It cannot find out that this is a rewrite of a system that is
already in production, that the person typing is the only one who knows the domain,
or that nothing may touch the payments module without a migration plan. Those are the
facts that decide how an agent should behave here, and there is exactly one place to
get them.

Three rules, which are the same three the library interview follows:

**A question is never load-bearing.** With no terminal — CI, a pipe, a model calling
the binary — nothing is asked, no profile is written, and the install is the one that
happened before this module existed.

**Every answer may be empty.** Enter skips a question; a profile with two answers in
it is worth more than an interrogation somebody abandoned halfway through.

**The answers are the repository's, not EDIFY's.** They are written to
`.edify/profile.md` in plain Markdown for a person to edit, and recorded in the ledger
as `answered` — an origin `edify upgrade` will never overwrite.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .agents import BY_ID
from .ui import Out

PROFILE_MARKER = "<!-- edify:profile -->"


@dataclass
class Question:
    key: str
    prompt: str
    hint: str = ""
    default: str = ""
    # A question whose answer changes what gets installed, rather than what gets
    # written down. Asked first, and asked even when the rest is skipped.
    decides_install: bool = False


@dataclass
class Profile:
    """What the person said. Every field optional; the file shows what was answered."""

    answers: dict[str, str] = field(default_factory=dict)
    asked: bool = False

    def get(self, key: str) -> str:
        return (self.answers.get(key) or "").strip()

    @property
    def filled(self) -> dict[str, str]:
        return {k: v.strip() for k, v in self.answers.items() if (v or "").strip()}

    @property
    def described(self) -> dict[str, str]:
        """The answers that describe the person and the work, as against the two that
        decide what gets installed. Only these make a profile worth writing: a file
        whose whole content is "runtimes: all" tells the next session nothing it could
        not have seen by looking at the folder."""
        return {k: v for k, v in self.filled.items() if k in DESCRIBING}

    def as_dict(self) -> dict[str, str]:
        return dict(self.filled)


# -- the questions -----------------------------------------------------------
# Eight, and they stop. The list is short on purpose: a setup command that interviews
# somebody for five minutes is a setup command they run once and then work around.
# The first two decide what gets installed, which is why they are asked first and why
# they are not part of what makes a profile worth writing.

QUESTIONS: tuple[Question, ...] = (
    Question(
        key="agents",
        prompt="  which agents do you use here?",
        hint="all · none · ids like claude,codex,cursor — this decides what gets installed",
        default="all",
        decides_install=True,
    ),
    Question(
        key="stack",
        prompt="  anything in the stack that detection would miss?",
        hint="tech ids like `postgres redis`, or enter to take what was detected",
        default="",
        decides_install=True,
    ),
    Question(
        key="name",
        prompt="  what should an agent call you?",
    ),
    Question(
        key="role",
        prompt="  what is your role on this?",
        hint="founder · staff engineer · data scientist · learning to code — anything",
    ),
    Question(
        key="building",
        prompt="  what is being built here, in one line?",
        hint="this is the line every session starts from",
    ),
    Question(
        key="done",
        prompt="  what does done look like for the next few weeks?",
    ),
    Question(
        key="explain",
        prompt="  how much should an agent explain as it works?",
        hint="brief · normal · teaching",
        default="normal",
    ),
    Question(
        key="constraints",
        prompt="  anything an agent must never do in this repository?",
        hint="e.g. never touch migrations · never commit to main · ask before adding a dependency",
    ),
)


DESCRIBING = tuple(q.key for q in QUESTIONS if not q.decides_install)


def default_name() -> str:
    """A name to offer, from the machine rather than from a guess."""
    try:
        result = subprocess.run(
            ["git", "config", "--get", "user.name"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return os.environ.get("USER") or os.environ.get("USERNAME") or ""


def ask(out: Out, *, defaults: dict[str, str] | None = None) -> Profile:
    """Put the questions. Returns an unasked profile when there is nobody to ask."""
    profile = Profile()
    if not out.interactive:
        return profile

    supplied = dict(defaults or {})
    out.prompt_line("")
    out.prompt_line(out.c("  a few questions first", "bold"))
    out.prompt_line(
        out.c(
            "  Detection reads your files; these are the things files do not say."
            "  Enter skips any of them.",
            "dim",
        )
    )
    out.prompt_line("")

    for question in QUESTIONS:
        default = supplied.get(question.key, question.default)
        if question.hint:
            out.prompt_line(out.c(f"      {question.hint}", "dim"))
        profile.answers[question.key] = out.ask(question.prompt, default=default)

    profile.asked = True
    out.prompt_line("")
    return profile


# -- what the answers change -------------------------------------------------


def agents_spec(profile: Profile, fallback: str) -> str:
    """The `--agents` value the answer implies, or the flag's own value.

    A flag the person typed always beats an answer they gave to a default-filled
    question, so an explicit `--agents claude` is not overridden by pressing enter
    through the interview.
    """
    answer = profile.get("agents")
    if not answer:
        return fallback
    normalised = answer.replace(",", " ").split()
    if len(normalised) == 1 and normalised[0].lower() in ("all", "none", "*"):
        return normalised[0].lower()
    known = [token.lower() for token in normalised if token.lower() in BY_ID]
    return " ".join(known) if known else fallback


def extra_tech(profile: Profile) -> list[str]:
    """Tech ids the person named that detection did not find."""
    answer = profile.get("stack")
    return [token.strip().lower() for token in answer.replace(",", " ").split() if token.strip()]


# -- the file ----------------------------------------------------------------


def render(profile: Profile) -> str:
    """`.edify/profile.md` — the answers, as prose an agent reads in one pass.

    Written as headings and short lines rather than a table, because the reader is a
    model loading it as context at the start of a session and a person editing it six
    weeks later when the answers have changed. Both of them do better with sentences.
    """
    name = profile.get("name")
    role = profile.get("role")
    who = " · ".join([p for p in (name, role) if p]) or "not stated"

    lines = [
        PROFILE_MARKER,
        "# Who this repository is being built for",
        "",
        f"**Working here:** {who}",
        "",
    ]

    sections = (
        ("What is being built", "building"),
        ("What done looks like", "done"),
        ("Constraints — these are not suggestions", "constraints"),
    )
    for heading, key in sections:
        value = profile.get(key)
        if value:
            lines += [f"## {heading}", "", value, ""]

    explain = profile.get("explain")
    if explain:
        lines += [
            "## How to talk to this person",
            "",
            f"Explanation: **{explain}**. "
            + _explain_note(explain),
            "",
        ]

    agents = profile.get("agents")
    if agents:
        lines += [f"**Agent runtimes installed here:** {agents}", ""]

    lines += [
        "---",
        "",
        "These answers came from `edify init new`. This file is yours: edit it whenever the",
        "answers change. EDIFY records it in the ledger and never overwrites it on upgrade.",
        "",
    ]
    return "\n".join(lines)


def _explain_note(explain: str) -> str:
    key = explain.strip().lower()
    if key.startswith("brief"):
        return "Give the answer and the diff; skip the walkthrough unless it is asked for."
    if key.startswith("teach"):
        return "Say why, not only what — name the trade-off you took and the one you left."
    return "Say what changed and why it was the right call, in a few lines."


def block_lines(profile: Profile) -> list[str]:
    """The two or three lines the instruction files carry.

    The profile itself stays in one file. What goes into `CLAUDE.md`, `AGENTS.md`, and
    the rest is a pointer at it plus the one line that is worth spending context on
    unconditionally — who this is and what they are building.
    """
    if not profile.described:
        return []
    name = profile.get("name")
    role = profile.get("role")
    building = profile.get("building")

    who = " · ".join([p for p in (name, role) if p])
    first = who or ""
    if building:
        first = f"{first} — building {building}" if first else f"Building {building}"
    lines = ["## Who you are working with", ""]
    if first:
        lines.append(first.rstrip(".") + ".")
    lines.append("Read `.edify/profile.md` before the first task — constraints and tone are in it.")
    return lines


def write(path: Path, profile: Profile) -> bool:
    """Write the profile. Returns whether anything was written."""
    if not profile.described:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(profile), encoding="utf-8")
    return True


def load(path: Path) -> Profile:
    """Read back what a previous run wrote, so a re-run can offer it as the default.

    Deliberately forgiving: this file is meant to be hand-edited, and a person who
    reformats it should not be re-interviewed from scratch. Only the fields that are
    still recognisable come back; the rest are simply not offered as defaults.
    """
    profile = Profile()
    if not path.is_file():
        return profile
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return profile

    heading_keys = {
        "what is being built": "building",
        "what done looks like": "done",
        "constraints — these are not suggestions": "constraints",
        "constraints": "constraints",
    }
    current = ""
    collected: dict[str, list[str]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            current = heading_keys.get(stripped[3:].strip().lower(), "")
            continue
        if stripped == "---":
            # The rule above the footer. Everything below it is EDIFY's own note
            # about the file, and collecting it would append the note to whichever
            # section happened to be last.
            current = ""
            continue
        if stripped.startswith("Explanation:"):
            profile.answers["explain"] = stripped.split("**")[1] if "**" in stripped else ""
            continue
        if stripped.startswith("**Working here:**"):
            who = stripped.split("**Working here:**", 1)[1].strip()
            if who and who != "not stated":
                name, _, role = who.partition("·")
                profile.answers["name"] = name.strip()
                if role.strip():
                    profile.answers["role"] = role.strip()
            continue
        if stripped.startswith("**Agent runtimes installed here:**"):
            profile.answers["agents"] = stripped.split(":**", 1)[1].strip()
            continue
        if current and stripped and not stripped.startswith(("#", "<!--", "**")):
            collected.setdefault(current, []).append(stripped)

    for key, value in collected.items():
        profile.answers[key] = " ".join(value).strip()
    profile.answers = {k: v for k, v in profile.answers.items() if v}
    return profile
