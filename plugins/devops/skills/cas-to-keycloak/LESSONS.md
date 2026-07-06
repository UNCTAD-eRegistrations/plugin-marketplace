# Lessons learned — cas-to-keycloak

Retrospective from the first end-to-end run of the `cas-to-keycloak` skill chain (Cuba LIVE, May 2026). Each lesson is paired with the patch that landed (or is planned) to close it. New contributors / future skill maintainers should read this before touching the templates — most of the items below were not in the original skill recipe and were learned only by running the chain against a real CAS-based deployment.

## Recipe drift in sibling skills (auth-cutover skill family)

The `migrate-apps-from-cas-to-keycloak` skill prescribes per-service env-var changes with a static recipe. Several were silently wrong:

- **`KEYCLOAK_CLIENT_SCOPE_ID` on `bpa-backend`** had a hardcoded UUID (`e7342283-…`) that doesn't exist in any country's realm. Correct value is the `id` of the `clientScopes[]` entry whose `name == "eregistrations"` — must be resolved from the realm JSON at config-generation time, not hardcoded. (Same pattern as `KEYCLOAK_INSTITUTIONS_GROUP_ID` resolves from the `groups[]` entry named `institutions`.)
- **`CAS_URL` and `PARTC_URL` on `ds-frontend`** were "removed" per the recipe; should be set to literal `null` instead. The ds-frontend JS falls back to a hardcoded CAS path (`/cback/v1.0/cas/spa.html#/?response_type=code&client_id=oauth-client-test…`) when these env vars are absent, even with `KEYCLOAK_ACTIVE=true`. Kenya LIVE — the canonical working KC reference — keeps both as `null`.
- **`KEYCLOAK_INSTITUTIONS_GROUP_ID` missing on `camunda`** — the recipe added it to bpa-backend/ds-backend but skipped camunda; Kenya has it on camunda.
- **`GDB_CLIENT_AUTH_ID_1=0` missing on `gdb`** — the recipe added the standard `AUTH_SERVICE_*_1` block but omitted `GDB_CLIENT_AUTH_ID_1`. Kenya has it.

**Patch:** `migrate-apps-from-cas-to-keycloak/SKILL.md` rewritten from "instructions to mutate vars" to **"diff per-service env against Kenya, bring to parity"**. Both UUIDs (`KEYCLOAK_INSTITUTIONS_GROUP_ID`, `KEYCLOAK_CLIENT_SCOPE_ID`) are resolved from the realm JSON, never hardcoded.

## Postgres version skew

Operator workstation's `pg_dump` was 18.3, source DB was 16.13, throwaway was 15-alpine, deploy target was 16.13. pg_dump 18 emits `SET transaction_timeout = 0` (PG 17+ only) and `\restrict <token>` / `\unrestrict <token>` meta-commands (psql 17+) — both rejected by older Postgres.

**Patches:**
1. `templates/dump-keycloak-local/docker-compose.yml` — throwaway Postgres bumped from 15-alpine to **17-alpine** so the seed can load PG-17-aware dumps. Shipped.
2. `templates/dump-keycloak-local/deploy-keycloak-dump.sh` — strips both `SET transaction_timeout` lines and `\restrict`/`\unrestrict` meta-commands with `sed` before piping into psql on the (PG 16) target host. Shipped.

## Source DB layout assumption

The skill originally assumed one Postgres database with two schemas (`cas`, `partc`). Cuba LIVE has two separate databases (`cas`, `partc`) on one cluster — each with a schema of the same name as its database. The user's earlier "same DB, two schemas" answer didn't match reality on Cuba.

**Patch:** `templates/dump-keycloak-local/fetch-dumps.sh` accepts optional `[cas-db] [partc-db]` args. Defaults to `cas`/`partc` (which works for both layouts when schema name == db name); consolidated-host operators pass the same db-name twice. Shipped.

## Dump-load logistics

- `run.sh` runs `pg_dump` *without* `--create`, so the dump is **object-only**. If the deploy script loads it with `psql -d postgres -f`, every CREATE TABLE lands in the `postgres` system DB instead of `keycloak`. Symptom: Keycloak boots, sees an empty `keycloak` DB, runs Liquibase against an empty schema, then fails because nothing matches the loaded realm.
- Loading the dump via `sudo -u postgres psql` creates objects owned by **postgres**, not by **keycloak**. Symptom: Keycloak connects fine (LOGIN attribute set), then `permission denied for table databasechangelog` on first query.

**Patch:** `templates/dump-keycloak-local/deploy-keycloak-dump.sh`:
1. DROPs and CREATEs the `keycloak` DB on the deploy host with `OWNER $KC_DB_USER` *before* loading.
2. Prepends `SET ROLE $KC_DB_USER;` to the dump stream so all CREATE TABLE rows are owned by the keycloak role.

Shipped.

We intentionally *don't* use `pg_dump --create`: the deploy script would still need to assert ownership separately, and an explicit DROP+CREATE in our script reads more clearly.

## Container env propagation

`docker compose restart <svc>` re-starts the container with its *creation-time* env vars. After a compose change (cutover) the apps need `docker compose up -d --force-recreate <svc>` to pick up the new vars. Symptom we hit: ds-backend kept generating CAS redirect URLs (`client_id=oauth-client-test`) even after the compose was committed and "restarted".

**Patch:** `templates/dump-keycloak-local/deploy-keycloak-dump.sh` uses `up -d` (which recreates if compose changed) instead of `restart` for the keycloak container; SKILL.md operator checklist explicitly tells the operator to `up -d --force-recreate` the app services as a separate manual step before declaring the cutover done.

## Keycloak admin bootstrap trap

`KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD` env vars only fire on the **first** Keycloak boot against an empty DB. The deploy pre-seeds the DB with a master-realm admin user copied from the seed's throwaway (where the admin was created with `admin/admin`). So:
- The operator's value in `.env` for `KEYCLOAK_ADMIN_USER_PASSWORD` is silently ignored.
- The live Keycloak's master admin password is `admin/admin` — the throwaway dev default.

**Patch:** SKILL.md deploy mode includes an explicit post-deploy operator step: log in with `admin/admin`, immediately reset via the admin UI *or* `kcadm.sh set-password -r master --username admin --new-password '<…>'`. The deploy script's final summary loudly prints this warning. (Future improvement: the seed could bootstrap with a random password and surface it in the secrets report — TODO.)

## HAProxy reload is not automatic

`/etc/haproxy/haproxy.cfg` is typically a symlink into `/opt/eregistrations/Conf-LIVE/haproxy/<country>/haproxy.cfg`. A `git pull` on the deploy host updates the file on disk but the running haproxy daemon still has the old config in memory. Until `systemctl reload haproxy` runs, the cutover routing isn't live.

We hit this twice: once when `login.cuba.*` was still routing to CAS even though the file had been updated; again briefly after the formio reorder.

**Patch:** SKILL.md deploy operator checklist explicitly lists `sudo systemctl reload haproxy` as a required step, with verification (`curl -sI` against the cutover hostname).

## Pre-existing HAProxy ordering bugs surface during cutover

Comparing cuba's haproxy.cfg against Kenya's, the `use_backend formio if formio_path` rule was **after** the `use_backend display_system if is_display_system …` catch-all. Result: `cuba.eregistrations.org/formio/*` was being routed to ds-backend (which 404s) instead of to formio. This was a pre-existing bug, not introduced by the cutover, but it became blocking when the cutover required other haproxy edits — and was only visible after a systematic comparison.

**Patch:** New `verify` mode in `cas-to-keycloak` SKILL.md — runs a structural diff of the country's compose and haproxy against a chosen reference (default: Kenya), reports auth-related env-var deltas and `use_backend` ordering anomalies, no mutation. Run it before any cutover.

## Realm template source

The first time I generated the cuba realm.json, I copied from `cuba-eregistrations/Conf-PREVIEW/mincex/compose/keycloak-realm.json`. That repo is a tenant-specific deployment artefact (MINCEX preview, NOT the cuba.eregistrations.org LIVE we were migrating). The authoritative template lives at `eregistrations-starter-conf/scripts/keycloak-realm.template.json` on bitbucket. You pointed at it mid-flight.

**Patch:** `prepare-keycloak-realm/SKILL.md` defaults to fetching the template from `eregistrations-starter-conf` via `gh` / `curl`. If the local clone is present, it uses that; otherwise it fetches.

## Credential-file boundaries

Workflows that genuinely need a value from a credential-bearing file on a remote host (`MAIL_PASSWORD` from `.env`, registry auth from `~/.docker/config.json`, …) **must not enumerate the file**. The agent asks the operator instead. Two incidents during this run: stopped by the hook + by the operator when trying to read `.env` and `~/.docker/config.json` respectively.

**Patch:** baked into the global no-credential-file-enumeration memory; SKILL.md mode docs explicitly state "deploy never reads `.env` files on the deploy host".

## Browser-side cache survives across cutovers

Outside the skill's scope but worth flagging: after the cutover, browsers with cached pre-cutover service workers / Cache API / IndexedDB / localStorage continue serving the old (CAS-based) JS even after a hard reload. Incognito works fine. Standard "clear cache" doesn't touch SW / IndexedDB / localStorage — only DevTools → Application → Clear site data does.

This is operator workflow, not skill responsibility, so deliberately **not** patched into the skill. If you need a fleet-wide fix, push a temporary `Clear-Site-Data` response header in haproxy and remove it once everyone has cycled through.

## BPA-postgres holds its own copy of the legacy FKs

The migration recipe focused on porting identity (users, groups, credentials) into Keycloak, but the **downstream FK graph** in BPA's own postgres was never re-mapped. BPA stores `String institution_id` / `String unit_id` in 4 tables / 5 columns (`registration_institution`, `role_institution.institution_id`, `role_institution.unit_id`, `registration_unit.institution_id`, `registration_unit.unit_id`). All of them held the legacy PARTC integer ids; BPA-frontend's `institution-controller.service.ts` forwarded those `String`s verbatim to KC `/admin/realms/<R>/groups/{id}/children?max=200`. KC interpreted e.g. `1` as a group UUID and returned 404 → silently empty institution pickers on every legacy reference. Cuba LIVE had **293 broken rows** across these columns.

Found a month post-cutover by a PM complaint about a 404 in DevTools.

**Patches:**
1. New sibling skill `cas-to-keycloak-rewrite-bpa-postgres` (Phase 8 in the orchestrator chain) — backup → preview in ROLLBACK'd transaction → COMMIT pattern. Reads `partc_institution_id` and `partc_unit_id` (or legacy `partc_institution_unit_id`) stamped on KC groups, builds the integer → UUID mapping, runs UPDATEs on the 4 BPA tables. Includes orphan triage workflow. Shipped.
2. `cas-to-keycloak-orchestrator/SKILL.md` updated: 8-phase → 9-phase chain, new operator gate before phase 8.

## SQL alias `attribute_partc_institution_unit_id` produces an ungainly KC attribute key

The original `partc_units.sql` aliased `ui.id` as `attribute_partc_institution_unit_id`. The migrator does propagate `attribute_*` aliases to KC subgroup attributes — so KC subgroups got the double-noun key `partc_institution_unit_id` (instead of the parallel-to-institutions `partc_unit_id` that would mirror `partc_institution_id`).

Functionally fine — Phase 8 (`rewrite-bpa-postgres`) reads either key. But the verbose name is misleading: I lost 30+ minutes searching for `partc_unit_id` on KC subgroups before realising the attribute was there under a different name. The mistake was preventable from the first day if the alias had been canonical.

**Patch:** `templates/dump-keycloak-local/cuba-sql/partc_units.sql` rename `attribute_partc_institution_unit_id` → `attribute_partc_unit_id`. Fresh migrations stamp the canonical key. Legacy migrations keep the verbose key (no migration needed; consumer reads either).

## Don't drop legacy `cas` / `partc` databases for at least 30 days post-cutover

Cuba LIVE needed PARTC alive when the rewrite skill was retroactively applied a month post-cutover. The `partc.institution_unit` table was the ground-truth needed to recover unit name → integer mappings when KC subgroups were missing the `partc_unit_id` attribute (Cuba had only the legacy `partc_institution_unit_id`).

Operators have historically kept side-by-side databases (`partc_old`, `partc_10072023`, etc.) — this is the right instinct, just not codified. The 30-day floor matches typical "did anyone notice anything broken" feedback latency for citizen-facing services.

**Patch:** Added explicit warning to `cas-to-keycloak/SKILL.md` deploy phase ("Do NOT drop the legacy cas/partc DBs for at least 30 days post-cutover — they're the ground-truth for downstream fix-ups"). Schedule the drop in a calendar reminder, not as a same-day step.

## Orphan PARTC memberships → `null` group path → HTTP 500 on user create

`migrate.js` builds each user's `groups` from `user-memberships.json`, resolving every membership to a Keycloak group path via `institutions.find(...)?.path` / `units.find(...)?.path`. When a membership points at an institution/unit that isn't in the migrated set (a stale/orphan PARTC reference), the optional-chain returns `undefined`, which serializes into the create-user payload as a `null` element in the `groups` array. Keycloak NPEs server-side resolving the bad group path and returns a bodyless **HTTP 500 `{"error":"unknown_error"}`** — no `errorMessage`, so the migrator's `error?.response?.data?.errorMessage` logged the failure reason as the literal **`undefined`**.

Symptom on Cuba test (June 2026): 14 of 730 users failed with reason "undefined". They were NOT email-related (email is null for every Cuba user) and NOT simple case-collisions. Splitting the create vs role-mapping catch and dumping the full error (`status`, `data`, `message`) showed all 14 were `status=500` and every one carried a `null` in its `groups` payload. Fixing it recovered all 14 — and *revealed* 2 previously-masked case-collisions (the second of a `Foo`/`foo` pair only reaches the 409 path once the first user actually gets created), so the genuine-collision count rose 9 → 11.

**Patch:** `templates/dump-keycloak-local/migrator-src/migrate.js` — append `.filter(Boolean)` to the `groups` array so unresolvable memberships are dropped (the user keeps every *valid* institution membership; only the dangling reference is discarded). Generic across countries — any instance with orphan partc memberships hits this. Shipped.

## Username collisions drop distinct users → recreate the loser keyed by email

Keycloak usernames are case-insensitive; CAS usernames are case-sensitive, and CAS even allows two DISTINCT people to share a username (e.g. Cuba has user 404 `Nelson`/nelson.garcia@… and user 106 `nelson`/nelsonadpa@gmail.com). The migrator creates the first, then the second gets **HTTP 409 "User exists with same username"** and is dropped — so that person simply doesn't exist in KC and can't log in (by username *or* email, since their email never landed either). On Cuba this was 11 users.

cuba.live LIVE handled it by keeping collision users with **`username = email`** (emails are unique, so no collision); they then sign in by email (`loginWithEmailAllowed`). The dropped user keeps full identity + bcrypt password + roles + group memberships once recreated through the normal path.

**Patch:** `templates/dump-keycloak-local/migrator-src/migrate.js` wraps `users.create` in `createUserWithUsernameFallback` — on a 409 username collision it retries once with the email as the username, then flows through the same `.then()` realm-role / client-role / group assignment. Idempotent and generic. (When patching an ALREADY-migrated realm rather than re-seeding, recreate the losers via admin REST with `{type:password,algorithm:bcrypt,hashedSaltedValue,hashIterations:10}` and backfill roles/groups from the migrator's `user-roles.json`/`user-memberships.json`.)

## Backfill must match users by `cas_user_id`, not username

Once the migrator keeps collision losers under `username = email` (previous lesson), matching a user by their original CAS **username** is broken. `backfillUser` searched `kc.users.find({ username: casUsername })` and case-insensitive-filtered — but for a collision loser (`nelson`, cas 106, now stored as `nelsonadpa@gmail.com`) that search returns the *winner* (`nelson`, cas 404) and grafts 106's roles onto 404's account. Verified on dev.cuba: `?username=nelson` returns three users; the filter picked the wrong one. The backfill also *under-counted* "missing users" the same way — collision winners occupy the losers' usernames, so a username diff reported 13 missing when 23 were actually absent.

**Patch:** `cuba-sql/backfill.js` `backfillUser` now resolves the KC user by the stable `cas_user_id` attribute first (`kc.users.find({ q: 'cas_user_id:<id>' })`), falling back to the username match only for pre-attribute migrations. Verified: `?q=cas_user_id:106` → exactly `nelsonadpa@gmail.com`, `?q=cas_user_id:404` → exactly `nelson`. The same rule applies to any post-migration "who's missing" audit — count by `cas_user_id`, never username.

## Split identity across CAS + PARTC → officer rights silently lost

The migrator joins a user's login, roles, and institution/unit memberships on one `cas_user_id`. That drops rights when one human spans two legacy ids. Cuba dev: `nelsonadpa@gmail.com` is CAS user **106** (his live login, `citizen`), but PARTC user **23** — `cas_id=23`, same email — carries his Part B officer business-roles across 3 institutions. The migration carried the login (106, no PARTC membership) and left the officer identity (23) behind. He logs in fine and sees no desks; nothing logs it. Same family as the FK-orphan and username-collision problems: identity keyed on the wrong field.

**Patch:** new **`reconcile`** mode + `templates/dump-keycloak-local/reconcile-identities.sh` — a read-only pre-cutover audit that cross-checks CAS emails against PARTC officer identities and flags (A) email→different-cas-id, (B) dangling cas_id, (C) one email under multiple CAS logins. Surface for a human, don't auto-fix (Part B access is KC group-membership-driven, so remediation is adding the login-id account to the right institution groups). Verified on dev.cuba: flags exactly the nelson split, zero false positives.

## KC admin token issuer must match the API base URL

The phase-8/9 rewrite helpers minted a client-credentials token via `http://localhost:8080` *inside* the keycloak container, then called the **public** admin API — which 401s, because the token's issuer (`localhost:8080`) doesn't match the public hostname. Mint the token against the same base URL you'll call (`https://login.<domain>/realms/<R>/…/token`), or accept a pre-minted token. Cheap fix, otherwise a confusing dead-end.

## Seed throwaway: amd64-only image + short health grace

`unctad/keycloak:2.18` is linux/amd64 only — under qemu on an Apple-Silicon laptop the seed is unusably slow and flaky (also hit Docker Desktop proxy/DNS drops mid-pull). **Run `seed` on an amd64 host — the deploy host itself is the natural choice.** Separately, the throwaway keycloak had no explicit healthcheck, so it inherited the image's 60s `start_period`; a Quarkus cold build + realm import routinely needs 2-3 minutes, so `run.sh` saw "unhealthy" and tore the stack down before import finished.

**Patch:** `templates/dump-keycloak-local/docker-compose.yml` gives the keycloak service an explicit healthcheck with `start_period: 600s`; SKILL.md seed notes the amd64-host requirement.

## Staged tooling silently lags the plugin

The skill runs from a copy of `dump-keycloak-local/` staged into the country
repo's `sql/`, and (correctly) won't clobber operator edits — but it also never
refreshed un-modified files, and the plugin cache is version-pinned. So a fix on
`main` need never reach a cutover. dev.cuba proved it: the migrator's collision
fix was already upstream, yet the seed still dropped 23 users because the staged
copy predated it (issue #42).

**Patch:** ship a `TOOLING_VERSION` stamp (tracks the skill's `metadata.version`)
and a `check-tooling-version.sh` guard that every mode runs first — it compares
the staged stamp against the plugin's and stops with a re-stage instruction when
the staged copy is older or unstamped. Bump `TOOLING_VERSION` in the same commit
as any change under `dump-keycloak-local/`.

## Email-as-login CAS users have NULL `cas.user_property.value` for `username`

Some CAS installs (elsalvador LIVE) hold users whose `cas.user_property` row at `property_id=1` (username) doesn't exist — they registered with email and have only `property_id=2` (primary_email). The original `cas_users.sql` `LEFT OUTER JOIN cas.user_property … WHERE property_id=1` returns NULL `username` for these users, and the migrator's `KcAdminClient.users.create({ username: null, … })` fails with `User name is missing`. On elsalvador LIVE the gap was **17431 of 59197 users (29%)** lost on the first seed pass.

**Patch:** `cuba-sql/cas_users.sql` (and country-template equivalents) wrap the username SELECT in `COALESCE(up.value, up2.value) AS username` — when CAS lacks an explicit username, fall back to the primary_email. Recovered 15443 users on the elsalvador rerun (final fail count 1988, almost entirely case-insensitive username collisions per the next lesson). The fallback adds a small risk of `<email>` colliding with an existing `<email>` username in another row; that case re-raises as a regular collision and is recoverable via backfill.

## Long-running `backfill.sh` outlives its admin token

`backfill.js` calls `kc.auth({...grantType:'password'})` **once at startup**. The admin-cli token's default `access.token.lifespan` on a freshly-deployed realm is 60s. The user-roles loop on elsalvador LIVE ran through ~14000 users (≈15 min) before all subsequent API calls returned `401 Unauthorized` — **44906 failures** out of ~59000 attempts, all of them token expiry, none data-related.

**Patch:** `backfill.js` lifts the credentials dict into a `const credentials` and calls `await kc.auth(credentials)` inside the existing `processed % 100 === 0` reporting branch. Token refreshes every 100 users (≈5–10s on a warm realm) — bounded, silent, no operator config needed. Alternative deployed elsewhere: bump admin-cli `access.token.lifespan` to 3600s via `kcadm.sh update clients/<id>`; less invasive but country-specific.

## `fetch-dumps.sh` post-dump sanity check crashes the whole script on SIGPIPE

The current `fetch-dumps.sh` runs `xzcat "$outfile" | awk … { exit }'` to row-count the dumped table. `awk … exit` closes its stdin while `xzcat` is still writing → `xzcat` receives SIGPIPE → exits 141. With `set -euo pipefail` the whole script aborts even though the dump itself succeeded and is sitting on disk. Symptom: `Exit code 141` after the locale warning, no `==Done==` banner. Operator thinks fetch failed when the dump is actually fine.

**Patch:** wrap the sanity-check pipeline in `set +o pipefail` (or `|| true` on the inner awk), restore `pipefail` after. Operator-facing fallback: re-run the dump command manually — the dump command itself works; only the sanity check is broken.

## Split-host topology — DB and swarm on separate hosts

`deploy-keycloak-dump.sh` assumes one SSH host runs both the Postgres-with-`sudo -u postgres` and the docker-managed Keycloak service. elsalvador LIVE is split: `unctad_elsalvador_live_db` holds Postgres, `unctad_elsalvador_live` is the swarm manager with Keycloak. The script's single `SSH_HOST` arg can't address both.

**Patch:** none yet (deferred). Operator-side workaround that worked on elsalvador: a one-off split script that `scp + psql`s on the DB host then `ssh + docker service update`s on the swarm host. For a longer-term fix the skill should accept `DB_SSH_HOST` and `SWARM_SSH_HOST` separately. The `docker service update` step also needs `sudo` on the swarm host because the SSH user typically isn't in the `docker` group on production hosts; `sudo -n docker …` is the right call.

## Quick reference — where each lesson landed

| # | Lesson | Patch landing site |
|---|---|---|
| 1 | Skill recipes hardcoded UUIDs / removed vars instead of nulling / missed vars | `migrate-apps-from-cas-to-keycloak/SKILL.md` (eregistrations repo) |
| 2 | Pre-existing config drift only visible via reference comparison | new `verify` mode in this skill |
| 3 | PG version skew (pg_dump 18 → PG ≤17) | `templates/.../docker-compose.yml` PG17 + `deploy-keycloak-dump.sh` sed strip |
| 4 | Object-only dump + ownership trap | `deploy-keycloak-dump.sh` DROP/CREATE + SET ROLE |
| 5 | Two-DB source layout vs one-DB-two-schemas assumption | `fetch-dumps.sh` accepts `[cas-db] [partc-db]` |
| 6 | `docker compose restart` preserves stale env | SKILL.md deploy checklist + operator `up -d --force-recreate` step |
| 7 | Pre-seeded admin password trap (admin/admin from throwaway) | SKILL.md deploy summary warns + manual kcadm reset step |
| 9 | Realm template source ambiguity | `prepare-keycloak-realm/SKILL.md` points at starter-conf |
| 10 | HAProxy daemon needs explicit reload | SKILL.md deploy checklist adds `systemctl reload haproxy` |
| 11 | BPA-postgres holds legacy PARTC integer FKs that BPA-frontend forwards to KC | new `cas-to-keycloak-rewrite-bpa-postgres` skill (Phase 8) |
| 12 | SQL alias produced verbose `partc_institution_unit_id` instead of canonical `partc_unit_id` | `cuba-sql/partc_units.sql` alias rename; consumers read either key |
| 13 | Legacy `cas` / `partc` databases dropped too soon block downstream fix-ups | SKILL.md deploy phase: 30-day-floor warning |
| 14 | Orphan PARTC membership → `null` group path → KC 500 "undefined" on user create | `migrator-src/migrate.js` `.filter(Boolean)` on the `groups` array |
| 15 | Username collision drops a distinct CAS user (409) | `migrate.js` `createUserWithUsernameFallback` retries with email as username |
| 16 | Backfill matched users by username → wrong/lost roles + under-counted missing | `cuba-sql/backfill.js` matches by `cas_user_id` attribute first |
| 17 | Split identity (CAS login vs PARTC officer id) silently drops officer rights | new `reconcile` mode + `reconcile-identities.sh` audit |
| 18 | Rewrite helpers' admin token issuer ≠ public API URL → 401 | mint token via the public base URL (SKILL notes) |
| 19 | Seed image amd64-only + 60s health grace too short | `docker-compose.yml` explicit healthcheck `start_period:600s`; run seed on amd64 host |
| 20 | Non-collision user-create failures printed "undefined" | `migrate.js` catch surfaces `error`/`message`/status |
| 21 | Staged tooling silently lags the plugin → upstream fixes miss cutovers | `TOOLING_VERSION` + `check-tooling-version.sh` staleness guard (issue #42) |
| 22 | Email-as-login users skipped (null `cas.user_property` username) | `cuba-sql/cas_users.sql` `COALESCE(up.value, up2.value)` |
| 23 | Long-running backfill outlives admin token | `backfill.js` re-auths every 100 users |
| 24 | `fetch-dumps.sh` SIGPIPE crash from awk sanity check + pipefail | wrap sanity check in `set +o pipefail` |
| 25 | Split-host topology not supported by `deploy-keycloak-dump.sh` | docs only — manual scp+ssh workaround; future: `DB_SSH_HOST` + `SWARM_SSH_HOST` |

(Item 8 — browser-side cache nuke via Clear-Site-Data — deliberately out of scope; operator workflow, not skill responsibility.)

(Two further elsalvador-run lessons — `flyway.repair()` row deletion on renamed migrations, and `-Dflyway.outOfOrder=true` ignored by raw `Flyway.configure()` — were initially drafted for this file but moved to `upgrade-eregistrations-instance/LESSONS.md`: they're BPA-backend Java behaviour that surfaces post-handoff, not a cas-to-keycloak concern.)
