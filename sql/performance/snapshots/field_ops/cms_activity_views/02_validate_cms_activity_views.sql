-- Validate CISADM CMS Field Activity views after create.

SELECT owner, object_name, object_type, status
FROM all_objects
WHERE object_name IN (
    'CMS_C1_REPRESENTATIVE_BODA_VW',
    'CMS_D1_ACTIVITY_CHAR_VW',
    'CMS_D1_ACTIVITY_D1FA_BODA_VW'
)
ORDER BY object_name, owner;

SELECT owner, synonym_name, table_owner, table_name
FROM all_synonyms
WHERE synonym_name IN (
    'CMS_C1_REPRESENTATIVE_BODA_VW',
    'CMS_D1_ACTIVITY_CHAR_VW',
    'CMS_D1_ACTIVITY_D1FA_BODA_VW'
)
ORDER BY synonym_name, owner;

SELECT 'CMS_C1_REPRESENTATIVE_BODA_VW' AS view_name, COUNT(*) AS row_cnt
FROM cisadm.cms_c1_representative_boda_vw
UNION ALL
SELECT 'CMS_D1_ACTIVITY_CHAR_VW', COUNT(*)
FROM cisadm.cms_d1_activity_char_vw
UNION ALL
SELECT 'CMS_D1_ACTIVITY_D1FA_BODA_VW', COUNT(*)
FROM cisadm.cms_d1_activity_d1fa_boda_vw;

SELECT 'CISREAD.CMS_C1_REPRESENTATIVE_BODA_VW' AS access_path, COUNT(*) AS row_cnt
FROM cisread.cms_c1_representative_boda_vw
UNION ALL
SELECT 'CISREAD.CMS_D1_ACTIVITY_CHAR_VW', COUNT(*)
FROM cisread.cms_d1_activity_char_vw
UNION ALL
SELECT 'CISREAD.CMS_D1_ACTIVITY_D1FA_BODA_VW', COUNT(*)
FROM cisread.cms_d1_activity_d1fa_boda_vw;

-- Domain join smoke: D1FA activity -> BO enrichment
SELECT COUNT(*) AS d1fa_with_boda
FROM cisadm.d1_activity act
INNER JOIN cisadm.cms_d1_activity_d1fa_boda_vw boda
    ON boda.d1_activity_id = act.d1_activity_id;
