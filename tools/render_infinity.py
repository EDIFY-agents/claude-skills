#!/usr/bin/env python3
"""Render the CLI's infinity into an SVG the README can play.

`edify init` paints a lemniscate while it works (`src/edify/anim.py`). A README
cannot run a terminal, but it can show the same curve moving, and the shape here
is not redrawn by hand: the static lattice of dots is *exactly* the grid cells
`anim._cell` lands on, imported from the module itself. If the curve in the CLI
changes, this image changes with it.

    python tools/render_infinity.py assets/infinity.svg

The head and its trail glide along the continuous curve with `animateMotion`
rather than stepping through `anim`'s 48 precomputed frames. Frame-stepping is
right in a terminal, where a character cell is the smallest thing that exists;
in vector output it only throws away resolution the medium already has, and the
file would carry 48 copies of the grid to do it.

`prefers-reduced-motion: reduce` gets a still head parked at the start of the
curve, the same courtesy `pipeline.svg` already extends. Motion nobody asked for
is not decoration, and this file is the CLI's own rule about decoration applied
to a README.

No dependencies, like everything else here.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from edify import anim  # noqa: E402

# The brand, as tokens — the same ones `tools/render_terminal.py` uses, so the
# header and the terminal images below it read as one set. Dark only: this is a
# picture of a terminal, and it paints its own background rather than borrowing
# whichever theme GitHub is in.
BG = "#0B0F17"          # card
RULE = "#1E2733"        # hairline border
LATTICE = "#2E3E5C"     # the curve at rest — `·` in the terminal
TRAIL = "#4C8DFF"       # the warm trail — `○`
HEAD = "#EEF3F8"        # the head — `●`
DIM = "#5E6B7E"         # caption

FONT = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'DejaVu Sans Mono', monospace")

CELL_W = 16             # one terminal column
CELL_H = 22             # one terminal row, at this width the 2:1 aspect the CLI corrects for
PAD_X = 40
PAD_TOP = 34
PAD_BOT = 46            # room for the caption

#: One loop, in seconds: the CLI's own frame count at the CLI's own frame rate.
DURATION = anim.FRAMES / anim.FPS
#: Dots behind the head, and the fraction of a loop the last one lags by. The
#: terminal's `TRAIL` is 34 of 480 samples; this is the same 7% of the curve,
#: spent on fewer, fading dots because a vector dot does not need a neighbour to
#: look continuous.
TRAIL_DOTS = 16
TRAIL_SPAN = anim.TRAIL / anim.SAMPLES

W = PAD_X * 2 + (anim.WIDTH - 1) * CELL_W
H = PAD_TOP + PAD_BOT + (anim.HEIGHT - 1) * CELL_H

CAPTION = "the infinite loop, made finite"


def cell_xy(row: int, col: int) -> tuple[float, float]:
    """A grid cell as a point on the card."""
    return PAD_X + col * CELL_W, PAD_TOP + row * CELL_H


def lattice() -> list[tuple[float, float]]:
    """Every cell the terminal animation lights up, in the terminal's own order."""
    seen: set[tuple[int, int]] = set()
    points: list[tuple[float, float]] = []
    for i in range(anim.SAMPLES):
        cell = anim._cell(2.0 * math.pi * i / anim.SAMPLES)
        if cell not in seen:
            seen.add(cell)
            points.append(cell_xy(*cell))
    return points


def curve_path(samples: int = 220) -> str:
    """The continuous curve, in card coordinates, as a closed path.

    Sampled from `anim._point` — the same Gerono, before the grid rounds it — so
    the head travels the ideal curve while the lattice shows where a character
    cell can actually put it.
    """
    parts: list[str] = []
    for i in range(samples):
        x, y = anim._point(2.0 * math.pi * i / samples)
        px = PAD_X + (x + 1.0) / 2.0 * (anim.WIDTH - 1) * CELL_W
        py = PAD_TOP + (0.5 - y) * (anim.HEIGHT - 1) * CELL_H
        parts.append(f"{'M' if i == 0 else 'L'}{px:.1f} {py:.1f}")
    parts.append("Z")
    return "".join(parts)


def moving_dot(index: int, path_id: str) -> str:
    """One dot on the curve, lagging the head by `index` steps.

    A negative `begin` starts the animation partway through, which is how each
    dot sits behind the one in front of it without any per-dot path arithmetic.
    """
    lag = 0.0 if TRAIL_DOTS < 2 else index / (TRAIL_DOTS - 1)
    fade = (1.0 - lag) ** 1.7
    if index == 0:
        dot = f'<circle r="4.2" fill="{HEAD}" filter="url(#glow)"/>'
    else:
        dot = (f'<circle r="{2.9 - 1.5 * lag:.2f}" fill="{TRAIL}" '
               f'opacity="{0.06 + 0.82 * fade:.3f}"/>')
    begin = -lag * TRAIL_SPAN * DURATION
    return (f'<g>{dot}'
            f'<animateMotion dur="{DURATION:.2f}s" repeatCount="indefinite" '
            f'begin="{begin:.3f}s" rotate="auto">'
            # Both spellings: SVG 2 dropped the `xlink:` prefix, and some
            # renderers still only look for the old one.
            f'<mpath href="#{path_id}" xlink:href="#{path_id}"/>'
            f'</animateMotion></g>')


def still_dots() -> str:
    """The reduced-motion picture: the head parked where the loop begins.

    Drawn from the same curve at `t = 0` and just behind it, so a reader who has
    asked their machine to stop moving still sees what the animation is *of*,
    rather than a bare lattice with the point of the image removed.
    """
    parts = ['<g class="still">']
    for index in range(TRAIL_DOTS - 1, -1, -1):
        lag = 0.0 if TRAIL_DOTS < 2 else index / (TRAIL_DOTS - 1)
        t = -lag * TRAIL_SPAN * 2.0 * math.pi
        x, y = anim._point(t)
        px = PAD_X + (x + 1.0) / 2.0 * (anim.WIDTH - 1) * CELL_W
        py = PAD_TOP + (0.5 - y) * (anim.HEIGHT - 1) * CELL_H
        if index == 0:
            parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.2" '
                         f'fill="{HEAD}" filter="url(#glow)"/>')
        else:
            fade = (1.0 - lag) ** 1.7
            parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" '
                         f'r="{2.9 - 1.5 * lag:.2f}" fill="{TRAIL}" '
                         f'opacity="{0.06 + 0.82 * fade:.3f}"/>')
    parts.append('</g>')
    return "".join(parts)


#: Which of the two groups the reader gets. Default is the animation; a machine
#: that asks for less motion gets the still one instead.
STYLE = ('.still{display:none}'
         '@media (prefers-reduced-motion: reduce){'
         '.motion{display:none}.still{display:inline}}')


def render() -> str:
    path_id = "curve"
    label = ("EDIFY: an infinity traced dot by dot, the animation the CLI paints "
             "while it works")
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="{label}">',
        f'<title>{label}</title>',
        f'<style>{STYLE}</style>',
        '<defs>',
        f'<path id="{path_id}" d="{curve_path()}"/>',
        # Soft halo on the head only. The trail is dim enough to read as afterglow
        # without one, and a blur per dot is a blur the renderer runs 16 times.
        '<filter id="glow" x="-200%" y="-200%" width="500%" height="500%">',
        '<feGaussianBlur stdDeviation="3.4" result="b"/>',
        '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/>'
        '<feMergeNode in="SourceGraphic"/></feMerge>',
        '</filter>',
        '</defs>',
        f'<rect width="{W}" height="{H}" rx="10" fill="{BG}"/>',
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" '
        f'fill="none" stroke="{RULE}" stroke-width="1"/>',
    ]

    out.append(f'<g fill="{LATTICE}">')
    for x, y in lattice():
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="1.9"/>')
    out.append('</g>')

    # Painted tail first, so the head is always the thing on top — the same rule
    # `anim._build` follows when it fills a character cell.
    out.append('<g class="motion">')
    for index in range(TRAIL_DOTS - 1, -1, -1):
        out.append(moving_dot(index, path_id))
    out.append('</g>')
    out.append(still_dots())

    out.append(
        f'<text x="{W / 2:.0f}" y="{H - 18}" font-family="{FONT}" font-size="11.5" '
        f'fill="{DIM}" text-anchor="middle" letter-spacing="1.6">{CAPTION}</text>')
    out.append('</svg>')
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        print("usage: python tools/render_infinity.py <out.svg>", file=sys.stderr)
        return 2
    destination = Path(argv[1])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render(), encoding="utf-8")
    print(f"wrote {destination} ({destination.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
