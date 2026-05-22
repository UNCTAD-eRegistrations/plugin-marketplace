-- Surface cas.user_role assignments as realm roles.
--
-- partc.user_role is the primary source for role mappings, but Cuba's CAS dump
-- carries a handful of assignments that don't have a partc-side counterpart
-- (notably `manager`, which doesn't exist in partc.role at all). Without this
-- query those users would lose the role on migration.
--
-- cas.role names match Keycloak realm roles directly, so no name normalisation
-- is needed. extract.sh merges this output with partc_user_roles.json and
-- dedupes (attribute_cas_user_id, role_name, realm_role, client) before
-- writing user-roles.json.
SELECT u.id AS attribute_cas_user_id, r.role_name, true AS realm_role, null AS client
FROM cas."user" u
         INNER JOIN cas.user_role ur ON (ur.user_id = u.id)
         INNER JOIN cas."role" r ON (ur.role_id = r.id);
