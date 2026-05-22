#!/bin/bash
# Fetch CAS + partc schema dumps from a source eRegistrations Postgres host.
#
# Assumes:
#   * Both `cas` and `partc` are SCHEMAS inside a single Postgres database on
#     the same cluster (current eRegistrations convention).
#   * The operator has ssh access to the source host with sudo privileges
#     (so `sudo -u postgres pg_dump …` runs without an additional prompt).
#
# Output:
#   <repo>/sql/cas.sql    (xz-compressed pg_dump of schema cas)
#   <repo>/sql/partc.sql  (xz-compressed pg_dump of schema partc)
#
# Both filenames match what run.sh expects so it can load them directly.
#
# Usage:
#   ./fetch-dumps.sh <ssh-host> <db-name> <repo-root>
#
# Example:
#   ./fetch-dumps.sh swarm.vucecuba.mincex.gob.cu eregistrations \
#       /home/jenkins/cuba-eregistrations
#
# Re-runs overwrite the existing dumps.

set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "usage: $0 <ssh-host> <db-name> <repo-root>" >&2
    exit 2
fi

SSH_HOST="$1"
DB_NAME="$2"
REPO_ROOT="$3"

if [[ ! -d "$REPO_ROOT" ]]; then
    echo "Repo root '$REPO_ROOT' does not exist." >&2
    exit 2
fi

SQL_DIR="$REPO_ROOT/sql"
mkdir -p "$SQL_DIR"

dump_schema() {
    local schema="$1" outfile="$2"
    echo "== Dumping schema '$schema' from $SSH_HOST:$DB_NAME → $outfile =="
    # `-Fp` (plain) so `xzcat | psql` works in run.sh.
    # `-n <schema>` restricts to one schema; `-O` and `-x` strip owners and
    # privileges so the restore side doesn't have to mirror server roles
    # (CREATE ROLE statements are added explicitly in run.sh).
    ssh "$SSH_HOST" "sudo -u postgres pg_dump -d '$DB_NAME' -n '$schema' -Fp -O -x | xz -c" > "$outfile.tmp"
    mv "$outfile.tmp" "$outfile"

    # Sanity-check: extract a row count from one well-known table per schema
    # so a silent empty-dump failure shows up at fetch time rather than at
    # seed time.
    local user_table=""
    case "$schema" in
        cas)   user_table='cas."user"'   ;;
        partc) user_table='partc."user"' ;;
    esac
    if [[ -n "$user_table" ]]; then
        # Count rows by spotting the COPY block in the dump.
        local rows
        rows=$(xzcat "$outfile" | awk -v t="COPY $user_table" '
            $0 ~ t { in_copy=1; next }
            in_copy && /^\\\.$/ { exit }
            in_copy { n++ }
            END { print n+0 }
        ')
        echo "   $user_table rows: $rows"
        if [[ "$rows" == "0" ]]; then
            echo "   WARNING: zero rows in $user_table — verify db/schema names" >&2
        fi
    fi
    ls -lh "$outfile"
}

dump_schema cas   "$SQL_DIR/cas.sql"
dump_schema partc "$SQL_DIR/partc.sql"

echo
echo "== Done =="
echo "Dumps written to $SQL_DIR/"
echo "Next step: run ./run.sh to produce sql/keycloak.sql."
