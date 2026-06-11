CREATE OR REPLACE PROCEDURE cisadm.refresh_pay_event_rpt_curr AS
    v_load_dttm      TIMESTAMP := SYSTIMESTAMP;
    v_window_start   DATE := ADD_MONTHS(TRUNC(SYSDATE), -6);
BEGIN
    DELETE FROM cisadm.pay_event_rpt_curr snap
    WHERE snap.pay_dt < v_window_start;
    COMMIT;

    DELETE FROM cisadm.pay_event_rpt_curr snap
    WHERE snap.pay_dt >= v_window_start
       OR EXISTS (
           SELECT 1
           FROM cisadm.ci_pay pay
           JOIN cisadm.ci_pay_event pe
               ON pe.pay_event_id = pay.pay_event_id
           WHERE pay.pay_id = snap.pay_id
             AND pe.pay_dt >= v_window_start
       );
    COMMIT;

    INSERT INTO cisadm.pay_event_rpt_curr (
        pay_id,
        pay_event_id,
        pay_dt,
        pay_event_cre_dttm,
        doc_id,
        acct_id,
        per_id,
        customer_name,
        pay_amt,
        currency_cd,
        pay_status_flg,
        pay_status_desc,
        can_rsn_cd,
        can_rsn_desc,
        match_type_cd,
        match_type_desc,
        match_val,
        non_cis_name,
        non_cis_ref_nbr,
        non_cis_comment,
        days_old,
        event_tender_count,
        event_tender_amt,
        distinct_tender_type_count,
        sole_tender_type_cd,
        sole_tender_type_desc,
        event_tndr_ctl_count,
        primary_tndr_ctl_id,
        primary_tndr_source_cd,
        primary_tndr_source_desc,
        primary_tndr_ctl_status_flg,
        primary_tndr_ctl_status_desc,
        event_dep_ctl_count,
        primary_dep_ctl_id,
        primary_dep_ctl_status_flg,
        primary_dep_ctl_status_desc,
        primary_dep_ctl_end_balance,
        event_dep_amt,
        acct_pp_count,
        active_pp_count,
        primary_pp_id,
        primary_pp_stat_flg,
        primary_pp_stat_desc,
        primary_pp_type_cd,
        primary_pp_type_desc,
        primary_pp_start_dt,
        load_dttm
    )
    WITH
    refresh_scope AS (
        SELECT pay.pay_id
        FROM cisadm.ci_pay pay
        JOIN cisadm.ci_pay_event pe
            ON pe.pay_event_id = pay.pay_event_id
        WHERE pe.pay_dt >= v_window_start
    ),
    main_cust AS (
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
                    ap.per_id
            ) AS rn
        FROM cisadm.ci_acct_per ap
        JOIN cisadm.ci_per_name pn
            ON pn.per_id = ap.per_id
        WHERE ap.main_cust_sw = 'Y'
          AND (pn.prim_name_sw = 'Y' OR pn.name_type_flg = 'PRIM')
    ),
    tender_event_profile AS (
        SELECT
            pt.pay_event_id,
            COUNT(*) AS event_tender_count,
            SUM(pt.tender_amt) AS event_tender_amt,
            COUNT(DISTINCT pt.tender_type_cd) AS distinct_tender_type_count,
            CASE
                WHEN COUNT(DISTINCT pt.tender_type_cd) = 1 THEN MIN(pt.tender_type_cd)
            END AS sole_tender_type_cd
        FROM cisadm.ci_pay_tndr pt
        GROUP BY pt.pay_event_id
    ),
    event_tndr_ctl_profile AS (
        SELECT
            pt.pay_event_id,
            COUNT(DISTINCT pt.tndr_ctl_id) AS event_tndr_ctl_count,
            MIN(pt.tndr_ctl_id) KEEP (
                DENSE_RANK FIRST ORDER BY pt.tndr_ctl_id
            ) AS primary_tndr_ctl_id
        FROM cisadm.ci_pay_tndr pt
        WHERE pt.tndr_ctl_id IS NOT NULL
        GROUP BY pt.pay_event_id
    ),
    event_dep_ctl_profile AS (
        SELECT
            pt.pay_event_id,
            COUNT(DISTINCT tc.dep_ctl_id) AS event_dep_ctl_count,
            MIN(tc.dep_ctl_id) KEEP (
                DENSE_RANK FIRST ORDER BY tc.dep_ctl_id
            ) AS primary_dep_ctl_id
        FROM cisadm.ci_pay_tndr pt
        JOIN cisadm.ci_tndr_ctl tc
            ON tc.tndr_ctl_id = pt.tndr_ctl_id
        WHERE tc.dep_ctl_id IS NOT NULL
        GROUP BY pt.pay_event_id
    ),
    event_dep_amt_profile AS (
        SELECT
            dep.pay_event_id,
            SUM(dep.deposit_amt) AS event_dep_amt
        FROM (
            SELECT DISTINCT
                pt.pay_event_id,
                td.tndr_dep_id,
                td.deposit_amt
            FROM cisadm.ci_pay_tndr pt
            JOIN cisadm.ci_tndr_ctl tc
                ON tc.tndr_ctl_id = pt.tndr_ctl_id
            JOIN cisadm.ci_tndr_dep td
                ON td.dep_ctl_id = tc.dep_ctl_id
        ) dep
        GROUP BY dep.pay_event_id
    ),
    pp_agg AS (
        SELECT
            pp.acct_id,
            COUNT(*) AS acct_pp_count,
            SUM(CASE WHEN NULLIF(TRIM(pp.pp_stat_flg), '') = '20' THEN 1 ELSE 0 END) AS active_pp_count
        FROM cisadm.ci_pp pp
        GROUP BY pp.acct_id
    ),
    primary_pp AS (
        SELECT
            pp.acct_id,
            pp.pp_id,
            pp.pp_stat_flg,
            pp.pp_type_cd,
            pp.start_dt
        FROM (
            SELECT
                pp.acct_id,
                pp.pp_id,
                pp.pp_stat_flg,
                pp.pp_type_cd,
                pp.start_dt,
                ROW_NUMBER() OVER (
                    PARTITION BY pp.acct_id
                    ORDER BY
                        CASE WHEN NULLIF(TRIM(pp.pp_stat_flg), '') = '20' THEN 0 ELSE 1 END,
                        pp.start_dt DESC NULLS LAST,
                        pp.pp_id
                ) AS rn
            FROM cisadm.ci_pp pp
        ) pp
        WHERE pp.rn = 1
    )
    SELECT
        pay.pay_id,
        pay.pay_event_id,
        pe.pay_dt,
        pe.cre_dttm,
        pe.doc_id,
        pay.acct_id,
        mc.per_id,
        mc.customer_name,
        pay.pay_amt,
        pay.currency_cd,
        pay.pay_status_flg,
        pay_status.descr,
        pay.can_rsn_cd,
        can_rsn.descr,
        pay.match_type_cd,
        match_type.descr,
        pay.match_val,
        pay.non_cis_name,
        pay.non_cis_ref_nbr,
        SUBSTR(pay.non_cis_comment, 1, 2000),
        CASE
            WHEN pe.pay_dt IS NOT NULL THEN TRUNC(SYSDATE) - TRUNC(pe.pay_dt)
        END,
        NVL(tep.event_tender_count, 0),
        NVL(tep.event_tender_amt, 0),
        NVL(tep.distinct_tender_type_count, 0),
        tep.sole_tender_type_cd,
        sole_tender.descr,
        NVL(etc.event_tndr_ctl_count, 0),
        etc.primary_tndr_ctl_id,
        tc.tndr_source_cd,
        tndr_src.descr,
        tc.tndr_ctl_st_flg,
        tndr_ctl_stat.descr,
        NVL(edc.event_dep_ctl_count, 0),
        edc.primary_dep_ctl_id,
        dc.dep_ctl_status_flg,
        dep_ctl_stat.descr,
        dc.end_balance,
        NVL(eda.event_dep_amt, 0),
        NVL(ppa.acct_pp_count, 0),
        NVL(ppa.active_pp_count, 0),
        ppp.pp_id,
        ppp.pp_stat_flg,
        pp_stat.descr,
        ppp.pp_type_cd,
        pp_type.descr,
        ppp.start_dt,
        v_load_dttm
    FROM cisadm.ci_pay pay
    JOIN refresh_scope rs
        ON rs.pay_id = pay.pay_id
    JOIN cisadm.ci_pay_event pe
        ON pe.pay_event_id = pay.pay_event_id
    LEFT JOIN main_cust mc
        ON mc.acct_id = pay.acct_id
       AND mc.rn = 1
    LEFT JOIN tender_event_profile tep
        ON tep.pay_event_id = pay.pay_event_id
    LEFT JOIN event_tndr_ctl_profile etc
        ON etc.pay_event_id = pay.pay_event_id
    LEFT JOIN event_dep_ctl_profile edc
        ON edc.pay_event_id = pay.pay_event_id
    LEFT JOIN event_dep_amt_profile eda
        ON eda.pay_event_id = pay.pay_event_id
    LEFT JOIN pp_agg ppa
        ON ppa.acct_id = pay.acct_id
    LEFT JOIN primary_pp ppp
        ON ppp.acct_id = pay.acct_id
    LEFT JOIN cisadm.ci_tndr_ctl tc
        ON tc.tndr_ctl_id = etc.primary_tndr_ctl_id
    LEFT JOIN cisadm.ci_dep_ctl dc
        ON dc.dep_ctl_id = edc.primary_dep_ctl_id
    LEFT JOIN cisadm.ci_lookup_val_l pay_status
        ON TRIM(pay_status.field_name) = 'PAY_STATUS_FLG'
       AND TRIM(pay_status.field_value) = TRIM(pay.pay_status_flg)
       AND pay_status.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_pay_can_rsn_l can_rsn
        ON can_rsn.can_rsn_cd = pay.can_rsn_cd
       AND can_rsn.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_match_type_l match_type
        ON match_type.match_type_cd = pay.match_type_cd
       AND match_type.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_tender_type_l sole_tender
        ON sole_tender.tender_type_cd = tep.sole_tender_type_cd
       AND sole_tender.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_tndr_srce_l tndr_src
        ON tndr_src.tndr_source_cd = tc.tndr_source_cd
       AND tndr_src.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l tndr_ctl_stat
        ON TRIM(tndr_ctl_stat.field_name) = 'TNDR_CTL_ST_FLG'
       AND TRIM(tndr_ctl_stat.field_value) = TRIM(tc.tndr_ctl_st_flg)
       AND tndr_ctl_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l dep_ctl_stat
        ON TRIM(dep_ctl_stat.field_name) = 'DEP_CTL_STATUS_FLG'
       AND TRIM(dep_ctl_stat.field_value) = TRIM(dc.dep_ctl_status_flg)
       AND dep_ctl_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l pp_stat
        ON TRIM(pp_stat.field_name) = 'PP_STAT_FLG'
       AND TRIM(pp_stat.field_value) = TRIM(ppp.pp_stat_flg)
       AND pp_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_pp_type_l pp_type
        ON pp_type.pp_type_cd = ppp.pp_type_cd
       AND pp_type.language_cd = 'ENG';

    COMMIT;
END;
/
