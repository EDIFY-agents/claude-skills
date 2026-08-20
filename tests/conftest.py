"""Fixtures: a small repository with a real shape, and an isolated EDIFY home.

Every test that touches the filesystem gets its own temporary tree. Nothing here
writes to the developer's machine, and `EDIFY_HOME` is redirected so a licence test
can never disturb a real licence.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

PACKAGE_JSON = """\
{
  "name": "demo",
  "scripts": {"build": "tsc", "test": "vitest run", "lint": "eslint ."},
  "dependencies": {"express": "4.19.2", "pg": "8.11.5"},
  "devDependencies": {"vitest": "1.6.0", "typescript": "5.4.5"}
}
"""

TSCONFIG = '{"compilerOptions": {"strict": true, "target": "ES2022"}}\n'

TOKENS_TS = """\
import crypto from "node:crypto";

export function generate(length: number): string {
  return crypto.randomBytes(length).toString("base64url").slice(0, length);
}

export function isWellFormed(token: string): boolean {
  return token.length === 32;
}
"""

MEMBERS_TS = """\
import { generate } from "../auth/tokens";

export class MemberService {
  add(email: string) {
    return { email, token: generate(32) };
  }
}

export const ROLES = ["admin", "member"];
"""

ROUTER_TS = """\
import express from "express";
import { MemberService } from "./members";

const app = express();
app.get("/members", (_req, res) => res.json([]));
app.post("/members", (_req, res) => res.status(201).json(new MemberService().add("a@b.c")));
export default app;
"""

MIGRATION_SQL = """\
create table members (
  id uuid primary key default gen_random_uuid(),
  email citext not null,
  created_at timestamptz not null default now()
);
create unique index members_email_idx on members (email);
"""

TOOLS_PY = '''\
"""A python module, so the exact backend has something to parse."""

MAX_RETRIES = 3


class Retrier:
    def __init__(self, limit: int = MAX_RETRIES) -> None:
        self.limit = limit

    def run(self, fn):
        return fn()


def with_retry(fn, limit: int = MAX_RETRIES):
    return Retrier(limit).run(fn)
'''


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository with TypeScript, Python, SQL, routes, and a real import chain."""
    root = tmp_path / "demo"
    (root / "src" / "auth").mkdir(parents=True)
    (root / "src" / "api").mkdir(parents=True)
    (root / "migrations").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)

    (root / "package.json").write_text(PACKAGE_JSON, encoding="utf-8")
    (root / "tsconfig.json").write_text(TSCONFIG, encoding="utf-8")
    (root / "src" / "auth" / "tokens.ts").write_text(TOKENS_TS, encoding="utf-8")
    (root / "src" / "api" / "members.ts").write_text(MEMBERS_TS, encoding="utf-8")
    (root / "src" / "api" / "router.ts").write_text(ROUTER_TS, encoding="utf-8")
    (root / "migrations" / "0027_members.up.sql").write_text(MIGRATION_SQL, encoding="utf-8")
    (root / "src" / "tools.py").write_text(TOOLS_PY, encoding="utf-8")
    return root


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the licence directory. No test may read or write a real licence."""
    home = tmp_path / "edify-home"
    monkeypatch.setenv("EDIFY_HOME", str(home))
    for name in (
        "EDIFY_LICENSE",
        "EDIFY_LICENSE_FILE",
        "EDIFY_LICENSE_PUBKEY",
        "EDIFY_REPO",
        # Whatever the developer's shell says about prompting and feedback, the
        # suite decides for itself — otherwise these tests pass or fail by shell.
        "EDIFY_ASSUME_YES",
        "EDIFY_NO_PROMPT",
        "EDIFY_NO_FEEDBACK",
        "EDIFY_NO_ANIM",
        "EDIFY_BUY_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    return home


@pytest.fixture
def installed(repo: Path) -> Path:
    """A repository with `edify init` already run over it."""
    from edify.cli import main

    assert main(["--repo", str(repo), "--quiet", "init"]) == 0
    return repo
