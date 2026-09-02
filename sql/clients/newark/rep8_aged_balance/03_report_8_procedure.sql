-- Compatibility stub for legacy {call REPORT_8()} dataset (unused by current REP8_VW table band).
-- Returns the demographic rowset; bucket columns are computed in REP8_VW SQL.

PROMPT Creating JRS2C2M.REPORT_8 procedure stub...

CREATE OR REPLACE PROCEDURE jrs2c2m.report_8 (
    p_result OUT SYS_REFCURSOR
) AS
BEGIN
    OPEN p_result FOR
        SELECT
            account,
            lot,
            lotsuff,
            block,
            blocksuf,
            qlfr,
            block_lot,
            status,
            property_descr,
            cycle,
            estimated,
            service_location_name,
            service_address,
            service_phone,
            billing_name,
            billing_address,
            city_state,
            zip_code,
            billing_phone,
            ward,
            CAST(NULL AS NUMBER) AS arrears_90,
            CAST(NULL AS NUMBER) AS arrears_60,
            CAST(NULL AS NUMBER) AS arrears_30,
            CAST(NULL AS NUMBER) AS arrears_total,
            CAST(NULL AS NUMBER) AS new_charges,
            CAST(NULL AS NUMBER) AS current_bal,
            street_name,
            CAST(NULL AS VARCHAR2(30)) AS latest_pay_dt
        FROM jrs2c2m.cm_aged_balance;
END report_8;
/
