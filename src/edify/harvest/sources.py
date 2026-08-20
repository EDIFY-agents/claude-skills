"""`edify/harvest/sources.md` — the source table, and which row a run draws from.

Two jobs, both mechanical.

**The parse.** A markdown table because a person reviews additions to it. Read by
column *name* rather than position, so the table can gain a column — it gained
`fetch` — without every older table becoming unparseable.

**The choice.** A run has a budget of a few candidates and a list of places to draw
them from, and picking the place was the step nobody specified: the skill said "read
sources.md" and left the selection to whatever the model felt like that morning.
That is a lookup, so it is done here and never by a prompt — same law as the licence
allowlist. `rank` scores every row from the ledger's own yield history and returns
them ordered, with the arithmetic attached so the answer can be argued with.

What the score is made of, and why each part is in it:

    eligible          a posture that resolves to an allowlisted SPDX id can be
                      staged; an index can only be read for links; anything else
                      cannot be harvested at all and ranks last with the reason
    yield             admitted / (admitted + rejected), from the human door and
                      never from the screen — a source with a high screen pass rate
                      and a low admission rate is producing plausible files, which
                      is the failure mode worth ranking down
    untried           an unknown yield beats a known-bad one and loses to a
                      known-good one, which is the whole of what "unknown" means
    archived          an upstream that is frozen has a fixed amount left in it and
                      nothing new arriving, so it ranks below every live source with
                      the same posture — this is what the first version got wrong,
                      because with no such term four MIT rows tied on score and the
                      alphabetical tie-break handed the run an archived repository
    exhaustion        every candidate already in the ledger from this source is one
                      fewer left in it; a source drawn from eight times is tapped
                      out relative to a fresh one
    staleness         a month since the last run brings a good source back around

Ties break on the source name, so the answer is the same on Tuesday.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import screen as screener

# What a row's `kind` can say about how it is drawn from. Anything else is treated
# as `repository` — the table is authored by a person and a typo should not silently
# change what a run does with the row.
KINDS = ("repository", "index", "engagement")

# Columns may be missing from an older table (`fetch`, `status`), and the yield
# columns are advisory — the ledger is the thing that actually knows.
_HEADERS = {
    "source": ("source",),
    "kind": ("kind",),
    "fetch": ("fetch", "where", "path"),
    "posture": ("licence posture", "license posture", "licence", "license", "posture"),
    "status": ("status", "state"),
}

# A frozen upstream. Absent from the table means live, because most rows are.
ARCHIVED = ("archived", "frozen", "deprecated", "unmaintained")


@dataclass
class Source:
    name: str
    kind: str = "repository"
    fetch: str = ""
    posture: str = ""
    status: str = "active"

    @property
    def archived(self) -> bool:
        return self.status.strip().lower() in ARCHIVED

    @property
    def spdx(self) -> str:
        """The posture resolved to an SPDX id, or `NONE-FOUND`.

        A posture is what to *expect*, never what is recorded: `stage --license`
        carries the licence as actually found at fetch time and the screen decides
        on that. This only sets how promising the row is.
        """
        return screener.resolve_license(_first_licence(self.posture))

    @property
    def eligible(self) -> bool:
        return self.spdx in screener.ALLOWED_LICENSES

    def to_json(self) -> dict:
        return {
            "source": self.name,
            "kind": self.kind,
            "fetch": self.fetch,
            "licence_posture": self.posture,
            "spdx": self.spdx,
            "status": "archived" if self.archived else "active",
        }


@dataclass
class Ranked:
    source: Source
    score: int
    admitted: int = 0
    rejected: int = 0
    seen: int = 0
    last_run: str = "never"
    reasons: list[str] = field(default_factory=list)

    @property
    def why(self) -> str:
        return " · ".join(self.reasons)

    def to_json(self) -> dict:
        return {
            **self.source.to_json(),
            "score": self.score,
            "admitted": self.admitted,
            "rejected": self.rejected,
            "seen": self.seen,
            "last_run": self.last_run,
            "why": self.why,
        }


# -- the parse --------------------------------------------------------------


def read(path: Path) -> list[Source]:
    """Every real row of the source table, in the order a person wrote them."""
    if not path.is_file():
        return []
    rows = _tables(path.read_text(encoding="utf-8"))
    out: list[Source] = []
    for columns in rows:
        name = columns.get("source", "")
        if not name or _placeholder(name):
            continue
        kind = (columns.get("kind") or "repository").strip().lower()
        out.append(
            Source(
                name=name,
                kind=kind if kind in KINDS else "repository",
                fetch=columns.get("fetch", ""),
                posture=columns.get("posture", ""),
                status=columns.get("status", "") or "active",
            )
        )
    return out


def _tables(text: str) -> list[dict[str, str]]:
    """Rows as {column name: cell}, for every pipe table in the file.

    The header row names the columns and the separator row is what proves it was a
    header. A table with no recognised `source` column is not the source table —
    `sources.md` also carries prose tables — so it contributes nothing.
    """
    rows: list[dict[str, str]] = []
    header: dict[int, str] | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set("-: ") and c for c in cells):
            continue  # the separator row
        if header is None:
            header = _map_columns(cells)
            continue
        if "source" not in header.values():
            continue
        rows.append({header[i]: cell for i, cell in enumerate(cells) if i in header})
    return rows


def _map_columns(cells: list[str]) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for index, cell in enumerate(cells):
        label = cell.strip().lower().strip("*`")
        for key, spellings in _HEADERS.items():
            if label in spellings and key not in mapping.values():
                mapping[index] = key
                break
    return mapping


def _placeholder(name: str) -> bool:
    """The `| — | — | — |` row a table carries when it is honestly empty."""
    return set(name) <= set("—-– ") or name.lower() in ("source", "")


def _first_licence(posture: str) -> str:
    """The SPDX-looking token out of a prose posture cell.

    A posture is written for a person — "Apache-2.0 per skill, some source-available"
    — so the resolver gets the first token that could be an id rather than the
    sentence. Everything it cannot pin down is `NONE-FOUND`, which is the same
    answer as absent and ranks the row out.
    """
    text = (posture or "").strip()
    if not text:
        return ""
    for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-]{1,20}", text):
        if screener.resolve_license(token) in screener.ALLOWED_LICENSES:
            return token
    return text


# -- the choice -------------------------------------------------------------


def rank(sources: list[Source], yields: dict[str, tuple[int, int, int, str]], today: str = "") -> list[Ranked]:
    """Every source, best first, with the arithmetic that put it there.

    `yields` is `{source: (admitted, rejected, seen, last_run)}` from the ledger.
    Nothing here reads the network or a model: same inputs, same order.
    """
    today = today or date.today().isoformat()
    out: list[Ranked] = []
    for source in sources:
        admitted, rejected, seen, last_run = yields.get(source.name, (0, 0, 0, "never"))
        score = 0
        reasons: list[str] = []

        if source.kind == "index":
            score += 40
            reasons.append("an index — read for links, never staged")
        elif source.eligible:
            score += 100
            reasons.append(f"{source.spdx} is on the allowlist")
        else:
            reasons.append(f"posture `{source.posture or 'none'}` resolves to NONE-FOUND — the screen rejects it")

        if source.archived:
            score -= 30
            reasons.append("archived — a fixed amount left in it, nothing new arriving (-30)")

        decided = admitted + rejected
        if decided:
            rate = admitted / decided
            score += round(50 * rate)
            reasons.append(f"{admitted}/{decided} admitted at the door")
        else:
            score += 25
            reasons.append("never yielded a decision — unknown yield")

        if seen:
            drawn = min(40, 5 * seen)
            score -= drawn
            reasons.append(f"{seen} already in the ledger (-{drawn})")

        months = _months_since(last_run, today)
        if months:
            score += min(12, months)
            reasons.append(f"last drawn {last_run}")

        out.append(Ranked(source, score, admitted, rejected, seen, last_run, reasons))

    return sorted(out, key=lambda r: (-r.score, r.source.name))


def choose(ranked: list[Ranked], wanted: str = "") -> Ranked | None:
    """The one row this run draws from.

    `wanted` forces a row by name or by unambiguous substring, because a person who
    has a reason to draw from a particular place should not have to argue with a
    score. Without it, the best-scoring harvestable row wins; an ineligible row is
    never chosen, since a run that stages from it is a run that gets rejected.
    """
    if wanted:
        exact = [r for r in ranked if r.source.name == wanted]
        if exact:
            return exact[0]
        partial = [r for r in ranked if wanted.lower() in r.source.name.lower()]
        return partial[0] if len(partial) == 1 else None
    for row in ranked:
        if row.source.eligible or row.source.kind == "index":
            return row
    return None


def _months_since(last_run: str, today: str) -> int:
    """Whole months between two ISO dates. `never` is zero — untried is scored above."""
    if not last_run or last_run == "never":
        return 0
    try:
        then = date.fromisoformat(last_run)
        now = date.fromisoformat(today)
    except ValueError:
        return 0
    return max(0, (now.year - then.year) * 12 + (now.month - then.month))
