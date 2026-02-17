-- GOVERNED: Validated Address to ACCT_ID mapping (live production source).
-- Links physical location to accounts via CI_SA and CI_PREM. INNER JOIN ensures we only
-- return accounts with a matching premise; no row = "No Data" (not zero balance).
--
-- Parameter: :address (VARCHAR2) – partial or full address (e.g. "123 Main St").
-- Return: up to 5 rows with ACCT_ID, PREM_ID, ADDRESS1. Guardrail ROWNUM <= 5 limits broad searches.
--
-- Table choice: CI_PREM = premise/location source of truth; CI_SA = active service agreements.
-- CHAR_PREM_ID links SA to premise. SA_STATUS_FLG = '20' keeps scope aligned to governed active accounts.
-- If your schema uses PREM_ID instead of CHAR_PREM_ID, change join to SA.PREM_ID = P.PREM_ID.
-- If your schema uses ADDR_LINE_1 instead of ADDRESS1, adjust column names accordingly.

SELECT DISTINCT SA.ACCT_ID, P.PREM_ID, P.ADDRESS1
FROM CISADM.CI_PREM P
INNER JOIN CISADM.CI_SA SA ON P.PREM_ID = SA.CHAR_PREM_ID
WHERE (P.ADDRESS1_UPR LIKE '%' || UPPER(TRIM(:address)) || '%'
       OR P.ADDRESS1 LIKE '%' || TRIM(:address) || '%')
  AND NULLIF(TRIM(SA.SA_STATUS_FLG), '') = '20'
  AND ROWNUM <= 5;
