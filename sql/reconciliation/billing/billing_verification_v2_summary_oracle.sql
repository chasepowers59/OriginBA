WITH cycle_last_event AS (
    SELECT
        x.bill_cycle_code,
        MAX(x.event_date) AS cycle_last_event_date
    FROM (
        SELECT
            NULLIF(TRIM(NVL(b.bill_cyc_cd, ac.bill_cyc_cd)), '') AS bill_cycle_code,
            TRUNC(NVL(b.bill_dt, b.cre_dttm)) AS event_date
        FROM cisadm.ci_bill b
        LEFT JOIN cisadm.ci_acct ac
            ON ac.acct_id = b.acct_id
        WHERE NULLIF(TRIM(NVL(b.bill_cyc_cd, ac.bill_cyc_cd)), '') IS NOT NULL
          AND NVL(b.bill_dt, b.cre_dttm) >= ADD_MONTHS(TRUNC(SYSDATE), -18)
          AND NVL(b.bill_dt, b.cre_dttm) < TRUNC(SYSDATE) + 1

        UNION ALL

        SELECT
            NULLIF(TRIM(NVL(s.bill_cyc_cd, NVL(b.bill_cyc_cd, ac.bill_cyc_cd))), '') AS bill_cycle_code,
            TRUNC(NVL(b.bill_dt, s.cre_dttm)) AS event_date
        FROM cisadm.ci_bseg s
        LEFT JOIN cisadm.ci_bill b
            ON b.bill_id = s.bill_id
        LEFT JOIN cisadm.ci_sa sa
            ON sa.sa_id = s.sa_id
        LEFT JOIN cisadm.ci_acct ac
            ON ac.acct_id = NVL(b.acct_id, sa.acct_id)
        WHERE NULLIF(TRIM(NVL(s.bill_cyc_cd, NVL(b.bill_cyc_cd, ac.bill_cyc_cd))), '') IS NOT NULL
          AND NVL(b.bill_dt, s.cre_dttm) >= ADD_MONTHS(TRUNC(SYSDATE), -18)
          AND NVL(b.bill_dt, s.cre_dttm) < TRUNC(SYSDATE) + 1
    ) x
    GROUP BY x.bill_cycle_code
),
expected_active AS (
    SELECT
        NULLIF(TRIM(ac.bill_cyc_cd), '') AS bill_cycle_code,
        COUNT(DISTINCT sa.sa_id) AS expected_active_sa_count,
        COUNT(DISTINCT sa.acct_id) AS expected_active_account_count
    FROM cisadm.ci_sa sa
    JOIN cisadm.ci_acct ac
        ON ac.acct_id = sa.acct_id
    WHERE TRIM(sa.sa_status_flg) = '20'
      AND NULLIF(TRIM(ac.bill_cyc_cd), '') IS NOT NULL
    GROUP BY NULLIF(TRIM(ac.bill_cyc_cd), '')
),
latest_bill_headers AS (
    SELECT
        cle.bill_cycle_code,
        b.acct_id,
        b.bill_id,
        b.bill_stat_flg,
        TRUNC(b.bill_dt) AS bill_date,
        TRUNC(b.cre_dttm) AS bill_create_date,
        TRUNC(NVL(b.bill_dt, b.cre_dttm)) AS event_date
    FROM cycle_last_event cle
    JOIN cisadm.ci_bill b
        ON NULLIF(TRIM(NVL(b.bill_cyc_cd, (
            SELECT ac.bill_cyc_cd
            FROM cisadm.ci_acct ac
            WHERE ac.acct_id = b.acct_id
        ))), '') = cle.bill_cycle_code
       AND TRUNC(NVL(b.bill_dt, b.cre_dttm)) = cle.cycle_last_event_date
),
latest_segments AS (
    SELECT
        cle.bill_cycle_code,
        NVL(b.acct_id, sa.acct_id) AS acct_id,
        s.sa_id,
        s.bseg_id,
        s.bill_id,
        TRUNC(NVL(b.bill_dt, s.cre_dttm)) AS event_date
    FROM cycle_last_event cle
    JOIN cisadm.ci_bseg s
        ON NULLIF(TRIM(s.bill_cyc_cd), '') = cle.bill_cycle_code
    LEFT JOIN cisadm.ci_bill b
        ON b.bill_id = s.bill_id
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = s.sa_id
    WHERE TRUNC(NVL(b.bill_dt, s.cre_dttm)) = cle.cycle_last_event_date
),
cycle_catalog AS (
    SELECT bill_cycle_code FROM expected_active
    UNION
    SELECT bill_cycle_code FROM cycle_last_event
),
cycle_descr AS (
    SELECT
        TRIM(bill_cyc_cd) AS bill_cycle_code,
        MAX(descr) AS bill_cycle_description
    FROM cisadm.ci_bill_cyc_l
    WHERE language_cd IN ('ENG', 'EN')
    GROUP BY TRIM(bill_cyc_cd)
)
SELECT
    cc.bill_cycle_code,
    NVL(cd.bill_cycle_description, 'Cycle ' || cc.bill_cycle_code) AS bill_cycle_description,
    NVL(ea.expected_active_sa_count, 0) AS expected_active_sa_count,
    NVL(ea.expected_active_account_count, 0) AS expected_active_account_count,
    COUNT(DISTINCT ls.sa_id) AS actual_billed_sa_count,
    COUNT(DISTINCT lbh.acct_id) AS actual_billed_account_count,
    COUNT(DISTINCT ls.bseg_id) AS actual_bill_segment_count,
    COUNT(DISTINCT lbh.bill_id) AS actual_bill_count,
    GREATEST(NVL(ea.expected_active_sa_count, 0) - COUNT(DISTINCT ls.sa_id), 0) AS missing_active_sa_count,
    GREATEST(NVL(ea.expected_active_account_count, 0) - COUNT(DISTINCT lbh.acct_id), 0) AS missing_active_account_count,
    cle.cycle_last_event_date,
    CASE
        WHEN cle.cycle_last_event_date = MAX(cle.cycle_last_event_date) OVER () THEN 'Y'
        ELSE 'N'
    END AS most_recent_bill_cycle_sw
FROM cycle_catalog cc
LEFT JOIN cycle_last_event cle
    ON cle.bill_cycle_code = cc.bill_cycle_code
LEFT JOIN expected_active ea
    ON ea.bill_cycle_code = cc.bill_cycle_code
LEFT JOIN latest_bill_headers lbh
    ON lbh.bill_cycle_code = cc.bill_cycle_code
LEFT JOIN latest_segments ls
    ON ls.bill_cycle_code = cc.bill_cycle_code
LEFT JOIN cycle_descr cd
    ON cd.bill_cycle_code = cc.bill_cycle_code
GROUP BY
    cc.bill_cycle_code,
    NVL(cd.bill_cycle_description, 'Cycle ' || cc.bill_cycle_code),
    NVL(ea.expected_active_sa_count, 0),
    NVL(ea.expected_active_account_count, 0),
    cle.cycle_last_event_date
ORDER BY cc.bill_cycle_code;
