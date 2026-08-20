#!/usr/bin/env python3
"""Render real terminal output into an SVG that looks like a terminal.

The README shows the product working. That evidence is only worth anything if it
is real, so these images are generated from captured output of the actual binary
rather than drawn by hand — and this script is committed so anyone can regenerate
them and check.

    python tools/render_terminal.py assets/specs/graph-where.txt assets/graph-where.svg

The input file is a transcript: lines beginning with `$ ` are prompts, everything
else is output. A line of `---` splits the transcript into visual blocks.

No dependencies, like everything else here.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

# The brand, as tokens. Dark only: a terminal is dark, and a light-mode terminal
# screenshot reads as a mockup even when it is not.
BG = "#0B0F17"          # window body
CHROME = "#111825"      # title bar
RULE = "#1E2733"        # hairlines
TEXT = "#C9D4E0"        # ordinary output
DIM = "#5E6B7E"         # chrome text, comments
ACCENT = "#4C8DFF"      # the prompt marker, command names
GREEN = "#3FB950"       # ok
AMBER = "#D29922"       # degraded
RED = "#F85149"         # error
WHITE = "#EEF3F8"       # the command the user typed

FONT = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'DejaVu Sans Mono', monospace")

CH = 8.42               # character advance at 14px in this stack
LH = 22                 # line height
PAD_X = 22
PAD_TOP = 52            # below the title bar
PAD_BOT = 20
BAR = 34                # title bar height


def classify(line: str) -> str:
    """Which token colours this line. Order matters: first match wins."""
    stripped = line.strip()
    if line.startswith("$ "):
        return "prompt"
    if stripped.startswith("#"):
        return "comment"
    if stripped.startswith(("ok  ", "ok\t")) or stripped.startswith("ok "):
        return "ok"
    if stripped.startswith("degraded") or stripped.startswith("warn"):
        return "warn"
    if stripped.startswith(("error", "missing", "modified", "amber")):
        return "error"
    if stripped.startswith(("→", "->")):
        return "accent"
    return "text"


COLOURS = {
    "prompt": WHITE, "comment": DIM, "ok": GREEN, "warn": AMBER,
    "error": RED, "accent": ACCENT, "text": TEXT,
}


def render(lines: list[str], title: str) -> str:
    width = max([len(l) for l in lines] + [len(title) + 8, 46])
    w = int(width * CH) + PAD_X * 2
    h = PAD_TOP + len(lines) * LH + PAD_BOT

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="Terminal: {html.escape(title)}">',
        f'<rect width="{w}" height="{h}" rx="10" fill="{BG}"/>',
        f'<path d="M10 0 h{w - 20} a10 10 0 0 1 10 10 v{BAR - 10} h-{w} '
        f'v-{BAR - 10} a10 10 0 0 1 10 -10 z" fill="{CHROME}"/>',
        f'<line x1="0" y1="{BAR}" x2="{w}" y2="{BAR}" stroke="{RULE}" stroke-width="1"/>',
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" '
        f'fill="none" stroke="{RULE}" stroke-width="1"/>',
    ]

    for i, dot in enumerate(("#F85149", "#D29922", "#3FB950")):
        out.append(f'<circle cx="{20 + i * 17}" cy="{BAR / 2}" r="5" fill="{dot}" opacity="0.85"/>')

    out.append(
        f'<text x="{w / 2}" y="{BAR / 2 + 4}" font-family="{FONT}" font-size="11.5" '
        f'fill="{DIM}" text-anchor="middle" letter-spacing="0.4">{html.escape(title)}</text>'
    )

    y = PAD_TOP + 4
    for line in lines:
        kind = classify(line)
        if kind == "prompt":
            out.append(
                f'<text x="{PAD_X}" y="{y}" font-family="{FONT}" font-size="14" '
                f'xml:space="preserve"><tspan fill="{ACCENT}">$ </tspan>'
                f'<tspan fill="{WHITE}">{html.escape(line[2:])}</tspan></text>'
            )
        else:
            out.append(
                f'<text x="{PAD_X}" y="{y}" font-family="{FONT}" font-size="14" '
                f'fill="{COLOURS[kind]}" xml:space="preserve">{html.escape(line)}</text>'
            )
        y += LH

    out.append("</svg>")
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    raw = src.read_text(encoding="utf-8").rstrip("\n").split("\n")

    title = raw[0][2:].strip() if raw and raw[0].startswith("#!") else src.stem
    body = raw[1:] if raw and raw[0].startswith("#!") else raw

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(render(body, title), encoding="utf-8")
    print(f"{dst}  ({len(body)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
