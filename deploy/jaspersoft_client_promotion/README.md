# Jaspersoft Client Promotion Staging

Prepare Standard Offering import ZIPs for all six SmartCity test clients.

## Canonical client datasources (committed)

Full JDBC exports live in:

`deploy/jaspersoft_datasources/clients/`

Each client gets its own `{Client}_DS.xml` injected into the import package —
not a rename of `Origin_DEV_DS`.

## Patch VEE Exception To Do joins first

The shipped VEE Exception domain inner-joins the To Do chain
(`CI_TD_DRLKEY` / `CI_TD_DRLKEY_TY` / `CI_TD_ENTRY` and its lookups) onto
`D1_INIT_MSRMT_DATA`. Clients without IMD To Do entries lose the whole
exception population as soon as an Ad Hoc view selects a To Do field
(Newark TEST: 475,842 exceptions to 0 rows). Relax them before building:

```bash
python3 scripts/jaspersoft/patch_vee_exception_todo_joins.py \
  --source "/path/to/standard offering.zip" \
  --output "/path/to/standard offering_vee_todo_leftouter.zip"
```

Then use the patched ZIP as `--source-zip` below.

## Build all client packages

```bash
python3 scripts/jaspersoft/run_client_standard_offering_pipeline.py \
  --source-zip "/path/to/standard offering.zip" \
  --skip-archive
```

One client only:

```bash
python3 scripts/jaspersoft/run_client_standard_offering_pipeline.py \
  --source-zip "/path/to/standard offering.zip" \
  --clients Ellensburg \
  --skip-archive
```

Outputs:

`prepared_imports/<Client>_Standard_Offering_import.zip`

## Import

Log into each **client tenant** → **Repository** → Import the matching ZIP.
Do not import from server root (same rule as Origin_STAGE / Origin_DEV).

## Mapping

`client_org_mapping.csv` — org resource ID → datasource alias.

## Folder layout

- `incoming_datasources/` — optional drop zone for refreshed ZIP exports (gitignored)
- `prepared_imports/` — generated import ZIPs (gitignored)
- `archive/` — source exports after successful batch (gitignored)

See [jaspersoft_client_promotion_pipeline.md](/Users/chase/OriginBA-3/docs/jaspersoft_client_promotion_pipeline.md).
