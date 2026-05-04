---
name: correct-db-passwords
description: >
  Generate a script that resets PostgreSQL and MongoDB user passwords on the DB
  hosts backing an eRegistrations stack to match the values in the host's
  `.env` file. Handles BOTH the legacy compose shape (variable-driven —
  `=$BPA_POSTGRES_DB_USER`, `=$BPA_POSTGRES_DB_PASSWORD`) and the swarm
  post-cleanup shape (hardcoded literal usernames + Docker-secret-named
  passwords — `=bpa`, `=DOCKER_SECRET:BPA_POSTGRES_DB_PASSWORD`), and any
  mixture of the two within a single stack. Discovery is service-block-scoped:
  for every service that talks to Postgres or MongoDB it extracts the
  user / database / password-source triple from environment lines and JDBC
  URLs, then emits `sync-db-passwords.sh` — a self-contained bash script that
  runs `ALTER USER` on Postgres and `db.changeUserPassword` on MongoDB.
  Idempotent. Password-only — never creates users or databases.
license: UNCTAD-Internal
compatibility: >
  Requires a docker-stack.yml or docker-compose.yml. The matching `.env` is
  optional at generation time — validation moves to script runtime, where
  `.env` is sourced on the deployment host. For swarm-post-cleanup stacks
  whose Mongo credentials are hidden inside `*_MONGODB_URI` secrets, a sibling
  `init-swarm.sh` is the canonical source for the user/db/password var
  mapping; the skill prompts when it cannot be located. The generated script
  assumes Postgres on the same host as the script (peer auth via
  `sudo -u postgres psql`) and MongoDB reachable at `$SERVICE_HOST:27017`. For
  remote/dockerized Postgres, `--pg-tcp` switches to TCP+password.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(test *), Bash(ls *), Bash(grep *), Bash(diff *), AskUserQuestion, TodoWrite
metadata:
  version: "1.2.0"
  version-date: "2026-05-04"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<path-to-docker-stack.yml-or-instance-dir>"
  jira: "TOBE-17731"
---

You are an expert eRegistrations DevOps engineer. Your task is to read an instance's `docker-stack.yml` (or `docker-compose.yml`), identify every PostgreSQL and MongoDB application user the stack expects, and emit a single bash script that the operator runs on the DB host to align server-side passwords with the values in `.env`.

## Why this skill exists

`/docker-swarm-migration` produces `init-swarm.sh`, which puts the desired passwords into Docker secrets so the application containers can read them. That handles the **application side** only. The **server side** — the `postgres` and `mongod` processes the apps connect to — has its own users with their own (possibly older) passwords. When secrets are rotated, when an instance is moved from compose to swarm, or when an operator hand-edits `.env`, the two sides drift. This skill closes the gap from the same `.env` that feeds `init-swarm.sh`, so both sides stay in sync without two sources of truth.

## Core capabilities

1. Parse a service-block view of `docker-stack.yml` or `docker-compose.yml` — every service that talks to Postgres or MongoDB
2. Extract `(user, database, password-source)` triples from each service's environment lines and JDBC URLs, recognizing **three** kinds of source per slot:
   - **literal** — value baked into the YAML (`=bpa`)
   - **envvar** — reference to a `.env` variable (`=$BPA_POSTGRES_DB_USER`)
   - **secret** — Docker-secret-named password (`=DOCKER_SECRET:BPA_POSTGRES_DB_PASSWORD`)
3. For Mongo URIs hidden inside `DOCKER_SECRET:*_MONGODB_URI` references, recover the user/db/password var names from the sibling `init-swarm.sh`'s URI-assembly lines
4. Emit `sync-db-passwords.sh` with three modes (apply / dry-run / generate-sql-files) that resolves every source to a runtime value via `set -a; source .env; set +a` on the deployment host
5. Idempotent by construction — `ALTER USER` and `db.changeUserPassword` are safe to re-run
6. Password-only — refuse to `CREATE USER`, `CREATE DATABASE`, or `GRANT`

## Reasoning principles

1. **Stack is authoritative for "which users and databases"; `.env` is authoritative for "what password"**. The skill never invents either side. Discovery extracts user/db from the YAML; password values are looked up at the script's runtime, not the skill's generation time.
2. **Password-only**. Never `CREATE USER`, never `CREATE DATABASE`, never grant privileges. Those are bootstrap concerns owned by other tooling. This skill's promise is "the user already exists; align its password."
3. **Two shapes, one output**. The same `sync-db-passwords.sh` template handles compose, swarm-post-cleanup, and any mixture — the only thing that varies is the encoded `(user, db, pw_var)` rows.
4. **`.env` lives on the deployment host, not the repo**. Generation must succeed without a local `.env`. Pre-flight `.env` validation, when possible, is a courtesy — the runtime check in the generated script is the source of truth.
5. **Idempotent over clever**. Running the generated script twice is exactly the same as running it once.
6. **Plaintext flows through `.env`**. Same trust boundary as `init-swarm.sh`. Don't add new password-handling primitives; reuse the pattern operators already understand.
7. **Quote everything**. Passwords commonly contain `'`, `"`, `\`, `$`. The generated script must escape correctly for both psql and mongosh contexts (see *Escaping rules* below).

## Out of scope

- Creating users or databases (use bootstrap SQL / Mongo init scripts)
- Granting privileges, ALTER ROLE attributes, role membership
- Rotating Docker secrets (that's `/docker-swarm-migration`'s init-swarm.sh and `--generate` mode)
- Reading passwords from Docker secrets at runtime — the script reads `.env`, same as `init-swarm.sh`
- MongoDB replica sets / sharded clusters — single-node `mongod` only (eRegistrations production shape)
- Postgres roles other than the per-service application roles (not `postgres`, not replication roles)
- Anything cross-host — the generated script targets one Postgres + one MongoDB at `$SERVICE_HOST`

## Stack shapes

The skill recognizes three patterns. Real stacks may mix them service-by-service.

### Shape A — compose / variable-driven

Everything goes through `.env`. Typical of pre-2.18 instances on `docker-compose.yml`.

```yaml
bpa-backend:
  environment:
    - "SPRING_DATASOURCE_URL=jdbc:postgresql://postgres_host:5432/$BPA_POSTGRES_DB_NAME"
    - "SPRING_DATASOURCE_USERNAME=$BPA_POSTGRES_DB_USER"
    - "SPRING_DATASOURCE_PASSWORD=$BPA_POSTGRES_DB_PASSWORD"
```

Discovery: user, db, pw all resolve via `.env` at runtime.

### Shape B — swarm post-cleanup

Username and database name baked into the YAML; password comes from a Docker secret. Typical of post-migration instances (e.g. Palestine DEV).

```yaml
bpa-backend:
  environment:
    - "SPRING_DATASOURCE_URL=jdbc:postgresql://postgres_host:5432/bpa"
    - "SPRING_DATASOURCE_USERNAME=bpa"
    - "SPRING_DATASOURCE_PASSWORD=DOCKER_SECRET:BPA_POSTGRES_DB_PASSWORD"
```

Discovery: user and db are literals; pw is the secret name, which the skill maps to a `.env` variable name (via `init-swarm.sh` if present, otherwise 1:1 by default).

### Shape C — mixed

A service can mix kinds. E.g. user is a literal, db is an envvar, pw is a secret. The encoding handles each slot independently.

### MongoDB sub-shapes

For Mongo, the stack file may show:
- A composite URI assembled in YAML (Shape A): `mongodb://$U:$P@host:port/$D` — decompose into user/db/pw vars
- A URI received from a secret (Shape B): `=DOCKER_SECRET:GRAYLOG_MONGODB_URI` — opaque from YAML alone; recover the var names from the matching line in `init-swarm.sh` (`GRAYLOG_MONGODB_URI="mongodb://${U}:${P}@host:port/${D}"`)

If neither the composite URI nor `init-swarm.sh` resolves the Mongo triple, prompt the user. Never guess.

## Workflow

### Phase 1: Input gathering

Use **AskUserQuestion** for missing values. If `$ARGUMENTS[0]` is provided, treat it as the stack path or its parent directory and skip Question 1.

**Question 1 — Source stack file:**
```
question: "Path to docker-stack.yml or docker-compose.yml (or its containing directory)?"
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

**Question 2 — `init-swarm.sh` (Shape B Mongo only):**
```
question: "Path to init-swarm.sh (only needed when Mongo URIs are passed via DOCKER_SECRET)?"
options:
  - label: "Sibling of the stack file (Recommended)"
    description: "Look for init-swarm.sh next to the stack"
  - label: "Custom path"
    description: "Specify a different init-swarm.sh path"
  - label: "Not available"
    description: "Skill will prompt for each Mongo user/db/password var name"
default: "Sibling of the stack file"
```

Skip this question entirely if no `*_MONGODB_URI` / `*_MONGO_URI` secret reference is present in the stack.

**Question 3 — `.env` file (optional pre-flight only):**
```
question: "Path to .env (skip if .env lives only on the deployment host)?"
options:
  - label: "Sibling of the stack file (Recommended if locally checked-out)"
    description: "Pre-flight every required password key in .env"
  - label: "Custom path"
    description: "Specify a different .env path"
  - label: "Not available locally"
    description: "Skip pre-flight; rely on the script's runtime check on the host"
default: "Sibling of the stack file"
```

Generation MUST succeed even when `.env` is unavailable. Skip pre-flight, mark the summary as "validation deferred to runtime".

**Question 4 — Output location:**
```
question: "Where should sync-db-passwords.sh be written?"
options:
  - label: "Same directory as the stack file (Recommended)"
    description: "Write alongside docker-stack.yml + init-swarm.sh"
  - label: "Custom path"
    description: "Specify a different output path"
default: "Same directory as the stack file"
```

**Question 5 — Dry-run:**
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

The discovery loop is **service-block-scoped**, not regex-over-the-whole-file. For each service in the YAML:

1. Identify the service name (yaml key at indent level 2, e.g. `bpa-backend:`).

2. Walk the service's `environment:` block and collect all `KEY=VALUE` entries. Recognize both list and map forms:
   ```yaml
   environment:
     - "KEY=value"            # list form
     KEY: value               # map form
   ```

3. **Postgres detection** — a service is a Postgres consumer iff its environment contains at least one of:
   - `KC_DB_USERNAME` (Keycloak)
   - `SPRING_DATASOURCE_USERNAME` (Spring services: bpa-backend, camunda, cashier)
   - `DATABASE_USERNAME` (Django services: ds-backend, gdb, statistics-backend)
   - `POSTGRES_USER` (rare — direct postgres image)

4. For each Postgres consumer, extract:
   - **user_source** — the value of the `*USERNAME` / `POSTGRES_USER` line. Classify:
     - Starts with `$` → `envvar:<varname>` (strip the `$`, also handle `${VAR}`)
     - Otherwise → `literal:<value>`
   - **pw_source** — the value of the matching `*PASSWORD` / `POSTGRES_PASSWORD` line. Classify:
     - `=$VAR` → `envvar:<varname>`
     - `=DOCKER_SECRET:NAME` → `secret:<NAME>`
     - `=literal` → unsupported for password (warn and skip — passwords don't belong in YAML)
   - **db_source** — first match wins, in this order:
     - `DATABASE_NAME` env line
     - `POSTGRES_DB` env line
     - Path component of any `*_URL=jdbc:postgresql://host:port/<db>` (or `<db>?params`)
     - Otherwise warn and prompt user

5. **Mongo detection** — a service is a Mongo consumer iff its environment or `secrets:` contains any of:
   - `MONGO_CONNECTION_STR=` env line
   - `*_MONGODB_URI=` env line
   - `*_MONGO_URI=` env line (e.g. `RH_MONGO_URI`)
   - `*_MONGODB_URI` listed in `secrets:` (with a same-named env line that just references it as a passthrough)

6. For each Mongo consumer, extract a `(user, db, pw)` triple from the URI:
   - **Composite envvar URI** (Shape A): `mongodb://$U:$P@host:port/$D` — decompose with regex; `$D` may be absent → `db = ""` (admin DB at runtime).
   - **Secret URI** (Shape B): the env line is `=DOCKER_SECRET:NAME` and the YAML alone is opaque. Read `init-swarm.sh` and locate the assignment `NAME="mongodb://${U}:${P}@host:port/${D}"`. Decompose the same way.
   - If neither path resolves, **prompt** with AskUserQuestion for user/db/pw var names. Never guess.

7. **Password-source → env-var name mapping**:
   - `envvar:<NAME>` → use `<NAME>` directly
   - `secret:<NAME>` → look in `init-swarm.sh` for `create_secret "<NAME>" "${VAR}"`. If found, use `<VAR>`. If `init-swarm.sh` is absent or has no matching line, default to `<NAME>` itself (1:1 mapping — common in post-cleanup stacks like Palestine DEV) and **note this** in the summary so the operator can sanity-check.

8. **Pre-flight `.env`** (when locally available): for every distinct password env-var name, confirm a non-empty value exists. List any missing.

**Checkpoint** — print the full discovered table to the user before writing anything:

```
=== Discovery ===
Stack: <relative path>   Shape: <A | B | mixed>
init-swarm.sh: <path | not used>
.env:           <path | "validation deferred">

Postgres users (N):
  service              user                db                  pw env-var
  bpa-backend          bpa                 bpa                 BPA_POSTGRES_DB_PASSWORD
  ds-backend           display_system      display_system      DS_POSTGRES_DB_PASSWORD
  ...

MongoDB users (K):
  service              user                db                  pw env-var
  graylog              $GRAYLOG_MONGO_DB_USER   $GRAYLOG_MONGO_DB_NAME   GRAYLOG_MONGO_DB_PASSWORD
  restheart            admin               admin               RESTHEART_MONGO_DB_PASSWORD
  ...

Proceed?
```

Render `literal` values plain and `envvar` values prefixed with `$`. If pre-flight `.env` was performed and any password is missing, list them and ask "skip these users / abort".

### Phase 3: Connection-credential strategy

The generated script needs to authenticate as a privileged user against each engine to run `ALTER USER` / `db.changeUserPassword`. eRegistrations DB hosts run Postgres and MongoDB on the same machine that operators SSH into, so the defaults are tuned for that:

**Postgres — peer auth via `sudo -u postgres psql` (default).**
The eRegistrations DB-host operator account has `sudo` rights to switch to the `postgres` OS user, which maps to the `postgres` superuser DB role via peer authentication on the local Unix socket. No password is required, no TCP listener is needed, and there is no superuser password to handle anywhere. The generated script runs:

```bash
sudo -u "$PG_OS_USER" psql -d postgres -v ON_ERROR_STOP=1 <<< "$(emit_pg_sql)"
```

`PG_OS_USER` defaults to `postgres` and is overridable via env var (rare — only matters when the OS user is renamed).

**Postgres — TCP fallback (opt-in).**
For stacks where peer auth isn't possible (dockerized postgres on the same host, postgres on a remote host, the operator account doesn't have sudo, etc.), pass `--pg-tcp` (or set `PG_VIA=tcp` in the environment). The script then connects via TCP+password using `PG_TCP_USER` / `PG_TCP_PASSWORD` (prompted if unset) at `$SERVICE_HOST:5432`.

**MongoDB — TCP+admin password (always).**
MongoDB has no OS-level peer auth equivalent. The generated script connects to `mongodb://$MONGO_ADMIN_USER:$MONGO_ADMIN_PASSWORD@$SERVICE_HOST:27017/admin?authSource=admin`. `MONGO_ADMIN_USER` defaults to `admin`; `MONGO_ADMIN_PASSWORD` is prompted at run time (silent) if unset.

The skill does **not** ask the user about these at generation time — the defaults match every standard eRegistrations DB host. The operator chooses TCP at run time only when peer auth isn't an option.

**Hard-coding super-credentials remains forbidden.** The skill never writes `PG_TCP_PASSWORD` or `MONGO_ADMIN_PASSWORD` into the generated script. If asked to, refuse and explain: *"Super-credentials must be passed at runtime via env or prompt. Refusing to embed them in a checked-out file."*

### Phase 4: Generation

Use **Write** to emit `sync-db-passwords.sh` from the template in *Generated script*.

Substitution points:
- `__GENERATED_AT__` → ISO-8601 timestamp
- `__STACK_FILE__` → relative path to the stack file
- `__ENV_FILE_HINT__` → `.env` (literal) — the operator points the script elsewhere via positional arg
- `__SHAPE_NOTE__` → `A`, `B`, or `mixed`
- `__PG_USER_ROWS__` → one quoted line per Postgres user, format `'<user_spec>|<db_spec>|<pw_envvar>'`
  - `<user_spec>` and `<db_spec>` are either a literal string or a `$VAR_NAME` reference
  - `<pw_envvar>` is always a bare env var name (no `$`)
- `__MONGO_USER_ROWS__` → same shape for MongoDB; empty `<db_spec>` slot is permitted (means the admin DB)
- `__SERVICE_HOST_FALLBACK__` → literal `127.0.0.1`

If dry-run was selected, print the rendered script + the discovered user table to chat instead of writing.

### Phase 5: Validation

1. **Smoke test** the rendered file:
   ```bash
   test -f sync-db-passwords.sh
   ```

2. **Round-trip table** — re-grep the rendered script for `PG_USERS=` and `MONGO_USERS=` and confirm every discovered service appears.

3. **No literal passwords** — Use **Grep**:
   ```bash
   grep -E "PASSWORD\s*=\s*['\"][^$]" sync-db-passwords.sh
   ```
   Must return empty. Passwords are only ever referenced by **variable name** in the script body — never embedded literally.

4. **Final summary** echoes the discovery table from Phase 2 plus the next-step instructions:
   ```
   === DB password sync script ready ===

   Stack:    <relative path>           Shape: <A|B|mixed>
   Output:   <relative path>
   Pre-flight .env: <ok | skipped (validation deferred to runtime)>

   <Postgres + MongoDB tables, same shape as Phase 2 checkpoint>

   Next steps on the deployment host:
     1. scp sync-db-passwords.sh to /opt/eregistrations/<env>/compose/<country>/
     2. cd to that directory (where .env lives)
     3. chmod +x sync-db-passwords.sh
     4. Dry-run:   ./sync-db-passwords.sh -n
     5. Apply:     ./sync-db-passwords.sh
   ```

## Generated script

```bash
#!/usr/bin/env bash
# Sync Postgres + MongoDB user passwords with .env values.
# Generated by /correct-db-passwords on __GENERATED_AT__
# Source stack: __STACK_FILE__   (shape: __SHAPE_NOTE__)
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
# Postgres connection (default: peer auth via sudo):
#   PG_OS_USER            OS user to sudo to (default: postgres). The matching
#                         DB role is implied by peer authentication.
#
# Postgres connection (TCP override, when peer auth isn't available — pass
# --pg-tcp or set PG_VIA=tcp):
#   PG_TCP_USER           (default: postgres)
#   PG_TCP_PASSWORD       (prompted at run time if unset)
#
# MongoDB connection (always TCP):
#   MONGO_ADMIN_USER      (default: admin)
#   MONGO_ADMIN_PASSWORD  (prompted at run time if unset)
#
# Honoured from .env:
#   SERVICE_HOST          (default: __SERVICE_HOST_FALLBACK__) — used for Mongo
#                         and for Postgres only when --pg-tcp is set
#   plus every password env-var named in PG_USERS / MONGO_USERS below.

set -eu
set -o pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

MODE="apply"
OUT_DIR="."
ENV_FILE="__ENV_FILE_HINT__"
SCOPE="all"
PG_VIA="${PG_VIA:-peer}"   # peer (default) | tcp

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
        --pg-tcp)        PG_VIA="tcp"; shift ;;
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

# Each row: '<user_spec>|<db_spec>|<pw_envvar_name>'
# <user_spec> / <db_spec>: a literal value, or '$VAR' to look up VAR in .env.
# <pw_envvar_name>: bare env var name (always indirect).
# Quoted with single quotes so '$' does NOT expand at array creation time.
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

# Single-quote escape for Postgres SQL string literal.
sql_escape() { local s="$1"; printf '%s' "${s//\'/\'\'}"; }

# JS string-literal escape for mongosh --eval. Order matters: backslash first.
js_escape()  { local s="$1"; s="${s//\\/\\\\}"; s="${s//\'/\\\'}"; printf '%s' "$s"; }

missing_inputs=()
note_missing() {
    local label="$1" raw="$2"
    if [[ "$raw" == \$* ]]; then
        local name="${raw:1}"
        [ -z "${!name:-}" ] && missing_inputs+=("$label ($raw)")
    elif [ -z "$raw" ]; then
        missing_inputs+=("$label (empty literal)")
    fi
    return 0
}
note_missing_envvar() {
    local label="$1" name="$2"
    [ -z "${!name:-}" ] && missing_inputs+=("$label (\$$name)")
    return 0
}

preflight() {
    local row user_spec db_spec pw_var
    if [ "$SCOPE" != "mongo" ]; then
        for row in "${PG_USERS[@]}"; do
            IFS='|' read -r user_spec db_spec pw_var <<< "$row"
            note_missing       "Postgres user"     "$user_spec"
            note_missing       "Postgres database" "$db_spec"
            note_missing_envvar "Postgres password" "$pw_var"
        done
    fi
    if [ "$SCOPE" != "pg" ]; then
        for row in "${MONGO_USERS[@]}"; do
            IFS='|' read -r user_spec db_spec pw_var <<< "$row"
            note_missing       "Mongo user"     "$user_spec"
            note_missing_envvar "Mongo password" "$pw_var"
        done
    fi
    if [ "${#missing_inputs[@]}" -gt 0 ]; then
        echo -e "${RED}Aborted - missing in $ENV_FILE:${NC}" >&2
        printf '  - %s\n' "${missing_inputs[@]}" >&2
        exit 1
    fi
}

emit_pg_sql() {
    local row user_spec db_spec pw_var user db pw
    for row in "${PG_USERS[@]}"; do
        IFS='|' read -r user_spec db_spec pw_var <<< "$row"
        user=$(resolve_kv "$user_spec")
        db=$(resolve_kv "$db_spec")
        pw="${!pw_var:-}"
        printf -- "-- %s @ %s\n" "$user" "$db"
        printf -- "ALTER USER \"%s\" WITH PASSWORD '%s';\n" "$user" "$(sql_escape "$pw")"
    done
}

emit_mongo_js() {
    local row user_spec db_spec pw_var user db pw
    for row in "${MONGO_USERS[@]}"; do
        IFS='|' read -r user_spec db_spec pw_var <<< "$row"
        user=$(resolve_kv "$user_spec")
        db=$(resolve_kv "$db_spec")
        pw="${!pw_var:-}"
        # Empty $db → admin DB (RestHeart-style URIs without path).
        [ -z "$db" ] && db="admin"
        printf "// %s @ %s\n" "$user" "$db"
        printf "db.getSiblingDB('%s').changeUserPassword('%s', '%s');\n" \
            "$(js_escape "$db")" "$(js_escape "$user")" "$(js_escape "$pw")"
    done
}

apply_pg() {
    if [ "$PG_VIA" = "tcp" ]; then
        PGPASSWORD="$PG_TCP_PASSWORD" psql \
            -h "$SERVICE_HOST" -p 5432 -U "$PG_TCP_USER" -d postgres \
            -v ON_ERROR_STOP=1 \
            <<< "$(emit_pg_sql)"
    else
        sudo -u "$PG_OS_USER" psql \
            -d postgres \
            -v ON_ERROR_STOP=1 \
            <<< "$(emit_pg_sql)"
    fi
}

apply_mongo() {
    mongosh --quiet \
        "mongodb://${MONGO_ADMIN_USER}:${MONGO_ADMIN_PASSWORD}@${SERVICE_HOST}:27017/admin?authSource=admin" \
        --eval "$(emit_mongo_js)"
}

preflight

case "$MODE" in
    apply)
        PG_OS_USER="${PG_OS_USER:-postgres}"
        PG_TCP_USER="${PG_TCP_USER:-postgres}"
        MONGO_ADMIN_USER="${MONGO_ADMIN_USER:-admin}"
        if [ "$SCOPE" != "mongo" ] && [ "$PG_VIA" = "tcp" ]; then
            prompt_if_unset PG_TCP_PASSWORD 1
        fi
        if [ "$SCOPE" != "pg" ]; then
            prompt_if_unset MONGO_ADMIN_PASSWORD 1
        fi
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
```

The `preflight` call near the top of the script (right after `apply`-mode credential prompts) aborts BEFORE any SQL/JS is emitted when a password env-var is missing. That keeps dry-run output truthful — no misleading `WITH PASSWORD ''` lines, then a confusing trailer.

## Encoding rules

| Slot | Form | Meaning |
|---|---|---|
| user / db | `bpa` | Literal. Used as-is. |
| user / db | `$BPA_POSTGRES_DB_USER` | `.env` lookup. Single-quote the array entry so the `$` is preserved as data. |
| user / db | empty (mongo db only) | Admin DB at runtime. |
| pw | `BPA_POSTGRES_DB_PASSWORD` | Bare `.env` var name — always indirect; never literal. |

**Critical:** any literal containing a `$` is an error condition. eRegistrations DB usernames and database names are alphanumeric+underscore. If the skill ever produces `literal:$something` it has misclassified the source — abort and report.

## Escaping rules

The `*_escape` functions handle all common cases. Skill-emitted test fixtures and examples must not bypass them.

| Context | Hazard | Escape |
|---|---|---|
| `psql` SQL string literal | `'` inside password | Double the quote: `'` → `''` |
| `mongosh --eval` JS string | `\` inside password | Escape backslash first: `\` → `\\` |
| `mongosh --eval` JS string | `'` inside password | After backslash escape: `'` → `\'` |
| Anywhere | `$` inside password | None needed — values are referenced via `${var}` after `set -a; source .env`, not interpolated into double-quoted format strings |

The order in `js_escape` matters: backslash must be escaped **before** single quote.

## Examples

### Example 1 — Shape A discovery (Mali compose)

Source `docker-compose.yml` references `$BPA_POSTGRES_DB_USER`, `$BPA_POSTGRES_DB_NAME`, `$BPA_POSTGRES_DB_PASSWORD` etc. Rendered arrays:

```bash
PG_USERS=(
    '$KEYCLOAK_POSTGRES_DB_USER|$KEYCLOAK_POSTGRES_DB_NAME|KEYCLOAK_POSTGRES_DB_PASSWORD'
    '$CAMUNDA_POSTGRES_DB_USER|$CAMUNDA_POSTGRES_DB_NAME|CAMUNDA_POSTGRES_DB_PASSWORD'
    '$BPA_POSTGRES_DB_USER|$BPA_POSTGRES_DB_NAME|BPA_POSTGRES_DB_PASSWORD'
    '$DS_POSTGRES_DB_USER|$DS_POSTGRES_DB_NAME|DS_POSTGRES_DB_PASSWORD'
    '$CASHIER_POSTGRES_DB_USER|$CASHIER_POSTGRES_DB_NAME|CASHIER_POSTGRES_DB_PASSWORD'
    '$GDB_POSTGRES_DB_USER|$GDB_POSTGRES_DB_NAME|GDB_POSTGRES_DB_PASSWORD'
    '$STATISTICS_POSTGRES_DB_USER|$STATISTICS_POSTGRES_DB_NAME|STATISTICS_POSTGRES_DB_PASSWORD'
)

MONGO_USERS=(
    '$GRAYLOG_MONGO_DB_USER|$GRAYLOG_MONGO_DB_NAME|GRAYLOG_MONGO_DB_PASSWORD'
    '$FORMIO_MONGO_DB_USER|$FORMIO_MONGO_DB_NAME|FORMIO_MONGO_DB_PASSWORD'
    '$RESTHEART_MONGO_DB_USER||RESTHEART_MONGO_DB_PASSWORD'
)
```

Note `RESTHEART_*` has an empty db slot — the URI in the stack has no DB path, so the runtime falls back to `admin`.

### Example 2 — Shape B discovery (Palestine DEV swarm)

Source `docker-stack.yml` has hardcoded usernames + DB literals + `DOCKER_SECRET:*` passwords. No `init-swarm.sh` was located, so the skill defaults `secret:NAME` → env var `NAME` (1:1) and notes this in the summary. Rendered arrays:

```bash
PG_USERS=(
    'keycloak|keycloak|KEYCLOAK_POSTGRES_DB_PASSWORD'
    'camunda|camunda|CAMUNDA_POSTGRES_DB_PASSWORD'
    'bpa|bpa|BPA_POSTGRES_DB_PASSWORD'
    'display_system|display_system|DS_POSTGRES_DB_PASSWORD'
    'cashier|cashier|CASHIER_POSTGRES_DB_PASSWORD'
    'gdb|gdb|GDB_POSTGRES_DB_PASSWORD'
    'statistics|statistics|STATISTICS_POSTGRES_DB_PASSWORD'
)

# Mongo users were resolved by prompting (init-swarm.sh not available, no
# composite URIs in the stack). The operator confirmed the standard variable
# names from .env on the deployment host.
MONGO_USERS=(
    '$GRAYLOG_MONGO_DB_USER|$GRAYLOG_MONGO_DB_NAME|GRAYLOG_MONGO_DB_PASSWORD'
    '$FORMIO_MONGO_DB_USER|$FORMIO_MONGO_DB_NAME|FORMIO_MONGO_DB_PASSWORD'
    '$RESTHEART_MONGO_DB_USER||RESTHEART_MONGO_DB_PASSWORD'
)
```

### Example 3 — Shape B with `init-swarm.sh` available

Same Postgres rows as Example 2. For Mongo, the skill reads the URI-assembly lines from `init-swarm.sh`:

```
GRAYLOG_MONGODB_URI="mongodb://${GRAYLOG_MONGO_DB_USER}:${GRAYLOG_MONGO_DB_PASSWORD}@mongodb_host:27017/${GRAYLOG_MONGO_DB_NAME}"
FORMIO_MONGODB_URI="mongodb://${FORMIO_MONGO_DB_USER}:${FORMIO_MONGO_DB_PASSWORD}@docserver_mongo:27017/${FORMIO_MONGO_DB_NAME}"
RESTHEART_MONGO_URI="mongodb://${RESTHEART_MONGO_DB_USER}:${RESTHEART_MONGO_DB_PASSWORD}@mongodb_host:27017"
```

…and produces the same Mongo array as Example 1 / 2.

If `init-swarm.sh` ALSO contains explicit `create_secret "<NAME>" "${VAR}"` mappings that diverge from the secret name (e.g. `create_secret "BPA_DB_PASSWORD" "${BPA_POSTGRES_DB_PASSWORD}"`), the password env var becomes `BPA_POSTGRES_DB_PASSWORD`, not `BPA_DB_PASSWORD`. The skill must follow `create_secret` mappings whenever they're present.

### Example 4 — Final report

```
=== DB password sync script ready ===

Stack:    Conf-DEV/compose/dev/docker-stack.yml
Shape:    B (swarm post-cleanup)
Output:   Conf-DEV/compose/dev/sync-db-passwords.sh
Pre-flight .env: skipped (validation deferred to runtime)

Postgres users (7):
  service              user                db                  pw env-var
  keycloak             keycloak            keycloak            KEYCLOAK_POSTGRES_DB_PASSWORD
  camunda              camunda             camunda             CAMUNDA_POSTGRES_DB_PASSWORD
  bpa-backend          bpa                 bpa                 BPA_POSTGRES_DB_PASSWORD
  ds-backend           display_system      display_system      DS_POSTGRES_DB_PASSWORD
  cashier              cashier             cashier             CASHIER_POSTGRES_DB_PASSWORD
  gdb                  gdb                 gdb                 GDB_POSTGRES_DB_PASSWORD
  statistics-backend   statistics          statistics          STATISTICS_POSTGRES_DB_PASSWORD

MongoDB users (3):
  service              user                                db                                pw env-var
  graylog              $GRAYLOG_MONGO_DB_USER              $GRAYLOG_MONGO_DB_NAME            GRAYLOG_MONGO_DB_PASSWORD
  formio               $FORMIO_MONGO_DB_USER               $FORMIO_MONGO_DB_NAME             FORMIO_MONGO_DB_PASSWORD
  restheart            $RESTHEART_MONGO_DB_USER            (admin)                           RESTHEART_MONGO_DB_PASSWORD

Notes:
  - init-swarm.sh not found locally; secret-name → env-var fallback used (1:1)
  - Mongo triples confirmed interactively against the standard eRegistrations names

Next steps on the deployment host:
  1. scp sync-db-passwords.sh to /opt/eregistrations/Conf-DEV/compose/dev/
  2. cd to that directory (where .env lives)
  3. chmod +x sync-db-passwords.sh
  4. Dry-run:   ./sync-db-passwords.sh -n
  5. Apply:     ./sync-db-passwords.sh
```

## CRITICAL RULES

- NEVER embed plaintext passwords in `sync-db-passwords.sh`. Reference variable names; let `set -a; source .env` resolve them at run time.
- NEVER add `CREATE USER`, `CREATE DATABASE`, or `GRANT` statements — out of scope.
- NEVER hard-code superuser/admin credentials, even on user request. Decline that option and explain why.
- NEVER classify a literal containing `$` — that's almost always a misread; abort and report.
- If a stack uses `DOCKER_SECRET:*` and `init-swarm.sh` is unreachable, default the secret-name → env-var mapping to 1:1 AND surface the assumption in the summary so the operator can correct it before applying.
- If both `docker-stack.yml` and `docker-compose.yml` exist, prefer the stack file. Note the choice in the summary.
- Pre-flight `.env` validation is optional. The runtime check in `sync-db-passwords.sh` is the source of truth — do not refuse to generate just because `.env` isn't local.
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

For an existing swarm-post-cleanup stack (Shape B, no `init-swarm.sh` checked in), only steps 2 and 4 apply — and step 2 may need the operator to confirm Mongo triples interactively.

## Dependencies

- Tools (skill): Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, TodoWrite
- Tools (generated script, on the operator's host): bash 4+, `psql` (postgresql-client), `mongosh`
- Prerequisites: a stack file with at least one Postgres or Mongo consumer service. `.env` is required at script-runtime on the deployment host; optional at skill-generation time.
