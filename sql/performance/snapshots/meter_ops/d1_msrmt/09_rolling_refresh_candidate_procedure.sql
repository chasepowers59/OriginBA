-- Candidate rolling-window procedure for CISADM.D1_MSRMT_RPT_CURR.
--
-- Do not deploy this version until:
--   1. 07_refresh_strategy_diagnostics.sql supports a rolling-window decision.
--   2. The final window length is chosen.
--   3. 08_fast_before_after_validation.sql is captured before and after cutover.

CREATE OR REPLACE PROCEDURE cisadm.refresh_d1_msrmt_rpt_curr AS
    v_window_start DATE := ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12);
BEGIN
    /*
        Candidate implementation pattern:

        DELETE FROM cisadm.d1_msrmt_rpt_curr
        WHERE msrmt_dttm >= v_window_start;

        INSERT INTO cisadm.d1_msrmt_rpt_curr (...)
        SELECT ...
        FROM cisadm.d1_msrmt msrmt
        WHERE msrmt.msrmt_dttm >= v_window_start;

        COMMIT;
    */

    RAISE_APPLICATION_ERROR(
        -20001,
        'Rolling D1_MSRMT refresh candidate is not finalized. Run diagnostics and validation before deployment.'
    );
END;
/
