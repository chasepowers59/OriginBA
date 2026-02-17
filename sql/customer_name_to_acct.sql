-- GOVERNED: Validated Customer Name to ACCT_ID mapping (live production source).
-- Resolves human names to billing accounts via CI_PER_NAME and CI_ACCT_PER. INNER JOIN
-- ensures only accounts linked to a matching person are returned; no row = "No Data".
--
-- Parameter: :customer_name (VARCHAR2) - full or partial name (e.g. "Olivia Powers").
-- Return: up to 5 rows with ACCT_ID, ENTITY_NAME, PER_ID. Guardrail ROWNUM <= 5 limits broad searches.
--
-- Table choice: CI_PER_NAME = source of truth for person names; CI_ACCT_PER = account-person link.
-- PRIM_NAME_SW = 'Y' targets primary name only. MAIN_CUST_SW = 'Y' targets primary account holder.
-- If your schema uses FULL_NAME or NAME instead of ENTITY_NAME, adjust the WHERE clause.
-- If ENTITY_NAME_UPR is not present, use UPPER(ENTITY_NAME) LIKE '%' || UPPER(:customer_name) || '%'.

SELECT DISTINCT AP.ACCT_ID, PN.ENTITY_NAME, PN.PER_ID
FROM CISADM.CI_PER_NAME PN
INNER JOIN CISADM.CI_ACCT_PER AP ON PN.PER_ID = AP.PER_ID
WHERE PN.ENTITY_NAME_UPR LIKE '%' || UPPER(TRIM(:customer_name)) || '%'
  AND PN.PRIM_NAME_SW = 'Y'
  AND AP.MAIN_CUST_SW = 'Y'
  AND ROWNUM <= 5;
