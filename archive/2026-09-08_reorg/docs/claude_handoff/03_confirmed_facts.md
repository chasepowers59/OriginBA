# 03 — Confirmed facts log

Cite as: **confirmed via Cursor on &lt;date&gt; / `--client &lt;alias&gt;`**.

## 2026-08-10 — Balance-forward (multi-client)

Checked reachable TEST/internal DBs: all `CI_CUST_CL.OPEN_ITEM_SW = 'N'`, `CI_MATCH_EVT` row count 0, FT `MATCH_EVT_ID` blank where scanned.

Debt/paid logic = ARS rules, **not** open-item match events.

## 2026-08-11 — Origin DEV (`int_dev`) session

### Environment
- `DB_NAME`: PDEVDB_DEMO
- `SERVICE_NAME`: pdevdb_demo.devprivatesn.devvcn.oraclevcn.com
- `USER`: CPOWERS

### SA_STATUS_FLG (lookup + live distribution)

| Value | Meaning | SA count (int_dev) |
|-------|---------|---------------------|
| 05 | Incomplete | — |
| 10 | Pending Start | 5 |
| **20** | **Active** | **1249** |
| 30 | Pending Stop | — |
| 40 | Stopped | 8 |
| 45 | *(no ENG lookup)* | 5 |
| 50 | Reactivated | — |
| 60 | Closed | 330 |
| 70 | Canceled | 11 |

### Other ENG lookups (abbreviated)

- `BILL_STAT_FLG`: C=Complete, P=Pending
- `BSEG_STAT_FLG`: 10 Incomplete … 50 Frozen … 60 Canceled … 70 OK
- `FT_TYPE_FLG`: BS/BX, PS/PX, AD/AX
- `GL_DISTRIB_STATUS`: D Distributed, G Generated, M Modified, N Pending
- `PAY_STATUS_FLG` / `ADJ_STATUS_FLG`: 10/20/30/50/60 pattern (Frozen=50)
- `FREEZE_SW` / `REDUNDANT_SW`: **not** in `ci_lookup_val_l` under those names — treat as Y/N switches

### Active 7 snapshots present on int_dev

| Table | approx_rows |
|-------|-------------|
| BSEG_BILLED_USAGE_RPT_CURR | 19646 |
| BSEG_SQ_USAGE_RPT_CURR | 19021 |
| D1_MSRMT_RPT_CURR | 28959 |
| D1_USAGE_RPT_CURR | 95 |
| D1_USAGE_SCALAR_DTL_RPT_CURR | 128 |
| FT_GL_DISTRIBUTION_RPT_CURR | 214 |
| FT_RPT_CURR | 55320 |

## CHAR padding rule (permanent)

C2M CHAR columns are space-padded. Always:

```sql
NULLIF(TRIM(flag_col), '') = 'xx'
```

## Device / Ad Hoc performance (Newark lesson)

- Heavy path: `CMS_DVC_ACCT` (device → install → SP id → SA/account)
- Fast path: Distinct Device ID + latest effective config + latest install; avoid SA Status unless required
