-- Install gate: domain support objects (CMS views + CMS_SA_SNAPSHOT).
-- Returns rows only on failure (empty result set = pass).
-- Run after 04c_validate_all_domain_support_objects.sql for automated pass/fail signaling.

SELECT 'CMS_SA_SNAPSHOT',
       'MISSING_OR_INVALID_OBJECT',
       'expected CISADM table/procedure not VALID'
FROM dual
WHERE EXISTS (
    SELECT 1
    FROM all_objects
    WHERE owner = 'CISADM'
      AND object_name IN ('CMS_SA_SNAPSHOT', 'REFRESH_CMS_SA_SNAPSHOT')
      AND status <> 'VALID'
)
   OR NOT EXISTS (
    SELECT 1
    FROM all_objects
    WHERE owner = 'CISADM'
      AND object_name = 'CMS_SA_SNAPSHOT'
      AND object_type = 'TABLE'
      AND status = 'VALID'
)
   OR NOT EXISTS (
    SELECT 1
    FROM all_objects
    WHERE owner = 'CISADM'
      AND object_name = 'REFRESH_CMS_SA_SNAPSHOT'
      AND object_type IN ('PROCEDURE', 'FUNCTION')
      AND status = 'VALID'
)

UNION ALL

SELECT 'CMS_SA_SNAPSHOT',
       'MISSING_CISREAD_SYNONYM',
       'CISREAD.CMS_SA_SNAPSHOT synonym missing or not pointing at CISADM'
FROM dual
WHERE NOT EXISTS (
    SELECT 1
    FROM all_synonyms
    WHERE owner = 'CISREAD'
      AND synonym_name = 'CMS_SA_SNAPSHOT'
      AND table_owner = 'CISADM'
      AND table_name = 'CMS_SA_SNAPSHOT'
)

UNION ALL

SELECT 'CMS_SA_SNAPSHOT',
       'EMPTY_TABLE',
       'Snapshot has zero rows after refresh'
FROM dual
WHERE (SELECT COUNT(*) FROM cisadm.cms_sa_snapshot) = 0

UNION ALL

SELECT 'CMS_SA_SNAPSHOT',
       'MISSING_LDAY_SLICE',
       'No LDAY rows present after refresh'
FROM dual
WHERE (SELECT COUNT(*) FROM cisadm.cms_sa_snapshot WHERE cm_snapshot_type_flg = 'LDAY') = 0

UNION ALL

SELECT 'CMS_SA_SNAPSHOT',
       'DUPLICATE_GRAIN',
       'duplicate_sa_id_groups=' || TO_CHAR(COUNT(*))
FROM (
    SELECT sa_id
    FROM cisadm.cms_sa_snapshot
    WHERE cm_snapshot_type_flg = 'LDAY'
    GROUP BY sa_id
    HAVING COUNT(*) > 1
)
HAVING COUNT(*) > 0

UNION ALL

SELECT 'CMS_SA_SNAPSHOT',
       'BUCKET_SUM_GAP',
       'gap_rows=' || TO_CHAR(COUNT(*))
FROM (
    SELECT sa_id
    FROM cisadm.cms_sa_snapshot
    WHERE cm_snapshot_type_flg = 'LDAY'
      AND ABS(
            NVL(cur_bal, 0)
            - (
                NVL(ars_amt1, 0) + NVL(ars_amt2, 0) + NVL(ars_amt3, 0)
                + NVL(ars_amt4, 0) + NVL(ars_amt5, 0)
              )
          ) > 0.01
)
HAVING COUNT(*) > 0

UNION ALL

SELECT 'CMS_SA_SNAPSHOT',
       'CUR_BAL_FT_PARITY_GAP',
       'delta=' || TO_CHAR(ABS(snap_cur_bal - ft_cur_bal))
FROM (
    SELECT
        (SELECT SUM(cur_bal)
         FROM cisadm.cms_sa_snapshot
         WHERE cm_snapshot_type_flg = 'LDAY') AS snap_cur_bal,
        (SELECT SUM(ft.cur_amt)
         FROM cisadm.ci_ft ft
         WHERE ft.freeze_sw = 'Y'
           AND ft.not_in_ars_sw = 'N'
           AND ft.ars_dt IS NOT NULL
           AND TRUNC(ft.ars_dt) <= TRUNC(SYSDATE)) AS ft_cur_bal
    FROM dual
)
WHERE ABS(NVL(snap_cur_bal, 0) - NVL(ft_cur_bal, 0)) > 0.01

UNION ALL

SELECT view_name,
       'MISSING_OR_INVALID_VIEW',
       'expected CISADM view not VALID'
FROM (
    SELECT 'CMS_D1_DVC_IDENTIFIER_VW' AS view_name FROM dual
    UNION ALL SELECT 'CMS_D1_DVC_BODA_VW' FROM dual
    UNION ALL SELECT 'CMS_W1_ASSET_IDENTIFIER_VW' FROM dual
    UNION ALL SELECT 'CMS_C1_REPRESENTATIVE_BODA_VW' FROM dual
    UNION ALL SELECT 'CMS_D1_ACTIVITY_CHAR_VW' FROM dual
    UNION ALL SELECT 'CMS_D1_ACTIVITY_D1FA_BODA_VW' FROM dual
) expected
WHERE NOT EXISTS (
    SELECT 1
    FROM all_objects o
    WHERE o.owner = 'CISADM'
      AND o.object_name = expected.view_name
      AND o.object_type = 'VIEW'
      AND o.status = 'VALID'
)

UNION ALL

SELECT synonym_name,
       'MISSING_CISREAD_SYNONYM',
       'CISREAD synonym missing or not pointing at CISADM view'
FROM (
    SELECT 'CMS_D1_DVC_IDENTIFIER_VW' AS synonym_name FROM dual
    UNION ALL SELECT 'CMS_D1_DVC_BODA_VW' FROM dual
    UNION ALL SELECT 'CMS_W1_ASSET_IDENTIFIER_VW' FROM dual
    UNION ALL SELECT 'CMS_C1_REPRESENTATIVE_BODA_VW' FROM dual
    UNION ALL SELECT 'CMS_D1_ACTIVITY_CHAR_VW' FROM dual
    UNION ALL SELECT 'CMS_D1_ACTIVITY_D1FA_BODA_VW' FROM dual
) expected
WHERE NOT EXISTS (
    SELECT 1
    FROM all_synonyms s
    WHERE s.owner = 'CISREAD'
      AND s.synonym_name = expected.synonym_name
      AND s.table_owner = 'CISADM'
      AND s.table_name = expected.synonym_name
)
