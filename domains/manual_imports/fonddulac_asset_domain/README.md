# Fond du Lac asset domain: the empty "Current Location/Organization ID"

Ticket (2026-09-18): in the Ad Hoc view `FDLWU_Meter_View_ALL_RES_MTRs`, meter 52222349 shows
`CURRENT_DISPOSITION = IN-INSTALLED` with an empty `CURRENT_LOC_ORG_ID`, while C2M shows the
meter installed at 600 LUCO RD (disposition history: 11-04-2016 Installed, 10-20-2025 09:00 In
Store, 10-20-2025 09:05 Installed).

## Root cause (measured on the Fond du Lac TEST instance)

`W1_ASSET_NODE` is the placement history, one row per asset and effective date. The domain's
derived table `SC_CURRENT_DISPOSITION` takes the latest-dated row, which is exactly what C2M's
Disposition History calls current, and that part is right. The report column "Current
Location/Organization ID" reads that row's `CURR_NODE_ID`. But `CURR_NODE_ID` (with
`CURR_ASSET_ID`) is a "current" pointer the application maintains on one row per asset, and on
this meter the pointer stayed on the 09:00 In Store row when the 09:05 re-install was recorded:

| effective | disposition | NODE_ID | CURR_NODE_ID |
| --- | --- | --- | --- |
| 2016-11-04 | IN-INSTALLED | 062867200600 | null |
| 2025-10-20 09:00 | NI-INSTORE | 918551807362 | 918551807362 |
| 2025-10-20 09:05 | IN-INSTALLED | 062867200600 | null |

So the latest row carries the location in `NODE_ID` (062867200600 is the 600 LUCO RD service
point) and nothing in `CURR_NODE_ID`. `NODE_ID` is filled on all 43,600 latest rows; the pointer is
stale on 2 (serials 52222349 and 20160346, both re-installed minutes after an In Store entry).

The first attempt (select by the pointer) was wrong: it made those two meters read as In Store.
Recorded here so it is not tried again.

## The fix (no ids, names, labels or joins change)

Keep the latest row; fall back to the plain columns when the pointer is empty:

```sql
SELECT AN.ASSET_ID, AN.EFF_DTTM, AN.ASSET_DPOS_FLG, AN.NODE_ID, AN.ATTCH_TO_ASSET_ID, AN.BO_DATA_AREA, AN.VERSION,
       NVL(AN.CURR_ASSET_ID, AN.ASSET_ID) AS CURR_ASSET_ID,
       NVL(AN.CURR_NODE_ID, AN.NODE_ID) AS CURR_NODE_ID,
       NVL(AN.CURR_ATTCH_TO_ASSET_ID, AN.ATTCH_TO_ASSET_ID) AS CURR_ATTCH_TO_ASSET_ID,
       AN.FAILURE_FLG, AN.ACT_ID
FROM CISADM.W1_ASSET_NODE AN
WHERE AN.EFF_DTTM = (SELECT MAX(AN2.EFF_DTTM) FROM CISADM.W1_ASSET_NODE AN2 WHERE AN2.ASSET_ID = AN.ASSET_ID AND AN2.EFF_DTTM <= SYSDATE)
```

Proven on TEST: 43,600 assets, one row each, a location on every one; meter 52222349 answers
`IN-INSTALLED 2025-10-20 09:05 at 062867200600` where the legacy query answers `(empty)`.

## Import the fixed COPY (does not touch the original)

`FDL_Asset_Domain_Fixed_import.zip` (also in `~/Downloads/`) creates or overwrites
`/SmartCity/Report/FDL_Asset/SC_Asset_Domain_Fixed`, "FDL Asset Domain (Fixed)", on
`FondDuLac_DS`. Logged into the Fond du Lac org: Repository > Import > the zip, overwrite. A view
saved onto it shows meter 52222349 installed at 600 LUCO RD's service point.

Existing reports keep pointing at the ORIGINAL domain. Once the copy proves out, paste the same
query into the original's `SC_CURRENT_DISPOSITION` derived table in the Domain Designer; the
ids are unchanged, so nothing rebinds.

## Also worth knowing

The join `W1_ASSET_NODE.NODE_ID == SC_SP_EQUIPMENT.ID_VALUE` runs on the RAW history table, so
service-point columns (SPID, PREM_ADDR, PIN) come from every placement row a meter ever had, not
its current one. Not this ticket, but a meter that moved between service points will show more
than one row or the wrong point there.
