---
name: cas-to-keycloak-rewrite-camunda-role-groups
description: >
  Rewrite legacy CAS-style tokens (`i<partc_id>[_<role>]`,
  `u<partc_id>[_<role>]`, bare unit ids) in Camunda's
  `ereg_service_role_group` table to the Keycloak group UUIDs created by the
  CAS-to-KC migration. Required cutover step — without it ds-backend's
  institution filter (`apps/utilities/institution_permissions.py`) finds no
  overlap between the user's KC group UUIDs and the stored legacy tokens, so
  every PartB operator sees an empty service list until each service is
  republished through BPA. Reads the `partc_institution_id` /
  `partc_unit_id` attributes stamped on KC groups by the `cas-to-keycloak`
  seed phase. Phase 9 in the cas-to-keycloak orchestrator chain.
license: UNCTAD-Internal
compatibility: >
  Requires the `cas-to-keycloak` seed + deploy phases completed so the
  target Keycloak holds every institution + unit as KC groups, each carrying
  the corresponding `partc_*` attribute. Requires a KC admin bearer token
  (service account or admin) and psql access to the Camunda postgres
  database.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, TodoWrite
metadata:
  version: "1.0.0"
  version-date: "2026-07-03"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<country>"
  jira: "TOBE-17751"
---

# Rewrite Camunda `ereg_service_role_group` Tokens

The migrator populates Keycloak (users + groups + memberships) but **does not
touch the Camunda BPMN database**. Camunda still owns a table
`public.ereg_service_role_group(service_id, role_id, group, determinant)`
that ties each service-role to the institution / unit allowed to handle it.
Its `group` column carries legacy CAS tokens:

- `i<partc_id>` or `i<partc_id>_<businessRole>` (e.g. `i5`, `i5_processing`)
  — an institution membership requirement.
- `u<partc_id>[_<businessRole>]` — a unit membership requirement.
- Bare `<partc_id>` — Cuba-flavoured shorthand for a unit id.
- `applicant`, `super_mario` — magic tokens, must be preserved as-is.
- UUIDs — already migrated entries (services that have been republished
  through BPA post-migration).

After the app cutover (migrate-apps phase), ds-backend's
`apps/utilities/institution_permissions.py` intersects these tokens with the
user's KC group UUIDs and finds no overlap — so every PartB operator sees an
empty service list until either every service is re-published through BPA or
this table is rewritten directly. The latter is faster, idempotent, and
side-effect-free.

This skill ships two artefacts (in this skill's directory):

- `rewrite_camunda_role_groups.py` — read-only against KC; walks the
  institutions tree via the Admin REST API and emits `inst_map.csv` +
  `unit_map.csv` (legacy partc id → KC group UUID).
- `rewrite_camunda_role_groups.sql.tpl` — transactional psql script that
  stages the CSVs and rewrites the table, with a self-backup and a hard
  assertion that no legacy token survives.

## STEP 0: Gather info

Ask the operator:

1. **Realm name** (e.g. `CU`).
2. **KC base URL** (e.g. `https://login.<country>.eregistrations.org`).
3. **`INSTITUTION_GROUP_ID`** — the institutions root group UUID (threaded
   from the prepare-realm phase, or read from bpa-backend's
   `KEYCLOAK_INSTITUTIONS_GROUP_ID` env).
4. **Camunda postgres connection** (`$CAMUNDA_DB_URL` or host + db name for
   `psql`).
5. **KC admin bearer token** (service account or admin — the script only
   reads groups).

## STEP 1: Build the legacy-id → UUID maps from KC

```bash
ADMIN_TOKEN="<service-account bearer token for KC admin REST>"
python rewrite_camunda_role_groups.py \
    --kc-url "https://login.${REALM_NAME,,}.eregistrations.org" \
    --realm  "$REALM_NAME" \
    --root-id "$INSTITUTION_GROUP_ID" \
    --token   "$ADMIN_TOKEN" \
    --out-dir /tmp
```

The script warns (stderr) about any institution/unit group missing its
`partc_institution_id` / `partc_unit_id` attribute — those rows cannot be
translated and mean the seed phase ran with an older SQL template. Resolve
the attributes first (see `cas-to-keycloak-rewrite-bpa-postgres`'s
"Fallback" section — same root cause, same fix).

## STEP 2: Apply the rewrite against Camunda postgres

The `.tpl` needs no substitution — its only `${...}` occurrence sits in a
comment — so staging it is a plain copy:

```bash
cp rewrite_camunda_role_groups.sql.tpl /tmp/rewrite_camunda_role_groups.sql
psql "$CAMUNDA_DB_URL" -f /tmp/rewrite_camunda_role_groups.sql
```

The SQL does, in order:

1. Snapshot existing rows into `ereg_service_role_group__bkp_premigration`
   (timestamped — safe to re-run, each run appends its own snapshot).
2. UPDATE `i<N>[_<role>]` rows → institution KC UUID (role suffix dropped —
   KC has no business-role granularity per institution).
3. UPDATE bare `<N>` and `u<N>[_<role>]` rows → unit KC UUID.
4. Assert no legacy tokens remain — raises (rolling back the transaction)
   if any do.
5. Propagate the OR-collapsed `determinant` onto each duplicate set, then
   deduplicate (multiple `i<N>_<role1>` / `i<N>_<role2>` rows collapse to
   one row pointing at the same UUID).
6. Report final row counts.

## STEP 3: Verify

```sql
-- Should be 0:
SELECT count(*) FROM ereg_service_role_group
 WHERE "group" ~ '^[iu]?[0-9]+(_.+)?$';
```

And end-to-end as a known PartB operator (replace `$JWT` with their token):

```bash
curl -sH "Authorization: Bearer $JWT" \
     "https://${REALM_NAME,,}.eregistrations.org/es/backend/services?isPartB=1&onlyMyRoles=1" \
   | jq length    # > 0 if the user's institution owns at least one service
```

## Rollback (no pg_dump needed)

Restore the earliest snapshot (later snapshots are re-run artefacts of
already-migrated rows):

```sql
BEGIN;
TRUNCATE ereg_service_role_group;
INSERT INTO ereg_service_role_group (service_id, role_id, "group", determinant)
    SELECT service_id, role_id, "group", determinant
      FROM ereg_service_role_group__bkp_premigration
     WHERE backup_ts = (SELECT min(backup_ts)
                          FROM ereg_service_role_group__bkp_premigration);
COMMIT;
```

## Caveats

- **Republished services already use UUIDs.** The script is idempotent — a
  rewrite over rows already containing UUIDs is a no-op.
- **CAS business-role granularity is lost on purpose.** If the destination
  realm needs to distinguish e.g. `i5_manager` from `i5_processing`, the
  business role must be represented as a KC realm role (or sub-group)
  before this phase — and the SQL template extended to map the
  `iN_<role>` suffix to that signal. The default flattening (drop role
  suffix) matches the current ds-backend filter, which only considers
  institution / unit membership.
- **Bare-integer-as-unit-id is a Cuba convention.** Other deployments may
  use `uN` consistently. The SQL handles both shapes; the regex only fires
  on truly bare integers, so the rewrite never misinterprets an
  `applicant` / `super_mario` neighbour.
- **Service-attribute `Draft` regression.** Independent of this skill, BPA's
  publish flow has been observed to leave `[{"attribute":"Draft"}]` on
  ds-backend's `Service.service_attributes` after a republish post-
  migration. This makes the service invisible to non-Draft users via
  `apps/services/views.py:has_service_access`. If you opt to republish
  services post-cutover instead of running this phase, expect to manually
  clear the Draft attribute. The direct rewrite avoids the publish flow and
  therefore avoids this regression.
