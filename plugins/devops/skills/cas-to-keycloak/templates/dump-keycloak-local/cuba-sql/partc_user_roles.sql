-- Cuba-specific rewrite of cas-to-keycloak/partc_user_roles.sql.
--
-- Surfaces every realm-role assignment in partc, not just a hardcoded handful.
-- The previous version filtered on cas.role-style names ('sysadmin','manager',
-- 'statistic','citizen','bot','external-bot'); since this query reads
-- partc.role, only the three names that happen to overlap survived
-- ('sysadmin','citizen','bot'), silently dropping every Cuba-specific admin
-- role and the partb/Draft/super_mario/superinspector/statistic family.
--
-- Strategy now:
--   * Every partc.role row, minus BPA and TUTORIAL (handled below as
--     bpa-frontend / bpa-backend client roles for backwards compat), is
--     surfaced as a realm role.
--   * Name normalisation:
--       statistics            -> statistic           (realm has singular)
--       TRANSLATION_MANAGER   -> translation_manager (realm has lowercase)
--       GLOBAL_TRANSLATOR     -> global_translator
--       LOCAL_TRANSLATOR      -> local_translator
--   * Roles that don't exist as realm roles yet (VUCE, FITO, RCP, INHEM,
--     ONURE, ZOO, RCENASA, ORSA, ONN, FARMYOPT, CERTSAN, CECMED) are emitted
--     under their partc names; the migrator wrapper creates any missing realm
--     role on the fly before assignment, and keycloak-realm.json now declares
--     them too so a fresh realm import has them out of the box.
--   * BPA / TUTORIAL client-role UNIONs are kept verbatim from the previous
--     version so existing behaviour (BPA -> bpa-frontend+bpa-backend for
--     non-sysadmin users, TUTORIAL -> bpa-frontend for everyone) is preserved
--     even though BPA services aren't deployed in Cuba's stack.
SELECT u.cas_id AS attribute_cas_user_id,
       CASE r.role_name
           WHEN 'statistics'           THEN 'statistic'
           WHEN 'TRANSLATION_MANAGER'  THEN 'translation_manager'
           WHEN 'GLOBAL_TRANSLATOR'    THEN 'global_translator'
           WHEN 'LOCAL_TRANSLATOR'     THEN 'local_translator'
           ELSE r.role_name
       END AS role_name,
       true AS realm_role,
       null AS client
FROM partc."user" u
         INNER JOIN partc.user_role ur ON (ur.user_id = u.id)
         INNER JOIN partc."role" r ON (ur.role_id = r.id)
WHERE r.role_name NOT IN ('BPA', 'TUTORIAL')
UNION
SELECT u.cas_id AS attribute_cas_user_id, r.role_name, false AS realm_role, 'bpa-frontend' AS client
FROM partc."user" u
         INNER JOIN partc.user_role ur ON (ur.user_id = u.id)
         INNER JOIN partc."role" r ON (ur.role_id = r.id)
WHERE (r.role_name = 'BPA'
  AND u.cas_id NOT IN (SELECT DISTINCT u.cas_id
                       FROM partc."user" u
                                INNER JOIN partc.user_role ur ON (ur.user_id = u.id)
                                INNER JOIN partc."role" r ON (ur.role_id = r.id)
                       WHERE r.role_name = 'sysadmin'))
  OR r.role_name = 'TUTORIAL'
UNION
SELECT u.cas_id AS attribute_cas_user_id, r.role_name, false AS realm_role, 'bpa-backend' AS client
FROM partc."user" u
         INNER JOIN partc.user_role ur ON (ur.user_id = u.id)
         INNER JOIN partc."role" r ON (ur.role_id = r.id)
WHERE r.role_name IN ('BPA')
  AND u.cas_id NOT IN (SELECT DISTINCT u.cas_id
                       FROM partc."user" u
                                INNER JOIN partc.user_role ur ON (ur.user_id = u.id)
                                INNER JOIN partc."role" r ON (ur.role_id = r.id)
                       WHERE r.role_name = 'sysadmin');
