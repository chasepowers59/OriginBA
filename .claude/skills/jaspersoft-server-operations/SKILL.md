---
name: jaspersoft-server-operations
description: Operate the three SmartCity JasperReports Server environments (internal, test, prod) through the REST API - inventory and backup every organization into the repo, diff environments, deploy and promote report units and Standard Offering folders, and the standing safety rules (snapshot before, diff after, Origin_DEV by default, prod only on an explicit go). Use before ANY change to a Jaspersoft server, when asked what an environment or client contains, when promoting between environments, or when something on a server looks different from the repo.
---

# Jaspersoft server operations

## The estate (measured 2026-09-17; re-measure with `jrs_repository.py --env X whoami`)

| env | URL | what it holds |
| --- | --- | --- |
| `test` | https://smartcity-jrs-test.originsmartops.com/jasperserver-pro | JRS 10.0.0 PRO; one instance, every client an org under `organization_1`: Ellensburg, Fond_Du_Lac, CityCorp, College_Station, Odessa, Newark1, Origin_DEV, Origin_TEST |
| `prod` | https://smartcity-jrs.originsmartops.com/jasperserver-pro | **JRS 9.0.0 PRO (JRXML 6 model) until its 10.0 upgrade, due days after 2026-09-18** -- re-snapshot and diff right after. Org-scoped logins only (`user\|Org`): CityCorp, Ellensburg, Newark1, Fond_Du_Lac, College_Station; Odessa 401 with this account |
| `internal` | https://origin-c2m-demo.originsmartops.com:8443/jasperserver-pro | JRS 10.0.0 PRO; three orgs (see `jaspersoft/inventory/CLIENTS.md`) |

Reachable only over the VPN. Credentials: `JRS_<ENV>_URL / _USER / _PASSWORD / _INSECURE` in
`~/OriginBA-3/.env` (the test server also answers to `JRS_URL/USER/PASSWORD`); only key names are
ever printed. A login is org-scoped (`user|Org`) or a superuser; superuser paths are
`/organizations/organization_1/organizations/<Org>/...`.

## The rules (Chase, 2026-09-17)

1. **Snapshot before any change**: `jrs_inventory.py snapshot --env <env> [--org <Org>]`. The
   server's own export lands as a re-importable zip under `backups/jaspersoft/` (gitignored)
   and a diffable tree under `jaspersoft/inventory/<env>/<org>/` (committed, passwords
   redacted). That zip is the rollback. No snapshot, no change.
   - `prod` is org-scoped (the login is `user|Org`, it sees only that org): `--orgs A B C`
     exports each org's root with the login re-scoped. Works for CityCorp, Ellensburg,
     Newark1, Fond_Du_Lac, College_Station; Odessa and Origin_* answer 401 there.
   - **A prod (JRS 9.0) export can hang forever on one folder** (Fond_Du_Lac 2026-09-18:
     `/SmartCity/Report/FDL_Bill_Processing_Reports__Linda_` and `FDL_Trial_Balance` never
     finished, even alone). `--split /SmartCity /SmartCity/Report --part-cap 300` exports the
     tenant folder by folder, splitting the named folders into their children; a part that
     is not done after the cap is recorded under `snapshot.stuck` in the summary and skipped,
     the rest of the tenant lands. The backup is then one zip per part (`<Org>__<folder>.zip`).
   - Never run two prod exports at once; the exporter is the live server's own thread.
2. **Origin_DEV on `test` is the only place changes happen without a specific instruction.**
   Every other org is a live client tenant; `prod` is read-only until Chase names the org and
   the change. Never edit a datasource anywhere.
3. **Diff after**: `jrs_inventory.py diff test:Origin_DEV test:Origin_DEV` against the
   pre-change snapshot (or env:Org vs env:Org for a promotion) and put the result in the
   commit message. A change that cannot be shown as a diff did not happen.
4. **Deploy with REST, not import zips** (`jrs_deploy_report_units.py`); two zip shapes
   "succeeded" and created nothing on this server. Promotion of whole folders uses the
   server's export (`/rest_v2/export`, which is what a snapshot is) re-imported into the
   named org -- prove it on Origin_DEV first, then Origin_TEST, before any client.
5. Commit the inventory after every snapshot: the repo is the version history the servers
   do not keep.

## Tools

| | |
| --- | --- |
| `scripts/jaspersoft/jrs_repository.py --env X whoami / search / list / import` | who am I, where is a resource, what a folder holds |
| `scripts/jaspersoft/jrs_inventory.py snapshot [--orgs] [--split] / diff / summary / clients / environments` | backup + inventory + comparison; `jaspersoft/inventory/{README,CLIENTS,ENVIRONMENTS}.md` are generated |
| `scripts/jaspersoft/jrs_deploy_report_units.py --org X --datasource Y [--run FROM TO]` | create/overwrite report units from the finance-pack specs and execute them |
| `tests/test_jrs_inventory.py` | the offline half of the inventory tool on a real export |

## What the REST API can and cannot do here

Can: browse every org/folder/resource with type, label, dates and content (JRXML, domain
schema, Ad Hoc state); create, overwrite, delete, copy and move resources (structure intact);
export any URIs with dependencies; import into a named org; run reports to PDF/XLSX/CSV;
read pick-list values; permissions, users, roles, organizations; scheduled jobs.
Cannot: server configuration, JDBC drivers, font extensions (Aptos), Ad Hoc design editing.
