# CISADM view DDL export (demo)

- **Schema:** `CISADM`
- **Exported:** 2026-06-18 19:32:55 UTC
- **Views:** 282
- **Succeeded:** 282
- **Failed:** 0

## Files

| Path | Description |
| --- | --- |
| `index.csv` | View inventory with file paths |
| `all_views_ddl.sql` | Combined `CREATE OR REPLACE VIEW` statements |
| `ddl/<VIEW_NAME>.sql` | Full DDL per view |
| `view_select_logic/<VIEW_NAME>.sql` | SELECT logic only (after `AS`) |

## Regenerate

```bash
python3 scripts/local/export_cisadm_view_ddl.py --client demo
```
