# 07 — The MCP Registry

How the system reaches things that are not in the repository — current library
documentation above all — without taxing every session for the privilege. Rationale is
in `../09-context-and-mcp.md`; this is the shape.

---

## 1. The file

`.edify/mcp.md` — one table, flat, human-readable, committed.

```markdown
| server | version | provides | roles | phases | network | source |
|---|---|---|---|---|---|---|
| docs | 1.4.2 | version-correct API docs for installed packages | planner implementer debugger | 1 2 3 4 5 6 | outbound | <origin> |
| tickets | 0.9.0 | issue and PR context by id | planner | — | internal | <origin> |
| db-staging | 2.1.0 | read-only schema and sample rows | planner implementer | 1 3 | internal | <origin> |
| browser | 3.0.1 | drives a real browser, captures console and screenshots | verifier | 7 | local | <origin> |
```

Seven columns, and the two that carry the design are `roles` and `phases`.

| column | meaning |
|---|---|
| `server` | stable id, referenced nowhere else by any other name |
| `version` | **exact**, pinned; `edify doctor` probes that the running server matches |
| `provides` | one line — what question this answers that nothing local can |
| `roles` | which roles may load it (`08-...` §5 role list), or `—` for none by default |
| `phases` | which build phases may load it, or `—` |
| `network` | `outbound` \| `internal` \| `local` — what it needs to reach |
| `source` | where the server came from, for the same provenance reason skills carry one |

## 2. Scoping is the whole mechanism

A connected server injects its tool descriptions into every session's context, used or
not. Eight servers across a forty-task build is that tax paid three hundred and twenty
times.

So a server is **loaded per spawn**, from the intersection of its `roles` and `phases`
with the task about to run:

```
spawn(task) →
    servers = mcp.where(role ∈ task.role AND phase ∈ task.phase)
    load(servers)   # usually zero or one
```

A phase 0 foundation task loads nothing. A phase 4 surface implementer loads the docs
server. The phase 7 verifier loads the browser. Nobody loads everything, and the common
case — zero or one server — is what keeps a spawn payload on one page (P6).

**A server that cannot be scoped is a server that taxes the whole run.** That is the
bar an addition has to clear, and it is a design question rather than a preference: if a
server is genuinely needed by every role in every phase, it should be, and the registry
should say so explicitly rather than by omission.

## 3. The default registry

**One entry: `docs`.** A documentation server that serves version-correct API
documentation for the packages actually installed.

It is the default because it closes the one hallucination class the graph cannot. The
graph makes every in-repository reference exact. Nothing makes an out-of-repository
reference exact, and the model's weights are a snapshot of a world where the library
was two major versions younger. That is where confidently wrong code comes from once
the in-repository problem is solved.

The link that makes it work: **`plan.md`'s technology-decision table names the library
and its exact version** (`03-plan-format.md` §4); the docs server resolves that version's
real API at the moment a builder needs it. Neither half is worth much alone — a pinned
version nobody can consult is a comment, and a docs server with no pinned version is a
guess about which docs to fetch.

Everything else is per-repository and added deliberately. There is no starter pack of
interesting possibilities.

## 4. Trust

Everything a server returns is **untrusted input**, and the rules are short:

- **Marked with origin and version** wherever it lands. A fact from `docs@1.4.2` is
  recorded as such, never laundered into a plain assertion.
- **Never written into the graph.** Not a node, not an edge, not once. The graph's whole
  value is that nothing narrated or fetched enters it (`06-graph.md` §3).
- **Never written into a spec or plan without its version.** A claim about a library's
  behavior that does not say which version is a claim with a shelf life and no label.
- **Instruction-like content is flagged, not followed.** Tool output that contains
  directives aimed at the agent is the textbook injection vector, and a curated registry
  is what keeps the surface small enough for that check to be meaningful.

## 5. Offline

Servers whose `network` is `outbound` are simply **absent** on a network without it, and
the session states that they are absent.

The failure this prevents is specific: a silent fallback to recollection produces
exactly the invented interface the docs server exists to stop, with no signal that it
happened. An absent server that says so makes a builder cite what it does not know; an
absent server that fails quietly makes it guess confidently.

`internal` and `local` servers are unaffected — a staging database or a browser on the
same machine needs no outbound access, which is why the column distinguishes them.

## 6. Commands

```
edify mcp list                    the registry, with what each is scoped to
edify mcp check                   each server responds and its version matches the pin
edify mcp for <role> <phase>      what a spawn in this position would load
```

`for` exists so the scoping is inspectable rather than implicit. "Why did this task have
the browser loaded?" should be one command, not an investigation.

## 7. What this is not

- **Not a marketplace.** Additions are reviewed like library skills. There is no
  browsing, no catalog, no discovery flow.
- **Not always-on.** The registry declares what *may* be loaded, never what *is*.
- **Not a channel into the graph.** Stated twice because it is the invariant most
  tempting to relax: a docs server that knows a package's exported symbols looks like a
  graph extender, and it is not one — it describes a package, not this codebase, and it
  describes it from outside our trust boundary.
- **Not required.** Everything works with the registry empty. The docs entry is a
  recommendation that pays for itself in most repositories, not a dependency.
