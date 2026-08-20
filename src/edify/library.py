"""Choosing which library entries go into a repository.

A skill file is persistent trusted context: once installed, every matching spawn
loads it as instruction. `select_for_stack` already narrows the library to what the
detected stack can use — this module is the step after, where a person confirms the
list before any of it becomes trusted context in their codebase.

Two rules hold it in place:

**A question is never load-bearing.** With no terminal — CI, a pipe, a model calling
the binary — nothing is asked and the stack-matched set is installed, which is what
this command did before the question existed. `--skills` states the answer up front
for a script that wants one.

**The question is a person's, never a model's.** `docs/design/architecture/09-cli.md` §1
says no `edify` command lets a model decide what is installed. Being asked in a
terminal does not change that; it narrows a set that was already computed by lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import EdifyError
from .formats import skill as skill_format
from .skills import select_for_stack
from .ui import Out


@dataclass(frozen=True)
class Candidate:
    path: Path
    skill: skill_format.Skill

    @property
    def name(self) -> str:
        return self.skill.name or self.path.stem


def candidates_for_stack(source_dir: Path, tech: list[str]) -> list[Candidate]:
    """The library entries this repository's stack matches, parsed and ordered."""
    chosen = select_for_stack(source_dir, tech)
    out = [Candidate(path, skill_format.parse(path, path.name)) for path in chosen]
    # Role entries every repository needs come first, then the stack-specific ones.
    return sorted(out, key=lambda c: (c.skill.tech != ["any"], c.skill.role, c.name))


def choose(out: Out, candidates: list[Candidate], spec: str = "auto") -> list[Candidate]:
    """Resolve `--skills` into the entries to install.

        auto            ask when there is a terminal, otherwise all
        all | yes       every entry the stack matched
        none            no entries — `edify skills add <path>` installs them later
        ask             ask, and fall back to all with nobody to ask
        <names…>        exactly these, by name or filename
    """
    if not candidates:
        return []

    wanted = (spec or "auto").strip()
    if wanted in ("all", "yes", "*"):
        return list(candidates)
    if wanted == "none":
        return []
    if wanted not in ("auto", "ask"):
        return _by_name(candidates, wanted)
    if wanted == "auto" and not out.interactive:
        return list(candidates)
    return _interview(out, candidates)


# ---------------------------------------------------------------------------


def _interview(out: Out, candidates: list[Candidate]) -> list[Candidate]:
    if not out.interactive:
        return list(candidates)

    out.prompt_line("")
    out.prompt_line(out.c("  the agent library", "bold"))
    out.prompt_line(
        out.c(
            "  These files become trusted instruction in every matching session."
            " Take the ones you want.",
            "dim",
        )
    )
    out.prompt_line("")
    width = max(len(c.name) for c in candidates)
    for i, candidate in enumerate(candidates, start=1):
        skill = candidate.skill
        out.prompt_line(
            f"  {str(i).rjust(2)}  {candidate.name.ljust(width)}  "
            f"{(skill.role or '-').ljust(11)} {_tech(skill.tech).ljust(26)} "
            + out.c(f"{skill.body_lines} lines · {skill.provenance or '-'}", "dim")
        )
        out.prompt_line(f"      {out.c(skill.description or '', 'dim')}")
    out.prompt_line("")

    while True:
        answer = out.ask(
            "  which entries? all · none · numbers like 1-4,7 · names, then enter",
            default="all",
        )
        try:
            return _parse(candidates, answer)
        except EdifyError as exc:
            out.warn(exc.message)


def _tech(tech: list[str], width: int = 26) -> str:
    """The stack column, kept to one width. A deep specialist names a dozen; the
    first two say what it is, and `edify skills list` has the full set."""
    full = " ".join(tech) or "any"
    if len(full) <= width:
        return full
    kept: list[str] = []
    for item in tech:
        if len(" ".join([*kept, item])) > width - 2:
            break
        kept.append(item)
    return " ".join(kept or tech[:1]) + " +" + str(len(tech) - len(kept or tech[:1]))


def _parse(candidates: list[Candidate], answer: str) -> list[Candidate]:
    text = answer.strip().lower()
    if text in ("all", "a", "yes", "y", "*", ""):
        return list(candidates)
    if text in ("none", "n", "-"):
        return []
    if any(ch.isdigit() for ch in text) and not any(c.isalpha() for c in text.replace("-", " ")):
        return _by_number(candidates, text)
    return _by_name(candidates, text)


def _by_number(candidates: list[Candidate], text: str) -> list[Candidate]:
    picked: set[int] = set()
    for part in text.replace(",", " ").split():
        if "-" in part:
            first, _, last = part.partition("-")
            try:
                lo, hi = int(first), int(last)
            except ValueError:
                raise EdifyError(f"`{part}` is not a number or a range") from None
            picked.update(range(min(lo, hi), max(lo, hi) + 1))
            continue
        try:
            picked.add(int(part))
        except ValueError:
            raise EdifyError(f"`{part}` is not a number or a range") from None

    out_of_range = sorted(n for n in picked if not 1 <= n <= len(candidates))
    if out_of_range:
        raise EdifyError(f"there is no entry {out_of_range[0]} — the list runs 1 to {len(candidates)}")
    return [candidates[n - 1] for n in sorted(picked)]


def _by_name(candidates: list[Candidate], text: str) -> list[Candidate]:
    by_name = {c.name.lower(): c for c in candidates}
    by_name.update({c.path.stem.lower(): c for c in candidates})
    picked: list[Candidate] = []
    unknown: list[str] = []
    for token in text.replace(",", " ").split():
        key = token.lower().removesuffix(".md")
        candidate = by_name.get(key)
        if candidate is None:
            unknown.append(token)
        elif candidate not in picked:
            picked.append(candidate)
    if unknown:
        raise EdifyError(
            f"no entry named `{unknown[0]}`",
            hint="names are the ones in the list; `all` takes every one of them",
        )
    return sorted(picked, key=lambda c: candidates.index(c))
