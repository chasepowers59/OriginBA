-- Newark REP8 legacy support object: account / premise demographics for REP8_VW.
-- One row per account with open receivable activity (matches legacy REPORT_8 population).

PROMPT Creating JRS2C2M.CM_AGED_BALANCE view...

CREATE OR REPLACE VIEW jrs2c2m.cm_aged_balance AS
WITH prem_char AS (
    SELECT
        prem_id,
        MAX(
            CASE WHEN char_type_cd = 'LOT' THEN
                TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
            END
        ) AS lot,
        MAX(
            CASE WHEN char_type_cd = 'LOTSUFF' THEN
                TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
            END
        ) AS lotsuff,
        MAX(
            CASE WHEN char_type_cd = 'BLOCK' THEN
                TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
            END
        ) AS block,
        MAX(
            CASE WHEN char_type_cd = 'BLOCKSUF' THEN
                TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
            END
        ) AS blocksuf,
        MAX(
            CASE WHEN char_type_cd = 'BLCK/LOT' THEN
                TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
            END
        ) AS block_lot,
        MAX(
            CASE WHEN char_type_cd = 'CMC-QLFR' THEN
                TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
            END
        ) AS qlfr,
        MAX(
            CASE WHEN char_type_cd = 'WARD' THEN
                TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
            END
        ) AS ward
    FROM cisadm.ci_prem_char
    WHERE char_type_cd IN ('LOT', 'LOTSUFF', 'BLOCK', 'BLOCKSUF', 'BLCK/LOT', 'CMC-QLFR', 'WARD')
    GROUP BY prem_id
),
acct_prem AS (
    SELECT acct_id, MIN(prem_id) AS prem_id
    FROM (
        SELECT DISTINCT
            sa.acct_id,
            sp.prem_id
        FROM cisadm.ci_sa sa
        JOIN cisadm.ci_sa_sp sasp
          ON sasp.sa_id = sa.sa_id
         AND sasp.stop_dttm IS NULL
        JOIN cisadm.ci_sp sp
          ON sp.sp_id = sasp.sp_id
        WHERE sp.prem_id IS NOT NULL
    )
    GROUP BY acct_id
),
acct_with_rc AS (
    SELECT DISTINCT acct_id
    FROM jrs2c2m.cm_receivables
),
main_person AS (
    SELECT
        ap.acct_id,
        ap.per_id,
        ROW_NUMBER() OVER (
            PARTITION BY ap.acct_id
            ORDER BY CASE WHEN ap.main_cust_sw = 'Y' THEN 0 ELSE 1 END, ap.per_id
        ) AS rn
    FROM cisadm.ci_acct_per ap
),
person AS (
    SELECT
        mp.acct_id,
        TRIM(
            NVL(p.ovrd_mail_name1, '') || ' ' ||
            NVL(p.ovrd_mail_name2, '') || ' ' ||
            NVL(p.ovrd_mail_name3, '')
        ) AS billing_name
    FROM main_person mp
    JOIN cisadm.ci_per p
      ON p.per_id = mp.per_id
    WHERE mp.rn = 1
),
phone AS (
    SELECT
        mp.acct_id,
        MAX(pp.phone) KEEP (DENSE_RANK FIRST ORDER BY pp.seq_num) AS billing_phone
    FROM main_person mp
    JOIN cisadm.ci_per_phone pp
      ON pp.per_id = mp.per_id
    GROUP BY mp.acct_id
)
SELECT
    a.acct_id AS account,
    pc.lot,
    pc.lotsuff,
    pc.block,
    pc.blocksuf,
    pc.qlfr,
    pc.block_lot,
    a.coll_cl_cd AS status,
    TRIM(p.address1 || ' ' || NVL(p.address2, '')) AS property_descr,
    a.bill_cyc_cd AS cycle,
    CAST(NULL AS VARCHAR2(1)) AS estimated,
    TRIM(p.address1) AS service_location_name,
    TRIM(
        p.address1 || ' ' ||
        NVL(p.address2, '') || ' ' ||
        NVL(p.address3, '') || ' ' ||
        NVL(p.address4, '')
    ) AS service_address,
    TRIM(p.postal) AS service_address_zip_code,
    ph.billing_phone AS service_phone,
    per.billing_name,
    TRIM(
        mp.address1 || ' ' ||
        NVL(mp.address2, '') || ' ' ||
        NVL(mp.address3, '') || ' ' ||
        NVL(mp.address4, '')
    ) AS billing_address,
    TRIM(mp.city || ', ' || mp.state) AS city_state,
    TRIM(mp.postal) AS zip_code,
    ph.billing_phone,
    pc.ward,
    TRIM(p.address1) AS street_name
FROM acct_with_rc rc
JOIN cisadm.ci_acct a
  ON a.acct_id = rc.acct_id
LEFT JOIN acct_prem ap
  ON ap.acct_id = a.acct_id
LEFT JOIN cisadm.ci_prem p
  ON p.prem_id = ap.prem_id
LEFT JOIN prem_char pc
  ON pc.prem_id = ap.prem_id
LEFT JOIN cisadm.ci_prem mp
  ON mp.prem_id = a.mailing_prem_id
LEFT JOIN person per
  ON per.acct_id = a.acct_id
LEFT JOIN phone ph
  ON ph.acct_id = a.acct_id;
