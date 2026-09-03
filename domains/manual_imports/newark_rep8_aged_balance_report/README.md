# Newark REP8 — JRS deploy (client tenant)

**Status:** Import validated on Newark1 TEST (2026-09-02). Report loads from `JRS2C2M.REP8_AGED_BALANCE` staging table.

## Import zip

Rebuild:

```bash
python3 scripts/jaspersoft/build_newark_rep8_report_import.py
```

Import while logged into **Newark1**:

1. Repository → Import → **`REP8_Aged_Balance_staging_client_import.zip`**
2. Overwrite when prompted.

### What worked (tenant-relative Standard Offering layout)

- `index.xml`: `/DataSource/Newark1_DS` → public template → **folder** `/SmartCity/Report/Workstreams/Debt_Management` — **no** `rootTenantId`
- Zip paths match folder URI exactly (`Workstreams/Debt_Management`, not `Standard_Offering`)
- Includes: DS, `Report_Date`, public dashboard template, patched `main_jrxml.data`
- Excludes: `favorites/`, `organizations/...`, `rootTenantId`

Full playbook: [docs/jaspersoft_client_tenant_report_import.md](../../../docs/jaspersoft_client_tenant_report_import.md)

Skill: `.claude/skills/jaspersoft-client-tenant-import/SKILL.md`

## Database staging

Nightly table: `CISADM.NEWARK_REP8_AGED_BALANCE` (synonym/view: `JRS2C2M.REP8_AGED_BALANCE`)

```bash
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --file sql/clients/newark/rep8_aged_balance/09_run_refresh.sql
```

See `sql/clients/newark/rep8_aged_balance/README.md`.

## Studio fallback

`REP8_Aged_Balance_staging_publish.jrxml` → publish to `/SmartCity/Report/Workstreams/Debt_Management/REP8_Aged_Balance`.

## Troubleshooting run failures

| Symptom | Likely cause |
|---------|----------------|
| `no.such.export.process` on open | Export job died immediately — often **broken JRXML** on server (re-import fixed zip) or stale browser tab polling old task UUID |
| Spinner then same UUID error | Close tab, incognito, re-run; if new UUID still fails, re-import |

Rebuild after JRXML fixes:

```bash
python3 scripts/jaspersoft/build_newark_rep8_report_import.py
```

## Failed approaches (do not retry)

| Approach | Why it failed |
|----------|----------------|
| `rootTenantId=Newark1` at server root | `import.organization.into.root.not.allowed` inside tenant |
| Report-only zip (no DS) | `Reference resource Newark1_DS not found` |
| `promote_tenant_root_export_light_touch` | Moved report to `Standard_Offering`; index still said `Workstreams` |
| Stale `favorites/` from source export | Contributed to import instability |
