-- Active approved snapshot-table indexes
--
-- Use this file to keep the create statements for indexes that are currently
-- accepted for use on governed snapshot tables.

-- FT_GL_DISTRIBUTION_RPT_CURR
-- Helps adjustment-report filters that use:
--   FT_TYPE_FLG + ADJ_STATUS_FLG + ACCOUNTING_DT
CREATE INDEX CISADM.XOBA_FTGLRPT_FT_ADJSTAT_ACCTDT
    ON CISADM.FT_GL_DISTRIBUTION_RPT_CURR (FT_TYPE_FLG, ADJ_STATUS_FLG, ACCOUNTING_DT);

-- FT_RPT_CURR
-- Helps FT report filters that use:
--   FT_TYPE_FLG + ACCOUNTING_DT
CREATE INDEX CISADM.XOBA_FTRPT_FT_ACCTDT
    ON CISADM.FT_RPT_CURR (FT_TYPE_FLG, ACCOUNTING_DT);
