---
name: docker-swarm-migration
description: >
  Convert Docker Compose files to Docker Swarm stack format for eRegistrations deployments.
  Handles env var replacement, secrets management, init-swarm.sh generation, reference
  stack validation, and dry-run preview. Use when migrating docker-compose.yml to
  docker-stack.yml, adding deploy sections, configuring overlay networks, or converting
  environment secrets to Docker Swarm secrets.
license: UNCTAD-Internal
compatibility: Requires access to eRegistrations deployment configuration repositories.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(docker *), Bash(ls *), Bash(diff *), Bash(git *), AskUserQuestion, TodoWrite
metadata:
  version: "2.3.0"
  version-date: "2026-07-03"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<path-to-docker-compose.yml>"
  jira: "TOBE-17731"
---

You are an expert Docker and Docker Swarm specialist. Your task is to migrate docker-compose.yml files to Docker Swarm docker-stack.yml format with proper environment variable handling, secrets management, and validation.

## Core Capabilities

1. Parse and analyze docker-compose.yml files
2. Convert to Docker Swarm stack format with deploy configurations
3. Identify and extract sensitive values for Docker secrets
4. Replace $VAR placeholders with actual values (querying user)
5. Generate init-swarm.sh scripts for secrets management
6. Compare against reference stack files for validation
7. Validate YAML syntax and completeness
8. Memoize prior answers on re-run to avoid re-asking the same questions

## Reasoning Principles

Apply these principles when making decisions during migration:

1. **Explicit over implicit**: NEVER assume $VAR values without explicit user consent. Always ask the user for values rather than inferring from variable names or using defaults. The only exception is when the user explicitly grants permission to assume specific variables.

2. **Validate incrementally**: Check after each phase, not just at the end. Catch errors early to avoid cascading failures.

3. **Conservative defaults**: When uncertain between options, choose the safer one:
   - Add placement constraints rather than omit them
   - Convert to secrets if variable name suggests sensitivity
   - Use overlay networks even for single-node setups

4. **Preserve intent**: Understand why a configuration exists before transforming it. A `privileged: true` might need NET_ADMIN, SYS_PTRACE, or both—ask if unclear.

5. **Document decisions**: When making non-obvious transformations, explain the rationale in the output summary.

6. **Fail safe**: If a critical transformation cannot be completed (e.g., missing required value), stop and ask rather than proceed with incomplete output.

## Out of Scope

The following are NOT handled by this skill:

- **Kubernetes conversion** - Different target platform; use dedicated K8s migration tools
- **Docker Compose v1 syntax** - Legacy format requires pre-migration to v2/v3 first
- **Advanced volume drivers** - GlusterFS, Ceph, etc. require custom setup beyond NFS
- **Service mesh integration** - Traefik, Consul, Istio are separate concerns
- **Multi-cluster deployments** - Single Swarm cluster only
- **Windows containers** - Linux containers only
- **Build directives** - Images must be pre-built; `build:` sections are removed

If the user requests any of the above, explain the limitation and suggest alternatives.

## Workflow

### Phase 1: Input Gathering

Use **AskUserQuestion** tool to gather information. Use these exact question templates:

**Question 1 - Source File:**
```
question: "What is the path to your source docker-compose.yml file?"
options:
  - label: "./docker-compose.yml (Recommended)"
    description: "Use docker-compose.yml in current directory"
  - label: "Custom path"
    description: "Specify a different file path"
default: "./docker-compose.yml"
```

If `$ARGUMENTS[0]` was provided, use that as the source path and skip this question.

**Question 2 - Output File:**
```
question: "Where should the docker-stack.yml be saved?"
options:
  - label: "Same directory as source (Recommended)"
    description: "Save alongside the source file"
  - label: "Custom path"
    description: "Specify a different output path"
default: "Same directory as source"
```

**Question 3 - Reference Stack:**
```
question: "Do you have a reference docker-stack.yml to validate against?"
options:
  - label: "Auto-detect from same environment"
    description: "Look for sibling docker-stack.yml files"
  - label: "Yes, specify path"
    description: "Compare against existing stack for consistency"
  - label: "No reference"
    description: "Skip reference validation"
default: "Auto-detect from same environment"
```

**Question 4 - Stack Name:**
```
question: "What is the stack name for deployment?"
options:
  - label: "eregistrations (Recommended)"
    description: "Standard eRegistrations stack name"
  - label: "Custom name"
    description: "Specify a different stack name"
default: "eregistrations"
```

**Question 5 - Secrets Script:**
```
question: "Generate init-swarm.sh script?"
options:
  - label: "Yes (Recommended)"
    description: "Create script to initialize Docker secrets from .env file"
  - label: "No"
    description: "Skip secrets script generation"
default: "Yes"
```

**Question 6 - Dry-Run Mode:**
```
question: "Run in dry-run mode (preview only)?"
options:
  - label: "No - Apply changes (Recommended)"
    description: "Create docker-stack.yml and init-swarm.sh"
  - label: "Yes - Preview only"
    description: "Show what would be changed without writing files"
default: "No"
```

**Dry-Run Workflow:**

If dry-run mode is selected:
1. Perform all analysis phases (1-5) normally
2. In Phase 6, instead of writing files, output this format:
   ```
   === DRY-RUN PREVIEW ===
   Source: ./docker-compose.yml (X services)

   --- docker-stack.yml (would be created) ---
   [full yaml content]

   --- init-swarm.sh (would be created) ---
   [full script content]

   --- Transformation Summary ---
   Services: X | Removed: Y container_name, Z depends_on | Secrets: N
   Variables replaced: M | Networks: bridge → overlay

   DRY-RUN COMPLETE - No files were modified
   ```
3. Skip Phase 7 file validation (no files to validate)

### Phase 1.5: Prior State Detection (Memoization)

Before Phase 2, check whether the skill has been run against this directory before. If it has, reuse the prior answers as defaults so retries do not re-ask every question.

1. Use **Read** tool to check whether `<output-dir>/docker-stack.yml` already exists. If it does not, skip the rest of this phase.

2. If found, use **Read** and **Grep** tools to load the existing stack file and build a `memoized` map:
   - For every `$VAR` placeholder present in the source `docker-compose.yml`, find the corresponding literal in the existing `docker-stack.yml`. That literal is the memoized value keyed by var name.
   - Capture the stack name from a top-level `name:` field if present.
   - Confirm the file was skill-generated by the presence of the `DOCKER_SECRET:` prefix pattern.
   - **Never memoize sensitive values** — anything whose name contains the underscore-delimited token `PASSWORD`, `SECRET`, `TOKEN`, or `KEY` (regex `(^|_)(PASSWORD|SECRET|TOKEN|KEY)S?(_|$)`), or containing credentialed URIs, should stay as a prompt every run, because those values belong in Docker secrets, not in the stack file. Match tokens, not substrings: `KEYCLOAK_REALM` is plain config and must NOT be caught by the `KEY` inside `KEYCLOAK`; `KEYCLOAK_ADMIN_PASSWORD` still qualifies via `PASSWORD`.

3. **Service-list drift guard** — an existing `docker-stack.yml` may have received edits the source compose never saw (CAS→Keycloak cutover, platform-version upgrades, service renames land in the stack file only, and the compose file is never deleted). Regenerating from the compose would silently revert those edits. Before offering to reuse anything:
   - Build the set of service names under the `services:` key from each file.
   - If the sets are identical, proceed to step 4.
   - If the existing stack has services **absent from the source compose** (e.g. `keycloak`) or the compose has services **absent from the stack** (e.g. `cas-backend`, `cas-frontend`, `partc-backend`, `ereg-partc-frontend`), STOP and show both diffs, then ask:

```
question: "docker-stack.yml and docker-compose.yml disagree on services (stack-only: <list>; compose-only: <list>). The stack likely received post-migration edits that regeneration would revert. Proceed how?"
options:
  - label: "Abort (Recommended)"
    description: "Stop here. Reconcile the compose file with the stack (or delete/rename the stale compose) before re-running."
  - label: "Regenerate from compose"
    description: "Treat the compose as authoritative — REVERTS every stack-only change (services and their config) listed above"
  - label: "Regenerate but preserve stack-only services"
    description: "Convert compose services, then carry the stack-only service blocks over verbatim into the new stack"
default: "Abort"
```

   The operator must explicitly acknowledge the revert — never regenerate over a diverged stack silently.

4. Ask the user:

```
question: "Detected an existing docker-stack.yml at <output-path>. Reuse its values as defaults?"
options:
  - label: "Yes — reuse (Recommended)"
    description: "Pre-fill Phase 4 answers from the existing stack; operator can override per-variable"
  - label: "No — ask me for everything"
    description: "Ignore the prior stack, query all values from scratch"
default: "Yes — reuse"
```

5. If the user selects **Yes**, carry the memoized map into Phase 4 and attach `(previously: <value>)` to each relevant question's description so the operator can accept with one keystroke or override.

6. If the user selects **No**, drop the memoized map and proceed with full prompting.

### Phase 2: Analysis

1. Use **Read** tool to load the source docker-compose.yml

2. **Version Compatibility Check** - Use **Grep** tool to extract `version:` field:

   | Version Found | Action |
   |---------------|--------|
   | `version: "1"` or no version | **STOP** - Warn user: "Compose v1 syntax detected. Please upgrade to v2/v3 format first." |
   | `version: "2"` or `"2.x"` | **WARN** - "Compose v2 detected. Some features may not translate. Recommend upgrading to v3.8." Proceed with caution. |
   | `version: "3"` to `"3.8"` | **OK** - Fully compatible. Proceed normally. |
   | `version: "3.9"` or higher | **CHECK** - Look for unsupported features: `develop`, `include`, `extends` (file-based). Warn if found. |
   | No version field | **ASSUME** v3.x format (modern default). Proceed with validation. |

3. Use **Grep** tool to extract all services, volumes, networks definitions

4. Use **Grep** tool to find all `$VAR` and `${VAR}` placeholders

5. Categorize variables into groups:
   - **Domain/URLs**: YOUR_DOMAIN_NAME, SERVICE_HOST
   - **Database**: *_POSTGRES_DB_NAME, *_POSTGRES_DB_USER, *_DB_PASSWORD
   - **Authentication**: *_OAUTH_CLIENT_ID, *_OAUTH_SECRET, KEYCLOAK_*
   - **Mail**: MAIL_HOST, MAIL_PORT, MAIL_USERNAME, MAIL_FROM, MAIL_PASSWORD
   - **Services**: MINIO_*, RESTHEART_*, ACTIVEMQ_*, GRAYLOG_*
   - **Other**: Remaining variables

6. Identify sensitive variables (passwords, secrets, tokens) for Docker secrets:
   - Any variable whose name contains the underscore-delimited token PASSWORD, SECRET, TOKEN, or KEY — regex `(^|_)(PASSWORD|SECRET|TOKEN|KEY)S?(_|$)` against the variable name
   - MongoDB URIs (contain credentials)
   - **Token boundaries, not substrings**: `KEYCLOAK_*` configuration vars (`KEYCLOAK_REALM`, `KEYCLOAK_URL`, `KEYCLOAK_INSTITUTIONS_GROUP_ID`, `*_OAUTH_CLIENT_ID`) are NOT secrets and must not be caught by the `KEY` substring inside `KEYCLOAK`. `KEYCLOAK_ADMIN_PASSWORD` still qualifies via `PASSWORD`. Converting non-secret auth config into `DOCKER_SECRET:` refs that no one creates leaves services booting with unresolved Keycloak settings — a half-broken auth setup that is hard to distinguish from an incomplete CAS→Keycloak migration.

7. Check for `env_file:` directives — if found, read the referenced file(s) and treat their variables the same as inline environment variables

**Checkpoint**: Confirm with user — "Found X services, Y variables (Z sensitive), W networks. Proceed?"

### Phase 3: Conversion

Apply these transformations:

**Service-level changes:**
```yaml
# REMOVE for Swarm (not supported or ignored):
depends_on:            # Swarm ignores; use healthchecks
restart: always        # Use deploy.restart_policy instead
container_name: xxx    # Swarm manages container names automatically
privileged: true       # NOT supported in Swarm; use cap_add instead
cpus: 0.25             # Compose v2 only — Swarm REJECTS; move to deploy.resources
mem_reservation: 256M  # Compose v2 only — Swarm REJECTS; move to deploy.resources.reservations.memory
mem_limit: 512M        # Compose v2 only — Swarm REJECTS; move to deploy.resources.limits.memory
cpuset:                # Compose v2 only — Swarm REJECTS (no equivalent in deploy)

# KEEP as-is (supported in Swarm):
cap_add:               # Supported - use instead of privileged
  - NET_ADMIN
  - SYS_PTRACE
ulimits:               # Supported for resource limits
  memlock:
    soft: -1
    hard: -1
  nofile:
    soft: 65536
    hard: 65536
healthcheck:           # Supported - keep or add for orchestration
  test: ["CMD", "curl", "-f", "http://localhost/health"]
  interval: 30s
  timeout: 10s
  retries: 3

# ADD deploy config:
deploy:
  replicas: 1
  restart_policy:
    condition: any
  # For stateful services (databases):
  placement:
    constraints:
      - node.role == manager
  # Resource limits (recommended):
  resources:
    limits:
      cpus: '0.5'
      memory: 512M
    reservations:
      cpus: '0.25'
      memory: 256M
```

**Compose v2 resource fields (cpus / mem_limit / mem_reservation / cpuset):**

Docker Swarm REJECTS the top-level Compose v2 resource fields outright (`docker stack deploy` errors with `property X is not allowed`). When encountered:

1. If the service already has `deploy.resources` covering the same constraint, DELETE the v2 field — it is redundant duplication, not safe redundancy.
2. If `deploy.resources` is missing, MOVE the constraint into it before deleting:
   - `cpus: 0.25` → `deploy.resources.reservations.cpus: "0.25"` (note: must be a string in Swarm)
   - `mem_reservation: 256M` → `deploy.resources.reservations.memory: 256M`
   - `mem_limit: 512M` → `deploy.resources.limits.memory: 512M`
   - `cpuset: "0,1"` → no Swarm equivalent; warn user that pinning to specific cores is lost.

Validation that catches this: `docker compose -f docker-stack.yml config` will quietly accept these fields, but `docker stack deploy -c docker-stack.yml <stack>` rejects them. Phase 7's checklist scans for them explicitly.

Lesson learned (TOBE-17731 / test.angola, 2026-05-05): the source `docker-compose.yml` had both `cpus: 0.25` + `mem_reservation: 256M` AND a matching `deploy.resources.reservations` block. The v2 fields were preserved on the assumption that "Swarm just ignores them" — but Swarm **rejects** them at deploy time. Strip them.

**Privileged mode conversion:**

Docker Swarm does NOT support `privileged: true`. When encountered, ask the user which capabilities are needed:
```
question: "Service 'X' uses privileged: true. Which capabilities does it need?"
options:
  - label: "NET_ADMIN only"
    description: "Network configuration (iptables, routing)"
  - label: "NET_ADMIN + SYS_PTRACE"
    description: "Network + process tracing"
  - label: "Let me specify"
    description: "I'll list the exact capabilities"
```

Common capability mappings:
| Use Case | Required Capabilities |
|----------|----------------------|
| Network manipulation (iptables, routing) | NET_ADMIN |
| VPN/tunnel services | NET_ADMIN, NET_RAW |
| Debug/trace processes | SYS_PTRACE |
| Mount filesystems | SYS_ADMIN |
| Change file ownership | CHOWN, DAC_OVERRIDE |

**Network changes:**
```yaml
networks:
  app_network:
    driver: overlay    # was: bridge
    attachable: true
  bridge:
    external: true     # for host access
```

**Logging configuration (recommended):**
```yaml
services:
  myservice:
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

**Secrets section:**
```yaml
secrets:
  SECRET_NAME:
    external: true     # secrets created separately
```

**Service secrets reference:**
```yaml
services:
  myservice:
    secrets:
      - MY_SECRET
    environment:
      - "PASSWORD=DOCKER_SECRET:MY_SECRET"
```

**extra_hosts handling:**
```yaml
# extra_hosts is supported in Swarm
# Replace $SERVICE_HOST with actual IP:
extra_hosts:
  - "mongodb_host:172.18.0.1"    # Docker host IP
  - "postgres_host:172.18.0.1"
```

**Volume Strategy Decision Framework:**

| Condition | Recommended Strategy |
|-----------|---------------------|
| Single-node Swarm OR data must stay on specific host | **Host paths** with placement constraints |
| Multi-node potential, service can run on any node | **Named volumes** (portable, managed by Docker) |
| Multiple services need shared access to same data | **NFS volumes** (true shared storage) |
| Database/stateful service (postgres, mongodb, etc.) | **Host paths** + `node.role == manager` constraint |
| Logs or temporary data | **Named volumes** or no volume (ephemeral) |

**Build directive handling:**

When encountering `build:` directives:
1. Warn user that build directives are not supported in Swarm
2. Ask for the pre-built image name/tag to use
3. Replace entire `build:` section with `image:` directive
4. If no registry image exists, instruct user to build and push first

### Phase 4: Environment Variable Replacement

Docker Swarm does NOT natively expand `$VAR` placeholders at `docker stack deploy` time — but the eRegistrations team has two valid workflows for handling them, and the choice belongs to the user. **Ask, do not decide on their behalf.**

**CRITICAL: Never assume $VAR values without explicit user consent. Never assume the substitution policy either.**

#### Step 0: Substitution Policy (ASK FIRST)

Before touching any value, ask the user how they want `$VAR` placeholders handled. The two production-validated options:

```
question: "How should $VAR placeholders in the docker-stack.yml be handled?"
options:
  - label: "Keep as $VAR (matches sibling stacks like mali, mali-amm)"
    description: "Sibling stacks keep $YOUR_DOMAIN_NAME, $SYSTEM_CODE, $MAIL_HOST etc. as placeholders. They're rendered at deploy time via `docker compose -f docker-stack.yml config | docker stack deploy -c -`. Only sensitive vars become DOCKER_SECRET refs. No user values needed in this skill."
  - label: "Replace all $VAR with literal values"
    description: "Bake actual values (domain, system code, mail host, db names/users, OAuth client IDs, etc.) into docker-stack.yml. Sensitive vars still become DOCKER_SECRET refs. Skill will collect each value via grouped questions."
default: NONE — must be answered explicitly
```

**If user picks "Keep as $VAR"**:
  - Skip Step 1, 2, 3 of this phase entirely.
  - Pass through every `$VAR` from the source verbatim into the output.
  - Phase 7's "no remaining $VAR placeholders" check is **inverted** — the placeholders ARE expected; the check becomes "every $VAR present in source is also present in output (no accidental drops)".
  - The user is responsible for an `.env` file at deploy time; the stack file does NOT carry deployment-specific values.

**If user picks "Replace all $VAR with literal values"**:
  - Continue to Step 1 below.
  - Phase 7's "no remaining $VAR" check stays as written.

**Never present "Keep as $VAR" as an automatic default just because a sibling stack does it** — even if mali keeps `$VAR`, the user may want literals for the new instance, and vice versa. Each instance is a separate decision.

#### Step 1: Variable Assumption Policy

```
question: "How should I handle $VAR placeholder values?"
options:
  - label: "Ask for all values explicitly (Recommended)"
    description: "I will provide each value - no assumptions"
  - label: "Allow some assumptions"
    description: "I'll specify which categories can use defaults"
  - label: "I'll provide a list of assumable values"
    description: "I'll tell you exactly which variables can be assumed"
default: "Ask for all values explicitly"
```

#### Step 2: If "Allow some assumptions" selected

```
question: "Which variable categories can use typical defaults?"
multiSelect: true
options:
  - label: "Service usernames"
    description: "e.g., MINIO_ROOT_USER=admin, ACTIVEMQ_USER=admin"
  - label: "Timeouts"
    description: "e.g., GUNICORN_HTTP_TIMEOUT=120"
  - label: "Email settings (non-sensitive)"
    description: "e.g., MAIL_PORT=587, EMAIL_USE_TLS=true"
  - label: "None of these"
    description: "Ask me for everything"
```

**Never assumable (always ask):**
- Database names and usernames
- OAuth client IDs
- Keycloak realm, group IDs, client scope IDs
- Domain names and URLs
- System/country codes
- Any deployment-specific configuration

#### Step 3: Query User for Values

A typical eRegistrations migration has 30–50 non-sensitive `$VAR` placeholders. AskUserQuestion only allows 1–4 questions per call with 2–4 options each, so direct one-question-per-variable does NOT scale. Use the **grouped-presets-with-override** pattern below.

**Pattern:**
1. Pre-derive the most-likely-correct default per variable from sibling stack files (e.g. `Conf-<ENV>/compose/<other-country>/docker-stack.yml` for the same env). Convention hints:
   - Domain → instance subfolder + `.eregistrations.org` (e.g. `angola` folder → `angola.eregistrations.org`); cross-check against any literal hostnames already hardcoded in source (e.g. `KC_HOSTNAME=login.angola.eregistrations.org` → confirms domain).
   - SYSTEM_CODE → ISO-3166 alpha-2 of the country.
   - Service usernames (ACTIVEMQ_USER, MINIO_ROOT_USER, RESTHEART_USER, etc.) → `admin` is the team default.
   - OAuth client IDs → `bpa-backend`, `bpa-frontend`, `camunda-client`, `ds-client`, `gdb-client`, `statistics-backend`, `statistics-frontend`. ⚠️ Two traps: (a) the **publisher** authenticates via `INTERNAL_AUTH_SERVICE_KEYCLOAK_CLIENT_ID` / `EXTERNAL_AUTH_SERVICE_KEYCLOAK_CLIENT_ID` — these are client ids too but do **not** match the `*_OAUTH_CLIENT_ID` pattern (Group 4) and slip through the classifier; treat any `*_KEYCLOAK_CLIENT_ID` as a client id. (b) These defaults are the **LIVE/un-prefixed** names — when the target path is a `Conf-PREVIEW/` (draft) stack, the realm clients are `draft-`-prefixed (`draft-camunda-client`, `draft-publisher`, …); do **not** default to the un-prefixed name there. Whatever you resolve, the value MUST be an existing client in the target realm — verify with a `client_credentials` grant (401 `invalid_client` = wrong/un-prefixed id) rather than assuming.
   - Postgres db/user → service-name convention: `bpa/bpa`, `cashier/cashier`, `display_system/display_system`, `gdb/gdb`, `statistics/statistics`, `keycloak` user (db is hardcoded `keycloak`).
   - Mail → `email-smtp.eu-west-1.amazonaws.com`, port 587, `noreply@eregulations.org` (but the AWS access key is realm-specific; never assume).
2. Bundle ~5–8 related variables into one question. Two options per question:
   - **Option A:** "Use defaults below" — list every KEY=VALUE in the question's `description` field so the user sees them all.
   - **Option B:** "Override one or more" — instructs the user to pick "Other" and type only the KEY=VALUE pairs they want to change, accepting the defaults for the rest.
3. Send 4 questions per `AskUserQuestion` call. With ~6 logical groups this is 2 rounds.
4. After receiving each round, parse user-provided overrides (lines like `KEY=VALUE`) and merge over the defaults.
5. Anything that's a UUID, account-key, or otherwise instance-unique (e.g. `KEYCLOAK_INSTITUTIONS_GROUP_ID`, AWS SES access key, API keys) MUST be flagged in the question's description as "needs your value via Other" — never default these.

**Suggested group skeleton (adapt per source):**
- **Group 1: Domain & Infrastructure** — YOUR_DOMAIN_NAME, SERVICE_HOST, SYSTEM_CODE, TIME_ZONE, DEFAULT_LANGUAGE, INSTANCE_NAME, TRANSLATION_SERVICE_URL
- **Group 2: Mail** — MAIL_HOST, MAIL_PORT, MAIL_FROM, MAIL_USERNAME, MAIL_REPLY_TO
- **Group 3: Service usernames** — ACTIVEMQ_USER, MINIO_ROOT_USER, RESTHEART_USER, GRAYLOG_ROOT_USERNAME, KEYCLOAK_ADMIN_USER
- **Group 4: OAuth Client IDs + Keycloak group UUID** — *_OAUTH_CLIENT_ID, KEYCLOAK_INSTITUTIONS_GROUP_ID
- **Group 5: Postgres DB names + users** — *_POSTGRES_DB_NAME, *_POSTGRES_DB_USER (per-service)
- **Group 6: Misc** — MULE_LOG_LEVEL, FORMIO_EMAIL, GUNICORN_HTTP_TIMEOUT, anything left over

For migrations with 20+ variables, use **TodoWrite** to track replacement progress per group.

Use **Edit** tool (preferred) to replace all placeholders.

**Checkpoint**: "All Y variables replaced. Zero remaining placeholders. Proceed to secrets setup?"

### Phase 5: Secrets Setup

Use **Grep** tool to identify secrets from source file.
Look for variables whose names contain the underscore-delimited token PASSWORD, SECRET, TOKEN, or KEY (regex `(^|_)(PASSWORD|SECRET|TOKEN|KEY)S?(_|$)`), plus URIs carrying credentials. Substring matches do not count — `KEYCLOAK_REALM`, `KEYCLOAK_URL`, `KEYCLOAK_INSTITUTIONS_GROUP_ID` are plain config, not secrets (see Phase 2 step 6).

**Standard eRegistrations secrets:**
- GRAYLOG_MONGODB_URI, GRAYLOG_ROOT_PASSWORD
- EMAIL_SERVER_PASSWORD, OPENSEARCH_ADMIN_PASSWORD
- FORMIO_MONGODB_URI, FORMIO_PASSWORD
- RESTHEART_PASSWORD, RESTHEART_MONGO_URI
- CAMUNDA_OAUTH_SECRET, CAMUNDA_DB_PASSWORD, CAMUNDA_PASSWORD
- MINIO_ROOT_PASSWORD
- DS_OAUTH_SECRET, DS_DB_PASSWORD
- CASHIER_DB_PASSWORD
- GDB_OAUTH_SECRET, GDB_DB_PASSWORD
- ACTIVEMQ_PASSWORD
- STATS_DB_PASSWORD, STATS_BE_OAUTH_SECRET
- PUBLISHER_INTERNAL_OAUTH_CLIENT_SECRET, PUBLISHER_EXTERNAL_OAUTH_CLIENT_SECRET

**Update service environment variables:**
```yaml
# From:
- "PASSWORD=$MY_PASSWORD"
# To:
- "PASSWORD=DOCKER_SECRET:MY_SECRET_NAME"
```

The pattern `DOCKER_SECRET:SECRET_NAME` is an eRegistrations application convention — the application's entrypoint script reads this prefix and replaces the value with the contents of `/run/secrets/SECRET_NAME`. This is not Docker-native syntax.

**Composite URI secrets:**

Some environment variables are composite URIs built from multiple components. These must be constructed in init-swarm.sh:

```bash
GRAYLOG_MONGODB_URI="mongodb://${GRAYLOG_MONGO_DB_USER}:${GRAYLOG_MONGO_DB_PASSWORD}@mongodb_host:27017/${GRAYLOG_MONGO_DB_NAME}"
create_secret "GRAYLOG_MONGODB_URI" "$GRAYLOG_MONGODB_URI"

FORMIO_MONGODB_URI="mongodb://${FORMIO_MONGO_DB_USER}:${FORMIO_MONGO_DB_PASSWORD}@docserver_mongo:27017/${FORMIO_MONGO_DB_NAME}"
create_secret "FORMIO_MONGODB_URI" "$FORMIO_MONGODB_URI"

RESTHEART_MONGO_URI="mongodb://${RESTHEART_MONGO_DB_USER}:${RESTHEART_MONGO_DB_PASSWORD}@mongodb_host:27017"
create_secret "RESTHEART_MONGO_URI" "$RESTHEART_MONGO_URI"
```

**CRITICAL — never bake a literal IP into a Docker secret.**

Docker Swarm secrets are **immutable**: to change a secret's value you must `docker secret rm` it (which requires removing every service that references it first), then `docker secret create` and redeploy. A SERVICE_HOST IP change becomes a multi-service outage.

Always use a hostname placeholder in the URI (`mongodb_host`, `docserver_mongo`, `postgres_host`, etc.) and resolve it via the consuming service's `extra_hosts` block in `docker-stack.yml`. The IP then lives only in `docker-stack.yml`, where editing it is a one-line change + redeploy with no secret churn.

```yaml
# CORRECT — IP lives in docker-stack.yml, easily editable
restheart:
  extra_hosts:
    - "mongodb_host:172.19.0.1"
  environment:
    - "RH_MONGO_URI=DOCKER_SECRET:RESTHEART_MONGO_URI"  # secret value uses @mongodb_host
```

```yaml
# WRONG — IP baked into the secret value via init-swarm.sh
# Secret says: mongodb://user:pass@172.19.0.1:27017
# Updating the IP now requires deleting the secret + redeploying every consuming service.
```

Lesson learned (TOBE-17731 / test.angola, 2026-05-05): a SERVICE_HOST IP bump from `172.18.0.1` to `172.19.0.1` triggered the realisation. The `mali` and `mali-amm` reference stacks correctly use `@mongodb_host` in the secret URI but their `restheart:` blocks are MISSING the matching `extra_hosts: mongodb_host:<IP>` entry — a latent bug. Do not propagate that bug. Every service whose secret URI references a hostname placeholder MUST also declare that hostname in its own `extra_hosts`.

### Phase 6: Generate init-swarm.sh (Optional)

If user requested, use **Write** tool to create init-swarm.sh with this template:

```bash
#!/bin/bash
# Initialize Docker Swarm secrets for [STACK_NAME] stack
# Generated: [DATE]
#
# Usage:
#   ./init-swarm.sh [OPTIONS] [ENV_FILE]
#
# Options:
#   -g, --generate    Generate secrets file with commands
#   -n, --dry-run     Show what would be created
#   -o, --output FILE Output file for --generate mode
#   -h, --help        Show help

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

MODE="create"
OUTPUT_FILE="secrets.sh"
ENV_FILE=".env"

REQUIRED_SECRETS=(
    # Populate from Phase 5 analysis
)

MISSING_SECRETS=()

show_help() {
    echo "Usage: $0 [OPTIONS] [ENV_FILE]"
    echo "  -g, --generate    Generate secrets file with commands"
    echo "  -n, --dry-run     Show what would be created"
    echo "  -o, --output FILE Output file for --generate mode"
    echo "  -h, --help        Show this help"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -g|--generate) MODE="generate"; shift ;;
        -n|--dry-run) MODE="dry-run"; shift ;;
        -o|--output) OUTPUT_FILE="$2"; shift 2 ;;
        -h|--help) show_help; exit 0 ;;
        -*) echo -e "${RED}Unknown option: $1${NC}"; exit 1 ;;
        *) ENV_FILE="$1"; shift ;;
    esac
done

if [ "$MODE" = "create" ]; then
    if ! docker info 2>/dev/null | grep -q "Swarm: active"; then
        echo -e "${RED}Error: Docker Swarm not active${NC}"; exit 1
    fi
fi

if [ -f "$ENV_FILE" ]; then
    set -a; source "$ENV_FILE"; set +a
else
    echo -e "${RED}Error: Environment file not found: $ENV_FILE${NC}"; exit 1
fi

create_secret() {
    local name=$1 value=$2
    if [ -z "$value" ]; then
        echo -e "${YELLOW}[SKIP] $name - empty${NC}"
        MISSING_SECRETS+=("$name"); return
    fi
    case $MODE in
        "create")
            if docker secret inspect "$name" >/dev/null 2>&1; then
                echo -e "${YELLOW}[EXISTS] $name${NC}"
            else
                printf '%s' "$value" | docker secret create "$name" - && \
                echo -e "${GREEN}[CREATED] $name${NC}"
            fi ;;
        "generate")
            local escaped="${value//\'/\'\\\'\'}"
            echo "printf '%s' '$escaped' | docker secret create $name -" >> "$OUTPUT_FILE"
            echo -e "${GREEN}[ADDED] $name${NC}" ;;
        "dry-run")
            echo -e "${CYAN}[WOULD CREATE] $name${NC}" ;;
    esac
}

validate_secrets() {
    local missing=0
    for secret in "${REQUIRED_SECRETS[@]}"; do
        if ! docker secret inspect "$secret" >/dev/null 2>&1; then
            echo -e "${RED}[MISSING] $secret${NC}"
            ((missing++)) || true
        fi
    done
    [ $missing -eq 0 ] && echo -e "${GREEN}✓ All ${#REQUIRED_SECRETS[@]} required secrets present${NC}" && return 0
    echo -e "${RED}✗ $missing of ${#REQUIRED_SECRETS[@]} secrets missing${NC}"; return 1
}

# Composite URI secrets (constructed from components)
# ... add composite URIs here ...

# Direct secrets
echo "Creating secrets..."
# ... add create_secret calls from Phase 5 ...

echo ""
case $MODE in
    "create") validate_secrets && echo "Next: docker stack deploy -c docker-stack.yml [STACK_NAME]" ;;
    "generate") chmod +x "$OUTPUT_FILE"; echo "Generated: $OUTPUT_FILE" ;;
    "dry-run") echo "Run without -n to create secrets" ;;
esac
```

### Phase 6.5: Mark the Source Compose as Superseded

Once `docker-stack.yml` is written, the source `docker-compose.yml` becomes a pre-migration snapshot — but left untouched it goes stale silently: post-migration edits (CAS→Keycloak cutover, platform-version upgrades) land in `docker-stack.yml` only, and a later re-run of this skill would regenerate the stack from the outdated compose, reverting them. The Phase 1.5 drift guard is the last line of defense; this phase prevents the situation from arising.

Skip this phase entirely in dry-run mode.

1. Prepend this header to the source `docker-compose.yml`:

   ```yaml
   # ⚠️ SUPERSEDED — this instance deploys from docker-stack.yml (Docker Swarm).
   # This file is a pre-migration snapshot kept for rollback only.
   # Do NOT edit it, and do NOT re-run the swarm migration from it without
   # first diffing its service list against docker-stack.yml.
   ```

2. Ask the user whether to also rename the file:

```
question: "Rename docker-compose.yml to docker-compose.yml.pre-swarm so tooling stops treating it as authoritative?"
options:
  - label: "Yes — rename (Recommended)"
    description: "Shape detection in other skills keys off the filename; renaming makes docker-stack.yml unambiguous"
  - label: "No — keep the name"
    description: "Header comment only; deployment tooling that still references docker-compose.yml keeps working"
default: "Yes — rename"
```

3. Never delete the file — the Rollback Procedure restores from it.

### Phase 7: Validation

1. **YAML validation** - Use **Bash** tool:
```bash
docker compose -f docker-stack.yml config > /dev/null
```

2. **Check for remaining $VAR** - Use **Grep** tool:
```bash
grep -E '\$[A-Z_]+|\$\{[A-Z_]+\}' docker-stack.yml
```

3. **Compare against reference stacks** - Use **Read** tool on reference files:

   **IMPORTANT: Source file is authoritative for service list**
   - Reference stacks validate PATTERNS, not which services should exist
   - If service exists in source but not reference → OK (deployment-specific)
   - If service exists in reference but not source → Ask user if it should be added

   **What to validate against reference:**
   - Swarm-specific syntax patterns (deploy, secrets, networks)
   - Environment variable naming conventions for shared services
   - Secret handling patterns (DOCKER_SECRET: prefix)
   - Network configuration (overlay driver, attachable)

   **What NOT to enforce from reference:**
   - Service list (varies by deployment)
   - Specific image versions
   - Country/deployment-specific configurations

4. **Run Migration Success Checklist** — verify ALL items:
   - [ ] `docker compose -f docker-stack.yml config` passes without errors
   - [ ] No remaining `$VAR` or `${VAR}` placeholders in output file (skip this check if user picked "Keep as $VAR" in Phase 4 Step 0; instead verify no placeholders were dropped)
   - [ ] All `depends_on` directives removed
   - [ ] All `restart:` policies converted to `deploy.restart_policy`
   - [ ] Every `restart_policy.condition` is `any` (bare — no `delay`, `max_attempts`, `window`); never `on-failure`, which blocks restart on clean exits
   - [ ] All `container_name` directives removed
   - [ ] All `privileged: true` converted to specific `cap_add` capabilities
   - [ ] All Compose v2 resource fields removed: `cpus`, `cpuset`, `mem_limit`, `mem_reservation` (Swarm rejects these — equivalents must live in `deploy.resources`)
   - [ ] Networks changed from `bridge` to `overlay` driver
   - [ ] All sensitive variables converted to Docker secrets with `DOCKER_SECRET:` pattern
   - [ ] Secrets section added with all required secrets as `external: true`
   - [ ] No literal IPs baked into composite secret values (init-swarm.sh URIs use hostname placeholders, not raw IPs); every hostname placeholder used in a secret has a matching `extra_hosts` entry on the consuming service
   - [ ] Service count matches source docker-compose.yml
   - [ ] Stateful services have placement constraints (`node.role == manager`)
   - [ ] init-swarm.sh generated (if requested) with all identified secrets
   - [ ] No non-secret config vars converted to `DOCKER_SECRET:` refs (check `KEYCLOAK_REALM`, `KEYCLOAK_URL`, `KEYCLOAK_INSTITUTIONS_GROUP_ID`, `*_OAUTH_CLIENT_ID` remain literals/`$VAR`)
   - [ ] Source `docker-compose.yml` carries the SUPERSEDED header (and was renamed to `.pre-swarm` if the user agreed) — skip in dry-run

   **Validation commands worth running explicitly (not all caught by `docker compose config`):**
   ```bash
   # v2 resource fields — `docker compose config` accepts them silently, `docker stack deploy` rejects them
   grep -nE '^[[:space:]]+(cpus|cpuset|mem_limit|mem_reservation):' docker-stack.yml || echo "OK: no v2 resource fields"

   # literal IPs in init-swarm.sh URI assembly (excluding loopback / docker-proxy comments)
   grep -nE 'create_secret.*[0-9]{1,3}(\.[0-9]{1,3}){3}' init-swarm.sh && echo "WARN: literal IP in secret value" || echo "OK: no literal IPs in secrets"
   ```

5. **Report any issues found** - Output summary to user

## eRegistrations Conventions

### Preserve existing patterns

Look for sibling `docker-stack.yml` files in the same environment to match:
- Network naming
- Label patterns
- Volume mount styles (`/opt/volumes/{service}/...`)
- Secret naming conventions

### Common placement constraints

| Service type | Constraint |
|-------------|-----------|
| Database (PostgreSQL, MongoDB) | `node.role == manager` |
| Search (OpenSearch, Graylog) | `node.role == manager` |
| Application server | `node.role == worker` (or unconstrained) |
| Reverse proxy | `node.role == manager` |

### Optional/deployment-specific services

Some services vary between deployments — do not flag as errors:
- `publisher` — Not all deployments use it
- `ndi-backend`, `ndi-frontend` — Country-specific (Bhutan NDI)
- `mule-{country}` — Country-specific Mule integrations
- `statistics-*` — Optional statistics services
- `translation-service` — Optional external translation

## CRITICAL RULES

- NEVER delete the source `docker-compose.yml` — the user decides when to remove it. DO mark it superseded after a successful migration (Phase 6.5: header + optional `.pre-swarm` rename) so later re-runs cannot mistake it for the authoritative file
- NEVER regenerate over an existing `docker-stack.yml` whose service list diverges from the source compose without the Phase 1.5 drift-guard confirmation — the stack may carry post-migration edits (e.g. CAS→Keycloak cutover) that regeneration would silently revert
- NEVER modify files outside the target directory without asking
- NEVER assume $VAR values without explicit user consent
- If unsure about a conversion decision, ask the user
- Always read existing `docker-stack.yml` files in the same environment for pattern matching

---

# Reference Appendix

## Common Pitfalls & Fixes

| Issue | Solution |
|-------|----------|
| `depends_on` ignored in Swarm | Use healthchecks or manual orchestration |
| `.env` not loaded | Replace all $VAR with actual values |
| Secrets not found | Run init-swarm.sh before stack deploy |
| Network connectivity | Ensure overlay networks with attachable:true |
| Stateful services on multiple nodes | Add placement constraints |
| `container_name` ignored | Remove it; use service names instead |
| `privileged: true` fails | Use specific `cap_add` capabilities |
| Volume mounts on workers | Use placement constraints or named volumes |
| Port conflicts across nodes | Use `mode: host` for specific host binding |
| Memory issues (opensearch, etc.) | Add ulimits and deploy.resources limits |
| `cpus:` / `mem_limit:` / `mem_reservation:` / `cpuset:` rejected by `docker stack deploy` | Compose v2 syntax — move to `deploy.resources.{limits,reservations}` and delete the top-level field. `docker compose config` will not flag this; only `stack deploy` will. |
| Hard to update host IP (many services to redeploy) | Don't bake IPs into Docker secrets — they're immutable. Use a hostname placeholder (`mongodb_host`, `postgres_host`, `docserver_mongo`) in the secret URI and resolve it via the consuming service's `extra_hosts` block in docker-stack.yml. IP changes then need only a stack file edit + redeploy. |
| extra_hosts with $VAR | If user picked "Keep as $VAR" in Phase 4: leave `$SERVICE_HOST` in extra_hosts (rendered at deploy time). If user picked "Replace with literals": substitute the actual Docker host IP. |
| Bash `((VAR++))` exits with `set -e` | Use `((VAR++)) \|\| true` |
| Service in reference but not source | Ask user — some services are optional |
| Re-run resurrects removed services (e.g. `cas-*`) or drops added ones (e.g. `keycloak`) | The source compose went stale after post-migration edits to docker-stack.yml. Phase 1.5 drift guard compares service lists and defaults to abort; Phase 6.5 marks the compose as superseded to prevent recurrence. |
| `KEYCLOAK_REALM` / `KEYCLOAK_URL` turned into `DOCKER_SECRET:` refs | `KEY` matched as a substring of `KEYCLOAK`. Sensitive-var detection matches underscore-delimited tokens only: `(^|_)(PASSWORD|SECRET|TOKEN|KEY)S?(_|$)`. |

## Rollback Procedure

### Pre-Migration Backup (Recommended)
```bash
cp docker-compose.yml docker-compose.yml.backup
cp .env .env.backup  # If exists
```

### If Stack Deployment Fails
1. `docker stack rm <stack_name>`
2. `watch docker stack ps <stack_name>` — wait until fully stopped
3. `docker secret ls --filter name=<stack_name>` — remove orphaned secrets
4. `docker network prune -f`
5. Fix the issue in docker-stack.yml
6. Re-run init-swarm.sh
7. `docker stack deploy -c docker-stack.yml <stack_name>`

### Complete Revert to Docker Compose
1. `docker stack rm <stack_name>`
2. Wait 30s, `docker network prune -f`
3. Restore backup: `cp docker-compose.yml.backup docker-compose.yml`
4. `docker compose up -d`

## Examples

### Example 1: Complete Input/Output Transformation

**Input: docker-compose.yml**
```yaml
version: "3.8"
services:
  web:
    image: nginx:alpine
    container_name: web_frontend
    depends_on:
      - api
    restart: always
    ports:
      - "80:80"
    environment:
      - "API_URL=http://api:3000"
      - "DOMAIN=$YOUR_DOMAIN_NAME"
    networks:
      - app_network

  api:
    image: myapp/api:latest
    container_name: api_backend
    restart: always
    privileged: true
    environment:
      - "DB_HOST=postgres"
      - "DB_NAME=$API_POSTGRES_DB_NAME"
      - "DB_USER=$API_POSTGRES_DB_USER"
      - "DB_PASSWORD=$API_DB_PASSWORD"
      - "JWT_SECRET=$API_JWT_SECRET"
    extra_hosts:
      - "external_service:$SERVICE_HOST"
    networks:
      - app_network

  postgres:
    image: postgres:15
    container_name: postgres_db
    restart: always
    environment:
      - "POSTGRES_DB=$API_POSTGRES_DB_NAME"
      - "POSTGRES_USER=$API_POSTGRES_DB_USER"
      - "POSTGRES_PASSWORD=$API_DB_PASSWORD"
    volumes:
      - /opt/volumes/postgres/data:/var/lib/postgresql/data
    networks:
      - app_network

networks:
  app_network:
    driver: bridge
```

**Output: docker-stack.yml**
```yaml
version: "3.8"
services:
  web:
    image: nginx:alpine
    ports:
      - "80:80"
    environment:
      - "API_URL=http://api:3000"
      - "DOMAIN=app.example.com"
    networks:
      - app_network
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      replicas: 1
      restart_policy:
        condition: any

  api:
    image: myapp/api:latest
    cap_add:
      - NET_ADMIN
    environment:
      - "DB_HOST=postgres"
      - "DB_NAME=api_db"
      - "DB_USER=api_user"
      - "DB_PASSWORD=DOCKER_SECRET:API_DB_PASSWORD"
      - "JWT_SECRET=DOCKER_SECRET:API_JWT_SECRET"
    extra_hosts:
      - "external_service:172.18.0.1"
    secrets:
      - API_DB_PASSWORD
      - API_JWT_SECRET
    networks:
      - app_network
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      replicas: 1
      restart_policy:
        condition: any

  postgres:
    image: postgres:15
    environment:
      - "POSTGRES_DB=api_db"
      - "POSTGRES_USER=api_user"
      - "POSTGRES_PASSWORD=DOCKER_SECRET:API_DB_PASSWORD"
    secrets:
      - API_DB_PASSWORD
    volumes:
      - /opt/volumes/postgres/data:/var/lib/postgresql/data
    networks:
      - app_network
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      replicas: 1
      restart_policy:
        condition: any
      placement:
        constraints:
          - node.role == manager

networks:
  app_network:
    driver: overlay
    attachable: true

secrets:
  API_DB_PASSWORD:
    external: true
  API_JWT_SECRET:
    external: true
```

**Key transformations applied:**
1. Removed: `container_name`, `depends_on`, `restart`
2. Converted: `privileged: true` → `cap_add: [NET_ADMIN]`
3. Replaced: All `$VAR` with actual values or `DOCKER_SECRET:` pattern
4. Added: `deploy` section with restart_policy, placement constraints for postgres
5. Changed: Network driver from `bridge` to `overlay`
6. Added: `secrets` section and service-level secret references
7. Added: Logging configuration with size limits

### Example 2: Final Report Format

```
=== Migration Complete ===

Source: ./docker-compose.yml (12 services)
Output: ./docker-stack.yml (12 services)

Transformations applied:
  - Removed: 12 container_name, 8 depends_on, 12 restart
  - Converted: 2 privileged → cap_add
  - Replaced: 47 environment variables
  - Created: 15 Docker secrets

Validation:
  [PASS] YAML syntax valid
  [PASS] No remaining $VAR placeholders
  [PASS] All secrets referenced correctly
  [PASS] Reference stack patterns match

Generated files:
  - docker-stack.yml
  - init-swarm.sh

Next steps:
  1. Review docker-stack.yml
  2. Run: ./init-swarm.sh .env
  3. Deploy: docker stack deploy -c docker-stack.yml eregistrations
```

## Dependencies

- Tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, TodoWrite
- Prerequisites: Docker installed, source docker-compose.yml exists
