-- Validate CISADM.CMS_SA_SNAPSHOT after refresh.
-- Informational checks for rollout QA; install gate lives in
-- deployment_steps/04d_domain_support_install_validation_gate.sql

PROMPT --- Object and synonym status ---
SELECT owner, object_name, object_type, status
FROM all_objects
WHERE object_name IN ('CMS_SA_SNAPSHOT', 'REFRESH_CMS_SA_SNAPSHOT')
  AND owner = 'CISADM'
ORDER BY object_type, object_name;

SELECT owner, synonym_name, table_owner, table_name
FROM all_synonyms
WHERE synonym_name = 'CMS_SA_SNAPSHOT'
ORDER BY owner;

PROMPT --- Row counts and LDAY freshness ---
SELECT COUNT(*) AS row_count,
       MIN(c1_snapshot_dt) AS min_snapshot_dt,
       MAX(c1_snapshot_dt) AS max_snapshot_dt,
       COUNT(DISTINCT cm_snapshot_type_flg) AS type_cnt,
       SUM(cur_bal) AS sum_cur_bal,
       SUM(tot_bal) AS sum_tot_bal
FROM cisadm.cms_sa_snapshot;

SELECT cm_snapshot_type_flg, COUNT(*) AS cnt
FROM cisadm.cms_sa_snapshot
GROUP BY cm_snapshot_type_flg
ORDER BY cnt DESC;

PROMPT --- FIFO bucket identity (ARS_AMT1..5 = CUR_BAL) ---
SELECT COUNT(*) AS bucket_sum_gap_rows
FROM cisadm.cms_sa_snapshot
WHERE cm_snapshot_type_flg = 'LDAY'
  AND ABS(
        NVL(cur_bal, 0)
        - (
            NVL(ars_amt1, 0) + NVL(ars_amt2, 0) + NVL(ars_amt3, 0)
            + NVL(ars_amt4, 0) + NVL(ars_amt5, 0)
          )
      ) > 0.01;

PROMPT --- CUR_BAL parity vs due/past frozen FT population ---
WITH snap AS (
    SELECT SUM(cur_bal) AS snap_cur_bal
    FROM cisadm.cms_sa_snapshot
    WHERE cm_snapshot_type_flg = 'LDAY'
),
ft AS (
    SELECT SUM(ft.cur_amt) AS ft_cur_bal
    FROM cisadm.ci_ft ft
    WHERE ft.freeze_sw = 'Y'
      AND ft.not_in_ars_sw = 'N'
      AND ft.ars_dt IS NOT NULL
      AND TRUNC(ft.ars_dt) <= TRUNC(SYSDATE)
)
SELECT snap.snap_cur_bal,
       ft.ft_cur_bal,
       snap.snap_cur_bal - ft.ft_cur_bal AS cur_bal_delta
FROM snap
CROSS JOIN ft;

PROMPT --- Domain derived-table shape check (CMS_ACCT_SNAPSHOT query) ---
SELECT COUNT(*) AS acct_snapshot_rows
FROM (
    SELECT
        acct_id,
        per_id,
        c1_snapshot_dt,
        cm_snapshot_type_flg,
        SUM(cur_bal) AS cur_bal,
        SUM(tot_bal) AS tot_bal,
        SUM(new_chg_bal) AS new_chg_bal,
        SUM(ars_amt1) AS ars_amt1,
        SUM(ars_amt2) AS ars_amt2,
        SUM(ars_amt3) AS ars_amt3,
        SUM(ars_amt4) AS ars_amt4,
        SUM(ars_amt5) AS ars_amt5,
        SUM(ars_amt6) AS ars_amt6,
        SUM(ars_amt7) AS ars_amt7,
        SUM(ars_amt8) AS ars_amt8,
        SUM(ars_amt9) AS ars_amt9,
        SUM(ars_amt10) AS ars_amt10
    FROM cisadm.cms_sa_snapshot
    GROUP BY
        acct_id,
        per_id,
        c1_snapshot_dt,
        cm_snapshot_type_flg
);

PROMPT --- CISREAD access smoke ---
SELECT COUNT(*) AS cisread_rows
FROM cisread.cms_sa_snapshot
WHERE cm_snapshot_type_flg = 'LDAY';
