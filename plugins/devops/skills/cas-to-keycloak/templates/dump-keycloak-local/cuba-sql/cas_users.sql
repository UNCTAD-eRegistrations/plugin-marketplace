-- Cuba-specific rewrite of cas-to-keycloak/cas_users.sql.
-- Cuba's cas.property IDs differ from El Salvador's: username/email IDs are
-- swapped, and DUI/NIT do not exist (replaced by identification_number at id=16).
-- See cas.property:
--   1  primary_email
--   2  username
--   6  last_name              ("1er Apellido")
--   7  first_name             ("1er Nombre")
--  10  phone
--  16  identification_number  (Cuban "Carné de Identidad")
-- other_names ("2do Nombre") and other_lastname ("2do Apellido") have
-- environment-dependent IDs, so they are looked up by name via subqueries
-- below — see VUCE-36.
SELECT DISTINCT
    up.value  AS username,
    up2.value AS primary_email,
    CASE WHEN v.id IS NOT NULL THEN true ELSE false END AS email_validated,
    up3.value AS first_name,
    up4.value AS "name",
    up8.password AS "password",
    "user".id AS attribute_cas_user_id,
    up5.value AS attribute_phone,
    up6.value AS attribute_identification_number,
    up7.value AS attribute_other_names,
    up9.value AS attribute_other_lastname
FROM cas."user"
    LEFT OUTER JOIN cas.user_property up  ON "user".id = up.user_id  AND up.property_id  = 2  -- username
    LEFT OUTER JOIN cas.user_property up2 ON "user".id = up2.user_id AND up2.property_id = 1  -- primary_email
    LEFT OUTER JOIN cas.user_property up3 ON "user".id = up3.user_id AND up3.property_id = 7  -- first name
    LEFT OUTER JOIN cas.user_property up4 ON "user".id = up4.user_id AND up4.property_id = 6  -- last name
    LEFT OUTER JOIN cas.user_property up5 ON "user".id = up5.user_id AND up5.property_id = 10 -- phone
    LEFT OUTER JOIN cas.user_property up6 ON "user".id = up6.user_id AND up6.property_id = 16 -- identification_number
    LEFT OUTER JOIN cas.user_property up7 ON "user".id = up7.user_id
        AND up7.property_id = (SELECT id FROM cas.property WHERE name = 'other_names')        -- "2do Nombre"     (VUCE-36)
    LEFT OUTER JOIN cas.user_property up9 ON "user".id = up9.user_id
        AND up9.property_id = (SELECT id FROM cas.property WHERE name = 'other_lastname')     -- "2do Apellido"   (VUCE-36)
    LEFT OUTER JOIN cas.user_password up8 ON "user".id = up8.user_id
    LEFT OUTER JOIN cas.verification  v   ON "user".id = v.subject_user_id AND v.property_id = up2.property_id;
