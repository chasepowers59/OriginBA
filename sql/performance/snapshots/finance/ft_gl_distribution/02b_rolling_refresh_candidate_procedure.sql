-- Candidate rolling-window procedure for CISADM.FT_GL_DISTRIBUTION_RPT_CURR.
--
-- Do not deploy this version until:
--   1. 10_refresh_strategy_diagnostics.sql supports a rolling-window decision.
--   2. The final window length is chosen.
--   3. 11_before_after_validation.sql is captured before and after cutover.
--
-- Intended operating model if approved:
--   - one-time full-history baseline load first
--   - then rolling-window maintenance refresh
--   - preserve older history already present in FT_GL_DISTRIBUTION_RPT_CURR
--
-- Current placeholder:
--   This file preserves the intended scaffold and cutover logic, but the
--   actual delete/reload slice is not finalized yet.

CREATE OR REPLACE PROCEDURE cisadm.refresh_ft_gl_distribution_rpt_curr AS
    v_window_start DATE := ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12);
BEGIN
    /*
        Candidate implementation pattern:

        1. Delete only snapshot rows whose parent FT accounting date is within
           the rolling window.

        DELETE FROM cisadm.ft_gl_distribution_rpt_curr snap
        WHERE EXISTS (
            SELECT 1
            FROM cisadm.ci_ft ft
            WHERE ft.ft_id = snap.ft_id
              AND ft.redundant_sw = 'N'
              AND ft.accounting_dt >= v_window_start
        );

        2. Reinsert only the same source slice.

        INSERT INTO cisadm.ft_gl_distribution_rpt_curr (...)
        SELECT ...
        FROM cisadm.ci_ft_gl ft_gl
        JOIN cisadm.ci_ft ft
          ON ft.ft_id = ft_gl.ft_id
         AND ft.redundant_sw = 'N'
        WHERE ft.accounting_dt >= v_window_start;

        3. Commit.

        Decision still pending:
        - whether the final window is 12 months, 18 months, or another period
        - whether additional create-date safety overlap is needed
        - whether recent back-posting into older accounting periods requires a
          wider retained maintenance window
    */

    RAISE_APPLICATION_ERROR(
        -20001,
        'Rolling FT_GL refresh candidate is not finalized. Run diagnostics and validation before deployment.'
    );
END;
/
