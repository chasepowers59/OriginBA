-- Compare source max string lengths for volatile fields before refresh.
-- Use this if another ORA-12899 appears and you want to identify the next candidate quickly.

SELECT 'D1_USAGE.USG_EXT_ID' AS source_column, MAX(LENGTH(usg_ext_id)) AS max_length
FROM cisadm.d1_usage
UNION ALL
SELECT 'D1_USAGE.ORG_USAGE_ID', MAX(LENGTH(org_usage_id))
FROM cisadm.d1_usage
UNION ALL
SELECT 'CMS_D1_USAGE_BODA_VW.D2_SKIP_REASON_FLG', MAX(LENGTH(d2_skip_reason_flg))
FROM cisadm.cms_d1_usage_boda_vw
UNION ALL
SELECT 'CMS_D1_USAGE_BODA_VW.DATE_BREAK', MAX(LENGTH(date_break))
FROM cisadm.cms_d1_usage_boda_vw
UNION ALL
SELECT 'CMS_D1_USAGE_BODA_VW.PROFILE_FACTOR_CD', MAX(LENGTH(profile_factor_cd))
FROM cisadm.cms_d1_usage_boda_vw
UNION ALL
SELECT 'CMS_D1_USAGE_BODA_VW.FACTOR_CHAR_VALUE', MAX(LENGTH(factor_char_value))
FROM cisadm.cms_d1_usage_boda_vw
UNION ALL
SELECT 'CMS_D1_USAGE_BODA_VW.SCALAR_MIN_OFFSET_DAYS', MAX(LENGTH(scalar_min_offset_days))
FROM cisadm.cms_d1_usage_boda_vw
UNION ALL
SELECT 'CMS_D1_USAGE_BODA_VW.SCALAR_MAX_OFFSET_DAYS', MAX(LENGTH(scalar_max_offset_days))
FROM cisadm.cms_d1_usage_boda_vw
ORDER BY
    max_length DESC NULLS LAST,
    source_column;
