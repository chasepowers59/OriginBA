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
4. **Report units deploy with REST descriptors** (`jrs_deploy_report_units.py`). **Folder
   promotion is proven (Origin_DEV -> Origin_TEST, 2026-09-18,
   `jaspersoft/docs/origin_dev_to_origin_test_promotion_plan.md`):** org-scoped export of the
   folder, the client pipeline (`run_client_import_pipeline.py`, tenant-root, light touch,
   datasource overlay), both verifiers PASS, then `jrs_repository.py import` as `user|<Org>`
   with `rootTenantId=<Org>` added to index.xml (the REST importer refuses the UI's
   no-rootTenantId shape: `import.root.into.organization.not.allowed`). Before EVERY promotion
   export the target org's datasource fresh and use that as the overlay -- the stored
   FondDuLac_DS overlay pointed at a retired host. Snapshot before and after; the after diff
   against the source must be datasource name, `componentType`, and Workstreams->Standard_Offering
   rewiring only.
5. Commit the inventory after every snapshot: the repo is the version history the servers
   do not keep.

## Tools

| | |
| --- | --- |
| `scripts/jaspersoft/jrs_repository.py --env X [--org Y] whoami / search / list / perms / jobs / job / users / roles / export / run` | read the server: who am I, where is a resource, what a folder holds, who can see it, what is scheduled, a report's PDF |
| `scripts/jaspersoft/jrs_repository.py --env X --org Y --confirm Y [--i-mean-prod] [--dry-run] import / copy / move / delete / mkdir / perms-set / job-run / job-delete` | WRITE the server. Every write must name the org back (`--confirm`), prod also needs `--i-mean-prod`, and `--dry-run` prints the exact call. `tests/test_jrs_repository_ops.py` pins the calls and the guards |
| `scripts/jaspersoft/jrs_inventory.py snapshot [--orgs] [--split] / diff / summary / clients / environments` | backup + inventory + comparison; `jaspersoft/inventory/{README,CLIENTS,ENVIRONMENTS}.md` are generated |
| `scripts/jaspersoft/jrs_deploy_report_units.py --org X --datasource Y [--run FROM TO]` | create/overwrite report units from the finance-pack specs and execute them |
| `scripts/jaspersoft/jrs_run_sweep.py --env X --org Y [--folder F] --out jaspersoft/sweeps/<env>_<org>_<date>.json` | RUN everything in a folder and classify it: Ad Hoc views through queryExecutions with the view as datasource (ok / EMPTY / error), report units through the reports service, dashboards through dashboardExecutions. The post-promotion smoke, and the before/after of a server upgrade (diff the two JSON files by uri). On the test server dashboards answer `ERR_CONNECTION_REFUSED` from the server's own headless export engine, not from the dashboard: classified `export-engine`, and the UI opens them fine (Chase, 2026-09-18) |
| `scripts/jaspersoft/audit_adhoc_saved_filters.py --env X --org Y --client <config id>` | saved Ad Hoc filter values that name the SOURCE client's configuration and the target does not have (the promoted view returns nothing there); reads the explorer's per-client config export |
| `tests/test_jrs_inventory.py` | the offline half of the inventory tool on a real export |

## What the REST API can and cannot do here

Can: browse every org/folder/resource with type, label, dates and content (JRXML, domain
schema, Ad Hoc state); create, overwrite, delete, copy and move resources (structure intact);
export any URIs with dependencies; import into a named org; run reports to PDF/XLSX/CSV;
read pick-list values; permissions, users, roles, organizations; scheduled jobs.
Cannot: server configuration, JDBC drivers, font extensions (Aptos), Ad Hoc design editing.

## Lessons that cost time (2026-09-18) -- read before promoting or upgrading

1. **REST import inside an org needs `rootTenantId=<Org>` in index.xml.** The pipeline's UI
   package (no rootTenantId) fails by REST with `import.root.into.organization.not.allowed` and
   creates nothing. Add the property after `pathProcessorId`; both verifiers still PASS with
   `--tenant-id <Org>`. `/public/templates/actual_size.820.jrxml` in the package is fine.
2. **Poll `/rest_v2/import/<id>/state`, not `/import/<id>`** (10.0 answers the latter with the
   task's parameters, then 404). `jrs_repository.py import` does this now.
3. **Never promote with a stored datasource overlay.** Export the target org's `/DataSource/<DS>`
   fresh (org-scoped login) and use that as the overlay; the stored FondDuLac_DS pointed at the
   retired pre-25.4 host. The import re-saves the DS with its own bytes (only the version counter
   moves) -- prove it with a before/after diff of the DS XML.
4. **The after-diff against the source is never zero.** Expect: the DS name, a
   `<componentType>default</componentType>` the 10.0 server adds on save, and the pipeline's
   rewiring of `/SmartCity/Report/Workstreams/...` references to `Standard_Offering/...` (ten
   Origin_DEV resources still point at the legacy tree). Anything else is a defect.
5. **A failed import can still change the org:** the server materialised Origin_TEST's
   `/themes/default` from its parent on the first (failed) attempt. Harmless, but it shows in
   the after-snapshot; do not chase it.
6. **Saved Ad Hoc filters travel with the view.** Authored over Ellensburg, they name Ellensburg
   rate schedules, GL codes, SA types; at another client those views return nothing. Run
   `audit_adhoc_saved_filters.py` after every promotion and hand the client the review; the
   replacement value is the client's decision, never a wording match.
7. **Running Ad Hoc views by REST:** `POST /rest_v2/queryExecutions` with content type
   `application/execution.<multiLevel|multiAxis>Query+json`, Accept `application/<kind>Data+json`,
   body `{"dataSource":{"reference":{"uri":<VIEW uri>}},"query":<view query>}`. The VIEW as
   datasource (not its domain) resolves calculated fields; filter parameters must be inlined
   (their names "conflict with metadata field"). The reports service refuses view URIs.
   Dashboards: `POST /rest_v2/dashboardExecutions` `{"uri","format"}` then `/status` and
   `/outputResource`; on the test server the headless export engine answers
   `ERR_CONNECTION_REFUSED` (server config, dashboards open in the UI).
8. **Before an upgrade:** `jrs_run_sweep.py` over `/SmartCity` for EVERY prod org, committed to
   `jaspersoft/sweeps/`, plus the inventory snapshot. After: the same, then `jrs_run_sweep.py
   compare before.json after.json` (broke / healed / emptied / slower; row-count drift is the
   snapshot refresh, not the upgrade) and `jrs_inventory.py diff`. Run both sweeps after the same
   refresh wave (10:00-13:30 or 16:00-19:30 UTC) so counts line up.
9. **Slow views are real findings**, not tool faults: Usage_Transaction___Not_Used_on_Bill
   exceeds 240 s at Fond du Lac; Measurements___No_Reads 100 s. A view over 30 s is a candidate
   for the snapshot layer.
10. **"Empty" is calibrated (2026-09-19, CityCorp prod).** The cause was never whitespace: an Ad Hoc
    "is any value" filter is saved as `in (field, [])` -- an empty list -- which the UI ignores and
    the query-executions service applies literally (`x IN ()` = no rows). The runner drops those
    (`_drop_any_value`); views that read 0 now answer 14,574 / 6,945 / 392 rows. An empty after the
    fix is real: a client-specific filter value (audit_adhoc_saved_filters.py), a feature the client
    does not use, or a date window with nothing in it. Verified by bisecting the saved filters one at
    a time (`jrs_view_calibrate.py` is the harness for the next such question).
11. **Speed, corrected (2026-09-19):** running five prod orgs at once with 6 workers each (30
    concurrent executions) SATURATED the prod 9.0 server: descriptor GETs and TLS handshakes timed
    out, the median successful view took 20 s (2 s on test), Newark1 read 120 timeouts of 160. A
    baseline taken that way hides real breakage. Prod sweeps run ONE org at a time, 3 workers, 120 s
    cap (whole tenant ~1,300 resources, ~1-1.5 h). The parallel `--org A --org B` form is for the
    test server. A run's honesty check: the median ok time should be single-digit seconds, and no
    "descriptor None" errors.

## The playbook: what to run for each thing Chase needs (2026-09-20)

Every entry assumes the VPN is up and follows the rules above: snapshot before, diff after,
Origin_DEV by default, prod only when named with `--i-mean-prod`. All commands take `--env
test|prod|internal` and `--org <Org>` (the login becomes `user|Org`; paths are then tenant-relative
`/SmartCity/...`).

| Need | Command(s) | Proof |
| --- | --- | --- |
| What is on a server / in an org | `jrs_inventory.py snapshot --env X --org Y` (superuser) or `--orgs Y` (org-scoped, prod); commit `jaspersoft/inventory/` | `jaspersoft/inventory/{README,CLIENTS,ENVIRONMENTS}.md` regenerate with `summary`, `clients`, `environments` |
| Back up before a change | the same snapshot: the zip under `backups/jaspersoft/<env>/<stamp>/` is the rollback | `jrs_repository.py import <that zip>` restores it (org-export shape carries `rootTenantId`) |
| Roll back | `jrs_repository.py --env X --org Y --confirm Y import backups/.../Y.zip` (or one folder: `export` it first, keep the zip) | snapshot again, `jrs_inventory.py diff` shows the change undone |
| Promote the Standard Offering to a client org | `jaspersoft/docs/origin_dev_to_origin_test_promotion_plan.md` steps: org-scoped `export` of the folder from Origin_DEV, export the TARGET org's `/DataSource/<DS>` fresh, `run_client_import_pipeline.py` with that overlay, both verifiers PASS, add `rootTenantId`, `jrs_repository.py import` as `user|Org` | after-snapshot vs source: same file set, only DS name / componentType / Workstreams rewiring differ; datasource XML byte-identical to its own export |
| Promote one report or folder | `jrs_repository.py --org Origin_DEV export /SmartCity/Report/X --out x.zip`, then the tenant-import builder (`build_client_tenant_report_import.py`) or, for Origin-owned orgs, `import` the export as-is | `search` finds it in the target; `run` renders it |
| Deploy a SQL report unit | `jrs_deploy_report_units.py --org Y --datasource <DS>` (REST descriptors; never an import zip for these) | `--run FROM TO` renders the PDF |
| Fix a domain without breaking reports | change the derived-table SQL or a join in the schema, keep every item id/label; import as a COPY first (`domains/manual_imports/fonddulac_asset_domain/` is the pattern), prove it, then paste into the original | `jrs_view_calibrate.py`-style queryExecutions against copy and original on the same keys |
| Rearrange folders | `mkdir`, `move`, `copy` (destination is a FOLDER; the resource keeps its name); Ad Hoc views and dashboards keep working because references are by URI and the server rewrites them on move | `list` the new place; `jrs_run_sweep.py --folder <new>` runs everything there |
| Retire a resource | `export` it to a zip first, then `delete` | the zip re-imports it |
| Who can see what | `perms /uri`; change with `perms-set /uri role/ROLE_X:18 ...` (REPLACES the list: name every recipient you keep; 18 = read+execute, 30 = full, 1 = administer) | `perms` again |
| Scheduled reports | `jobs [--report /uri]`, `job ID`, `job-run ID`, `job-delete ID`. Jobs are NOT in a repository export: list them before an upgrade or a move (a moved report's jobs follow it; a deleted report's jobs die) | `jobs` before and after |
| Users and roles | `users [--role R]`, `roles` (read). Creating users is a UI task here: it needs the org's password policy and is not something to script against a client tenant | |
| Does everything still load (upgrade, promotion) | `jrs_run_sweep.py --env prod --org Y --folder /SmartCity --types view,report --workers 3 --timeout 120 --out jaspersoft/sweeps/<name>.json`, ONE org at a time on prod; then `jrs_run_sweep.py compare before.json after.json` | broke / healed / emptied / slower lists; row-count drift is the snapshot refresh |
| A client says a view is empty | `audit_adhoc_saved_filters.py --env X --org Y --client <id>` (Ellensburg-only filter values), then `jrs_view_calibrate.py` on the view | the review markdown names what the client configures instead |
| Letters | not the report pipeline: `~/originba-letterprint/.claude/skills/jaspersoft-letter-delivery` |

What the server cannot be asked to do over REST, so it stays a human task: server configuration
and JDBC drivers, font extensions (Aptos), the Ad Hoc designer itself (a view's layout is edited in
the UI; its query and filters can be read and changed as JSON through `resources?expanded=true`),
and datasource passwords (an export carries them encrypted; `perms` and `users` never print them).

### About mr-wolf-gb/jasperreports-mcp-server (assessed 2026-09-20)
A Node MCP wrapper over the same `/rest_v2` API: generic resource CRUD, run/async execution,
jobs, users/roles, permissions, domain read, health. It adds nothing the scripts above do not
already do against these servers, and it lacks the parts that matter here: export/import zips
(the backup, rollback and promotion path), org-scoped logins per call, Ad Hoc view execution via
`queryExecutions` with the any-value fix, inventory diffs, and the write guards. Its delete /
permissions / user tools with one global credential are exactly the footgun the rules exist to
prevent on a shared multi-tenant server. Not adopted; the gaps it exposed (copy/move/delete/mkdir/
permissions/jobs/users) were added to `jrs_repository.py` with `--confirm` and `--i-mean-prod`.
