---
name: prepare-instance-for-live
description: >
  Generate `prepare-instance-for-live.sh` — a self-contained bash script
  that prepares a prelive eRegistrations instance for go-live by clearing
  all runtime/published artifacts. Drops and recreates the Camunda and
  ds-backend (`display_system`) Postgres databases (Camunda's
  `schema-update: true` re-bootstraps the engine schema on restart;
  Django runs migrations on startup), re-applies the post-recreate
  privileges the apps need (`pg_trgm` extension on display_system; read-only
  GRANTs to the statistics role on camunda), drops the Mongo `formio`
  database, and deletes the `_id: 'activeservices'` document from
  `documents.settings`. Service-block-scoped discovery against
  `docker-stack.yml` extracts per-instance Postgres DB names + owner roles
  + the statistics role name. Live backends are terminated via
  `pg_terminate_backend` before each `DROP DATABASE`. Idempotent. Typed
  instance-name confirmation rail. Admin users are not touched — they
  re-sync from Keycloak on next login.
license: UNCTAD-Internal
compatibility: >
  Requires a `docker-stack.yml` (swarm shape only — pre-swarm compose
  instances must run /docker-swarm-migration first). Postgres and MongoDB
  on the same host as the script (peer auth via `sudo -u postgres` for
  Postgres; TCP+admin password or `--mongo-noauth` for Mongo). Owner roles
  (`camunda`, `display_system`) and the statistics role must already exist
  on the Postgres cluster — this skill only manipulates databases, never
  roles. Application containers are NOT restarted by the generated script;
  the operator does that after the wipe.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(test *), Bash(ls *), Bash(grep *), AskUserQuestion, TodoWrite
metadata:
  version: "1.0.0"
  version-date: "2026-05-10"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<path-to-docker-stack.yml-or-instance-dir>"
  jira: "TOBE-17813"
---

You are an expert eRegistrations DevOps engineer. Your task is to read an instance's `docker-stack.yml`, identify the Postgres DBs + owner roles for `camunda` and `ds-backend` (and the statistics role that reads camunda data), and emit a single bash script that the operator runs on the DB host to bring the instance to a clean go-live state.

## Why this skill exists

Promoting a prelive instance to live requires wiping all runtime / published artifacts (test publishes, applicant filings, deployed processes) while keeping admin-side configuration intact (services in BPA admin UI, payment providers, branding, system translations, admin users).

The proven approach (May 2026) is small and well-defined:

1. Drop + recreate the **Camunda** Postgres database. Camunda's `schema-update: true` (in `application.yaml`) re-bootstraps the engine schema on next start, and Flyway re-applies the project's `ereg_*` migrations.
2. Drop + recreate the **ds-backend** (`display_system`) Postgres database. Django runs migrations on startup; admin users re-sync from Keycloak on next login.
3. Drop the Mongo **`formio`** database. The Formio service rebuilds nothing — schemas are re-published when BPA re-publishes services.
4. Delete the **`_id: 'activeservices'`** document from `documents.settings` so the cached active-service list doesn't claim services are live when they aren't.

Two non-obvious post-recreate steps are mandatory:

- **camunda** — the `statistics` role's read access has to be re-granted because GRANTs do not survive a `DROP DATABASE`.
- **display_system** — the `pg_trgm` extension is reset by `DROP DATABASE`; Django's trigram-search querysets fail without it.

Today this is an oral checklist. This skill turns it into a generated script with a confirmation rail and per-instance discovery.

## Core capabilities

1. Parse a service-block view of `docker-stack.yml`. For each of `camunda`, `ds-backend` (the DS Django service), and `statistics-backend` (or `statistics`), extract:
   - For camunda + ds-backend: `(database_name, owner_role)` from the service's environment and JDBC URL.
   - For statistics-backend: only the `*_USERNAME` (the role name; we don't drop or recreate the statistics DB).
2. Emit `prepare-instance-for-live.sh` with the discovered names baked in as constants. Mongo DB names (`formio`, `documents`) and the `activeservices` selector are also baked in (constant across instances).
3. The generated script supports `apply` / `--dry-run` / `--backup` and runs each operation in a SEPARATE `psql` invocation (because pre-drop, drop+create, and post-recreate need different connection targets).
4. Idempotent — `DROP DATABASE IF EXISTS` / `CREATE EXTENSION IF NOT EXISTS` / `dropDatabase` / `deleteOne` are all safe to re-run.
5. Database-only — refuses to `CREATE USER`, `ALTER ROLE`, `GRANT` on roles, drop additional Mongo DBs, or touch admin users.

## Reasoning principles

1. **`docker-stack.yml` is authoritative for "which DBs + which owners + which statistics role."** The skill never invents either. Discovery extracts names from the YAML; the generated script applies them at runtime.
2. **Database-only**. Never `CREATE USER`, never `CREATE/ALTER ROLE`. Roles are bootstrap concerns owned by other tooling. The skill's promise is "the user already exists; align database state."
3. **Termination is mandatory.** Live application connections will block `DROP DATABASE`. The script always runs `pg_terminate_backend` against the target DB before dropping, regardless of whether the operator stopped the application stack first. Belt-and-braces is cheap.
4. **Post-recreate steps are mandatory, not optional.** Skipping the camunda statistics GRANTs leaves the statistics service unable to read camunda data; skipping `pg_trgm` on display_system breaks Django trigram queries. The script always runs them; if the statistics role doesn't exist, fail loudly.
5. **Typed-name confirmation rail.** A go-live wipe is destructive enough that a yes/no prompt is too easy to mis-press. The script requires the operator to retype the instance name.
6. **Plaintext flows through `.env`** for any TCP fallback (Mongo admin, optional Postgres TCP). Same trust boundary as `init-swarm.sh` and `correct-db-passwords`. Never embed superuser credentials in the generated script.
7. **Application containers are not the skill's concern.** The generated script prints `docker service update --force …` reminders at the end; the operator runs them.

## Out of scope

- Creating users / roles / databases that don't exist (use bootstrap SQL / `init-swarm.sh`)
- ALTER ROLE attributes, role membership, password rotation
- Wiping admin users (they re-sync from Keycloak)
- Wiping the BPA `publish` table or any other RestHeart Mongo collection (confirmed unnecessary by the May 2026 prelive cleanup; if the need returns, separate skill)
- MinIO / S3 bucket cleanup (Django's `post_delete` signals + `services_*` rebuild from RestHeart make this unnecessary in practice)
- Camunda deployment delete via REST API (the DB recreate already handles deployments)
- Keycloak realm cleanup
- Public-pages CDN invalidation
- Restarting application containers
- MongoDB replica sets / sharded clusters — single-node `mongod` only
- Postgres servers reachable only via TCP from a different host (out of scope per the eRegistrations stack convention; `--pg-tcp` opt-in handles dockerized-postgres-on-same-host only)

## Stack shapes

The skill recognizes the same Shape A / Shape B / mixed split as `correct-db-passwords`:

- **Shape A — compose / variable-driven.** Service env lines reference `.env` variables: `DATABASE_NAME=$DS_POSTGRES_DB_NAME`, `DATABASE_USERNAME=$DS_POSTGRES_DB_USER`. Discovery resolves the name at skill time by looking up the `.env` next to the stack file (if available) or prompts for the value (if `.env` is not locally checked out).
- **Shape B — swarm post-cleanup.** Service env lines have hardcoded literals: `DATABASE_NAME=display_system`, `DATABASE_USERNAME=display_system`. Discovery uses the literal directly. Most modern instances are Shape B post-`docker-swarm-migration`.
- **Mixed.** Per-slot — a service can have a literal user but an envvar database name. The encoding handles each slot independently.

For password-only operations, this skill needs neither passwords nor admin credentials at generation time. Discovery only needs DB name + owner role + statistics role.

## Workflow

### Phase 1 — Input gathering

Use **AskUserQuestion** for missing values. If `$ARGUMENTS[0]` is provided, treat it as the stack path or its parent directory and skip Question 1.

**Question 1 — Source stack file:**
```
question: "Path to docker-stack.yml (or its containing directory)?"
options:
  - label: "./docker-stack.yml (Recommended)"
  - label: "Custom path"
default: "./docker-stack.yml"
```

If a directory is supplied, look for `docker-stack.yml` inside it. If only `docker-compose.yml` is found, abort with: *"prepare-instance-for-live targets swarm-shape stacks only. Run /docker-swarm-migration first, or apply the operations manually."*

**Question 2 — `.env` (optional, only when Shape A vars are detected):**
```
question: "Path to .env (skip if .env lives only on the deployment host)?"
options:
  - label: "Sibling of the stack file (Recommended)"
  - label: "Custom path"
  - label: "Not available — prompt for each Shape A var"
default: "Sibling of the stack file"
```

Skip this question entirely if the discovered DB name + owner + statistics role are all literals (Shape B).

**Question 3 — Instance name (for the typed-confirmation rail):**
```
question: "Instance name (for the script's typed-name confirmation prompt)?"
default: <derived from the directory containing the stack file>
```

The default is the deepest directory name in the stack-file path (e.g. `Conf-PREVIEW/compose/lesotho/docker-stack.yml` → `lesotho`). The operator can override.

**Question 4 — Output location:**
```
question: "Where should prepare-instance-for-live.sh be written?"
options:
  - label: "Same directory as the stack file (Recommended)"
  - label: "Custom path"
default: "Same directory as the stack file"
```

**Question 5 — Dry-run:**
```
question: "Generate in dry-run mode (preview only, no file written)?"
options:
  - label: "No — write the script (Recommended)"
  - label: "Yes — preview only"
default: "No"
```

### Phase 2 — Discovery

Service-block-scoped (NOT regex over the whole file). Walk `docker-stack.yml` once and collect:

**`camunda` service block** — required. If absent, abort.
- `db_source` — first match wins:
  - `POSTGRES_DB` env line
  - `DATABASE_NAME` env line
  - Path component of `SPRING_DATASOURCE_URL=jdbc:postgresql://host:port/<db>` (also handles `<db>?params`)
- `owner_source` — first match wins:
  - `SPRING_DATASOURCE_USERNAME` env line
  - `POSTGRES_USER` env line
- Default if all missing (rare): `camunda` for both.

**`ds-backend` service block** — required. If absent, abort with: *"ds-backend service block not found. This skill targets stacks that include ds-backend; use a different cleanup approach if the instance has no DS."*
- `db_source` — first match wins:
  - `DATABASE_NAME` env line
  - `POSTGRES_DB` env line
  - Path component of any `*_URL=jdbc:postgresql://...` (rare for Django; included for completeness)
- `owner_source` — first match wins:
  - `DATABASE_USERNAME` env line
  - `POSTGRES_USER` env line
- Canonical defaults: `display_system` for both.

**`statistics-backend` (or `statistics`) service block** — optional.
- `role_source` — first match wins:
  - `SPRING_DATASOURCE_USERNAME` env line
  - `DATABASE_USERNAME` env line
  - `POSTGRES_USER` env line
- Default if the service block is absent or has no username line: `statistics`. Note this in the discovery summary so the operator can correct via `--statistics-role` at script run time if needed.

Classify each slot the same way `correct-db-passwords` does (see its lines 211-223): `literal:<value>` if the YAML value is plain, `envvar:<NAME>` if it starts with `$` / `${...}`. For envvar slots, look up the `.env` next to the stack (when available) and resolve to a runtime value. If `.env` isn't locally checked out, **the skill prompts** for each Shape A var rather than guessing.

**Checkpoint** — print the discovery table to the user before writing anything:

```
=== Discovery ===
Stack:    <relative path>     Shape: <A | B | mixed>
.env:     <path | "deferred to runtime">
Instance: <derived or operator-supplied>

Postgres targets:
  service              db                  owner               role kind
  camunda              camunda             camunda             literal | envvar
  ds-backend           display_system      display_system      literal | envvar

Statistics role (read-only on camunda):
  service              role                kind
  statistics-backend   statistics          literal | envvar | <default>

Mongo (constants):
  drop database 'formio'
  delete documents.settings { _id: 'activeservices' }

Proceed?
```

If any slot is missing and unprompt-able (e.g. statistics-backend block absent), surface the default and the assumption explicitly. The operator types `y` (or any non-empty answer) to proceed.

### Phase 3 — Connection-credential strategy

Same defaults as `correct-db-passwords` (see its lines 266-291):

- **Postgres — peer auth** via `sudo -u postgres psql` (default). Most eRegistrations DB hosts have an operator account with sudo to the `postgres` OS user, which maps to the `postgres` superuser DB role via peer auth on the local Unix socket. No password handling.
- **Postgres — TCP fallback** via `--pg-tcp`. The script connects via `PGPASSWORD=$PG_TCP_PASSWORD psql -h $SERVICE_HOST -p 5432 -U $PG_TCP_USER`. `PG_TCP_PASSWORD` is prompted (silent) at run time if unset.
- **MongoDB — TCP+admin password** (default). The script connects via `mongodb://$MONGO_ADMIN_USER:$MONGO_ADMIN_PASSWORD@$SERVICE_HOST:27017/admin?authSource=admin`. `MONGO_ADMIN_PASSWORD` is prompted (silent) at run time if unset.
- **MongoDB — no-auth opt-in** via `--mongo-noauth`. Connects to `mongodb://$SERVICE_HOST:27017` without credentials. Common in single-node DEV setups.

The skill does NOT ask the user about these at generation time — defaults match every standard eRegistrations DB host.

**Hard-coding super-credentials remains forbidden.** Refuse if asked to embed `PG_TCP_PASSWORD` or `MONGO_ADMIN_PASSWORD` in the generated file. Explain: *"Super-credentials must be passed at runtime via env or prompt. Refusing to embed them in a checked-out file."*

### Phase 4 — Generation

Use **Write** to emit `prepare-instance-for-live.sh` from the template in *Generated script*.

Substitution points:
- `__GENERATED_AT__` → ISO-8601 timestamp (UTC)
- `__STACK_FILE__` → relative path to the stack file
- `__INSTANCE_NAME__` → operator-supplied or derived from path
- `__CAMUNDA_DB__`, `__CAMUNDA_USER__` → literals or `$VAR` references
- `__DS_DB__`, `__DS_USER__` → literals or `$VAR` references
- `__STATISTICS_ROLE__` → literal or `$VAR` reference
- `__SERVICE_HOST_FALLBACK__` → literal `127.0.0.1`

For envvar slots, render the substitution as `$VAR_NAME`; the script's runtime `set -a; source .env; set +a` resolves them. For literal slots, render the literal directly.

If dry-run was selected, print the rendered script + the discovery table to chat instead of writing.

### Phase 5 — Validation

1. **Smoke** — `test -f prepare-instance-for-live.sh`.
2. **Round-trip** — `grep` the rendered script for `CAMUNDA_DB=` / `DS_DB=` / `STATISTICS_ROLE=` lines; their values must match the discovery table.
3. **No literal passwords** — `grep -E "PASSWORD\s*=\s*['\"][^$]" prepare-instance-for-live.sh` must return empty.
4. **Final summary** echoes the discovery table from Phase 2 plus the next-step instructions:
   ```
   === prepare-instance-for-live.sh ready ===

   Stack:    <relative path>           Shape: <A | B | mixed>
   Output:   <relative path>
   Instance: <name>

   <Postgres + statistics + Mongo tables, same shape as Phase 2>

   Next steps on the deployment host:
     1. (Optional) Stop the application stack: docker stack rm <stack>
     2. scp prepare-instance-for-live.sh to /opt/eregistrations/<env>/compose/<country>/
     3. cd to that directory (where .env lives, if Shape A)
     4. chmod +x prepare-instance-for-live.sh
     5. Dry-run:   ./prepare-instance-for-live.sh -n
     6. Apply:     ./prepare-instance-for-live.sh
     7. Redeploy:  docker stack deploy -c docker-stack.yml <stack>
   ```

## Generated script

```bash
#!/usr/bin/env bash
# prepare-instance-for-live.sh
# Generated by /devops:prepare-instance-for-live on __GENERATED_AT__
# Source stack: __STACK_FILE__
#
# Operations (in order, all idempotent):
#   1. Terminate live backends on '__CAMUNDA_DB__'
#      DROP + CREATE DATABASE '__CAMUNDA_DB__' OWNER '__CAMUNDA_USER__'
#      Re-grant read-only access on camunda to '__STATISTICS_ROLE__'
#   2. Terminate live backends on '__DS_DB__'
#      DROP + CREATE DATABASE '__DS_DB__' OWNER '__DS_USER__'
#      CREATE EXTENSION IF NOT EXISTS pg_trgm  (Django trigram search)
#   3. Drop Mongo database 'formio'
#   4. Delete documents.settings { _id: 'activeservices' }
#
# Usage:
#   ./prepare-instance-for-live.sh [OPTIONS] [ENV_FILE]
#
# Options:
#   -n, --dry-run             Print what would run; do not connect
#   -b, --backup              pg_dump (camunda + display_system) and
#                             mongodump (formio + documents.settings) before
#                             wiping. Default: off.
#       --backup-dir DIR      Where to write backups (default: ./backup-<UTC>)
#       --pg-tcp              Use TCP+password instead of peer auth
#       --mongo-noauth        Connect to Mongo without admin credentials
#       --statistics-role NM  Override discovered statistics role
#   -y, --yes                 Skip the typed-instance-name confirmation rail
#   -h, --help                Show this help
#
# Postgres (default: peer auth via sudo):
#   PG_OS_USER            OS user to sudo to (default: postgres)
#
# Postgres (TCP override, --pg-tcp or PG_VIA=tcp):
#   PG_TCP_USER           (default: postgres)
#   PG_TCP_PASSWORD       (prompted silently if unset)
#
# MongoDB (TCP):
#   MONGO_ADMIN_USER      (default: admin)
#   MONGO_ADMIN_PASSWORD  (prompted silently if unset)
#   --mongo-noauth        no-auth opt-in
#
# Honoured from .env (when ENV_FILE points at a sourceable file):
#   SERVICE_HOST          (default: __SERVICE_HOST_FALLBACK__) — Mongo +
#                         (when --pg-tcp) Postgres
#   plus any $VAR references baked into CAMUNDA_DB / CAMUNDA_USER /
#   DS_DB / DS_USER / STATISTICS_ROLE below.

set -eu
set -o pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

# -- Substituted at skill-generation time --
INSTANCE_NAME="__INSTANCE_NAME__"
CAMUNDA_DB="__CAMUNDA_DB__"
CAMUNDA_USER="__CAMUNDA_USER__"
DS_DB="__DS_DB__"
DS_USER="__DS_USER__"
STATISTICS_ROLE="__STATISTICS_ROLE__"

# -- Constants (same across all instances) --
MONGO_FORMIO_DB="formio"
MONGO_DOCS_DB="documents"
MONGO_SETTINGS_COL="settings"
MONGO_ACTIVESERVICES_ID="activeservices"

# -- Defaults --
MODE="apply"
DO_BACKUP="false"
BACKUP_DIR=""
ENV_FILE=""
SKIP_CONFIRM="false"
PG_VIA="${PG_VIA:-peer}"
MONGO_AUTH="${MONGO_AUTH:-required}"

show_help() {
    sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--dry-run)        MODE="dry-run"; shift ;;
        -b|--backup)         DO_BACKUP="true"; shift ;;
        --backup-dir)        BACKUP_DIR="${2:?--backup-dir requires a value}"; shift 2 ;;
        --pg-tcp)            PG_VIA="tcp"; shift ;;
        --mongo-noauth)      MONGO_AUTH="none"; shift ;;
        --statistics-role)   STATISTICS_ROLE="${2:?--statistics-role requires a value}"; shift 2 ;;
        -y|--yes)            SKIP_CONFIRM="true"; shift ;;
        -h|--help)           show_help; exit 0 ;;
        -*) echo -e "${RED}Unknown option: $1${NC}" >&2; exit 1 ;;
        *)  ENV_FILE="$1"; shift ;;
    esac
done

[[ -z "$BACKUP_DIR" ]] && BACKUP_DIR="./backup-$(date -u +%Y%m%dT%H%M%SZ)"

# Source .env when one is supplied (or autodetected next to the script).
if [[ -z "$ENV_FILE" && -f "./.env" ]]; then
    ENV_FILE="./.env"
fi
if [[ -n "$ENV_FILE" ]]; then
    if [[ ! -f "$ENV_FILE" ]]; then
        echo -e "${RED}Error: env file not found: $ENV_FILE${NC}" >&2
        exit 1
    fi
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

SERVICE_HOST="${SERVICE_HOST:-__SERVICE_HOST_FALLBACK__}"

# Resolve a slot: $VAR → ${VAR}; otherwise the literal.
resolve_kv() {
    local raw="$1"
    if [[ "$raw" == \$* ]]; then
        local name="${raw:1}"
        printf '%s' "${!name:-}"
    else
        printf '%s' "$raw"
    fi
}

CAMUNDA_DB_R="$(resolve_kv "$CAMUNDA_DB")"
CAMUNDA_USER_R="$(resolve_kv "$CAMUNDA_USER")"
DS_DB_R="$(resolve_kv "$DS_DB")"
DS_USER_R="$(resolve_kv "$DS_USER")"
STATISTICS_ROLE_R="$(resolve_kv "$STATISTICS_ROLE")"

# -- Preflight --
preflight() {
    local missing=()
    [[ -z "$CAMUNDA_DB_R"      ]] && missing+=("camunda DB ($CAMUNDA_DB)")
    [[ -z "$CAMUNDA_USER_R"    ]] && missing+=("camunda owner ($CAMUNDA_USER)")
    [[ -z "$DS_DB_R"           ]] && missing+=("ds-backend DB ($DS_DB)")
    [[ -z "$DS_USER_R"         ]] && missing+=("ds-backend owner ($DS_USER)")
    [[ -z "$STATISTICS_ROLE_R" ]] && missing+=("statistics role ($STATISTICS_ROLE)")
    if (( ${#missing[@]} > 0 )); then
        echo -e "${RED}Aborted - cannot resolve:${NC}" >&2
        printf '  - %s\n' "${missing[@]}" >&2
        exit 1
    fi
}

# -- psql wrappers --
pg_psql() {
    # Args: <connect-db> <sql-stdin>
    local db="$1"; shift
    if [[ "$PG_VIA" = "tcp" ]]; then
        PGPASSWORD="${PG_TCP_PASSWORD:-}" psql \
            -h "$SERVICE_HOST" -p 5432 -U "${PG_TCP_USER:-postgres}" -d "$db" \
            -v ON_ERROR_STOP=1 "$@"
    else
        sudo -u "${PG_OS_USER:-postgres}" psql \
            -d "$db" -v ON_ERROR_STOP=1 "$@"
    fi
}

# -- SQL emitters --
emit_pre_drop() {
    local db="$1"
    cat <<SQL
SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
 WHERE datname = '$db' AND pid <> pg_backend_pid();
SQL
}

emit_drop_create() {
    local db="$1" owner="$2"
    cat <<SQL
DROP DATABASE IF EXISTS "$db";
CREATE DATABASE "$db" OWNER "$owner";
SQL
}

emit_camunda_post() {
    cat <<SQL
GRANT CONNECT ON DATABASE "$CAMUNDA_DB_R" TO "$STATISTICS_ROLE_R";
GRANT USAGE ON SCHEMA public TO "$STATISTICS_ROLE_R";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "$STATISTICS_ROLE_R";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO "$STATISTICS_ROLE_R";
SQL
}

emit_ds_post() {
    cat <<SQL
CREATE EXTENSION IF NOT EXISTS pg_trgm;
SQL
}

emit_mongo_js() {
    cat <<JS
const fr = db.getSiblingDB('$MONGO_FORMIO_DB').dropDatabase();
print('formio dropDatabase ok=' + fr.ok);
const dr = db.getSiblingDB('$MONGO_DOCS_DB')
              .getCollection('$MONGO_SETTINGS_COL')
              .deleteOne({ _id: '$MONGO_ACTIVESERVICES_ID' });
print('documents.settings activeservices deleted=' + dr.deletedCount);
JS
}

# -- Apply / dry-run wrappers --
do_pg_step() {
    local label="$1" connect_db="$2"; shift 2
    if [[ "$MODE" = "dry-run" ]]; then
        echo -e "${CYAN}-- $label (dry-run, connect=$connect_db) --${NC}"
        cat
        return
    fi
    pg_psql "$connect_db" <<< "$(cat)" >/dev/null
    echo -e "${GREEN}[OK] $label${NC}"
}

do_mongo_step() {
    local label="$1" mongo_uri="$2"; shift 2
    if [[ "$MODE" = "dry-run" ]]; then
        echo -e "${CYAN}-- $label (dry-run) --${NC}"
        cat
        return
    fi
    mongosh --quiet "$mongo_uri" --eval "$(cat)"
    echo -e "${GREEN}[OK] $label${NC}"
}

# -- Backup --
ensure_backup_dir() { mkdir -p "$BACKUP_DIR" "$BACKUP_DIR/mongo"; }

backup_pg() {
    local db="$1"
    local out="$BACKUP_DIR/postgres-$db.sql"
    echo -e "${CYAN}pg_dump $db -> $out${NC}"
    if [[ "$PG_VIA" = "tcp" ]]; then
        PGPASSWORD="${PG_TCP_PASSWORD:-}" pg_dump \
            -h "$SERVICE_HOST" -p 5432 -U "${PG_TCP_USER:-postgres}" \
            --create --clean "$db" > "$out"
    else
        sudo -u "${PG_OS_USER:-postgres}" pg_dump --create --clean "$db" > "$out"
    fi
}

backup_mongo() {
    local mongo_uri="$1"
    echo -e "${CYAN}mongodump formio + documents -> $BACKUP_DIR/mongo${NC}"
    mongodump --uri "$mongo_uri" --db "$MONGO_FORMIO_DB" --out "$BACKUP_DIR/mongo" --quiet
    mongodump --uri "$mongo_uri" --db "$MONGO_DOCS_DB" --collection "$MONGO_SETTINGS_COL" \
        --query "{\"_id\":\"$MONGO_ACTIVESERVICES_ID\"}" \
        --out "$BACKUP_DIR/mongo" --quiet
}

# -- Confirm --
confirm() {
    if [[ "$SKIP_CONFIRM" = "true" ]]; then
        return
    fi
    cat <<EOF

About to wipe instance '${YELLOW}${INSTANCE_NAME}${NC}' on $(hostname):
  Postgres:
    - DROP + CREATE "$CAMUNDA_DB_R" OWNER "$CAMUNDA_USER_R"
        + GRANT to "$STATISTICS_ROLE_R"
    - DROP + CREATE "$DS_DB_R" OWNER "$DS_USER_R"
        + CREATE EXTENSION pg_trgm
  Mongo:
    - dropDatabase('$MONGO_FORMIO_DB')
    - documents.settings.deleteOne({ _id: '$MONGO_ACTIVESERVICES_ID' })

Backup: $DO_BACKUP (dir: $BACKUP_DIR)

EOF
    read -rp "Type the instance name ('$INSTANCE_NAME') to proceed: " typed
    if [[ "$typed" != "$INSTANCE_NAME" ]]; then
        echo -e "${RED}Aborted by operator.${NC}" >&2
        exit 1
    fi
}

# -- main --
preflight

# Compute Mongo URI now (used by both backup and apply).
case "$MONGO_AUTH" in
    none)
        MONGO_URI="mongodb://${SERVICE_HOST}:27017"
        ;;
    *)
        if [[ -z "${MONGO_ADMIN_PASSWORD:-}" && "$MODE" != "dry-run" ]]; then
            read -rsp "MONGO_ADMIN_PASSWORD: " MONGO_ADMIN_PASSWORD; echo
        fi
        MONGO_URI="mongodb://${MONGO_ADMIN_USER:-admin}:${MONGO_ADMIN_PASSWORD:-}@${SERVICE_HOST}:27017/admin?authSource=admin"
        ;;
esac

if [[ "$PG_VIA" = "tcp" && -z "${PG_TCP_PASSWORD:-}" && "$MODE" != "dry-run" ]]; then
    read -rsp "PG_TCP_PASSWORD: " PG_TCP_PASSWORD; echo
fi

confirm

if [[ "$DO_BACKUP" = "true" && "$MODE" != "dry-run" ]]; then
    ensure_backup_dir
    backup_pg "$CAMUNDA_DB_R"
    backup_pg "$DS_DB_R"
    backup_mongo "$MONGO_URI"
fi

# 1. Camunda
emit_pre_drop "$CAMUNDA_DB_R" \
  | do_pg_step "camunda: terminate backends" "postgres"
emit_drop_create "$CAMUNDA_DB_R" "$CAMUNDA_USER_R" \
  | do_pg_step "camunda: drop+create" "postgres"
emit_camunda_post \
  | do_pg_step "camunda: grant statistics" "$CAMUNDA_DB_R"

# 2. ds-backend / display_system
emit_pre_drop "$DS_DB_R" \
  | do_pg_step "display_system: terminate backends" "postgres"
emit_drop_create "$DS_DB_R" "$DS_USER_R" \
  | do_pg_step "display_system: drop+create" "postgres"
emit_ds_post \
  | do_pg_step "display_system: pg_trgm" "$DS_DB_R"

# 3 + 4. Mongo
emit_mongo_js | do_mongo_step "mongo: drop formio + delete activeservices" "$MONGO_URI"

cat <<EOF

${GREEN}Done.${NC} Recommended next steps:

  docker service update --force <stack>_bpa-backend
  docker service update --force <stack>_camunda
  docker service update --force <stack>_ds-backend

EOF
```

The `pg_psql` wrapper takes a connect-db argument because pre-drop must run against `postgres` (not the target DB), drop+create runs against `postgres` (DROP DATABASE refuses to run from inside the target DB), and the post-recreate steps run against the freshly-created DB.

## Examples

### Example 1 — Shape B discovery (canonical post-cleanup stack)

Source `docker-stack.yml`:

```yaml
camunda:
  environment:
    - "SPRING_DATASOURCE_URL=jdbc:postgresql://postgres_host:5432/camunda"
    - "SPRING_DATASOURCE_USERNAME=camunda"
    - "SPRING_DATASOURCE_PASSWORD=DOCKER_SECRET:CAMUNDA_POSTGRES_DB_PASSWORD"

ds-backend:
  environment:
    - "DATABASE_NAME=display_system"
    - "DATABASE_USERNAME=display_system"
    - "DATABASE_PASSWORD=DOCKER_SECRET:DS_POSTGRES_DB_PASSWORD"

statistics-backend:
  environment:
    - "SPRING_DATASOURCE_USERNAME=statistics"
```

Generated substitutions:
```
INSTANCE_NAME="lesotho"
CAMUNDA_DB="camunda"
CAMUNDA_USER="camunda"
DS_DB="display_system"
DS_USER="display_system"
STATISTICS_ROLE="statistics"
```

### Example 2 — Shape A discovery (older variable-driven stack)

Source `docker-compose.yml`:

```yaml
camunda:
  environment:
    - "SPRING_DATASOURCE_URL=jdbc:postgresql://postgres_host:5432/$CAMUNDA_POSTGRES_DB_NAME"
    - "SPRING_DATASOURCE_USERNAME=$CAMUNDA_POSTGRES_DB_USER"

ds-backend:
  environment:
    - "DATABASE_NAME=$DS_POSTGRES_DB_NAME"
    - "DATABASE_USERNAME=$DS_POSTGRES_DB_USER"
```

Generated substitutions (envvar slots preserved as `$VAR`; resolved at script runtime via `set -a; source .env`):
```
CAMUNDA_DB="$CAMUNDA_POSTGRES_DB_NAME"
CAMUNDA_USER="$CAMUNDA_POSTGRES_DB_USER"
DS_DB="$DS_POSTGRES_DB_NAME"
DS_USER="$DS_POSTGRES_DB_USER"
STATISTICS_ROLE="statistics"   # default; statistics service block absent
```

This is the only case where Shape A would still apply — `prepare-instance-for-live` requires swarm shape (`docker-stack.yml`), so most invocations will see Shape B. Shape A support is kept for completeness; if encountered, abort and instruct the operator to run `/docker-swarm-migration` first.

### Example 3 — Final summary

```
=== prepare-instance-for-live.sh ready ===

Stack:    Conf-PREVIEW/compose/lesotho/docker-stack.yml
Output:   Conf-PREVIEW/compose/lesotho/prepare-instance-for-live.sh
Instance: lesotho                            Shape: B

Postgres targets:
  service              db                  owner               role kind
  camunda              camunda             camunda             literal
  ds-backend           display_system      display_system      literal

Statistics role (read-only on camunda):
  service              role                kind
  statistics-backend   statistics          literal

Mongo (constants):
  drop database 'formio'
  delete documents.settings { _id: 'activeservices' }

Notes:
  - Owner roles + statistics role assumed to already exist on the Postgres cluster
  - Generated script does NOT restart application containers

Next steps on the deployment host:
  1. (Optional) Stop the application stack: docker stack rm lesotho
  2. scp prepare-instance-for-live.sh to /opt/eregistrations/Conf-PREVIEW/compose/lesotho/
  3. cd to that directory
  4. chmod +x prepare-instance-for-live.sh
  5. Dry-run:   ./prepare-instance-for-live.sh -n
  6. Apply:     ./prepare-instance-for-live.sh
  7. Redeploy:  docker stack deploy -c docker-stack.yml lesotho
```

## CRITICAL RULES

- NEVER embed plaintext passwords (Postgres TCP, Mongo admin) in `prepare-instance-for-live.sh`. Reference variable names; let `set -a; source .env` resolve them at runtime.
- NEVER add `CREATE USER`, `CREATE ROLE`, `ALTER ROLE`, or password rotation. Owner roles and the statistics role MUST exist already.
- NEVER drop additional Mongo databases. The only Mongo writes are `formio.dropDatabase()` and one `documents.settings.deleteOne` for `_id: 'activeservices'`.
- NEVER skip the `pg_terminate_backend` step. Live application connections will block `DROP DATABASE`; without termination the script fails halfway through.
- NEVER skip the camunda `GRANT … TO statistics` block or the display_system `CREATE EXTENSION pg_trgm` block. Both are mandatory post-recreate state.
- NEVER hard-code superuser/admin credentials, even on user request. Decline with the same wording as `correct-db-passwords`.
- If the Camunda or ds-backend service block is missing from the stack file, abort. This skill is for stacks that contain both.
- If `docker-compose.yml` is supplied instead of `docker-stack.yml`, abort with a pointer to `/docker-swarm-migration`.
- ALWAYS chmod is the operator's job — do not call `chmod` from inside this skill.

## Companion skills

| Concern | Where it lives |
|---|---|
| Build the swarm-shape stack file | `/devops:docker-swarm-migration` |
| Sync DB-side passwords with `.env` after a swarm migration | `/devops:correct-db-passwords` |
| Stand up a new draft (UAT) instance from a LIVE one | `/devops:create-draft-instance` |
| Promote a prelive instance to live (this skill) | `/devops:prepare-instance-for-live` |
| Roll an instance up a platform version | `/devops:upgrade-eregistrations-instance` |

Run order for a typical prelive→live promotion (operator-facing):

1. `/devops:prepare-instance-for-live` against the prelive's `docker-stack.yml` → produces `prepare-instance-for-live.sh`
2. (Optional) `docker stack rm <stack>` to drain application containers — not required because the script terminates backends explicitly, but cleaner.
3. Run the generated script on the deployment host.
4. `docker stack deploy -c docker-stack.yml <stack>` (or `docker service update --force …` for individual services).
5. Smoke-test the now-empty instance; re-publish services from BPA admin as needed; admin users land via Keycloak login.

## Dependencies

- Tools (skill): Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, TodoWrite
- Tools (generated script, on the deployment host): bash 4+, `psql` + `pg_dump` (postgresql-client), `mongosh` + `mongodump`, `sudo` (for peer auth)
- Prerequisites: `docker-stack.yml` containing both `camunda` and `ds-backend` service blocks; Postgres + MongoDB on the same host as the script; owner roles (`camunda`, `display_system`) and the statistics role already exist on the Postgres cluster.
