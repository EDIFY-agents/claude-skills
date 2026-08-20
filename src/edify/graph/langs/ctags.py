"""Adapter for a pinned external extractor.

The design's preferred extractor is a third-party static binary with syntax-tree
parsing and broad language coverage, wrapped so it emits our TSV contract. This is
that wrapper. The contract is the asset; the extractor is replaceable by
construction, and this module is the only thing that has to change when it is
replaced.

Nothing here is required. With no external extractor present the built-in backends
run and `meta` records which one produced each language.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from ..model import Edge, Extraction, Node, fingerprint, node_id

# ctags kinds → our node kinds. Anything unmapped is dropped rather than guessed.
_KIND_MAP = {
    "function": "symbol",
    "func": "symbol",
    "method": "symbol",
    "class": "symbol",
    "struct": "symbol",
    "interface": "symbol",
    "trait": "symbol",
    "enum": "symbol",
    "enumerator": "symbol",
    "constant": "symbol",
    "variable": "symbol",
    "member": "symbol",
    "typedef": "symbol",
    "type": "symbol",
    "module": "module",
    "namespace": "module",
    "package": "package",
    "table": "table",
}


def available(binary: str = "ctags") -> str | None:
    """The resolved path of the external extractor, or None."""
    path = shutil.which(binary)
    if not path:
        return None
    try:
        out = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    # Only the Universal variant emits the JSON we parse. The exuberant one does
    # not, and quietly producing nothing would be worse than declining.
    if "Universal Ctags" not in (out.stdout or "") + (out.stderr or ""):
        return None
    return path


def version(binary: str = "ctags") -> str:
    path = shutil.which(binary)
    if not path:
        return "-"
    try:
        out = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return "-"
    first = (out.stdout or out.stderr or "").splitlines()
    return first[0].strip() if first else "-"


def extract_tree(root: Path, files: list[str], binary: str = "ctags") -> Extraction:
    """Run the external extractor over an explicit file list.

    The file list comes from our own walk, so the extractor never decides what is
    in scope — ignore rules stay in one place.
    """
    out = Extraction()
    path = available(binary)
    if not path or not files:
        return out

    # A file list on stdin keeps the command line under every platform's limit.
    listing = "\n".join(files)
    try:
        proc = subprocess.run(
            [
                path,
                "--output-format=json",
                "--fields=+nKz",
                "--extras=",
                "-L",
                "-",
                "-f",
                "-",
            ],
            input=listing,
            capture_output=True,
            text=True,
            cwd=str(root),
            timeout=600,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return out

    seen_files: set[str] = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            tag = json.loads(line)
        except json.JSONDecodeError:
            continue
        if tag.get("_type") != "tag":
            continue
        rel = Path(tag.get("path", "")).as_posix().lstrip("./")
        name = tag.get("name")
        kind = _KIND_MAP.get(str(tag.get("kind", "")).lower())
        if not rel or not name or not kind:
            continue
        lineno = int(tag.get("line", 1) or 1)
        scope = tag.get("scope")
        qualified = f"{scope}.{name}" if scope else name

        file_id = node_id("file", rel, ".")
        if rel not in seen_files:
            seen_files.add(rel)
            module_id = node_id("module", rel, ".")
            out.nodes.append(Node(module_id, "module", rel, 1, rel.rsplit("/", 1)[-1]))
            out.edges.append(Edge(file_id, "defines", module_id))

        sym_id = node_id(kind, rel, qualified)
        signature = tag.get("signature") or tag.get("pattern") or qualified
        out.nodes.append(Node(sym_id, kind, rel, lineno, qualified, fingerprint(str(signature))))
        out.edges.append(Edge(node_id("module", rel, "."), "defines", sym_id))
        if tag.get("language"):
            out.languages.add(str(tag["language"]).lower())
    return out
