-- Cuba's partc.institution_unit schema matches; schema prefix added.
-- Alias `ui.id` as `attribute_partc_unit_id` (not the longer-form
-- `attribute_partc_institution_unit_id`) so the migrator stamps KC subgroup
-- attributes with the canonical key `partc_unit_id` — analogous to
-- `partc_institution_id` on parent institution groups. Legacy migrations
-- (pre-rename) carry `partc_institution_unit_id` instead; the downstream
-- `cas-to-keycloak-rewrite-bpa-postgres` skill reads either key.
SELECT
    ui.id              AS attribute_partc_unit_id,
    ui.institution_id  AS attribute_partc_institution_id,
    ui.name,
    ui.url             AS attribute_url
FROM
    partc.institution_unit ui;
