SELECT
    probe_name,
    bill_cycle_code,
    row_count,
    mismatch_count
FROM (
    SELECT
        'BILL_TO_ACCOUNT' AS probe_name,
        NULLIF(TRIM(NVL(b.bill_cyc_cd, ac.bill_cyc_cd)), '') AS bill_cycle_code,
        COUNT(*) AS row_count,
        SUM(
            CASE
                WHEN NULLIF(TRIM(b.bill_cyc_cd), '') IS NOT NULL
                 AND NULLIF(TRIM(ac.bill_cyc_cd), '') IS NOT NULL
                 AND TRIM(b.bill_cyc_cd) <> TRIM(ac.bill_cyc_cd)
                THEN 1
                ELSE 0
            END
        ) AS mismatch_count
    FROM cisadm.ci_bill b
    LEFT JOIN cisadm.ci_acct ac
        ON ac.acct_id = b.acct_id
    WHERE NVL(b.bill_dt, b.cre_dttm) >= ADD_MONTHS(TRUNC(SYSDATE), -18)
      AND NVL(b.bill_dt, b.cre_dttm) < TRUNC(SYSDATE) + 1
      AND NULLIF(TRIM(NVL(b.bill_cyc_cd, ac.bill_cyc_cd)), '') IS NOT NULL
    GROUP BY NULLIF(TRIM(NVL(b.bill_cyc_cd, ac.bill_cyc_cd)), '')

    UNION ALL

    SELECT
        'BSEG_TO_BILL' AS probe_name,
        NULLIF(TRIM(NVL(s.bill_cyc_cd, b.bill_cyc_cd)), '') AS bill_cycle_code,
        COUNT(*) AS row_count,
        SUM(
            CASE
                WHEN NULLIF(TRIM(s.bill_cyc_cd), '') IS NOT NULL
                 AND NULLIF(TRIM(b.bill_cyc_cd), '') IS NOT NULL
                 AND TRIM(s.bill_cyc_cd) <> TRIM(b.bill_cyc_cd)
                THEN 1
                ELSE 0
            END
        ) AS mismatch_count
    FROM cisadm.ci_bseg s
    LEFT JOIN cisadm.ci_bill b
        ON b.bill_id = s.bill_id
    WHERE NVL(b.bill_dt, s.cre_dttm) >= ADD_MONTHS(TRUNC(SYSDATE), -18)
      AND NVL(b.bill_dt, s.cre_dttm) < TRUNC(SYSDATE) + 1
      AND NULLIF(TRIM(NVL(s.bill_cyc_cd, b.bill_cyc_cd)), '') IS NOT NULL
    GROUP BY NULLIF(TRIM(NVL(s.bill_cyc_cd, b.bill_cyc_cd)), '')
)
ORDER BY mismatch_count DESC, row_count DESC, probe_name, bill_cycle_code;
