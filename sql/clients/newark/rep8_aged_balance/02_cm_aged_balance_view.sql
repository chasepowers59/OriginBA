-- Newark REP8 demographics view: one row per account with receivable activity.
-- Premise resolution prefers mailing / SA.CHAR_PREM_ID (many Newark accounts have no open SA_SP).
-- Legacy STATUS = premise char CUST STA (Customer Status), not collection class.

PROMPT Creating JRS2C2M.CM_AGED_BALANCE view...

CREATE OR REPLACE VIEW jrs2c2m.cm_aged_balance AS
WITH acct_with_rc AS (
    SELECT DISTINCT acct_id
    FROM jrs2c2m.cm_receivables
),
sa_prem AS (
    SELECT
        sa.acct_id,
        sa.char_prem_id AS prem_id,
        CASE WHEN sa.sa_status_flg = '20' THEN 1 ELSE 2 END AS pref
    FROM cisadm.ci_sa sa
    WHERE sa.char_prem_id IS NOT NULL
),
sp_prem AS (
    SELECT
        sa.acct_id,
        sp.prem_id,
        CASE WHEN sasp.stop_dttm IS NULL THEN 3 ELSE 4 END AS pref
    FROM cisadm.ci_sa sa
    JOIN cisadm.ci_sa_sp sasp
      ON sasp.sa_id = sa.sa_id
    JOIN cisadm.ci_sp sp
      ON sp.sp_id = sasp.sp_id
    WHERE sp.prem_id IS NOT NULL
),
acct_prem_candidates AS (
    SELECT a.acct_id, a.mailing_prem_id AS prem_id, 0 AS pref
    FROM cisadm.ci_acct a
    JOIN acct_with_rc rc
      ON rc.acct_id = a.acct_id
    WHERE a.mailing_prem_id IS NOT NULL
    UNION ALL
    SELECT acct_id, prem_id, pref FROM sa_prem
    UNION ALL
    SELECT acct_id, prem_id, pref FROM sp_prem
),
acct_prem AS (
    SELECT acct_id, prem_id
    FROM (
        SELECT
            acct_id,
            prem_id,
            ROW_NUMBER() OVER (
                PARTITION BY acct_id
                ORDER BY pref, prem_id
            ) AS rn
        FROM acct_prem_candidates
    )
    WHERE rn = 1
),
prem_char AS (
    SELECT
        prem_id,
        MAX(CASE WHEN char_type_cd = 'LOT' THEN
            TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
        END) AS lot,
        MAX(CASE WHEN char_type_cd = 'LOTSUFF' THEN
            TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
        END) AS lotsuff,
        MAX(CASE WHEN char_type_cd = 'BLOCK' THEN
            TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
        END) AS block,
        MAX(CASE WHEN char_type_cd = 'BLOCKSUF' THEN
            TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
        END) AS blocksuf,
        MAX(CASE WHEN char_type_cd = 'BLCK/LOT' THEN
            TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
        END) AS block_lot,
        MAX(CASE WHEN char_type_cd = 'CMC-QLFR' THEN
            TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
        END) AS qlfr,
        MAX(CASE WHEN char_type_cd = 'WARD' THEN
            TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
        END) AS ward,
        MAX(CASE WHEN char_type_cd = 'CUST STA' THEN
            TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
        END) AS customer_status_cd,
        MAX(CASE WHEN char_type_cd = 'PRPRTYTY' THEN
            TRIM(COALESCE(NULLIF(TRIM(char_val), ''), NULLIF(TRIM(adhoc_char_val), '')))
        END) AS property_type_cd
    FROM cisadm.ci_prem_char
    WHERE char_type_cd IN (
        'LOT', 'LOTSUFF', 'BLOCK', 'BLOCKSUF', 'BLCK/LOT', 'CMC-QLFR', 'WARD',
        'CUST STA', 'PRPRTYTY'
    )
    GROUP BY prem_id
),
-- Distinct customer statuses across all premises linked to the account (legacy can show multiple)
acct_status_distinct AS (
    SELECT DISTINCT
        c.acct_id,
        NVL(cvl.descr, pc.customer_status_cd) AS customer_status_desc
    FROM (
        SELECT DISTINCT acct_id, prem_id FROM acct_prem_candidates
    ) c
    JOIN prem_char pc
      ON pc.prem_id = c.prem_id
    LEFT JOIN cisadm.ci_char_val_l cvl
      ON cvl.char_type_cd = 'CUST STA'
     AND cvl.char_val = pc.customer_status_cd
     AND cvl.language_cd = 'ENG'
    WHERE pc.customer_status_cd IS NOT NULL
),
acct_status_all AS (
    SELECT
        acct_id,
        LISTAGG(customer_status_desc, ' | ')
            WITHIN GROUP (ORDER BY customer_status_desc) AS customer_status_all
    FROM acct_status_distinct
    GROUP BY acct_id
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
        ) AS billing_name_override,
        pn.entity_name AS primary_entity_name
    FROM main_person mp
    JOIN cisadm.ci_per p
      ON p.per_id = mp.per_id
    LEFT JOIN cisadm.ci_per_name pn
      ON pn.per_id = mp.per_id
     AND pn.name_type_flg = 'PRIM'
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
),
latest_coll_comment AS (
    SELECT
        acct_id,
        comments
    FROM (
        SELECT
            cp.acct_id,
            TRIM(cp.comments) AS comments,
            ROW_NUMBER() OVER (
                PARTITION BY cp.acct_id
                ORDER BY cp.cre_dttm DESC NULLS LAST, cp.coll_proc_id DESC
            ) AS rn
        FROM cisadm.ci_coll_proc cp
        WHERE TRIM(cp.comments) IS NOT NULL
    )
    WHERE rn = 1
)
SELECT
    a.acct_id AS account,
    pc.lot,
    pc.lotsuff,
    pc.block,
    pc.blocksuf,
    pc.qlfr,
    pc.block_lot,
    -- Legacy STATUS column = Customer Status description (CUST STA)
    NVL(cust_sta_l.descr, pc.customer_status_cd) AS status,
    pc.customer_status_cd,
    NVL(cust_sta_l.descr, pc.customer_status_cd) AS customer_status_desc,
    asa.customer_status_all,
    a.coll_cl_cd,
    coll_cl_l.descr AS coll_cl_desc,
    a.cust_cl_cd,
    cust_cl_l.descr AS cust_cl_desc,
    a.cis_division,
    ap.prem_id,
    -- Legacy PROPERTY DESCRIPTION = Property Type (PRPRTYTY)
    NVL(prpty_l.descr, pc.property_type_cd) AS property_descr,
    pc.property_type_cd,
    NVL(prpty_l.descr, pc.property_type_cd) AS property_type_desc,
    a.bill_cyc_cd AS cycle,
    CAST(NULL AS VARCHAR2(1)) AS estimated,
    -- Legacy SERVICE LOCATION NAME = primary person entity name
    NVL(NULLIF(TRIM(per.primary_entity_name), ''), NULLIF(TRIM(per.billing_name_override), '')) AS service_location_name,
    TRIM(
        p.address1 || ' ' ||
        NVL(p.address2, '') || ' ' ||
        NVL(p.address3, '') || ' ' ||
        NVL(p.address4, '')
    ) AS service_address,
    TRIM(p.postal) AS service_address_zip_code,
    ph.billing_phone AS service_phone,
    NVL(NULLIF(TRIM(per.billing_name_override), ''), per.primary_entity_name) AS billing_name,
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
    TRIM(p.address1) AS street_name,
    lcc.comments
FROM acct_with_rc rc
JOIN cisadm.ci_acct a
  ON a.acct_id = rc.acct_id
LEFT JOIN acct_prem ap
  ON ap.acct_id = a.acct_id
LEFT JOIN cisadm.ci_prem p
  ON p.prem_id = ap.prem_id
LEFT JOIN prem_char pc
  ON pc.prem_id = ap.prem_id
LEFT JOIN acct_status_all asa
  ON asa.acct_id = a.acct_id
LEFT JOIN cisadm.ci_prem mp
  ON mp.prem_id = a.mailing_prem_id
LEFT JOIN person per
  ON per.acct_id = a.acct_id
LEFT JOIN phone ph
  ON ph.acct_id = a.acct_id
LEFT JOIN cisadm.ci_coll_cl_l coll_cl_l
  ON coll_cl_l.coll_cl_cd = a.coll_cl_cd
 AND coll_cl_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_cust_cl_l cust_cl_l
  ON cust_cl_l.cust_cl_cd = a.cust_cl_cd
 AND cust_cl_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_char_val_l cust_sta_l
  ON cust_sta_l.char_type_cd = 'CUST STA'
 AND cust_sta_l.char_val = pc.customer_status_cd
 AND cust_sta_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_char_val_l prpty_l
  ON prpty_l.char_type_cd = 'PRPRTYTY'
 AND prpty_l.char_val = pc.property_type_cd
 AND prpty_l.language_cd = 'ENG'
LEFT JOIN latest_coll_comment lcc
  ON lcc.acct_id = a.acct_id;
