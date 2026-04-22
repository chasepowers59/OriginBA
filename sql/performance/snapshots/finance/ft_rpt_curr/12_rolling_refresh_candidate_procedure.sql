-- Candidate rolling-window procedure for CISADM.FT_RPT_CURR.
--
-- Do not deploy this version until:
--   1. 10a_refresh_strategy_diagnostics.sql supports a rolling-window decision.
--   2. The final window length is chosen.
--   3. 11_before_after_validation.sql is captured before and after cutover.

CREATE OR REPLACE PROCEDURE cisadm.refresh_ft_rpt_curr AS
    v_window_start DATE := ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12);
BEGIN
    /*
        Candidate implementation pattern:

        DELETE FROM cisadm.ft_rpt_curr
        WHERE accounting_dt >= v_window_start;

        INSERT INTO cisadm.ft_rpt_curr (...)
        SELECT ...
        FROM cisadm.ci_ft ft
        WHERE ft.redundant_sw = 'N'
          AND ft.accounting_dt >= v_window_start;

        COMMIT;
    */

    RAISE_APPLICATION_ERROR(
        -20001,
        'Rolling FT_RPT refresh candidate is not finalized. Run diagnostics and validation before deployment.'
    );
END;
/
