-- rewrite_camunda_role_groups.sql.tpl
--
-- Translates legacy CAS-style tokens in Camunda's `ereg_service_role_group`
-- table to the KC group UUIDs created by the migrator. Run AFTER the migrator
-- has produced the enriched KC dump and AFTER the new KC realm is in place,
-- but BEFORE the deployment goes live so the institution filter in ds-backend
-- (apps/utilities/institution_permissions.py) can match user group UUIDs.
--
-- Preconditions for this script to be self-sufficient:
--   1. Every KC institution group has a `partc_institution_id` attribute
--      whose value is the legacy PARTC integer id (string).
--   2. Every KC institution-unit group has a `partc_unit_id` attribute
--      whose value is the legacy PARTC integer id (string).
--   Both invariants are upheld by the migrator's group-creation step — confirm
--   on the target KC realm with:
--     SELECT g.name, a.name, a.value
--     FROM keycloak_group g JOIN group_attribute a ON a.group_id = g.id
--     WHERE a.name IN ('partc_institution_id','partc_unit_id') ORDER BY g.name;
--
-- This script is parameterised at the database level: it reads the KC
-- mapping from the KC postgres database via a foreign-data-wrapper or
-- (recommended) a CSV staged into a temp table before running. The CSV
-- approach is portable and used below.
--
-- Inputs (CSV files staged into temp tables):
--   /tmp/inst_map.csv  — header: partc_id,kc_group_id   (institution rows)
--   /tmp/unit_map.csv  — header: partc_id,kc_group_id   (unit rows)
--
-- The CSV files are produced by `rewrite_camunda_role_groups.py` (see
-- companion script) which queries the live KC admin API for the
-- institutions tree under ${INSTITUTION_GROUP_ID} and emits both maps.

BEGIN;

-- Defensive snapshot so the operator can roll back without pg_dump.
CREATE TABLE IF NOT EXISTS ereg_service_role_group__bkp_premigration
    AS SELECT *, now() AS backup_ts FROM ereg_service_role_group WITH NO DATA;
INSERT INTO ereg_service_role_group__bkp_premigration
    SELECT *, now() FROM ereg_service_role_group;

-- Stage maps. Replace COPY paths with whatever your loader uses.
CREATE TEMP TABLE _inst_map (partc_id int PRIMARY KEY, kc_group_id text NOT NULL);
CREATE TEMP TABLE _unit_map (partc_id int PRIMARY KEY, kc_group_id text NOT NULL);
\copy _inst_map FROM '/tmp/inst_map.csv' WITH (FORMAT csv, HEADER true);
\copy _unit_map FROM '/tmp/unit_map.csv' WITH (FORMAT csv, HEADER true);

-- 1) Translate i<N>[_<role>] tokens to the institution UUID.
UPDATE ereg_service_role_group r
   SET "group" = m.kc_group_id
  FROM _inst_map m
 WHERE r."group" ~ '^i[0-9]+(_.+)?$'
   AND m.partc_id = ((regexp_match(r."group",'^i([0-9]+)'))[1])::int;

-- 2) Translate bare <N> tokens (Cuba convention: bare-int = unit_id) and
--    explicit u<N>[_<role>] tokens to the unit UUID.
UPDATE ereg_service_role_group r
   SET "group" = m.kc_group_id
  FROM _unit_map m
 WHERE (r."group" ~ '^[0-9]+$' OR r."group" ~ '^u[0-9]+(_.+)?$')
   AND m.partc_id = ((regexp_match(r."group",'^u?([0-9]+)'))[1])::int;

-- 3) Verify: should be zero rows after the two UPDATEs above.
DO $$
DECLARE n int;
BEGIN
    SELECT count(*) INTO n FROM ereg_service_role_group
     WHERE "group" ~ '^[iu]?[0-9]+(_.+)?$';
    IF n > 0 THEN
        RAISE EXCEPTION 'Untranslated legacy tokens remain: %', n;
    END IF;
END $$;

-- 4) Dedupe — multiple i<N>_<role> rows collapsed to the same UUID.
--    Keep one row per (service_id, role_id, group) tuple. `determinant` is
--    OR-collapsed because the original CAS-flavoured rows could differ
--    only on that flag for the same business meaning.
--    First propagate the OR-ed determinant onto every row of each duplicate
--    set (so the survivor carries it), then delete the extras.
WITH agg AS (
    SELECT service_id, role_id, "group",
           bool_or(determinant) AS determinant
      FROM ereg_service_role_group
     GROUP BY service_id, role_id, "group"
    HAVING count(*) > 1
)
UPDATE ereg_service_role_group r
   SET determinant = a.determinant
  FROM agg a
 WHERE r.service_id = a.service_id
   AND r.role_id   = a.role_id
   AND r."group"   = a."group"
   AND r.determinant IS DISTINCT FROM a.determinant;

WITH dedup AS (
    SELECT service_id, role_id, "group",
           min(ctid) AS keep_ctid
      FROM ereg_service_role_group
     GROUP BY service_id, role_id, "group"
    HAVING count(*) > 1
)
DELETE FROM ereg_service_role_group r
 USING dedup d
 WHERE r.service_id = d.service_id
   AND r.role_id   = d.role_id
   AND r."group"   = d."group"
   AND r.ctid     <> d.keep_ctid;

-- 5) Final sanity: report how many rows survived.
DO $$
DECLARE n int; legacy int; uuids int;
BEGIN
    SELECT count(*) INTO n      FROM ereg_service_role_group;
    SELECT count(*) INTO legacy FROM ereg_service_role_group
        WHERE "group" ~ '^[iu]?[0-9]+(_.+)?$';
    SELECT count(*) INTO uuids  FROM ereg_service_role_group
        WHERE "group" ~ '^[0-9a-f]{8}-';
    RAISE NOTICE 'ereg_service_role_group rows: % (legacy=% uuids=%)', n, legacy, uuids;
END $$;

COMMIT;
