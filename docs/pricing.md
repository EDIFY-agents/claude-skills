# Pricing

**Free, forever, with no account.** Every command, every query, every check, the
whole methodology tree. Not a trial, and it does not expire.

---

## 1. The position

EDIFY has no server, no daemon, and no database, and everything works offline
except `edify upgrade`. That is not a limitation to route around when money
enters the picture — it is the product's most defensible property in exactly the
accounts this is for, where a build server has no outbound network and a
procurement process for anything that does.

So the commercial layer preserves it: **a signed licence token, verified locally,
with no phone-home and no activation server.**

## 2. What is free and what is $20

| | free | pro — **$20 per user per month** |
|---|---|---|
| `/spec` `/plan` `/tasks` `/build` `/verify` — the methodology | ✅ | ✅ |
| `edify init`, the conventions scrape, `CLAUDE.md` | ✅ | ✅ |
| every graph query — `where` `dependents` `defines` `overlap` `references` | ✅ | ✅ |
| `edify check`, `--fix`, `--exit-code`, `--json` | ✅ | ✅ |
| `edify skills`, `edify mcp`, `edify doctor`, `edify governance` | ✅ | ✅ |
| the twelve shipped skill entries | ✅ | ✅ |
| **graph size** | 25,000 nodes | unlimited |
| **`edify upgrade`** — new curated library entries | — | ✅ |
| **registry entries** | 1 server | unlimited |
| **projects installed on one machine** | 3 | unlimited |
| **seats on one licence** | 1 | team plan |

Five gates, and they are the only five. They live in one readable file,
[`src/edify/licensing/tier.py`](../src/edify/licensing/tier.py), as
`graph.unlimited`, `library.upgrade`, `mcp.multi`, `projects.unlimited`, and
`team`.

### Why these five

Each is a place where the paying customer's need diverges from the free user's,
rather than a place where a working feature was removed to create a reason to
pay:

- **25,000 nodes** is roughly a 200–300k-line repository. Below that, a frontier
  model in auto mode is already good and EDIFY is genuinely optional — the free
  plan should be complete there, and it is. Above it is precisely the population
  the product exists for.
- **`upgrade`** is the only command that touches the network, and the curated
  library is the only asset with an ongoing cost: gathering, screening,
  rewriting, and a human reading every entry. Charging for the thing with a
  marginal cost is honest; charging for a local file read is not.
- **One server** covers the default registry exactly — the `docs` entry, which is
  the one that closes the invented-interface failure. A second server means a
  team with internal systems, which means a company.
- **Three projects** is the line between a person trying EDIFY and a person whose
  work runs on it. One repository is an evaluation; two is a side project; the
  fourth is a working week.
- **Seats** is the ordinary team boundary and needs no defence.

## 3. How the licence works

```bash
edify license status                   # what this machine is entitled to
edify license projects                 # which repositories are using a slot
edify license projects forget PATH     # release one
edify license buy --seats 3            # opens a browser, not a socket
edify license activate <token>         # the token you were emailed
```

The token is Ed25519-signed and verified locally against a public key compiled
into the binary. **There is no activation server and no phone-home.** An
air-gapped machine activates exactly like a connected one.

The project count is a readable file on your machine — `projects.tsv` beside the
licence — and nothing about it is ever sent anywhere. A project is keyed on its
git remote, so a re-clone, a second worktree, and a fresh CI checkout are one
project rather than three; a repository you delete returns its slot on its own.
**Only a new project is ever refused** — anything already installed keeps
installing, forever, and every non-install command ignores the ledger entirely.

The price appears at a gate and in `edify license status`. Nowhere else: there is
no periodic reminder, and that was decided rather than overlooked.

## 4. The commitments

These are the load-bearing promises, stated so you can hold us to them:

1. **No telemetry.** Not anonymous, not aggregate, not opt-out. See
   [privacy.md](privacy.md).
2. **The project ledger never leaves your machine.** It is a plain TSV you can
   read and edit.
3. **No periodic nag.** The price appears at a gate and in `license status`.
4. **The free tier is a whole system, not a trial.** It does not expire, and it
   does not require an account.
5. **Every version converts to Apache 2.0 after two years.** Irrevocably — see
   [GOVERNANCE.md](../GOVERNANCE.md).

## 5. The honest part

The source is readable, the check is local, and anyone determined can remove it.

**Paying is a contract, not a technical protection measure.** We would rather say
that than break offline operation pretending otherwise. A licence server is
bypassed by a hosts file, and obfuscation in a readable Python package is
theatre. EDIFY does not claim enforcement it does not have — that rule is
[principle P7](design/01-principles.md), and this is the same rule applied to
revenue.

What stops a *company* reselling EDIFY is not the gate. It is
[the licence](../LICENSE) and [the trademark](../TRADEMARK.md), which are
enforceable in the place such things are actually enforced.
