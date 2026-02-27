# Deployment Compliance Checklist

## Pre-Deployment
1. Confirm review/approval status.
2. Enumerate all objects: reports, domains, dashboards, datasources, dependencies.
3. Backup target datasource and target objects.

## Packaging
1. Export changed objects only.
2. Use Legacy Key, include dependencies, include permissions, full resource paths.
3. If org names differ, replace org paths and datasource references globally in package.

## Import
1. Import mode: UPDATE only.
2. Verify import status success.
3. Re-import target datasource backup to preserve credentials/settings.

## Validation
1. Run report/ad hoc/dashboard smoke tests.
2. Verify create/update dates.
3. Confirm client isolation and datasource isolation.

## Closeout
1. Record deployment notes and validation evidence.
2. Archive package and logs under dated folder.
