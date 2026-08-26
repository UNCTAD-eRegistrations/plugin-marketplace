# Phase 9 — Smoke test

Smoke test: all 3 containers healthy, public homepage 200, a real
 procedure page 200 (proves the DB connection + migrated data works, not
 just the root path). **Login succeeding is not enough** — a successful
 login only proves the credential hash is right; it says nothing about
 permissions. Compare `RolePermission` row counts per role against the
 sibling used for the schema migration (`SELECT Role_Name, COUNT(*) FROM
 RolePermission GROUP BY Role_Name` on both DBs) — see `phase-2-schema-migration.md` for why this can
 be silently wrong even when everything else looks fine.
