"""The two failure shapes the CLI has.

`EdifyError` is a condition the user can fix — a missing graph, an unreadable
registry, a licence that does not cover a command. It prints one line and exits
non-zero. Anything else is a bug and gets a traceback, because hiding one costs
more than it saves.
"""

from __future__ import annotations


class EdifyError(Exception):
    """A condition the person running the command can do something about."""

    exit_code = 1

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class NotInstalled(EdifyError):
    """`.edify/` is absent — the repository has never been initialised."""

    exit_code = 3

    def __init__(self, root: str) -> None:
        super().__init__(
            f"no .edify/ directory under {root}",
            hint="run `edify init` in the repository root",
        )


class GraphMissing(EdifyError):
    """The graph has not been extracted yet, or was removed."""

    exit_code = 4

    def __init__(self) -> None:
        super().__init__(
            "no graph on disk",
            hint="run `edify graph build`",
        )


class TierRequired(EdifyError):
    """A paid entitlement is needed. Stated plainly, with the price and both doors.

    The price appears here, at `edify license status`, and at the two soft caps
    that warn rather than raise. Nowhere else — no periodic reminder, nothing on an
    ordinary run. That is `docs/pricing.md` §4 commitment 3, and it was
    decided rather than overlooked.

    No new exit code: 7 already means "this needs the paid plan", and a second one
    would have to be documented in three places to buy nothing.
    """

    exit_code = 7

    def __init__(self, feature: str, plan: str = "pro") -> None:
        # Imported here rather than at module scope: `errors` is imported by
        # `licensing.tier`, and the other direction would be a cycle.
        from .licensing.tier import PRO_PRICE

        super().__init__(
            f"{feature} is part of the {plan} plan — {PRO_PRICE}",
            hint="edify license buy   ·   have a token already? edify license activate <token>",
        )
