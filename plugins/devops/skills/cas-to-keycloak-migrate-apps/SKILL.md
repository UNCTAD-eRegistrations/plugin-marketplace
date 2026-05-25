---
name: cas-to-keycloak-migrate-apps
description: >
  Flip an eRegistrations country instance's application services from CAS to
  Keycloak. Removes the cas-backend / cas-frontend / partc-backend /
  partc-frontend service blocks from the compose, removes CAS/PARTC ACLs +
  backends from the haproxy, and updates each remaining service's env vars
  (KEYCLOAK_*, AUTH_SERVICE_*, OAUTH_*) to point at the new Keycloak.
  Resolves the two realm UUIDs from realm.json (institutions group +
  eregistrations client scope) — never hardcoded. Diffs against kenya LIVE
  as the canonical reference. Phase 4 in the cas-to-keycloak orchestrator
  chain.
license: UNCTAD-Internal
compatibility: >
  Requires the keycloak service to be already in the compose
  (use `cas-to-keycloak-add-service` first) and a populated realm.json
  alongside (use `cas-to-keycloak-prepare-realm` first).
allowed-tools: Read, Write, Edit, Grep, Glob, AskUserQuestion, TodoWrite
metadata:
  version: "1.0.0"
  version-date: "2026-05-22"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<env>/<country>"
  jira: "TOBE-17751"
---

# Migrate Apps from CAS to Keycloak Skill

You are migrating application services from CAS to Keycloak authentication. This involves removing CAS/PARTC services, removing CAS-related HAProxy configuration, and updating environment variables in all application services to use Keycloak.

**Prerequisites:** The Keycloak service must already be in the compose. Run `cas-to-keycloak-add-service` first if not.

## STEP 0: Gather Information

Ask the user for:
1. **Environment and country** - e.g., `Conf-LIVE/compose/elsalvador` or `Conf-TEST/compose/cuba`
2. **Keycloak hostname** - e.g., `login.elsalvador.eregistrations.org`
3. **System code / Keycloak realm** - e.g., `SV`, `CU`, `LS`
4. **Keycloak institutions group ID** - a UUID for the institutions group in Keycloak (ask the user or use a placeholder variable `$KEYCLOAK_INSTITUTIONS_GROUP_ID`)

Then read the existing docker-compose/docker-stack file and the corresponding HAProxy config to understand the current state.

## STEP 1: Detect Deployment Mode

Read the target file and determine:
- **Docker Compose mode**: File is typically named `docker-compose.yml`, uses `container_name:`, `restart: always`, environment variables use `$VAR_NAME` syntax
- **Docker Swarm mode**: File is typically named `docker-stack.yml`, uses `deploy:` sections with placement/replicas, uses `secrets:` sections, environment variables may use `DOCKER_SECRET:SECRET_NAME` syntax

This distinction affects how secrets are referenced.

## STEP 2: Verify Keycloak Exists

Check that the compose file already has a `keycloak` service defined. If not, warn the user and suggest using the `add-keycloak` skill first.

## STEP 3: Remove CAS Stack Services

Remove these service definitions entirely from the compose file:

### 3.1 `cas-backend`
- Image: `unctad/eregcasbackend:*` or `unctad/casbackend:*`
- Port: 8282
- Remove the entire service block

### 3.2 `cas-frontend`
- Image: `unctad/eregcasfrontend:*` or `unctad/casfrontend:*`
- Port: 4401
- Remove the entire service block

### 3.3 `partc-backend`
- Image: `unctad/eregpartcbackend:*`
- Port: 8383
- Remove the entire service block

### 3.4 `partc-frontend` (may be named `ereg-partc-frontend`)
- Image: `unctad/eregpartcfrontend:*`
- Port: 4400
- Remove the entire service block

### 3.5 Remove CAS/PARTC secrets (Swarm mode only)
If the file has a top-level `secrets:` section, remove these external secrets:
- `CAS_POSTGRES_DB_PASSWORD`
- `CAS_FE_OAUTH_CLIENT_SECRET`
- `PARTC_POSTGRES_DB_PASSWORD`
- `PARTC_FE_OAUTH_CLIENT_SECRET`
- Any other `CAS_*` or `PARTC_*` secrets

## STEP 4: Update Environment Variables in Existing Services

For each service below, make the specified changes. Only modify variables that exist in the current file — some instances may not have all services.

### 4.1 `camunda`
**Add:**
```yaml
KEYCLOAK_ACTIVE: 'true'
KEYCLOAK_URL: http://keycloak:8080
KEYCLOAK_REALM: <SYSTEM_CODE>
KEYCLOAK_RESOURCE: camunda-client
KEYCLOAK_SECRET: $CAMUNDA_OAUTH_CLIENT_SECRET   # or DOCKER_SECRET:CAMUNDA_OAUTH_CLIENT_SECRET in swarm
KEYCLOAK_INSTITUTIONS_GROUP_ID: <resolved from realm.json>
```
**Remove:** Any `CAS_BACKEND` or `PARTC_BACKEND` references.

> Camunda's institution-aware flows need `KEYCLOAK_INSTITUTIONS_GROUP_ID`; without it they don't resolve. Match kenya LIVE.

### 4.2 `bpa-backend`
**Add:**
```yaml
KEYCLOAK_ACTIVE: 'true'
KEYCLOAK_URL: http://keycloak:8080
KEYCLOAK_REALM: <SYSTEM_CODE>
KEYCLOAK_RESOURCE: bpa-backend
KEYCLOAK_SECRET: $BPA_BE_OAUTH_CLIENT_SECRET   # or DOCKER_SECRET:BPA_BE_OAUTH_CLIENT_SECRET in swarm
KEYCLOAK_CLIENT_SCOPE_ID: <resolved from realm.json — see below>
KEYCLOAK_INSTITUTIONS_GROUP_ID: <resolved from realm.json — see below>
```

**Resolving the two UUIDs from realm.json:**
- `KEYCLOAK_INSTITUTIONS_GROUP_ID` = the `id` of the top-level entry in `groups[]` whose `name == "institutions"`.
- `KEYCLOAK_CLIENT_SCOPE_ID` = the `id` of the entry in `clientScopes[]` whose `name == "eregistrations"`.

Both vary per realm — never hardcode.

### 4.3 `bpa-frontend`
**Change:**
- `KEYCLOAK_ACTIVE` from empty/missing to `true`
- `OAUTH_CLIENT_ID` from CAS client (e.g., `bpa-client`) to `bpa-frontend`

**Add:**
```yaml
KEYCLOAK_URL: https://<KEYCLOAK_HOSTNAME>/
KEYCLOAK_REALM: <SYSTEM_CODE>
KEYCLOAK_INSTITUTIONS_GROUP_ID: $KEYCLOAK_INSTITUTIONS_GROUP_ID
```

**Remove:**
- `CAS_URL` (e.g., `https://eid.<domain>/cback/v1.0/`)
- `PARTC_URL` (e.g., `https://partc.<domain>/partc/v1.0/`)
- `OAUTH_SECRET` (not needed with Keycloak for frontend)

### 4.4 `ds-backend`
**Change:**
- `AUTH_SERVICE_TYPE` from `CAS` to `KEYCLOAK`
- `AUTH_SERVICE_BACKEND_URL` from `http://cas-backend:8282` to `http://keycloak:8080`
- `AUTH_SERVICE_PUBLIC_URL` from `https://eid.<domain>/cback/v1.0` to `https://<KEYCLOAK_HOSTNAME>`
- `AUTH_SERVICE_CLIENT_ID` to `ds-client`
- `AUTH_SERVICE_CLIENT_SECRET` to `$DS_OAUTH_CLIENT_SECRET` (or `DOCKER_SECRET:DS_OAUTH_CLIENT_SECRET` in swarm)
- `AUTH_SERVICE_CLIENT_SCOPE` to `openid email profile`

**Add:**
```yaml
AUTH_SERVICE_REALM: <SYSTEM_CODE>
AUTH_SERVICE_INSTITUTION_GROUP_ID: $KEYCLOAK_INSTITUTIONS_GROUP_ID
```

### 4.5 `ds-frontend`
**Change:**
- `KEYCLOAK_ACTIVE` from empty/missing to `true`
- `OAUTH_CLIENT_ID` from CAS client (e.g., `ds-fe`) to `ds-frontend`
- `OAUTH_SECRET` to `null`
- `CAS_URL` to literal `null` (do NOT remove — see note below)
- `PARTC_URL` to literal `null` (do NOT remove — see note below)

**Add:**
```yaml
KEYCLOAK_URL: https://<KEYCLOAK_HOSTNAME>/
KEYCLOAK_REALM: <SYSTEM_CODE>
KEYCLOAK_INSTITUTIONS_GROUP_ID: <resolved from realm.json>
```

> **Critical:** ds-frontend's JS falls back to a hardcoded CAS URL (`/cback/v1.0/cas/spa.html#/?…&client_id=oauth-client-test…`) when `CAS_URL` is *absent*, even with `KEYCLOAK_ACTIVE=true`. Setting the var to literal `null` tells the JS "don't try CAS"; removing it doesn't. Match kenya LIVE.

### 4.6 `mule` (and any country-specific mule like `mule-lesotho`, `mule-elsalvador`)
**Change:**
- `AUTH_SERVICE_TYPE` from `CAS` to `KEYCLOAK`
- `AUTH_SERVICE_URL` from `http://cas-backend:8282/cback/v1.0` to `http://keycloak:8080`

**Add:**
```yaml
AUTH_SERVICE_REALM: <SYSTEM_CODE>
AUTH_RESOURCE: camunda-client
AUTH_SECRET: $CAMUNDA_OAUTH_CLIENT_SECRET   # or DOCKER_SECRET:CAMUNDA_OAUTH_CLIENT_SECRET in swarm
```

### 4.7 `license-registry` / `gdb`
**Change:**
- `AUTH_SERVICE_TYPE_1` from `CAS` to `KEYCLOAK`
- `AUTH_SERVICE_NAME_1` to the realm code (e.g. `CU`, `KE`) — matches kenya pattern, not a freeform display name
- `AUTH_SERVICE_BACKEND_URL_1` from `http://cas-backend:8282` to `http://keycloak:8080`
- `AUTH_SERVICE_PUBLIC_URL_1` from `https://eid.<domain>/cback/v1.0/` to `https://<KEYCLOAK_HOSTNAME>/`
- `AUTH_SERVICE_CLIENT_ID_1` to `gdb-client`
- `AUTH_SERVICE_CLIENT_SECRET_1` to `$GDB_OAUTH_CLIENT_SECRET` (or `DOCKER_SECRET:GDB_OAUTH_CLIENT_SECRET` in swarm)
- `AUTH_SERVICE_CLIENT_SCOPE_1` to `openid email profile`

**Add:**
```yaml
AUTH_SERVICE_REALM_1: <SYSTEM_CODE>
GDB_CLIENT_AUTH_ID_1: 0
```

> gdb's secondary auth-service resolution requires `GDB_CLIENT_AUTH_ID_1`. Match kenya LIVE.

### 4.8 `statistics-backend`
**Change/Add:**
```yaml
AUTH_SERVICE_TYPE: KEYCLOAK
AUTH_SERVICE_BACKEND_URL: http://keycloak:8080
AUTH_SERVICE_REALM: <SYSTEM_CODE>
AUTH_SERVICE_CLIENT_ID: statistics-backend
AUTH_SERVICE_CLIENT_SECRET: $STATISTICS_BE_OAUTH_CLIENT_SECRET
AUTH_SERVICE_CLIENT_SCOPE: openid email profile
```

**Remove:**
- `CAS_API_URL`

### 4.9 `statistics-frontend`
**Change:**
- `KEYCLOAK_ACTIVE` from empty/missing to `true`
- `OAUTH_CLIENT_ID` from CAS client (e.g., `stats-fe`) to `statistics-frontend`

**Add:**
```yaml
KEYCLOAK_URL: https://<KEYCLOAK_HOSTNAME>/
KEYCLOAK_REALM: <SYSTEM_CODE>
```

**Remove:**
- `AUTH_URL` (CAS URL)
- `CAS_BASE_URL`
- `OAUTH_SECRET`

### 4.10 `myaccount` (if present)
**Change:**
- `AUTH_SERVICE_TYPE` from `CAS` to `KEYCLOAK`
- `AUTH_SERVICE_BACKEND_URL` from `http://cas-backend:8282` to `http://keycloak:8080`
- `AUTH_SERVICE_PUBLIC_URL` from CAS public URL to `https://<KEYCLOAK_HOSTNAME>`

**Add:**
```yaml
AUTH_SERVICE_REALM: <SYSTEM_CODE>
```

## STEP 5: Update HAProxy Configuration

Find the HAProxy config at: `<ENV>/haproxy/<country>/haproxy.cfg`

### 5.1 Remove CAS-related configuration

**Remove ACLs:**
```
acl is_cas hdr(Host) -i eid.<domain>
acl cas_path path -i -m beg /cback
```

**Remove use_backend rules:**
```
use_backend cas_backend if is_cas cas_path
use_backend cas_frontend if is_cas
```

**Remove CAS backends:**
```
backend cas_backend
  ... (entire block)

backend cas_frontend
  ... (entire block)
```

### 5.2 Remove PARTC-related configuration

**Remove ACLs:**
```
acl is_partc hdr(Host) -i partc.<domain>
acl partc_path path -i -m beg /partc
```

**Remove use_backend rules:**
```
use_backend partc_backend if partc_path
use_backend partc_frontend if is_partc
```

**Remove PARTC backends:**
```
backend partc_frontend
  ... (entire block)

backend partc_backend
  ... (entire block)
```

### 5.3 Remove CAS token whitelist references
Remove any lines referencing:
- `cas-bot-token-whitelist.lst`
- `cas-external-bot-token-whitelist.lst`

## STEP 6: Verification Checklist

After making all changes, verify:

1. **No CAS references remain**: Search the modified compose file for `cas-backend`, `cas-frontend`, `partc-backend`, `partc-frontend`, `CAS_URL`, `PARTC_URL`, `CAS_BASE_URL`, `AUTH_SERVICE_TYPE=CAS`, `AUTH_SERVICE_TYPE: CAS`
2. **No PARTC references remain**: Search for `partc` in both compose and HAProxy files
3. **Keycloak service exists**: Verify the keycloak service block is present (should already be there from `add-keycloak` skill)
4. **All services updated**: Each service listed in Step 4 that exists in the file has been updated
5. **HAProxy updated**: CAS/PARTC backends removed
6. **Secrets consistency** (swarm mode): All `DOCKER_SECRET:*` references have corresponding entries in the top-level `secrets:` section
7. **Domain consistency**: All URLs use the correct environment domain (no mixed dev/test/live domains)
8. **Port consistency**: No service still references port 8282 (CAS) or 8383 (PARTC)

## STEP 7: Summary Report

After completing the migration, provide a summary:
- Number of services removed
- Number of services modified
- List of new environment variables/secrets that need to be provisioned (if not already done via `cas-to-keycloak-prepare-realm`):
  - `CAMUNDA_OAUTH_CLIENT_SECRET` — Camunda's OAuth client secret in Keycloak
  - `BPA_BE_OAUTH_CLIENT_SECRET` — BPA Backend's OAuth client secret
  - `DS_OAUTH_CLIENT_SECRET` — DS Backend's OAuth client secret
  - `GDB_OAUTH_CLIENT_SECRET` — GDB/License Registry's OAuth client secret
  - `STATISTICS_BE_OAUTH_CLIENT_SECRET` — Statistics Backend's OAuth client secret
  - `KEYCLOAK_INSTITUTIONS_GROUP_ID` — Institutions group UUID from Keycloak
- Reminder to verify the Keycloak realm is configured with matching client secrets (use `cas-to-keycloak-prepare-realm` if not done yet).
- For zero-downtime cutover on the target host: `cas-to-keycloak seed` produces a dump with realm + CAS users + groups in one shot; `cas-to-keycloak deploy` loads it and restarts Keycloak.

## IMPORTANT NOTES

- **Never change domain/environment-specific values** (like `$SERVICE_HOST`, `$YOUR_DOMAIN_NAME`) unless specifically asked — only change auth-related configuration
- **Preserve all non-auth environment variables** — do not modify database connections, mail config, or other unrelated settings
- **Preserve formatting** — match the indentation and style of the existing file
- **Preserve service ordering** — do not reorder services in the compose file
- **Use a reference instance** when unsure — compare against a working Keycloak instance in the same environment tier (e.g., use `Conf-LIVE/compose/colombia` as reference for other LIVE migrations)
