"""Markdown headings as `doc-section` nodes.

Structural rather than scanned: a heading is a heading. This is what lets a spec's
`## Assertions` block be cited as `file:line` and what makes `documents` edges
possible between a document section and the module it describes.
"""

from __future__ import annotations

import re

from ..model import Edge, Extraction, Node, fingerprint, node_id

_HEADING = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


def extract(rel_path: str, source: str) -> Extraction:
    out = Extraction(languages={"markdown"})
    file_id = node_id("file", rel_path, ".")
    in_fence = False
    stack: list[str] = []

    for lineno, raw in enumerate(source.splitlines(), start=1):
        if _FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING.match(raw)
        if not m:
            continue
        depth = len(m.group("hashes"))
        title = m.group("title").strip()
        del stack[depth - 1 :]
        stack.append(title)
        name = " > ".join(stack)
        sec_id = node_id("doc-section", rel_path, name)
        out.nodes.append(Node(sec_id, "doc-section", rel_path, lineno, name, fingerprint(title)))
        out.edges.append(Edge(file_id, "defines", sec_id))
    return out
