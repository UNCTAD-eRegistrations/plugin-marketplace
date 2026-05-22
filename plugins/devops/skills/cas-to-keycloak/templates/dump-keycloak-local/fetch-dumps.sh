#!/bin/bash
# Fetch CAS + partc schema dumps from a source eRegistrations Postgres host.
#
# Supports both layouts the platform has used in practice:
#   * Two separate databases on the same cluster (the historical CAS-based
#     deployments — `psql -d cas` and `psql -d partc`, each holding a schema
#     of the same name as the database). This is what Cuba LIVE looks like.
#   * Single database holding both schemas (consolidated dev / replay hosts).
#
# In either case the schema names inside the dumps are `cas` and `partc` —
# never `public` — because the existing migrator's SQL extracts reference
# them by schema prefix.
#
# Output:
#   <repo>/sql/cas.sql    (xz-compressed pg_dump of schema cas)
#   <repo>/sql/partc.sql  (xz-compressed pg_dump of schema partc)
#
# Both filenames match what run.sh expects so it can load them directly.
#
# Usage:
#   ./fetch-dumps.sh <ssh-host> <repo-root> [cas-db] [partc-db]
#
# Defaults: cas-db = cas, partc-db = partc (matches the historical two-DB
# layout). For a consolidated host, pass the same db-name twice:
#   ./fetch-dumps.sh swarm.example.com /home/jenkins/x eregistrations eregistrations
#
# Re-runs overwrite the existing dumps.

set -euo pipefail

if [[ $# -lt 2 || $# -gt 4 ]]; then
    echo "usage: $0 <ssh-host> <repo-root> [cas-db] [partc-db]" >&2
    exit 2
fi

SSH_HOST="$1"
REPO_ROOT="$2"
CAS_DB="${3:-cas}"
PARTC_DB="${4:-partc}"

if [[ ! -d "$REPO_ROOT" ]]; then
    echo "Repo root '$REPO_ROOT' does not exist." >&2
    exit 2
fi

SQL_DIR="$REPO_ROOT/sql"
mkdir -p "$SQL_DIR"

dump_schema() {
    local db="$1" schema="$2" outfile="$3"
    echo "== Dumping schema '$schema' from $SSH_HOST:$db → $outfile =="
    # `-Fp` (plain) so `xzcat | psql` works in run.sh.
    # `-n <schema>` restricts to one schema; `-O` and `-x` strip owners and
    # privileges so the restore side doesn't have to mirror server roles
    # (CREATE ROLE statements are added explicitly in run.sh).
    ssh "$SSH_HOST" "sudo -u postgres pg_dump -d '$db' -n '$schema' -Fp -O -x | xz -c" > "$outfile.tmp"
    mv "$outfile.tmp" "$outfile"

    # Sanity-check: extract a row count from one well-known table per schema
    # so a silent empty-dump failure shows up at fetch time rather than at
    # seed time.
    local rows
    rows=$(xzcat "$outfile" | awk -v t="COPY ${schema}.\"user\"" '
        $0 ~ t { in_copy=1; next }
        in_copy && /^\\\.$/ { exit }
        in_copy { n++ }
        END { print n+0 }
    ')
    echo "   ${schema}.\"user\" rows: $rows"
    if [[ "$rows" == "0" ]]; then
        echo "   WARNING: zero rows in ${schema}.\"user\" — verify db/schema names" >&2
    fi
    ls -lh "$outfile"
}

dump_schema "$CAS_DB"   cas   "$SQL_DIR/cas.sql"
dump_schema "$PARTC_DB" partc "$SQL_DIR/partc.sql"

echo
echo "== Done =="
echo "Dumps written to $SQL_DIR/"
echo "Next step: run ./run.sh to produce sql/keycloak.sql."
