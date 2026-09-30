# Newark REP8 Aged Balance — Ad Hoc Domain

Flat domain over **`JRS2C2M.REP8_AGED_BALANCE`** (nightly staging, account grain).

## Canonical schema (import-validated Newark1)

**Source of truth:** [`schema.reference.xml`](schema.reference.xml)

Do not regenerate schema structure from scratch — edit `schema.reference.xml` only, then rebuild the zip.

### Field naming (important)

| Domain field | Correct meaning |
|---|---|
| `COLL_CL_CD` / `COLL_CL_DESC` | **Collection class** |
| `STATUS` | Legacy alias of collection class code (not account active/inactive) |
| `CUST_CL_CD` / `CUST_CL_DESC` | **Customer class** |
| `HAS_ACTIVE_SA` / `INACTIVE_ONLY_SW` / `SA_STATUS_SUMMARY` | Active vs inactive SA rollup (`ACTIVE` / `INACTIVE` / `MIXED` / `NONE`) |
| `ZIP_CODE` | Billing ZIP |
| `SERVICE_ADDRESS_ZIP_CODE` | Service premise ZIP |

Filter inactive accounts with `INACTIVE_ONLY_SW = 'Y'` or `SA_STATUS_SUMMARY = 'INACTIVE'`.

### What a working flat domain schema looks like

| Rule | Example |
|------|---------|
| Flat `jdbcTable` only | `REP8_AGED_BALANCE` on `JRS2C2M` — **no** `JoinTree_1`, **no** joins |
| `itemGroups` with nested `items` | Business folders under Account Identification, Property, Parcel, Billing, Amounts, Dates |
| **Not** root-level `<items>` | Root `<items>` is JRS **export** shape; import needs `<itemGroups>` |
| `schemaMap` | `JRS2C2M` + `defaultSchema` only |
| Group labels with `&` | Use `&amp;` in XML (`Property &amp; Service Location`) |
| Import zip `index.xml` | Domain resource only — no datasource overlay in the same zip |

### Failed approaches (do not repeat)

- Join-tree / live `CI_FT` SQL domain (`newark_account_aged_balance/`)
- Root `<items>` list (parsed on export, fails on import)
- Single monolithic `itemGroup` or alphabetized flat items
- Report-style import zip (`folder` + `Newark1_DS` in `index.xml`)
- `CISADM` in `schemaMap` when table is `JRS2C2M.REP8_AGED_BALANCE`

## Import

1. Log into **Newark1**
2. Delete any broken prior import of this domain (or overwrite)
3. Repository → Import → **`Newark_REP8_Aged_Balance_Domain_client_import.zip`**
4. Requires existing `/DataSource/Newark1_DS`

## Rebuild zip from canonical schema

```bash
python3 scripts/jaspersoft/build_newark_rep8_staging_domain_import.py
python3 scripts/jaspersoft/validate_domain_schema.py \
  domains/manual_imports/newark_rep8_aged_balance_domain/schema.reference.xml
```

## Ad Hoc

1. **Create → Ad Hoc View**
2. Domain: **Newark REP8 Aged Balance - Domain**
3. Fields under **Aged Balance (REP8)** — grouped folders
4. Filter **Report Date** for the `rpt_dt` slice
5. Optional: filter **Inactive Account Indicator** = `Y` for inactive-only lists

## Database

`sql/clients/newark/rep8_aged_balance/README.md` — refresh via `CISADM.REFRESH_NEWARK_REP8_AGED_BALANCE`.
