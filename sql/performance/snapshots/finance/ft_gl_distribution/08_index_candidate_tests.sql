-- Index candidate tests for CISADM.FT_GL_DISTRIBUTION_RPT_CURR
--
-- Purpose:
--   Test a small set of table-specific candidate indexes for the FT GL
--   distribution snapshot using the real filter pattern most often used in
--   reporting: ACCOUNTING_DT, FT_TYPE_FLG, and DST_ID.
--
-- Important:
--   - Test one candidate at a time in DEV.
--   - Re-run the same benchmark queries before and after each candidate.
--   - Drop the prior test index before creating the next one.
--   - These indexes are for the snapshot table itself. Source-table indexes do
--     not automatically help queries against FT_GL_DISTRIBUTION_RPT_CURR.
--
-- Why these three candidates:
--   1. (FT_TYPE_FLG, DST_ID, ACCOUNTING_DT)
--      Best starting point when reports usually filter by all three.
--      Equality predicates come first, then the date range.
--   2. (DST_ID, ACCOUNTING_DT)
--      Useful if many reports filter by distribution code and date but omit FT type.
--   3. (FT_TYPE_FLG, ACCOUNTING_DT)
--      Useful if many reports filter by FT type and date but omit DST_ID.
--
-- Why not descriptions first:
--   - FT_TYPE_FLG_DESC and DST_DESC are wider text columns.
--   - Code columns are usually more selective and more stable.
--   - Prefer filtering on FT_TYPE_FLG / DST_ID while displaying the descriptions.

SET SERVEROUTPUT ON
SET FEEDBACK ON
SET TIMING ON

PROMPT ============================================================
PROMPT Current index inventory for FT_GL_DISTRIBUTION_RPT_CURR
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
  AND i.table_name = 'FT_GL_DISTRIBUTION_RPT_CURR'
ORDER BY i.index_name, c.column_position;

PROMPT
PROMPT ============================================================
PROMPT Benchmark parameter prompts
PROMPT Use a real slow report slice. Keep the same inputs for every test.
PROMPT ============================================================

ACCEPT p_start_dt CHAR PROMPT 'Start accounting date (YYYY-MM-DD): '
ACCEPT p_end_dt   CHAR PROMPT 'End accounting date exclusive (YYYY-MM-DD): '
ACCEPT p_ft_type  CHAR PROMPT 'FT type code to test (example BS): '
ACCEPT p_dst_id   CHAR PROMPT 'DST_ID to test (example 4000): '

PROMPT
PROMPT ============================================================
PROMPT Baseline / benchmark queries
PROMPT Run these before any test index, then again after each candidate.
PROMPT ============================================================

PROMPT
PROMPT Query A: Date + FT type + DST_ID aggregate
SELECT COUNT(*) AS row_count,
       SUM(gl_amount) AS gl_amount,
       SUM(statistic_amount) AS statistic_amount
FROM cisadm.ft_gl_distribution_rpt_curr
WHERE accounting_dt >= TO_DATE('&p_start_dt', 'YYYY-MM-DD')
  AND accounting_dt < TO_DATE('&p_end_dt', 'YYYY-MM-DD')
  AND ft_type_flg = '&p_ft_type'
  AND dst_id = '&p_dst_id';

PROMPT
PROMPT Query B: Date + DST_ID aggregate
SELECT COUNT(*) AS row_count,
       SUM(gl_amount) AS gl_amount
FROM cisadm.ft_gl_distribution_rpt_curr
WHERE accounting_dt >= TO_DATE('&p_start_dt', 'YYYY-MM-DD')
  AND accounting_dt < TO_DATE('&p_end_dt', 'YYYY-MM-DD')
  AND dst_id = '&p_dst_id';

PROMPT
PROMPT Query C: Date + FT type aggregate
SELECT COUNT(*) AS row_count,
       SUM(gl_amount) AS gl_amount
FROM cisadm.ft_gl_distribution_rpt_curr
WHERE accounting_dt >= TO_DATE('&p_start_dt', 'YYYY-MM-DD')
  AND accounting_dt < TO_DATE('&p_end_dt', 'YYYY-MM-DD')
  AND ft_type_flg = '&p_ft_type';

PROMPT
PROMPT Query D: Detail extract sample on the full three-filter pattern
SELECT *
FROM (
    SELECT ft_id,
           gl_seq_nbr,
           accounting_dt,
           ft_type_flg,
           dst_id,
           gl_acct,
           gl_amount,
           statistic_amount,
           sa_id,
           bill_id,
           load_dttm
    FROM cisadm.ft_gl_distribution_rpt_curr
    WHERE accounting_dt >= TO_DATE('&p_start_dt', 'YYYY-MM-DD')
      AND accounting_dt < TO_DATE('&p_end_dt', 'YYYY-MM-DD')
      AND ft_type_flg = '&p_ft_type'
      AND dst_id = '&p_dst_id'
    ORDER BY accounting_dt, ft_id, gl_seq_nbr
)
FETCH FIRST 500 ROWS ONLY;

PROMPT
PROMPT ============================================================
PROMPT Candidate 1
PROMPT FT_TYPE_FLG + DST_ID + ACCOUNTING_DT
PROMPT Best first candidate when your reports usually use all three filters.
PROMPT ============================================================

-- CREATE INDEX CISADM.XOBA_FTGLRPT_FT_DST_ACCTDT
--     ON CISADM.FT_GL_DISTRIBUTION_RPT_CURR (FT_TYPE_FLG, DST_ID, ACCOUNTING_DT);
--
-- BEGIN
--     DBMS_STATS.GATHER_TABLE_STATS(
--         ownname => 'CISADM',
--         tabname => 'FT_GL_DISTRIBUTION_RPT_CURR',
--         cascade => TRUE
--     );
-- END;
-- /
--
-- DROP INDEX CISADM.XOBA_FTGLRPT_FT_DST_ACCTDT;

PROMPT
PROMPT ============================================================
PROMPT Candidate 2
PROMPT DST_ID + ACCOUNTING_DT
PROMPT Use if many real reports skip FT_TYPE_FLG but still filter by DST_ID.
PROMPT ============================================================

-- CREATE INDEX CISADM.XOBA_FTGLRPT_DST_ACCTDT
--     ON CISADM.FT_GL_DISTRIBUTION_RPT_CURR (DST_ID, ACCOUNTING_DT);
--
-- BEGIN
--     DBMS_STATS.GATHER_TABLE_STATS(
--         ownname => 'CISADM',
--         tabname => 'FT_GL_DISTRIBUTION_RPT_CURR',
--         cascade => TRUE
--     );
-- END;
-- /
--
-- DROP INDEX CISADM.XOBA_FTGLRPT_DST_ACCTDT;

PROMPT
PROMPT ============================================================
PROMPT Candidate 3
PROMPT FT_TYPE_FLG + ACCOUNTING_DT
PROMPT Use if many real reports skip DST_ID but still filter by FT type.
PROMPT ============================================================

-- CREATE INDEX CISADM.XOBA_FTGLRPT_FT_ACCTDT
--     ON CISADM.FT_GL_DISTRIBUTION_RPT_CURR (FT_TYPE_FLG, ACCOUNTING_DT);
--
-- BEGIN
--     DBMS_STATS.GATHER_TABLE_STATS(
--         ownname => 'CISADM',
--         tabname => 'FT_GL_DISTRIBUTION_RPT_CURR',
--         cascade => TRUE
--     );
-- END;
-- /
--
-- DROP INDEX CISADM.XOBA_FTGLRPT_FT_ACCTDT;

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
  AND i.table_name = 'FT_GL_DISTRIBUTION_RPT_CURR'
ORDER BY i.index_name, c.column_position;
