-- 4a) Manual first run (use 02a for baseline, 02 for scheduled rolling refresh)
BEGIN
    cisadm.refresh_field_activity_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. governed source population)
SELECT COUNT(*) AS snapshot_count
FROM cisadm.field_activity_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.d1_activity act
INNER JOIN cisadm.d1_activity_type act_type
    ON act_type.activity_type_cd = act.activity_type_cd
   AND act_type.activity_type_cat_flg = 'D1FA'
INNER JOIN cisadm.cms_d1_activity_d1fa_boda_vw boda
    ON boda.d1_activity_id = act.d1_activity_id;

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    d1_activity_id,
    COUNT(*) AS row_count
FROM cisadm.field_activity_rpt_curr
GROUP BY d1_activity_id
HAVING COUNT(*) > 1;

-- 4d) Rolling window coverage (6-month policy on activity dates)
SELECT
    MIN(act_cre_dttm) AS min_act_cre_dttm,
    MAX(act_cre_dttm) AS max_act_cre_dttm,
    MIN(start_dttm) AS min_start_dttm,
    MAX(start_dttm) AS max_start_dttm,
    COUNT(*) AS row_count
FROM cisadm.field_activity_rpt_curr;

SELECT
    COUNT(*) AS rows_outside_6_month_activity_window
FROM cisadm.field_activity_rpt_curr
WHERE NVL(act_cre_dttm, TIMESTAMP '1900-01-01') < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
  AND NVL(start_dttm, TIMESTAMP '1900-01-01') < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
  AND NVL(status_upd_dttm, TIMESTAMP '1900-01-01') < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
  AND NVL(end_dttm, TIMESTAMP '1900-01-01') < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6);

-- 4e) Null coverage check for governed descriptions
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN activity_type_desc IS NULL AND activity_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_activity_type_desc,
    SUM(CASE WHEN bo_status_desc IS NULL AND bo_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bo_status_desc,
    SUM(CASE WHEN cancel_reason_desc IS NULL AND cancel_reason IS NOT NULL THEN 1 ELSE 0 END) AS missing_cancel_reason_desc,
    SUM(CASE WHEN field_task_type_desc IS NULL AND field_task_type IS NOT NULL THEN 1 ELSE 0 END) AS missing_field_task_type_desc,
    SUM(CASE WHEN d1_sp_type_desc IS NULL AND d1_sp_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_d1_sp_type_desc,
    SUM(CASE WHEN acct_customer_name IS NULL AND acct_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_acct_customer_name
FROM cisadm.field_activity_rpt_curr;

-- 4f) Activity status profile
SELECT
    bo_status_cd,
    bo_status_desc,
    activity_type_cd,
    activity_type_desc,
    COUNT(*) AS activity_count
FROM cisadm.field_activity_rpt_curr
GROUP BY
    bo_status_cd,
    bo_status_desc,
    activity_type_cd,
    activity_type_desc
ORDER BY
    activity_count DESC,
    bo_status_cd,
    activity_type_cd;

-- 4g) Service-point linkage profile
SELECT
    CASE
        WHEN d1_sp_id IS NULL THEN 'No D1_SP link'
        WHEN sp_id IS NULL THEN 'D1_SP only'
        WHEN prem_id IS NULL THEN 'CI_SP only'
        WHEN acct_id IS NULL THEN 'Premise without account'
        ELSE 'Full SP/Prem/Acct chain'
    END AS linkage_band,
    COUNT(*) AS activity_count
FROM cisadm.field_activity_rpt_curr
GROUP BY
    CASE
        WHEN d1_sp_id IS NULL THEN 'No D1_SP link'
        WHEN sp_id IS NULL THEN 'D1_SP only'
        WHEN prem_id IS NULL THEN 'CI_SP only'
        WHEN acct_id IS NULL THEN 'Premise without account'
        ELSE 'Full SP/Prem/Acct chain'
    END
ORDER BY activity_count DESC;

-- 4h) Aging sanity checks
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN days_old < 0 THEN 1 ELSE 0 END) AS negative_days_old,
    SUM(CASE WHEN days_completed < 0 THEN 1 ELSE 0 END) AS negative_days_completed,
    SUM(CASE WHEN days_started_since_create < 0 THEN 1 ELSE 0 END) AS negative_days_started_since_create
FROM cisadm.field_activity_rpt_curr;

-- 4i) Appointment profile
SELECT
    appointment_flg,
    COUNT(*) AS activity_count,
    SUM(CASE WHEN appointment_window_start_dttm IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_appointment_window
FROM cisadm.field_activity_rpt_curr
GROUP BY appointment_flg
ORDER BY activity_count DESC;

-- 4j) Spot-check recent activities
SELECT *
FROM (
    SELECT
        d1_activity_id,
        activity_type_desc,
        bo_status_desc,
        act_cre_dttm,
        start_dttm,
        end_dttm,
        days_old,
        d1_customername,
        d1_sp_id,
        sp_city,
        division_cd,
        acct_id,
        acct_customer_name
    FROM cisadm.field_activity_rpt_curr
    ORDER BY act_cre_dttm DESC NULLS LAST, d1_activity_id
)
WHERE ROWNUM <= 25;
