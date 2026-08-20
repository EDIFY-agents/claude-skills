"""`edify graph` — build the map and ask it questions.

Six subcommands, all mechanical, all sub-second on a laptop. These are the commands
`CLAUDE.md` points at, and the only part of the CLI a model invokes routinely.
"""

from __future__ import annotations

from .. import anim
from ..context import Context
from ..graph import extract, queries
from ..licensing import tier


def build(ctx: Context) -> int:
    ctx.layout.require_installed()
    cap = ctx.entitlement.node_cap
    with anim.spinner(ctx.out, "reading every file, building the map"):
        result = extract.build(ctx.layout, backend=ctx.args.extractor, node_cap=cap)

    ctx.out.data(result.as_dict())
    ctx.out.line(
        f"{result.nodes} nodes · {result.edges} edges · {result.files} files"
        f" · {result.backend}"
    )
    covered = ", ".join(f"{k} ({v})" for k, v in sorted(result.languages.items()))
    if covered:
        ctx.out.line(f"covered: {covered}")
    if result.uncovered:
        ctx.out.line(
            "not covered: "
            + ", ".join(f"{k} ({v} files)" for k, v in sorted(result.uncovered.items()))
        )
        ctx.out.note("a language the extractor does not handle has no nodes. That gap is stated, not filled.")
    if result.truncated_at is not None:
        ctx.out.warn(
            f"the graph was truncated at {result.truncated_at:,} nodes — this repository is larger than the free plan covers"
        )
        ctx.out.note("a truncated graph answers fewer questions, exactly.")
        ctx.out.note(tier.upsell())
    return 0


def update(ctx: Context) -> int:
    ctx.layout.require_installed()
    ctx.store.require()
    with anim.spinner(ctx.out, f"re-extracting {len(ctx.args.dirs)} director(ies)"):
        result = extract.build(
            ctx.layout,
            backend=ctx.args.extractor,
            node_cap=ctx.entitlement.node_cap,
            subdirs=ctx.args.dirs,
        )
    ctx.out.data(result.as_dict())
    ctx.out.line(f"{result.nodes} nodes · {result.edges} edges (re-extracted {len(ctx.args.dirs)} directories)")
    return 0


def where(ctx: Context) -> int:
    ctx.store.require()
    hits = queries.where(ctx.store, ctx.args.name, kind=ctx.args.kind)
    ctx.out.data([_node(n) for n in hits])
    if not hits:
        ctx.out.line(f"nothing named `{ctx.args.name}` in the graph")
        return 1
    for node in hits:
        ctx.out.line(f"{node.ref}\t{node.kind}\t{node.name}")
    return 0


def dependents(ctx: Context) -> int:
    ctx.store.require()
    hits = queries.dependents(ctx.store, ctx.args.symbol, depth=ctx.args.depth)
    ctx.out.data([_node(n) for n in hits])
    if not hits:
        ctx.out.line(f"nothing in this repository depends on `{ctx.args.symbol}`")
        return 0
    for node in hits:
        ctx.out.line(f"{node.ref}\t{node.kind}\t{node.name}")
    return 0


def references(ctx: Context) -> int:
    ctx.store.require()
    hits = queries.references(ctx.store, ctx.args.name)
    ctx.out.data([_node(n) for n in hits])
    for node in hits:
        ctx.out.line(f"{node.ref}\t{node.kind}\t{node.name}")
    if not hits:
        ctx.out.line(f"no references to `{ctx.args.name}` in this repository")
    return 0


def defines(ctx: Context) -> int:
    ctx.store.require()
    hits = queries.defines(ctx.store, ctx.args.file)
    ctx.out.data([_node(n) for n in hits])
    if not hits:
        ctx.out.line(f"`{ctx.args.file}` defines nothing the graph indexes")
        return 0
    for node in hits:
        ctx.out.line(f"{node.line}\t{node.kind}\t{node.name}")
    return 0


def overlap(ctx: Context) -> int:
    ctx.store.require()
    a = _split(ctx.args.a)
    b = _split(ctx.args.b)
    result = queries.overlap(ctx.store, a, b, depth=ctx.args.depth)
    ctx.out.data(
        {
            "safe": result.safe,
            "overlapping": sorted(result.overlapping),
            "a_radius": sorted(result.a_radius),
            "b_radius": sorted(result.b_radius),
        }
    )
    if result.safe:
        ctx.out.line("disjoint — these may run in parallel")
        return 0
    ctx.out.line("overlapping:")
    for path in sorted(result.overlapping):
        ctx.out.line(f"  {path}")
    return 1


def stat(ctx: Context) -> int:
    ctx.store.require()
    meta = ctx.store.meta
    kinds: dict[str, int] = {}
    for node in ctx.store.nodes:
        kinds[node.kind] = kinds.get(node.kind, 0) + 1
    relations: dict[str, int] = {}
    for edge in ctx.store.edges:
        relations[edge.relation] = relations.get(edge.relation, 0) + 1

    ctx.out.data({"meta": meta, "kinds": kinds, "relations": relations})
    ctx.out.table(["kind", "count"], [[k, str(v)] for k, v in sorted(kinds.items())])
    ctx.out.line("")
    ctx.out.table(["relation", "count"], [[k, str(v)] for k, v in sorted(relations.items())])
    ctx.out.line("")
    for key in ("commit", "extractor", "extractor_version", "languages_covered", "languages_uncovered"):
        if key in meta:
            ctx.out.line(f"{key}: {meta[key]}")
    problems = ctx.store.verify_checksums()
    for problem in problems:
        ctx.out.warn(problem)
    return 0


def _split(value: str) -> list[str]:
    return [p.strip() for p in value.replace(",", " ").split() if p.strip()]


def _node(node) -> dict[str, object]:
    return {
        "id": node.id,
        "kind": node.kind,
        "file": node.file,
        "line": node.line,
        "name": node.name,
        "ref": node.ref,
        "fingerprint": node.fingerprint,
    }
