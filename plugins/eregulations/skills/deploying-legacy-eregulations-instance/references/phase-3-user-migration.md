# Phase 3 — Migrate users from the temp Global DB

Migrate users: backfill legacy `Role` rows from the temp Global DB first
(see `phase-2-schema-migration.md` — this has to happen *before* phase 2's migration script, not after it), then master users (`IsMasterUser=1`, copied to every instance) + this
instance's own users (via `User_Role.SystemInstance_ID = <old numeric ID
from Web.config>`) + their `User_Role` rows + `UserFeedback`, all as
cross-database `INSERT ... SELECT ... WHERE NOT EXISTS (...)` against the
temp DB. Add `COLLATE DATABASE_DEFAULT` to any column used in a
cross-database `JOIN`/`WHERE`/`NOT IN` — the old Windows server's DB and the
shared container's DB are very likely different default collations, and
you'll get `Msg 468` otherwise. `User`/`UserFeedback` have identity PKs —
wrap the inserts in `SET IDENTITY_INSERT [User] ON` / `OFF` (and same for
`UserFeedback`) to preserve the original IDs that `User_Role` references.
Run a duplicate-username check first (`GROUP BY UserName HAVING COUNT(*) >
1`, scoped to this SystemInstanceID + master users) — collation is
case-insensitive, so `ahmed`/`Ahmed` collide. When you find a real
duplicate (same email, two accounts), keep the one with the more recent
`LastLogin` and/or broader `User_Role` footprint across instances, skip
the other; check both accounts' `<name>`-scoped role rows are identical
first so you're not silently dropping a permission the stale account had
that the kept one doesn't.
