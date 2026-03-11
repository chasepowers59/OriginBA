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
        sa.acct_id,
        sa.sa_id
    FROM cisadm.ci_sa sa
    JOIN cisadm.ci_acct ac
        ON ac.acct_id = sa.acct_id
    WHERE TRIM(sa.sa_status_flg) = '20'
      AND NULLIF(TRIM(ac.bill_cyc_cd), '') IS NOT NULL
),
bill_status_lookup AS (
    SELECT
        field_value AS status_code,
        MAX(descr) AS status_description
    FROM cisadm.ci_lookup_val_l
    WHERE field_name = 'BILL_STAT_FLG'
      AND language_cd = 'ENG'
    GROUP BY field_value
),
bseg_status_lookup AS (
    SELECT
        field_value AS status_code,
        MAX(descr) AS status_description
    FROM cisadm.ci_lookup_val_l
    WHERE field_name = 'BSEG_STAT_FLG'
      AND language_cd = 'ENG'
    GROUP BY field_value
),
latest_bill_headers AS (
    SELECT
        cle.bill_cycle_code,
        b.acct_id AS account_id,
        b.bill_id,
        TRUNC(b.bill_dt) AS bill_date,
        TRUNC(b.cre_dttm) AS bill_create_date,
        NVL(bsl.status_description, 'BILL_STATUS_' || b.bill_stat_flg) AS bill_status_description,
        TRUNC(NVL(b.bill_dt, b.cre_dttm)) AS event_date
    FROM cycle_last_event cle
    JOIN cisadm.ci_bill b
        ON NULLIF(TRIM(NVL(b.bill_cyc_cd, (
            SELECT ac.bill_cyc_cd
            FROM cisadm.ci_acct ac
            WHERE ac.acct_id = b.acct_id
        ))), '') = cle.bill_cycle_code
       AND TRUNC(NVL(b.bill_dt, b.cre_dttm)) = cle.cycle_last_event_date
    LEFT JOIN bill_status_lookup bsl
        ON bsl.status_code = b.bill_stat_flg
),
latest_segments AS (
    SELECT
        cle.bill_cycle_code,
        NVL(b.acct_id, sa.acct_id) AS account_id,
        s.sa_id AS service_agreement_id,
        s.prem_id AS premise_id,
        s.bill_id,
        s.bseg_id AS bill_segment_id,
        TRUNC(b.bill_dt) AS bill_date,
        TRUNC(b.cre_dttm) AS bill_create_date,
        TRUNC(s.cre_dttm) AS bseg_create_date,
        NVL(bsl.status_description, 'BILL_STATUS_' || b.bill_stat_flg) AS bill_status_description,
        NVL(ssl.status_description, 'BSEG_STATUS_' || s.bseg_stat_flg) AS bseg_status_description,
        TRUNC(NVL(b.bill_dt, s.cre_dttm)) AS event_date
    FROM cycle_last_event cle
    JOIN cisadm.ci_bseg s
        ON NULLIF(TRIM(s.bill_cyc_cd), '') = cle.bill_cycle_code
    LEFT JOIN cisadm.ci_bill b
        ON b.bill_id = s.bill_id
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = s.sa_id
    LEFT JOIN bill_status_lookup bsl
        ON bsl.status_code = b.bill_stat_flg
    LEFT JOIN bseg_status_lookup ssl
        ON ssl.status_code = s.bseg_stat_flg
    WHERE TRUNC(NVL(b.bill_dt, s.cre_dttm)) = cle.cycle_last_event_date
)
SELECT
    y.bill_cycle_code,
    y.account_id,
    y.service_agreement_id,
    y.premise_id,
    y.bill_id,
    y.bill_segment_id,
    y.bill_date,
    y.bill_create_date,
    y.bseg_create_date,
    y.bill_status_description,
    y.bseg_status_description,
    'Y' AS is_error_sw,
    y.error_reason,
    y.exception_type,
    y.recommended_action,
    y.event_date,
    CASE
        WHEN y.event_date = MAX(y.event_date) OVER () THEN 'Y'
        ELSE 'N'
    END AS most_recent_bill_cycle_sw
FROM (
    SELECT
        ea.bill_cycle_code,
        ea.acct_id AS account_id,
        ea.sa_id AS service_agreement_id,
        CAST(NULL AS VARCHAR2(60)) AS premise_id,
        CAST(NULL AS VARCHAR2(60)) AS bill_id,
        CAST(NULL AS VARCHAR2(60)) AS bill_segment_id,
        CAST(NULL AS DATE) AS bill_date,
        CAST(NULL AS DATE) AS bill_create_date,
        CAST(NULL AS DATE) AS bseg_create_date,
        CAST(NULL AS VARCHAR2(200)) AS bill_status_description,
        CAST(NULL AS VARCHAR2(200)) AS bseg_status_description,
        'Active service agreement is assigned to the cycle but no bill header appears in the latest cycle snapshot.' AS error_reason,
        'MISSING_EXPECTED_BILL' AS exception_type,
        'Review account billing completion and batch outcome for the latest cycle run.' AS recommended_action,
        cle.cycle_last_event_date AS event_date
    FROM expected_active ea
    JOIN cycle_last_event cle
        ON cle.bill_cycle_code = ea.bill_cycle_code
    LEFT JOIN latest_bill_headers lbh
        ON lbh.bill_cycle_code = ea.bill_cycle_code
       AND lbh.account_id = ea.acct_id
    WHERE lbh.account_id IS NULL

    UNION ALL

    SELECT
        lbh.bill_cycle_code,
        lbh.account_id,
        CAST(NULL AS VARCHAR2(60)) AS service_agreement_id,
        CAST(NULL AS VARCHAR2(60)) AS premise_id,
        lbh.bill_id,
        CAST(NULL AS VARCHAR2(60)) AS bill_segment_id,
        lbh.bill_date,
        lbh.bill_create_date,
        CAST(NULL AS DATE) AS bseg_create_date,
        lbh.bill_status_description,
        CAST(NULL AS VARCHAR2(200)) AS bseg_status_description,
        'Bill header exists in the latest cycle snapshot but no bill segment row is linked to that bill.' AS error_reason,
        'MISSING_BSEG' AS exception_type,
        'Review bill segment generation and confirm the bill completed with segment output.' AS recommended_action,
        lbh.event_date
    FROM latest_bill_headers lbh
    LEFT JOIN latest_segments ls
        ON ls.bill_cycle_code = lbh.bill_cycle_code
       AND ls.bill_id = lbh.bill_id
    WHERE ls.bill_id IS NULL

    UNION ALL

    SELECT
        ls.bill_cycle_code,
        ls.account_id,
        ls.service_agreement_id,
        ls.premise_id,
        ls.bill_id,
        ls.bill_segment_id,
        ls.bill_date,
        ls.bill_create_date,
        ls.bseg_create_date,
        ls.bill_status_description,
        ls.bseg_status_description,
        'Bill segment row exists in the latest cycle snapshot but no matching bill header is present.' AS error_reason,
        'ORPHAN_BSEG' AS exception_type,
        'Review bill header creation and confirm the segment is attached to the correct bill.' AS recommended_action,
        ls.event_date
    FROM latest_segments ls
    LEFT JOIN latest_bill_headers lbh
        ON lbh.bill_cycle_code = ls.bill_cycle_code
       AND lbh.bill_id = ls.bill_id
    WHERE lbh.bill_id IS NULL

    UNION ALL

    SELECT
        lbh.bill_cycle_code,
        lbh.account_id,
        CAST(NULL AS VARCHAR2(60)) AS service_agreement_id,
        CAST(NULL AS VARCHAR2(60)) AS premise_id,
        lbh.bill_id,
        CAST(NULL AS VARCHAR2(60)) AS bill_segment_id,
        lbh.bill_date,
        lbh.bill_create_date,
        CAST(NULL AS DATE) AS bseg_create_date,
        lbh.bill_status_description,
        CAST(NULL AS VARCHAR2(200)) AS bseg_status_description,
        'Bill status indicates an exception condition in the latest cycle snapshot.' AS error_reason,
        'BILL_STATUS_EXCEPTION' AS exception_type,
        'Review bill status and billing batch logs for the affected bill.' AS recommended_action,
        lbh.event_date
    FROM latest_bill_headers lbh
    WHERE REGEXP_LIKE(UPPER(NVL(lbh.bill_status_description, '')), 'ERROR|EXCEPTION|FAIL')

    UNION ALL

    SELECT
        ls.bill_cycle_code,
        ls.account_id,
        ls.service_agreement_id,
        ls.premise_id,
        ls.bill_id,
        ls.bill_segment_id,
        ls.bill_date,
        ls.bill_create_date,
        ls.bseg_create_date,
        ls.bill_status_description,
        ls.bseg_status_description,
        'Bill segment status indicates an exception condition in the latest cycle snapshot.' AS error_reason,
        'BSEG_STATUS_EXCEPTION' AS exception_type,
        'Review bill segment status and the billing batch or retry path for the segment.' AS recommended_action,
        ls.event_date
    FROM latest_segments ls
    WHERE REGEXP_LIKE(UPPER(NVL(ls.bseg_status_description, '')), 'ERROR|EXCEPTION|FAIL')
) y
ORDER BY y.bill_cycle_code, y.account_id, y.service_agreement_id, y.bill_id, y.bill_segment_id;
