---
name: cas-to-keycloak-add-service
description: >
  Add the Keycloak service to an eRegistrations instance that currently uses
  CAS authentication. Inserts the keycloak service block into the country's
  docker-compose.yml / docker-stack.yml (docker-compose or swarm shape) and
  the keycloak ACLs + backends into the haproxy.cfg. Idempotent — if a
  keycloak block is already present, surfaces it for the operator and exits
  without changes. Phase 0a in the cas-to-keycloak orchestrator chain.
license: UNCTAD-Internal
compatibility: >
  Requires a country deploy repo following the eRegistrations layout
  (`Conf-<ENV>/compose/<country>/docker-{compose,stack}.yml`,
  `Conf-<ENV>/haproxy/<country>/haproxy.cfg`).
allowed-tools: Read, Write, Edit, Grep, Glob, AskUserQuestion, TodoWrite
metadata:
  version: "1.0.0"
  version-date: "2026-05-22"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<env>/<country>"
  jira: "TOBE-17751"
---

# Add Keycloak Service Skill

You are adding a Keycloak authentication service to an eRegistrations instance. This involves adding the keycloak service definition to the docker-compose/docker-stack file and adding Keycloak routing to the HAProxy configuration.

## STEP 0: Gather Information

Ask the user for:
1. **Environment and country** - e.g., `Conf-LIVE/compose/elsalvador` or `Conf-TEST/compose/cuba`
2. **Keycloak hostname** - e.g., `login.elsalvador.eregistrations.org` (usually `login.<env>.<country>.eregistrations.org`)
3. **System code / Keycloak realm** - e.g., `SV`, `CU`, `LS` (the country code used as Keycloak realm)
4. **Keycloak image version** - default: `unctad/keycloak:2.17`
5. **PostgreSQL host for Keycloak** - usually the same `$SERVICE_HOST` or `postgres_host` used by other services

Then read the existing docker-compose/docker-stack file and the corresponding HAProxy config to understand the current state.

## STEP 1: Check if Keycloak Already Exists

Search the compose file for an existing `keycloak` service definition.

**If Keycloak already exists:**
- Notify the user: "This instance already has a Keycloak service configured. There is nothing to do."
- Show the existing keycloak service definition for reference
- Stop here — do not make any changes

**If Keycloak does NOT exist:** proceed to the next steps.

## STEP 2: Detect Deployment Mode

Read the target file and determine:
- **Docker Compose mode**: File is typically named `docker-compose.yml`, uses `container_name:`, `restart: always`, environment variables use `$VAR_NAME` syntax
- **Docker Swarm mode**: File is typically named `docker-stack.yml`, uses `deploy:` sections with placement/replicas, uses `secrets:` sections, environment variables may use `DOCKER_SECRET:SECRET_NAME` syntax

This distinction affects how secrets are handled and how the keycloak service is defined.

## STEP 3: Add Keycloak Service

Add the keycloak service definition. Use the appropriate template based on deployment mode:

### Docker Compose mode:
```yaml
  keycloak:
    restart: always
    container_name: keycloak
    image: unctad/keycloak:2.17
    ports:
      - "8180:8080"
      - "9003:9000"
    environment:
      HTTP_ADDRESS_FORWARDING: 'true'
      KC_DB: 'postgres'
      KC_DB_URL: 'jdbc:postgresql://postgres_host:5432/keycloak'
      KC_DB_USERNAME: 'keycloak'
      KC_DB_PASSWORD: $KEYCLOAK_DB_PASSWORD
      KC_DB_SCHEMA: 'public'
      KC_HOSTNAME: '<KEYCLOAK_HOSTNAME>'
      KC_HOSTNAME_STRICT_HTTPS: 'true'
      KC_HOSTNAME_STRICT: 'true'
      KEYCLOAK_ADMIN: $KEYCLOAK_ADMIN_USER
      KEYCLOAK_ADMIN_PASSWORD: $KEYCLOAK_ADMIN_USER_PASSWORD
      KEYCLOAK_STATISTICS: all
    extra_hosts:
      - "postgres_host:$SERVICE_HOST"
```

### Docker Swarm mode:
```yaml
  keycloak:
    image: unctad/keycloak:2.17
    ports:
      - "8180:8080"
      - "9003:9000"
    environment:
      HTTP_ADDRESS_FORWARDING: 'true'
      KC_DB: 'postgres'
      KC_DB_URL: 'jdbc:postgresql://postgres_host:5432/keycloak'
      KC_DB_USERNAME: 'keycloak'
      KC_DB_PASSWORD: DOCKER_SECRET:KEYCLOAK_DB_PASSWORD
      KC_DB_SCHEMA: 'public'
      KC_HOSTNAME: '<KEYCLOAK_HOSTNAME>'
      KC_HOSTNAME_STRICT_HTTPS: 'true'
      KC_HOSTNAME_STRICT: 'true'
      KEYCLOAK_ADMIN: DOCKER_SECRET:KEYCLOAK_ADMIN_USER
      KEYCLOAK_ADMIN_PASSWORD: DOCKER_SECRET:KEYCLOAK_ADMIN_USER_PASSWORD
      KEYCLOAK_STATISTICS: all
    extra_hosts:
      - "postgres_host:<SERVICE_HOST_IP>"
    secrets:
      - KEYCLOAK_DB_PASSWORD
      - KEYCLOAK_ADMIN_USER
      - KEYCLOAK_ADMIN_USER_PASSWORD
    networks:
      eregistrations_default: {}
```
And add `KEYCLOAK_DB_PASSWORD`, `KEYCLOAK_ADMIN_USER`, and `KEYCLOAK_ADMIN_USER_PASSWORD` to the top-level `secrets:` section as `external: true`.

**Placement:** Add the keycloak service near the top of the file, after infrastructure services like graylog/mongo but before application services.

## STEP 4: Add Keycloak HAProxy Configuration

Find the HAProxy config at: `<ENV>/haproxy/<country>/haproxy.cfg`

**Add ACLs** (in the frontend section, alongside other ACLs):
```
acl is_auth hdr(Host) -i <KEYCLOAK_HOSTNAME>
acl is_health path_beg -i /health
```

Note: `is_health` may already exist — only add it if it's not already present.

**Add use_backend rules:**
```
use_backend keycloak_health_backend if is_auth is_health
use_backend keycloak if is_auth
```
Note: The health backend rule MUST come before the main keycloak rule.

**Add Keycloak backends:**
```
backend keycloak
    mode http
    acl master_deny_path path_beg -i /auth/realms/<SYSTEM_CODE>/clients-registrations/openid-connect
    acl realm_deny_path path_beg -i /auth/realms/master/clients-registrations/openid-connect
    acl realm_deny_account_path path_beg -i /auth/realms/<SYSTEM_CODE>/account/
    http-request deny if master_deny_path
    http-request deny if realm_deny_path
    http-request deny if realm_deny_account_path
    server keycloak 127.0.0.1:8180

backend keycloak_health_backend
    mode http
    server keycloak_health_backend 127.0.0.1:9003
```

## STEP 5: Summary Report

After completing the addition, provide a summary:

### Properties to add to the server

Tell the user that the following properties need to be configured on the server:

**For Docker Compose environments (add to server's `.env` file):**
```
KEYCLOAK_DB_PASSWORD=<generate-a-secure-password>
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_USER_PASSWORD=<generate-a-secure-password>
```

**For Docker Swarm environments (add as Docker secrets):**
```bash
echo "<generate-a-secure-password>" | docker secret create KEYCLOAK_DB_PASSWORD -
echo "admin" | docker secret create KEYCLOAK_ADMIN_USER -
echo "<generate-a-secure-password>" | docker secret create KEYCLOAK_ADMIN_USER_PASSWORD -
```

### Additional reminders:
- A PostgreSQL database named `keycloak` must be provisioned with user `keycloak` and the password matching `KEYCLOAK_DB_PASSWORD`
- The Keycloak realm still needs to be configured (use `cas-to-keycloak-prepare-realm`).
- If migrating from CAS, the CAS services still need to be removed and app env vars updated (use `cas-to-keycloak-migrate-apps`).
- To pre-seed the `keycloak` Postgres DB with realm + CAS users + groups in one shot before first boot on the target host (avoids a live `--import-realm` and CAS data migration in the cutover window), use `cas-to-keycloak seed` followed by `cas-to-keycloak deploy`.

## IMPORTANT NOTES

- **Never change domain/environment-specific values** (like `$SERVICE_HOST`, `$YOUR_DOMAIN_NAME`) unless specifically asked — only add auth-related configuration
- **Preserve all existing services** — this skill only ADDS Keycloak, it does not remove or modify existing services
- **Preserve formatting** — match the indentation and style of the existing file
- **Use a reference instance** when unsure — compare against a working Keycloak instance in the same environment tier (e.g., use `Conf-TEST/compose/jamaica` as a reference)
