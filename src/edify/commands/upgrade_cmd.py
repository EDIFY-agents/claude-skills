"""`edify upgrade` — pull a newer skill library and re-index.

The one command in the working set that is allowed to reach the network, and it
has a documented plain-archive path so an air-gapped machine can still be
upgraded: download the archive somewhere with a network, carry it across, and
point `--archive` at it.

Nothing else in this CLI opens a socket while it is doing your work. The one other
command that can reach out is `edify self update`, which replaces the binary
itself rather than anything in a repository, and which hands the fetching to uv,
pipx, or pip rather than doing any of it here.
"""

from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .. import __version__, assets, governance, host, library, skills as skills_index
from ..context import Context
from ..errors import EdifyError
from ..formats import skill as skill_format
from ..tsv import sha256_file

DEFAULT_CHANNEL = "stable"
INDEX_URL = "https://registry.edify.dev/library/{channel}.json"


def run(ctx: Context) -> int:
    ctx.layout.require_installed()
    ctx.entitlement.require("library.upgrade")

    if ctx.args.archive:
        return _from_archive(ctx, Path(ctx.args.archive).expanduser())
    if ctx.args.check:
        return _check_only(ctx)
    return _from_network(ctx)


# ---------------------------------------------------------------------------


def _check_only(ctx: Context) -> int:
    manifest = _fetch_manifest(ctx)
    current = assets.manifest().get("library", "0")
    ctx.out.data({"installed": current, "available": manifest.get("version"), "cli": __version__})
    ctx.out.line(f"installed library {current} · available {manifest.get('version', 'unknown')}")
    return 0


def _from_network(ctx: Context) -> int:
    manifest = _fetch_manifest(ctx)
    url = manifest.get("archive")
    checksum = manifest.get("sha256")
    if not url:
        raise EdifyError("the channel manifest names no archive")

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "library-archive"
        try:
            with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 - pinned https
                target.write_bytes(response.read())
        except (urllib.error.URLError, OSError) as exc:
            raise EdifyError(
                f"could not reach {url}: {exc}",
                hint="download it on a networked machine and use `edify upgrade --archive <path>`",
            ) from exc

        actual = sha256_file(target)
        if checksum and actual != checksum:
            raise EdifyError(
                "the downloaded archive does not match the checksum in the manifest",
                hint="this is refused rather than installed — untrusted text becomes trusted context once installed",
            )
        return _from_archive(ctx, target)


def _from_archive(ctx: Context, archive: Path) -> int:
    """Install skill entries from a local archive.

    Every entry is validated before it lands. An archive is untrusted text until
    something has read it, and a skill file is persistent trusted context in every
    session that loads it — so an invalid entry is rejected, not repaired.
    """
    if not archive.is_file():
        raise EdifyError(f"{archive} is not a file")

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "staged"
        staging.mkdir()
        _unpack(archive, staging)

        candidates = sorted(staging.rglob("*.md"))
        if not candidates:
            raise EdifyError("the archive contains no skill entries")

        staged, rejected = [], []
        for path in candidates:
            parsed = skill_format.parse(path, path.name)
            problems = [p for p in skill_format.validate(parsed) if p[0] != "skill-over-budget"]
            if problems:
                rejected.append((path.name, problems[0][1]))
                continue
            if parsed.provenance == "adapted" and not parsed.license:
                rejected.append((path.name, "adapted with no licence"))
                continue
            staged.append(library.Candidate(path, parsed))

        # The same question `init` asks, for the same reason: these arrived from
        # outside and become trusted instruction the moment they land.
        spec = "all" if getattr(ctx.args, "yes", False) else getattr(ctx.args, "skills", "auto")
        chosen = library.choose(ctx.out, staged, spec)
        installed = []
        for candidate in chosen:
            shutil.copyfile(candidate.path, ctx.layout.skills_dir / candidate.path.name)
            installed.append(candidate.name)
        declined = len(staged) - len(chosen)

    rows, skipped = skills_index.build_index(ctx.layout)
    # A newly installed entry that the host runtime cannot see is not installed in the
    # only sense the person cares about, so the mirror moves with the library.
    mirrored = host.sync(ctx.layout)
    ledger = governance.rebuild(ctx.layout)
    ctx.out.data(
        {
            "installed": installed,
            "declined": declined,
            "rejected": rejected,
            "index_rows": rows,
            "mirrored": sum(1 for m in mirrored if m.kind == "skill"),
            "governed_files": len(ledger),
        }
    )
    ctx.out.line(
        f"{len(installed)} entries installed · {declined} declined · index now {rows} rows"
    )
    for name, reason in rejected:
        ctx.out.warn(f"rejected {name}: {reason}")
    for problem in skipped:
        ctx.out.warn(f"skipped in index — {problem}")
    for path in host.stale(ctx.layout):
        ctx.out.warn(f"{ctx.layout.rel(path)} points at an entry that is no longer installed — safe to delete")
    return 0


def _fetch_manifest(ctx: Context) -> dict:
    url = INDEX_URL.format(channel=ctx.args.channel or DEFAULT_CHANNEL)
    try:
        with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - pinned https
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        raise EdifyError(
            f"could not reach the library channel: {exc}",
            hint="everything except `upgrade` works offline; use `--archive <path>` on an air-gapped network",
        ) from exc


def _unpack(archive: Path, into: Path) -> None:
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            for member in zf.namelist():
                if member.startswith("/") or ".." in Path(member).parts:
                    raise EdifyError(f"the archive contains an unsafe path: {member}")
            zf.extractall(into)
        return
    if tarfile.is_tarfile(archive):
        with tarfile.open(archive) as tf:
            for member in tf.getmembers():
                if member.name.startswith("/") or ".." in Path(member.name).parts:
                    raise EdifyError(f"the archive contains an unsafe path: {member.name}")
            tf.extractall(into, filter="data")
        return
    raise EdifyError(f"{archive} is neither a zip nor a tar archive")
