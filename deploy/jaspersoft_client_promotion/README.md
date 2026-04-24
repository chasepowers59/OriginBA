# Jaspersoft Client Promotion Staging

Use this folder to stage DEV export ZIPs and target datasource exports before
running the client promotion pipeline in `scripts/jaspersoft/`.

This staging area is for Jaspersoft repository package movement only.

It is not part of:

- DB procedure deployment
- SQL validation
- snapshot refresh operations
- Domain build engineering

Tracked contents here are templates and folder scaffolding only.

Do not commit:

- raw client export ZIPs
- target datasource export ZIPs
- prepared import ZIPs
- temporary working folders

Use:

- `incoming_exports/` for untouched source export ZIPs from Jaspersoft Server
- `incoming_datasources/` for one target datasource export ZIP or extracted
  folder per client org
- `prepared_imports/` for final rewritten import ZIPs
- `prepared_imports/_tmp/` for transient script workspaces
- `archive/` for original DEV export ZIPs after successful preparation
- `client_org_mapping.csv` for target org to datasource mapping
