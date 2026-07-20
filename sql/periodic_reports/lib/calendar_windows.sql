-- Calendar window reference for periodic reports (copy into WHERE clauses).
-- All windows are rolling — no bind parameters; re-run each period automatically.

-- =============================================================================
-- ANNUAL — previous full calendar year
-- =============================================================================
--   dt >= TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY')
--   AND dt <  TRUNC(SYSDATE, 'YYYY')

-- =============================================================================
-- QUARTERLY — previous full calendar quarter
-- =============================================================================
--   dt >= TRUNC(ADD_MONTHS(SYSDATE, -3), 'Q')
--   AND dt <  TRUNC(SYSDATE, 'Q')

-- =============================================================================
-- SEMI-ANNUAL — previous six full calendar months
-- =============================================================================
--   dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
--   AND dt <  TRUNC(SYSDATE, 'MM')

-- =============================================================================
-- Date column by workstream
-- =============================================================================
-- Billing:     BILL_DT
-- Finance FT:  ACCOUNTING_DT
-- FT GL:       ACCOUNTING_DT
-- Payments:    PAY_DT
-- Usage:       USAGE_START_DTTM / START_DTTM (cast to DATE where needed)
-- Workflow:    TD_CRE_DTTM / QUEUE_ANCHOR_DTTM
-- Field ops:   ACT_CRE_DTTM / START_DTTM
