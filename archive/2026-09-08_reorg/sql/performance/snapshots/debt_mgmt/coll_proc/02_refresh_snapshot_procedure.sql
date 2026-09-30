CREATE OR REPLACE PROCEDURE cisadm.refresh_coll_proc_rpt_curr AS
BEGIN
    DELETE FROM cisadm.coll_proc_rpt_curr;
    COMMIT;

    INSERT /*+ APPEND */ INTO cisadm.coll_proc_rpt_curr (
        coll_proc_id,
        acct_id,
        per_id,
        customer_name,
        coll_proc_tmpl_cd,
        coll_proc_tmpl_desc,
        coll_cl_cntl_cd,
        coll_cl_cntl_desc,
        currency_cd,
        coll_status_flg,
        coll_status_desc,
        coll_stat_rsn_flg,
        coll_stat_rsn_desc,
        coll_cat_prio_flg,
        coll_cat_prio_desc,
        crit_prio_flg,
        crit_prio_desc,
        coll_ars_dt,
        ars_amt,
        trigger_bp_sw,
        comments,
        coll_proc_cre_dttm,
        bill_cyc_cd,
        bill_cyc_desc,
        coll_cl_cd,
        coll_cl_desc,
        cust_cl_cd,
        cust_cl_desc,
        acct_mgmt_grp_cd,
        acct_mgmt_grp_desc,
        bud_plan_cd,
        bud_plan_desc,
        cr_review_dt,
        postpone_cr_rvw_dt,
        event_count,
        open_event_count,
        completed_event_count,
        first_trigger_dt,
        last_trigger_dt,
        first_completion_dt,
        last_completion_dt,
        next_event_seq,
        next_event_type_cd,
        next_event_type_desc,
        next_event_status_flg,
        next_event_status_desc,
        next_event_trigger_dt,
        latest_event_seq,
        latest_event_type_cd,
        latest_event_type_desc,
        latest_event_status_flg,
        latest_event_status_desc,
        latest_event_trigger_dt,
        latest_event_completion_dt,
        load_dttm
    )
    WITH
    customer_choice AS (
        SELECT
            ap.acct_id,
            ap.per_id,
            pn.entity_name_upr AS customer_name,
            ROW_NUMBER() OVER (
                PARTITION BY ap.acct_id
                ORDER BY
                    CASE WHEN ap.fin_resp_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN ap.main_cust_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN pn.prim_name_sw = 'Y' THEN 0 ELSE 1 END,
                    pn.seq_num,
                    pn.per_id
            ) AS rn
        FROM cisadm.ci_acct_per ap
        JOIN cisadm.ci_per_name pn
            ON pn.per_id = ap.per_id
        WHERE ap.main_cust_sw = 'Y'
          AND (pn.prim_name_sw = 'Y' OR pn.name_type_flg = 'PRIM')
    ),
    event_rollup AS (
        SELECT
            evt.coll_proc_id,
            COUNT(*) AS event_count,
            SUM(CASE WHEN evt.completion_dt IS NULL THEN 1 ELSE 0 END) AS open_event_count,
            SUM(CASE WHEN evt.completion_dt IS NOT NULL THEN 1 ELSE 0 END) AS completed_event_count,
            MIN(evt.trigger_dt) AS first_trigger_dt,
            MAX(evt.trigger_dt) AS last_trigger_dt,
            MIN(evt.completion_dt) AS first_completion_dt,
            MAX(evt.completion_dt) AS last_completion_dt
        FROM cisadm.ci_coll_evt evt
        GROUP BY evt.coll_proc_id
    ),
    next_event AS (
        SELECT
            nxt.coll_proc_id,
            nxt.evt_seq,
            nxt.coll_evt_typ_cd,
            nxt.coll_evt_stat_flg,
            nxt.trigger_dt
        FROM (
            SELECT
                evt.coll_proc_id,
                evt.evt_seq,
                evt.coll_evt_typ_cd,
                evt.coll_evt_stat_flg,
                evt.trigger_dt,
                ROW_NUMBER() OVER (
                    PARTITION BY evt.coll_proc_id
                    ORDER BY evt.evt_seq
                ) AS rn
            FROM cisadm.ci_coll_evt evt
            WHERE evt.completion_dt IS NULL
        ) nxt
        WHERE nxt.rn = 1
    ),
    latest_event AS (
        SELECT
            latest.coll_proc_id,
            latest.evt_seq,
            latest.coll_evt_typ_cd,
            latest.coll_evt_stat_flg,
            latest.trigger_dt,
            latest.completion_dt
        FROM (
            SELECT
                evt.coll_proc_id,
                evt.evt_seq,
                evt.coll_evt_typ_cd,
                evt.coll_evt_stat_flg,
                evt.trigger_dt,
                evt.completion_dt,
                ROW_NUMBER() OVER (
                    PARTITION BY evt.coll_proc_id
                    ORDER BY evt.evt_seq DESC
                ) AS rn
            FROM cisadm.ci_coll_evt evt
        ) latest
        WHERE latest.rn = 1
    )
    SELECT
        cp.coll_proc_id,
        cp.acct_id,
        cust.per_id,
        cust.customer_name,
        cp.coll_proc_tmpl_cd,
        coll_proc_tmpl.descr,
        cp.coll_cl_cntl_cd,
        coll_cl_cntl.descr,
        cp.currency_cd,
        cp.coll_status_flg,
        coll_status.descr,
        cp.coll_stat_rsn_flg,
        coll_stat_rsn.descr,
        cp.coll_cat_prio_flg,
        coll_cat_prio.descr,
        cp.crit_prio_flg,
        crit_prio.descr,
        cp.coll_ars_dt,
        cp.ars_amt,
        cp.trigger_bp_sw,
        cp.comments,
        cp.cre_dttm,
        acct.bill_cyc_cd,
        bill_cyc.descr,
        acct.coll_cl_cd,
        coll_cl.descr,
        acct.cust_cl_cd,
        cust_cl.descr,
        acct.acct_mgmt_grp_cd,
        acct_mgmt.descr,
        acct.bud_plan_cd,
        bud_plan.descr,
        acct.cr_review_dt,
        acct.postpone_cr_rvw_dt,
        evt_roll.event_count,
        evt_roll.open_event_count,
        evt_roll.completed_event_count,
        evt_roll.first_trigger_dt,
        evt_roll.last_trigger_dt,
        evt_roll.first_completion_dt,
        evt_roll.last_completion_dt,
        nxt.evt_seq,
        nxt.coll_evt_typ_cd,
        nxt_type.descr,
        nxt.coll_evt_stat_flg,
        nxt_status.descr,
        nxt.trigger_dt,
        latest.evt_seq,
        latest.coll_evt_typ_cd,
        latest_type.descr,
        latest.coll_evt_stat_flg,
        latest_status.descr,
        latest.trigger_dt,
        latest.completion_dt,
        SYSTIMESTAMP
    FROM cisadm.ci_coll_proc cp
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = cp.acct_id
    LEFT JOIN customer_choice cust
        ON cust.acct_id = cp.acct_id
       AND cust.rn = 1
    LEFT JOIN event_rollup evt_roll
        ON evt_roll.coll_proc_id = cp.coll_proc_id
    LEFT JOIN next_event nxt
        ON nxt.coll_proc_id = cp.coll_proc_id
    LEFT JOIN latest_event latest
        ON latest.coll_proc_id = cp.coll_proc_id
    LEFT JOIN cisadm.ci_coll_proc_tm_l coll_proc_tmpl
        ON coll_proc_tmpl.coll_proc_tmpl_cd = cp.coll_proc_tmpl_cd
       AND coll_proc_tmpl.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_cl_cntl_l coll_cl_cntl
        ON coll_cl_cntl.coll_cl_cntl_cd = cp.coll_cl_cntl_cd
       AND coll_cl_cntl.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l coll_status
        ON TRIM(coll_status.field_name) = 'COLL_STATUS_FLG'
       AND TRIM(coll_status.field_value) = TRIM(cp.coll_status_flg)
       AND coll_status.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l coll_stat_rsn
        ON TRIM(coll_stat_rsn.field_name) = 'COLL_STAT_RSN_FLG'
       AND TRIM(coll_stat_rsn.field_value) = TRIM(cp.coll_stat_rsn_flg)
       AND coll_stat_rsn.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l coll_cat_prio
        ON TRIM(coll_cat_prio.field_name) = 'COLL_CAT_PRIO_FLG'
       AND TRIM(coll_cat_prio.field_value) = TRIM(cp.coll_cat_prio_flg)
       AND coll_cat_prio.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l crit_prio
        ON TRIM(crit_prio.field_name) = 'CRIT_PRIO_FLG'
       AND TRIM(crit_prio.field_value) = TRIM(cp.crit_prio_flg)
       AND crit_prio.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l bill_cyc
        ON bill_cyc.bill_cyc_cd = acct.bill_cyc_cd
       AND bill_cyc.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_cl_l coll_cl
        ON coll_cl.coll_cl_cd = acct.coll_cl_cd
       AND coll_cl.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cust_cl_l cust_cl
        ON cust_cl.cust_cl_cd = acct.cust_cl_cd
       AND cust_cl.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt
        ON acct_mgmt.acct_mgmt_grp_cd = acct.acct_mgmt_grp_cd
       AND acct_mgmt.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bud_plan_l bud_plan
        ON bud_plan.bud_plan_cd = acct.bud_plan_cd
       AND bud_plan.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_evt_typ_l nxt_type
        ON nxt_type.coll_evt_typ_cd = nxt.coll_evt_typ_cd
       AND nxt_type.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l nxt_status
        ON TRIM(nxt_status.field_name) = 'COLL_EVT_STAT_FLG'
       AND TRIM(nxt_status.field_value) = TRIM(nxt.coll_evt_stat_flg)
       AND nxt_status.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_evt_typ_l latest_type
        ON latest_type.coll_evt_typ_cd = latest.coll_evt_typ_cd
       AND latest_type.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l latest_status
        ON TRIM(latest_status.field_name) = 'COLL_EVT_STAT_FLG'
       AND TRIM(latest_status.field_value) = TRIM(latest.coll_evt_stat_flg)
       AND latest_status.language_cd = 'ENG';

    COMMIT;
END;
/
