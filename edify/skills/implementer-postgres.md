---
name: implementer-postgres
description: Implements a schema, migration, or query task against a relational database.
kind: skill
role: implementer
phase: 1 3 5 6
tech: postgres mysql prisma drizzle typeorm sqlalchemy
provenance: original
license: -
---

# Implementer — schema and migrations

## What you're doing

A phase-1 contract task, usually: a table, a migration, and the type that mirrors
it. Everything phase 1 produces is frozen when phase 1 ends, so this is the work
three later phases are built against.

## How the work goes

1. Read the task block, then open the most recent migration in this repository and
   copy its conventions exactly: id column and its default, timestamp columns and
   their type, foreign keys and their delete behaviour, where indexes are declared.
2. The migration number comes from `plan.md`'s cross-cutting section. It was
   allocated once, on purpose, so two tasks never claim the same one. Do not pick
   your own.
3. Write the down migration in the same commit. A migration with no rollback is a
   deployment you cannot reverse, and the closure checklist has a row for it.
4. Put the constraint in the database, not only in the application. The unique
   partial index that stops the second pending row is the thing that actually holds
   under a race; the service-layer check is what makes the error message nice.
5. Mirror the table into the type or model file the codebase keeps for it, and add
   it to whatever union or registry the neighbouring types are in.
6. Run the migration up and then down against a test database before saying it
   works. `edify graph where <table>` afterwards confirms it is on the map.

## The traps specific to this stack

- Adding a `NOT NULL` column with no default rewrites the table and locks it. On a
  large table, add nullable, backfill, then constrain — in separate migrations.
- An index created without `CONCURRENTLY` on a live table blocks writes for its
  duration.
- `ON DELETE CASCADE` is a data-retention decision wearing a schema costume. Say
  which one the spec asked for.
- A timestamp without a time zone will be read as three different instants by three
  services.
- A uniqueness rule that has to ignore soft-deleted rows is a partial index, not a
  plain one.

## When you're stuck

- **The task is wrong** — the referenced table does not exist, the migration number
  is taken. Write `BLOCKED T-n: <what you found>` and stop.
- **The task is silent on something real** — copy the most recent migration's
  answer, add one row to `## Decisions`, and continue.

Never edit a migration that has already been applied anywhere. Write a new one.

## What you hand back

The task id, the files you changed, the up-and-down migration output verbatim, and
`done`, `blocked: <reason>`, or `decided: <the row>`.
