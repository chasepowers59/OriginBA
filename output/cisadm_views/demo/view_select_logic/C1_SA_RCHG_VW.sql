-- SELECT logic for CISADM.C1_SA_RCHG_VW
SELECT
    "SA_ID","EFFDT","RCR_CHG_AMT","CURRENCY_CD"
FROM
    ci_sa_rchg_hist a
WHERE
    a.effdt = (
        SELECT
            MAX(b.effdt)
        FROM
            ci_sa_rchg_hist b
        WHERE
            a.sa_id = b.sa_id
            AND   b.effdt <= CURRENT_DATE
    )
