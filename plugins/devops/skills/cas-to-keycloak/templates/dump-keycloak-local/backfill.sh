#!/bin/bash
# Backfill missing realm roles + role mappings into an already-running Keycloak.
#
# Companion to run.sh: where run.sh produces sql/keycloak.sql from scratch
# (full re-seed), backfill.sh applies the diff from user-roles.json against a
# running realm without taking the deployment down.
#
# Targets the running Keycloak you point it at — typically the preview stack
# (graylog.draftvucecuba.mincex.gob.cu while login.* DNS is pending) — using
# the master-realm admin account.
#
# Prerequisites:
#   * migrator-workdir/user-roles.json  -- target role state
#   * migrator-workdir/users.json       -- cas_user_id -> username mapping
#   Both are produced by run.sh / cuba-sql/extract.sh. If they're missing or
#   stale, re-run run.sh first.
#
# Usage:
#   AUTH_URL=https://graylog.draftvucecuba.mincex.gob.cu \
#   AUTH_REALM_NAME=CU \
#   AUTH_ADMIN_USERNAME=admin \
#   AUTH_ADMIN_PASSWORD='...' \
#   AUTH_ADMIN_CLIENT=admin-cli \
#   ./backfill.sh
#
# Idempotent: re-running after success is a no-op.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$SCRIPT_DIR/migrator-workdir"

: "${COUNTRY:=cuba}"
EXTRACT_DIR="$SCRIPT_DIR/${COUNTRY}-sql"

for f in user-roles.json users.json; do
    if [[ ! -s "$WORKDIR/$f" ]]; then
        echo "Missing $WORKDIR/$f — run ./run.sh first to produce the JSON extracts." >&2
        exit 2
    fi
done

for v in AUTH_URL AUTH_REALM_NAME AUTH_ADMIN_USERNAME AUTH_ADMIN_PASSWORD AUTH_ADMIN_CLIENT; do
    if [[ -z "${!v:-}" ]]; then
        echo "Missing required env var: $v" >&2
        echo "See header of $0 for example usage." >&2
        exit 2
    fi
done

# The migrator compose service also needs these (for the realm-import volume
# mount + container env), but in backfill mode the keycloak service is not
# started, so REALM_JSON_PATH only needs to exist as a path — point it at the
# vendored compose file itself so the file is real but never read.
: "${KC_REALM_NAME:=$AUTH_REALM_NAME}"
: "${REALM_JSON_PATH:=./docker-compose.yml}"
: "${INSTITUTION_GROUP_ID:=00000000-0000-0000-0000-000000000000}"
: "${MIGRATOR_SRC_PATH:=./migrator-src}"
export COUNTRY KC_REALM_NAME REALM_JSON_PATH INSTITUTION_GROUP_ID MIGRATOR_SRC_PATH

echo "== Staging backfill.js into migrator-workdir =="
cp "$EXTRACT_DIR/backfill.js" "$WORKDIR/backfill.js"

# Reuse the migrator container so node_modules is shared with run.sh and the
# admin URL stays on the kc network when targeting a co-deployed Keycloak.
# When AUTH_URL points at an external host (the usual case for backfill), the
# container reaches it via the host network.
#
# TLS verification is disabled here on purpose: this tool only ever points at
# Cuba's internal Keycloak deployments (preview/live), where the public certs
# are known to drift expired between renewals and the operator has out-of-
# band trust in the target. Re-enable strict TLS by exporting
# NODE_TLS_REJECT_UNAUTHORIZED=1 before running.
echo "== Running backfill against $AUTH_URL realm=$AUTH_REALM_NAME =="
docker compose -f "$SCRIPT_DIR/docker-compose.yml" run --rm \
    -e AUTH_URL="$AUTH_URL" \
    -e AUTH_REALM_NAME="$AUTH_REALM_NAME" \
    -e AUTH_ADMIN_USERNAME="$AUTH_ADMIN_USERNAME" \
    -e AUTH_ADMIN_PASSWORD="$AUTH_ADMIN_PASSWORD" \
    -e AUTH_ADMIN_CLIENT="$AUTH_ADMIN_CLIENT" \
    -e NODE_TLS_REJECT_UNAUTHORIZED="${NODE_TLS_REJECT_UNAUTHORIZED:-0}" \
    migrator sh -c '
set -euo pipefail
cp /src/package.json /app/
cp /src/package-lock.json /app/ 2>/dev/null || true
cd /app
if [ ! -d node_modules ]; then
    npm install --no-audit --no-fund --loglevel=error
fi
node backfill.js
'
