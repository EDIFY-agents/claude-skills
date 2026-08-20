"""Finding the shipped methodology tree.

The authored tree lives at the repository root in `edify/` (the source tree of
`docs/design/architecture/01-folder-structure.md` §1) and is copied into the wheel at
`edify/assets/`. Both layouts resolve here, so a developer running from a checkout
and a user running an installed wheel get the same files.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from .errors import EdifyError

_SUBTREES = ("commands", "formats", "skills", "mcp", "harvest", "templates")


@lru_cache(maxsize=1)
def asset_root() -> Path:
    """The directory holding manifest.md, commands/, formats/, skills/, mcp/, harvest/."""
    override = os.environ.get("EDIFY_ASSETS")
    if override:
        p = Path(override).expanduser().resolve()
        if _looks_like_assets(p):
            return p
        raise EdifyError(f"EDIFY_ASSETS points at {p}, which has no commands/ or skills/")

    # Installed wheel: src/edify/assets/
    packaged = Path(__file__).resolve().parent / "assets"
    if _looks_like_assets(packaged):
        return packaged

    # Developer checkout: <repo>/edify/
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "edify"
        if candidate != packaged and _looks_like_assets(candidate):
            return candidate

    raise EdifyError(
        "the methodology tree is missing from this install",
        hint="reinstall edify-cli, or set EDIFY_ASSETS to a checkout's edify/ directory",
    )


def _looks_like_assets(path: Path) -> bool:
    return path.is_dir() and (path / "commands").is_dir() and (path / "skills").is_dir()


def subtree(name: str) -> Path:
    if name not in _SUBTREES:
        raise EdifyError(f"unknown asset subtree: {name}")
    return asset_root() / name


def read(*parts: str) -> str:
    path = asset_root().joinpath(*parts)
    if not path.is_file():
        raise EdifyError(f"missing shipped asset: {'/'.join(parts)}")
    return path.read_text(encoding="utf-8")


def manifest() -> dict[str, str]:
    """The pinned versions and checksums the install declares. Flat key: value."""
    out: dict[str, str] = {}
    path = asset_root() / "manifest.md"
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("- ") or ":" not in line:
            continue
        key, _, value = line[2:].partition(":")
        out[key.strip().strip("`*")] = value.strip().strip("`")
    return out
