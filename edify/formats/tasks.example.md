---
feature: team-invitations
spec: spec.md
plan: —
status: approved
phases: 8
tasks: 16
date: 2026-08-06
---

# tasks — team invitations

> **This file is the worked example for `04-tasks-format.md`.** It is a complete plan
> for a real-shaped feature in a TypeScript / Postgres / React codebase: an admin
> invites someone by email, the invitee opens a link and joins the workspace. Read it
> for calibration — how much precision is enough, what a good pattern pointer looks
> like, how steps are written so a cheap model never has to choose. Do not fill it in
> as a template; a plan is derived from a spec and a graph, never from a shape.
>
> This feature has **no `plan.md`**, and that is the normal case: it introduces no new
> technology, spans one milestone, and needs no cross-cutting strategy
> (`03-plan-format.md` §1). `../plan-ex.md` is the example for work that does.

## Phases

| # | phase | tasks | parallel-safe | exit check |
|---|---|---|---|---|
| 0 | Foundation | T-1 | — | `npm run build` |
| 1 | Contracts — **frozen at phase end** | T-2, T-3 | — | `npm run migrate:test && npm run typecheck` |
| 2 | **Verification** — assertions as failing tests | T-4, T-5 | T-4 ∥ T-5 | `npm test -- invitations` reports **17 failing, 0 passing** |
| 3 | Core | T-6, T-7 | T-6 ∥ T-7 | `npm test -- invitations/service` |
| 4 | Surfaces | T-8, T-9, T-10, T-11 | T-8 ∥ T-9 ∥ T-10 ∥ T-11 | `npm test -- invitations && npm run typecheck` |
| 5 | Integration | T-12, T-13 | — | `npm run test:e2e -- invitations` |
| 6 | Hardening | T-14, T-15 | T-14 ∥ T-15 | `npm test -- invitations` |
| 7 | Proof | T-16 | — | see T-16 |

Phase 4's four tasks are parallel-safe because their file sets and the dependents of
those files are disjoint — computed with `edify graph overlap`, not asserted. Phase 1
and phase 5 are serial by nature: one migration and one wiring pass each need the whole
picture.

**Read phase 2's exit check carefully: it asserts failure.** After phase 2 this feature
has seventeen red tests and no implementation, which is the correct state of a codebase
that has decided what finished means and is not finished. Every phase after it is
measured by how much of that red turns green — a count anyone can watch, rather than a
series of claims about progress.

---

## Phase 0 · Foundation

### T-1 · Add the invitation config block and feature flag

Phase 0 · Role build · Skill implementer-node · Size xs
Discharges CL-1
Depends on — · Parallel with —

Files

| path | range | action |
|---|---|---|
| src/config/index.ts | 44-71 | edit |
| src/config/index.test.ts | 30-58 | edit |
| .env.example | 12-18 | edit |

Follow the pattern at
- `src/config/index.ts:22-43` — the `sessions` block: same `z.object` shape, same
  `parseEnv` call, same default-plus-override style. Copy it exactly.
- `src/config/index.test.ts:12-29` — the test for that block, including how missing
  env vars are asserted.

Steps
1. In `src/config/index.ts`, after the `sessions` block ending at line 43, add an
   `invitations` block with three keys: `ttlHours` (number, default `72`),
   `maxPerHour` (number, default `20`), `enabled` (boolean, default `false`).
2. Register the three env vars in the same `parseEnv` call the `sessions` block uses:
   `INVITE_TTL_HOURS`, `INVITE_MAX_PER_HOUR`, `INVITE_ENABLED`.
3. Add the three names to `.env.example` under the existing `# features` comment at
   line 12, each with its default as the value.
4. In `src/config/index.test.ts`, add a case mirroring the one at lines 12-29 that
   asserts the defaults apply when the env vars are absent.

Done when
- `npm test -- config` passes
- `npm run build` succeeds
- `grep INVITE_ .env.example` returns three lines

---

## Phase 1 · Contracts — frozen at phase end

Everything this phase produces is fixed when it ends. A later task that needs one of
these shapes changed stops and becomes a `/tasks` amendment.

### T-2 · Create the invitations table and its migration

Phase 1 · Role data · Skill implementer-postgres · Size s
Discharges REQ-1, REQ-3, CL-4
Depends on — · Parallel with —

Files

| path | range | action |
|---|---|---|
| migrations/0031_invitations.up.sql | — | new |
| migrations/0031_invitations.down.sql | — | new |
| src/db/schema.ts | 118-146 | edit |

Follow the pattern at
- `migrations/0027_members.up.sql:1-24` — the same table conventions: `id uuid primary
  key default gen_random_uuid()`, `created_at timestamptz not null default now()`,
  `workspace_id` with `on delete cascade`, and the trailing index block.
- `migrations/0027_members.down.sql:1-3` — the down migration is always a bare
  `drop table if exists ... cascade;`.
- `src/db/schema.ts:92-117` — the `members` table type, exported and added to the
  `Tables` union at line 146.

Steps
1. Write `migrations/0031_invitations.up.sql` creating table `invitations` with
   columns: `id`, `workspace_id uuid not null references workspaces(id) on delete
   cascade`, `email citext not null`, `role text not null check (role in
   ('admin','member'))`, `token char(32) not null unique`, `invited_by uuid not null
   references users(id)`, `expires_at timestamptz not null`, `accepted_at timestamptz`,
   `revoked_at timestamptz`, `created_at`.
2. Add two indexes in the same trailing block style as `0027`: a unique partial index
   on `(workspace_id, email)` where `accepted_at is null and revoked_at is null`, and
   a plain index on `token`.
3. Write the matching down migration.
4. In `src/db/schema.ts`, add the `Invitation` type after the `Member` type at line
   117, and add `invitations` to the `Tables` union at line 146.

Done when
- `npm run migrate:test` applies and rolls back cleanly
- `npm run typecheck` passes
- Inserting two pending invitations for the same `(workspace_id, email)` raises a
  unique violation; inserting one after the first is accepted does not

### T-3 · Freeze the invitations API contract

Phase 1 · Role api-design · Skill implementer-node · Size s
Discharges REQ-1, REQ-2, REQ-6
Depends on T-2 · Parallel with —

Files

| path | range | action |
|---|---|---|
| src/api/contracts/invitations.ts | — | new |
| src/api/contracts/index.ts | 8-14 | edit |
| docs/api/invitations.md | — | new |

Follow the pattern at
- `src/api/contracts/members.ts:1-58` — the whole file shape: one `z` schema per
  request and response, `export type X = z.infer<typeof xSchema>` beneath each, and
  the `Errors` const at the bottom listing every error code the endpoints can return.
- `docs/api/members.md:1-40` — the documentation shape, one section per endpoint.

Steps
1. Create `src/api/contracts/invitations.ts` with four request/response pairs:
   `CreateInvitation` (in: `email`, `role`; out: `id`, `email`, `role`, `expiresAt`),
   `GetInvitation` (in: `token`; out: `workspaceName`, `email`, `role`, `expiresAt`),
   `AcceptInvitation` (in: `token`; out: `workspaceId`, `membershipId`), and
   `ListInvitations` (out: an array of the `CreateInvitation` response shape).
2. Add an `Errors` const in the same style as `members.ts:48-58` with:
   `INVITE_NOT_FOUND`, `INVITE_EXPIRED`, `INVITE_ALREADY_ACCEPTED`, `INVITE_REVOKED`,
   `INVITE_RATE_LIMITED`, `INVITE_ALREADY_MEMBER`.
3. Re-export from `src/api/contracts/index.ts`, alphabetically, at line 8-14.
4. Write `docs/api/invitations.md` documenting the four endpoints, following the
   members shape.

Done when
- `npm run typecheck` passes
- `npm run lint` passes
- Every error code named in the spec's `## Error states` appears in the `Errors` const

---

## Phase 2 · Verification

Every assertion in the spec becomes an executable test that **fails**. These live in
`tests/assertions/` — separate from the co-located unit tests the implementation tasks
write, so the two never collide and so "how many spec assertions are satisfied" stays a
number anyone can read off one command.

### T-4 · Assertions A-1..A-11 as failing tests — invitation lifecycle

Phase 2 · Role test · Skill test-writer-node · Size m
Discharges A-1, A-2, A-3, A-4, A-5, A-6, A-7, A-8, A-9, A-10, A-11
Verification example (A-1..A-6, A-8..A-11), property (A-7)
Depends on T-3 · Parallel with T-5

Files

| path | range | action |
|---|---|---|
| tests/assertions/invitations.lifecycle.test.ts | — | new |
| tests/assertions/invitations.token.property.test.ts | — | new |

Follow the pattern at
- `tests/assertions/members.lifecycle.test.ts:1-52` — the assertion-test shape: one
  `describe` per REQ, one `it` per assertion, and the assertion id in the test name so a
  failure output names what is unsatisfied. Copy this exactly.
- `tests/assertions/helpers.ts:1-40` — `makeWorkspace()`, `makeUser()`, and the
  `truncate` in `afterEach`.
- `tests/assertions/auth.token.property.test.ts:1-30` — the property-test shape for
  A-7, including the generator and the shrink configuration.

Steps
1. Create `tests/assertions/invitations.lifecycle.test.ts` with one `describe` per
   requirement REQ-1, REQ-3, REQ-4, REQ-6 and one `it` per assertion, named
   `A-N: <the assertion text from the spec, verbatim>`.
2. Write each test against the contract frozen in T-3 — import the request and response
   types, never redeclare a shape.
3. For A-7 ("no two invitations in a workspace share a token"), write a property test in
   `invitations.token.property.test.ts`: generate 1,000 tokens, assert distinctness, and
   assert the base32 alphabet and 32-character length hold for every generated value.
   The spec marks A-7 `property` because it is a rule over all inputs, not a case.
4. Do not stub the implementation to make anything pass. The imports resolve to modules
   that do not exist yet; that is the expected failure mode at this phase.

Done when
- `npm test -- tests/assertions/invitations` runs and reports **11 failing, 0 passing**
- Every failure message contains the assertion id it covers
- `npm run typecheck` still passes — the tests compile against the frozen contract

### T-5 · Assertions A-12..A-17 as failing tests — surfaces and error states

Phase 2 · Role test · Skill test-writer-node · Size m
Discharges A-12, A-13, A-14, A-15, A-16, A-17
Verification example (A-12..A-16), observation (A-17)
Depends on T-3 · Parallel with T-4

Files

| path | range | action |
|---|---|---|
| tests/assertions/invitations.api.test.ts | — | new |
| tests/assertions/invitations.ui.test.tsx | — | new |

Follow the pattern at
- `tests/assertions/members.api.test.ts:1-60` — the request-test shape, including
  `authedAs(admin)` from `test/helpers/auth.ts:18` and how a `403` is asserted.
- `tests/assertions/password-reset.ui.test.tsx:1-70` — the MSW handler setup, one
  handler per error state.

Steps
1. Write `invitations.api.test.ts` covering A-12 (an admin can create), A-13 (a
   non-admin gets 403), A-14 (the unauthenticated preview returns exactly four fields),
   and A-15 (accepting twice creates one membership).
2. For A-14, assert the **exact key set** of the response, not a subset — the endpoint
   is unauthenticated, so its response body is the whole security surface and a subset
   assertion would not catch a leak.
3. Write `invitations.ui.test.tsx` covering A-16: each of the four error codes renders
   its own distinct message, asserted by text.
4. A-17 (the accept page is keyboard-navigable and screen-reader-labelled) is marked
   `observation` in the spec — write no test for it here. It is discharged in T-16 step
   3 with a captured recording. Add a skipped placeholder named `A-17: see T-16` so the
   assertion count stays honest.

Done when
- `npm test -- tests/assertions/invitations` now reports **17 failing, 1 skipped,
  0 passing** across T-4's and T-5's files
- The skipped test names T-16 as its discharge

---

## Phase 3 · Core

### T-6 · Implement token generation and validation

Phase 3 · Role domain · Skill implementer-node · Size s
Discharges REQ-2, CL-2
Depends on T-3 · Parallel with T-7

Files

| path | range | action |
|---|---|---|
| src/invitations/token.ts | — | new |
| src/invitations/token.test.ts | — | new |

Follow the pattern at
- `src/auth/tokens.ts:14-38` — `generate()` already produces 32-character base32 from
  `crypto.randomBytes`; call it rather than writing a second generator. Its collision
  test at `src/auth/tokens.test.ts:8-22` is the test to copy.

Steps
1. Create `src/invitations/token.ts` exporting `newInviteToken()` that delegates to
   `generate(32)` from `src/auth/tokens.ts:14`.
2. Export `isWellFormed(token: string): boolean` — exactly 32 chars, base32 alphabet
   only. This is a shape check, not an existence check; existence is the service's job.
3. Write `src/invitations/token.test.ts`: well-formed tokens pass, wrong length fails,
   non-base32 characters fail, and 10,000 generated tokens are all distinct.

Done when
- `npm test -- invitations/token` passes
- `edify graph references generate` shows this file among the callers — confirming no
  second generator was written

### T-7 · Implement the invitation service

Phase 3 · Role domain · Skill implementer-node · Size m
Discharges REQ-1, REQ-3, REQ-4, REQ-6
Depends on T-2, T-3 · Parallel with T-6

Files

| path | range | action |
|---|---|---|
| src/invitations/service.ts | — | new |
| src/invitations/service.test.ts | — | new |

Follow the pattern at
- `src/members/service.ts:1-140` — the whole service shape: a plain object of async
  functions taking `(db, ...args)` as the first parameter, no class, errors thrown as
  `AppError(Errors.X)` from `src/errors.ts:9`, and transactions via `withTx` from
  `src/db/tx.ts:11`.
- `src/members/service.test.ts:1-44` — the fixture setup: `makeWorkspace()`,
  `makeUser()`, and the `truncate` in `afterEach`.

Steps
1. Create `src/invitations/service.ts` exporting four functions:
   `create(db, {workspaceId, email, role, invitedBy})`, `getByToken(db, token)`,
   `accept(db, {token, userId})`, `revoke(db, {id, workspaceId})`.
2. `create` — reject with `INVITE_ALREADY_MEMBER` if the email already belongs to a
   member of that workspace (query the existing helper at
   `src/members/service.ts:62`), generate a token with `newInviteToken()`, set
   `expires_at` to `now() + config.invitations.ttlHours`, insert, and return the row.
3. `getByToken` — throw `INVITE_NOT_FOUND` when absent, `INVITE_EXPIRED` when
   `expires_at < now()`, `INVITE_ALREADY_ACCEPTED` when `accepted_at` is set,
   `INVITE_REVOKED` when `revoked_at` is set. Check in that order — an expired,
   already-accepted invite reports as accepted, which is the message the spec's
   `## Error states` asks for.
4. `accept` — inside `withTx`: re-validate via `getByToken`, insert the membership
   using `members.service.add` at `src/members/service.ts:88`, set `accepted_at`,
   return `{workspaceId, membershipId}`.
5. `revoke` — set `revoked_at`; throw `INVITE_NOT_FOUND` if the row is not in the
   given workspace.
6. Write `src/invitations/service.test.ts` covering: the happy path for all four
   functions, each of the five error codes, and accepting twice (the second must
   throw `INVITE_ALREADY_ACCEPTED` and must not create a second membership).

Done when
- `npm test -- invitations/service` passes
- The double-accept test asserts exactly one row in `memberships` afterwards
- **A-1..A-6 and A-8..A-11 in `tests/assertions/invitations.lifecycle.test.ts` go
  green** — this task is finished when phase 2's red turns green, not when its own unit
  tests pass

---

## Phase 4 · Surfaces

All four tasks build against the contract frozen in T-3. Their file sets are disjoint.

### T-8 · POST /workspaces/:id/invitations

Phase 4 · Role api · Skill implementer-node · Size s
Discharges REQ-1
Depends on T-3, T-7 · Parallel with T-9, T-10, T-11

Files

| path | range | action |
|---|---|---|
| src/api/routes/invitations.create.ts | — | new |
| src/api/routes/invitations.create.test.ts | — | new |
| src/api/router.ts | 61-74 | edit |

Follow the pattern at
- `src/api/routes/members.add.ts:1-52` — the exact handler shape: `requireRole('admin')`
  middleware first, contract schema parse, service call, `201` with a `Location`
  header, `AppError` mapped by the shared error middleware.
- `src/api/routes/members.add.test.ts:1-60` — the request-test shape, including
  `authedAs(admin)` from `test/helpers/auth.ts:18`.

Steps
1. Create the handler calling `invitations.service.create`, guarded by
   `requireRole('admin')` from `src/api/middleware/role.ts:7`.
2. Parse the body with `createInvitationSchema` from the frozen contract. Do not
   redefine the shape.
3. Return `201` with the response body and `Location:
   /workspaces/:id/invitations/:inviteId`.
4. Register the route in `src/api/router.ts` in the block at lines 61-74, alphabetically
   between `members` and `projects`.
5. Write the test: an admin creates one successfully; a non-admin gets `403`; a
   duplicate pending invite gets `409` with `INVITE_ALREADY_MEMBER` or the unique
   violation mapped by `src/api/middleware/errors.ts:31`.

Done when
- `npm test -- invitations.create` passes
- `curl -X POST` against a dev server with an admin session returns `201` and a
  `Location` header

### T-9 · GET /invitations/:token — the unauthenticated preview

Phase 4 · Role api · Skill implementer-node · Size s
Discharges REQ-2
Depends on T-3, T-7 · Parallel with T-8, T-10, T-11

Files

| path | range | action |
|---|---|---|
| src/api/routes/invitations.get.ts | — | new |
| src/api/routes/invitations.get.test.ts | — | new |
| src/api/router.ts | 61-74 | edit |
| src/api/middleware/auth.ts | 40-52 | edit |

Follow the pattern at
- `src/api/routes/password-reset.get.ts:1-38` — the only other unauthenticated
  token-lookup endpoint. Same shape, same `publicRoutes` registration, same
  deliberately thin response body.

Steps
1. Create the handler calling `invitations.service.getByToken`, returning only
   `workspaceName`, `email`, `role`, `expiresAt` — never the inviter's identity or any
   workspace detail beyond the name. This endpoint is unauthenticated; the response
   body is the whole security surface.
2. Add the path to the `publicRoutes` array at `src/api/middleware/auth.ts:40-52`,
   beside the password-reset entry.
3. Register in `src/api/router.ts` lines 61-74.
4. Write the test: a valid token returns the four fields and nothing else (assert the
   exact key set); expired returns `410` with `INVITE_EXPIRED`; unknown returns `404`.

Done when
- `npm test -- invitations.get` passes
- The response-shape assertion is on the exact key set, not a subset

### T-10 · POST /invitations/:token/accept

Phase 4 · Role api · Skill implementer-node · Size s
Discharges REQ-3
Depends on T-3, T-7 · Parallel with T-8, T-9, T-11

Files

| path | range | action |
|---|---|---|
| src/api/routes/invitations.accept.ts | — | new |
| src/api/routes/invitations.accept.test.ts | — | new |
| src/api/router.ts | 61-74 | edit |

Follow the pattern at
- `src/api/routes/members.add.ts:1-52` — same handler shape, but authenticated as any
  logged-in user rather than role-guarded.

Steps
1. Create the handler calling `invitations.service.accept` with the session user id
   from `req.user.id`.
2. Return `200` with `{workspaceId, membershipId}`.
3. Register in `src/api/router.ts` lines 61-74.
4. Write the test: accepting while logged in works; accepting while logged out returns
   `401`; accepting an already-accepted invite returns `409`; accepting an invite whose
   email differs from the session user's email still succeeds — the spec's REQ-3 says
   the link is the credential.

Done when
- `npm test -- invitations.accept` passes
- The already-accepted case asserts exactly one membership row

### T-11 · The invite-accept page

Phase 4 · Role frontend · Skill implementer-react · Size m
Discharges REQ-2, REQ-6
Depends on T-3 · Parallel with T-8, T-9, T-10

Files

| path | range | action |
|---|---|---|
| web/src/pages/AcceptInvite.tsx | — | new |
| web/src/pages/AcceptInvite.test.tsx | — | new |
| web/src/routes.tsx | 28-41 | edit |

Follow the pattern at
- `web/src/pages/ResetPassword.tsx:1-96` — the same token-in-the-URL page: reads the
  token with `useParams`, fetches via `useQuery`, and renders four states in the same
  order — loading, error, ready, submitted. Copy that state machine exactly.
- `web/src/pages/ResetPassword.test.tsx:1-70` — the MSW handler setup for each state.

Steps
1. Create the page reading `:token` from the route, fetching `GET /invitations/:token`
   with the generated client at `web/src/api/client.ts:12`.
2. Render the four states. For the error state, map each error code from the frozen
   contract to a specific sentence — expired, already accepted, revoked, not found —
   rather than one generic failure message. The spec's `## Error states` names all
   four.
3. On accept, call `POST /invitations/:token/accept` and navigate to
   `/workspaces/:workspaceId` on success.
4. If the visitor is not logged in, send them to `/login?next=<current path>` — the
   pattern is at `web/src/pages/ResetPassword.tsx:44`.
5. Register the route `/invite/:token` in `web/src/routes.tsx` lines 28-41, in the
   public routes block.
6. Write the test covering all four error states plus the happy path, with MSW
   handlers per state.

Done when
- `npm test -- AcceptInvite` passes
- Each of the four error codes renders its own distinct message, asserted by text

---

## Phase 5 · Integration

### T-12 · Send the invitation email

Phase 5 · Role integration · Skill implementer-node · Size s
Discharges REQ-1, REQ-5
Depends on T-8 · Parallel with —

Files

| path | range | action |
|---|---|---|
| src/email/templates/invitation.tsx | — | new |
| src/api/routes/invitations.create.ts | 30-46 | edit |
| src/email/templates/invitation.test.tsx | — | new |

Follow the pattern at
- `src/email/templates/password-reset.tsx:1-64` — the template shape and how the link
  is built from `config.publicUrl`.
- `src/api/routes/members.add.ts:38-45` — how a route enqueues mail: `mailer.enqueue`,
  never `mailer.send`, so a mail failure never fails the request.

Steps
1. Create the template taking `{workspaceName, inviterName, acceptUrl, expiresAt}`.
2. Build `acceptUrl` as `${config.publicUrl}/invite/${token}` — this must match the
   route registered in T-11 step 5.
3. In the create handler, after the service call and before the response, enqueue the
   mail with `mailer.enqueue`.
4. Write the template test asserting the rendered link matches the T-11 route exactly.

Done when
- `npm test -- email/invitation` passes
- Creating an invite in the dev environment puts exactly one message in the outbox
- A forced mailer failure still returns `201` — the enqueue is not in the request path

### T-13 · End-to-end: invite, open, accept

Phase 5 · Role integration · Skill implementer-node · Size m
Discharges REQ-1, REQ-2, REQ-3
Depends on T-8, T-9, T-10, T-11, T-12 · Parallel with —

Files

| path | range | action |
|---|---|---|
| e2e/invitations.spec.ts | — | new |

Follow the pattern at
- `e2e/password-reset.spec.ts:1-88` — the full shape: seeded users, the outbox helper
  at `e2e/helpers/outbox.ts:9` for pulling the link out of the sent mail, and the
  `test.describe.serial` wrapper.

Steps
1. Seed a workspace with an admin and one non-member user.
2. As the admin, invite the non-member's email through the UI.
3. Read the accept URL out of the outbox with the existing helper.
4. Open it as the non-member, accept, and assert landing on the workspace page.
5. Assert the members list now shows the new member with the invited role.
6. Re-open the same URL and assert the already-accepted message renders.

Done when
- `npm run test:e2e -- invitations` passes twice in a row from a clean database

---

## Phase 6 · Hardening

### T-14 · Rate-limit invitation creation

Phase 6 · Role reliability · Skill implementer-node · Size s
Discharges CL-3
Depends on T-8 · Parallel with T-15

Files

| path | range | action |
|---|---|---|
| src/api/routes/invitations.create.ts | 12-20 | edit |
| src/api/routes/invitations.create.test.ts | 60-84 | edit |

Follow the pattern at
- `src/api/middleware/rateLimit.ts:22-40` — the middleware exists; this is a
  registration, not an implementation.
- `src/api/routes/password-reset.request.ts:14` — an endpoint already applying it,
  keyed per workspace.

Steps
1. Apply `rateLimit({key: 'workspace', max: config.invitations.maxPerHour, window:
   '1h'})` to the create route, after the role guard and before the handler.
2. Add a test that the `maxPerHour + 1`-th request in a window returns `429` with
   `INVITE_RATE_LIMITED`.

Done when
- `npm test -- invitations.create` passes
- The limit is read from config, not hard-coded — `grep -n '20' src/api/routes/invitations.create.ts` returns nothing

### T-15 · Audit-log every invitation lifecycle event

Phase 6 · Role reliability · Skill implementer-node · Size s
Discharges CL-5
Depends on T-7 · Parallel with T-14

Files

| path | range | action |
|---|---|---|
| src/invitations/service.ts | 40-160 | edit |
| src/invitations/service.test.ts | 120-150 | edit |

Follow the pattern at
- `src/members/service.ts:96-104` — `audit.record(db, {actor, action, subject})` called
  inside the same transaction as the change, never after it.

Steps
1. Add `audit.record` calls inside the existing transactions in `create`, `accept`, and
   `revoke`, with actions `invitation.created`, `invitation.accepted`,
   `invitation.revoked`.
2. The subject is the invitation id; the actor is `invitedBy` for create and the
   accepting user for accept.
3. Extend the service test to assert one audit row per operation, and that a rolled-back
   transaction leaves none.

Done when
- `npm test -- invitations/service` passes
- The rollback case asserts zero audit rows

---

## Phase 7 · Proof

### T-16 · Verify the feature

Phase 7 · Role verifier · Skill verifier · Size m
Discharges REQ-1..REQ-6, all CL rows
Depends on all · Parallel with —

**Runs in a fresh session that wrote none of the code.** Nothing below is taken on
report; every command is re-run and its raw output pasted.

Files: none — this task writes evidence, not code.

Steps
1. Re-run the full suite and paste the raw output: `npm test && npm run test:e2e`. The
   assertion suite is the headline number: `npm test -- tests/assertions/invitations`
   must report **16 passing, 1 skipped, 0 failing** — the seventeen that phase 2 wrote.
2. Confirm the ordering with `git log --stat`: every file under `tests/assertions/`
   landed before the source file it exercises. A suite written afterwards encodes the
   behavior the code has rather than the behavior the spec asked for, and this is the
   only way to know which happened.
3. Run the feature for real: start the dev stack, invite an address, pull the link from
   the outbox, accept it in a fresh browser profile, and paste the transcript.
4. Discharge A-17 / CL-7, the one `observation` assertion: navigate the accept page by
   keyboard only and with a screen reader, and attach the recording. An observation
   without attached evidence is a claim.
5. Walk `## Coverage` row by row and mark each satisfied with its evidence, waived with
   its reason, or blocked with what is missing. Check each assertion against the
   verification kind the spec declared for it — a property test that became an example
   test is a silent downgrade and is reported, not accepted.
6. Read the whole diff as one design: is there one way of doing each thing, or several?
   Check specifically for a second token generator, a second error-mapping style, and
   inconsistent naming between `invite` and `invitation`.
7. Check the spec's `## Open questions` — every one either resolved or restated as a
   standing assumption for the release note.

Done when
- The assertion suite reports 16 passing, 1 skipped, 0 failing, with raw output attached
- Every `## Coverage` row is satisfied, waived, or explicitly blocked
- The raw transcript of step 3 and the recording from step 4 are in the report, not
  summaries of them
- The one-design read is written down with what was checked, not asserted as clean

---

## Coverage

| source | what it is | asserted by | built by |
|---|---|---|---|
| REQ-1 | An admin can invite someone by email | T-4, T-5 | T-2, T-7, T-8, T-12, T-13 |
| REQ-2 | The invitee can see who invited them before accepting | T-5 | T-3, T-9, T-11, T-13 |
| REQ-3 | Accepting the link creates the membership | T-4, T-5 | T-2, T-7, T-10, T-13 |
| REQ-4 | An admin can revoke a pending invitation | T-4 | T-7 |
| REQ-5 | The invitee receives an email with the link | T-4 | T-12 |
| REQ-6 | Expired, used, and revoked links each say what happened | T-4, T-5 | T-3, T-7, T-11 |
| CL-1 | The feature is behind a flag | — | T-1 |
| CL-2 | Tokens are unguessable and single-use | T-4 (property) | T-6, T-7 |
| CL-3 | Invitation creation is rate-limited | T-5 | T-14 |
| CL-4 | The migration has a rollback | — | T-2 |
| CL-5 | Lifecycle events are audit-logged | T-4 | T-15 |
| CL-6 | Personal data has a retention rule | `waived` — the only personal datum is an email address the inviting admin already holds; the row is deleted with the workspace by cascade | |
| CL-7 | The accept page is accessible | T-5 (skipped placeholder) | `observation` — discharged in T-16 step 4 |

Every row filled, checked before the gate. An empty cell means the plan is not ready,
and this table is the reason "we forgot the permission" becomes a blank cell somebody
notices in ten seconds rather than an incident.

**The `asserted by` column is what makes this verification-first rather than a good
intention.** A row with a builder and no asserter is a requirement nobody wrote a failing
test for — it will be built, it will look done, and nothing will ever have proved it. The
two rows with a dash are legitimately structural (a flag exists or it does not; a down
migration runs or it does not) and are covered by their tasks' done-checks. Any other
dash in that column blocks the gate.

## Decisions

Empty at the gate. Appended during `/build`; every later spawn carries this section.

| # | decision | why | binds |
|---|---|---|---|
| D-1 | Accepting an invite whose email differs from the logged-in user's succeeds | T-10 step 4 raised it; the spec's REQ-3 says the link is the credential, and forwarding an invite is a real workflow. Recorded so the hardening phase does not re-close it | T-10, T-13, T-16 |
