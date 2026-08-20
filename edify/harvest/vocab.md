# Controlled vocabulary

Three short lists. Every consumer of the skill index breaks silently if an id
appears that no consumer knows, so extending any of these is a reviewed change.

## `role`

| id | when it runs |
|---|---|
| `planner` | `/spec`, `/plan`, `/tasks` |
| `adversary` | `/spec`, after the draft — never the drafting session |
| `test` | phase 2, one task per assertion group |
| `implementer` | every build task from phase 3 on, plus phases 0 and 1 |
| `debugger` | after a task fails its done-check twice |
| `verifier` | phase 7 and `/verify` — never a session that wrote code |

## `phase`

`0` foundation · `1` contracts · `2` verification · `3` core · `4` surfaces ·
`5` integration · `6` hardening · `7` proof

Space-separated on one line. A skill that serves several phases lists them all.

## `tech`

The stack and domain ids a repository's detected stack is matched against. `any`
means the entry applies regardless of stack.

**Languages** — `python` `typescript` `javascript` `go` `rust` `java` `kotlin`
`csharp` `ruby` `php` `swift` `scala` `dart` `elixir` `c` `cpp` `sql` `shell`
`lua`

**Front end** — `react` `nextjs` `vue` `svelte` `angular`

**Back end** — `express` `fastify` `nestjs` `django` `flask` `fastapi` `rails`
`laravel` `symfony` `spring` `gin` `echo` `actix` `axum`

**Data** — `postgres` `mysql` `mongodb` `redis` `prisma` `drizzle` `typeorm`
`sqlalchemy`

**Test** — `jest` `vitest` `mocha` `pytest` `rspec` `junit` `phpunit` `playwright`
`cypress`

**Other** — `aws` `terraform` `docker` `kubernetes` `celery` `tokio` `pydantic`
`api-design` `any`

## Adding an id

Two questions, and both have to be yes. Does something detect it — is there a
manifest entry, a lockfile, or an extension that puts it in `.edify/stack.tsv`? And
does at least one skill entry use it? An id that nothing detects never matches, and
an id no entry uses is a word in a file.
