-- Cuba's partc.institution_unit schema matches; schema prefix added.
SELECT
    ui.id              AS attribute_partc_institution_unit_id,
    ui.institution_id  AS attribute_partc_institution_id,
    ui.name,
    ui.url             AS attribute_url
FROM
    partc.institution_unit ui;
