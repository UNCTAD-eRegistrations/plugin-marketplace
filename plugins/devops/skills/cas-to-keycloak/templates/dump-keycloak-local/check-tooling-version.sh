#!/bin/bash
# Staleness guard for the vendored cas-to-keycloak tooling.
#
# The skill stages this whole `dump-keycloak-local/` directory into a country
# repo's `sql/` and runs from there. A fix that lands in the plugin therefore
# does NOT reach a cutover whose staged copy is old — which is exactly how a
# dev.cuba seed dropped 23 users to a bug that was already fixed upstream
# (see issue #42 / LESSONS "staged tooling goes stale").
#
# This script compares the AUTHORITATIVE version (the TOOLING_VERSION shipped
# next to this script, inside the plugin) against the version of a STAGED copy,
# and fails loudly when the staged copy is older or missing its stamp. Every
# mode (fetch/seed/deploy/backfill/reconcile) should run it before doing work.
#
# Usage:
#   check-tooling-version.sh <staged-dir>
# where <staged-dir> is the country repo's sql/dump-keycloak-local/.
# Exit codes: 0 = up to date, 3 = stale/missing (caller should re-stage), 2 = usage.

set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTHORITATIVE_FILE="$SELF_DIR/TOOLING_VERSION"

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <staged-dir>" >&2
    exit 2
fi
STAGED_DIR="$1"
STAGED_FILE="$STAGED_DIR/TOOLING_VERSION"

if [[ ! -f "$AUTHORITATIVE_FILE" ]]; then
    echo "check-tooling-version: no TOOLING_VERSION beside this script — cannot verify." >&2
    exit 2
fi
AUTHORITATIVE="$(tr -d '[:space:]' < "$AUTHORITATIVE_FILE")"

if [[ ! -f "$STAGED_FILE" ]]; then
    echo "!! STALE TOOLING: '$STAGED_DIR' has no TOOLING_VERSION (staged before versioning existed)."
    echo "   Authoritative version is $AUTHORITATIVE. Re-stage the tooling before running:"
    echo "     cp -a \"$SELF_DIR/.\" \"$STAGED_DIR/\"   # after reconciling any local edits"
    exit 3
fi
STAGED="$(tr -d '[:space:]' < "$STAGED_FILE")"

# Numeric-aware compare: staged is stale iff it sorts strictly before authoritative.
if [[ "$STAGED" == "$AUTHORITATIVE" ]]; then
    echo "tooling up to date ($STAGED)."
    exit 0
fi
older="$(printf '%s\n%s\n' "$STAGED" "$AUTHORITATIVE" | sort -V | head -1)"
if [[ "$older" == "$STAGED" ]]; then
    echo "!! STALE TOOLING: staged copy is $STAGED but the plugin ships $AUTHORITATIVE."
    echo "   Fixes since $STAGED will NOT run. Re-stage before proceeding:"
    echo "     cp -a \"$SELF_DIR/.\" \"$STAGED_DIR/\"   # after reconciling any local edits"
    exit 3
fi

# Staged newer than plugin — operator is ahead (local WIP); note but don't block.
echo "note: staged tooling ($STAGED) is newer than this plugin ($AUTHORITATIVE) — using staged copy."
exit 0
