-- Index candidate tests for CISADM.FT_RPT_CURR
--
-- Purpose:
--   Test table-specific candidate indexes for the FT header snapshot using the
--   most common report filter pattern described for this object:
--   ACCOUNTING_DT + FT_TYPE_FLG.
--
-- Important:
--   - Test one candidate at a time in DEV.
--   - Re-run the same benchmark queries before and after each candidate.
--   - Drop the prior test index before creating the next one.
--   - These indexes are for FT_RPT_CURR itself. Source-table indexes do not
--     automatically help queries against the snapshot table.
--
-- Recommended starting point:
--   1. (FT_TYPE_FLG, ACCOUNTING_DT)
--      Best first candidate when FT type is an equality filter and accounting
--      date is a range filter.
--
-- Secondary candidate:
--   2. (ACCOUNTING_DT)
--      Only test if many real reports use date ranges without FT_TYPE_FLG.

SET SERVEROUTPUT ON
SET FEEDBACK ON
SET TIMING ON

PROMPT ============================================================
PROMPT Current index inventory for FT_RPT_CURR
PROMPT ============================================================

SELECT i.index_name,
       i.uniqueness,
       c.column_name,
       c.column_position
FROM all_indexes i
JOIN all_ind_columns c
  ON c.index_owner = i.owner
 AND c.index_name = i.index_name
WHERE i.owner = 'CISADM'
  AND i.table_name = 'FT_RPT_CURR'
ORDER BY i.index_name, c.column_position;

PROMPT
PROMPT ============================================================
PROMPT Benchmark parameter prompts
PROMPT Use a real slow FT report slice. Keep the same inputs for every test.
PROMPT ============================================================

ACCEPT p_start_dt CHAR PROMPT 'Start accounting date (YYYY-MM-DD): '
ACCEPT p_end_dt   CHAR PROMPT 'End accounting date exclusive (YYYY-MM-DD): '
ACCEPT p_ft_type  CHAR PROMPT 'FT type code to test (example AD): '

PROMPT
PROMPT ============================================================
PROMPT Baseline / benchmark queries
PROMPT Run these before any test index, then again after each candidate.
PROMPT ============================================================

PROMPT
PROMPT Query A: Date + FT type aggregate
SELECT COUNT(*) AS row_count,
       SUM(cur_amt) AS cur_amt,
       SUM(tot_amt) AS tot_amt
FROM cisadm.ft_rpt_curr
WHERE accounting_dt >= TO_DATE('&p_start_dt', 'YYYY-MM-DD')
  AND accounting_dt < TO_DATE('&p_end_dt', 'YYYY-MM-DD')
  AND ft_type_flg = '&p_ft_type';

PROMPT
PROMPT Query B: Date-only aggregate
SELECT COUNT(*) AS row_count,
       SUM(cur_amt) AS cur_amt
FROM cisadm.ft_rpt_curr
WHERE accounting_dt >= TO_DATE('&p_start_dt', 'YYYY-MM-DD')
  AND accounting_dt < TO_DATE('&p_end_dt', 'YYYY-MM-DD');

PROMPT
PROMPT Query C: Detail extract sample on the common filter pattern
SELECT *
FROM (
    SELECT ft_id,
           ft_type_flg,
           ft_type_flg_desc,
           accounting_dt,
           acct_id,
           sa_id,
           bill_id,
           cur_amt,
           tot_amt,
           gl_distrib_status,
           gl_distrib_status_desc,
           load_dttm
    FROM cisadm.ft_rpt_curr
    WHERE accounting_dt >= TO_DATE('&p_start_dt', 'YYYY-MM-DD')
      AND accounting_dt < TO_DATE('&p_end_dt', 'YYYY-MM-DD')
      AND ft_type_flg = '&p_ft_type'
    ORDER BY accounting_dt, ft_id
)
FETCH FIRST 1000 ROWS ONLY;

PROMPT
PROMPT ============================================================
PROMPT Candidate 1
PROMPT FT_TYPE_FLG + ACCOUNTING_DT
PROMPT Best first candidate when reports usually use both filters.
PROMPT ============================================================

-- CREATE INDEX CISADM.XOBA_FTRPT_FT_ACCTDT
--     ON CISADM.FT_RPT_CURR (FT_TYPE_FLG, ACCOUNTING_DT);
--
-- BEGIN
--     DBMS_STATS.GATHER_TABLE_STATS(
--         ownname => 'CISADM',
--         tabname => 'FT_RPT_CURR',
--         cascade => TRUE
--     );
-- END;
-- /
--
-- DROP INDEX CISADM.XOBA_FTRPT_FT_ACCTDT;

PROMPT
PROMPT ============================================================
PROMPT Candidate 2
PROMPT ACCOUNTING_DT only
PROMPT Test only if many real reports use date ranges without FT type.
PROMPT ============================================================

-- CREATE INDEX CISADM.XOBA_FTRPT_ACCTDT
--     ON CISADM.FT_RPT_CURR (ACCOUNTING_DT);
--
-- BEGIN
--     DBMS_STATS.GATHER_TABLE_STATS(
--         ownname => 'CISADM',
--         tabname => 'FT_RPT_CURR',
--         cascade => TRUE
--     );
-- END;
-- /
--
-- DROP INDEX CISADM.XOBA_FTRPT_ACCTDT;

PROMPT
PROMPT ============================================================
PROMPT Optional verification after each CREATE INDEX
PROMPT ============================================================

SELECT i.index_name,
       i.status,
       i.visibility,
       c.column_name,
       c.column_position
FROM all_indexes i
JOIN all_ind_columns c
  ON c.index_owner = i.owner
 AND c.index_name = i.index_name
WHERE i.owner = 'CISADM'
  AND i.table_name = 'FT_RPT_CURR'
ORDER BY i.index_name, c.column_position;
