CREATE OR REPLACE PROCEDURE cisadm.refresh_wo_proc_rpt_curr AS
    v_window_start DATE := ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6);
    v_load_dttm    TIMESTAMP := SYSTIMESTAMP;
BEGIN
    DELETE FROM cisadm.wo_proc_rpt_curr snap
    WHERE snap.wo_proc_cre_dttm < v_window_start
      AND snap.wo_proc_compl_dt IS NOT NULL
      AND snap.wo_proc_compl_dt < v_window_start;

    DELETE FROM cisadm.wo_proc_rpt_curr snap
    WHERE snap.wo_proc_cre_dttm >= v_window_start
       OR snap.wo_proc_compl_dt IS NULL
       OR snap.wo_proc_compl_dt >= v_window_start;
    COMMIT;

    INSERT INTO cisadm.wo_proc_rpt_curr (
        wo_proc_id,
        acct_id,
        per_id,
        customer_name,
        currency_cd,
        wo_proc_tmpl_cd,
        wo_proc_tmpl_desc,
        wo_cntl_cd,
        wo_cntl_desc,
        wo_status_flg,
        wo_status_desc,
        wo_stat_rsn_flg,
        wo_stat_rsn_desc,
        uncoll_proc_stat_flg,
        uncoll_proc_stat_desc,
        crit_prio_flg,
        crit_prio_desc,
        trigger_bp_sw,
        comments,
        wo_proc_cre_dttm,
        wo_proc_compl_dt,
        process_duration_days,
        ars_at_start,
        ars_at_end,
        ars_diff,
        wo_sa_active_amt,
        wo_sa_inactive_amt,
        wo_sa_count,
        wo_sa_active_count,
        wo_sa_inactive_count,
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
        days_old,
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
    wo_sa_roll AS (
        SELECT
            wosa.wo_proc_id,
            COUNT(*) AS wo_sa_count,
            SUM(CASE WHEN NULLIF(TRIM(wosa.wo_sa_stat_flg), '') = '10' THEN 1 ELSE 0 END) AS wo_sa_active_count,
            SUM(CASE WHEN NULLIF(TRIM(wosa.wo_sa_stat_flg), '') = '20' THEN 1 ELSE 0 END) AS wo_sa_inactive_count,
            SUM(CASE WHEN NULLIF(TRIM(wosa.wo_sa_stat_flg), '') = '10' THEN NVL(wosa.ars_amt, 0) ELSE 0 END) AS wo_sa_active_amt,
            SUM(CASE WHEN NULLIF(TRIM(wosa.wo_sa_stat_flg), '') = '20' THEN NVL(wosa.ars_amt, 0) ELSE 0 END) AS wo_sa_inactive_amt
        FROM cisadm.ci_wo_proc_sa wosa
        GROUP BY wosa.wo_proc_id
    ),
    event_rollup AS (
        SELECT
            evt.wo_proc_id,
            COUNT(*) AS event_count,
            SUM(CASE WHEN evt.completion_dt IS NULL THEN 1 ELSE 0 END) AS open_event_count,
            SUM(CASE WHEN evt.completion_dt IS NOT NULL THEN 1 ELSE 0 END) AS completed_event_count,
            MIN(evt.trigger_dt) AS first_trigger_dt,
            MAX(evt.trigger_dt) AS last_trigger_dt,
            MIN(evt.completion_dt) AS first_completion_dt,
            MAX(evt.completion_dt) AS last_completion_dt
        FROM cisadm.ci_wo_evt evt
        GROUP BY evt.wo_proc_id
    ),
    next_event AS (
        SELECT
            nxt.wo_proc_id,
            nxt.evt_seq,
            nxt.wo_evt_typ_cd,
            nxt.wo_evt_stat_flg,
            nxt.trigger_dt
        FROM (
            SELECT
                evt.wo_proc_id,
                evt.evt_seq,
                evt.wo_evt_typ_cd,
                evt.wo_evt_stat_flg,
                evt.trigger_dt,
                ROW_NUMBER() OVER (
                    PARTITION BY evt.wo_proc_id
                    ORDER BY evt.evt_seq
                ) AS rn
            FROM cisadm.ci_wo_evt evt
            WHERE evt.completion_dt IS NULL
        ) nxt
        WHERE nxt.rn = 1
    ),
    latest_event AS (
        SELECT
            latest.wo_proc_id,
            latest.evt_seq,
            latest.wo_evt_typ_cd,
            latest.wo_evt_stat_flg,
            latest.trigger_dt,
            latest.completion_dt
        FROM (
            SELECT
                evt.wo_proc_id,
                evt.evt_seq,
                evt.wo_evt_typ_cd,
                evt.wo_evt_stat_flg,
                evt.trigger_dt,
                evt.completion_dt,
                ROW_NUMBER() OVER (
                    PARTITION BY evt.wo_proc_id
                    ORDER BY evt.evt_seq DESC
                ) AS rn
            FROM cisadm.ci_wo_evt evt
        ) latest
        WHERE latest.rn = 1
    )
    SELECT
        wp.wo_proc_id,
        wp.acct_id,
        COALESCE(bi.per_id, cust.per_id),
        cust.customer_name,
        COALESCE(bi.currency_cd, acct.currency_cd),
        wp.wo_proc_tmpl_cd,
        wo_tmpl.descr,
        wp.wo_cntl_cd,
        wo_cntl.descr,
        wp.wo_status_flg,
        wo_status.descr,
        wp.wo_stat_rsn_flg,
        wo_stat_rsn.descr,
        bi.uncoll_proc_stat_flg,
        uncoll_status.descr,
        wp.crit_prio_flg,
        crit_prio.descr,
        wp.trigger_bp_sw,
        wp.comments,
        wp.cre_dttm,
        bi.wo_proc_compl_dt,
        bi.uncoll_proc_dur,
        bi.ars_at_start,
        bi.ars_at_end,
        bi.ars_diff,
        NVL(wosa.wo_sa_active_amt, 0),
        NVL(wosa.wo_sa_inactive_amt, 0),
        NVL(wosa.wo_sa_count, 0),
        NVL(wosa.wo_sa_active_count, 0),
        NVL(wosa.wo_sa_inactive_count, 0),
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
        evt_roll.event_count,
        evt_roll.open_event_count,
        evt_roll.completed_event_count,
        evt_roll.first_trigger_dt,
        evt_roll.last_trigger_dt,
        evt_roll.first_completion_dt,
        evt_roll.last_completion_dt,
        nxt.evt_seq,
        nxt.wo_evt_typ_cd,
        nxt_type.descr,
        nxt.wo_evt_stat_flg,
        nxt_status.descr,
        nxt.trigger_dt,
        latest.evt_seq,
        latest.wo_evt_typ_cd,
        latest_type.descr,
        latest.wo_evt_stat_flg,
        latest_status.descr,
        latest.trigger_dt,
        latest.completion_dt,
        CASE
            WHEN wp.cre_dttm IS NOT NULL THEN TRUNC(SYSDATE) - TRUNC(wp.cre_dttm)
        END,
        v_load_dttm
    FROM cisadm.ci_wo_proc wp
    LEFT JOIN cisadm.c1_bi_woproc_vw bi
        ON bi.uncoll_proc_id = wp.wo_proc_id
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = wp.acct_id
    LEFT JOIN customer_choice cust
        ON cust.acct_id = wp.acct_id
       AND cust.rn = 1
    LEFT JOIN wo_sa_roll wosa
        ON wosa.wo_proc_id = wp.wo_proc_id
    LEFT JOIN event_rollup evt_roll
        ON evt_roll.wo_proc_id = wp.wo_proc_id
    LEFT JOIN next_event nxt
        ON nxt.wo_proc_id = wp.wo_proc_id
    LEFT JOIN latest_event latest
        ON latest.wo_proc_id = wp.wo_proc_id
    LEFT JOIN cisadm.ci_wo_proc_tmpl_l wo_tmpl
        ON wo_tmpl.wo_proc_tmpl_cd = wp.wo_proc_tmpl_cd
       AND wo_tmpl.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_wo_cntl_l wo_cntl
        ON wo_cntl.wo_cntl_cd = wp.wo_cntl_cd
       AND wo_cntl.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l wo_status
        ON TRIM(wo_status.field_name) = 'WO_STATUS_FLG'
       AND TRIM(wo_status.field_value) = TRIM(wp.wo_status_flg)
       AND wo_status.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l wo_stat_rsn
        ON TRIM(wo_stat_rsn.field_name) = 'WO_STAT_RSN_FLG'
       AND TRIM(wo_stat_rsn.field_value) = TRIM(wp.wo_stat_rsn_flg)
       AND wo_stat_rsn.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l uncoll_status
        ON TRIM(uncoll_status.field_name) = 'UNCOLL_PROC_STAT_FLG'
       AND TRIM(uncoll_status.field_value) = TRIM(bi.uncoll_proc_stat_flg)
       AND uncoll_status.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l crit_prio
        ON TRIM(crit_prio.field_name) = 'CRIT_PRIO_FLG'
       AND TRIM(crit_prio.field_value) = TRIM(wp.crit_prio_flg)
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
    LEFT JOIN cisadm.ci_wo_evt_typ_l nxt_type
        ON nxt_type.wo_evt_typ_cd = nxt.wo_evt_typ_cd
       AND nxt_type.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l nxt_status
        ON TRIM(nxt_status.field_name) = 'WO_EVT_STAT_FLG'
       AND TRIM(nxt_status.field_value) = TRIM(nxt.wo_evt_stat_flg)
       AND nxt_status.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_wo_evt_typ_l latest_type
        ON latest_type.wo_evt_typ_cd = latest.wo_evt_typ_cd
       AND latest_type.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l latest_status
        ON TRIM(latest_status.field_name) = 'WO_EVT_STAT_FLG'
       AND TRIM(latest_status.field_value) = TRIM(latest.wo_evt_stat_flg)
       AND latest_status.language_cd = 'ENG'
    WHERE wp.cre_dttm >= v_window_start
       OR bi.wo_proc_compl_dt IS NULL
       OR bi.wo_proc_compl_dt >= v_window_start;

    COMMIT;
END;
/
