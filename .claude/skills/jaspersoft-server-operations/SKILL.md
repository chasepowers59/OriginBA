---
name: jaspersoft-server-operations
description: Operate the three SmartCity JasperReports Server environments (internal, test, prod) through the REST API - inventory and backup every organization into the repo, diff environments, deploy and promote report units and Standard Offering folders, and the standing safety rules (snapshot before, diff after, Origin_DEV by default, prod only on an explicit go). Use before ANY change to a Jaspersoft server, when asked what an environment or client contains, when promoting between environments, or when something on a server looks different from the repo.
---

# Jaspersoft server operations

## The estate (measured 2026-09-17; re-measure with `jrs_repository.py --env X whoami`)

| env | URL | what it holds |
| --- | --- | --- |
| `test` | https://smartcity-jrs-test.originsmartops.com/jasperserver-pro | JRS 10.0.0 PRO; one instance, every client an org under `organization_1`: Ellensburg, Fond_Du_Lac, CityCorp, College_Station, Odessa, Newark1, Origin_DEV, Origin_TEST |
| `prod` | https://smartcity-jrs.originsmartops.com/jasperserver-pro | **JRS 9.0.0 PRO (JRXML 6 model) until its 10.0 upgrade, upgraded 2026-09-21**. **ROOT, measured 2026-09-22**: `cpowers@originutility.com` holds ROLE_SUPERUSER + ROLE_ADMINISTRATOR here exactly as on test and internal, and `/rest_v2/organizations` lists the tree. The old "org-scoped only, bare login 401" note was never the server: `JRS_PROD_USER` carried `\|CityCorp`, so every call inherited that org. The key now holds the BARE user name and `--org` re-scopes per call |
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
   - `prod` is ROOT since the credential was corrected (2026-09-22), so a plain
     `snapshot --env prod` takes the whole server in one superuser pass, the way test and
     internal already run; `--orgs A B C` still re-scopes per org when that is what you want.
     Odessa's old 401 was the CityCorp-scoped login, not a permission: re-check it at root.
   - **A stored credential can carry an org, and then nothing is un-scoped.** `JRS_PROD_USER`
     read `user|CityCorp`, so `whoami` with no `--org` still answered "organization CityCorp"
     and `/rest_v2/organizations` returned 204 -- which reads exactly like a permission wall
     and is not one. Check the login's SCOPE before concluding anything about its RIGHTS:
     `whoami` prints the scope first, then the roles, then whether the org tree lists.
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
| `scripts/jaspersoft/jrs_adhoc_chart_props.py --env X --org Y --folder F --set name=value [--only-if name=value] [--dry-run] [--i-mean-prod]` | set Highcharts advanced properties on EVERY Ad Hoc chart state under a folder, dashboard-embedded copies included; backs each state up under `backups/jaspersoft/adhoc_state/`, reads every PUT back. `tests/test_jrs_adhoc_chart_props.py` pins the XML patch on real states |
| `scripts/jaspersoft/jrs_sa360_prem_char_apply.py --env X --org Y [--dry-run] [--i-mean-prod]` | give an org's Service Agreement 360 domain the premise-characteristics group IN PLACE: export (the rollback), patch THAT org's export (its own DS id), PUT the schema with its version, then four proofs (read-back byte-equal, `/domains/<uri>/metadata` lists the group, every bound view runs, a flat query of the new items returns rows). Live 2026-09-21: College_Station test, Ellensburg test + prod |
| `scripts/jaspersoft/jrs_promote.py --from env:Org --to env:Org --resource U [--resource U2] [--into F] [--ds DS] [--param K=V] [--replace] [--dry-run] [--check-only] [--i-mean-prod]` | **THE org-to-org move (2026-09-24)**: domains, report units, Ad Hoc views, dashboards or whole folders, as ROOT on both sides (no per-org login, so Odessa is reachable like any org), across servers too. Package = the target's own datasource (+ any referenced domain) byte for byte, plus the scope rewritten onto the target org/destination folder with every datasource reference repointed; refuses if the source org path, datasource name or database host survives; after import re-exports and compares, then EXECUTES every promoted resource (domain metadata + probe query, report PDF with `--param`, view query, dashboard). `--check-only` re-runs just the execution proof. `tests/test_jrs_promote.py` pins the package on root-export shapes. Live 2026-09-24: A/P request domain + report Origin_DEV -> Odessa, ties Oracle 21/21 |
| `scripts/jaspersoft/jrs_copy_resources.py --from env:Org --to env:Org --view U / --folder F` | the ORG-SCOPED predecessor (needs a login in both orgs): replaces a view or folder inside the target's own export; keep for a server where root is not held |
| `scripts/jaspersoft/jrs_check_topic_kinds.py --env X --org Y [--folder F]` | views whose topic disagrees with their state about a measure: the one predictor of 'executes but will not open' that survived calibration |
| `scripts/jaspersoft/jrs_domain_query.py --env X --org Y|ROOT --domain U [--fields set.item,...] [--agg set.item:Function ...] [--where DomEL] --out f.json` | rows out of a domain by item id; with `--agg` a GROUPED query (fields = group-by, none = grand total; the only way to a total through a domain, a flat query is row-level whatever the item's default aggregation); `--where` a DomEL filter (`ts'2026-01-01 00:00:00'` date literal). Measured shapes: aggregations name `fieldRef`; groupBy is a list of `{"group": {...}}` / `{"allGroup": {...}}`; a grouped query with detail fields answers one row per detail row |
| `scripts/jaspersoft/build_adjustment_domain.py --ds DS --out f.xml` | the comprehensive Adjustment domain (root CI_ADJ, every join outer, 40 tables + 3 derived, 221 items); `tests/test_adjustment_domain.py`; README under `domains/manual_imports/adjustment_domain/` |
| `scripts/jaspersoft/jrs_import_domain.py --env X --org Y --ds <DS> --folder F --name N --label L --schema f.xml` | CREATE a domain from a schema, packaged with the org's own datasource; then metadata + a probe query |
| `scripts/jaspersoft/jrs_sa360_prem_char_apply.py`, `patch_write_offs_domain.py`, `build_adj_ap_request_domain.py` | the domain builders/patches of 2026-09-21..23, each with its tests and README under `domains/manual_imports/` |
| `scripts/jaspersoft/jrs_deploy_report_units.py --org Y --datasource DS [--only SPEC] [--run FROM TO]` | the finance-pack report units from `generate_sql_report_pack.py` SPECS; `--only` for one |
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
| Promote a client's folder TEST org -> PROD org (the production deployment path from 2026-09-21 on) | `jrs_promote_test_to_prod.py --org Y --folder /SmartCity/Report/Standard_Offering --ds <DS> --dry-run` then with `--i-mean-prod`. Both orgs name the datasource the SAME (FondDuLac_DS) at DIFFERENT hosts, and the folder export CARRIES the datasource XML: imported as-is it would repoint prod at the test database. The script replaces the DataSource tree with prod's own export taken minutes earlier, lists it first, sets rootTenantId, and refuses if any test-host string survives | prod DS byte-identical to its own export; `jrs_inventory.py diff test:Y prod:Y --folder ...` = dates/version only; sweep the folder |
| Promote one report / domain / view / folder to another org (any org, any server) | `jrs_promote.py --from test:Origin_DEV --to test:Odessa --resource U --into F --ds <DS> --param FROM_DT=... --dry-run`, then without `--dry-run` (prod: `--i-mean-prod`). Root on both sides; `--into` places it, `--ds` names the target's datasource when it has more than one (Odessa: `Origin_DataVergence_DS` = the DEV database, what its 51 Standard Offering domains use; `Odessa_DS` = the TEST database) | steps 1-7 of the tool: package verified, import without warnings, re-export matches, every promoted resource executes; then tie a domain or report count to the client's database as in the 2026-09-24 section |
| Reformat charts (label size, colour, axis text) across a folder | `jrs_adhoc_chart_props.py --env X --org Y --folder F --set plotOptions.series.dataLabels.style.fontSize=15px ... --dry-run`, then for real; never `style.color=contrast` for labels outside the bars | reload the dashboard in the Browser pane and read computed colour/size of `.highcharts-data-label text` and what `elementsFromPoint` finds under each label |
| Add the premise-characteristics group to a client's SA 360 domain | `jrs_sa360_prem_char_apply.py --env X --org Y --dry-run`, then for real (prod: `--i-mean-prod`); never copy Origin_DEV's schema file into another org | the tool's four proofs print PASS; then the Ad Hoc designer in the Browser pane (Chase logs in) before the client is told; tell them to create a NEW Ad Hoc view on the domain |
| Deploy a SQL report unit | `jrs_deploy_report_units.py --org Y --datasource <DS>` (REST descriptors; never an import zip for these) | `--run FROM TO` renders the PDF |
| Fix a domain, Chase's way (preferred, no package) | Domain Designer > open the domain > Edit > Import the schema XML: replaces ONLY the schema file, the datasource and everything else stay; `jrs_debug.py domain-apply URI --schema file` is the same operation over REST. Prove the schema first as a copy (`domain-copy`) or on TEST |
| Fix a domain without breaking reports | change the derived-table SQL or a join in the schema, keep every item id/label; import as a COPY first (`domains/manual_imports/fonddulac_asset_domain/` is the pattern), prove it, then paste into the original | `jrs_view_calibrate.py`-style queryExecutions against copy and original on the same keys |
| Rearrange folders | `mkdir`, `move`, `copy` (destination is a FOLDER; the resource keeps its name); Ad Hoc views and dashboards keep working because references are by URI and the server rewrites them on move | `list` the new place; `jrs_run_sweep.py --folder <new>` runs everything there |
| Retire a resource | `export` it to a zip first, then `delete` | the zip re-imports it |
| Who can see what | `perms /uri`; change with `perms-set /uri role/ROLE_X:18 ...` (REPLACES the list: name every recipient you keep; 18 = read+execute, 30 = full, 1 = administer) | `perms` again |
| Scheduled reports | `jobs [--report /uri]`, `job ID`, `job-run ID`, `job-delete ID`. Jobs are NOT in a repository export: list them before an upgrade or a move (a moved report's jobs follow it; a deleted report's jobs die) | `jobs` before and after |
| Users and roles | `users [--role R]`, `roles` (read). Creating users is a UI task here: it needs the org's password policy and is not something to script against a client tenant | |
| The whole check for one org in one command (upgrade morning, post-promotion) | `jrs_validate.py --env prod --org Y [--folder /SmartCity] [--cap 20] [--baseline <before>.json] --label post_upgrade [--exclude <hanging folders>]`: snapshot (rollback zip), inventory diff vs the last committed tree, sweep with a per-resource cap (past it = SLOW, move on), compare with the baseline, write `jaspersoft/sweeps/<env>_<org>_<label>_<stamp>.md` | the .md: verdict line, broke / went empty / now slow / healed / missing / new, inventory added/removed/changed, errors, slow list |
| Does everything still load (upgrade, promotion) | `jrs_run_sweep.py --env prod --org Y --folder /SmartCity --types view,report --workers 3 --timeout 120 --out jaspersoft/sweeps/<name>.json`, ONE org at a time on prod; then `jrs_run_sweep.py compare before.json after.json` | broke / healed / emptied / slower lists; row-count drift is the snapshot refresh |
| A client says a report or view is wrong | `jrs_debug.py --env X --org Y [--client id] inspect URI` (a view's domain, fields, every saved filter with its value, any-value placeholders, values the client does not configure, the derived tables and joins its tables touch; a report's query and controls), `run URI --bisect` (execute; when empty, each saved filter alone with its row count). Fix: `domain-copy URI --name NEW --set-query ID=file.sql --set-join "OLD=>NEW"` (a second domain beside the original, org's own DS listed first), prove on it, then `domain-apply URI --schema file` (in place; item ids unchanged so bound views survive), `view-update URI --drop-filter F --set-filter F=a,b --swap-field OLD=NEW`, `report-update URI --jrxml f`. All writes: `--confirm Org`, prod `--i-mean-prod`, `--dry-run` first | `run` on the copy vs the original on the same keys (the Fond du Lac pattern: 16,672 = 16,672, 0 blank) |
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

### Live-verified vs authored-offline (2026-09-20)
Verified against a server: inventory/snapshot/diff, REST import (org-export shape), report-unit
deploy and run, view execution via queryExecutions (any-value fix), dashboard execution, the
domain copy import, export_zip. Live-verified 2026-09-21 as well: `jrs_promote_test_to_prod.py` end to end (Ellensburg, Newark1),
`jrs_fix_stripped_topics.py` (111 views), file-resource PUT with version, `jrs_debug.py domain-apply` (College_Station SA 360, 2026-09-21: it now fetches the file's version first; without it the PUT is a 409). Still authored offline only, dry-run first: `jrs_repository.py` copy/move/delete/mkdir/perms-set/jobs/users/roles,
`jrs_debug.py` view-update (PUT
of the adhocDataView descriptor), report-update (PUT of `<unit>_files/main_jrxml`), and
`jrs_promote_test_to_prod.py` end to end (its packaging is proven on the real 2026-09-18 exports).

## Tomorrow's order (10.0 upgrade review, then test-to-prod deployments), 2026-09-21

1. VPN on. `jrs_repository.py --env prod whoami` must say 10.0.0. Read `/DataSource` of each prod
   org (`--org Y list /DataSource`) and confirm the URLs are the prod hosts.
2. Per prod org, one at a time: `jrs_validate.py --env prod --org Y --label post_upgrade --cap 20`
   (CityCorp first, its Standard Offering has the 2026-09-18 baseline sweep; Fond_Du_Lac with
   `--exclude /SmartCity/Report/FDL_Bill_Processing_Reports__Linda_ /SmartCity/Report/FDL_Trial_Balance`).
   Snapshot ~5-10 min, sweep ~10-15 min at a 20 s cap. Commit `jaspersoft/inventory` + `sweeps`.
3. Read the five .md files: BROKE lists and inventory "changed" are the upgrade's effects; SLOW is a
   list to hand the DBAs, not a blocker; row-count drift is the refresh.
4. Then, per client Chase names: `jrs_promote_test_to_prod.py --org Y --ds <DS> --dry-run` (package
   on disk, PASS), then `--i-mean-prod`, then `jrs_validate.py --env prod --org Y --folder
   /SmartCity/Report/Standard_Offering --label post_promote --baseline <the post_upgrade sweep>`.

Parallelism, honestly: one prod server serves every org, so five orgs at once saturates it (measured
2026-09-19: median ok 20 s, fake timeouts). The sweep's 3 workers ARE the parallelism on prod; the
test server takes `--org A --org B` at once. Agents in parallel pay off on the work that does not
hit the server: reading five summaries, the per-client filter reviews, domain fixes for different
clients, writing up. A short cap is what makes the run fast: nothing is waited for.

## JRXML 6 on the 10.0 server, settled (2026-09-20, before the prod upgrade)

Measured here: the JasperReports 7.0.7 LIBRARY refuses JRXML 6 ("Unable to load report" on a repo
report, the legacy Odessa letter, and Ellensburg's live bill pulled from the 10.0 test server), and
6.20.6 refuses JRXML 7; `net.sf.jasperreports:jasperreports-legacy` is not on Maven Central. The
vendor: JR 7 replaced the Digester parser with Jackson and deliberately broke loading of 6.x files;
Studio 7+ converts. BUT JasperReports Server 10.0 **PRO** carries the `LegacyXmlLoader` from
JRL-Pro, gated on a valid license; the upgrade guide has the script check the license for exactly
that reason. So prod's 596 JRXML 6 report units (CityCorp 109, College Station 149, Ellensburg 159,
Fond du Lac 61, Newark 118) keep loading on 10.0 PRO -- as the 10.0 TEST server already proves with
its JRXML 6 bills -- provided the license is in place. Monday's first check after `serverInfo` says
10.0.0: `licenseType` and `expiration` in the same answer, then run one legacy JRXML 6 unit per org.
A JRXML 6 unit that fails with "Unable to load report" on 10.0 = license/legacy-loader problem, not
a report problem. Authoring stays: JRXML 7 for new units on 10.0; the 7-to-6 converter only for a
9.0 target. Sources: community.jaspersoft.com upgrade guide 9.0->10.0.0; jasperreports README
(Jaspersoft/jasperreports GitHub); Jaspersoft/jasperreports issue #442.

## Cursor's Ad Hoc topic brief, checked (2026-09-20)
Agreed and already in the repo: `strip_jrs8_incompatible_jrxml_uuid.py` converts `<query
language="domain">` to `<queryString>`, strips `uuid` and parameter `nestedType`, for Ad Hoc
`topicJRXML` bound for a 9.0 Ad Hoc loader; `verify_prepared_import.py --expect-jrs8-adhoc-compat`
gates it; JRXML 7 units use `<query>`, domain reports use `<queryString language="domain">` with the
domain `<query>` XML inside the CDATA. Two corrections: (1) "no rootTenantId for in-tenant import" is
the UI's Repository > Import; the REST importer REQUIRES `rootTenantId=<Org>` (measured 2026-09-18);
(2) after the 10.0 upgrade the strip is probably unnecessary (10.0 emits `<query>` topics itself and
the 10.0 test server opens them) -- decide by opening one promoted Ad Hoc view on prod, not by rule.

## First morning on prod 10.0 (2026-09-21): the 9.0 Ad Hoc strip is the thing that broke

Symptom: "AdhocDataView state initialization error" opening Ad Hoc views; whole folders of the
Standard Offering on CityCorp, a folder on Newark1, nothing elsewhere. Cause: every view promoted
to the 9.0 server through `strip_jrs8_incompatible_jrxml_uuid.py` carries a topic JRXML with no
namespace, no uuid, no nestedType and `<queryString>`. 10.0's licensed legacy loader keys on the
JRXML 6 namespace; a namespace-less topic is parsed as JRXML 7 and fails. The view's state and the
domain were fine (state byte-identical to the test org's; domain schema identical). Views re-saved
on the server after promotion had a normal JRXML 6 topic and worked -- which is why some views in
the same folder worked and others did not.
Fix: `jrs_fix_stripped_topics.py --env prod --org Y [--scan | --i-mean-prod]`: scans every Ad Hoc
view's topic for the stripped shape, backs the old topic up under `backups/jaspersoft/topics/`,
replaces it with the 10.0-generated topic the same view carries on the test org (same state,
same domain), then opens and runs it. 2026-09-21: CityCorp 103/103, Newark1 8/8, all open; zero
stripped topics remain on any prod org. Rule from now on: **never run the 9.0 strip for a 10.0
target**; `--expect-jrs8-adhoc-compat` is a 9.0-era check and stays off. A prod restart mid-run
drops a PUT: the tool retries once, and a rerun resumes from the scan.
Also learned: a file resource PUT needs the current `version` echoed back (409 "versions not
match" otherwise) and its descriptor is read with Accept `application/repository.file+json`.

## Test-to-prod promotions of 2026-09-21 (the deployment path, live)
Ellensburg and Newark1: `jrs_promote_test_to_prod.py --org Y --ds Y_DS --dry-run` (PASS), then
`--i-mean-prod`. Each: prod org snapshot (rollback), test folder export, prod's own DS export,
package, verify, import ("Import succeeded", no warnings), snapshot again. Proof per org: DS host
identical to the 09-18 export; folder identical to test in every file after volatile fields (691 /
697); zero stripped topics; every view opened and executed with a short cap. Ellensburg 116 rows /
7 empty / 27 slow (20 s) / 0 errors; Newark1 69 / 10 / 74 slow (15 s) / 0 errors -- Newark's volume
makes half its views slow, not broken. Wall clock ~11 min Ellensburg, ~21 min Newark (its 306 MB
org export twice). Standard Offering now on prod: CityCorp, Ellensburg, Newark1.

## After a domain change, prove it where the USER looks, before announcing it (2026-09-21)
College_Station's SA 360 got the premise-characteristics group by in-place schema PUT; the
file read back byte-equal, the domain opened, the bound view ran, a flat query returned
191,114 rows -- and the client replied that he could not see it. What the server-side checks do
NOT cover, in the order to check:
1. `GET /rest_v2/domains/<uri>/metadata` is the Ad Hoc-facing presentation (sets + items as the
   designer lists them). Run it after every schema change; the file is not the proof.
2. An in-place `_files/schema` PUT leaves the DOMAIN resource's version/updateDate untouched
   (College_Station: version 0, 2026-06-17), so anything cached on the domain resource -- a
   user's Ad Hoc session, the designer's metadata cache -- can keep the old field tree. A
   re-save in Domain Designer (or log out/in for the user) refreshes it.
3. Users open EXISTING saved views. Say in the announcement: create a NEW Ad Hoc view from the
   domain (Create > Ad Hoc View > Domains > Service Agreement 360), then the new set is in the
   field tree. Name the environment (test vs prod) in the same message: prod College_Station
   has no Standard Offering, so a user who checks prod sees nothing.
4. The definitive proof is the Ad Hoc designer itself: Chase logs into that server/org in the
   Browser pane, open Create > Ad Hoc View on the domain, screenshot the field tree. Do this
   BEFORE the reply goes to the client, not after.

## Copying ONE view between client orgs, and what the importer really does (2026-09-23)

Ellensburg prod's "Financial Transaction - Bill Cycle Transactions" would not open in the Ad Hoc
editor (console: `fetchFieldsList` -> `Cannot read properties of null (reading 'rootNode')`, then
`hardEscape(...).join is not a function`) while executing perfectly through the API. Everything
server-side was healthy and byte-identical to test: query 1.6s with real rows, domain items 45/45,
every referenced field resolving, filters well formed. Two plausible culprits were DISPROVED by
comparing against CityCorp's working copy of the same view: a unitless `legend.itemStyle.fontSize=17`
(CityCorp works WITH it; 43 states in the org carry it) and a missing `<seriesColors>` (17 of 24
states in the folder lack it). What remained was the saved crosstab layout itself -- the
transaction-type dimension sitting in `columnGroups` with an `expandedLevels` entry -- and THAT
theory died at calibration the same morning: "Meter Operations - Daily Installations" in
Ellensburg prod carries the identical shape and opens fine (Chase, 2026-09-23). Then Newark1's
copy of the SAME view, whose saved state is Ellensburg's broken state byte for byte apart from two
run-mode flags, opened fine too. So the stateXML is not the cause either. **The cause is in the
TOPIC** (`<view>_files/topicJRXML`, generated per org): the view's only measure is CountAll of
`FT_CORE.FT_ID`, and both broken Ellensburg topics declare that field `kind=DIMENSION` while
both working copies (Newark1, CityCorp) declare it `kind=MEASURE`. The editor builds its
measures list from a field the topic says is not a measure -> `fetchFieldsList` null rootNode,
then a template joins a non-list. A re-save in the editor does NOT fix it: the topic is
regenerated from the existing topic's metadata and keeps the bad kind. The data layer never
notices because queryExecutions reads the state, not the topic. **A sweep calling a view "ok"
says nothing about whether it OPENS.** The `layout_scan_prod_*_20260923.json` files committed
before calibration are signature hits, NOT a defect list; `jrs_scan_adhoc_layout.py` compares
states by identity, which also does not predict this. The predictor is
`jrs_check_topic_kinds.py`: for every view, each field the state aggregates must be
`kind=MEASURE` in its topic. Fleet result 2026-09-23 (Standard Offering folder): prod Ellensburg /
CityCorp / Newark1 = 0 hits (Ellensburg because the CityCorp copy replaced its topic); test
CityCorp / Newark1 / College_Station / Fond_Du_Lac / Origin_DEV = 0; test Ellensburg = 1, the
same Bill Cycle view, the SOURCE the prod copy was promoted from -- replaced from test CityCorp
so the next promotion does not carry it back. Only real measures count: a table view records
EVERY column as a `<measure>` element, and only `measure="true"` aggregates (the first cut of the
rule flagged 64 of 150 views for that). test Odessa answers 401 to the org-scoped login: unchecked. Fix for a hit: `jrs_copy_resources.py --view` from an org whose
topic is right, or re-create the view so the topic is regenerated from the domain.

Fix: `scripts/jaspersoft/jrs_copy_resources.py --from prod:CityCorp --to prod:Ellensburg
--view <uri> [--dry-run] --i-mean-prod` (also `--folder`, and across environments: FDL's
`/SmartCity/Report/FDL_Active_Write_Off_Process` went prod -> test on 2026-09-23 the same way).
Three import facts it encodes, all measured here:

1. **The importer resolves a resource's references only against what is IN the package.** A package
   holding the view alone returns "Import succeeded" WITH an `import.reference.resource.not.found`
   warning naming the domain, and writes NOTHING (the view's updateDate never moved). Any warning
   is a failed deploy until explained.
2. So the package is the TARGET's own export -- its datasource and domain byte for byte, verified
   file by file -- with only the view's `.xml` and `_files/` taken from the source org. The
   precondition is checked first: the two orgs' domains must expose identical item ids.

Importing the target's own datasource back bumps its `<version>` and re-encrypts
`connectionPassword` with a fresh salt; `connectionUrl` and `connectionUser` are unchanged, and the
view executing afterwards proves the connection. Do not read that ciphertext change as a repoint.

3. **The index tag is literal.** A folder export lists itself as `<folder>`, a resource export as
   `<resource>`. Writing a folder as `<resource>` answers "Reference resource not found" for the
   folder and nothing inside it lands. Keep the target export's own entries.

Also: `jrs_repository.py` takes `--confirm` / `--i-mean-prod` as GLOBAL flags, before the
subcommand; after it, argparse rejects the call and nothing is written.

## Ad Hoc chart formatting from here (2026-09-21, internal Origin_DEMO demo tweak)
A chart's look is Highcharts options in the view's `stateXML` under
`<chartState><advancedProperties><advancedChartProperty><name>plotOptions.series.dataLabels.style.fontSize</name><value>15px</value>...`
(the UI's Chart Format > Advanced Properties). Dashboards EMBED their own copy of every view
(`<Dashboard>_files/tmpAdv_*` and `.../dashboardReport`), so a change to the standalone view does
not reach the dashboard: edit every `stateXML` under the folder whose mode is `ichart`. PUT the file
resource with its current `version`, back the originals up under `backups/jaspersoft/adhoc_state/`.
Applied to 20 states (Usage, Measurements, Device): dataLabels 15px bold, no text outline (the
"fuzzy" look is Highcharts' contrast outline at 11px), axis and legend labels 13px. The org's theme
(`/themes/default`, byte-identical to NewestOriginBATheme) has no chart rules; a theme CSS rule
(`.highcharts-data-labels text{...!important}`) is the global alternative. The internal server's
headless dashboard export is broken (chromium will not start), so visual proof is a person's reload.
Crosstab header alignment needs the live DOM: open the dashboard in the Browser pane, Chase logs
in, inspect and test CSS there before touching the theme.

## Theme CSS from here (2026-09-21): how a stylesheet change actually reaches the page
An org's `/themes/default/overrides_custom.css` may be a REFERENCE (`referenceUri`) to a root theme
(`/themes/OriginBA Branded/...` on internal); edit the root file. Theme files refuse REST PUT (403,
even as superuser); the import service takes them: a package with the exporter's own file shape --
`<fileResource dataFile="overrides_custom.css.data">` descriptor + `.data` file + index listing the
resource -- imports "succeeded" and writes the file (a descriptor WITHOUT `dataFile` also says
succeeded and writes nothing). Then the server keeps serving the OLD bytes from its theme cache
(`/_themes/<hash>/...`, max-age 1 year) until someone clicks **Set as Active Theme** on the theme in
the repository UI; re-setting the org's theme over REST does not flush it. Ellensburg-style scope
check: DEV and STAGE hold their own copies, so the root edit reached only Origin_DEMO.
Chart labels, CORRECTED the same day from the live DOM: `dataLabels.style.color = contrast` is right
only for a label INSIDE its bar. Every label on these dashboards sits OUTSIDE (above a column, beside
a bar, over a gauge), and there this Highcharts build resolves `contrast` to WHITE on the white plot
area: four labels vanished and Chase asked whether they had been removed. The fix is an explicit
`#1F2933` with `textOutline none` (`jrs_adhoc_chart_props.py --only-if ...=contrast --set ...=#1F2933`,
20 states, each read back; both dashboards re-measured: every label rgb(31,41,51) over
`highcharts-plot-background`). Gauge numbers carry inline colours and never changed. Rule 2 (chart
text, gauge captions 9px) is served after the UI flush: the org's theme hash changed (A966A7AA) and
the served overrides_custom.css is 37,012 bytes with both rules. Measure a formatting change in the
DOM (colour, size, what lies under the label) before calling it done; the state file cannot tell you.

## Building a NEW domain from scratch (2026-09-23, Adjustment A/P Request domain)
Author the schema in a builder (`build_adj_ap_request_domain.py` is the template: TABLES, JOINS,
CALCULATED, SETS, MEASURES -> XML), test it offline (`tests/test_adj_ap_request_domain.py`), import
with `jrs_import_domain.py`, prove with its probe and `jrs_domain_query.py`. Three things the
validator does NOT catch and the server does: `<joinInfo alias>` must be the root TABLE id (500
"ordering minJoins" otherwise); no empty `<filterString>` ("exception parsing filter string ''");
report-unit descriptions over 250 characters are refused. Verify grain and join reachability in
Oracle FIRST (read-only MCP): the request->adjustment link is 1:1 and never fails, but 2 of 16
Odessa adjustments point at a missing SA, so everything past the adjustment is outer.

## Hiding a folder from every client user (2026-09-23, Workstreams and Origin_Tools)
Chase's pattern, set from the root superuser in each client org: explicit permissions on the
folder, `role:/ROLE_USER` = 0 AND `role:/ROLE_ADMINISTRATOR` = 0 (No Access), so only the root
superuser sees it; org admins lose it too. Tested by logging in as a user. Applied to
`/SmartCity/Report/Workstreams` (by Chase) on the five test client orgs; applied to
`/SmartCity/Origin_Tools` by tool and then rolled back the same hour on Chase's word (a theme looked
broken at the time; it recovered on its own, and permission entries on a reports folder cannot
reach a theme) -- Origin_Tools is visible again there; re-hide only on an explicit go; prod already had `ROLE_USER=0` on Origin_Tools everywhere and on Workstreams for
CityCorp / Fond_Du_Lac / College_Station only -- Ellensburg and Newark1 prod Workstreams still
inherit (visible), a gap to close on Chase's word. `perms-set` REPLACES the list; the recipient is
`role:/ROLE_X` (colon) -- `role/ROLE_X` is a 400. Before hiding, prove nothing outside depends on
it: scan every inventory file (descriptors AND `.data` -- dashboards embed views by path) for the
folder's URIs, and the org's jobs. Workstreams' only dependents were five Origin_Tools views
(three Workstreams domains), and Origin_Tools has none, so hiding both breaks nothing a user
could still run. Deleting Workstreams (90 resources) needs those five repointed or removed
first; hide now, delete later.

## Moving anything between orgs as ROOT (2026-09-24, `jrs_promote.py`)

Chase: promote the A/P request domain + report from Origin_DEV to "Odessa dev" fast, with every
safe check kept, and make that the way objects move from now on. "Odessa dev" is the Odessa org
on the TEST server whose Standard Offering binds to `Origin_DataVergence_DS` (label
"Odessa_DataVergence_DS (DEV)", pdevdb_odessa: 51 of 51 domain references); `Odessa_DS` points at
the TEST database. Chase's own Odessa login differs from the root one; it was never needed.

Why root, measured: the superuser exports and imports with ABSOLUTE paths
(`/organizations/organization_1/organizations/<Org>/...`, index `rootTenantId="organizations"`),
so a package rewritten from one org's paths to another's lands in the other org, and no
org-scoped login (the thing that answered 401 on Odessa) is involved. What the root export
shape taught, each now a test in `tests/test_jrs_promote.py`:
- A root export drags EVERY ancestor `.folder.xml` along, up to `/organizations` itself. None of
  it may travel: the org root folder is never re-imported. The package carries only the
  referenced resources' own files (datasource, a view's domain) from the target's export.
- A domain names its datasource in THREE places: the descriptor `<dataSourceReference><uri>`
  and `<alias>`, and inside `schema.data` as `datasourceId="X"` on every table AND
  `<jdbcDataSource id="X">` under `<dataSources>`. The verify step (source datasource name must
  not survive) caught the fourth one on the first dry run.
- A moved resource's own descriptor (or a folder's `.folder.xml`) names its PARENT, which no
  path move covers when `--into` is a different folder: repointed first, then the path moves
  (longest first, on uri boundaries so `/adj` never rewrites `/adj_ap_requests_control`).
- Exports for a promotion are taken WITHOUT repository permissions: the resources inherit the
  destination folder's, which is what a client org wants.
- Importing two resources whose parent folder exists, with no folder entries in the package,
  works (Odessa Adjustments, 2026-09-24): the importer needs referenced RESOURCES in the
  package, not ancestor folders. Missing destination folders are written into the package.
Proof on Odessa: import without warnings; re-export of all 8 package files matches (stamps
ignored); domain metadata 6 sets, flat query 21 rows = `count(*) from ci_adj_apreq` on
pdevdb_odessa (21, all with an adjustment); status x adjustment-status groups (H/50 1, P/50 10,
R/50 2, X/50 4, X/60 4) and the report's group sums (686.00, 191.23, 2,078.07 / 2,085.84) tie the
database to the cent. Package under `backups/jaspersoft/promote/<stamp>/` with `source.zip`,
`target_carried.zip`, `target_after.zip` (a replace also writes `target_before.zip`, the rollback;
a fresh add rolls back with `jrs_repository.py delete`).

## The Adjustment domain, and the two Ad Hoc engine facts it exposed (2026-09-24)

Chase: take the Workstreams Adjustment domain into the Standard Offering and make it comprehensive
("all things adjustments"); then put the domain and the static A/P report in every client's
Adjustments folder. Built as `build_adjustment_domain.py` (see its README for the design and the
proofs, all exact against Oracle), imported on Origin_DEV with `jrs_import_domain.py`, rolled out
with `jrs_promote.py` per org (`--ds` from `clients.yml`: Ellensburg_DS, FondDuLac_DS, CityCorp_DS,
CollegeStation_DS, Newark1_DS, Origin_DataVergence_DS).

1. **The Ad Hoc engine's 300,000-row cap is a SERVER setting** (Chase; he can raise it). A query
   whose work is pushed to the database (distinct counts, grouping on real columns or on a
   CaseWhen of real columns) counts everything: 2,237,269 FTs on the FT and GL snapshot domain,
   501,193 adjustments. A query with a Sum / CountAll / a group on a non-pushable field is
   evaluated in memory and answers 300,001 -- silently, per group (Credit 159,498 right, Debit cut
   at 140,503 = the remainder to 300,001). A flat detail query reports `totalCounts` 300001 too.
   QA rule from here: tie COUNTS on the full population with `--agg X:CountDistinct`, tie MONEY on
   a window under the cap with `--where`; both are exact on the Adjustment domain. Ad Hoc users
   are under the same cap on every domain: a view that sums an unfiltered big domain is wrong,
   quietly, above 300k rows.
2. **`ElapsedDays(Today(0), col)` is evaluated in memory**: a flag built on it grouped 478,372 of
   501,193 rows. Anything with "today" in it belongs in a derived table's SQL (`trunc(sysdate) -
   col`), which is pushed down and exact. `IsNull(x) or x == ' '` is the right test for an unset
   CHAR key (they hold spaces, not null): transfers tied 261,050 with it.
3. `jrs_import_domain.py` with `update=true` REPLACES an existing domain in place (used twice on
   Origin_DEV the same hour); the probe now reads two items of the ROOT set only, because two of
   every set drags every derived table in (152 s on 501k rows).

Rollout result (test server, 2026-09-24, domain + static report into every client's
`Finance/Adjustments`): Ellensburg 501,193 / 748, Fond_Du_Lac 719,248 / 1,574, CityCorp 328,285 /
1,352, College_Station 3,449,442 / 11,299, Newark1 9,963,883 / 52, Odessa 44,410 / 21 -- each pair
is the domain's distinct count of adjustments / A/P requests AND the client database's `count(*)`,
exact on all six. Two tool lessons from the run: a JDBC url can read `@//host:port/service`
(CityCorp_DS), and the host check must treat a host the TARGET's own datasource shares as
not foreign (Origin_DEV_DS, Ellensburg_DS and CityCorp_DS all sit on 10.13.4.91); the repository
search can lag an import by seconds, so the execution step re-lists before calling a resource
missing. Prod: not touched; same command with `--i-mean-prod` per org on Chase's word.

## Additive-only domain changes, and the three that shipped this way (2026-09-24)

Chase's rule: a change to a deployed domain ADDS; every existing id, label, join, resource,
calculation and measure stays, or bound views and reports break. `domain_schema.additions_only(before,
after)` is the proof (empty list) and `jrs_domain_patch_apply.py --patch <module>` refuses anything
else before it writes; `domain_schema.add_to_schema(...)` is how a patch module adds tables, joins,
calculated fields and sets to an org's EXPORTED schema (never a rebuilt one). Seven proofs per org:
export (rollback), patch + validate + additive, PUT with version, read-back byte-equal, metadata lists
the new sets, every bound view executes, probe of the new items. Bound views are found by reading
every Ad Hoc view descriptor in the org (minutes on 300 views; the slow step).

- **Severance Process domain** `patch_severance_domain`: `CI_SEV_EVT_FA` -> `CI_FA` (the field
  activity each event created; 15,297 of 15,297 resolve at Ellensburg) + labels, `CI_SEV_PROC_TMP`.
  Probe = 226,391 rows = the event count: grain untouched.
- **Field Activity domain** `patch_field_activity_domain`: the CCB field activity behind the MDM
  activity through `D1_ACTIVITY_IDENTIFIER` type **`D1RI`** (101,668 of 101,668 resolve to `CI_FA`,
  max ONE per activity, up to 8 activities per FA; the old dbt note that they "do not link" tested
  FA_EXT_ID and the BO external reference, which are empty). 33,886 of the domain's 37,057 activities
  carry one (completed 15,641 / pending 2,549 / canceled 15,696), 3,171 do not. Also `CI_FO`, the
  FA type / dispatch group / cancel reason labels, the C/P/X status lookup.
- **Bill Cycle Schedule domain** (new, `build_bill_cycle_schedule_domain.py`): see its README; the
  equality join cycle + window start is right (0 unmatched bills inside any window range; the
  unmatched are off-cycle bills with no cycle at all).
- **Standardized_Reports**: the five static SQL report units moved from their module folders to
  `Standard_Offering/Standardized_Reports` on Origin_DEV (`jrs_repository.py --confirm ROOT move`;
  a body-less PUT needs `Content-Type: application/json` or 10.0 answers 500 "MediaType ... null"),
  all five render from there; `generate_sql_report_pack.FOLDER` deploys there from now on. No
  scheduled job referenced them (every job on the server is a paused College_Station legacy one plus
  one Odessa test job). Clients get the folder with `jrs_promote.py --resource .../Standardized_Reports
  --into /SmartCity/Report/Standard_Offering`.
Scheduling, for the record: a job = report + trigger (once / simple / calendar) + fixed parameter
values + output formats + destination (repository folder, email, FTP), runs as its creator; REST
`/rest_v2/jobs` (our `jobs / job / job-run / job-delete`). A schedulable standard report needs
RELATIVE date defaults (last month), which the pack's FROM_DT / TO_DT do not have yet.

## College_Station PROD -> TEST, 21 custom resources + their domains (2026-09-25)

Chase's list (20 Ad Hoc views + 1 report under `/SmartCity/Report/Custom_Reports`), all moved with
`jrs_promote.py --from prod:College_Station --to test:College_Station --ds CollegeStation_DS`, prod
read only. Two prerequisites first (the cash-receipt domain and the "Status Updates" view the report
is built on), then the 21 (5 replaced test copies), then EVERY referenced domain replaced with
prod's (13) at Chase's word ("they may have changed the domain and built the prod views on it"),
then all 22 executed on test again. Proof per item: import without warnings, re-export byte-equal
to prod inside the scope, execution. Row counts differ between test and prod because the two
databases are at different points in time; that is not a defect (Chase). Tool lessons, each now a
test: the same org id on two servers shares its root path (the "source org path survives" guard
only fires when the roots differ); a folder the tool creates is re-serialised on import (proved by
existence); domain item ids are FULL group paths (`CI_ADJ_1.CI_ADJ_TYPE_L.DESCR`) and groups nest,
so `domain_items` walks the tree; view field ids are read from the state's `fieldName` / `name`
attributes, never bare tokens; a group-less domain keeps its items on the root level and is probed
by bare item id; the repository search lags an import by seconds (re-list before calling a
resource missing); a heavy view's execution can exceed the 600 s API read (Status Updates the
first time) -- it imported byte-equal and executed on the re-check.

## A scheduled job that "fails" may have rendered fine: read `lastError` first (FDL prod, 2026-09-28)

Four Fond_Du_Lac prod jobs (three runs of `FDL_Asset/FDLWU_Meter_View_C2M_All`, one of
`FDL_Asset/FDL_LSV_SA_Mail_Addr`) alerted FAIL right after the client's C2M 25.4 upgrade, and the
alert body said "error while generating this report". Every job's own `lastError`
(`jrs_get.py --env prod /rest_v2/jobs/<id>`) said `report.scheduling.error.upload.to.ftp.server ...
2: no such file`: SFTP status 2 = the remote folder is gone. Both reports rendered on request with
the jobs' exact parameters (16,666 and 14,369 CSV rows), the domains and derived tables answered,
no dropped view involved. The jobs deliver CSV by SFTP to `sftp.originsmartops.com:2022` as
`fdl-sftpuser` into `/u00/fonddulac/interface/Origin/Analytics/Download` (the C2M interface
directory the utility's import reads); the upgrade rebuilt that side. Fix is on the SFTP host
(recreate the directory / permissions) or the four jobs' `folderPath` (PUT /rest_v2/jobs/<id>,
prod write). The `job` subcommand truncates at 800 characters; `jrs_get.py` prints the whole thing
with passwords masked. `jrs_repository.py run --format csv --param K=V` reproduces a job's run.
