# Fond du Lac asset domain: the empty "Current Location/Organization ID"

Ticket (2026-09-18): in the Ad Hoc view `FDLWU_Meter_View_ALL_RES_MTRs`, meter 52222349 shows
`CURRENT_DISPOSITION = IN-INSTALLED`, `CURRENT_DISP_DT = 10/28/25` and an empty
`CURRENT_LOC_ORG_ID`, while C2M shows the meter installed at 600 LUCO RD (current disposition
dated 10-20-2025 9:05).

## Root cause

The domain's derived table `SC_CURRENT_DISPOSITION` picks, per asset, the `W1_ASSET_NODE` row
with the latest `EFF_DTTM` not after today. The report column reads that row's `CURR_NODE_ID`
("Current Location/Organization ID"). But `CURR_NODE_ID` (with `CURR_ASSET_ID`) is the
application's own marker of THE current row: measured on Ellensburg, exactly one row per asset
carries it and every history row has it null, while `NODE_ID` is filled on every row. So the
column is empty precisely when the latest-dated row is not the row the application calls
current. That is this meter: the domain found a row dated 10/28/25 that C2M does not treat as
the current disposition (its disposition history ends 10-20-2025), so the row's `CURR_NODE_ID`
is null and the location vanishes, while the disposition and date print from that same row.

## The fix (no ids, names, labels or joins change)

Only the derived table's SQL changes: prefer the row the application marks current, fall back
to the latest effective row for assets that have no marker.

```sql
SELECT AN.* FROM CISADM.W1_ASSET_NODE AN
WHERE AN.EFF_DTTM = (SELECT COALESCE(MAX(CASE WHEN AN2.CURR_ASSET_ID IS NOT NULL THEN AN2.EFF_DTTM END),
                                     MAX(CASE WHEN AN2.EFF_DTTM <= SYSDATE THEN AN2.EFF_DTTM END))
                     FROM CISADM.W1_ASSET_NODE AN2 WHERE AN2.ASSET_ID = AN.ASSET_ID)
```

`schema.fixed.xml` is `schema.original.xml` with exactly that query replaced (four lines differ;
every field id, item id, label and join is byte-identical), so every report and Ad Hoc view on
the domain keeps working. On real Ellensburg rows plus one fabricated later-dated non-current
row, the legacy query returned 579 locations for 580 assets and the fixed one 580, one row per
asset.

## Import the fixed COPY (does not touch the original)

`FDL_Asset_Domain_Fixed_import.zip` (also in `~/Downloads/`) creates a second domain,
`/SmartCity/Report/FDL_Asset/SC_Asset_Domain_Fixed`, labelled "FDL Asset Domain (Fixed)", on
`FondDuLac_DS`, with the fixed schema. Same single-resource package shape as the Newark SA 360
bundle that imported cleanly. Logged into the Fond du Lac org: Repository > Import > the zip.
Then build a test Ad Hoc view on the copy (or Save As the ticket's view onto it) and check meter
52222349: disposition dated 10-20-2025, location 600 LUCO RD's service point.

Existing reports keep pointing at the ORIGINAL domain. Once the copy proves out, either replace
the original's derived-table query in the Domain Designer (same four lines; ids unchanged, so
nothing rebinds) or repoint the views. The copy is the proof, not the deployment.

## Apply

1. Run `validate_current_disposition.sql` on the Fond du Lac instance (read only). Query 1 shows
   the meter's rows and which one carries `CURR_ASSET_ID`; query 2 counts every asset the legacy
   rule gets wrong; query 3 proves the fixed rule answers all of them.
2. In the Fond du Lac org, open the domain in the Domain Designer, replace the
   `SC_CURRENT_DISPOSITION` derived-table query with the one above (or upload
   `schema.fixed.xml`), save.
3. Re-run the Ad Hoc view: `CURRENT_DISP_DT` should now read the disposition C2M shows and
   `CURRENT_LOC_ORG_ID` the service point.

## Also worth knowing

The join `W1_ASSET_NODE.NODE_ID == SC_SP_EQUIPMENT.ID_VALUE` runs on the RAW history table, so
service-point columns (SPID, PREM_ADDR, PIN) come from every placement row a meter ever had, not
from its current one. It does not cause this ticket, but a meter that moved between service
points will show more than one row or the wrong point there.
