"""Output. One place, so `--json` and `--no-color` are honoured everywhere.

Every command writes through here. Machine output goes to stdout as JSON when
`--json` is set; human notes and warnings go to stderr so a pipe stays clean.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ANSI = {
    "reset": "\033[0m",
    "dim": "\033[2m",
    "bold": "\033[1m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
}


def _emit(text: str, stream: Any = None) -> None:
    """One `print`, for every channel, that a cp1252 console cannot kill.

    Windows consoles still default to a code page that has no `→` and no `·`, and
    a command that did its work and then died writing the sentence about it is the
    worst of both outcomes — the ledger is saved, the exit code says failure. So an
    unencodable character degrades to a replacement rather than a traceback.
    """
    stream = stream if stream is not None else sys.stdout
    try:
        print(text, file=stream)
    except UnicodeEncodeError:
        encoding = getattr(stream, "encoding", None) or "ascii"
        print(text.encode(encoding, "replace").decode(encoding, "replace"), file=stream)


def _has_terminal() -> bool:
    """A person at both ends of this invocation. The one place that is decided."""
    try:
        return bool(sys.stdin.isatty()) and bool(sys.stderr.isatty())
    except (AttributeError, ValueError):  # a replaced stdin, a closed stream
        return False


class Out:
    """The output channel for one command invocation."""

    def __init__(
        self,
        json_mode: bool = False,
        color: bool | None = None,
        quiet: bool = False,
        anim: bool = True,
    ):
        self.json_mode = json_mode
        self.quiet = quiet
        # `--no-anim`. Kept as its own attribute rather than folded into `animated`
        # so `anim.banner` — which survives a pipe and a CI log, and so cannot ask
        # `animated` — has something to read.
        self.no_anim = not anim
        if color is None:
            color = (
                sys.stdout.isatty()
                and os.environ.get("NO_COLOR") is None
                and os.environ.get("TERM") != "dumb"
            )
        self.color = bool(color) and not json_mode

    # -- styling ---------------------------------------------------------

    def c(self, text: str, style: str) -> str:
        if not self.color:
            return text
        return f"{_ANSI.get(style, '')}{text}{_ANSI['reset']}"

    # -- channels --------------------------------------------------------

    def line(self, text: str = "") -> None:
        """A line of the command's actual answer. Suppressed in JSON mode."""
        if self.json_mode or self.quiet:
            return
        _emit(text)

    def note(self, text: str) -> None:
        """Context for a human. Never part of the answer, so it goes to stderr."""
        if self.quiet:
            return
        _emit(self.c(text, "dim"), sys.stderr)

    def warn(self, text: str) -> None:
        _emit(f"{self.c('warning', 'yellow')} {text}", sys.stderr)

    def error(self, text: str, hint: str | None = None) -> None:
        _emit(f"{self.c('error', 'red')} {text}", sys.stderr)
        if hint:
            _emit(f"        {self.c(hint, 'dim')}", sys.stderr)

    def ok(self, text: str) -> None:
        if self.quiet:
            return
        _emit(f"{self.c('ok', 'green')} {text}", sys.stderr)

    def data(self, payload: Any) -> None:
        """The machine-readable form of the answer. Only emitted in JSON mode."""
        if not self.json_mode:
            return
        _emit(json.dumps(payload, indent=2, sort_keys=True, default=str))

    # -- asking ----------------------------------------------------------

    @property
    def interactive(self) -> bool:
        """Whether this invocation is allowed to ask a person a question.

        A prompt that appears inside a pipeline, a CI job, or a model's tool call is
        a hang rather than a question. So it takes a terminal at both ends, human
        output, and nothing in the environment saying otherwise. Every caller has a
        defined answer for when this is false — a question is never load-bearing.
        """
        if self.json_mode or self.quiet:
            return False
        if os.environ.get("EDIFY_ASSUME_YES") or os.environ.get("EDIFY_NO_PROMPT") or os.environ.get("CI"):
            return False
        return _has_terminal()

    @property
    def animated(self) -> bool:
        """Whether this invocation is allowed to paint over its own output.

        The one place tty, `--json`, `--quiet`, `--no-anim`, `EDIFY_NO_ANIM`, `CI`
        and `TERM=dumb` are decided, so no call site invents its own rule and the
        two disagree. Sitting beside `interactive` on purpose: both answer "is
        there a person watching this happen, right now?".

        stderr specifically, because that is where the animation paints. A piped
        stdout with a terminal on stderr still animates, which is what somebody
        running `edify graph build > out.txt` wants to see.
        """
        if self.json_mode or self.quiet or self.no_anim:
            return False
        if os.environ.get("EDIFY_NO_ANIM") or os.environ.get("CI"):
            return False
        if os.environ.get("TERM") == "dumb":
            return False
        try:
            return bool(sys.stderr.isatty())
        except (AttributeError, ValueError):  # a replaced or closed stream
            return False

    def prompt_line(self, text: str = "") -> None:
        """Part of a question — a menu row, a heading. Never part of the answer."""
        if self.json_mode or self.quiet:
            return
        _emit(text, sys.stderr)

    def ask(self, question: str, default: str = "") -> str:
        """One line of input, on stderr so a pipe on stdout stays clean."""
        if not self.interactive:
            return default
        suffix = f" [{default}]" if default else ""
        print(f"{self.c(question, 'bold')}{suffix} ", end="", file=sys.stderr, flush=True)
        try:
            answer = input().strip()
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
            return default
        return answer or default

    # -- tables ----------------------------------------------------------

    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        """A plain aligned table. No box drawing — it has to survive a pipe."""
        if self.json_mode or self.quiet:
            return
        if not rows:
            return
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(widths):
                    widths[i] = max(widths[i], len(str(cell)))
        head = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
        _emit(self.c(head, "bold"))
        _emit(self.c("  ".join("-" * w for w in widths), "dim"))
        for row in rows:
            _emit("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)))
