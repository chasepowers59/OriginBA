CREATE OR REPLACE PROCEDURE cisadm.refresh_acct_customer_rpt_curr AS
    v_load_dttm TIMESTAMP := SYSTIMESTAMP;
BEGIN
    EXECUTE IMMEDIATE 'TRUNCATE TABLE cisadm.acct_customer_rpt_curr';

    INSERT INTO cisadm.acct_customer_rpt_curr (
        acct_id,
        setup_dt,
        bill_cyc_cd,
        bill_cyc_desc,
        cust_cl_cd,
        cust_cl_desc,
        coll_cl_cd,
        coll_cl_desc,
        acct_mgmt_grp_cd,
        acct_mgmt_grp_desc,
        bud_plan_cd,
        bud_plan_desc,
        cis_division,
        cis_division_desc,
        currency_cd,
        access_grp_cd,
        mailing_prem_id,
        bill_after_dt,
        cr_review_dt,
        postpone_cr_rvw_dt,
        int_cr_review_sw,
        no_dep_rvw_sw,
        protect_cyc_sw,
        protect_prem_sw,
        protect_div_sw,
        alert_info,
        per_id,
        customer_name,
        bill_rte_type_cd,
        bill_rte_type_desc,
        per_or_bus_flg,
        per_or_bus_desc,
        address1,
        address2,
        city,
        state,
        postal,
        country,
        emailid,
        ls_sl_flg,
        ls_sl_desc,
        home_phone,
        cell_phone,
        work_phone,
        primary_email,
        alert_count,
        open_alert_count,
        latest_alert_type_cd,
        latest_alert_type_desc,
        latest_alert_start_dt,
        active_sa_count,
        total_sa_count,
        distinct_active_sa_type_count,
        distinct_active_svc_type_count,
        sole_active_sa_type_cd,
        sole_active_sa_type_desc,
        earliest_sa_start_dt,
        latest_sa_start_dt,
        landlord_agreement_count,
        primary_ll_id,
        primary_ll_descr,
        load_dttm
    )
    WITH
    main_cust AS (
        SELECT
            ap.acct_id,
            ap.per_id,
            ap.bill_rte_type_cd,
            pn.entity_name_upr AS customer_name,
            per.per_or_bus_flg,
            per.address1,
            per.address2,
            per.city,
            per.state,
            per.postal,
            per.country,
            per.emailid,
            per.ls_sl_flg
        FROM cisadm.ci_acct_per ap
        JOIN cisadm.ci_per per
            ON per.per_id = ap.per_id
        JOIN cisadm.ci_per_name pn
            ON pn.per_id = ap.per_id
           AND pn.name_type_flg = 'PRIM'
        WHERE ap.main_cust_sw = 'Y'
    ),
    contact_ranked AS (
        SELECT
            cd.per_id,
            crt.comm_rte_meth_flg,
            cd.contact_value,
            ROW_NUMBER() OVER (
                PARTITION BY cd.per_id, crt.comm_rte_meth_flg
                ORDER BY
                    CASE WHEN cd.cnd_primary_flg = 'C1YS' THEN 0 ELSE 1 END,
                    cd.c1_contact_id
            ) AS rn
        FROM cisadm.c1_per_contdet cd
        JOIN cisadm.c1_comm_rte_type crt
            ON crt.comm_rte_type_cd = cd.comm_rte_type_cd
        WHERE cd.cnd_actinact_flg = 'C1AC'
    ),
    contact_pivot AS (
        SELECT
            cr.per_id,
            MAX(CASE WHEN cr.comm_rte_meth_flg = 'EMAIL' AND cr.rn = 1 THEN cr.contact_value END) AS primary_email,
            MAX(CASE WHEN cr.comm_rte_meth_flg = 'PHONE' AND cr.rn = 1 THEN cr.contact_value END) AS home_phone,
            MAX(CASE WHEN cr.comm_rte_meth_flg = 'PHONE' AND cr.rn = 2 THEN cr.contact_value END) AS cell_phone,
            MAX(CASE WHEN cr.comm_rte_meth_flg = 'PHONE' AND cr.rn = 3 THEN cr.contact_value END) AS work_phone
        FROM contact_ranked cr
        GROUP BY cr.per_id
    ),
    alert_agg AS (
        SELECT
            al.acct_id,
            COUNT(*) AS alert_count,
            SUM(
                CASE
                    WHEN TRUNC(SYSDATE) >= al.start_dt
                     AND (al.end_dt IS NULL OR TRUNC(SYSDATE) <= al.end_dt)
                    THEN 1
                    ELSE 0
                END
            ) AS open_alert_count
        FROM cisadm.ci_acct_alert al
        GROUP BY al.acct_id
    ),
    latest_alert AS (
        SELECT
            al.acct_id,
            al.alert_type_cd AS latest_alert_type_cd,
            al.start_dt AS latest_alert_start_dt
        FROM (
            SELECT
                al.acct_id,
                al.alert_type_cd,
                al.start_dt,
                ROW_NUMBER() OVER (
                    PARTITION BY al.acct_id
                    ORDER BY al.start_dt DESC, al.alert_type_cd
                ) AS rn
            FROM cisadm.ci_acct_alert al
        ) al
        WHERE al.rn = 1
    ),
    sa_agg AS (
        SELECT
            sa.acct_id,
            COUNT(*) AS total_sa_count,
            SUM(CASE WHEN sa.sa_status_flg = '20' THEN 1 ELSE 0 END) AS active_sa_count,
            COUNT(DISTINCT CASE WHEN sa.sa_status_flg = '20' THEN sa.sa_type_cd END) AS distinct_active_sa_type_count,
            COUNT(DISTINCT CASE WHEN sa.sa_status_flg = '20' THEN st.svc_type_cd END) AS distinct_active_svc_type_count,
            CASE
                WHEN COUNT(DISTINCT CASE WHEN sa.sa_status_flg = '20' THEN sa.sa_type_cd END) = 1
                THEN MAX(CASE WHEN sa.sa_status_flg = '20' THEN sa.sa_type_cd END)
            END AS sole_active_sa_type_cd,
            MIN(sa.start_dt) AS earliest_sa_start_dt,
            MAX(sa.start_dt) AS latest_sa_start_dt
        FROM cisadm.ci_sa sa
        LEFT JOIN cisadm.ci_sa_type st
            ON st.sa_type_cd = sa.sa_type_cd
           AND st.cis_division = sa.cis_division
        GROUP BY sa.acct_id
    ),
    ll_agg AS (
        SELECT
            ll.acct_id,
            COUNT(DISTINCT ll.ll_id) AS landlord_agreement_count,
            MIN(ll.ll_id) AS primary_ll_id,
            MIN(ll.descr) KEEP (DENSE_RANK FIRST ORDER BY ll.ll_id) AS primary_ll_descr
        FROM cisadm.ci_landlord ll
        GROUP BY ll.acct_id
    )
    SELECT
        acct.acct_id,
        acct.setup_dt,
        acct.bill_cyc_cd,
        bill_cyc_l.descr,
        acct.cust_cl_cd,
        cust_cl_l.descr,
        acct.coll_cl_cd,
        coll_cl_l.descr,
        acct.acct_mgmt_grp_cd,
        acct_mgmt_l.descr,
        acct.bud_plan_cd,
        bud_plan_l.descr,
        acct.cis_division,
        cis_div_l.descr,
        acct.currency_cd,
        acct.access_grp_cd,
        acct.mailing_prem_id,
        acct.bill_after_dt,
        acct.cr_review_dt,
        acct.postpone_cr_rvw_dt,
        acct.int_cr_review_sw,
        acct.no_dep_rvw_sw,
        acct.protect_cyc_sw,
        acct.protect_prem_sw,
        acct.protect_div_sw,
        SUBSTR(acct.alert_info, 1, 4000),
        mc.per_id,
        mc.customer_name,
        mc.bill_rte_type_cd,
        bill_rte_l.descr,
        mc.per_or_bus_flg,
        per_bus_l.descr,
        mc.address1,
        mc.address2,
        mc.city,
        mc.state,
        mc.postal,
        mc.country,
        mc.emailid,
        mc.ls_sl_flg,
        ls_sl_l.descr,
        cp.home_phone,
        cp.cell_phone,
        cp.work_phone,
        cp.primary_email,
        NVL(aa.alert_count, 0),
        NVL(aa.open_alert_count, 0),
        la.latest_alert_type_cd,
        alert_type_l.descr80,
        la.latest_alert_start_dt,
        NVL(sa.active_sa_count, 0),
        NVL(sa.total_sa_count, 0),
        NVL(sa.distinct_active_sa_type_count, 0),
        NVL(sa.distinct_active_svc_type_count, 0),
        sa.sole_active_sa_type_cd,
        sa_type_l.descr,
        sa.earliest_sa_start_dt,
        sa.latest_sa_start_dt,
        NVL(ll.landlord_agreement_count, 0),
        ll.primary_ll_id,
        ll.primary_ll_descr,
        v_load_dttm
    FROM cisadm.ci_acct acct
    LEFT JOIN main_cust mc
        ON mc.acct_id = acct.acct_id
    LEFT JOIN contact_pivot cp
        ON cp.per_id = mc.per_id
    LEFT JOIN alert_agg aa
        ON aa.acct_id = acct.acct_id
    LEFT JOIN latest_alert la
        ON la.acct_id = acct.acct_id
    LEFT JOIN sa_agg sa
        ON sa.acct_id = acct.acct_id
    LEFT JOIN ll_agg ll
        ON ll.acct_id = acct.acct_id
    LEFT JOIN cisadm.ci_bill_cyc_l bill_cyc_l
        ON bill_cyc_l.bill_cyc_cd = acct.bill_cyc_cd
       AND bill_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON cust_cl_l.cust_cl_cd = acct.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON coll_cl_l.coll_cl_cd = acct.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt_l
        ON acct_mgmt_l.acct_mgmt_grp_cd = acct.acct_mgmt_grp_cd
       AND acct_mgmt_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bud_plan_l bud_plan_l
        ON bud_plan_l.bud_plan_cd = acct.bud_plan_cd
       AND bud_plan_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cis_division_l cis_div_l
        ON cis_div_l.cis_division = acct.cis_division
       AND cis_div_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_rt_type_l bill_rte_l
        ON bill_rte_l.bill_rte_type_cd = mc.bill_rte_type_cd
       AND bill_rte_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l per_bus_l
        ON TRIM(per_bus_l.field_name) = 'PER_OR_BUS_FLG'
       AND TRIM(per_bus_l.field_value) = TRIM(mc.per_or_bus_flg)
       AND per_bus_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l ls_sl_l
        ON TRIM(ls_sl_l.field_name) = 'LS_SL_FLG'
       AND TRIM(ls_sl_l.field_value) = TRIM(mc.ls_sl_flg)
       AND ls_sl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_alert_type_l alert_type_l
        ON alert_type_l.alert_type_cd = la.latest_alert_type_cd
       AND alert_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_sa_type_l sa_type_l
        ON sa_type_l.sa_type_cd = sa.sole_active_sa_type_cd
       AND sa_type_l.cis_division = acct.cis_division
       AND sa_type_l.language_cd = 'ENG';

    COMMIT;
END;
/
