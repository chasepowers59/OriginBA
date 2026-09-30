-- 4a) Manual first run (use 02a for baseline, 02 for scheduled rolling refresh)
BEGIN
    cisadm.refresh_case_prem_contact_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. CMS_CI_CASE_VW source population)
SELECT COUNT(*) AS snapshot_count
FROM cisadm.case_prem_contact_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.cms_ci_case_vw;

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    case_id,
    COUNT(*) AS row_count
FROM cisadm.case_prem_contact_rpt_curr
GROUP BY case_id
HAVING COUNT(*) > 1;

-- 4d) Rolling window coverage (6-month policy on CASE_CRE_DTTM)
SELECT
    MIN(case_cre_dttm) AS min_case_cre_dttm,
    MAX(case_cre_dttm) AS max_case_cre_dttm,
    COUNT(*) AS row_count
FROM cisadm.case_prem_contact_rpt_curr;

SELECT
    COUNT(*) AS rows_older_than_6_months
FROM cisadm.case_prem_contact_rpt_curr
WHERE case_cre_dttm < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6);

-- 4e) Null coverage check for governed descriptions
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN case_type_desc IS NULL AND case_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_case_type_desc,
    SUM(CASE WHEN case_status_desc IS NULL AND case_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_case_status_desc,
    SUM(CASE WHEN case_cond_desc IS NULL AND case_cond_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_case_cond_desc,
    SUM(CASE WHEN prem_type_desc IS NULL AND prem_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_prem_type_desc,
    SUM(CASE WHEN bill_cyc_desc IS NULL AND bill_cyc_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_cyc_desc,
    SUM(CASE WHEN cust_cl_desc IS NULL AND cust_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_cust_cl_desc,
    SUM(CASE WHEN latest_cc_type_desc IS NULL AND latest_cc_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_latest_cc_type_desc,
    SUM(CASE WHEN case_person_name_upr IS NULL AND per_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_case_person_name,
    SUM(CASE WHEN acct_customer_name_upr IS NULL AND acct_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_acct_customer_name
FROM cisadm.case_prem_contact_rpt_curr;

-- 4f) Case status profile
SELECT
    case_type_cd,
    case_type_desc,
    case_status_cd,
    case_status_desc,
    COUNT(*) AS case_count
FROM cisadm.case_prem_contact_rpt_curr
GROUP BY
    case_type_cd,
    case_type_desc,
    case_status_cd,
    case_status_desc
ORDER BY
    case_count DESC,
    case_type_cd,
    case_status_cd;

-- 4g) Customer contact linkage profile
SELECT
    CASE
        WHEN cc_count = 0 THEN 'No linked contacts'
        WHEN cc_count = 1 THEN 'Single linked contact'
        ELSE 'Multiple linked contacts'
    END AS cc_linkage_band,
    COUNT(*) AS case_count
FROM cisadm.case_prem_contact_rpt_curr
GROUP BY
    CASE
        WHEN cc_count = 0 THEN 'No linked contacts'
        WHEN cc_count = 1 THEN 'Single linked contact'
        ELSE 'Multiple linked contacts'
    END
ORDER BY case_count DESC;

-- 4h) Spot-check recent cases with premise and latest contact context
SELECT
    case_id,
    case_type_cd,
    case_status_cd,
    case_cre_dttm,
    prem_city,
    prem_state,
    prem_postal,
    cc_count,
    latest_cc_dttm,
    latest_cc_type_cd
FROM cisadm.case_prem_contact_rpt_curr
WHERE case_cre_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
  AND ROWNUM <= 20;
