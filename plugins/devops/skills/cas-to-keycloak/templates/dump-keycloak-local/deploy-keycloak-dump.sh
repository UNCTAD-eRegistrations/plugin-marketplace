#!/bin/bash
# Load a seeded sql/keycloak.sql onto the target deploy host's Keycloak
# Postgres, then restart the Keycloak service to pick up the imported realm
# without burning the cutover window on a live --import-realm boot.
#
# Workflow:
#   1. scp sql/keycloak.sql to the target host (under /tmp/<basename>).
#   2. ssh into the host and `sudo -u postgres psql` the dump into the
#      target database. The dump itself begins with `DROP DATABASE IF EXISTS`
#      (assuming it was produced by `pg_dump --clean --if-exists`), so a
#      one-shot load is safe; we additionally pg_terminate_backend before
#      psql to flush any existing connections.
#   3. Restart the Keycloak service. Two shapes supported:
#        compose: `docker compose restart keycloak` from the compose dir
#        swarm:   `docker service update --force <stack>_keycloak`
#      Auto-detected from the host's running stack; overridable.
#   4. Wait for the Keycloak health endpoint to come back healthy.
#
# Usage:
#   ./deploy-keycloak-dump.sh <ssh-host> <repo-root> [options]
#
# Options (env vars):
#   KC_DB_NAME=keycloak                  database name on the target Postgres
#   KC_DB_USER=keycloak                  owner / connect user
#   KC_COMPOSE_DIR=/opt/eregistrations/Conf-LIVE/compose/<country>
#                                        path to docker-compose dir on the host;
#                                        compose mode only.
#   KC_SWARM_STACK=<empty>               if set, treat target as swarm and run
#                                        `docker service update` against
#                                        ${KC_SWARM_STACK}_keycloak.
#   KC_HEALTH_URL=http://127.0.0.1:9003/health/ready
#                                        used for the post-restart probe.
#   DRY_RUN=0                            1 = print the commands without
#                                        executing the destructive ones.
#
# This script is the "semi-auto" deploy step in the cas-to-keycloak chain. It
# never reads .env files on the deploy host; secrets the operator needs to
# wire (KC_DB_PASSWORD, KEYCLOAK_ADMIN_*, OAuth client secrets) are surfaced
# by the seed / realm-prep steps and are the operator's responsibility to
# place via the appropriate channel (env file or docker secret).

set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "usage: $0 <ssh-host> <repo-root>" >&2
    exit 2
fi

SSH_HOST="$1"
REPO_ROOT="$2"
DUMP="$REPO_ROOT/sql/keycloak.sql"

KC_DB_NAME="${KC_DB_NAME:-keycloak}"
KC_DB_USER="${KC_DB_USER:-keycloak}"
KC_COMPOSE_DIR="${KC_COMPOSE_DIR:-}"
KC_SWARM_STACK="${KC_SWARM_STACK:-}"
KC_HEALTH_URL="${KC_HEALTH_URL:-http://127.0.0.1:9003/health/ready}"
DRY_RUN="${DRY_RUN:-0}"

if [[ ! -s "$DUMP" ]]; then
    echo "Missing $DUMP — run seed (run.sh) first." >&2
    exit 2
fi

REMOTE_PATH="/tmp/$(basename "$DUMP")"

say() { printf '== %s ==\n' "$*"; }
do_remote() {
    if [[ "$DRY_RUN" == "1" ]]; then
        printf '[dry-run] ssh %s %q\n' "$SSH_HOST" "$1"
    else
        ssh "$SSH_HOST" "$1"
    fi
}

say "Uploading dump to $SSH_HOST:$REMOTE_PATH ($(du -h "$DUMP" | cut -f1))"
if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run] scp %s %s:%s\n' "$DUMP" "$SSH_HOST" "$REMOTE_PATH"
else
    scp -q "$DUMP" "$SSH_HOST:$REMOTE_PATH"
fi

say "Terminating live $KC_DB_NAME connections + loading dump"
# The dump's `DROP DATABASE IF EXISTS` will fail if there are still active
# sessions on the database, so flush them first. psql -v ON_ERROR_STOP=1
# ensures we abort loudly on a load error rather than producing a half-imported
# realm DB.
do_remote "sudo -u postgres psql -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$KC_DB_NAME' AND pid <> pg_backend_pid();\" >/dev/null"
do_remote "sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -f $REMOTE_PATH >/dev/null"

# Restart Keycloak so it picks up the new realm state.
if [[ -n "$KC_SWARM_STACK" ]]; then
    say "Restarting swarm service ${KC_SWARM_STACK}_keycloak"
    do_remote "docker service update --force ${KC_SWARM_STACK}_keycloak >/dev/null"
else
    if [[ -z "$KC_COMPOSE_DIR" ]]; then
        # Best-effort default — operator can override via env.
        KC_COMPOSE_DIR="/opt/eregistrations/Conf-LIVE/compose/$(basename "$REPO_ROOT" | sed -E 's/-eregistrations$//')"
    fi
    say "Restarting compose keycloak in $KC_COMPOSE_DIR"
    do_remote "cd $KC_COMPOSE_DIR && docker compose restart keycloak"
fi

# Wait for health endpoint. Quarkus-based Keycloak (2.17+) exposes the
# management-port health endpoint at $KC_HEALTH_URL.
say "Waiting for Keycloak health probe ($KC_HEALTH_URL)"
if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run] poll %s up to 180s\n' "$KC_HEALTH_URL"
else
    deadline=$(($(date +%s) + 180))
    until ssh "$SSH_HOST" "curl -sf --max-time 3 $KC_HEALTH_URL >/dev/null" 2>/dev/null; do
        (( $(date +%s) > deadline )) && { echo "  ! Health probe timed out after 180s" >&2; exit 1; }
        printf '.'
        sleep 5
    done
    echo " → healthy"
fi

# Clean up the staged dump on the remote (it's just a copy of what's in git).
do_remote "rm -f $REMOTE_PATH"

say "Done"
echo "Keycloak on $SSH_HOST is running with the freshly-seeded realm."
echo "Next: run cas-to-keycloak-backfill (in case the seed missed any role mappings)."
