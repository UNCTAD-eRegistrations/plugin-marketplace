---
name: docker-swarm-migration
description: >
  Convert Docker Compose files to Docker Swarm stack format for eRegistrations deployments.
  Handles env var replacement, secrets management, init-secrets.sh generation, reference
  stack validation, and dry-run preview. Use when migrating docker-compose.yml to
  docker-stack.yml, adding deploy sections, configuring overlay networks, or converting
  environment secrets to Docker Swarm secrets.
license: UNCTAD-Internal
compatibility: Requires access to eRegistrations deployment configuration repositories.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(docker *), Bash(ls *), Bash(diff *), Bash(git *), AskUserQuestion, TodoWrite
metadata:
  version: "2.0.0"
  version-date: "2026-03-27"
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
5. Generate init-secrets.sh scripts for secrets management
6. Compare against reference stack files for validation
7. Validate YAML syntax and completeness

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
question: "Generate init-secrets.sh script?"
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
    description: "Create docker-stack.yml and init-secrets.sh"
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

   --- init-secrets.sh (would be created) ---
   [full script content]

   --- Transformation Summary ---
   Services: X | Removed: Y container_name, Z depends_on | Secrets: N
   Variables replaced: M | Networks: bridge → overlay

   DRY-RUN COMPLETE - No files were modified
   ```
3. Skip Phase 7 file validation (no files to validate)

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
   - Any variable containing PASSWORD, SECRET, TOKEN, KEY
   - MongoDB URIs (contain credentials)

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
    condition: on-failure
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

Docker Swarm does NOT support .env file variable substitution. All `$VAR` placeholders must be replaced with actual values.

**CRITICAL: Never assume $VAR values without explicit user consent.**

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

Organize variables into logical groups and query:

- **Group 1: Domain & Infrastructure** — YOUR_DOMAIN_NAME, SERVICE_HOST, SYSTEM_CODE, TIME_ZONE
- **Group 2: Database Configuration** — *_POSTGRES_DB_NAME, *_POSTGRES_DB_USER, *_MONGO_DB_NAME
- **Group 3: Authentication** — *_OAUTH_CLIENT_ID, KEYCLOAK_REALM, KEYCLOAK_INSTITUTIONS_GROUP_ID
- **Group 4: Mail Configuration** — MAIL_HOST, MAIL_PORT, MAIL_USERNAME, MAIL_FROM
- **Group 5: Service Configuration** — MINIO_ROOT_USER, RESTHEART_USER, ACTIVEMQ_USER
- **Group 6: Timeouts & Other** — GUNICORN_HTTP_TIMEOUT, DEFAULT_LANGUAGE

For migrations with 20+ variables, use **TodoWrite** to track replacement progress per group.

Use **Edit** tool (preferred) to replace all placeholders.

**Checkpoint**: "All Y variables replaced. Zero remaining placeholders. Proceed to secrets setup?"

### Phase 5: Secrets Setup

Use **Grep** tool to identify secrets from source file.
Look for variables containing: PASSWORD, SECRET, TOKEN, KEY, URI (with credentials)

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

Some environment variables are composite URIs built from multiple components. These must be constructed in init-secrets.sh:

```bash
GRAYLOG_MONGODB_URI="mongodb://${GRAYLOG_MONGO_DB_USER}:${GRAYLOG_MONGO_DB_PASSWORD}@mongodb_host:27017/${GRAYLOG_MONGO_DB_NAME}"
create_secret "GRAYLOG_MONGODB_URI" "$GRAYLOG_MONGODB_URI"

FORMIO_MONGODB_URI="mongodb://${FORMIO_MONGO_DB_USER}:${FORMIO_MONGO_DB_PASSWORD}@docserver_mongo:27017/${FORMIO_MONGO_DB_NAME}"
create_secret "FORMIO_MONGODB_URI" "$FORMIO_MONGODB_URI"

RESTHEART_MONGO_URI="mongodb://${RESTHEART_MONGO_DB_USER}:${RESTHEART_MONGO_DB_PASSWORD}@${SERVICE_HOST}:27017"
create_secret "RESTHEART_MONGO_URI" "$RESTHEART_MONGO_URI"
```

### Phase 6: Generate init-secrets.sh (Optional)

If user requested, use **Write** tool to create init-secrets.sh with this template:

```bash
#!/bin/bash
# Initialize Docker Swarm secrets for [STACK_NAME] stack
# Generated: [DATE]
#
# Usage:
#   ./init-secrets.sh [OPTIONS] [ENV_FILE]
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
   - [ ] No remaining `$VAR` or `${VAR}` placeholders in output file
   - [ ] All `depends_on` directives removed
   - [ ] All `restart:` policies converted to `deploy.restart_policy`
   - [ ] All `container_name` directives removed
   - [ ] All `privileged: true` converted to specific `cap_add` capabilities
   - [ ] Networks changed from `bridge` to `overlay` driver
   - [ ] All sensitive variables converted to Docker secrets with `DOCKER_SECRET:` pattern
   - [ ] Secrets section added with all required secrets as `external: true`
   - [ ] Service count matches source docker-compose.yml
   - [ ] Stateful services have placement constraints (`node.role == manager`)
   - [ ] init-secrets.sh generated (if requested) with all identified secrets

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

- NEVER delete the source `docker-compose.yml` — the user decides when to remove it
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
| Secrets not found | Run init-secrets.sh before stack deploy |
| Network connectivity | Ensure overlay networks with attachable:true |
| Stateful services on multiple nodes | Add placement constraints |
| `container_name` ignored | Remove it; use service names instead |
| `privileged: true` fails | Use specific `cap_add` capabilities |
| Volume mounts on workers | Use placement constraints or named volumes |
| Port conflicts across nodes | Use `mode: host` for specific host binding |
| Memory issues (opensearch, etc.) | Add ulimits and deploy.resources limits |
| extra_hosts with $VAR | Replace $SERVICE_HOST with actual Docker host IP |
| Bash `((VAR++))` exits with `set -e` | Use `((VAR++)) \|\| true` |
| Service in reference but not source | Ask user — some services are optional |

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
6. Re-run init-secrets.sh
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
        condition: on-failure

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
        condition: on-failure

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
        condition: on-failure
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
  - init-secrets.sh

Next steps:
  1. Review docker-stack.yml
  2. Run: ./init-secrets.sh .env
  3. Deploy: docker stack deploy -c docker-stack.yml eregistrations
```

## Dependencies

- Tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, TodoWrite
- Prerequisites: Docker installed, source docker-compose.yml exists
