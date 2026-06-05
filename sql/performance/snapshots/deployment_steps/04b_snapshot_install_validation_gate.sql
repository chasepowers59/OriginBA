-- Install gate: post-load sanity for all 7 active snapshots.
-- Returns rows only on failure (empty result set = pass).
-- Run after 04_validate_all_active_snapshots.sql for automated pass/fail signaling.

SELECT 'FT_RPT_CURR' AS snapshot_name,
       'EMPTY_TABLE' AS failure_code,
       'Snapshot has zero rows after install' AS detail
FROM dual
WHERE (SELECT COUNT(*) FROM cisadm.ft_rpt_curr) = 0

UNION ALL

SELECT 'FT_RPT_CURR',
       'DUPLICATE_GRAIN',
       'duplicate_ft_id_groups=' || TO_CHAR(COUNT(*))
FROM (
    SELECT ft_id
    FROM cisadm.ft_rpt_curr
    GROUP BY ft_id
    HAVING COUNT(*) > 1
)

UNION ALL

SELECT 'BSEG_BILLED_USAGE_RPT_CURR',
       'EMPTY_TABLE',
       'Snapshot has zero rows after install'
FROM dual
WHERE (SELECT COUNT(*) FROM cisadm.bseg_billed_usage_rpt_curr) = 0

UNION ALL

SELECT 'BSEG_BILLED_USAGE_RPT_CURR',
       'DUPLICATE_GRAIN',
       'duplicate_bseg_id_groups=' || TO_CHAR(COUNT(*))
FROM (
    SELECT bseg_id
    FROM cisadm.bseg_billed_usage_rpt_curr
    GROUP BY bseg_id
    HAVING COUNT(*) > 1
)

UNION ALL

SELECT 'BSEG_SQ_USAGE_RPT_CURR',
       'EMPTY_TABLE',
       'Snapshot has zero rows after install'
FROM dual
WHERE (SELECT COUNT(*) FROM cisadm.bseg_sq_usage_rpt_curr) = 0

UNION ALL

SELECT 'BSEG_SQ_USAGE_RPT_CURR',
       'DUPLICATE_GRAIN',
       'duplicate_determinant_groups=' || TO_CHAR(COUNT(*))
FROM (
    SELECT bseg_id, uom_cd, tou_cd, sqi_cd
    FROM cisadm.bseg_sq_usage_rpt_curr
    GROUP BY bseg_id, uom_cd, tou_cd, sqi_cd
    HAVING COUNT(*) > 1
)

UNION ALL

SELECT 'D1_MSRMT_RPT_CURR',
       'EMPTY_TABLE',
       'Snapshot has zero rows after install'
FROM dual
WHERE (SELECT COUNT(*) FROM cisadm.d1_msrmt_rpt_curr) = 0

UNION ALL

SELECT 'D1_MSRMT_RPT_CURR',
       'DUPLICATE_GRAIN',
       'duplicate_measr_comp_dttm_groups=' || TO_CHAR(COUNT(*))
FROM (
    SELECT measr_comp_id, msrmt_dttm
    FROM cisadm.d1_msrmt_rpt_curr
    GROUP BY measr_comp_id, msrmt_dttm
    HAVING COUNT(*) > 1
)

UNION ALL

SELECT 'FT_GL_DISTRIBUTION_RPT_CURR',
       'EMPTY_TABLE',
       'Snapshot has zero rows after install'
FROM dual
WHERE (SELECT COUNT(*) FROM cisadm.ft_gl_distribution_rpt_curr) = 0

UNION ALL

SELECT 'FT_GL_DISTRIBUTION_RPT_CURR',
       'DUPLICATE_GRAIN',
       'duplicate_ft_gl_seq_groups=' || TO_CHAR(COUNT(*))
FROM (
    SELECT ft_id, gl_seq_nbr
    FROM cisadm.ft_gl_distribution_rpt_curr
    GROUP BY ft_id, gl_seq_nbr
    HAVING COUNT(*) > 1
)

UNION ALL

SELECT 'D1_USAGE_RPT_CURR',
       'EMPTY_TABLE',
       'Snapshot has zero rows after install'
FROM dual
WHERE (SELECT COUNT(*) FROM cisadm.d1_usage_rpt_curr) = 0

UNION ALL

SELECT 'D1_USAGE_RPT_CURR',
       'DUPLICATE_GRAIN',
       'duplicate_d1_usage_id_groups=' || TO_CHAR(COUNT(*))
FROM (
    SELECT d1_usage_id
    FROM cisadm.d1_usage_rpt_curr
    GROUP BY d1_usage_id
    HAVING COUNT(*) > 1
)

UNION ALL

SELECT 'D1_USAGE_SCALAR_DTL_RPT_CURR',
       'EMPTY_TABLE',
       'Snapshot has zero rows after install'
FROM dual
WHERE (SELECT COUNT(*) FROM cisadm.d1_usage_scalar_dtl_rpt_curr) = 0

UNION ALL

SELECT 'D1_USAGE_SCALAR_DTL_RPT_CURR',
       'DUPLICATE_GRAIN',
       'duplicate_usage_seq_groups=' || TO_CHAR(COUNT(*))
FROM (
    SELECT d1_usage_id, seq_num
    FROM cisadm.d1_usage_scalar_dtl_rpt_curr
    GROUP BY d1_usage_id, seq_num
    HAVING COUNT(*) > 1
)
