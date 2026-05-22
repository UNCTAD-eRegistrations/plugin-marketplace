#!/bin/bash
# backfill-other-name-attrs.sh — Patch existing Keycloak users with the
# `other_names` and `other_lastname` attributes that VUCE-36 missed during
# the initial CAS→Keycloak migration.
#
# Reads the regenerated migrator-workdir/users.json (which now carries
# attribute_other_names + attribute_other_lastname) and PATCHes each
# matching live Keycloak user, preserving all other attributes.
#
# Idempotent: skips users already carrying the same values, and reports any
# user that doesn't exist in the target Keycloak (e.g. case-collision losers).
#
# Usage:
#   AUTH_URL=https://login.draftvucecuba.mincex.gob.cu \
#   AUTH_REALM=CU \
#   AUTH_ADMIN_USERNAME=admin \
#   AUTH_ADMIN_PASSWORD='…' \
#   ./backfill-other-name-attrs.sh [--dry-run]
#
# Optional env vars:
#   AUTH_ADMIN_CLIENT  — admin client (default admin-cli)
#   AUTH_INSECURE=1    — skip TLS verify (use only for self-signed / staging)
#
# Requires: bash, curl, jq.

set -euo pipefail

DRY_RUN=0
case "${1:-}" in
    -n|--dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '2,/^$/p' "$0"; exit 0 ;;
    "")           ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
esac

: "${AUTH_URL:?Set AUTH_URL (e.g. https://login.draftvucecuba.mincex.gob.cu)}"
: "${AUTH_REALM:?Set AUTH_REALM (e.g. CU)}"
: "${AUTH_ADMIN_USERNAME:?Set AUTH_ADMIN_USERNAME}"
: "${AUTH_ADMIN_PASSWORD:?Set AUTH_ADMIN_PASSWORD}"
AUTH_ADMIN_CLIENT="${AUTH_ADMIN_CLIENT:-admin-cli}"

CURL_OPTS=()
[[ "${AUTH_INSECURE:-0}" == "1" ]] && CURL_OPTS+=(-k)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USERS_JSON="$SCRIPT_DIR/migrator-workdir/users.json"
[[ -f $USERS_JSON ]] || { echo "Missing $USERS_JSON — re-run cuba-sql/extract.sh first" >&2; exit 1; }

command -v jq   >/dev/null || { echo "jq not installed"   >&2; exit 1; }
command -v curl >/dev/null || { echo "curl not installed" >&2; exit 1; }

get_token() {
    local resp
    resp=$(curl -sS "${CURL_OPTS[@]}" -X POST "$AUTH_URL/realms/master/protocol/openid-connect/token" \
        -H 'Content-Type: application/x-www-form-urlencoded' \
        --data-urlencode "grant_type=password" \
        --data-urlencode "client_id=$AUTH_ADMIN_CLIENT" \
        --data-urlencode "username=$AUTH_ADMIN_USERNAME" \
        --data-urlencode "password=$AUTH_ADMIN_PASSWORD" 2>&1) || { echo "$resp" >&2; return 1; }
    jq -r '.access_token // empty' <<<"$resp"
}

if ! TOKEN=$(get_token); then
    echo "Auth call failed (see error above). If TLS chain is the issue, retry with AUTH_INSECURE=1." >&2
    exit 1
fi
[[ -n $TOKEN ]] || { echo "Auth returned no token. Check AUTH_ADMIN_USERNAME/PASSWORD against $AUTH_URL/realms/master." >&2; exit 1; }
TOKEN_TS=$(date +%s)

refresh_token_if_stale() {
    # Master admin tokens default to 60 s lifetime; refresh proactively at 45 s.
    if (( $(date +%s) - TOKEN_TS > 45 )); then
        TOKEN=$(get_token)
        TOKEN_TS=$(date +%s)
    fi
}

candidates=$(jq '[.[] | select(.attribute_other_names or .attribute_other_lastname)] | length' "$USERS_JSON")
echo "Source candidates with at least one missing attribute: $candidates"
echo "Target: $AUTH_URL  realm=$AUTH_REALM"
(( DRY_RUN )) && echo "(dry-run: no PUT calls will be issued)"
echo "---"

patched=0; unchanged=0; missing=0; failed=0

while IFS= read -r u; do
    refresh_token_if_stale
    username=$(jq -r .username <<<"$u")
    on=$(jq -r '.attribute_other_names    // empty' <<<"$u")
    ol=$(jq -r '.attribute_other_lastname // empty' <<<"$u")

    found=$(curl -sf "${CURL_OPTS[@]}" -G "$AUTH_URL/admin/realms/$AUTH_REALM/users" \
        -H "Authorization: Bearer $TOKEN" \
        --data-urlencode "username=$username" \
        --data-urlencode "exact=true" \
        --data-urlencode "briefRepresentation=false" || echo '[]')
    user=$(jq -c '.[0] // empty' <<<"$found")
    if [[ -z $user || $user == "null" ]]; then
        printf '  MISSING   %s\n' "$username"
        missing=$((missing+1))
        continue
    fi

    user_id=$(jq -r .id <<<"$user")
    cur_on=$(jq -r '.attributes.other_names[0]    // empty' <<<"$user")
    cur_ol=$(jq -r '.attributes.other_lastname[0] // empty' <<<"$user")
    if [[ "$cur_on" == "$on" && "$cur_ol" == "$ol" ]]; then
        unchanged=$((unchanged+1))
        continue
    fi

    merged=$(jq --arg n "$on" --arg l "$ol" '
        .attributes = (.attributes // {})
        | if $n != "" then .attributes.other_names    = [$n] else . end
        | if $l != "" then .attributes.other_lastname = [$l] else . end
    ' <<<"$user")

    if (( DRY_RUN )); then
        printf '  WOULD     %s  other_names=%q other_lastname=%q\n' "$username" "$on" "$ol"
        patched=$((patched+1))
        continue
    fi

    if curl -sf "${CURL_OPTS[@]}" -o /dev/null -X PUT "$AUTH_URL/admin/realms/$AUTH_REALM/users/$user_id" \
        -H "Authorization: Bearer $TOKEN" \
        -H 'Content-Type: application/json' \
        -d "$merged"; then
        printf '  PATCHED   %s\n' "$username"
        patched=$((patched+1))
    else
        printf '  FAILED    %s\n' "$username"
        failed=$((failed+1))
    fi
done < <(jq -c '.[] | select(.attribute_other_names or .attribute_other_lastname)' "$USERS_JSON")

echo "---"
echo "Patched:   $patched"
echo "Unchanged: $unchanged   (already had matching values)"
echo "Missing:   $missing     (not present in target Keycloak — likely case-collision losers)"
echo "Failed:    $failed"
