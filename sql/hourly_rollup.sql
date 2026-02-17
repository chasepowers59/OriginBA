-- GOVERNED: Hourly Rollup for utility metering analytics (C2M-native)
-- Context: Oracle 19/21c, large tables, partition pruning on D1_MSRMT.MSRMT_DTTM.
-- Bind variables required:
--   :client_id   VARCHAR2/NUMBER  (mapped to D1_SP.DIVISION_CD for tenant isolation)
--   :start_ts    TIMESTAMP
--   :end_ts      TIMESTAMP
--
-- Estimated impact (when predicates are selective and partition pruning is active):
--   - I/O: medium to high, proportional to partitions touched between :start_ts and :end_ts
--   - TEMP: medium for HASH GROUP BY on hourly aggregates
--   - PGA: medium; monitor workarea size for high cardinality windows
--
-- Rollback plan:
--   1) Revert to previous report SQL version.
--   2) Drop any newly introduced indexes (see optional DDL section).
--   3) Re-check plan hash and elapsed time against baseline capture.

--------------------------------------------------------------------------------
-- Main query (partition-pruned on MSRMT_DTTM)
--------------------------------------------------------------------------------
SELECT
    SP.DIVISION_CD AS CLIENT_ID,
    SP.D1_SP_ID,
    MC.MEASR_COMP_ID,
    TRUNC(M.MSRMT_DTTM, 'HH24') AS READING_HOUR,
    SUM(NVL(M.READING_VAL, NVL(M.MSRMT_VAL, 0))) AS TOTAL_READING_VALUE,
    COUNT(*) AS READING_COUNT
FROM CISADM.D1_MSRMT M
JOIN CISADM.D1_MEASR_COMP MC
  ON MC.MEASR_COMP_ID = M.MEASR_COMP_ID
JOIN CISADM.D1_INSTALL_EVT IE
  ON IE.DEVICE_CONFIG_ID = MC.DEVICE_CONFIG_ID
JOIN CISADM.D1_SP SP
  ON SP.D1_SP_ID = IE.D1_SP_ID
WHERE SP.DIVISION_CD = :client_id
  AND M.MSRMT_DTTM >= :start_ts
  AND M.MSRMT_DTTM <  :end_ts
GROUP BY
    SP.DIVISION_CD,
    SP.D1_SP_ID,
    MC.MEASR_COMP_ID,
    TRUNC(M.MSRMT_DTTM, 'HH24')
ORDER BY
    READING_HOUR,
    MC.MEASR_COMP_ID;

--------------------------------------------------------------------------------
-- Explain plan + xplan inspection
--------------------------------------------------------------------------------
EXPLAIN PLAN FOR
SELECT
    SP.DIVISION_CD AS CLIENT_ID,
    SP.D1_SP_ID,
    MC.MEASR_COMP_ID,
    TRUNC(M.MSRMT_DTTM, 'HH24') AS READING_HOUR,
    SUM(NVL(M.READING_VAL, NVL(M.MSRMT_VAL, 0))) AS TOTAL_READING_VALUE,
    COUNT(*) AS READING_COUNT
FROM CISADM.D1_MSRMT M
JOIN CISADM.D1_MEASR_COMP MC
  ON MC.MEASR_COMP_ID = M.MEASR_COMP_ID
JOIN CISADM.D1_INSTALL_EVT IE
  ON IE.DEVICE_CONFIG_ID = MC.DEVICE_CONFIG_ID
JOIN CISADM.D1_SP SP
  ON SP.D1_SP_ID = IE.D1_SP_ID
WHERE SP.DIVISION_CD = :client_id
  AND M.MSRMT_DTTM >= :start_ts
  AND M.MSRMT_DTTM <  :end_ts
GROUP BY
    SP.DIVISION_CD,
    SP.D1_SP_ID,
    MC.MEASR_COMP_ID,
    TRUNC(M.MSRMT_DTTM, 'HH24');

SELECT *
FROM TABLE(DBMS_XPLAN.DISPLAY(NULL, NULL, 'BASIC +PREDICATE +ALIAS +NOTE +PARTITION'));

--------------------------------------------------------------------------------
-- Optional index recommendations (evaluate in DEV/QA first)
--------------------------------------------------------------------------------
-- 1) D1_MSRMT: local index aligned to partition key for pruning + join to measuring component
-- CREATE INDEX IX_D1_MSRMT_DTTM_MC
--   ON CISADM.D1_MSRMT (MSRMT_DTTM, MEASR_COMP_ID)
--   LOCAL;
--
-- 2) D1_MEASR_COMP: join accelerator from MSRMT to install events
-- CREATE INDEX IX_D1_MEASR_COMP_CFG_MC
--   ON CISADM.D1_MEASR_COMP (DEVICE_CONFIG_ID, MEASR_COMP_ID);
--
-- 3) D1_INSTALL_EVT: device config to service point link + date filter
-- CREATE INDEX IX_D1_INSTALL_EVT_CFG_SP
--   ON CISADM.D1_INSTALL_EVT (DEVICE_CONFIG_ID, D1_SP_ID, D1_INSTALL_DTTM);
--
-- 4) D1_SP: tenant/division filter
-- CREATE INDEX IX_D1_SP_DIVISION
--   ON CISADM.D1_SP (DIVISION_CD, D1_SP_ID);
--
-- If global reporting predicates dominate across many partitions, evaluate a GLOBAL index
-- tradeoff versus LOCAL (DML maintenance vs cross-partition query speed).

--------------------------------------------------------------------------------
-- Smoke dataset for staging validation (5-20 rows)
--------------------------------------------------------------------------------
-- Assumes staging schema objects:
--   STG_D1_MSRMT (CLIENT_ID, D1_SP_ID, MEASR_COMP_ID, MSRMT_DTTM, READING_VAL)
--
-- INSERT INTO STG_D1_MSRMT (CLIENT_ID, D1_SP_ID, MEASR_COMP_ID, MSRMT_DTTM, READING_VAL)
-- SELECT :client_id,
--        800000 + MOD(LEVEL, 5),
--        900000 + LEVEL,
--        CAST(:start_ts AS DATE) + (LEVEL / 24),
--        1.25 + MOD(LEVEL, 5)
-- FROM DUAL CONNECT BY LEVEL <= 12;
--
-- COMMIT;
