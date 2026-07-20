-- Validate CISADM.CMS_W1_ASSET_IDENTIFIER_VW after create.

SELECT owner, object_name, object_type, status
FROM all_objects
WHERE object_name = 'CMS_W1_ASSET_IDENTIFIER_VW'
ORDER BY owner, object_type;

SELECT owner, synonym_name, table_owner, table_name
FROM all_synonyms
WHERE synonym_name = 'CMS_W1_ASSET_IDENTIFIER_VW'
ORDER BY owner;

SELECT COUNT(*) AS cisadm_rows
FROM cisadm.cms_w1_asset_identifier_vw;

SELECT COUNT(*) AS cisread_rows
FROM cisread.cms_w1_asset_identifier_vw;

-- Domain join smoke: asset -> identifier overlay
SELECT COUNT(*) AS assets_with_identifier_overlay
FROM cisadm.w1_asset a
INNER JOIN cisadm.cms_w1_asset_identifier_vw v
    ON v.asset_id = a.asset_id;
