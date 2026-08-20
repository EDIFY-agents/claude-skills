# The `spec.md` format

What is being built and why. One file per feature, read by a human in ten minutes.
The worked instance is `spec.example.md`; this document is the contract.

---

## Frontmatter

Flat, scalars only, five keys.

```yaml
---
feature: team-invitations
status: draft            # draft | approved | amended
date: 2026-08-06
supersedes: —            # a spec this one replaces, or —
brief-source: —          # a file or ticket the brief came from, or —
---
```

## The sections, in order

```
# spec — <feature>
## Brief                the ask, verbatim, never edited
## Intent               numbered clauses, one per distinct thing this must accomplish
## Constraints          what is GIVEN: versions, platforms, real commands, hard limits
## Requirements         a table: id · requirement · the assertions that prove it
## Assertions           a table: id · statement · verification kind · citation
## What this entails    the closure checklist — what this implies that nobody asked for
## Open questions       every ambiguity, its readings, the one adopted, who resolves it
## Non-goals            what this explicitly does not do
```

## `## Brief`

The person's words, unedited. Three lines is normal. It is the only uncontaminated
statement of intent in the system, and both the adversary and the final review
check the result against it rather than against the draft that grew out of it.

## `## Intent`

Numbered clauses. Stable numbering — clauses are appended or struck, never
renumbered. Every requirement traces to a clause; a clause with no requirement
serving it is an incomplete spec.

## `## Constraints`

What is **given**, not chosen: the languages and versions already in use, the
target platforms and their floors, the package manager and test runner already
installed, the real build/test/lint/run commands, and the requirements that are not
up for negotiation.

Which library to use, at which version, over which alternative, is a *decision* and
belongs in `plan.md`. Mixing the two makes a decision look like a law of nature.

## `## Requirements`

| id | requirement | assertions |
|---|---|---|
| REQ-1 | An admin can invite someone by email | A-1, A-2, A-3 |

A requirement with no assertion is a wish. `edify check` reports it.

## `## Assertions`

| id | assertion | verification | citation |
|---|---|---|---|
| A-1 | An invitation token is 32 characters of base32 | property | src/auth/tokens.ts:14-38 |
| A-2 | Accepting an expired invitation returns 410 | example | new |

**verification** is one of `types` `example` `contract` `property` `model` `proof`
`observation`, cheapest to strongest. Pick the strongest kind that is *cheap* for
this assertion, not the strongest available. A pure function or data transformation
defaults to `property`. Anything expressible in the type system gets `types` in
addition to whatever else it gets — types are free and additive. Anything at
`model` or `proof` must be budgeted in `plan.md`, because an unbudgeted model check
silently becomes an example test during the build and nobody notices.

**citation** is `file:line`, `file:line-line`, or the literal `new`. Never a bare
filename.

Phase 2 of the build turns every row here into a failing executable test before any
code exists. An assertion that cannot become a failing test was never an assertion,
and the cheapest moment to discover that is while writing this table.

## `## What this entails`

| id | what it entails | status |
|---|---|---|
| CL-1 | The feature is behind a flag | REQ-4 |
| CL-2 | Invitation emails are rate-limited | open — adversary-found |
| CL-3 | Personal data has a retention rule | waived — the only datum is an email the admin already holds |

Everything the feature implies that nobody asked for: the permission declared and
requested, the migration and its rollback, the error and empty and loading states,
the authorization check on the new endpoint, the logs and the alert threshold, the
translation keys, the retention rule. Each row is satisfied by a requirement,
deliberately waived with a reason, or open — and an open row is what the human gate
is for.

## `## Open questions`

| # | question | readings | adopted | who resolves |
|---|---|---|---|---|

The human either resolves these or accepts the defaults on the record. An
unresolved question with real consequences blocks the gate; everything else becomes
a stated assumption and resurfaces in the final review as "we assumed X."

## What `edify check` reports

A missing required section. A requirement with no assertion. An assertion with no
verification kind, or one not on the ladder. A citation that is a bare filename. An
assertion serving no requirement. An open checklist row.
