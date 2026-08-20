"""Sorted, checksummed TSV.

Both graph files and the skill index are sorted text, so a rebuild over unchanged
input produces byte-identical output. That property is what makes "did the graph
change?" a comparison rather than an analysis, and it is why nothing here writes a
timestamp.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, Iterator, Sequence

_ESCAPES = {"\t": "\\t", "\n": "\\n", "\r": "\\r", "\\": "\\\\"}


def escape(value: str) -> str:
    """Make a field safe for a tab-separated line, reversibly."""
    out = []
    for ch in str(value):
        if ch == "\\":
            out.append("\\\\")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        else:
            out.append(ch)
    return "".join(out)


def unescape(value: str) -> str:
    out = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            out.append({"t": "\t", "n": "\n", "r": "\r", "\\": "\\"}.get(nxt, nxt))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def write_rows(path: Path, rows: Iterable[Sequence[str]], header: Sequence[str] | None = None) -> str:
    """Write rows sorted, LF-terminated, and return the file's sha256.

    Sorting is on the rendered line, so the ordering is a property of the bytes
    rather than of whatever object produced them.
    """
    lines = sorted("\t".join(escape(c) for c in row) for row in rows)
    body = ""
    if header:
        body += "#" + "\t".join(header) + "\n"
    body += "".join(line + "\n" for line in lines)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body.encode("utf-8"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def read_rows(path: Path) -> Iterator[list[str]]:
    """Stream a TSV, skipping the comment header. Never loads the whole file."""
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n").rstrip("\r")
            if not line or line.startswith("#"):
                continue
            yield [unescape(c) for c in line.split("\t")]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    if not path.exists():
        return "-"
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_kv(path: Path) -> dict[str, str]:
    """The `meta` file: one `key=value` per line, no nesting, no timestamps."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip()
    return out


def write_kv(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"{k}={v}\n" for k, v in sorted(values.items()))
    path.write_bytes(body.encode("utf-8"))
