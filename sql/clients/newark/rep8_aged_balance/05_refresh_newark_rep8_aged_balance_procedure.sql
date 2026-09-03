-- Rebuild CISADM.NEWARK_REP8_AGED_BALANCE for one as-of date.
-- Balance/aging from CMS_SA_SNAPSHOT; demographics from CM_AGED_BALANCE.
-- Prerequisite: refresh CMS_SA_SNAPSHOT for the same as-of date before calling this proc.

PROMPT Dropping legacy JRS2C2M procedure if present...

BEGIN
    EXECUTE IMMEDIATE 'DROP PROCEDURE jrs2c2m.refresh_newark_rep8_aged_balance';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-4043, -1031) THEN
            RAISE;
        END IF;
END;
/

PROMPT Creating CISADM.REFRESH_NEWARK_REP8_AGED_BALANCE procedure...

CREATE OR REPLACE PROCEDURE cisadm.refresh_newark_rep8_aged_balance (
    p_rpt_dt IN DATE DEFAULT TRUNC(SYSDATE)
) AS
    v_rpt_dt DATE := TRUNC(NVL(p_rpt_dt, SYSDATE));
BEGIN
    DELETE FROM cisadm.newark_rep8_aged_balance
    WHERE rpt_dt = v_rpt_dt;

    INSERT INTO cisadm.newark_rep8_aged_balance (
        rpt_dt,
        account,
        lot,
        lotsuff,
        block,
        blocksuf,
        qlfr,
        block_lot,
        status,
        customer_status_cd,
        customer_status_desc,
        customer_status_all,
        coll_cl_cd,
        coll_cl_desc,
        cust_cl_cd,
        cust_cl_desc,
        cis_division,
        prem_id,
        property_descr,
        property_type_cd,
        property_type_desc,
        cycle,
        estimated,
        service_location_name,
        service_address,
        service_address_zip_code,
        service_phone,
        billing_name,
        billing_address,
        city_state,
        zip_code,
        billing_phone,
        ward,
        street_name,
        current_bal,
        new_charges,
        arrears_30_principal,
        arrears_30_interest,
        arrears_60_principal,
        arrears_60_interest,
        arrears_90_principal,
        arrears_90_interest,
        arrears_total,
        latest_pay_dt,
        pa_flag,
        has_active_sa,
        active_sa_count,
        inactive_only_sw,
        sa_status_summary,
        has_credit_balance,
        comments,
        refreshed_at
    )
    WITH sa_acct AS (
        SELECT
            s.acct_id,
            SUM(s.cur_bal) AS current_bal,
            SUM(s.ars_amt1) AS new_charges,
            SUM(s.ars_amt2) AS arrears_30,
            SUM(s.ars_amt3) AS arrears_60,
            SUM(s.ars_amt4 + s.ars_amt5) AS arrears_90,
            SUM(s.ars_amt2 + s.ars_amt3 + s.ars_amt4 + s.ars_amt5) AS arrears_total
        FROM cisadm.cms_sa_snapshot s
        WHERE s.cm_snapshot_type_flg = 'LDAY'
          AND s.c1_snapshot_dt = v_rpt_dt
        GROUP BY s.acct_id
    ),
    sa_status AS (
        SELECT
            sa.acct_id,
            SUM(CASE WHEN sa.sa_status_flg = '20' THEN 1 ELSE 0 END) AS active_sa_count,
            SUM(CASE WHEN sa.sa_status_flg <> '20' THEN 1 ELSE 0 END) AS inactive_sa_count,
            COUNT(*) AS sa_count
        FROM cisadm.ci_sa sa
        GROUP BY sa.acct_id
    ),
    latest_pay AS (
        SELECT
            p.acct_id,
            MAX(pe.pay_dt) AS latest_pay_dt
        FROM cisadm.ci_pay p
        JOIN cisadm.ci_pay_event pe
          ON pe.pay_event_id = p.pay_event_id
        WHERE p.pay_status_flg = '50'
        GROUP BY p.acct_id
    ),
    pa_flag AS (
        SELECT
            sa.acct_id,
            'Y' AS pa_flag
        FROM cisadm.ci_sa sa
        WHERE sa.sa_type_cd = 'PA'
          AND sa.sa_status_flg = '20'
        GROUP BY sa.acct_id
    )
    SELECT
        v_rpt_dt,
        ab.account,
        ab.lot,
        ab.lotsuff,
        ab.block,
        ab.blocksuf,
        ab.qlfr,
        ab.block_lot,
        ab.status,
        ab.customer_status_cd,
        ab.customer_status_desc,
        ab.customer_status_all,
        ab.coll_cl_cd,
        ab.coll_cl_desc,
        ab.cust_cl_cd,
        ab.cust_cl_desc,
        ab.cis_division,
        ab.prem_id,
        ab.property_descr,
        ab.property_type_cd,
        ab.property_type_desc,
        ab.cycle,
        ab.estimated,
        ab.service_location_name,
        ab.service_address,
        ab.service_address_zip_code,
        ab.service_phone,
        ab.billing_name,
        ab.billing_address,
        ab.city_state,
        ab.zip_code,
        ab.billing_phone,
        ab.ward,
        ab.street_name,
        NVL(sa.current_bal, 0),
        NVL(sa.new_charges, 0),
        NVL(sa.arrears_30, 0),
        0,
        NVL(sa.arrears_60, 0),
        0,
        NVL(sa.arrears_90, 0),
        0,
        NVL(sa.arrears_total, 0),
        lp.latest_pay_dt,
        NVL(pf.pa_flag, 'N'),
        CASE WHEN NVL(ss.active_sa_count, 0) > 0 THEN 'Y' ELSE 'N' END,
        NVL(ss.active_sa_count, 0),
        CASE
            WHEN NVL(ss.active_sa_count, 0) = 0
             AND NVL(ss.sa_count, 0) > 0
            THEN 'Y'
            ELSE 'N'
        END,
        CASE
            WHEN NVL(ss.active_sa_count, 0) > 0
             AND NVL(ss.inactive_sa_count, 0) > 0
            THEN 'MIXED'
            WHEN NVL(ss.active_sa_count, 0) > 0
            THEN 'ACTIVE'
            WHEN NVL(ss.sa_count, 0) > 0
            THEN 'INACTIVE'
            ELSE 'NONE'
        END,
        CASE WHEN NVL(sa.current_bal, 0) < 0 THEN 'Y' ELSE 'N' END,
        ab.comments,
        SYSTIMESTAMP
    FROM jrs2c2m.cm_aged_balance ab
    LEFT JOIN sa_acct sa
      ON sa.acct_id = ab.account
    LEFT JOIN sa_status ss
      ON ss.acct_id = ab.account
    LEFT JOIN latest_pay lp
      ON lp.acct_id = ab.account
    LEFT JOIN pa_flag pf
      ON pf.acct_id = ab.account;

    COMMIT;
END refresh_newark_rep8_aged_balance;
/

PROMPT REFRESH_NEWARK_REP8_AGED_BALANCE procedure created.
