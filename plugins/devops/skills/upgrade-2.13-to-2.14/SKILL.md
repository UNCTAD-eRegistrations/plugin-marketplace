---
name: upgrade-2.13-to-2.14
description: >
  Upgrade a single eRegistrations instance under
  `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml` from 2.13 to 2.14, where
  `<env>` is one of dev/test/preview/prelive/live. This is the largest mechanical
  step in the chain: bumps every `unctad/<service>:$<VAR>_VER` (or pinned
  semver) image to `:RC` (the platform tag introduced in 2.14), drops the legacy
  Keycloak `/auth` path from internal and public URLs across `bpa-frontend`,
  `bpa-backend`, `camunda`, `mule`, `ereg-cms-frontend`, `statistics-backend`,
  `statistics-frontend`, renames `MONGO_URI` → `RH_MONGO_URI` on `restheart`,
  bumps `EREGISTRATIONS_VERSION` and `BUILD_TYPE` to the values the rest of the
  chain expects (non-dev: `2.14` / `RC`; dev: `DEV` / `DEV`). **Keycloak Quarkus
  migration is mandatory** — when Wildfly env vars are detected on the keycloak
  service block, the skill replaces them with the Quarkus block (`KC_DB_*`,
  `KC_HOSTNAME*`) without prompting; this is a hard requirement of the 2.14
  baseline, not an optional cleanup. Conditionally adds an `opensearch-node1`
  service block plus repoints `GRAYLOG_ELASTICSEARCH_HOSTS` from
  `$SERVICE_HOST:9200` to `opensearch-node1:9200` when the graylog service
  still references the legacy Elasticsearch endpoint. Strict mode — aborts on anything unexpected.
  Env-aware anomaly thresholds. LIVE invocations require a retype-country
  confirmation rail before commit (skipped in chain mode — the orchestrator
  does it once up front). Two invocation modes: standalone (creates branch,
  pushes, opens PR) and chain mode (`CHAIN_MODE=1 CHAIN_BRANCH=<name>`,
  commits to orchestrator-managed branch, no push, no PR). Swarm-stack
  (docker-stack.yml) shape only — instances still on docker-compose.yml must
  run /docker-swarm-migration first.
license: UNCTAD-Internal
compatibility: Run from the eregistrations-v4 working tree on master (standalone) or on the orchestrator-supplied chain branch (chain mode), with a clean tracked tree. Requires an authenticated CLI for the host VCS in standalone mode (gh for GitHub origins; Bitbucket origins skip CLI PR creation and print a manual link).
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git *), Bash(gh *), Bash(grep *), Bash(test *), Bash(ls *), Bash(basename *), Bash(dirname *), AskUserQuestion
metadata:
  version: "1.0.0"
  version-date: "2026-05-04"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[<country>] [<env>] [BACKUP_CONFIRMED=1] [CHAIN_MODE=1 CHAIN_BRANCH=<name>]"
  jira: "TOBE-17814"
---

# Upgrade an eRegistrations instance from 2.13 to 2.14

You are performing the eRegistrations 2.13 → 2.14 upgrade of a single instance. The target file is `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml`, where `<env>` ∈ {dev, test, preview, prelive, live}. This is **the largest mechanical step in the chain**: 2.14 introduced the `:RC` tag channel for every `unctad/*` image (replacing per-service `$<VAR>_VER` env-var pinning) and changed how Keycloak is integrated (drop `/auth` path; optionally migrate the keycloak service from Wildfly to Quarkus; optionally add `opensearch-node1` and repoint Graylog).

The historical 2.13 → 2.14 commits varied across countries — Lomas (`c99340f9`) did the full Keycloak Quarkus + Opensearch migration in one shot; Mali (`9f900cc8`) bumped images and URLs but kept Wildfly Keycloak; DEV instances (`0b39d556`) only bumped `EREGISTRATIONS_VERSION`. This skill encodes the **superset** with conditional rules: required transformations apply everywhere, conditional blocks (Keycloak Quarkus, Opensearch) apply only when their respective preconditions are detected.

Operate in **strict mode**: any anomaly pauses for explicit user input, with `abort` as the default.

The skill is invoked as `/upgrade-2.13-to-2.14` with optional positional args (see *Arguments* below). It is also routed to by the `upgrade-eregistrations-instance` orchestrator when it detects a swarm-stack instance whose `unctad/*` images use `$<VAR>_VER` interpolation or pinned semver tags **and** whose `EREGISTRATIONS_VERSION` is `2.13` (or `$EREGISTRATIONS_VERSION` env-var-interpolated).

When the upgrade is approved, **standalone mode** commits on a fresh branch `chore/upgrade-<env>-<country>-2.13-to-2.14`, pushes it, and opens a pull request. **Chain mode** (orchestrator-invoked) skips branch creation, push, and PR — it commits a single step-scoped commit on the orchestrator-managed branch and returns.

## Arguments

The skill accepts up to four positional/flag tokens, whitespace-separated, in any order:

- `<env>` — one of `dev`, `test`, `preview`, `prelive`, `live` (lowercase).
- `<country>` — the folder name under `Conf-<UPPER_ENV>/compose/`, e.g. `lomasdezamora`, `mali`, `cuba`.
- `BACKUP_CONFIRMED=1` — flag. Suppresses the STEP 1.5 backup prompt.
- `CHAIN_MODE=1` — flag. Switches to chain mode: orchestrator owns branch/push/PR. Requires `CHAIN_BRANCH` to also be set.
- `CHAIN_BRANCH=<branch>` — the branch the orchestrator already created and switched to. Sub-skill commits here.

Tokenizer rules:
- Whitespace-split.
- For each token: if it matches `^[A-Z_]+=.+$`, treat as a `KEY=VALUE` flag and store; if lowercased it equals one of the env keywords, set `<env>`; otherwise it's `<country>`.
- Unknown `KEY=VALUE` flags warn ("Unknown flag `<token>`, ignoring.") but do not abort.

Missing positional values trigger AskUserQuestion prompts in STEP 1. If `<country>` was supplied via args, validation is single-shot (no retry loop).

Env → directory mapping:

| `<env>` | `<UPPER_ENV>` | Directory |
|---|---|---|
| dev | `DEV` | `Conf-DEV/compose/` |
| test | `TEST` | `Conf-TEST/compose/` |
| preview | `PREVIEW` | `Conf-PREVIEW/compose/` |
| prelive | `PRELIVE` | `Conf-PRELIVE/compose/` |
| live | `LIVE` | `Conf-LIVE/compose/` |

## Scope (intentionally narrow)

- **In scope:** a single `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml` whose `unctad/*` images are pinned via `$<SERVICE>_VER` env-var interpolation **or** pinned semver tags (e.g. `:5.17.7-0`, `:1.260.10`) **and** whose `EREGISTRATIONS_VERSION` is `2.13` or `$EREGISTRATIONS_VERSION`.
- **Out of scope:** instances still on `docker-compose.yml` (refuse and point at `/docker-swarm-migration`), Coolify-managed instances, simultaneous upgrades of multiple instances, version pairs other than 2.13 → 2.14.

If the target instance has only `docker-compose.yml` (no `docker-stack.yml`), abort with: "`<country>` is still on docker-compose.yml. Run `/docker-swarm-migration` first to convert the instance to swarm, then re-run this skill."

## STEP 0: Pre-flight git checks

Before doing anything else, verify the repository is in a state where the upgrade can proceed.

**Standalone mode** (no `CHAIN_MODE=1`):

1. **Working tree is a git repo at the repo root.** Run `git rev-parse --show-toplevel`. If it errors, abort: "Not in a git working tree."
2. **Current branch is `master`.** Run `git rev-parse --abbrev-ref HEAD`. If not `master`, abort: "Refusing to run on branch <branch>. Switch to master first."
3. **No staged or modified tracked files.** Run `git status --porcelain --untracked-files=no`. If non-empty, abort and print: "There are staged or modified tracked files. Resolve the changes below first." followed by the same output.
4. **Origin host detected, CLI authenticated.** If the orchestrator already set `HOST` in conversation state, reuse it. Otherwise resolve it now: `git remote get-url origin`.
   - URL contains `github.com` → set `HOST=github`. Run `gh auth status`. If it errors, abort: "GitHub CLI (gh) is not installed or not authenticated. Install gh and run `gh auth login` before re-running this skill."
   - URL contains `bitbucket.org` → set `HOST=bitbucket`. The skill will skip CLI-based PR creation and print a manual Bitbucket URL after push.
   - Otherwise abort: "Unsupported origin host: <url>."
5. **`master` is in sync with origin.** Run `git pull --ff-only origin master`. On failure, abort and print the git error verbatim.

**Chain mode** (`CHAIN_MODE=1`):

1. **Working tree is a git repo at the repo root.** Same as standalone.
2. **Currently on the orchestrator-supplied chain branch.** Run `git rev-parse --abbrev-ref HEAD`. If it doesn't equal `<CHAIN_BRANCH>`, abort: "Chain mode expected branch `<CHAIN_BRANCH>` but on `<actual>`. Orchestrator state inconsistent."
3. **No staged or modified tracked files.** Same as standalone.
4. **Skip host detection and pull** — orchestrator did both already.

When pre-flight passes, proceed to STEP 1.

## STEP 1: Resolve env, country, target

1. **Resolve `<env>`.** If supplied via args, use it. Otherwise AskUserQuestion: "Which environment? dev / test / preview / prelive / live." Lowercase, validate. Two-strikes invalid → abort.

2. **Compute `<UPPER_ENV>`** from the table above.

3. **Verify eregistrations-v4 shape.** Run `test -d "Conf-<UPPER_ENV>/compose"`. If missing, abort: "`Conf-<UPPER_ENV>/compose/` does not exist."

4. **Find candidates.** Candidates are docker-stack.yml files that have `EREGISTRATIONS_VERSION=2.13` (literal or `$EREGISTRATIONS_VERSION` interpolated) **and** `unctad/*` images using `$<VAR>_VER` or pinned semver tags (i.e. *not* `:RC`/`:BETA`/`:2.17`/`:2.18`):

   ```bash
   for f in Conf-<UPPER_ENV>/compose/*/docker-stack.yml; do
     if grep -qE 'EREGISTRATIONS_VERSION=["'"'"']?(2\.13|\$EREGISTRATIONS_VERSION)' "$f" \
        && grep -qE 'image:[[:space:]]*unctad/[^:[:space:]]+:(\$[A-Z_]+_VER|[0-9]+\.[0-9]+)' "$f"; then
       echo "$(basename "$(dirname "$f")")"
     fi
   done | sort
   ```

5. **No candidates found.** If zero lines: "Nothing to upgrade — no `Conf-<UPPER_ENV>` swarm-stack instance has `EREGISTRATIONS_VERSION=2.13` on `unctad/*:$VAR_VER`-style images. Note: instances still on `docker-compose.yml` must run `/docker-swarm-migration` first." Exit 0.

6. **Resolve `<country>`.**
   - If supplied via args: validate against candidates list. Invalid → single-shot abort.
   - If not supplied: list candidates, ask "Which `<env>` instance? Type the country folder name." Two-strikes invalid → abort.

7. **Confirm target file exists.** Compute `TARGET=Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml`. Run `test -f "$TARGET"`. If missing, abort.

8. Save state for the rest of the run: `<env>`, `<UPPER_ENV>`, `<country>`, `TARGET`.

## STEP 1.5: Backup confirmation

If `BACKUP_CONFIRMED=1` was passed (orchestrator-routed and chain-mode invocations always set this), skip this step.

Otherwise AskUserQuestion: "Is the current state of `<env>`/`<country>` recoverable (snapshot, prior tag, manual export)? (y/N)"

- `y` (case-insensitive) → STEP 2.
- `N` or empty → abort: "Resolve backups before re-running."

## STEP 2: Pre-transformation strict scan

Compute env-aware anomaly thresholds. The 2.13 baseline used inconsistent values for these env vars (DEV instances often had `BUILD_TYPE=$BPA_FRONTEND_VER` and `EREGISTRATIONS_VERSION=$EREGISTRATIONS_VERSION` interpolation, non-dev had literal `LIVE` / `2.13`). The skill normalizes the post-state to the values the rest of the chain (2.14 → 2.15 onward) expects:

| `<env>` | accepted source `BUILD_TYPE` (2.13) | accepted source `EREGISTRATIONS_VERSION` (2.13) | post-state (2.14) |
|---|---|---|---|
| dev | any of `DEV`, `$BPA_FRONTEND_VER`, `LIVE` | any of `DEV`, `$EREGISTRATIONS_VERSION`, `2.13` | `BUILD_TYPE=DEV`, `EREGISTRATIONS_VERSION=DEV` |
| test, preview, prelive, live | `LIVE` | `2.13` or `$EREGISTRATIONS_VERSION` | `BUILD_TYPE=RC`, `EREGISTRATIONS_VERSION=2.14` |

Print: "Env: `<env>`. Accepted source `BUILD_TYPE` ∈ <accepted_BT_set>. Accepted source `EREGISTRATIONS_VERSION` ∈ <accepted_EV_set>. Post-state: `BUILD_TYPE=<post_BT>`, `EREGISTRATIONS_VERSION=<post_EV>`."

Scan `<TARGET>` for **anomalies**. Each pauses for `(c)ontinue / (s)kip / (a)bort` (default abort, empty = abort). `c` applies the relevant rule to this occurrence; `s` leaves untouched (remembered for the kind); `a` exits without edits.

**Anomaly kinds:**

1. **Already-2.14+ unctad image tags.** Any `unctad/*:RC`, `:BETA`, `:2.17`, `:2.18` line. Suggests partial prior upgrade. Default abort.

2. **Already-2.14 `EREGISTRATIONS_VERSION`.** Any `EREGISTRATIONS_VERSION=2.14` line. Default abort.

3. **Unexpected `EREGISTRATIONS_VERSION` value.** Any `EREGISTRATIONS_VERSION=` line whose RHS (after stripping quotes) is not in the accepted-source set for `<env>` and not `2.14` (covered above).

4. **Unexpected `BUILD_TYPE` value.** Any `BUILD_TYPE=` line whose RHS (after stripping quotes) is not in the accepted-source set for `<env>` and not the post-state value.

5. **Unexpected unctad image tag.** A line matching `image:\s*unctad/[^:]+:[^ ]+` whose tag is not in `{$<VAR>_VER, pinned-semver, DEV}`. Country-specific images on `:DEV` (e.g. `unctad/mule3-mali:DEV`) are expected — typical answer `s`.

6. **Missing expected service blocks.** If the file lacks `bpa-frontend:`, `restheart:`, or `keycloak:` service blocks. Print missing names and pause — typical `s` for unusual variants.

If no anomalies: "No anomalies. Detecting conditional preconditions." and proceed.

### Precondition detection

Before applying transformations, detect which Keycloak shape and which Graylog shape the file is in:

- **`KEYCLOAK_QUARKUS_NEEDED`**: true if the `keycloak:` service block contains any of:
  - `PROXY_ADDRESS_FORWARDING`
  - `DB_VENDOR=POSTGRES`
  - `DB_ADDR=`
  - `DB_DATABASE=`
  - `DB_USER=`
  - `DB_PASSWORD=`

  False only if all of those are absent **and** the block already contains Quarkus markers (`KC_DB`, `KC_HOSTNAME`, etc.) — meaning Keycloak was migrated independently before this skill ran. Mixed (Wildfly *and* Quarkus markers present) → raise as anomaly, default abort.

  **Important:** Quarkus migration on the keycloak service block is a **hard requirement** of the 2.14 baseline — the next sub-skills in the chain (`/upgrade-2.14-to-2.15` onward) and the runtime `unctad/keycloak:RC` image at 2.14+ both assume Quarkus. The skill applies the migration without prompting when `KEYCLOAK_QUARKUS_NEEDED=true`. If you don't want it applied, abort the whole skill and migrate Keycloak manually first.

- **`OPENSEARCH_NEEDED`**: true if the `graylog:` service block contains `GRAYLOG_ELASTICSEARCH_HOSTS:` referencing `$SERVICE_HOST:9200` (or any host that is *not* `opensearch-node1:9200`) AND the file does **not** contain a top-level `opensearch-node1:` service. Otherwise false.

Print the booleans: "Keycloak Quarkus migration: <yes|no>. Opensearch addition: <yes|no>."

## STEP 3: Apply the required transformations

Edit `<TARGET>` in place. Preserve indentation and line endings exactly. Apply rules in order; each operates on the file produced by the previous.

### Image tag rules

**Rule 1 — Bump `unctad/<service>:$<SERVICE>_VER` to `unctad/<service>:RC`.**

For every line matching `^(\s*)image:\s*unctad/([^:\s]+):\$[A-Z_]+_VER\s*$`, replace the tag portion with `:RC`. Keep leading whitespace and image name verbatim.

**Rule 2 — Bump `unctad/<service>:<pinned-semver>` to `unctad/<service>:RC`.**

For every line matching `^(\s*)image:\s*unctad/([^:\s]+):([0-9]+\.[0-9]+(\.[0-9]+)?(-[0-9]+)?)\s*$` where `<service>` is **not** in the country-image deny-list (`mule3-<country>`, `mule4-<country>`, `cashier-<country>`), replace the tag with `:RC`.

**Rule 3 — License-registry / GDB special case.**

If a line matches `image:\s*unctad/license-registry:` (any tag), the canonical 2.14 RC tag is `:RC` (same as other services). Apply Rule 1 / Rule 2. Note that 2.15 → 2.16 will later move this specific service to `:DEV` — that is out of scope for this skill.

**Rule 4 — Country-image and floating-tag services left alone.**

Skip lines matching `unctad/(mule3-|mule4-|cashier-)`. Their `:DEV` (or other) tags follow a country-specific lifecycle. Skip `unctad/statistics-backend:DEV` and `unctad/ds-frontend:DEV` if present (these floating-tag services are introduced post-2.14 and shouldn't appear on a 2.13 baseline; if they do, raise an anomaly via STEP 2).

### Keycloak URL rules (always apply)

These rules drop the `/auth` path segment that Wildfly Keycloak required and Quarkus Keycloak doesn't. Apply across all services that talk to Keycloak.

**Rule 5 — Internal `KEYCLOAK_URL` drop `/auth`.**

For every env-list item matching `KEYCLOAK_URL=http://keycloak:8080/auth` (with or without quotes, in any service's `environment:` list — typically `camunda`, `bpa-backend`, `bpa-frontend` (internal variant), `mule`, `js-assistant`), strip the `/auth` suffix → `KEYCLOAK_URL=http://keycloak:8080`.

**Rule 6 — Internal `AUTH_SERVICE_URL` drop `/auth`.**

Same shape as Rule 5 but for `AUTH_SERVICE_URL=http://keycloak:8080/auth` (typically on `mule`).

**Rule 7 — Internal `AUTH_SERVICE_BACKEND_URL` drop `/auth`.**

For `AUTH_SERVICE_BACKEND_URL=http://keycloak:8080/auth` (typically on `ereg-cms-frontend`, `statistics-backend`), strip `/auth`.

**Rule 8 — Public `KEYCLOAK_URL` drop `/auth/`.**

For public-facing variants matching `KEYCLOAK_URL=https://login.$YOUR_DOMAIN_NAME/auth/` (with the trailing slash; typically on `bpa-frontend`, `statistics-frontend`), strip `/auth/` → `KEYCLOAK_URL=https://login.$YOUR_DOMAIN_NAME/`.

**Rule 9 — Public `AUTH_SERVICE_PUBLIC_URL` drop `/auth`.**

For `AUTH_SERVICE_PUBLIC_URL=https://login.$YOUR_DOMAIN_NAME/auth` (typically on `ereg-cms-frontend`), strip `/auth` (no trailing slash variant).

For each rule, log how many lines matched. If a rule expected matches in a service block that is present but matches zero, raise it as an anomaly (the service may have been customized).

### RestHeart rule

**Rule 10 — Rename `MONGO_URI` to `RH_MONGO_URI` on `restheart`.**

Locate the `restheart:` service block. For the env-list item matching `MONGO_URI=<value>` (with or without quotes), replace just the var name with `RH_MONGO_URI`. Keep `<value>` and quoting style intact. If both `MONGO_URI` and `RH_MONGO_URI` exist already, raise an anomaly.

### Env-var rules on `bpa-frontend`

The post-state values are env-aware (per the table at the top of STEP 2):

- Non-dev envs (`test`, `preview`, `prelive`, `live`): post-state `EREGISTRATIONS_VERSION=2.14`, `BUILD_TYPE=RC`.
- Dev env: post-state `EREGISTRATIONS_VERSION=DEV`, `BUILD_TYPE=DEV`.

**Rule 11 — Normalize `EREGISTRATIONS_VERSION` on bpa-frontend.**

Replace any list item whose stripped content is `- EREGISTRATIONS_VERSION=<accepted_source>` (where `<accepted_source>` is any value in the accepted-source set for `<env>` — `2.13` / `$EREGISTRATIONS_VERSION` for non-dev, `DEV` / `$EREGISTRATIONS_VERSION` / `2.13` for dev), or quoted variants, with `- EREGISTRATIONS_VERSION=<post_EV>` (the env-specific post-state value). Preserve original indentation, dash, and quoting style.

**Rule 12 — Normalize `BUILD_TYPE` on bpa-frontend.**

Replace any list item whose stripped content is `- BUILD_TYPE=<accepted_source>` (where `<accepted_source>` is any value in the accepted-source set for `<env>` — `LIVE` for non-dev, `DEV` / `$BPA_FRONTEND_VER` / `LIVE` for dev), or quoted variants, with `- BUILD_TYPE=<post_BT>`.

### Env-var rules on `ereg-cms-frontend` (DS-side service)

**Rule 13 — Normalize `EREGISTRATIONS_VERSION` and `BUILD_TYPE` on ereg-cms-frontend.**

Locate the `ereg-cms-frontend:` service block. Apply the same replacements as Rule 11 and Rule 12 inside its `environment:` list. If neither var is present, append `- "EREGISTRATIONS_VERSION=<post_EV>"` and `- "BUILD_TYPE=<post_BT>"` (matching the surrounding double-quoted style).

## STEP 3.5: Apply Keycloak Quarkus migration (mandatory when `KEYCLOAK_QUARKUS_NEEDED`)

Keycloak Quarkus migration is a **hard requirement** of the 2.14 baseline — it is not optional and there is no opt-out prompt.

If `KEYCLOAK_QUARKUS_NEEDED=false` (Keycloak was already migrated to Quarkus before this skill ran), skip this entire step.

Otherwise:

1. **Locate the `keycloak:` service block** at top-level indent (2 spaces).

2. **Replace the entire `environment:` list** with the canonical Quarkus block. The before/after shapes:

   **Before (Wildfly):**

   ```yaml
     keycloak:
       restart: always
       container_name: keycloak
       image: unctad/keycloak:RC          # already bumped by Rule 1 by this point
       ports:
         - "8180:8080"
         - "9990:9990"
       environment:
         - "PROXY_ADDRESS_FORWARDING=true"
         - "DB_VENDOR=POSTGRES"
         - "DB_ADDR=$SERVICE_HOST"
         - "DB_DATABASE=$KEYCLOAK_POSTGRES_DB_NAME"
         - "DB_USER=$KEYCLOAK_POSTGRES_DB_USER"
         - "DB_PASSWORD=$KEYCLOAK_POSTGRES_DB_PASSWORD"
         - "KEYCLOAK_STATISTICS=all"
   ```

   **After (Quarkus):**

   ```yaml
     keycloak:
       restart: always
       container_name: keycloak
       image: unctad/keycloak:RC
       ports:
         - "8180:8080"
         - "9990:9990"
       environment:
         - "HTTP_ADDRESS_FORWARDING=true"
         - "KC_DB=postgres"
         - "KC_DB_URL=jdbc:postgresql://postgres_host:5432/keycloak"
         - "KC_DB_USERNAME=$KEYCLOAK_POSTGRES_DB_USER"
         - "KC_DB_PASSWORD=$KEYCLOAK_POSTGRES_DB_PASSWORD"
         - "KC_DB_SCHEMA=public"
         - "KC_HOSTNAME=login.$YOUR_DOMAIN_NAME"
         - "KC_HOSTNAME_STRICT_HTTPS=true"
         - "KC_HOSTNAME_STRICT=true"
         - "KEYCLOAK_STATISTICS=all"
         - "KC_LOG_LEVEL=INFO"
       extra_hosts:
         - "postgres_host:$SERVICE_HOST"
   ```

3. **Country-specific risks to surface before applying.** Print:

   ```
   Applying mandatory Keycloak Quarkus migration. The template hardcodes:
   - DB name: keycloak (your instance may use a different name via $KEYCLOAK_POSTGRES_DB_NAME)
   - Hostname: login.$YOUR_DOMAIN_NAME (template; expanded at deploy time)
   - Log level: INFO
   - Strict HTTPS hostname: enabled

   Existing $KEYCLOAK_POSTGRES_DB_NAME usage will be lost — the JDBC URL hard-codes /keycloak.
   If your instance uses a non-default DB name, abort now (Ctrl-C / answer "a" to the next anomaly), migrate Keycloak manually, and re-run this skill.
   ```

   No `(y/N)` prompt — the migration is required for the 2.14 baseline. The user-facing escape hatch is to abort the whole skill (e.g. by raising any anomaly in STEP 2 with `a`, or by Ctrl-C) and migrate Keycloak manually before re-running.

4. **Apply the replacement.** Replace the entire `environment:` list of the `keycloak:` block with the Quarkus list above. If an `extra_hosts:` block does not already exist on `keycloak:`, append it after the new `environment:` block. If `extra_hosts:` exists with `postgres_host` already in it, leave it alone. If it exists without `postgres_host`, add the `postgres_host:$SERVICE_HOST` entry to the existing list.

## STEP 3.6: Apply Opensearch migration (only if `OPENSEARCH_NEEDED`)

If `OPENSEARCH_NEEDED=false`, skip this entire step.

Otherwise:

1. **Repoint Graylog at Opensearch.** In the `graylog:` service block:
   - Replace `GRAYLOG_ELASTICSEARCH_HOSTS: http://$SERVICE_HOST:9200` with `GRAYLOG_ELASTICSEARCH_HOSTS: http://opensearch-node1:9200`. Preserve the mapping-style key (`KEY: value`) or list-style (`- KEY=value`) as found.
   - Remove the `extra_hosts:` entry `- "elastic_host:$SERVICE_HOST"` if present. If `extra_hosts:` becomes empty, remove the empty `extra_hosts:` key too.

2. **Insert the `opensearch-node1` service block.** Add the following block immediately after the `graylog:` service (before the next service definition), matching the prevailing 2-space top-level indent:

   ```yaml
     opensearch-node1:
       image: opensearchproject/opensearch:2.12.0
       container_name: opensearch-node1
       environment:
         - plugins.security.disabled=true
         - cluster.name=opensearch-cluster
         - node.name=opensearch-node1
         - discovery.seed_hosts=opensearch-node1
         - cluster.initial_cluster_manager_nodes=opensearch-node1
         - bootstrap.memory_lock=true
         - "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m"
         - OPENSEARCH_INITIAL_ADMIN_PASSWORD=$OPENSEARCH_ADMIN_PASSWORD
         - path.repo=/opt/os_backup
       ulimits:
         memlock:
           soft: -1
           hard: -1
         nofile:
           soft: 65536
           hard: 65536
       volumes:
         - /opt/volumes/opensearch/data:/usr/share/opensearch/data
         - /opt/volumes/opensearch/os_backup:/opt/os_backup
       networks:
         - graylog_network
   ```

3. **Country-specific risks to surface.** Before writing the block, print:

   ```
   Opensearch service block is about to be added. The template hardcodes:
   - Image: opensearchproject/opensearch:2.12.0
   - Volume paths: /opt/volumes/opensearch/{data,os_backup} on the host
   - Network: graylog_network (must already exist in the file's `networks:` section)
   - Required env: $OPENSEARCH_ADMIN_PASSWORD (must be set in the deployment env)

   Verify the volume paths and the graylog_network reference for <country>. After deploy, you will need to backfill Graylog indices into Opensearch via a one-time data migration outside this skill's scope.
   ```

   AskUserQuestion: "Add Opensearch block as-is? (y/N — N skips this step and you do it manually)".

   - `y` → insert the block; ensure `graylog_network` is referenced in the file's top-level `networks:` section (raise an anomaly if not).
   - `N` or empty → skip. Leave Graylog pointing at the legacy ES endpoint. Print: "Opensearch block not added. Graylog will continue to write to `$SERVICE_HOST:9200`. Manual data migration required separately." Continue with STEP 4.

## STEP 4: Post-transformation safety scan

After applying the rules, scan the modified `<TARGET>` for any remaining surprises that would suggest the upgrade is incomplete:

1. `grep -nE 'image:[[:space:]]*unctad/[^:]+:\$[A-Z_]+_VER' "$TARGET" || true` — should be empty (Rule 1 catches all `$VAR_VER` images).
2. `grep -nE 'image:[[:space:]]*unctad/[^:]+:[0-9]+\.[0-9]+' "$TARGET" || true` — should match only country-image services (mule3-/mule4-/cashier-) if any. Any other match is a missed bump.
3. `grep -n 'EREGISTRATIONS_VERSION=2\.13' "$TARGET" || true` — should be empty.
4. `grep -n 'EREGISTRATIONS_VERSION=\$EREGISTRATIONS_VERSION' "$TARGET" || true` — should be empty.
5. `grep -nE 'KEYCLOAK_URL=http://keycloak:8080/auth' "$TARGET" || true` — should be empty.
6. `grep -nE 'AUTH_SERVICE_(URL|BACKEND_URL)=http://keycloak:8080/auth' "$TARGET" || true` — should be empty.
7. `grep -n 'login\.\$YOUR_DOMAIN_NAME/auth' "$TARGET" || true` — should be empty.
8. `grep -n '^\s*-\s*"\?MONGO_URI=' "$TARGET" || true` — should be empty (Rule 10 renamed it).
9. If `KEYCLOAK_QUARKUS_NEEDED=true` and the user said `y`, also check: `grep -nE '"?(PROXY_ADDRESS_FORWARDING|DB_VENDOR|DB_ADDR|DB_DATABASE|DB_USER|DB_PASSWORD)=' "$TARGET" || true` — should be empty.

For every match, present it as an anomaly with `(c)ontinue / (s)kip / (a)bort`. `a` rolls back via `git restore -- "$TARGET"` and exits.

## STEP 5: Diff review

Show diff: `git --no-pager diff --no-color -- "$TARGET"`. Print verbatim. Note the diff will be **large** — typically 60–150 lines depending on conditional rules — much bigger than later step skills.

**Standalone mode**: AskUserQuestion: "Commit, push, and open PR? (y/N)". `y` → STEP 5.5 (LIVE only) → STEP 6. Anything else → `git restore -- "$TARGET"` and exit cleanly.

**Chain mode**: skip the y/N prompt — the orchestrator already gathered intent. Proceed straight to STEP 6 (commit only). The orchestrator handles the between-step pause and the squash + PR at the end of the chain.

## STEP 5.5: LIVE confirmation rail (standalone mode only when `<env>=live`)

In **chain mode**, this step is skipped — the orchestrator does the LIVE retype-country rail once before the first step and threads `BACKUP_CONFIRMED=1` plus the chain branch through.

In **standalone mode** for live envs:

1. Print: "This will upgrade a LIVE production instance: `<country>`. Type the country name exactly to confirm."
2. Read trimmed answer. Compare to `<country>` exactly (case-sensitive).
3. Mismatch → `git restore -- "$TARGET"` and exit cleanly: "Country name mismatch. Aborted."

## STEP 6: Commit (and push/PR in standalone mode)

### Chain mode

1. **Stage and commit on the chain branch.**

   ```bash
   git add "$TARGET"
   git commit -m "Step 2.13→2.14 on <env>.<country> TOBE-17814"
   ```

2. Print: "Step 2.13→2.14 committed on `<CHAIN_BRANCH>`." Return control to the orchestrator. Do not push, do not open a PR.

### Standalone mode

1. **Compute branch name.** `BRANCH=chore/upgrade-<env>-<country>-2.13-to-2.14`.

2. **Check branch doesn't exist** (locally and on origin). If it does, abort and `git restore -- "$TARGET"`.

3. **Create branch and commit.**

   ```bash
   git checkout -b "$BRANCH"
   git add "$TARGET"
   git commit -m "Upgrade <env>.<country> from 2.13 to 2.14 TOBE-17814"
   ```

4. **Push.** `git push -u origin "$BRANCH"`. On rejection: leave the local commit, print recovery hint.

5. **Open PR.**
   - GitHub: `gh pr create --base master --head "$BRANCH" --title "Upgrade <env>.<country> from 2.13 to 2.14" --body "<body>"`
   - Bitbucket: skip CLI; print the manual link in the format `https://bitbucket.org/<workspace>/<repo>/pull-requests/new?source=$BRANCH&dest=master`.

6. **Print the PR URL.**

7. **Switch back to master.** `git checkout master`.

## Reference: failure modes

| Class | Examples | Outcome |
|---|---|---|
| Hard abort (no edits) | not in git repo; not on master (standalone) / not on chain branch (chain mode); dirty tree; gh missing on GitHub origin in standalone mode; pull fails; `Conf-<UPPER_ENV>/compose/` missing; user mistypes country twice (interactive); country supplied via args is invalid; target file missing; branch already exists locally or on origin (standalone) | Print failure reason, exit non-zero. |
| Clean exit (no edits) | candidate scan finds zero files; selected file has zero `unctad/*:$VAR_VER` lines; user said "N" to backup confirmation | Print "Nothing to upgrade" / "<country> appears to be already past 2.13", exit 0. |
| Soft pause | any anomaly (pre-scan, post-scan, precondition detection); diff-review answered N (standalone only); LIVE retype-country mismatch (standalone only); user said `N` to the Opensearch confirmation | Wait for input; on abort/restore/mismatch, run `git restore -- "$TARGET"` and exit cleanly. The Opensearch addition has an opt-out (the data backfill is a separate operation). The Keycloak Quarkus migration has no opt-out — to skip it, abort the whole skill and migrate Keycloak manually first. |

## Reference: PR body template (standalone mode)

```
## Summary

Mechanical upgrade of `Conf-<UPPER_ENV>/compose/<country>/docker-stack.yml`
from eRegistrations 2.13 to 2.14.

## Required transformations applied

- Bumped every `unctad/<service>:$<VAR>_VER` (and pinned-semver) image tag
  to `:RC` (the platform tag introduced in 2.14).
- Dropped `/auth` path suffix from `KEYCLOAK_URL` (internal + public),
  `AUTH_SERVICE_URL`, `AUTH_SERVICE_BACKEND_URL`, `AUTH_SERVICE_PUBLIC_URL`.
- Renamed `MONGO_URI` → `RH_MONGO_URI` on `restheart`.
- Bumped `EREGISTRATIONS_VERSION` from `2.13` (or `$EREGISTRATIONS_VERSION`)
  to `2.14` on `bpa-frontend` and `ereg-cms-frontend`.
- Bumped `BUILD_TYPE=LIVE` → `BUILD_TYPE=RC` on `bpa-frontend` and
  `ereg-cms-frontend` (non-dev envs only).

## Mandatory Keycloak Quarkus migration

<one of:>
- Applied: replaced Wildfly env vars (`PROXY_ADDRESS_FORWARDING`, `DB_*`,
  `KEYCLOAK_STATISTICS`) with the Quarkus block (`HTTP_ADDRESS_FORWARDING`,
  `KC_DB*`, `KC_HOSTNAME*`, `KC_LOG_LEVEL=INFO`) and added
  `extra_hosts: postgres_host:$SERVICE_HOST`.
- Not needed (Keycloak was already on Quarkus before this run).

## Optional Opensearch addition

<one of:>
- Opensearch migration applied: added `opensearch-node1` service block
  (`opensearchproject/opensearch:2.12.0`) and repointed
  `GRAYLOG_ELASTICSEARCH_HOSTS` from `$SERVICE_HOST:9200` to
  `opensearch-node1:9200`. Note: a one-time data backfill from the legacy
  Elasticsearch into Opensearch is required separately.
- Opensearch migration skipped (operator chose to handle manually, or
  Graylog was already pointing at Opensearch).

## Anomalies skipped

<skipped>

## Test plan

- [ ] CI passes.
- [ ] Reviewer eyeballs the diff against the rules in this skill, paying
      particular attention to the Keycloak Quarkus block (DB name, hostname)
      and the Opensearch block (volume paths, network reference).
- [ ] After deploy: keycloak service comes up healthy on Quarkus,
      Graylog ingestion lands in opensearch-node1 (if applied),
      `bpa-frontend`, `bpa-backend`, `restheart`, `camunda` all reachable.
- [ ] Smoke-test BPA login flow end-to-end (auth path drop is the riskiest
      change beyond the Keycloak block).
```
