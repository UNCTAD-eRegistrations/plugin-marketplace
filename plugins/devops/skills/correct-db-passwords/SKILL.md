---
name: correct-db-passwords
description: >
  Generate a script that resets PostgreSQL and MongoDB user passwords on the DB
  hosts backing an eRegistrations Docker Swarm stack to match the values in the
  stack's .env file. Discovers `*_POSTGRES_DB_USER` / `*_POSTGRES_DB_NAME` and
  `*_MONGO_DB_USER` / `*_MONGO_DB_NAME` triples from `docker-stack.yml` (or
  `docker-compose.yml`), reads the matching `*_PASSWORD` values from `.env`,
  and emits `sync-db-passwords.sh` — a self-contained bash script that runs
  `ALTER USER` on Postgres and `db.changeUserPassword` on MongoDB. Use after
  rotating Docker secrets, after migrating an instance from compose to swarm,
  or whenever DB-side credentials have drifted from the values applications
  expect. Idempotent. Password-only — never creates users or databases.
license: UNCTAD-Internal
compatibility: >
  Requires the eRegistrations docker-stack.yml (or docker-compose.yml) and its
  sibling .env file. Assumes Postgres reachable at `$SERVICE_HOST:5432` and
  MongoDB at `$SERVICE_HOST:27017` from the host that will run the generated
  script. The operator running the generated script needs Postgres superuser
  credentials and MongoDB admin credentials.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(test *), Bash(ls *), Bash(grep *), Bash(diff *), AskUserQuestion, TodoWrite
metadata:
  version: "1.0.0"
  version-date: "2026-05-04"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<path-to-docker-stack.yml-or-instance-dir>"
  jira: "TOBE-17731"
---

You are an expert eRegistrations DevOps engineer. Your task is to read an instance's `docker-stack.yml` (or `docker-compose.yml`) plus its `.env` file, identify every PostgreSQL and MongoDB application user the stack expects, and emit a single bash script that aligns the DB-side passwords with the `.env` values.

## Why this skill exists

`/docker-swarm-migration` produces `init-swarm.sh`, which puts the desired passwords into Docker secrets so the application containers can read them. That handles the **application side** only. The **server side** — the `postgres` and `mongod` processes the apps connect to — already has its own users with their own (possibly older) passwords.

When secrets are rotated, when an instance is moved from compose to swarm, or when an operator hand-edits `.env`, the two sides drift. This skill produces the matching `sync-db-passwords.sh` so the same `.env` file that feeds `init-swarm.sh` is also the source of truth for the DB users themselves.

## Core capabilities

1. Parse `docker-stack.yml` / `docker-compose.yml` for service env vars referencing `*_POSTGRES_DB_USER` / `*_POSTGRES_DB_NAME` / `*_MONGO_DB_USER` / `*_MONGO_DB_NAME`
2. Pair each user with its matching `*_PASSWORD` env var by family prefix (e.g. `BPA_POSTGRES_DB_USER` → `BPA_POSTGRES_DB_PASSWORD`)
3. Validate every pairing has a value in `.env`
4. Emit `sync-db-passwords.sh` with three modes (apply / dry-run / generate-sql-files)
5. Idempotency by construction — `ALTER USER` and `db.changeUserPassword` are safe to re-run
6. Refuse to invent users or databases — if a user is referenced in the stack but missing from `.env`, list it and abort

## Reasoning principles

1. **Stack is authoritative for "which users"; .env is authoritative for "what password"**. The skill never invents either side. If a service references `$FOO_POSTGRES_DB_USER` and `.env` has no `FOO_POSTGRES_DB_PASSWORD`, that's an abort, not a default.
2. **Password-only**. Never `CREATE USER`, never `CREATE DATABASE`, never grant privileges. Those are bootstrap concerns owned by other tooling. This skill's promise is "the user already exists; align its password."
3. **Idempotent over clever**. Running the generated script twice is exactly the same as running it once. No rollback table, no "skip if unchanged" logic — just re-apply.
4. **Plaintext flows through `.env`**. Same trust boundary as `init-swarm.sh`. Don't add new password-handling primitives; reuse the pattern operators already understand.
5. **Server is reachable, or we abort cleanly**. The generated script must fail fast on connection issues — never silently skip a user.
6. **Quote everything**. Passwords commonly contain `'`, `"`, `\`, `$`. The generated script must escape correctly for both psql and mongosh contexts (see *Escaping rules* below).

## Out of scope

- Creating users or databases (use bootstrap SQL / Mongo init scripts)
- Granting privileges, ALTER ROLE attributes, role membership
- Rotating Docker secrets (that's `/docker-swarm-migration`'s init-swarm.sh and `--generate` mode)
- Connecting to managed/cloud DBs over TLS with custom auth (PG superuser + Mongo admin only)
- Reading passwords from Docker secrets at runtime — this script reads `.env`, same as `init-swarm.sh`
- MongoDB replica sets / sharded clusters — single-node `mongod` only (eRegistrations production shape)
- Postgres roles other than the per-service application roles (not `postgres`, not replication roles)
- Anything cross-host — the generated script targets one Postgres + one MongoDB at `$SERVICE_HOST`

If the user asks for any of the above, explain the limitation and point to the right tool.

## Workflow

### Phase 1: Input gathering

Use **AskUserQuestion** for missing values. If `$ARGUMENTS[0]` is provided, treat it as the stack path or its parent directory and skip Question 1.

**Question 1 — Source stack file:**
```
question: "Path to docker-stack.yml (or its containing directory)?"
options:
  - label: "./docker-stack.yml (Recommended)"
    description: "Use docker-stack.yml in the current directory"
  - label: "./docker-compose.yml"
    description: "Pre-swarm shape; the skill still works"
  - label: "Custom path"
    description: "Specify a different file or directory"
default: "./docker-stack.yml"
```

If a directory is supplied, prefer `docker-stack.yml` over `docker-compose.yml`. If both are absent, abort.

**Question 2 — .env file:**
```
question: "Where is the .env file with the desired passwords?"
options:
  - label: "Sibling of the stack file (Recommended)"
    description: "Look for .env next to docker-stack.yml"
  - label: "Custom path"
    description: "Specify a different .env path"
default: "Sibling of the stack file"
```

**Question 3 — Output location:**
```
question: "Where should sync-db-passwords.sh be written?"
options:
  - label: "Same directory as the stack file (Recommended)"
    description: "Write alongside docker-stack.yml + init-swarm.sh"
  - label: "Custom path"
    description: "Specify a different output path"
default: "Same directory as the stack file"
```

**Question 4 — Dry-run:**
```
question: "Generate in dry-run mode (preview only, no file written)?"
options:
  - label: "No — write the script (Recommended)"
    description: "Create sync-db-passwords.sh on disk"
  - label: "Yes — preview only"
    description: "Print the would-be script and the discovered user table"
default: "No"
```

### Phase 2: Discovery

1. Use **Read** on the stack file. If both `docker-stack.yml` and `docker-compose.yml` exist, use the stack file — it has post-migration variable shapes. Note in the summary which one was used.

2. Use **Grep** to extract service environment lines mentioning `POSTGRES_DB` or `MONGO_DB`:
   ```bash
   grep -E '(POSTGRES|MONGO)_DB_(USER|NAME|PASSWORD)' <stack-file>
   ```

3. Build the **Postgres user table**. For every distinct `<FAMILY>_POSTGRES_DB_USER` reference, derive:
   - `user_var` = `<FAMILY>_POSTGRES_DB_USER`
   - `db_var`   = `<FAMILY>_POSTGRES_DB_NAME` (must also appear in the stack)
   - `pw_var`   = `<FAMILY>_POSTGRES_DB_PASSWORD` (looked up in `.env`, **not** required in the stack — swarm-shape stacks reference passwords via Docker secrets like `DOCKER_SECRET:<FAMILY>_DB_PASSWORD`)

4. Build the **MongoDB user table** the same way for `<FAMILY>_MONGO_DB_*` triples.

5. **Standard eRegistrations families** (anchor list — confirm each is actually referenced before including it):

   | Family | Postgres? | Mongo? | Notes |
   |---|---|---|---|
   | `KEYCLOAK` | Yes | — | |
   | `CAMUNDA`  | Yes | — | |
   | `BPA`      | Yes | — | |
   | `DS`       | Yes | — | |
   | `CASHIER`  | Yes | — | |
   | `GDB`      | Yes | — | |
   | `STATISTICS` | Yes | — | env var name is the long form |
   | `GRAYLOG`  | — | Yes | DB = `$GRAYLOG_MONGO_DB_NAME` |
   | `FORMIO`   | — | Yes | DB = `$FORMIO_MONGO_DB_NAME` |
   | `RESTHEART`| — | Yes | URI has no path → user lives in `admin` DB |

   The skill must not hard-code this list as the source of truth. Discover from the stack first; cross-check against the table second to catch typos and missing services.

6. Use **Read** on `.env`. For every discovered `pw_var`, confirm a non-empty value exists. Track any missing in a list.

**Checkpoint:** Confirm with the user — *"Found N Postgres users (across M databases) and K MongoDB users. .env supplies all N+K passwords. Proceed?"* If any password is missing, list them and ask whether to proceed (skip those users) or abort.

### Phase 3: Connection-credential strategy

The generated script needs:
- Postgres superuser credentials to run `ALTER USER` on each application role
- MongoDB admin credentials to run `db.changeUserPassword` on each application user

eRegistrations does **not** standardize where these live — they belong to the DB host bootstrap, not the stack `.env`. The generated script therefore does **not** read them from `.env` by default; it accepts them via env vars (`PG_SUPER_USER`, `PG_SUPER_PASSWORD`, `MONGO_ADMIN_USER`, `MONGO_ADMIN_PASSWORD`) or interactive prompts.

Ask the user:

```
question: "Where should the generated script source the Postgres + Mongo super-credentials?"
options:
  - label: "Env vars or prompt at run time (Recommended)"
    description: "Operator exports PG_SUPER_PASSWORD / MONGO_ADMIN_PASSWORD before running, or types them when prompted"
  - label: "Read from .env if present"
    description: "Source POSTGRES_PASSWORD and MONGO_INITDB_ROOT_PASSWORD from .env, fall back to prompt"
  - label: "Hard-code into the script"
    description: "NOT recommended — only for ephemeral lab use"
default: "Env vars or prompt at run time"
```

If the user picks "Hard-code", abort and explain: *"Refusing to write a script with embedded super-credentials. Use the recommended option and pass them at runtime."* This is the one case where the skill overrides user choice — the security cost is too high.

### Phase 4: Generation

Use **Write** to emit `sync-db-passwords.sh` from the template in the *Generated script* section below.

Substitution points:
- `__GENERATED_AT__` → ISO-8601 timestamp
- `__STACK_FILE__` → relative path to the discovered stack file
- `__ENV_FILE__` → relative path to the discovered `.env`
- `__PG_USER_ROWS__` → one line per Postgres user, format `"<USER_VAR>:<DB_VAR>:<PW_VAR>"` (variable names, not values — the script resolves them after sourcing `.env`)
- `__MONGO_USER_ROWS__` → same shape for MongoDB
- `__SERVICE_HOST_FALLBACK__` → literal `127.0.0.1` (the script honours `$SERVICE_HOST` from `.env` first)

If dry-run was selected in Phase 1, print the rendered script + the user table to chat instead of writing.

### Phase 5: Validation

1. **Shellcheck-clean** — Use **Bash** (`Bash(test *)` and `Bash(ls *)` in allowed-tools cover the smoke checks; deeper validation is the operator's responsibility):
   ```bash
   test -f sync-db-passwords.sh && test -x sync-db-passwords.sh
   ```
   The Write call should `chmod +x` via the script's first line `#!/usr/bin/env bash` — the operator runs `chmod +x` themselves; the skill notes this in the summary.

2. **Round-trip table** — re-grep the rendered script for `PG_USERS=` and `MONGO_USERS=` and confirm every discovered user appears.

3. **No literal passwords** — Use **Grep**:
   ```bash
   grep -E "PASSWORD\s*=\s*['\"][^$]" sync-db-passwords.sh
   ```
   Must return empty. Passwords are only ever referenced by **variable name** in the script body — never embedded literally.

4. **Final summary** to user:
   ```
   === DB password sync script ready ===

   Stack:    <relative path>
   .env:     <relative path>
   Output:   <relative path>

   Postgres users (N):
     <user>  →  <db>      (from $<PW_VAR>)
     ...
   MongoDB users (K):
     <user>  →  <db>      (from $<PW_VAR>)
     ...

   Next steps:
     1. Review sync-db-passwords.sh
     2. chmod +x sync-db-passwords.sh
     3. Dry-run:   ./sync-db-passwords.sh -n
     4. Apply:     ./sync-db-passwords.sh
   ```

## Generated script

The script below is the canonical template. Substitute the marker tokens (`__…__`) at write time.

```bash
#!/usr/bin/env bash
# Sync Postgres + MongoDB user passwords with .env values.
# Generated by /correct-db-passwords on __GENERATED_AT__
# Source stack: __STACK_FILE__
# Source env:   __ENV_FILE__
#
# Usage:
#   ./sync-db-passwords.sh [OPTIONS] [ENV_FILE]
#
# Options:
#   -n, --dry-run       Print the SQL/JS that would run; do not connect
#   -g, --generate      Write postgres.sql + mongo.js for manual application
#   -o, --output-dir D  Directory for --generate output (default: .)
#   -p, --pg-only       Only sync Postgres users
#   -m, --mongo-only    Only sync MongoDB users
#   -h, --help          Show this help
#
# Required at run-time (env or prompt):
#   PG_SUPER_USER         (default: postgres)
#   PG_SUPER_PASSWORD
#   MONGO_ADMIN_USER      (default: admin)
#   MONGO_ADMIN_PASSWORD
#
# Honoured from .env:
#   SERVICE_HOST          (default: __SERVICE_HOST_FALLBACK__)

set -eu
set -o pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

MODE="apply"
OUT_DIR="."
ENV_FILE=".env"
SCOPE="all"

show_help() {
    sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--dry-run)    MODE="dry-run"; shift ;;
        -g|--generate)   MODE="generate"; shift ;;
        -o|--output-dir) OUT_DIR="${2:?--output-dir requires an argument}"; shift 2 ;;
        -p|--pg-only)    SCOPE="pg"; shift ;;
        -m|--mongo-only) SCOPE="mongo"; shift ;;
        -h|--help)       show_help; exit 0 ;;
        -*) echo -e "${RED}Unknown option: $1${NC}" >&2; exit 1 ;;
        *)  ENV_FILE="$1"; shift ;;
    esac
done

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: env file not found: $ENV_FILE${NC}" >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

SERVICE_HOST="${SERVICE_HOST:-__SERVICE_HOST_FALLBACK__}"

# (USER_VAR:DB_VAR:PW_VAR) — names, not values; resolved indirectly below.
PG_USERS=(
__PG_USER_ROWS__
)

MONGO_USERS=(
__MONGO_USER_ROWS__
)

prompt_if_unset() {
    local name="$1" silent="${2:-0}" value
    if [ -z "${!name:-}" ]; then
        if [ "$silent" = "1" ]; then
            read -rsp "$name: " value; echo
        else
            read -rp  "$name: " value
        fi
        printf -v "$name" '%s' "$value"
    fi
}

# Indirect-expand a NAME → its value (Bash 4+).
val_of() { printf '%s' "${!1:-}"; }

# Single-quote escape for Postgres SQL string literal.
sql_escape() { local s="$1"; printf '%s' "${s//\'/\'\'}"; }

# JS string-literal escape for mongosh --eval. Order matters: backslash first.
js_escape()  { local s="$1"; s="${s//\\/\\\\}"; s="${s//\'/\\\'}"; printf '%s' "$s"; }

missing_inputs=()
require_var_in_env() {
    local var="$1" subject="$2"
    if [ -z "${!var:-}" ]; then
        missing_inputs+=("$subject ($var)")
    fi
}

emit_pg_sql() {
    local user_var db_var pw_var user db pw
    for row in "${PG_USERS[@]}"; do
        IFS=':' read -r user_var db_var pw_var <<< "$row"
        user=$(val_of "$user_var"); db=$(val_of "$db_var"); pw=$(val_of "$pw_var")
        require_var_in_env "$user_var" "Postgres user"
        require_var_in_env "$db_var"   "Postgres database"
        require_var_in_env "$pw_var"   "Postgres password"
        printf -- "-- %s @ %s\n" "$user" "$db"
        printf -- "ALTER USER \"%s\" WITH PASSWORD '%s';\n" "$user" "$(sql_escape "$pw")"
    done
}

emit_mongo_js() {
    local user_var db_var pw_var user db pw
    for row in "${MONGO_USERS[@]}"; do
        IFS=':' read -r user_var db_var pw_var <<< "$row"
        user=$(val_of "$user_var"); db=$(val_of "$db_var"); pw=$(val_of "$pw_var")
        require_var_in_env "$user_var" "Mongo user"
        require_var_in_env "$pw_var"   "Mongo password"
        # Empty $db → admin DB (RestHeart-style URIs without path).
        [ -z "$db" ] && db="admin"
        printf "// %s @ %s\n" "$user" "$db"
        printf "db.getSiblingDB('%s').changeUserPassword('%s', '%s');\n" \
            "$(js_escape "$db")" "$(js_escape "$user")" "$(js_escape "$pw")"
    done
}

apply_pg() {
    local sql; sql=$(emit_pg_sql)
    if [ "${#missing_inputs[@]}" -gt 0 ]; then return 1; fi
    PGPASSWORD="$PG_SUPER_PASSWORD" psql \
        -h "$SERVICE_HOST" -p 5432 -U "$PG_SUPER_USER" -d postgres \
        -v ON_ERROR_STOP=1 \
        <<< "$sql"
}

apply_mongo() {
    local js; js=$(emit_mongo_js)
    if [ "${#missing_inputs[@]}" -gt 0 ]; then return 1; fi
    mongosh --quiet \
        "mongodb://${MONGO_ADMIN_USER}:${MONGO_ADMIN_PASSWORD}@${SERVICE_HOST}:27017/admin?authSource=admin" \
        --eval "$js"
}

case "$MODE" in
    apply)
        PG_SUPER_USER="${PG_SUPER_USER:-postgres}"
        MONGO_ADMIN_USER="${MONGO_ADMIN_USER:-admin}"
        if [ "$SCOPE" != "mongo" ]; then prompt_if_unset PG_SUPER_PASSWORD 1;    fi
        if [ "$SCOPE" != "pg"    ]; then prompt_if_unset MONGO_ADMIN_PASSWORD 1; fi
        ;;
esac

if [ "$SCOPE" != "mongo" ]; then
    case "$MODE" in
        dry-run)  echo -e "${CYAN}-- Postgres (dry-run) --${NC}"; emit_pg_sql ;;
        generate) emit_pg_sql > "$OUT_DIR/postgres.sql"; echo -e "${GREEN}Wrote $OUT_DIR/postgres.sql${NC}" ;;
        apply)    echo -e "${CYAN}Applying Postgres updates…${NC}"; apply_pg && echo -e "${GREEN}[OK] Postgres synced${NC}" ;;
    esac
fi

if [ "$SCOPE" != "pg" ]; then
    case "$MODE" in
        dry-run)  echo -e "${CYAN}-- MongoDB (dry-run) --${NC}"; emit_mongo_js ;;
        generate) emit_mongo_js > "$OUT_DIR/mongo.js"; echo -e "${GREEN}Wrote $OUT_DIR/mongo.js${NC}" ;;
        apply)    echo -e "${CYAN}Applying MongoDB updates…${NC}"; apply_mongo && echo -e "${GREEN}[OK] MongoDB synced${NC}" ;;
    esac
fi

if [ "${#missing_inputs[@]}" -gt 0 ]; then
    echo -e "${RED}Aborted — missing in $ENV_FILE:${NC}" >&2
    printf '  - %s\n' "${missing_inputs[@]}" >&2
    exit 1
fi
```

## Escaping rules

The two `*_escape` functions in the generated script handle all common cases. The skill must not bypass them when emitting test fixtures or examples.

| Context | Hazard | Escape |
|---|---|---|
| `psql` SQL string literal | `'` inside password | Double the quote: `'` → `''` |
| `mongosh --eval` JS string | `\` inside password | Escape backslash first: `\` → `\\` |
| `mongosh --eval` JS string | `'` inside password | After backslash escape: `'` → `\'` |
| Anywhere | `$` inside password | None needed — values are referenced via `${var}` after `set -a; source .env`, not interpolated into double-quoted format strings |

The order in `js_escape` matters: backslash must be escaped **before** single quote, otherwise `\'` would be re-escaped to `\\'`.

## Examples

### Example 1 — Discovered user table

For a Mali-test stack referencing `KEYCLOAK_*`, `CAMUNDA_*`, `BPA_*`, `DS_*`, `CASHIER_*`, `GDB_*`, `STATISTICS_*` on Postgres and `GRAYLOG_*`, `FORMIO_*`, `RESTHEART_*` on Mongo, the rendered arrays are:

```bash
PG_USERS=(
    "KEYCLOAK_POSTGRES_DB_USER:KEYCLOAK_POSTGRES_DB_NAME:KEYCLOAK_POSTGRES_DB_PASSWORD"
    "CAMUNDA_POSTGRES_DB_USER:CAMUNDA_POSTGRES_DB_NAME:CAMUNDA_POSTGRES_DB_PASSWORD"
    "BPA_POSTGRES_DB_USER:BPA_POSTGRES_DB_NAME:BPA_POSTGRES_DB_PASSWORD"
    "DS_POSTGRES_DB_USER:DS_POSTGRES_DB_NAME:DS_POSTGRES_DB_PASSWORD"
    "CASHIER_POSTGRES_DB_USER:CASHIER_POSTGRES_DB_NAME:CASHIER_POSTGRES_DB_PASSWORD"
    "GDB_POSTGRES_DB_USER:GDB_POSTGRES_DB_NAME:GDB_POSTGRES_DB_PASSWORD"
    "STATISTICS_POSTGRES_DB_USER:STATISTICS_POSTGRES_DB_NAME:STATISTICS_POSTGRES_DB_PASSWORD"
)

MONGO_USERS=(
    "GRAYLOG_MONGO_DB_USER:GRAYLOG_MONGO_DB_NAME:GRAYLOG_MONGO_DB_PASSWORD"
    "FORMIO_MONGO_DB_USER:FORMIO_MONGO_DB_NAME:FORMIO_MONGO_DB_PASSWORD"
    "RESTHEART_MONGO_DB_USER::RESTHEART_MONGO_DB_PASSWORD"
)
```

Note `RESTHEART_*` has an empty `DB_VAR` slot — its URI in the stack has no DB path, so the runtime falls back to `admin`.

### Example 2 — Final report

```
=== DB password sync script ready ===

Stack:    Conf-TEST/compose/mali/docker-stack.yml
.env:     Conf-TEST/compose/mali/.env
Output:   Conf-TEST/compose/mali/sync-db-passwords.sh

Postgres users (7):
  ${KEYCLOAK_POSTGRES_DB_USER}    @ ${KEYCLOAK_POSTGRES_DB_NAME}    (from $KEYCLOAK_POSTGRES_DB_PASSWORD)
  ${CAMUNDA_POSTGRES_DB_USER}     @ ${CAMUNDA_POSTGRES_DB_NAME}     (from $CAMUNDA_POSTGRES_DB_PASSWORD)
  ${BPA_POSTGRES_DB_USER}         @ ${BPA_POSTGRES_DB_NAME}         (from $BPA_POSTGRES_DB_PASSWORD)
  ${DS_POSTGRES_DB_USER}          @ ${DS_POSTGRES_DB_NAME}          (from $DS_POSTGRES_DB_PASSWORD)
  ${CASHIER_POSTGRES_DB_USER}     @ ${CASHIER_POSTGRES_DB_NAME}     (from $CASHIER_POSTGRES_DB_PASSWORD)
  ${GDB_POSTGRES_DB_USER}         @ ${GDB_POSTGRES_DB_NAME}         (from $GDB_POSTGRES_DB_PASSWORD)
  ${STATISTICS_POSTGRES_DB_USER}  @ ${STATISTICS_POSTGRES_DB_NAME}  (from $STATISTICS_POSTGRES_DB_PASSWORD)

MongoDB users (3):
  ${GRAYLOG_MONGO_DB_USER}    @ ${GRAYLOG_MONGO_DB_NAME}
  ${FORMIO_MONGO_DB_USER}     @ ${FORMIO_MONGO_DB_NAME}
  ${RESTHEART_MONGO_DB_USER}  @ admin

Next steps:
  1. Review sync-db-passwords.sh
  2. chmod +x sync-db-passwords.sh
  3. Dry-run:   ./sync-db-passwords.sh -n
  4. Apply:     ./sync-db-passwords.sh
```

## CRITICAL RULES

- NEVER embed plaintext passwords in `sync-db-passwords.sh`. Reference variable names; let `set -a; source .env` resolve them at run time.
- NEVER add `CREATE USER`, `CREATE DATABASE`, or `GRANT` statements — out of scope.
- NEVER hard-code superuser/admin credentials, even on user request. Decline that option and explain why.
- If a user is referenced in the stack but its password is missing from `.env`, list every missing var and abort. Do not skip silently.
- If both `docker-stack.yml` and `docker-compose.yml` exist, prefer the stack file. Note the choice in the summary.
- ALWAYS chmod is the operator's job — do not call `chmod` from inside this skill.

## Companion to docker-swarm-migration

| Concern | Where it lives |
|---|---|
| Build the swarm-shape stack file | `/docker-swarm-migration` |
| Push `.env` values into Docker secrets so apps can read them | `init-swarm.sh` (output of `/docker-swarm-migration`) |
| Push `.env` values into the Postgres / Mongo servers themselves | `sync-db-passwords.sh` (output of this skill) |

Run order on a fresh swarm migration:
1. `/docker-swarm-migration` → produces `docker-stack.yml` + `init-swarm.sh`
2. `/correct-db-passwords` → produces `sync-db-passwords.sh`
3. `./init-swarm.sh .env` → seeds Docker secrets
4. `./sync-db-passwords.sh` → aligns DB-side passwords
5. `docker stack deploy -c docker-stack.yml eregistrations`

## Dependencies

- Tools (skill): Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, TodoWrite
- Tools (generated script, on the operator's host): bash 4+, `psql` (postgresql-client), `mongosh`
- Prerequisites: a swarm-shape stack file with `*_POSTGRES_DB_*` / `*_MONGO_DB_*` triples and a sibling `.env`
