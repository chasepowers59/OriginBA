# Newark Account Aged Balance Domain (REP8 replacement)

Standalone Newark domain for REP8-style aged balance reporting. **Not** a patch of Standard Offering SA Snapshot — that approach produced invalid schema XML for JRS import.

## Root cause of prior import failures

1. **Invalid `<parameters>` block** inserted into schema (not part of schema v1.3).
2. **ElementTree re-serialization** of the 1,400-line SA Snapshot schema introduced self-closing tags JRS rejects.
3. **Join tree modeled as `jdbcQuery`** with a duplicated bucket SQL `<query>` block — JRS expects join trees as **`jdbcTable`** with `joinInfo` / `joinList` / `tableRefList` only (no `<query>` on the join tree).
4. **Malformed import `index.xml`** — resource path was outside `<module id="repositoryResources">`.

This package is generated from scratch with parser-safe derived SQL (`SELECT * FROM (...) X` wrappers) and validated by `scripts/jaspersoft/validate_domain_schema.py`.

## Import

1. Log into JRS as Newark tenant (`Newark1`).
2. Import `Newark_Account_Aged_Balance_Domain_import.zip` (repo or `~/Downloads`).
3. Target: `/SmartCity/Report/Workstreams/Debt_Management`
4. Requires `/DataSource/Newark1_DS`.
5. Delete any previously failed import of this domain before re-importing.

## Use

- **Join tree:** `JoinTree_1` — Newark Aged Balance (REP8)
- **Field group:** Newark Aged Balance (REP8)
- **As-of date:** Buckets use `TRUNC(SYSDATE)` at query time. **Report Date (As-Of)** exposes `RPT_DT`.
- For SA Snapshot Ad Hoc (Join Trees 1–2), continue using Standard Offering **SA Snapshot - Aged Balance** domain on the tenant.

## Rebuild

```bash
python3 scripts/jaspersoft/build_newark_account_aged_balance_domain.py
python3 scripts/jaspersoft/validate_domain_schema.py \
  domains/manual_imports/newark_account_aged_balance/Newark_Account_Aged_Balance___Domain_files/schema.data
```

## Legacy REP8 → Domain field mapping

| REP8 column | Domain field |
|-------------|----------------|
| Report Date | Report Date (As-Of) |
| ACCOUNT | Account |
| BLOCK_LOT / BLOCK / BLOCKSUF / LOT / LOTSUFF / QLFR / WARD | Newark premise char fields |
| STATUS | Status (Collection Class) |
| CYCLE | Bill Cycle |
| PROPERTY_DESCR | Property Description |
| SERVICE_LOCATION_NAME / SERVICE_ADDRESS / STREET_NAME | Service premise address |
| SERVICE_ADDRESS_ZIP_CODE | Service Zip |
| BILLING_NAME | Billing Name |
| BILLING_ADDRESS / CITY_STATE / ZIP_CODE | Mailing premise |
| BILLING_PHONE | Billing Phone |
| CURRENT_BAL | Current Balance |
| NEW_CHARGES | New Charges |
| ARREARS_30_PRINCIPAL / ARREARS_30_INTEREST / ARREARS_30 | 30-day bucket (LPC split + total) |
| ARREARS_60_* | 60-day bucket |
| ARREARS_90_* | 90-day bucket |
| ARREARS_TOTAL | Arrears Total |
| LATEST_PAY_DT | Latest Payment Date |
| PA_FLAG | Payment Arrangement Flag |

## Logic notes

- **LPC split:** `parent_id = 'LPC'` rows are interest; other debits are principal (OTC REP8_VW parity).
- **As-of:** `ARS_DT <= TRUNC(SYSDATE)`; bucket windows use today minus 30/60/90/120 days.
- **Credit offset:** `LEAST` / `GREATEST` rules match legacy REP8 JRXML.
- **No shared procedure changes:** does not modify `REFRESH_CMS_SA_SNAPSHOT`.
