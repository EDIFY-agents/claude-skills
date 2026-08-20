"""Asking how this is going, without becoming a tool that phones home.

`docs/pricing.md` §4 commits to no telemetry — "not anonymous, not
aggregate, not opt-out" — and the reason it gives is the buyer: frequently the
person who has to explain to somebody external what touched the source tree. That
commitment is not weakened here, so this module is built to the opposite shape from
the usual one:

* Nothing is ever transmitted. `edify feedback` writes a file on this machine and
  prints where it is. Sending it is a thing the person does, with a command they can
  read, to an address they can see.
* Nothing is collected in the background. There is no event, no counter of what you
  ran, no repository name, no path, no stack. The file contains the answers typed
  into it and three lines about the install, and you can read the whole thing before
  deciding anybody else should.
* The invitation appears at most once per released version, only on a real terminal,
  and `edify feedback off` ends it permanently.

The one piece of state is a small file in the user config directory — never inside a
repository — holding a run counter and which version last asked. It is written only
on interactive runs, so a CI job, a pipe, or a model calling the binary leaves no
trace at all.
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import __version__
from .paths import user_config_dir
from .tsv import read_kv, write_kv
from .ui import Out

# The invitation waits until somebody has actually used the tool. One run is not an
# opinion, and asking at that point is a pop-up rather than a question.
INVITE_AFTER_RUNS = 3

ISSUES_URL = "https://github.com/edify-dev/edify/issues/new"
REPO = "edify-dev/edify"

QUESTIONS = (
    ("doing", "  What were you using EDIFY for?"),
    ("worked", "  What worked?"),
    ("friction", "  What got in the way?"),
    ("change", "  What would you change first?"),
)


def state_path() -> Path:
    return user_config_dir() / "state"


def _load() -> dict[str, str]:
    return read_kv(state_path())


def _save(values: dict[str, str]) -> None:
    try:
        write_kv(state_path(), values)
    except OSError:
        pass  # a read-only home is not a reason for a command to fail


def disabled() -> bool:
    if os.environ.get("EDIFY_NO_FEEDBACK"):
        return True
    return _load().get("feedback", "on") == "off"


def set_enabled(on: bool) -> None:
    values = _load()
    values["feedback"] = "on" if on else "off"
    _save(values)


# -- the invitation ----------------------------------------------------------


def maybe_invite(out: Out) -> None:
    """One dim line on stderr, at most once per version. Never blocks, never asks.

    Called on every CLI entry, and on all but a handful of them it returns without
    touching the disk.
    """
    if not out.interactive or disabled():
        return

    values = _load()
    runs = _int(values.get("runs", "0")) + 1
    values["runs"] = str(runs)
    values["version"] = __version__
    _save(values)

    if values.get("invited") == __version__ or runs < INVITE_AFTER_RUNS:
        return
    values["invited"] = __version__
    _save(values)

    out.prompt_line("")
    out.prompt_line(
        out.c("  How is EDIFY working on this codebase?", "bold")
        + out.c("  `edify feedback` — four questions.", "dim")
    )
    out.prompt_line(
        out.c(
            "  It writes a file on this machine and sends nothing."
            "  `edify feedback off` and this line never appears again.",
            "dim",
        )
    )
    out.prompt_line("")


def _int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


# -- writing one entry -------------------------------------------------------


@dataclass
class Entry:
    answers: dict[str, str]
    contact: str = ""

    def render(self) -> str:
        lines = [
            "# EDIFY feedback",
            "",
            f"- edify: {__version__}",
            f"- python: {platform.python_version()} on {platform.system()} {platform.machine()}",
            f"- written: {date.today().isoformat()}",
        ]
        if self.contact:
            lines.append(f"- contact: {self.contact}")
        lines.append("")
        for key, question in QUESTIONS:
            answer = self.answers.get(key, "").strip()
            if not answer:
                continue
            lines.append(f"## {question.strip()}")
            lines.append("")
            lines.append(answer)
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def directory() -> Path:
    return user_config_dir() / "feedback"


def existing() -> list[Path]:
    folder = directory()
    if not folder.is_dir():
        return []
    return sorted(folder.glob("*.md"))


def write(entry: Entry) -> Path:
    folder = directory()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{len(existing()) + 1:04d}.md"
    path.write_text(entry.render(), encoding="utf-8")

    values = _load()
    values["given"] = str(_int(values.get("given", "0")) + 1)
    _save(values)
    return path


def how_to_send(path: Path) -> list[str]:
    """The two ways to send it, both of which the person performs themselves."""
    return [
        f"gh issue create --repo {REPO} --title 'feedback' --body-file \"{path}\"",
        f"or paste it into {ISSUES_URL}",
    ]


def interview(out: Out) -> Entry | None:
    """Four questions. Returns None if there is nobody to ask."""
    if not out.interactive:
        return None

    out.prompt_line("")
    out.prompt_line(out.c("  Four questions, all skippable with enter.", "bold"))
    out.prompt_line(
        out.c(
            f"  The answers go to a file under {directory()} and travel no further"
            " until you send them.",
            "dim",
        )
    )
    out.prompt_line("")

    answers: dict[str, str] = {}
    for key, question in QUESTIONS:
        answers[key] = out.ask(question)
    contact = out.ask("  Your email, if you want a reply (enter to skip)")
    out.prompt_line("")
    return Entry(answers=answers, contact=contact)
