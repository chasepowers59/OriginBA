PROMPT ============================================================
PROMPT Active transactional values by workstream
PROMPT ============================================================
PROMPT Run these read-only queries to identify which configured values are actually active in this client environment.

PROMPT [Finance] FT type usage by accounting month
SELECT
    ft.ft_type_flg,
    TRUNC(ft.accounting_dt, 'MM') AS accounting_month,
    COUNT(*) AS ft_count,
    SUM(NVL(ft.cur_amt, 0)) AS total_cur_amt
FROM cisadm.ci_ft ft
WHERE ft.accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
GROUP BY
    ft.ft_type_flg,
    TRUNC(ft.accounting_dt, 'MM')
ORDER BY
    accounting_month,
    ft.ft_type_flg;

PROMPT [Billing] Completed bill segments by SA type and bill cycle
SELECT
    sa.sa_type_cd,
    bseg.bill_cyc_cd,
    COUNT(*) AS bseg_count,
    SUM(NVL(calc_agg.total_calc_amt, 0)) AS total_calc_amt
FROM cisadm.ci_bseg bseg
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
   AND bill.bill_stat_flg = 'C '
LEFT JOIN cisadm.ci_sa sa
    ON sa.sa_id = bseg.sa_id
LEFT JOIN (
    SELECT bseg_id, SUM(NVL(calc_amt, 0)) AS total_calc_amt
    FROM cisadm.ci_bseg_calc
    GROUP BY bseg_id
) calc_agg
    ON calc_agg.bseg_id = bseg.bseg_id
WHERE bill.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
GROUP BY
    sa.sa_type_cd,
    bseg.bill_cyc_cd
ORDER BY
    bseg_count DESC,
    sa.sa_type_cd,
    bseg.bill_cyc_cd;

PROMPT [Billing] Billed determinant activity by UOM / TOU / SQI
SELECT
    sq.uom_cd,
    sq.tou_cd,
    sq.sqi_cd,
    COUNT(*) AS sq_rows,
    SUM(NVL(sq.bill_sq, 0)) AS total_bill_sq
FROM cisadm.ci_bseg_sq sq
INNER JOIN cisadm.ci_bseg bseg
    ON bseg.bseg_id = sq.bseg_id
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
   AND bill.bill_stat_flg = 'C '
WHERE bill.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
GROUP BY
    sq.uom_cd,
    sq.tou_cd,
    sq.sqi_cd
ORDER BY
    total_bill_sq DESC,
    sq_rows DESC;

PROMPT [Meter Ops] Measurement activity by service point type and measurement component type
SELECT
    sp.d1_sp_type_cd,
    mc.measr_comp_type_cd,
    COUNT(*) AS msrmt_rows,
    SUM(NVL(msrmt.msrmt_val, 0)) AS total_msrmt_val
FROM cisadm.d1_msrmt msrmt
LEFT JOIN cisadm.d1_measr_comp mc
    ON mc.measr_comp_id = msrmt.measr_comp_id
LEFT JOIN cisadm.d1_install_evt ie
    ON ie.device_config_id = mc.device_config_id
   AND (ie.d1_install_dttm IS NULL OR ie.d1_install_dttm <= msrmt.msrmt_dttm)
   AND (ie.d1_removal_dttm IS NULL OR ie.d1_removal_dttm > msrmt.msrmt_dttm)
LEFT JOIN cisadm.d1_sp sp
    ON sp.d1_sp_id = ie.d1_sp_id
WHERE msrmt.msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
GROUP BY
    sp.d1_sp_type_cd,
    mc.measr_comp_type_cd
ORDER BY
    msrmt_rows DESC,
    sp.d1_sp_type_cd,
    mc.measr_comp_type_cd;

PROMPT [Meter Ops] Usage activity by usage group, usage type, and source flag
SELECT
    u.usg_grp_cd,
    us.us_type_cd,
    u.usg_src_flg,
    COUNT(*) AS usage_rows,
    SUM(NVL(u.tot_usg_trans_cnt, 0)) AS total_usage_trans_cnt
FROM cisadm.d1_usage u
LEFT JOIN cisadm.d1_us us
    ON us.us_id = u.us_id
WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
GROUP BY
    u.usg_grp_cd,
    us.us_type_cd,
    u.usg_src_flg
ORDER BY
    usage_rows DESC,
    u.usg_grp_cd,
    us.us_type_cd,
    u.usg_src_flg;
