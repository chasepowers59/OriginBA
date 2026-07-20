PROMPT ============================================================
PROMPT Run CISADM.REFRESH_CMS_SA_SNAPSHOT
PROMPT ============================================================

BEGIN
    cisadm.refresh_cms_sa_snapshot;
END;
/

PROMPT ============================================================
PROMPT Validate CISADM.CMS_SA_SNAPSHOT
PROMPT ============================================================

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

-- Domain derived-table shape check (CMS_ACCT_SNAPSHOT query)
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

SELECT owner, object_name, object_type, status
FROM all_objects
WHERE object_name IN ('CMS_SA_SNAPSHOT', 'REFRESH_CMS_SA_SNAPSHOT')
  AND owner = 'CISADM'
ORDER BY object_type, object_name;

PROMPT --- Extended validation (bucket identity, FT parity) ---
@@04_validate_cms_sa_snapshot.sql
