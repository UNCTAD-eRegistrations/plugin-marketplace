#!/bin/bash
# Boot postgres + cas-db + partc-db + keycloak, import realm via Keycloak's
# baked entrypoint, load CAS/PARTC source dumps, extract JSON inputs, run the
# cas-to-keycloak migrator against the running Keycloak, then pg_dump the
# enriched Keycloak DB to sql/keycloak.sql (overwrites prior realm-only dump).
# Everything is torn down on exit.
#
# Idempotent: safe to re-run; output is overwritten.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUT="$REPO_ROOT/sql/keycloak.sql"
CAS_XZ="$REPO_ROOT/sql/cas.sql"
PARTC_XZ="$REPO_ROOT/sql/partc.sql"

# Country / instance parameters — also picked up by docker-compose.yml.
# COUNTRY            sub-dir holding the country-specific SQL extracts (e.g.
#                    "cuba" -> $SCRIPT_DIR/cuba-sql/). Compose project name
#                    derives from this too.
# KC_REALM_NAME      Keycloak realm to expect after import (e.g. CU, SV).
# REALM_JSON_PATH    relative path from $SCRIPT_DIR to the realm JSON to
#                    import (resolved into the keycloak container).
# INSTITUTION_GROUP_ID  UUID of the realm's institutions group.
# MIGRATOR_SRC_PATH  relative path from $SCRIPT_DIR to the vendored cas-to-
#                    keycloak source (defaults to ./migrator-src).
: "${COUNTRY:=cuba}"
: "${KC_REALM_NAME:=CU}"
: "${REALM_JSON_PATH:?REALM_JSON_PATH must be set (relative to $SCRIPT_DIR)}"
: "${INSTITUTION_GROUP_ID:?INSTITUTION_GROUP_ID must be set}"
: "${MIGRATOR_SRC_PATH:=./migrator-src}"

export COUNTRY KC_REALM_NAME REALM_JSON_PATH INSTITUTION_GROUP_ID MIGRATOR_SRC_PATH

EXTRACT_DIR="$SCRIPT_DIR/${COUNTRY}-sql"
if [[ ! -d "$EXTRACT_DIR" ]]; then
    echo "Country extract dir '$EXTRACT_DIR' not found." >&2
    echo "Create it by copying cuba-sql/ as a starting point, then adapt the SQL." >&2
    exit 2
fi

cd "$SCRIPT_DIR"

# Ensure the writable migrator workdir exists (bind-mounted at /app).
mkdir -p "$SCRIPT_DIR/migrator-workdir"

cleanup() {
    echo "== Tearing down stack =="
    docker compose down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "== Pulling images =="
docker compose pull

echo "== Starting postgres + cas-db + partc-db =="
docker compose up -d postgres cas-db partc-db

for svc in postgres cas-db partc-db; do
    cid=$(docker compose ps -q "$svc")
    for i in {1..30}; do
        health=$(docker inspect --format='{{.State.Health.Status}}' "$cid" 2>/dev/null || echo "starting")
        [[ "$health" == "healthy" ]] && break
        sleep 2
    done
    if [[ "$health" != "healthy" ]]; then
        echo "  ! $svc failed to become healthy" >&2
        docker compose logs "$svc" --tail=40 >&2
        exit 1
    fi
done
echo "  → all three DBs healthy"

echo "== Loading CAS dump into cas-db =="
# Dump references role `cas` for schema ownership — pre-create so restore is clean.
docker compose exec -T cas-db psql -U postgres -d postgres -c "CREATE ROLE cas;" >/dev/null 2>&1 || true
xzcat "$CAS_XZ" | docker compose exec -T cas-db psql -U postgres -d postgres -q -v ON_ERROR_STOP=1 >/dev/null
cas_user_count=$(docker compose exec -T cas-db psql -U postgres -d postgres -tAc 'SELECT count(*) FROM cas."user";')
echo "  → cas.user rows: $cas_user_count"

echo "== Loading PARTC dump into partc-db =="
# Dump references role `partc` for schema ownership — pre-create so restore is clean.
docker compose exec -T partc-db psql -U postgres -d postgres -c "CREATE ROLE partc;" >/dev/null 2>&1 || true
xzcat "$PARTC_XZ" | docker compose exec -T partc-db psql -U postgres -d postgres -q -v ON_ERROR_STOP=1 >/dev/null
partc_user_count=$(docker compose exec -T partc-db psql -U postgres -d postgres -tAc 'SELECT count(*) FROM partc."user";')
echo "  → partc.user rows: $partc_user_count"

echo "== Starting keycloak =="
docker compose up -d keycloak

KC_CID=$(docker compose ps -q keycloak)
echo "== Waiting for keycloak health (realm import runs during startup, ~90-180s) =="
deadline=$(($(date +%s) + 900))
while :; do
    health=$(docker inspect --format='{{.State.Health.Status}}' "$KC_CID" 2>/dev/null || echo "starting")
    case "$health" in
        healthy)
            echo " → healthy"
            break
            ;;
        unhealthy)
            echo " → unhealthy; dumping logs:" >&2
            docker compose logs keycloak --tail=80 >&2
            exit 1
            ;;
    esac
    (( $(date +%s) > deadline )) && { echo " → timed out" >&2; docker compose logs keycloak --tail=80 >&2; exit 1; }
    printf '.'
    sleep 5
done

echo "== Verifying realm $KC_REALM_NAME is present in the Keycloak DB =="
if ! docker compose exec -T postgres psql -U keycloak -d keycloak -tAc \
        "SELECT name FROM realm WHERE name='$KC_REALM_NAME';" | grep -qx "$KC_REALM_NAME"; then
    echo "Realm $KC_REALM_NAME not found — import likely failed." >&2
    docker compose logs keycloak --tail=120 >&2
    exit 1
fi

echo "== Extending admin-cli access token lifespan to 1h (for long migrations) =="
# Get a master-realm admin token, look up the admin-cli client id, PUT the
# extended lifespan. All done from inside the keycloak container so the
# endpoint is reachable on localhost without publishing ports.
docker compose exec -T keycloak sh -c '
set -euo pipefail
TOKEN=$(curl -sS -X POST \
    -d "client_id=admin-cli" -d "username=admin" -d "password=admin" -d "grant_type=password" \
    http://localhost:8080/realms/master/protocol/openid-connect/token \
    | sed -E "s/.*\"access_token\":\"([^\"]+)\".*/\1/")
ADMIN_CLI_ID=$(curl -sS -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8080/admin/realms/master/clients?clientId=admin-cli" \
    | sed -E "s/.*\"id\":\"([^\"]+)\".*/\1/" | head -1)
curl -sS -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"attributes\":{\"access.token.lifespan\":\"3600\"}}" \
    "http://localhost:8080/admin/realms/master/clients/$ADMIN_CLI_ID"
echo "  → admin-cli lifespan set to 3600s"
'

echo "== Extracting migration inputs =="
"$EXTRACT_DIR/extract.sh"

echo "== Running cas-to-keycloak migrator =="
# Stage the tool into the writable workdir, plus a small wrapper that flips
# the keycloak-admin client between master (for auth) and the target realm
# (for ops), then run it. node_modules persists in the workdir across reruns
# for speed.
cp "$EXTRACT_DIR/migrate-wrapper.js" "$SCRIPT_DIR/migrator-workdir/migrate-wrapper.js"
docker compose run --rm migrator sh -c '
set -euo pipefail
cp /src/package.json /app/
cp /src/package-lock.json /app/ 2>/dev/null || true
cp /src/migrate.js /app/
cd /app
if [ ! -d node_modules ]; then
    npm install --no-audit --no-fund --loglevel=error
fi
node migrate-wrapper.js
'

echo "== Dumping enriched keycloak database → $OUT =="
docker compose exec -T postgres \
    pg_dump -U keycloak -d keycloak \
        --no-owner --no-privileges \
        --clean --if-exists \
    > "$OUT"

echo "== Dump complete =="
ls -lh "$OUT"
wc -l "$OUT"
