-- Origin C2M Governance Snippets
-- Reusable WHERE clauses and expressions for reports, Domains, and ETL.
-- Apply these in every C2M query that touches the relevant tables.

-- =============================================================================
-- 1. BLANK STRING NORMALIZATION (use in SELECT and WHERE as needed)
-- =============================================================================
-- Replace <column> with the actual column name.
-- NULLIF(TRIM(<column>), '')   AS <column>
-- WHERE NULLIF(TRIM(<column>), '') = 'value'

-- =============================================================================
-- 2. SAFETY FILTERS
-- =============================================================================

-- Financial facts: only frozen, audited data
-- Use with CI_BSEG or other billing/financial fact tables.
FREEZE_SW = 'Y'

-- Active accounts only (service agreements)
-- Use with CI_SA or joins to service points.
SA_STATUS_FLG = '20'

-- Active accounts with normalized flag (if column may be space-padded)
NULLIF(TRIM(SA_STATUS_FLG), '') = '20'

-- =============================================================================
-- 2b. RELEVANT DATA: ARREARS (active SAs only; exclude already paid off)
-- =============================================================================
-- Use in CI_FT arrears queries so only current, outstanding debt is counted.
-- CI_FT (arrears): frozen, in arrears, not payment types, valid arrears date
--   AND join to CI_SA with active-only so closed/cancelled SAs are excluded.
-- FREEZE_SW = 'Y' AND NOT_IN_ARS_SW = 'N' AND FT_TYPE_FLG NOT IN ('PS', 'PX')
--   AND ARS_DT IS NOT NULL
-- JOIN CI_SA: NULLIF(TRIM(SA.SA_STATUS_FLG), '') = '20'
-- After aggregation: HAVING SUM(FT.CUR_AMT) > 0
-- Gold standard (multi-layer): FREEZE_SW='Y', NOT_IN_ARS_SW='N', ARS_DT IS NOT NULL,
--   active SA only; balance check HAVING SUM(FT.CUR_AMT) > 0. For tenant isolation,
--   join F1_BUS_OBJ when available to verify standard life cycle per client.

-- =============================================================================
-- 3. MANDATORY DATE WINDOW (e.g. 90-day facts)
-- =============================================================================
-- Use on fact tables to limit scope and protect performance.
-- Adjust -3 (months) as required by the report (e.g. -1 for 30 days).

-- For a date column such as BILL_DT, EVENT_DT, etc.:
-- WHERE <date_column> >= ADD_MONTHS(TRUNC(SYSDATE), -3)
--   AND <date_column> <  TRUNC(SYSDATE) + 1

-- Example for BILL_DT (90-day window):
-- WHERE BILL_DT >= ADD_MONTHS(TRUNC(SYSDATE), -3)
--   AND BILL_DT <  TRUNC(SYSDATE) + 1

-- =============================================================================
-- 3b. AUDIT VS REPORTING MODE (toggle via RISK_DATA_ENABLED in .env)
-- =============================================================================
-- Reporting Mode (default): Clean Data only — FREEZE_SW = 'Y', SA_STATUS_FLG = '20'.
-- Audit Mode (RISK_DATA_ENABLED=1): Also run Risk Data queries; use statuses below.
-- SA_STATUS_FLG: '10' = Pending, '20' = Active, '70' = Canceled
-- PAY_STATUS_FLG: 'P' = Pending (tender stage; not yet in GL)
-- FREEZE_SW: 'Y' = finalized/audited, 'N' = not frozen (human or batch not finalized)
-- For AC-061 / Customer Contact Letters: Welcome Letter when SA moves 10 -> 20.
-- In Jaspersoft: conditional style (e.g. yellow) for rows where FREEZE_SW = 'N' so auditor sees unfinalized figures.

-- =============================================================================
-- 4. COMBINED EXAMPLE (financial segment + active account + date window)
-- =============================================================================
/*
SELECT
  b.seg_id,
  NULLIF(TRIM(b.customer_id), '')   AS customer_id,
  b.amount,
  b.bill_dt
FROM ci_bseg b
JOIN ci_sa s ON s.sa_id = b.sa_id
WHERE b.FREEZE_SW = 'Y'
  AND NULLIF(TRIM(s.SA_STATUS_FLG), '') = '20'
  AND b.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE), -3)
  AND b.bill_dt <  TRUNC(SYSDATE) + 1;
*/
