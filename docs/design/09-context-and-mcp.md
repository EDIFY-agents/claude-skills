# 09 — Context Outside the Repository: MCP

**The failure it prevents:** the invented interface. The model calls a method that was
removed two versions ago, passes an argument the library never had, or writes against
an API shape it remembers from training. `file:line` citations cannot catch this class,
because the thing being cited is not in the repository — and it is the single largest
remaining source of confidently wrong code once the graph has solved everything inside
the repository.

**The design goal:** the model can reach current, version-correct information about
things outside this codebase — and pays for that reach only when it uses it.

---

## 1. The two halves of context, and why the second one needs a protocol

The graph solves context *inside* the repository. Everything a session needs to know
about this codebase is derivable, mechanical, and free after extraction.

Nothing about the world outside it is. The exact API of the version of the library in
`package.json`, the ticket that explains why this endpoint exists, the schema of the
staging database, what the page actually renders — none of that is in the repository
and none of it is reliably in the model's weights, because weights are a snapshot and
libraries move weekly.

**MCP is the interface for that second half**, and treating it as first-class is not
optional: a harness that solves in-repository context perfectly and leaves external
context to recollection has fixed the cheaper of the two problems.

## 2. The cost that makes this a design problem

Every connected server injects its tool descriptions into every session's context. That
cost is paid whether or not the tools are used, on every launch, for the whole run.
Connect eight servers and a forty-task build pays for eight tool catalogs eighty times.

There is a second cost that is not measured in tokens. A third-party server is a supply
chain — code we did not write, fetched from somewhere, running with whatever access it
was granted — and its *output* is untrusted text arriving mid-session, which is the
textbook prompt-injection surface.

So MCP is designed here the way skills are designed: **a small curated registry, pulled
per role, never pushed globally.**

## 3. The design

**A registry, not a connection list.** One file declares every server the repository
may use: what it is, its pinned version, what it is for, and — the load-bearing field —
**which roles and phases may load it**. `/spec` gets the documentation server, because
resolving a library's real API is exactly its job. A phase 4 implementer working on a
React surface gets the documentation server for its stack. A phase 0 build task gets
nothing. Nobody gets everything.

**Pull, not push.** This is the same law that governs the spawn payload. Context that
might be useful costs tokens on every launch; context fetched when needed costs nothing
until then. A server that cannot be scoped to a role is a server that taxes the whole
run, and that is the bar it has to clear.

**The default set is small and specific.** One documentation server that serves
version-correct API documentation for the libraries the plan names, plus whatever the
repository's own systems require. No marketplace browsing, no catalog of interesting
possibilities. Every addition has to name the failure it prevents, and a server that
does not visibly earn its cost is removed.

**Server output is untrusted input.** Marked with its origin and version. Never written
into the graph — the graph's entire value is that nothing narrated enters it. Never
written into a spec or plan as a fact without the version it came from. Output
containing instruction-like content is flagged rather than followed, which is the
standard defense and the reason the registry is curated rather than open.

**Offline degrades honestly.** On a network with no outbound access, servers that need
one are simply absent, and the session says so. The alternative — silently falling back
to recollection — produces exactly the invented interface this exists to prevent, with
no signal that it happened.

## 4. Where it connects to the rest of the system

The link that makes this more than a configuration file: **`plan.md` names the libraries
and their exact versions; the documentation server is what makes those versions real at
build time.**

A plan that says "HTTP client: the standard one, version 5.2, chosen over the two
alternatives for its streaming support" is a decision. Without a way to consult version
5.2's actual API, a builder writes against whatever it remembers, which may be version
3. With it, the builder asks and gets the current shape. The plan and the registry are
two halves of one mechanism, and neither is worth much alone.

The second connection is the reverse direction: **integrating with a new tool is a plan
decision, not an improvisation.** When a feature needs to reach a new external
system — a ticket tracker, a database, a browser, a design tool — that is a row in the
plan's technology decisions with its alternative named, and a row in the registry with
its scope declared. It is not a server somebody connected on a Tuesday that everyone now
pays for.

## 5. What this deliberately is not

- **Not a marketplace.** The registry is a short curated list, and additions are
  reviewed the same way library skills are.
- **Not "connect everything and let the model decide".** That is the design that makes
  every session slower and every tool catalog a permanent tax.
- **Not a channel into the graph.** No external content becomes a node or an edge, at
  any point, for any reason.
- **Not a hard requirement.** Everything in EDIFY works with the registry empty. The
  documentation server is the one entry that pays for itself in most repositories, and
  even it is a recommendation rather than a dependency.
