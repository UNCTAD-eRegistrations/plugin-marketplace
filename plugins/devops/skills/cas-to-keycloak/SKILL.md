---
name: cas-to-keycloak
description: >
  End-to-end CAS → Keycloak user / role migration pipeline for eRegistrations
  country instances. Three operational modes: `fetch` (dump cas + partc
  schemas from a source Postgres via ssh + sudo), `seed` (run a throwaway
  Docker stack that imports the realm JSON and produces an enriched
  `sql/keycloak.sql` ready to load into a target Keycloak's Postgres), and
  `backfill` (apply only the realm-role + role-mapping diff against an
  already-running Keycloak — idempotent, useful when the previous seed was
  buggy or new custom roles appear in partc later). Generic across country
  instances; ships Cuba's SQL extracts as a reference; tested against the
  Cuba MINCEX preview deployment.
license: UNCTAD-Internal
compatibility: >
  Requires Docker + docker compose, a country eRegistrations config repo
  under /home/jenkins or /opt (either `eregistrations` or
  `<country>-eregistrations`), and (for fetch) ssh + sudo access to the
  source Postgres host. The target Keycloak (for backfill) is reached by
  HTTPS from the operator workstation.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(ls *), Bash(find *), Bash(stat *), Bash(git *), Bash(cp *), Bash(mkdir *), Bash(chmod *), Bash(test *), Bash(bash *), Bash(./run.sh *), Bash(./backfill.sh *), Bash(./fetch-dumps.sh *), Bash(docker *), Bash(xzcat *), Bash(grep *), Bash(awk *), Bash(wc *), Bash(python3 *), AskUserQuestion, TodoWrite
metadata:
  version: "1.3.1"
  version-date: "2026-08-25"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "fetch|seed|backfill [country]"
  jira: "TOBE-17751"
---

You are an expert eRegistrations DevOps engineer. Your task is to orchestrate the CAS → Keycloak migration for an eRegistrations country instance: fetch source dumps, produce a Keycloak realm import artefact, and/or backfill missing roles + role mappings into an already-running Keycloak.

**Read `LESSONS.md` (alongside this file) before invoking any mutating mode** — it covers gotchas (PG version skew, container env propagation, admin bootstrap trap, browser cache survivors, etc.) whose symptoms look like other problems.

## Five modes

| Mode | What it does | Inputs the skill prompts for |
|---|---|---|
| `verify` | Diff the country's compose + haproxy against a working KC reference (default: kenya). Reports auth-related env-var deltas and `use_backend` ordering anomalies. **No mutation.** Run before any cutover. | reference country (default kenya) |
| `reconcile` | Cross-check CAS + PARTC source identities for split-identity hazards the migrator (which keys everything on one `cas_user_id`) would silently drop. **No mutation.** Run before fetch/seed. | ssh host, optional db names |
| `fetch` | ssh to source Postgres, `sudo -u postgres pg_dump -n cas` + `-n partc`, xz-compress, write to `<repo>/sql/{cas,partc}.sql`. | ssh host, optional db names |
| `seed` | Spin up throwaway `postgres + cas-db + partc-db + keycloak + migrator` stack (PG 17 throwaway), import realm, load dumps, run migrator, `pg_dump` the enriched Keycloak DB → `<repo>/sql/keycloak.sql`. | (resolves from repo) |
| `deploy` | scp `sql/keycloak.sql` to the target deploy host, DROP+CREATE the keycloak DB owned by the keycloak role, load the dump as that role (so ownership is right), restart Keycloak, wait for the health endpoint. | ssh host, compose vs swarm, optional db/health overrides |
| `backfill` | Connect to a running Keycloak; create missing realm roles, then diff/apply realm-role + client-role mappings per user. Idempotent. | target `AUTH_URL`, realm, admin creds |

All modes share a setup step: locate the country repo, stage the vendored `dump-keycloak-local/` tooling into it.

## Repo discovery

The country config repo lives at one of:
- `/home/jenkins/eregistrations` (generic monorepo)
- `/home/jenkins/<country>-eregistrations` (country-only)
- `/opt/eregistrations`
- `/opt/<country>-eregistrations`

Resolution rule:
1. Get the country arg (e.g. `cuba`); fall back to prompting via AskUserQuestion.
2. Probe all four paths in order. Collect the ones that exist and are git repos (`test -d <path>/.git`).
3. If multiple match, pick the *freshest* — the one whose `HEAD` commit timestamp is newest (`git -C <path> log -1 --format=%ct`).
4. Confirm the resolved path with the operator before any mutating action.

For Cuba, layout is `Conf-<ENV>/mincex/compose/…` (instance-first). For other countries it is typically `Conf-<ENV>/compose/<country>/…` (country-second). Detect by globbing:
- `Conf-PREVIEW/*/compose/docker-stack.yml` — country-only layout (e.g. cuba-eregistrations: instance is the `*`)
- `Conf-PREVIEW/compose/*/docker-stack.yml` — generic layout

The skill needs to know **where the realm JSON is** for the seed mode and **what realm name** is configured:
- realm JSON path: under the matching `Conf-PREVIEW/.../compose/keycloak-realm.json`
- realm name: `.realm` field inside that JSON

## Staging the vendored tooling

The skill ships `templates/dump-keycloak-local/` containing:

```
dump-keycloak-local/
├── run.sh                 # full seed pipeline
├── backfill.sh            # in-place backfill against a running Keycloak
├── fetch-dumps.sh         # ssh + sudo -u postgres pg_dump
├── docker-compose.yml     # throwaway stack
├── cuba-sql/              # Cuba-specific SQL extracts + migrate-wrapper + backfill.js
│   ├── cas_users.sql
│   ├── cas_user_roles.sql
│   ├── partc_institutions.sql
│   ├── partc_units.sql
│   ├── partc_user_memberships.sql
│   ├── partc_user_roles.sql
│   ├── extract.sh
│   ├── migrate-wrapper.js
│   └── backfill.js
├── migrator-src/          # vendored cas-to-keycloak Node tool
│   ├── migrate.js
│   ├── migrate-lomas.js   # eRegistrations v2 (mano) source variant — LOM-21
│   ├── package.json
│   └── package-lock.json
├── TOOLING_VERSION        # authoritative version of this tooling (tracks skill metadata.version)
├── check-tooling-version.sh  # staleness guard (see below)
└── backfill-other-name-attrs.sh
```

On every run:
1. Resolve `<repo>/sql/dump-keycloak-local/` as the staging target.
2. Copy missing files from `templates/dump-keycloak-local/` into the target — **including `TOOLING_VERSION`**.
3. **Never overwrite operator-modified files** without explicit confirmation. If a file already exists and differs from the template, diff and ask.
4. `sql/` is gitignored by convention in these repos; staging into it is non-destructive to git history.

### Staleness guard (run before EVERY mode)

The staged copy can silently lag the plugin — a fix that lands upstream never
reaches a cutover whose `sql/dump-keycloak-local/` was staged from an older
plugin. This is not hypothetical: a dev.cuba seed dropped 23 users to a bug
that was already fixed in the migrator, because the staged copy predated the
fix (issue #42).

Before doing any work in fetch / seed / deploy / backfill / reconcile, run:

```bash
<skill-templates>/dump-keycloak-local/check-tooling-version.sh <repo>/sql/dump-keycloak-local
```

- **exit 0** — staged copy matches (or is newer than) the plugin; proceed.
- **exit 3** — staged copy is older or unstamped. **Stop.** Re-stage the tooling
  (`cp -a <skill-templates>/dump-keycloak-local/. <repo>/sql/dump-keycloak-local/`)
  after reconciling any operator edits per rule 3, then re-run the check.

Bump `TOOLING_VERSION` to the skill's new `metadata.version` in the same commit
whenever any file under `dump-keycloak-local/` changes, so the guard can see the
difference.

For a new country (e.g. `lesotho`):
- Detect that `<repo>/sql/dump-keycloak-local/lesotho-sql/` does not exist.
- Copy `cuba-sql/` → `lesotho-sql/` as a starting point.
- Pause and tell the operator: "Cuba's SQL extracts have been copied as a starting point for `lesotho`. Open `lesotho-sql/cas_users.sql` and the partc files, verify property IDs / role names, then re-run."
- Exit without running.

## Mode: reconcile

Read-only identity audit of the CAS + PARTC **source** data, before any dump or
seed. The migrator joins a user's login, roles, and institution/unit
memberships on a single `cas_user_id`; that silently loses rights whenever one
human spans two legacy ids — most commonly a PARTC officer identity attached to
an old CAS account while the person's live login is a newer CAS account with
the same email. The person migrates fine as an applicant and sees no Part B
desks, with nothing in any log.

1. Prompt for `ssh-host` and (optionally) the `cas`/`partc` db names.
2. Run `<repo>/sql/dump-keycloak-local/reconcile-identities.sh <host> [cas-db] [partc-db]`.
3. Report the three anomaly classes it prints:
   - **A** — PARTC officer identity whose email maps to a *different* cas id than PARTC stored (rights will attach to the wrong / no KC user).
   - **B** — PARTC officer identity whose `cas_id` has no CAS login at all (dangling).
   - **C** — one email under multiple CAS logins (ambiguous identity).
4. Surface for operator decision — do **not** auto-fix. The remediation for class A is to add the corresponding KC institution/unit groups to the login-id account after cutover (Part B access in eRegistrations is group-membership-driven, so the `citizen` realm role stays and only groups are added).

The script resolves each schema's email property id from its own catalog, so it
is not hardcoded to one instance's property numbering. "Officer identity" is a
PARTC user with at least one institution/unit business-role — applicant-only
PARTC users carry no rights and are not flagged.

## Mode: verify

Structural diff against a reference KC LIVE (default `kenya`). No mutations. Run **before** seed/deploy to catch:
- Auth-related env-var deltas per service (missing `KEYCLOAK_INSTITUTIONS_GROUP_ID`, dropped `CAS_URL=null`, hardcoded UUIDs)
- `use_backend` ordering anomalies (path-rules buried after host catch-alls — see LESSONS.md "Pre-existing HAProxy ordering bugs")

1. Locate the country repo + reference repo.
2. Resolve `<repo>/Conf-LIVE/compose/<country>/docker-{compose,stack}.yml` for both.
3. Per service block, parse env vars filtered to `(AUTH_*, KEYCLOAK_*, OAUTH_*, CAS_*, PARTC_*)`. Report:
   - keys in reference but missing in target
   - keys with different non-domain values
4. Per `frontend www-https`, list `use_backend` rules in order. Flag any path-based rule (e.g. `if formio_path`) that appears AFTER a host-only catch-all (`if is_display_system …`) — that's a routing trap.
5. Print findings + suggested fixes. Operator decides whether to apply.

A standalone helper at `templates/dump-keycloak-local/verify-against-reference.sh` does the comparison; the skill is just a thin orchestrator around it.

## Mode: fetch

1. Prompt for `ssh-host` and `db-name` via AskUserQuestion (no defaults — every country has its own).
2. Confirm: "About to run `ssh <host> 'sudo -u postgres pg_dump -d <db> -n cas | xz' > <repo>/sql/cas.sql` (and the same for partc). Proceed?"
3. On confirm, execute `<repo>/sql/dump-keycloak-local/fetch-dumps.sh <host> <db> <repo>`.
4. Report sizes and the user-row sanity counts the script prints.

## Mode: seed

1. Confirm `<repo>/sql/cas.sql` and `<repo>/sql/partc.sql` exist. If either is missing, offer to invoke fetch first; otherwise abort.
2. Resolve env vars for `docker-compose.yml`:
   - `COUNTRY` = country arg
   - `KC_REALM_NAME` = `.realm` from the resolved realm JSON
   - `REALM_JSON_PATH` = path *relative to dump-keycloak-local/* to the realm JSON (e.g. `../../Conf-PREVIEW/mincex/compose/keycloak-realm.json`)
   - `INSTITUTION_GROUP_ID` = auto-resolved from the realm JSON. Walk `groups[]`, pick the top-level entry where `name == "institutions"`, take its `id`. Display the value and ask the operator to confirm before proceeding. Abort if no such group exists (the migrator can't run without one).
   - `MIGRATOR_SRC_PATH` = `./migrator-src` (vendored)
3. Run `<repo>/sql/dump-keycloak-local/run.sh` with those env vars exported.
4. After completion, report:
   - `wc -l sql/keycloak.sql` and `ls -lh`
   - Realm-role count and per-role assignment counts via the same Python snippet the dev workflow uses (see `cuba-sql/extract.sh`).
   - Any `Failed to create user` lines from the run output (these are case-insensitive username collisions — pre-existing migrator behaviour, recoverable via backfill).

## Mode: deploy

Load a seeded `sql/keycloak.sql` onto the target deploy host's Keycloak Postgres and restart Keycloak so the imported realm is live, without burning the cutover window on a slow `--import-realm` boot.

1. Confirm `<repo>/sql/keycloak.sql` exists. If missing, run seed first; abort.
2. Prompt via AskUserQuestion for:
   - `SSH_HOST` — target deploy host (e.g. `unctad_cuba_live`)
   - Deployment shape:
     - `compose` → asks for `KC_COMPOSE_DIR` (defaults to `/opt/eregistrations/Conf-LIVE/compose/<country>`)
     - `swarm` → asks for `KC_SWARM_STACK` (the stack name; service `<stack>_keycloak` is restarted)
   - Optional: `KC_DB_NAME` (default `keycloak`), `KC_DB_USER` (default `keycloak`), `KC_HEALTH_URL` (default `http://127.0.0.1:9003/health/ready`)
3. Confirm: "About to scp `sql/keycloak.sql` to `<SSH_HOST>:/tmp/`, terminate live `<KC_DB_NAME>` connections, run `sudo -u postgres psql -f` on it, and restart Keycloak. The `--clean --if-exists` headers in the dump will drop the existing Keycloak DB. Proceed?"
4. On confirm, run `<repo>/sql/dump-keycloak-local/deploy-keycloak-dump.sh <SSH_HOST> <repo>` with the relevant env vars exported.
5. Report: dump upload size, psql load summary, restart confirmation, health-probe status.

Deploy **never reads `.env` files on the deploy host** (memory rule). DB / OAuth client secrets must already be in place on the host (set by the operator out-of-band) before `deploy` runs — otherwise the post-restart Keycloak will fail to come up and the health probe will time out.

Dry-run via `DRY_RUN=1`.

### Post-deploy operator checklist (deploy mode MUST print this to stdout at the end)

1. **Master admin is `admin/admin`.** The pre-seeded DB bypasses Keycloak's `KEYCLOAK_ADMIN*` env-var bootstrap — the throwaway's `admin/admin` is what's actually live. Log in and reset immediately:
   ```
   docker exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
     --server http://localhost:8080 --realm master --user admin --password admin
   docker exec keycloak /opt/keycloak/bin/kcadm.sh set-password \
     -r master --username admin --new-password '<…>'
   ```
2. **Apps still on stale env vars.** After the cutover compose lands on the host, the existing app containers retain their creation-time env vars. `docker compose restart` does NOT pick up new env. **Use `up -d --force-recreate`**:
   ```
   sudo docker compose -f <stack>.yml up -d --force-recreate \
     bpa-frontend bpa-backend ds-frontend ds-backend \
     statistics-frontend statistics-backend gdb camunda mule
   ```
3. **HAProxy daemon needs an explicit reload.** `/etc/haproxy/haproxy.cfg` is typically a symlink into `/opt/eregistrations/Conf-LIVE/haproxy/<country>/`, so a git pull updates the file but the running daemon keeps the old config in memory:
   ```
   sudo systemctl reload haproxy
   curl -sI https://login.<domain>/ | head -5   # should show Keycloak, not the old auth backend
   ```
4. **Browser cache survives.** Users with cached pre-cutover JS will look broken (the JS still calls `/cback/...` and hits 404s). Standard cache clear doesn't touch service workers / IndexedDB / localStorage — incognito works, normal browser doesn't. Tell affected users to open DevTools → Application → Clear site data. (Fleet-wide nuke via `Clear-Site-Data` haproxy header is operator-owned, intentionally out of skill scope.)
5. **Run `cas-to-keycloak-rewrite-bpa-postgres` BEFORE declaring the cutover complete.** BPA-postgres still holds legacy PARTC integer FKs in `registration_institution`, `role_institution`, `registration_unit` — BPA-frontend forwards those to KC and 404s on every institution picker. The orchestrator chains this as Phase 8; if you're running modes manually, invoke that sibling skill explicitly after deploy.
6. **Do NOT drop the legacy `cas` / `partc` databases for at least 30 days post-cutover.** They are the ground-truth needed to recover mappings if anything downstream surfaces an unmapped reference later (Cuba LIVE needed PARTC alive a month post-cutover to retroactively recover unit mappings). Schedule the drop in a calendar reminder, not as a same-day step. Operators have historically kept side-by-side databases (`partc_old`, `partc_10072023`, etc.) — codify the instinct.

## Mode: backfill

1. Confirm `<repo>/sql/dump-keycloak-local/migrator-workdir/{users,user-roles}.json` exist. If missing, instruct operator to run seed first; abort.
2. Prompt via AskUserQuestion for:
   - `AUTH_URL` — target Keycloak base URL (e.g. `https://login.<domain>` or the temp Cuba preview `https://graylog.draftvucecuba.mincex.gob.cu`)
   - `AUTH_REALM_NAME` — target realm
   - `AUTH_ADMIN_USERNAME` — master-realm admin (default `admin`)
   - `AUTH_ADMIN_PASSWORD` — master-realm admin password (no default; do **not** echo)
3. Confirm: "About to apply diff against `<AUTH_URL>` realm=`<AUTH_REALM_NAME>`. This will create missing realm roles and add missing role mappings to existing users. Proceed?"
4. On confirm, run `<repo>/sql/dump-keycloak-local/backfill.sh` with the env vars exported.
5. Report the script's summary block: roles created, users matched, assignments added vs already-present, failures.

`NODE_TLS_REJECT_UNAUTHORIZED=0` is set inside `backfill.sh` by default — eRegistrations internal Keycloak certs drift expired. If the operator wants strict TLS, accept `NODE_TLS_REJECT_UNAUTHORIZED=1` as an override and pass it through.

## Variant: eRegistrations v2 (mano) source — no CAS (LOM-21)

Some legacy instances run the pre-CAS eRegistrations **v2 / mano** stack (dbjs storage, `mano-auth` login) — e.g. Lomas de Zamora (`elomas.gob.ar`). Fetch/seed do not apply: there is no CAS/PARTC Postgres, and the stored hash `bcrypt(sha256(email + password))` cannot be verified by Keycloak, so **credentials are not migrated** — users set a new password via "Forgot password" at first login (`resetPasswordAllowed` + SMTP must be on in the realm). Use `migrator-src/migrate-lomas.js` instead of `migrate.js`:

1. **Export on the old server** (in the v2 app folder). The stock `npm run generate-users-list` only lists role `user` holders — officials are missing — so prefer the migration export shipped with the v2 repo (`bin/generate-users-migration-export` → `tmp/users-migration-export.json`: all `mano-auth` roles, v2 `userId`, role-derived institution). Passwords are never exported.
2. **Stage** this tooling into `<repo>/sql/dump-keycloak-local/` (gitignored) and `npm install` inside `migrator-src/`.
3. **Credentials** go in `migrator-src/.env.lomas` (gitignored — never the tracked `.env`): `AUTH_URL`, `AUTH_REALM_NAME`, `AUTH_ADMIN_CLIENT`, `AUTH_ADMIN_SECRET`. A rehearsal realm uses its own file via `--env-file <path>` (e.g. `.env.lomas.test` pointing `AUTH_REALM_NAME` at `AR_TEST` with that realm's client) — a realm-scoped client cannot create realms, so create the rehearsal realm by importing a sanitised partial-export of the production realm in the admin console. With `AUTH_ADMIN_SECRET` set the script uses `client_credentials` against the **instance realm** — a confidential client whose service account holds `realm-management` → `realm-admin`; without it, the classic username/password flow. No `migrate-wrapper.js` realm swap is needed.
4. **Validate → pilot → import**: `npm run migrate-lomas -- --csv lomas-users.csv [--json lomas-users.json] --dry-run`, then import a handful of team-owned rows and walk forgot-password → login end-to-end, then the full run. Existing realm users count as `skipped-existing` (409), so re-running with a fresher export right before cutover is safe; the script re-authenticates every 4 minutes.
5. **Reports** in `out/`: `results-<timestamp>.csv` (per-email audit trail) and `officials-mapping-sheet.csv` (Part B accounts needing manual role/institution assignment — in v2 the role → institution mapping lives in the model's `Role.meta`, not in per-user data).

Durable keys are stamped as attributes (`legacy_user_id`, `legacy_created_at`, `legacy_submitted_count`, `migrated_from=elomas-v2`, plus `identification_number` / `phone` when the export has them) so a later data migration can link back to accounts — never key data on the IdP subject id (see VUCE-43). The realm must accept them: `unmanagedAttributePolicy` ≠ `DISABLED`, or declare them in the user profile.

## Reasoning principles

1. **Same cluster, schemas-not-databases**: every supported source matches the current eRegistrations convention — one Postgres, two schemas (`cas`, `partc`) in one DB. Reject inputs that contradict this with a clear error.
2. **Fail loud on missing inputs**: never invent ssh hosts, DB names, realm IDs, or admin credentials. Always prompt; never use defaults from a prior country.
3. **Idempotent staging**: every re-run is safe. Don't clobber operator edits to the staged SQL extracts without diff + confirmation.
4. **Country isolation**: country-specific SQL lives under `<country>-sql/`; never run a country's pipeline against another country's extracts.
5. **Verify dumps before seeding**: before invoking `run.sh`, `xzcat sql/cas.sql | head -3` and confirm it's a Postgres dump (`-- PostgreSQL database dump`); same for partc. Catches truncated dumps or wrong-host fetches.
6. **Confirm before destructive remote ops**: fetch (writes to operator workstation only) is safe; seed (writes only to operator workstation, no remote side-effects) is safe; backfill **mutates the running Keycloak** and must always be confirmed by name (`AUTH_URL` + realm) before invocation.

## Out of scope

- Producing or modifying the realm.json itself (use a separate skill or hand-edit).
- Promoting partc.business_role (institution-scoped) assignments to flat realm roles — currently dropped on purpose because the scope semantics differ.
- Migrating MongoDB / camunda / restheart data — only Keycloak realm content.
- Country-specific data-massage steps after migration — the operator runs `backfill-other-name-attrs.sh` (vendored) manually if needed.

## Reference: Cuba

For testing the skill against the canonical first-supported country:
- country arg: `cuba`
- expected repo: `/home/jenkins/cuba-eregistrations` (or `/opt/cuba-eregistrations`)
- realm JSON: `Conf-PREVIEW/mincex/compose/keycloak-realm.json`
- realm name: `CU`
- INSTITUTION_GROUP_ID: `967d3d31-5114-4131-b7e1-f5c652227259` (verifiable in the realm JSON)
- known target Keycloaks: preview at `https://graylog.draftvucecuba.mincex.gob.cu` (temporary host — flip back to `login.draftvucecuba.mincex.gob.cu` once that DNS lands)
- existing extracts: `cuba-sql/` shipped with the skill

For a fresh Cuba run the skill should be able to take you from `fetch cuba` → `seed cuba` → `backfill cuba` with prompts only for the ssh host, DB name (fetch), and target AUTH_URL + admin creds (backfill).
