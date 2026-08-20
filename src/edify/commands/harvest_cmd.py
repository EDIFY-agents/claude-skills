"""`edify harvest` — the mechanical steps of the curation pipeline.

    pick ──▶ stage ──▶ screen ──▶ propose ──▶ ◆ admit | reject

`pick`, `stage`, `screen`, and `propose` run unattended. `admit` does not, and no
flag makes it: it is the only thing standing between a stranger's text and
persistent trusted context in a customer's repository, and it costs a person
minutes per entry.

The gathering itself is not here. `10-harvest.md` puts fetching in step ①, but the
CLI is a pure function over files — `edify` opens no socket except `upgrade` — so
the caller fetches and `stage` records what arrived. That split is also why the raw
bytes land in a `.txt` file rather than a `.md` one: nothing downstream should be
tempted to read a candidate as a document when it is evidence.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path

from ..context import Context
from ..errors import EdifyError
from ..formats import skill as skill_format
from ..harvest import screen as screener
from ..harvest import sources as source_table
from ..harvest.ledger import Candidate, Ledger, candidate_id
from ..tsv import sha256_bytes


def _guard(ctx: Context) -> Ledger:
    """Harvest runs in EDIFY's own repository, never in a client's."""
    if not ctx.layout.is_edify_repo():
        raise EdifyError(
            "harvest runs in EDIFY's own repository, never in a client's",
            hint="a client's own conventions go straight into .edify/skills/ with `provenance: client`",
        )
    return Ledger.load(ctx.layout.harvest_ledger)


def _find(ledger: Ledger, cid: str) -> Candidate:
    cand = ledger.get(cid)
    if not cand:
        raise EdifyError(f"no candidate `{cid}` in the ledger", hint="`edify harvest status` lists what is in flight")
    return cand


# -- ① pick -----------------------------------------------------------------


def pick(ctx: Context) -> int:
    """Which source to draw from, and what not to gather again.

    Two answers, and the first one used to be missing. `pick` printed the whole
    source table and left the choice of row to the caller, which meant the choice was
    a model's mood: a run could draw from an archived upstream, or from the row whose
    licence the screen was always going to reject, and nothing in the pipeline
    noticed until step ②. Selecting a row is a lookup over the table and the ledger,
    so it happens here — deterministic, with the arithmetic printed.

    The second answer is the three identities of everything ever handled, so a
    candidate rejected in March is never re-read, re-screened, or re-proposed in
    August.
    """
    ledger = _guard(ctx)
    sources = source_table.read(ctx.layout.harvest_refs / "sources.md")
    yields = {row[0]: (row[1], row[2], row[3], row[4]) for row in ledger.by_source()}
    ranked = source_table.rank(sources, yields)
    wanted = getattr(ctx.args, "source", "") or ""
    chosen = source_table.choose(ranked, wanted)

    if wanted and not chosen:
        raise EdifyError(
            f"no source in the table matches `{wanted}`",
            hint="`edify harvest pick` with no --source lists every row",
        )

    seen = {
        "urls": sorted({c.url for c in ledger.sorted() if c.url}),
        "names": sorted({c.name for c in ledger.sorted() if c.name}),
        "sha256": sorted({c.content_sha256 for c in ledger.sorted() if c.content_sha256}),
    }
    in_flight = ledger.in_state("staged", "screened", "proposed")
    ctx.out.data(
        {
            "chosen": chosen.to_json() if chosen else None,
            "sources": [r.to_json() for r in ranked],
            "yield": [
                dict(zip(("source", "admitted", "rejected", "seen", "last_run"), y)) for y in ledger.by_source()
            ],
            "seen": seen,
            "budget": getattr(ctx.args, "count", 0),
            "in_flight": [c.id for c in in_flight],
        }
    )

    if not ranked:
        ctx.out.line("no sources listed")
        ctx.out.note("add one to edify/harvest/sources.md — adding a source is a reviewed change")
        return 0

    if chosen:
        ctx.out.line(f"draw from  {chosen.source.name}")
        ctx.out.line(f"fetch      {chosen.source.fetch or '(the whole tree — no fetch path recorded)'}")
        ctx.out.line(f"posture    {chosen.source.posture or 'none recorded'}")
        ctx.out.line(f"why        {chosen.why}")
        if chosen.source.kind == "index":
            ctx.out.warn(
                "this row is an index — read it for links and draw from what they point at, "
                "under that repository's own licence. Never stage its bytes."
            )
        ctx.out.line("")
    else:
        ctx.out.warn("no source in the table can be harvested from — every posture resolves to NONE-FOUND")

    if getattr(ctx.args, "all", False) or not chosen:
        rows = [
            [
                ("→ " if chosen and r is chosen else "  ") + r.source.name,
                r.source.kind,
                r.source.spdx,
                str(r.score),
                f"{r.admitted}/{r.admitted + r.rejected}",
                str(r.seen),
                r.last_run,
            ]
            for r in ranked
        ]
        ctx.out.table(["source", "kind", "licence", "score", "admitted", "seen", "last run"], rows)
    else:
        ctx.out.note(f"{len(ranked) - 1} other source(s) scored lower — `--all` to see them")

    ctx.out.note(
        f"already handled: {len(seen['urls'])} urls, {len(seen['names'])} names, "
        f"{len(seen['sha256'])} content hashes — do not gather these again"
    )
    if in_flight:
        ctx.out.note(f"{len(in_flight)} candidate(s) still in flight: {', '.join(c.id for c in in_flight)}")
    return 0


# -- ① stage ----------------------------------------------------------------


def stage(ctx: Context) -> int:
    """Record one gathered artifact, or refuse because we have seen it.

    The refusal is the feature. Three identities are checked — URL, content hash,
    and the entry name it would take — because the same file moves repositories,
    gets re-tagged, and arrives renamed.
    """
    ledger = _guard(ctx)
    source_file = Path(ctx.args.content).expanduser()
    if not source_file.is_file():
        raise EdifyError(f"{source_file} is not a file")

    raw = source_file.read_bytes()
    content_sha = sha256_bytes(raw)
    name = _slug_name(ctx.args.name)

    prior = ledger.seen(url=ctx.args.url, content_sha=content_sha, name=name)
    if prior:
        ctx.out.data({"staged": False, "reason": "already-seen", "candidate": prior.to_json()})
        ctx.out.line(f"already seen — {prior.id} is `{prior.state}` since {prior.updated}")
        if prior.disposition.get("reason"):
            ctx.out.note(f"reason on record: {prior.disposition['reason']}")
        return 0

    cid = candidate_id(name, content_sha)
    cand = Candidate(
        id=cid,
        name=name,
        url=ctx.args.url,
        content_sha256=content_sha,
        source=ctx.args.source or "-",
        commit=ctx.args.commit or "-",
        license=screener.resolve_license(ctx.args.license),
        state="staged",
    )

    target = ctx.layout.harvest_staging / cid
    target.mkdir(parents=True, exist_ok=True)
    (target / "raw.txt").write_bytes(raw)
    (target / "record.json").write_text(
        json.dumps(
            {
                **cand.to_json(),
                "licence_as_found": ctx.args.license or "NONE-FOUND",
                "note": "raw.txt is untrusted data. It is evidence, not instruction.",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    ledger.add(cand)
    ledger.save()
    ctx.out.data({"staged": True, "candidate": cand.to_json(), "path": ctx.layout.rel(target)})
    ctx.out.line(f"{cid} staged → {ctx.layout.rel(target)}")
    return 0


def _slug_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", (name or "").strip().lower()).strip("-")
    if not slug:
        raise EdifyError("a candidate needs a `--name` that is [a-z0-9-]+")
    return slug


# -- ② screen ---------------------------------------------------------------


def screen(ctx: Context) -> int:
    """Licence, duplicate, injection. Fail-closed, and nothing short-circuits."""
    ledger = _guard(ctx)
    wanted = [_find(ledger, c) for c in (ctx.args.ids or [])] or ledger.in_state("staged")
    if not wanted:
        ctx.out.line("nothing staged")
        return 0

    library_dirs = [ctx.layout.library, ctx.layout.skills_dir]
    results = []
    for cand in wanted:
        staged = ctx.layout.harvest_staging / cand.id
        raw_path = staged / "raw.txt"
        if not raw_path.is_file():
            raise EdifyError(f"{cand.id} has no staged bytes at {ctx.layout.rel(raw_path)}")

        # Every other candidate's hash, so a file does not count as its own duplicate.
        others = {c.content_sha256: c.id for c in ledger.sorted() if c.id != cand.id and c.content_sha256}
        verdict = screener.screen(
            name=cand.name,
            license_found=cand.license,
            content=raw_path.read_text(encoding="utf-8", errors="replace"),
            content_sha=cand.content_sha256,
            library_dirs=library_dirs,
            existing_shas=others,
        )
        cand.screen = verdict.to_json()

        if verdict.verdict == "quarantine":
            ledger.set_state(cand, "quarantined")
            _move(staged, ctx.layout.harvest_quarantine / cand.id, verdict)
        elif verdict.verdict == "reject":
            ledger.set_state(cand, "rejected")
            cand.disposition = {
                "by": "screen",
                "on": date.today().isoformat(),
                "reason": "; ".join(c.detail for c in verdict.failures),
            }
        else:
            ledger.set_state(cand, "screened")

        results.append((cand, verdict))

    ledger.save()
    ctx.out.data([{"id": c.id, **v.to_json()} for c, v in results])
    ctx.out.table(
        ["candidate", "verdict", "why"],
        [
            [c.id, v.verdict, "ok" if v.verdict == "pass" else "; ".join(f.code for f in v.failures)]
            for c, v in results
        ],
    )
    for cand, verdict in results:
        if verdict.verdict == "quarantine":
            ctx.out.warn(f"{cand.id} quarantined → {ctx.layout.rel(ctx.layout.harvest_quarantine / cand.id)}")
    return 0


def _move(staged: Path, target: Path, verdict: screener.Verdict) -> None:
    """Quarantine is a place things go, not a decision made in passing."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    if staged.is_dir():
        shutil.move(str(staged), str(target))
    else:
        target.mkdir(parents=True, exist_ok=True)
    (target / "screen.json").write_text(json.dumps(verdict.to_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


# -- ④ propose --------------------------------------------------------------


def propose(ctx: Context) -> int:
    """The rewritten file, the original beside it, the provenance, and the case.

    Refuses a rewrite that would not survive `edify check`, and refuses one that
    claims `provenance: original` — a file that came from somewhere else is
    `adapted`, and its `license` field is the SPDX id plus `repo@commit`.
    """
    ledger = _guard(ctx)
    cand = _find(ledger, ctx.args.id)
    if cand.state != "screened":
        raise EdifyError(
            f"{cand.id} is `{cand.state}` — only a screened candidate can be proposed",
            hint="run `edify harvest screen` first; a rejected or quarantined candidate does not proceed",
        )

    rewritten = Path(ctx.args.file).expanduser()
    if not rewritten.is_file():
        raise EdifyError(f"{rewritten} is not a file")

    parsed = skill_format.parse(rewritten, rewritten.name)
    problems = skill_format.validate(parsed)
    if problems:
        for _, message, line in problems:
            ctx.out.error(f"{rewritten.name}:{line} {message}")
        raise EdifyError("the rewrite is not a valid entry", hint="eight frontmatter fields, four sections, under budget")
    if parsed.provenance != "adapted":
        raise EdifyError(
            f"`provenance: {parsed.provenance}` — anything harvested is `adapted`",
            hint=f"and `license: {cand.license} {_repo_at_commit(cand)}`",
        )

    target = ctx.layout.harvest_proposals / cand.id
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(rewritten, target / "rewritten.md")
    staged_raw = ctx.layout.harvest_staging / cand.id / "raw.txt"
    original_lines = 0
    if staged_raw.is_file():
        shutil.copyfile(staged_raw, target / "original.txt")
        original_lines = len(staged_raw.read_text(encoding="utf-8", errors="replace").splitlines())

    (target / "proposal.md").write_text(
        _proposal(cand, parsed, ctx.args.case, original_lines, ctx.layout.rel(target)), encoding="utf-8"
    )
    ledger.set_state(cand, "proposed")
    ledger.save()

    ctx.out.data({"id": cand.id, "path": ctx.layout.rel(target), "lines": parsed.body_lines, "was": original_lines})
    ctx.out.line(f"{cand.id} proposed → {ctx.layout.rel(target / 'proposal.md')}")
    ctx.out.note(f"{original_lines} lines in, {parsed.body_lines} out · a person reads it next")
    return 0


def _repo_at_commit(cand: Candidate) -> str:
    repo = re.sub(r"^https?://(www\.)?", "", cand.url).rstrip("/")
    return f"{repo}@{cand.commit}"


def _proposal(cand: Candidate, parsed, case: str, original_lines: int, rel: str) -> str:
    checks = "\n".join(
        f"- `{c['code']}` {'ok' if c['ok'] else 'FAIL'} — {c['detail']}" for c in cand.screen.get("checks", [])
    )
    return f"""# Proposal — {cand.name}

`{cand.id}` · staged {cand.first_seen} · **awaiting a human**

## What it serves

{case}

## Provenance

| field | value |
|---|---|
| url | {cand.url} |
| commit | {cand.commit} |
| licence | {cand.license} |
| source | {cand.source} |
| sha256 | {cand.content_sha256} |

## Screen

Verdict: **{cand.screen.get('verdict', '-')}**

{checks}

## The rewrite

`{rel}/rewritten.md` — {parsed.body_lines} lines of body, from {original_lines}.
The original is beside it at `{rel}/original.txt`, which is data and not a document.

| field | value |
|---|---|
| role | {parsed.role} |
| phase | {' '.join(parsed.phases)} |
| tech | {' '.join(parsed.tech)} |
| provenance | {parsed.provenance} |
| license | {parsed.license} |

## The door

Read `rewritten.md` in full, then:

    edify harvest admit {cand.id} --by <your name>
    edify harvest reject {cand.id} --reason "<why>"

There is no other door — not for speed, not for volume.
"""


# -- ◆ the human door -------------------------------------------------------


def admit(ctx: Context) -> int:
    """A person read it and says yes. This is the only step that cannot be automated.

    It refuses to run without a terminal. A `--yes` flag here would be the whole
    pipeline's single point of failure, so there is not one.
    """
    ledger = _guard(ctx)
    cand = _find(ledger, ctx.args.id)
    if cand.state != "proposed":
        raise EdifyError(
            f"{cand.id} is `{cand.state}` — only a proposed candidate can be admitted",
            hint="gather, screen, and propose come first",
        )
    if not cand.screen.get("verdict") == "pass":
        raise EdifyError(f"{cand.id} did not pass the screen", hint="a screen failure is not a judgment call")

    proposal = ctx.layout.harvest_proposals / cand.id / "rewritten.md"
    if not proposal.is_file():
        raise EdifyError(f"no rewrite at {ctx.layout.rel(proposal)}")

    if not ctx.out.interactive:
        raise EdifyError(
            "admission needs a person at a terminal",
            hint="gather, screen, rewrite, and propose run unattended; this one does not, and no flag changes that",
        )
    ctx.out.prompt_line(f"\n{proposal.read_text(encoding='utf-8')}\n")
    answer = ctx.out.ask(f"admit {cand.id} as `{cand.name}` into the library? (type the name to confirm)")
    if answer.strip() != cand.name:
        ctx.out.line("not admitted")
        return 1

    parsed = skill_format.parse(proposal, proposal.name)
    target = ctx.layout.library / f"{parsed.name}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(proposal, target)

    ledger.set_state(cand, "admitted")
    cand.disposition = {"by": ctx.args.by, "on": date.today().isoformat(), "reason": "admitted"}
    ledger.save()

    installed, mirrored = _setup(ctx, target)

    ctx.out.data(
        {
            "id": cand.id,
            "admitted": True,
            "path": ctx.layout.rel(target),
            "installed": ctx.layout.rel(installed) if installed else None,
            "mirrored": [ctx.layout.rel(p) for p in mirrored],
        }
    )
    ctx.out.ok(f"{cand.name} → {ctx.layout.rel(target)}")
    if installed:
        ctx.out.ok(f"installed here too → {ctx.layout.rel(installed)} · indexed")
    for path in mirrored:
        ctx.out.ok(f"the runtime can see it at → {ctx.layout.rel(path)}")
    ctx.out.note("record the yield in edify/harvest/sources.md — `edify harvest status` prints the row")
    return 0


def _setup(ctx: Context, entry: Path) -> tuple[Path | None, list[Path]]:
    """The step after the door: an admitted entry becomes a usable one.

    Admission copies the rewrite into `edify/skills/`, which is the authored library —
    the thing that ships. That is not the same as being installed: `edify skills
    resolve` reads `.edify/skills/`, and the host runtime reads `.claude/`, in one of
    two shapes depending on the entry's `kind` — `skills/<name>/SKILL.md` for a skill,
    `agents/<name>.md` for an agent. An entry that is only in the authored tree is
    admitted and unusable, and the gap was quiet enough that a run could look finished
    while nothing could load what it produced.

    Returns both halves so admission can report where the thing actually is rather
    than naming a directory and hoping. This is deliberately behind the human door
    rather than before it — installing a stranger's text is exactly the thing that
    waits for a person to say yes.
    """
    from .. import governance, host, skills as skills_index

    ctx.layout.skills_dir.mkdir(parents=True, exist_ok=True)
    installed = ctx.layout.skills_dir / entry.name
    shutil.copyfile(entry, installed)
    rows, skipped = skills_index.build_index(ctx.layout)
    written = host.sync(ctx.layout)
    governance.rebuild(ctx.layout)
    for problem in skipped:
        ctx.out.warn(f"skipped in index — {problem}")
    ctx.out.note(f"index now {rows} rows")

    name = skill_format.parse(installed, ctx.layout.rel(installed)).name
    mirrored = [w.path for w in written if w.name == name and w.kind in ("skill", "agent")]
    return installed, mirrored


def reject(ctx: Context) -> int:
    """A person read it and says no. The reason is the point — it is why this is cheap next time."""
    ledger = _guard(ctx)
    cand = _find(ledger, ctx.args.id)
    if cand.state in ("admitted",):
        raise EdifyError(f"{cand.id} is already admitted", hint="remove the entry from the library by hand")
    ledger.set_state(cand, "rejected")
    cand.disposition = {"by": ctx.args.by or "-", "on": date.today().isoformat(), "reason": ctx.args.reason}
    ledger.save()
    ctx.out.data({"id": cand.id, "rejected": True, "reason": ctx.args.reason})
    ctx.out.line(f"{cand.id} rejected — {ctx.args.reason}")
    return 0


# -- status -----------------------------------------------------------------


def status(ctx: Context) -> int:
    ledger = _guard(ctx)
    counts = ledger.counts()
    rows = [
        [c.id, c.state, c.license, c.source, c.updated, (c.disposition.get("reason") or "")[:48]]
        for c in ledger.sorted()
    ]
    ctx.out.data(
        {
            "counts": counts,
            "candidates": [c.to_json() for c in ledger.sorted()],
            "yield": [dict(zip(("source", "admitted", "rejected", "seen", "last_run"), y)) for y in ledger.by_source()],
        }
    )
    if not rows:
        ctx.out.line("nothing harvested")
        ctx.out.note("`edify harvest pick` lists the sources")
        return 0
    ctx.out.table(["candidate", "state", "licence", "source", "updated", "reason"], rows)
    ctx.out.line("")
    ctx.out.line("  ".join(f"{k} {v}" for k, v in counts.items() if v))
    ctx.out.line("")
    ctx.out.line("yield, for edify/harvest/sources.md:")
    for name, admitted, rejected, _seen, last in ledger.by_source():
        ctx.out.line(f"| {name} | | | {admitted} | {rejected} | {last} |")
    return 0
