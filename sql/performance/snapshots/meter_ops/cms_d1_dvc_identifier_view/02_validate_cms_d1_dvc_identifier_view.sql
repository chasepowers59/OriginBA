-- Validate CISADM.CMS_D1_DVC_IDENTIFIER_VW after create.

SELECT owner, object_name, object_type, status
FROM all_objects
WHERE object_name = 'CMS_D1_DVC_IDENTIFIER_VW'
ORDER BY owner, object_type;

SELECT owner, synonym_name, table_owner, table_name
FROM all_synonyms
WHERE synonym_name = 'CMS_D1_DVC_IDENTIFIER_VW'
ORDER BY owner;

SELECT COUNT(*) AS cisadm_rows
FROM cisadm.cms_d1_dvc_identifier_vw;

SELECT COUNT(*) AS cisread_rows
FROM cisread.cms_d1_dvc_identifier_vw;

-- Domain join smoke: device -> identifier overlay
SELECT COUNT(*) AS devices_with_identifier_overlay
FROM cisadm.d1_dvc d
INNER JOIN cisadm.cms_d1_dvc_identifier_vw v
    ON v.d1_device_id = d.d1_device_id;
