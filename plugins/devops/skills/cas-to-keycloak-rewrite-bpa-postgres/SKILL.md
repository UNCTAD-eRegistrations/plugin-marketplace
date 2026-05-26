---
name: cas-to-keycloak-rewrite-bpa-postgres
description: >
  Rewrite legacy PARTC integer institution_id / unit_id values in BPA's own
  postgres to the corresponding Keycloak group UUIDs after a CAS-to-KC
  migration. Required cutover step — without it, BPA-frontend's institution
  picker calls KC `/admin/realms/<R>/groups/{id}/children` with stale PARTC
  integers and 404s. Reads the `partc_institution_id` / `partc_unit_id`
  attributes stamped on KC groups by the `cas-to-keycloak` seed phase
  (accepts the legacy `partc_institution_unit_id` key for back-compat).
  Phase 8 in the cas-to-keycloak orchestrator chain.
license: UNCTAD-Internal
compatibility: >
  Requires the `cas-to-keycloak` seed + deploy phases completed so the
  target Keycloak holds every institution + unit as KC groups, each
  carrying the corresponding `partc_*` attribute. Requires ssh to the
  deploy host with sudo (for `docker exec` against the keycloak container
  and `sudo -u postgres psql` against the BPA database).
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, TodoWrite
metadata:
  version: "1.0.0"
  version-date: "2026-05-26"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<country>"
  jira: "TOBE-17751"
---

# Rewrite BPA Postgres Institution Refs

After the seed + deploy phases port identities to Keycloak, BPA's own postgres still holds the legacy PARTC integer FKs in **4 tables / 5 columns**:

| Table | Column(s) | Holds |
|---|---|---|
| `registration_institution` | `institution_id` | PARTC integer institution id |
| `role_institution` | `institution_id` | same |
| `role_institution` | `unit_id` | PARTC integer unit id (optional) |
| `registration_unit` | `institution_id`, `unit_id` | both |

BPA-frontend's `institution-controller.service.ts` reads these `String` columns and forwards them verbatim to KC `/admin/realms/<R>/groups/{id}/children?max=200`. KC treats `1` as a group UUID and returns 404 `{"error":"Could not find group by id"}`. Result: empty institution pickers / silent UI breakage on every legacy reference.

This skill rewrites them deterministically using the `partc_institution_id` / `partc_unit_id` attributes stamped on KC groups by `cas-to-keycloak` (seed phase). It's idempotent — running it twice is a no-op on the second pass.

## STEP 0: Gather info

Ask the operator:
1. **Realm name** (e.g. `CU`).
2. **Country instance host** for SSH (e.g. `cuba.live` from `~/.ssh/config`).
3. **BPA postgres DB name** — defaults to `eregistrationbpa`.

`KEYCLOAK_INSTITUTIONS_GROUP_ID`, `KEYCLOAK_RESOURCE`, `KEYCLOAK_SECRET` are recovered from the `bpa-backend` container's runtime env (no `.env` file enumeration).

## STEP 1: Build the mapping from KC

Walk root institutions → subgroups, extract `partc_institution_id` / `partc_unit_id` (or legacy `partc_institution_unit_id`), dump to JSON for review.

```bash
ssh <country.host> 'set -e
ENV=$(sudo -n docker inspect bpa-backend --format "{{range .Config.Env}}{{println .}}{{end}}")
RES=$(echo "$ENV" | awk -F= "/^KEYCLOAK_RESOURCE=/{print substr(\$0,index(\$0,\"=\")+1); exit}")
SEC=$(echo "$ENV" | awk -F= "/^KEYCLOAK_SECRET=/{print substr(\$0,index(\$0,\"=\")+1); exit}")
GRP=$(echo "$ENV" | awk -F= "/^KEYCLOAK_INSTITUTIONS_GROUP_ID=/{print substr(\$0,index(\$0,\"=\")+1); exit}")
REALM=<REALM>
sudo -n docker exec keycloak curl -sS -X POST \
  "http://localhost:8080/realms/$REALM/protocol/openid-connect/token" \
  -d "grant_type=client_credentials" -d "client_id=$RES" -d "client_secret=$SEC" > /tmp/tok.json
export TOKEN=$(python3 -c "import json; print(json.load(open(\"/tmp/tok.json\"))[\"access_token\"])")
export GRP REALM
sudo -n docker exec keycloak curl -sS -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/admin/realms/$REALM/groups/$GRP/children?max=200" > /tmp/insts.json
python3 <<PYEOF
import os, json, subprocess
TOKEN, REALM = os.environ["TOKEN"], os.environ["REALM"]
insts = json.load(open("/tmp/insts.json"))
out = {"institutions": [], "units": []}
for g in insts:
    a = g.get("attributes") or {}
    pid = (a.get("partc_institution_id") or [None])[0]
    out["institutions"].append({"partc_id": pid, "uuid": g["id"], "name": g["name"]})
    if g.get("subGroupCount", 0):
        r = subprocess.run(["sudo","-n","docker","exec","keycloak","curl","-sS",
            "-H","Authorization: Bearer "+TOKEN,
            "http://localhost:8080/admin/realms/"+REALM+"/groups/"+g["id"]+"/children?max=200"],
            capture_output=True, text=True)
        for sg in json.loads(r.stdout):
            sa = sg.get("attributes") or {}
            # Accept either the canonical key (post-rename) or the legacy verbose key.
            uid = (sa.get("partc_unit_id") or sa.get("partc_institution_unit_id") or [None])[0]
            out["units"].append({"partc_unit_id": uid, "uuid": sg["id"], "name": sg["name"],
                                 "parent_uuid": g["id"], "parent_partc_id": pid})
print(json.dumps(out, indent=2, ensure_ascii=False))
PYEOF
' > /tmp/mapping.json
```

Spot-check: every institution has a non-null `partc_id`. Every unit has a non-null `partc_unit_id`. If any are null, the seed phase ran with an even older SQL template — see "Fallback" below.

## STEP 2: Inspect broken rows (no writes)

```sql
SELECT 'registration_institution' AS t, institution_id, COUNT(*)
FROM registration_institution
WHERE institution_id !~ '^[0-9a-fA-F-]{36}$'
GROUP BY institution_id
UNION ALL
SELECT 'role_institution.institution_id', institution_id, COUNT(*)
FROM role_institution
WHERE institution_id !~ '^[0-9a-fA-F-]{36}$'
GROUP BY institution_id
UNION ALL
SELECT 'registration_unit', institution_id || '/' || unit_id, COUNT(*)
FROM registration_unit
WHERE institution_id !~ '^[0-9a-fA-F-]{36}$' OR unit_id !~ '^[0-9a-fA-F-]{36}$'
GROUP BY institution_id, unit_id
UNION ALL
SELECT 'role_institution.unit_id', institution_id || '/' || unit_id, COUNT(*)
FROM role_institution
WHERE unit_id IS NOT NULL AND unit_id !~ '^[0-9a-fA-F-]{36}$'
GROUP BY institution_id, unit_id
ORDER BY 1, 2;
```

This surfaces **orphans** early — PARTC integers that appear in BPA but have no `partc_*` attribute on any KC group. Two kinds:
- **Pre-migration corruption** — refs to PARTC ids that never existed in PARTC either (e.g. `unit_id=11` when PARTC's max is 10). Broken in CAS too; migration just made them throw 404 instead of returning empty.
- **Mis-assigned children** — refs like `(institution=AGR, unit=3)` where unit 3 belongs to MINCEX in PARTC. Designer typo at service creation.

## STEP 3: Backup BPA postgres

```bash
ssh <country.host> '
BACKUP=/tmp/eregistrationbpa-pre-instfix-$(date +%Y%m%d-%H%M%S).sql.gz
sudo -u postgres pg_dump <bpadb> | gzip > "$BACKUP"
ls -lh "$BACKUP"
'
```

Keep until the operator confirms the post-rewrite UI works as expected (typically 24-48h).

## STEP 4: Apply UPDATE in a ROLLBACK'd preview transaction

Build the `inst_map` and `unit_map` CTEs from STEP 1's mapping (one `VALUES` row per non-orphan id), then:

```sql
BEGIN;
-- institution-level (apply BEFORE unit-level — unit UPDATE joins on the now-UUID institution_id)
WITH inst_map(partc_id, kc_uuid) AS (VALUES ...) -- from /tmp/mapping.json
UPDATE registration_institution ri SET institution_id = im.kc_uuid
FROM inst_map im WHERE ri.institution_id = im.partc_id;

WITH inst_map(partc_id, kc_uuid) AS (VALUES ...)
UPDATE role_institution ri SET institution_id = im.kc_uuid
FROM inst_map im WHERE ri.institution_id = im.partc_id;

-- unit-level
WITH unit_map(partc_inst, partc_unit, kc_inst_uuid, kc_unit_uuid) AS (VALUES ...)
UPDATE registration_unit ru SET institution_id = um.kc_inst_uuid, unit_id = um.kc_unit_uuid
FROM unit_map um WHERE ru.institution_id = um.partc_inst AND ru.unit_id = um.partc_unit;

WITH unit_map(partc_inst, partc_unit, kc_inst_uuid, kc_unit_uuid) AS (VALUES ...)
UPDATE role_institution ri SET unit_id = um.kc_unit_uuid
FROM unit_map um
WHERE ri.institution_id = um.kc_inst_uuid  -- post-step-1 UUID
  AND ri.unit_id = um.partc_unit
  AND ri.unit_id !~ '^[0-9a-fA-F-]{36}$';

-- VERIFY: remaining non-UUID rows should be exactly the orphan list from STEP 2
SELECT 'registration_institution' AS t, institution_id, COUNT(*)
FROM registration_institution WHERE institution_id !~ '^[0-9a-fA-F-]{36}$' GROUP BY institution_id
UNION ALL
SELECT 'role_institution.institution_id', institution_id, COUNT(*)
FROM role_institution WHERE institution_id !~ '^[0-9a-fA-F-]{36}$' GROUP BY institution_id
UNION ALL
SELECT 'registration_unit', institution_id||'/'||unit_id, COUNT(*)
FROM registration_unit
WHERE institution_id !~ '^[0-9a-fA-F-]{36}$' OR unit_id !~ '^[0-9a-fA-F-]{36}$'
GROUP BY institution_id, unit_id
UNION ALL
SELECT 'role_institution.unit_id', institution_id||'/'||unit_id, COUNT(*)
FROM role_institution
WHERE unit_id IS NOT NULL AND unit_id !~ '^[0-9a-fA-F-]{36}$'
GROUP BY institution_id, unit_id
ORDER BY 1, 2;

ROLLBACK;  -- swap to COMMIT once verified
```

Confirm row counts match expectations and orphans match. **Do NOT skip the verify** — this is the gate.

## STEP 5: Commit

Re-run STEP 4 with `COMMIT` in place of `ROLLBACK`. No service restart needed (BPA-frontend reads these rows per request; the next page load picks up the new FKs).

## STEP 6: Triage orphans

Join broken rows up to the owning service / role to surface ownership:

```sql
-- registration orphans linked to a service (Bucket A — needs design intent)
SELECT ri.id, ri.institution_id AS broken, r.name AS registration, s.id, s.name AS service
FROM registration_institution ri
JOIN registration r ON r.id = ri.registration_id
LEFT JOIN service_registration sr ON sr.registration_id = r.id
LEFT JOIN service s ON s.id = sr.service_id
WHERE ri.institution_id !~ '^[0-9a-fA-F-]{36}$';

-- role orphans
SELECT ri.id, ri.institution_id AS broken, role.name AS role, s.id, s.name AS service
FROM role_institution ri
JOIN role ON role.id = ri.role_id
LEFT JOIN service s ON s.id = role.service_id
WHERE ri.institution_id !~ '^[0-9a-fA-F-]{36}$';

-- (analogous joins for registration_unit, role_institution.unit_id)
```

Two patterns emerge:
- **Active service** → ticket the service owner; they decide what the ref *should* point at, or whether to delete.
- **Unlinked registration (no `service_registration` join)** → safe DELETE; dead row.

Surface, don't auto-fix. The orphan rows were broken even in the CAS era — the rewrite skill's job ends here.

## STEP 7: Verify

Re-run STEP 2; only the explicitly-accepted orphans should remain.

## Fallback for legacy migrations (KC subgroups missing both attribute keys)

The expected case post-seed is that every KC subgroup carries one of the two attribute keys (either canonical `partc_unit_id` or legacy `partc_institution_unit_id` — both produced from the same `attribute_*` SQL alias in `partc_units.sql`). If a subgroup is missing both:

1. **PARTC still alive on target host** (recommended — codified in `cas-to-keycloak/LESSONS.md` as "don't drop CAS/PARTC for 30 days"). Query `partc.institution_unit` directly to build the unit mapping by `(parent_partc_institution_id, name)` → KC subgroup name. Then re-stamp KC subgroups with `partc_unit_id` for next time:
   ```bash
   # PATCH attributes via /admin/realms/<R>/groups/{uuid} with merged attributes dict
   ```
2. **PARTC dump on operator laptop** — `psql -f partc.sql` into a scratch container, then same as option 1.

If neither is available, fall back to name-matching with operator confirmation per ambiguous case. Tedious; do only as last resort.

## IMPORTANT NOTES

- **`_aud` (Envers) tables are deliberately not touched.** They record what BPA held as of past timestamps; rewriting them would obscure the historical truth. SQL UPDATE bypasses JPA so Envers won't auto-shadow either — that's fine.
- **No service restart needed.** BPA-frontend reads these rows fresh per request.
- **Orphans are NOT migration bugs.** They're pre-existing data-quality issues that the migration merely surfaced (CAS silently returned empty; KC throws 404). Treat them as a separate cleanup ticket, not as a blocker for the migration cutover.
- **Test case:** Cuba LIVE (May 2026) — 293 rows fixed across 4 tables, 10 pre-existing orphan rows (PARTC inst 16/22 phantom, AGR phantom units, ONURE phantom unit). All orphans confirmed broken even in CAS.
