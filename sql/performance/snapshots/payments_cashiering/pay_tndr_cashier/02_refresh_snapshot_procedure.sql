CREATE OR REPLACE PROCEDURE cisadm.refresh_pay_tndr_cash_rpt_curr AS
    v_load_dttm TIMESTAMP := SYSTIMESTAMP;
BEGIN
    DELETE FROM cisadm.pay_tndr_cash_rpt_curr;
    COMMIT;

    -- Base load stays at tender grain. Event/payment/deposit-control context is
    -- joined in only where it preserves one row per PAY_TENDER_ID.
    INSERT INTO cisadm.pay_tndr_cash_rpt_curr (
        pay_tender_id,
        pay_event_id,
        pay_dt,
        payor_acct_id,
        per_id,
        customer_name,
        event_pay_count,
        sole_pay_id,
        event_pay_status_flg,
        event_pay_status_desc,
        event_pay_amt,
        event_tender_count,
        event_tender_amt,
        tender_type_cd,
        tender_type_desc,
        tndr_status_flg,
        tndr_ctl_id,
        tndr_ctl_cre_dttm,
        tndr_source_cd,
        tndr_source_desc,
        tndr_srce_type_flg,
        dep_ctl_id,
        dep_ctl_cre_dttm,
        dep_ctl_status_flg,
        dep_ctl_srce_type_flg,
        dep_ctl_start_balance,
        dep_ctl_end_balance,
        tender_amt,
        source_family_cd,
        source_family_desc,
        staged_tender_sw,
        pay_tnd_stg_st_flg,
        ext_source_id,
        apay_src_cd,
        apay_src_name,
        apay_rte_type_cd,
        dep_ctl_tndr_dep_count,
        dep_ctl_tndr_dep_amt,
        event_pay_seg_count,
        event_pay_seg_amt,
        event_match_evt_count,
        load_dttm
    )
    WITH
    pay_profile AS (
        SELECT /*+ MATERIALIZE */
            p.pay_event_id,
            COUNT(*) AS event_pay_count,
            CASE
                WHEN COUNT(*) = 1 THEN MIN(p.pay_id)
            END AS sole_pay_id,
            CASE
                WHEN COUNT(DISTINCT p.pay_status_flg) = 1 THEN MIN(p.pay_status_flg)
            END AS event_pay_status_flg,
            SUM(p.pay_amt) AS event_pay_amt
        FROM cisadm.ci_pay p
        GROUP BY p.pay_event_id
    ),
    tender_event_profile AS (
        SELECT /*+ MATERIALIZE */
            pt.pay_event_id,
            COUNT(*) AS event_tender_count,
            SUM(pt.tender_amt) AS event_tender_amt
        FROM cisadm.ci_pay_tndr pt
        GROUP BY pt.pay_event_id
    )
    SELECT
        pt.pay_tender_id,
        pt.pay_event_id,
        pe.pay_dt,
        pt.payor_acct_id,
        CAST(NULL AS VARCHAR2(40)) AS per_id,
        CAST(NULL AS VARCHAR2(200)) AS customer_name,
        pay_prof.event_pay_count,
        pay_prof.sole_pay_id,
        pay_prof.event_pay_status_flg,
        pay_status.descr AS event_pay_status_desc,
        pay_prof.event_pay_amt,
        te_prof.event_tender_count,
        te_prof.event_tender_amt,
        pt.tender_type_cd,
        ttl.descr AS tender_type_desc,
        pt.tndr_status_flg,
        pt.tndr_ctl_id,
        tc.cre_dttm AS tndr_ctl_cre_dttm,
        tc.tndr_source_cd,
        tsl.descr AS tndr_source_desc,
        ts.tndr_srce_type_flg,
        tc.dep_ctl_id,
        dc.cre_dttm AS dep_ctl_cre_dttm,
        dc.dep_ctl_status_flg,
        dc.tndr_srce_type_flg AS dep_ctl_srce_type_flg,
        dc.start_balance,
        dc.end_balance,
        pt.tender_amt,
        CASE
            WHEN TRIM(pt.tender_type_cd) IN ('OPCC', 'OPOC')
              OR TRIM(tc.tndr_source_cd) = 'ORIGINP' THEN 'ORIGINPAY'
            WHEN TRIM(tc.tndr_source_cd) = 'ACH' THEN 'LEGACY_APAY'
            ELSE 'OTHER'
        END AS source_family_cd,
        CASE
            WHEN TRIM(pt.tender_type_cd) IN ('OPCC', 'OPOC')
              OR TRIM(tc.tndr_source_cd) = 'ORIGINP' THEN 'OriginPay'
            WHEN TRIM(tc.tndr_source_cd) = 'ACH' THEN 'Legacy Auto Pay'
            ELSE 'Other Cashiering Source'
        END AS source_family_desc,
        'N' AS staged_tender_sw,
        CAST(NULL AS VARCHAR2(8)) AS pay_tnd_stg_st_flg,
        CAST(NULL AS VARCHAR2(60)) AS ext_source_id,
        CAST(NULL AS VARCHAR2(40)) AS apay_src_cd,
        CAST(NULL AS VARCHAR2(240)) AS apay_src_name,
        CAST(NULL AS VARCHAR2(40)) AS apay_rte_type_cd,
        0 AS dep_ctl_tndr_dep_count,
        0 AS dep_ctl_tndr_dep_amt,
        CAST(NULL AS NUMBER(18,0)) AS event_pay_seg_count,
        CAST(NULL AS NUMBER(18,2)) AS event_pay_seg_amt,
        CAST(NULL AS NUMBER(18,0)) AS event_match_evt_count,
        v_load_dttm
    FROM cisadm.ci_pay_tndr pt
    JOIN cisadm.ci_pay_event pe
        ON pe.pay_event_id = pt.pay_event_id
    LEFT JOIN pay_profile pay_prof
        ON pay_prof.pay_event_id = pt.pay_event_id
    LEFT JOIN tender_event_profile te_prof
        ON te_prof.pay_event_id = pt.pay_event_id
    LEFT JOIN cisadm.ci_lookup_val_l pay_status
        ON TRIM(pay_status.field_name) = 'PAY_STATUS_FLG'
       AND TRIM(pay_status.field_value) = TRIM(pay_prof.event_pay_status_flg)
       AND pay_status.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_tender_type_l ttl
        ON ttl.tender_type_cd = pt.tender_type_cd
       AND ttl.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_tndr_ctl tc
        ON tc.tndr_ctl_id = pt.tndr_ctl_id
    LEFT JOIN cisadm.ci_tndr_srce ts
        ON ts.tndr_source_cd = tc.tndr_source_cd
    LEFT JOIN cisadm.ci_tndr_srce_l tsl
        ON tsl.tndr_source_cd = tc.tndr_source_cd
       AND tsl.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_dep_ctl dc
        ON dc.dep_ctl_id = tc.dep_ctl_id;

    COMMIT;

    -- Customer context is filled after the tender-grain base load so we can
    -- prioritize one account-person row without disturbing the base population.
    MERGE INTO cisadm.pay_tndr_cash_rpt_curr tgt
    USING (
        SELECT
            ap.acct_id,
            MAX(ap.per_id) KEEP (
                DENSE_RANK FIRST ORDER BY
                    CASE WHEN ap.fin_resp_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN ap.main_cust_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN pn.prim_name_sw = 'Y' THEN 0 ELSE 1 END,
                    pn.seq_num,
                    pn.per_id
            ) AS per_id,
            MAX(pn.entity_name_upr) KEEP (
                DENSE_RANK FIRST ORDER BY
                    CASE WHEN ap.fin_resp_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN ap.main_cust_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN pn.prim_name_sw = 'Y' THEN 0 ELSE 1 END,
                    pn.seq_num,
                    pn.per_id
            ) AS customer_name
        FROM cisadm.ci_acct_per ap
        JOIN cisadm.ci_per_name pn
            ON pn.per_id = ap.per_id
        JOIN (
            SELECT DISTINCT payor_acct_id
            FROM cisadm.pay_tndr_cash_rpt_curr
            WHERE payor_acct_id IS NOT NULL
        ) tender
            ON tender.payor_acct_id = ap.acct_id
        WHERE ap.main_cust_sw = 'Y'
          AND (pn.prim_name_sw = 'Y' OR pn.name_type_flg = 'PRIM')
        GROUP BY ap.acct_id
    ) src
        ON (tgt.payor_acct_id = src.acct_id)
    WHEN MATCHED THEN UPDATE SET
        tgt.per_id = src.per_id,
        tgt.customer_name = src.customer_name;

    MERGE INTO cisadm.pay_tndr_cash_rpt_curr tgt
    USING (
        SELECT
            pts.pay_tender_id,
            MAX(pts.pay_tnd_stg_st_flg) AS pay_tnd_stg_st_flg,
            MAX(pts.ext_source_id) AS ext_source_id,
            MAX(aps.apay_src_cd) AS apay_src_cd,
            MAX(apsl.apay_src_name) AS apay_src_name,
            MAX(aps.apay_rte_type_cd) AS apay_rte_type_cd
        FROM cisadm.ci_pay_tndr_st pts
        LEFT JOIN cisadm.ci_apay_src aps
            ON aps.ext_source_id = pts.ext_source_id
        LEFT JOIN cisadm.ci_apay_src_l apsl
            ON apsl.apay_src_cd = aps.apay_src_cd
           AND apsl.language_cd = 'ENG'
        JOIN (
            SELECT DISTINCT pay_tender_id
            FROM cisadm.pay_tndr_cash_rpt_curr
        ) tender
            ON tender.pay_tender_id = pts.pay_tender_id
        GROUP BY pts.pay_tender_id
    ) src
        ON (tgt.pay_tender_id = src.pay_tender_id)
    WHEN MATCHED THEN UPDATE SET
        tgt.staged_tender_sw = 'Y',
        tgt.pay_tnd_stg_st_flg = src.pay_tnd_stg_st_flg,
        tgt.ext_source_id = src.ext_source_id,
        tgt.apay_src_cd = src.apay_src_cd,
        tgt.apay_src_name = src.apay_src_name,
        tgt.apay_rte_type_cd = src.apay_rte_type_cd;

    MERGE INTO cisadm.pay_tndr_cash_rpt_curr tgt
    USING (
        SELECT
            td.dep_ctl_id,
            COUNT(*) AS dep_ctl_tndr_dep_count,
            SUM(td.deposit_amt) AS dep_ctl_tndr_dep_amt
        FROM cisadm.ci_tndr_dep td
        JOIN (
            SELECT DISTINCT dep_ctl_id
            FROM cisadm.pay_tndr_cash_rpt_curr
            WHERE dep_ctl_id IS NOT NULL
        ) snap
            ON snap.dep_ctl_id = td.dep_ctl_id
        GROUP BY td.dep_ctl_id
    ) src
        ON (tgt.dep_ctl_id = src.dep_ctl_id)
    WHEN MATCHED THEN UPDATE SET
        tgt.dep_ctl_tndr_dep_count = src.dep_ctl_tndr_dep_count,
        tgt.dep_ctl_tndr_dep_amt = src.dep_ctl_tndr_dep_amt;

    UPDATE cisadm.pay_tndr_cash_rpt_curr tgt
    SET
        tgt.source_family_cd = CASE
            WHEN tgt.staged_tender_sw = 'Y' THEN 'STAGED_EXTERNAL'
            WHEN TRIM(tgt.tender_type_cd) IN ('OPCC', 'OPOC')
              OR TRIM(tgt.tndr_source_cd) = 'ORIGINP' THEN 'ORIGINPAY'
            WHEN TRIM(tgt.tndr_source_cd) = 'ACH' THEN 'LEGACY_APAY'
            ELSE 'OTHER'
        END,
        tgt.source_family_desc = CASE
            WHEN tgt.staged_tender_sw = 'Y' THEN 'Staged External Tender'
            WHEN TRIM(tgt.tender_type_cd) IN ('OPCC', 'OPOC')
              OR TRIM(tgt.tndr_source_cd) = 'ORIGINP' THEN 'OriginPay'
            WHEN TRIM(tgt.tndr_source_cd) = 'ACH' THEN 'Legacy Auto Pay'
            ELSE 'Other Cashiering Source'
        END;

    -- Pay-segment context is event-level overlay only. It is summarized here to
    -- avoid row multiplication from PAY -> PAY_SEG in the base load.
    MERGE INTO cisadm.pay_tndr_cash_rpt_curr tgt
    USING (
        SELECT
            p.pay_event_id,
            COUNT(ps.pay_seg_id) AS event_pay_seg_count,
            SUM(ps.pay_seg_amt) AS event_pay_seg_amt,
            COUNT(DISTINCT ps.match_evt_id) AS event_match_evt_count
        FROM cisadm.ci_pay p
        JOIN cisadm.ci_pay_seg ps
            ON ps.pay_id = p.pay_id
        JOIN (
            SELECT DISTINCT pay_event_id
            FROM cisadm.pay_tndr_cash_rpt_curr
        ) snap
            ON snap.pay_event_id = p.pay_event_id
        GROUP BY p.pay_event_id
    ) src
        ON (tgt.pay_event_id = src.pay_event_id)
    WHEN MATCHED THEN UPDATE SET
        tgt.event_pay_seg_count = src.event_pay_seg_count,
        tgt.event_pay_seg_amt = src.event_pay_seg_amt,
        tgt.event_match_evt_count = src.event_match_evt_count;

    COMMIT;
END;
/
