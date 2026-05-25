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

(Item 8 — browser-side cache nuke via Clear-Site-Data — deliberately out of scope; operator workflow, not skill responsibility.)
