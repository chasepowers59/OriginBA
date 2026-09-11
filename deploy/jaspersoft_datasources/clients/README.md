# SmartCity client JDBC datasource exports

Canonical Jaspersoft datasource exports for the six test clients. Each folder is
a full server export (org-tree layout) used by the promotion pipeline to inject
`<Client>_DS.xml` with the correct JDBC URL, user, and encrypted password.

| Folder | Client org | JDBC service (from export) |
| --- | --- | --- |
| `Ellensburg_DS/` | Ellensburg | `ptestdb_ellensburg...` |
| `CityCorp_DS/` | CityCorp | `ptestdb_citycorp...` |
| `CityCorp_PROD_DS/` | CityCorp (PROD) | `PPRODDB_CITYCORP...` (tenant-root layout, DS name `CityCorp_DS`) |
| `CollegeStation_DS/` | College_Station | `PTESTDB_COLLEGESTATION...` (tenant-root `/DataSource`, host `smartcity-db-test-v1-2`) |
| `FondDuLac_DS/` | Fond_Du_Lac | `ptestdb_fonddulac...` |
| `Newark1_DS/` | Newark1 | `PTESTDB_NEWARK...` (tenant-root `/DataSource`, host `smartcity-db-test-v1-2`) |
| `Odessa_DS/` | Odessa | `pdevdb_odessa...` |

Original ZIP backups (same content) are archived under `archive/2026-09-08_reorg/deploy/` (2026-09-08); the unpacked folders here are the record.

Refresh from Jaspersoft: export `/DataSource/<Client>_DS` inside the client tenant and replace the matching folder here (or run `store_canonical_datasource_export.py` after adding the alias to allowed list).

Mapping file: `deploy/jaspersoft_client_promotion/client_org_mapping.csv`

Build all client Standard Offering import ZIPs:

```bash
python3 scripts/jaspersoft/run_client_standard_offering_pipeline.py \
  --source-zip "/path/to/standard offering.zip" \
  --skip-archive
```

Import **inside each client tenant** (Repository → Import):

`deploy/jaspersoft_client_promotion/prepared_imports/<Client>_Standard_Offering_import.zip`
\n\n## Names of record (2026-09-08)\n\nEach client's DataSource name is an attribute of its row in `~/originba_dbt/clients.yml` (`jaspersoft.ds_name`), which is what the promotion CSV is generated from. Odessa is recorded with two candidates (`Origin_DataVergence_DS`, the one the pipeline injects; `Odessa_DS`, documented above) and `ds_verified: false` until a read of the live tenant's `/DataSource` folder settles it; both folders stay until then. CityCorp PROD's folder is `CityCorp_PROD_DS/` while the DataSource it holds is named `CityCorp_DS` (tenant-root layout) -- recorded on the instance.\n