# Fond du Lac asset domain: the empty "Current Location/Organization ID"

Ticket (2026-09-18): in the Ad Hoc view `FDLWU_Meter_View_ALL_RES_MTRs`, meter 52222349 shows
`CURRENT_DISPOSITION = IN-INSTALLED` with an empty `CURRENT_LOC_ORG_ID`, while C2M shows the
meter installed at 600 LUCO RD.

## What is actually happening (measured on Fond du Lac TEST and PROD, same rows on both)

`W1_ASSET_NODE` is the asset's placement history. Meter 52222349 has three rows:

| effective | disposition | NODE_ID | CURR_NODE_ID (the app's "current" pointer) |
| --- | --- | --- | --- |
| 2016-11-04 | IN-INSTALLED | 062867200600 (600 LUCO RD) | null |
| 2025-10-20 09:00 | NI-INSTORE | 918551807362 (Mobile Stock) | 918551807362 |
| 2025-10-20 09:05 | IN-INSTALLED | 062867200600 | null |

When the meter was re-installed five minutes after the In Store entry, C2M left its "current"
pointer on the In Store row. That is C2M data, not ours, and it is rare: 2 of 16,672 installed
smart meters (serials 52222349 and 20160346). But the domain and the view both lean on that
pointer, which is our side:

1. The view's `CURRENT_LOC_ORG_ID` column is the RAW `W1_ASSET_NODE.CURR_NODE_ID`, and its
   filter_3 is `CURR_NODE_ID not equal (null)`. For every normal meter that filter keeps exactly
   the pointer row; for this meter it keeps the In Store row, whose node is not a service point,
   so every service-point column (PREM_ID, PREM_ADDR, PIN, MTR_SITE_ID, SP_TYPE) goes blank and
   the location shows Mobile Stock. That is what you saw after the derived-table change: the
   view's own pointer filter, not the change.
2. The domain joins the service-point tables from the RAW placement history
   (`W1_ASSET_NODE.NODE_ID == SC_SP_EQUIPMENT.ID_VALUE`), so every placement a meter ever had
   contributes a row: 16,672 installed meters become 20,541 meter-premise rows. The view's
   pointer filter is what was hiding that fan-out.

Two earlier attempts are recorded so they are not repeated: selecting the current placement BY
the pointer showed those meters as In Store (wrong); fixing only the derived table's location
left the view's pointer filter picking the In Store row.

## The fix, v3 (no ids, names or labels change; two joins and one query)

Derived table `SC_CURRENT_DISPOSITION`: keep the latest-dated row (what C2M's Disposition
History shows), fall back to the plain columns when the pointer is empty:

```sql
SELECT AN.ASSET_ID, AN.EFF_DTTM, AN.ASSET_DPOS_FLG, AN.NODE_ID, AN.ATTCH_TO_ASSET_ID, AN.BO_DATA_AREA, AN.VERSION,
       NVL(AN.CURR_ASSET_ID, AN.ASSET_ID) AS CURR_ASSET_ID,
       NVL(AN.CURR_NODE_ID, AN.NODE_ID) AS CURR_NODE_ID,
       NVL(AN.CURR_ATTCH_TO_ASSET_ID, AN.ATTCH_TO_ASSET_ID) AS CURR_ATTCH_TO_ASSET_ID,
       AN.FAILURE_FLG, AN.ACT_ID
FROM CISADM.W1_ASSET_NODE AN
WHERE AN.EFF_DTTM = (SELECT MAX(AN2.EFF_DTTM) FROM CISADM.W1_ASSET_NODE AN2 WHERE AN2.ASSET_ID = AN.ASSET_ID AND AN2.EFF_DTTM <= SYSDATE)
```

Join: the service-point tables hang off the current placement, not the history:

```
SC_CURRENT_DISPOSITION.NODE_ID == SC_SP_EQUIPMENT.ID_VALUE   (was W1_ASSET_NODE.NODE_ID == ...)
```

Proven on the TEST org (copy imported as `SC_Asset_Domain_Fixed`), every installed smart meter:

| | original | v3 |
| --- | ---: | ---: |
| installed smart meters | 16,672 | 16,672 |
| meter x premise rows | 20,541 | 16,672 |
| meters with no location | 2 | 0 |

Meter 52222349 on v3: `IN-INSTALLED`, location 062867200600, 600 LUCO RD, PIN
FDL-15-17-02-41-154-00, meter site 536-WT-000, cycle 03, WT-RES.

## Files

- `FDL_Asset_Domain_Fixed_PROD_import.zip` (also in `~/Downloads/`): the copy for the PROD org,
  in the server's own org-export shape, with prod's own `FondDuLac_DS` export of 2026-09-18
  listed first so the reference resolves (it re-saves the datasource with its own bytes; the
  TEST run proved URL, user and driver untouched). Import inside the Fond du Lac org.
- `FDL_Asset_Domain_Fixed_TEST_import.zip`: the same for TEST (already imported there).
- `schema.fixed.xml`: v3 schema, to paste into the ORIGINAL through the Domain Designer once the
  copy proves out (`schema.original.xml` beside it; `diff` shows the query and the one join).
- `validate_current_disposition.sql`: read-only checks for the instance.

## The two view edits (needed on every view that uses the pointer)

1. Replace the `CURRENT_LOC_ORG_ID` column: use "Current Location/Organization ID" from the
   `SC_CURRENT_DISPOSITION` set, not from `W1_ASSET_NODE`.
2. Delete filter_3 (`Current Location/Organization ID` from W1_ASSET_NODE "is not equal to" blank).
   With v3 the meter is already one row; the filter only reintroduces the pointer.
