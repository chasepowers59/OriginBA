# Proving the promotion: Origin_DEV to Origin_TEST

Written 2026-09-18, before any run (VPN off). The rule in `jaspersoft-server-operations` is
that folder promotion is proven on Origin_DEV, then Origin_TEST, before any client. Nothing in
the repo has ever targeted Origin_TEST: no environment profile, no mapping row, no
`Origin_TEST_DS` overlay, and the org holds no Standard Offering (inventory 2026-09-18).
This is the plan to close that, using the same package shape a client promotion uses, so the
proof carries over.

## What is true today (measured)

| | Origin_DEV (test server) | Origin_TEST (test server) |
| --- | --- | --- |
| Standard Offering | 53 domains, 156 views, 14 dashboards, 4 report units; last change 2026-09-18 | none (legacy `/SmartCity/Report/Workstreams` layout only) |
| Datasources | `Origin_DEV_DS` (JRS2C2M @ 10.13.4.91/ptestdb_ellensburg), `Origin_INT_DEV_DS` | `Origin_TEST_DS` (JRS2C2M @ smartcity-db-test/ptestdb_ellensburg), `Origin_DEV_DS` |
| Login | `cpowers@originutility.com|Origin_DEV` | `cpowers@originutility.com|Origin_TEST` |

Both datasources reach the Ellensburg 25.4 TEST database, so a smoke test in Origin_TEST
returns real rows.

## Steps (VPN on; each step names its proof)

1. **Baseline.** `jrs_inventory.py snapshot --env test --org Origin_DEV` and `--org Origin_TEST`;
   commit. The Origin_TEST zip is the rollback.
2. **Capture the target datasource.** Export `/DataSource/Origin_TEST_DS` from the Origin_TEST org
   (org-scoped login) into `deploy/jaspersoft_datasources/canonical/Origin_TEST_DS/` the way the
   other canonical folders are laid out (index.xml + `resources/DataSource/Origin_TEST_DS.xml`,
   password as the server's encrypted value). Add the registry row: `clients.yml` has no
   Origin_TEST entry; the promotion mapping needs `Origin_TEST,Origin_TEST_DS`, so add it to a
   one-off mapping file under `deploy/jaspersoft_client_promotion/` (the NEWARK_DEBT_MGMT recipe
   is the precedent) rather than to the client registry.
3. **Export the source.** The Standard Offering folder from Origin_DEV by REST
   (`/rest_v2/export` of `/SmartCity/Report/Standard_Offering`, org-scoped login), which is the
   tenant-root export shape the pipeline expects. Keep the zip under `backups/` (gitignored).
4. **Patch (guard) and build.** `patch_vee_exception_todo_joins.py` on the export -- a no-op on a
   current export, since the Origin_DEV VEE Exception domain has carried all eleven To Do joins as
   left outer since 2026-08-27 (measured in the 2026-09-18 inventory; CityCorp PROD and Odessa
   test still hold the 2025-09-11 domain with eight inner joins). Then
   `run_client_import_pipeline.py --src-org Origin_DEV --src-ds Origin_DEV_DS --mapping <one-off
   csv> --datasource-export-dir deploy/jaspersoft_datasources/canonical` with the tenant-root,
   org-relative, import-into-existing-tenant, light-touch flags the Standard Offering pipeline
   passes (read them from `run_client_standard_offering_pipeline.py`, do not retype them).
5. **Verify.** `verify_prepared_import.py --zip ... --target-org Origin_TEST --target-ds
   Origin_TEST_DS --repository-layout tenant_root --expect-datasource-overlay
   --import-module-folder-uri /SmartCity/Report/Standard_Offering` must print `status: PASS`.
6. **Import by REST, inside the org.** `jrs_repository.py --env test import <zip>` with
   `JRS_USER=cpowers@originutility.com|Origin_TEST`. The tool exits non-zero on warnings; a
   warning is a failed deploy until explained.
7. **Smoke.** List `/SmartCity/Report/Standard_Offering` in Origin_TEST by REST (all nine
   modules present, domain count equals the source); open one domain-based Ad Hoc view per module
   and one dashboard in the UI against `Origin_TEST_DS` and confirm rows, not a connection error.
8. **Diff.** Snapshot Origin_TEST again; `jrs_inventory.py diff test:Origin_DEV test:Origin_TEST
   --folder /SmartCity/Report/Standard_Offering`. The only expected differences are the
   datasource reference (`Origin_DEV_DS` to `Origin_TEST_DS`) and dates. Anything else is a
   pipeline defect to fix before a client sees it. Commit the inventory with the diff in the
   message.
9. **Rollback, if needed.** Delete `/SmartCity/Report/Standard_Offering` in Origin_TEST by REST,
   or import the step-1 zip.

## What this proves, and what it does not

Proves: the export shape, the VEE patch, the tenant-root rewrite, the datasource overlay, the
REST import path, and the diff-based acceptance, end to end on the 10.0 server. That is every
moving part of a client promotion except the client's own datasource and org.

Does not prove: the 9.0 prod server (it moves to 10.0 on 2026-09-21; prove there after the
upgrade, against the re-snapshotted baseline), and Fond du Lac (no Standard Offering on either
server; its test org is the first real target once this passes).

## Open questions for Chase

- Should Origin_TEST keep the Standard Offering permanently as the staging org (the rule says
  yes), or be cleaned after the proof?
- Origin_TEST also carries a datasource named `Origin_DEV_DS`. Leave it, or remove it so a
  package that leaked the source datasource name would fail loudly there?

## Result (2026-09-18, run end to end)

**Proven.** `/SmartCity/Report/Standard_Offering` from Origin_DEV is in Origin_TEST: 53 domains,
156 Ad Hoc views, 14 dashboards, 4 report units, nine modules -- the same file set as the source
(0 only-in either side). Origin_TEST_DS was re-saved with its own export's bytes: URL, user,
driver and update date unchanged (only the repository version counter moved 30 to 31). The
adjustment-type pick-list answered 59 codes from the Ellensburg test database through
Origin_TEST_DS in one second and a report rendered. Baseline and after snapshots are committed.

**What the run taught, and what changed because of it.**
- The REST import inside an org needs the package to carry `rootTenantId=<Org>` -- the server's
  own org-export shape. The tenant-root package the pipeline builds (no rootTenantId, for the
  UI's Repository > Import) fails by REST with `import.root.into.organization.not.allowed`, and
  nothing is created. So: pipeline package + `rootTenantId` property = the REST package. The
  `/public` dashboard template in the package was not the cause (tested without it).
- `jrs_repository.py import` polled `/rest_v2/import/<id>`, which on 10.0 returns the task's
  parameters, so it reported "still running" on a failed task. It polls `/state` now and prints
  the failure reason.
- The verifiers pass either shape (`--tenant-id <Org>` for the REST one).
- 171 of the 728 files differ after import, all descriptor-level: the server adds
  `<componentType>default</componentType>` to local resources on save, and 7 dashboards plus
  3 views that in Origin_DEV still point at `/SmartCity/Report/Workstreams/...` domains (the
  legacy tree, including the old VEE Exception domain) are rewired by the pipeline to the
  Standard_Offering copies. That rewiring is correct for every client; it also means those ten
  Origin_DEV resources read the legacy domains at home.
- Side effect: the first (failed) import made the server materialise Origin_TEST's
  `/themes/default` from its parent (five ORIGINBA_V1x note files, created 16:10 UTC, content
  dated 2026-08-12). Theme inheritance, not content from the package; harmless, recorded.
- The repo's `deploy/jaspersoft_datasources/clients/FondDuLac_DS` overlay was STALE: it pointed
  at the pre-25.4 host (`smartcity-db-test`, `origintestvcn`) while the live datasource points at
  `smartcity-db-test-v1-2`. Importing with it would have moved Fond du Lac's datasource back.
  The overlay is now the org's own export of 2026-09-18, and the rule is: **export the target
  org's datasource fresh before every promotion; never promote with a stored overlay.**

Fond du Lac's package is built and verified from the same source export
(`prepared_imports/Fond_Du_Lac_Standard_Offering_import_rest.zip`, DS byte-identical to the
live export, no Origin_DEV identifier, PASS on both verifiers). Not imported: a client org waits
for Chase's word.
