#!/bin/bash
# Runs the 5 Cuba-specific queries against the running cas-db / partc-db
# containers, wraps each result in a JSON array, and writes them into
# ../migrator-workdir/ where the migrator service picks them up.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE="$SCRIPT_DIR/../docker-compose.yml"
OUT_DIR="$SCRIPT_DIR/../migrator-workdir"
mkdir -p "$OUT_DIR"

# $1 = compose service (cas-db | partc-db)
# $2 = target database (postgres — the default DB; dumps populate schemas cas/partc inside it)
# $3 = absolute path to the .sql file
# $4 = output JSON filename (in migrator-workdir)
extract() {
    local svc="$1" db="$2" sql="$3" out="$4"
    # Strip SQL comments (including inline `-- foo`) and trailing semicolon so
    # the query can be used as a subselect. Critical: must strip ALL `-- …`
    # runs, not just lines starting with `--`, or the trailing comment will
    # swallow the rest of the query once newlines are collapsed to spaces.
    local query
    query=$(sed -E 's/--[^\n]*//g' "$sql" | tr '\n' ' ' | sed -E 's/;[[:space:]]*$//')
    local wrapped="SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json) FROM (${query}) t;"
    echo "  → $out  (via $svc)"
    docker compose -f "$COMPOSE" exec -T "$svc" \
        psql -U postgres -d "$db" -tAc "$wrapped" > "$OUT_DIR/$out"
    local count
    count=$(python3 -c "import json,sys; print(len(json.load(open('$OUT_DIR/$out'))))" 2>/dev/null || echo "?")
    echo "     rows: $count"
}

echo "== Extracting Cuba migration inputs =="
extract cas-db   postgres "$SCRIPT_DIR/cas_users.sql"             users.json
extract partc-db postgres "$SCRIPT_DIR/partc_institutions.sql"    institutions.json
extract partc-db postgres "$SCRIPT_DIR/partc_units.sql"           units.json
extract partc-db postgres "$SCRIPT_DIR/partc_user_memberships.sql" user-memberships.json
# Role mappings come from BOTH partc.user_role (primary, includes Cuba-specific
# admin roles) and cas.user_role (catches manager and any cas-only roles).
# Merged below; downstream migrate.js sees a single user-roles.json.
extract partc-db postgres "$SCRIPT_DIR/partc_user_roles.sql"      user-roles-partc.json
extract cas-db   postgres "$SCRIPT_DIR/cas_user_roles.sql"        user-roles-cas.json

echo "== Merging partc + cas role mappings into user-roles.json =="
python3 - <<PY
import json, pathlib
out_dir = pathlib.Path("$OUT_DIR")
partc = json.loads((out_dir / "user-roles-partc.json").read_text())
cas   = json.loads((out_dir / "user-roles-cas.json").read_text())
# Dedupe on the tuple downstream migrate.js distinguishes on.
seen = set()
merged = []
for row in partc + cas:
    key = (row["attribute_cas_user_id"], row["role_name"], bool(row.get("realm_role")), row.get("client"))
    if key in seen:
        continue
    seen.add(key)
    merged.append(row)
(out_dir / "user-roles.json").write_text(json.dumps(merged))
print(f"  merged rows: partc={len(partc)} cas={len(cas)} unique={len(merged)}")
PY

echo "== Sanity: distinct realm roles about to be assigned =="
python3 -c "
import json
roles = json.load(open('$OUT_DIR/user-roles.json'))
realm_roles = sorted({r['role_name'] for r in roles if r.get('realm_role')})
client_roles = sorted({(r['client'], r['role_name']) for r in roles if not r.get('realm_role')})
print('realm roles:', realm_roles)
print('client roles:', client_roles)
"

echo "== Done =="
