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

-- Translate every row into its target group in ONE pass, then atomically
-- replace the table. Doing the UPDATEs in place first (as an earlier version
-- did) violates the (service_id, role_id, "group") primary key mid-statement:
-- when a service-role carries both `i5` and `i5_manager`, both map to the same
-- institution UUID, and the first row's UPDATE collides with the second before
-- the later dedup step can run. Verified on dev.cuba (55 such collapses):
--   ERROR: duplicate key value violates unique constraint
--          "ereg_service_role_group_pkey"
-- Computing the new value into a staging table and rewriting via
-- INSERT ... GROUP BY collapses duplicates in the same statement, so the PK is
-- never transiently violated and `determinant` is OR-collapsed for free.

-- 1) Compute the target group per row. Magic tokens (applicant, super_mario)
--    and rows already holding a UUID fall through the CASE unchanged.
CREATE TEMP TABLE _new AS
SELECT r.service_id, r.role_id,
       CASE
         WHEN r."group" ~ '^i[0-9]+(_.+)?$'
           THEN COALESCE(im.kc_group_id, r."group")
         WHEN r."group" ~ '^[0-9]+$' OR r."group" ~ '^u[0-9]+(_.+)?$'
           THEN COALESCE(um.kc_group_id, r."group")
         ELSE r."group"
       END AS new_group,
       r.determinant
FROM ereg_service_role_group r
LEFT JOIN _inst_map im
       ON r."group" ~ '^i[0-9]+(_.+)?$'
      AND im.partc_id = ((regexp_match(r."group",'^i([0-9]+)'))[1])::int
LEFT JOIN _unit_map um
       ON (r."group" ~ '^[0-9]+$' OR r."group" ~ '^u[0-9]+(_.+)?$')
      AND um.partc_id = ((regexp_match(r."group",'^u?([0-9]+)'))[1])::int;

-- 2) Verify every legacy token translated (an untranslated one means the KC
--    group for that partc id is missing its attribute — an orphan). Raise so
--    the transaction rolls back rather than shipping a half-mapped table.
DO $$
DECLARE n int;
BEGIN
    SELECT count(*) INTO n FROM _new WHERE new_group ~ '^[iu]?[0-9]+(_.+)?$';
    IF n > 0 THEN
        RAISE EXCEPTION 'Untranslated legacy tokens remain: %', n;
    END IF;
END $$;

-- 3) Atomic replace. GROUP BY collapses the (service_id, role_id, group)
--    duplicates that the token→UUID mapping creates, OR-ing determinant.
TRUNCATE ereg_service_role_group;
INSERT INTO ereg_service_role_group (service_id, role_id, "group", determinant)
SELECT service_id, role_id, new_group, bool_or(determinant)
  FROM _new
 GROUP BY service_id, role_id, new_group;

-- 4) Final sanity: report how many rows survived.
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
