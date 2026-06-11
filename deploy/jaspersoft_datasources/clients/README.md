# SmartCity client JDBC datasource exports

Canonical Jaspersoft datasource exports for the six test clients. Each folder is
a full server export (org-tree layout) used by the promotion pipeline to inject
`<Client>_DS.xml` with the correct JDBC URL, user, and encrypted password.

| Folder | Client org | JDBC service (from export) |
| --- | --- | --- |
| `Ellensburg_DS/` | Ellensburg | `ptestdb_ellensburg...` |
| `CityCorp_DS/` | CityCorp | `ptestdb_citycorp...` |
| `CollegeStation_DS/` | College_Station | `ptestdb_collegestation...` |
| `FondDuLac_DS/` | Fond_Du_Lac | `ptestdb_fonddulac...` |
| `Newark1_DS/` | Newark1 | `ptestdb_newark...` |
| `Odessa_DS/` | Odessa | `pdevdb_odessa...` |

Original ZIP backups (same content): `deploy/EllensburgDS.zip`, `deploy/CityCorpDS.zip`, etc.

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
