"""The mechanical half of `/harvest`.

`docs/design/architecture/10-harvest.md` splits curation into four steps and one door.
Three of the four steps are judgment and belong to a model; the parts that are not
judgment live here, because a lookup that gives the same answer on Tuesday is worth
more than a careful reading that does not.

What this package decides, and a model never does:

- **the licence** — an allowlist lookup, fail-closed. Whether we may ship somebody
  else's work is a legal question, not a plausible-sounding one.
- **whether we have seen this before** — a hash comparison against `ledger.json`.
- **whether the text is trying to give instructions** — a pattern scan whose only
  outcome is quarantine, which is a place things go rather than a decision made in
  passing.

What it refuses to decide: admission. There is one door and a person is standing
in it (`admit` will not run unattended, by construction).

Nothing here opens a socket. Gathering is the caller's job — the CLI stays a pure
function over files, so the bytes are already on disk before any of this runs.
"""

from __future__ import annotations

from . import ledger, screen

__all__ = ["ledger", "screen"]
