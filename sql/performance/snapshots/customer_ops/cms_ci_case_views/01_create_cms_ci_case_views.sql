-- CMS Case views expected by Standard Offering Case Domain.
-- Source: CISADM pattern used on Ellensburg / CityCorp TEST (CI_CASE + CI_CASE_LOG).

PROMPT ============================================================
PROMPT Create CISADM.CMS_CI_CASE_VW + CMS_CI_CASE_LOG_VW (SO Case Domain)
PROMPT ============================================================

CREATE OR REPLACE FORCE EDITIONABLE VIEW cisadm.cms_ci_case_vw (
    case_id,
    case_type_cd,
    case_status_cd,
    acct_id,
    per_id,
    prem_id,
    user_id,
    case_cre_dttm,
    case_cond_flg,
    closed_dttm,
    ilm_dt,
    ilm_arch_sw,
    case_dur
) AS
SELECT
    ca.case_id,
    ca.case_type_cd,
    ca.case_status_cd,
    ca.acct_id,
    ca.per_id,
    ca.prem_id,
    ca.user_id,
    c2.cre_dttm AS case_cre_dttm,
    ca.case_cond_flg,
    c2.closed_dttm,
    ca.ilm_dt,
    ca.ilm_arch_sw,
    CASE
        WHEN c2.closed_dttm IS NULL
            THEN ROUND((CURRENT_DATE - c2.cre_dttm) * 24 * 60, 2)
        ELSE ROUND((c2.closed_dttm - c2.cre_dttm) * 24 * 60, 2)
    END AS case_dur
FROM cisadm.ci_case ca
INNER JOIN (
    SELECT
        c1.case_id,
        MAX(cl.log_dttm) AS cre_dttm,
        MAX(cr.log_dttm) AS closed_dttm
    FROM cisadm.ci_case c1
    INNER JOIN cisadm.ci_case_log cl
        ON cl.case_id = c1.case_id
       AND cl.case_log_type_flg = 'CASC'
    LEFT JOIN cisadm.ci_case_log cr
        ON c1.case_cond_flg = 'CLSD'
       AND cr.case_id = c1.case_id
       AND cr.case_log_type_flg = 'STAT'
    GROUP BY c1.case_id
) c2
    ON c2.case_id = ca.case_id;

CREATE OR REPLACE FORCE EDITIONABLE VIEW cisadm.cms_ci_case_log_vw (
    case_id,
    seq_num,
    case_log_type_flg,
    case_type_cd,
    case_status_cd,
    acct_id,
    per_id,
    prem_id,
    user_id,
    log_dttm,
    prev_log_dttm,
    prev_case_status_cd,
    prev_state_dur,
    curr_state_dur
) AS
SELECT
    clog.case_id,
    clog.seq_num,
    clog.case_log_type_flg,
    ca.case_type_cd,
    clog.case_status_cd,
    ca.acct_id,
    ca.per_id,
    ca.prem_id,
    ca.user_id,
    clog.log_dttm,
    LAG(clog.log_dttm) OVER (
        PARTITION BY clog.case_id ORDER BY clog.log_dttm, clog.seq_num
    ) AS prev_log_dttm,
    LAG(clog.case_status_cd) OVER (
        PARTITION BY clog.case_id ORDER BY clog.log_dttm, clog.seq_num
    ) AS prev_case_status_cd,
    DECODE(
        clog.case_log_type_flg,
        'CASC',
        0,
        ROUND(
            (
                clog.log_dttm
                - LAG(clog.log_dttm) OVER (
                    PARTITION BY clog.case_id ORDER BY clog.log_dttm, clog.seq_num
                  )
            ) * 24 * 60,
            2
        )
    ) AS prev_state_dur,
    CASE
        WHEN st.status_cond_flg <> 'FINL'
         AND LEAD(clog.log_dttm) OVER (
                PARTITION BY clog.case_id ORDER BY clog.log_dttm, clog.seq_num
             ) IS NULL
            THEN ROUND((CURRENT_DATE - clog.log_dttm) * 24 * 60, 2)
        WHEN st.status_cond_flg <> 'FINL'
         AND LEAD(clog.log_dttm) OVER (
                PARTITION BY clog.case_id ORDER BY clog.log_dttm, clog.seq_num
             ) IS NOT NULL
            THEN ROUND(
                (
                    LEAD(clog.log_dttm) OVER (
                        PARTITION BY clog.case_id ORDER BY clog.log_dttm, clog.seq_num
                    )
                    - clog.log_dttm
                ) * 24 * 60,
                2
            )
        ELSE 0
    END AS curr_state_dur
FROM cisadm.ci_case_log clog
JOIN cisadm.ci_case ca
  ON ca.case_id = clog.case_id
JOIN cisadm.ci_case_status st
  ON st.case_type_cd = ca.case_type_cd
 AND st.case_status_cd = clog.case_status_cd
WHERE clog.case_log_type_flg IN ('CASC', 'STAT');

-- Grants / synonyms (skip silently if role/user missing on limited-priv DBs)
BEGIN
    EXECUTE IMMEDIATE 'GRANT SELECT ON cisadm.cms_ci_case_vw TO cis_user';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'GRANT SELECT ON cisadm.cms_ci_case_vw TO cis_read';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'GRANT SELECT ON cisadm.cms_ci_case_vw TO cisread';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'GRANT SELECT ON cisadm.cms_ci_case_vw TO cisuser';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'GRANT SELECT ON cisadm.cms_ci_case_vw TO jrs2c2m';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'GRANT SELECT ON cisadm.cms_ci_case_log_vw TO cis_user';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'GRANT SELECT ON cisadm.cms_ci_case_log_vw TO cis_read';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'GRANT SELECT ON cisadm.cms_ci_case_log_vw TO cisread';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'GRANT SELECT ON cisadm.cms_ci_case_log_vw TO cisuser';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'GRANT SELECT ON cisadm.cms_ci_case_log_vw TO jrs2c2m';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

CREATE OR REPLACE SYNONYM cisread.cms_ci_case_vw FOR cisadm.cms_ci_case_vw;
CREATE OR REPLACE SYNONYM cisread.cms_ci_case_log_vw FOR cisadm.cms_ci_case_log_vw;

PROMPT CMS Case views ready.
SELECT object_name, status
FROM all_objects
WHERE owner = 'CISADM'
  AND object_name IN ('CMS_CI_CASE_VW', 'CMS_CI_CASE_LOG_VW')
ORDER BY 1;
