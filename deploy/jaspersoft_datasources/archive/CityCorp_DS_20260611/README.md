# CityCorp_DS datasource refresh (2026-06-11)

Source export: `CityCorp_DS_export.zip` (from Jaspersoft tenant **CityCorp**).

## Connection change

| Field | Previous | Updated |
| --- | --- | --- |
| JDBC URL | `jdbc:oracle:thin:@10.13.4.91:1521/ptestdb_citycorp...` | `jdbc:oracle:thin:@//10.13.4.91:1521/ptestdb_citycorp...` |
| Version | 55 | 58 |
| Encrypted password | rotated | matches new export |

Canonical copy updated at:

`deploy/jaspersoft_datasources/clients/CityCorp_DS/`

Backup ZIP regenerated:

`deploy/CityCorpDS.zip`

## Rebuild client import package

```bash
python3 scripts/jaspersoft/run_client_standard_offering_pipeline.py \
  --source-zip "/path/to/standard offering.zip" \
  --clients CityCorp \
  --skip-archive
```

Import inside the **CityCorp** tenant:

`deploy/jaspersoft_client_promotion/prepared_imports/CityCorp_Standard_Offering_import.zip`
