-- find_bill_cycle_numbers.sql
-- Purpose: identify where bill cycle codes actually exist and list the values.
-- Safe: read-only diagnostics.

-- Date window used below (edit if needed):
-- START_DT = DATE '2020-01-01'
-- END_DT   = DATE '2025-12-31'

WITH params AS (
    SELECT
        DATE '2020-01-01' AS start_dt,
        DATE '2025-12-31' AS end_dt
    FROM dual
)
SELECT 'CI_BILL.BILL_CYC_CD' AS source_col,
       COUNT(*) AS total_rows,
       COUNT(CASE WHEN TRIM(B.BILL_CYC_CD) IS NOT NULL THEN 1 END) AS non_null_rows
FROM CISADM.CI_BILL B
CROSS JOIN params P
WHERE NVL(B.BILL_DT, B.CRE_DTTM) >= P.start_dt
  AND NVL(B.BILL_DT, B.CRE_DTTM) <  P.end_dt + 1
UNION ALL
SELECT 'CI_BSEG.BILL_CYC_CD' AS source_col,
       COUNT(*) AS total_rows,
       COUNT(CASE WHEN TRIM(S.BILL_CYC_CD) IS NOT NULL THEN 1 END) AS non_null_rows
FROM CISADM.CI_BSEG S
CROSS JOIN params P
WHERE NVL(S.END_DT, S.CRE_DTTM) >= P.start_dt
  AND NVL(S.END_DT, S.CRE_DTTM) <  P.end_dt + 1
UNION ALL
SELECT 'CI_ACCT.BILL_CYC_CD' AS source_col,
       COUNT(*) AS total_rows,
       COUNT(CASE WHEN TRIM(A.BILL_CYC_CD) IS NOT NULL THEN 1 END) AS non_null_rows
FROM CISADM.CI_ACCT A
UNION ALL
SELECT 'D1_USAGE.MSRMT_CYC_CD' AS source_col,
       COUNT(*) AS total_rows,
       COUNT(CASE WHEN TRIM(U.MSRMT_CYC_CD) IS NOT NULL THEN 1 END) AS non_null_rows
FROM CISADM.D1_USAGE U
CROSS JOIN params P
WHERE U.START_DTTM >= P.start_dt
  AND U.START_DTTM <  P.end_dt + 1
UNION ALL
SELECT 'D1_SP.MSRMT_CYC_CD' AS source_col,
       COUNT(*) AS total_rows,
       COUNT(CASE WHEN TRIM(SP.MSRMT_CYC_CD) IS NOT NULL THEN 1 END) AS non_null_rows
FROM CISADM.D1_SP SP
ORDER BY 1;

-- Top bill cycle values from CI_BSEG (most likely billing-side source when CI_BILL is null).
WITH params AS (
    SELECT
        DATE '2020-01-01' AS start_dt,
        DATE '2025-12-31' AS end_dt
    FROM dual
)
SELECT
    TRIM(S.BILL_CYC_CD) AS bill_cycle_code,
    COUNT(*) AS row_count
FROM CISADM.CI_BSEG S
CROSS JOIN params P
WHERE NVL(S.END_DT, S.CRE_DTTM) >= P.start_dt
  AND NVL(S.END_DT, S.CRE_DTTM) <  P.end_dt + 1
  AND TRIM(S.BILL_CYC_CD) IS NOT NULL
GROUP BY TRIM(S.BILL_CYC_CD)
ORDER BY COUNT(*) DESC, TRIM(S.BILL_CYC_CD);

-- Top bill cycle values from CI_BILL (for confirmation).
WITH params AS (
    SELECT
        DATE '2020-01-01' AS start_dt,
        DATE '2025-12-31' AS end_dt
    FROM dual
)
SELECT
    TRIM(B.BILL_CYC_CD) AS bill_cycle_code,
    COUNT(*) AS row_count
FROM CISADM.CI_BILL B
CROSS JOIN params P
WHERE NVL(B.BILL_DT, B.CRE_DTTM) >= P.start_dt
  AND NVL(B.BILL_DT, B.CRE_DTTM) <  P.end_dt + 1
  AND TRIM(B.BILL_CYC_CD) IS NOT NULL
GROUP BY TRIM(B.BILL_CYC_CD)
ORDER BY COUNT(*) DESC, TRIM(B.BILL_CYC_CD);

-- Map discovered cycle code to description table.
WITH cycle_codes AS (
    SELECT DISTINCT TRIM(S.BILL_CYC_CD) AS bill_cycle_code
    FROM CISADM.CI_BSEG S
    WHERE TRIM(S.BILL_CYC_CD) IS NOT NULL
    UNION
    SELECT DISTINCT TRIM(B.BILL_CYC_CD) AS bill_cycle_code
    FROM CISADM.CI_BILL B
    WHERE TRIM(B.BILL_CYC_CD) IS NOT NULL
)
SELECT
    C.bill_cycle_code,
    L.LANGUAGE_CD,
    L.DESCR
FROM cycle_codes C
LEFT JOIN CISADM.CI_BILL_CYC_L L
    ON TRIM(L.BILL_CYC_CD) = C.bill_cycle_code
   AND L.LANGUAGE_CD IN ('ENG', 'EN')
ORDER BY C.bill_cycle_code, L.LANGUAGE_CD;
