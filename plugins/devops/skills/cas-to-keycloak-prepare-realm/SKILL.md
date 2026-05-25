---
name: cas-to-keycloak-prepare-realm
description: >
  Prepare a Keycloak realm JSON configuration file by substituting all
  `*_PLACEHOLDER` tokens in the canonical starter-conf template with concrete
  values (realm code, domain, OAuth client IDs, generated client-secret
  UUIDs, SMTP config). Writes the realm.json to the target country's
  `Conf-<ENV>/compose/<country>/`. Phase 0b in the cas-to-keycloak
  orchestrator chain.
license: UNCTAD-Internal
compatibility: >
  Requires access to `unctad/eregistrations-starter-conf` (Bitbucket) — via
  local clone or via git over operator-configured creds — for the
  authoritative `scripts/keycloak-realm.template.json`. Falls back to the
  cached template bundled with this skill (may be stale) if neither path
  resolves.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, TodoWrite
metadata:
  version: "1.0.0"
  version-date: "2026-05-22"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<env>/<country>"
  jira: "TOBE-17751"
---

# Prepare Keycloak Realm Skill

You are preparing a Keycloak realm configuration file by substituting placeholders in the canonical starter-conf template, generating client-secret UUIDs, and writing the realm.json to the target country's compose directory.

## STEP 0: Gather Information

The template contains the following placeholders. Ask the user for values you cannot derive:

### Placeholders that require user input:
1. **REALM_PLACEHOLDER** — The Keycloak realm name / system code (e.g., `SV`, `CU`, `LS`, `PS`)
2. **YOUR_DOMAIN_NAME_PLACEHOLDER** — The base domain name (e.g., `elsalvador.eregistrations.org`, `cuba.eregistrations.org`)

### Placeholders that can be derived:
3. **REALM_LOWERCASE_PLACEHOLDER** — Lowercase version of REALM_PLACEHOLDER (e.g., `sv`, `cu`, `ls`)

### Placeholders for secrets (generate UUID values):
4. **BPA_BE_OAUTH_CLIENT_SECRET_PLACEHOLDER** — BPA Backend OAuth client secret
5. **CAMUNDA_OAUTH_CLIENT_SECRET_PLACEHOLDER** — Camunda OAuth client secret
6. **DS_BE_OAUTH_CLIENT_SECRET_PLACEHOLDER** — Display System Backend OAuth client secret
7. **GDB_OAUTH_CLIENT_SECRET_PLACEHOLDER** — GDB/License Registry OAuth client secret
8. **STATS_BE_OAUTH_CLIENT_SECRET_PLACEHOLDER** — Statistics Backend OAuth client secret

For each `*_SECRET_PLACEHOLDER`, generate a random UUID (e.g., using `uuidgen` command).

## STEP 1: Read the Template

The **authoritative** realm template lives at `scripts/keycloak-realm.template.json` inside the `unctad/eregistrations-starter-conf` repository (Bitbucket). Resolve it in this order, asking the operator if ambiguous:

1. If the operator has a local clone of `eregistrations-starter-conf`, ask them for the path (or accept it via env var, e.g. `STARTER_CONF_DIR`). Read `<path>/scripts/keycloak-realm.template.json` from there.
2. Otherwise fetch a fresh copy via `git clone --depth=1` into `/tmp/eregistrations-starter-conf` (operator must have credentials configured). Use that.
3. As a last resort, fall back to `keycloak-realm.json` shipped alongside this skill and warn the operator that it may be stale.

> Do NOT use realm JSON files from tenant-specific deployment repos (e.g. `cuba-eregistrations/Conf-PREVIEW/mincex/compose/keycloak-realm.json` or any country's `Conf-LIVE` artefact) as the template source — those are populated outputs of past runs, not the canonical template.

This is a large JSON file (~2000 lines). Read it in chunks if needed.

## STEP 2: Perform Replacements

Replace ALL occurrences of each placeholder in the JSON file:

1. Replace `REALM_PLACEHOLDER` with the realm name (e.g., `SV`)
2. Replace `REALM_LOWERCASE_PLACEHOLDER` with the lowercase realm name (e.g., `sv`)
3. Replace `YOUR_DOMAIN_NAME_PLACEHOLDER` with the domain name (e.g., `elsalvador.eregistrations.org`)
4. Replace `BPA_BE_OAUTH_CLIENT_SECRET_PLACEHOLDER` with the generated UUID
5. Replace `CAMUNDA_OAUTH_CLIENT_SECRET_PLACEHOLDER` with the generated UUID
6. Replace `DS_BE_OAUTH_CLIENT_SECRET_PLACEHOLDER` with the generated UUID
7. Replace `GDB_OAUTH_CLIENT_SECRET_PLACEHOLDER` with the generated UUID
8. Replace `STATS_BE_OAUTH_CLIENT_SECRET_PLACEHOLDER` with the generated UUID

**IMPORTANT:** Use the `sed` command or similar to perform replacements to avoid issues with the large file. Write the output to the target country's directory, e.g.:
```
<ENV>/compose/<country>/keycloak-realm.json
```

## STEP 3: Validate

After replacements, verify:
1. No `_PLACEHOLDER` strings remain in the output file
2. The JSON is valid (use `python3 -m json.tool` or similar to validate)
3. All secret values are unique UUIDs

## STEP 4: Output Generated Secrets

Present the generated secret values to the user in a clear format. These secrets must be configured on the server.

**For Docker Compose environments (add to server's `.env` file):**
```
BPA_BE_OAUTH_CLIENT_SECRET=<generated-uuid>
CAMUNDA_OAUTH_CLIENT_SECRET=<generated-uuid>
DS_OAUTH_CLIENT_SECRET=<generated-uuid>
GDB_OAUTH_CLIENT_SECRET=<generated-uuid>
STATISTICS_BE_OAUTH_CLIENT_SECRET=<generated-uuid>
```

**For Docker Swarm environments (create as Docker secrets):**
```bash
echo "<generated-uuid>" | docker secret create BPA_BE_OAUTH_CLIENT_SECRET -
echo "<generated-uuid>" | docker secret create CAMUNDA_OAUTH_CLIENT_SECRET -
echo "<generated-uuid>" | docker secret create DS_OAUTH_CLIENT_SECRET -
echo "<generated-uuid>" | docker secret create GDB_OAUTH_CLIENT_SECRET -
echo "<generated-uuid>" | docker secret create STATISTICS_BE_OAUTH_CLIENT_SECRET -
```

Ask the user which environment type they are using (Docker Compose or Docker Swarm) and show the appropriate format.

### Important mapping note:
The placeholder names in the realm JSON map to environment variable names used in the docker-compose/docker-stack files as follows:
| Realm JSON placeholder | Docker env variable / secret name |
|---|---|
| `BPA_BE_OAUTH_CLIENT_SECRET_PLACEHOLDER` | `BPA_BE_OAUTH_CLIENT_SECRET` |
| `CAMUNDA_OAUTH_CLIENT_SECRET_PLACEHOLDER` | `CAMUNDA_OAUTH_CLIENT_SECRET` |
| `DS_BE_OAUTH_CLIENT_SECRET_PLACEHOLDER` | `DS_OAUTH_CLIENT_SECRET` |
| `GDB_OAUTH_CLIENT_SECRET_PLACEHOLDER` | `GDB_OAUTH_CLIENT_SECRET` |
| `STATS_BE_OAUTH_CLIENT_SECRET_PLACEHOLDER` | `STATISTICS_BE_OAUTH_CLIENT_SECRET` |

## STEP 5: Realm Import Reminder

Remind the user:
- The generated `keycloak-realm.json` file needs to be imported into Keycloak
- This can be done via: Keycloak Admin Console > Create Realm > Import JSON
- Or by mounting the file as a volume in the keycloak service and using the `--import-realm` flag
- After import, the "Institutions" group must be created manually in Keycloak and its UUID should be noted as `KEYCLOAK_INSTITUTIONS_GROUP_ID`
- For cutover pre-seeding (realm + CAS users + groups in one dump): use `cas-to-keycloak seed` followed by `cas-to-keycloak deploy`.

## IMPORTANT NOTES

- **Do NOT modify the template file** — always write the output to the target country's directory
- **All secret UUIDs must be unique** — generate a fresh UUID for each placeholder
- **Preserve JSON structure** — ensure the output is valid JSON after all replacements
