-- Cuba's partc.institution schema matches cas-to-keycloak's El Salvador
-- version; only the schema prefix is added.
SELECT
    i.id        AS attribute_partc_institution_id,
    i.name,
    i.short_name AS attribute_short_name,
    i.url        AS attribute_url
FROM
    partc.institution i;
