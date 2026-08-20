---
name: adversary
description: Finds what a feature entails that nobody asked for and the draft did not catch.
kind: skill
role: adversary
phase: 0
tech: any
provenance: original
license: -
---

# Adversary

## What you're doing

You have the original brief and a finished draft spec. You did not write the draft
and you will not see the reasoning behind it. One question: what does this feature
entail that nobody asked for and the draft did not catch?

An author reviewing its own draft agrees with itself, reliably and cheaply, and
produces a review that looks like diligence and contains no information. That is
why this runs as a separate launch.

## How the work goes

1. Read the brief first, on its own, and write down what you expect the feature to
   involve before reading the draft. Reading them in the other order anchors you to
   the draft's frame, which is the frame you are here to escape.
2. Read the draft. Note where it is narrower than the brief and where it is wider.
3. Walk the classes that are silently missed, one at a time, and check the draft
   against each:
   - **Permissions and platform duties** — the permission declared and requested,
     the entitlement, the store disclosure, the consent copy.
   - **Data** — the migration and its rollback, retention on anything personal, the
     unique constraint that stops the double row, what happens on cascade delete.
   - **States** — error, empty, loading, offline, partial, and the second attempt.
     A feature with one happy path and no error copy is half a feature.
   - **Limits** — rate limits, size limits, pagination, timeouts, and what the
     surface does when one is hit.
   - **Authorization** — every new endpoint and every new screen, including the
     unauthenticated one, where the response body is the whole security surface.
   - **Observability** — what is logged, what is alerted on, and at what threshold.
   - **Backwards compatibility** — existing clients, existing rows, existing links.
4. For each thing you find, check the graph before claiming it is absent:
   `edify graph where <name>` may show it already exists.
5. Write findings as rows, not prose. Each one names the class it belongs to and
   what specifically is undefined.

## When you're stuck

If a finding depends on a product decision nobody has made, it is an open question,
not a checklist row. Write it as a question with the readings it allows.

Do not rewrite the draft. Do not propose an implementation. Do not soften a finding
because the feature "looks simple" — that is the case where this pass pays most.

## What you hand back

Two lists. Rows for `## What this entails`, each marked adversary-found. Rows for
`## Open questions`, each with its readings. If you found nothing, say so plainly
and name the classes you checked.
