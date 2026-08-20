# Security Policy

## Reporting a vulnerability

**Do not open a public issue.**

Use GitHub's [private vulnerability
reporting](https://github.com/edify-dev/edify/security/advisories/new), or email **security@edify.dev**.

Include what you would want to receive: the version (`edify self where`), the
platform, a reproduction, and what an attacker gets out of it.

| | target |
|---|---|
| acknowledgement | 48 hours |
| initial assessment | 5 working days |
| fix or documented mitigation | 30 days for high severity |
| public advisory | after a fix ships, crediting you unless you prefer otherwise |

We do not run a paid bounty. We do credit reporters in the advisory and the
changelog.

## Supported versions

The latest minor release. EDIFY is pre-1.0; there is no long-term support
branch yet, and pretending otherwise would be the kind of claim this project
tries not to make.

## What is in scope

- Arbitrary code execution from a crafted repository, graph file, spec, plan,
  task list, or skill entry.
- Path traversal in anything that writes into a repository — `init`, `setup`,
  `init new`, `upgrade`, `skills add`.
- Signature forgery or verification bypass in `edify license activate`
  (`src/edify/licensing/ed25519.py`, `token.py`).
- Any network call from a command other than `edify upgrade` and
  `edify self update`. **This one is a security bug by definition.** See
  [docs/privacy.md](docs/privacy.md).
- Secrets leaking into `.edify/`, the graph, or any file EDIFY writes.
- Tampering with `.edify/governance.tsv` such that `governance verify` reports
  clean on a file that changed.

## What is out of scope

- **Removing the licence check.** The source is readable, the verification is
  local, and anyone determined can delete it. That is stated plainly in
  [docs/pricing.md](docs/pricing.md) rather than hidden: paying is a contract,
  not a technical protection measure. Reports that the gate can be bypassed
  describe the design. Reports that a *signature check* accepts a forged token
  are in scope and serious.
- Findings that require an attacker who already has write access to the
  repository or the developer's machine.
- Output of a language model invoked by your own agent runtime. EDIFY does not
  host, wrap, or route to a model.
- Social engineering, physical access, and denial of service against a local
  CLI.

## Design properties you can verify yourself

These are not promises; they are checkable in an afternoon:

- No runtime dependencies — `pyproject.toml`, `[project] dependencies = []`.
  Nothing in the supply chain to compromise but Python itself.
- No telemetry, anywhere, in any form — see [docs/privacy.md](docs/privacy.md).
- Exactly two commands open a socket, both of them by explicit user action.
- Every file EDIFY installs is hashed and recorded in `.edify/governance.tsv`;
  `edify governance verify` tells you what changed since.
