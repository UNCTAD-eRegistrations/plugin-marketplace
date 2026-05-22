-- Cuba's partc.user_bus_role_institution(_unit) schema matches; schema prefix added.
SELECT
    DISTINCT u.cas_id AS attribute_cas_user_id, i.institution_id, CAST(null AS int) AS institution_unit_id
FROM
    partc.user_bus_role_institution i
    INNER JOIN partc."user" u ON i.user_id = u.id
UNION
SELECT
    DISTINCT u.cas_id AS attribute_cas_user_id, CAST(null AS int) AS institution_id, iu.institution_unit_id
FROM
    partc.user_bus_role_institution_unit iu
    INNER JOIN partc."user" u ON iu.user_id = u.id;
