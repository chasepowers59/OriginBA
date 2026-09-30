# Device Service Point Snapshot

This folder is for the meter-operations device snapshot built from governed `D1_DVC` sources with current install, service-point, premise, usage-subscription, and asset context.

## Purpose

`CISADM.DEVICE_SP_RPT_CURR` is the standardized meter-operations snapshot for current device placement and asset linkage.

It consolidates legacy live-domain subjects into one governed device grain:
- `Device - Domain` (device header, identifiers, configuration, install event)
- `Asset - Domain` (asset header and identifier overlay via `CMS_D1_DVC_IDENTIFIER_VW.ASSET_ID`)

## Grain

One row per `D1_DVC_ID` (`D1_DVC.D1_DEVICE_ID`).

Natural key:
- `D1_DVC_ID`

## Driving truth

Device truth comes from `CISADM.D1_DVC`.

Current placement resolves through:
- effective `CISADM.D1_DVC_CFG` as of refresh time
- time-valid `CISADM.D1_INSTALL_EVT` for the effective configuration
- `CISADM.D1_SP`
- `CISADM.CI_SP` and `CISADM.CI_PREM` via `D1_INSTALL_EVT.D1_SP_ID = CI_SP.SP_ID`
- time-valid `CISADM.D1_US_SP` joined to `CISADM.D1_US` for the current service point

Asset truth is joined at device grain through:
- `CISADM.CMS_D1_DVC_IDENTIFIER_VW`
- `CISADM.W1_ASSET`
- `CISADM.CMS_W1_ASSET_IDENTIFIER_VW`

Install-event and configuration counts are pre-aggregated before join so the snapshot never inherits install-history fan-out.

## What is included

- device type, status, manufacturer, model, and lookup descriptions (`LANGUAGE_CD = 'ENG'`)
- device identifier overlay fields (serial, badge, external id, utility device id, asset id)
- lightweight asset header fields when the device is linked to `W1_ASSET`
- current effective configuration reference
- current install event and `CURRENTLY_INSTALLED_SW`
- current D1 service point, CIS service point, and premise context
- primary active usage subscription on the current service point
- `INSTALL_EVENT_COUNT`, `DEVICE_CONFIG_COUNT`, and `ACTIVE_US_LINK_COUNT`
- `LOAD_DTTM`

## What is intentionally excluded

- row-per-install-event detail
- row-per-device-event detail (`D1_DVC_EVT`)
- asset location / node hierarchy detail from `W1_ASSET_NODE` and `W1_NODE`
- activity workflow detail (`D1_ACTIVITY`, `W1_ASSET.ACT_ID` workflow joins)
- account / SA overlays from legacy device-domain fan-out paths

Those belong in lower-grain meter-operations or customer snapshots.

## Key design rules

- `D1_DVC_ID` is the only additive population key.
- Effective configuration is the latest `D1_DVC_CFG.EFF_DTTM` not after refresh time.
- Current install event uses the same time-valid single-row rule used in governed measurement snapshots.
- Usage subscription context resolves through time-valid `D1_US_SP`; only one primary `US_ID` is published per device row.
- Full-history deployment uses `02a_full_history_refresh_procedure.sql` (`TRUNCATE` + `INSERT`).
- Scheduled maintenance uses `02_refresh_snapshot_procedure.sql`, which:
  1. deletes dormant devices with no install/config activity in the retention window and not currently installed
  2. deletes and re-inserts the six-month refresh scope (recent device changes, install events, configurations, and currently installed devices)

## Recommended use

- installed-device inventory and placement reporting
- device-to-asset traceability at device grain
- current service point and premise context for field operations
- active usage-subscription lookup by installed device

## Do not use for

- install-event history analysis
- asset location / node hierarchy reporting
- device-event or activity workflow detail
- usage-transaction or measurement detail

Use separate lower-grain snapshots or live domains for those subjects.

## Workflow

1. Create the snapshot table with `01_create_snapshot_table.sql`.
2. Load full history once with `02a_full_history_refresh_procedure.sql`.
3. Deploy the rolling refresh procedure from `02_refresh_snapshot_procedure.sql`.
4. Validate row safety and aggregate parity with `04_validation_queries.sql`.

## Implemented snapshot

- `01_create_snapshot_table.sql`
- `02a_full_history_refresh_procedure.sql`
- `02_refresh_snapshot_procedure.sql`
- `04_validation_queries.sql`
