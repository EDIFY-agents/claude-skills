"""`harvest/ledger.json` — every candidate ever seen, and what became of it.

One file, one job: **nothing is gathered, screened, or offered twice.** A harvest
run that re-proposes last month's rejection wastes the only expensive step in the
pipeline, which is the human reading at the end of it.

A candidate is recognised by three independent keys — its URL, the sha256 of its
raw bytes, and the entry name it would take. Any one matching is a match, because
the same file moves between repositories, gets re-tagged, and arrives renamed.

JSON rather than TSV, unlike the rest of `.edify/`: a ledger row is a nested record
(a screen verdict holds a list of checks) and the sorted-TSV property that makes the
graph diffable buys nothing for a file nobody rebuilds. Written sorted and indented
so a diff still reads.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterator

SCHEMA = 1

# In flight, then terminal. A candidate in a terminal state is never offered again;
# one in flight is resumable but also never re-gathered.
IN_FLIGHT = ("staged", "screened", "proposed")
TERMINAL = ("admitted", "rejected", "quarantined")
STATES = IN_FLIGHT + TERMINAL

_SLUG = re.compile(r"[^a-z0-9]+")


def slug(text: str) -> str:
    return _SLUG.sub("-", text.strip().lower()).strip("-") or "candidate"


def candidate_id(name: str, content_sha: str) -> str:
    """Stable across runs: the same bytes under the same name are the same id."""
    return f"{slug(name)}-{content_sha[:8]}"


def normalise_url(url: str) -> str:
    """Enough normalisation that a trailing slash is not a second candidate."""
    u = url.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.rstrip("/")


@dataclass
class Candidate:
    id: str
    name: str
    url: str
    content_sha256: str
    source: str = "-"
    commit: str = "-"
    license: str = "NONE-FOUND"
    state: str = "staged"
    first_seen: str = ""
    updated: str = ""
    screen: dict[str, Any] = field(default_factory=dict)
    disposition: dict[str, Any] = field(default_factory=dict)

    @property
    def screened_pass(self) -> bool:
        return self.screen.get("verdict") == "pass"

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "content_sha256": self.content_sha256,
            "source": self.source,
            "commit": self.commit,
            "license": self.license,
            "state": self.state,
            "first_seen": self.first_seen,
            "updated": self.updated,
            "screen": self.screen,
            "disposition": self.disposition,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Candidate":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


class Ledger:
    """The whole file, held in memory. It is a few hundred records at most."""

    def __init__(self, path: Path, candidates: dict[str, Candidate] | None = None):
        self.path = path
        self.candidates: dict[str, Candidate] = candidates or {}

    # -- io --------------------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> "Ledger":
        """A missing ledger is an empty one — the first run must not need a setup step."""
        if not path.is_file():
            return cls(path)
        raw = json.loads(path.read_text(encoding="utf-8") or "{}")
        found = raw.get("schema", SCHEMA)
        if found > SCHEMA:
            raise ValueError(f"{path} is schema {found}; this edify understands {SCHEMA}")
        entries = {k: Candidate.from_json(v) for k, v in (raw.get("candidates") or {}).items()}
        return cls(path, entries)

    def save(self) -> None:
        payload = {
            "schema": SCHEMA,
            "updated": date.today().isoformat(),
            "candidates": {k: self.candidates[k].to_json() for k in sorted(self.candidates)},
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # -- the one question this file exists to answer ----------------------

    def seen(self, *, url: str = "", content_sha: str = "", name: str = "") -> Candidate | None:
        """Have we handled this before, under any of its three identities?"""
        wanted_url = normalise_url(url) if url else ""
        for cand in self.candidates.values():
            if wanted_url and normalise_url(cand.url) == wanted_url:
                return cand
            if content_sha and cand.content_sha256 == content_sha:
                return cand
            if name and cand.name == name:
                return cand
        return None

    # -- mutation --------------------------------------------------------

    def add(self, cand: Candidate) -> Candidate:
        today = date.today().isoformat()
        cand.first_seen = cand.first_seen or today
        cand.updated = today
        self.candidates[cand.id] = cand
        return cand

    def get(self, cid: str) -> Candidate | None:
        if cid in self.candidates:
            return self.candidates[cid]
        # A prefix is enough as long as it is unambiguous — ids carry a hash tail
        # nobody wants to type.
        matches = [c for k, c in self.candidates.items() if k.startswith(cid)]
        return matches[0] if len(matches) == 1 else None

    def set_state(self, cand: Candidate, state: str) -> None:
        if state not in STATES:
            raise ValueError(f"unknown state: {state}")
        cand.state = state
        cand.updated = date.today().isoformat()

    # -- reading ---------------------------------------------------------

    def in_state(self, *states: str) -> list[Candidate]:
        return [c for c in self.sorted() if c.state in states]

    def sorted(self) -> list[Candidate]:
        return [self.candidates[k] for k in sorted(self.candidates)]

    def counts(self) -> dict[str, int]:
        out = {s: 0 for s in STATES}
        for cand in self.candidates.values():
            out[cand.state] = out.get(cand.state, 0) + 1
        return out

    def by_source(self) -> Iterator[tuple[str, int, int, int, str]]:
        """`source, admitted, rejected, seen, last run` — the yield history sources.md carries.

        Counts come from the human door, not the screen. A source with a high screen
        pass rate and a low admission rate is producing plausible files, which is the
        failure mode worth noticing.
        """
        sources: dict[str, list[Candidate]] = {}
        for cand in self.candidates.values():
            sources.setdefault(cand.source or "-", []).append(cand)
        for name in sorted(sources):
            group = sources[name]
            admitted = sum(1 for c in group if c.state == "admitted")
            rejected = sum(1 for c in group if c.state in ("rejected", "quarantined"))
            last = max((c.updated for c in group if c.updated), default="never")
            yield name, admitted, rejected, len(group), last
