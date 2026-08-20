# {{repo}}
Stack: {{stack}}  ·  Tests: {{test}}

## Commands
/spec   — write the spec before anything else
/plan   — technology decisions and milestones, for work that needs them
/tasks  — turn an approved spec into the phased build plan
/build  — execute an approved plan, start to finish
/verify — re-run everything and produce the evidence

## The codebase map
.edify/graph/ — every symbol, route, and table, with the edges between them.
  edify graph where <name>        → file:line and signature
  edify graph dependents <symbol> → everything that breaks if it changes
Search the graph before reading files. Never guess a path.

## Where things live
Features: specs/<feature>/   Skills: .edify/skills/   Servers: .edify/mcp.md
